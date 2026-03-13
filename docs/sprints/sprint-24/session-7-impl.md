# Sprint 24, Session 7: Server Initialization + Firehose Pipeline Integration

## Pre-Flight Checks
1. Read: `argus/api/server.py` (lifespan handler), `argus/intelligence/__init__.py` (CatalystPipeline.run()), `argus/intelligence/startup.py` (create_intelligence_components()), `argus/intelligence/config.py` (QualityEngineConfig)
2. Scoped test: `python -m pytest tests/intelligence/ tests/api/test_server.py -x -q`
3. Branch: `sprint-24`

## Objective
Initialize Quality Engine + Sizer in server.py lifespan. Wire firehose mode into CatalystPipeline.run() and polling loop. Add quality component factory to startup.py.

## Requirements

### 1. In `argus/intelligence/startup.py`:

Add factory function:
```python
def create_quality_components(
    config: QualityEngineConfig, db_manager: DBManager | None = None
) -> tuple[SetupQualityEngine, DynamicPositionSizer] | None:
    """Build quality engine + sizer from config. Returns None if disabled."""
    if not config.enabled:
        return None
    engine = SetupQualityEngine(config, db_manager=db_manager)
    sizer = DynamicPositionSizer(config)
    return engine, sizer
```

### 2. In `argus/api/server.py`:

In the lifespan handler (after intelligence components are created):
- Call `create_quality_components()` with system config
- Store engine and sizer on AppState (add fields to AppState dataclass or dict)
- Register quality engine health component: `health_monitor.update_component("quality_engine", ComponentStatus.HEALTHY)`

### 3. In `argus/intelligence/__init__.py` (CatalystPipeline):

Modify `run()` to accept `firehose: bool = False` parameter. When True:
- Call each enabled source's `fetch_catalysts(symbols=[], firehose=True)` instead of `fetch_catalysts(symbols=symbol_list, firehose=False)`
- Rest of pipeline (dedup → classify → store → publish) unchanged

### 4. In polling loop (`startup.py` `run_polling_loop()`):

Add `firehose` parameter (default True for background polling). When firehose=True, call `pipeline.run(symbols=[], firehose=True)`. The polling loop no longer needs the symbol list in firehose mode — it pulls everything.

## Constraints
- Do NOT modify: `argus/intelligence/classifier.py`, `argus/intelligence/storage.py`, `argus/intelligence/models.py`, `argus/intelligence/briefing.py`
- Do NOT change existing intelligence shutdown sequence

## Test Targets
- `test_create_quality_components_enabled`: Returns (engine, sizer) tuple
- `test_create_quality_components_disabled`: Returns None when enabled=false
- `test_pipeline_run_firehose_mode`: Sources called with firehose=True
- `test_pipeline_run_per_symbol_mode`: Default behavior unchanged (firehose=False)
- `test_polling_loop_firehose`: Polling loop calls pipeline.run(firehose=True)
- `test_server_lifespan_quality_init`: Quality components created during startup
- `test_server_lifespan_quality_disabled`: No components when enabled=false
- `test_health_component_registered`: quality_engine in health monitor
- Edge cases: pipeline run with firehose when sources return empty
- Minimum: 10
- Test command: `python -m pytest tests/intelligence/ tests/api/test_server.py -x -q`

## Definition of Done
- [ ] Quality components initialized in server lifespan
- [ ] Firehose mode wired into pipeline
- [ ] Polling loop uses firehose by default
- [ ] Health component registered
- [ ] All existing tests pass
- [ ] 10+ new tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-7-closeout.md`.

