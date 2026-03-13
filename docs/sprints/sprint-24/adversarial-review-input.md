# Sprint 24 — Adversarial Review Input Package

> Paste this entire document into a fresh Claude.ai conversation to run the adversarial review.
> The reviewer should stress-test the spec and session breakdown, then produce a verdict.

---

## Instructions

You are conducting an Adversarial Review of Sprint 24 for ARGUS, a fully automated multi-strategy day trading system for US equities. Your job is to find flaws, gaps, ambiguities, and risks in the sprint design before implementation begins. Be rigorous. If the design is sound, say so — but challenge every assumption.

**Focus areas (from sprint campaign):**
1. Quality scoring edge cases — what happens at score boundaries (39 vs. 40, 84 vs. 85)?
2. Dynamic sizer failure modes — what if quality engine returns invalid score? What if Risk Manager and sizer disagree?
3. Signal pipeline timing — does quality scoring add latency to execution? Is that acceptable for day trading?
4. Integration stress — does the quality filter change existing strategy behavior? Regression risk to four active strategies?
5. Firehose data quality — symbol association accuracy for Finnhub general news and SEC EDGAR EFTS search

**Additional areas to probe:**
6. The share_count=0 decision (option B) — is there any code path where share_count=0 could leak to Order Manager?
7. On-demand catalyst lookup at signal time — is 5 seconds too long? Could it cause missed fills?
8. Historical Match stubbed at 50 — does a constant 15% dimension distort grade distributions?
9. Config weight sum validation — what happens if config file is hand-edited to wrong sum?

---

## Sprint Goal

Build the SetupQualityEngine (5-dimension 0–100 composite scoring) and DynamicPositionSizer (quality grade → risk tier → share count). Includes DEC-327 firehose pipeline refactoring, on-demand catalyst lookup, quality history recording for Sprint 28's Learning Loop, and quality UI across 5 Command Center pages.

---

## Sprint Spec (Summary)

### Deliverables
1. SignalEvent enrichment: `pattern_strength`, `signal_context`, `quality_score`, `quality_grade` fields
2. Pattern strength scoring for all 4 active strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum)
3. DEC-327 firehose source refactoring (Finnhub general news, SEC EDGAR EFTS search)
4. SetupQualityEngine: 5-dimension scoring (PS 30%, CQ 25%, VP 20%, HM 15%, RA 10%)
5. DynamicPositionSizer: grade → risk tier → share calculation from scratch
6. Config models + YAML + quality_history DB table
7. Signal flow wiring in main.py between signal generation and Risk Manager
8. On-demand catalyst lookup with 5s timeout
9. Server initialization + firehose pipeline integration
10. 3 API endpoints (quality/{symbol}, quality/history, quality/distribution)
11. Frontend: quality badges on Trades, live scores on Orchestrator, distribution panels on Dashboard, grade chart on Performance, scatter plot on Debrief

### Key Design Decisions
- **Strategies set share_count=0** — Dynamic Sizer calculates from scratch (option B). If sizer bypassed, share_count=0 → no trade (fail-closed).
- **Historical Match stubbed at 50** — preserves 5-dimension framework. 15% weight on constant 50 adds 7.5 points to every score. No effect on differentiation.
- **Quality Engine always-on** — no config gating. Enabled from the start.
- **C/C- signals filtered** — never reach Risk Manager. Configurable via `min_grade_to_trade`.
- **Fail-closed on quality engine error** — exception in scoring → signal does not execute.

### Quality Grade Thresholds and Risk Tiers

| Grade | Score Range | Risk % Range |
|-------|-----------|--------------|
| A+ | 90–100 | 2.0–3.0% |
| A | 80–89 | 1.5–2.0% |
| A- | 70–79 | 1.0–1.5% |
| B+ | 60–69 | 0.75–1.0% |
| B | 50–59 | 0.5–0.75% |
| B- | 40–49 | 0.25–0.5% |
| C+ | 30–39 | 0.25% |
| C/C- | 0–29 | SKIP |

### Signal Flow (After Sprint 24)
```
strategy.on_candle() → SignalEvent (share_count=0, pattern_strength populated)
    ↓
Quality Engine: fetch catalysts, RVOL, regime → score_setup() → SetupQuality
    ↓
Filter: grade below min_grade_to_trade? → log + record quality_history → skip
    ↓
Dynamic Sizer: calculate_shares(quality, entry, stop, capital, buying_power) → shares
    ↓
Shares ≤ 0? → log + record → skip
    ↓
Enrich: dataclasses.replace(signal, share_count=shares, quality_score=..., quality_grade=...)
    ↓
Record quality_history + publish QualitySignalEvent
    ↓
Risk Manager: evaluate_signal(enriched_signal) → existing 7-check gate
    ↓
Order Manager → Broker
```

---

## Specification by Contradiction (Summary)

**Does NOT:** implement Learning Loop, use ML/Claude API for scoring, change strategy entry/exit logic, change Risk Manager gates, add PreMarketEngine, add new strategies, change CatalystClassifier, add WebSocket quality streaming, implement order flow dimension, add config gating

**Do NOT modify:** risk_manager.py, orchestrator.py, order_manager.py, trade_logger.py, ai/*, classifier.py, storage.py, models.py, fmp_news.py, backtest/*

---

## Session Breakdown (12 Sessions)

| # | Scope | Score | Key Risk |
|---|-------|-------|----------|
| 1 | SignalEvent + ORB Pattern Strength | 15 | 4 modified files |
| 2 | VWAP + AfMo Pattern Strength | 11 | — |
| 3 | DEC-327 Firehose Sources | 13 | API endpoint behavior |
| 4 | Quality Engine Core | 15 | Test count |
| 5a | Sizer + Config Models | 11 | — |
| 5b | Config Wiring + YAML + DB | 12 | — |
| 6 | Signal Flow Wiring | 16.5 | Core integration |
| 7 | Server Init + Pipeline + On-Demand | 14.5 | 4 modified files |
| 8 | API Routes | 12 | — |
| 9 | FE: Components + Hooks + Trades | 13 | — |
| 10 | FE: Orchestrator + Dashboard | 14 | — |
| 11 | FE: Performance + Debrief | 14 | — |
| 11f | Visual-Review Fixes | — | Contingency |

---

## Relevant Architecture Context

### Current Signal Flow (Pre-Sprint 24)
```python
# In main.py _on_candle_for_strategies():
signal = await strategy.on_candle(event)  # share_count calculated by strategy
if signal is not None:
    result = await self._risk_manager.evaluate_signal(signal)
    await self._event_bus.publish(result)
```

### Strategy Position Sizing (Current)
Each strategy's `calculate_position_size()`:
```python
risk_per_share = entry_price - stop_price
risk_dollars = allocated_capital * max_loss_per_trade_pct  # Fixed 1%
shares = int(risk_dollars / risk_per_share)
```

### Risk Manager evaluate_signal() Checks (Unchanged)
1. Circuit breaker active → Reject
2. Daily loss limit → Reject
3. Weekly loss limit → Reject
4. Max concurrent positions → Reject
5. Single-stock concentration (DEC-249) → Modify or reject
6. Cash reserve → Modify or reject
7. Buying power → Modify or reject
8. PDT check → Reject

At each modify step: if reduced shares < min_position_risk_dollars ($100) floor → Reject (DEC-251)

### CatalystStorage Query Interface
```python
async def get_catalysts_by_symbol(self, symbol: str, limit: int = 50, since: datetime | None = None) -> list[ClassifiedCatalyst]
```
ClassifiedCatalyst has `quality_score: float` (0–100).

### Finnhub Current Approach (Per-Symbol)
```python
for symbol in symbols:
    news = await self._fetch_company_news(symbol, fetch_time)  # 1 call per symbol
    recommendations = await self._fetch_recommendations(symbol, fetch_time)  # 1 call per symbol
```

### SEC EDGAR Current Approach (Per-Symbol)
```python
for symbol in symbols:
    cik = self._cik_map.get(symbol.upper())
    filings = await self._fetch_filings(cik, symbol.upper())  # 1 call per CIK
```

---

## Your Verdict

After reviewing, produce:

1. **CONFIRMED** or **REVISIONS NEEDED**
2. For each finding:
   - Severity: CRITICAL / HIGH / MEDIUM / LOW
   - Category: Design Flaw / Gap / Ambiguity / Risk
   - Description
   - Recommended fix (if REVISIONS NEEDED)
3. Summary assessment: is this sprint ready for implementation?
