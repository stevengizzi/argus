# Tier 2 Review: Sprint 21.7, Session 1

## Instructions
READ-ONLY session. Follow .claude/skills/review.md.
Do NOT modify any files.

## Sprint Spec (Session Scope)
New file: argus/data/fmp_scanner.py with FMPScannerSource(Scanner).
Extended: argus/core/events.py WatchlistItem with scan_source + selection_reason.
New tests: tests/data/test_fmp_scanner.py

## Specification by Contradiction
- Must NOT modify DatabentoScanner, AlpacaScanner, StaticScanner
- Must NOT modify any strategy files
- Must NOT use httpx (dev-only dep)
- Must NOT store API key outside of runtime env read in start()

## [PASTE CLOSE-OUT REPORT HERE]
---BEGIN-CLOSE-OUT---

**Session:** Sprint 21.7 — Session 1: FMPScannerSource + WatchlistItem Extension
**Date:** 2026-03-05
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/events.py | modified | Added scan_source and selection_reason fields to WatchlistItem dataclass with empty-string defaults for backward compatibility |
| argus/data/fmp_scanner.py | added | New FMP scanner module with FMPScannerConfig (plain class) and FMPScannerSource implementing Scanner ABC |
| tests/data/test_fmp_scanner.py | added | 15 test cases covering all FMP scanner functionality as specified |

### Judgment Calls
None

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| WatchlistItem scan_source field (default="") | DONE | events.py:136 |
| WatchlistItem selection_reason field (default="") | DONE | events.py:137 |
| FMPScannerConfig plain class (not Pydantic) | DONE | fmp_scanner.py:25-43 |
| FMPScannerSource implements Scanner ABC | DONE | fmp_scanner.py:46-236 |
| start() reads API key from env, raises if missing | DONE | fmp_scanner.py:66-77 |
| stop() clears API key | DONE | fmp_scanner.py:79-82 |
| scan() calls _fetch_candidates with fallback | DONE | fmp_scanner.py:84-111 |
| _fetch_candidates concurrent endpoint calls | DONE | fmp_scanner.py:113-165 |
| Deduplication (gainers/losers win over actives) | DONE | fmp_scanner.py:142-157 |
| Price filter (min_price <= price <= max_price) | DONE | fmp_scanner.py:196-197 |
| selection_reason format (gap_up_X.X%, gap_down_X.X%, high_volume) | DONE | fmp_scanner.py:200-208 |
| gap_pct = changesPercentage / 100 | DONE | fmp_scanner.py:201 |
| _fallback_candidates with scan_source="fmp_fallback" | DONE | fmp_scanner.py:225-231 |
| All 15 new tests pass | DONE | tests/data/test_fmp_scanner.py |
| Full test suite passes | DONE | 1,752 tests passing |
| ruff check passes | DONE | No errors |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| WatchlistItem backward compat (core/data tests) | PASS | 514 tests pass in tests/core/ tests/data/ |
| Scanner ABC compliance | PASS | isinstance(scanner, Scanner) returns True |
| No imports from new file in existing files | PASS | grep -r fmp_scanner argus/ returns 0 hits |

### Test Results
- Tests run: 1,752
- Tests passed: 1,752
- Tests failed: 0
- New tests added: 15
- Command used: `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
None

---END-CLOSE-OUT---

## Sprint-Level Regression Checklist
| Check | How to Verify |
|-------|---------------|
| StaticScanner unchanged | git diff argus/data/scanner.py |
| DatabentoScanner unchanged | git diff argus/data/databento_scanner.py |
| WatchlistItem backward compat | existing tests that construct WatchlistItem() still pass |
| events.py new fields have defaults | WatchlistItem() with no args succeeds |

## Sprint-Level Escalation Criteria
- ESCALATE if: WatchlistItem changes break any existing test
- ESCALATE if: FMPScannerSource does not implement full Scanner ABC
- ESCALATE if: API key is stored as an instance variable set at construction (not at start())
- ESCALATE if: aiohttp session is created at module level (not in method scope)

## Review Scope
- Diff: git diff HEAD~1
- Test command: pytest tests/data/test_fmp_scanner.py -v && pytest tests/ -x -q
- Files that MUST NOT have been modified:
  argus/data/databento_scanner.py, argus/data/alpaca_scanner.py,
  argus/data/scanner.py (Scanner ABC — only WatchlistItem import change allowed),
  any file in argus/strategies/
