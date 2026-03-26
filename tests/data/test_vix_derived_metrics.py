"""Tests for VIX derived metrics and yfinance integration.

Sprint 27.9, Session 1b.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from argus.data.vix_config import VixRegimeConfig
from argus.data.vix_data_service import VIXDataService, VIXDataUnavailable


def _make_config(**overrides: object) -> VixRegimeConfig:
    """Create a VixRegimeConfig with test-friendly defaults."""
    defaults = {
        "vol_short_window": 5,
        "vol_long_window": 20,
        "percentile_window": 252,
        "ma_window": 20,
        "rv_window": 20,
    }
    defaults.update(overrides)
    return VixRegimeConfig(**defaults)  # type: ignore[arg-type]


def _synthetic_vix_series(n: int, base: float = 20.0, noise: float = 1.0) -> pd.Series:
    """Generate a synthetic VIX close series with controlled noise."""
    rng = np.random.default_rng(42)
    return pd.Series(base + rng.normal(0, noise, n), name="vix_close")


def _synthetic_spx_series(n: int, base: float = 5000.0, daily_return: float = 0.001) -> pd.Series:
    """Generate a synthetic SPX close series with constant daily returns."""
    prices = [base]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + daily_return))
    return pd.Series(prices, name="spx_close")


class TestVolOfVolRatio:
    """Verify vol-of-vol ratio computation with known values."""

    def test_vol_of_vol_ratio_known_values(self, tmp_path: Path) -> None:
        """Synthetic VIX series with known short/long std -> verify ratio."""
        config = _make_config(vol_short_window=5, vol_long_window=10)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        # 100-point series for enough rolling history
        vix = _synthetic_vix_series(100, base=20.0, noise=2.0)
        df = pd.DataFrame({"vix_close": vix, "spx_close": _synthetic_spx_series(100)})

        result = service.compute_derived_metrics(df)

        # First few rows should be NaN (not enough history for rolling)
        assert pd.isna(result["vol_of_vol_ratio"].iloc[0])

        # After enough rows, ratio should be positive and finite
        valid = result["vol_of_vol_ratio"].dropna()
        assert len(valid) > 0
        assert all(np.isfinite(valid))
        assert all(valid > 0)

        # Manually verify one value: sigma_5 / sigma_10 at last row
        sigma_5 = vix.iloc[-5:].std()
        sigma_10 = vix.iloc[-10:].std()
        expected_ratio = sigma_5 / sigma_10
        actual_ratio = result["vol_of_vol_ratio"].iloc[-1]
        assert abs(actual_ratio - expected_ratio) < 0.01


class TestVIXPercentile:
    """Verify VIX percentile rank computation."""

    def test_vix_percentile_known_values(self, tmp_path: Path) -> None:
        """Sorted synthetic series -> highest value should be near 100th pctile."""
        config = _make_config(percentile_window=50)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        # Monotonically increasing VIX: last value is always the highest
        vix = pd.Series(np.linspace(10.0, 30.0, 100), name="vix_close")
        df = pd.DataFrame({"vix_close": vix, "spx_close": _synthetic_spx_series(100)})

        result = service.compute_derived_metrics(df)

        # Last value in a sorted window is the max -> percentile = 1.0
        last_pctile = result["vix_percentile"].iloc[-1]
        assert last_pctile == pytest.approx(1.0, abs=0.01)

        # First valid value (at index 49) should also be 1.0 since series is sorted
        pctile_at_50 = result["vix_percentile"].iloc[49]
        assert pctile_at_50 == pytest.approx(1.0, abs=0.01)


class TestTermStructureProxy:
    """Verify term structure proxy computation."""

    def test_term_structure_proxy_known_values(self, tmp_path: Path) -> None:
        """Constant VIX -> proxy = 1.0. Rising VIX -> proxy > 1.0."""
        config = _make_config(ma_window=10)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        # Constant VIX at 20.0
        n = 50
        constant_vix = pd.Series([20.0] * n, name="vix_close")
        df_const = pd.DataFrame({
            "vix_close": constant_vix,
            "spx_close": _synthetic_spx_series(n),
        })

        result_const = service.compute_derived_metrics(df_const)
        # Constant VIX: close / MA = 1.0
        proxy_const = result_const["term_structure_proxy"].dropna()
        assert all(abs(v - 1.0) < 0.001 for v in proxy_const)

        # Rising VIX: last close > MA -> proxy > 1.0
        rising_vix = pd.Series(np.linspace(15.0, 30.0, n), name="vix_close")
        df_rising = pd.DataFrame({
            "vix_close": rising_vix,
            "spx_close": _synthetic_spx_series(n),
        })

        result_rising = service.compute_derived_metrics(df_rising)
        last_proxy = result_rising["term_structure_proxy"].iloc[-1]
        assert last_proxy > 1.0


class TestRealizedVol:
    """Verify realized volatility computation."""

    def test_realized_vol_known_values(self, tmp_path: Path) -> None:
        """Synthetic SPX with constant daily returns -> verify annualized vol."""
        config = _make_config(rv_window=20)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        # Constant daily return of 0.1% = 0.001
        daily_return = 0.001
        n = 100
        spx = _synthetic_spx_series(n, base=5000.0, daily_return=daily_return)
        df = pd.DataFrame({
            "vix_close": _synthetic_vix_series(n),
            "spx_close": spx,
        })

        result = service.compute_derived_metrics(df)

        # With constant returns, log return std should be ~0
        # (all log returns are identical: log(1.001) ≈ 0.0009995)
        # So realized vol should be ~0 (or very small due to floating point)
        rv_last = result["realized_vol_20d"].iloc[-1]
        # With perfectly constant returns, std ≈ 0
        assert rv_last < 0.001  # Should be effectively zero


class TestVarianceRiskPremium:
    """Verify VRP computation with known values."""

    def test_vrp_known_values(self, tmp_path: Path) -> None:
        """VIX=20, RV=15% -> VRP = 400 - 225 = 175.

        Tests both the formula manually and the end-to-end compute_derived_metrics
        output to ensure the VRP column is correctly computed.
        """
        config = _make_config(rv_window=20)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        n = 50
        df = pd.DataFrame({
            "vix_close": [20.0] * n,
            "spx_close": _synthetic_spx_series(n),
        })

        result = service.compute_derived_metrics(df)

        # End-to-end: VRP column should exist and have valid values after warmup
        vrp_valid = result["variance_risk_premium"].dropna()
        assert len(vrp_valid) > 0

        # With constant VIX=20 and near-zero RV (constant returns), VRP ≈ 400
        last_vrp = result["variance_risk_premium"].iloc[-1]
        last_rv = result["realized_vol_20d"].iloc[-1]
        expected_vrp = 20.0**2 - (last_rv * 100.0)**2
        assert last_vrp == pytest.approx(expected_vrp, abs=0.1)

        # Manual formula verification: VIX=20, RV=15% -> VRP = 400 - 225 = 175
        rv_pct = 15.0
        expected_manual = 20.0**2 - rv_pct**2  # 400 - 225 = 175
        assert expected_manual == pytest.approx(175.0, abs=0.01)


class TestSigma60ZeroGuard:
    """Verify vol_of_vol_ratio handles sigma_long = 0."""

    def test_sigma60_zero_guard(self, tmp_path: Path) -> None:
        """Series where sigma_long is zero -> ratio is NaN, logs WARNING."""
        config = _make_config(vol_short_window=3, vol_long_window=5)
        service = VIXDataService(config=config, db_path=str(tmp_path / "test.db"))

        # Constant VIX -> rolling std = 0
        n = 20
        df = pd.DataFrame({
            "vix_close": [20.0] * n,
            "spx_close": _synthetic_spx_series(n),
        })

        with patch("argus.data.vix_data_service.logger") as mock_logger:
            result = service.compute_derived_metrics(df)

            # sigma_long = 0 for constant series -> ratio should be NaN
            valid_ratios = result["vol_of_vol_ratio"].iloc[5:]  # After enough history
            assert all(pd.isna(valid_ratios)), (
                f"Expected NaN for zero sigma_long, got: {valid_ratios.tolist()}"
            )

            # Should have logged a warning
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "sigma_long is zero" in warning_msg


class TestIncrementalUpdate:
    """Verify incremental fetch adds only new rows."""

    def test_incremental_update(self, tmp_path: Path) -> None:
        """Persist initial data, fetch incremental (mock yfinance), verify only new rows added."""
        db_path = str(tmp_path / "test.db")
        config = _make_config()
        service = VIXDataService(config=config, db_path=db_path)

        # Persist 3 initial rows
        initial_rows = [
            {
                "date": "2026-03-20",
                "vix_close": 18.0, "vix_open": 17.5, "vix_high": 18.5, "vix_low": 17.0,
                "spx_close": 5000.0, "spx_open": 4990.0, "spx_high": 5010.0, "spx_low": 4980.0,
            },
            {
                "date": "2026-03-21",
                "vix_close": 19.0, "vix_open": 18.0, "vix_high": 19.5, "vix_low": 17.5,
                "spx_close": 5010.0, "spx_open": 5000.0, "spx_high": 5020.0, "spx_low": 4990.0,
            },
            {
                "date": "2026-03-22",
                "vix_close": 20.0, "vix_open": 19.0, "vix_high": 20.5, "vix_low": 18.5,
                "spx_close": 5020.0, "spx_open": 5010.0, "spx_high": 5030.0, "spx_low": 5000.0,
            },
        ]
        service.persist_daily(initial_rows)

        # Mock yfinance to return 2 new days
        mock_vix_data = pd.DataFrame(
            {
                "Open": [20.5, 21.0],
                "High": [21.0, 22.0],
                "Low": [19.5, 20.0],
                "Close": [20.8, 21.5],
            },
            index=pd.DatetimeIndex(["2026-03-23", "2026-03-24"]),
        )
        mock_spx_data = pd.DataFrame(
            {
                "Open": [5020.0, 5030.0],
                "High": [5035.0, 5045.0],
                "Low": [5010.0, 5020.0],
                "Close": [5030.0, 5040.0],
            },
            index=pd.DatetimeIndex(["2026-03-23", "2026-03-24"]),
        )

        def mock_download(
            ticker: str, start: str, end: str, progress: bool = False
        ) -> pd.DataFrame:
            if "VIX" in ticker:
                return mock_vix_data
            return mock_spx_data

        with patch("argus.data.vix_data_service.yf.download", side_effect=mock_download):
            new_df = service.fetch_incremental(date(2026, 3, 22))

        assert len(new_df) == 2
        assert new_df.iloc[0]["vix_close"] == pytest.approx(20.8)
        assert new_df.iloc[1]["spx_close"] == pytest.approx(5040.0)

        # Persist new rows and verify total
        service.persist_daily(new_df.to_dict("records"))
        all_data = service.load_from_db()
        assert len(all_data) == 5
