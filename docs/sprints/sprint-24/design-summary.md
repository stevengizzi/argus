# Sprint 24 Design Summary

> **Compaction insurance.** If context is lost, this document alone is sufficient to regenerate all sprint artifacts.
> Updated post-adversarial-review.

**Sprint Goal:** Build the SetupQualityEngine (5-dimension 0–100 composite scoring) and DynamicPositionSizer (quality grade → risk tier → share count) that transform ARGUS from binary pass/fail signal filtering to intelligence-driven trade grading and sizing. Includes DEC-327 firehose pipeline refactoring, quality history recording for Sprint 28's Learning Loop, and quality visibility across all 5 Command Center pages.

**Execution Mode:** Human-in-the-loop

**Session Breakdown:**

- Session 1: SignalEvent enrichment (pattern_strength, signal_context, quality_score, quality_grade fields + QualitySignalEvent) + ORB family pattern strength scoring. share_count=0 in ORB signal builders.
  - Creates: —
  - Modifies: `argus/core/events.py`, `argus/strategies/orb_base.py`, `argus/strategies/orb_breakout.py`, `argus/strategies/orb_scalp.py`
  - Integrates: N/A
  - Score: 15 (High — exception: breadth not depth, ORB shares base class)

- Session 2: VWAP Reclaim + Afternoon Momentum pattern strength scoring. share_count=0.
  - Creates: —
  - Modifies: `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`
  - Integrates: Session 1
  - Score: 11 (Medium)

- Session 3: DEC-327 firehose source refactoring. Finnhub `/news?category=general` (1 call) + SEC EDGAR EFTS search (1 call). Symbol association via `related` field / CIK→ticker map. `fetch_catalysts()` gains `firehose: bool` parameter. Per-symbol methods retained.
  - Creates: —
  - Modifies: `argus/intelligence/sources/finnhub.py`, `argus/intelligence/sources/sec_edgar.py`
  - Integrates: N/A (independent)
  - Score: 13 (Medium)

- Session 4: SetupQualityEngine core. 5 dimension scorers per rubrics, grade mapping, risk tier. Pure stateless scoring, no IO. <150 lines.
  - Creates: `argus/intelligence/quality_engine.py`
  - Modifies: —
  - Integrates: N/A
  - Score: 15 (High — exception: single file, test count inflates)

- Session 5a: DynamicPositionSizer + Pydantic config models (QualityEngineConfig with `enabled` field, QualityWeightsConfig with sum validator, QualityThresholdsConfig, QualityRiskTiersConfig).
  - Creates: `argus/intelligence/position_sizer.py`
  - Modifies: `argus/intelligence/config.py`
  - Integrates: Session 4
  - Score: 11 (Medium)

- Session 5b: Config wiring + YAML + DB schema. SystemConfig gets quality_engine field. `config/quality_engine.yaml` created. quality_history table in schema.sql. Both system YAML files updated.
  - Creates: `config/quality_engine.yaml`
  - Modifies: `argus/core/config.py`, `argus/db/schema.sql`, `config/system.yaml`, `config/system_live.yaml`
  - Integrates: Session 5a
  - Score: 12 (Medium)

- Session 6a: Pipeline wiring + unit tests. Wire Quality Engine + Sizer into `_on_candle_for_strategies()`. Backtest bypass (BrokerSource.SIMULATED → legacy sizing). Config bypass (enabled=false → legacy). Risk Manager check 0 guard (reject share_count ≤ 0). `record_quality_history()` on engine.
  - Creates: —
  - Modifies: `argus/main.py`, `argus/intelligence/quality_engine.py`, `argus/core/risk_manager.py` (one-line guard only)
  - Integrates: Sessions 1+2+4+5a+5b (core integration)
  - Score: 15 (High — exception: irreducible integration, split from original 16.5)

- Session 6b: Integration tests + error paths. Full pipeline tests, error paths (engine exception, storage unavailable, sizer returns 0), bypass verification, canary test setup. Test-only session.
  - Creates: —
  - Modifies: test files only
  - Integrates: Session 6a
  - Score: 9 (Low)

- Session 7: Server initialization + firehose pipeline integration. Quality Engine + Sizer in server.py lifespan. Firehose mode in CatalystPipeline.run(). Quality component factory in startup.py.
  - Creates: —
  - Modifies: `argus/api/server.py`, `argus/intelligence/__init__.py`, `argus/intelligence/startup.py`
  - Integrates: Sessions 3+5b+6a
  - Score: 12 (Medium)

- Session 8: API routes. GET /quality/{symbol}, /quality/history, /quality/distribution. JWT auth. Router registration.
  - Creates: `argus/api/routes/quality.py`
  - Modifies: `argus/api/routes/__init__.py`
  - Integrates: Sessions 4+5b+7
  - Score: 12 (Medium)

- Session 9: Frontend — QualityBadge component (reusable, grade-colored, tooltip), TanStack Query hooks (useQuality.ts), quality grade column on Trades page.
  - Creates: `QualityBadge.tsx`, `useQuality.ts`
  - Modifies: Trades page components
  - Integrates: Session 8
  - Score: 13 (Medium)

- Session 10: Frontend — Orchestrator live quality scores + Dashboard quality distribution mini-card + Signal Quality Distribution panel + filtered signals counter.
  - Creates: `QualityDistributionCard.tsx`, `SignalQualityPanel.tsx`
  - Modifies: Orchestrator page, Dashboard page
  - Integrates: Session 9
  - Score: 14 (At threshold)

- Session 11: Frontend — Performance "by quality grade" chart + Debrief quality vs. outcome scatter plot.
  - Creates: `QualityGradeChart.tsx`, `QualityOutcomeScatter.tsx`
  - Modifies: Performance page, Debrief page
  - Integrates: Session 9
  - Score: 14 (At threshold)

- Session 11f: Visual-review fixes — contingency, 0.5 session.

**Key Decisions:**

- **SignalEvent gets `pattern_strength: float = 50.0` + `signal_context: dict` + `quality_score: float = 0.0` + `quality_grade: str = ""`** — typed scalar for Quality Engine, rich metadata for Learning Loop, downstream fields populated by `dataclasses.replace()`. Defaults preserve backward compatibility.
- **QualitySignalEvent is informational (UI only)** — separate event type on Event Bus. Does NOT participate in execution pipeline. Risk Manager receives standard enriched SignalEvent.
- **Strategies set share_count=0** (option B) — Dynamic Sizer calculates from scratch. Fail-closed: if sizer bypassed, share_count=0 → rejected by RM check 0.
- **Config-gated: `quality_engine.enabled: true`** (default true) — provides rollback during paper trading and A/B comparison at Sprint 28. When disabled, legacy sizing path used (same as backtest bypass).
- **Backtest bypass** — `BrokerSource.SIMULATED` → quality pipeline skipped entirely, legacy strategy-calculated sizing. No backtest/* files modified.
- **Risk Manager check 0** — defensive guard rejecting share_count ≤ 0. One-line addition to evaluate_signal(). Defense-in-depth.
- **Historical Match stubbed at 50/100** — preserves 5-dimension framework. Sprint 28 Learning Loop replaces with real data. Effective score range ~7.5–92.5. Grade thresholds PROVISIONAL.
- **Dimension scoring rubrics defined:** PS = passthrough, CQ = max quality_score from 24h catalysts (empty → 50), VP = RVOL breakpoint interpolation (None → 50), HM = constant 50, RA = regime in allowed_regimes → 80, not → 20, empty → 70.
- **Risk tier: flat midpoint per grade** — score 80 and 89 both get (1.5+2.0)/2 = 1.75%. No intra-grade interpolation.
- **DEC-327 firehose refactor** — Finnhub general news (1 call/cycle) + SEC EDGAR EFTS search (1 call/cycle) replace N+1 per-symbol pattern. FMP stays disabled (Starter plan).
- **No on-demand live API fetch in scoring path** — catalyst data from local catalyst.db only (< 100ms query). Firehose polling loop keeps DB current.
- **quality_history table in argus.db** — full component breakdown per scored signal. Outcome columns NULL until Sprint 28 wires PositionClosedEvent.
- **Weight sum validation** — Pydantic model_validator, tolerance ±0.001, startup fails on violation.

**Scope Boundaries:**

- IN: SetupQualityEngine (5 dimensions with rubrics), DynamicPositionSizer (grade→midpoint risk→shares), pattern_strength on all 4 strategies, DEC-327 firehose refactoring, backtest bypass, config gating, RM check 0 guard, quality_history DB table, QualitySignalEvent, 3 API endpoints, UI on Trades/Orchestrator/Dashboard/Performance/Debrief, filtered signals counter
- OUT: Learning Loop (Sprint 28), ML/Claude API for scoring, strategy entry/exit changes, RM gate changes (beyond check 0), PreMarketEngine, new strategies, CatalystClassifier changes, WebSocket quality streaming, order flow (DEC-238), on-demand live API fetch, outcome recording automation, quality_history retention, Orchestrator changes, CatalystStorage schema changes, intra-grade risk interpolation

**Regression Invariants:**

1. Strategies still decide when to signal — Quality Engine never prevents signal generation
2. Risk Manager gates remain non-bypassable (check 0 added; checks 1–7 unchanged)
3. Circuit breakers remain non-overridable
4. Event Bus FIFO ordering maintained
5. All existing 2,532 pytest + 446 Vitest pass
6. Backtest bypass: Replay Harness identical results pre/post sprint
7. Config bypass: enabled=false → identical to pre-Sprint-24

**File Scope:**

- Create: `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/api/routes/quality.py`, `config/quality_engine.yaml`, 6 frontend components
- Modify: `events.py`, `orb_base.py`, `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `finnhub.py`, `sec_edgar.py`, `intelligence/config.py`, `core/config.py`, `db/schema.sql`, `main.py`, `risk_manager.py` (one-line), `server.py`, `intelligence/__init__.py`, `intelligence/startup.py`, `api/routes/__init__.py`, `system.yaml`, `system_live.yaml`, frontend pages
- Do not modify: `orchestrator.py`, `order_manager.py`, `trade_logger.py`, `ai/*`, `classifier.py`, `storage.py`, `models.py`, `fmp_news.py`, `backtest/*`, `briefing.py`

**Config Changes:**

New section `quality_engine` in system.yaml / system_live.yaml:
- `enabled: true` — config gate (default true)
- `weights.*` — 5 dimension weights (sum validated to 1.0)
- `thresholds.*` — grade boundaries (strictly descending)
- `risk_tiers.*` — risk % ranges per grade ([min, max], midpoint used)
- `min_grade_to_trade: "C+"` — minimum grade to execute

All YAML field names verified against Pydantic model names. Regression item: no silently ignored keys.

**Test Strategy:**

- Backend: ~115–130 new pytest. Pattern strength (~30), quality engine (~22), sizer (~12), config (~8), DB (~4), signal flow unit (~10), integration (~12), API (~10), firehose (~18).
- Frontend: ~45–55 new Vitest. QualityBadge + hooks (~10), Trades (~4), Orchestrator + Dashboard (~10), Performance + Debrief (~10).
- Total: ~160–185 new tests. Post-sprint: ~2,660–2,720 pytest + ~490–500 Vitest.
- Canary test: Replay Harness before/after (BrokerSource.SIMULATED — identical results).

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: None
- Runner config: Not generated

**Dependencies:**

- Sprint 23.9 complete (2,532 pytest + 446 Vitest)
- CatalystStorage, Universe Manager, RegimeClassifier, IndicatorEngine, Event Bus, DBManager all operational

**Escalation Criteria:**

- Halt: QE exception blocks all trading, canary test failure, test regression, backtest bypass failure
- Tier 3: firehose returns zero items >3 cycles, config validation failures, sizer positions violate RM limits >30%, pattern strength clusters <10-point spread

**Doc Updates Needed:**

- architecture.md, decision-log.md, dec-index.md, risk-register.md, project-knowledge.md, sprint-history.md, roadmap.md, CLAUDE.md, sprint-campaign.md, project-bible.md, strategy spec sheets, config files

**Artifacts to Generate:**

1. Sprint Spec ✅
2. Specification by Contradiction ✅
3. Session Breakdown ✅
4. Escalation Criteria ✅
5. Regression Checklist ✅
6. Doc Update Checklist ✅
7. Adversarial Review Input Package ✅
8. Revision Rationale ✅
9. Review Context File ✅
10. Implementation Prompts ×14 (Sessions 1, 2, 3, 4, 5a, 5b, 6a, 6b, 7, 8, 9, 10, 11, 11f) ✅
11. Review Prompts ×13 (Sessions 1–11) ✅
12. Work Journal Handoff Prompt ✅
