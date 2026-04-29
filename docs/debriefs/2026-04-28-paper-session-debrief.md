# Paper Session Debrief — 2026-04-28

> **Boot commit:** `0236e27` (Sprint 31.91 S5a.1 — HealthMonitor SystemAlertEvent consumer + REST surface)
> **Operator note:** Sprint 31.91 (D14) and Sprint 31.915 closed AFTER this boot. Post-boot work is **not** in scope for this debrief.
> **Input:** `logs/argus_20260428.jsonl` (52 MB uncompressed, 215,001 events)
> **Protocol:** `docs/protocols/market-session-debrief.md`
> **Verdict:** **CRITICAL — Sprint 31.91 cessation criterion #5 (5 clean paper sessions post-seal) FAILS on session #1.** DEF-204 mechanism is still firing post-DEC-385 / DEC-386 / DEC-388. Two distinct uncovered paths identified.

---

## Executive Summary

| Dimension | Status | Notes |
|---|---|---|
| Market coverage | ⚠ Partial | 09:29 → 15:16 ET (5h 47m). Ended 44 min before close due to disk pressure. |
| Startup | ✅ Clean | 12 phases in ~6s, warm cache, 6,439 symbols, 15 strategies routed, 15 variants spawned. |
| Data flow | ✅ Healthy | 66 heartbeats, ~12K candles/5min steady-state, 0 stale episodes, 0 SPY-unavailable. |
| Strategy pipeline | ✅ Functional | 1,269 positions opened across 15 strategies. Pipeline producing signals. |
| **DEF-204 mechanism** | 🔴 **NOT CLOSED** | **60 NEW phantom shorts during session** + 27 pre-existing not auto-cleaned. **DEC-386 ~98% claim falsified.** |
| Phantom-short gate | ✅ Working as designed | 86 symbols engaged, 48 signals blocked, 161 auto-clears, 86 unique gate engagements. Gate is a trailing safety net — does not prevent the over-flatten that creates the short. |
| Alert observability | ✅ S5a.1 working | 13,516 `HealthMonitor consumed alert` lines (UUID-tagged, type=phantom_short, severity=critical). REST surface active. WS fan-out / persistence not yet in boot (S5a.2 lands later). |
| Trade economics | 🔴 Loss | 1,243 closed, 25.6% win rate, **−$8,446.27 realized**, 14.8 min avg hold. |
| Disk / DB | 🔴 Caused early shutdown | `evaluation.db` already at **22.2 GB** at boot; Sprint 31.915 retention fix is post-boot. |
| Operator mitigation | ✅ Ran post-session | `scripts/ibkr_close_all_positions.py` executed after manual shutdown. |

---

## Phase 1 — Session Boundaries

```
First event: 2026-04-28T13:29:13.595Z  (09:29:13 ET — boot)
Shutdown signal: 2026-04-28T19:16:35.565Z  (15:16:35 ET — operator-initiated)
Final event: 2026-04-28T19:17:04.532Z  (15:17:04 ET)
Duration: 5h 47m 51s
```

**Cycles:** 1 start, 1 stop. **Shutdown was graceful** — full lifespan teardown ran:
- 88 open orders cancelled at IBKR
- OrderManager → Orchestrator → HealthMonitor → CatalystStorage → RegimeHistoryStore → DB → broker disconnect, all in sequence
- `ARGUS TRADING SYSTEM — STOPPED` banner emitted at 19:16:59.839Z
- One trailing reconnect attempt scheduled (benign — caught by lifespan exit, log line `Task was destroyed but it is pending` at 19:17:04 is the standard async-cleanup orphan)

**No fatal errors. 0 mid-session crashes.** Operator manually stopped the process; the system did not panic-exit.

The 44-minute gap before market close is the operational signal: ARGUS missed the 15:30 ET signal cutoff → 16:00 ET EOD flatten window entirely. There is no EOD-flatten log. There is no signal-cutoff log. Both are absent because the process was already gone.

---

## Phase 2 — Startup Health

```
[1/12]  13:29:13.595  Loading configuration
[2/12]  13:29:13.612  Initializing database
[3/12]  13:29:13.616  Connecting to broker         ← 43-position invariant violation surfaces here
[4/12]  13:29:14.134  Starting health monitor
[5/12]  13:29:14.134  Initializing risk manager
[6/12]  13:29:14.282  Initializing data service
[7/12]  13:29:14.282  Running pre-market scan
[7.5]   13:29:14.420  Building Universe Manager
[8/12]  13:29:15.472  Creating strategy instances
[8.5]   13:29:15.503  Initializing regime intelligence V2
[9/12]  13:29:15.507  Initializing orchestrator (orb_family_mutual_exclusion=False)
[9/12]  13:29:15.614  Experiment variants spawned: 15
[10.3]  13:29:15.614  Initializing telemetry store
[9.5]   13:29:16.019  Building routing table
[10/12] 13:29:16.136  Starting order manager
[10.25] 13:29:16.166  Initializing quality pipeline
[10.4]  13:29:16.168  Wiring event routing
[10.7]  13:29:16.168  Initializing counterfactual engine
[11/12] 13:29:16.176  Starting data streams
[12/12] 13:29:17.362  Starting API server
                      API ready at 13:29:18.776
                      ARGUS Started at 13:29:19.319  ← total boot ~5.7s
```

**Routing table (full universe = 6,439 symbols):**

| Strategy | Routed | | Strategy | Routed |
|---|---:|---|---|---:|
| ORB Breakout | 2,188 | | Bull Flag | 2,188 |
| ORB Scalp | 2,188 | | Flat-Top Breakout | 2,188 |
| VWAP Reclaim | 1,893 | | Dip-and-Rip | 3,562 |
| Afternoon Momentum | 2,188 | | HOD Break | 4,551 |
| Red-to-Green | 3,562 | | ABCD | 3,181 |

**Experiment variants:** 15 spawned (project knowledge says 22 configured — gap of 7 likely accounted for by patterns where reference data wasn't ready or filters rejected the variant; not blocking).

**Margin circuit at boot:** Closed (no events).

### 🔴 STARTUP INVARIANT VIOLATED — 43 pre-existing non-long positions

```
13:29:14.134  STARTUP INVARIANT VIOLATED: broker returned 43 non-long position(s) at connect:
    BB(177), SOXS(390), FSM(51), TRMD(31), APPN(93), NOK(973), USAR(15), NAT(325),
    MIR(94), KNX(29), SH(1106), ...  [all side=SELL]
```

This is the load-bearing finding. Yesterday's `ibkr_close_all_positions.py` did not zero the account. **The flatten script is leaking shorts session-over-session.**

DEC-385 (side-aware reconciliation) prevents ARGUS from auto-cleaning these (correct safety posture: never cover a real short the operator opened). But the script that *is* supposed to clean them isn't doing it. This is an independent gap from DEF-204's intra-session creation mechanism.

Within the first ~50 seconds of session, 27 of those 43 surfaced as `BROKER ORPHAN SHORT DETECTED` alerts (re-firing every reconciliation cycle for the rest of the session, ~280×). The other 16 were on symbols ARGUS didn't trade today, so the per-symbol reconciliation never re-touched them.

---

## Phase 3 — Data Flow

| Metric | Value | Healthy? |
|---|---|---|
| Heartbeats | 66 over 5h 47m | ✅ |
| Steady-state throughput | 12K–13K candles / 5min, 3,500–3,700 active symbols | ✅ |
| Stale data episodes | 0 | ✅ |
| Late-session sample | 19:09 UTC: 12,920 candles, 3,709 symbols active, 0 unmapped, 1,925 universe-dropped | ✅ |
| Warm-up calls | 0 success / 0 fail (cache was warm; nothing to backfill) | ✅ |

Data pipeline is not contributing to today's problems.

---

## Phase 4 — Strategy Pipeline

### 4.1 — Trade Funnel (live)

```
Positions opened:          1,269
Positions closed (formal): 1,243
Win rate:                  25.6%   (318 wins / 1,243 closes)
Total realized P&L:        -$8,446.27
Average hold time:         14.8 min
```

**Closure-reason breakdown:**

| Reason | Count | % |
|---|---:|---:|
| stop_loss | 741 | 59.6% |
| time_stop | 232 | 18.7% |
| trailing_stop | 185 | 14.9% |
| target_1 | 58 | 4.7% |
| target_2 | 27 | 2.2% |

**Read:** Every reason category fires, telemetry is intact, but the win-rate / closure-reason mix is unhealthy — 59.6% stop-outs vs 6.9% target-hits is the dominant signal that the entries are being eaten by either spread/slippage or by the over-flatten mechanism (see Phase 4.3).

### 4.2 — Counterfactual / Shadow / Overflow

```
Counterfactual position opens: 18,893
  ├── Shadow-mode (variants):       ~14,000  (22 shadow variants × ~640 fires)
  ├── Overflow → counterfactual:     4,700   (50-pos cap reached repeatedly)
  └── Phantom-short gate rejections:    48
```

The 4,700 broker-overflow routings deserve a separate note: ARGUS hit the `max_concurrent_positions=50` cap repeatedly throughout the day, and DEC-375 routed approved signals to the CounterfactualTracker as shadow positions. The PromotionEvaluator data for today is therefore heavily skewed — the variants under-shadow-tested are actually the live-mode strategies whose signals were routed to counterfactual due to capacity, not genuine variant comparisons.

### 4.3 — Phantom-Short Gate (DEC-385 / Session 2c.2 + 2d)

```
Symbols engaged:          86
Signal blocks:            48   (OrderApprovedEvent REJECTED, phantom_short_gated_symbols)
Auto-clears (5-cycle):   161
Total clear-attempt logs: 296
```

**The gate is doing its job downstream of the bug.** 86 distinct symbols had the gate engage; 48 follow-on signals were correctly suppressed; 161 auto-clears fired when the broker eventually showed zero shares for a symbol (most likely after the operator's post-session flatten or natural cover via subsequent buying). The gate is not the defect — it is the only thing keeping the loss from compounding into 4-figure new-position territory on the same symbols.

The gate cannot prevent the *first* phantom short on a symbol — by the time it engages, the over-flatten has already happened.

---

## Phase 5 — Catalyst Pipeline

```
Pipeline cycles run:       11    (expected ~12 over 5h 47m at 30-min cadence — match)
SPY data unavailable:      0
```

Catalyst pipeline ran at expected cadence. Not a contributor to today's issues.

---

## Phase 6 — Error Catalog

```
Total events:    215,001
INFO:            151,344  (70.4%)
WARNING:          35,677  (16.6%)
ERROR:            14,336  (6.7%)
CRITICAL:         13,644  (6.3%)
```

### CRITICAL events — 13,644 total

```
argus.execution.order_manager   13,642   (BROKER ORPHAN SHORT DETECTED — DEF-204 signature)
argus.core.health                    2   (component health degradations)
```

13,508 unique orphan-short detection events. 87 distinct symbols. The 1-per-minute cadence × 87 symbols × ~280 minutes of average dwell = ~13.5K events. Volume = function of recon cadence × dwell-time × symbol count. Not redundant noise — each event is the per-cycle re-detection of the same unresolved short, exactly as DEC-385's continuous-detection contract specifies.

### Top ERROR templates

| Count | Template | Class |
|---:|---|---|
| 5,739 | `Order Canceled - reason:` | Cancel race / shutdown side-effects |
| **5,348** | `Order rejected - reason:Your account has a minimum of N orders working on either the buy or sell side` | **IBKR per-symbol per-side order limit exceeded** |
| **1,629** | `Order rejected - reason:The contract is not available for short sale` | **Locate-rejection retry storm** |
| 915 | `OrderId N that needs to be cancelled cannot be cancelled, state: Cancelled` | Cancel-already-cancelled race (low-priority noise) |
| 239 | `Order rejected - reason:N order cancel` | Mostly IBKR rejecting bracket amendments after partial fill |
| 152 | `Revision rejected due to unapproved modification followed by cancelled order` | Bracket amendment race |
| 118 | `OrderId N that needs to be cancelled cannot be cancelled, state: PendingCancel` | Cancel race |
| 79 | `OrderId N that needs to be cancelled is not found` | Cancel race |
| 48 | `OrderId N that needs to be cancelled cannot be cancelled, state: Filled` | **Stop fired before cancel — over-flatten signature** |
| **38** | `Stop retry failed for <SYM>. Emergency flattening` | **Stop resubmission broke down** |
| **14** | `Stop resubmission exhausted for <SYM> after N attempts — triggering emergency flatten` | **DEC-372 retry cap hit — emergency path triggered** |

### Margin / EOD / Signal cutoff

```
Margin circuit breaker events:  0
EOD flatten events:             0    (process exited before 16:00 ET)
Signal cutoff events:           0    (process exited before 15:30 ET)
IBKR disconnects:               1    (at shutdown — graceful)
Fatal errors:                   0
SPY data unavailable:           0
```

---

## 🔴 PRIMARY FINDING — DEF-204 Mechanism Has Two Uncovered Paths

DEC-386 (Tier 3 verdict 2026-04-27) claims `~98%` of DEF-204's mechanism is closed via OCA-Group Threading + Broker-Only Safety. Today's session falsifies that claim. The gap is more than 2%, and the residual paths are *both* in the standalone-SELL category that S1b was supposed to cover.

### Phantom shorts created today

| | Count | Notes |
|---|---:|---|
| Pre-existing at boot (≤10 min after connect) | 27 symbols | Prior-session leakage; flatten script gap |
| **NEW during session** | **60 symbols** | **Created by ARGUS today, post-DEC-386** |
| Total absolute phantom-short shares | 12,605 | Sum of \|shares\| across 87 unique symbols |
| Top 5 NEW phantom shorts by share count | PCT 3,837 · ACHR 402 · PDYN 400 · HPK 313 · MX 297 | |

### Path #1 — Trail-Stop / Bracket-Stop Concurrent Trigger (BITU is the canonical trace)

**Smoking-gun timeline (BITU, 13:36:02 → 13:41:18 UTC):**

```
13:36:02.412  ORB breakout signal: entry=14.41, stop=14.38, T1=14.45, T2=14.48
13:36:02.929  Signal approved: 364 BITU
13:36:02.960  Bracket placed: BUY 364 + SELL 364 STOP + SELL 182 LIMIT + SELL 182 LIMIT
13:36:08.264  Position opened @ 14.43 (slippage +0.02)
13:36:08.265  Bracket children at IBKR (#443 STOP, #444/445 LIMIT)
13:36:08.266  Bracket amended: stop=14.39, T1=14.46

13:37:10.107  Order placed → IBKR #462 SELL 182 BITU STOP    ← post-T1 reduced bracket stop
13:37:10.107  T1 hit for BITU: 182 shares @ 14.46 (+5.46). Stop moved to breakeven 14.44.

13:41:02.235  Trail stop triggered: trail=0.00, price=14.44   ← matches breakeven of #462
13:41:02.236  Order placed → IBKR #633 SELL 182 BITU MARKET   ← trail stop emits market order
13:41:02.378  Position closed: BITU | PnL: 5.46 | Reason: trailing_stop | Hold: 294s

13:41:18.819  Position reconciliation: 2 mismatch(es) — BITU, OHI
13:41:18.819  CRITICAL  BROKER ORPHAN SHORT DETECTED: BITU shares=182    ← over-flatten
13:41:18.819  CRITICAL  Phantom-short gate ENGAGED for BITU
```

**What happened:** The trail-stop logic placed a SELL 182 MARKET (#633) at the *same instant* price triggered the bracket stop (#462, also SELL 182, breakeven 14.44). Both executed before either could cancel the other. Total sold = 364 against 182 long → **182 short**.

**Why DEC-386 didn't catch this:** DEC-386 S1b threads standalone SELLs into the OCA group at *placement time*. That works when the trail stop fires before the bracket stop has any reason to trigger — IBKR's OCA mechanism then cancels the bracket sibling. It does **not** work when both legs trigger from the same price action concurrently — at that point, both are already in flight, and OCA cancellation propagation (the 50–200ms validated by Phase A spike `PATH_1_SAFE`) is *too slow* relative to fill latency on the bracket stop, which is itself a stop-trigger market with no cancel window.

This is the **concurrent-trigger race** path. It is structurally outside DEC-386 S1b's coverage.

**Fix direction (proposal — does NOT belong in this debrief, but flagging for sprint planning):**
Either (a) the trail stop must *amend* the bracket stop's price rather than place a new market, or (b) the trail stop must cancel-and-await the bracket stop before placing its market, accepting 50–200ms of unprotected exposure as the cost of correctness, or (c) the system must classify the second fill as `redundant_exit_observed` and reconcile it away as a SAFE outcome (the marker DEC-386 introduced) — but doing that requires the recon layer to *trust* the marker, which currently it does not.

### Path #2 — Locate-Rejection Retry Storm with Held-Order Release (PCT is the canonical trace)

**Smoking-gun timeline (PCT, 14:34 → 18:08 UTC):**

```
14:34:05.434  Signal approved: 247 PCT
14:34:07.141  Position opened @ 7.17 (slippage -0.09 — fill BELOW intended entry)
14:34:07.142  Bracket children: SELL 247 STOP, SELL 123 LIMIT, SELL 124 LIMIT
14:34:07.142  Bracket amended: stop=7.10, T1=7.24

14:54:17.680  Order placed → IBKR #4269 SELL 247 PCT STOP    ← escalation stop ADDED on top
14:54:17.680  Escalation stop updated for PCT: new_stop=7.17

15:04:08.399  Time stop for PCT: open 1801 sec (limit=1800)
15:04:08.400  Order placed → IBKR #5065 SELL 247 PCT MARKET  ← time stop emits market

15:04:08+     [Order rejected] reason:The contract is not available for short sale
15:04:13      Time stop fires again, places SELL 247 MARKET (rejected with same)
15:04:18      Time stop fires again, places SELL 247 MARKET (rejected with same)
...           (loop continues every 5s)

18:08:33.xxx  CRITICAL  BROKER ORPHAN SHORT DETECTED: PCT shares=3,837
```

PCT alone accounts for **2,107 SELL order placement events** (full session). XNDU shows the same pattern with 1,616 SELL placements. CRWG with 3,294. Combined, three symbols account for **7,017 of the 11,000 SELL order events.**

**What happened:** Three independent SELL paths competed for the same position:
1. Bracket stop (amended → escalated)
2. Escalation stop placed standalone (#4269) at 14:54
3. Time-stop market emitter (kicks in at +1800s)

When the time stop fires, IBKR returns "contract is not available for short sale" — this is **a HOLD pending borrow, not a hard reject**. ARGUS's retry logic interprets it as a transient failure and retries every 5 seconds. Meanwhile, IBKR's locate engine eventually finds borrow availability and **releases held orders in batch**. With 16+ retries queued, all of them fire sequentially, each treated as a fresh short because the previous fills already covered the long.

Result: 247 × ~16 = ~3,952 shares sold against 247 long → **~3,705 net short** (observed: 3,837, close enough to the model).

The 38 `Stop retry failed for <SYM>. Emergency flattening` events and 14 `Stop resubmission exhausted` events are this same path triggering across other symbols.

**Why DEC-386 didn't catch this:** DEC-386 covers placement-time OCA threading. It does not address the failure mode where IBKR holds an order pending borrow and ARGUS's retry layer (DEC-372 stop retry caps + DEF-158 retry side-check from Sprint 31.91 S3) does not recognize the held state as "still in flight." DEF-158's retry side-check is a 3-branch gate (per the Session 3 commit message); none of those branches treats "contract is not available for short sale" as a held-pending-borrow that *will probably fill later*.

This is the **locate-rejection-as-held-order** path. It is structurally outside both DEC-386's OCA coverage and DEF-158's retry side-check.

### Why these two paths exhaust the 60-new phantom-short symbol list

Spot-check: BITU (Path #1) appears at 13:41:18 with 182 shares — exactly one bracket × trail-stop concurrent trigger. The new-shorts timeline shows the *first phantom short* on each symbol; subsequent re-detections on the same symbol just refresh the alert. The 60 symbols decompose roughly into: a handful of large-quantity locate-rejection retry storms (PCT 3,837, ACHR 402, PDYN 400, HPK 313, MX 297, NVD 252 — the top 6 alone account for ~5,500 of the 12,605 absolute shares) and a long tail of small concurrent-trigger races (BITU 182, OHI 115, CSIQ 115, BHVN 110, …). Two distinct mechanisms, both observable today.

---

## 🔴 SECONDARY FINDING — `evaluation.db` Bloat Forced Premature Shutdown

```
13:29:15.616  evaluation.db ~22746.1 MB  ← 22.2 GB at boot
```

Sprint 31.915 (commit `e58edec`) added config-driven `evaluation.db` retention with VACUUM (DEC-389). That commit landed **after** boot commit `0236e27`. The retention fix is therefore not present in today's session, and the DB grew unbounded throughout the day on top of an already-22 GB starting state.

The operator reports: ran out of disk space → manually shut down → ran `ibkr_close_all_positions.py`.

**Action:** Sprint 31.915's VACUUM-on-startup must run with the next session's first boot. Disk needs verifying free before that boot; the 22 GB DB will need to be either VACUUMed (close → sync VACUUM via `asyncio.to_thread()` → reopen, per Sprint 31.8 S2 Lessons Learned) or truncated under the new retention policy.

---

## ✅ Alert Observability (Sprint 31.91 S5a.1) — Behaved as Specified

The boot commit's S5a.1 deliverable is HealthMonitor as the SystemAlertEvent consumer + REST surface. Observed:

```
"HealthMonitor consumed alert <UUID> (type=phantom_short severity=critical source=reconciliation)" — 13,516 lines
```

Each alert is:
- UUID-tagged (canonical event ID)
- Typed (`phantom_short`)
- Severity-classed (`critical`)
- Source-attributed (`reconciliation`)

This is exactly the contract S5a.1 was specified against. WebSocket fan-out, SQLite persistence, auto-resolution policy, and the migration framework universal adoption (S5a.2 and Impromptu C) all landed AFTER this boot — their absence here is expected and correct.

The alert observability subsystem isn't responsible for *preventing* the orphan shorts; it's responsible for making them visible. It did that. The visibility is what enabled this debrief to identify the two mechanisms cleanly.

---

## Findings — Recommended DEF Items

> *Per protocol §7.5. To be filed in CLAUDE.md DEF table at next doc-sync.*

### 🔴 DEF (CRITICAL) — DEF-204 Mechanism Path #1: Trail-Stop / Bracket-Stop Concurrent-Trigger Race

DEC-386's standalone-SELL OCA threading (S1b) does not cover the case where the trail stop's market emit and the bracket stop's price-trigger fire concurrently. Both legs execute → over-flatten → phantom short. **Empirical evidence today: 60 new phantom shorts; BITU at 13:41:18 is the canonical trace.** Falsifies the DEC-386 `~98%` claim. Should sprint-gate the next paper-session window. Fix direction: trail stop must amend the bracket stop, not place a new market — or accept cancel-and-await unprotected gap.

### 🔴 DEF (CRITICAL) — DEF-204 Mechanism Path #2: Locate-Rejection Retry Storm

When IBKR returns `contract is not available for short sale`, ARGUS's retry logic treats it as transient and retries every 5s. IBKR holds the order pending borrow and releases queued orders when borrow becomes available. **Result: 16+ orders execute sequentially.** PCT (3,837 shares short), CRWG (3,294 SELL events), XNDU (1,616 SELL events). Fix direction: detect "held pending locate" as a distinct state, suspend retries until IBKR confirms cancel or fill, OR cap absolute SELL volume per symbol per session.

### 🟠 DEF (HIGH) — `ibkr_close_all_positions.py` Leaks Shorts Session-Over-Session

43 non-long positions present at boot despite operator running the daily flatten yesterday. Sprint 31.91's operator-daily-flatten mitigation depends on this script being complete. Need: post-script verification step that re-queries IBKR positions and asserts `non_long_count == 0`, with a non-zero exit code and operator notification on mismatch.

### 🟠 DEF (HIGH) — Sprint 31.915 Retention Fix Must Be Present at Next Boot

`evaluation.db` at 22.2 GB at boot. Even with retention enabled going forward, the existing 22 GB needs an explicit VACUUM (close → `asyncio.to_thread(VACUUM)` → reopen pattern from Sprint 31.8 S2). Without it, disk pressure recurs.

### 🟡 DEF (MEDIUM) — `Stop retry failed → Emergency flattening` (38 events) Correlates With New Phantom Shorts

The emergency-flatten path (DEC-372 retry cap exhausted) is currently a SELL emit. Suspicion: when emergency flatten fires while the bracket stop is also in flight, both execute. Worth instrumenting whether emergency flatten cancels-and-awaits before placing its replacement.

### 🟡 DEF (MEDIUM) — 5,348 "minimum of N orders working" Rejections

IBKR per-symbol per-side order limit exceeded 5,348 times. Confirms that the retry storms and the bracket amendment churn are pushing past IBKR's per-side cap. Need circuit breaker at the OrderManager level: if a symbol has > N pending SELLs in last M seconds, suppress new SELLs until reconcile completes.

### 🟢 DEF (LOW) — Cancel-Race Noise in Logs

5,739 `Order Canceled` + 915 `cannot be cancelled, state: Cancelled` + 118 `state: PendingCancel` + 79 `not found` + 48 `state: Filled` = ~6,900 cancel-related ERROR-level lines. None blocking, but the volume suggests the cancel path is being asked to do work that's already done. Worth promoting these to WARNING and suppressing the redundant continuations.

---

## Action Items — Before Next Paper Session

1. **Run `scripts/ibkr_close_all_positions.py`** (operator already did — confirmed in handoff). Add a verification step that re-queries position list and asserts zero non-longs before the next ARGUS boot. **If non-longs persist, escalate before booting.**
2. **VACUUM `evaluation.db`** under Sprint 31.915's retention policy. Verify file shrinks meaningfully (target: <1 GB) before next boot.
3. **Confirm next boot is at HEAD** (or at minimum, includes Sprint 31.915 + Sprint 31.91 D14). Today's boot at S5a.1 is the cleanest possible "DEC-386 in place, full alert observability not yet" baseline; the diagnostic value is now extracted, but going forward the debrief baseline should be the sealed sprint head.
4. **Sprint planning input:** Two new CRITICAL DEF items above need sprint-gating disposition. Recommend they go to the next sprint after Sprint 31B (Research Console / Variant Factory) is closed, OR — if Steven wants — they can supersede Sprint 31B as a Sprint 31.92 (analogous to how Sprint 31.91 inherited the DEF-014 + DEF-204 work). The cessation criterion #5 ("5 paper sessions clean post-seal") cannot tick today's session as clean; it stays at 0 / 5.
5. **Do NOT cease daily-flatten mitigation.** Cessation criterion #5 is unmet. Continue running `scripts/ibkr_close_all_positions.py` after every session until 5 consecutive clean sessions.

---

## What This Debrief Does NOT Conclude

- **Whether DEC-386 should be amended in-place or a new DEC issued.** That's a sprint-planning call. The empirical finding is "two paths uncovered"; the documentation response is downstream.
- **Whether the trail-stop logic should be amended-vs-cancel-and-await.** Both have correctness/latency tradeoffs. Belongs in a sprint Phase A spike.
- **Whether DEF-158's retry side-check needs a 4th branch for "held pending locate."** Likely yes, but needs the IBKR error-code semantics validated against documented behavior, not just observed behavior.
- **Whether the 4,700 broker-overflow routings are over-firing today** (50-pos cap reached repeatedly). Possibly fine; possibly indicates `max_concurrent_positions` is too tight for the actual signal volume of 13 live + 2 shadow strategies × current universe. Requires a separate analysis pass.

---

## Database Queries Pending

If desired, the following can be run against the live SQLite stores (Claude does not have direct DB access):

1. `data/evaluation.db` — actual file size on disk + table-row counts (verify Sprint 31.915 retention will operate as expected)
2. `data/argus.db` quality_history filtered by today's `created_at` — grade distribution and grade-outcome correlation (not surfaced in JSONL)
3. `data/counterfactual.db` counterfactual_positions filtered by today — variant vs base shadow comparison (the 18,893 counterfactual opens contain the data)
4. `data/experiments.db` promotion_events for last 7 days — has any variant approached promotion thresholds, given today's heavy shadow data

These are Phase 4b / 4c / 7.3 enrichments per protocol; not blocking for the synthesis above.
