"""Synthetic LAS file generator for benchmarking.

Generates LAS files of configurable size, width, and feature complexity.
Files are written to a temp directory and cached so repeated benchmark runs
reuse the same data.  The generator is deterministic (seeded RNG) so results
are reproducible across machines.

Usage as a library
------------------
    from benchmarks.generate import Generator
    gen = Generator(seed=42)
    path = gen.make(rows=100_000, curves=8, version=2.0)

Usage from the command line
---------------------------
    python -m benchmarks.generate          # generate the full default matrix
    python -m benchmarks.generate --rows 1000000 --curves 8  # single file
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_CACHE_DIR: Optional[Path] = None

CURVE_POOL = [
    ("GR", "GAPI", "Gamma Ray"),
    ("NPHI", "V/V", "Neutron Porosity"),
    ("RHOB", "G/CC", "Bulk Density"),
    ("DT", "US/FT", "Sonic Transit Time"),
    ("SP", "MV", "Spontaneous Potential"),
    ("CALI", "IN", "Caliper"),
    ("ILD", "OHMM", "Deep Induction"),
    ("ILM", "OHMM", "Medium Induction"),
    ("SFLU", "OHMM", "Shallow Focused"),
    ("SFLA", "OHMM", "Shallow Laterolog"),
    ("DPHI", "V/V", "Density Porosity"),
    ("PEF", "B/E", "Photoelectric Factor"),
    ("DRHO", "G/CC", "Density Correction"),
    ("MSFL", "OHMM", "Micro-Spherical"),
    ("LLD", "OHMM", "Laterolog Deep"),
    ("LLS", "OHMM", "Laterolog Shallow"),
    ("SGR", "GAPI", "Spectral GR"),
    ("CGR", "GAPI", "Computed GR"),
    ("TNPH", "V/V", "Thermal Neutron"),
    ("RHOZ", "G/CC", "Corrected Density"),
]


def _cache_dir() -> Path:
    """Return (and create) the cache directory for generated LAS files."""
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = Path(tempfile.gettempdir()) / "las_rs_bench"
        _CACHE_DIR.mkdir(exist_ok=True)
    return _CACHE_DIR


def set_cache_dir(path: str | Path) -> None:
    """Override the default cache directory."""
    global _CACHE_DIR
    _CACHE_DIR = Path(path)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class Generator:
    """Deterministic synthetic LAS file generator.

    Parameters
    ----------
    seed : int
        Seed for the numpy random number generator.  Using the same seed
        across runs guarantees identical files (and therefore reproducible
        benchmark numbers).
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    # -- curve metadata -----------------------------------------------------

    def _pick_curves(self, n: int) -> list[tuple[str, str, str]]:
        """Return *n* (mnemonic, unit, descr) tuples.

        When n > len(CURVE_POOL) we generate synthetic names like C021, C022…
        """
        curves = []
        for i in range(n):
            if i < len(CURVE_POOL):
                curves.append(CURVE_POOL[i])
            else:
                tag = f"C{i + 1:03d}"
                curves.append((tag, "NONE", f"Synthetic curve {tag}"))
        return curves

    # -- data generation ----------------------------------------------------

    def _generate_data(
        self,
        rows: int,
        n_curves: int,
        start_depth: float = 1000.0,
        step: float = 0.1524,
        null_fraction: float = 0.0,
        null_value: float = -999.25,
    ) -> np.ndarray:
        """Return a (rows, 1 + n_curves) array: depth column + curve data."""
        depth = np.arange(rows, dtype=np.float64) * step + start_depth
        data = self.rng.standard_normal((rows, n_curves)) * 50 + 100
        # inject nulls
        if null_fraction > 0:
            mask = self.rng.random((rows, n_curves)) < null_fraction
            data[mask] = null_value
        return np.column_stack([depth, data])

    # -- header writing -----------------------------------------------------

    @staticmethod
    def _write_header(
        f,
        version: float,
        wrap: bool,
        null_value: float,
        start: float,
        stop: float,
        step: float,
        curves: list[tuple[str, str, str]],
        dlm: str = "SPACE",
    ) -> None:
        f.write("~VERSION INFORMATION\n")
        f.write(f" VERS.  {version:.1f} : CWLS LOG ASCII STANDARD -VERSION {version:.1f}\n")
        wrap_str = "YES" if wrap else "NO"
        wrap_descr = "Multiple lines per depth step" if wrap else "One line per depth step"
        f.write(f" WRAP.  {wrap_str} : {wrap_descr}\n")
        if version >= 3.0:
            f.write(f" DLM .  {dlm} : Column Data Section Delimiter\n")

        f.write("~WELL INFORMATION\n")
        f.write(f" STRT.M  {start:.4f} : START DEPTH\n")
        f.write(f" STOP.M  {stop:.4f} : STOP DEPTH\n")
        f.write(f" STEP.M  {step:.4f} : STEP\n")
        f.write(f" NULL.   {null_value} : NULL VALUE\n")
        f.write(" COMP.   BENCHMARK SYNTHETIC CO : COMPANY\n")
        f.write(" WELL.   PERFTEST-1 : WELL\n")
        f.write(" FLD .   SYNTHETIC BASIN : FIELD\n")
        f.write(" LOC .   00-00-000-00W0 : LOCATION\n")

        f.write("~CURVE INFORMATION\n")
        f.write(" DEPT.M  : Depth\n")
        for mnem, unit, descr in curves:
            f.write(f" {mnem:<5s}.{unit:<6s}: {descr}\n")

        f.write("~PARAMETER INFORMATION\n")
        f.write(" BHT .DEGC  85.0 : Bottom Hole Temperature\n")
        f.write(" BS  .MM   215.9 : Bit Size\n")
        f.write(" FD  .G/CC   1.1 : Fluid Density\n")

        f.write("~OTHER\n")
        f.write("Synthetically generated LAS file for benchmark testing.\n")

    # -- data writing -------------------------------------------------------

    @staticmethod
    def _write_data_unwrapped(f, data: np.ndarray, fmt: str = "%.4f") -> None:
        f.write("~ASCII\n")
        for row in data:
            line = " ".join(fmt % v for v in row)
            f.write(f" {line}\n")

    @staticmethod
    def _write_data_wrapped(
        f, data: np.ndarray, fmt: str = "%.4f", width: int = 79
    ) -> None:
        f.write("~ASCII\n")
        for row in data:
            full_line = " ".join(fmt % v for v in row)
            wrapped = textwrap.fill(full_line, width=width)
            f.write(wrapped + "\n")

    # -- public API ---------------------------------------------------------

    def make(
        self,
        rows: int = 10_000,
        curves: int = 8,
        version: float = 2.0,
        wrap: bool = False,
        null_fraction: float = 0.0,
        null_value: float = -999.25,
        step: float = 0.1524,
        start_depth: float = 1000.0,
        fmt: str = "%.4f",
        dlm: str = "SPACE",
        force: bool = False,
    ) -> Path:
        """Generate a LAS file and return the path.

        The file is cached based on a hash of all parameters.  Pass
        ``force=True`` to regenerate even if a cached copy exists.

        Parameters
        ----------
        rows : int
            Number of depth samples.
        curves : int
            Number of log curves (excluding depth).
        version : float
            LAS version (1.2, 2.0, or 3.0).
        wrap : bool
            If True, data section is wrapped.
        null_fraction : float
            Fraction of data values to replace with null (0.0 – 1.0).
        null_value : float
            Null sentinel value.
        step : float
            Depth step in metres.
        start_depth : float
            Starting depth.
        fmt : str
            Printf format for numeric data.
        dlm : str
            Delimiter (SPACE, COMMA, TAB) — only affects v3.0.
        force : bool
            Regenerate even if cached.

        Returns
        -------
        Path to the generated LAS file.
        """
        # Build a deterministic cache key from all parameters.
        # Use a hash of the full bit_generator state to avoid version-specific
        # dict key differences across numpy releases.
        state_bytes = str(self.rng.bit_generator.state).encode()
        state_hash = hashlib.md5(state_bytes).hexdigest()[:8]
        key_str = (
            f"r{rows}_c{curves}_v{version}_w{wrap}_nf{null_fraction}"
            f"_nv{null_value}_s{step}_sd{start_depth}_fmt{fmt}_dlm{dlm}"
            f"_seed{state_hash}"
        )
        file_hash = hashlib.md5(key_str.encode()).hexdigest()[:12]
        tag = f"bench_{rows}r_{curves}c_v{version}"
        if wrap:
            tag += "_wrapped"
        if null_fraction > 0:
            tag += f"_null{int(null_fraction * 100)}pct"
        filename = f"{tag}_{file_hash}.las"
        path = _cache_dir() / filename

        if path.exists() and not force:
            return path

        curve_meta = self._pick_curves(curves)
        data = self._generate_data(
            rows, curves, start_depth, step, null_fraction, null_value
        )
        stop_depth = start_depth + (rows - 1) * step

        with open(path, "w", encoding="utf-8") as f:
            self._write_header(
                f,
                version=version,
                wrap=wrap,
                null_value=null_value,
                start=start_depth,
                stop=stop_depth,
                step=step,
                curves=curve_meta,
                dlm=dlm,
            )
            if wrap:
                self._write_data_wrapped(f, data, fmt=fmt)
            else:
                self._write_data_unwrapped(f, data, fmt=fmt)

        return path

    def make_batch(
        self,
        count: int = 500,
        rows: int = 1_000,
        curves: int = 8,
        **kwargs,
    ) -> list[Path]:
        """Generate *count* independent LAS files for batch-processing benchmarks.

        Each file gets a unique seed derived from the generator's base seed
        plus the file index, ensuring different data in every file.
        """
        base_state = self.rng.bit_generator.state
        paths = []
        for i in range(count):
            gen_i = Generator(seed=42_000 + i)
            path = gen_i.make(rows=rows, curves=curves, **kwargs)
            paths.append(path)
        return paths


# ---------------------------------------------------------------------------
# Pre-defined benchmark matrix
# ---------------------------------------------------------------------------

BENCHMARK_MATRIX = {
    # name: (rows, curves, extra kwargs)
    "tiny": (100, 4, {}),
    "small": (1_000, 8, {}),
    "medium": (100_000, 8, {}),
    "large": (1_000_000, 8, {}),
    "wide_small": (1_000, 200, {}),
    "wide_medium": (10_000, 200, {}),
    "wrapped_medium": (100_000, 30, {"wrap": True}),
    "nulls_light": (100_000, 8, {"null_fraction": 0.05}),
    "nulls_heavy": (100_000, 8, {"null_fraction": 0.30}),
    "single_curve": (1_000_000, 1, {}),
}


def generate_matrix(force: bool = False) -> dict[str, Path]:
    """Generate all files in the benchmark matrix and return {name: path}."""
    gen = Generator(seed=42)
    result = {}
    for name, (rows, curves, kwargs) in BENCHMARK_MATRIX.items():
        path = gen.make(rows=rows, curves=curves, force=force, **kwargs)
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  {name:20s}  {rows:>10,} rows × {curves:>3} curves  {size_mb:7.1f} MB  {path.name}")
        result[name] = path
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic LAS files for benchmarking")
    parser.add_argument("--rows", type=int, default=None, help="Single file: number of rows")
    parser.add_argument("--curves", type=int, default=8, help="Single file: number of curves")
    parser.add_argument("--version", type=float, default=2.0, help="LAS version")
    parser.add_argument("--wrap", action="store_true", help="Wrap data")
    parser.add_argument("--null-fraction", type=float, default=0.0, help="Fraction of nulls")
    parser.add_argument("--force", action="store_true", help="Regenerate even if cached")
    parser.add_argument("--cache-dir", type=str, default=None, help="Override cache directory")
    parser.add_argument("--matrix", action="store_true", help="Generate full benchmark matrix")
    parser.add_argument("--batch", type=int, default=None, help="Generate N batch files")
    args = parser.parse_args()

    if args.cache_dir:
        set_cache_dir(args.cache_dir)

    print(f"Cache directory: {_cache_dir()}")

    if args.matrix:
        print("\nGenerating benchmark matrix:")
        generate_matrix(force=args.force)
    elif args.batch:
        print(f"\nGenerating batch of {args.batch} files:")
        gen = Generator(seed=42)
        paths = gen.make_batch(count=args.batch, rows=args.rows or 1000, curves=args.curves)
        total_mb = sum(p.stat().st_size for p in paths) / (1024 * 1024)
        print(f"  {len(paths)} files, {total_mb:.1f} MB total")
    elif args.rows:
        gen = Generator(seed=42)
        path = gen.make(
            rows=args.rows,
            curves=args.curves,
            version=args.version,
            wrap=args.wrap,
            null_fraction=args.null_fraction,
            force=args.force,
        )
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"\nGenerated: {path}  ({size_mb:.1f} MB)")
    else:
        print("\nGenerating full benchmark matrix (default):")
        generate_matrix(force=args.force)


if __name__ == "__main__":
    main()
