# FIX-13b-test-hygiene-refactors — Close-out

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session ID:** `FIX-13b-test-hygiene-refactors`
- **Stage:** 8 Wave 2
- **Baseline HEAD:** `0ed59b3` (Stage 8a barrier — FIX-13a complete)
- **Date executed:** 2026-04-23
- **Self-assessment:** **MINOR_DEVIATIONS** (see Judgment Calls §3)
- **Context State:** GREEN

## 1. Commits (7)

| # | SHA | Summary |
|---|-----|---------|
| 1 | `18a73d7` | F5 — `_build_system()` uses real `ArgusSystem.__init__` |
| 2 | `edcc626` | F7+F8 — 6 sprint-dated integration files → `tests/integration/historical/` |
| 3 | `3f8cfc7` | F9 — monkeypatch `eod_flatten_timeout_seconds` to 0.1s (6 tests) |
| 4 | `9d27909` | F11 — 13 order-manager test files under `tests/execution/order_manager/` |
| 5 | `d9d3fe2` | F18 — `_make_trade` helper extraction in `tests/api/conftest.py` |
| 6 | `d329856` | F21 — `monitor_poll_seconds` injection on `AlpacaDataService` |
| 7 | `0352a85` | F23 — `make_orb_config` → `orb_config_factory` pytest fixture |

A separate docs-only commit for this close-out + back-annotations will follow.

## 2. Change Manifest

| File | Change | Why |
|------|--------|-----|
| `tests/strategies/test_shadow_mode.py` | Replace `object.__new__(ArgusSystem)` with real `ArgusSystem(config_dir=Path(...), dry_run=True, enable_api=False)` | F5 — kill silent-attribute-tautology class |
| `tests/integration/historical/` | New directory + `__init__.py` + `README.md` | F7/F8 — frozen historical-tests location |
| `tests/test_integration_sprint{2,3,4a,4b,5,13}.py` → `tests/integration/historical/` | `git mv` 6 files | F7/F8 — de-clutter top-level `tests/` |
| `tests/execution/order_manager/test_{core,def158,exit_config,exit_management,hardening,reconciliation,reconciliation_log,reconciliation_redesign,safety,sprint2875,sprint295,sprint329,t2}.py` | `git mv` 13 files; strip `test_order_manager_` prefix; bump `Path(__file__).parents[2] → parents[3]` in 4 spots | F11 — subpackage consolidation + path compensation |
| `tests/execution/test_order_manager.py`, `test_order_manager_sprint295.py` (pre-move) | Per-test `monkeypatch.setattr(order_manager._config, "eod_flatten_timeout_seconds", 0.1)` on 6 tests | F9 — drop 30s/1s fill-wait to 0.1s |
| `argus/data/alpaca_data_service.py` | Add `monitor_poll_seconds: float = 5.0` constructor param; read via `self._monitor_poll_seconds` in `_stale_data_monitor()` (2 `asyncio.sleep` sites) | F21 — production-side injection point |
| `tests/data/test_alpaca_data_service.py` | `data_service` fixture passes `monitor_poll_seconds=0.1`; 2 `asyncio.sleep(6)` → `asyncio.sleep(0.3)` | F21 — test-side consumption |
| `tests/api/conftest.py` | Extract `_make_trade(...)` helper; rewrite 15 seeded trades to use it | F18 — LOC reduction ~228 → ~105 in fixture body |
| `tests/strategies/test_orb_breakout.py` | Replace module-level `make_orb_config` with `orb_config_factory` fixture returning callable; 35 test signature + call-site migrations; add `default_orb_config` fixture | F23 — fixture-ification |
| `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-13-test-hygiene.md` | 7 STATUS lines back-annotated to RESOLVED FIX-13b; Split Notice header updated to reference FIX-13c for Finding 13 | session close-out |

## 3. Judgment Calls

Documented because MINOR_DEVIATIONS applies — kickoff phrasing vs in-session reality diverged on these three:

- **F7/F8 Sprint 13 triage — moved, not deleted.** The kickoff's recommendation was "read first, then decide." Reading `test_integration_sprint13.py` (178 LOC, 3 classes) found: `TestBrokerSelection` (3 tests) duplicates an inline if/elif broker-type chain — dead weight; `TestIBKRBrokerIntegration` (2 tests) is subsumed by `tests/execution/test_ibkr_broker.py` coverage; `TestBrokerSourceConfig` (3 tests) genuinely exercises live `BrokerSource` enum values + `IBKRConfig` defaults. Chose **move**, not delete, to preserve the live-surface regression-guard value. Documented in the new `README.md`.
- **F9 — all 6 tests monkeypatched even though 4 already ran at ~1s.** Empirically only 2 of the 6 flatten tests ran at 30s wall-clock; 4 others were already reduced to ~1s via FIX-04 P1-G2-M04's `config` fixture (`eod_flatten_timeout_seconds=1`). The kickoff's "do NOT skip any of the 6 tests" instruction was honored uniformly; added monkeypatch on all 6 brings them to 0.1s each regardless. Full-suite savings ~63s (kickoff predicted ~180s pre-FIX-04).
- **F23 — factory fixture returning a callable, not `default_orb_config.model_copy(update=...)`.** Kickoff's Hazard guidance recommended `model_copy(update={...})` for Pydantic configs. `OrbBreakoutConfig` carries nested `risk_limits` (`StrategyRiskLimits`) + `operating_window` (`OperatingWindow`) sub-models. Six of 35 call sites update fields nested inside those sub-models (`max_trades_per_day`, `max_daily_loss_pct`, `max_loss_per_trade_pct`, `latest_entry`). `model_copy(update={"risk_limits": default.risk_limits.model_copy(update={"max_trades_per_day": 2})})` is verbose per site. Chose the kickoff's first option instead: convert `make_orb_config` to `orb_config_factory` fixture returning a callable. All 14 original keyword args preserved. `default_orb_config` fixture added but unused for now (call sites with no overrides still use `orb_config_factory()` for consistency).

## 4. Scope Verification

| Spec requirement | Status | Implementation pointer |
|------------------|--------|------------------------|
| F5: `_build_system()` no longer uses `object.__new__` | ✅ RESOLVED | `tests/strategies/test_shadow_mode.py:85-96` + commit `18a73d7` |
| F7+F8: 6 sprint-dated integration files in `tests/integration/historical/` with README | ✅ RESOLVED | `tests/integration/historical/*` + commit `edcc626` |
| F9: all 6 flatten tests monkeypatch timeout to 0.1s | ✅ RESOLVED | `tests/execution/order_manager/test_core.py` (5 tests) + `test_sprint295.py` (1 test) + commit `3f8cfc7` |
| F11: 13 order-manager test files consolidated under `tests/execution/order_manager/` | ✅ RESOLVED | `tests/execution/order_manager/*.py` + commit `9d27909` |
| F18: `_make_trade` helper extracted; fixture body ~228 → ~60 LOC | ✅ RESOLVED | `tests/api/conftest.py:238-271` (helper) + :278-357 (rewritten seeded list); commit `d9d3fe2`. Actual LOC: fixture body ~105 (vs kickoff target ~50-80 — kept one kwarg per field for readability) |
| F21: `AlpacaDataService` accepts `monitor_poll_seconds`; 2 test sleeps → 0.3s | ✅ RESOLVED | `argus/data/alpaca_data_service.py:73,88,614,631,701` + `tests/data/test_alpaca_data_service.py:80-96,522,549` + commit `d329856` |
| F23: `make_orb_config` replaced with fixture; function deleted | ✅ RESOLVED | `tests/strategies/test_orb_breakout.py:16-69` (fixtures) + commit `0352a85` |
| F13 (AI Copilot coverage) deferred to FIX-13c | ✅ DEFERRED per kickoff | Back-annotated in spec to reference FIX-13c |

## 5. Regression Checks

| Check | Expected | Actual | Pass |
|-------|----------|--------|------|
| Full pytest suite (`-n auto --ignore=tests/test_main.py`) | ≥ 4987 (baseline) | 4987 | ✅ |
| Vitest full suite | 859 (baseline) | 859 | ✅ |
| Scoped: `tests/strategies/test_shadow_mode.py` | 21/21 | 21/21 | ✅ |
| Scoped: `tests/integration/historical/` | 31/31 | 31/31 | ✅ |
| Scoped: `tests/execution/order_manager/` | 238/238 | 238/238 | ✅ |
| Scoped: `tests/execution/` | 408/408 | 408/408 | ✅ |
| Scoped: `tests/api/` | 552/552 | 552/552 | ✅ |
| Scoped: `tests/data/` | 451/451 | 451/451 | ✅ |
| Scoped: `tests/strategies/` | 790/790 | 790/790 | ✅ |
| F9 duration reduction | 64.11s → ~1s for the 6 tests | 64.11s → 0.79s | ✅ |
| F21 duration reduction | ~12s → ~1s for stale-monitor class | ~12s → ~0.7s | ✅ |
| No `--skip-validation`/`--force` added to production code | none | none | ✅ |
| No workflow/ submodule edits | none | none (RULE-018 respected) | ✅ |
| Production `eod_flatten_timeout_seconds` default unchanged | 30s | 30s | ✅ |
| Production `AlpacaDataService` monitor default unchanged | 5.0s | 5.0s (new kwarg has `= 5.0`) | ✅ |

## 6. Test Results

| Surface | Pre-session (baseline `0ed59b3`) | Post-session | Delta |
|---------|----------------------------------|--------------|-------|
| pytest | 4987 | 4987 | 0 |
| Vitest | 859 | 859 | 0 |

Zero net test-count delta as expected — all 7 findings are refactors, not behavior additions.

### Runtime

Full pytest suite (`-n auto`): **56.42s** post-session (baseline run not re-measured but the 63s scoped savings from F9 + ~11s from F21 directly reduce the ceiling).

## 7. Remaining Items

None in FIX-13b scope. All 7 findings RESOLVED.

One follow-on outside FIX-13b scope:

- **Finding 13 (P1-G1-L05)** — AI Copilot coverage expansion. Deferred to **FIX-13c-ai-copilot-coverage** per the Stage 8 Parallel plan. Spec back-annotated with the deferral pointer.

## 8. Notes for Tier 2 reviewer

- `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-13-test-hygiene.md` reflects final RESOLVED status on Findings 5, 7, 8, 9, 11, 18, 21, 23. Finding 13 now points to FIX-13c.
- The FIX-04 P1-G2-M04 fixture pre-reduction (1s `eod_flatten_timeout_seconds` override on the default `config` fixture) had already resolved most of F9's "30s × 6 = 3min" claim before this session started; only 2 of the 6 tests still ran at 30s pre-monkeypatch.
- F11 required bumping `Path(__file__).parents[2] → parents[3]` in `test_core.py` (1 site) and `test_sprint329.py` (3 sites) because the new subpackage nesting adds one directory level under `tests/`.
- F23's migration was done via an in-session Python script that (1) swapped the module-level function for two fixtures, (2) walked all `def test_*(...)` signatures in the file and injected `orb_config_factory` as a parameter wherever the body referenced `make_orb_config`, (3) text-replaced `make_orb_config(` → `orb_config_factory(`. Only remaining `make_orb_config` reference is in the fixture's own historical-note docstring.
- `_make_trade` in `tests/api/conftest.py` is private (leading underscore) and file-scoped — not intended for re-use from test modules. If a future session wants it shared, it should be promoted to a proper helpers module with a named export.
