# Dev Log: Sprint 27 Doc Sync

**Date:** 2026-03-22
**Branch:** main

## What Changed

Documentation-only session synchronizing all project docs after Sprint 27
(BacktestEngine Core). 6 sessions, all CLEAR, +85 pytest, no new DECs.

### Documents Updated
- **docs/project-knowledge.md**: Test counts (3,010+620), sprint history table
  (Sprint 27 row), Build Track Queue (Sprint 27 struck, 21.6 next), Backtesting
  bullet (BacktestEngine added), file structure, Expanded Vision (BacktestEngine ✅).
- **docs/architecture.md**: Section 5 intro updated to three-layer approach.
  New section 5.1.6 BacktestEngine with SynchronousEventBus, HistoricalDataFeed,
  engine architecture, walk-forward integration, layer comparison table.
  Directory structure updated with new files.
- **docs/sprint-history.md**: Sprint 27 entry (6 sessions, +85 pytest, all CLEAR).
  Timeline overview (Phase Q). Sprint statistics updated (27 sprints, 3,630 tests).
- **CLAUDE.md**: Active sprint → None, next → 21.6, tests → 3,010, backtest
  section updated, DEF-088 trigger updated, DEF-089 added, CLI command added,
  sprint history ref updated.
- **docs/roadmap.md**: Version bumped to v2.0, current state paragraph updated,
  Sprint 27 marked complete with delivered scope, Sprint 21.6 marked as NEXT
  with updated scope referencing BacktestEngine.

### No Changes Needed
- **docs/decision-log.md**: No new DEC entries (Sprint 27 produced zero decisions).
- **docs/dec-index.md**: No new entries.
- **docs/risk-register.md**: No new risks (Databento rate limit risk did not materialize).

### New Deferred Items
- DEF-089: In-memory ResultsCollector for parallel sweeps (pre-assigned during
  Sprint 27 planning, deferred to Sprint 32).

### Compression Recommendations
- CLAUDE.md Deferred Items table: ~50 resolved items with strikethrough. Consider
  archiving resolved items to a separate file to reduce CLAUDE.md size.
- .claude/rules/sprint_14_rules.md: Header says "Active During Sprint 14" but
  contracts are still valid. Consider renaming to "API Contracts" for clarity.
