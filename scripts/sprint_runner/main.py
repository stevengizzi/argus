"""CLI entry point and execution loop for the sprint runner.

Implements the full execution state machine that drives sprint sessions
via Claude Code CLI invocations.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .cli import (
    Colors,
    build_argument_parser,
    print_error,
    print_header,
    print_progress,
    print_success,
    print_summary_table,
    print_warning,
)
from .config import RunnerConfig
from .conformance import ConformanceChecker
from .cost import CostTracker
from .executor import (
    ClaudeCodeExecutor,
    StructuredCloseout,
    StructuredVerdict,
    prepend_reinforcement_instruction,
)
from .git_ops import (
    FileValidationError,
    checkpoint,
    commit,
    compute_file_hash,
    diff_files,
    diff_full,
    get_sha,
    is_clean,
    rollback,
    run_tests,
    validate_pre_session_files,
    validate_protected_files,
    verify_branch,
)
from .lock import LockError, LockFile
from .notifications import NotificationData, NotificationManager
from .parallel import find_parallel_group, run_parallel_group
from .state import (
    ConformanceVerdict as ConformanceVerdictEnum,
)
from .state import (
    RunPhase,
    RunState,
    RunStatus,
    SessionPlanEntry,
    SessionPlanStatus,
    SessionResult,
)
from .triage import TriageManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


TEST_BASELINE_PLACEHOLDER = "{{TEST_BASELINE}}"
CLOSEOUT_PLACEHOLDER = "[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]"


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class LoopResult:
    """Result of the execution loop."""

    status: RunStatus
    halt_reason: str | None = None
    sessions_completed: int = 0
    warnings: list[str] | None = None


# ---------------------------------------------------------------------------
# Execution Loop
# ---------------------------------------------------------------------------


class SprintRunner:
    """The sprint runner orchestrator.

    Implements the full execution loop: startup → session loop → completion.
    """

    def __init__(
        self,
        config: RunnerConfig,
        repo_root: Path,
        resume: bool = False,
        pause: bool = False,
        stop_after: str | None = None,
        dry_run: bool = False,
        from_session: str | None = None,
        skip_sessions: list[str] | None = None,
    ) -> None:
        """Initialize the sprint runner.

        Args:
            config: Runner configuration.
            repo_root: Path to the repository root.
            resume: Whether resuming from existing state.
            pause: Whether to pause after current session.
            stop_after: Session ID to stop after.
            dry_run: Dry run mode (no executor calls).
            from_session: Session ID to start from.
            skip_sessions: Session IDs to skip.
        """
        self.config = config
        self.repo_root = repo_root
        self.resume = resume
        self.pause = pause
        self.stop_after = stop_after
        self.dry_run = dry_run
        self.from_session = from_session
        self.skip_sessions = skip_sessions or []

        self.lock = LockFile(repo_root)
        self.executor = ClaudeCodeExecutor(config.execution)
        self.state: RunState | None = None
        self.warnings: list[str] = []

        # Run log paths
        base_dir = config.run_log.base_directory
        self.run_log_base = Path(base_dir) if base_dir else repo_root

        # Notification manager
        self.notifications = NotificationManager(config.notifications)

        # Triage manager
        self.triage_manager = TriageManager(self.executor, config.triage, repo_root)

        # Conformance checker
        self.conformance_checker = ConformanceChecker(
            self.executor, config.conformance, repo_root
        )

        # Cost tracker
        self.cost_tracker = CostTracker(config.cost)

        # Sprint directory for loading spec files
        self.sprint_dir = Path(config.sprint.directory)

    @property
    def state_file(self) -> Path:
        """Path to the run state file."""
        return self.repo_root / "run-state.json"

    def _get_session_log_dir(self, session_id: str) -> Path:
        """Get the run-log directory for a session."""
        return self.run_log_base / "run-log" / session_id

    def _save_to_run_log(self, session_id: str, filename: str, content: str) -> None:
        """Save content to the run log directory.

        Args:
            session_id: The session ID.
            filename: The filename to save.
            content: The content to write.
        """
        log_dir = self._get_session_log_dir(session_id)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / filename).write_text(content)

    def _save_closeout_json(self, session_id: str, closeout: StructuredCloseout) -> None:
        """Save structured closeout JSON to run log."""
        log_dir = self._get_session_log_dir(session_id)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "closeout-structured.json").write_text(
            json.dumps(closeout.raw, indent=2)
        )

    def _save_verdict_json(self, session_id: str, verdict: StructuredVerdict) -> None:
        """Save structured verdict JSON to run log."""
        log_dir = self._get_session_log_dir(session_id)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "review-verdict.json").write_text(json.dumps(verdict.raw, indent=2))

    def _patch_test_baseline(self, prompt: str, baseline: int) -> str:
        """Patch test baseline into prompt.

        Args:
            prompt: The prompt content.
            baseline: Current test baseline count.

        Returns:
            Patched prompt with baseline inserted.
        """
        return prompt.replace(TEST_BASELINE_PLACEHOLDER, str(baseline))

    def _extract_closeout_markdown(self, output: str) -> str:
        """Extract the human-readable close-out report before the JSON block.

        Args:
            output: Full session output.

        Returns:
            The close-out report markdown portion.
        """
        marker = "```json:structured-closeout"
        idx = output.find(marker)
        if idx > 0:
            return output[:idx].strip()
        return output

    async def run(self) -> LoopResult:
        """Execute the sprint runner loop.

        Returns:
            LoopResult with final status and any halt reason.
        """
        # Dry run header
        if self.dry_run:
            print_header("DRY RUN MODE")
            print("No Claude Code CLI calls will be made.\n", flush=True)

        # Resume validation
        if self.resume:
            valid, error = self._validate_resume_state()
            if not valid:
                print_error(error)
                return LoopResult(status=RunStatus.HALTED, halt_reason=error)

        # Startup sequence
        try:
            self._startup()
        except (LockError, FileValidationError) as e:
            print_error(str(e))
            return LoopResult(status=RunStatus.HALTED, halt_reason=str(e))

        assert self.state is not None

        # Print session plan
        total_sessions = len(self.state.session_plan)
        print_header(f"Sprint {self.state.sprint} - {total_sessions} Sessions")
        for i, s in enumerate(self.state.session_plan):
            status = "PENDING" if s.status == SessionPlanStatus.PENDING else str(s.status)
            print_progress(i + 1, total_sessions, s.session_id, status)
        print(flush=True)

        # Initial test baseline
        if self.state.status == RunStatus.NOT_STARTED:
            print(f"{Colors.DIM}Running initial test baseline...{Colors.RESET}", flush=True)
            test_count, all_pass = run_tests(
                "python -m pytest tests/ -x -q",
                cwd=self.repo_root,
            )
            if not all_pass:
                self._halt("Test suite has failures at startup")
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason="Test suite has failures at startup",
                )
            self.state.test_baseline.initial = test_count
            self.state.test_baseline.current = test_count
            self.state.status = RunStatus.RUNNING
            self.state.git_state.sprint_start_sha = get_sha(cwd=self.repo_root)
            self.state.git_state.current_sha = self.state.git_state.sprint_start_sha
            self.state.save(self.state_file)
            print(f"{Colors.GREEN}Baseline: {test_count} tests passing{Colors.RESET}\n", flush=True)

        # Validate skip-session dependencies before entering loop
        skip_result = self._validate_skip_dependencies()
        if skip_result.status == RunStatus.HALTED:
            return skip_result

        sessions_completed = 0
        processed_sessions: set[str] = set()

        # Session loop
        i = 0
        while i < len(self.state.session_plan):
            session = self.state.session_plan[i]

            if session.status in (SessionPlanStatus.COMPLETE, SessionPlanStatus.SKIPPED):
                sessions_completed += 1
                i += 1
                continue

            # Handle --from-session: skip and mark prior sessions
            if self.from_session and session.session_id != self.from_session:
                if session.status == SessionPlanStatus.PENDING:
                    session.status = SessionPlanStatus.SKIPPED
                    self.state.save(self.state_file)
                    print_progress(
                        i + 1, total_sessions, session.session_id, "SKIPPED"
                    )
                    i += 1
                    continue
            elif self.from_session and session.session_id == self.from_session:
                self.from_session = None  # Found it, process from here

            # Handle --skip-session
            if session.session_id in self.skip_sessions:
                session.status = SessionPlanStatus.SKIPPED
                self.state.save(self.state_file)
                print_progress(i + 1, total_sessions, session.session_id, "SKIPPED")
                i += 1
                continue

            # Check for parallel group
            parallel_sessions = find_parallel_group(
                self.state.session_plan,
                self.state.session_results,
                self.config.session_metadata,
            )

            if parallel_sessions and len(parallel_sessions) >= 2:
                # Filter to sessions not yet processed
                parallel_sessions = [
                    s for s in parallel_sessions
                    if s.session_id not in processed_sessions
                ]

                if len(parallel_sessions) >= 2:
                    result = await self._handle_parallel_sessions(parallel_sessions)

                    if result.status == RunStatus.HALTED:
                        self._print_run_summary()
                        return result

                    for ps in parallel_sessions:
                        processed_sessions.add(ps.session_id)
                        sessions_completed += 1

                    # Skip to next unprocessed session
                    while i < len(self.state.session_plan):
                        if self.state.session_plan[i].session_id in processed_sessions:
                            i += 1
                        else:
                            break
                    continue

            # Print progress
            print_progress(i + 1, total_sessions, session.session_id, "RUNNING")

            # Execute session
            result = await self._execute_session(session)
            processed_sessions.add(session.session_id)

            if result.status == RunStatus.HALTED:
                # Check if auto-split applies
                session_result = self.state.session_results.get(session.session_id)
                if session_result and self._handle_auto_split(session, session_result):
                    # Auto-split inserted sub-sessions, rollback and re-execute
                    if self.state.git_state.checkpoint_sha:
                        rollback(self.state.git_state.checkpoint_sha, cwd=self.repo_root)
                    # Re-scan from current position (sub-sessions were inserted)
                    total_sessions = len(self.state.session_plan)
                    continue

                print_progress(i + 1, total_sessions, session.session_id, "FAILED")
                self._print_run_summary()
                return result

            print_progress(i + 1, total_sessions, session.session_id, "COMPLETE")
            sessions_completed += 1
            i += 1

            # Check --stop-after
            if self.stop_after and session.session_id == self.stop_after:
                self._halt("Manual pause requested")
                self._print_run_summary()
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason="Manual pause requested",
                    sessions_completed=sessions_completed,
                    warnings=self.warnings if self.warnings else None,
                )

            # Check --pause
            if self.pause:
                self._halt("Manual pause requested")
                self._print_run_summary()
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason="Manual pause requested",
                    sessions_completed=sessions_completed,
                    warnings=self.warnings if self.warnings else None,
                )

        # Post-loop: run doc sync
        await self._run_doc_sync()

        # Post-loop: set final status
        if self.warnings:
            self.state.status = RunStatus.COMPLETED_WITH_WARNINGS
            self.state.issues_count.warnings = len(self.warnings)
        else:
            self.state.status = RunStatus.COMPLETED

        self.state.timestamps.run_completed = datetime.now(UTC).isoformat()
        self.state.save(self.state_file)
        self.lock.release()

        # Send sprint completion notification
        self._send_completed_notification(sessions_completed)

        # Check conformance fallback threshold
        self._check_conformance_fallback_warning()

        # Print summary
        self._print_run_summary()
        print_success(f"Sprint completed with {sessions_completed} sessions")

        return LoopResult(
            status=self.state.status,
            sessions_completed=sessions_completed,
            warnings=self.warnings if self.warnings else None,
        )

    def _startup(self) -> None:
        """Startup sequence: lock, load/create state, verify git.

        Raises:
            LockError: If lock cannot be acquired.
            GitStateError: If git state is invalid.
        """
        sprint_number = Path(self.config.sprint.directory).name.replace("sprint-", "")

        # Check/acquire lock
        if self.resume:
            self.lock.validate_or_clear()
        self.lock.acquire(sprint_number)

        # Load or create state
        if self.state_file.exists():
            self.state = RunState.load(self.state_file)
        else:
            self.state = RunState.create_initial(self.config)
            self.state.save(self.state_file)

        # Verify git branch
        if not verify_branch(self.config.git.branch, cwd=self.repo_root):
            raise LockError(
                f"Not on expected branch '{self.config.git.branch}'"
            )

        # Verify clean state
        if not is_clean(cwd=self.repo_root):
            raise LockError("Git working directory has uncommitted changes")

    def _halt(self, reason: str) -> None:
        """Handle halt condition.

        Args:
            reason: The halt reason.
        """
        if self.state is None:
            return

        self.state.status = RunStatus.HALTED
        self.state.halt_reason = reason
        self.state.save(self.state_file)

        # Save patch if uncommitted changes
        if not is_clean(cwd=self.repo_root):
            patch = diff_full(cwd=self.repo_root)
            if patch and self.state.current_session:
                self._save_to_run_log(self.state.current_session, "uncommitted.patch", patch)
            # Rollback to checkpoint
            if self.state.git_state.checkpoint_sha:
                rollback(self.state.git_state.checkpoint_sha, cwd=self.repo_root)

        self.lock.release()

        # Check conformance fallback threshold
        self._check_conformance_fallback_warning()

        # Send HALTED notification
        self._send_halted_notification(reason)

    def _validate_skip_dependencies(self) -> LoopResult:
        """Validate that skipped sessions don't break dependencies.

        Checks that no non-skipped session depends on a skipped session,
        unless the skipped session is already COMPLETED.

        Returns:
            LoopResult (RUNNING to continue, HALTED if dependency is unsatisfied).
        """
        if not self.skip_sessions or self.state is None:
            return LoopResult(status=RunStatus.RUNNING)

        skip_set = set(self.skip_sessions)

        # Build map of session statuses for quick lookup
        session_status: dict[str, SessionPlanStatus] = {}
        for session in self.state.session_plan:
            session_status[session.session_id] = session.status

        # Check each non-skipped session's dependencies
        for session in self.state.session_plan:
            if session.session_id in skip_set:
                continue  # This session is being skipped, skip checking it

            for dep_id in session.depends_on:
                if dep_id in skip_set:
                    # Dependency is being skipped - check if it's already complete
                    dep_status = session_status.get(dep_id)
                    if dep_status != SessionPlanStatus.COMPLETE:
                        reason = (
                            f"Session {session.session_id} depends on {dep_id}, "
                            f"which is being skipped but is not COMPLETE "
                            f"(status: {dep_status})"
                        )
                        self._halt(reason)
                        return LoopResult(status=RunStatus.HALTED, halt_reason=reason)

        return LoopResult(status=RunStatus.RUNNING)

    async def _execute_session(self, session: SessionPlanEntry) -> LoopResult:
        """Execute a single session through the full pipeline.

        Args:
            session: The session to execute.

        Returns:
            LoopResult with status (continue or halt).
        """
        assert self.state is not None

        session_id = session.session_id
        self.state.current_session = session_id
        session.status = SessionPlanStatus.RUNNING
        self.state.save(self.state_file)

        # Initialize session result
        if session_id not in self.state.session_results:
            self.state.session_results[session_id] = SessionResult()
        session_result = self.state.session_results[session_id]

        # Step 1: Pre-flight
        self.state.current_phase = RunPhase.PRE_FLIGHT
        self.state.save(self.state_file)

        preflight_result = await self._preflight(session, session_result)
        if preflight_result.status == RunStatus.HALTED:
            return preflight_result

        # Step 2: Git checkpoint
        checkpoint_sha = checkpoint(cwd=self.repo_root)
        self.state.git_state.checkpoint_sha = checkpoint_sha
        session_result.git_sha_before = checkpoint_sha
        self.state.save(self.state_file)

        # Step 3: Implementation
        self.state.current_phase = RunPhase.IMPLEMENTATION
        self.state.save(self.state_file)
        self._send_phase_transition("Implementation started", f"Session {session_id}")

        impl_result = await self._run_implementation(session, session_result)
        if impl_result is None:
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Implementation failed for {session_id}",
            )

        output, closeout = impl_result
        self._send_phase_transition(
            "Implementation complete", "Extracting close-out and verifying tests"
        )

        # Step 4b: Independent test verification (DEC-291)
        self.state.current_phase = RunPhase.CLOSEOUT_PARSE
        self.state.save(self.state_file)

        verify_result = self._verify_tests_independently(closeout, session_result)
        if verify_result.status == RunStatus.HALTED:
            return verify_result

        # Step 4c: Diff validation (DEC-294)
        diff_result = self._validate_diff(session_id, closeout)
        if diff_result.status == RunStatus.HALTED:
            return diff_result

        # Step 5: Review
        self.state.current_phase = RunPhase.REVIEW
        self.state.save(self.state_file)

        review_result = await self._run_review(session, output)
        if review_result is None:
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Review failed for {session_id}",
            )

        verdict = review_result
        self._send_phase_transition(
            "Review complete", f"Verdict: {verdict.verdict}"
        )

        # Step 6: Verdict extraction done in _run_review

        # Step 7: Decision gate (including triage for CONCERNS)
        self.state.current_phase = RunPhase.VERDICT_PARSE
        self.state.save(self.state_file)

        decision_result = await self._decision_gate(
            verdict, closeout, session, session_result
        )
        if decision_result.status == RunStatus.HALTED:
            return decision_result

        # Step 8: Cost check (now using CostTracker)
        cost_result = self._check_cost(session_result, output)
        if cost_result.status == RunStatus.HALTED:
            return cost_result

        # Step 9: Conformance check (after CLEAR/resolved verdict)
        self.state.current_phase = RunPhase.CONFORMANCE_CHECK
        self.state.save(self.state_file)

        conformance_result = await self._run_conformance_check(
            session, closeout, session_result
        )
        if conformance_result.status == RunStatus.HALTED:
            return conformance_result

        # Git commit (after CLEAR + CONFORMANT)
        self.state.current_phase = RunPhase.GIT_COMMIT
        self.state.save(self.state_file)

        if self.config.git.auto_commit and not self.dry_run:
            message = self.config.git.commit_message_format.format(
                sprint=self.state.sprint,
                session_id=session_id,
                title=session.title or session_id,
            )
            new_sha = commit(message, cwd=self.repo_root)
            session_result.git_sha_after = new_sha
            self.state.git_state.current_sha = new_sha

        # State update
        session.status = SessionPlanStatus.COMPLETE
        session_result.review_verdict = verdict.verdict  # type: ignore
        self.state.current_phase = RunPhase.COMPLETE
        new_baseline = session_result.tests_after or self.state.test_baseline.current
        self.state.test_baseline.current = new_baseline
        self.state.save(self.state_file)

        # Send session complete notification
        self._send_session_complete_notification(session, session_result)

        return LoopResult(status=RunStatus.RUNNING, sessions_completed=1)

    async def _preflight(
        self, session: SessionPlanEntry, session_result: SessionResult
    ) -> LoopResult:
        """Pre-flight checks for a session.

        Args:
            session: The session entry.
            session_result: The session result to populate.

        Returns:
            LoopResult (RUNNING to continue, HALTED on failure).
        """
        assert self.state is not None

        # Dynamic test baseline from previous session
        expected_tests = self.state.test_baseline.current

        # Run tests
        actual_tests, all_pass = run_tests("python -m pytest tests/ -x -q", cwd=self.repo_root)

        if not all_pass:
            self._halt("Test suite has failures before session start")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason="Test suite has failures before session start",
            )

        tolerance = self.config.execution.test_count_tolerance
        if abs(actual_tests - expected_tests) > tolerance:
            self._halt(
                f"Test baseline mismatch: expected {expected_tests}, got {actual_tests}"
            )
            reason = f"Test baseline mismatch: expected {expected_tests}, got {actual_tests}"
            return LoopResult(status=RunStatus.HALTED, halt_reason=reason)

        session_result.tests_before = actual_tests

        # Verify git state
        current_sha = get_sha(cwd=self.repo_root)
        if current_sha != self.state.git_state.current_sha:
            self._halt(
                f"Git state diverged. Expected {self.state.git_state.current_sha}, "
                f"found {current_sha}"
            )
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason="Git state diverged from run-state",
            )

        if not is_clean(cwd=self.repo_root):
            self._halt("Git working directory has uncommitted changes")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason="Git has uncommitted changes",
            )

        # Pre-session file validation (DEC-292)
        # Collect files from prior sessions' creates
        prior_creates: list[str] = []
        for prior_session_id, _prior_result in self.state.session_results.items():
            if prior_session_id == session.session_id:
                break
            # Files from prior sessions would be tracked in closeout data
            # For now, this is a placeholder - actual implementation would
            # parse closeout data stored in session results

        if prior_creates:
            try:
                validate_pre_session_files(prior_creates, cwd=self.repo_root)
            except FileValidationError as e:
                self._halt(f"Pre-session file validation failed: {e}")
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason=f"Pre-session file validation failed: {e}",
                )

        # Verify prompt file exists
        if session.prompt_file:
            prompt_path = Path(session.prompt_file)
            if not prompt_path.exists():
                self._halt(f"Prompt file not found: {session.prompt_file}")
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason=f"Prompt file not found: {session.prompt_file}",
                )

        # Review context hash verification (DEC-297)
        if self.config.sprint.review_context_file:
            try:
                current_hash = compute_file_hash(
                    self.config.sprint.review_context_file, cwd=self.repo_root
                )
                if self.state.review_context_hash is None:
                    self.state.review_context_hash = current_hash
                    self.state.save(self.state_file)
                elif current_hash != self.state.review_context_hash:
                    self.warnings.append(
                        "Review context file has changed since sprint start"
                    )
            except FileValidationError:
                # Review context file optional
                pass

        return LoopResult(status=RunStatus.RUNNING)

    async def _run_implementation(
        self, session: SessionPlanEntry, session_result: SessionResult
    ) -> tuple[str, StructuredCloseout] | None:
        """Run implementation phase with retry logic.

        Args:
            session: The session entry.
            session_result: The session result to populate.

        Returns:
            Tuple of (output, closeout) on success, None on failure.
        """
        assert self.state is not None

        if not session.prompt_file:
            self._halt(f"No prompt file for session {session.session_id}")
            return None

        prompt = Path(session.prompt_file).read_text()
        prompt = self._patch_test_baseline(prompt, self.state.test_baseline.current)

        max_retries = self.config.execution.max_retries

        for attempt in range(max_retries + 1):
            result = await self.executor.run_session(prompt, dry_run=self.dry_run)

            # Save output immediately
            self._save_to_run_log(session.session_id, "implementation-output.md", result.output)

            session_result.output_size_bytes = result.output_size_bytes
            session_result.compaction_likely = result.compaction_likely
            session_result.duration_seconds = int(result.duration_seconds)

            if result.compaction_likely:
                size = result.output_size_bytes
                msg = f"Session {session.session_id} output is {size} bytes — compaction likely"
                self.warnings.append(msg)

            # Try to extract closeout
            try:
                closeout = self.executor.extract_structured_closeout(result.output)
            except Exception as e:
                closeout = None
                self.warnings.append(f"Closeout extraction error: {e}")

            if closeout is not None:
                self._save_closeout_json(session.session_id, closeout)
                closeout_md = self._extract_closeout_markdown(result.output)
                self._save_to_run_log(session.session_id, "closeout-report.md", closeout_md)
                return (result.output, closeout)

            # Classify failure
            failure_type = self.executor.classify_failure(result.output)
            session_result.retries = attempt + 1
            session_result.retry_reasons.append(failure_type)

            if attempt < max_retries:
                # Rollback to checkpoint before retry
                if self.state.git_state.checkpoint_sha:
                    rollback(self.state.git_state.checkpoint_sha, cwd=self.repo_root)

                if failure_type == "llm_compliance":
                    prompt = prepend_reinforcement_instruction(prompt)

                # Exponential backoff delay
                delay = self.config.execution.retry_delay_seconds * (4**attempt)
                await asyncio.sleep(delay)
            else:
                if failure_type == "llm_compliance":
                    self._halt(
                        f"Implementation may be complete but structured output missing after "
                        f"{max_retries} retries. Review saved output manually."
                    )
                else:
                    self._halt(f"No output after {max_retries} retries")
                return None

        return None

    def _verify_tests_independently(
        self, closeout: StructuredCloseout, session_result: SessionResult
    ) -> LoopResult:
        """Independent test verification (DEC-291).

        Args:
            closeout: The extracted closeout.
            session_result: The session result to populate.

        Returns:
            LoopResult (RUNNING to continue, HALTED on mismatch).
        """
        actual_tests, actual_all_pass = run_tests(
            "python -m pytest tests/ -x -q", cwd=self.repo_root
        )
        session_result.tests_after = actual_tests

        closeout_all_pass = closeout.tests.get("all_pass", True)
        closeout_after = closeout.tests.get("after", actual_tests)

        if actual_all_pass != closeout_all_pass:
            self._halt(
                f"Close-out claims all_pass={closeout_all_pass} but "
                f"independent verification shows all_pass={actual_all_pass}"
            )
            reason = (
                f"Test verification mismatch: claimed all_pass={closeout_all_pass}, "
                f"actual={actual_all_pass}"
            )
            return LoopResult(status=RunStatus.HALTED, halt_reason=reason)

        tolerance = self.config.execution.test_count_tolerance
        if abs(actual_tests - closeout_after) > tolerance:
            self._halt(
                f"Close-out claims {closeout_after} tests but "
                f"independent verification found {actual_tests}"
            )
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Test count mismatch: claimed {closeout_after}, actual {actual_tests}",
            )

        return LoopResult(status=RunStatus.RUNNING)

    def _validate_diff(self, session_id: str, closeout: StructuredCloseout) -> LoopResult:
        """Diff validation (DEC-294).

        Args:
            session_id: The session ID.
            closeout: The extracted closeout.

        Returns:
            LoopResult (RUNNING to continue, HALTED on violation).
        """
        changed_files = diff_files(cwd=self.repo_root)

        # Check protected files
        protected = self.config.protected_files or []
        violations = validate_protected_files(changed_files, protected)

        if violations:
            self._halt(f"Protected files modified: {violations}")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Protected files modified: {violations}",
            )

        # Check expected creates against actual diff
        expected_creates = closeout.files_created
        missing_creates = [f for f in expected_creates if f not in changed_files]
        if missing_creates:
            self.warnings.append(f"Expected files not in diff: {missing_creates}")

        # Save diff as patch
        patch = diff_full(cwd=self.repo_root)
        self._save_to_run_log(session_id, "git-diff.patch", patch)

        return LoopResult(status=RunStatus.RUNNING)

    async def _run_review(
        self, session: SessionPlanEntry, impl_output: str
    ) -> StructuredVerdict | None:
        """Run review phase.

        Args:
            session: The session entry.
            impl_output: The implementation output.

        Returns:
            StructuredVerdict on success, None on failure.
        """
        if not session.review_prompt_file:
            # Create a minimal verdict if no review prompt
            return StructuredVerdict(
                schema_version="1.0",
                sprint=self.state.sprint if self.state else "",
                session=session.session_id,
                verdict="CLEAR",
                findings=[],
                spec_conformance={"status": "CONFORMANT"},
                files_reviewed=[],
                tests_verified={"all_pass": True},
                raw={
                    "schema_version": "1.0",
                    "sprint": self.state.sprint if self.state else "",
                    "session": session.session_id,
                    "verdict": "CLEAR",
                    "findings": [],
                    "spec_conformance": {"status": "CONFORMANT"},
                    "files_reviewed": [],
                    "tests_verified": {"all_pass": True},
                },
            )

        review_prompt_path = Path(session.review_prompt_file)
        if not review_prompt_path.exists():
            self._halt(f"Review prompt file not found: {session.review_prompt_file}")
            return None

        review_prompt = review_prompt_path.read_text()

        # Inject closeout report into placeholder
        closeout_md = self._extract_closeout_markdown(impl_output)
        review_prompt = review_prompt.replace(CLOSEOUT_PLACEHOLDER, closeout_md)

        result = await self.executor.run_session(review_prompt, dry_run=self.dry_run)
        self._save_to_run_log(session.session_id, "review-output.md", result.output)

        try:
            verdict = self.executor.extract_structured_verdict(result.output)
        except Exception as e:
            self._halt(f"Failed to extract review verdict: {e}")
            return None

        if verdict is None:
            # Fallback: attempt to extract verdict from prose
            verdict = self._extract_prose_verdict(result.output, session)
            if verdict is None:
                msg = "Review output missing structured verdict (no JSON block or prose found)"
                self._halt(msg)
                return None

        self._save_verdict_json(session.session_id, verdict)
        return verdict

    def _extract_prose_verdict(
        self, output: str, session: SessionPlanEntry
    ) -> StructuredVerdict | None:
        """Fallback: extract verdict from prose when JSON block is missing.

        Searches for patterns like "**Verdict:** CONCERNS" or "Verdict: CLEAR"
        in the review output.

        Args:
            output: The full review output text.
            session: The session being reviewed.

        Returns:
            StructuredVerdict if a verdict keyword is found, None otherwise.
        """
        # Pattern matches "Verdict:" with optional bold markers, followed by verdict keyword
        prose_verdict_pattern = re.compile(
            r'\*?\*?[Vv]erdict\*?\*?\s*[:\s]+\s*(CLEAR|CONCERNS|ESCALATE)',
            re.IGNORECASE,
        )
        match = prose_verdict_pattern.search(output)
        if not match:
            return None

        verdict_str = match.group(1).upper()
        self.warnings.append(
            f"Review verdict extracted from prose (no JSON block): {verdict_str}"
        )

        return StructuredVerdict(
            schema_version="1.0",
            sprint=self.state.sprint if self.state else "",
            session=session.session_id,
            verdict=verdict_str,
            findings=[],
            spec_conformance={"status": "UNKNOWN", "note": "Parsed from prose, no structured data"},
            files_reviewed=[],
            tests_verified={"all_pass": True, "note": "Not verified, parsed from prose"},
            raw={
                "schema_version": "1.0",
                "sprint": self.state.sprint if self.state else "",
                "session": session.session_id,
                "verdict": verdict_str,
                "findings": [],
                "spec_conformance": {"status": "UNKNOWN", "note": "Parsed from prose"},
                "files_reviewed": [],
                "tests_verified": {"all_pass": True},
                "_parsed_from_prose": True,
            },
        )

    async def _decision_gate(
        self,
        verdict: StructuredVerdict,
        closeout: StructuredCloseout,
        session: SessionPlanEntry,
        session_result: SessionResult,
    ) -> LoopResult:
        """Decision gate (Step 7) with triage integration.

        Args:
            verdict: The review verdict.
            closeout: The structured closeout.
            session: The session entry.
            session_result: The session result.

        Returns:
            LoopResult (RUNNING to proceed, HALTED on escalate).
        """
        assert self.state is not None

        # Automatic escalation checks
        spec_conformance = verdict.spec_conformance
        if isinstance(spec_conformance, dict):
            status = spec_conformance.get("status", "")
            if status == "MAJOR_DEVIATION":
                self._halt("Major spec deviation detected")
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason="Major spec deviation detected",
                )

        # Check findings for files_not_modified or regression_checklist failures
        for finding in verdict.findings:
            if isinstance(finding, dict):
                if finding.get("type") == "files_not_modified" and not finding.get("passed", True):
                    self._halt("Files modified that should not have been")
                    return LoopResult(
                        status=RunStatus.HALTED,
                        halt_reason="Files modified that should not have been",
                    )
                is_regr_checklist = finding.get("type") == "regression_checklist"
                if is_regr_checklist and not finding.get("all_passed", True):
                    self._halt("Regression checklist failed")
                    return LoopResult(
                        status=RunStatus.HALTED,
                        halt_reason="Regression checklist failed",
                    )

        # Verdict-based routing
        if verdict.verdict == "ESCALATE":
            self._halt("Review escalated")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason="Review escalated",
            )

        # Check if triage is needed
        needs_triage = False
        triage_reason = ""

        if verdict.verdict == "CONCERNS":
            needs_triage = True
            triage_reason = "CONCERNS verdict"
        elif verdict.verdict == "CLEAR":
            # Check for scope_gaps or prior_session_bugs in closeout
            if closeout.scope_gaps:
                needs_triage = True
                triage_reason = "scope_gaps in closeout"
            elif closeout.prior_session_bugs:
                needs_triage = True
                triage_reason = "prior_session_bugs in closeout"

        if needs_triage:
            if not self.config.triage.enabled:
                # Triage disabled but concerns exist — halt
                self._halt(f"Concerns detected ({triage_reason}) but triage is disabled")
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason=f"Concerns detected ({triage_reason}) but triage is disabled",
                )

            # Check max auto-fixes limit
            if self.triage_manager.check_max_auto_fixes_exceeded():
                self._halt(
                    f"Max auto-fixes ({self.config.triage.max_auto_fixes}) exceeded"
                )
                return LoopResult(
                    status=RunStatus.HALTED,
                    halt_reason="Max auto-fixes exceeded",
                )

            # Run triage
            self.state.current_phase = RunPhase.TRIAGE
            self.state.save(self.state_file)
            self._send_phase_transition("Triage", f"Running triage ({triage_reason})")

            triage_result = await self._run_triage(
                closeout, verdict, session, session_result
            )
            if triage_result.status == RunStatus.HALTED:
                return triage_result

        # CLEAR (or resolved) — proceed
        return LoopResult(status=RunStatus.RUNNING)

    async def _run_triage(
        self,
        closeout: StructuredCloseout,
        verdict: StructuredVerdict,
        session: SessionPlanEntry,
        session_result: SessionResult,
    ) -> LoopResult:
        """Run Tier 2.5 triage.

        Args:
            closeout: The structured closeout.
            verdict: The review verdict.
            session: The session entry.
            session_result: The session result.

        Returns:
            LoopResult based on triage recommendation.
        """
        assert self.state is not None

        # Load sprint spec files
        sprint_spec = self._load_sprint_spec()
        spec_by_contradiction = self._load_spec_by_contradiction()
        session_breakdown = self._load_session_breakdown()

        # Get next/dependent sessions
        next_sessions = self._get_next_sessions(session.session_id)
        dependent_sessions = self._get_dependent_sessions(session.session_id)

        triage_verdict = await self.triage_manager.run_triage(
            closeout=closeout.raw,
            verdict=verdict.raw if verdict else None,
            sprint_spec=sprint_spec,
            spec_by_contradiction=spec_by_contradiction,
            session_breakdown=session_breakdown,
            sprint=self.state.sprint,
            session=session.session_id,
            next_sessions=next_sessions,
            dependent_sessions=dependent_sessions,
        )

        # Save triage verdict
        self._save_to_run_log(
            session.session_id,
            "triage-verdict.json",
            json.dumps(triage_verdict.raw, indent=2),
        )
        session_result.triage_verdict = triage_verdict.overall_recommendation

        # Route on recommendation
        if triage_verdict.overall_recommendation == "HALT":
            self._halt("Triage recommended HALT")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason="Triage recommended HALT",
            )

        if triage_verdict.overall_recommendation == "INSERT_FIXES_THEN_PROCEED":
            if self.config.triage.auto_insert_fixes:
                # Insert fix sessions
                inserted = self.triage_manager.insert_fix_sessions(
                    triage_verdict,
                    self.state,
                    session.session_id,
                    self.sprint_dir,
                )
                session_result.fix_sessions_inserted = inserted
                self.state.issues_count.fix_sessions_inserted += len(inserted)
                self.state.save(self.state_file)

                if inserted:
                    self.warnings.append(
                        f"Inserted fix sessions: {', '.join(inserted)}"
                    )

        # PROCEED or INSERT_FIXES_THEN_PROCEED (after insertion)
        return LoopResult(status=RunStatus.RUNNING)

    def _load_sprint_spec(self) -> str:
        """Load sprint spec content."""
        spec_path = self.sprint_dir / "sprint-spec.md"
        if spec_path.exists():
            return spec_path.read_text()
        return "(sprint spec not found)"

    def _load_spec_by_contradiction(self) -> str:
        """Load spec-by-contradiction content."""
        spec_path = self.sprint_dir / "spec-by-contradiction.md"
        if spec_path.exists():
            return spec_path.read_text()
        return "(spec-by-contradiction not found)"

    def _load_session_breakdown(self) -> str:
        """Load session breakdown content."""
        breakdown_path = self.sprint_dir / "session-breakdown.md"
        if breakdown_path.exists():
            return breakdown_path.read_text()
        return "(session breakdown not found)"

    def _get_next_sessions(self, current_session_id: str) -> list[str]:
        """Get list of sessions after the current one."""
        if self.state is None:
            return []

        found = False
        next_sessions = []
        for session in self.state.session_plan:
            if found:
                next_sessions.append(session.session_id)
            if session.session_id == current_session_id:
                found = True
        return next_sessions

    def _get_dependent_sessions(self, current_session_id: str) -> list[str]:
        """Get list of sessions that depend on the current one."""
        if self.state is None:
            return []

        dependent = []
        for session in self.state.session_plan:
            if current_session_id in session.depends_on:
                dependent.append(session.session_id)
        return dependent

    def _check_cost(self, session_result: SessionResult, output: str) -> LoopResult:
        """Cost check (Step 8) using CostTracker.

        Args:
            session_result: The session result.
            output: The session output string.

        Returns:
            LoopResult (RUNNING to continue, HALTED if ceiling exceeded).
        """
        assert self.state is not None

        # Update cost tracking using CostTracker
        self.cost_tracker.update(
            session_id=self.state.current_session or "",
            output=output,
            run_state=self.state,
        )

        # Check ceiling
        if self.cost_tracker.check_ceiling(self.state):
            cost = self.state.cost.total_cost_estimate_usd
            ceiling = self.state.cost.ceiling_usd
            self._halt(f"Cost ceiling exceeded: ${cost:.2f} > ${ceiling:.2f}")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Cost ceiling exceeded: ${cost:.2f}",
            )

        return LoopResult(status=RunStatus.RUNNING)

    async def _run_conformance_check(
        self,
        session: SessionPlanEntry,
        closeout: StructuredCloseout,
        session_result: SessionResult,
    ) -> LoopResult:
        """Run spec conformance check (Step 9).

        Args:
            session: The session entry.
            closeout: The structured closeout.
            session_result: The session result.

        Returns:
            LoopResult (RUNNING to continue, HALTED on DRIFT-MAJOR).
        """
        assert self.state is not None

        if not self.config.conformance.enabled:
            return LoopResult(status=RunStatus.RUNNING)

        self._send_phase_transition("Conformance check", "Verifying spec alignment")

        # Load sprint spec files
        sprint_spec = self._load_sprint_spec()
        spec_by_contradiction = self._load_spec_by_contradiction()
        session_breakdown = self._load_session_breakdown()

        # Get completed sessions
        completed_sessions = [
            s.session_id
            for s in self.state.session_plan
            if s.status == SessionPlanStatus.COMPLETE
        ]
        completed_sessions.append(session.session_id)

        # Get cumulative files
        cumulative_created = self._get_cumulative_files_created()
        cumulative_modified = self._get_cumulative_files_modified()

        # Get cumulative diff from sprint start
        cumulative_diff = self._get_cumulative_diff()

        conformance_verdict = await self.conformance_checker.check(
            sprint_spec=sprint_spec,
            spec_by_contradiction=spec_by_contradiction,
            session_breakdown=session_breakdown,
            completed_sessions=completed_sessions,
            cumulative_files_created=cumulative_created,
            cumulative_files_modified=cumulative_modified,
            cumulative_diff=cumulative_diff,
            current_closeout=closeout.raw,
            sprint=self.state.sprint,
            session=session.session_id,
        )

        # Save conformance verdict
        self._save_to_run_log(
            session.session_id,
            "conformance-verdict.json",
            json.dumps(conformance_verdict.raw, indent=2),
        )

        # Track fallback usage
        if conformance_verdict.is_fallback:
            self.state.conformance_fallback_count += 1
            self.state.save(self.state_file)

        # Map verdict to enum
        if conformance_verdict.verdict == "CONFORMANT":
            session_result.conformance_verdict = ConformanceVerdictEnum.CONFORMANT
        elif conformance_verdict.verdict == "DRIFT-MINOR":
            session_result.conformance_verdict = ConformanceVerdictEnum.DRIFT_MINOR
            self.warnings.append(
                f"Conformance: DRIFT-MINOR - {conformance_verdict.drift_summary}"
            )
        elif conformance_verdict.verdict == "DRIFT-MAJOR":
            session_result.conformance_verdict = ConformanceVerdictEnum.DRIFT_MAJOR

        # Check if should halt
        if self.conformance_checker.should_halt(conformance_verdict):
            self._halt(f"Conformance check: {conformance_verdict.verdict}")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=f"Conformance check: {conformance_verdict.verdict}",
            )

        return LoopResult(status=RunStatus.RUNNING)

    def _check_conformance_fallback_warning(self) -> None:
        """Log warning if conformance fallback count exceeds threshold.

        Should be called after all sessions complete or at halt.
        """
        if self.state is None:
            return

        if self.state.conformance_fallback_count > 2:
            print_warning(
                f"Conformance check defaulted to CONFORMANT "
                f"{self.state.conformance_fallback_count} times this run. "
                "Check conformance subagent reliability."
            )

    def _get_cumulative_files_created(self) -> list[str]:
        """Get all files created across completed sessions."""
        if self.state is None:
            return []

        files = []
        for session_id, result in self.state.session_results.items():
            # Try to load closeout for this session
            closeout_path = self._get_session_log_dir(session_id) / "closeout-structured.json"
            if closeout_path.exists():
                try:
                    data = json.loads(closeout_path.read_text())
                    files.extend(data.get("files_created", []))
                except (json.JSONDecodeError, OSError):
                    pass
        return list(set(files))

    def _get_cumulative_files_modified(self) -> list[str]:
        """Get all files modified across completed sessions."""
        if self.state is None:
            return []

        files = []
        for session_id, result in self.state.session_results.items():
            # Try to load closeout for this session
            closeout_path = self._get_session_log_dir(session_id) / "closeout-structured.json"
            if closeout_path.exists():
                try:
                    data = json.loads(closeout_path.read_text())
                    files.extend(data.get("files_modified", []))
                except (json.JSONDecodeError, OSError):
                    pass
        return list(set(files))

    def _get_cumulative_diff(self) -> str:
        """Get cumulative diff from sprint start to current HEAD."""
        if self.state is None or not self.state.git_state.sprint_start_sha:
            return ""

        from .git_ops import _run_git

        result = _run_git(
            "diff",
            self.state.git_state.sprint_start_sha,
            "HEAD",
            cwd=self.repo_root,
        )
        if result.returncode == 0:
            return result.stdout
        return ""

    # -----------------------------------------------------------------------
    # Notification Helpers
    # -----------------------------------------------------------------------

    def _send_halted_notification(self, reason: str) -> None:
        """Send HALTED notification.

        Args:
            reason: The halt reason.
        """
        if self.state is None:
            return

        completed = sum(
            1 for s in self.state.session_plan
            if s.status == SessionPlanStatus.COMPLETE
        )
        total = len(self.state.session_plan)
        run_log_path = str(self.run_log_base / "run-log")

        data = NotificationData(
            sprint=self.state.sprint,
            session=self.state.current_session or "",
            halt_reason=reason,
            current_phase=str(self.state.current_phase) if self.state.current_phase else "",
            completed_sessions=completed,
            total_sessions=total,
            run_log_path=run_log_path,
        )
        title, body = self.notifications.format_halted(data)
        self.notifications.send("HALTED", title, body, self.state)
        self.state.save(self.state_file)

    def _send_completed_notification(self, sessions_completed: int) -> None:
        """Send COMPLETED notification.

        Args:
            sessions_completed: Number of sessions completed.
        """
        if self.state is None:
            return

        total = len(self.state.session_plan)
        warnings_count = len(self.warnings)

        # Calculate test delta
        tests_before = self.state.test_baseline.initial
        tests_after = self.state.test_baseline.current

        # Calculate duration
        start = self.state.timestamps.run_started
        end = self.state.timestamps.run_completed or datetime.now(UTC).isoformat()
        duration = self._format_duration(start, end)

        # Count fix sessions
        fix_count = sum(
            len(r.fix_sessions_inserted) for r in self.state.session_results.values()
        )

        data = NotificationData(
            sprint=self.state.sprint,
            completed_sessions=sessions_completed,
            total_sessions=total,
            tests_before=tests_before,
            tests_after=tests_after,
            fix_count=fix_count,
            cost=f"{self.state.cost.total_cost_estimate_usd:.2f}",
            duration=duration,
            doc_sync_status="pending" if warnings_count == 0 else f"{warnings_count} warnings",
        )
        title, body = self.notifications.format_completed(data)
        self.notifications.send("COMPLETED", title, body, self.state)
        self.state.save(self.state_file)

    def _send_session_complete_notification(
        self, session: SessionPlanEntry, session_result: SessionResult
    ) -> None:
        """Send SESSION_COMPLETE notification.

        Args:
            session: The completed session.
            session_result: The session result.
        """
        if self.state is None:
            return

        completed = sum(
            1 for s in self.state.session_plan
            if s.status == SessionPlanStatus.COMPLETE
        )
        total = len(self.state.session_plan)

        # Find next session
        next_session = "end of sprint"
        for i, s in enumerate(self.state.session_plan):
            if s.session_id == session.session_id and i + 1 < total:
                next_session = self.state.session_plan[i + 1].session_id
                break

        data = NotificationData(
            sprint=self.state.sprint,
            session=session.session_id,
            tests_before=session_result.tests_before or 0,
            tests_after=session_result.tests_after or 0,
            next_session=next_session,
            completed_sessions=completed,
            total_sessions=total,
        )
        title, body = self.notifications.format_session_complete(data)
        self.notifications.send("SESSION_COMPLETE", title, body, self.state)
        self.state.save(self.state_file)

    def _send_phase_transition(self, phase_name: str, description: str) -> None:
        """Send PHASE_TRANSITION notification.

        Args:
            phase_name: Name of the phase.
            description: Description of what's happening.
        """
        if self.state is None:
            return

        data = NotificationData(
            sprint=self.state.sprint,
            session=self.state.current_session or "",
            phase_name=phase_name,
            phase_description=description,
        )
        title, body = self.notifications.format_phase_transition(data)
        self.notifications.send("PHASE_TRANSITION", title, body, self.state)
        self.state.save(self.state_file)

    def _format_duration(self, start_iso: str, end_iso: str) -> str:
        """Format duration between two ISO timestamps.

        Args:
            start_iso: Start timestamp in ISO format.
            end_iso: End timestamp in ISO format.

        Returns:
            Formatted duration string (e.g., "1h 23m").
        """
        try:
            start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            delta = end - start
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        except Exception:
            return "unknown"

    # -----------------------------------------------------------------------
    # Auto-Split Helpers
    # -----------------------------------------------------------------------

    def _handle_auto_split(
        self, session: SessionPlanEntry, session_result: SessionResult
    ) -> bool:
        """Handle auto-split on compaction detection.

        If compaction_likely is True AND session_metadata has auto_split config,
        insert sub-sessions into the session plan and return True to indicate
        the session should be re-executed from the first sub-session.

        Args:
            session: The session that triggered compaction.
            session_result: The session result with compaction info.

        Returns:
            True if auto-split was applied and sub-sessions inserted.
        """
        if not session_result.compaction_likely:
            return False

        if self.config.session_metadata is None:
            return False

        meta = self.config.session_metadata.get(session.session_id)
        if meta is None or meta.auto_split is None:
            return False

        auto_split = meta.auto_split
        if not auto_split.splits:
            return False

        # Insert sub-sessions
        assert self.state is not None
        inserted_ids = self._insert_auto_split_sessions(
            session, auto_split.splits
        )

        if inserted_ids:
            self.warnings.append(
                f"Auto-split triggered for {session.session_id}: "
                f"inserted {', '.join(inserted_ids)}"
            )
            return True

        return False

    def _insert_auto_split_sessions(
        self, parent_session: SessionPlanEntry, splits: list
    ) -> list[str]:
        """Insert auto-split sub-sessions into the session plan.

        Args:
            parent_session: The parent session being split.
            splits: List of SplitDef with id, title, scope.

        Returns:
            List of inserted session IDs.
        """
        assert self.state is not None

        inserted_ids: list[str] = []

        # Find insertion point (after parent session)
        insert_idx = -1
        for i, s in enumerate(self.state.session_plan):
            if s.session_id == parent_session.session_id:
                insert_idx = i + 1
                break

        if insert_idx < 0:
            return inserted_ids

        # Mark parent as SKIPPED (replaced by sub-sessions)
        parent_session.status = SessionPlanStatus.SKIPPED

        # Create and insert sub-sessions
        for split_def in splits:
            sub_session_id = f"{parent_session.session_id}-{split_def.id}"

            # Generate prompt file path
            prompt_file = str(
                self.sprint_dir / f"sprint-{self.state.sprint}-{sub_session_id}-impl.md"
            )
            review_file = str(
                self.sprint_dir / f"sprint-{self.state.sprint}-{sub_session_id}-review.md"
            )

            sub_session = SessionPlanEntry(
                session_id=sub_session_id,
                title=split_def.title,
                status=SessionPlanStatus.INSERTED,
                depends_on=[parent_session.session_id] if inserted_ids else [],
                prompt_file=prompt_file,
                review_prompt_file=review_file,
                inserted_by=parent_session.session_id,
            )

            self.state.session_plan.insert(insert_idx, sub_session)
            insert_idx += 1
            inserted_ids.append(sub_session_id)

        self.state.save(self.state_file)
        return inserted_ids

    # -----------------------------------------------------------------------
    # Doc Sync Automation
    # -----------------------------------------------------------------------

    async def _run_doc_sync(self) -> bool:
        """Run doc sync automation after all sessions complete.

        Loads doc-sync prompt template, builds prompt with accumulated issues
        and doc update checklist, invokes Claude Code, and saves output.
        Does NOT auto-commit - logs notification for developer review.

        Returns:
            True if doc sync ran successfully.
        """
        if not self.config.doc_sync.enabled:
            return True

        if self.state is None:
            return False

        print_progress(
            len(self.state.session_plan),
            len(self.state.session_plan),
            "DOC-SYNC",
            "RUNNING",
        )

        # Load doc-sync prompt template
        template_path = Path(self.config.doc_sync.prompt_template)
        if not template_path.exists():
            print_warning(f"Doc-sync template not found: {template_path}")
            return False

        template = template_path.read_text()

        # Build prompt with accumulated issues
        accumulated_issues = self._gather_accumulated_issues()
        target_docs = "\n".join(f"- {d}" for d in self.config.doc_sync.target_documents)

        prompt = template.replace("{{ACCUMULATED_ISSUES}}", accumulated_issues)
        prompt = prompt.replace("{{TARGET_DOCUMENTS}}", target_docs)
        prompt = prompt.replace("{{SPRINT}}", self.state.sprint)

        # Set phase
        self.state.current_phase = RunPhase.DOC_SYNC
        self.state.save(self.state_file)

        # Run doc sync session
        result = await self.executor.run_session(prompt, dry_run=self.dry_run)

        # Save output
        log_dir = self.run_log_base / "run-log" / "doc-sync"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "doc-sync-output.md").write_text(result.output)

        print_warning(
            "Doc-sync output ready for review. "
            f"See {log_dir / 'doc-sync-output.md'}"
        )

        return True

    def _gather_accumulated_issues(self) -> str:
        """Gather accumulated issues from all sessions for doc-sync.

        Returns:
            Formatted string of accumulated issues.
        """
        if self.state is None:
            return ""

        issues: list[str] = []

        # Collect scope gaps
        for session_id in self.state.session_results:
            closeout_path = self._get_session_log_dir(session_id) / "closeout-structured.json"
            if closeout_path.exists():
                try:
                    data = json.loads(closeout_path.read_text())
                    if data.get("scope_gaps"):
                        for gap in data["scope_gaps"]:
                            issues.append(f"[{session_id}] SCOPE_GAP: {gap}")
                    if data.get("dec_entries_needed"):
                        for dec in data["dec_entries_needed"]:
                            issues.append(f"[{session_id}] DEC_ENTRY: {dec}")
                    if data.get("doc_impacts"):
                        for doc in data["doc_impacts"]:
                            issues.append(f"[{session_id}] DOC_IMPACT: {doc}")
                except (json.JSONDecodeError, OSError):
                    pass

        # Add warnings
        for warning in self.warnings:
            issues.append(f"[WARNING] {warning}")

        if not issues:
            return "(No accumulated issues)"

        return "\n".join(issues)

    # -----------------------------------------------------------------------
    # Summary Output
    # -----------------------------------------------------------------------

    def _print_run_summary(self) -> None:
        """Print a summary table of the run results."""
        if self.state is None:
            return

        sessions_data: list[tuple[str, str, int | None, str | None]] = []

        for session in self.state.session_plan:
            result = self.state.session_results.get(session.session_id)

            if session.status == SessionPlanStatus.SKIPPED:
                verdict = "SKIPPED"
            elif result and result.review_verdict:
                verdict = str(result.review_verdict)
            elif session.status == SessionPlanStatus.COMPLETE:
                verdict = "COMPLETE"
            else:
                verdict = str(session.status)

            test_delta = None
            if result and result.tests_before is not None and result.tests_after is not None:
                test_delta = result.tests_after - result.tests_before

            duration_str = None
            if result and result.duration_seconds:
                mins = result.duration_seconds // 60
                secs = result.duration_seconds % 60
                duration_str = f"{mins}m {secs}s"

            sessions_data.append((session.session_id, verdict, test_delta, duration_str))

        print_header(f"Sprint {self.state.sprint} Summary")
        print_summary_table(sessions_data)

        # Overall stats
        total_tests_delta = self.state.test_baseline.current - self.state.test_baseline.initial
        total_cost = self.state.cost.total_cost_estimate_usd
        initial = self.state.test_baseline.initial
        current = self.state.test_baseline.current
        print(f"\n{Colors.BOLD}Overall:{Colors.RESET}")
        print(f"  Tests: {initial} -> {current} (+{total_tests_delta})")
        print(f"  Cost: ${total_cost:.2f} / ${self.state.cost.ceiling_usd:.2f}")
        print(f"  Status: {self.state.status}")

        if self.warnings:
            print(f"\n{Colors.YELLOW}Warnings ({len(self.warnings)}):{Colors.RESET}")
            for w in self.warnings[:5]:  # Show first 5
                print(f"  - {w}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more")

    # -----------------------------------------------------------------------
    # Parallel Execution Helpers
    # -----------------------------------------------------------------------

    async def _handle_parallel_sessions(
        self, parallel_sessions: list[SessionPlanEntry]
    ) -> LoopResult:
        """Execute parallel sessions as a group.

        Args:
            parallel_sessions: Sessions to run in parallel.

        Returns:
            LoopResult with combined status.
        """
        session_ids = [s.session_id for s in parallel_sessions]
        print(
            f"{Colors.CYAN}Running {len(parallel_sessions)} sessions in parallel: "
            f"{', '.join(session_ids)}{Colors.RESET}"
        )

        result = await run_parallel_group(parallel_sessions, self)

        if not result.all_success:
            self._halt(result.halt_reason or "Parallel session failed")
            return LoopResult(
                status=RunStatus.HALTED,
                halt_reason=result.halt_reason,
            )

        return LoopResult(
            status=RunStatus.RUNNING,
            sessions_completed=len(parallel_sessions),
        )

    # -----------------------------------------------------------------------
    # Resume Logic
    # -----------------------------------------------------------------------

    def _validate_resume_state(self) -> tuple[bool, str]:
        """Validate state for resume operation.

        Returns:
            Tuple of (valid, error_message). If valid, error_message is empty.
        """
        if not self.state_file.exists():
            return False, "No run-state.json found. Cannot resume."

        try:
            state = RunState.load(self.state_file)
        except Exception as e:
            return False, f"Failed to load run-state.json: {e}"

        # Validate schema version
        if state.schema_version != "1.0":
            return False, f"Unsupported schema version: {state.schema_version}"

        # Validate git SHA matches
        current_sha = get_sha(cwd=self.repo_root)
        if state.git_state.current_sha and current_sha != state.git_state.current_sha:
            return False, (
                f"Git SHA mismatch. State expects {state.git_state.current_sha}, "
                f"but current HEAD is {current_sha}. "
                "Resolve git state before resuming."
            )

        # Validate test baseline within tolerance
        test_count, all_pass = run_tests(
            "python -m pytest tests/ -x -q", cwd=self.repo_root
        )
        tolerance = self.config.execution.test_count_tolerance
        if abs(test_count - state.test_baseline.current) > tolerance:
            return False, (
                f"Test count mismatch. State expects {state.test_baseline.current}, "
                f"but found {test_count}. Delta exceeds tolerance ({tolerance})."
            )

        if not all_pass:
            return False, "Test suite has failures. Fix before resuming."

        return True, ""

    def _determine_resume_point(self) -> tuple[str | None, RunPhase | None]:
        """Determine where to resume from based on current state.

        Returns:
            Tuple of (session_id, phase) to resume from.
            If None, None, start from beginning.
        """
        if self.state is None:
            return None, None

        current_session = self.state.current_session
        current_phase = self.state.current_phase

        if not current_session:
            return None, None

        # Check if implementation output exists
        impl_output_path = (
            self._get_session_log_dir(current_session) / "implementation-output.md"
        )

        if current_phase == RunPhase.IMPLEMENTATION:
            # Rollback and re-run full session
            return current_session, RunPhase.PRE_FLIGHT

        if current_phase in (RunPhase.REVIEW, RunPhase.VERDICT_PARSE):
            # Check if implementation output exists
            if impl_output_path.exists():
                # Resume from review
                return current_session, RunPhase.REVIEW
            else:
                # Re-run from implementation
                return current_session, RunPhase.PRE_FLIGHT

        # For later phases, re-run the session
        return current_session, RunPhase.PRE_FLIGHT


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def async_main(args) -> int:
    """Async main entry point.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # Load configuration
    try:
        config = RunnerConfig.from_yaml(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    # Apply mode override if specified
    if args.mode:
        config.execution.mode = args.mode

    # Determine repo root (assume current directory or parent of config)
    repo_root = Path.cwd()

    # Create and run the runner
    runner = SprintRunner(
        config=config,
        repo_root=repo_root,
        resume=args.resume,
        pause=args.pause,
        stop_after=args.stop_after,
        dry_run=args.dry_run,
        from_session=args.from_session,
        skip_sessions=args.skip_session,
    )

    result = await runner.run()

    if result.status == RunStatus.HALTED:
        print(f"Runner halted: {result.halt_reason}", file=sys.stderr)
        return 1
    elif result.status == RunStatus.COMPLETED_WITH_WARNINGS:
        print(f"Runner completed with {len(result.warnings or [])} warnings")
        return 0
    elif result.status == RunStatus.COMPLETED:
        print(f"Runner completed successfully ({result.sessions_completed} sessions)")
        return 0

    print("Runner initialized. Config loaded.")
    return 0


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
