"""Cross-validation tests: PatternModule PatternParam defaults vs Pydantic config fields.

Sprint 32, Session 1 — verifies all 28 new fields added to 6 config classes
match the corresponding pattern constructor defaults exactly, that Pydantic
rejects out-of-range values, and that existing YAML configs load cleanly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    ABCDConfig,
    BullFlagConfig,
    DipAndRipConfig,
    FlatTopBreakoutConfig,
    GapAndGoConfig,
    HODBreakConfig,
    PreMarketHighBreakConfig,
)
from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.dip_and_rip import DipAndRipPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.patterns.gap_and_go import GapAndGoPattern
from argus.strategies.patterns.hod_break import HODBreakPattern
from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

# ---------------------------------------------------------------------------
# Registry: maps pattern class → corresponding Pydantic config class
# ---------------------------------------------------------------------------

_PATTERN_CONFIG_PAIRS: list[tuple[type, type]] = [
    (BullFlagPattern, BullFlagConfig),
    (FlatTopBreakoutPattern, FlatTopBreakoutConfig),
    (DipAndRipPattern, DipAndRipConfig),
    (HODBreakPattern, HODBreakConfig),
    (GapAndGoPattern, GapAndGoConfig),
    (ABCDPattern, ABCDConfig),
    (PreMarketHighBreakPattern, PreMarketHighBreakConfig),
]

# ---------------------------------------------------------------------------
# Cross-validation: PatternParam.default == Pydantic field default
# ---------------------------------------------------------------------------


class TestCrossValidation:
    """Verify every PatternParam name exists in the Pydantic config class
    and that defaults match exactly."""

    @pytest.mark.parametrize("pattern_cls, config_cls", _PATTERN_CONFIG_PAIRS)
    def test_all_pattern_param_names_exist_in_config(
        self, pattern_cls: type, config_cls: type
    ) -> None:
        """Every PatternParam.name must exist as a field on the config class."""
        pattern = pattern_cls()
        params = pattern.get_default_params()
        config_fields = config_cls.model_fields

        missing = [p.name for p in params if p.name not in config_fields]
        assert not missing, (
            f"{config_cls.__name__} is missing fields for PatternParams: {missing}"
        )

    @pytest.mark.parametrize("pattern_cls, config_cls", _PATTERN_CONFIG_PAIRS)
    def test_pattern_param_defaults_match_config_defaults(
        self, pattern_cls: type, config_cls: type
    ) -> None:
        """Every PatternParam.default must equal the Pydantic field default."""
        pattern = pattern_cls()
        params = pattern.get_default_params()
        config_fields = config_cls.model_fields

        mismatches: list[str] = []
        for param in params:
            if param.name not in config_fields:
                continue  # already caught by the previous test
            field_info = config_fields[param.name]
            pydantic_default = field_info.default
            if pydantic_default != param.default:
                mismatches.append(
                    f"{param.name}: PatternParam.default={param.default!r} "
                    f"!= Pydantic default={pydantic_default!r}"
                )

        assert not mismatches, (
            f"{config_cls.__name__} default mismatches:\n" + "\n".join(mismatches)
        )

    def test_dip_and_rip_is_complete_reference(self) -> None:
        """DipAndRipConfig is the reference 'complete' config — all params covered."""
        pattern = DipAndRipPattern()
        params = pattern.get_default_params()
        config_fields = DipAndRipConfig.model_fields

        missing = [p.name for p in params if p.name not in config_fields]
        assert not missing, (
            f"Reference DipAndRipConfig has unexpected missing fields: {missing}"
        )


# ---------------------------------------------------------------------------
# Boundary validation: Pydantic rejects out-of-range values
# ---------------------------------------------------------------------------


class TestBoundaryValidation:
    """Verify Pydantic Field bounds reject out-of-range values."""

    def _minimal_config(self) -> dict[str, Any]:
        """Minimal required fields shared by all StrategyConfig subclasses."""
        return {
            "strategy_id": "test",
            "name": "Test",
            "version": "1.0.0",
            "operating_window": {"earliest_entry": "09:30", "latest_entry": "15:00"},
        }

    # --- BullFlagConfig ---

    def test_bull_flag_min_score_threshold_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "min_score_threshold": 101.0}
        with pytest.raises(ValidationError):
            BullFlagConfig(**cfg)

    def test_bull_flag_min_score_threshold_negative_rejected(self) -> None:
        cfg = {**self._minimal_config(), "min_score_threshold": -1.0}
        with pytest.raises(ValidationError):
            BullFlagConfig(**cfg)

    def test_bull_flag_pole_strength_cap_zero_rejected(self) -> None:
        cfg = {**self._minimal_config(), "pole_strength_cap_pct": 0.0}
        with pytest.raises(ValidationError):
            BullFlagConfig(**cfg)

    def test_bull_flag_breakout_excess_cap_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "breakout_excess_cap_pct": 0.51}
        with pytest.raises(ValidationError):
            BullFlagConfig(**cfg)

    # --- FlatTopBreakoutConfig ---

    def test_flat_top_min_score_threshold_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "min_score_threshold": 200.0}
        with pytest.raises(ValidationError):
            FlatTopBreakoutConfig(**cfg)

    def test_flat_top_max_range_narrowing_negative_rejected(self) -> None:
        cfg = {**self._minimal_config(), "max_range_narrowing": -0.1}
        with pytest.raises(ValidationError):
            FlatTopBreakoutConfig(**cfg)

    # --- HODBreakConfig ---

    def test_hod_break_vwap_extended_pct_zero_rejected(self) -> None:
        cfg = {**self._minimal_config(), "vwap_extended_pct": 0.0}
        with pytest.raises(ValidationError):
            HODBreakConfig(**cfg)

    def test_hod_break_vwap_extended_pct_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "vwap_extended_pct": 0.11}
        with pytest.raises(ValidationError):
            HODBreakConfig(**cfg)

    # --- GapAndGoConfig ---

    def test_gap_and_go_min_score_threshold_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "min_score_threshold": 150.0}
        with pytest.raises(ValidationError):
            GapAndGoConfig(**cfg)

    def test_gap_and_go_gap_atr_cap_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "gap_atr_cap": 11.0}
        with pytest.raises(ValidationError):
            GapAndGoConfig(**cfg)

    def test_gap_and_go_prior_day_avg_volume_negative_rejected(self) -> None:
        cfg = {**self._minimal_config(), "prior_day_avg_volume": -1.0}
        with pytest.raises(ValidationError):
            GapAndGoConfig(**cfg)

    # --- ABCDConfig ---

    def test_abcd_swing_lookback_below_min_rejected(self) -> None:
        cfg = {**self._minimal_config(), "swing_lookback": 1}
        with pytest.raises(ValidationError):
            ABCDConfig(**cfg)

    def test_abcd_swing_lookback_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "swing_lookback": 21}
        with pytest.raises(ValidationError):
            ABCDConfig(**cfg)

    def test_abcd_fib_b_min_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "fib_b_min": 1.1}
        with pytest.raises(ValidationError):
            ABCDConfig(**cfg)

    def test_abcd_completion_tolerance_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "completion_tolerance_percent": 6.0}
        with pytest.raises(ValidationError):
            ABCDConfig(**cfg)

    def test_abcd_target_extension_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "target_extension": 3.1}
        with pytest.raises(ValidationError):
            ABCDConfig(**cfg)

    # --- PreMarketHighBreakConfig ---

    def test_premarket_min_score_threshold_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "min_score_threshold": 101.0}
        with pytest.raises(ValidationError):
            PreMarketHighBreakConfig(**cfg)

    def test_premarket_vwap_extended_pct_above_max_rejected(self) -> None:
        cfg = {**self._minimal_config(), "vwap_extended_pct": 0.11}
        with pytest.raises(ValidationError):
            PreMarketHighBreakConfig(**cfg)

    def test_premarket_gap_up_bonus_pct_negative_rejected(self) -> None:
        cfg = {**self._minimal_config(), "gap_up_bonus_pct": -1.0}
        with pytest.raises(ValidationError):
            PreMarketHighBreakConfig(**cfg)


# ---------------------------------------------------------------------------
# YAML backward compatibility: all 7 strategy YAML configs load cleanly
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent.parent / "config" / "strategies"

_YAML_CONFIG_MAP: list[tuple[str, type]] = [
    ("bull_flag.yaml", BullFlagConfig),
    ("flat_top_breakout.yaml", FlatTopBreakoutConfig),
    ("dip_and_rip.yaml", DipAndRipConfig),
    ("hod_break.yaml", HODBreakConfig),
    ("gap_and_go.yaml", GapAndGoConfig),
    ("abcd.yaml", ABCDConfig),
    ("premarket_high_break.yaml", PreMarketHighBreakConfig),
]


class TestYamlBackwardCompat:
    """Verify existing YAML configs load without errors through Pydantic models."""

    @pytest.mark.parametrize("yaml_file, config_cls", _YAML_CONFIG_MAP)
    def test_yaml_loads_without_error(self, yaml_file: str, config_cls: type) -> None:
        """YAML config must load and validate through the Pydantic model."""
        path = _CONFIG_DIR / yaml_file
        assert path.exists(), f"Strategy YAML not found: {path}"

        with open(path) as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)

        # Should not raise
        instance = config_cls(**raw)
        assert instance.strategy_id is not None

    @pytest.mark.parametrize("yaml_file, config_cls", _YAML_CONFIG_MAP)
    def test_yaml_new_fields_use_defaults_when_absent(
        self, yaml_file: str, config_cls: type
    ) -> None:
        """Fields added in Sprint 32 S1 must silently default when absent from YAML."""
        path = _CONFIG_DIR / yaml_file
        assert path.exists()

        with open(path) as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)

        instance = config_cls(**raw)
        pattern_cls, _ = next(
            (pc, cc) for pc, cc in _PATTERN_CONFIG_PAIRS if cc is config_cls
        )
        pattern = pattern_cls()
        for param in pattern.get_default_params():
            value = getattr(instance, param.name, None)
            assert value is not None or param.default is None, (
                f"{config_cls.__name__}.{param.name} should default to {param.default!r} "
                f"when absent from YAML but got None"
            )
