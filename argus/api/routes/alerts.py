"""Alerts REST routes (Sprint 31.91 D9a — DEF-014).

Operator-facing endpoints for the HealthMonitor active-alert state
machine. Three endpoints:

- ``GET /api/v1/alerts/active`` — current alerts (ACTIVE + ACKNOWLEDGED).
- ``GET /api/v1/alerts/history`` — append-only history with optional
  ``since`` window.
- ``POST /api/v1/alerts/{alert_id}/acknowledge`` — atomic + idempotent
  acknowledgment (200 / 404 / 200-late-ack paths; all paths that
  successfully resolve an alert ID write an audit-log row).

Persistence: the audit-log table ``alert_acknowledgment_audit`` lives in
``data/operations.db`` alongside Session 2c.1's
``phantom_short_gated_symbols``. Each acknowledgment is written inside a
single SQLite transaction; the in-memory state mutation runs inside the
transaction window so a failed COMMIT rolls back both the audit row AND
the in-memory transition (MEDIUM #10 atomicity criterion).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.core.health import (
    ActiveAlert,
    AlertLifecycleState,
    HealthMonitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alerts"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AlertResponse(BaseModel):
    """Wire format for an ``ActiveAlert``.

    All datetimes are emitted as ISO-8601 UTC strings.
    """

    alert_id: str
    alert_type: str
    severity: str
    source: str
    message: str
    metadata: dict[str, Any]
    state: str
    created_at_utc: str
    acknowledged_at_utc: str | None
    acknowledged_by: str | None
    archived_at_utc: str | None
    acknowledgment_reason: str | None


class AcknowledgeRequest(BaseModel):
    """Operator-supplied payload for ``POST .../acknowledge``.

    ``reason`` must be ≥10 chars so audit-log entries are meaningful.
    """

    reason: str = Field(
        min_length=10,
        description="Operator's justification for acknowledging the alert.",
    )
    operator_id: str = Field(
        min_length=1,
        description="Operator identifier (single-user system uses 'operator').",
    )


class AcknowledgeResponse(BaseModel):
    """Successful acknowledgment response.

    ``state`` is ``acknowledged`` for the normal + idempotent paths and
    ``archived`` for the late-ack path (alert auto-resolved before ack).
    """

    alert_id: str
    acknowledged_at_utc: str
    acknowledged_by: str
    reason: str
    audit_id: int
    state: str


class AuditEntryResponse(BaseModel):
    """One row of the ``alert_acknowledgment_audit`` log.

    ``audit_kind`` is one of ``ack`` / ``duplicate_ack`` / ``late_ack``
    matching the values written by ``acknowledge_alert``.
    """

    audit_id: int
    timestamp_utc: str
    alert_id: str
    operator_id: str
    reason: str
    audit_kind: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alert_to_response(alert: ActiveAlert) -> AlertResponse:
    """Project an ``ActiveAlert`` to its wire form."""
    return AlertResponse(
        alert_id=alert.alert_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        source=alert.source,
        message=alert.message,
        metadata=dict(alert.metadata),
        state=alert.state.value,
        created_at_utc=alert.created_at_utc.isoformat(),
        acknowledged_at_utc=(
            alert.acknowledged_at_utc.isoformat()
            if alert.acknowledged_at_utc
            else None
        ),
        acknowledged_by=alert.acknowledged_by,
        archived_at_utc=(
            alert.archived_at_utc.isoformat()
            if alert.archived_at_utc
            else None
        ),
        acknowledgment_reason=alert.acknowledgment_reason,
    )


def _resolve_operations_db_path(state: AppState) -> str:
    """Resolve the path to ``data/operations.db``.

    Mirrors the resolution used by ``main.py`` when constructing the
    OrderManager: ``{config.data_dir}/operations.db``. Falls back to
    ``data/operations.db`` if config is unavailable.
    """
    if state.config is not None:
        data_dir = getattr(state.config, "data_dir", "data")
        return str(Path(data_dir) / "operations.db")
    return "data/operations.db"


async def _insert_audit_row(
    db: aiosqlite.Connection,
    *,
    timestamp_utc: str,
    alert_id: str,
    operator_id: str,
    reason: str,
    audit_kind: str,
) -> int:
    """INSERT a row and return ``lastrowid`` (raises if not yielded)."""
    cursor = await db.execute(
        """
        INSERT INTO alert_acknowledgment_audit
            (timestamp_utc, alert_id, operator_id, reason, audit_kind)
        VALUES (?, ?, ?, ?, ?)
        """,
        (timestamp_utc, alert_id, operator_id, reason, audit_kind),
    )
    audit_id = cursor.lastrowid
    if audit_id is None:  # pragma: no cover - defensive
        raise RuntimeError("audit-log INSERT returned no lastrowid")
    return audit_id


async def _atomic_acknowledge(
    db_path: str,
    *,
    health_monitor: HealthMonitor,
    alert: ActiveAlert,
    operator_id: str,
    reason: str,
    now_utc: datetime,
) -> int:
    """Atomic: write audit row + apply in-memory ack inside one txn.

    If the in-memory mutation raises (it shouldn't — it's a pure attribute
    assignment), or the COMMIT fails, the audit row is rolled back AND
    the in-memory state is reverted to its pre-mutation snapshot.
    """
    pre_state = alert.state
    pre_ack_at = alert.acknowledged_at_utc
    pre_ack_by = alert.acknowledged_by
    pre_ack_reason = alert.acknowledgment_reason

    async with aiosqlite.connect(db_path) as db:
        try:
            audit_id = await _insert_audit_row(
                db,
                timestamp_utc=now_utc.isoformat(),
                alert_id=alert.alert_id,
                operator_id=operator_id,
                reason=reason,
                audit_kind="ack",
            )
            health_monitor.apply_acknowledgment(
                alert,
                operator_id=operator_id,
                reason=reason,
                now_utc=now_utc,
            )
            await db.commit()
        except Exception:
            # Roll back in-memory state to the pre-mutation snapshot.
            alert.state = pre_state
            alert.acknowledged_at_utc = pre_ack_at
            alert.acknowledged_by = pre_ack_by
            alert.acknowledgment_reason = pre_ack_reason
            raise
    return audit_id


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/active", response_model=list[AlertResponse])
async def get_active_alerts(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> list[AlertResponse]:
    """Return alerts currently in ACTIVE or ACKNOWLEDGED state.

    Sprint 31.91 D9a — Session 5a.1 surface. Auto-resolution policy
    (5a.2) will drop alerts to ARCHIVED automatically; until then the
    only transition out of ACTIVE/ACKNOWLEDGED is operator-driven.
    """
    return [
        _alert_to_response(a)
        for a in state.health_monitor.get_active_alerts()
    ]


@router.get("/history", response_model=list[AlertResponse])
async def get_alert_history(
    since: str | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> list[AlertResponse]:
    """Return historical alerts within an optional ``since`` window.

    ``since`` is an ISO-8601 timestamp. Alerts created before ``since``
    are excluded. In-memory only in 5a.1; SQLite-backed in 5a.2.
    """
    since_dt: datetime | None = None
    if since is not None:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'since' timestamp: {exc}",
            ) from exc
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=UTC)
    return [
        _alert_to_response(a)
        for a in state.health_monitor.get_alert_history(since=since_dt)
    ]


@router.get("/{alert_id}/audit", response_model=list[AuditEntryResponse])
async def get_alert_audit_trail(
    alert_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> list[AuditEntryResponse]:
    """Return the acknowledgment audit trail for one alert, oldest-first.

    Reads ``alert_acknowledgment_audit`` rows for ``alert_id`` from
    ``data/operations.db``. Returns an empty list if no audit rows exist
    (e.g., the alert was never acknowledged or the alert id is unknown);
    the operator-facing UI distinguishes these via the active-alerts list.

    Sprint 31.91 Session 5e — D13 Observatory alerts panel detail view.
    """
    db_path = _resolve_operations_db_path(state)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        # Schema column is ``id`` (auto-increment PK); the wire field is
        # ``audit_id`` to match ``AcknowledgeResponse.audit_id`` semantics.
        cursor = await db.execute(
            """
            SELECT id AS audit_id, timestamp_utc, alert_id, operator_id,
                   reason, audit_kind
            FROM alert_acknowledgment_audit
            WHERE alert_id = ?
            ORDER BY id ASC
            """,
            (alert_id,),
        )
        rows = await cursor.fetchall()
    return [
        AuditEntryResponse(
            audit_id=row["audit_id"],
            timestamp_utc=row["timestamp_utc"],
            alert_id=row["alert_id"],
            operator_id=row["operator_id"],
            reason=row["reason"],
            audit_kind=row["audit_kind"],
        )
        for row in rows
    ]


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AcknowledgeResponse,
)
async def acknowledge_alert(
    alert_id: str,
    payload: AcknowledgeRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> AcknowledgeResponse:
    """Atomic + idempotent acknowledgment.

    Per MEDIUM #10:

    - 200 (success): alert was ACTIVE; transitions to ACKNOWLEDGED.
      Audit row written with ``audit_kind="ack"``.
    - 200 (idempotent): alert already ACKNOWLEDGED. Original
      acknowledger info preserved in response. Duplicate audit row
      written with ``audit_kind="duplicate_ack"``.
    - 200 (late-ack): alert auto-resolved to ARCHIVED before ack.
      Response state="archived". Late audit row written with
      ``audit_kind="late_ack"``.
    - 404: alert ID unknown (never created or evicted from the bounded
      history window). NO audit row written.

    The atomic transition pattern: the audit-log INSERT and the
    in-memory mutation happen inside the same SQLite transaction. If the
    COMMIT raises, BOTH revert.
    """
    health_monitor = state.health_monitor
    db_path = _resolve_operations_db_path(state)
    now_utc = datetime.now(UTC)

    alert = health_monitor.get_alert_by_id(alert_id)

    if alert is None:
        # Could be unknown OR archived (auto-resolved before ack).
        archived = health_monitor.get_archived_alert_by_id(alert_id)
        if archived is None:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found.",
            )
        # Late-ack path: write a "late_ack" audit row, return state="archived".
        async with aiosqlite.connect(db_path) as db:
            audit_id = await _insert_audit_row(
                db,
                timestamp_utc=now_utc.isoformat(),
                alert_id=alert_id,
                operator_id=payload.operator_id,
                reason=payload.reason,
                audit_kind="late_ack",
            )
            await db.commit()
        logger.info(
            "Alert %s late-acknowledged by operator %s (already archived). "
            "Audit-id: %d.",
            alert_id,
            payload.operator_id,
            audit_id,
        )
        return AcknowledgeResponse(
            alert_id=alert_id,
            acknowledged_at_utc=now_utc.isoformat(),
            acknowledged_by=payload.operator_id,
            reason=payload.reason,
            audit_id=audit_id,
            state=AlertLifecycleState.ARCHIVED.value,
        )

    # Idempotent 200 path: already acknowledged.
    if alert.state == AlertLifecycleState.ACKNOWLEDGED:
        async with aiosqlite.connect(db_path) as db:
            audit_id = await _insert_audit_row(
                db,
                timestamp_utc=now_utc.isoformat(),
                alert_id=alert_id,
                operator_id=payload.operator_id,
                reason=payload.reason,
                audit_kind="duplicate_ack",
            )
            await db.commit()
        logger.info(
            "Alert %s duplicate-acknowledge by operator %s. Original "
            "acknowledger %s preserved. Audit-id: %d.",
            alert_id,
            payload.operator_id,
            alert.acknowledged_by,
            audit_id,
        )
        # Original acknowledger info preserved.
        return AcknowledgeResponse(
            alert_id=alert_id,
            acknowledged_at_utc=(
                alert.acknowledged_at_utc.isoformat()
                if alert.acknowledged_at_utc
                else now_utc.isoformat()
            ),
            acknowledged_by=alert.acknowledged_by or payload.operator_id,
            reason=alert.acknowledgment_reason or payload.reason,
            audit_id=audit_id,
            state=AlertLifecycleState.ACKNOWLEDGED.value,
        )

    # Archived already (race: caller had a stale active-alerts list).
    if alert.state == AlertLifecycleState.ARCHIVED:
        async with aiosqlite.connect(db_path) as db:
            audit_id = await _insert_audit_row(
                db,
                timestamp_utc=now_utc.isoformat(),
                alert_id=alert_id,
                operator_id=payload.operator_id,
                reason=payload.reason,
                audit_kind="late_ack",
            )
            await db.commit()
        return AcknowledgeResponse(
            alert_id=alert_id,
            acknowledged_at_utc=now_utc.isoformat(),
            acknowledged_by=payload.operator_id,
            reason=payload.reason,
            audit_id=audit_id,
            state=AlertLifecycleState.ARCHIVED.value,
        )

    # Normal path: ACTIVE → ACKNOWLEDGED, atomic transition.
    audit_id = await _atomic_acknowledge(
        db_path,
        health_monitor=health_monitor,
        alert=alert,
        operator_id=payload.operator_id,
        reason=payload.reason,
        now_utc=now_utc,
    )

    # Sprint 31.91 5a.2: post-commit, persist alert_state + fan out to
    # WebSocket subscribers. Best-effort; persistence failures are
    # logged inside ``persist_acknowledgment_after_commit`` and do not
    # affect the REST response (the in-memory transition + audit row
    # are already durable).
    try:
        await health_monitor.persist_acknowledgment_after_commit(alert)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Post-commit persistence failed for ack of %s: %s",
            alert_id,
            exc,
        )

    logger.info(
        "Alert %s acknowledged by operator %s. Audit-id: %d.",
        alert_id,
        payload.operator_id,
        audit_id,
    )
    return AcknowledgeResponse(
        alert_id=alert_id,
        acknowledged_at_utc=now_utc.isoformat(),
        acknowledged_by=payload.operator_id,
        reason=payload.reason,
        audit_id=audit_id,
        state=AlertLifecycleState.ACKNOWLEDGED.value,
    )
