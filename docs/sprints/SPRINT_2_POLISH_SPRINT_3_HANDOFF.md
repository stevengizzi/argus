# ARGUS — Sprint 2 Polish Review + Sprint 3 Planning Handoff

> **Date:** February 15, 2026
> **Purpose:** Start a fresh conversation to (1) review the Sprint 2 polish transcript, (2) confirm Sprint 2 is finalized, and (3) produce the full Sprint 3 implementation spec.
> **Instructions:** Paste this document as your first message. Then paste the Claude Code Sprint 2 polish session transcript. After the review is confirmed, say "Ready for Sprint 3 spec" and Claude will produce the full Sprint 3 handoff.

---

## What Happened Before This Conversation

### Sprint 2 Implementation (Complete)
Sprint 2 built: Broker ABC, SimulatedBroker, BrokerRouter, Risk Manager (account-level), 107 tests passing, ruff clean. All committed.

### Sprint 2 Code Review (Complete)
A thorough review was conducted. Overall assessment: **solid, ship it.** Six categories of issues were identified and a Claude Code prompt was created to address them. Here's what the polish prompt asked for:

#### Fix 1: Store strategy_id on PendingBracketOrder directly
The `simulate_price_update()` method had a fragile fallback Position construction just to extract `strategy_id`. Fix: add `strategy_id` field to `PendingBracketOrder`, populate from entry order in `place_bracket_order()`, use directly in `simulate_price_update()`.

#### Fix 2: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`
`datetime.utcnow()` is deprecated in Python 3.12+. Replace all occurrences across Sprint 2 files.

#### Fix 3: Reconstruct weekly P&L on restart
`reconstruct_state()` only rebuilt daily P&L, not weekly. Safety bug — mid-week restart would reset the weekly loss limit to zero. Fix: query TradeLogger for trades from Monday through today, sum into `_weekly_realized_pnl`. Also reconstruct PDT day trades for the rolling window. May require adding `get_trades_by_date_range()` to TradeLogger.

#### Fix 4: Add missing tests
- **4a:** Buying power modification path test (Risk Manager step 6, independent from step 5)
- **4b:** `reconstruct_state()` tests — daily P&L, weekly P&L, PDT trades reconstruction
- **4c:** Partial bracket fill test — the core ORB exit pattern (T1 fills 50%, stop remains for other 50%, T2 fills remaining)

#### Fix 5: Document implicit decisions in code comments
- SimulatedBroker `buying_power = cash` (no margin in V1) — comment explaining divergence with real brokers
- `PositionClosedEvent` optional timestamps — comment explaining why optional and when they'll be required

### Design Decision Made: Cash Reserve Basis (DEC-037)
The Risk Manager's cash reserve calculation was discussed. Current behavior uses `account.equity` (includes unrealized P&L), which creates a perverse incentive where drawdowns lower the reserve threshold.

**Decision: Use start-of-day equity (option b).**
- The Risk Manager stores `_start_of_day_equity` during `reset_daily_state()`
- Reserve = `_start_of_day_equity * cash_reserve_pct`
- Stable throughout the day, immune to unrealized P&L swings
- Resets naturally each morning via the Orchestrator's pre-market routine

**This change may or may not have been included in the polish prompt. If not, it should be flagged for the user to add as a follow-up fix or included in Sprint 3.**

---

## What This Session Should Do

### Part 1: Review the Sprint 2 Polish Transcript

Review the pasted Claude Code transcript for:

1. **Were all 5 fixes implemented?** Check each one off.
2. **Did any fixes introduce new issues?** Especially Fix 3 (weekly P&L reconstruction) since it touches the TradeLogger interface.
3. **Test count:** Should be ~112+ (107 original + 4-5 new tests from Fix 4).
4. **Ruff clean?**
5. **Was the cash reserve basis change (DEC-037 — start-of-day equity) implemented?** If not, flag it.

Output a structured review with ✅/⚠️/❌ per fix.

### Part 2: Confirm Sprint 2 Finalized

If all fixes pass review, confirm Sprint 2 is done.

Draft all pending document updates so the user can copy-paste-commit:

**Decision Log entries needed:**
- DEC-035 (Sprint 2 micro-decisions) — content drafted below
- DEC-036 (SimulatedBroker has no margin model) — content drafted below
- DEC-037 (Cash reserve uses start-of-day equity) — content drafted below

**Other docs:**
- CLAUDE.md — update Current State
- Risk Register — add RSK-013 (weekly loss limit reset on restart)
- Project Knowledge (02_PROJECT_KNOWLEDGE.md) — update current state and key decisions

All draft content is provided in the "Pre-Drafted Document Updates" section below.

### Part 3: Sprint 3 Spec

After the user confirms Sprint 2 is finalized (they'll say "Ready for Sprint 3 spec" or similar), produce the full Sprint 3 implementation spec.

Sprint 3 scope: **BaseStrategy ABC + Scanner + Data Service + ORB Breakout Strategy**

#### Micro-Decisions Already Made (Do Not Re-Ask)

| ID | Decision | Choice |
|----|----------|--------|
| MD-1 | Scanner architecture | **(a) Build full Scanner module in Sprint 3** — Scanner takes ScannerCriteria from strategies and returns symbols. Fully functional pre-market scanning. |
| MD-2 | Data Service timeframes | Awaiting user selection (options: all 5, 1m only, or framework + 1m) |
| MD-3 | Indicator computation | Awaiting user selection (options: inside Data Service, separate module, or inside strategies) |
| MD-4 | ORB opening range tracking | Awaiting user selection (options: strategy-internal or Data Service indicator) |
| MD-5 | ReplayDataService data format | Awaiting user selection (options: Parquet, CSV, or both) |
| MD-6 | ORB entry order type | Awaiting user selection (options: market order + chase filter, or limit order) |
| MD-7 | Breakout confirmation definition | Awaiting user confirmation of proposed thresholds |

**Important:** MD-1 was answered (option a). MD-2 through MD-7 were presented to the user but NOT yet answered. The new conversation must re-present MD-2 through MD-7 for the user's selection before producing the Sprint 3 spec. Use the same options and recommendations from the prior conversation (reproduced below).

#### MD-2: Data Service timeframes for V1
- **(a)** Build all 5 timeframes (1s, 5s, 1m, 5m, 15m) in ReplayDataService from day one.
- **(b)** Start with 1m only. Add other timeframes when strategies need them.
- **(c)** Build the multi-timeframe framework but only implement 1m for Sprint 3. Configuration declares which timeframes are active.
- **Recommendation:** (c)

#### MD-3: Indicator computation location
- **(a)** Inside Data Service, published as IndicatorEvent on the bus. Strategies consume passively.
- **(b)** Separate IndicatorService module that subscribes to CandleEvent and publishes IndicatorEvent.
- **(c)** Indicators computed inside each strategy as needed. No shared indicators in V1.
- **Recommendation:** (a)

#### MD-4: ORB opening range tracking
- **(a)** ORB tracks internally (strategy-specific daily state). Accumulates CandleEvents during the window.
- **(b)** Data Service provides opening range as a shared indicator via IndicatorEvent.
- **Recommendation:** (a)

#### MD-5: ReplayDataService data format
- **(a)** Parquet only (efficient, typed, standard in quant, 5-10x smaller than CSV).
- **(b)** CSV only (human-readable, easy to inspect).
- **(c)** Both — ReplayDataService auto-detects format.
- **Recommendation:** (a)

#### MD-6: ORB entry order type
- **(a)** Market order — guaranteed fill. Chase protection is a pre-entry filter: skip if price already moved >0.5% past breakout level. Simpler, more reliable.
- **(b)** Limit order at breakout level + chase_protection_pct — controlled slippage, risk of no fill.
- **Recommendation:** (a)

#### MD-7: Breakout confirmation definition (proposed thresholds)
- **Breakout confirmed:** 1-minute candle must *close* above opening range high (for long). Not just a wick.
- **Volume confirmation:** Breakout candle volume > 1.5x average volume of candles during the opening range formation period.
- **VWAP alignment:** Current price is above VWAP at time of breakout.
- User needs to confirm or adjust these thresholds.

#### Key Architecture References for Sprint 3
- BaseStrategy interface: `docs/03_ARCHITECTURE.md` Section 3.4
- Data Service interface: `docs/03_ARCHITECTURE.md` Section 3.2
- ORB strategy rules: `docs/01_PROJECT_BIBLE.md` Section 4.2 (Strategy 1)
- ORB config: `config/strategies/orb_breakout.yaml`
- Strategy template: `docs/04_STRATEGY_TEMPLATE.md`
- Event types: `argus/core/events.py`

#### Sprint 3 Build Order (Preliminary — Finalize After Micro-Decisions)
- Step 6: BaseStrategy ABC + ScannerCriteria model + Scanner module
- Step 7: Data Service abstraction + ReplayDataService + Indicator computation
- Step 8: ORB Breakout strategy implementation (full entry/exit logic)
- Step 9: Tests for all of the above

#### Remaining Phase 1 Sprints (After Sprint 3)
- **Sprint 4** (Steps 8–9 from original plan): Alpaca Broker adapter (real paper trading) + Order Manager (position management, stop adjustments, time stops, EOD flatten)
- **Sprint 5** (Steps 10–11): Health monitoring + Integration testing (3+ days on Alpaca paper trading)

---

## Pre-Drafted Document Updates

These are ready to copy-paste-commit once Sprint 2 polish is confirmed.

### Decision Log — DEC-035

```markdown
### DEC-035 | Sprint 2 Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Five implementation-level decisions for Sprint 2: (1) Weekly loss limit resets on calendar week (Monday). (2) Circuit breaker is internally enforced by Risk Manager (`_circuit_breaker_active` flag), not externally. (3) SimulatedBroker provides `simulate_price_update()` for bracket order testing. (4) PDT threshold is configurable via `pdt.threshold_balance` in risk_limits.yaml (default $25,000). (5) Risk Manager queries Broker for live account state rather than maintaining its own copy. |
| **Rationale** | (1) Simplest correct implementation; matches trading week. (2) Avoids coupling to external state; `reset_daily_state()` clears it. (3) Essential for deterministic bracket order testing without real price feeds. (4) Future-proofs for regulatory changes. (5) Single source of truth for account state avoids stale data bugs. |
| **Status** | Active |
```

### Decision Log — DEC-036

```markdown
### DEC-036 | SimulatedBroker Has No Margin Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | SimulatedBroker sets `buying_power = cash` (no margin). The Risk Manager's cash reserve check (step 5) and buying power check (step 6) currently produce equivalent results. These will diverge when AlpacaBroker introduces margin in Sprint 4. |
| **Alternatives** | Simulate margin in SimulatedBroker |
| **Rationale** | Margin simulation adds complexity with no testing value until real margin data is available. The two-step check structure is correct; only the input data differs between simulated and real brokers. |
| **Status** | Active |
```

### Decision Log — DEC-037

```markdown
### DEC-037 | Cash Reserve Uses Start-of-Day Equity
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | The Risk Manager's cash reserve is calculated as `start_of_day_equity * cash_reserve_pct`. The `_start_of_day_equity` value is snapshotted during `reset_daily_state()` (called by the Orchestrator pre-market). It does not change during the trading day. |
| **Alternatives** | (a) Use live equity (includes unrealized P&L — creates perverse incentive where drawdowns lower the reserve threshold, allowing more risk). (c) Use high water mark (ratchets up permanently — overly conservative, one good day raises the floor forever). |
| **Rationale** | Start-of-day equity is stable throughout the session, immune to unrealized P&L swings, and resets naturally each morning. Avoids the perverse dynamic of live equity while not being permanently ratcheted like high water mark. |
| **Status** | Active |
```

### CLAUDE.md — Current State Update

```markdown
## Current State

Phase 1 — Core Trading Engine with ORB strategy. Sprint 2 complete (Broker Abstraction + Risk Manager). Sprint 3 next (BaseStrategy + Scanner + Data Service + ORB Strategy).

Update this section as development progresses.
```

### Risk Register — RSK-013

```markdown
### RSK-013 — Weekly Loss Limit Reset on Restart
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Description** | If the system restarts mid-week, the weekly realized P&L must be reconstructed from the database. Without reconstruction, the weekly loss limit effectively resets to zero, allowing more risk than intended. |
| **Mitigation** | `reconstruct_state()` method queries TradeLogger for the current week's trades and rebuilds weekly P&L. Implemented and tested in Sprint 2 polish. |
| **Owner** | Risk Manager |
```

### Project Knowledge (02) — Updates

Add to "Key Decisions Made":
```
- **SimulatedBroker margin:** No margin model in V1. buying_power = cash. Diverges from real brokers. DEC-036.
- **Cash reserve basis:** Uses start-of-day equity (snapshotted pre-market), not live equity. DEC-037.
```

Update "Current Project State":
```
**Phase:** Phase 1 in progress. Sprint 2 complete. Sprint 3 next.
**Current sprint:** Sprint 3 — BaseStrategy ABC + Scanner + Data Service + ORB Strategy. Steps 6–9 of 11.
**Next milestone:** ORB strategy producing signals from replayed historical data, validated against manual inspection.
```

---

## Key Decisions in Effect (Do Not Relitigate)

All decisions from the prior conversation remain active:

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

---

## Future Tasks to Track

| Item | When | Context |
|------|------|---------|
| Inject clock/date provider into Risk Manager | Sprint 4 (integration testing) | `date.today()` calls make date-boundary testing hard |
| Verify DEC-037 (start-of-day equity) is implemented | Sprint 2 polish review | May not have been in the original polish prompt — check transcript |

---

*End of Handoff*

**→ PASTE THE CLAUDE CODE SPRINT 2 POLISH SESSION TRANSCRIPT BELOW THIS LINE ←**
