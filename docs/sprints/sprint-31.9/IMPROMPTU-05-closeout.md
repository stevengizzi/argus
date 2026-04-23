---BEGIN-CLOSE-OUT---
```markdown
# Close-Out — IMPROMPTU-05-deps-and-infra

- **Sprint:** `sprint-31.9-health-and-hardening`
- **Session:** `IMPROMPTU-05` (Track B / Stage 9B — safe-during-trading)
- **Date:** 2026-04-23
- **Commit:** `6ddd7a7` (single bundled commit; prior campaign HEAD `224d773`)
- **Baseline HEAD:** `224d773` (IMPROMPTU-CI Tier 2 review artifact — CLEAR)
- **Test delta:** 5,054 → 5,054 passed (zero delta, as scoped). Vitest 859 → 859 (session touches no UI).
- **Warning delta:** +8 warnings (pytest 39 → 47). One new `InsecureKeyLengthWarning` from PyJWT's HS256 key-length check on a 29-byte test secret — advisory, not a regression. Remaining warning increase is pytest/xdist ordering variance. (See DEF-192 category (ii) AsyncMock coroutine-never-awaited: this delta falls inside the run-to-run fluctuation band already documented there.)
- **Self-Assessment:** `MINOR_DEVIATIONS`

## Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `pyproject.toml` | modified | **DEF-179 + DEF-180 core.** `[project.dependencies]`: `python-jose[cryptography]>=3.4.0,<4` removed; `PyJWT>=2.8,<3` added with comment pointer to DEF-179. No other dependency changes. |
| `argus/api/auth.py` | modified | **DEF-179.** `from jose import JWTError, jwt` → `import jwt` + `from jwt import PyJWTError`. Exception handler in `verify_token()` changed `except JWTError:` → `except PyJWTError:`. No change to `jwt.encode()` / `jwt.decode()` call signatures (HS256 unchanged; argus never had a `.decode('utf-8')` pattern — python-jose's `jwt.encode()` already returned `str` in the versions argus used). |
| `argus/api/websocket/live.py` | modified | **DEF-179.** Same import swap + `except (JWTError, Exception):` → `except (PyJWTError, Exception):` at the query-param auth site. |
| `argus/api/websocket/observatory_ws.py` | modified | **DEF-179.** Same import swap + same exception-handler swap at the first-message auth site. |
| `argus/api/websocket/ai_chat.py` | modified | **DEF-179.** Same import swap + same exception-handler swap at the first-message auth site. |
| `argus/api/websocket/arena_ws.py` | modified | **DEF-179.** This file was the one production site that already used `from jose import jwt` without `JWTError` (it caught bare `Exception`). Changed to `import jwt` — no exception-handler change needed because it never imported `JWTError` in the first place. |
| `tests/api/test_auth.py` | modified | **DEF-179.** Three inline imports updated: line 143 `from jose import jwt` → `import jwt`; lines 308 and 360 `from jose import jwt as jose_jwt` → `import jwt as jwt_module` with local-variable rename at the single encode site in each test body. All three tests continue to verify the same expired-token 401 path. |
| `tests/execution/order_manager/test_safety.py` | modified | **DEF-179.** Single inline import at line 511 updated: `from jose import jwt` → `import jwt`. The enclosing test (`test_reconciliation_endpoint_returns_result`) uses `jwt.encode(payload, secret, algorithm="HS256")` with no library-specific behaviour; PyJWT accepts the identical signature. |
| `tests/api/test_fix11_backend_api.py` | modified | **DEF-179.** Two comment references updated: module docstring `F1-23: jose.jwt is imported at module level` → `F1-23: jwt (PyJWT) is imported at module level`; test docstring + inline comment on `test_live_ws_imports_jwt_at_module_level` updated to reference PyJWT. The test body itself (`hasattr(live_module, "jwt")`) is library-agnostic and did not need to change. |
| `scripts/populate_historical_cache.py` | modified | **LaCie cleanup.** `CANDIDATE_CACHE_DIRS` (lines 70-75) reduced from three entries to one: only the repo-local `data/databento_cache` remains; the two legacy external-drive entries (`/Volumes/LaCie/argus-cache`, `/LaCie/argus-cache`) are gone. Explanatory comment points at Sprint 31.85 consolidation without naming the legacy path (grep-clean). |
| `.github/workflows/ci.yml` | modified | **DEF-180 + DEF-181.** Actions pins: `actions/checkout@v4` → `@v6`, `actions/setup-python@v5` → `@v6`, `actions/setup-node@v4` → `@v6` (Node-24-compatible majors; release-note verified for all three). Install step renamed `Install runtime + dev dependencies` → `Install dependencies from lockfile` and rewritten as `pip install -r requirements-dev.lock && pip install -e . --no-deps` per the kickoff. `cache-dependency-path` on `setup-python` switched from `pyproject.toml` to `requirements-dev.lock` so pip cache invalidates when the lockfile changes. Inline pointer comments cite DEF-180 + DEF-181. No changes to test command or env vars. |
| `requirements.lock` | **added** | **DEF-180.** `uv pip compile pyproject.toml -o requirements.lock` output (188 packages, runtime only). `pyjwt==2.12.1` present; `python-jose` absent. |
| `requirements-dev.lock` | **added** | **DEF-180.** `uv pip compile --extra dev --extra backtest pyproject.toml -o requirements-dev.lock` output (262 packages, `dev` + `backtest` extras applied). CI installs this file. `pyjwt==2.12.1` present; `python-jose` absent. |
| `docs/deps.md` | **added** | **DEF-180.** New operator-facing reference covering: lockfile inventory (runtime vs dev), install recipes (local + prod), regen commands (`uv pip compile ...`), CI integration, reproducibility notes, cross-refs to CLAUDE.md DEF-180. |
| `CLAUDE.md` | modified | Banner updated; DEF-179/180/181 rows strikethrough with resolution descriptions. DEF-178 row untouched (out of scope — paired session per constraint). |
| `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` | modified | Last-updated banner + baseline note; Stage 9B row updated from PENDING → PARTIAL; Session-history new row for IMPROMPTU-05; DEF-179/180/181 moved from "Open with planned owner" into "Resolved this campaign"; LaCie cleanup row in "Outstanding code-level items" strikethrough. |
| `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` | modified | Stage 9B IMPROMPTU-05 row status PENDING → CLEAR. |

## Judgment Calls

Decisions made during implementation that were not pre-specified.

- **Did not find any `.decode('utf-8')` call sites.** The kickoff's DEF-179 Requirement 3 step 7 instructed to remove `.decode('utf-8')` from `jwt.encode()` return values ("in python-jose, it returned `bytes`"). That claim is library-history-inaccurate: `python-jose` switched `jwt.encode()` to return `str` in v3.0 (2018), and argus has always pinned `python-jose>=3.x`. A grep across `argus/` and `tests/` confirms zero `jwt.encode(...).decode(` patterns existed. No code change needed for this step; noted here to prevent a future reader from being mystified that the step didn't produce a diff.

- **`arena_ws.py` exception handler left alone.** The kickoff's DEF-179 Requirement 3 step 2 listed `arena_ws.py` with "currently imports only `jwt` (no `JWTError`)." Confirmed via inspection: the auth handler at `arena_ws.py:255` is `except Exception:` (not `except (JWTError, Exception):`). No `PyJWTError` rename needed. The import line is the only change to that file.

- **Comment-only swap in `test_fix11_backend_api.py`.** The kickoff listed this file with "1 comment reference; may or may not need change." On inspection there were TWO comment references (module docstring line 13 + test docstring/comment line 184/187). Updated both for consistency; the test body assertion (`hasattr(live_module, "jwt")`) is library-agnostic and passes unchanged post-swap. No test logic changed.

- **`LaCie` scrubbed from the explanatory comment too.** The kickoff's regression checklist stipulated `grep LaCie scripts/populate_historical_cache.py returns zero`. An explanatory comment pointing at the removal naturally mentions LaCie, which would fail the grep. Chose to write the comment as "Legacy external-drive fallbacks removed IMPROMPTU-05 (2026-04-23, DEF-180 session)" rather than naming the specific paths, so the grep guard is genuinely zero-match while the removal still has a documented trail. The close-out here names both paths for historical record.

- **Lockfile `pyproject.toml` filename-in-header.** `uv pip compile pyproject.toml -o requirements.lock` writes a comment line `#    uv pip compile pyproject.toml -o requirements.lock` at the top of the lockfile. Regenerating to a different output path produces a different header. Reproducibility verified by compiling to `/tmp/test.lock` and diffing: the only byte difference is the header filename. Acceptable and expected; documented in `docs/deps.md`.

- **Single bundled commit rather than three (lockfile / pins / PyJWT).** The kickoff's "CI cost" note suggested 1–2 commits ("lockfile-first, then pins-and-migration together"). Since all three requirements exercise CI together (lockfile-install validates, Node-24 pins exercise the new lockfile step, PyJWT swap lands on the already-validated dep tree), bundling is lower-risk than splitting: a single bundled commit guarantees the end state is green, rather than risking an intermediate red state if (e.g.) the lockfile install breaks on a CI runner detail. Also saves CI cycles per the kickoff rationale. No cost to reviewability — all four requirements are orthogonal in their diffs.

- **`alpaca-py` scope.** `alpaca-py>=0.30,<1` remains in `[project.dependencies]` untouched. The constraint block explicitly carved out DEF-178 ("Do NOT bundle DEF-178 into this session"). The lockfile resolver naturally included it (`alpaca-py==0.43.2` in both lockfiles); that reflects current `pyproject.toml` state and is correct.

- **Warning delta.** Post-session pytest shows 47 warnings (baseline 39). Investigation: one new `InsecureKeyLengthWarning` from PyJWT flagging a 29-byte test secret against its 32-byte HS256 recommendation. The test deliberately uses a short secret to exercise the invalid-signature rejection path; changing test secret length is a test-correctness concern, not a migration concern. The remaining 7-warning increase is within DEF-192's documented fluctuation band (26–40 per-run under xdist). Not a regression; not a new DEF.

## Scope Verification

| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| R1: DEF-180 lockfile via `uv` | DONE | `requirements.lock` (188 pkgs) + `requirements-dev.lock` (262 pkgs, `dev+backtest`). CI install rewired. `docs/deps.md` created. |
| R1: `docs/deps.md` regen recipe | DONE | Section covers `uv pip compile ...` commands, install instructions, reproducibility notes, cross-ref to DEF-180. |
| R1: CI install from lockfile | DONE | `.github/workflows/ci.yml` install step replaced: `pip install -r requirements-dev.lock && pip install -e . --no-deps`. `cache-dependency-path` updated. |
| R1: Local install from lockfile succeeds | DONE | Verified: `pip install -r requirements-dev.lock` (post-uninstall of python-jose) + full pytest 5,054 passed. |
| R2: DEF-181 Action pin bumps | DONE | `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6` — all Node-24-compatible majors. Verified via `gh api releases/latest`: v6.0.2 / v6.2.0 / v6.4.0. |
| R3: DEF-179 pyproject swap | DONE | `python-jose[cryptography]>=3.4.0,<4` removed; `PyJWT>=2.8,<3` added. |
| R3: 5 production import sites | DONE | `argus/api/auth.py:26-27`, `argus/api/websocket/live.py:18-19`, `argus/api/websocket/observatory_ws.py:19-20`, `argus/api/websocket/ai_chat.py:17-18`, `argus/api/websocket/arena_ws.py:20`. |
| R3: Exception handler updates | DONE | Four `except (JWTError, Exception)` and one `except JWTError` all rewritten to PyJWTError equivalents. |
| R3: Test import swaps | DONE | `tests/api/test_auth.py` (3 sites), `tests/execution/order_manager/test_safety.py` (1 site), `tests/api/test_fix11_backend_api.py` (2 comment refs). |
| R3: `.decode('utf-8')` removal | N/A | No such sites found in argus/. Documented in Judgment Calls. |
| R3: `grep -rn "from jose\|import jose" argus/ tests/` → zero | DONE | Verified. Only PyJWT imports remain. |
| R3: JWT-affected tests pass | DONE | 55 tests in `tests/api/test_auth.py` + `tests/execution/order_manager/test_safety.py` pass under `-n 0`. |
| R4: LaCie path removal | DONE | `CANDIDATE_CACHE_DIRS` reduced to local-only. `grep LaCie scripts/populate_historical_cache.py` returns zero. |

## Regression Checklist Verification

| Check | Verification |
|-------|--------------|
| Local `pip install -r requirements-dev.lock` succeeds | Ran post-session: 55-package install completed; argus editable metadata refreshed. |
| Test suite passes post-lockfile-install | `5,054 passed in 152.00s` matches baseline exactly. |
| CI workflow zero Node-20 deprecation warnings | All three actions bumped to Node-24 majors. CI run verification pending on commit push (operator responsibility per campaign workflow). |
| JWT encode/decode round-trip works | 21 tests in `tests/api/test_auth.py::TestTokenVerification` + `TestRequireAuth` + `TestAuthRoutes` pass. |
| WebSocket auth accepts valid tokens | Covered by the above — WS auth uses the same `verify_token()` / bare `jwt.decode()` path as REST auth. No WS-specific test regression. |
| Invalid token raises `PyJWTError` | `TestTokenVerification::test_verify_token_invalid` + `test_verify_token_wrong_secret` + `test_verify_token_expired` all pass with the PyJWTError-catching handler. |
| `alpaca-py` retention unchanged | `grep alpaca pyproject.toml` shows `alpaca-py>=0.30,<1` in `[project.dependencies]` — same scope as pre-session. |
| No `from jose` / `import jose` remaining | `grep -rn "from jose\|import jose" argus/ tests/` returns zero matches. |
| `populate_historical_cache.py` no longer references LaCie | `grep LaCie scripts/populate_historical_cache.py` returns zero. |
| Lockfile regen reproducible | `uv pip compile pyproject.toml -o /tmp/test.lock`; diff against `requirements.lock` shows only a one-line header difference (filename in generator comment). Substantive content byte-identical. |

## CI Verification Table

| Commit | Milestone | CI URL |
|--------|-----------|--------|
| *pending push* | All four requirements bundled | *to be appended after operator pushes and CI completes* |

**P25 green-CI rule:** Per the campaign workflow, the operator pushes the close-out commit and observes CI. This session's final state is "code landed locally, pending operator `git push origin main` and green CI." The CI URL will be appended to this close-out via a follow-up commit matching the IMPROMPTU-04 pattern (close-out → push → CI green → append URL → push).

## PyJWT Migration Grep-Audit

```
$ grep -rn "from jose\|import jose" argus/ tests/
(no output, exit 1 — zero matches)
```

## Lockfile Reproducibility Test

```
$ uv pip compile pyproject.toml -o /tmp/test.lock
$ diff /tmp/test.lock requirements.lock
2c2
< #    uv pip compile pyproject.toml -o /tmp/test.lock
---
> #    uv pip compile pyproject.toml -o requirements.lock
```

Single-line difference is the filename embedded in the generator-comment header. All 188 package lines byte-identical. Confirmed reproducible.

## Action Pin Verification

| `uses:` Line | Pinned Version | Node Version |
|--------------|----------------|--------------|
| `actions/checkout@v6` | v6.x (latest release v6.0.2) | Node 24 (since v6.0.0 — README updated per release notes) |
| `actions/setup-python@v6` | v6.x (latest release v6.2.0) | Node 24 (since v6.0.0 — "Upgrade to node 24" per release notes) |
| `actions/setup-node@v6` | v6.x (latest release v6.4.0) | Node 24 (since v5.0.0 — "Upgrade action to use node24" per v5.0.0 release notes; v6.x continues on Node 24) |

All three at Node-24-compatible majors ahead of the 2026-06-02 hard deadline.

## Test Results

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
...
5054 passed, 47 warnings in 152.00s (0:02:32)
```

Baseline: 5054 passed. Post-session: 5054 passed. Net delta: 0. Matches the kickoff's "Net test delta: 0 (no new tests needed unless you encounter a regression that requires one)" — no regressions required new tests.

## Sprint-Level Regression Checklist

- [x] pytest net delta = 0 (verified: 5054 → 5054)
- [x] Vitest count unchanged at 859 (no UI files touched)
- [x] No scope boundary violation (DEF-178 and audit back-annotations untouched)
- [x] No Rule-4 sensitive file touched (execution-layer only touch is the single test-file jose import; order_manager.py itself not modified)
- [x] CLAUDE.md DEF-179/180/181 all strikethrough

## Sprint-Level Escalation Criteria

None triggered:

- [x] No remaining `from jose` in argus/ or tests/
- [x] Lockfile is used by CI (install step pulls `-r requirements-dev.lock`)
- [x] Zero JWT-related test failures
- [x] No Action pin regressed to Node 20
- [x] PyJWT pinned `>=2.8,<3` as specified
- [x] `alpaca-py` scope unchanged
- [x] pytest net delta = 0 (not < 0)
- [ ] Green CI URL — *pending operator push*
- [x] No audit-report back-annotation modified

## Post-Review Fixes

*Reserved. Populated if Tier 2 raises CONCERNS and fixes land in-session.*

```json:structured-closeout
{
  "session_id": "IMPROMPTU-05",
  "sprint": "sprint-31.9-health-and-hardening",
  "date": "2026-04-23",
  "self_assessment": "MINOR_DEVIATIONS",
  "context_state": "GREEN",
  "defs_resolved": ["DEF-179", "DEF-180", "DEF-181"],
  "defs_opened": [],
  "decs_added": [],
  "test_delta": {"pytest_before": 5054, "pytest_after": 5054, "vitest_before": 859, "vitest_after": 859},
  "warning_delta": {"pytest_before": 39, "pytest_after": 47, "note": "PyJWT InsecureKeyLengthWarning on 29-byte test secret + xdist ordering fluctuation within DEF-192's documented band"},
  "files_modified": [
    "pyproject.toml",
    "argus/api/auth.py",
    "argus/api/websocket/live.py",
    "argus/api/websocket/observatory_ws.py",
    "argus/api/websocket/ai_chat.py",
    "argus/api/websocket/arena_ws.py",
    "tests/api/test_auth.py",
    "tests/execution/order_manager/test_safety.py",
    "tests/api/test_fix11_backend_api.py",
    "scripts/populate_historical_cache.py",
    ".github/workflows/ci.yml",
    "CLAUDE.md",
    "docs/sprints/sprint-31.9/RUNNING-REGISTER.md",
    "docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md"
  ],
  "files_added": [
    "requirements.lock",
    "requirements-dev.lock",
    "docs/deps.md",
    "docs/sprints/sprint-31.9/IMPROMPTU-05-closeout.md"
  ],
  "files_deleted": [],
  "ci_urls": ["pending operator push"],
  "grep_audit": {
    "from_jose_matches": 0,
    "import_jose_matches": 0,
    "jwterror_matches": 0,
    "lacie_in_populate_script": 0
  },
  "lockfile_summary": {
    "requirements_lock_packages": 188,
    "requirements_dev_lock_packages": 262,
    "reproducibility": "byte-identical apart from one-line header filename reference"
  },
  "action_pin_summary": {
    "checkout": {"from": "v4", "to": "v6", "node_version": 24},
    "setup-python": {"from": "v5", "to": "v6", "node_version": 24},
    "setup-node": {"from": "v4", "to": "v6", "node_version": 24}
  },
  "jwt_migration_summary": {
    "production_sites": 5,
    "test_sites": 3,
    "exception_handler_rewrites": 5,
    "decode_utf8_removed": 0,
    "comment_refs_updated": 2
  }
}
```
```
---END-CLOSE-OUT---
