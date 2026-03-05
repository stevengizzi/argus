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
