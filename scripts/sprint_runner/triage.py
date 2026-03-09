"""Tier 2.5 automated triage for the sprint runner.

Invokes a Claude Code subagent to classify issues and recommend actions
per the tier-2.5-triage.md protocol.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.sprint_runner.config import TriageConfig
    from scripts.sprint_runner.executor import ClaudeCodeExecutor, StructuredCloseout
    from scripts.sprint_runner.state import RunState, SessionPlanEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class TriageIssue:
    """A single issue identified during triage."""

    description: str
    source: str  # "scope_gap" | "prior_session_bug" | "review_finding"
    category: str  # "CAT_1" | "CAT_2" | "CAT_3_SMALL" | "CAT_3_SUBSTANTIAL" | "CAT_4"
    action: str  # "INSERT_FIX" | "DEFER" | "HALT" | "LOG_WARNING"
    rationale: str
    fix_description: str | None = None
    blocks_sessions: list[str] = field(default_factory=list)
    defer_target: str | None = None


@dataclass
class FixSession:
    """A fix session to be inserted."""

    fix_id: str
    description: str
    insert_before: str | None = None
    scope: str = ""
    affected_files: list[str] = field(default_factory=list)


@dataclass
class DeferredItem:
    """An item deferred to post-sprint."""

    description: str
    target: str
    def_entry_needed: bool = False


@dataclass
class TriageVerdict:
    """Result of a triage invocation."""

    schema_version: str
    sprint: str
    session: str
    issues: list[TriageIssue]
    overall_recommendation: str  # "PROCEED" | "INSERT_FIXES_THEN_PROCEED" | "HALT"
    fix_sessions_needed: list[FixSession] = field(default_factory=list)
    deferred_items: list[DeferredItem] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Extraction Helpers
# ---------------------------------------------------------------------------

TRIAGE_VERDICT_PATTERN = re.compile(
    r"```json:triage-verdict\s*\n(.*?)\n```",
    re.DOTALL,
)


def _extract_triage_verdict(output: str) -> dict[str, Any] | None:
    """Extract triage verdict JSON from subagent output.

    Args:
        output: The subagent output text.

    Returns:
        Parsed JSON dict, or None if not found.
    """
    match = TRIAGE_VERDICT_PATTERN.search(output)
    if not match:
        return None

    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _parse_triage_verdict(data: dict[str, Any]) -> TriageVerdict:
    """Parse raw triage JSON into TriageVerdict dataclass.

    Args:
        data: Parsed JSON dict.

    Returns:
        TriageVerdict instance.
    """
    issues = []
    for issue_data in data.get("issues", []):
        issues.append(
            TriageIssue(
                description=issue_data.get("description", ""),
                source=issue_data.get("source", ""),
                category=issue_data.get("category", ""),
                action=issue_data.get("action", ""),
                rationale=issue_data.get("rationale", ""),
                fix_description=issue_data.get("fix_description"),
                blocks_sessions=issue_data.get("blocks_sessions", []),
                defer_target=issue_data.get("defer_target"),
            )
        )

    fix_sessions = []
    for fix_data in data.get("fix_sessions_needed", []):
        fix_sessions.append(
            FixSession(
                fix_id=fix_data.get("fix_id", ""),
                description=fix_data.get("description", ""),
                insert_before=fix_data.get("insert_before"),
                scope=fix_data.get("scope", ""),
                affected_files=fix_data.get("affected_files", []),
            )
        )

    deferred = []
    for def_data in data.get("deferred_items", []):
        deferred.append(
            DeferredItem(
                description=def_data.get("description", ""),
                target=def_data.get("target", ""),
                def_entry_needed=def_data.get("def_entry_needed", False),
            )
        )

    return TriageVerdict(
        schema_version=data.get("schema_version", "1.0"),
        sprint=data.get("sprint", ""),
        session=data.get("session", ""),
        issues=issues,
        overall_recommendation=data.get("overall_recommendation", "HALT"),
        fix_sessions_needed=fix_sessions,
        deferred_items=deferred,
        raw=data,
    )


# ---------------------------------------------------------------------------
# Triage Manager
# ---------------------------------------------------------------------------


class TriageManager:
    """Manages Tier 2.5 automated triage.

    Invokes Claude Code subagent with triage prompt, parses verdict,
    and supports fix session insertion.
    """

    def __init__(
        self, executor: ClaudeCodeExecutor, config: TriageConfig, repo_root: Path
    ) -> None:
        """Initialize the triage manager.

        Args:
            executor: Claude Code executor for subagent calls.
            config: Triage configuration.
            repo_root: Path to the repository root.
        """
        self.executor = executor
        self.config = config
        self.repo_root = repo_root
        self._fix_sessions_inserted = 0

    @property
    def fix_sessions_inserted(self) -> int:
        """Number of fix sessions inserted so far."""
        return self._fix_sessions_inserted

    def _load_template(self) -> str:
        """Load the triage prompt template.

        Returns:
            Template content as string.
        """
        template_path = self.repo_root / self.config.prompt_template
        if not template_path.exists():
            raise FileNotFoundError(f"Triage template not found: {template_path}")
        return template_path.read_text()

    def _load_fix_template(self) -> str:
        """Load the fix prompt template.

        Returns:
            Template content as string.
        """
        template_path = self.repo_root / self.config.fix_prompt_template
        if not template_path.exists():
            raise FileNotFoundError(f"Fix template not found: {template_path}")
        return template_path.read_text()

    def _build_triage_prompt(
        self,
        closeout: dict[str, Any],
        verdict: dict[str, Any] | None,
        sprint_spec: str,
        spec_by_contradiction: str,
        session_breakdown: str,
        sprint: str,
        session: str,
        next_sessions: list[str],
        dependent_sessions: list[str],
    ) -> str:
        """Build the triage prompt from template and inputs.

        Args:
            closeout: Structured closeout data.
            verdict: Structured review verdict (if any).
            sprint_spec: Sprint specification content.
            spec_by_contradiction: Spec-by-contradiction content.
            session_breakdown: Session breakdown table content.
            sprint: Sprint number.
            session: Session ID.
            next_sessions: List of next session IDs.
            dependent_sessions: List of dependent session IDs.

        Returns:
            Populated prompt string.
        """
        template = self._load_template()

        # Build replacements
        replacements = {
            "{SPRINT}": sprint,
            "{SESSION}": session,
            "{SPRINT_SPEC}": sprint_spec,
            "{SPEC_BY_CONTRADICTION}": spec_by_contradiction,
            "{SESSION_BREAKDOWN}": session_breakdown,
            "{STRUCTURED_CLOSEOUT}": json.dumps(closeout, indent=2),
            "{STRUCTURED_VERDICT_OR_NULL}": (
                json.dumps(verdict, indent=2) if verdict else "null"
            ),
            "{NEXT_SESSIONS}": ", ".join(next_sessions) if next_sessions else "None",
            "{DEPENDENT_SESSIONS}": (
                ", ".join(dependent_sessions) if dependent_sessions else "None"
            ),
            "{MAX_AUTO_FIXES}": str(self.config.max_auto_fixes),
        }

        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    async def run_triage(
        self,
        closeout: dict[str, Any],
        verdict: dict[str, Any] | None,
        sprint_spec: str,
        spec_by_contradiction: str,
        session_breakdown: str,
        sprint: str,
        session: str,
        next_sessions: list[str] | None = None,
        dependent_sessions: list[str] | None = None,
    ) -> TriageVerdict:
        """Run Tier 2.5 triage on a session's issues.

        Args:
            closeout: Structured closeout data (dict).
            verdict: Structured review verdict (if any).
            sprint_spec: Sprint specification content.
            spec_by_contradiction: Spec-by-contradiction content.
            session_breakdown: Session breakdown table content.
            sprint: Sprint number.
            session: Session ID.
            next_sessions: List of next session IDs.
            dependent_sessions: List of dependent session IDs.

        Returns:
            TriageVerdict with classifications and recommendations.
        """
        prompt = self._build_triage_prompt(
            closeout=closeout,
            verdict=verdict,
            sprint_spec=sprint_spec,
            spec_by_contradiction=spec_by_contradiction,
            session_breakdown=session_breakdown,
            sprint=sprint,
            session=session,
            next_sessions=next_sessions or [],
            dependent_sessions=dependent_sessions or [],
        )

        try:
            result = await self.executor.run_session(prompt)
            data = _extract_triage_verdict(result.output)

            if data is None:
                # Conservative bias: if no parseable verdict, treat as HALT
                logger.warning(
                    f"Triage subagent returned no parseable verdict for {session}. "
                    "Treating as HALT per conservative bias."
                )
                return TriageVerdict(
                    schema_version="1.0",
                    sprint=sprint,
                    session=session,
                    issues=[],
                    overall_recommendation="HALT",
                    raw={"error": "no_parseable_verdict"},
                )

            return _parse_triage_verdict(data)

        except Exception as e:
            # On any failure, return HALT (conservative bias per protocol)
            logger.warning(
                f"Triage subagent failed for {session}: {e}. Treating as HALT."
            )
            return TriageVerdict(
                schema_version="1.0",
                sprint=sprint,
                session=session,
                issues=[],
                overall_recommendation="HALT",
                raw={"error": str(e)},
            )

    def generate_fix_prompt(
        self,
        issue: TriageIssue,
        fix_session: FixSession,
        sprint_spec: str,
        sprint: str,
        source_session: str,
        expected_tests: int,
        sprint_regression_checklist: str = "",
        sprint_escalation_criteria: str = "",
    ) -> str:
        """Generate a fix session implementation prompt.

        Args:
            issue: The issue being fixed.
            fix_session: Fix session details.
            sprint_spec: Sprint specification content.
            sprint: Sprint number.
            source_session: Original session ID.
            expected_tests: Expected test count.
            sprint_regression_checklist: Sprint-level regression checklist.
            sprint_escalation_criteria: Sprint-level escalation criteria.

        Returns:
            Populated fix prompt string.
        """
        template = self._load_fix_template()

        # Build affected files read list
        read_list = "\n".join(
            f"   - Read: `{f}`" for f in fix_session.affected_files
        ) or "   - (none)"

        # Build affected files list
        affected_list = "\n".join(
            f"- `{f}`" for f in fix_session.affected_files
        ) or "- (none)"

        replacements = {
            "{SPRINT}": sprint,
            "{FIX_ID}": fix_session.fix_id,
            "{DESCRIPTION}": fix_session.description,
            "{SOURCE_SESSION}": source_session,
            "{CATEGORY}": issue.category,
            "{SOURCE_TYPE}": issue.source,
            "{ISSUE_DESCRIPTION}": issue.description,
            "{BLOCKED_SESSIONS}": (
                ", ".join(issue.blocks_sessions) if issue.blocks_sessions else "None"
            ),
            "{EXPECTED_TESTS}": str(expected_tests),
            "{AFFECTED_FILES_READ_LIST}": read_list,
            "{FIX_DESCRIPTION}": issue.fix_description or fix_session.description,
            "{FIX_REQUIREMENTS}": fix_session.scope,
            "{DO_NOT_MODIFY_LIST}": "files outside the fix scope",
            "{AFFECTED_FILES}": affected_list,
            "{FIX_VERIFICATION}": (
                f"Issue '{issue.description}' is resolved and tested"
            ),
            "{SPRINT_REGRESSION_CHECKLIST}": (
                sprint_regression_checklist or "See review-context.md"
            ),
            "{SPRINT_ESCALATION_CRITERIA}": (
                sprint_escalation_criteria or "See review-context.md"
            ),
        }

        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    def insert_fix_sessions(
        self,
        triage_verdict: TriageVerdict,
        run_state: RunState,
        current_session_id: str,
        sprint_dir: Path,
    ) -> list[str]:
        """Insert fix sessions into the run state's session plan.

        Args:
            triage_verdict: The triage verdict with fix sessions needed.
            run_state: The current run state.
            current_session_id: The current session's ID.
            sprint_dir: Path to the sprint directory.

        Returns:
            List of inserted fix session IDs.
        """
        from scripts.sprint_runner.state import SessionPlanEntry, SessionPlanStatus

        if not self.config.auto_insert_fixes:
            return []

        inserted_ids: list[str] = []

        for fix_session in triage_verdict.fix_sessions_needed:
            # Check max auto-fixes limit
            if self._fix_sessions_inserted >= self.config.max_auto_fixes:
                logger.warning(
                    f"Max auto-fixes ({self.config.max_auto_fixes}) reached. "
                    f"Cannot insert {fix_session.fix_id}."
                )
                break

            # Find insertion point (after current session)
            insert_idx = None
            for i, session in enumerate(run_state.session_plan):
                if session.session_id == current_session_id:
                    insert_idx = i + 1
                    break

            if insert_idx is None:
                logger.error(
                    f"Could not find insertion point for fix session {fix_session.fix_id}"
                )
                continue

            # Create SessionPlanEntry for fix session
            fix_entry = SessionPlanEntry(
                session_id=fix_session.fix_id,
                title=fix_session.description,
                status=SessionPlanStatus.INSERTED,
                depends_on=[current_session_id],
                parallelizable=False,
                prompt_file=str(sprint_dir / f"{fix_session.fix_id}-impl.md"),
                review_prompt_file=str(sprint_dir / f"{fix_session.fix_id}-review.md"),
                inserted_by=current_session_id,
            )

            # Insert into session plan
            run_state.session_plan.insert(insert_idx, fix_entry)
            inserted_ids.append(fix_session.fix_id)
            self._fix_sessions_inserted += 1

            logger.info(
                f"Inserted fix session {fix_session.fix_id} after {current_session_id}"
            )

        return inserted_ids

    def check_max_auto_fixes_exceeded(self) -> bool:
        """Check if the max auto-fixes limit has been exceeded.

        Returns:
            True if limit exceeded, False otherwise.
        """
        return self._fix_sessions_inserted >= self.config.max_auto_fixes

    def reset_fix_count(self) -> None:
        """Reset the fix session count (e.g., for a new sprint)."""
        self._fix_sessions_inserted = 0
