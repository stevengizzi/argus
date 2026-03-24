"""Tests for Sprint 27.65 S4.5 — carry-forward fixes.

Tests cover:
- R2G zero-R guard suppresses signals with entry ≈ target
- R2G concurrent position check disabled when max=0
- AccountUpdateEvent published via Event Bus (not dead code)
- R2G normal signals unaffected by new guards
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.config import RedToGreenConfig
from argus.core.events import AccountUpdateEvent, CandleEvent, Side, SignalEvent
from argus.strategies.red_to_green import (
    KeyLevelType,
    RedToGreenState,
    RedToGreenStrategy,
    RedToGreenSymbolState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_r2g_config(**overrides: object) -> RedToGreenConfig:
    """Build a RedToGreenConfig with sensible defaults."""
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


def _make_testing_level_state(
    prior_close: float = 100.0,
    level_type: KeyLevelType = KeyLevelType.PRIOR_CLOSE,
    level_price: float = 100.0,
    level_test_bars: int = 3,
    level_attempts: int = 1,
    gap_pct: float = -0.03,
    volumes: list[int] | None = None,
) -> RedToGreenSymbolState:
    """Build a symbol state in TESTING_LEVEL for entry checks."""
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
    """Build a candle that passes entry checks (within window, above level)."""
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


# ---------------------------------------------------------------------------
# R1: R2G Zero-R Guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2g_zero_r_guard() -> None:
    """R2G with entry ≈ target (zero R) does not emit signal."""
    # Use a tiny stop_buffer_pct so risk_per_share is tiny → t1 ≈ entry
    config = _make_r2g_config(
        stop_buffer_pct=0.00001,
        target_1_r=1.0,
    )
    strategy = RedToGreenStrategy(config=config)
    strategy.set_watchlist(["TSLA"])

    # Set up TESTING_LEVEL state with level_price very close to close
    # so entry ≈ stop → risk_per_share → ~0 → t1 ≈ entry
    state = _make_testing_level_state(
        level_price=100.199,  # Very close to close=100.2
        level_test_bars=3,
    )
    strategy._symbol_states["TSLA"] = state

    candle = _make_entry_candle(close=100.2, volume=60000)
    signal = await strategy.on_candle(candle)

    # Should be suppressed by zero-R guard
    assert signal is None
    # State should NOT transition to ENTERED
    assert state.state == RedToGreenState.TESTING_LEVEL


# ---------------------------------------------------------------------------
# R1: R2G Concurrent Limit Disabled When Zero
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2g_concurrent_limit_disabled_when_zero() -> None:
    """max_concurrent_positions=0 means check is skipped entirely."""
    config = _make_r2g_config(
        risk_limits={"max_concurrent_positions": 0},
    )
    assert config.risk_limits.max_concurrent_positions == 0

    strategy = RedToGreenStrategy(config=config)
    strategy.set_watchlist(["TSLA", "AAPL", "NVDA"])

    # Mark two symbols as ENTERED (active positions)
    strategy._symbol_states["AAPL"] = RedToGreenSymbolState(
        state=RedToGreenState.ENTERED
    )
    strategy._symbol_states["NVDA"] = RedToGreenSymbolState(
        state=RedToGreenState.ENTERED
    )

    # Set up TSLA in TESTING_LEVEL ready for entry
    state = _make_testing_level_state(level_price=100.0)
    strategy._symbol_states["TSLA"] = state

    candle = _make_entry_candle(close=100.2, volume=60000)
    signal = await strategy.on_candle(candle)

    # With max=0 (disabled), signal should still fire despite 2 active
    assert signal is not None
    assert isinstance(signal, SignalEvent)
    assert signal.symbol == "TSLA"
    assert state.state == RedToGreenState.ENTERED


# ---------------------------------------------------------------------------
# R2: AccountUpdateEvent Not Dead Code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_update_event_published_via_bus() -> None:
    """AccountUpdateEvent is published through Event Bus, not manually broadcast."""
    from argus.api.websocket.live import EVENT_TYPE_MAP, WebSocketBridge
    from argus.core.event_bus import EventBus

    # Verify AccountUpdateEvent is in EVENT_TYPE_MAP
    assert AccountUpdateEvent in EVENT_TYPE_MAP
    assert EVENT_TYPE_MAP[AccountUpdateEvent] == "account.update"

    # Verify the bridge subscribes to AccountUpdateEvent
    bridge = WebSocketBridge()
    event_bus = EventBus()
    order_manager = MagicMock()
    order_manager.get_all_positions_flat.return_value = []
    config = MagicMock()
    config.ws_heartbeat_interval_seconds = 300  # long interval to avoid heartbeat
    config.ws_tick_throttle_ms = 1000

    mock_broker = AsyncMock()

    bridge.start(event_bus, order_manager, config, broker=mock_broker)

    try:
        # Verify AccountUpdateEvent is subscribed via standard handler
        # The bridge should handle AccountUpdateEvent through _handle_standard_event
        subscribers = event_bus._subscribers.get(AccountUpdateEvent, [])
        assert len(subscribers) > 0, (
            "AccountUpdateEvent should be subscribed in the Event Bus"
        )
    finally:
        bridge.stop()


# ---------------------------------------------------------------------------
# R1: Normal R2G Signal Unaffected by Guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2g_normal_signal_unaffected_by_guards() -> None:
    """Valid R2G signals still emit normally with zero-R and concurrent guards."""
    config = _make_r2g_config()
    strategy = RedToGreenStrategy(config=config)
    strategy.set_watchlist(["TSLA"])

    # Normal setup with clear R (level=100, close=100.2, stop~99.9)
    state = _make_testing_level_state(
        level_price=100.0,
        level_test_bars=3,
    )
    strategy._symbol_states["TSLA"] = state

    candle = _make_entry_candle(close=100.2, volume=60000)
    signal = await strategy.on_candle(candle)

    assert signal is not None
    assert isinstance(signal, SignalEvent)
    assert signal.symbol == "TSLA"
    assert signal.side == Side.LONG
    assert signal.entry_price == 100.2
    assert signal.stop_price < signal.entry_price
    assert signal.target_prices[0] > signal.entry_price
    assert signal.share_count == 0  # Quality Engine handles sizing
    assert signal.pattern_strength > 0.0
    assert state.state == RedToGreenState.ENTERED
