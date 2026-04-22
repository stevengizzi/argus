# FIX-17-claude-rules — Tier 2 Review

> Tier 2 independent review produced per `workflow/claude/skills/review.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-17-claude-rules (.claude/rules refresh; 16 H3 findings)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-21
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | Commit `451b444` touches exactly the 9 declared rule files (8 edits + 1 rename target) and 1 audit markdown back-annotation. 149 deletions / 794 insertions. No production code, no tests. Sibling FIX-15 / FIX-00 unstaged changes in the working tree were correctly NOT staged into this commit. |
| Close-Out Accuracy | PASS | Change manifest matches `git show --stat` exactly. Scope Verification table is accurate. Judgment calls (RENAME over DELETE, ARGUS-side-only for H3-13, soft CLAUDE.md size guidance, 15-strategy cross-ref) all conform to the audit's stated preferences. CSV-absorbed-into-sibling-commit disclosure is honest and verifiable (9dd44f2 contains 16 `RESOLVED FIX-17` markers in `phase-2-review.csv`). |
| Test Health | PASS | On clean FIX-17 checkout: `python -m pytest --ignore=tests/test_main.py -n auto -q` → **4,934 passed** in 122.4s. Zero failures. DEF-150 did not trigger on this run because the clock was outside its minute-0/1 window. Net delta vs Phase 3 baseline (4,933 passed, 1 failed): +1 test passing. Close-out's reported "1 failed = DEF-150 flake" is consistent with documented DEF-150 behavior at the close-out's clock. |
| Regression Checklist | PASS | All 8 campaign-level checks PASS or N/A (see Findings). No new regressions attributable to this commit. |
| Architectural Compliance | PASS | Rule updates are consistent with established patterns. New sections (Config-Gating, Separate-DB, Fire-and-Forget, Trust-Cache-on-Startup, Non-Bypassable Validation, Domain Model, Margin CB, Broker-Confirmed Reconciliation, PatternModule Conventions, Regime Gating, Shadow Mode, Telemetry Wire-Up, Serialization, ThrottledLogger, Time/Timezones, Vitest) each cite the precedent DEC / Sprint / DEF. Cross-references between files (architecture ↔ risk-rules, architecture ↔ code-style, testing ↔ risk-rules, doc-updates → doc-sync skill) are consistent. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL findings (10 MEDIUM + 5 LOW + 1 COSMETIC); pytest net delta +1 ≥ 0; no scope violation in the final commit; only the expected DEF-150 flake surface observed (and not even that on the clean-checkout run); no Rule-4 sensitive file touched (doc-only); all 14 in-scope back-annotations present. |

### Findings

**LOW-1 — `code-style.md` ThrottledLogger import path is wrong.**
`code-style.md` lines 128 and 132 reference the module as `argus/utils/throttled_logger.py`, but the actual module is `argus/utils/log_throttle.py`. The copy-paste example at line 132 (`from argus.utils.throttled_logger import ThrottledLogger`) will produce `ModuleNotFoundError`. All real call sites in the codebase use `from argus.utils.log_throttle import ThrottledLogger` — verified at `argus/core/risk_manager.py:31`, `argus/execution/order_manager.py:59`, `argus/execution/ibkr_broker.py:41`, plus Sprint 29.5 review and test files.
**Recommendation:** one-line fix in the next doc-sync pass — correct both the bracketed link target at line 128 and the `from argus.utils...` import at line 132 to `log_throttle`. Not a blocker for CLEAR.

**LOW-2 — `api-conventions.md` minor OrderManager surface drift.**
`api-conventions.md` lines 120–124 claim three methods on OrderManager:
- `get_managed_positions(self) -> list[ManagedPosition]` — actual return type is `dict[str, list[ManagedPosition]]` (see `argus/execution/order_manager.py:2833`).
- `get_managed_position(self, symbol: str) -> ManagedPosition | None` — **this method does not exist** (`grep 'def get_managed_position\b'` returns no matches).
- `async def close_position(self, symbol: str) -> None` — actual signature is `async def close_position(self, symbol: str, reason: str = "api_close") -> bool`.
The file includes a self-disclaimer ("when it disagrees with the code, the code wins and this file should be updated") which is the correct stance. Severity is LOW because the file is explicitly a crib sheet.
**Recommendation:** next doc-sync pass — correct `get_managed_positions` return type, drop the non-existent singular `get_managed_position`, add the `reason` parameter and `-> bool` return on `close_position`.

**INFO-1 — Rename lineage claim is overstated.**
The close-out states `git log --follow .claude/rules/api-conventions.md` "preserves lineage." In practice git sees a `D sprint_14_rules.md` + `A api-conventions.md` because the content rewrite was extensive enough that even `-M50` rename detection doesn't link them. `--follow` only returns the single new commit. Cosmetic — the content refresh was delivered correctly. The commit message preserves human-discoverable provenance.
**Recommendation:** no action required.

**INFO-2 — Clean working tree not achieved at review time due to concurrent sibling sessions.**
The close-out disclosed an unstaged change in `tests/sprint_runner/test_state.py`. On re-inspection at review time there are additional unstaged changes from concurrent FIX-15 and FIX-00 sessions (counterfactual.py, quality_engine.py, startup.py, main.py, config YAMLs, several new `tests/test_fix01_*.py` files, and a staged `sprint_14_rules.md`). These are unrelated to FIX-17 and were correctly excluded from commit `451b444`. Initial test run during this review mixed these changes in and produced 4 spurious failures (2 counterfactual wiring + 2 quality engine) related to FIX-15 / FIX-01's mock data. Re-running after `git stash -u` on clean HEAD produced the expected 4,934 passed / 0 failed.
**Recommendation:** no action required for FIX-17. Sibling sessions need to reconcile their working-tree state before their own close-out, but that's their problem.

**Regression checklist results (from the 8 campaign-level checks):**
1. pytest net delta ≥ 0 against baseline 4,933 passed → **PASS** (+1 vs baseline on clean FIX-17 checkout).
2. DEF-150 flake remains the only pre-existing failure (no new regressions) → **PASS** (DEF-150 did not trigger at review time; no other failures).
3. No file outside this session's declared Scope was modified in the final commit → **PASS** (9 rule files + 1 audit markdown per `git show 451b444 --stat`).
4. Every resolved finding back-annotated with `**RESOLVED FIX-17-claude-rules**` → **PASS** (14 of 14 in-scope rows in `p1-h3-claude-rules.md` §14; rows 15–16 are metarepo-only. CSV has 16 markers across H3-01..H3-16 — absorbed into sibling FIX-15 commit `9dd44f2` per close-out disclosure).
5. Every DEF closure recorded in CLAUDE.md → **PASS (N/A)** (no DEF closed or opened by this session).
6. Every new DEF/DEC referenced in commit message bullets → **PASS (N/A)** (no new DEF/DEC created).
7. `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted → **N/A** (no such findings in FIX-17 scope).
8. `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md → **N/A** (no such findings in FIX-17 scope).

### Recommendation
Proceed to the next session. FIX-17 is a high-quality, surgical doc refresh that closed all 14 in-scope H3 findings with complete and accurate back-annotation. The two LOW findings (wrong ThrottledLogger import path; OrderManager surface drift) are worth catching in the next doc-sync pass but do not rise to CONCERNS — neither affects runtime behavior and one is explicitly hedged by the file's own "code wins" disclaimer. The test baseline improved (+1 vs Phase 3 baseline on clean checkout). Several durable patterns (non-bypassable validation, fire-and-forget writes, trust-cache-on-startup, shadow-first validation, PatternModule conventions) were codified for the first time. The CSV back-annotation absorption into the sibling FIX-15 commit is a process wart the close-out disclosed honestly; the authoritative markdown audit report is under the correct FIX-17 commit.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-17-claude-rules",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "code-style.md lines 128 and 132 reference the module as argus/utils/throttled_logger.py, but the actual module is argus/utils/log_throttle.py. The `from argus.utils.throttled_logger import ThrottledLogger` example will produce ModuleNotFoundError. All real call sites use `from argus.utils.log_throttle import ThrottledLogger`.",
      "severity": "LOW",
      "category": "OTHER",
      "file": ".claude/rules/code-style.md",
      "recommendation": "Next doc-sync pass: correct the import path to argus.utils.log_throttle (both the bracketed link at line 128 and the code example at line 132)."
    },
    {
      "description": "api-conventions.md OrderManager Query Surface section claims (1) get_managed_positions returns list[ManagedPosition] (actual: dict[str, list[ManagedPosition]]), (2) a singular get_managed_position(symbol) method exists (it does not), and (3) close_position signature is `(self, symbol: str) -> None` (actual: `(self, symbol: str, reason: str = 'api_close') -> bool`). The file has an explicit 'code wins' disclaimer which mitigates severity.",
      "severity": "LOW",
      "category": "OTHER",
      "file": ".claude/rules/api-conventions.md",
      "recommendation": "Next doc-sync pass: refresh the three method signatures to match argus/execution/order_manager.py. Drop the non-existent get_managed_position (singular)."
    },
    {
      "description": "Close-out claims `git log --follow .claude/rules/api-conventions.md` preserves lineage from sprint_14_rules.md. Git rename detection (even with -M50) does not link the two files due to extensive content rewrite; --follow only returns the single new commit. Cosmetic-only; the commit message preserves human-discoverable provenance.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "docs/audits/audit-2026-04-21/phase-3-prompts/FIX-17-claude-rules.md",
      "recommendation": "No action required."
    },
    {
      "description": "Working tree contains unstaged changes from concurrent FIX-00 and FIX-15 sessions (argus/intelligence/*, scoring_fingerprint.py, counterfactual wiring, config YAMLs, new test files). These are outside FIX-17 and were correctly excluded from commit 451b444. Full-suite pytest over the dirty tree surfaces 4 unrelated failures which disappear when stashed; clean FIX-17 checkout yields 4,934 / 0.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "working tree (not in commit 451b444)",
      "recommendation": "Owning sibling sessions should reconcile their working-tree state before their own close-out."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 16 H3 findings addressed. All 14 in-scope audit rows back-annotated in p1-h3-claude-rules.md. The 2 out-of-scope rows (rows 15–16) are metarepo-only and correctly excluded per Universal RULE-018. CSV back-annotation absorbed into sibling FIX-15 commit 9dd44f2 (disclosed honestly in close-out commit message).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    ".claude/rules/architecture.md",
    ".claude/rules/backtesting.md",
    ".claude/rules/code-style.md",
    ".claude/rules/doc-updates.md",
    ".claude/rules/risk-rules.md",
    ".claude/rules/testing.md",
    ".claude/rules/trading-strategies.md",
    ".claude/rules/api-conventions.md",
    ".claude/rules/sprint_14_rules.md (deleted)",
    "docs/audits/audit-2026-04-21/p1-h3-claude-rules.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4934,
    "new_tests_adequate": true,
    "test_quality_notes": "Doc-only change — no new tests required. Full suite on clean FIX-17 checkout: 4,934 passed in 122.4s with 0 failures (DEF-150 flake did not trigger outside its minute-0/1 window). Net delta vs Phase 3 baseline of 4,933 passed / 1 failed: +1 test passing."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0", "passed": true, "notes": "4,934 passed, 0 failed on clean checkout; net +1 vs baseline"},
      {"check": "No file outside declared scope modified", "passed": true, "notes": "Commit touches only 9 .claude/rules/*.md + 1 audit markdown"},
      {"check": "DEF-150 remains the only expected pre-existing failure", "passed": true, "notes": "DEF-150 did not trigger this run; no other failures appeared"},
      {"check": "Rule-4 sensitive file touched without authorization", "passed": true, "notes": "No production code or sensitive files touched"},
      {"check": "Every resolved finding back-annotated", "passed": true, "notes": "14 of 14 in-scope rows marked RESOLVED FIX-17-claude-rules in p1-h3-claude-rules.md; rows 15–16 metarepo-only"},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "N/A — no DEF closed or opened by this session"},
      {"check": "Every new DEF/DEC referenced in commit bullets", "passed": true, "notes": "N/A — no new DEF/DEC created"},
      {"check": "read-only-no-fix-needed findings verified OR promoted", "passed": true, "notes": "N/A — no such findings in this FIX's scope"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session.",
    "Next doc-sync pass: fix the ThrottledLogger import path in code-style.md (argus.utils.throttled_logger → argus.utils.log_throttle) and the OrderManager surface drift in api-conventions.md (get_managed_positions return type, drop get_managed_position singular, close_position signature)."
  ]
}
```
