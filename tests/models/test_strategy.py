"""Tests for strategy models."""

from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
    StrategyWatchlistItem,
)


class TestScannerCriteria:
    """Tests for ScannerCriteria dataclass."""

    def test_default_values(self) -> None:
        """ScannerCriteria has sensible defaults."""
        criteria = ScannerCriteria()
        assert criteria.min_price == 10.0
        assert criteria.max_price == 200.0
        assert criteria.min_volume_avg_daily == 1_000_000
        assert criteria.min_relative_volume == 2.0
        assert criteria.min_gap_pct is None
        assert criteria.max_results == 20

    def test_custom_values(self) -> None:
        """ScannerCriteria accepts custom values."""
        criteria = ScannerCriteria(
            min_price=5.0,
            max_price=100.0,
            min_volume_avg_daily=500_000,
            min_relative_volume=3.0,
            min_gap_pct=0.03,
            excluded_symbols=["GME", "AMC"],
        )
        assert criteria.min_price == 5.0
        assert criteria.min_gap_pct == 0.03
        assert "GME" in criteria.excluded_symbols

    def test_excluded_symbols_default_empty(self) -> None:
        """Excluded symbols defaults to empty list."""
        criteria = ScannerCriteria()
        assert criteria.excluded_symbols == []


class TestProfitTarget:
    """Tests for ProfitTarget dataclass."""

    def test_creates_target(self) -> None:
        """ProfitTarget stores R-multiple and position percentage."""
        target = ProfitTarget(r_multiple=1.0, position_pct=0.5)
        assert target.r_multiple == 1.0
        assert target.position_pct == 0.5

    def test_multiple_targets(self) -> None:
        """Multiple profit targets can be created."""
        targets = [
            ProfitTarget(r_multiple=1.0, position_pct=0.5),
            ProfitTarget(r_multiple=2.0, position_pct=0.5),
        ]
        assert targets[0].r_multiple == 1.0
        assert targets[1].r_multiple == 2.0


class TestExitRules:
    """Tests for ExitRules dataclass."""

    def test_basic_exit_rules(self) -> None:
        """ExitRules stores stop type and price function."""
        rules = ExitRules(stop_type="fixed", stop_price_func="midpoint")
        assert rules.stop_type == "fixed"
        assert rules.stop_price_func == "midpoint"
        assert rules.targets == []
        assert rules.time_stop_minutes is None

    def test_exit_rules_with_targets(self) -> None:
        """ExitRules can include profit targets."""
        rules = ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[
                ProfitTarget(r_multiple=1.0, position_pct=0.5),
                ProfitTarget(r_multiple=2.0, position_pct=0.5),
            ],
            time_stop_minutes=30,
        )
        assert len(rules.targets) == 2
        assert rules.time_stop_minutes == 30

    def test_trailing_stop_config(self) -> None:
        """ExitRules can configure trailing stops."""
        rules = ExitRules(
            stop_type="trailing",
            stop_price_func="atr",
            trailing_stop_atr_multiplier=2.0,
        )
        assert rules.stop_type == "trailing"
        assert rules.trailing_stop_atr_multiplier == 2.0


class TestMarketConditionsFilter:
    """Tests for MarketConditionsFilter dataclass."""

    def test_default_values(self) -> None:
        """MarketConditionsFilter has empty defaults."""
        conditions = MarketConditionsFilter()
        assert conditions.allowed_regimes == []
        assert conditions.max_vix is None
        assert conditions.min_vix is None

    def test_custom_conditions(self) -> None:
        """MarketConditionsFilter accepts custom values."""
        conditions = MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "range_bound"],
            max_vix=35.0,
            require_spy_above_sma=20,
        )
        assert "bullish_trending" in conditions.allowed_regimes
        assert conditions.max_vix == 35.0
        assert conditions.require_spy_above_sma == 20


class TestStrategyWatchlistItem:
    """Tests for StrategyWatchlistItem dataclass."""

    def test_minimal_item(self) -> None:
        """StrategyWatchlistItem requires only symbol."""
        item = StrategyWatchlistItem(symbol="AAPL")
        assert item.symbol == "AAPL"
        assert item.gap_pct is None
        assert item.relative_volume is None

    def test_full_item(self) -> None:
        """StrategyWatchlistItem can store all metadata."""
        item = StrategyWatchlistItem(
            symbol="AAPL",
            gap_pct=0.05,
            relative_volume=3.5,
            atr=2.50,
            premarket_volume=1_000_000,
            catalyst="Earnings",
        )
        assert item.gap_pct == 0.05
        assert item.relative_volume == 3.5
        assert item.atr == 2.50
        assert item.catalyst == "Earnings"
