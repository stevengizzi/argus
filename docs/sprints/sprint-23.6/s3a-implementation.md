# Sprint 23.6, Session 3a: Intelligence Startup Factory

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/config.py`
   - `argus/intelligence/__init__.py` (CatalystPipeline constructor)
   - `argus/intelligence/classifier.py` (CatalystClassifier constructor)
   - `argus/intelligence/storage.py` (CatalystStorage constructor)
   - `argus/intelligence/briefing.py` (BriefingGenerator constructor)
   - `argus/intelligence/sources/__init__.py` (CatalystSource ABC)
2. Run the test suite: `python -m pytest tests/intelligence/ -x -q`
   Expected: all passing (including S1 and S2b changes)
3. Verify S1, S2a, S2b completed: batch store in pipeline, ET defaults, email validation
4. Verify you are on the correct branch: `sprint-23.6`

## Objective
Create a standalone factory function that builds all intelligence pipeline components from config. This function will be called by the app lifecycle handler (Session 3b) but is independently testable.

## Requirements

1. **Create `argus/intelligence/startup.py`** with a factory function and result dataclass:

   ```python
   @dataclass
   class IntelligenceComponents:
       """Container for all intelligence pipeline components."""
       pipeline: CatalystPipeline
       storage: CatalystStorage
       classifier: CatalystClassifier
       briefing_generator: BriefingGenerator
       sources: list[CatalystSource]
   ```

   ```python
   async def create_intelligence_components(
       config: CatalystConfig,
       event_bus: EventBus,
       ai_client: ClaudeClient | None,
       usage_tracker: UsageTracker | None,
       data_dir: str = "data",
   ) -> IntelligenceComponents | None:
   ```

2. **Factory logic:**
   - If `config.enabled` is False: return None immediately.
   - Create `CatalystStorage` with path `{data_dir}/catalyst.db`.
   - Build sources list based on individual source `enabled` flags:
     - If `config.sources.sec_edgar.enabled`: create `SECEdgarClient(config.sources.sec_edgar)`
     - If `config.sources.fmp_news.enabled`: create `FMPNewsSource(config.sources.fmp_news)` (check actual class name)
     - If `config.sources.finnhub.enabled`: create `FinnhubSource(config.sources.finnhub)` (check actual class name)
   - Create `CatalystClassifier`:
     - If `ai_client` is not None and `ai_client.enabled`: pass ai_client and usage_tracker
     - If ai_client is None or disabled: create classifier with a disabled/mock client so it degrades to fallback-only. Check how the classifier handles `client.enabled == False` — it already returns None from `_classify_with_claude` in that case, so passing a disabled client is fine.
   - Create `BriefingGenerator` with the ai_client, storage, usage_tracker, and config.briefing.
   - Create `CatalystPipeline` with sources, classifier, storage, event_bus, config.
   - Return the `IntelligenceComponents` dataclass.

3. **Add a shutdown helper:**
   ```python
   async def shutdown_intelligence(components: IntelligenceComponents) -> None:
   ```
   Calls `components.pipeline.stop()` and `components.storage.close()`.

4. **Logging:** Log at INFO level what was created (which sources enabled, classifier mode).

## Constraints
- Do NOT modify any existing file — only create `argus/intelligence/startup.py`
- Do NOT modify `argus/core/config.py` in this session (that's S3b)
- The factory function takes `CatalystConfig` as a parameter — it does not load config from YAML itself
- The factory must be testable without a running FastAPI app

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/intelligence/test_startup.py`:
  1. `test_create_disabled_returns_none` — config.enabled=False → returns None
  2. `test_create_enabled_all_sources` — all three sources enabled → components has 3 sources
  3. `test_create_enabled_partial_sources` — only sec_edgar enabled → components has 1 source
  4. `test_create_no_sources_enabled` — all sources disabled → components has 0 sources, pipeline still created
  5. `test_create_no_ai_client` — ai_client=None → classifier created (fallback mode)
  6. `test_create_with_ai_client` — ai_client provided → classifier uses it
  7. `test_shutdown_calls_stop_and_close` — verify pipeline.stop() and storage.close() called
  8. `test_storage_path_uses_data_dir` — verify storage DB path includes data_dir
- Minimum new test count: 8
- Test command: `python -m pytest tests/intelligence/test_startup.py -x -q`

## Definition of Done
- [ ] `argus/intelligence/startup.py` created with factory + shutdown functions
- [ ] Factory returns None when disabled
- [ ] Factory respects individual source enabled flags
- [ ] Classifier degrades gracefully without AI client
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] No ruff lint errors: `ruff check argus/intelligence/startup.py`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff HEAD --name-only` shows only new files and test files |
| Existing intelligence tests pass | `python -m pytest tests/intelligence/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.
