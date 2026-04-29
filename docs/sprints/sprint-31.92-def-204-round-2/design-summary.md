# Sprint 31.92 — Design Summary

> **Phase B artifact (revised post-Round-1 adversarial review).** Captures the
> sprint's design decisions, scope, and shape after Round 1 revisions applied
> 2026-04-29. This artifact is the single-page snapshot Tier 2 reviewers and
> Phase D prompt generators consult to confirm scope intent.
>
> **Revision history:** Round 1 authored 2026-04-28 with H1 cancel-and-await default; Round-1-revised 2026-04-29: Path #1 mechanism reversed to H2 amend-stop-price as PRIMARY DEFAULT (Round-1 C-3 disposition); ceiling enhanced with `cumulative_pending_sell_shares` reservation pattern (C-1); `is_reconstructed: bool` flag added for restart-safety (C-2); position-keyed suppression dict (H-2); broker-verification at suppression timeout (H-3); startup CRITICAL warning at AC4.6 (H-4); S1b spike scope expanded for hard-to-borrow microcap symbols (M-1); validation framing scoped to in-process logic only (M-2); composite validation as Pytest with JSON side-effect (M-3). Net session count UNCHANGED at 10. Net test count target raised from 53–65 to 75–95.

## Goal

Close DEF-204's two empirically-falsifying mechanism paths from the 2026-04-28 paper-session debrief: (Path #1) trail-stop / bracket-stop concurrent-trigger race producing 182-share phantom short on BITU; (Path #2) locate-rejection-as-held retry storm producing 3,837-share phantom short on PCT. Add structural defense-in-depth via long-only SELL-volume ceiling with concurrency-safe pending-share reservation pattern + reconstructed-position refusal posture. Cleanly close DEF-212 `_OCA_TYPE_BRACKET` constant drift hygiene rider. Materialize as DEC-390 with structural closure framing (NOT aggregate percentage claims per process-evolution lesson F.5).

## Sprint shape

**Sprint scope:** 4-layer composition (mirrors DEC-385/386 layered-decomposition pattern):

- **L1 Path #1 mechanism (S2a + S2b):** `_trail_flatten` + `_resubmit_stop_with_retry` emergency-flatten branch + (conditionally) `_escalation_update_stop` close concurrent-trigger race via S1a-spike-selected mechanism — H2 amend-stop-price PRIMARY DEFAULT (preserves AMD-2 invariant; `modifyOrder` round-trip ≤50ms p95); H4 hybrid (try amend, fall back to cancel-and-await on rejection) if amend rejection rate 5–20%; H1 cancel-and-await as LAST-RESORT FALLBACK only if both H2 and H4 empirically infeasible.
- **L2 Path #2 detection + position-keyed suppression + broker-verified timeout (S3a + S3b):** Add `_LOCATE_REJECTED_FINGERPRINT` constant + `_is_locate_rejection()` helper in `argus/execution/ibkr_broker.py`. Add position-keyed `OrderManager._locate_suppressed_until: dict[ULID, float]` (keyed by `ManagedPosition.id` for cross-position safety) + `_is_locate_suppressed()` helper. Wire detection at `place_order` exception in 4 standalone-SELL paths (`_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`). Suppression-timeout fallback queries broker for actual position state BEFORE alert publication (eliminates false-positive class without coupling to `IBKRReconnectedEvent` consumer that doesn't exist until Sprint 31.94).
- **L3 Long-only SELL-volume ceiling with pending-share reservation (S4a):** Add THREE fields on `ManagedPosition` — `cumulative_pending_sell_shares: int = 0` (incremented synchronously at place-time before `await`; closes asyncio yield-gap race), `cumulative_sold_shares: int = 0` (incremented at confirmed fill), `is_reconstructed: bool = False` (set True in `reconstruct_from_broker`; refuses ALL ARGUS-emitted SELLs on reconstructed positions until Sprint 31.94 D3). Ceiling check: `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total` AND `not position.is_reconstructed`. Guards 5 standalone-SELL emit sites; bracket placement explicitly excluded. New `POLICY_TABLE` entry for `sell_ceiling_violation` alert.
- **L4 DEF-212 rider with operator-visible rollback warning (S4b):** `OrderManager.__init__` accepts `bracket_oca_type: int`; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`; 4 occurrences of `_OCA_TYPE_BRACKET` module constant replaced by `self._bracket_oca_type`; module constant deleted. Startup CRITICAL warning when `bracket_oca_type != 1`.

**Sprint sequencing:** S1a + S1b spikes (parallelizable) → S2a → S2b → S3a → S3b → S4a → S4b → S5a → S5b. Strictly sequential post-spike; every implementation/validation session touches `argus/execution/order_manager.py`.

**Falsifiable foundation:** S1a + S1b Phase A spike artifacts gate Phase D impl prompts. S5a + S5b validation artifacts gate sprint seal. Composite validation as Pytest test with JSON side-effect; daily CI updates artifact mtime for freshness.

## Key Decisions

1. **Path #1 mechanism: H2 amend-stop-price PRIMARY DEFAULT** (Round-1 C-3 reversal of original H1 default). H2 keeps the bracket stop live with updated trigger price; AMD-2 invariant preserved; DEC-117 atomic-bracket invariant preserved; zero unprotected window. H4 hybrid is fallback if H2 alone has 5–20% rejection rate. H1 cancel-and-await is last-resort only if both H2 and H4 empirically infeasible (AMD-2 superseded by AMD-2-prime; operator-audit logging mandatory).
2. **Concurrency-safe pending-share reservation pattern** (Round-1 C-1). The ceiling check is `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total`. Pending counter increments synchronously at place-time (BEFORE the `await place_order(...)` yield-point) — closes the asyncio yield-gap race that two coroutines on the same `ManagedPosition` could otherwise exploit. Pending counter decrements on cancel/reject and transfers to filled counter on fill.
3. **`is_reconstructed: bool` refusal posture** (Round-1 C-2 conservative disposition). Reconstructed positions (set `True` in `reconstruct_from_broker`) refuse ALL ARGUS-emitted SELLs. Operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism until Sprint 31.94 D3 (boot-time adoption-vs-flatten policy) lands. Conservative posture chosen over reviewer-proposed alternatives (trades-table reconstruction; SQLite persistence) on attribution-ambiguity / scope-creep grounds.
4. **Position-keyed locate-suppression dict** (Round-1 H-2). Keyed by `ManagedPosition.id` (ULID), NOT symbol — preserves cross-position safety when sequential entries exist on same symbol within a session.
5. **Broker-verification at suppression timeout** (Round-1 H-3). AC2.5 fallback queries `broker.get_positions()` BEFORE alert publication. Three branches: zero (held order resolved cleanly), expected-long (no phantom short), unexpected (publish `phantom_short_retry_blocked`). Eliminates false-positive class without coupling to `IBKRReconnectedEvent` (Sprint 31.94 territory).
6. **Startup CRITICAL warning at AC4.6** (Round-1 H-4). Operator-visible warning emits at OrderManager init when `bracket_oca_type != 1`. `IBKRConfig.bracket_oca_type` Pydantic validator preserved (rollback escape hatch per DEC-386 design intent).
7. **Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) DEFERRED** to Sprint 31.93 (component-ownership scope). Tier 3 #1 Concern B (DEF-212 constant drift) RESOLVED in Sprint 31.92 S4b.
8. **DEF-211 D1+D2+D3 (Sprint 31.94 sprint-gating)** STRICTLY OUT — Sprint 31.92 must NOT modify `argus/main.py:1081` (`reconstruct_from_broker()` call site), `check_startup_position_invariant`, `_startup_flatten_disabled` flag, or `reconstruct_from_broker` body BEYOND the single-line `is_reconstructed = True` addition.
9. **Hard-to-borrow microcap spike scope** (Round-1 M-1). S1b operator-curates ≥5 PCT-class symbols × ≥10 trials per symbol. Suppression-window default derived from spike p99 + 20% margin (likely 18000s = 5hr; hard floor at 18000s if H6 ruled-out per S1b's `recommended_locate_suppression_seconds` field).
10. **Validation artifacts framed as in-process logic only** (Round-1 M-2). AC5.1/AC5.2 explicitly NOT production safety evidence. Cessation criterion #5 (5 paper sessions clean post-seal) is the production-validation gate.
11. **Composite validation as Pytest test with JSON side-effect** (Round-1 M-3). Test fixture writes JSON before assertion; daily CI workflow updates artifact mtime for freshness.
12. **DEC-390 structural-closure framing** (process-evolution lesson F.5). NO aggregate percentage claims (no "comprehensive," "complete," "fully closed," "covers ~N%"). Replaces DEC-386's empirically-falsified `~98%` claim with "L1 closes Path #1 / L2 closes Path #2 / L3 + AC3.7 reconstructed-position refusal provides structural defense-in-depth / L4 closes constant-drift hygiene."

## File Scope

**Modify:**
- `argus/execution/order_manager.py` (S2a, S2b, S3a, S3b, S4a, S4b — 6 sessions touch this file; sequential by necessity)
- `argus/execution/ibkr_broker.py` (S3a — fingerprint helper)
- `argus/main.py` (S4b — `OrderManager` construction call site)
- `argus/core/config.py` (S3a — 3 new `OrderManagerConfig` fields total)
- `argus/core/alert_auto_resolution.py` (S4a — POLICY_TABLE 14th entry for `sell_ceiling_violation`)
- `config/system_live.yaml` (S3a — new fields surfaced)
- `tests/execution/order_manager/test_def204_round2_path1.py` (new, S2a + S2b)
- `tests/execution/order_manager/test_def204_round2_path2.py` (new, S3a + S3b)
- `tests/execution/order_manager/test_def204_round2_ceiling.py` (new, S4a)
- `tests/execution/order_manager/test_def212_oca_type_wiring.py` (new, S4b)
- `tests/integration/test_def204_round2_validation.py` (new, S5a + S5b — extended at S5b for composite + restart scenarios)
- `tests/api/test_policy_table_exhaustiveness.py` (S4a — update for 14th entry)
- `scripts/spike_def204_round2_path{1,2}.py` (new, S1a + S1b)
- `scripts/validate_def204_round2_path1.py` (new, S5a)
- `scripts/validate_def204_round2_path2.py` (new, S5b)
- `scripts/spike-results/spike-def204-round2-path{1,2}-results.json` (new, S1a + S1b)
- `scripts/spike-results/sprint-31.92-validation-{path1,path2}.json` (new, autogenerated + committed)
- `scripts/spike-results/sprint-31.92-validation-composite.json` (new, autogenerated by Pytest test side-effect at S5b; daily CI updates mtime per AC5.3)

**Document at sprint-close (D14 doc-sync per `doc-update-checklist.md`):**
- `CLAUDE.md` (DEF-204 + DEF-212 status updates; active-sprint pointer)
- `docs/decision-log.md` (DEC-390)
- `docs/dec-index.md` (DEC-390 entry)
- `docs/sprint-history.md` (Sprint 31.92 row + per-sprint detail block)
- `docs/roadmap.md` (sprint close-out narrative + roadmap re-baseline)
- `docs/project-knowledge.md` (DEF table sync; active-sprint pointer)
- `docs/architecture.md` (§3.7 OrderManager additions: pending-reservation, is_reconstructed, position-keyed suppression dict, broker-verification, bracket_oca_type flow, Path #1 mechanism, Path #2 detection)
- `docs/risk-register.md` (5 RSKs filed)
- `docs/pre-live-transition-checklist.md` (Sprint 31.92 gate criteria — 12 items)
- `docs/process-evolution.md` (lesson F.5 — structural closure framing pattern)
- `.github/workflows/` (daily CI workflow for composite test freshness — operator-manual sprint-close task)

**Do NOT modify** (full list in SbC §"Do NOT modify"):
- `argus/execution/broker.py` (ABC) — Sprint 31.93 prerogative
- `argus/execution/alpaca_broker.py` — Sprint 31.95 retirement
- `argus/execution/simulated_broker.py` (semantic changes) — fixture subclasses in tests acceptable
- `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA threading) — preserve byte-for-byte
- `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used; NOT relocated
- `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b) — preserve verbatim
- `argus/execution/order_manager.py::reconstruct_from_broker` body BEYOND single-line `is_reconstructed = True` addition — Sprint 31.94 D1
- `argus/execution/order_manager.py::reconcile_positions` Pass 1/2 (DEC-385 L3+L5) — preserve verbatim
- `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check (DEF-158 fix anchor `a11c001`, lines ~3424–3489) — preserve verbatim
- `argus/main.py::check_startup_position_invariant` and `_startup_flatten_disabled` flag — Sprint 31.94 D2
- `argus/main.py:1081` (`reconstruct_from_broker()` call site) — Sprint 31.94 D1
- `argus/core/health.py::HealthMonitor` consumer + 13 existing POLICY_TABLE entries — preserve
- `argus/core/health.py::rehydrate_alerts_from_db` (DEC-388 L3) — preserve
- `argus/api/v1/alerts.py` REST endpoints + `argus/ws/v1/alerts.py` WebSocket endpoint (DEC-388 L4) — preserve
- `argus/frontend/...` (entire frontend) — zero UI changes
- `data/operations.db` schema (DEC-388 L3) — preserve; new `sell_ceiling_violation` alerts use existing `alert_state` table
- `data/argus.db` trades/positions/quality_history schemas — preserve; new fields are in-memory only
- DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md` — preserve (leave-as-historical)
- `IBKRConfig.bracket_oca_type` Pydantic validator — preserve runtime-flippability per DEC-386 design intent

## Test Strategy

**Net pytest target:** 75–95 logical tests (90–105 effective with parametrize multipliers per protocol §"Parametrized tests count per case, not per decorator"). **Final test-count target:** 5,344–5,374 pytest (5,269 baseline + 75–105 new), 913 Vitest unchanged.

**Per-session test deltas (revised estimate):**
| Session | Pytest Δ | Vitest Δ |
|---------|---------:|---------:|
| S1a | 0 | 0 |
| S1b | 0 | 0 |
| S2a | +6 to +7 | 0 |
| S2b | +7 | 0 |
| S3a | +6 | 0 |
| S3b | +8 | 0 |
| S4a | +7 logical (≈8 effective) | 0 |
| S4b | +6 logical (≈10 effective with parametrize) | 0 |
| S5a | +4 | 0 |
| S5b | +9 logical | 0 |
| **Total range** | **+75 to +95** | **0** |

**Test dependencies:**
- DEC-328 tiering: full suite at S1a pre-flight + every close-out + final review.
- New tests follow existing naming convention (`test_def204_round2_*` for path/ceiling, `test_def212_*` for rider).
- S5b composite test produces JSON artifact as side-effect; daily CI workflow updates mtime.

## Regression Invariants (preserved or established)

**Preserved from prior sprints:**
1. DEC-117 atomic bracket order placement
2. DEC-364 `cancel_all_orders()` no-args ABC contract
3. DEC-369 broker-confirmed reconciliation immunity
4. DEC-372 stop retry caps + exponential backoff
5. DEC-385 6-layer side-aware reconciliation (preserved byte-for-byte; `phantom_short_retry_blocked` alert path reused)
6. DEC-386 4-layer OCA architecture (preserved byte-for-byte; `bracket_oca_type=0` rollback escape hatch preserved with new AC4.6 startup warning)
7. DEC-388 alert observability subsystem (preserved; POLICY_TABLE extended with 14th entry)
8. DEF-158 retry 3-branch side-check (preserved verbatim — Path #2 detection is upstream at `place_order` exception, NOT a 4th branch)
9. `# OCA-EXEMPT:` exemption mechanism (preserved)

**Baseline preservation:**
10. Test count baseline (≥ 5,269 pytest at every close-out; 913 Vitest)
11. Pre-existing flake count (≤ baseline; DEF-150/167/171/190/192 unchanged)
12. Frontend immutability (zero `.tsx`/`.ts`/`.css` changes)

**New in Sprint 31.92:**
13. Long-only SELL-volume ceiling with pending+sold reservation pattern: `cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty ≤ shares_total` per `ManagedPosition` (REWRITTEN per Round-1 C-1)
14. Path #2 locate-rejection fingerprint deterministic + position-keyed suppression + broker-verified timeout (EXPANDED per Round-1 H-2 + H-3)
15. `_OCA_TYPE_BRACKET` module constant deleted; grep regression guard
16. AC4.4 OCA-type lock-step (NOT operational validity); `bracket_oca_type=0` threads through consistently (REFRAMED per Round-1 H-4)
17. AMD-2 invariant mechanism-conditional (H2 preserved / H4 mixed / H1 superseded) (REFRAMED per Round-1 C-3)
18. Spike artifacts committed and ≤30 days fresh at first post-merge paper session
19. (NEW) `is_reconstructed = True` refusal posture holds for all ARGUS-emitted SELL paths (Round-1 C-2)
20. (NEW) Pending-reservation state-transition completeness — all 5 transitions enumerated (Round-1 C-1)
21. (NEW) Broker-verification three-branch coverage at suppression timeout (Round-1 H-3)
22. (NEW) Mechanism-conditional operator-audit logging per AC1.6 (Round-1 C-3)

## Risks Filed at Sprint-Close

5 RSKs filed (depending on H2/H4/H1 mechanism selection at S1a):
- **RSK-DEC-390-AMEND** (PRIMARY if H2 selected) OR **RSK-DEC-390-CANCEL-AWAIT-LATENCY** (FALLBACK if H1 or H4-with-fallback-active)
- **RSK-DEC-390-FINGERPRINT** (UNCONDITIONAL)
- **RSK-CEILING-FALSE-POSITIVE** (UNCONDITIONAL; mitigated by S5b composite + A-class halt A11)
- **RSK-RECONSTRUCTED-POSITION-DEGRADATION** (UNCONDITIONAL; TIME-BOUNDED by Sprint 31.94 D3 seal)
- **RSK-SUPPRESSION-LEAK** (UNCONDITIONAL; PARTIALLY MITIGATED by AC2.5 broker-verification; full coupling deferred to Sprint 31.94)

## Inheritance Pointers

- **Sprint 31.93** (component-ownership): inherits Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation); DEF-208 pre-live paper stress test fixture infrastructure.
- **Sprint 31.94** (reconnect-recovery): inherits DEF-211 D1+D2+D3 (sprint-gating); RSK-DEC-386-DOCSTRING bound; `IBKRReconnectedEvent` producer/consumer wiring (eliminates RSK-SUPPRESSION-LEAK reconnect-blindness); D3 boot-time adoption-vs-flatten policy (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION).
- **Sprint 35+** (Learning Loop V2): inherits DEF-209 extended scope (`Position.side`, `redundant_exit_observed`, `cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed` SQLite persistence prerequisite).
- **Process-evolution** (RETRO-FOLD candidate, next campaign): metarepo amendments to `protocols/sprint-planning.md` + `protocols/adversarial-review.md` + `protocols/tier-3-review.md` for lesson F.5 structural-closure framing pattern.

## Cessation criteria for DEF-204

DEF-204 transitions from RESOLVED-PENDING-PAPER-VALIDATION to RESOLVED when ALL of:
1. ✅ Sprint 31.91 sealed (cumulative — 2026-04-28).
2. ✅ Sprint 31.92 sealed (target: post-Round-2-clear + Phase D + 10 sessions complete).
3. ✅ Sprint 31.92 spike + validation artifacts committed to `main` and ≤30 days old.
4. ✅ DEC-390 written below in `docs/decision-log.md` with structural-closure framing.
5. ⏸️ **5 paper sessions clean post-Sprint-31.92 seal** — counter starts at 0/5 on sprint-close.
6. ⏸️ Sprint 31.94 sealed (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION via D3).

Operator daily-flatten via `scripts/ibkr_close_all_positions.py` continues until criterion #5 satisfied. Live trading transition gated by criterion #5 + DEF-208 pre-live paper stress test (Sprint 31.93 OR 31.94).

## Adversarial Review Round 2 Status

Round 1 verdict (2026-04-29): Outcome B — 3 Critical + 4 High + 3 Medium findings, all dispositioned per `revision-rationale.md`. This package is the post-revision input for Round 2.

Round 2 scope: validate the revisions specifically (did fixes introduce new failure modes?), not the original design. See `adversarial-review-input-package.md` (revised) §"Round 2 framing" for targeted scrutiny questions across 4 risk classes (Class I — accept-in-full revisions; Class II — partial-accept dispositions; Class III — new edge cases / out-of-scope items; Class IV — cross-cutting structural concerns).

Round 2 verdict outcomes:
- **CLEAR:** sprint planner proceeds to Phase D prompt generation (10 implementation prompts + 10 review prompts + review-context.md + work-journal-handoff.md = 22 artifacts).
- **Outcome B with ≥1 Critical:** A-class halt A14 fires; sprint planner returns to Phase A; revisions re-applied; Round 3 adversarial review.