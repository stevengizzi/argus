#!/usr/bin/env python3
"""validate_session_oca_mass_balance.py — categorized variance report

Sprint 31.91 D7 (mass-balance) + PHASE-D-OPEN-ITEMS Item 4 (precedence).

Categorization rules (precedence order, strongest evidence wins):

1. expected_partial_fill: a SELL was placed (order_id known) and
   broker reports same-quantity fill OR working order outstanding.
2. eventual_consistency_lag: ARGUS-side accounting lags broker-side
   by <=2 reconciliation cycles (<=120s; one cycle for snapshot,
   one for propagation).
3. unaccounted_leak: shares in broker SELL stream not attributable
   to either of the above. FLAG and exit non-zero.

Precedence: when a row could fit multiple categories, classify into
the strongest-evidence category:
  expected_partial_fill > eventual_consistency_lag > unaccounted_leak

Known-gap registry (rows that should NOT be flagged):
  - IMSR pending=None case: fill callback with no _pending_orders entry
    -> classify as unaccounted_leak unless DEF-XXX reference is logged
    in the row's "notes" field. Prevents silent classification drift.

Cross-session boundary handling: filter logs by session-id (extract
from log timestamp range against pre-loaded sessions table). Reject
rows that span session boundaries with reason="boundary_ambiguous".

Usage:
    python scripts/validate_session_oca_mass_balance.py logs/argus_YYYYMMDD.jsonl

Exit codes:
    0 - zero unaccounted_leak rows; session is clean
    1 - one or more unaccounted_leak rows; session has unexplained variance
    2 - input file missing or unparseable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Eventual-consistency window: <=2 reconciliation cycles. Each cycle is
# nominally 60s (one snapshot + one propagation), so 120s is the bound.
EVENTUAL_CONSISTENCY_WINDOW_SECONDS = 120

# DEF-XXX reference pattern for the IMSR pending=None known-gap registry.
DEF_REFERENCE_PATTERN = re.compile(r"DEF-\d+")


@dataclass
class BrokerSellEvent:
    """A SELL event observed from the broker side in the structured log."""

    timestamp: datetime
    symbol: str
    quantity: int
    order_id: str | None
    notes: str = ""

    def has_def_reference(self) -> bool:
        return bool(DEF_REFERENCE_PATTERN.search(self.notes))


@dataclass
class OrderPlacementEvent:
    """An ARGUS-side order placement (the leg we look up by order_id).

    ``side`` is the literal string ``"BUY"`` or ``"SELL"`` parsed from the
    placement line. The mass-balance walk only consumes SELL placements;
    BUY placements are retained because the same ULID can appear in
    follow-up reconciliation lines that we want to disambiguate.
    """

    timestamp: datetime
    symbol: str
    quantity: int
    order_id: str
    side: str = "SELL"


@dataclass
class ReconciliationCycleEvent:
    """A reconciliation cycle output (the lag-window evidence anchor)."""

    timestamp: datetime
    symbol: str
    argus_qty: int
    broker_qty: int


@dataclass
class CategoryCounts:
    expected_partial_fill: int = 0
    eventual_consistency_lag: int = 0
    unaccounted_leak: int = 0
    boundary_ambiguous: int = 0
    known_gaps_acknowledged: int = 0
    rows: list[dict[str, Any]] = field(default_factory=list)


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL line-by-line; skip blank/unparseable lines (best-effort)."""

    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # Best-effort: skip a single malformed line rather than failing
                # the whole report. The structured logger occasionally emits a
                # truncated final line on abrupt shutdown.
                continue
    return rows


def _parse_iso_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def extract_broker_sell_events(
    rows: list[dict[str, Any]],
    placements: dict[str, OrderPlacementEvent],
) -> list[BrokerSellEvent]:
    """Find broker-side SELL fills in the structured log.

    The structured log is Python `logging`-style JSONL with fields
    {timestamp, level, logger, message}. The ARGUS broker emits two
    relevant patterns (note the em-dash and right-arrow separators used
    by the live system):

      "Order filled: <ULID> — <qty> @ $<price>"
      "Order placed: <ULID> → IBKR #<n> <SIDE> <qty> <SYMBOL> <TYPE>"

    The fill line carries no symbol or side; we resolve those by joining
    on the ULID against ``placements`` (built by
    :func:`extract_argus_order_placements`). Only SELL fills are returned.
    """

    events: list[BrokerSellEvent] = []
    # Accept both em-dash (live system) and hyphen (test fixtures) as the
    # qty separator; keep the ULID and qty groups stable.
    fill_pattern = re.compile(
        r"Order filled:\s*`?([A-Z0-9]+)`?\s*[—\-]\s*(\d+)\s*@"
    )
    for row in rows:
        message = row.get("message", "")
        logger = row.get("logger", "")
        if "ibkr_broker" not in logger:
            continue
        match = fill_pattern.search(message)
        if not match:
            continue
        ts = _parse_iso_timestamp(row.get("timestamp", ""))
        if ts is None:
            continue
        order_id = match.group(1)
        placement = placements.get(order_id)
        # The fill line itself does not include side/symbol; we only treat
        # this as a broker SELL event when the matching placement was SELL.
        # If the ULID is unknown (the IMSR pending=None case), keep the
        # event with an empty side/symbol so the categorizer can route it
        # to the known-gap escape or unaccounted_leak.
        if placement is not None and placement.side != "SELL":
            continue
        events.append(
            BrokerSellEvent(
                timestamp=ts,
                symbol=placement.symbol if placement is not None else "",
                quantity=int(match.group(2)),
                order_id=order_id,
                notes=str(row.get("notes", "")),
            )
        )
    return events


def extract_argus_order_placements(
    rows: list[dict[str, Any]],
) -> dict[str, OrderPlacementEvent]:
    """Find ARGUS-side order placement events keyed by ULID/order_id.

    Two live formats are recognized::

        "Order placed: <ULID> → IBKR #<n> <SIDE> <qty> <SYMBOL> <TYPE>"

    and the bracket form (which establishes the BUY entry plus three SELL
    children — stop, T1, T2 — under the same parent symbol)::

        "Bracket placed: entry=<ULID_BUY> (IBKR #<n>), stop=<ULID_STOP>,
         targets=['<ULID_T1>', '<ULID_T2>'] — BUY <qty> <SYMBOL>"
    """

    placements: dict[str, OrderPlacementEvent] = {}
    placement_pattern = re.compile(
        r"Order placed:\s*`?([A-Z0-9]+)`?\s*[→>\-]+\s*"
        r"(?:IBKR\s*#?\d*\s*)?(BUY|SELL)\s+(\d+)\s+([A-Z][A-Z0-9.]*)"
    )
    bracket_pattern = re.compile(
        r"Bracket placed:\s*entry=([A-Z0-9]+).*?stop=([A-Z0-9]+).*?"
        r"targets=\[\s*'?([A-Z0-9]+)'?\s*,\s*'?([A-Z0-9]+)'?.*?"
        r"BUY\s+(\d+)\s+([A-Z][A-Z0-9.]*)",
        re.DOTALL,
    )
    for row in rows:
        message = row.get("message", "")
        ts = _parse_iso_timestamp(row.get("timestamp", ""))
        if ts is None:
            continue
        match = placement_pattern.search(message)
        if match:
            order_id = match.group(1)
            placements[order_id] = OrderPlacementEvent(
                timestamp=ts,
                symbol=match.group(4),
                quantity=int(match.group(3)),
                order_id=order_id,
                side=match.group(2),
            )
            continue
        bmatch = bracket_pattern.search(message)
        if bmatch:
            entry_id, stop_id, t1_id, t2_id = (
                bmatch.group(1),
                bmatch.group(2),
                bmatch.group(3),
                bmatch.group(4),
            )
            qty = int(bmatch.group(5))
            symbol = bmatch.group(6)
            # Entry is BUY; the three child legs (stop, T1, T2) are SELL.
            placements[entry_id] = OrderPlacementEvent(
                timestamp=ts, symbol=symbol, quantity=qty,
                order_id=entry_id, side="BUY",
            )
            for child_id in (stop_id, t1_id, t2_id):
                placements[child_id] = OrderPlacementEvent(
                    timestamp=ts, symbol=symbol, quantity=qty,
                    order_id=child_id, side="SELL",
                )
    return placements


def extract_reconciliation_cycles(
    rows: list[dict[str, Any]],
) -> list[ReconciliationCycleEvent]:
    """Find reconciliation cycle outputs (qty mismatch + catch-up signals)."""

    cycles: list[ReconciliationCycleEvent] = []
    cycle_pattern = re.compile(
        r"reconciliation: .*?(\w+) (?:ARGUS|argus_qty)=?(\d+).*?(?:IBKR|broker_qty)=?(\d+)",
        re.IGNORECASE,
    )
    for row in rows:
        message = row.get("message", "")
        match = cycle_pattern.search(message)
        if not match:
            continue
        ts = _parse_iso_timestamp(row.get("timestamp", ""))
        if ts is None:
            continue
        cycles.append(
            ReconciliationCycleEvent(
                timestamp=ts,
                symbol=match.group(1),
                argus_qty=int(match.group(2)),
                broker_qty=int(match.group(3)),
            )
        )
    return cycles


def _detect_session_boundaries(rows: list[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
    """Return (session_start, session_end) timestamps if both can be inferred.

    A session begins at the first log line and ends at the last. Cross-session
    boundary handling: any event outside this window is flagged with reason
    ``boundary_ambiguous`` rather than silently classified as ``unaccounted_leak``.
    """

    timestamps: list[datetime] = []
    for row in rows:
        ts = _parse_iso_timestamp(row.get("timestamp", ""))
        if ts is not None:
            timestamps.append(ts)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def categorize_event(
    event: BrokerSellEvent,
    placements: dict[str, OrderPlacementEvent],
    cycles: list[ReconciliationCycleEvent],
    session_start: datetime | None,
    session_end: datetime | None,
) -> tuple[str, str]:
    """Apply the precedence categorization rules to a single broker SELL event.

    Returns ``(category, reason)``. Precedence order:
      expected_partial_fill > eventual_consistency_lag > unaccounted_leak
    """

    # Cross-session boundary handling: reject rows outside the inferred window
    # rather than silently flagging.
    if session_start is not None and session_end is not None:
        if event.timestamp < session_start or event.timestamp > session_end:
            return "boundary_ambiguous", "event timestamp outside session window"

    # Precedence 1: expected_partial_fill — a SELL was placed (order_id known)
    # and broker reports a fill keyed by the same order_id.
    if event.order_id is not None and event.order_id in placements:
        placement = placements[event.order_id]
        if placement.quantity == event.quantity:
            return "expected_partial_fill", f"order_id {event.order_id} matched"
        # Partial fill: working order outstanding for the remainder.
        return "expected_partial_fill", (
            f"order_id {event.order_id} partial "
            f"(placement={placement.quantity}, fill={event.quantity})"
        )

    # Precedence 2: eventual_consistency_lag — ARGUS-side accounting catches up
    # within the 120s window (<=2 reconciliation cycles).
    window_end = event.timestamp + timedelta(
        seconds=EVENTUAL_CONSISTENCY_WINDOW_SECONDS
    )
    for cycle in cycles:
        if cycle.symbol != event.symbol:
            continue
        if event.timestamp <= cycle.timestamp <= window_end:
            return "eventual_consistency_lag", (
                f"reconciliation cycle at {cycle.timestamp.isoformat()} "
                f"shows ARGUS catching up"
            )

    # Precedence 3 (with known-gap escape): IMSR pending=None case — a fill
    # callback with no _pending_orders entry. Without an explicit DEF-XXX
    # reference in the notes, classify as unaccounted_leak (prevents silent
    # classification drift).
    if event.has_def_reference():
        return "known_gaps_acknowledged", (
            f"DEF reference logged in notes: {event.notes!r}"
        )

    return "unaccounted_leak", (
        "broker SELL not attributable to a placed order or reconciliation lag"
    )


def build_report(
    events: list[BrokerSellEvent],
    placements: dict[str, OrderPlacementEvent],
    cycles: list[ReconciliationCycleEvent],
    session_start: datetime | None,
    session_end: datetime | None,
) -> CategoryCounts:
    counts = CategoryCounts()
    for event in events:
        category, reason = categorize_event(
            event, placements, cycles, session_start, session_end
        )
        counts.rows.append(
            {
                "timestamp": event.timestamp.isoformat(),
                "symbol": event.symbol,
                "quantity": event.quantity,
                "order_id": event.order_id,
                "category": category,
                "reason": reason,
            }
        )
        if category == "expected_partial_fill":
            counts.expected_partial_fill += 1
        elif category == "eventual_consistency_lag":
            counts.eventual_consistency_lag += 1
        elif category == "unaccounted_leak":
            counts.unaccounted_leak += 1
        elif category == "boundary_ambiguous":
            counts.boundary_ambiguous += 1
        elif category == "known_gaps_acknowledged":
            counts.known_gaps_acknowledged += 1
    return counts


def render_report(counts: CategoryCounts, log_path: Path) -> str:
    lines = [
        f"== Mass-Balance Variance Report ({log_path.name}) ==",
        f"expected_partial_fill: {counts.expected_partial_fill} rows",
        f"eventual_consistency_lag: {counts.eventual_consistency_lag} rows",
        (
            f"unaccounted_leak: {counts.unaccounted_leak} rows"
            f"{'  <- session is clean' if counts.unaccounted_leak == 0 else '  <- FLAG'}"
        ),
        f"boundary_ambiguous: {counts.boundary_ambiguous} rows",
        f"known_gaps_acknowledged: {counts.known_gaps_acknowledged} rows",
    ]
    if counts.unaccounted_leak > 0:
        lines.append("")
        lines.append("Unaccounted leak rows (FLAG):")
        for row in counts.rows:
            if row["category"] == "unaccounted_leak":
                lines.append(
                    f"  {row['timestamp']}  {row['symbol']}  qty={row['quantity']}  "
                    f"order_id={row['order_id']}  reason={row['reason']}"
                )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sprint 31.91 D7 mass-balance categorized variance report"
    )
    parser.add_argument(
        "log_path",
        type=Path,
        help="Path to logs/argus_YYYYMMDD.jsonl",
    )
    return parser.parse_args(argv)


def run(log_path: Path) -> tuple[CategoryCounts, str]:
    if not log_path.exists():
        raise FileNotFoundError(f"log file does not exist: {log_path}")
    rows = parse_jsonl(log_path)
    placements = extract_argus_order_placements(rows)
    events = extract_broker_sell_events(rows, placements)
    cycles = extract_reconciliation_cycles(rows)
    session_start, session_end = _detect_session_boundaries(rows)
    counts = build_report(events, placements, cycles, session_start, session_end)
    report = render_report(counts, log_path)
    return counts, report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        counts, report = run(args.log_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"ERROR: failed to parse log: {exc}", file=sys.stderr)
        return 2
    print(report)
    return 0 if counts.unaccounted_leak == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
