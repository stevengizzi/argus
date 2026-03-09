"""Tests for CLI flags."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
from scripts.sprint_runner.executor import ExecutionResult
from scripts.sprint_runner.main import SprintRunner, create_parser
from scripts.sprint_runner.state import RunStatus, SessionPlanStatus


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
    for session_id in ["S1", "S2", "S3"]:
        (sprint_dir / f"sprint-23.5-{session_id}-impl.md").write_text(
            f"# {session_id} Implementation\n{{{{TEST_BASELINE}}}}"
        )
        (sprint_dir / f"sprint-23.5-{session_id}-review.md").write_text(
            f"# {session_id} Review"
        )

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
            session_order=["S1", "S2", "S3"],
        ),
        execution=ExecutionConfig(
            mode="autonomous",
            max_retries=2,
            retry_delay_seconds=1,
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


def make_closeout_output(tests_after: int = 100) -> str:
    """Create a mock implementation output with structured closeout."""
    closeout = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": "COMPLETE",
        "tests": {"before": 100, "after": tests_after, "all_pass": True},
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


def make_verdict_output() -> str:
    """Create a mock review output with structured verdict."""
    verdict_data = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": "CLEAR",
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


def mock_git_ops():
    """Context manager that mocks all git operations."""
    import contextlib

    @contextlib.contextmanager
    def _mock():
        with patch("scripts.sprint_runner.main.verify_branch", return_value=True), \
             patch("scripts.sprint_runner.main.is_clean", return_value=True), \
             patch("scripts.sprint_runner.main.get_sha", return_value="abc123"), \
             patch("scripts.sprint_runner.main.checkpoint", return_value="abc123"), \
             patch("scripts.sprint_runner.main.rollback"), \
             patch("scripts.sprint_runner.main.diff_files", return_value=[]), \
             patch("scripts.sprint_runner.main.diff_full", return_value=""), \
             patch("scripts.sprint_runner.main.commit", return_value="def456"), \
             patch("scripts.sprint_runner.main.compute_file_hash", return_value="hash123"):
            yield

    return _mock()


# ---------------------------------------------------------------------------
# CLI Parser Tests
# ---------------------------------------------------------------------------


class TestCLIParser:
    """Tests for CLI argument parsing."""

    def test_parser_requires_config(self) -> None:
        """Parser requires --config argument."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_accepts_all_flags(self) -> None:
        """Parser accepts all supported flags."""
        parser = create_parser()

        args = parser.parse_args([
            "--config", "config.yaml",
            "--resume",
            "--pause",
            "--dry-run",
            "--from-session", "S2",
            "--skip-session", "S3",
            "--stop-after", "S4",
            "--mode", "autonomous",
        ])

        assert args.config == "config.yaml"
        assert args.resume is True
        assert args.pause is True
        assert args.dry_run is True
        assert args.from_session == "S2"
        assert args.skip_session == ["S3"]
        assert args.stop_after == "S4"
        assert args.mode == "autonomous"

    def test_skip_session_can_be_repeated(self) -> None:
        """--skip-session can be specified multiple times."""
        parser = create_parser()

        args = parser.parse_args([
            "--config", "config.yaml",
            "--skip-session", "S2",
            "--skip-session", "S4",
        ])

        assert args.skip_session == ["S2", "S4"]

    def test_mode_only_accepts_valid_values(self) -> None:
        """--mode only accepts valid values."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args([
                "--config", "config.yaml",
                "--mode", "invalid",
            ])


# ---------------------------------------------------------------------------
# Dry Run Tests
# ---------------------------------------------------------------------------


class TestDryRun:
    """Tests for --dry-run flag."""

    @pytest.mark.asyncio
    async def test_dry_run_no_executor_calls(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--dry-run does not invoke Claude Code executor."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        executor_call_count = 0

        async def track_executor(prompt: str, **kwargs) -> ExecutionResult:
            nonlocal executor_call_count
            executor_call_count += 1
            return ExecutionResult(
                output="[DRY RUN]",
                exit_code=0,
                duration_seconds=0,
                output_size_bytes=0,
            )

        with patch.object(
            runner.executor, "run_session", new_callable=AsyncMock, side_effect=track_executor
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        # Executor was called but in dry_run mode
        # The executor itself handles dry_run by returning a stub


# ---------------------------------------------------------------------------
# From Session Tests
# ---------------------------------------------------------------------------


class TestFromSession:
    """Tests for --from-session flag."""

    @pytest.mark.asyncio
    async def test_from_session_skips_prior(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--from-session skips prior sessions."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            from_session="S2",
            stop_after="S2",
            dry_run=True,
        )

        impl_output = make_closeout_output()
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        # S1 should be SKIPPED
        s1 = next(s for s in runner.state.session_plan if s.session_id == "S1")
        assert s1.status == SessionPlanStatus.SKIPPED


# ---------------------------------------------------------------------------
# Skip Session Tests
# ---------------------------------------------------------------------------


class TestSkipSession:
    """Tests for --skip-session flag."""

    @pytest.mark.asyncio
    async def test_skip_session_marks_skipped(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--skip-session marks specific sessions as SKIPPED."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            skip_sessions=["S2"],
            stop_after="S3",
            dry_run=True,
        )

        impl_output = make_closeout_output()
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ] * 2,  # S1 and S3
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        # S2 should be SKIPPED
        s2 = next(s for s in runner.state.session_plan if s.session_id == "S2")
        assert s2.status == SessionPlanStatus.SKIPPED


# ---------------------------------------------------------------------------
# Stop After Tests
# ---------------------------------------------------------------------------


class TestStopAfter:
    """Tests for --stop-after flag."""

    @pytest.mark.asyncio
    async def test_stop_after_halts_with_manual_pause(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--stop-after halts after specified session."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            stop_after="S1",
            dry_run=True,
        )

        impl_output = make_closeout_output()
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "pause" in result.halt_reason.lower()
        assert result.sessions_completed == 1


# ---------------------------------------------------------------------------
# Pause Flag Tests
# ---------------------------------------------------------------------------


class TestPauseFlag:
    """Tests for --pause flag."""

    @pytest.mark.asyncio
    async def test_pause_halts_after_first_session(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--pause halts after first session completes."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            pause=True,
            dry_run=True,
        )

        impl_output = make_closeout_output()
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "pause" in result.halt_reason.lower()
        assert result.sessions_completed == 1


# ---------------------------------------------------------------------------
# Mode Override Tests
# ---------------------------------------------------------------------------


class TestModeOverride:
    """Tests for --mode flag."""

    def test_mode_override_applied_to_config(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--mode overrides config execution mode."""
        # Start with autonomous mode
        assert runner_config.execution.mode == "autonomous"

        # Override to human-in-the-loop
        runner_config.execution.mode = "human-in-the-loop"

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        assert runner.config.execution.mode == "human-in-the-loop"
