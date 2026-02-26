"""Tests for dev mode extensions for Pattern Library (Sprint 21a Session 2).

Tests the mock data created in dev mode for the Pattern Library page:
- MockStrategy instances have family, description_short, time_window_display
- Performance summaries are computed from seeded trade data
- Backtest summaries are present on mock strategy configs
- All 4 mock strategies have distinct family values
"""

from __future__ import annotations

import pytest

from argus.api.dev_state import create_dev_state


@pytest.mark.asyncio
async def test_dev_state_mock_strategies_have_family() -> None:
    """Dev state mock strategies have family field populated via config."""
    state = await create_dev_state()

    families = []
    for strategy_id, strategy in state.strategies.items():
        # Check strategy config has family attribute
        assert hasattr(strategy.config, "family"), (
            f"Strategy {strategy_id} config missing family attribute"
        )
        assert strategy.config.family != "", f"Strategy {strategy_id} config has empty family"
        families.append(strategy.config.family)

    # Should have 4 strategies
    assert len(families) == 4


@pytest.mark.asyncio
async def test_dev_state_mock_strategies_have_description_short() -> None:
    """Dev state mock strategies have description_short field populated via config."""
    state = await create_dev_state()

    for strategy_id, strategy in state.strategies.items():
        # Check strategy config has description_short attribute
        assert hasattr(
            strategy.config, "description_short"
        ), f"Strategy {strategy_id} config missing description_short"
        assert (
            strategy.config.description_short != ""
        ), f"Strategy {strategy_id} config has empty description_short"
        # Description should be a meaningful sentence
        assert len(strategy.config.description_short) > 20, (
            f"Strategy {strategy_id} description too short: {strategy.config.description_short}"
        )


@pytest.mark.asyncio
async def test_dev_state_mock_strategies_have_time_window_display() -> None:
    """Dev state mock strategies have time_window_display field populated via config."""
    state = await create_dev_state()

    for strategy_id, strategy in state.strategies.items():
        # Check strategy config has time_window_display attribute
        assert hasattr(
            strategy.config, "time_window_display"
        ), f"Strategy {strategy_id} config missing time_window_display"
        assert (
            strategy.config.time_window_display != ""
        ), f"Strategy {strategy_id} config has empty time_window_display"
        # Time window should contain AM or PM
        assert (
            "AM" in strategy.config.time_window_display
            or "PM" in strategy.config.time_window_display
        ), (
            f"Strategy {strategy_id} time_window_display missing AM/PM: "
            f"{strategy.config.time_window_display}"
        )


@pytest.mark.asyncio
async def test_dev_state_backtest_summaries_present() -> None:
    """Dev state mock strategy configs have backtest_summary populated."""
    state = await create_dev_state()

    for strategy_id, strategy in state.strategies.items():
        config = strategy.config

        # Check config has backtest_summary
        assert hasattr(
            config, "backtest_summary"
        ), f"Strategy {strategy_id} config missing backtest_summary"

        bs = config.backtest_summary
        assert bs is not None, f"Strategy {strategy_id} has None backtest_summary"

        # Check backtest_summary fields are populated
        assert bs.status != "not_validated", (
            f"Strategy {strategy_id} backtest status still 'not_validated'"
        )
        assert bs.total_trades is not None, (
            f"Strategy {strategy_id} backtest_summary missing total_trades"
        )
        assert bs.total_trades > 0, (
            f"Strategy {strategy_id} backtest_summary total_trades should be positive"
        )
        assert bs.data_months is not None and bs.data_months > 0, (
            f"Strategy {strategy_id} backtest_summary missing data_months"
        )
        assert bs.last_run is not None, (
            f"Strategy {strategy_id} backtest_summary missing last_run"
        )


@pytest.mark.asyncio
async def test_dev_state_strategies_have_distinct_families() -> None:
    """All 4 mock strategies should have at least 3 distinct family values."""
    state = await create_dev_state()

    families = set()
    for strategy in state.strategies.values():
        families.add(strategy.config.family)

    # With 4 strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum):
    # - ORB Breakout and ORB Scalp share "orb_family"
    # - VWAP Reclaim has "mean_reversion"
    # - Afternoon Momentum has "momentum"
    # So we expect 3 distinct families
    assert len(families) >= 3, f"Expected at least 3 distinct families, got {families}"

    # Verify specific families exist
    expected_families = {"orb_family", "mean_reversion", "momentum"}
    assert expected_families.issubset(
        families
    ), f"Missing expected families. Expected {expected_families}, got {families}"
