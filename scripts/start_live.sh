#!/usr/bin/env bash
# Argus Trading System — Live Mode Startup Script
#
# Pre-flight checks:
#   1. .env file exists
#   2. IB Gateway is running (port 4002)
#   3. DATABENTO_API_KEY is set
#   4. No existing ARGUS process running
#
# Usage:
#   ./scripts/start_live.sh              # Start engine only
#   ./scripts/start_live.sh --with-ui    # Start engine + Command Center UI

set -euo pipefail

# Navigate to project root (parent of scripts/)
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

LOG_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${LOG_DIR}/argus.pid"
UI_PID_FILE="${LOG_DIR}/ui.pid"
LOG_FILE="${LOG_DIR}/argus_$(date +%Y-%m-%d).log"

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
# Pre-flight Check 1: .env file exists
# ─────────────────────────────────────────────────────────────
log_info "Pre-flight check 1/4: Checking .env file..."
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    log_error ".env file not found at ${PROJECT_ROOT}/.env"
    log_error "Copy .env.example to .env and configure your API keys."
    exit 1
fi
log_info "  .env file found"

# Load .env to check variables
set -a
source "${PROJECT_ROOT}/.env"
set +a

# ─────────────────────────────────────────────────────────────
# Pre-flight Check 2: IB Gateway is running
# ─────────────────────────────────────────────────────────────
log_info "Pre-flight check 2/4: Checking IB Gateway (port 4002)..."
IB_PORT="${IBKR_PORT:-4002}"
if ! nc -z 127.0.0.1 "$IB_PORT" 2>/dev/null; then
    log_error "IB Gateway is not running on port $IB_PORT"
    log_error "Start IB Gateway and ensure it's configured for paper trading."
    log_error "  - API Settings: Enable ActiveX and Socket Clients"
    log_error "  - Socket port: $IB_PORT"
    log_error "  - Trusted IPs: 127.0.0.1"
    exit 1
fi
log_info "  IB Gateway reachable on port $IB_PORT"

# ─────────────────────────────────────────────────────────────
# Pre-flight Check 3: DATABENTO_API_KEY is set
# ─────────────────────────────────────────────────────────────
log_info "Pre-flight check 3/4: Checking DATABENTO_API_KEY..."
if [[ -z "${DATABENTO_API_KEY:-}" ]]; then
    log_error "DATABENTO_API_KEY is not set in .env"
    log_error "Add DATABENTO_API_KEY=db-xxx to your .env file."
    exit 1
fi
log_info "  DATABENTO_API_KEY is set"

# ─────────────────────────────────────────────────────────────
# Pre-flight Check 4: No existing ARGUS process
# ─────────────────────────────────────────────────────────────
log_info "Pre-flight check 4/4: Checking for existing ARGUS process..."
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log_error "ARGUS is already running (PID: $OLD_PID)"
        log_error "Stop it first with: ./scripts/stop_live.sh"
        exit 1
    else
        log_warn "Stale PID file found. Removing..."
        rm -f "$PID_FILE"
    fi
fi
log_info "  No existing process found"

# ─────────────────────────────────────────────────────────────
# Create log directory
# ─────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

# ─────────────────────────────────────────────────────────────
# Start ARGUS
# ─────────────────────────────────────────────────────────────
log_info "Starting ARGUS in live mode..."
log_info "  Config: config/system_live.yaml"
log_info "  Log: $LOG_FILE"

# Start ARGUS with nohup so it survives terminal close
nohup python -m argus.main --config config/system_live.yaml \
    >> "$LOG_FILE" 2>&1 &

ARGUS_PID=$!
echo "$ARGUS_PID" > "$PID_FILE"

# Wait a moment and verify it started
sleep 2
if ! kill -0 "$ARGUS_PID" 2>/dev/null; then
    log_error "ARGUS failed to start. Check log: $LOG_FILE"
    rm -f "$PID_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi

log_info "ARGUS started successfully (PID: $ARGUS_PID)"

# ─────────────────────────────────────────────────────────────
# Optionally start Command Center UI
# ─────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--with-ui" ]]; then
    log_info "Starting Command Center UI..."

    if [[ ! -d "${PROJECT_ROOT}/argus/ui" ]]; then
        log_error "UI directory not found at ${PROJECT_ROOT}/argus/ui"
        exit 1
    fi

    cd "${PROJECT_ROOT}/argus/ui"

    # Check if npm is available
    if ! command -v npm &>/dev/null; then
        log_error "npm not found. Install Node.js to run the UI."
        exit 1
    fi

    # Start UI dev server
    nohup npm run dev >> "${LOG_DIR}/ui_$(date +%Y-%m-%d).log" 2>&1 &
    UI_PID=$!
    echo "$UI_PID" > "$UI_PID_FILE"

    sleep 2
    if ! kill -0 "$UI_PID" 2>/dev/null; then
        log_error "UI failed to start. Check log: ${LOG_DIR}/ui_$(date +%Y-%m-%d).log"
        rm -f "$UI_PID_FILE"
    else
        log_info "Command Center UI started (PID: $UI_PID)"
    fi

    cd "$PROJECT_ROOT"
fi

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
log_info "─────────────────────────────────────────────────────"
log_info "ARGUS is running"
log_info "  PID: $ARGUS_PID"
log_info "  Log: $LOG_FILE"
if [[ -f "$UI_PID_FILE" ]]; then
    log_info "  UI:  http://localhost:5173"
fi
log_info ""
log_info "Commands:"
log_info "  View logs:  tail -f $LOG_FILE"
log_info "  Stop:       ./scripts/stop_live.sh"
log_info "─────────────────────────────────────────────────────"
