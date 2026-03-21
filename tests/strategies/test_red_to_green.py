"""Tests for the Red-to-Green strategy (Sprint 26, Sessions 2 + 3).

Tests cover:
- Config loading from YAML
- Config YAML key validation (no silently ignored keys)
- Config gap validator
- State machine transitions: WATCHING → GAP_DOWN_CONFIRMED
- State machine: gap up stays WATCHING
- State machine: large gap → EXHAUSTED
- State machine: GAP_DOWN_CONFIRMED → TESTING_LEVEL
- State machine: max level attempts → EXHAUSTED
- S3: Entry at VWAP level, entry at prior close
- S3: Entry rejected — no volume, chase, outside window
- S3: Level failure to GAP_DOWN_CONFIRMED
- S3: Pattern strength scoring and bounds
- S3: Scanner criteria negative gap, market conditions filter
- S3: Exit rules stop below level
- S3: Reconstruct state, signal share_count=0
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from argus.core.config import RedToGreenConfig, load_red_to_green_config, load_yaml_file
from argus.core.events import CandleEvent, Side, SignalEvent
from argus.strategies.red_to_green import (
    KeyLevelType,
    RedToGreenState,
    RedToGreenStrategy,
    RedToGreenSymbolState,
)

# Path to the YAML config
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "strategies" / "red_to_green.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides: object) -> RedToGreenConfig:
    """Build a RedToGreenConfig with sensible defaults, allowing overrides."""
    defaults: dict[str, object] = {
        "strategy_id": "strat_red_to_green",
        "name": "Red-to-Green",
        "version": "1.0.0",
        "min_gap_down_pct": 0.02,
        "max_gap_down_pct": 0.10,
        "level_proximity_pct": 0.003,
        "min_level_test_bars": 2,
        "volume_confirmation_multiplier": 1.2,
        "max_chase_pct": 0.003,
        "max_level_attempts": 2,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 20,
        "stop_buffer_pct": 0.001,
    }
    defaults.update(overrides)
    return RedToGreenConfig(**defaults)


def _make_candle(
    symbol: str = "TSLA",
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 50000,
) -> CandleEvent:
    """Build a CandleEvent with sensible defaults."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=datetime(2026, 3, 24, 14, 45, tzinfo=UTC),  # 10:45 ET
    )


def _make_strategy(config: RedToGreenConfig | None = None) -> RedToGreenStrategy:
    """Build a RedToGreenStrategy with default config."""
    cfg = config or _make_config()
    return RedToGreenStrategy(config=cfg)


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestRedToGreenConfig:
    """Tests for RedToGreenConfig and YAML loading."""

    def test_config_loads_from_yaml(self) -> None:
        """Load red_to_green.yaml and verify all fields are populated."""
        config = load_red_to_green_config(CONFIG_PATH)

        assert config.strategy_id == "strat_red_to_green"
        assert config.name == "Red-to-Green"
        assert config.version == "1.0.0"
        assert config.enabled is True
        assert config.pipeline_stage == "exploration"
        assert config.family == "reversal"
        assert config.min_gap_down_pct == 0.02
        assert config.max_gap_down_pct == 0.10
        assert config.level_proximity_pct == 0.003
        assert config.min_level_test_bars == 2
        assert config.volume_confirmation_multiplier == 1.2
        assert config.max_chase_pct == 0.003
        assert config.max_level_attempts == 2
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 20
        assert config.stop_buffer_pct == 0.001
        assert config.operating_window.earliest_entry == "09:45"
        assert config.operating_window.latest_entry == "11:00"
        assert config.risk_limits.max_trades_per_day == 6
        assert config.risk_limits.max_concurrent_positions == 2
        assert config.benchmarks.min_win_rate == 0.40
        assert config.benchmarks.max_drawdown_pct == 0.12
        assert config.backtest_summary.status == "vectorbt_module_ready"
        assert config.universe_filter is not None
        assert config.universe_filter.min_price == 5.0

    def test_config_yaml_key_validation(self) -> None:
        """Verify no silently ignored keys in the YAML config."""
        raw = load_yaml_file(CONFIG_PATH)

        # Collect all top-level keys from YAML
        yaml_keys = set(raw.keys())

        # Collect all field names from RedToGreenConfig (including inherited)
        model_fields = set(RedToGreenConfig.model_fields.keys())

        # Every YAML key should map to a model field
        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), (
            f"YAML keys not recognized by RedToGreenConfig: {unrecognized}"
        )

    def test_config_gap_validator_valid(self) -> None:
        """min_gap_down_pct < max_gap_down_pct passes validation."""
        config = _make_config(min_gap_down_pct=0.02, max_gap_down_pct=0.10)
        assert config.min_gap_down_pct < config.max_gap_down_pct

    def test_config_gap_validator_invalid(self) -> None:
        """min_gap_down_pct >= max_gap_down_pct raises ValueError."""
        with pytest.raises(ValidationError, match="min_gap_down_pct"):
            _make_config(min_gap_down_pct=0.10, max_gap_down_pct=0.05)

        with pytest.raises(ValidationError, match="min_gap_down_pct"):
            _make_config(min_gap_down_pct=0.05, max_gap_down_pct=0.05)


# ---------------------------------------------------------------------------
# State Machine Tests
# ---------------------------------------------------------------------------


class TestRedToGreenStateMachine:
    """Tests for RedToGreenStrategy state machine transitions."""

    @pytest.mark.asyncio
    async def test_state_machine_watching_to_gap_confirmed(self) -> None:
        """Mock candle with gap < -2% triggers WATCHING → GAP_DOWN_CONFIRMED."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = strategy._get_symbol_state("TSLA")
        state.prior_close = 100.0

        # Candle opens at 97.0 → gap = -3%
        candle = _make_candle(symbol="TSLA", open_=97.0, close=97.5)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.GAP_DOWN_CONFIRMED
        assert state.gap_pct == pytest.approx(-0.03)

    @pytest.mark.asyncio
    async def test_state_machine_watching_ignores_gap_up(self) -> None:
        """Positive gap stays WATCHING."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = strategy._get_symbol_state("TSLA")
        state.prior_close = 100.0

        # Candle opens at 103.0 → gap = +3%
        candle = _make_candle(symbol="TSLA", open_=103.0, close=103.5)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.WATCHING

    @pytest.mark.asyncio
    async def test_state_machine_watching_to_exhausted_large_gap(self) -> None:
        """Gap > max_gap_down_pct → EXHAUSTED."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = strategy._get_symbol_state("TSLA")
        state.prior_close = 100.0

        # Candle opens at 88.0 → gap = -12% (exceeds 10% max)
        candle = _make_candle(symbol="TSLA", open_=88.0, close=88.5)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.EXHAUSTED
        assert "exceeds max" in state.exhaustion_reason

    @pytest.mark.asyncio
    async def test_state_machine_gap_confirmed_to_testing_level(self) -> None:
        """Price near prior_close → GAP_DOWN_CONFIRMED → TESTING_LEVEL."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = strategy._get_symbol_state("TSLA")
        state.state = RedToGreenState.GAP_DOWN_CONFIRMED
        state.gap_pct = -0.03
        state.prior_close = 100.0

        # Close at 99.8 → 0.2% from prior_close (within 0.3% proximity)
        candle = _make_candle(symbol="TSLA", open_=97.0, close=99.8)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.TESTING_LEVEL
        assert state.current_level_type is not None
        assert state.level_attempts == 1

    @pytest.mark.asyncio
    async def test_state_machine_max_level_attempts_exhaustion(self) -> None:
        """After max_level_attempts → EXHAUSTED."""
        config = _make_config(max_level_attempts=2)
        strategy = _make_strategy(config)
        strategy.set_watchlist(["TSLA"])

        state = strategy._get_symbol_state("TSLA")
        state.state = RedToGreenState.GAP_DOWN_CONFIRMED
        state.gap_pct = -0.03
        state.prior_close = 100.0
        state.level_attempts = 2  # Already at max

        candle = _make_candle(symbol="TSLA", open_=97.0, close=99.8)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.EXHAUSTED
        assert "Max level attempts" in state.exhaustion_reason

    @pytest.mark.asyncio
    async def test_terminal_states_return_none(self) -> None:
        """Terminal states (ENTERED, EXHAUSTED) return None immediately."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        candle = _make_candle(symbol="TSLA")

        # ENTERED → None
        state = strategy._get_symbol_state("TSLA")
        state.state = RedToGreenState.ENTERED
        result = await strategy.on_candle(candle)
        assert result is None

        # EXHAUSTED → None
        state.state = RedToGreenState.EXHAUSTED
        result = await strategy.on_candle(candle)
        assert result is None

    @pytest.mark.asyncio
    async def test_non_watchlist_symbol_ignored(self) -> None:
        """Symbols not in watchlist return None without state changes."""
        strategy = _make_strategy()
        strategy.set_watchlist(["AAPL"])

        candle = _make_candle(symbol="TSLA")
        result = await strategy.on_candle(candle)

        assert result is None
        assert "TSLA" not in strategy._symbol_states

    def test_reset_daily_state_clears_symbols(self) -> None:
        """reset_daily_state() clears all per-symbol state."""
        strategy = _make_strategy()
        strategy._symbol_states["TSLA"] = RedToGreenSymbolState(
            state=RedToGreenState.GAP_DOWN_CONFIRMED
        )
        strategy._symbol_states["AAPL"] = RedToGreenSymbolState(
            state=RedToGreenState.TESTING_LEVEL
        )

        strategy.reset_daily_state()

        assert len(strategy._symbol_states) == 0
        assert strategy.trade_count_today == 0


# ---------------------------------------------------------------------------
# Session 3: Entry / Exit / Pattern Strength Tests
# ---------------------------------------------------------------------------


def _make_testing_level_state(
    prior_close: float = 100.0,
    level_type: KeyLevelType = KeyLevelType.PRIOR_CLOSE,
    level_price: float = 100.0,
    level_test_bars: int = 3,
    level_attempts: int = 1,
    gap_pct: float = -0.03,
    volumes: list[int] | None = None,
) -> RedToGreenSymbolState:
    """Build a symbol state in TESTING_LEVEL with defaults for entry checks."""
    return RedToGreenSymbolState(
        state=RedToGreenState.TESTING_LEVEL,
        gap_pct=gap_pct,
        current_level_type=level_type,
        current_level_price=level_price,
        level_test_bars=level_test_bars,
        level_attempts=level_attempts,
        premarket_low=0.0,
        prior_close=prior_close,
        recent_volumes=volumes if volumes is not None else [40000, 45000, 42000],
    )


def _make_entry_candle(
    symbol: str = "TSLA",
    close: float = 100.2,
    volume: int = 60000,
) -> CandleEvent:
    """Build a candle that should pass entry checks (within window, above level)."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=99.5,
        high=100.5,
        low=99.0,
        close=close,
        volume=volume,
        # 10:45 ET → within 09:45–11:00 window
        timestamp=datetime(2026, 3, 24, 14, 45, tzinfo=UTC),
    )


class TestRedToGreenEntry:
    """Tests for TESTING_LEVEL → ENTERED transition (Sprint 26 S3)."""

    @pytest.mark.asyncio
    async def test_entry_at_prior_close_level(self) -> None:
        """Candle near prior_close with volume → SignalEvent."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = _make_testing_level_state(
            prior_close=100.0,
            level_type=KeyLevelType.PRIOR_CLOSE,
            level_price=100.0,
        )
        strategy._symbol_states["TSLA"] = state

        # Close slightly above level, high volume
        candle = _make_entry_candle(close=100.2, volume=60000)
        signal = await strategy.on_candle(candle)

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert signal.symbol == "TSLA"
        assert signal.side == Side.LONG
        assert signal.entry_price == 100.2
        assert state.state == RedToGreenState.ENTERED

    @pytest.mark.asyncio
    async def test_entry_at_vwap_level(self) -> None:
        """Candle near VWAP level with volume → SignalEvent."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = _make_testing_level_state(
            level_type=KeyLevelType.VWAP,
            level_price=99.5,
        )
        strategy._symbol_states["TSLA"] = state

        candle = _make_entry_candle(close=99.7, volume=60000)
        signal = await strategy.on_candle(candle)

        assert signal is not None
        assert signal.entry_price == 99.7
        assert "vwap" in signal.rationale.lower()
        assert state.state == RedToGreenState.ENTERED

    @pytest.mark.asyncio
    async def test_entry_rejected_no_volume(self) -> None:
        """Volume below multiplier → no signal, stays TESTING_LEVEL."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = _make_testing_level_state()
        strategy._symbol_states["TSLA"] = state

        # Average volume ~42333, multiplier 1.2 → need ~50800. Volume 30000 fails.
        candle = _make_entry_candle(close=100.2, volume=30000)
        signal = await strategy.on_candle(candle)

        assert signal is None
        assert state.state == RedToGreenState.TESTING_LEVEL

    @pytest.mark.asyncio
    async def test_entry_rejected_chase(self) -> None:
        """Close too far above level → no signal (chase guard)."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        # max_chase_pct=0.003 → limit = 100.0 * 1.003 = 100.30
        state = _make_testing_level_state(level_price=100.0)
        strategy._symbol_states["TSLA"] = state

        # Close at 100.50 → above chase limit
        candle = _make_entry_candle(close=100.50, volume=60000)
        signal = await strategy.on_candle(candle)

        assert signal is None
        assert state.state == RedToGreenState.TESTING_LEVEL

    @pytest.mark.asyncio
    async def test_entry_rejected_outside_window(self) -> None:
        """Before earliest_entry → no signal."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        state = _make_testing_level_state()
        strategy._symbol_states["TSLA"] = state

        # 9:30 ET = 13:30 UTC → before 09:45 ET window
        candle = CandleEvent(
            symbol="TSLA",
            timeframe="1m",
            open=99.5,
            high=100.5,
            low=99.0,
            close=100.2,
            volume=60000,
            timestamp=datetime(2026, 3, 24, 13, 30, tzinfo=UTC),
        )
        signal = await strategy.on_candle(candle)

        assert signal is None
        assert state.state == RedToGreenState.TESTING_LEVEL

    @pytest.mark.asyncio
    async def test_level_failure_to_gap_confirmed(self) -> None:
        """Price drops far below level → back to GAP_DOWN_CONFIRMED."""
        config = _make_config(max_level_attempts=3)
        strategy = _make_strategy(config)
        strategy.set_watchlist(["TSLA"])

        # level_proximity_pct=0.003, drop threshold = 0.003*3 = 0.009
        # level=100, price drops to 98.5 → drop = 1.5% > 0.9%
        state = _make_testing_level_state(
            level_price=100.0,
            level_attempts=1,
        )
        strategy._symbol_states["TSLA"] = state

        candle = _make_entry_candle(close=98.5, volume=60000)
        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.GAP_DOWN_CONFIRMED


class TestRedToGreenPatternStrength:
    """Tests for _calculate_pattern_strength (Sprint 26 S3)."""

    def test_pattern_strength_scoring(self) -> None:
        """Verify score components and bounds (0–100)."""
        strategy = _make_strategy()
        candle = _make_entry_candle(close=100.2, volume=60000)
        state = _make_testing_level_state(
            level_type=KeyLevelType.VWAP,
            level_price=100.0,
            gap_pct=-0.03,
            level_test_bars=4,
        )

        strength, context = strategy._calculate_pattern_strength(
            candle, state, KeyLevelType.VWAP, volume_ratio=1.5,
        )

        assert 0.0 <= strength <= 100.0
        assert context["level_type"] == "vwap"
        assert context["level_credit"] == 35.0
        assert context["volume_credit"] <= 25.0
        assert context["gap_credit"] <= 20.0
        assert context["level_test_credit"] <= 20.0

    def test_pattern_strength_clamped(self) -> None:
        """Pattern strength never exceeds 100 or goes below 0."""
        strategy = _make_strategy()
        candle = _make_entry_candle(close=100.2, volume=100000)
        state = _make_testing_level_state(
            level_type=KeyLevelType.VWAP,
            gap_pct=-0.03,
            level_test_bars=20,
        )

        strength, _ = strategy._calculate_pattern_strength(
            candle, state, KeyLevelType.VWAP, volume_ratio=10.0,
        )

        assert strength <= 100.0
        assert strength >= 0.0


class TestRedToGreenAbstractMethods:
    """Tests for scanner criteria, exit rules, market filter (Sprint 26 S3)."""

    def test_scanner_criteria_negative_gap(self) -> None:
        """min_gap_pct should be negative (gap-down scanning)."""
        strategy = _make_strategy()
        criteria = strategy.get_scanner_criteria()

        assert criteria.min_gap_pct is not None
        assert criteria.min_gap_pct < 0

    def test_market_conditions_filter(self) -> None:
        """allowed_regimes contains expected values."""
        strategy = _make_strategy()
        mcf = strategy.get_market_conditions_filter()

        assert "bullish_trending" in mcf.allowed_regimes
        assert "range_bound" in mcf.allowed_regimes
        assert mcf.max_vix == 35.0

    def test_exit_rules_stop_below_level(self) -> None:
        """Exit rules use level_low stop with correct R-multiples."""
        strategy = _make_strategy()
        rules = strategy.get_exit_rules()

        assert rules.stop_type == "fixed"
        assert rules.stop_price_func == "level_low"
        assert len(rules.targets) == 2
        assert rules.targets[0].r_multiple == 1.0
        assert rules.targets[1].r_multiple == 2.0
        assert rules.time_stop_minutes == 20

    def test_signal_event_share_count_zero(self) -> None:
        """calculate_position_size always returns 0 (Quality Engine handles)."""
        strategy = _make_strategy()
        assert strategy.calculate_position_size(100.0, 99.0) == 0
        assert strategy.calculate_position_size(50.0, 48.0) == 0


class TestRedToGreenReconstructState:
    """Tests for reconstruct_state (Sprint 26 S3)."""

    @pytest.mark.asyncio
    async def test_reconstruct_state_open_position(self) -> None:
        """Completed trades mark symbols as EXHAUSTED."""
        strategy = _make_strategy()
        strategy.set_watchlist(["TSLA"])

        # Mock trade_logger
        trade = MagicMock()
        trade.strategy_id = "strat_red_to_green"
        trade.symbol = "TSLA"
        trade.net_pnl = 50.0

        trade_logger = AsyncMock()
        trade_logger.get_trades_by_date.return_value = [trade]

        await strategy.reconstruct_state(trade_logger)

        state = strategy._get_symbol_state("TSLA")
        assert state.state == RedToGreenState.EXHAUSTED
        assert "reconstructed" in state.exhaustion_reason
