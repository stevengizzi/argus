"""Tests for sprint runner configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.sprint_runner.config import (
    ExecutionConfig,
    NotificationTiers,
    RunnerConfig,
    SprintConfig,
)


class TestRunnerConfig:
    """Tests for RunnerConfig."""

    def test_load_valid_config(self, valid_config_file: Path) -> None:
        """Test loading a valid configuration file."""
        config = RunnerConfig.from_yaml(str(valid_config_file))

        assert config.execution.mode == "autonomous"
        assert config.execution.max_retries == 2
        assert config.git.branch == "sprint-23.5"
        assert config.cost.ceiling_usd == 25.0
        assert len(config.sprint.session_order) == 2

    def test_load_config_file_not_found(self) -> None:
        """Test loading a non-existent configuration file."""
        with pytest.raises(FileNotFoundError):
            RunnerConfig.from_yaml("/nonexistent/path/config.yaml")

    def test_invalid_max_retries_rejected(
        self, temp_dir: Path, valid_sprint_dir: Path
    ) -> None:
        """Test that max_retries > 5 is rejected."""
        config_data = {
            "sprint": {"directory": str(valid_sprint_dir)},
            "execution": {"max_retries": 10},  # Invalid: > 5
        }
        config_path = temp_dir / "invalid.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError):
            RunnerConfig.from_yaml(str(config_path))

    def test_defaults_applied(self, valid_sprint_dir: Path, temp_dir: Path) -> None:
        """Test that defaults are applied for missing fields."""
        minimal_config = {"sprint": {"directory": str(valid_sprint_dir)}}
        config_path = temp_dir / "minimal.yaml"
        with open(config_path, "w") as f:
            yaml.dump(minimal_config, f)

        config = RunnerConfig.from_yaml(str(config_path))

        assert config.execution.mode == "autonomous"
        assert config.execution.max_retries == 2
        assert config.git.auto_commit is True
        assert config.cost.ceiling_usd == 50.0
        assert config.triage.enabled is True

    def test_env_override_mode(
        self, valid_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test ARGUS_RUNNER_MODE environment variable override."""
        monkeypatch.setenv("ARGUS_RUNNER_MODE", "human-in-the-loop")

        config = RunnerConfig.from_yaml(str(valid_config_file))

        assert config.execution.mode == "human-in-the-loop"

    def test_env_override_cost_ceiling(
        self, valid_config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test ARGUS_COST_CEILING environment variable override."""
        monkeypatch.setenv("ARGUS_COST_CEILING", "100.0")

        config = RunnerConfig.from_yaml(str(valid_config_file))

        assert config.cost.ceiling_usd == 100.0


class TestSprintConfig:
    """Tests for SprintConfig."""

    def test_directory_must_exist(self) -> None:
        """Test that sprint directory must exist."""
        with pytest.raises(ValueError, match="does not exist"):
            SprintConfig(directory="/nonexistent/path")


class TestExecutionConfig:
    """Tests for ExecutionConfig."""

    def test_valid_modes(self) -> None:
        """Test valid execution modes."""
        exec_config = ExecutionConfig(mode="autonomous")
        assert exec_config.mode == "autonomous"

        exec_config = ExecutionConfig(mode="human-in-the-loop")
        assert exec_config.mode == "human-in-the-loop"

    def test_invalid_mode_rejected(self) -> None:
        """Test that invalid mode is rejected."""
        with pytest.raises(ValueError, match="Invalid execution mode"):
            ExecutionConfig(mode="invalid-mode")


class TestNotificationTiers:
    """Tests for NotificationTiers."""

    def test_halted_cannot_be_disabled(self) -> None:
        """Test that HALTED tier cannot be disabled."""
        with pytest.raises(ValueError, match="HALTED cannot be disabled"):
            NotificationTiers(HALTED=False, COMPLETED=True)

    def test_completed_cannot_be_disabled(self) -> None:
        """Test that COMPLETED tier cannot be disabled."""
        with pytest.raises(ValueError, match="COMPLETED cannot be disabled"):
            NotificationTiers(HALTED=True, COMPLETED=False)
