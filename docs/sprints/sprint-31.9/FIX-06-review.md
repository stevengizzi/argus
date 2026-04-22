```markdown
---BEGIN-REVIEW---

**Reviewing:** Sprint 31.9 Phase 3 audit remediation — `FIX-06-data-layer` (Stage 5 Wave 1)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | `argus/core/events.py` addition (SystemAlertEvent frozen dataclass) is documented scope expansion with clear justification in close-out judgment call #3 — purely additive, no existing subscribers disturbed, prerequisite for DEF-014 emitter side. All other 30 modified files fall within the declared scope. No Rule-4-sensitive files touched. |
| Close-Out Accuracy | PASS | Change manifest matches actual diff exactly (`git diff 776f7c8..4ea09a7` = 31 files). All 9 judgment calls honest and well-reasoned. Commit message structure matches spec template. |
| Test Health | PASS | Full suite: `5017 passed, 40 warnings in 83.01s` (0 failures). Vitest: `859 passed / 115 files`. Net +17 new tests match the claimed delta precisely. DEF-150 flake did not fire. |
| Regression Checklist | PASS | All 8 campaign-level checks verified — see individual results below. |
| Architectural Compliance | PASS | SystemAlertEvent follows existing frozen-dataclass pattern alongside `DataStaleEvent`/`DataResumedEvent`. Public accessor added on `FMPReferenceClient` respects the property-based API pattern. Raw-string regex extracted as module constant preserves DuckDB semantics. No new `# type: ignore` introduced. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding unresolved; pytest net delta +17 ≥ 0; documented scope accommodation is defensible; no new test-failure surfaces; no Rule-4 sensitive file touched; audit back-annotations present across all 4 contributing audit docs; CRITICAL regression tests exercise the previously-broken runtime path (load_config overlay resolution). |

### Regression Checklist — Per-Item Verification

1. **pytest net delta ≥ 0 against baseline 5,000 passed** — PASS. Local run: 5,017 passed. Net +17 matches claim.
2. **DEF-150 remains sole pre-existing failure** — PASS. 0 failures observed. DEF-150 is time-of-day-bounded (minute ∈ {0,1}); it happened to pass in this run, which is consistent with flaky behavior (not a regression).
3. **No file outside declared Scope modified** — PASS-WITH-CAVEAT. `argus/core/events.py` addition documented as SCOPE EXPANSION in close-out judgment call #3 — accepted as necessary prerequisite for the DEF-014 emitter site. All other file edits fall within the session's declared scope (data-layer modules + config + tests + docs).
4. **Audit-report back-annotations present** — PASS. FIX-06 mention counts: `p1-c2-data-layer.md`=19, `p1-d1-catalyst-quality.md`=2, `p1-g1-test-coverage.md`=1, `p1-i-dependencies.md`=1. Total 23 back-annotations across 4 audit docs. Finding 2 of p1-c2 correctly NOT annotated (was FIX-16, out of FIX-06 scope).
5. **DEF closures recorded in CLAUDE.md** — PASS. DEF-014 marked PARTIALLY RESOLVED with scope note on HealthMonitor deferral; DEF-037/165 marked fully RESOLVED with strikethrough; DEF-032 re-verified in place with FIX-06 attribution; DEF-183 opened with complete remediation recipe.
6. **New DEFs referenced in commit message bullets** — PASS. Commit `4ea09a7` references DEF-014/037/165 + implicit DEF-183 context in the Alpaca deferral line.
7. **`read-only-no-fix-needed` findings verified and annotated** — PASS. F12 (`_MAX_BARS_PER_SYMBOL` magic number), F18 (databento_utils LIVE), F22 (replay_data_service LIVE for backtesting), F23 (scanner.py Scanner ABC + StaticScanner LIVE) all RESOLVED-VERIFIED with inspection records.
8. **`deferred-to-defs` findings: fix applied AND DEF opened** — PASS. F7/F9 → DEF-165 resolved; F17 → DEF-183 opened; F20 → DEF-032 re-verified in place with pointer comment.

### Specific Verification Tasks

**F25 CRITICAL resolution (three-layer defense):**
- **Layer 1** `config/historical_query.yaml:14` — `cache_dir: "data/databento_cache_consolidated"` ✓ on disk.
- **Layer 2** `argus/data/historical_query_config.py:28` — Python default synced to consolidated ✓.
- **Layer 3** Three regression tests in `tests/test_fix01_load_config_merge.py`:
  - `test_historical_query_overlay_resolves_consolidated_cache` — exercises `load_config()` overlay path end-to-end ✓.
  - `test_historical_query_default_is_consolidated_when_overlay_missing` — guards Python default ✓.
  - `test_real_historical_query_yaml_points_at_consolidated` — guards the repo YAML against accidental revert ✓.
- All 3 pass in isolation and together. Revert-proof quality confirmed by inspection of the assertion targets.

**F2 multi-month parquet cache:**
- `_check_parquet_cache()` now enumerates months in `[start, end]`, fail-closes on any missing month. Previously returned a silently-truncated single-month frame.
- Test `test_multi_month_concat_single_and_missing_coverage` covers all three scenarios (happy path + single-month regression + missing-middle-month fail-closed) in one function. The consolidation workaround for the pandas/pyarrow period-extension re-registration is acknowledged as pragmatic.

**F8 regex raw-string fix:**
- Verified semantically equivalent to the pre-session `'.*/([^/]+)/[^/]+\\.parquet$'` literal. The f-string expansion of `_SYMBOL_FROM_FILENAME_REGEX = r".*/([^/]+)/[^/]+\.parquet$"` produces the exact same SQL string for DuckDB's regex engine. Initial attempt to inline `r'...'` in the SQL literal was correctly caught and rejected during implementation (DuckDB interprets `r` as a type cast).

**F5 DEF-014 SystemAlertEvent:**
- Confirmed purely additive at `argus/core/events.py:405-430`. Grep of `SystemAlertEvent` across `argus/`: only the new emission site in `databento_data_service.py:_run_with_reconnection()` references the class. Existing TODOs at `ibkr_broker.py:453,531` and `alpaca_data_service.py:593` correctly untouched.
- Emission at max-retries-exceeded wrapped in try/except with `logger.exception()` fallback — prevents alert emission failure from obscuring the original reconnection exhaustion log.

**F19 DEF-037 API key redaction:**
- `_redact()` helper at `argus/data/fmp_reference.py:864-880` correctly handles both active-key (masks) and no-key (pass-through) paths.
- Threaded through the 4 FMP network-error log sites (fetch_stock_list × 2, canary test × 2) and WARNING comment added to `databento_data_service.py::fetch_daily_bars()` error handlers.
- Regression tests at `test_redact_masks_api_key_in_error_strings` + `test_redact_noop_when_api_key_not_set`.

**F13/F14 FMP circuit breaker + firehose log:**
- `_auth_disabled_until` correctly checked at top of `fetch_catalysts()`; 1h backoff; `reset_disabled_flag()` clears both flags.
- Firehose-mode one-shot log gated by `_firehose_skip_logged` flag (reset in `start()`).
- Test `test_circuit_breaker_sticky_across_cycles` correctly asserts the new sticky contract; prior test `test_circuit_breaker_resets_between_cycles` appropriately renamed (asserted the bug's contract).

**F11 naive-timestamp fail-fast:**
- `IntradayCandleStore.on_candle()` raises `ValueError` with descriptive message on naive timestamps. Production path unaffected (Databento always emits UTC-aware). Regression test `test_candle_store_rejects_naive_timestamp` confirms.

**F24 private-attr reach-in:**
- Grep of `_reference_client._cache` across `argus/`: 0 hits. Only `UniverseManager.rebuild_after_refresh()` at line 582 still reaches into `_cache` for dict-copy (not `.keys()`) — acknowledged in-session as narrowly out-of-scope (audit finding specifically targeted `.keys()` access; dict-snapshot at line 582 is a different access that wants the data, for which no public accessor exists yet).

**F15 script renames:**
- All 5 scripts renamed via `git mv` (status shows `R` entries). `CLAUDE.md` command example updated for `scripts/diagnose_time_stop_eod.py`. No stale references in code (remaining mentions are in historical audit/sprint docs — expected).

### Observations

The 9 judgment calls in the close-out are all well-justified and conservative — particularly:
- Judgment call #1 (F25 via overlay path rather than spec option (b)) correctly recognizes that FIX-16 superseded the spec's suggestion.
- Judgment call #3 (events.py scope expansion) is the most load-bearing; the alternative of leaving DEF-014 partially open with a log-only signal was considered and rejected for sound reasons.
- Judgment call #4 (F17 Alpaca retirement deferred via DEF-183) correctly avoids the `main.py` scope boundary.
- Judgment call #7 (F26 VIX FMP-fallback nonexistence) is an honest correction of audit-wording drift.

Nothing in the session meets the ESCALATE criteria. The MINOR_DEVIATIONS self-assessment is appropriately calibrated — two documented judgment calls (events.py expansion + F26 scope interpretation) are proportionate and necessary, not spec violations.

### Recommendation

Proceed to next session (FIX-07 intelligence / catalyst / quality per campaign tracker). FIX-06-data-layer cleared all 26 findings with:
- One acceptable documented scope expansion (SystemAlertEvent)
- Three-layer revert-proof regression defense on the F25 CRITICAL cache repoint
- Clean test health (+17 tests, 0 failures)
- Precise audit back-annotations across 4 contributing audit docs
- Well-articulated DEF lifecycle (1 PARTIAL + 2 RESOLVED + 1 re-verified + 1 opened)

Operator follow-ups are tracked via the new/updated DEFs — none block the next FIX-NN session:
- DEF-014 HealthMonitor subscription (awaits P1-A1 M9)
- DEF-177 RejectionStage.MARGIN_CIRCUIT (cross-domain, unchanged)
- DEF-183 Alpaca incubator retirement (new, opened with clear recipe)

CAMPAIGN-COMPLETENESS-TRACKER.md operator edits being left unstaged is acknowledged and not a review concern.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "31.9-phase-3-audit",
  "session": "FIX-06-data-layer",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "argus/core/events.py — SystemAlertEvent frozen dataclass added; file not in session's declared scope. Purely additive, no existing subscribers disturbed, documented as judgment call #3. Required prerequisite for DEF-014 emitter side. Accommodated, not flagged.",
      "severity": "INFO",
      "category": "SCOPE_BOUNDARY_VIOLATION",
      "file": "argus/core/events.py",
      "recommendation": "Accept as documented scope expansion. HealthMonitor subscription deferred to P1-A1 M9 per DEF-014 partial-resolution note in CLAUDE.md."
    },
    {
      "description": "F26 VIX test coverage interpretation — audit spec mentioned 'FMP fallback branch' that does not exist in VIXDataService (yfinance-only with VIXDataUnavailable graceful degradation). 4 tests cover the spirit (refresh happy / empty-raises / past-today-skip / initialize-fallback). Audit row back-annotated as partial.",
      "severity": "INFO",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/data/test_vix_data_service.py",
      "recommendation": "No action — audit wording did not reflect code reality; judgment call #7 addresses it."
    },
    {
      "description": "F2 multi-month parquet tests consolidated into a single function due to pandas/pyarrow period-extension re-registration error when running 3 separate parquet-writing test functions sequentially in the same pytest xdist worker. Workable but not ideal.",
      "severity": "INFO",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/data/test_databento_data_service.py",
      "recommendation": "Opportunistic — investigate a cleaner pyarrow registry isolation approach (pytest fixture with per-test teardown?) if this pattern repeats elsewhere."
    },
    {
      "description": "UniverseManager.rebuild_after_refresh() at line 582 still accesses _reference_client._cache directly (dict-snapshot, not .keys()). Not in FIX-06 audit scope (finding targeted .keys() access only) but is a related pattern worth a future follow-on.",
      "severity": "LOW",
      "category": "ARCHITECTURE",
      "file": "argus/data/universe_manager.py",
      "recommendation": "Future opportunistic fix — expose a public reference-data accessor on FMPReferenceClient if the pattern needs to be purged entirely. Not blocking."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "All 26 findings addressed. Two documented judgment calls (events.py scope expansion, F26 test scope interpretation) are proportionate and necessary. F25 CRITICAL resolved via FIX-16-compatible overlay path rather than spec option (b); close-out documents why option (b) is moot post-FIX-16.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/config.py",
    "argus/core/events.py",
    "argus/data/databento_data_service.py",
    "argus/data/fmp_reference.py",
    "argus/data/fmp_scanner.py",
    "argus/data/historical_query_config.py",
    "argus/data/historical_query_service.py",
    "argus/data/intraday_candle_store.py",
    "argus/data/universe_manager.py",
    "argus/intelligence/sources/fmp_news.py",
    "config/historical_query.yaml",
    "tests/core/test_config.py",
    "tests/data/test_databento_data_service.py",
    "tests/data/test_fmp_reference.py",
    "tests/data/test_historical_query_config.py",
    "tests/data/test_intraday_candle_store.py",
    "tests/data/test_universe_manager.py",
    "tests/data/test_vix_data_service.py",
    "tests/intelligence/test_sources/test_fmp_news.py",
    "tests/test_fix01_load_config_merge.py",
    "CLAUDE.md",
    "docs/operations/parquet-cache-layout.md",
    "docs/audits/audit-2026-04-21/p1-c2-data-layer.md",
    "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md",
    "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md",
    "docs/audits/audit-2026-04-21/p1-i-dependencies.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 5017,
    "new_tests_adequate": true,
    "test_quality_notes": "+17 regression tests, all passing. F25 CRITICAL has a three-layer defense (overlay resolution, default-when-missing, real-YAML guard) — revert-proof by construction. F2 multi-month test covers happy path + single-month regression + missing-middle-month fail-closed in one function (pyarrow workaround acknowledged). F11 naive-timestamp test exercises the raise path. F19 _redact tests cover both active-key and no-key paths. F13/F14 sticky circuit breaker test correctly asserts the new sticky contract (vs the prior reset-each-cycle contract). Vitest: 859/859 pass."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 5,000", "passed": true, "notes": "5000 -> 5017 (net +17). Verified via full suite run."},
      {"check": "DEF-150 flake remains only pre-existing failure (no new regressions)", "passed": true, "notes": "0 failures in this review run. DEF-150 happened to pass; no other pre-existing failures re-emerged."},
      {"check": "No file outside declared Scope modified", "passed": true, "notes": "events.py addition documented as scope expansion in judgment call #3 — accepted as prerequisite for DEF-014 emitter side."},
      {"check": "Every resolved finding back-annotated in audit report", "passed": true, "notes": "Grep: 19 (p1-c2) + 2 (p1-d1) + 1 (p1-g1) + 1 (p1-i) = 23 FIX-06-data-layer annotations across 4 audit files."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "DEF-014 PARTIAL, DEF-037 RESOLVED, DEF-165 RESOLVED, DEF-032 re-verified in place, DEF-183 new — all present in DEF table."},
      {"check": "Every new DEF/DEC referenced in commit message bullets", "passed": true, "notes": "Commit 4ea09a7 cites DEF-014/037/165 + implicit DEF-183 context in the Alpaca line."},
      {"check": "read-only-no-fix-needed findings: verification or DEF promoted", "passed": true, "notes": "F12/F18/F22/F23 back-annotated as RESOLVED-VERIFIED."},
      {"check": "deferred-to-defs findings: fix applied AND DEF-NNN added", "passed": true, "notes": "F7/F9 via DEF-165 closure; F17 via new DEF-183; F20 via DEF-032 re-verification."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to Stage 5 Wave 2 (FIX-07 intelligence / catalyst / quality).",
    "Paste close-out + review artifacts into Work Journal per sprint-campaign choreography."
  ]
}
```
