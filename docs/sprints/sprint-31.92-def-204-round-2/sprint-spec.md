# Sprint 31.92: DEF-204 Round 2 — Trail-Stop / Bracket-Stop Race + Locate-Rejection Hold + DEF-212 Rider

## Goal

Close the two uncovered DEF-204 mechanism paths surfaced by the 2026-04-28 paper-session debrief — Path #1 (trail-stop / bracket-stop concurrent-trigger race; canonical trace BITU 13:36→13:41 producing 182-share phantom short) and Path #2 (locate-rejection-as-held-order retry storm; canonical trace PCT producing 3,837-share phantom short) — plus a structural long-only SELL-volume ceiling on `ManagedPosition` as defense-in-depth, plus the DEF-212 `_OCA_TYPE_BRACKET` constant-drift rider. This sprint resolves the residual ~2% of DEF-204's mechanism that DEC-386 did not cover (empirically falsified by the Apr 28 session producing 60 NEW phantom shorts post-DEC-386). CRITICAL safety, non-safe-during-trading, adversarial review required.

## Scope

### Deliverables

1. **Path #1 closure** — `_trail_flatten` and `_resubmit_stop_with_retry` emergency-flatten path coordinate with the bracket stop such that no concurrent-trigger race produces a SELL fill exceeding the position's long quantity. `_escalation_update_stop` receives the same treatment IFF spike S1a confirms it has the same race surface.
2. **Path #2 closure** — IBKR rejection error string `"contract is not available for short sale"` is detected as `_is_locate_rejection()` (held-pending-borrow), NOT as transient reject. Per-symbol suppression dict prevents subsequent SELL emissions for that symbol until either (a) IBKR's held order fills (suppression released by fill callback), (b) IBKR explicitly cancels the held order, or (c) suppression-timeout window expires (`locate_suppression_seconds`, default 300s) — at which point the path falls back to the existing `phantom_short_retry_blocked` CRITICAL alert.
3. **Long-only SELL-volume ceiling** — Every `ManagedPosition` carries a `cumulative_sold_shares` running sum (incremented in `on_fill` for SELL-side fills). Before `place_order(SELL)` at every emit site (5+), assert `cumulative_sold_shares + requested_qty ≤ shares_total`. Violations refuse the SELL, emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical")`, and log CRITICAL. Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`, fail-closed).
4. **DEF-212 rider** — `OrderManager.__init__` accepts `bracket_oca_type: int` parameter; `argus/main.py` construction call site passes `config.ibkr.bracket_oca_type`; the four occurrences of `_OCA_TYPE_BRACKET` module constant in `argus/execution/order_manager.py` become `self._bracket_oca_type`; the module constant is deleted. Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) DEFERRED to Sprint 31.93.
5. **Falsifiable end-to-end validation** — Synthetic SimulatedBroker scenarios for Path #1 (concurrent-trigger race) and Path #2 (locate-rejection storm with held-order release) produce ZERO phantom shorts; composite scenario (all 5+ SELL emit sites under load + ceiling enabled) is asserted via Pytest integration tests. Validation scripts produce JSON artifacts under `scripts/spike-results/sprint-31.92-validation-{path1,path2}.json`. (No standalone `*-composite.json` artifact; composite validation is in-suite.)
6. **DEC-390 materialization** — Four-layer DEC entry mirroring DEC-385/386's layered-decomposition pattern, written below at sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0; Pattern A applies if Tier 3 escalates mid-sprint).

### Acceptance Criteria

1. **Path #1 closure (Deliverable 1):**
   - **AC1.1 (testable):** Synthetic concurrent-trigger scenario via `SimulatedBroker` test fixture — long position, bracket stop at $14.39, trail stop tripped at $14.44 in same tick as bracket trigger price — produces total SELL fills `≤ position.shares_total`. Test asserted at S5a; the BITU 13:41 trace structurally replicated.
   - **AC1.2 (testable):** `_trail_flatten` no longer issues a market SELL while the bracket stop is in `Submitted`/`PreSubmitted` state without first cancelling-and-awaiting that bracket stop's cancellation propagation (or, if S1a spike selects amend-stop-price OPTION (a), without first amending the bracket stop's price). Asserted by mocking `IBKRBroker.cancel_all_orders` (or `amend_order`) and verifying call ordering at S2a.
   - **AC1.3 (testable):** `_resubmit_stop_with_retry`'s emergency-flatten branch (DEC-372 retry-cap exhausted at line ~976) applies the same Path #1 mechanism. Asserted at S2b.
   - **AC1.4 (preserved):** AMD-8 guard ("complete no-op if `_flatten_pending` already set") preserved verbatim. AMD-4 guard ("no-op if `shares_remaining ≤ 0`") preserved verbatim.
   - **AC1.5 (intentional modification):** AMD-2 invariant ("sell before cancel") in `_trail_flatten` is INTENTIONALLY MODIFIED if S1a spike selects OPTION (b) cancel-and-await. The modification is explicitly logged in DEC-390 with rationale; the existing AMD-2 regression test is updated, NOT removed.

2. **Path #2 closure (Deliverable 2):**
   - **AC2.1 (testable):** New helper `_is_locate_rejection(error: BaseException) -> bool` in `argus/execution/ibkr_broker.py` returns True iff `str(error).lower()` contains the substring fingerprint `"contract is not available for short sale"` (case-insensitive). Asserted at S3a with both positive and negative cases.
   - **AC2.2 (testable):** `OrderManager._locate_suppressed_until: dict[str, float]` symbol-keyed dict; suppression check `_is_locate_suppressed(symbol, now) -> bool` returns True iff `symbol in dict and dict[symbol] > now`. Asserted at S3a.
   - **AC2.3 (testable):** When `_is_locate_rejection(exc)` matches in `place_order` exception handler at any of the 4 SELL emit sites, suppression set to `now + locate_suppression_seconds`; INFO log emitted; NO retry; NO CRITICAL alert. Asserted parametrically across all 4 sites at S3b.
   - **AC2.4 (testable):** Subsequent SELL emit attempts at any site for a suppressed symbol within the window: skip + INFO log + return early; NO `place_order` call. Asserted parametrically at S3b.
   - **AC2.5 (testable):** Suppression-timeout fallback — when suppression expires WITHOUT a fill callback or explicit IBKR cancel, the next SELL emit at that symbol publishes `SystemAlertEvent(alert_type="phantom_short_retry_blocked", ...)` per DEC-385 (re-uses existing alert type, NOT a new one) and clears suppression. Asserted at S3b.
   - **AC2.6 (testable):** Fill callback for a previously-suppressed symbol clears suppression. Asserted at S3a.
   - **AC2.7 (preserved):** DEF-158 retry 3-branch side-check (BUY → resubmit / SELL → alert+halt / unknown → halt) preserved verbatim — Path #2 adds a NEW upstream detection at `place_order` exception, NOT a 4th branch.

3. **Long-only SELL-volume ceiling (Deliverable 3):**
   - **AC3.1 (testable):** New field `ManagedPosition.cumulative_sold_shares: int = 0`. Incremented in `on_fill` for every SELL-side fill (T1, T2, bracket stop, trail-flatten, escalation-flatten, retry-flatten, EOD-flatten, locate-released-flatten). Asserted at S4a.
   - **AC3.2 (testable):** `_check_sell_ceiling(position, requested_qty) -> bool` returns False iff `position.cumulative_sold_shares + requested_qty > position.shares_total`. Called at every SELL emit site BEFORE `place_order(SELL)`. Asserted parametrically across all 5+ SELL emit sites at S4a.
   - **AC3.3 (testable):** Ceiling violation: refuse the SELL, do NOT add to `_flatten_pending`, emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical", metadata={...})`, log CRITICAL. Asserted at S4a.
   - **AC3.4 (testable):** Ceiling is per-`ManagedPosition`, NOT per-symbol. Multiple sequential `ManagedPosition` records for the same symbol within a session each have independent ceilings. Asserted at S4a.
   - **AC3.5 (testable):** `reconstruct_from_broker`-derived positions (DEC-369 broker-confirmed) initialize `cumulative_sold_shares = 0` and `shares_total = abs(broker_position.shares)`. Asserted at S4a.
   - **AC3.6 (config-gated):** Config flag `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`); when `false`, ceiling check returns True unconditionally and no metric is incremented (zero-overhead disable path). Asserted at S4a.
   - **AC3.7 (alert observability):** New `POLICY_TABLE` entry in `argus/core/alert_auto_resolution.py` for `sell_ceiling_violation` alert type — recommend `operator_ack_required=True`, `auto_resolution_predicate=None` (manual-ack only). Asserted by AST policy-table exhaustiveness regression guard `tests/api/test_policy_table_exhaustiveness.py`.

4. **DEF-212 rider (Deliverable 4):**
   - **AC4.1 (testable):** `OrderManager.__init__` accepts `bracket_oca_type: int` keyword argument, stored as `self._bracket_oca_type`. Default value preserved at 1 only via `IBKRConfig.bracket_oca_type`'s Pydantic default; no module constant fallback. Asserted at S4b.
   - **AC4.2 (testable):** All 4 occurrences of `_OCA_TYPE_BRACKET` module constant (lines ~3212, ~3601, ~3714, ~3822) replaced by `self._bracket_oca_type`. Module constant `_OCA_TYPE_BRACKET = 1` at line ~105 deleted. Asserted at S4b.
   - **AC4.3 (testable):** Grep regression guard: `tests/regression/test_no_oca_type_bracket_constant.py` greps `argus/execution/order_manager.py` for `_OCA_TYPE_BRACKET` and asserts zero matches. Fails noisy if the constant ever returns. Asserted at S4b.
   - **AC4.4 (testable):** Operator flips `IBKRConfig.bracket_oca_type` to 0 (RESTART-REQUIRED rollback) → bracket children get `ocaType=0` AND standalone-SELL OCA threading sets `ocaType=0` consistently (no divergence). Asserted at S4b with parametrized test over `bracket_oca_type ∈ {0, 1}` × all 4 OCA-thread sites.
   - **AC4.5 (preserved):** All Sprint 31.91 DEC-386 OCA invariants (S0/S1a/S1b/S1c) preserved byte-for-byte. Existing tests pass without modification.

5. **Falsifiable end-to-end validation (Deliverable 5):**
   - **AC5.1:** `scripts/validate_def204_round2_path1.py` produces `scripts/spike-results/sprint-31.92-validation-path1.json` with `path1_safe: true` AND `phantom_shorts_observed: 0` AND `total_sold_le_total_bought: true`. Run at S5a; output committed to repo as falsifiable evidence per regression invariant 22 (analog of DEC-386's `PATH_1_SAFE` spike artifact, valid ≤30 days).
   - **AC5.2:** `scripts/validate_def204_round2_path2.py` produces `scripts/spike-results/sprint-31.92-validation-path2.json` with `path2_suppression_works: true` AND `sell_emits_per_symbol_within_window ≤ 1` AND `held_order_fill_propagates: true`. Run at S5b.
   - **AC5.3:** Composite validation implemented as Pytest integration tests in `tests/integration/test_def204_round2_validation.py` (test names `test_composite_validation_zero_phantom_shorts_under_load` and `test_composite_validation_ceiling_blocks_under_adversarial_load`) — assertions: under benign synthetic-broker load, `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`; under adversarial synthetic-broker load (forced over-flatten attempts at all 5+ SELL emit sites), `ceiling_violations_correctly_blocked ≥ 1`. Run at S5b. **Amendment rationale (Phase C session-breakdown):** the standalone composite script was demoted to integration tests for compaction-risk discipline; Pytest-based assurance is functionally equivalent and avoids a 4th validation script with its own JSON-schema discipline. The two single-path validation scripts (`validate_def204_round2_path1.py` and `validate_def204_round2_path2.py`) and their JSON artifacts ARE preserved (AC5.1 and AC5.2 unchanged) because they serve as 30-day-freshness operational artifacts per regression invariant 18.
   - **AC5.4:** All three validation artifacts committed to `main` BEFORE sprint-close (D14 doc-sync). Sprint cannot be sealed without these.

6. **DEC-390 materialization (Deliverable 6):**
   - **AC6.1:** DEC-390 written below in `docs/decision-log.md` at sprint-close, four-layer structure (L1 Path #1 mechanism / L2 Path #2 fingerprint+suppression / L3 SELL-volume ceiling / L4 DEF-212 wiring), Cross-References to DEC-385, DEC-386, DEC-388, DEF-204, DEF-212, Apr 28 paper-session debrief, S1a + S1b spike artifacts, S5a + S5b validation artifacts.
   - **AC6.2:** `docs/dec-index.md` updated.
   - **AC6.3:** Sprint 31.91's empirically-falsified `~98%` claim acknowledged in DEC-390 Context section; DEC-386 preserved unchanged (per Phase A decision — leave-as-historical).

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Path #1 cancel-and-await latency overhead per trail-flatten | ≤ 200ms p95 | S1a spike measures on paper IBKR; S5a fixture asserts under simulated propagation |
| `_check_sell_ceiling` per-call overhead | ≤ 10µs | S4a benchmark — `pytest --benchmark` on hot path |
| `_is_locate_rejection` per-call overhead | ≤ 5µs | S3a benchmark — string-lowercase + substring; trivial |
| `_locate_suppressed_until` dict lookup overhead | ≤ 5µs | S3b benchmark — single dict.get + float comparison |
| Full-suite test runtime regression | ≤ +30s vs baseline 5,269 pytest | DEC-328 final-review full-suite measurement |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `order_manager.locate_suppression_seconds` | `OrderManagerConfig` | `locate_suppression_seconds` | `300` (`Field(default=300, ge=10, le=3600)`) |
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig` | `long_only_sell_ceiling_enabled` | `True` (fail-closed) |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig` | `long_only_sell_ceiling_alert_on_violation` | `True` |
| `ibkr.bracket_oca_type` | `IBKRConfig` | `bracket_oca_type` | `1` — **EXISTING (no schema change); S4b consumes** |

Regression checklist item: "New `OrderManagerConfig` fields verified against Pydantic model — YAML field names match Pydantic field names exactly; CI test loads `config/system_live.yaml` and asserts no unrecognized keys under `order_manager.*` (test added at S3a or S4a, whichever lands first)."

## Dependencies

- Sprint 31.91 SEALED at HEAD (verified D14 sprint-close 2026-04-28). DEC-385 + DEC-386 + DEC-388 materialized.
- Sprint 31.915 SEALED at HEAD (verified — DEC-389 evaluation.db retention + VACUUM-on-startup).
- Phase 0 cross-reference renumbering edits applied to `CLAUDE.md` + `docs/roadmap.md` (verified 2026-04-29 via repo pull).
- Operator runs `scripts/ibkr_close_all_positions.py` daily until cessation criterion #5 satisfied (5 paper sessions clean post-Sprint-31.92 seal). Operator confirmed Apr 28 boot-time 43-short residue was missed-run human error, NOT a script defect.
- Spike outputs (S1a + S1b JSON artifacts) gate Phase D implementation prompts for S2a/S2b and S3a/S3b respectively. The implementation prompts are NOT generated until spike artifacts land and operator approves the chosen mechanism.
- Paper IBKR Gateway accessible (account U24619949) for S1a + S1b spike measurements. Spike sessions are non-safe-during-trading; run during pre-market or after-hours.

## Relevant Decisions

- **DEC-386 (Sprint 31.91 Tier 3 #1, 2026-04-27)** — 4-layer OCA-Group Threading + Broker-Only Safety. Closes ~98% of DEF-204 mechanism via OCA-cancellation enforcement at IBKR. **Empirically falsified 2026-04-28** (60 NEW phantom shorts post-DEC-386, debrief at `docs/debriefs/2026-04-28-paper-session-debrief.md`). DEC-386 preserved unchanged; DEC-390 closes the residual ~2% structurally. Constrains Sprint 31.92: S0/S1a/S1b/S1c surfaces preserved byte-for-byte; existing `# OCA-EXEMPT:` exemption mechanism re-used; existing `_is_oca_already_filled_error` re-used (NOT relocated this sprint).
- **DEC-385 (Sprint 31.91, 2026-04-02 → 2026-04-28)** — 6-layer Side-Aware Reconciliation Contract. The `phantom_short_retry_blocked` alert path (used by DEF-158 retry side-check) is re-used by Path #2's suppression-timeout fallback. Constrains Sprint 31.92: DEF-158's 3-branch side-check (BUY/SELL/unknown) preserved verbatim; Path #2 adds NEW upstream detection at `place_order` exception, not a 4th branch.
- **DEC-388 (Sprint 31.91, 2026-04-28)** — Alert Observability Architecture. New `sell_ceiling_violation` alert type added to `POLICY_TABLE` per AC3.7. Existing `phantom_short_retry_blocked` re-used per AC2.5. Constrains Sprint 31.92: must update `POLICY_TABLE` and AST exhaustiveness regression guard.
- **DEC-372 (Sprint 27.95)** — Stop Resubmission Cap with Exponential Backoff. The emergency-flatten branch in `_resubmit_stop_with_retry` (where retry cap is exhausted) is one of Path #1's surfaces. DEC-372's cap mechanism preserved; AC1.3 adds the cancel-and-await before the emergency SELL.
- **DEC-369 (Sprint 27.95)** — Broker-Confirmed Reconciliation. AC3.5 must compose with broker-confirmed positions: `cumulative_sold_shares = 0` initialization is correct because broker-confirmed positions enter ARGUS's tracking AFTER the broker fill that created them.
- **DEC-364 (Sprint 27.95)** — `cancel_all_orders()` no-args ABC contract. Path #1 OPTION (b) cancel-and-await uses DEC-386 S0's `cancel_all_orders(symbol, await_propagation=True)` extended signature. DEC-364's no-args contract preserved.
- **DEC-345 (Sprint 27.7)** — Separate-DB pattern. `sell_ceiling_violation` alerts persist via existing `data/operations.db` infrastructure (DEC-388 L3); no new DB.
- **DEC-328 (Sprint 23.5)** — Test suite tiering. Applied: S1a pre-flight = full suite; S1b–S5b pre-flights = scoped; all close-outs = full suite; non-final reviews = scoped; final review = full suite.
- **DEC-122 (Sprint 8)** — Per-signal time stops. The PCT canonical Path #2 trace fired its first SELL via the time-stop path; AC2.3 + AC2.4 protect that path.
- **DEC-117 (Sprint 7)** — Atomic bracket order placement. AC4.5 preserves this byte-for-byte.

## Relevant Risks

- **RSK-DEC-386-DOCSTRING (Sprint 31.91)** — Time-bounded contract on `reconstruct_from_broker()` STARTUP-ONLY docstring; bound by Sprint 31.94. Sprint 31.92 does NOT modify this surface (Sprint 31.94's responsibility per Phase 0 renumbering).
- **NEW RSK-DEC-390-AMEND (proposed):** If S1a spike selects Path #1 OPTION (a) amend-stop-price (not the prior-recommended cancel-and-await), the AMD-2 invariant in `_trail_flatten` ("sell before cancel") is preserved, but a NEW invariant ("amend before sell") is introduced. The amend-stop-price path depends on IBKR's `modifyOrder` semantics being deterministic at sub-50ms — if a future IBKR API change introduces non-determinism, the mechanism degrades silently. Mitigation: regression guard at S2a asserts mock `IBKRBroker.modify_order` was called before `place_order(SELL)`; OPS-LIVE-OPS doc paragraph documents the IBKR-API-version assumption.
- **NEW RSK-DEC-390-FINGERPRINT (proposed):** `_is_locate_rejection()` substring fingerprint depends on IBKR's exact rejection error string `"contract is not available for short sale"`. If IBKR changes this string in a future API update, the detection silently fails (locate-rejections fall through to generic exception → CRITICAL log via existing path → debugging cycle). Mitigation: S1b spike captures exact current string in JSON artifact; S5b validation re-runs against live paper IBKR and fails-closed if string drifts; quarterly re-validation flag in `docs/risk-register.md`.
- **NEW RSK-CEILING-FALSE-POSITIVE (proposed):** If a broker fill callback arrives out-of-order or partial-fill granularity differs between SimulatedBroker and IBKR (e.g., 100-share fill arrives as 50+50 in two callbacks), `cumulative_sold_shares` could be off-by-one in transient state. Mitigation: AC3.1 increments AT confirmed fill, not at order placement; partial-fill aggregation in `on_fill` already handles this for T1/T2 paths. Validation: parametrize S5b composite test with partial-fill scenarios.
- **NEW RSK-SUPPRESSION-LEAK (proposed):** `_locate_suppressed_until` dict accumulates symbol entries; if symbols suppress without ever clearing (timeout never fires because no subsequent SELL emit), dict grows unbounded. Mitigation: suppression-timeout fallback (AC2.5) explicitly clears the dict entry on alert publication; periodic GC sweep in OrderManager's housekeeping loop (cleared at EOD via existing teardown). Validation: S5b stress test with 100+ suppressed symbols asserts dict cleared at session-end.
- **RSK-022 (Sprint 21.6)** — IBKR Gateway nightly resets. Sprint 31.92 does NOT introduce new dependencies on Gateway uptime; Path #2's locate-rejection detection IS Gateway-uptime-independent (the rejection arrives via the same `ib_async` callback path used today).

## Hypothesis Prescription

This sprint's first two sessions (S1a + S1b) are diagnostic phases. The symptoms (Path #1 over-flatten, Path #2 retry storm) are reproducible from the Apr 28 trace data, but the spec author's primary hypothesis for Path #1's correct mechanism is NOT yet conclusively validated — only the cancel-and-await direction is theoretically derivable from DEC-386's existing infrastructure; OPTION (a) amend-stop-price has open empirical questions about IBKR latency. Path #2's fingerprint stability is also empirically unresolved.

| ID | Hypothesis | Confirms-if | Rules-out-if | Spec-prescribed fix shape |
|----|-----------|-------------|--------------|---------------------------|
| H1 (Path #1) | OPTION (b) cancel-and-await is the correct mechanism: cancelling the bracket stop with `await_propagation=True` BEFORE placing the trail-stop SELL preserves correctness and accepts a bounded 50–200ms unprotected gap as the cost. | S1a spike measures `cancel_all_orders(symbol, await_propagation=True)` round-trip latency on paper IBKR ≤ 200ms p95 over ≥50 trials. | S1a measures p95 > 500ms OR observes non-deterministic propagation (some trials never converge). | Cancel-and-await before SELL in `_trail_flatten`, `_resubmit_stop_with_retry` emergency path, and (conditional on IBKR amend semantics) `_escalation_update_stop`. AMD-2 invariant intentionally modified. |
| H2 (Path #1) | OPTION (a) amend-stop-price is the correct mechanism: trail stop amends the bracket stop's price via `modifyOrder` rather than placing a new market SELL, eliminating the second-SELL race entirely. | S1a measures `modifyOrder` round-trip latency ≤ 50ms p95 AND amend semantics are deterministic across ≥50 trials. | S1a observes amend rejection rates >5% OR amend doesn't actually update the IBKR-side bracket stop in some trials. | Amend bracket stop's `auxPrice` to trail-stop price; remove the trail-flatten market SELL emission. AMD-2 invariant preserved. |
| H3 (Path #1) | OPTION (c) recon-trusts-marker — accept the over-flatten as inevitable but mark `redundant_exit_observed = True` (DEC-386 S1b's existing field) so reconciliation classifies the resulting short as SAFE rather than phantom. | (Not validated in S1a — REJECTED at Phase A: requires `ManagedPosition.redundant_exit_observed` persistence which DEC-386 deferred to Sprint 35+ Learning Loop V2.) | (Implicit — already ruled out at Phase A.) | N/A — REJECTED. Listed for completeness in DEC-390 Context section. |
| H4 (Path #1) | OPTION (d) hybrid — combine (a) amend with (b) cancel-and-await as fallback when amend fails. | S1a observes amend success rate 70–95%. | S1a observes amend success rate ≥99% (use H2 alone) OR ≤50% (use H1 alone). | Two-path implementation: amend first, fall back to cancel-and-await on amend rejection. Adds complexity; only chosen if H2 alone is unreliable AND H1 alone is too slow. |
| H5 (Path #2) | The locate-rejection error string `"contract is not available for short sale"` is stable in current `ib_async` API and matches the substring exactly. | S1b's manual reproduction (force a SELL on a known hard-to-borrow stock during paper hours) captures the exact string AND it matches the debrief's literal text. | S1b captures a different string OR multiple strings depending on conditions. | Substring fingerprint helper as specified. If RULES-OUT, fingerprint becomes a regex or a list of substrings; impl prompt updated at S3a. |
| H6 (Path #2) | Suppression window of 300s (5 min) is long enough to capture IBKR's typical hold-pending-borrow release window. | S1b observes hold-pending-borrow median release time < 60s and p99 < 240s across ≥10 trials. | S1b observes p99 release time > 600s OR releases never observed (test stocks not actually held, only hard-rejected). | If H6 RULED OUT — if releases >300s observed, raise default to 600s; if releases never observed in spike, the suppression-timeout fallback is the dominant code path and AC2.5 escalation behavior is what matters most. |

**Required halt-or-proceed gate language** (verbatim into S2a + S2b + S3a + S3b implementation prompts, per protocol §"Hypothesis Prescription"):

> If the diagnostic confirms H1, proceed to Phase B with the H1 fix shape.
> If H2/H4 (etc.) are confirmed, adapt the fix shape to match the confirmed
> mechanism. If findings are inconclusive or fall outside the enumerated
> hypotheses, HALT and write the diagnostic findings file with status
> INCONCLUSIVE; surface to operator before proceeding. Do NOT ship a Phase B
> fix that doesn't address the Phase A finding.

The escape-hatch language is load-bearing. The implementing session is explicitly authorized to deviate from the spec-prescribed fix shape when the diagnostic finding warrants it, provided the deviation is called out in the close-out's "Judgment Calls" section with cross-reference to the spike artifact under `scripts/spike-results/spike-def204-round2-{path1,path2}-results.json`.

## Session Count Estimate

**10 sessions** estimated, decomposed into 2 spike sessions (S1a + S1b — no production code changes; output JSON artifacts) + 8 implementation/validation sessions (S2a + S2b + S3a + S3b + S4a + S4b + S5a + S5b). Rationale per Phase A Step 5 compaction risk assessment: every session's pre-split score landed in the 14+ range (HIGH or CRITICAL) primarily because `argus/execution/order_manager.py` is 4,421 lines and dominates pre-flight reads. The 10-session breakdown keeps each post-split session ≤ 12 points. No frontend visual review (zero UI changes) — no contingency budget for visual-review fixes.

Adversarial review (Phase C-1) may surface revisions that re-shape S2a/S2b or S3a/S3b; if scope expands, session count grows; if scope contracts (e.g., S2b folds into S2a if `_escalation_update_stop` is determined out-of-scope by spike S1a), session count shrinks.