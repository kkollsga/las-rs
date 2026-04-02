#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Benchmark runner for las_rs
#
# Usage:
#   ./benchmarks/run.sh 0.1.0                    # tier1+tier2 (quick, ~2min)
#   ./benchmarks/run.sh 0.1.0 --full             # all tiers (~10min+)
#   ./benchmarks/run.sh 0.1.0 --quick            # tier1 only (~30s)
#   ./benchmarks/run.sh 0.1.0 --suite read       # specific suite
#   ./benchmarks/run.sh 0.1.0 --suite lasio      # lasio baseline
#   ./benchmarks/run.sh --generate-only           # just generate test files
#   ./benchmarks/run.sh --report                  # print latest results
#   ./benchmarks/run.sh --report --compare V1 V2  # compare versions
#   ./benchmarks/run.sh --report --vs-lasio V1    # compare vs lasio
#   ./benchmarks/run.sh --report --markdown       # as markdown
#   ./benchmarks/run.sh --report --charts         # generate PNG charts
#
# Tiers:
#   tier1  Quick (~30s)   — tiny/small files, fast ops. During development.
#   tier2  Medium (~2min) — medium files, most features. Before commits.
#   tier3  Full (~10min+) — large files, batch, wrapped. Before releases.
#
# Results are UPSERTED: re-running a subset only updates those benchmarks.
# ---------------------------------------------------------------------------

set -euo pipefail
cd "$(dirname "$0")/.."

JSON_DIR="benchmarks/results"
mkdir -p "$JSON_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ---- Report mode ----
if [[ "${1:-}" == "--report" ]]; then
    shift
    python benchmarks/report.py "$@"
    exit 0
fi

# ---- Generate-only mode ----
if [[ "${1:-}" == "--generate-only" ]]; then
    python -m benchmarks.generate --matrix
    exit 0
fi

# ---- Benchmark mode: require version ----
VERSION="${1:?Usage: $0 VERSION [--quick|--full|--suite NAME]}"
shift

TIER_FILTER="-m tier1 or tier2"   # default: quick + medium
SUITE="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)  TIER_FILTER="-m tier1"; shift ;;
        --full)   TIER_FILTER=""; shift ;;
        --suite)  SUITE="$2"; shift 2 ;;
        *)        echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Generate benchmark files
echo "=== Generating synthetic LAS files ==="
python -m benchmarks.generate --matrix
echo ""

run_and_collect() {
    local label="$1"
    local library="$2"
    shift 2
    local json_file="$JSON_DIR/${label}_${TIMESTAMP}.json"

    echo "=== Running: $label (library=$library) ==="
    pytest "$@" \
        $TIER_FILTER \
        --benchmark-only \
        --benchmark-json="$json_file" \
        --benchmark-columns=min,max,mean,stddev,median,ops \
        --benchmark-group-by=group \
        --benchmark-sort=fullname \
        --benchmark-warmup=on \
        -v || true

    if [[ -f "$json_file" ]]; then
        echo ""
        python benchmarks/collect.py "$json_file" --version "$VERSION" --library "$library"
    fi
}

case "$SUITE" in
    read)    run_and_collect "read"    "las_rs" benchmarks/bench_read.py ;;
    write)   run_and_collect "write"   "las_rs" benchmarks/bench_write.py ;;
    ops)     run_and_collect "ops"     "las_rs" benchmarks/bench_ops.py ;;
    compare) run_and_collect "compare" "las_rs" benchmarks/bench_compare.py ;;
    batch)   run_and_collect "batch"   "las_rs" benchmarks/bench_batch.py ;;
    lasio)   run_and_collect "lasio"   "lasio"  benchmarks/bench_lasio_baseline.py ;;
    all)
        run_and_collect "las_rs"  "las_rs" benchmarks/bench_read.py benchmarks/bench_write.py benchmarks/bench_ops.py
        ;;
    *)
        echo "Unknown suite: $SUITE"
        echo "Valid: read, write, ops, compare, batch, lasio, all"
        exit 1
        ;;
esac

echo ""
echo "=== Results for $VERSION ==="
python benchmarks/report.py --version "$VERSION"
