"""Parallel session execution for the sprint runner.

Enables concurrent execution of independent sessions within the same
parallel group, while maintaining serialized git commits.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .git_ops import commit

if TYPE_CHECKING:
    from .executor import ClaudeCodeExecutor, StructuredCloseout
    from .main import SprintRunner
    from .state import RunState, SessionPlanEntry, SessionResult


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class ParallelSessionResult:
    """Result of a single session in a parallel group."""

    session_id: str
    success: bool
    halt_reason: str | None = None
    closeout: Any = None
    output: str = ""
    session_result: Any = None


@dataclass
class ParallelGroupResult:
    """Result of executing a parallel group."""

    all_success: bool
    results: list[ParallelSessionResult] = field(default_factory=list)
    halt_reason: str | None = None


# ---------------------------------------------------------------------------
# Parallel Group Detection
# ---------------------------------------------------------------------------


def find_parallel_group(
    session_plan: list[SessionPlanEntry],
    session_results: dict[str, SessionResult],
    session_metadata: dict[str, Any] | None,
) -> list[SessionPlanEntry]:
    """Find sessions that can run in parallel.

    Sessions can run in parallel if:
    1. They share the same parallel_group
    2. They have parallelizable=True
    3. All their dependencies are met (completed or skipped)

    Args:
        session_plan: The full session plan.
        session_results: Results of completed sessions.
        session_metadata: Session metadata with parallel_group info.

    Returns:
        List of sessions that can run in parallel. Empty if none found.
    """
    from .state import SessionPlanStatus

    if not session_metadata:
        return []

    # Find all pending sessions with their parallel groups
    pending_by_group: dict[str, list[SessionPlanEntry]] = {}

    for session in session_plan:
        if session.status != SessionPlanStatus.PENDING:
            continue

        # Check if parallelizable
        if not session.parallelizable:
            continue

        # Get parallel_group from metadata
        meta = session_metadata.get(session.session_id)
        if not meta or not meta.parallel_group:
            continue

        # Check dependencies met
        deps_met = True
        for dep in session.depends_on:
            # Find dependency in session plan
            dep_session = next(
                (s for s in session_plan if s.session_id == dep), None
            )
            if dep_session is None:
                deps_met = False
                break
            if dep_session.status not in (
                SessionPlanStatus.COMPLETE,
                SessionPlanStatus.SKIPPED,
            ):
                deps_met = False
                break

        if not deps_met:
            continue

        # Group by parallel_group
        group = meta.parallel_group
        if group not in pending_by_group:
            pending_by_group[group] = []
        pending_by_group[group].append(session)

    # Return the first group with multiple sessions
    for group_sessions in pending_by_group.values():
        if len(group_sessions) >= 2:
            return group_sessions

    return []


def check_dependencies_met(
    session: SessionPlanEntry,
    session_plan: list[SessionPlanEntry],
) -> bool:
    """Check if all dependencies for a session are met.

    Args:
        session: The session to check.
        session_plan: The full session plan.

    Returns:
        True if all dependencies are complete or skipped.
    """
    from .state import SessionPlanStatus

    for dep in session.depends_on:
        dep_session = next(
            (s for s in session_plan if s.session_id == dep), None
        )
        if dep_session is None:
            return False
        if dep_session.status not in (
            SessionPlanStatus.COMPLETE,
            SessionPlanStatus.SKIPPED,
        ):
            return False

    return True


# ---------------------------------------------------------------------------
# Parallel Execution
# ---------------------------------------------------------------------------


async def run_parallel_group(
    sessions: list[SessionPlanEntry],
    runner: SprintRunner,
) -> ParallelGroupResult:
    """Execute sessions in parallel, serializing git commits after completion.

    Each session runs its full execution pipeline concurrently. After all
    parallel sessions complete, git commits are applied serially in session
    order. If any session fails (ESCALATE or HALT), all results are saved
    but the run halts.

    Args:
        sessions: List of sessions to execute in parallel.
        runner: The SprintRunner instance.

    Returns:
        ParallelGroupResult with combined results.
    """
    from .state import RunStatus, SessionPlanStatus

    # Execute all sessions concurrently
    tasks = [
        _execute_session_parallel(session, runner)
        for session in sessions
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    parallel_results: list[ParallelSessionResult] = []
    all_success = True
    first_halt_reason = None

    for i, result in enumerate(results):
        session = sessions[i]

        if isinstance(result, Exception):
            parallel_results.append(
                ParallelSessionResult(
                    session_id=session.session_id,
                    success=False,
                    halt_reason=str(result),
                )
            )
            all_success = False
            if first_halt_reason is None:
                first_halt_reason = f"Session {session.session_id}: {result}"
        elif result.success:
            parallel_results.append(result)
        else:
            parallel_results.append(result)
            all_success = False
            if first_halt_reason is None:
                first_halt_reason = result.halt_reason

    return ParallelGroupResult(
        all_success=all_success,
        results=parallel_results,
        halt_reason=first_halt_reason,
    )


async def _execute_session_parallel(
    session: SessionPlanEntry,
    runner: SprintRunner,
) -> ParallelSessionResult:
    """Execute a single session as part of a parallel group.

    This runs the session's implementation and review phases without
    committing to git. Git commits are handled after all parallel
    sessions complete.

    Args:
        session: The session to execute.
        runner: The SprintRunner instance.

    Returns:
        ParallelSessionResult for this session.
    """
    from .state import RunStatus

    # Execute the session through the runner's pipeline
    # This returns a LoopResult
    loop_result = await runner._execute_session(session)

    return ParallelSessionResult(
        session_id=session.session_id,
        success=loop_result.status != RunStatus.HALTED,
        halt_reason=loop_result.halt_reason,
        session_result=runner.state.session_results.get(session.session_id)
        if runner.state
        else None,
    )


def serialize_git_commits(
    results: list[ParallelSessionResult],
    runner: SprintRunner,
    session_order: list[str],
) -> list[str]:
    """Commit changes for parallel sessions in deterministic order.

    Git commits must be serialized to maintain a linear history.
    Commits are made in the original session order.

    Args:
        results: Results from parallel execution.
        runner: The SprintRunner instance.
        session_order: Original session order for deterministic commits.

    Returns:
        List of commit SHAs in order.
    """
    commit_shas: list[str] = []

    # Sort results by original session order
    result_map = {r.session_id: r for r in results}
    ordered_results = [
        result_map[sid] for sid in session_order if sid in result_map
    ]

    for result in ordered_results:
        if result.success:
            message = runner.config.git.commit_message_format.format(
                sprint=runner.state.sprint if runner.state else "",
                session_id=result.session_id,
                title=result.session_id,
            )
            if runner.config.git.auto_commit and not runner.dry_run:
                sha = commit(message, cwd=runner.repo_root)
                commit_shas.append(sha)
                if runner.state:
                    runner.state.git_state.current_sha = sha

    return commit_shas
