# Sprint 27.6, Session 3: MarketCorrelationTracker

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/config.py` (CorrelationConfig)
   - `argus/core/regime.py` (RegimeVector fields for correlation)
2. Run scoped test baseline:
   ```
   python -m pytest tests/core/test_regime.py tests/core/test_breadth.py -x -q
   ```
   Expected: all passing
3. Verify you are on the correct branch

## Objective
Build MarketCorrelationTracker as a standalone module that computes rolling 20-day pairwise correlation for top N symbols during pre-market. Uses FMP daily bars. File-based JSON cache keyed by calendar date (ET).

## Requirements

1. Create `argus/core/market_correlation.py` with class `MarketCorrelationTracker`:
   - Constructor: `(config: CorrelationConfig)`
   - `async def compute(self, fetch_daily_bars_fn, get_top_symbols_fn) -> None`:
     - `get_top_symbols_fn() -> list[str]`: Returns top N symbols by avg daily volume from Universe Manager reference cache
     - `fetch_daily_bars_fn(symbol, lookback_days) -> pd.DataFrame | None`: FMP daily bars
     - Check file cache first. If cache date (ET) == today → load and return
     - Otherwise: fetch daily bars for top N symbols concurrently via `asyncio.gather()`, compute returns, compute pairwise correlation matrix, store results + update cache
   - `get_correlation_snapshot() -> dict`: Returns `{"average_correlation": float, "correlation_regime": str, "symbols_used": int}`
   - Correlation regime: dispersed (<dispersed_threshold), normal, concentrated (>concentrated_threshold)
   - File cache at `data/correlation_cache.json` with schema: `{"date": "YYYY-MM-DD", "symbols": [...], "average_correlation": float, "correlation_regime": str}`
   - Graceful degradation: if daily bars unavailable for most symbols → neutral defaults (avg_correlation=0.4, regime="normal")
   - Edge cases: single symbol → neutral, all identical returns → correlation 1.0, insufficient history (<20 days) → exclude symbol

## Constraints
- Do NOT modify any existing files
- Do NOT import or call FMP/Universe Manager directly — accept callables as parameters (dependency injection for testability)
- Module is standalone, wired in S6

## Test Targets
- New tests (~10) in `tests/core/test_market_correlation.py`:
  - Construction with config
  - compute_from known data → correct average correlation
  - correlation_regime: dispersed, normal, concentrated classification
  - Single symbol → neutral defaults
  - All identical returns → correlation 1.0
  - Insufficient history → exclude symbol, neutral if too few remain
  - File cache write and read
  - File cache same-day hit (no recomputation)
  - File cache stale date → recompute
  - get_correlation_snapshot returns current state
- Minimum: 10
- Test command: `python -m pytest tests/core/test_market_correlation.py -x -q -v`

## Definition of Done
- [ ] MarketCorrelationTracker with async compute, cache, snapshots
- [ ] Graceful degradation on missing data
- [ ] File cache with date-keyed invalidation
- [ ] 10+ tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-3-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new file + tests |
| Dependency injection | Constructor takes no FMP/UM references directly |
| Cache schema correct | Test loads cache JSON and validates keys |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-3-closeout.md`
3. Test command: `python -m pytest tests/core/test_market_correlation.py -x -q -v`
4. Files NOT to modify: all existing files

## Session-Specific Review Focus
1. Verify dependency injection pattern (no direct FMP/UM imports)
2. Verify cache invalidation is date-keyed (ET, not UTC)
3. Verify graceful degradation (never raises on missing data)
4. Verify no naming collision with existing `core/correlation.py` (strategy P&L tracker)
