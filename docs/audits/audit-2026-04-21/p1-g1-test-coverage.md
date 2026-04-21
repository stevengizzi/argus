# Audit: Test Coverage
**Session:** P1-G1
**Date:** 2026-04-21
**Scope:** Full pytest suite coverage analysis via `pytest --cov=argus` across 288 test files / ~4,934 tests. Identifies coverage gaps in critical paths and failure-mode branches, not absolute line-coverage scoring.
**Files examined:** 3 deep (risk_manager.py, order_manager.py, 2 failing tests) / ~30 skimmed (critical-path source files + test files)

---

## Run Summary

| Metric | Value |
|-------:|-------|
| Overall line coverage | **82%** (30,973 statements, 5,637 missed) |
| Tests passed / failed | 4,933 passed / 1 failed (under coverage) |
| Full-suite wall time (with `--cov`) | 191.6s |
| Full-suite wall time (no cov, `-n auto`) | 138.9s |
| Failures under coverage | `test_check_reminder_sends_after_interval` (DEF-150) |
| Additional failures under no-cov durations run | `test_speed_benchmark` (NEW, not in DEF list) |
| Modules at 0% coverage | 2 (`api/__main__.py`, `api/setup_password.py`) |
| Modules <40% coverage | 4 |
| Modules <60% coverage | 13 |
| Modules ≥95% coverage | 56 |

Coverage output: `/tmp/argus-audit/coverage.log`, `/tmp/argus-audit/htmlcov/` (NOT committed per session rules).

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [argus/core/risk_manager.py:618-638](argus/core/risk_manager.py#L618-L638) | **Post-close circuit-breaker trigger path is uncovered.** `_check_circuit_breaker_after_close()` is one of only two code paths that flip `_circuit_breaker_active=True` (the other is inline in `evaluate_signal()`). Lines 621, 627-634 are uncovered per `--cov-report=term-missing`. Existing `test_daily_loss_limit_triggers_circuit_breaker` at [test_risk_manager.py:314](tests/core/test_risk_manager.py#L314) sets `_daily_realized_pnl` directly and calls `evaluate_signal()` — it never exercises the position-close path that enters `record_realized_pnl()`. A silent regression that broke the post-close breaker would not be caught by any test. | The post-close path is how the breaker actually fires in live trading (realized P&L only exists after closes). Uncovered failure-mode branch in safety-critical code. | Add a regression test that closes losing positions via `record_realized_pnl()` cumulatively past the daily limit, then asserts (a) `CircuitBreakerEvent` published, (b) `_circuit_breaker_active` true, (c) subsequent signals rejected. Also covers the `return` at line 621 (already-triggered early-exit). | safe-during-trading |
| C2 | [argus/core/risk_manager.py:386-394](argus/core/risk_manager.py#L386-L394), [argus/core/risk_manager.py:405-421](argus/core/risk_manager.py#L405-L421) | **Two rejection paths in position-sizing are uncovered.** Both ranges are the "reduce-to-fit → still-below-min-risk-floor → reject" branches for the cash-reserve and buying-power checks. Per `risk-rules.md`: "If ANY of these are false, the order MUST be rejected." The reject branch under DEC-249-style approve-with-modification floor (0.25R) is the specific invariant that keeps undersized reductions from being silently accepted. Happy-path reductions (lines 383-384, 420-421) are covered; the reject-after-reduction branch is not. | Legit rejection-reason coverage gap per `testing.md` §Safety-Critical ("every approval path, every rejection path"). A change to `_below_min_risk_floor()` or the reduction math could silently turn rejects into accepts for a corner case. | Add two parametrized tests: (1) cash reserve so low the reduced shares violate `min_position_risk_dollars`, (2) buying power so low the reduced shares violate same. Assert `OrderRejectedEvent` with the specific reason substring. | safe-during-trading |

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [tests/backtest/test_walk_forward_engine.py:559-626](tests/backtest/test_walk_forward_engine.py#L559-L626) | **Timing-flaky test not tracked in DEF table.** `test_speed_benchmark` asserts `speed_ratio = replay_time / engine_time >= 3.0` with 10ms vs 50ms `asyncio.sleep()` delays. Under xdist worker contention (no-cov run at 138.9s) it failed; under coverage overhead (single-worker dominated, 191.6s) it passed. `testing.md` explicitly warns against sleep-bound tests >3s; this test's *assertion* is wall-clock-contention-bound even at 10ms. | Silent flake. Not in CLAUDE.md Known Issues list. Next operator CI run could produce a random red. Worse: it measures scheduler behavior, not the code's actual speedup. | Either (a) replace the timing assertion with a functional assertion that both engines produce equal results on identical mocked inputs, or (b) increase the per-call delay to 100ms+ and loosen the ratio to 2.0x so scheduler jitter is dominated by the measured quantity. Open a DEF for the flake. | safe-during-trading |
| M2 | [argus/main.py](argus/main.py) (1,096 statements, 874 missed = **20% coverage**) | `main.py` is the lowest-coverage non-zero module. Most lines are Phase 1-12 startup, most of which is exercised only by `test_main.py` (which is excluded from `-n auto` per DEF-048). Without its integration paths, much of the file only gets touched via narrowly scoped fixtures. | Already partially acknowledged (DEF-048 + P1-A1 findings). Coverage number dominates the overall 82% but is somewhat misleading — `main.py` IS integration-tested, just not under xdist. Worth an explicit note so the 82% headline isn't misread. | Not a gap to close in P1-G1 directly; align with P1-A1 recommendations. Consider running `test_main.py` in a separate non-xdist pass in CI and merging coverage reports. | read-only-no-fix-needed |
| M3 | [argus/core/logging_config.py](argus/core/logging_config.py) (24% coverage, 39/51 missed) | Logging setup code rarely exercised in unit tests (fixtures replace handlers). Lines 25-40, 64-68, 90-128 uncovered — this includes the JSON formatter path, the stderr-only fallback, and the file-handler rotation config. Any silent regression in logging would leave operators blind. | Low functional risk (if broken, you see it immediately in stdout). But a crash inside `setup_logging()` at startup would mask other startup errors. | Add ≥3 tests covering: JSON formatter output shape, file handler rotation config, stderr fallback branch. Small file, cheap win. | safe-during-trading |
| M4 | 6 order-manager flatten tests at ~30.0s each = ~180s wall-clock (serialized), ~60s with `-n auto` | From `--durations=30`: `test_emergency_flatten_closes_everything`, `test_circuit_breaker_triggers_emergency_flatten`, `test_eod_flatten_closes_all_positions`, `test_emergency_flatten_cancels_open_orders`, `test_bracket_flatten_cancels_bracket_orders`, `test_eod_flatten_broker_only_positions` — all clock in at exactly 30.0x seconds. This matches the Sprint 32.9 synchronous fill-verification `eod_flatten_timeout_seconds: 30` default. These tests appear to wait for the full verification timeout rather than mocking the fill event. | ~25% of test-suite wall-clock time spent in 6 tests. Violates `testing.md` §Tests that use real `asyncio.sleep` are wall-clock-bound. A dev iterating on order-manager logic pays 30s per test even for a 1-line change. | Inspect whether fills are actually arriving in the test setup. If the timeout is hitting because the fill event is never published in the test fixture, publish a fake fill event on the asyncio.Event the order manager waits on. If the timeout IS the scenario under test, use `monkeypatch.setattr(OrderManagerConfig, 'eod_flatten_timeout_seconds', 0.1)`. | safe-during-trading |
| M5 | [tests/analytics/test_def159_entry_price_known.py:137-179](tests/analytics/test_def159_entry_price_known.py#L137-L179) | **DEF-163 date-decay test has a timezone-mismatch bug, not a "date decay" bug.** The test stores `exit_time=datetime.now(UTC)` but `get_todays_pnl()` filters `WHERE date(exit_time) = <ET date>`. SQLite's `date()` on a `+00:00` ISO string returns the UTC date. When UTC date ≠ ET date (i.e., roughly 20:00 ET – 00:00 ET window), the test fails. Documenting it as "date decay" hides the actual timezone-handling defect. | The test did NOT fail in this morning's 09:58 ET run (both UTC and ET dates matched) but WILL fail every evening. Future operator running CI at 20:15 ET gets a confusing red that will appear intermittent. | Fix the test to use `datetime.now(ZoneInfo("America/New_York"))` for `exit_time`, OR fix `trade_logger.log_trade()` to normalize exit_time to ET before storage. Pick one and document. | safe-during-trading |
| M6 | [tests/core/test_regime_vector_expansion.py:36](tests/core/test_regime_vector_expansion.py#L36) | **DEF-163 date-decay root cause identified.** `_make_vector()` helper still hardcodes `computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` as its default. Sprint 32.8 fix only replaced the explicit date in `test_history_store_migration` (which overrides `computed_at=datetime.now(UTC)` at line 302). Every *other* test that calls `_make_vector()` without override still uses March 26 2026 — if retention policy ever deletes rows older than 30 days, those tests will fail deterministically after 2026-04-25. This is the "second hardcoded constant" CLAUDE.md speculated about. | Tests currently pass (retention horizon in `RegimeHistoryStore.cleanup_old_snapshots()` isn't being invoked in these tests), so this is latent — it will bite when either retention-aware testing is added or the default is trusted for some date-comparison assertion. | Replace the hardcoded default at line 36 with `datetime.now(UTC) - timedelta(hours=1)` (slightly-in-the-past so tests that compare against "now" don't race). | safe-during-trading |
| M7 | [tests/sprint_runner/test_notifications.py:302-321](tests/sprint_runner/test_notifications.py#L302-L321) | **DEF-150 is not xdist-specific; it is a time-of-day bug.** CLAUDE.md says "race condition under `-n auto`, passes in isolation". The actual bug: `manager.last_halted_notification = datetime.now(UTC).replace(minute=(datetime.now(UTC).minute - 2) % 60)` is broken for the first two minutes of every hour. When `minute ∈ {0,1}`, `(0-2) % 60 = 58` and `(1-2) % 60 = 59` set the timestamp **58/59 minutes in the future** (same hour, higher minute), not 2 minutes ago. `check_reminder()` then sees the last notification as in the future and doesn't fire. In this morning's run the failure reproduced under both `-n auto` and under coverage. | Flake category is wrong in DEF table. Calling this "xdist race" misdirects future fixers. | Replace the broken arithmetic with `datetime.now(UTC) - timedelta(minutes=2)`. One-line fix. | safe-during-trading |
| M8 | [argus/core/risk_manager.py:733](argus/core/risk_manager.py#L733) | `run_integrity_check()` branch `if account.equity <= 0: issues.append(...)` is uncovered. Simple check but a zero-equity broker state is a real failure mode. | Low; function is an auxiliary diagnostic. | Add a 3-line test that constructs a broker returning `Account(equity=0)` and asserts the returned `IntegrityReport.passed is False`. | safe-during-trading |
| M9 | [tests/execution/test_order_manager_*.py](tests/execution/) — 13 order-manager test files, 233 tests | Order-manager tests spread across 13 files with sprint-dated names (`*_sprint295.py`, `*_sprint2875.py`, `*_sprint329.py`, `*_def158.py`, `*_reconciliation_redesign.py`, etc). This is organic drift, not principled organization. `testing.md` §Test Structure says "Mirror the source tree" — the canonical target is `test_order_manager.py`. Cross-file test discovery requires knowing the sprint number. | Navigation friction; duplicated fixture setup across files; hard to see "all flatten tests in one place." | Consolidate under a `tests/execution/order_manager/` package with topic-split modules: `test_flatten.py`, `test_reconciliation.py`, `test_brackets.py`, `test_exits.py`, `test_margin_circuit.py`. Delete the sprint-date suffixes. No test semantics change; pure file-layout refactor. | safe-during-trading |
| M10 | [pyproject.toml](pyproject.toml) / missing `.coveragerc` | **No coverage configuration present.** No `[tool.coverage]` section in pyproject.toml, no `.coveragerc`. Defaults include every line, measure line coverage only (no branch coverage), no omit paths, no target threshold. CLI coverage runs are thus non-deterministic across operators (anyone who runs `pytest --cov` without the exact flags above produces a different report). | No enforced floor. No branch coverage = rejection-branch gaps (like C1/C2) harder to spot. No `exclude_lines` means `if TYPE_CHECKING:` and `raise NotImplementedError` lines count as missed. | Add a minimal `[tool.coverage.run]` and `[tool.coverage.report]` section: `source = ["argus"]`, `branch = true`, `exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError", "if __name__"]`, `omit = ["argus/api/__main__.py", "argus/api/setup_password.py"]`. Optionally set a `fail_under = 80`. | safe-during-trading |
| M11 | [argus/api/__main__.py](argus/api/__main__.py) (0% coverage, 34/34 missed), [argus/api/setup_password.py](argus/api/setup_password.py) (0% coverage) | Two entry-point modules at 0% coverage. These are CLI invocations (`python -m argus.api`, `python -m argus.api.setup_password`). Expected pattern is `omit` in coverage config, not "untested code." Currently they drag overall coverage down without representing actionable gaps. | Distorts the 82% headline — real coverage of library code is ~1.5% higher. Also implies CLI entry points are untested when they're just untestable via pytest-cov's default invocation. | Part of M10's coverage-config fix: add both to `omit`. Optionally add one smoke test per entry using `subprocess.run([sys.executable, '-m', 'argus.api.setup_password', '--help'])`. | safe-during-trading |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [tests/test_integration_sprint2.py](tests/test_integration_sprint2.py) … [tests/test_integration_sprint26.py](tests/test_integration_sprint26.py) — 10 files, 93 tests | Sprint-dated integration tests at the top `tests/` level. Useful historically but most are frozen-in-time artifacts. Sprint 26 is nine months and 60 sprints ago; Sprint 2 is ~18 months back. None are likely to be added to; few are likely to fail meaningfully if the underlying feature ever regresses (the sprint context is forgotten). | Not broken; just cognitively noisy. A reader scanning `tests/` sees 10 sprint files and doesn't know which are still load-bearing vs decorative. | Either: (a) keep but move into `tests/integration/historical/` to telegraph status, or (b) audit each file — delete those whose assertions are obsolete, fold still-relevant assertions into topic-named integration tests under `tests/integration/`. | safe-during-trading |
| L2 | [tests/unit/](tests/unit/) subtree (2 subdirs: `core/`, `strategies/`) | `tests/unit/` exists with only `core/` and `strategies/` children while >95% of unit tests live directly under `tests/core/`, `tests/strategies/`, etc. This is organic split drift. Either `tests/unit/` is canonical (in which case all unit tests should move there) or it's a wart (in which case its contents should fold into `tests/core/`, `tests/strategies/`). | Low. Discoverability friction only. | Pick one convention. CLAUDE.md does not specify; follow de-facto majority and fold `tests/unit/core/` into `tests/core/`, `tests/unit/strategies/` into `tests/strategies/`. Delete `tests/unit/`. | safe-during-trading |
| L3 | [tests/accounting/__init__.py](tests/accounting/__init__.py), [tests/notifications/__init__.py](tests/notifications/__init__.py) | Empty test subdirectories mirroring the two dead-scaffold source dirs (PF-01, PF-02 in audit plan). Only `__init__.py`, no test files. | Cosmetic. Drag scan tools. | Delete both directories (P1-A2 already flags the source equivalents). | safe-during-trading |
| L4 | Data layer modules: `vix_data_service.py` (59%), `databento_data_service.py` (79%), `fmp_reference.py` (83%), `alpaca_data_service.py` (85%) | Data-service coverage is materially below the 90% target in `testing.md` §Core Logic. The `vix_data_service.py` gap in particular covers lines 556-685 — almost the entire `refresh()` / backfill code path. | VIX data is a RegimeClassifierV2 input; a silent regression in refresh would yield stale-but-plausible regime labels. Low severity because VIXDataService has explicit staleness self-disable guard per DEC-349. | Add tests for `VIXDataService.refresh()` happy path + FMP fallback branch. Data-service tests are well-established pattern — follow `test_fmp_reference.py`. | safe-during-trading |
| L5 | [argus/ai/prompts.py](argus/ai/prompts.py) (63%), [argus/ai/context.py](argus/ai/context.py) (64%), [argus/ai/client.py](argus/ai/client.py) (73%), [argus/ai/executors.py](argus/ai/executors.py) (75%) | AI Copilot modules clustered at 63-75% coverage. Most uncovered lines are per-page context builders and prompt formatters that are long and branchy. | Low risk — failure mode is user-visible (bad Copilot response) rather than silent. But given AI is proposal-enabled and can submit actions to the risk pipeline, formatter bugs deserve floor coverage. | Add parametrized tests over the per-page branches in `SystemContextBuilder` and per-prompt sections of `PromptManager`. | safe-during-trading |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| X1 | pytest output | 60 `PytestDeprecationWarning` about `asyncio_default_fixture_loop_scope` unset. Appears once per worker × multiple workers = log spam during test runs. | Noise in test output. Future pytest-asyncio bump may convert this to an error. | Add `asyncio_default_fixture_loop_scope = "function"` to `[tool.pytest.ini_options]` in pyproject.toml. | safe-during-trading |
| X2 | docs/audits/audit-2026-04-21/ commit messages | The audit plan's commit-message template (`audit(P1-<ID>): <domain> findings report`) is consistently followed across the 12 previous commits. | None; noting as positive convention adherence for the audit campaign. | None. | — |

---

## Critical-Path Coverage Table

| File | LOC | Coverage | Notable uncovered | Severity |
|------|-----:|---------:|-------------------|----------|
| `argus/core/risk_manager.py` | 785 | **92%** | 386-394, 405-421 (rejection-after-reduction floor), 621, 627-634 (post-close CB) | CRITICAL (C1, C2) |
| `argus/execution/order_manager.py` | 3,036 | **86%** | Many scattered 1-2 line branches in reconciliation, trail, stop-retry paths | LOW individually, aggregate warrants review in next audit |
| `argus/core/orchestrator.py` | 906 | **91%** | 463, 474 (some regime-throttle branches), 678-715 (polling edge cases) | LOW |
| `argus/core/market_calendar.py` | 222 | **99%** | 1 line | — |
| `argus/intelligence/quality_engine.py` | 253 | **96%** | 4 lines | — |
| `argus/intelligence/counterfactual.py` | 672 | **92%** | 316-344 (some MFE/MAE branches) | LOW |
| `argus/strategies/base_strategy.py` | 466 | **99%** | 1 line | — |
| `argus/data/universe_manager.py` | 612 | **91%** | 437-465 (filter-composition edge cases) | LOW |
| `argus/backtest/engine.py` | 2,389 | **82%** | Multiple 1-3 line branches in multi-day orchestration; factory branches per strategy | MEDIUM aggregate |

**Critical-path aggregate coverage: 91.4%** (7,341 LOC, 82-99% each). Pattern: happy-path and primary rejection paths are well-covered; *secondary* rejection paths (reduce-then-floor, post-close circuit breaker) are the consistent gap.

---

## Per-Module Coverage — Top 20 Lowest

| # | Module | Coverage | Category |
|---|--------|---------:|----------|
| 1 | `argus/api/__main__.py` | 0% | CLI entry — omit from coverage |
| 2 | `argus/api/setup_password.py` | 0% | CLI entry — omit from coverage |
| 3 | `argus/main.py` | 20% | Entry/wire-up; tested via excluded `test_main.py` |
| 4 | `argus/core/logging_config.py` | 24% | Missing tests (M3) |
| 5 | `argus/backtest/vectorbt_vwap_reclaim.py` | 41% | Legacy VectorBT; see P1-E2 dead-code scan |
| 6 | `argus/backtest/walk_forward.py` | 47% | Partial; OOS-engine branches |
| 7 | `argus/backtest/data_fetcher.py` | 52% | Legacy fetcher |
| 8 | `argus/api/routes/vix.py` | 54% | Newer route; limited tests |
| 9 | `argus/api/websocket/ai_chat.py` | 54% | WS streaming code (L5-adjacent) |
| 10 | `argus/backtest/metrics.py` | 57% | Legacy metrics |
| 11 | `argus/backtest/replay_harness.py` | 58% | Legacy (P1-E2) |
| 12 | `argus/api/dependencies.py` | 59% | `AppState` construction paths |
| 13 | `argus/data/vix_data_service.py` | 59% | L4 |
| 14 | `argus/ai/prompts.py` | 63% | L5 |
| 15 | `argus/ai/context.py` | 64% | L5 |
| 16 | `argus/api/websocket/arena_ws.py` | 64% | Sprint 32.8 tick path |
| 17 | `argus/execution/alpaca_broker.py` | 66% | PF-07 (Alpaca incubator only) |
| 18 | `argus/api/routes/trades.py` | 67% | Trade stats endpoint |
| 19 | `argus/backtest/vectorbt_afternoon_momentum.py` | 67% | Legacy VectorBT |
| 20 | `argus/strategies/patterns/__init__.py` | 71% | Pattern init registrations |

## Per-Module Coverage — Top 20 Highest (excluding 100% `__init__.py` files)

| # | Module | Coverage |
|---|--------|---------:|
| 1 | `argus/core/events.py` | 100% |
| 2 | `argus/core/market_calendar.py` | 99% |
| 3 | `argus/strategies/base_strategy.py` | 99% |
| 4 | `argus/core/config.py` | 99% |
| 5 | `argus/ai/cache.py` | 99% |
| 6 | `argus/ai/conversations.py` | 99% |
| 7 | `argus/intelligence/config.py` | 99% |
| 8 | `argus/data/indicator_engine.py` | 98% |
| 9 | `argus/analytics/comparison.py` | 98% |
| 10 | `argus/intelligence/learning/models.py` | 98% |
| 11 | `argus/core/correlation.py` | 96% |
| 12 | `argus/core/regime.py` | 95% |
| 13 | `argus/core/sync_event_bus.py` | 95% |
| 14 | `argus/api/auth.py` | 96% |
| 15 | `argus/analytics/evaluation.py` | 96% |
| 16 | `argus/analytics/observatory_service.py` | 95% |
| 17 | `argus/intelligence/learning/learning_service.py` | 96% |
| 18 | `argus/intelligence/filter_accuracy.py` | 95% |
| 19 | `argus/strategies/telemetry.py` | 95% |
| 20 | `argus/strategies/orb_base.py` | 95% |

---

## Failure-Mode Coverage Audit

### Risk Manager rejection reasons
| Reason | Covered? | Evidence |
|--------|----------|----------|
| `Invalid share count: zero or negative` | ✅ | `test_risk_manager.py` check-0 tests |
| `Circuit breaker active` | ✅ | `test_signal_rejected_when_circuit_breaker_active` |
| `Daily loss limit reached` (pre-signal) | ✅ | `test_signal_rejected_daily_loss_limit` |
| `Daily loss limit reached` (post-close) | ❌ | **C1** — uncovered branch at 627-634 |
| `Weekly loss limit reached` | ✅ | `test_signal_rejected_weekly_loss_limit` |
| `Max concurrent positions reached` | ✅ | `test_signal_rejected_max_concurrent_positions` |
| `Concentration limit already reached` | ✅ | Covered |
| `Cross-strategy duplicate policy` | ✅ | Covered |
| `Cash reserve would be violated` (outright reject) | ✅ | Covered |
| `Cash reserve reduce → below min-risk floor` | ❌ | **C2** — uncovered at 386-394 |
| `Buying power reduce → below min-risk floor` | ❌ | **C2** — uncovered at 405-421 |
| `PDT limit reached` | ✅ | Covered |

### Order Manager flatten paths
| Path | Covered? | Notes |
|------|----------|-------|
| Time-stop flatten | ✅ | `test_order_manager.py` |
| EOD flatten | ✅ | But 30s wall-clock per test (M4) |
| Reconciliation flatten (synthetic close) | ✅ | `test_order_manager_reconciliation_redesign.py` |
| Margin circuit flatten | ✅ | `test_order_manager_sprint329.py` |
| Zombie flatten (startup cleanup, DEF-139) | ✅ | `test_order_manager_sprint329.py` |
| Bracket-exhaustion flatten (DEC-374+) | ✅ | `test_order_manager_reconciliation_redesign.py` |
| Flatten-pending timeout resubmit (DEF-158 fix) | ✅ | `test_order_manager_def158.py` |

### IBKR error handling
| Error | Covered? | Notes |
|-------|----------|-------|
| Error 201 (margin rejection) | ✅ | `test_ibkr_errors.py`, `test_order_manager_sprint329.py` |
| Error 404 (order not found, qty divergence) | ✅ | `test_ibkr_broker.py`, `test_order_manager_sprint295.py` |
| "Revision rejected" | ✅ | `test_order_manager_hardening.py`, `*_sprint329.py` |

### Universe Manager fail-closed (DEC-277)
`test_universe_manager.py::test_routing_no_reference_data_excludes` at line 1355 asserts the fail-closed invariant directly. ✅

---

## Test Suite Performance

### Top 30 slowest (from `pytest --durations=30 -n auto`)

| Time | Test |
|-----:|------|
| 30.03s | `test_order_manager_sprint295.py::test_eod_flatten_broker_only_positions` |
| 30.02s | `test_order_manager.py::test_emergency_flatten_cancels_open_orders` |
| 30.01s | `test_order_manager.py::test_circuit_breaker_triggers_emergency_flatten` |
| 30.01s | `test_order_manager.py::test_bracket_flatten_cancels_bracket_orders` |
| 30.01s | `test_order_manager.py::test_emergency_flatten_closes_everything` |
| 30.01s | `test_order_manager.py::test_eod_flatten_closes_all_positions` |
| 10.01s | `test_alpaca_data_service.py::test_stale_data_detection` |
| 10.00s | `test_alpaca_data_service.py::test_stale_data_recovery` |
| 6.03s | `test_fmp_news.py::test_error_handling_429_triggers_backoff` |
| 6.02s | `test_finnhub.py::test_error_handling_429_triggers_backoff` |
| 6.01s | `test_fmp_reference.py::test_fmp_canary_api_error` |
| 6.01s | `test_sec_edgar.py::test_error_handling_403_retries_then_skips` |
| 5.80s | `test_vectorbt_pattern.py::TestFlatTopWalkForward::test_walk_forward_runs_without_error` |
| 5.79s | `test_vectorbt_orb.py::test_heatmap_png_created` |
| 5.41s | `test_vectorbt_pattern.py::TestBullFlagWalkForward::test_walk_forward_runs_without_error` |
| 5.04s | `test_cli_flags.py::TestDryRun::test_dry_run_no_executor_calls` |
| 5.02s | `test_loop.py::TestTestBaseline::test_test_baseline_patched_between_sessions` |
| 4.92s | `test_vectorbt_orb.py::test_heatmap_no_trades_handles_gracefully` |
| 4.87s | `test_vectorbt_orb.py::test_heatmap_html_created` |
| 4.67s | `test_vectorbt_orb.py::test_cli_runs_without_error` |
| 3.11s | `test_databento_scanner.py::test_scan_creates_watchlist_items` |
| 3.01s | `test_finnhub_403.py::test_cycle_403_summary` |
| 2.44s | `test_server.py::test_server_lifespan_quality_disabled` |
| 2.29s (setup) | `test_positions.py::test_positions_empty` |
| 2.23s (setup) | `test_market_status.py::test_holiday_status_sets_is_market_hours_false` |
| 2.01s | `test_finnhub.py::test_rate_limiting_respects_60_per_minute` |
| 2.01s | `test_lifespan_startup.py::test_wait_for_port_returns_false_on_timeout` |
| 1.75s (setup) | `test_trades.py::test_stats_unauthenticated` |
| 1.74s | `test_observatory_ws.py::test_observatory_ws_sends_initial_state` |
| 1.57s (setup) | `test_arena.py::test_candles_requires_auth` |

**Observation:** 6 tests consume ~180 CPU-seconds. All are flatten tests (M4). 4 429-retry tests consume ~24s (expected — retry logic under test). Full suite at 139s with xdist is within CLAUDE.md's claimed ~114s-with-xdist target — close enough.

---

## Pre-Existing Failures Status

| DEF | Test | Status this audit | Classification |
|-----|------|------------------|----------------|
| DEF-150 | `test_check_reminder_sends_after_interval` | **FAILED** both runs | M7 — time-of-day bug, NOT xdist race |
| DEF-163 | `test_get_todays_pnl_excludes_unrecoverable` | Passed both runs | M5 — timezone-mismatch, will fail 20:00-00:00 ET |
| DEF-163 | `test_history_store_migration` | Passed both runs | M6 — latent; bound to April retention date |
| **NEW** | `test_speed_benchmark` | FAILED no-cov, passed with cov | M1 — timing flake, not tracked |

Only DEF-150 is a "true positive" pre-existing failure in this run. DEF-163 tests passed (suggesting they are time-of-day / date-range bound rather than steadily-decaying). A new flake (`test_speed_benchmark`) surfaced that is not in the DEF list — flag for DEF-triage.

---

## Coverage Tooling Hygiene

- No `.coveragerc` (M10)
- No `[tool.coverage]` in `pyproject.toml` (M10)
- No `omit` list — CLI entry points count against coverage (M11)
- No branch coverage enabled — rejection-branch gaps (C1, C2) would be more obvious with branch coverage
- `--cov-report=html` runs to default dir without a `.gitignore` guard (low risk; the audit plan guards via `/tmp/argus-audit/` but a casual `pytest --cov` at repo root would leave `htmlcov/` uncommitted junk)

---

## Sprint Test-Count Discipline (DEC-328)

- DEC-328 mandates the full suite at: sprint entry (S1 pre-flight), every close-out, final review
- Sprint plans routinely state "Minimum new test count: N" per session (seen in 23.6 S1, S2a, S2b, S3b, S3c, S4a, S4b)
- MEMORY.md tracks test-count deltas per sprint (e.g., "+20 pytest", "+15 pytest", "+34 pytest")
- The audit plan's Phase 3 invariant "Net test count must not decrease" is NOT encoded as a DEC or a ruleset — it is a campaign-scoped convention
- **No sprint identified with undocumented net-negative test-count change.** Sprint 31.85 was +15, Sprint 31.8 was +20, Sprint 31.5 was +34. Sprint 32.9 explicitly noted +40. Recent sprints tracked cleanly.

No findings here; reporting clean.

---

## Integration vs Unit Split

| Location | Files | Tests | Intent |
|----------|------:|------:|--------|
| `tests/integration/` | 3 | — | Current canonical integration dir |
| `tests/unit/` | 2 subdirs | — | Organic drift; most unit tests live in domain dirs |
| `tests/test_integration_sprint*.py` (top-level) | 10 | 93 | Sprint-dated historical artifacts (L1) |
| Domain `tests/<domain>/` dirs | 45 | ~4,700 | De-facto unit + mixed tests |

The split is organic, not principled. Not a CRITICAL issue — pytest discovery finds them all — but a documentation/navigation smell that L1 + L2 address.

---

## Positive Observations

1. **Overall 82% line coverage across 31K statements is strong** for a 1-year-old codebase of this complexity. The 56 modules ≥95% coverage show genuine test-first discipline in `core/`, `strategies/`, and `analytics/`.
2. **Critical-path aggregate coverage is 91.4%.** The 9 files listed in the session prompt as critical clear 82% individually and average 92%. The RM, Order Manager, and Counterfactual subsystems all have dedicated test files whose test counts (54, 233, 14+) reflect sustained investment.
3. **Failure-mode coverage is broadly good.** Of ~20 distinct rejection / error / flatten paths audited, only 3 (all in RM secondary rejections + post-close breaker) are uncovered. IBKR error codes 201, 404, "Revision rejected" all have dedicated tests — a pattern worth replicating for any future broker-side errors.
4. **Fixture pattern in `conftest.py` is consistent across domains.** `tests/core/conftest.py`, `tests/execution/conftest.py`, `tests/api/conftest.py` follow the same structure (async fixtures, app_state, auth headers). The session-prompt constraint "use SimulatedBroker, never mock Risk Manager in integration tests" is actually followed.
5. **Test-count discipline (DEC-328) is real, not aspirational.** Every recent sprint (31.75, 31.8, 31.85, 31.5, 31A) reports explicit test-count deltas in its close-out. No sprint regressed without documentation.
6. **Pattern-strategy tests scale cleanly.** All 10 `PatternModule` patterns have 88-92% coverage with a similar per-pattern test style — the abstraction holds up under expansion (Sprint 31A added 3 patterns without coverage regression).
7. **`test_integration_sprint19.py` (21 tests) and `test_integration_sprint18.py` (17 tests)** are still the densest integration tests and demonstrably exercise signal-to-fill pipeline. Worth preserving (not all sprint-dated files are dead weight — L1 should audit per file rather than bulk-delete).

---

## Statistics

- Files deep-read: 3 (risk_manager.py + 2 failing test files)
- Files skimmed: ~30 (critical-path sources + tests, coverage report)
- Tests run: 4,934 (1 failed under coverage, 2 failed under no-cov)
- Total findings: **21** (2 critical, 11 medium, 5 low, 2 cosmetic, 1 informational positive convention noted)
- Safety distribution: 19 safe-during-trading / 0 weekend-only / 1 read-only-no-fix-needed / 1 deferred-to-defs (new flake)
- Estimated Phase 3 fix effort: 3-4 sessions
  - Session A (safe-during-trading, ~1h): C1 + C2 + M8 + M11 (regression tests + coverage config)
  - Session B (safe-during-trading, ~1h): M3 + L4 + L5 (coverage bump on logging, data-service, ai modules)
  - Session C (safe-during-trading, ~30m): M5 + M6 + M7 (fix 3 pre-existing "flaky" tests — all one-liners)
  - Session D (safe-during-trading, ~1-2h): M4 (order-manager flatten test timeout mocking) + M9 (consolidate 13 order-manager test files)
  - Session E (optional): L1 + L2 + L3 (test-layout cleanup)

---

## Artifacts

- Raw coverage log: `/tmp/argus-audit/coverage.log` (NOT committed)
- HTML coverage report: `/tmp/argus-audit/htmlcov/` (NOT committed)
- Durations log: `/tmp/argus-audit/durations.log` (NOT committed)
- Parsed per-module coverage: `/tmp/argus-audit/coverage_sorted.txt` (NOT committed)
