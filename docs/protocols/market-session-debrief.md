# Protocol: Market Session Debrief

> **Location:** `docs/protocols/market-session-debrief.md`
> **Context:** Claude.ai conversation, post-market close
> **When to use:** After every market session where ARGUS was running (paper or live)
> **Input:** JSONL log file + access to run SQLite queries
> **Output:** Session debrief report with findings, DEF items, and action items for tomorrow
> **Time:** ~10–15 minutes with this protocol, vs ~45+ minutes ad-hoc
>
> Last updated: 2026-04-02. Calibrated against March 17 + March 20 sessions. Sprint 32.9+ additions: shadow/counterfactual phase, quality distribution phase, margin circuit breaker checks, EOD flatten reporting, signal cutoff checks.

---

## Prerequisites

The operator provides:
1. **The JSONL log file only:** `logs/argus_YYYYMMDD.jsonl` — this is the structured JSON log containing every distinct event in a parseable format. Do NOT provide `logs/argus_YYYY-MM-DD.log` — that file contains the same events in human-readable format plus multi-line continuation lines (Databento error details, Python tracebacks, uvicorn output) that bloat it to ~2.4x the JSONL size with zero additional trading-relevant information. Exception: provide the .log file only if debugging a specific uvicorn/startup issue not appearing in the JSONL.
2. Access to run Python/SQLite queries against `data/argus.db`, `data/evaluation.db`, and `data/catalyst.db`
3. Any observations from watching the Command Center (screenshots, notes, or "didn't watch")
4. **Do NOT provide** `logs/ui_YYYY-MM-DD.log` — this contains only Vite dev server output (port conflicts, hot-reload). Not useful for trading diagnostics.

---

## Phase 1 — Session Boundaries

**Goal:** How many times did ARGUS start/stop today? Were shutdowns graceful or crashes?

```python
# Run against the JSONL log file
import json, sys
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if any(k in m for k in ['STARTING', 'STOPPED', 'SHUTTING DOWN', 'Fatal error']):
        print(f"  {d['timestamp']}: {m[:100]}")
```

**What to check:**
- How many start/stop cycles? Multiple means crashes or restarts.
- Was each shutdown graceful ("Auto-shutdown initiated", "EOD flatten triggered") or a crash ("Fatal error")?
- If crashed: what was the fatal error message? Was it recovered?
- Total market time covered: compare first "fully live" timestamp to shutdown timestamp against market hours (9:30 AM – 4:00 PM ET / 3:30 PM – 10:00 PM SAST).

**Red flags:**
- More than 2 start/stop cycles in a day
- Crash during market hours with no restart
- Startup completing after strategy windows have closed

---

## Phase 2 — Startup Health

**Goal:** Did all 12 startup phases complete? How long did each take?

```python
import json
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if m.startswith('[') and '/12]' in m:
        print(f"  {d['timestamp']}: {m}")
    if 'Viable universe built' in m:
        print(f"  {d['timestamp']}: {m[:120]}")
    if 'Routing table' in m:
        print(f"  {d['timestamp']}: {m[:120]}")
    if 'API server started' in m:
        print(f"  {d['timestamp']}: {m}")
    if 'Argus Started' in m:
        print(f"  {d['timestamp']}: {m}")
```

**Key metrics to extract:**
- Time from start to "API server started" (total startup duration)
- Universe Manager: total symbols fetched → viable count → pass rate
- Reference cache: how many stale/missing? Full rebuild or incremental?
- Routing table: symbols per strategy
- Regime classification: actual classification or "SPY data unavailable" fallback?

**Healthy baseline:**
- Startup < 15 minutes (warm cache) or < 30 minutes (cold cache, partial)
- Viable pass rate: 15–20% of total
- Routing: 1,500–2,500 symbols per strategy
- Regime: actual classification, not fallback

**Red flags:**
- Startup > 30 minutes (cache staleness issue)
- "SPY data unavailable" (regime defaults to range_bound — may exclude strategies)
- Routing table shows 0 symbols for any strategy
- Any phase missing from the log (startup didn't complete)

**Sprint 32.9+ additional startup checks:**

- **Experiment pipeline boot:** Search for `"Experiment variants spawned"` — how many variants were spawned? If 0 and `experiments.enabled: true` with variants configured in the YAML, that's a problem.

```python
import json
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if any(k in m for k in ['Experiment variants spawned', 'ExperimentStore initialized',
                             'VariantSpawner', 'margin circuit', 'shadow mode']):
        print(f"  {d['timestamp'][11:16]}: {m[:120]}")
```

- **Strategy mode inventory:** From the routing/allocation log, count live vs shadow strategies at boot. Expected: 10 live + 2 shadow (ABCD, Flat-Top) + N variant shadows. If a live strategy shows as shadow, a YAML misconfiguration is likely.
- **Margin circuit breaker state:** Confirm `_margin_circuit_open: False` at boot. The circuit always starts closed (reset in `_reset_daily_state()`). Any log line mentioning "Margin circuit breaker OPEN" at boot would indicate a code bug.

---

## Phase 3 — Data Flow

**Goal:** Was market data flowing? How much? Any gaps?

```python
import json
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if 'Data heartbeat' in m:
        t = d['timestamp'][11:16]
        print(f"  {t} UTC: {m}")
    if 'stale' in m.lower() and 'data' in m.lower() and 'reference' not in m.lower():
        print(f"  STALE: {d['timestamp']}: {m[:100]}")
```

**Key metrics:**
- Heartbeat candle counts over time (should ramp up as warm-up completes)
- Steady-state throughput: ~12,000–15,000 candles per 5 min with full universe
- Number and duration of stale data episodes
- Warm-up success rate:

```python
import json
success = fail = 0
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if 'Lazy warm-up for' in m and 'fetched' in m: success += 1
    elif 'Lazy warm-up for' in m and 'failed' in m: fail += 1
if success + fail > 0:
    print(f"  Warm-up: {success} success, {fail} failed, {success/(success+fail)*100:.0f}% rate")
```

**Healthy baseline:**
- Heartbeat never drops to 0 during market hours
- Stale episodes < 60 seconds each, < 5 per session
- Warm-up success rate > 60% (lower is acceptable on mid-session boot)

**Red flags:**
- Heartbeat at 0 for extended periods (data feed disconnected)
- Stale episode > 5 minutes (circuit breaker would halt trading)
- Warm-up success rate < 20% (indicators won't be valid for most symbols)

---

## Phase 4 — Strategy Pipeline Verification

**Goal:** Did strategies evaluate setups? How far did signals get through the pipeline? This is the critical diagnostic chain. Query in this exact order — if any step returns zero, the remaining steps will also be zero.

### Step 4.1 — Orchestrator Decisions

Were strategies allocated capital and activated?

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')
c = conn.execute("""
    SELECT decision_type, strategy_id, details
    FROM orchestrator_decisions
    WHERE date = '2026-03-DD'
    ORDER BY created_at
""")
for row in c.fetchall():
    print(f"  {row[0]:12s}  {row[1]:35s}  {row[2][:100]}")
conn.close()
```

**What to check:**
- Each strategy should have an `allocation` decision with `"eligible": true`
- Any `exclusion` decisions? Check the `details` JSON for `regime` and `eligible` fields
- If a strategy is excluded: is it because of regime? throttling? What regime was active?

**If a strategy is excluded by regime:**
- Check `allowed_regimes` in that strategy's source file:
  ```bash
  grep -A3 "allowed_regimes" argus/strategies/<strategy_name>.py
  ```
- Compare against the classified regime (from Phase 2)
- Determine if the exclusion is correct or overly conservative

**Stop here if:** All strategies are excluded. Root cause is regime classification, not evaluation logic.

### Step 4.2 — Evaluation Events

Did strategies actually evaluate candles and record telemetry?

```python
import sqlite3
conn = sqlite3.connect('data/evaluation.db')  # DEC-345: evaluation_events moved from argus.db

# Total count
c = conn.execute("""
    SELECT COUNT(*) FROM evaluation_events
    WHERE trading_date = '2026-03-DD'
""")
print(f"  Total evaluation events: {c.fetchone()[0]}")

# Per strategy
c = conn.execute("""
    SELECT strategy_id, COUNT(*), COUNT(DISTINCT symbol)
    FROM evaluation_events
    WHERE trading_date = '2026-03-DD'
    GROUP BY strategy_id
""")
for row in c.fetchall():
    print(f"  {row[0]:35s}  events={row[1]:6d}  symbols={row[2]:4d}")

# Event type distribution
c = conn.execute("""
    SELECT event_type, result, COUNT(*)
    FROM evaluation_events
    WHERE trading_date = '2026-03-DD'
    GROUP BY event_type, result
    ORDER BY COUNT(*) DESC
    LIMIT 15
""")
for row in c.fetchall():
    print(f"  {row[0]:30s}  {row[1]:8s}  count={row[2]}")

conn.close()
```

**Healthy baseline:**
- 200K–500K events per active strategy per full session (~1M+ total across 3 strategies)
- Multiple event types: TIME_WINDOW_CHECK, CONDITION_CHECK, OPENING_RANGE_UPDATE, ENTRY_EVALUATION, STATE_TRANSITION, QUALITY_SCORED, SIGNAL_GENERATED, etc.
- Mix of PASS and FAIL results

**If zero events:**
- Strategies were allocated but never called `record_evaluation()`
- Possible causes:
  - Strategy time windows closed before system came online
  - Candles not reaching strategies (data routing issue)
  - Telemetry instrumentation not wired (Sprint 24.5 bug)
  - Strategy `is_active` flag set to False despite allocation

### Step 4.3 — Closest Misses (from evaluation events)

Which symbols got closest to triggering?

```python
import sqlite3, json
conn = sqlite3.connect('data/evaluation.db')  # DEC-345: evaluation_events moved from argus.db
c = conn.execute("""
    SELECT symbol, strategy_id, event_type, result, reason, metadata_json
    FROM evaluation_events
    WHERE trading_date = '2026-03-DD'
      AND event_type = 'ENTRY_EVALUATION'
    ORDER BY rowid DESC
    LIMIT 20
""")
for row in c.fetchall():
    meta = json.loads(row[5]) if row[5] else {}
    conditions_passed = meta.get('conditions_passed', '?')
    conditions_total = meta.get('conditions_total', '?')
    print(f"  {row[0]:8s}  {row[1]:30s}  {row[3]:6s}  {conditions_passed}/{conditions_total}  reason={row[4][:60]}")
conn.close()
```

**What to look for:**
- Symbols passing 5+ out of 7–8 conditions (close misses)
- Repeated blocking condition across multiple symbols (calibration target)
- Any PASS results (signals generated)

**Skip this step if:** Step 4.2 returned zero events.

### Step 4.4 — Quality Engine Activity

Did any signals reach the quality scoring pipeline?

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')
c = conn.execute("""
    SELECT COUNT(*) FROM quality_history
    WHERE created_at >= '2026-03-DD'
""")
today_count = c.fetchone()[0]
c = conn.execute("SELECT COUNT(*) FROM quality_history")
total_count = c.fetchone()[0]
print(f"  Quality history today: {today_count}")
print(f"  Quality history total: {total_count}")

if today_count > 0:
    c = conn.execute("""
        SELECT symbol, strategy_id, composite_score, grade, calculated_shares
        FROM quality_history
        WHERE created_at >= '2026-03-DD'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    for row in c.fetchall():
        print(f"  {row[0]:8s}  {row[1]:30s}  score={row[2]:.0f}  grade={row[3]}  shares={row[4]}")

conn.close()
```

**Skip this step if:** Step 4.2 showed no SIGNAL_GENERATED events.

### Step 4.5 — Trade Execution

Did any trades execute?

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')

# Trades today
c = conn.execute("PRAGMA table_info(trades)")
cols = [r[1] for r in c.fetchall()]
date_col = 'created_at'  # adjust if different

c = conn.execute(f"""
    SELECT COUNT(*) FROM trades
    WHERE date({date_col}) = '2026-03-DD'
""")
print(f"  Trades today: {c.fetchone()[0]}")

# Recent trades
c = conn.execute(f"""
    SELECT * FROM trades
    ORDER BY {date_col} DESC LIMIT 3
""")
for row in c.fetchall():
    print(f"  {row}")

conn.close()
```

---

## Phase 4b — Shadow & Counterfactual Performance

**Goal:** Understand what shadow strategies and rejected signals would have done. This is the diagnostic layer for the experiment pipeline and filter accuracy.

### Counterfactual volume and outcomes

```python
import sqlite3
conn = sqlite3.connect('data/counterfactual.db')

# Volume: opened and closed today
c = conn.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END)
    FROM counterfactual_positions
    WHERE date(opened_at) = '2026-03-DD'
""")
row = c.fetchone()
print(f"  Opened: {row[0]}, Closed: {row[1]}")

# Per-strategy outcomes
c = conn.execute("""
    SELECT strategy_id,
           COUNT(*) as total,
           SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed,
           SUM(CASE WHEN theoretical_r_multiple > 0 AND closed_at IS NOT NULL THEN 1 ELSE 0 END) as wins,
           AVG(CASE WHEN closed_at IS NOT NULL THEN theoretical_r_multiple ELSE NULL END) as avg_r,
           AVG(CASE WHEN closed_at IS NOT NULL THEN theoretical_pnl ELSE NULL END) as avg_pnl
    FROM counterfactual_positions
    WHERE date(opened_at) = '2026-03-DD'
    GROUP BY strategy_id
""")
for row in c.fetchall():
    closed = row[2] or 0
    win_rate = (row[3] / closed * 100) if closed > 0 else 0
    print(f"  {row[0]:35s}  total={row[1]:3d}  closed={closed:3d}  "
          f"wr={win_rate:.0f}%  avg_r={row[4] or 0:.2f}  avg_pnl=${row[5] or 0:.2f}")

conn.close()
```

### Rejection funnel by stage

```python
import sqlite3
conn = sqlite3.connect('data/counterfactual.db')
c = conn.execute("""
    SELECT rejection_stage, COUNT(*)
    FROM counterfactual_positions
    WHERE date(opened_at) = '2026-03-DD'
    GROUP BY rejection_stage
    ORDER BY COUNT(*) DESC
""")
print("Rejection funnel:")
for row in c.fetchall():
    print(f"  {row[0]:30s}  {row[1]:4d}")
conn.close()
```

**Known stages:** `quality_filter`, `position_sizer`, `risk_manager`, `shadow`, `broker_overflow`, `margin_circuit_breaker`.

### Exits by reason

```python
import sqlite3
conn = sqlite3.connect('data/counterfactual.db')
c = conn.execute("""
    SELECT exit_reason, COUNT(*)
    FROM counterfactual_positions
    WHERE date(opened_at) = '2026-03-DD'
      AND closed_at IS NOT NULL
    GROUP BY exit_reason
    ORDER BY COUNT(*) DESC
""")
print("Shadow exits by reason:")
for row in c.fetchall():
    print(f"  {str(row[0]):25s}  {row[1]:4d}")
conn.close()
```

**What to check:**
- `eod_closed` vs `target_hit`/`stopped_out`: high eod_closed means most counterfactuals weren't resolved before market close — useful for assessing whether holds are long enough to get a read.
- Rejection funnel skew: if `quality_filter` is catching 90%+ of rejections, the grade thresholds may be too tight. If `risk_manager` is most common, position sizing or capital constraints are the bottleneck.

### Variant vs base comparison

```python
import sqlite3
conn = sqlite3.connect('data/counterfactual.db')
# Compare variant performance vs base strategy (shadow mode positions)
c = conn.execute("""
    SELECT strategy_id,
           COUNT(*) as trades,
           SUM(CASE WHEN theoretical_r_multiple > 0 AND closed_at IS NOT NULL THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed,
           AVG(CASE WHEN closed_at IS NOT NULL THEN theoretical_r_multiple ELSE NULL END) as avg_r
    FROM counterfactual_positions
    WHERE date(opened_at) = '2026-03-DD'
      AND rejection_stage = 'shadow'
    GROUP BY strategy_id
    ORDER BY avg_r DESC
""")
print("Shadow-mode (variant + base shadow) today:")
for row in c.fetchall():
    closed = row[3] or 0
    wr = (row[2] / closed * 100) if closed > 0 else 0
    print(f"  {row[0]:40s}  trades={row[1]:3d}  closed={closed:3d}  wr={wr:.0f}%  avg_r={row[4] or 0:.2f}")
conn.close()
```

**Healthy baseline (after experiments.enabled=true):**
- ABCD and Flat-Top each producing 1–10 counterfactual shadow positions per session
- Promotion requires 30 shadow trades per 5-day window → ~6 per session minimum
- Variant performance divergence visible after 10+ sessions

**Red flags:**
- Zero shadow positions for ABCD or Flat-Top (shadow mode strategies not evaluating)
- `rejection_stage = 'shadow'` count is 0 (shadow routing not wired)

---

## Phase 4c — Quality Engine Performance

**Goal:** Verify the Sprint 32.9 recalibration is producing grade distribution across the full range. If grades are still clustering in one bucket, the thresholds need further adjustment.

### Grade distribution

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')
c = conn.execute("""
    SELECT grade, COUNT(*)
    FROM quality_history
    WHERE created_at >= '2026-03-DD'
    GROUP BY grade
    ORDER BY grade
""")
print("Grade distribution today:")
for row in c.fetchall():
    print(f"  {row[0]:5s}  {row[1]:4d}")
conn.close()
```

**Target range after Sprint 32.9 recalibration:** A+ (≥72), A (≥66), A- (≥61), B+ (≥56), B (≥51), B- (≥46), C+ (≥40). Scores will range roughly 35–77 in typical sessions. If all signals cluster at one grade, check `pattern_strength` and `volume_profile` dimension scores.

### Grade-outcome correlation

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')
c = conn.execute("""
    SELECT qh.grade,
           COUNT(*) as signals,
           SUM(CASE WHEN qh.outcome_r_multiple > 0 THEN 1 ELSE 0 END) as wins,
           AVG(qh.outcome_r_multiple) as avg_r
    FROM quality_history qh
    WHERE qh.created_at >= '2026-03-DD'
      AND qh.outcome_trade_id IS NOT NULL
    GROUP BY qh.grade
    ORDER BY qh.grade
""")
print("Grade-outcome correlation (completed trades only):")
for row in c.fetchall():
    signals = row[1]
    wr = (row[2] / signals * 100) if signals > 0 else 0
    print(f"  {row[0]:5s}  signals={signals:3d}  win_rate={wr:.0f}%  avg_r={row[3] or 0:.2f}")
conn.close()
```

**What to check:** A-grade trades should outperform B-grade, which should outperform C-grade. If ordering is inverted, the scoring dimensions aren't predictive — flag for learning loop analysis.

### Dimension score averages

```python
import sqlite3
conn = sqlite3.connect('data/argus.db')
c = conn.execute("""
    SELECT
        AVG(pattern_strength) as pattern_strength,
        AVG(catalyst_quality) as catalyst_quality,
        AVG(volume_profile) as volume_profile,
        AVG(historical_match) as historical_match,
        AVG(regime_alignment) as regime_alignment,
        AVG(composite_score) as composite_score
    FROM quality_history
    WHERE created_at >= '2026-03-DD'
""")
row = c.fetchone()
if row and row[0] is not None:
    print(f"  pattern_strength:  {row[0]:.1f}")
    print(f"  catalyst_quality:  {row[1]:.1f}  (expect ~50 — no real-time catalyst data)")
    print(f"  volume_profile:    {row[2]:.1f}")
    print(f"  historical_match:  {row[3]:.1f}  (expect 0 — weight zeroed Sprint 32.9)")
    print(f"  regime_alignment:  {row[4]:.1f}")
    print(f"  composite_score:   {row[5]:.1f}  (expect 35-77 range)")
conn.close()
```

**Expected after Sprint 32.9:** `historical_match` should be ~50 (neutral stub) but contribute 0 to composite (weight zeroed). `catalyst_quality` typically ~50 (neutral) until real-time catalyst data improves. If `pattern_strength` or `volume_profile` is constant across all signals, check the IndicatorEngine data for that session.

---

## Phase 5 — Catalyst Pipeline

**Goal:** Is the intelligence layer producing data?

```python
import json
cycles = []
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if 'Pipeline cycle' in m:
        cycles.append(f"  {d['timestamp'][11:16]} UTC: {m[:100]}")
    if 'Classification cycle cost' in m:
        cycles.append(f"  {d['timestamp'][11:16]} UTC: {m[:80]}")
print(f"Catalyst pipeline cycles: {len(cycles) // 2}")
for c in cycles:
    print(c)
```

Also check the catalyst database:

```python
import sqlite3
conn = sqlite3.connect('data/catalyst.db')
c = conn.execute("SELECT COUNT(*) FROM catalyst_events")
print(f"  Total catalyst events: {c.fetchone()[0]}")
# Today's events (find the timestamp column first)
c = conn.execute("PRAGMA table_info(catalyst_events)")
print(f"  Columns: {[r[1] for r in c.fetchall()]}")
conn.close()
```

**Healthy baseline:**
- 1 cycle every 30 minutes during market hours (~13 cycles per full day)
- ~100 items fetched per cycle, ~60 stored after dedup
- Claude API cost < $0.50 per cycle, < $5/day total

**Red flags:**
- Zero cycles (pipeline not polling — check if catalyst.enabled is true)
- "Cost ceiling reached" messages (daily budget exhausted)
- Source errors (FMP 403, Finnhub 403, SEC EDGAR timeouts)

---

## Phase 6 — Error Catalog

**Goal:** Categorize all non-INFO log events. Separate actionable from benign.

```python
import json
from collections import Counter
categories = Counter()
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    if d.get('level') not in ('WARNING', 'ERROR', 'CRITICAL'): continue
    m = d.get('message', '')
    if 'warm-up' in m and 'failed' in m:
        categories['Warm-up 422 (benign)'] += 1
    elif 'warm-up' in m and 'fetched' in m:
        continue  # INFO that might be miscategorized
    elif 'stale' in m.lower() and 'data feed' in m.lower():
        categories['Stale data episode'] += 1
    elif 'Finnhub' in m and '403' in m:
        categories['Finnhub 403 (benign on free tier)'] += 1
    elif 'FMP' in m and '403' in m:
        categories['FMP 403 (Starter plan limit)'] += 1
    elif 'IB Gateway disconnected' in m:
        categories['IBKR disconnect'] += 1
    elif 'HMDS' in m:
        categories['IBKR HMDS warning (benign)'] += 1
    elif 'Fatal error' in m:
        categories['FATAL — investigate'] += 1
    elif 'Task was destroyed' in m:
        categories['Orphaned async task (cleanup)'] += 1
    elif 'Unclosed client session' in m:
        categories['Unclosed aiohttp session (cleanup)'] += 1
    elif 'SPY data unavailable' in m:
        categories['SPY data unavailable — regime fallback'] += 1
    elif 'Heartbeat POST failed' in m:
        categories['Notification heartbeat failed'] += 1
    elif d.get('level') == 'CRITICAL' and 'ALERT' in m:
        categories['System alert (check message)'] += 1
    else:
        categories[f"[{d.get('level')}] {m[:60]}"] += 1

print("Error/Warning catalog:")
for k, v in sorted(categories.items(), key=lambda x: -x[1]):
    benign = '(benign)' in k or '(cleanup)' in k
    marker = '  ' if benign else '⚠ '
    print(f"  {marker}{v:5d}  {k}")
```

**Known benign warnings:**
- Warm-up 422: Databento historical data lag. Symbols build indicators from live candles instead.
- Finnhub 403: Free tier rate limiting. Expected.
- FMP 403: Starter plan doesn't include news endpoints. Expected when fmp_news.enabled is false.
- IBKR HMDS: Historical Market Data Service connection notice. Informational.
- Orphaned tasks / unclosed sessions: Shutdown cleanup issues. Low priority.

**Always investigate:**
- Fatal errors
- IBKR disconnects during market hours (not at shutdown)
- SPY data unavailable (means regime wasn't actually classified)
- Any ERROR not in the known-benign list

**Sprint 32.9+ specific checks:**

**Margin circuit breaker activations:**

```python
import json
margin_events = []
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if 'margin circuit' in m.lower() or 'Margin circuit' in m:
        margin_events.append(f"  {d['timestamp'][11:19]}: {m[:120]}")
for e in margin_events:
    print(e)
if not margin_events:
    print("  No margin circuit breaker events — clean session")
```

Check: Was the circuit triggered? At what time? How many rejections before it opened? Did it auto-reset? If it opened, that signals position count or buying power is under stress — review `max_concurrent_positions` config.

**EOD flatten results:**

```python
import json
flatten_events = []
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if any(k in m for k in ['EOD flatten', 'Pass 1', 'Pass 2', 'positions remaining',
                             'flatten triggered', 'flatten complete', 'timed_out']):
        flatten_events.append(f"  {d['timestamp'][11:19]}: {m[:120]}")
for e in flatten_events:
    print(e)
```

Report: Pass 1 filled/timed-out counts, Pass 2 broker-only orphan count, and whether verification found zero remaining positions. Any "CRITICAL: positions remain after flatten" is a hard escalation.

**Signal cutoff:**

```python
import json
for line in open('logs/argus_YYYYMMDD.jsonl'):
    d = json.loads(line)
    m = d.get('message', '')
    if 'signal cutoff' in m.lower() or 'Pre-EOD signal cutoff' in m:
        print(f"  {d['timestamp'][11:19]}: {m[:120]}")
```

Check: Did the cutoff activate? At what time? If no signals were generated after 15:30 anyway, this is expected and benign. The cutoff is safety padding.

---

## Phase 7 — Synthesis

**Goal:** Produce the session debrief report.

### 7.1 — Session Summary

Fill in:
- **Market coverage:** What percentage of market hours was ARGUS live?
- **Strategy windows covered:** Which strategy windows were active while ARGUS was running?
- **Data flow:** Steady-state candle throughput, warm-up success rate
- **Pipeline depth reached:** How far did signals get? (Universe → Viable → Routed → Evaluated → Near-trigger → Signal → Quality → Trade)
- **Catalyst activity:** Cycles run, items classified, cost

### 7.2 — Root Cause for Zero Trades (if applicable)

Work through this decision tree:

```
Trades = 0?
├── Quality history today = 0?
│   ├── Evaluation events today = 0?
│   │   ├── Orchestrator excluded strategies?
│   │   │   ├── YES → Regime exclusion or throttling. Check allowed_regimes.
│   │   │   └── NO → Strategies allocated but not evaluating.
│   │   │       ├── Strategy windows closed before startup? → Startup timing issue.
│   │   │       └── Windows open but no evaluations? → Candle routing or telemetry bug.
│   │   └── Evaluation events > 0 but no signals?
│   │       └── Check closest misses. What conditions are blocking? Calibration issue.
│   └── Quality history > 0 but no trades?
│       └── Quality scores too low (all filtered at grade threshold)? Or Risk Manager rejected?
└── Trades > 0 → System is working. Analyze trade quality.
```

### 7.3 — Shadow Strategy Assessment (Sprint 32.9+)

**Shadow data sufficiency:** Are ABCD and Flat-Top generating enough counterfactual data for the PromotionEvaluator? The promotion gate requires `promotion_min_shadow_trades` (config: 30 trades per 5-day window). That means ~6 shadow trades per session per strategy minimum.

If either shadow strategy is generating fewer than 6 trades/day:
- Check whether its signal conditions are triggering at all (Phase 4.3 closest misses, filtered by strategy)
- Check whether its configured `allowed_regimes` match the actual session regime
- Consider loosening entry conditions or widening the operating window

**Variant promotion readiness:** For variants with 5+ days of shadow data, are any approaching promotion thresholds? Query the experiments DB:

```python
import sqlite3
conn = sqlite3.connect('data/experiments.db')
c = conn.execute("""
    SELECT pattern_name, shadow_trades, shadow_expectancy, status
    FROM experiments
    WHERE is_baseline = 0
    ORDER BY shadow_trades DESC
""")
print("Variant shadow data accumulation:")
for row in c.fetchall():
    print(f"  {row[0]:40s}  shadow_trades={row[1]:4d}  "
          f"expectancy={row[2]:.3f if row[2] is not None else 'N/A'}  status={row[3]}")

# Recent promotion events
c = conn.execute("""
    SELECT variant_id, action, reason, timestamp
    FROM promotion_events
    WHERE date(timestamp) >= date('now', '-7 days')
    ORDER BY timestamp DESC
    LIMIT 10
""")
print("\nRecent promotion events (last 7 days):")
for row in c.fetchall():
    print(f"  {row[3][:10]}  {row[0]:40s}  {row[1]:10s}  {row[2][:60]}")

conn.close()
```

### 7.5 — DEF Items

Log any issues discovered as DEF items with priority:
- **HIGH:** Issues that prevent trading (regime exclusion, startup timing, data routing)
- **MEDIUM:** Issues that degrade performance (warm-up failures, stale data episodes)
- **LOW:** Cleanup items (orphaned tasks, misleading log messages)

### 7.6 — Action Items for Tomorrow

Always include:
1. **Start time recommendation:** When to start ARGUS relative to market open
2. **Config changes to apply before next session** (if any)
3. **Specific things to observe** during the next session
4. **Queries to run pre-market** to verify fixes

---

## Quick Reference: Database Schemas

### evaluation.db — evaluation_events (DEC-345)
```
id INTEGER, trading_date TEXT, timestamp TEXT, symbol TEXT, strategy_id TEXT,
event_type TEXT, result TEXT, reason TEXT, metadata_json TEXT
```

### argus.db — orchestrator_decisions
```
id TEXT, date TEXT, decision_type TEXT, strategy_id TEXT, details TEXT,
rationale TEXT, created_at TEXT
```

### argus.db — quality_history
```
id TEXT, symbol TEXT, strategy_id TEXT, scored_at TEXT, pattern_strength REAL,
catalyst_quality REAL, volume_profile REAL, historical_match REAL,
regime_alignment REAL, composite_score REAL, grade TEXT, risk_tier TEXT,
entry_price REAL, stop_price REAL, calculated_shares INTEGER,
signal_context TEXT, outcome_trade_id TEXT, outcome_realized_pnl REAL,
outcome_r_multiple REAL, created_at TEXT
```

### argus.db — trades
```
(query PRAGMA table_info(trades) to confirm — schema not verified yet)
```

### counterfactual.db — counterfactual_positions (Sprint 27.7)
```
position_id TEXT, symbol TEXT, strategy_id TEXT, entry_price REAL, stop_price REAL,
target_price REAL, time_stop_seconds INTEGER, rejection_stage TEXT, rejection_reason TEXT,
quality_score REAL, quality_grade TEXT, regime_vector_snapshot TEXT, signal_metadata TEXT,
opened_at TEXT, closed_at TEXT, exit_price REAL, exit_reason TEXT,
theoretical_pnl REAL, theoretical_r_multiple REAL, duration_seconds REAL,
max_adverse_excursion REAL, max_favorable_excursion REAL, bars_monitored INTEGER,
variant_id TEXT
```

### experiments.db — experiments, variants, promotion_events (Sprint 32)
```
experiments: experiment_id, pattern_name, parameter_fingerprint, parameters_json,
    status, backtest_result_json, shadow_trades, shadow_expectancy, is_baseline,
    created_at, updated_at

variants: variant_id, base_pattern, parameter_fingerprint, parameters_json,
    mode, source, exit_overrides, created_at

promotion_events: event_id, variant_id, action, previous_mode, new_mode,
    reason, comparison_verdict_json, shadow_trades, shadow_expectancy, timestamp
```

### catalyst.db — catalyst_events
```
id TEXT, symbol TEXT, catalyst_type TEXT, quality_score REAL, headline TEXT,
summary TEXT, source TEXT, source_url TEXT, filing_type TEXT, headline_hash TEXT,
published_at TEXT, classified_at TEXT, classified_by TEXT, trading_relevance TEXT,
created_at TEXT, fetched_at TEXT
```

### Log message patterns

| Pattern | Meaning |
|---------|---------|
| `[N/12] ...` | Startup phase N |
| `Data heartbeat: X candles received in last 5m (Y symbols active)` | Data flow health |
| `Lazy warm-up for SYMBOL: fetched N historical candles` | Successful indicator backfill |
| `Lazy warm-up for SYMBOL failed: 422` | Historical data not yet available (benign) |
| `Data feed stale for Xs` | No candles received for X seconds |
| `Data feed resumed after stale period` | Candle flow recovered |
| `Pipeline cycle: N fetched, M dedups, K classified, J stored` | Catalyst pipeline cycle summary |
| `Classification cycle cost: $X.XX` | Claude API cost for catalyst classification |
| `SPY data unavailable — using previous regime: X` | Regime not classified, using fallback |
| `Routing table: strategy X matches N/M symbols` | Universe Manager symbol routing |
| `EOD flatten triggered` | End-of-day position flattening |
| `Auto-shutdown initiated` | Graceful post-EOD shutdown |
| `Fatal error during startup: ...` | Startup crash — check error message |

---

## Changelog

- **2026-03-17:** Initial version. Calibrated against March 17 session (zero evaluation events due to regime exclusion + late startup). Added database schemas, error catalog, decision tree for zero-trade diagnosis.
- **2026-03-17 (post-debrief):** Specified JSONL-only input. The `.log` file contains the same events as JSONL plus ~7,000 multi-line continuation lines (Databento 422 details, tracebacks, uvicorn output) with zero additional trading information. UI log also excluded — contains only Vite dev server output.
- **2026-03-20:** Corrected evaluation_events database path from `data/argus.db` to `data/evaluation.db` (DEC-345, Sprint 25.6). Updated healthy baseline for evaluation events from "thousands" to 200K–500K per strategy per full session (calibrated against March 20 data: 1,159,232 total across 3 strategies, 1,653 symbols). Updated event type list to match actual telemetry output. Filled in catalyst_events schema from live database.
- **2026-04-02 (Sprint 32.9+):** Added Phase 2 startup checks (experiment pipeline boot, strategy mode inventory, margin circuit breaker state). Added Phase 4b (Shadow & Counterfactual Performance — rejection funnel, variant vs base comparison, exit breakdown). Added Phase 4c (Quality Engine Performance — grade distribution, grade-outcome correlation, dimension averages). Expanded Phase 6 with margin circuit breaker, EOD flatten, and signal cutoff log queries. Added Phase 7.3 (Shadow Strategy Assessment + variant promotion readiness). Added counterfactual.db and experiments.db schemas to Quick Reference.
