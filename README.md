# las-rs

A high-performance LAS file parser and writer for Python, written in Rust.

Reads and writes LAS 1.2, 2.0, and 3.0 well log files. Designed as a fast, drop-in alternative to [lasio](https://github.com/kinverarity1/lasio).

## Installation

```bash
pip install las-rs
```

Prebuilt wheels are available for Python 3.10 -- 3.13 on Linux (x86_64), macOS (ARM), and Windows (x64).

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

## License

[MIT](LICENSE)
