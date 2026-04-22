"""Tests for VIX data service config and persistence.

Sprint 27.9, Session 1a.

FIX-06 audit 2026-04-21 (P1-G1-L04) extended with refresh-path coverage.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
import yaml
from pydantic import ValidationError

from argus.data.vix_config import VixRegimeConfig
from argus.data.vix_data_service import VIXDataService, VIXDataUnavailable

_ET = ZoneInfo("America/New_York")


def _make_row(row_date: str, vix_close: float = 18.5) -> dict:
    """Create a synthetic vix_daily row."""
    return {
        "date": row_date,
        "vix_open": vix_close - 0.5,
        "vix_high": vix_close + 1.0,
        "vix_low": vix_close - 1.0,
        "vix_close": vix_close,
        "spx_open": 5000.0,
        "spx_high": 5050.0,
        "spx_low": 4980.0,
        "spx_close": 5020.0,
        "vol_of_vol_ratio": 0.85,
        "vix_percentile": 0.45,
        "term_structure_proxy": 1.05,
        "realized_vol_20d": 14.2,
        "variance_risk_premium": 4.3,
    }


class TestConfigYamlMatchesPydanticModel:
    """R13: Verify YAML keys align with Pydantic model fields."""

    def test_config_yaml_matches_pydantic_model(self) -> None:
        """Load vix_regime.yaml and verify all keys recognized by VixRegimeConfig."""
        yaml_path = Path("config/vix_regime.yaml")
        assert yaml_path.exists(), f"YAML config not found: {yaml_path}"

        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        assert raw is not None, "YAML file is empty"

        # Check top-level keys
        model_fields = set(VixRegimeConfig.model_fields.keys())
        yaml_keys = set(raw.keys())

        unexpected = yaml_keys - model_fields
        assert not unexpected, (
            f"YAML keys not in VixRegimeConfig model: {unexpected}"
        )

        # Check nested boundary keys
        from argus.data.vix_config import (
            TermStructureBoundaries,
            VRPBoundaries,
            VolRegimeBoundaries,
        )

        nested_checks = {
            "vol_regime_boundaries": VolRegimeBoundaries,
            "term_structure_boundaries": TermStructureBoundaries,
            "vrp_boundaries": VRPBoundaries,
        }

        for yaml_key, model_cls in nested_checks.items():
            if yaml_key in raw and isinstance(raw[yaml_key], dict):
                nested_model_fields = set(model_cls.model_fields.keys())
                nested_yaml_keys = set(raw[yaml_key].keys())
                unexpected_nested = nested_yaml_keys - nested_model_fields
                assert not unexpected_nested, (
                    f"YAML keys under '{yaml_key}' not in {model_cls.__name__}: "
                    f"{unexpected_nested}"
                )

        # Verify round-trip: YAML can construct a valid config
        config = VixRegimeConfig(**raw)
        assert config.enabled is True
        assert config.vol_short_window == 5
        assert config.vol_long_window == 20


class TestConfigValidators:
    """Verify invalid configs raise ValidationError."""

    def test_short_window_greater_than_long_raises(self) -> None:
        """vol_short_window >= vol_long_window should fail."""
        with pytest.raises(ValidationError, match="vol_short_window"):
            VixRegimeConfig(vol_short_window=25, vol_long_window=20)

    def test_short_window_equal_to_long_raises(self) -> None:
        """vol_short_window == vol_long_window should fail."""
        with pytest.raises(ValidationError, match="vol_short_window"):
            VixRegimeConfig(vol_short_window=20, vol_long_window=20)

    def test_max_staleness_days_below_minimum_raises(self) -> None:
        """max_staleness_days < 1 should fail."""
        with pytest.raises(ValidationError):
            VixRegimeConfig(max_staleness_days=0)

    def test_history_years_below_minimum_raises(self) -> None:
        """history_years < 1 should fail."""
        with pytest.raises(ValidationError):
            VixRegimeConfig(history_years=0)

    def test_update_interval_below_minimum_raises(self) -> None:
        """update_interval_seconds < 60 should fail."""
        with pytest.raises(ValidationError):
            VixRegimeConfig(update_interval_seconds=30)


class TestPersistAndLoadRoundtrip:
    """Verify data integrity through persist → load cycle."""

    def test_persist_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Insert synthetic rows, load, verify integrity."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig()
        service = VIXDataService(config=config, db_path=db_path)

        rows = [
            _make_row("2026-03-20", vix_close=17.5),
            _make_row("2026-03-21", vix_close=18.0),
            _make_row("2026-03-24", vix_close=19.2),
        ]
        service.persist_daily(rows)
        assert service.is_ready

        df = service.load_from_db()
        assert len(df) == 3
        assert list(df["date"]) == ["2026-03-20", "2026-03-21", "2026-03-24"]
        assert df.iloc[0]["vix_close"] == 17.5
        assert df.iloc[2]["vix_close"] == 19.2
        assert df.iloc[1]["realized_vol_20d"] == 14.2

    def test_persist_upserts_on_duplicate_date(self, tmp_path: Path) -> None:
        """INSERT OR REPLACE should update existing rows."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig()
        service = VIXDataService(config=config, db_path=db_path)

        service.persist_daily([_make_row("2026-03-20", vix_close=17.5)])
        service.persist_daily([_make_row("2026-03-20", vix_close=22.0)])

        df = service.load_from_db()
        assert len(df) == 1
        assert df.iloc[0]["vix_close"] == 22.0


class TestStalenessLogic:
    """Verify business-day staleness detection."""

    def test_staleness_logic(self, tmp_path: Path) -> None:
        """Data from 5+ business days ago should be stale."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig(max_staleness_days=3)
        service = VIXDataService(config=config, db_path=db_path)

        # Insert data from 10 calendar days ago (well beyond 3 bdays)
        old_date = (date.today() - timedelta(days=10)).isoformat()
        service.persist_daily([_make_row(old_date)])
        assert service.is_stale is True

        # Insert today's data
        today = date.today().isoformat()
        service.persist_daily([_make_row(today)])
        assert service.is_stale is False

    def test_no_data_is_stale(self, tmp_path: Path) -> None:
        """Empty database should report stale."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig()
        service = VIXDataService(config=config, db_path=db_path)
        assert service.is_stale is True


class TestGetLatestDailyWeekend:
    """Verify weekend/holiday handling in get_latest_daily."""

    def test_get_latest_daily_weekend(self, tmp_path: Path) -> None:
        """On Saturday, last trading day is Friday; Friday data should return."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig(max_staleness_days=3)
        service = VIXDataService(config=config, db_path=db_path)

        # Find the most recent Friday
        today = date.today()
        days_since_friday = (today.weekday() - 4) % 7
        friday = today - timedelta(days=days_since_friday)
        friday_str = friday.isoformat()

        service.persist_daily([_make_row(friday_str, vix_close=20.0)])

        # Mock current time as Saturday 10:00 AM ET
        saturday = friday + timedelta(days=1)
        mock_now = datetime(
            saturday.year, saturday.month, saturday.day,
            10, 0, 0, tzinfo=_ET,
        )

        with patch("argus.data.vix_data_service.datetime") as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = service.get_latest_daily()

        assert result is not None
        assert result["data_date"] == friday_str
        assert result["vix_close"] == 20.0


class TestRefreshPath:
    """Coverage for the yfinance refresh / backfill code path.

    FIX-06 audit 2026-04-21 (P1-G1-L04): lines 556-685 (``initialize`` +
    ``fetch_incremental`` + ``_fetch_range``) were below the 90% data-service
    coverage floor. Data service has no FMP fallback — its graceful-
    degradation path is ``VIXDataUnavailable`` when yfinance returns empty.
    """

    def _synthetic_yf_frame(self, dates: list[str]) -> pd.DataFrame:
        """Build a pandas DataFrame shaped like yfinance daily output."""
        index = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
        return pd.DataFrame(
            {
                "Open": [100.0 + i for i in range(len(dates))],
                "High": [101.0 + i for i in range(len(dates))],
                "Low": [99.0 + i for i in range(len(dates))],
                "Close": [100.5 + i for i in range(len(dates))],
            },
            index=index,
        )

    def test_fetch_range_happy_path_merges_vix_and_spx(
        self, tmp_path: Path
    ) -> None:
        """``_fetch_range`` should merge VIX + SPX frames on the date index."""
        config = VixRegimeConfig()
        service = VIXDataService(
            config=config, db_path=str(tmp_path / "test_vix.db")
        )

        vix_frame = self._synthetic_yf_frame(["2026-03-20", "2026-03-21"])
        spx_frame = self._synthetic_yf_frame(["2026-03-20", "2026-03-21"])

        with patch(
            "argus.data.vix_data_service.yf.download",
            side_effect=[vix_frame, spx_frame],
        ):
            result = service._fetch_range(
                date(2026, 3, 20), date(2026, 3, 22)
            )

        assert not result.empty
        assert list(result["date"]) == ["2026-03-20", "2026-03-21"]
        assert "vix_close" in result.columns
        assert "spx_close" in result.columns
        assert result.iloc[0]["vix_close"] == 100.5

    def test_fetch_range_raises_when_both_empty(
        self, tmp_path: Path
    ) -> None:
        """When yfinance returns empty for BOTH symbols, VIXDataUnavailable."""
        config = VixRegimeConfig()
        service = VIXDataService(
            config=config, db_path=str(tmp_path / "test_vix.db")
        )

        empty = pd.DataFrame()
        with patch(
            "argus.data.vix_data_service.yf.download",
            side_effect=[empty, empty],
        ):
            with pytest.raises(VIXDataUnavailable):
                service._fetch_range(date(2026, 3, 20), date(2026, 3, 22))

    def test_fetch_incremental_skips_when_start_past_today(
        self, tmp_path: Path
    ) -> None:
        """If last_date >= today, fetch_incremental returns empty without
        calling yfinance."""
        config = VixRegimeConfig()
        service = VIXDataService(
            config=config, db_path=str(tmp_path / "test_vix.db")
        )

        tomorrow = date.today() + timedelta(days=1)
        with patch(
            "argus.data.vix_data_service.yf.download"
        ) as mock_download:
            result = service.fetch_incremental(tomorrow)

        assert result.empty
        assert mock_download.call_count == 0

    @pytest.mark.asyncio
    async def test_initialize_falls_back_to_cached_data_on_yfinance_failure(
        self, tmp_path: Path
    ) -> None:
        """When yfinance raises VIXDataUnavailable mid-initialize, the service
        gracefully falls back to cached data and still marks itself ready."""
        db_path = str(tmp_path / "test_vix.db")
        config = VixRegimeConfig()
        service = VIXDataService(config=config, db_path=db_path)

        cached_date = (date.today() - timedelta(days=1)).isoformat()
        service.persist_daily([_make_row(cached_date, vix_close=18.0)])

        async def _immediate_raise() -> pd.DataFrame:
            raise VIXDataUnavailable("simulated yfinance outage")

        with patch.object(
            service, "fetch_incremental",
            side_effect=VIXDataUnavailable("simulated"),
        ):
            # Keep the background task from actually launching.
            with patch.object(service, "_start_daily_update_task"):
                await service.initialize()

        assert service.is_ready is True
        df = service.load_from_db()
        assert not df.empty
