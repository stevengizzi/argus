#!/usr/bin/env bash
# run_sweep_batch.sh — Orchestrate overnight full-universe pattern sweeps.
#
# Runs in three phases:
#   1. Symbol resolution (resolve_sweep_symbols.py — single DuckDB open)
#   2. Validation: confirm each symbol file exists and report counts
#   3. Pattern sweeps with per-pattern error isolation
#
# Usage:
#   ./scripts/run_sweep_batch.sh                  # all patterns
#   ./scripts/run_sweep_batch.sh micro_pullback hod_break  # subset
#
# Environment overrides:
#   CACHE_DIR, DATE_RANGE, WORKERS
#
# Sprint 31.75, Session 3b.

set -euo pipefail

# --- Configuration ---
CACHE_DIR="${CACHE_DIR:-data/databento_cache}"
DATE_RANGE="${DATE_RANGE:-2025-01-01,2025-12-31}"
WORKERS="${WORKERS:-2}"
LOG_DIR="data/sweep_logs"
PERSIST_DB="data/historical_query.duckdb"
PATTERNS=(
    micro_pullback
    dip_and_rip
    hod_break
    abcd
    narrow_range_breakout
    vwap_bounce
    flat_top_breakout
    bull_flag
    gap_and_go
    premarket_high_break
)

# Support optional positional args to run a subset of patterns
if [[ $# -gt 0 ]]; then
    PATTERNS=("$@")
fi

# --- Pre-flight checks ---
if [[ ! -d "$CACHE_DIR" ]]; then
    echo "ERROR: Cache directory does not exist: $CACHE_DIR"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found in PATH"
    exit 1
fi

mkdir -p "$LOG_DIR"

echo "=== ARGUS Overnight Sweep Batch ==="
echo "  Cache dir:  $CACHE_DIR"
echo "  Date range: $DATE_RANGE"
echo "  Workers:    $WORKERS"
echo "  Patterns:   ${#PATTERNS[@]}"
echo "  Log dir:    $LOG_DIR"
echo ""

# --- Phase 1: Symbol resolution ---
echo "=== Phase 1: Resolving symbols ==="
python3 scripts/resolve_sweep_symbols.py \
    --all-patterns \
    --cache-dir "$CACHE_DIR" \
    --date-range "$DATE_RANGE" \
    --persist-db "$PERSIST_DB" \
    --output-dir "$LOG_DIR"

echo ""

# --- Phase 2: Validate symbol files ---
echo "=== Phase 2: Validating symbol files ==="
for pattern in "${PATTERNS[@]}"; do
    symfile="$LOG_DIR/symbols_${pattern}.txt"
    if [[ ! -f "$symfile" ]]; then
        echo "  WARNING: No symbol file for $pattern — will be skipped in Phase 3"
        continue
    fi
    count=$(wc -l < "$symfile" | tr -d ' ')
    echo "  $pattern: $count symbols"
done

echo ""

# --- Phase 3: Run sweeps with per-pattern error isolation ---
echo "=== Phase 3: Running sweeps ==="
for pattern in "${PATTERNS[@]}"; do
    symfile="$LOG_DIR/symbols_${pattern}.txt"
    [[ ! -f "$symfile" ]] && continue

    logfile="$LOG_DIR/sweep_${pattern}_$(date +%Y%m%d).log"
    progress_file="$LOG_DIR/${pattern}_progress.json"

    echo "=== Starting: $pattern ==="
    python3 scripts/run_experiment.py \
        --pattern "$pattern" \
        --cache-dir "$CACHE_DIR" \
        --symbols "@${symfile}" \
        --date-range "$DATE_RANGE" \
        --workers "$WORKERS" \
        > "$logfile" 2>&1 || {
        echo "FAILED: $pattern (see $logfile)"
        echo "{\"status\": \"failed\", \"pattern\": \"$pattern\"}" > "$progress_file"
        continue
    }
    echo "COMPLETED: $pattern"
    echo "{\"status\": \"completed\", \"pattern\": \"$pattern\"}" > "$progress_file"
done

echo ""

# --- Phase 4: Completion sentinel ---
echo "{\"completed\": true, \"timestamp\": \"$(date -Iseconds)\"}" \
    > "$LOG_DIR/batch_complete.json"
echo "=== Batch complete ==="
