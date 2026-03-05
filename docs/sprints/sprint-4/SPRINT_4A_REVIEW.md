# ARGUS — Sprint 4a Review

## Purpose
Review the Sprint 4a Claude Code session transcripts and confirm Sprint 4a is finalized.

## What Sprint 4a Delivered
- **Clock protocol** (`argus/core/clock.py`): SystemClock, FixedClock, Clock protocol. Injected into Risk Manager + BaseStrategy. Resolves DEF-001. 14 tests.
- **AlpacaConfig** (`argus/core/config.py`): New config model for Alpaca connections. Updated `config/brokers.yaml`.
- **Dependencies**: `alpaca-py>=0.30`, `python-dotenv>=1.0`. `.env.example` created. `.env` confirmed in `.gitignore`.
- **AlpacaDataService** (`argus/data/alpaca_data_service.py`): Implements DataService ABC via alpaca-py. WebSocket streaming (bars + trades), indicator computation, warm-up, stale data monitoring, reconnection with backoff. 20 tests.
- **AlpacaBroker** (`argus/execution/alpaca_broker.py`): Implements Broker ABC via alpaca-py. REST + WebSocket, order ID mapping, bracket orders (single T1 target), event publishing. 19 tests.
- **Integration tests**: 2 tests — full pipeline with mocks, bracket order flow.
- **Total tests**: 277 (276 passing, 1 flaky pre-existing)

## What to Review

For each transcript, check:

1. **Does AlpacaDataService correctly implement the DataService ABC?**
   - start() / stop() / get_current_price() / get_indicator() / get_historical_candles()
   - Bar handler → CandleEvent + IndicatorEvents published to Event Bus
   - Trade handler → TickEvent published, price cache updated
   - Indicator warm-up from historical data (60 candles)
   - VWAP daily reset at market open
   - Stale data monitor (30s timeout)
   - WebSocket reconnection (exponential backoff, jitter)
   - asyncio integration pattern (did it use Pattern 1 — _run_forever coroutine?)

2. **Does AlpacaBroker correctly implement the Broker ABC?**
   - place_order / place_bracket_order / cancel_order / modify_order / get_positions / get_account / flatten_all
   - Order ID mapping (ULID ↔ Alpaca UUID)
   - TradingStream handler maps fill/cancel/reject to our events
   - Bracket order uses single T1 target (Alpaca limitation acknowledged)
   - API keys loaded from environment (never hardcoded)
   - Error handling for Alpaca API failures

3. **Clock injection correctness:**
   - Risk Manager uses clock.now() and clock.today() instead of datetime.now()/date.today()
   - BaseStrategy uses clock similarly
   - Existing tests still pass with default SystemClock
   - FixedClock used in new tests where date control needed

4. **Any implementation deviations from the spec (SPRINT_4A_SPEC.md)?**
   - Flag deviations. If they're reasonable improvements, note for Decision Log.

5. **Test quality:**
   - Target was ~66 new tests, actual is ~55 (14 + 20 + 19 + 2). Assess coverage gaps.
   - The 1 flaky pre-existing test — what is it? Should we fix it?
   - Are mocks realistic? Do they test the right boundaries?

6. **Ruff clean?**

## After Review

If Sprint 4a passes review:
1. Confirm Sprint 4a is done
2. Draft all document updates:
   - DEC-039 for Decision Log (Sprint 4a micro-decisions — may already be drafted in prior session)
   - CLAUDE.md — update Current State, Tech Stack, mark DEF-001 done
   - 02_PROJECT_KNOWLEDGE.md — update current state, add new key decisions
   - 03_ARCHITECTURE.md — replace alpaca-trade-api with alpaca-py in Technology Stack
   - 07_PHASE1_SPRINT_PLAN.md — mark Sprint 4a ✅ Complete with test count
   - Note any new risks or assumptions for Risk Register
3. Flag anything that should be fixed before Sprint 4b begins

Do NOT proceed to Sprint 4b planning — that will happen in a separate session.

→ PASTE THE CLAUDE CODE SPRINT 4a SESSION TRANSCRIPTS BELOW THIS LINE ←