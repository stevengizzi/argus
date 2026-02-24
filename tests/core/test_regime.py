"""Tests for market regime classification."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from argus.core.config import OrchestratorConfig
from argus.core.regime import (
    MarketRegime,
    RegimeClassifier,
    RegimeIndicators,
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
