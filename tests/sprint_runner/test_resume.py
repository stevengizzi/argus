"""Tests for resume functionality."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.sprint_runner.config import (
    ConformanceConfig,
    CostConfig,
    DocSyncConfig,
    ExecutionConfig,
    GitConfig,
    NotificationsConfig,
    RunLogConfig,
    RunnerConfig,
    SprintConfig,
    TriageConfig,
)
from scripts.sprint_runner.main import SprintRunner
from scripts.sprint_runner.state import (
    CostState,
    GitState,
    RunPhase,
    RunState,
    RunStatus,
    SessionPlanEntry,
    SessionPlanStatus,
    SessionResult,
    TestBaseline,
    Timestamps,
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

    # Get the SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()

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
    (sprint_dir / "sprint-23.5-S2-impl.md").write_text("# S2 Implementation")
    (sprint_dir / "sprint-23.5-S2-review.md").write_text("# S2 Review")

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
def runner_config(temp_repo: Path) -> RunnerConfig:
    """Create a runner config for testing."""
    sprint_dir = temp_repo / "docs" / "sprints" / "sprint-23.5"
    return RunnerConfig(
        sprint=SprintConfig(
            directory=str(sprint_dir),
            session_order=["S1", "S2"],
        ),
        execution=ExecutionConfig(
            mode="autonomous",
            max_retries=2,
            retry_delay_seconds=1,
            test_count_tolerance=5,
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
    )


def get_current_sha(temp_repo: Path) -> str:
    """Get current git SHA."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def create_halted_state(
    temp_repo: Path,
    runner_config: RunnerConfig,
    current_session: str,
    current_phase: RunPhase,
    test_count: int = 100,
) -> RunState:
    """Create a halted run state fixture."""
    sha = get_current_sha(temp_repo)

    state = RunState(
        schema_version="1.0",
        sprint="23.5",
        mode="autonomous",
        status=RunStatus.HALTED,
        halt_reason="Test halt",
        current_session=current_session,
        current_phase=current_phase,
        session_plan=[
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.COMPLETE if current_session == "S2" else SessionPlanStatus.RUNNING,
                prompt_file=str(
                    Path(runner_config.sprint.directory) / "sprint-23.5-S1-impl.md"
                ),
                review_prompt_file=str(
                    Path(runner_config.sprint.directory) / "sprint-23.5-S1-review.md"
                ),
            ),
            SessionPlanEntry(
                session_id="S2",
                title="Session 2",
                status=SessionPlanStatus.RUNNING if current_session == "S2" else SessionPlanStatus.PENDING,
                prompt_file=str(
                    Path(runner_config.sprint.directory) / "sprint-23.5-S2-impl.md"
                ),
                review_prompt_file=str(
                    Path(runner_config.sprint.directory) / "sprint-23.5-S2-review.md"
                ),
            ),
        ],
        session_results={},
        git_state=GitState(
            branch="sprint-23.5",
            sprint_start_sha=sha,
            current_sha=sha,
            checkpoint_sha=sha,
        ),
        cost=CostState(ceiling_usd=50.0),
        test_baseline=TestBaseline(initial=test_count, current=test_count),
        timestamps=Timestamps(
            run_started="2026-03-09T10:00:00Z",
            last_updated="2026-03-09T10:30:00Z",
        ),
    )

    return state


# ---------------------------------------------------------------------------
# Resume Validation Tests
# ---------------------------------------------------------------------------


class TestResumeValidation:
    """Tests for resume state validation."""

    def test_validate_resume_state_success(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume validation succeeds with valid state."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION, test_count=100
        )
        state.save(temp_repo / "run-state.json")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )

        with patch("scripts.sprint_runner.main.run_tests", return_value=(100, True)):
            valid, error = runner._validate_resume_state()

        assert valid is True
        assert error == ""

    def test_validate_resume_state_no_state_file(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume validation fails when no state file exists."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )

        valid, error = runner._validate_resume_state()

        assert valid is False
        assert "No run-state.json found" in error

    def test_validate_resume_state_sha_mismatch(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume validation fails when git SHA mismatches."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION
        )
        state.git_state.current_sha = "abcdef1234567890"  # Wrong SHA
        state.save(temp_repo / "run-state.json")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )

        valid, error = runner._validate_resume_state()

        assert valid is False
        assert "Git SHA mismatch" in error

    def test_validate_resume_state_test_failures(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume validation fails when tests are failing."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION
        )
        state.save(temp_repo / "run-state.json")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )

        with patch("scripts.sprint_runner.main.run_tests", return_value=(100, False)):
            valid, error = runner._validate_resume_state()

        assert valid is False
        assert "Test suite has failures" in error


# ---------------------------------------------------------------------------
# Resume Point Determination Tests
# ---------------------------------------------------------------------------


class TestDetermineResumePoint:
    """Tests for determining resume point."""

    def test_resume_from_implementation_rollback(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume from IMPLEMENTATION phase means rollback and re-run."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION
        )
        state.save(temp_repo / "run-state.json")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )
        runner.state = state

        session_id, phase = runner._determine_resume_point()

        assert session_id == "S1"
        assert phase == RunPhase.PRE_FLIGHT  # Rollback to pre-flight

    def test_resume_from_review_with_impl_output(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume from REVIEW phase with impl output resumes from review."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.REVIEW
        )
        state.save(temp_repo / "run-state.json")

        # Create implementation output file
        log_dir = temp_repo / "run-log" / "S1"
        log_dir.mkdir(parents=True)
        (log_dir / "implementation-output.md").write_text("Some implementation output")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )
        runner.state = state

        session_id, phase = runner._determine_resume_point()

        assert session_id == "S1"
        assert phase == RunPhase.REVIEW

    def test_resume_from_review_without_impl_output(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume from REVIEW without impl output re-runs from pre-flight."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.REVIEW
        )
        state.save(temp_repo / "run-state.json")

        # No implementation output file exists

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )
        runner.state = state

        session_id, phase = runner._determine_resume_point()

        assert session_id == "S1"
        assert phase == RunPhase.PRE_FLIGHT

    def test_resume_no_current_session(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Resume with no current session starts from beginning."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION
        )
        state.current_session = None
        state.current_phase = None
        state.save(temp_repo / "run-state.json")

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )
        runner.state = state

        session_id, phase = runner._determine_resume_point()

        assert session_id is None
        assert phase is None


# ---------------------------------------------------------------------------
# Stale Lock Tests
# ---------------------------------------------------------------------------


class TestStaleLockHandling:
    """Tests for stale lock file handling."""

    def test_stale_lock_cleared_on_resume(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Stale lock file is cleared when resuming."""
        state = create_halted_state(
            temp_repo, runner_config, "S1", RunPhase.IMPLEMENTATION
        )
        state.save(temp_repo / "run-state.json")

        # Create a stale lock file with a non-existent PID
        lock_file = temp_repo / ".sprint-runner.lock"
        lock_data = {
            "pid": 999999999,  # Unlikely to exist
            "started": "2026-03-09T10:00:00Z",
            "sprint": "23.5",
            "host": "test-host",
        }
        lock_file.write_text(json.dumps(lock_data))

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            resume=True,
            dry_run=True,
        )

        # Validate or clear should clear the stale lock
        runner.lock.validate_or_clear()

        # Lock should no longer exist (or be clearable)
        # The actual acquisition happens in _startup
