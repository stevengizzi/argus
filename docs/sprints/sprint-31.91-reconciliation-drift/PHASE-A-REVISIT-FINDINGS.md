# Sprint 31.91 — Phase A Revisit Findings Memo

> **Date:** 2026-04-27
> **Status:** Complete; input to Phase B/C revision (third iteration)
> **Predecessors:** First-pass adversarial review (2026-04-27 morning, NOT confirmed, 7 BLOCKING/HIGH); first-pass-revision artifacts (2026-04-27 midday); second-pass adversarial review (2026-04-27 afternoon, NOT confirmed, 5 BLOCKING + 4 HIGH + 6 MEDIUM + 3 LOW)
> **Trigger:** Per protocol §"campaign-orchestration.md §7," second pass with new BLOCKING findings is "diagnostic of deeper issue." Phase A revisit ordered to verify the foundational mechanism premise (B1) before continuing spec revision.

This memo synthesizes the three Phase A info-gathering activities and the
disposition of all 15 second-pass findings. After operator review, the
revised Phase B/C artifacts can be produced from these dispositions.

---

## Phase A Activities — Results

### A1. IBKR OCA late-add behavior spike (B1 + B4 verification)

**Script:** `scripts/spike_ibkr_oca_late_add.py`
**Run:** 2026-04-27 10:47 ET, paper account, clientId=99, SPY
**Result file:** `spike-results-1777301262.json`

**Outcome: `PATH_1_SAFE` (unambiguous).** All three delay variants
(100ms / 500ms / 2s) showed Order C rejected pre-submit with IBKR Error 201
"OCA group is already filled."

**Bonus observation (Trials 2 and 3):** IBKR's enforcement is *stricter*
than just late-add rejection. Once any OCA-group member has filled, *all*
subsequent same-group submissions are rejected — including same-batch
siblings if they lose the microsecond race against fill propagation
(Trial 2's Order B was rejected at submission; Trial 3 same). The OCA
group transitions into a terminal "filled" state.

**Implications:**

1. **Sessions 1a + 1b architecture is sound.** OCA grouping closes the
   IMSR mechanism. Late-add SELLs cannot accidentally fill against zero
   broker position once the group has triggered.

2. **Error 201 / "OCA group is already filled" is the success signature.**
   ARGUS code that submits any OCA-group SELL must distinguish this
   specific Error 201 reason from generic Error 201 rejections (margin,
   etc.) and treat it as a SAFE failure.

3. **Strategy SELL paths must handle OCA-filled gracefully.** Log INFO
   not ERROR; mark as "redundant exit"; do not trigger DEF-158 retry
   path.

4. **Bracket placement should defensively handle OCA-filled on T1/T2
   submission.** Rare but possible if market moves fast enough for the
   stop to fill in the bracket-placement micro-window. DEC-117
   atomic-bracket rollback already handles this; spec should explicitly
   note that Error 201/OCA-filled at this stage is expected.

**Spec impact:** Sessions 1a and 1b add Error-201/OCA-filled handling.
No new sessions required.

### A2. `reconstruct_from_broker()` call-site verification (B3)

**Method:** grep for production call sites of `reconstruct_from_broker`
across the codebase.

**Finding:** Exactly **one** production call site, at `argus/main.py:1081`,
gated by `_startup_flatten_disabled` in the startup sequence. **No
mid-session reconnect path exists today.** All other matches are in
test files.

**Implications:**

1. **B3's catastrophic scenario is forward-looking, not present.** The
   "cancel-all on live mid-session orders" failure mode requires a
   reconnect handler that doesn't exist yet. Sprint 31.93 (DEF-194/195/196)
   is the sprint that would add it; that sprint must avoid naive
   `reconstruct_from_broker()` invocation.

2. **No `ReconstructContext` enum needed in Sprint 31.91.** The fix
   simplifies to a contract docstring on `reconstruct_from_broker()`
   stating: "Currently startup-only. If a future caller needs
   mid-session semantics, they MUST add a context parameter and use a
   different cancellation strategy. Naive invocation on live mid-session
   positions will cancel working bracket children and leave positions
   unprotected."

3. **Live-enable gate disconnect-reconnect criterion moves to Sprint 31.93.**
   Sprint 31.91's gate becomes "≥3 paper sessions with mass-balance
   acceptance AND zero `phantom_short` alerts" (drop the
   disconnect-reconnect leg).

4. **Add a forward-pointer DEF or roadmap.md entry** for Sprint 31.93's
   prerequisites: the reconnect handler must distinguish stale-from-yesterday
   orders from live-this-session orders before any cancel-all.

**Spec impact:** Session 1c spec simplifies — no enum needed, just a
docstring. Adversarial input package's "Revision Rationale" section
updates accordingly. Sprint 31.93 roadmap entry gains a prerequisite.

### A3. B5 audit-rows code-read

**Rows examined:** #1/#2 (`risk_manager.py:335` + `:771`), #3
(`main.py:1412` → drifted to `:1505-1535`), #8 (`order_manager.py:~1734`),
#11 (`health.py:443-450`).

#### Row #1 / #2 — Risk Manager max-concurrent-positions

```python
# argus/core/risk_manager.py:335
positions = await self._broker.get_positions()
max_pos = self._config.account.max_concurrent_positions
if max_pos > 0 and len(positions) >= max_pos:
    return OrderRejectedEvent(reason=f"Max concurrent positions ({max_pos}) reached")
```

**Confirmed UNSAFE.** `len(positions)` includes broker-state phantom
shorts. With 44 phantom shorts and `max_concurrent_positions: 50`, ARGUS
has 6 effective slots for legitimate longs. Audit disposition
"side-agnostic; count is correct regardless" was wrong-rationale.

**Fix:** Same pattern as Session 2b's margin-circuit fix:
```python
positions = await self._broker.get_positions()
long_positions = [p for p in positions if p.side == OrderSide.BUY]
if max_pos > 0 and len(long_positions) >= max_pos:
```
Plus log breakdown line + regression test (phantom-short count > 0
should not cause `concurrent_positions_exceeded` rejections).

#### Row #3 — `main.py:1505-1535` reconcile call site

```python
broker_pos_list = await self._broker.get_positions()
broker_positions: dict[str, float] = {}
for pos in broker_pos_list:
    symbol = getattr(pos, "symbol", "")
    qty = float(getattr(pos, "shares", 0))
    if symbol and qty != 0:
        broker_positions[symbol] = qty

await self._order_manager.reconcile_positions(broker_positions)
```

**Already in Session 2a's scope.** This is exactly the side-stripped
`dict[str, float]` contract DEC-385's typed-contract refactor fixes.
Audit's disposition is correct; only the line reference needs update
(was `:1412`, now `:1505-1535` after intervening edits).

**Spec impact:** Session 2a spec line references update.

#### Row #8 — `order_manager.py:~1734` EOD Pass 2 short detection

```python
elif side == OrderSide.SELL:
    logger.error(
        "EOD flatten: DETECTED UNEXPECTED SHORT POSITION %s (%d shares). "
        "NOT auto-covering. Investigate and cover manually...",
        symbol, qty,
    )
```

**Audit is technically correct** (no `place_order` call) **but incomplete
in spirit.** This site detects the canonical phantom-short condition and
emits only a log line. After Session 2b ships the `phantom_short`
`SystemAlertEvent`, this site should ALSO emit it — otherwise we have
two detection points (this site + reconciliation orphan loop) producing
different observability for the same condition.

**Fix:** Session 2b expansion. EOD Pass 2 short-detection emits
`SystemAlertEvent(alert_type="phantom_short", severity="critical",
source="eod_flatten", ...)` in addition to the existing log line. Add
unit test asserting alert is emitted.

#### Row #11 — `health.py:443-450` daily integrity check

```python
unprotected = []
for pos in positions:  # iterates ALL positions, no side filter
    symbol = getattr(pos, "symbol", str(pos))
    if symbol not in symbols_with_stops:
        unprotected.append(symbol)

if unprotected:
    msg = f"Positions WITHOUT stop orders: {', '.join(unprotected)}"
    logger.error(msg)
    await self._send_alert(
        title="Integrity Check FAILED",
        body=msg,
        severity="critical",
    )
```

**Audit understated the impact.** Iterates ALL broker positions
(long + short) without side filter and emits `severity="critical"`
alerts via `_send_alert(...)` for each position without a stop. With
44 phantom shorts present, it fires 44 generic "Integrity Check FAILED"
critical alerts, drowning out the specific `phantom_short` taxonomy.

**Fix:** Session 2b expansion. Integrity check becomes side-aware:
- Long-orphans without stops → existing "Integrity Check FAILED" alert
  (preserve current behavior; legitimate concern)
- Shorts (which by construction have no stops AND should not have stops
  because ARGUS is long-only) → emit specific `phantom_short` alert,
  excluded from the "missing stop" count
- "Daily integrity check: All N positions have stops. OK." logging
  becomes "Daily integrity check: N longs protected, M shorts (phantom)
  detected and routed to phantom_short alert."

#### Cumulative B5 impact

Three sites needing side-awareness, all the same pattern (side-aware
filter + side-routed alert). All fold into the H3-split 2b.2 session.
2b.2's scope grows but stays under compaction threshold because the
pattern is uniform across the three sites.

---

## Findings × Dispositions Table

### BLOCKING (5)

| # | Finding | Spike-dependent? | Disposition | Spec impact |
|---|---------|------------------|-------------|-------------|
| **B1** | OCA late-add semantics unverified | YES | **Resolved by spike: PATH_1_SAFE.** Sessions 1a+1b sound. | Document Error 201/OCA-filled as success signature. Add to Sessions 1a + 1b deliverables. |
| **B2** | `cancel_all_orders(symbol)` propagation race | NO | **ACCEPT.** Extend signature with `await_propagation: bool = False`. Session 1c sites use `await_propagation=True`. On 2s timeout, abort SELL + emit `cancel_propagation_timeout` alert. | Session 0 signature change; Session 1c usage. New alert type. |
| **B3** | `reconstruct_from_broker()` mid-session reconnect risk | NO (verified) | **Simplified.** No `ReconstructContext` enum needed today (no mid-session call site). Add contract docstring + Sprint 31.93 prerequisite. Live-enable disconnect-reconnect leg moves to 31.93. | Session 1c gets docstring. Sprint 31.93 roadmap entry. Live-enable gate criteria simplifies. |
| **B4** | IMSR replay can't validate Session 1 OCA mechanism | YES (paired with B1) | **Spike serves as the falsification test.** PATH_1_SAFE is the in-suite proof. Add the spike script to repo as `scripts/spike_ibkr_oca_late_add.py` for re-running on future regressions. Upgrade DEF-208 to "blocking on Sprint 31.91 closeout" preserved. | Session 4 reframe: spike-script-rerun is the OCA mechanism check; mass-balance script + IMSR-from-Apr-24-log are the cumulative-fix checks. |
| **B5** | Risk Manager max-concurrent-positions side-blind on broker reads | NO (verified) | **Confirmed UNSAFE + 2 sibling sites.** Three-site pattern: `risk_manager.py:335`+`:771`, `order_manager.py:~1734`, `health.py:443-450`. All need side-awareness. | Session 2b → split into 2b.1 + 2b.2 (per H3); 2b.2 takes all 3 sites. |

### HIGH (4)

| # | Finding | Disposition | Spec impact |
|---|---------|-------------|-------------|
| **H1** | `bracket_oca_type: 0` mid-session flip inconsistent | **ACCEPT.** Make rollback restart-required. Document in runbook; remove "mid-session escape hatch" framing from Performance Considerations. | Sprint Spec Performance Considerations rewritten. Runbook section in `live-operations.md`. |
| **H2** | 5-share mass-balance tolerance unjustified | **ACCEPT.** Replace single tolerance with categorized variance (`expected_partial_fill` / `eventual_consistency_lag` / `unaccounted_leak`). Live-enable gate: zero `unaccounted_leak` rows across 3 paper sessions. | Session 4 script redesign. Acceptance criteria reframed. |
| **H3** | Sessions 2b/2c borderline scoring; pre-empt split | **ACCEPT.** 2b → 2b.1 + 2b.2; 2c → 2c.1 + 2c.2. Sprint becomes 12 sessions. Duration 5–6 weeks. | Session Breakdown major rewrite. |
| **H4** | Synthetic IMSR replay is a tautology | **ACCEPT.** Apr 24 log confirmed available at `logs/argus_2026-04-24.log` AND `logs/argus_20260424.jsonl` (per operator). Use `.jsonl` for the mass-balance script; remove synthetic-recreation language entirely. | Session 4 spec amendment. |

### MEDIUM (6)

| # | Finding | Disposition | Spec impact |
|---|---------|-------------|-------------|
| **M1** | "Deterministic per-bracket ULID" oxymoron | **ACCEPT.** Specify `oca_group_id = f'oca_{parent_ulid}'` (or SHA-256 truncation if IBKR ocaGroup field length is bounded; verify against `ib_async`). | Sprint Spec D2; SbC edge case row. |
| **M2** | `_broker_orphan_long_cycles` lifecycle gaps | **ACCEPT.** Specify cleanup on broker-zero (3-cycle), exponential-backoff re-alert (3 → 6 → 12 → 24 capped at hourly), reset on session start. | Session 2b.1 spec. |
| **M3** | Operator override audit-log schema unspecified | **ACCEPT.** `phantom_short_override_audit` table in `data/operations.db` with full schema. Persists across restarts. | Session 2d spec. |
| **M4** | 3-cycle clear-threshold without independent justification | **PARTIAL ACCEPT.** Default to `5` instead of `3` (cost-of-error asymmetry: phantom-short re-engagement is strictly worse than DEC-370's miss-counter false positive). Configurable; can tune later. | Session 2c.2 default value. |
| **M5** | Per-symbol gate state lost on restart | **ACCEPT.** Persist `phantom_short_gated_symbols` to `data/operations.db`. Rehydrate on startup before OrderManager processes events. Closes 60s window of unsafe entries on restart. | Session 2c.1 expansion. |
| **M6** | 4 alerts without UI integration | **PARTIAL ACCEPT.** Combine reviewer's option (2)+(3): ship `scripts/poll_critical_alerts.py` CLI tool this sprint (~half-session, fold into Session 2d) AND tighten live-enable gate to require Command Center surface from a future DEF-014 expansion sprint. | Session 2d expansion. Live-enable gate addition. |

### LOW (3)

| # | Finding | Disposition | Spec impact |
|---|---------|-------------|-------------|
| **L1** | AlpacaBroker ABC throwaway | **ACCEPT.** `raise DeprecationWarning("AlpacaBroker queued for retirement in Sprint 31.94")` instead of throwaway functional code. | Session 0 spec. |
| **L2** | Disconnect-reconnect test method unspecified | **MOOT.** Per B3, disconnect-reconnect leg moves to Sprint 31.93. | n/a |
| **L3** | ≥10 startup gated symbols threshold arbitrary | **ACCEPT.** Always fire one aggregate alert + always fire per-symbol alerts (no suppression). Removes boundary-case awkwardness. | Session 2d spec. |

---

## Sprint 31.91 Revised Shape

**12 sessions** (was 10 after first pass; 6 originally):

| # | Session | Scope summary |
|---|---------|---------------|
| 0 | `Broker.cancel_all_orders(symbol, *, await_propagation: bool = False)` API extension | ABC + 3 impls (AlpacaBroker DeprecationWarning) + tests |
| 1a | Bracket OCA grouping | + Error 201/OCA-filled defensive handling on T1/T2 submission |
| 1b | Standalone-SELL OCA threading (4 paths) | + Error 201/OCA-filled graceful handling (log INFO, mark redundant) |
| 1c | Broker-only paths safety | Sites use `await_propagation=True`; `reconstruct_from_broker()` gets contract docstring |
| **— Tier 3 architectural review fires here (after 1c) —** | | |
| 2a | Reconciliation contract refactor | Line refs updated to current `:1505-1535` |
| 2b.1 | Broker-orphan SHORT branch + `phantom_short` alert + long-cycle infrastructure | M2 lifecycle (cleanup/backoff/reset) |
| 2b.2 | **Side-aware reads:** margin-circuit reset + Risk Manager position cap + EOD Pass 2 alert emission + Health integrity check | All 3 B5 sites; same pattern |
| 2c.1 | Per-symbol gate state + handler + per-symbol granularity | M5 SQLite persistence |
| 2c.2 | Clear-threshold + auto-clear logic | M4 default = 5 cycles |
| 2d | Operator override API + aggregate alert + runbook + `poll_critical_alerts.py` CLI | M3 audit-log schema; M6 CLI tool; L3 always-both-alerts |
| 3 | DEF-158 retry side-check + severity fix | (unchanged) |
| 4 | Mass-balance categorized variance + Apr 24 log replay + live-enable gate criteria | H2 categorized; H4 .jsonl direct; live-enable revised |

**Sprint duration:** 5–6 weeks. Operator daily-flatten mitigation continues throughout.

**Token budget:** ~165K → ~195K (12 sessions × ~13K + Tier 3 + buffer).

**Live-enable gate (revised):**
- ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows
- AND zero `phantom_short` alerts across those sessions
- AND first-day-live monitored validation (smallest position size, single symbol)
- ~~~~Disconnect-reconnect leg~~~~ — moved to Sprint 31.93's gate
- ~~~~Command Center surface for `phantom_short*` alerts~~~~ — moved to DEF-014 expansion sprint's gate

---

## Risk and Confidence Assessment

The spike is the highest-confidence-density evidence the planning process
has produced. Path 1 collapses ~half the second-pass blocking findings to
spec amendments. Path 2 would have required architectural reformulation;
we don't need that now.

Remaining risks:

1. **Single-spike-run replication.** The spike was run once. IBKR paper
   semantics are documented as "loose" relative to live. Recommend
   re-running the spike against live IBKR with smallest-size during the
   monitored first-day live validation period (live-enable gate
   addition).

2. **Compaction-score drift on 2b.2.** Three sites + alert-emission
   wiring + state changes might push 2b.2 above 13.0 once full
   Creates/Modifies enumeration is done in the revised Session
   Breakdown. Watch threshold; further split if needed.

3. **Mass-balance categorization complexity.** H2's three-category split
   needs careful definition. `expected_partial_fill` is well-defined
   (ARGUS-side accounting matches a working order); `eventual_consistency_lag`
   needs a precise time-window definition (1 reconciliation cycle? 2?).
   The categorization logic is non-trivial and warrants Tier 2 review
   focus on Session 4.

4. **Third-pass adversarial review.** Strongly recommended after Phase B/C
   revision. If a third pass surfaces yet another tier of new BLOCKING
   findings, that's the trigger to seriously consider whether ARGUS's
   broader architecture (not just this fix) needs rework before a
   live-trading transition.

---

## Next Steps

1. **Operator review of this memo.** Confirm dispositions; flag anything
   I've miscategorized.

2. **Phase B revision** — revised design summary capturing 12-session
   shape and all dispositions. Compaction insurance for the rest of the
   revision pass.

3. **Phase C revision** — sprint-spec, session-breakdown, SbC,
   escalation-criteria, regression-checklist, doc-update-checklist;
   adversarial-review-input-package gets second Revision Rationale
   section.

4. **Phase C-1 third-pass adversarial review** — separate Claude.ai
   conversation against revised artifacts. If clears with minor
   observations only → Phase D. If new BLOCKING findings → diagnostic of
   deeper issue, escalate.

5. **Phase D** — 12 implementation prompts + 12 Tier 2 review prompts +
   work journal handoff prompt.

---

*End Sprint 31.91 Phase A Revisit Findings Memo.*
