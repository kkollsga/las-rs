//! `las_rs` — a high-performance parser and writer for LAS (Log ASCII
//! Standard) well-log files, supporting LAS 1.2, 2.0, and 3.0.
//!
//! The crate is pure Rust by default. The optional `python` feature adds the
//! PyO3 bindings that back the [`las-rs`](https://pypi.org/project/las-rs/)
//! PyPI wheel; Rust consumers never pull PyO3 or numpy.
//!
//! # Quick start
//!
//! ```no_run
//! // Read from disk (encoding auto-detected).
//! let las = las_rs::read_file("welllog.las")?;
//!
//! // Header metadata.
//! println!("well: {:?}", las.well_value("WELL"));
//! println!("index unit: {:?}", las.index_unit);
//!
//! // Curve data (NULLs are NaN).
//! for name in las.curve_mnemonics() {
//!     let n = las.curve_data(name).map_or(0, |d| d.len());
//!     println!("{name}: {n} samples");
//! }
//! # Ok::<(), las_rs::LasError>(())
//! ```
//!
//! Parse from a string with [`parse`], or take full control of parsing via
//! [`ReadOptions`] + [`parse_with`] / [`read_file_with`].
#![allow(unused_variables, unused_assignments, non_snake_case)]

pub mod api;
pub mod core;
pub mod reader;
pub mod writer;

#[cfg(feature = "python")]
pub mod python;

pub use core::types::{HeaderItem, CurveItem, SectionItems, Value};
pub use core::las_file::LASFile;
pub use core::errors::LasError;

pub use api::{parse, parse_with, read_file, read_file_with, ReadOptions};
pub use reader::data::NullPolicy;

#[cfg(feature = "python")]
pub use python::errors::{LASDataError, LASHeaderError, LASUnknownUnitError};
