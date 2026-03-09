# Tier 2 Review: Sprint 23.3, Session 1 — Universe Manager Wide Pipe + Warm-Up Fix

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context

**Sprint Goal:** Complete the Universe Manager's full-universe architecture (DEC-263,
DEC-299) by feeding it the complete FMP stock-list (~8,000 symbols) instead of the
scanner's 15-symbol watchlist, and fix the warm-up bug where indicator warm-up runs
for excluded symbols.

**What This Sprint Does NOT Do:**
- Does NOT modify `universe_manager.py` — it already accepts any symbol list
- Does NOT modify strategy files, AI layer, Orchestrator, Risk Manager, Event Bus
- Does NOT modify `databento_data_service.py`
- Does NOT add any symbol-pattern pre-filtering or heuristic exclusions
- Does NOT change the `build_viable_universe()` interface or return type
- Does NOT change FMP Scanner behavior

**Regression Checklist:**
| Check | How to Verify |
|-------|---------------|
| All existing tests pass | `python -m pytest tests/ -x -q` — 2,289+ passing |
| Universe Manager disabled path unchanged | Disable UM in config, run UM tests — same behavior |
| FMP Scanner independent operation | Scanner tests pass, scanner not called differently |
| No constrained files modified | `git diff --name-only` check |
| Warm-up only runs for viable symbols when UM enabled | New test + log inspection |
| Fallback to scanner symbols on stock-list failure | New test covers this |
| Fail-closed behavior preserved | Symbols with failed profile fetch excluded from viable set |

**Escalation Criteria:**
Escalate to Tier 3 if:
1. The `build_viable_universe()` interface was changed (should be untouched)
2. Any strategy files, AI layer, Orchestrator, or Risk Manager files were modified
3. The warm-up path for Universe Manager DISABLED does not match pre-session behavior
4. The FMP Scanner's behavior was altered
5. Rate limiting or retry logic could cause startup to exceed 45 minutes
6. New dependencies were added beyond what's already in requirements.txt

## Tier 1 Close-Out Report
[PASTE THE CLOSE-OUT REPORT HERE AFTER THE IMPLEMENTATION SESSION]

## Review Scope
- Diff to review: `git diff HEAD~1` (or the appropriate range for the session's commit)
- Test command: `python -m pytest tests/ -x -q`
- Files that should NOT have been modified:
  - `argus/data/universe_manager.py`
  - `argus/data/databento_data_service.py`
  - Any file in `argus/strategies/`
  - Any file in `argus/ai/`
  - Any file in `argus/core/` (Orchestrator, Risk Manager)
  - Any file in `argus/execution/`
  - Any file in `config/strategies/`

## Session-Specific Review Focus
1. **Verify `fetch_stock_list()` calls the correct endpoint:** Must be
   `/stable/stock-list?apikey={key}`, not any legacy v3/v4 path.
2. **Verify no pre-filtering of stock-list results:** The method should return ALL
   symbols from the response. No regex, pattern matching, or heuristic exclusion.
3. **Verify rate limiting math:** With semaphore(5) and 0.2s per-call spacing,
   the effective rate must not exceed 300 calls/min (5/sec). Check that the
   implementation actually enforces this — a semaphore alone is not sufficient
   if calls complete faster than 0.2s.
4. **Verify retry logic:** Retries on 429 and 5xx only. 4xx (except 429) should
   NOT be retried. Backoff intervals should be 2s, 4s, 8s (exponential).
5. **Verify fallback chain in `main.py`:** Stock-list failure → scanner symbols
   (with WARNING log). Empty viable set → scanner symbols (with ERROR log).
   Universe Manager disabled → scanner symbols (no FMP stock-list call at all).
6. **Verify warm-up input:** When UM is enabled, the warm-up must receive the
   viable symbols returned by `build_viable_universe()`, NOT the raw stock-list
   and NOT the scanner symbols.
7. **Verify fail-closed behavior preserved:** A symbol whose profile fetch failed
   (after retries) must NOT appear in the viable universe.
8. **Verify progress logging:** Log messages every 500 symbols with count, percentage,
   success/failure breakdown, and elapsed time.
9. **Verify no changes to `build_viable_universe()` interface:** The method should
   still accept a list of symbols and return the same structure as before.
10. **Check test coverage:** At least 13 new tests. Tests should cover all three
    fallback paths, retry behavior, concurrency, and progress logging.

## Additional Context
This is an impromptu fix sprint completing the DEC-263 full-universe architecture.
The FMP stable API migration (DEC-298) was a hotfix committed without tests during
a live session — this session adds retroactive test coverage for that migration
alongside the new functionality. The `fmp_reference.py` file was already modified
by the hotfix, so this session's changes build on top of that committed state.
