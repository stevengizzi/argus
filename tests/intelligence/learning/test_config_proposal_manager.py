"""Tests for ConfigProposalManager.

Sprint 28, Session 4.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.learning.config_proposal_manager import (
    ConfigProposalManager,
)
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfigProposal,
    LearningLoopConfig,
)
from argus.intelligence.quality_engine import load_quality_engine_config


# --- Fixtures ---


@pytest.fixture()
def qe_yaml_path(tmp_path: Path) -> str:
    """Create a temporary quality_engine.yaml with valid defaults."""
    yaml_data = {
        "enabled": True,
        "weights": {
            "pattern_strength": 0.30,
            "catalyst_quality": 0.25,
            "volume_profile": 0.20,
            "historical_match": 0.15,
            "regime_alignment": 0.10,
        },
        "thresholds": {
            "a_plus": 90,
            "a": 80,
            "a_minus": 70,
            "b_plus": 60,
            "b": 50,
            "b_minus": 40,
            "c_plus": 30,
        },
        "risk_tiers": {
            "a_plus": [0.02, 0.03],
            "a": [0.015, 0.02],
            "a_minus": [0.01, 0.015],
            "b_plus": [0.0075, 0.01],
            "b": [0.005, 0.0075],
            "b_minus": [0.0025, 0.005],
            "c_plus": [0.0025, 0.0025],
        },
        "min_grade_to_trade": "C+",
    }
    path = tmp_path / "quality_engine.yaml"
    path.write_text(yaml.safe_dump(yaml_data, default_flow_style=False, sort_keys=False))
    return str(path)


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Return a temp DB path."""
    return str(tmp_path / "learning.db")


@pytest.fixture()
async def store(db_path: str) -> LearningStore:
    """Initialize a LearningStore."""
    s = LearningStore(db_path=db_path)
    await s.initialize()
    return s


@pytest.fixture()
def ll_config() -> LearningLoopConfig:
    """Default LearningLoopConfig."""
    return LearningLoopConfig()


@pytest.fixture()
async def manager(
    ll_config: LearningLoopConfig,
    store: LearningStore,
    qe_yaml_path: str,
) -> ConfigProposalManager:
    """Create a ConfigProposalManager with temp files."""
    return ConfigProposalManager(
        config=ll_config,
        store=store,
        quality_engine_yaml_path=qe_yaml_path,
    )


def _make_proposal(
    proposal_id: str = "prop-001",
    field_path: str = "weights.pattern_strength",
    current_value: float = 0.30,
    proposed_value: float = 0.35,
    status: str = "APPROVED",
    report_id: str = "rpt-001",
) -> ConfigProposal:
    """Create a ConfigProposal for testing."""
    now = datetime.now(UTC)
    return ConfigProposal(
        proposal_id=proposal_id,
        report_id=report_id,
        field_path=field_path,
        current_value=current_value,
        proposed_value=proposed_value,
        rationale="Test proposal",
        status=status,
        created_at=now,
        updated_at=now,
    )


# --- Tests ---


@pytest.mark.asyncio
async def test_apply_pending_single_proposal(
    manager: ConfigProposalManager,
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """apply_pending applies a single APPROVED proposal and updates YAML."""
    proposal = _make_proposal()
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-001", "APPROVED")

    applied = await manager.apply_pending()

    assert applied == ["prop-001"]

    # Verify YAML was updated
    raw = yaml.safe_load(Path(qe_yaml_path).read_text())
    assert raw["weights"]["pattern_strength"] == pytest.approx(0.35, abs=0.001)

    # Other weights should be redistributed to sum to 1.0
    total = sum(raw["weights"].values())
    assert total == pytest.approx(1.0, abs=0.001)


@pytest.mark.asyncio
async def test_apply_pending_multiple_proposals(
    manager: ConfigProposalManager,
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """apply_pending applies multiple APPROVED proposals sequentially."""
    p1 = _make_proposal(
        proposal_id="prop-001",
        field_path="weights.pattern_strength",
        current_value=0.30,
        proposed_value=0.35,
    )
    p2 = _make_proposal(
        proposal_id="prop-002",
        field_path="weights.catalyst_quality",
        current_value=0.25,
        proposed_value=0.20,
    )
    await store.save_proposal(p1)
    await store.update_proposal_status("prop-001", "APPROVED")
    await store.save_proposal(p2)
    await store.update_proposal_status("prop-002", "APPROVED")

    applied = await manager.apply_pending()

    assert len(applied) == 2
    assert "prop-001" in applied
    assert "prop-002" in applied


@pytest.mark.asyncio
async def test_cumulative_drift_guard_stops_at_limit(
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """Cumulative drift guard prevents proposals that exceed max_cumulative_drift."""
    config = LearningLoopConfig(max_cumulative_drift=0.10)
    mgr = ConfigProposalManager(
        config=config,
        store=store,
        quality_engine_yaml_path=qe_yaml_path,
    )

    # Record a prior change of 0.08 drift
    await store.record_change(
        field_path="weights.pattern_strength",
        old_value=0.30,
        new_value=0.38,
        source="learning_loop",
    )

    # New proposal would add 0.05 more drift → 0.13 > 0.10 limit
    proposal = _make_proposal(
        proposal_id="prop-drift",
        field_path="weights.pattern_strength",
        current_value=0.38,
        proposed_value=0.43,
    )
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-drift", "APPROVED")

    applied = await mgr.apply_pending()

    # Should NOT be applied due to drift guard
    assert applied == []


@pytest.mark.asyncio
async def test_max_change_per_cycle_rejection(
    manager: ConfigProposalManager,
) -> None:
    """validate_proposal rejects proposals exceeding max_change_per_cycle."""
    proposal = _make_proposal(
        current_value=0.30,
        proposed_value=0.50,  # delta 0.20 > default 0.10
    )

    valid, explanation = manager.validate_proposal(proposal)

    assert not valid
    assert "max_change_per_cycle" in explanation


@pytest.mark.asyncio
async def test_weight_sum_to_one_enforcement(
    manager: ConfigProposalManager,
) -> None:
    """validate_proposal accepts proposals where redistribution is feasible."""
    proposal = _make_proposal(
        current_value=0.30,
        proposed_value=0.35,  # delta 0.05 within limits
    )

    valid, explanation = manager.validate_proposal(proposal)

    assert valid
    assert "passes" in explanation.lower()


@pytest.mark.asyncio
async def test_weight_below_001_rejection(
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """validate_proposal rejects when redistribution pushes any weight below 0.01."""
    # Set up YAML where one other weight is already very small (0.02).
    # If we increase pattern_strength by 0.09, the redistribution of the
    # remaining 0.65 across 4 dims would push regime_alignment (0.02) below 0.01.
    yaml_data = {
        "enabled": True,
        "weights": {
            "pattern_strength": 0.30,
            "catalyst_quality": 0.45,
            "volume_profile": 0.15,
            "historical_match": 0.08,
            "regime_alignment": 0.02,
        },
        "thresholds": {
            "a_plus": 90, "a": 80, "a_minus": 70,
            "b_plus": 60, "b": 50, "b_minus": 40, "c_plus": 30,
        },
        "risk_tiers": {
            "a_plus": [0.02, 0.03], "a": [0.015, 0.02],
            "a_minus": [0.01, 0.015], "b_plus": [0.0075, 0.01],
            "b": [0.005, 0.0075], "b_minus": [0.0025, 0.005],
            "c_plus": [0.0025, 0.0025],
        },
        "min_grade_to_trade": "C+",
    }
    Path(qe_yaml_path).write_text(
        yaml.safe_dump(yaml_data, default_flow_style=False, sort_keys=False)
    )
    config = LearningLoopConfig(max_weight_change_per_cycle=0.50)
    mgr = ConfigProposalManager(
        config=config, store=store, quality_engine_yaml_path=qe_yaml_path,
    )

    # Propose setting pattern_strength to 0.80 (delta 0.50 — at cycle limit)
    # Remaining 0.20 across 4 dims: regime_alignment was 0.02/0.70 * 0.20 ≈ 0.0057 < 0.01
    proposal = _make_proposal(
        current_value=0.30,
        proposed_value=0.80,
    )

    valid, explanation = mgr.validate_proposal(proposal)

    assert not valid
    assert "below 0.01" in explanation


@pytest.mark.asyncio
async def test_pydantic_validation_failure_leaves_yaml_unchanged(
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """When Pydantic validation fails, YAML stays unchanged."""
    config = LearningLoopConfig()
    mgr = ConfigProposalManager(
        config=config,
        store=store,
        quality_engine_yaml_path=qe_yaml_path,
    )

    original = Path(qe_yaml_path).read_text()

    # Proposal that sets a threshold to an invalid value (not a weight)
    proposal = _make_proposal(
        proposal_id="prop-bad",
        field_path="thresholds.a_plus",
        current_value=90.0,
        # Relies on QualityThresholdsConfig validating values in [0, 100] range.
        # If that validator is ever relaxed, this test needs a different invalid value.
        proposed_value=200.0,  # > 100, Pydantic will reject
    )
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-bad", "APPROVED")

    applied = await mgr.apply_pending()

    assert applied == []
    assert Path(qe_yaml_path).read_text() == original


@pytest.mark.asyncio
async def test_atomic_write_creates_backup(
    manager: ConfigProposalManager,
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """Atomic write creates a .bak file before writing."""
    proposal = _make_proposal()
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-001", "APPROVED")

    await manager.apply_pending()

    backup_path = Path(f"{qe_yaml_path}.bak")
    assert backup_path.exists()

    # Backup should contain the original config
    backup_data = yaml.safe_load(backup_path.read_text())
    assert backup_data["weights"]["pattern_strength"] == pytest.approx(0.30, abs=0.001)


@pytest.mark.asyncio
async def test_atomic_write_tempfile_rename(
    manager: ConfigProposalManager,
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """Verify atomic write uses tempfile+rename (no partial writes)."""
    proposal = _make_proposal()
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-001", "APPROVED")

    # Before apply, take snapshot
    original_data = yaml.safe_load(Path(qe_yaml_path).read_text())

    await manager.apply_pending()

    # After apply, file should be valid YAML
    new_data = yaml.safe_load(Path(qe_yaml_path).read_text())
    assert isinstance(new_data, dict)
    assert new_data["weights"]["pattern_strength"] == pytest.approx(0.35, abs=0.001)

    # No temp files should remain
    parent = Path(qe_yaml_path).parent
    tmp_files = list(parent.glob("*.yaml.tmp"))
    assert len(tmp_files) == 0


@pytest.mark.asyncio
async def test_revert_via_apply_single_change(
    manager: ConfigProposalManager,
    store: LearningStore,
    qe_yaml_path: str,
) -> None:
    """apply_single_change reverts a config value and records history."""
    await manager.apply_single_change("weights.pattern_strength", 0.25)

    raw = yaml.safe_load(Path(qe_yaml_path).read_text())
    assert raw["weights"]["pattern_strength"] == pytest.approx(0.25, abs=0.001)

    # Weights should still sum to 1.0
    total = sum(raw["weights"].values())
    assert total == pytest.approx(1.0, abs=0.001)

    # Check change history
    changes = await store.get_change_history()
    assert len(changes) == 1
    assert changes[0]["source"] == "revert"
    assert float(changes[0]["new_value"]) == pytest.approx(0.25, abs=0.001)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_yaml_parse_failure_raises(tmp_path: Path) -> None:
    """YAML parse failure on startup raises RuntimeError."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("invalid: [yaml: broken: {")

    config = LearningLoopConfig()
    store = LearningStore(db_path=str(tmp_path / "test.db"))
    await store.initialize()

    with pytest.raises(RuntimeError, match="parse failure"):
        ConfigProposalManager(
            config=config,
            store=store,
            quality_engine_yaml_path=str(bad_yaml),
        )


@pytest.mark.asyncio
async def test_yaml_missing_file_raises(tmp_path: Path) -> None:
    """Missing quality_engine.yaml on startup raises RuntimeError."""
    config = LearningLoopConfig()
    store = LearningStore(db_path=str(tmp_path / "test.db"))
    await store.initialize()

    with pytest.raises(RuntimeError, match="not found"):
        ConfigProposalManager(
            config=config,
            store=store,
            quality_engine_yaml_path=str(tmp_path / "nonexistent.yaml"),
        )


def test_config_validation_learning_loop_yaml() -> None:
    """Verify config/learning_loop.yaml loads into LearningLoopConfig correctly."""
    yaml_path = Path("config/learning_loop.yaml")
    assert yaml_path.exists(), "config/learning_loop.yaml must exist"

    raw = yaml.safe_load(yaml_path.read_text())
    assert isinstance(raw, dict)

    # All 13 fields must be present
    expected_keys = {
        "enabled",
        "analysis_window_days",
        "min_sample_count",
        "min_sample_per_regime",
        "max_weight_change_per_cycle",
        "max_cumulative_drift",
        "cumulative_drift_window_days",
        "auto_trigger_enabled",
        "correlation_window_days",
        "report_retention_days",
        "correlation_threshold",
        "weight_divergence_threshold",
        "correlation_p_value_threshold",
    }

    assert set(raw.keys()) == expected_keys, (
        f"YAML keys {set(raw.keys())} != expected {expected_keys}"
    )

    # Must parse without error
    config = LearningLoopConfig(**raw)

    # Verify no silently ignored fields
    model_fields = set(LearningLoopConfig.model_fields.keys())
    assert set(raw.keys()) == model_fields, (
        f"YAML keys {set(raw.keys())} != model fields {model_fields}"
    )


@pytest.mark.asyncio
async def test_apply_pending_records_change_history(
    manager: ConfigProposalManager,
    store: LearningStore,
) -> None:
    """apply_pending records changes in config_change_history."""
    proposal = _make_proposal()
    await store.save_proposal(proposal)
    await store.update_proposal_status("prop-001", "APPROVED")

    await manager.apply_pending()

    changes = await store.get_change_history()
    assert len(changes) == 1
    assert changes[0]["field_path"] == "weights.pattern_strength"
    assert changes[0]["source"] == "learning_loop"
    assert changes[0]["proposal_id"] == "prop-001"


@pytest.mark.asyncio
async def test_apply_pending_no_approved_returns_empty(
    manager: ConfigProposalManager,
    store: LearningStore,
) -> None:
    """apply_pending returns empty list when no approved proposals."""
    applied = await manager.apply_pending()
    assert applied == []


@pytest.mark.asyncio
async def test_cumulative_drift_query(
    manager: ConfigProposalManager,
    store: LearningStore,
) -> None:
    """get_cumulative_drift correctly sums absolute changes."""
    # Record two changes
    await store.record_change(
        field_path="weights.pattern_strength",
        old_value=0.30,
        new_value=0.35,
        source="learning_loop",
    )
    await store.record_change(
        field_path="weights.pattern_strength",
        old_value=0.35,
        new_value=0.32,
        source="learning_loop",
    )

    drift = await manager.get_cumulative_drift("pattern_strength", window_days=30)

    # |0.35 - 0.30| + |0.32 - 0.35| = 0.05 + 0.03 = 0.08
    assert drift == pytest.approx(0.08, abs=0.001)


@pytest.mark.asyncio
async def test_validate_proposal_unknown_dimension(
    manager: ConfigProposalManager,
) -> None:
    """validate_proposal rejects unknown weight dimensions."""
    proposal = _make_proposal(
        field_path="weights.nonexistent_dim",
        current_value=0.0,
        proposed_value=0.10,
    )

    valid, explanation = manager.validate_proposal(proposal)

    assert not valid
    assert "Unknown weight dimension" in explanation


@pytest.mark.asyncio
async def test_load_quality_engine_config_helper(qe_yaml_path: str) -> None:
    """load_quality_engine_config returns a valid QualityEngineConfig."""
    config = load_quality_engine_config(yaml_path=qe_yaml_path)
    assert isinstance(config, QualityEngineConfig)
    assert config.weights.pattern_strength == pytest.approx(0.30, abs=0.001)
