/// Header line parser: parses `MNEM.UNIT  value : descr` format.

use once_cell::sync::Lazy;
use regex::Regex;

#[derive(Debug, Clone)]
pub struct ParsedHeaderLine {
    pub mnemonic: String,
    pub unit: String,
    pub value: String,
    pub descr: String,
}

// Primary header line regex: MNEM.UNIT VALUE : DESCR
// Unit is directly attached to the dot (no whitespace between dot and unit).
// This correctly handles: VERS.  1.2 : desc  (unit="" value="1.2")
//                    and:  STRT.M  500 : desc  (unit="M" value="500")
static HEADER_RE: Lazy<Regex> = Lazy::new(|| {
    // The separator colon must have at least one space before it to distinguish
    // from colons in time values (13:45:00) or key:value pairs (KB:10.5).
    Regex::new(r"^\s*([^.]*?)\.(\S*)\s+(.*?)\s+:\s*(.*)$").unwrap()
});

// Lines with colon but no space between unit and value (e.g., `GR.GAPI:GAMMA RAY`)
static HEADER_COMPACT_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^\s*([^.]*?)\.(\S*?)\s*:\s*(.*)$").unwrap()
});

// Fallback: no colon present
static NO_COLON_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^\s*([^.]*?)\.(\S*)\s*(.*)$").unwrap()
});

pub fn parse_header_line(line: &str) -> Option<ParsedHeaderLine> {
    let trimmed = line.trim();
    if trimmed.is_empty() || trimmed.starts_with('#') {
        return None;
    }

    // If no dot, try no-period fallback (name : value or name value : descr)
    if !trimmed.contains('.') {
        return parse_no_period_line(trimmed);
    }

    // Try primary regex (has colon and space between unit-group and value)
    if let Some(caps) = HEADER_RE.captures(trimmed) {
        let mnemonic = caps.get(1).map_or("", |m| m.as_str()).trim().to_string();
        // Validate: if mnemonic contains ':', the dot was likely a decimal point, not a separator
        if !mnemonic.contains(':') {
            let unit = strip_brackets(caps.get(2).map_or("", |m| m.as_str()).trim());
            let value = caps.get(3).map_or("", |m| m.as_str()).trim().to_string();
            let descr = caps.get(4).map_or("", |m| m.as_str()).trim().to_string();
            return Some(ParsedHeaderLine { mnemonic, unit, value, descr });
        }
        // Fall through to no-period handling
        return parse_no_period_line(trimmed);
    }

    // Try compact format: MNEM.UNIT:DESCR (colon right after unit, no space for value)
    if let Some(caps) = HEADER_COMPACT_RE.captures(trimmed) {
        let mnemonic = caps.get(1).map_or("", |m| m.as_str()).trim().to_string();
        if !mnemonic.contains(':') {
            let unit = strip_brackets(caps.get(2).map_or("", |m| m.as_str()).trim());
            let descr = caps.get(3).map_or("", |m| m.as_str()).trim().to_string();
            return Some(ParsedHeaderLine { mnemonic, unit, value: String::new(), descr });
        }
        return parse_no_period_line(trimmed);
    }

    // Try fallback (no colon)
    if let Some(caps) = NO_COLON_RE.captures(trimmed) {
        let mnemonic = caps.get(1).map_or("", |m| m.as_str()).trim().to_string();
        if !mnemonic.contains(':') {
            let unit = strip_brackets(caps.get(2).map_or("", |m| m.as_str()).trim());
            let value = caps.get(3).map_or("", |m| m.as_str()).trim().to_string();
            return Some(ParsedHeaderLine { mnemonic, unit, value, descr: String::new() });
        }
        return parse_no_period_line(trimmed);
    }

    None
}

/// Parse a header line that has no period separator.
/// Handles formats like:
///   `NAME VALUE : DESCR`
///   `NAME :VALUE`
///   `NAME : VALUE`
fn parse_no_period_line(trimmed: &str) -> Option<ParsedHeaderLine> {
    // Find the LAST ` : ` (space-colon-space) as the primary separator
    // This handles lines like "COMP  ACME CORP : COMPANY NAME"
    if let Some(sep_pos) = trimmed.rfind(" : ") {
        let before = trimmed[..sep_pos].trim();
        let after = trimmed[sep_pos+3..].trim();
        if !before.is_empty() {
            return Some(ParsedHeaderLine {
                mnemonic: before.to_string(),
                unit: String::new(),
                value: after.to_string(),
                descr: String::new(),
            });
        }
    }

    // Try simple colon split (NAME :VALUE or NAME: VALUE)
    if let Some(colon_pos) = trimmed.find(':') {
        let before = trimmed[..colon_pos].trim();
        let after = trimmed[colon_pos+1..].trim();

        if !before.is_empty() {
            return Some(ParsedHeaderLine {
                mnemonic: before.to_string(),
                unit: String::new(),
                value: after.to_string(),
                descr: String::new(),
            });
        }
    }
    None
}

/// Strip surrounding brackets/parens from unit strings: [M] → M, (GAPI) → GAPI
fn strip_brackets(unit: &str) -> String {
    let s = unit.trim();
    if (s.starts_with('[') && s.ends_with(']'))
        || (s.starts_with('(') && s.ends_with(')'))
    {
        s[1..s.len()-1].to_string()
    } else {
        s.to_string()
    }
}

/// Parse a value string into the best type: try i64, then f64, then keep as string.
/// UWI and API fields are always kept as strings.
pub fn parse_value(value_str: &str, mnemonic: &str) -> ValueType {
    let upper = mnemonic.to_uppercase();
    // UWI and API are always strings
    if upper == "UWI" || upper == "API" {
        return ValueType::Str(value_str.to_string());
    }

    let trimmed = value_str.trim();
    if trimmed.is_empty() {
        return ValueType::Str(String::new());
    }

    // Try integer
    if let Ok(i) = trimmed.parse::<i64>() {
        // Only use int if the string doesn't have a decimal point
        if !trimmed.contains('.') {
            return ValueType::Int(i);
        }
    }

    // Try float
    if let Ok(f) = trimmed.parse::<f64>() {
        return ValueType::Float(f);
    }

    ValueType::Str(value_str.to_string())
}

#[derive(Debug, Clone)]
pub enum ValueType {
    Str(String),
    Int(i64),
    Float(f64),
}
