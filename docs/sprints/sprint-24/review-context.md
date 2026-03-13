# Sprint 24 — Review Context File

> This file is read by every Tier 2 review session. It contains the full Sprint Spec,
> Specification by Contradiction, Sprint-Level Regression Checklist, and Sprint-Level
> Escalation Criteria. Do not duplicate this content in individual review prompts.
>
> **Save this file to:** `docs/sprints/sprint-24/review-context.md`

---

## Review Instructions

Follow the review skill in `.claude/skills/review.md`. This is a READ-ONLY session.
Do NOT modify any source code files. The only permitted file write is the review report itself.

Your review report MUST include a structured JSON verdict at the end, fenced with
` ```json:structured-verdict `. See the review skill for the full schema.

---

## Sprint Spec (Embedded)

### Goal
Build the SetupQualityEngine (5-dimension 0–100 composite scoring) and DynamicPositionSizer (quality grade → risk tier → share count). Includes DEC-327 firehose pipeline refactoring, quality history recording for Sprint 28's Learning Loop, and quality UI across 5 Command Center pages.

### Key Design Decisions
- **Strategies set share_count=0** — Dynamic Sizer calculates from scratch. If bypassed, share_count=0 → rejected by Risk Manager check 0 (fail-closed).
- **Historical Match stubbed at 50** — preserves 5-dimension framework. Effective score range ~7.5–92.5. Thresholds PROVISIONAL.
- **Config-gated:** `quality_engine.enabled: true` (default). When disabled, legacy sizing path used.
- **Backtest bypass:** `BrokerSource.SIMULATED` → legacy sizing, quality pipeline skipped entirely.
- **C/C- signals filtered** — never reach Risk Manager. `min_grade_to_trade` configurable (default "C+").
- **Fail-closed on quality engine error** — exception → signal does not execute.
- **Risk tier: flat midpoint per grade** — score 80 and 89 both get (1.5+2.0)/2 = 1.75%.
- **QualitySignalEvent** is informational (UI only), not in execution pipeline.

### Dimension Scoring Rubrics
- **Pattern Strength (30%):** Passthrough from signal.pattern_strength (0–100).
- **Catalyst Quality (25%):** Max quality_score from 24h catalysts. Empty → 50.
- **Volume Profile (20%):** RVOL breakpoints: ≤0.5→10, 1.0→40, 2.0→70, ≥3.0→95. None→50.
- **Historical Match (15%):** Constant 50 (V1 stub).
- **Regime Alignment (10%):** In allowed_regimes→80, not in list→20, empty list→70.

### Quality Grades and Risk Tiers
| Grade | Score | Risk % (midpoint) |
|-------|-------|-------------------|
| A+ | 90–100 | 2.5% |
| A | 80–89 | 1.75% |
| A- | 70–79 | 1.25% |
| B+ | 60–69 | 0.875% |
| B | 50–59 | 0.625% |
| B- | 40–49 | 0.375% |
| C+ | 30–39 | 0.25% |
| C/C- | 0–29 | SKIP |

### Signal Flow (After Sprint 24)
```
strategy.on_candle() → SignalEvent (share_count=0, pattern_strength populated)
    ↓
[If BrokerSource.SIMULATED or quality_engine.enabled==false]:
    Legacy sizing → Risk Manager → Order Manager (existing flow)
    ↓
[If quality pipeline active]:
    Fetch catalysts from catalyst.db, RVOL, regime
    ↓
    score_setup() → SetupQuality
    ↓
    Grade below min_grade_to_trade? → log + record quality_history → skip
    ↓
    calculate_shares() → shares
    ↓
    Shares ≤ 0? → log + record → skip
    ↓
    dataclasses.replace(signal, share_count=shares, quality_score=..., quality_grade=...)
    ↓
    Record quality_history + publish QualitySignalEvent (informational)
    ↓
    Risk Manager check 0: share_count ≤ 0? → reject (defensive guard)
    Risk Manager checks 1–7: existing gates (unchanged)
    ↓
    Order Manager → Broker
```

### Config Changes
New section `quality_engine` in system.yaml / system_live.yaml. Key fields:
- `enabled: true` — config gate
- `weights.*` — 5 dimension weights (must sum to 1.0)
- `thresholds.*` — grade boundaries (strictly descending)
- `risk_tiers.*` — risk % ranges per grade
- `min_grade_to_trade: "C+"` — minimum grade to execute

### Files Created
`argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/api/routes/quality.py`, `config/quality_engine.yaml`, 6 frontend components

### Files Modified
`events.py`, `orb_base.py`, `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `finnhub.py`, `sec_edgar.py`, `intelligence/config.py`, `core/config.py`, `db/schema.sql`, `main.py`, `server.py`, `intelligence/__init__.py`, `intelligence/startup.py`, `api/routes/__init__.py`, `risk_manager.py` (one-line guard only), frontend pages (Trades, Orchestrator, Dashboard, Performance, Debrief)

### Do NOT Modify
`orchestrator.py`, `order_manager.py`, `trade_logger.py`, `ai/*`, `classifier.py`, `storage.py`, `models.py`, `fmp_news.py`, `backtest/*`, `briefing.py`

---

## Specification by Contradiction (Embedded)

**Does NOT:** implement Learning Loop, use ML/Claude API for scoring, change strategy entry/exit logic, change RM gates (except check 0 guard), add PreMarketEngine, add new strategies, change CatalystClassifier, add WebSocket quality streaming, implement order flow dimension, add on-demand live API fetch in scoring path, add outcome recording automation.

**Permitted RM modification:** One-line check 0 in `evaluate_signal()`: reject if `share_count <= 0`.

---

## Sprint-Level Regression Checklist (Embedded)

### Core Trading Pipeline
- [ ] All 4 strategies produce SignalEvents when entry criteria met
- [ ] No strategy entry/exit logic altered
- [ ] Risk Manager check 0 rejects share_count ≤ 0
- [ ] Risk Manager checks 1–7 unchanged
- [ ] C/C- signals never reach Risk Manager
- [ ] Circuit breakers non-overridable
- [ ] Event Bus FIFO ordering maintained

### Backtest Bypass
- [ ] Replay Harness with BrokerSource.SIMULATED: identical results to pre-sprint
- [ ] Legacy sizing uses original formula
- [ ] Quality scoring/sizing/recording all skipped in backtest mode
- [ ] No backtest/* files modified

### Config Gating
- [ ] quality_engine.enabled: true in both config files
- [ ] When disabled: identical to pre-Sprint-24 behavior
- [ ] When disabled: no quality_history rows, no QualitySignalEvents

### Signal Integrity
- [ ] SignalEvent backward compatible (existing constructors work)
- [ ] dataclasses.replace() used for enrichment (original never mutated)
- [ ] Enriched signal preserves all original fields

### Strategy Behavior
- [ ] ORB Breakout: same signals under same conditions
- [ ] ORB Scalp: same signals under same conditions
- [ ] VWAP Reclaim: same signals under same conditions
- [ ] Afternoon Momentum: same signals under same conditions

### Intelligence Pipeline
- [ ] CatalystPipeline per-symbol mode (firehose=False) still works
- [ ] CatalystClassifier unchanged
- [ ] CatalystStorage unchanged
- [ ] Catalyst config-gating (DEC-300) still works
- [ ] FMP circuit breaker (DEC-323) still active
- [ ] Daily cost ceiling (DEC-303) still enforced
- [ ] Firehose ≤ 3 API calls per source per cycle

### Configuration
- [ ] quality_engine config fields match Pydantic model (no silently ignored keys)
- [ ] Weight sum validated (startup fails if ≠ 1.0)
- [ ] Missing section uses valid defaults
- [ ] Existing config sections unmodified

### Database
- [ ] quality_history table in argus.db (not catalyst.db)
- [ ] Existing tables unmodified
- [ ] catalyst_events table unmodified

### API
- [ ] Existing endpoints unchanged
- [ ] New quality endpoints require JWT auth

### Frontend
- [ ] Existing panels/columns unchanged (only new additions)
- [ ] Pipeline health gating (DEC-329) still active
- [ ] Existing TanStack Query hooks still function

### Tests
- [ ] All 2,532 existing pytest pass
- [ ] All 446 existing Vitest pass
- [ ] No test file deleted or renamed

---

## Sprint-Level Escalation Criteria (Embedded)

### Immediate Halt
1. Quality Engine exception blocks ALL trading (when enabled)
2. Canary test failure (signal count mismatch)
3. Existing test suite regression
3a. Backtest bypass failure (Replay Harness produces different results)
3b. Legacy sizing path produces different results when disabled

### Escalate to Tier 3
4. Firehose returns zero items >3 consecutive cycles
5. Config weight sum validation fails on existing YAML
6. Sizer positions consistently violate RM concentration limits (>30%)
7. Pattern strength scores cluster <10-point spread

### Informational
8. Catalyst data unavailable >50% of scored signals
9. All signals score same grade (log, don't escalate unless 3+ sessions)
