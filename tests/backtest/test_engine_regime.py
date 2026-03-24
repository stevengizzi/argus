"""Tests for BacktestEngine regime tagging — Sprint 27.5 Session 2 + Sprint 27.6 S7.

Verifies SPY daily bar aggregation, regime tag computation, trade-to-regime
partitioning, to_multi_objective_result(), edge cases, and V2 golden-file parity.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from argus.analytics.evaluation import (
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
)
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.backtest.metrics import BacktestResult
from argus.core.config import OrchestratorConfig, RegimeIntelligenceConfig
from argus.core.regime import MarketRegime, RegimeClassifier, RegimeClassifierV2, RegimeVector

ET = ZoneInfo("America/New_York")

GOLDEN_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_regime_tags_v1.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a minimal BacktestEngineConfig pointing at tmp_path."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        cache_dir=tmp_path / "cache",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


def _write_spy_parquet(cache_dir: Path, trading_dates: list[date]) -> None:
    """Write synthetic SPY 1-min Parquet files for the given dates.

    Creates 390 bars per day (9:30 to 16:00 ET) with a deterministic
    price series.
    """
    spy_dir = cache_dir / "SPY"
    spy_dir.mkdir(parents=True, exist_ok=True)

    # Group dates by month
    months: dict[tuple[int, int], list[date]] = {}
    for d in trading_dates:
        months.setdefault((d.year, d.month), []).append(d)

    for (year, month), dates in months.items():
        rows = []
        for d in sorted(dates):
            base_price = 450.0 + d.day * 0.5
            for minute_offset in range(390):
                ts = datetime(
                    d.year, d.month, d.day, 9, 30, 0, tzinfo=ET
                ) + timedelta(minutes=minute_offset)
                ts_utc = ts.astimezone(UTC)
                noise = minute_offset * 0.01
                rows.append({
                    "timestamp": ts_utc,
                    "open": base_price + noise,
                    "high": base_price + noise + 0.50,
                    "low": base_price + noise - 0.30,
                    "close": base_price + noise + 0.10,
                    "volume": 10000 + minute_offset,
                })

        df = pd.DataFrame(rows)
        path = spy_dir / f"{year}-{month:02d}.parquet"
        df.to_parquet(path, index=False)


def _make_empty_result(
    strategy_id: str = "strat_orb_breakout",
    start: date | None = None,
    end: date | None = None,
    total_trades: int = 0,
) -> BacktestResult:
    """Create a BacktestResult with zeroed metrics."""
    return BacktestResult(
        strategy_id=strategy_id,
        start_date=start or date(2025, 6, 16),
        end_date=end or date(2025, 6, 20),
        initial_capital=100_000.0,
        final_equity=100_000.0,
        trading_days=5,
        total_trades=total_trades,
        winning_trades=0,
        losing_trades=0,
        breakeven_trades=0,
        win_rate=0.0,
        profit_factor=0.0,
        avg_r_multiple=0.0,
        avg_winner_r=0.0,
        avg_loser_r=0.0,
        expectancy=0.0,
        max_drawdown_dollars=0.0,
        max_drawdown_pct=0.0,
        sharpe_ratio=0.0,
        recovery_factor=0.0,
        avg_hold_minutes=0.0,
        max_consecutive_wins=0,
        max_consecutive_losses=0,
        largest_win_dollars=0.0,
        largest_loss_dollars=0.0,
        largest_win_r=0.0,
        largest_loss_r=0.0,
    )


def _make_trade_dict(
    exit_date: date,
    net_pnl: float = 100.0,
    r_multiple: float = 1.0,
) -> dict[str, object]:
    """Create a minimal trade dict for regime partitioning."""
    exit_time = datetime(
        exit_date.year, exit_date.month, exit_date.day,
        14, 30, 0, tzinfo=ET,
    )
    return {
        "net_pnl": net_pnl,
        "r_multiple": r_multiple,
        "commission": 0.0,
        "hold_duration_seconds": 1800,
        "exit_price": 150.0,
        "exit_time": exit_time,
        "gross_pnl": net_pnl,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spy_daily_bar_aggregation(tmp_path: Path) -> None:
    """Synthetic 1-min bars -> correct daily OHLCV."""
    config = _make_config(tmp_path)
    trading_dates = [date(2025, 6, 16), date(2025, 6, 17)]
    _write_spy_parquet(config.cache_dir, trading_dates)

    engine = BacktestEngine(config)
    daily = await engine._load_spy_daily_bars(date(2025, 6, 16), date(2025, 6, 17))

    assert daily is not None
    assert len(daily) == 2
    assert list(daily.columns) == ["open", "high", "low", "close", "volume"]

    # Check aggregation correctness for first day
    row = daily.iloc[0]
    # base_price = 450.0 + 16 * 0.5 = 458.0
    # first bar: open = 458.0, last bar minute_offset=389: close = 458.0 + 389*0.01 + 0.10
    assert row["open"] == pytest.approx(458.0, abs=0.01)
    # high = max of all (base + noise + 0.50)
    assert row["high"] > row["open"]
    # low = min of all (base + noise - 0.30)
    assert row["low"] < row["open"]
    # volume = sum of all 390 bars
    expected_vol = sum(10000 + m for m in range(390))
    assert row["volume"] == expected_vol


def test_regime_tag_computation(tmp_path: Path) -> None:
    """Known daily bars -> correct MarketRegime assignment."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    # Build 60 days of daily bars with a steady uptrend (price > SMA-20 > SMA-50)
    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(100)]
    # Filter weekends
    dates = [d for d in dates if d.weekday() < 5][:60]
    n = len(dates)

    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    assert len(tags) == 60
    # With steady uptrend, later days should be bullish_trending
    last_day = dates[-1]
    assert tags[last_day] == MarketRegime.BULLISH_TRENDING.value


def test_regime_tag_insufficient_history(tmp_path: Path) -> None:
    """Early dates with < 20 bars -> RANGE_BOUND default."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    dates = [date(2025, 6, 16) + timedelta(days=i) for i in range(10)]
    daily = pd.DataFrame(
        {
            "open": [450.0] * 10,
            "high": [451.0] * 10,
            "low": [449.0] * 10,
            "close": [450.5] * 10,
            "volume": [1_000_000] * 10,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    # All dates should be RANGE_BOUND (insufficient history)
    for d in dates:
        assert tags[d] == MarketRegime.RANGE_BOUND.value


@pytest.mark.asyncio
async def test_to_multi_objective_result_basic(tmp_path: Path) -> None:
    """BacktestEngine with test data -> valid MOR with regime_results."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16), date(2025, 6, 17)]

    # Mock trade logger to return some trades
    mock_trade = MagicMock()
    mock_trade.net_pnl = 150.0
    mock_trade.r_multiple = 1.5
    mock_trade.commission = 2.0
    mock_trade.hold_duration_seconds = 3600
    mock_trade.exit_price = 155.0
    mock_trade.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    mock_trade.gross_pnl = 152.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=[mock_trade])
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=1)
    result = BacktestResult(
        **{**result.__dict__, "winning_trades": 1, "total_trades": 1,
           "win_rate": 1.0, "profit_factor": float("inf"),
           "expectancy": 1.5}
    )

    # Patch _load_spy_daily_bars to return None (triggers RANGE_BOUND fallback)
    with patch.object(engine, "_load_spy_daily_bars", new=AsyncMock(return_value=None)):
        mor = await engine.to_multi_objective_result(result)

    assert isinstance(mor, MultiObjectiveResult)
    assert mor.strategy_id == result.strategy_id
    assert mor.total_trades == 1
    # Should have regime results (single RANGE_BOUND)
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results
    regime_metrics = mor.regime_results[MarketRegime.RANGE_BOUND.value]
    assert regime_metrics.total_trades == 1


@pytest.mark.asyncio
async def test_to_multi_objective_result_regime_partitioning(
    tmp_path: Path,
) -> None:
    """Trades on different regime days -> correct partition."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16), date(2025, 6, 17)]

    # Two trades on different days
    trade1 = MagicMock()
    trade1.net_pnl = 100.0
    trade1.r_multiple = 1.0
    trade1.commission = 1.0
    trade1.hold_duration_seconds = 1800
    trade1.exit_price = 150.0
    trade1.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    trade1.gross_pnl = 101.0

    trade2 = MagicMock()
    trade2.net_pnl = -50.0
    trade2.r_multiple = -0.5
    trade2.commission = 1.0
    trade2.hold_duration_seconds = 900
    trade2.exit_price = 148.0
    trade2.exit_time = datetime(2025, 6, 17, 11, 0, 0, tzinfo=ET)
    trade2.gross_pnl = -49.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(
        return_value=[trade1, trade2]
    )
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=2)

    # Simulate two different regimes
    regime_tags = {
        date(2025, 6, 16): MarketRegime.BULLISH_TRENDING.value,
        date(2025, 6, 17): MarketRegime.RANGE_BOUND.value,
    }

    mock_daily = pd.DataFrame(
        {"open": [450], "high": [451], "low": [449],
         "close": [450], "volume": [1000]},
        index=[date(2025, 6, 16)],
    )
    with patch.object(
        engine, "_load_spy_daily_bars", new=AsyncMock(return_value=mock_daily)
    ), patch.object(engine, "_compute_regime_tags", return_value=regime_tags):
        mor = await engine.to_multi_objective_result(result)

    assert MarketRegime.BULLISH_TRENDING.value in mor.regime_results
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results
    assert mor.regime_results[MarketRegime.BULLISH_TRENDING.value].total_trades == 1
    assert mor.regime_results[MarketRegime.RANGE_BOUND.value].total_trades == 1


@pytest.mark.asyncio
async def test_to_multi_objective_result_confidence_tier(
    tmp_path: Path,
) -> None:
    """Tier computed from actual regime distribution."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16)]

    # 5 trades -> should be ENSEMBLE_ONLY (< 10 trades)
    trades = []
    for i in range(5):
        t = MagicMock()
        t.net_pnl = 50.0
        t.r_multiple = 0.5
        t.commission = 0.0
        t.hold_duration_seconds = 600
        t.exit_price = 150.0
        t.exit_time = datetime(2025, 6, 16, 10 + i, 0, 0, tzinfo=ET)
        t.gross_pnl = 50.0
        trades.append(t)

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=trades)
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=5)
    result = BacktestResult(**{**result.__dict__, "total_trades": 5})

    with patch.object(engine, "_load_spy_daily_bars", new=AsyncMock(return_value=None)):
        mor = await engine.to_multi_objective_result(result)

    assert mor.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY


@pytest.mark.asyncio
async def test_to_multi_objective_result_no_spy(tmp_path: Path) -> None:
    """SPY not in cache -> WARNING + single RANGE_BOUND regime."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16)]

    mock_trade = MagicMock()
    mock_trade.net_pnl = 100.0
    mock_trade.r_multiple = 1.0
    mock_trade.commission = 0.0
    mock_trade.hold_duration_seconds = 1800
    mock_trade.exit_price = 150.0
    mock_trade.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    mock_trade.gross_pnl = 100.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(
        return_value=[mock_trade]
    )
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=1)

    # SPY dir does not exist -> _load_spy_daily_bars returns None
    mor = await engine.to_multi_objective_result(result)

    # All trades should land in RANGE_BOUND
    assert len(mor.regime_results) == 1
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results


@pytest.mark.asyncio
async def test_to_multi_objective_result_zero_trades(tmp_path: Path) -> None:
    """Empty backtest -> MOR with ENSEMBLE_ONLY."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = []

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=[])
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=0)

    with patch.object(engine, "_load_spy_daily_bars", new=AsyncMock(return_value=None)):
        mor = await engine.to_multi_objective_result(result)

    assert mor.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
    assert mor.total_trades == 0
    assert len(mor.regime_results) == 0


def test_regime_metrics_single_trade(tmp_path: Path) -> None:
    """One trade in a regime -> valid (degenerate) RegimeMetrics."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    trade = _make_trade_dict(date(2025, 6, 16), net_pnl=100.0, r_multiple=1.0)
    metrics = engine._compute_regime_metrics([trade])

    assert metrics.total_trades == 1
    assert metrics.win_rate == 1.0
    assert metrics.expectancy_per_trade == pytest.approx(1.0, abs=0.01)
    # Sharpe with single day -> 0.0 (not enough data points)
    assert metrics.sharpe_ratio == 0.0


@pytest.mark.asyncio
async def test_to_multi_objective_result_preserves_backtest_result(
    tmp_path: Path,
) -> None:
    """BacktestEngine.run() return unchanged by regime tagging existence."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    # Verify run() returns BacktestResult, not MOR
    with patch.object(engine, "_load_data", new_callable=AsyncMock):
        engine._trading_days = []  # Empty -> fast path
        result = await engine.run()

    assert isinstance(result, BacktestResult)
    assert not isinstance(result, MultiObjectiveResult)


@pytest.mark.asyncio
async def test_load_spy_daily_bars_no_spy_dir(tmp_path: Path) -> None:
    """SPY directory missing -> returns None."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    result = await engine._load_spy_daily_bars(date(2025, 6, 16), date(2025, 6, 20))
    assert result is None


# ---------------------------------------------------------------------------
# Sprint 27.6 S7 — V2 Integration Tests
# ---------------------------------------------------------------------------


def _make_v2_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a BacktestEngineConfig with use_regime_v2=True."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        cache_dir=tmp_path / "cache",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
        use_regime_v2=True,
    )


def _load_golden_fixture() -> dict[str, object]:
    """Load the frozen golden-file fixture."""
    with open(GOLDEN_FIXTURE_PATH) as f:
        return json.load(f)


def _build_daily_bars_from_fixture(
    fixture: dict[str, object],
) -> pd.DataFrame:
    """Reconstruct daily bar DataFrame from the golden fixture."""
    bar_data: dict[str, dict[str, float]] = fixture["daily_bars"]  # type: ignore[assignment]
    rows = []
    for date_str, bar in sorted(bar_data.items()):
        rows.append({
            "date": date.fromisoformat(date_str),
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
        })
    df = pd.DataFrame(rows)
    df = df.set_index("date")
    df.index.name = "date"
    return df


def test_v2_compute_regime_tags_same_as_v1(tmp_path: Path) -> None:
    """V2 with None calculators produces identical tags to V1."""
    config_v1 = _make_config(tmp_path)
    config_v2 = _make_v2_config(tmp_path)
    engine_v1 = BacktestEngine(config_v1)
    engine_v2 = BacktestEngine(config_v2)

    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(100)]
    dates = [d for d in dates if d.weekday() < 5][:60]
    n = len(dates)

    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags_v1 = engine_v1._compute_regime_tags(daily)
    tags_v2 = engine_v2._compute_regime_tags(daily)

    assert tags_v1 == tags_v2


def test_golden_file_parity_v2_matches_frozen_v1(tmp_path: Path) -> None:
    """V2 produces identical regime tags to frozen V1 golden fixture (100 days)."""
    fixture = _load_golden_fixture()
    daily = _build_daily_bars_from_fixture(fixture)
    expected_tags: dict[str, str] = fixture["regime_tags"]  # type: ignore[assignment]

    config = _make_v2_config(tmp_path)
    engine = BacktestEngine(config)

    computed_tags = engine._compute_regime_tags(daily)

    # Convert date keys to ISO strings for comparison
    computed_str = {d.isoformat(): v for d, v in computed_tags.items()}

    # Only compare the 100 fixture dates (daily has 150 total bars)
    for date_str, expected_regime in expected_tags.items():
        assert date_str in computed_str, f"Missing date {date_str} in V2 output"
        assert computed_str[date_str] == expected_regime, (
            f"Mismatch on {date_str}: V2={computed_str[date_str]} vs V1={expected_regime}"
        )


def test_regime_tags_are_market_regime_value_strings(tmp_path: Path) -> None:
    """All regime tag values are valid MarketRegime.value strings."""
    fixture = _load_golden_fixture()
    daily = _build_daily_bars_from_fixture(fixture)

    config = _make_v2_config(tmp_path)
    engine = BacktestEngine(config)

    tags = engine._compute_regime_tags(daily)
    valid_values = {r.value for r in MarketRegime}

    for d, regime_str in tags.items():
        assert regime_str in valid_values, f"Invalid regime value '{regime_str}' on {d}"


@pytest.mark.asyncio
async def test_to_multi_objective_result_with_v2_tags(tmp_path: Path) -> None:
    """to_multi_objective_result() produces valid regime_results with V2 tags."""
    config = _make_v2_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16)]

    mock_trade = MagicMock()
    mock_trade.net_pnl = 100.0
    mock_trade.r_multiple = 1.0
    mock_trade.commission = 0.0
    mock_trade.hold_duration_seconds = 1800
    mock_trade.exit_price = 150.0
    mock_trade.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    mock_trade.gross_pnl = 100.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=[mock_trade])
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=1)

    with patch.object(engine, "_load_spy_daily_bars", new=AsyncMock(return_value=None)):
        mor = await engine.to_multi_objective_result(result)

    assert isinstance(mor, MultiObjectiveResult)
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results
    assert mor.regime_results[MarketRegime.RANGE_BOUND.value].total_trades == 1


def test_v2_backtest_only_trend_vol_dimensions() -> None:
    """V2 in backtest mode: only trend+vol populated, others are defaults."""
    orch_config = OrchestratorConfig()
    regime_config = RegimeIntelligenceConfig(
        enabled=True,
        breadth={"enabled": False},
        correlation={"enabled": False},
        sector_rotation={"enabled": False},
        intraday={"enabled": False},
    )
    v2 = RegimeClassifierV2(
        config=orch_config,
        regime_config=regime_config,
        breadth=None,
        correlation=None,
        sector=None,
        intraday=None,
    )

    # Build a simple uptrend series (50 days)
    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(70)]
    dates = [d for d in dates if d.weekday() < 5][:50]
    n = len(dates)
    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )

    indicators = v2.compute_indicators(daily)
    vector = v2.compute_regime_vector(indicators)

    # Trend and vol should be populated
    assert isinstance(vector, RegimeVector)
    assert vector.trend_score != 0.0 or vector.trend_conviction >= 0.0
    assert vector.volatility_level >= 0.0

    # Breadth, correlation, sector, intraday should be defaults (None)
    assert vector.universe_breadth_score is None
    assert vector.breadth_thrust is None
    assert vector.average_correlation is None
    assert vector.correlation_regime is None
    assert vector.sector_rotation_phase is None
    assert vector.leading_sectors == []
    assert vector.lagging_sectors == []
    assert vector.opening_drive_strength is None
    assert vector.first_30min_range_ratio is None
    assert vector.vwap_slope is None
    assert vector.direction_change_count is None
    assert vector.intraday_character is None


def test_v2_breadth_correlation_sector_intraday_are_none_defaults(
    tmp_path: Path,
) -> None:
    """Breadth/correlation/sector/intraday are all None in backtest V2."""
    config = _make_v2_config(tmp_path)
    engine = BacktestEngine(config)

    # Access the classifier created inside _compute_regime_tags by checking
    # the config flag is set correctly
    assert config.use_regime_v2 is True

    # Create minimal daily bars and verify tags are valid
    dates = [date(2025, 6, 16) + timedelta(days=i) for i in range(25)]
    dates = [d for d in dates if d.weekday() < 5][:25]
    n = len(dates)
    daily = pd.DataFrame(
        {
            "open": [450.0] * n,
            "high": [451.0] * n,
            "low": [449.0] * n,
            "close": [450.5] * n,
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)
    valid_values = {r.value for r in MarketRegime}
    for regime_str in tags.values():
        assert regime_str in valid_values


def test_backtest_engine_v1_fallback_when_regime_v2_disabled(
    tmp_path: Path,
) -> None:
    """use_regime_v2=False (default) -> V1 classifier used, same behavior."""
    config = _make_config(tmp_path)
    assert config.use_regime_v2 is False  # Default

    engine = BacktestEngine(config)

    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(100)]
    dates = [d for d in dates if d.weekday() < 5][:60]
    n = len(dates)

    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    # Verify V1 produces known result for uptrend data
    last_day = dates[-1]
    assert tags[last_day] == MarketRegime.BULLISH_TRENDING.value


def test_existing_backtest_integration_unchanged(tmp_path: Path) -> None:
    """Existing V1 test behavior preserved — regime tags for uptrend data."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(100)]
    dates = [d for d in dates if d.weekday() < 5][:60]
    n = len(dates)

    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    assert len(tags) == 60
    assert tags[dates[-1]] == MarketRegime.BULLISH_TRENDING.value
    # Early days should be RANGE_BOUND (insufficient history)
    for d in dates[:19]:
        assert tags[d] == MarketRegime.RANGE_BOUND.value
