# Fix Session FIX-18-deps-and-infra: pyproject.toml + infra

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 15
**Files touched:** `../../pyproject.toml`, `../../scripts/resolve_sweep_symbols.py`, `[.env.example:21-25](../../../.env.example#L21-L25)`
**Safety tag:** `weekend-only`
**Theme:** Dependency pinning, CVE-flagged packages (python-jose, passlib), CI absence, and operator-script hardening.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MUST be paused. No open positions. No active alerts.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline (expected for weekend-only)"

# If paper trading is running, STOP before proceeding:
#   ./scripts/stop_live.sh
# Confirm zero open positions at IBKR paper account U24619949 via Command Center.
# This session MAY touch production paths. Do NOT run during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-18): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `../../pyproject.toml`: 10 findings
- `../../scripts/resolve_sweep_symbols.py`: 2 findings
- `[.env.example:21-25](../../../.env.example#L21-L25)`: 1 finding

## Findings to Fix

### Finding 1: `P1-I-M01` [MEDIUM]

**File/line:** [pyproject.toml:20-21](../../../pyproject.toml#L20-L21)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`databento>=0.40.0` and `ib_async>=2.1.0` have no upper version bound.** Both talk to external services with live money on the line. A `pip install -U` by an operator, a fresh venv build, or a CI cache-miss could silently pull a breaking major-version bump (e.g., `databento` 1.x, `ib_async` 3.x) and corrupt live-trading wire-up. Every other runtime dep in the file has a `<N` upper bound.

**Impact:**

> Silent breakage on re-install. Execution-path libs are the worst place for this.

**Suggested fix:**

> Add explicit upper bounds: `"databento>=0.40.0,<1"` and `"ib_async>=2.1.0,<3"`. Verify against current installed versions before pinning.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 2: `P1-I-M02` [MEDIUM]

**File/line:** [pyproject.toml:25](../../../pyproject.toml#L25) + [argus/api/auth.py:26](../../../argus/api/auth.py#L26) and 5 other files
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`python-jose[cryptography]` has CVE-2024-33663 (algorithm confusion) affecting <3.4.0** and the library has had no release since 2022. Used in 6 files for JWT signing/verification on the Command Center API.

**Impact:**

> Security exposure on paper-trading API auth. Low blast radius today (single-user auth, not public-facing), but the dep is a zombie.

**Suggested fix:**

> Migrate from `python-jose` → `PyJWT` (`pyjwt[crypto]>=2.8,<3`). API: `jwt.encode(payload, secret, algorithm="HS256")` / `jwt.decode(...)` — nearly drop-in for the 6 imports. Single-session Phase 3 fix.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 3: `P1-I-M03` [MEDIUM]

**File/line:** [pyproject.toml:26](../../../pyproject.toml#L26) + [argus/api/auth.py](../../../argus/api/auth.py)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`passlib[bcrypt]` is effectively abandoned** (last release 2020) and emits `AttributeError: module 'bcrypt' has no attribute '__about__'` warnings under bcrypt >=4.1. Used for operator-password hashing.

**Impact:**

> Library rot; not a live security issue but a maintenance time-bomb.

**Suggested fix:**

> Replace with direct `bcrypt` calls (`bcrypt.hashpw` / `bcrypt.checkpw`) — the passlib wrapper adds little value for a single scheme. Or adopt `argon2-cffi` if rotating hash scheme.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 4: `P1-I-M04` [MEDIUM]

**File/line:** [pyproject.toml:38](../../../pyproject.toml#L38)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`plotly` is declared under `[project.optional-dependencies].dev`** but imported by 5 production-adjacent files in `argus/backtest/`: `vectorbt_afternoon_momentum.py`, `vectorbt_vwap_reclaim.py`, `vectorbt_orb_scalp.py`, `vectorbt_orb.py`, `report_generator.py`. An operator installing only the runtime set (no `[dev]` extra) will fail `python -m argus.backtest.*` commands documented in [CLAUDE.md:112-120](../../../CLAUDE.md#L112-L120).

**Impact:**

> Broken operator install path.

**Suggested fix:**

> Move `plotly>=5.18,<6` from `dev` → `backtest` extras. (Note: may become moot if P1-E2 M2 adopted to retire `report_generator.py` + vectorbt_*.py files.)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 5: `P1-I-M05` [MEDIUM]

**File/line:** [pyproject.toml:42,46](../../../pyproject.toml#L42)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`vectorbt>=0.28,<1` and `scikit-learn>=1.5,<2` are declared in `[project.optional-dependencies].backtest` but imported nowhere in the codebase.** The `vectorbt_*.py` files are named after the library but use pure NumPy/Pandas — the file header of [vectorbt_orb.py:11](../../../argus/backtest/vectorbt_orb.py#L11) explicitly says *"VectorBT had numba/coverage compatibility issues at install time"*. `scikit-learn` appears in no grep hits.

**Impact:**

> Dead dep declarations — confusing signal to readers and to `pip-audit` scans.

**Suggested fix:**

> Remove both from the `backtest` extra. If scipy (2 files) + numpy + matplotlib (1 file) + plotly (M4 placement) are the real backtest surface, list only those.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 6: `P1-I-L02` [LOW]

**File/line:** [pyproject.toml:14](../../../pyproject.toml#L14)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `python-ulid>=2.2,<3` — library is at v3.x. Minor lag.

**Impact:**

> None (v2→v3 is non-breaking for the `ULID()`/`str` use in the codebase per DEC-026).

**Suggested fix:**

> Bump on next dependency refresh pass.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 7: `P1-I-L03` [LOW]

**File/line:** [pyproject.toml:16](../../../pyproject.toml#L16)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `pyarrow>=14.0,<18` — upper bound excludes 18.x (current latest).

**Impact:**

> None today; future upgrade friction.

**Suggested fix:**

> Bump to `<19` next dependency refresh.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 8: `P1-I-L04` [LOW]

**File/line:** [pyproject.toml:17](../../../pyproject.toml#L17)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `alpaca-py>=0.30,<1` is still in `[project.dependencies]` despite DEC-086 demoting Alpaca to incubator-only. 4 files still import it (alpaca_broker, alpaca_data_service, alpaca_scanner, backtest/data_fetcher).

**Impact:**

> Live mode does not need Alpaca; keeping it in core dependencies perpetuates incubator baggage.

**Suggested fix:**

> Longer-term: move `alpaca-py` to `[project.optional-dependencies].incubator` and gate the 4 imports behind feature detection. Cross-ref PF-07 (flagged for P1-C1 / P1-C2).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 9: `P1-I-L05` [LOW]

**File/line:** [pyproject.toml:45](../../../pyproject.toml#L45)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `matplotlib` is declared under `backtest` extras but imported by exactly one file: [vectorbt_orb.py](../../../argus/backtest/vectorbt_orb.py). If that file is retired (P1-E2 M5 scenario), matplotlib becomes dead.

**Impact:**

> None today.

**Suggested fix:**

> Recheck once P1-E2 decisions land.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 10: `P1-I-C03` [COSMETIC]

**File/line:** [pyproject.toml:54-56](../../../pyproject.toml#L54-L56)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Pytest markers: only `slow` registered. Elsewhere in the codebase `@pytest.mark.asyncio` is used pervasively (auto mode handles it) but no other custom markers are registered — however, the project uses `-n auto` (xdist) without a registered marker, and test-selection tools like `-m "not slow"` could benefit from an `integration` / `unit` split.

**Impact:**

> Minor — no warnings spam today.

**Suggested fix:**

> Consider adding `integration` and `unit` markers for test-selection precision. Optional.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 11: `P1-I-M08` [MEDIUM]

**File/line:** [scripts/resolve_sweep_symbols.py:211-216](../../../scripts/resolve_sweep_symbols.py#L211-L216)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **SQL f-string interpolation for numeric Pydantic fields** (cleanup tracker #2 — confirmed). Today safe because Pydantic enforces `float`/`int`; tomorrow unsafe the moment someone adds a string-typed filter (e.g., "P/E < 30" expression). No defense-in-depth.

**Impact:**

> Defense-in-depth gap in an operator-invoked sweep tool.

**Suggested fix:**

> Convert to DuckDB parameter binding: `service.query("... HAVING AVG(close) >= ? AND AVG(close) <= ? AND AVG(volume) >= ?", [min_price, max_price, min_avg_volume])`, building the clause list and param list in lockstep.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 12: `P1-I-M09` [MEDIUM]

**File/line:** [scripts/resolve_sweep_symbols.py:171](../../../scripts/resolve_sweep_symbols.py#L171)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_count_cache_symbols()` hardcodes `'historical'` DuckDB VIEW name** (cleanup tracker #3 — confirmed). The view name is an internal detail of `HistoricalQueryService`. A rename during the pending cache-consolidation cutover (DEF-161 resolved, but `cache_dir` repoint in `config/historical_query.yaml` is still operator-pending per Sprint 31.85 close-out) could land on a schema where the script silently returns 0.

**Impact:**

> Tight coupling between an operational sweep script and a service implementation detail.

**Suggested fix:**

> Add a public method on `HistoricalQueryService` — e.g., `count_distinct_symbols() -> int` — and call that from the script. Decouples the VIEW name from consumers.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 13: `P1-I-M06` [MEDIUM]

**File/line:** (no file — absence)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **No CI configuration exists.** No `.github/`, no `.gitlab-ci.yml`, no `Jenkinsfile`. All test enforcement is local. The ARGUS test suite is 4,934 pytest + 846 Vitest tests — a CI matrix would catch regressions that the operator could miss during a solo dev workflow, especially under xdist-sensitive configurations (DEF-048, DEF-150) where local runs can be flaky.

**Impact:**

> No external check on test-count regression, lint regression, or Python-version incompatibility. Amplifies the risk of M1-style silent breaks.

**Suggested fix:**

> Minimum viable CI: a single GitHub Actions workflow running `python -m pytest --ignore=tests/test_main.py -n auto -q` + `cd argus/ui && npx vitest run` on push to main, matrixed against the `requires-python = ">=3.11"` minimum. Does not need to run live-broker tests.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 14: `P1-I-M07` [MEDIUM]

**File/line:** (no file — absence)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **No Python lockfile** (no `poetry.lock`, `uv.lock`, `pdm.lock`, `requirements-lock.txt`). Reproducibility depends entirely on the version-range solver producing the same tree across installs. Combined with M1 (unbounded `databento` / `ib_async`), a clean re-install could produce a different execution-path runtime than what was validated in the last sprint. Frontend has `package-lock.json` ✅; Python doesn't.

**Impact:**

> Reproducibility gap. Not acute today, but one bad upgrade will expose it.

**Suggested fix:**

> Commit a `uv.lock` or `requirements.lock` (generated via `uv pip compile pyproject.toml -o requirements.lock`) alongside `pyproject.toml`. Wire CI (when added per M6) to install from the lockfile.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

### Finding 15: `P1-I-C01` [COSMETIC]

**File/line:** [.env.example:21-25](../../../.env.example#L21-L25)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` fallback env-var names** (read by `backtest/data_fetcher.py:714-715, 749-750`) are undocumented. `.env.example` only mentions `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`.

**Impact:**

> Mildly confusing for operators who have legacy alpaca-py environment layouts (APCA_ is the alpaca-py default naming).

**Suggested fix:**

> Add one-line comment in `.env.example` after line 25: `# Alternate names also supported: APCA_API_KEY_ID, APCA_API_SECRET_KEY (alpaca-py default convention)`

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-18-deps-and-infra**`.

## Post-Session Verification

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-18-deps-and-infra** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-18-deps-and-infra**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-18): deps + infra hardening

Addresses audit findings:
- P1-I-M01 [MEDIUM]: 'databento>=0
- P1-I-M02 [MEDIUM]: 'python-jose[cryptography]' has CVE-2024-33663 (algorithm confusion) affecting <3
- P1-I-M03 [MEDIUM]: 'passlib[bcrypt]' is effectively abandoned (last release 2020) and emits 'AttributeError: module 'bcrypt' has no attribu
- P1-I-M04 [MEDIUM]: 'plotly' is declared under '[project
- P1-I-M05 [MEDIUM]: 'vectorbt>=0
- P1-I-L02 [LOW]: 'python-ulid>=2
- P1-I-L03 [LOW]: 'pyarrow>=14
- P1-I-L04 [LOW]: 'alpaca-py>=0
- P1-I-L05 [LOW]: 'matplotlib' is declared under 'backtest' extras but imported by exactly one file: [vectorbt_orb
- P1-I-C03 [COSMETIC]: Pytest markers: only 'slow' registered
- P1-I-M08 [MEDIUM]: SQL f-string interpolation for numeric Pydantic fields (cleanup tracker #2 — confirmed)
- P1-I-M09 [MEDIUM]: '_count_cache_symbols()' hardcodes ''historical'' DuckDB VIEW name (cleanup tracker #3 — confirmed)
- P1-I-M06 [MEDIUM]: No CI configuration exists
- P1-I-M07 [MEDIUM]: No Python lockfile (no 'poetry
- P1-I-C01 [COSMETIC]: 'APCA_API_KEY_ID' and 'APCA_API_SECRET_KEY' fallback env-var names (read by 'backtest/data_fetcher

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions
- [ ] Commit pushed to `main` with the exact message format above
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-18-deps-and-infra**`
