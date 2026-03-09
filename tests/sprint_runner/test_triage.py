"""Tests for Tier 2.5 triage module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.sprint_runner.config import ExecutionConfig, TriageConfig
from scripts.sprint_runner.executor import ClaudeCodeExecutor, ExecutionResult
from scripts.sprint_runner.state import RunState, SessionPlanEntry, SessionPlanStatus
from scripts.sprint_runner.triage import (
    TriageManager,
    TriageVerdict,
    TriageIssue,
    FixSession,
    _extract_triage_verdict,
    _parse_triage_verdict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def triage_config() -> TriageConfig:
    """Create a test triage config."""
    return TriageConfig(
        enabled=True,
        prompt_template="docs/protocols/templates/tier-2.5-triage-prompt.md",
        auto_insert_fixes=True,
        max_auto_fixes=3,
        fix_prompt_template="docs/protocols/templates/fix-prompt.md",
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

    # Create templates
    templates_dir = tmp_path / "docs" / "protocols" / "templates"
    templates_dir.mkdir(parents=True)

    triage_template = """# Tier 2.5 Triage
    Sprint: {SPRINT}
    Session: {SESSION}
    """
    (templates_dir / "tier-2.5-triage-prompt.md").write_text(triage_template)

    fix_template = """# Fix Session {FIX_ID}
    Sprint: {SPRINT}
    """
    (templates_dir / "fix-prompt.md").write_text(fix_template)

    return tmp_path


@pytest.fixture
def triage_manager(
    mock_executor: ClaudeCodeExecutor,
    triage_config: TriageConfig,
    temp_sprint_dir: Path,
) -> TriageManager:
    """Create a triage manager for testing."""
    return TriageManager(mock_executor, triage_config, temp_sprint_dir)


# ---------------------------------------------------------------------------
# Extraction Tests
# ---------------------------------------------------------------------------


class TestTriageVerdictExtraction:
    """Tests for triage verdict extraction."""

    def test_extracts_valid_triage_verdict(self) -> None:
        """Extracts valid triage verdict JSON block."""
        output = '''
Analysis complete.

```json:triage-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "issues": [],
  "overall_recommendation": "PROCEED"
}
```
'''
        result = _extract_triage_verdict(output)
        assert result is not None
        assert result["overall_recommendation"] == "PROCEED"

    def test_returns_none_when_block_missing(self) -> None:
        """Returns None when no triage verdict block found."""
        output = "Just some regular output."
        result = _extract_triage_verdict(output)
        assert result is None

    def test_returns_none_on_malformed_json(self) -> None:
        """Returns None for malformed JSON."""
        output = '''
```json:triage-verdict
{invalid json}
```
'''
        result = _extract_triage_verdict(output)
        assert result is None


class TestParseTriageVerdict:
    """Tests for triage verdict parsing."""

    def test_parses_full_verdict(self) -> None:
        """Parses a complete triage verdict."""
        data = {
            "schema_version": "1.0",
            "sprint": "23",
            "session": "S1",
            "issues": [
                {
                    "description": "Test issue",
                    "source": "scope_gap",
                    "category": "CAT_3_SMALL",
                    "action": "INSERT_FIX",
                    "rationale": "Minor gap",
                    "fix_description": "Add missing test",
                }
            ],
            "overall_recommendation": "INSERT_FIXES_THEN_PROCEED",
            "fix_sessions_needed": [
                {
                    "fix_id": "S1-fix-1",
                    "description": "Add test",
                    "insert_before": "S2",
                    "scope": "test only",
                    "affected_files": ["test_foo.py"],
                }
            ],
            "deferred_items": [],
        }

        result = _parse_triage_verdict(data)

        assert isinstance(result, TriageVerdict)
        assert result.sprint == "23"
        assert result.overall_recommendation == "INSERT_FIXES_THEN_PROCEED"
        assert len(result.issues) == 1
        assert result.issues[0].category == "CAT_3_SMALL"
        assert len(result.fix_sessions_needed) == 1
        assert result.fix_sessions_needed[0].fix_id == "S1-fix-1"


# ---------------------------------------------------------------------------
# Triage Manager Tests
# ---------------------------------------------------------------------------


class TestTriageManager:
    """Tests for TriageManager."""

    @pytest.mark.asyncio
    async def test_insert_fix_routes_on_verdict(
        self, triage_manager: TriageManager, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """INSERT_FIX action routes correctly."""
        mock_output = '''
```json:triage-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "issues": [{"description": "Bug", "source": "scope_gap", "category": "CAT_1", "action": "INSERT_FIX", "rationale": "Fix needed"}],
  "overall_recommendation": "INSERT_FIXES_THEN_PROCEED",
  "fix_sessions_needed": [{"fix_id": "S1-fix-1", "description": "Fix bug"}]
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await triage_manager.run_triage(
            closeout={},
            verdict=None,
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            sprint="23",
            session="S1",
        )

        assert result.overall_recommendation == "INSERT_FIXES_THEN_PROCEED"
        assert len(result.fix_sessions_needed) == 1

    @pytest.mark.asyncio
    async def test_defer_routes_on_verdict(
        self, triage_manager: TriageManager, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """DEFER action routes correctly."""
        mock_output = '''
```json:triage-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "issues": [{"description": "Feature idea", "source": "scope_gap", "category": "CAT_4", "action": "DEFER", "rationale": "Not needed now", "defer_target": "Sprint 23.1"}],
  "overall_recommendation": "PROCEED",
  "deferred_items": [{"description": "Feature idea", "target": "Sprint 23.1", "def_entry_needed": false}]
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await triage_manager.run_triage(
            closeout={},
            verdict=None,
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            sprint="23",
            session="S1",
        )

        assert result.overall_recommendation == "PROCEED"
        assert len(result.deferred_items) == 1

    @pytest.mark.asyncio
    async def test_halt_routes_on_verdict(
        self, triage_manager: TriageManager, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """HALT action routes correctly."""
        mock_output = '''
```json:triage-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "issues": [{"description": "Major gap", "source": "scope_gap", "category": "CAT_3_SUBSTANTIAL", "action": "HALT", "rationale": "Too big for auto-fix"}],
  "overall_recommendation": "HALT"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await triage_manager.run_triage(
            closeout={},
            verdict=None,
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            sprint="23",
            session="S1",
        )

        assert result.overall_recommendation == "HALT"

    @pytest.mark.asyncio
    async def test_log_warning_routes_on_verdict(
        self, triage_manager: TriageManager, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """LOG_WARNING action routes correctly."""
        mock_output = '''
```json:triage-verdict
{
  "schema_version": "1.0",
  "sprint": "23",
  "session": "S1",
  "issues": [{"description": "Minor concern", "source": "review_finding", "category": "CAT_4", "action": "LOG_WARNING", "rationale": "Low severity"}],
  "overall_recommendation": "PROCEED"
}
```
'''
        mock_executor.run_session.return_value = ExecutionResult(
            output=mock_output, exit_code=0, duration_seconds=1.0, output_size_bytes=len(mock_output)
        )

        result = await triage_manager.run_triage(
            closeout={},
            verdict=None,
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            sprint="23",
            session="S1",
        )

        assert result.overall_recommendation == "PROCEED"
        assert len(result.issues) == 1
        assert result.issues[0].action == "LOG_WARNING"

    @pytest.mark.asyncio
    async def test_subagent_failure_returns_halt(
        self, triage_manager: TriageManager, mock_executor: ClaudeCodeExecutor
    ) -> None:
        """Subagent failure (no parseable verdict) returns HALT."""
        mock_executor.run_session.return_value = ExecutionResult(
            output="No JSON block here", exit_code=0, duration_seconds=1.0, output_size_bytes=20
        )

        result = await triage_manager.run_triage(
            closeout={},
            verdict=None,
            sprint_spec="",
            spec_by_contradiction="",
            session_breakdown="",
            sprint="23",
            session="S1",
        )

        assert result.overall_recommendation == "HALT"
        assert "error" in result.raw

    def test_max_auto_fixes_check(self, triage_manager: TriageManager) -> None:
        """Max auto-fixes limit is enforced."""
        # Insert 3 fix sessions (max)
        triage_manager._fix_sessions_inserted = 3

        assert triage_manager.check_max_auto_fixes_exceeded() is True

        # Reset and check again
        triage_manager.reset_fix_count()
        assert triage_manager.check_max_auto_fixes_exceeded() is False

    def test_fix_insertion_into_plan(
        self, triage_manager: TriageManager, temp_sprint_dir: Path
    ) -> None:
        """Fix sessions are inserted into the session plan."""
        # Create a mock run state
        from scripts.sprint_runner.config import GitConfig, RunnerConfig, SprintConfig
        from scripts.sprint_runner.state import GitState

        run_state = RunState(
            sprint="23",
            session_plan=[
                SessionPlanEntry(session_id="S1", title="Session 1"),
                SessionPlanEntry(session_id="S2", title="Session 2"),
            ],
            git_state=GitState(branch="main"),
        )

        triage_verdict = TriageVerdict(
            schema_version="1.0",
            sprint="23",
            session="S1",
            issues=[],
            overall_recommendation="INSERT_FIXES_THEN_PROCEED",
            fix_sessions_needed=[
                FixSession(
                    fix_id="S1-fix-1",
                    description="Fix issue",
                    insert_before="S2",
                    scope="Fix scope",
                    affected_files=["test.py"],
                )
            ],
        )

        inserted = triage_manager.insert_fix_sessions(
            triage_verdict, run_state, "S1", temp_sprint_dir / "sprint-23"
        )

        assert len(inserted) == 1
        assert inserted[0] == "S1-fix-1"
        assert len(run_state.session_plan) == 3
        assert run_state.session_plan[1].session_id == "S1-fix-1"
        assert run_state.session_plan[1].status == SessionPlanStatus.INSERTED
        assert run_state.session_plan[1].inserted_by == "S1"
