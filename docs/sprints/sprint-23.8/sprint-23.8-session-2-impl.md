# Sprint 23.8, Session 2: Cost Ceiling Enforcement + Classifier Guards

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/sprints/sprint-23.8-spec.md`
   - `argus/intelligence/classifier.py`
   - `argus/intelligence/pipeline.py` (to understand how classifier is invoked)
   - `argus/ai/usage.py` (UsageTracker interface)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: 2,511+ tests passing (Session 1 may have added tests)
3. Verify you are on the correct branch: `sprint-23.8-pipeline-fixes`
4. Verify Session 1 is complete: `git log --oneline -5` should show Session 1 commit(s)

## Objective
Wire the UsageTracker into the classification path so every Claude API call is cost-tracked, enforce the `daily_cost_ceiling_usd` before each classification call, and add safety guards for when `usage_tracker` is `None`.

## Requirements

1. **In `argus/intelligence/classifier.py` — cost ceiling enforcement:**
   - Before each Claude API classification call, check cumulative daily cost against `daily_cost_ceiling_usd`:
     ```python
     if self._usage_tracker is not None:
         today = datetime.now().strftime("%Y-%m-%d")
         usage = await self._usage_tracker.get_daily_usage(today)
         if usage and usage.total_cost >= self._config.daily_cost_ceiling_usd:
             logger.info(
                 f"Daily cost ceiling reached (${usage.total_cost:.4f} >= "
                 f"${self._config.daily_cost_ceiling_usd:.2f}), "
                 f"switching to rule-based fallback for remaining {remaining_count} items"
             )
             # Fall through to rule-based classification for remaining items
     ```
   - After each successful Claude API call, record the usage:
     ```python
     if self._usage_tracker is not None:
         await self._usage_tracker.record_usage(
             model=response.model,
             input_tokens=response.usage.input_tokens,
             output_tokens=response.usage.output_tokens,
             # ... other fields as UsageTracker.record_usage expects
         )
     ```
   - Adapt the above to match the actual UsageTracker interface — read `argus/ai/usage.py` to get the exact method signatures.

2. **In `argus/intelligence/classifier.py` — None guards:**
   - Every call to `self._usage_tracker` must be guarded with `if self._usage_tracker is not None`
   - This includes both `record_usage()` and `get_daily_usage()` calls
   - When `usage_tracker is None`, classification proceeds normally without cost tracking — no errors, no warnings (this is expected when AI layer is disabled)

3. **In `argus/intelligence/classifier.py` or `pipeline.py` — cycle cost logging:**
   - After classification completes for a batch, log the total cost for that cycle:
     ```python
     logger.info(
         f"Classification cycle cost: ${cycle_cost:.4f} "
         f"({claude_count} via Claude, {fallback_count} via fallback)"
     )
     ```
   - If the ceiling was reached mid-batch, the log should reflect how many items went to Claude vs fallback.

4. **Verify rule-based fallback path works:**
   - When the cost ceiling is reached, remaining items must be classified via the rule-based fallback (DEC-301), not dropped.
   - The fallback classifier already exists — ensure the ceiling logic routes to it correctly.
   - The `classified` log line at the end of `pipeline.py` already distinguishes Claude vs fallback counts — verify this still reports correctly after ceiling enforcement.

## Constraints
- Do NOT modify: `argus/ai/usage.py` (UsageTracker interface), `argus/ai/claude_client.py`, source files, `startup.py`, `server.py`, `storage.py`
- Do NOT change: Classification categories, prompt templates, rule-based fallback logic, dedup stages
- Do NOT add: New config fields (use existing `daily_cost_ceiling_usd` and `max_batch_size`)
- If the UsageTracker interface doesn't support what's needed, STOP and document what's missing — do not modify UsageTracker. This would be an escalation trigger.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test classifier with `usage_tracker=None` — classification completes without error
  2. Test cost ceiling enforcement — mock UsageTracker to return cost at ceiling, verify remaining items routed to fallback
  3. Test cost ceiling not yet reached — mock UsageTracker to return cost below ceiling, verify Claude classification proceeds
  4. Test `record_usage` called after each Claude classification — mock and verify call count
  5. Test cycle cost logging — verify log output includes cost and counts
- Minimum new test count: 5
- Test command: `python -m pytest tests/intelligence/ -x -q -k "classifier"`

## Definition of Done
- [ ] Daily cost checked before each Claude API classification call
- [ ] When ceiling reached, remaining items classified via rule-based fallback
- [ ] `record_usage()` called after each successful Claude call
- [ ] All `usage_tracker` access guarded with `is not None` check
- [ ] Cycle cost logged at INFO with Claude count and fallback count
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Classification still produces results | `python -m pytest tests/intelligence/ -k "classifier"` — all pass |
| Rule-based fallback still works | Test with `usage_tracker=None` produces classified items |
| Pipeline cycle log still shows counts | Grep test output or logs for "Classified N items" |
| No import changes to ai/ modules | `git diff --name-only` shows no files in `argus/ai/` |
| Dedup stages unaffected | `python -m pytest tests/intelligence/ -k "dedup"` — all pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`
