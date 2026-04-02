pub fn natural_sort_key(s: &str) -> Vec<(bool, u64, String)> {
    let mut parts = Vec::new();
    let mut num_buf = String::new();
    let mut str_buf = String::new();

    for ch in s.chars() {
        if ch.is_ascii_digit() {
            if !str_buf.is_empty() {
                parts.push((false, 0u64, str_buf.clone()));
                str_buf.clear();
            }
            num_buf.push(ch);
        } else {
            if !num_buf.is_empty() {
                let n = num_buf.parse::<u64>().unwrap_or(0);
                parts.push((true, n, String::new()));
                num_buf.clear();
            }
            str_buf.push(ch);
        }
    }
    if !num_buf.is_empty() {
        let n = num_buf.parse::<u64>().unwrap_or(0);
        parts.push((true, n, String::new()));
    }
    if !str_buf.is_empty() {
        parts.push((false, 0, str_buf));
    }
    parts
}

pub fn normalize_depth_unit(unit: &str) -> Option<String> {
    let upper = unit.to_uppercase().trim().to_string();
    match upper.as_str() {
        "FT" | "F" | "FEET" | "FOOT" => Some("FT".to_string()),
        "M" | "METER" | "METERS" | "METRES" | "METRE" | "\u{043C}" => Some("M".to_string()),
        ".1IN" | "0.1IN" => Some(".1IN".to_string()),
        _ => None, // Unknown unit
    }
}
