# Sprint 21.6.2, Session 1: BacktestEngine Risk Overrides

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` lines 898–911 — `_load_risk_config()` (loads risk_limits.yaml verbatim)
   - `argus/backtest/engine.py` lines 238–250 — where risk_config is applied to RiskManager
   - `argus/backtest/config.py` lines 137–178 — `BacktestEngineConfig` (no risk override field yet)
   - `argus/core/config.py` lines 201–235 — `RiskConfig`, `AccountRiskConfig`, `CrossStrategyRiskConfig` (Pydantic models with validators)
   - `argus/core/risk_manager.py` lines 298–340 — concentration limit + min risk floor rejection logic
   - `argus/backtest/walk_forward.py` lines 780–808 — `_validate_oos_backtest_engine()` (builds BacktestEngineConfig)
   - `config/risk_limits.yaml` — production values: `min_position_risk_dollars: 100.0`, `max_single_stock_pct: 0.05`, `cash_reserve_pct: 0.20`
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/backtest/ -x -q
   ```
   Expected: all passing (~383 tests)
3. Verify you are on branch: `main`

## Objective
Add a `risk_overrides` mechanism to `BacktestEngineConfig` so that backtests can relax production risk constraints that are inappropriate for single-strategy validation. This addresses DEC-359: production rules (5% concentration, $100 min risk floor) cause Risk Manager to reject all signals in single-strategy backtests where tight stops produce low per-share risk.

## Problem Summary
The rejection chain in ORB backtests:
1. Legacy sizing computes shares correctly (21.6.1 fix ✓)
2. Concentration limit (5% single-stock) reduces shares drastically for high-priced stocks
3. Reduced shares × tight ORB stop = dollar risk well below $100 floor → ALL signals rejected
4. Result: zero trades despite valid signals

## Requirements

### 1. Add `risk_overrides` field to `BacktestEngineConfig`

In `argus/backtest/config.py`, add to `BacktestEngineConfig`:

```python
# Risk overrides for single-strategy backtesting (DEC-359)
# Applied on top of risk_limits.yaml to relax constraints that are
# inappropriate for isolated strategy validation.
risk_overrides: dict[str, Any] = Field(default_factory=lambda: {
    "account.min_position_risk_dollars": 1.0,
    "account.cash_reserve_pct": 0.05,
    "cross_strategy.max_single_stock_pct": 0.50,
})
```

The defaults are permissive backtest values:
- `min_position_risk_dollars: 1.0` — effectively removes the $100 floor (Pydantic: `gt=0`, so 1.0 is valid)
- `cash_reserve_pct: 0.05` — 5% reserve instead of 20% (Pydantic: `ge=0, le=0.5`, so 0.05 is valid)
- `max_single_stock_pct: 0.50` — 50% instead of 5% (Pydantic: `gt=0, le=0.5`, so 0.50 is the maximum allowed)

Using a dict with dot-separated keys (same convention as `config_overrides`) keeps the interface consistent.

### 2. Apply risk overrides in `_load_risk_config()`

In `argus/backtest/engine.py`, modify `_load_risk_config()`:

```python
def _load_risk_config(self, config_dir: Path) -> RiskConfig:
    """Load risk configuration from YAML, then apply backtest overrides.

    Args:
        config_dir: Path to the config directory.

    Returns:
        RiskConfig with backtest risk_overrides applied.
    """
    risk_file = config_dir / "risk_limits.yaml"
    if risk_file.exists():
        data = load_yaml_file(risk_file)
        risk_config = RiskConfig(**data)
    else:
        risk_config = RiskConfig()

    # Apply backtest risk overrides (DEC-359)
    for key, value in self._config.risk_overrides.items():
        parts = key.split(".", 1)
        if len(parts) == 2:
            section, field = parts
            sub_config = getattr(risk_config, section, None)
            if sub_config is not None and hasattr(sub_config, field):
                setattr(sub_config, field, value)
                logger.debug("Risk override applied: %s = %s", key, value)
            else:
                logger.warning("Unknown risk override key: %s", key)

    return risk_config
```

**Key requirements:**
- Apply overrides AFTER loading from YAML (override, not replace)
- Use `setattr` to bypass Pydantic validators on individual fields (the dict was already validated at BacktestEngineConfig construction time — the values are known-safe)
- Log each override at DEBUG level for transparency
- Warn on unrecognized keys

### 3. No changes to revalidation script or walk-forward

The `risk_overrides` field has sensible defaults in the `BacktestEngineConfig` definition. This means:
- `_validate_oos_backtest_engine()` in walk_forward.py already creates a `BacktestEngineConfig` — it gets the defaults automatically
- `run_backtest_engine_fallback()` in revalidate_strategy.py already creates a `BacktestEngineConfig` — same thing
- No changes needed in either file

If someone wants production-equivalent risk for a specific backtest, they can pass `risk_overrides={}` (empty dict) to explicitly opt out.

## Constraints
- Do NOT modify: `argus/core/risk_manager.py`, `argus/core/config.py`, any strategy file, any execution file, any frontend file, any API file
- Do NOT modify: `config/risk_limits.yaml` (production values stay unchanged)
- Do NOT modify: `argus/backtest/walk_forward.py`, `scripts/revalidate_strategy.py`
- Do NOT change: Risk Manager logic, signal evaluation behavior, or any risk gating rules
- The override mechanism is ONLY in BacktestEngine — production code in `main.py` is never affected

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to add in `tests/backtest/test_engine_sizing.py` (extending 21.6.1's file):
  1. `test_risk_overrides_applied` — create BacktestEngine with default risk_overrides, verify `_load_risk_config()` returns a RiskConfig with `min_position_risk_dollars=1.0`, `max_single_stock_pct=0.50`, `cash_reserve_pct=0.05`
  2. `test_risk_overrides_empty_uses_production` — create with `risk_overrides={}`, verify RiskConfig matches production YAML values
  3. `test_risk_overrides_partial` — pass only `{"account.min_position_risk_dollars": 5.0}`, verify that field is 5.0 but other defaults are still applied (because the default dict has all three)
  4. `test_risk_overrides_unknown_key_warns` — pass `{"bogus.field": 42}`, verify it logs a warning and doesn't crash
- Minimum new test count: 4
- Test command: `python -m pytest tests/backtest/test_engine_sizing.py -x -q`

## Definition of Done
- [ ] `BacktestEngineConfig.risk_overrides` field exists with sensible defaults
- [ ] `_load_risk_config()` applies overrides after YAML load
- [ ] Default overrides enable single-strategy backtesting without zero-trade rejections
- [ ] 4+ new tests passing
- [ ] All existing tests still pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Production risk_limits.yaml unchanged | `git diff config/risk_limits.yaml` shows no changes |
| Existing backtest tests pass | `python -m pytest tests/backtest/ -x -q` |
| Risk Manager code unchanged | `git diff argus/core/risk_manager.py` shows no changes |
| Default overrides are Pydantic-safe values | All within field validators (1.0 > 0, 0.05 in [0, 0.5], 0.50 in (0, 0.5]) |
| Empty overrides = production behavior | `test_risk_overrides_empty_uses_production` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-21.6/session-21.6.2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The close-out report path: `docs/sprints/sprint-21.6/session-21.6.2-closeout.md`
2. The diff range: `git diff HEAD~1`
3. The test command: `python -m pytest tests/backtest/test_engine_sizing.py -x -q`
4. Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/core/config.py`, any file in `argus/strategies/`, `argus/execution/`, `argus/ui/`, `argus/api/`, `config/risk_limits.yaml`, `argus/backtest/walk_forward.py`, `scripts/revalidate_strategy.py`

The @reviewer will write its report to:
`docs/sprints/sprint-21.6/session-21.6.2-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out and review report files per the Post-Review Fix Documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `risk_overrides` default values are within Pydantic validator ranges for their target fields (gt, ge, le constraints)
2. Verify `setattr` on Pydantic sub-models actually persists (Pydantic v2 models may need `model_config = ConfigDict(frozen=False)` or similar — check if AccountRiskConfig and CrossStrategyRiskConfig are frozen)
3. Verify `_load_risk_config()` applies overrides AFTER YAML load, not before
4. Verify no changes to `risk_manager.py` or `config/risk_limits.yaml`
5. Verify the override mechanism cannot be triggered from production code paths (`main.py`)

## Escalation Criteria
1. If Pydantic model freezing prevents `setattr` on risk config sub-models → need alternative approach (dict mutation before construction, or model_copy)
2. If default overrides cause existing backtest tests to fail (tests that assumed production risk values) → may need to explicitly set `risk_overrides={}` in those tests
