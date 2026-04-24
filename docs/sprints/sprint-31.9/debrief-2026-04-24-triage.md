# Sprint 31.9 Triage Summary — Market Session 2026-04-24

> **Source:** Market session debrief against `logs/argus_20260424.jsonl` (28 MB uncompressed, 130,593 lines).
> **Running process startup commit:** `16c049a` (Sprint 31.9 Stage 1 + Stage 2 + Stage 3 + Stage 4 + Stage 5 + Stage 6 + Stage 7 + Stage 8 Wave 1–3 + CI hotfix + **IMPROMPTU-04 (A1 fix, DEF-199) + IMPROMPTU-10 (evaluation.db retention) + RETRO-FOLD** complete).
> **Debrief protocol:** `docs/protocols/market-session-debrief.md` (7-phase).
> **Baselines for comparison:** `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` + `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md`.
> **Analyst:** Claude (Claude.ai, post-market-close Apr 24).
> **Status:** **DEF-199 A1 fix confirmed working; today's cascade is a DIFFERENT bug family.** Bucket A has one NEW work-blocker finding. C1 fix validated. IMPROMPTU-10 retention has ambiguous evidence — requires DB-side check.

---

## TL;DR — Delta Analysis vs April 22/23

1. **IMPROMPTU-04's A1 fix WORKED.** 44 positions at EOD flatten were detected as unexpected shorts and **NOT auto-covered**. The log contains 44 ERROR lines of the form `EOD flatten: DETECTED UNEXPECTED SHORT POSITION X (Y shares). NOT auto-covering. Investigate and cover manually...`. ARGUS-reported quantities match operator's `ibkr_close_all_positions.py` BUY quantities **exactly** (44 symbols / 14,249 shares — zero discrepancy per symbol). This is **a mathematical signature of 1.00×** (ARGUS detected + refused + operator covered the exact amount), not the 2.00× doubling of yesterday and Monday. **DEF-199 has NOT regressed.** The A1 fix is behaving exactly as designed: detect, refuse, escalate to operator.

2. **Today's cascade is a DIFFERENT bug family — it is NOT DEF-199.** Without A1 doubling to mask it, today's data reveals the TRUE pre-doubling upstream cascade: **44 symbols / 14,249 shares**. Compare:
   - **Monday (Apr 22):** 51 symbols / 13,898 shares were pre-doubling; A1 then doubled them to 51 symbols / 34,239 shares at EOD.
   - **Yesterday (Apr 23):** 42 symbols / 6,949 shares were pre-doubling; A1 then doubled them to 42 symbols / 13,898 shares at EOD.
   - **Today (Apr 24):** 44 symbols / 14,249 shares went short through the session; A1 correctly refused to double them; operator covered the actual 14,249.

   **Today's raw upstream cascade is ~2.0× worse than yesterday's** (14,249 vs 6,949 pre-doubling shares) despite a much lighter network event profile. A1 was the downstream amplifier; when it's removed, we see the upstream C4/C11-family cascade at its true scale — and the true scale is larger than yesterday's. This is **prompt hypothesis (3)**: IMPROMPTU-04 addressed one trigger of the broader problem, but there are multiple upstream triggers flipping positions short, and the dominant one today is not the one A1 addressed.

3. **Mechanism of today's 44-short cascade is under-explained and requires a new investigation.** The three candidate mechanisms from Apr 22/23 only partially explain today:
   - **DEC-372 stop-retry exhaustion (C4):** 45 events today (vs 34 yesterday) — but only **4 of 44** EOD-short symbols (ECH, PD, SMCX, SOXS) had a stop-retry-exhaustion event. The other 40 went short via some other path.
   - **Network-triggered reconnect snapshot (A1 yesterday's evidence):** Today's only network event was a 12-second IBKR Error 1100/1102 blip at 15:40 UTC (11:40 ET). No "Position mismatch after reconnect!" snapshot event fired today. Nothing like yesterday's 79-position-enumeration with 20 already short. Position reconciliation mismatch count grew gradually from 3 → 5 → 7 → 44 through the day rather than jumping in a single reconnect.
   - **Bracket SELL legs filling against already-closed positions:** Only 6 orphan-fill WARNING lines today (`"fill for X but no matching position"`). Far too few to explain 40 symbol-level shorts.

   **→ This is a NEW bug (or bug family) requiring a fresh investigation.** See C12 below.

4. **C1 fix (IMPROMPTU-04) confirmed WORKING.** Log volume dropped from yesterday's 938,754 lines (184 MB) to today's **130,593 lines (28 MB) — an 86% line-count reduction / 85% size reduction**. Top logger `argus.strategies.pattern_strategy` dropped from 829,190 → **21,891 lines (97% reduction)**. The `pattern_strategy.py:318` INFO→DEBUG downgrade is unambiguously in effect.

5. **IMPROMPTU-04 startup invariant: INCONCLUSIVE from log evidence alone.** The helper is in `argus/main.py:123` (`check_startup_position_invariant`) and its call site at line 376 only emits a log line when `startup_positions` is non-empty. Today's boot log shows `Retrieved 0 positions from IBKR` at 13:17:39 UTC — so the invariant ran against an empty list, returned `(True, [])`, and silently set `_startup_flatten_disabled = False`. **No invariant log fired.** This is correct behavior (nothing to validate), NOT a regression, but it also means today's data does not exercise the invariant against real positions. The invariant remains latent-present and unexercised until a session boots with non-empty broker state.

6. **IMPROMPTU-10 (evaluation.db retention) — AMBIGUOUS evidence.** The store logs a NEW boot WARNING (`EvaluationEventStore: DB size 13875.6 MB exceeds 2000 MB threshold — investigate write volume`) confirming IMPROMPTU-10 instrumentation shipped. **But the retention loop does NOT appear to have fired or done useful work today.** The 4-hour periodic retention `_run_periodic_retention()` would first fire at ~17:17 UTC (4h after boot); session ran until 20:42 UTC (at least one iteration expected, probably two). **No `EvaluationEventStore: retention deleted N rows` lines appear in the log.** However, the retention method only logs when `deleted > 0` — so absence is ambiguous between "task never fired" vs "task fired but nothing to delete". The DB size trajectory strongly argues the task is NOT effectively deleting: **13,875 MB at boot today vs 9,294 MB yesterday boot (+49% in one day, +4,581 MB).** This is the same per-day delta as yesterday's C5 finding (+4,518 MB from Monday→Tuesday), which means IMPROMPTU-10 has not changed the growth rate. Freelist 0% rules out "VACUUM failing to reclaim"; retention DELETE is either not running or not finding old rows. **Requires operator DB-side query** (see Open Verification Gaps) before flagging as regression.

7. **Network event profile today was MILD.** 1 brief IBKR Error 1100 at 15:40 UTC immediately restored by Error 1102 at 15:40:45 (12 seconds total) + 1 Databento 40-second stream timeout at 15:40:33 also in the same window, 1 reconnect attempt. No Errno 61, no multi-minute outage. Yesterday had a 2-minute Gateway outage (Errno 61 × 5); Monday had a 40-second Databento+IBKR blip. **Today the cascade was WORSE in raw shares despite the LIGHTEST network stimulus of the three days.** This further undermines the "network events trigger the cascade" model.

8. **Other things that changed:**
   - **Stop-retry-exhaustion events: 45 today vs 34 yesterday (+32%).** Clustered 09:37–10:56 ET (31 events = 69% of total) BEFORE today's 15:40 UTC network event — reinforcing C11 from yesterday (non-network trigger is real). Symbols are largely different from yesterday's list (1 overlap: ECH).
   - **Max-concurrent rejections: 21,692 today vs 21,458 yesterday** (essentially unchanged). Same divergence pattern.
   - **Counterfactual dataset: 22,706 positions opened/closed** (+6.3% vs yesterday's 21,359). Largest single-day capture so far.
   - **No EOD shutdown-tail observable in this log.** Log runs 13:17:37 UTC → 20:42:32 UTC (`SHUTTING DOWN`). No `STOPPED` line. Operator presumably compressed the log mid-shutdown. C9 from yesterday (63-minute shutdown tail) cannot be evaluated today.
   - **One NEW FIX-04 behavior observed (positive):** At 16:17:09 UTC, `Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty` — DEF-158-class dup-SELL prevention **using broker qty to correct a stale ARGUS view**. This is working correctly.

9. **Stable things (unchanged, confirming hypothesis):**
   - Window summaries (DEF-138): 30 today = same as yesterday and Monday.
   - 15 variant strategies spawned at boot (same).
   - `[N/12]` phase labels unchanged (DEF-198 still open).
   - VIXDataService wired cleanly at boot (`ready=True, stale=False`) — FIX-05 still landed correctly.
   - 17 catalyst pipeline cycles (vs yesterday's 16 — uptime-proportional).

---

## Confidence Levels

- **🟢 Proven** — Directly inspected in code + matching mathematical/empirical evidence from the log.
- **🟡 Strongly supported** — Multiple lines of log evidence converge on the same explanation, but not exhaustively traced.
- **🟠 Hypothesis** — Consistent with evidence but not fully verified; operator should validate.
- **⚪ Not verified** — Explicitly noted as a gap requiring DB query or code tracing beyond what was done.

---

## Bucket A — Work-Blocker Findings

### A1 (RESOLVED) 🟢 IMPROMPTU-04's DEF-199 A1 fix landed and is WORKING

**Evidence of A1 working:** 44 `DETECTED UNEXPECTED SHORT POSITION X (Y shares). NOT auto-covering.` ERROR lines fired at 19:50:05 UTC (3:50 PM ET). Cross-check with operator's `ibkr_close_all_positions.py` cleanup transcript:

| Symbol | ARGUS-detected short qty (from log) | Operator BUY qty | Ratio |
|---|---:|---:|---:|
| TSLL | 4,137 | 4,137 | 1.00 |
| NAVI | 1,195 | 1,195 | 1.00 |
| FNGD | 694 | 694 | 1.00 |
| JBLU | 679 | 679 | 1.00 |
| MSTZ | 533 | 533 | 1.00 |
| HIMX | 528 | 528 | 1.00 |
| DHT | 519 | 519 | 1.00 |
| IMAX | 514 | 514 | 1.00 |
| ... (36 more at 1.00×) | | | 1.00 |
| MXL | 5 | 5 | 1.00 |
| **TOTAL** | **14,249** | **14,249** | **1.000** |

**Set equality** between ARGUS-detected and operator-covered: zero symbols only in ARGUS log, zero only in operator list, zero quantity mismatches. **The A1 fix prevented the doubling and surfaced the true upstream cascade to the operator for manual remediation.** This is exactly the designed behavior.

**Severity now:** RESOLVED as a Sprint 31.9 work-blocker. DEF-199 is closed.

**What this does NOT resolve:** The 14,249 shares of unexpected short exposure at EOD. Those came from an upstream cascade mechanism that IMPROMPTU-04 did not address — see **C12 below**.

---

### A2 (NEW) 🟢 A DIFFERENT upstream cascade is producing 44-position short exposure independent of DEF-199

**Severity:** CRITICAL (safety) — fresh work-blocker, distinct from A1/DEF-199.

**What happened today:** 44 broker positions were short at EOD totaling 14,249 shares. This is NOT the DEF-199 "ARGUS sees a long, SELLs, flips it short, doubles it" pattern. Today ARGUS saw the positions as ALREADY-SHORT when it iterated through them at EOD — the A1 fix correctly refused to sell them, and operator had to cover the exact quantities ARGUS reported. The upstream cascade that flipped 14,249 shares short during the session is **mechanistically distinct from DEF-199** and is the larger safety problem now that the doubling is gone.

**Mechanism is NOT yet identified.** Today's log argues against all three candidate mechanisms the Apr 22/23 debriefs hypothesized:

- **Candidate 1 — DEC-372 stop-retry-exhaustion flipping positions short (C4, Apr 22):** 45 stop-retry events fired today (vs 34 yesterday). Cross-reference against 44 EOD-short symbols:
  - Stop-retry symbols: `{ADMA, AMDL, BAR, CGCP, CRML, DB, ECH, ENVX, EWG, FLNC, GSG, INTW, IPGP, IREZ, KODK, MBB, NUVB, NWSA, OBDC, PAR, PCT, PD, PHYS, QUBT, SAN, SBS, SMCX, SOXS, SPRY, TAL, TASK, TSDD, UCO, VIA, VICI, VXX, VZ, WU, XNCR, XNDU}` (40 unique symbols).
  - **Overlap with 44 EOD-short symbols: only 4 — {ECH, PD, SMCX, SOXS}.**
  - The other **40 of 44 EOD shorts have no stop-retry-exhaustion event anywhere in the log.** Stop-retry is not the primary mechanism today.

- **Candidate 2 — Gateway-outage reconnect snapshot showing already-short positions (A1 evidence, Apr 23):** Yesterday logged a single "`Position mismatch after reconnect! ...(MIR -200, CIFR -131, TSLL -809, ...)`" entry enumerating 79 positions with 20 already short at reconnect. **No such log line exists today.** The brief 12-second IBKR Error 1100/1102 blip at 15:40 UTC did not produce this kind of snapshot, nor did reconciliation show a single large jump in mismatches.

- **Candidate 3 — Stray bracket SELL legs filling against already-closed positions:** Only **6 orphan-fill WARNING lines** today (`"T1/T2/Stop fill for X but no matching position"`). Far too few to account for 40 symbol-level short flips.

**What the evidence DOES show:** The position reconciliation mismatch count grew gradually through the day (3 → 5 → 7 → ... → 44), not in a single jump. Reconciliation warnings appear every ~60 seconds via the periodic reconciliation task. 378 reconciliation-mismatch WARNING lines fired across the session. **This argues that positions flipped short one-at-a-time through the session via some mechanism that bypasses ARGUS's tracking entirely** — not a cascade event, but a slow drip.

**One circumstantial clue:** `Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty` at 16:17:09 UTC. ARGUS thought it had 200 long IMSR; IBKR had only 100. FIX-04's DEF-158 path correctly used IBKR's qty for the flatten. But IMSR also appears in the 44-symbol EOD short list at `-200`. So after the 16:17 flatten fired (selling 100), IBKR held 0 net IMSR briefly, and then *something* — subsequent bracket leg fills? re-entries? — took it to -200 by EOD. This suggests **partial-position bracket leg mismatches** (which is a known failure mode documented in yesterday's debrief) combined with **quantity-tracking drift between ARGUS and IBKR**. But this is speculation; full end-to-end tracing of one symbol is needed.

**Why this is a work-blocker:** Without identifying the mechanism, there is no fix. Paper-trading data continues to be contaminated by daily 14K+ share unexpected-short events. Live-trading transition remains unsafe. The A1 fix guarantees the operator SEES the problem at EOD — but doesn't prevent the exposure from accumulating DURING the session. If any of today's 44 shorts had moved significantly against the (unwanted) short direction mid-session, intraday margin calls / losses would have been real regardless of the EOD detector.

**Required regression tests for the eventual fix:** These cannot be written until the mechanism is identified. The investigation must reproduce the gradual-drip pattern (reconciliation mismatch count climbing from 3 → 44 over ~6 hours) in a controlled harness, not just the cascade-event patterns of DEC-372 or network disconnects.

**Required before next paper session:** YES. This is the replacement work-blocker for DEF-199 now that DEF-199 is resolved. NO-GO for another paper session until the root cause is identified and ideally mitigated.

**Escalation needed:** Because today's log reveals this bug has been running silently underneath DEF-199 for at least three consecutive days (and likely longer — it was hidden by A1 doubling every time), the Sprint 31.9 scope should consider whether any of the Stage 3–8 landings interact with this code path and need re-review. No evidence of that from today's log, but the scope question should be answered before next paper session.

---

## Bucket B — Already Covered by Sprint 31.9 Scope

### B1 🟢 FIX-05 / DEF-170 VIX regime intelligence — VALIDATED (matches Apr 23)

```
13:17:44  VIXDataService: loaded 768 cached rows, last date: 2026-04-23
13:17:44  VIXDataService: fetching incremental data (1 days missing since 2026-04-23)
13:17:45  VIXDataService: fetched 2 rows from yfinance (2026-04-24 to 2026-04-25)
13:17:45  VIXDataService: persisted 769 daily rows
13:17:45  VIXDataService: initialization complete, ready=True
13:17:45  VIXDataService wired into Orchestrator (forwarded to RegimeClassifierV2 if present)
13:17:45  VIXDataService initialized (ready=True, stale=False)
```

Cache-load + 1-day incremental fetch + persist + wiring all clean. DB-side VIX field non-null check still a gap (see Open Verification Gaps — **this is the IMPROMPTU-09 VG-9 verification**).

### B2 🟢 FIX-04 execution-layer hardening — VALIDATED + new positive evidence

- Position reconciliation warnings continue firing (378 across the session) with the typed `ReconciliationResult` format. No AttributeErrors on `ReconciliationResult` fields.
- **NEW POSITIVE:** `Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty` at 16:17:09 UTC — this is DEF-158 dup-SELL prevention actively using IBKR's view to correct a stale ARGUS quantity. The fix is **doing useful work** today, not just inert.
- DEC-372 stop-retry refinement landed (45 events today vs 34 yesterday but with much milder network stimulus — interpretation is ambiguous, not a FIX-04 regression).
- Scope boundary correctly observed: FIX-04 did not cover A1 (which IMPROMPTU-04 did) and did not cover A2's mystery mechanism (which nothing has addressed yet).

### B3 🟢 FIX-11 backend lifespan + FIX-03 health monitor expansion — VALIDATED (matches Apr 22/23)

All startup phases `[1/12]` through `[12/12]` fired cleanly with sub-phases. `[8.5/12]` regime intelligence V2, `[10.3/12]` telemetry store, `[10.25/12]` quality pipeline, `[10.4/12]` event routing, `[10.7/12]` counterfactual engine — all present with same ordering as yesterday. `Viable universe set: 6428 symbols` at 13:17:42, `API server started on 0.0.0.0:8000` at 13:17:45 (8 seconds total). Clean.

### B4 🟢 IMPROMPTU-04 C1 fix (pattern_strategy.py:318 INFO→DEBUG) — VALIDATED

Log volume dropped dramatically:
- **Total log lines: 130,593 today vs 938,754 yesterday (86% reduction)**
- **Top logger `argus.strategies.pattern_strategy`: 21,891 lines today vs 829,190 yesterday (97% reduction)**

The `"evaluating X with partial history"` INFO spam is gone. Debriefs will be faster from here on.

### B5 🟢 IMPROMPTU-04 A1 fix — VALIDATED (see A1 above)

44/44 short positions correctly DETECTED + refused + escalated. Zero doublings. The `DETECTED UNEXPECTED SHORT POSITION` ERROR message matches the implementation (`order_manager.py:1707` + `:1684` three-branch logic).

### B6 ⚪ IMPROMPTU-04 Startup invariant — PRESENT but UNEXERCISED today

Code present at `argus/main.py:123` (`check_startup_position_invariant`) + call site at `:376` + gating at `:1074`. Today's boot had `positions=0` from IBKR, so the invariant ran against an empty list, passed silently, and set `_startup_flatten_disabled = False`. **No invariant log line fired** — this is correct behavior per the source (the `if startup_positions:` branch only logs on non-empty lists).

**To exercise the positive-path log:** ARGUS would need to boot while IBKR held any position. Today's session started clean (`Retrieved 0 positions from IBKR` because operator had run `ibkr_close_all_positions.py` the previous close + submitted paper reset). Future sessions where shorts survive to next-day boot will trigger the ERROR branch (`STARTUP INVARIANT VIOLATED: broker returned N non-long position(s)...`).

### B7 🟡 IMPROMPTU-10 evaluation.db retention — AMBIGUOUS evidence (possible regression)

Positive landed evidence:
- `EvaluationEventStore: DB size 13875.6 MB exceeds 2000 MB threshold — investigate write volume` WARNING at 13:17:41 UTC → IMPROMPTU-10's new boot-time threshold WARNING is present.
- `EvaluationEventStore pre-initialized by main.py` at 13:17:44 UTC → pre-init path landed.

Ambiguous evidence:
- **No `retention deleted N rows` INFO line fired during the session.** Session uptime was ~7h 25m. With `RETENTION_INTERVAL_SECONDS = 4 * 60 * 60 = 14,400s`, at least one retention iteration (probably two) should have fired — but the retention method only logs when `deleted > 0` (source code `telemetry_store.py:294`), so silence is consistent with both "task fired and found nothing to delete" AND "task never fired".
- **No `periodic retention iteration failed` WARNING either.** So the loop either didn't run or ran without exceptions and without deletions.
- **No `startup VACUUM complete` at boot** — the startup VACUUM is gated by `STARTUP_RECLAIM_FREELIST_RATIO` but freelist=0.0%, so this is expected.

Growth evidence (strongly suggests retention is NOT deleting):
- Yesterday boot: 9,294 MB. Today boot: 13,875 MB. **+4,581 MB in one day (+49%).**
- This is the SAME per-day delta as Monday→Tuesday (+4,518 MB). IMPROMPTU-10 has **not slowed the growth rate at all**.
- If retention were actively deleting 7+ day old rows, the DB would stabilize at `~7 × per-day write rate` (≈30–35 GB). Since it's 13.8 GB and still growing, it's consistent with either "DB hasn't accumulated 7 days of data yet" OR "retention not deleting". The former is possible only if the DB is <3 days old, which contradicts yesterday's 9.3 GB / Monday's 4.8 GB boot sizes — the DB has been accumulating for at least 3 days of actual content.

**Verdict:** IMPROMPTU-10's boot-threshold warning landed, but the periodic retention loop has not visibly reduced DB size. Either it's not firing, or it's firing but DELETE `WHERE trading_date < cutoff` is finding zero rows. Operator DB-side query is needed:
```sql
SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;
```
If `MIN(trading_date)` is >7 days old, DELETE should have deleted rows and we'd see the INFO log — which we don't. So either MIN is ≤7 days old (retention simply has nothing to do yet, and DB will stabilize on day ~7) OR there's a bug (DELETE not committing, or task not running).

### B8 🟢 Other Stage 3–8 items — unchanged, clean

- **FIX-06 SystemAlertEvent emitter:** No new errors, no SystemAlertEvent emissions (consumer side P1-A1 M9 still pending, as designed).
- **FIX-07 intelligence/catalyst/quality:** 17 pipeline cycles ran cleanly (100 fetched / 100 classified / 64–67 stored per cycle). One more cycle than yesterday (uptime proportional).
- **FIX-08 experiment + learning loop:** 15 variants spawned at boot (same as Apr 22/23). Still 15, not the 22 claimed by CLAUDE.md — **stale doc-sync issue carries over from yesterday's B2**.
- **FIX-09 backtest retirements:** No ImportError / ModuleNotFoundError. Silent as predicted.
- **FIX-13a/b/c + IMPROMPTU-CI:** CI-only, no runtime observable.
- **RETRO-FOLD:** Docs-only on argus side. No runtime observable. Confirmed no unexpected runtime changes.

---

## Bucket C — New Findings

### C1 (RESOLVED) 🟢 pattern_strategy.py:318 INFO-level log spam

Covered by IMPROMPTU-04 C1 fix. See B4 above. Log shrank 86%. Finding is frozen / closed.

---

### C2 (RESOLVED) IBKR stale-position cache

Already downgraded to LOW yesterday; today's 1.00× ratio confirms there's no stale-cache manifestation to remove. Closed.

---

### C3 🟢 `max_concurrent_positions` count diverges from broker state — SAME PATTERN, SLIGHTLY MILDER

**Severity:** HIGH (for live trading; MEDIUM for paper) — unchanged.

**Today's position-count time series:**
- max_concurrent signal rejections: **21,692** (vs yesterday's 21,458 — essentially same, +1%).
- ARGUS internal stayed capped at 50.
- Position reconciliation mismatch count grew gradually 3 → 5 → 7 → 44 through the day.
- Peak reconciliation mismatch: 44 (at EOD). No mid-session peak as dramatic as yesterday's 70 at 11:02 ET (because no 2-min Gateway outage today).
- 44 untracked positions at EOD (vs yesterday's 42, Monday's 51).

**Root cause (unchanged):** The `max_concurrent_positions` check uses only ARGUS's internal `_managed_positions` dict. IBKR broker positions accumulate past ARGUS's view when entry/exit accounting drifts. Today the drift was gradual (not triggered by a network event), strengthening the hypothesis that this is a routine-operation class of bug.

**Required before next paper session:** Not strictly required if A2's mechanism is identified and fixed. C3 is downstream of A2.

---

### C4 🟢 DEC-372 stop-retry-exhaustion events — COUNT UP, OVERLAP WITH EOD SHORTS DOWN

**Severity:** MEDIUM (contributor, but not the primary cause today) — unchanged model, reduced relevance.

**Today: 45 events** (vs yesterday's 34, Monday's 32 — new high count). Distribution:
- 17 events in 13:xx UTC (09:xx ET) — opening-hour cluster
- 14 events in 14:xx UTC (10:xx ET)
- 5 events in 15:xx UTC (11:xx ET) — 4 before the 11:40 ET network blip
- 3 events in 16:xx UTC (12:xx ET)
- 2 events in 17:xx UTC (13:xx ET)
- 2 events in 18:xx UTC (14:xx ET)
- 2 events in 19:xx UTC (15:xx ET)

**Today confirms C11 hypothesis from yesterday:** 31 of 45 (69%) fired before the 15:40 UTC network event. DEC-372 cascades fire without any network trigger. The fix design must handle at least two triggers.

**Overlap with 44-symbol EOD-short list: 4 of 44 (9%).** Much lower than Apr 22's 5 of 51 (10%) and Apr 23's 1 of 42 (2%). **DEC-372 stop-retry is NOT the primary upstream cause of the EOD-short cascade today.** C4 is a separate problem; fixing C4 alone will not materially reduce the EOD-short count.

**Required before next paper session:** No, but the C4 fix session now has clearer data — the design must account for the non-network trigger and accept that fixing C4 alone will NOT close A2.

---

### C5 🟢 `evaluation.db` now 13,875 MB at boot — further +49% / +4,581 MB in one day

**Severity:** HIGH (trajectory) — unchanged from Apr 23 upgrade.

- Monday boot: 4,776 MB.
- Yesterday boot: 9,294 MB (+95%).
- **Today boot: 13,875 MB (+49% vs yesterday, +190% vs Monday).**
- Freelist still 0%.

IMPROMPTU-10 landed its boot-threshold WARNING but the periodic retention appears to have not reduced the per-day growth rate (still ~4.5 GB/day). See B7 above for the full ambiguity analysis.

**Required before next paper session:** No. But operator DB-side query is recommended pre-sprint-close (see Open Verification Gaps) to disposition whether IMPROMPTU-10 actually resolved the retention mechanic or if a follow-up is needed.

---

### C6 🟢 Boot phase labels `[N/12]` vs handoff-claimed `[N/17]` — UNCHANGED

**Severity:** LOW (documentation accuracy). Same as Apr 22/23. DEF-198 still open.

---

### C9 — NOT OBSERVABLE today

The 63-minute shutdown tail from yesterday (C9) cannot be evaluated today because the log ends at `SHUTTING DOWN` with no `STOPPED` line. Log was presumably gzipped while shutdown was still in progress. IMPROMPTU-09 may want to note this gap — no evidence today either for or against the 63-minute hang regression.

---

### C10 🟢 `max_concurrent_positions` WARNING log spam — UNCHANGED

21,692 Risk Manager WARNING lines of the form `"Signal rejected: max concurrent positions (50) reached"`. Still not ThrottledLogger'd. Same LOW severity opportunistic cleanup finding from yesterday.

---

### C11 🟢 Stop-retry-exhaustion fires BEFORE network events — REINFORCED

31 of 45 DEC-372 exhaustions today fired in the 09:37–10:56 ET window, all BEFORE the 15:40 UTC (11:40 ET) brief IBKR blip. With only a 12-second network event in the whole session, basically all morning stop-retry cascades have no proximate network cause. **C11 (design-input for post-31.9 C4 fix) is strengthened: at least two triggers, and today the non-network trigger dominated 4:1.**

---

### C12 (NEW) 🟢 Unidentified upstream cascade flipping 44 positions short through a 6-hour market session

**Severity:** CRITICAL (safety). This is **the replacement A1 / A2 work-blocker** now that DEF-199 is resolved.

**Evidence:** See A2 above for full detail. Short version:
- 44 symbols went short through the session totaling 14,249 shares of unexpected exposure.
- Mechanism is NOT dominantly any of: DEC-372 stop-retry-exhaustion (4/44 overlap), network-triggered reconnect snapshots (no such event today), or bracket SELL leg orphan fills (only 6 orphan-fill warnings total).
- Reconciliation mismatch count grew gradually (3 → 5 → 7 → 44) rather than cascading in a single event — suggests a **slow-drip bug** distinct from all previously-diagnosed cascade mechanisms.
- The 14,249 shares is the true pre-doubling cascade size and it is LARGER than yesterday's (6,949) and Monday's (13,898 equivalent). A1 was masking the growth; with A1 fixed we can now see the upstream is getting WORSE over time, not better.

**Hypotheses for the mechanism (all 🟠 un-traced):**
1. **Partial-position bracket-leg accounting drift:** A bracket entry fills 200 shares but ARGUS-side tracking misses the fill callback for partial chunks (or misattributes them), and subsequent stop/target fills treat ARGUS's phantom remainder as real. Over many cycles, IBKR-side position drifts negative. Consistent with the IMSR 200-vs-100 qty mismatch at 16:17.
2. **Re-entry races on closed positions:** Strategy fires signal N+1 before bracket legs from signal N are fully reconciled, placing BUY N+1 while SELL N+1's bracket legs are still live. One of the legs then fills against the net-negative position IBKR now sees.
3. **Reconciliation-driven reconstruct_from_broker() interaction:** DEC-370's `auto_cleanup_unconfirmed: false` default makes unconfirmed positions immune to reconciliation auto-close, but MAY allow accounting drift to accumulate silently.
4. **Something FIX-04 missed:** DEF-158 dup-SELL prevention is working at `_check_flatten_pending_timeouts` (e.g., the IMSR line). But the same class of bug in a different code path could still fire.

**Required investigation before next paper session:** End-to-end trace of a single symbol. Recommend picking **TSLL** (today's largest at 4,137 shares short) — trace every BUY/SELL order ID, every fill callback, every reconciliation mismatch involving TSLL across the session. The TSLL timeline is in the log (the `grep TSLL logs/argus_20260424.jsonl` command returns 376 lines; many are routine strategy signals but the trade-lifecycle lines starting with `Position opened` / `Position closed` / `Order placed` / `Bracket placed` / `T1 hit` / `T2 hit` / `Stop hit` / `Trail stop triggered` are tractable by hand). **The prompt's specific TSLL question — "4,137 shares today vs yesterday's 1,618; multiplier 2.56× — doubling or not?" — the answer is: today's 4,137 is the true pre-doubling count, NOT a multiplier of yesterday's 1,618.** Yesterday's 1,618 was ARGUS-seen 809 × 2 (DEF-199 doubling). Today's 4,137 is the unmodified upstream cascade size for TSLL. The two numbers represent DIFFERENT cascades flipping different amounts of TSLL short on different days; there is no multiplier relationship between them.

**Required before next paper session:** YES. NO-GO for next paper session until mechanism is identified.

**DEF candidacy:** New DEF number needed. Severity CRITICAL. Likely to require a dedicated impromptu session or an early Sprint 32 session.

---

## Procedure Recommendation

**IMPROMPTU-04 closes successfully** (DEF-199 resolved, C1 fix validated). But **a new work-blocker (A2 / C12) emerges to replace it** and prevents next-paper-session clearance.

**Required before next paper session:**
1. **Operator DB-side verification** of IMPROMPTU-10 retention (B7 / Open Verification Gaps below) — not strictly blocking but should happen before Sprint 31.9 close.
2. **Investigation of C12 upstream cascade mechanism.** Full end-to-end trace of at least one symbol across the session. Preferably TSLL.

**Not needed in this cycle:**
- No IMPROMPTU-04 reopen. A1/C1 fix is working.
- C4/C11 post-31.9 cross-domain session continues as planned but is not the critical-path blocker.
- C3 (max_concurrent divergence) continues as-is; it's downstream of C12.

**Note on IMPROMPTU-09 (verification sweep):** Today's debrief surfaces at least one contradiction with prior findings that IMPROMPTU-09 will need to disposition:
- **Apr 23 A1 confirmed the 2.00× doubling was deterministic.** Today's data reinforces that claim (the fix reliably prevented doubling) but also reveals the upstream cascade that feeds A1 is LARGER than either of the prior two days' post-doubling totals. So while yesterday's A1 analysis was correct about the doubling mechanism, its framing of "the 2.00× is the whole problem" missed that the upstream cascade is itself a safety issue of equal severity. This is not a contradiction of yesterday's finding per se, but an important reframing.

---

## Go / No-Go for Tomorrow's Pre-Open

**NO-GO until A2 / C12 is investigated and the mechanism identified.** Unchanged verdict from the prior two days, but with a new reason.

**Rationale:**
- A1 / DEF-199 is resolved. Paper-trading is no longer blocked by the doubling mechanism.
- **But the upstream cascade is still actively flipping 14,249 shares short per session**, and paper-trading data continues to be contaminated.
- Without knowing the mechanism, there is no way to mitigate besides the A1 detector-and-escalate pattern — which requires operator intervention daily.
- Live-trading transition risk is arguably WORSE than pre-IMPROMPTU-04 because A2/C12 will cause intraday margin events, not just EOD doublings.

**Mitigations if investigation cannot complete quickly:**
- Continue operator `ibkr_close_all_positions.py` routine at EOD. A1 detection provides clear visibility.
- Do NOT increase `max_concurrent_positions` from 50 until A2's mechanism is understood.
- Consider lowering `max_concurrent_positions` temporarily (30?) to reduce the blast radius while investigation happens.

---

## Open Verification Gaps

DB-backed checks required. **Bold items are IMPROMPTU-09 VG-items called out in the operator's debrief prompt.**

| Gap | Query / Action | Purpose |
|---|---|---|
| **VG-9 — VIX dimensions in regime_history.db (FIX-05 / DEF-170 DB-side)** | `SELECT MIN(vix_close), MAX(vix_close), AVG(vix_close), COUNT(*) FROM regime_history WHERE date(timestamp) = '2026-04-24';` | Validates today's B1 finding at DB level |
| **IMPROMPTU-10 retention status (NEW critical gap)** | `SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;` + row counts by date for the last 14 days | Validates whether retention is actually deleting rows. If `MIN(trading_date)` is >7 days old, IMPROMPTU-10 retention is broken. If ≤7 days, retention is "fine but hasn't had anything to delete yet" and the DB will stabilize by day 7. |
| FIX-01 `catalyst_quality` non-constant (unchanged from Apr 22/23) | `SELECT strategy_id, AVG(catalyst_quality), MIN(catalyst_quality), MAX(catalyst_quality), COUNT(*) FROM quality_history WHERE date(created_at) = '2026-04-24' GROUP BY strategy_id;` | Confirms FIX-01 behavioral claim |
| Quality grade distribution shift (unchanged from Apr 22/23) | `SELECT grade, COUNT(*) FROM quality_history WHERE date(created_at) = '2026-04-24' GROUP BY grade ORDER BY grade;` | Confirms Sprint 32.9 recalibration effect |
| Daily cost ceiling for catalyst classifier (unchanged from Apr 22/23) | SQL against `data/catalyst.db` for today's classifier spend + compare to DEC-324 ceiling | Confirms DEC-324 cost-ceiling enforcement |
| **NEW: End-to-end trace of one A2 short-flip (TSLL suggested)** | Extract all TSLL lines with `grep TSLL logs/argus_20260424.jsonl`. Walk through BUY orders, bracket leg placements, reconciliation events, and EOD detection. | Definitive proof of (or refutation of) the C12 partial-position-accounting-drift hypothesis |
| Learning Loop proposal generation (unchanged from Apr 23) | Query `data/learning.db` for today's LearningReport row count | Validates FIX-08 session-end trigger |

---

## Appendix A — Cascade Timeline

| Time (UTC / ET) | Event |
|---|---|
| 13:17:37 UTC / 09:17 AM ET | ARGUS startup (off `16c049a`, 13 min pre-open buffer). `ARGUS TRADING SYSTEM — STARTING` |
| 13:17:39 / 09:17 | IBKR connected at 127.0.0.1:4002 (clientId=1, positions=0). Account equity 777,142.88. IMPROMPTU-04 invariant runs against empty list — passes silently. |
| 13:17:41 / 09:17 | EvaluationEventStore initialized. **WARNING: DB size 13,875.6 MB exceeds 2000 MB threshold** — IMPROMPTU-10 boot-threshold WARNING fires correctly. |
| 13:17:41 / 09:17 | Orchestrator initialized; 15 experiment variants spawned. |
| 13:17:42 / 09:17 | Routing table built; Viable universe 6,428 symbols. |
| 13:17:44–45 / 09:17 | VIXDataService cache-load + incremental fetch + persist + wired into Orchestrator (FIX-05 still clean). |
| 13:17:45 / 09:17 | `API server started on 0.0.0.0:8000`. Total boot: ~8 seconds. |
| 13:17:45 / 09:17 | `ARGUS TRADING SYSTEM — RUNNING`. |
| 13:17:46 / 09:17 | `ALERT: Argus Started — Watching 6428 symbols. Mode: PAPER TRADING` (CRITICAL-level alert, as designed). |
| 13:30 / 09:30 | Market open. |
| 13:36:00 / 09:36 | First Pre-Market High Break signal (TSLL). First BUY order placed. |
| 13:37:37 / 09:37 | **First stop-retry-exhaustion + emergency flatten: SAN** (pre-outage; C11 pattern). |
| 13:37:45 / 09:37 | First position reconciliation mismatch: 3 symbols (MWA, STRC, TSN). Divergence begins accumulating. |
| 13:37–14:56 / 09:37–10:56 | 31 of 45 DEC-372 stop-retry-exhaustions fire in this window — NO network event in this window. |
| 13:38:45 → 19:50:05 / 09:38 → 15:50 | Reconciliation mismatch count grows gradually 3 → 5 → 7 → … → 44 across the session. No cascading jumps. |
| 15:40:14 / 11:40 | **IBKR Error 1100, reqId -1: Connectivity between IBKR and TWS has been lost.** |
| 15:40:24 / 11:40 | Data feed stale for 31.0s (WARNING). |
| 15:40:33 / 11:40 | Databento stream timeout: 40 seconds. Reconnect attempt 1/10. |
| 15:40:39 / 11:40 | Data feed resumed after stale period. |
| 15:40:45 / 11:40 | **IBKR Error 1102, reqId -1: Connectivity restored.** Total network blip: ~31–40 seconds depending on measurement. **No "Position mismatch after reconnect!" snapshot logged today** (unlike Apr 23). |
| 16:17:09 / 12:17 | `Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty` — DEF-158 dup-SELL prevention actively using broker view. (IMSR subsequently appears as -200 short at EOD.) |
| 19:30 / 15:30 | Expected signal cutoff — **no explicit signal cutoff log line observed today.** |
| 19:50:04 / 15:50 | `EOD flatten triggered — closing all positions`. |
| 19:50:05 / 15:50 | `EOD flatten Pass 1: 1 filled, 0 timed out`. |
| 19:50:05 / 15:50 | **44 ERROR lines: `DETECTED UNEXPECTED SHORT POSITION X (Y shares). NOT auto-covering. Investigate and cover manually...`** — IMPROMPTU-04 A1 fix fires correctly. |
| 19:50:05 / 15:50 | **CRITICAL: `EOD flatten: 44 positions remain after both passes: [TSLL, INTC, ECH, MWA, FNGD, IMAX, OTIS, STRC, GLNG, DHT, ...]`** |
| 19:50:05 / 15:50 | `EOD flatten complete. Auto-shutdown in 60s...` |
| 19:51:23 → 19:58:23 / 15:51–15:58 | Periodic reconciliation continues to report the same 44 mismatches (the positions are still there — ARGUS correctly did not SELL). |
| ~19:55 / 15:55 | **Operator observes 44 short positions on IBKR. Runs `ibkr_close_all_positions.py`. BUYs 14,249 shares. ALL 44 at exactly 1.00× ratio — zero doubling.** Submits paper account reset. |
| 20:42:31 / 16:42 | `ARGUS TRADING SYSTEM — SHUTTING DOWN` (CRITICAL alert). |
| 20:42:32 / 16:42 | `Shutdown requested` — last log line observable. **No `STOPPED` line** — log presumably gzipped mid-shutdown. C9 shutdown-tail evaluation not possible today. |

---

## Appendix B — Session Stats

| Metric | Today (Apr 24) | Yesterday (Apr 23) | Monday (Apr 22) | Δ today vs yesterday |
|---|---:|---:|---:|---:|
| Startup commit | `16c049a` | `ffcfb5c` | `f57a965` | IMPROMPTU-04/10 + RETRO-FOLD |
| Session startup→last-log | 7h 25m | 8h 11m | 6h 51m | −46m (early shutdown or early log cut-off) |
| **Total log lines** | **130,593** | **938,754** | **895,543** | **−86%** |
| **Log file size (uncompressed)** | **28 MB** | **184 MB** | **184 MB** | **−85%** |
| INFO / WARNING / ERROR / CRITICAL | 108,693 / 16,707 / 5,189 / 4 | 916,292 / 16,988 / 5,471 / 3 | 876,758 / 14,195 / 4,587 / 3 | INFO −88%, WARN −2%, ERROR −5%, CRIT +1 |
| Top logger (by volume) | `argus.intelligence.counterfactual` — 45,413 (35%) | `argus.strategies.pattern_strategy` — 829,190 (88%) | 798,195 (89%) | **pattern_strategy dropped to 21,891 (17%)** |
| `argus.strategies.pattern_strategy` lines | **21,891** | 829,190 | 798,195 | **−97%** |
| Viable universe | 6,428 | 6,427 | 6,366 | +1 |
| Live + variant strategies | 15 + 15 = 30 | 15 + 15 = 30 | 15 + 15 = 30 | same |
| **`evaluation.db` boot size** | **13,875 MB** | **9,294 MB** | **4,776 MB** | **+49% (+4,581 MB)** |
| Databento disconnects (mid-session) | 1 (40s stream timeout at 15:40 UTC, within IBKR blip) | 0 | 1 (09:29 blip) | similar |
| IB Gateway outages (mid-session) | 1 (Error 1100→1102, ~12s, 15:40 UTC) | 1 (11:01–11:03 ET, Errno 61 × 5) | 1 (09:29 ET Error 1100→1102) | much milder today |
| Stop-retry-exhaustion events (DEC-372) | **45** | 34 | 32 | +32% (highest of 3 days) |
| DEC-372 events BEFORE network blip | 31/45 (69%) | 23/34 (68%) | 0/32 (0%, network at start) | C11 reinforced |
| Position reconciliation mismatch peak | 44 (at EOD, gradual accumulation) | 70 (at 11:02, during outage) | unknown (at least 51 at EOD) | different shape |
| Position reconciliation WARNING lines | 378 | 374 | ~150+ | ~same as yesterday |
| `max_concurrent_positions` WARNING rejections | 21,692 | 10,729 | 8,996 | +102% |
| Total max-concurrent signal rejections | 21,692 | 21,458 | 8,996 | +1% |
| **Untracked SHORT positions at EOD** | **44** | **42** | **51** | **+5%** |
| **Operator BUY cleanup shares** | **14,249** | **13,898** | **34,239** | **+3%** |
| **Pre-doubling upstream cascade shares** | **14,249** (1.00×) | **6,949** (doubled to 13,898) | **~17,120** (doubled to 34,239) | **+105% pre-doubling** |
| **EOD doubling ratio** | **1.00× (A1 fix prevented doubling)** | **2.00×** | **~2.00× (50 of 51 at 2.00×)** | **A1 fix worked** |
| Counterfactual positions opened/closed | 22,706 / 22,706 | 21,359 / 21,359 | 20,658 / 20,658 | +6.3% |
| Trades logged (live) | 900 | unknown | unknown | — |
| Window summaries emitted (DEF-138) | 30 | 30 | 30 | same |
| Catalyst pipeline cycles | 17 | 16 | — | +1 (uptime proportional) |
| CRITICAL events (log) | 4 (startup alert, EOD flatten remaining, shutdown alert + 1) | 3 | 3 | +1 |
| `STARTUP INVARIANT` log fired | No (empty positions at connect) | n/a (fix not yet landed) | n/a | IMPROMPTU-04 present but unexercised |
| `retention deleted N rows` log fired | No (ambiguous — see B7) | n/a (not yet landed) | n/a | IMPROMPTU-10 status inconclusive |
| `DETECTED UNEXPECTED SHORT POSITION` log fired | **Yes, 44×** | n/a | n/a | **IMPROMPTU-04 A1 fix working** |

---

## Appendix C — Key File References

| Finding | File / Line | Status |
|---|---|---|
| DEF-199 A1 fix — EOD Pass 2 side check | `argus/execution/order_manager.py:1707` | **RESOLVED by IMPROMPTU-04 (commit `0623801`)** |
| DEF-199 A1 fix — EOD Pass 1 retry side check | `argus/execution/order_manager.py:1684` | **RESOLVED by IMPROMPTU-04** |
| IMPROMPTU-04 startup invariant helper | `argus/main.py:123` (`check_startup_position_invariant`) | **PRESENT** (unexercised today, positions=0 at connect) |
| IMPROMPTU-04 startup invariant call-site | `argus/main.py:376` | **PRESENT** |
| IMPROMPTU-04 invariant-gated reconstruct_from_broker | `argus/main.py:1074` | **PRESENT** |
| C1 fix — pattern_strategy.py:318 INFO→DEBUG | `argus/strategies/pattern_strategy.py:318` | **RESOLVED by IMPROMPTU-04** (97% log reduction) |
| IMPROMPTU-10 EvaluationEventStore retention | `argus/strategies/telemetry_store.py:154` (spawn), `:275` (cleanup_old_events), `:310` (_run_periodic_retention) | **PRESENT** at boot, **no runtime log evidence** of deletion |
| IMPROMPTU-10 boot threshold WARNING | `argus/strategies/telemetry_store.py` (size-check at init) | **FIRED at boot as designed** |
| NEW: A2 / C12 — unidentified upstream cascade mechanism | **unknown; possibly `argus/execution/order_manager.py` bracket leg accounting** | **NEW WORK-BLOCKER; investigation needed** |
| Campaign state | `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | |
| Yesterday's triage (Apr 23) | `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md` | baseline |
| Monday's triage (Apr 22) | `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` | baseline |
| Debrief protocol | `docs/protocols/market-session-debrief.md` | |

---

## Sprint 31.9 Triage Summary — 2026-04-24

Three-bucket breakdown for direct paste into the Sprint 31.9 tracking conversation.

### Bucket A — Work-blocker findings (immediate fix required)

| ID | Finding | Severity | One-sentence root-cause hypothesis |
|---|---|---|---|
| A1 | **RESOLVED** — IMPROMPTU-04's DEF-199 fix is working; 44 of 44 EOD-detected unexpected shorts correctly refused and escalated to operator with zero doubling. | RESOLVED | DEF-199 closed by IMPROMPTU-04 (commit `0623801`). |
| **A2 (NEW)** | **A different upstream cascade is flipping ~14K shares short per session, independent of DEF-199.** 44 symbols / 14,249 shares short at EOD through a gradual-drip mechanism (reconciliation mismatch count climbs 3 → 44 across 6 hours), NOT via DEC-372 stop-retry (4/44 overlap), NOT via a network reconnect snapshot (no such event), NOT via bracket-leg orphan fills (only 6 total). Mechanism unidentified. | **CRITICAL (safety)** | Likely **partial-position bracket-leg accounting drift** between ARGUS and IBKR (circumstantial evidence: IMSR 200-vs-100 flatten-qty mismatch at 16:17), producing slow divergence that FIX-04's dup-SELL prevention catches on some paths but not others. Mechanism must be identified before next paper session. |

### Bucket B — Already covered by Sprint 31.9 scope

| ID | Finding | Session | Validation verdict |
|---|---|---|---|
| B1 | VIX regime intelligence wiring (DEF-170) | FIX-05 | ✅ VIXDataService ready=True, stale=False at boot. DB-side VIX non-null check still a gap (IMPROMPTU-09 VG-9). |
| B2 | FIX-04 execution-layer hardening + DEF-158 dup-SELL prevention | FIX-04 | ✅ Clean runtime. **Positive NEW evidence:** `Flatten qty mismatch for IMSR: ARGUS=200, IBKR=100 — using IBKR qty` at 16:17 shows DEF-158 actively correcting a stale ARGUS view using broker state. |
| B3 | FIX-11 backend lifespan + FIX-03 health monitor expansion (all 30 strategy components, DebriefService live-mode) | FIX-03 + FIX-11 | ✅ All 30 components healthy; `[N/12]` phases still same labels (DEF-198). |
| B4 | **IMPROMPTU-04 C1 fix (`pattern_strategy.py:318` INFO→DEBUG)** | IMPROMPTU-04 | ✅ **Log volume dropped 86% (130K vs 939K lines); top logger pattern_strategy dropped 97%.** Unambiguously working. |
| B5 | **IMPROMPTU-04 A1 fix (EOD Pass 2 + Pass 1 retry side-check)** | IMPROMPTU-04 | ✅ **44 of 44 unexpected shorts DETECTED + refused + operator manually covered exact quantities. Zero doubling. DEF-199 closed.** |
| B6 | **IMPROMPTU-04 startup invariant** | IMPROMPTU-04 | ⚪ Present, unexercised (positions=0 at connect today). Remains latent-present; will fire on a session that boots with non-empty broker state. |
| B7 | **IMPROMPTU-10 evaluation.db retention** | IMPROMPTU-10 | 🟡 **AMBIGUOUS.** Boot-threshold WARNING landed cleanly. But no `retention deleted N rows` INFO line fired all session, and DB grew +4.58 GB day-over-day (unchanged from pre-IMPROMPTU-10 growth rate). Operator DB-side query needed to disposition. |
| B8 | FIX-06/FIX-07/FIX-08/FIX-09/FIX-13a-c/IMPROMPTU-CI/RETRO-FOLD | various | ✅ All silent/clean; 17 catalyst cycles, 15 variants, no import errors, no WebSocket disconnect crashes. |

### Bucket C — New findings requiring disposition

| ID | Finding | Severity | One-sentence root-cause hypothesis |
|---|---|---|---|
| C1 | pattern_strategy.py:318 log spam | RESOLVED | Covered by IMPROMPTU-04 C1 fix. See B4. |
| C3 | `max_concurrent_positions` divergence (21,692 rejections today, gradual 3→44 reconciliation mismatch climb) | HIGH live / MEDIUM paper | Same mechanism as Apr 22/23; downstream of A2/C12. |
| C4 | 45 DEC-372 stop-retry exhaustions today (+32% vs yesterday), only 4/44 overlap with EOD-short symbols | MEDIUM (contributor but not primary) | Network-unrelated cancel-race dominates (69% pre-network); C4 is real but NOT today's primary cascade driver. |
| C5 | evaluation.db 13,875 MB at boot (+49% / +4.58 GB in one day) | HIGH (trajectory) | IMPROMPTU-10 boot WARNING landed but periodic retention apparently not reducing growth rate. See B7. |
| C6 | `[N/12]` vs handoff-claimed `[N/17]` phase labels | LOW (docs) | Unchanged from Apr 22/23; DEF-198 still open. |
| C9 | Shutdown tail (Apr 23 was 63 min) | N/A today | Log ends at `SHUTTING DOWN` with no `STOPPED` — cannot evaluate. |
| C10 | 21,692 max-concurrent WARNING lines not ThrottledLogger'd | LOW (log hygiene) | Unchanged from Apr 23. Opportunistic cleanup follow-on to C1. |
| C11 | DEC-372 events fire before network events (31/45 pre-network today) | MEDIUM (design input for C4 fix) | Reinforced — non-network trigger is real and dominant today. Post-31.9 C4 fix must account for it. |
| **C12 (NEW)** | **44 unexpected shorts accumulated through the session via unidentified mechanism.** 14,249 shares of pre-doubling exposure. Not DEC-372 (4/44), not reconnect snapshot (no event), not orphan bracket fills (6 total). Reconciliation mismatch grows gradually 3→44. | **CRITICAL (safety)** | **Unidentified — possibly partial-position bracket-leg accounting drift** (IMSR 200-vs-100 circumstantial evidence). This is the **replacement work-blocker** now that DEF-199 is resolved. |

---

*End of Sprint 31.9 Triage Summary — Market Session 2026-04-24.*
