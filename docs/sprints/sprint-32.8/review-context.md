# Sprint 32.8 Review Context

This file is referenced by all Tier 2 review prompts for Sprint 32.8.

## Sprint Spec
See: `docs/sprints/sprint-32.8/sprint-spec.md`

## Specification by Contradiction
See: `docs/sprints/sprint-32.8/spec-by-contradiction.md`

## Sprint-Level Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | All 12 strategies remain registered and active | Startup log shows 12 strategies created + registered |
| 2 | Arena WebSocket still delivers all 5 message types | Run `useArenaWebSocket.test.ts` — auth, tick, candle, opened, closed, stats |
| 3 | Arena REST endpoints still return position + candle data | Run `ArenaPage.test.tsx` |
| 4 | Dashboard renders all data (repositioned, not missing) | Visual check: equity, P&L, positions, timeline, signal quality, AI insight, learning loop all visible |
| 5 | Live Trades tab retains all existing functionality | Sort, filter, outcome toggle, date range, infinite scroll, trade detail panel |
| 6 | Shadow Trades tab shows all shadow trade data | Strategy filter, rejection stage filter, date range, trade list |
| 7 | Existing pytest baseline passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |
| 8 | Existing Vitest baseline passes | `cd argus/ui && npx vitest run` |
| 9 | No Python files modified outside arena_ws.py and intraday_candle_store.py | `git diff --name-only` check |
| 10 | No event definitions changed | `git diff argus/core/events.py` shows no changes |
| 11 | No database schema changes | `git diff` shows no `.db` file creation or ALTER TABLE |
| 12 | No config file changes | `git diff config/` shows no changes |

## Sprint-Level Escalation Criteria

Escalate to Tier 3 (human review required) if:

1. **Trading engine modification** — any change to files in `argus/core/`, `argus/strategies/`, `argus/execution/` (except `arena_ws.py`), or `argus/data/` (except `intraday_candle_store.py`)
2. **Event definition change** — any modification to `argus/core/events.py`
3. **API contract change** — any change to REST endpoint signatures or WebSocket message schemas that would break existing frontend consumers
4. **Performance regression** — Arena WS TickEvent subscription causing measurable CPU increase visible in system monitoring
5. **Data loss** — Dashboard refactor accidentally removing access to any data that was previously visible (relocated is fine, removed is not)
6. **Test baseline regression** — more than 2 pre-existing test failures (DEF-137 and DEF-138 are known pre-existing)
