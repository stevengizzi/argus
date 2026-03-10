# Sprint 23.6, Session 4a: Reference Data Cache Layer

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_reference.py` (FMPReferenceConfig and FMPReferenceClient)
   - `tests/data/test_fmp_reference.py`
2. Run the test suite: `python -m pytest tests/data/test_fmp_reference.py -x -q`
   Expected: all passing
3. Verify you are on the correct branch: `sprint-23.6`

## Objective
Add file-based caching to FMPReferenceClient so reference data persists across restarts. This session builds the cache layer; Session 4b wires it into the warm-up flow.

## Minor Issues from Previous Session Review

From Session 3c review:

**CONCERNS**: The implementation is functionally correct and all spec requirements are met. However, 2 lint violations should be fixed in the next session (this session - 4a):

1. Run `ruff check --fix argus/intelligence/startup.py` to fix import sorting
2. Replace try-except-pass in server.py:214-217 with `with contextlib.suppress(asyncio.CancelledError):`

These are minor issues that don't block proceeding, but should be addressed to maintain code quality standards.

## Requirements

1. **In `argus/data/fmp_reference.py`**, add config fields to `FMPReferenceConfig`:
   ```python
   cache_file: str = "data/reference_cache.json"
   cache_max_age_hours: int = 24
   ```

2. **Add cache save method** to `FMPReferenceClient`:
   ```python
   def save_cache(self) -> None:
   ```
   - Serialize the internal `_reference_cache` (or equivalent dict of `{symbol: SymbolReferenceData}`) to JSON.
   - Each entry should include a `cached_at` ISO timestamp (when the data was fetched).
   - Write to a temp file first (`.tmp` suffix), then `os.replace()` to the target path (atomic write).
   - Handle serialization of `SymbolReferenceData` — since it's a dataclass, convert to dict.
   - Create parent directories if needed.
   - Log INFO with file path and symbol count.

3. **Add cache load method** to `FMPReferenceClient`:
   ```python
   def load_cache(self) -> dict[str, SymbolReferenceData]:
   ```
   - Read from `self._config.cache_file`.
   - Parse JSON, reconstruct `SymbolReferenceData` objects.
   - If file doesn't exist: return empty dict, log INFO "No cache file found".
   - If file is corrupt (invalid JSON, missing keys): return empty dict, log WARNING.
   - Do NOT filter by staleness here — that's the caller's job (S4b).
   - Return the dict.

4. **Add staleness check method**:
   ```python
   def get_stale_symbols(
       self,
       cached: dict[str, SymbolReferenceData],
       all_symbols: list[str],
       max_age_hours: int,
   ) -> list[str]:
   ```
   - Return symbols that are either: (a) not in the cache, or (b) in the cache but older than `max_age_hours`.
   - Compare `cached_at` timestamp against current time.

5. **SymbolReferenceData serialization:** Add `to_dict()` and `from_dict()` methods (or use dataclasses.asdict / a constructor). Include `cached_at: str` (ISO timestamp) in the serialized form. This field is cache metadata, not part of the reference data model itself.

## Constraints
- Do NOT modify `argus/data/universe_manager.py` (that's S4b)
- Do NOT modify the warm-up flow or `build_viable_universe` (that's S4b)
- Do NOT change the FMPReferenceClient constructor signature
- Do NOT add network calls in save/load — cache is purely filesystem
- Cache format must be human-readable JSON (not pickle, msgpack, etc.)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/data/test_fmp_reference.py`:
  1. `test_save_cache_creates_file` — save cache, verify file exists with correct content
  2. `test_load_cache_round_trip` — save then load, verify data matches
  3. `test_load_cache_missing_file` — no file → empty dict, no error
  4. `test_load_cache_corrupt_file` — malformed JSON → empty dict, WARNING logged
  5. `test_load_cache_truncated_file` — partial JSON → empty dict, WARNING logged
  6. `test_save_cache_atomic_write` — verify temp file used (or at minimum, file is valid after save)
  7. `test_get_stale_symbols_all_fresh` — all cached within max_age → returns only missing symbols
  8. `test_get_stale_symbols_some_stale` — some entries older than max_age → returned as stale
  9. `test_get_stale_symbols_all_missing` — empty cache → all symbols returned
  10. `test_cache_includes_cached_at` — verify each entry has cached_at timestamp
- Minimum new test count: 10
- Test command: `python -m pytest tests/data/test_fmp_reference.py -x -q`

## Definition of Done
- [ ] Cache save writes atomic JSON file with per-symbol cached_at
- [ ] Cache load reads and reconstructs SymbolReferenceData objects
- [ ] Missing/corrupt file handled gracefully (empty dict, no crash)
- [ ] Staleness check identifies missing and old entries
- [ ] Config fields added (cache_file, cache_max_age_hours)
- [ ] All existing tests pass
- [ ] 10+ new tests written and passing
- [ ] No ruff lint errors

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing FMP tests pass | `python -m pytest tests/data/test_fmp_reference.py -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/core/ argus/execution/ argus/ai/ argus/ui/` empty |
| Universe Manager untouched | `git diff HEAD -- argus/data/universe_manager.py` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.
