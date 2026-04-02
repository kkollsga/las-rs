/// Data section parser: handles whitespace-delimited and comma-delimited data,
/// wrapped mode, and null policies.

use once_cell::sync::Lazy;
use regex::Regex;
use std::borrow::Cow;

static COMMA_DECIMAL_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(\d),(\d)").unwrap());
static RUNON_HYPHEN_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(\d)-(\d)").unwrap());

/// Strip Ctrl-Z (EOF marker) without allocating if not present.
#[inline]
fn strip_ctrl_z(s: &str) -> Cow<'_, str> {
    if memchr::memchr(0x1A, s.as_bytes()).is_some() {
        Cow::Owned(s.replace('\x1A', ""))
    } else {
        Cow::Borrowed(s)
    }
}

#[derive(Debug, Clone)]
pub enum NullPolicy {
    Strict,      // Only replace exact NULL header value
    None,        // No replacement at all
    Common,      // NULL + common sentinels (-999.25, 9999.25, etc.)
    Aggressive,  // Common + 999, 9999, etc.
    All,         // Aggressive + any non-numeric
    Custom(Vec<f64>),
    CustomMixed { floats: Vec<f64>, strings: Vec<String> },
}

impl NullPolicy {
    pub fn from_str_or_list(val: &str) -> Self {
        match val.to_lowercase().as_str() {
            "strict" => NullPolicy::Strict,
            "none" => NullPolicy::None,
            "common" => NullPolicy::Common,
            "aggressive" => NullPolicy::Aggressive,
            "all" => NullPolicy::All,
            _ => NullPolicy::Strict,
        }
    }
}

pub fn parse_data_section(
    lines: &[&str],
    n_curves: usize,
    null_value: f64,
    delimiter: Option<char>,
) -> Vec<Vec<f64>> {
    parse_data_inner(lines, n_curves, null_value, delimiter, false, &NullPolicy::Strict, &["#".to_string()])
}

/// Result of data parsing: float columns + auto-detected string columns
pub struct ParsedData {
    pub float_columns: Vec<Vec<f64>>,
    pub string_columns: std::collections::HashMap<usize, Vec<String>>,
}

pub fn parse_data_section_with_policy(
    lines: &[&str],
    n_curves: usize,
    null_value: f64,
    delimiter: Option<char>,
    wrapped: bool,
    null_policy: &NullPolicy,
    read_policy: Option<&str>,
    ignore_comments: &[String],
) -> ParsedData {
    // For wrapped mode, use the old parse_data_inner (no string auto-detect)
    if wrapped {
        let effective_lines: Vec<String>;
        let final_refs: Vec<&str>;
        if let Some(policy) = read_policy {
            effective_lines = lines.iter().map(|line| apply_read_policy(line, policy)).collect();
            final_refs = effective_lines.iter().map(|s| s.as_str()).collect();
        } else {
            effective_lines = Vec::new();
            final_refs = lines.to_vec();
        }
        let float_columns = parse_data_inner(
            &final_refs, n_curves, null_value, delimiter, true, null_policy, ignore_comments
        );
        return ParsedData {
            float_columns,
            string_columns: std::collections::HashMap::new(),
        };
    }

    // Unwrapped mode: check if string detection is needed
    let effective_lines: Vec<String>;
    let line_refs: Vec<&str>;

    if let Some(policy) = read_policy {
        effective_lines = lines.iter().map(|line| apply_read_policy(line, policy)).collect();
        line_refs = effective_lines.iter().map(|s| s.as_str()).collect();
    } else {
        effective_lines = Vec::new();
        line_refs = lines.to_vec();
    }
    let data_lines = &line_refs;

    let is_comment = |line: &str| -> bool {
        let trimmed = line.trim();
        ignore_comments.iter().any(|prefix| trimmed.starts_with(prefix.as_str()))
    };

    // Fast path: sample first 20 data lines to check for non-numeric tokens.
    // If all tokens parse as f64, skip string detection entirely (90%+ of files).
    let sample_size = 20;
    let mut has_non_numeric = false;
    let mut sampled = 0;
    for line in data_lines.iter() {
        let trimmed = line.trim();
        if trimmed.is_empty() || is_comment(trimmed) { continue; }
        let cleaned = strip_ctrl_z(trimmed);
        let cleaned = cleaned.trim();
        if cleaned.is_empty() { continue; }
        let tokens: Vec<&str> = match delimiter {
            Some(',') => cleaned.split(',').map(|s| s.trim()).collect(),
            Some('\t') => cleaned.split('\t').map(|s| s.trim()).collect(),
            _ => cleaned.split_whitespace().collect(),
        };
        for (i, tok) in tokens.iter().enumerate() {
            if i > 0 && tok.parse::<f64>().is_err() && !tok.is_empty() {
                has_non_numeric = true;
                break;
            }
        }
        if has_non_numeric { break; }
        sampled += 1;
        if sampled >= sample_size { break; }
    }

    // Fast path: all-numeric file → use single-pass parse_data_inner (no allocations)
    if !has_non_numeric {
        let float_columns = parse_data_inner(
            data_lines, n_curves, null_value, delimiter, false, null_policy, ignore_comments
        );
        return ParsedData {
            float_columns,
            string_columns: std::collections::HashMap::new(),
        };
    }

    // Slow path: string detection needed — two-pass approach

    let mut all_rows: Vec<Vec<String>> = Vec::new();
    for line in data_lines.iter() {
        let trimmed = line.trim();
        if trimmed.is_empty() || is_comment(trimmed) { continue; }
        let cleaned = strip_ctrl_z(trimmed);
        let cleaned = cleaned.trim();
        if cleaned.is_empty() { continue; }

        let tokens: Vec<String> = match delimiter {
            Some(',') => cleaned.split(',').map(|s| s.trim().to_string()).collect(),
            Some('\t') => cleaned.split('\t').map(|s| s.trim().to_string()).collect(),
            _ => tokenize_whitespace(cleaned),
        };
        all_rows.push(tokens);
    }

    if all_rows.is_empty() || n_curves == 0 {
        return ParsedData {
            float_columns: vec![Vec::new(); n_curves],
            string_columns: std::collections::HashMap::new(),
        };
    }

    // Detect which columns have non-numeric data
    let max_cols = all_rows.iter().map(|r| r.len()).max().unwrap_or(0);
    let mut non_numeric_count = vec![0usize; max_cols];
    let mut total_count = vec![0usize; max_cols];

    for row in &all_rows {
        for (col, token) in row.iter().enumerate() {
            if col >= max_cols { break; }
            total_count[col] += 1;
            if token.parse::<f64>().is_err() {
                non_numeric_count[col] += 1;
            }
        }
    }

    // A column is "string" if >50% of its values are non-numeric (skip col 0 = index)
    let mut string_col_set: std::collections::HashSet<usize> = std::collections::HashSet::new();
    for col in 1..max_cols {
        if total_count[col] > 0 && non_numeric_count[col] > total_count[col] / 2 {
            string_col_set.insert(col);
        }
    }

    // Pass 2: Build float and string columns
    let mut float_columns: Vec<Vec<f64>> = vec![Vec::new(); max_cols.max(n_curves)];
    let mut string_columns: std::collections::HashMap<usize, Vec<String>> = std::collections::HashMap::new();
    for &col in &string_col_set {
        string_columns.insert(col, Vec::new());
    }

    for row in &all_rows {
        for col in 0..float_columns.len() {
            if col < row.len() {
                if string_col_set.contains(&col) {
                    string_columns.get_mut(&col).unwrap().push(row[col].clone());
                    float_columns[col].push(f64::NAN);
                } else {
                    float_columns[col].push(row[col].parse::<f64>().unwrap_or(f64::NAN));
                }
            } else {
                float_columns[col].push(f64::NAN);
            }
        }
    }

    // Apply null policy on float columns (skip col 0 and string columns)
    apply_null_policy(&mut float_columns, null_value, null_policy);

    ParsedData { float_columns, string_columns }
}

/// Tokenize a whitespace-delimited line, respecting quoted strings
fn tokenize_whitespace(line: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut in_quotes = false;

    for ch in line.chars() {
        if ch == '"' {
            in_quotes = !in_quotes;
            // Don't include the quote chars in the token
        } else if ch.is_whitespace() && !in_quotes {
            if !current.is_empty() {
                tokens.push(current.clone());
                current.clear();
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        tokens.push(current);
    }
    tokens
}

fn apply_read_policy(line: &str, policy: &str) -> String {
    let mut result = line.to_string();
    if policy.contains("comma-decimal") {
        result = COMMA_DECIMAL_RE.replace_all(&result, "$1.$2").to_string();
    }
    if policy.contains("run-on(-)") {
        result = RUNON_HYPHEN_RE.replace_all(&result, "$1 -$2").to_string();
    }
    result
}

fn parse_data_inner(
    lines: &[&str],
    n_curves: usize,
    null_value: f64,
    delimiter: Option<char>,
    wrapped: bool,
    null_policy: &NullPolicy,
    ignore_comments: &[String],
) -> Vec<Vec<f64>> {
    let is_comment = |line: &str| -> bool {
        let trimmed = line.trim();
        ignore_comments.iter().any(|prefix| trimmed.starts_with(prefix.as_str()))
    };
    if lines.is_empty() || n_curves == 0 {
        return vec![Vec::new(); n_curves];
    }

    let mut columns: Vec<Vec<f64>> = vec![Vec::new(); 0];

    if wrapped && n_curves > 0 {
        // Wrapped mode: accumulate tokens across lines
        let mut all_tokens: Vec<f64> = Vec::new();
        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() || is_comment(trimmed) {
                continue;
            }
            let cleaned = strip_ctrl_z(trimmed);
            let cleaned = cleaned.trim();
            if cleaned.is_empty() {
                continue;
            }
            let tokens: Vec<&str> = match delimiter {
                Some(',') => cleaned.split(',').map(|s| s.trim()).collect(),
                Some('\t') => cleaned.split('\t').map(|s| s.trim()).collect(),
                _ => cleaned.split_whitespace().collect(),
            };
            for tok in tokens {
                all_tokens.push(parse_token(tok));
            }
        }

        // Reshape: every n_curves tokens is one depth step
        // Handle sparse data: if tokens don't divide evenly, try detecting
        // actual columns per step
        let total = all_tokens.len();
        let actual_cols = if total % n_curves == 0 {
            n_curves
        } else {
            // Try to find a divisor close to n_curves
            let mut best = n_curves;
            for candidate in (1..=n_curves).rev() {
                if total % candidate == 0 {
                    best = candidate;
                    break;
                }
            }
            best
        };

        columns = vec![Vec::new(); n_curves];
        let mut idx = 0;
        while idx + actual_cols <= all_tokens.len() {
            for col in 0..actual_cols {
                columns[col].push(all_tokens[idx + col]);
            }
            // Fill remaining curves with NaN for this row
            for col in actual_cols..n_curves {
                columns[col].push(f64::NAN);
            }
            idx += actual_cols;
        }
    } else {
        // Normal (unwrapped) mode — pre-allocate columns
        let estimated_rows = lines.len(); // upper bound
        if n_curves > 0 {
            columns = (0..n_curves)
                .map(|_| Vec::with_capacity(estimated_rows))
                .collect();
        }

        let inline_null = matches!(null_policy, NullPolicy::Strict);

        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() || is_comment(trimmed) {
                continue;
            }
            let cleaned = strip_ctrl_z(trimmed);
            let cleaned = cleaned.trim();
            if cleaned.is_empty() {
                continue;
            }

            let tokens: Vec<&str> = match delimiter {
                Some(',') => cleaned.split(',').map(|s| s.trim()).collect(),
                Some('\t') => cleaned.split('\t').map(|s| s.trim()).collect(),
                _ => cleaned.split_whitespace().collect(),
            };

            // Grow columns if needed (for excess data columns)
            while columns.len() < tokens.len() {
                let existing_rows = if columns.is_empty() { 0 } else { columns[0].len() };
                let mut col = Vec::with_capacity(estimated_rows);
                col.resize(existing_rows, f64::NAN);
                columns.push(col);
            }

            for (col_idx, token) in tokens.iter().enumerate() {
                let val = parse_token(token);
                // Inline null replacement for Strict policy (skip index column 0)
                let val = if inline_null && col_idx > 0 && (val - null_value).abs() < 1e-10 {
                    f64::NAN
                } else {
                    val
                };
                columns[col_idx].push(val);
            }

            for col_idx in tokens.len()..columns.len() {
                columns[col_idx].push(f64::NAN);
            }
        }
    }

    // Apply null replacement for non-Strict policies (skip if already inlined)
    if !matches!(null_policy, NullPolicy::Strict) {
        apply_null_policy(&mut columns, null_value, null_policy);
    }

    columns
}

fn apply_null_policy(columns: &mut [Vec<f64>], null_value: f64, policy: &NullPolicy) {
    match policy {
        NullPolicy::None => {
            // No replacement at all
        }
        NullPolicy::Strict => {
            // Only replace exact NULL header value
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if (*val - null_value).abs() < 1e-10 {
                        *val = f64::NAN;
                    }
                }
            }
        }
        NullPolicy::Common => {
            let sentinels = vec![null_value, -999.25, 9999.25, 999.25];
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if sentinels.iter().any(|s| (*val - s).abs() < 1e-10) {
                        *val = f64::NAN;
                    }
                    // Also handle "-" (already NaN from parse_token)
                }
            }
        }
        NullPolicy::Aggressive => {
            let sentinels = vec![
                null_value, -999.25, 9999.25, 999.25,
                999.0, 9999.0, 2147483647.0, 32767.0,
            ];
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if sentinels.iter().any(|s| (*val - s).abs() < 1e-10) {
                        *val = f64::NAN;
                    }
                    // -0.0 check
                    if *val == 0.0 && val.is_sign_negative() {
                        *val = f64::NAN;
                    }
                }
            }
        }
        NullPolicy::All => {
            // Aggressive + any NaN that was already set (from non-numeric text)
            let sentinels = vec![
                null_value, -999.25, 9999.25, 999.25,
                999.0, 9999.0, 2147483647.0, 32767.0,
            ];
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if sentinels.iter().any(|s| (*val - s).abs() < 1e-10) {
                        *val = f64::NAN;
                    }
                    // NaN already set for non-numeric text in parse_token
                }
            }
        }
        NullPolicy::Custom(values) => {
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if values.iter().any(|s| (*val - s).abs() < 1e-10) {
                        *val = f64::NAN;
                    }
                }
            }
        }
        NullPolicy::CustomMixed { floats, strings: _ } => {
            // String sentinels already became NaN from parse_token (non-numeric)
            // Float sentinels need explicit replacement
            for col_idx in 1..columns.len() {
                for val in &mut columns[col_idx] {
                    if floats.iter().any(|s| (*val - s).abs() < 1e-10) {
                        *val = f64::NAN;
                    }
                }
            }
        }
    }
}

#[inline(always)]
fn parse_token(token: &str) -> f64 {
    // fast_float2 is 2-5x faster than str::parse for float parsing
    fast_float2::parse(token).unwrap_or(f64::NAN)
}

/// Parse data section that may contain string columns.
pub fn parse_data_section_with_strings(
    lines: &[&str],
    n_curves: usize,
    null_value: f64,
    delimiter: Option<char>,
    string_column_indices: &[usize],
) -> (Vec<Vec<f64>>, std::collections::HashMap<usize, Vec<String>>) {
    use std::collections::HashMap;

    if lines.is_empty() || n_curves == 0 {
        return (vec![Vec::new(); n_curves], HashMap::new());
    }

    let mut float_columns: Vec<Vec<f64>> = Vec::new();
    let mut string_columns: HashMap<usize, Vec<String>> = HashMap::new();
    for &idx in string_column_indices {
        string_columns.insert(idx, Vec::new());
    }

    for line in lines {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let cleaned = strip_ctrl_z(trimmed);
        let cleaned = cleaned.trim();
        if cleaned.is_empty() {
            continue;
        }

        let tokens: Vec<&str> = match delimiter {
            Some(',') => cleaned.split(',').map(|s| s.trim()).collect(),
            Some('\t') => cleaned.split('\t').map(|s| s.trim()).collect(),
            _ => cleaned.split_whitespace().collect(),
        };

        while float_columns.len() < tokens.len() {
            let existing_rows = if float_columns.is_empty() { 0 } else { float_columns[0].len() };
            float_columns.push(vec![f64::NAN; existing_rows]);
        }

        for (col_idx, token) in tokens.iter().enumerate() {
            if string_column_indices.contains(&col_idx) {
                string_columns.entry(col_idx)
                    .or_insert_with(Vec::new)
                    .push(token.to_string());
                float_columns[col_idx].push(f64::NAN);
            } else {
                float_columns[col_idx].push(parse_token(token));
            }
        }

        for col_idx in tokens.len()..float_columns.len() {
            float_columns[col_idx].push(f64::NAN);
        }
    }

    // Null replacement (skip column 0)
    for col_idx in 1..float_columns.len() {
        if string_column_indices.contains(&col_idx) {
            continue;
        }
        for val in &mut float_columns[col_idx] {
            if (*val - null_value).abs() < 1e-10 {
                *val = f64::NAN;
            }
        }
    }

    (float_columns, string_columns)
}
