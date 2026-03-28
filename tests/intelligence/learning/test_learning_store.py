"""Tests for LearningStore SQLite persistence.

Covers report CRUD, proposal CRUD, status transitions, supersession logic
(Amendment 6), change history, retention enforcement (Amendment 11),
WAL mode, and empty DB edge cases.

Sprint 28, Session 3a.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import aiosqlite
import pytest

from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    CorrelationResult,
    DataQualityPreamble,
    LearningReport,
    ThresholdRecommendation,
    WeightRecommendation,
)


# --- Fixtures ---


@pytest.fixture()
def db_path(tmp_path: object) -> str:
    """Provide a temporary DB path."""
    return os.path.join(str(tmp_path), "test_learning.db")


@pytest.fixture()
async def store(db_path: str) -> LearningStore:
    """Initialize a LearningStore with a temporary DB."""
    s = LearningStore(db_path=db_path)
    await s.initialize()
    return s


def _make_report(
    report_id: str = "RPT-001",
    generated_at: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> LearningReport:
    """Create a minimal LearningReport for testing."""
    now = datetime.now(UTC)
    return LearningReport(
        report_id=report_id,
        generated_at=generated_at or now,
        analysis_window_start=window_start or (now - timedelta(days=30)),
        analysis_window_end=window_end or now,
        data_quality=DataQualityPreamble(
            trading_days_count=20,
            total_trades=50,
            total_counterfactual=30,
            effective_sample_size=80,
            known_data_gaps=[],
            earliest_date=now - timedelta(days=30),
            latest_date=now,
        ),
        weight_recommendations=[
            WeightRecommendation(
                dimension="pattern_strength",
                current_weight=0.25,
                recommended_weight=0.30,
                delta=0.05,
                correlation_trade_source=0.45,
                correlation_counterfactual_source=0.40,
                p_value=0.03,
                sample_size=50,
                confidence=ConfidenceLevel.MODERATE,
                regime_breakdown={"trending": 0.50, "choppy": 0.30},
                source_divergence_flag=False,
            ),
        ],
        threshold_recommendations=[
            ThresholdRecommendation(
                grade="B+",
                current_threshold=65.0,
                recommended_direction="lower",
                missed_opportunity_rate=0.15,
                correct_rejection_rate=0.80,
                sample_size=40,
                confidence=ConfidenceLevel.MODERATE,
            ),
        ],
        correlation_result=CorrelationResult(
            strategy_pairs=[("orb_breakout", "vwap_reclaim")],
            correlation_matrix={("orb_breakout", "vwap_reclaim"): 0.25},
            flagged_pairs=[],
            excluded_strategies=[],
            window_days=20,
        ),
    )


def _make_proposal(
    proposal_id: str = "PROP-001",
    report_id: str = "RPT-001",
    field_path: str = "weights.pattern_strength",
    status: str = "PENDING",
) -> ConfigProposal:
    """Create a minimal ConfigProposal for testing."""
    now = datetime.now(UTC)
    return ConfigProposal(
        proposal_id=proposal_id,
        report_id=report_id,
        field_path=field_path,
        current_value=0.25,
        proposed_value=0.30,
        rationale="Correlation analysis suggests increase",
        status=status,
        created_at=now,
        updated_at=now,
    )


# --- WAL mode ---


@pytest.mark.asyncio
async def test_wal_mode_enabled(db_path: str, store: LearningStore) -> None:
    """WAL journal mode is set on initialization."""
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "wal"


# --- Report CRUD ---


@pytest.mark.asyncio
async def test_save_and_get_report(store: LearningStore) -> None:
    """Round-trip save and retrieve a LearningReport."""
    report = _make_report()
    await store.save_report(report)

    loaded = await store.get_report("RPT-001")
    assert loaded is not None
    assert loaded.report_id == "RPT-001"
    assert loaded.data_quality.total_trades == 50
    assert len(loaded.weight_recommendations) == 1
    assert loaded.weight_recommendations[0].dimension == "pattern_strength"
    assert len(loaded.threshold_recommendations) == 1
    assert loaded.correlation_result is not None
    assert loaded.correlation_result.window_days == 20


@pytest.mark.asyncio
async def test_get_report_missing(store: LearningStore) -> None:
    """get_report returns None for nonexistent ID."""
    result = await store.get_report("NONEXISTENT")
    assert result is None


@pytest.mark.asyncio
async def test_list_reports_ordering_and_limit(store: LearningStore) -> None:
    """list_reports returns reports ordered by generated_at descending."""
    base = datetime(2026, 3, 1, tzinfo=UTC)
    for i in range(5):
        report = _make_report(
            report_id=f"RPT-{i:03d}",
            generated_at=base + timedelta(days=i),
        )
        await store.save_report(report)

    # All 5
    reports = await store.list_reports()
    assert len(reports) == 5
    assert reports[0].report_id == "RPT-004"  # newest first
    assert reports[4].report_id == "RPT-000"

    # With limit
    limited = await store.list_reports(limit=2)
    assert len(limited) == 2
    assert limited[0].report_id == "RPT-004"


@pytest.mark.asyncio
async def test_list_reports_date_filter(store: LearningStore) -> None:
    """list_reports filters by start_date and end_date."""
    base = datetime(2026, 3, 1, tzinfo=UTC)
    for i in range(5):
        report = _make_report(
            report_id=f"RPT-{i:03d}",
            generated_at=base + timedelta(days=i),
        )
        await store.save_report(report)

    # Filter to days 1-3 only
    filtered = await store.list_reports(
        start_date=base + timedelta(days=1),
        end_date=base + timedelta(days=3),
    )
    ids = {r.report_id for r in filtered}
    assert ids == {"RPT-001", "RPT-002", "RPT-003"}


@pytest.mark.asyncio
async def test_list_reports_empty_db(store: LearningStore) -> None:
    """list_reports returns empty list on empty DB."""
    reports = await store.list_reports()
    assert reports == []


# --- Proposal CRUD ---


@pytest.mark.asyncio
async def test_save_and_list_proposals(store: LearningStore) -> None:
    """Round-trip save and list proposals."""
    report = _make_report()
    await store.save_report(report)

    proposal = _make_proposal()
    await store.save_proposal(proposal)

    proposals = await store.list_proposals()
    assert len(proposals) == 1
    assert proposals[0].proposal_id == "PROP-001"
    assert proposals[0].field_path == "weights.pattern_strength"
    assert proposals[0].status == "PENDING"


@pytest.mark.asyncio
async def test_list_proposals_with_filters(store: LearningStore) -> None:
    """list_proposals filters by status and report_id."""
    report = _make_report()
    await store.save_report(report)

    p1 = _make_proposal(proposal_id="P1", status="PENDING")
    p2 = _make_proposal(proposal_id="P2", status="APPROVED")
    p3 = _make_proposal(proposal_id="P3", report_id="RPT-OTHER", status="PENDING")
    await store.save_proposal(p1)
    await store.save_proposal(p2)
    await store.save_proposal(p3)

    # Filter by status
    pending = await store.list_proposals(status_filter="PENDING")
    assert len(pending) == 2

    # Filter by report_id
    rpt001 = await store.list_proposals(report_id_filter="RPT-001")
    assert len(rpt001) == 2

    # Filter by both
    both = await store.list_proposals(
        status_filter="PENDING", report_id_filter="RPT-001"
    )
    assert len(both) == 1
    assert both[0].proposal_id == "P1"


@pytest.mark.asyncio
async def test_get_pending_proposals(store: LearningStore) -> None:
    """get_pending_proposals returns only PENDING proposals."""
    report = _make_report()
    await store.save_report(report)

    await store.save_proposal(_make_proposal(proposal_id="P1", status="PENDING"))
    await store.save_proposal(_make_proposal(proposal_id="P2", status="APPROVED"))
    await store.save_proposal(_make_proposal(proposal_id="P3", status="PENDING"))

    pending = await store.get_pending_proposals()
    ids = {p.proposal_id for p in pending}
    assert ids == {"P1", "P3"}


# --- Status transitions ---


@pytest.mark.asyncio
async def test_update_proposal_status_approved(store: LearningStore) -> None:
    """Transition PENDING → APPROVED sets updated_at."""
    report = _make_report()
    await store.save_report(report)
    await store.save_proposal(_make_proposal())

    await store.update_proposal_status("PROP-001", "APPROVED", notes="Looks good")

    proposals = await store.list_proposals(status_filter="APPROVED")
    assert len(proposals) == 1
    assert proposals[0].status == "APPROVED"
    assert proposals[0].human_notes == "Looks good"


@pytest.mark.asyncio
async def test_update_proposal_status_applied_sets_applied_at(
    store: LearningStore,
    db_path: str,
) -> None:
    """Transition to APPLIED sets the applied_at timestamp."""
    report = _make_report()
    await store.save_report(report)
    await store.save_proposal(_make_proposal())

    await store.update_proposal_status("PROP-001", "APPLIED")

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT applied_at FROM config_proposals WHERE proposal_id = ?",
            ("PROP-001",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["applied_at"] is not None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_update_proposal_status_reverted_sets_reverted_at(
    store: LearningStore,
    db_path: str,
) -> None:
    """Transition to REVERTED sets the reverted_at timestamp."""
    report = _make_report()
    await store.save_report(report)
    await store.save_proposal(_make_proposal())

    await store.update_proposal_status("PROP-001", "REVERTED")

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT reverted_at FROM config_proposals WHERE proposal_id = ?",
            ("PROP-001",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert dict(row)["reverted_at"] is not None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_full_proposal_state_machine(store: LearningStore) -> None:
    """Walk through PENDING → APPROVED → APPLIED → REVERTED."""
    report = _make_report()
    await store.save_report(report)
    await store.save_proposal(_make_proposal())

    await store.update_proposal_status("PROP-001", "APPROVED")
    p = (await store.list_proposals(status_filter="APPROVED"))[0]
    assert p.status == "APPROVED"

    await store.update_proposal_status("PROP-001", "APPLIED")
    p = (await store.list_proposals(status_filter="APPLIED"))[0]
    assert p.status == "APPLIED"

    await store.update_proposal_status("PROP-001", "REVERTED")
    p = (await store.list_proposals(status_filter="REVERTED"))[0]
    assert p.status == "REVERTED"


@pytest.mark.asyncio
async def test_dismissed_and_rejected_statuses(store: LearningStore) -> None:
    """Verify DISMISSED, REJECTED_GUARD, REJECTED_VALIDATION transitions."""
    report = _make_report()
    await store.save_report(report)

    await store.save_proposal(_make_proposal(proposal_id="P1"))
    await store.save_proposal(_make_proposal(proposal_id="P2"))
    await store.save_proposal(_make_proposal(proposal_id="P3"))

    await store.update_proposal_status("P1", "DISMISSED", notes="Not needed")
    await store.update_proposal_status("P2", "REJECTED_GUARD", notes="Guard check")
    await store.update_proposal_status("P3", "REJECTED_VALIDATION")

    dismissed = await store.list_proposals(status_filter="DISMISSED")
    assert len(dismissed) == 1
    assert dismissed[0].human_notes == "Not needed"

    guard = await store.list_proposals(status_filter="REJECTED_GUARD")
    assert len(guard) == 1

    validation = await store.list_proposals(status_filter="REJECTED_VALIDATION")
    assert len(validation) == 1


# --- Supersession (Amendment 6) ---


@pytest.mark.asyncio
async def test_supersede_proposals_only_pending_from_prior_reports(
    store: LearningStore,
) -> None:
    """supersede_proposals sets PENDING proposals from prior reports to SUPERSEDED."""
    r1 = _make_report(report_id="RPT-OLD")
    r2 = _make_report(report_id="RPT-NEW")
    await store.save_report(r1)
    await store.save_report(r2)

    # Old report: 1 pending, 1 approved
    await store.save_proposal(
        _make_proposal(proposal_id="P-OLD-1", report_id="RPT-OLD", status="PENDING")
    )
    await store.save_proposal(
        _make_proposal(proposal_id="P-OLD-2", report_id="RPT-OLD", status="APPROVED")
    )
    # Persist the APPROVED status
    await store.update_proposal_status("P-OLD-2", "APPROVED")

    # New report: 1 pending
    await store.save_proposal(
        _make_proposal(proposal_id="P-NEW-1", report_id="RPT-NEW", status="PENDING")
    )

    count = await store.supersede_proposals("RPT-NEW")
    assert count == 1  # Only P-OLD-1 (PENDING from old report)

    # P-OLD-1 is now SUPERSEDED
    superseded = await store.list_proposals(status_filter="SUPERSEDED")
    assert len(superseded) == 1
    assert superseded[0].proposal_id == "P-OLD-1"

    # P-OLD-2 still APPROVED (not touched)
    approved = await store.list_proposals(status_filter="APPROVED")
    assert len(approved) == 1

    # P-NEW-1 still PENDING (same report, not touched)
    pending = await store.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0].proposal_id == "P-NEW-1"


@pytest.mark.asyncio
async def test_supersede_proposals_no_pending(store: LearningStore) -> None:
    """supersede_proposals returns 0 when no PENDING proposals exist."""
    count = await store.supersede_proposals("RPT-NEW")
    assert count == 0


# --- Change history ---


@pytest.mark.asyncio
async def test_record_and_get_change_history(store: LearningStore) -> None:
    """Record changes and retrieve them."""
    await store.record_change(
        field_path="weights.pattern_strength",
        old_value=0.25,
        new_value=0.30,
        source="learning_loop",
        proposal_id="P1",
        report_id="RPT-001",
    )
    await store.record_change(
        field_path="weights.volume_profile",
        old_value=0.20,
        new_value=0.15,
        source="revert",
    )

    history = await store.get_change_history()
    assert len(history) == 2
    assert history[0]["field_path"] == "weights.pattern_strength"
    assert float(history[0]["old_value"]) == 0.25  # type: ignore[arg-type]
    assert float(history[0]["new_value"]) == 0.30  # type: ignore[arg-type]
    assert history[1]["source"] == "revert"


@pytest.mark.asyncio
async def test_get_change_history_date_filter(store: LearningStore) -> None:
    """get_change_history filters by date range."""
    await store.record_change("field_a", 1.0, 2.0)
    await store.record_change("field_b", 3.0, 4.0)

    # All records
    all_changes = await store.get_change_history()
    assert len(all_changes) == 2

    # Future filter returns nothing
    future = datetime.now(UTC) + timedelta(days=1)
    filtered = await store.get_change_history(start_date=future)
    assert len(filtered) == 0


@pytest.mark.asyncio
async def test_get_latest_change(store: LearningStore) -> None:
    """get_latest_change returns the most recent change for a field."""
    await store.record_change("weights.pattern_strength", 0.25, 0.28)
    await store.record_change("weights.pattern_strength", 0.28, 0.30)
    await store.record_change("weights.volume_profile", 0.20, 0.15)

    latest = await store.get_latest_change("weights.pattern_strength")
    assert latest is not None
    assert float(latest["old_value"]) == 0.28  # type: ignore[arg-type]
    assert float(latest["new_value"]) == 0.30  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_latest_change_missing(store: LearningStore) -> None:
    """get_latest_change returns None for unknown field."""
    result = await store.get_latest_change("nonexistent.field")
    assert result is None


# --- Retention enforcement (Amendment 11) ---


@pytest.mark.asyncio
async def test_enforce_retention_deletes_old_reports(store: LearningStore) -> None:
    """enforce_retention deletes reports older than retention_days."""
    old_time = datetime.now(UTC) - timedelta(days=100)
    recent_time = datetime.now(UTC) - timedelta(days=5)

    await store.save_report(_make_report("RPT-OLD", generated_at=old_time))
    await store.save_report(_make_report("RPT-RECENT", generated_at=recent_time))

    deleted = await store.enforce_retention(retention_days=30)
    assert deleted == 1

    # Old one gone, recent one remains
    assert await store.get_report("RPT-OLD") is None
    assert await store.get_report("RPT-RECENT") is not None


@pytest.mark.asyncio
async def test_enforce_retention_protects_applied_reverted_reports(
    store: LearningStore,
) -> None:
    """Amendment 11: Reports referenced by APPLIED/REVERTED proposals survive."""
    old_time = datetime.now(UTC) - timedelta(days=100)

    # Two old reports
    await store.save_report(_make_report("RPT-APPLIED", generated_at=old_time))
    await store.save_report(_make_report("RPT-PLAIN", generated_at=old_time))

    # One has an APPLIED proposal
    await store.save_proposal(
        _make_proposal(proposal_id="P-A", report_id="RPT-APPLIED")
    )
    await store.update_proposal_status("P-A", "APPLIED")

    deleted = await store.enforce_retention(retention_days=30)
    assert deleted == 1  # Only RPT-PLAIN deleted

    # RPT-APPLIED protected
    assert await store.get_report("RPT-APPLIED") is not None
    assert await store.get_report("RPT-PLAIN") is None


@pytest.mark.asyncio
async def test_enforce_retention_protects_reverted_reports(
    store: LearningStore,
) -> None:
    """Reports referenced by REVERTED proposals also survive retention."""
    old_time = datetime.now(UTC) - timedelta(days=100)

    await store.save_report(_make_report("RPT-REVERTED", generated_at=old_time))
    await store.save_proposal(
        _make_proposal(proposal_id="P-R", report_id="RPT-REVERTED")
    )
    await store.update_proposal_status("P-R", "REVERTED")

    deleted = await store.enforce_retention(retention_days=30)
    assert deleted == 0

    assert await store.get_report("RPT-REVERTED") is not None


@pytest.mark.asyncio
async def test_enforce_retention_empty_db(store: LearningStore) -> None:
    """enforce_retention on empty DB returns 0."""
    deleted = await store.enforce_retention(retention_days=30)
    assert deleted == 0


# --- Indexes verification ---


@pytest.mark.asyncio
async def test_indexes_created(db_path: str, store: LearningStore) -> None:
    """All 4 required indexes exist after initialization."""
    expected = {
        "idx_reports_generated_at",
        "idx_proposals_status",
        "idx_proposals_report_id",
        "idx_changes_applied_at",
    }
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )
        rows = await cursor.fetchall()
        index_names = {row[0] for row in rows}

    assert expected.issubset(index_names)


# --- get_approved_proposals ---


@pytest.mark.asyncio
async def test_get_approved_proposals(store: LearningStore) -> None:
    """get_approved_proposals returns only APPROVED proposals."""
    report = _make_report()
    await store.save_report(report)

    await store.save_proposal(_make_proposal(proposal_id="P1"))
    await store.save_proposal(_make_proposal(proposal_id="P2"))
    await store.update_proposal_status("P1", "APPROVED")

    approved = await store.get_approved_proposals()
    assert len(approved) == 1
    assert approved[0].proposal_id == "P1"


# --- Fire-and-forget error handling ---


@pytest.mark.asyncio
async def test_save_report_fire_and_forget(tmp_path: object) -> None:
    """save_report does not raise on DB error (fire-and-forget)."""
    # Point to a read-only path to trigger an error
    bad_path = os.path.join(str(tmp_path), "readonly", "learning.db")
    s = LearningStore(db_path=bad_path)
    # Don't initialize — no tables exist
    # save_report should not raise
    report = _make_report()
    await s.save_report(report)  # Should not raise
