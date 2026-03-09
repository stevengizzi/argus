# Sprint 23.5, Session 4: API Routes + Briefing Generator

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/models.py` (data models — ClassifiedCatalyst, IntelligenceBrief)
   - `argus/intelligence/storage.py` (S3 output — CatalystStorage methods)
   - `argus/intelligence/classifier.py` (S3 output — for briefing reuse)
   - `argus/ai/client.py` (ClaudeClient for briefing generation)
   - `argus/api/app.py` (existing router registration pattern)
   - `argus/api/routes.py` (existing endpoint patterns — auth, response format)
2. Run the test suite: `cd argus && python -m pytest tests/ -x -q`
   Expected: 2,101+ tests + S1–S3 tests, all passing
3. Verify S3 artifacts exist: `ls argus/intelligence/storage.py argus/intelligence/classifier.py`

## Objective
Expose catalyst data via REST API endpoints and build the Claude-powered pre-market intelligence brief generator. This session makes the pipeline's data accessible to the frontend (Sessions 5–6).

## Requirements

1. **Create `argus/api/intelligence_routes.py`**: FastAPI router for intelligence endpoints.
   - Router prefix: `/api/v1` (catalysts and premarket endpoints).
   - All endpoints require JWT authentication (use existing `get_current_user` dependency from `argus/api/auth.py`).
   - **`GET /api/v1/catalysts/{symbol}`**: Returns catalysts for a symbol.
     - Query params: `limit: int = 50`, `since: str | None` (ISO datetime, filter by published_at).
     - Response: `{"catalysts": [...], "count": int, "symbol": str}`
     - If no catalysts: return `{"catalysts": [], "count": 0, "symbol": symbol}` (200, not 404).
   - **`GET /api/v1/catalysts/recent`**: Returns recent catalysts across all symbols.
     - Query params: `limit: int = 50`, `offset: int = 0`.
     - Response: `{"catalysts": [...], "count": int, "total": int}`
   - **`GET /api/v1/premarket/briefing`**: Returns the most recent briefing for today.
     - Query params: `date: str | None` (YYYY-MM-DD, defaults to today ET).
     - Response: full IntelligenceBrief as JSON.
     - If no briefing for date: return 404 with `{"detail": "No briefing found for {date}"}`.
   - **`GET /api/v1/premarket/briefing/history`**: Returns past briefings.
     - Query params: `limit: int = 30`.
     - Response: `{"briefings": [...], "count": int}`
   - **`POST /api/v1/premarket/briefing/generate`**: Trigger briefing generation.
     - Request body: `{"symbols": list[str] | None}` (optional — if null, uses watchlist).
     - Response: generated IntelligenceBrief as JSON.
     - If generation fails: return 500 with error detail.
   - Response models should be Pydantic models for OpenAPI schema generation.

2. **Create `argus/intelligence/briefing.py`**: BriefingGenerator class.
   - Constructor takes: `ClaudeClient`, `CatalystStorage`, `UsageTracker`, `BriefingConfig`.
   - **`async def generate_brief(symbols: list[str], date: str | None = None) -> IntelligenceBrief`**:
     1. Determine date (default: today ET).
     2. Fetch all catalysts for the given symbols from storage (last 24 hours).
     3. If no catalysts found, generate a minimal brief: "No material catalysts detected for {date}."
     4. Group catalysts by category: earnings, insider trades, analyst actions, etc.
     5. Build a Claude prompt with the grouped catalysts, requesting a structured markdown brief with 5 sections:
        - **Top Catalysts**: Ranked by quality_score, top 5–10 items with symbol, headline, quality score, and one-sentence summary.
        - **Earnings Calendar**: Any earnings-related catalysts.
        - **Insider Activity**: Form 4 filings, insider trades.
        - **Analyst Actions**: Upgrades, downgrades, price target changes.
        - **Risk Alerts**: Any catalysts with quality_score > 70 and trading_relevance "high" that suggest caution.
     6. Call Claude API to generate the narrative brief.
     7. Track cost via UsageTracker.
     8. Create IntelligenceBrief object and store via CatalystStorage.
     9. Return the brief.
   - Brief `content` field is markdown. Use headers (##), bullet points, bold for symbols.
   - Cap symbols at `briefing.max_symbols` from config (default 30).

3. **Modify `argus/api/app.py`**: Register the intelligence router.
   - Import `intelligence_routes` router.
   - Register alongside existing routers using `app.include_router()`.
   - The intelligence router should be registered only when the app starts (same pattern as other routers).
   - Add the CatalystStorage, BriefingGenerator as app state dependencies (following existing patterns for how routes access services).

## Constraints
- Do NOT modify any existing route files (`argus/api/routes.py`, `argus/api/ai_routes.py`, `argus/api/debrief_routes.py`, etc.)
- Do NOT modify `argus/intelligence/classifier.py` or `argus/intelligence/storage.py` (only read from them)
- Do NOT add WebSocket endpoints for catalyst streaming
- All Claude API calls in briefing generation must be mocked in tests
- Use existing JWT auth dependency — do not create new auth logic

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/api/test_intelligence_routes.py` and `tests/intelligence/test_briefing.py`:
  - API tests:
    1. GET catalysts/{symbol}: returns catalysts for known symbol
    2. GET catalysts/{symbol}: returns empty list for unknown symbol (200, not 404)
    3. GET catalysts/recent: returns recent catalysts with pagination
    4. GET premarket/briefing: returns today's briefing
    5. GET premarket/briefing: returns 404 when no briefing exists
    6. GET premarket/briefing/history: returns ordered list
    7. POST premarket/briefing/generate: generates and returns briefing
    8. All endpoints: 401 without JWT token
  - Briefing tests:
    1. Generate brief with catalysts: produces 5-section markdown
    2. Generate brief without catalysts: produces "no catalysts" message
    3. Cost tracked via UsageTracker
    4. Symbols capped at max_symbols config
- Minimum new test count: 12
- Test command: `python -m pytest tests/api/test_intelligence_routes.py tests/intelligence/test_briefing.py -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥12)
- [ ] All Claude API calls mocked in tests
- [ ] JWT auth required on all new endpoints
- [ ] Existing API routes unchanged (verified by existing tests passing)
- [ ] Ruff linting passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing routes unchanged | `git diff argus/api/routes.py argus/api/ai_routes.py argus/api/debrief_routes.py` returns empty |
| Intelligence router registered | `grep "intelligence" argus/api/app.py` shows router registration |
| JWT auth on all endpoints | Every endpoint function has `current_user` dependency parameter |
| No WebSocket additions | `grep "websocket\|WebSocket" argus/api/intelligence_routes.py` returns 0 |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/rsprint-23.5-eview-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`
