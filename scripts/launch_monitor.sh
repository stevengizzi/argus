#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# Argus Trading System — Unattended Launch Monitor
# ═══════════════════════════════════════════════════════════════════════
#
# Schedules ARGUS launch before market open, then monitors health at
# key checkpoints with push notifications to your phone via ntfy.sh.
#
# Designed for days when you leave the house before market open and
# need ARGUS to start, run, and report status autonomously.
#
# Checkpoints:
#   1. POST-LAUNCH    — 3 min after ARGUS starts: API reachable?
#   2. PRE-MARKET     — 9:00 AM ET: Data service connected?
#   3. MARKET OPEN    — 9:35 AM ET: Candle data flowing?
#   4. PERIODIC       — Every 30 min during session: still healthy?
#   5. MARKET CLOSE   — 4:05 PM ET: Final status summary
#
# Usage:
#   ./scripts/launch_monitor.sh                     # Default: launch at 8:00 AM ET
#   ./scripts/launch_monitor.sh --launch-et 07:30   # Custom ET launch time
#   ./scripts/launch_monitor.sh --now               # Launch immediately + monitor
#   ./scripts/launch_monitor.sh --monitor-only      # Skip launch, monitor existing
#
# Prerequisites:
#   - ntfy.sh app on phone (or web push via ntfy.sh)
#   - .env file with all API keys
#   - IB Gateway running (or will be running by launch time)
#   - jq installed (apt install jq)
#
# Notifications:
#   Phone push via ntfy.sh. Subscribe to your topic in the ntfy app.
#   Free, no account needed: https://ntfy.sh
#
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

# ntfy.sh topic — subscribe to this in the ntfy app on your phone
# Override with ARGUS_NTFY_TOPIC env var
NTFY_TOPIC="${ARGUS_NTFY_TOPIC:-argus-alerts}"

# Default launch time in ET (Eastern Time)
LAUNCH_ET="${ARGUS_LAUNCH_ET:-08:00}"

# API connection
API_HOST="127.0.0.1"
API_PORT=8000
API_PASSWORD="${ARGUS_API_PASSWORD:-argus}"

# Periodic check interval during market hours (seconds)
PERIODIC_INTERVAL=1800  # 30 minutes

# Log file
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/launch_monitor_$(date +%Y%m%d).log"

# ── Argument Parsing ──────────────────────────────────────────────────

LAUNCH_NOW=false
MONITOR_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --launch-et)
            LAUNCH_ET="$2"
            shift 2
            ;;
        --now)
            LAUNCH_NOW=true
            shift
            ;;
        --monitor-only)
            MONITOR_ONLY=true
            shift
            ;;
        --ntfy-topic)
            NTFY_TOPIC="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--launch-et HH:MM] [--now] [--monitor-only] [--ntfy-topic TOPIC]"
            echo ""
            echo "Options:"
            echo "  --launch-et HH:MM   Launch time in ET (default: 08:00)"
            echo "  --now               Launch ARGUS immediately, then monitor"
            echo "  --monitor-only      Don't launch — just monitor an already-running instance"
            echo "  --ntfy-topic TOPIC  ntfy.sh topic (default: argus-alerts)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

# Convert ET time (HH:MM) to local epoch (handles SAST→ET offset)
et_to_local_epoch() {
    local et_time="$1"  # HH:MM format
    local today
    today=$(date +%Y-%m-%d)
    # Use Python for reliable timezone conversion
    python3 -c "
from datetime import datetime
from zoneinfo import ZoneInfo
et = ZoneInfo('America/New_York')
local = ZoneInfo('$(timedatectl show -p Timezone --value 2>/dev/null || echo 'Africa/Johannesburg')')
dt_et = datetime.strptime('${today} ${et_time}', '%Y-%m-%d %H:%M').replace(tzinfo=et)
dt_local = dt_et.astimezone(local)
print(int(dt_local.timestamp()))
"
}

# Get current time as ET string (HH:MM)
now_et() {
    python3 -c "
from datetime import datetime
from zoneinfo import ZoneInfo
print(datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M'))
"
}

# Get current epoch
now_epoch() {
    date +%s
}

# Sleep until a specific ET time. Returns immediately if time has passed.
sleep_until_et() {
    local target_et="$1"
    local label="$2"
    local target_epoch
    target_epoch=$(et_to_local_epoch "$target_et")
    local now
    now=$(now_epoch)
    local wait_secs=$(( target_epoch - now ))

    if (( wait_secs <= 0 )); then
        log "Target time $target_et ET already passed — proceeding immediately"
        return 0
    fi

    local wait_mins=$(( wait_secs / 60 ))
    log "Sleeping ${wait_mins}m until ${target_et} ET ($label)..."
    sleep "$wait_secs"
}

# ── Notification ──────────────────────────────────────────────────────

ntfy() {
    local title="$1"
    local msg="$2"
    local priority="${3:-default}"
    local tags="${4:-}"

    local extra_headers=()
    [[ -n "$tags" ]] && extra_headers+=(-H "Tags: $tags")

    curl -s \
        -H "Title: $title" \
        -H "Priority: $priority" \
        "${extra_headers[@]}" \
        -d "$msg" \
        "https://ntfy.sh/$NTFY_TOPIC" > /dev/null 2>&1 || true

    log "NTFY [$priority]: $title — $msg"
}

# ── Health Check API ──────────────────────────────────────────────────

# Cache JWT token (valid 24h, so one fetch per script run is fine)
JWT_TOKEN=""

get_token() {
    if [[ -n "$JWT_TOKEN" ]]; then
        echo "$JWT_TOKEN"
        return
    fi

    local resp
    resp=$(curl -s --max-time 5 -X POST \
        "http://${API_HOST}:${API_PORT}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"password\": \"${API_PASSWORD}\"}" 2>/dev/null) || true

    JWT_TOKEN=$(echo "$resp" | jq -r '.access_token // empty' 2>/dev/null) || true
    echo "$JWT_TOKEN"
}

# Fetch health JSON. Returns empty string on failure.
fetch_health() {
    local token
    token=$(get_token)
    if [[ -z "$token" ]]; then
        echo ""
        return
    fi

    curl -s --max-time 10 \
        -H "Authorization: Bearer $token" \
        "http://${API_HOST}:${API_PORT}/api/v1/health" 2>/dev/null || echo ""
}

# Check if ARGUS process is alive
is_argus_running() {
    local pid_file="${LOG_DIR}/argus.pid"
    if [[ ! -f "$pid_file" ]]; then
        return 1
    fi
    local pid
    pid=$(cat "$pid_file")
    kill -0 "$pid" 2>/dev/null
}

# Parse health JSON and return structured summary
parse_health() {
    local health="$1"
    if [[ -z "$health" ]]; then
        echo "UNREACHABLE"
        return
    fi

    local status
    status=$(echo "$health" | jq -r '.status // "unknown"')
    local uptime
    uptime=$(echo "$health" | jq -r '.uptime_seconds // 0')
    local last_data
    last_data=$(echo "$health" | jq -r '.last_data_received // "none"')
    local components
    components=$(echo "$health" | jq -r '
        [.components | to_entries[] |
         select(.value.status != "healthy") |
         "\(.key)=\(.value.status)"] | join(", ")' 2>/dev/null) || components=""

    local uptime_min=$(( uptime / 60 ))

    if [[ -z "$components" ]]; then
        echo "OK|${status}|${uptime_min}m|data=${last_data}|all components healthy"
    else
        echo "DEGRADED|${status}|${uptime_min}m|data=${last_data}|issues: ${components}"
    fi
}

# Check recent log for critical errors (last N lines)
check_log_errors() {
    local argus_log="${LOG_DIR}/argus_$(date +%Y-%m-%d).log"
    if [[ ! -f "$argus_log" ]]; then
        echo ""
        return
    fi
    # Look for CRITICAL or specific failure patterns in last 50 lines
    tail -50 "$argus_log" | grep -i "CRITICAL\|max reconnection retries\|Data feed is DEAD\|Failed to start" | tail -3 || echo ""
}

# ── Checkpoint Functions ──────────────────────────────────────────────

checkpoint_post_launch() {
    log "═══ CHECKPOINT: POST-LAUNCH (3 min after start) ═══"

    # First check: is the process even alive?
    if ! is_argus_running; then
        ntfy "🔴 ARGUS CRASHED ON STARTUP" \
             "Process not running 3 min after launch. Check log: $LOG_FILE" \
             "urgent" "rotating_light"
        return 1
    fi

    # Second check: health endpoint
    local health
    health=$(fetch_health)
    local parsed
    parsed=$(parse_health "$health")
    local result="${parsed%%|*}"

    case "$result" in
        OK)
            ntfy "✅ ARGUS Started" \
                 "$(echo "$parsed" | tr '|' ' ')" \
                 "default" "white_check_mark"
            ;;
        DEGRADED)
            ntfy "⚠️ ARGUS Started (Degraded)" \
                 "$(echo "$parsed" | tr '|' ' ')" \
                 "high" "warning"
            ;;
        UNREACHABLE)
            # Process is alive but API isn't responding — might still be starting
            ntfy "⚠️ ARGUS API Unreachable" \
                 "Process alive but health endpoint not responding. May still be in startup. Will recheck at market open." \
                 "high" "warning"
            ;;
    esac
}

checkpoint_pre_market() {
    log "═══ CHECKPOINT: PRE-MARKET (9:00 AM ET) ═══"

    local health
    health=$(fetch_health)
    local parsed
    parsed=$(parse_health "$health")
    local result="${parsed%%|*}"

    if [[ "$result" == "UNREACHABLE" ]]; then
        if ! is_argus_running; then
            ntfy "🔴 ARGUS DOWN BEFORE MARKET" \
                 "Process died before market open. Manual intervention needed." \
                 "urgent" "rotating_light"
        else
            ntfy "⚠️ ARGUS API Down Pre-Market" \
                 "Process alive but API unreachable. Check logs." \
                 "urgent" "warning"
        fi
        return 1
    fi

    # Check for critical log errors
    local errors
    errors=$(check_log_errors)
    if [[ -n "$errors" ]]; then
        ntfy "⚠️ ARGUS Pre-Market Warnings" \
             "Critical log entries detected: ${errors:0:200}" \
             "high" "warning"
    fi

    log "Pre-market check: $parsed"
}

checkpoint_market_open() {
    log "═══ CHECKPOINT: MARKET OPEN (9:35 AM ET) ═══"

    local health
    health=$(fetch_health)

    if [[ -z "$health" ]]; then
        if ! is_argus_running; then
            ntfy "🔴 ARGUS DOWN AT MARKET OPEN" \
                 "System is not running. No trading will occur today." \
                 "urgent" "rotating_light"
        else
            ntfy "🔴 ARGUS API DOWN AT OPEN" \
                 "Process alive but API unreachable at market open." \
                 "urgent" "rotating_light"
        fi
        return 1
    fi

    local status
    status=$(echo "$health" | jq -r '.status // "unknown"')
    local last_data
    last_data=$(echo "$health" | jq -r '.last_data_received // "none"')
    local uptime
    uptime=$(echo "$health" | jq -r '.uptime_seconds // 0')
    local uptime_min=$(( uptime / 60 ))

    # Critical check: is data flowing?
    if [[ "$last_data" == "none" ]] || [[ "$last_data" == "null" ]]; then
        ntfy "🔴 NO DATA AT MARKET OPEN" \
             "ARGUS is ${status} (up ${uptime_min}m) but last_data_received is null. Databento may be disconnected. Strategies will not fire." \
             "urgent" "rotating_light"
        return 1
    fi

    # Check component health
    local unhealthy_count
    unhealthy_count=$(echo "$health" | jq '[.components | to_entries[] | select(.value.status != "healthy")] | length')

    if (( unhealthy_count == 0 )); then
        ntfy "✅ Market Open — All Systems Go" \
             "Status: ${status}, up ${uptime_min}m. Data flowing (last: ${last_data}). All components healthy." \
             "default" "white_check_mark,chart_with_upwards_trend"
    else
        local issues
        issues=$(echo "$health" | jq -r '[.components | to_entries[] | select(.value.status != "healthy") | "\(.key): \(.value.status)"] | join(", ")')
        ntfy "⚠️ Market Open — Degraded" \
             "Status: ${status}, up ${uptime_min}m. Data flowing. Issues: ${issues}" \
             "high" "warning"
    fi
}

checkpoint_periodic() {
    local check_num="$1"
    log "═══ CHECKPOINT: PERIODIC #${check_num} ═══"

    local health
    health=$(fetch_health)

    if [[ -z "$health" ]]; then
        if ! is_argus_running; then
            ntfy "🔴 ARGUS DOWN MID-SESSION" \
                 "System crashed during market hours (check #${check_num})." \
                 "urgent" "rotating_light"
            return 1
        fi
        # Process alive but API down — less critical, might be transient
        log "Periodic check #${check_num}: API unreachable but process alive"
        return 0
    fi

    local status
    status=$(echo "$health" | jq -r '.status // "unknown"')
    local last_data
    last_data=$(echo "$health" | jq -r '.last_data_received // "none"')

    # Only notify if something is wrong — don't spam healthy status every 30 min
    if [[ "$status" != "healthy" ]] || [[ "$last_data" == "none" ]] || [[ "$last_data" == "null" ]]; then
        ntfy "⚠️ ARGUS Mid-Session Issue" \
             "Check #${check_num}: status=${status}, last_data=${last_data}" \
             "high" "warning"
    fi

    # Check for critical log errors
    local errors
    errors=$(check_log_errors)
    if [[ -n "$errors" ]]; then
        ntfy "⚠️ Critical Errors in Log" \
             "Check #${check_num}: ${errors:0:200}" \
             "high" "warning"
    fi

    log "Periodic check #${check_num}: status=${status}, data=${last_data}"
}

checkpoint_market_close() {
    log "═══ CHECKPOINT: MARKET CLOSE (4:05 PM ET) ═══"

    local health
    health=$(fetch_health)

    if [[ -z "$health" ]]; then
        ntfy "📊 ARGUS EOD — System Down" \
             "API unreachable at market close. Check logs for session summary." \
             "default" "bar_chart"
        return
    fi

    local status
    status=$(echo "$health" | jq -r '.status // "unknown"')
    local uptime
    uptime=$(echo "$health" | jq -r '.uptime_seconds // 0')
    local uptime_hrs=$(( uptime / 3600 ))
    local uptime_min=$(( (uptime % 3600) / 60 ))
    local last_data
    last_data=$(echo "$health" | jq -r '.last_data_received // "none"')
    local last_trade
    last_trade=$(echo "$health" | jq -r '.last_trade // "none"')

    ntfy "📊 ARGUS EOD Summary" \
         "Status: ${status}. Uptime: ${uptime_hrs}h${uptime_min}m. Last data: ${last_data}. Last trade: ${last_trade}. Run debrief when home." \
         "default" "bar_chart"
}

# ── Main Orchestration ────────────────────────────────────────────────

main() {
    log "═══════════════════════════════════════════════════"
    log "ARGUS Launch Monitor — Starting"
    log "═══════════════════════════════════════════════════"
    log "Project root:  $PROJECT_ROOT"
    log "ntfy topic:    $NTFY_TOPIC"
    log "Launch time:   $LAUNCH_ET ET"
    log "Launch now:    $LAUNCH_NOW"
    log "Monitor only:  $MONITOR_ONLY"
    log "Log file:      $LOG_FILE"
    log ""

    # ── Step 0: Validate prerequisites ──
    if ! command -v jq &>/dev/null; then
        echo "ERROR: jq is required. Install with: sudo apt install jq"
        exit 1
    fi

    if ! command -v curl &>/dev/null; then
        echo "ERROR: curl is required."
        exit 1
    fi

    # Validate ntfy.sh is reachable
    if ! curl -s --max-time 5 "https://ntfy.sh/$NTFY_TOPIC/json?poll=1" > /dev/null 2>&1; then
        log "WARNING: ntfy.sh unreachable — notifications may not work"
    fi

    # ── Step 1: Launch ARGUS (unless --monitor-only) ──
    if [[ "$MONITOR_ONLY" == "true" ]]; then
        log "Monitor-only mode — skipping launch"
        if ! is_argus_running; then
            log "WARNING: ARGUS is not running. Health checks will fail."
            ntfy "⚠️ Monitor Started (No ARGUS)" \
                 "Monitor-only mode but ARGUS process not found." \
                 "high" "warning"
        else
            ntfy "📡 Monitor Active" \
                 "Monitoring existing ARGUS instance. Checkpoints: pre-market, open, periodic, close." \
                 "low" "satellite"
        fi
    else
        # Wait for launch time (unless --now)
        if [[ "$LAUNCH_NOW" == "true" ]]; then
            log "Launching ARGUS immediately (--now flag)"
        else
            local now_et_str
            now_et_str=$(now_et)
            log "Current time: ${now_et_str} ET. Launch scheduled for ${LAUNCH_ET} ET."

            ntfy "📡 ARGUS Monitor Active" \
                 "Launch scheduled for ${LAUNCH_ET} ET. Checkpoints: post-launch, pre-market (9:00), open (9:35), periodic (30m), close (16:05). Go enjoy your day." \
                 "low" "satellite"

            sleep_until_et "$LAUNCH_ET" "ARGUS launch"
        fi

        # Pre-flight: check if already running
        if is_argus_running; then
            log "ARGUS is already running — skipping launch"
            ntfy "ℹ️ ARGUS Already Running" \
                 "Skipped launch — existing instance detected. Proceeding to monitoring." \
                 "default" "information_source"
        else
            log "Launching ARGUS via start_live.sh..."
            # Use start_live.sh which has all the pre-flight checks
            if bash "${PROJECT_ROOT}/scripts/start_live.sh" >> "$LOG_FILE" 2>&1; then
                log "start_live.sh completed successfully"
            else
                local exit_code=$?
                log "start_live.sh failed with exit code $exit_code"
                ntfy "🔴 ARGUS LAUNCH FAILED" \
                     "start_live.sh exited with code ${exit_code}. Pre-flight check may have failed (IB Gateway? API keys?). Check log: ${LOG_FILE}" \
                     "urgent" "rotating_light"
                # Don't exit — continue monitoring in case it was a transient failure
                # and the user fixes it remotely
            fi
        fi

        # Post-launch health check (wait 3 min for startup to complete)
        log "Waiting 180s for ARGUS startup to complete..."
        sleep 180
        checkpoint_post_launch
    fi

    # ── Step 2: Pre-market check (9:00 AM ET) ──
    sleep_until_et "09:00" "pre-market check"
    checkpoint_pre_market

    # ── Step 3: Market open check (9:35 AM ET) ──
    sleep_until_et "09:35" "market open check"
    checkpoint_market_open

    # ── Step 4: Periodic checks during market hours ──
    local check_num=0
    while true; do
        # Check if we've passed market close (16:00 ET)
        local current_et
        current_et=$(now_et)
        local current_hour="${current_et%%:*}"
        local current_min="${current_et##*:}"
        local current_minutes=$(( current_hour * 60 + current_min ))

        # 16:00 ET = 960 minutes
        if (( current_minutes >= 960 )); then
            break
        fi

        sleep "$PERIODIC_INTERVAL"
        check_num=$(( check_num + 1 ))
        checkpoint_periodic "$check_num"
    done

    # ── Step 5: Market close summary (4:05 PM ET) ──
    sleep_until_et "16:05" "market close summary"
    checkpoint_market_close

    log ""
    log "═══════════════════════════════════════════════════"
    log "ARGUS Launch Monitor — Complete"
    log "═══════════════════════════════════════════════════"
    log ""
    log "Market session ended. ARGUS is still running (EOD flatten"
    log "will close positions automatically). Run the debrief protocol"
    log "when you get home."
}

# ── Entry Point ───────────────────────────────────────────────────────

# Trap Ctrl+C for clean exit
trap 'log "Monitor interrupted by user"; exit 0' INT TERM

main "$@"
