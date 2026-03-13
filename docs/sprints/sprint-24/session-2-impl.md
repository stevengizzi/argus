# Sprint 24, Session 2: VWAP Reclaim + Afternoon Momentum Pattern Strength

## Pre-Flight Checks
1. Read these files:
   - `argus/core/events.py` (updated SignalEvent from Session 1)
   - `argus/strategies/vwap_reclaim.py`
   - `argus/strategies/afternoon_momentum.py`
   - `argus/strategies/base_strategy.py`
2. Run scoped test baseline (Session 2+):
   `python -m pytest tests/strategies/test_vwap_reclaim.py tests/strategies/test_afternoon_momentum.py -x -q`
3. Verify branch: `sprint-24`

## Objective
Implement pattern_strength scoring for VWAP Reclaim and Afternoon Momentum. Update signal builders to set share_count=0. Populate signal_context with strategy-specific factor values.

## Requirements

### 1. In `argus/strategies/vwap_reclaim.py`:

Add `_calculate_pattern_strength()` method. Scoring factors:

- **State machine path quality (30%):** Clean pullback→hold→reclaim = 85. If the state machine went through extra transitions (e.g., re-testing, choppy hold) = 40–60 depending on number of extra transitions. Derive from the state history already tracked.
- **Pullback depth (25%):** Distance of pullback low from VWAP, relative to entry-to-VWAP distance. Optimal range (0.3–0.5×) = 80. Too shallow (<0.2×) or too deep (>0.7×) = 35. Parabolic curve peaking at 0.4×.
- **Reclaim volume (25%):** Volume on reclaim candle vs average pullback candle volume. Ratio >1.5× = 80, 1.0× = 50, <0.8× = 30. Linear.
- **Distance-to-VWAP (20%):** At signal time. At VWAP = 90, 0.5% away = 60, >1% away = 40. Linear.

Set `share_count=0` in signal builder. Populate `signal_context` with:
```python
{"path_quality": "clean", "pullback_depth_ratio": 0.4, "reclaim_volume_ratio": 1.8,
 "vwap_distance_pct": 0.002, "path_credit": 85.0, "depth_credit": 80.0,
 "volume_credit": 72.0, "distance_credit": 85.0}
```

### 2. In `argus/strategies/afternoon_momentum.py`:

Add `_calculate_pattern_strength()` method. Scoring factors:

- **Entry condition margin (35%):** For each of the 8 entry conditions, assess how far above threshold the actual value is. >10% above = full credit per condition. At threshold = 50% credit. Average across conditions, scale to 0–100.
- **Consolidation tightness (25%):** Consolidation range / ATR. Tighter = better. Ratio 0.3 = 90, 0.5 = 65, 0.8 = 40. Linear.
- **Volume surge (25%):** Breakout candle volume / consolidation average volume. >2.0× = 85, 1.5× = 65, <1.2× = 30. Linear.
- **Time-in-window (15%):** Minutes remaining in operating window (2:00–3:30 PM). At 2:00 (90 min remaining) = 80. At 3:00 (30 min) = 50. At 3:15 (15 min) = 35. Linear.

Set `share_count=0`. Populate `signal_context` with raw values and per-factor credits.

## Constraints
- Do NOT modify: `argus/strategies/orb_base.py`, `argus/strategies/orb_breakout.py`, `argus/strategies/orb_scalp.py`, `argus/core/events.py`, `argus/core/risk_manager.py`, `argus/backtest/*`
- Do NOT change: entry/exit logic. Same conditions trigger signals.

## Test Targets
- New tests:
  - `test_vwap_pattern_strength_varies_with_path_quality`: Clean path → higher score
  - `test_vwap_pattern_strength_varies_with_pullback_depth`: Optimal depth → higher score
  - `test_vwap_pattern_strength_varies_with_reclaim_volume`: Higher ratio → higher score
  - `test_vwap_pattern_strength_range`: All outputs in [0, 100]
  - `test_vwap_signal_share_count_zero`: share_count=0 on signal
  - `test_vwap_signal_context_populated`: Contains expected keys
  - `test_afmo_pattern_strength_varies_with_conditions`: More margin → higher score
  - `test_afmo_pattern_strength_varies_with_tightness`: Tighter consolidation → higher
  - `test_afmo_pattern_strength_varies_with_volume_surge`: Higher surge → higher
  - `test_afmo_pattern_strength_time_factor`: Earlier in window → higher
  - `test_afmo_signal_share_count_zero`: share_count=0
  - `test_afmo_signal_context_populated`: Contains expected keys
- Minimum new test count: 12
- Test command: `python -m pytest tests/strategies/test_vwap_reclaim.py tests/strategies/test_afternoon_momentum.py -x -q`

## Definition of Done
- [ ] VWAP Reclaim produces varied pattern_strength scores
- [ ] Afternoon Momentum produces varied pattern_strength scores
- [ ] Both set share_count=0
- [ ] Both populate signal_context with factor values
- [ ] All existing tests pass
- [ ] 12+ new tests passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| VWAP Reclaim same signals under same conditions | Existing VWAP tests pass |
| Afternoon Momentum same signals under same conditions | Existing AfMo tests pass |
| No ORB files modified | `git diff --name-only` shows no orb_*.py |

## Close-Out
Follow `.claude/skills/close-out.md`. Write report to `docs/sprints/sprint-24/session-2-closeout.md`.

## Sprint-Level Regression Checklist
*(Same as Session 1 — see review-context.md)*

## Sprint-Level Escalation Criteria
*(Same as Session 1 — see review-context.md)*
