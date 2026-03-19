---BEGIN-REVIEW---

# Sprint 25.6 Session 1 — Tier 2 Review

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-20
**Commit:** a5ef6a1 (fix: separate evaluation telemetry DB + rate-limit warnings)
**Close-out self-assessment:** MINOR_DEVIATIONS

---

## 1. Spec Compliance

### 1.1 Deliverable: EvaluationEventStore initialized with `data/evaluation.db` path
**Status: PASS**
- `main.py` Phase 10.3 creates the store at `config.system.data_dir / "evaluation.db"` (line 580).
- `server.py` standalone/dev mode creates at `"data/evaluation.db"` (line 267).
- Both paths resolve to `data/evaluation.db` given the default `data_dir = "data"`.
- Minor inconsistency: `main.py` uses the config-driven `data_dir` while `server.py` hardcodes `"data"`. These would diverge if `data_dir` were overridden. Low risk since `data_dir` has never been customized, but worth noting.

### 1.2 Deliverable: Health check loop reuses existing store instance
**Status: PASS**
- `_evaluation_health_check_loop()` now references `self._eval_store` directly (line 768).
- The previous pattern of constructing a new `EvaluationEventStore()`, calling `initialize()`, and `close()` on every 5-minute cycle is fully removed.
- The `EvaluationEventStore` import was removed from the health check method (previously imported inline).

### 1.3 Deliverable: Write failure warnings rate-limited to 1 per 60 seconds
**Status: PASS**
- `telemetry_store.py` uses `time.monotonic()` with a 60-second suppression window via `_last_warning_time` instance variable and `_WARNING_INTERVAL_SECONDS` class constant.
- Time-based suppression (not counter-based) confirmed.
- Monotonic clock is the correct choice (immune to wall clock adjustments).

### 1.4 Deliverable: All existing tests pass + 5+ new tests
**Status: PASS**
- 6 new tests in `tests/strategies/test_telemetry_store.py`, all passing.
- Tests cover: DB path separation, argus.db isolation, write persistence, rate-limiting suppression, interval resumption, and pre-initialized store health check reuse.

---

## 2. Session-Specific Review Focus

| # | Focus Item | Verdict | Notes |
|---|-----------|---------|-------|
| 1 | `evaluation.db` is the path used, not `argus.db` | PASS | Both `main.py` and `server.py` use `evaluation.db`. |
| 2 | Health check does NOT call `EvaluationEventStore()` or `initialize()` per cycle | PASS | Inline import + construction + init + close removed. Uses `self._eval_store`. |
| 3 | Rate-limiting uses time-based suppression (not counter) | PASS | `time.monotonic()` comparison against `_WARNING_INTERVAL_SECONDS`. |
| 4 | No `argus.db` tables affected | PASS | No changes to `trade_logger.py`, `db/manager.py`, or any schema files. |
| 5 | `ObservatoryService` queries still work | PASS | `ObservatoryService` initialized at line 292 with `app_state.telemetry_store`, which holds the same store instance. `execute_query()` method unchanged. |

---

## 3. Forbidden File Check
**PASS** -- None of the forbidden files were modified: `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`, `db/manager.py`, strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `base_strategy.py`), `catalyst_pipeline.py`.

---

## 4. Test Results
- Scoped test command: `python -m pytest tests/strategies/test_telemetry_store.py -x -v`
- Result: **6 passed in 0.18s**

---

## 5. Findings

### 5.1 CONCERN: Undocumented frontend changes in commit
The commit `a5ef6a1` includes substantial frontend changes not mentioned in the close-out report:
- `TradeTable.tsx`: 173 lines changed -- pagination replaced with scrollable table + sortable columns
- `TradesPage.tsx`: 66 lines changed -- pagination removed, Zustand store integration for filter persistence
- `TradeFilters.tsx`: `page` field removed from `FilterState`
- `TradeTable.test.tsx`: pagination props removed from tests
- `TradesTab.tsx`: pagination props removed

These changes correspond to Sprint 25.6 deliverables 5 (scroll replaces pagination) and 8 (sortable columns), which are Session 3 scope per the sprint spec. They appear to have been committed together with Session 1 work in a single commit, which means the close-out report is incomplete -- it only documents the backend telemetry changes.

**Impact:** The close-out report is not a reliable record of what changed. The frontend changes themselves appear correct and well-structured, but their inclusion without documentation in the close-out creates a review gap. A reviewer relying solely on the close-out would miss these changes entirely.

### 5.2 CONCERN: Hardcoded path in server.py vs config-driven path in main.py
`server.py` line 267 uses `str(Path("data/evaluation.db"))` while `main.py` line 580 uses `str(Path(config.system.data_dir) / "evaluation.db")`. If `data_dir` were ever changed from its default `"data"`, the standalone API server would write to a different location than the main system. This is low risk today but violates the architectural rule "NEVER hardcode configuration values -- always read from YAML config files."

---

## 6. Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|-----------|
| 1 | DB separation causes data corruption in `argus.db` | No |
| 2 | Regime reclassification unexpectedly excludes strategies | N/A (not in session scope) |
| 3 | Frontend changes require unplanned backend API changes | No -- frontend changes remove pagination props only |
| 4 | Test count drops by more than 5 | No -- count increased by 6 |

No escalation criteria triggered.

---

## 7. Regression Checklist (Session-Relevant Items)

| # | Check | Result |
|---|-------|--------|
| 1 | Trades still logged to `argus.db` | PASS (no changes to trade logging) |
| 2 | Quality history still in `argus.db` | PASS (no changes to quality pipeline) |
| 4 | Evaluation events write to `evaluation.db` | PASS (verified in tests) |
| 5 | No "EvaluationEventStore initialized" spam | PASS (single initialization in main.py, conditional in server.py) |

---

## 8. Verdict

**CONCERNS**

The backend telemetry changes (DB separation, rate-limiting, health check reuse) are well-implemented and fully tested. All session-specific review focus items pass. No escalation criteria triggered.

Two concerns documented:
1. The commit bundles undocumented frontend changes (TradeTable pagination-to-scroll + sortable columns) that are not mentioned in the close-out report. The close-out is incomplete as a change manifest.
2. Minor hardcoded path inconsistency between `server.py` and `main.py` for the evaluation DB location.

Neither concern blocks progress, but the first means this close-out cannot be treated as a complete record of the commit's changes.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "25.6",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings": [
    {
      "severity": "MEDIUM",
      "category": "documentation",
      "description": "Commit includes undocumented frontend changes (TradeTable pagination-to-scroll, sortable columns, TradesPage filter persistence) not listed in close-out report change manifest. 5 frontend files modified with ~250 net line changes omitted from documentation.",
      "files": [
        "argus/ui/src/features/trades/TradeTable.tsx",
        "argus/ui/src/features/trades/TradeTable.test.tsx",
        "argus/ui/src/features/trades/TradeFilters.tsx",
        "argus/ui/src/features/patterns/tabs/TradesTab.tsx",
        "argus/ui/src/pages/TradesPage.tsx"
      ],
      "recommendation": "Future sessions should ensure the close-out change manifest covers all files in the commit, or frontend changes should be in a separate commit."
    },
    {
      "severity": "LOW",
      "category": "code_quality",
      "description": "server.py hardcodes 'data/evaluation.db' while main.py uses config.system.data_dir. Paths diverge if data_dir is customized.",
      "files": ["argus/api/server.py"],
      "recommendation": "Use config-driven path in server.py standalone mode to match main.py."
    }
  ],
  "tests_passed": true,
  "tests_count": 6,
  "forbidden_files_clean": true,
  "escalation_triggered": false
}
```
