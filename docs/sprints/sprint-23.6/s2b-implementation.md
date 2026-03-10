# Sprint 23.6, Session 2b: Pipeline Batch Store + FMP Canary + Semantic Dedup + Publish Ordering

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/__init__.py` (CatalystPipeline)
   - `argus/intelligence/storage.py` (verify S1's `store_catalysts_batch()` exists)
   - `argus/intelligence/config.py`
   - `argus/data/fmp_reference.py`
   - `argus/intelligence/models.py`
2. Run the test suite: `python -m pytest tests/intelligence/ tests/data/test_fmp_reference.py -x -q`
   Expected: all passing (including S1's new tests)
3. Verify S1 completed: `store_catalysts_batch()` exists in storage.py
4. Verify you are on the correct branch: `sprint-23.6`

## Objective
Four changes to the pipeline and FMP client: (1) use batch store from S1 in pipeline, (2) add FMP schema canary at startup, (3) implement post-classification semantic dedup, (4) separate store and publish phases.

## Requirements

1. **In `argus/intelligence/config.py`**, add to `CatalystConfig`:
   ```python
   dedup_window_minutes: int = 30
   ```

2. **In `argus/data/fmp_reference.py`**, add canary test to `start()`:
   - After API key validation, fetch profile for "AAPL" using the existing `_fetch_single_profile_with_retry()` method (or a direct request to `/stable/profile?symbol=AAPL`).
   - Verify the response contains keys: `symbol`, `companyName`, `marketCap`, `price`.
   - On success: log INFO "FMP canary test passed — API schema validated".
   - On failure (missing keys, HTTP error, timeout): log WARNING with details. Do NOT raise — canary failure is non-blocking.
   - If API key is not set (already handled earlier in start), skip canary.

3. **In `argus/intelligence/__init__.py`**, refactor `CatalystPipeline.run_poll()`:

   a. **Semantic dedup** — After classification (Step 3) and before storage (Step 4), add a dedup pass:
      - Group classified catalysts by `(symbol, category)`.
      - Within each group, if multiple items have `published_at` within `self._config.dedup_window_minutes` of each other, keep only the one with the highest `quality_score`.
      - Log the number of items removed by semantic dedup.

   b. **Batch store** — Replace the per-item `self._storage.store_catalyst(catalyst)` loop with a single call to `self._storage.store_catalysts_batch(deduped_catalysts)`.

   c. **Publish after store** — After the batch store completes, iterate over the stored catalysts and publish `CatalystEvent` for each. Wrap each `event_bus.publish()` in try/except — log WARNING on failure but continue to the next item.

   The flow should be:
   ```
   Step 1: Fetch from all sources concurrently
   Step 2: Headline hash dedup (existing)
   Step 3: Classify batch (existing)
   Step 4: Semantic dedup (NEW — by symbol + category + time window)
   Step 5: Batch store (NEW — single transaction)
   Step 6: Publish events (NEW — separate pass, per-item error handling)
   ```

4. **Add a private method** `_semantic_dedup()` to CatalystPipeline:
   ```python
   def _semantic_dedup(self, catalysts: list[ClassifiedCatalyst]) -> list[ClassifiedCatalyst]:
   ```
   This is a pure function (no async needed). Group by `(symbol, category)`, within each group sort by `published_at`, walk through chronologically — if the gap between consecutive items is ≤ `dedup_window_minutes`, keep the one with higher `quality_score`. If equal scores, keep the first.

## Constraints
- Do NOT modify `argus/intelligence/storage.py` (S1 already done)
- Do NOT modify `argus/core/events.py` (S2a already done)
- Do NOT modify any strategy, Risk Manager, Orchestrator, or execution file
- Do NOT change the CatalystPipeline constructor signature
- Do NOT change the CatalystEvent schema

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/intelligence/test_pipeline.py`:
  1. `test_pipeline_uses_batch_store` — verify `store_catalysts_batch` called instead of individual `store_catalyst`
  2. `test_pipeline_publish_after_store` — verify events published only after all stored
  3. `test_pipeline_publish_failure_continues` — mock one publish failure, verify others still publish
  4. `test_semantic_dedup_same_symbol_category_within_window` — 2 items same (sym, cat), within window → keep higher score
  5. `test_semantic_dedup_same_symbol_different_category` — 2 items same sym, different cat → both kept
  6. `test_semantic_dedup_same_category_outside_window` — 2 items same (sym, cat), outside window → both kept
  7. `test_semantic_dedup_equal_scores_keeps_first` — tied scores → first by published_at wins
  8. `test_dedup_window_configurable` — verify dedup_window_minutes from config is respected
- New tests in `tests/data/test_fmp_reference.py`:
  9. `test_fmp_canary_success` — mock AAPL response with expected keys, verify INFO log
  10. `test_fmp_canary_missing_keys` — mock response missing keys, verify WARNING log, no raise
  11. `test_fmp_canary_api_error` — mock HTTP error, verify WARNING log, no raise
- Minimum new test count: 11
- Test command: `python -m pytest tests/intelligence/test_pipeline.py tests/data/test_fmp_reference.py -x -q`

## Config Validation
Verify `dedup_window_minutes` field exists in CatalystConfig:
```python
from argus.intelligence.config import CatalystConfig
assert "dedup_window_minutes" in CatalystConfig.model_fields
```

## Definition of Done
- [ ] Pipeline uses batch store (single transaction)
- [ ] Publish phase is separate from store phase
- [ ] Failed publishes don't prevent other publishes
- [ ] Semantic dedup removes same-(symbol,category) items within time window
- [ ] FMP canary validates schema at startup (non-blocking)
- [ ] `dedup_window_minutes` config field exists with default 30
- [ ] All existing tests pass
- [ ] 11+ new tests written and passing
- [ ] No ruff lint errors

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Pipeline still produces correct output | Existing pipeline tests pass |
| FMP client still starts without error | Existing FMP tests pass |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/core/ argus/execution/ argus/ai/ argus/ui/` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md` — Escalation Criteria section.
