"""Per-alert-type auto-resolution policy table (Sprint 31.91 5a.2, HIGH #1).

Each entry maps an ``alert_type`` to a ``PolicyEntry`` describing
(a) whether the policy ever fires, (b) which Event Bus event types its
predicate consumes, and (c) the predicate body. HealthMonitor wires the
table by subscribing to the union of consumed event types and
delegating per-alert evaluation to the registered predicate.

Table is exhaustive: every alert type emitted in the sprint MUST be
present. Alerts that never auto-resolve use ``NEVER_AUTO_RESOLVE`` —
the lambda-False sentinel — to make exhaustiveness a runtime property
rather than a "missing key" silent omission.

Configuration coupling: ``phantom_short`` reads its consecutive-cycle
threshold from ``ReconciliationConfig.broker_orphan_consecutive_clear_threshold``,
NOT a duplicated field. This keeps the auto-resolver and the Session
2c.2 entry-gate clear in lockstep — operators changing one changes
both.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from argus.core.events import (
    DataResumedEvent,
    DatabentoHeartbeatEvent,
    Event,
    IBKRReconnectedEvent,
    OrderFilledEvent,
    ReconciliationCompletedEvent,
)

if TYPE_CHECKING:
    from argus.core.health import ActiveAlert


# ---------------------------------------------------------------------------
# Predicate context
# ---------------------------------------------------------------------------


@dataclass
class PredicateContext:
    """Per-evaluation context passed to predicates.

    Holds the cross-cycle counters predicates need without leaking those
    counters into ``ActiveAlert``'s wire format. Owned by HealthMonitor;
    a single context instance is shared across the lifetime of an alert.
    """

    # phantom_short / stranded_broker_long: consecutive zero-shares cycles.
    consecutive_zero_cycles: int = 0
    # databento_dead_feed: consecutive healthy heartbeats.
    consecutive_healthy_heartbeats: int = 0
    # phantom_short_startup_engaged: track engaged-symbol-set + 24h timer.
    engaged_symbols: set[str] | None = None
    engaged_at_utc: datetime | None = None


# Predicate signature: (alert, event, context) -> True iff cleared.
Predicate = Callable[
    ["ActiveAlert", Event, PredicateContext],
    bool,
]


# ---------------------------------------------------------------------------
# Policy entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyEntry:
    """Describes one alert-type's auto-resolution policy."""

    alert_type: str
    consumes_event_types: tuple[type[Event], ...]
    predicate: Predicate
    operator_ack_required: bool
    description: str


# ---------------------------------------------------------------------------
# Predicate implementations
# ---------------------------------------------------------------------------


def _never_auto_resolve(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """Sentinel: this alert NEVER auto-resolves; operator must ack."""
    return False


# Compatibility alias matching the spec's naming.
NEVER_AUTO_RESOLVE: Predicate = _never_auto_resolve


def make_phantom_short_predicate(
    *,
    threshold_provider: Callable[[], int],
) -> Predicate:
    """Phantom-short auto-resolver: N consecutive zero-shares cycles.

    Reads the threshold via ``threshold_provider`` so HealthMonitor can
    inject ``lambda: config.reconciliation.broker_orphan_consecutive_clear_threshold``
    at construction time and keep auto-resolution in lockstep with
    Session 2c.2's gate-clear logic. NEVER hardcoded to 5; NEVER read
    from a duplicated AlertsConfig field.
    """

    def _predicate(
        alert: "ActiveAlert",
        event: Event,
        context: PredicateContext,
    ) -> bool:
        if not isinstance(event, ReconciliationCompletedEvent):
            return False
        symbol = alert.metadata.get("symbol") if alert.metadata else None
        if not isinstance(symbol, str) or not symbol:
            return False
        broker_shares = event.broker_shares_by_symbol.get(symbol, 0)
        if broker_shares == 0:
            context.consecutive_zero_cycles += 1
        else:
            # Re-detection — reset the counter so the predicate doesn't
            # stutter resolve.
            context.consecutive_zero_cycles = 0
        return context.consecutive_zero_cycles >= threshold_provider()

    return _predicate


def _stranded_broker_long_predicate(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """Stranded-long auto-resolver: broker reports zero for the symbol."""
    if not isinstance(event, ReconciliationCompletedEvent):
        return False
    symbol = alert.metadata.get("symbol") if alert.metadata else None
    if not isinstance(symbol, str) or not symbol:
        return False
    return event.broker_shares_by_symbol.get(symbol, 0) == 0


def _ibkr_reconnect_predicate(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """ibkr_disconnect auto-resolver: any successful IBKR reconnect."""
    return isinstance(event, IBKRReconnectedEvent)


def _ibkr_auth_success_predicate(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """ibkr_auth_failure auto-resolver: any subsequent IBKR-authenticated op."""
    # OrderFilledEvent's existence implies a successful authenticated
    # round-trip with the broker; IBKRReconnectedEvent obviously also
    # qualifies. Either is sufficient.
    return isinstance(event, (OrderFilledEvent, IBKRReconnectedEvent))


def _databento_heartbeat_predicate(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """databento_dead_feed auto-resolver: 3 healthy heartbeats."""
    if isinstance(event, DatabentoHeartbeatEvent):
        context.consecutive_healthy_heartbeats += 1
    elif isinstance(event, DataResumedEvent) and event.provider == "databento":
        # Treat a DataResumed as a confirming healthy heartbeat too —
        # the data layer emits DataResumedEvent today and may emit
        # DatabentoHeartbeatEvent in a later session.
        context.consecutive_healthy_heartbeats += 1
    else:
        return False
    return context.consecutive_healthy_heartbeats >= 3


def _phantom_short_startup_engaged_predicate(
    alert: "ActiveAlert",
    event: Event,
    context: PredicateContext,
) -> bool:
    """phantom_short_startup_engaged: all engaged symbols cleared OR 24h elapsed.

    Closing condition is operator-acknowledgment-required AND
    auto-resolves when either (a) every engaged symbol is broker-zero,
    or (b) 24 hours have passed since engagement. The 24h elapsed branch
    is operator-friendly: at startup the gate engages, the operator may
    not be at their desk; after 24h the alert auto-archives so it
    doesn't accumulate forever in the active list.
    """
    # 24h-elapsed branch.
    engaged_at = context.engaged_at_utc or alert.created_at_utc
    if engaged_at and datetime.now(UTC) - engaged_at >= timedelta(hours=24):
        return True

    # all-cleared branch.
    if not isinstance(event, ReconciliationCompletedEvent):
        return False
    engaged = context.engaged_symbols
    if engaged is None:
        engaged_meta = alert.metadata.get("engaged_symbols") if alert.metadata else None
        if isinstance(engaged_meta, (list, tuple, set)):
            engaged = {str(s) for s in engaged_meta}
            context.engaged_symbols = engaged
        else:
            return False
    if not engaged:
        return True
    return all(
        event.broker_shares_by_symbol.get(sym, 0) == 0
        for sym in engaged
    )


# ---------------------------------------------------------------------------
# Policy table
# ---------------------------------------------------------------------------


def build_policy_table(
    *,
    phantom_short_threshold_provider: Callable[[], int],
) -> dict[str, PolicyEntry]:
    """Construct the alert-type → PolicyEntry table.

    ``phantom_short_threshold_provider`` is injected by HealthMonitor so
    the predicate reads the live value from ``ReconciliationConfig`` —
    this is the single-source-of-truth coupling with Session 2c.2.
    """
    phantom_short_predicate = make_phantom_short_predicate(
        threshold_provider=phantom_short_threshold_provider,
    )
    return {
        "phantom_short": PolicyEntry(
            alert_type="phantom_short",
            consumes_event_types=(ReconciliationCompletedEvent,),
            predicate=phantom_short_predicate,
            operator_ack_required=False,
            description=(
                "N consecutive zero-shares cycles for the symbol "
                "(N from ReconciliationConfig.broker_orphan_consecutive_clear_threshold; "
                "matches Session 2c.2 gate-clear)."
            ),
        ),
        "stranded_broker_long": PolicyEntry(
            alert_type="stranded_broker_long",
            consumes_event_types=(ReconciliationCompletedEvent,),
            predicate=_stranded_broker_long_predicate,
            operator_ack_required=False,
            description="Broker reports zero shares for the symbol.",
        ),
        "phantom_short_retry_blocked": PolicyEntry(
            alert_type="phantom_short_retry_blocked",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description="NEVER auto-resolves; operator ack required.",
        ),
        "cancel_propagation_timeout": PolicyEntry(
            alert_type="cancel_propagation_timeout",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description="NEVER auto-resolves; operator ack required.",
        ),
        "ibkr_disconnect": PolicyEntry(
            alert_type="ibkr_disconnect",
            consumes_event_types=(IBKRReconnectedEvent,),
            predicate=_ibkr_reconnect_predicate,
            operator_ack_required=False,
            description="Successful subsequent IBKR reconnect.",
        ),
        "ibkr_auth_failure": PolicyEntry(
            alert_type="ibkr_auth_failure",
            consumes_event_types=(OrderFilledEvent, IBKRReconnectedEvent),
            predicate=_ibkr_auth_success_predicate,
            operator_ack_required=False,
            description="Successful subsequent IBKR-authenticated operation.",
        ),
        "databento_dead_feed": PolicyEntry(
            alert_type="databento_dead_feed",
            consumes_event_types=(DatabentoHeartbeatEvent, DataResumedEvent),
            predicate=_databento_heartbeat_predicate,
            operator_ack_required=False,
            description="3 consecutive healthy heartbeats.",
        ),
        "phantom_short_startup_engaged": PolicyEntry(
            alert_type="phantom_short_startup_engaged",
            consumes_event_types=(ReconciliationCompletedEvent,),
            predicate=_phantom_short_startup_engaged_predicate,
            operator_ack_required=True,
            description="All engaged symbols cleared OR 24h elapsed.",
        ),
        "eod_residual_shorts": PolicyEntry(
            alert_type="eod_residual_shorts",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. EOD-bounded "
                "short residue (Sprint 30 deferred residue); operator "
                "should review before next session."
            ),
        ),
        "eod_flatten_failed": PolicyEntry(
            alert_type="eod_flatten_failed",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. Failed EOD "
                "flatten — positions remain at session close, requires "
                "operator attention before next session."
            ),
        ),
    }


def all_consumed_event_types(
    table: dict[str, PolicyEntry],
) -> set[type[Event]]:
    """Return the union of event types every active predicate consumes."""
    types: set[type[Event]] = set()
    for entry in table.values():
        types.update(entry.consumes_event_types)
    return types


__all__ = [
    "NEVER_AUTO_RESOLVE",
    "PolicyEntry",
    "Predicate",
    "PredicateContext",
    "all_consumed_event_types",
    "build_policy_table",
    "make_phantom_short_predicate",
]


# Silence unused-import lint complaints; ``Any`` is occasionally useful in
# downstream patches and keeping the import here removes future churn.
_ = Any
