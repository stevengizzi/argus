"""Tests for market regime classification."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from argus.core.config import (
    BreadthConfig,
    CorrelationConfig,
    IntradayConfig,
    OrchestratorConfig,
    RegimeIntelligenceConfig,
    SectorRotationConfig,
    SystemConfig,
)
from argus.core.regime import (
    MarketRegime,
    RegimeClassifier,
    RegimeClassifierV2,
    RegimeIndicators,
    RegimeVector,
    VolatilityBucket,
)


def make_config(
    vol_low: float = 0.08,
    vol_normal: float = 0.16,
    vol_high: float = 0.25,
    vol_crisis: float = 0.35,
) -> OrchestratorConfig:
    """Create an OrchestratorConfig with specified volatility thresholds."""
    return OrchestratorConfig(
        vol_low_threshold=vol_low,
        vol_normal_threshold=vol_normal,
        vol_high_threshold=vol_high,
        vol_crisis_threshold=vol_crisis,
    )


def make_daily_bars(
    num_bars: int,
    start_price: float = 400.0,
    trend: float = 0.0,
    volatility: float = 0.01,
) -> pd.DataFrame:
    """Create synthetic daily bars for testing.

    Args:
        num_bars: Number of daily bars to generate.
        start_price: Starting close price.
        trend: Daily percentage trend (0.01 = +1% per day).
        volatility: Daily percentage volatility for noise.

    Returns:
        DataFrame with columns [timestamp, open, high, low, close, volume].
    """
    import numpy as np

    np.random.seed(42)  # Deterministic for testing

    timestamps = pd.date_range(end=datetime.now(UTC), periods=num_bars, freq="D")
    closes = [start_price]
    for _ in range(1, num_bars):
        # Apply trend and add noise
        daily_return = trend + np.random.normal(0, volatility)
        closes.append(closes[-1] * (1 + daily_return))

    closes = pd.Series(closes)

    # Create OHLC from closes
    highs = closes * (1 + np.abs(np.random.normal(0, volatility, num_bars)))
    lows = closes * (1 - np.abs(np.random.normal(0, volatility, num_bars)))
    opens = (closes.shift(1).fillna(closes.iloc[0]) + closes) / 2

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens.values,
            "high": highs.values,
            "low": lows.values,
            "close": closes.values,
            "volume": [1_000_000] * num_bars,
        }
    )


def make_indicators(
    spy_price: float = 450.0,
    spy_sma_20: float | None = 445.0,
    spy_sma_50: float | None = 440.0,
    spy_roc_5d: float | None = 0.02,
    spy_realized_vol_20d: float | None = 0.12,
    spy_vs_vwap: float | None = 0.001,
) -> RegimeIndicators:
    """Create RegimeIndicators for testing."""
    return RegimeIndicators(
        spy_price=spy_price,
        spy_sma_20=spy_sma_20,
        spy_sma_50=spy_sma_50,
        spy_roc_5d=spy_roc_5d,
        spy_realized_vol_20d=spy_realized_vol_20d,
        spy_vs_vwap=spy_vs_vwap,
        timestamp=datetime.now(UTC),
    )


class TestComputeIndicators:
    """Tests for RegimeClassifier.compute_indicators()."""

    def test_compute_indicators_basic_with_sufficient_data(self) -> None:
        """With 60 bars, all indicators should be computed."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(60, start_price=450.0, trend=0.001)

        indicators = classifier.compute_indicators(bars)

        assert indicators.spy_price == pytest.approx(bars["close"].iloc[-1])
        assert indicators.spy_sma_20 is not None
        assert indicators.spy_sma_50 is not None
        assert indicators.spy_roc_5d is not None
        assert indicators.spy_realized_vol_20d is not None
        assert indicators.spy_vs_vwap is not None
        assert indicators.timestamp is not None

    def test_compute_indicators_sma_values_are_correct(self) -> None:
        """SMA values should match manual calculation."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(60)

        indicators = classifier.compute_indicators(bars)

        expected_sma_20 = bars["close"].tail(20).mean()
        expected_sma_50 = bars["close"].tail(50).mean()
        assert indicators.spy_sma_20 == pytest.approx(expected_sma_20)
        assert indicators.spy_sma_50 == pytest.approx(expected_sma_50)

    def test_compute_indicators_roc_is_correct(self) -> None:
        """ROC-5d should match manual calculation."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(60)

        indicators = classifier.compute_indicators(bars)

        close_now = bars["close"].iloc[-1]
        close_5d_ago = bars["close"].iloc[-6]
        expected_roc = (close_now - close_5d_ago) / close_5d_ago
        assert indicators.spy_roc_5d == pytest.approx(expected_roc)

    def test_compute_indicators_realized_vol_is_annualized(self) -> None:
        """Realized vol should be annualized (multiplied by sqrt(252))."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(60, volatility=0.02)

        indicators = classifier.compute_indicators(bars)

        daily_returns = bars["close"].pct_change().dropna()
        expected_daily_vol = daily_returns.tail(20).std()
        expected_annualized = expected_daily_vol * (252**0.5)
        assert indicators.spy_realized_vol_20d == pytest.approx(expected_annualized)

    def test_compute_indicators_insufficient_data_for_sma50(self) -> None:
        """With 25 bars, SMA-50 should be None, SMA-20 available."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(25)

        indicators = classifier.compute_indicators(bars)

        assert indicators.spy_sma_20 is not None
        assert indicators.spy_sma_50 is None

    def test_compute_indicators_insufficient_data_for_both_smas(self) -> None:
        """With 10 bars, both SMAs should be None."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(10)

        indicators = classifier.compute_indicators(bars)

        assert indicators.spy_sma_20 is None
        assert indicators.spy_sma_50 is None

    def test_compute_indicators_insufficient_data_for_roc(self) -> None:
        """With 5 bars, ROC-5d should be None (needs 6)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(5)

        indicators = classifier.compute_indicators(bars)

        assert indicators.spy_roc_5d is None

    def test_compute_indicators_insufficient_data_for_realized_vol(self) -> None:
        """With 15 bars, realized vol should be None (needs 21)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(15)

        indicators = classifier.compute_indicators(bars)

        assert indicators.spy_realized_vol_20d is None

    def test_compute_indicators_empty_dataframe_raises(self) -> None:
        """Empty DataFrame should raise ValueError."""
        config = make_config()
        classifier = RegimeClassifier(config)
        empty_bars = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        with pytest.raises(ValueError, match="empty"):
            classifier.compute_indicators(empty_bars)

    def test_compute_indicators_missing_columns_raises(self) -> None:
        """DataFrame missing required columns should raise ValueError."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bad_bars = pd.DataFrame({"timestamp": [1, 2], "close": [100, 101]})

        with pytest.raises(ValueError, match="missing required columns"):
            classifier.compute_indicators(bad_bars)

    def test_compute_indicators_vwap_position_is_relative(self) -> None:
        """VWAP position should be relative to typical price."""
        config = make_config()
        classifier = RegimeClassifier(config)
        bars = make_daily_bars(60)

        indicators = classifier.compute_indicators(bars)

        latest = bars.iloc[-1]
        typical_price = (latest["high"] + latest["low"] + latest["close"]) / 3
        expected_vs_vwap = (latest["close"] - typical_price) / typical_price
        assert indicators.spy_vs_vwap == pytest.approx(expected_vs_vwap)


class TestClassifyBullish:
    """Tests for bullish market regime classification."""

    def test_classify_bullish_trending_above_both_smas_low_vol(self) -> None:
        """SPY above both SMAs with low vol → BULLISH_TRENDING."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=0.02,  # +2% momentum
            spy_realized_vol_20d=0.06,  # Below low threshold
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.BULLISH_TRENDING

    def test_classify_bullish_trending_above_both_smas_normal_vol(self) -> None:
        """SPY above both SMAs with normal vol → BULLISH_TRENDING."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=0.015,
            spy_realized_vol_20d=0.12,  # Normal vol
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.BULLISH_TRENDING

    def test_classify_bullish_with_positive_momentum_confirmation(self) -> None:
        """Positive momentum should reinforce bullish classification."""
        config = make_config()
        classifier = RegimeClassifier(config)
        # SPY above both SMAs (+2 base), with strong momentum
        indicators = make_indicators(
            spy_price=460.0,
            spy_sma_20=455.0,
            spy_sma_50=450.0,  # Above both
            spy_roc_5d=0.03,  # +3% strong momentum confirms
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # +2 (strong bull) + 1 (momentum confirmation) = +3 → BULLISH_TRENDING
        assert regime == MarketRegime.BULLISH_TRENDING


class TestClassifyBearish:
    """Tests for bearish market regime classification."""

    def test_classify_bearish_trending_below_both_smas(self) -> None:
        """SPY below both SMAs → BEARISH_TRENDING."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=430.0,
            spy_sma_20=445.0,
            spy_sma_50=450.0,
            spy_roc_5d=-0.02,  # -2% momentum
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.BEARISH_TRENDING

    def test_classify_bearish_with_negative_momentum_confirmation(self) -> None:
        """Negative momentum should reinforce bearish classification."""
        config = make_config()
        classifier = RegimeClassifier(config)
        # SPY below both SMAs (-2 base), with negative momentum
        indicators = make_indicators(
            spy_price=435.0,
            spy_sma_20=445.0,  # Below SMA-20
            spy_sma_50=440.0,  # Below SMA-50 too
            spy_roc_5d=-0.025,  # Negative momentum confirms
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # -2 (strong bear) + (-1) (momentum confirmation) = -3 → BEARISH_TRENDING
        assert regime == MarketRegime.BEARISH_TRENDING


class TestClassifyRangeBound:
    """Tests for range-bound market regime classification."""

    def test_classify_range_bound_price_between_smas(self) -> None:
        """SPY between SMAs with flat momentum → RANGE_BOUND."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=447.0,
            spy_sma_20=450.0,  # Above SPY
            spy_sma_50=445.0,  # Below SPY
            spy_roc_5d=0.005,  # Flat momentum
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.RANGE_BOUND

    def test_classify_range_bound_contradicting_momentum(self) -> None:
        """Mixed SMAs should classify as range-bound regardless of momentum."""
        config = make_config()
        classifier = RegimeClassifier(config)
        # Price between SMAs (mixed signal), with negative momentum
        indicators = make_indicators(
            spy_price=447.0,
            spy_sma_20=445.0,  # Above SMA-20
            spy_sma_50=450.0,  # Below SMA-50
            spy_roc_5d=-0.02,  # Momentum doesn't help resolve mixed signal
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # Mixed SMAs → trend score 0 → RANGE_BOUND
        assert regime == MarketRegime.RANGE_BOUND


class TestClassifyHighVolatility:
    """Tests for high volatility market regime classification."""

    def test_classify_high_volatility_with_strong_bull_trend(self) -> None:
        """High vol + strong bullish trend (score >= 2) → HIGH_VOLATILITY."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,  # Above both SMAs → +2
            spy_sma_50=440.0,
            spy_roc_5d=0.03,
            spy_realized_vol_20d=0.28,  # Above high threshold
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_classify_high_volatility_with_strong_bear_trend(self) -> None:
        """High vol + strong bearish trend (score <= -2) → HIGH_VOLATILITY."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=430.0,
            spy_sma_20=445.0,  # Below both SMAs → -2
            spy_sma_50=450.0,
            spy_roc_5d=-0.03,
            spy_realized_vol_20d=0.30,  # Above high threshold
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_classify_high_vol_without_strong_trend_is_range_bound(self) -> None:
        """High vol without strong trend doesn't trigger HIGH_VOLATILITY."""
        config = make_config()
        classifier = RegimeClassifier(config)
        # Mixed SMAs → 0 trend score, not strong enough for HIGH_VOLATILITY
        indicators = make_indicators(
            spy_price=447.0,
            spy_sma_20=445.0,  # Above SMA-20
            spy_sma_50=450.0,  # Below SMA-50
            spy_roc_5d=0.005,  # Neutral momentum
            spy_realized_vol_20d=0.28,  # High vol
        )

        regime = classifier.classify(indicators)

        # High vol but no strong trend (mixed SMAs) → RANGE_BOUND
        assert regime == MarketRegime.RANGE_BOUND


class TestClassifyCrisis:
    """Tests for crisis market regime classification."""

    def test_classify_crisis_overrides_bullish_trend(self) -> None:
        """Crisis vol overrides bullish trend → CRISIS."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,  # Above both SMAs
            spy_sma_50=440.0,
            spy_roc_5d=0.05,  # Strong positive momentum
            spy_realized_vol_20d=0.40,  # Crisis level
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.CRISIS

    def test_classify_crisis_overrides_bearish_trend(self) -> None:
        """Crisis vol overrides bearish trend → CRISIS."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=420.0,
            spy_sma_20=445.0,  # Below both SMAs
            spy_sma_50=450.0,
            spy_roc_5d=-0.10,  # Strong negative momentum
            spy_realized_vol_20d=0.50,  # Crisis level
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.CRISIS

    def test_classify_crisis_at_exact_threshold(self) -> None:
        """Vol exactly at crisis threshold → CRISIS."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=445.0,
            spy_sma_20=445.0,
            spy_sma_50=445.0,
            spy_roc_5d=0.0,
            spy_realized_vol_20d=0.35,  # Exactly at crisis threshold
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.CRISIS


class TestClassifyMissingIndicators:
    """Tests for graceful degradation with missing indicators."""

    def test_classify_missing_both_smas_returns_range_bound(self) -> None:
        """Missing SMAs → trend score 0 → RANGE_BOUND."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=None,
            spy_sma_50=None,
            spy_roc_5d=0.02,
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.RANGE_BOUND

    def test_classify_missing_realized_vol_uses_normal_default(self) -> None:
        """Missing realized vol → defaults to NORMAL bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        # Strong bullish trend, but missing vol
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=0.02,
            spy_realized_vol_20d=None,  # Missing
        )

        regime = classifier.classify(indicators)

        # Normal vol default means no crisis/high vol override
        assert regime == MarketRegime.BULLISH_TRENDING

    def test_classify_missing_momentum_still_classifies(self) -> None:
        """Missing momentum doesn't prevent classification."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=None,  # Missing
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # Strong bull (+2) without momentum confirmation
        assert regime == MarketRegime.BULLISH_TRENDING

    def test_classify_only_sma20_available(self) -> None:
        """With only SMA-20 available, classification still works."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,  # Above
            spy_sma_50=None,
            spy_roc_5d=0.015,
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # +1 (mild bull from SMA-20) + momentum → BULLISH_TRENDING
        assert regime == MarketRegime.BULLISH_TRENDING


class TestClassifyBoundaryConditions:
    """Tests for edge cases and boundary conditions."""

    def test_classify_price_exactly_at_sma20(self) -> None:
        """Price exactly at SMA-20 should be neutral for that SMA."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=445.0,
            spy_sma_20=445.0,  # Exactly at
            spy_sma_50=440.0,  # Above
            spy_roc_5d=0.0,
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        # Price = SMA-20 is neutral, above SMA-50 creates mixed signal → RANGE_BOUND
        assert regime == MarketRegime.RANGE_BOUND

    def test_classify_price_exactly_at_both_smas(self) -> None:
        """Price exactly at both SMAs → RANGE_BOUND."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=445.0,
            spy_sma_20=445.0,
            spy_sma_50=445.0,
            spy_roc_5d=0.0,
            spy_realized_vol_20d=0.12,
        )

        regime = classifier.classify(indicators)

        assert regime == MarketRegime.RANGE_BOUND

    def test_classify_vol_exactly_at_high_threshold_is_high(self) -> None:
        """Vol exactly at high threshold → HIGH bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=0.02,
            spy_realized_vol_20d=0.25,  # Exactly at high threshold
        )

        regime = classifier.classify(indicators)

        # High vol + strong trend → HIGH_VOLATILITY
        assert regime == MarketRegime.HIGH_VOLATILITY

    def test_classify_vol_just_below_high_threshold_is_normal(self) -> None:
        """Vol just below high threshold → NORMAL bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(
            spy_price=450.0,
            spy_sma_20=445.0,
            spy_sma_50=440.0,
            spy_roc_5d=0.02,
            spy_realized_vol_20d=0.24,  # Just below high
        )

        regime = classifier.classify(indicators)

        # Normal vol, strong trend → BULLISH_TRENDING
        assert regime == MarketRegime.BULLISH_TRENDING


class TestVolatilityThresholds:
    """Tests for volatility bucket classification."""

    def test_vol_bucket_low(self) -> None:
        """Vol below low threshold → LOW bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_realized_vol_20d=0.05)

        bucket = classifier._compute_volatility_bucket(indicators)

        assert bucket == VolatilityBucket.LOW

    def test_vol_bucket_normal(self) -> None:
        """Vol between low and high thresholds → NORMAL bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_realized_vol_20d=0.12)

        bucket = classifier._compute_volatility_bucket(indicators)

        assert bucket == VolatilityBucket.NORMAL

    def test_vol_bucket_high(self) -> None:
        """Vol between high and crisis thresholds → HIGH bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_realized_vol_20d=0.30)

        bucket = classifier._compute_volatility_bucket(indicators)

        assert bucket == VolatilityBucket.HIGH

    def test_vol_bucket_crisis(self) -> None:
        """Vol above crisis threshold → CRISIS bucket."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_realized_vol_20d=0.45)

        bucket = classifier._compute_volatility_bucket(indicators)

        assert bucket == VolatilityBucket.CRISIS

    def test_vol_bucket_missing_defaults_to_normal(self) -> None:
        """Missing vol → NORMAL bucket (conservative default)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_realized_vol_20d=None)

        bucket = classifier._compute_volatility_bucket(indicators)

        assert bucket == VolatilityBucket.NORMAL


class TestMomentumConfirmation:
    """Tests for momentum confirmation logic."""

    def test_momentum_bullish_above_threshold(self) -> None:
        """ROC > +1% → bullish confirmation."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_roc_5d=0.015)  # +1.5%

        confirmation = classifier._compute_momentum_confirmation(indicators)

        assert confirmation == 1

    def test_momentum_bearish_below_threshold(self) -> None:
        """ROC < -1% → bearish confirmation."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_roc_5d=-0.02)  # -2%

        confirmation = classifier._compute_momentum_confirmation(indicators)

        assert confirmation == -1

    def test_momentum_neutral_within_thresholds(self) -> None:
        """ROC between -1% and +1% → neutral."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_roc_5d=0.005)  # +0.5%

        confirmation = classifier._compute_momentum_confirmation(indicators)

        assert confirmation == 0

    def test_momentum_exactly_at_bullish_threshold(self) -> None:
        """ROC exactly at +1% → neutral (not above)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_roc_5d=0.01)  # Exactly +1%

        confirmation = classifier._compute_momentum_confirmation(indicators)

        assert confirmation == 0

    def test_momentum_missing_returns_neutral(self) -> None:
        """Missing ROC → neutral confirmation."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_roc_5d=None)

        confirmation = classifier._compute_momentum_confirmation(indicators)

        assert confirmation == 0


class TestTrendScore:
    """Tests for trend score computation."""

    def test_trend_score_strong_bull(self) -> None:
        """Price above both SMAs → +2."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=450.0, spy_sma_20=445.0, spy_sma_50=440.0)

        score = classifier._compute_trend_score(indicators)

        assert score == 2

    def test_trend_score_strong_bear(self) -> None:
        """Price below both SMAs → -2."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=430.0, spy_sma_20=445.0, spy_sma_50=450.0)

        score = classifier._compute_trend_score(indicators)

        assert score == -2

    def test_trend_score_mixed_above_sma20_below_sma50(self) -> None:
        """Price above SMA-20 but below SMA-50 → 0 (mixed)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=447.0, spy_sma_20=445.0, spy_sma_50=450.0)

        score = classifier._compute_trend_score(indicators)

        assert score == 0

    def test_trend_score_mixed_below_sma20_above_sma50(self) -> None:
        """Price below SMA-20 but above SMA-50 → 0 (mixed)."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=447.0, spy_sma_20=450.0, spy_sma_50=445.0)

        score = classifier._compute_trend_score(indicators)

        assert score == 0

    def test_trend_score_missing_smas_returns_zero(self) -> None:
        """Missing both SMAs → 0."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=450.0, spy_sma_20=None, spy_sma_50=None)

        score = classifier._compute_trend_score(indicators)

        assert score == 0

    def test_trend_score_only_sma20_available_above(self) -> None:
        """Only SMA-20 available, price above → +1."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=450.0, spy_sma_20=445.0, spy_sma_50=None)

        score = classifier._compute_trend_score(indicators)

        assert score == 1

    def test_trend_score_only_sma50_available_below(self) -> None:
        """Only SMA-50 available, price below → -1."""
        config = make_config()
        classifier = RegimeClassifier(config)
        indicators = make_indicators(spy_price=435.0, spy_sma_20=None, spy_sma_50=440.0)

        score = classifier._compute_trend_score(indicators)

        assert score == -1


# ============================================================================
# RegimeVector Tests (Sprint 27.6)
# ============================================================================


class TestRegimeVector:
    """Tests for the RegimeVector frozen dataclass."""

    def test_construction_with_all_fields(self) -> None:
        """RegimeVector constructs with all 6 dimensions populated."""
        now = datetime.now(UTC)
        rv = RegimeVector(
            computed_at=now,
            trend_score=0.8,
            trend_conviction=0.9,
            volatility_level=0.15,
            volatility_direction=0.2,
            universe_breadth_score=0.65,
            breadth_thrust=True,
            average_correlation=0.45,
            correlation_regime="normal",
            sector_rotation_phase="risk_on",
            leading_sectors=["XLK", "XLY"],
            lagging_sectors=["XLU", "XLP"],
            opening_drive_strength=0.6,
            first_30min_range_ratio=1.1,
            vwap_slope=0.0003,
            direction_change_count=1,
            intraday_character="trending",
            primary_regime=MarketRegime.BULLISH_TRENDING,
            regime_confidence=0.85,
        )

        assert rv.trend_score == 0.8
        assert rv.trend_conviction == 0.9
        assert rv.volatility_level == 0.15
        assert rv.universe_breadth_score == 0.65
        assert rv.breadth_thrust is True
        assert rv.average_correlation == 0.45
        assert rv.correlation_regime == "normal"
        assert rv.sector_rotation_phase == "risk_on"
        assert rv.leading_sectors == ["XLK", "XLY"]
        assert rv.lagging_sectors == ["XLU", "XLP"]
        assert rv.opening_drive_strength == 0.6
        assert rv.intraday_character == "trending"
        assert rv.primary_regime == MarketRegime.BULLISH_TRENDING
        assert rv.regime_confidence == 0.85

    def test_frozen_immutability(self) -> None:
        """RegimeVector is frozen — attributes cannot be mutated."""
        rv = RegimeVector(
            computed_at=datetime.now(UTC),
            trend_score=0.5,
            trend_conviction=0.7,
            volatility_level=0.12,
            volatility_direction=0.0,
            primary_regime=MarketRegime.RANGE_BOUND,
            regime_confidence=0.6,
        )

        with pytest.raises(AttributeError):
            rv.trend_score = 0.9  # type: ignore[misc]

        with pytest.raises(AttributeError):
            rv.primary_regime = MarketRegime.CRISIS  # type: ignore[misc]

    def test_to_dict_from_dict_roundtrip_full(self) -> None:
        """to_dict → from_dict roundtrip preserves all fields."""
        now = datetime.now(UTC)
        original = RegimeVector(
            computed_at=now,
            trend_score=-0.5,
            trend_conviction=0.6,
            volatility_level=0.22,
            volatility_direction=-0.3,
            universe_breadth_score=0.45,
            breadth_thrust=False,
            average_correlation=0.55,
            correlation_regime="concentrated",
            sector_rotation_phase="risk_off",
            leading_sectors=["XLE"],
            lagging_sectors=["XLK", "XLY"],
            opening_drive_strength=0.3,
            first_30min_range_ratio=0.8,
            vwap_slope=-0.0001,
            direction_change_count=4,
            intraday_character="choppy",
            primary_regime=MarketRegime.BEARISH_TRENDING,
            regime_confidence=0.72,
        )

        d = original.to_dict()
        restored = RegimeVector.from_dict(d)

        assert restored.computed_at == original.computed_at
        assert restored.trend_score == original.trend_score
        assert restored.trend_conviction == original.trend_conviction
        assert restored.volatility_level == original.volatility_level
        assert restored.volatility_direction == original.volatility_direction
        assert restored.universe_breadth_score == original.universe_breadth_score
        assert restored.breadth_thrust == original.breadth_thrust
        assert restored.average_correlation == original.average_correlation
        assert restored.correlation_regime == original.correlation_regime
        assert restored.sector_rotation_phase == original.sector_rotation_phase
        assert restored.leading_sectors == original.leading_sectors
        assert restored.lagging_sectors == original.lagging_sectors
        assert restored.opening_drive_strength == original.opening_drive_strength
        assert restored.first_30min_range_ratio == original.first_30min_range_ratio
        assert restored.vwap_slope == original.vwap_slope
        assert restored.direction_change_count == original.direction_change_count
        assert restored.intraday_character == original.intraday_character
        assert restored.primary_regime == original.primary_regime
        assert restored.regime_confidence == original.regime_confidence

    def test_to_dict_from_dict_roundtrip_with_none_fields(self) -> None:
        """Roundtrip works when optional (intraday, breadth, etc.) fields are None."""
        original = RegimeVector(
            computed_at=datetime.now(UTC),
            trend_score=0.3,
            trend_conviction=0.5,
            volatility_level=0.10,
            volatility_direction=0.0,
            primary_regime=MarketRegime.RANGE_BOUND,
            regime_confidence=0.40,
        )

        d = original.to_dict()
        assert d["universe_breadth_score"] is None
        assert d["intraday_character"] is None
        assert d["opening_drive_strength"] is None

        restored = RegimeVector.from_dict(d)
        assert restored.universe_breadth_score is None
        assert restored.breadth_thrust is None
        assert restored.average_correlation is None
        assert restored.correlation_regime is None
        assert restored.sector_rotation_phase is None
        assert restored.leading_sectors == []
        assert restored.lagging_sectors == []
        assert restored.opening_drive_strength is None
        assert restored.intraday_character is None
        assert restored.direction_change_count is None


# ============================================================================
# RegimeClassifierV2 Tests (Sprint 27.6)
# ============================================================================


def make_regime_config(
    breadth_enabled: bool = True,
    correlation_enabled: bool = True,
    sector_enabled: bool = True,
    intraday_enabled: bool = True,
) -> RegimeIntelligenceConfig:
    """Create a RegimeIntelligenceConfig for testing."""
    return RegimeIntelligenceConfig(
        breadth=BreadthConfig(enabled=breadth_enabled),
        correlation=CorrelationConfig(enabled=correlation_enabled),
        sector_rotation=SectorRotationConfig(enabled=sector_enabled),
        intraday=IntradayConfig(enabled=intraday_enabled),
    )


class TestRegimeClassifierV2:
    """Tests for RegimeClassifierV2."""

    def test_classify_delegates_to_v1_bullish(self) -> None:
        """V2.classify() returns same result as V1 for bullish."""
        config = make_config()
        regime_config = make_regime_config()
        v1 = RegimeClassifier(config)
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=450.0, spy_sma_20=445.0, spy_sma_50=440.0,
            spy_roc_5d=0.02, spy_realized_vol_20d=0.12,
        )

        assert v2.classify(indicators) == v1.classify(indicators)
        assert v2.classify(indicators) == MarketRegime.BULLISH_TRENDING

    def test_classify_delegates_to_v1_bearish(self) -> None:
        """V2.classify() returns same result as V1 for bearish."""
        config = make_config()
        regime_config = make_regime_config()
        v1 = RegimeClassifier(config)
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=430.0, spy_sma_20=445.0, spy_sma_50=450.0,
            spy_roc_5d=-0.02, spy_realized_vol_20d=0.12,
        )

        assert v2.classify(indicators) == v1.classify(indicators)
        assert v2.classify(indicators) == MarketRegime.BEARISH_TRENDING

    def test_classify_delegates_to_v1_crisis(self) -> None:
        """V2.classify() returns same result as V1 for crisis."""
        config = make_config()
        regime_config = make_regime_config()
        v1 = RegimeClassifier(config)
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(spy_realized_vol_20d=0.40)

        assert v2.classify(indicators) == v1.classify(indicators)
        assert v2.classify(indicators) == MarketRegime.CRISIS

    def test_classify_delegates_to_v1_range_bound(self) -> None:
        """V2.classify() returns same result as V1 for range bound."""
        config = make_config()
        regime_config = make_regime_config()
        v1 = RegimeClassifier(config)
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=447.0, spy_sma_20=450.0, spy_sma_50=445.0,
            spy_roc_5d=0.005, spy_realized_vol_20d=0.12,
        )

        assert v2.classify(indicators) == v1.classify(indicators)
        assert v2.classify(indicators) == MarketRegime.RANGE_BOUND

    def test_classify_delegates_to_v1_high_volatility(self) -> None:
        """V2.classify() returns same result as V1 for high volatility."""
        config = make_config()
        regime_config = make_regime_config()
        v1 = RegimeClassifier(config)
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=450.0, spy_sma_20=445.0, spy_sma_50=440.0,
            spy_roc_5d=0.03, spy_realized_vol_20d=0.28,
        )

        assert v2.classify(indicators) == v1.classify(indicators)
        assert v2.classify(indicators) == MarketRegime.HIGH_VOLATILITY

    def test_compute_regime_vector_with_no_calculators(self) -> None:
        """V2 with all calculators None produces valid RegimeVector with defaults."""
        config = make_config()
        regime_config = make_regime_config()
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=450.0, spy_sma_20=445.0, spy_sma_50=440.0,
            spy_roc_5d=0.02, spy_realized_vol_20d=0.12,
        )

        rv = v2.compute_regime_vector(indicators)

        assert isinstance(rv, RegimeVector)
        assert rv.primary_regime == MarketRegime.BULLISH_TRENDING
        assert rv.trend_score > 0.0  # Bullish → positive trend_score
        assert rv.trend_conviction > 0.0
        assert rv.volatility_level == 0.12
        # Optional dimensions are None when no calculators
        assert rv.universe_breadth_score is None
        assert rv.breadth_thrust is None
        assert rv.average_correlation is None
        assert rv.correlation_regime is None
        assert rv.sector_rotation_phase is None
        assert rv.leading_sectors == []
        assert rv.lagging_sectors == []
        assert rv.opening_drive_strength is None
        assert rv.intraday_character is None
        # Confidence should be reduced due to missing dimensions
        assert 0.0 < rv.regime_confidence < 1.0

    def test_compute_regime_vector_trend_score_from_indicators(self) -> None:
        """V2 computes correct trend_score from indicator signals."""
        config = make_config()
        regime_config = make_regime_config()
        v2 = RegimeClassifierV2(config, regime_config)

        # Strong bull: above both SMAs → V1 trend score +2 → normalized to +1.0
        bullish = make_indicators(
            spy_price=460.0, spy_sma_20=450.0, spy_sma_50=440.0,
            spy_roc_5d=0.02, spy_realized_vol_20d=0.12,
        )
        rv_bull = v2.compute_regime_vector(bullish)
        assert rv_bull.trend_score == pytest.approx(1.0)

        # Strong bear: below both SMAs → V1 trend score -2 → normalized to -1.0
        bearish = make_indicators(
            spy_price=430.0, spy_sma_20=445.0, spy_sma_50=450.0,
            spy_roc_5d=-0.02, spy_realized_vol_20d=0.12,
        )
        rv_bear = v2.compute_regime_vector(bearish)
        assert rv_bear.trend_score == pytest.approx(-1.0)

        # Mixed: between SMAs → V1 trend score 0 → normalized to 0.0
        mixed = make_indicators(
            spy_price=447.0, spy_sma_20=450.0, spy_sma_50=445.0,
            spy_roc_5d=0.005, spy_realized_vol_20d=0.12,
        )
        rv_mixed = v2.compute_regime_vector(mixed)
        assert rv_mixed.trend_score == pytest.approx(0.0)


class TestRegimeConfidence:
    """Tests for regime_confidence computation (signal_clarity × data_completeness)."""

    def test_crisis_regime_high_signal_clarity(self) -> None:
        """Crisis regime → signal_clarity = 0.95."""
        config = make_config()
        regime_config = make_regime_config()
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(spy_realized_vol_20d=0.45)
        rv = v2.compute_regime_vector(indicators)

        assert rv.primary_regime == MarketRegime.CRISIS
        # signal_clarity=0.95, data_completeness=2/6 (trend+vol only)
        expected = 0.95 * (2.0 / 6.0)
        assert rv.regime_confidence == pytest.approx(expected, abs=0.01)

    def test_strong_trend_moderate_clarity(self) -> None:
        """Strong bullish trend → signal_clarity = 0.85."""
        config = make_config()
        regime_config = make_regime_config()
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=460.0, spy_sma_20=450.0, spy_sma_50=440.0,
            spy_roc_5d=0.03, spy_realized_vol_20d=0.12,
        )
        rv = v2.compute_regime_vector(indicators)

        # trend_score=1.0 (>=0.75), vol>0 → clarity=0.85, completeness=2/6
        expected = 0.85 * (2.0 / 6.0)
        assert rv.regime_confidence == pytest.approx(expected, abs=0.01)

    def test_disabled_dimensions_improve_completeness(self) -> None:
        """Disabling unused dimensions increases data_completeness ratio."""
        config = make_config()
        # Disable all optional dimensions → only trend+vol (2/2 = 1.0 completeness)
        regime_config = make_regime_config(
            breadth_enabled=False,
            correlation_enabled=False,
            sector_enabled=False,
            intraday_enabled=False,
        )
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=460.0, spy_sma_20=450.0, spy_sma_50=440.0,
            spy_roc_5d=0.03, spy_realized_vol_20d=0.12,
        )
        rv = v2.compute_regime_vector(indicators)

        # trend_score=1.0 → clarity=0.85, completeness=2/2=1.0
        expected = 0.85 * 1.0
        assert rv.regime_confidence == pytest.approx(expected, abs=0.01)

    def test_indeterminate_low_clarity(self) -> None:
        """Missing SMAs and no momentum → indeterminate (0.40 clarity)."""
        config = make_config()
        regime_config = make_regime_config(
            breadth_enabled=False,
            correlation_enabled=False,
            sector_enabled=False,
            intraday_enabled=False,
        )
        v2 = RegimeClassifierV2(config, regime_config)

        indicators = make_indicators(
            spy_price=450.0, spy_sma_20=None, spy_sma_50=None,
            spy_roc_5d=None, spy_realized_vol_20d=0.12,
        )
        rv = v2.compute_regime_vector(indicators)

        # trend_score=0.0 → indeterminate → clarity=0.40, completeness=2/2=1.0
        expected = 0.40 * 1.0
        assert rv.regime_confidence == pytest.approx(expected, abs=0.01)


# ============================================================================
# Config Model Tests (Sprint 27.6)
# ============================================================================


class TestRegimeIntelligenceConfig:
    """Tests for RegimeIntelligenceConfig Pydantic models."""

    def test_default_loading(self) -> None:
        """RegimeIntelligenceConfig loads with all defaults."""
        config = RegimeIntelligenceConfig()

        assert config.enabled is True
        assert config.persist_history is True
        assert config.breadth.enabled is True
        assert config.breadth.ma_period == 20
        assert config.breadth.thrust_threshold == 0.80
        assert config.correlation.enabled is True
        assert config.correlation.lookback_days == 20
        assert config.correlation.dispersed_threshold == 0.30
        assert config.correlation.concentrated_threshold == 0.60
        assert config.sector_rotation.enabled is True
        assert config.intraday.enabled is True
        assert config.intraday.first_bar_minutes == 5
        assert config.intraday.classification_times == ["09:35", "10:00", "10:30"]

    def test_invalid_breadth_threshold_rejected(self) -> None:
        """Breadth thrust_threshold > 1.0 is rejected."""
        with pytest.raises(Exception):
            BreadthConfig(thrust_threshold=1.5)

    def test_invalid_correlation_lookback_rejected(self) -> None:
        """Correlation lookback_days < 5 is rejected."""
        with pytest.raises(Exception):
            CorrelationConfig(lookback_days=2)

    def test_config_file_loading(self) -> None:
        """config/regime.yaml loads and matches RegimeIntelligenceConfig fields."""
        config_path = Path("config/regime.yaml")
        assert config_path.exists(), "config/regime.yaml not found"

        with open(config_path) as f:
            raw = yaml.safe_load(f)

        config = RegimeIntelligenceConfig(**raw)

        assert config.enabled is True
        assert config.breadth.ma_period == 20
        assert config.correlation.top_n_symbols == 50
        assert config.intraday.max_direction_changes_trending == 2

    def test_config_silently_ignored_key_detection(self) -> None:
        """Extra/unknown keys in YAML should be detected (not silently ignored)."""
        config_path = Path("config/regime.yaml")
        with open(config_path) as f:
            raw = yaml.safe_load(f)

        # Verify all top-level keys in YAML are recognized by the model
        model_fields = set(RegimeIntelligenceConfig.model_fields.keys())
        yaml_keys = set(raw.keys())

        unrecognized = yaml_keys - model_fields
        assert unrecognized == set(), f"Unrecognized YAML keys: {unrecognized}"

        # Verify sub-model keys match too
        if "breadth" in raw:
            breadth_fields = set(BreadthConfig.model_fields.keys())
            breadth_yaml = set(raw["breadth"].keys())
            assert breadth_yaml - breadth_fields == set(), \
                f"Unrecognized breadth keys: {breadth_yaml - breadth_fields}"

        if "correlation" in raw:
            corr_fields = set(CorrelationConfig.model_fields.keys())
            corr_yaml = set(raw["correlation"].keys())
            assert corr_yaml - corr_fields == set(), \
                f"Unrecognized correlation keys: {corr_yaml - corr_fields}"

        if "intraday" in raw:
            intraday_fields = set(IntradayConfig.model_fields.keys())
            intraday_yaml = set(raw["intraday"].keys())
            assert intraday_yaml - intraday_fields == set(), \
                f"Unrecognized intraday keys: {intraday_yaml - intraday_fields}"

    def test_system_config_includes_regime_intelligence(self) -> None:
        """SystemConfig has regime_intelligence field with correct default."""
        config = SystemConfig()

        assert hasattr(config, "regime_intelligence")
        assert isinstance(config.regime_intelligence, RegimeIntelligenceConfig)
        assert config.regime_intelligence.enabled is True
