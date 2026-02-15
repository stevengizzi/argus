# ARGUS — Sprint 3 Review + Sprint 4a Planning Handoff

> **Date:** February 15, 2026
> **Purpose:** Start a fresh conversation to (1) review the Sprint 3 implementation transcript, (2) confirm Sprint 3 is finalized, and (3) produce the full Sprint 4a implementation spec.
> **Instructions:** Paste this document as your first message. Then paste the Claude Code Sprint 3 session transcript. After the review is confirmed, say "Ready for Sprint 4a spec" and Claude will produce the full Sprint 4a handoff.

---

## What Happened Before This Conversation

### Sprint 1 (Complete)
Config system, Event Bus, data models, database (SQLite + aiosqlite), Trade Logger. 52 tests.

### Sprint 2 (Complete)
Broker ABC, SimulatedBroker, BrokerRouter, Risk Manager (account-level). 107 tests.

### Sprint 2 Polish (Complete)
Five code review fixes: PendingBracketOrder strategy_id, datetime.utcnow() deprecation, weekly P&L reconstruction, missing tests (buying power mod, reconstruction, partial bracket fill), code comments. 112 tests. Ruff clean. Committed.

### Sprint 3 Implementation (Under Review)
Sprint 3 built: BaseStrategy ABC, Scanner ABC + StaticScanner, Data Service ABC + ReplayDataService (1m candles, indicator computation), ORB Breakout strategy (full entry/exit logic), integration test. ~150+ tests expected.

Sprint 3 also included a pre-sprint fix: DEC-037 (Risk Manager cash reserve uses start-of-day equity instead of live equity).

---

## What This Session Should Do

### Part 1: Review the Sprint 3 Transcript

Review the pasted Claude Code transcript for:

1. **Was DEC-037 (start-of-day equity) implemented?** Check:
   - `_start_of_day_equity` field added to RiskManager
   - `reset_daily_state()` snapshots current equity
   - `evaluate_signal()` step 5 uses `_start_of_day_equity`
   - Fallback to live equity if `_start_of_day_equity == 0`
   - Tests for the above

2. **Were all Sprint 3 components built?** Check each:
   - [ ] Config models (OrbBreakoutConfig, DataServiceConfig, ScannerConfig)
   - [ ] Strategy models (ScannerCriteria, ExitRules, ProfitTarget, MarketConditionsFilter, WatchlistItem)
   - [ ] BaseStrategy ABC (all methods from Architecture doc 3.4)
   - [ ] Scanner ABC + StaticScanner
   - [ ] Data Service ABC + ReplayDataService (Parquet, 1m candles)
   - [ ] Indicator computation (VWAP, ATR(14), RVOL, SMA 9/20/50)
   - [ ] OrbBreakout strategy (OR formation, breakout detection, signal emission)
   - [ ] Integration test (scanner → data → strategy → risk → broker)

3. **ORB Breakout correctness check:**
   - Does OR form correctly from the first `orb_window_minutes` of candles?
   - Does breakout detection require candle *close* above OR high (not just wick)?
   - Is volume confirmation checked (1.5x average of OR candles)?
   - Is VWAP alignment checked?
   - Is chase protection applied (skip if price > OR high + 0.5%)?
   - Is the stop at OR midpoint (per DEC-012)?
   - Are targets at 1R and 2R?
   - Does position sizing follow the formula: `shares = risk_dollars / (entry - stop)`?

4. **ReplayDataService correctness:**
   - Does it read Parquet files?
   - Does it publish CandleEvents in chronological order?
   - Does it compute and publish IndicatorEvents?
   - Are indicators computed correctly (especially VWAP daily reset)?
   - Does `get_current_price()` return latest close?
   - Does `get_indicator()` return latest computed value?

5. **Did any implementation deviate from the spec?** Flag deviations. If they're reasonable improvements, note them as potential new decisions to log.

6. **Test count:** Target ~150+. Count them.

7. **Ruff clean?**

Output a structured review with ✅/⚠️/❌ per component.

### Part 2: Confirm Sprint 3 Finalized

If all components pass review, confirm Sprint 3 is done.

Draft all pending document updates:

**Decision Log entries needed:**
- DEC-038 (Sprint 3 micro-decisions) — collect any implementation decisions from the transcript
- Any new decisions made during Sprint 3 implementation

**Other docs:**
- CLAUDE.md — update Current State to "Sprint 3 complete"
- Project Knowledge (02) — update current state, add any new key decisions
- Architecture (03) — update if any interfaces changed from the spec
- Risk Register (06) — add any new risks identified

### Part 3: Sprint 4a Spec

After the user confirms Sprint 3 is finalized (they'll say "Ready for Sprint 4a spec" or similar), produce the full Sprint 4a implementation spec.

Sprint 4a scope: **Alpaca Broker Adapter + Alpaca Data Service (Live Connections)**

#### Sprint 4a Components (Preliminary)

1. **AlpacaDataService** — Implements the `DataService` ABC using Alpaca's WebSocket + REST APIs
   - WebSocket streaming for real-time tick and trade data
   - Real-time 1m candle building from tick data
   - Live indicator computation (VWAP, ATR, RVOL, SMAs — same as ReplayDataService)
   - Stale data detection (30-second timeout)
   - Implements the same interface as ReplayDataService — strategies can't tell the difference

2. **AlpacaBroker** — Implements the `Broker` ABC using `alpaca-trade-api` SDK
   - Paper trading mode (connects to `paper-api.alpaca.markets`)
   - Implements: `place_order`, `place_bracket_order`, `cancel_order`, `modify_order`, `get_positions`, `get_account`, `get_order_status`, `flatten_all`
   - WebSocket subscription for order status updates
   - Handles Alpaca-specific order types and responses

3. **Clock injection** — Injectable Clock protocol for date-boundary testing (DEF-001)

4. **Integration:** AlpacaDataService → OrbBreakout → RiskManager → AlpacaBroker end-to-end with paper trading

#### Micro-Decisions to Present for Sprint 4a
These should be identified during the Sprint 3 review. Likely topics:
- Alpaca WebSocket handling (library choice, reconnection strategy)
- Candle building from ticks vs. subscribing to Alpaca's bar stream directly
- Error handling for Alpaca API failures (retry policy, fallback behavior)
- How to test AlpacaBroker without live market hours (mock strategies, recorded responses)

---

## Key Decisions in Effect (Do Not Relitigate)

All decisions from DEC-001 through DEC-037 remain active, plus Sprint 3 micro-decisions:

| ID | Summary |
|----|---------|
| DEC-027 | Risk Manager approve-with-modification. Reduce shares (0.25R floor), tighten targets. Never modify stops/entry/side. |
| DEC-028 | Strategies: daily-stateful, session-stateless. Reset between days, reconstruct from DB on restart. |
| DEC-029 | Data delivery via Event Bus only. No callback subscription on DataService. Sync queries retained. |
| DEC-030 | Order Manager: event-driven (tick subscription) + 5s fallback poll + scheduled EOD flatten. |
| DEC-031 | IBKR adapter deferred to Phase 3+. Only SimulatedBroker and AlpacaBroker in Phase 1. |
| DEC-032 | Config via Pydantic BaseModel. YAML → Pydantic flow. |
| DEC-033 | Event Bus: type-only subscription. Filtering in handlers, not at bus level. |
| DEC-034 | Async DB via aiosqlite. DatabaseManager owns connection. TradeLogger is sole persistence interface. |
| DEC-035 | Sprint 2 micro-decisions (calendar week, internal circuit breaker, simulate_price_update, PDT threshold, broker state queries). |
| DEC-036 | SimulatedBroker has no margin model (buying_power = cash). |
| DEC-037 | Cash reserve uses start-of-day equity, not live equity. |
| MD-1 | Scanner ABC + StaticScanner. Real AlpacaScanner in Sprint 4. |
| MD-2 | Multi-timeframe framework, only 1m in Sprint 3. |
| MD-3 | Indicators inside Data Service, published as IndicatorEvent. |
| MD-4 | ORB tracks opening range internally. |
| MD-5 | Parquet only for ReplayDataService. |
| MD-6 | Market order + chase protection filter. |
| MD-7 | Candle close > OR high, volume > 1.5x OR avg, price > VWAP. |

---

## Future Tasks to Track

| Item | When | Context |
|------|------|---------|
| Inject clock/date provider into Risk Manager | Sprint 4a | `date.today()` calls make date-boundary testing hard |
| AlpacaScanner (real pre-market scanning) | Sprint 4b | Replace StaticScanner with live Alpaca screener |
| Order Manager (position lifecycle management) | Sprint 4b | Stop-to-breakeven, time stops, EOD flatten |
| Multi-timeframe candle aggregation | When needed | Framework exists, only 1m implemented |
| RVOL baseline from historical data | Sprint 4a+ | Current RVOL may be approximate |
| Short selling support | After long-only ecosystem proven | DEC-011 |

---

## Remaining Phase 1 Sprints

- **Sprint 4a** (next): Alpaca Data Service (live WebSocket streaming, candle building, indicators) + Alpaca Broker adapter (paper trading) + Clock injection
- **Sprint 4b**: Order Manager (position lifecycle, stop adjustments, time stops, EOD flatten) + AlpacaScanner (real pre-market scanning)
- **Sprint 5**: Health monitoring + Integration testing (3+ days on Alpaca paper trading)

---

*End of Handoff*

**→ PASTE THE CLAUDE CODE SPRINT 3 SESSION TRANSCRIPT BELOW THIS LINE ←**
