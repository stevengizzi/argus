# Tier 2 Review: Sprint 21.7, Session 2

## Instructions
READ-ONLY session. Follow .claude/skills/review.md.

## Sprint Spec (Session Scope)
main.py scanner routing updated (scanner_type dispatch from scanner.yaml).
scanner.yaml updated with fmp_scanner section.
watchlist API endpoint populated with scan_source/selection_reason.
api/types.ts WatchlistItem updated.

## Specification by Contradiction
- Must NOT change DatabentoScanner or AlpacaScanner initialization logic
- Must NOT modify any strategy files
- static_symbols fallback must still work when scanner returns nothing

## [PASTE CLOSE-OUT REPORT HERE]

## Sprint-Level Regression Checklist
| Check | Verify |
|-------|--------|
| Static scanner fallback intact | grep "static_symbols" main.py — still referenced |
| Databento branch preserved | git diff main.py — databento elif block unchanged |
| AppState backward compat | existing tests using AppState still pass |
| scanner.yaml replay path | scanner_type: "static" works for replay/backtest |

## Sprint-Level Escalation Criteria
- ESCALATE if: static fallback removed or broken
- ESCALATE if: AppState changes break existing API tests
- ESCALATE if: scanner_type routing uses data_source instead of scanner.yaml key

## Review Scope
- Diff: git diff HEAD~1
- Test command: pytest tests/ -x -q
- Files that MUST NOT have been modified:
  argus/data/databento_scanner.py, argus/data/alpaca_scanner.py,
  any file in argus/strategies/, argus/core/risk_manager.py,
  argus/core/orchestrator.py
