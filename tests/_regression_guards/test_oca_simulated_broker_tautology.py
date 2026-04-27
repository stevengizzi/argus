"""Regression invariant 21 — SimulatedBroker OCA-assertion tautology guard.

Per Sprint 31.91 regression-checklist invariant 21 (third-pass MEDIUM #11):
SimulatedBroker's OCA implementation is a no-op acknowledgment of the
``ocaGroup``/``ocaType`` Order fields. Any test that asserts OCA-cancellation
*semantics* (cancellation propagation, sibling-fill blocking, late-add
rejection) against SimulatedBroker passes whether OCA is wired correctly or
not — the test becomes a tautology.

This guard scans ``tests/`` for files that import ``SimulatedBroker`` AND
reference any OCA-related identifier (``oca``, ``OCA``, ``ocaGroup``,
``ocaType``). Such files must use IBKR mocks, not SimulatedBroker, OR mark
themselves with the ``# allow-oca-sim: <reason>`` allow-list comment.

DEF-208 tracks the structural gap; ``scripts/spike_ibkr_oca_late_add.py``
is the live-IBKR regression check that mitigates the gap.
"""

from __future__ import annotations

import os
import re


def test_no_oca_assertion_uses_simulated_broker() -> None:
    """Anti-tautology guard (MEDIUM #11): tests asserting OCA behavior
    must use IBKR mocks. SimulatedBroker's OCA is a no-op
    acknowledgment, so any assertion of OCA-cancellation semantics
    against SimulatedBroker passes whether OCA is wired correctly or
    not. Future test authors who reach for SimulatedBroker because
    it's faster will produce false-passes.

    DEF-208 tracks the gap; spike script
    (scripts/spike_ibkr_oca_late_add.py) is the live-IBKR regression
    check that mitigates the gap.

    NOTE on the OCA-identifier regex (Sprint 31.91 Session 1a deviation):
    the canonical regression-checklist invariant 21 specifies
    ``r"oca|OCA|ocaGroup|ocaType"``. The bare lowercase ``oca`` alternative
    matches as a substring of common Python words like ``local``,
    ``allocation``, ``nonlocal``, ``vocabulary`` — producing dozens of
    false positives across the existing test suite (test_main.py,
    test_risk_manager.py, test_orchestrator.py, etc.). The regex below
    preserves the spec's INTENT (catch tests that reference OCA
    identifiers / OCA-grouping behavior) while eliminating the
    substring-of-unrelated-word trigger. The four matched alternatives
    cover every form of OCA reference seen in the codebase: whole-word
    ``OCA`` (uppercase acronym), the ib_async camelCase identifiers
    ``ocaGroup`` / ``ocaType``, and the ARGUS snake_case forms
    ``oca_group_id`` / ``oca_group``. Disclosed in
    ``docs/sprints/sprint-31.91-reconciliation-drift/session-1a-closeout.md``.
    """
    forbidden: list[str] = []
    for root, _, files in os.walk("tests"):
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                src = fh.read()
            uses_sim = "SimulatedBroker" in src
            asserts_oca = bool(
                re.search(
                    r"\bOCA\b|ocaGroup|ocaType|oca_group|oca_type",
                    src,
                )
            )
            if uses_sim and asserts_oca:
                # Allow-list: tests legitimately verifying SimulatedBroker
                # accepts the OCA fields without crashing (bookkeeping)
                # mark themselves with this comment.
                if "# allow-oca-sim:" in src:
                    continue
                forbidden.append(path)
    assert not forbidden, (
        f"OCA-behavior tests must use IBKR mocks, not SimulatedBroker, "
        f"to avoid no-op tautology. Found in: {forbidden}. "
        f"Mark known-safe cases with `# allow-oca-sim: <reason>` comment."
    )
