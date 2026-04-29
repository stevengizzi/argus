# Sprint 31.92 Design Summary

**Sprint Goal:** Close the two uncovered DEF-204 mechanism paths surfaced by the 2026-04-28 paper-session debrief — Path #1 (trail-stop / bracket-stop concurrent-trigger race; canonical trace BITU 13:36→13:41) and Path #2 (locate-rejection-as-held-order retry storm; canonical trace PCT 3,837 shares short) — plus a structural long-only SELL-volume ceiling as defense-in-depth, plus the DEF-212 `_OCA_TYPE_BRACKET` constant-drift rider. Resolves residual ~2% of DEF-204's mechanism that DEC-386 did not cover. CRITICAL safety, non-safe-during-trading, adversarial review required.

---

**Session Breakdown:**

- **Session 1a (`s1a-spike-path1`):** Phase A spike — characterize IBKR amend-stop-price latency vs cancel-and-await latency on paper IBKR; emit go/no-go decision for Path #1 mechanism (4 candidate options).
  - Creates: `scripts/spike_def204_round2_path1.py`, `scripts/spike-results/spike-def204-round2-path1-results.json`
  - Modifies: (none)
  - Integrates: N/A — outputs consumed by S2a/S2b spec.

- **Session 1b (`s1b-spike-path2`):** Phase A spike — capture exact IBKR rejection error-string fingerprint for `"contract is not available for short sale"`; characterize IBKR hold-pending-borrow release timing window (median, p95, p99); validate that SimulatedBroker can be extended to replay this state.
  - Creates: `scripts/spike_def204_round2_path2.py`, `scripts/spike-results/spike-def204-round2-path2-results.json`
  - Modifies: (none)
  - Integrates: N/A — outputs consumed by S3a/S3b spec.

- **Session 2a (`s2a-path1-trail-flatten`):** Implement chosen Path #1 mechanism in `_trail_flatten` only. Recommended default (gated by spike): cancel-and-await the bracket stop using existing `cancel_all_orders(symbol, await_propagation=True)` infrastructure before placing the trail-stop SELL, accepting bounded 50–200ms unprotected gap as the cost of correctness. AMD-2 invariant ("sell before cancel") is INTENTIONALLY MODIFIED.
  - Creates: (10–14 tests in `tests/execution/order_manager/test_def204_round2_path1.py`)
  - Modifies: `argus/execution/order_manager.py` (`_trail_flatten`)
  - Integrates: S1a spike result; preserves DEC-386 OCA threading; preserves DEC-385 phantom-short detection.

- **Session 2b (`s2b-path1-other-paths`):** Apply same Path #1 mechanism to `_resubmit_stop_with_retry` emergency-flatten path (the 38 "Stop retry failed → emergency flatten" events on Apr 28). Apply to `_escalation_update_stop` IFF spike confirms applicability (bracket-stop displacement scenario).
  - Creates: (8–10 tests appended to S2a test module)
  - Modifies: `argus/execution/order_manager.py` (same file as S2a)
  - Integrates: S2a's mechanism choice and helper, if any.

- **Session 3a (`s3a-path2-fingerprint`):** Add `_LOCATE_REJECTED_FINGERPRINT` substring constant + `_is_locate_rejection(error)` helper in `argus/execution/ibkr_broker.py`, mirroring DEC-386's `_is_oca_already_filled_error` pattern. Add `OrderManager._locate_suppressed_until: dict[str, float]` symbol-keyed suppression state with config-driven `locate_suppression_seconds` (default 300s, validated by S1b spike). Implement suppression-timeout fallback path (publishes `phantom_short_retry_blocked` if held order never resolves within window).
  - Creates: `_LOCATE_REJECTED_FINGERPRINT`, `_is_locate_rejection()`, suppression dict + helper methods, ~10–12 tests in `tests/execution/order_manager/test_def204_round2_path2.py`
  - Modifies: `argus/execution/ibkr_broker.py`, `argus/execution/order_manager.py`, `argus/core/config.py` (add `OrderManagerConfig.locate_suppression_seconds`)
  - Integrates: S1b spike fingerprint string + window measurement; reuses DEC-388 `phantom_short_retry_blocked` alert path from DEC-385.

- **Session 3b (`s3b-path2-emit-sites`):** Wire `_is_locate_rejection()` exception-classification + suppression check into all four standalone-SELL paths: `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`. Each site checks suppression BEFORE placing SELL (skip + INFO log if suppressed) and classifies `place_order` exceptions into the locate-rejection branch (set suppression + INFO log + NO retry).
  - Creates: (8–10 tests appended to S3a test module)
  - Modifies: `argus/execution/order_manager.py` (same 4 SELL emit sites)
  - Integrates: S3a's helper + suppression dict.

- **Session 4a (`s4a-ceiling`):** Implement long-only SELL-volume ceiling as structural defense-in-depth (AC4). Add `ManagedPosition.cumulative_sold_shares: int = 0` field (per-position, NOT per-symbol). Increment on every confirmed SELL fill (in `on_fill` for SELL-side orders). Guard at every SELL emit site: BEFORE `place_order(SELL)`, assert `cumulative_sold_shares + requested_qty ≤ shares_total`; if violation, refuse SELL + emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical")` + log CRITICAL. Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`, fail-closed).
  - Creates: `ManagedPosition.cumulative_sold_shares` field, `_check_sell_ceiling()` helper, parametrized regression test enumerating all 5+ SELL emit sites, ~12–14 tests
  - Modifies: `argus/execution/order_manager.py`, `argus/core/config.py` (add 2 OrderManagerConfig fields)
  - Integrates: Independent of Path #1/#2 fixes — composes additively.

- **Session 4b (`s4b-def212-rider`):** DEF-212 wiring. Extend `OrderManager.__init__` to accept `bracket_oca_type: int` parameter (NOT full `IBKRConfig` — minimal surface change to leave broader component-ownership refactor for Sprint 31.93). Update `argus/main.py` construction call site (the only one) to pass `config.ibkr.bracket_oca_type`. Replace 4 occurrences of module constant `_OCA_TYPE_BRACKET` with `self._bracket_oca_type`. Delete the module constant. Tier 3 #1 Concern A relocation (`_is_oca_already_filled_error` → `broker.py`) DEFERRED to Sprint 31.93 (file overlap with component-ownership scope).
  - Creates: ~6–8 tests in `tests/execution/order_manager/test_def212_oca_type_wiring.py`
  - Modifies: `argus/execution/order_manager.py`, `argus/main.py`
  - Integrates: Touches construction surface; coordinates with S4a's OrderManager modifications via merge ordering.

- **Session 5a (`s5a-validation-path1`):** Falsifiable end-to-end validation for Path #1. Build synthetic concurrent-trigger scenario via SimulatedBroker fixture: position with bracket stop at $14.39, trail stop trips at $14.44 simultaneously with bracket trigger price; assert AC1 (`total_sold ≤ position.shares_total`) AND AC4 (no ceiling violation alerts). Replays the BITU 13:41 trace structurally.
  - Creates: `scripts/validate_def204_round2_path1.py`, `scripts/spike-results/sprint-31.92-validation-path1.json`, ~6 tests in `tests/integration/test_def204_round2_validation.py`
  - Modifies: (light fixture additions only)
  - Integrates: Validates S2a + S2b + S4a together.

- **Session 5b (`s5b-validation-path2-and-end-to-end`):** Falsifiable end-to-end validation for Path #2 + composite. Synthetic locate-rejection storm: SimulatedBroker fixture rejects first SELL with locate-not-available, releases held order at random time within suppression window, asserts ≤1 SELL emit per symbol within window AND fill propagates correctly. Composite: stress-test all 5 SELL emit sites with ceiling enabled; assert zero phantom shorts under load.
  - Creates: `scripts/validate_def204_round2_path2.py`, `scripts/validate_def204_round2_composite.py`, `scripts/spike-results/sprint-31.92-validation-{path2,composite}.json`, ~9 tests appended to S5a test module
  - Modifies: (light fixture additions to test SimulatedBroker harness)
  - Integrates: Validates S3a + S3b + S4a together AND validates the entire sprint composite (Path #1 + Path #2 + ceiling).

---

**Key Decisions:**

- **DEC-390 (proposed; reserved at Phase A) — Concurrent-Trigger Race Closure + Locate-Rejection Hold Detection + Long-Only SELL-Volume Ceiling.** Four-layer composition mirroring DEC-385/386's layered-decomposition pattern: (L1) Path #1 mechanism — cancel-and-await before SELL on `_trail_flatten`, `_resubmit_stop_with_retry` emergency path, and conditionally `_escalation_update_stop`; (L2) Path #2 — `_is_locate_rejection()` substring fingerprint + symbol-keyed suppression dict + suppression-timeout fallback to `phantom_short_retry_blocked` alert; (L3) `ManagedPosition.cumulative_sold_shares` long-only SELL-volume ceiling as structural defense-in-depth; (L4) DEF-212 rider — `OrderManager.__init__(bracket_oca_type)` wiring replaces `_OCA_TYPE_BRACKET` module constant.
- **Path #1 mechanism choice:** Empirical via S1a spike, with prior-recommended OPTION (b) cancel-and-await — aligned with DEC-386 S1c's existing `await_propagation` infrastructure, accepts bounded 50–200ms unprotected window as cost of correctness, simplest correctness story. Spike must measure (a) amend-stop-price latency to confirm (b) is the better trade-off; if amend latency is ≤50ms reliably, switch to (a). OPTION (c) recon-trusts-marker REJECTED at Phase A (requires `redundant_exit_observed` persistence which DEC-386 explicitly deferred to Sprint 35+ Learning Loop V2). OPTION (d) hybrid REJECTED (premature complexity).
- **AC4 ceiling granularity:** Per-`ManagedPosition` (NOT per-`(symbol, session)`). ARGUS supports multiple positions on same symbol within session (sequential ORB Breakout entries on AAPL); per-symbol ceiling would conflate them.
- **`_is_oca_already_filled_error` relocation (Tier 3 #1 Concern A) DEFERRED.** Stays in `ibkr_broker.py` for this sprint. File overlap with Sprint 31.93 component-ownership refactor; that sprint is the natural home.
- **DEC-386 NOT amended in-place.** Empirical claim of `~98% mechanism closure` was made in good faith from data available 2026-04-27. Apr 28 falsification is recorded in the debrief and DEC-390's Context section. Preserves historical record.
- **DEF-231 NOT filed.** The 43 pre-existing shorts at Apr 28 boot were operator-side missed-run of `ibkr_close_all_positions.py` the night prior, not a script defect. Script is doing its job; debrief HIGH severity item retracted at Phase A.

---

**Scope Boundaries:**

- **IN:**
  - Path #1 (trail-stop / bracket-stop concurrent trigger) closure across `_trail_flatten`, `_resubmit_stop_with_retry` emergency path, and conditionally `_escalation_update_stop`
  - Path #2 (locate-rejection-as-held) detection + suppression across all 4 standalone-SELL paths
  - Long-only SELL-volume ceiling on `ManagedPosition` as structural defense-in-depth
  - DEF-212 rider: `IBKRConfig.bracket_oca_type` wired into `OrderManager.__init__`, `_OCA_TYPE_BRACKET` constant deleted
  - Falsifiable end-to-end validation (S5a + S5b)
  - DEC-390 materialization at sprint-close

- **OUT:**
  - Structural refactor of `_flatten_position`, `_trail_flatten`, `_escalation_update_stop`, `_check_flatten_pending_timeouts` beyond AC1–AC4 (Sprint 31.93)
  - DEC-386 4-layer architecture modifications (S0/S1a/S1b/S1c byte-for-byte preserved)
  - DEC-385 6-layer side-aware reconciliation modifications
  - DEF-158 retry 3-branch side-check modifications (Path #2 adds a NEW upstream detection point at `place_order` rejection, NOT a 4th branch)
  - `evaluation.db` 22GB bloat (Sprint 31.915 — already merged)
  - `_is_oca_already_filled_error` relocation to `broker.py` (Tier 3 #1 Concern A → Sprint 31.93)
  - DEF-211 D1+D2+D3 (Sprint 31.94)
  - DEF-194/195/196 reconnect-recovery (Sprint 31.94)
  - DEF-178/183 alpaca retirement (Sprint 31.95)
  - Sprint 31B Research Console
  - 4,700 broker-overflow routings analysis (debrief explicitly defers; separate analysis pass)
  - DEF-215 reconciliation-WARNING throttling (deferred per its own routing)
  - `ibkr_close_all_positions.py` post-run verification feature (operator-tooling enhancement; out of safety-sprint scope; can be picked up as future opportunistic touch — operator confirmed 2026-04-29 the Apr 28 shorts were missed-run human error, not a script defect)

---

**Regression Invariants:**

- R1: DEC-117 atomic bracket order placement — preserved.
- R2: DEC-364 `cancel_all_orders()` no-args ABC contract — preserved (uses positional+keyword overload from DEC-386 S0).
- R3: DEC-369 broker-confirmed reconciliation immunity — preserved.
- R4: DEC-372 stop retry caps + exponential backoff — preserved.
- R5: DEC-385 6-layer side-aware reconciliation monotonic-safety matrix — preserved.
- R6: DEC-386 4-layer OCA architecture (S0/S1a/S1b/S1c) — preserved byte-for-byte.
- R7: DEC-388 alert observability subsystem — preserved; this sprint ADDS one alert type (`sell_ceiling_violation`) and re-uses one existing (`phantom_short_retry_blocked`).
- R8: DEF-158 retry 3-branch side-check (BUY → resubmit / SELL → alert+halt / unknown → halt) — preserved verbatim. Path #2 adds a NEW detection at `place_order` exception, NOT a modification of the 3-branch gate.
- R9: `# OCA-EXEMPT:` exemption mechanism — preserved.
- R10: AMD-2 "sell before cancel" ordering invariant on `_trail_flatten` — **INTENTIONALLY MODIFIED** if S1a spike selects OPTION (b). Adversarial review must scrutinize this. DEC-390 must call out the change explicitly with rationale.
- R11: 5,269 pytest + 913 Vitest preserved green at sprint baseline.
- R12 (NEW): Long-only SELL-volume ceiling — `cumulative_sold_shares ≤ shares_total` for every `ManagedPosition` at all times. Parametrized regression test enumerates all SELL emit sites.
- R13 (NEW): DEF-212 wiring — no occurrences of `_OCA_TYPE_BRACKET` after S4b lands; grep regression guard.

---

**File Scope:**

- **Modify:**
  - `argus/execution/order_manager.py` (S2a, S2b, S3a, S3b, S4a, S4b — 6 sessions touch this file; sequential by necessity)
  - `argus/execution/ibkr_broker.py` (S3a — fingerprint helper)
  - `argus/main.py` (S4b — `OrderManager` construction call site)
  - `argus/core/config.py` (S3a, S4a — 3 new `OrderManagerConfig` fields total)
  - `config/system_live.yaml` (S3a, S4a — new fields surfaced)
  - `tests/execution/order_manager/test_def204_round2_path1.py` (new, S2a + S2b)
  - `tests/execution/order_manager/test_def204_round2_path2.py` (new, S3a + S3b)
  - `tests/execution/order_manager/test_def204_round2_ceiling.py` (new, S4a)
  - `tests/execution/order_manager/test_def212_oca_type_wiring.py` (new, S4b)
  - `tests/integration/test_def204_round2_validation.py` (new, S5a + S5b)
  - `scripts/spike_def204_round2_path{1,2}.py` (new, S1a + S1b)
  - `scripts/validate_def204_round2_path1.py` (new, S5a)
  - `scripts/validate_def204_round2_path2.py` (new, S5b)
  - `scripts/spike-results/spike-def204-round2-path{1,2}-results.json` (new, S1a + S1b)
  - `scripts/spike-results/sprint-31.92-validation-path1.json` (new, S5a, autogenerated + committed)
  - `scripts/spike-results/sprint-31.92-validation-path2.json` (new, S5b, autogenerated + committed)

- **Do not modify:**
  - `argus/execution/broker.py` (ABC — touching it is Sprint 31.93's prerogative)
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement)
  - `argus/execution/simulated_broker.py` (test fixture extensions OK; semantic changes OUT)
  - DEC-385 / DEC-386 / DEC-388 implementation surfaces beyond the explicitly-modified sites listed above
  - `IBKRBroker.place_bracket_order` (DEC-386 S1a)
  - `_handle_oca_already_filled` (DEC-386 S1b)
  - `reconcile_positions()` Pass 1 / Pass 2 (DEC-385)
  - `check_startup_position_invariant()` in `argus/main.py` (Sprint 31.94 D2)
  - `reconstruct_from_broker()` (Sprint 31.94 D1)
  - HealthMonitor consumer / `POLICY_TABLE` / alert REST + WS surfaces (DEC-388 — ADD a `POLICY_TABLE` entry for `sell_ceiling_violation`, do NOT refactor)
  - Frontend (`AlertBanner`, `AlertToastStack`, `AlertsPanel`) — OUT of scope

---

**Config Changes:**

| YAML field | Pydantic model field | Default | Validator | Session |
|------------|----------------------|---------|-----------|---------|
| `order_manager.locate_suppression_seconds` | `OrderManagerConfig.locate_suppression_seconds` | 300 | `Field(default=300, ge=10, le=3600)` | S3a |
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig.long_only_sell_ceiling_enabled` | `true` (fail-closed) | `Field(default=True)` | S4a |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig.long_only_sell_ceiling_alert_on_violation` | `true` | `Field(default=True)` | S4a |
| (existing) `ibkr.bracket_oca_type` | `IBKRConfig.bracket_oca_type` | 1 | `Field(default=1, ge=0, le=1)` | S4b consumes — no schema change |

Regression checklist item: "New config fields verified against Pydantic model (no silently ignored keys); YAML field names match Pydantic field names; CI test loads `config/system_live.yaml` and asserts no unrecognized keys under `order_manager.*`."

---

**Test Strategy:**

- New tests by session (using protocol baseline ~5/new file + ~3/modified file + ~2/endpoint, NO 2× multiplier — this sprint creates no new infrastructure layer):
  - S1a: 0 (spike — no Pytest) — produces JSON artifact for S2a/S2b consumption
  - S1b: 0 (spike) — produces JSON artifact for S3a/S3b consumption
  - S2a: ~10 (`_trail_flatten` Path #1, edge cases E1.1–E1.8, AMD-2 modification regression)
  - S2b: ~8 (other Path #1 surfaces, `_resubmit_stop_with_retry` emergency path)
  - S3a: ~10 (locate-rejection fingerprint, suppression state, suppression-timeout fallback, edge cases E2.1–E2.7)
  - S3b: ~8 (4 SELL emit sites × 2 outcomes — suppressed and not-suppressed)
  - S4a: ~12 (parametrized SELL emit site enumeration × ceiling pass/fail; edge cases E4.1–E4.5)
  - S4b: ~6 (DEF-212 wiring, grep-guard for constant deletion, OCA-type lock-step preserved)
  - S5a: ~6 (Path #1 falsifiable validation)
  - S5b: ~9 (Path #2 + composite falsifiable validation)
- **Estimated total new pytest:** ~69 (range 60–80 with parametrized expansion; budget +85 to absorb parametrize multipliers per protocol §"Parametrized tests count per case, not per decorator").
- **Vitest delta:** 0 (no frontend changes).
- **DEC-328 tiering:** S1a pre-flight = full suite (`-n auto`); S1b–S5b pre-flights = scoped (`tests/execution/order_manager/` + `tests/integration/test_def204_round2_validation.py`); all close-outs = full suite; non-final reviews = scoped; final review (S5b) = full suite.
- **Final test count target:** 5,338–5,354 pytest (5,269 + 60–85), 913 Vitest unchanged.

---

**Runner Compatibility:**

- **Mode:** human-in-the-loop. CRITICAL safety + non-safe-during-trading. Operator presence at each session boundary required.
- **Parallelizable sessions:** S1a + S1b (different scripts, no codebase write conflicts, both read-only) — operator may run in parallel Claude.ai sessions if context permits. All implementation sessions (S2a/S2b/S3a/S3b/S4a/S4b/S5a/S5b) SEQUENTIAL — every one of them touches `argus/execution/order_manager.py`.
- **Estimated token budget:** ~10 sessions × ~150K tokens each ≈ 1.5M tokens total (excluding adversarial review + Tier 3 if escalated). Within Claude Code session budget for Opus.
- **Runner-specific escalation notes:** N/A (HiTL).

---

**Dependencies:**

- Sprint 31.91 SEALED at HEAD (verified — D14 sprint-close 2026-04-28).
- Sprint 31.915 SEALED at HEAD (verified — DEC-389 evaluation.db retention).
- Operator runs `scripts/ibkr_close_all_positions.py` daily until cessation criterion #5 satisfied (5 paper sessions clean post-Sprint-31.92 seal).
- Phase 0 cross-reference renumbering edits applied to `CLAUDE.md` + `docs/roadmap.md` — VERIFIED 2026-04-29.
- Spike outputs (S1a + S1b JSON artifacts) gate Phase D implementation prompts for S2a/S2b and S3a/S3b respectively.

---

**Escalation Criteria (Tier 3 review triggers):**

- Path #1 spike (S1a) reveals IBKR amend-stop-price latency is unbounded or non-deterministic → mechanism choice is non-trivial → Tier 3 review on mechanism selection BEFORE S2a impl prompt.
- Path #2 spike (S1b) reveals the locate-rejection error string is NOT stable across IBKR API versions → fingerprint-based detection is fragile → Tier 3 on detection strategy.
- AC4 ceiling implementation reveals architectural conflict with DEC-369 broker-confirmed reconciliation immunity (broker-confirmed positions don't have entry-fill provenance for `shares_total`) → Tier 3.
- Validation S5a or S5b produces ANY phantom short under any synthetic scenario → halt sprint, do not seal.
- Any session produces a structured close-out with `verdict: BLOCKED` → halt + Tier 3.
- Any session's full suite drops below 5,269 pytest baseline → halt + Tier 3.
- Adversarial Review (Phase C-1) produces ≥1 Critical finding → return to Phase A for revisions.

---

**Doc Updates Needed (post-sprint-close, populated at S5b close-out + D14 doc-sync):**

- `CLAUDE.md` — DEF-204 row marked RESOLVED; DEF-212 row marked RESOLVED (both via Sprint 31.92 / DEC-390); DEF-208 routing column updated if S4b's restraint defers fixture infrastructure (likely no change); active-sprint pointer updated to next horizon (Sprint 31B or Sprint 31.93).
- `docs/decision-log.md` — DEC-390 written below at sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0; Pattern A may apply if Tier 3 escalates mid-sprint).
- `docs/dec-index.md` — DEC-390 entry added.
- `docs/sprint-history.md` — Sprint 31.92 row added (date, tests, key DECs).
- `docs/roadmap.md` — Sprint 31.92 close-out narrative; cessation criterion #5 status update; next-sprint-up pointer.
- `docs/architecture.md` — §3.7 Order Manager updated for the locate-suppression dict + ceiling field; §3.7d may add a §"Long-Only SELL-Volume Ceiling" subsection.
- `docs/pre-live-transition-checklist.md` — verify `OrderManagerConfig.long_only_sell_ceiling_enabled` set to `true` for live (already default-true; informational).
- `docs/risk-register.md` — RSK-DEC-386-DOCSTRING bound NOT changed (Sprint 31.94's responsibility); add note that DEC-386's `~98%` claim was empirically falsified 2026-04-28 and structurally closed by DEC-390.
- `docs/process-evolution.md` — F.5 (TBD): DEC empirical-claim falsification → Tier 3 verdict revision. Captured at sprint-close for next campaign's RETRO-FOLD.

---

**Artifacts to Generate (Phase C):**

1. ✅ Design Summary (this document)
2. Sprint Spec
3. Specification by Contradiction
4. Session Breakdown (with Creates/Modifies/Integrates per session, scoring tables for all 10 sessions)
5. Sprint-Level Escalation Criteria
6. Sprint-Level Regression Checklist
7. Doc Update Checklist
8. **Adversarial Review Input Package** (this sprint warrants adversarial review per Phase A Step 8)

**Phase C-1 Adversarial Review Gate** halts here. Phase D (prompts + review context) follows post-revision.