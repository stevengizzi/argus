"""Sprint 31.91 Impromptu A — DEF-219 policy-table exhaustiveness regression guard.

Scans production code (``argus/``) for ``SystemAlertEvent(alert_type=<literal>)``
constructions, extracts the literal alert_type strings, and asserts each is
a key in ``build_policy_table(...)``. Catches the producer/consumer drift
that DEF-217 was (a producer emitting an alert_type missing from the policy
table) and the consumer/producer drift that DEF-218 was (the policy table
missing a key for an active emitter).

Three test cases:
1. ``test_all_emitted_alert_types_have_policy_entries`` — every emitted
   alert_type is a policy-table key.
2. ``test_no_computed_alert_type_in_production`` — every
   ``SystemAlertEvent(alert_type=...)`` construction uses a string literal.
   Non-literal values defeat the static-analysis regression guard.
3. ``test_policy_table_has_no_orphan_entries`` — every policy-table key has
   at least one production emitter (catches dead-code policy entries).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from argus.core.alert_auto_resolution import build_policy_table

ARGUS_ROOT = Path(__file__).resolve().parents[2] / "argus"

# Files excluded from the production scan:
# - alert_auto_resolution.py: the policy table itself, not a producer.
# - tests/ subdirectories: not production code.
_EXCLUDED_FILES = {
    ARGUS_ROOT / "core" / "alert_auto_resolution.py",
}


def _is_systemalertevent_call(node: ast.AST) -> bool:
    """True iff ``node`` is a ``SystemAlertEvent(...)`` Call node.

    Matches both bare ``SystemAlertEvent(...)`` and attribute-style
    ``module.SystemAlertEvent(...)`` invocations, since import style varies
    across the codebase.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "SystemAlertEvent":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "SystemAlertEvent":
        return True
    return False


def _extract_alert_type_kwarg(call: ast.Call) -> ast.expr | None:
    """Return the ``alert_type=...`` keyword's value node, or None."""
    for kw in call.keywords:
        if kw.arg == "alert_type":
            return kw.value
    return None


def _iter_production_systemalertevent_calls() -> (
    list[tuple[Path, ast.Call, ast.expr | None]]
):
    """Walk argus/ and yield (path, Call node, alert_type value) triples.

    The third element is the AST node bound to ``alert_type=`` (or None if
    the kwarg is absent — a malformed but legal Python construction).
    """
    results: list[tuple[Path, ast.Call, ast.expr | None]] = []
    for py_path in ARGUS_ROOT.rglob("*.py"):
        if py_path in _EXCLUDED_FILES:
            continue
        # Skip __pycache__ defensively.
        if "__pycache__" in py_path.parts:
            continue
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        for node in ast.walk(tree):
            if not _is_systemalertevent_call(node):
                continue
            results.append(
                (py_path, node, _extract_alert_type_kwarg(node))
            )
    return results


def test_no_computed_alert_type_in_production() -> None:
    """Every ``SystemAlertEvent(alert_type=...)`` uses a string literal.

    A computed (variable / function call / formatted-string) alert_type
    silently defeats this static-analysis regression guard. If the type
    system requires a computed value at some emitter site, this test must
    be updated to whitelist that site explicitly — otherwise the guard
    becomes a false-confidence shim.

    See ``templates/implementation-prompt.md`` v1.5.0's structural-anchor
    amendment for the rationale: alert_types must be statically resolvable
    to keep the policy-table contract enforceable.
    """
    offenders: list[str] = []
    for path, _call, value in _iter_production_systemalertevent_calls():
        if value is None:
            offenders.append(
                f"{path.relative_to(ARGUS_ROOT.parent)}: "
                "SystemAlertEvent(...) missing alert_type kwarg"
            )
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            continue
        offenders.append(
            f"{path.relative_to(ARGUS_ROOT.parent)}:"
            f"{value.lineno}: alert_type is not a string literal "
            f"(node type: {type(value).__name__})"
        )
    assert not offenders, (
        "All SystemAlertEvent(alert_type=...) constructions must use a "
        "string literal so the policy-table regression guard can verify "
        "exhaustiveness statically. Offenders:\n  - "
        + "\n  - ".join(offenders)
    )


def _emitted_alert_types() -> set[str]:
    """Set of literal alert_type strings emitted by production code."""
    emitted: set[str] = set()
    for _path, _call, value in _iter_production_systemalertevent_calls():
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            emitted.add(value.value)
    return emitted


def test_all_emitted_alert_types_have_policy_entries() -> None:
    """Every alert_type emitted in argus/ is a policy-table key.

    Catches the DEF-217 failure mode: an emitter publishes an alert_type
    that the consumer's policy table does not key on. Effect of the
    original DEF-217 was that the Databento dead-feed alert persisted as
    ACTIVE forever instead of auto-resolving on heartbeat resumption,
    because the consumer's policy entry was dead code.
    """
    emitted = _emitted_alert_types()
    table = build_policy_table(phantom_short_threshold_provider=lambda: 5)
    policy_keys = set(table.keys())
    missing = emitted - policy_keys
    assert not missing, (
        "The following alert_types are emitted by production code but "
        "have no PolicyEntry in build_policy_table(). Add a PolicyEntry "
        "for each (NEVER_AUTO_RESOLVE if no automatic clearing rule "
        "applies). Missing types: " + ", ".join(sorted(missing))
    )


def test_policy_table_has_no_orphan_entries() -> None:
    """Every policy-table key has at least one production emitter.

    Inverse-direction guard. DEF-217 was, in effect, a dead-code policy
    entry — the policy table keyed on ``databento_dead_feed`` but no
    production emitter used that string (the producer used
    ``max_retries_exceeded`` instead). Catching orphan entries forces the
    policy table to track real emitters, not aspirational ones.
    """
    emitted = _emitted_alert_types()
    table = build_policy_table(phantom_short_threshold_provider=lambda: 5)
    policy_keys = set(table.keys())
    orphans = policy_keys - emitted
    assert not orphans, (
        "The following PolicyEntry keys have no production emitter. "
        "Either remove the entry or add the missing emitter site. "
        "Orphans: " + ", ".join(sorted(orphans))
    )


# Sanity assertion — run-once side effect that fails fast if argus/ is
# unreadable from the test path. Gives a clear early signal if the
# directory layout drifts.
def test_argus_root_resolves() -> None:
    assert ARGUS_ROOT.is_dir(), f"argus/ not found at {ARGUS_ROOT}"
    assert (ARGUS_ROOT / "core" / "alert_auto_resolution.py").is_file()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
