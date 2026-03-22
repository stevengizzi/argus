# Sprint 26, Session 10f: Visual Review Fixes

## Context
Visual review of the Pattern Library page and broader app after S10 + dev_state fix revealed two issues with the 3 new strategies (Red-to-Green, Bull Flag, Flat-Top Breakout):

1. **Strategy badge labels show "STRA"** — The short-label map in the badge component doesn't have entries for the new strategy IDs. Dashboard Session Summary shows "STRA STRA STRA" instead of meaningful abbreviations.
2. **New strategies missing from System Status and System page Components** — Health monitor components for the 3 new strategies weren't registered in `dev_state.py`.

## Pre-Flight
1. Read these files to find the badge label map:
   ```bash
   grep -rn "ORB\|SCALP\|VWAP\|MOM" argus/ui/src/ --include="*.tsx" --include="*.ts" -l
   ```
   Then read the file(s) containing the short-label mapping (likely a badge or tag component).

2. Read `argus/api/dev_state.py` to check health component registration.

3. Run baseline:
   ```bash
   cd argus/ui && npx vitest run
   ```

## Fix 1: Strategy Badge Short Labels

Find the component that maps strategy IDs to short display labels (the one producing "ORB", "SCALP", "VWAP", "MOM"). Add entries for:
- `red_to_green` → `"R2G"`
- `bull_flag` → `"FLAG"`
- `flat_top_breakout` → `"FLAT"`

If there's also a color map for strategy badges, add appropriate colors for the new strategies. Use distinct colors that don't collide with the existing four. Suggested: R2G = orange/amber, FLAG = teal/cyan, FLAT = purple/violet — but match the project's existing color palette conventions.

## Fix 2: Health Components in dev_state.py

Check `argus/api/dev_state.py` for the health status mock. The 3 new strategies need health components registered matching the naming convention in `main.py` Phase 9:
```python
# These should already exist for the original 4:
# strategy_orb, strategy_orb_scalp, strategy_vwap_reclaim, strategy_afternoon_momentum
# Add matching entries for:
# strategy_red_to_green, strategy_bull_flag, strategy_flat_top_breakout
```

All 3 should show `status: "healthy"` in the mock, matching the existing strategies.

## Constraints
- Do NOT modify `main.py`, `base_strategy.py`, `events.py`, `orchestrator.py`
- Do NOT modify any strategy source files or pattern modules
- Do NOT modify PatternCard.tsx, PatternFilters.tsx, or PatternLibraryPage.tsx (those are S10 deliverables, already correct)
- Frontend changes should be limited to the badge/label component and any associated color maps
- Backend changes limited to `dev_state.py`

## Test Targets
- Update or add Vitest tests to verify the new badge labels render correctly
- Update `test_dev_state_patterns.py` if health component assertions exist
- Run full suites:
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  cd argus/ui && npx vitest run
  ```

## Verification
After fixes, restart both servers and confirm:
1. Dashboard Session Summary: badges show R2G, FLAG, FLAT (not STRA)
2. Dashboard System Status: all 7 strategy health components listed as healthy
3. System page Components card: all 7 strategies listed
4. No regressions on Pattern Library page (still 7 cards, filters work)

## Close-Out
Write to: `docs/sprints/sprint-26/session-10f-closeout.md`
Include structured closeout JSON block.