# Sprint 32.75, Session 12: Arena Animations + Polish

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/ui/src/pages/ArenaPage.tsx`, `argus/ui/src/features/arena/ArenaCard.tsx`
2. Scoped tests: `cd argus/ui && npx vitest run src/features/arena/`
3. Verify branch: `main`
4. S11 merged

## Objective
Add entry/exit animations, attention-weighted priority sizing, and polish to the Arena.

## Requirements
1. **Entry animation**: Wrap ArenaCard grid items with Framer Motion `AnimatePresence`. New cards: `initial={{ opacity: 0, scale: 0.95 }}` → `animate={{ opacity: 1, scale: 1 }}` with `transition={{ duration: 0.3 }}`.

2. **Exit animation**: Exiting cards: `exit={{ opacity: 0 }}` with `transition={{ duration: 0.5 }}`. Before exit, briefly flash card background (green tint `bg-green-500/10` for profit, red tint `bg-red-500/10` for loss) for 300ms, then fade out. Grid reflows smoothly as cards are removed (Framer Motion layout animations).

3. **Attention-weighted priority sizing**: Compute priority score (0-1) per card every 2 seconds:
   - Proximity to stop: `(price - stop) / (entry - stop)` closer to 0 = higher priority
   - Proximity to T1: `(T1 - price) / (T1 - entry)` closer to 0 = higher priority
   - Take `1 - min(proximity_to_stop, proximity_to_T1)` as priority score
   - Map to grid column span: score > 0.7 → `span 2` (double-wide), else `span 1`
   - Smooth CSS transitions on size change: `transition: all 500ms ease`

4. **Disconnection indicator**: When WS status is `disconnected` or `error`, show a translucent overlay banner across the grid: "Connection lost — reconnecting..."

5. **Final polish**: Ensure keyboard shortcut for Arena page (suggest `a`). Verify mobile layout works (single column on phone).

## Constraints
- Do NOT modify chart rendering or data flow (S9/S11)
- Priority sizing must not cause layout thrashing (recompute at most every 2 seconds)
- Animations must not block chart updates

## Test Targets
- Entry/exit animations trigger on position add/remove
- Priority score computation correct
- Disconnection overlay appears on WS disconnect
- Minimum: 3 tests
- Command: `cd argus/ui && npx vitest run src/features/arena/`

## Visual Review
1. New position cards animate in smoothly (scale + fade)
2. Closed positions flash green/red then dissolve
3. High-priority cards (near stop or T1) are visually larger
4. Grid reflows without jarring jumps when cards enter/exit
5. Disconnection overlay visible when WS disconnects

## Definition of Done
- [ ] Entry/exit animations working
- [ ] Priority sizing functional
- [ ] Disconnection indicator visible
- [ ] Keyboard shortcut registered
- [ ] Mobile layout verified
- [ ] Full test suite passes: `cd argus && python -m pytest -x -q -n auto && cd argus/ui && npx vitest run`
- [ ] Close-out: `docs/sprints/sprint-32.75/session-12-closeout.md`
- [ ] Tier 2 review via @reviewer (FINAL session — full suite in review)

## Session-Specific Review Focus
1. Verify AnimatePresence wraps the grid item list correctly (common Framer Motion pitfall: key must be stable per-position)
2. Verify priority recomputation interval is 2s not per-frame
3. Verify mobile single-column layout still works with priority span overrides
4. Final session: verify ALL 4,400+ pytest + 700 Vitest pass
