"""Tests for spec conformance check module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.sprint_runner.config import ConformanceConfig, ExecutionConfig
from scripts.sprint_runner.conformance import (
    ConformanceChecker,
    ConformanceVerdict,
    ConformanceFinding,
    FileScopeCheck,
    SpecContradictionCheck,
    IntegrationCheck,
    _extract_conformance_verdict,
    _parse_conformance_verdict,
    _summarize_large_diff,
    MAX_DIFF_SIZE_BYTES,
)
from scripts.sprint_runner.executor import ClaudeCodeExecutor, ExecutionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conformance_config() -> ConformanceConfig:
    """Create a test conformance config."""
    return ConformanceConfig(
        enabled=True,
        prompt_template="docs/protocols/templates/spec-conformance-prompt.md",
        drift_minor_action="warn",
        drift_major_action="halt",
    )


@pytest.fixture
def execution_config() -> ExecutionConfig:
    """Create a test execution config."""
    return ExecutionConfig(
        mode="autonomous",
        max_retries=2,
        retry_delay_seconds=1,
    )


@pytest.fixture
def mock_executor(execution_config: ExecutionConfig) -> ClaudeCodeExecutor:
    """Create a mock executor."""
    executor = ClaudeCodeExecutor(execution_config)
    executor.run_session = AsyncMock()
    return executor


@pytest.fixture
def temp_sprint_dir(tmp_path: Path) -> Path:
    """Create a temporary sprint directory with templates."""
    sprint_dir = tmp_path / "sprint-23"
    sprint_dir.mkdir()

    # Create template
    templates_dir = tmp_path / "docs" / "protocols" / "templates"
    templates_dir.mkdir(parents=True)

    template = """# Spec Conformance Check
    Sprint: {SPRINT}
    Session: {SESSION}
    """
    (templates_dir / "spec-conformance-prompt.md").write_text(template)

    return tmp_path


@pytest.fixture
def conformance_checker(
    mock_executor: ClaudeCodeExecutor,
    conformance_config: ConformanceConfig,
    temp_sprint_dir: Path,
) -> ConformanceChecker:
    """Create a conformance checker for testing."""
    return ConformanceChecker(mock_executor, conformance_config, temp_sprint_dir)


# ---------------------------------------------------------------------------
# Extraction Tests
# ---------------------------------------------------------------------------


class TestConformanceVerdictExtraction:
    """Tests for conformance verdict extraction."""

    def test_extracts_valid_conformance_verdict(self) -> None:
        """Extracts valid conformance verdict JSON block."""
        output = '''
Analysis complete.

```json:conformance-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "cumulative_sessions_checked": ["S1"],
  "verdict": "CONFORMANT",
  "findings": [],
  "file_scope_check": {},
  "spec_by_contradiction_check": {"clean": true},
  "integration_check": {},
  "drift_summary": "All good"
}
```
'''
        result = _extract_conformance_verdict(output)
        assert result is not None
        assert result["verdict"] == "CONFORMANT"

    def test_returns_none_when_block_missing(self) -> None:
        """Returns None when no conformance verdict block found."""
        output = "Just some regular output."
        result = _extract_conformance_verdict(output)
        assert result is None


class TestParseConformanceVerdict:
    """Tests for conformance verdict parsing."""

    def test_parses_full_verdict(self) -> None:
        """Parses a complete conformance verdict."""
        data = {
            "schema_version": "1.0",
            "sprint": "23",
            "session": "S1",
            "cumulative_sessions_checked": ["S1"],
            "verdict": "DRIFT-MINOR",
            "findings": [
                {
                    "type": "NAMING",
                    "severity": "LOW",
                    "description": "Inconsistent naming",
                    "details": "foo vs bar",
                }
            ],
            "file_scope_check": {
                "unexpected_files_created": ["extra.py"],
                "unexpected_files_modified": [],
                "expected_files_missing": [],
            },
            "spec_by_contradiction_check": {"violations": [], "clean": True},
            "integration_check": {
                "verified": ["S1 integrated"],
                "missing": [],
                "not_yet_due": [],
            },
            "drift_summary": "Minor naming issue",
        }

        result = _parse_conformance_verdict(data)

        assert isinstance(result, ConformanceVerdict)
        assert result.verdict == "DRIFT-MINOR"
        assert len(result.findings) == 1
        assert result.findings[0].finding_type == "NAMING"
        assert len(result.file_scope_check.unexpected_files_created) == 1


class TestLargeDiffSummary:
    """Tests for large diff summarization."""

    def test_summarizes_large_diff(self) -> None:
        """Large diffs are summarized at file level."""
        large_diff = "+" * 100000 + "\n" + "-" * 50000
        files_created = ["new_file.py"]
        files_modified = ["existing.py"]

        summary = _summarize_large_diff(large_diff, files_created, files_modified)

        assert "[DIFF SUMMARIZED" in summary
        assert "new_file.py" in summary
        assert "existing.py" in summary
        assert "additions" in summary
        assert "deletions" in summary


# ---------------------------------------------------------------------------
# Conformance Checker Tests
# ---------------------------------------------------------------------------


class TestConformanceChecker:
    """Tests for ConformanceChecker."""

    @pytest.mark.asyncio
    async def test_conformant_verdict_routing(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """CONFORMANT verdict routes correctly."""
        mock_output = '''
```json:conformance-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "cumulative_sessions_checked": ["S1"],
  "verdict": "CONFORMANT",
  "findings": [],
  "file_scope_check": {},
  "spec_by_contradiction_check": {"clean": true},
  "integration_check": {},
  "drift_summary": "All conformant"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert not conformance_checker.should_halt(result)

    @pytest.mark.asyncio
    async def test_drift_minor_verdict_routing(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """DRIFT-MINOR verdict routes correctly (warn by default)."""
        mock_output = '''
```json:conformance-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "cumulative_sessions_checked": ["S1"],
  "verdict": "DRIFT-MINOR",
  "findings": [{"type": "NAMING", "severity": "LOW", "description": "Minor issue"}],
  "file_scope_check": {},
  "spec_by_contradiction_check": {"clean": true},
  "integration_check": {},
  "drift_summary": "Minor drift"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "DRIFT-MINOR"
        # Default config is drift_minor_action="warn", so should not halt
        assert not conformance_checker.should_halt(result)

    @pytest.mark.asyncio
    async def test_drift_major_verdict_routing(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """DRIFT-MAJOR verdict routes correctly (halt)."""
        mock_output = '''
```json:conformance-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "cumulative_sessions_checked": ["S1"],
  "verdict": "DRIFT-MAJOR",
  "findings": [{"type": "SPEC_CONTRADICTION", "severity": "HIGH", "description": "Major issue"}],
  "file_scope_check": {},
  "spec_by_contradiction_check": {"violations": ["Modified protected file"], "clean": false},
  "integration_check": {},
  "drift_summary": "Major drift detected"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "DRIFT-MAJOR"
        assert conformance_checker.should_halt(result)

    @pytest.mark.asyncio
    async def test_subagent_failure_returns_conformant(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """Subagent failure returns CONFORMANT (defense-in-depth)."""
        mock_executor.run_session.return_value = ExecutionResult(
            output="No JSON block here", exit_code=0, duration_seconds=1.0, output_size_bytes=20
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert "error" in result.raw

    @pytest.mark.asyncio
    async def test_disabled_returns_conformant(
        self, mock_executor: ClaudeCodeExecutor, temp_sprint_dir: Path
    ) -> None:
        """Disabled conformance check returns CONFORMANT."""
        config = ConformanceConfig(enabled=False)
        checker = ConformanceChecker(mock_executor, config, temp_sprint_dir)

        result = await checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert result.raw.get("disabled") is True
        # Executor should not have been called
        mock_executor.run_session.assert_not_called()


# ---------------------------------------------------------------------------
# Conformance Fallback Tests
# ---------------------------------------------------------------------------


class TestConformanceFallbackFlag:
    """Tests for conformance fallback flag functionality."""

    @pytest.mark.asyncio
    async def test_conformance_fallback_sets_flag_on_parse_failure(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """When conformance check fails to parse verdict, is_fallback is True."""
        mock_executor.run_session.return_value = ExecutionResult(
            output="No JSON block here - unparseable output",
            exit_code=0,
            duration_seconds=1.0,
            output_size_bytes=40
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert result.is_fallback is True
        assert "error" in result.raw

    @pytest.mark.asyncio
    async def test_conformance_fallback_sets_flag_on_exception(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """When conformance check raises exception, is_fallback is True."""
        mock_executor.run_session.side_effect = Exception("Network error")

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert result.is_fallback is True
        assert "error" in result.raw

    @pytest.mark.asyncio
    async def test_successful_conformance_has_fallback_false(
        self, conformance_checker: ConformanceChecker, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """Successful conformance check has is_fallback=False."""
        mock_output = '''
```json:conformance-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "cumulative_sessions_checked": ["S1"],
  "verdict": "CONFORMANT",
  "findings": [],
  "file_scope_check": {},
  "spec_by_contradiction_check": {"clean": true},
  "integration_check": {},
  "drift_summary": "All conformant"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await conformance_checker.check(
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            completed_sessions=["S1"],
            cumulative_files_created=[],
            cumulative_files_modified=[],
            cumulative_diff="",
            current_closeout={},
            sprint="23",
            session="S1",
        )

        assert result.verdict == "CONFORMANT"
        assert result.is_fallback is False

    def test_conformance_verdict_default_is_fallback_false(self) -> None:
        """ConformanceVerdict default is_fallback is False."""
        verdict = ConformanceVerdict(
            schema_version="1.0",
            sprint="23",
            session="S1",
            cumulative_sessions_checked=["S1"],
            verdict="CONFORMANT",
            findings=[],
            file_scope_check=FileScopeCheck(),
            spec_by_contradiction_check=SpecContradictionCheck(),
            integration_check=IntegrationCheck(),
            drift_summary="OK",
        )
        assert verdict.is_fallback is False


class TestConformanceFallbackCount:
    """Tests for conformance fallback count tracking in RunState."""

    def test_conformance_fallback_count_field_exists(self) -> None:
        """RunState has conformance_fallback_count field defaulting to 0."""
        from scripts.sprint_runner.state import GitState, RunState

        state = RunState(
            sprint="23",
            git_state=GitState(branch="main"),
        )
        assert hasattr(state, "conformance_fallback_count")
        assert state.conformance_fallback_count == 0

    def test_conformance_fallback_count_increments(self) -> None:
        """conformance_fallback_count can be incremented."""
        from scripts.sprint_runner.state import GitState, RunState

        state = RunState(
            sprint="23",
            git_state=GitState(branch="main"),
        )

        assert state.conformance_fallback_count == 0
        state.conformance_fallback_count += 1
        assert state.conformance_fallback_count == 1
        state.conformance_fallback_count += 1
        assert state.conformance_fallback_count == 2

    def test_conformance_fallback_count_persists_through_save_load(
        self, tmp_path: Path
    ) -> None:
        """conformance_fallback_count persists through save/load cycle."""
        from scripts.sprint_runner.state import GitState, RunState

        state = RunState(
            sprint="23",
            git_state=GitState(branch="main"),
            conformance_fallback_count=5,
        )

        state_path = tmp_path / "state.json"
        state.save(state_path)

        loaded = RunState.load(state_path)
        assert loaded.conformance_fallback_count == 5


class TestConformanceFallbackWarningThreshold:
    """Tests for conformance fallback warning threshold behavior."""

    def test_conformance_fallback_warning_threshold_not_triggered_at_2(
        self, capsys, tmp_path: Path
    ) -> None:
        """Warning is NOT logged when count is 2 or less."""
        from scripts.sprint_runner.state import GitState, RunState
        from scripts.sprint_runner.main import SprintRunner
        from scripts.sprint_runner.config import (
            RunnerConfig, SprintConfig, ExecutionConfig, GitConfig,
            NotificationsConfig, CostConfig,
        )

        # Create minimal config
        sprint_dir = tmp_path / "sprint-23"
        sprint_dir.mkdir()

        config = RunnerConfig(
            sprint=SprintConfig(directory=str(sprint_dir), session_order=[]),
            execution=ExecutionConfig(mode="autonomous"),
            git=GitConfig(branch="sprint-23"),
            notifications=NotificationsConfig(),
            cost=CostConfig(),
        )

        runner = SprintRunner(config, tmp_path)
        runner.state = RunState(
            sprint="23",
            git_state=GitState(branch="sprint-23"),
            conformance_fallback_count=2,
        )

        runner._check_conformance_fallback_warning()

        captured = capsys.readouterr()
        assert "Conformance check defaulted to CONFORMANT" not in captured.out

    def test_conformance_fallback_warning_triggered_at_3(
        self, capsys, tmp_path: Path
    ) -> None:
        """Warning IS logged when count exceeds 2."""
        from scripts.sprint_runner.state import GitState, RunState
        from scripts.sprint_runner.main import SprintRunner
        from scripts.sprint_runner.config import (
            RunnerConfig, SprintConfig, ExecutionConfig, GitConfig,
            NotificationsConfig, CostConfig,
        )

        # Create minimal config
        sprint_dir = tmp_path / "sprint-23"
        sprint_dir.mkdir()

        config = RunnerConfig(
            sprint=SprintConfig(directory=str(sprint_dir), session_order=[]),
            execution=ExecutionConfig(mode="autonomous"),
            git=GitConfig(branch="sprint-23"),
            notifications=NotificationsConfig(),
            cost=CostConfig(),
        )

        runner = SprintRunner(config, tmp_path)
        runner.state = RunState(
            sprint="23",
            git_state=GitState(branch="sprint-23"),
            conformance_fallback_count=3,
        )

        runner._check_conformance_fallback_warning()

        captured = capsys.readouterr()
        assert "Conformance check defaulted to CONFORMANT 3 times" in captured.out
        assert "conformance subagent reliability" in captured.out
