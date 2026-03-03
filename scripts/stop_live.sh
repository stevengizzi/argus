#!/usr/bin/env bash
# Argus Trading System — Graceful Shutdown Script
#
# Sends SIGINT for graceful shutdown (positions closed, DB committed).
# Waits up to 60 seconds for clean exit, then force kills if necessary.
#
# Usage:
#   ./scripts/stop_live.sh

set -euo pipefail

# Navigate to project root (parent of scripts/)
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

LOG_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${LOG_DIR}/argus.pid"
UI_PID_FILE="${LOG_DIR}/ui.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# ─────────────────────────────────────────────────────────────
# Stop Command Center UI (if running)
# ─────────────────────────────────────────────────────────────
if [[ -f "$UI_PID_FILE" ]]; then
    UI_PID=$(cat "$UI_PID_FILE")
    if kill -0 "$UI_PID" 2>/dev/null; then
        log_info "Stopping Command Center UI (PID: $UI_PID)..."
        kill "$UI_PID" 2>/dev/null || true
        sleep 1
        if kill -0 "$UI_PID" 2>/dev/null; then
            kill -9 "$UI_PID" 2>/dev/null || true
        fi
        log_info "UI stopped"
    fi
    rm -f "$UI_PID_FILE"
fi

# ─────────────────────────────────────────────────────────────
# Check if ARGUS is running
# ─────────────────────────────────────────────────────────────
if [[ ! -f "$PID_FILE" ]]; then
    log_warn "No ARGUS process found (PID file missing: $PID_FILE)"
    exit 0
fi

ARGUS_PID=$(cat "$PID_FILE")

if ! kill -0 "$ARGUS_PID" 2>/dev/null; then
    log_warn "ARGUS process $ARGUS_PID is not running (stale PID file)"
    rm -f "$PID_FILE"
    exit 0
fi

# ─────────────────────────────────────────────────────────────
# Send graceful shutdown signal (SIGINT)
# ─────────────────────────────────────────────────────────────
log_info "Sending graceful shutdown to ARGUS (PID: $ARGUS_PID)..."
log_info "This will close all positions and commit database changes."

kill -INT "$ARGUS_PID"

# ─────────────────────────────────────────────────────────────
# Wait for clean exit (up to 60 seconds)
# ─────────────────────────────────────────────────────────────
TIMEOUT=60
for i in $(seq 1 $TIMEOUT); do
    if ! kill -0 "$ARGUS_PID" 2>/dev/null; then
        log_info "ARGUS stopped cleanly after ${i}s"
        rm -f "$PID_FILE"
        echo ""
        log_info "─────────────────────────────────────────────────────"
        log_info "ARGUS shutdown complete"
        log_info "─────────────────────────────────────────────────────"
        exit 0
    fi

    # Show progress every 5 seconds
    if (( i % 5 == 0 )); then
        log_info "  Waiting for graceful shutdown... (${i}/${TIMEOUT}s)"
    fi

    sleep 1
done

# ─────────────────────────────────────────────────────────────
# Force kill if graceful shutdown failed
# ─────────────────────────────────────────────────────────────
log_warn "ARGUS did not stop gracefully within ${TIMEOUT}s"
log_warn "Force killing process..."

kill -9 "$ARGUS_PID" 2>/dev/null || true
rm -f "$PID_FILE"

log_warn "ARGUS force killed. Check logs for any issues."
log_warn "  Log: ${LOG_DIR}/argus_$(date +%Y-%m-%d).log"
