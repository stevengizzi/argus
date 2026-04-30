"""Sprint 31.92 Session 1a — Path #1 mechanism diagnostic spike.

Phase A diagnostic spike against paper IBKR Gateway. NON-SAFE-DURING-TRADING.
Run pre-market or after-hours.

Resolves the H2/H4/H1 mechanism question for Path #1 fix by measuring four
axes against the live broker:

  Mode A:  H2 baseline modify_order round-trip latency + rejection rate +
           deterministic broker-side auxPrice propagation.
  Mode B:  Four adversarial axes for the H2 mechanism:
             (i)   concurrent amends across N>=3 positions
             (ii)  amends during a Gateway reconnect window
             (iii) amends with stale order IDs
             (iv)  joint reconnect + concurrent (worst-case combination)
  Mode C:  H1 cancel-and-await latency baseline.
  Mode D:  N=100 cancel-then-immediate-SELL HARD GATE per Decision 2 — any
           single conflict in 100 trials disqualifies H1.

Emits scripts/spike-results/spike-def204-round2-path1-results.json with the
14 required keys per the implementation prompt. Decision rule (verbatim from
sprint-spec.md § Hypothesis Prescription, H-R2-2-tightened):

  worst-axis Wilson UB < 5%  AND zero-conflict-100  -> h2_amend  (PROCEED)
  5% <= worst < 20%          AND zero-conflict-100  -> h4_hybrid (PROCEED)
  worst >= 20%               AND zero-conflict-100  -> h1_cancel_and_await
                                                        (PROCEED, operator
                                                        confirmation required
                                                        before S2a/S2b)
  zero-conflict-100 == False                        -> H1 unsafe; if worst
                                                        < 20% fall back to
                                                        H2/H4 per bracket;
                                                        else INCONCLUSIVE.

Exit codes:
  0  PROCEED
  1  INCONCLUSIVE (operator review required before S2a/S2b prompt generation)
  2+ Connection or invocation error

USAGE:
  python scripts/spike_def204_round2_path1.py \
      --account U24619949 --client-id 1 \
      --symbols SPY,QQQ,IWM,XLF \
      --num-trials-per-axis 50 --n-stress-trials 100

REQUIREMENTS:
  - IBKR paper Gateway running on port 4002
  - clientId 1 reserved for this spike (clientId 2 reserved for parallel S1b)
  - Market CLOSED (non-safe-during-trading constraint)
  - Operator at terminal for axes (ii) + (iv) Gateway-disconnect prompts
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
from typing import Any, cast

try:
    from ib_async import Trade
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
log = logging.getLogger("def204-spike")
logging.getLogger("ib_async").setLevel(logging.WARNING)


# Mode B axis keys per Implementation Prompt Requirement 2
AXIS_CONCURRENT = "concurrent_amends"
AXIS_RECONNECT = "reconnect_window_amends"
AXIS_STALE_ID = "stale_id_amends"
AXIS_JOINT = "joint_reconnect_concurrent_amends"

DEFAULT_SYMBOLS = ["SPY", "QQQ", "IWM", "XLF"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SpikeShortPositionDetected(Exception):
    """Raised when the spike harness encounters a short position.

    Sprint 31.92 Tier 3 Review #2 verdict §Cat A.2 (DEF-237): the spike is a
    long-only diagnostic. Encountering a short during cleanup means a prior
    session left contamination OR upstream code emitted an unexpected SELL.
    Either way, the spike refuses to "cover" the short — that path is the
    DEF-204 cascade that the Sprint 31.91 IMPROMPTU-04 production fix already
    addresses for trading code. Aborting the spike is strictly safer than
    issuing a BUY-to-cover from a diagnostic harness.
    """

    def __init__(self, symbol: str, side: Any, shares: int) -> None:
        self.symbol = symbol
        self.side = side
        self.shares = shares
        super().__init__(
            f"SHORT position detected on {symbol}: side={side} shares={shares}. "
            "Long-only spike policy: spike does NOT cover shorts. Aborting."
        )


# ---------------------------------------------------------------------------
# Pre-flight guards — fail-fast on wrong-window invocations
# ---------------------------------------------------------------------------


def _is_market_hours_et() -> tuple[bool, str]:
    """Return (open, reason). NYSE regular-hours window 09:30 - 16:00 ET, Mon - Fri.

    Holidays not enumerated — IBKR's "queued for next session" 399 message
    detected by `_MarketClosedDetector` is the secondary catch for holidays
    and early-close days. The wall-clock check is the cheap first line.
    """
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
    """Listens to IBKR errorEvent for 'will not be placed at the exchange
    until <next session>' messages. IBKR emits this as error code 399 on
    overnight-queued orders; firing once is enough to abort the spike."""

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


# ---------------------------------------------------------------------------
# Result dataclasses — JSON output schema mirrors these
# ---------------------------------------------------------------------------


@dataclass
class AxisResult:
    n_trials: int = 0
    n_rejections: int = 0
    rejection_rate_pct: float = 0.0
    wilson_upper_bound_pct: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ModeATrial:
    symbol: str
    success: bool
    rejected: bool
    propagation_ok: bool
    round_trip_ms: float
    error: str | None = None


@dataclass
class ModeCTrial:
    symbol: str
    success: bool
    round_trip_ms: float
    error: str | None = None


@dataclass
class ModeDTrial:
    symbol: str
    conflict: bool
    cancel_to_sell_gap_ms: float
    conflict_signature: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def _wilson_upper_bound(successes: int, n: int, confidence: float = 0.95) -> float:
    """Wilson-score upper-confidence-bound for a binomial proportion.

    `successes` here is the count of REJECTIONS (the failure event we are
    bounding). Returns the upper bound on the rejection-rate percentage.
    Falls back to 100.0 when n == 0 so a degenerate axis can never satisfy
    the H2/H4 < 5% / < 20% gates.
    """
    if n == 0:
        return 100.0
    # 95% CI -> z = 1.96; 99% CI -> z = 2.5758
    z = 1.96 if confidence == 0.95 else 2.5758
    p = successes / n
    denom = 1 + (z * z) / n
    centre = p + (z * z) / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n)
    upper = (centre + spread) / denom
    return round(upper * 100.0, 2)


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
        strategy_id="spike_def204_path1",
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
    )


def _build_stop(symbol: str, stop_price: float) -> Order:
    return Order(
        strategy_id="spike_def204_path1",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        stop_price=round(stop_price, 2),
        quantity=1,
    )


def _build_sell(symbol: str, qty: int) -> Order:
    return Order(
        strategy_id="spike_def204_path1",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=qty,
    )


async def _get_market_price(broker: IBKRBroker, symbol: str) -> float | None:
    """Fetch a usable price for `symbol` via the broker's ib_async client.

    Tries last/midpoint/close (with delayed fallbacks). Returns None on
    failure — the calling code should treat that as a per-symbol skip.
    Spike-only — uses broker._ib intentionally; production code MUST NOT.

    Assumes contracts have already been qualified via the resolver's
    qualify_contracts() pass at startup (populates `conId`, required for
    `reqMktData`'s ticker hashing).
    """
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
    """1% below current price (or $0.50 floor for low-priced symbols).

    Wide enough that 15-minute delayed-data drift on a paper account
    doesn't accidentally trigger the stop before we can exercise it. The
    smoke-test attempt on c1b4bf2 / 9cedaba used a flat 50 cents; the
    actual realtime price moved away from the delayed quote and the stop
    fired 700ms after entry. 1% is plenty of room on SPY (~$7) and still
    safe on cheaper symbols where 1% > $0.50.
    """
    return max(0.50, price * 0.01)


def _safe_modified_stop_offset(price: float) -> float:
    """0.5% below current price (or $0.50 floor). Distinct from the
    initial offset so the deterministic-propagation check has a real
    auxPrice delta to verify after `modify_order`."""
    return max(0.50, price * 0.005)


async def _wait_for_entry_fill_by_ulid(
    broker: IBKRBroker, entry_ulid: str, timeout_s: float = 15.0
) -> int:
    """Wait for `entry_ulid`'s underlying ib_async trade to reach Filled.

    Returns filled quantity (0 = timed out / cancelled / rejected). More
    reliable than polling `broker.get_positions()` because (a) the IBKR
    position cache has a small lag behind fill events, and (b) if the
    bracket's stop child fires immediately after the entry, the position
    cache shows 0 even though the entry executed — which the prior
    positions-based wait misread as "entry_did_not_fill".

    Spike-only — uses broker._ulid_to_ibkr + broker._ib.trades()
    directly; production code MUST NOT.
    """
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
    PreSubmitted). False if it's terminal (Filled / Cancelled / Inactive)
    or if the broker doesn't recognize the ULID. Used after entry fill
    to skip a trial cleanly when a fast market move tripped the stop
    pre-amendment."""
    ib_order_id = broker._ulid_to_ibkr.get(stop_ulid)
    if ib_order_id is None:
        return False
    for trade in broker._ib.trades():
        if trade.order.orderId == ib_order_id:
            return trade.orderStatus.status in ("Submitted", "PreSubmitted")
    return False


async def _flatten(broker: IBKRBroker, symbol: str) -> None:
    """Cancel any open orders for `symbol` and close any net long position.

    Cat A.2 (DEF-237): three-branch side-aware logic mirroring the Sprint
    31.91 IMPROMPTU-04 production precedent. ARGUS's `Position` model
    exposes the signed-quantity information via `(side, shares)` —
    `IBKRBroker.get_positions()` derives `side = BUY if ib_pos.position > 0
    else SELL` and `shares = abs(int(ib_pos.position))` per
    `argus/execution/ibkr_broker.py:1109-1111`. Reading `(p.side, p.shares)`
    reconstructs the signed quantity unambiguously; reading `p.shares`
    alone (the prior side-blind pattern) is the absolute-value trap that
    DEF-199 / DEF-204 are filed against.

    The verdict's Cat A.2 spec block referenced `p._raw_ib_pos.position`
    which does not exist on `argus.models.trading.Position` (Pydantic
    BaseModel; grep-verified zero matches in `argus/` and `scripts/`).
    Operator disposition received via the Sprint 31.92 Work Journal
    Option-B selection: apply the verdict's spirit via `(side, shares)`
    reading (mirrors IMPROMPTU-04 production fix at
    `argus/main.py::check_startup_position_invariant` +
    `argus/execution/order_manager.py:1684/1707`). See Unit 3 close-out
    Judgment-Call note for the full audit trail.
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
        # Defensive zero-shares branch — IBKRBroker.get_positions filters
        # zero-quantity positions at ibkr_broker.py:1106 so this should never
        # fire in practice; defense-in-depth is cheap.
        if p.shares == 0:
            log.info("Cleanup: %s already flat (shares=0)", symbol)
            break
        if p.side == OrderSide.BUY and p.shares > 0:
            # Genuine long — flatten via SELL (the original supported case).
            try:
                await broker.place_order(_build_sell(symbol, p.shares))
            except Exception as e:
                log.warning("Cleanup close raised on %s: %s", symbol, e)
            break
        if p.side == OrderSide.SELL and p.shares > 0:
            # Short detected — long-only spike policy refuses to cover.
            log.warning(
                "Cleanup: SHORT position detected on %s (side=%s shares=%d). "
                "Long-only spike policy: NOT covering. Aborting spike.",
                symbol, p.side, p.shares,
            )
            raise SpikeShortPositionDetected(symbol, p.side, p.shares)
        # UNKNOWN side — defends against future OrderSide enum extension
        # (current enum has only BUY/SELL; this branch is unreachable today).
        log.error(
            "Cleanup: UNKNOWN side for %s (side=%r shares=%d) — skipping cleanup",
            symbol, p.side, p.shares,
        )
        break
    await asyncio.sleep(0.5)


async def _open_entry_with_bracket(
    broker: IBKRBroker, symbol: str, current_price: float
) -> tuple[str, str] | None:
    """Place a 1-share BUY entry + STP child. Returns (entry_ulid, stop_ulid).

    Uses the 1%-or-$0.50-floor initial stop offset to avoid pre-firing
    the stop on delayed-data drift. After entry fills (detected via the
    trade-status path, not the positions cache), verifies the stop child
    is still in a working state — if a fast market move tripped it
    anyway, returns None and the caller skips the trial.
    """
    entry = _build_entry(symbol)
    stop_offset = _safe_initial_stop_offset(current_price)
    stop = _build_stop(symbol, current_price - stop_offset)
    result = await broker.place_bracket_order(entry, stop, [])
    if result.entry.status not in (OrderStatus.SUBMITTED, OrderStatus.FILLED):
        return None
    entry_ulid = result.entry.order_id
    stop_ulid = result.stop.order_id
    filled_qty = await _wait_for_entry_fill_by_ulid(broker, entry_ulid, timeout_s=15.0)
    if filled_qty == 0:
        return None
    # Brief beat for the stop child to settle into Submitted state
    # post-entry-fill before we verify it's still working.
    await asyncio.sleep(0.3)
    if not _stop_is_working(broker, stop_ulid):
        return None
    return entry_ulid, stop_ulid


def _verify_aux_price(
    broker: IBKRBroker, stop_ulid: str, expected_aux: float
) -> bool:
    """Query open trades and verify the stop child's auxPrice matches.

    Logs the observed auxPrice at INFO unconditionally so that on a False
    return the operator can distinguish "broker cache lag (actual ~ expected
    but tolerance miss)" from "actually didn't propagate (actual stale or
    zero)". This is the Cat A.1 (DEF-236) instrumentation arm — the wait /
    reqOpenOrders arms live at the call site in _measure_mode_a.
    """
    ib_order_id = broker._ulid_to_ibkr.get(stop_ulid)
    if ib_order_id is None:
        log.info(
            "verify_aux_price: stop_ulid=%s not in _ulid_to_ibkr (expected=%.2f)",
            stop_ulid, round(expected_aux, 2),
        )
        return False
    trades = broker._ib.openTrades()
    for t in trades:
        t = cast(Trade, t)
        if t.order.orderId == ib_order_id:
            actual = float(getattr(t.order, "auxPrice", 0.0) or 0.0)
            matched = abs(actual - round(expected_aux, 2)) < 0.005
            log.info(
                "verify_aux_price: stop_ulid=%s ib_order_id=%d actual_auxPrice=%.4f expected=%.2f matched=%s",
                stop_ulid, ib_order_id, actual, round(expected_aux, 2), matched,
            )
            return matched
    log.info(
        "verify_aux_price: stop_ulid=%s ib_order_id=%d not found in openTrades (expected=%.2f)",
        stop_ulid, ib_order_id, round(expected_aux, 2),
    )
    return False


# ---------------------------------------------------------------------------
# Measurement Mode A — H2 baseline modify_order
# ---------------------------------------------------------------------------


async def _measure_mode_a(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> list[ModeATrial]:
    log.info("=== Mode A: H2 baseline modify_order — %d trials ===", num_trials)
    trials: list[ModeATrial] = []
    sym_idx = 0
    for trial_num in range(1, num_trials + 1):
        symbol = symbols[sym_idx % len(symbols)]
        sym_idx += 1
        price = await _get_market_price(broker, symbol)
        if not price:
            trials.append(ModeATrial(symbol, False, False, False, 0.0,
                                     error="price_unavailable"))
            continue
        opened = await _open_entry_with_bracket(broker, symbol, price)
        if opened is None:
            trials.append(ModeATrial(symbol, False, False, False, 0.0,
                                     error="entry_did_not_fill"))
            await _flatten(broker, symbol)
            continue
        _, stop_ulid = opened
        new_aux = round(price - _safe_modified_stop_offset(price), 2)
        t0 = time.monotonic()
        try:
            res = await broker.modify_order(stop_ulid, {"price": new_aux})
            rtt_ms = (time.monotonic() - t0) * 1000.0
            rejected = res.status == OrderStatus.REJECTED
            # Cat A.1 (DEF-236): the prior 500ms wait sampled the client-side
            # ib_async cache before the broker's orderStatus callback
            # propagated the new auxPrice — producing 0/50 propagation_ok in
            # S1a v1 despite 50/50 modify_order successes. Sprint 31.92 Tier 3
            # Review #2 verdict §Cat A.1 fix: extend wait to 2.5s AND force a
            # broker-side state pull via reqOpenOrders() before sampling. The
            # observed auxPrice is logged inside _verify_aux_price so a False
            # return is diagnostic ("actual stale" vs "actual ~ expected,
            # tolerance miss").
            await asyncio.sleep(2.5)
            await broker._ib.reqOpenOrders()
            propagated = _verify_aux_price(broker, stop_ulid, new_aux)
            trials.append(ModeATrial(
                symbol=symbol,
                success=not rejected,
                rejected=rejected,
                propagation_ok=propagated,
                round_trip_ms=round(rtt_ms, 2),
                error=res.message if rejected else None,
            ))
        except Exception as e:
            rtt_ms = (time.monotonic() - t0) * 1000.0
            trials.append(ModeATrial(symbol, False, True, False,
                                     round(rtt_ms, 2), error=str(e)))
        finally:
            await _flatten(broker, symbol)
        if trial_num % 10 == 0:
            log.info("  Mode A progress: %d/%d", trial_num, num_trials)
    return trials


# ---------------------------------------------------------------------------
# Measurement Mode B — adversarial axes
# ---------------------------------------------------------------------------


async def _amend_one(
    broker: IBKRBroker, stop_ulid: str, new_aux: float
) -> tuple[bool, str | None]:
    """Single modify_order — returns (rejected, error_str). Used by axes."""
    try:
        res = await broker.modify_order(stop_ulid, {"price": new_aux})
        if res.status == OrderStatus.REJECTED:
            return True, res.message or "REJECTED"
        return False, None
    except Exception as e:
        return True, str(e)


async def _axis_concurrent(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> AxisResult:
    """Axis (i): concurrent amends across N>=3 positions. Each TRIAL fires
    >=3 amends inside <=10ms via asyncio.gather; trial counts contribute
    one rejection-or-success per amend."""
    log.info("=== Mode B axis (i) concurrent — %d trials ===", num_trials)
    result = AxisResult()
    n_pos = max(3, min(len(symbols), 4))
    syms_round = symbols[:n_pos]
    for trial_num in range(1, num_trials + 1):
        opens: list[tuple[str, str, float]] = []  # (symbol, stop_ulid, price)
        for s in syms_round:
            price = await _get_market_price(broker, s)
            if not price:
                continue
            o = await _open_entry_with_bracket(broker, s, price)
            if o is None:
                await _flatten(broker, s)
                continue
            opens.append((s, o[1], price))
        if len(opens) < 3:
            result.notes.append(
                f"trial {trial_num}: only opened {len(opens)} positions, skipping"
            )
            for s, _, _ in opens:
                await _flatten(broker, s)
            continue
        # Fire all amends inside <=10ms by constructing the coroutines first
        # then handing the batch to asyncio.gather (which schedules eagerly).
        coros = [_amend_one(broker, ulid, round(price - _safe_modified_stop_offset(price), 2))
                 for _, ulid, price in opens]
        outcomes = await asyncio.gather(*coros, return_exceptions=False)
        for rejected, _err in outcomes:
            result.n_trials += 1
            if rejected:
                result.n_rejections += 1
        for s, _, _ in opens:
            await _flatten(broker, s)
        if trial_num % 5 == 0:
            log.info("  axis (i) progress: %d/%d", trial_num, num_trials)
    if result.n_trials > 0:
        result.rejection_rate_pct = round(
            100.0 * result.n_rejections / result.n_trials, 2
        )
    result.wilson_upper_bound_pct = _wilson_upper_bound(
        result.n_rejections, result.n_trials
    )
    return result


async def _axis_reconnect(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> AxisResult:
    """Axis (ii): amends during Gateway reconnect window. Operator-orchestrated:
    pause for operator to disconnect Gateway, fire amends rapidly during the
    window, operator types RECONNECTED when Gateway is back. Trial cadence is
    one amend per ~500ms during the window, capped at num_trials."""
    log.info("=== Mode B axis (ii) reconnect — up to %d trials ===", num_trials)
    result = AxisResult()
    # Open one position so we have a live stop_ulid to amend
    sym = symbols[0]
    price = await _get_market_price(broker, sym)
    if not price:
        result.notes.append("axis (ii): could not fetch price; skipped")
        return result
    opened = await _open_entry_with_bracket(broker, sym, price)
    if opened is None:
        result.notes.append("axis (ii): entry did not fill; skipped")
        await _flatten(broker, sym)
        return result
    _, stop_ulid = opened

    print()
    print("=" * 72)
    print("  AXIS (ii) RECONNECT WINDOW — OPERATOR ACTION REQUIRED")
    print("=" * 72)
    print("  1. Disconnect IBKR Gateway NOW (kill the process or pull network).")
    print("  2. Script will fire %d amends every ~500ms while disconnected." % num_trials)
    print("  3. When Gateway is back, type 'RECONNECTED' + Enter to resume.")
    print("=" * 72)

    # Run a background reader for stdin "RECONNECTED" sentinel
    reconnected = asyncio.Event()

    async def _watch_stdin() -> None:
        loop = asyncio.get_event_loop()
        while not reconnected.is_set():
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if line and "RECONNECT" in line.strip().upper():
                reconnected.set()
                return

    watcher = asyncio.create_task(_watch_stdin())
    try:
        for _ in range(num_trials):
            if reconnected.is_set():
                break
            new_aux = round(price - _safe_modified_stop_offset(price), 2)
            rejected, _err = await _amend_one(broker, stop_ulid, new_aux)
            result.n_trials += 1
            if rejected:
                result.n_rejections += 1
            await asyncio.sleep(0.5)
    finally:
        if not watcher.done():
            watcher.cancel()
        await asyncio.sleep(2.0)  # Give Gateway breathing room post-reconnect
        await _flatten(broker, sym)

    if result.n_trials > 0:
        result.rejection_rate_pct = round(
            100.0 * result.n_rejections / result.n_trials, 2
        )
    result.wilson_upper_bound_pct = _wilson_upper_bound(
        result.n_rejections, result.n_trials
    )
    return result


async def _axis_stale_id(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> AxisResult:
    """Axis (iii): amends with stale order IDs. Open a bracket, capture the
    stop ULID, cancel it, then fire modify_order against the cancelled ULID."""
    log.info("=== Mode B axis (iii) stale-ID — %d trials ===", num_trials)
    result = AxisResult()
    sym_idx = 0
    for trial_num in range(1, num_trials + 1):
        symbol = symbols[sym_idx % len(symbols)]
        sym_idx += 1
        price = await _get_market_price(broker, symbol)
        if not price:
            continue
        opened = await _open_entry_with_bracket(broker, symbol, price)
        if opened is None:
            await _flatten(broker, symbol)
            continue
        _, stop_ulid = opened
        await _flatten(broker, symbol)  # invalidates the stop ULID
        await asyncio.sleep(0.2)
        rejected, _err = await _amend_one(broker, stop_ulid, round(price - _safe_modified_stop_offset(price), 2))
        result.n_trials += 1
        if rejected:
            result.n_rejections += 1
        if trial_num % 10 == 0:
            log.info("  axis (iii) progress: %d/%d", trial_num, num_trials)
    if result.n_trials > 0:
        result.rejection_rate_pct = round(
            100.0 * result.n_rejections / result.n_trials, 2
        )
    result.wilson_upper_bound_pct = _wilson_upper_bound(
        result.n_rejections, result.n_trials
    )
    return result


async def _axis_joint(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> AxisResult:
    """Axis (iv): joint reconnect + concurrent — N>=3 concurrent amends
    DURING a Gateway reconnect window. Worst-case for H2."""
    log.info("=== Mode B axis (iv) joint — up to %d trials ===", num_trials)
    result = AxisResult()
    n_pos = max(3, min(len(symbols), 4))
    syms_round = symbols[:n_pos]

    # Open the positions BEFORE prompting for disconnect
    opens: list[tuple[str, str, float]] = []
    for s in syms_round:
        price = await _get_market_price(broker, s)
        if not price:
            continue
        o = await _open_entry_with_bracket(broker, s, price)
        if o is None:
            await _flatten(broker, s)
            continue
        opens.append((s, o[1], price))
    if len(opens) < 3:
        result.notes.append(
            f"axis (iv): opened only {len(opens)} positions; insufficient for joint axis"
        )
        for s, _, _ in opens:
            await _flatten(broker, s)
        return result

    print()
    print("=" * 72)
    print("  AXIS (iv) JOINT RECONNECT+CONCURRENT — OPERATOR ACTION REQUIRED")
    print("=" * 72)
    print("  1. Disconnect IBKR Gateway NOW.")
    print("  2. Script will fire %d concurrent-amend rounds every ~500ms" % num_trials)
    print("     across %d positions while disconnected." % len(opens))
    print("  3. When Gateway is back, type 'RECONNECTED' + Enter to resume.")
    print("=" * 72)

    reconnected = asyncio.Event()

    async def _watch_stdin() -> None:
        loop = asyncio.get_event_loop()
        while not reconnected.is_set():
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if line and "RECONNECT" in line.strip().upper():
                reconnected.set()
                return

    watcher = asyncio.create_task(_watch_stdin())
    try:
        for _ in range(num_trials):
            if reconnected.is_set():
                break
            coros = [_amend_one(broker, ulid, round(price - _safe_modified_stop_offset(price), 2))
                     for _, ulid, price in opens]
            outcomes = await asyncio.gather(*coros, return_exceptions=False)
            for rejected, _err in outcomes:
                result.n_trials += 1
                if rejected:
                    result.n_rejections += 1
            await asyncio.sleep(0.5)
    finally:
        if not watcher.done():
            watcher.cancel()
        await asyncio.sleep(2.0)
        for s, _, _ in opens:
            await _flatten(broker, s)

    if result.n_trials > 0:
        result.rejection_rate_pct = round(
            100.0 * result.n_rejections / result.n_trials, 2
        )
    result.wilson_upper_bound_pct = _wilson_upper_bound(
        result.n_rejections, result.n_trials
    )
    return result


# ---------------------------------------------------------------------------
# Measurement Mode C — H1 cancel-and-await latency
# ---------------------------------------------------------------------------


async def _measure_mode_c(
    broker: IBKRBroker, symbols: list[str], num_trials: int
) -> list[ModeCTrial]:
    log.info("=== Mode C: H1 cancel-and-await — %d trials ===", num_trials)
    trials: list[ModeCTrial] = []
    sym_idx = 0
    for trial_num in range(1, num_trials + 1):
        symbol = symbols[sym_idx % len(symbols)]
        sym_idx += 1
        price = await _get_market_price(broker, symbol)
        if not price:
            trials.append(ModeCTrial(symbol, False, 0.0, error="price_unavailable"))
            continue
        opened = await _open_entry_with_bracket(broker, symbol, price)
        if opened is None:
            trials.append(ModeCTrial(symbol, False, 0.0, error="entry_did_not_fill"))
            await _flatten(broker, symbol)
            continue
        t0 = time.monotonic()
        try:
            await broker.cancel_all_orders(symbol=symbol, await_propagation=True)
            rtt_ms = (time.monotonic() - t0) * 1000.0
            trials.append(ModeCTrial(symbol, True, round(rtt_ms, 2)))
        except CancelPropagationTimeout as e:
            rtt_ms = (time.monotonic() - t0) * 1000.0
            trials.append(ModeCTrial(symbol, False, round(rtt_ms, 2), error=str(e)))
        except Exception as e:
            rtt_ms = (time.monotonic() - t0) * 1000.0
            trials.append(ModeCTrial(symbol, False, round(rtt_ms, 2), error=str(e)))
        finally:
            await _flatten(broker, symbol)
        if trial_num % 10 == 0:
            log.info("  Mode C progress: %d/%d", trial_num, num_trials)
    return trials


# ---------------------------------------------------------------------------
# Measurement Mode D — N=100 cancel-then-immediate-SELL HARD GATE
# ---------------------------------------------------------------------------


def _classify_d_conflict(
    sell_result: Any, post_positions: list[Any], symbol: str, gap_ms: float
) -> tuple[bool, str | None]:
    """Inspect Mode D outcome for any of the four conflict signatures listed
    in the implementation prompt: bracket-child OCA conflict, locate
    suppression, position-state inconsistency, or any broker-side error."""
    if isinstance(sell_result, Exception):
        return True, f"sell_raised: {sell_result}"
    status = getattr(sell_result, "status", None)
    msg = getattr(sell_result, "message", "") or ""
    if status == OrderStatus.REJECTED:
        return True, f"sell_rejected: {msg}"
    msg_lower = msg.lower()
    if "oca" in msg_lower:
        return True, f"oca_conflict: {msg}"
    if "locate" in msg_lower:
        return True, f"locate_suppression: {msg}"
    # Position-state inconsistency: after the SELL completes the position
    # should land at zero (long flatten) or short (the bug we are guarding
    # against). Either short OR remaining long counts as a conflict.
    for p in post_positions:
        if p.symbol == symbol and p.shares != 0:
            return True, f"position_state_inconsistency: shares={p.shares}"
    if gap_ms > 50.0:
        # >50ms gap means cancel-await did not return quickly enough; this
        # is a soft signal but still recorded as a conflict for the gate.
        return True, f"cancel_to_sell_gap_too_large: {gap_ms:.1f}ms"
    return False, None


async def _measure_mode_d(
    broker: IBKRBroker, symbols: list[str], n_trials: int
) -> list[ModeDTrial]:
    log.info("=== Mode D: N=%d cancel-then-immediate-SELL HARD GATE ===", n_trials)
    trials: list[ModeDTrial] = []
    sym_idx = 0
    for trial_num in range(1, n_trials + 1):
        symbol = symbols[sym_idx % len(symbols)]
        sym_idx += 1
        price = await _get_market_price(broker, symbol)
        if not price:
            trials.append(ModeDTrial(symbol, True, 0.0,
                                     conflict_signature="price_unavailable"))
            continue
        opened = await _open_entry_with_bracket(broker, symbol, price)
        if opened is None:
            trials.append(ModeDTrial(symbol, True, 0.0,
                                     conflict_signature="entry_did_not_fill"))
            await _flatten(broker, symbol)
            continue
        # _open_entry_with_bracket already waited for the entry trade to
        # reach Filled status; the spike always opens 1 share.
        shares = 1
        sell_result: Any
        try:
            await broker.cancel_all_orders(symbol=symbol, await_propagation=True)
            t_after_cancel = time.monotonic()
            # <=10ms gap from cancel-return to SELL-fire per implementation
            # prompt Decision 2. Construct Order outside hot path; place
            # immediately.
            sell_order = _build_sell(symbol, shares)
            sell_result = await broker.place_order(sell_order)
            gap_ms = (time.monotonic() - t_after_cancel) * 1000.0
        except Exception as e:
            sell_result = e
            gap_ms = -1.0
        # Allow IBKR a beat to settle the SELL fill before sampling positions
        await asyncio.sleep(1.0)
        post = await broker.get_positions()
        conflict, sig = _classify_d_conflict(sell_result, post, symbol, gap_ms)
        trials.append(ModeDTrial(symbol, conflict, round(gap_ms, 2),
                                 conflict_signature=sig))
        await _flatten(broker, symbol)
        if trial_num % 10 == 0:
            log.info("  Mode D progress: %d/%d (conflicts so far: %d)",
                     trial_num, n_trials,
                     sum(1 for t in trials if t.conflict))
    return trials


# ---------------------------------------------------------------------------
# Decision rule
# ---------------------------------------------------------------------------


def _apply_decision_rule(
    worst_axis_ub: float,
    zero_conflict_in_100: bool,
    propagation_ok: bool,
) -> tuple[str, str | None, str | None]:
    """Returns (status, selected_mechanism, inconclusive_reason)."""
    if not propagation_ok:
        return ("INCONCLUSIVE", None,
                "modify_order auxPrice did not propagate deterministically; "
                "Mode A propagation check failed at >0% rate")
    if not zero_conflict_in_100:
        # H1 NOT eligible regardless of UB.
        if worst_axis_ub < 5.0:
            return ("PROCEED", "h2_amend", None)
        if worst_axis_ub < 20.0:
            return ("PROCEED", "h4_hybrid", None)
        return ("INCONCLUSIVE", None,
                f"H1 unsafe ({{conflicts in 100 trials}}) AND worst-axis "
                f"Wilson UB {worst_axis_ub:.1f}% >= 20%; alternative "
                "architectural fix required (likely Sprint 31.94 D3 or earlier)")
    # zero_conflict_in_100 == True
    if worst_axis_ub < 5.0:
        return ("PROCEED", "h2_amend", None)
    if worst_axis_ub < 20.0:
        return ("PROCEED", "h4_hybrid", None)
    return ("PROCEED", "h1_cancel_and_await", None)


# ---------------------------------------------------------------------------
# JSON aggregation + emit
# ---------------------------------------------------------------------------


def _build_results(
    mode_a: list[ModeATrial],
    axes: dict[str, AxisResult],
    mode_c: list[ModeCTrial],
    mode_d: list[ModeDTrial],
) -> dict[str, Any]:
    rtt_a = [t.round_trip_ms for t in mode_a if t.success]
    h2_p50 = _percentile(rtt_a, 50.0)
    h2_p95 = _percentile(rtt_a, 95.0)
    n_a = len(mode_a)
    n_a_rejected = sum(1 for t in mode_a if t.rejected)
    h2_rejection_rate = round(100.0 * n_a_rejected / n_a, 2) if n_a else 0.0
    h2_propagation = (
        n_a > 0 and all(t.propagation_ok for t in mode_a if t.success)
    )
    rtt_c = [t.round_trip_ms for t in mode_c if t.success]
    h1_p50 = _percentile(rtt_c, 50.0)
    h1_p95 = _percentile(rtt_c, 95.0)
    n_d = len(mode_d)
    n_d_conflict = sum(1 for t in mode_d if t.conflict)
    zero_conflict_in_100 = (n_d == 100 and n_d_conflict == 0)
    worst_axis_ub = max(
        (axes[k].wilson_upper_bound_pct for k in axes), default=100.0
    )
    status, mechanism, reason = _apply_decision_rule(
        worst_axis_ub, zero_conflict_in_100, h2_propagation
    )
    trial_count = (
        n_a
        + sum(a.n_trials for a in axes.values())
        + len(mode_c)
        + n_d
    )
    out: dict[str, Any] = {
        "status": status,
        "selected_mechanism": mechanism,
        "h2_modify_order_p50_ms": h2_p50,
        "h2_modify_order_p95_ms": h2_p95,
        "h2_rejection_rate_pct": h2_rejection_rate,
        "h2_deterministic_propagation": h2_propagation,
        "adversarial_axes_results": {k: asdict(v) for k, v in axes.items()},
        "worst_axis_wilson_ub": worst_axis_ub,
        "h1_cancel_all_orders_p50_ms": h1_p50,
        "h1_cancel_all_orders_p95_ms": h1_p95,
        "h1_propagation_n_trials": n_d,
        "h1_propagation_zero_conflict_in_100": zero_conflict_in_100,
        "trial_count": trial_count,
        "spike_run_date": _now_utc_iso(),
    }
    if reason is not None:
        out["inconclusive_reason"] = reason
    out["_raw"] = {
        "mode_a_trials": [asdict(t) for t in mode_a],
        "mode_c_trials": [asdict(t) for t in mode_c],
        "mode_d_trials": [asdict(t) for t in mode_d],
    }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _abort_with_inconclusive(
    broker: IBKRBroker, out_path: str, reason: str
) -> None:
    """Write an INCONCLUSIVE stub JSON + disconnect cleanly. Used by the
    pre-flight guards so an aborted run still leaves a parseable artifact
    on disk for the operator and the close-out skill."""
    results = {
        "status": "INCONCLUSIVE",
        "selected_mechanism": None,
        "inconclusive_reason": reason,
        "h2_modify_order_p50_ms": 0.0,
        "h2_modify_order_p95_ms": 0.0,
        "h2_rejection_rate_pct": 0.0,
        "h2_deterministic_propagation": False,
        "adversarial_axes_results": {},
        "worst_axis_wilson_ub": 100.0,
        "h1_cancel_all_orders_p50_ms": 0.0,
        "h1_cancel_all_orders_p95_ms": 0.0,
        "h1_propagation_n_trials": 0,
        "h1_propagation_zero_conflict_in_100": False,
        "trial_count": 0,
        "spike_run_date": _now_utc_iso(),
    }
    try:
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
    except Exception as e:
        log.warning("Could not write INCONCLUSIVE JSON to %s: %s", out_path, e)
    try:
        await broker.disconnect()
    except Exception:
        pass


async def main_async(args: argparse.Namespace) -> int:
    log.info(
        "Sprint 31.92 S1a Path #1 spike — account=%s clientId=%d symbols=%s",
        args.account, args.client_id, args.symbols,
    )
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if len(symbols) < 3:
        log.error("At least 3 symbols required for axes (i) + (iv); got %d", len(symbols))
        return 2
    if args.dry_run:
        log.warning("DRY RUN — script structure validated, no IBKR connection made")
        return 0

    # Guard 1: market-hours pre-flight (wall-clock + weekday). The spike
    # measures live `modify_order` semantics against working brackets;
    # outside the NYSE regular-hours window IBKR queues orders for the
    # next session and no fills occur. Refuse to proceed with a clear
    # error before paying any connection cost.
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

    # Cat A.2 (DEF-237): pre-spike position-sweep refusal-to-start gate per
    # Sprint 31.92 Tier 3 Review #2 verdict §Cat A.2. Mode D's 16/18 QQQ
    # contamination cluster in S1a v1 was caused by residual positions
    # carried over from a prior aborted spike run; the side-blind _flatten()
    # then doubled the short across the next trial. With Cat A.2's
    # three-branch _flatten() in place, the residual would now raise
    # SpikeShortPositionDetected mid-trial — but refusing to start at all
    # is strictly safer than discovering the problem on trial #N.
    #
    # Operator must clear residuals BEFORE re-running. The verified-safe
    # tooling is `scripts/ibkr_close_all_positions.py` (DEF-239 audited
    # 2026-04-30: imports `ib_async.Position` directly, signed-quantity
    # branching at L54-57, structurally inaccessible to DEF-204 bug class).
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
        sys.exit(2)

    # Qualify contracts once at startup. ib_async's `reqMktData()` hashes
    # the Contract for ticker-cache lookup, which requires `conId` to be
    # populated. `IBKRContractResolver.get_stock_contract()` returns a bare
    # Stock(); `qualify_contracts()` populates `conId` and overwrites the
    # cache with the qualified Contract. Also set delayed market-data type
    # once (paper accounts don't have real-time subscriptions by default).
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

    # Guard 2 + 3: attach IBKR error 399 detector so the smoke test can
    # distinguish "couldn't fill in 15s" from "queued for next session"
    # (NYSE holiday or wall-clock-passed-edge-cases the Guard 1 check
    # missed).
    detector = _MarketClosedDetector()
    broker._ib.errorEvent += detector

    out_path = args.output_json
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Guard 3: pre-measurement smoke test. One bracket on the first
    # symbol; if entry doesn't fill OR the queued-for-next-session
    # detector fires, abort before grinding through 50 Mode A trials of
    # the same failure.
    log.info("Smoke test: placing one bracket on %s to verify fills are live...", symbols[0])
    smoke_price = await _get_market_price(broker, symbols[0])
    if not smoke_price:
        log.error("Smoke test: could not fetch market price for %s. "
                  "Confirm market data subscription / Gateway connectivity.",
                  symbols[0])
        await _abort_with_inconclusive(
            broker, out_path,
            f"smoke test: market price unavailable for {symbols[0]}",
        )
        return 1
    smoke_opened = await _open_entry_with_bracket(broker, symbols[0], smoke_price)
    if detector.queued_for_next_session:
        log.error(
            "Smoke test: IBKR queued the order for the next session "
            "(error 399: %s). Market is closed; aborting. Re-run during "
            "live regular-hours session with ARGUS stopped.",
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
    log.info("Smoke test PASSED: bracket on %s filled cleanly. Proceeding.", symbols[0])
    await _flatten(broker, symbols[0])

    try:
        mode_a = await _measure_mode_a(broker, symbols, args.num_trials_per_axis)
        # Guard 4: first-trial sentinel for Mode A. If the first trial
        # failed entry-fill and Guard 3 didn't catch it, something
        # changed mid-run (Gateway disconnect, market-hours edge). Halt
        # rather than grind through 49 more identical failures.
        if mode_a and mode_a[0].error == "entry_did_not_fill":
            raise RuntimeError(
                "Mode A trial 1 entry did not fill despite smoke-test pass; "
                "likely mid-run Gateway disconnect or market-state change."
            )
        axes = {
            AXIS_CONCURRENT: await _axis_concurrent(broker, symbols, max(30, args.num_trials_per_axis // 2)),
            AXIS_RECONNECT: await _axis_reconnect(broker, symbols, max(30, args.num_trials_per_axis // 2)),
            AXIS_STALE_ID: await _axis_stale_id(broker, symbols, max(30, args.num_trials_per_axis // 2)),
            AXIS_JOINT: await _axis_joint(broker, symbols, max(30, args.num_trials_per_axis // 2)),
        }
        mode_c = await _measure_mode_c(broker, symbols, args.num_trials_per_axis)
        mode_d = await _measure_mode_d(broker, symbols, args.n_stress_trials)
    except Exception as e:
        log.exception("Spike crashed mid-run: %s", e)
        results = {
            "status": "INCONCLUSIVE",
            "selected_mechanism": None,
            "inconclusive_reason": f"spike crashed: {e}",
            "h2_modify_order_p50_ms": 0.0,
            "h2_modify_order_p95_ms": 0.0,
            "h2_rejection_rate_pct": 0.0,
            "h2_deterministic_propagation": False,
            "adversarial_axes_results": {},
            "worst_axis_wilson_ub": 100.0,
            "h1_cancel_all_orders_p50_ms": 0.0,
            "h1_cancel_all_orders_p95_ms": 0.0,
            "h1_propagation_n_trials": 0,
            "h1_propagation_zero_conflict_in_100": False,
            "trial_count": 0,
            "spike_run_date": _now_utc_iso(),
        }
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        try:
            await broker.disconnect()
        except Exception:
            pass
        return 1

    results = _build_results(mode_a, axes, mode_c, mode_d)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log.info("Results written to %s", out_path)

    print()
    print("=" * 72)
    print("SPRINT 31.92 S1a — PATH #1 MECHANISM SPIKE — RESULTS")
    print("=" * 72)
    print(f"  status:              {results['status']}")
    print(f"  selected_mechanism:  {results['selected_mechanism']}")
    print(f"  h2 modify p50/p95:   {results['h2_modify_order_p50_ms']:.1f}ms / "
          f"{results['h2_modify_order_p95_ms']:.1f}ms")
    print(f"  h2 rejection rate:   {results['h2_rejection_rate_pct']:.2f}%")
    print(f"  h2 deterministic:    {results['h2_deterministic_propagation']}")
    print(f"  worst-axis Wilson UB:{results['worst_axis_wilson_ub']:.2f}%")
    for k, v in results["adversarial_axes_results"].items():
        print(f"    {k:>40}: {v['n_rejections']}/{v['n_trials']} rej "
              f"(UB {v['wilson_upper_bound_pct']:.2f}%)")
    print(f"  h1 cancel p50/p95:   {results['h1_cancel_all_orders_p50_ms']:.1f}ms / "
          f"{results['h1_cancel_all_orders_p95_ms']:.1f}ms")
    print(f"  zero-conflict-in-100:{results['h1_propagation_zero_conflict_in_100']} "
          f"(N={results['h1_propagation_n_trials']})")
    if "inconclusive_reason" in results:
        print(f"  inconclusive_reason: {results['inconclusive_reason']}")
    print("=" * 72)

    try:
        await broker.disconnect()
    except Exception as e:
        log.warning("Disconnect raised (non-fatal): %s", e)

    if results["status"] == "PROCEED":
        if results["selected_mechanism"] == "h1_cancel_and_await":
            print()
            print("  H1 selected — operator written confirmation REQUIRED before")
            print("  S2a/S2b implementation prompts may be generated.")
            print()
        return 0
    return 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sprint 31.92 S1a Path #1 mechanism spike (paper IBKR)"
    )
    p.add_argument("--account", required=True,
                   help="IBKR account ID (e.g., U24619949)")
    p.add_argument("--client-id", type=int, default=1,
                   help="IBKR clientId (default 1; 2 reserved for parallel S1b)")
    p.add_argument("--num-trials-per-axis", type=int, default=50,
                   help="Trials per measurement mode A/B/C (default 50; "
                        "axes use max(30, N//2))")
    p.add_argument("--n-stress-trials", type=int, default=100,
                   help="HARD GATE per Decision 2: cancel-then-SELL stress "
                        "trials (default 100; do not reduce)")
    p.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                   help="Comma-separated symbols for trials "
                        "(default SPY,QQQ,IWM,XLF; need >=3)")
    p.add_argument(
        "--output-json",
        default="scripts/spike-results/spike-def204-round2-path1-results.json",
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
    if args.n_stress_trials != 100:
        log.warning(
            "n-stress-trials=%d differs from HARD GATE default 100; "
            "Decision 2 requires N=100 for the gate to bind.",
            args.n_stress_trials,
        )
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
