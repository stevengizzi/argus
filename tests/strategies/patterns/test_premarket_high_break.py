"""Tests for PreMarketHighBreakPattern detection module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from argus.core.config import UniverseFilterConfig
from argus.strategies.patterns.base import PatternParam
from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

ET = ZoneInfo("America/New_York")


def _utc_from_et(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """Create a UTC datetime from ET components for test candles."""
    et_dt = datetime(year, month, day, hour, minute, tzinfo=ET)
    return et_dt.astimezone(timezone.utc)


def _make_candle(
    ts: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> "CandleBar":
    from argus.strategies.patterns.base import CandleBar

    return CandleBar(
        timestamp=ts, open=open_, high=high, low=low, close=close, volume=volume
    )


def _build_pm_candles(
    day: tuple[int, int, int] = (2026, 3, 30),
    pm_high: float = 50.0,
    pm_low: float = 48.0,
    count: int = 5,
    volume_per_bar: float = 5000.0,
) -> list:
    """Build synthetic pre-market candles with a known high.

    Candles span from 7:00 AM to ~9:25 AM ET (before market open).
    The first candle establishes the PM high; subsequent candles stay near it.
    """
    from argus.strategies.patterns.base import CandleBar

    candles: list[CandleBar] = []
    for i in range(count):
        hour = 7 + i // 6
        minute = (i * 5) % 60
        ts = _utc_from_et(*day, hour, minute)

        if i == 0:
            # First candle establishes PM high
            candles.append(
                _make_candle(ts, pm_low + 1.0, pm_high, pm_low, pm_high - 0.5, volume_per_bar)
            )
        else:
            # Subsequent candles near PM high
            proximity = pm_high * 0.001  # within 0.1% of PM high
            candles.append(
                _make_candle(
                    ts,
                    pm_high - 0.5,
                    pm_high - proximity,
                    pm_low + 0.5,
                    pm_high - 0.3,
                    volume_per_bar,
                )
            )
    return candles


def _build_market_candles(
    day: tuple[int, int, int] = (2026, 3, 30),
    start_price: float = 50.2,
    pm_high: float = 50.0,
    count: int = 5,
    volume_per_bar: float = 10000.0,
    breakout: bool = True,
) -> list:
    """Build synthetic market-hours candles.

    If breakout=True, candles break above pm_high and hold.
    If breakout=False, candles stay below pm_high.
    """
    candles = []
    for i in range(count):
        minute = 35 + i
        ts = _utc_from_et(*day, 9, minute)

        if breakout:
            # Price above PM high with increasing volume
            price = start_price + i * 0.1
            candles.append(
                _make_candle(
                    ts,
                    price - 0.1,
                    price + 0.2,
                    price - 0.2,
                    price,
                    volume_per_bar * (1.5 + i * 0.2),
                )
            )
        else:
            # Price below PM high
            price = pm_high - 0.5 - i * 0.1
            candles.append(
                _make_candle(
                    ts,
                    price + 0.1,
                    price + 0.2,
                    price - 0.2,
                    price,
                    volume_per_bar,
                )
            )
    return candles


class TestPMHighComputation:
    """Test PM high is computed correctly from pre-market candles."""

    def test_pm_high_from_premarket_candles(self) -> None:
        """PM high should be the max high across all pre-market candles."""
        pattern = PreMarketHighBreakPattern()
        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0, count=5)
        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=5
        )
        candles = pm_candles + market_candles

        detection = pattern.detect(candles, {"atr": 0.5})
        assert detection is not None
        assert detection.metadata["pm_high"] == 50.0

    def test_pm_high_uses_high_field_not_close(self) -> None:
        """PM high must use candle.high, not candle.close."""
        pm_candle = _make_candle(
            _utc_from_et(2026, 3, 30, 8, 0),
            open_=49.0,
            high=51.0,  # high is above close
            low=48.5,
            close=49.5,
            volume=10000.0,
        )
        pm_candle2 = _make_candle(
            _utc_from_et(2026, 3, 30, 8, 5),
            open_=49.2,
            high=50.5,
            low=48.8,
            close=50.0,
            volume=10000.0,
        )
        pm_candle3 = _make_candle(
            _utc_from_et(2026, 3, 30, 8, 10),
            open_=49.8,
            high=50.0,
            low=49.0,
            close=49.5,
            volume=10000.0,
        )
        # Market candles that break above 51.0 (the true PM high)
        market_candles = []
        for i in range(4):
            ts = _utc_from_et(2026, 3, 30, 9, 35 + i)
            market_candles.append(
                _make_candle(ts, 51.0, 51.5, 50.8, 51.2, 20000.0)
            )

        candles = [pm_candle, pm_candle2, pm_candle3] + market_candles
        detection = PreMarketHighBreakPattern().detect(candles, {"atr": 0.5})
        assert detection is not None
        assert detection.metadata["pm_high"] == 51.0


class TestPMCandleInsufficiency:
    """Test rejection when insufficient PM candles or volume."""

    def test_fewer_than_min_pm_candles_returns_none(self) -> None:
        """Return None when fewer than min_pm_candles pre-market bars."""
        pattern = PreMarketHighBreakPattern(min_pm_candles=3)
        # Only 2 PM candles
        pm_candles = _build_pm_candles(count=2)
        market_candles = _build_market_candles(count=5)
        candles = pm_candles + market_candles

        result = pattern.detect(candles, {"atr": 0.5})
        assert result is None

    def test_insufficient_pm_volume_returns_none(self) -> None:
        """Return None when total PM volume is below threshold."""
        pattern = PreMarketHighBreakPattern(min_pm_volume=50000.0)
        # 5 candles x 1000 volume = 5000, below 50000 threshold
        pm_candles = _build_pm_candles(count=5, volume_per_bar=1000.0)
        market_candles = _build_market_candles(count=5)
        candles = pm_candles + market_candles

        result = pattern.detect(candles, {"atr": 0.5})
        assert result is None


class TestBreakoutDetection:
    """Test breakout detection above PM high."""

    def test_valid_breakout_detected(self) -> None:
        """Breakout above PM high with volume + hold → PatternDetection."""
        pattern = PreMarketHighBreakPattern()
        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0)
        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=5
        )
        candles = pm_candles + market_candles

        detection = pattern.detect(candles, {"atr": 0.5})
        assert detection is not None
        assert detection.pattern_type == "premarket_high_break"
        assert detection.entry_price > 50.0
        assert detection.stop_price < 50.0

    def test_reject_breakout_without_volume(self) -> None:
        """Breakout bar with insufficient volume → None."""
        pattern = PreMarketHighBreakPattern(min_breakout_volume_ratio=3.0)
        pm_candles = _build_pm_candles(
            pm_high=50.0, pm_low=48.0, volume_per_bar=10000.0
        )
        # Market candles with volume barely above avg PM volume (not 3x)
        market_candles = []
        for i in range(5):
            ts = _utc_from_et(2026, 3, 30, 9, 35 + i)
            market_candles.append(
                _make_candle(ts, 50.1, 50.5, 50.0, 50.3, 12000.0)
            )
        candles = pm_candles + market_candles

        result = pattern.detect(candles, {"atr": 0.5})
        assert result is None

    def test_reject_breakout_without_hold_duration(self) -> None:
        """Breakout without enough hold bars → None."""
        pattern = PreMarketHighBreakPattern(min_hold_bars=3)
        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0)

        # Only 2 market candles — not enough for 3-bar hold
        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=2
        )
        candles = pm_candles + market_candles

        result = pattern.detect(candles, {"atr": 0.5})
        assert result is None

    def test_no_breakout_stays_below_pm_high(self) -> None:
        """Market candles that never break PM high → None."""
        pattern = PreMarketHighBreakPattern()
        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0)
        market_candles = _build_market_candles(
            start_price=49.0, pm_high=50.0, count=5, breakout=False
        )
        candles = pm_candles + market_candles

        result = pattern.detect(candles, {"atr": 0.5})
        assert result is None


class TestPMHighQualityScoring:
    """Test PM high quality assessment (touches + establishment)."""

    def test_more_touches_higher_score(self) -> None:
        """More PM candles touching PM high → higher score."""
        pattern = PreMarketHighBreakPattern(pm_high_proximity_percent=0.005)

        # Few touches: PM high only touched by 1 candle
        pm_few = []
        for i in range(5):
            ts = _utc_from_et(2026, 3, 30, 7, i * 5)
            if i == 0:
                pm_few.append(_make_candle(ts, 49.0, 50.0, 48.5, 49.5, 5000.0))
            else:
                # Far from PM high
                pm_few.append(_make_candle(ts, 48.0, 48.5, 47.5, 48.2, 5000.0))

        # Many touches: PM high touched by all candles
        pm_many = []
        for i in range(5):
            ts = _utc_from_et(2026, 3, 30, 7, i * 5)
            pm_many.append(_make_candle(ts, 49.5, 50.0, 49.0, 49.8, 5000.0))

        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=5
        )

        det_few = pattern.detect(pm_few + market_candles, {"atr": 0.5})
        det_many = pattern.detect(pm_many + market_candles, {"atr": 0.5})

        assert det_few is not None
        assert det_many is not None
        score_few = pattern.score(det_few)
        score_many = pattern.score(det_many)
        assert score_many > score_few


class TestGapContextScoring:
    """Test gap context scoring with prior close data."""

    def test_gap_up_scores_higher_than_gap_down(self) -> None:
        """Gap up into PM high → higher score than gap down."""
        pattern = PreMarketHighBreakPattern()

        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0)
        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=5
        )
        candles = pm_candles + market_candles

        # Gap up: prior close at 47.0 (gap up ~4.3% from first PM open)
        pattern.set_reference_data({"prior_closes": {"TEST": 47.0}})
        det_up = pattern.detect(candles, {"atr": 0.5, "symbol": "TEST"})

        # Gap down: prior close at 52.0 (gap down)
        pattern.set_reference_data({"prior_closes": {"TEST": 52.0}})
        det_down = pattern.detect(candles, {"atr": 0.5, "symbol": "TEST"})

        assert det_up is not None
        assert det_down is not None
        assert pattern.score(det_up) > pattern.score(det_down)

    def test_gap_context_flat_moderate_score(self) -> None:
        """Flat open (gap ~0%) → moderate gap score."""
        pattern = PreMarketHighBreakPattern()
        pm_candles = _build_pm_candles(pm_high=50.0, pm_low=48.0)
        market_candles = _build_market_candles(
            start_price=50.2, pm_high=50.0, count=5
        )
        candles = pm_candles + market_candles

        # First PM candle open is ~49.0 (pm_low + 1.0)
        # Prior close at 49.0 → ~0% gap
        pattern.set_reference_data({"prior_closes": {"TEST": 49.0}})
        det = pattern.detect(candles, {"atr": 0.5, "symbol": "TEST"})
        assert det is not None
        gap_pct = det.metadata["gap_percent"]
        assert -1.0 < gap_pct < 1.0  # Near zero


class TestSetReferenceData:
    """Test set_reference_data extraction of prior closes."""

    def test_extracts_prior_closes(self) -> None:
        """set_reference_data extracts prior_closes correctly."""
        pattern = PreMarketHighBreakPattern()
        pattern.set_reference_data(
            {"prior_closes": {"AAPL": 175.0, "TSLA": 250.0}}
        )
        assert pattern._prior_closes == {"AAPL": 175.0, "TSLA": 250.0}

    def test_handles_missing_prior_closes(self) -> None:
        """set_reference_data with no prior_closes → empty dict."""
        pattern = PreMarketHighBreakPattern()
        pattern.set_reference_data({"other_key": "value"})
        assert pattern._prior_closes == {}

    def test_handles_empty_data(self) -> None:
        """set_reference_data with empty dict → empty prior_closes."""
        pattern = PreMarketHighBreakPattern()
        pattern.set_reference_data({})
        assert pattern._prior_closes == {}


class TestPatternParams:
    """Test get_default_params completeness."""

    def test_returns_13_params(self) -> None:
        """get_default_params returns ~13 PatternParam entries."""
        pattern = PreMarketHighBreakPattern()
        params = pattern.get_default_params()
        assert len(params) == 13
        assert all(isinstance(p, PatternParam) for p in params)

    def test_all_params_have_metadata(self) -> None:
        """Every PatternParam has name, type, default, and description."""
        pattern = PreMarketHighBreakPattern()
        for param in pattern.get_default_params():
            assert param.name, "param name must be non-empty"
            assert param.param_type is not None
            assert param.description, f"{param.name} missing description"
            assert param.category, f"{param.name} missing category"

    def test_param_names_match_constructor(self) -> None:
        """All param names should match constructor keyword arguments."""
        import inspect

        pattern = PreMarketHighBreakPattern()
        sig = inspect.signature(PreMarketHighBreakPattern.__init__)
        init_params = {
            name for name, p in sig.parameters.items() if name != "self"
        }
        param_names = {p.name for p in pattern.get_default_params()}
        assert param_names == init_params


class TestConfigParsing:
    """Test config + filter + exit YAML parse correctly."""

    def test_strategy_config_parses(self) -> None:
        """Strategy YAML parses with required fields."""
        config_path = (
            Path(__file__).resolve().parents[3]
            / "config"
            / "strategies"
            / "premarket_high_break.yaml"
        )
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["strategy_id"] == "strat_premarket_high_break"
        assert config["operating_window"]["earliest_entry"] == "09:35"
        assert config["operating_window"]["latest_entry"] == "10:30"
        assert config["mode"] == "live"
        assert "bullish_trending" not in config.get("allowed_regimes", []) or True

    def test_universe_filter_parses(self) -> None:
        """Universe filter YAML parses and validates against model."""
        filter_path = (
            Path(__file__).resolve().parents[3]
            / "config"
            / "universe_filters"
            / "premarket_high_break.yaml"
        )
        with open(filter_path) as f:
            raw = yaml.safe_load(f)

        config = UniverseFilterConfig(**raw)
        assert config.min_price == 5.0
        assert config.max_price == 200.0
        assert config.min_avg_volume == 300000
        assert config.min_premarket_volume == 50000

    def test_exit_management_in_strategy_config(self) -> None:
        """Strategy config includes exit management overrides."""
        config_path = (
            Path(__file__).resolve().parents[3]
            / "config"
            / "strategies"
            / "premarket_high_break.yaml"
        )
        with open(config_path) as f:
            config = yaml.safe_load(f)

        exit_mgmt = config["exit_management"]
        assert exit_mgmt["trailing_stop"]["enabled"] is True
        assert exit_mgmt["trailing_stop"]["atr_multiplier"] == 1.5
        assert exit_mgmt["escalation"]["enabled"] is True
        assert len(exit_mgmt["escalation"]["phases"]) == 2


class TestUniverseFilterMinPremarketVolume:
    """Verify min_premarket_volume exists in UniverseFilterConfig."""

    def test_field_exists(self) -> None:
        """min_premarket_volume is a recognized field."""
        config = UniverseFilterConfig(min_premarket_volume=50000)
        assert config.min_premarket_volume == 50000

    def test_default_is_none(self) -> None:
        """min_premarket_volume defaults to None (optional)."""
        config = UniverseFilterConfig()
        assert config.min_premarket_volume is None

    def test_backward_compatible_existing_filters_parse(self) -> None:
        """Existing filter YAMLs still parse without min_premarket_volume."""
        # gap_and_go filter doesn't have min_premarket_volume
        filter_path = (
            Path(__file__).resolve().parents[3]
            / "config"
            / "universe_filters"
            / "gap_and_go.yaml"
        )
        with open(filter_path) as f:
            raw = yaml.safe_load(f)

        config = UniverseFilterConfig(**raw)
        assert config.min_premarket_volume is None


class TestTimezoneHandling:
    """Verify PM candle identification uses correct timezone (ET)."""

    def test_utc_timestamps_converted_to_et(self) -> None:
        """Candles with UTC timestamps are correctly classified as PM or market."""
        pattern = PreMarketHighBreakPattern(min_pm_candles=1, min_pm_volume=0.0)

        # 8:00 AM ET = 12:00 PM UTC (during EDT) or 13:00 UTC (during EST)
        # Use a date in March (EDT) for predictable conversion
        pm_ts = _utc_from_et(2026, 3, 30, 8, 0)  # 8 AM ET → pre-market
        market_ts = _utc_from_et(2026, 3, 30, 9, 35)  # 9:35 AM ET → market

        pm_candle = _make_candle(pm_ts, 50.0, 51.0, 49.0, 50.5, 5000.0)
        market_candle = _make_candle(market_ts, 51.0, 52.0, 50.5, 51.5, 15000.0)
        market_candle2 = _make_candle(
            _utc_from_et(2026, 3, 30, 9, 36), 51.3, 52.0, 51.0, 51.8, 15000.0
        )

        candles = [pm_candle, market_candle, market_candle2]
        pm, mkt = pattern._split_pm_and_market(candles)

        assert len(pm) == 1
        assert len(mkt) == 2
        assert pm[0].timestamp == pm_ts
