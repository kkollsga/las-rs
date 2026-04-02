# las_rs — Implementation Plan

## Overview

las_rs is a high-performance LAS (Log ASCII Standard) file parser and writer, built as a pure Rust library with thin Python bindings via PyO3. It implements the CWLS LAS specification (versions 1.2, 2.0, and 3.0) and exposes a Python API compatible with the de facto standard Python LAS library, enabling drop-in migration.

This plan is a clean-room implementation derived entirely from:
- The CWLS LAS 1.2, 2.0, and 3.0 file format specifications
- Our 415-test acceptance suite (`tests/test_phase*.py`)
- Our benchmark baseline (`benchmarks/results.csv`)
- The public Python API contract defined by our test assertions

No third-party source code is referenced during implementation.

---

## Architecture

```
las_rs/
├── Cargo.toml                 # Workspace root
├── pyproject.toml              # Maturin build config
├── src/                        # Pure Rust library crate
│   ├── lib.rs                  # Crate root, public API re-exports
│   ├── types.rs                # HeaderItem, CurveItem, SectionItems
│   ├── reader/
│   │   ├── mod.rs              # Reader entry point
│   │   ├── encoding.rs         # BOM detection, chardet bridge, codec fallback
│   │   ├── sections.rs         # Section discovery (~ line scanner)
│   │   ├── header.rs           # Header line regex parser
│   │   ├── data.rs             # Data section parser (normal + fast engine)
│   │   └── policies.rs         # Read/null policies, regex substitutions
│   ├── writer/
│   │   ├── mod.rs              # Writer entry point
│   │   ├── header.rs           # Header section formatting
│   │   └── data.rs             # Data section formatting (wrap, column alignment)
│   ├── las_file.rs             # LASFile struct and methods
│   ├── defaults.rs             # Standard mnemonics, depth units, order definitions
│   ├── errors.rs               # LASDataError, LASHeaderError, LASUnknownUnitError
│   └── spec.rs                 # LAS spec constants (version-specific field ordering)
├── python/
│   └── las_rs/
│       ├── __init__.py         # Python package: re-exports, read() function
│       ├── _native.pyi         # Type stubs for the Rust extension
│       └── py_bindings.rs      # PyO3 wrapper module (#[pymodule])
├── tests/                      # Python acceptance tests (415 tests, all xfail)
├── benchmarks/                 # Performance benchmarks + baseline
└── plan.md                     # This file
```

---

## Data Model (Rust Core)

### HeaderItem

```rust
pub struct HeaderItem {
    pub original_mnemonic: String,   // Raw mnemonic from file (preserved for write fidelity)
    session_mnemonic: String,        // May have :N suffix for duplicates
    pub unit: String,
    pub value: Value,                // Enum: Str(String) | Int(i64) | Float(f64)
    pub descr: String,
}
```

Key behaviors:
- `mnemonic()` returns `session_mnemonic` (computed, may have `:1` suffix)
- `useful_mnemonic()` returns `original_mnemonic` if non-blank, else `"UNKNOWN"`
- Setting `set_mnemonic(name)` updates `original_mnemonic` and recomputes `session_mnemonic`
- Dict-like access for Python: `item["mnemonic"]`, `item["unit"]`, `item["value"]`, `item["descr"]`
- JSON serialization uses `original_mnemonic`
- Pickleable via `__reduce__`

### CurveItem

```rust
pub struct CurveItem {
    pub header: HeaderItem,
    pub data: Vec<f64>,       // Or ndarray for zero-copy numpy interop
}
```

Extends HeaderItem with a data array. `API_code` is an alias for `value`.

### SectionItems

```rust
pub struct SectionItems {
    items: Vec<HeaderItem>,    // or Vec<CurveItem> for curve sections
    pub mnemonic_transforms: bool,  // case-insensitive comparison when true
}
```

Behaves as a list with dict-like access:
- `__getitem__` by mnemonic string or integer index or slice
- `__setitem__` with HeaderItem replaces; with scalar updates `.value`
- `__delitem__` by mnemonic or index
- `__contains__` by mnemonic string or item reference
- `__getattr__` / `__setattr__` for `section.COMP` style access
- `keys()`, `values()`, `items()`, `dictview()`
- `get(mnemonic, default, add)` with type-aware defaults (HeaderItem vs CurveItem)
- `append()` / `insert()` trigger `assign_duplicate_suffixes()`

### Value

```rust
pub enum Value {
    Str(String),
    Int(i64),
    Float(f64),
}
```

The parser attempts `i64` → `f64` → `String` for header values. UWI and API fields are always kept as `String` (never parsed as numbers, even if they look numeric like `300E074350061450`).

### LASFile

```rust
pub struct LASFile {
    pub sections: HashMap<String, Section>,
    pub encoding: Option<String>,
    pub index_unit: Option<String>,
    index_initial: Option<Vec<f64>>,
}

pub enum Section {
    Items(SectionItems),
    Text(String),
}
```

Properties (Python-side via `#[getter]`):
- `version` → `sections["Version"]`
- `well` → `sections["Well"]`
- `curves` → `sections["Curves"]`
- `params` → `sections["Parameter"]`
- `other` → `sections["Other"]` (String)
- `header` → full sections dict
- `data` → 2D numpy array (column stack of all curve data)
- `index` → first curve's data array
- `depth_m` / `depth_ft` → unit-converted index
- `curvesdict` → `{mnemonic: CurveItem}`
- `json` → JSON string via custom encoder

All properties have setters.

---

## Phase 1: Core Types

**Goal:** `HeaderItem`, `CurveItem`, `SectionItems` working in Rust with PyO3 bindings.

**Acceptance:** `tests/test_phase1_*.py` — 57 tests pass.

### Tasks

1. **Scaffold project**
   - `Cargo.toml` with pyo3, numpy, serde_json, regex dependencies
   - `pyproject.toml` with maturin build backend
   - Python package at `python/las_rs/__init__.py`
   - Verify `maturin develop` builds and `import las_rs` works

2. **Implement `Value` enum**
   - `Str`, `Int`, `Float` variants
   - `Display`, `PartialEq`, `From<&str>` conversions
   - Python: transparent conversion (str/int/float)

3. **Implement `HeaderItem`**
   - Constructor: `new(mnemonic, unit, value, descr, data)`
   - `original_mnemonic`, `useful_mnemonic()`, `set_session_mnemonic_only()`
   - `set_mnemonic()` updates both `original_mnemonic` and recomputes session
   - `__getitem__` for dict-style read access (mnemonic, unit, value, descr, original_mnemonic, useful_mnemonic)
   - `__setattr__` for attribute writes (mnemonic setter triggers rename logic)
   - `__repr__`, `__reduce__` (pickle), `json` property
   - PyO3: `#[pyclass]` with `#[pymethods]`

4. **Implement `CurveItem`**
   - Inherits from HeaderItem (composition in Rust, inheritance in Python)
   - `data` field: numpy array interop via `numpy::PyArray1`
   - `API_code` property (alias for value)
   - `__repr__` includes `data.shape`
   - `json` includes data as list

5. **Implement `SectionItems`**
   - Backed by `Vec<Box<dyn Item>>` or enum dispatch
   - All sequence protocol methods: `__len__`, `__getitem__`, `__setitem__`, `__delitem__`, `__contains__`, `__iter__`
   - Slice support: `items[1:4]` returns new `SectionItems`
   - Dict-like access by mnemonic string
   - `keys()`, `values()`, `items()`, `iterkeys()`, `itervalues()`, `iteritems()`
   - `get(mnemonic, default, add)` with type-aware logic
   - `append()`, `insert()` — both trigger `assign_duplicate_suffixes()`
   - `assign_duplicate_suffixes(test_mnemonic)` — `:1`, `:2`, `:3` suffixing
   - `mnemonic_transforms` flag for case-insensitive comparison
   - `__getattr__` / `__setattr__` for `section.COMP` access
   - `set_item()`, `set_item_value()`, `dictview()`
   - `__str__` — aligned table output
   - `json` property

---

## Phase 2: Reading

**Goal:** Parse LAS 1.2 and 2.0 files from filenames, file objects, and strings.

**Acceptance:** `tests/test_phase2_*.py` — 109 tests pass.

### Tasks

6. **File opening (`reader/mod.rs`)**
   - Accept `&str` (filename, URL, or LAS content), file objects, `pathlib.Path`
   - Detect input type: multi-line string → `StringIO`, single line → filename, URL regex → fetch
   - LiDAR guard: first 4 bytes `"LASF"` → `IOError`
   - Return `(BufReader, Option<encoding>)`

7. **Encoding detection (`reader/encoding.rs`)**
   - BOM detection: UTF-8 BOM (`EF BB BF`) → `utf-8-sig`
   - Bridge to Python's `chardet` via PyO3 for auto-detection
   - Fallback chain: ascii → windows-1252 → latin-1
   - Support explicit `encoding` kwarg override
   - `encoding_errors`: strict / replace / ignore
   - `autodetect_encoding`: `true` / `false` / `"chardet"` (string)
   - `autodetect_encoding_chars`: number of bytes to sample

8. **Section discovery (`reader/sections.rs`)**
   - Scan for lines starting with `~`
   - Record: `(byte_offset, first_line_no, last_line_no, section_title)`
   - Classify: `~V` → Version, `~W` → Well, `~C` → Curves, `~P` → Parameter, `~O` → Other, `~A` → Data
   - LAS 3.0: `~Log_Definition` → Curves, `~Log_Parameter` → Parameter, `*_Data` → Data
   - No `~` sections found → `KeyError`

9. **Header line parser (`reader/header.rs`)**
   - Primary regex: `name.unit value : descr`
   - Edge cases:
     - Missing period (no `.` before `:`)
     - Missing colon (no description)
     - Double dots (`..`) from mnemonic abbreviation
     - Time values with colons (`13:45:00`)
     - Units with spaces (`1000 lbf`)
     - Cyrillic/Unicode units
     - Dots embedded in mnemonic names
   - Version-aware field ordering:
     - LAS 1.2 Well section: STRT/STOP/STEP/NULL use `value:descr`; others use `descr:value`
     - LAS 2.0+: all `value:descr`
   - `mnemonic_case` kwarg: upper / lower / preserve
   - Skip comment lines (configurable, default `#`)
   - `ignore_header_errors`: catch parse failures as warnings

10. **Section parser**
    - Version section: extract VERS, WRAP, DLM
    - Well section: extract STRT, STOP, STEP, NULL + all well items
    - Curves section: build `CurveItem` per line
    - Parameter section: build `HeaderItem` per line with numeric value parsing
    - Other section: join lines as plain text
    - Non-standard sections: store by title in sections dict
    - Number parsing: attempt `i64` → `f64` → keep as string. UWI/API always string.

11. **Read edge cases**
    - Missing VERS / WRAP / NULL → use defaults, continue
    - Missing `~A` section → empty data
    - Blank lines in headers → skip
    - Blank lines before first `~` → skip
    - Duplicate mnemonics → suffix with `:1`, `:2`
    - Empty mnemonics → `"UNKNOWN"`
    - Excess data columns → auto-create unnamed curves
    - Sparse curves (defined but no data) → NaN-filled arrays
    - Barebones files with missing sections → graceful defaults

---

## Phase 3: Data Section

**Goal:** Parse data sections with full policy support, wrapped data, and string columns.

**Acceptance:** `tests/test_phase3_*.py` — 53 tests pass.

### Tasks

12. **Read/null policy engine (`reader/policies.rs`)**
    - Read policies (regex substitutions applied to data lines before parsing):
      - `comma-decimal-mark`: `(\d),(\d)` → `\1.\2`
      - `run-on(-)`: `(\d)-(\d)` → `\1 -\2`
      - `run-on(.)`: multi-decimal → `NaN NaN`
      - Default: all three. Empty `()` disables all.
      - Auto-detect: if hyphens in every sampled line, remove `run-on(-)` sub
    - Null policies (value replacement after parsing):
      - `none`: no replacement
      - `strict`: only replace header NULL value with NaN
      - `common`: NULL + `(null)`, `-`, `9999.25`, `999.25`, `NA`, `INF`, `IO`, `IND`
      - `aggressive`: common + `999`, `9999`, `2147483647`, `32767`, `-0.0`
      - `all`: aggressive + any non-numeric text
      - Custom: list of values/sentinel names
    - Index column (column 0) is NEVER null-replaced

13. **Data section inspection**
    - Sample first ~20 data lines
    - Count columns per line (after regex subs)
    - Detect inconsistent column counts → return -1
    - Check for hyphens in every line → recommend removing hyphen subs

14. **Fast data parser (default engine)**
    - Use Rust's fast string parsing — no numpy dependency for the core
    - Parse lines, split on delimiter (whitespace / comma / tab)
    - Build column-major `Vec<Vec<f64>>` directly
    - Handle quoted strings (`"pick gamma"` stays as one token)
    - Strip `chr(26)` (Ctrl-Z / EOF marker)
    - Reshape into per-curve arrays
    - Apply null replacement
    - Release GIL during parsing via `py.allow_threads()`

15. **Normal engine (compatibility fallback)**
    - Line-by-line parsing with full regex substitution pipeline
    - Handles wrapped data (values span multiple lines per depth step)
    - Handles mixed string/float data (`{S}` format columns)
    - `dtypes` kwarg: `"auto"` / `dict` / `list` / `False`

16. **Wrapped data support**
    - When WRAP=YES, accumulate tokens across lines until `n_curves` values collected per depth step
    - Always uses normal engine (fast engine doesn't handle wrapping)

17. **Post-processing**
    - Assign data arrays to CurveItem objects
    - NULL → NaN replacement (skip index column)
    - Detect depth/index unit from STRT/STOP/STEP/curve[0] units
    - Standardize depth units: FT/F/FEET/FOOT → `"FT"`, M/METER/METRES/м → `"M"`, .1IN → `".1IN"`
    - Store `index_initial` copy for write-time comparison

---

## Phase 4: Writing

**Goal:** Write LAS files with full formatting control.

**Acceptance:** `tests/test_phase4_*.py` — 55 tests pass.

### Tasks

18. **Header writer (`writer/header.rs`)**
    - Version-aware field ordering (LAS 1.2 descr:value swap for Well section)
    - Configurable `header_width` (default 60)
    - Auto-calculated column widths from content
    - Format: `MNEM.UNIT  value : descr` (or reversed for 1.2)

19. **Data writer (`writer/data.rs`)**
    - NaN → NULL value string replacement
    - Configurable `fmt` (default `"%.5f"`), `column_fmt` per-column overrides
    - `len_numeric_field`: auto (default), fixed width, or -1 (no padding)
    - `lhs_spacer` (default `" "`), `spacer` (default `" "`)
    - `data_section_header` (default `"~ASCII"`)
    - `mnemonics_header`: add curve names to `~A` line
    - Wrapped mode: `textwrap` at `data_width` (default 79)

20. **Write method (`LASFile.write()`)**
    - Accept file path string or file-like object
    - `version` kwarg: 1.2 / 2.0 / None (use file's version). Does NOT mutate in-memory VERS.
    - `wrap` kwarg: True / False / None (use file's WRAP)
    - `STRT`, `STOP`, `STEP` kwargs: override calculated values
    - Auto-recalculate STRT/STOP/STEP from data if index changed since read
    - Update STRT/STOP/STEP units from index curve
    - Sections written in order: ~Version, ~Well, ~Curves, ~Params, ~Other, ~ASCII
    - Write uses `original_mnemonic` (not session `:N` suffixes)

21. **CSV export (`LASFile.to_csv()`)**
    - Accept file path or file-like object
    - `mnemonics`: True (use curve mnemonics) / False / explicit list
    - `units`: True (use curve units) / False / explicit list
    - `units_loc`: `"line"` / `"[]"` / `"()"`
    - Pass `**kwargs` through to Python's `csv.writer`

---

## Phase 5: Advanced Features

**Goal:** DataFrame integration, JSON, encoding, curve operations, depth units, serialization.

**Acceptance:** `tests/test_phase5_*.py` — 120 tests pass.

### Tasks

22. **DataFrame integration**
    - `df(include_units=False)` → `pandas.DataFrame`
    - First curve (depth) becomes DataFrame index
    - String dtype columns auto-converted to float64 if possible
    - `include_units=True` appends `" (unit)"` to column names, uses `original_mnemonic`
    - `set_data(array, names=None, truncate=False)`
    - `set_data_from_df(df)` — index becomes first curve, column names become mnemonics

23. **JSON export**
    - `json` property returns `{"metadata": {...}, "data": {...}}`
    - Metadata: sections as dictviews
    - Data: `{mnemonic: [values...]}`, NaN → `null`
    - `JSONEncoder` class for `json.dumps(las, cls=JSONEncoder)`
    - Setter raises `Exception`

24. **Curve manipulation**
    - `append_curve(mnemonic, data, unit, descr, value)`
    - `insert_curve(ix, mnemonic, data, unit, descr, value)`
    - `delete_curve(mnemonic=None, ix=None)` — index takes precedence
    - `update_curve(mnemonic=None, data=False, unit=False, descr=False, value=False, ix=None)`
    - `append_curve_item(CurveItem)` / `insert_curve_item(ix, CurveItem)` / `replace_curve_item(ix, CurveItem)`
    - `get_curve(mnemonic)` → CurveItem
    - `__getitem__` by mnemonic or int → data array
    - `__setitem__` — array appends new curve; CurveItem replaces or appends
    - `keys()`, `values()`, `items()` for curve iteration
    - `stack_curves(mnemonic_or_list, sort_curves=True)` → 2D numpy array

25. **Depth units**
    - Auto-detection from STRT/STOP/STEP/curve[0] units
    - Recognized: FT/F/FEET/FOOT, M/METER/METRES/м, .1IN/0.1IN
    - `depth_m` property: convert to meters
    - `depth_ft` property: convert to feet
    - `.1IN` conversion: `index / 120` for feet, `(index / 120) * 0.3048` for meters
    - `index_unit` kwarg at read time to override detection
    - Conflicting units → `None`
    - Unknown unit → `LASUnknownUnitError` on conversion

26. **Serialization**
    - Pickle support for `HeaderItem`, `CurveItem`, `SectionItems`, `LASFile`
    - Via `__reduce__` returning constructor args

27. **Encoding (Python-side)**
    - BOM detection in Rust
    - `chardet` bridge via PyO3 (call Python's chardet from Rust)
    - Fallback chain in Rust: try ascii, windows-1252, latin-1
    - Store detected encoding on `LASFile.encoding`

---

## Phase 6: LAS 3.0

**Goal:** Proper LAS 3.0 support beyond what existing tools provide.

**Acceptance:** `tests/test_phase6_*.py` — 12 tests pass.

### Tasks

28. **LAS 3.0 section mapping**
    - `~Log_Definition` → `sections["Curves"]`
    - `~Log_Parameter` → `sections["Parameter"]`
    - Other `*_Definition`, `*_Parameter`, `*_Data` sections → stored by title
    - DLM header item: SPACE (default), COMMA, TAB

29. **Delimiter handling**
    - SPACE: split on whitespace (respecting quoted strings)
    - COMMA: split on `,`
    - TAB: split on `\t` (respecting quoted strings)

30. **String data columns**
    - `{S}` format in curve definition → column is string type
    - `{F}` → float, `{E}` → scientific notation float
    - Mixed float/string data sections work without crashing

31. **Future LAS 3.0 enhancements** (post-MVP)
    - Format field (`{F}`, `{S}`, `{E}`, `{A:spacing}`) parsing into HeaderItem
    - Association field (`| Run[1]`) parsing
    - Multiple `DataSet` triplets (Definition/Parameter/Data)
    - Array channel grouping (`NMR[1]..NMR[5]` → 2D)
    - Parameter zoning (comma-separated value ranges)
    - LAS 3.0 writer

---

## Phase 7: Polish & Performance

**Goal:** File I/O edge cases, error types, property accessors, and performance optimization.

**Acceptance:** `tests/test_phase7_*.py` — 25 tests pass. All 415 tests pass. Benchmarks beat baseline.

### Tasks

32. **Error types**
    - `LASDataError(Exception)` — data reshape failures, corrupt data
    - `LASHeaderError(Exception)` — malformed header lines
    - `LASUnknownUnitError(Exception)` — unknown depth unit conversion
    - Proper error chaining with context messages

33. **File I/O polish**
    - `pathlib.Path` → string conversion
    - URL detection (http/https/ftp regex) → fetch via Python's urllib
    - Multi-line string detection → in-memory parse
    - File handle detection → read directly
    - `__version__` attribute on the package

34. **Property accessors**
    - All getters/setters for version, well, curves, params, other, header, data, index
    - `update_start_stop_step(STRT, STOP, STEP, fmt)` — recalculate from data
    - `update_units_from_index_curve()` — sync units

35. **Performance optimization**
    - Profile with `criterion` (Rust-side benchmarks)
    - Release GIL during all parsing and writing (`py.allow_threads()`)
    - Zero-copy numpy interop where possible (`PyArray1::from_vec`)
    - SIMD-friendly data layout (column-major storage)
    - Lazy `data` property (avoid vstack until accessed)
    - String interning for mnemonics
    - Pre-compiled regex (lazy_static / once_cell)

36. **Benchmark validation**
    - Run full benchmark suite: `./benchmarks/run.sh VERSION --full`
    - Run comparison: `./benchmarks/run.sh VERSION --suite compare`
    - Targets (10K rows × 8 curves):

      | Operation | Baseline | Target | Speedup |
      |---|---|---|---|
      | Read (fast) | 29 ms | < 3 ms | 10x |
      | Read (compat) | 89 ms | < 9 ms | 10x |
      | Write | 62 ms | < 6 ms | 10x |
      | Round-trip | 24 ms | < 3 ms | 8x |
      | `las["GR"]` | 542 ns | < 50 ns | 10x |
      | `las.data` | 5.4 µs | < 500 ns | 10x |
      | JSON export | 38 ms | < 4 ms | 10x |

---

## Implementation Order

```
Phase 1  ██░░░░░░░░░░  Core types (HeaderItem, CurveItem, SectionItems)
Phase 2  ████░░░░░░░░  Reading (file open, sections, header parse)
Phase 3  ██████░░░░░░  Data section (parsers, policies, wrapped)
Phase 4  ████████░░░░  Writing (header/data format, CSV)
Phase 5  ██████████░░  Advanced (DataFrame, JSON, curves, encoding)
Phase 6  ███████████░  LAS 3.0
Phase 7  ████████████  Polish & performance
```

Each phase is independently testable. Run `pytest tests/test_phaseN_*.py` after each phase to track progress — tests flip from `xfail` to passing.

---

## Project Setup Commands

```bash
# Initial scaffold
cargo init --lib
maturin init --bindings pyo3

# Development cycle
maturin develop --release          # Build and install into current venv
pytest tests/test_phase1_*.py -v   # Run phase 1 tests

# Benchmarks
./benchmarks/run.sh 0.1.0 --quick      # Tier 1 only (~30s)
./benchmarks/run.sh 0.1.0              # Tier 1+2 (~2min)
./benchmarks/run.sh 0.1.0 --full       # All tiers (~10min)

# Compare against baseline
python benchmarks/report.py --vs-lasio 0.1.0
python benchmarks/report.py --compare 0.1.0 0.2.0 --charts
```

---

## Dependencies

### Rust
- `pyo3` — Python bindings
- `numpy` (pyo3 crate) — zero-copy array interop
- `regex` — header line parsing
- `serde` + `serde_json` — JSON serialization
- `encoding_rs` — character encoding detection and conversion
- `rayon` — parallel batch processing (Phase 7)
- `once_cell` — lazy-initialized compiled regexes
- `memchr` — fast byte scanning for section discovery

### Python (runtime)
- `numpy` — required
- `pandas` — optional (for `.df()`)

### Python (dev)
- `maturin` — build tool
- `pytest` — test runner
- `pytest-benchmark` — performance benchmarks

---

## Key Design Decisions

1. **Column-major storage.** Curve data stored as independent `Vec<f64>` per curve, not a single 2D array. This matches the LAS format (data is per-curve metadata) and avoids expensive reshaping. The `data` property lazily vstacks on access.

2. **Value enum, not stringly-typed.** Header values are `Value::Int | Float | Str`, not raw strings. Parsing happens once at read time. UWI/API fields are forced to `Str`.

3. **Regex compiled once.** All header-line patterns compiled at module load via `once_cell::Lazy`. No per-line regex compilation.

4. **GIL released during I/O.** All file reading and writing runs inside `py.allow_threads()`. Only the final numpy array construction requires the GIL.

5. **Composition over inheritance.** `CurveItem` contains a `HeaderItem` in Rust. The Python layer uses `__getattr__` delegation to simulate inheritance for API compatibility.

6. **Session mnemonics are ephemeral.** The `:1`, `:2` suffixes exist only in memory. Writes always use `original_mnemonic`. Re-reading a written file recomputes suffixes fresh.

7. **Spec-first, not clone-first.** Implementation follows the CWLS LAS specification documents. Test assertions define the API contract. No third-party source code is referenced.
