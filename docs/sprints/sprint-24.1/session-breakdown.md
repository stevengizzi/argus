# Sprint 24.1 — Session Breakdown

## Dependency Chain

```
S1a (trades quality wiring) ──→ S2 (e2e test + EFTS)
S1b (trivial backend fixes)  ──→ (independent)
S3  (TypeScript fixes)        ──→ S4a, S4b
S4a (layout fixes)            ──→ S4f (contingency)
S4b (interactivity)           ──→ S4f (contingency)
```

S1a and S1b can run in either order. S3 is independent of all backend sessions.
S4a and S4b depend on S3 (fix TS errors before adding more frontend code).
S2 depends on S1a (exercises the quality wiring).

---

## Session 1a: Trades Quality Column Wiring

**Objective:** Wire quality_grade and quality_score through the full trades persistence chain so completed trades store quality data and the frontend shows actual badges.

**Items:** 2 (DEF-058)

**Creates:** Nothing
**Modifies:** `argus/db/schema.sql`, `argus/models/trading.py`, `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`
**Integrates:** N/A (completes backend chain; API routes in `api/routes/trades.py` + frontend `Trade` type already pre-wired)
**Parallelizable:** false (single logical chain, cannot be split)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 0 | 0 |
| Files modified | 4 (schema.sql, trading.py, order_manager.py, trade_logger.py) | 4 |
| Pre-flight context reads | 5 (core/events.py, schema.sql, trading.py, order_manager.py, trade_logger.py) | 5 |
| New tests | ~8 | 4 |
| Complex integration wiring | 1 (4-file chain: schema → model → order_manager → trade_logger) | 3 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **16 (High — accepted)** |

**Accepted justification:** All 4 modifications are small surgical changes along a single logical chain. Splitting creates half-wired state. No new files. No external APIs.

### Key Implementation Notes
- Schema: `ALTER TABLE trades ADD COLUMN quality_grade TEXT; ALTER TABLE trades ADD COLUMN quality_score REAL;` — idempotent via IF NOT EXISTS or try/except
- ManagedPosition: add `quality_grade: str = ""` and `quality_score: float = 0.0` with defaults
- `_handle_entry_fill()` (~line 500): populate from `signal.quality_grade` and `signal.quality_score`
- `_close_position()` (~line 1190): pass `quality_grade` and `quality_score` from ManagedPosition to Trade constructor
- Trade model: add optional fields with defaults
- TradeLogger: add to INSERT column list and params tuple; add to `_row_to_trade()` with fallback for NULL rows

---

## Session 1b: Trivial Backend Fixes

**Objective:** Execute 5 small independent backend fixes — log level, public accessors, PROVISIONAL comments, seed script guard.

**Items:** 1, 3, 12, 13 (plus EFTS diagnostic prep for S2)

**Creates:** Nothing
**Modifies:** `argus/main.py`, `argus/intelligence/quality_engine.py`, `argus/api/routes/quality.py`, `config/system.yaml`, `config/system_live.yaml`, `scripts/seed_quality_data.py`
**Integrates:** N/A (all independent fixes)
**Parallelizable:** false (small session, not worth splitting)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 0 | 0 |
| Files modified | 6 | 6 |
| Pre-flight context reads | 4 (main.py, quality_engine.py, quality.py routes, seed script) | 4 |
| New tests | ~4 | 2 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **12 (Medium)** |

### Key Implementation Notes
- Item 1: `argus/main.py` line 559: `logger.debug(...)` → `logger.warning(...)`
- Item 3: `quality_engine.py`: add `@property def db(self)` returning `self._db` and `@property def config(self)` returning `self._config`. Update `quality.py` routes: 5 occurrences of `._db` → `.db` and `._config` → `.config`. Remove `# type: ignore[union-attr]` comments.
- Item 12: Add `# NOTE: Thresholds are PROVISIONAL — recalibrate after Sprint 28` comment to quality_engine section in both system.yaml and system_live.yaml
- Item 13: Add argparse flag `--i-know-this-is-dev` to seed script. Print warning and `sys.exit(1)` if not passed.

---

## Session 2: ArgusSystem E2E Quality Test + EFTS Validation

**Objective:** Write a true end-to-end integration test that exercises the full quality pipeline through ArgusSystem, plus validate the EFTS URL.

**Items:** 8, 4 (DEF-050, DEF-057)

**Creates:** `tests/integration/test_quality_pipeline_e2e.py` (or similar location)
**Modifies:** Possibly `argus/intelligence/sources/sec_edgar.py` (only if EFTS URL is broken)
**Integrates:** Exercises Session 1a's trades quality wiring through full system
**Parallelizable:** false (depends on S1a, complex context)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 (e2e test file) | 2 |
| Files modified | 0–1 (sec_edgar.py only if EFTS broken) | 0.5 |
| Pre-flight context reads | 8 (main.py, quality_engine.py, position_sizer.py, risk_manager.py, config, events.py, order_manager.py, strategy base) | 8 |
| New tests | ~8 | 4 |
| Complex integration wiring | 1 (full ArgusSystem init with mocked broker/data) | 3 |
| External API debugging | 0 (EFTS diagnostic is just a curl, not debugging) | 0 |
| Large files (>150 lines) | 1 (e2e test likely >150 lines) | 2 |
| **Total** | | **19.5 (Critical — accepted)** |

**Accepted justification:** Creates only 1 file, modifies 0. All compaction risk is from context reads — if compaction occurs, there is no broken state to roll back, only lost test progress. The test file is self-contained.

### Key Implementation Notes
- ArgusSystem init with: quality_engine enabled, BrokerSource != SIMULATED (use a mock broker), mock DataService, at least one strategy instance
- Feed a SignalEvent with pattern_strength > 0 and share_count=0 through `_process_signal()`
- Assert: quality_engine.score_setup() produced a score, sizer.calculate_shares() returned > 0, risk_manager.evaluate_signal() received enriched signal with quality_grade and quality_score
- Use in-memory SQLite for both argus.db and catalyst.db
- EFTS diagnostic: single curl to `https://efts.sec.gov/LATEST/search-index?dateRange=custom&startdt=2026-03-13&forms=8-K,4`. Document HTTP status and response shape. Fix sec_edgar.py only if URL is broken.

---

## Session 3: TypeScript Build Fixes

**Objective:** Fix all 22 pre-existing `tsc --noEmit` strict-mode errors to achieve zero TypeScript errors.

**Items:** 7 (DEF-059)

**Creates:** Nothing
**Modifies:** ~8-11 files: `src/api/types.ts`, `src/components/CatalystAlertPanel.tsx`, `src/features/copilot/ChatMessage.tsx`, `src/features/copilot/StreamingMessage.tsx`, `src/features/copilot/CopilotPanel.tsx`, `src/features/copilot/TickerText.tsx`, `src/features/dashboard/AIInsightCard.tsx`, `src/features/dashboard/PositionDetailPanel.tsx`, `src/features/debrief/journal/ConversationBrowser.tsx`, `src/pages/PatternLibraryPage.tsx`, `src/pages/TradesPage.tsx`
**Integrates:** N/A
**Parallelizable:** false (modifications across many files, but all simple type fixes)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 0 | 0 |
| Files modified | ~10 | 10 |
| Pre-flight context reads | ~3 (types.ts, Card component types, tsconfig) | 3 |
| New tests | 0 (validation = tsc --noEmit + Vitest) | 0 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **13 (Medium)** |

### Error Categories and Fixes

| Category | Count | Files | Fix |
|----------|-------|-------|-----|
| CardHeaderProps missing `icon` | 4 | CatalystAlertPanel, AIInsightCard (×3) | Extend CardHeader type or restructure prop passing |
| `child.props` unknown (React.Children) | 4 | ChatMessage (×2), StreamingMessage (×2) | Cast to `React.ReactElement` |
| Unused variables (TS6133) | 2 | CopilotPanel (`pageKey`), ConversationBrowser (`EASE`) | Remove or prefix with `_` |
| Missing JSX namespace | 1 | TickerText | Import React or use `React.JSX.Element` |
| StrategyInfo missing fields | 3 | PatternLibraryPage | Add `live_metrics` and `backtest_metrics` to StrategyInfo type |
| Trade type field mismatch | 2 | TradesPage | Use `pnl_dollars`/correct field names or add missing fields |
| Unused destructured var (TS6133) | 1 | PositionDetailPanel (`entryPrice`) | Remove or prefix with `_` |
| **Total** | **~17 fixes across 22 errors** | | |

---

## Session 4a: Frontend Layout Fixes

**Objective:** Fix Orchestrator 3-column layout and relocate QualityOutcomeScatter from Debrief to Performance.

**Items:** 5, 6 (DEF-055, DEF-056)

**Creates:** Nothing
**Modifies:** `src/pages/OrchestratorPage.tsx`, Debrief page/tab files, Performance page/tab files
**Integrates:** N/A
**Parallelizable:** false (small session)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 0 | 0 |
| Files modified | ~3-4 | 3.5 |
| Pre-flight context reads | 3 | 3 |
| New tests | ~2 | 1 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **7.5 (Low)** |

### Key Implementation Notes
- Item 5: OrchestratorPage — wrap Decision Log, Catalyst Alerts, and Recent Signals in a responsive 3-column grid (`grid grid-cols-1 lg:grid-cols-3 gap-4` or similar)
- Item 6: Move `QualityOutcomeScatter` import and usage from Debrief Quality tab → Performance Distribution tab. Remove the Quality tab entirely from Debrief. Remove 'q' shortcut from keyboard navigation. Update DebriefPage docstring.

---

## Session 4b: Frontend Interactivity

**Objective:** Add interactivity to quality UI components — tooltips, legends, quality columns in Dashboard tables, clickable signal rows.

**Items:** 9, 10, 11 (DEF-052, DEF-053, DEF-054)

**Creates:** 1 file (signal detail panel/expandable row component)
**Modifies:** Dashboard quality cards (QualityDistributionCard, SignalQualityPanel), Dashboard Positions/Recent Trades tables, Orchestrator RecentSignals
**Integrates:** N/A
**Parallelizable:** false (interrelated UI changes)

### Compaction Risk Score

| Factor | Detail | Points |
|--------|--------|--------|
| New files created | 1 (signal detail component) | 2 |
| Files modified | ~4-5 | 4.5 |
| Pre-flight context reads | ~4 | 4 |
| New tests | ~3 | 1.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **12 (Medium)** |

### Key Implementation Notes
- Item 9: Add Recharts `<Tooltip>` to donut chart segments. Add `<Legend>` component. Histogram bars already support tooltips via Recharts — verify and enhance.
- Item 10: Add QualityBadge column to Dashboard Positions table and Recent Trades table. Same pattern as Trades page quality column.
- Item 11: Add expandable row or modal to RecentSignals. Show quality_grade, quality_score, component scores, entry/stop/pattern_strength. May use existing detail panel pattern or create new SignalDetailPanel component.

---

## Session 4f: Visual Review Fixes (Contingency)

**Objective:** Fix any visual issues discovered during Session 4a/4b review.

**Items:** Issues found during 4a/4b visual review
**Scope:** 0.5 session budget. If no issues found, session is unused.

---

## Summary Table

| Session | Items | Scope | Score | Status |
|---------|-------|-------|-------|--------|
| S1a | 2 | Trades quality column wiring | 16 (High — accepted) | Backend |
| S1b | 1, 3, 12, 13 | Trivial backend fixes | 12 (Medium) | Backend |
| S2 | 8, 4 | ArgusSystem e2e test + EFTS | 19.5 (Critical — accepted) | Backend |
| S3 | 7 | TypeScript build fixes | 13 (Medium) | Frontend |
| S4a | 5, 6 | Frontend layout fixes | 7.5 (Low) | Frontend |
| S4b | 9, 10, 11 | Frontend interactivity | 12 (Medium) | Frontend |
| S4f | — | Visual review fixes (contingency) | — | Frontend |
