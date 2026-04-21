# Audit: Legacy Backtest Dead-Code Scan

**Session:** P1-E2
**Date:** 2026-04-21
**Scope:** Import-graph liveness analysis of 8 large legacy files in `argus/backtest/` (total ~12,000 LOC) to determine which can be safely deleted post-BacktestEngine (Sprint 27) + ExperimentRunner (Sprint 32) absorption.
**Files examined:** 8 deep / 0 skimmed — grep-heavy, not deep-read.

---

## Per-File Verdict Table

| # | File | LOC | Production imports? | Test imports? | Script/CLI caller? | Live-code dependency chain? | Verdict |
|---|------|----:|---------------------|---------------|--------------------|----------------------------|---------|
| 1 | [walk_forward.py](../../../argus/backtest/walk_forward.py) | 2,743 | [vectorbt_pattern.py:32](../../../argus/backtest/vectorbt_pattern.py#L32) | [test_walk_forward.py:13](../../../tests/backtest/test_walk_forward.py#L13), [test_walk_forward_engine.py:19](../../../tests/backtest/test_walk_forward_engine.py#L19) | [revalidate_strategy.py:28](../../../scripts/revalidate_strategy.py#L28), [run_validation.py:37](../../../scripts/run_validation.py#L37), [revalidate_all_strategies.py](../../../scripts/revalidate_all_strategies.py) (subprocess), [validate_all_strategies.py](../../../scripts/validate_all_strategies.py) (subprocess, Sprint 27.8) | `run_fixed_params_walk_forward()` is the VectorBT-IS + Replay-OOS driver used by the operational strategy revalidation workflow | **LIVE** |
| 2 | [vectorbt_orb.py](../../../argus/backtest/vectorbt_orb.py) | 1,326 | [walk_forward.py:37](../../../argus/backtest/walk_forward.py#L37) (imports `SweepConfig`, `run_sweep`) | [test_vectorbt_orb.py](../../../tests/backtest/test_vectorbt_orb.py), [test_vectorbt_data_loading.py](../../../tests/backtest/test_vectorbt_data_loading.py) | — (own `__main__`/CLI exists but no operational invoker) | Kept alive by `walk_forward.run_fixed_params_walk_forward()` ORB branch (`strategy=orb`, `_WALK_FORWARD_SUPPORTED`) | **TRANSITIVELY LIVE** |
| 3 | [vectorbt_orb_scalp.py](../../../argus/backtest/vectorbt_orb_scalp.py) | 1,052 | [walk_forward.py:38-39](../../../argus/backtest/walk_forward.py#L38-L39) (`ScalpSweepConfig`, `run_sweep as run_scalp_sweep`) | [test_vectorbt_orb_scalp.py](../../../tests/backtest/test_vectorbt_orb_scalp.py) | — | Kept alive by walk_forward ORB Scalp branch | **TRANSITIVELY LIVE** |
| 4 | [vectorbt_afternoon_momentum.py](../../../argus/backtest/vectorbt_afternoon_momentum.py) | 1,332 | [walk_forward.py:36](../../../argus/backtest/walk_forward.py#L36) + two lazy imports at lines 526, 1910 | [test_vectorbt_afternoon_momentum.py](../../../tests/backtest/test_vectorbt_afternoon_momentum.py) | — | Kept alive by walk_forward Afternoon branch | **TRANSITIVELY LIVE** |
| 5 | [vectorbt_vwap_reclaim.py](../../../argus/backtest/vectorbt_vwap_reclaim.py) | 1,260 | [walk_forward.py:42-43](../../../argus/backtest/walk_forward.py#L42-L43) | [test_vectorbt_vwap_reclaim.py](../../../tests/backtest/test_vectorbt_vwap_reclaim.py) | — | Kept alive by walk_forward VWAP branch. Most-recent validation artifacts: `data/backtest_runs/validation/vwap_reclaim/` dated 2026-03-26 (~4 weeks pre-audit) | **TRANSITIVELY LIVE** |
| 6 | [vectorbt_red_to_green.py](../../../argus/backtest/vectorbt_red_to_green.py) | 1,025 | [walk_forward.py:40-41](../../../argus/backtest/walk_forward.py#L40-L41), [vectorbt_pattern.py:29](../../../argus/backtest/vectorbt_pattern.py#L29) (`load_symbol_data`) | [test_vectorbt_red_to_green.py](../../../tests/backtest/test_vectorbt_red_to_green.py) | — | Imported by walk_forward (but R2G is NOT in `_WALK_FORWARD_SUPPORTED` — branch unreachable via operational path) AND by vectorbt_pattern for shared `load_symbol_data` helper. Net: file is alive for the helper only. | **TRANSITIVELY LIVE** (partial — R2G walk-forward branch is dead) |
| 7 | [vectorbt_pattern.py](../../../argus/backtest/vectorbt_pattern.py) | 1,057 | **none** | [test_vectorbt_pattern.py](../../../tests/backtest/test_vectorbt_pattern.py), [test_runtime_wiring.py:134,163,276](../../../tests/test_runtime_wiring.py#L134) | — (own CLI exists, no operational invoker) | Effectively superseded by BacktestEngine + ExperimentRunner (Sprint 32 pipeline). `_create_pattern_by_name` duplicates the canonical [`build_pattern_from_config()`](../../../argus/strategies/patterns/factory.py) from Sprint 32 S3. | **TEST-ONLY (effectively dead)** |
| 8 | [report_generator.py](../../../argus/backtest/report_generator.py) | 1,232 | **none** | [test_report_generator.py](../../../tests/backtest/test_report_generator.py) | — (CLI documented in [CLAUDE.md:119](../../../CLAUDE.md#L119) but no operational invoker) | Most-recent generated artifacts: `reports/orb_*.html` dated 2026-02-17 — pre-Sprint 27 era, i.e. 2+ months stale. Sprint 25.7 replaced HTML reports with JSON debrief export (DEC-348); Sprint 27+ reporting flows through Command Center pages. | **TEST-ONLY (likely dead)** |

**Total:** 11,027 LOC across 8 files. 6 files LIVE or TRANSITIVELY LIVE (9,738 LOC). 2 files TEST-ONLY candidates for deletion (2,289 LOC).

---

## CRITICAL Findings

*None.* No safety-critical paths affected — all 8 files are offline/development-only.

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [argus/backtest/vectorbt_pattern.py](../../../argus/backtest/vectorbt_pattern.py) (entire file, 1,057 LOC) | **PatternBacktester is effectively dead.** No production import, no operational script calls it. Directly superseded by BacktestEngine + ExperimentRunner (Sprint 32 pipeline) for pattern strategies — the only pattern-based validation path that actually runs via operational scripts is BacktestEngine-only through `revalidate_strategy.py` (bull_flag, flat_top_breakout, red_to_green all have `walk_forward: False` in [revalidate_all_strategies.py:57-62](../../../scripts/revalidate_all_strategies.py#L57-L62)). The Sprint 32 S3 "factory delegation" work (DEF-121) retrofitted the file for all 7 patterns but no consumer was ever wired. | Retiring this file removes 1,057 production LOC + 852 test LOC (2 files, ~50 tests). `_create_pattern_by_name` helper is a duplicate of the canonical factory in [`argus/strategies/patterns/factory.py::build_pattern_from_config`](../../../argus/strategies/patterns/factory.py). | Phase 3: (a) confirm no one uses `python -m argus.backtest.vectorbt_pattern` operationally; (b) update [tests/test_runtime_wiring.py:134,163,276](../../../tests/test_runtime_wiring.py#L134) to call `build_pattern_from_config()` and `_load_pattern_config` replacement via the canonical factory instead; (c) delete `argus/backtest/vectorbt_pattern.py` + `tests/backtest/test_vectorbt_pattern.py`; (d) update [docs/roadmap.md:361,516,675](../../../docs/roadmap.md), project-knowledge.md, and CLAUDE.md MEMORY notes. | `safe-during-trading` |
| M2 | [argus/backtest/report_generator.py](../../../argus/backtest/report_generator.py) (entire file, 1,232 LOC) | **HTML report generator is likely dead.** No production import, no operational script calls it. Latest HTML artifacts in `reports/` are dated 2026-02-17 (pre-Sprint 27 BacktestEngine). Sprint 25.7 replaced session-end HTML with JSON debrief export (DEC-348); Sprint 27+ reporting flows through Command Center UI pages (Arena, Performance, Observatory). The CLI invocation is still documented at [CLAUDE.md:119](../../../CLAUDE.md#L119). | Retiring this file removes 1,232 production LOC + 578 test LOC. CLAUDE.md commands section needs 1 line removed. | Phase 3: (a) confirm with Steven the HTML report is not part of any manual workflow; (b) delete `argus/backtest/report_generator.py` + `tests/backtest/test_report_generator.py`; (c) remove line 119 from CLAUDE.md commands; (d) optionally `git rm reports/orb_*.html` and add `reports/` to `.gitignore` if they are stale artifacts not worth keeping. | `safe-during-trading` |
| M3 | [argus/backtest/walk_forward.py:40-41](../../../argus/backtest/walk_forward.py#L40-L41) + R2G branch | **R2G walk-forward branch is unreachable via operational path.** `revalidate_strategy.py:42` has `_WALK_FORWARD_SUPPORTED = {"orb", "orb_scalp", "vwap_reclaim", "afternoon_momentum"}` — red_to_green is excluded. R2G can only be invoked via `python -m argus.backtest.walk_forward --strategy red_to_green`, which is not invoked anywhere. The import of `R2GSweepConfig` / `run_r2g_sweep` at the top of walk_forward.py is only kept alive because the R2G branch code still references them. | Dead branch inside an otherwise-live file. Removing the R2G branch would let vectorbt_red_to_green.py stop being walk_forward-imported, but it would still be needed for `load_symbol_data` via vectorbt_pattern.py — UNLESS M1 is adopted, in which case vectorbt_red_to_green.py would also lose its only remaining live consumer. | Couple with M1 and M4: if PatternBacktester is deleted AND the R2G branch is excised from walk_forward.py, then vectorbt_red_to_green.py can itself be deleted (another ~1,025 LOC + ~573 test LOC). Defer this as a Phase 3 follow-on after M1 lands. | `safe-during-trading` |
| M4 | [argus/backtest/vectorbt_red_to_green.py](../../../argus/backtest/vectorbt_red_to_green.py) (conditional on M1+M3) | **R2G VectorBT becomes deletable if M1 + M3 are adopted.** Today it is TRANSITIVELY LIVE via two thin threads: (a) the dead R2G branch in walk_forward.py (M3), (b) the `load_symbol_data` helper used by vectorbt_pattern.py (M1). Cut both and the file has no remaining consumers. | A 2nd-phase cleanup worth ~1,598 LOC once M1 + M3 are complete. Not standalone actionable — must chain. | Mark as "Phase 3 follow-on" to M1. | `safe-during-trading` |
| M5 | [argus/backtest/walk_forward.py](../../../argus/backtest/walk_forward.py) (2,743 LOC) | **walk_forward.py is LIVE but surfaces a strategic question: is VectorBT-IS walk-forward still the right path, or should revalidate_strategy.py migrate fully to BacktestEngine for IS as well?** The IS path inside `run_fixed_params_walk_forward` invokes VectorBT `run_sweep` from 4 different files (`vectorbt_orb`, `vectorbt_orb_scalp`, `vectorbt_vwap_reclaim`, `vectorbt_afternoon_momentum`). The OOS path uses ReplayHarness (or BacktestEngine via `oos_engine="backtest_engine"`). If the IS path migrated to BacktestEngine (via `scripts/run_experiment.py` which already does sweeps via `ExperimentRunner` + `ProcessPoolExecutor`), then walk_forward.py + all 4 vectorbt_*.py files could collectively be retired. | This is a ~6,713 LOC retirement opportunity, plus ~4,108 LOC of related tests. Replacement requires: adding walk-forward windowing + WFE computation on top of ExperimentRunner. ExperimentStore already gives per-window SQLite persistence. | Too large to fix-now. Open a new **DEF** entry: "Migrate walk-forward IS path from VectorBT to BacktestEngine (retire walk_forward.py + 4 vectorbt_*.py, DEC-149 supersede gate)." Priority: MEDIUM. Trigger: next sprint planning where validation tooling is on the agenda (likely Sprint 33+). | `read-only-no-fix-needed` (observation → new DEF) |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [docs/decision-log.md:1649](../../../docs/decision-log.md#L1649) — DEC-149 | DEC-149 (VectorBT precompute+vectorize mandate) is **still active** because operational revalidation still uses `run_sweep` from the 4 vectorbt_*.py files. It is NOT yet a superseded-list candidate. Only once M5 (walk-forward migration) lands does DEC-149 become retirable. Recording this here so a future audit doesn't accidentally mark DEC-149 superseded prematurely. | Prevents incorrect DEC cleanup. | No action. Revisit when M5's DEF is closed. | `read-only-no-fix-needed` |
| L2 | [reports/](../../../reports/) directory | `orb_baseline_defaults.html`, `orb_baseline_relaxed.html`, `orb_final_validation.html` — all dated Feb 16–17, 2026 (pre-Sprint 27). Not regenerated since. | ~175 KB of stale HTML committed to the repo, `.gitignore` in the directory suggests it was intended to ignore new output but the three files predate it. | If M2 is adopted, consider deleting these three HTML files in the same PR since they reference the retired tool. Otherwise leave alone. | `safe-during-trading` |
| L3 | [tests/backtest/test_vectorbt_data_loading.py](../../../tests/backtest/test_vectorbt_data_loading.py) (61 LOC) | Small test file that imports `load_symbol_data` from `vectorbt_orb.py`. Retained because vectorbt_orb is live. No immediate action. | If M5 + M1 + M3 all land, this test becomes obsolete. | Part of the M5 cleanup bundle; not standalone. | `safe-during-trading` (conditional) |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [CLAUDE.md:117](../../../CLAUDE.md#L117) | Commands section advertises `python -m argus.backtest.vectorbt_orb ...` as if it's a primary user-facing workflow. In practice, operators invoke `scripts/revalidate_strategy.py` (or `scripts/validate_all_strategies.py`), not the VectorBT CLIs directly. | Mild developer confusion for newcomers. | If M1/M2 land, retune the Backtesting commands section to showcase the operational wrappers (revalidate_strategy.py, validate_all_strategies.py, run_experiment.py) and drop the direct vectorbt_*.py invocations. | `safe-during-trading` |
| C2 | [argus/backtest/walk_forward.py:526,1910](../../../argus/backtest/walk_forward.py#L526) | Two lazy in-function imports of `vectorbt_afternoon_momentum`. They duplicate the module-level import at line 36. | Minor duplication; likely an artifact from when the module was smaller. | Remove the two lazy imports; the top-level import already satisfies them. | `safe-during-trading` |

---

## Deletion Safety Matrix

### M1 — vectorbt_pattern.py + test_vectorbt_pattern.py (safe to delete now)

| File | Direct Imports from production | Test Imports | Config References | Script References | Doc References | LOC Removed |
|------|-------------------------------:|-------------:|------------------:|------------------:|---------------:|------------:|
| `argus/backtest/vectorbt_pattern.py` | 0 | 2 files | 0 | 0 | 4 (roadmap.md lines 361, 516, 675; sprint-history.md; project-knowledge.md; dev-logs/2026-04-01_sprint32-s3.md) | 1,057 |
| `tests/backtest/test_vectorbt_pattern.py` | — | — | — | — | — | 852 |
| `tests/test_runtime_wiring.py` (update, not delete) | — | — | — | — | — | ~10 line edits (swap 3 imports to canonical factory) |
| **Subtotal** | | | | | | **1,909 LOC deleted + ~10 LOC edited** |

Test-count delta: approximately −40 to −50 tests (test_vectorbt_pattern.py has ~45 test functions).

### M2 — report_generator.py + test_report_generator.py (safe to delete pending Steven confirm)

| File | Direct Imports from production | Test Imports | Config References | Script References | Doc References | LOC Removed |
|------|-------------------------------:|-------------:|------------------:|------------------:|---------------:|------------:|
| `argus/backtest/report_generator.py` | 0 | 1 file | 0 | 0 | 1 (CLAUDE.md:119) + references in Sprint 21.6 docs (archived-sprint, do not modify) | 1,232 |
| `tests/backtest/test_report_generator.py` | — | — | — | — | — | 578 |
| CLAUDE.md (edit) | — | — | — | — | — | 1 line removal |
| **Subtotal** | | | | | | **1,810 LOC deleted + 1 LOC edited** |

Test-count delta: approximately −20 to −30 tests.

### M3 + M4 — R2G VectorBT branch retirement (Phase 3 follow-on; chain after M1)

| File | Action | LOC Delta |
|------|--------|-----------|
| `argus/backtest/walk_forward.py` | Delete R2G branch (~lines 40–41, 628–641, 2156+ cross_validate R2G path, and parser options) | ~−150 LOC (edit) |
| `argus/backtest/vectorbt_red_to_green.py` | Delete entire file (becomes orphaned once M1 removes vectorbt_pattern.py's `load_symbol_data` import) | −1,025 |
| `tests/backtest/test_vectorbt_red_to_green.py` | Delete entire file | −573 |
| **Subtotal** | | **≈−1,748 LOC** |

### M5 — walk-forward migration to BacktestEngine (NEW DEF; not executed in Phase 3 of this audit)

| File | Action | LOC Delta |
|------|--------|-----------|
| `argus/backtest/walk_forward.py` | Delete entire file (after feature-matched replacement) | −2,743 |
| `argus/backtest/vectorbt_orb.py` + test | Delete | −(1,326 + 1,266) |
| `argus/backtest/vectorbt_orb_scalp.py` + test | Delete | −(1,052 + 762) |
| `argus/backtest/vectorbt_afternoon_momentum.py` + test | Delete | −(1,332 + 686) |
| `argus/backtest/vectorbt_vwap_reclaim.py` + test | Delete | −(1,260 + 421) |
| `tests/backtest/test_vectorbt_data_loading.py` | Delete | −61 |
| `tests/backtest/test_walk_forward.py` | Delete | −1,171 |
| `tests/backtest/test_walk_forward_engine.py` | Delete | −637 |
| `scripts/revalidate_strategy.py` | Rewrite (BacktestEngine-only IS path) | net new LOC offset |
| `scripts/run_validation.py` | Delete (wrapper becomes unneeded if revalidate supports symbols directly) | −60 |
| `scripts/revalidate_all_strategies.py` | Simplify (walk_forward flag becomes irrelevant) | −20 (edit) |
| DEC-149 | Mark superseded in decision-log.md | 1 edit |
| **Total** | | **≈−12,777 LOC (plus offset by new code for WFE computation atop ExperimentRunner)** |

---

## Phase 3 Impact Estimate

| Tier | What | Production LOC removed | Test LOC removed | Test count delta | Status |
|------|------|-----------------------:|-----------------:|------------------:|--------|
| **T1 (immediate)** | M1 + M2 (vectorbt_pattern + report_generator) | 2,289 | 1,430 | −60 to −80 | Ready for Phase 3; `safe-during-trading` |
| **T2 (chain after T1)** | M3 + M4 (R2G walk-forward branch + vectorbt_red_to_green.py) | 1,175 | 573 | −15 to −25 | Dependent on T1; `safe-during-trading` |
| **T3 (future sprint)** | M5 (retire walk_forward.py + 4 vectorbt_*.py via BacktestEngine migration) | ~6,713 | ~4,404 | −150 to −200 | New DEF; out of Phase 3 audit scope |

**Conservative Phase 3 outcome (T1 only):** −3,719 LOC, −60-80 tests. Net reduction in the backtest/ surface: ~21% (3,719 / 17,122).

**Aggressive Phase 3 outcome (T1 + T2):** −5,467 LOC, −75-100 tests. Net reduction: ~32%.

**Full reduction (T1 + T2 + T3 executed across multiple sprints):** ≈ −17,400 LOC combined — retires the entire VectorBT legacy subsystem. Reduces backtest/ from 17,122 LOC to approximately 5,000 LOC of production code (BacktestEngine + ReplayHarness + historical_data_feed + config + scanner_simulator + data_fetcher + metrics + manifest + data_validator + tick_synthesizer + backtest_data_service).

---

## DEC-149 Recommendation

**Do NOT add DEC-149 to the superseded list in `decision-log.md` yet.**

DEC-149 (VectorBT precompute+vectorize mandate) remains effective for the 4 operational VectorBT sweep files (`vectorbt_orb`, `vectorbt_orb_scalp`, `vectorbt_vwap_reclaim`, `vectorbt_afternoon_momentum`) that are invoked by `walk_forward.run_fixed_params_walk_forward()` via `scripts/revalidate_strategy.py`.

DEC-149 becomes a supersede candidate only after M5 (walk-forward migration) completes and all 4 VectorBT sweep files are deleted. At that point, the Phase 3 fix session should include a mechanical decision-log update: add DEC-149 to the superseded list with rationale "superseded by BacktestEngine-based walk-forward (ExperimentRunner + WFE computation on top)".

---

## Positive Observations

1. **Clean operational layering.** `scripts/revalidate_strategy.py` → `walk_forward.run_fixed_params_walk_forward()` → `run_sweep()` from each vectorbt_*.py file is a tidy, greppable dependency chain. No hidden plugins, no reflection tricks, no dynamic imports. Deletion safety is actually assessable — which is unusual for a 90-sprint codebase.

2. **Sprint 27.8 preserved isolation deliberately.** [docs/sprints/sprint-27.8/sprint-27.8-s2-impl.md:60](../../../docs/sprints/sprint-27.8/sprint-27.8-s2-impl.md) explicitly instructed "Do NOT modify `revalidate_strategy.py`" and "Use subprocess calls... for isolation." This decision kept the VectorBT path live-but-independent while the new validate_all_strategies.py orchestrator was built, letting the two coexist without coupling. A good pattern for large subsystem transitions.

3. **Every suspect file has a consistent CLI footer.** All 8 files declare `prog="python -m argus.backtest.<name>"` in their argparse setup. Whether or not each CLI is operationally used, the convention makes standalone invocation predictable — valuable for ad-hoc debugging and for future "can I just run this once?" operator moves.

4. **Test isolation was correctly preserved for PatternBacktester.** Even though vectorbt_pattern.py is effectively dead, `tests/test_runtime_wiring.py` continues to use `_create_pattern_by_name` — which is a FACTORY INTEGRATION test. When the file is deleted, the tests should re-target the canonical `build_pattern_from_config()`; the tests themselves are genuinely valuable (they assert "all 7 patterns can be constructed from their YAML configs"), even if their current entry point is the wrong module. Preserve the tests, migrate the imports.

5. **Sprint 31A.5 + 31.85 (DuckDB + Parquet consolidation) did not create new dependencies on the legacy VectorBT path.** `HistoricalQueryService` targets the consolidated cache for analytical queries; it does NOT re-use `load_symbol_data` from vectorbt_orb/red_to_green. That separation means the DuckDB subsystem can stand alone even if the VectorBT legacy path gets retired later.

---

## Statistics

- Files deep-read: 0 full files (grep-heavy audit; read ~60-line windows of walk_forward.py, revalidate_strategy.py, run_validation.py, vectorbt_pattern.py, test_runtime_wiring.py as evidence)
- Files skimmed (listing + first-line docstrings + CLI invocation check): 8
- Total findings: 10 (0 critical, 5 medium, 3 low, 2 cosmetic)
- Safety distribution: 7 safe-during-trading / 0 weekend-only / 3 read-only-no-fix-needed / 0 deferred-to-defs *(M5 becomes a new DEF; tracked separately)*
- Estimated Phase 3 fix effort (T1 tier): **1 session, ~90 minutes** (mechanical deletions + 3 import swaps in test_runtime_wiring.py + 1 CLAUDE.md edit + 4 doc references + full test run to verify baseline drop is intentional and net LOC reduction confirmed)
- T2 tier effort: +1 session, ~60 minutes (chained after T1)
- T3 tier effort: 1 new DEF → dedicated sprint, 3-5 sessions (out of audit scope)
