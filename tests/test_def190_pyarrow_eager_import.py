"""Regression test for DEF-190 (pyarrow xdist race).

Assert that ``tests/conftest.py`` imports ``pyarrow`` and
``pyarrow.pandas_compat`` eagerly. If either import is removed, the xdist
race on ``register_extension_type('pandas.period')`` can return.
"""

from __future__ import annotations

from pathlib import Path


def test_conftest_prewarms_pyarrow_extensions() -> None:
    conftest = (Path(__file__).parent / "conftest.py").read_text()
    assert "_prewarm_pyarrow_pandas_extensions" in conftest, (
        "tests/conftest.py must prewarm pyarrow pandas-extension types (DEF-190). "
        "Without this, two xdist workers can race on register_extension_type "
        "during first DataFrame→Arrow conversion and raise ArrowKeyError."
    )
    assert "Period(" in conftest, (
        "Prewarm must actually trigger pandas.period extension registration "
        "via a Period-dtype DataFrame conversion (DEF-190)."
    )
