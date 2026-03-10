# Sprint 23.6, Session 3b: App Lifecycle Wiring (Static)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/api/server.py` (full file — understand lifespan pattern)
   - `argus/api/dependencies.py` (AppState dataclass)
   - `argus/intelligence/startup.py` (S3a's factory — verify it exists)
   - `argus/core/config.py` (SystemConfig — where to add catalyst field)
   - `config/system.yaml` (catalyst section already exists, lines 89-116)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: all passing (including S1, S2a, S2b, S3a changes)
3. Verify S3a completed: `argus/intelligence/startup.py` exists with `create_intelligence_components()`
4. Verify you are on the correct branch: `sprint-23.6`

## Objective
Wire the intelligence startup factory into the FastAPI lifespan handler and add `CatalystConfig` to `SystemConfig`. After this session, the catalyst pipeline initializes on app startup when `catalyst.enabled: true` and cleans up on shutdown. No polling yet (that's S3c).

## Requirements

1. **In `argus/core/config.py`**, add `catalyst` field to `SystemConfig`:
   ```python
   from argus.intelligence.config import CatalystConfig
   # ... in SystemConfig class:
   catalyst: CatalystConfig = Field(default_factory=CatalystConfig)
   ```
   Use a TYPE_CHECKING import if circular import risk exists; otherwise direct import is fine since `CatalystConfig` is a simple Pydantic model with no `argus.core` dependencies.

2. **In `argus/api/server.py`**, add intelligence initialization to the `lifespan()` handler:

   Follow the exact same pattern as the AI services block (lines 68-121). Add a new block AFTER the AI services initialization and BEFORE the WebSocket bridge start:

   ```python
   # Initialize intelligence pipeline if enabled
   intelligence_initialized_here = False
   if app_state.config and app_state.config.catalyst and app_state.config.catalyst.enabled:
       try:
           from argus.intelligence.startup import (
               create_intelligence_components,
               shutdown_intelligence,
           )

           components = await create_intelligence_components(
               config=app_state.config.catalyst,
               event_bus=app_state.event_bus,
               ai_client=app_state.ai_client,  # May be None if AI disabled
               usage_tracker=app_state.usage_tracker,  # May be None
               data_dir=app_state.config.data_dir,
           )

           if components is not None:
               await components.pipeline.start()
               app_state.catalyst_storage = components.storage
               app_state.briefing_generator = components.briefing_generator
               intelligence_initialized_here = True
               logger.info("Intelligence pipeline initialized (%d sources)", len(components.sources))
       except Exception as e:
           logger.error(f"Failed to initialize intelligence pipeline: {e}")
   elif app_state.config and app_state.config.catalyst and not app_state.config.catalyst.enabled:
       logger.info("Intelligence pipeline disabled")
   ```

   In the shutdown section (after `yield`), add cleanup:
   ```python
   # Cleanup intelligence pipeline
   if intelligence_initialized_here:
       try:
           from argus.intelligence.startup import shutdown_intelligence
           # Need to store components reference — see implementation note below
           await shutdown_intelligence(components)
       except Exception as e:
           logger.error(f"Failed to shutdown intelligence pipeline: {e}")
       app_state.catalyst_storage = None
       app_state.briefing_generator = None
       logger.info("Intelligence pipeline cleaned up")
   ```

   **Implementation note:** You'll need to keep `components` in scope between startup and shutdown. The simplest way: declare `components = None` before the try block and check it in the shutdown section.

3. **Store `components` for shutdown access.** Either:
   - Keep `components` as a local variable in lifespan (it's a closure, so it persists through `yield`)
   - Or attach it to app_state as a private field

   The closure approach is simplest and matches how `ai_initialized_here` works.

## Constraints
- Do NOT modify `argus/intelligence/startup.py` (S3a already done)
- Do NOT modify any strategy, Risk Manager, Orchestrator, execution, analytics, or UI file
- Do NOT add polling in this session (that's S3c)
- Do NOT change the existing AI services initialization block — add alongside it
- Do NOT change any AppState field types — only set existing `catalyst_storage` and `briefing_generator` fields

## Config Validation
After adding `catalyst` to SystemConfig, write a test that:
1. Loads `config/system.yaml`
2. Extracts the `catalyst` section keys
3. Verifies all keys are recognized by `CatalystConfig.model_fields`
4. Verifies no keys are silently ignored

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests (in `tests/api/test_server_intelligence.py` or similar):
  1. `test_config_loads_catalyst_section` — load system.yaml, verify config.catalyst is CatalystConfig
  2. `test_config_catalyst_default_disabled` — config.catalyst.enabled is False by default
  3. `test_config_catalyst_yaml_keys_match_model` — no silently ignored YAML keys
  4. `test_lifespan_catalyst_enabled` — with catalyst.enabled=True (mocked), AppState.catalyst_storage is not None after startup
  5. `test_lifespan_catalyst_disabled` — with catalyst.enabled=False, AppState.catalyst_storage remains None
  6. `test_lifespan_catalyst_shutdown_cleanup` — after shutdown, AppState.catalyst_storage is None
  7. `test_lifespan_catalyst_error_graceful` — factory raises → logged, app continues without intelligence
  8. `test_lifespan_ai_disabled_catalyst_enabled` — AI client None but catalyst enabled → classifier uses fallback
- Minimum new test count: 8
- Test command: `python -m pytest tests/api/test_server_intelligence.py -x -q`

## Definition of Done
- [ ] `SystemConfig.catalyst` field exists, loads from YAML
- [ ] Intelligence components created in lifespan when enabled
- [ ] AppState.catalyst_storage and briefing_generator populated
- [ ] Cleanup runs on shutdown
- [ ] Config YAML keys match Pydantic model (no silently ignored fields)
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] No ruff lint errors

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Config loading works | `python -c "from argus.core.config import load_config; c = load_config('config/system.yaml'); print(c.catalyst.enabled)"` |
| Existing server tests pass | `python -m pytest tests/api/ -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/execution/ argus/analytics/ argus/backtest/ argus/ui/` empty |
| AI services init unchanged | Review diff of server.py — AI block untouched |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.
