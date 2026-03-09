# Sprint 23.5, Session 2: Data Source Clients — SEC EDGAR, FMP News, Finnhub

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/models.py` (S1 output — CatalystRawItem, compute_headline_hash)
   - `argus/intelligence/config.py` (S1 output — source configs)
   - `argus/data/fmp_reference.py` (pattern: aiohttp client, rate limiting, error handling)
   - `argus/data/fmp_scanner.py` (pattern: FMP API interaction)
   - `argus/core/events.py` (CatalystEvent from S1)
2. Run the test suite: `cd argus && python -m pytest tests/ -x -q`
   Expected: 2,101+ tests + S1 tests, all passing
3. Verify S1 artifacts exist: `ls argus/intelligence/models.py argus/intelligence/config.py`

## Objective
Implement three data source client classes for catalyst data ingestion: SEC EDGAR (filings), FMP News (stock news + press releases), and Finnhub (company news + analyst recommendations). All implement a common CatalystSource ABC. All external API calls must be mockable for testing — no live API calls in tests.

## Requirements

1. **Create `argus/intelligence/sources/__init__.py`**: Define the CatalystSource ABC:
   ```python
   class CatalystSource(ABC):
       """Abstract base class for catalyst data sources."""
       
       @abstractmethod
       async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
           """Fetch raw catalyst items for the given symbols."""
           ...
       
       @abstractmethod
       async def start(self) -> None:
           """Initialize the source (create HTTP session, etc.)."""
           ...
       
       @abstractmethod
       async def stop(self) -> None:
           """Clean up resources."""
           ...
       
       @property
       @abstractmethod
       def source_name(self) -> str:
           """Return the source identifier (e.g., 'sec_edgar')."""
           ...
   ```

2. **Create `argus/intelligence/sources/sec_edgar.py`**: SEC EDGAR client.
   - Uses `data.sec.gov` REST API (no API key needed, free).
   - **CIK Mapping**: Fetch company tickers from `https://www.sec.gov/files/company_tickers.json` (cached — load once at start, refresh every 24 hours). Maps ticker → CIK. If ticker not found, skip that symbol.
   - **Filing Fetch**: For each symbol, fetch recent filings from `https://data.sec.gov/submissions/CIK{cik_padded_10}.json`. Parse the `recentFilings` array. Filter by `form` field matching config `filing_types` (default: "8-K", "4"). Extract: form type, filing date, primary document URL, items (for 8-K: Item 2.02 etc.).
   - **Rate Limiting**: SEC requires max 10 requests/second. Implement a simple asyncio rate limiter (token bucket or semaphore with delay). SEC also requires `User-Agent` header with contact email — read from `config.sources.sec_edgar.user_agent_email`.
   - **Error Handling**: HTTP 403 (rate limited) → backoff and retry (max 3). HTTP 404 (CIK not found) → skip symbol, log warning. Timeout → skip, log warning. Connection error → skip, log error.
   - Return `list[CatalystRawItem]` with `source="sec_edgar"`, `filing_type` set to form type, `source_url` to filing URL, `metadata` containing items list and accession number.

3. **Create `argus/intelligence/sources/fmp_news.py`**: FMP News client.
   - Uses FMP Starter plan endpoints (300 calls/min).
   - **Stock News**: `GET https://financialmodelingprep.com/api/v3/stock_news?tickers={sym1,sym2,...}&limit=50&apikey={key}`. Batch up to 5 tickers per call. Returns JSON array with: symbol, publishedDate, title, text, url, site.
   - **Press Releases**: `GET https://financialmodelingprep.com/api/v3/press-releases/{symbol}?limit=10&apikey={key}`. One call per symbol. Returns JSON array with: symbol, date, title, text.
   - **Deduplication**: Apply `compute_headline_hash()` to each headline. Return only items not seen in the current fetch batch.
   - **API Key**: Read from environment variable specified in `config.sources.fmp_news.api_key_env_var`. If not set, log warning and return empty list.
   - **Error Handling**: HTTP 401/403 → log error "FMP API key invalid", disable source for this cycle. HTTP 429 → exponential backoff, max 3 retries. Empty response → normal (not all symbols have news).
   - Return `list[CatalystRawItem]` with `source="fmp_news"` or `source="fmp_press_release"`, `source_url` to article URL.

4. **Create `argus/intelligence/sources/finnhub.py`**: Finnhub client.
   - Uses Finnhub free tier REST API (60 calls/min).
   - **Company News**: `GET https://finnhub.io/api/v1/company-news?symbol={sym}&from={date}&to={date}&token={key}`. One call per symbol. Date range: last 24 hours (or since last poll). Returns JSON array with: category, datetime, headline, id, image, related, source, summary, url.
   - **Recommendation Trends**: `GET https://finnhub.io/api/v1/stock/recommendation?symbol={sym}&token={key}`. Returns analyst recommendation changes. Convert to CatalystRawItem with `category` context in metadata.
   - **Rate Limiting**: 60 calls/min. Implement rate limiter.
   - **API Key**: Read from environment variable specified in `config.sources.finnhub.api_key_env_var`. If not set, log warning and return empty list.
   - **Error Handling**: Same pattern as FMP — 401/403 disables, 429 backs off, empty is normal.
   - Return `list[CatalystRawItem]` with `source="finnhub"`, `source_url` to article URL.

5. **All clients**: Use `aiohttp.ClientSession` for HTTP requests. Create session in `start()`, close in `stop()`. Follow the pattern from `argus/data/fmp_reference.py` for session management and error handling.

## Constraints
- Do NOT modify any files outside `argus/intelligence/sources/`
- Do NOT make live API calls in tests — all HTTP responses must be mocked using `aioresponses` or `unittest.mock.AsyncMock`
- Do NOT register any Event Bus subscribers
- SEC EDGAR client MUST include User-Agent header — SEC will block requests without it
- All clients MUST handle missing API keys gracefully (return empty list, log warning)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/intelligence/test_sources/`:
  - `test_sec_edgar.py`:
    1. CIK mapping: ticker found → correct CIK
    2. CIK mapping: ticker not found → skip symbol
    3. Filing fetch: parse 8-K filing correctly
    4. Filing fetch: parse Form 4 filing correctly
    5. Filing fetch: filter by filing_types config
    6. Rate limiting: requests throttled to 10/sec
    7. Error handling: 403 → retry then skip
    8. Error handling: 404 → skip with warning
  - `test_fmp_news.py`:
    1. Stock news: parse multi-ticker response
    2. Press releases: parse single-symbol response
    3. Batch tickers: correctly batched in groups of 5
    4. Dedup: duplicate headlines filtered
    5. Missing API key: returns empty list with warning
    6. Error handling: 429 → backoff
  - `test_finnhub.py`:
    1. Company news: parse response correctly
    2. Recommendation trends: parse and convert to CatalystRawItem
    3. Rate limiting: respects 60/min
    4. Missing API key: returns empty list with warning
    5. Error handling: 401 → disable for cycle
    6. Date range: uses last 24 hours
- Minimum new test count: 18
- Test command: `python -m pytest tests/intelligence/test_sources/ -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥18)
- [ ] All HTTP calls mocked in tests (no live API calls)
- [ ] SEC EDGAR client includes User-Agent header with email from config
- [ ] Each client handles missing API key gracefully
- [ ] Ruff linting passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No files modified outside intelligence/sources/ | `git diff --name-only` shows only new files in intelligence/sources/ |
| No live API calls in tests | `grep -r "financialmodelingprep.com\|data.sec.gov\|finnhub.io" tests/` — only in mock URLs, not actual requests |
| FMP scanner unaffected | `python -m pytest tests/data/test_fmp_scanner.py -v` passes |
| All clients return CatalystRawItem list | Type checking in tests |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`
