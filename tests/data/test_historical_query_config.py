"""Tests for HistoricalQueryConfig Pydantic model.

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from argus.data.historical_query_config import HistoricalQueryConfig


class TestHistoricalQueryConfigDefaults:
    """Verify default field values."""

    def test_enabled_defaults_to_false(self) -> None:
        config = HistoricalQueryConfig()
        assert config.enabled is False

    def test_cache_dir_default(self) -> None:
        config = HistoricalQueryConfig()
        assert config.cache_dir == "data/databento_cache"

    def test_max_memory_mb_default(self) -> None:
        config = HistoricalQueryConfig()
        assert config.max_memory_mb == 2048

    def test_default_threads_default(self) -> None:
        config = HistoricalQueryConfig()
        assert config.default_threads == 4


class TestHistoricalQueryConfigValidation:
    """Verify field-level validation."""

    def test_max_memory_mb_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            HistoricalQueryConfig(max_memory_mb=0)

    def test_default_threads_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            HistoricalQueryConfig(default_threads=0)

    def test_cache_dir_must_not_be_empty(self) -> None:
        with pytest.raises(Exception):
            HistoricalQueryConfig(cache_dir="")

    def test_cache_dir_must_not_be_blank(self) -> None:
        with pytest.raises(Exception):
            HistoricalQueryConfig(cache_dir="   ")

    def test_valid_custom_values_accepted(self) -> None:
        config = HistoricalQueryConfig(
            enabled=True,
            cache_dir="/tmp/custom-cache",
            max_memory_mb=4096,
            default_threads=8,
        )
        assert config.enabled is True
        assert config.cache_dir == "/tmp/custom-cache"
        assert config.max_memory_mb == 4096
        assert config.default_threads == 8


class TestHistoricalQueryConfigYaml:
    """Verify the YAML file cross-validates with the Pydantic model."""

    def test_yaml_loads_into_config(self) -> None:
        """historical_query.yaml is a bare-field standalone overlay (FIX-16).

        Previously had a `historical_query:` wrapper; flattened by FIX-16
        (audit 2026-04-21, H2-D06) to match the DEC-384 / FIX-02 convention.
        """
        yaml_path = Path("config/historical_query.yaml")
        assert yaml_path.exists(), f"YAML file not found: {yaml_path}"

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # No top-level wrapper — fields live at the root.
        config = HistoricalQueryConfig(**data)
        assert config.enabled is True

    def test_all_yaml_keys_are_recognized(self) -> None:
        """Bare-field YAML keys all map to HistoricalQueryConfig fields."""
        yaml_path = Path("config/historical_query.yaml")
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        model_fields = set(HistoricalQueryConfig.model_fields.keys())
        yaml_keys = set(data.keys())

        unrecognized = yaml_keys - model_fields
        assert not unrecognized, (
            f"YAML keys not in HistoricalQueryConfig.model_fields: {unrecognized}"
        )
