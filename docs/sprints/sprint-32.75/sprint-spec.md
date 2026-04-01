# Sprint 32.75: The Arena + UI/Operational Sweep

## Goal
Deliver The Arena — a dedicated real-time multi-chart position visualization page showing all open positions as synchronized, live-updating candlestick charts — alongside 13 UI bug fixes and polish items and 5 operational fixes identified in the April 1, 2026 market session debrief.

## Scope

### Deliverables

1. **Strategy identity system completion** — All 12 strategies have unique colors, badge abbreviations, display names, and single-letter identifiers across every component in the application.

2. **The Arena page** — 9th Command Center page displaying all open positions as a responsive grid of mini-candlestick charts with sub-second live updates, entry/exit animations, price level overlays, and attention-weighted priority sizing.

3. **Dashboard layout overhaul** — Removal of low-value cards (Recent Trades, System Status), repositioning of Signal Quality and AI Insight, inline Positions toggle, and VIX Regime card redesign.

4. **Orchestrator page fixes** — Total P&L Today and Trades Today display real session data. Capital Allocation uses strategy colors and display names. Catalyst headlines are clickable links.

5. **TradeChart price line bug fix** — Position detail panel renders exactly one set of Entry/Stop/T1/Current price markers regardless of data update frequency.

6. **AI Insight context enhancement** — SystemContextBuilder provides full portfolio context, not just top-5 positions.

7. **Operational fixes** — Broker overflow capacity raised to 60, post-IBKR-reconnect portfolio query delay, per-strategy end-of-window evaluation summary logging.

8. **IBC setup documentation** — Complete setup guide for IB Controller auto-restart with launchd plist template and credential management documentation.

### Acceptance Criteria

1. Strategy identity system:
   - All 12 strategies render unique non-grey colors in Dashboard, Orchestrator, Performance, Arena, and Pattern Library pages
   - Badge component shows unique abbreviation for each strategy (no "STRA" fallbacks)
   - `getStrategyDisplay()` returns correct config for all 12 strategy IDs (with and without `strat_` prefix)
   - Session Timeline shows all 12 strategies with correct operating windows
   - AllocationDonut renders all 12 strategies in unique colors with display names (not `strat_xxx` format)

2. The Arena:
   - Renders ≥30 simultaneous TradingView Lightweight Charts instances with no visible render lag
   - Each chart displays ~30 minutes of 1-minute candles with the current candle updating sub-second from tick data
   - Price level lines visible: entry (blue dashed), stop (red solid), T1 (green dashed), trailing stop (yellow, updates dynamically)
   - New positions animate in (fade + scale); closed positions flash exit color and dissolve
   - Grid reflows smoothly when positions open/close
   - Sort by: entry time (default), strategy, P&L, urgency (proximity to stop/target)
   - Filter by strategy via dropdown
   - Aggregate stats bar shows: position count, total unrealized P&L, net R-multiple, entries/exits in last 5 minutes
   - Empty state when no positions open
   - Accessible via 9th nav item

3. Dashboard overhaul:
   - Recent Trades and System Status cards removed from all three responsive layouts (phone, tablet, desktop)
   - Signal Quality and AI Insight card positions swapped (Signal Quality in 3-card row with Today's Stats and Session Timeline)
   - All/Open/Closed toggle rendered inline with Positions card header (no extra row)
   - VIX Regime card condensed or enriched (no longer occupying full row for minimal data)

4. Orchestrator page fixes:
   - Total P&L Today reflects sum of closed trades' P&L for current ET date
   - Trades Today reflects count of closed trades for current ET date
   - Capital Allocation legend uses display names from strategyConfig
   - Catalyst Alert headlines are anchor tags with `target="_blank"` and `rel="noopener noreferrer"`

5. TradeChart fix:
   - Price lines removed and recreated on each data update (no accumulation)
   - Position detail panel chart shows exactly one Entry line, one Stop line, one T1 line, one Current line

6. AI Insight:
   - SystemContextBuilder includes all open positions (not just top 5) in context payload
   - AI responses reference full portfolio state, not partial data

7. Operational fixes:
   - `overflow.broker_capacity` set to 60 in `config/overflow.yaml`
   - After IBKR reconnection, first portfolio query delayed 3s with retry if snapshot returns significantly fewer positions than expected
   - Each strategy logs summary at end of operating window: symbols evaluated, signals generated, rejection counts by reason
   - Stop retry exhaustion (42/day on April 1) investigated and findings documented

8. IBC documentation:
   - `docs/ibc-setup.md` covers: IBC installation, configuration, credential storage, launchd plist setup, verification steps
   - Template launchd plist at `scripts/ibc/com.argus.ibgateway.plist`

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Arena render latency (30 charts) | < 100ms per frame | Chrome DevTools Performance tab |
| Arena render latency (60 charts) | < 200ms per frame | Chrome DevTools Performance tab |
| Arena WebSocket throughput | 60 messages/sec sustained | Backend log analysis |
| Arena initial load (REST) | < 2s for 30 positions | Network tab timing |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default | Change |
|-----------|---------------|------------|---------|--------|
| `overflow.broker_capacity` | `OverflowConfig` | `broker_capacity` | 30 | → 60 |

No new config fields introduced. One existing field value change.

## Dependencies
- Sprint 32.5 complete and merged to main
- TradingView Lightweight Charts (already in package.json)
- Framer Motion (already in package.json)
- Existing WebSocket infrastructure (`api/websocket/` module)
- Existing IntradayCandleStore (DEC-368) providing candle data
- Existing PositionUpdatedEvent WebSocket publishing (Sprint 29.5)

## Relevant Decisions
- DEC-368: IntradayCandleStore — provides candle data for Arena REST endpoint
- DEC-342: Strategy evaluation telemetry — end-of-window logging follows this pattern
- DEC-369/370: Reconciliation safety — post-reconnect delay must not interfere with broker-confirmed position tracking
- DEC-375: Overflow routing — broker_capacity change affects overflow threshold
- DEC-109: Design north star — Arena visual design should match existing dark theme

## Relevant Risks
- RSK-022: IB Gateway nightly resets — IBC setup documentation addresses this
- Performance risk: 30-60 simultaneous chart instances may stress browser rendering. TradingView LC is designed for this but needs empirical validation.

## Session Count Estimate
12 sessions + 0.5 visual-review contingency = 12.5 sessions. Organized in 5 parallel waves. Large sprint justified by three independent work streams (UI polish, operational fixes, Arena page) that share minimal file overlap and parallelize well. Critical path is 5-6 sequential steps even with 12 total sessions.
