"""Reconciliation control routes (Sprint 31.91 Session 2d, D5).

Operator-facing endpoints for the side-aware reconciliation contract
(DEC-385). Currently exposes one endpoint:

- ``POST /api/v1/reconciliation/phantom-short-gate/clear`` — manually
  clear the per-symbol phantom-short entry gate engaged by Session 2c.1
  (broker-orphan SHORT detection). Persists a row to
  ``data/operations.db::phantom_short_override_audit`` capturing the
  full forensic context (M3) and atomically deletes the gated-symbols
  row in the same SQLite transaction.

Auth pattern mirrors ``argus/api/routes/controls.py`` — every handler
requires ``Depends(require_auth)`` because an override carries a
safety-critical implication (re-arming entries on a symbol the
operator has confirmed reconciled).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reconciliation"])


class ClearPhantomShortGateRequest(BaseModel):
    """Operator request to manually clear the phantom-short gate for a
    symbol. ``reason`` is mandatory and must be ≥10 chars so the audit
    log is meaningful — operators cannot simply pass an empty string."""

    symbol: str = Field(min_length=1, description="Ticker symbol to clear.")
    reason: str = Field(
        min_length=10,
        description="Operator's justification for manual gate clearance.",
    )


class ClearPhantomShortGateResponse(BaseModel):
    """Successful clearance — captures the audit-log row PK so the
    operator can later retrieve the full forensic record."""

    symbol: str
    cleared_at_utc: str
    cleared_at_et: str
    audit_id: int
    prior_engagement_source: str | None
    prior_engagement_alert_id: str | None


@router.post(
    "/phantom-short-gate/clear",
    response_model=ClearPhantomShortGateResponse,
)
async def clear_phantom_short_gate(
    payload: ClearPhantomShortGateRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ClearPhantomShortGateResponse:
    """Manually clear the phantom-short entry gate for ``symbol``.

    Persistence-first: the audit-log INSERT and the gated-symbols DELETE
    happen inside a single SQLite transaction. Only after the transaction
    commits successfully does the in-memory ``_phantom_short_gated_symbols``
    set get mutated. A SQLite write failure leaves the gate engaged
    (fail-closed).

    Returns the audit-log row PK so the operator can later query
    ``data/operations.db::phantom_short_override_audit`` for the full
    forensic context (timestamps, prior engagement source, full request
    payload).

    Raises:
        HTTPException 404: ``symbol`` is not currently gated. No audit-log
            row is written.
    """
    order_manager = state.order_manager
    symbol = payload.symbol.strip().upper()

    # Fast 404 — gate not engaged for this symbol; no operation to perform.
    if symbol not in order_manager._phantom_short_gated_symbols:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol {symbol} is not currently gated.",
        )

    # Persist FIRST (audit-log INSERT + gated DELETE in single transaction).
    audit_id, prior_source, prior_alert_id = (
        await order_manager.clear_phantom_short_gate_with_audit(
            symbol=symbol,
            reason=payload.reason,
            override_payload_json=json.dumps(payload.model_dump()),
        )
    )

    # In-memory state mutates AFTER persistence succeeds. If the SQLite
    # write raised, this code never runs and the gate stays engaged.
    order_manager._phantom_short_gated_symbols.discard(symbol)
    order_manager._phantom_short_clear_cycles.pop(symbol, None)

    logger.warning(
        "Phantom-short gate MANUALLY CLEARED for %s by operator. "
        "Reason: %r. Audit-id: %d.",
        symbol,
        payload.reason,
        audit_id,
    )

    utcnow = datetime.now(UTC)
    et_now = utcnow.astimezone(ZoneInfo("America/New_York"))
    return ClearPhantomShortGateResponse(
        symbol=symbol,
        cleared_at_utc=utcnow.isoformat(),
        cleared_at_et=et_now.isoformat(),
        audit_id=audit_id,
        prior_engagement_source=prior_source,
        prior_engagement_alert_id=prior_alert_id,
    )
