---BEGIN-REVIEW---

**Reviewing:** Sprint 27.65 S2 — Trade Correctness + Risk Config
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-24
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | R1 (bracket amendment), R2 (concurrent limits), R3 (zero-R guard), R4 (S1 CONCERNS resolution) all implemented. |
| Close-Out Accuracy | MINOR_ISSUE | Close-out claims separate file-level changes to risk_manager.py and config.py, but S1-S3 are squashed into a single commit — close-out is correct about the changes existing, but the per-session attribution cannot be verified from git history. |
| Test Health | PASS | 734 scoped tests passing (execution + risk_manager + strategies). 12+ new tests in test_order_manager_safety.py covering all four requirements. |
| Regression Checklist | PASS | Normal stop/target paths unaffected. Bracket amendment correctly guarded by BrokerSource check. Risk Manager circuit breakers untouched. Reconciliation remains warn-only. |
| Architectural Compliance | PASS | No new order paths bypass Risk Manager. Amendment reuses existing submit helpers with retry+flatten safety net. SimulatedBroker bypass preserved. |
| Escalation Criteria | NONE_TRIGGERED | (1) No new unguarded order paths. (2) Reconciliation is warn-only. (3) Bracket amendment always resubmits stop first; stop retry failure triggers emergency flatten. (4) BrokerSource.SIMULATED path preserved. (5) Circuit breaker logic unchanged. |

### Findings

**MEDIUM — Brief unprotected window during bracket amendment**
File: `argus/execution/order_manager.py`, lines 673-713
The amendment logic cancels all three bracket legs (stop, T1, T2) sequentially (lines 673-699), then resubmits them sequentially (lines 706-713). Between the cancel of the stop and its resubmission, the position has no server-side stop protection. This window is likely sub-second (two async broker calls), and the stop is resubmitted first (correct priority). If the stop resubmission fails, the existing `_submit_stop_order` retry logic triggers emergency flatten (lines 1216-1221), so the position does not remain unprotected indefinitely. The close-out acknowledges this in Judgment Call #1. This is acceptable for paper trading but worth noting for live trading readiness: an alternative approach would be to submit new orders first, then cancel the old ones (modify-rather-than-cancel-and-replace).

**LOW — Red-to-Green strategy missing zero-R guard and concurrent position check**
Files: `argus/strategies/red_to_green.py`
The zero-R guard (`_has_zero_r`) was added to `orb_base.py` and `pattern_strategy.py` but not to `red_to_green.py`. R2G is a standalone BaseStrategy subclass that constructs signals via R-multiples, making zero-R less likely but not impossible (e.g., if `target_1_r` is configured to a very small value and floating-point rounding produces entry approximately equal to target). Similarly, the strategy-level `max_concurrent_positions` skip-when-zero guard was added to ORB, VWAP Reclaim, and Afternoon Momentum but not R2G. The system-level Risk Manager check handles the concurrent limit correctly for all strategies, so this is a defense-in-depth gap rather than a functional bug.

**LOW — Squashed commit makes per-session review difficult**
The single commit `1255064` covers S1-S3 together, making it impossible to verify which changes belong to which session from git history alone. The close-out reports are self-consistent, but an independent reviewer cannot confirm session-level attribution from the diff. This is a process observation, not a code issue.

### Recommendation

No escalation required. The bracket amendment logic is safety-critical but correctly handles failure modes via the existing stop retry + emergency flatten mechanism. The brief unprotected window during amendment is a known trade-off documented in the close-out. The R2G missing guards are defense-in-depth gaps that do not affect correctness (Risk Manager provides the system-level check).

For future consideration:
1. Add zero-R guard to R2G for consistency across all strategies.
2. Consider submit-before-cancel pattern for bracket amendment to eliminate the unprotected window entirely (relevant for live trading hardening).

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "confidence": 0.90,
  "findings": [
    {
      "severity": "MEDIUM",
      "category": "safety",
      "description": "Brief unprotected window during bracket amendment (cancel-then-resubmit pattern). Mitigated by stop-first priority and emergency flatten on retry failure.",
      "file": "argus/execution/order_manager.py",
      "lines": "673-713"
    },
    {
      "severity": "LOW",
      "category": "consistency",
      "description": "Red-to-Green strategy missing zero-R guard and strategy-level concurrent position check. System-level Risk Manager check provides coverage.",
      "file": "argus/strategies/red_to_green.py",
      "lines": null
    },
    {
      "severity": "LOW",
      "category": "process",
      "description": "Squashed S1-S3 commit prevents per-session git attribution. Close-out reports are self-consistent but not independently verifiable from diff.",
      "file": null,
      "lines": null
    }
  ],
  "escalation_criteria_triggered": [],
  "tests_pass": true,
  "test_count": 734,
  "new_tests": 12,
  "protected_files_clean": true,
  "recommendations": [
    "Add zero-R guard to RedToGreenStrategy for defense-in-depth consistency",
    "Consider submit-before-cancel bracket amendment pattern for live trading hardening"
  ]
}
```
