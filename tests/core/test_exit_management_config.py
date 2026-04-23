"""Tests for exit management Pydantic config models and deep_update utility.

Sprint 28.5, Session S2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.config import (
    ExitEscalationConfig,
    ExitManagementConfig,
    EscalationPhase,
    TrailingStopConfig,
    deep_update,
)
from argus.core.events import SignalEvent
from argus.core.exit_math import StopToLevel


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_EXIT_YAML = _CONFIG_DIR / "exit_management.yaml"


# ---------------------------------------------------------------------------
# 1. TrailingStopConfig defaults
# ---------------------------------------------------------------------------


class TestTrailingStopConfig:
    """TrailingStopConfig validation tests."""

    def test_valid_defaults(self) -> None:
        """TrailingStopConfig loads with all defaults correctly."""
        cfg = TrailingStopConfig()
        assert cfg.enabled is False
        assert cfg.type == "atr"
        assert cfg.atr_multiplier == 2.5
        assert cfg.percent == 0.02
        assert cfg.fixed_distance == 0.50
        assert cfg.activation == "after_t1"
        assert cfg.activation_profit_pct == 0.005
        assert cfg.min_trail_distance == 0.05

    def test_rejects_atr_multiplier_zero(self) -> None:
        """atr_multiplier must be > 0."""
        with pytest.raises(ValidationError, match="atr_multiplier"):
            TrailingStopConfig(atr_multiplier=0)

    def test_rejects_atr_multiplier_negative(self) -> None:
        """atr_multiplier must be > 0."""
        with pytest.raises(ValidationError, match="atr_multiplier"):
            TrailingStopConfig(atr_multiplier=-1.0)

    def test_rejects_percent_above_max(self) -> None:
        """percent must be <= 0.2."""
        with pytest.raises(ValidationError, match="percent"):
            TrailingStopConfig(percent=0.25)

    def test_rejects_percent_zero(self) -> None:
        """percent must be > 0."""
        with pytest.raises(ValidationError, match="percent"):
            TrailingStopConfig(percent=0)

    def test_rejects_unknown_key(self) -> None:
        """extra='forbid' catches unknown keys."""
        with pytest.raises(ValidationError, match="bogus_field"):
            TrailingStopConfig(bogus_field=123)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 2. EscalationPhase
# ---------------------------------------------------------------------------


class TestEscalationPhase:
    """EscalationPhase validation tests."""

    def test_rejects_elapsed_pct_above_one(self) -> None:
        """elapsed_pct must be <= 1.0."""
        with pytest.raises(ValidationError, match="elapsed_pct"):
            EscalationPhase(elapsed_pct=1.5, stop_to=StopToLevel.BREAKEVEN)

    def test_rejects_elapsed_pct_zero(self) -> None:
        """elapsed_pct must be > 0."""
        with pytest.raises(ValidationError, match="elapsed_pct"):
            EscalationPhase(elapsed_pct=0, stop_to=StopToLevel.BREAKEVEN)

    def test_valid_phase(self) -> None:
        """Valid phase construction."""
        phase = EscalationPhase(elapsed_pct=0.5, stop_to=StopToLevel.HALF_PROFIT)
        assert phase.elapsed_pct == 0.5
        assert phase.stop_to == StopToLevel.HALF_PROFIT

    def test_rejects_unknown_key(self) -> None:
        """extra='forbid' catches unknown keys."""
        with pytest.raises(ValidationError):
            EscalationPhase(elapsed_pct=0.5, stop_to=StopToLevel.BREAKEVEN, extra_key=True)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 3. StopToLevel enum completeness (AMD-5)
# ---------------------------------------------------------------------------


def test_stop_to_level_has_all_four_values() -> None:
    """StopToLevel enum must have all 4 AMD-5 values."""
    expected = {"breakeven", "quarter_profit", "half_profit", "three_quarter_profit"}
    actual = {member.value for member in StopToLevel}
    assert actual == expected


# ---------------------------------------------------------------------------
# 4. ExitEscalationConfig
# ---------------------------------------------------------------------------


class TestExitEscalationConfig:
    """ExitEscalationConfig validation tests."""

    def test_validates_phases_sorted_ascending(self) -> None:
        """Phases must be sorted by elapsed_pct ascending."""
        with pytest.raises(ValidationError, match="sorted"):
            ExitEscalationConfig(
                enabled=True,
                phases=[
                    EscalationPhase(elapsed_pct=0.75, stop_to=StopToLevel.HALF_PROFIT),
                    EscalationPhase(elapsed_pct=0.50, stop_to=StopToLevel.BREAKEVEN),
                ],
            )

    def test_rejects_duplicate_elapsed_pct(self) -> None:
        """Duplicate elapsed_pct values fail the ascending sort check."""
        with pytest.raises(ValidationError, match="sorted"):
            ExitEscalationConfig(
                enabled=True,
                phases=[
                    EscalationPhase(elapsed_pct=0.50, stop_to=StopToLevel.BREAKEVEN),
                    EscalationPhase(elapsed_pct=0.50, stop_to=StopToLevel.HALF_PROFIT),
                ],
            )

    def test_valid_sorted_phases(self) -> None:
        """Valid sorted phases pass validation."""
        cfg = ExitEscalationConfig(
            enabled=True,
            phases=[
                EscalationPhase(elapsed_pct=0.33, stop_to=StopToLevel.BREAKEVEN),
                EscalationPhase(elapsed_pct=0.66, stop_to=StopToLevel.HALF_PROFIT),
                EscalationPhase(elapsed_pct=0.90, stop_to=StopToLevel.THREE_QUARTER_PROFIT),
            ],
        )
        assert len(cfg.phases) == 3

    def test_empty_phases_valid(self) -> None:
        """Empty phases list is valid (escalation disabled)."""
        cfg = ExitEscalationConfig(enabled=False, phases=[])
        assert cfg.phases == []

    def test_rejects_unknown_key(self) -> None:
        """extra='forbid' catches unknown keys."""
        with pytest.raises(ValidationError):
            ExitEscalationConfig(enabled=False, bad_key="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 5. ExitManagementConfig round-trip from YAML
# ---------------------------------------------------------------------------


def test_exit_management_config_round_trip_from_yaml() -> None:
    """Load exit_management.yaml and construct ExitManagementConfig without error."""
    assert _EXIT_YAML.exists(), f"Missing {_EXIT_YAML}"
    raw = yaml.safe_load(_EXIT_YAML.read_text())
    cfg = ExitManagementConfig(**raw)
    # Verify YAML values load correctly (enabled=true as of Sprint 28.5 config change)
    assert cfg.trailing_stop.enabled is True
    assert cfg.trailing_stop.type == "atr"
    assert cfg.trailing_stop.atr_multiplier == 2.5
    assert cfg.trailing_stop.percent == 0.02
    assert cfg.trailing_stop.fixed_distance == 0.50
    assert cfg.trailing_stop.activation == "after_t1"
    assert cfg.trailing_stop.activation_profit_pct == 0.005
    assert cfg.trailing_stop.min_trail_distance == 0.05
    assert cfg.escalation.enabled is False
    assert cfg.escalation.phases == []


# ---------------------------------------------------------------------------
# 6. Unknown YAML key raises ValidationError (extra="forbid")
# ---------------------------------------------------------------------------


def test_unknown_yaml_key_raises_validation_error() -> None:
    """Extra keys in YAML data trigger ValidationError."""
    raw = yaml.safe_load(_EXIT_YAML.read_text())
    raw["trailing_stop"]["bogus_field"] = 123
    with pytest.raises(ValidationError, match="bogus_field"):
        ExitManagementConfig(**raw)


# ---------------------------------------------------------------------------
# 7-8. deep_update (AMD-1)
# ---------------------------------------------------------------------------


class TestDeepUpdate:
    """deep_update utility tests."""

    def test_single_field_override_inherits_rest(self) -> None:
        """Override one nested field; all others inherit from base."""
        base = {
            "trailing_stop": {
                "enabled": False,
                "type": "atr",
                "atr_multiplier": 2.5,
                "percent": 0.02,
            },
            "escalation": {"enabled": False, "phases": []},
        }
        override = {"trailing_stop": {"atr_multiplier": 3.0}}
        result = deep_update(base, override)
        assert result["trailing_stop"]["atr_multiplier"] == 3.0
        assert result["trailing_stop"]["enabled"] is False
        assert result["trailing_stop"]["type"] == "atr"
        assert result["trailing_stop"]["percent"] == 0.02
        assert result["escalation"]["enabled"] is False

    def test_full_section_override(self) -> None:
        """Override an entire trailing_stop section."""
        base = {
            "trailing_stop": {
                "enabled": False,
                "type": "atr",
                "atr_multiplier": 2.5,
            },
            "escalation": {"enabled": False},
        }
        override = {
            "trailing_stop": {
                "enabled": True,
                "type": "percent",
                "atr_multiplier": 5.0,
            }
        }
        result = deep_update(base, override)
        assert result["trailing_stop"]["enabled"] is True
        assert result["trailing_stop"]["type"] == "percent"
        assert result["trailing_stop"]["atr_multiplier"] == 5.0
        # escalation untouched
        assert result["escalation"]["enabled"] is False

    def test_does_not_mutate_inputs(self) -> None:
        """Neither base nor override dict is mutated."""
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 99}}
        base_copy = {"a": {"b": 1, "c": 2}}
        override_copy = {"a": {"b": 99}}
        deep_update(base, override)
        assert base == base_copy
        assert override == override_copy

    def test_override_key_not_in_base(self) -> None:
        """Keys in override but not in base are included."""
        base = {"a": 1}
        override = {"b": 2}
        result = deep_update(base, override)
        assert result == {"a": 1, "b": 2}

    def test_scalar_override_replaces_dict(self) -> None:
        """A scalar override replaces a dict value (non-recursive case)."""
        base = {"a": {"nested": True}}
        override = {"a": "flat"}
        result = deep_update(base, override)
        assert result["a"] == "flat"


# ---------------------------------------------------------------------------
# 9-10. SignalEvent atr_value backward compatibility
# ---------------------------------------------------------------------------


class TestSignalEventAtrValue:
    """SignalEvent atr_value field tests."""

    def test_default_atr_value_none(self) -> None:
        """Existing SignalEvent construction works without atr_value."""
        sig = SignalEvent(
            strategy_id="test",
            symbol="AAPL",
            entry_price=150.0,
            stop_price=148.0,
        )
        assert sig.atr_value is None

    def test_atr_value_set_correctly(self) -> None:
        """atr_value field stores the provided value."""
        sig = SignalEvent(
            strategy_id="test",
            symbol="AAPL",
            entry_price=150.0,
            stop_price=148.0,
            atr_value=1.5,
        )
        assert sig.atr_value == 1.5

    def test_atr_value_carried_on_signal_rejected_event(self) -> None:
        """SignalRejectedEvent carries atr_value via its signal reference."""
        from argus.core.events import SignalRejectedEvent

        sig = SignalEvent(strategy_id="test", symbol="AAPL", atr_value=2.0)
        rejected = SignalRejectedEvent(
            signal=sig,
            rejection_reason="test",
            rejection_stage="QUALITY_FILTER",
        )
        assert rejected.signal is not None
        assert rejected.signal.atr_value == 2.0


# ---------------------------------------------------------------------------
# ExitManagementConfig extra='forbid' on nested model
# ---------------------------------------------------------------------------


def test_exit_management_config_rejects_unknown_top_key() -> None:
    """ExitManagementConfig itself rejects unknown top-level keys."""
    with pytest.raises(ValidationError):
        ExitManagementConfig(trailing_stop=TrailingStopConfig(), unknown_section={})  # type: ignore[call-arg]
