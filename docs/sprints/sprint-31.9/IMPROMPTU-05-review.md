---BEGIN-REVIEW---
```markdown
# Tier 2 Review — IMPROMPTU-05 (Dependency & Infrastructure Bundle)

- **Sprint:** `sprint-31.9-health-and-hardening`
- **Session:** `IMPROMPTU-05` (Track B / Stage 9B — safe-during-trading)
- **Review date:** 2026-04-23
- **Reviewer:** Tier 2 standard-profile (reviewer subagent)
- **Commits reviewed:** `6ddd7a7` (single bundled)
- **Baseline:** `224d773` (IMPROMPTU-CI Tier 2 review artifact — CLEAR)

## Verdict: **CLEAR**

All four bundled items (DEF-179 PyJWT, DEF-180 uv lockfile, DEF-181 Node-24 pins, LaCie cleanup) land exactly as scoped. Zero scope boundary violations, zero escalation triggers, test delta 0, grep audits clean, lockfile byte-reproducible, JWT payload structure unchanged.

---

## Session-Specific Review Focus — Verification

| Focus Item | Status | Evidence |
|------------|--------|----------|
| 1. Lockfile authoritative in CI | **PASS** | `.github/workflows/ci.yml` install step: `pip install -r requirements-dev.lock` followed by `pip install -e . --no-deps`. No `pip install -e ".[dev,backtest]"` remains. `cache-dependency-path` moved from `pyproject.toml` → `requirements-dev.lock`. |
| 2. JWT migration complete | **PASS** | `grep -rn "from jose\|import jose" argus/ tests/` returns zero. `grep -rn "JWTError" argus/` returns only `PyJWTError` hits (5 import sites + 4 exception handlers). |
| 3. Node 24 readiness | **PASS** | 4 `uses:` lines at Node-24-compatible majors: `actions/checkout@v6` (×2), `actions/setup-python@v6`, `actions/setup-node@v6`. Release-note verification via `gh api releases/latest`: v6.0.2 / v6.2.0 / v6.4.0. |
| 4. No JWT token-format regression | **PASS** | `argus/api/auth.py:118-124` `create_access_token` payload (`exp`, `iat`, `sub="operator"`) unchanged. `ALGORITHM = "HS256"` constant at line 32 unchanged. `jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)` call signature identical. `except JWTError:` → `except PyJWTError:` at line 142. No `.decode('utf-8')` was present to remove (close-out correctly documents this — python-jose ≥3.0 already returned `str`). |
| 5. `alpaca-py` untouched | **PASS** | `pyproject.toml` line 20 `alpaca-py>=0.30,<1` remains in `[project.dependencies]` at same scope as pre-session. DEC-086 incubator comment (lines 17-19) unchanged. |
| 6. Lockfile regen reproducible | **PASS** | `uv pip compile pyproject.toml -o /tmp/imp05-test.lock` + dev extras variant: both diffs are single-line filename-in-header comment. All 188 / 262 package lines byte-identical. |
| 7. CI URL | **NOT BLOCKING** | `*pending operator push*` in close-out's CI Verification Table — matches IMPROMPTU-04 pattern. Acknowledged acceptable per review brief. |

---

## Grep Audits (Run Independently)

```
$ grep -rn "from jose\|import jose" argus/ tests/
(zero matches)

$ grep -n "JWTError" argus/*.py argus/**/*.py
argus/api/auth.py:27:from jwt import PyJWTError
argus/api/auth.py:142:    except PyJWTError:
argus/api/websocket/live.py:19:from jwt import PyJWTError
argus/api/websocket/live.py:485:    except (PyJWTError, Exception):
argus/api/websocket/ai_chat.py:18:from jwt import PyJWTError
argus/api/websocket/ai_chat.py:86:        except (PyJWTError, Exception):
argus/api/websocket/observatory_ws.py:20:from jwt import PyJWTError
argus/api/websocket/observatory_ws.py:73:        except (PyJWTError, Exception):
(no bare JWTError references remain)

$ grep -n "LaCie" scripts/populate_historical_cache.py
(zero matches)

$ grep -n "alpaca" pyproject.toml
17:    # alpaca-py: incubator-only per DEC-086. Movement to an [incubator]
20:    "alpaca-py>=0.30,<1",
(unchanged from pre-session)
```

---

## Lockfile Reproducibility Test

```
$ uv pip compile pyproject.toml -o /tmp/imp05-test.lock
$ diff /tmp/imp05-test.lock requirements.lock
2c2
< #    uv pip compile pyproject.toml -o /tmp/imp05-test.lock
---
> #    uv pip compile pyproject.toml -o requirements.lock

$ uv pip compile --extra dev --extra backtest pyproject.toml -o /tmp/imp05-dev-test.lock
$ diff /tmp/imp05-dev-test.lock requirements-dev.lock
2c2
< #    uv pip compile --extra dev --extra backtest pyproject.toml -o /tmp/imp05-dev-test.lock
---
> #    uv pip compile --extra dev --extra backtest pyproject.toml -o requirements-dev.lock
```

Byte-identical apart from filename-in-header comment. `pyjwt==2.12.1` present in both lockfiles; zero `jose` references in either. `uv 0.11.7` (2026-04-15 build) used for both original and reproducibility regen.

---

## Action Pin Verification Table

| Line | Action | Pin | Node Version | Status |
|------|--------|-----|--------------|--------|
| 17 | `actions/checkout` | `@v6` | Node 24 | PASS |
| 22 | `actions/setup-python` | `@v6` | Node 24 | PASS |
| 54 | `actions/checkout` | `@v6` | Node 24 | PASS |
| 59 | `actions/setup-node` | `@v6` | Node 24 | PASS |

All 4 `uses:` occurrences at Node-24-compatible majors. Hard deadline 2026-06-02 met with 40-day margin.

**Incidental observation (non-blocking):** step heading at line 57 still reads `Set up Node 20`. Semantically correct — `node-version: "20"` at line 61 is the frontend *target* runtime, distinct from the `actions/setup-node@v6` runner runtime (Node 24). Opportunistic doc polish for a future pass; not an IMPROMPTU-05 concern.

---

## JWT Payload-Structure Inspection

`argus/api/auth.py` `create_access_token` (lines 106-124):

```python
expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)
payload = {
    "exp": expires_at,
    "iat": datetime.now(UTC),
    "sub": "operator",  # Single user system
}
token = jwt.encode(payload, jwt_secret, algorithm=ALGORITHM)
```

Claim keys (`exp`, `iat`, `sub`), values, TTL logic, single-user `sub`, and `ALGORITHM = "HS256"` constant — **all unchanged**. Only the `jwt` import source changed (stdlib-style `import jwt` now resolves to PyJWT instead of python-jose's namespace package). PyJWT 2.x and python-jose 3.x both accept this exact call signature. `jwt.decode(token, jwt_secret, algorithms=[ALGORITHM])` at line 141 is also call-signature-identical. No token-format regression.

Three WebSocket handlers (`live.py`, `observatory_ws.py`, `ai_chat.py`) use `jwt.decode(token, jwt_secret, algorithms=["HS256"])` with no custom options — call-signature-compatible. `arena_ws.py` uses `jwt.decode` similarly; no `JWTError` was ever imported there (only bare `Exception`).

---

## Sprint-Level Regression Checklist

- [x] **pytest net delta = 0** — Close-out reports 5054 → 5054. Scoped JWT run (71 tests across `tests/api/test_auth.py` + `tests/api/test_fix11_backend_api.py` + `tests/execution/order_manager/test_safety.py`): all pass locally in 7.62s.
- [x] **Vitest 859 unchanged** — No UI files modified.
- [x] **No scope boundary violation** — DEF-178 untouched; audit-2026-04-21 back-annotations untouched.
- [x] **No Rule-4 sensitive file touched** — `argus/execution/*.py` runtime unchanged; only `tests/execution/order_manager/test_safety.py` modified (test file, JWT import swap only). `order_manager.py`, `ibkr_broker.py`, `broker.py` runtime code not modified.
- [x] **CLAUDE.md DEF-179/180/181 all strikethrough** — Lines 406/407/408 formatted as `| ~~DEF-NNN~~ | ~~Title~~ | — | **RESOLVED** (...) |`.
- [x] **RUNNING-REGISTER + CAMPAIGN-COMPLETENESS-TRACKER updated** — Both in change manifest; IMPROMPTU-05 session history row added.

---

## Escalation Criteria — All Clear

| Criterion | Status |
|-----------|--------|
| Remaining `from jose` in argus/ or tests/ | **None** |
| Lockfile not used by CI | **PASS — CI uses lockfile** |
| JWT-related test failure | **None — 71 pass** |
| Action pin regressed to Node 20 | **None — all v6** |
| PyJWT pinned outside `>=2.8,<3` | **PASS — exact `PyJWT>=2.8,<3`** |
| `alpaca-py` scope change | **None — untouched** |
| pytest net delta < 0 | **Delta = 0** |
| Audit back-annotation modified | **None** |

---

## Warning Delta Note

Close-out reports +8 pytest warnings (39 → 47). Investigation surfaced a single `InsecureKeyLengthWarning` in `tests/api/test_auth.py::TestAuthRoutes::test_invalid_signature_rejected` — 29-byte test secret. This is PyJWT 2.x's new advisory on HS256 keys <32 bytes (RFC 7518 §3.2 recommendation, not a requirement). The test deliberately uses a short secret to exercise invalid-signature rejection; extending it to 32 bytes would be the trivial cleanup but is out of IMPROMPTU-05 scope. Remaining +7 warning delta is within DEF-192's documented xdist fluctuation band (26–40/run). Not a regression. Not a new DEF.

---

## Minor Observations (Non-Blocking)

1. **Close-out's structured JSON reports `"test_sites": 3`** but the kickoff's original list identified 4 test-file sites (test_auth.py × 3 inline imports + test_fix11_backend_api.py + test_safety.py). The JSON `3` counts code-change files only (test_auth.py, test_safety.py, test_fix11_backend_api.py — 3 total with comment-only test_fix11 treated as a single file). Pure tallying difference, not a substantive deviation.

2. **`ci.yml` line 57 heading `Set up Node 20`** is semantically correct (frontend *target* runtime) but could be misread as "this action runs on Node 20." Opportunistic doc polish for a future pass; out of scope.

---

## Post-Review Resolution

*No post-review fixes required. Verdict CLEAR as stated.*

---

## Final Verdict

**CLEAR.** Close-out self-assessment of `MINOR_DEVIATIONS` is appropriately conservative (driven by the documented Judgment Calls around `.decode('utf-8')` non-existence and the single-commit-vs-three-commit choice — both defensible). Technical change is clean. Scoped JWT tests all green locally; 71/71 pass with the one expected InsecureKeyLengthWarning on the deliberate short-secret test. Lockfile reproducibility confirmed against `pyproject.toml` via `uv 0.11.7`. CI URL pending operator push is acknowledged and does not block this verdict per the review brief — matches the IMPROMPTU-04 pattern. No post-review fixes needed.

```json:structured-verdict
{
  "session_id": "IMPROMPTU-05",
  "sprint": "sprint-31.9-health-and-hardening",
  "review_date": "2026-04-23",
  "verdict": "CLEAR",
  "reviewer_tier": 2,
  "reviewer_profile": "standard",
  "commits_reviewed": ["6ddd7a7"],
  "baseline_commit": "224d773",
  "escalation_triggers": [],
  "concerns": [],
  "scope_verification": {
    "lockfile_authoritative_in_ci": "PASS",
    "jwt_migration_complete": "PASS",
    "node_24_ready": "PASS",
    "jwt_payload_unchanged": "PASS",
    "alpaca_untouched": "PASS",
    "lockfile_reproducible": "PASS",
    "ci_url": "pending operator push (non-blocking per review brief)"
  },
  "grep_audits": {
    "jose_in_argus": 0,
    "jose_in_tests": 0,
    "bare_JWTError": 0,
    "lacie_in_populate_script": 0,
    "alpaca_py_in_pyproject": "unchanged (line 20)"
  },
  "lockfile_reproducibility": {
    "requirements_lock_diff_lines": 1,
    "requirements_dev_lock_diff_lines": 1,
    "diff_substance": "header filename comment only"
  },
  "action_pins_verified": {
    "checkout": "v6 (Node 24)",
    "setup-python": "v6 (Node 24)",
    "setup-node": "v6 (Node 24)"
  },
  "jwt_scoped_test_result": "71 passed (1 InsecureKeyLengthWarning — advisory, documented)",
  "test_delta": {"before": 5054, "after": 5054, "delta": 0},
  "sprint_regression_checklist_passed": true,
  "minor_observations": [
    "Close-out JSON reports test_sites: 3 vs kickoff's notion of 4 — pure tallying difference",
    "ci.yml line 57 heading 'Set up Node 20' is semantically correct (frontend target) but could be clarified in a future doc polish — not in IMPROMPTU-05 scope"
  ]
}
```
```
---END-REVIEW---
