# Sprint 12 Review — Handoff Context

> **For the Claude.ai review conversation.** Paste this at the start of the new conversation (alongside the project files). It gives the reviewing Claude full context on what was designed, what decisions were made, and what to look for in the implementation transcripts.

---

## What Sprint 12 Is

Sprint 12 builds the **DatabentoDataService adapter** — ARGUS's primary production market data service. It replaces the Alpaca IEX feed (which only captures 2–3% of market volume per DEC-081) with institutional-grade exchange-direct data from Databento ($199/mo, DEC-082).

**Previous state:** 542 tests, Sprints 1–11 complete. Paper trading active on Alpaca IEX (system stability testing only).

**Target:** ~110 new tests across 6 components. ~650 total.

---

## Sprint 12 Components (6 total)

The spec was split into **two Claude Code prompts** to avoid context exhaustion:

### Prompt 1 (Components 1–3):
1. **DatabentoConfig** — Pydantic config model (`argus/config/databento_config.py`). Dataset selection (default: XNAS.ITCH), schema subscriptions, reconnection params, circuit breaker threshold. ~10 tests.
2. **DatabentoSymbolMap** — Bidirectional instrument_id ↔ ticker symbol mapping (`argus/data/databento_symbol_map.py`). Needed because Databento uses integer IDs, not string symbols. ~15 tests.
3. **DatabentoDataService (Core)** — Implements DataService ABC (`argus/data/databento_data_service.py`). Live TCP streaming via `databento` library, callback dispatch on Databento's reader thread bridged to asyncio via `loop.call_soon_threadsafe()`, indicator computation reusing existing logic, stale data monitoring. ~40 tests.

### Prompt 2 (Components 4–6):
4. **Reconnection + Circuit Breaker** — Exponential backoff reconnection wrapper, enhanced stale data monitor publishing DataStaleEvent/DataResumedEvent. ~15 tests.
5. **DataFetcher Databento Backend** — Extends existing DataFetcher with `fetch_symbol_month_databento()`. Historical API queries → Parquet cache. Same output schema as Alpaca for VectorBT/Replay Harness compatibility. ~15 tests.
6. **Scanner + Integration** — DatabentoScanner (stub-level OK for V1), system wiring in main.py for config-driven DataService selection, env var documentation. ~15 tests.

---

## Key Design Decisions Made During Sprint 12 Design

These were agreed upon before implementation:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Dataset** | `XNAS.ITCH` (Nasdaq TotalView) | Most recommended for trading firms, deepest historical data, L2/L3 available, covers NASDAQ-listed stocks that ORB targets |
| **Threading model** | Databento callbacks on reader thread → `loop.call_soon_threadsafe()` → asyncio Event Bus | Idiomatic Databento pattern, clean bridge to asyncio |
| **Symbol subscription** | Pre-scanned watchlist (not ALL_SYMBOLS for live), configurable | Bandwidth management. Config supports both modes. |
| **Dual subscription** | Two `subscribe()` calls: `ohlcv-1m` + `trades` | Let Databento compute bars (nanosecond precision), trades for real-time price updates. Matches AlpacaDataService dual-stream pattern. |
| **Development without subscription** | All tests use mocks (DEC-087). No `databento` import at module level. | Subscription activated at end of sprint for integration testing only. |
| **L2 depth** | Config field exists (`enable_depth: bool = False`), not activated | Designed from day one per research report, activated when a strategy needs it |

---

## What to Look For During Review

### Critical Correctness Checks

1. **DataService ABC compliance:** Does DatabentoDataService implement ALL methods from the DataService ABC? (`start`, `stop`, `get_current_price`, `get_indicator`, `get_historical_candles`, `get_watchlist_data`)

2. **Indicator parity:** Does the indicator computation use the EXACT same logic as AlpacaDataService and BacktestDataService? Check if a shared module was extracted or if code was copied. Copied code = tech debt to flag.

3. **Thread safety:** The callback dispatch runs on Databento's reader thread. Verify that:
   - `_dispatch_record()` does NOT `await` anything (it can't — it's on a non-asyncio thread)
   - Event Bus publishing is properly bridged via `call_soon_threadsafe()`
   - `_price_cache` and `_indicator_cache` updates are safe (Python dict single-key operations are GIL-protected)

4. **Timestamp handling:** Databento uses nanosecond Unix timestamps. Verify conversion to `datetime` with UTC timezone is correct: `datetime.fromtimestamp(ts_event / 1e9, tz=timezone.utc)`.

5. **Historical data schema compatibility:** The output of `get_historical_candles()` and `fetch_symbol_month_databento()` must have columns `[timestamp, open, high, low, close, volume]` — same as Alpaca data. Check that VectorBT and Replay Harness could consume it without changes.

6. **No real Databento imports at module level:** All `import databento as db` must be inside methods or behind `TYPE_CHECKING`. Tests must be able to run without the `databento` package installed.

### Reconnection Logic Checks

7. **Exponential backoff math:** `delay = min(base * 2^(retries-1), max_delay)`. Verify the progression: 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s, 60s, 60s (capped).

8. **Clean shutdown:** When `stop()` is called, the reconnection loop must exit cleanly without attempting another reconnect.

9. **Symbol map cleared on reconnect:** New session sends fresh SymbolMappingMsg events, so the old mappings must be cleared.

### Integration Checks

10. **Config-driven provider selection:** main.py should support `provider: "databento"` and `provider: "alpaca"` without code changes.

11. **Existing tests unchanged:** All 542 existing tests must still pass. The Databento adapter is additive — nothing is removed.

12. **New events defined:** DataStaleEvent and DataResumedEvent (or equivalent) must be properly defined and importable.

---

## Document Updates Needed After Sprint 12

After review is complete and sprint is confirmed done, these docs need updating:

| Document | What to Update |
|----------|---------------|
| **05_DECISION_LOG.md** | New DEC entries for any implementation decisions made during Sprint 12 (dataset choice, threading model, etc. — if not already logged) |
| **02_PROJECT_KNOWLEDGE.md** | Update "Current Project State" — Sprint 12 complete, test count, Build Track queue shifts |
| **03_ARCHITECTURE.md** | Mark DatabentoDataService as IMPLEMENTED. Update any interface changes. |
| **10_PHASE3_SPRINT_PLAN.md** | Move Sprint 12 to completed table. Record outcomes. |
| **CLAUDE.md** | Update Current State to reflect Sprint 12 complete, next sprint. |
| **06_RISK_REGISTER.md** | Update RSK-021 (data feed failure) — now mitigated by circuit breaker. Any new risks identified. |

---

## Questions That May Arise During Review

**Q: Why not use `async for record in live_client` instead of callbacks?**
A: The Databento Python client's async iteration pattern requires calling `start()` explicitly and manages its own thread internally regardless. The callback pattern (`add_callback`) is the officially documented pattern and gives us explicit control over the thread bridging. Both are valid; we chose callbacks for clarity.

**Q: Why XNAS.ITCH instead of a consolidated feed?**
A: XNAS.ITCH (Nasdaq TotalView) is Databento's most recommended feed for trading firms. It has the deepest historical data (most complete for backtest/live parity), provides L2/L3 when needed, and covers the majority of high-gap NASDAQ-listed stocks that ORB targets. We can add XNYS.PILLAR later if we need NYSE-listed stock coverage. The dataset is configurable.

**Q: Is the DatabentoScanner fully implemented?**
A: No — it's intentionally stub-level for Sprint 12. The key value of this sprint is live streaming (DatabentoDataService) and historical data (DataFetcher). The scanner can be enhanced when we're ready for full-universe scanning. The existing StaticScanner or AlpacaScanner can serve in the interim.

**Q: When does the Databento subscription get activated?**
A: Per DEC-087, after Sprint 12 implementation is complete and ready for integration testing. All development and unit tests use mock clients. The user will activate the subscription manually when ready to test against real data.
