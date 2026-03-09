# Sprint 23.5: Regression Checklist

Run after every session. Every check must pass before proceeding to the next session.

## Core System Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R1 | All existing pytest tests pass | `cd argus && python -m pytest tests/ -x -q` — expect 2,101+ passing | All |
| R2 | All existing Vitest tests pass | `cd argus/ui && npx vitest run` — expect 392+ passing | S5, S6, S6f |
| R3 | No modifications to protected files | `git diff --name-only HEAD~1` — verify none of: `argus/ai/*`, `argus/strategies/*`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/*`, `argus/data/universe_manager.py`, `argus/data/fmp_scanner.py`, `argus/data/fmp_reference.py`, `argus/data/databento_data_service.py`, `argus/analytics/*` | All |
| R4 | No CatalystEvent subscribers registered | `grep -r "subscribe.*CatalystEvent\|CatalystEvent.*subscribe" argus/ --include="*.py"` — expect 0 matches (only publish, no subscribe) | S1, S3 |
| R5 | Event Bus behavior unchanged | Existing event types (CandleEvent, SignalEvent, etc.) continue to work. CatalystEvent is additive only. | S1 |
| R6 | Ruff linting passes | `cd argus && ruff check .` | All |

## Config Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R7 | Config YAML↔Pydantic match | Test loads `config/system.yaml` catalyst section, verifies all keys recognized by CatalystConfig model (no silently ignored keys) | S1 |
| R8 | Default-disabled operation | With `catalyst.enabled: false` (the default), system startup and all existing functionality unchanged | S1 |
| R9 | Missing API key degradation | With `ANTHROPIC_API_KEY` unset: pipeline uses fallback classifier. With `FMP_API_KEY` unset: FMP source disabled, others work. With `FINNHUB_API_KEY` unset: Finnhub source disabled, others work. | S2, S3 |

## API Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R10 | Existing API endpoints unchanged | `grep -r "router\|app.include" argus/api/app.py` — existing routers still registered, intelligence router added alongside (not replacing) | S4 |
| R11 | JWT authentication on new endpoints | All new `/api/v1/catalysts/*` and `/api/v1/premarket/*` endpoints require valid JWT | S4 |
| R12 | API returns correct error codes | GET for nonexistent symbol returns empty list (not 404). GET briefing for date with no brief returns 404. POST generate returns 200 on success. | S4 |

## AI Layer Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R13 | AI Copilot fully functional | No modifications to `argus/ai/` directory. Copilot WebSocket, conversation history, action proposals all unchanged. | All |
| R14 | UsageTracker integration | Classifier calls tracked in `ai_usage` table with correct cost estimates | S3 |
| R15 | Daily cost ceiling enforcement | When `daily_cost_ceiling_usd` is reached, classifier stops calling Claude API and uses fallback | S3 |

## Data Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R16 | Universe Manager read-only | Pipeline reads from UniverseManager but never calls any mutating methods | S3 |
| R17 | FMP Scanner independent | FMP news client is completely separate from FMPScannerSource — different class, different endpoints, no shared state | S2 |
| R18 | SQLite tables isolated | New tables (`catalyst_events`, `intelligence_briefs`) do not alter or depend on existing tables (`ai_conversations`, `ai_messages`, `ai_proposals`, `ai_usage`, `trades`, etc.) | S3 |

## Frontend Integrity

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R19 | Dashboard existing panels unchanged | All existing Dashboard cards (Account, Today Stats, Goals, Market, Regime, Deployment, Universe Status, AI Insight) render correctly | S5 |
| R20 | Orchestrator existing panels unchanged | All existing Orchestrator panels (allocation, regime, decisions, strategy status) render correctly | S5 |
| R21 | Debrief existing tabs unchanged | All existing Debrief sections (Briefings, Documents, Journal) render correctly | S6 |
| R22 | No conditional rendering anti-pattern | New components use same DOM structure with children handling empty states — no conditional skeleton/content swaps creating different React element trees (DEC-established anti-pattern) | S5, S6 |

## Test Coverage

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R23 | New test count meets minimum | Count new test functions — target ~68, minimum 50 | Final session |
| R24 | All external APIs mocked | No test makes live HTTP requests to SEC EDGAR, FMP, Finnhub, or Claude API | S2, S3, S4 |
| R25 | Config validation test exists | Test that loads system.yaml and verifies all `catalyst.*` keys match CatalystConfig.model_fields.keys() | S1 |
