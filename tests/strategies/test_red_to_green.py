"""Tests for the Red-to-Green strategy (Sprint 26, Session 2).

Tests cover:
- Config loading from YAML
- Config YAML key validation (no silently ignored keys)
- Config gap validator
- State machine transitions: WATCHING → GAP_DOWN_CONFIRMED
- State machine: gap up stays WATCHING
- State machine: large gap → EXHAUSTED
- State machine: GAP_DOWN_CONFIRMED → TESTING_LEVEL
- State machine: max level attempts → EXHAUSTED
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from argus.core.config import RedToGreenConfig, load_red_to_green_config, load_yaml_file
from argus.core.events import CandleEvent
from argus.strategies.red_to_green import (
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
        assert config.backtest_summary.status == "not_validated"
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
