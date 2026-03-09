"""Tests for parallel session execution."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.sprint_runner.config import SessionMetadata
from scripts.sprint_runner.parallel import (
    ParallelGroupResult,
    ParallelSessionResult,
    check_dependencies_met,
    find_parallel_group,
    run_parallel_group,
    serialize_git_commits,
)
from scripts.sprint_runner.state import (
    SessionPlanEntry,
    SessionPlanStatus,
    SessionResult,
)


# ---------------------------------------------------------------------------
# find_parallel_group Tests
# ---------------------------------------------------------------------------


class TestFindParallelGroup:
    """Tests for finding parallel groups."""

    def test_finds_parallel_group_with_two_sessions(self) -> None:
        """Find a parallel group with two sessions in the same group."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.COMPLETE,
            ),
            SessionPlanEntry(
                session_id="S2a",
                title="Session 2a",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
                depends_on=["S1"],
            ),
            SessionPlanEntry(
                session_id="S2b",
                title="Session 2b",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
                depends_on=["S1"],
            ),
            SessionPlanEntry(
                session_id="S3",
                title="Session 3",
                status=SessionPlanStatus.PENDING,
                depends_on=["S2a", "S2b"],
            ),
        ]

        session_metadata = {
            "S2a": SessionMetadata(
                title="Session 2a",
                parallelizable=True,
                parallel_group="group-2",
            ),
            "S2b": SessionMetadata(
                title="Session 2b",
                parallelizable=True,
                parallel_group="group-2",
            ),
        }

        session_results: dict[str, SessionResult] = {}

        result = find_parallel_group(session_plan, session_results, session_metadata)

        assert len(result) == 2
        assert {s.session_id for s in result} == {"S2a", "S2b"}

    def test_no_parallel_group_when_deps_not_met(self) -> None:
        """No parallel group found when dependencies are not met."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.PENDING,  # Not complete!
            ),
            SessionPlanEntry(
                session_id="S2a",
                title="Session 2a",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
                depends_on=["S1"],
            ),
            SessionPlanEntry(
                session_id="S2b",
                title="Session 2b",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
                depends_on=["S1"],
            ),
        ]

        session_metadata = {
            "S2a": SessionMetadata(
                title="Session 2a",
                parallelizable=True,
                parallel_group="group-2",
            ),
            "S2b": SessionMetadata(
                title="Session 2b",
                parallelizable=True,
                parallel_group="group-2",
            ),
        }

        result = find_parallel_group(session_plan, {}, session_metadata)

        assert len(result) == 0

    def test_no_parallel_group_without_metadata(self) -> None:
        """No parallel group found without session metadata."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
            ),
            SessionPlanEntry(
                session_id="S2",
                title="Session 2",
                status=SessionPlanStatus.PENDING,
                parallelizable=True,
            ),
        ]

        result = find_parallel_group(session_plan, {}, None)

        assert len(result) == 0


# ---------------------------------------------------------------------------
# run_parallel_group Tests
# ---------------------------------------------------------------------------


class TestRunParallelGroup:
    """Tests for running parallel groups."""

    @pytest.mark.asyncio
    async def test_parallel_execution_via_timing(self) -> None:
        """Verify parallel execution via timing (both sessions run concurrently)."""
        sessions = [
            SessionPlanEntry(
                session_id="S2a",
                title="Session 2a",
                status=SessionPlanStatus.PENDING,
            ),
            SessionPlanEntry(
                session_id="S2b",
                title="Session 2b",
                status=SessionPlanStatus.PENDING,
            ),
        ]

        execution_times: list[tuple[str, float, float]] = []

        async def mock_execute(session: SessionPlanEntry) -> None:
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # 100ms delay
            end = asyncio.get_event_loop().time()
            execution_times.append((session.session_id, start, end))

        # Create mock runner with tracked execution
        mock_runner = MagicMock()
        mock_runner.state = MagicMock()
        mock_runner.state.session_results = {}
        mock_runner.state.sprint = "23.5"
        mock_runner.config = MagicMock()
        mock_runner.config.git = MagicMock()
        mock_runner.config.git.auto_commit = False
        mock_runner.dry_run = True

        # Track whether _execute_session was called concurrently
        call_count = 0
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def tracking_execute(session):
            nonlocal call_count, max_concurrent, current_concurrent
            async with lock:
                call_count += 1
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            await asyncio.sleep(0.05)

            async with lock:
                current_concurrent -= 1

            from scripts.sprint_runner.main import LoopResult
            from scripts.sprint_runner.state import RunStatus
            return LoopResult(status=RunStatus.RUNNING)

        mock_runner._execute_session = tracking_execute

        result = await run_parallel_group(sessions, mock_runner)

        # Verify concurrency
        assert call_count == 2
        assert max_concurrent == 2  # Both running at same time

    @pytest.mark.asyncio
    async def test_one_parallel_session_fails_halts_all(self) -> None:
        """If one parallel session fails, the group halts."""
        sessions = [
            SessionPlanEntry(
                session_id="S2a",
                title="Session 2a",
                status=SessionPlanStatus.PENDING,
            ),
            SessionPlanEntry(
                session_id="S2b",
                title="Session 2b",
                status=SessionPlanStatus.PENDING,
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.state = MagicMock()
        mock_runner.state.session_results = {}
        mock_runner.state.sprint = "23.5"

        call_count = 0

        async def mock_execute(session):
            nonlocal call_count
            call_count += 1
            from scripts.sprint_runner.main import LoopResult
            from scripts.sprint_runner.state import RunStatus
            if session.session_id == "S2a":
                return LoopResult(status=RunStatus.HALTED, halt_reason="Test failure")
            return LoopResult(status=RunStatus.RUNNING)

        mock_runner._execute_session = mock_execute

        result = await run_parallel_group(sessions, mock_runner)

        assert result.all_success is False
        assert result.halt_reason is not None
        assert "S2a" in result.halt_reason or "failure" in result.halt_reason.lower()

    @pytest.mark.asyncio
    async def test_parallel_group_all_succeed(self) -> None:
        """All parallel sessions succeed."""
        sessions = [
            SessionPlanEntry(
                session_id="S2a",
                title="Session 2a",
                status=SessionPlanStatus.PENDING,
            ),
            SessionPlanEntry(
                session_id="S2b",
                title="Session 2b",
                status=SessionPlanStatus.PENDING,
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.state = MagicMock()
        mock_runner.state.session_results = {}
        mock_runner.state.sprint = "23.5"

        async def mock_execute(session):
            from scripts.sprint_runner.main import LoopResult
            from scripts.sprint_runner.state import RunStatus
            return LoopResult(status=RunStatus.RUNNING)

        mock_runner._execute_session = mock_execute

        result = await run_parallel_group(sessions, mock_runner)

        assert result.all_success is True
        assert len(result.results) == 2


# ---------------------------------------------------------------------------
# serialize_git_commits Tests
# ---------------------------------------------------------------------------


class TestSerializeGitCommits:
    """Tests for serializing git commits after parallel execution."""

    def test_commits_in_session_order(self) -> None:
        """Git commits happen in original session order."""
        results = [
            ParallelSessionResult(session_id="S2b", success=True),
            ParallelSessionResult(session_id="S2a", success=True),
        ]

        mock_runner = MagicMock()
        mock_runner.state = MagicMock()
        mock_runner.state.sprint = "23.5"
        mock_runner.state.git_state = MagicMock()
        mock_runner.config = MagicMock()
        mock_runner.config.git = MagicMock()
        mock_runner.config.git.auto_commit = True
        mock_runner.config.git.commit_message_format = "[Sprint {sprint}] Session {session_id}: {title}"
        mock_runner.dry_run = False
        mock_runner.repo_root = "/fake/repo"

        commit_order: list[str] = []

        with patch("scripts.sprint_runner.parallel.commit") as mock_commit:
            def track_commit(msg, cwd):
                # Extract session_id from message
                if "S2a" in msg:
                    commit_order.append("S2a")
                elif "S2b" in msg:
                    commit_order.append("S2b")
                return "sha123"

            mock_commit.side_effect = track_commit

            # Session order: S2a, S2b (alphabetical)
            session_order = ["S2a", "S2b"]
            shas = serialize_git_commits(results, mock_runner, session_order)

        assert commit_order == ["S2a", "S2b"]  # Order matches session_order
        assert len(shas) == 2

    def test_skips_failed_sessions_in_commits(self) -> None:
        """Failed sessions are not committed."""
        results = [
            ParallelSessionResult(session_id="S2a", success=True),
            ParallelSessionResult(session_id="S2b", success=False, halt_reason="Failed"),
        ]

        mock_runner = MagicMock()
        mock_runner.state = MagicMock()
        mock_runner.state.sprint = "23.5"
        mock_runner.state.git_state = MagicMock()
        mock_runner.config = MagicMock()
        mock_runner.config.git = MagicMock()
        mock_runner.config.git.auto_commit = True
        mock_runner.config.git.commit_message_format = "[Sprint {sprint}] {session_id}"
        mock_runner.dry_run = False
        mock_runner.repo_root = "/fake/repo"

        with patch("scripts.sprint_runner.parallel.commit") as mock_commit:
            mock_commit.return_value = "sha123"

            session_order = ["S2a", "S2b"]
            shas = serialize_git_commits(results, mock_runner, session_order)

        # Only one commit (S2a)
        assert mock_commit.call_count == 1
        assert len(shas) == 1


# ---------------------------------------------------------------------------
# check_dependencies_met Tests
# ---------------------------------------------------------------------------


class TestCheckDependenciesMet:
    """Tests for dependency checking."""

    def test_deps_met_when_all_complete(self) -> None:
        """Dependencies are met when all deps are complete."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.COMPLETE,
            ),
            SessionPlanEntry(
                session_id="S2",
                title="Session 2",
                status=SessionPlanStatus.PENDING,
                depends_on=["S1"],
            ),
        ]

        result = check_dependencies_met(session_plan[1], session_plan)
        assert result is True

    def test_deps_met_when_skipped(self) -> None:
        """Dependencies are met when deps are skipped."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.SKIPPED,
            ),
            SessionPlanEntry(
                session_id="S2",
                title="Session 2",
                status=SessionPlanStatus.PENDING,
                depends_on=["S1"],
            ),
        ]

        result = check_dependencies_met(session_plan[1], session_plan)
        assert result is True

    def test_deps_not_met_when_pending(self) -> None:
        """Dependencies not met when deps are pending."""
        session_plan = [
            SessionPlanEntry(
                session_id="S1",
                title="Session 1",
                status=SessionPlanStatus.PENDING,
            ),
            SessionPlanEntry(
                session_id="S2",
                title="Session 2",
                status=SessionPlanStatus.PENDING,
                depends_on=["S1"],
            ),
        ]

        result = check_dependencies_met(session_plan[1], session_plan)
        assert result is False
