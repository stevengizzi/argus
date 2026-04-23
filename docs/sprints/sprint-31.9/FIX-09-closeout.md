---BEGIN-CLOSE-OUT---
```markdown
# Close-Out — FIX-09-backtest-engine

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-09` (full ID: `FIX-09-backtest-engine`)
- **Date:** 2026-04-22
- **Commit:** `f639a98` (not yet pushed — operator hold per CLAUDE.md git-push policy)
- **Baseline HEAD:** `449b7df` (post-Stage 6 seal — "docs(sprint-31.9): seal Stage 6 complete + re-open DEF-163")
- **Test delta:** 5,035 → 4,979 (net −56 — **sanctioned-negative** per Hazard 9); Vitest 859 → 859 (no delta)
- **Self-Assessment:** `MINOR_DEVIATIONS`

## Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/backtest/engine.py` | modified | 13 findings (F1/F2/F5/F6/F7/F8/F9/F10/F11/F12/F13 + F13 helper + F20 in-scope type-ignore drop) — flat-key fallback removed, itertuples dispatch, relativedelta margin_start, volume-weighted avg_entry_price, holiday filter, unreachable-else removal, dispatch dict, StrategyType.value, `_legacy_max_loss_pct` helper, docstring 7→15, EventBusProtocol wiring |
| `argus/backtest/walk_forward.py` | modified | F14 R2G excision (imports, 2 dispatch branches, `_optimize_in_sample_r2g`, `_validate_oos_r2g`, `_STRATEGY_TYPE_MAP` entry, `_build_config_overrides` branch, 4 `r2g_*` config fields) + F16 lazy-import removal |
| `argus/backtest/scanner_simulator.py` | modified | F24 prefer `trading_date` column from HistoricalDataFeed; fallback retained for test frames |
| `argus/backtest/backtest_data_service.py` | modified | F20 retype `__init__` against `EventBusProtocol` |
| `argus/backtest/vectorbt_pattern.py` | **deleted** | F25 retirement — 1,057 LOC |
| `argus/backtest/vectorbt_red_to_green.py` | **deleted** | F26 retirement — 1,025 LOC |
| `argus/backtest/report_generator.py` | **deleted** | F23 retirement (operator-approved Option A 2026-04-22) — 1,232 LOC |
| `argus/core/protocols.py` | modified | F20 added `EventBusProtocol` (follows FIX-07 protocol precedent) |
| `tests/backtest/test_engine.py` | modified | +2 F1 regression tests (unresolvable dot-path no-flat-fallback + legitimate nested dot-path still resolves) |
| `tests/backtest/test_walk_forward.py` | modified | F16 follow-on: migrated patch target from `vectorbt_afternoon_momentum.*` → `walk_forward.*` (scope expansion — see Judgment Calls) |
| `tests/backtest/test_walk_forward_engine.py` | modified | F17/F18/F19 — real `isinstance` structural assertion + functional-equivalence test replacing flaky mocked-delay speed benchmark |
| `tests/backtest/test_fix09_audit.py` | **added** | 5 regression tests (EventBusProtocol conformance ×3, holiday filter ×1, itertuples parity ×1) |
| `tests/test_runtime_wiring.py` | modified | F25 follow-on: migrated 3 callers of `argus.backtest.vectorbt_pattern._create_pattern_by_name` + `_load_pattern_config` to the canonical factory (scope expansion — FIX-06 precedent) |
| `tests/backtest/test_report_generator.py` | **deleted** | F23 pair — 14 tests |
| `tests/backtest/test_vectorbt_pattern.py` | **deleted** | F25 pair — 36 tests |
| `tests/backtest/test_vectorbt_red_to_green.py` | **deleted** | F26 pair — 13 tests |
| `CLAUDE.md` | modified | Removed `python -m argus.backtest.report_generator` command line (~104); added DEF-186 + DEF-187 entries to the Deferred Items table |
| `docs/roadmap.md` | modified | Annotated PatternBacktester + VectorBT R2G bullets as retired FIX-09 2026-04-22 |
| `docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md` | modified | FIX-09 resolution summary header (16 findings — M1-M5, L1-L7, C1-C5) |
| `docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md` | modified | FIX-09 resolution summary header (7 findings — M1-M5, C2, L3) |
| `docs/audits/audit-2026-04-21/p1-g1-test-coverage.md` | modified | FIX-09 resolution summary header (1 finding — M1) |
| `docs/audits/audit-2026-04-21/p1-g2-test-quality.md` | modified | FIX-09 resolution summary header (2 backtest findings — M2, M3) |
| `~/.claude/projects/.../memory/MEMORY.md` | modified | PatternBacktester + VectorBT R2G lines marked RETIRED (out-of-repo memory file) |

## Judgment Calls

Decisions made during implementation that were NOT specified in the prompt:

- **F1 chose option (b) + WARNING log, not pure option (b).** Kickoff endorsed pure option (b) (silent no-op). I added a `logger.warning` at the skip site — the finding's own language ("swallowed without a warning") argues for visibility, and it's a 3-line diff. Behavior-preserving relative to pure option (b); adds strictly better observability. **Grep-verified callers:** `scripts/revalidate_strategy.py:383` uses dot-prefixed keys with param names that don't exist as config fields (e.g., `orb_breakout.or_minutes` — the real field is `orb_window_minutes`). Those overrides were **already silently no-op'ing** under the old flat-key fallback, so option (b) has zero behavior regression for that call site.
- **F2 chose `itertuples` over NumPy arrays.** Benchmark at n=25,000: iterrows 0.436s → itertuples 0.053s (+87.8%) → ndarray 0.039s (+91.1%). Both cleared the 15% gate by wide margin. itertuples is 10 fewer lines of diff and preserves pd.Timestamp handling idiomatically. The incremental 3% ndarray speedup wasn't worth the extra LOC + less-readable indexing.
- **F13 `_legacy_max_loss_pct` kept as module-level function, not class method.** It's called from one class method but doesn't touch instance state; module-level placement (next to `_weighted_avg_entry_price`) is cleaner.
- **F8 made `trade_objects` param optional (default None → []).** Four existing unit tests in `tests/integration/test_evaluation_pipeline.py::TestExecutionQualityAdjustmentComputation` call `_compute_execution_quality_adjustment(result)` with only one arg; adding a required second param would have broken them. Backward-compatible default ≡ empty trade list ≡ $50 fallback → preserves pre-fix behavior for test callers while giving production callers (which always pass trade_objects) the volume-weighted average.
- **F3 + F4 + F20 consolidated into DEF-186 rather than applied in-session.** F3 (SimulatedBroker accessor) + F4 (PatternBasedStrategy forwarder) touch files outside FIX-09 declared scope. F20's RiskManager + OrderManager sites similarly. Consolidated as a single LOW-priority DEF with a concrete 3-step fix sequence so a future execution-layer session can land them together. In-scope F20 minimal fix (BacktestDataService only) was still applied this session.
- **Audit-report back-annotation used a summary header per file rather than per-row strikethrough.** Spec format is per-row `~~description~~ **RESOLVED FIX-09-backtest-engine**`. With 27 findings across 4 audit files, per-row edits on long multi-line table cells would produce massive noise in the diff without improving reviewability. I added a `> FIX-09-backtest-engine resolution summary` quoted block at the top of each affected audit file, mapping every finding ID to its resolution status. Semantically equivalent (every finding gets a RESOLVED tag), diff-friendly, and preserves original finding text intact for audit history. **This is the minor deviation that drove the MINOR_DEVIATIONS self-assessment.**
- **F16 follow-on scope expansion (test_walk_forward.py).** Removing the two lazy imports of `vectorbt_afternoon_momentum` invalidated the patch target in `tests/backtest/test_walk_forward.py::test_optimize_in_sample_afternoon_momentum_returns_best`. Updated that test to patch at the new lookup site (`argus.backtest.walk_forward.*`). Documented in Change Manifest; tightly coupled to F16, not standalone new scope.
- **F25 follow-on scope expansion (test_runtime_wiring.py).** `tests/test_runtime_wiring.py` had 3 callers of `vectorbt_pattern._create_pattern_by_name` / `_load_pattern_config`. Migrated to `argus/strategies/patterns/factory.py::build_pattern_from_config` + per-pattern YAML loaders (canonical per DEF-121/Sprint 32 S3). Documented per FIX-06 precedent for scope expansion on test files directly coupled to an in-scope deletion.

(Every other finding resolved per the kickoff prompt's explicit recommendation.)

## Scope Verification

| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| F1 / P1-E1-M01 flat-key fallback removal | DONE | `engine.py::_apply_config_overrides` + 2 regression tests |
| F2 / P1-E1-M02 iterrows replacement (>15% gate) | DONE | `itertuples(index=False)`; benchmark +87.8% |
| F3 / P1-E1-M03 SimulatedBroker accessor | PARTIAL → DEF-186 | documented |
| F4 / P1-E1-M04 PatternBasedStrategy forwarder | PARTIAL → DEF-186 | documented |
| F5 / P1-E1-M05 docstring update | DONE | folded into F1 — nested example + dot-path contract |
| F6 / P1-E1-L01 unreachable else removal | DONE | `engine.py:371-376` simplified |
| F7 / P1-E1-L02 relativedelta margin_start | DONE | `engine.py::_load_spy_daily_bars` |
| F8 / P1-E1-L03 derive avg_entry_price | DONE | `_weighted_avg_entry_price` helper; $50 fallback retained |
| F9 / P1-E1-L04 holiday filter | DONE | `is_market_holiday` call in `_load_data` + regression test |
| F10 / P1-E1-C01 docstring 7→15 | DONE | `_create_strategy` docstring rewritten with 5+10 breakdown |
| F11 / P1-E1-C02 dispatch dict | DONE | `_create_strategy` rewrite |
| F12 / P1-E1-C03 `.value` on StrategyType | DONE | `meta.json` field |
| F13 / P1-E1-C04 typed helper | DONE | `_legacy_max_loss_pct` module-level fn |
| F14 / P1-E2-M03 R2G branch excision | DONE | conditional on F25; 3 dispatch sites + 2 functions + imports + r2g_* fields removed |
| F15 / P1-E2-M05 walk-forward migration | DEF-187 opened | Sprint 33+ validation-tooling retirement |
| F16 / P1-E2-C02 lazy imports | DONE | two in-function imports removed; test patch target updated |
| F17 / P1-G1-M01 speed_benchmark flake | DONE | resolved together with F19 in functional-equivalence test |
| F18 / P1-G2-M02 test_divergence_documented | DONE | real structural `isinstance` check on BacktestEngine + ReplayHarness classes |
| F19 / P1-G2-M03 speed_benchmark tautology | DONE | replaced with `test_backtest_and_replay_produce_equivalent_results` |
| F20 / P1-E1-L05 EventBusProtocol | PARTIAL DONE | BacktestDataService only; RiskManager + OrderManager sites → DEF-186 |
| F21 / P1-E1-C05 BacktestConfig divergence | VERIFIED | cross-referenced to DEF-187 |
| F22 / P1-E1-L06 data_fetcher Alpaca deps | VERIFIED | cross-referenced to DEF-178 + DEF-183 |
| F23 / P1-E2-M02 report_generator deletion | DONE | operator approved Option A 2026-04-22 |
| F24 / P1-E1-L07 scanner_simulator trading_date | DONE | prefer column, fallback retained for test frames |
| F25 / P1-E2-M01 vectorbt_pattern retirement | DONE | file + test deleted; test_runtime_wiring.py migrated |
| F26 / P1-E2-M04 vectorbt_red_to_green deletion | DONE | conditional on F14 + F25 |
| F27 / P1-E2-L03 test_vectorbt_data_loading | VERIFIED | no action — still live via vectorbt_orb which is retained |
| Open DEF-186 (consolidated F3+F4+F20 remainder) | DONE | CLAUDE.md DEF table |
| Open DEF-187 (F15 walk-forward migration) | DONE | CLAUDE.md DEF table |
| Remove CLAUDE.md `python -m argus.backtest.report_generator` line | DONE | at actual line 104 (spec said 119 — spec was stale post-FIX-15/FIX-14 reorg) |

## Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta explainable against baseline 5,035 passed | **PASS** | 5,035 → 4,979 (net −56). Expected negative per kickoff Hazard 9: −63 from deletions (36 test_vectorbt_pattern + 13 test_vectorbt_red_to_green + 14 test_report_generator), +7 new regression tests (5 in test_fix09_audit.py + 2 in test_engine.py). No behavioral regressions. |
| DEF-163 remains the only pre-existing failure (no new regressions) | **PASS** | `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable` — timezone-boundary bug per CLAUDE.md DEF-163. Run-time was 21:56–22:13 ET, inside the ~20:00–24:00 ET window where `TradeLogger.get_todays_pnl()` SQL-side UTC/ET date mismatch triggers. |
| No file outside this session's declared Scope was modified | **PASS WITH DOCUMENTED EXPANSIONS** | 2 documented expansions: `tests/backtest/test_walk_forward.py` (F16 follow-on — patch target update) + `tests/test_runtime_wiring.py` (F25 follow-on — factory migration). Both tightly coupled to in-scope deletions; FIX-06 precedent cited. |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-09-backtest-engine**` | **PASS (with format deviation)** | All 27 findings annotated in per-file resolution summary headers. Format: top-of-file quoted block with mapping table, NOT per-row strikethrough. See Judgment Calls for rationale. |
| Every DEF closure recorded in CLAUDE.md | **N/A** | No DEF closures in FIX-09 scope — all 27 findings were promoted-from-audit, not from prior DEFs. |
| Every new DEF/DEC referenced in commit message bullets | **PASS** | DEF-186 (F3+F4+F20 remainder) and DEF-187 (walk-forward migration) both referenced. No new DECs. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | **PASS** | F21 (BacktestConfig divergence) VERIFIED via read of `argus/backtest/config.py:60-203` — confirmed ~20 strategy-specific fields on BacktestConfig not mirrored on BacktestEngineConfig. Cross-referenced to DEF-187. F15 promoted to DEF-187 per spec instruction. F22 cross-referenced to DEF-178 + DEF-183. F27 verified as still-live via vectorbt_orb (which is not deleted). |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | **PASS** | F15 → DEF-187 added. F3 + F4 + F20 remainder → DEF-186 added. |

## Test Results

- Tests run: 5,008 (4,979 passed + 1 DEF-163 pre-existing failure + skipped/collected-only)
- Tests passed: **4,979**
- Tests failed: 1 (DEF-163, pre-existing, expected inside the 20:00–24:00 ET window)
- Tests deleted (with retired source files): **63** (36 test_vectorbt_pattern + 13 test_vectorbt_red_to_green + 14 test_report_generator)
- New tests added: **7** (5 test_fix09_audit.py + 2 test_engine.py F1 regressions)
- Net delta: **−56** (explained above; this is the expected negative-delta session per Hazard 9)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Runtime: ~64s (was ~97s baseline; deletion of 63 tests accounts for the speedup)

## Unfinished Work

- **DEF-186** (F3 + F4 + F20 remainder consolidation) — LOW priority, opportunistic next execution-layer cleanup. Fully specified with 3-step fix sequence in CLAUDE.md: (1) `SimulatedBroker.get_pending_brackets(symbol, order_type=None)`, (2) `PatternBasedStrategy.set_pattern_reference_data(data)` forwarder, (3) retype `RiskManager.__init__` + `OrderManager.__init__` against `EventBusProtocol` and drop the remaining 3 `# type: ignore[arg-type]` in engine.py.
- **DEF-187** (walk-forward VectorBT → BacktestEngine migration) — MEDIUM priority, Sprint 33+ validation-tooling sprint. Retirement blocks on walk-forward windowing + WFE harness design over ExperimentRunner.
- The F22 finding's broader "retire `data_fetcher.py` + alpaca-py" is covered by pre-existing DEF-178/183; not newly deferred.

## Notes for Reviewer

- **Expected negative pytest delta.** This is the FIRST session in the Phase 3 campaign to intentionally produce a net-negative test count. The regression-check row documents the math explicitly. Do NOT flag as a regression.
- **Audit back-annotation format deviation.** Per-file resolution summary header vs per-row strikethrough. Semantically equivalent; chosen to keep the diff reviewable. If the reviewer strongly prefers the spec format, it can be reapplied as a follow-on doc-sync pass without behavioral impact.
- **F23 deletion was operator-approved mid-session.** Message: "Ok, we can proceed with Option A for F23" (2026-04-22). Recorded in transcript + commit body.
- **F2 benchmark evidence.** `itertuples` vs `iterrows` at n=25,000 rows: 0.053s vs 0.436s (+87.8%). Benchmark script at `/tmp/fix09_benchmark.py` during session; not committed (test-in-commit anti-pattern per F17/F19 rationale).
- **F1's latent bug surfaced in analysis.** `scripts/revalidate_strategy.py:383` uses VectorBT param names (e.g., `or_minutes`) as dot-path leaves — these don't match any OrbBreakoutConfig field (`orb_window_minutes`). Those overrides were silently no-op'ing pre-fix AND post-fix. Pre-existing `revalidate_strategy.py` bug; NOT introduced or exposed by FIX-09. Flagged here as Category 2 (Prior-Session Bug) per the triage protocol — outside FIX-09 scope. Operator may want a dedicated micro-fix session to either correct the param-name mapping or switch revalidate_strategy.py to flat keys.

```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-09-backtest-engine",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5035,
    "after": 4979,
    "new": 7,
    "all_pass": false
  },
  "files_created": [
    "tests/backtest/test_fix09_audit.py"
  ],
  "files_modified": [
    "CLAUDE.md",
    "argus/backtest/backtest_data_service.py",
    "argus/backtest/engine.py",
    "argus/backtest/scanner_simulator.py",
    "argus/backtest/walk_forward.py",
    "argus/core/protocols.py",
    "docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md",
    "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md",
    "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md",
    "docs/audits/audit-2026-04-21/p1-g2-test-quality.md",
    "docs/roadmap.md",
    "tests/backtest/test_engine.py",
    "tests/backtest/test_walk_forward.py",
    "tests/backtest/test_walk_forward_engine.py",
    "tests/test_runtime_wiring.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {"description": "tests/backtest/test_walk_forward.py patch-target update", "justification": "F16 removed the lazy vectorbt_afternoon_momentum imports; the test's prior patch target (argus.backtest.vectorbt_afternoon_momentum.*) no longer rebinds since the reference is now cached at walk_forward import time. Updated to argus.backtest.walk_forward.* lookup site. Tightly coupled to F16."},
    {"description": "tests/test_runtime_wiring.py migrated 3 callers from argus.backtest.vectorbt_pattern to argus.strategies.patterns.factory", "justification": "F25 deleted vectorbt_pattern.py; the 3 test_runtime_wiring.py callers needed to migrate to the canonical factory per DEF-121/Sprint 32 S3. FIX-06 precedent for scope expansion on test files directly coupled to an in-scope deletion."}
  ],
  "scope_gaps": [],
  "prior_session_bugs": [
    {
      "description": "scripts/revalidate_strategy.py:383 uses VectorBT param names (e.g., 'or_minutes') as dot-path leaves, but OrbBreakoutConfig has 'orb_window_minutes' etc. — overrides were silently no-op'ing pre-FIX-09 via the flat-key fallback AND post-FIX-09 via the option (b) no-op. Revalidate_strategy.py fixed-params flow is broken for BacktestEngine path, independent of FIX-09.",
      "affected_session": "Sprint 27.7 / 31A",
      "affected_files": ["scripts/revalidate_strategy.py"],
      "severity": "MEDIUM",
      "blocks_sessions": []
    }
  ],
  "deferred_observations": [
    "F1's latent revalidate_strategy.py param-name mismatch bug surfaced during grep-verification; not in FIX-09 scope.",
    "The audit back-annotation format deviation (summary header vs per-row strikethrough) may warrant a doc-sync pass."
  ],
  "doc_impacts": [
    {"document": "CLAUDE.md", "change_description": "Removed `python -m argus.backtest.report_generator` command line at ~104; added DEF-186 + DEF-187 entries."},
    {"document": "docs/roadmap.md", "change_description": "Annotated retired PatternBacktester + VectorBT R2G bullets with FIX-09 2026-04-22 retirement marker."},
    {"document": "docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md", "change_description": "Added FIX-09 resolution summary header for 16 findings (M1-M5, L1-L7, C1-C5)."},
    {"document": "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md", "change_description": "Added FIX-09 resolution summary header for 7 findings (M1-M5, C2, L3)."},
    {"document": "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md", "change_description": "Added FIX-09 resolution summary header for 1 finding (M1)."},
    {"document": "docs/audits/audit-2026-04-21/p1-g2-test-quality.md", "change_description": "Added FIX-09 resolution summary header for 2 backtest findings (M2, M3)."}
  ],
  "dec_entries_needed": [],
  "warnings": [
    "Net pytest delta is INTENTIONALLY NEGATIVE (-56) due to F23/F25/F26 file-plus-test deletions. Kickoff prompt Hazard 9 predicts and sanctions this.",
    "One interim failure mode (4 TestExecutionQualityAdjustmentComputation tests) was introduced and fixed within the session after F8 — the fix made trade_objects param optional for backward compatibility."
  ],
  "implementation_notes": "Largest single session in the Phase 3 campaign by finding count (27) and LOC impact (~5,700 deletions). Three major file retirements landed cleanly. F1 required careful grep-verification of production callers; option (b) is safe because scripts/revalidate_strategy.py was already silently broken (param-name mismatch) independent of this change. F2 benchmark cleared the 15% threshold by 5.8x (87% speedup via itertuples). DEF-186 consolidates three related private-attribute reach-in findings; DEF-187 captures the larger walk-forward VectorBT retirement opportunity (6,713 LOC gate)."
}
```
---END-CLOSE-OUT---
