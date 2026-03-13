# Sprint 24: Session Breakdown (Revised)

> **Post-adversarial-review revision.** Key changes: Session 6 split into 6a/6b, Session 7 simplified (on-demand live fetch removed), risk_manager.py carve-out for share_count guard.

## Dependency Chain

```
Session 1 (SignalEvent + ORB) ──→ Session 2 (VWAP + AfMo) ──→──┐
                                                                 │
Session 3 (Firehose Sources) ──→──────────────────────────────┐  │
                                                              │  │
Session 4 (Quality Engine) ──→ Session 5a (Sizer + Config) ──┤  │
                                                              │  │
                               Session 5b (YAML + DB) ───────┤  │
                                                              │  │
                                                              ↓  ↓
                                        Session 6a (Pipeline Wiring + Unit Tests)
                                                              │
                                                              ↓
                                        Session 6b (Integration Tests + Error Paths)
                                                              │
                                                              ↓
                                    Session 7 (Server Init + Firehose Pipeline)
                                                              │
                                                              ↓
                                              Session 8 (API Routes)
                                                              │
                                                              ↓
                                     Session 9 (FE: Components + Hooks + Trades)
                                                              │
                                                              ↓
                                     Session 10 (FE: Orchestrator + Dashboard)
                                                              │
                                                              ↓
                                     Session 11 (FE: Performance + Debrief)
                                                              │
                                                              ↓
                                     Session 11f (Visual-Review Fixes — contingency)
```

---

## Session 1: SignalEvent Enrichment + ORB Family Pattern Strength

**Objective:** Add pattern_strength, signal_context, quality_score, quality_grade fields to SignalEvent. Add QualitySignalEvent (informational, for UI) to events.py. Implement pattern_strength scoring for ORB Breakout and ORB Scalp via shared logic in OrbBaseStrategy. Update ORB signal builders to set share_count=0.

**Creates:** —
**Modifies:** `argus/core/events.py`, `argus/strategies/orb_base.py`, `argus/strategies/orb_breakout.py`, `argus/strategies/orb_scalp.py`
**Integrates:** N/A
**Parallelizable:** false

**Pattern strength factors (ORB family — computed in OrbBaseStrategy):**
- Volume ratio credit: how far above volume_threshold_rvol? (at threshold = 40, 3× threshold = 90)
- ATR ratio credit: how ideal is OR range size? (mid-range of bounds = 80, extremes = 30)
- Chase distance credit: how close is breakout to OR high? (at OR high = 90, at chase_protection_pct = 30)
- VWAP position credit: how far above VWAP? (just above = 50, strongly above = 80, diminishing returns)
- Weighted combination to 0–100 pattern_strength. signal_context includes raw factor values.

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 | 4 |
| Pre-flight context reads | 2 (base_strategy.py, data/service.py) | 2 |
| New tests | ~18 | 9 |
| **Total** | | **15 (High — exception: breadth not depth, ORB shares base class)** |

---

## Session 2: VWAP Reclaim + Afternoon Momentum Pattern Strength

**Objective:** Implement pattern_strength scoring for VWAP Reclaim and Afternoon Momentum. Update signal builders to set share_count=0.

**Creates:** —
**Modifies:** `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`
**Integrates:** Session 1 (new SignalEvent fields)
**Parallelizable:** false

**Pattern strength factors (VWAP Reclaim):**
- State machine path quality: clean pullback→hold→reclaim = 85, messy = 40
- Pullback depth: 0.3–0.5× VWAP distance optimal = 80, too shallow/deep = 35
- Reclaim volume vs pullback average: >1.5× = 80, <1.0× = 30
- Distance-to-VWAP: at VWAP = 90, >1% away = 40

**Pattern strength factors (Afternoon Momentum):**
- Entry condition margin: per-condition credit for >10% above threshold
- Consolidation tightness: range/ATR (0.3 = 90, 0.8 = 40)
- Volume surge: breakout vs consolidation average (>2× = 85, <1.2× = 30)
- Time-in-window: 2:00 = 80, 3:15 = 35

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 3 | 3 |
| New tests | ~12 | 6 |
| **Total** | | **11 (Medium)** ✓ |

---

## Session 3: DEC-327 Firehose Source Refactoring

**Objective:** Refactor Finnhub and SEC EDGAR sources from per-symbol polling to feed-level pulls. Add `firehose: bool` parameter to `fetch_catalysts()`.

**Creates:** —
**Modifies:** `argus/intelligence/sources/finnhub.py`, `argus/intelligence/sources/sec_edgar.py`
**Integrates:** N/A (independent)
**Parallelizable:** false

**Finnhub firehose:**
- New `_fetch_general_news()`: `GET /news?category=general` (1 call)
- New `_associate_symbols()`: maps `related` field to tickers; items without `related` get empty symbol
- `fetch_catalysts(firehose=True)` calls general news. Recommendations still per-symbol (no firehose endpoint).

**SEC EDGAR firehose:**
- New `_fetch_recent_filings_firehose()`: EFTS full-text search for 8-K, Form 4 (1 call)
- Maps filings to symbols via reverse CIK→ticker lookup
- `fetch_catalysts(firehose=True)` calls firehose method.

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~18 | 9 |
| **Total** | | **13 (Medium)** ✓ |

---

## Session 4: Quality Engine Core

**Objective:** Create SetupQualityEngine with 5 dimension scorers per defined rubrics, grade mapping, risk tier assignment. Pure stateless scoring — dependencies passed as arguments. Target <150 lines.

**Creates:** `argus/intelligence/quality_engine.py`
**Modifies:** —
**Integrates:** N/A
**Parallelizable:** false

**Module design:**
- `SetupQuality` dataclass: score, grade, risk_tier, components dict, rationale
- `QualityGrade` constants: A_PLUS through C_MINUS
- `score_setup(signal, catalysts, rvol, regime, allowed_regimes) → SetupQuality`
- Dimension scorers follow rubrics from spec:
  - `_score_pattern_strength(signal)` → passthrough signal.pattern_strength
  - `_score_catalyst_quality(catalysts)` → max quality_score from 24h catalysts, or 50
  - `_score_volume_profile(rvol)` → breakpoint mapping with interpolation, or 50
  - `_score_historical_match()` → constant 50
  - `_score_regime_alignment(regime, allowed)` → 80 if in list, 20 if not, 70 if empty
- `_grade_from_score(score)` → configurable thresholds
- `_risk_tier_from_grade(grade)` → midpoint of grade's range (flat within grade)

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~22 | 11 |
| **Total** | | **15 (High — exception: single file, test count inflates, low cognitive complexity)** |

---

## Session 5a: Dynamic Position Sizer + Config Models

**Objective:** Create DynamicPositionSizer. Add Pydantic config models with validators (including `enabled` field, weight sum validation).

**Creates:** `argus/intelligence/position_sizer.py`
**Modifies:** `argus/intelligence/config.py`
**Integrates:** Session 4 (references SetupQuality, QualityGrade)
**Parallelizable:** false

**Sizer design (~80 lines):**
- `calculate_shares(quality, entry_price, stop_price, allocated_capital, buying_power) → int`
- `risk_pct = midpoint(config.risk_tiers[quality.grade])` — flat within grade
- `shares = int(allocated_capital * risk_pct / abs(entry_price - stop_price))`
- Buying power check: `if shares * entry_price > buying_power: reduce`
- Return `max(0, shares)`

**Config validators:**
- `QualityWeightsConfig`: `@model_validator` — `sum(weights) == 1.0` (±0.001), startup fails with `ValidationError` if violated
- `QualityThresholdsConfig`: each in [0, 100], strictly descending
- `QualityRiskTiersConfig`: each pair min ≤ max, both in [0.0, 1.0]
- `QualityEngineConfig`: `enabled: bool = True`, `min_grade_to_trade` valid grade string

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~12 | 6 |
| **Total** | | **11 (Medium)** ✓ |

---

## Session 5b: Config Wiring + YAML + DB Schema

**Objective:** Add `quality_engine: QualityEngineConfig` to SystemConfig. Create `config/quality_engine.yaml`. Add quality_history table to schema.sql. Update both system.yaml and system_live.yaml.

**Creates:** `config/quality_engine.yaml`
**Modifies:** `argus/core/config.py`, `argus/db/schema.sql`, `config/system.yaml`, `config/system_live.yaml`
**Integrates:** Session 5a (QualityEngineConfig referenced by SystemConfig)
**Parallelizable:** false

**quality_engine.yaml includes:**
```yaml
# NOTE: With Historical Match stubbed at 50 (Sprint 24), effective score range
# is ~7.5 to ~92.5. Grade thresholds are PROVISIONAL — recalibrate after Sprint 28.
enabled: true
weights: { pattern_strength: 0.30, catalyst_quality: 0.25, volume_profile: 0.20, historical_match: 0.15, regime_alignment: 0.10 }
thresholds: { a_plus: 90, a: 80, a_minus: 70, b_plus: 60, b: 50, b_minus: 40, c_plus: 30 }
risk_tiers: { a_plus: [0.02, 0.03], a: [0.015, 0.02], ... }
min_grade_to_trade: "C+"
```

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 4 | 4 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~8 | 4 |
| **Total** | | **12 (Medium)** ✓ |

---

## Session 6a: Pipeline Wiring + Unit Tests

**Objective:** Wire Quality Engine + Dynamic Sizer into `_on_candle_for_strategies()`. Add backtest bypass (BrokerSource.SIMULATED) and config bypass (enabled=false). Add share_count=0 defensive guard in Risk Manager (check 0). Add `record_quality_history()` to quality engine. Unit test each branch.

**Creates:** —
**Modifies:** `argus/main.py`, `argus/intelligence/quality_engine.py` (add record_quality_history), `argus/core/risk_manager.py` (one-line guard)
**Integrates:** Sessions 1+2 (SignalEvent), 4 (engine), 5a (sizer), 5b (DB schema)
**Parallelizable:** false

**Signal flow in `_on_candle_for_strategies()`:**
```python
signal = await strategy.on_candle(event)
if signal is not None:
    # Bypass: backtest mode or quality engine disabled
    if self._broker_source == BrokerSource.SIMULATED or not self._quality_engine_enabled:
        # Legacy sizing: use strategy's risk formula
        shares = self._legacy_calculate_shares(signal, strategy)
        enriched = dataclasses.replace(signal, share_count=shares)
        result = await self._risk_manager.evaluate_signal(enriched)
        await self._event_bus.publish(result)
        continue

    # Quality pipeline
    catalysts = await self._catalyst_storage.get_catalysts_by_symbol(signal.symbol, ...)
    rvol = await self._data_service.get_indicator(signal.symbol, "rvol")
    quality = self._quality_engine.score_setup(signal, catalysts, rvol, ...)

    if quality.grade below min_grade_to_trade:
        await self._quality_engine.record_quality_history(signal, quality, shares=0)
        continue

    shares = self._position_sizer.calculate_shares(quality, ...)
    if shares <= 0:
        await self._quality_engine.record_quality_history(signal, quality, shares=0)
        continue

    enriched = dataclasses.replace(signal, share_count=shares, quality_score=..., quality_grade=...)
    await self._quality_engine.record_quality_history(enriched, quality)
    await self._event_bus.publish(QualitySignalEvent(...))
    result = await self._risk_manager.evaluate_signal(enriched)
    await self._event_bus.publish(result)
```

**Risk Manager guard (check 0):**
```python
if signal.share_count <= 0:
    return OrderRejectedEvent(signal=signal, reason="Invalid share count: zero or negative")
```

| Factor | Count | Points |
|--------|-------|--------|
| Files modified | 3 (main.py, quality_engine.py, risk_manager.py) | 3 |
| Pre-flight context reads | 4 (position_sizer.py, events.py, risk_manager.py, storage.py) | 4 |
| New tests | ~10 unit tests (one per branch) | 5 |
| Complex integration wiring | 1 | 3 |
| **Total** | | **15 (High — exception: irreducible integration, Split from original 16.5)** |

---

## Session 6b: Integration Tests + Error Paths

**Objective:** Full integration tests running multiple signals through the quality pipeline. Error path tests. Backtest bypass verification. Canary test setup.

**Creates:** —
**Modifies:** Test files only
**Integrates:** Session 6a (pipeline wired)
**Parallelizable:** false

**Test coverage:**
- Multiple signals with varied pattern_strength → different grades and share counts
- Quality engine exception → fail-closed (signal does not execute)
- CatalystStorage unavailable → catalyst dimension = 50 (neutral fallback)
- Sizer returns 0 → signal filtered
- C/C- signal → filtered, recorded in quality_history
- Backtest mode (BrokerSource.SIMULATED) → legacy sizing, no quality pipeline
- Config disabled (enabled=false) → legacy sizing
- share_count=0 reaching Risk Manager → rejected by check 0
- Canary: known signals through Replay Harness in simulated mode → identical to pre-sprint

| Factor | Count | Points |
|--------|-------|--------|
| Files modified | 0 (test files only) | 0 |
| Pre-flight context reads | 3 (main.py, quality_engine.py, risk_manager.py) | 3 |
| New tests | ~12 integration tests | 6 |
| **Total** | | **9 (Low)** ✓ |

---

## Session 7: Server Initialization + Firehose Pipeline Integration

**Objective:** Initialize Quality Engine + Sizer in server.py lifespan. Wire firehose mode into CatalystPipeline.run() and polling loop. Update startup.py to construct quality components.

**Creates:** —
**Modifies:** `argus/api/server.py`, `argus/intelligence/__init__.py` (CatalystPipeline), `argus/intelligence/startup.py`
**Integrates:** Sessions 3 (firehose sources), 5b (config), 6a (main.py expects initialized engine)
**Parallelizable:** false

**Changes per file:**
- `server.py` (~15 lines): construct QualityEngine + Sizer in lifespan, add to AppState
- `__init__.py` (CatalystPipeline): add firehose branch to `run()` — when firehose=True, call sources with firehose=True
- `startup.py` (~20 lines): `create_quality_components(config, db_manager)` factory; called from server.py

*(Simplified from pre-review: no on-demand fetch method, no quality_engine.py modifications.)*

| Factor | Count | Points |
|--------|-------|--------|
| Files modified | 3 (server.py, __init__.py, startup.py) | 3 |
| Pre-flight context reads | 3 (intelligence/config.py, position_sizer.py, quality_engine.py) | 3 |
| New tests | ~12 | 6 |
| **Total** | | **12 (Medium)** ✓ |

---

## Session 8: API Routes for Quality Data

**Objective:** Create quality API routes with 3 endpoints. Register in router.

**Creates:** `argus/api/routes/quality.py`
**Modifies:** `argus/api/routes/__init__.py`
**Integrates:** Sessions 4+5b+7 (quality engine + DB + server)
**Parallelizable:** false

**Endpoints:**
- `GET /api/v1/quality/{symbol}` — Most recent quality score. Returns 404 if no history.
- `GET /api/v1/quality/history` — Paginated, filterable (symbol, strategy, grade, dates).
- `GET /api/v1/quality/distribution` — Today's grade distribution (all grades, zero counts included).

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Pre-flight context reads | 3 | 3 |
| New tests | ~12 | 6 |
| **Total** | | **12 (Medium)** ✓ |

---

## Session 9: Frontend — Quality Components + Hooks + Trades Page

**Objective:** Create QualityBadge (reusable, grade-colored, grade-to-size tooltip), TanStack Query hooks, quality grade column on Trades page.

**Creates:** `QualityBadge.tsx`, `useQuality.ts`
**Modifies:** Trades page components
**Integrates:** Session 8 (API routes)
**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 1 | 1 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~12 Vitest | 6 |
| **Total** | | **13 (Medium)** ✓ |

---

## Session 10: Frontend — Orchestrator + Dashboard Quality Panels

**Objective:** Orchestrator live quality scores. Dashboard quality distribution mini-card, Signal Quality Distribution panel, filtered signals counter.

**Creates:** `QualityDistributionCard.tsx`, `SignalQualityPanel.tsx`
**Modifies:** Orchestrator page, Dashboard page
**Integrates:** Session 9 (QualityBadge, hooks)
**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~12 Vitest | 6 |
| **Total** | | **14 (High — at threshold)** |

---

## Session 11: Frontend — Performance + Debrief Quality Charts

**Objective:** Performance "by quality grade" bar chart. Debrief quality vs. outcome scatter plot.

**Creates:** `QualityGradeChart.tsx`, `QualityOutcomeScatter.tsx`
**Modifies:** Performance page, Debrief page
**Integrates:** Session 9 (hooks)
**Parallelizable:** false

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | 4 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 2 | 2 |
| New tests | ~12 Vitest | 6 |
| **Total** | | **14 (High — at threshold)** |

---

## Session 11f: Visual-Review Fixes (Contingency — 0.5 Session)

If no visual issues found, unused.

---

## Revised Summary Table

| Session | Scope | Creates | Modifies | Score | Risk |
|---------|-------|---------|----------|-------|------|
| 1 | SignalEvent + ORB Pattern Strength | — | 4 files | 15 | High (exception) |
| 2 | VWAP + AfMo Pattern Strength | — | 2 files | 11 | Medium ✓ |
| 3 | DEC-327 Firehose Sources | — | 2 files | 13 | Medium ✓ |
| 4 | Quality Engine Core | 1 file | — | 15 | High (exception) |
| 5a | Sizer + Config Models | 1 file | 1 file | 11 | Medium ✓ |
| 5b | Config Wiring + YAML + DB | 1 file | 4 files | 12 | Medium ✓ |
| 6a | Pipeline Wiring + Unit Tests | — | 3 files | 15 | High (exception — split from 16.5) |
| 6b | Integration Tests + Error Paths | — | tests only | 9 | Low ✓ |
| 7 | Server Init + Firehose Pipeline | — | 3 files | 12 | Medium ✓ (was 14.5) |
| 8 | API Routes | 1 file | 1 file | 12 | Medium ✓ |
| 9 | FE: Components + Hooks + Trades | 2 files | 1 file | 13 | Medium ✓ |
| 10 | FE: Orchestrator + Dashboard | 2 files | 2 files | 14 | At threshold |
| 11 | FE: Performance + Debrief | 2 files | 2 files | 14 | At threshold |
| 11f | Visual-Review Fixes | — | TBD | — | Contingency |

**Changes from pre-review:**
- Session 6 split into 6a (15) + 6b (9) — down from 16.5
- Session 7 simplified from 14.5 to 12 (on-demand live fetch removed)
- Session 6a adds risk_manager.py one-line guard
- Total: 13 sessions + contingency (was 12 + contingency)

**Estimated total new tests:** ~160–185 (115–130 pytest + 45–55 Vitest)
**Post-sprint totals:** ~2,660–2,720 pytest + ~490–500 Vitest
