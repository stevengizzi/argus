"""Learning Loop REST API routes.

Exposes the Learning Loop analysis pipeline, config proposals,
and change history via REST endpoints. All endpoints JWT-protected.

Sprint 28, Session 5.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

# Valid transitions per Amendment 6: terminal states cannot transition
_TERMINAL_STATUSES = frozenset({"SUPERSEDED", "REVERTED", "REJECTED_GUARD", "REJECTED_VALIDATION"})


# --- Request/Response Models ---


class TriggerResponse(BaseModel):
    """Response for POST /trigger."""

    report_id: str
    generated_at: str
    weight_recommendations: int
    threshold_recommendations: int
    proposals_generated: int
    timestamp: str


class ReportSummaryResponse(BaseModel):
    """Summary of a learning report for list endpoints."""

    report_id: str
    generated_at: str
    analysis_window_start: str
    analysis_window_end: str
    weight_recommendations: int
    threshold_recommendations: int
    version: int


class ProposalResponse(BaseModel):
    """A config proposal."""

    proposal_id: str
    report_id: str
    field_path: str
    current_value: float
    proposed_value: float
    rationale: str
    status: str
    created_at: str
    updated_at: str
    human_notes: str | None


class ApproveRequest(BaseModel):
    """Request body for approve/dismiss endpoints."""

    notes: str | None = None


class ChangeHistoryEntry(BaseModel):
    """A config change history record."""

    change_id: int
    proposal_id: str | None
    field_path: str
    old_value: float
    new_value: float
    source: str
    applied_at: str
    report_id: str | None


# --- Helper functions ---


def _get_learning_service(state: AppState):
    """Get LearningService or raise 503."""
    if state.learning_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning loop not available",
        )
    return state.learning_service


def _get_learning_store(state: AppState):
    """Get LearningStore or raise 503."""
    if state.learning_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning loop not available",
        )
    return state.learning_store


def _get_proposal_manager(state: AppState):
    """Get ConfigProposalManager or raise 503."""
    if state.config_proposal_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning loop not available",
        )
    return state.config_proposal_manager


# --- Endpoints ---


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_analysis(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> TriggerResponse:
    """Run the learning loop analysis pipeline.

    Returns report summary on success. 409 if already running.
    """
    service = _get_learning_service(state)
    store = _get_learning_store(state)

    try:
        report = await service.run_analysis()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis already running",
        )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning loop is disabled",
        )

    # Count proposals generated for this report
    proposals = await store.list_proposals(report_id_filter=report.report_id)

    now = datetime.now(UTC)
    return TriggerResponse(
        report_id=report.report_id,
        generated_at=report.generated_at.isoformat(),
        weight_recommendations=len(report.weight_recommendations),
        threshold_recommendations=len(report.threshold_recommendations),
        proposals_generated=len(proposals),
        timestamp=now.isoformat(),
    )


@router.get("/reports")
async def list_reports(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """List learning reports with optional date filters."""
    store = _get_learning_store(state)

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    reports = await store.list_reports(
        start_date=start_dt, end_date=end_dt, limit=limit
    )

    return {
        "reports": [
            ReportSummaryResponse(
                report_id=r.report_id,
                generated_at=r.generated_at.isoformat(),
                analysis_window_start=r.analysis_window_start.isoformat(),
                analysis_window_end=r.analysis_window_end.isoformat(),
                weight_recommendations=len(r.weight_recommendations),
                threshold_recommendations=len(r.threshold_recommendations),
                version=r.version,
            ).model_dump()
            for r in reports
        ],
        "count": len(reports),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Get a single learning report by ID."""
    store = _get_learning_store(state)
    report = await store.get_report(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
    return {
        "report": report.to_dict(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/proposals")
async def list_proposals(
    status_filter: str | None = Query(default=None, alias="status"),
    report_id: str | None = Query(default=None),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """List config proposals with optional filters."""
    store = _get_learning_store(state)
    proposals = await store.list_proposals(
        status_filter=status_filter, report_id_filter=report_id
    )
    return {
        "proposals": [
            ProposalResponse(
                proposal_id=p.proposal_id,
                report_id=p.report_id,
                field_path=p.field_path,
                current_value=p.current_value,
                proposed_value=p.proposed_value,
                rationale=p.rationale,
                status=p.status,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
                human_notes=p.human_notes,
            ).model_dump()
            for p in proposals
        ],
        "count": len(proposals),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    body: ApproveRequest | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Approve a PENDING proposal. 400 for illegal transitions."""
    store = _get_learning_store(state)
    proposal = await store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    if proposal.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve proposal in {proposal.status} status",
        )

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only approve PENDING proposals, current status: {proposal.status}",
        )

    notes = body.notes if body else None
    await store.update_proposal_status(proposal_id, "APPROVED", notes=notes)

    updated = await store.get_proposal(proposal_id)
    assert updated is not None
    return {
        "proposal": ProposalResponse(
            proposal_id=updated.proposal_id,
            report_id=updated.report_id,
            field_path=updated.field_path,
            current_value=updated.current_value,
            proposed_value=updated.proposed_value,
            rationale=updated.rationale,
            status=updated.status,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            human_notes=updated.human_notes,
        ).model_dump(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/proposals/{proposal_id}/dismiss")
async def dismiss_proposal(
    proposal_id: str,
    body: ApproveRequest | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Dismiss a PENDING proposal."""
    store = _get_learning_store(state)
    proposal = await store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    if proposal.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dismiss proposal in {proposal.status} status",
        )

    if proposal.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only dismiss PENDING proposals, current status: {proposal.status}",
        )

    notes = body.notes if body else None
    await store.update_proposal_status(proposal_id, "DISMISSED", notes=notes)

    updated = await store.get_proposal(proposal_id)
    assert updated is not None
    return {
        "proposal": ProposalResponse(
            proposal_id=updated.proposal_id,
            report_id=updated.report_id,
            field_path=updated.field_path,
            current_value=updated.current_value,
            proposed_value=updated.proposed_value,
            rationale=updated.rationale,
            status=updated.status,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            human_notes=updated.human_notes,
        ).model_dump(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/proposals/{proposal_id}/revert")
async def revert_proposal(
    proposal_id: str,
    body: ApproveRequest | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Revert an APPLIED proposal. 400 if not APPLIED or already REVERTED."""
    store = _get_learning_store(state)
    manager = _get_proposal_manager(state)
    proposal = await store.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )

    if proposal.status == "REVERTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal already reverted",
        )

    if proposal.status != "APPLIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only revert APPLIED proposals, current status: {proposal.status}",
        )

    # Apply the revert (write old value back to YAML)
    try:
        await manager.apply_single_change(
            proposal.field_path, proposal.current_value
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Revert failed: {exc}",
        )

    notes = body.notes if body else None
    await store.update_proposal_status(proposal_id, "REVERTED", notes=notes)

    updated = await store.get_proposal(proposal_id)
    assert updated is not None
    return {
        "proposal": ProposalResponse(
            proposal_id=updated.proposal_id,
            report_id=updated.report_id,
            field_path=updated.field_path,
            current_value=updated.current_value,
            proposed_value=updated.proposed_value,
            rationale=updated.rationale,
            status=updated.status,
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            human_notes=updated.human_notes,
        ).model_dump(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/config-history")
async def get_config_history(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Get config change audit trail."""
    store = _get_learning_store(state)

    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    changes = await store.get_change_history(
        start_date=start_dt, end_date=end_dt
    )

    return {
        "changes": [
            ChangeHistoryEntry(
                change_id=int(c["change_id"]),  # type: ignore[arg-type]
                proposal_id=str(c["proposal_id"]) if c.get("proposal_id") else None,
                field_path=str(c["field_path"]),
                old_value=float(c["old_value"]),  # type: ignore[arg-type]
                new_value=float(c["new_value"]),  # type: ignore[arg-type]
                source=str(c["source"]),
                applied_at=str(c["applied_at"]),
                report_id=str(c["report_id"]) if c.get("report_id") else None,
            ).model_dump()
            for c in changes
        ],
        "count": len(changes),
        "timestamp": datetime.now(UTC).isoformat(),
    }
