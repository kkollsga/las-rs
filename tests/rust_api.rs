//! Thorough integration test for the pure-Rust `las_rs` API.
//!
//! Exercises the crates.io-facing surface (`read_file`, `parse`, `parse_with`,
//! `ReadOptions`, `NullPolicy`, and the `LASFile` accessors / writers) against
//! the real fixture LAS files, with the `python` feature OFF — i.e. exactly
//! what a Rust consumer gets from `cargo add las_rs`.
//!
//! Run with: `cargo test --test rust_api`

use std::path::PathBuf;

use las_rs::{parse, parse_with, read_file, read_file_with, LASFile, NullPolicy, ReadOptions};

/// Absolute path to a file under `tests/fixtures/`.
fn fixture(rel: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures").join(rel)
}

/// A scratch path unique to this process, under the OS temp dir.
fn scratch(name: &str) -> PathBuf {
    std::env::temp_dir().join(format!("las_rs_test_{}_{}", std::process::id(), name))
}

// ---------------------------------------------------------------------------
// Reading real fixtures across LAS versions
// ---------------------------------------------------------------------------

#[test]
fn reads_v12_fixture() {
    let las = read_file(fixture("v12/sample_v12.las")).expect("v1.2 should parse");

    assert_eq!(las.well_value("WELL").as_deref(), Some("GAMMA-7 #3"));
    assert_eq!(las.index_unit.as_deref(), Some("M"));

    // First (index) curve is depth; four curves declared.
    let mnemonics = las.curve_mnemonics();
    assert_eq!(mnemonics, vec!["DEPT", "GR", "NPHI", "RHOB"]);

    let depth = las.index().expect("has an index curve");
    assert_eq!(depth.len(), 6);
    assert_eq!(depth[0], 500.0);
    assert_eq!(depth[5], 502.5);

    let gr = las.curve_data("GR").expect("has GR");
    assert_eq!(gr.len(), 6);
    assert!((gr[0] - 34.2150).abs() < 1e-9, "GR[0] = {}", gr[0]);

    // Case-insensitive curve lookup.
    assert!(las.curve_data("gr").is_some());
    assert!(las.get_curve("RHOB").is_some());
    assert!(las.curve_data("NOPE").is_none());
}

#[test]
fn reads_v20_fixture() {
    let las = read_file(fixture("v20/sample_v20.las")).expect("v2.0 should parse");

    assert_eq!(las.well_value("WELL").as_deref(), Some("DEEP HORIZON #1"));
    assert_eq!(las.index_unit.as_deref(), Some("FT"));
    assert_eq!(las.curve_mnemonics(), vec!["DEPT", "DT", "GR", "CALI", "SP"]);

    let sp = las.curve_data("SP").expect("has SP");
    assert_eq!(sp.len(), 6);
    assert!((sp[0] - (-58.76)).abs() < 1e-9, "SP[0] = {}", sp[0]);
}

#[test]
fn reads_v30_comma_delimited_with_string_column() {
    let las = read_file(fixture("v30/sample_v30.las")).expect("v3.0 should parse");

    assert_eq!(las.well_value("WELL").as_deref(), Some("THORNFIELD-6"));
    assert_eq!(las.index_unit.as_deref(), Some("M"));

    let depth = las.index().expect("has an index curve");
    assert_eq!(depth[0], 1450.0);

    // The LITH column carries string data ("SANDSTONE", ...).
    let lith = las.get_curve("LITH").expect("has LITH curve");
    assert!(
        lith.string_data.is_some(),
        "LITH should retain string data for a {{S}}-typed column",
    );
}

#[test]
fn reads_v30_curve_definition_section_titles() {
    // A 3.0 file whose primary dataset uses the ~Curve_Definition /
    // ~Curve_Parameter / ~Curve_ASCII_Standard titles (Petrel core-log exports)
    // instead of ~Log_*. Regression: these used to fall through to a Custom
    // section, so curves came back empty.
    let las = read_file(fixture("v30/sample_v30_curvedef.las")).expect("v3.0 curve-def should parse");

    assert_eq!(las.curve_mnemonics(), vec!["DEPT", "GR", "RHOB", "NPHI"]);

    let depth = las.index().expect("has an index curve");
    assert_eq!(depth[0], 1450.0);

    let gr = las.curve_data("GR").expect("has GR");
    assert!((gr[1] - 78.645).abs() < 1e-9, "GR[1] = {}", gr[1]);
}

#[test]
fn reads_v30_comma_delimited_all_numeric() {
    // A comma-delimited 3.0 file with NO string column. Regression for the
    // comma-decimal-mark read policy fusing comma-separated columns
    // (`1450.0,55.231` -> `1450.055.231`) when comma is the field delimiter,
    // which silently produced all-NaN curves on the non-string-column path.
    let las = read_file(fixture("v30/sample_v30_comma_numeric.las")).expect("v3.0 comma should parse");

    assert_eq!(las.curve_mnemonics(), vec!["DEPT", "GR", "RHOB"]);

    let dept = las.index().expect("has an index curve");
    assert_eq!(dept[0], 1450.0);
    assert_eq!(dept[2], 1452.0);

    let rhob = las.curve_data("RHOB").expect("has RHOB");
    assert!((rhob[0] - 2.512).abs() < 1e-9, "RHOB[0] = {}", rhob[0]);
}

// ---------------------------------------------------------------------------
// Parsing from in-memory strings
// ---------------------------------------------------------------------------

const INLINE_LAS: &str = "\
~VERSION INFORMATION
 VERS.   2.0 : LAS VERSION 2.0
 WRAP.    NO : ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.M   10.0 : START DEPTH
 STOP.M   12.0 : STOP DEPTH
 STEP.M    1.0 : STEP VALUE
 NULL. -999.25 : NULL VALUE
 WELL.  INLINE-1 : WELL NAME
~CURVE INFORMATION
 DEPT.M    : DEPTH
 GR  .GAPI : GAMMA RAY
~ASCII
 10.0  11.1
 11.0  22.2
 12.0  33.3
";

#[test]
fn parses_inline_string() {
    let las = parse(INLINE_LAS).expect("inline LAS should parse");
    assert_eq!(las.well_value("WELL").as_deref(), Some("INLINE-1"));
    assert_eq!(las.curve_mnemonics(), vec!["DEPT", "GR"]);
    let gr = las.curve_data("GR").unwrap();
    assert_eq!(gr, &[11.1, 22.2, 33.3]);
}

// ---------------------------------------------------------------------------
// NULL handling and read options
// ---------------------------------------------------------------------------

#[test]
fn default_null_policy_replaces_declared_null_only() {
    // Declared NULL is -999.25. Under the default policy only that exact value
    // becomes NaN; the 9999.25 sentinels survive.
    let las = read_file(fixture("edge_cases/null_policy_common.las")).expect("parse");

    let gr = las.curve_data("GR").unwrap();
    assert!(gr[1].is_nan(), "GR[1] (-999.25) should be NaN under default policy");

    let nphi = las.curve_data("NPHI").unwrap();
    assert!(
        !nphi[2].is_nan() && (nphi[2] - 9999.25).abs() < 1e-9,
        "NPHI[2] (9999.25) should survive the default policy, got {}",
        nphi[2],
    );
}

#[test]
fn common_null_policy_catches_extra_sentinels() {
    let opts = ReadOptions { null_policy: Some(NullPolicy::Common), ..Default::default() };
    let las = parse_with(
        &std::fs::read_to_string(fixture("edge_cases/null_policy_common.las")).unwrap(),
        &opts,
    )
    .expect("parse");

    let nphi = las.curve_data("NPHI").unwrap();
    assert!(nphi[2].is_nan(), "NPHI[2] (9999.25) should be NaN under Common policy");
    let rhob = las.curve_data("RHOB").unwrap();
    assert!(rhob[3].is_nan(), "RHOB[3] (9999.25) should be NaN under Common policy");
}

#[test]
fn ignore_data_skips_the_ascii_section() {
    let opts = ReadOptions { ignore_data: true, ..Default::default() };
    let las = read_file_with(fixture("v20/sample_v20.las"), &opts).expect("parse");

    // Headers are still present...
    assert_eq!(las.well_value("WELL").as_deref(), Some("DEEP HORIZON #1"));
    assert_eq!(las.curve_mnemonics(), vec!["DEPT", "DT", "GR", "CALI", "SP"]);
    // ...but no sample data was read.
    let total: usize = las.curve_mnemonics().iter().map(|m| las.curve_data(m).map_or(0, |d| d.len())).sum();
    assert_eq!(total, 0, "ignore_data should leave all curves empty");
}

#[test]
fn mnemonic_case_lower_folds_names() {
    let opts = ReadOptions { mnemonic_case: Some("lower".to_string()), ..Default::default() };
    let las = read_file_with(fixture("v20/sample_v20.las"), &opts).expect("parse");

    assert!(las.curve_mnemonics().contains(&"gr"), "names should be lowercased: {:?}", las.curve_mnemonics());
    // Lookup stays case-insensitive regardless of stored case.
    assert!(las.curve_data("GR").is_some());
}

// ---------------------------------------------------------------------------
// Encodings (auto-detect)
// ---------------------------------------------------------------------------

#[test]
fn decodes_latin1_fallback() {
    // No BOM, not valid UTF-8 → Windows-1252 fallback. Must not panic and must
    // still parse the structure.
    let las = read_file(fixture("encodings/latin1.las")).expect("latin1 should decode + parse");
    assert!(las.well_value("WELL").unwrap().contains("FORAGE"));
    assert!(las.curve_data("GR").is_some());
}

#[test]
fn decodes_utf8_and_utf16_bom() {
    for f in ["encodings/utf8_bom.las", "encodings/utf16_le_bom.las", "encodings/utf16_be_bom.las"] {
        let las = read_file(fixture(f)).unwrap_or_else(|e| panic!("{f} should decode: {e}"));
        assert!(las.index().is_some(), "{f} should have an index curve");
    }
}

// ---------------------------------------------------------------------------
// Round-trip + writing
// ---------------------------------------------------------------------------

#[test]
fn roundtrip_preserves_curve_data() {
    let original = read_file(fixture("v20/sample_v20.las")).expect("parse");
    let text = original.to_las_string().expect("serialize");
    let reparsed = parse(&text).expect("re-parse serialized output");

    assert_eq!(original.curve_mnemonics(), reparsed.curve_mnemonics());

    for name in original.curve_mnemonics() {
        let a = original.curve_data(name).unwrap();
        let b = reparsed.curve_data(name).unwrap();
        assert_eq!(a.len(), b.len(), "{name} length changed across round-trip");
        for (i, (x, y)) in a.iter().zip(b.iter()).enumerate() {
            match (x.is_nan(), y.is_nan()) {
                (true, true) => {}
                _ => assert!((x - y).abs() < 1e-4, "{name}[{i}]: {x} != {y}"),
            }
        }
    }
}

#[test]
fn write_file_then_read_back() {
    let las = parse(INLINE_LAS).expect("parse");
    let out = scratch("written.las");

    las.write_file(&out).expect("write");
    let back = read_file(&out).expect("read back");

    assert_eq!(back.well_value("WELL").as_deref(), Some("INLINE-1"));
    assert_eq!(back.curve_data("GR").unwrap(), &[11.1, 22.2, 33.3]);

    let _ = std::fs::remove_file(&out);
}

// ---------------------------------------------------------------------------
// Error paths
// ---------------------------------------------------------------------------

#[test]
fn errors_on_non_las_text() {
    let err = read_file(fixture("edge_cases/not_a_las_file.las"));
    assert!(err.is_err(), "a file with no ~ sections should error");
}

#[test]
fn errors_on_missing_file() {
    let err = read_file(fixture("does/not/exist.las"));
    assert!(err.is_err());
}

#[test]
fn rejects_binary_lidar_las() {
    // A binary LiDAR ".las" begins with the magic bytes "LASF".
    let out = scratch("lidar.las");
    std::fs::write(&out, b"LASF\x00\x01\x02\x03binary point cloud data").unwrap();

    let err = read_file(&out);
    assert!(err.is_err(), "binary LiDAR LAS should be rejected, not parsed as text");

    let _ = std::fs::remove_file(&out);
}

// ---------------------------------------------------------------------------
// Constructing in memory
// ---------------------------------------------------------------------------

#[test]
fn create_default_is_usable() {
    let las = LASFile::create_default();
    // A fresh file has the VERS/WRAP version items but no curves yet.
    assert!(las.index().is_none());
    assert!(las.curve_mnemonics().is_empty());
}
