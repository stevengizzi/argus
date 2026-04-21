# ARGUS — Paper Trading Validation Guide

> *Version 2.0 | April 21, 2026 (audit FIX-15 rewrite)*
> *Supersedes v1.0 (Feb 16, 2026), which documented the retired Alpaca paper-trading stack.*
> *ARGUS paper trading is now Databento (market data) + IBKR paper (execution). See also:
> [live-operations.md](live-operations.md) for the full daily runbook and
> [pre-live-transition-checklist.md](pre-live-transition-checklist.md) for the config
> values that must be restored before live trading.*

---

## 1. What Paper Trading Is and Why It Matters

Paper trading is simulated trading with fake money against real market data. ARGUS connects to
**IBKR paper** (via IB Gateway on port 4002) for order routing and to **Databento EQUS.MINI** for
market data. IBKR paper accounts mirror the live API — same order types, same WebSocket streams,
same bracket-order semantics — but with a virtual balance and no real money at risk.

This is not optional. Paper trading is the bridge between "all tests pass" and "I trust this
system with real capital." You are validating that:

- The system runs without crashing for an entire trading session (9:30 AM – 4:00 PM ET)
- Orders in `data/argus.db` match what IBKR Gateway and TWS show
- Strategies identify reasonable setups (not garbage stocks, not phantom breakouts)
- Risk limits, circuit breakers, and the quality engine actually gate the signals they should
- Stops, trailing stops, partial profit-taking on T1, time stops, and EOD flatten all work
- The system recovers gracefully from the inevitable weirdness of live data (gaps, halts,
  thin liquidity, Databento reconnections, IBKR 201/202 errors, startup zombie positions)

**Minimum validation period:** 3 trading days. **Recommended:** 5–10 trading days before any
live-capital work. After any config change that affects order flow or risk, reset the counter.

**Success criteria:** Zero crashes, zero unlogged trades, zero missed EOD flattens, risk limits
never exceeded, and at least several complete trade lifecycles observed across strategies
(entry → stop/T1 partial/trail → exit).

---

## 2. Setting Up Your IBKR Paper Trading Environment

### 2.1 IBKR Paper Account

Paper trading requires an Interactive Brokers account with paper-trading enabled. If you don't
already have one:

1. Sign up at [interactivebrokers.com](https://www.interactivebrokers.com/) for an individual
   account. A live account is required to access paper trading (IBKR ties the paper login to
   a live identity).
2. Once the live account is approved, log in to Client Portal and enable the paper trading
   account. You will be issued a separate paper username (prefixed `DU…`).
3. Paper accounts start with $1,000,000 in virtual funds by default.

You do NOT need to fund the live account to paper-trade. ARGUS never places live orders from
the paper configuration as long as the Gateway is running in paper mode and ports are correct.

### 2.2 IB Gateway + IBC

ARGUS connects to IB Gateway (not TWS) on port **4002** (paper) / **4001** (live).
Install and configure IB Gateway plus IBC (the controller that keeps it up) per
[ibc-setup.md](ibc-setup.md).

Verify after setup:
- Gateway shows "Paper Trading" in the login banner
- Account number shown in Gateway starts with `DU` (paper indicator)
- API Settings: "Enable ActiveX and Socket Clients" = checked
- Socket port = **4002**
- Read-Only API = unchecked
- "Allow connections from localhost only" = checked

### 2.3 Databento Market Data

ARGUS uses Databento EQUS.MINI for intraday OHLCV and ticks. Sign up at
[databento.com](https://databento.com/) and generate an API key. EQUS.MINI is the canonical
dataset (DEC-248).

The daily reference data and regime SPY bars come from FMP Starter plan; pre-market scanning
also runs through FMP. You will need both keys.

### 2.4 Configure ARGUS

Create `.env` in the project root (gitignored — never commit):

```bash
# Databento market data
DATABENTO_API_KEY=db-your_key_here

# FMP (pre-market scanner, reference data, daily SPY bars)
FMP_API_KEY=your_fmp_key_here

# API JWT secret (generate with: python -m argus.api.setup_password)
ARGUS_JWT_SECRET=your_secure_secret_here

# Optional — AI Copilot. Disabled gracefully if unset.
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Finnhub (optional — news + analyst recs for catalyst pipeline)
FINNHUB_API_KEY=your_finnhub_key_here
```

IBKR credentials are handled by IB Gateway (not `.env`). ARGUS connects to localhost:4002 with
no credentials — Gateway-side auth is sufficient.

Verify the config files that ARGUS reads for paper trading (config/system_live.yaml is the
authoritative file for paper + live):

```
config/
├── system_live.yaml          # Top-level: Databento + IBKR paper (THIS is what paper uses)
├── system.yaml               # Alpaca incubator legacy — NOT used for paper
├── brokers.yaml              # IBKR host, port 4002, client_id
├── risk_limits.yaml          # Daily/weekly loss limits (10x relaxed for paper)
├── orchestrator.yaml         # Regime, scheduling, throttle (paper: throttle disabled)
├── quality_engine.yaml       # Risk tiers (paper: 10x reduced risk per tier)
├── strategies/*.yaml         # Per-strategy config, includes `mode: live` or `mode: shadow`
├── experiments.yaml          # Variant spawning (enabled: true in paper)
├── historical_query.yaml     # DuckDB cache dir for research queries
└── ...
```

The paper-trading overrides that differ from live are documented in
[pre-live-transition-checklist.md](pre-live-transition-checklist.md) — restore those values
before live trading.

### 2.5 Monitoring (recommended)

**Healthchecks.io heartbeat:** See [live-operations.md §Monitoring](live-operations.md) for
`health.heartbeat_url_env`/`health.alert_webhook_url_env` wiring. URLs live in `.env`, not in
the YAML (DEF-005 resolved).

**Discord webhook:** Same mechanism — `alert_webhook_url_env` points at an environment variable
name.

### 2.6 Verify Your Setup (Dry Run)

```bash
python -m argus.main --dry-run
```

This should:
- Load `config/system_live.yaml` without errors
- Connect to IB Gateway at localhost:4002 and read account info (`DU…`)
- Connect to Databento and validate the API key
- Initialize all components through the 17-phase startup sequence
- Shut down cleanly without streaming data or placing orders

If dry-run fails:
- Confirm IB Gateway is running in paper mode on port 4002
- Confirm `.env` has a valid `DATABENTO_API_KEY` and `FMP_API_KEY`
- Confirm Databento is operational (status at databento.com)
- Check `logs/` for the startup-phase log messages

---

## 3. Your First Trading Day

### 3.1 Pre-Market (before 9:30 AM ET)

All market times are Eastern Time (ET). Market hours are 9:30 AM – 4:00 PM ET. The system's
EOD flatten fires at 3:55 PM ET by default; pre-EOD signal cutoff is 3:30 PM ET (Sprint 32.9).

> ⚠️ **Do not start ARGUS between ~22:30 ET and pre-market open (DEF-164).** Time-based
> after-hours auto-shutdown can collide with in-flight service init. Safe start windows:
> pre-market (≥ 04:00 ET) through standard shutdown.

Start 15–30 minutes before market open using the standard launcher, which runs 4 pre-flight
checks (IB Gateway port, `.env`, `DATABENTO_API_KEY`, no existing ARGUS process):

```bash
./scripts/start_live.sh            # backend only
./scripts/start_live.sh --with-ui  # backend + Command Center UI
```

Watch for the 17-phase startup sequence in the terminal. The "API server healthy" signal fires
only after the port is actually bound (Sprint 31.8 DEF-155 fix), so if it flips green, the
system really is ready.

Pre-market scanner results appear as log lines similar to:

```
INFO - UniverseManager resolved 3,812 viable symbols
INFO - FMP pre-market scan: 24 gapping candidates (gap > 2%)
INFO - Watchlist: TSLA +3.2%, NVDA +2.8%, AMD +2.1%, ...
```

If the scanner finds zero candidates on a quiet morning, strategies simply won't trade. If it
consistently finds zero, widen scanner filters in `config/scanner.yaml` or inspect FMP API
responses via `scripts/diagnose_databento.py` / FMP API logs.

### 3.2 Market Open (9:30 AM ET)

ORB strategies build their opening range during the first N minutes (per-strategy config).
Non-ORB strategies gate entries on their own per-strategy activation windows (VWAP Reclaim,
Afternoon Momentum, Red-to-Green, Bull Flag, Dip-and-Rip, HOD Break, Gap-and-Go, Pre-Market
High Break, Micro Pullback, VWAP Bounce, Narrow Range Breakout).

In the logs, you should see candle events arriving every minute and strategies tracking their
internal state.

### 3.3 Active Trading Window

Sample log sequence for a valid entry under the quality pipeline:

```
INFO - OrbBreakout signal: BUY TSLA @ 245.30 (stop 243.80, targets [247.30, 249.30])
INFO - SetupQualityEngine grade=A, composite_score=72 (pattern=30, volume=28, regime=14)
INFO - DynamicPositionSizer shares=80 (risk_pct=0.003 paper, risk_per_share=$1.50)
INFO - RiskManager approved signal for TSLA (80 shares)
INFO - OrderManager placing bracket for TSLA (entry + stop + T1 + T2)
INFO - IBKRBroker bracket submitted: parent=12345, stop=12346, t1=12347, t2=12348
INFO - IBKRBroker order filled: TSLA 80 @ 245.32
INFO - Position opened: TSLA 80 shares @ 245.32
```

After a position opens, the Order Manager monitors it via tick data:

- **T1 hit:** First partial exit. Stop moves to breakeven or trail activates (per
  `config/exit_management.yaml`, `trailing_stop.activation = on_t1` by default).
- **T2 hit:** Full exit. Trade complete.
- **Stop hit:** Full exit at loss. Broker-side stop is the safety net; client-side trail check
  provides belt-and-suspenders.
- **Time stop:** Per-signal `time_stop_seconds` expired (DEC-122). Exit at market.
- **Trail stop:** Client-side trail breach flattens the position (Sprint 28.5).
- **EOD flatten:** 3:55 PM ET. Synchronous fill verification with asyncio.Event per symbol
  (Sprint 32.9 fix for DEF-140). Pass 1 closes managed positions; Pass 2 flattens any
  broker-confirmed positions ARGUS didn't manage.

### 3.4 After Hours

- Use `./scripts/stop_live.sh` for graceful shutdown (SIGINT, 60s timeout, force kill fallback).
- Components shut down in reverse order (17-phase → phase-0).
- All pending writes are flushed. `evaluation.db` VACUUM runs on startup-reclaim when size
  exceeds 500 MB and freelist > 50% (Sprint 31.8 DEF-157 fix).

---

## 4. Daily Validation Checklist

Run this every day after the session. This is the most important part — you're building
confidence that the system behaves correctly.

### 4.1 Compare Database to IBKR

**IBKR Trader Workstation (TWS) or Client Portal** is the authoritative order/position view.
Log in with the paper account (`DU…`) and pull up "Account Management" → Activity → Trades.

**Query your local database:**

```bash
sqlite3 data/argus.db
```

Useful queries:

```sql
-- All trades from today
SELECT * FROM trades WHERE date(entry_time) = date('now');

-- Summary: count, wins, losses, P&L
SELECT
    COUNT(*) AS num_trades,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) AS losses,
    ROUND(SUM(realized_pnl), 2) AS total_pnl
FROM trades
WHERE date(entry_time) = date('now')
  AND entry_price_known = 1;   -- excludes DEF-159 reconstructed trades

-- Open positions (should be empty after EOD)
SELECT * FROM trades WHERE exit_time IS NULL;

-- Strategy-level daily summaries
SELECT * FROM strategy_daily_summary ORDER BY date DESC LIMIT 5;

-- Counterfactual (shadow / rejected signals tracked by Sprint 27.7)
SELECT COUNT(*) FROM counterfactual_positions WHERE date(entry_time) = date('now');
```

**What to verify:**

- Every IBKR fill has a corresponding trades row (same symbol, side, quantity, fill time within
  a second or two)
- Realized P&L agrees within slippage tolerance
- No "ghost" trades in `data/argus.db` absent from IBKR (indicates a logging bug or a
  startup-zombie reconstruction — the `entry_price_known` column filters those out)
- No open positions after EOD flatten (Pass 1 + Pass 2)

### 4.2 Log files

Logs are structured JSON. Useful filters:

```bash
grep '"level":"ERROR"'   logs/argus.log | tail -20
grep '"level":"WARNING"' logs/argus.log | tail -20
grep 'circuit_breaker'   logs/argus.log
grep 'margin_circuit'    logs/argus.log      # IBKR error 201 (Sprint 32.9)
grep 'reconcile'         logs/argus.log
grep 'reconnect'         logs/argus.log
grep 'signal_cutoff'     logs/argus.log      # pre-EOD cutoff events
```

### 4.3 Debrief export

The shutdown path writes `logs/debrief_YYYYMMDD.json` (DEC-348). This includes the
safety-summary block (margin-circuit status, EOD Pass 1/2 counts, signal-cutoff skips) plus the
final order/position state. The Command Center Debrief page also renders this data.

### 4.4 Trade quality review (subjective)

This is where your trading experience matters. Pull up the charts (TradingView, IBKR's chart,
or the Command Center Arena page) and look at the trades the system took:

- Were these reasonable setups per the strategy spec?
- Were stop placements sensible?
- Did any trades get stopped out immediately (possible sign of entering into resistance)?
- Did the quality grades reported by SetupQualityEngine correlate with outcome?
- Were the gap / PM-high / catalyst stocks the scanner found actually interesting?

You're not judging profitability yet — 3–5 days is statistically meaningless. You are judging
whether the system is making *sensible decisions* based on strategy logic.

### 4.5 Shadow strategies + experiment variants

Sprint 32.5 experiment pipeline and Sprint 27.7 counterfactual engine record shadow trades
alongside live ones. Check the **Shadow Trades** tab in the Command Center Trade Log and the
**Experiments** page (keyboard shortcut `0`) for variant and promotion state. With
`experiments.enabled=true` in paper, 22 shadow variants are actively collecting data.

---

## 5. Common Issues

### 5.1 No Trades Happening

Likely causes:

- **Scanner finding nothing** — quiet morning, or filters too restrictive in
  `config/scanner.yaml`. Check FMP response via `grep 'FMP' logs/argus.log`.
- **Quality engine rejecting signals** — all signals grading B or below in paper mode is
  expected during calibration; see quality_engine.yaml recalibration notes from Sprint 32.9.
- **Risk Manager or concentration limits rejecting** — check `OrderRejectedEvent` logs.
- **Margin circuit breaker open** — Sprint 32.9 margin circuit trips at 10 consecutive IBKR
  201 rejections; resets after 20 successful fills. Grep for `margin_circuit`.

### 5.2 Immediate Stop-Outs

- Opening range too tight → stop too close; review per-strategy ATR/R multipliers
- False breakouts bypassing confirmation filters → check strategy PatternParams in
  `config/strategies/*.yaml`
- Paper-trading IBKR repricing storm (DEF-100) — a thin-book-simulation artifact; ThrottledLogger
  suppresses the spam but positions still churn

### 5.3 IBKR Gateway Reconnects

IBKR paper occasionally drops the client connection, especially during high volatility. ARGUS
has reconnection logic in IBKRBroker with a 3-second hardcoded post-reconnect delay (Sprint
32.75) before re-querying the portfolio snapshot:

```
WARNING - IBKR disconnect. Reconnecting...
INFO    - IBKR reconnected. Waiting 3s before portfolio snapshot query.
INFO    - Portfolio snapshot: 2 positions recovered.
```

Occasional reconnects (1–3 per session) are normal. Frequent ones suggest Gateway instability
— restart IB Gateway and check the IBC launchd log.

Broker-side bracket orders (stop + T1 + T2) live on IBKR's servers and continue to execute
during an ARGUS outage. You only lose client-side active management (trail update, escalation,
time stops) during a disconnect.

### 5.4 EOD Flatten Not Firing

EOD flatten fires at 3:55 PM ET. If positions remain after 4:00 PM:

- Check system uptime — if ARGUS crashed before 3:55 PM, the flatten never ran
- Check logs for `eod_flatten_pass1_count`, `eod_flatten_pass2_count` (Sprint 31A DEF-144 safety
  summary attrs)
- Verify timezone handling — all market comparisons MUST convert UTC → ET (DEC-061)
- Sprint 32.9 added synchronous fill verification with asyncio.Event per symbol (30s timeout,
  1 retry) after the Sprint 31.8 DEF-140 root cause (`getattr(pos, "qty", 0)` vs `shares`)

**Manual cleanup:** Close stragglers via TWS or Client Portal directly. Track the incident.

### 5.5 Duplicate Sells / Position Flips

Sprint 31.8 DEF-158 fixed three independent duplicate-SELL root causes (flatten-timeout
resubmit, startup cleanup, stop-fill race). If you see a position flip negative (short) after
what should have been a close, capture the log sequence around the fills and file a new DEF.

### 5.6 DuckDB / HistoricalQueryService Hangs

If ARGUS start hangs at "Phase 12 HistoricalQueryService init" during non-market hours, see
DEF-164 (scheduling collision with after-hours shutdown) and DEF-165 (connection close hangs
when CREATE VIEW is interrupted). Mitigation: start ARGUS only inside the safe window (≥ 04:00
ET through standard shutdown).

### 5.7 Database / IBKR Inconsistencies

Investigate every inconsistency — these are the bugs that matter most for live trading:

- Order submitted but not filled (reviewed in `order_manager.log`, `data/argus.db.orders` is
  not persisted per DEF-031 — reconstruct from IBKR activity)
- Reconciliation ghost positions (DEF-098/099) — Sprint 27.8 auto-cleanup generates synthetic
  close records with `ExitReason.RECONCILIATION`; the `entry_price_known` column excludes these
  from metrics (DEF-159)
- Startup zombie flatten (Sprint 27.95) — zero-qty ghosts are silently skipped; real zombies
  are flattened via market order when `startup.flatten_unknown_positions: true`

---

## 6. Recording Your Observations

Keep a daily log. For each session record:

```
## Day N — [Date] — [Day of Week]

Market regime: [e.g., bullish_trending, range_bound, high_vol]
Scanner results: [count, quality of candidates]
Trades taken: [count, symbols, strategies]
Shadow trades: [counterfactual positions + experiment variant count]
Trades won/lost: [count each]
Total P&L: [dollar amount]
System uptime: [full session? restarts?]
Safety summary: [margin-circuit trips, EOD pass1/pass2 counts, signal-cutoff skips]

Issues found:
- [...]

Config changes considered:
- [...]

Questions for later:
- [...]
```

This log feeds into sprint planning and the Performance Workbench.

---

## 7. When to Stop Paper Trading and Move Forward

Paper trading validation is complete when ALL of the following are true:

1. **Stability:** 3+ full sessions with zero crashes and zero unhandled exceptions.
2. **Data integrity:** Every trade in `data/argus.db` (filtered by `entry_price_known = 1`)
   matches IBKR's activity history. No ghost trades, no missing trades.
3. **Risk compliance:** Daily loss limits, weekly loss limits, concentration cap, position
   sizing, circuit breakers (including margin-circuit Sprint 32.9), and the quality pipeline
   all functioned correctly. No limit was exceeded.
4. **Complete lifecycle:** Observed at least one trade through full lifecycle — entry → stop
   management (breakeven on T1 or trail activation) → exit (T2, stop, time stop, trail, or
   EOD flatten). Ideally you've seen multiple exit types.
5. **EOD flatten:** Works correctly every day (Pass 1 + Pass 2). No positions remain after
   market close.
6. **Recovery:** If any restarts happened, the system reconstructed its state correctly — Risk
   Manager daily P&L accurate, Order Manager recovered open positions, reconciliation handled
   any orphans.
7. **Monitoring:** Heartbeat pings consistent. Alerts fire when they should. Margin-circuit
   events surface in Command Center if triggered.
8. **Before live transition:** Walk through
   [pre-live-transition-checklist.md](pre-live-transition-checklist.md) and restore every
   value.

You do NOT need to be profitable. Profitability in 3–5 days is statistically meaningless.

If issues are found, fix them, reset your validation counter, and run for another 3 days.
Don't carry forward partial validation periods where known bugs existed.

---

## 8. Useful Commands

```bash
# Start paper trading (backend only)
./scripts/start_live.sh

# Start paper trading + Command Center UI
./scripts/start_live.sh --with-ui

# Graceful shutdown
./scripts/stop_live.sh

# Dry run — connect, validate, don't trade
python -m argus.main --dry-run

# Query database
sqlite3 data/argus.db

# Today's trades (excluding reconstruction rows)
sqlite3 data/argus.db "SELECT * FROM trades \
  WHERE date(entry_time) = date('now') AND entry_price_known = 1;"

# Open positions (should be empty after market close)
sqlite3 data/argus.db "SELECT * FROM trades WHERE exit_time IS NULL;"

# Counterfactual positions (shadow + rejected signals)
sqlite3 data/counterfactual.db "SELECT COUNT(*) FROM counterfactual_positions \
  WHERE date(entry_time) = date('now');"

# Errors in today's log
grep '"level":"ERROR"' logs/argus.log

# Margin-circuit events (Sprint 32.9)
grep 'margin_circuit' logs/argus.log

# Watch logs in real time
tail -f logs/argus.log | python -m json.tool

# Diagnose Databento
python scripts/diagnose_databento.py

# Integration sanity checks
python scripts/test_session8_integration.py
```

---

## 9. Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| System won't start | Missing `.env` / bad Databento or FMP key | Check `.env`; `python -m argus.main --dry-run` |
| IBKR connection refused | Gateway not running in paper mode on port 4002 | Start IB Gateway; verify port + paper indicator (`DU…`) |
| "Connection refused" to Databento | API key invalid or Databento outage | Check `DATABENTO_API_KEY`; [databento.com status](https://databento.com/) |
| Scanner finds 0 stocks | Pre-market filters too restrictive OR FMP 403 | Widen filters; confirm FMP Starter plan is active |
| No trades across hours | Quality engine grading all B, or risk rejecting | Check SetupQualityEngine log lines + OrderRejectedEvent |
| Trades in IBKR but not in DB | Logging bug or crash between fill and log | Check `logs/argus.log` around the fill timestamp |
| Trades in DB but not IBKR | Reconstruction (`entry_price_known=0`) or bug | Filter by `entry_price_known=1`; investigate remainder |
| EOD flatten missed | Crash before 3:55 PM ET | Check uptime; manually flatten via TWS |
| Constant IBKR reconnects | Gateway instability / network | Restart Gateway; check IBC log |
| Margin circuit open | 10 consecutive IBKR 201 rejections | Inspect buying power; circuit resets after 20 fills |
| Circuit breaker triggered | Daily / weekly loss limit hit | Working as designed — review losing trades |
| DuckDB hang on start | DEF-164 scheduling collision | Start only in safe window (≥ 04:00 ET) |

---

## 10. Cross-References

- [live-operations.md](live-operations.md) — Full daily runbook for Databento + IBKR paper
- [pre-live-transition-checklist.md](pre-live-transition-checklist.md) — Config values to
  restore before live
- [ibc-setup.md](ibc-setup.md) — IB Gateway + IBC launchd setup
- [operations/parquet-cache-layout.md](operations/parquet-cache-layout.md) — Cache separation
  (Sprint 31.85 canonical reference)
- `.claude/rules/risk-rules.md`, `.claude/rules/architecture.md`, `.claude/rules/testing.md`
  — Invariants this guide assumes

---

*End of Paper Trading Validation Guide v2.0 (2026-04-21 audit FIX-15 rewrite).*
*Supersedes v1.0 (Alpaca-based, Feb 16, 2026).*
