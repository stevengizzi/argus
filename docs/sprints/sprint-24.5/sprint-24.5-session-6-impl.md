# Sprint 24.5, Session 6: Operational Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ai/summary.py` (AI Insight clock bug — find _assemble_insight_data)
   - `argus/ai/context.py` (check for related uptime/session references)
   - `argus/intelligence/sources/finnhub.py` (403 log level — find line ~341)
   - `argus/intelligence/sources/fmp_news.py` (circuit breaker — find _disabled_for_cycle)
   - `config/system_live.yaml` (verify fmp_news.enabled: false)
   - `argus/api/routes/health.py` (uptime calculation — context for clock bug)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/ai/ tests/intelligence/ -x -q
   ```
   Expected: all passing
3. Verify branch: `sprint-24.5`

## Objective
Fix three operational issues discovered during live QA: AI Insight card showing
wrong session elapsed time, Finnhub 403 log noise, and FMP circuit breaker test
coverage.

## Requirements

1. **AI Insight Clock Bug Fix** — in `argus/ai/summary.py`:

   a. Find `_assemble_insight_data()` method. Currently it computes:
      ```python
      data["market_open"] = 9 * 60 + 30 <= now_et.hour * 60 + now_et.minute <= 16 * 60
      ```

   b. Add a `session_elapsed_minutes` field:
      ```python
      market_open_minutes = 9 * 60 + 30  # 9:30 ET
      market_close_minutes = 16 * 60  # 16:00 ET
      now_minutes = now_et.hour * 60 + now_et.minute

      if now_minutes < market_open_minutes:
          data["session_status"] = "pre_market"
          data["session_elapsed_minutes"] = None
          data["minutes_until_open"] = market_open_minutes - now_minutes
      elif now_minutes <= market_close_minutes:
          data["session_status"] = "open"
          data["session_elapsed_minutes"] = now_minutes - market_open_minutes
          data["minutes_until_open"] = None
      else:
          data["session_status"] = "closed"
          data["session_elapsed_minutes"] = None
          data["minutes_until_open"] = None
      ```

   c. Also check if the insight prompt template (in `summary.py` or `prompts.py`)
      uses "uptime" or "start_time" to generate the "X minutes into session"
      text. If it does, update it to use `session_elapsed_minutes` instead.
      Search for any references to `uptime` in the insight generation path.

   d. If the `_assemble_summary_data()` method (for daily summaries, not
      insights) has a similar issue, fix it too.

2. **Finnhub 403 Log Downgrade** — in `argus/intelligence/sources/finnhub.py`:

   a. Find the 403 handler (around line 341-342):
      ```python
      if response.status == 403:
          logger.error("Finnhub API access denied (HTTP 403)")
      ```

   b. Change to:
      ```python
      if response.status == 403:
          logger.warning("Finnhub HTTP 403 for %s — free tier coverage gap", url)
      ```

   c. Add a per-cycle 403 counter. In the class, add `self._cycle_403_count: int = 0`
      and `self._cycle_total_requests: int = 0`. Reset both at the start of each
      poll cycle (find the cycle start method). Increment on each 403.

   d. At the end of each poll cycle, if `_cycle_403_count > 0`:
      ```python
      logger.info(
          "Finnhub cycle summary: %d/%d symbols returned 403 — free tier coverage gap",
          self._cycle_403_count,
          self._cycle_total_requests,
      )
      ```

3. **FMP Circuit Breaker Test** — write test coverage for DEC-323:

   a. In `tests/intelligence/test_fmp_circuit_breaker.py` (new file):
      - Test: mock HTTP 403 on first symbol → `_disabled_for_cycle` becomes True
      - Test: after first 403, remaining symbols are skipped (count of HTTP
        requests should be 1, not N)
      - Test: after cycle reset, `_disabled_for_cycle` is False again
      - Test: verify `config/system_live.yaml` has `fmp_news.enabled: false`

4. **(Optional, if time allows)** Create `docs/designs/candle-cache.md`:
   A design document specifying the local candle cache architecture:
   - Persistence format (SQLite table or flat file)
   - Replay mechanism (how candles are fed back to strategies on restart)
   - Indicator rebuild flow (how indicators warm up from cache)
   - Safety guards (prevent order submission during replay, mark replay state)
   - Estimated implementation effort
   This is a design doc only — no code.

## Constraints
- Do NOT modify any strategy files
- Do NOT modify `argus/main.py`, `argus/core/events.py`, `argus/api/websocket/live.py`
- Do NOT change FMP circuit breaker behavior — only add tests for existing behavior
- Do NOT enable FMP news in any config file
- Keep Finnhub 403 changes minimal — just log level and counter

## Test Targets
New tests:
1. `tests/ai/test_insight_clock.py`:
   - `test_session_status_pre_market` — before 9:30 ET → pre_market, minutes_until_open set
   - `test_session_status_open` — 10:00 ET → open, session_elapsed_minutes = 30
   - `test_session_status_closed` — 17:00 ET → closed, both None
2. `tests/intelligence/test_finnhub_403.py`:
   - `test_403_logged_as_warning` — mock 403, verify WARNING not ERROR
   - `test_cycle_403_summary` — mock multiple 403s, verify INFO summary
3. `tests/intelligence/test_fmp_circuit_breaker.py`:
   - `test_first_403_trips_breaker` — mock 403, verify _disabled_for_cycle
   - `test_remaining_symbols_skipped` — verify no more HTTP requests after trip
   - `test_cycle_reset_clears_breaker` — reset method clears flag
- Minimum new test count: 7
- Test command (final session — full suite): `python -m pytest -x -q -n auto`

## Definition of Done
- [ ] AI Insight shows correct session elapsed time from 9:30 ET
- [ ] Finnhub 403 logged at WARNING with per-cycle summary
- [ ] FMP circuit breaker has test coverage
- [ ] All existing tests pass (full suite)
- [ ] ≥7 new tests written and passing
- [ ] ruff linting passes
- [ ] Vitest suite passes: `cd argus/ui && npx vitest run`
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-6-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| AI Insight still generates | `python -m pytest tests/ai/ -x -q` |
| Finnhub still fetches for working symbols | `python -m pytest tests/intelligence/ -k "finnhub" -x -q` |
| FMP news still disabled | `grep "enabled: false" config/system_live.yaml` (under fmp_news) |
| No strategy changes | `python -m pytest tests/strategies/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-6-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-6-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (FINAL session — full suite): `python -m pytest -x -q -n auto && cd argus/ui && npx vitest run`
5. Files NOT to modify: `argus/core/events.py`, `argus/main.py`, any strategy files

## Session-Specific Review Focus (for @reviewer)
1. Verify session_elapsed_minutes uses 9:30 ET as reference (not boot time, not UTC)
2. Verify the insight prompt template actually uses the new field (not still using uptime)
3. Verify Finnhub 403 log level is WARNING (grep for logger.error with 403)
4. Verify FMP circuit breaker tests mock HTTP correctly (not hitting real API)
5. Verify system_live.yaml unchanged (fmp_news.enabled still false)
6. Full suite passes as this is the final session

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
