# Sprint 25: Regression Checklist

## Trading Pipeline Integrity

| Check | How to Verify |
|-------|---------------|
| No files modified in `argus/strategies/` | `git diff --name-only HEAD~N \| grep strategies/` returns empty |
| No files modified in `argus/core/orchestrator.py` or `argus/core/risk_manager.py` | `git diff --name-only HEAD~N \| grep -E 'orchestrator\|risk_manager'` returns empty |
| No files modified in `argus/execution/` | `git diff --name-only HEAD~N \| grep execution/` returns empty |
| No files modified in `argus/intelligence/quality_engine.py` or `position_sizer.py` | Grep check returns empty |
| No files modified in `argus/intelligence/catalyst/` | Grep check returns empty |
| No files modified in `argus/data/` | Grep check returns empty |
| No files modified in `argus/ai/` | Grep check returns empty |
| No new Event Bus subscribers added | `grep -r "subscribe\|add_subscriber" argus/ --include="*.py"` count unchanged |
| Evaluation telemetry schema unchanged | `EvaluationEventStore` table DDL unchanged in git diff |

## Existing Pages

| Check | How to Verify |
|-------|---------------|
| Dashboard page loads and renders | Start dev server, navigate to Dashboard, no errors in console |
| Trades page loads and renders | Navigate to Trades, no errors |
| Performance page loads and renders | Navigate to Performance, no errors |
| Orchestrator page loads and renders | Navigate to Orchestrator, Decision Stream still works |
| Pattern Library page loads and renders | Navigate to Pattern Library, no errors |
| The Debrief page loads and renders | Navigate to Debrief, no errors |
| System page loads and renders | Navigate to System, no errors |
| AI Copilot still functional | Open Copilot panel, send test message, response received |

## API and WebSocket

| Check | How to Verify |
|-------|---------------|
| Existing API endpoints unchanged | `python -m pytest tests/api/ -x -q` passes |
| `/ws/v1/ai/chat` WebSocket still functional | Copilot chat test (above) |
| New Observatory endpoints JWT-protected | `curl` without auth returns 401 |
| Observatory WS does not affect AI WS | Both connections active simultaneously without interference |

## Frontend Build

| Check | How to Verify |
|-------|---------------|
| Three.js code-split (not in main bundle) | `npm run build`, check chunk sizes — Three.js in separate lazy chunk |
| Non-Observatory page load time not degraded | Lighthouse score on Dashboard, compare before/after |
| All existing Vitest tests pass | `cd argus/ui && npx vitest run` |
| TypeScript strict mode passes | `cd argus/ui && npx tsc --noEmit` |

## Config

| Check | How to Verify |
|-------|---------------|
| New observatory config fields verified against ObservatoryConfig Pydantic model | Config validation test: all YAML keys recognized by model, no silently ignored keys |
| System starts with observatory.enabled: false | Start with config disabled, no errors, no Observatory WS endpoint mounted |
| System starts with observatory section absent from YAML | Defaults applied, no crash |

## Tests

| Check | How to Verify |
|-------|---------------|
| All pytest pass | `python -m pytest tests/ --ignore=tests/test_main.py -x -q` |
| All Vitest pass | `cd argus/ui && npx vitest run` |
| Test count does not decrease | Compare against baseline: 2,768 pytest + 523 Vitest |
