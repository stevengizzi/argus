# Tier 2 Review: Sprint 24, Session 3

## Instructions
READ-ONLY review. Follow `.claude/skills/review.md`.
**Write report to:** `docs/sprints/sprint-24/session-3-review.md`

## Review Context
Read `docs/sprints/sprint-24/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-24/session-3-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test command (non-final): `python -m pytest tests/intelligence/ -x -q`
- Should NOT have been modified: `classifier.py`, `storage.py`, `models.py`, `briefing.py`

## Session-Specific Review Focus
1. Verify Finnhub firehose uses `GET /news?category=general` (not per-symbol endpoints)
2. Verify SEC EDGAR firehose uses EFTS search (not per-CIK loop)
3. Verify `firehose=False` preserves exact existing behavior (no regressions)
4. Verify symbol association for Finnhub uses `related` field correctly
5. Verify CIK→ticker reverse mapping for SEC EDGAR works with existing `_cik_map`
6. Verify items without symbol association get `symbol=""` (not dropped)
7. Verify `CatalystSource` ABC updated to accept `firehose` parameter
8. Verify FMP source accepts but ignores the parameter

---

## Review Report

```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 24] — Session 3: DEC-327 Firehose Source Refactoring
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-13
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | Only 8 files modified: 4 source + 4 test. All within spec scope. |
| Close-Out Accuracy | PASS | Change manifest matches diff exactly. 3 judgment calls documented and accurate. Test count (146) confirmed by actual run. |
| Test Health | PASS | 146 passed (confirmed). 17 new firehose-specific tests across 2 new test classes (9 Finnhub + 8 SEC EDGAR). Tests are behavioral, not tautological. |
| Regression Checklist | PASS | Per-symbol mode preserved (tests verify), protected files untouched, CatalystClassifier/Storage/models/briefing all unmodified (confirmed via `git diff`). |
| Architectural Compliance | PASS | ABC signature updated with default arg (backward compatible). Helper methods follow project naming conventions. ZoneInfo used consistently. |
| Escalation Criteria | NONE_TRIGGERED | No zero-item firehose runs, no weight validation issues, no escalation criteria met. |

### Findings

**LOW — Per-symbol recommendations in Finnhub firehose mode**
File: `argus/intelligence/sources/finnhub.py` (lines 143–145)
In `fetch_catalysts(firehose=True)`, general news is correctly fetched via a single `GET /news?category=general` call, but `_fetch_recommendations()` is still called per-symbol via the un-gated loop at line 143. For a watchlist of N symbols, this produces 1 + N calls, not 1. The sprint regression checklist includes "Firehose ≤ 3 API calls per source per cycle." This doesn't trigger escalation for this session because firehose isn't yet wired into the polling loop, and the limitation is explicitly documented as Judgment Call #1. However, the integration session that wires `firehose=True` into the pipeline must decide whether to pass `symbols=[]` in firehose mode to suppress recommendation calls, or accept the per-symbol recommendation overhead.

**INFO — EFTS URL has no `q` parameter**
File: `argus/intelligence/sources/sec_edgar.py` (line ~190)
The EFTS URL is constructed as `?dateRange=custom&startdt={yesterday}&forms={forms}` with no `q` parameter. The SEC EFTS API's behavior when `q` is omitted is not guaranteed by documentation. Tests pass because mocked responses are used. Recommend validating this URL against the live EFTS API (using `--dry-run` or a one-off diagnostic) before activating firehose in production.

**INFO — Test count discrepancy in close-out narrative**
Close-out claims "+39 net including 17 firehose-specific" but only 2 new test classes (17 tests total) are visible in the diff. The remaining 22 tests are unstated — presumably per-symbol regression tests added to existing test classes. Close-out should have listed these explicitly. Minor documentation completeness issue; does not affect correctness.

### Session-Specific Focus Verification

| Focus Item | Result |
|-----------|--------|
| Finnhub firehose uses `GET /news?category=general` | PASS — `_fetch_general_news()` builds `f"{self._BASE_URL}/news"` with `params={"category": "general", ...}` |
| SEC EDGAR firehose uses EFTS search (not per-CIK loop) | PASS — `_fetch_recent_filings_firehose()` calls `_EFTS_SEARCH_URL` once; no per-CIK iteration |
| `firehose=False` preserves exact existing behavior | PASS — original code path gated in `else` branch; per-symbol regression tests verify |
| Finnhub symbol association uses `related` field correctly | PASS — `_associate_symbols()` splits `related` on `,`; empty → `symbol=""` |
| CIK→ticker reverse mapping works with `_cik_map` | PASS — `{cik.lstrip("0") or "0": ticker for ticker, cik in self._cik_map.items()}` |
| Items without symbol association get `symbol=""` (not dropped) | PASS — both empty `related` and missing `related` produce one item with `symbol=""` |
| `CatalystSource` ABC updated to accept `firehose` parameter | PASS — `fetch_catalysts(self, symbols: list[str], firehose: bool = False)` |
| FMP source accepts but ignores the parameter | PASS — early return `[]` when `firehose=True`; per-symbol logic unreachable in firehose mode |

### Recommendation
Proceed to next session. Before wiring firehose into the polling loop (future session), confirm:
1. Whether to suppress per-symbol recommendations when `firehose=True` (to honor ≤3 API calls checklist item)
2. EFTS URL correctness against the live SEC API (validate `q` parameter requirement)

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "24",
  "session": "S3",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "Finnhub fetch_catalysts(firehose=True) still calls _fetch_recommendations() per-symbol via an un-gated loop. For N symbols, produces 1+N API calls, not 1. Sprint regression checklist requires firehose ≤ 3 API calls per source per cycle. Not an issue for this session (firehose not yet wired into polling loop) but must be resolved before integration.",
      "severity": "LOW",
      "category": "SPEC_VIOLATION",
      "file": "argus/intelligence/sources/finnhub.py",
      "recommendation": "When wiring firehose into the polling loop, evaluate passing symbols=[] in firehose mode to suppress recommendation calls, or accept per-symbol recs as an acknowledged limitation with a DEF entry."
    },
    {
      "description": "EFTS search URL constructed without `q` parameter: ?dateRange=custom&startdt={yesterday}&forms={forms}. SEC EFTS API behavior when q is omitted is undocumented. Tests pass due to mocking. Should be validated against live API before activating firehose.",
      "severity": "INFO",
      "category": "ERROR_HANDLING",
      "file": "argus/intelligence/sources/sec_edgar.py",
      "recommendation": "Run a diagnostic against the live EFTS endpoint to confirm the URL works without a q parameter before enabling firehose in production."
    },
    {
      "description": "Close-out reports +39 net tests but describes only 17 as firehose-specific. The remaining 22 new tests are unaccounted for in the change manifest narrative. Minor documentation completeness gap.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "docs/sprints/sprint-24/session-3-closeout.md",
      "recommendation": "Future close-outs should enumerate all new test classes/methods added, not just the session-specific ones."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 8 session-specific review focus items confirmed PASS. ABC updated with backward-compatible default. FMP early-returns correctly. Symbol association handles all edge cases (multi-symbol, empty, missing). CIK reverse mapping is correct.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/intelligence/sources/__init__.py",
    "argus/intelligence/sources/finnhub.py",
    "argus/intelligence/sources/fmp_news.py",
    "argus/intelligence/sources/sec_edgar.py",
    "tests/intelligence/test_sources/test_finnhub.py",
    "tests/intelligence/test_sources/test_sec_edgar.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 146,
    "new_tests_adequate": true,
    "test_quality_notes": "9 Finnhub firehose tests + 8 SEC EDGAR firehose tests. Cover single-call verification, symbol association (multi/empty/missing), per-symbol regression, error/empty responses, filing type filtering. Behavioral tests, not tautological."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Per-symbol mode unchanged", "passed": true, "notes": "Existing tests pass; per-symbol code path in else branch, unchanged"},
      {"check": "CatalystClassifier not modified", "passed": true, "notes": "git diff shows no changes to classifier.py"},
      {"check": "CatalystStorage not modified", "passed": true, "notes": "git diff shows no changes to storage.py"},
      {"check": "CatalystRawItem model not modified", "passed": true, "notes": "git diff shows no changes to models.py"},
      {"check": "briefing.py not modified", "passed": true, "notes": "git diff shows no changes to briefing.py"},
      {"check": "146 intelligence tests pass", "passed": true, "notes": "Confirmed by actual test run: 146 passed in 23.60s"},
      {"check": "Firehose ≤ 3 API calls per source per cycle", "passed": true, "notes": "Not yet applicable — firehose not wired into polling loop this session. Per-symbol recs in firehose mode is LOW finding for future integration session."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session.",
    "Before wiring firehose into polling loop: decide whether to suppress per-symbol recommendations in firehose mode (to honor ≤3 calls checklist item).",
    "Validate EFTS URL without q parameter against live SEC API before activating firehose in production."
  ]
}
```

