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

> ⚠️ **DO NOT start ARGUS between ~22:30 ET and pre-market open (DEF-164).**
> Time-based after-hours auto-shutdown fires during this window and can
> collide with in-flight service initialization (notably `HistoricalQueryService`
> DuckDB VIEW creation). A 2026-04-20 operator-initiated start at 23:30 ET
> triggered shutdown 51 seconds into init and hung the process at 70% CPU /
> 40% memory until force-killed. See DEF-164 (scheduling collision) and
> DEF-165 (DuckDB close hangs when VIEW creation is interrupted) for details.
> Safe start windows: pre-market (≥ 04:00 ET) through standard shutdown.
> Code-level fix is weekend-only; this operator warning is the current
> mitigation.

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

#### Startup Zombie Cleanup (Sprint 27.95)

During startup, ARGUS queries IBKR for existing positions and open orders:
- Positions **with** associated bracket orders → classified as managed, reconstructed
- Positions **without** orders → classified as zombies:
  - `startup.flatten_unknown_positions: true` (default): flattened via market order
  - `startup.flatten_unknown_positions: false`: WARNING logged, position tracked as RECO
  - **Note:** RECO positions created with `flatten_unknown_positions=false` have `stop_price=0.0` — requires manual stop placement via IBKR TWS/Gateway
- Zero-quantity ghost positions are silently skipped (no flatten attempt)

Watch for these log messages during startup:
```
INFO - Startup: flatting unknown position AAPL (100 shares, no bracket orders)
WARNING - Startup: unknown position AAPL (100 shares) — flatten disabled, creating RECO position
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

#### Overflow Routing (Sprint 27.95)

When open positions reach `overflow.broker_capacity` (default 30), approved signals are
routed to CounterfactualTracker instead of IBKR:
```
INFO - Overflow routing: 30/30 positions, routing AAPL signal to counterfactual
```

Monitor overflow activity:
- **Log messages**: Search for "Overflow routing" in logs
- **Counterfactual DB**: Query `data/counterfactual.db` for `rejection_stage = 'BROKER_OVERFLOW'`
- **API endpoint**: `GET /api/v1/counterfactual/accuracy` with date range filter

Config: `overflow.enabled: true` (default), `overflow.broker_capacity: 30` in
`config/overflow.yaml` and `config/system.yaml`/`system_live.yaml`.

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

### IBC (Recommended for Unattended Operation)

IBC automates IBKR Gateway startup and reconnection after nightly resets without Docker. See **`docs/ibc-setup.md`** for the full setup guide including:
- IBC installation and configuration
- macOS launchd plist template for automatic startup at login
- Gateway reconnection behavior after nightly disconnect

IBC is the preferred approach for macOS. Docker is also an option:

```bash
docker run -d \
  --name ibgateway \
  -p 4002:4002 \
  -e TWSUSERID=your_username \
  -e TWSPASSWORD=your_password \
  -e TRADING_MODE=paper \
  ghcr.io/gnzsnz/ib-gateway:stable
```

### Post-Reconnect Behavior (Sprint 32.75)

After ARGUS reconnects to IBKR, `IBKRBroker` waits **3 seconds** before querying the portfolio position snapshot. If the snapshot returns empty (common immediately after reconnect), it retries once after another 3s. This prevents false "no positions" state from an immediately-reconnected session. The 3s delay is hardcoded — evaluate for live trading (may need adjustment for lower-latency setups).

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

## 8. Post-Session Debrief

After market close, run the structured debrief protocol to diagnose system behavior and identify action items.

**Protocol:** `docs/protocols/market-session-debrief.md`

**What to provide:**
- The debrief export JSON: `logs/debrief_YYYYMMDD.json` (auto-generated at shutdown, Sprint 25.7, DEC-348)
- The JSONL log file: `logs/argus_YYYYMMDD.jsonl` (NOT the .log or UI log)
- Access to run SQLite queries against `data/argus.db`, `data/catalyst.db`, and `data/evaluation.db`
- Any Command Center observations (screenshots, notes)

**What it produces:**
- Session coverage report (which strategy windows were active)
- Strategy pipeline diagnosis (where in the funnel did signals stop?)
- Data flow analysis (candle throughput, warm-up success, stale episodes)
- Catalyst pipeline report (cycles, cost, classification counts)
- Error catalog (actionable vs benign)
- DEF items for issues discovered
- Action items for tomorrow's session

**When to run:** After every market session, or at minimum when zero trades occur and you need to understand why. The protocol includes a decision tree for zero-trade diagnosis that traces the issue from orchestrator regime exclusion through evaluation telemetry to quality engine to trade execution.

**Typical runtime:** 10–15 minutes with the protocol, vs 45+ minutes ad-hoc.

---

## 9. Operating Schedule (ET)

The operator is on the US East Coast (ET) — no timezone conversion needed. All times below are Eastern Time.

| Event | Time (ET) |
|-------|-----------|
| System startup recommended | 9:15 AM |
| US Market pre-open | 9:00 AM |
| **US Market open** | **9:30 AM** |
| ORB window (5-min) | 9:35 AM |
| ORB Breakout active | 9:35 AM – 11:30 AM |
| VWAP Reclaim active | 10:00 AM – 12:00 PM |
| Afternoon Momentum active | 2:00 PM – 3:30 PM |
| EOD flatten begins | 3:55 PM |
| **US Market close** | **4:00 PM** |
| IB Gateway nightly disconnect | ~11:45 PM |

---

## Quick Reference Card

### Startup
```bash
# Start Gateway first, then:
./scripts/start_live.sh --with-ui

# Unattended launch + monitoring (Sprint 25.7)
./scripts/launch_monitor.sh              # Launch at next market open + monitor
./scripts/launch_monitor.sh --now        # Launch immediately + monitor
./scripts/launch_monitor.sh --monitor-only  # Monitor only (system already running)
./scripts/launch_monitor.sh --launch-et HH:MM  # Launch at specific ET time
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

## 10. AI Copilot Operations

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

## 11. Regime Intelligence Operations

*Added in Sprint 27.6. Config-gated via `regime_intelligence.enabled` in `config/regime.yaml`.*

### Overview

When enabled, the Regime Intelligence system extends the V1 RegimeClassifier with 4 additional dimension calculators, producing a multi-dimensional `RegimeVector` (6 dimensions: trend, volatility, breadth, correlation, sector rotation, intraday character). All data comes from existing subscriptions at zero additional cost.

### Pre-Market Checks

During pre-market startup, the regime system performs:

1. **Correlation fetch** — MarketCorrelationTracker fetches cached daily returns for top N symbols and computes pairwise correlation. Uses FMP daily bars or computed from Databento candle data.
2. **Sector performance fetch** — SectorRotationAnalyzer fetches sector performance from FMP sector endpoint via `asyncio.gather()` alongside correlation fetch.
3. **Note:** FMP sector performance endpoint may return HTTP 403 on Starter plan ($22/mo). The SectorRotationAnalyzer handles this gracefully — sector rotation dimension returns None, and the RegimeVector is still valid with the remaining 5 dimensions populated.

### Intraday Updates

During market hours:
- **BreadthCalculator** updates on every CandleEvent (streaming, zero-cost from existing Databento subscription)
- **IntradayCharacterDetector** classifies session character at configurable times (default: 9:35, 10:00, 10:30 ET)
- **RegimeClassifierV2** recomputes the full RegimeVector during periodic regime reclassification (300s interval)
- **RegimeHistoryStore** persists each computed vector to `data/regime_history.db` (fire-and-forget, 7-day retention)

### Observatory Visualization

The Observatory page's Session Vitals Bar displays regime dimensions in real-time:
- REST endpoint `/api/v1/observatory/session-summary` includes `regime_vector_summary`
- WebSocket push includes regime data in `evaluation_summary` messages
- All optional/null when regime intelligence disabled — no frontend errors

### Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| Regime Intelligence disabled | Only V1 regime shown | Check `regime_intelligence.enabled` in `config/regime.yaml` |
| Sector rotation always null | FMP 403 on Starter plan | Expected on $22/mo plan. Upgrade to Premium ($59/mo) or accept 5-dimension vectors |
| Breadth score null | Too few symbols in universe | Check `breadth.min_symbols` threshold (default 50). Universe Manager must be active with sufficient viable symbols |
| Correlation always null | No cached daily returns | Ensure FMP daily bars fetch completes during pre-market. Check FMP API key |
| Intraday character null | Too few SPY bars | Wait until `intraday.min_spy_bars` (default 3) worth of SPY candles arrive |

---

## 12. Scheduled Maintenance Tasks

*Added 2026-04-22 (FIX-21). Closes DEF-097 + DEF-162.*

### Monthly Parquet Cache Refresh

The historical data cache has two sides (see `docs/operations/parquet-cache-layout.md`):

- `data/databento_cache/` — read-only source of truth for `BacktestEngine`. Populated by `scripts/populate_historical_cache.py`, which pulls Databento OHLCV-1m Parquet files month-by-month for three datasets (EQUS.MINI, XNAS.ITCH, XNYS.PILLAR).
- `data/databento_cache_consolidated/` — derived per-symbol cache used by `HistoricalQueryService` (DuckDB). Produced by `scripts/consolidate_parquet_cache.py`, which merges the monthly files into one Parquet per symbol with an embedded `symbol` column.

Both must be refreshed monthly as Databento publishes new calendar months. The two scripts are designed to run as a chained pair: `--update` pulls only months newer than what's already cached, and `--resume` (the consolidator's default) re-runs only symbols whose source row count grew.

**Recommended cron line** (runs 02:00 ET on the 2nd of each month — gives Databento time to publish the prior month):

```
0 2 2 * * cd "/Users/stevengizzi/Documents/Coding Projects/argus" && python3 scripts/populate_historical_cache.py --update >> logs/cache_update.log 2>&1 && python3 scripts/consolidate_parquet_cache.py --resume >> logs/cache_consolidate.log 2>&1
```

The `&&` chain means consolidation only runs if population succeeded. Failures of either step land in a distinct log file so the operator can diagnose them independently.

**Prerequisites:**

- Mac awake at the scheduled time (either system always-on, or pmset schedule a wake — cron does not wake a sleeping Mac).
- Both caches are local under `data/` in the repo. No external drive is required. (The populate script's fallback list still includes `/Volumes/LaCie/argus-cache` for legacy reasons, but the local candidate is resolved first.)
- `DATABENTO_API_KEY` available in the environment or in `.env` at repo root.
- Enough free disk on the destination filesystem — `consolidate_parquet_cache.py` enforces a 60 GB preflight and refuses to start below that.

**Install:**

```bash
crontab -e            # append the line above
crontab -l            # verify it registered
```

**Verify it ran:**

```bash
tail -50 logs/cache_update.log
tail -50 logs/cache_consolidate.log
```

A successful run ends with a download summary (populate) and an atomic-rename confirmation per consolidated symbol (consolidate). If either log ends mid-sentence or reports a Python traceback, halt and re-run manually before the next scheduled invocation.

**Expected runtime:**

- `populate --update`: ~5–15 min for one new month across the three datasets.
- `consolidate --resume`: ~2–5 min for just the symbols whose source row count changed. First-time full consolidation after Sprint 31.85 was ~45 min for ~24K symbols — `--resume` is dramatically faster on steady-state monthly deltas.

---

## OCA Architecture Operations (Sprint 31.91 / DEC-386)

> Sprint 31.91 introduced a 4-layer OCA architecture closing DEF-204's primary mechanism. This section covers the operator-facing procedures: rollback, lock-step constraints, failure-mode response, and the spike-script trigger registry.

### Rollback procedure: `bracket_oca_type: 1 → 0` is RESTART-REQUIRED

If a paper-session debrief (or live monitoring) shows bracket-stop fill-slippage degradation beyond the documented 50–200ms cancellation propagation cost (mean slippage on $7–15 share universe degrades by >$0.05 vs pre-Sprint-31.91 baseline — escalation criterion A8 in Sprint 31.91 spec), evaluate rollback:

1. **STOP ARGUS** (`Ctrl+C` in the terminal, or `kill -SIGTERM <pid>`). Do NOT attempt mid-session config flip — it is explicitly unsupported per Sprint 31.91 Sprint Spec §"Performance Considerations" H1 disposition.
2. **Run operator daily flatten** (`scripts/ibkr_close_all_positions.py`) to ensure no positions exist at the broker before restart.
3. **Edit `config/system.yaml` AND `config/system_live.yaml`** — set `ibkr.bracket_oca_type: 0` in BOTH files. The config change must be visible in whichever YAML the runtime selects.
4. **Restart ARGUS**. Confirm at startup that `IBKRConfig.bracket_oca_type == 0` is logged.
5. **Verify behavior:** the Phase A spike script (`scripts/spike_ibkr_oca_late_add.py`) under `bracket_oca_type=0` should NOT return `PATH_1_SAFE` (because the OCA group is no longer set). This is expected; you have rolled back the OCA architecture.

**Rolling forward** (`0 → 1`) follows the same RESTART-REQUIRED procedure in reverse. Mid-session flip in either direction is unsupported.

### `_OCA_TYPE_BRACKET` constant lock-step

`argus/execution/order_manager.py` carries a module-level constant `_OCA_TYPE_BRACKET = 1` (Sprint 31.91 Session 1b). It mirrors `IBKRConfig.bracket_oca_type`'s default value because `OrderManager` does not currently have access to `IBKRConfig` (Sprint 31.92 component-ownership refactor will close this gap via DEF-212).

**Operator obligation when flipping `bracket_oca_type` to 0 for rollback:** the constant in `order_manager.py:82` should be updated to `0` in lock-step. **If you do not update it, the divergence is functionally a no-op** (standalone SELLs decorate with `ocaType=1` and an `oca_group_id` that has no other live OCA members at the broker, so cancellation is vacuous), but the architectural intent is silently violated. Two-file edit:

```
config/system.yaml:        ibkr.bracket_oca_type: 0
config/system_live.yaml:   ibkr.bracket_oca_type: 0
argus/execution/order_manager.py:82:  _OCA_TYPE_BRACKET: int = 0
```

This lock-step burden disappears once Sprint 31.92 lands DEF-212.

### Cancel-propagation timeout failure-mode response

**What it is:** Sprint 31.91 Session 1c added cancel-then-SELL gating to three broker-only paths (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`). On `CancelPropagationTimeout` (2-second budget exceeded for `cancel_all_orders(symbol, await_propagation=True)` to observe an empty filtered open-orders state), the SELL is **aborted** and a critical `SystemAlertEvent(alert_type="cancel_propagation_timeout")` is emitted.

**The intentional trade-off:** the position remains at the broker as a phantom long with no working stop. This is preferable to placing the SELL without verifying broker-side cancellation, which could create an unbounded phantom short on a runaway upside (asymmetric-risk argument; see Sprint 31.91 Sprint Spec §"Failure Mode Documentation" and DEC-386).

**Operator response when this alert fires:**

1. **Identify the symbol(s)** from the alert message (`f"cancel_all_orders did not propagate within timeout for {symbol} (shares={shares}, stage={stage})..."`). Today the alert is visible only in logs and via the event-bus debug surface — **the Command Center will not show it until Sprint 31.91 Session 5a.1 lands.** Until then, tail the structured log (`logs/argus_YYYYMMDD.jsonl`) for `cancel_propagation_timeout` events:

   ```bash
   grep -F '"alert_type": "cancel_propagation_timeout"' logs/argus_$(date +%Y%m%d).jsonl
   ```

2. **Manually flatten the affected symbol(s) before the next session begins:**

   ```bash
   python scripts/ibkr_close_all_positions.py --symbols PHANTOM,OTHER
   ```

   (Or run with no `--symbols` arg to flatten everything, which is the daily mitigation procedure already in place.)

3. **Investigate the underlying IBKR connectivity issue.** A `cancel_propagation_timeout` in steady-state operation indicates IBKR is taking >2s to acknowledge a cancellation — likely a network blip, IBKR Gateway lag, or a broker-side issue. Check the IBKR Gateway logs and connectivity metrics for the same time window.

4. **Do NOT attempt to bypass the abort by re-running the flatten without addressing the timeout.** The abort is the safety mechanism; bypassing it is what creates the phantom-short risk we're avoiding.

### Spike-script trigger registry (Sprint 31.91 regression invariant 22)

The Phase A spike script `scripts/spike_ibkr_oca_late_add.py` is the **live-IBKR regression check** that verifies IBKR continues to enforce ocaType=1 atomic cancellation pre-submit (the success signature is `PATH_1_SAFE`). Failure to return `PATH_1_SAFE` invalidates the OCA architecture seal and triggers Tier 3 review.

**Run the spike script before any of the following events:**

- [ ] **Before any live-trading transition.** Live-enable gate item per `pre-live-transition-checklist.md` §"Sprint 31.91 — OCA Architecture & Reconciliation Drift".
- [ ] **Before AND after any `ib_async` library version upgrade.** The spike's behavior depends on `ib_async`'s exception-string passthrough.
- [ ] **Before AND after any IBKR API version change** (TWS / IB Gateway upgrade). IBKR has historically modified Error 201 reason strings between versions.
- [ ] **Monthly during paper-trading windows.** Calendar reminder (any monthly cadence works; no enforced date). The most-recent result file (`scripts/spike-results/spike-results-YYYYMMDD.json`) must be ≤30 days old per regression invariant 22 — `tests/_regression_guards/test_spike_script_freshness.py` (lands at Session 4) enforces this in CI.

**How to run:**

```bash
# IB Gateway must be running and connected (paper account, port 4002).
python scripts/spike_ibkr_oca_late_add.py

# Result file is written to scripts/spike-results/spike-results-YYYYMMDD.json
# Verify the verdict:
jq '.overall_outcome' scripts/spike-results/spike-results-$(date +%Y-%m-%d).json
# Expected: "PATH_1_SAFE"
```

**If the verdict is anything other than `PATH_1_SAFE`** (e.g., `PATH_2_RACE`, `PATH_3_LATE_FILL`, or an explicit error): halt the trigger event (live transition / upgrade), and either roll back to `bracket_oca_type: 0` (RESTART-REQUIRED procedure above) or arrange Tier 3 architectural review of the new mechanism behavior.

### Operator daily flatten — current status

Daily `scripts/ibkr_close_all_positions.py` at session close **remains required** throughout the Sprint 31.91 sprint window. It becomes optional only after:

1. Sprint 31.91 sealed (all 18 sessions complete).
2. ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows + zero `phantom_short`/`phantom_short_retry_blocked`/`cancel_propagation_timeout` alerts.
3. Session 5a.1 (HealthMonitor consumer) landed so alerts are Command-Center-visible.
4. Pre-live paper stress test under live-config simulation passes.

See `docs/pre-live-transition-checklist.md` §"Sprint 31.91 — OCA Architecture & Reconciliation Drift" for the full gate list.

---

*End of Live Operations Guide v1.5*
*Last updated: 2026-04-27 (Sprint 31.91 Tier 3 review #1 doc-sync — OCA architecture operations section)*
