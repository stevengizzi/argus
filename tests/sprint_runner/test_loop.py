"""Tests for the sprint runner execution loop."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.sprint_runner.config import (
    ConformanceConfig,
    CostConfig,
    CostRates,
    ExecutionConfig,
    GitConfig,
    NotificationsConfig,
    RunLogConfig,
    RunnerConfig,
    SprintConfig,
    TriageConfig,
)
from scripts.sprint_runner.executor import ExecutionResult
from scripts.sprint_runner.main import CLOSEOUT_PLACEHOLDER, SprintRunner
from scripts.sprint_runner.state import RunState, RunStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_closeout_output(
    tests_before: int = 100,
    tests_after: int = 115,
    all_pass: bool = True,
    files_created: list[str] | None = None,
    files_modified: list[str] | None = None,
) -> str:
    """Create a mock implementation output with structured closeout."""
    closeout = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": "COMPLETE",
        "tests": {"before": tests_before, "after": tests_after, "all_pass": all_pass},
        "files_created": files_created or [],
        "files_modified": files_modified or [],
        "scope_additions": [],
        "scope_gaps": [],
        "prior_session_bugs": [],
        "deferred_observations": [],
        "doc_impacts": [],
        "dec_entries_needed": [],
    }
    return f"""
Implementation completed successfully.

Some prose output here.

```json:structured-closeout
{json.dumps(closeout, indent=2)}
```
"""


def make_verdict_output(
    verdict: str = "CLEAR",
    spec_conformance_status: str = "CONFORMANT",
) -> str:
    """Create a mock review output with structured verdict."""
    verdict_data = {
        "schema_version": "1.0",
        "sprint": "23.5",
        "session": "S1",
        "verdict": verdict,
        "findings": [],
        "spec_conformance": {"status": spec_conformance_status},
        "files_reviewed": ["file.py"],
        "tests_verified": {"all_pass": True, "count": 115},
    }
    return f"""
Review completed.

```json:structured-verdict
{json.dumps(verdict_data, indent=2)}
```
"""


@contextlib.contextmanager
def mock_git_ops(diff_files_return: list[str] | None = None):
    """Context manager that mocks all git operations."""
    with patch("scripts.sprint_runner.main.verify_branch", return_value=True), \
         patch("scripts.sprint_runner.main.is_clean", return_value=True), \
         patch("scripts.sprint_runner.main.get_sha", return_value="abc123"), \
         patch("scripts.sprint_runner.main.checkpoint", return_value="abc123"), \
         patch("scripts.sprint_runner.main.rollback"), \
         patch("scripts.sprint_runner.main.diff_files", return_value=diff_files_return or []), \
         patch("scripts.sprint_runner.main.diff_full", return_value=""), \
         patch("scripts.sprint_runner.main.commit", return_value="def456"), \
         patch("scripts.sprint_runner.main.compute_file_hash", return_value="hash123"):
        yield


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
    (sprint_dir / "sprint-23.5-S1-review.md").write_text("# S1 Review\n[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]")
    (sprint_dir / "sprint-23.5-S2-impl.md").write_text("# S2 Implementation\n{{TEST_BASELINE}}")
    (sprint_dir / "sprint-23.5-S2-review.md").write_text("# S2 Review")
    (sprint_dir / "sprint-23.5-S3-impl.md").write_text("# S3 Implementation\n{{TEST_BASELINE}}")
    (sprint_dir / "sprint-23.5-S3-review.md").write_text("# S3 Review")
    (sprint_dir / "review-context.md").write_text("# Review Context")

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
            review_context_file=str(sprint_dir / "review-context.md"),
        ),
        execution=ExecutionConfig(
            mode="autonomous",
            max_retries=2,
            retry_delay_seconds=1,
            test_count_tolerance=0,
            compaction_threshold_bytes=100000,
        ),
        git=GitConfig(
            branch="sprint-23.5",
            auto_commit=True,
            commit_message_format="[Sprint {sprint}] Session {session_id}: {title}",
        ),
        notifications=NotificationsConfig(),
        cost=CostConfig(
            ceiling_usd=50.0,
            rates=CostRates(
                input_per_million=3.0,
                output_per_million=15.0,
            ),
        ),
        run_log=RunLogConfig(base_directory=""),
        # Disable triage and conformance for tests (no templates available)
        triage=TriageConfig(enabled=False),
        conformance=ConformanceConfig(enabled=False),
        protected_files=[],
    )


# ---------------------------------------------------------------------------
# Happy Path Tests
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Tests for successful execution paths."""

    @pytest.mark.asyncio
    async def test_three_sessions_all_clear_completes(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Happy path: 3 sessions, all CLEAR → COMPLETED."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_before=100, tests_after=115)
        review_output = make_verdict_output(verdict="CLEAR")

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ] * 3,
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            side_effect=[
                (100, True), (100, True), (115, True),
                (115, True), (115, True),
                (115, True), (115, True),
            ],
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.COMPLETED
        assert result.sessions_completed == 3

    @pytest.mark.asyncio
    async def test_state_transitions_not_started_to_completed(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """State transitions: NOT_STARTED → RUNNING → COMPLETED."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ] * 3,
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            assert not runner.state_file.exists()
            result = await runner.run()
            assert runner.state_file.exists()
            state = RunState.load(runner.state_file)
            assert state.status == RunStatus.COMPLETED


# ---------------------------------------------------------------------------
# Halt Tests
# ---------------------------------------------------------------------------


class TestHaltConditions:
    """Tests for halt conditions."""

    @pytest.mark.asyncio
    async def test_escalate_in_session_2_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """ESCALATE in session 2 → HALTED at session 2."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        clear_review = make_verdict_output(verdict="CLEAR")
        escalate_review = make_verdict_output(verdict="ESCALATE")

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=clear_review, exit_code=0, duration_seconds=5, output_size_bytes=500),
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=escalate_review, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "escalated" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_concerns_in_session_2_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """CONCERNS in session 2 → HALTED (triage placeholder halts)."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        clear_review = make_verdict_output(verdict="CLEAR")
        concerns_review = make_verdict_output(verdict="CONCERNS")

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=clear_review, exit_code=0, duration_seconds=5, output_size_bytes=500),
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=concerns_review, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "concerns" in result.halt_reason.lower() or "triage" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_preflight_missing_file_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Pre-flight catches missing file → HALTED."""
        prompt_file = temp_repo / "docs" / "sprints" / "sprint-23.5" / "sprint-23.5-S1-impl.md"
        prompt_file.unlink()

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        with patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "not found" in result.halt_reason.lower() or "prompt" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_protected_file_violation_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Protected file violation in diff → HALTED."""
        runner_config.protected_files = ["CLAUDE.md"]

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100, files_modified=["CLAUDE.md"])
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
        ), mock_git_ops(diff_files_return=["CLAUDE.md"]):
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "protected" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_independent_test_verification_mismatch_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Independent test verification mismatch → HALTED."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(all_pass=True)

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            return_value=ExecutionResult(
                output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000
            ),
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            side_effect=[
                (100, True),  # Startup
                (100, True),  # Preflight
                (100, False),  # Independent verify - fails!
            ],
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "verification" in result.halt_reason.lower() or "mismatch" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_cost_ceiling_exceeded_halts(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Cost ceiling exceeded → HALTED."""
        runner_config.cost.ceiling_usd = 0.001

        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "cost" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_stop_after_halts_with_manual_pause(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--stop-after S2 → HALTED after S2 with 'Manual pause' reason."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            stop_after="S2",
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ] * 2,
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "pause" in result.halt_reason.lower()
        assert result.sessions_completed == 2


# ---------------------------------------------------------------------------
# Test Baseline Tests
# ---------------------------------------------------------------------------


class TestTestBaseline:
    """Tests for test baseline patching."""

    @pytest.mark.asyncio
    async def test_test_baseline_patched_between_sessions(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Test baseline patched between sessions (2101 → 2116 → 2131)."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        prompts_sent: list[str] = []

        async def capture_prompt(prompt: str, **kwargs) -> ExecutionResult:
            prompts_sent.append(prompt)
            if "review" in prompt.lower() or CLOSEOUT_PLACEHOLDER not in prompt:
                return ExecutionResult(
                    output=make_verdict_output(),
                    exit_code=0,
                    duration_seconds=5,
                    output_size_bytes=500,
                )
            idx = len([p for p in prompts_sent if "{{TEST_BASELINE}}" not in p and "review" not in p.lower()]) - 1
            tests_after = [2116, 2131, 2146][min(idx, 2)]
            return ExecutionResult(
                output=make_closeout_output(tests_after=tests_after),
                exit_code=0,
                duration_seconds=10,
                output_size_bytes=1000,
            )

        test_counts = [2101, 2101, 2116, 2116, 2131, 2131, 2146]
        test_idx = [0]

        def mock_tests(*args, **kwargs):
            result = (test_counts[min(test_idx[0], len(test_counts) - 1)], True)
            test_idx[0] += 1
            return result

        with patch.object(
            runner.executor, "run_session", new_callable=AsyncMock, side_effect=capture_prompt
        ), patch("scripts.sprint_runner.main.run_tests", side_effect=mock_tests), mock_git_ops():
            result = await runner.run()

        impl_prompts = [p for p in prompts_sent if "{{TEST_BASELINE}}" not in p and "# S" in p and "Review" not in p]
        assert len(impl_prompts) >= 1


# ---------------------------------------------------------------------------
# Run Log Tests
# ---------------------------------------------------------------------------


class TestRunLog:
    """Tests for run-log file creation."""

    @pytest.mark.asyncio
    async def test_run_log_files_created_correctly(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Run-log files created in correct directory structure."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ] * 3,
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        s1_log_dir = temp_repo / "run-log" / "S1"
        assert s1_log_dir.exists()
        assert (s1_log_dir / "implementation-output.md").exists()
        assert (s1_log_dir / "closeout-structured.json").exists()
        assert (s1_log_dir / "closeout-report.md").exists()
        assert (s1_log_dir / "review-output.md").exists()
        assert (s1_log_dir / "review-verdict.json").exists()
        assert (s1_log_dir / "git-diff.patch").exists()

    @pytest.mark.asyncio
    async def test_atomic_state_writes(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """State persisted atomically after each session."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            stop_after="S1",
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
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
            await runner.run()

        assert runner.state_file.exists()
        state = RunState.load(runner.state_file)
        assert state.session_results.get("S1") is not None


# ---------------------------------------------------------------------------
# State Transition Tests
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Tests for state transitions."""

    @pytest.mark.asyncio
    async def test_state_halted_on_failure(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """State transitions: NOT_STARTED → RUNNING → HALTED."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
        escalate_review = make_verdict_output(verdict="ESCALATE")

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=escalate_review, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        state = RunState.load(runner.state_file)
        assert state.status == RunStatus.HALTED


# ---------------------------------------------------------------------------
# Retry Tests
# ---------------------------------------------------------------------------


class TestRetryBehavior:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_closeout_retry_on_transient_failure(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """Close-out retry on transient failure (mock first call fails, second succeeds)."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            stop_after="S1",
            dry_run=True,
        )

        no_closeout_output = "Some output without structured closeout"
        good_impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        with patch.object(
            runner.executor,
            "run_session",
            new_callable=AsyncMock,
            side_effect=[
                ExecutionResult(output=no_closeout_output, exit_code=0, duration_seconds=10, output_size_bytes=100),
                ExecutionResult(output=good_impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000),
                ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500),
            ],
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            result = await runner.run()

        assert result.status == RunStatus.HALTED
        assert "pause" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_llm_compliance_retry_prepends_reinforcement(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """LLM-compliance retry prepends reinforcement instruction."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            stop_after="S1",
            dry_run=True,
        )

        llm_compliance_output = """
Some implementation work done.

---BEGIN-CLOSE-OUT---
Implementation completed successfully.
---END-CLOSE-OUT---

But no JSON block!
"""
        good_impl_output = make_closeout_output(tests_after=100)
        review_output = make_verdict_output()

        prompts_seen: list[str] = []

        async def track_prompts(prompt: str, **kwargs) -> ExecutionResult:
            prompts_seen.append(prompt)
            if len(prompts_seen) == 1:
                return ExecutionResult(output=llm_compliance_output, exit_code=0, duration_seconds=10, output_size_bytes=100)
            elif len(prompts_seen) == 2:
                return ExecutionResult(output=good_impl_output, exit_code=0, duration_seconds=10, output_size_bytes=1000)
            else:
                return ExecutionResult(output=review_output, exit_code=0, duration_seconds=5, output_size_bytes=500)

        with patch.object(
            runner.executor, "run_session", new_callable=AsyncMock, side_effect=track_prompts
        ), patch(
            "scripts.sprint_runner.main.run_tests",
            return_value=(100, True),
        ), mock_git_ops():
            await runner.run()

        assert len(prompts_seen) >= 2
        assert "IMPORTANT" in prompts_seen[1]
        assert "structured close-out JSON" in prompts_seen[1]


# ---------------------------------------------------------------------------
# Pause Flag Test
# ---------------------------------------------------------------------------


class TestPauseFlag:
    """Tests for --pause flag."""

    @pytest.mark.asyncio
    async def test_pause_flag_halts_after_first_session(
        self, temp_repo: Path, runner_config: RunnerConfig
    ) -> None:
        """--pause flag halts after first session completes."""
        runner = SprintRunner(
            config=runner_config,
            repo_root=temp_repo,
            pause=True,
            dry_run=True,
        )

        impl_output = make_closeout_output(tests_after=100)
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
