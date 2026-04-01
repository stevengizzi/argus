# Sprint 32.75, Session 9: MiniChart Component

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/ui/src/components/TradeChart.tsx` (existing TradingView LC usage), `argus/ui/src/features/arena/index.ts`
2. Scoped tests: `cd argus/ui && npx vitest run src/features/arena/`
3. Branch: `sprint-32.75-session-9`

## Objective
Create standalone MiniChart (TradingView LC wrapper) and ArenaCard (card frame with overlays) components.

## Requirements
1. **Create `ui/src/features/arena/MiniChart.tsx`**:
   - Props: `candles: CandleData[]`, `entryPrice`, `stopPrice`, `targetPrices`, `trailingStopPrice`, `width`, `height`
   - Create TradingView LC chart instance in useEffect with cleanup (`chart.remove()`)
   - Dark theme matching app (background transparent, grid subtle)
   - Candlestick series with candle data from props
   - Price level lines via createPriceLine: entry (blue #3b82f6, dashed), stop (red #ef4444, solid), T1 (green #22c55e, dashed), trailing stop (yellow #eab308, dashed). Track lines in ref, clean up on re-render (S4 pattern).
   - Time axis: minimal labels, no crosshair, compact.
   - Expose imperative handle via `useImperativeHandle` + `forwardRef` for live updates in S11: `updateCandle(candle)`, `updateTrailingStop(price)`, `appendCandle(candle)`

2. **Create `ui/src/features/arena/ArenaCard.tsx`**:
   - Props: position data (symbol, strategy_id, pnl, r_multiple, hold_seconds, entry/stop/target/trailing prices, candles)
   - Layout: Strategy badge + symbol (top-left), P&L + R (top-right, green/red color), MiniChart (center, fills available space), hold timer (bottom-left, counts up), stop-to-T1 progress bar (bottom, thin gradient red→green showing where price sits between stop and T1)
   - Card border: 1px with strategy color (from strategyConfig)

## Constraints
- MiniChart must be a pure component — no data fetching, no WebSocket
- Chart size responsive to card container
- Do NOT import from any page-level components
- Use the TradingView Lightweight Charts API already in package.json

## Test Targets
- MiniChart creates chart instance on mount and removes on unmount
- MiniChart creates correct number of price lines
- ArenaCard renders all overlay elements
- ArenaCard formats P&L correctly (green positive, red negative)
- Progress bar computes position between stop and T1
- Minimum: 6 tests
- Command: `cd argus/ui && npx vitest run src/features/arena/`

## Visual Review
1. MiniChart renders candles with correct colors on dark background
2. Price level lines visible and correctly colored
3. ArenaCard shows all overlay elements (badge, P&L, timer, progress bar)
4. Card looks good at various sizes (280px to 400px wide)

## Definition of Done
- [ ] MiniChart renders static candles with price levels
- [ ] ArenaCard frame with all overlays
- [ ] Imperative handle exposed for live updates
- [ ] Close-out: `docs/sprints/sprint-32.75/session-9-closeout.md`
- [ ] Tier 2 review via @reviewer
