"""Regression tests for ``scripts/revalidate_strategy.py``.

Covers the DEF-189 fix (IMPROMPTU-07, 2026-04-23): VectorBT-era param
names were silently dropped from BacktestEngine's config_overrides
because the prior ``{yaml_name}.{k}`` form produced dot-paths that
don't resolve as nested Pydantic submodels. The fix translates names
via ``_PARAM_NAME_MAP`` and validates each key against the target
config's ``model_fields``, so every key in the returned dict is
guaranteed to hit a real Pydantic field on the target config.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

import pytest

# Import revalidate_strategy.py as a module (it's a script, not a package).
_REVALIDATE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "revalidate_strategy.py"
_SPEC = importlib.util.spec_from_file_location("revalidate_strategy", _REVALIDATE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
revalidate_strategy = importlib.util.module_from_spec(_SPEC)
sys.modules["revalidate_strategy"] = revalidate_strategy
_SPEC.loader.exec_module(revalidate_strategy)


class TestTranslateParams:
    """DEF-189: verify VectorBT→Pydantic name translation + field validation."""

    def test_orb_remaps_vectorbt_names_to_pydantic_fields(self) -> None:
        """`or_minutes` → `orb_window_minutes`, `target_r` → `target_2_r`,
        `max_hold_minutes` → `time_stop_minutes` — the three renames that
        together cover the ORB overrides the prior code silently dropped."""
        translated = revalidate_strategy._translate_params(
            "orb",
            {
                "or_minutes": 30,
                "target_r": 2.5,
                "max_hold_minutes": 20,
                "max_range_atr_ratio": 3.0,  # Already matches OrbBreakoutConfig
            },
        )
        assert translated == {
            "orb_window_minutes": 30,
            "target_2_r": 2.5,
            "time_stop_minutes": 20,
            "max_range_atr_ratio": 3.0,
        }

    def test_vwap_reclaim_renames_volume_and_time_stop(self) -> None:
        """`volume_multiplier`→`volume_confirmation_multiplier`,
        `time_stop_bars`→`time_stop_minutes`, `target_r`→`target_2_r`."""
        translated = revalidate_strategy._translate_params(
            "vwap_reclaim",
            {
                "min_pullback_pct": 0.003,
                "min_pullback_bars": 4,
                "volume_multiplier": 1.5,
                "target_r": 2.0,
                "time_stop_bars": 25,
            },
        )
        assert translated == {
            "min_pullback_pct": 0.003,
            "min_pullback_bars": 4,
            "volume_confirmation_multiplier": 1.5,
            "target_2_r": 2.0,
            "time_stop_minutes": 25,
        }

    def test_afternoon_momentum_renames(self) -> None:
        """`target_r`→`target_2_r`, `time_stop_bars`→`max_hold_minutes`."""
        translated = revalidate_strategy._translate_params(
            "afternoon_momentum",
            {
                "consolidation_atr_ratio": 0.5,
                "min_consolidation_bars": 25,
                "volume_multiplier": 1.3,
                "target_r": 2.0,
                "time_stop_bars": 45,
            },
        )
        assert translated["target_2_r"] == 2.0
        assert translated["max_hold_minutes"] == 45
        assert translated["consolidation_atr_ratio"] == 0.5

    def test_red_to_green_pass_through(self) -> None:
        """All `extract_fixed_params` keys for red_to_green already match
        RedToGreenConfig field names — no renaming, all keys preserved."""
        translated = revalidate_strategy._translate_params(
            "red_to_green",
            {
                "min_gap_down_pct": 0.025,
                "level_proximity_pct": 0.004,
                "volume_confirmation_multiplier": 1.3,
                "time_stop_minutes": 25,
            },
        )
        assert translated == {
            "min_gap_down_pct": 0.025,
            "level_proximity_pct": 0.004,
            "volume_confirmation_multiplier": 1.3,
            "time_stop_minutes": 25,
        }

    def test_bad_key_is_dropped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A param that doesn't map to a Pydantic field (typo or stale
        VectorBT name) is filtered out and a WARNING is logged. This is
        the defense against the DEF-189 silent-no-op failure mode — the
        old code would feed such a key straight to
        ``_apply_config_overrides``, which would silently skip it."""
        caplog.set_level(logging.WARNING, logger="revalidate_strategy")
        translated = revalidate_strategy._translate_params(
            "orb",
            {
                "or_minutes": 15,  # Valid → orb_window_minutes
                "nonexistent_field_xyz": 999,  # Invalid → dropped
            },
        )
        assert translated == {"orb_window_minutes": 15}
        assert "nonexistent_field_xyz" in caplog.text
        assert "OrbBreakoutConfig" in caplog.text

    def test_unknown_strategy_key_raises(self) -> None:
        """Guards against silent mis-routing if revalidate_strategy gets a
        new supported strategy without a corresponding config_class entry."""
        with pytest.raises(ValueError, match="Unknown strategy key"):
            revalidate_strategy._translate_params("nonexistent_strategy", {})


class TestConfigOverridesFormat:
    """End-to-end check: the dict handed to BacktestEngineConfig now uses
    flat keys (not ``{yaml_name}.{k}`` dot-paths) so strict dot-path
    resolution on the target config finds every field."""

    def test_no_dot_prefixed_keys_in_orb_translation(self) -> None:
        translated = revalidate_strategy._translate_params(
            "orb",
            {"or_minutes": 10, "target_r": 1.5, "max_hold_minutes": 15},
        )
        for key in translated:
            assert "." not in key, (
                f"Translated key {key!r} contains a dot — this is the exact "
                "pattern that caused DEF-189's silent no-op. BacktestEngine's "
                "_apply_config_overrides expects flat keys against the "
                "strategy's top-level Pydantic fields."
            )

    def test_all_orb_translated_keys_exist_on_orb_breakout_config(self) -> None:
        """Guarantee: every translated key hits a real Pydantic field on
        OrbBreakoutConfig. If this regresses, BacktestEngine's
        ``_apply_config_overrides`` will silently skip the override."""
        from argus.core.config import OrbBreakoutConfig

        translated = revalidate_strategy._translate_params(
            "orb",
            {
                "or_minutes": 10,
                "target_r": 1.5,
                "max_hold_minutes": 15,
                "max_range_atr_ratio": 3.0,
            },
        )
        valid = set(OrbBreakoutConfig.model_fields.keys())
        for key in translated:
            assert key in valid, f"{key!r} is not a field on OrbBreakoutConfig"
