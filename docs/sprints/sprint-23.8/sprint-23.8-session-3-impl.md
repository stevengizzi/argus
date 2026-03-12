# Sprint 23.8, Session 3: Source Hardening + Databento Warm-Up Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/sprints/sprint-23.8-spec.md`
   - `argus/intelligence/sources/sec_edgar.py`
   - `argus/intelligence/sources/finnhub.py`
   - `argus/intelligence/sources/fmp_news.py`
   - `argus/data/databento_data_service.py` (search for "lazy warm-up" or "warm_up" or "backfill")
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: 2,511+ tests passing (Sessions 1–2 may have added tests)
3. Verify you are on the correct branch: `sprint-23.8-pipeline-fixes`
4. Verify Sessions 1–2 are complete: `git log --oneline -10` should show their commits

## Objective
Harden all three intelligence source HTTP clients with explicit socket-level timeouts, add a circuit breaker to FMP news to prevent 403 spam, and fix the Databento lazy warm-up to avoid 422 rejections from the historical API.

## Requirements

1. **In `argus/intelligence/sources/sec_edgar.py` — explicit timeouts:**
   - Find where `aiohttp.ClientSession` is created (likely in `start()` or `__init__`)
   - Change the timeout from `ClientTimeout(total=30)` (or whatever it currently is) to:
     ```python
     ClientTimeout(total=30, sock_connect=10, sock_read=20)
     ```
   - This ensures DNS/connection hangs (10s) and silent server hangs (20s) are caught independently, rather than relying only on the `total` timer which can behave unpredictably with DNS.

2. **In `argus/intelligence/sources/finnhub.py` — explicit timeouts:**
   - Same change as sec_edgar: `ClientTimeout(total=30, sock_connect=10, sock_read=20)`

3. **In `argus/intelligence/sources/fmp_news.py` — explicit timeouts + circuit breaker:**
   - Same timeout change: `ClientTimeout(total=30, sock_connect=10, sock_read=20)`
   - Add a circuit breaker for 403 (plan restriction) responses:
     ```python
     # Instance variable
     self._circuit_open = False

     async def fetch_catalysts(self, symbols: list[str]) -> list[RawCatalyst]:
         self._circuit_open = False  # Reset at start of each cycle
         results = []
         for symbol in symbols:
             if self._circuit_open:
                 continue  # Skip remaining symbols this cycle
             try:
                 items = await self._fetch_for_symbol(symbol)
                 results.extend(items)
             except FMPAuthError:  # or however 403 is currently raised/handled
                 if not self._circuit_open:
                     logger.error(f"FMP API key invalid (HTTP 403) — disabling FMP news source for this poll cycle")
                     self._circuit_open = True
         if self._circuit_open:
             logger.warning(f"FMP news circuit breaker: skipped {skipped_count} symbols after 403")
         return results
     ```
   - Adapt the above to match the actual code structure — the 403 may be detected via HTTP status code check rather than a custom exception. Read the existing error handling to understand the pattern, then add the circuit breaker around it.
   - The key behavior: first 403 → log ERROR + set flag. All subsequent symbols → skip silently. End of cycle → log WARNING with skip count. Next cycle → flag resets.

4. **In `argus/data/databento_data_service.py` — lazy warm-up end timestamp clamp:**
   - Find the lazy warm-up code path (Sprint 23.7, DEC-316). It's triggered on mid-session boot when a symbol's first candle arrives and the system needs to backfill indicators.
   - The `end` parameter for the Databento historical API request is currently set to approximately `now`. Databento's historical API has a ~10 minute lag, causing 422 `data_end_after_available_end` errors.
   - Clamp the `end` parameter:
     ```python
     # Databento historical API lags ~10min behind live stream (DEC-326)
     HISTORICAL_LAG_BUFFER = timedelta(seconds=600)
     end = datetime.now(timezone.utc) - HISTORICAL_LAG_BUFFER
     ```
   - Ensure this ONLY affects the mid-session lazy warm-up path. The pre-market boot path (which skips warm-up entirely per DEC-316) must not be modified.
   - If `end` would be before `start` after clamping (e.g., system just started and there's <10min of history), skip the warm-up for that symbol with a DEBUG log and let it build from the live stream — this is the same graceful degradation already used for pre-market boot.

## Constraints
- Do NOT modify: `startup.py`, `pipeline.py`, `server.py`, `classifier.py`, `storage.py`, `core/`, `strategies/`, `execution/`, `ui/`, `ai/`
- Do NOT change: Source fetch logic (what data is requested), dedup behavior, classification, storage schema
- Do NOT add: New config fields, new source types, new API endpoints
- Do NOT modify the Databento live streaming connection — only the historical backfill request in lazy warm-up

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test SEC Edgar client creates session with `sock_connect=10, sock_read=20` timeout
  2. Test Finnhub client creates session with `sock_connect=10, sock_read=20` timeout
  3. Test FMP news client creates session with `sock_connect=10, sock_read=20` timeout
  4. Test FMP news circuit breaker: mock 403 on first symbol, verify remaining symbols skipped
  5. Test FMP news circuit breaker resets between cycles: mock 403 in cycle 1, verify cycle 2 retries
  6. Test Databento lazy warm-up clamps `end` to `now - 600s`
  7. Test Databento lazy warm-up skips symbol when clamped `end` < `start`
  8. Test pre-market boot path is unaffected by clamping (warm-up is skipped entirely)
- Minimum new test count: 7
- Test command: `python -m pytest tests/intelligence/sources/ tests/data/test_databento*.py -x -q`

## Definition of Done
- [ ] All three sources use `ClientTimeout(total=30, sock_connect=10, sock_read=20)`
- [ ] FMP news circuit breaker: first 403 sets flag, remaining symbols skipped, flag resets next cycle
- [ ] Circuit breaker logs ERROR on first 403, WARNING with skip count at end
- [ ] Databento lazy warm-up `end` clamped to `now - 600s`
- [ ] Clamped `end < start` skips warm-up gracefully (DEBUG log)
- [ ] Pre-market boot path (skip warm-up) unaffected
- [ ] All existing tests pass
- [ ] 7+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| SEC Edgar source starts | Boot with `catalyst.enabled: true`, see "SECEdgarClient started" in log |
| Finnhub source starts | Boot log shows "FinnhubClient started" |
| FMP news source starts (when enabled) | Boot log shows "FMPNewsClient started" |
| Sources respect existing rate limits | Rate limit config unchanged in source constructors |
| Databento live streaming unaffected | `grep "Connected to Databento" logs/` shows connection |
| Pre-market boot skips warm-up | Boot before market hours, see "Pre-market boot — skipping indicator warm-up" |
| No changes to data service public interface | `git diff argus/data/databento_data_service.py` shows only warm-up changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`
