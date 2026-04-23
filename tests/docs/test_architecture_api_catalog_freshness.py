"""DEF-168 regression guard — architecture.md must list every API route.

The FastAPI app exposes its schema at `app.openapi()`. This test walks every
path in that schema and asserts the path string appears somewhere in
`docs/architecture.md`. The same check is enforced for WebSocket routes
(FastAPI does not include them in the OpenAPI schema, so we fall back to
the helper in `scripts/generate_api_catalog.py`).

When this test fails the remediation is always the same: run

    python scripts/generate_api_catalog.py --verify

for the same diagnostic, then either edit `docs/architecture.md` by hand or
use `python scripts/generate_api_catalog.py --path-prefix /api/v1/<thing>`
to regenerate the relevant section and paste.

Resolved: DEF-168 (Sprint 31.9 IMPROMPTU-08, 2026-04-23).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARCHITECTURE_MD = REPO_ROOT / "docs" / "architecture.md"

# Routes auto-mounted by FastAPI that we deliberately don't catalog.
_IGNORED_PATHS: set[str] = {
    "/openapi.json",
    "/docs",
    "/redoc",
    "/docs/oauth2-redirect",
}


def _load_generator_module():
    """Import `scripts/generate_api_catalog.py` by path.

    Avoids adding a package `__init__.py` under `scripts/` (that directory is
    a loose collection of CLI tools, not a Python package).
    """
    scripts_dir = REPO_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import generate_api_catalog  # type: ignore[import-not-found]

    return generate_api_catalog


def test_architecture_md_lists_all_rest_routes() -> None:
    """Every route in `app.openapi()` must appear in architecture.md."""
    generator = _load_generator_module()
    app = generator._build_app_for_introspection()
    schema = app.openapi()
    md_text = ARCHITECTURE_MD.read_text()

    missing: list[str] = []
    for path in schema.get("paths", {}):
        if path in _IGNORED_PATHS:
            continue
        if path not in md_text:
            missing.append(path)

    if missing:
        pytest.fail(
            f"{len(missing)} REST route(s) missing from docs/architecture.md. "
            f"Run `python scripts/generate_api_catalog.py --verify` for the same "
            f"diagnostic, then regenerate with "
            f"`python scripts/generate_api_catalog.py` and paste. Missing: {missing}"
        )


def test_architecture_md_lists_all_websocket_routes() -> None:
    """Every `@<router>.websocket(...)` path must appear in architecture.md."""
    generator = _load_generator_module()
    entries = generator.extract_websocket_endpoints()
    md_text = ARCHITECTURE_MD.read_text()

    missing = [e["path"] for e in entries if e["path"] not in md_text]
    if missing:
        pytest.fail(
            f"{len(missing)} WebSocket route(s) missing from docs/architecture.md. "
            f"Update the §4 WebSocket table. Missing: {missing}"
        )


def test_catalog_generator_is_idempotent() -> None:
    """Running the generator twice produces identical Markdown (deterministic).

    If this test fails, the script has nondeterministic ordering (dict hash
    randomization, time-dependent output, etc.) — a latent drift risk.
    """
    generator = _load_generator_module()
    app = generator._build_app_for_introspection()
    schema = app.openapi()
    endpoints_a = generator.extract_rest_endpoints(schema)
    endpoints_b = generator.extract_rest_endpoints(schema)
    assert endpoints_a == endpoints_b, "extract_rest_endpoints is not deterministic"

    markdown_a = generator.render_rest_catalog(endpoints_a, group_by="tag")
    markdown_b = generator.render_rest_catalog(endpoints_b, group_by="tag")
    assert markdown_a == markdown_b, "render_rest_catalog is not deterministic"


def test_verify_helper_detects_drift() -> None:
    """The named `verify_catalog_freshness()` helper must regress on drift.

    Proves the CI-facing `--verify` gate isn't vacuously passing. Exercises
    the actual helper the script's `--verify` mode calls (not a reimplementation).
    """
    import copy

    generator = _load_generator_module()
    app = generator._build_app_for_introspection()
    schema = app.openapi()

    # Baseline: the real schema is in sync with architecture.md.
    ok_clean, missing_clean = generator.verify_catalog_freshness(schema)
    assert ok_clean, f"Pre-check failed — clean schema reports drift: {missing_clean}"

    # Drift case: inject a synthetic route into a local schema copy and
    # run the helper against THAT (a small monkey-patch keeps the tool
    # pointed at the mutated schema without touching the real app).
    fake_schema = copy.deepcopy(schema)
    sentinel = "/api/v1/never-documented-synthetic-sentinel-def168"
    fake_schema["paths"][sentinel] = {
        "get": {"summary": "Fake", "description": "", "responses": {"200": {}}}
    }

    class _FakeApp:
        def openapi(self) -> dict:
            return fake_schema

    import unittest.mock

    with unittest.mock.patch.object(
        generator, "_build_app_for_introspection", return_value=_FakeApp()
    ):
        ok_drift, missing_drift = generator.verify_catalog_freshness(fake_schema)

    assert not ok_drift, "verify_catalog_freshness() did not detect the injected fake route"
    assert sentinel in missing_drift, f"Expected sentinel path in missing list, got {missing_drift}"
