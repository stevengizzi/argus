"""Spec conformance check for the sprint runner.

Invokes a Claude Code subagent to verify cumulative changes conform
to the sprint spec per the spec-conformance-check.md protocol.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts.sprint_runner.config import ConformanceConfig
    from scripts.sprint_runner.executor import ClaudeCodeExecutor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum diff size before summarizing at file level (~50KB)
MAX_DIFF_SIZE_BYTES = 50 * 1024


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class ConformanceFinding:
    """A single finding from conformance check."""

    finding_type: str  # FILE_SCOPE | SPEC_CONTRADICTION | NAMING | INTEGRATION | DESIGN_INTENT
    severity: str  # INFO | LOW | MEDIUM | HIGH
    description: str
    details: str | None = None


@dataclass
class FileScopeCheck:
    """Results of file scope verification."""

    unexpected_files_created: list[str] = field(default_factory=list)
    unexpected_files_modified: list[str] = field(default_factory=list)
    expected_files_missing: list[str] = field(default_factory=list)


@dataclass
class SpecContradictionCheck:
    """Results of spec-by-contradiction compliance check."""

    violations: list[str] = field(default_factory=list)
    clean: bool = True


@dataclass
class IntegrationCheck:
    """Results of integration wiring verification."""

    verified: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    not_yet_due: list[str] = field(default_factory=list)


@dataclass
class ConformanceVerdict:
    """Result of a conformance check invocation."""

    schema_version: str
    sprint: str
    session: str
    cumulative_sessions_checked: list[str]
    verdict: str  # "CONFORMANT" | "DRIFT-MINOR" | "DRIFT-MAJOR"
    findings: list[ConformanceFinding]
    file_scope_check: FileScopeCheck
    spec_by_contradiction_check: SpecContradictionCheck
    integration_check: IntegrationCheck
    drift_summary: str
    raw: dict[str, Any] = field(default_factory=dict)
    is_fallback: bool = False


# ---------------------------------------------------------------------------
# Extraction Helpers
# ---------------------------------------------------------------------------

CONFORMANCE_VERDICT_PATTERN = re.compile(
    r"```json:conformance-verdict\s*\n(.*?)\n```",
    re.DOTALL,
)


def _extract_conformance_verdict(output: str) -> dict[str, Any] | None:
    """Extract conformance verdict JSON from subagent output.

    Args:
        output: The subagent output text.

    Returns:
        Parsed JSON dict, or None if not found.
    """
    match = CONFORMANCE_VERDICT_PATTERN.search(output)
    if not match:
        return None

    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _parse_conformance_verdict(data: dict[str, Any]) -> ConformanceVerdict:
    """Parse raw conformance JSON into ConformanceVerdict dataclass.

    Args:
        data: Parsed JSON dict.

    Returns:
        ConformanceVerdict instance.
    """
    findings = []
    for f in data.get("findings", []):
        findings.append(
            ConformanceFinding(
                finding_type=f.get("type", ""),
                severity=f.get("severity", "INFO"),
                description=f.get("description", ""),
                details=f.get("details"),
            )
        )

    file_scope_data = data.get("file_scope_check", {})
    file_scope = FileScopeCheck(
        unexpected_files_created=file_scope_data.get("unexpected_files_created", []),
        unexpected_files_modified=file_scope_data.get("unexpected_files_modified", []),
        expected_files_missing=file_scope_data.get("expected_files_missing", []),
    )

    spec_contra_data = data.get("spec_by_contradiction_check", {})
    spec_contra = SpecContradictionCheck(
        violations=spec_contra_data.get("violations", []),
        clean=spec_contra_data.get("clean", True),
    )

    integ_data = data.get("integration_check", {})
    integration = IntegrationCheck(
        verified=integ_data.get("verified", []),
        missing=integ_data.get("missing", []),
        not_yet_due=integ_data.get("not_yet_due", []),
    )

    return ConformanceVerdict(
        schema_version=data.get("schema_version", "1.0"),
        sprint=data.get("sprint", ""),
        session=data.get("session", ""),
        cumulative_sessions_checked=data.get("cumulative_sessions_checked", []),
        verdict=data.get("verdict", "CONFORMANT"),
        findings=findings,
        file_scope_check=file_scope,
        spec_by_contradiction_check=spec_contra,
        integration_check=integration,
        drift_summary=data.get("drift_summary", ""),
        raw=data,
    )


def _summarize_large_diff(diff: str, files_created: list[str], files_modified: list[str]) -> str:
    """Summarize a large diff at file level.

    Args:
        diff: The full diff content.
        files_created: List of created files.
        files_modified: List of modified files.

    Returns:
        File-level summary string.
    """
    summary_parts = ["[DIFF SUMMARIZED - exceeds 50KB limit]", ""]

    if files_created:
        summary_parts.append("Files Created:")
        for f in files_created:
            summary_parts.append(f"  + {f}")
        summary_parts.append("")

    if files_modified:
        summary_parts.append("Files Modified:")
        for f in files_modified:
            summary_parts.append(f"  ~ {f}")
        summary_parts.append("")

    # Try to extract some statistics from the diff
    lines = diff.split("\n")
    additions = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))

    summary_parts.append(f"Statistics: +{additions} additions, -{deletions} deletions")

    return "\n".join(summary_parts)


# ---------------------------------------------------------------------------
# Conformance Checker
# ---------------------------------------------------------------------------


class ConformanceChecker:
    """Checks spec conformance after each session.

    Invokes Claude Code subagent to verify cumulative changes align
    with the sprint spec and respect spec-by-contradiction boundaries.
    """

    def __init__(
        self, executor: ClaudeCodeExecutor, config: ConformanceConfig, repo_root: Path
    ) -> None:
        """Initialize the conformance checker.

        Args:
            executor: Claude Code executor for subagent calls.
            config: Conformance configuration.
            repo_root: Path to the repository root.
        """
        self.executor = executor
        self.config = config
        self.repo_root = repo_root

    def _load_template(self) -> str:
        """Load the conformance prompt template.

        Returns:
            Template content as string.
        """
        template_path = self.repo_root / self.config.prompt_template
        if not template_path.exists():
            raise FileNotFoundError(f"Conformance template not found: {template_path}")
        return template_path.read_text()

    def _build_conformance_prompt(
        self,
        sprint_spec: str,
        spec_by_contradiction: str,
        session_breakdown: str,
        completed_sessions: list[str],
        cumulative_files_created: list[str],
        cumulative_files_modified: list[str],
        cumulative_diff: str,
        current_closeout: dict[str, Any],
        sprint: str,
        session: str,
    ) -> str:
        """Build the conformance prompt from template and inputs.

        Args:
            sprint_spec: Sprint specification content.
            spec_by_contradiction: Spec-by-contradiction content.
            session_breakdown: Session breakdown table content.
            completed_sessions: List of completed session IDs.
            cumulative_files_created: List of all created files.
            cumulative_files_modified: List of all modified files.
            cumulative_diff: Cumulative git diff content.
            current_closeout: Current session's closeout data.
            sprint: Sprint number.
            session: Session ID.

        Returns:
            Populated prompt string.
        """
        template = self._load_template()

        # Handle large diff
        diff_content = cumulative_diff
        if len(cumulative_diff.encode("utf-8")) > MAX_DIFF_SIZE_BYTES:
            diff_content = _summarize_large_diff(
                cumulative_diff, cumulative_files_created, cumulative_files_modified
            )

        # Format lists
        files_created_str = (
            "\n".join(f"- {f}" for f in cumulative_files_created)
            if cumulative_files_created
            else "(none)"
        )
        files_modified_str = (
            "\n".join(f"- {f}" for f in cumulative_files_modified)
            if cumulative_files_modified
            else "(none)"
        )
        completed_sessions_str = ", ".join(completed_sessions) if completed_sessions else "(none)"
        completed_sessions_array = json.dumps(completed_sessions)

        replacements = {
            "{SPRINT}": sprint,
            "{SESSION}": session,
            "{SPRINT_SPEC}": sprint_spec,
            "{SPEC_BY_CONTRADICTION}": spec_by_contradiction,
            "{SESSION_BREAKDOWN}": session_breakdown,
            "{COMPLETED_SESSIONS_LIST}": completed_sessions_str,
            "{CUMULATIVE_FILES_CREATED}": files_created_str,
            "{CUMULATIVE_FILES_MODIFIED}": files_modified_str,
            "{CUMULATIVE_DIFF_OR_SUMMARY}": diff_content,
            "{CURRENT_CLOSEOUT_JSON}": json.dumps(current_closeout, indent=2),
            "{COMPLETED_SESSIONS_ARRAY}": completed_sessions_array,
        }

        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    async def check(
        self,
        sprint_spec: str,
        spec_by_contradiction: str,
        session_breakdown: str,
        completed_sessions: list[str],
        cumulative_files_created: list[str],
        cumulative_files_modified: list[str],
        cumulative_diff: str,
        current_closeout: dict[str, Any],
        sprint: str,
        session: str,
    ) -> ConformanceVerdict:
        """Run spec conformance check.

        Args:
            sprint_spec: Sprint specification content.
            spec_by_contradiction: Spec-by-contradiction content.
            session_breakdown: Session breakdown table content.
            completed_sessions: List of completed session IDs.
            cumulative_files_created: List of all created files.
            cumulative_files_modified: List of all modified files.
            cumulative_diff: Cumulative git diff content.
            current_closeout: Current session's closeout data.
            sprint: Sprint number.
            session: Session ID.

        Returns:
            ConformanceVerdict with conformance status.
        """
        if not self.config.enabled:
            # Return CONFORMANT if disabled
            return ConformanceVerdict(
                schema_version="1.0",
                sprint=sprint,
                session=session,
                cumulative_sessions_checked=completed_sessions,
                verdict="CONFORMANT",
                findings=[],
                file_scope_check=FileScopeCheck(),
                spec_by_contradiction_check=SpecContradictionCheck(),
                integration_check=IntegrationCheck(),
                drift_summary="Conformance check disabled",
                raw={"disabled": True},
            )

        prompt = self._build_conformance_prompt(
            sprint_spec=sprint_spec,
            spec_by_contradiction=spec_by_contradiction,
            session_breakdown=session_breakdown,
            completed_sessions=completed_sessions,
            cumulative_files_created=cumulative_files_created,
            cumulative_files_modified=cumulative_files_modified,
            cumulative_diff=cumulative_diff,
            current_closeout=current_closeout,
            sprint=sprint,
            session=session,
        )

        try:
            result = await self.executor.run_session(prompt)
            data = _extract_conformance_verdict(result.output)

            if data is None:
                # Per protocol: if check itself fails, log WARNING and return CONFORMANT
                logger.warning(
                    f"Conformance check for {session} returned no parseable verdict. "
                    "Defaulting to CONFORMANT (defense-in-depth, not critical gate)."
                )
                return ConformanceVerdict(
                    schema_version="1.0",
                    sprint=sprint,
                    session=session,
                    cumulative_sessions_checked=completed_sessions,
                    verdict="CONFORMANT",
                    findings=[],
                    file_scope_check=FileScopeCheck(),
                    spec_by_contradiction_check=SpecContradictionCheck(),
                    integration_check=IntegrationCheck(),
                    drift_summary="Check failed to produce verdict; defaulting to CONFORMANT",
                    raw={"error": "no_parseable_verdict"},
                    is_fallback=True,
                )

            return _parse_conformance_verdict(data)

        except Exception as e:
            # Per protocol: if check fails, log WARNING and return CONFORMANT
            logger.warning(
                f"Conformance check failed for {session}: {e}. "
                "Defaulting to CONFORMANT (defense-in-depth, not critical gate)."
            )
            return ConformanceVerdict(
                schema_version="1.0",
                sprint=sprint,
                session=session,
                cumulative_sessions_checked=completed_sessions,
                verdict="CONFORMANT",
                findings=[],
                file_scope_check=FileScopeCheck(),
                spec_by_contradiction_check=SpecContradictionCheck(),
                integration_check=IntegrationCheck(),
                drift_summary=f"Check failed: {e}; defaulting to CONFORMANT",
                raw={"error": str(e)},
                is_fallback=True,
            )

    def should_halt(self, verdict: ConformanceVerdict) -> bool:
        """Determine if the runner should halt based on verdict.

        Args:
            verdict: The conformance verdict.

        Returns:
            True if runner should halt, False otherwise.
        """
        if verdict.verdict == "DRIFT-MAJOR":
            # DRIFT-MAJOR always halts
            return True

        if verdict.verdict == "DRIFT-MINOR":
            # DRIFT-MINOR halts only if config says to halt
            return self.config.drift_minor_action == "halt"

        # CONFORMANT - proceed
        return False
