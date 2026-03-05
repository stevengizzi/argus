# Performance Workbench — Design Brief (DEC-229)

> Deferred from Sprint 21d. Estimated 11–14 sessions + 2 code reviews. Slot as Sprint 21e when ready.

---

## Vision

Transform the Performance page from a fixed 5-tab layout into a customizable widget grid — a "Performance Workbench" where the user can arrange, resize, and compose visualizations into personalized analysis workflows. The goal is to evolve from "dashboard" to "trading workstation."

### Why This Matters

1. **Scale:** ARGUS currently has 8 visualizations. By Sprint 25+ there will be 15+ (setup quality distributions, order flow depth, catalyst timelines, strategy-specific breakdowns). Fixed tabs require a design decision for each new visualization ("which tab?"). A widget grid means new visualizations join the palette and the user places them.

2. **Personal workflows:** Different analysis contexts need different layouts:
   - *Morning Prep:* Calendar P&L + heatmap + risk waterfall — "how did I do recently, what's my exposure?"
   - *Post-Session Review:* R-multiple distribution + trade replay + correlation matrix — "what happened today?"
   - *Weekly Report:* Equity curve + treemap + comparative overlay — "big picture"
   - These are personal workflows, not generic presets. The user builds them.

3. **Information density:** Side-by-side pairing (DEC-227) was a step in this direction, but the grid approach handles it systematically — equal row heights, snap alignment, and proper aspect ratio constraints per widget type.

### Design North Star

"Bloomberg Terminal meets Grafana." Dense, customizable, information-rich — but dark-themed, polished, and purpose-built for trading analysis. Not a generic dashboard builder; every widget is a trading-specific visualization.

---

## Implementation Stages

### Stage 1 — Rearrangeable Presets (~4–5 sessions + 1 code review)

**Goal:** Existing 5 tabs become grid layouts that you can rearrange and resize. Layouts persist.

**Tasks:**
1. Install `react-grid-layout` (or `react-grid-layout` with `react-resizable`)
2. Define a `WidgetDefinition` type for each visualization:
   ```typescript
   interface WidgetDefinition {
     id: string;                    // e.g., 'equity-curve', 'heatmap', 'r-distribution'
     component: React.ComponentType;
     label: string;
     icon: string;
     minW: number;  // minimum grid columns
     minH: number;  // minimum grid rows
     maxW?: number;
     maxH?: number;
     defaultW: number;
     defaultH: number;
   }
   ```
3. Define min/max size constraints per widget:
   - **Equity Curve:** needs width (minW: 6, minH: 3) — time series needs horizontal space
   - **Daily P&L Histogram:** needs width (minW: 6, minH: 2)
   - **Trade Activity Heatmap:** needs both (minW: 5, minH: 4) — 13×5 grid
   - **Calendar P&L:** needs width (minW: 5, minH: 4) — 7-column calendar
   - **R-Multiple Histogram:** moderate (minW: 4, minH: 3)
   - **Risk Waterfall:** taller than wide (minW: 3, minH: 4)
   - **Portfolio Treemap:** needs area (minW: 4, minH: 3)
   - **Correlation Matrix:** compact (minW: 3, minH: 3)
   - **Comparative Overlay:** same as equity curve (minW: 6, minH: 3)
   - **Trade Replay:** needs both (minW: 6, minH: 5) — chart + controls + info panel
   - **Metrics Grid:** wide, short (minW: 6, minH: 1)

4. Convert existing 5 tab layouts to serialized `react-grid-layout` `Layout[]` objects:
   ```typescript
   const DEFAULT_LAYOUTS: Record<string, Layout[]> = {
     overview: [
       { i: 'metrics-grid', x: 0, y: 0, w: 12, h: 1 },
       { i: 'equity-curve', x: 0, y: 1, w: 12, h: 4 },
       { i: 'daily-pnl', x: 0, y: 5, w: 12, h: 3 },
     ],
     heatmaps: [
       { i: 'heatmap', x: 0, y: 0, w: 12, h: 5 },
       { i: 'calendar', x: 0, y: 5, w: 12, h: 5 },
     ],
     // ... etc
   };
   ```

5. Wrap each visualization component in a `WidgetCard` shell (title bar, optional strategy filter, drag handle)

6. Enable drag-to-rearrange and resize within each tab

7. **Layout persistence via backend:**
   - New API endpoint: `GET/PUT /api/v1/user/layouts`
   - Schema: `{ tabs: [{ id, label, layout: Layout[] }] }`
   - Save on every layout change (debounced 1–2s)
   - Load on page mount, fall back to DEFAULT_LAYOUTS if no saved layout

8. Equal row heights come for free from `react-grid-layout`'s row-based grid

**Responsive behavior:**
- Desktop (≥1024px): Full grid, 12-column, drag and resize enabled
- Tablet (640–1023px): Reduced grid (6 or 8 columns), drag enabled, resize may be disabled
- Mobile (<640px): Single-column stack, no drag/resize — fixed order per tab

**Code Review Checkpoint:** Verify resize snap feel, min/max constraints prevent illegible charts, mobile fallback works, layouts persist across page refresh and browser restart.

### Stage 2 — Full Workbench (~5–7 sessions + 1 code review)

**Goal:** Widget palette, custom tabs, drag-from-palette.

**Tasks:**
1. **Widget Palette / Sandbox:**
   - Horizontal strip or collapsible panel at top of the Performance page
   - Shows all available widgets as small preview tiles (icon + label)
   - Widgets already on the current tab are visually marked (e.g., checkmark or dimmed)
   - A widget can appear on multiple tabs (independent instances)

2. **Drag from palette to grid:**
   - Drag a widget tile from the palette into the grid area
   - Drop creates a new widget instance at default size
   - Grid items shift to accommodate (react-grid-layout handles this)

3. **Custom tab CRUD:**
   - "+" button to create a new tab (prompt for name)
   - Right-click or long-press tab label to rename or delete
   - Reorder tabs via drag (optional — nice to have)
   - Default tabs (Overview, Heatmaps, Distribution, Portfolio, Replay) are restorable but deletable
   - Empty tab state: "Drag widgets from the palette above to build your layout"

4. **Widget removal:**
   - "×" button on widget card title bar (visible on hover or always in edit mode)
   - Removing a widget from a tab doesn't delete it — it returns to the palette as available

5. **Keyboard shortcuts:**
   - Existing `o/h/d/p/r` become dynamic (map to tab index or let user assign)
   - `n` to create new tab (when on Performance page)
   - Consider `e` to toggle edit mode (show drag handles, resize grippers, remove buttons) vs always-on editing

6. **Backend persistence update:**
   - `PUT /api/v1/user/layouts` now includes custom tabs: `{ tabs: [{ id, label, isCustom, layout }] }`
   - Tab order, names, and layouts all serialized

7. **Mobile fallback:**
   - Custom tabs exist on mobile but use a predetermined single-column stack based on widget order in the layout
   - Palette is accessible but uses an "add" button + modal picker instead of drag-and-drop

**Code Review Checkpoint:** Full workbench UX across desktop/tablet/mobile. Custom tab CRUD. Palette interaction. Persistence of custom layouts. Migration path from Stage 1 saved layouts.

---

## Technical Notes

### Library Choice
`react-grid-layout` is the recommended library. It handles:
- Drag and drop with collision avoidance
- Resize with snap to grid
- Responsive layouts (different Layout[] per breakpoint)
- Serializable layouts (JSON-friendly)
- Used by Grafana, Jupyter, and many analytics platforms

Install: `npm install react-grid-layout @types/react-grid-layout`

CSS: Import `react-grid-layout/css/styles.css` and `react-resizable/css/styles.css`. Override with Tailwind/dark theme styles as needed.

### Backend Schema
```python
# New Pydantic model
class PerformanceLayout(BaseModel):
    tabs: list[LayoutTab]

class LayoutTab(BaseModel):
    id: str
    label: str
    is_custom: bool = False
    layout: list[LayoutItem]

class LayoutItem(BaseModel):
    i: str      # widget ID
    x: int
    y: int
    w: int
    h: int

# New endpoint in api/routes/
# GET  /api/v1/user/layouts → PerformanceLayout (or defaults if none saved)
# PUT  /api/v1/user/layouts → save PerformanceLayout
```

Storage: SQLite table `user_layouts` with single row (single-user system), JSON column for serialized layout. Or simpler: JSON file in data directory.

### Widget-Level Props
Each widget component should accept standardized props:
```typescript
interface WidgetProps {
  period: Period;           // from period selector
  strategyFilter?: string;  // from strategy dropdown (where applicable)
  compact?: boolean;        // true when widget is at/near minimum size
}
```

The `compact` prop allows widgets to simplify their rendering at small sizes (hide legends, reduce label density, etc.). This extends the existing `compact` pattern from DEC-183.

---

## Dependencies

- All 8 Performance visualizations complete (DEC-205) ✅
- Unified color scale (DEC-224) ✅
- Dynamic text contrast (DEC-225) ✅
- Side-by-side layout (DEC-227) — will be superseded by grid but validates the concept ✅

## Decisions Made

- DEC-229: Performance Workbench approved and deferred
- Backend API persistence (not localStorage/storage API) — keeps user state centralized
- react-grid-layout as library choice
- Two-stage rollout (presets first, then full workbench)
- DEC-218 (fixed 5-tab organization) superseded when implemented

## Open Questions (Resolve When Building)

1. Should the metrics grid row (Trades, Win Rate, Profit Factor, etc.) be a draggable widget or always pinned at the top?
2. Should the period selector live in the page header (outside the grid) or be a widget itself?
3. Grid row height in pixels — needs tuning during implementation (48px? 60px? depends on content density)
4. Should widget instances share filter state (one strategy dropdown affects all widgets on the tab) or have independent filters?
