"""Fixtures for sprint runner tests.

Uses the workflow submodule's sprint_runner package via the
scripts/sprint_runner symlink.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

# Set ARGUS env prefix so the generalized runner config reads
# ARGUS_RUNNER_MODE, ARGUS_RUNNER_SPRINT_DIR, ARGUS_COST_CEILING
os.environ.setdefault("WORKFLOW_ENV_PREFIX", "ARGUS")


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_sprint_dir(temp_dir: Path) -> Path:
    """Create a valid sprint directory structure."""
    sprint_dir = temp_dir / "docs" / "sprints" / "sprint-23.5"
    sprint_dir.mkdir(parents=True)

    # Create placeholder prompt files
    (sprint_dir / "sprint-23.5-S1-impl.md").write_text("# S1 Implementation")
    (sprint_dir / "sprint-23.5-S1-review.md").write_text("# S1 Review")
    (sprint_dir / "sprint-23.5-S2-impl.md").write_text("# S2 Implementation")
    (sprint_dir / "sprint-23.5-S2-review.md").write_text("# S2 Review")
    (sprint_dir / "review-context.md").write_text("# Review Context")

    return sprint_dir


@pytest.fixture
def valid_config_data(valid_sprint_dir: Path) -> dict:
    """Generate valid configuration data."""
    return {
        "sprint": {
            "directory": str(valid_sprint_dir),
            "session_order": ["S1", "S2"],
            "review_context_file": str(valid_sprint_dir / "review-context.md"),
        },
        "execution": {
            "mode": "autonomous",
            "max_retries": 2,
        },
        "git": {
            "branch": "sprint-23.5",
        },
        "notifications": {
            "tiers": {
                "HALTED": True,
                "COMPLETED": True,
            },
            "primary": {
                "type": "ntfy",
                "endpoint": "https://ntfy.sh/test-topic",
            },
        },
        "cost": {
            "ceiling_usd": 25.0,
        },
    }


@pytest.fixture
def valid_config_file(temp_dir: Path, valid_config_data: dict) -> Path:
    """Create a valid configuration file."""
    config_path = temp_dir / "runner-config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(valid_config_data, f)
    return config_path
