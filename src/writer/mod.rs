use std::collections::HashMap;

use crate::core::errors::LasError;
use crate::core::las_file::LASFile;
use crate::core::types::ItemWrapper;

pub fn format_las(
    las: &LASFile,
    version_override: Option<f64>,
    wrap_override: Option<bool>,
    mnemonics_header: bool,
    fmt: Option<&str>,
    data_section_header: Option<&str>,
    lhs_spacer: &str,
    spacer: &str,
    len_numeric_field: Option<i32>,
    column_fmt: &HashMap<usize, String>,
    step_override: Option<f64>,
    strt_override: Option<f64>,
    stop_override: Option<f64>,
) -> Result<String, LasError> {
    // Pre-allocate buffer based on estimated output size
    let n_curves = las.curves_section.items.len();
    let n_rows = las.curves_section.items.first()
        .and_then(|item| if let ItemWrapper::Curve(c) = item { Some(c.curve_data.len()) } else { None })
        .unwrap_or(0);
    let estimated = 2000 + n_rows * n_curves * 15; // header + data
    let mut out = String::with_capacity(estimated);

    let fmt_str = fmt.unwrap_or("%.5f");
    let precision = parse_fmt_precision(fmt_str);

    // Get NULL value
    let null_value = las.well_section.find_index_by_mnemonic("NULL")
        .map(|idx| {
            let item: &ItemWrapper = &las.well_section.items[idx];
            item.value().display_str().parse::<f64>().unwrap_or(-999.25)
        })
        .unwrap_or(-999.25);

    // Determine version for output
    let write_version = match version_override {
        Some(v) => v,
        None => {
            match las.version_section.find_index_by_mnemonic("VERS") {
                Some(idx) => {
                    let item: &ItemWrapper = &las.version_section.items[idx];
                    item.value().display_str().parse::<f64>().unwrap_or(2.0)
                }
                None => {
                    return Err(LasError::Header(
                        "Cannot write: VERS item missing from version section and no version override specified".to_string()
                    ));
                }
            }
        }
    };

    // Validate WRAP exists if no override
    if wrap_override.is_none() && las.version_section.find_index_by_mnemonic("WRAP").is_none() {
        return Err(LasError::Header(
            "Cannot write: WRAP item missing from version section and no wrap override specified".to_string()
        ));
    }

    // ~Version
    out.push_str("~Version ---------------------------------------------------\n");
    if version_override.is_some() {
        // Write overridden version
        out.push_str(&format!("VERS.   {:.1} : CWLS LOG ASCII STANDARD - VERSION {:.1}\n", write_version, write_version));
    } else {
        for item in &las.version_section.items {
            if item.original_mnemonic().to_uppercase() == "VERS" && version_override.is_some() {
                continue; // skip, already written
            }
            write_header_item(&mut out, item);
        }
    }
    if version_override.is_some() {
        // Also write WRAP
        for item in &las.version_section.items {
            if item.original_mnemonic().to_uppercase() != "VERS" {
                write_header_item(&mut out, item);
            }
        }
    }

    // ~Well -- apply STRT/STOP/STEP overrides and auto-sync units from index curve
    out.push_str("~Well ------------------------------------------------------\n");
    // Get actual depth range and unit from index curve
    let (actual_stop, index_unit) = las.curves_section.items.first()
        .map(|item| {
            if let ItemWrapper::Curve(c) = item {
                (c.curve_data.last().copied(), c.header.unit.clone())
            } else { (None, String::new()) }
        })
        .unwrap_or((None, String::new()));
    for item in &las.well_section.items {
        let mnem_upper = item.original_mnemonic().to_uppercase();
        // For STRT/STOP/STEP: use index curve's unit if available
        let effective_unit = if matches!(mnem_upper.as_str(), "STRT" | "STOP" | "STEP") && !index_unit.is_empty() {
            &index_unit
        } else {
            item.unit()
        };
        if mnem_upper == "STRT" && strt_override.is_some() {
            out.push_str(&format!(" {}.{}  {} : {}\n",
                item.original_mnemonic(), effective_unit,
                format!("{:.5}", strt_override.unwrap()), item.descr()));
        } else if mnem_upper == "STOP" {
            let stop_val = stop_override.or(actual_stop);
            if let Some(sv) = stop_val {
                out.push_str(&format!(" {}.{}  {} : {}\n",
                    item.original_mnemonic(), effective_unit,
                    format!("{:.5}", sv), item.descr()));
            } else {
                write_header_item(&mut out, item);
            }
        } else if mnem_upper == "STEP" && step_override.is_some() {
            out.push_str(&format!(" {}.{}  {} : {}\n",
                item.original_mnemonic(), effective_unit,
                format!("{:.5}", step_override.unwrap()), item.descr()));
        } else if matches!(mnem_upper.as_str(), "STRT" | "STOP" | "STEP") {
            // Auto-sync unit from index curve
            out.push_str(&format!(" {}.{}  {} : {}\n",
                item.original_mnemonic(), effective_unit,
                item.value().display_str(), item.descr()));
        } else {
            write_header_item(&mut out, item);
        }
    }

    // ~Curves
    out.push_str("~Curves ----------------------------------------------------\n");
    for item in &las.curves_section.items {
        write_header_item(&mut out, item);
    }

    // ~Params (if any)
    if !las.params_section.items.is_empty() {
        out.push_str("~Params ----------------------------------------------------\n");
        for item in &las.params_section.items {
            write_header_item(&mut out, item);
        }
    }

    // ~Other (if any)
    if !las.other_section.trim().is_empty() {
        out.push_str("~Other -----------------------------------------------------\n");
        out.push_str(&las.other_section);
        if !las.other_section.ends_with('\n') {
            out.push('\n');
        }
    }

    // ~ASCII
    let header = data_section_header.unwrap_or("~ASCII -----------------------------------------------------");
    out.push_str(header);
    out.push('\n');

    if mnemonics_header {
        // Write curve names as a comment line
        let names: Vec<&str> = las.curves_section.items.iter()
            .map(|item| item.original_mnemonic())
            .collect();
        out.push_str(&format!(" {}\n", names.join("        ")));
    }

    // Write data
    let n_curves = las.curves_section.items.len();
    if n_curves > 0 {
        let n_rows = match &las.curves_section.items[0] {
            ItemWrapper::Curve(c) => c.curve_data.len(),
            _ => 0,
        };

        let should_wrap = wrap_override.unwrap_or(false);

        use std::fmt::Write;

        // Pre-compute per-column precision
        let col_precs: Vec<usize> = (0..n_curves)
            .map(|i| column_fmt.get(&i).map(|cf| parse_fmt_precision(cf)).unwrap_or(precision))
            .collect();

        for row_idx in 0..n_rows {
            if should_wrap {
                // Wrapped mode -- still uses vec approach for line-width tracking
                let mut vals = Vec::with_capacity(n_curves);
                for (col_idx, item) in las.curves_section.items.iter().enumerate() {
                    if let ItemWrapper::Curve(c) = item {
                        let v = if row_idx < c.curve_data.len() { c.curve_data[row_idx] } else { f64::NAN };
                        let prec = col_precs[col_idx.min(col_precs.len() - 1)];
                        let mut s = String::new();
                        if v.is_nan() {
                            write!(s, "{:.prec$}", null_value, prec = prec).unwrap();
                        } else {
                            write!(s, "{:.prec$}", v, prec = prec).unwrap();
                        }
                        vals.push(s);
                    }
                }
                if !vals.is_empty() {
                    write!(out, " {}\n", vals[0]).unwrap();
                    let mut line_len = 1usize;
                    out.push(' ');
                    for (i, val) in vals[1..].iter().enumerate() {
                        if line_len + val.len() + 2 > 79 && i > 0 {
                            out.push('\n');
                            out.push(' ');
                            line_len = 1;
                        }
                        out.push_str(val);
                        line_len += val.len();
                        if i < vals.len() - 2 {
                            out.push_str("  ");
                            line_len += 2;
                        }
                    }
                    out.push('\n');
                }
            } else {
                // Unwrapped mode -- write directly to buffer, zero intermediate allocations
                out.push_str(lhs_spacer);
                let mut first = true;
                for (col_idx, item) in las.curves_section.items.iter().enumerate() {
                    if let ItemWrapper::Curve(c) = item {
                        if !first { out.push_str(spacer); }
                        first = false;
                        let v = if row_idx < c.curve_data.len() { c.curve_data[row_idx] } else { f64::NAN };
                        let prec = col_precs[col_idx.min(col_precs.len() - 1)];
                        match len_numeric_field {
                            Some(w) if w > 0 => {
                                // Padded: need intermediate string for width
                                let mut tmp = String::new();
                                if v.is_nan() {
                                    write!(tmp, "{:.prec$}", null_value, prec = prec).unwrap();
                                } else {
                                    write!(tmp, "{:.prec$}", v, prec = prec).unwrap();
                                }
                                write!(out, "{:>width$}", tmp, width = w as usize).unwrap();
                            }
                            _ => {
                                if v.is_nan() {
                                    write!(out, "{:.prec$}", null_value, prec = prec).unwrap();
                                } else {
                                    write!(out, "{:.prec$}", v, prec = prec).unwrap();
                                }
                            }
                        }
                    }
                }
                out.push('\n');
            }
        }
    }

    Ok(out)
}

pub fn format_csv(
    las: &LASFile,
    mnemonics: Option<&[String]>,
    units: Option<&[String]>,
    units_loc: Option<&str>,
    lineterminator: &str,
    no_units: bool,
) -> Result<String, LasError> {
    let mut out = String::new();

    // Determine column names
    let default_names: Vec<String> = las.curves_section.items.iter()
        .map(|item| item.original_mnemonic().to_string())
        .collect();

    let col_names: Vec<String> = match mnemonics {
        Some(m) => m.to_vec(),
        None => default_names.clone(),
    };

    // Get units
    let curve_units: Vec<String> = las.curves_section.items.iter()
        .map(|item| item.unit().to_string())
        .collect();

    let unit_strings: Vec<String> = if no_units {
        vec![]
    } else {
        match units {
            Some(u) => u.to_vec(),
            None => curve_units.clone(),
        }
    };

    // Build header based on units_loc
    match units_loc {
        Some("[]") => {
            let headers: Vec<String> = col_names.iter().enumerate().map(|(i, name)| {
                if i < unit_strings.len() && !unit_strings[i].is_empty() {
                    format!("{}[{}]", name, unit_strings[i])
                } else {
                    name.clone()
                }
            }).collect();
            out.push_str(&headers.join(","));
            out.push_str(lineterminator);
        }
        Some("()") => {
            let headers: Vec<String> = col_names.iter().enumerate().map(|(i, name)| {
                if i < unit_strings.len() && !unit_strings[i].is_empty() {
                    format!("{}({})", name, unit_strings[i])
                } else {
                    name.clone()
                }
            }).collect();
            out.push_str(&headers.join(","));
            out.push_str(lineterminator);
        }
        Some("line") => {
            // Mnemonic header
            out.push_str(&col_names.join(","));
            out.push_str(lineterminator);
            // Unit header
            out.push_str(&unit_strings.join(","));
            out.push_str(lineterminator);
        }
        _ => {
            // Default: just mnemonics
            out.push_str(&col_names.join(","));
            out.push_str(lineterminator);
        }
    }

    // Data rows — write directly to buffer, zero intermediate allocations
    use std::fmt::Write;
    let n_curves = las.curves_section.items.len();
    if n_curves > 0 {
        let n_rows = match &las.curves_section.items[0] {
            ItemWrapper::Curve(c) => c.curve_data.len(),
            _ => 0,
        };
        // Pre-allocate for data
        out.reserve(n_rows * n_curves * 12);
        for row_idx in 0..n_rows {
            let mut first = true;
            for item in &las.curves_section.items {
                if let ItemWrapper::Curve(c) = item {
                    if !first { out.push(','); }
                    first = false;
                    let v = if row_idx < c.curve_data.len() {
                        c.curve_data[row_idx]
                    } else {
                        f64::NAN
                    };
                    if !v.is_nan() {
                        write!(out, "{}", v).unwrap();
                    }
                }
            }
            out.push_str(lineterminator);
        }
    }

    Ok(out)
}

pub fn write_header_item(out: &mut String, item: &ItemWrapper) {
    let mnemonic = item.original_mnemonic();
    let unit = item.unit();
    let value = item.value().display_str();
    let descr = item.descr();
    out.push_str(&format!(" {}.{}  {} : {}\n", mnemonic, unit, value, descr));
}

pub fn parse_fmt_precision(fmt: &str) -> usize {
    // Parse "%.5f" -> 5
    if let Some(start) = fmt.find('.') {
        let rest = &fmt[start + 1..];
        let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
        digits.parse::<usize>().unwrap_or(5)
    } else {
        5
    }
}
