---BEGIN-REVIEW---

# Tier 2 Review -- Sprint 21.6.2, Session 1

**Reviewer:** @reviewer subagent
**Date:** 2026-03-23
**Verdict:** CLEAR

## Diff Analysis

The commit modifies 3 source files and adds 1 documentation file:

1. **argus/backtest/config.py** -- Added `risk_overrides` field to `BacktestEngineConfig` with a `default_factory` lambda providing 3 permissive override entries for backtesting.
2. **argus/backtest/engine.py** -- Modified `_load_risk_config()` to iterate `risk_overrides`, parse dot-separated keys into (section, field), and apply via `setattr` on the appropriate Pydantic sub-model. Includes debug logging on success and warning on unrecognized keys.
3. **tests/backtest/test_engine_sizing.py** -- Added 4 new tests: default overrides applied, empty overrides preserve production values, partial custom overrides, and unknown key warning.
4. **docs/sprints/sprint-21.6/session-21.6.2-closeout.md** -- Close-out report.

Total diff is small and focused (~90 lines of production code + tests). No unrelated changes.

## Spec Compliance

| Spec Requirement | Status | Notes |
|-----------------|--------|-------|
| Add `risk_overrides` field to `BacktestEngineConfig` | DONE | Matches spec exactly (same field name, type, defaults) |
| Apply risk overrides in `_load_risk_config()` after YAML load | DONE | Override loop runs after `RiskConfig(**data)` construction |
| No changes to walk_forward.py or revalidate_strategy.py | DONE | Neither file appears in diff |
| No changes to risk_manager.py or risk_limits.yaml | DONE | Neither file appears in diff |
| 4+ new tests | DONE | 4 tests added, all passing |
| All existing tests pass | DONE | 8/8 pass in test_engine_sizing.py |
| Default overrides enable single-strategy backtesting | DONE | $1 floor, 5% reserve, 50% concentration |

Implementation matches the spec verbatim -- the code in the diff is character-for-character what the spec prescribed.

## Session-Specific Checks

### 1. Default values within Pydantic validator ranges

Verified against `argus/core/config.py`:

| Override Key | Value | Pydantic Constraint | Valid? |
|-------------|-------|-------------------|--------|
| `account.min_position_risk_dollars` | 1.0 | `gt=0` | Yes (1.0 > 0) |
| `account.cash_reserve_pct` | 0.05 | `ge=0, le=0.5` | Yes (0 <= 0.05 <= 0.5) |
| `cross_strategy.max_single_stock_pct` | 0.50 | `gt=0, le=0.5` | Yes (0 < 0.50 <= 0.5) |

All three defaults are within their respective Pydantic field constraints.

### 2. setattr persistence on Pydantic v2 sub-models

Confirmed:
- Pydantic version: 2.10.5
- `AccountRiskConfig` and `CrossStrategyRiskConfig` are plain `BaseModel` subclasses with no `model_config` / `ConfigDict(frozen=True)` -- `setattr` works and persists.
- Independently verified: `setattr` on Pydantic v2 non-frozen models does NOT trigger field validators. This means an out-of-range override value (e.g., `cash_reserve_pct: 0.99`) would silently bypass the `le=0.5` constraint. The spec explicitly anticipated this: "Use setattr to bypass Pydantic validators on individual fields (the dict was already validated at BacktestEngineConfig construction time -- the values are known-safe)." The defaults are safe; user-provided overrides carry responsibility. This is acceptable for a backtest-only configuration path.

### 3. Override application order

`_load_risk_config()` first loads `RiskConfig` from YAML (or defaults), then iterates `risk_overrides` and applies via `setattr`. Overrides are applied AFTER YAML load. Correct.

### 4. No changes to risk_manager.py or risk_limits.yaml

Confirmed via `git diff HEAD~1 --name-only`. Neither `argus/core/risk_manager.py` nor `config/risk_limits.yaml` appears in the changed file list.

### 5. Override mechanism isolated from production code paths

- `main.py` does not import `BacktestEngineConfig` or `BacktestEngine` (confirmed via grep).
- The `risk_overrides` field only exists on `BacktestEngineConfig`, which is only constructed in `argus/backtest/engine.py` (CLI), `argus/backtest/walk_forward.py` (OOS validation), and test files.
- Production startup (`main.py`) loads risk config via `RiskConfig` directly from `config/risk_limits.yaml` through `SystemConfig` -- a completely separate code path.
- The override mechanism cannot be triggered from production.

## Forbidden File Check

| File/Pattern | Modified? |
|-------------|-----------|
| `argus/core/risk_manager.py` | No |
| `argus/core/config.py` | No |
| `argus/strategies/*` | No |
| `argus/execution/*` | No |
| `argus/ui/*` | No |
| `argus/api/*` | No |
| `config/risk_limits.yaml` | No |
| `argus/backtest/walk_forward.py` | No |
| `scripts/revalidate_strategy.py` | No |

No forbidden files were modified.

## Test Verification

```
python -m pytest tests/backtest/test_engine_sizing.py -x -q
8 passed in 0.04s
```

All 8 tests pass (4 pre-existing + 4 new). The 4 new tests cover:
1. Default overrides applied correctly
2. Empty overrides preserve production YAML values
3. Partial custom overrides only affect specified fields
4. Unknown override key logs warning without crashing

## Findings

**No blocking issues.**

One observation worth noting for future reference (non-blocking):

- **setattr bypasses Pydantic validators:** As confirmed by testing, `setattr` on Pydantic v2 models does not enforce field-level constraints (`gt`, `ge`, `le`). If a future caller passes an out-of-range value in `risk_overrides` (e.g., `cash_reserve_pct: 5.0`), it would be silently accepted. The spec explicitly chose this tradeoff and documented it. If validation of user-provided overrides becomes desirable later, `model_validate` or `model_copy(update=...)` on the sub-models would enforce constraints. This is a design choice, not a bug.

## Verdict Rationale

CLEAR. The implementation matches the spec exactly -- the code is verbatim from the spec's code blocks. All 5 session-specific review focus items check out. No forbidden files were modified. All tests pass. The setattr/validator bypass is explicitly acknowledged in both the spec and the close-out report. The change is small, focused, and correct.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "21.6.2",
  "session": "S1",
  "verdict": "CLEAR",
  "findings": [
    {
      "severity": "low",
      "category": "design_observation",
      "description": "setattr on Pydantic v2 models bypasses field validators. Out-of-range user-provided risk_overrides values would be silently accepted. Spec explicitly chose this tradeoff. Non-blocking.",
      "file": "argus/backtest/engine.py",
      "line": 958
    }
  ],
  "tests_pass": true,
  "test_count": 8,
  "forbidden_files_clean": true,
  "spec_compliance": "full",
  "escalation_triggers": []
}
```
