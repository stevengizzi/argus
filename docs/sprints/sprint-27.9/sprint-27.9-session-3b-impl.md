# Sprint 27.9, Session 3b: Pipeline Consumer Wiring + Integration Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/briefing_generator.py` (understand brief generation flow + prompt structure)
   - `argus/core/orchestrator.py` (understand pre-market routine + logging)
   - `argus/analytics/setup_quality_engine.py` (understand regime_alignment scoring)
   - `argus/data/vix_data_service.py` (get_latest_daily API)
   - `argus/core/regime_history.py` (record method signature)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/integration/ tests/api/test_vix_routes.py -x -q
   ```
   Expected: all passing

## Objective
Wire VIX data into BriefingGenerator (VIX section), Orchestrator (pre-market logging), and SetupQualityEngine (infrastructure stub). Write integration tests verifying the full pipeline.

## Requirements

1. **Modify `argus/intelligence/briefing_generator.py`**:
   - Add VIX context section to the intelligence brief. This goes in the **user message content** (not system prompt), appended after existing catalyst sections.
   - Accept optional `vix_data_service` parameter (or access from app state).
   - New method or section in brief generation:
     ```python
     def _build_vix_context(self) -> Optional[str]:
         if self.vix_service is None or not self.vix_service.is_ready:
             return None
         latest = self.vix_service.get_latest_daily()
         if latest is None:
             return None
         # Format: "## VIX Regime Context\n- VIX Close: {vix_close} (as of {data_date})\n- VRP: {vrp} ({tier})\n- Vol Regime: {phase} ({momentum})\n- Term Structure: {term_structure_regime}\n"
         return formatted_string
     ```
   - If VIX context returns None: omit section entirely. Brief is valid without it.
   - **Do NOT change system prompt.** VIX context is informational, goes in user message.

2. **Modify `argus/core/orchestrator.py`**:
   - In the pre-market routine (before first candle processing), if VIXDataService is available:
     ```python
     if self.vix_service and self.vix_service.is_ready:
         latest = self.vix_service.get_latest_daily()
         if latest:
             logger.info(
                 f"VIX regime context: phase={latest.get('vol_regime_phase')}, "
                 f"momentum={latest.get('vol_regime_momentum')}, "
                 f"VRP={latest.get('variance_risk_premium'):.1f} ({latest.get('vrp_tier')}), "
                 f"VIX={latest.get('vix_close'):.2f} (as of {latest.get('data_date')})"
             )
     ```
   - Accept optional `vix_data_service` parameter in constructor or via setter method.
   - If not available: skip logging, no error.

3. **Modify `argus/analytics/setup_quality_engine.py`**:
   - **Infrastructure only — no behavioral change.** Add a comment or docstring noting:
     ```python
     # FUTURE (post-Sprint 28): When strategies specify phase-space conditions in
     # their operating conditions, the regime_alignment dimension (10% weight) can
     # incorporate VIX regime phase and momentum. Currently dormant — new dimensions
     # are match-any, so regime_alignment score is unchanged.
     ```
   - If the regime_alignment calculator accesses `RegimeVector`, verify it handles None for new fields without error. If it iterates over fields or uses `asdict()`, add guards.
   - **Do NOT change the scoring formula or weights.** Score must be identical to pre-sprint.

4. **Modify `argus/core/regime_history.py`** (if not already done in 2a):
   - Ensure `record()` call sites in `main.py` or wherever regime is persisted now pass `vix_close` from the RegimeVector or VIXDataService.

5. **Create `tests/integration/test_vix_pipeline.py`** (8 tests):
   - `test_briefing_with_vix_data`: Mock VIXDataService with data → brief contains VIX section
   - `test_briefing_without_vix_data`: VIXDataService=None → brief generated without VIX section, no error
   - `test_briefing_stale_vix`: VIXDataService stale → brief omits VIX section
   - `test_orchestrator_vix_logging`: Mock VIXDataService → verify log message emitted (caplog)
   - `test_orchestrator_no_vix`: VIXDataService=None → no log, no error
   - `test_quality_engine_unchanged`: Same input → same quality_score with and without VIXDataService
   - `test_regime_history_records_vix_close`: After regime classification with VIX → history entry has vix_close
   - `test_regime_history_records_null_when_stale`: VIX stale → history entry has vix_close=None

## Constraints
- Do NOT change BriefingGenerator system prompt or behavioral guardrails (DEC-273)
- Do NOT change SetupQualityEngine scoring formula or weights
- Do NOT change DynamicPositionSizer behavior
- Do NOT modify Orchestrator's strategy activation or regime classification logic
- VIX context in brief goes in user message, NOT system prompt

## Test Targets
- Existing tests: all must still pass
- New tests: 8 in `tests/integration/test_vix_pipeline.py`
- Test command: `python -m pytest tests/integration/test_vix_pipeline.py -x -q`

## Definition of Done
- [ ] BriefingGenerator includes VIX section when data available, omits when not
- [ ] Orchestrator logs VIX context pre-market
- [ ] SetupQualityEngine infrastructure commented, scoring unchanged
- [ ] Regime history records vix_close
- [ ] 8 new tests passing
- [ ] R7: Quality scores identical to pre-sprint (integration test)
- [ ] R8: Position sizes identical to pre-sprint
- [ ] R9: Briefing valid without VIX
- [ ] All existing tests pass
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-3b-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R7: Quality scores unchanged | test_quality_engine_unchanged |
| R9: Briefing valid without VIX | test_briefing_without_vix_data |
| BriefingGenerator system prompt unmodified | `git diff argus/intelligence/briefing_generator.py` → no system prompt changes |
| SetupQualityEngine scoring unchanged | test_quality_engine_unchanged with assertAlmostEqual |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-3b-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-3b-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/integration/test_vix_pipeline.py tests/intelligence/ tests/core/test_orchestrator*.py -x -q`
5. Do-not-modify: `argus/strategies/`, `argus/execution/`, `argus/backtest/`, `argus/ai/`, `argus/data/databento_data_service.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify VIX context is in USER message, NOT system prompt (check BriefingGenerator diff)
2. Verify quality engine scoring formula/weights are UNTOUCHED
3. Verify Orchestrator VIX logging is INFO-level, not WARNING/ERROR
4. Verify regime history recording handles vix_close=None gracefully
5. ESCALATION CHECK: If quality scores differ from pre-sprint → ESCALATE (#5)

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as in review-context.md. R7, R8, R9 primary.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as in review-context.md. #5 (quality/sizing changes) most relevant.
