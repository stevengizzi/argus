"""Tests for --workers CLI flag and universe filter YAML files (Sprint 31.5, Session 3).

Covers:
- parse_args --workers flag parsing
- workers default falls back to ExperimentConfig.max_workers
- config/experiments.yaml max_workers field recognized by ExperimentConfig
- All 10 universe filter YAMLs parse into valid UniverseFilterConfig instances
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from argus.core.config import UniverseFilterConfig  # noqa: E402
from argus.intelligence.experiments.config import ExperimentConfig  # noqa: E402
from scripts.run_experiment import load_config, parse_args  # noqa: E402

_UNIVERSE_FILTERS_DIR = _REPO_ROOT / "config" / "universe_filters"
_EXPERIMENTS_YAML = _REPO_ROOT / "config" / "experiments.yaml"


# ---------------------------------------------------------------------------
# --workers CLI flag tests
# ---------------------------------------------------------------------------


def test_cli_workers_flag_parsed() -> None:
    """--workers N stores N as an integer on the namespace."""
    ns = parse_args(["--pattern", "bull_flag", "--workers", "8"])
    assert ns.workers == 8


def test_cli_workers_flag_value_1() -> None:
    """--workers 1 parses correctly (sequential mode)."""
    ns = parse_args(["--pattern", "bull_flag", "--workers", "1"])
    assert ns.workers == 1


def test_cli_workers_flag_value_4() -> None:
    """--workers 4 parses correctly."""
    ns = parse_args(["--pattern", "bull_flag", "--workers", "4"])
    assert ns.workers == 4


def test_cli_workers_default_is_none() -> None:
    """Without --workers flag, args.workers is None (config default is used)."""
    ns = parse_args(["--pattern", "bull_flag"])
    assert ns.workers is None


def test_cli_workers_default_from_config() -> None:
    """When args.workers is None, workers resolves to ExperimentConfig.max_workers."""
    ns = parse_args(["--pattern", "bull_flag"])
    config = load_config()
    workers = ns.workers if ns.workers is not None else config.max_workers
    assert workers == config.max_workers


# ---------------------------------------------------------------------------
# experiments.yaml max_workers field
# ---------------------------------------------------------------------------


def test_experiments_yaml_max_workers_field() -> None:
    """config/experiments.yaml max_workers key is recognized by ExperimentConfig."""
    raw = yaml.safe_load(_EXPERIMENTS_YAML.read_text())
    assert isinstance(raw, dict)
    assert "max_workers" in raw, "max_workers key missing from config/experiments.yaml"
    config = ExperimentConfig(**raw)
    assert config.max_workers == raw["max_workers"]


def test_experiments_yaml_max_workers_value() -> None:
    """config/experiments.yaml sets max_workers to 4."""
    raw = yaml.safe_load(_EXPERIMENTS_YAML.read_text())
    assert isinstance(raw, dict)
    assert raw["max_workers"] == 4


def test_experiments_yaml_roundtrip() -> None:
    """Full YAML roundtrip into ExperimentConfig succeeds with extra='forbid'."""
    raw = yaml.safe_load(_EXPERIMENTS_YAML.read_text())
    assert isinstance(raw, dict)
    config = ExperimentConfig(**raw)
    assert config.max_workers == 4


# ---------------------------------------------------------------------------
# Universe filter YAML validation — all 10 patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "bull_flag",
        "flat_top_breakout",
        "abcd",
        "dip_and_rip",
        "gap_and_go",
        "hod_break",
        "micro_pullback",
        "narrow_range_breakout",
        "premarket_high_break",
        "vwap_bounce",
    ],
)
def test_universe_filter_yamls_all_valid(name: str) -> None:
    """Each universe filter YAML parses into a valid UniverseFilterConfig."""
    filter_path = _UNIVERSE_FILTERS_DIR / f"{name}.yaml"
    assert filter_path.exists(), f"Missing universe filter file: {filter_path}"
    raw = yaml.safe_load(filter_path.read_text()) or {}
    config = UniverseFilterConfig(**raw)
    # All loaded YAMLs must have at least one non-None filter
    non_none_values = [
        v
        for v in [config.min_price, config.max_price, config.min_avg_volume]
        if v is not None
    ]
    assert len(non_none_values) > 0, f"Filter '{name}' has no static filter criteria"


def test_bull_flag_filter_values() -> None:
    """bull_flag.yaml has the expected filter values."""
    raw = yaml.safe_load((_UNIVERSE_FILTERS_DIR / "bull_flag.yaml").read_text()) or {}
    config = UniverseFilterConfig(**raw)
    assert config.min_price == pytest.approx(10.0)
    assert config.max_price == pytest.approx(500.0)
    assert config.min_avg_volume == 500000


def test_flat_top_breakout_filter_values() -> None:
    """flat_top_breakout.yaml has the expected filter values."""
    raw = (
        yaml.safe_load((_UNIVERSE_FILTERS_DIR / "flat_top_breakout.yaml").read_text())
        or {}
    )
    config = UniverseFilterConfig(**raw)
    assert config.min_price == pytest.approx(10.0)
    assert config.max_price == pytest.approx(500.0)
    assert config.min_avg_volume == 500000
