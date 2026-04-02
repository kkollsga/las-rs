pub mod sections;
pub mod header;
pub mod data;

use crate::core::errors::LasError;
use crate::core::helpers::normalize_depth_unit;
use crate::core::las_file::LASFile;
use crate::core::types::{CurveItem, HeaderItem, ItemWrapper, SectionItems, Value};
use header::ValueType;
use sections::{SectionKind, SectionRange};

pub fn read_las(
    content: &str,
    ignore_header_errors: bool,
    mnemonic_case: Option<&str>,
    ignore_data: bool,
    null_policy: Option<data::NullPolicy>,
    read_policy: Option<String>,
    ignore_comments: &[String],
) -> Result<LASFile, LasError> {
    let lines: Vec<&str> = content.lines().collect();

    // Section discovery
    let section_ranges = sections::discover_sections(&lines);

    if section_ranges.is_empty() {
        return Err(LasError::KeyError("No ~ sections found in LAS file".to_string()));
    }

    let mut las = LASFile::create_default();
    // Clear default version items -- we'll rebuild from file
    las.version_section.items.clear();

    // Detect LAS version, WRAP, and delimiter in first pass
    let mut las_version = 2.0f64;
    let mut null_value = -999.25f64;
    let mut delimiter: Option<char> = None;
    let mut wrapped = false;

    for sec in &section_ranges {
        if sec.kind == SectionKind::Version {
            for line_idx in sec.start_line..sec.end_line {
                if let Some(parsed) = header::parse_header_line(lines[line_idx]) {
                    let upper = parsed.mnemonic.to_uppercase();
                    if upper == "VERS" {
                        if let Ok(v) = parsed.value.trim().parse::<f64>() {
                            las_version = v;
                        }
                    }
                    if upper == "WRAP" {
                        let wrap_val = parsed.value.trim().to_uppercase();
                        wrapped = wrap_val == "YES";
                    }
                    if upper == "DLM" {
                        let dlm_upper = parsed.value.trim().to_uppercase();
                        if dlm_upper == "COMMA" {
                            delimiter = Some(',');
                        } else if dlm_upper == "TAB" {
                            delimiter = Some('\t');
                        }
                    }
                }
            }
        }
    }

    let _is_v12 = las_version < 2.0;
    let effective_null_policy = null_policy.unwrap_or(data::NullPolicy::Strict);
    let mut string_col_indices: Vec<usize> = Vec::new();

    // Second pass: parse all sections
    for sec in &section_ranges {
        match &sec.kind {
            SectionKind::Version => {
                parse_header_section(&lines, sec, &mut las.version_section, false, ignore_header_errors)?;
            }
            SectionKind::Well => {
                parse_header_section(&lines, sec, &mut las.well_section, true, ignore_header_errors)?;
                // Extract NULL value
                if let Some(idx) = las.well_section.find_index_by_mnemonic("NULL") {
                    let item: &ItemWrapper = &las.well_section.items[idx];
                    let val_str = item.value().display_str();
                    if let Ok(v) = val_str.parse::<f64>() {
                        null_value = v;
                    }
                }
            }
            SectionKind::Curves => {
                let string_cols = parse_curve_section(&lines, sec, &mut las.curves_section, ignore_header_errors)?;
                // Store for data parsing
                string_col_indices = string_cols;
            }
            SectionKind::Parameter => {
                parse_header_section(&lines, sec, &mut las.params_section, true, ignore_header_errors)?;
            }
            SectionKind::Other => {
                let mut text_lines = Vec::new();
                for line_idx in sec.start_line..sec.end_line {
                    text_lines.push(lines[line_idx]);
                }
                las.other_section = text_lines.join("\n");
            }
            SectionKind::Data => {
                if !ignore_data {
                    let data_lines: Vec<&str> = (sec.start_line..sec.end_line)
                        .map(|i| lines[i])
                        .collect();
                    let n_curves = las.curves_section.items.len();

                    if !string_col_indices.is_empty() {
                        // Parse with string column support
                        let (float_cols, str_cols) = data::parse_data_section_with_strings(
                            &data_lines, n_curves, null_value, delimiter,
                            &string_col_indices,
                        );
                        assign_data_to_curves(&mut las.curves_section, float_cols, n_curves);
                        // Assign string data to string columns
                        for (&col_idx, strings) in &str_cols {
                            if col_idx < las.curves_section.items.len() {
                                if let ItemWrapper::Curve(ref mut c) = las.curves_section.items[col_idx] {
                                    c.string_data = Some(strings.clone());
                                }
                            }
                        }
                    } else {
                        let parsed = data::parse_data_section_with_policy(
                            &data_lines, n_curves, null_value, delimiter,
                            wrapped, &effective_null_policy,
                            read_policy.as_deref(), ignore_comments,
                        );
                        assign_data_to_curves(&mut las.curves_section, parsed.float_columns, n_curves);
                        // Assign auto-detected string data to curves
                        for (&col_idx, strings) in &parsed.string_columns {
                            if col_idx < las.curves_section.items.len() {
                                if let ItemWrapper::Curve(ref mut c) = las.curves_section.items[col_idx] {
                                    c.string_data = Some(strings.clone());
                                }
                            }
                        }
                    }
                }
            }
            SectionKind::Custom(title) => {
                let mut custom_sec = SectionItems {
                    items: Vec::new(),
                    mnemonic_transforms: true,
                };
                parse_header_section(&lines, sec, &mut custom_sec, false, ignore_header_errors)?;
                las.custom_sections.insert(title.clone(), custom_sec);
            }
        }
    }

    // Apply mnemonic_case transformation
    if let Some(case) = mnemonic_case {
        apply_mnemonic_case(&mut las, case);
    }

    // Detect index unit
    las.index_unit = detect_index_unit(&las);

    Ok(las)
}

pub fn parse_header_section(
    lines: &[&str],
    sec: &SectionRange,
    section: &mut SectionItems,
    parse_numeric_values: bool,
    ignore_header_errors: bool,
) -> Result<(), LasError> {
    for line_idx in sec.start_line..sec.end_line {
        let line = lines[line_idx];
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        match header::parse_header_line(line) {
            Some(parsed) => {
                let value = if parse_numeric_values {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                } else {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                };

                let mnemonic = if parsed.mnemonic.is_empty() {
                    "UNKNOWN".to_string()
                } else {
                    parsed.mnemonic
                };

                let item = HeaderItem {
                    original_mnemonic: mnemonic.clone(),
                    session_mnemonic: mnemonic.clone(),
                    unit: parsed.unit,
                    value,
                    descr: parsed.descr,
                    data: Value::Str(String::new()),
                };
                let orig = item.original_mnemonic.clone();
                section.items.push(ItemWrapper::Header(item));
                section.assign_duplicate_suffixes_for(&orig);
            }
            None => {
                if !ignore_header_errors && !trimmed.is_empty() && !trimmed.starts_with('#') {
                    return Err(LasError::Header(format!(
                        "Failed to parse header line: {}", trimmed
                    )));
                }
            }
        }
    }
    Ok(())
}

pub fn parse_curve_section(
    lines: &[&str],
    sec: &SectionRange,
    section: &mut SectionItems,
    ignore_header_errors: bool,
) -> Result<Vec<usize>, LasError> {
    let mut string_col_indices = Vec::new();
    let mut curve_idx = 0usize;
    for line_idx in sec.start_line..sec.end_line {
        let line = lines[line_idx];
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        match header::parse_header_line(line) {
            Some(parsed) => {
                // Check for {S} format code indicating string column
                let is_string_col = parsed.value.contains("{S}") || parsed.descr.contains("{S}");
                let value_clean = if is_string_col {
                    let v = parsed.value.replace("{S}", "").trim().to_string();
                    match header::parse_value(&v, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                } else {
                    match header::parse_value(&parsed.value, &parsed.mnemonic) {
                        ValueType::Int(i) => Value::Int(i),
                        ValueType::Float(f) => Value::Float(f),
                        ValueType::Str(s) => Value::Str(s),
                    }
                };

                if is_string_col {
                    string_col_indices.push(curve_idx);
                }

                let mnemonic = if parsed.mnemonic.is_empty() {
                    "UNKNOWN".to_string()
                } else {
                    parsed.mnemonic
                };

                let item = CurveItem {
                    header: HeaderItem {
                        original_mnemonic: mnemonic.clone(),
                        session_mnemonic: mnemonic.clone(),
                        unit: parsed.unit,
                        value: value_clean,
                        descr: parsed.descr.replace("{S}", "").trim().to_string(),
                        data: Value::Str(String::new()),
                    },
                    curve_data: Vec::new(),
                    string_data: None,
                    dtype_override: None,
                };
                let orig = item.header.original_mnemonic.clone();
                section.items.push(ItemWrapper::Curve(item));
                section.assign_duplicate_suffixes_for(&orig);
                curve_idx += 1;
            }
            None => {
                if !ignore_header_errors {
                    // skip
                }
            }
        }
    }
    Ok(string_col_indices)
}

pub fn assign_data_to_curves(curves_section: &mut SectionItems, mut columns: Vec<Vec<f64>>, n_declared: usize) {
    let n_data_cols = columns.len();
    let n_rows = if columns.is_empty() { 0 } else { columns[0].len() };

    // Assign data to declared curves -- move ownership, no clone
    for (i, item) in curves_section.items.iter_mut().enumerate() {
        if let ItemWrapper::Curve(ref mut c) = item {
            if i < n_data_cols {
                c.curve_data = std::mem::take(&mut columns[i]);
            } else {
                c.curve_data = vec![f64::NAN; n_rows];
            }
        }
    }

    // Handle excess data columns
    if n_data_cols > n_declared {
        for col_idx in n_declared..n_data_cols {
            let mnemonic = format!("UNKNOWN_{}", col_idx - n_declared + 1);
            let item = CurveItem {
                header: HeaderItem {
                    original_mnemonic: mnemonic.clone(),
                    session_mnemonic: mnemonic,
                    unit: String::new(),
                    value: Value::Str(String::new()),
                    descr: format!("Auto-generated from excess data column {}", col_idx),
                    data: Value::Str(String::new()),
                },
                curve_data: std::mem::take(&mut columns[col_idx]),
                string_data: None,
                dtype_override: None,
            };
            curves_section.items.push(ItemWrapper::Curve(item));
        }
    }
}

pub fn detect_index_unit(las: &LASFile) -> Option<String> {
    // Get STRT unit
    let strt_unit = las.well_section.find_index_by_mnemonic("STRT")
        .and_then(|idx| {
            let item: &ItemWrapper = &las.well_section.items[idx];
            let unit = item.unit();
            if unit.is_empty() { None } else { normalize_depth_unit(unit) }
        });

    // Get first curve unit
    let curve_unit = las.curves_section.items.first()
        .and_then(|item| {
            let unit = item.unit();
            if unit.is_empty() { None } else { normalize_depth_unit(unit) }
        });

    // If both are present and disagree, return None (inconsistent)
    match (&strt_unit, &curve_unit) {
        (Some(s), Some(c)) if s != c => None,
        (Some(s), _) => Some(s.clone()),
        (_, Some(c)) => Some(c.clone()),
        _ => None,
    }
}

pub fn apply_mnemonic_case(las: &mut LASFile, case: &str) {
    let transform = |name: &str| -> String {
        match case {
            "upper" => name.to_uppercase(),
            "lower" => name.to_lowercase(),
            _ => name.to_string(), // "preserve" or unknown
        }
    };

    for section in [
        &mut las.version_section,
        &mut las.well_section,
        &mut las.curves_section,
        &mut las.params_section,
    ] {
        for item in &mut section.items {
            let new_orig = transform(item.original_mnemonic());
            let new_sess = transform(item.session_mnemonic());
            match item {
                ItemWrapper::Header(h) => {
                    h.original_mnemonic = new_orig;
                    h.session_mnemonic = new_sess;
                }
                ItemWrapper::Curve(c) => {
                    c.header.original_mnemonic = new_orig;
                    c.header.session_mnemonic = new_sess;
                }
            }
        }
    }
}
