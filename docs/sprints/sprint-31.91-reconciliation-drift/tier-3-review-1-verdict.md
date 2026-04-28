# Sprint 31.91 — Tier 3 Architectural Review #1 (Verdict)

> **Verdict:** PROCEED
> **Date:** 2026-04-27
> **Scope:** Combined diff of Sessions 0 + 1a + 1b + 1c (OCA architecture track).
> **Anchor commit:** `bf7b869` on `main` (`docs(sprint-31.91): session 1c Tier 2 review verdict (CLEAR)`).
> **Reviewer:** Claude.ai (planning instance); review conducted against `protocols/tier-3-review.md` in claude-workflow metarepo at workflow-version 1.0.0.
> **Sessions reviewed:** 0 (`9b7246c`), 1a (`b25b419`), 1b (`6009397`), 1c (`49beae2`).

## Verdict summary

The 4-layer OCA architecture across Sessions 0+1a+1b+1c is architecturally sound and ships safely. All upstream invariants (DEC-117 atomic-bracket, DEC-364 cancel_all_orders no-args, DEC-369 broker-confirmed, DEC-372 stop retry, DEF-199 A1 fix) are preserved verbatim. The Phase A spike (`scripts/spike_ibkr_oca_late_add.py`, result `PATH_1_SAFE` 2026-04-25) is fresh per regression invariant 22 (≤30 days).

The architecture closes ~98% of DEF-204's blast radius per IMPROMPTU-11's mass-balance attribution. The remaining ~2% (secondary detection-blindness mechanisms in reconcile / DEF-158 retry path / EOD Pass 2) is closed by Sessions 2a–2d + 3, which remain in flight per the original sprint plan.

DEC-386 (OCA-Group Threading + Broker-Only Safety) is written to `decision-log.md` documenting the architectural decision and its alternatives.

## What was reviewed

The combined diff `9b7246c^..bf7b869` was inspected against the four review dimensions in `protocols/tier-3-review.md`:

1. **Architectural soundness:** the 4-layer stack (API contract → bracket OCA → standalone-SELL OCA → broker-only safety) is monotonically additive — each session strictly adds capability without removing any. The regression checklist's invariant 14 monotonic-safety matrix verifies this row-by-row. No layer's safety property is contingent on a layer above it being absent.
2. **Upstream invariant preservation:** DEC-117 atomic-bracket invariant verified (rollback still fires on Error 201, only log severity differs based on the OCA-filled distinguishing helper). DEC-364 no-args contract verified (`cancel_all_orders()` with no args has identical behavior pre- and post-Session-0). DEC-369 broker-confirmed-immunity verified (no path now flattens or amplifies a broker-confirmed position without explicit operator override). DEC-372 stop-retry caps verified (the Session 1b OCA threading on `_resubmit_stop_with_retry` does not change retry semantics, only adds an OCA group ID). DEF-199 A1 fix verified (the IMPROMPTU-04 EOD Pass 2 refusal logic is at a different code path entirely; lines 1670-1750 of `order_manager.py` have zero edits in the combined diff).
3. **Falsifiable validation:** Phase A spike result `PATH_1_SAFE` (`scripts/spike-results/spike-results-2026-04-25.json`) is the falsifiable empirical claim that IBKR enforces ocaType=1 atomic cancellation pre-submit. The spike script is registered in `live-operations.md` for re-run before any IBKR/ib_async upgrade and before live transition. CI green throughout all 4 sessions; 4 Tier 2 reviews CLEAR.
4. **Failure-mode trade-offs documented:** Session 1c's leaked-long failure mode (cancel-timeout abort) is the documented trade-off vs. unbounded phantom-short risk. The asymmetric-risk argument (bounded long preferable to unbounded short on runaway upside) is sound. Operator response is documented in `live-operations.md`.

## Three focus areas — all ACCEPTABLE with caveats

### Focus Area 1 — Leaked-long failure mode visibility

Session 1c emits `SystemAlertEvent(alert_type="cancel_propagation_timeout")` when the 2s cancel-propagation budget is exceeded. The asymmetric-risk reasoning (bounded leaked-long vs unbounded phantom-short) is sound. **Caveat:** the alert is currently visible only in logs — no Command Center surface, no banner, no toast. Until Session 5a.1 (HealthMonitor consumer) lands, an operator not actively tailing logs would not see the alert. **Resolution:** captured in `pre-live-transition-checklist.md` as a HARD live-trading prerequisite ("Session 5a.1 must land before live transition") — not a soft preference.

### Focus Area 2 — `reconstruct_from_broker` STARTUP-ONLY contract

Session 1c added a contractual STARTUP-ONLY docstring rather than a runtime gate, because the do-not-modify list for Session 1c forbade modifying `argus/main.py:1081` (the only call site). The docstring documents that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — without it, the unconditional `cancel_all_orders` would WIPE OUT today's working bracket children at any mid-session reconnect. **Resolution:** filed as DEF-211 (Sprint 31.93 sprint-gating). Time-bounded: ARGUS does not currently support mid-session reconnect at all, so the docstring is sufficient until Sprint 31.93 lands the runtime gate. RSK-DEC-386-DOCSTRING tracks the time-bounded contract.

### Focus Area 3 — `# OCA-EXEMPT:` marker discipline

Session 1b's grep regression guard (`tests/_regression_guards/test_oca_threading_completeness.py::test_no_sell_without_oca_when_managed_position_has_oca`) enforces OCA-threading discipline on standalone SELLs. Legitimate broker-only paths (which have no `ManagedPosition` to thread) are exempted via the canonical `# OCA-EXEMPT: <reason>` comment. **Headroom:** the grep guard's regex has 22+ lines of margin (Session 1c uses 6 OCA-EXEMPT markers; the grep accommodates many more). Long-horizon: a structural-typing alternative (`BrokerOnlySell` marker class) was considered and correctly deferred — it would require type changes across `Broker.place_order`, `OrderManager`, and every test that constructs an `Order`. The grep + comment is the surgical choice for this sprint scope. Long-horizon revisit deferred to post-Sprint-35.

## Six additional concerns surfaced (A–F)

### Concern A — Module abstraction leakage of `_is_oca_already_filled_error`

The defensive helper `_is_oca_already_filled_error` lives at module scope in `argus/execution/ibkr_broker.py` but is consumed by `argus/execution/order_manager.py` (line 59, import). The helper conceptually belongs to the broker abstraction layer (it distinguishes IBKR error codes), not to the IBKR-specific implementation.

**Resolution:** Sprint 31.92 component-ownership refactor will relocate the helper from `ibkr_broker.py` to `broker.py` (the ABC module) and rename to drop the leading underscore (it's now public to the broker abstraction). Filed implicitly as a sibling follow-up to DEF-212 in CLAUDE.md.

### Concern B — `_OCA_TYPE_BRACKET = 1` constant drift risk

Session 1b introduced `_OCA_TYPE_BRACKET = 1` as a module constant in `argus/execution/order_manager.py:82` because Session 1b's do-not-modify list forbade extending `OrderManager.__init__` at the `argus/main.py` call site. The constant mirrors `IBKRConfig.bracket_oca_type` (default 1). Lock-step is enforced only by docstring + planned `live-operations.md` paragraph.

**Resolution:** filed as DEF-212 in CLAUDE.md. Sprint 31.92 component-ownership refactor will wire `IBKRConfig` (or just the `bracket_oca_type` field) into `OrderManager.__init__` and replace the module constant with an instance attribute. Lock-step constraint documented in `live-operations.md` until then.

### Concern C — `SystemAlertEvent.metadata` schema gap

The current `SystemAlertEvent` schema at `argus/core/events.py:405` has no structured `metadata` field. Session 1c's `_emit_cancel_propagation_timeout_alert` helper encodes `symbol`, `shares`, `stage` into the formatted message string. Session 5a.1's existing impl prompt (lines 123 and 153) already references `event.metadata` on the assumption that the field will be added — but no session in the sprint plan currently scopes that work. The HealthMonitor consumer + Sessions 5b's auto-resolution policy + 5c's frontend banner all benefit from typed metadata access.

**Resolution:** filed as DEF-213 in CLAUDE.md. Session 5a.1 impl prompt amended (Patch 9 of this doc-sync) with Pre-Flight Check 7 (verify field existence) and conditional Requirement 0 (schema extension + atomic emitter migration of existing sites: Databento dead-feed + 3 Session 1c invocations + emitters added by Sessions 2b.1/2b.2/2c.1/2d/3 before 5a.1 lands).

### Concern D — `ManagedPosition.redundant_exit_observed` persistence

Session 1b added `ManagedPosition.redundant_exit_observed: bool` to mark SELLs that short-circuited because another OCA member fired first. The field is set in memory but not persisted to historical record stores (`analytics/debrief_export.py`, `quality_history` writer in `intelligence/quality_engine.py`). Future Learning Loop V2 promotion/demotion decisions need to attribute exits by mechanism, not just by direction.

**Resolution:** folded into existing DEF-209 (the SbC-reserved field-preservation defer). DEF-209's scope text in CLAUDE.md is extended to cover both `Position.side` AND `ManagedPosition.redundant_exit_observed`. Sprint 35+ horizon (Learning Loop V2 prerequisite); not a current bug because in-memory fields work today.

### Concern E — Test fixture drift risk across 12 files

12+ test files under `tests/execution/` construct `MagicMock()` brokers with hand-rolled `place_order`/`cancel_order`/`cancel_all_orders` mocks. As `Broker` ABC evolves, these per-file mocks risk drifting out of sync with the ABC.

**Resolution:** test-hygiene backlog item; not filed as a DEF (no safety implications, pure mechanical refactor cost). Suggested: extract a `make_broker_mock()` helper to `tests/execution/conftest.py` and migrate existing files; ~2 hours of mechanical work. Captured here for awareness only.

### Concern F — Test 4 `get_positions` side-effect chain brittleness

The Session 1c test `test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short` uses `mock_broker.get_positions.side_effect = [[long_zombie], []]` (a 2-element list). If a future refactor adds another `get_positions` call in `eod_flatten`, the test would fail with `StopIteration` rather than producing a meaningful diagnostic.

**Resolution:** test-hygiene backlog; not filed as a DEF. Suggested: replace the side-effect list with a callable that handles arbitrary call counts; ~10 minutes. Captured here for awareness only.

## Inherited follow-ups

- **Sprint 31.92** (component-ownership refactor): inherits Concern A (helper relocation) + DEF-212 (`IBKRConfig` wiring into `OrderManager`).
- **Sprint 31.93** (reconnect-recovery): inherits DEF-211 — EXTENDED SCOPE per Apr 27 paper-session debrief Findings 3 + 4 (folded in during Tier 3 doc-sync). Three coupled deliverables: (D1) `ReconstructContext` enum + parameter threading; (D2) IMPROMPTU-04 startup invariant gate refactor; (D3) boot-time adoption-vs-flatten policy decision. All three must land together; Sprint 31.93 cannot be sealed without all three. Once landed, retire today's operator daily-flatten requirement.
- **Sprint 31.91 Session 5a.1** (alert observability backend half-1): inherits TWO sprint-gating items: (a) DEF-213 (`SystemAlertEvent.metadata` schema extension + atomic emitter migration; Tier 3 Concern C); (b) DEF-214 (EOD verification timing race + side-aware classification + distinct alert paths; Apr 27 debrief Finding 1). Both items folded into 5a.1 impl prompt as Requirement 0 and Requirement 0.5 respectively (this doc-sync's Patch 9).
- **Sprint 35+** (Learning Loop V2): inherits DEF-209 extended scope (`Position.side` + `ManagedPosition.redundant_exit_observed` persistence in historical-record writers).
- **Deferred with sharp revisit trigger:** DEF-215 (reconciliation per-cycle log spam, Apr 27 debrief Finding 2) — revisit only if observed lasting ≥10 consecutive cycles AFTER Sprint 31.91 has been sealed for ≥5 paper sessions.
- **Test-hygiene backlog:** Concerns E and F (broker-mock fixture consolidation + Test 4 brittleness).

## Apr 27 paper-session debrief inputs folded into this Tier 3 doc-sync

After the OCA architecture review verdict was reached, the Apr 27 paper-session debrief (debrief at `docs/debriefs/2026-04-27-paper-session-debrief.md`) was completed. **The Apr 27 paper session ran on a pre-`bf7b869` commit — Sessions 0/1a/1b/1c had not yet landed.** Therefore Apr 27's 43-symbol short cascade is another DEF-204 manifestation on the same pre-fix code that produced the Apr 22-24 cascades, NOT a test of OCA architecture coverage. Apr 27 does not validate or invalidate Sessions 0-1c; the first OCA-effective paper session will be the next post-`bf7b869` session (Apr 28 or later).

What Apr 27 DOES contribute is **four follow-on findings unrelated to OCA architecture coverage** that the debrief identified by reviewing post-cascade behavior:

- **Finding 1 — EOD verification timing race + side-blind classification.** Filed as DEF-214; routed to Sprint 31.91 Session 5a.1 (preferred) over the original handoff routing of Session 4. Tier 3 chose 5a.1 over 4 because Session 4 is third-pass-sealed (its falsifiable mass-balance claim should not be diluted with live-broker-poll work) and because the alert-observability coupling is structurally tighter — the false-positive CRITICAL would otherwise pollute the consumer/banner/toast pipeline that 5a.1-5d build.
- **Finding 2 — Reconciliation per-cycle log spam.** Filed as DEF-215; deferred with sharp revisit trigger. The 300-WARNING-per-5-hours observed Apr 27 was a symptom of upstream condition (DEF-204 cascade survived through reconciliation), not a logging defect; once OCA prevents the underlying leak, the per-cycle WARNING becomes a useful "still happening" signal rather than noise.
- **Finding 3 — `max_concurrent_positions` counts broker-only longs.** Folded into DEF-211's extended scope as the cap-interaction cost of NOT making the boot-time adoption-vs-flatten policy decision. On Apr 27 Boot 2, 42 broker-only longs left only 8 effective slots; degraded operation rather than clean restart. After Sprint 31.91 lands, Pattern A filters broker-only SHORTs but longs still inflate the cap unless adopted.
- **Finding 4 — Boot-time reconciliation policy + IMPROMPTU-04 gate.** Folded into DEF-211's extended scope as deliverables D2 (gate refactor) and D3 (adoption policy). Session 1c's docstring queues this work by reference; DEF-211 makes the queuing explicit at CLAUDE.md visibility level.

The Apr 27 evidence also elevated operator-mitigation visibility: the operator forgot to run `scripts/ibkr_close_all_positions.py` between Apr 27 sessions, leaving ~$70K notional in unintended shorts overnight. CLAUDE.md's active-sprint summary now uses **REQUIRED, NOT OPTIONAL** framing for the operator daily-flatten step.

## Workflow protocol amendment surfaced by this review

This review surfaced a gap in the Tier 3 protocol itself (`protocols/tier-3-review.md` in the claude-workflow metarepo). The protocol's required output schema names "DEC entries," "RSK entries," and "doc updates" but does NOT explicitly require "DEF entries (for items carrying forward to sprints other than the one just reviewed)." Concern C in this review was almost missed as a DEF candidate because the protocol's checklist did not prompt for DEF enumeration the way it prompts for DECs and RSKs.

**Resolution:** workflow metarepo amendment to `protocols/tier-3-review.md` is part of this doc-sync pass (separate Claude Code prompt; not in the ARGUS repo). Workflow-version bumped 1.0.0 → 1.0.1 to reflect the protocol change.

## Acceptance — Sprint 31.91 cleared to proceed to Session 2a

With this verdict and the doc-sync pass landed:

- DEC-386 written.
- DEF-209 (formal filing + Concern D extension), DEF-211 (EXTENDED SCOPE per Apr 27 Findings 3+4), DEF-212, DEF-213, DEF-214 (Apr 27 Finding 1), DEF-215 (Apr 27 Finding 2, deferred) filed in CLAUDE.md.
- RSK-DEC-386-DOCSTRING filed in risk-register.md (time-bounded by Sprint 31.93).
- Architecture.md §3.3 + §3.7 updated with OCA architecture.
- Pre-live-transition-checklist.md gates encoded.
- Live-operations.md OCA architecture operations section added (rollback, lock-step, failure-mode response, spike trigger registry).
- Session 5a.1 impl prompt amended for DEF-213 schema work AND DEF-214 EOD verification fix (Patch 9 v3).
- Metarepo `protocols/tier-3-review.md` amended (workflow-version 1.0.1) to require DEF entries + verdict artifact in Output schema.

Sprint 31.91 implementation continues with Session 2a per the existing sprint plan. The OCA architecture established in Sessions 0–1c is the safety net behind Session 2b.1's broker-orphan SHORT detection; Session 2a's scope is unchanged by this Tier 3 review.

---

*Verdict generated 2026-04-27 against `protocols/tier-3-review.md` v1.0.0.*
*Doc-sync pass commits referenced: see `git log --grep "Tier 3 review #1 doc-sync"` post-application.*
*Next Tier 3 review: scheduled after Session 5b lands per Sprint Spec §"Tier 3 review checkpoints."*
