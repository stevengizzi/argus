# IMPROMPTU-08 — Tier 2 Review

**Reviewer:** @reviewer subagent (Tier 2, read-only)
**Review date:** 2026-04-23
**Commit under review:** UNCOMMITTED (working tree on `main`). Operator handoff item: commit + green CI URL to be cited on push.
**Diff range:** `git diff HEAD` (4 tracked + 3 untracked paths listed below)
**CI run cited:** TBD — pending commit (flagged as operator handoff; not a review blocker per kickoff guidance)
**Close-out read:** `docs/sprints/sprint-31.9/IMPROMPTU-08-closeout.md` (CLEAN self-assessment)

---BEGIN-REVIEW---

## Summary

IMPROMPTU-08 is a docs-and-tooling session that closes DEF-168 by regenerating the 9 API-catalog sections of `docs/architecture.md` from the authoritative FastAPI `app.openapi()` schema, and commits a small introspection script so future regens are one command plus a CI gate. The diff is tightly scoped: zero runtime code changed (`git diff argus/` empty), only documentation, a new `scripts/generate_api_catalog.py` (455 LOC), a new `tests/docs/` package with 4 freshness tests, and the campaign-tracker bookkeeping updates.

All seven session-specific review checks pass. The drift-probe (removing `/api/v1/arena/positions` from the doc) produces a clean, precise failure with the exact missing path in the message, then reverts green — the regression gate is revert-proof. The generator is idempotent (byte-identical output across two runs). The WebSocket fallback parser catches all four `@<router>.websocket(...)` decorators in `argus/api/websocket/`. Narrative/DEC/diagram content around the regenerated catalog regions is preserved; the `§14.2 Comparison Module API` ambiguous-section decision is documented in-line; the `§7.8` AI-chat JSON schema blocks are untouched.

One minor code-quality finding on `test_verify_helper_detects_drift` (re-implements the detection logic inline instead of exercising `verify_catalog_freshness()`) and one stale inline HTML comment on architecture.md line 160 that now needs a trivial update. Neither rises to ESCALATE.

**Verdict: CONCERNS (both non-blocking, follow-on).**

## Session-specific review focus (kickoff §"Session-Specific Review Focus")

### Check 1 — No runtime API change

```
$ git diff HEAD -- argus/     →  (empty)
$ git diff HEAD -- config/    →  (empty)
$ git diff HEAD -- workflow/  →  (empty)
```

**Status: CLEAR.** The three escalation-guard diffs are all empty. No runtime code, no YAML config, no submodule edits.

### Check 2 — Catalog completeness (freshness gate)

```
$ python scripts/generate_api_catalog.py --verify
OK — architecture.md lists every REST + WebSocket endpoint.
$ echo $?
0
```

**Status: CLEAR.** Exit 0 + "OK" diagnostic. Pre-fix value (cited in close-out) was 33 missing paths; post-fix is clean.

### Check 3 — Narrative preservation (spot-checked 5 sections, target was 3)

- **§4 catalog freshness note (L1695-1704).** Present, correctly cites DEF-168 + IMPROMPTU-08, points at both `scripts/generate_api_catalog.py --verify` and the new test module. "How to regenerate" remediation is explicit.
- **§4 Implementation Status (Sprint 14) (L1706-1717).** Intact. 9-bullet list preserved.
- **§4 Authentication block (L1989-1995).** Intact. DEC-351 + DEC-102 cross-refs preserved; `HTTPBearer(auto_error=False)` behavior described.
- **§4 WebSocket stream-payload blocks (L1967-1987).** Both fenced payload enumerations preserved. The `/ws/v1/arena` block correctly lists `arena_tick_price` (Sprint 32.8) in the first payload line — not deleted as escalation check 5 worried about.
- **§7.8 AI-chat Client→Server / Server→Client JSON schemas (L2481-2498).** Both fenced JSON blocks intact — `auth` / `message` / `cancel` and `token` / `tool_use` / `stream_end` / `error` envelopes are all preserved. This section was correctly NOT catalog-replaced.
- **§13.5.1 Arena narrative (L2694-2696).** `OrderManager.get_managed_positions()`, `overflow.broker_capacity` (50 aligned with `max_concurrent_positions`), `IntradayCandleStore`, and the **390 → 720** bar-cap update are all present. Close-out §"Judgment calls (5)" flagged this as a stale-fact refresh; spot-checked against MEMORY.md / CLAUDE.md — Sprint 32.8 did raise to 720 (MEMORY.md: `_MAX_BARS_PER_SYMBOL 390→720`), so the update is accurate.
- **§14.2 Comparison Module API (L2750-2764).** Renamed per ambiguous-section decision. In-section note explicitly states "Python module, not an HTTP API — `comparison.py` is not route-exposed." Introspection cross-checked:
  ```
  $ python -c "import inspect, importlib; m = importlib.import_module('argus.analytics.comparison'); ..."
  compare            (a: 'MultiObjectiveResult', b: 'MultiObjectiveResult') -> 'ComparisonVerdict'
  pareto_frontier    (results: 'list[MultiObjectiveResult]') -> 'list[MultiObjectiveResult]'
  soft_dominance     (a: ..., b: ..., tolerance: 'dict[str, float] | None' = None) -> 'bool'
  is_regime_robust   (result: ..., min_regimes: 'int' = 3) -> 'bool'
  format_comparison_report (a: ..., b: ...) -> 'str'
  ```
  All 5 documented signatures match the live `inspect.signature()` output byte-for-byte. `format_comparison_report` (previously undocumented per close-out) is now listed.
- **§15.8 Experiments + Counterfactual REST (L2879-2899).** `GET /api/v1/counterfactual/accuracy` is now present (was flagged as previously-missing). Behaviour notes preserved: 503-when-disabled, BackgroundTasks dispatch, R-multiple serialization (IMPROMPTU-07 cross-ref), FilterAccuracyReport breakdown.

**Status: CLEAR.** Narrative, DEC cross-references, sprint notes, and ASCII fenced blocks are preserved. Only enumeration-style bullet lists were replaced — the exact treatment the kickoff mandated.

### Check 4 — Regression test actually regresses (drift probe)

Manual probe sequence:
```
$ cp docs/architecture.md /tmp/architecture_backup.md
$ grep -c '/api/v1/arena/positions' docs/architecture.md     →  3
$ sed -i '' 's|/api/v1/arena/positions|/api/v1/arena/REDACTED_FOR_PROBE|g' docs/architecture.md
$ grep -c '/api/v1/arena/positions' docs/architecture.md     →  0
$ python -m pytest tests/docs/.../test_architecture_md_lists_all_rest_routes -xvs
E  Failed: 1 REST route(s) missing from docs/architecture.md. Run `python scripts/generate_api_catalog.py
E  --verify` for the same diagnostic, then regenerate with
E  `python scripts/generate_api_catalog.py` and paste. Missing: ['/api/v1/arena/positions']
$ cp /tmp/architecture_backup.md docs/architecture.md       →  reverted
$ python -m pytest tests/docs/.../test_architecture_md_lists_all_rest_routes -xvs
PASSED
```

**Status: CLEAR.** Test regresses cleanly with the exact missing-path diagnostic + remediation recipe, then passes post-revert. Revert-proof against doc drift.

### Check 5 — Script idempotence

```
$ python scripts/generate_api_catalog.py > /tmp/run1.md 2>/dev/null
$ python scripts/generate_api_catalog.py > /tmp/run2.md 2>/dev/null
$ diff /tmp/run1.md /tmp/run2.md
(empty — IDEMPOTENT OK)
$ python -m pytest tests/docs/test_architecture_api_catalog_freshness.py::test_catalog_generator_is_idempotent -xvs
PASSED
```

**Status: CLEAR.** Byte-identical across invocations. The `endpoints.sort(key=lambda e: (e["path"], e["method"]))` on `generate_api_catalog.py:202` and `entries.sort(...)` on L245 + `sorted(groups.keys())` on L308 collectively guarantee deterministic output.

### Check 6 — WebSocket fallback catches every `@router.websocket(...)`

```
$ grep -rn "@\w*router\.websocket\|@\w*\.websocket" argus/api/websocket/
argus/api/websocket/arena_ws.py:220:@arena_ws_router.websocket("/ws/v1/arena")
argus/api/websocket/observatory_ws.py:40:@observatory_ws_router.websocket("/ws/v1/observatory")
argus/api/websocket/ai_chat.py:49:@ai_ws_router.websocket("/ws/v1/ai/chat")
argus/api/websocket/live.py:467:@ws_router.websocket("/ws/v1/live")
```

All 4 WS paths appear in `docs/architecture.md`:
- `/ws/v1/ai/chat`: 4 occurrences (§4 WebSocket table + §7.8 detail + §4 audit cross-refs)
- `/ws/v1/arena`: 4 occurrences (§4 WebSocket table + §13.5.2 detail + narrative)
- `/ws/v1/live`: 2 occurrences (§4 WebSocket table + stream-payload narrative)
- `/ws/v1/observatory`: 2 occurrences (§4 WebSocket table + §13.2 header)

The regex in `generate_api_catalog.py:211-214` — `@\w+\.websocket\s*\(\s*['\"]([^'\"]+)['\"]` — correctly matches all 4 decorator styles (`@arena_ws_router.`, `@observatory_ws_router.`, `@ai_ws_router.`, `@ws_router.`).

**Status: CLEAR.**

### Check 7 — Test-count math

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
...
5077 passed, 32 warnings in 53.93s
```

Baseline was 5073; post-session is 5077 → delta +4, all in the new `tests/docs/test_architecture_api_catalog_freshness.py` module (4-test collection verified via `--collect-only`).

**Status: CLEAR.** Matches close-out claim exactly.

## Sprint-level regression checks

- **pytest net delta = +4 (target +1 per kickoff; delta came in 3 over because the close-out added idempotence, drift-sanity, and all-WS guards on top of the required all-REST guard — all defensible).** CLEAR.
- **Vitest count unchanged.** No `argus/ui/` files in `git status` — confirmed via `git diff HEAD -- argus/ui/` returning empty. CLEAR.
- **No scope boundary violation.** `git diff argus/` empty, `git diff config/` empty, `git diff workflow/` empty, `git diff docs/audit-2026-04-21/` empty. CLEAR.
- **No runtime code change.** Reconfirmed. CLEAR.

## Sprint-level escalation criteria (none triggered)

| Criterion | Status |
|---|---|
| Any file under `argus/` modified | ✅ None — `git diff argus/` empty |
| OpenAPI schema structurally changed (routes/tags/response_model) | ✅ Script only reads `app.openapi()`; no route decorators, tags, or response_models touched |
| Script not idempotent | ✅ Two-run diff empty; `test_catalog_generator_is_idempotent` passes |
| Regression test passes with a known-missing route (test is vacuous) | ✅ Drift-probe confirmed: removing `/api/v1/arena/positions` fails the test with correct diagnostic |
| Narrative/DEC/diagram content deleted or reworded beyond catalog sections | ✅ Spot-checked 7 sections; only enumeration-style bullet lists replaced |
| Catalog freshness note missing from near top of §4 | ✅ Present at L1695-1704 |
| §14.2 was regenerated from OpenAPI | ✅ Kept as Python-module doc with introspected signatures + in-section "not applicable" note |
| §7.8 WebSocket JSON schema blocks deleted | ✅ Both JSON blocks preserved at L2485-2498 |
| `scripts/generate_api_catalog.py` does anything beyond reading the schema | ✅ Only reads `app.openapi()`; `_build_app_for_introspection()` constructs an in-process app (no lifespan, no DB, no broker connect) for schema reads, as the docstring describes |

**No escalation triggers fired.**

## Findings

### Finding 1 — `test_verify_helper_detects_drift` doesn't exercise the real helper it claims to guard

**Severity:** CONCERNS (non-blocking, follow-on).
**Evidence:** `tests/docs/test_architecture_api_catalog_freshness.py:107-140`. The test's docstring says "The freshness helper must actually regress when a fake route is added. Sanity check that the verify gate isn't vacuously passing." The body imports the generator module and does construct a fake schema, but then at L124-L138 it reimplements the detection logic inline (`[p for p in fake_schema["paths"] if p not in _IGNORED_PATHS and p not in ARCHITECTURE_MD.read_text()]`) rather than calling `generator.verify_catalog_freshness(fake_schema)` (defined at `scripts/generate_api_catalog.py:358`).

This means:
- The test proves the *pattern* detects drift (true).
- The test does NOT prove that `verify_catalog_freshness()` uses that pattern — if someone changed the helper to, say, skip paths via a denylist or add a bug like `if path.lower() not in md_text.lower()`, this test would still pass.

End-to-end protection is still provided by `test_architecture_md_lists_all_rest_routes` (which I drift-probed and confirmed regresses correctly), so this is not a correctness gap — it is a naming/intent mismatch.

**Remediation:** Follow-on, single-line fix. Replace L124-L138 with:
```python
ok, missing = generator.verify_catalog_freshness(fake_schema)
assert not ok, "Verify-helper logic did not detect the injected fake route"
assert "/api/v1/never-documented-synthetic-sentinel-def168" in missing
```

This is non-blocking — the overall gate works.

### Finding 2 — Stale inline HTML comment references DEF-168 as "remains open"

**Severity:** CONCERNS (non-blocking, follow-on — trivial doc hygiene).
**Evidence:** `docs/architecture.md:156-163`. An HTML comment block inside §3.1 (event catalog) reads: "DEF-168 still tracks the broader API-catalog drift; this block was regenerated from `argus/core/events.py` but a full FastAPI-introspection rebuild remains open." This comment was accurate when FIX-05 (audit 2026-04-21) shipped the event-catalog patch, but now that IMPROMPTU-08 has closed DEF-168, the "remains open" clause is inaccurate.

The comment is not rendered in any Markdown preview (HTML `<!-- -->` is invisible in rendered docs), so this is strictly a source-code hygiene item for future doc authors who grep for DEF-168.

**Remediation:** Update L160-L163 to:
```
(actually two fields: `viable_count`, `total_fetched`). A full FastAPI-introspection
rebuild landed under DEF-168 / IMPROMPTU-08 (2026-04-23); this block was regenerated
from `argus/core/events.py` as part of FIX-05.
```

Or delete the comment entirely now that both sibling patches have landed. Non-blocking; can be folded into the next doc-sync pass.

### Finding 3 — (Info-only) Test-count overshot by +3 vs kickoff's +1 target

**Severity:** Informational only (not CONCERNS).
**Evidence:** Kickoff §"Test Targets" specifies `Net test delta: +1`. Actual delta is +4. The additional 3 tests (`test_architecture_md_lists_all_websocket_routes`, `test_catalog_generator_is_idempotent`, `test_verify_helper_detects_drift`) add valuable defense-in-depth guards (WS path coverage, nondeterminism regression-guard, and the sanity check from Finding 1). All 4 tests are in the new module; none modify existing tests.

No remediation — overshoot is positive-signal (more coverage, not less, and the kickoff's `+1` target was a floor not a ceiling).

## Operator handoff items

1. **Green CI URL** (kickoff Definition-of-Done and operator-handoff summary both require it). Not available at review time — work is uncommitted. To be cited when the session commits to `main`. Per the review kickoff ("Green CI URL is 'TBD' — the work is not yet committed. Do not fail on that; flag it as an operator handoff item"), this is a handoff item, not a verdict blocker.
2. **Finding 1 + 2 remediation** (~10 minutes) — either a follow-on commit in the same sprint-close session or a deferred doc-hygiene pass. Neither is blocking.

## Test verification (local)

| Harness | Result |
|---|---|
| `python -m pytest --ignore=tests/test_main.py -n auto -q` | 5077 passed, 32 warnings in 53.93s |
| `python -m pytest tests/docs/test_architecture_api_catalog_freshness.py -xvs` | 4 passed in 1.07s |
| `python scripts/generate_api_catalog.py --verify` | exit 0, "OK — architecture.md lists every REST + WebSocket endpoint." |
| `python scripts/generate_api_catalog.py --stats` | exit 0; stderr: `[stats] built app in <ms>; 100 REST route(s); 4 WebSocket route(s)` |
| `python scripts/generate_api_catalog.py --websocket` | 4 rows (all /ws/v1/* paths), correct module attribution |
| `python scripts/generate_api_catalog.py --path-prefix /api/v1/arena` | 2 rows (`GET /api/v1/arena/candles/{symbol}`, `GET /api/v1/arena/positions`) |
| Drift probe (manual) | Test fails cleanly with correct diagnostic; revert → passes again |
| Idempotence check (manual `diff` of two invocations) | empty (byte-identical) |

## Verdict

**CONCERNS — non-blocking, follow-on.**

Both findings are minor: Finding 1 is a test that proves the right behaviour via duplicated inline logic rather than by exercising the named helper (functional-but-not-what-it-says-on-the-tin), and Finding 2 is a stale HTML comment that now contradicts resolved state. Neither affects correctness. The primary drift gate (`test_architecture_md_lists_all_rest_routes`) was drift-probed end-to-end and regresses cleanly. All 7 session-specific review focus checks and all sprint-level regression checks pass. No escalation criterion was triggered.

Recommend merge after:
1. (Required by kickoff) Commit + cite green CI URL on final push.
2. (Optional, follow-on) Fold Finding 1 + Finding 2 into either the same commit or the next doc-sync pass. Both are one-line edits.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "blocking": false,
  "escalation_triggered": false,
  "findings": [
    {
      "id": "IMPROMPTU-08-F1",
      "severity": "CONCERNS",
      "title": "test_verify_helper_detects_drift reimplements detection logic inline instead of calling verify_catalog_freshness()",
      "location": "tests/docs/test_architecture_api_catalog_freshness.py:107-140",
      "blocking": false,
      "remediation": "Replace inline list-comprehension with `ok, missing = generator.verify_catalog_freshness(fake_schema)`. Single-line fix. End-to-end protection already provided by test_architecture_md_lists_all_rest_routes (drift-probed and confirmed)."
    },
    {
      "id": "IMPROMPTU-08-F2",
      "severity": "CONCERNS",
      "title": "Stale inline HTML comment at architecture.md:160 states DEF-168 remains open",
      "location": "docs/architecture.md:156-163",
      "blocking": false,
      "remediation": "Update comment to cite DEF-168 as resolved via IMPROMPTU-08, or delete the comment entirely. HTML comment is invisible in rendered Markdown; strict source-hygiene item only."
    },
    {
      "id": "IMPROMPTU-08-F3",
      "severity": "INFO",
      "title": "Test-count delta +4 vs kickoff +1 target (overshoot, positive-signal)",
      "location": "tests/docs/test_architecture_api_catalog_freshness.py (entire module)",
      "blocking": false,
      "remediation": "None — +1 was a floor not a ceiling. Extra 3 tests add defense-in-depth (WS coverage, idempotence guard, drift-sanity guard)."
    }
  ],
  "scope_violations": [],
  "escalation_criteria_checked": [
    { "criterion": "Any file under argus/ modified", "triggered": false },
    { "criterion": "OpenAPI schema structurally changed", "triggered": false },
    { "criterion": "Script not idempotent", "triggered": false },
    { "criterion": "Regression test passes with a known-missing route (vacuous)", "triggered": false },
    { "criterion": "Narrative/DEC/diagram content deleted beyond catalog sections", "triggered": false },
    { "criterion": "Catalog freshness note missing near top of §4", "triggered": false },
    { "criterion": "§14.2 regenerated from OpenAPI (should stay Python-module doc)", "triggered": false },
    { "criterion": "§7.8 WebSocket JSON schema blocks deleted", "triggered": false },
    { "criterion": "Script does anything beyond reading the OpenAPI schema", "triggered": false }
  ],
  "test_results": {
    "pytest_full_suite": { "passed": 5077, "failed": 0, "skipped": 0, "delta_vs_baseline": 4, "baseline": 5073 },
    "new_module_tests": { "collected": 4, "passed": 4, "failed": 0 },
    "verify_gate_exit_code": 0,
    "idempotence_diff_empty": true,
    "drift_probe_result": "test fails cleanly with correct diagnostic; passes after revert"
  },
  "operator_handoff_items": [
    "Green CI URL to be cited on commit (kickoff Definition-of-Done, operator-handoff summary).",
    "Optional: fold Finding 1 + Finding 2 remediation into same commit or next doc-sync pass (both are one-line edits)."
  ]
}
```
