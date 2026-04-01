# Sprint 32.75, Session 4: Bug Fixes + AI Context

## Pre-Flight Checks
1. Read context:
   - `docs/sprints/sprint-32.75/review-context.md`
   - `argus/ui/src/components/TradeChart.tsx` (lines 210-295)
   - `argus/ai/system_context.py`
2. Run scoped tests: `python -m pytest tests/ai/ -x -q && cd argus/ui && npx vitest run src/components/TradeChart.test.tsx`
3. Verify branch: `sprint-32.75-session-4`

## Objective
Fix the duplicate price labels bug in the position detail chart and enhance AI Insight's portfolio context.

## Requirements

1. **TradeChart price line fix** — In `ui/src/components/TradeChart.tsx`, in the useEffect starting at ~line 213:
   - Add a `useRef` to track created price line objects: `const priceLinesRef = useRef<ReturnType<typeof candleSeries.createPriceLine>[]>([])`
   - At the start of the effect (before creating new lines), remove all tracked price lines: `priceLinesRef.current.forEach(line => candleSeries.removePriceLine(line)); priceLinesRef.current = [];`
   - Store each newly created price line in the ref array
   - In the cleanup function of the useEffect, also remove all tracked price lines

2. **AI Insight context enhancement** — In `argus/ai/system_context.py` (SystemContextBuilder):
   - Find where position data is injected into the context (look for "top 5" or similar limiting logic)
   - Expand to include ALL open positions (up to 50 for context window management)
   - Include per-position: symbol, strategy, side, entry_price, current_price, unrealized_pnl, r_multiple, hold_duration
   - Add portfolio summary: total position count, total unrealized P&L, count by strategy, count winning vs losing

## Constraints
- Do NOT modify TradeChart's candlestick data handling or chart initialization
- Do NOT change the chart's visual appearance beyond fixing the duplicate lines
- Do NOT modify the AI API call logic, prompt templates, or Claude model selection
- Do NOT change any other dashboard or position panel components

## Test Targets
- TradeChart test: verify createPriceLine called exactly once per price level after data update (mock test)
- TradeChart test: verify removePriceLine called before recreating lines on second data update
- AI context test: verify SystemContextBuilder includes all positions when >5 exist
- Minimum: 4 new/updated tests
- Command: `cd argus/ui && npx vitest run src/components/TradeChart.test.tsx`

## Visual Review
1. **Position detail panel**: Open a position detail, wait for several tick updates — only one set of Entry/Stop/T1/Current labels should appear on the price axis
2. **AI Insight card**: Ask Copilot about current positions — response should reference the full portfolio, not say "positions not shown in the top 5"

Verification conditions: App running with open positions and AI enabled

## Definition of Done
- [ ] TradeChart creates exactly one set of price lines regardless of data updates
- [ ] SystemContextBuilder injects full portfolio context
- [ ] All tests pass
- [ ] Close-out written to `docs/sprints/sprint-32.75/session-4-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| TradeChart renders candles correctly | Existing test: candle data set correctly |
| Price lines show correct prices | Existing test: createPriceLine called with correct entry/stop/target values |
| AI Copilot still responds | Test endpoint returns 200 |

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-4-closeout.md`

## Tier 2 Review
Test command: `python -m pytest tests/ai/ -x -q && cd argus/ui && npx vitest run src/components/TradeChart.test.tsx`. Files NOT to modify: TradeChart chart initialization, AI prompt templates, Claude model config.

## Session-Specific Review Focus
1. Verify price line cleanup happens BEFORE new creation (not after) — wrong order would flash empty then repopulate
2. Verify the useRef tracks the actual return value of createPriceLine(), not just the options object
3. Verify AI context doesn't exceed context window limits with 50+ positions (check token estimate)
