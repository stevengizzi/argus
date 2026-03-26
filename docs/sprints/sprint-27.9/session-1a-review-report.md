---BEGIN-REVIEW---

**Reviewing:** Sprint 27.9 S1a — Config Model + VIXDataService Skeleton
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-26
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All spec requirements met. No forbidden files modified. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. Self-assessment CLEAN is reasonable. |
| Test Health | PASS | 11 new tests, all passing (0.07s). |
| Regression Checklist | PASS | R13 verified (YAML-to-Pydantic alignment test passes). R1-R12, R14-R15 not yet testable. |
| Architectural Compliance | PASS | Follows existing patterns (separate DB per DEC-345, WAL mode, Pydantic config model). |
| Escalation Criteria | NONE_TRIGGERED | No yfinance import. No changes to events/strategies/execution/backtest/ai. No SINDy creep. |

### Findings

**MEDIUM: Enum member names diverge from sprint spec (F-001)**
File: `argus/data/vix_config.py`
The sprint spec (review-context.md) defines specific enum members:
- `VolRegimePhase`: CALM/TRANSITION/**VOL_EXPANSION**/CRISIS
- `VolRegimeMomentum`: **STABILIZING**/NEUTRAL/**DETERIORATING**
- `TermStructureRegime`: **CONTANGO_LOW/CONTANGO_HIGH/BACKWARDATION_LOW/BACKWARDATION_HIGH**

The implementation uses different names:
- `VolRegimePhase`: CALM/TRANSITION/**ELEVATED**/CRISIS
- `VolRegimeMomentum`: **RISING/FALLING/STABLE**
- `TermStructureRegime`: **CONTANGO/FLAT/BACKWARDATION** (3 members instead of 4)

The session 1a impl spec says only "Enum definitions: VolRegimePhase, VolRegimeMomentum, TermStructureRegime, VRPTier" without specifying members, so this is not a session-spec violation. However, the sprint-level spec is authoritative, and later sessions (calculators, RegimeVector expansion) will need these exact enum members. This divergence will need reconciliation in Session 2a or earlier.

**LOW: `_last_trading_day()` does not account for US market holidays (F-002)**
File: `argus/data/vix_data_service.py`, lines 219-240
The spec says "if weekend/holiday, return Friday/last business day." The implementation handles weekends (Saturday/Sunday rollback) but not US market holidays (e.g., MLK Day, Presidents Day, Good Friday). On a post-holiday Tuesday morning, this method could return Monday (a holiday) as the last trading day. The `is_stale` logic uses `pd.bdate_range` which also does not account for market holidays (only business days = Mon-Fri). This is a known limitation that is acceptable for a skeleton session -- `pd.bdate_range` with a `holidays` parameter or the `pandas_market_calendars` library could address it in a later session. The `max_staleness_days=3` default provides enough buffer for most single-holiday scenarios.

**INFO: `is_stale` opens a new DB connection on every property access (F-003)**
File: `argus/data/vix_data_service.py`, lines 188-217
The `is_stale` property opens and closes a fresh SQLite connection each time it is called. Since `get_latest_daily()` also calls `is_stale` internally, a single `get_latest_daily()` call opens two separate connections. For daily-frequency data this is not a performance concern, but worth noting for when this service is integrated into the update loop (Session 1b+).

**INFO: Commit includes unrelated working-tree changes in git status (F-004)**
The `git diff HEAD~1` output initially appeared to include validation JSON and script changes, but inspection of the commit itself (`git log --stat`) confirms only the 6 expected files were committed. The working tree has unrelated unstaged changes from previous sprints. No action needed.

### Recommendation
CONCERNS due to F-001 (enum naming divergence from sprint spec). The enum member names in `vix_config.py` do not match the sprint-level specification. This is non-blocking for Session 1a (which only requires config models and data service skeleton), but will require reconciliation before Session 2a (calculators) begins, as the calculators directly reference these enum members. Recommend addressing at the start of Session 1b or 2a to avoid cascading naming inconsistencies.

All other aspects of the implementation are clean: WAL mode confirmed, business-day staleness confirmed, get_latest_daily behavior correct, no yfinance import, no forbidden file modifications, tests comprehensive.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.9",
  "session": "S1a",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "Enum member names diverge from sprint spec: VolRegimePhase uses ELEVATED instead of VOL_EXPANSION, VolRegimeMomentum uses RISING/FALLING/STABLE instead of STABILIZING/NEUTRAL/DETERIORATING, TermStructureRegime uses 3 members (CONTANGO/FLAT/BACKWARDATION) instead of 4 (CONTANGO_LOW/CONTANGO_HIGH/BACKWARDATION_LOW/BACKWARDATION_HIGH)",
      "severity": "MEDIUM",
      "category": "NAMING_CONVENTION",
      "file": "argus/data/vix_config.py",
      "recommendation": "Reconcile enum members with sprint spec before Session 2a (calculators). Either update enums to match spec or document the deliberate deviation as a DEC entry."
    },
    {
      "description": "_last_trading_day() handles weekends but not US market holidays. pd.bdate_range also excludes only weekends, not holidays.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/data/vix_data_service.py",
      "recommendation": "Acceptable for skeleton. max_staleness_days=3 provides buffer. Consider pandas_market_calendars if precision needed later."
    },
    {
      "description": "is_stale property opens a new DB connection on every call. get_latest_daily() triggers two separate connections.",
      "severity": "INFO",
      "category": "PERFORMANCE",
      "file": "argus/data/vix_data_service.py",
      "recommendation": "No action needed for daily-frequency data. Note for future optimization if called in tight loops."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "Session 1a impl spec met. Sprint-level spec enum member names not matched (session spec did not specify members explicitly).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/data/vix_config.py",
    "argus/data/vix_data_service.py",
    "argus/core/config.py",
    "config/vix_regime.yaml",
    "tests/data/test_vix_data_service.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 11,
    "new_tests_adequate": true,
    "test_quality_notes": "11 tests cover config validation (5), persistence roundtrip (2), staleness (2), weekend handling (1), YAML alignment (1). All meaningful with clear assertions."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "R13: Config YAML keys match Pydantic model", "passed": true, "notes": "test_config_yaml_matches_pydantic_model passes"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Reconcile enum member names with sprint spec before Session 2a"
  ]
}
```
