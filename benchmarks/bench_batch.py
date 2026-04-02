"""Benchmarks: Batch file processing.

Measures the speedup from processing many LAS files in parallel.
This is where las_rs's rayon-based parallelism should shine compared
to lasio's GIL-bound sequential processing.

Run with: pytest benchmarks/bench_batch.py --benchmark-only -v
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

import pytest

import las_rs

try:
    import lasio

    HAS_LASIO = True
except ImportError:
    HAS_LASIO = False

skip_no_lasio = pytest.mark.skipif(not HAS_LASIO, reason="lasio not installed")


# ---------------------------------------------------------------------------
# Sequential reads
# ---------------------------------------------------------------------------


@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-sequential")
def test_las_rs_sequential_500(benchmark, batch_files):
    """Read 500 files sequentially with las_rs."""

    def go():
        results = []
        for path in batch_files:
            results.append(las_rs.read(str(path)))
        return results

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-sequential")
def test_lasio_sequential_500(benchmark, batch_files):
    """Read 500 files sequentially with lasio."""

    def go():
        results = []
        for path in batch_files:
            results.append(lasio.read(str(path)))
        return results

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


# ---------------------------------------------------------------------------
# Parallel reads (Python threading — tests GIL release)
# ---------------------------------------------------------------------------


@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-threaded")
def test_las_rs_threaded_500(benchmark, batch_files):
    """Read 500 files with ThreadPoolExecutor — tests GIL release in las_rs."""

    def go():
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(las_rs.read, str(p)) for p in batch_files]
            return [f.result() for f in concurrent.futures.as_completed(futures)]

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-threaded")
def test_lasio_threaded_500(benchmark, batch_files):
    """Read 500 files with ThreadPoolExecutor — lasio holds the GIL."""

    def go():
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(lasio.read, str(p)) for p in batch_files]
            return [f.result() for f in concurrent.futures.as_completed(futures)]

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


# ---------------------------------------------------------------------------
# Parallel reads (multiprocessing — both libraries benefit)
# ---------------------------------------------------------------------------


def _read_las_rs(path_str: str):
    """Top-level function for pickling in multiprocessing."""
    return las_rs.read(path_str)


def _read_lasio(path_str: str):
    """Top-level function for pickling in multiprocessing."""
    return lasio.read(path_str)


@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-multiprocess")
def test_las_rs_multiprocess_500(benchmark, batch_files):
    """Read 500 files with ProcessPoolExecutor."""

    def go():
        paths_str = [str(p) for p in batch_files]
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
            return list(pool.map(_read_las_rs, paths_str, chunksize=32))

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


@skip_no_lasio
@pytest.mark.tier3
@pytest.mark.benchmark(group="batch-multiprocess")
def test_lasio_multiprocess_500(benchmark, batch_files):
    """Read 500 files with ProcessPoolExecutor."""

    def go():
        paths_str = [str(p) for p in batch_files]
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
            return list(pool.map(_read_lasio, paths_str, chunksize=32))

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


# ---------------------------------------------------------------------------
# Batch read+write pipeline
# ---------------------------------------------------------------------------


@pytest.mark.tier2
@pytest.mark.benchmark(group="batch-pipeline")
def test_las_rs_pipeline_100(benchmark, batch_files):
    """Read 100 files → add a curve → write back (pipeline throughput)."""
    import numpy as np
    from io import StringIO

    files = batch_files[:100]

    def go():
        outputs = []
        for path in files:
            las = las_rs.read(str(path))
            fake = np.zeros(len(las.index))
            las.append_curve("SYNTH", fake, unit="NONE", descr="Benchmark synthetic")
            s = StringIO()
            las.write(s)
            outputs.append(s.getvalue())
        return outputs

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)


@skip_no_lasio
@pytest.mark.tier2
@pytest.mark.benchmark(group="batch-pipeline")
def test_lasio_pipeline_100(benchmark, batch_files):
    """Read 100 files → add a curve → write back (pipeline throughput)."""
    import numpy as np
    from io import StringIO

    files = batch_files[:100]

    def go():
        outputs = []
        for path in files:
            las = lasio.read(str(path))
            fake = np.zeros(len(las.index))
            las.append_curve("SYNTH", fake, unit="NONE", descr="Benchmark synthetic")
            s = StringIO()
            las.write(s)
            outputs.append(s.getvalue())
        return outputs

    benchmark.pedantic(go, rounds=3, warmup_rounds=1)
