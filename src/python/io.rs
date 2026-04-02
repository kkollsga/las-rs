use pyo3::exceptions::PyIOError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::core::las_file::LASFile;
use crate::core::types::ItemWrapper;
use crate::python::conversions::{kwarg_opt_string, kwarg_string};
use crate::reader;
use crate::reader::data;

/// Python-facing read function
pub fn py_read(py: Python<'_>, source: &Bound<'_, PyAny>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<LASFile> {
    let ignore_header_errors = kwargs
        .and_then(|kw| kw.get_item("ignore_header_errors").ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(false);

    let mnemonic_case = kwargs
        .and_then(|kw| kw.get_item("mnemonic_case").ok().flatten())
        .and_then(|v| v.extract::<String>().ok());

    let ignore_data = kwargs
        .and_then(|kw| kw.get_item("ignore_data").ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(false);

    let null_policy = kwargs
        .and_then(|kw| kw.get_item("null_policy").ok().flatten())
        .map(|v| {
            // Check if it's a pure float list
            if let Ok(values) = v.extract::<Vec<f64>>() {
                return data::NullPolicy::Custom(values);
            }
            // Check if it's a string policy name
            if let Ok(s) = v.extract::<String>() {
                return data::NullPolicy::from_str_or_list(&s);
            }
            // Try as mixed list (strings + numbers)
            if let Ok(seq) = v.try_iter() {
                let mut floats = Vec::new();
                let mut strings = Vec::new();
                for item in seq {
                    if let Ok(item) = item {
                        if let Ok(f) = item.extract::<f64>() {
                            floats.push(f);
                        } else if let Ok(s) = item.extract::<String>() {
                            strings.push(s);
                        }
                    }
                }
                if !floats.is_empty() || !strings.is_empty() {
                    return data::NullPolicy::CustomMixed { floats, strings };
                }
            }
            data::NullPolicy::Strict
        });

    let read_policy_raw = kwargs
        .and_then(|kw| kw.get_item("read_policy").ok().flatten());
    let read_policy = if let Some(ref rp) = read_policy_raw {
        if let Ok(s) = rp.extract::<String>() {
            Some(s)
        } else {
            // Empty tuple/list = no policies
            None
        }
    } else {
        // Default: apply comma-decimal-mark substitution
        Some("comma-decimal-mark".to_string())
    };

    let ignore_comments = kwargs
        .and_then(|kw| kw.get_item("ignore_comments").ok().flatten())
        .map(|v| {
            // Try Vec<String> first (works for both lists and tuples)
            if let Ok(list) = v.extract::<Vec<String>>() {
                return list;
            }
            if let Ok(s) = v.extract::<String>() {
                return vec![s];
            }
            vec!["#".to_string()]
        })
        .unwrap_or_else(|| vec!["#".to_string()]);

    let index_unit_override = kwarg_opt_string(kwargs, "index_unit");
    let encoding = kwarg_opt_string(kwargs, "encoding");
    let encoding_errors = kwarg_string(kwargs, "encoding_errors", "replace");

    let (content, detected_encoding) = resolve_source(py, source, encoding.as_deref(), &encoding_errors)?;

    // Release the GIL during parsing -- read_las is pure Rust, no Python objects
    let mut las = py.detach(|| {
        reader::read_las(&content, ignore_header_errors, mnemonic_case.as_deref(), ignore_data, null_policy, read_policy, &ignore_comments)
    })?;
    las.encoding = detected_encoding;

    // Apply index_unit override -- also update curve and well units
    if let Some(ref unit) = index_unit_override {
        las.index_unit = Some(unit.clone());
        // Update first curve's unit
        if let Some(ItemWrapper::Curve(ref mut c)) = las.curves_section.items.first_mut() {
            c.header.unit = unit.clone();
        }
        // Update STRT/STOP/STEP units
        for name in &["STRT", "STOP", "STEP"] {
            if let Some(idx) = las.well_section.find_index_by_mnemonic(name) {
                if let ItemWrapper::Header(ref mut h) = las.well_section.items[idx] {
                    h.unit = unit.clone();
                }
            }
        }
    }

    // Apply dtypes kwarg
    let dtypes_raw = kwargs.and_then(|kw| kw.get_item("dtypes").ok().flatten());
    if let Some(ref dt) = dtypes_raw {
        if let Ok(false_val) = dt.extract::<bool>() {
            if !false_val {
                // dtypes=False -> store all curve data as strings
                for item in &mut las.curves_section.items {
                    if let ItemWrapper::Curve(ref mut c) = item {
                        if c.string_data.is_none() {
                            let strings: Vec<String> = c.curve_data.iter()
                                .map(|v| if v.is_nan() { String::new() } else { format!("{}", v) })
                                .collect();
                            c.string_data = Some(strings);
                        }
                    }
                }
            }
        } else if let Ok(dict) = dt.cast::<PyDict>() {
            // dtypes={"GR": int} -> set dtype override on specific curves
            for (key, dtype_obj) in dict.iter() {
                let name: String = key.extract()?;
                if let Some(idx) = las.curves_section.find_index_by_mnemonic(&name) {
                    if let ItemWrapper::Curve(ref mut c) = las.curves_section.items[idx] {
                        let type_name = dtype_obj.str().map(|s| s.to_string()).unwrap_or_default();
                        if type_name.contains("int") {
                            c.dtype_override = Some("int".to_string());
                        }
                    }
                }
            }
        }
    }

    Ok(las)
}

pub fn resolve_source(_py: Python<'_>, source: &Bound<'_, PyAny>, encoding: Option<&str>, encoding_errors: &str) -> PyResult<(String, Option<String>)> {
    // Check if it's a string
    if let Ok(s) = source.extract::<String>() {
        // Multi-line string (LAS content)?
        if s.contains('\n') {
            return Ok((s, None));
        }
        // Single line -- treat as filename
        // Check for LiDAR guard
        let path = std::path::Path::new(&s);
        if !path.exists() {
            return Err(PyIOError::new_err(format!("File not found: {}", s)));
        }
        let bytes = std::fs::read(&s)
            .map_err(|e| PyIOError::new_err(format!("Cannot read file: {}: {}", s, e)))?;

        // LiDAR guard: first 4 bytes == "LASF"
        if bytes.len() >= 4 && &bytes[0..4] == b"LASF" {
            return Err(PyIOError::new_err(
                "This is a LiDAR LAS file (binary), not a Log ASCII Standard file"
            ));
        }

        // Try to decode
        return decode_bytes(&bytes, encoding, encoding_errors);
    }

    // Check for pathlib.Path
    if let Ok(path_str) = source.call_method0("__fspath__") {
        if let Ok(s) = path_str.extract::<String>() {
            let bytes = std::fs::read(&s)
                .map_err(|e| PyIOError::new_err(format!("Cannot read file: {}: {}", s, e)))?;
            return decode_bytes(&bytes, encoding, encoding_errors);
        }
    }

    // File-like object: call .read()
    if let Ok(content) = source.call_method0("read") {
        if let Ok(s) = content.extract::<String>() {
            return Ok((s, None));
        }
        if let Ok(b) = content.extract::<Vec<u8>>() {
            return decode_bytes(&b, encoding, encoding_errors);
        }
    }

    Err(PyIOError::new_err("Cannot read from source: expected filename, string, or file-like object"))
}

pub fn decode_bytes(bytes: &[u8], encoding: Option<&str>, encoding_errors: &str) -> PyResult<(String, Option<String>)> {
    // If explicit encoding specified, use it
    if let Some(enc) = encoding {
        let enc_upper = enc.to_uppercase();
        // Normalize common aliases
        let enc_normalized = match enc_upper.as_str() {
            "LATIN-1" | "LATIN1" | "ISO-8859-1" | "ISO8859-1" => "WINDOWS-1252",
            "UTF-8-SIG" => "UTF-8",
            other => other,
        };
        let (content, enc_name) = match enc_normalized {
            "UTF-16-LE" | "UTF16-LE" => {
                let (cow, _, had_errors) = encoding_rs::UTF_16LE.decode(bytes);
                if encoding_errors == "strict" && had_errors {
                    return Err(pyo3::exceptions::PyUnicodeDecodeError::new_err(
                        format!("'{}' codec can't decode bytes", enc)
                    ));
                }
                (cow.to_string(), enc.to_string())
            }
            "UTF-16-BE" | "UTF16-BE" => {
                let (cow, _, had_errors) = encoding_rs::UTF_16BE.decode(bytes);
                if encoding_errors == "strict" && had_errors {
                    return Err(pyo3::exceptions::PyUnicodeDecodeError::new_err(
                        format!("'{}' codec can't decode bytes", enc)
                    ));
                }
                (cow.to_string(), enc.to_string())
            }
            "UTF-8" | "UTF8" => {
                if encoding_errors == "strict" {
                    match std::str::from_utf8(bytes) {
                        Ok(s) => (s.to_string(), "utf-8".to_string()),
                        Err(e) => {
                            return Err(pyo3::exceptions::PyUnicodeDecodeError::new_err(
                                format!("'utf-8' codec can't decode byte 0x{:02x} in position {}: invalid continuation byte",
                                    bytes.get(e.valid_up_to()).copied().unwrap_or(0),
                                    e.valid_up_to())
                            ));
                        }
                    }
                } else {
                    (String::from_utf8_lossy(bytes).to_string(), "utf-8".to_string())
                }
            }
            _ => {
                // Try encoding_rs for other encodings
                let label = enc_normalized.to_lowercase();
                if let Some(encoder) = encoding_rs::Encoding::for_label(label.as_bytes()) {
                    let (cow, _, had_errors) = encoder.decode(bytes);
                    if encoding_errors == "strict" && had_errors {
                        return Err(pyo3::exceptions::PyUnicodeDecodeError::new_err(
                            format!("'{}' codec can't decode bytes", enc)
                        ));
                    }
                    (cow.to_string(), enc.to_string())
                } else {
                    return Err(PyIOError::new_err(format!("Unknown encoding: {}", enc)));
                }
            }
        };
        return Ok((content, Some(enc_name)));
    }

    // Auto-detect: BOM detection
    if bytes.starts_with(b"\xEF\xBB\xBF") {
        return Ok((String::from_utf8_lossy(&bytes[3..]).to_string(), Some("utf-8-sig".to_string())));
    }
    if bytes.starts_with(b"\xFF\xFE") {
        let (cow, _, _) = encoding_rs::UTF_16LE.decode(bytes);
        return Ok((cow.to_string(), Some("utf-16-le".to_string())));
    }
    if bytes.starts_with(b"\xFE\xFF") {
        let (cow, _, _) = encoding_rs::UTF_16BE.decode(bytes);
        return Ok((cow.to_string(), Some("utf-16-be".to_string())));
    }

    // Try UTF-8 first
    if encoding_errors == "strict" {
        if let Ok(s) = std::str::from_utf8(bytes) {
            return Ok((s.to_string(), Some("utf-8".to_string())));
        }
        return Err(pyo3::exceptions::PyUnicodeDecodeError::new_err(
            "'utf-8' codec can't decode bytes: invalid byte sequence"
        ));
    }

    if let Ok(s) = std::str::from_utf8(bytes) {
        return Ok((s.to_string(), Some("utf-8".to_string())));
    }

    // Fall back to Windows-1252
    let (cow, _, _) = encoding_rs::WINDOWS_1252.decode(bytes);
    Ok((cow.to_string(), Some("windows-1252".to_string())))
}
