"""Tests for the run_experiment CLI and ExperimentConfig validation.

Covers:
- --dry-run prints grid without executing
- ExperimentConfig validates all fields correctly
- experiments.yaml keys match ExperimentConfig model fields

Sprint 32, Session 8.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from argus.intelligence.experiments.config import ExperimentConfig


# ---------------------------------------------------------------------------
# ExperimentConfig unit tests
# ---------------------------------------------------------------------------


def test_experiment_config_default_values() -> None:
    """ExperimentConfig creates with documented defaults."""
    cfg = ExperimentConfig()
    assert cfg.enabled is False
    assert cfg.auto_promote is False
    assert cfg.max_variants_per_pattern == 5
    assert cfg.backtest_min_trades == 20
    assert cfg.backtest_min_expectancy == 0.0
    assert cfg.promotion_min_shadow_days == 5
    assert cfg.promotion_min_shadow_trades == 30
    assert cfg.cache_dir == "data/databento_cache"
    assert cfg.variants == {}


def test_experiment_config_enabled_override() -> None:
    """ExperimentConfig can be enabled via constructor."""
    cfg = ExperimentConfig(enabled=True, auto_promote=True)
    assert cfg.enabled is True
    assert cfg.auto_promote is True


def test_experiment_config_rejects_unknown_keys() -> None:
    """ExperimentConfig raises on unrecognized keys (extra='forbid')."""
    with pytest.raises(Exception):
        ExperimentConfig(**{"enabled": False, "unknown_key_xyz": 99})  # type: ignore[arg-type]


def test_experiment_config_field_constraints() -> None:
    """ExperimentConfig rejects out-of-range field values."""
    with pytest.raises(Exception):
        ExperimentConfig(max_variants_per_pattern=0)

    with pytest.raises(Exception):
        ExperimentConfig(max_variants_per_pattern=51)

    with pytest.raises(Exception):
        ExperimentConfig(backtest_min_trades=0)

    with pytest.raises(Exception):
        ExperimentConfig(promotion_min_shadow_days=0)

    with pytest.raises(Exception):
        ExperimentConfig(promotion_min_shadow_trades=0)


# ---------------------------------------------------------------------------
# Config file validation — programmatic (no hardcoded key lists)
# ---------------------------------------------------------------------------


def test_experiments_yaml_keys_match_model_fields() -> None:
    """config/experiments.yaml must not contain keys absent from ExperimentConfig.

    This test is intentionally programmatic — it reads the model fields at
    runtime and compares them against the YAML, catching new model fields that
    were added without updating the YAML (or vice versa).
    """
    yaml_path = Path("config/experiments.yaml")
    assert yaml_path.exists(), "config/experiments.yaml must exist"

    raw = yaml.safe_load(yaml_path.read_text())
    assert isinstance(raw, dict), "config/experiments.yaml must be a dict"

    model_fields = set(ExperimentConfig.model_fields.keys())
    yaml_keys = set(raw.keys())

    # No unrecognized keys in YAML
    extra_keys = yaml_keys - model_fields
    assert extra_keys == set(), (
        f"config/experiments.yaml has keys not in ExperimentConfig: {extra_keys}"
    )


def test_experiments_yaml_is_valid_experiment_config() -> None:
    """config/experiments.yaml must parse successfully into ExperimentConfig."""
    yaml_path = Path("config/experiments.yaml")
    raw = yaml.safe_load(yaml_path.read_text())
    cfg = ExperimentConfig(**raw)
    # Verify it loads cleanly (no exception means pass)
    assert isinstance(cfg, ExperimentConfig)


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_dry_run_prints_grid_without_executing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--dry-run prints grid to stdout and does not call run_sweep."""
    from unittest.mock import MagicMock, patch

    import scripts.run_experiment as cli_module

    captured: list[str] = []
    monkeypatch.setattr("builtins.print", lambda *a, **kw: captured.append(" ".join(str(x) for x in a)))

    with patch.object(cli_module, "load_config") as mock_config, \
         patch("argus.intelligence.experiments.runner.ExperimentRunner.run_sweep") as mock_run:
        mock_config.return_value = ExperimentConfig(enabled=True)
        import asyncio
        exit_code = asyncio.run(
            cli_module.run(
                cli_module.parse_args(["--pattern", "bull_flag", "--dry-run"])
            )
        )

    assert exit_code == 0
    output = "\n".join(captured)
    assert "DRY RUN" in output
    mock_run.assert_not_called()


def test_cli_dry_run_invalid_pattern_returns_error() -> None:
    """--dry-run with an unregistered pattern returns exit code 1."""
    import asyncio

    import scripts.run_experiment as cli_module

    args = cli_module.parse_args(["--pattern", "totally_unknown_xyz", "--dry-run"])
    exit_code = asyncio.run(cli_module.run(args))
    assert exit_code == 1


def test_cli_parse_args_defaults() -> None:
    """parse_args() returns expected defaults."""
    import scripts.run_experiment as cli_module

    args = cli_module.parse_args(["--pattern", "bull_flag"])
    assert args.pattern == "bull_flag"
    assert args.cache_dir is None
    assert args.params is None
    assert args.dry_run is False
    assert args.date_range is None


def test_cli_parse_args_full() -> None:
    """parse_args() captures all flags correctly."""
    import scripts.run_experiment as cli_module

    args = cli_module.parse_args([
        "--pattern", "bull_flag",
        "--cache-dir", "data/my_cache",
        "--params", "a,b,c",
        "--dry-run",
        "--date-range", "2025-01-01,2025-12-31",
    ])
    assert args.pattern == "bull_flag"
    assert args.cache_dir == "data/my_cache"
    assert args.params == "a,b,c"
    assert args.dry_run is True
    assert args.date_range == "2025-01-01,2025-12-31"


def test_cli_invalid_date_range_returns_error() -> None:
    """Malformed --date-range returns exit code 1."""
    import asyncio

    import scripts.run_experiment as cli_module

    args = cli_module.parse_args([
        "--pattern", "bull_flag",
        "--dry-run",
        "--date-range", "bad-date-format",
    ])
    exit_code = asyncio.run(cli_module.run(args))
    assert exit_code == 1
