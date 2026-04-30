"""
Sprint 31.92, Session 1b — Phase A diagnostic spike: IBKR locate-rejection
fingerprint + hard-to-borrow microcap suppression-window calibration.

Probes the broker exception surface for hard-to-borrow microcaps (PCT-class)
to capture (a) the exact substring fingerprint of locate-rejection errors
(H5) and (b) the empirical hold-pending-borrow release window (H6). Output
JSON's `fingerprint_string` and `recommended_locate_suppression_seconds`
fields gate Phase D impl prompts S3a + S3b.

Per-trial protocol:
  1. BUY a small qty (default 1 share) at market — establish a long position.
  2. Wait for fill confirmation (≤10s).
  3. Force-emit a SELL on the same qty via raw ib_async (mirrors how
     IBKRBroker.place_order would route — but standalone so the spike does
     not depend on OrderManager wiring).
  4. Watch the SELL order's lifecycle for up to `case_a_max_age_seconds`
     (default 30s):
       * If a locate-rejection error fires within ≤2s → case B. Capture
         the error string for fingerprinting.
       * If the order stays Submitted/PreSubmitted >2s without rejecting
         AND without filling → case A (held pending borrow). If it later
         fills before the watchdog cancels it, record a release event
         with elapsed-time-from-submit measurement.
  5. Cleanup: cancel the SELL if still working; flatten any residual
     long position via a fresh MARKET SELL (cleanup-path errors
     swallowed — non-disruptive).

NOT SAFE DURING TRADING. Run pre-market or after-hours only. Account
U24619949 / clientId=2 (clientId=1 reserved for parallel S1a).

USAGE:
  python scripts/spike_def204_round2_path2.py \\
      --account U24619949 --client-id 2 \\
      --symbols PCT,ACHR,PDYN,HPK,MX,NVD \\
      --trials-per-symbol 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import cast

try:
    from ib_async import IB, Contract, MarketOrder, Stock, Trade
except ImportError:
    print("ERROR: ib_async not installed. Install with: pip install ib_async", file=sys.stderr)
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("def204-r2-path2-spike")
logging.getLogger("ib_async").setLevel(logging.WARNING)


# H5 candidate fingerprint (verified against operator-curated trial set).
DEFAULT_FINGERPRINT_CANDIDATE = "contract is not available for short sale"
CASE_B_RAISE_WINDOW_SECONDS = 2.0
CANONICAL_SYMBOL = "PCT"


@dataclass
class TrialResult:
    symbol: str
    trial_index: int
    sell_order_id: int | None = None
    case: str = "unknown"  # "A" (held), "B" (rejected), "none" (no observation), "error"
    error_string: str | None = None
    pending_seconds: float = 0.0
    released: bool = False
    release_seconds: float | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class SpikeResults:
    status: str = "INCONCLUSIVE"
    fingerprint_string: str = ""
    fingerprint_stable: bool = False
    case_a_observed: bool = False
    case_a_count: int = 0
    case_b_count: int = 0
    case_a_max_age_seconds: int = 0
    release_events_observed: int = 0
    release_p50_seconds: float | None = None
    release_p95_seconds: float | None = None
    release_p99_seconds: float | None = None
    release_max_seconds: float | None = None
    recommended_locate_suppression_seconds: int = 18000
    symbols_tested: list[str] = field(default_factory=list)
    trials_per_symbol: int = 0
    spike_run_date: str = ""
    trials: list[TrialResult] = field(default_factory=list)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    return float(statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1]) if len(values) >= 2 else float(values[0])


def _longest_common_substring(strings: list[str]) -> str:
    """Return the longest substring that appears in every input string.

    Used as the case-B fingerprint when not all observations agree on the
    canonical candidate. Empty input → empty string.
    """
    if not strings:
        return ""
    shortest = min(strings, key=len).lower()
    longest = ""
    for length in range(len(shortest), 0, -1):
        for start in range(len(shortest) - length + 1):
            candidate = shortest[start : start + length]
            if all(candidate in s.lower() for s in strings):
                if len(candidate) > len(longest):
                    longest = candidate
        if longest:
            break
    return longest


async def _wait_for_fill(ib: IB, trade: Trade, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = trade.orderStatus.status
        if status == "Filled":
            return True
        if status in ("Cancelled", "ApiCancelled", "Inactive"):
            return False
        await asyncio.sleep(0.05)
    return False


async def _ensure_flat(ib: IB, contract: Contract) -> None:
    """Best-effort cleanup: cancel open orders for symbol; flatten residual qty."""
    try:
        for t in [t for t in ib.openTrades() if t.contract.symbol == contract.symbol]:
            try:
                ib.cancelOrder(t.order)
            except Exception:
                pass
        await asyncio.sleep(0.5)
        for p in [p for p in ib.positions() if p.contract.symbol == contract.symbol]:
            if abs(p.position) > 0:
                close = MarketOrder("SELL" if p.position > 0 else "BUY", abs(int(p.position)))
                close.tif = "DAY"
                close_trade = ib.placeOrder(p.contract, close)
                await _wait_for_fill(ib, close_trade, timeout_s=5.0)
    except Exception as e:
        log.warning("Cleanup non-fatal error for %s: %s", contract.symbol, e)


async def _run_one_trial(
    ib: IB,
    contract: Contract,
    symbol: str,
    trial_index: int,
    case_a_max_age_seconds: int,
    error_capture: dict[int, str],
) -> TrialResult:
    """Establish long, force a SELL, classify case A vs B, observe release."""
    trial = TrialResult(symbol=symbol, trial_index=trial_index)
    log.info("=== %s trial %d ===", symbol, trial_index)

    try:
        buy = MarketOrder("BUY", 1)
        buy.tif = "DAY"
        buy_trade = ib.placeOrder(contract, buy)
        if not await _wait_for_fill(ib, buy_trade, timeout_s=10.0):
            trial.case = "error"
            trial.notes.append("BUY entry did not fill within 10s — skipping trial")
            return trial

        # Force the SELL emission. The qty matches the long position; no OCA
        # decoration; the SELL is standalone — mirrors the canonical Path #2
        # emission shape (`_flatten_position`, `_trail_flatten`, etc.).
        sell = MarketOrder("SELL", 1)
        sell.tif = "DAY"
        submit_at = time.monotonic()
        sell_trade = ib.placeOrder(contract, sell)
        trial.sell_order_id = sell_trade.order.orderId

        deadline = submit_at + case_a_max_age_seconds
        case_b_window_end = submit_at + CASE_B_RAISE_WINDOW_SECONDS
        last_status = ""

        while time.monotonic() < deadline:
            status = sell_trade.orderStatus.status
            now = time.monotonic()
            err = error_capture.get(trial.sell_order_id or -1)

            # Case B: locate-rejection arrived (via errorEvent or terminal status).
            if err is not None and now <= case_b_window_end + 1.0:
                trial.case = "B"
                trial.error_string = err
                trial.pending_seconds = round(now - submit_at, 3)
                log.info("  case B: rejected within %.2fs — %r", trial.pending_seconds, err)
                break
            # Case A → release-event branch.
            if status == "Filled":
                trial.released = True
                trial.release_seconds = round(now - submit_at, 3)
                trial.case = "A" if (now - submit_at) > CASE_B_RAISE_WINDOW_SECONDS else "B"
                trial.pending_seconds = trial.release_seconds
                log.info(
                    "  fill at %.2fs (case=%s; release_event=%s)",
                    trial.release_seconds,
                    trial.case,
                    trial.released,
                )
                break
            # Case B via terminal status without explicit error string (rare).
            if status in ("Cancelled", "ApiCancelled", "Inactive") and now <= case_b_window_end + 1.0:
                trial.case = "B"
                trial.error_string = err or f"terminal_status:{status}"
                trial.pending_seconds = round(now - submit_at, 3)
                log.info("  case B (terminal): %s", trial.error_string)
                break

            if status != last_status and status:
                log.debug("  %s @ %.2fs", status, now - submit_at)
                last_status = status
            await asyncio.sleep(0.1)
        else:
            # Watchdog timed out without classification → case A (held).
            trial.case = "A"
            trial.pending_seconds = round(time.monotonic() - submit_at, 3)
            log.info("  case A: held %s for %.2fs (no fill, no reject)", symbol, trial.pending_seconds)

    finally:
        await _ensure_flat(ib, contract)

    return trial


def _compute_summary(results: SpikeResults, case_a_max_age: int) -> None:
    """Populate aggregate fields on `results` from `results.trials`."""
    case_b_strings = [t.error_string for t in results.trials if t.case == "B" and t.error_string]
    case_a_pendings = [t.pending_seconds for t in results.trials if t.case == "A"]
    release_seconds = [t.release_seconds for t in results.trials if t.released and t.release_seconds is not None]

    results.case_b_count = sum(1 for t in results.trials if t.case == "B")
    results.case_a_count = sum(1 for t in results.trials if t.case == "A")
    results.case_a_observed = results.case_a_count > 0
    results.case_a_max_age_seconds = int(max(case_a_pendings)) if case_a_pendings else 0
    results.release_events_observed = len(release_seconds)

    if case_b_strings:
        lower = [s.lower() for s in case_b_strings]
        if all(DEFAULT_FINGERPRINT_CANDIDATE in s for s in lower):
            results.fingerprint_string = DEFAULT_FINGERPRINT_CANDIDATE
            results.fingerprint_stable = len(set(lower)) == 1 or all(DEFAULT_FINGERPRINT_CANDIDATE in s for s in lower)
        else:
            common = _longest_common_substring(case_b_strings)
            results.fingerprint_string = common
            results.fingerprint_stable = False

    if release_seconds:
        results.release_p50_seconds = round(_percentile(release_seconds, 50), 3)
        results.release_p95_seconds = round(_percentile(release_seconds, 95), 3)
        results.release_p99_seconds = round(_percentile(release_seconds, 99), 3)
        results.release_max_seconds = round(max(release_seconds), 3)
        results.recommended_locate_suppression_seconds = max(
            18000, min(86400, int(results.release_p99_seconds * 1.2))
        )
    else:
        # H6 rules-out: no observed releases → fall back to 5hr conservative default.
        results.recommended_locate_suppression_seconds = 18000


def _determine_status(results: SpikeResults, pct_reachable: bool) -> str:
    if not pct_reachable or CANONICAL_SYMBOL not in results.symbols_tested:
        return "INCONCLUSIVE"
    # No observations at all → the curated symbols did not trigger locate behavior.
    if results.case_a_count == 0 and results.case_b_count == 0:
        return "INCONCLUSIVE"
    # Fingerprint extraction failed despite case-B observations.
    if results.case_b_count > 0 and not results.fingerprint_string:
        return "INCONCLUSIVE"
    # Explicit composite from spec: <5 symbols AND zero case-B → INCONCLUSIVE.
    if len(results.symbols_tested) < 5 and results.case_b_count == 0:
        return "INCONCLUSIVE"
    return "PROCEED"


async def main_async(args: argparse.Namespace) -> int:
    started = _now_utc_iso()
    requested_symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    log.info(
        "DEF-204 R2 Path #2 spike — port=%d clientId=%d account=%s symbols=%s trials/sym=%d",
        args.port,
        args.client_id,
        args.account or "(default)",
        ",".join(requested_symbols),
        args.trials_per_symbol,
    )

    if CANONICAL_SYMBOL not in requested_symbols:
        log.error("PCT must be in --symbols (canonical reference per spec; absence trips A2).")
        return 1
    if len(requested_symbols) < 5:
        log.warning(
            "Curated list has %d symbols (<5); soft halt C10 — proceeding with documented caveat.",
            len(requested_symbols),
        )

    if args.dry_run:
        log.info("--dry-run set; skipping IBKR connection. Emitting placeholder JSON for schema check.")
        results = SpikeResults(
            status="INCONCLUSIVE",
            symbols_tested=requested_symbols,
            trials_per_symbol=args.trials_per_symbol,
            spike_run_date=started,
        )
        _emit_json(results, args.output_json)
        return 1

    ib = IB()
    try:
        await ib.connectAsync(
            host=args.host,
            port=args.port,
            clientId=args.client_id,
            timeout=10,
            account=args.account or "",
        )
        log.info("Connected to IBKR Gateway.")
        ib.reqMarketDataType(3)  # delayed data; execution is real-time regardless
    except Exception as e:
        log.error("Failed to connect to IBKR Gateway: %s", e)
        return 2

    # Capture errorEvent payloads keyed by orderId so per-trial classification
    # can read the locate-rejection reason string off the wire.
    error_capture: dict[int, str] = {}

    def _on_error(req_id: int, code: int, msg: str, contract: Contract | None = None) -> None:
        if req_id and msg:
            error_capture[req_id] = f"[{code}] {msg}"

    ib.errorEvent += _on_error

    results = SpikeResults(
        symbols_tested=[],
        trials_per_symbol=args.trials_per_symbol,
        spike_run_date=started,
    )
    pct_reachable = True

    try:
        for symbol in requested_symbols:
            try:
                stock = Stock(symbol, "SMART", "USD")
                qualified = await ib.qualifyContractsAsync(stock)
                if not isinstance(qualified, list) or not qualified or qualified[0] is None:
                    log.error("Could not qualify contract %s — skipping symbol", symbol)
                    if symbol == CANONICAL_SYMBOL:
                        pct_reachable = False
                    continue
                contract = cast(Contract, qualified[0])
                results.symbols_tested.append(symbol)

                for i in range(1, args.trials_per_symbol + 1):
                    try:
                        trial = await _run_one_trial(
                            ib, contract, symbol, i, args.case_a_max_age_seconds, error_capture
                        )
                    except Exception as e:
                        log.exception("%s trial %d crashed: %s", symbol, i, e)
                        trial = TrialResult(symbol=symbol, trial_index=i, case="error")
                        trial.notes.append(f"crashed: {e}")
                        await _ensure_flat(ib, contract)
                    results.trials.append(trial)
                    await asyncio.sleep(1.0)  # inter-trial cooldown
            except Exception as e:
                log.exception("Symbol %s loop crashed: %s", symbol, e)
                if symbol == CANONICAL_SYMBOL:
                    pct_reachable = False

        _compute_summary(results, args.case_a_max_age_seconds)
        results.status = _determine_status(results, pct_reachable)
        results.spike_run_date = _now_utc_iso()
        _emit_json(results, args.output_json)
        _print_summary(results)
        return 0 if results.status == "PROCEED" else 1

    finally:
        ib.errorEvent -= _on_error
        try:
            ib.disconnect()
        except Exception:
            pass


def _emit_json(results: SpikeResults, path: str) -> None:
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    payload = asdict(results)
    payload.pop("trials", None)  # per-trial detail is debugging-only; keep the artifact tight
    # Round-trip the 16 required keys to surface schema drift early.
    required = {
        "status", "fingerprint_string", "fingerprint_stable",
        "case_a_observed", "case_a_count", "case_b_count",
        "case_a_max_age_seconds", "release_events_observed",
        "release_p50_seconds", "release_p95_seconds", "release_p99_seconds",
        "release_max_seconds", "recommended_locate_suppression_seconds",
        "symbols_tested", "trials_per_symbol", "spike_run_date",
    }
    missing = required - set(payload)
    if missing:
        raise RuntimeError(f"Spike JSON schema missing required keys: {missing}")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    log.info("Spike artifact written to %s", path)


def _print_summary(results: SpikeResults) -> None:
    print()
    print("=" * 72)
    print("DEF-204 ROUND 2 — PATH #2 LOCATE-REJECTION SPIKE — RESULTS")
    print("=" * 72)
    print(f"  status                                = {results.status}")
    print(f"  fingerprint_string                    = {results.fingerprint_string!r}")
    print(f"  fingerprint_stable                    = {results.fingerprint_stable}")
    print(f"  symbols_tested                        = {results.symbols_tested}")
    print(f"  case_a_count / case_b_count           = {results.case_a_count} / {results.case_b_count}")
    print(f"  release_events_observed               = {results.release_events_observed}")
    print(f"  release p50 / p95 / p99 / max         = "
          f"{results.release_p50_seconds} / {results.release_p95_seconds} / "
          f"{results.release_p99_seconds} / {results.release_max_seconds}")
    print(f"  recommended_locate_suppression_seconds= {results.recommended_locate_suppression_seconds}")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DEF-204 Round 2 — Path #2 locate-rejection spike (Sprint 31.92 S1b)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4002, help="IBKR Gateway paper port (default 4002)")
    p.add_argument("--client-id", type=int, default=2, help="IBKR clientId (default 2; clientId=1 reserved for S1a)")
    p.add_argument("--account", default="", help="IBKR account (default U24619949 expected via paper Gateway)")
    p.add_argument("--symbols", required=True,
                   help="Comma-separated operator-curated hard-to-borrow microcaps; PCT must be included.")
    p.add_argument("--trials-per-symbol", type=int, default=10)
    p.add_argument("--case-a-max-age-seconds", type=int, default=30,
                   help="Watchdog cancel threshold for held SELLs (default 30s)")
    p.add_argument("--output-json", default="scripts/spike-results/spike-def204-round2-path2-results.json")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip IBKR connection; emit placeholder JSON for schema validation only.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        log.warning("Interrupted by user — partial results may be unwritten.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
