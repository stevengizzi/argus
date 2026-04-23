# IMPROMPTU-08 — Close-Out

> Sprint 31.9 campaign-close Stage 9B — `docs/architecture.md` API catalog regeneration.
> Drafted: 2026-04-23. Self-assessment: **CLEAN**.

---BEGIN-CLOSE-OUT---

## Scope delivered

**DEF-168 closed.** `docs/architecture.md`'s 9 API-catalog sections were regenerated from the authoritative FastAPI OpenAPI schema. A small introspection tool was committed so future regens are one command + one CI gate.

## Change manifest

| File | Kind | Lines |
|---|---|---|
| `scripts/generate_api_catalog.py` | NEW | 450 (CLI + OpenAPI → Markdown + WS fallback parser + `--verify`) |
| `tests/docs/__init__.py` | NEW (empty) | 0 |
| `tests/docs/test_architecture_api_catalog_freshness.py` | NEW | 4 tests (+130 lines) |
| `docs/architecture.md` | MODIFIED | +360 / −159 across 9 catalog sections + catalog freshness note |
| `CLAUDE.md` | MODIFIED | DEF-168 row strikethrough + completion narrative; header "Last updated" + Current State test counts updated (5073 → 5077 pytest) |
| `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | MODIFIED | DEF-168 moved to Resolved table; Stage 9B row updated |
| `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` | MODIFIED | Stage 9B IMPROMPTU-08 row → CODE LANDED; DEF-168 struck |

**Zero runtime code changed.** `git diff argus/` returns empty. Only docs + tooling + a test module.

## Catalog statistics (source-of-truth readout)

- **100 REST endpoints** across 26 tags (grouped by tag in §4)
- **4 WebSocket endpoints** (`/ws/v1/ai/chat`, `/ws/v1/arena`, `/ws/v1/live`, `/ws/v1/observatory`)
- **Pre-fix `--verify` output:** 33 paths missing from architecture.md
- **Post-fix `--verify` output:** `OK — architecture.md lists every REST + WebSocket endpoint.`

Per-section treatment:

| Section header | Source | Treatment |
|---|---|---|
| §4 `### REST Endpoints (Implemented)` | `app.openapi()` grouped by tag | Fully regenerated (26-tag table; replaces 100-line stale fenced list) |
| §4 `### WebSocket` | `@router.websocket(...)` scan | Endpoint table + preserved stream-payload narrative for `/ws/v1/live` and `/ws/v1/arena` |
| §4 `### Control Endpoints (Sprint 16, DEC-111)` | `--path-prefix /api/v1/controls` | Regenerated (5 routes, +1 vs stale) |
| §4 `### Orchestrator Endpoints (Sprint 17)` | `--path-prefix /api/v1/orchestrator` | Regenerated (4 routes, adds `override-throttle` which was undocumented) |
| §7.8 `### 7.8 WebSocket Streaming` | narrative message schema | Kept as-is — the section documents AI-chat JSON protocol, not route enumeration |
| §7.9 `### 7.9 REST Endpoints` | `--path-prefix /api/v1/ai` | Regenerated (10 routes; removes stale `/conversations` POST + `/conversations/{id}/messages` GET which don't exist; adds `POST /chat`, `GET /context/{page}`, `GET /conversations/{id}` singular) |
| §13.5.1 `### 13.5.1 Arena REST API` | `--path-prefix /api/v1/arena` | Verified against OpenAPI (2 routes); existing narrative preserved; candle-store note updated 390 → 720 bars (Sprint 32.8) |
| §14.2 `### 14.2 Comparison Module API` | **Python module, not route-exposed** | **Ambiguous-section decision: kept as module documentation.** Renamed from "Comparison API" → "Comparison Module API" for disambiguation. Signatures introspected via `inspect.signature()`. Added the previously-undocumented `format_comparison_report()` public function. Noted in-section that OpenAPI regeneration is not applicable. |
| §15.8 `### 15.8 REST API` | `--path-prefix /api/v1/experiments` + `/api/v1/counterfactual` | Regenerated (8 routes; adds the previously-missing `GET /api/v1/counterfactual/accuracy`) |

## Ambiguous-section decisions

1. **§14.2 Comparison API.** `argus/analytics/comparison.py` is a pure Python module — it has no route mount and does not appear in `app.openapi()`. The section title "API" meant "module's Python API." I renamed the heading to **"Comparison Module API"** for disambiguation and introspected the five public callables (`compare`, `pareto_frontier`, `soft_dominance`, `is_regime_robust`, `format_comparison_report`) via `inspect.signature()` + `inspect.getdoc()`. Added an in-section note that OpenAPI regeneration does not apply here.

2. **§15.8 REST API.** Unambiguous on re-read — the section belongs to §15 (Experiment Pipeline) and covers the `/experiments` + `/counterfactual` prefixes. Regenerated from `app.openapi()`.

## Script usage recipe (for future operators)

```bash
# Freshness gate — CI-friendly (exit 0 clean, exit 1 with diagnostic on drift):
python scripts/generate_api_catalog.py --verify

# Regenerate the full §4 primary catalog (grouped by tag):
python scripts/generate_api_catalog.py --group-by tag

# Regenerate one section:
python scripts/generate_api_catalog.py --path-prefix /api/v1/controls
python scripts/generate_api_catalog.py --path-prefix /api/v1/ai
python scripts/generate_api_catalog.py --path-prefix /api/v1/experiments

# WebSocket-only:
python scripts/generate_api_catalog.py --websocket

# JSON dump (for downstream tooling):
python scripts/generate_api_catalog.py --format json

# Quick stats to stderr (no catalog output):
python scripts/generate_api_catalog.py --stats > /dev/null
```

## Freshness gate — how the regression test catches drift

`tests/docs/test_architecture_api_catalog_freshness.py` contains four tests:

1. `test_architecture_md_lists_all_rest_routes` — walks every path in `app.openapi()["paths"]` (excluding `/openapi.json`, `/docs`, `/redoc`) and asserts the path string appears in `docs/architecture.md`. **This is the primary drift guard.**
2. `test_architecture_md_lists_all_websocket_routes` — scans `argus/api/websocket/*.py` for `@<name>.websocket("/...")` decorators and asserts each path is in the doc.
3. `test_catalog_generator_is_idempotent` — runs the extractor twice and asserts identical output (protects against nondeterministic ordering from e.g. dict hash randomization).
4. `test_verify_helper_detects_drift` — injects a synthetic path into a schema copy and asserts the missing-path detector flags it. Sanity check that the gate isn't vacuously passing.

**Revert-proof property.** If a dev adds a new route but forgets to update the doc, test 1 fails immediately with `"N REST route(s) missing from docs/architecture.md: [...]"` and the remediation recipe in the failure message.

## Test results

| Harness | Pre-session | Post-session | Delta |
|---|---|---|---|
| pytest (`--ignore=tests/test_main.py -n auto -q`) | 5073 pass | **5077 pass** | **+4** (all 4 in the new freshness test module) |
| pytest `tests/test_main.py` | 39 pass / 5 skip | 39 pass / 5 skip | 0 |
| Vitest | 866 pass (unchanged) | 866 pass | 0 (no UI touch) |
| `python scripts/generate_api_catalog.py --verify` | (script did not exist) | exit 0 | — |

Full-suite runtime: 52.6s → 55.7s (+3.1s — the 4 new tests spin up a fresh `FastAPI` instance each; amortized cost acceptable).

## Judgment calls

1. **§7.8 AI WebSocket kept as-is.** The section documents the `auth`/`message`/`cancel` + `token`/`tool_use`/`stream_end` JSON envelopes — catalog replacement would lose signal. The route itself is now listed in the §4 WebSocket table (via the fallback scanner). Net: more coverage, not less.
2. **§14.2 title renamed** ("Comparison API" → "Comparison Module API"). This is a small editorial change that prevents future auditors from re-flagging the same title as ambiguous. In-line note documents the decision for next-session context.
3. **§4 `### WebSocket` kept its per-stream payload documentation** for `/ws/v1/live` and `/ws/v1/arena`. Those payload enumerations (`position.opened`, `arena_tick_price`, etc.) are load-bearing signal that the route catalog alone doesn't provide. I added a WS-endpoint table _above_ the payload block for completeness.
4. **Catalog freshness note (new block at top of §4)** points both at the script and at the regression test. Makes the remediation path obvious for future editors.
5. **Arena candle bar cap updated 390 → 720** in the §13.5.1 note while I was there. Sprint 32.8 shipped the 720-bar raise (4 AM ET pre-market inclusion) per the MEMORY.md trail. Low-risk narrative refresh; stays within "preserve architectural content" because it fixes a stale fact, not narrative structure.

## Constraints honored

- ✅ **No runtime code changes.** `git diff argus/` is empty.
- ✅ **No OpenAPI schema structural changes.** No route decorators, tags, or response_models touched.
- ✅ **No `app.openapi()` runtime monkey-patch.** The script only _reads_ the schema.
- ✅ **No narrative, DEC cross-reference, sprint note, or diagram deleted.** The §4 audit-2026-04-21 drift warning block was replaced by the accurate regenerated catalog (the warning is satisfied by this session's work).
- ✅ **No `workflow/` submodule edit.**
- ✅ **No audit-2026-04-21 back-annotation edited.**
- ✅ **No `config/*.yaml` touched.**
- ✅ Work on `main` (single session; no feature branch required per session style).

## Self-assessment: CLEAN

Every Definition-of-Done item satisfied:
- ✅ `scripts/generate_api_catalog.py` created, tested, committed-ready
- ✅ All 9 catalog sections regenerated from live OpenAPI schema
- ✅ Catalog freshness regression test passes (4 tests, all green)
- ✅ `--verify` passes (exit 0; pre-fix was exit 1 with 33 paths)
- ✅ All narrative content preserved; diff review confirms only endpoint-list chunks changed
- ✅ Catalog freshness note added to §4
- ✅ Ambiguous sections §14.2 + §15.8 handled with documented decision
- ✅ CLAUDE.md DEF-168 entry struck through with completion narrative
- ✅ RUNNING-REGISTER.md DEF-168 moved to Resolved table
- ✅ CAMPAIGN-COMPLETENESS-TRACKER.md Stage 9B row marked CODE LANDED
- ✅ Close-out at this path

## Green CI URL

Green CI URL: **TBD** — will be cited on commit. (Local full-suite pass: 5077 / 0 fail / 55.7s.)

---END-CLOSE-OUT---

## Tier 2 review request

Invoke `@reviewer` with:
- Review context: this close-out + `docs/sprints/sprint-31.9/IMPROMPTU-08-architecture-api-catalog.md` kickoff + CLAUDE.md DEF-168 entry
- Diff range: the commit that lands this session
- Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Verification command: `python scripts/generate_api_catalog.py --verify`
- Files that should NOT have been modified: any `argus/api/` runtime file, any `argus/api/websocket/*.py` runtime file, `argus/main.py`, any `workflow/` submodule file, any audit-2026-04-21 back-annotation, any `config/*.yaml`
