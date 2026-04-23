"""Tests for argus.intelligence.config."""

from __future__ import annotations

from pathlib import Path

import yaml

import pytest

from argus.intelligence.config import (
    CatalystConfig,
    FinnhubConfig,
    FMPNewsConfig,
    OverflowConfig,
    SECEdgarConfig,
)

_SYSTEM_YAML = Path(__file__).parents[2] / "config" / "system.yaml"


class TestCatalystConfigDefaults:
    def test_loads_with_default_values(self) -> None:
        cfg = CatalystConfig()
        assert cfg.enabled is False
        assert cfg.polling_interval_premarket_seconds == 900
        assert cfg.polling_interval_session_seconds == 1800
        assert cfg.max_batch_size == 20
        assert cfg.daily_cost_ceiling_usd == 5.0
        assert cfg.classification_cache_ttl_hours == 24

    def test_sources_default_to_enabled(self) -> None:
        cfg = CatalystConfig()
        assert cfg.sources.sec_edgar.enabled is True
        assert cfg.sources.fmp_news.enabled is True
        assert cfg.sources.finnhub.enabled is True

    def test_briefing_model_defaults_to_none(self) -> None:
        cfg = CatalystConfig()
        assert cfg.briefing.model is None
        assert cfg.briefing.max_symbols == 30

    def test_sec_edgar_default_filing_types(self) -> None:
        cfg = SECEdgarConfig()
        assert "8-K" in cfg.filing_types
        assert "4" in cfg.filing_types

    def test_fmp_news_default_endpoints(self) -> None:
        cfg = FMPNewsConfig()
        assert "stock_news" in cfg.endpoints
        assert "press_releases" in cfg.endpoints

    def test_finnhub_default_rate_limit(self) -> None:
        cfg = FinnhubConfig()
        assert cfg.rate_limit_per_minute == 60


class TestCatalystConfigYamlAlignment:
    """Verify YAML keys align with Pydantic model fields (no silently ignored keys)."""

    def _flatten_keys(self, d: dict, prefix: str = "") -> set[str]:
        """Recursively collect all dotted keys from a nested dict."""
        keys: set[str] = set()
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            if isinstance(v, dict):
                keys.update(self._flatten_keys(v, full_key))
        return keys

    def _model_fields_recursive(self, model_class: type, prefix: str = "") -> set[str]:
        """Recursively collect all dotted field names from a Pydantic model."""
        from pydantic import BaseModel

        fields: set[str] = set()
        for field_name, field_info in model_class.model_fields.items():
            full_name = f"{prefix}.{field_name}" if prefix else field_name
            fields.add(full_name)
            annotation = field_info.annotation
            # Check if annotation itself is a Pydantic model
            try:
                if issubclass(annotation, BaseModel):
                    fields.update(self._model_fields_recursive(annotation, full_name))
            except TypeError:
                pass  # annotation is not a class (e.g., Optional[str])
        return fields

    def test_yaml_catalyst_keys_all_recognized_by_model(self) -> None:
        """No YAML key under catalyst: should be absent from CatalystConfig model."""
        raw = yaml.safe_load(_SYSTEM_YAML.read_text())
        catalyst_yaml = raw.get("catalyst", {})

        yaml_keys = self._flatten_keys(catalyst_yaml)
        model_keys = self._model_fields_recursive(CatalystConfig)

        unrecognized = yaml_keys - model_keys
        assert not unrecognized, (
            f"YAML keys not present in CatalystConfig model: {sorted(unrecognized)}"
        )

    def test_yaml_catalyst_loads_into_config_without_error(self) -> None:
        """system.yaml catalyst section must parse cleanly into CatalystConfig."""
        raw = yaml.safe_load(_SYSTEM_YAML.read_text())
        catalyst_data = raw.get("catalyst", {})
        cfg = CatalystConfig(**catalyst_data)
        assert cfg.enabled is True

    def test_yaml_catalyst_enabled_is_true(self) -> None:
        raw = yaml.safe_load(_SYSTEM_YAML.read_text())
        assert raw["catalyst"]["enabled"] is True

    def test_yaml_catalyst_sources_sec_edgar_filing_types(self) -> None:
        raw = yaml.safe_load(_SYSTEM_YAML.read_text())
        filing_types = raw["catalyst"]["sources"]["sec_edgar"]["filing_types"]
        assert "8-K" in filing_types
        assert "4" in filing_types

    def test_yaml_catalyst_briefing_model_is_none(self) -> None:
        raw = yaml.safe_load(_SYSTEM_YAML.read_text())
        assert raw["catalyst"]["briefing"]["model"] is None


class TestOverflowConfigDefaults:
    """Tests for OverflowConfig default values and validation."""

    def test_loads_with_default_values(self) -> None:
        """OverflowConfig defaults: enabled=True, broker_capacity=30."""
        cfg = OverflowConfig()
        assert cfg.enabled is True
        assert cfg.broker_capacity == 30

    def test_validates_broker_capacity_non_negative(self) -> None:
        """broker_capacity=0 is valid (effectively disables all positions)."""
        cfg = OverflowConfig(broker_capacity=0)
        assert cfg.broker_capacity == 0

    def test_rejects_negative_broker_capacity(self) -> None:
        """broker_capacity must be >= 0."""
        with pytest.raises(ValueError):
            OverflowConfig(broker_capacity=-1)


# IMPROMPTU-06: TestOverflowConfigYamlAlignment deleted. The overflow section
# was removed from config/system.yaml in Sprint 32.x — the authoritative file
# is config/overflow.yaml. Both tests in the deleted class passed vacuously
# against an empty `raw.get("overflow", {})` and asserted nothing about
# real-world alignment.
