/// Data section parser: handles whitespace-delimited and comma-delimited data,
/// wrapped mode, and null policies.

use once_cell::sync::Lazy;
use regex::Regex;

static COMMA_DECIMAL_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(\d),(\d)").unwrap());
static RUNON_HYPHEN_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"(\d)-(\d)").unwrap());

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

pub fn parse_data_section_with_policy(
    lines: &[&str],
    n_curves: usize,
    null_value: f64,
    delimiter: Option<char>,
    wrapped: bool,
    null_policy: &NullPolicy,
    read_policy: Option<&str>,
    ignore_comments: &[String],
) -> Vec<Vec<f64>> {
    // Apply read policy substitutions to lines
    if let Some(policy) = read_policy {
        let transformed: Vec<String> = lines.iter().map(|line| {
            apply_read_policy(line, policy)
        }).collect();
        let transformed_refs: Vec<&str> = transformed.iter().map(|s| s.as_str()).collect();
        parse_data_inner(&transformed_refs, n_curves, null_value, delimiter, wrapped, null_policy, ignore_comments)
    } else {
        parse_data_inner(lines, n_curves, null_value, delimiter, wrapped, null_policy, ignore_comments)
    }
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
            let cleaned = trimmed.replace('\x1A', "");
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
        // Normal (unwrapped) mode
        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() || is_comment(trimmed) {
                continue;
            }
            let cleaned = trimmed.replace('\x1A', "");
            let cleaned = cleaned.trim();
            if cleaned.is_empty() {
                continue;
            }

            let tokens: Vec<&str> = match delimiter {
                Some(',') => cleaned.split(',').map(|s| s.trim()).collect(),
                Some('\t') => cleaned.split('\t').map(|s| s.trim()).collect(),
                _ => cleaned.split_whitespace().collect(),
            };

            while columns.len() < tokens.len() {
                let existing_rows = if columns.is_empty() { 0 } else { columns[0].len() };
                columns.push(vec![f64::NAN; existing_rows]);
            }

            for (col_idx, token) in tokens.iter().enumerate() {
                columns[col_idx].push(parse_token(token));
            }

            for col_idx in tokens.len()..columns.len() {
                columns[col_idx].push(f64::NAN);
            }
        }
    }

    // Apply null replacement based on policy (skip column 0 = index)
    apply_null_policy(&mut columns, null_value, null_policy);

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

fn parse_token(token: &str) -> f64 {
    token.trim().parse::<f64>().unwrap_or(f64::NAN)
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
        let cleaned = trimmed.replace('\x1A', "");
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
