# Sprint 28, Session S6cf-4: Final Polish

## Pre-Flight Checks
1. Run: `python -m pytest tests/intelligence/learning/ -x -q` (expect ~141 passed)
2. Run: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -5` (expect 680 passed)
3. Verify correct branch, S6cf-3 changes committed

## Objective
Three targeted polish fixes. No new features, no architectural changes.

---

## Fix 1: Remove redundant Pydantic validators (S1-F3)

**File: `argus/intelligence/learning/models.py`**

`LearningLoopConfig` has 4 `@field_validator` methods (lines 404–438) that duplicate constraints already expressed by `Field(ge=, le=)` on the same fields (lines 390–402). The validators add custom error messages but otherwise enforce identical bounds. Remove them — Pydantic v2's `Field` constraints produce clear error messages that include the field name, which is what the existing tests match on.

**Changes:**

1. **Delete lines 404–438** — all four validator methods:
   - `validate_min_sample_count`
   - `validate_max_weight_change`
   - `validate_max_cumulative_drift`
   - `validate_p_value_threshold`

2. **Remove `field_validator` from the Pydantic import** (line 17):
   ```python
   # BEFORE:
   from pydantic import BaseModel, Field, field_validator
   # AFTER:
   from pydantic import BaseModel, Field
   ```

**Test safety:** All 6 existing validation tests in `TestLearningLoopConfig` (test_models.py lines 307–341) use `pytest.raises(ValidationError, match="<field_name>")`. Pydantic v2's `Field(ge=)` errors include the field name in the `loc` tuple, which appears in `ValidationError.__str__()`, so all `match=` patterns will still match. No test changes needed.

**Verification:** Run `python -m pytest tests/intelligence/learning/test_models.py::TestLearningLoopConfig -v` to confirm all 6 validation tests pass after removal.

---

## Fix 2: Replace private attribute access with public property (S5-F1)

**Two files, one line each.**

### 2a. Add `closed_position_count` property to CounterfactualTracker

**File: `argus/intelligence/counterfactual.py`**

Add a property after `get_closed_positions()` (after line 397):

```python
    @property
    def closed_position_count(self) -> int:
        """Number of closed counterfactual positions."""
        return len(self._closed_positions)
```

### 2b. Use the public property in main.py

**File: `argus/main.py`, lines 1603–1608**

Replace:
```python
            counterfactual_count = 0
            if self._counterfactual_tracker is not None:
                closed = getattr(
                    self._counterfactual_tracker, "_closed_positions", []
                )
                counterfactual_count = len(closed)
```

With:
```python
            counterfactual_count = 0
            if self._counterfactual_tracker is not None:
                counterfactual_count = getattr(
                    self._counterfactual_tracker, "closed_position_count", 0
                )
```

**Why still `getattr`:** The tracker is typed as `object | None` (line 163) due to lazy import / duck-typing. Calling `.closed_position_count` directly would fail type checking. `getattr` with a default of `0` preserves the duck-typing pattern while accessing a public API instead of a private attribute. If `closed_position_count` is ever renamed, the fallback is `0` (safe — only affects the count metadata on `SessionEndEvent`, not control flow).

---

## Fix 3: Add test for config-disabled path in server lifespan (S5-F3)

**File: `tests/api/test_learning_api.py`**

Add a new test that verifies when `learning_loop.enabled=false`, the learning components remain None.

```python
@pytest.mark.asyncio
async def test_learning_disabled_components_are_none(tmp_path: Path) -> None:
    """When learning_loop.enabled=false, learning components are not initialized."""
    set_jwt_secret(TEST_JWT_SECRET)

    disabled_config = LearningLoopConfig(enabled=False)

    event_bus = EventBus()
    health_monitor = HealthMonitor(config=HealthConfig())
    clock = FixedClock()
    broker = SimulatedBroker()
    risk_manager = RiskManager(config=SystemConfig().risk)
    order_manager = OrderManager(
        broker=broker,
        event_bus=event_bus,
        clock=clock,
        config=OrderManagerConfig(),
    )

    system_config = SystemConfig(
        api=ApiConfig(
            password_hash=hash_password(TEST_PASSWORD),
        ),
        learning_loop=disabled_config,
    )

    app = create_app()
    app_state = AppState(
        config=system_config,
        event_bus=event_bus,
        health_monitor=health_monitor,
        order_manager=order_manager,
        clock=clock,
    )
    app.state.app_state = app_state

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger lifespan by making any request
        response = await client.get("/api/v1/health")
        assert response.status_code in (200, 401)  # Either works — we just need lifespan to run

    # Verify learning components were NOT initialized
    assert app_state.learning_service is None
    assert app_state.learning_store is None
    assert app_state.config_proposal_manager is None
```

**Note:** The exact fixture setup may need adjustment to match how other tests in `test_learning_api.py` construct `AppState`. Use the existing `app_with_learning` fixture as a reference pattern but override the config to be disabled. If the test needs lifespan to actually execute (to run the init branch), ensure the `AsyncClient` context manager triggers it. If `create_app()` uses a lifespan context, the ASGI transport should trigger it on first request.

---

## Constraints

- Do NOT modify any strategy files, risk manager, orchestrator
- Do NOT modify config files
- `counterfactual.py` modification is limited to one property addition (4 lines)
- `main.py` modification is limited to the `getattr` change (3 lines net)
- `models.py` modification is deletion only (remove validators + unused import)
- All existing tests must continue to pass

## Test Targets

- All ~141 existing learning pytest tests must pass
- All 680 existing Vitest tests must pass
- Specifically verify: `python -m pytest tests/intelligence/learning/test_models.py::TestLearningLoopConfig -v` (6 tests)
- New test: `test_learning_disabled_components_are_none`
- Run `ruff check argus/intelligence/learning/models.py argus/intelligence/counterfactual.py argus/main.py`

## Definition of Done

- [ ] 4 redundant `field_validator` methods removed from `LearningLoopConfig`
- [ ] `field_validator` import removed from models.py
- [ ] All 6 existing `TestLearningLoopConfig` validation tests still pass
- [ ] `closed_position_count` property added to `CounterfactualTracker`
- [ ] `main.py` uses `getattr(tracker, "closed_position_count", 0)` instead of private `_closed_positions` access
- [ ] New test: disabled learning loop leaves components as None
- [ ] All existing tests pass
- [ ] Close-out report
- [ ] @reviewer

## Session-Specific Review Focus (for @reviewer)

1. Verify all 6 `TestLearningLoopConfig` tests pass with only `Field(ge=,le=)` constraints (no custom validators)
2. Verify `closed_position_count` property returns `int`, not `list`
3. Verify `main.py` getattr default is `0` (int), not `[]` (list) — must match the new property return type
4. Verify disabled-path test actually triggers server lifespan (learning init branch)
5. Run `ruff check` on modified files — zero new warnings

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
