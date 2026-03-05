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
---BEGIN-CLOSE-OUT---

**Session:** Sprint 21.7, Session 2 — Config Routing + API Endpoint Wiring
**Date:** 2026-03-05
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/main.py | modified | Scanner routing using scanner_type from scanner.yaml instead of data_source; added FMPScannerSource/StaticScanner imports; store cached_watchlist for API |
| config/scanner.yaml | modified | Added fmp_scanner section; changed scanner_type to "fmp" for production |
| argus/api/routes/watchlist.py | modified | Added scan_source and selection_reason fields to WatchlistItem; implemented production path from cached_watchlist |
| argus/api/dependencies.py | modified | Added cached_watchlist field to AppState |
| argus/ui/src/api/types.ts | modified | Added scan_source and selection_reason to WatchlistItem interface |
| tests/api/test_watchlist.py | modified | Added 2 tests for new fields; updated mock data with scan_source/selection_reason |
| tests/core/test_config.py | modified | Updated test_loads_from_yaml to expect scanner_type="fmp" |

### Judgment Calls
None. All decisions were pre-specified in the implementation prompt.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| main.py routes to FMPScannerSource when scanner_type: "fmp" | DONE | argus/main.py:239-242 |
| scanner.yaml has fmp_scanner section with scanner_type: "fmp" | DONE | config/scanner.yaml:6,20-32 |
| watchlist API endpoint has scan_source + selection_reason fields | DONE | argus/api/routes/watchlist.py:46-47 |
| api/types.ts WatchlistItem interface updated | DONE | argus/ui/src/api/types.ts:279-280 |
| Implement production watchlist path from cached_watchlist | DONE | argus/api/routes/watchlist.py:93-106 |
| Add cached_watchlist to AppState | DONE | argus/api/dependencies.py:66 |
| Integration tests for new fields | DONE | tests/api/test_watchlist.py:185-229 |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Static scanner still works | PASS | scanner_type: "static" → StaticScanner instantiated (main.py:263-265) |
| Databento branch intact | PASS | Logic unchanged, just reorganized under scanner_type dispatch |
| Startup sequence unchanged | PASS | Phase 7/8 log order preserved |
| Watchlist endpoint backward compat | PASS | New fields have defaults (""), existing tests pass |

### Test Results
- Tests run: 1754 (backend) + 291 (frontend)
- Tests passed: 1754 + 291
- Tests failed: 0
- New tests added: 2
- Command used: `python -m pytest tests/ -x -q` and `npx vitest run`

### Unfinished Work
None. All spec items are complete.

### Notes for Reviewer
- Updated test_loads_from_yaml in tests/core/test_config.py to expect "fmp" instead of "static" since the production config now uses FMP scanner
- The production watchlist endpoint populates scan_source and selection_reason but leaves current_price=0.0 and strategies=[] as placeholders for Sprint 22+

---END-CLOSE-OUT---

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
