# Sprint 23, Session 1a: FMP Reference Data Client

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_scanner.py` (existing FMP integration pattern — auth, error handling, aiohttp usage)
   - `argus/core/config.py` (Pydantic model patterns, config loading)
   - `docs/architecture.md` §3.2 (DataService architecture)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: 1,977+ tests, all passing
3. Verify you are on the correct branch: `sprint-23` (create from main if needed)

## Objective
Build the FMP batch reference data client that fetches Company Profile and Share Float data for thousands of symbols, with caching and graceful degradation.

## Requirements

1. Create `argus/data/fmp_reference.py` with:

   a. `SymbolReferenceData` dataclass:
      - `symbol: str`
      - `sector: str | None` (GICS sector from Company Profile)
      - `industry: str | None`
      - `market_cap: float | None` (in USD)
      - `float_shares: float | None` (from Share Float endpoint)
      - `exchange: str | None` (e.g., "NASDAQ", "NYSE")
      - `prev_close: float | None`
      - `avg_volume: float | None` (average volume)
      - `is_otc: bool` (derived from exchange field)
      - `fetched_at: datetime`

   b. `FMPReferenceConfig` dataclass:
      - `base_url: str = "https://financialmodelingprep.com/api/v3"` (v3 API for batch profile)
      - `api_key_env_var: str = "FMP_API_KEY"`
      - `batch_size: int = 50` (symbols per batch request)
      - `cache_ttl_hours: int = 24`
      - `max_retries: int = 3`
      - `request_timeout_seconds: float = 30.0`

   c. `FMPReferenceClient` class:
      - `__init__(self, config: FMPReferenceConfig)`: stores config, initializes empty cache dict
      - `async def fetch_reference_data(self, symbols: list[str]) -> dict[str, SymbolReferenceData]`:
        - Splits symbols into batches of `batch_size`
        - For each batch, calls FMP batch Company Profile endpoint: `GET /api/v3/profile/{sym1,sym2,...}?apikey=KEY`
        - Parses response into SymbolReferenceData (map FMP fields: `sector`, `mktCap`, `exchangeShortName`, `price`, `volAvg`)
        - Handles: HTTP errors (retry with backoff), partial failures (log and continue), empty responses
        - Rate limits: max 300 calls/min (use asyncio.sleep between batches if needed)
        - Returns dict[symbol, SymbolReferenceData]
      - `async def fetch_float_data(self, symbols: list[str]) -> dict[str, float]`:
        - Calls FMP Share Float endpoint for symbols (batch if supported, sequential if not)
        - Returns dict[symbol, float_shares]
        - Graceful on failure: returns empty dict, logs warning
      - `async def build_reference_cache(self, symbols: list[str]) -> dict[str, SymbolReferenceData]`:
        - Orchestrates: fetch_reference_data → merge float_data → store in `_cache`
        - Returns the full cache dict
        - Logs: total symbols, successful fetches, failed fetches, elapsed time
      - `def get_cached(self, symbol: str) -> SymbolReferenceData | None`: cache lookup
      - `def is_cache_fresh(self) -> bool`: checks if cache age < TTL
      - `@property def cache_age_minutes(self) -> float`: age of cache in minutes
      - `@property def cached_symbol_count(self) -> int`

   d. Mark OTC symbols: set `is_otc = True` if exchange field contains "OTC" or similar identifiers from FMP data.

2. Follow the pattern from `fmp_scanner.py`:
   - Use `aiohttp` for HTTP requests
   - Read API key from environment variable
   - Log all API interactions at DEBUG level
   - Handle missing API key gracefully (raise RuntimeError on start, not on import)

## Constraints
- Do NOT modify any existing files in this session
- Do NOT import from or depend on Universe Manager (not yet created)
- Do NOT add FMP-specific dependencies (use existing aiohttp)
- Do NOT call real FMP API in tests — mock all HTTP requests

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_fetch_reference_data_success`: mock batch response, verify SymbolReferenceData fields
  2. `test_fetch_reference_data_batch_splitting`: 120 symbols with batch_size=50 → 3 API calls
  3. `test_fetch_reference_data_partial_failure`: one batch fails, others succeed → partial results
  4. `test_fetch_reference_data_all_fail`: all batches fail → empty dict, no exception
  5. `test_fetch_float_data_success`: mock float response, verify values
  6. `test_build_reference_cache`: end-to-end with mock, verify merged data
  7. `test_cache_freshness`: verify is_cache_fresh and cache_age_minutes
  8. `test_otc_detection`: symbols with OTC exchange → is_otc=True
- Minimum new test count: 8
- Test command: `python -m pytest tests/data/test_fmp_reference.py -v`

## Definition of Done
- [ ] `argus/data/fmp_reference.py` created with all classes and methods
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] FMP batch endpoint URL and field mapping documented in code comments
- [ ] Graceful degradation tested (API failures don't crash)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new files |
| All existing tests pass | `python -m pytest tests/ -x -q` |
| Ruff passes | `python -m ruff check argus/data/fmp_reference.py` |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R3: All existing tests pass (pytest 1,977+, Vitest 377+, ruff clean).
R4: No existing behavior changed (this session creates new files only).

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
E12: If this session required modifying any "Do not modify" files → ESCALATE.
E2: If FMP batch endpoint requires Premium plan (not available on Starter) → ESCALATE. Note: we won't know this until Session 4b integration testing with live API. In this session, we mock all HTTP calls.
