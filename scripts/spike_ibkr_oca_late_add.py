"""
Sprint 31.91 — Phase A revisit spike: IBKR OCA late-add behavior

Tests IBKR's behavior when an order is submitted to an OCA group AFTER one
member has already filled. This is the foundational mechanism question for
Sprint 31.91 (Adversarial Review Finding B1).

Three plausible IBKR behaviors:
  (a) REJECT — late-add returned with API error / cancelled before working
  (b) ACCEPT_AS_STANDALONE — late-add accepted, treated as fresh group of 1
      (mechanism NOT closed for IMSR scenario)
  (c) AUTO_CANCEL — late-add briefly accepted then auto-cancelled within ~1s

The spike runs three variants at delays of 100ms, 500ms, and 2s post-fill
to distinguish (a)/(b)/(c) reliably.

Test sequence (per delay variant):
  1. Connect to IBKR Gateway via ib_async (default clientId=99 to avoid
     ARGUS collision at clientId=1)
  2. BUY 1 share of test symbol (default SPY) at market — gives us a position
  3. Submit Order A: SELL LIMIT 1 share at aggressive price (will fill),
     ocaGroup=<unique>, ocaType=1
  4. Submit Order B: SELL LIMIT 1 share at far-from-market (won't fill),
     same ocaGroup, ocaType=1
  5. Wait for Order A fill — confirms OCA group has triggered
  6. Verify Order B was auto-cancelled by IBKR (sanity check on OCA semantics)
  7. Wait `delay_ms` post-fill
  8. Submit Order C: SELL LIMIT 1 share at far-from-market with same ocaGroup,
     ocaType=1
  9. Wait 5 seconds, observe Order C final status
 10. Cleanup: cancel any working orders, ensure flat position

Expected mappings:
  - Order C status `Submitted` (working) at 5s         → case (b) — UNSAFE
  - Order C status `Cancelled` within ~1s              → case (c)
  - Order C rejection / API error before `Submitted`   → case (a) — SAFE

Result interpretation across the 3 delays:
  - All three cases (a) → Sessions 1a+1b architecture is sound; proceed
  - All three cases (b) → late-add architecture insufficient; reformulate
    Session 1b around cancel-then-place-with-await pattern
  - Mixed → race-window-dependent; need finer analysis

USAGE:
  # Recommended: stop ARGUS first
  python spike_ibkr_oca_late_add.py --port 4002 --client-id 99 --symbol SPY

  # Or concurrent with ARGUS at clientId=1 (separate clientId)
  python spike_ibkr_oca_late_add.py --port 4002 --client-id 99 --symbol SPY \
      --output spike-results-2026-04-27.json

REQUIREMENTS:
  - ib_async installed (matches ARGUS's pin)
  - IBKR Gateway running on the specified port (paper account)
  - Market hours (orders need to actually fill on real liquidity)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import cast

# ib_async API surface — matches ARGUS's import pattern
try:
    from ib_async import IB, Contract, LimitOrder, MarketOrder, Stock, Trade
except ImportError:
    print(
        "ERROR: ib_async not installed. Install with: pip install ib_async",
        file=sys.stderr,
    )
    sys.exit(1)


# Logging — keep it visible; this is operator-run, results matter
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("oca-spike")
# Quiet ib_async's chattier loggers
logging.getLogger("ib_async").setLevel(logging.WARNING)


# Outcome classification per the spec
OUTCOME_REJECTED_PRE_SUBMIT = "rejected_pre_submit"
OUTCOME_ACCEPTED_AS_STANDALONE = "accepted_as_standalone"
OUTCOME_AUTO_CANCELLED = "auto_cancelled"
OUTCOME_UNCLASSIFIED = "unclassified"
OUTCOME_ERROR = "error"


@dataclass
class TrialResult:
    """Result of one spike trial at a specific post-fill delay."""

    delay_ms: int
    oca_group_id: str
    order_a_id: int | None = None
    order_b_id: int | None = None
    order_c_id: int | None = None
    order_a_filled: bool = False
    order_b_status_after_a_fills: str | None = None
    order_c_initial_status: str | None = None
    order_c_final_status: str | None = None
    order_c_status_history: list[str] = field(default_factory=list)
    order_c_error: str | None = None
    outcome: str = OUTCOME_UNCLASSIFIED
    notes: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class SpikeResults:
    """Top-level spike result dump."""

    started_at_utc: str
    finished_at_utc: str
    symbol: str
    client_id: int
    port: int
    ib_async_version: str | None
    trials: list[TrialResult] = field(default_factory=list)
    overall_outcome: str = "pending"
    overall_interpretation: str = ""


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ms() -> int:
    return int(time.time() * 1000)


async def _wait_for_fill(ib: IB, trade: Trade, timeout_s: float = 10.0) -> bool:
    """Wait for a trade to fill or timeout. Returns True if filled."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        # ib_async populates trade.orderStatus.status as it changes
        status = trade.orderStatus.status
        if status == "Filled":
            return True
        if status in ("Cancelled", "ApiCancelled", "Inactive"):
            return False
        await asyncio.sleep(0.05)
    return False


async def _capture_order_c_lifecycle(
    ib: IB, trade_c: Trade, observation_seconds: float = 5.0
) -> tuple[list[str], str | None]:
    """Watch Order C's status for `observation_seconds` and capture history.

    Returns (status_history, final_status). Final status is the last observed
    non-empty status.
    """
    history: list[str] = []
    last_seen: str | None = None
    deadline = time.time() + observation_seconds
    while time.time() < deadline:
        s = trade_c.orderStatus.status
        if s and s != last_seen:
            history.append(f"{_ms()}:{s}")
            last_seen = s
        await asyncio.sleep(0.02)
    return history, last_seen


def _classify_outcome(trial: TrialResult) -> str:
    """Map observed Order C status sequence to one of the three cases."""
    if trial.order_c_error and trial.order_c_initial_status in (None, ""):
        return OUTCOME_REJECTED_PRE_SUBMIT
    final = trial.order_c_final_status or ""
    if final in ("Submitted", "PreSubmitted"):
        return OUTCOME_ACCEPTED_AS_STANDALONE
    if final in ("Cancelled", "ApiCancelled", "Inactive"):
        # Distinguish "cancelled because of OCA semantics" from "rejected pre-submit"
        # by checking whether the order ever reached Submitted state.
        was_submitted = any(
            "Submitted" in s or "PreSubmitted" in s for s in trial.order_c_status_history
        )
        if was_submitted:
            return OUTCOME_AUTO_CANCELLED
        return OUTCOME_REJECTED_PRE_SUBMIT
    return OUTCOME_UNCLASSIFIED


async def _ensure_flat(ib: IB, contract: Contract) -> None:
    """Cancel all open orders for the symbol; close any position to flat."""
    log.info("Cleanup: cancelling open orders + flattening position…")

    # Cancel anything open
    open_trades = [t for t in ib.openTrades() if t.contract.symbol == contract.symbol]
    for t in open_trades:
        try:
            ib.cancelOrder(t.order)
        except Exception as e:
            log.warning("Cleanup: cancelOrder failed for %s: %s", t.order.orderId, e)
    if open_trades:
        await asyncio.sleep(0.5)

    # Close any net position
    positions = [p for p in ib.positions() if p.contract.symbol == contract.symbol]
    for p in positions:
        if abs(p.position) > 0:
            close_order = MarketOrder(
                "SELL" if p.position > 0 else "BUY", abs(int(p.position))
            )
            close_order.tif = "DAY"
            log.info(
                "Cleanup: closing %s position of %d shares",
                "long" if p.position > 0 else "short",
                abs(int(p.position)),
            )
            close_trade = ib.placeOrder(p.contract, close_order)
            await _wait_for_fill(ib, close_trade, timeout_s=5.0)

    log.info("Cleanup complete.")


async def _run_one_trial(
    ib: IB, contract: Contract, current_price: float, delay_ms: int, trial_num: int
) -> TrialResult:
    """Run one spike trial at the given post-fill delay."""
    start = time.time()
    oca_group = f"oca-spike-{uuid.uuid4().hex[:12]}"
    trial = TrialResult(delay_ms=delay_ms, oca_group_id=oca_group)

    log.info(
        "=== Trial %d (delay=%dms, oca_group=%s) ===", trial_num, delay_ms, oca_group
    )

    try:
        # Step 1: BUY 1 share at market to give us a long position
        log.info("Step 1: BUY 1 share %s at market", contract.symbol)
        buy = MarketOrder("BUY", 1)
        buy.tif = "DAY"
        buy_trade = ib.placeOrder(contract, buy)
        if not await _wait_for_fill(ib, buy_trade, timeout_s=5.0):
            trial.notes.append("Initial BUY did not fill within 5s — aborting trial")
            trial.outcome = OUTCOME_ERROR
            return trial

        # Step 2: Order A — MARKET SELL (will fill immediately regardless
        # of price-staleness in our delayed-data view; Order A is the OCA
        # trigger leg and we don't care what price it fills at, only that
        # the OCA group transitions to "triggered" state).
        order_a = MarketOrder("SELL", 1)
        order_a.tif = "DAY"
        order_a.ocaGroup = oca_group
        order_a.ocaType = 1  # Cancel with block
        order_a.transmit = True

        # Step 3: Order B — far-from-market SELL LIMIT (won't fill)
        far_price = round(current_price * 1.50, 2)
        order_b = LimitOrder("SELL", 1, far_price)
        order_b.tif = "DAY"
        order_b.ocaGroup = oca_group
        order_b.ocaType = 1
        order_b.transmit = True

        log.info(
            "Step 2-3: placing Order A (MARKET trigger) and Order B (far LIMIT @ %.2f) in OCA group",
            far_price,
        )
        trade_a = ib.placeOrder(contract, order_a)
        trade_b = ib.placeOrder(contract, order_b)
        trial.order_a_id = trade_a.order.orderId
        trial.order_b_id = trade_b.order.orderId

        # Step 4: Wait for Order A fill
        log.info("Step 4: waiting for Order A fill…")
        a_filled = await _wait_for_fill(ib, trade_a, timeout_s=10.0)
        trial.order_a_filled = a_filled
        if not a_filled:
            trial.notes.append("Order A did not fill within 10s — aborting trial")
            trial.outcome = OUTCOME_ERROR
            return trial

        # Step 5: Sanity check — Order B should be auto-cancelled by OCA
        # Give IBKR ~500ms to propagate the OCA cancellation
        await asyncio.sleep(0.5)
        b_status = trade_b.orderStatus.status
        trial.order_b_status_after_a_fills = b_status
        log.info("Order B status after A fills: %s", b_status)
        if b_status not in ("Cancelled", "ApiCancelled", "Inactive"):
            trial.notes.append(
                f"OCA semantics SANITY FAILURE: Order B status is {b_status!r}, "
                f"expected Cancelled. ocaType=1 may not be working as expected."
            )

        # Step 6: Wait the configured delay post-fill
        # (We've already used ~500ms for the sanity check; subtract that)
        already_waited_ms = 500
        remaining_delay = max(0, delay_ms - already_waited_ms)
        if remaining_delay > 0:
            log.info("Step 6: waiting additional %dms (delay=%dms total)", remaining_delay, delay_ms)
            await asyncio.sleep(remaining_delay / 1000.0)

        # Step 7: Submit Order C — late-add to the same OCA group
        order_c = LimitOrder("SELL", 1, far_price)
        order_c.tif = "DAY"
        order_c.ocaGroup = oca_group
        order_c.ocaType = 1
        order_c.transmit = True

        log.info("Step 7: submitting Order C (late-add) with ocaGroup=%s", oca_group)
        try:
            trade_c = ib.placeOrder(contract, order_c)
            trial.order_c_id = trade_c.order.orderId
            # Give IBKR a beat to acknowledge before reading status
            await asyncio.sleep(0.1)
            trial.order_c_initial_status = trade_c.orderStatus.status
            log.info("Order C initial status: %s", trial.order_c_initial_status)

            # Step 8: Watch Order C lifecycle for 5 seconds
            history, final = await _capture_order_c_lifecycle(
                ib, trade_c, observation_seconds=5.0
            )
            trial.order_c_status_history = history
            trial.order_c_final_status = final
            log.info("Order C final status: %s (history: %s)", final, history)
        except Exception as e:
            trial.order_c_error = str(e)
            log.warning("Order C placement raised: %s", e)

        # Classify
        trial.outcome = _classify_outcome(trial)
        log.info("Trial %d outcome: %s", trial_num, trial.outcome)

    finally:
        await _ensure_flat(ib, contract)
        trial.elapsed_seconds = round(time.time() - start, 2)

    return trial


def _interpret_overall(trials: list[TrialResult]) -> tuple[str, str]:
    """Map trial outcomes to overall interpretation for the operator."""
    outcomes = [t.outcome for t in trials]
    unique = set(outcomes)

    if unique == {OUTCOME_REJECTED_PRE_SUBMIT}:
        return (
            "PATH_1_SAFE",
            "All three delay variants showed Order C rejected pre-submit. "
            "IBKR enforces that an OCA group, once triggered, refuses new "
            "members. Sessions 1a+1b architecture is SOUND. Proceed with "
            "spec amendments per other findings.",
        )
    if unique == {OUTCOME_ACCEPTED_AS_STANDALONE}:
        return (
            "PATH_2_REFORMULATE",
            "All three delay variants showed Order C accepted as a working "
            "standalone order. IBKR treats a triggered OCA group as 'just a "
            "string label' — late-add becomes a fresh group of 1. Sessions "
            "1a+1b INSUFFICIENT for late-add cases. Reformulate Session 1b "
            "around cancel-then-place-with-await pattern (mirroring Session "
            "1c). OCA grouping retained for bracket-internal races only.",
        )
    if unique == {OUTCOME_AUTO_CANCELLED}:
        return (
            "PATH_3_RACE_DEPENDENT",
            "All three delay variants showed Order C auto-cancelled. IBKR "
            "appears to detect post-trigger OCA group state but does so "
            "asynchronously. Behavior is race-window-dependent. Recommend "
            "treating as Path 2 for safety: explicit cancel-then-place-with-"
            "await is more robust than relying on async auto-cancel.",
        )
    # Mixed
    return (
        "PATH_MIXED_NEEDS_ANALYSIS",
        f"Mixed outcomes across delays: {dict(zip([t.delay_ms for t in trials], outcomes))}. "
        "Behavior is delay-sensitive. Likely a race-window between order acceptance "
        "and OCA-group-state propagation. Recommend treating as Path 2 for safety.",
    )


async def main_async(args: argparse.Namespace) -> int:
    started = _now_utc()
    log.info(
        "Sprint 31.91 OCA late-add spike — port=%d clientId=%d symbol=%s",
        args.port,
        args.client_id,
        args.symbol,
    )

    ib = IB()
    try:
        await ib.connectAsync(
            host=args.host, port=args.port, clientId=args.client_id, timeout=10
        )
        log.info("Connected to IBKR Gateway.")

        # Use delayed market data (type 3) — paper accounts don't include
        # real-time data subscriptions by default, but delayed is free and
        # sufficient for the spike. Order execution is real-time regardless
        # of market data tier.
        ib.reqMarketDataType(3)
        log.info("Switched to delayed market data (type 3, 15-min stale).")
    except Exception as e:
        log.error("Failed to connect to IBKR Gateway: %s", e)
        log.error(
            "Verify: (1) IBKR Gateway running on port %d; "
            "(2) clientId %d not in use by another connection (ARGUS uses 1); "
            "(3) paper account selected.",
            args.port,
            args.client_id,
        )
        return 2

    try:
        # Resolve contract. ib_async's qualifyContractsAsync return type is a
        # union (Contract | list[Contract | None] | None) that pyright cannot
        # narrow cleanly through subscripting; cast once after the runtime
        # checks have eliminated all the unsafe variants.
        stock = Stock(args.symbol, "SMART", "USD")
        contracts = await ib.qualifyContractsAsync(stock)
        if not isinstance(contracts, list) or not contracts or contracts[0] is None:
            log.error("Could not qualify contract %s", args.symbol)
            return 3
        contract = cast(Contract, contracts[0])

        # Get current price (use last/mid from market data)
        ticker = ib.reqMktData(contract, "", False, False)
        # Delayed data sometimes takes 3-5s to populate; give it room.
        await asyncio.sleep(4.0)

        # Try multiple price sources in priority order. With delayed data
        # (type 3), `last`/`close` are typically None and the populated
        # fields are `delayedLast` / `delayedClose`. `marketPrice()` is
        # ib_async's smart fallback that handles both cases.
        candidates = [
            ("marketPrice()", ticker.marketPrice()),
            ("last", ticker.last),
            ("delayedLast", getattr(ticker, "delayedLast", None)),
            ("close", ticker.close),
            ("delayedClose", getattr(ticker, "delayedClose", None)),
            ("midpoint()", ticker.midpoint()),
        ]
        current_price = None
        price_source = None
        for name, val in candidates:
            try:
                if val is not None and val > 0 and val == val:  # NaN check
                    current_price = float(val)
                    price_source = name
                    break
            except (TypeError, ValueError):
                continue

        if not current_price:
            log.error(
                "Could not get current price for %s — tried: %s. Is the market open?",
                args.symbol,
                ", ".join(f"{n}={v}" for n, v in candidates),
            )
            return 4
        log.info(
            "Current price for %s: %.2f (source: %s)",
            args.symbol,
            current_price,
            price_source,
        )

        # Run trials
        delays_ms = [int(d.strip()) for d in args.delays.split(",")]
        results = SpikeResults(
            started_at_utc=started,
            finished_at_utc="",
            symbol=args.symbol,
            client_id=args.client_id,
            port=args.port,
            ib_async_version=getattr(__import__("ib_async"), "__version__", None),
        )

        for i, delay_ms in enumerate(delays_ms, start=1):
            try:
                trial = await _run_one_trial(ib, contract, current_price, delay_ms, i)
            except Exception as e:
                log.exception("Trial %d crashed: %s", i, e)
                trial = TrialResult(delay_ms=delay_ms, oca_group_id=f"crashed-{i}")
                trial.outcome = OUTCOME_ERROR
                trial.notes.append(f"crashed: {e}")
                # Best-effort cleanup
                try:
                    await _ensure_flat(ib, contract)
                except Exception:
                    pass
            results.trials.append(trial)
            # Inter-trial cooldown
            await asyncio.sleep(2.0)

        results.finished_at_utc = _now_utc()
        results.overall_outcome, results.overall_interpretation = _interpret_overall(
            results.trials
        )

        # Persist
        out_path = args.output or f"spike-results-{int(time.time())}.json"
        with open(out_path, "w") as f:
            json.dump(asdict(results), f, indent=2, default=str)
        log.info("Results written to %s", out_path)

        # Summary
        print()
        print("=" * 72)
        print("SPRINT 31.91 OCA LATE-ADD SPIKE — RESULTS")
        print("=" * 72)
        for t in results.trials:
            print(
                f"  delay={t.delay_ms:>5}ms | outcome={t.outcome:<28} | "
                f"order_c_final={t.order_c_final_status!s:<12}"
            )
        print("-" * 72)
        print(f"OVERALL: {results.overall_outcome}")
        print()
        print(results.overall_interpretation)
        print("=" * 72)
        return 0

    finally:
        # Final defensive cleanup
        try:
            contract_for_cleanup = Stock(args.symbol, "SMART", "USD")
            cs = await ib.qualifyContractsAsync(contract_for_cleanup)
            if isinstance(cs, list) and cs and cs[0] is not None:
                await _ensure_flat(ib, cast(Contract, cs[0]))
        except Exception as e:
            log.warning("Final cleanup pass had an issue (non-fatal): %s", e)
        ib.disconnect()
        log.info("Disconnected from IBKR Gateway.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="IBKR OCA late-add behavior spike (Sprint 31.91 Phase A)"
    )
    p.add_argument(
        "--host", default="127.0.0.1", help="IBKR Gateway host (default 127.0.0.1)"
    )
    p.add_argument(
        "--port",
        type=int,
        default=4002,
        help="IBKR Gateway port (4002 paper, 4001 live; default 4002)",
    )
    p.add_argument(
        "--client-id",
        type=int,
        default=99,
        help="IBKR clientId (default 99 — avoids ARGUS at clientId=1)",
    )
    p.add_argument(
        "--symbol",
        default="SPY",
        help="Test symbol (default SPY — high liquidity, not in ARGUS scanner)",
    )
    p.add_argument(
        "--delays",
        default="100,500,2000",
        help="Comma-separated post-fill delays in ms (default 100,500,2000)",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default spike-results-<timestamp>.json)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        log.warning("Interrupted by user — attempting cleanup")
        return 130


if __name__ == "__main__":
    sys.exit(main())