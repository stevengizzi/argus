# Sprint 23.5, Session 3: Classifier + Storage + Pipeline Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/models.py` (data models)
   - `argus/intelligence/config.py` (CatalystConfig)
   - `argus/intelligence/sources/__init__.py` (CatalystSource ABC)
   - `argus/ai/client.py` (ClaudeClient — how to send messages)
   - `argus/ai/usage.py` (UsageTracker — how to track costs)
   - `argus/core/events.py` (Event Bus + CatalystEvent)
2. Run the test suite: `cd argus && python -m pytest tests/ -x -q`
   Expected: 2,101+ tests + S1 + S2 tests, all passing
3. Verify S2 artifacts exist: `ls argus/intelligence/sources/sec_edgar.py argus/intelligence/sources/fmp_news.py argus/intelligence/sources/finnhub.py`

## Objective
Build the Claude API batch classifier with dynamic sizing, SQLite storage for catalysts and classifications, and wire the complete CatalystPipeline: sources → dedup → classify → store → Event Bus publish. This is the integration session that makes the pipeline functional end-to-end.

## Requirements

1. **Create `argus/intelligence/classifier.py`**: CatalystClassifier class.
   - Constructor takes: `ClaudeClient`, `UsageTracker`, `CatalystConfig`.
   - **`classify_batch(items: list[CatalystRawItem]) -> list[ClassifiedCatalyst]`**:
     - Deduplicate items by headline hash (using `compute_headline_hash`).
     - Check classification cache — if hash exists and TTL not expired, return cached classification.
     - Group uncached items into batches. Dynamic sizing: the prompt instructs Claude to process them, but the code groups into chunks of `max_batch_size` (default 20).
     - For each batch, call Claude API with classification prompt (see below).
     - Parse Claude's structured JSON response into `CatalystClassification` objects.
     - Check daily cost ceiling via `UsageTracker.get_daily_total()`. If ceiling reached, switch remaining items to fallback classifier.
     - Cache new classifications by headline hash.
     - Return list of `ClassifiedCatalyst` (raw item + classification).
   - **Classification Prompt**: System message instructs Claude to classify each headline into one of 8 categories, assign quality_score 0–100, provide a one-sentence trading-relevant summary, and rate trading_relevance as high/medium/low/none. Response must be valid JSON array. Include few-shot examples in the system prompt:
     - "AAPL beats Q3 earnings, revenue up 12%" → earnings, 85, "Apple exceeded expectations with strong revenue growth", high
     - "CEO of XYZ purchases 50,000 shares" → insider_trade, 72, "Significant insider buying signals management confidence", high
     - "Company updates corporate governance policy" → corporate_event, 15, "Routine governance update with no trading impact", none
   - **Fallback Classifier** (`_classify_fallback(item: CatalystRawItem) -> CatalystClassification`):
     - Keyword-based classification: "earnings|revenue|EPS|profit|loss" → earnings; "insider|Form 4|purchase|sale|director|officer" → insider_trade; "8-K|10-K|10-Q|SEC|filing" → sec_filing; "upgrade|downgrade|analyst|target|rating" → analyst_action; "FDA|approval|regulatory" → regulatory; "merger|acquisition|buyout|IPO|offering" → corporate_event.
     - Default: "other" with quality_score 25 and trading_relevance "low".
     - Always sets `classified_by="fallback"`.

2. **Create `argus/intelligence/storage.py`**: CatalystStorage class.
   - Uses `aiosqlite` following existing patterns (see `argus/ai/conversations.py` for pattern).
   - **Tables**:
     - `catalyst_events`: id (TEXT PK, ULID), symbol, catalyst_type, quality_score, headline, summary, source, source_url, filing_type, headline_hash, published_at, classified_at, classified_by, trading_relevance, created_at.
     - `catalyst_classifications_cache`: headline_hash (TEXT PK), category, quality_score, summary, trading_relevance, classified_by, cached_at.
     - `intelligence_briefs`: id (TEXT PK, ULID), date (TEXT), brief_type (TEXT), content (TEXT), symbols_json (TEXT — JSON array), catalyst_count (INT), generated_at (TEXT), generation_cost_usd (REAL).
   - **Methods**:
     - `initialize()` — create tables if not exist.
     - `store_catalyst(catalyst: ClassifiedCatalyst) -> str` — store and return ULID.
     - `get_catalysts_by_symbol(symbol: str, limit: int = 50) -> list[ClassifiedCatalyst]`.
     - `get_recent_catalysts(limit: int = 50, offset: int = 0) -> list[ClassifiedCatalyst]`.
     - `get_cached_classification(headline_hash: str) -> CatalystClassification | None`.
     - `cache_classification(headline_hash: str, classification: CatalystClassification)`.
     - `is_cache_valid(headline_hash: str, ttl_hours: int) -> bool`.
     - `store_brief(brief: IntelligenceBrief) -> str` — store and return ULID.
     - `get_brief(date: str, brief_type: str = "premarket") -> IntelligenceBrief | None`.
     - `get_brief_history(limit: int = 30) -> list[IntelligenceBrief]`.
   - Database path: `{data_dir}/catalyst.db` (separate from main DB, following the AI layer pattern with `ai.db`).

3. **Modify `argus/intelligence/__init__.py`**: Add CatalystPipeline class.
   - Constructor takes: `sources: list[CatalystSource]`, `classifier: CatalystClassifier`, `storage: CatalystStorage`, `event_bus: EventBus`, `config: CatalystConfig`.
   - **`async def run_poll(symbols: list[str]) -> list[ClassifiedCatalyst]`**:
     1. Fetch raw items from all enabled sources concurrently (`asyncio.gather`).
     2. Flatten results. Deduplicate across sources by headline hash (first occurrence wins).
     3. Classify batch via `classifier.classify_batch()`.
     4. Store each classified catalyst via `storage.store_catalyst()`.
     5. Publish `CatalystEvent` on Event Bus for each newly classified item.
     6. Return the classified catalysts.
   - **`async def start()`**: Initialize storage, start all sources.
   - **`async def stop()`**: Stop all sources.
   - Log: total items fetched per source, dedup count, classified count, fallback count, cost.

## Constraints
- Do NOT modify any files outside `argus/intelligence/`
- Do NOT register any Event Bus subscribers for CatalystEvent — only publish
- Do NOT make live Claude API calls in tests — mock ClaudeClient responses
- Do NOT import or use any strategy, risk manager, or orchestrator classes
- Use `python-ulid` for IDs following existing pattern (DEC-026)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/intelligence/`:
  - `test_classifier.py`:
    1. Classify batch: parses Claude JSON response correctly
    2. Dynamic batching: respects max_batch_size
    3. Cache hit: cached headline returns cached classification
    4. Cache miss: uncached headline calls Claude API
    5. Fallback: keywords correctly map to categories (test each category)
    6. Fallback: unknown headline → "other"
    7. Cost ceiling: stops calling Claude when daily limit reached
    8. Malformed Claude response: falls back gracefully
    9. Quality score range: 0–100 enforced
  - `test_storage.py`:
    1. store_catalyst + get_catalysts_by_symbol round-trip
    2. get_recent_catalysts with limit and offset
    3. cache_classification + get_cached_classification round-trip
    4. is_cache_valid with expired TTL
    5. store_brief + get_brief round-trip
    6. get_brief_history returns ordered by date
  - `test_pipeline.py`:
    1. Full pipeline: sources return items → dedup → classify → store → events published
    2. Cross-source dedup: same headline from FMP and Finnhub → classified once
  - Minimum new test count: 16
  - Test command: `python -m pytest tests/intelligence/test_classifier.py tests/intelligence/test_storage.py tests/intelligence/test_pipeline.py -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥16)
- [ ] All Claude API calls mocked in tests
- [ ] CatalystEvent published on Event Bus (verified in pipeline test)
- [ ] No CatalystEvent subscribers registered
- [ ] Cost ceiling enforcement tested
- [ ] Ruff linting passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No files modified outside intelligence/ | `git diff --name-only` |
| No CatalystEvent subscribers | `grep -r "subscribe.*CatalystEvent" argus/` returns 0 |
| AI layer untouched | `git diff argus/ai/` returns empty |
| SQLite tables isolated | New tables in catalyst.db, not in main DB or ai.db |
| UsageTracker used for cost tracking | `grep "usage_tracker\|UsageTracker" argus/intelligence/classifier.py` finds references |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/review-context.md`
