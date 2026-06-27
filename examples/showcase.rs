//! Runnable demonstration of the pure-Rust `las_rs` API.
//!
//! Run against a bundled fixture:
//!
//! ```text
//! cargo run --example showcase
//! ```
//!
//! Or point it at your own file:
//!
//! ```text
//! cargo run --example showcase -- path/to/welllog.las
//! ```

use las_rs::{read_file, LasError};

fn main() -> Result<(), LasError> {
    let path = std::env::args().nth(1).unwrap_or_else(|| {
        format!("{}/tests/fixtures/v20/sample_v20.las", env!("CARGO_MANIFEST_DIR"))
    });

    println!("Reading {path}\n");
    let las = read_file(&path)?;

    // ---- Header metadata --------------------------------------------------
    println!("Well:        {}", las.well_value("WELL").unwrap_or_else(|| "<none>".into()));
    println!("Field:       {}", las.well_value("FLD").unwrap_or_else(|| "<none>".into()));
    println!("Service co.: {}", las.well_value("SRVC").unwrap_or_else(|| "<none>".into()));
    println!("Index unit:  {}", las.index_unit.as_deref().unwrap_or("<unknown>"));
    if let Some(enc) = &las.encoding {
        println!("Encoding:    {enc}");
    }

    // ---- Depth range ------------------------------------------------------
    if let Some(depth) = las.index() {
        if let (Some(first), Some(last)) = (depth.first(), depth.last()) {
            println!("Depth:       {first} -> {last}  ({} samples)", depth.len());
        }
    }

    // ---- Per-curve summary ------------------------------------------------
    println!("\nCurves:");
    for name in las.curve_mnemonics() {
        let curve = las.get_curve(name).unwrap();
        let data = &curve.curve_data;
        let nulls = data.iter().filter(|v| v.is_nan()).count();
        let finite: Vec<f64> = data.iter().copied().filter(|v| v.is_finite()).collect();
        let (min, max) = finite.iter().fold((f64::INFINITY, f64::NEG_INFINITY), |(lo, hi), &v| {
            (lo.min(v), hi.max(v))
        });
        let range = if finite.is_empty() {
            "no numeric data".to_string()
        } else {
            format!("min {min:.3}, max {max:.3}")
        };
        println!(
            "  {:<6} [{:<6}] {:<24} {} samples, {} null  ({range})",
            name,
            curve.header.unit,
            curve.header.descr,
            data.len(),
            nulls,
        );
    }

    // ---- Round-trip back to LAS text -------------------------------------
    let text = las.to_las_string()?;
    println!("\nSerialized back to {} bytes of LAS text.", text.len());

    Ok(())
}
