# Sprint 28.5: Revision Rationale

> **Date:** March 29, 2026
> **Context:** Adversarial review produced 8 required + 4 recommended amendments. All 12 adopted.

---

## Required Amendments — All Adopted

| AMD | Finding | Decision | Impact |
|-----|---------|----------|--------|
| AMD-1 | Config merge semantics undefined (top-level vs field-level) | **Adopted: field-level deep merge** via `deep_update()`, matching DEC-359 risk_overrides pattern. | S2 scope: add deep_update utility + test. No session count change. |
| AMD-2 | Trail flatten order (cancel safety stop first) creates naked-position risk on crash | **Adopted: sell first, cancel second.** Crash between steps yields possible double fill (dedup handles) instead of no protection. | S4b: rewrite trail flatten sequence. Safety-critical — specific test required. |
| AMD-3 | Escalation cancel-old + submit-new failure leaves position with no broker stop | **Adopted: flatten on failure.** Single-attempt submit; if it fails, immediately flatten. | S4b: add failure recovery path + ERROR logging. |
| AMD-4 | Trail/escalation could submit sell for 0 shares after T2 fills | **Adopted: shares_remaining > 0 guard** before any sell submission. Trail/escalation exit becomes no-op when shares already fully exited. | S4b: add guard at top of trail/escalation exit paths. |
| AMD-5 | `stop_to` values undefined — "half profit" ambiguous (relative to what?) | **Adopted: precise formulas using high_watermark.** Added `quarter_profit` and `three_quarter_profit` for granularity. All profit-based values reference dynamic high watermark, not static T1/T2 targets. | S1: `StopToLevel` enum + formulas in `compute_escalation_stop()`. S2: enum in Pydantic model. |
| AMD-6 | Escalation stop updates counted against DEC-372 retry cap could exhaust budget during normal operation | **Adopted: escalation exempt from retry cap.** Escalation uses single-attempt submit; failure triggers AMD-3 recovery. DEC-372 retry cap applies only to connectivity-failure loops. | S4b: skip retry counter for escalation path. |
| AMD-7 | Bar-processing order — updating high watermark before exit check creates look-ahead bias | **Adopted: prior-state-first ordering.** Compute effective stop from prior bar state → evaluate exit → THEN update high watermark. Preserves worst-case-for-longs semantics. | S5: restructure bar processing in BacktestEngine and CounterfactualTracker. Specific regression test added. |
| AMD-8 | Trail code could cancel broker safety stop before checking _flatten_pending, leaving position naked if flatten blocked | **Adopted: _flatten_pending check is the absolute FIRST step.** Complete no-op if flatten already pending — no cancellations, no submissions, no state changes. | S4b: _flatten_pending check before any broker interaction in trail AND escalation paths. Reinforces AMD-2. |

## Recommended Amendments — All Adopted

| AMD | Finding | Decision | Impact |
|-----|---------|----------|--------|
| AMD-9 | Strategies may compute ATR with different periods, producing inconsistent trail distances | **Adopted: standardize on ATR(14) via IndicatorEngine.** Strategies without IndicatorEngine ATR access emit None; trail falls back to percent. Code comments document ATR source. | S3: verify ATR(14) in strategy signal emissions. Informational flag in escalation criteria if variance detected. |
| AMD-10 | Legacy `enable_trailing_stop`/`trailing_stop_atr_multiplier` fields will confuse future developers | **Adopted: startup WARNING when legacy fields are active.** Legacy fields explicitly ignored — new ExitManagementConfig is canonical. | S3: add warning in main.py at config load. |
| AMD-11 | Fixed-dollar `min_trail_distance` ($0.05) meaningless for very high or very low priced stocks | **Adopted: document as calibrated for $5–$200 range.** Per-strategy override available. Percentage-based floor deferred to future enhancement. | Config table annotation. No code change. |
| AMD-12 | Negative ATR value would compute trail stop above current price, triggering immediate exit | **Adopted: None/zero/negative ATR guard.** `compute_trailing_stop()` returns None for invalid ATR. | S1: add validation + 2 new tests (negative, zero). |

## Session Count Impact

No session count change (6+1 contingency unchanged). Two sessions (S2, S4b) pushed to the High compaction threshold (14, 14.5) due to additional amendment-mandated tests. Both accepted with rationale documented in Session Breakdown.

## Spec-Level Artifacts Updated

1. **Sprint Spec** — All 12 amendments incorporated into acceptance criteria, config changes, and relevant decisions sections.
2. **Spec by Contradiction** — AMD-10 (deprecated config warning in refactor boundaries), AMD-11 (percentage min_trail_distance deferred).
3. **Session Breakdown** — Amendment references added to affected sessions, test counts adjusted, compaction scores recalculated.
4. **Escalation Criteria** — AMD-1 (config merge complexity), AMD-3/5 (naked position from escalation failure), AMD-7 (bar-processing order violation) added.
5. **Regression Checklist** — Per-amendment verification items added for AMD-1 through AMD-12.
