"""Tests for sprint runner state management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sprint_runner.config import RunnerConfig
from scripts.sprint_runner.state import (
    GitState,
    ReviewVerdict,
    RunPhase,
    RunState,
    RunStatus,
    SessionPlanEntry,
    SessionPlanStatus,
    SessionResult,
)


class TestRunState:
    """Tests for RunState."""

    def test_create_initial_state(self, valid_config_file: Path) -> None:
        """Test creating initial state from config."""
        config = RunnerConfig.from_yaml(str(valid_config_file))
        state = RunState.create_initial(config)

        assert state.status == RunStatus.NOT_STARTED
        assert state.sprint == "23.5"
        assert state.mode == "autonomous"
        assert len(state.session_plan) == 2
        assert state.session_plan[0].session_id == "S1"
        assert state.session_plan[1].session_id == "S2"
        assert state.cost.ceiling_usd == 25.0
        assert state.timestamps.run_started != ""

    def test_save_and_load_state(self, temp_dir: Path) -> None:
        """Test atomic save and load of state."""
        state = RunState(
            sprint="23",
            mode="autonomous",
            status=RunStatus.RUNNING,
            current_session="S1",
            current_phase=RunPhase.IMPLEMENTATION,
            git_state=GitState(branch="sprint-23", sprint_start_sha="abc123"),
        )

        state_path = temp_dir / "run-state.json"
        state.save(state_path)

        assert state_path.exists()
        assert not (temp_dir / "run-state.json.tmp").exists()  # Temp file cleaned up

        loaded = RunState.load(state_path)
        assert loaded.sprint == "23"
        assert loaded.status == RunStatus.RUNNING
        assert loaded.current_session == "S1"
        assert loaded.current_phase == RunPhase.IMPLEMENTATION

    def test_atomic_write_creates_temp_file(self, temp_dir: Path) -> None:
        """Test that atomic write uses temp file."""
        state = RunState(
            sprint="23",
            git_state=GitState(branch="main"),
        )

        state_path = temp_dir / "test-state.json"
        state.save(state_path)

        # Temp file should not exist after successful save
        assert not state_path.with_suffix(".json.tmp").exists()
        assert state_path.exists()

    def test_load_nonexistent_file(self, temp_dir: Path) -> None:
        """Test loading non-existent state file."""
        with pytest.raises(FileNotFoundError):
            RunState.load(temp_dir / "nonexistent.json")

    def test_load_invalid_schema_version(self, temp_dir: Path) -> None:
        """Test loading state with invalid schema version."""
        state_path = temp_dir / "invalid-version.json"
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": "2.0",  # Invalid
                    "sprint": "23",
                    "mode": "autonomous",
                    "status": "NOT_STARTED",
                    "git_state": {"branch": "main"},
                }
            )
        )

        with pytest.raises(ValueError, match="Unsupported schema version"):
            RunState.load(state_path)

    def test_status_transitions(self) -> None:
        """Test valid status transitions."""
        state = RunState(
            sprint="23",
            status=RunStatus.NOT_STARTED,
            git_state=GitState(branch="main"),
        )
        assert state.status == RunStatus.NOT_STARTED

        state.status = RunStatus.RUNNING
        assert state.status == RunStatus.RUNNING

        state.status = RunStatus.HALTED
        state.halt_reason = "Test halt"
        assert state.status == RunStatus.HALTED
        assert state.halt_reason == "Test halt"


class TestSessionResult:
    """Tests for SessionResult."""

    def test_review_verdict_string_assignment_is_coerced_to_enum(self) -> None:
        """Raw string assignments (from parsed review payloads) must coerce."""
        result = SessionResult()
        result.review_verdict = "CLEAR"  # type: ignore[assignment]

        assert isinstance(result.review_verdict, ReviewVerdict)
        assert result.review_verdict is ReviewVerdict.CLEAR

    def test_model_dump_json_emits_no_serializer_warning(self) -> None:
        """Serializing a string-assigned verdict must not warn (DEF-034)."""
        import warnings

        result = SessionResult()
        result.review_verdict = "CLEAR"  # type: ignore[assignment]

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            payload = result.model_dump_json()

        serializer_warnings = [
            w for w in captured if "Pydantic serializer" in str(w.message)
        ]
        assert serializer_warnings == [], serializer_warnings
        assert '"review_verdict":"CLEAR"' in payload


class TestSessionPlanEntry:
    """Tests for SessionPlanEntry."""

    def test_default_values(self) -> None:
        """Test default values for session plan entry."""
        entry = SessionPlanEntry(session_id="S1", title="Test Session")

        assert entry.status == SessionPlanStatus.PENDING
        assert entry.depends_on == []
        assert entry.parallelizable is False
        assert entry.inserted_by is None

    def test_with_dependencies(self) -> None:
        """Test session with dependencies."""
        entry = SessionPlanEntry(
            session_id="S2",
            title="Dependent Session",
            depends_on=["S1"],
            parallelizable=False,
        )

        assert entry.depends_on == ["S1"]
