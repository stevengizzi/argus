# Sprint 26, Session 2: RedToGreenConfig + State Machine Skeleton

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/base_strategy.py` (BaseStrategy — do NOT modify)
   - `argus/strategies/vwap_reclaim.py` (state machine reference)
   - `argus/core/config.py` (existing config classes + loader pattern)
   - `argus/core/events.py` (SignalEvent — do NOT modify)
   - `argus/models/strategy.py` (ScannerCriteria, ExitRules, MarketConditionsFilter)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/strategies/ -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on the correct branch

## Objective
Create the RedToGreenStrategy skeleton with 5-state machine, per-symbol state tracking, config model, YAML config, and state transition tests. Entry criteria details are completed in Session 3.

## Requirements

1. **Create `config/strategies/red_to_green.yaml`:**
   ```yaml
   strategy_id: "strat_red_to_green"
   name: "Red-to-Green"
   version: "1.0.0"
   enabled: true
   asset_class: "us_stocks"
   pipeline_stage: "exploration"
   family: "reversal"
   description_short: "Gap-down reversal at key support levels (VWAP, premarket low, prior close)."
   time_window_display: "9:45–11:00 AM"

   operating_window:
     earliest_entry: "09:45"
     latest_entry: "11:00"
     force_close: "15:50"

   min_gap_down_pct: 0.02      # Minimum gap down (2%)
   max_gap_down_pct: 0.10      # Maximum gap down (10%) — beyond this, thesis is too risky
   level_proximity_pct: 0.003  # Within 0.3% of key level to trigger TESTING_LEVEL
   min_level_test_bars: 2      # Min bars at level before entry
   volume_confirmation_multiplier: 1.2
   max_chase_pct: 0.003        # Don't chase if >0.3% above level
   max_level_attempts: 2       # Max levels to try before EXHAUSTED
   target_1_r: 1.0
   target_2_r: 2.0
   time_stop_minutes: 20
   stop_buffer_pct: 0.001

   risk_limits:
     max_loss_per_trade_pct: 0.01
     max_daily_loss_pct: 0.03
     max_trades_per_day: 6
     max_concurrent_positions: 2

   benchmarks:
     min_win_rate: 0.40
     min_profit_factor: 1.1
     min_sharpe: 0.3
     max_drawdown_pct: 0.12

   backtest_summary:
     status: "not_validated"

   universe_filter:
     min_price: 5.0
     max_price: 200.0
     min_avg_volume: 500000
   ```

2. **Add to `argus/core/config.py`:**

   a. `RedToGreenConfig(StrategyConfig)` class:
      - Fields matching all YAML keys above with appropriate types, defaults, and Field validators
      - `model_validator(mode="after")`: min_gap_down_pct < max_gap_down_pct
      - Place after `AfternoonMomentumConfig`

   b. `load_red_to_green_config(path: Path) -> RedToGreenConfig` loader function:
      - Follow exact pattern of `load_vwap_reclaim_config()`

3. **Create `argus/strategies/red_to_green.py`:**

   a. **`RedToGreenState` StrEnum:**
      - `WATCHING` — initial, waiting for gap confirmation
      - `GAP_DOWN_CONFIRMED` — stock gapped down, looking for key levels
      - `TESTING_LEVEL` — price approaching/testing a key support level
      - `ENTERED` — position taken (terminal)
      - `EXHAUSTED` — gave up (terminal): gap too large, max attempts, window expired

   b. **`KeyLevelType` StrEnum:**
      - `VWAP`, `PREMARKET_LOW`, `PRIOR_CLOSE`

   c. **`RedToGreenSymbolState` dataclass:**
      - `state: RedToGreenState = RedToGreenState.WATCHING`
      - `gap_pct: float = 0.0`
      - `current_level_type: KeyLevelType | None = None`
      - `current_level_price: float = 0.0`
      - `level_test_bars: int = 0`
      - `level_attempts: int = 0`
      - `premarket_low: float = 0.0`
      - `prior_close: float = 0.0`
      - `exhaustion_reason: str = ""`

   d. **`RedToGreenStrategy(BaseStrategy)` class skeleton:**
      - `__init__(self, config: RedToGreenConfig, data_service=None, clock=None)` — store config, init `_symbol_states: dict[str, RedToGreenSymbolState]`
      - `async def on_candle(self, event: CandleEvent) -> SignalEvent | None:` — route to state handlers:
        - Check if symbol in watchlist (return None if not)
        - Get/create per-symbol state
        - Route to `_handle_watching()`, `_handle_gap_confirmed()`, `_handle_testing_level()` based on state
        - Terminal states (ENTERED, EXHAUSTED) → return None
      - `_handle_watching(symbol, candle, state) -> RedToGreenState` — check if gap_pct < -min_gap_down_pct; if so → GAP_DOWN_CONFIRMED. If gap > max_gap_down_pct → EXHAUSTED
      - `_handle_gap_confirmed(symbol, candle, state) -> RedToGreenState` — identify nearest key level, check proximity → TESTING_LEVEL. After max_level_attempts → EXHAUSTED
      - `_handle_testing_level(symbol, candle, state) -> tuple[RedToGreenState, SignalEvent | None]` — STUB returning (current_state, None). Full implementation in S3.
      - `async def on_tick(self, event)` — pass (no tick-based management for R2G V1)
      - `def reset_daily_state(self)` — clear `_symbol_states`, call super
      - `async def reconstruct_state(self, trade_logger)` — STUB (full implementation S3)
      - `def get_scanner_criteria(self) -> ScannerCriteria` — STUB returning basic criteria
      - `def calculate_position_size(self, entry, stop) -> int` — return 0 (Quality Engine handles)
      - `def get_exit_rules(self) -> ExitRules` — STUB
      - `def get_market_conditions_filter(self) -> MarketConditionsFilter` — STUB
      - Evaluation telemetry: `record_evaluation()` calls on state transitions

4. **Update `argus/strategies/__init__.py`:**
   - Add `from argus.strategies.red_to_green import RedToGreenStrategy`

## Constraints
- Do NOT modify `argus/strategies/base_strategy.py`
- Do NOT modify any existing strategy files
- Do NOT modify `argus/core/events.py`
- Do NOT wire R2G into main.py yet (that's S9)
- STUBs are acceptable for methods completed in S3 — mark with `# TODO: Sprint 26 S3`

## Config Validation
Write a test that loads `config/strategies/red_to_green.yaml` and verifies all keys are recognized by `RedToGreenConfig`:
1. Load YAML, extract top-level + nested keys
2. Compare against `RedToGreenConfig.model_fields.keys()`
3. Assert no silently ignored keys

## Test Targets
New tests in `tests/strategies/test_red_to_green.py`:
1. `test_config_loads_from_yaml` — load red_to_green.yaml, verify all fields populated
2. `test_config_yaml_key_validation` — no silently ignored keys
3. `test_config_gap_validator` — min < max passes, min >= max raises ValueError
4. `test_state_machine_watching_to_gap_confirmed` — mock candle with gap < -2% triggers transition
5. `test_state_machine_watching_ignores_gap_up` — positive gap stays WATCHING
6. `test_state_machine_watching_to_exhausted_large_gap` — gap > max → EXHAUSTED
7. `test_state_machine_gap_confirmed_to_testing_level` — price near VWAP → TESTING_LEVEL
8. `test_state_machine_max_level_attempts_exhaustion` — after max_level_attempts → EXHAUSTED
- Minimum new test count: 8
- Test command: `python -m pytest tests/strategies/test_red_to_green.py -x -v`

## Definition of Done
- [ ] `config/strategies/red_to_green.yaml` created with all parameters
- [ ] `RedToGreenConfig` class with validator in config.py
- [ ] `load_red_to_green_config()` loader function
- [ ] `RedToGreenStrategy` skeleton with state machine routing
- [ ] State transitions WATCHING→GAP_DOWN_CONFIRMED and GAP_DOWN_CONFIRMED→TESTING_LEVEL implemented
- [ ] Terminal states (ENTERED, EXHAUSTED) return None
- [ ] Evaluation telemetry on state transitions
- [ ] All existing tests pass
- [ ] 8 new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-26/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Follow close-out skill in .claude/skills/close-out.md. Write to: `docs/sprints/sprint-26/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-26/review-context.md`
2. Close-out: `docs/sprints/sprint-26/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/test_red_to_green.py -x -v`
5. Do-not-modify: `argus/strategies/base_strategy.py`, `argus/core/events.py`, existing strategy files

## Session-Specific Review Focus (for @reviewer)
1. Verify RedToGreenConfig has model_validator for gap range
2. Verify config YAML keys match Pydantic model field names exactly
3. Verify state machine routes to correct handlers per state
4. Verify EXHAUSTED state is terminal (on_candle returns None immediately)
5. Verify evaluation telemetry on each state transition
6. Verify STUBs are clearly marked with `# TODO: Sprint 26 S3`

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md` — Escalation Criteria section.
