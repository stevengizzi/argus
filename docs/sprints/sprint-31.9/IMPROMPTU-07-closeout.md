# IMPROMPTU-07 — Doc-Hygiene + Small Ops + UI Bug Fixes Bundle — Close-Out

**Session:** IMPROMPTU-07 (Sprint 31.9 / audit-2026-04-21 Stage 9B)
**Date:** 2026-04-23
**Scope:** 11 requirements bundled — 5 DEF closures (DEF-164, DEF-169, DEF-189, DEF-191, DEF-198) + 3 Apr 21 debrief residuals (F-05, F-06, F-08) + 3 non-DEF items (Cosmetic X1–X6, shadow-variant badge, CLAUDE.md variant count clarification).
**Safety tag:** `safe-during-trading` — log-level tweaks, REST response additive field, UI styling, doc updates; no runtime logic or schema changes.
**Context state:** GREEN (session well within context limits; all requirements + tests landed + docs reconciled before close-out).

---

## 1. Change manifest

| File | Type | Summary |
|---|---|---|
| `argus/main.py` | modified | DEF-164: `_boot_monotonic` instance field + `time.monotonic()` capture at top of `start()` + grace-window check in `_on_shutdown_requested`. DEF-198 path (b): `start()` docstring phase count corrected ("five config-gated sub-phases" → "seven sub-phases (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7) — 19 phases total"). R9: 6 pure archaeology inline comments removed (lines 211, 219, 224, 228, 229, 231). |
| `argus/core/config.py` | modified | DEF-164: `OrderManagerConfig.auto_shutdown_boot_grace_minutes: int = Field(default=10, ge=0)` added alongside the existing `auto_shutdown_*` fields. |
| `argus/core/risk_manager.py` | modified | F-08: `logger.warning(...)` → `logger.debug(...)` for the `PRIORITY_BY_WIN_RATE is not fully implemented` emission at :622 + inline rationale comment. |
| `argus/analytics/trade_logger.py` | modified | F-05: `trade.id[:8]` → `trade.id[:12]` at :126 and :648. DEF-191 doc-only: module-level NOTE block on `get_todays_pnl()` documenting the SQLite `date()` UTC-normalization quirk, market-hours safety envelope, and fix options for a future after-hours-trading sprint. |
| `argus/api/routes/counterfactual.py` | modified | F-06: new `_compute_r_multiple()` + `_enrich_with_r_multiples()` helpers; `get_counterfactual_positions` now returns positions enriched with `mfe_r` / `mae_r` fields. Original dollar fields `max_favorable_excursion` / `max_adverse_excursion` preserved for backward-compat (additive only). MAE is flipped to negative R at the enrichment step. |
| `argus/ui/src/api/types.ts` | modified | F-06: `ShadowTrade` interface extended with `mfe_r: number \| null` + `mae_r: number \| null` fields. |
| `argus/ui/src/features/trades/ShadowTradesTab.tsx` | modified | F-06: `SortKey` union swapped `max_favorable_excursion`/`max_adverse_excursion` → `mfe_r`/`mae_r`. Column headers, sort testids, and `RMultipleCell` bindings updated to the R-multiple fields. |
| `argus/ui/src/features/trades/ShadowTradesTab.test.tsx` | modified | F-06: fixture extended with `mfe_r` + `mae_r`; new test `test_f06_mfe_mae_r_columns_render_from_r_multiple_fields` asserts column headers bind the new sort testids and RMultipleCell renders the R values (not the dollar fields). |
| `argus/ui/src/utils/strategyConfig.ts` | modified | R10: new `stripVariantSuffix()` delimiter-based helper (parses `__` structural separator). `getStrategyDisplay` + `getStrategyBorderClass` + `getStrategyBarClass` + `getStrategyBadgeClass` + `getStrategyColor` all fall back to the base strategy's display config when the full variant ID isn't in `STRATEGY_DISPLAY`. Variant badges inherit the base strategy's color + short name + letter while preserving the full variant ID in `badgeId`. |
| `argus/ui/src/utils/strategyConfig.test.ts` | modified | R10: +7 tests under `describe('experiment-variant strategy IDs (IMPROMPTU-07, 2026-04-23)')` — inherit-base-color, bull_flag + dip_and_rip variant family, badge-class resolution, border/bar/color accessor resolution, base-id no-op, unknown-base grey fallback. |
| `scripts/revalidate_strategy.py` | modified | DEF-189: `_PARAM_NAME_MAP` constant + `_translate_params()` helper with Pydantic `model_fields` validation. `config_overrides = {f"{yaml_name}.{k}": v for ...}` → `config_overrides = _translate_params(strategy_key, fixed_params)`. Flat-key, validated form replaces the silently-no-op'd dot-prefixed form. |
| `tests/scripts/test_revalidate_strategy.py` | created | DEF-189: +8 pytest (`TestTranslateParams` + `TestConfigOverridesFormat`) covering ORB/VWAP/Afternoon/R2G rename paths, unknown-key skip-with-warning, unknown-strategy-key `ValueError`, flat-key invariant, and the `OrbBreakoutConfig.model_fields` membership guarantee. |
| `tests/core/test_boot_grace.py` | created | DEF-164: +4 pytest — deferral inside grace window, shutdown proceeds post-grace, grace=0 disables suppression, `_boot_monotonic=None` defensive bypass. |
| `tests/analytics/test_trade_logger.py` | modified | F-05: +2 pytest under `TestF05LogTruncationWidth` — assert the 12-char ULID prefix is present in the `log_trade` INFO line and the `log_orchestrator_decision` DEBUG line. |
| `tests/api/test_counterfactual_api.py` | modified | F-06: +2 pytest under `TestF06MfeMaeRMultiples` — field presence (`mfe_r`/`mae_r` alongside preserved dollar fields) + known-value R-multiple math (entry=100, stop=95, mfe=3.0 → `mfe_r=0.6`; mae=2.0 dollars → `mae_r=-0.4` via the sign-flip at enrichment). |
| `CLAUDE.md` | modified | Strikethroughs for DEF-164, DEF-169, DEF-189, DEF-191, DEF-198 with RESOLVED annotations + IMPROMPTU-07 reference. R11: variant count methodology note added to the "Experiment Variants" bullet ("22 = `sum(len(v) for v in yaml.safe_load(...)`"). Header line updated with IMPROMPTU-07 summary + test delta. |
| `docs/architecture.md` | modified | §3.9: "17 phases (12 primary + 5 sub-phases)" → "19 phases (12 primary + 7 sub-phases: 7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7)" with IMPROMPTU-07 DEF-198 pointer. |
| `docs/sprints/sprint-31.9/FIX-03-closeout.md` | modified | 3 phase-count references corrected ("17-phase actual sequence" → "19-phase actual sequence — 12 primary + 7 sub-phases (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7)"). |
| `docs/debriefs/debrief-2026-04-21.md` | modified | F-05 + F-06 + F-08 entries annotated with **RESOLVED IMPROMPTU-07 (2026-04-23)** + regression-test pointers + approach-chosen note (F-06 took option (a) per debrief). |
| `docs/sprints/sprint-31.9/impromptu-01-log-ui-hygiene.md` | modified | Top-of-file annotation: "[RETIRED 2026-04-23 — scope executed by IMPROMPTU-07]" — placeholder retained for archive reference only. |
| `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | modified | 11 new "Resolved this campaign" rows (DEF-164, DEF-169, DEF-189, DEF-191, DEF-198, F-05, F-06, F-08, shadow-variant badge, Cosmetic X1–X6). "Open with planned owner" section: DEF-169/189/191/198 struck through with IMPROMPTU-07 resolution annotations. "Outstanding code-level items" section: Cosmetic X1–X6 + Shadow-variant badge rows struck through. |
| `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` | modified | Stage 9B IMPROMPTU-07 row: ⏸ PENDING → ✅ CLEAR (pending commit). 5 DEF rows (164/169/189/191/198) struck through with IMPROMPTU-07 pointers. |

**Files NOT modified** (per IMPROMPTU-07 kickoff scope boundaries + reviewer constraints):
- `workflow/` submodule (Universal RULE-018).
- `docs/audits/audit-2026-04-21/*` (audit report back-annotation out of scope).
- `argus/execution/order_manager.py` (IMPROMPTU-06 scope).
- `argus/api/auth.py` / JWT files (IMPROMPTU-05 scope).
- `config/experiments.yaml` (not this session's scope).
- `CounterfactualPosition` SQLite schema (F-06 additive at serialization time only).

---

## 2. DEF-198 path decision (required by kickoff §Close-Out point 1)

**Path (b) chosen — handoff doc correction.**

Rationale:
1. The kickoff preamble recommended path (b) as default for three reasons: (i) renumbering `[N/12]` labels to a consistent `[M/K]` scheme across 20+ phase logs is error-prone and cosmetic; (ii) the FIX-03 handoff's "17-phase" claim was plausibly aspirational rather than delivered; (iii) the operational boot sequence works correctly regardless of the numbering-label denominator.
2. Before editing docs I grep-verified the actual count via `grep -E "^\s*logger\.info\(\"\[[0-9]" argus/main.py`. Result: 19 distinct labeled phases — 12 primary (1–12) + 7 sub-phases (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7). The prior "17" miscount missed 9.5 (Routing Table, DEC-343) and 10.4 (Event Routing, renumbered from 10.5 per FIX-03 P1-A1-L07).
3. No operator authorization for path (a) was sought; per the kickoff's "must not be chosen without operator authorization" constraint.

Docs corrected:
- `docs/architecture.md:1199` — "17 phases (12 primary + 5 sub-phases)" → "19 phases (12 primary + 7 sub-phases: 7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7)".
- `docs/sprints/sprint-31.9/FIX-03-closeout.md` rows 20, 85, 212 — all three references to "17-phase" updated to "19-phase" with IMPROMPTU-07 DEF-198 pointer.
- `argus/main.py::ArgusSystem.start()` docstring — "Twelve primary phases plus five config-gated sub-phases" → "Twelve primary phases plus seven sub-phases (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7) — 19 phases total".

`[N/12]` log labels were left as-is (path (a) not chosen).

---

## 3. DEF-189 fix verification (kickoff §Close-Out point 2)

The prior form built keys like `"orb_breakout.or_minutes"`. Under BacktestEngine's strict dot-path resolution (FIX-09 P1-E1-M01), every such key failed silently at the first `parts[:-1]` segment because `orb_breakout` is not a nested submodel on `OrbBreakoutConfig` (it's the YAML filename). The WARNING in `_apply_config_overrides` logged every failure, but revalidations kept running with default params.

Fix verification:
- `_PARAM_NAME_MAP` per-strategy name-remap table covers every strategy `revalidate_strategy.py` supports (`orb`, `orb_scalp`, `vwap_reclaim`, `afternoon_momentum`, `red_to_green`, `bull_flag`, `flat_top_breakout`) — including empty sub-maps for strategies whose `extract_fixed_params` output already matches Pydantic field names (red_to_green, bull_flag, flat_top_breakout), so future-proof.
- `_translate_params()` validates every translated key against `config_class.model_fields` and filters unknown keys with a WARNING listing the dropped keys + their target-class name — the defense against future `extract_fixed_params` drift.
- Regression tests demonstrate: (a) `or_minutes` → `orb_window_minutes`, `target_r` → `target_2_r`, `max_hold_minutes` → `time_stop_minutes` all land on real OrbBreakoutConfig fields; (b) bogus keys are filtered and logged (not silently dropped); (c) no translated key contains a `.` (regression against the dot-prefix pattern); (d) every translated ORB key is in `OrbBreakoutConfig.model_fields`.

Sprint 33 Statistical Validation sprint will re-run contaminated revalidations with the correct params — scoped out of IMPROMPTU-07 per the kickoff constraints.

---

## 4. F-06 REST response schema (kickoff §Close-Out point 3)

Example response shape (one position element):

```json
{
  "position_id": "pos_happy_1",
  "symbol": "AAPL",
  "strategy_id": "orb_breakout",
  "entry_price": 100.0,
  "stop_price": 95.0,
  "target_price": 110.0,
  "rejection_stage": "quality_filter",
  "rejection_reason": "grade too low",
  "quality_grade": "B",
  "opened_at": "2026-03-25T10:00:00",
  "closed_at": "2026-03-25T10:30:00",
  "exit_price": 98.0,
  "theoretical_pnl": -2.0,
  "theoretical_r_multiple": -0.4,
  "max_favorable_excursion": 3.0,
  "max_adverse_excursion": 2.0,
  "mfe_r": 0.6,
  "mae_r": -0.4,
  "bars_monitored": 10
}
```

**Backward-compat invariant preserved:** the dollar-valued `max_favorable_excursion` and `max_adverse_excursion` fields remain in the response body unchanged. Every existing consumer keeps working. The two new fields (`mfe_r`, `mae_r`) are purely additive — null when any required input is missing or per-share risk ≤ 0.

**Sign convention:** `mfe_r` is positive (favorable excursion in R). `mae_r` is negative (drawdown stored as positive dollars at the store layer → flipped to negative R at the enrichment step so the UI's `RMultipleCell` renders `-0.40R` as an operator expects).

Regression test `TestF06MfeMaeRMultiples::test_mfe_r_matches_known_r_multiple` verifies the math: entry=100, stop=95 (risk_per_share=5), max_favorable_excursion=3.0 → `mfe_r=0.6`; max_adverse_excursion=2.0 dollars → `mae_r=-0.4`.

---

## 5. UI visual-review checklist (kickoff §Close-Out point 4)

The operator should verify the following in the live Command Center after commit:

1. **Shadow Trades page** (`/trades` → Shadow Trades tab): the MFE and MAE columns render as R-multiples (`+1.23R` / `-0.85R`) with the expected sign — favorable positive, adverse negative. Before this fix they rendered as `$0.00R`-style labels because the cell was formatting dollar-denominated excursions through `RMultipleCell`.
2. **Strategy badge display** (any page — Dashboard, Trades, Observatory, Experiments): shadow-variant IDs (`strat_bull_flag__v2_strong_pole`, `strat_dip_and_rip__v2_tight_dip_quality`, etc.) now render with the base strategy's color (Bull Flag → cyan-400, Dip-and-Rip → rose-400) rather than the greyed-out fallback. The short name follows the base ("FLAG", "DIP") so the visual identity matches the live counterpart.
3. **Dashboard + Trades live-strategy badges** (regression check): `strat_orb_breakout`, `strat_vwap_reclaim`, etc. continue to render with their established colors — the variant fallback is purely additive and base-id resolution is unchanged.
4. **Browser DevTools network tab → `GET /api/v1/counterfactual/positions`**: inspect the response body — every element should now include `mfe_r` + `mae_r` alongside the preserved `max_favorable_excursion` + `max_adverse_excursion` fields.

Verification conditions:
- `experiments.enabled: true` in `config/experiments.yaml` (already set).
- At least one closed shadow position in `counterfactual_positions` table (normal paper-session operation).
- Any shadow-variant strategy that has fired at least one signal — e.g. `strat_bull_flag__v2_strong_pole` on a live bull-flag symbol.

---

## 6. Apr 21 placeholder retirement note (kickoff §Close-Out point 5)

Annotated at the top of `docs/sprints/sprint-31.9/impromptu-01-log-ui-hygiene.md`:

> **[RETIRED 2026-04-23 — scope executed by IMPROMPTU-07]** This placeholder's F-05 / F-06 / F-08 scope was bundled into `IMPROMPTU-07-doc-hygiene-and-ui-fixes.md` and landed with the DEF-164/169/189/191/198 doc-hygiene bundle. See `IMPROMPTU-07-closeout.md` for the close-out artifact. This file is retained for archival reference only. F-01 (pattern_strategy log level) was already closed earlier in the campaign.

The original placeholder body (scope enumeration, file list, etc.) was preserved intact so the archive is still interpretable.

---

## 7. Test results

**pytest delta:** 5057 (pre) → **5073** (post) = **+16**, ≥ +3 baseline target from kickoff.

New pytest from this session:
- `tests/scripts/test_revalidate_strategy.py` — +8 (DEF-189, `TestTranslateParams` 6 + `TestConfigOverridesFormat` 2).
- `tests/core/test_boot_grace.py` — +4 (DEF-164).
- `tests/analytics/test_trade_logger.py::TestF05LogTruncationWidth` — +2 (F-05).
- `tests/api/test_counterfactual_api.py::TestF06MfeMaeRMultiples` — +2 (F-06 REST).

**Total: +16 new pytest tests** (exceeds kickoff test-target of +3 to +6).

**Vitest delta:** 859 (pre) → **866** (post) = **+7**, ≥ +1 baseline target from kickoff.

New Vitest from this session:
- `strategyConfig.test.ts` — +6 (R10 shadow-variant badge: variant inherits base color/name/shortName; dip_and_rip variants inherit rose; `getStrategyBadgeClass` variant-resolves; border/bar/color accessors all resolve variants to base; base-id no-op guard; unknown-base grey fallback; all under `describe('experiment-variant strategy IDs (IMPROMPTU-07, 2026-04-23)')`).
- `ShadowTradesTab.test.tsx::test_f06_mfe_mae_r_columns_render_from_r_multiple_fields` — +1 (F-06 UI: asserts column headers bind `sort-mfe_r`/`sort-mae_r` testids, old `sort-max_*_excursion` testids are gone, and `RMultipleCell` renders the R-multiple values).

**Total: +7 new Vitest tests** — ≥ +1 kickoff target.

All existing tests pass. No test deletions. Pre-existing known failures (DEF-150 flaky first-2-min-of-hour, DEF-167 Vitest hardcoded-date where still present in fixtures) are outside IMPROMPTU-07 scope and unchanged by this session.

---

## 8. Self-assessment — **CLEAR**

All 11 requirements landed:
1. ✅ DEF-198 path (b) — doc correction (actual 19 phases, not 17).
2. ✅ DEF-189 — `_PARAM_NAME_MAP` + `_translate_params()` + 8 regression tests.
3. ✅ DEF-164 — `auto_shutdown_boot_grace_minutes` config + `_boot_monotonic` + shutdown deferral + 4 regression tests.
4. ✅ DEF-191 — module-level NOTE block on `get_todays_pnl()` (doc-only, no code change).
5. ✅ DEF-169 — marked RESOLVED-VERIFIED (strikethrough in CLAUDE.md + RUNNING-REGISTER + CAMPAIGN tracker; FIX-11 commit `fc7eb7c` referenced).
6. ✅ F-05 — `[:8]` → `[:12]` at both trade_logger.py sites + 2 regression tests.
7. ✅ F-06 — REST response enrichment with `mfe_r` + `mae_r` (additive, dollar fields preserved); TypeScript type extended; ShadowTradesTab bound to R fields; 2 pytest + 1 Vitest tests.
8. ✅ F-08 — `logger.warning` → `logger.debug` at risk_manager.py:622 (no regression test needed per kickoff).
9. ✅ Cosmetic X1–X6 — 6 pure-archaeology inline comments removed from `argus/main.py`.
10. ✅ Shadow-variant badge — structural `__` delimiter-based fallback in `strategyConfig.ts`; all 5 accessor helpers resolve variants to base; 7 Vitest tests.
11. ✅ CLAUDE.md variant count methodology note + 5 DEF strikethroughs + top-of-file session summary.

Docs reconciled:
- ✅ Apr 21 debrief F-05/F-06/F-08 annotated with RESOLVED IMPROMPTU-07.
- ✅ `impromptu-01-log-ui-hygiene.md` top-of-file retirement annotation.
- ✅ RUNNING-REGISTER "Resolved this campaign" (+11 rows) + "Open with planned owner" struck through + "Outstanding code-level items" struck through.
- ✅ CAMPAIGN-COMPLETENESS-TRACKER Stage 9B IMPROMPTU-07 → ✅ CLEAR + 5 DEF rows struck through.
- ✅ architecture.md + FIX-03-closeout.md phase counts corrected.

Scope boundaries respected:
- ✅ No `workflow/` submodule edits.
- ✅ No audit-report back-annotations modified.
- ✅ No contaminated revalidations re-run (DEF-189 bug-fix only, re-run deferred to Sprint 33 per kickoff).
- ✅ No `CounterfactualPosition` SQLite schema changes (F-06 at serialization layer only).
- ✅ Path (a) renumbering for DEF-198 NOT chosen (no operator authorization sought).
- ✅ No shadow-variant Badge name-pattern heuristic (delimiter-based structural parsing only).
- ✅ No `order_manager.py` / `auth.py` / other-impromptu-scope edits.

**Commits:** pending (single squashed commit planned).

**Green CI URL:** pending push.

---

## 9. Deferred items surfaced this session

- **Sprint 33 Statistical Validation** — DEF-189 post-fix revalidations still pending; re-run scoped to that sprint per kickoff. Note added to RUNNING-REGISTER.
- **DEF-168 architecture.md API catalog** — adjacent to DEF-198 (both are architecture.md drift) but out of IMPROMPTU-07 scope; stays queued for IMPROMPTU-08.
- **Shadow-variant badge visual verification** — structural fix landed with 7 regression tests; operator visual verification during next paper-session run is recommended but not required for close-out.
- **DEF-029 trade-replay endpoint** — DEF-169 was reclassified RESOLVED-VERIFIED but the underlying `GET /trades/{id}/replay` still returns 501 until DEF-029 is picked up. Non-urgent.

---

## 10. Tier 2 Review

Tier 2 review to be launched via the `reviewer` subagent against this close-out + the diff range. Review artifact will land at `docs/sprints/sprint-31.9/IMPROMPTU-07-review.md`.
