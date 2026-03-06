# Sprint 23, Session 1b: Universe Manager Core

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_reference.py` (Session 1a output — FMPReferenceClient, SymbolReferenceData)
   - `argus/core/config.py` (config patterns)
   - `argus/data/scanner.py` (Scanner ABC — UniverseManager wraps this)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: 1,977+ tests + Session 1a tests, all passing
3. Verify branch: `sprint-23`

## Objective
Build the Universe Manager core class that orchestrates FMP reference data fetching, constructs the viable universe via system-level filters, and provides the foundation for strategy-specific routing (added in Session 3a).

## Requirements

1. Create `argus/data/universe_manager.py` with:

   a. `UniverseManager` class:
      - `__init__(self, reference_client: FMPReferenceClient, config: UniverseManagerConfig, scanner: Scanner)`:
        - Stores dependencies
        - Initializes `_viable_symbols: set[str] = set()`
        - Initializes `_reference_cache: dict[str, SymbolReferenceData] = {}`
        - Initializes `_routing_table: dict[str, set[str]] = {}` (populated in Session 3a)
        - Initializes `_last_build_time: datetime | None = None`

      - `async def build_viable_universe(self) -> set[str]`:
        1. Fetch full symbol list from FMP (use Company Profile batch or stock list endpoint)
        2. Call `reference_client.build_reference_cache(symbols)` to get reference data
        3. Apply system-level filters:
           - `exclude_otc`: if True, exclude symbols where `is_otc == True`
           - `min_price` / `max_price`: filter on `prev_close`
           - `min_avg_volume`: filter on `avg_volume`
        4. Store result in `_viable_symbols`
        5. Store reference cache in `_reference_cache`
        6. Set `_last_build_time`
        7. Log: total fetched, viable count, filter pass rates
        8. Return viable set

      - `async def build_viable_universe_fallback(self, scanner_symbols: list[str]) -> set[str]`:
        - Fallback when FMP fails: use scanner results as viable universe
        - Still try to fetch reference data for these symbols (may partially succeed)
        - Log warning about degraded mode
        - Return set of scanner symbols

      - Properties:
        - `viable_symbols -> set[str]`
        - `viable_count -> int`
        - `reference_cache -> dict[str, SymbolReferenceData]`
        - `last_build_time -> datetime | None`
        - `is_built -> bool`: whether build_viable_universe has been called
        - `get_reference_data(symbol: str) -> SymbolReferenceData | None`

   b. Import `UniverseManagerConfig` from config (note: this model is created in Session 2a — for now, define a temporary placeholder or use a dict config. The Session 2a model will replace this.)

      **IMPORTANT:** Since Session 2a hasn't run yet, use a simple dataclass or dict for config in this session. Session 4a will wire the real Pydantic config. This avoids a dependency on Session 2a while keeping Session 1b self-contained.

      Temporary config pattern:
      ```python
      @dataclass
      class UniverseManagerConfig:
          enabled: bool = False
          min_price: float = 5.0
          max_price: float = 10000.0
          min_avg_volume: int = 100000
          exclude_otc: bool = True
          reference_cache_ttl_hours: int = 24
          fmp_batch_size: int = 50
      ```

2. The UniverseManager does NOT handle routing in this session — that's Session 3a. This session only builds the viable universe.

3. The `build_viable_universe()` method needs a source of symbols to fetch. Options:
   - Use FMP's stock list endpoint (`/api/v3/stock/list`) to get all tradable US symbols
   - Or accept a pre-supplied list from the scanner
   - **Recommendation:** Accept an optional `initial_symbols: list[str] | None` parameter. If None, fetch from FMP stock list. If provided (e.g., from scanner), use those as the starting universe.

## Constraints
- Do NOT modify any existing files
- Do NOT implement routing table logic (Session 3a)
- Do NOT touch strategy configs or strategy code
- The temporary config dataclass will be replaced by the real Pydantic model in Session 4a — design the interface so the swap is trivial

## Test Targets
After implementation:
- Existing tests + Session 1a tests: all pass
- New tests:
  1. `test_build_viable_universe_success`: mock reference client, verify filter application
  2. `test_system_filter_exclude_otc`: OTC symbols excluded when exclude_otc=True
  3. `test_system_filter_price_range`: symbols outside price range excluded
  4. `test_system_filter_min_volume`: low-volume symbols excluded
  5. `test_build_viable_universe_fmp_failure`: reference client fails → fallback to scanner symbols
  6. `test_viable_universe_properties`: count, is_built, last_build_time
  7. `test_get_reference_data`: lookup cached data for viable symbol
  8. `test_empty_universe`: all symbols filtered out → empty set, warning logged
- Minimum new test count: 8
- Test command: `python -m pytest tests/data/test_universe_manager.py -v`

## Definition of Done
- [ ] `argus/data/universe_manager.py` created
- [ ] Viable universe construction with all system-level filters
- [ ] Fallback path for FMP failure
- [ ] All existing tests + Session 1a tests pass
- [ ] 8+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new files |
| All existing tests pass | `python -m pytest tests/ -x -q` |
| Ruff passes | `python -m ruff check argus/data/universe_manager.py` |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3: All existing tests pass. R4: No existing behavior changed (new files only).

## Sprint-Level Escalation Criteria
E12: If modifying "Do not modify" files → ESCALATE.
