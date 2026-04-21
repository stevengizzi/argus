"""Regression guard for FIX-01 audit 2026-04-21 / DEC-384 / Option B.

``load_config()`` deep-merges standalone ``config/<name>.yaml`` files over
the corresponding top-level key of the system config with precedence
``standalone > live > base``. ``config/quality_engine.yaml`` is the
first overlay; FIX-02 will add ``config/overflow.yaml``.

These tests use ``tmp_path`` + synthetic YAML files so they never touch
the real ``config/`` tree in the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from argus.core.config import _STANDALONE_SYSTEM_OVERLAYS, load_config


# A minimal system YAML that satisfies SystemConfig validation. Only the
# ``quality_engine`` block matters for the merge tests; the rest is filler.
_BASE_SYSTEM_YAML = {
    "timezone": "America/New_York",
    "market_open": "09:30",
    "market_close": "16:00",
    "log_level": "INFO",
    "heartbeat_interval_seconds": 60,
    "data_dir": "data",
    "data_source": "alpaca",
    "broker_source": "simulated",
    "quality_engine": {
        "enabled": True,
        "weights": {
            "pattern_strength": 0.30,
            "catalyst_quality": 0.25,
            "volume_profile": 0.20,
            "historical_match": 0.15,
            "regime_alignment": 0.10,
        },
        "thresholds": {
            "a_plus": 90,
            "a": 80,
            "a_minus": 70,
            "b_plus": 60,
            "b": 50,
            "b_minus": 40,
            "c_plus": 30,
        },
        "risk_tiers": {
            "a_plus": [0.02, 0.03],
            "a": [0.015, 0.02],
            "a_minus": [0.01, 0.015],
            "b_plus": [0.0075, 0.01],
            "b": [0.005, 0.0075],
            "b_minus": [0.0025, 0.005],
            "c_plus": [0.0025, 0.0025],
        },
        "min_grade_to_trade": "C+",
    },
}


def _write_system_yaml(config_dir: Path, data: dict) -> Path:
    """Write system.yaml into *config_dir* and return the path."""
    path = config_dir / "system.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def _write_quality_overlay(config_dir: Path, data: dict) -> Path:
    """Write quality_engine.yaml into *config_dir* and return the path."""
    path = config_dir / "quality_engine.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


# ---------------------------------------------------------------------------
# 1. Baseline — load_config reads the system.yaml quality_engine block
# ---------------------------------------------------------------------------


def test_load_config_reads_system_yaml_quality_engine(tmp_path: Path) -> None:
    """Without a standalone overlay, the system.yaml values reach the
    validated QualityEngineConfig."""
    _write_system_yaml(tmp_path, _BASE_SYSTEM_YAML)

    config = load_config(tmp_path)

    assert config.system.quality_engine.weights.pattern_strength == 0.30
    assert config.system.quality_engine.thresholds.a_plus == 90


# ---------------------------------------------------------------------------
# 2. Override — standalone YAML wins over system.yaml
# ---------------------------------------------------------------------------


def test_standalone_quality_engine_overrides_system_yaml(tmp_path: Path) -> None:
    """When config/quality_engine.yaml exists it wins over the system.yaml
    quality_engine block — precedence standalone > live."""
    _write_system_yaml(tmp_path, _BASE_SYSTEM_YAML)

    # Standalone: Sprint 32.9 recalibration values.
    overlay = {
        "enabled": True,
        "weights": {
            "pattern_strength": 0.375,
            "catalyst_quality": 0.25,
            "volume_profile": 0.275,
            "historical_match": 0.0,
            "regime_alignment": 0.10,
        },
        "thresholds": {
            "a_plus": 72,
            "a": 66,
            "a_minus": 61,
            "b_plus": 56,
            "b": 51,
            "b_minus": 46,
            "c_plus": 40,
        },
    }
    _write_quality_overlay(tmp_path, overlay)

    config = load_config(tmp_path)

    assert config.system.quality_engine.weights.pattern_strength == 0.375
    assert config.system.quality_engine.weights.historical_match == 0.0
    assert config.system.quality_engine.thresholds.a_plus == 72
    assert config.system.quality_engine.thresholds.c_plus == 40


# ---------------------------------------------------------------------------
# 3. Fallback — no standalone, system.yaml values survive
# ---------------------------------------------------------------------------


def test_missing_standalone_falls_back_to_system_yaml(tmp_path: Path) -> None:
    """Without config/quality_engine.yaml the loaded config reflects only
    system.yaml (no error, no overlay applied)."""
    _write_system_yaml(tmp_path, _BASE_SYSTEM_YAML)
    # Deliberately no quality_engine.yaml.

    config = load_config(tmp_path)

    assert config.system.quality_engine.weights.pattern_strength == 0.30
    assert config.system.quality_engine.thresholds.a_plus == 90


# ---------------------------------------------------------------------------
# 4. Standalone-only key — preserved in merged result
# ---------------------------------------------------------------------------


def test_key_only_in_standalone_appears_in_merged_result(tmp_path: Path) -> None:
    """A key present in the standalone YAML but not in system.yaml must
    appear in the merged config. min_grade_to_trade is stripped from the
    base block and re-added via the overlay."""
    base = {
        **_BASE_SYSTEM_YAML,
        "quality_engine": {
            **_BASE_SYSTEM_YAML["quality_engine"],
        },
    }
    del base["quality_engine"]["min_grade_to_trade"]
    _write_system_yaml(tmp_path, base)

    overlay = {"min_grade_to_trade": "B"}
    _write_quality_overlay(tmp_path, overlay)

    config = load_config(tmp_path)

    assert config.system.quality_engine.min_grade_to_trade == "B"


# ---------------------------------------------------------------------------
# 5. Live-only key — preserved when standalone doesn't touch it
# ---------------------------------------------------------------------------


def test_key_only_in_system_survives_partial_overlay(tmp_path: Path) -> None:
    """A key present in system.yaml but absent from the overlay is preserved
    in the merged result (merge is deep, not replace)."""
    _write_system_yaml(tmp_path, _BASE_SYSTEM_YAML)

    # Overlay only touches weights; thresholds + risk_tiers + min_grade
    # should survive from system.yaml.
    overlay = {
        "weights": {
            "pattern_strength": 0.375,
            "catalyst_quality": 0.25,
            "volume_profile": 0.275,
            "historical_match": 0.0,
            "regime_alignment": 0.10,
        }
    }
    _write_quality_overlay(tmp_path, overlay)

    config = load_config(tmp_path)

    # Overlay value.
    assert config.system.quality_engine.weights.pattern_strength == 0.375
    # Untouched system.yaml values.
    assert config.system.quality_engine.thresholds.a_plus == 90
    assert config.system.quality_engine.min_grade_to_trade == "C+"


# ---------------------------------------------------------------------------
# 6. Structural — the overlay registry must include quality_engine
# ---------------------------------------------------------------------------


def test_quality_engine_is_registered_overlay() -> None:
    """The module-scope overlay registry lists quality_engine.yaml. FIX-02
    extends this tuple to add overflow.yaml without touching load_config()."""
    keys = {section_key for section_key, _filename in _STANDALONE_SYSTEM_OVERLAYS}
    assert "quality_engine" in keys
