---BEGIN-CLOSE-OUT---
```markdown
# Close-Out — IMPROMPTU-04-eod-short-flip-and-log-hygiene

- **Sprint:** `sprint-31.9-health-and-hardening`
- **Session:** `IMPROMPTU-04` (Track B / Stage 9A — safety-critical)
- **Date:** 2026-04-23
- **Commit:** `0623801` (pushed to `origin/main` after docs close-out)
- **Baseline HEAD:** `c655cb3` (debrief triage + IMPROMPTU-04 kickoff committed)
- **Test delta:** 5,039 → 5,052 passed (+13 net). Vitest 859 → 859 (session touches no UI).
- **Warning delta:** unchanged (no new warnings introduced).
- **Self-Assessment:** `MINOR_DEVIATIONS`

## Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/execution/order_manager.py` | modified | **A1 fix, two sites.** `:1707` (EOD Pass 2) and `:1684` (EOD Pass 1 retry) now branch on `pos.side`: `OrderSide.BUY` → existing `_flatten_unknown_position` SELL call; `OrderSide.SELL` → ERROR log identifying unexpected short + skip; unknown side → ERROR log + skip. Pass 1 retry now builds a `broker_side_map` alongside the existing `broker_qty_map`. `OrderSide` import already present from prior sessions. No other changes to this file. |
| `argus/main.py` | modified | **Startup invariant.** New module-level helper `check_startup_position_invariant(positions) -> tuple[bool, list[str]]` (pure function, fails closed on missing `side` attribute). New `ArgusSystem._startup_flatten_disabled: bool` attribute. After `self._broker.connect()` in `start()`, `get_positions()` is audited; flag set on any non-BUY side or any exception (fail-closed). Gates `self._order_manager.reconstruct_from_broker()` — skipped entirely when the flag is set, WARNING logged. |
| `argus/strategies/pattern_strategy.py` | modified | **C1 fix.** `:318` `logger.info` → `logger.debug` for the `"evaluating %s with partial history (%d/%d)"` warm-up log. Apr 22 paper session: 778,293 of 895,543 total log lines (87%) came from this single site. No other changes. |
| `tests/execution/order_manager/test_def199_eod_short_flip.py` | **added** | Canaries 1 + 2: 6 revert-proof tests for the A1 Pass 2 + Pass 1-retry side-check. Covers SELL-position skipped, LONG still flattened, mixed long+short only flattens long, side=None skipped with ERROR, Pass 1 retry skips short, Pass 1 retry still flattens long on timeout. Reverting either filter-site fix causes a clear, named assertion failure. |
| `tests/test_startup_position_invariant.py` | **added** | Canary 4: 5 pure-function tests for `check_startup_position_invariant()`. Covers empty list, all-long, single-short, mixed, and position-missing-side-attr (fail-closed). Uses real `Position` objects where possible; a `MagicMock(spec=[])` is used only for the missing-attribute case. |
| `tests/strategies/patterns/test_pattern_strategy.py` | modified | Canary 3: 2 new tests appended at end of file covering the C1 log-level downgrade. `test_warmup_partial_history_log_does_not_fire_at_info_level` (reverting the level regresses to INFO and fails) + `test_warmup_partial_history_log_still_fires_at_debug_level` (non-regression — log content preserved). |
| `tests/execution/order_manager/test_sprint295.py` | modified | Pre-existing Sprint 29.5 test updates — 2 MagicMock broker-position sites now declare `side=OrderSide.BUY` (attribute was absent, which the new side-check routes to the "unknown side" ERROR branch). Added `OrderSide` to imports. Intent of the affected tests (verifying long-position flatten happy paths) is unchanged. |
| `tests/execution/order_manager/test_sprint329.py` | modified | Pre-existing Sprint 32.9 test update — `_make_broker_position()` helper now takes an optional `side: OrderSide = OrderSide.BUY` parameter and sets `pos.side` on the mock. Shorts can be injected via `side=OrderSide.SELL`. All 49 tests in these two files pass unchanged otherwise. |
| `CLAUDE.md` | modified | DEF-199 row: `| DEF-199 | ... |` → `| ~~DEF-199~~ | ~~...~~ | — | **RESOLVED** (IMPROMPTU-04, 2026-04-23, commit `0623801`): three-part fix ...` with full resolution description. Last-updated banner bumped. |
| `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | modified | Last-updated banner + Campaign HEAD → `0623801`; baseline tests → 5,052; Stage 9A row marked ✅ COMPLETE with commit SHA; new session-history row for IMPROMPTU-04; baseline progression updated; DEF-199 moved into "Resolved this campaign"; DEF-199 row in "New DEFs" table strikethrough with resolution pointer. |
| `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` | modified | Last-updated comment bumped; Stage 9A row marked ✅ CODE LANDED with commit SHA; DEF-199 moved from "Will resolve" into a new "Already resolved during campaign" sub-table. |

## Judgment Calls

Decisions made during implementation that were not pre-specified.

- **Startup invariant integration point.** The kickoff (Requirement 3, final paragraph) authorized "the simplest path: skip the `_drain_startup_flatten_queue` call in `argus/main.py` when `self._startup_flatten_disabled` is True." On inspection, `_drain_startup_flatten_queue` is not called from `main.py` — it is invoked from inside `OrderManager._poll_loop` when market opens. The two realistic integration points in `main.py` are: (a) gate `reconstruct_from_broker()` entirely, or (b) thread a `skip_zombie_flatten` parameter through `OrderManager.reconstruct_from_broker()`. Option (b) would modify `order_manager.py` outside the authorized `:1684`/`:1707` window and was thus out of scope per the constraints block. Chose (a): gate the entire `reconstruct_from_broker()` call. Trade-off: legit bracket-equipped long positions also skip reconstruction when the flag is set — but the flag only sets on *unexpected shorts*, and the operator mandate in that state is "investigate and cover manually before restart," so not auto-reconstructing is a feature not a bug. Documented in the `main.py` call-site comment.

- **Invariant helper placed at module level, not as an `ArgusSystem` method.** The kickoff didn't specify where the helper should live. Putting it at module level (rather than as a method) keeps it testable as a pure function with a simple imports-only dependency graph. `tests/test_startup_position_invariant.py` imports it directly with `from argus.main import check_startup_position_invariant` and exercises 5 scenarios without spinning up the full `ArgusSystem` state machine. The alternative (inlining the logic or making it a method) would have forced the test suite to mock most of `ArgusSystem.__init__`.

- **Fail-closed on missing `side` attribute.** The kickoff's "defensive: side=None skipped" pattern extends to "defensive: side attribute missing entirely." A future broker adapter returning Position-shaped objects without a `side` field would silently pass through if the helper only checked `side != OrderSide.BUY` (because `getattr(pos, "side", None) != OrderSide.BUY` would be True but the Pass-2 ERROR branch would fire correctly). For the *invariant helper*, however, absence-of-side means we can't tell if this is a short — safer to flag it as a violation and disable auto-cleanup. Used a sentinel pattern (`getattr(pos, "side", _sentinel)`) so callers get an explicit `side=MISSING` descriptor in the log.

- **Pre-existing test mock updates.** 5 pre-existing tests in `test_sprint295.py` (2 sites) and `test_sprint329.py` (1 helper, 3 call sites via helper) failed after the A1 fix because their `MagicMock` broker positions didn't set `side` — the attribute resolved to a `MagicMock` auto-attribute which `!= OrderSide.BUY`, routing them to the new ERROR branch. These are legitimate mock updates, not test-logic changes: the tests are verifying the happy path of flattening long positions, and the mocks just needed to declare they *are* long. `_make_broker_position` in `test_sprint329.py` gained a `side: OrderSide = OrderSide.BUY` parameter so shorts can still be injected explicitly (and are, via the DEF-199 canary tests elsewhere). Two MagicMock sites in `test_sprint295.py` updated inline.

- **No change to `_flatten_unknown_position` implementation.** The kickoff's constraints block was explicit: the side-check goes in the *filter* (the decision point), not in the flatten implementation. Adhered. `_flatten_unknown_position` is unchanged, so any future caller that legitimately needs to place a BUY (e.g., short-covering logic in a future Sprint 28+ shorting feature) can call it directly without re-plumbing.

- **Sprint 32.9 / 29.5 test baseline restored, not rewritten.** The updates to `test_sprint295.py` and `test_sprint329.py` are the minimum diff: a new `.side = OrderSide.BUY` assignment per MagicMock, or a default param on the helper. No test logic changed. All 49 tests in these files pass post-update. This preserves the prior sprint's regression coverage.

## Scope Verification

| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| R1: A1 fix at `order_manager.py:1707` (EOD Pass 2) | DONE | Three-branch logic (BUY flatten / SELL ERROR skip / unknown ERROR skip) with matching log messages. |
| R2: A1 fix at `order_manager.py:1684` (EOD Pass 1 retry) | DONE | New `broker_side_map` built alongside `broker_qty_map`; same three-branch logic with Pass-1-retry-specific log wording. |
| R3: Startup invariant in `main.py` | DONE | Module-level helper + `_startup_flatten_disabled` attribute + post-connect audit + gated `reconstruct_from_broker()` call. Fails closed on exception. |
| R4: C1 fix at `pattern_strategy.py:318` | DONE | `logger.info` → `logger.debug`. Explanatory comment added. Content of log message unchanged. |
| Canary 1 revert-proof (Pass 2) | DONE | `test_short_position_is_not_flattened_by_pass2`: reverts → `place_order` called with SELL for FAKE → `assert_not_called()` fires → test fails with a clear message. |
| Canary 2 revert-proof (Pass 1 retry) | DONE | `test_pass1_retry_skips_short_position`: reverts → retry "retrying" WARNING fires → assertion on absence of that log fails. |
| Canary 3 revert-proof (C1 log) | DONE | `test_warmup_partial_history_log_does_not_fire_at_info_level`: revert `logger.debug` → `logger.info` → INFO caplog captures `"partial history"` record → assertion fails. |
| Canary 4 revert-proof (invariant) | DONE | 5 tests on the pure helper. Reverting the helper to always-pass would break `test_single_short_fails_invariant` and `test_mixed_longs_and_shorts_returns_just_the_shorts`. |
| Grep-verify `get_positions()` call sites | DONE | See "Grep-audit" section below. 11 call sites in `argus/`; 2 fixed here, 9 enumerated with rationale. |

## Regression Checklist

| Check | Evidence |
|---|---|
| Position with `side=BUY, shares=100` still gets flattened by EOD Pass 2 | `test_long_position_is_still_flattened_by_pass2` — asserts SELL placed, symbol + qty matches. |
| Position with `side=SELL, shares=100` does NOT get flattened by EOD Pass 2 | `test_short_position_is_not_flattened_by_pass2` — asserts `place_order.assert_not_called()`; ERROR log present. |
| Position with `side=None, shares=100` is skipped with ERROR log | `test_pass2_position_with_side_none_is_skipped`. |
| EOD Pass 1 retry respects same side check | `test_pass1_retry_skips_short_position`. |
| `pattern_strategy.py:318` no longer fires at INFO | `test_warmup_partial_history_log_does_not_fire_at_info_level` (caplog INFO+ filter, 9 warm-up bars, zero matches). |
| `pattern_strategy.py:318` still fires at DEBUG (log content preserved) | `test_warmup_partial_history_log_still_fires_at_debug_level`. |
| Startup invariant blocks cleanup on unexpected short | `test_single_short_fails_invariant` + `test_mixed_longs_and_shorts_returns_just_the_shorts` + `main.py` call-site gating the `reconstruct_from_broker()` call. |
| Startup invariant passes when all positions are long | `test_all_long_positions_returns_ok` + `test_empty_positions_returns_ok`. |
| Startup invariant fails-closed on missing `side` attr | `test_position_without_side_attr_fails_closed`. |
| No other `get_positions()` call site was missed | Grep-audit below. |
| Order Manager bracket amendment flow unchanged | `git diff` shows edits only at the authorized filter sites (`:1684` + `:1707` regions). Bracket amendment / stop-retry / reconciliation code untouched. |
| `IBKRBroker.get_positions()` signature + `abs(int(...))` unchanged | `git diff` shows zero edits to `argus/execution/ibkr_broker.py`. |
| `Position.shares: int = Field(ge=1)` unchanged | `git diff` shows zero edits to `argus/models/trading.py`. |

## Grep-Audit of `broker.get_positions()` Call Sites

Run: `grep -rn "broker\.get_positions\|await.*get_positions\|\.get_positions(" argus/` (production only).

| # | File:Line | Disposition | Rationale |
|---|---|---|---|
| 1 | `argus/core/risk_manager.py:335` | **Intentionally different** | Max-concurrent-positions check uses `len(positions)` only. Side-agnostic; count is correct regardless. No short-flip surface. |
| 2 | `argus/core/risk_manager.py:771` | **Intentionally different** | `daily_integrity_check` uses `len(positions)` only. Same rationale as #1. |
| 3 | `argus/main.py:1412` | **Intentionally different** | Background reconciliation task builds `{symbol: qty}` dict and calls `OrderManager.reconcile_positions()`. Downstream reconciliation validates symbol-set membership, not flatten decisions. Could be improved to emit a divergence alert for shorts, but that's DEF-195 scope (post-31.9 reconnect-recovery sprint). |
| 4 | `argus/analytics/debrief_export.py:336` | **Intentionally different** | Read-only export for end-of-session debrief JSON. No flatten decision. Side-agnostic by design (wants to see whatever is there). |
| 5 | `argus/execution/order_manager.py:1492` | **Intentionally different** | Margin circuit breaker auto-reset — uses `len(broker_positions)` only. Count-threshold based; side-agnostic. |
| 6 | `argus/execution/order_manager.py:1677` | **FIXED by this session** | EOD Pass 1 retry. `broker_side_map` now built alongside `broker_qty_map`; three-branch side check applied. |
| 7 | `argus/execution/order_manager.py:1701` | **FIXED by this session** | EOD Pass 2. Three-branch side check applied to the `qty > 0` filter. |
| 8 | `argus/execution/order_manager.py:1729` | **Intentionally different** | Post-flatten verification query — logs CRITICAL with `remaining_syms` list if Pass 1+2 left anything. Informational only; no order placed. |
| 9 | `argus/execution/order_manager.py:1810` | **Startup-cleanup path — gated by the new invariant** | `reconstruct_from_broker()`: classifies positions into managed (has bracket orders) vs zombie (no orders); zombies go to `_flatten_unknown_position`. The new `ArgusSystem._startup_flatten_disabled` flag set by the startup invariant skips the *entire* `reconstruct_from_broker()` call when any non-BUY side is detected at connect. A per-position side-check inside `reconstruct_from_broker()` itself would be tighter (allow legit longs to reconstruct while blocking zombie-short flattens), but would require a constructor-signature or method-signature change to `OrderManager`, which is out of scope per the constraints block. |
| 10 | `argus/execution/order_manager.py:2354` | **Intentionally different** | `_check_flatten_pending_timeouts` — re-queries broker qty for a *known* in-flight flatten to detect DEF-158 (fill already happened). Matches on symbol only, uses `abs(int(shares))` for quantity; doesn't place a new SELL blindly. No short-flip surface. |
| 11 | `argus/core/health.py:419` | **Intentionally different** | Daily integrity check — walks positions + open orders to verify stop-order coverage. Read-only; no order placement. |

Total: 11 call sites. 2 fixed by this session. 1 covered defensively by the new startup invariant (site #9). 8 intentionally different (count-only, read-only, or side-aware in a different way).

## Side-Effect Audit

- **Bracket amendment flow:** `git diff argus/execution/order_manager.py` confirms no edits to `_amend_bracket_stop`, `_amend_stop_price`, `_stop_cancel_retry_*`, or `_bracket_legs_*` — unchanged.
- **Stop-retry logic:** Same — no edits to `stop_cancel_retry_max` handling or `_amended_prices`.
- **Reconciliation code path:** No edits to `reconcile_positions()` or `_broker_confirmed` gating.
- **`get_positions()` signature:** Zero edits to `argus/execution/ibkr_broker.py`, `argus/execution/broker.py`, `argus/execution/simulated_broker.py`, or `argus/execution/alpaca_broker.py`.
- **`Position.shares` Pydantic constraint:** Zero edits to `argus/models/trading.py`.
- **`_flatten_unknown_position` implementation:** Zero edits. The side-check is in the caller (the filter), not the callee.
- **`workflow/` submodule:** Zero edits (RULE-018 respected).

## Context State

**GREEN.** Session completed well within context limits. Full suite pytest run completed and shows 5,052 passing. 4 canary test categories (A1 Pass 2, A1 Pass 1 retry, C1 log, startup invariant) all flip from FAIL (pre-fix) to PASS (post-fix) — each verified explicitly before and after the fix. No compaction events. No destructive git operations.

## CI Attestation

Pending. The CI run triggered by `git push` for commit `0623801` has not yet been observed green at the time of close-out drafting. Per P25 the close-out MUST cite a green CI URL; the operator should block the "paper trading CLEARED TO RESUME" line on that verification. The same applies to the docs-only follow-up commit that lands this close-out and the doc updates — neither should be treated as final until CI is green.

Per the constraints block, the current commit must not be considered merged until CI green is observed. If CI is red for any reason, escalate and do NOT resume paper trading.

## Paper-Trading Readiness Attestation

**CONDITIONAL GO, pending (a) Tier 2 adversarial review CLEAR/CONCERNS-resolved verdict and (b) green CI.** With both conditions met, the operator may resume paper trading after stopping and restarting ARGUS (code changes don't hot-reload). See the kickoff's "Post-Session ARGUS Restart Timing" table for recommended restart windows. Restart verification: tail `logs/argus_YYYYMMDD.jsonl` for (1) absence of the `"partial history"` INFO spam; (2) new `"Startup invariant: N broker positions at connect, all long — auto-cleanup enabled."` INFO line OR `"STARTUP INVARIANT VIOLATED"` ERROR if something unexpected is still open; (3) next-EOD wording "closing untracked long broker position" rather than "closing untracked broker position".

## Deferred Items

None new. Cross-references (already tracked on CLAUDE.md):
- DEF-194 (stale position cache after reconnect) — causal upstream of DEF-199 on Apr 22.
- DEF-195 (`max_concurrent_positions` diverges from broker state) — related blast-radius amplifier.
- DEF-196 (32 DEC-372 stop-retry-exhaustion cascade) — the mechanism that likely flipped the 50 positions short before EOD.

These three are scheduled for the post-31.9 Reconnect-Recovery sprint; IMPROMPTU-04's scope is deliberately limited to the EOD safety gate, not the session-long cascade that produced the initial shorts.

```json:structured-closeout
{
  "session_id": "IMPROMPTU-04-eod-short-flip-and-log-hygiene",
  "sprint_id": "sprint-31.9-health-and-hardening",
  "date": "2026-04-23",
  "commit": "0623801",
  "baseline_head": "c655cb3",
  "self_assessment": "MINOR_DEVIATIONS",
  "context_state": "GREEN",
  "test_delta_pytest": 13,
  "test_delta_vitest": 0,
  "pytest_pre": 5039,
  "pytest_post": 5052,
  "vitest_pre": 859,
  "vitest_post": 859,
  "warnings_delta": 0,
  "defs_closed": ["DEF-199"],
  "defs_partial": [],
  "defs_opened": [],
  "decs_landed": [],
  "files_production_modified": [
    "argus/execution/order_manager.py",
    "argus/main.py",
    "argus/strategies/pattern_strategy.py"
  ],
  "files_test_modified": [
    "tests/execution/order_manager/test_sprint295.py",
    "tests/execution/order_manager/test_sprint329.py",
    "tests/strategies/patterns/test_pattern_strategy.py"
  ],
  "files_test_added": [
    "tests/execution/order_manager/test_def199_eod_short_flip.py",
    "tests/test_startup_position_invariant.py"
  ],
  "files_doc_modified": [
    "CLAUDE.md",
    "docs/sprints/sprint-31.9/RUNNING-REGISTER.md",
    "docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md"
  ],
  "files_doc_added": [
    "docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md"
  ],
  "files_untouched_per_scope": [
    "argus/execution/ibkr_broker.py",
    "argus/models/trading.py",
    "workflow/**"
  ],
  "ci_url": "pending — link to add after CI run completes against 0623801",
  "tier_2_verdict": "pending",
  "paper_trading_readiness": "CONDITIONAL_GO_PENDING_TIER_2_AND_CI"
}
```
```
---END-CLOSE-OUT---
