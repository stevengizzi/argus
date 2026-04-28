"""Tests for Sprint 31.91 Session 4 / PHASE-D-OPEN-ITEMS Item 7.

Standardizes ``scripts/spike_ibkr_oca_late_add.py`` and regression
invariant 22 on the **ISO-with-dashes** filename convention
(``spike-results-YYYY-MM-DD.json``) across all three sources that
previously disagreed:

- Script default output (was Unix epoch)
- Docstring example (was ISO with dashes — already correct)
- Regression invariant 22 date parser (was compact YYYYMMDD)
"""

from __future__ import annotations

import datetime as _datetime
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "spike_ibkr_oca_late_add.py"
INVARIANT_PATH = (
    REPO_ROOT
    / "docs"
    / "sprints"
    / "sprint-31.91-reconciliation-drift"
    / "regression-checklist.md"
)


def test_spike_script_default_output_is_iso_date_in_spike_results_dir():
    """Item 7 Test 9: the script's default output path is
    ``scripts/spike-results/spike-results-YYYY-MM-DD.json``.

    Verified by reading the source and asserting the construction expression
    uses ``date.today().isoformat()`` and the directory is
    ``scripts/spike-results``. We do NOT actually run the spike script
    (that would require an IBKR Gateway connection); the compile-time
    string-construction is the load-bearing artifact.
    """

    source = SCRIPT_PATH.read_text()

    # The default-output path must reference the ISO-with-dashes form.
    # Two acceptable patterns: f-string with `_datetime.date.today().isoformat()`
    # or the explicit `datetime.date.today().isoformat()` form.
    assert (
        "date.today().isoformat()" in source
    ), (
        "Spike script default output should call `date.today().isoformat()` "
        f"(ISO-with-dashes); pattern not found in {SCRIPT_PATH}. The Item 7 "
        f"surgical fix replaces the prior `int(time.time())` Unix-epoch form."
    )

    # The default location must be scripts/spike-results/.
    assert (
        '"scripts/spike-results"' in source
        or "'scripts/spike-results'" in source
    ), (
        "Spike script default output should write into "
        "`scripts/spike-results/`; directory literal not found in source."
    )

    # The legacy Unix-epoch form must be gone.
    assert "int(time.time())" not in source, (
        "Legacy Unix-epoch default-output form `int(time.time())` is still "
        "present in the spike script; Item 7 surgical fix is incomplete."
    )


def test_invariant_22_date_parser_handles_iso_format_with_dashes():
    """Item 7 Test 10: regression invariant 22's date parser accepts the
    ISO-with-dashes filename format (e.g. ``spike-results-2026-04-25.json``)
    via ``datetime.date.fromisoformat`` directly, without the prior
    ``f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"`` reconstruction.
    """

    invariant = INVARIANT_PATH.read_text()

    # The doc must reference the ISO-with-dashes filename pattern.
    assert "spike-results-YYYY-MM-DD.json" in invariant, (
        "Regression invariant 22 should reference ISO-with-dashes "
        "`spike-results-YYYY-MM-DD.json`; pattern not found."
    )

    # The legacy compact-YYYYMMDD parser block must be gone.
    assert "date_str[:4]" not in invariant, (
        "Legacy compact-YYYYMMDD slicing `date_str[:4]` still present in "
        "invariant 22's parser block; Item 7 surgical fix is incomplete."
    )

    # The new parser pattern: `fromisoformat(date_str)` directly.
    assert "fromisoformat(date_str)" in invariant, (
        "Invariant 22 should call `datetime.date.fromisoformat(date_str)` "
        "directly on the dash-form filename; pattern not found."
    )

    # Behavioral verification: emulate the parser logic on a sample filename
    # and assert it produces the expected date.
    sample = "spike-results-2026-04-25.json"
    date_str = sample[len("spike-results-"):-len(".json")]
    parsed = _datetime.date.fromisoformat(date_str)
    assert parsed == _datetime.date(2026, 4, 25)
