# Sprint 21d — Code Review Plan

## Review Schedule

Three reviews at natural breakpoints, plus a final sign-off:

| Review | After Session | What's Built | Focus |
|--------|--------------|--------------|-------|
| **Review #1** | Session 5 | Backend endpoints, nav restructure, Dashboard complete | Data layer correctness, nav UX, Dashboard layout |
| **Review #2** | Session 10 | All 8 Performance visualizations complete | Chart quality, data accuracy, analytical value |
| **Review #3 (Final)** | Session 13 | Everything built, integration verified | Full system walkthrough, regressions, polish |

## Review Procedure

### Before Each Review

**You (Steven) do:**
1. Run dev mode: `cd argus && python -m argus.api --dev` + `cd argus/ui && npm run dev`
2. Take screenshots at all 3 breakpoints (desktop 1512px, tablet 834px, mobile 393px) for the components built since last review
3. Run test suites and note counts: `pytest` and `cd argus/ui && npx vitest run`
4. Copy the handoff brief (below) into a new Claude conversation in this project
5. Upload screenshots as images in that conversation

**Screenshots needed per review:**

Review #1 (~8 screenshots):
- Dashboard market-hours: desktop, tablet, mobile
- Dashboard pre-market (?premarket=true): desktop, mobile
- Sidebar with dividers: desktop
- Mobile bottom bar (5 tabs): mobile
- More sheet open: mobile

Review #2 (~10 screenshots):
- Performance Overview tab: desktop
- Performance Heatmaps tab: desktop, mobile
- Performance Distribution tab: desktop
- Performance Portfolio tab: desktop
- Performance Replay (paused mid-trade): desktop, mobile
- Calendar P&L close-up: desktop
- Correlation matrix close-up: desktop

Review #3 (~12 screenshots):
- Dashboard market-hours: desktop, mobile
- Dashboard pre-market: desktop
- Performance: 1 screenshot per tab at desktop (5 total)
- System page: desktop
- Copilot panel open: desktop, mobile
- Copilot button visible: mobile
- More sheet: mobile

### During Each Review

**The review conversation should:**
1. Examine all screenshots for visual quality, alignment, responsive behavior
2. Spot-check component code for patterns, accessibility, performance
3. Verify test coverage for new components
4. Flag any issues as: **Must Fix** (before next session) or **Note** (acceptable, track if needed)
5. Confirm or reject: "Review #N PASSED" or "Review #N — fixes needed: [list]"

**I (Claude) will:**
- Compare against sprint spec decisions (DEC-204 through DEC-218)
- Check responsive breakpoint behavior
- Verify design principles (DEC-109): information density, ambient awareness, motion budget
- Flag any deviations from spec
- Draft any new decision log entries if implementation diverged from spec

### After Each Review

**If PASSED:**
- Continue to next session block
- No doc updates needed mid-sprint (all done in Session 14)

**If fixes needed:**
- You run a fix session in Claude Code with the specific issues listed
- Re-screenshot the fixed areas
- Quick re-review (can be lightweight — just confirm fixes)

### Document Updates

**All doc updates happen in Session 14** (final session), not during reviews. This avoids context-switching overhead mid-sprint. The only exception: if a review reveals a design decision that needs to change, I'll draft the DEC entry during the review conversation so you can add it to the decision log immediately (prevents the next Claude Code session from building on a stale decision).

### Post-Sprint Final Sign-Off

After Session 14 completes docs, you paste the updated Project Knowledge into this Claude project's instructions. That's the sync point for the next sprint.


# Sprint 21d — Code Review Handoff Briefs

Copy-paste the appropriate brief into a new Claude conversation in this project to kick off each review.

---

## Review #1 Handoff Brief (After Session 5)

```
Sprint 21d Code Review #1 — Dashboard + Nav + Backend

WHAT WAS BUILT (Sessions 1–5):
- Backend: 4 new API endpoints (heatmap, distribution, correlation, replay) + goals config endpoint + TradeLogger.get_daily_pnl_by_strategy() + dev mock data expansion
- Nav: Desktop sidebar with group dividers (Monitor|Operate|Learn|Maintain), mobile 5-tab + More bottom sheet (MoreSheet.tsx with Framer Motion), 'c' keyboard shortcut for copilot
- Dashboard: OrchestratorStatusStrip (single-line ambient data, click→Orchestrator), HeatStripPortfolioBar (SVG position segments colored by P&L), GoalTracker (monthly target progress from config YAML), PreMarketLayout (time-gated shell with countdown + placeholder cards), removed RiskAllocationPanel/emergency controls (migrated to Orchestrator)

SPRINT SPEC DECISIONS TO VERIFY:
- DEC-204: Dashboard narrowed — status strip replaces full orchestrator widgets
- DEC-211: Sidebar dividers between groups, mobile 5+More pattern
- DEC-213: Pre-market layout is full shell with placeholder cards, time-gated
- DEC-214: GoalTracker reads monthly_target_usd from GoalsConfig in system.yaml
- DEC-216: Mobile primary tabs = Dashboard, Trades, Orchestrator, Patterns, More

TEST COUNTS:
- Expected: ~1683 pytest (1664 + ~19 new) + ~151 Vitest (138 + ~13 new)
- Actual: [FILL IN from test run]

SCREENSHOTS ATTACHED:
[Upload 8 screenshots: Dashboard desktop/tablet/mobile, Dashboard pre-market desktop/mobile, sidebar dividers, mobile bottom bar, More sheet]

REVIEW CHECKLIST:
1. Dashboard layout: Does OrchestratorStatusStrip read well? Is data density right?
2. HeatStripPortfolioBar: Are position segments proportional? Color scale readable?
3. GoalTracker: Does pace calculation make sense? Color transitions correct?
4. PreMarketLayout: Do placeholders look intentional (not broken)? Countdown working?
5. Nav: Are sidebar dividers subtle enough? Does More sheet feel native?
6. Backend: Do endpoint response shapes match what frontend hooks expect?
7. Responsive: Any overflow, truncation, or touch target issues?
8. Test coverage: Any gaps in the new backend endpoints?
```

---

## Review #2 Handoff Brief (After Session 10)

```
Sprint 21d Code Review #2 — Performance Analytics Suite

WHAT WAS BUILT (Sessions 6–10):
- Performance page refactored with 5-tab layout (Overview, Heatmaps, Distribution, Portfolio, Replay)
- TradeActivityHeatmap: D3 color scales + React SVG, 13×5 grid (time×day), click→filter trades
- CalendarPnlView: Custom SVG monthly calendar, daily P&L colors, month navigation
- RMultipleHistogram: Recharts bar chart, 0.25R bins, strategy filter dropdown
- RiskWaterfall: Custom SVG horizontal bars with running total line
- PortfolioTreemap: D3 hierarchy+treemap layout, sized by value, colored by P&L
- CorrelationMatrix: Custom SVG NxN grid, D3 diverging color scale
- ComparativePeriodOverlay: Ghost line on existing EquityCurve (previous period comparison)
- TradeReplay: Lightweight Charts candlestick with playback controls, entry/exit/stop markers, speed selector, scrubber

SPRINT SPEC DECISIONS TO VERIFY:
- DEC-205: All 8 visualizations built in 5-tab layout
- DEC-206: Heatmap uses D3 color scales with React SVG
- DEC-207: Treemap uses D3 hierarchy+treemap (not custom)
- DEC-208: Comparative overlay as ghost line on existing EquityCurve
- DEC-209: Trade Replay uses Lightweight Charts with progressive bar reveal
- DEC-215: Chart library assignments (D3 for treemap/heatmap/correlation, Recharts for histogram, Custom SVG for calendar/waterfall, LWC for replay/overlay)
- DEC-218: Tab organization (Overview, Heatmaps, Distribution, Portfolio, Replay)

TEST COUNTS:
- Expected: ~1689 pytest (1664 + ~25) + ~174 Vitest (138 + ~36 new)
- Actual: [FILL IN from test run]

SCREENSHOTS ATTACHED:
[Upload 10 screenshots: each Performance tab at desktop, Heatmaps tab mobile, Replay desktop+mobile, Calendar close-up, Correlation close-up]

REVIEW CHECKLIST:
1. Tab navigation: Smooth switching? Period selector affects all tabs?
2. Heatmap: Color scale readable? Diverging center correct (0 = neutral)? Cell labels visible?
3. Calendar: Days align correctly? Weekend graying? Month nav works?
4. Histogram: Bins correct (0.25R)? Red/green split at 0? Mean/median annotations?
5. Waterfall: Running total line accurate? Positions sorted by risk?
6. Treemap: Rectangles sized correctly? Labels readable on large rects, hidden on small? Mobile fallback?
7. Correlation: 4×4 matrix renders? Diagonal = 1.0? Color scale -1 to +1?
8. Overlay: Ghost line aligns with current period? Toggle works? Legend clear?
9. Replay: Playback smooth? Markers appear at correct bars? Speed changes work? Scrubber responsive?
10. Responsive: Any chart that breaks on mobile? Treemap mobile fallback working?
11. Dev mock data: Do all charts look plausible with mock data? Any obviously wrong values?
```

---

## Review #3 Handoff Brief — Final Review (After Session 13)

```
Sprint 21d Code Review #3 — Final Review

WHAT WAS BUILT (Sessions 11–13):
- System page: removed StrategyCards + EmergencyControls, added IntelligencePlaceholders (6 future component cards)
- CopilotPanel: slide-out chat shell, page context indicator, placeholder content, disabled input
- CopilotButton: floating action button, adaptive positioning (desktop/mobile), hides when panel open
- copilotUI Zustand store, 'c' keyboard shortcut
- Responsive QA: all components verified at 3 breakpoints
- Skeleton loading states for new components
- Animation tuning (entrance animations, tab transitions, spring physics)
- Full integration verification: dev mode walkthrough, cross-page navigation, keyboard shortcuts

SPRINT SPEC DECISIONS TO VERIFY:
- DEC-210: System narrowed to infrastructure + intelligence placeholders
- DEC-212: CopilotPanel is new component (not SlideInPanel reuse), persists across pages
- DEC-217: Button position — desktop bottom-right 24px, mobile above tab bar

FULL SPRINT SUMMARY:
- Sessions completed: 13 of 14 (Session 14 is docs only)
- New backend: 5 API endpoints, 1 new TradeLogger method, GoalsConfig, dev mock expansion
- New frontend: ~20 new components across Dashboard, Performance, System, Copilot, Navigation
- Chart libraries added: D3 (scale, color, hierarchy, interpolate modules)
- Removed from Dashboard: RiskAllocationPanel (CapitalAllocation, RiskGauge, MarketRegimeCard)
- Removed from System: StrategyCards, EmergencyControls

TEST COUNTS:
- Expected: ~1689 pytest + ~182 Vitest
- Actual: [FILL IN from test run]

SCREENSHOTS ATTACHED:
[Upload 12 screenshots: Dashboard desktop/mobile, Dashboard pre-market desktop, all 5 Performance tabs desktop, System desktop, Copilot panel desktop/mobile, Copilot button mobile, More sheet mobile]

REVIEW CHECKLIST — FULL SYSTEM:
1. Dashboard: StatusStrip → HeatStrip → Cards → Positions → Trades — reads top to bottom?
2. Dashboard pre-market: Feels intentional? Placeholders clearly communicate "coming soon"?
3. Performance suite: All 8 visualizations render with mock data? Analytical value clear?
4. Trade Replay: Most complex component — works smoothly? Any jank?
5. System: Clean after removal? Intelligence placeholders informative?
6. Copilot: Panel opens/closes smoothly? Context indicator accurate? Placeholder content clear?
7. Navigation: Sidebar dividers visible but subtle? Mobile More sheet native-feeling?
8. Keyboard shortcuts: 1–7, w, c all work from every page?
9. Cross-page: Symbol clicks → SymbolDetailPanel from all surfaces? Trade clicks → TradeDetailPanel?
10. Regressions: Orchestrator page unchanged? Pattern Library unchanged? Debrief unchanged?
11. Mobile: Touch targets ≥44px? No horizontal overflow? Safe area padding correct?
12. Animations: All <500ms? Nothing blocks interaction? Skeletons show during load?
13. Console: Any errors or warnings in browser dev tools?

DECISIONS TO LOG:
[List any implementation divergences from spec discovered during sessions — I'll draft DEC entries]

SIGN-OFF:
If this review passes, Session 14 handles all doc updates and Sprint 21d is COMPLETE.
The next sprint is Sprint 22 (AI Layer MVP).
```
