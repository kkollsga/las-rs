//! Ergonomic, pure-Rust entry points for reading, inspecting, and writing
//! LAS files.
//!
//! The low-level workhorses live in [`crate::reader`] and [`crate::writer`]
//! and take many positional arguments. This module wraps them with sane
//! defaults so the common case is a one-liner:
//!
//! ```no_run
//! let las = las_rs::read_file("welllog.las")?;
//! println!("curves: {:?}", las.curve_mnemonics());
//! if let Some(gr) = las.curve_data("GR") {
//!     println!("{} GR samples", gr.len());
//! }
//! # Ok::<(), las_rs::LasError>(())
//! ```
//!
//! For full control over parsing, build a [`ReadOptions`] and call
//! [`parse_with`] / [`read_file_with`].

use std::path::Path;

use crate::core::errors::LasError;
use crate::core::las_file::LASFile;
use crate::reader::data::NullPolicy;

// Only used by the inherent accessor impl below, which is gated to non-python
// builds (PyO3 supplies equivalent #[pymethods] when the python feature is on).
#[cfg(not(feature = "python"))]
use std::collections::HashMap;
#[cfg(not(feature = "python"))]
use crate::core::types::{CurveItem, ItemWrapper};

/// Options controlling how a LAS file is parsed.
///
/// [`Default`] mirrors the defaults of the Python `las_rs.read()` binding:
/// strict header parsing, no mnemonic case folding, full data parsing, the
/// header-declared NULL value, comma-decimal-mark normalization, and `#` as
/// the inline comment marker.
#[derive(Debug, Clone)]
pub struct ReadOptions {
    /// Continue past malformed header lines instead of erroring.
    pub ignore_header_errors: bool,
    /// Fold all mnemonics to `"upper"` / `"lower"`, or leave as-is (`None`).
    pub mnemonic_case: Option<String>,
    /// Parse the `~ASCII` data section. Set `false` for a fast headers-only read.
    pub ignore_data: bool,
    /// Which values are treated as NULL. `None` uses the file's declared NULL.
    pub null_policy: Option<NullPolicy>,
    /// Pre-parse data substitutions, e.g. `"comma-decimal-mark"`. `None` disables.
    pub read_policy: Option<String>,
    /// Line prefixes treated as comments inside the data section.
    pub ignore_comments: Vec<String>,
}

impl Default for ReadOptions {
    fn default() -> Self {
        ReadOptions {
            ignore_header_errors: false,
            mnemonic_case: None,
            ignore_data: false,
            null_policy: None,
            read_policy: Some("comma-decimal-mark".to_string()),
            ignore_comments: vec!["#".to_string()],
        }
    }
}

/// Parse LAS content from an in-memory string with default [`ReadOptions`].
pub fn parse(content: &str) -> Result<LASFile, LasError> {
    parse_with(content, &ReadOptions::default())
}

/// Parse LAS content from an in-memory string with explicit [`ReadOptions`].
pub fn parse_with(content: &str, opts: &ReadOptions) -> Result<LASFile, LasError> {
    crate::reader::read_las(
        content,
        opts.ignore_header_errors,
        opts.mnemonic_case.as_deref(),
        opts.ignore_data,
        opts.null_policy.clone(),
        opts.read_policy.clone(),
        &opts.ignore_comments,
    )
}

/// Read and parse a LAS file from disk with default [`ReadOptions`].
///
/// Encoding is auto-detected (BOM, then UTF-8, falling back to Windows-1252).
pub fn read_file<P: AsRef<Path>>(path: P) -> Result<LASFile, LasError> {
    read_file_with(path, &ReadOptions::default())
}

/// Read and parse a LAS file from disk with explicit [`ReadOptions`].
pub fn read_file_with<P: AsRef<Path>>(path: P, opts: &ReadOptions) -> Result<LASFile, LasError> {
    let path = path.as_ref();
    let bytes = std::fs::read(path)
        .map_err(|e| LasError::Io(format!("Cannot read file {}: {}", path.display(), e)))?;

    // Binary LiDAR ".las" files start with the magic "LASF"; they are not
    // Log ASCII Standard text and must not be fed to the text parser.
    if bytes.len() >= 4 && &bytes[0..4] == b"LASF" {
        return Err(LasError::Data(format!(
            "{} is a binary LiDAR LAS file, not a Log ASCII Standard file",
            path.display()
        )));
    }

    let content = decode_bytes(&bytes);
    parse_with(&content, opts)
}

/// Decode raw bytes to a `String`, auto-detecting the encoding via BOM, then
/// UTF-8, then a lossless Windows-1252 fallback. Mirrors the auto-detect path
/// of the Python binding's reader.
fn decode_bytes(bytes: &[u8]) -> String {
    if let Some(rest) = bytes.strip_prefix(b"\xEF\xBB\xBF") {
        return String::from_utf8_lossy(rest).into_owned();
    }
    if bytes.starts_with(b"\xFF\xFE") {
        let (cow, _, _) = encoding_rs::UTF_16LE.decode(bytes);
        return cow.into_owned();
    }
    if bytes.starts_with(b"\xFE\xFF") {
        let (cow, _, _) = encoding_rs::UTF_16BE.decode(bytes);
        return cow.into_owned();
    }
    if let Ok(s) = std::str::from_utf8(bytes) {
        return s.to_owned();
    }
    let (cow, _, _) = encoding_rs::WINDOWS_1252.decode(bytes);
    cow.into_owned()
}

/// Ergonomic read accessors for Rust consumers.
///
/// Gated to non-`python` builds: when the `python` feature is on (the maturin
/// wheel build), `LASFile` carries the PyO3 `#[pymethods]` instead, some of
/// which (`index`, `get_curve`) share these names. Rust embedders always build
/// without the `python` feature, so they always have this API.
#[cfg(not(feature = "python"))]
impl LASFile {
    /// The mnemonics of every curve in `~Curves`, in file order (the first is
    /// the index/depth curve).
    pub fn curve_mnemonics(&self) -> Vec<&str> {
        self.curves_section
            .items
            .iter()
            .map(|item| item.session_mnemonic())
            .collect()
    }

    /// The full [`CurveItem`] for `mnemonic` (case-insensitive), if present.
    pub fn get_curve(&self, mnemonic: &str) -> Option<&CurveItem> {
        let idx = self.curves_section.find_index_by_mnemonic(mnemonic)?;
        match &self.curves_section.items[idx] {
            ItemWrapper::Curve(c) => Some(c),
            _ => None,
        }
    }

    /// The numeric samples of curve `mnemonic` (case-insensitive). NULLs are
    /// represented as `f64::NAN`.
    pub fn curve_data(&self, mnemonic: &str) -> Option<&[f64]> {
        self.get_curve(mnemonic).map(|c| c.curve_data.as_slice())
    }

    /// The index curve's samples — typically depth or time. Resolves to the
    /// first curve whose mnemonic is a known depth/time alias (`DEPT`, `DEPTH`,
    /// `MD`, `TVD`, …), falling back to the first curve when none match.
    pub fn index(&self) -> Option<&[f64]> {
        let pos = self.curves_section.index_curve_position()?;
        match &self.curves_section.items[pos] {
            ItemWrapper::Curve(c) => Some(c.curve_data.as_slice()),
            _ => None,
        }
    }

    /// The display value of a `~Well` header item by mnemonic (e.g. `"WELL"`,
    /// `"STRT"`), case-insensitive.
    pub fn well_value(&self, mnemonic: &str) -> Option<String> {
        let idx = self.well_section.find_index_by_mnemonic(mnemonic)?;
        Some(self.well_section.items[idx].value().display_str())
    }

    /// Render the file back to a LAS-format string using default writer
    /// settings (matches the Python binding's `str(las)`).
    pub fn to_las_string(&self) -> Result<String, LasError> {
        let empty: HashMap<usize, String> = HashMap::new();
        crate::writer::format_las(
            self, None, None, false, None, None, " ", "  ", None, &empty, None, None, None,
        )
    }

    /// Render the file and write it to `path`.
    pub fn write_file<P: AsRef<Path>>(&self, path: P) -> Result<(), LasError> {
        let path = path.as_ref();
        let text = self.to_las_string()?;
        std::fs::write(path, text)
            .map_err(|e| LasError::Io(format!("Cannot write file {}: {}", path.display(), e)))
    }
}
