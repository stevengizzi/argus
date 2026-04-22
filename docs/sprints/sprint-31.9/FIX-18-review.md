# FIX-18-deps-and-infra — Tier 2 Review

> Independent review per `workflow/claude/skills/review.md`. Read-only; no source files were modified. Findings below.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-18-deps-and-infra (commit 7aabb96)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | 9 files changed. Scope files touched: pyproject.toml, scripts/resolve_sweep_symbols.py, .env.example, .github/workflows/ci.yml (new). Expected-scope support files: tests/scripts/test_resolve_sweep_symbols.py (+5 regression tests), CLAUDE.md (DEF-178/179/180 additions, appended rows only), audit docs (back-annotations), FIX-18-closeout.md (standard Phase 3 output). Zero Rule-4 sensitive files touched — verified via `git show 7aabb96 --name-only`: no argus/api/auth.py, no argus/api/websocket/*.py. |
| Close-Out Accuracy | PASS | Change manifest mirrors diff exactly. 4 judgment calls (M-02 option c, M-03 no-call-site impact, M-06 single-file CI, M-09 via existing public API) all traceable to the diff. Self-assessment MINOR_DEVIATIONS is honest — 2 deliberate deferrals (M-07 → DEF-180; L-04 → DEF-178) plus M-02 option-c choice over audit's suggested full PyJWT swap. |
| Test Health | PASS | Full suite reran locally: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q` → 4,989 passed + 1 failed (63.55s). The 1 failure is `tests/sprint_runner/test_notifications.py::test_check_reminder_sends_after_interval` — this is DEF-150, the known time-of-day arithmetic flake (`(minute - 2) % 60` breaks when minute ∈ {0,1}). Test ran at 13:02 ET — exactly the first-2-minutes-of-the-hour danger window. Total count (4,989 + 1 DEF-150 = 4,990) matches close-out's stated post-session count; net delta +5 from the 4,985 baseline is consistent with exactly 5 new regression tests added to tests/scripts/test_resolve_sweep_symbols.py (verified via `git show 7aabb96 -- tests/scripts/test_resolve_sweep_symbols.py | grep -c "^+def test_"` → 5). New tests are substantive (not tautological) — the grep-guard test actually reads the script source and asserts the three banned f-string patterns are absent; the M-09 tests use a MagicMock that would fail if the script regressed to calling `service.query("... FROM historical ...")`. |
| Regression Checklist | PASS | All 8 campaign-level checks pass — see table below. |
| Architectural Compliance | PASS | M-08 parametrization lockstep verified at scripts/resolve_sweep_symbols.py:215-236: (a) no f-string interpolates filter values into SQL text (only static HAVING-clause body is f-string-joined), (b) each of 3 conditionals appends exactly one placeholder AND one param, (c) params list order `[start_date, end_date, *having_params]` matches the `WHERE date >= ? AND date <= ?` + appended HAVING placeholder order. M-09 uses the service's existing `get_date_coverage()` public API (service returns `{"symbol_count": int, ...}` at argus/data/historical_query_service.py:451) — structurally cleaner than adding a new method, zero service-side edits. M-02 option c is defensible: PyPI query confirms python-jose 3.4.0 released 2025-02-18 and 3.5.0 shipped subsequently; OSV database confirms CVE-2024-33663 (GHSA-6c5p-j8vq-pqhj / PYSEC-2024-232) is fixed in 3.4.0. M-03 passlib-removal: `grep -rn "passlib" argus/` returns zero matches; `argus/api/auth.py:23` imports bcrypt directly. CI YAML parses cleanly (`yaml.safe_load` round-trip); 2 jobs (pytest, vitest); `pip install -e ".[dev,backtest]"` valid post-session (both extras present in pyproject.toml); `cd argus/ui && npm ci && npm run test` matches argus/ui/package.json `"test": "vitest run"`. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding (all 15 findings are MEDIUM/LOW/COSMETIC); pytest net delta positive (+5 new tests, 0 regressions); no scope boundary violation; no Rule-4 sensitive path touched; no unexpected failure surface (the 1 failing test is DEF-150, not a new regression); 15/15 audit rows back-annotated in both `p1-i-dependencies.md` and `phase-2-review.csv`. |

### Detailed Verification of Scrutiny Items

1. **M-02 option (c) — python-jose 3.4.0/3.5.0 exist + CVE fixed.** Verified against PyPI and OSV:
   - `pip index versions python-jose` → `Available versions: 3.5.0, 3.4.0, 3.3.0, ...`
   - PyPI JSON API: python-jose 3.4.0 `upload_time: 2025-02-18T17:26:40` (contradicts audit's "no release since 2022" claim).
   - OSV query for python-jose PyPI package: CVE-2024-33663 (GHSA-6c5p-j8vq-pqhj) has `fixed: 3.4.0`.
   The `>=3.4.0,<4` lower-bound bump correctly excludes the CVE. DEF-179 captures the full PyJWT migration intent. PASS.

2. **M-03 — passlib is a ghost dep; no call-site changes needed.** Grep-verified: `grep -rn "passlib" argus/` returns zero matches in production code. `argus/api/auth.py:23` reads `import bcrypt` directly. Removal of `passlib[bcrypt]>=1.7,<2` and addition of `bcrypt>=4.1,<6` as a direct dep is a clean swap — previously bcrypt was pulled transitively via passlib's `[bcrypt]` extra; now it's an explicit constraint. `>=4.1` floor matches the finding's stated warning-fix version. PASS.

3. **M-09 — `_count_cache_symbols()` decoupled via existing public API.** Read scripts/resolve_sweep_symbols.py:172-177: the body now reads `int(service.get_date_coverage().get("symbol_count", 0))`. Verified argus/data/historical_query_service.py:413-455: `get_date_coverage()` is a public method that (when `symbol=None`) executes `SELECT COUNT(DISTINCT symbol) AS symbol_count, ... FROM historical` and returns a dict keyed `"symbol_count"`. Functionally equivalent to the removed `SELECT COUNT(DISTINCT symbol) AS n FROM historical` query in the script, and the VIEW-name coupling now lives inside the service (its rightful owner). Note: `_apply_static_filters()` at line 230 still references `FROM historical` directly, but that was NOT in the M-09 finding's cited scope (line 171, the count function). Sibling `_apply_static_filters` coupling could be tracked opportunistically if the VIEW name is ever renamed, but it's not a FIX-18 regression. PASS.

4. **M-08 — parametrization is lockstep and injection-safe.** Read scripts/resolve_sweep_symbols.py:211-236:
   - **No f-string interpolates a filter value:** The 3 HAVING conditionals use string literals `"AVG(close) >= ?"` / `"AVG(close) <= ?"` / `"AVG(volume) >= ?"`. Only the static join into `having_sql` is an f-string, and it contains only bind markers.
   - **Param count equals placeholder count in every branch:** Each conditional block appends exactly 1 placeholder AND 1 param. With start_date + end_date always contributing 2 placeholders / 2 params in the WHERE clause, total placeholders = 2 + (0-3 depending on filters) = total params.
   - **Order matches:** Params list `[start_date, end_date, *having_params]` preserves the WHERE-first-then-HAVING order; `having_params` is appended in the same order as `having_clauses`.
   - Grep-guard test `test_resolve_sweep_symbols_script_has_no_fstring_sql_injection` reads the script source and fails on any reintroduction of `f"AVG(close) >= {`, `f"AVG(close) <= {`, or `f"AVG(volume) >= {` — meaningful regression protection.
   PASS.

5. **M-06 — CI workflow is syntactically valid and matches project conventions.** `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` parses cleanly. Jobs: `pytest` + `vitest`. Key details verified:
   - `pip install -e ".[dev,backtest]"` — both extras present in post-session pyproject.toml (dev: pytest/pytest-asyncio/pytest-cov/ruff/httpx; backtest: numpy/matplotlib/scipy/plotly).
   - `ANTHROPIC_API_KEY: ""` + dummy `ARGUS_JWT_SECRET` mirrors the autouse-env-cleanup pattern in tests/ai/conftest.py (DEF-048/049 mitigation).
   - `cd argus/ui && npm ci && npm run test` — argus/ui/package.json `"test": "vitest run"` matches.
   - Python 3.11 matches `requires-python = ">=3.11"` in pyproject.toml; Node 20 is standard for Vite 5.x projects.
   - No matrix, no artifacts, no codecov — matches the "default to simple" kickoff guidance. DEF-180 lockfile work will naturally extend this file. PASS.

6. **DEF-178/179/180 entries are concrete, not stubs.** All three entries contain:
   - A precise problem statement with file paths / line numbers.
   - A trigger condition ("Opportunistic / execution-layer cleanup sprint" / "Opportunistic / next API-layer cleanup sprint" / "Dedicated single-session sprint (~30-60 min)").
   - A concrete next-step recipe — DEF-178 sequences 3 explicit steps including the `[incubator]` extras block to add; DEF-179 specifies `PyJWT>=2.8,<3` with the exact API-difference notes (`jwt.encode` returns str, exception class renames); DEF-180 enumerates the 4 uv commands and the CI integration step. No TBD stubs. PASS.

7. **Parallel-session hygiene — FIX-10 vs FIX-18 file overlap.**
   - `git diff 4cfd8b4..675bf78 --name-only` (FIX-10): `CLAUDE.md`, `docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md`, `docs/audits/audit-2026-04-21/phase-2-review.csv`, `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`.
   - `git diff 675bf78..7aabb96 --name-only` (FIX-18): `.env.example`, `.github/workflows/ci.yml`, `CLAUDE.md`, `docs/audits/audit-2026-04-21/p1-i-dependencies.md`, `docs/audits/audit-2026-04-21/phase-2-review.csv`, `docs/sprints/sprint-31.9/FIX-18-closeout.md`, `pyproject.toml`, `scripts/resolve_sweep_symbols.py`, `tests/scripts/test_resolve_sweep_symbols.py`.
   - **Overlap:** CLAUDE.md + phase-2-review.csv. Both files touched at non-overlapping sections:
     - CLAUDE.md: FIX-10 edited the Backtesting commands section (line ~91, splitting operational wrappers from direct module CLIs); FIX-18 appended DEF-178/179/180 rows (line ~406-408). Different sections, no conflict.
     - phase-2-review.csv: FIX-10 annotated P1-E2-* rows; FIX-18 annotated P1-I-* rows. Disjoint row sets.
   No merge friction. PASS.

8. **Rule-4 sensitive files untouched.** `git show 7aabb96 --name-only` confirms no `argus/api/auth.py` and no `argus/api/websocket/*.py` were modified. The grep of the commit message body mentions `argus/api/auth.py:23` in a narrative context (M-03 judgment call), but only to explain why no call-site edit was needed — the file is genuinely untouched. PASS.

### Regression Checklist Results

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,985 | PASS | Local re-run: 4,989 passed + 1 failed (DEF-150 flake). Total run-size = 4,990 ≥ 4,985. Net +5 new tests, all in tests/scripts/test_resolve_sweep_symbols.py. |
| DEF-150 flake remains the only pre-existing failure | PASS | Exactly 1 failure, exactly `test_check_reminder_sends_after_interval` — DEF-150 signature. Reviewer's run was at 13:02 ET (within the first-2-minutes-of-the-hour danger window); that matches DEF-150's documented trigger pattern. No new regressions. |
| No file outside declared Scope modified | PASS | 9 files changed. Scope: pyproject.toml, resolve_sweep_symbols.py, .env.example (+ .github/workflows/ci.yml as new-file M-06 deliverable). Expected support: tests/scripts/test_resolve_sweep_symbols.py (regression tests mandated by finding-level step 3), CLAUDE.md (DEF additions, appended rows only), audit docs (back-annotations mandated by post-session checklist), FIX-18-closeout.md (close-out skill output). Zero Rule-4 sensitive files. |
| Every resolved finding back-annotated in audit report | PASS | `grep -c "FIX-18"` in p1-i-dependencies.md = 15, phase-2-review.csv = 15. All 15 findings carry RESOLVED / RESOLVED-VERIFIED / DEFERRED FIX-18-deps-and-infra markers. |
| Every DEF closure recorded in CLAUDE.md | PASS (N/A) | No pre-existing DEFs closed. 3 new DEFs (178/179/180) appended to CLAUDE.md DEF table with concrete next-step recipes. |
| Every new DEF/DEC referenced in commit message | PASS | Commit body enumerates DEF-178 (alpaca-py), DEF-179 (python-jose → PyJWT), DEF-180 (lockfile) under "New DEFs opened". No new DECs (option-c mitigation uses existing dep-pinning convention; CI adoption does not require a DEC per Phase 3 precedent). |
| read-only-no-fix-needed findings: verification recorded OR DEF promoted | PASS | L-05 (matplotlib) RESOLVED-VERIFIED — the finding's own text says "Recheck once P1-E2 decisions land"; P1-E2 / FIX-10 just landed without retiring vectorbt_orb.py; matplotlib remains in `[backtest]` pending a future M5-level decision. Verification = the finding's own conditional being applied. |
| deferred-to-defs findings: fix applied AND DEF-NNN added to CLAUDE.md | PASS | M-07 (lockfile) → DEF-180 added; L-04 (alpaca-py → [incubator]) → DEF-178 added. M-02 was ALSO partially deferred (full PyJWT swap → DEF-179) but M-02's CVE mitigation was applied this session via the version pin — not a pure deferral, which is why self-assessment is MINOR_DEVIATIONS rather than CLEAN. |

### Findings

No HIGH or CRITICAL findings.

**INFO-1 (style, informational).** `scripts/resolve_sweep_symbols.py:230` — the sibling `_apply_static_filters()` function still references `FROM historical` (the DuckDB VIEW name) directly, even after M-09 decoupled `_count_cache_symbols()` via the service's public API. This was NOT in the M-09 finding's cited scope (which called out line 171 only), so the omission is not a scope violation, but if the VIEW name is ever renamed during the cache-consolidation cutover (`config/historical_query.yaml` operator repoint still pending per Sprint 31.85 close-out), `_apply_static_filters` would silently break while `_count_cache_symbols` would continue working. No action required now; fold into the next `resolve_sweep_symbols.py` touch or add to DEF-178's broader migration notes. **Severity: INFO.**

### Recommendation

**Proceed to next session (CLEAR).**

All 15 findings landed with appropriate dispositions: 12 RESOLVED via code/config change, 1 RESOLVED-VERIFIED with justified no-op (L-05 matplotlib), 2 DEFERRED with concrete DEF entries (M-07 → DEF-180, L-04 → DEF-178). The M-02 judgment call (option c over the audit's suggested full PyJWT migration) is defensible and factually grounded — PyPI + OSV confirm python-jose 3.4.0 shipped 2025-02-18 and fixes CVE-2024-33663, so the lower-bound bump fully closes the security exposure cited in the finding. The full PyJWT swap is tracked as DEF-179 with a near-drop-in recipe. Scope discipline held (9 files, zero Rule-4 sensitive touches, zero overlap with concurrent FIX-10 commit). Tests net-positive (+5, 0 new regressions; the 1 failing test is the known DEF-150 time-of-day flake, matching its exact documented trigger). Audit docs fully back-annotated (15/15 rows in both the markdown report and CSV). 3 new DEFs include concrete recipes, not TBD stubs.

Single INFO-severity note: `_apply_static_filters()` retains a direct `FROM historical` VIEW-name coupling that parallels the M-09 coupling just removed from `_count_cache_symbols()`. Opportunistic cleanup, not a blocker — the M-09 finding was explicit about the line-171 scope.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-18-deps-and-infra",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "scripts/resolve_sweep_symbols.py:230 still references 'FROM historical' directly in _apply_static_filters(). The M-09 fix decoupled _count_cache_symbols() only (per the finding's cited scope at line 171). Sibling coupling is not a scope violation but would silently break _apply_static_filters() if the VIEW name is renamed during the pending cache-consolidation cutover. Opportunistic cleanup candidate.",
      "severity": "INFO",
      "category": "ARCHITECTURE",
      "file": "scripts/resolve_sweep_symbols.py",
      "recommendation": "Fold into the next resolve_sweep_symbols.py touch or add as a note on DEF-178. Consider adding a parallel helper to HistoricalQueryService (e.g., filter_symbols_by_having(start, end, min_price=..., max_price=..., min_volume=...) → list[str]) that owns the VIEW-name coupling internally."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "13 of 15 findings fully resolved this session; 2 deliberately deferred (M-07 lockfile → DEF-180; L-04 alpaca-py full migration → DEF-178) with concrete next-step recipes per kickoff scope guidance. M-02 chose option c (lower-bound bump to >=3.4.0 excluding CVE-2024-33663) over the audit's suggested full PyJWT migration; the judgment is factually grounded — PyPI confirms python-jose 3.4.0 (2025-02-18) and 3.5.0 both shipped, contradicting the audit's 'no release since 2022' claim; OSV confirms CVE-2024-33663 fixed in 3.4.0. Full PyJWT swap tracked as DEF-179. MINOR_DEVIATION classification reflects the 2 deferrals + option-c choice on M-02, all documented and justified.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    ".env.example",
    ".github/workflows/ci.yml",
    "CLAUDE.md",
    "argus/api/auth.py",
    "argus/data/historical_query_service.py",
    "argus/ui/package.json",
    "docs/audits/audit-2026-04-21/p1-i-dependencies.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "docs/sprints/sprint-31.9/FIX-18-closeout.md",
    "pyproject.toml",
    "scripts/resolve_sweep_symbols.py",
    "tests/scripts/test_resolve_sweep_symbols.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4990,
    "new_tests_adequate": true,
    "test_quality_notes": "5 new tests in tests/scripts/test_resolve_sweep_symbols.py cover (a) M-08 placeholder-vs-param lockstep with all filters set, (b) M-08 dynamic filter-count correctness with partial filters, (c) M-09 public-API path verified via MagicMock (confirms get_date_coverage() called and service.query NOT called), (d) M-09 error degradation (exception → returns 0 matches prior behavior), and (e) M-08 grep-guard on script source (fails if f-string HAVING interpolation is reintroduced). No tautological tests. Grep-guard pattern mirrors the FIX-16 test_existing_experiments_yaml_has_no_typos_in_variant_params precedent and the Sprint 31.85 consolidate_parquet_cache test_no_bypass_flag_exists precedent. Local re-run: 4,989 passed + 1 failed. The 1 failure is tests/sprint_runner/test_notifications.py::test_check_reminder_sends_after_interval — DEF-150, the documented time-of-day arithmetic flake that triggers in the first 2 minutes of every hour (reviewer's run was at 13:02 ET). Total run-size 4,990 matches the close-out's post-session count."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 4,985", "passed": true, "notes": "4,989 passed + 1 DEF-150 flake = 4,990 total. Net +5 new tests. Delta = +5."},
      {"check": "DEF-150 flake remains the only pre-existing failure (no new regressions)", "passed": true, "notes": "Exactly 1 failing test, exactly test_check_reminder_sends_after_interval (DEF-150). Review run-time 13:02 ET is inside the documented first-2-minutes-of-the-hour trigger window. No new regressions introduced."},
      {"check": "No file outside declared Scope was modified", "passed": true, "notes": "9 files changed. 3 scope files (pyproject.toml, scripts/resolve_sweep_symbols.py, .env.example) + 1 new scope file (.github/workflows/ci.yml for M-06) + expected support (tests/scripts/test_resolve_sweep_symbols.py regression tests, CLAUDE.md DEF additions, audit doc back-annotations, FIX-18-closeout.md standard output). Zero Rule-4 sensitive files touched."},
      {"check": "Every resolved finding back-annotated in audit report", "passed": true, "notes": "15/15 FIX-18 annotations in docs/audits/audit-2026-04-21/p1-i-dependencies.md AND docs/audits/audit-2026-04-21/phase-2-review.csv (12 RESOLVED + 1 RESOLVED-VERIFIED + 2 DEFERRED markers)."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "N/A — no pre-existing DEFs closed this session. 3 new DEFs (178/179/180) appended to CLAUDE.md DEF table with full concrete recipes."},
      {"check": "Every new DEF/DEC referenced in commit message", "passed": true, "notes": "Commit body bullets include all three: 'DEF-178: alpaca-py → [incubator]', 'DEF-179: python-jose → PyJWT migration', 'DEF-180: Python lockfile via uv pip compile + CI integration'. No new DECs needed."},
      {"check": "read-only-no-fix-needed findings: verification recorded OR DEF promoted", "passed": true, "notes": "L-05 matplotlib: RESOLVED-VERIFIED. Finding's own text said 'Recheck once P1-E2 decisions land'; FIX-10 landed without retiring vectorbt_orb.py, so matplotlib remains in [backtest] per the finding's conditional. Annotation matches."},
      {"check": "deferred-to-defs findings: fix applied AND DEF-NNN added to CLAUDE.md", "passed": true, "notes": "M-07 lockfile → DEF-180 (full uv pip compile recipe); L-04 alpaca-py incubator → DEF-178 (3-step migration sequence). Both DEF entries are concrete, not TBD stubs."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session. No blockers.",
    "Optional: pair the sibling _apply_static_filters() VIEW-name coupling cleanup with the next resolve_sweep_symbols.py touch or fold into DEF-178's migration notes (INFO-1, not required now)."
  ]
}
```
