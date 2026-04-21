"""Regression guard for FIX-01 audit 2026-04-21 / DEF-082 / P1-D1 C1.

The quality pipeline's CatalystStorage must connect to ``catalyst.db`` (where
the intelligence pipeline writes classified catalysts), not ``argus.db``
(which is the trades / system DB and has no catalyst rows). Pointing at
the wrong DB silently made ``catalyst_quality`` a constant neutral 50.0
for every signal. This test grep-guards Phase 10.25 against regressing.
"""

from __future__ import annotations

from pathlib import Path


def test_phase_10_25_catalyst_storage_uses_catalyst_db() -> None:
    """``argus/main.py`` Phase 10.25 points CatalystStorage at catalyst.db."""
    main_py = Path(__file__).parent.parent / "argus" / "main.py"
    source = main_py.read_text()

    # The quality pipeline block must reference catalyst.db.
    assert 'Path(config.system.data_dir) / "catalyst.db"' in source, (
        "Phase 10.25 CatalystStorage construction must point at catalyst.db "
        "(not argus.db) — see FIX-01 / DEF-082. The intelligence pipeline "
        "writes classified catalysts into catalyst.db; argus.db has 0 rows."
    )

    # Explicit guard against the previous buggy path.
    buggy = (
        'if self._catalyst_storage is None:\n'
        '                try:\n'
        '                    from argus.intelligence.storage import '
        'CatalystStorage\n'
        '\n'
        '                    db_path = Path(config.system.data_dir) / '
        '"argus.db"\n'
    )
    assert buggy not in source, (
        "Phase 10.25 must not reintroduce the argus.db path for "
        "CatalystStorage — see FIX-01 / DEF-082."
    )
