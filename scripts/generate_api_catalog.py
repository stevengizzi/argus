#!/usr/bin/env python3
"""Generate a Markdown catalog of Command Center API endpoints.

The Argus FastAPI app (`argus.api.server.create_app`) is the authoritative
source for REST endpoints: every route mounted on the app appears in
`app.openapi()["paths"]`. This script introspects that schema and emits a
Markdown catalog that can be pasted into `docs/architecture.md`.

WebSocket endpoints are NOT included in `app.openapi()` (FastAPI omits them).
A fallback parser scans `argus/api/websocket/*.py` for
`@<name>router.websocket("/ws/...")` decorators and uses the containing
module's docstring first line as the summary.

Typical invocations (from repo root):

    # All REST endpoints, grouped by tag (default):
    python scripts/generate_api_catalog.py

    # Filter to a prefix (arena/experiments/etc.):
    python scripts/generate_api_catalog.py --path-prefix /api/v1/arena

    # WebSocket catalog only (§7.8 AI / general /ws/v1/* fallback):
    python scripts/generate_api_catalog.py --websocket

    # Freshness gate for CI: exits non-zero if any route in app.openapi()
    # is missing from docs/architecture.md:
    python scripts/generate_api_catalog.py --verify

DEF-168 — IMPROMPTU-08 (Sprint 31.9 campaign close).
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WS_SOURCE_DIR = REPO_ROOT / "argus" / "api" / "websocket"
ARCHITECTURE_MD = REPO_ROOT / "docs" / "architecture.md"

# Paths auto-exposed by FastAPI that we never want in the catalog.
_EXCLUDED_PATHS: tuple[str, ...] = ("/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect")


# ---------------------------------------------------------------------------
# FastAPI app construction (minimal — no live broker, no DB connections)
# ---------------------------------------------------------------------------


def _build_app_for_introspection() -> Any:
    """Construct a FastAPI app with every router mounted, for schema reads.

    The observatory router is config-gated in `create_app`, so we build an
    `ObservatoryConfig(enabled=True)` on the `SystemConfig` we pass in. No
    broker connects, no DB opens — we never trigger the lifespan.
    """
    import time as _time

    from argus.analytics.config import ObservatoryConfig
    from argus.analytics.trade_logger import TradeLogger
    from argus.api.dependencies import AppState
    from argus.api.server import create_app
    from argus.core.clock import SystemClock
    from argus.core.config import HealthConfig, OrderManagerConfig, RiskConfig, SystemConfig
    from argus.core.event_bus import EventBus
    from argus.core.health import HealthMonitor
    from argus.core.risk_manager import RiskManager
    from argus.db.manager import DatabaseManager
    from argus.execution.order_manager import OrderManager
    from argus.execution.simulated_broker import SimulatedBroker

    event_bus = EventBus()
    clock = SystemClock()
    broker = SimulatedBroker(initial_cash=100_000.0)
    db = DatabaseManager(Path(":memory:"))
    trade_logger = TradeLogger(db)
    risk_manager = RiskManager(
        config=RiskConfig(),
        broker=broker,
        event_bus=event_bus,
        clock=clock,
    )
    order_manager = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )
    health_monitor = HealthMonitor(
        event_bus=event_bus,
        clock=clock,
        config=HealthConfig(),
        broker=broker,
        trade_logger=trade_logger,
    )
    config = SystemConfig(observatory=ObservatoryConfig(enabled=True))

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        clock=clock,
        config=config,
        start_time=_time.time(),
    )
    return create_app(app_state)


# ---------------------------------------------------------------------------
# REST catalog extraction
# ---------------------------------------------------------------------------


def _first_line(text: str | None) -> str:
    """Return the first non-empty line of a multi-line string."""
    if not text:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _extract_response_model(operation: dict[str, Any]) -> str:
    """Pull the response schema name out of an operation object."""
    responses = operation.get("responses", {})
    # Prefer 200; fall back to the first 2xx.
    candidate = responses.get("200")
    if candidate is None:
        for code, resp in responses.items():
            if code.startswith("2"):
                candidate = resp
                break
    if not candidate:
        return ""
    content = candidate.get("content", {})
    schema = content.get("application/json", {}).get("schema", {})
    ref = schema.get("$ref")
    if ref:
        return ref.split("/")[-1]
    # Arrays of refs
    items = schema.get("items", {})
    ref = items.get("$ref") if isinstance(items, dict) else None
    if ref:
        return f"list[{ref.split('/')[-1]}]"
    schema_type = schema.get("type")
    return str(schema_type) if schema_type else ""


def extract_rest_endpoints(
    schema: dict[str, Any],
    path_prefix: str | None = None,
    exclude_prefix: str | None = None,
) -> list[dict[str, Any]]:
    """Flatten `app.openapi()` into a list of endpoint dicts.

    Each entry has: method, path, summary, description, tags (list), response_model.
    """
    endpoints: list[dict[str, Any]] = []
    for path, methods in schema.get("paths", {}).items():
        if path in _EXCLUDED_PATHS:
            continue
        if path_prefix and not path.startswith(path_prefix):
            continue
        if exclude_prefix and path.startswith(exclude_prefix):
            continue
        for method, operation in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            # Prefer docstring first line (more informative than FastAPI's
            # auto-generated "Get Positions" summary from the operationId).
            summary = _first_line(operation.get("description")) or operation.get("summary", "")
            # Dedupe tags while preserving order (multi-include-router mounts
            # can stack the same tag twice: router tag + include_router tag).
            seen: set[str] = set()
            tags: list[str] = []
            for tag in operation.get("tags", []):
                if tag not in seen:
                    seen.add(tag)
                    tags.append(tag)
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": operation.get("description", ""),
                    "tags": tags,
                    "response_model": _extract_response_model(operation),
                }
            )
    # Stable ordering: path alphabetical, then method.
    endpoints.sort(key=lambda e: (e["path"], e["method"]))
    return endpoints


# ---------------------------------------------------------------------------
# WebSocket fallback parser
# ---------------------------------------------------------------------------


_WS_DECORATOR_RE = re.compile(
    r"@\w+\.websocket\s*\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)


def extract_websocket_endpoints(source_dir: Path = WS_SOURCE_DIR) -> list[dict[str, str]]:
    """Scan websocket modules for `@<router>.websocket("...")` decorators.

    Returns entries with: path, module (filename stem), summary (first line of
    the module docstring).
    """
    entries: list[dict[str, str]] = []
    if not source_dir.is_dir():
        return entries
    for py_file in sorted(source_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        text = py_file.read_text()
        # Module docstring first line (rough parse — no ast to avoid
        # import-loading these modules).
        summary = ""
        if text.lstrip().startswith('"""'):
            start = text.index('"""') + 3
            end = text.index('"""', start)
            summary = _first_line(text[start:end])
        for match in _WS_DECORATOR_RE.finditer(text):
            entries.append(
                {
                    "path": match.group(1),
                    "module": py_file.stem,
                    "summary": summary,
                }
            )
    entries.sort(key=lambda e: e["path"])
    return entries


# ---------------------------------------------------------------------------
# Markdown emission
# ---------------------------------------------------------------------------


def _endpoint_row(endpoint: dict[str, Any]) -> str:
    method = endpoint["method"]
    path = endpoint["path"]
    summary = endpoint["summary"] or "(no summary)"
    return f"| `{method:<6} {path}` | {summary} |"


def _endpoint_bullet(endpoint: dict[str, Any]) -> str:
    """Compact bullet form (used when table would be noisy)."""
    method = endpoint["method"]
    path = endpoint["path"]
    summary = endpoint["summary"] or "(no summary)"
    parts = [f"- **`{method} {path}`** — {summary}"]
    tags = endpoint.get("tags") or []
    response = endpoint.get("response_model") or ""
    if tags or response:
        extras = []
        if tags:
            extras.append(f"tags: `{', '.join(tags)}`")
        if response:
            extras.append(f"response: `{response}`")
        parts.append("  - " + "; ".join(extras))
    return "\n".join(parts)


def render_rest_catalog(
    endpoints: list[dict[str, Any]],
    group_by: str = "tag",
    style: str = "table",
) -> str:
    """Render REST endpoints as a Markdown catalog.

    ``style``: "table" (method+path | summary) or "bullet" (with tags+response).
    ``group_by``: "tag", "prefix", or "none".
    """
    if not endpoints:
        return "_(no endpoints match the provided filter)_"

    # Group.
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if group_by == "none":
        groups[""] = endpoints
    elif group_by == "prefix":
        for e in endpoints:
            parts = [p for p in e["path"].split("/") if p]
            # /api/v1/arena/positions -> "arena"; /api/v1/positions -> "positions"
            key = parts[2] if len(parts) >= 3 and parts[0] == "api" else (parts[0] if parts else "")
            groups[key].append(e)
    else:  # tag
        for e in endpoints:
            key = ", ".join(e["tags"]) if e["tags"] else "untagged"
            groups[key].append(e)

    lines: list[str] = []
    for group_name in sorted(groups.keys()):
        if group_name and group_by != "none":
            lines.append(f"**{group_name}**")
            lines.append("")
        if style == "bullet":
            for endpoint in groups[group_name]:
                lines.append(_endpoint_bullet(endpoint))
            lines.append("")
        else:  # table
            lines.append("| Endpoint | Summary |")
            lines.append("|----------|---------|")
            for endpoint in groups[group_name]:
                lines.append(_endpoint_row(endpoint))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_websocket_catalog(entries: list[dict[str, str]]) -> str:
    """Render WebSocket endpoints as a Markdown table."""
    if not entries:
        return "_(no WebSocket endpoints found)_"
    lines = [
        "| Endpoint | Module | Description |",
        "|----------|--------|-------------|",
    ]
    for entry in entries:
        lines.append(f"| `WS {entry['path']}` | `{entry['module']}` | {entry['summary']} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# JSON emission (for tooling / --format json)
# ---------------------------------------------------------------------------


def render_json(endpoints: list[dict[str, Any]], ws_entries: list[dict[str, str]]) -> str:
    import json

    return json.dumps(
        {"rest": endpoints, "websocket": ws_entries},
        indent=2,
        sort_keys=True,
    )


# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------


def verify_catalog_freshness(schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (ok, missing_paths). ``ok`` is False if any path is undocumented.

    Also checks that every `@<router>.websocket("...")` path shows up in the
    architecture.md file.
    """
    md_text = ARCHITECTURE_MD.read_text() if ARCHITECTURE_MD.exists() else ""
    missing: list[str] = []
    for path in schema.get("paths", {}):
        if path in _EXCLUDED_PATHS:
            continue
        if path not in md_text:
            missing.append(path)
    for entry in extract_websocket_endpoints():
        if entry["path"] not in md_text:
            missing.append(f"WS {entry['path']}")
    missing.sort()
    return (not missing, missing)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ensure_event_loop() -> None:
    """FastAPI/starlette's test-side routines sometimes poke at a running loop.

    We don't await anything, but guard against "no current event loop" warnings
    under some Python configurations.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path-prefix", default=None, help="Include only paths starting with this prefix (e.g., /api/v1/arena)")
    parser.add_argument("--exclude-prefix", default=None, help="Exclude paths starting with this prefix")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--group-by", choices=("tag", "prefix", "none"), default="none")
    parser.add_argument("--style", choices=("table", "bullet"), default="table", help="Markdown output style (default table)")
    parser.add_argument("--websocket", action="store_true", help="Emit WebSocket catalog (in addition to REST if no --path-prefix given)")
    parser.add_argument("--verify", action="store_true", help="Exit non-zero if any route is missing from docs/architecture.md")
    parser.add_argument("--stats", action="store_true", help="Print route-count statistics to stderr")
    args = parser.parse_args(argv)

    _ensure_event_loop()

    t0 = time.perf_counter()
    app = _build_app_for_introspection()
    schema = app.openapi()
    build_ms = int((time.perf_counter() - t0) * 1000)

    if args.verify:
        ok, missing = verify_catalog_freshness(schema)
        if ok:
            print("OK — architecture.md lists every REST + WebSocket endpoint.", file=sys.stderr)
            return 0
        print(f"DRIFT — {len(missing)} endpoint(s) missing from docs/architecture.md:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    endpoints = extract_rest_endpoints(
        schema,
        path_prefix=args.path_prefix,
        exclude_prefix=args.exclude_prefix,
    )
    ws_entries = extract_websocket_endpoints() if args.websocket or args.path_prefix is None else []

    if args.stats:
        print(
            f"[stats] built app in {build_ms} ms; {len(endpoints)} REST route(s); "
            f"{len(ws_entries)} WebSocket route(s)",
            file=sys.stderr,
        )

    if args.format == "json":
        print(render_json(endpoints, ws_entries))
        return 0

    out: list[str] = []
    if not args.websocket or args.path_prefix is not None:
        out.append(render_rest_catalog(endpoints, group_by=args.group_by, style=args.style))
    if args.websocket or (args.path_prefix is None and ws_entries):
        if out:
            out.append("\n**WebSocket endpoints**\n")
        out.append(render_websocket_catalog(ws_entries))
    print("".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
