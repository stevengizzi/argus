"""Tests for auto-split on compaction detection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.sprint_runner.config import (
    AutoSplitConfig,
    ConformanceConfig,
    CostConfig,
    DocSyncConfig,
    ExecutionConfig,
    GitConfig,
    NotificationsConfig,
    RunLogConfig,
    RunnerConfig,
    SessionMetadata,
    SplitDef,
    SprintConfig,
    TriageConfig,
)
from scripts.sprint_runner.executor import ExecutionResult
from scripts.sprint_runner.main import SprintRunner
from scripts.sprint_runner.state import (
    RunPhase,
    RunState,
    RunStatus,
    SessionPlanEntry,
    SessionPlanStatus,
    SessionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_repo(temp_dir: Path) -> Path:
    """Create a temporary git repository with sprint files."""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )

    # Create and commit initial file
    (temp_dir / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "-A"], cwd=temp_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )

    # Create expected branch
    subprocess.run(
        ["git", "checkout", "-b", "sprint-23.5"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )

    # Create sprint directory
    sprint_dir = temp_dir / "docs" / "sprints" / "sprint-23.5"
    sprint_dir.mkdir(parents=True)

    # Create prompt files
    (sprint_dir / "sprint-23.5-S1-impl.md").write_text("# S1 Implementation\n{{TEST_BASELINE}}")
    (sprint_dir / "sprint-23.5-S1-review.md").write_text("# S1 Review")

    # Commit sprint files
    subprocess.run(["git", "add", "-A"], cwd=temp_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add sprint files"],
        cwd=temp_dir,
        capture_output=True,
        check=True,
    )

    return temp_dir


@pytest.fixture
def config_with_auto_split(temp_repo: Path) -> RunnerConfig:
    """Create a runner config with auto-split configuration."""
    sprint_dir = temp_repo / "docs" / "sprints" / "sprint-23.5"
    return RunnerConfig(
        sprint=SprintConfig(
            directory=str(sprint_dir),
            session_order=["S1"],
        ),
        execution=ExecutionConfig(
            mode="autonomous",
            max_retries=2,
            retry_delay_seconds=1,
            compaction_threshold_bytes=100,  # Low threshold for testing
        ),
        git=GitConfig(
            branch="sprint-23.5",
            auto_commit=True,
        ),
        notifications=NotificationsConfig(),
        cost=CostConfig(ceiling_usd=50.0),
        run_log=RunLogConfig(base_directory=""),
        triage=TriageConfig(enabled=False),
        conformance=ConformanceConfig(enabled=False),
        doc_sync=DocSyncConfig(enabled=False),
        session_metadata={
            "S1": SessionMetadata(
                title="Session 1",
                compaction_score=8,
                auto_split=AutoSplitConfig(
                    trigger="compaction_score > 7",
                    splits=[
                        SplitDef(id="a", title="Part A", scope="first half"),
                        SplitDef(id="b", title="Part B", scope="second half"),
                    ],
                ),
            ),
        },
    )


def make_closeout_output(
    tests_before: int = 100,
    tests_after: int = 100,
    all_pass: bool = True,
) -> str:
    """Create a mock implementation output with structured closeout."""
    closeout = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": "COMPLETE",
        "tests": {"before": tests_before, "after": tests_after, "all_pass": all_pass},
        "files_created": [],
        "files_modified": [],
        "scope_additions": [],
        "scope_gaps": [],
        "prior_session_bugs": [],
        "deferred_observations": [],
        "doc_impacts": [],
        "dec_entries_needed": [],
    }
    return f"""
Implementation completed.

```json:structured-closeout
{json.dumps(closeout, indent=2)}
```
"""


def make_verdict_output(verdict: str = "CLEAR") -> str:
    """Create a mock review output with structured verdict."""
    verdict_data = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": verdict,
        "findings": [],
        "spec_conformance": {"status": "CONFORMANT"},
        "files_reviewed": [],
        "tests_verified": {"all_pass": True},
    }
    return f"""
Review completed.

```json:structured-verdict
{json.dumps(verdict_data, indent=2)}
```
"""


# ---------------------------------------------------------------------------
# Auto-Split Tests
# ---------------------------------------------------------------------------


class TestAutoSplit:
    """Tests for auto-split functionality."""

    def test_handle_auto_split_inserts_sub_sessions(
        self, temp_repo: Path, config_with_auto_split: RunnerConfig
    ) -> None:
        """Auto-split inserts sub-sessions into the session plan."""
        runner = SprintRunner(
            config=config_with_auto_split,
            repo_root=temp_repo,
            dry_run=True,
        )

        # Create initial state
        runner.state = RunState.create_initial(config_with_auto_split)

        # Create a session result indicating compaction
        session = runner.state.session_plan[0]
        session_result = SessionResult(
            compaction_likely=True,
            output_size_bytes=200,
        )
        runner.state.session_results["S1"] = session_result

        # Handle auto-split
        result = runner._handle_auto_split(session, session_result)

        assert result is True
        assert len(runner.state.session_plan) == 3  # S1 (skipped) + S1-a + S1-b
        assert runner.state.session_plan[0].status == SessionPlanStatus.SKIPPED
        assert runner.state.session_plan[1].session_id == "S1-a"
        assert runner.state.session_plan[2].session_id == "S1-b"

    def test_no_auto_split_without_compaction(
        self, temp_repo: Path, config_with_auto_split: RunnerConfig
    ) -> None:
        """No auto-split when compaction_likely is False."""
        runner = SprintRunner(
            config=config_with_auto_split,
            repo_root=temp_repo,
            dry_run=True,
        )

        runner.state = RunState.create_initial(config_with_auto_split)

        session = runner.state.session_plan[0]
        session_result = SessionResult(
            compaction_likely=False,  # No compaction
            output_size_bytes=50,
        )
        runner.state.session_results["S1"] = session_result

        result = runner._handle_auto_split(session, session_result)

        assert result is False
        assert len(runner.state.session_plan) == 1

    def test_no_auto_split_without_config(
        self, temp_repo: Path
    ) -> None:
        """No auto-split when session has no auto_split config."""
        sprint_dir = temp_repo / "docs" / "sprints" / "sprint-23.5"
        sprint_dir.mkdir(parents=True, exist_ok=True)
        (sprint_dir / "sprint-23.5-S1-impl.md").write_text("# S1")
        (sprint_dir / "sprint-23.5-S1-review.md").write_text("# S1 Review")

        config = RunnerConfig(
            sprint=SprintConfig(
                directory=str(sprint_dir),
                session_order=["S1"],
            ),
            execution=ExecutionConfig(
                mode="autonomous",
                compaction_threshold_bytes=100,
            ),
            git=GitConfig(branch="sprint-23.5"),
            triage=TriageConfig(enabled=False),
            conformance=ConformanceConfig(enabled=False),
            # No session_metadata with auto_split
        )

        runner = SprintRunner(
            config=config,
            repo_root=temp_repo,
            dry_run=True,
        )

        runner.state = RunState.create_initial(config)

        session = runner.state.session_plan[0]
        session_result = SessionResult(
            compaction_likely=True,
            output_size_bytes=200,
        )
        runner.state.session_results["S1"] = session_result

        result = runner._handle_auto_split(session, session_result)

        assert result is False
        assert len(runner.state.session_plan) == 1

    def test_insert_auto_split_sessions_creates_correct_files(
        self, temp_repo: Path, config_with_auto_split: RunnerConfig
    ) -> None:
        """Inserted sub-sessions have correct prompt file paths."""
        runner = SprintRunner(
            config=config_with_auto_split,
            repo_root=temp_repo,
            dry_run=True,
        )

        runner.state = RunState.create_initial(config_with_auto_split)

        session = runner.state.session_plan[0]
        splits = config_with_auto_split.session_metadata["S1"].auto_split.splits

        inserted = runner._insert_auto_split_sessions(session, splits)

        assert inserted == ["S1-a", "S1-b"]

        # Check prompt file paths
        s1a = runner.state.session_plan[1]
        assert "S1-a-impl.md" in s1a.prompt_file
        assert "S1-a-review.md" in s1a.review_prompt_file

        s1b = runner.state.session_plan[2]
        assert "S1-b-impl.md" in s1b.prompt_file
        assert "S1-b-review.md" in s1b.review_prompt_file

    def test_sub_sessions_have_correct_dependencies(
        self, temp_repo: Path, config_with_auto_split: RunnerConfig
    ) -> None:
        """Sub-sessions have correct dependency chain."""
        runner = SprintRunner(
            config=config_with_auto_split,
            repo_root=temp_repo,
            dry_run=True,
        )

        runner.state = RunState.create_initial(config_with_auto_split)

        session = runner.state.session_plan[0]
        session_result = SessionResult(compaction_likely=True)
        runner.state.session_results["S1"] = session_result

        runner._handle_auto_split(session, session_result)

        # S1-a depends on nothing (first sub-session)
        s1a = runner.state.session_plan[1]
        assert s1a.depends_on == []

        # S1-b depends on S1 (parent)
        s1b = runner.state.session_plan[2]
        assert "S1" in s1b.depends_on

    def test_split_tracking_in_warnings(
        self, temp_repo: Path, config_with_auto_split: RunnerConfig
    ) -> None:
        """Auto-split events are tracked in warnings."""
        runner = SprintRunner(
            config=config_with_auto_split,
            repo_root=temp_repo,
            dry_run=True,
        )

        runner.state = RunState.create_initial(config_with_auto_split)

        session = runner.state.session_plan[0]
        session_result = SessionResult(compaction_likely=True)
        runner.state.session_results["S1"] = session_result

        runner._handle_auto_split(session, session_result)

        assert len(runner.warnings) == 1
        assert "Auto-split" in runner.warnings[0]
        assert "S1" in runner.warnings[0]
        assert "S1-a" in runner.warnings[0]
        assert "S1-b" in runner.warnings[0]
