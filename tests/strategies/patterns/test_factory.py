"""Tests for argus.strategies.patterns.factory.

Covers:
    - get_pattern_class: class name and snake_case resolution, unknown name
    - extract_detection_params: correct fields extracted, base fields excluded
    - build_pattern_from_config: all 7 patterns, non-default values, inferred name
    - compute_parameter_fingerprint: determinism, detection-param sensitivity,
      non-detection-param insensitivity
"""

from __future__ import annotations

import pytest

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
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    extract_detection_params,
    get_pattern_class,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_FIELDS = {"strategy_id": "test", "name": "Test Strategy"}


def _bull_flag_config(**overrides: object) -> BullFlagConfig:
    return BullFlagConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _flat_top_config(**overrides: object) -> FlatTopBreakoutConfig:
    return FlatTopBreakoutConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _dip_and_rip_config(**overrides: object) -> DipAndRipConfig:
    return DipAndRipConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _hod_break_config(**overrides: object) -> HODBreakConfig:
    return HODBreakConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _gap_and_go_config(**overrides: object) -> GapAndGoConfig:
    return GapAndGoConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _abcd_config(**overrides: object) -> ABCDConfig:
    return ABCDConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


def _premarket_config(**overrides: object) -> PreMarketHighBreakConfig:
    return PreMarketHighBreakConfig(**{**_BASE_FIELDS, **overrides})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_pattern_class
# ---------------------------------------------------------------------------


class TestGetPatternClass:
    def test_resolves_pascal_case_class_name(self) -> None:
        cls = get_pattern_class("BullFlagPattern")
        assert cls is BullFlagPattern

    def test_resolves_snake_case_alias(self) -> None:
        cls = get_pattern_class("bull_flag")
        assert cls is BullFlagPattern

    def test_resolves_all_snake_case_aliases(self) -> None:
        cases = [
            ("bull_flag", BullFlagPattern),
            ("flat_top_breakout", FlatTopBreakoutPattern),
            ("dip_and_rip", DipAndRipPattern),
            ("hod_break", HODBreakPattern),
            ("gap_and_go", GapAndGoPattern),
            ("abcd", ABCDPattern),
            ("premarket_high_break", PreMarketHighBreakPattern),
        ]
        for alias, expected_cls in cases:
            assert get_pattern_class(alias) is expected_cls, (
                f"snake_case alias '{alias}' should resolve to {expected_cls.__name__}"
            )

    def test_raises_value_error_for_unknown_name(self) -> None:
        with pytest.raises(ValueError, match="Unknown pattern"):
            get_pattern_class("NonExistentPattern")

    def test_raises_value_error_for_unknown_snake_case(self) -> None:
        with pytest.raises(ValueError, match="Unknown pattern"):
            get_pattern_class("does_not_exist")


# ---------------------------------------------------------------------------
# extract_detection_params
# ---------------------------------------------------------------------------


class TestExtractDetectionParams:
    def test_returns_only_detection_params_not_base_fields(self) -> None:
        config = _bull_flag_config()
        params = extract_detection_params(config, BullFlagPattern)

        # Detection params must be present
        assert "pole_min_bars" in params
        assert "flag_max_bars" in params
        assert "breakout_volume_multiplier" in params

        # Base StrategyConfig fields must NOT be present
        assert "strategy_id" not in params
        assert "name" not in params
        assert "enabled" not in params
        assert "operating_window" not in params
        assert "risk_limits" not in params

    def test_returns_correct_default_values(self) -> None:
        config = _bull_flag_config()
        params = extract_detection_params(config, BullFlagPattern)

        assert params["pole_min_bars"] == 5
        assert params["pole_min_move_pct"] == pytest.approx(0.03)
        assert params["flag_max_bars"] == 20
        assert params["flag_max_retrace_pct"] == pytest.approx(0.50)

    def test_reflects_non_default_config_values(self) -> None:
        config = _bull_flag_config(pole_min_bars=7, flag_max_bars=15)
        params = extract_detection_params(config, BullFlagPattern)

        assert params["pole_min_bars"] == 7
        assert params["flag_max_bars"] == 15

    def test_logs_warning_for_missing_param(self, caplog: pytest.LogCaptureFixture) -> None:
        """Patching a minimal pattern class that declares a param not on the config."""
        from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternParam

        class _ExtraParamPattern(BullFlagPattern):
            def get_default_params(self) -> list[PatternParam]:
                base = super().get_default_params()
                extra = PatternParam(
                    name="nonexistent_param",
                    param_type=float,
                    default=0.0,
                    description="Does not exist on any config",
                )
                return base + [extra]

        config = _bull_flag_config()
        import logging
        with caplog.at_level(logging.WARNING, logger="argus.strategies.patterns.factory"):
            params = extract_detection_params(config, _ExtraParamPattern)  # type: ignore[arg-type]

        assert "nonexistent_param" not in params
        assert any("nonexistent_param" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# build_pattern_from_config
# ---------------------------------------------------------------------------


class TestBuildPatternFromConfig:
    def test_builds_bull_flag_from_default_config(self) -> None:
        config = _bull_flag_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, BullFlagPattern)

    def test_builds_flat_top_from_default_config(self) -> None:
        config = _flat_top_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, FlatTopBreakoutPattern)

    def test_builds_dip_and_rip_from_default_config(self) -> None:
        config = _dip_and_rip_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, DipAndRipPattern)

    def test_builds_hod_break_from_default_config(self) -> None:
        config = _hod_break_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, HODBreakPattern)

    def test_builds_gap_and_go_from_default_config(self) -> None:
        config = _gap_and_go_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, GapAndGoPattern)

    def test_builds_abcd_from_default_config(self) -> None:
        config = _abcd_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, ABCDPattern)

    def test_builds_premarket_high_break_from_default_config(self) -> None:
        config = _premarket_config()
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, PreMarketHighBreakPattern)

    def test_non_default_params_propagate_to_pattern(self) -> None:
        config = _bull_flag_config(pole_min_bars=7, flag_max_bars=30)
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, BullFlagPattern)
        # Verify the values were actually wired through by reading the pattern's
        # get_default_params() which reflects instance state.
        param_map = {p.name: p.default for p in pattern.get_default_params()}
        assert param_map["pole_min_bars"] == 7
        assert param_map["flag_max_bars"] == 30

    def test_explicit_pattern_name_overrides_inference(self) -> None:
        # ABCDConfig has pattern_class="ABCDPattern" — passing an explicit name
        # should still work and win over the config field.
        config = _abcd_config()
        pattern = build_pattern_from_config(config, pattern_name="abcd")
        assert isinstance(pattern, ABCDPattern)

    def test_raises_value_error_for_unknown_pattern_name(self) -> None:
        config = _bull_flag_config()
        with pytest.raises(ValueError, match="Unknown pattern"):
            build_pattern_from_config(config, pattern_name="phantom_pattern")

    def test_abcd_config_uses_pattern_class_field(self) -> None:
        """ABCDConfig.pattern_class drives resolution without an explicit arg."""
        config = _abcd_config()
        assert config.pattern_class == "ABCDPattern"
        pattern = build_pattern_from_config(config)
        assert isinstance(pattern, ABCDPattern)

    def test_snake_case_pattern_name_accepted(self) -> None:
        config = _bull_flag_config()
        pattern = build_pattern_from_config(config, pattern_name="bull_flag")
        assert isinstance(pattern, BullFlagPattern)


# ---------------------------------------------------------------------------
# compute_parameter_fingerprint
# ---------------------------------------------------------------------------


class TestComputeParameterFingerprint:
    def test_fingerprint_is_16_hex_chars(self) -> None:
        config = _bull_flag_config()
        fp = compute_parameter_fingerprint(config, BullFlagPattern)
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_identical_configs_produce_identical_fingerprint(self) -> None:
        config_a = _bull_flag_config()
        config_b = _bull_flag_config()
        assert compute_parameter_fingerprint(config_a, BullFlagPattern) == (
            compute_parameter_fingerprint(config_b, BullFlagPattern)
        )

    def test_different_detection_param_produces_different_fingerprint(self) -> None:
        config_a = _bull_flag_config(pole_min_bars=5)
        config_b = _bull_flag_config(pole_min_bars=8)
        assert compute_parameter_fingerprint(config_a, BullFlagPattern) != (
            compute_parameter_fingerprint(config_b, BullFlagPattern)
        )

    def test_non_detection_param_does_not_affect_fingerprint(self) -> None:
        """Changing strategy_id or name must NOT change the fingerprint."""
        config_a = BullFlagConfig(strategy_id="strategy_a", name="Strategy A")
        config_b = BullFlagConfig(strategy_id="strategy_b", name="Strategy B")
        assert compute_parameter_fingerprint(config_a, BullFlagPattern) == (
            compute_parameter_fingerprint(config_b, BullFlagPattern)
        )

    def test_fingerprint_is_deterministic_on_repeated_calls(self) -> None:
        config = _bull_flag_config()
        first = compute_parameter_fingerprint(config, BullFlagPattern)
        second = compute_parameter_fingerprint(config, BullFlagPattern)
        assert first == second

    def test_fingerprint_differs_between_pattern_types(self) -> None:
        """Different pattern classes with different param sets give different hashes."""
        bull_fp = compute_parameter_fingerprint(_bull_flag_config(), BullFlagPattern)
        abcd_fp = compute_parameter_fingerprint(_abcd_config(), ABCDPattern)
        assert bull_fp != abcd_fp

    def test_enabled_flag_does_not_affect_fingerprint(self) -> None:
        config_enabled = _bull_flag_config(enabled=True)
        config_disabled = _bull_flag_config(enabled=False)
        assert compute_parameter_fingerprint(config_enabled, BullFlagPattern) == (
            compute_parameter_fingerprint(config_disabled, BullFlagPattern)
        )

    # --- Sprint 32.5 S1: exit_overrides backward-compat and expansion ---

    def test_golden_hash_backward_compat(self) -> None:
        """Detection-only fingerprint must equal the pre-expansion golden hash."""
        config = _bull_flag_config()
        fp = compute_parameter_fingerprint(config, BullFlagPattern)
        assert fp == "8b396d4d14db4198"

    def test_none_exit_overrides_matches_golden_hash(self) -> None:
        """Passing exit_overrides=None must produce the same hash as omitting it."""
        config = _bull_flag_config()
        fp_default = compute_parameter_fingerprint(config, BullFlagPattern)
        fp_none = compute_parameter_fingerprint(config, BullFlagPattern, exit_overrides=None)
        assert fp_default == fp_none

    def test_empty_exit_overrides_matches_detection_only(self) -> None:
        """exit_overrides={} must produce the same hash as exit_overrides=None."""
        config = _bull_flag_config()
        fp_none = compute_parameter_fingerprint(config, BullFlagPattern, exit_overrides=None)
        fp_empty = compute_parameter_fingerprint(config, BullFlagPattern, exit_overrides={})
        assert fp_none == fp_empty

    def test_nonempty_exit_overrides_produces_different_fingerprint(self) -> None:
        """Non-empty exit_overrides must yield a fingerprint distinct from detection-only."""
        config = _bull_flag_config()
        fp_detection = compute_parameter_fingerprint(config, BullFlagPattern)
        fp_with_exit = compute_parameter_fingerprint(
            config, BullFlagPattern, exit_overrides={"trailing_stop.atr_multiplier": 2.5}
        )
        assert fp_detection != fp_with_exit

    def test_different_exit_overrides_produce_different_fingerprints(self) -> None:
        """Two variants differing only in exit_overrides receive distinct fingerprints."""
        config = _bull_flag_config()
        fp_a = compute_parameter_fingerprint(
            config, BullFlagPattern, exit_overrides={"trailing_stop.atr_multiplier": 2.0}
        )
        fp_b = compute_parameter_fingerprint(
            config, BullFlagPattern, exit_overrides={"trailing_stop.atr_multiplier": 3.0}
        )
        assert fp_a != fp_b

    def test_exit_overrides_fingerprint_is_deterministic(self) -> None:
        """Same exit_overrides dict always produces the same fingerprint."""
        config = _bull_flag_config()
        overrides = {"trailing_stop.atr_multiplier": 2.5, "escalation.trigger_r": 1.0}
        fp_first = compute_parameter_fingerprint(config, BullFlagPattern, exit_overrides=overrides)
        fp_second = compute_parameter_fingerprint(config, BullFlagPattern, exit_overrides=overrides)
        assert fp_first == fp_second

    def test_exit_overrides_result_is_16_hex_chars(self) -> None:
        """Fingerprint with exit_overrides still returns exactly 16 hex chars."""
        config = _bull_flag_config()
        fp = compute_parameter_fingerprint(
            config, BullFlagPattern, exit_overrides={"trailing_stop.atr_multiplier": 2.5}
        )
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)
