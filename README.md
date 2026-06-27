# las-rs

A high-performance LAS file parser and writer, written in Rust with first-class Python bindings.

Reads and writes LAS 1.2, 2.0, and 3.0 well log files. Designed as a fast, drop-in alternative to [lasio](https://github.com/kinverarity1/lasio).

Available both as a Rust crate ([`las_rs`](https://crates.io/crates/las_rs) on crates.io — pure Rust, no Python dependency) and as a Python package ([`las-rs`](https://pypi.org/project/las-rs/) on PyPI).

## Installation

Python:

```bash
pip install las-rs
```

Prebuilt wheels are available for Python 3.10 -- 3.13 on Linux (x86_64), macOS (ARM), and Windows (x64).

Rust:

```bash
cargo add las_rs
```

The crate is pure Rust by default — no PyO3 or numpy in your dependency tree.

## Quick start

```python
import las_rs

# Read a LAS file
las = las_rs.read("welllog.las")

# Access header metadata
print(las.well["WELL"].value)   # Well name
print(las.well["STRT"].value)   # Start depth
print(las.index_unit)           # "M", "FT", etc.

# Access curve data (numpy arrays)
gr = las["GR"]
depth = las.index

# Iterate curves
for name, data in las.items():
    print(name, data.shape)

# Convert to pandas DataFrame
df = las.df()
```

## Reading options

```python
las = las_rs.read(
    "welllog.las",
    encoding="latin-1",              # Auto-detected if omitted
    ignore_header_errors=True,       # Continue past malformed headers
    ignore_data=True,                # Parse headers only (fast)
    null_policy=["-999", "-999.25"], # Custom null markers
    dtypes={"STATUS": str},          # Keep specific curves as strings
)
```

`read()` accepts a file path, a `pathlib.Path`, a string containing LAS content, or any file-like object with a `.read()` method.

## Working with curves

```python
import numpy as np

# Add a curve
las.append_curve("CALC", data=np.zeros(len(las.index)), unit="GAPI", descr="Computed")

# Update a curve
las.update_curve(mnemonic="GR", data=new_data)

# Delete a curve
las.delete_curve(mnemonic="CALC")

# Stack selected curves into a 2D array
matrix = las.stack_curves(["GR", "NPHI", "RHOB"])

# Get full curve metadata
curve = las.get_curve("GR")
print(curve.mnemonic, curve.unit, curve.descr)
```

## Writing and export

```python
# Write LAS file
las.write("output.las", version=2.0)

# Export to CSV
las.to_csv("output.csv", units=True)

# JSON
json_str = las.json
```

## Depth conversion

```python
depth_m  = las.depth_m    # Index converted to meters
depth_ft = las.depth_ft   # Index converted to feet
```

## Rust

The same engine is usable directly from Rust, without the Python layer:

```rust
use las_rs::{read_file, parse, ReadOptions, NullPolicy};

// Read a file from disk (encoding auto-detected).
let las = read_file("welllog.las")?;

// Header metadata.
println!("well:       {:?}", las.well_value("WELL"));
println!("index unit: {:?}", las.index_unit);

// Curve data — NULLs are represented as f64::NAN.
for name in las.curve_mnemonics() {
    let n = las.curve_data(name).map_or(0, |d| d.len());
    println!("{name}: {n} samples");
}

// Access the index (first) curve and a named curve.
let depth = las.index().unwrap_or(&[]);
if let Some(gr) = las.curve_data("GR") {
    println!("first GR sample at depth {}: {}", depth[0], gr[0]);
}

// Parse from an in-memory string, with custom options.
let opts = ReadOptions { null_policy: Some(NullPolicy::Common), ..Default::default() };
let las2 = las_rs::parse_with("~VERSION\nVERS. 2.0:\n~ASCII\n", &opts)?;

// Write back out.
las.write_file("out.las")?;
let text: String = las.to_las_string()?;
# let _ = (parse, las2, text);
Ok::<(), las_rs::LasError>(())
```

Full API docs: [docs.rs/las_rs](https://docs.rs/las_rs).

## License

[MIT](LICENSE)
