# Sprint 24, Session 1: SignalEvent Enrichment + ORB Family Pattern Strength

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` (SignalEvent definition)
   - `argus/strategies/orb_base.py` (ORB base class with signal building)
   - `argus/strategies/orb_breakout.py` (breakout signal builder)
   - `argus/strategies/orb_scalp.py` (scalp signal builder)
   - `argus/data/service.py` (DataService interface for indicator queries)
2. Run test baseline (Session 1 — full suite):
   `python -m pytest tests/ -x -q -n auto`
   Expected: 2,532 tests, all passing
3. Verify branch: `sprint-24` (create from main if needed)

## Objective
Add `pattern_strength`, `signal_context`, `quality_score`, `quality_grade` fields to SignalEvent. Add QualitySignalEvent (informational event for UI). Implement pattern strength scoring for ORB Breakout and ORB Scalp via shared logic in OrbBaseStrategy. Update all ORB signal builders to set `share_count=0`.

## Requirements

### 1. In `argus/core/events.py`:

Add four fields to `SignalEvent` frozen dataclass (after existing fields):
```python
pattern_strength: float = 50.0  # 0-100, strategy-assessed signal quality
signal_context: dict = field(default_factory=dict)  # Strategy-specific metadata
quality_score: float = 0.0  # Populated by Quality Engine after scoring
quality_grade: str = ""  # Populated by Quality Engine after scoring
```

Add new `QualitySignalEvent` frozen dataclass (in Intelligence events section):
```python
@dataclass(frozen=True)
class QualitySignalEvent(Event):
    """Informational event published for UI consumers after quality scoring.
    Does NOT participate in execution pipeline."""
    symbol: str = ""
    strategy_id: str = ""
    score: float = 0.0
    grade: str = ""
    risk_tier: str = ""
    components: dict = field(default_factory=dict)
    rationale: str = ""
```

### 2. In `argus/strategies/orb_base.py`:

Add a `_calculate_pattern_strength()` method to `OrbBaseStrategy` that computes a 0–100 score from ORB-specific factors. All ORB family strategies share this logic.

```python
def _calculate_pattern_strength(
    self, candle: CandleEvent, state: OrbSymbolState,
    volume_ratio: float, atr_ratio: float | None
) -> tuple[float, dict]:
    """Calculate ORB family pattern strength (0-100) and context dict."""
```

**Scoring factors (weighted combination):**
- **Volume ratio credit (30%):** Maps volume_ratio (actual / threshold). At threshold (1.0×) = 40, at 2.0× = 65, at 3.0× = 90. Linear interpolation, clamped [10, 95].
- **ATR ratio credit (25%):** Maps OR range / ATR ratio. Mid-range of configured [min_range_atr_ratio, max_range_atr_ratio] = 80. At extremes = 30. Parabolic curve (peak at midpoint).
- **Chase distance credit (25%):** How close breakout is to OR high. At OR high = 90, at chase_protection_pct limit = 30. Linear.
- **VWAP position credit (20%):** Distance above VWAP. Just above (0-0.2%) = 50, 0.5% above = 70, 1%+ = 80. Clamped at 85 (diminishing returns).

Returns `(pattern_strength, signal_context_dict)` where signal_context contains:
```python
{"volume_ratio": 2.3, "atr_ratio": 0.68, "chase_distance_pct": 0.002, "vwap_distance_pct": 0.005,
 "volume_credit": 65.0, "atr_credit": 78.0, "chase_credit": 75.0, "vwap_credit": 60.0}
```

### 3. In `argus/strategies/orb_breakout.py`:

Modify `_build_breakout_signal()` to:
- Call `self._calculate_pattern_strength()` with breakout-specific data
- Set `share_count=0` (Dynamic Sizer will calculate in Sprint 24 Session 6a)
- Set `pattern_strength` and `signal_context` on the SignalEvent

### 4. In `argus/strategies/orb_scalp.py`:

Same changes as orb_breakout.py — update the signal builder to call `_calculate_pattern_strength()`, set `share_count=0`, and populate `pattern_strength` + `signal_context`.

## Constraints
- Do NOT modify: `argus/strategies/base_strategy.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/risk_manager.py`, `argus/backtest/*`
- Do NOT change: strategy entry/exit logic (same conditions still trigger signals)
- Do NOT change: existing `calculate_position_size()` method signature (it still exists but share_count=0 means it's no longer called in the signal builder)
- Preserve backward compatibility: existing code constructing SignalEvent without new fields must still work (default values handle this)

## Test Targets
- Existing tests: all must still pass
- New tests to write:
  - `test_signal_event_new_fields_defaults`: SignalEvent() has pattern_strength=50, signal_context={}, quality_score=0.0, quality_grade=""
  - `test_signal_event_backward_compatible`: SignalEvent(strategy_id="x", symbol="AAPL", ...) works without new fields
  - `test_quality_signal_event_creation`: QualitySignalEvent fields populated correctly
  - `test_orb_pattern_strength_varies_with_volume`: Higher volume ratio → higher pattern_strength
  - `test_orb_pattern_strength_varies_with_atr`: Mid-range ATR ratio → higher than extremes
  - `test_orb_pattern_strength_varies_with_chase`: Closer to OR high → higher score
  - `test_orb_pattern_strength_varies_with_vwap`: Further above VWAP → higher (with diminishing returns)
  - `test_orb_pattern_strength_range`: All outputs in [0, 100] across varied inputs
  - `test_orb_signal_context_populated`: signal_context dict contains expected keys
  - `test_orb_breakout_share_count_zero`: ORB Breakout signal has share_count=0
  - `test_orb_scalp_share_count_zero`: ORB Scalp signal has share_count=0
  - `test_orb_breakout_pattern_strength_populated`: Signal has pattern_strength != 50.0
  - `test_orb_scalp_pattern_strength_populated`: Signal has pattern_strength != 50.0
  - `test_orb_pattern_strength_at_least_3_distinct_buckets`: With varied inputs, at least 3 different scores >= 10 apart
  - Tests for edge cases: volume_ratio=0, atr_ratio=None, state with missing OR data
- Minimum new test count: 16
- Test command: `python -m pytest tests/core/test_events.py tests/strategies/ -x -q`

## Definition of Done
- [ ] SignalEvent has 4 new fields with correct defaults
- [ ] QualitySignalEvent defined in events.py
- [ ] OrbBaseStrategy._calculate_pattern_strength() produces varied 0-100 scores
- [ ] ORB Breakout and ORB Scalp signal builders set share_count=0
- [ ] ORB Breakout and ORB Scalp populate pattern_strength and signal_context
- [ ] All existing tests pass
- [ ] 16+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| SignalEvent backward compatible | `SignalEvent(strategy_id="x", symbol="AAPL", side=Side.LONG, entry_price=100, stop_price=95, target_prices=(105,), share_count=50, rationale="test")` constructs without error |
| ORB Breakout still fires under same conditions | Existing ORB breakout tests pass (signal generation unchanged) |
| ORB Scalp still fires under same conditions | Existing ORB scalp tests pass |
| No backtest files modified | `git diff --name-only` shows no `argus/backtest/` files |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

**Write the close-out report to:** `docs/sprints/sprint-24/session-1-closeout.md`

## Sprint-Level Regression Checklist
*(See review-context.md — embedded in implementation prompt for implementer reference)*

### Core Trading Pipeline
- [ ] All 4 strategies produce SignalEvents when entry criteria met
- [ ] No strategy entry/exit logic altered
- [ ] Circuit breakers non-overridable
- [ ] Event Bus FIFO ordering maintained

### Signal Integrity
- [ ] SignalEvent backward compatible (existing constructors work)
- [ ] Enriched signal preserves all original fields

### Tests
- [ ] All 2,532 existing pytest pass
- [ ] All 446 existing Vitest pass

## Sprint-Level Escalation Criteria
1. Quality Engine exception blocks ALL trading → investigate immediately
2. Canary test failure → halt
3. Existing test suite regression → halt current session
3a. Backtest bypass failure → halt
7. Pattern strength scores cluster <10-point spread → escalate
