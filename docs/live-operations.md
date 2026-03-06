# ARGUS Live Operations Guide

> *Version 1.0 | March 3, 2026*
> *Operational reference for running ARGUS with Databento + IBKR paper trading*

---

## 1. Daily Startup Procedure

### Step 1: Launch IB Gateway

1. Open IB Gateway application
2. Select "Paper Trading" login mode
3. Log in with your paper trading credentials
4. Verify the account number shows **"DU"** prefix (paper account indicator)
5. Ensure API Settings are correct:
   - Enable ActiveX and Socket Clients: **checked**
   - Socket port: **4002** (paper) or **4001** (live)
   - Read-Only API: **unchecked**
   - Allow connections from localhost only: **checked**

### Step 2: Verify Environment Configuration

Ensure `.env` contains:
```bash
# Databento
DATABENTO_API_KEY=your_key_here

# IBKR (usually uses localhost, no credentials in env)
# Port configured in config/brokers.yaml

# API JWT Secret
ARGUS_JWT_SECRET=your_secure_secret_here

# FMP Scanner (Sprint 21.7+)
FMP_API_KEY=your_fmp_api_key_here

# Claude API for AI Copilot (Sprint 22+)
# Optional — AI features disabled if unset
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

### Step 3: Start ARGUS

```bash
# Backend only
./scripts/start_live.sh

# Backend + Command Center UI
./scripts/start_live.sh --with-ui
```

### Step 4: Verify Startup

Watch the terminal for the 12-phase startup sequence:
```
Phase 1/12: Loading configuration...
Phase 2/12: Initializing database...
Phase 3/12: Connecting to broker...
Phase 4/12: Initializing health monitor...
Phase 5/12: Initializing risk manager...
Phase 6/12: Connecting to data service...
Phase 7/12: Initializing scanner...
Phase 8/12: Loading strategies...
Phase 9/12: Initializing orchestrator...
Phase 10/12: Initializing order manager...
Phase 11/12: Starting data streams...
Phase 12/12: Starting API server...

ARGUS started successfully. System ready.
```

### Step 5: Verify in Command Center

1. Open http://localhost:5173 (or your configured UI port)
2. Log in with your configured password
3. **Dashboard**: Prices should update in real-time once market opens
4. **System page**: All components should show green/healthy status

---

## 2. Daily Shutdown Procedure

### Standard Shutdown

```bash
./scripts/stop_live.sh
```

### Verify Clean Shutdown

1. Check terminal output:
   ```
   Initiating graceful shutdown...
   Phase 12/12: Stopping API server...
   Phase 11/12: Stopping data streams...
   ...
   Phase 1/12: Saving configuration...
   ARGUS shutdown complete.
   ```

2. Verify no open positions:
   - Check IBKR TWS/Gateway for any remaining positions
   - EOD flatten should have closed all positions before shutdown

3. Verify no open orders:
   - Check IBKR for any orphaned orders
   - Shutdown should have cancelled any pending orders

### IB Gateway

After ARGUS shutdown, you can either:
- **Leave Gateway running**: Ready for next session
- **Close Gateway**: If not trading tomorrow or for maintenance

---

## 3. Monitoring During Operation

### Command Center Pages

| Page | What to Check | Frequency |
|------|---------------|-----------|
| **Dashboard** | Live prices updating, strategy deployment bars | Every 30 min |
| **Orchestrator** | Regime badge, allocation donut, decision timeline | Every 30 min |
| **Trade Log** | New trades appearing, P&L updating | After each trade |
| **System** | All components healthy (green indicators) | Hourly |

### Terminal Log Monitoring

Watch for these log messages:

#### Normal Operation
```
INFO - Signal generated: ORB_BREAKOUT AAPL LONG
INFO - Risk: APPROVED - ORB_BREAKOUT AAPL 100 shares
INFO - Order submitted: bracket order for AAPL
INFO - Order filled: AAPL 100 @ 185.50
INFO - Position closed: AAPL +1.2R ($240.00)
```

#### Recoverable Issues (usually auto-recover)
```
WARNING - Reconnecting to Databento (attempt 1/5)...
WARNING - STALE DATA detected for AAPL (35s since last update)
INFO - Data resumed for AAPL
```

#### Issues Requiring Attention
```
ERROR - Max reconnection attempts exceeded for Databento
ERROR - IBKR connection lost, unable to reconnect
CRITICAL - Circuit breaker triggered: daily loss limit
```

### Key Events to Watch

| Event | Log Message | Action |
|-------|-------------|--------|
| Strategy setup found | `Signal generated` | None - watch for approval |
| Risk gate outcome | `Risk: APPROVED` or `Risk: REJECTED` | Review if many rejections |
| Trade executed | `Order filled` | None - normal |
| Trade completed | `Position closed` with R-multiple | Review if loss streak |
| Connection issue | `Reconnecting` | Monitor - usually recovers |
| Data gap | `STALE DATA` | Investigate if >60s or persistent |
| Circuit breaker | `Circuit breaker triggered` | Trading halted - review positions |

---

## 4. Mid-Session Restart

If ARGUS crashes or needs restart during market hours:

### Step 1: Stop ARGUS

```bash
# Graceful shutdown
./scripts/stop_live.sh

# If unresponsive (last resort)
pkill -9 -f "python -m argus.main"
```

### Step 2: Check IBKR State

Open IB Gateway or TWS and verify:
- **Positions**: Note any open positions (they persist on broker side)
- **Orders**: Note any pending/working orders
- **Account**: Check buying power and P&L

### Step 3: Restart ARGUS

```bash
./scripts/start_live.sh --with-ui
```

During startup, ARGUS will:
1. Call `reconstruct_from_broker()` to recover open positions
2. Match positions to existing ManagedPosition state
3. Resume monitoring open positions with existing stops

### Step 4: Verify State Recovery

In Command Center:
1. **Trade Log**: Open positions should appear
2. **Dashboard**: Position count should match IBKR
3. **System**: All components healthy

If positions don't match:
1. Stop ARGUS
2. Manually close positions in IBKR if needed
3. Start ARGUS fresh

---

## 5. IB Gateway Maintenance

### Daily Disconnect

IBKR enforces a nightly server restart. IB Gateway will disconnect:
- **Weekdays**: ~11:45 PM ET
- **Weekends**: Similar window Sunday night

**Typical behavior**:
1. Gateway shows "Connecting..."
2. ARGUS reconnection handler detects disconnect
3. Automatic reconnection attempts every 5-30 seconds
4. Connection restored within 1-5 minutes

### If Auto-Reconnect Fails

```bash
# 1. Stop ARGUS
./scripts/stop_live.sh

# 2. Restart IB Gateway
# Close and reopen the application, or:
# Docker: docker restart ibgateway

# 3. Wait for Gateway to show "Ready"

# 4. Start ARGUS
./scripts/start_live.sh --with-ui
```

### Docker Option (Recommended for Unattended Operation)

For auto-restart capability, consider the IBKR Gateway Docker image:

```bash
docker run -d \
  --name ibgateway \
  -p 4002:4002 \
  -e TWSUSERID=your_username \
  -e TWSPASSWORD=your_password \
  -e TRADING_MODE=paper \
  ghcr.io/gnzsnz/ib-gateway:stable
```

This container auto-restarts after nightly disconnects.

---

## 6. Emergency Procedures

### Flatten All Positions

**Command Center** (preferred):
1. Navigate to Orchestrator page
2. Click "Flatten All" in Global Controls section
3. Confirm in the modal dialog
4. Monitor Trade Log for close confirmations

**API** (if UI unavailable):
```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=operator&password=your_password" | jq -r '.access_token')

# Flatten all positions
curl -X POST http://localhost:8000/api/v1/orchestrator/flatten-all \
  -H "Authorization: Bearer $TOKEN"
```

### Pause All Strategies

Stops new signals while keeping existing positions open:

**Command Center**:
1. Navigate to Orchestrator page
2. Click "Pause All" in Global Controls section
3. Existing positions continue to be managed (stops, targets, time stops)
4. No new entries until resumed

### Kill Switch (Nuclear Option)

```bash
# Graceful - recommended
./scripts/stop_live.sh

# Force kill (if unresponsive)
pkill -9 -f "python -m argus.main"
pkill -9 -f "uvicorn"
```

**After emergency shutdown**:
1. Open IBKR directly
2. Manually close any positions if needed
3. Cancel any orphaned orders
4. Review what happened in logs

---

## 7. Common Issues

### Connection Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused on port 4002` | IB Gateway not running or API not enabled | Start Gateway, verify API settings |
| `IBKR: Not connected` | Gateway disconnected | Restart Gateway, wait for "Ready" |
| `Databento: Connection timeout` | Network issue or API key invalid | Check internet, verify API key |
| `Max reconnection attempts exceeded` | Persistent connection failure | Check network, restart services |

### Data Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `data_end_after_available_end` | Historical data lag in Databento | Normal at market open - scanner uses fallback |
| `STALE DATA for [symbol]` | No updates for >30s | Usually recovers; if persistent, check Databento status |
| `Scanner fallback to static list` | Historical data unavailable | Normal before market; uses static watchlist |

### Risk Manager Rejections

| Rejection Reason | Cause | Action |
|------------------|-------|--------|
| `Single-stock exposure would exceed limit` | 5% concentration limit | Working as designed - position sizing correct |
| `Daily loss limit reached` | Circuit breaker triggered | Trading halted for the day |
| `Insufficient buying power` | Account depleted | Review positions, wait for closes |
| `Strategy allocation exhausted` | Strategy at max deployment | Normal - wait for closes to free capital |

### Startup Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `Regime: range_bound (fallback)` | SPY data not yet available | Normal at startup; resolves when data flows |
| `Strategy reconstruction: 0 positions` | Clean start (no prior positions) | Normal |
| `Failed to load strategy` | Config or code error | Check strategy config and logs |

---

## 8. Taipei Timezone Reference

For operating from Taipei (UTC+8), use this schedule:

| Event | Eastern Time (ET) | Taipei Time (UTC+8) |
|-------|-------------------|---------------------|
| System startup recommended | 9:15 AM | 10:15 PM (same day) |
| US Market pre-open | 9:00 AM | 10:00 PM |
| **US Market open** | **9:30 AM** | **10:30 PM** |
| ORB window (5-min) | 9:35 AM | 10:35 PM |
| ORB Breakout active | 9:35 AM – 11:30 AM | 10:35 PM – 12:30 AM |
| VWAP Reclaim active | 10:00 AM – 12:00 PM | 11:00 PM – 1:00 AM |
| Afternoon Momentum active | 2:00 PM – 3:30 PM | 3:00 AM – 4:30 AM |
| EOD flatten begins | 3:55 PM | 4:55 AM |
| **US Market close** | **4:00 PM** | **5:00 AM** |
| IB Gateway nightly disconnect | ~11:45 PM | ~12:45 PM (next day) |

### Typical Operating Schedule (Taipei)

| Time (Taipei) | Activity |
|---------------|----------|
| 10:15 PM | Start IB Gateway, start ARGUS |
| 10:30 PM | Market opens - monitoring begins |
| 10:35 PM – 12:30 AM | ORB strategies active - peak activity |
| 12:30 AM – 3:00 AM | Midday lull - periodic checks |
| 3:00 AM – 4:30 AM | Afternoon Momentum - second activity peak |
| 4:55 AM | EOD flatten - verify all positions closed |
| 5:00 AM | Market closes - can sleep or stop system |

### Daylight Saving Time Notes

- **US DST begins**: Second Sunday in March (clocks forward 1 hour)
- **US DST ends**: First Sunday in November (clocks back 1 hour)
- Taiwan does not observe DST
- Offset is **+13 hours** during US standard time, **+12 hours** during US DST

When US changes DST, your schedule shifts by 1 hour. Update your alarms accordingly.

---

## Quick Reference Card

### Startup
```bash
# Start Gateway first, then:
./scripts/start_live.sh --with-ui
```

### Shutdown
```bash
./scripts/stop_live.sh
```

### Emergency Flatten
```bash
# UI: Orchestrator → Flatten All
# API: POST /api/v1/orchestrator/flatten-all
```

### Force Kill
```bash
pkill -9 -f "python -m argus.main"
```

### Verify State
- **Command Center**: Dashboard + System pages
- **IBKR**: Account window for positions/orders
- **Logs**: `tail -f logs/argus.log`

---

## 8. AI Copilot Operations

*Added in Sprint 22. Requires `ANTHROPIC_API_KEY` environment variable.*

### Overview

The AI Copilot provides Claude-powered analysis, advisory, and action proposals through a structured approval workflow. Key characteristics:

- **Graceful degradation**: All AI features disabled when `ANTHROPIC_API_KEY` unset. Trading engine operates identically.
- **Advisory only**: Claude never recommends specific entries/exits or places trades autonomously.
- **Approval workflow**: Configuration changes require explicit operator approval.

### AI-Related Commands

```bash
# Run with AI enabled (requires ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY="sk-..." ./scripts/start_live.sh --with-ui

# Check AI status
curl http://localhost:8000/api/v1/ai/status

# Check AI usage/cost
curl http://localhost:8000/api/v1/ai/usage
```

### Using the Copilot

1. **Open Copilot**: Press `Cmd/Ctrl+K` or click the brain icon
2. **Ask questions**: Type naturally about positions, performance, or strategy behavior
3. **Context-aware**: Copilot knows which page you're on and what you're viewing

### Action Proposals

When Claude proposes a configuration change, it appears as an **ActionCard**:

| Action Type | What It Does | Approval Required |
|-------------|--------------|-------------------|
| `propose_allocation_change` | Adjust strategy capital allocation | Yes |
| `propose_risk_param_change` | Modify risk parameter | Yes |
| `propose_strategy_suspend` | Suspend strategy | Yes |
| `propose_strategy_resume` | Resume suspended strategy | Yes |
| `generate_report` | Generate analytical report | No (immediate) |

**Approval workflow:**
1. Review the proposed change in the ActionCard
2. Click **Approve** or **Reject** (keyboard: `y` / `n`)
3. If approving, a 4-condition re-check runs:
   - Target entity still exists
   - Regime hasn't changed unfavorably
   - Equity within ±5% of proposal time
   - No circuit breaker active
4. If all checks pass, the change is executed

**Proposal TTL**: Proposals expire after 5 minutes if not acted upon.

### Cost Monitoring

AI usage is tracked per-call in the `ai_usage` SQLite table.

```bash
# View usage summary
curl http://localhost:8000/api/v1/ai/usage

# Response includes:
# - Today's input/output tokens
# - Today's estimated cost
# - Current month total cost
# - Per-day average
```

**Estimated costs** (Claude Opus, DEC-098):
- Input tokens: $15.00 / 1M tokens
- Output tokens: $75.00 / 1M tokens
- Typical monthly: ~$35–50 with normal usage

### Dashboard AI Insight Card

The Dashboard includes an AI insight card that:
- Auto-refreshes every 5 minutes during market hours
- Shows "AI not available" when service disabled
- Can be manually refreshed at any time

### Learning Journal (Debrief)

The Debrief page includes a **Learning Journal** conversation browser:
- View past AI conversations by date and tag
- Filter by: `pre-market`, `session`, `research`, `debrief`, `general`
- Review Claude's analysis from previous trading days

### Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| AI disabled | "AI not available" in Dashboard | Check `ANTHROPIC_API_KEY` in `.env` |
| Slow responses | Streaming delay >5s | Check network; Claude API may be under load |
| Proposal expired | "Proposal expired" error | Re-ask Claude for the recommendation |
| Rate limited | "Rate limit exceeded" | Wait 60 seconds; reduce request frequency |

---

*End of Live Operations Guide v1.1*
