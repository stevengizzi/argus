"""Tests for cache checkpoint merge fix (B1/DEC-361) and trust-cache-on-startup (B2/DEC-362).

Sprint 25.9, Session 2.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import StrategyConfig, UniverseFilterConfig, UniverseManagerConfig
from argus.data.fmp_reference import (
    FMPReferenceClient,
    FMPReferenceConfig,
    SymbolReferenceData,
)
from argus.data.universe_manager import UniverseManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ref_data(symbol: str, sector: str = "Technology") -> SymbolReferenceData:
    """Create a SymbolReferenceData with sensible defaults."""
    return SymbolReferenceData(
        symbol=symbol,
        sector=sector,
        industry="Software",
        market_cap=1_000_000_000,
        prev_close=50.0,
        avg_volume=500_000,
        exchange="NASDAQ",
        is_otc=False,
        fetched_at=datetime.now(ZoneInfo("UTC")),
    )


def _write_cache_file(
    path: str,
    symbols: list[str],
    age_hours: float = 1.0,
) -> None:
    """Write a cache JSON file with given symbols."""
    cached_at = datetime.now(ZoneInfo("UTC")) - timedelta(hours=age_hours)
    data: dict = {}
    for sym in symbols:
        ref = _make_ref_data(sym)
        entry = ref.to_dict(cached_at=cached_at)
        entry["cached_at"] = cached_at.isoformat()
        data[sym] = entry
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# B1 — Checkpoint merge tests
# ---------------------------------------------------------------------------

class TestCheckpointMerge:
    """Tests for B1: cache checkpoint merge preserves existing entries."""

    @pytest.fixture
    def tmp_cache_path(self, tmp_path: Path) -> str:
        return str(tmp_path / "reference_cache.json")

    @pytest.fixture
    def config(self, tmp_cache_path: str) -> FMPReferenceConfig:
        return FMPReferenceConfig(
            cache_file=tmp_cache_path,
            rate_limit_delay_seconds=0,
        )

    @pytest.fixture
    def client(self, config: FMPReferenceConfig) -> FMPReferenceClient:
        c = FMPReferenceClient(config)
        c._api_key = "test_key"
        return c

    async def test_checkpoint_merge_preserves_existing_entries(
        self, client: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """B1 test 1: Existing entries A, B, C. Fetch updates B, adds D.
        After checkpoint, cache contains A, B (fresh), C, D."""
        # Pre-populate disk cache with A, B, C
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT", "GOOG"])

        # Mock FMP to return data for MSFT (update) and TSLA (new)
        async def mock_fetch(session: object, symbol: str) -> SymbolReferenceData | None:
            if symbol in ("MSFT", "TSLA"):
                return _make_ref_data(symbol, sector="Updated")
            return None

        with patch.object(client, "_fetch_single_profile_with_retry", side_effect=mock_fetch):
            await client.fetch_reference_data(["MSFT", "TSLA"])

        # save_cache was called during fetch (or we call it now to verify merge)
        client.save_cache()

        # Read back the cache file
        with open(tmp_cache_path) as f:
            saved = json.load(f)

        # All four symbols should be present
        assert "AAPL" in saved, "Existing entry AAPL lost"
        assert "MSFT" in saved, "Updated entry MSFT lost"
        assert "GOOG" in saved, "Existing entry GOOG lost"
        assert "TSLA" in saved, "New entry TSLA lost"

        # MSFT should have the updated sector
        assert saved["MSFT"]["sector"] == "Updated"

    async def test_checkpoint_merge_with_empty_existing_cache(
        self, client: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """B1 test 2: First-ever fetch with no existing cache. No crash."""
        # No cache file exists
        assert not Path(tmp_cache_path).exists()

        async def mock_fetch(session: object, symbol: str) -> SymbolReferenceData | None:
            return _make_ref_data(symbol)

        with patch.object(client, "_fetch_single_profile_with_retry", side_effect=mock_fetch):
            result = await client.fetch_reference_data(["AAPL", "MSFT"])

        assert len(result) == 2
        client.save_cache()

        with open(tmp_cache_path) as f:
            saved = json.load(f)
        assert "AAPL" in saved
        assert "MSFT" in saved

    async def test_checkpoint_merge_with_zero_stale_symbols(
        self, client: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """B1 test 3: Cache is fresh. Fetch with empty list is no-op."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT"])

        result = await client.fetch_reference_data([])
        assert result == {}

        # Original cache should still be loadable
        loaded = client.load_cache()
        assert "AAPL" in loaded
        assert "MSFT" in loaded

    async def test_sequential_checkpoints_preserve_entries(
        self, client: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """B1 test 10: Two sequential checkpoints during same fetch both
        produce valid merged caches (no entries lost between checkpoints)."""
        # Pre-populate with 3 entries
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT", "GOOG"])

        call_count = 0

        async def mock_fetch(session: object, symbol: str) -> SymbolReferenceData | None:
            nonlocal call_count
            call_count += 1
            return _make_ref_data(symbol)

        symbols = [f"SYM{i}" for i in range(5)]

        with patch.object(client, "_fetch_single_profile_with_retry", side_effect=mock_fetch):
            await client.fetch_reference_data(symbols)

        client.save_cache()

        with open(tmp_cache_path) as f:
            saved = json.load(f)

        # All original + new should be present
        assert "AAPL" in saved
        assert "MSFT" in saved
        assert "GOOG" in saved
        for i in range(5):
            assert f"SYM{i}" in saved


# ---------------------------------------------------------------------------
# B2 — Trust cache on startup tests
# ---------------------------------------------------------------------------

class TestTrustCacheStartup:
    """Tests for B2: trust-cache-on-startup behavior."""

    @pytest.fixture
    def tmp_cache_path(self, tmp_path: Path) -> str:
        return str(tmp_path / "reference_cache.json")

    @pytest.fixture
    def um_config(self) -> UniverseManagerConfig:
        return UniverseManagerConfig(
            enabled=True,
            min_price=1.0,
            max_price=10000.0,
            min_avg_volume=100,
            exclude_otc=True,
            trust_cache_on_startup=True,
        )

    def _make_um(
        self,
        tmp_cache_path: str,
        config: UniverseManagerConfig,
    ) -> tuple[UniverseManager, FMPReferenceClient]:
        """Create a UniverseManager with a real FMPReferenceClient."""
        fmp_config = FMPReferenceConfig(
            cache_file=tmp_cache_path,
            rate_limit_delay_seconds=0,
        )
        fmp_client = FMPReferenceClient(fmp_config)
        fmp_client._api_key = "test_key"
        scanner = MagicMock()
        um = UniverseManager(fmp_client, config, scanner)
        return um, fmp_client

    async def test_trust_cache_returns_cached_data_without_api_calls(
        self, tmp_cache_path: str, um_config: UniverseManagerConfig
    ) -> None:
        """B2 test 4: With trust=True and non-empty cache, build_viable_universe
        returns immediately with cached data. No FMP API calls."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT", "GOOG"])

        um, fmp_client = self._make_um(tmp_cache_path, um_config)

        # Spy on fetch_reference_data_incremental to verify it's NOT called
        fmp_client.fetch_reference_data_incremental = AsyncMock()

        viable = await um.build_viable_universe(
            ["AAPL", "MSFT", "GOOG"], trust_cache=True
        )

        # Should return viable symbols from cache
        assert len(viable) > 0
        # fetch_reference_data_incremental should NOT have been called
        fmp_client.fetch_reference_data_incremental.assert_not_called()

    async def test_trust_cache_disabled_reverts_to_blocking(
        self, tmp_cache_path: str
    ) -> None:
        """B2 test 5: With trust=False, build_viable_universe blocks on
        fetching stale entries (existing behavior)."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT"])

        config = UniverseManagerConfig(
            enabled=True,
            min_price=1.0,
            max_price=10000.0,
            min_avg_volume=100,
            exclude_otc=True,
            trust_cache_on_startup=False,
        )
        um, fmp_client = self._make_um(tmp_cache_path, config)

        # Mock the incremental fetch (the blocking path)
        ref_data = {
            "AAPL": _make_ref_data("AAPL"),
            "MSFT": _make_ref_data("MSFT"),
        }
        fmp_client.fetch_reference_data_incremental = AsyncMock(return_value=ref_data)

        viable = await um.build_viable_universe(
            ["AAPL", "MSFT"], trust_cache=False
        )

        # fetch_reference_data_incremental SHOULD have been called
        fmp_client.fetch_reference_data_incremental.assert_called_once()
        assert len(viable) > 0

    async def test_trust_cache_with_missing_cache_falls_back(
        self, tmp_cache_path: str, um_config: UniverseManagerConfig
    ) -> None:
        """B2 test 6: If cache doesn't exist, fall back to synchronous fetch
        regardless of trust_cache_on_startup config."""
        # No cache file
        assert not Path(tmp_cache_path).exists()

        um, fmp_client = self._make_um(tmp_cache_path, um_config)

        ref_data = {"AAPL": _make_ref_data("AAPL")}
        fmp_client.fetch_reference_data_incremental = AsyncMock(return_value=ref_data)

        viable = await um.build_viable_universe(
            ["AAPL"], trust_cache=True
        )

        # Should fall through to blocking fetch since cache is empty
        fmp_client.fetch_reference_data_incremental.assert_called_once()
        assert len(viable) > 0

    async def test_background_refresh_task_runs(
        self, tmp_cache_path: str
    ) -> None:
        """B2 test 7: Background refresh task starts and runs."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT"], age_hours=48)

        fmp_config = FMPReferenceConfig(
            cache_file=tmp_cache_path,
            rate_limit_delay_seconds=0,
            cache_max_age_hours=24,
        )
        client = FMPReferenceClient(fmp_config)
        client._api_key = "test_key"

        # Mock the fetch to simulate successful refresh
        async def mock_fetch(session: object, symbol: str) -> SymbolReferenceData | None:
            return _make_ref_data(symbol, sector="Refreshed")

        with patch.object(client, "_fetch_single_profile_with_retry", side_effect=mock_fetch):
            await client.background_refresh(["AAPL", "MSFT"])

        # Cache should be updated
        assert client._cache["AAPL"].sector == "Refreshed"
        assert client._cache["MSFT"].sector == "Refreshed"

    async def test_background_refresh_handles_fmp_errors(
        self, tmp_cache_path: str
    ) -> None:
        """B2 test 8: Background refresh handles FMP errors gracefully."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT"])

        fmp_config = FMPReferenceConfig(
            cache_file=tmp_cache_path,
            rate_limit_delay_seconds=0,
        )
        client = FMPReferenceClient(fmp_config)
        client._api_key = "test_key"

        # Mock to raise exception
        with patch.object(
            client, "fetch_reference_data",
            new_callable=AsyncMock,
            side_effect=Exception("FMP 429 rate limit"),
        ):
            # Should not raise — logs error and returns
            await client.background_refresh(["AAPL", "MSFT"])

        # Client should still be functional (didn't crash)
        assert client._api_key == "test_key"

    async def test_routing_table_rebuild_after_refresh(
        self, tmp_cache_path: str
    ) -> None:
        """B2 test 9: After background refresh, routing table is rebuilt
        and strategy watchlists are updated."""
        _write_cache_file(tmp_cache_path, ["AAPL", "MSFT", "GOOG"])

        um_config = UniverseManagerConfig(
            enabled=True,
            min_price=1.0,
            max_price=10000.0,
            min_avg_volume=100,
            exclude_otc=True,
        )
        fmp_config = FMPReferenceConfig(
            cache_file=tmp_cache_path,
            rate_limit_delay_seconds=0,
        )
        fmp_client = FMPReferenceClient(fmp_config)
        fmp_client._api_key = "test_key"
        scanner = MagicMock()
        um = UniverseManager(fmp_client, um_config, scanner)

        # Populate internal cache to simulate post-refresh state
        ref_data = {
            "AAPL": _make_ref_data("AAPL"),
            "MSFT": _make_ref_data("MSFT"),
            "GOOG": _make_ref_data("GOOG"),
            "TSLA": _make_ref_data("TSLA"),  # New symbol added by refresh
        }
        fmp_client._cache = ref_data

        # Build routing table with one strategy
        strategy_config = StrategyConfig(
            strategy_id="test_strategy",
            name="Test Strategy",
            allocated_capital=100000,
        )

        um.rebuild_after_refresh({"test_strategy": strategy_config})

        # Routing table should include all 4 symbols
        assert um.viable_count == 4
        assert "TSLA" in um.viable_symbols
        assert um.get_strategy_universe_size("test_strategy") == 4


# ---------------------------------------------------------------------------
# Config validation test
# ---------------------------------------------------------------------------

class TestConfigValidation:
    """Config validation: trust_cache_on_startup recognized by Pydantic model."""

    def test_trust_cache_on_startup_in_yaml_config(self) -> None:
        """Verify YAML config key maps to Pydantic model field."""
        import yaml

        yaml_path = Path("config/system.yaml")
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)

        um_section = raw.get("universe_manager", {})
        model_fields = set(UniverseManagerConfig.model_fields.keys())

        # All YAML keys should be recognized by the model
        for key in um_section:
            assert key in model_fields, (
                f"YAML key '{key}' not in UniverseManagerConfig model fields"
            )

        # Specifically check the new field
        assert "trust_cache_on_startup" in um_section
        assert "trust_cache_on_startup" in model_fields

    def test_trust_cache_on_startup_default_value(self) -> None:
        """Verify default value is True."""
        config = UniverseManagerConfig()
        assert config.trust_cache_on_startup is True
