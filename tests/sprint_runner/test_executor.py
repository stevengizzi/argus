"""Tests for the Claude Code CLI executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.sprint_runner.config import ExecutionConfig
from scripts.sprint_runner.executor import (
    CLOSEOUT_PATTERN,
    VERDICT_PATTERN,
    ClaudeCodeExecutor,
    CLITimeoutError,
    ExecutionResult,
    RetryExhaustedError,
    StructuredCloseout,
    StructuredVerdict,
    ValidationError,
    compute_content_hash,
    extract_json_block,
    prepend_reinforcement_instruction,
    retry_with_backoff,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def execution_config() -> ExecutionConfig:
    """Create a test execution config."""
    return ExecutionConfig(
        mode="autonomous",
        max_retries=2,
        retry_delay_seconds=1,  # Short for tests
        session_timeout_seconds=30,
        compaction_threshold_bytes=1000,  # Low for testing
    )


@pytest.fixture
def executor(execution_config: ExecutionConfig) -> ClaudeCodeExecutor:
    """Create a test executor."""
    return ClaudeCodeExecutor(execution_config)


# ---------------------------------------------------------------------------
# JSON Block Extraction Tests
# ---------------------------------------------------------------------------


class TestExtractJsonBlock:
    """Tests for JSON block extraction."""

    def test_extract_valid_closeout_block(self) -> None:
        """Extracts valid structured-closeout JSON block."""
        output = '''
Some prose output here.

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "verdict": "COMPLETE"
}
```

More text after.
'''
        result = extract_json_block(output, CLOSEOUT_PATTERN)
        assert result is not None
        assert result["schema_version"] == "1.0"
        assert result["sprint"] == "23"
        assert result["verdict"] == "COMPLETE"

    def test_extract_valid_verdict_block(self) -> None:
        """Extracts valid structured-verdict JSON block."""
        output = '''
Review output.

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "verdict": "CLEAR"
}
```
'''
        result = extract_json_block(output, VERDICT_PATTERN)
        assert result is not None
        assert result["verdict"] == "CLEAR"

    def test_returns_none_when_block_missing(self) -> None:
        """Returns None when no JSON block is found."""
        output = "Just some regular output without any JSON blocks."
        result = extract_json_block(output, CLOSEOUT_PATTERN)
        assert result is None

    def test_raises_on_malformed_json(self) -> None:
        """Raises ValidationError for malformed JSON."""
        output = '''
```json:structured-closeout
{
  "schema_version": "1.0",
  "invalid json here
}
```
'''
        with pytest.raises(ValidationError, match="Invalid JSON"):
            extract_json_block(output, CLOSEOUT_PATTERN)


# ---------------------------------------------------------------------------
# Executor Tests
# ---------------------------------------------------------------------------


class TestClaudeCodeExecutor:
    """Tests for ClaudeCodeExecutor."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_mock_result(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Dry run returns mock result without invoking subprocess."""
        result = await executor.run_session("test prompt", dry_run=True)

        assert isinstance(result, ExecutionResult)
        assert "[DRY RUN]" in result.output
        assert result.exit_code == 0
        assert result.duration_seconds == 0.0
        assert not result.compaction_likely

    @pytest.mark.asyncio
    async def test_cli_success_captures_output(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Successful CLI invocation captures stdout."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"test output", b""))
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch("scripts.sprint_runner.executor.asyncio.create_subprocess_exec") as mock_exec:
            # Return the mock process directly (AsyncMock handles awaiting)
            mock_exec.return_value = mock_process
            executor._cli_verified = True  # Skip version check

            result = await executor.run_session("test prompt")

        assert result.output == "test output"
        assert result.exit_code == 0
        assert result.output_size_bytes == len(b"test output")

    @pytest.mark.asyncio
    async def test_cli_timeout_raises_error(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """CLI timeout raises CLITimeoutError."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=TimeoutError())
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch("scripts.sprint_runner.executor.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_process
            executor._cli_verified = True

            with pytest.raises(CLITimeoutError, match="timed out"):
                await executor.run_session("test prompt", timeout=1)

    @pytest.mark.asyncio
    async def test_compaction_detection_when_output_large(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Detects compaction when output exceeds threshold."""
        large_output = "x" * 2000  # Exceeds 1000 byte threshold

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(large_output.encode(), b""))
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch("scripts.sprint_runner.executor.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_process
            executor._cli_verified = True

            result = await executor.run_session("test prompt")

        assert result.compaction_likely is True
        assert result.output_size_bytes == 2000


# ---------------------------------------------------------------------------
# Structured Extraction Tests
# ---------------------------------------------------------------------------


class TestStructuredExtraction:
    """Tests for structured output extraction methods."""

    def test_extract_structured_closeout_valid(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Extracts and parses valid structured closeout."""
        output = '''
Session output...

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {"before": 100, "after": 110, "new": 10, "all_pass": true},
  "files_created": ["file1.py"],
  "files_modified": ["file2.py"],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": []
}
```
'''
        result = executor.extract_structured_closeout(output)

        assert result is not None
        assert isinstance(result, StructuredCloseout)
        assert result.sprint == "23"
        assert result.session == "S1"
        assert result.verdict == "COMPLETE"
        assert result.tests["all_pass"] is True
        assert "file1.py" in result.files_created

    def test_extract_structured_closeout_missing_fields(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Raises ValidationError when required fields missing."""
        output = '''
```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "23"
}
```
'''
        with pytest.raises(ValidationError, match="Missing required fields"):
            executor.extract_structured_closeout(output)

    def test_extract_structured_verdict_valid(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Extracts and parses valid structured verdict."""
        output = '''
```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "verdict": "CLEAR",
  "findings": [],
  "spec_conformance": {"status": "CONFORMANT", "notes": ""},
  "files_reviewed": ["file.py"],
  "tests_verified": {"all_pass": true, "count": 100}
}
```
'''
        result = executor.extract_structured_verdict(output)

        assert result is not None
        assert isinstance(result, StructuredVerdict)
        assert result.verdict == "CLEAR"
        assert result.spec_conformance["status"] == "CONFORMANT"


# ---------------------------------------------------------------------------
# Failure Classification Tests
# ---------------------------------------------------------------------------


class TestFailureClassification:
    """Tests for failure classification."""

    def test_llm_compliance_when_prose_exists_without_json(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Classifies as llm_compliance when prose closeout exists but no JSON."""
        output = '''
Some output...

---BEGIN-CLOSE-OUT---
Implementation completed successfully...
---END-CLOSE-OUT---

(but no JSON block)
'''
        result = executor.classify_failure(output)
        assert result == "llm_compliance"

    def test_transient_when_no_closeout_at_all(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Classifies as transient when no closeout markers present."""
        output = "Error: Connection reset\nNo output generated."

        result = executor.classify_failure(output)
        assert result == "transient"

    def test_transient_when_both_prose_and_json_exist(
        self, executor: ClaudeCodeExecutor
    ) -> None:
        """Classifies as transient when both exist (JSON extraction should work)."""
        output = '''
---BEGIN-CLOSE-OUT---
Implementation completed.
---END-CLOSE-OUT---

```json:structured-closeout
{"schema_version": "1.0"}
```
'''
        # This is actually "transient" because both exist (not an LLM compliance failure)
        result = executor.classify_failure(output)
        assert result == "transient"


# ---------------------------------------------------------------------------
# Retry Logic Tests
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self) -> None:
        """Returns immediately on successful first attempt."""
        call_count = 0

        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(success_func, max_retries=2, base_delay=0.01)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self) -> None:
        """Retries when function fails."""
        call_count = 0

        def failing_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary failure")
            return "success"

        result = await retry_with_backoff(
            failing_then_success, max_retries=2, base_delay=0.01
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_retry_exhausted_after_max_retries(self) -> None:
        """Raises RetryExhaustedError when all retries fail."""
        call_count = 0

        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent failure")

        with pytest.raises(RetryExhaustedError, match="Exhausted 2 retries"):
            await retry_with_backoff(always_fails, max_retries=2, base_delay=0.01)

        assert call_count == 3  # Initial attempt + 2 retries


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_prepend_reinforcement_instruction(self) -> None:
        """Adds reinforcement instruction to prompt."""
        original = "Original prompt here."
        result = prepend_reinforcement_instruction(original)

        assert "IMPORTANT:" in result
        assert "structured close-out JSON" in result
        assert result.endswith(original)

    def test_compute_content_hash(self) -> None:
        """Computes SHA-256 hash of content."""
        content = "test content"
        result = compute_content_hash(content)

        # Verify it's a valid hex SHA-256 (64 characters)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

        # Same content produces same hash
        assert compute_content_hash(content) == result

        # Different content produces different hash
        assert compute_content_hash("other content") != result
