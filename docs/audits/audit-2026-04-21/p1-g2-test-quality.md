# Audit: Test Quality (Sampling)
**Session:** P1-G2
**Date:** 2026-04-21
**Scope:** Qualitative sampling across 321 pytest files — 33 files deep-read across 10 domains, cross-checked against P1-G1 coverage report and `.claude/rules/testing.md`.
**Files examined:** 33 deep / ~40 skimmed (for grep/corroboration)

Where P1-G1 answered "does it cover the path?", this session answers "is the test itself any good?" Findings are confirmations/refinements of G1 or net-new quality flags.

> **FIX-09-backtest-engine resolution summary (2026-04-22) — backtest-related P1-G2 findings only:**
>
> | Finding | Status |
> |---------|--------|
> | M2 (P1-G2-M02) — `test_divergence_documented` asserts nothing | **RESOLVED FIX-09-backtest-engine** (replaced `assert True` with structural `isinstance(BacktestEngine, type)` + `isinstance(ReplayHarness, type)` assertion — behavioral divergence between engines is documented in `.claude/rules/backtesting.md` and exercised by the functional-equivalence tests in the same file) |
> | M3 (P1-G2-M03) — `test_speed_benchmark` tautological + flaky | **RESOLVED FIX-09-backtest-engine** (deleted; replaced with `test_backtest_and_replay_produce_equivalent_results` — same-sign P&L + ≤20% trade-count divergence on identical mocked fixtures; mirrors the existing `test_equivalence_*` pattern in the same file) |

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [tests/strategies/test_shadow_mode.py:83-147](tests/strategies/test_shadow_mode.py#L83-L147) | **`_build_system()` calls `object.__new__(ArgusSystem)` and manually assigns 15+ private attributes.** The test bypasses `ArgusSystem.__init__` entirely, then hand-rolls an in-memory system via `MagicMock` assignments to `_event_bus`, `_counterfactual_enabled`, `_orchestrator`, `_config`, `_quality_engine`, `_position_sizer`, `_broker`, `_risk_manager`, `_grade_meets_minimum`, etc. A silent regression in `ArgusSystem.__init__` wiring (e.g., a new required field, an order change between `_orchestrator` and `_counterfactual_enabled` being set) would leave this test **green** despite live-system breakage. The pattern also couples the test to private attribute names: any rename of `_counterfactual_enabled → _cf_enabled` breaks the test without changing `_process_signal` behavior. | Safety-critical: shadow-mode routing is the execution path for counterfactual tracking and affects live signal dispatch. A false-green here means shadow routing can silently regress between releases. Pattern is used across 13 test classes in this file. | Refactor to construct `ArgusSystem` via a real but minimal `__init__`, or extract `_process_signal` into a standalone service class with a minimal dependency interface. If neither is feasible, at minimum add an explicit `assert hasattr(system, attr)` guard at top of `_build_system()` for every attribute it sets, so an `__init__` rename surfaces a loud import-time error rather than a silent tautology. | safe-during-trading |

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [tests/core/test_regime_vector_expansion.py:236-314](tests/core/test_regime_vector_expansion.py#L236-L314) | **`test_history_store_migration` is NOT an xdist race — it is a UTC-vs-ET timezone boundary bug.** See full characterization in §7 below. The test captures `old_date`/`new_date` using `datetime.now(UTC)` (lines 245, 247) but `RegimeHistoryStore.record()` internally computes `trading_date` using `.astimezone(_ET)` at [regime_history.py:128-130](argus/core/regime_history.py#L128-L130). During the ~4h window when ET date ≠ UTC date (8 PM ET EDT / 7 PM ET EST until midnight UTC), the test fails deterministically: (a) the query for "UTC yesterday" matches both the manually-inserted old row AND the newly-recorded row because ET-today equals UTC-yesterday, (b) the query for "UTC today" matches zero rows because no record has trading_date = ET-tomorrow. Cleanup tracker #4 (Sprint 31.75) and multiple sprint close-outs describe this as an "xdist race"; it is not — it's timezone drift that presents as flake because different test runs hit the boundary window at different times. | Mislabeled bug category sends future fixers on a wild goose chase for parallelism issues. Also: this test currently guards the RegimeHistoryStore migration path from Sprint 27.9 — letting it rot means the migration becomes untested. Reconfirmed pre-existing during Sprint 31.85. | Replace `datetime.now(UTC)` at lines 245, 247, 302 with `datetime.now(UTC).astimezone(ZoneInfo("America/New_York"))` — then the captured `old_date`/`new_date` will match the store's internal ET-based trading_date and the test will pass deterministically regardless of time-of-day. Also update CLAUDE.md Known Issues entry: re-classify from "xdist race" to "timezone boundary". | safe-during-trading |
| M2 | [tests/backtest/test_walk_forward_engine.py:530-550](tests/backtest/test_walk_forward_engine.py#L530-L550) | **`test_divergence_documented` literally asserts nothing.** The body is `assert True, "<long doc message>"` — the test name implies behavior verification but the code is a docstring container. Silent failure mode #4.2 from the prompt: "Tests asserting nothing after setup (setup runs, no assertion — effectively a smoke test mislabeled as a unit test)." A reader scanning the test file sees `test_divergence_documented` in green and assumes coverage; there is none. | Produces false confidence. The comment explicitly calls this out ("# This test is intentionally documentary — it always passes"), but that intent is hidden inside the function — the pytest collector/reporter treats it as a real test. | Either (a) delete the test and move the docstring into a module-level docstring or `docs/backtesting.md` block, or (b) replace with an `assert isinstance(BacktestEngine, type)` or similar structural check that at least fails if the documented class goes away, or (c) promote it to a real test that runs both engines on identical bars and asserts directional agreement. | safe-during-trading |
| M3 | [tests/backtest/test_walk_forward_engine.py:558-626](tests/backtest/test_walk_forward_engine.py#L558-L626) | **`test_speed_benchmark` is tautological + flaky.** The mocks include hand-coded `asyncio.sleep(0.01)` and `asyncio.sleep(0.05)` delays; the assertion `speed_ratio >= 3.0` then measures the ratio of the mocked delays, not any production code behavior. P1-G1 M1 flagged the flake; this finding adds the tautology characterization. A refactor that replaces `BacktestEngine.run` with a genuinely slow implementation would not fail this test — it measures the mocks only. | Same as G1 M1 plus: the test cannot detect any real performance regression because the real engines are never exercised. | Replace with a functional equivalence check: run both engines over identical 5-day mocked fixtures and assert same-sign P&L and trade-count-within-20% — same assertion used at [line 514-522](tests/backtest/test_walk_forward_engine.py#L514-L522) for a related test. Delete the mocked-delay speed assertion. | safe-during-trading |
| M4 | [tests/execution/test_order_manager.py:700-752](tests/execution/test_order_manager.py#L700-L752) | **`test_emergency_flatten_*` fixtures lack a fill-event publisher — 30s wait comes from `OrderManagerConfig()` default `eod_flatten_timeout_seconds=30`.** Confirms and explains G1 M4. The test calls `order_manager.emergency_flatten()` which calls `eod_flatten()` which creates `asyncio.Event`s per symbol and does `await asyncio.wait_for(gather(...), timeout=30.0)`. The mock broker `place_order` returns `OrderStatus.PENDING` but **no test code ever sets the corresponding `_eod_flatten_events[symbol].set()` via a synthetic `OrderFilledEvent`** — so each of 6 tests waits the full 30s timeout. 180s of wall-clock is wasted per full suite run. | Confirms G1 M4 diagnosis. Adds specificity: the fix is either (a) publish a synthetic `OrderFilledEvent` after `emergency_flatten()` kicks off, or (b) override the config fixture with `eod_flatten_timeout_seconds=0.1`. | Override the shared `config` fixture for these specific tests with `OrderManagerConfig(eod_flatten_timeout_seconds=0.1)`. Alternatively, subscribe to `OrderSubmittedEvent` in the test, and publish a matching `OrderFilledEvent` synchronously. Pattern to follow: [test_order_manager_sprint329.py:320-340](tests/execution/test_order_manager_sprint329.py#L320-L340) already overrides `eod_flatten_timeout_seconds=1` or `=5` for its tests — replicate that for the `test_order_manager.py` tests. | safe-during-trading |
| M5 | [tests/data/test_alpaca_data_service.py:505-557](tests/data/test_alpaca_data_service.py#L505-L557) | **`test_stale_data_detection` and `test_stale_data_recovery` use real `asyncio.sleep(6)` against a 5-second monitor interval.** Each test is 10s wall-clock. `.claude/rules/testing.md` §Tests-that-use-real-asyncio.sleep: "If a test needs more than ~3s of real sleep, reconsider whether it can be tested at a lower level." The monitor polls every 5s (hardcoded in `_stale_data_monitor`), so a 6s sleep waits for one poll cycle. | Two 10s tests in a data-service module that is otherwise fast. G1 top-30-slowest table lists both. Unlike the flatten tests, these are testing a real behavior (monitor loop), but at the wrong level. | Refactor the monitor to accept an injected poll interval, then pass `monitor_poll_seconds=0.1` in test setup. Alternatively, test `_check_stale_once()` (a synchronous helper) rather than the full loop — removes the need to wait for `asyncio.sleep` at all. | safe-during-trading |
| M6 | [tests/core/test_risk_manager.py:289, 306, 323, 346, 423-425, 502](tests/core/test_risk_manager.py) | **11+ tests mutate RiskManager private attributes (`rm._circuit_breaker_active`, `rm._daily_realized_pnl`, `rm._weekly_realized_pnl`, `rm._pdt_tracker.record_day_trade(...)`, `rm._trades_today`).** This is brittle-setup (Q3.2) + excessive-mocking-via-backdoor (Q2.3). A refactor of RiskManager's internal state shape (e.g., `_daily_realized_pnl → _account_state.daily_pnl`) breaks every test that pokes internals without any public-API change. The tests are effectively testing a specific internal layout, not behavior. | Latent maintenance cost. Refactors to RiskManager become larger than they should because the test suite has a private-attribute coupling surface. Also makes the rejection-path tests (G1 C1/C2) harder to add cleanly — the new tests would follow the same anti-pattern. | Introduce public test-only methods or a `@classmethod` builder: `RiskManager.with_daily_pnl(-3000.0)` for test setup. Or drive state through published `PositionClosedEvent`s (which already works — see `test_position_closed_updates_daily_pnl` at [line 437](tests/core/test_risk_manager.py#L437)). Gradually migrate each `rm._foo = ...` callsite to event-driven setup. | safe-during-trading |
| M7 | [tests/strategies/test_shadow_mode.py:108](tests/strategies/test_shadow_mode.py#L108) | **Lambda-based `__eq__` monkeypatch on `MagicMock` to force specific equality outcome: `mock_config.system.broker_source.__eq__ = lambda self, other: False`.** This is a subtle form of tautology: the test is controlling a comparison result rather than using a real `BrokerSource` enum value. If `_process_signal` logic is refactored to check `broker_source is BrokerSource.SIMULATED`, the lambda will silently not be triggered and the test may pass or fail unpredictably. | The pattern obscures what the test is actually asserting. G1 didn't catch this because it's coupled to the C1 `_build_system()` pattern. | Replace with a real `BrokerSource.DATABENTO` (or equivalent live enum value) instead of a MagicMock lambda. | safe-during-trading |
| M8 | [tests/api/test_observatory_ws.py:210, 232, 396, 443, 555, 610](tests/api/test_observatory_ws.py) [tests/api/test_arena_ws.py:76, 94](tests/api/test_arena_ws.py) | **8 WebSocket tests use `except Exception: pass` to swallow expected `WebSocketDisconnect`.** Silent-failure category Q4.1. If the server changes to raise a different exception (e.g., a new `WebSocketError` subclass), these tests still pass because any exception is swallowed. The idiomatic replacement is `with pytest.raises(WebSocketDisconnect):`. | The tests still exercise the right code path, but their guard is too loose. A regression from `close(code=4001)` to `close(code=1000)` would not surface — the broad except swallows it. | Replace each `try/except Exception: pass` with explicit `with pytest.raises((WebSocketDisconnect, <specific exception>)):` — Starlette raises `WebSocketDisconnect` on client-side `close()` and `RuntimeError` in a handful of cases. Enumerate the two and fail on anything else. | safe-during-trading |
| M9 | [tests/](tests/) class-vs-function mix | **Class-based vs function-based test organization is inconsistent across the suite.** Class-based: `test_clock.py`, `test_risk_manager.py`, `test_event_bus.py`, `test_regime_vector_expansion.py`, `test_shadow_mode.py`, `test_position_sizer.py`, `test_tools.py`, `test_auth.py`, `test_trades.py`, `test_trade_logger.py`, `test_alpaca_data_service.py`. Function-based: `test_order_manager.py`, `test_engine.py`, `test_def159_entry_price_known.py`, `test_quality_engine.py`. `.claude/rules/testing.md` does not mandate either style, so this is organic drift. Complicates navigation and test discovery. | Discoverability friction only. Not a correctness risk. `testing.md` could pick a convention and apply it going forward. | Either (a) pick class-based as the canonical form (matches the majority) and leave existing function-based files alone until they're touched next, or (b) amend `testing.md` to say "either is acceptable" to codify the status quo. Do NOT bulk-rewrite — churn for churn's sake. Codify direction so new tests align. | safe-during-trading |
| M10 | [tests/test_integration_sprint2.py](tests/test_integration_sprint2.py), [tests/test_integration_sprint3.py](tests/test_integration_sprint3.py), [tests/test_integration_sprint4a.py](tests/test_integration_sprint4a.py), [tests/test_integration_sprint4b.py](tests/test_integration_sprint4b.py), [tests/test_integration_sprint5.py](tests/test_integration_sprint5.py), [tests/test_integration_sprint13.py](tests/test_integration_sprint13.py) — 6 historical files | **Sprint 2-13 integration tests are archaeological artifacts.** Read Sprint 2 (345 lines, pre-Alpaca broker work), Sprint 3 (435 lines, cash-reserve), Sprint 4a/4b (643 lines total, Orchestrator), Sprint 5 (325 lines, Phase 1 handoff), Sprint 13 (178 lines, API dependencies). These tests assert on behavior from 1-year-old architecture decisions (DEC-027, DEC-037 era). Sprint 2 still imports `Trade`, `Order`, `Side` from `argus.models.trading` — still works, but the specific shapes tested are subsumed by later, denser tests. Per-file triage below (§7 Historical Integration Tests). | Not broken; the tests pass. But a reader opening `tests/test_integration_sprint4a.py` has no way to know whether it's still a load-bearing regression guard or a decorative artifact. | Triage per file (table in §7). Keep sprint-18/19/20/26 (validate current behavior); deprecate sprint-2/3/4a/4b/5 (move to `tests/integration/historical/` with a note in a README); delete sprint-13 only after confirming its 5 tests aren't unique coverage. | safe-during-trading |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [tests/core/test_regime_vector_expansion.py:36](tests/core/test_regime_vector_expansion.py#L36) | **`_make_vector()` hardcodes `computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` as default** — confirms G1 M6. Not every caller passes `computed_at=` override, so tests like `test_construction_with_all_fields` store March 26 2026 as their timestamp. Latent until a retention cleanup is added or a test starts asserting on "recent" timestamps. | Latent; will bite when retention-aware tests are written. | Replace with `datetime.now(UTC) - timedelta(hours=1)` (slightly-in-the-past lookback so any "now"-based assertion stays valid). | safe-during-trading |
| L2 | [tests/strategies/test_orb_breakout.py:16-53](tests/strategies/test_orb_breakout.py#L16-L53) | **`make_orb_config()` helper has 14 parameters, most with defaults.** Signals a missing factory fixture. 1,460 lines in this file; similar helper patterns across the strategy-tests directory. | Verbose test setup. Mostly cosmetic; tests pass. | Either (a) extract a `pytest.fixture` that yields a default-constructed `OrbBreakoutConfig` and let tests parametrize via `dataclasses.replace(config, field=new_value)`, or (b) use `pytest-factoryboy` / similar factory library. Incremental — start with one module. | safe-during-trading |
| L3 | [tests/api/conftest.py:247-486](tests/api/conftest.py#L247-L486) | **`seeded_trade_logger` inlines 15 `Trade(...)` dict-form constructors (240 lines of fixture setup).** Heavy Q3.1 duplication: each trade repeats ~14 field assignments. Refactoring a single field rename across these 15 calls is error-prone. | Mostly cosmetic; also makes the seeded-trade scenario hard to extend without editing the conftest. | Extract a `_make_trade(**overrides)` helper (analogous to patterns already used in `test_risk_manager.py`, `test_trade_logger.py`) that supplies defaults and allows per-trade overrides. Reduces to ~50 lines. | safe-during-trading |
| L4 | [tests/utils/test_log_throttle.py](tests/utils/test_log_throttle.py), [tests/api/test_lifespan_startup.py](tests/api/test_lifespan_startup.py) | **Two files use `time.sleep()` rather than `asyncio.sleep()`.** `testing.md` says "Never use `time.sleep()` — use `asyncio.sleep()`" (architecture.md). `test_log_throttle.py` tests time-based throttle behavior (legitimate use if the throttle uses wall-clock). `test_lifespan_startup.py`: need to verify. | Low; wall-clock tests are occasionally the right call. Worth confirming these are the intended exceptions. | If intentional (e.g., testing a `time.monotonic()`-based rate limiter), add a docstring explaining why. Otherwise, replace with mocked clock. | safe-during-trading |
| L5 | [tests/core/test_clock.py:14-34](tests/core/test_clock.py#L14-L34) | **`TestSystemClock.test_now_returns_current_utc_time` / `test_today_returns_current_date_in_configured_timezone` depend on real wall-clock time.** Q5.2 — depending on `datetime.now` without mocking. Low risk: the assertions are bounded (`before <= result <= after`) so timing is self-consistent. But they could fail if the system clock jumps (NTP drift, VM snapshot restore, DST boundary). | Very low. Expected to pass 99.999% of the time. Not a priority. | Accept as-is — verifying `SystemClock` actually returns system time is a legitimate test. | read-only-no-fix-needed |
| L6 | [tests/intelligence/test_startup.py](tests/intelligence/test_startup.py) | **9 `@patch` decorators in this file.** The file counts `@patch` / `with patch` the highest in the intelligence sample — but each is a legitimate factory-wiring patch, testing that `create_intelligence_components()` correctly skips disabled sources. Not excessive. | Not a concern; documenting the ceiling. | None. | read-only-no-fix-needed |
| L7 | [tests/accounting/__init__.py](tests/accounting/__init__.py), [tests/notifications/__init__.py](tests/notifications/__init__.py) | **Empty test directories mirroring dead source scaffolding.** Already flagged in G1 L3 — duplicating the confirmation here for completeness. | Cosmetic. | Delete both. | safe-during-trading |
| L8 | [tests/test_integration_sprint26.py:41](tests/test_integration_sprint26.py) | **Sprint 26 integration tests imports `AfternoonMomentumStrategy` that is unused in this file.** Minor dead import. | Cosmetic. | Remove unused import. | safe-during-trading |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| X1 | Test class naming | All test classes use `TestFoo` prefix; no `FooTest` or `FooTests` variants found in sample. Consistent. | None. | None. | — |
| X2 | Test file naming | All files follow `test_<module>.py`. One variant at `tests/test_integration_sprint*.py` uses sprint-number suffixes instead of module-mirroring — confirms G1 M10 (organic drift). | Discoverability. | Addressed by G1 M9 + M10 + this report's M10. | — |
| X3 | Test function naming | Mostly `test_<behavior>_<outcome>` compliant. Occasional lapses: `test_log_trade` (imperative-only, no outcome), `test_live_value` in `TestStrategyModeEnum` (enum-value rather than behavior), `test_pattern_strength_basic` (vague). Not widespread. | Low. | Rename opportunistically when touching a file; don't bulk-rewrite. | safe-during-trading |
| X4 | [tests/intelligence/test_quality_engine.py:52](tests/intelligence/test_quality_engine.py#L52) | `datetime.now(UTC) - timedelta(hours=hours_ago)` in test fixture producing "fresh" catalyst timestamps. Only borderline Q5.2 — the test doesn't assert on absolute time, just on `hours_ago` offset semantics. Low risk. | None. | None. | read-only-no-fix-needed |
| X5 | [tests/analytics/test_trade_logger.py:17-19](tests/analytics/test_trade_logger.py#L17-L19) | `make_trade()` default `entry_time = datetime(2026, 2, 15, 10, 0, 0)` (naive datetime, no tzinfo). Possible Pydantic serialization warning but no functional issue. | Cosmetic. | Prefer `datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)` to match project convention. | safe-during-trading |

---

## 7. Historical Integration Test Triage (per-file recommendation)

Per §7 of the session prompt. Each `test_integration_sprint*.py` triaged:

| File | Tests | Content summary | Status today | Recommendation |
|------|------:|-----------------|--------------|----------------|
| `test_integration_sprint2.py` | ~8 | Signal → RiskManager → SimulatedBroker → TradeLogger flow | Still runs, asserts older `Order/Trade` shapes; mostly subsumed by `tests/execution/` + `tests/core/test_risk_manager.py` | **Deprecate** — move to `tests/integration/historical/` with README note. Delete only after Phase 3 spot-check confirms no unique coverage. |
| `test_integration_sprint3.py` | ~10 | Cash-reserve mechanics, DEC-037 | Subsumed by current RM tests | **Deprecate** — same as sprint2. |
| `test_integration_sprint4a.py` | ~8 | Orchestrator Phase 1 | Orchestrator now ~906L with 1,759L of dedicated tests; these are redundant | **Delete** after Phase 3 confirms no unique coverage. |
| `test_integration_sprint4b.py` | ~9 | Orchestrator Phase 2 | Same as 4a | **Delete** after Phase 3 confirms. |
| `test_integration_sprint5.py` | ~8 | Phase 1 handoff integration | Subsumed by newer integration tests | **Deprecate**. |
| `test_integration_sprint13.py` | 5 | API dependencies, AppState | Sprint 14 tests + `tests/api/conftest.py` subsume | **Delete** after Phase 3 confirms. |
| `test_integration_sprint18.py` | ~17 | Multi-strategy operations | **Dense, still exercises signal-to-fill; G1 notes "worth preserving"** | **Keep** — rename to `tests/integration/test_multi_strategy.py`. |
| `test_integration_sprint19.py` | ~21 | 3-strategy ops (ORB + Scalp + VWAP) | Very dense; exercises cross-strategy risk checks | **Keep** — rename to `tests/integration/test_three_strategy_ops.py`. |
| `test_integration_sprint20.py` | ~12 | Regime-based allocation | Still relevant post-27.6 regime refactor | **Keep** — rename to `tests/integration/test_regime_allocation.py`. |
| `test_integration_sprint26.py` | ~10 | Sprint 26 strategy wiring (R2G, BullFlag, FlatTop) | Loads real YAML; verifies factory wiring for new strategies | **Keep** — rename to `tests/integration/test_pattern_strategy_wiring.py`. |

**Summary:** 4 delete/deprecate (5 if `test_integration_sprint13.py` proves redundant), 4 keep-and-rename, 2 borderline (sprint2+3 have historical documentation value). Do NOT bulk-delete; Phase 3 session should run each file in isolation, diff coverage against baseline, and only delete if coverage delta is zero.

---

## 8. Cleanup Tracker #4 — Full Characterization of `test_history_store_migration`

Per §6 of the session prompt. This is M1's root-cause analysis.

### The race that isn't a race

CLAUDE.md and Sprint 31.75 cleanup tracker describe this test as having an "xdist race condition." It doesn't. It has a **deterministic timezone boundary bug** that presents as flake because it depends on wall-clock time-of-day.

### Shared resource analysis
- **DB file:** Each invocation uses `tmp_path` → isolated. Not a shared resource.
- **Global state:** `RegimeHistoryStore` is a per-instance async wrapper; no module-level singletons. Not a shared resource.
- **Result:** Under xdist, each worker runs an independent DB and independent store. **No contention is possible.**

### What actually fails

The test mixes two date conventions:

1. **Test-computed dates (UTC):**
   - [line 245](tests/core/test_regime_vector_expansion.py#L245): `old_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")` — UTC yesterday
   - [line 247](tests/core/test_regime_vector_expansion.py#L247): `new_date = datetime.now(UTC).strftime("%Y-%m-%d")` — UTC today

2. **Store-computed dates (ET via `_ET` timezone):**
   - [regime_history.py:128-130](argus/core/regime_history.py#L128-L130): `now_et = regime_vector.computed_at.astimezone(_ET); trading_date = now_et.strftime("%Y-%m-%d")` — ET trading day

When `store.record(vector)` is called at line 303 with `computed_at=datetime.now(UTC)`, the store writes a row with `trading_date = ET-today`. The test then queries by `new_date = UTC-today` at line 310 and expects that row. These match only when UTC date == ET date.

### Deterministic failure window

| Time zone offset | Test run time (ET) | UTC date | ET date | `old_date` (UTC yesterday) | Stored `trading_date` (ET today) | `new_date` (UTC today) | Assertion result |
|------------------|--------------------|----------|--------|----------------------------|---------------------------------|------------------------|------------------|
| EDT (UTC-4) | 09:00 ET | today | today | yesterday | today | today | ✅ pass |
| EDT (UTC-4) | 15:00 ET | today | today | yesterday | today | today | ✅ pass |
| **EDT (UTC-4)** | **20:30 ET** | **today+1** | **today** | **today (UTC-yesterday is today in ET)** | **today** | **today+1** | **❌ line 307: 2 rows, not 1 ** |
| EDT (UTC-4) | 23:30 ET | today+1 | today | today | today | today+1 | ❌ line 307: 2 rows |
| EDT (UTC-4) | 01:00 ET (day 2) | today | today | yesterday | today | today | ✅ pass |
| EST (UTC-5) | 19:30 ET | today+1 | today | today | today | today+1 | ❌ fail |

**Conclusion:** The test fails deterministically during roughly **20:00–00:00 ET (EDT)** or **19:00–00:00 ET (EST)** every calendar day. Between ~00:00 ET and ~19:00 ET it passes. Under xdist this presents as flake because different runs execute at different times.

This matches the "reconfirmed pre-existing during Sprint 31.85" observation in Sprint 31.85's close-out at [session-1-closeout.md](docs/sprints/sprint-31.85/session-1-closeout.md) — the Sprint 31.85 run was at operator activation time, which can fall in the failure window.

### DEF-150 is a separate bug in a different file

G1's M7 finding identified DEF-150's root cause as `(datetime.now(UTC).minute - 2) % 60` being broken when `minute ∈ {0, 1}` in [tests/sprint_runner/test_notifications.py:313-315](tests/sprint_runner/test_notifications.py#L313-L315). That is **a different test in a different file** with **a different time-of-day bug**. Both have been mis-labeled as "xdist races" in CLAUDE.md; neither is.

### Suggested fix (not modifying — recommendation only)

```python
# Before (lines 244-247)
old_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
old_ts = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00-04:00")
new_date = datetime.now(UTC).strftime("%Y-%m-%d")

# After
from zoneinfo import ZoneInfo
_ET = ZoneInfo("America/New_York")
now_et = datetime.now(UTC).astimezone(_ET)
old_date = (now_et - timedelta(days=1)).strftime("%Y-%m-%d")
old_ts = (now_et - timedelta(days=1)).isoformat()
new_date = now_et.strftime("%Y-%m-%d")
```

Also update [line 302](tests/core/test_regime_vector_expansion.py#L302) to pass `computed_at=datetime.now(UTC)` unchanged (the store normalizes internally) — but now `new_date` will be in ET, matching the store's internal trading_date, so the query returns the expected row.

### Why not an xdist marker / serial / tmp_path isolation?

- **xdist group / serial marker:** Would not fix the issue — even serial, the test fails at 20:30 ET.
- **tmp_path isolation:** Already in place; not a parallelism issue.
- **pytest-freezegun / freezetime:** Would work but is heavier than the one-line fix above.

The timezone alignment is the minimal, correct change.

---

## 9. Cross-Reference with DEF-150 and DEF-163

Per §9 of the prompt, reconciling with G1:

| DEF | Test | Location | Actual root cause | Classification |
|-----|------|----------|-------------------|----------------|
| DEF-150 | `test_check_reminder_sends_after_interval` | `tests/sprint_runner/test_notifications.py:302` | `(datetime.now(UTC).minute - 2) % 60` mis-computes to 58/59 minutes when current minute ∈ {0, 1} → "last notification" set in the future | Time-of-day bug (first 2 min of every hour) — NOT xdist |
| DEF-163 (a) | `test_get_todays_pnl_excludes_unrecoverable` | `tests/analytics/test_def159_entry_price_known.py:137` | Test writes `exit_time=datetime.now(UTC)` but `get_todays_pnl()` filters by ET date. Fails ~20:00 ET to 00:00 ET. | Timezone boundary — NOT "date decay" |
| DEF-163 (b) | `test_history_store_migration` | `tests/core/test_regime_vector_expansion.py:236` | UTC-vs-ET date-string mismatch between test-captured and store-computed trading_date. Fails ~20:00 ET to 00:00 ET. | Timezone boundary — NOT xdist |
| (latent) | `_make_vector` default `computed_at` | `tests/core/test_regime_vector_expansion.py:36` | Hardcoded `datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` default | True "date decay" — latent |

**Key insight:** three "flaky" tests in the current DEF table are actually **three deterministic time-of-day/timezone bugs**, not flakes. A future developer chasing "xdist race" in `test_history_store_migration` would spend hours exploring `pytest-xdist` docs for a problem that has nothing to do with parallelism. The `test_history_store_migration` bug manifests during a 4-hour window every evening; a single operator running CI after dinner would see it reproduce reliably.

**Are the time-sensitive tests clearly marked?** No. None of the three carry a comment or marker explaining the time dependency. A `@pytest.mark.flaky(reason="UTC-vs-ET boundary, see DEF-XXX")` or inline `# FIXME: fails 20:00-00:00 ET, see audit P1-G2 M1` would help. Priority for Phase 3 cleanup sessions.

---

## Pre-Flagged Items

- **Cleanup tracker #4 (xdist race in `test_history_store_migration`):** ✅ Fully characterized in §8 above. Root cause: UTC-vs-ET timezone boundary, not xdist. Fix: 5-line timezone alignment in test setup. Priority MEDIUM (M1).

---

## Positive Observations

1. **`tests/api/conftest.py` is exemplary fixture composition.** 747 lines that construct a full `AppState` graph (EventBus + TradeLogger + SimulatedBroker + HealthMonitor + RiskManager + OrderManager + DebriefService) via layered fixtures. The `client` / `client_with_positions` / `client_with_trades` / `client_with_debrief` progression lets individual tests opt into specific state levels. Follows [DEC-100] AppState-via-Depends pattern faithfully.

2. **`FixedClock` injection is widely adopted.** Every sampled test in `tests/core/` and `tests/execution/` uses `FixedClock(datetime(..., tzinfo=UTC))` rather than mocking `datetime.now`. This is the rule at `.claude/rules/architecture.md` §Async Discipline working as intended. The `tests/core/test_clock.py` file itself (150 lines) formally tests the clock abstraction.

3. **`tests/execution/test_order_manager_sprint329.py` shows the right pattern for async timeout tests:** `eod_flatten_timeout_seconds=1` is overridden in the test fixture ([line 106](tests/execution/test_order_manager_sprint329.py#L106)). This is what `test_order_manager.py` flatten tests (M4) should replicate.

4. **`tests/execution/test_ibkr_errors.py` is a model for enumerable-domain testing.** Every error code in `IBKR_ERROR_MAP` gets exercised; the test set grows mechanically with the map. No brittle magic-numbers outside the map's declared set.

5. **Pattern-strategy tests (`tests/strategies/patterns/`) scale linearly with pattern count.** 10 pattern modules, each with a matching test file following the same 5-section structure (detection happy path, scoring, edge cases, time-window, parameters). Adding an 11th pattern in Sprint 31A followed the template without regression. Cross-reference G1 positive observation #6.

6. **`tests/intelligence/test_position_sizer.py` is dense, readable, and arithmetic-explicit.** Each test comments the expected computation (`# risk_pct = (0.015 + 0.02) / 2 = 0.0175`) inline. A reader can verify the test is correct without running it. 100-line file covering safety-critical sizing math.

7. **`tests/intelligence/test_classifier.py` demonstrates clean LLM-integration testing** — the `_make_claude_response()` helper returns `(response_dict, UsageRecord)` tuples that exactly mirror the production return shape. Tests never reach into `MagicMock.call_args`; they assert on the real post-classification state. Zero tautology.

8. **No `while True` loops found in sampled tests.** 321-file corpus, zero infinite-loop anti-patterns. CLAUDE.md universal rules stick.

9. **Real integration at [tests/test_integration_sprint19.py](tests/test_integration_sprint19.py)** loads real `OrbBreakoutStrategy`, real `VwapReclaimStrategy`, real `RiskManager` into a single test flow. 1,686 lines. Per `.claude/rules/testing.md` §Mocking "never mock the Risk Manager in integration tests" — actually honored. This is the rare integration test that would surface a real-world regression.

10. **Test-count discipline per DEC-328 is visible in the file record.** Sprints 31.5 (+34), 31.75 (+30), 31.8 (+20), 31.85 (+15) each deliver new tests matching the sprint content. No sprint introduced code without a matching test batch. Cross-reference G1 positive observation #5.

---

## Sampled Files Appendix

| Domain | Sampled | Files |
|--------|---------|-------|
| `tests/core/` | 4 | `test_risk_manager.py` (1,901L), `test_orchestrator.py` (1,759L, skimmed fixtures), `test_event_bus.py` (220L), `test_clock.py` (150L), `test_regime_vector_expansion.py` (329L — cleanup tracker #4) |
| `tests/execution/` | 4 | `test_order_manager.py` (1,150+L deep read on flatten paths), `test_order_manager_def158.py` (fixtures), `test_order_manager_sprint329.py` (selected sections), `test_ibkr_errors.py` (100L sample) |
| `tests/strategies/` | 3 | `test_orb_breakout.py` (120L sample of 1,460), `test_red_to_green.py` (80L sample of 588), `test_shadow_mode.py` (240L sample of 516 — CRITICAL finding) |
| `tests/intelligence/` | 5 | `test_counterfactual.py` (120L sample), `test_classifier.py` (100L sample), `test_quality_engine.py` (100L sample), `test_startup.py` (100L sample — 9 patches confirmed), `test_position_sizer.py` (100L complete sample) |
| `tests/backtest/` | 3 | `test_walk_forward_engine.py` (flagged tests read deep: lines 500-630), `test_engine.py` (80L sample), `test_historical_data_feed.py` (80L sample) |
| `tests/api/` | 4 | `conftest.py` (full 747L read — positive observation #1), `test_trades.py` (100L sample), `test_positions.py` (80L sample), `test_auth.py` (full 391L read), `test_lifespan_startup.py` (80L sample) |
| `tests/data/` | 3 | `test_databento_data_service.py` (80L sample), `test_alpaca_data_service.py` (80L sample + stale-data section), `test_universe_manager.py` (80L sample) |
| `tests/analytics/` | 2 | `test_def159_entry_price_known.py` (full 180L read — DEF-163 characterization), `test_trade_logger.py` (80L sample) |
| `tests/ai/` | 2 | `test_client.py` (80L sample), `test_tools.py` (60L sample) |
| Top-level integration | 3 of 10 | `test_integration_sprint2.py` (60L sample of 345), `test_integration_sprint19.py` (60L sample of 1,686), `test_integration_sprint26.py` (60L sample of 330) |
| **Cross-cutting greps** | — | `time.sleep` (2 files), `except Exception:` (5 files), `asyncio.sleep` non-zero (9 files), class-vs-function usage across all sampled files |

**Total files read:** 33 deep/sample + ~8 source files cross-referenced (`argus/execution/order_manager.py`, `argus/core/regime_history.py`, etc.) for finding validation.

---

## Statistics

- Files deep-read: 15 (those >80 lines of content read)
- Files sampled (1st 60-100 lines + targeted): 18
- Total sampled: 33 test files across 10 domains
- Total findings: **24** (1 critical, 10 medium, 8 low, 5 cosmetic)
- Safety distribution: **20 safe-during-trading / 0 weekend-only / 4 read-only-no-fix-needed / 0 deferred-to-defs**
- Estimated Phase 3 fix effort: **3 sessions**
  - Session A (safe-during-trading, ~45m): M1 + M2 + M3 (3 test bugs — timezone, documentary, tautological) + L1 (hardcoded date default) — batch of 4 small test fixes in `tests/core/` and `tests/backtest/`.
  - Session B (safe-during-trading, ~1h): M4 + M5 (order-manager flatten timeouts + alpaca stale-data timeouts — overlaps G1 M4). Also migrate M6 (RiskManager private-attribute pokes) incrementally — start with 3 callsites most coupled to the C1/C2 new tests.
  - Session C (safe-during-trading, ~1h): C1 (refactor `_build_system()` in `test_shadow_mode.py` to avoid `object.__new__`) + M7 (replace MagicMock `__eq__` lambda) + M8 (8 `except Exception: pass` → explicit `pytest.raises`). Tightly coupled — one session to avoid multiple passes.
  - Session D (optional, safe-during-trading, ~30m): M10 (historical integration test triage — move 4-5 files to `tests/integration/historical/`, delete 2-3 after per-file Phase 3 coverage check) + L7 + L8 (cosmetic cleanup).

- **Net new tests:** None required (this is a read-only audit). Phase 3 Session A–C fixes preserve test count (per-test fixes, no deletions).
- **Deletions recommended:** ~3-4 sprint-dated integration test files (M10) after per-file coverage verification — only if coverage delta is zero.

---

## Handoff Notes

- **Do not** re-classify DEF-150 or DEF-163 in CLAUDE.md during Phase 3 without cross-referencing this report and G1 M5/M6/M7. The three bugs are related by theme (time/timezone) but have distinct root causes and fix locations.
- **`test_shadow_mode.py` C1 refactor is architectural.** If `_process_signal` stays in `ArgusSystem` and the test-double pattern remains, the risk persists. Consider extracting `_process_signal` into a `SignalProcessor` service class as part of the Sprint 31B or later refactor pipeline. P1-A1 (main.py audit) may have an overlapping recommendation; cross-reference before opening as a standalone DEF.
- **`test_divergence_documented` (M2) — one-file delete or one-line replace.** Lowest cost, highest clarity win in this report. Recommend folding into Session A.
- **Historical integration tests (M10) — favor keeping over deleting.** Sprint 18/19/20/26 all exercise current behavior. Only Sprint 2/3/4a/4b/13 are candidates for deprecation/deletion, and only after per-file Phase 3 coverage diffing.

---

## FIX-05 Resolution (2026-04-22)

- **M1** ~~`test_history_store_migration` is NOT an xdist race — UTC-vs-ET timezone boundary~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. Lines 245, 247, and 302 now capture dates via `datetime.now(UTC).astimezone(ZoneInfo("America/New_York"))`, aligning with `RegimeHistoryStore.record()`'s ET-based `trading_date` computation. CLAUDE.md DEF-163 row updated to reflect Python-side resolution.
- **L1** ~~`_make_vector()` hardcodes `computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` as default~~ → **RESOLVED FIX-05-core-orchestrator-risk-regime**. Default replaced with `datetime.now(UTC) - timedelta(hours=1)` — slight past-offset preserves "now"-based assertions.
- **M6 (from p1-g1)** ~~11+ tests mutate RiskManager private attributes~~ → **NOT ADDRESSED FIX-05-core-orchestrator-risk-regime**. Left as-is in this session; a full migration to event-driven setup would add churn to the CRITICAL test additions and is better bundled with a dedicated test-layout pass. The new FIX-05 regression tests for C1/C2/M08 use the event-driven path (`PositionClosedEvent` pubsub, broker subclass) to avoid perpetuating the pattern.

Remaining G2 findings (M2 `test_divergence_documented`, M3 `test_speed_benchmark` tautological, M10 historical integration tests, L2+ etc.) are outside FIX-05 scope.
