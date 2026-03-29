"""Shared fixtures for AI module tests.

Ensures ANTHROPIC_API_KEY env var does not leak from .env (loaded by
argus.main at import time) into tests that assert on AIConfig defaults.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clear_anthropic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ANTHROPIC_API_KEY from env for all AI tests.

    argus.main calls load_dotenv() at module level, which can set this
    env var in xdist workers that happen to import argus.main before
    running AI tests. This fixture prevents that leakage.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
