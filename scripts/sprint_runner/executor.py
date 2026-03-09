"""Claude Code CLI executor.

Handles subprocess invocation of Claude Code CLI with structured output
extraction and retry logic.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from scripts.sprint_runner.config import ExecutionConfig


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    """Result of a Claude Code CLI invocation."""

    output: str
    exit_code: int
    duration_seconds: float
    output_size_bytes: int
    compaction_likely: bool = False


@dataclass
class StructuredCloseout:
    """Parsed structured close-out data."""

    schema_version: str
    sprint: str
    session: str
    verdict: str
    tests: dict[str, Any]
    files_created: list[str]
    files_modified: list[str]
    scope_additions: list[dict[str, Any]]
    scope_gaps: list[dict[str, Any]]
    prior_session_bugs: list[dict[str, Any]]
    deferred_observations: list[str]
    doc_impacts: list[dict[str, Any]]
    dec_entries_needed: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredVerdict:
    """Parsed structured review verdict data."""

    schema_version: str
    sprint: str
    session: str
    verdict: str
    findings: list[dict[str, Any]]
    spec_conformance: dict[str, Any]
    files_reviewed: list[str]
    tests_verified: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ExecutorError(Exception):
    """Base exception for executor errors."""


class CLINotFoundError(ExecutorError):
    """Claude Code CLI is not available."""


class CLITimeoutError(ExecutorError):
    """Claude Code CLI timed out."""


class ExtractionError(ExecutorError):
    """Failed to extract structured output."""


class ValidationError(ExecutorError):
    """Structured output validation failed."""


class RetryExhaustedError(ExecutorError):
    """All retries exhausted."""


# ---------------------------------------------------------------------------
# Extraction Helpers
# ---------------------------------------------------------------------------

# Regex patterns for extracting JSON blocks
CLOSEOUT_PATTERN = re.compile(
    r"```json:structured-closeout\s*\n(.*?)\n```",
    re.DOTALL,
)

VERDICT_PATTERN = re.compile(
    r"```json:structured-verdict\s*\n(.*?)\n```",
    re.DOTALL,
)

# Marker for prose close-out (to distinguish LLM compliance vs transient failures)
PROSE_CLOSEOUT_MARKER = "---BEGIN-CLOSE-OUT---"


# Required fields for validation
CLOSEOUT_REQUIRED_FIELDS = {
    "schema_version",
    "sprint",
    "session",
    "verdict",
    "tests",
    "files_created",
    "files_modified",
    "scope_additions",
    "scope_gaps",
    "prior_session_bugs",
    "deferred_observations",
    "doc_impacts",
    "dec_entries_needed",
}

VERDICT_REQUIRED_FIELDS = {
    "schema_version",
    "sprint",
    "session",
    "verdict",
    "findings",
    "spec_conformance",
    "files_reviewed",
    "tests_verified",
}


def extract_json_block(output: str, pattern: re.Pattern[str]) -> dict[str, Any] | None:
    """Extract and parse a JSON block from output.

    Args:
        output: The full output text to search.
        pattern: Compiled regex pattern with one capture group for the JSON.

    Returns:
        Parsed JSON as dict, or None if block not found.

    Raises:
        ValidationError: If JSON is found but cannot be parsed.
    """
    match = pattern.search(output)
    if not match:
        return None

    json_str = match.group(1).strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in structured block: {e}") from e


def validate_required_fields(data: dict[str, Any], required: set[str]) -> None:
    """Validate that all required fields are present.

    Args:
        data: The parsed data dict.
        required: Set of required field names.

    Raises:
        ValidationError: If any required field is missing.
    """
    missing = required - set(data.keys())
    if missing:
        raise ValidationError(f"Missing required fields: {sorted(missing)}")


# ---------------------------------------------------------------------------
# Claude Code Executor
# ---------------------------------------------------------------------------


class ClaudeCodeExecutor:
    """Executor for Claude Code CLI invocations.

    Handles subprocess management, output capture, structured extraction,
    and retry logic with exponential backoff.
    """

    def __init__(self, config: ExecutionConfig) -> None:
        """Initialize the executor.

        Args:
            config: Execution configuration with retry settings, timeouts, etc.
        """
        self.config = config
        self._cli_verified = False

    async def verify_cli(self) -> None:
        """Verify Claude Code CLI is available.

        Raises:
            CLINotFoundError: If the CLI cannot be found or executed.
        """
        if self._cli_verified:
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise CLINotFoundError(
                    f"Claude CLI returned error: {stderr.decode().strip()}"
                )
            self._cli_verified = True
        except FileNotFoundError as e:
            raise CLINotFoundError(
                "Claude Code CLI not found. Is it installed and in PATH?"
            ) from e

    async def run_session(
        self,
        prompt: str,
        timeout: int | None = None,
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Run a Claude Code session with the given prompt.

        Args:
            prompt: The prompt to send to Claude Code.
            timeout: Optional timeout in seconds. Uses config default if not specified.
            dry_run: If True, return mock result without invoking subprocess.

        Returns:
            ExecutionResult with output, exit code, duration, and size.

        Raises:
            CLINotFoundError: If Claude CLI is not available.
            CLITimeoutError: If the session times out.
        """
        if dry_run:
            return ExecutionResult(
                output="[DRY RUN] Session would have executed with prompt.",
                exit_code=0,
                duration_seconds=0.0,
                output_size_bytes=0,
                compaction_likely=False,
            )

        await self.verify_cli()

        effective_timeout = timeout
        if effective_timeout is None and self.config.session_timeout_seconds > 0:
            effective_timeout = self.config.session_timeout_seconds

        start_time = time.monotonic()

        try:
            # Build CLI args list
            # In autonomous mode, skip permission prompts since nobody is present to approve.
            # In human-in-the-loop mode, allow normal permission prompts for interactive approval.
            cli_args = ["claude", "--print", "--output-format", "text"]
            if self.config.mode == "autonomous":
                cli_args.append("--dangerously-skip-permissions")
            cli_args.append(prompt)

            proc = await asyncio.create_subprocess_exec(
                *cli_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            if effective_timeout:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=effective_timeout,
                )
            else:
                stdout, _ = await proc.communicate()

        except TimeoutError:
            proc.kill()
            await proc.wait()
            duration = time.monotonic() - start_time
            raise CLITimeoutError(
                f"Claude Code session timed out after {duration:.1f}s"
            ) from None

        duration = time.monotonic() - start_time
        output = stdout.decode("utf-8", errors="replace")
        output_size = len(output.encode("utf-8"))

        compaction_likely = output_size > self.config.compaction_threshold_bytes

        return ExecutionResult(
            output=output,
            exit_code=proc.returncode or 0,
            duration_seconds=duration,
            output_size_bytes=output_size,
            compaction_likely=compaction_likely,
        )

    def extract_structured_closeout(self, output: str) -> StructuredCloseout | None:
        """Extract and validate structured close-out from session output.

        Args:
            output: The full session output.

        Returns:
            StructuredCloseout if found and valid, None if block not found.

        Raises:
            ValidationError: If block found but invalid JSON or missing fields.
        """
        data = extract_json_block(output, CLOSEOUT_PATTERN)
        if data is None:
            return None

        validate_required_fields(data, CLOSEOUT_REQUIRED_FIELDS)

        return StructuredCloseout(
            schema_version=data["schema_version"],
            sprint=data["sprint"],
            session=data["session"],
            verdict=data["verdict"],
            tests=data["tests"],
            files_created=data["files_created"],
            files_modified=data["files_modified"],
            scope_additions=data["scope_additions"],
            scope_gaps=data["scope_gaps"],
            prior_session_bugs=data["prior_session_bugs"],
            deferred_observations=data["deferred_observations"],
            doc_impacts=data["doc_impacts"],
            dec_entries_needed=data["dec_entries_needed"],
            raw=data,
        )

    def extract_structured_verdict(self, output: str) -> StructuredVerdict | None:
        """Extract and validate structured review verdict from output.

        Args:
            output: The full review output.

        Returns:
            StructuredVerdict if found and valid, None if block not found.

        Raises:
            ValidationError: If block found but invalid JSON or missing fields.
        """
        data = extract_json_block(output, VERDICT_PATTERN)
        if data is None:
            return None

        validate_required_fields(data, VERDICT_REQUIRED_FIELDS)

        return StructuredVerdict(
            schema_version=data["schema_version"],
            sprint=data["sprint"],
            session=data["session"],
            verdict=data["verdict"],
            findings=data["findings"],
            spec_conformance=data["spec_conformance"],
            files_reviewed=data["files_reviewed"],
            tests_verified=data["tests_verified"],
            raw=data,
        )

    def classify_failure(self, output: str) -> str:
        """Classify a failure as transient or LLM-compliance.

        Per DEC-286/295: If prose close-out exists but no JSON block,
        the implementation likely completed but the LLM failed to include
        the structured appendix. Otherwise, it's a transient failure
        (network, timeout, etc.).

        Args:
            output: The session output.

        Returns:
            "llm_compliance" if prose close-out exists without JSON block.
            "transient" otherwise.
        """
        has_prose = PROSE_CLOSEOUT_MARKER in output
        has_json = CLOSEOUT_PATTERN.search(output) is not None

        if has_prose and not has_json:
            return "llm_compliance"
        return "transient"


# ---------------------------------------------------------------------------
# Retry Logic
# ---------------------------------------------------------------------------

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int,
    base_delay: float,
    on_retry: Callable[[int, Exception], None] | None = None,
) -> T:
    """Execute a function with exponential backoff retry.

    Delay formula: base_delay × 4^attempt (30s, 120s for default base_delay=30).

    Args:
        func: The function to execute (can be sync or async).
        max_retries: Maximum number of retries (0 = no retries, just one attempt).
        base_delay: Base delay in seconds before first retry.
        on_retry: Optional callback called before each retry with (attempt, exception).

    Returns:
        The result of the function.

    Raises:
        RetryExhaustedError: If all retries fail.
        Exception: The last exception if retries exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            last_exception = e

            if attempt < max_retries:
                delay = base_delay * (4**attempt)
                if on_retry:
                    on_retry(attempt, e)
                await asyncio.sleep(delay)
            else:
                raise RetryExhaustedError(
                    f"Exhausted {max_retries} retries. Last error: {e}"
                ) from e

    # Should not reach here, but satisfy type checker
    raise RetryExhaustedError(
        f"Exhausted {max_retries} retries. Last error: {last_exception}"
    )


def prepend_reinforcement_instruction(prompt: str) -> str:
    """Prepend reinforcement instruction for LLM-compliance retry.

    Args:
        prompt: The original prompt.

    Returns:
        Prompt with reinforcement instruction prepended.
    """
    reinforcement = (
        "IMPORTANT: You MUST include the structured close-out JSON appendix "
        "at the end of your response, formatted as a ```json:structured-closeout "
        "code block. This is a critical requirement for automated processing.\n\n"
    )
    return reinforcement + prompt


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: The content to hash.

    Returns:
        Hex digest of SHA-256 hash.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
