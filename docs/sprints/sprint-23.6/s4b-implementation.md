# Sprint 23.6, Session 4b: Incremental Warm-Up Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_reference.py` (S4a's cache methods — verify they exist)
   - `argus/data/universe_manager.py` (build_viable_universe, current warm-up flow)
   - `argus/main.py` (or wherever the warm-up sequence is called — check how Universe Manager is initialized)
2. Run the test suite: `python -m pytest tests/data/ -x -q`
   Expected: all passing (including S4a changes)
3. Verify S4a completed: `save_cache()`, `load_cache()`, `get_stale_symbols()` exist
4. Verify you are on the correct branch: `sprint-23.6`

## Objective
Wire the S4a cache layer into the Universe Manager warm-up flow so subsequent startups only fetch stale/missing reference data, reducing ~27-minute warm-up to ~2-5 minutes.

## Requirements

1. **In `argus/data/fmp_reference.py`**, add an incremental fetch method:
   ```python
   async def fetch_reference_data_incremental(
       self, all_symbols: list[str]
   ) -> dict[str, SymbolReferenceData]:
   ```
   This method:
   - Calls `self.load_cache()` to get cached data.
   - Calls `self.get_stale_symbols(cached, all_symbols, self._config.cache_max_age_hours)` to get delta.
   - If delta is empty: log INFO "All reference data cached and fresh", return cached data directly.
   - If delta is non-empty: log INFO with delta count, call existing `self.fetch_reference_data(delta)` for only the stale/missing symbols.
   - Merge fresh fetches with valid cached entries.
   - Call `self.save_cache()` with the merged result.
   - Return the merged dict.

2. **In `argus/data/universe_manager.py`** (or wherever warm-up is orchestrated), update the warm-up flow:
   - Check if cache file exists (or just always try incremental first).
   - Call `reference_client.fetch_reference_data_incremental(all_symbols)` instead of `reference_client.fetch_reference_data(all_symbols)`.
   - This should be in the `build_viable_universe()` method or the code that calls it in main.py.
   - **Locate the exact call site** by reading the code — the prompt can't know exactly where the warm-up is wired without seeing main.py's orchestration.

3. **Fallback:** If incremental fetch fails for any reason (cache load error + full fetch error), the system should log ERROR but not crash — the universe will be empty, which is handled by existing "empty viable universe" WARNING.

4. **After successful warm-up, save cache:** Ensure `save_cache()` is called after the full reference data is assembled (whether from cache + delta or from full fetch).

## Constraints
- Do NOT modify `argus/intelligence/` (pipeline code)
- Do NOT change the `build_viable_universe()` signature
- Do NOT change the FMPReferenceClient constructor signature
- Do NOT add new FMP API endpoints — reuse existing `fetch_reference_data()` for the delta
- Preserve the full-fetch path for first run (no cache)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/data/test_fmp_reference.py` and/or `tests/data/test_universe_manager.py`:
  1. `test_incremental_fetch_all_cached` — all symbols in fresh cache → no network calls, returns cached
  2. `test_incremental_fetch_some_stale` — half stale → fetches only stale, merges with fresh
  3. `test_incremental_fetch_no_cache` — no cache file → full fetch (existing behavior)
  4. `test_incremental_fetch_saves_cache` — after fetch, cache file updated
  5. `test_incremental_fetch_merge_correctness` — merged result has both cached and fresh entries
  6. `test_warm_up_uses_incremental` — verify build_viable_universe uses incremental path
  7. `test_warm_up_fallback_on_error` — cache corrupt + fetch error → empty universe, no crash
  8. `test_incremental_fetch_empty_delta_skips_network` — verify no HTTP calls when delta is empty
- Minimum new test count: 8
- Test command: `python -m pytest tests/data/ -x -q`

## Definition of Done
- [ ] Incremental fetch loads cache, diffs, fetches delta only
- [ ] Merged result saved back to cache
- [ ] No-cache path falls through to full fetch
- [ ] Warm-up flow in universe_manager or main.py uses incremental path
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] No ruff lint errors

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing FMP tests pass | `python -m pytest tests/data/test_fmp_reference.py -x -q` |
| Existing universe tests pass | `python -m pytest tests/data/test_universe_manager.py -x -q` |
| Full test suite passes | `python -m pytest tests/ -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/core/ argus/execution/ argus/ai/ argus/ui/` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.
