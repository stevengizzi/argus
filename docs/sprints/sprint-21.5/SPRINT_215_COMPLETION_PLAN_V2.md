# ARGUS Sprint 21.5 — Full Completion Plan (V2)

> **Master sequencing document.** Contains all Claude Code session prompts from current state through Sprint 21.5 completion. Sessions ordered to maximize tonight's non-market work and stack all live-market validation for tomorrow.
>
> **V2 changes:** Added scanner resilience fix (B0), updated B1 to include EQUS.MINI live stream diagnostic, updated C1 with EQUS.MINI verification as first gate check.

---

## Schedule Overview

| Block | Time (Taipei) | Time (ET) | Market | Sessions |
|-------|--------------|-----------|--------|----------|
| **Block A** | DONE | DONE | — | A1: Validation scripts ✅ |
| **Block B** | NOW (~4 AM) onward | After close | CLOSED | B0–B5: All non-market work |
| — | — | — | — | **⏸ Claude.ai code review checkpoint** |
| **Block C** | ~10:15 PM onward | 9:15 AM–4:00 PM | OPEN (full day) | C1–C3: Full market validation |
| — | — | — | — | **⏸ Claude.ai final review** |
| **Block D** | Next morning | After close | CLOSED | D1: Sprint closeout |

---

## Block A: COMPLETE ✅

Session A1 results:
- Flaky test fixed (dev_state.py deterministic breakeven)
- Session 8 validation: 13/13 PASS
- Session 9 resilience: 4/4 PASS
- EOD observation blocked — DatabentoScanner historical API returned 422 (EQUS.MINI data available only through Feb 28). Live streaming was never attempted. Scanner fell back to static watchlist, system started successfully watching 10 symbols.

---

## Block B: Non-Market Work (tonight)

### Session B0: Scanner Resilience + EQUS.MINI Diagnostic ⚡ NEW

```
# ARGUS Sprint 21.5 — Session B0: Scanner Resilience + EQUS.MINI Diagnostic

## Context
Read CLAUDE.md and docs/sprints/SPRINT_215_SPEC.md for full context.

During Session A1, the DatabentoScanner failed with:
    422 data_end_after_available_end
    The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'.
    The `end` in the query ('2026-03-03 00:00:00+00:00') is after the available range.

This is the HISTORICAL REST API (used by scanner for daily bars / gap
calculation), NOT the live streaming API. The live stream was never
attempted during Session A1. The system fell back to static watchlist
and started successfully.

Earlier sessions (4-6 follow-up) successfully streamed live data for
30+ minutes using XNAS.ITCH. After DEC-241/242 switched to EQUS.MINI,
live streaming has NOT been tested.

This session has two goals:
1. Make the scanner resilient to historical data lag
2. Write a diagnostic script to verify EQUS.MINI capabilities

## Part 1: Scanner Resilience Fix

Find the scanner code that makes the historical query:

    grep -n "end\|timeseries\|get_range\|daily\|batch" \
      argus/data/databento_scanner.py

The fix: when the historical API returns a 422 with
"data_end_after_available_end", the scanner should:

1. Catch the specific error
2. Retry with `end` set to the available end date from the error message
   (or use `end=None` / omit it if the API supports that)
3. If that also fails, fall back to the static watchlist (which it
   already does — just make the fallback cleaner with a clear log message)

The key insight: for gap scanning, we need YESTERDAY's daily bar, not
today's. So even if the historical API is 1-2 days behind, we can still
compute gaps from the most recent available close.

Implementation approach:

    async def _fetch_daily_bars(self, symbols: list[str]) -> pd.DataFrame:
        """Fetch daily bars, handling historical data lag gracefully."""
        try:
            # Try fetching with today as end date
            return await self._query_databento_daily(symbols, end=today)
        except DatabentoBadRequest as e:
            if "data_end_after_available_end" in str(e):
                # Historical data hasn't caught up to today
                # Extract available end from error or use yesterday
                logger.warning(
                    "Databento historical data lag detected. "
                    "Using most recent available data for gap scan."
                )
                # Retry with end=yesterday or end=None
                return await self._query_databento_daily(
                    symbols, end=last_available_date
                )
            raise

Also check: does the scanner use `start` and `end` params? Make sure
`start` is also reasonable (e.g., 2 trading days back, not just 1).

Write tests for the new fallback behavior:
- Test: scanner handles 422 gracefully and retries
- Test: scanner falls back to static watchlist if retry also fails
- Test: gap calculation works with data that's 1-2 days old

## Part 2: EQUS.MINI Diagnostic Script

Create scripts/diagnose_databento.py that tests all three Databento
API paths WITHOUT starting the full ARGUS system:

    #!/usr/bin/env python3
    """Diagnose Databento EQUS.MINI capabilities."""
    import asyncio
    import os
    import databento as db

    async def main():
        key = os.environ["DATABENTO_API_KEY"]
        client = db.Historical(key)
        live_client = db.Live(key)

        print("=" * 60)
        print("DATABENTO EQUS.MINI DIAGNOSTIC")
        print("=" * 60)

        # Test 1: Historical data availability
        print("\n[1] Historical Data Range")
        try:
            # Query metadata or make a small request to check range
            data = client.timeseries.get_range(
                dataset="EQUS.MINI",
                symbols=["SPY"],
                schema="ohlcv-1d",
                start="2026-02-25",  # Last week
                # Don't set end — let it use latest available
            )
            # Print the latest date available
            df = data.to_df()
            print(f"  Latest daily bar: {df.index.max()}")
            print(f"  SPY close: {df['close'].iloc[-1]}")
            print("  ✅ Historical daily bars working")
        except Exception as e:
            print(f"  ❌ Historical daily bars failed: {e}")

        # Test 2: Historical 1-minute bars (what DataService uses for warmup)
        print("\n[2] Historical 1-Minute Bars")
        try:
            data = client.timeseries.get_range(
                dataset="EQUS.MINI",
                symbols=["SPY"],
                schema="ohlcv-1m",
                start="2026-02-27T14:00:00",  # Last Friday afternoon
                end="2026-02-27T16:00:00",
            )
            df = data.to_df()
            print(f"  Bars returned: {len(df)}")
            print(f"  Time range: {df.index.min()} to {df.index.max()}")
            print("  ✅ Historical 1-min bars working")
        except Exception as e:
            print(f"  ❌ Historical 1-min bars failed: {e}")

        # Test 3: Live streaming capability check
        # NOTE: This should only be run during market hours for full
        # validation. Outside market hours, it will connect but receive
        # no data. Test connection establishment only.
        print("\n[3] Live Stream Connection")
        try:
            live_client.subscribe(
                dataset="EQUS.MINI",
                schema="ohlcv-1m",
                symbols=["SPY"],
            )
            # Don't actually start receiving — just verify subscription
            # accepted without error
            print("  ✅ Live subscription accepted (no data outside market hours)")
            # Clean up
            # live_client.close() or equivalent
        except Exception as e:
            print(f"  ❌ Live subscription failed: {e}")
            if "license" in str(e).lower():
                print("  ⚠️  This may indicate EQUS.MINI doesn't support")
                print("     live streaming on Standard plan. Check with Databento.")
            elif "dataset" in str(e).lower():
                print("  ⚠️  Dataset may not support this schema for live streaming.")

        # Test 4: Check what schemas are available
        print("\n[4] Available Schemas")
        for schema in ["ohlcv-1m", "ohlcv-1d", "trades", "mbp-10"]:
            try:
                # Small historical query to test schema support
                data = client.timeseries.get_range(
                    dataset="EQUS.MINI",
                    symbols=["SPY"],
                    schema=schema,
                    start="2026-02-27T15:55:00",
                    end="2026-02-27T16:00:00",
                )
                df = data.to_df()
                print(f"  {schema}: ✅ ({len(df)} records)")
            except Exception as e:
                print(f"  {schema}: ❌ ({e})")

        print("\n" + "=" * 60)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 60)

    asyncio.run(main())

IMPORTANT: Adapt this to the actual databento Python client API. Check:
    pip show databento
    python -c "import databento; help(databento.Historical)"

The diagnostic script should work RIGHT NOW (outside market hours) for
tests 1, 2, and 4. Test 3 (live stream) will connect but won't receive
data until market hours — that's expected and fine.

Run the diagnostic and save the output.

## Part 3: Check DatabentoDataService Live Start Path

Review how DatabentoDataService.start() initiates live streaming:

    grep -n "start\|subscribe\|live\|Live\|session" \
      argus/data/databento_data_service.py | head -30

Verify:
1. Does it use `databento.Live` client (separate from Historical)?
2. Does the live subscription specify the correct dataset (EQUS.MINI)?
3. Does it subscribe to both ohlcv-1m and trades schemas?
4. Is there any startup dependency on the scanner succeeding first?
   (If scanner failure blocks live stream startup, that's a bug)

If the live stream startup is blocked by scanner failure, fix the
dependency so they're independent.

## Definition of Done
- Scanner handles 422 gracefully with retry using available date range
- Scanner fallback to static watchlist is clean (no stack trace in logs)
- Diagnostic script created and run — output saved
- DatabentoDataService live startup verified as independent of scanner
- New tests for scanner resilience
- Commit: fix(scanner): handle historical data lag + EQUS.MINI diagnostic
```

---

### Session B1: Position Sizing Investigation

```
# ARGUS Sprint 21.5 — Session B1: Position Sizing Investigation

## Context
Read CLAUDE.md for full context. During the Sprint 21.5 live observation
(Sessions 4-6 follow-up), the VWAP Reclaim strategy generated a signal
requesting 3,573 shares of NFLX (~$97 x 3573 = ~$346K) on a $1M paper
account. Risk Manager correctly rejected it for exceeding the 5%
single-stock concentration limit ($50K). However, a signal this oversized
suggests a position sizing issue upstream.

## Goals
1. Trace the position sizing calculation path for the NFLX signal
2. Determine if this is systemic or an edge case
3. Fix if needed

## Investigation

Find and trace the position sizing logic:

    grep -n "shares\|position_size\|risk_per_trade\|calculate_shares" \
      argus/strategies/vwap_reclaim.py argus/strategies/base_strategy.py

    grep -n "shares\|position_size\|calculate" argus/core/risk_manager.py

    grep -n "risk_per_trade_pct\|max_single_stock_pct" \
      config/system_live.yaml config/strategies/vwap_reclaim.yaml

Answer these questions:
1. Where does share count get calculated? (Strategy? Risk Manager? Both?)
2. Is the strategy using TOTAL account equity or its ALLOCATED portion?
3. Is risk_per_trade_pct applied correctly? (should be 0.5-1% of allocated
   capital, not total equity)
4. Is stop distance factored in? (Tight stop = more shares = hits cap)

## The Math
With 4 strategies at equal weight on $1M:
- 20% cash reserve = $800K deployable
- $800K / 4 strategies = $200K per strategy
- 1% risk on $200K = $2,000 risk budget per trade
- If NFLX stop is $0.75 away: $2,000 / $0.75 = 2,667 shares x $97 = $259K
- 5% concentration limit = $50K = 515 shares max

The concentration limit should constrain before risk-based sizing.
The question is: WHERE should this constraint be applied?

## Decision Framework
- If most signals get rejected for concentration → add pre-flight check in
  BaseStrategy or position sizing utility so signals are right-sized before
  reaching Risk Manager
- If this is an edge case (tight stop + expensive stock + small account) →
  document as known behavior, the Risk Manager gate is working as designed
- Either way, the system is SAFE (Risk Manager catches it), this is about
  reducing noise and wasted processing

## If Fix is Needed
Add a pre-flight concentration cap in the position sizing path:

    max_position_value = total_equity * max_single_stock_pct
    max_shares_by_concentration = int(max_position_value / entry_price)
    shares = min(shares_by_risk, max_shares_by_concentration)

This should happen BEFORE SignalEvent is emitted, not in Risk Manager
(which remains the backstop).

## Definition of Done
- Position sizing path fully traced and documented
- Root cause identified (systemic vs edge case)
- Fix applied if systemic, or documented as known behavior if edge case
- If fixed: verify with a manual test that signals come out right-sized
- Commit: fix(sizing): [description] OR docs: position sizing investigation
```

---

### Session B2: Time Stop + EOD Flatten Validation Script

```
# ARGUS Sprint 21.5 — Session B2: Time Stop + EOD Flatten Script

## Context
Read CLAUDE.md for context. The Session 8 validation script explicitly
noted that time stop and EOD flatten were NOT covered because they require
waiting 30+ minutes or time manipulation. This session creates a targeted
test using FixedClock.

## Goal
Create scripts/test_time_stop_eod.py that validates time stop triggers
and EOD flatten using FixedClock, without needing to wait real time.

## Implementation

The script should:
1. Connect to IBKR paper (with DU prefix + port 4002 safety check)
2. Create Order Manager with FixedClock from argus/core/clock.py
3. Place a small position (1 share of a liquid stock like SPY)
4. Wait for fill confirmation
5. Set FixedClock to current time + max_hold_minutes for the strategy
6. Trigger Order Manager's tick/poll cycle
7. Verify position was closed with exit_reason = "time_stop"
8. Verify trade logged in TradeLogger

9. Place another small position
10. Wait for fill
11. Set FixedClock to 15:55 ET (3:55 PM — EOD flatten time)
12. Trigger Order Manager's EOD check
13. Verify position was closed with exit_reason = "eod_flatten"
14. Verify trade logged in TradeLogger

15. Clean up: ensure no open positions or orders remain
16. Print PASS/FAIL summary

## Key Files
- argus/core/clock.py — FixedClock implementation
- argus/execution/order_manager.py — time stop + EOD flatten logic
- argus/execution/ibkr_broker.py — broker connection

## Notes
- FixedClock is already built and tested (DEC-039/MD-4a-5)
- Order Manager and strategies accept a Clock protocol
- Check how FixedClock is injected — may need to pass it through config
  or directly to Order Manager constructor
- If FixedClock injection is not straightforward, check how tests do it
  (grep for FixedClock in tests/)

## Definition of Done
- scripts/test_time_stop_eod.py created
- Script runs successfully against IBKR paper
- Time stop trigger verified with correct exit reason
- EOD flatten trigger verified with correct exit reason
- Both trades persisted in TradeLogger
- No orphan positions after script completes
- Commit: feat(integration): time stop and EOD flatten validation script
```

---

### Session B3: Operational Scripts + Logging Tuning

```
# ARGUS Sprint 21.5 — Session B3: Operational Scripts + Logging

## Context
Read CLAUDE.md for context. ARGUS needs operational tooling for daily use.
Steven operates from Taipei, starting the system ~10:15 PM local (15 min
before US market open) and reviewing after US close the next morning.

## Part 1: Startup Script

Create scripts/start_live.sh:

    #!/usr/bin/env bash
    set -euo pipefail

    # Pre-flight checks
    # 1. Check .env exists
    # 2. Check IB Gateway is running (try connecting to port 4002)
    # 3. Check DATABENTO_API_KEY is set
    # 4. Check no existing ARGUS process running

    # Create dated log directory
    LOG_DIR="logs"
    LOG_FILE="${LOG_DIR}/argus_$(date +%Y-%m-%d).log"
    mkdir -p "$LOG_DIR"

    # Start ARGUS
    echo "[$(date)] Starting ARGUS in live mode..."
    python -m argus.main --config config/system_live.yaml \
      2>&1 | tee -a "$LOG_FILE" &

    ARGUS_PID=$!
    echo "$ARGUS_PID" > "$LOG_DIR/argus.pid"
    echo "[$(date)] ARGUS started (PID: $ARGUS_PID)"
    echo "[$(date)] Log: $LOG_FILE"

    # Optionally start frontend
    if [[ "${1:-}" == "--with-ui" ]]; then
      echo "[$(date)] Starting Command Center UI..."
      cd argus/ui && npm run dev &
      UI_PID=$!
      echo "$UI_PID" > "$LOG_DIR/ui.pid"
      echo "[$(date)] UI started (PID: $UI_PID)"
    fi

Adjust as needed based on actual project structure. Make executable.

## Part 2: Shutdown Script

Create scripts/stop_live.sh:

    #!/usr/bin/env bash
    set -euo pipefail

    PID_FILE="logs/argus.pid"

    if [[ ! -f "$PID_FILE" ]]; then
      echo "No ARGUS process found (no PID file)"
      exit 1
    fi

    ARGUS_PID=$(cat "$PID_FILE")
    echo "[$(date)] Sending graceful shutdown to ARGUS (PID: $ARGUS_PID)..."

    # Send SIGINT for graceful shutdown (positions closed, DB committed)
    kill -INT "$ARGUS_PID" 2>/dev/null || true

    # Wait up to 60 seconds for clean exit
    for i in $(seq 1 60); do
      if ! kill -0 "$ARGUS_PID" 2>/dev/null; then
        echo "[$(date)] ARGUS stopped cleanly after ${i}s"
        rm -f "$PID_FILE"
        # Also stop UI if running
        if [[ -f "logs/ui.pid" ]]; then
          kill "$(cat logs/ui.pid)" 2>/dev/null || true
          rm -f "logs/ui.pid"
        fi
        exit 0
      fi
      sleep 1
    done

    echo "[$(date)] WARNING: ARGUS did not stop gracefully. Force killing..."
    kill -9 "$ARGUS_PID" 2>/dev/null || true
    rm -f "$PID_FILE"

Make executable. Test both scripts (start then stop) with a quick
non-market-hours run to verify the mechanics work.

## Part 3: Logging Level Tuning

Review and adjust logging levels for production use. The goal is: enough
info to diagnose issues, not so much that logs become unreadable or fill
disk.

Target levels:
- Strategy decisions (signal generated, rejected, state transition): INFO
- Individual candle bars received: DEBUG (not INFO — too noisy)
- Order events (placed, cancelled, modified): INFO
- Fill events: INFO
- System health checks: INFO
- Connection events (connect/disconnect/reconnect): INFO
- Tick-level price updates: DEBUG only
- Indicator computation details: DEBUG only
- Risk Manager evaluations: INFO for rejections, DEBUG for approvals
- Orchestrator regime/allocation updates: INFO
- Scanner watchlist results: INFO

Find the logging statements that need adjustment:

    grep -rn "logger\.\(info\|debug\|warning\)" argus/data/databento_data_service.py | head -20
    grep -rn "logger\.\(info\|debug\|warning\)" argus/strategies/ | head -30
    grep -rn "logger\.\(info\|debug\|warning\)" argus/execution/ | head -30

Adjust any that are too verbose at INFO (especially per-bar and per-tick
logging). The live observation generated ~988K log lines in 30 minutes —
that's way too much for production.

## Definition of Done
- scripts/start_live.sh created and executable
- scripts/stop_live.sh created and executable
- Both scripts tested (start, verify running, stop, verify stopped)
- Logging levels adjusted for production
- Quick non-market test: start → run 2 min → stop → check log volume
- Commit: feat(ops): startup/shutdown scripts + production logging levels
```

---

### Session B4: LIVE_OPERATIONS.md + Command Center Pre-Check

```
# ARGUS Sprint 21.5 — Session B4: Operations Guide + UI Pre-Check

## Context
Read CLAUDE.md for context. This session creates the operations manual
and pre-checks the Command Center code for live data readiness.

## Part 1: Create docs/LIVE_OPERATIONS.md

Write a comprehensive operations guide covering:

### 1. Daily Startup Procedure
- IB Gateway: launch, log into paper account, verify "DU" prefix
- Verify .env configuration
- Run scripts/start_live.sh [--with-ui]
- Verify startup in logs (all 12 phases complete)
- Verify in Command Center: Dashboard loads, system health green

### 2. Daily Shutdown Procedure
- Run scripts/stop_live.sh
- Verify: all positions closed, no open orders
- Verify: log shows clean shutdown
- IB Gateway: can leave running or close

### 3. Monitoring During Operation
- Command Center pages to check:
  - Dashboard: live prices updating, strategy bars showing deployment
  - Orchestrator: regime badge, allocation donut, decision timeline
  - System: all components healthy (green)
- Terminal: watch for ERROR/WARNING in logs
- Key log messages to watch for:
  - "Signal generated" — strategy found a setup
  - "Risk: APPROVED/REJECTED" — risk gate outcome
  - "Order filled" — trade executed
  - "Position closed" — trade completed
  - "Reconnecting" — connection issue (usually recovers)
  - "STALE DATA" — data gap (investigate if persistent)

### 4. Mid-Session Restart
- If ARGUS crashes or needs restart during market hours:
  1. Run stop script (or kill if unresponsive)
  2. Check IBKR for open positions/orders (they persist on broker side)
  3. Start ARGUS — reconstruct_from_broker() will recover state
  4. Verify positions in Command Center match IBKR

### 5. IB Gateway Maintenance
- IB Gateway requires daily restart (IBKR enforces nightly disconnect)
- Gateway typically disconnects ~11:45 PM ET (Sunday–Friday)
- ARGUS reconnection handler should recover automatically
- If it doesn't: stop ARGUS, restart Gateway, start ARGUS
- Docker container option: ibkr/gateway Docker image for auto-restart

### 6. Emergency Procedures
- **Flatten All**: Command Center Orchestrator page → Flatten All button
  (or POST /api/v1/orchestrator/flatten-all with JWT)
- **Pause All**: Command Center → Pause All (stops new signals, keeps positions)
- **Kill Switch**: scripts/stop_live.sh (graceful) or kill -9 (nuclear)
- After emergency: check IBKR directly for position/order state

### 7. Common Issues
- "Connection refused on port 4002" → IB Gateway not running or not in API mode
- "data_end_after_available_end" → Historical data lag (scanner uses fallback — normal)
- "Single-stock exposure would exceed limit" → Position sizing vs concentration (known behavior, Risk Manager working as designed)
- "Scanner fallback to static list" → Databento historical data lag (normal before market open)
- "Regime: range_bound (fallback)" → SPY data not yet available (normal at startup)

### 8. Taipei Timezone Reference
| Event | ET | Taipei |
|-------|-----|--------|
| Start system | 9:15 AM | 10:15 PM |
| Market open | 9:30 AM | 10:30 PM |
| ORB window | 9:35–11:30 | 10:35 PM–12:30 AM |
| VWAP window | 10:00–12:00 | 11:00 PM–1:00 AM |
| PM Momentum | 2:00–3:30 | 3:00–4:30 AM |
| EOD flatten | 3:55 | 4:55 AM |
| Market close | 4:00 | 5:00 AM |

## Part 2: Command Center Live-Readiness Audit

Before tomorrow's live market session, review the UI code for potential
issues with real data (vs dev mock data). This is a code audit, not a
runtime test.

Check each page's data consumption:

    grep -rn "mockData\|devMode\|--dev\|mock" argus/ui/src/ | grep -v node_modules | grep -v __tests__

For each page, verify:
1. **Null/undefined guards**: What happens if an API endpoint returns
   empty data? (no trades yet, no positions, no decisions)
2. **Data shape assumptions**: Do components assume arrays are non-empty?
   Do they handle 0 values in denominators (win rate with 0 trades)?
3. **Real string lengths**: Symbol names, dollar amounts, percentages —
   do they overflow their containers at realistic values?
4. **Timestamp handling**: Do charts handle today's-data-only correctly?
   (Equity curve with 1 data point, P&L histogram with 1 bar)
5. **WebSocket data format**: Does the WS message format from the live
   API match what the frontend expects?

Focus on: Dashboard, Trade Log, Orchestrator, System pages (most likely
to surface issues with live data). Pattern Library and Debrief are less
data-dependent.

Fix any obvious null guards or data shape issues you find.

## Definition of Done
- docs/LIVE_OPERATIONS.md created with all 8 sections
- UI code audited for live data readiness
- Null guard fixes applied if found
- Commit: docs: LIVE_OPERATIONS.md + UI live data readiness fixes
```

---

### Session B5: Documentation Sync

```
# ARGUS Sprint 21.5 — Session B5: Documentation Updates

## Context
Read CLAUDE.md for context. This session updates all project documents
to reflect Sprint 21.5 progress through Block B completion.

## Checklist — check each doc, update ONLY if something changed

### 1. docs/decision-log.md
Check current highest DEC number first. Add any new decisions from
Sessions A1, B0-B4 that aren't already logged. Examples:
- Scanner resilience for historical data lag (B0)
- Position sizing investigation outcome (if a fix was made)
- Time stop/EOD validation approach (if noteworthy)
- Logging level standards (if worth codifying)
- EQUS.MINI diagnostic results

### 2. docs/sprints/SPRINT_215_SPEC.md
Update session outcomes for all completed sessions:
- Session A1 outcomes (validation script results, EOD blocked by scanner)
- Note Block B sessions as completed with outcomes
- Update remaining sessions to reflect Block C plan

### 3. CLAUDE.md
Update "Current State" section:
- Sprint 21.5 status: Blocks A+B complete, Block C (live market validation) pending
- Test count: current numbers
- Note: validation scripts executed, operational scripts created
- Note: Scanner resilience fix applied
- Note: LIVE_OPERATIONS.md created
- Note: EQUS.MINI diagnostic results

### 4. docs/project-knowledge.md
Draft the Sprint 21.5 Build Track entry update. Include:
- Accurate test counts (pytest + Vitest)
- Key deliverables list
- DEC references
- Status: pending full-day market validation (Block C)

This will be synced to Claude.ai project instructions after sprint
completion.

### 5. docs/10_PHASE3_SPRINT_PLAN.md
Update Sprint 21.5 tracking entry with current progress.

## Definition of Done
- All docs checked and updated as needed
- No DEC number conflicts (verify sequencing)
- Sprint spec reflects actual session outcomes
- Commit: docs: Sprint 21.5 Block A+B documentation sync
```

---

## ⏸ Code Review Checkpoint (Claude.ai)

> **After Block B is complete, check in with Claude.ai (me) before proceeding to Block C.**
>
> Bring:
> - **EQUS.MINI diagnostic results** (this is the #1 priority item)
> - Scanner resilience fix summary
> - Position sizing investigation outcome
> - Any other fixes made during Block B
> - Current test counts
> - Any issues or concerns
>
> I'll review and confirm you're clear for the full market day (Block C).
> If EQUS.MINI live streaming doesn't work, we need to pivot to XNAS.ITCH
> before the market day — I'll help with that decision during the review.

---

## Block C: Full Market Day Validation (tomorrow, market hours)

### Session C1: Full Trading Day — All Strategies Live 🎯

```
# ARGUS Sprint 21.5 — Session C1: Full Trading Day 🎯

## Context
Read CLAUDE.md and docs/LIVE_OPERATIONS.md for context.
THIS IS THE MILESTONE SESSION. First full-day live market run with all
four strategies active, Databento data, IBKR paper execution.

## MUST be run during US market hours (9:30 AM – 4:00 PM ET)
## Start 15 minutes before market open (9:15 AM ET / 10:15 PM Taipei)

## ⚡ GATE CHECK #1: EQUS.MINI Live Stream (do this FIRST) ⚡

Before starting the full system, verify live streaming works:

    # Quick test — does EQUS.MINI deliver live data right now?
    python scripts/diagnose_databento.py

If the diagnostic shows live subscription FAILS:
- STOP. Do not proceed with full system startup.
- Check the error message carefully:
  - "license" error → EQUS.MINI may not support live on Standard plan
  - "dataset not found" → typo or wrong dataset name
  - Connection timeout → network issue, retry
- If live streaming doesn't work with EQUS.MINI, switch config to
  XNAS.ITCH (which worked in Sessions 4-6):
      # In config/system_live.yaml, change:
      dataset: "XNAS.ITCH"
  Then re-run diagnostic to confirm XNAS.ITCH still works.
- Document the finding — this is a significant DEC entry.

If the diagnostic shows live subscription SUCCEEDS:
- Wait for market open (9:30 AM) and verify actual data arrives
- If ohlcv-1m bars appear for SPY within 2 minutes of open → proceed
- If no data after 2 minutes → check logs, may need XNAS.ITCH fallback

## Pre-Session Checklist
- [ ] EQUS.MINI (or XNAS.ITCH) live stream verified ← GATE CHECK #1
- [ ] IB Gateway running, logged into PAPER account (verify "DU" prefix)
- [ ] Databento subscription active
- [ ] .env has all required keys
- [ ] Command Center frontend running (cd argus/ui && npm run dev)
- [ ] All four strategies enabled in config
- [ ] scripts/start_live.sh tested (Block B)
- [ ] LIVE_OPERATIONS.md open for reference

## Startup

Use the startup script:

    ./scripts/start_live.sh --with-ui

Or if script needs adjustment, start manually:

    python -m argus.main --config config/system_live.yaml 2>&1 | tee logs/argus_$(date +%Y-%m-%d).log &
    cd argus/ui && npm run dev &

Open Command Center in browser (desktop + phone if possible).

## Monitoring Timeline

### Pre-Market (9:15–9:30 AM ET)
- [ ] All 12 startup phases complete
- [ ] Databento connection established (check: "DatabentoDataService started")
- [ ] IBKR paper connection established
- [ ] Scanner generates watchlist (or graceful fallback with clear log message)
- [ ] Regime classification runs (SPY data)
- [ ] All 4 strategies registered and healthy
- [ ] Command Center Dashboard loads with real data
- [ ] Command Center System page: all components green

### 9:30–9:35 AM (Opening Range)
- [ ] CandleEvents flowing for all watchlist symbols
- [ ] ORB strategies tracking opening range
- [ ] Indicators computing (check a few values against TradingView)

### 9:35–10:00 AM (ORB Signal Window)
- [ ] ORB Breakout evaluating breakout conditions
- [ ] ORB Scalp evaluating scalp conditions
- [ ] Signals generated OR correctly suppressed (log evidence either way)
- [ ] If signals: Risk Manager approval/rejection logged
- [ ] If trades: positions visible in Command Center

### 10:00 AM–12:00 PM (VWAP Reclaim Window)
- [ ] VWAP Reclaim state machine transitioning (WATCHING → ABOVE/BELOW)
- [ ] Signals generated or correctly suppressed
- [ ] Cross-strategy allocation checks working
- [ ] Position sizing reasonable (check against Block B investigation)

### 12:00–2:00 PM (Quiet Period)
- [ ] System stable, no excessive logging
- [ ] Data still flowing (spot check a few symbols)
- [ ] No memory leaks (check process RSS: ps aux | grep argus)
- [ ] WebSocket still connected (Command Center updating)
- [ ] Regime monitoring running (30-min cycle)

### 2:00–3:30 PM (Afternoon Momentum Window)
- [ ] Afternoon Momentum detecting consolidation patterns
- [ ] State machine: WATCHING → ACCUMULATING → CONSOLIDATED (or REJECTED)
- [ ] Signals generated or correctly suppressed

### 3:45 PM (Afternoon Momentum Force Close)
- [ ] Any open PM Momentum positions force-closed (DEC-159)
- [ ] Exit reason: "force_close" or "time_stop"

### 3:55 PM (EOD Flatten)
- [ ] Order Manager EOD flatten triggers
- [ ] ALL remaining positions closed
- [ ] ALL remaining orders cancelled

### 4:00 PM (Market Close)
- [ ] Orchestrator EOD review executes
- [ ] TradeLogger has all trades from today
- [ ] No orphan positions on IBKR
- [ ] No open orders remaining

## Post-Market Verification

    # Check trades
    python -c "
    from argus.analytics.trade_logger import TradeLogger
    import asyncio
    async def check():
        tl = TradeLogger('data/argus.db')
        await tl.initialize()
        trades = await tl.get_trades(limit=50)
        print(f'Trades today: {len(trades)}')
        for t in trades:
            print(f'  {t.symbol} {t.side} {t.shares}sh @ {t.entry_price} -> {t.exit_price} ({t.exit_reason})')
    asyncio.run(check())
    "

    # Check for errors
    grep -c "ERROR" logs/argus_$(date +%Y-%m-%d).log
    grep "ERROR" logs/argus_$(date +%Y-%m-%d).log | head -20

    # Check for warnings
    grep -c "WARNING" logs/argus_$(date +%Y-%m-%d).log

    # Check reconnection events
    grep -i "reconnect\|disconnect" logs/argus_$(date +%Y-%m-%d).log

    # Check data gaps
    grep -i "stale\|gap\|missing" logs/argus_$(date +%Y-%m-%d).log

    # Check memory (if still running)
    ps aux | grep argus

## Command Center Verification (during session)

While the system runs, verify ALL 7 pages with live data:

### Dashboard
- [ ] OrchestratorStatusStrip shows current phase
- [ ] StrategyDeploymentBar shows strategy allocations with accent colors
- [ ] GoalTracker shows pace (may be N/A on first day)
- [ ] MarketStatus shows live market data
- [ ] TodayStats shows real metrics
- [ ] SessionTimeline shows strategy windows + "now" marker
- [ ] RecentTrades shows trades (if any occurred)
- [ ] OpenPositions shows real-time prices (WebSocket updating)

### Trade Log
- [ ] Real trades from today visible
- [ ] Filtering by strategy works
- [ ] Pagination works
- [ ] CSV export works
- [ ] Click trade → TradeDetailPanel opens with real data

### Performance
- [ ] Metrics compute from real trades (even if limited)
- [ ] Equity curve renders (even with 1 day of data)
- [ ] No divide-by-zero or NaN display issues

### Orchestrator
- [ ] Session phase badge correct
- [ ] Regime classification showing real SPY-based result
- [ ] Strategy operations grid shows all 4 strategies
- [ ] Decision timeline shows real decisions
- [ ] Capital allocation donut reflects real state

### Pattern Library
- [ ] All 4 strategy cards visible
- [ ] Pipeline stages correct
- [ ] Spec sheets load (click into a strategy)
- [ ] Performance tab shows real data (if available)

### The Debrief
- [ ] Create a REAL Pre-Market briefing (test the creation flow)
- [ ] Create a REAL journal entry documenting this first full session
- [ ] Research Library: verify repo docs load correctly

### System
- [ ] All component health statuses reflect reality
  - Databento: connected
  - IBKR: connected
  - Strategies: active/inactive based on time window
  - Event Bus: healthy
  - Database: healthy

### Responsive Design (quick check during quiet period)
- [ ] Resize browser to tablet width (834px) — layout OK?
- [ ] Resize to phone width (393px) — layout OK?
- [ ] If PWA installed: open on phone — usable for monitoring?

## Take Notes On Everything
- What worked perfectly
- What had issues (with error messages)
- What UI elements didn't render correctly with real data
- Data quality observations
- Suggestions for improvement

## Definition of Done
- EQUS.MINI (or XNAS.ITCH) live streaming confirmed working
- Full 9:30 AM – 4:00 PM session completed without system crash
- All 4 strategies processed data during their active windows
- At least one complete data cycle per strategy observed
- All 7 Command Center pages verified with live data
- Post-market verification clean (no orphans)
- Session notes saved
- Commit: feat(integration): first full trading day — all strategies operational
```

---

### Session C2: UI Fixes + Taipei Workflow Test

```
# ARGUS Sprint 21.5 — Session C2: UI Fixes + Overnight Workflow

## Context
Read CLAUDE.md for context. Session C1 completed the first full trading
day. This session fixes any UI issues found and tests the real Taipei
overnight workflow.

## MUST span a US market session. Start ~10:15 PM Taipei (9:15 AM ET).

## Part 1: Fix Session C1 Issues (before market open)

Fix all issues documented in Session C1 notes:
- UI rendering issues with real data
- Null guard gaps
- Data shape mismatches
- WebSocket issues
- Any backend issues discovered

Commit each category separately with descriptive messages.

## Part 2: Taipei Overnight Workflow (during market hours)

This tests Steven's ACTUAL daily workflow:

1. Start system at ~10:15 PM Taipei using startup script:

       ./scripts/start_live.sh --with-ui

2. Open Command Center on phone (mobile browser or PWA)
3. Monitor during pre-market and first 30–60 min of trading on phone
4. Assess mobile experience (take notes):
   - Dashboard readable? Key metrics visible above the fold?
   - Can you see enough to decide if intervention is needed?
   - WebSocket updates working on mobile?
   - Any layout issues at phone width with real data?
5. Let system run unattended for the remainder of session (simulate sleeping)
6. After US market close (5:00 AM Taipei), review results:
   - Check Command Center Trade Log for today's trades
   - Check Orchestrator decision timeline
   - Check Performance page metrics
   - Review The Debrief — create EOD briefing
7. Shut down cleanly:

       ./scripts/stop_live.sh

8. Verify clean state:
   - All positions closed, no orphans
   - Database has today's trades
   - Logs captured full session

9. NEXT-DAY STARTUP TEST (can be done any time after shutdown):
   - Fresh start with startup script
   - Verify: system starts clean, no stale state from yesterday
   - Verify: database has yesterday's trades, today starts fresh
   - Verify: Command Center shows yesterday's trades in history
   - Shut down again (don't need to wait for market)

## Definition of Done
- All Session C1 UI fixes applied
- Full overnight workflow completed: start → run → unattended → review → shutdown
- Clean shutdown → clean next-day startup verified
- Mobile monitoring experience assessed with notes
- Commit: fix(integration): UI fixes + overnight workflow verification
```

---

### Session C3: Stability + Final Fixes (if needed)

```
# ARGUS Sprint 21.5 — Session C3: Stability Observation (if needed)

## Context
This session is OPTIONAL — only needed if Sessions C1 or C2 revealed
issues that require another full market session to validate.

If C1 and C2 were clean, skip directly to Block D.

## When to Use This Session
- C1 had crashes or data issues that were fixed but need re-validation
- C2 overnight workflow had problems that need a retry
- WebSocket stability issues need longer observation
- Memory growth detected that needs monitoring over full session
- Had to switch from EQUS.MINI to XNAS.ITCH and need to verify full day

## Goals
1. Third full market session — focus on whatever was problematic
2. Monitor for:
   - Memory usage over time (sample every 30 min)
   - WebSocket connection stability over full session
   - Databento stream reliability (reconnections? gaps?)
   - Log volume with production logging levels
3. Fix anything found
4. If clean: Sprint 21.5 live validation is COMPLETE

## Definition of Done
- Issue that triggered this session is resolved
- Full session clean
- Commit: fix(integration): [specific fix description]
```

---

## ⏸ Final Code Review (Claude.ai)

> **After Block C, check in with Claude.ai (me) for final Sprint 21.5 review.**
>
> Bring:
> - Full Session C1 notes (the big trading day)
> - Which dataset worked (EQUS.MINI or XNAS.ITCH fallback?)
> - UI issues found and fixed
> - Overnight workflow assessment
> - Any issues still open
> - Current test counts
> - Log analysis results (error count, warning count)
> - Mobile experience notes
>
> I'll do a final review and confirm Sprint 21.5 is complete, or identify any remaining gaps.

---

## Block D: Sprint Closeout (after Block C review)

### Session D1: Final Documentation + Sprint Completion

```
# ARGUS Sprint 21.5 — Session D1: Sprint Closeout

## Context
Read CLAUDE.md for context. All live validation is complete. This is
the final documentation pass and sprint closeout.

## Part 1: Final Documentation Updates

### docs/decision-log.md
Add any remaining DEC entries from Blocks A–C. Include:
- Final dataset decision (EQUS.MINI confirmed or XNAS.ITCH fallback)
- Scanner resilience pattern
- Any other architectural decisions from live testing

### docs/sprints/SPRINT_215_SPEC.md
Update ALL session outcomes through completion. Add:
- Final metrics (total trades executed, strategies that generated signals)
- Issues found and resolved
- Issues deferred to future sprints
- Sprint duration and session count

### CLAUDE.md
Final update:
- Sprint 21.5: ✅ COMPLETE
- Final test counts
- Live integration status: Databento [dataset] + IBKR paper validated
- Operational: LIVE_OPERATIONS.md, startup/shutdown scripts
- Next: Sprint 21.6 (backtest re-validation) + Sprint 22 (AI Layer)

### docs/project-knowledge.md
Final Build Track entry:

    - Sprint 21.5 (Live Integration): ✅ COMPLETE — XXXX tests (pytest)
      + XXX (Vitest), [dates]. Databento [dataset] live streaming
      (DEC-237, DEC-241–244). IBKR paper trading via IB Gateway (DEC-236).
      Scanner resilience for historical data lag. flatten_all() SMART
      routing fix. get_open_orders() Broker ABC addition. Full trading
      day stability validated. Position management lifecycle + state
      reconstruction + reconnection validated. Operational scripts +
      LIVE_OPERATIONS.md. [X] sessions total.

Update Key Decisions section with all new DECs.
Update Validation Track status.

### docs/10_PHASE3_SPRINT_PLAN.md
Move Sprint 21.5 to completed table with final metrics.

### docs/risk-register.md
Update any risks validated or invalidated during integration:
- RSK-022 (IB Gateway reliability): status update based on experience
- Any new risks discovered during live testing

## Part 2: Clean Up

- Remove any temporary debug logging added during integration
- Remove any test scripts that are no longer needed (keep the validation
  scripts — they're useful for future regression testing)
- Verify .gitignore covers logs/, .env, data/*.db

## Part 3: Final Verification

    # All tests pass
    python -m pytest tests/ -v --tb=short 2>&1 | tail -10
    cd argus/ui && npx vitest run 2>&1 | tail -10

    # System starts cleanly
    python -m argus.main --config config/system_live.yaml --dry-run

    # No uncommitted changes
    git status

## Part 4: Sprint 21.6 Spec Stub

Create docs/sprints/SPRINT_216_SPEC.md with a brief outline:
- Purpose: DEC-132 backtest re-validation with Databento data
- Scope: Re-run VectorBT sweeps + walk-forward for all 4 strategies
- Data source: Databento historical ([confirmed dataset])
- Compare against Alpaca-data baselines
- Adjust parameters if material differences found
- Runs parallel with Sprint 22

Don't write full prompts — just the outline. Full spec after Sprint 21.5
review with Claude.ai.

## Definition of Done
- All docs updated and consistent
- No temporary debug code remaining
- All tests pass
- Clean git status
- Sprint 21.6 stub created
- Final commit: docs: Sprint 21.5 complete — all documentation updated
- Tag: git tag sprint-21.5-complete
```

---

## Summary: Complete Session Sequence

| # | Session | Market? | Est. Time | Notes |
|---|---------|---------|-----------|-------|
| A1 | Validation scripts | — | ✅ DONE | 13/13 + 4/4 PASS |
| **B0** | **Scanner resilience + EQUS.MINI diagnostic** | **No** | **45–60 min** | **⚡ NEW — do first** |
| B1 | Position sizing investigation | No | 30–60 min | Tonight |
| B2 | Time stop + EOD validation script | No | 30–45 min | Tonight |
| B3 | Operational scripts + logging | No | 45–60 min | Tonight |
| B4 | LIVE_OPERATIONS.md + UI pre-check | No | 60–90 min | Tonight |
| B5 | Documentation sync | No | 30–45 min | Tonight |
| **⏸** | **Claude.ai review checkpoint** | — | — | **Bring EQUS.MINI diagnostic results** |
| C1 | Full trading day 🎯 | YES (tomorrow) | 7+ hours | EQUS.MINI gate check first |
| C2 | UI fixes + Taipei overnight workflow | YES (next day) | 7+ hours | Real workflow test |
| C3 | Stability re-test (if needed) | YES | 7+ hours | Optional |
| **⏸** | **Claude.ai final review** | — | — | **Before Block D** |
| D1 | Sprint closeout + docs | No | 60–90 min | Final |

**Total: 9–11 Claude Code sessions + 2 code reviews to Sprint 21.5 completion.**
