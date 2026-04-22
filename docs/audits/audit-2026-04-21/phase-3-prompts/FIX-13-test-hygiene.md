# Fix Session FIX-13-test-hygiene: tests/ — hygiene, mocks, flakes

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 25

## Scope additions (added 2026-04-22 post-CI-green)

Beyond the original DEF-150 + DEF-163 coverage, this session now also covers:

- **DEF-167** (Vitest hardcoded dates decay over time — partially resolved by
  FIX-11 which converted 4 flagged files to `new Date().toISOString()`; this
  session completes the scan of the remaining files)
- **DEF-171** (ULID xdist race — dormant locally pre-CI, now live with CI
  running xdist. Has flaked 3× under xdist locally during Sprint 31.9 reviews)

Both DEFs are known flakes that did NOT fire in the first green CI run
(`793d4fd`), but the four-DEF flake inventory should be cleared as a single
batch to consolidate test-hygiene work.

**Files touched:** `6 order-manager flatten tests at ~30.0s each = ~180s wall-cl`, `[tests/](tests/) class-vs-function mix`, `[tests/execution/test_order_manager_*.py](tests/execution/) `, `[tests/unit/](tests/unit/) subtree (2 subdirs: `core/`, `str`, `argus/ai/prompts.py`, `argus/api/__main__.py`, `argus/core/logging_config.py`, `pyproject.toml`, `tests/accounting/__init__.py`, `tests/analytics/test_def159_entry_price_known.py`, `tests/api/conftest.py`, `tests/api/test_observatory_ws.py`, `tests/core/test_clock.py`, `tests/data/test_alpaca_data_service.py`, `tests/intelligence/test_startup.py`, `tests/sprint_runner/test_notifications.py`, `tests/strategies/test_orb_breakout.py`, `tests/strategies/test_shadow_mode.py`, `tests/test_integration_sprint2.py`, `tests/test_integration_sprint26.py`, `tests/utils/test_log_throttle.py`
**Safety tag:** `safe-during-trading`
**Theme:** Test-suite hygiene: flaky test stabilization, unmocked async deps, stale skips, and xdist race conditions.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Verify paper trading is stable (no active alerts in session debrief).
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK for safe-during-trading"

# This session is safe-during-trading. Code paths touched here do NOT
# affect live signal/order flow. You may proceed during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-13): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `tests/accounting/__init__.py`: 2 findings
- `tests/sprint_runner/test_notifications.py`: 2 findings
- `tests/strategies/test_shadow_mode.py`: 2 findings
- `tests/test_integration_sprint2.py`: 2 findings
- `6 order-manager flatten tests at ~30.0s each = ~180s wall-cl`: 1 finding
- `[tests/](tests/) class-vs-function mix`: 1 finding
- `[tests/execution/test_order_manager_*.py](tests/execution/) `: 1 finding
- `[tests/unit/](tests/unit/) subtree (2 subdirs: `core/`, `str`: 1 finding
- `argus/ai/prompts.py`: 1 finding
- `argus/api/__main__.py`: 1 finding
- `argus/core/logging_config.py`: 1 finding
- `pyproject.toml`: 1 finding
- `tests/analytics/test_def159_entry_price_known.py`: 1 finding
- `tests/api/conftest.py`: 1 finding
- `tests/api/test_observatory_ws.py`: 1 finding
- `tests/core/test_clock.py`: 1 finding
- `tests/data/test_alpaca_data_service.py`: 1 finding
- `tests/intelligence/test_startup.py`: 1 finding
- `tests/strategies/test_orb_breakout.py`: 1 finding
- `tests/test_integration_sprint26.py`: 1 finding
- `tests/utils/test_log_throttle.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-G1-L03` [LOW]

**File/line:** [tests/accounting/__init__.py](tests/accounting/__init__.py), [tests/notifications/__init__.py](tests/notifications/__init__.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Empty test subdirectories mirroring the two dead-scaffold source dirs (PF-01, PF-02 in audit plan). Only `__init__.py`, no test files.

**Impact:**

> Cosmetic. Drag scan tools.

**Suggested fix:**

> Delete both directories (P1-A2 already flags the source equivalents).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 2: `P1-G2-L07` [LOW]

**File/line:** [tests/accounting/__init__.py](tests/accounting/__init__.py), [tests/notifications/__init__.py](tests/notifications/__init__.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Empty test directories mirroring dead source scaffolding.** Already flagged in G1 L3 — duplicating the confirmation here for completeness.

**Impact:**

> Cosmetic.

**Suggested fix:**

> Delete both.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 3: `P1-G1-M07` [MEDIUM]

**File/line:** [tests/sprint_runner/test_notifications.py:302-321](tests/sprint_runner/test_notifications.py#L302-L321)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **DEF-150 is not xdist-specific; it is a time-of-day bug.** CLAUDE.md says "race condition under `-n auto`, passes in isolation". The actual bug: `manager.last_halted_notification = datetime.now(UTC).replace(minute=(datetime.now(UTC).minute - 2) % 60)` is broken for the first two minutes of every hour. When `minute ∈ {0,1}`, `(0-2) % 60 = 58` and `(1-2) % 60 = 59` set the timestamp **58/59 minutes in the future** (same hour, higher minute), not 2 minutes ago. `check_reminder()` then sees the last notification as in the future and doesn't fire. In this morning's run the failure reproduced under both `-n auto` and under coverage.

**Impact:**

> Flake category is wrong in DEF table. Calling this "xdist race" misdirects future fixers.

**Suggested fix:**

> Replace the broken arithmetic with `datetime.now(UTC) - timedelta(minutes=2)`. One-line fix.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 4: `DEF-150` [LOW]

**File/line:** tests/sprint_runner/test_notifications.py:313-315
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Time-of-day arithmetic bug (NOT xdist race)

**Impact:**

> Test fails for first 2 minutes of every hour

**Suggested fix:**

> Replace (datetime.now(UTC).minute - 2) % 60 with datetime.now(UTC) - timedelta(minutes=2). UPDATE DEF ROW.

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 5: `P1-G2-C01` [CRITICAL]

**File/line:** [tests/strategies/test_shadow_mode.py:83-147](tests/strategies/test_shadow_mode.py#L83-L147)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_build_system()` calls `object.__new__(ArgusSystem)` and manually assigns 15+ private attributes.** The test bypasses `ArgusSystem.__init__` entirely, then hand-rolls an in-memory system via `MagicMock` assignments to `_event_bus`, `_counterfactual_enabled`, `_orchestrator`, `_config`, `_quality_engine`, `_position_sizer`, `_broker`, `_risk_manager`, `_grade_meets_minimum`, etc. A silent regression in `ArgusSystem.__init__` wiring (e.g., a new required field, an order change between `_orchestrator` and `_counterfactual_enabled` being set) would leave this test **green** despite live-system breakage. The pattern also couples the test to private attribute names: any rename of `_counterfactual_enabled → _cf_enabled` breaks the test without changing `_process_signal` behavior.

**Impact:**

> Safety-critical: shadow-mode routing is the execution path for counterfactual tracking and affects live signal dispatch. A false-green here means shadow routing can silently regress between releases. Pattern is used across 13 test classes in this file.

**Suggested fix:**

> Refactor to construct `ArgusSystem` via a real but minimal `__init__`, or extract `_process_signal` into a standalone service class with a minimal dependency interface. If neither is feasible, at minimum add an explicit `assert hasattr(system, attr)` guard at top of `_build_system()` for every attribute it sets, so an `__init__` rename surfaces a loud import-time error rather than a silent tautology.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 6: `P1-G2-M07` [MEDIUM]

**File/line:** [tests/strategies/test_shadow_mode.py:108](tests/strategies/test_shadow_mode.py#L108)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Lambda-based `__eq__` monkeypatch on `MagicMock` to force specific equality outcome: `mock_config.system.broker_source.__eq__ = lambda self, other: False`.** This is a subtle form of tautology: the test is controlling a comparison result rather than using a real `BrokerSource` enum value. If `_process_signal` logic is refactored to check `broker_source is BrokerSource.SIMULATED`, the lambda will silently not be triggered and the test may pass or fail unpredictably.

**Impact:**

> The pattern obscures what the test is actually asserting. G1 didn't catch this because it's coupled to the C1 `_build_system()` pattern.

**Suggested fix:**

> Replace with a real `BrokerSource.DATABENTO` (or equivalent live enum value) instead of a MagicMock lambda.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 7: `P1-G1-L01` [LOW]

**File/line:** [tests/test_integration_sprint2.py](tests/test_integration_sprint2.py) … [tests/test_integration_sprint26.py](tests/test_integration_sprint26.py) — 10 files, 93 tests
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Sprint-dated integration tests at the top `tests/` level. Useful historically but most are frozen-in-time artifacts. Sprint 26 is nine months and 60 sprints ago; Sprint 2 is ~18 months back. None are likely to be added to; few are likely to fail meaningfully if the underlying feature ever regresses (the sprint context is forgotten).

**Impact:**

> Not broken; just cognitively noisy. A reader scanning `tests/` sees 10 sprint files and doesn't know which are still load-bearing vs decorative.

**Suggested fix:**

> Either: (a) keep but move into `tests/integration/historical/` to telegraph status, or (b) audit each file — delete those whose assertions are obsolete, fold still-relevant assertions into topic-named integration tests under `tests/integration/`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 8: `P1-G2-M10` [MEDIUM]

**File/line:** [tests/test_integration_sprint2.py](tests/test_integration_sprint2.py), [tests/test_integration_sprint3.py](tests/test_integration_sprint3.py), [tests/test_integration_sprint4a.py](tests/test_integration_sprint4a.py), [tests/test_integration_sprint4b.py](tests/test_integration_sprint4b.py), [tests/test_integration_sprint5.py](tests/test_integration_sprint5.py), [tests/test_integration_sprint13.py](tests/test_integration_sprint13.py) — 6 historical files
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Sprint 2-13 integration tests are archaeological artifacts.** Read Sprint 2 (345 lines, pre-Alpaca broker work), Sprint 3 (435 lines, cash-reserve), Sprint 4a/4b (643 lines total, Orchestrator), Sprint 5 (325 lines, Phase 1 handoff), Sprint 13 (178 lines, API dependencies). These tests assert on behavior from 1-year-old architecture decisions (DEC-027, DEC-037 era). Sprint 2 still imports `Trade`, `Order`, `Side` from `argus.models.trading` — still works, but the specific shapes tested are subsumed by later, denser tests. Per-file triage below (§7 Historical Integration Tests).

**Impact:**

> Not broken; the tests pass. But a reader opening `tests/test_integration_sprint4a.py` has no way to know whether it's still a load-bearing regression guard or a decorative artifact.

**Suggested fix:**

> Triage per file (table in §7). Keep sprint-18/19/20/26 (validate current behavior); deprecate sprint-2/3/4a/4b/5 (move to `tests/integration/historical/` with a note in a README); delete sprint-13 only after confirming its 5 tests aren't unique coverage.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 9: `P1-G1-M04` [MEDIUM]

**File/line:** 6 order-manager flatten tests at ~30.0s each = ~180s wall-clock (serialized), ~60s with `-n auto`
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> From `--durations=30`: `test_emergency_flatten_closes_everything`, `test_circuit_breaker_triggers_emergency_flatten`, `test_eod_flatten_closes_all_positions`, `test_emergency_flatten_cancels_open_orders`, `test_bracket_flatten_cancels_bracket_orders`, `test_eod_flatten_broker_only_positions` — all clock in at exactly 30.0x seconds. This matches the Sprint 32.9 synchronous fill-verification `eod_flatten_timeout_seconds: 30` default. These tests appear to wait for the full verification timeout rather than mocking the fill event.

**Impact:**

> ~25% of test-suite wall-clock time spent in 6 tests. Violates `testing.md` §Tests that use real `asyncio.sleep` are wall-clock-bound. A dev iterating on order-manager logic pays 30s per test even for a 1-line change.

**Suggested fix:**

> Inspect whether fills are actually arriving in the test setup. If the timeout is hitting because the fill event is never published in the test fixture, publish a fake fill event on the asyncio.Event the order manager waits on. If the timeout IS the scenario under test, use `monkeypatch.setattr(OrderManagerConfig, 'eod_flatten_timeout_seconds', 0.1)`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 10: `P1-G2-M09` [MEDIUM]

**File/line:** [tests/](tests/) class-vs-function mix
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Class-based vs function-based test organization is inconsistent across the suite.** Class-based: `test_clock.py`, `test_risk_manager.py`, `test_event_bus.py`, `test_regime_vector_expansion.py`, `test_shadow_mode.py`, `test_position_sizer.py`, `test_tools.py`, `test_auth.py`, `test_trades.py`, `test_trade_logger.py`, `test_alpaca_data_service.py`. Function-based: `test_order_manager.py`, `test_engine.py`, `test_def159_entry_price_known.py`, `test_quality_engine.py`. `.claude/rules/testing.md` does not mandate either style, so this is organic drift. Complicates navigation and test discovery.

**Impact:**

> Discoverability friction only. Not a correctness risk. `testing.md` could pick a convention and apply it going forward.

**Suggested fix:**

> Either (a) pick class-based as the canonical form (matches the majority) and leave existing function-based files alone until they're touched next, or (b) amend `testing.md` to say "either is acceptable" to codify the status quo. Do NOT bulk-rewrite — churn for churn's sake. Codify direction so new tests align.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 11: `P1-G1-M09` [MEDIUM]

**File/line:** [tests/execution/test_order_manager_*.py](tests/execution/) — 13 order-manager test files, 233 tests
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Order-manager tests spread across 13 files with sprint-dated names (`*_sprint295.py`, `*_sprint2875.py`, `*_sprint329.py`, `*_def158.py`, `*_reconciliation_redesign.py`, etc). This is organic drift, not principled organization. `testing.md` §Test Structure says "Mirror the source tree" — the canonical target is `test_order_manager.py`. Cross-file test discovery requires knowing the sprint number.

**Impact:**

> Navigation friction; duplicated fixture setup across files; hard to see "all flatten tests in one place."

**Suggested fix:**

> Consolidate under a `tests/execution/order_manager/` package with topic-split modules: `test_flatten.py`, `test_reconciliation.py`, `test_brackets.py`, `test_exits.py`, `test_margin_circuit.py`. Delete the sprint-date suffixes. No test semantics change; pure file-layout refactor.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 12: `P1-G1-L02` [LOW]

**File/line:** [tests/unit/](tests/unit/) subtree (2 subdirs: `core/`, `strategies/`)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `tests/unit/` exists with only `core/` and `strategies/` children while >95% of unit tests live directly under `tests/core/`, `tests/strategies/`, etc. This is organic split drift. Either `tests/unit/` is canonical (in which case all unit tests should move there) or it's a wart (in which case its contents should fold into `tests/core/`, `tests/strategies/`).

**Impact:**

> Low. Discoverability friction only.

**Suggested fix:**

> Pick one convention. CLAUDE.md does not specify; follow de-facto majority and fold `tests/unit/core/` into `tests/core/`, `tests/unit/strategies/` into `tests/strategies/`. Delete `tests/unit/`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 13: `P1-G1-L05` [LOW]

**File/line:** [argus/ai/prompts.py](argus/ai/prompts.py) (63%), [argus/ai/context.py](argus/ai/context.py) (64%), [argus/ai/client.py](argus/ai/client.py) (73%), [argus/ai/executors.py](argus/ai/executors.py) (75%)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> AI Copilot modules clustered at 63-75% coverage. Most uncovered lines are per-page context builders and prompt formatters that are long and branchy.

**Impact:**

> Low risk — failure mode is user-visible (bad Copilot response) rather than silent. But given AI is proposal-enabled and can submit actions to the risk pipeline, formatter bugs deserve floor coverage.

**Suggested fix:**

> Add parametrized tests over the per-page branches in `SystemContextBuilder` and per-prompt sections of `PromptManager`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 14: `P1-G1-M11` [MEDIUM]

**File/line:** [argus/api/__main__.py](argus/api/__main__.py) (0% coverage, 34/34 missed), [argus/api/setup_password.py](argus/api/setup_password.py) (0% coverage)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Two entry-point modules at 0% coverage. These are CLI invocations (`python -m argus.api`, `python -m argus.api.setup_password`). Expected pattern is `omit` in coverage config, not "untested code." Currently they drag overall coverage down without representing actionable gaps.

**Impact:**

> Distorts the 82% headline — real coverage of library code is ~1.5% higher. Also implies CLI entry points are untested when they're just untestable via pytest-cov's default invocation.

**Suggested fix:**

> Part of M10's coverage-config fix: add both to `omit`. Optionally add one smoke test per entry using `subprocess.run([sys.executable, '-m', 'argus.api.setup_password', '--help'])`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 15: `P1-G1-M03` [MEDIUM]

**File/line:** [argus/core/logging_config.py](argus/core/logging_config.py) (24% coverage, 39/51 missed)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Logging setup code rarely exercised in unit tests (fixtures replace handlers). Lines 25-40, 64-68, 90-128 uncovered — this includes the JSON formatter path, the stderr-only fallback, and the file-handler rotation config. Any silent regression in logging would leave operators blind.

**Impact:**

> Low functional risk (if broken, you see it immediately in stdout). But a crash inside `setup_logging()` at startup would mask other startup errors.

**Suggested fix:**

> Add ≥3 tests covering: JSON formatter output shape, file handler rotation config, stderr fallback branch. Small file, cheap win.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 16: `P1-G1-M10` [MEDIUM]

**File/line:** [pyproject.toml](pyproject.toml) / missing `.coveragerc`
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **No coverage configuration present.** No `[tool.coverage]` section in pyproject.toml, no `.coveragerc`. Defaults include every line, measure line coverage only (no branch coverage), no omit paths, no target threshold. CLI coverage runs are thus non-deterministic across operators (anyone who runs `pytest --cov` without the exact flags above produces a different report).

**Impact:**

> No enforced floor. No branch coverage = rejection-branch gaps (like C1/C2) harder to spot. No `exclude_lines` means `if TYPE_CHECKING:` and `raise NotImplementedError` lines count as missed.

**Suggested fix:**

> Add a minimal `[tool.coverage.run]` and `[tool.coverage.report]` section: `source = ["argus"]`, `branch = true`, `exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError", "if __name__"]`, `omit = ["argus/api/__main__.py", "argus/api/setup_password.py"]`. Optionally set a `fail_under = 80`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 17: `P1-G1-M05` [MEDIUM]

**File/line:** [tests/analytics/test_def159_entry_price_known.py:137-179](tests/analytics/test_def159_entry_price_known.py#L137-L179)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **DEF-163 date-decay test has a timezone-mismatch bug, not a "date decay" bug.** The test stores `exit_time=datetime.now(UTC)` but `get_todays_pnl()` filters `WHERE date(exit_time) = <ET date>`. SQLite's `date()` on a `+00:00` ISO string returns the UTC date. When UTC date ≠ ET date (i.e., roughly 20:00 ET – 00:00 ET window), the test fails. Documenting it as "date decay" hides the actual timezone-handling defect.

**Impact:**

> The test did NOT fail in this morning's 09:58 ET run (both UTC and ET dates matched) but WILL fail every evening. Future operator running CI at 20:15 ET gets a confusing red that will appear intermittent.

**Suggested fix:**

> Fix the test to use `datetime.now(ZoneInfo("America/New_York"))` for `exit_time`, OR fix `trade_logger.log_trade()` to normalize exit_time to ET before storage. Pick one and document.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 18: `P1-G2-L03` [LOW]

**File/line:** [tests/api/conftest.py:247-486](tests/api/conftest.py#L247-L486)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`seeded_trade_logger` inlines 15 `Trade(...)` dict-form constructors (240 lines of fixture setup).** Heavy Q3.1 duplication: each trade repeats ~14 field assignments. Refactoring a single field rename across these 15 calls is error-prone.

**Impact:**

> Mostly cosmetic; also makes the seeded-trade scenario hard to extend without editing the conftest.

**Suggested fix:**

> Extract a `_make_trade(**overrides)` helper (analogous to patterns already used in `test_risk_manager.py`, `test_trade_logger.py`) that supplies defaults and allows per-trade overrides. Reduces to ~50 lines.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 19: `P1-G2-M08` [MEDIUM]

**File/line:** [tests/api/test_observatory_ws.py:210, 232, 396, 443, 555, 610](tests/api/test_observatory_ws.py) [tests/api/test_arena_ws.py:76, 94](tests/api/test_arena_ws.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **8 WebSocket tests use `except Exception: pass` to swallow expected `WebSocketDisconnect`.** Silent-failure category Q4.1. If the server changes to raise a different exception (e.g., a new `WebSocketError` subclass), these tests still pass because any exception is swallowed. The idiomatic replacement is `with pytest.raises(WebSocketDisconnect):`.

**Impact:**

> The tests still exercise the right code path, but their guard is too loose. A regression from `close(code=4001)` to `close(code=1000)` would not surface — the broad except swallows it.

**Suggested fix:**

> Replace each `try/except Exception: pass` with explicit `with pytest.raises((WebSocketDisconnect, <specific exception>)):` — Starlette raises `WebSocketDisconnect` on client-side `close()` and `RuntimeError` in a handful of cases. Enumerate the two and fail on anything else.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 20: `P1-G2-L05` [LOW]

**File/line:** [tests/core/test_clock.py:14-34](tests/core/test_clock.py#L14-L34)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> **`TestSystemClock.test_now_returns_current_utc_time` / `test_today_returns_current_date_in_configured_timezone` depend on real wall-clock time.** Q5.2 — depending on `datetime.now` without mocking. Low risk: the assertions are bounded (`before <= result <= after`) so timing is self-consistent. But they could fail if the system clock jumps (NTP drift, VM snapshot restore, DST boundary).

**Impact:**

> Very low. Expected to pass 99.999% of the time. Not a priority.

**Suggested fix:**

> Accept as-is — verifying `SystemClock` actually returns system time is a legitimate test.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-13-test-hygiene**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-13-test-hygiene**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 21: `P1-G2-M05` [MEDIUM]

**File/line:** [tests/data/test_alpaca_data_service.py:505-557](tests/data/test_alpaca_data_service.py#L505-L557)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`test_stale_data_detection` and `test_stale_data_recovery` use real `asyncio.sleep(6)` against a 5-second monitor interval.** Each test is 10s wall-clock. `.claude/rules/testing.md` §Tests-that-use-real-asyncio.sleep: "If a test needs more than ~3s of real sleep, reconsider whether it can be tested at a lower level." The monitor polls every 5s (hardcoded in `_stale_data_monitor`), so a 6s sleep waits for one poll cycle.

**Impact:**

> Two 10s tests in a data-service module that is otherwise fast. G1 top-30-slowest table lists both. Unlike the flatten tests, these are testing a real behavior (monitor loop), but at the wrong level.

**Suggested fix:**

> Refactor the monitor to accept an injected poll interval, then pass `monitor_poll_seconds=0.1` in test setup. Alternatively, test `_check_stale_once()` (a synchronous helper) rather than the full loop — removes the need to wait for `asyncio.sleep` at all.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 22: `P1-G2-L06` [LOW]

**File/line:** [tests/intelligence/test_startup.py](tests/intelligence/test_startup.py)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> **9 `@patch` decorators in this file.** The file counts `@patch` / `with patch` the highest in the intelligence sample — but each is a legitimate factory-wiring patch, testing that `create_intelligence_components()` correctly skips disabled sources. Not excessive.

**Impact:**

> Not a concern; documenting the ceiling.

**Suggested fix:**

> None.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-13-test-hygiene**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-13-test-hygiene**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 23: `P1-G2-L02` [LOW]

**File/line:** [tests/strategies/test_orb_breakout.py:16-53](tests/strategies/test_orb_breakout.py#L16-L53)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`make_orb_config()` helper has 14 parameters, most with defaults.** Signals a missing factory fixture. 1,460 lines in this file; similar helper patterns across the strategy-tests directory.

**Impact:**

> Verbose test setup. Mostly cosmetic; tests pass.

**Suggested fix:**

> Either (a) extract a `pytest.fixture` that yields a default-constructed `OrbBreakoutConfig` and let tests parametrize via `dataclasses.replace(config, field=new_value)`, or (b) use `pytest-factoryboy` / similar factory library. Incremental — start with one module.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 24: `P1-G2-L08` [LOW]

**File/line:** [tests/test_integration_sprint26.py:41](tests/test_integration_sprint26.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Sprint 26 integration tests imports `AfternoonMomentumStrategy` that is unused in this file.** Minor dead import.

**Impact:**

> Cosmetic.

**Suggested fix:**

> Remove unused import.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

### Finding 25: `P1-G2-L04` [LOW]

**File/line:** [tests/utils/test_log_throttle.py](tests/utils/test_log_throttle.py), [tests/api/test_lifespan_startup.py](tests/api/test_lifespan_startup.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Two files use `time.sleep()` rather than `asyncio.sleep()`.** `testing.md` says "Never use `time.sleep()` — use `asyncio.sleep()`" (architecture.md). `test_log_throttle.py` tests time-based throttle behavior (legitimate use if the throttle uses wall-clock). `test_lifespan_startup.py`: need to verify.

**Impact:**

> Low; wall-clock tests are occasionally the right call. Worth confirming these are the intended exceptions.

**Suggested fix:**

> If intentional (e.g., testing a `time.monotonic()`-based rate limiter), add a docstring explaining why. Otherwise, replace with mocked clock.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-13-test-hygiene**`.

## Post-Session Verification (before commit)

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-13-test-hygiene** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-13-test-hygiene**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-13` (full ID: `FIX-13-test-hygiene`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-13-test-hygiene**` | | |
| Every DEF closure recorded in CLAUDE.md | | |
| Every new DEF/DEC referenced in commit message bullets | | |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | | |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | | |

### Output format

Render the close-out inside a fenced markdown code block (triple backticks
with `markdown` language hint) bracketed by `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---` markers, followed by the `json:structured-closeout`
JSON appendix. Exact format per the close-out.md skill.

The operator will copy this block into the Work Journal conversation on
Claude.ai. Do NOT summarize or modify the format — the conversation parses
these blocks by structure.

### Self-assessment gate

Per close-out.md:
- **CLEAN:** all findings resolved, no unexpected decisions, all tests pass, all regression checks pass
- **MINOR_DEVIATIONS:** all findings addressed but minor judgment calls needed
- **FLAGGED:** any partial finding, test failures, regression check failures, scope exceeded, architectural concerns

**Proceed to the Commit section below UNLESS self-assessment is FLAGGED.**
If FLAGGED, pause. Surface the flag to the operator with a clear
description. Do not push. Wait for operator direction.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-13): test hygiene

Addresses audit findings:
- P1-G1-L03 [LOW]: Empty test subdirectories mirroring the two dead-scaffold source dirs (PF-01, PF-02 in audit plan)
- P1-G2-L07 [LOW]: Empty test directories mirroring dead source scaffolding
- P1-G1-M07 [MEDIUM]: DEF-150 is not xdist-specific; it is a time-of-day bug
- DEF-150 [LOW]: Time-of-day arithmetic bug (NOT xdist race)
- P1-G2-C01 [CRITICAL]: '_build_system()' calls 'object
- P1-G2-M07 [MEDIUM]: Lambda-based '__eq__' monkeypatch on 'MagicMock' to force specific equality outcome: 'mock_config
- P1-G1-L01 [LOW]: Sprint-dated integration tests at the top 'tests/' level
- P1-G2-M10 [MEDIUM]: Sprint 2-13 integration tests are archaeological artifacts
- P1-G1-M04 [MEDIUM]: From '--durations=30': 'test_emergency_flatten_closes_everything', 'test_circuit_breaker_triggers_emergency_flatten', 't
- P1-G2-M09 [MEDIUM]: Class-based vs function-based test organization is inconsistent across the suite
- P1-G1-M09 [MEDIUM]: Order-manager tests spread across 13 files with sprint-dated names ('*_sprint295
- P1-G1-L02 [LOW]: 'tests/unit/' exists with only 'core/' and 'strategies/' children while >95% of unit tests live directly under 'tests/co
- P1-G1-L05 [LOW]: AI Copilot modules clustered at 63-75% coverage
- P1-G1-M11 [MEDIUM]: Two entry-point modules at 0% coverage
- P1-G1-M03 [MEDIUM]: Logging setup code rarely exercised in unit tests (fixtures replace handlers)
- P1-G1-M10 [MEDIUM]: No coverage configuration present
- P1-G1-M05 [MEDIUM]: DEF-163 date-decay test has a timezone-mismatch bug, not a "date decay" bug
- P1-G2-L03 [LOW]: 'seeded_trade_logger' inlines 15 'Trade(
- P1-G2-M08 [MEDIUM]: 8 WebSocket tests use 'except Exception: pass' to swallow expected 'WebSocketDisconnect'
- P1-G2-L05 [LOW]: 'TestSystemClock
- P1-G2-M05 [MEDIUM]: 'test_stale_data_detection' and 'test_stale_data_recovery' use real 'asyncio
- P1-G2-L06 [LOW]: 9 '@patch' decorators in this file
- P1-G2-L02 [LOW]: 'make_orb_config()' helper has 14 parameters, most with defaults
- P1-G2-L08 [LOW]: Sprint 26 integration tests imports 'AfternoonMomentumStrategy' that is unused in this file
- P1-G2-L04 [LOW]: Two files use 'time

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Tier 2 Review (REQUIRED after commit — follows `workflow/claude/skills/review.md`)

After the commit above is pushed, invoke the Tier 2 reviewer in this same
session:

```
@reviewer

Please follow workflow/claude/skills/review.md to review the changes from
this session.

Inputs:
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-13-test-hygiene)
- **Close-out report:** the ---BEGIN-CLOSE-OUT--- block produced before commit
- **Regression checklist:** the 8 campaign-level checks embedded in the close-out
- **Escalation criteria:** trigger ESCALATE verdict if ANY of:
  - any CRITICAL severity finding
  - pytest net delta < 0
  - scope boundary violation (file outside declared Scope modified)
  - different test failure surfaces (not the expected DEF-150 flake)
  - Rule-4 sensitive file touched without authorization
  - audit-report back-annotation missing or incorrect
  - (FIX-01 only) Step 1G fingerprint checkpoint failed before pipeline edits proceeded

Produce the ---BEGIN-REVIEW--- block with verdict CLEAR / CONCERNS /
ESCALATE, followed by the json:structured-verdict JSON appendix. Do NOT
modify any code.
```

The reviewer produces its report in the format specified by review.md
(fenced markdown block, `---BEGIN-REVIEW---` markers, structured JSON
verdict). The operator copies this block into the Work Journal conversation
alongside the close-out.

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** (for Work Journal paste)
2. **The review markdown block** (for Work Journal paste)
3. **A one-line summary:** `Session FIX-13 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-13-test-hygiene**`
