"""Run state management.

Pydantic models matching the canonical schema in
docs/protocols/schemas/run-state-schema.md.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from .config import RunnerConfig

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(StrEnum):
    """Overall run status."""

    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    HALTED = "HALTED"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class RunPhase(StrEnum):
    """Current phase within the active session."""

    PRE_FLIGHT = "PRE_FLIGHT"
    IMPLEMENTATION = "IMPLEMENTATION"
    CLOSEOUT_PARSE = "CLOSEOUT_PARSE"
    REVIEW = "REVIEW"
    VERDICT_PARSE = "VERDICT_PARSE"
    TRIAGE = "TRIAGE"
    CONFORMANCE_CHECK = "CONFORMANCE_CHECK"
    GIT_COMMIT = "GIT_COMMIT"
    FIX_SESSION = "FIX_SESSION"
    DOC_SYNC = "DOC_SYNC"
    COMPLETE = "COMPLETE"


class SessionPlanStatus(StrEnum):
    """Status of a session in the plan."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    INSERTED = "INSERTED"


class ImplementationVerdict(StrEnum):
    """Implementation phase verdict."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"


class ReviewVerdict(StrEnum):
    """Review phase verdict."""

    CLEAR = "CLEAR"
    CONCERNS = "CONCERNS"
    ESCALATE = "ESCALATE"


class ConformanceVerdict(StrEnum):
    """Conformance check verdict."""

    CONFORMANT = "CONFORMANT"
    DRIFT_MINOR = "DRIFT-MINOR"
    DRIFT_MAJOR = "DRIFT-MAJOR"


class NotificationTier(StrEnum):
    """Notification tier."""

    HALTED = "HALTED"
    SESSION_COMPLETE = "SESSION_COMPLETE"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    WARNING = "WARNING"
    COMPLETED = "COMPLETED"


# ---------------------------------------------------------------------------
# State Sub-Models
# ---------------------------------------------------------------------------


class SessionPlanEntry(BaseModel):
    """A single entry in the session plan."""

    session_id: str
    title: str
    status: SessionPlanStatus = SessionPlanStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)
    parallelizable: bool = False
    prompt_file: str | None = None
    review_prompt_file: str | None = None
    inserted_by: str | None = None


class SessionResult(BaseModel):
    """Results from a completed session."""

    implementation_verdict: ImplementationVerdict | None = None
    review_verdict: ReviewVerdict | None = None
    conformance_verdict: ConformanceVerdict | None = None
    triage_verdict: str | None = None
    retries: int = 0
    retry_reasons: list[str] = Field(default_factory=list)
    tests_before: int | None = None
    tests_after: int | None = None
    git_sha_before: str | None = None
    git_sha_after: str | None = None
    token_usage_estimate: int | None = None
    cost_estimate_usd: float | None = None
    duration_seconds: int | None = None
    fix_sessions_inserted: list[str] = Field(default_factory=list)
    output_size_bytes: int | None = None
    compaction_likely: bool = False
    compaction_risk_score: int | None = None


class GitState(BaseModel):
    """Git state tracking."""

    branch: str
    sprint_start_sha: str = ""
    current_sha: str = ""
    checkpoint_sha: str | None = None


class CostState(BaseModel):
    """Cost tracking state."""

    total_tokens_estimate: int = 0
    total_cost_estimate_usd: float = 0.0
    ceiling_usd: float = 50.0


class TestBaseline(BaseModel):
    """Test count baseline tracking."""

    initial: int = 0
    current: int = 0


class IssuesCount(BaseModel):
    """Accumulated issue counts."""

    scope_gaps: int = 0
    prior_session_bugs: int = 0
    deferred_observations: int = 0
    fix_sessions_inserted: int = 0
    warnings: int = 0


class Timestamps(BaseModel):
    """Run timestamps."""

    run_started: str = ""
    last_updated: str = ""
    run_completed: str | None = None


class NotificationSent(BaseModel):
    """Record of a sent notification."""

    timestamp: str
    tier: NotificationTier
    message: str
    channel: str


# ---------------------------------------------------------------------------
# Top-Level State
# ---------------------------------------------------------------------------


class RunState(BaseModel):
    """Complete run state.

    Matches the canonical schema in docs/protocols/schemas/run-state-schema.md.
    The orchestrator's checkpoint — tracks current position in the session loop,
    accumulated results, and everything needed to resume from any interruption.
    """

    schema_version: str = "1.0"
    sprint: str
    mode: str = "autonomous"
    status: RunStatus = RunStatus.NOT_STARTED
    halt_reason: str | None = None
    current_session: str | None = None
    current_phase: RunPhase | None = None
    session_plan: list[SessionPlanEntry] = Field(default_factory=list)
    session_results: dict[str, SessionResult] = Field(default_factory=dict)
    git_state: GitState
    cost: CostState = Field(default_factory=CostState)
    test_baseline: TestBaseline = Field(default_factory=TestBaseline)
    issues_count: IssuesCount = Field(default_factory=IssuesCount)
    timestamps: Timestamps = Field(default_factory=Timestamps)
    review_context_hash: str | None = None
    notifications_sent: list[NotificationSent] = Field(default_factory=list)
    conformance_fallback_count: int = 0

    def save(self, path: str | Path) -> None:
        """Save state to file with atomic write.

        Writes to {path}.tmp first, then renames to {path} for atomicity.

        Args:
            path: Path to the state file.
        """
        filepath = Path(path)
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")

        # Update last_updated timestamp
        self.timestamps.last_updated = datetime.now(UTC).isoformat()

        # Write to temp file
        with open(tmp_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

        # Atomic rename
        os.rename(tmp_path, filepath)

    @classmethod
    def load(cls, path: str | Path) -> RunState:
        """Load state from file.

        Args:
            path: Path to the state file.

        Returns:
            Validated RunState instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            pydantic.ValidationError: If validation fails.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"State file not found: {path}")

        with open(filepath) as f:
            data = json.load(f)

        # Validate schema version
        schema_version = data.get("schema_version")
        if schema_version != "1.0":
            raise ValueError(
                f"Unsupported schema version '{schema_version}'. Expected '1.0'"
            )

        return cls(**data)

    @classmethod
    def create_initial(cls, config: RunnerConfig) -> RunState:
        """Create initial state from configuration.

        Args:
            config: The runner configuration.

        Returns:
            New RunState with NOT_STARTED status.
        """
        # Extract sprint number from directory path
        # e.g., "docs/sprints/sprint-23" → "23"
        sprint_dir = Path(config.sprint.directory)
        sprint_name = sprint_dir.name
        sprint_number = sprint_name.replace("sprint-", "")

        # Build initial session plan
        session_plan: list[SessionPlanEntry] = []
        for session_id in config.sprint.session_order:
            title = ""
            depends_on: list[str] = []
            parallelizable = False

            # Check session_metadata for extended info
            if config.session_metadata and session_id in config.session_metadata:
                meta = config.session_metadata[session_id]
                title = meta.title
                depends_on = meta.depends_on
                parallelizable = meta.parallelizable

            # Construct prompt file paths
            prompt_file = str(sprint_dir / f"{sprint_name}-{session_id}-impl.md")
            review_prompt_file = str(sprint_dir / f"{sprint_name}-{session_id}-review.md")

            session_plan.append(
                SessionPlanEntry(
                    session_id=session_id,
                    title=title,
                    depends_on=depends_on,
                    parallelizable=parallelizable,
                    prompt_file=prompt_file,
                    review_prompt_file=review_prompt_file,
                )
            )

        now = datetime.now(UTC).isoformat()

        return cls(
            sprint=sprint_number,
            mode=config.execution.mode,
            status=RunStatus.NOT_STARTED,
            session_plan=session_plan,
            git_state=GitState(branch=config.git.branch),
            cost=CostState(ceiling_usd=config.cost.ceiling_usd),
            timestamps=Timestamps(run_started=now, last_updated=now),
        )
