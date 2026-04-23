# Sprint 31.9 IMPROMPTU-05: Dependency & Infrastructure Bundle

> Drafted Phase 1b (post-IMPROMPTU-04 landing). Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Findings addressed:**
- **DEF-180** — Python lockfile via `uv` (no lockfile today; CI installs from version ranges).
- **DEF-181** — Node 20 GitHub Actions deprecation. `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4` all run on Node 20, forced to Node 24 on 2026-06-02 and removed 2026-09-16. **Hard deadline.**
- **DEF-179** — `python-jose` → `PyJWT` migration. 5 import sites in production + 4 in tests. CVE-2024-33663 already mitigated via `>=3.4.0,<4` bound; this removes the abandoned dependency entirely.
- **Non-DEF** — `populate_historical_cache.py:73-74` carries LaCie legacy paths (`/Volumes/LaCie/argus-cache`, `/LaCie/argus-cache`) from the pre-consolidation era. Remove.

**Files touched:**
- `pyproject.toml` (DEF-180 lockfile metadata + DEF-179 dep swap)
- `requirements.lock`, `requirements-dev.lock` (NEW — DEF-180)
- `.github/workflows/ci.yml` (DEF-180 install-from-lockfile + DEF-181 action pin bumps)
- `argus/api/auth.py` (DEF-179 import swap)
- `argus/api/websocket/ai_chat.py` (DEF-179 import swap)
- `argus/api/websocket/observatory_ws.py` (DEF-179 import swap)
- `argus/api/websocket/arena_ws.py` (DEF-179 import swap)
- `argus/api/websocket/live.py` (DEF-179 import swap)
- `tests/api/test_auth.py` (DEF-179 — 3 `from jose import ...` sites)
- `tests/api/test_fix11_backend_api.py` (DEF-179 — 1 comment reference; may or may not need change)
- `tests/execution/order_manager/test_safety.py` (DEF-179 — 1 import)
- `scripts/populate_historical_cache.py` (LaCie cleanup, lines 73-74)
- `docs/deps.md` (NEW — DEF-180 lockfile regen recipe)

**Safety tag:** `safe-during-trading` — no touches to running code paths. Paper trading can continue throughout.

**Theme:** Three dependency/infrastructure hygiene items that must land together because CI validates each. DEF-180 lockfile lands first; DEF-181 action pins land next and exercise the new lockfile on CI; DEF-179 PyJWT swap lands third and produces the first green CI run on the cleaned dep tree.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MAY be running — this session is safe-during-trading.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — also fine"
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline:** Post-IMPROMPTU-04 count (5,039 + A1 regression tests + 4 ≈ 5,043–5,046 pytest). 859 Vitest unchanged. Obtain precise count from the IMPROMPTU-04 close-out file.

### 3. Branch & workspace

```bash
git checkout main
git pull --ff-only
git log --oneline -5
# Expected: IMPROMPTU-04 final commit at HEAD.
git status
# Expected: "nothing to commit, working tree clean"
```

### 4. Verify `uv` availability

```bash
# If uv is not installed, install it first:
which uv || pip install uv
uv --version
```

`uv` is the recommended Python lockfile tool per DEF-180. If you prefer `pip-tools` or `poetry`, pause and confirm with the operator — switching locks costs session time and may blow scope.

## Pre-Flight Context Reading

1. Read these files:
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-05"
   - `CLAUDE.md` DEF-179, DEF-180, DEF-181 entries
   - `pyproject.toml` — full file; note `[project.dependencies]` version ranges
   - `.github/workflows/ci.yml` — full file; note action pins + install step
   - `argus/api/auth.py` — see how `python-jose` is used; understand `JWTError` vs `PyJWTError` semantic equivalence
   - `scripts/populate_historical_cache.py` lines 65–80 — see the `CANDIDATE_CACHE_DIRS` list context
   - FIX-18 close-out at `docs/sprints/sprint-31.9/FIX-18-closeout.md` — provides context for why version-range-only dependencies were left in place (explicit deferral of lockfile choice)

2. Verify the `python-jose` → `PyJWT` API differences:
   - `jwt.encode(payload, secret, algorithm="HS256")` returns `str` directly in PyJWT 2.x (no `.decode()` needed)
   - `jwt.decode(...)` raises `jwt.PyJWTError` subclasses (e.g., `ExpiredSignatureError`, `InvalidTokenError`) instead of `jose.JWTError`
   - PyJWT's exception hierarchy: `PyJWTError` is the base; `InvalidTokenError`, `ExpiredSignatureError`, `DecodeError` all inherit from it
   - Both libraries support HS256 + HS384 + HS512 + RS256 identically for the subset argus uses

3. Check CI cost for the session. Running CI on every intermediate commit burns minutes. Plan to push in 1–2 commits (lockfile-first, then pins-and-migration together) rather than 4 commits (one per requirement). Cost-efficient without sacrificing atomicity: lockfile commit validates independently, then bundled commit validates end-to-end.

## Objective

Land the Python lockfile infrastructure (DEF-180), update GitHub Actions pins to
Node-24-compatible versions (DEF-181), migrate JWT handling from `python-jose`
to `PyJWT` (DEF-179), and remove the dead LaCie cache path references. Three
CI-green milestones gate these.

## Requirements

### Requirement 1: DEF-180 — Python lockfile via `uv`

1. Generate the primary lockfile:
   ```bash
   uv pip compile pyproject.toml -o requirements.lock
   ```
2. Generate the dev/test lockfile with all extras:
   ```bash
   uv pip compile --extra dev --extra backtest pyproject.toml -o requirements-dev.lock
   ```
   Check which extras are actually defined in `pyproject.toml` and include all of them (likely `dev`, `backtest`, and possibly `intelligence` or similar). Do NOT include experimental `incubator` extra if present — that pulls `alpaca-py` which is slated for retirement (DEF-178/183).
3. Update `.github/workflows/ci.yml` to install from the lockfile. Change the current pattern (likely `pip install -e ".[dev]"` or similar) to:
   ```yaml
   - name: Install dependencies
     run: |
       python -m pip install --upgrade pip
       pip install -r requirements-dev.lock
       pip install -e . --no-deps
   ```
   The `--no-deps` on the editable install is important: we want the lockfile to be authoritative; the editable install just registers the argus package path.
4. Create `docs/deps.md` (NEW) with:
   - Regen recipe (`uv pip compile ...` commands)
   - When to regen (on `pyproject.toml` dep changes)
   - How to install locally (`pip install -r requirements-dev.lock`)
   - Cross-ref to `CLAUDE.md` DEF-180 for historical context
5. Verify the local install works: `pip install -r requirements-dev.lock && python -m pytest --ignore=tests/test_main.py -n auto -q` must pass.

### Requirement 2: DEF-181 — Node 20 action pin bumps

1. In `.github/workflows/ci.yml`, update each action to its Node-24-compatible successor. As of Phase 1b drafting (April 2026):
   - `actions/checkout@v4` → `actions/checkout@v5` (Node 24 support)
   - `actions/setup-python@v5` → `actions/setup-python@v6` if published; else stay on v5 and note the successor in a comment (v5 is the current latest as of 2026-04-23 and supports Node 24 natively)
   - `actions/setup-node@v4` → `actions/setup-node@v5` if published; same fallback logic
2. Verify each successor is published at https://github.com/actions/{name}/releases before pinning. If a successor is not yet published, pin to the latest tag + add a comment `# TODO DEF-181: bump to Node-24-compatible successor when published, before 2026-06-02` and log this partial resolution in the close-out.
3. Run the updated workflow to confirm no deprecation warnings appear on the Node-20 front. Push to a test branch or use `act` locally if available; otherwise push to main and observe the CI run.

### Requirement 3: DEF-179 — `python-jose` → `PyJWT` migration

1. Update `pyproject.toml` — remove `python-jose[cryptography]>=3.4.0,<4` from `[project.dependencies]`, add `PyJWT>=2.8,<3`. Regenerate the lockfiles (Requirement 1).
2. Swap imports at each of 5 production sites:
   - `argus/api/auth.py:26` — `from jose import JWTError, jwt` → `import jwt` + `from jwt import PyJWTError`
   - `argus/api/websocket/ai_chat.py:17` — same pattern
   - `argus/api/websocket/observatory_ws.py:19` — same
   - `argus/api/websocket/arena_ws.py:20` — currently imports only `jwt` (no `JWTError`); change to `import jwt`
   - `argus/api/websocket/live.py:18` — same pattern as auth.py
3. Swap test imports at 3 sites in `tests/api/test_auth.py` (lines 143, 308, 360). All use `from jose import jwt` or `from jose import jwt as jose_jwt` — change to `import jwt` / `import jwt as jwt_module`.
4. One test in `tests/execution/order_manager/test_safety.py:511` does `from jose import jwt` — change to `import jwt`.
5. `tests/api/test_fix11_backend_api.py:187` has a comment reference to jose; update to reference `jwt` (PyJWT) for accuracy.
6. Rewrite any exception handlers using `JWTError` → `PyJWTError`. The full list should be discoverable via:
   ```bash
   grep -rn "JWTError\|jose\." argus/ tests/ 2>/dev/null
   ```
   Each match must be converted or explicitly justified.
7. Remove `.decode('utf-8')` from any `jwt.encode(...)` call. In PyJWT 2.x, `encode()` returns `str`; in python-jose, it returned `bytes`. If argus has any pattern like:
   ```python
   token = jwt.encode(payload, secret).decode('utf-8')
   ```
   change to:
   ```python
   token = jwt.encode(payload, secret)
   ```
8. Run `tests/api/` + `tests/execution/order_manager/test_safety.py` specifically after the swap. All existing tests must pass.

### Requirement 4: LaCie cache path removal

1. In `scripts/populate_historical_cache.py`, remove the `/Volumes/LaCie/argus-cache` and `/LaCie/argus-cache` entries from `CANDIDATE_CACHE_DIRS` (lines 73-74). The consolidated cache lives at `data/databento_cache_consolidated/` per DEC-382-era consolidation; LaCie was the pre-2026 external-drive location.
2. Retain any other entries in the list if they reference relative paths inside the repo or `~/argus-cache`-style home-dir paths (operator preference may vary).
3. Add a brief comment explaining the removal in the commit.

## Constraints

- **Do NOT modify** any argus runtime code paths other than JWT import/decode/encode sites (Requirement 3). In particular, do NOT change JWT token structure, claim keys, TTL logic, or auth endpoint semantics.
- **Do NOT add** new dependencies during the lockfile generation beyond what's already in `pyproject.toml`. The lockfile resolves what's already declared; it does not introduce new direct deps.
- **Do NOT upgrade** any dependency version beyond a Major.Minor compatible with the declared range. Running `uv pip compile` will pick the latest valid resolution — that's fine — but do not manually edit lockfile entries to force upgrades outside the declared range.
- **Do NOT include** `alpaca-py` in the dev lockfile. If it's currently in `[project.dependencies]`, leave it there for this session (DEF-178 handles the move to `[incubator]` extra); just don't expand its footprint.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- **Do NOT bundle** DEF-178 (alpaca-py → incubator) into this session. That's named-horizon-deferred to post-31.9-alpaca-retirement.
- **Do NOT touch** any audit-2026-04-21 doc back-annotations.
- Work directly on `main` — matches campaign pattern.

## Test Targets

After implementation:
- All existing tests pass
- Net test delta: 0 (no new tests needed unless you encounter a regression that requires one)
- Test command (scoped):
  ```bash
  python -m pytest tests/api/ tests/execution/order_manager/test_safety.py -xvs -n 0
  ```
- Test command (full suite, at close-out):
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```
- **CI verification required (P25 rule):** three successive green CI runs:
  1. After lockfile commit (validates lockfile install works on CI)
  2. After action-pin commit (validates no Node-20 warnings)
  3. After PyJWT swap commit (validates migration + final state)

  If you commit requirements as a single batch, only one CI run is required but the post-commit greenness must be clean.

## Definition of Done

- [ ] All 4 requirements implemented
- [ ] All existing tests pass
- [ ] `requirements.lock` and `requirements-dev.lock` created, committed, and referenced from `.github/workflows/ci.yml`
- [ ] `docs/deps.md` created with regen recipe
- [ ] All 5 production + 4 test `from jose` imports swapped to PyJWT; `.decode()` calls removed where applicable
- [ ] GitHub Actions pins updated; no Node-20 deprecation warnings in CI output
- [ ] LaCie paths removed from `populate_historical_cache.py`
- [ ] `CLAUDE.md` DEF-179, DEF-180, DEF-181 entries all updated with strikethrough + commit SHA
- [ ] `RUNNING-REGISTER.md` updated: DEF-179/180/181 moved to "Resolved this campaign" table with IMPROMPTU-05 owner + commit SHA
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` Stage 9B row for IMPROMPTU-05 marked CLEAR
- [ ] Close-out report written to `docs/sprints/sprint-31.9/IMPROMPTU-05-closeout.md`
- [ ] Tier 2 standard review completed; review report at `docs/sprints/sprint-31.9/IMPROMPTU-05-review.md`
- [ ] Green CI run URL cited in the close-out (P25 rule)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Local `pip install -r requirements-dev.lock` succeeds on a clean venv | Run in a Docker or venv sandbox |
| Test suite passes post-install from lockfile | `pytest` runs with same count |
| CI workflow runs with zero Node-20 deprecation warnings | Check CI log output |
| JWT token encode/decode round-trip works | `tests/api/test_auth.py` suite passes |
| WebSocket auth still accepts valid tokens | `tests/api/` WebSocket tests pass |
| Invalid token raises `PyJWTError` (not `JWTError`) | Specific test in `test_auth.py` |
| `alpaca-py` retention unchanged | `grep alpaca pyproject.toml` still shows it at the same scope |
| No `from jose` imports anywhere in argus/ or tests/ | `grep -rn "from jose\|import jose" argus/ tests/` returns zero |
| `populate_historical_cache.py` no longer references LaCie | `grep LaCie scripts/populate_historical_cache.py` returns zero |
| Lockfile regen recipe works | Run the `uv pip compile` commands from `docs/deps.md` and confirm output matches committed lockfiles |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-31.9/IMPROMPTU-05-closeout.md`

Include in the close-out:
1. **CI verification table:** list each green CI run URL corresponding to each requirement's landing commit.
2. **PyJWT migration grep-audit:** confirm `grep -rn "from jose\|import jose" argus/ tests/` returns zero matches.
3. **Lockfile reproducibility test:** confirm regen from `pyproject.toml` produces byte-identical lockfiles (or document any drift and why it's acceptable).
4. **Action pin verification:** list each `uses:` line in `ci.yml` and note which Node version it runs on, confirming all are Node 24 compatible.
5. **Green CI run URL for the final commit SHA** (P25 rule).

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. Review context: this kickoff file + `CLAUDE.md` DEF-179/180/181 entries
2. Close-out report path: `docs/sprints/sprint-31.9/IMPROMPTU-05-closeout.md`
3. Diff range: `git diff HEAD~N` where N = number of commits in this session
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified:
   - Any `argus/` runtime file OTHER than the 5 JWT import sites
   - `argus/execution/*.py` (except the JWT-test file)
   - Any `workflow/` submodule file
   - Any audit-2026-04-21 doc back-annotation
   - `config/experiments.yaml` (unrelated to this scope)

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-05-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify the lockfile is authoritative.** `.github/workflows/ci.yml` must install from the lockfile with `--no-deps` on the editable install. If CI still runs `pip install -e ".[dev]"` or similar, the lockfile isn't being used.
2. **Verify JWT migration is complete.** `grep -rn "from jose\|import jose" argus/ tests/` must return zero. Any remaining `JWTError` exception handler must have been converted to `PyJWTError`.
3. **Verify Node 24 readiness.** Every `uses: actions/*` line must be at a version that supports Node 24. If any action isn't yet Node-24-ready, the close-out must document the TODO with a concrete follow-up plan (deadline 2026-06-02).
4. **Verify no token-format regression.** The JWT payload structure, claim keys, TTL, and issuer must be identical pre- vs post-migration. Read the diff around each `jwt.encode(...)` call and confirm only the library call signature changed, not the payload.
5. **Verify `alpaca-py` is untouched.** DEF-178 is explicitly out of scope.
6. **Verify lockfile regen is reproducible.** Run `uv pip compile pyproject.toml -o /tmp/test.lock` and diff against the committed `requirements.lock`. They should match byte-for-byte (modulo timestamp comments if any). Any drift = reproducibility concern.
7. **Verify green CI URL exists in close-out for the final commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0 (no new tests expected)
- Vitest count unchanged at 859 + IMPROMPTU-04 delta (this session touches no UI)
- No scope boundary violation
- No Rule-4 sensitive file touched
- CLAUDE.md DEF-179/180/181 all strikethrough

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE verdict if ANY of:
- Any remaining `from jose` import in `argus/` or `tests/` after the session
- Lockfile not actually used by CI (install step still pulls from ranges)
- Any JWT-related test failure
- Action pin bumped to a version that runs on Node 20 (regression)
- PyJWT version pinned outside `>=2.8,<3` range without explicit justification
- `alpaca-py` scope change (touched this session)
- pytest net delta < 0
- Green CI URL missing or CI red
- Audit-report back-annotation modified (out of scope)

## Post-Review Fix Documentation

Standard protocol per the implementation-prompt template. If CONCERNS are
raised and fixed in-session, update the close-out's "Post-Review Fixes"
section and the review's "Post-Review Resolution" section.

## Operator Handoff

Display to the operator:
1. Close-out markdown block (for Work Journal paste)
2. Review markdown block (for Work Journal paste)
3. **Lockfile summary:** total dep count in `requirements-dev.lock`; reproducibility confirmed Y/N
4. **Action pin summary:** each action + its new version + Node compatibility
5. **JWT migration summary:** 5 production + 4 test sites migrated; zero remaining `jose` imports
6. Green CI URL
7. One-line summary: `Session IMPROMPTU-05 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {pre} → {post}. CI: {URL}. DEFs closed: DEF-179, DEF-180, DEF-181.`
