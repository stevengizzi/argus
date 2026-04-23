# IMPROMPTU-07 — Tier 2 Review

**Reviewer:** @reviewer subagent (Tier 2, read-only)
**Review date:** 2026-04-23
**Commit under review:** `add4e83` (single squashed commit on `main`)
**Diff range:** `git diff 0918722..add4e83`
**CI run cited:** https://github.com/stevengizzi/argus/actions/runs/24860817762 (in_progress at review time; local test runs green — see §Test Verification)
**Close-out read:** `docs/sprints/sprint-31.9/IMPROMPTU-07-closeout.md` (CLEAR self-assessment)

---BEGIN-REVIEW---

## Summary

IMPROMPTU-07 is a doc-hygiene + small-ops + UI-cosmetic bundle that delivers on all 11 declared requirements without crossing any of the 12 escalation triggers listed in the kickoff. The diff is tightly scoped (23 files, 1,206 insertions / 56 deletions), the backward-compatibility posture on the REST change is genuine (additive only, storage schema untouched), and the structural shadow-variant resolution avoids the "name-pattern heuristic" anti-pattern that would have been a yellow flag. Test delta meets both the pytest (+16, target ≥+3) and Vitest (+7, target ≥+1) baselines with margin.

**Verdict: CLEAR.**

## Requirement-by-requirement verification

### R1 — DEF-198 path decision (path (b), documented)

Close-out §2 explicitly states path (b) was chosen and cites the grep-verification that produced the actual 19-phase count (12 primary + 7 sub-phases: 7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7). I re-ran the same grep:

```
grep -nE "^\s*logger\.info\(\"\[[0-9]" argus/main.py
→ 19 distinct phase labels (1/12 through 12/12 + 7.5/12, 8.5/12, 9.5/12, 10.25/12, 10.3/12, 10.4/12, 10.7/12).
```

- `docs/architecture.md:1199` now reads "19 phases (12 primary + 7 sub-phases: 7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7)" — verified at L1199.
- `docs/sprints/sprint-31.9/FIX-03-closeout.md` — verified three references corrected at rows 20, 85, 212 (the table row, the Finding 30 DONE marker, and the `doc_impacts[0]` JSON entry).
- `argus/main.py::ArgusSystem.start()` docstring — verified at L291 now reads "seven sub-phases (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7) — 19 phases total".
- `[N/12]` labels in `argus/main.py` were NOT renumbered (path (a) escalation trigger avoided). Confirmed the grep output above still shows `[1/12]` through `[12/12]`.

**Status: CLEAR.**

### R2 — DEF-189 fix covers all strategy types

`_PARAM_NAME_MAP` in `scripts/revalidate_strategy.py` covers every key in `_STRATEGY_YAML_MAP`:
- `orb`, `orb_scalp`, `vwap_reclaim`, `afternoon_momentum`, `red_to_green`, `bull_flag`, `flat_top_breakout` — all present (verified at L76-L105).
- Empty sub-maps for strategies whose `extract_fixed_params` output already matches Pydantic field names (`red_to_green`, `bull_flag`, `flat_top_breakout`, `orb_scalp`) — intentional and correctly documented inline.

`_translate_params()` (L108-L175):
- Imports all 7 Pydantic config classes locally.
- Raises `ValueError` on unknown `strategy_key` (defense against drift).
- Validates each translated key against `config_class.model_fields.keys()`.
- Unknown keys are skipped with a WARNING listing the dropped keys and target class name — not silently dropped. The WARNING defense against the DEF-189 silent-no-op failure mode is verified by `TestTranslateParams::test_bad_key_is_dropped_with_warning`.

`tests/scripts/test_revalidate_strategy.py` has 8 tests covering:
1. ORB renames (`or_minutes`→`orb_window_minutes`, `target_r`→`target_2_r`, `max_hold_minutes`→`time_stop_minutes`).
2. VWAP reclaim renames.
3. Afternoon momentum renames.
4. R2G pass-through.
5. Unknown-key filter-with-warning (verifies the DEF-189 defense).
6. Unknown-strategy-key `ValueError`.
7. No-dot-prefix invariant on translated keys (regression-guard against the pre-fix pattern).
8. `OrbBreakoutConfig.model_fields` membership guarantee.

**Status: CLEAR.** All 7 strategy types covered; validation is structural (Pydantic `model_fields`), not a stringly-typed allow-list.

### R3 — DEF-164 boot grace

All four expected components present and verified:
- `OrderManagerConfig.auto_shutdown_boot_grace_minutes: int = Field(default=10, ge=0)` added at `argus/core/config.py:924` with rationale comment.
- `self._boot_monotonic: float | None = None` added to `ArgusSystem.__init__` (L246).
- `self._boot_monotonic = time.monotonic()` captured at the top of `start()`, immediately after the banner INFO log and BEFORE any phase begins (L293).
- `_on_shutdown_requested` (L1998-L2028) checks `elapsed = time.monotonic() - self._boot_monotonic` against `grace * 60` and early-returns with an INFO log on deferral. The guard correctly handles all three defensive cases: `self._config is None`, `self._boot_monotonic is None`, `grace == 0`.

`tests/core/test_boot_grace.py` has exactly 4 tests matching the kickoff specification:
1. `test_auto_shutdown_deferred_when_inside_grace_window` — 3 min / 10 min → deferred.
2. `test_auto_shutdown_proceeds_after_grace_window` — 20 min / 10 min → proceeds.
3. `test_auto_shutdown_grace_disabled_when_zero` — grace=0 → proceeds.
4. `test_auto_shutdown_skips_grace_when_boot_time_is_none` — `_boot_monotonic=None` → proceeds.

All 4 executed and passed locally.

**Status: CLEAR.**

### R4 — DEF-191 doc-only

Inline NOTE block added at `argus/analytics/trade_logger.py:324-334` documenting:
- The SQLite `date()` UTC-normalization quirk.
- Why the quirk is currently harmless (market-hours-only trades).
- When it would become a bug (after-hours trading).
- Deferral to a future sprint with pointers to CLAUDE.md DEF-191 fix options.

No code change in `get_todays_pnl()`. No regression test. CLAUDE.md DEF-191 correctly marked `RESOLVED-DOC-ONLY` with IMPROMPTU-07 reference.

**Status: CLEAR.**

### R5 — DEF-169 reclassification

CLAUDE.md DEF-169 row struck through with **RESOLVED-VERIFIED** (IMPROMPTU-07, 2026-04-23) citing FIX-11 commit `fc7eb7c`. No code change in this commit (as required).

**Status: CLEAR.**

### R6 — F-05 ULID width

Both sites verified:
- `argus/analytics/trade_logger.py:126` — `trade.id[:8]` → `trade.id[:12]` ✓
- `argus/analytics/trade_logger.py:657` (diff reports `:648`, but the NOTE block insertion at `:324` pushed the line down 9; the test itself verifies behavioral outcome, not the line number) — `decision_id[:8]` → `decision_id[:12]` ✓

`TestF05LogTruncationWidth` class in `tests/analytics/test_trade_logger.py` has 2 tests:
1. `test_log_trade_emits_12_char_ulid_prefix` — asserts `trade.id[:12]` is present in the INFO log line.
2. `test_log_orchestrator_decision_emits_12_char_ulid_prefix` — asserts `decision_id[:12]` is present in the DEBUG log line.

The test comments explicitly call out the F-05 regression-proof nature ("8-char prefix alone without the extra 4 chars would indicate regression back to the F-05 bug"). Both tests passed locally.

**Status: CLEAR.**

### R7 — F-06 REST backward-compat

The F-06 implementation is structurally additive:

1. `_compute_r_multiple()` (`argus/api/routes/counterfactual.py:L71-L93`) — pure function, returns `None` on any missing input or zero-R.
2. `_enrich_with_r_multiples()` (L96-L125) — uses `dict(pos)` copy (never `pop`/`del`/`replace`), adds `mfe_r` + `mae_r` keys, leaves the dollar fields untouched.
3. `get_counterfactual_positions` endpoint changed from `"positions": positions` → `"positions": _enrich_with_r_multiples(positions)` at L194. Single-line wrapping call.

Verified the response example in close-out §4 matches the actual implementation:
- Dollar fields preserved: `max_favorable_excursion`, `max_adverse_excursion` (positive dollars as before).
- New fields additive: `mfe_r`, `mae_r` (nullable).

`ShadowTrade` interface at `argus/ui/src/api/types.ts:117-126` contains BOTH `max_favorable_excursion`/`max_adverse_excursion` AND `mfe_r`/`mae_r` — interface extension is additive.

`tests/api/test_counterfactual_api.py::TestF06MfeMaeRMultiples` contains the 2 expected tests:
- `test_response_includes_mfe_r_and_mae_r_fields` — explicitly asserts presence of both R fields AND the dollar fields (backward-compat guard built into the test).
- `test_mfe_r_matches_known_r_multiple` — checks sign convention (§R8 below).

`CounterfactualPosition` SQLite schema verified UNCHANGED — diff inspection shows no modification of `argus/intelligence/counterfactual_store.py` or `argus/intelligence/counterfactual.py`. No `ALTER TABLE` introduced.

**Status: CLEAR.**

### R8 — F-06 MAE sign convention

`_enrich_with_r_multiples()` at L118-L122:

```python
out["mae_r"] = _compute_r_multiple(mae_f, entry_f, stop_f)
if out["mae_r"] is not None and out["mae_r"] > 0:
    out["mae_r"] = -out["mae_r"]
```

This flips the stored-positive-dollars MAE to a negative R-multiple. Test `test_mfe_r_matches_known_r_multiple` correctly verifies:
- entry=100, stop=95, mfe=3.0 → `mfe_r == 0.6` (positive).
- entry=100, stop=95, mae=2.0 (positive dollars at store) → `mae_r == -0.4` (negative R).

Implementation matches both the close-out §4 description and the Apr 21 debrief F-06 option (a) intent.

**Status: CLEAR.**

### R9 — F-08 log downgrade

`argus/core/risk_manager.py:627` now reads `logger.debug(` (previously `logger.warning(`). Inline comment at L619-L625 explains the IMPROMPTU-07 rationale referencing the Apr 21 debrief F-08 finding and the "100+ per session at WARNING level, drowning genuine operational alerts" motivation.

**Status: CLEAR.**

### R10 — Cosmetic X1–X6

`grep -cE "# Sprint [0-9]" argus/main.py` returns **11** (post-session), down from 17 (pre-session per kickoff). The removal targets were all pure sprint-archaeology inline trailing comments (per the diff: `  # Sprint 23: Universe Manager`, `  # Sprint 25.5: eval health check`, `  # Sprint 25.9: background cache refresh`, `  # Sprint 27.7: CounterfactualTracker`, `  # Sprint 27.7: CounterfactualStore`, `  # Sprint 32 S7: PromotionEvaluator`).

The remaining 11 are all either (a) attached to lines providing current context (`# Sprint 27.6, closed on shutdown`, `# Sprint 27.65 S4: intraday bar store`, `# Sprint 32.9 / FIX-03 P1-A1-L05: one-shot log per session...`), or (b) inside longer explanatory blocks not visible as single-line archaeology. Spot-checked each remaining entry; none are pure archaeology. The discriminator (pure archaeology vs. current context) was applied correctly.

**Status: CLEAR.**

### R11 — Shadow-variant badge: structural, not name-pattern

Verified:

1. `stripVariantSuffix()` at `argus/ui/src/utils/strategyConfig.ts:265-269`:
```typescript
function stripVariantSuffix(strategyId: string): string {
  const idx = strategyId.indexOf('__');
  return idx >= 0 ? strategyId.slice(0, idx) : strategyId;
}
```
Structural `__` delimiter parse — NO name-pattern matching on `v2`/`v3`/`shadow`/`variant` literals.

2. Grep-audit: `grep -nE '"v2"|"v3"|"shadow"|"variant"' argus/ui/src/utils/strategyConfig.ts` returns **zero** matches outside of test string data and doc comments. Escalation trigger avoided.

3. All five accessor functions use `stripVariantSuffix(normalized)` for fallback lookup:
   - `getStrategyDisplay` — at L319, uses `baseId = stripVariantSuffix(prefixedId)` + preserves variant ID in `badgeId`.
   - `getStrategyBorderClass` — at L342-L349.
   - `getStrategyBarClass` — at L356-L363.
   - `getStrategyBadgeClass` — at L373-L379.
   - `getStrategyColor` — at L388-L395.

4. `strategyConfig.test.ts` adds a `describe('experiment-variant strategy IDs (IMPROMPTU-07, 2026-04-23)')` block with 6 tests (kickoff spec said 6 new tests; the close-out claims 7 but actual count in the diff is 6). The 6 tests cover:
   - Inherit-base color/name/letter/shortName + preserved `badgeId`.
   - Dip-and-rip v2 + v3 both inherit rose.
   - Badge-class variant uses base tint.
   - All 3 Tailwind accessors (border/bar/color) resolve variants to base.
   - Base strategy IDs unchanged (no false-positive stripping).
   - Truly unknown base still falls through to grey fallback.

Minor count discrepancy between close-out ("+7 Vitest, 6 of which are in the new describe block") and kickoff spec ("6 new tests"): close-out describes 6 strategy-variant tests in the new describe + 1 F-06 ShadowTradesTab test = 7 Vitest total. Confirming via full Vitest run: 866 total (= 859 pre + 7 new). Close-out count is correct when the F-06 ShadowTradesTab test is included in the "+7"; the 6-in-the-describe-block count is the strategy-variant sub-total.

**Status: CLEAR.**

## Escalation trigger audit (all 12)

| # | Trigger | Observation | Status |
|---|---|---|---|
| 1 | `/counterfactual/positions` broke backward compat | Dollar fields still present; additive-only enrichment verified via test + diff read | ✓ not tripped |
| 2 | `CounterfactualPosition` SQLite schema modified | Zero changes to `counterfactual_store.py` / `counterfactual.py`; no `ALTER TABLE` | ✓ not tripped |
| 3 | `revalidate_strategy.py` re-run executed | Zero new files under `data/revalidation/`; no `output_dir` artifacts in diff | ✓ not tripped |
| 4 | Phase-label renumbering path (a) without authorization | `argus/main.py` labels still `[N/12]`; close-out §2 documents path (b) decision | ✓ not tripped |
| 5 | Name-pattern heuristic in Badge logic | Grep-audit of strategyConfig.ts returns zero matches on "v2"/"v3"/"shadow"/"variant" in logic | ✓ not tripped |
| 6 | Full pytest net delta < +3 | Delta +16 (5057→5073) | ✓ not tripped |
| 7 | Vitest net delta < +1 | Delta +7 (859→866) | ✓ not tripped |
| 8 | CI URL missing / red | URL cited (24860817762); run in_progress at review time; local full suite green | ✓ documented; see §Test Verification |
| 9 | Audit-report back-annotation modified | `git diff --stat -- docs/audits/` returns empty | ✓ not tripped |
| 10 | Apr 21 placeholder not annotated | `impromptu-01-log-ui-hygiene.md` L3-L8 contains the `[RETIRED 2026-04-23 — scope executed by IMPROMPTU-07]` annotation block | ✓ not tripped |
| 11 | `workflow/` submodule modified | `git diff --stat -- workflow/` returns empty | ✓ not tripped |
| 12 | Vitest worker hang | Full Vitest run completed in 12.52s, 115 files / 866 tests all passing | ✓ not tripped |

## Sprint-level regression checklist

| Check | Observation |
|---|---|
| pytest net delta ≥ +3 | **+16** (5057 → 5073) |
| Vitest net delta ≥ +1 | **+7** (859 → 866) |
| No scope boundary violation | Only in-scope files modified; no `order_manager.py` / `auth.py` / `experiments.yaml` / counterfactual schema changes |
| CLAUDE.md DEF strikethroughs | DEF-164, DEF-169, DEF-189, DEF-191, DEF-198 all struck through with IMPROMPTU-07 annotation |
| CLAUDE.md variant-count methodology note | Added as a sub-bullet under "Experiment Variants" line (CLAUDE.md L26 in the diff) |

## Test verification

All test runs executed locally during this review:

- `python -m pytest tests/scripts/test_revalidate_strategy.py tests/core/test_boot_grace.py tests/analytics/test_trade_logger.py tests/api/test_counterfactual_api.py -q` → **42 passed in 4.81s**
- `python -m pytest --ignore=tests/test_main.py -n auto -q` → **5073 passed, 25 warnings in 49.76s**
- `cd argus/ui && npx vitest run --reporter=dot` → **115 test files, 866 tests passed in 12.52s**

CI run `24860817762` was still `in_progress` at the time of this review — no conclusion yet. Close-out commits to cite a green CI URL; per the kickoff P25 rule this is an operator-handoff step. Local test runs are green and the test matrix is the same one CI exercises; I don't flag this as a Concern because the close-out explicitly notes CI was pending at commit time and the reviewer contract accepts local verification when CI is still running.

## Observations / non-blocking

1. **Close-out Vitest count framing.** Close-out §7 reports "+6" under the new describe block. The diff actually contains 6 new tests in the describe + 1 F-06 ShadowTradesTab test = 7 total Vitest additions. The total count is right; the sub-total wording in the close-out is slightly ambiguous. Not worth flagging as a Concern — the arithmetic is verifiable (859 → 866 is +7, which matches the CLAUDE.md header update).

2. **Line-number drift in the close-out change-manifest row for trade_logger.py.** The row says `:126 and :648`, but after the DEF-191 NOTE block insertion at `:324-334` (11 lines), the second site is now at `:657`. This is cosmetic — the test verifies behavioral outcomes, not line numbers, so no regression risk. Close-outs conventionally cite pre-change line numbers; no action required.

3. **DEF-189 paired deferred work.** Sprint 33 Statistical Validation is the correct home for the contaminated-revalidation re-run. Close-out §9 surfaces this as a deferred item and RUNNING-REGISTER has the Sprint-33 pointer. Correctly handled.

4. **DEF-164 boot grace edge case.** The grace window is 10 minutes (configurable, `ge=0`). Very long inits (the kickoff cites a "5 min Parquet view build" during Phase 11 HistoricalQueryService) fit comfortably. If any future phase grows beyond 10 min typical, the config can raise the grace without code change. No concern today.

## Verdict

**CLEAR.**

All 11 requirements landed cleanly. Every escalation trigger was verified not-tripped. Backward compatibility on the F-06 REST change was both claimed and structurally demonstrated (dict copy + additive keys, unchanged SQLite schema). The shadow-variant Badge fix is delimiter-structural, not name-pattern heuristic. Test deltas exceed minima with margin (+16 pytest, +7 Vitest). Doc reconciliation is thorough (CLAUDE.md, architecture.md §3.9, FIX-03-closeout rows 20/85/212, debrief F-05/F-06/F-08 annotations, RUNNING-REGISTER, CAMPAIGN tracker, placeholder retirement annotation).

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session_id": "IMPROMPTU-07",
  "sprint_id": "sprint-31.9",
  "commit_sha": "add4e83",
  "diff_range": "0918722..add4e83",
  "files_modified_count": 23,
  "insertions": 1206,
  "deletions": 56,
  "pytest_delta": 16,
  "pytest_pre": 5057,
  "pytest_post": 5073,
  "vitest_delta": 7,
  "vitest_pre": 859,
  "vitest_post": 866,
  "defs_closed": ["DEF-164", "DEF-169", "DEF-189", "DEF-191", "DEF-198"],
  "debrief_residuals_closed": ["F-05", "F-06", "F-08"],
  "escalation_triggers_tripped": [],
  "concerns": [],
  "context_state": "GREEN",
  "ci_run_id": "24860817762",
  "ci_status_at_review": "in_progress",
  "local_tests_green": true
}
```

---END-REVIEW---
