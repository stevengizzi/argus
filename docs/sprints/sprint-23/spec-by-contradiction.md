# Sprint 23: What This Sprint Does NOT Do

## Out of Scope
These items are related to the sprint goal but are explicitly excluded:

1. **NLP Catalyst Pipeline**: No SEC EDGAR filing monitor, no FMP news feed, no Claude API catalyst classification, no CatalystEvent on Event Bus. Deferred to Sprint 23.5 — the Universe Manager is valuable without catalysts (most setups are technical per DEC-263).

2. **Pre-Market Intelligence Brief**: No morning scan summary, no catalyst research, no structured intelligence report. Deferred to Sprint 23.5.

3. **Catalyst badges in UI**: No catalyst quality indicators on Dashboard watchlist or trade entries. Deferred to Sprint 23.5.

4. **AI-generated debrief narratives**: No Claude API narrative generation for The Debrief page. Deferred to Sprint 23.5.

5. **Intraday re-scanning / dynamic universe expansion**: Pre-market universe is held for the full trading day. No periodic FMP re-scans, no dynamic Databento subscription additions mid-session. Deferred to Sprint 23.5+.

6. **Indicator warm-up for broad universe**: IndicatorEngine instances cold-start on viable symbols. ATR/SMA converge after ~20–50 bars (~20–50 minutes of market data). No batch historical bar fetch for 4,000+ symbols at startup. This is acceptable for paper trading. Batch warm-up deferred to future sprint if needed.

7. **FMP plan upgrade**: No upgrade from Starter ($22/mo). Company Profile and Share Float endpoints are available on Starter. Corporate calendars (earnings, IPO) require Premium — deferred to Sprint 23.5 scope assessment.

8. **Finnhub integration**: No Finnhub API integration. FMP + SEC EDGAR (in 23.5) are the planned catalyst data sources. Finnhub deferred unless FMP proves insufficient per DEC-164.

9. **Strategy `behavioral_triggers` config**: DEC-263 mentions strategies declaring `behavioral_triggers` (pattern conditions requiring live indicator data) in addition to `universe_filter`. Sprint 23 implements only `universe_filter` (symbol-level filtering). Behavioral triggers (which require per-candle indicator evaluation) are deferred to Sprint 24+ when the Setup Quality Engine provides the scoring framework.

10. **Strategy code changes**: No modifications to any strategy `.py` files. Only strategy YAML configs change (adding `universe_filter` sections). Strategy logic remains identical.

## Edge Cases to Reject
The implementation should NOT handle these cases in this sprint:

1. **FMP batch endpoint unavailable on Starter plan**: If the batch Company Profile endpoint turns out to require Premium, fall back to sequential single-symbol calls with rate limiting (300/min = 4,000 symbols in ~13 min). Log warning. Do NOT upgrade the FMP plan or halt startup. Flag as ESCALATE in close-out.

2. **Databento ALL_SYMBOLS subscription failure**: If ALL_SYMBOLS mode causes session errors, fall back to the existing scanner-based symbol list. Log error. Do NOT attempt dynamic subscription management. Flag as ESCALATE.

3. **Memory pressure from 8,000+ IndicatorEngine instances**: If memory exceeds 500MB above baseline, log warning. Do NOT implement memory optimization (LRU eviction, lazy instantiation). Flag as ESCALATE.

4. **FMP reference data returns incomplete data** (missing sector, market cap, or float for some symbols): Treat missing fields as "no data" — symbol passes any filter that checks a missing field. Do NOT skip the symbol entirely. Log count of symbols with incomplete data.

5. **Strategy filter matches zero symbols**: Log warning, strategy remains active but receives no candles. Do NOT fall back to static watchlist for that strategy.

6. **Candle events for symbols added to exchange mid-day** (IPOs, resumed halts): These will flow through Databento ALL_SYMBOLS but won't be in the pre-market reference data cache. They will fail the viable universe check (no reference data) and be discarded. Do NOT attempt to dynamically add them — this is intraday expansion, which is out of scope.

## Scope Boundaries
- Do NOT modify: `argus/ai/` (AI layer), `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/` (Order Manager, brokers), `argus/analytics/` (Trade Logger, Performance Calculator), `argus/strategies/*.py` (strategy Python code), `argus/backtest/` (backtesting infrastructure)
- Do NOT optimize: IndicatorEngine computation speed — DEC-263 confirms 2–4% CPU is adequate; Cython deferred to Phase 9+
- Do NOT refactor: Existing scanner classes (`FMPScannerSource`, `DatabentoScanner`, `AlpacaScanner`, `StaticScanner`) — Universe Manager wraps the scanner flow, does not replace scanner implementations
- Do NOT add: WebSocket streaming for universe updates (REST polling is sufficient for Dashboard), catalyst/news data sources, order flow integration, strategy-to-strategy correlation monitoring

## Interaction Boundaries
- This sprint does NOT change the behavior of: Risk Manager, Order Manager, Orchestrator allocation logic, Trade Logger, any strategy's signal generation logic, AI Copilot, any existing API endpoint
- This sprint does NOT affect: Backtesting/replay pipeline, VectorBT sweeps, Replay Harness, existing WebSocket streams (live data, AI chat), notification system

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| NLP Catalyst Pipeline (SEC EDGAR + FMP news + Claude API) | Sprint 23.5 | — |
| Pre-Market Intelligence Brief | Sprint 23.5 | — |
| Catalyst badges in UI | Sprint 23.5 | — |
| AI debrief narratives | Sprint 23.5 | — |
| Intraday re-scanning / dynamic universe expansion | Sprint 23.5+ | — |
| Strategy `behavioral_triggers` config | Sprint 24+ | — |
| Indicator batch warm-up for broad universe | Unscheduled | — |
| FMP plan upgrade (Premium for corporate calendars) | Sprint 23.5 decision | — |
| Finnhub integration | Unscheduled | DEC-164 trigger |
