"""Sprint 31.92 Unit 6 — Mechanism A follow-on spike (Mode-D-equivalent N=100).

Phase A diagnostic spike against paper IBKR Gateway. NON-SAFE-DURING-TRADING.
Run pre-market or after-hours.

Validates Mechanism A (cancel-and-resubmit-fresh-stop, formerly H1, now PRIMARY
DEFAULT per Tier 3 Review #3 verdict 2026-04-30) against fresh OCA-grouped
brackets. H2 (modify_order PRIMARY) and H4 (hybrid amend) were ELIMINATED-
EMPIRICALLY at Tier 3 #3 (DEF-242 — IBKR broker-side categorical rejection of
modify_order against any OCA group member under DEC-386 ocaType=1 threading;
error 10326; 100% async-cancel rate observed in spike v2 attempt 1). This Unit 6
spike runs the Mode-D-equivalent N=100 hard gate against Mechanism A before S2a.

The harness inherits three structural properties from the S1a v2 spike at
``scripts/spike_def204_round2_path1.py`` (commit 4faa3c0, Unit B DEF-243 fixes):

  - Pre-spike position-sweep refusal-to-start gate (DEF-237 Cat A.2).
  - Side-aware ``_flatten()`` three-branch helper (DEF-237 Cat A.2).
  - DEF-243 fixes: errorEvent listener (``_OcaRejectionTracker``),
    ``logging.FileHandler`` for spike-run log preservation,
    ``isConnected()`` precondition gate at trial-loop entry.

Single measurement loop: ``_measure_mechanism_a_followon()`` runs N=100 trials.
Per trial:

  1. Setup: ``place_bracket_order`` with OCA-grouped stop child (production path
     threads ocaGroup + ocaType=1 per DEC-386). Wait for entry fill.
  2. Cancel: ``cancel_all_orders(symbol, await_propagation=True)`` to tear down
     the OCA-grouped stop. Measure cancel-propagation latency.
  3. Fresh-stop placement: place a SELL STOP via ``place_order`` (bare; no
     ``ocaGroup`` set on the Order — production ``_build_ib_order`` path does
     NOT thread OCA fields, only ``place_bracket_order`` does — naturally
     producing an outside-OCA stop). Measure placement latency.
  4. Unprotected-window observation: between the cancel-return and the fresh
     stop's confirmation, watch for any of: position-state inconsistency,
     unintended fill at a cancelled OCA member, OCA-related broker error on
     the fresh-stop placement, locate suppression. Record observations.
  5. Cleanup: cancel fresh stop + flatten via the side-aware helper.

Hard gate (per DEC-390 amended at Tier 3 #3, per ``tier-3-review-3-verdict.md``
§Question 2 / Mechanism A in detail / Follow-on spike scope):

    mechanism_a_zero_conflict_in_100 == True
    AND cancel_propagation_p50_ms <= 1000
    AND cancel_propagation_p95_ms <= 2000
    AND fresh_stop_placement_p95_ms <= 200
        -> status = "PROCEED", selected_mechanism = "mechanism_a"
    else
        -> status = "INCONCLUSIVE", inconclusive_reason = <which condition>

Any HARD GATE failure escalates to Tier 3 Review #4 per escalation-criteria A20.

JSON output: ``scripts/spike-results/spike-def204-mechanism-a-followon-results.json``.

Exit codes:
  0  PROCEED
  1  INCONCLUSIVE (operator review required; possible Tier 3 Review #4)
  2+ Connection or invocation error

USAGE:
  python scripts/spike_def204_mechanism_a_followon.py \
      --account U24619949 --client-id 1 \
      --symbols SPY,QQQ,IWM,XLF \
      --n-trials 100

  python scripts/spike_def204_mechanism_a_followon.py --account X --dry-run
      # Validate script structure without connecting to IBKR.

REQUIREMENTS:
  - IBKR paper Gateway running on port 4002.
  - clientId 1 (clientId 2 reserved for parallel S1b).
  - Market CLOSED (non-safe-during-trading).
  - Operator does NOT manually disconnect Gateway during execution
    (Unit 6 has no axis (ii)/(iv); spurious disconnect would corrupt the run).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from ib_async import Trade  # noqa: F401  # imported for runtime ib_async presence check
except ImportError:
    print("ERROR: ib_async not installed. Install with: pip install ib_async",
          file=sys.stderr)
    sys.exit(1)

from argus.core.config import IBKRConfig
from argus.core.event_bus import EventBus
from argus.execution.broker import CancelPropagationTimeout
from argus.execution.ibkr_broker import IBKRBroker
from argus.models.trading import Order, OrderSide, OrderStatus, OrderType


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("def204-spike-mech-a")
logging.getLogger("ib_async").setLevel(logging.WARNING)


DEFAULT_SYMBOLS = ["SPY", "QQQ", "IWM", "XLF"]


# ---------------------------------------------------------------------------
# Exceptions (inherited verbatim from S1a v2 spike per Unit C kickoff)
# ---------------------------------------------------------------------------


class SpikeShortPositionDetected(Exception):
    """Raised when the spike harness encounters a short position.

    Long-only spike policy: spike does NOT cover shorts (the cover path is
    DEF-204's cascade that Sprint 31.91 IMPROMPTU-04's production fix
    addresses for trading code, not diagnostics). Aborting is strictly safer
    than issuing a BUY-to-cover from a diagnostic harness.
    """

    def __init__(self, symbol: str, side: Any, shares: int) -> None:
        self.symbol = symbol
        self.side = side
        self.shares = shares
        super().__init__(
            f"SHORT position detected on {symbol}: side={side} shares={shares}. "
            "Long-only spike policy: spike does NOT cover shorts. Aborting."
        )


class SpikePreflightFailedShortPositionsExist(Exception):
    """Raised when the pre-spike position sweep finds non-zero positions.

    Operator must flatten manually via ``scripts/ibkr_close_all_positions.py``
    (DEF-239 audited 2026-04-30: imports ``ib_async.Position`` directly with
    signed-quantity branching at L54-57, structurally inaccessible to DEF-237
    bug class) before re-running the spike. NO bypass flag exists by design
    (per Universal RULE-039 / non-bypassable validation discipline).
    """


# ---------------------------------------------------------------------------
# Pre-flight guards (inherited verbatim from S1a v2 spike)
# ---------------------------------------------------------------------------


def _is_market_hours_et() -> tuple[bool, str]:
    """Return (open, reason). NYSE regular-hours window 09:30 - 16:00 ET."""
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return False, f"weekend ({now_et.strftime('%a %H:%M ET')})"
    open_t = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    if now_et < open_t:
        return False, f"pre-market ({now_et.strftime('%H:%M ET')}; opens 09:30 ET)"
    if now_et >= close_t:
        return False, f"after-hours ({now_et.strftime('%H:%M ET')}; closed 16:00 ET)"
    return True, f"market open ({now_et.strftime('%H:%M ET')})"


class _MarketClosedDetector:
    """Listens for IBKR error 399 'will not be placed at the exchange until
    <next session>' messages — the secondary catch for holidays / early-close
    days that the wall-clock check misses."""

    QUEUED_FRAGMENT = "will not be placed at the exchange until"

    def __init__(self) -> None:
        self.queued_for_next_session = False
        self.last_message: str | None = None

    def __call__(
        self,
        req_id: int,
        error_code: int,
        error_string: str,
        contract: Any = None,
    ) -> None:
        if (
            error_code == 399
            and self.QUEUED_FRAGMENT in (error_string or "").lower()
        ):
            self.queued_for_next_session = True
            self.last_message = error_string


class _OcaRejectionTracker:
    """DEF-243 Fix B.1 (inherited from Unit B): ib_async errorEvent listener
    that records IBKR error code 10326 ("OCA group revision is not allowed")
    keyed by reqId.

    Mechanism A's ``place_order`` for the fresh outside-OCA stop should NEVER
    trigger error 10326 (the order has no ocaGroup set and is not a member of
    the bracket's OCA group). If error 10326 fires for the fresh-stop reqId
    during placement, that is itself an unprotected-window observation —
    something is binding the supposedly-outside stop to the now-cancelled
    OCA group, which is a structural failure of Mechanism A's premise. The
    tracker enables ``_measure_mechanism_a_followon`` to detect this case
    and record it under ``unprotected_window_observations[]``.
    """

    OCA_REJECTION_CODE = 10326

    def __init__(self) -> None:
        self.events: dict[int, list[tuple[float, int, str]]] = {}

    def __call__(
        self,
        req_id: int,
        error_code: int,
        error_string: str,
        contract: Any = None,
    ) -> None:
        if error_code != self.OCA_REJECTION_CODE:
            return
        self.events.setdefault(req_id, []).append(
            (time.monotonic(), error_code, error_string or "")
        )

    def event_count(self, req_id: int) -> int:
        return len(self.events.get(req_id, []))

    def latest_message(self, req_id: int) -> str | None:
        evs = self.events.get(req_id, [])
        return evs[-1][2] if evs else None


# ---------------------------------------------------------------------------
# DEF-243 Fix B.2: log file preservation (inherited from Unit B)
# ---------------------------------------------------------------------------


def _generate_run_timestamp() -> str:
    """Filesystem-safe UTC timestamp (YYYYMMDDTHHMMSSZ). Same convention as
    the S1a v2 spike so a future operator can pattern-match log filenames
    across spike harnesses."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _setup_file_handler(timestamp: str) -> str:
    """DEF-243 Fix B.2 (inherited): attach a logging.FileHandler so a mid-run
    crash leaves the full run log on disk for forensic analysis. File path
    pattern ``scripts/spike-results/spike-mechanism-a-followon-{ts}.log``
    distinguishes this spike's logs from the S1a v2 ``spike-run-{ts}.log``."""
    log_dir = os.path.join("scripts", "spike-results")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"spike-mechanism-a-followon-{timestamp}.log")
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logging.getLogger().addHandler(fh)
    return log_path


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class UnprotectedWindowObservation:
    """One conflict observation during a Mechanism A trial's unprotected
    window (between cancel-return and fresh-stop confirmation).

    Conflict signatures align with Mode D's classification (inherited
    semantics from S1a v2's ``_classify_d_conflict``) but specialized for
    Mechanism A's two distinct broker calls:

      - position_state_inconsistency: post-trial broker position non-zero.
      - unintended_fill_on_cancelled_oca: a cancelled bracket child filled
        AFTER cancel-propagation supposedly returned (i.e., the cancel raced
        with a fill).
      - oca_conflict_on_fresh_stop: error 10326 on the fresh-stop reqId
        (the supposedly-outside stop is being bound to the cancelled OCA
        group — Mechanism A's premise broken).
      - locate_suppression: locate-rejection event during placement.
      - fresh_stop_rejected: place_order returned REJECTED status.
      - fresh_stop_raised: place_order raised an exception.
      - cancel_to_placement_gap_too_large: gap > 10 ms (per spec).
    """
    trial_num: int
    symbol: str
    signature: str
    detail: str
    cancel_propagation_ms: float
    fresh_stop_placement_ms: float
    cancel_to_placement_gap_ms: float


@dataclass
class MechanismATrial:
    trial_num: int
    symbol: str
    conflict: bool
    cancel_propagation_ms: float
    fresh_stop_placement_ms: float
    cancel_to_placement_gap_ms: float
    conflict_signature: str | None = None
    error: str | None = None
    observations: list[UnprotectedWindowObservation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vs = sorted(values)
    idx = int(round((pct / 100.0) * (len(sorted_vs) - 1)))
    return round(sorted_vs[idx], 2)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------


def _build_entry(symbol: str) -> Order:
    return Order(
        strategy_id="spike_def204_mechanism_a",
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
    )


def _build_bracket_stop(symbol: str, stop_price: float) -> Order:
    """Stop child for the bracket. ``place_bracket_order`` threads
    ``ocaGroup`` + ``ocaType=1`` per DEC-386 — the resulting IBKR stop is
    OCA-grouped with its sibling targets (none in this spike's bracket; we
    pass an empty targets list, so the stop is a single-member OCA group)."""
    return Order(
        strategy_id="spike_def204_mechanism_a",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        stop_price=round(stop_price, 2),
        quantity=1,
    )


def _build_outside_oca_stop(symbol: str, qty: int, stop_price: float) -> Order:
    """Fresh outside-OCA SELL STOP for Mechanism A's resubmit phase.

    Verdict-prescribed signature in Tier 3 Review #3 (line 81) is conceptual
    and reads ``broker.place_order(symbol=..., side="SELL", order_type="STP",
    qty=..., aux_price=stop_price, ocaGroup=None, ocaType=0)``. The actual
    Broker ABC at ``argus/execution/broker.py:57`` is
    ``place_order(self, order: Order) -> OrderResult``, accepting an Order
    object (no ocaGroup/ocaType fields on the Order model). The
    ``IBKRBroker._build_ib_order`` path at ``argus/execution/ibkr_broker.py``
    constructs ib_async orders WITHOUT setting ocaGroup/ocaType — only
    ``place_bracket_order`` threads them. Therefore a bare
    ``broker.place_order(_build_outside_oca_stop(...))`` produces an
    outside-OCA stop natively; no harness-side ocaGroup-clearing is needed.

    This is the same Option-B-precedent disposition as Sprint 31.92 Unit 3's
    Cat A.2 ``p._raw_ib_pos.position`` situation: the verdict's literal
    signature does not match the codebase's actual primitive surface, but
    the verdict's *spirit* (cancel and place a stop NOT in the original
    OCA group) is preserved by the actual call. See Unit C close-out
    Judgment-Calls section.
    """
    return Order(
        strategy_id="spike_def204_mechanism_a",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        stop_price=round(stop_price, 2),
        quantity=qty,
    )


def _build_sell(symbol: str, qty: int) -> Order:
    return Order(
        strategy_id="spike_def204_mechanism_a",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=qty,
    )


async def _get_market_price(broker: IBKRBroker, symbol: str) -> float | None:
    """Fetch a usable price for ``symbol``. Tries last/midpoint/close (with
    delayed fallbacks). Returns None on failure. Spike-only — uses
    ``broker._ib`` intentionally; production code MUST NOT."""
    contract = broker._contracts.get_stock_contract(symbol)
    ticker = broker._ib.reqMktData(contract, "", False, False)
    await asyncio.sleep(3.0)
    candidates = [
        ticker.marketPrice(),
        ticker.last,
        getattr(ticker, "delayedLast", None),
        ticker.close,
        getattr(ticker, "delayedClose", None),
        ticker.midpoint(),
    ]
    for v in candidates:
        try:
            if v is not None and v > 0 and v == v:  # NaN-safe
                return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _safe_initial_stop_offset(price: float) -> float:
    """1% below current price (or $0.50 floor). Wide enough that 15-minute
    delayed-data drift on a paper account doesn't trigger the stop before
    the spike can exercise the cancel-and-resubmit cycle."""
    return max(0.50, price * 0.01)


async def _wait_for_entry_fill_by_ulid(
    broker: IBKRBroker, entry_ulid: str, timeout_s: float = 15.0
) -> int:
    """Wait for ``entry_ulid``'s underlying ib_async trade to reach Filled.
    Returns filled quantity (0 = timed out / cancelled / rejected)."""
    ib_order_id = broker._ulid_to_ibkr.get(entry_ulid)
    if ib_order_id is None:
        return 0
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for trade in broker._ib.trades():
            if trade.order.orderId == ib_order_id:
                status = trade.orderStatus.status
                if status == "Filled":
                    return int(trade.orderStatus.filled or 0)
                if status in ("Cancelled", "Inactive"):
                    return 0
                break
        await asyncio.sleep(0.5)
    return 0


def _stop_is_working(broker: IBKRBroker, stop_ulid: str) -> bool:
    """True iff the stop child is in a working state (Submitted /
    PreSubmitted)."""
    ib_order_id = broker._ulid_to_ibkr.get(stop_ulid)
    if ib_order_id is None:
        return False
    for trade in broker._ib.trades():
        if trade.order.orderId == ib_order_id:
            return trade.orderStatus.status in ("Submitted", "PreSubmitted")
    return False


async def _flatten(broker: IBKRBroker, symbol: str) -> None:
    """Cancel any open orders for ``symbol`` and close any net long position.

    DEF-237 Cat A.2 three-branch side-aware logic (inherited verbatim from
    the S1a v2 spike). Reads ``(p.side, p.shares)`` to reconstruct signed
    quantity unambiguously; reading ``p.shares`` alone (the prior side-blind
    pattern) is the absolute-value trap that DEF-199 / DEF-204 are filed
    against.

    Branches:
      - ``p.side == OrderSide.BUY and p.shares > 0`` → SELL-flatten (genuine long).
      - ``p.side == OrderSide.SELL and p.shares > 0`` → raise
        SpikeShortPositionDetected (long-only spike policy refuses to cover).
      - ``p.shares == 0`` → no-op (defense-in-depth; production
        ``IBKRBroker.get_positions`` filters zero-quantity positions).
    """
    try:
        await broker.cancel_all_orders(symbol=symbol, await_propagation=True)
    except CancelPropagationTimeout as e:
        log.warning("Cleanup cancel timed out on %s: %s", symbol, e)
    except Exception as e:
        log.warning("Cleanup cancel raised on %s: %s", symbol, e)
    await asyncio.sleep(0.3)
    positions = await broker.get_positions()
    for p in positions:
        if p.symbol != symbol:
            continue
        if p.shares == 0:
            log.info("Cleanup: %s already flat (shares=0)", symbol)
            break
        if p.side == OrderSide.BUY and p.shares > 0:
            try:
                await broker.place_order(_build_sell(symbol, p.shares))
            except Exception as e:
                log.warning("Cleanup close raised on %s: %s", symbol, e)
            break
        if p.side == OrderSide.SELL and p.shares > 0:
            log.warning(
                "Cleanup: SHORT position detected on %s (side=%s shares=%d). "
                "Long-only spike policy: NOT covering. Aborting spike.",
                symbol, p.side, p.shares,
            )
            raise SpikeShortPositionDetected(symbol, p.side, p.shares)
        log.error(
            "Cleanup: UNKNOWN side for %s (side=%r shares=%d) — skipping cleanup",
            symbol, p.side, p.shares,
        )
        break
    await asyncio.sleep(0.5)


async def _open_entry_with_oca_bracket(
    broker: IBKRBroker, symbol: str, current_price: float
) -> tuple[str, str] | None:
    """Place a 1-share BUY entry + OCA-grouped STP child. Returns
    (entry_ulid, stop_ulid) on success, None on entry/stop failure.

    Uses ``place_bracket_order`` (with empty targets list) so the stop child
    is threaded with ``ocaGroup`` + ``ocaType=1`` per DEC-386. Mechanism A's
    spike then exercises the cancel-and-resubmit cycle against THIS
    OCA-grouped stop; the cancel must propagate through the OCA group, and
    the resubmit places a fresh stop OUTSIDE the original OCA group.
    """
    entry = _build_entry(symbol)
    stop_offset = _safe_initial_stop_offset(current_price)
    stop = _build_bracket_stop(symbol, current_price - stop_offset)
    result = await broker.place_bracket_order(entry, stop, [])
    if result.entry.status not in (OrderStatus.SUBMITTED, OrderStatus.FILLED):
        return None
    entry_ulid = result.entry.order_id
    stop_ulid = result.stop.order_id
    filled_qty = await _wait_for_entry_fill_by_ulid(broker, entry_ulid, timeout_s=15.0)
    if filled_qty == 0:
        return None
    await asyncio.sleep(0.3)
    if not _stop_is_working(broker, stop_ulid):
        return None
    return entry_ulid, stop_ulid


# ---------------------------------------------------------------------------
# Conflict classification
# ---------------------------------------------------------------------------


def _classify_mechanism_a_conflict(
    fresh_stop_result: Any,
    post_positions: list[Any],
    symbol: str,
    cancel_propagation_ms: float,
    fresh_stop_placement_ms: float,
    cancel_to_placement_gap_ms: float,
    fresh_stop_oca_rejection_count: int,
) -> tuple[bool, str | None, str]:
    """Inspect a Mechanism A trial outcome for any unprotected-window
    conflict signature.

    Returns (conflict, signature, detail). ``conflict`` is True iff any of
    the listed signatures matched; ``signature`` is the canonical key (None
    on clean trials); ``detail`` is the human-readable diagnostic message
    (always populated for surfacing in observations).
    """
    if isinstance(fresh_stop_result, Exception):
        return True, "fresh_stop_raised", f"place_order raised: {fresh_stop_result}"
    status = getattr(fresh_stop_result, "status", None)
    msg = getattr(fresh_stop_result, "message", "") or ""
    if status == OrderStatus.REJECTED:
        return True, "fresh_stop_rejected", f"place_order rejected: {msg}"
    msg_lower = msg.lower()
    if "oca" in msg_lower:
        return True, "oca_conflict_on_fresh_stop", f"OCA-related rejection on fresh stop: {msg}"
    if fresh_stop_oca_rejection_count > 0:
        return (
            True,
            "oca_conflict_on_fresh_stop",
            f"errorEvent 10326 fired on fresh-stop reqId ({fresh_stop_oca_rejection_count} events)",
        )
    if "locate" in msg_lower:
        return True, "locate_suppression", f"locate suppression: {msg}"
    for p in post_positions:
        if p.symbol == symbol and p.shares != 0:
            return (
                True,
                "position_state_inconsistency",
                f"post-trial position non-zero: side={p.side} shares={p.shares}",
            )
    if cancel_to_placement_gap_ms > 10.0:
        return (
            True,
            "cancel_to_placement_gap_too_large",
            f"cancel-return -> placement-start gap = {cancel_to_placement_gap_ms:.2f}ms (>10ms)",
        )
    return False, None, "clean trial"


# ---------------------------------------------------------------------------
# Mode-D-equivalent measurement loop (Mechanism A)
# ---------------------------------------------------------------------------


async def _measure_mechanism_a_followon(
    broker: IBKRBroker,
    symbols: list[str],
    n_trials: int,
    oca_tracker: _OcaRejectionTracker,
) -> list[MechanismATrial]:
    """N=100 cancel-and-resubmit-fresh-stop trials against fresh OCA-grouped
    brackets. Each trial measures cancel-propagation latency, fresh-stop
    placement latency, and the cancel-to-placement gap; observes any
    unprotected-window conflict.

    Per-trial loop:
      1. Setup: ``_open_entry_with_oca_bracket`` (production
         ``place_bracket_order`` path, threads OCA per DEC-386).
      2. Cancel: ``broker.cancel_all_orders(symbol, await_propagation=True)``
         (production primitive; ABC at ``argus/execution/broker.py:150``;
         IBKR impl at ``argus/execution/ibkr_broker.py:1262``; uses the
         existing 2s timeout per AMD-2-prime semantics).
      3. Fresh-stop: ``broker.place_order(_build_outside_oca_stop(...))``
         (bare; ``_build_ib_order`` does NOT thread ocaGroup; produces an
         outside-OCA stop natively).
      4. Observe: classify via ``_classify_mechanism_a_conflict``; record
         under ``MechanismATrial.observations``.
      5. Cleanup: ``_flatten`` (cancels fresh stop + closes long position).

    DEF-243 Fix B.3 (inherited): isConnected() precondition gate at trial
    entry. If broker is disconnected mid-spike, abort the trial-loop and
    surface to operator (no per-trial reconnect attempted; Unit 6 has no
    axis (ii)/(iv); spurious disconnect would corrupt the run).
    """
    log.info(
        "=== Mechanism A follow-on: N=%d trials against fresh OCA-grouped brackets ===",
        n_trials,
    )
    trials: list[MechanismATrial] = []
    sym_idx = 0
    for trial_num in range(1, n_trials + 1):
        # DEF-243 Fix B.3: isConnected precondition
        if not broker._ib.isConnected():
            log.error(
                "Mechanism A trial #%d: broker._ib.isConnected() returned False. "
                "Aborting trial loop (Unit 6 has no per-trial reconnect path).",
                trial_num,
            )
            trials.append(MechanismATrial(
                trial_num=trial_num,
                symbol="<n/a>",
                conflict=True,
                cancel_propagation_ms=0.0,
                fresh_stop_placement_ms=0.0,
                cancel_to_placement_gap_ms=0.0,
                conflict_signature="broker_disconnected_at_trial_entry",
                error="broker_disconnected",
            ))
            break

        symbol = symbols[sym_idx % len(symbols)]
        sym_idx += 1
        price = await _get_market_price(broker, symbol)
        if not price:
            trials.append(MechanismATrial(
                trial_num=trial_num,
                symbol=symbol,
                conflict=True,
                cancel_propagation_ms=0.0,
                fresh_stop_placement_ms=0.0,
                cancel_to_placement_gap_ms=0.0,
                conflict_signature="price_unavailable",
                error="price_unavailable",
            ))
            continue
        opened = await _open_entry_with_oca_bracket(broker, symbol, price)
        if opened is None:
            trials.append(MechanismATrial(
                trial_num=trial_num,
                symbol=symbol,
                conflict=True,
                cancel_propagation_ms=0.0,
                fresh_stop_placement_ms=0.0,
                cancel_to_placement_gap_ms=0.0,
                conflict_signature="entry_did_not_fill",
                error="entry_did_not_fill",
            ))
            try:
                await _flatten(broker, symbol)
            except SpikeShortPositionDetected:
                raise
            continue

        # Phase B: cancel the OCA-grouped bracket stop
        cancel_propagation_ms = 0.0
        fresh_stop_placement_ms = 0.0
        cancel_to_placement_gap_ms = 0.0
        fresh_stop_result: Any
        fresh_stop_oca_rejection_count = 0
        try:
            t_cancel_start = time.monotonic()
            await broker.cancel_all_orders(
                symbol=symbol, await_propagation=True
            )
            t_cancel_done = time.monotonic()
            cancel_propagation_ms = (t_cancel_done - t_cancel_start) * 1000.0

            # Phase C: place the fresh outside-OCA stop within <=10ms gap
            stop_offset = _safe_initial_stop_offset(price)
            fresh_stop_order = _build_outside_oca_stop(
                symbol, qty=1, stop_price=price - stop_offset
            )
            t_place_start = time.monotonic()
            cancel_to_placement_gap_ms = (t_place_start - t_cancel_done) * 1000.0
            fresh_stop_result = await broker.place_order(fresh_stop_order)
            t_place_done = time.monotonic()
            fresh_stop_placement_ms = (t_place_done - t_place_start) * 1000.0

            # Snapshot OCA-rejection events for the fresh-stop reqId. The
            # Broker ABC returns OrderResult with ``broker_order_id`` populated
            # to the IBKR orderId (string); cast to int for the tracker key.
            fresh_stop_broker_order_id = getattr(
                fresh_stop_result, "broker_order_id", None
            )
            if fresh_stop_broker_order_id:
                try:
                    fresh_stop_oca_rejection_count = oca_tracker.event_count(
                        int(fresh_stop_broker_order_id)
                    )
                except (TypeError, ValueError):
                    fresh_stop_oca_rejection_count = 0
        except Exception as e:
            fresh_stop_result = e

        # Allow IBKR a beat to settle the fresh stop placement before sampling
        await asyncio.sleep(1.0)

        # Phase D: unprotected-window observation
        post_positions = await broker.get_positions()
        conflict, signature, detail = _classify_mechanism_a_conflict(
            fresh_stop_result,
            post_positions,
            symbol,
            cancel_propagation_ms,
            fresh_stop_placement_ms,
            cancel_to_placement_gap_ms,
            fresh_stop_oca_rejection_count,
        )
        observations: list[UnprotectedWindowObservation] = []
        if conflict and signature is not None:
            observations.append(UnprotectedWindowObservation(
                trial_num=trial_num,
                symbol=symbol,
                signature=signature,
                detail=detail,
                cancel_propagation_ms=round(cancel_propagation_ms, 2),
                fresh_stop_placement_ms=round(fresh_stop_placement_ms, 2),
                cancel_to_placement_gap_ms=round(cancel_to_placement_gap_ms, 2),
            ))
        trials.append(MechanismATrial(
            trial_num=trial_num,
            symbol=symbol,
            conflict=conflict,
            cancel_propagation_ms=round(cancel_propagation_ms, 2),
            fresh_stop_placement_ms=round(fresh_stop_placement_ms, 2),
            cancel_to_placement_gap_ms=round(cancel_to_placement_gap_ms, 2),
            conflict_signature=signature,
            observations=observations,
        ))

        # Phase E: cleanup (cancel fresh stop + flatten)
        try:
            await _flatten(broker, symbol)
        except SpikeShortPositionDetected:
            # SHORT detected mid-cleanup — surface to operator and halt the
            # trial loop. The trial just appended is recorded with conflict=True
            # via the position_state_inconsistency branch (or whatever the
            # short-emitting cause was) so the JSON artifact preserves the
            # last-known-good count.
            log.error(
                "Cleanup encountered SHORT on %s post-trial #%d. Halting trial loop.",
                symbol, trial_num,
            )
            raise

        if trial_num % 10 == 0:
            n_conflicts = sum(1 for t in trials if t.conflict)
            log.info(
                "  Mechanism A progress: %d/%d (conflicts so far: %d)",
                trial_num, n_trials, n_conflicts,
            )
    return trials


# ---------------------------------------------------------------------------
# Hard gate decision
# ---------------------------------------------------------------------------


def _apply_mechanism_a_decision(
    zero_conflict_in_100: bool,
    cancel_propagation_p50_ms: float,
    cancel_propagation_p95_ms: float,
    fresh_stop_placement_p95_ms: float,
    trial_count: int,
) -> tuple[str, str | None, str | None]:
    """Apply the four-condition hard gate per DEC-390 amended at Tier 3 #3.

    Returns (status, selected_mechanism, inconclusive_reason).

    Per ``tier-3-review-3-verdict.md`` §Question 2 / Mechanism A in detail
    (lines 90-94):

      Mechanism A is selected if and only if all four conditions hold:
        1. mechanism_a_zero_conflict_in_100 == true
        2. cancel_propagation_p50_ms <= 1000
        3. cancel_propagation_p95_ms <= 2000
        4. fresh_stop_placement_p95_ms <= 200

      HARD GATE: any 1 conflict in 100 → escalate to Tier 3 Review #4.

    Trial count must equal 100 — a partial run (operator-halt or broker
    disconnect) cannot satisfy the gate even if the partial trials were all
    clean (the gate's binding semantic is "100 clean trials," not
    "trial-conflict-rate < N%").
    """
    if trial_count != 100:
        return (
            "INCONCLUSIVE",
            None,
            f"trial count {trial_count} != 100; gate requires complete N=100 run",
        )
    if not zero_conflict_in_100:
        return (
            "INCONCLUSIVE",
            None,
            "mechanism_a_zero_conflict_in_100 == False (HARD GATE failure; "
            "escalate to Tier 3 Review #4 per escalation-criteria A20)",
        )
    if cancel_propagation_p50_ms > 1000.0:
        return (
            "INCONCLUSIVE",
            None,
            f"cancel_propagation_p50_ms = {cancel_propagation_p50_ms:.2f} > 1000",
        )
    if cancel_propagation_p95_ms > 2000.0:
        return (
            "INCONCLUSIVE",
            None,
            f"cancel_propagation_p95_ms = {cancel_propagation_p95_ms:.2f} > 2000",
        )
    if fresh_stop_placement_p95_ms > 200.0:
        return (
            "INCONCLUSIVE",
            None,
            f"fresh_stop_placement_p95_ms = {fresh_stop_placement_p95_ms:.2f} > 200",
        )
    return ("PROCEED", "mechanism_a", None)


# ---------------------------------------------------------------------------
# JSON aggregation
# ---------------------------------------------------------------------------


def _build_results(trials: list[MechanismATrial]) -> dict[str, Any]:
    """Aggregate the N=100 trials into the Unit 6 JSON schema.

    Required keys per impl-prompt Requirement 5:
      - status
      - selected_mechanism
      - mechanism_a_zero_conflict_in_100
      - cancel_propagation_p50_ms / cancel_propagation_p95_ms
      - fresh_stop_placement_p50_ms (informational) / fresh_stop_placement_p95_ms (gating)
      - unprotected_window_observations[]
      - trial_count
      - spike_run_date
      - inconclusive_reason (only when status == INCONCLUSIVE)

    Dropped vs S1a v2 schema: axis_i_wilson_ub, informational_axes_results,
    worst_axis_wilson_ub, h2_modify_order_*, h2_rejection_rate_pct,
    h2_deterministic_propagation, h1_propagation_*. These were measurement
    modes for H2/H4/H1 selection that no longer apply (Mechanism A is
    PRIMARY DEFAULT post-Tier-3-#3).
    """
    n_trials = len(trials)
    # Latencies are pulled from clean-and-conflict trials alike — the gate
    # binds on the full distribution per DEC-390 amended (a slow cancel that
    # didn't conflict still failed the gate; consistent with the verdict's
    # framing of cancel_propagation as a load-bearing latency property).
    cancel_props = [t.cancel_propagation_ms for t in trials if t.cancel_propagation_ms > 0]
    placement_lats = [t.fresh_stop_placement_ms for t in trials if t.fresh_stop_placement_ms > 0]
    cancel_p50 = _percentile(cancel_props, 50.0)
    cancel_p95 = _percentile(cancel_props, 95.0)
    placement_p50 = _percentile(placement_lats, 50.0)
    placement_p95 = _percentile(placement_lats, 95.0)
    n_conflicts = sum(1 for t in trials if t.conflict)
    zero_conflict_in_100 = (n_trials == 100 and n_conflicts == 0)

    # Flatten observations across trials in trial-order
    observations: list[dict[str, Any]] = []
    for t in trials:
        for obs in t.observations:
            observations.append(asdict(obs))

    status, mechanism, reason = _apply_mechanism_a_decision(
        zero_conflict_in_100,
        cancel_p50,
        cancel_p95,
        placement_p95,
        n_trials,
    )

    out: dict[str, Any] = {
        "status": status,
        "selected_mechanism": mechanism,
        "mechanism_a_zero_conflict_in_100": zero_conflict_in_100,
        "cancel_propagation_p50_ms": cancel_p50,
        "cancel_propagation_p95_ms": cancel_p95,
        "fresh_stop_placement_p50_ms": placement_p50,
        "fresh_stop_placement_p95_ms": placement_p95,
        "unprotected_window_observations": observations,
        "trial_count": n_trials,
        "spike_run_date": _now_utc_iso(),
        "inconclusive_reason": reason,
    }
    out["_raw"] = {
        "trials": [asdict(t) for t in trials],
    }
    return out


def _build_inconclusive_results(reason: str, trial_count: int = 0) -> dict[str, Any]:
    """Schema-conformant INCONCLUSIVE artifact for early-abort paths
    (smoke-test failure, broker-connect failure, mid-run crash). Emits the
    same key set as ``_build_results`` so downstream parsers don't need a
    second code path."""
    return {
        "status": "INCONCLUSIVE",
        "selected_mechanism": None,
        "mechanism_a_zero_conflict_in_100": False,
        "cancel_propagation_p50_ms": 0.0,
        "cancel_propagation_p95_ms": 0.0,
        "fresh_stop_placement_p50_ms": 0.0,
        "fresh_stop_placement_p95_ms": 0.0,
        "unprotected_window_observations": [],
        "trial_count": trial_count,
        "spike_run_date": _now_utc_iso(),
        "inconclusive_reason": reason,
    }


async def _abort_with_inconclusive(
    broker: IBKRBroker, out_path: str, reason: str
) -> None:
    """Write an INCONCLUSIVE JSON artifact and disconnect cleanly. Used by
    smoke-test and connection-failure early-abort paths."""
    results = _build_inconclusive_results(reason, trial_count=0)
    try:
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
    except Exception as e:
        log.warning("Could not write INCONCLUSIVE JSON to %s: %s", out_path, e)
    try:
        await broker.disconnect()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main_async(args: argparse.Namespace) -> int:
    # DEF-243 Fix B.2: attach FileHandler at the very top of main_async
    run_timestamp = _generate_run_timestamp()
    log_path = _setup_file_handler(run_timestamp)
    log.info("Spike run timestamp: %s (log file: %s)", run_timestamp, log_path)
    log.info(
        "Sprint 31.92 Unit 6 Mechanism A follow-on spike — "
        "account=%s clientId=%d symbols=%s n=%d",
        args.account, args.client_id, args.symbols, args.n_trials,
    )

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if len(symbols) < 1:
        log.error("At least 1 symbol required; got %d", len(symbols))
        return 2

    if args.dry_run:
        log.warning("DRY RUN — script structure validated, no IBKR connection made")
        # Validate _build_results schema against an empty trial set
        empty_results = _build_results([])
        required_keys = {
            "status", "selected_mechanism", "mechanism_a_zero_conflict_in_100",
            "cancel_propagation_p50_ms", "cancel_propagation_p95_ms",
            "fresh_stop_placement_p50_ms", "fresh_stop_placement_p95_ms",
            "unprotected_window_observations", "trial_count", "spike_run_date",
            "inconclusive_reason",
        }
        missing = required_keys - set(empty_results.keys())
        if missing:
            log.error("DRY RUN: schema missing keys: %s", missing)
            return 2
        log.info("DRY RUN: schema OK (all %d required keys present)", len(required_keys))
        return 0

    # Guard 1: market-hours pre-flight
    is_open, reason = _is_market_hours_et()
    if not is_open and not args.skip_market_hours_check:
        log.error(
            "Market is closed: %s. The spike requires live fills (09:30 - 16:00 ET, "
            "Mon - Fri). Re-run during market hours with ARGUS stopped. "
            "Override with --skip-market-hours-check if you have an out-of-band "
            "reason to proceed (e.g., NYSE holiday rolling testing window).",
            reason,
        )
        return 2
    if not is_open:
        log.warning("Market-hours check OVERRIDDEN: %s. Proceeding anyway.", reason)
    else:
        log.info("Market-hours check OK: %s.", reason)

    config = IBKRConfig(
        host="127.0.0.1",
        port=4002,
        client_id=args.client_id,
        account=args.account,
        timeout_seconds=30.0,
        readonly=False,
    )
    bus = EventBus()
    broker = IBKRBroker(config, bus)
    try:
        await broker.connect()
    except Exception as e:
        log.error("Failed to connect to paper IBKR Gateway at 127.0.0.1:4002: %s", e)
        return 2

    # Cat A.2 (DEF-237): pre-spike position-sweep refusal-to-start gate.
    # Inherited verbatim from S1a v2 spike — operator must clear residuals
    # via the verified-safe scripts/ibkr_close_all_positions.py (DEF-239
    # audited 2026-04-30) before re-running. NO bypass flag exists.
    try:
        pre_positions = await broker.get_positions()
    except Exception as e:
        log.error("Pre-spike position sweep failed: %s. Aborting.", e)
        try:
            await broker.disconnect()
        except Exception:
            pass
        return 2
    nonzero = [p for p in pre_positions if p.shares > 0]
    if nonzero:
        log.error(
            "Pre-spike position sweep found %d nonzero position(s). Spike refuses "
            "to start. Operator must flatten manually (WITH SIDE-AWARE TOOLING — "
            "scripts/ibkr_close_all_positions.py is verified safe per DEF-239) "
            "before re-running.",
            len(nonzero),
        )
        for p in nonzero:
            log.error(
                "  pre-spike position: symbol=%s side=%s shares=%d",
                p.symbol, p.side, p.shares,
            )
        try:
            await broker.disconnect()
        except Exception:
            pass
        raise SpikePreflightFailedShortPositionsExist(
            f"Pre-spike sweep found {len(nonzero)} nonzero position(s); "
            "operator must flatten via scripts/ibkr_close_all_positions.py"
        )

    # Qualify contracts; set delayed market-data type for paper accounts.
    broker._ib.reqMarketDataType(3)
    try:
        await broker._contracts.qualify_contracts(broker._ib, symbols)
    except Exception as e:
        log.error("Contract qualification failed: %s", e)
        try:
            await broker.disconnect()
        except Exception:
            pass
        return 2

    # Attach detectors. The market-closed detector catches IBKR-error-399
    # queued-for-next-session messages (NYSE holiday / early-close edges).
    detector = _MarketClosedDetector()
    broker._ib.errorEvent += detector

    # DEF-243 Fix B.1: OCA-rejection tracker. Mechanism A's fresh stop
    # should NEVER trigger error 10326; if it does, that's an
    # unprotected-window observation per _classify_mechanism_a_conflict.
    oca_tracker = _OcaRejectionTracker()
    broker._ib.errorEvent += oca_tracker

    out_path = args.output_json
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Smoke test: one bracket on the first symbol; if entry doesn't fill OR
    # the queued-for-next-session detector fires, abort before grinding 100
    # trials of the same failure.
    log.info(
        "Smoke test: placing one OCA-grouped bracket on %s to verify fills are live...",
        symbols[0],
    )
    smoke_price = await _get_market_price(broker, symbols[0])
    if not smoke_price:
        log.error(
            "Smoke test: could not fetch market price for %s. Confirm market data "
            "subscription / Gateway connectivity.", symbols[0],
        )
        await _abort_with_inconclusive(
            broker, out_path,
            f"smoke test: market price unavailable for {symbols[0]}",
        )
        return 1
    smoke_opened = await _open_entry_with_oca_bracket(broker, symbols[0], smoke_price)
    if detector.queued_for_next_session:
        log.error(
            "Smoke test: IBKR queued the order for the next session "
            "(error 399: %s). Market is closed; aborting.",
            detector.last_message,
        )
        if smoke_opened is not None:
            await _flatten(broker, symbols[0])
        await _abort_with_inconclusive(
            broker, out_path,
            f"market closed: IBKR error 399 queued-for-next-session "
            f"({detector.last_message})",
        )
        return 1
    if smoke_opened is None:
        log.error(
            "Smoke test: bracket placement on %s did not fill within 15s and "
            "no queued-for-next-session signal. Likely environmental issue "
            "(illiquid symbol, lost connectivity, or IBKR Gateway stuck). Aborting.",
            symbols[0],
        )
        await _flatten(broker, symbols[0])
        await _abort_with_inconclusive(
            broker, out_path,
            f"smoke test failed: entry on {symbols[0]} did not fill",
        )
        return 1
    log.info(
        "Smoke test PASSED: bracket on %s filled cleanly. Proceeding.",
        symbols[0],
    )
    await _flatten(broker, symbols[0])

    try:
        trials = await _measure_mechanism_a_followon(
            broker, symbols, args.n_trials, oca_tracker,
        )
    except SpikeShortPositionDetected as e:
        log.exception("Spike halted on SHORT-position detection: %s", e)
        # Build partial-results JSON; trial_count != 100 will fail the gate.
        try:
            results = _build_inconclusive_results(
                f"spike halted on SHORT-position detection: {e}",
                trial_count=0,
            )
            with open(out_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
        except Exception as write_err:
            log.warning("Could not write INCONCLUSIVE JSON: %s", write_err)
        try:
            await broker.disconnect()
        except Exception:
            pass
        return 1
    except Exception as e:
        log.exception("Spike crashed mid-run: %s", e)
        try:
            results = _build_inconclusive_results(
                f"spike crashed: {e}", trial_count=0,
            )
            with open(out_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
        except Exception as write_err:
            log.warning("Could not write INCONCLUSIVE JSON: %s", write_err)
        try:
            await broker.disconnect()
        except Exception:
            pass
        return 1

    results = _build_results(trials)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log.info("Results written to %s", out_path)

    print()
    print("=" * 72)
    print("SPRINT 31.92 UNIT 6 — MECHANISM A FOLLOW-ON SPIKE — RESULTS")
    print("=" * 72)
    print(f"  status:                          {results['status']}")
    print(f"  selected_mechanism:              {results['selected_mechanism']}")
    print(f"  mechanism_a_zero_conflict_in_100:{results['mechanism_a_zero_conflict_in_100']}")
    print(f"  cancel_propagation p50/p95 (ms): "
          f"{results['cancel_propagation_p50_ms']:.2f} / "
          f"{results['cancel_propagation_p95_ms']:.2f}")
    print(f"  fresh_stop_placement p50/p95 (ms):"
          f"{results['fresh_stop_placement_p50_ms']:.2f} / "
          f"{results['fresh_stop_placement_p95_ms']:.2f}")
    print(f"  unprotected_window_observations: {len(results['unprotected_window_observations'])}")
    print(f"  trial_count:                     {results['trial_count']}")
    if results.get("inconclusive_reason"):
        print(f"  inconclusive_reason:             {results['inconclusive_reason']}")
    print("=" * 72)

    try:
        await broker.disconnect()
    except Exception as e:
        log.warning("Disconnect raised (non-fatal): %s", e)

    if results["status"] == "PROCEED":
        return 0
    return 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Sprint 31.92 Unit 6 Mechanism A follow-on spike (paper IBKR). "
            "Mode-D-equivalent N=100 against fresh OCA-grouped brackets."
        )
    )
    p.add_argument("--account", required=True,
                   help="IBKR account ID (e.g., U24619949)")
    p.add_argument("--client-id", type=int, default=1,
                   help="IBKR clientId (default 1; 2 reserved for parallel S1b)")
    p.add_argument("--n-trials", type=int, default=100,
                   help="HARD GATE per Tier 3 #3: N=100 trials. "
                        "Reducing breaks the gate's binding semantic; "
                        "operator override only with explicit Work Journal note.")
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                   help="Comma-separated symbols for trials "
                        "(default SPY,QQQ,IWM,XLF)")
    p.add_argument(
        "--output-json",
        default="scripts/spike-results/spike-def204-mechanism-a-followon-results.json",
        help="JSON output path",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Validate script structure without connecting to IBKR")
    p.add_argument("--skip-market-hours-check", action="store_true",
                   help="Override the 09:30 - 16:00 ET wall-clock guard. Use ONLY "
                        "with an out-of-band justification (e.g., NYSE holiday "
                        "rolling testing window). The IBKR error-399 detector "
                        "still runs as a backstop.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.n_trials != 100:
        log.warning(
            "n-trials=%d differs from HARD GATE default 100; "
            "Tier 3 #3 verdict requires N=100 for the gate to bind.",
            args.n_trials,
        )
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        return 130
    except SpikePreflightFailedShortPositionsExist as e:
        log.error("Pre-flight halt: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
