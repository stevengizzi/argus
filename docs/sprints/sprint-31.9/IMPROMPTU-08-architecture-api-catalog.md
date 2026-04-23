# Sprint 31.9 IMPROMPTU-08: architecture.md API Catalog Regeneration

> Drafted Phase 1b. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Finding addressed:**
- **DEF-168** — `docs/architecture.md` API catalog sections are stale relative to the actual FastAPI app. The doc has 9 API-catalog section headers (lines 1691, 1708, 1910, 1921, 2309, 2328, 2507, 2565, 2688) documenting a subset of routes that have drifted from reality as endpoints were added during Sprints 28–32. The actual app at `argus/api/server.py:668` composes 30 route modules under `argus/api/routes/`. Regenerate the catalog sections so documentation matches implementation, and commit a small tooling script so future regens are one command.

**Files touched:**
- `docs/architecture.md` (major edit — ~200–500 lines of the 2,761 total will be rewritten, concentrated in the 9 API-catalog sections)
- `scripts/generate_api_catalog.py` (NEW — FastAPI introspection tool)
- `docs/architecture.md` header or a dedicated section may gain a "How this catalog is generated" note
- CLAUDE.md DEF-168 entry (strikethrough + commit SHA)

**Safety tag:** `safe-during-trading` — documentation + tooling only. No runtime code changes. Paper trading can continue.

**Theme:** Close DEF-168 by regenerating the API catalog from the authoritative source (the FastAPI app's OpenAPI schema), and leave behind tooling so the catalog stays fresh via one-command regen. Single-purpose session.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count: __________ (baseline)
```

**Expected baseline:** Post-IMPROMPTU-07 count.

### 3. Verify FastAPI app imports cleanly

```bash
python -c "from argus.api.server import app; print(f'{len(app.routes)} routes')"
# Expected: a three-digit number; non-zero, no ImportError
```

If this fails, investigate before proceeding — you can't regenerate the catalog from an app that won't import.

### 4. Branch & workspace

```bash
git checkout main
git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

1. Read these files:
   - `CLAUDE.md` DEF-168 entry
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-08"
   - `docs/architecture.md` lines 1685–1930 (§4 Command Center API) — the primary catalog
   - `docs/architecture.md` lines 2305–2340 (§7.8–7.9 WebSocket + REST in journal context)
   - `docs/architecture.md` lines 2500–2570 (§13.5.1 Arena REST API, §14.2 Comparison API)
   - `docs/architecture.md` lines 2685–2700 (§15.8 REST API)
   - `argus/api/server.py` — the `app = FastAPI(...)` construction; which routers are registered
   - Sample of 3–5 route files: `argus/api/routes/positions.py`, `argus/api/routes/orchestrator.py`, `argus/api/routes/experiments.py` (get a feel for the route decorator + response_model + docstring patterns argus uses)
   - `argus/api/routes/__init__.py` — how routes get exported

2. Understand the 9 catalog section headers in architecture.md:
   ```
   Line 1691: ## 4. Command Center API (`argus/api/`)
   Line 1708: ### REST Endpoints (Implemented)
   Line 1910: ### Control Endpoints (Sprint 16, DEC-111)
   Line 1921: ### Orchestrator Endpoints (Sprint 17)
   Line 2309: ### 7.8 WebSocket Streaming (`api/websocket/ai_chat.py`)
   Line 2328: ### 7.9 REST Endpoints
   Line 2507: ### 13.5.1 Arena REST API (`api/routes/arena.py`)
   Line 2565: ### 14.2 Comparison API (`analytics/comparison.py`)
   Line 2688: ### 15.8 REST API
   ```
   Note that §4 (lines 1691–~2000) is the primary flat catalog; §§7.8–15.8 are subsystem-specific catalogs embedded in narrative sections. The subsystem catalogs should be **regenerated from the same source** (`app.openapi()`) but **filtered by path prefix** or by the router-module file (e.g., §13.5.1 filters to `/arena/*`).

## Objective

1. Build a small FastAPI-introspection script (`scripts/generate_api_catalog.py`)
   that reads the authoritative OpenAPI schema and emits a Markdown catalog.
2. Use the script to regenerate the 9 API catalog sections in `docs/architecture.md`.
3. Preserve all narrative/architectural commentary around the catalogs — only
   the endpoint-list table/enumeration content gets replaced.
4. Leave the script committed so future updates are `python scripts/generate_api_catalog.py`.

## Requirements

### Requirement 1: Introspection script

1. Create `scripts/generate_api_catalog.py` with these CLI options:
   ```
   --path-prefix <prefix>    # Filter to routes matching this prefix (e.g., /arena)
   --exclude-prefix <prefix> # Exclude routes matching (e.g., /openapi.json, /docs)
   --format {markdown,json}  # Output format (default markdown)
   --router <module>         # Filter to a single router module (optional)
   --group-by {tag,prefix,module}  # How to group in output (default tag)
   ```

2. Core logic:
   ```python
   from argus.api.server import app
   schema = app.openapi()
   paths = schema["paths"]
   # For each path + method:
   #   - Extract summary, description (first line), tags, response_model name
   #   - Group per --group-by
   #   - Emit markdown
   ```

3. Markdown output format per endpoint:
   ```markdown
   - **`GET /positions`** — List all positions (live + shadow).
     - Tags: `positions`
     - Response: `PositionsResponse`
   ```
   (Exact format is flexible; the goal is "every endpoint is listed with method, path, one-line summary, and response model." Match the style of the existing catalog sections where possible — preserve the style operator is used to.)

4. WebSocket endpoints are NOT in `app.openapi()` (FastAPI doesn't emit them). For §7.8 WebSocket Streaming, the script falls back to parsing `argus/api/websocket/*.py` for `@router.websocket(...)` decorators. Extract the path + the module docstring first-line as the summary.

5. Self-test: when the script is run with no filters, it must emit a catalog that contains at least one entry for every path in `app.openapi()["paths"]`. Add a `--verify` mode that asserts this and exits non-zero on drift.

### Requirement 2: Regenerate the 9 catalog sections

For each of the 9 section headers, replace the stale content with script output using the appropriate filters:

| Section | Header | Filter args |
|---|---|---|
| §4 primary | `### REST Endpoints (Implemented)` (line 1708) | No filter — all REST endpoints |
| §4 control | `### Control Endpoints (Sprint 16, DEC-111)` (line 1910) | `--path-prefix /controls` |
| §4 orchestrator | `### Orchestrator Endpoints (Sprint 17)` (line 1921) | `--path-prefix /orchestrator` |
| §7.8 WebSocket | `### 7.8 WebSocket Streaming` (line 2309) | (WebSocket fallback parser) |
| §7.9 REST | `### 7.9 REST Endpoints` (line 2328) | `--path-prefix /ai` or `--router ai` |
| §13.5.1 Arena | `### 13.5.1 Arena REST API` (line 2507) | `--path-prefix /arena` |
| §14.2 Comparison | `### 14.2 Comparison API` (line 2565) | (This one may not be a route — it's the `analytics/comparison.py` module. If so, note the mismatch and document the module's public functions instead of regenerating from OpenAPI) |
| §15.8 REST API | `### 15.8 REST API` (line 2688) | (Context-dependent — read the surrounding section header to determine the subsystem) |

**Preservation rules:**
- Retain all architectural narrative paragraphs around each catalog
- Retain any cross-references to DECs, sprints, or FIX-NN commits
- Retain any diagrams or ASCII-art that surround the catalogs
- Retain hand-authored notes about authentication, rate limiting, or special behaviors
- Replace ONLY the endpoint-list bullets/tables

### Requirement 3: Catalog regeneration note

1. Near the top of §4 (line ~1691), add a brief meta-note:
   ```markdown
   > **Catalog freshness:** The endpoint listings below were regenerated on
   > {DATE} from the FastAPI `app.openapi()` schema via
   > `scripts/generate_api_catalog.py`. If you modify this file, also
   > rerun that script after any route addition/removal. A `--verify` mode
   > is available for CI.
   ```

2. If feasible and within scope budget, add a CI check: `python scripts/generate_api_catalog.py --verify` that fails the workflow if any route exists in `app.openapi()` but not in `architecture.md`. This requires parsing the markdown — fine if it takes ≤50 LOC; otherwise defer as a new DEF with a note in the close-out.

### Requirement 4: Handle ambiguous sections

1. **§14.2 Comparison API** — This section is titled "REST API" but the path description `analytics/comparison.py` suggests it's a module API, not an HTTP API. Read the surrounding context:
   - If `comparison.py` is a pure Python module (not route-exposed), rewrite the section to document the public function signatures instead. Use `inspect.signature()` on the public callables.
   - If it IS route-exposed under some prefix, regenerate from OpenAPI like the others.
   - Document the decision in the close-out.

2. **§15.8 REST API** — Determine the subsystem from the surrounding section header. Apply the appropriate filter, or if the subsystem has no routes, annotate the section as "planned/future" with a sprint reference.

### Requirement 5: Regression protection

1. Add a single regression test at `tests/docs/test_architecture_api_catalog_freshness.py` (new):
   ```python
   def test_architecture_md_lists_all_api_routes():
       """DEF-168: architecture.md must list every route registered in the FastAPI app."""
       from argus.api.server import app
       import re
       schema = app.openapi()
       with open("docs/architecture.md") as f:
           md = f.read()
       missing = []
       for path in schema["paths"].keys():
           if path in ("/openapi.json", "/docs", "/redoc"):
               continue
           # Check the path appears somewhere in the doc
           if path not in md:
               missing.append(path)
       assert not missing, f"{len(missing)} routes not in architecture.md: {missing[:10]}"
   ```
2. This test fails if the catalog drifts in the future — it's the freshness gate.

## Constraints

- **Do NOT modify** any argus runtime code (no route additions, no API contract changes).
- **Do NOT alter** the `app.openapi()` output by changing route decorators, tags, or response_model specifications. The catalog is a SHADOW of the app; fix the shadow, not the source.
- **Do NOT** write a tool that edits `app.openapi()` at runtime (e.g., monkey-patching FastAPI). The script READS the schema.
- **Do NOT delete** any architectural narrative, DEC cross-references, sprint notes, or diagrams. Only the endpoint-list content gets replaced.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- **Do NOT edit** audit-2026-04-21 doc back-annotations.
- Work directly on `main`.

## Test Targets

- New tests: **+1** (catalog freshness regression)
- Net test delta: +1
- Test command (scoped):
  ```bash
  python -m pytest tests/docs/test_architecture_api_catalog_freshness.py -xvs
  python scripts/generate_api_catalog.py --verify
  ```
- Full suite:
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Definition of Done

- [ ] `scripts/generate_api_catalog.py` created, tested, and committed
- [ ] 9 catalog sections in `docs/architecture.md` regenerated from current `app.openapi()` schema
- [ ] Catalog freshness regression test passes (and fails if a new route is added without re-running the script)
- [ ] `--verify` mode works and passes currently
- [ ] All narrative content preserved (diff review confirms only endpoint-list chunks changed)
- [ ] Catalog freshness note added near top of §4
- [ ] Ambiguous sections (§14.2, §15.8) handled with documented decision
- [ ] CLAUDE.md DEF-168 entry updated with strikethrough + commit SHA
- [ ] `RUNNING-REGISTER.md` updated: DEF-168 moved to "Resolved this campaign" table
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9B row for IMPROMPTU-08 marked CLEAR
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-08-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-08-review.md`
- [ ] Green CI URL cited (P25 rule)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Every route in `app.openapi()["paths"]` appears in architecture.md | Run `python scripts/generate_api_catalog.py --verify`; regression test passes |
| WebSocket endpoints appear in §7.8 via the fallback parser | Manual spot-check |
| Narrative/architectural content preserved | Diff the non-catalog line ranges; confirm zero changes |
| Catalog freshness note present near §4 top | Grep for "Catalog freshness" |
| `--verify` mode works | Run it manually; exit 0 |
| Script runs without errors | `python scripts/generate_api_catalog.py > /tmp/out.md` succeeds |
| architecture.md still renders as valid markdown | Use a markdown linter or preview tool |
| No runtime code changes | `git diff argus/` returns zero |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/IMPROMPTU-08-closeout.md`

Include:
1. **Catalog statistics:** N routes total, N REST, N WebSocket, distribution across the 9 sections
2. **Ambiguous-section decisions:** §14.2 and §15.8 outcomes
3. **Script usage recipe:** typical invocations for future operators
4. **Freshness gate:** how the regression test catches drift
5. **Green CI URL** for final commit

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out writes.

Provide:
1. Review context: this kickoff file + CLAUDE.md DEF-168 entry
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-08-closeout.md`
3. Diff range: `git diff HEAD~N`
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified:
   - Any `argus/api/` runtime file (routes or server.py)
   - Any `argus/api/websocket/*.py` runtime file
   - `argus/main.py`
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation
   - `config/*.yaml`

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-08-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify no runtime API change.** The whole point: docs drift was the bug, not the code. `git diff argus/` must return zero lines except whitespace/comment-only.
2. **Verify catalog completeness.** Run `python scripts/generate_api_catalog.py --verify` yourself. If it exits non-zero, the regeneration missed routes.
3. **Verify narrative preservation.** Spot-check 3+ of the 9 sections by reading the surrounding paragraphs in the diff — confirm architectural text, DEC refs, sprint notes, and diagrams are intact.
4. **Verify the regression test actually regresses.** Manually add a fake route to the app's OpenAPI schema (via monkey-patch or test fixture) and confirm the test fails. Then revert.
5. **Verify the script is idempotent.** Running the script twice should produce identical output.
6. **Verify the WebSocket fallback catches all `@router.websocket(...)` sites.**
7. **Verify green CI URL for final commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = +1
- Vitest count unchanged (no UI touch)
- No scope boundary violation
- No runtime code change (`git diff argus/` empty)

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Any file under `argus/` (excluding empty diffs on comments) modified
- OpenAPI schema structurally changed (routes renamed, response_model changed, tags changed)
- Script not idempotent (two runs produce different output)
- Regression test passes with a known-missing route (test is broken)
- Narrative/DEC/diagram content in architecture.md was deleted or reworded beyond catalog sections
- Green CI URL missing or CI red

## Post-Review Fix Documentation

Standard protocol per the implementation-prompt template.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Catalog stats:** total routes, section distribution
4. **Tooling note:** `python scripts/generate_api_catalog.py --verify` is now the freshness gate
5. Green CI URL
6. One-line summary: `Session IMPROMPTU-08 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {pre} → {post}. CI: {URL}. DEF closed: DEF-168. Future regens: python scripts/generate_api_catalog.py.`
