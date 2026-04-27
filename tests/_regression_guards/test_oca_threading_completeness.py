"""Sprint 31.91 Session 1b — OCA threading completeness regression guard.

Asserts that every ``_broker.place_order(...)`` call inside
``argus/execution/order_manager.py`` either:

(a) threads ``ManagedPosition.oca_group_id`` onto the placed Order
    (evidence: an ``ocaGroup`` / ``oca_group_id`` reference appears in
    the surrounding window of the same function), OR
(b) is annotated with an ``# OCA-EXEMPT: <reason>`` comment within the
    same window (broker-only paths handled by Session 1c, T1/T2 limit
    replacements covered by bracket OCA in Session 1a, and the
    ``_check_flatten_pending_timeouts`` retry path that Session 3 will
    re-touch).

This guard catches future SELL placement paths added without OCA
threading. The spec's literal regex
(``r"_broker\\.place_order\\([^)]*side\\s*=\\s*[^,)]*SELL[^)]*\\)"``)
does not match ARGUS's existing pattern of constructing the ``Order``
separately from the ``place_order`` call; this implementation preserves
the spec's intent — every SELL placement either threads OCA or is
explicitly exempt — while operating against the actual code shape. The
deviation is documented in
``docs/sprints/sprint-31.91-reconciliation-drift/session-1b-staged-flow-report.md``.

The test deliberately fails LOUDLY (with the offending site's surrounding
text in the assertion message) so a future contributor can resolve it by
either adding OCA threading or marking the site exempt with the
canonical comment shape ``# OCA-EXEMPT: <reason>``.
"""

from __future__ import annotations

import re
from pathlib import Path

ORDER_MANAGER_PATH = Path("argus/execution/order_manager.py")

# Number of lines to scan above each ``_broker.place_order`` call when
# looking for the threading evidence or the exemption comment. 30 lines
# comfortably covers the largest existing site (the
# ``_check_flatten_pending_timeouts`` block where the ``Order(...)``
# construction sits ~10 lines above the placement and the OCA-EXEMPT
# comment sits between them).
_WINDOW_LINES = 30

# Markers that count as "OCA threading is present in this window."
_OCA_THREADING_MARKERS: tuple[str, ...] = (
    "ocaGroup",
    "oca_group_id",
)

# Exemption comment shape. Must be the canonical form so reviewers can
# grep for "OCA-EXEMPT" across the codebase to enumerate exempt sites.
_OCA_EXEMPT_MARKER = "# OCA-EXEMPT:"


def test_no_sell_without_oca_when_managed_position_has_oca() -> None:
    """Every ``_broker.place_order(...)`` site in ``order_manager.py``
    threads OCA OR is marked ``# OCA-EXEMPT: <reason>``.

    Spec: Sprint 31.91 Session 1b prompt §6 (regression guard). Implements
    the spec's intent against ARGUS's actual code shape (Order
    constructed separately from the place_order call). See the test
    docstring for the rationale on the regex deviation.
    """
    src = ORDER_MANAGER_PATH.read_text()
    lines = src.splitlines()

    placement_re = re.compile(r"_broker\.place_order\(")
    placement_line_indices = [
        i for i, line in enumerate(lines) if placement_re.search(line)
    ]
    assert placement_line_indices, (
        f"Expected at least one ``_broker.place_order`` call in "
        f"{ORDER_MANAGER_PATH}; found none — has the file moved?"
    )

    failures: list[str] = []
    for idx in placement_line_indices:
        start = max(0, idx - _WINDOW_LINES)
        window = "\n".join(lines[start:idx + 1])

        has_threading = any(m in window for m in _OCA_THREADING_MARKERS)
        has_exemption = _OCA_EXEMPT_MARKER in window
        if has_threading or has_exemption:
            continue

        # Render the offending site for the failure message.
        failures.append(
            f"  Line {idx + 1}: {lines[idx].strip()}\n"
            f"  (window: lines {start + 1}-{idx + 1})"
        )

    assert not failures, (
        "Found ``_broker.place_order(...)`` site(s) without OCA "
        "threading and without an `# OCA-EXEMPT: <reason>` comment.\n"
        "Either thread ``ManagedPosition.oca_group_id`` onto the placed "
        "Order (Sprint 31.91 Session 1b pattern) OR mark the site with "
        "`# OCA-EXEMPT: <reason>` if it is intentionally exempt.\n\n"
        + "\n".join(failures)
    )


def test_oca_exempt_marker_recognized() -> None:
    """Negative-case verification: a synthetic SELL placement WITHOUT
    OCA / WITHOUT exemption is detected as a failure by the guard logic.

    Mirrors the production guard's window-scanning logic against an
    in-memory snippet so we can prove the guard fires when expected.
    """
    snippet = "\n".join(
        [
            "    order = Order(",
            "        symbol='X',",
            "        side=OrderSide.SELL,",
            "        order_type=TradingOrderType.MARKET,",
            "        quantity=1,",
            "    )",
            "    result = await self._broker.place_order(order)",
        ]
    )
    snippet_lines = snippet.splitlines()
    placement_idx = next(
        i for i, line in enumerate(snippet_lines)
        if "_broker.place_order(" in line
    )
    start = max(0, placement_idx - _WINDOW_LINES)
    window = "\n".join(snippet_lines[start:placement_idx + 1])

    has_threading = any(m in window for m in _OCA_THREADING_MARKERS)
    has_exemption = _OCA_EXEMPT_MARKER in window
    assert not (has_threading or has_exemption), (
        "Negative-case snippet should be flagged: has neither OCA "
        "threading nor `# OCA-EXEMPT:` marker."
    )


def test_oca_threading_marker_recognized() -> None:
    """Positive-case verification: a snippet WITH OCA threading passes."""
    snippet = "\n".join(
        [
            "    order = Order(",
            "        symbol='X', side=OrderSide.SELL,",
            "        order_type=TradingOrderType.MARKET, quantity=1,",
            "    )",
            "    if position.oca_group_id is not None:",
            "        order.ocaGroup = position.oca_group_id",
            "        order.ocaType = _OCA_TYPE_BRACKET",
            "    result = await self._broker.place_order(order)",
        ]
    )
    snippet_lines = snippet.splitlines()
    placement_idx = next(
        i for i, line in enumerate(snippet_lines)
        if "_broker.place_order(" in line
    )
    start = max(0, placement_idx - _WINDOW_LINES)
    window = "\n".join(snippet_lines[start:placement_idx + 1])

    has_threading = any(m in window for m in _OCA_THREADING_MARKERS)
    assert has_threading, (
        "Positive-case snippet should be recognized as threaded; the "
        "guard logic missed an ``ocaGroup`` / ``oca_group_id`` reference."
    )


def test_oca_exempt_comment_recognized() -> None:
    """Positive-case verification: a snippet with the exempt comment passes."""
    snippet = "\n".join(
        [
            "    order = Order(",
            "        symbol='X', side=OrderSide.SELL,",
            "        order_type=TradingOrderType.MARKET, quantity=1,",
            "    )",
            "    # OCA-EXEMPT: broker-only path; no ManagedPosition.",
            "    await self._broker.place_order(order)",
        ]
    )
    snippet_lines = snippet.splitlines()
    placement_idx = next(
        i for i, line in enumerate(snippet_lines)
        if "_broker.place_order(" in line
    )
    start = max(0, placement_idx - _WINDOW_LINES)
    window = "\n".join(snippet_lines[start:placement_idx + 1])

    has_exemption = _OCA_EXEMPT_MARKER in window
    assert has_exemption, (
        "Positive-case snippet should be recognized as exempt; the "
        "guard logic missed the `# OCA-EXEMPT:` marker."
    )
