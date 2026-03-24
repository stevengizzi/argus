# Sprint 27.6 Design Summary

**Sprint Goal:** Replace the single-dimension `MarketRegime` enum with a multi-dimensional `RegimeVector` that captures trend, volatility, breadth, correlation, sector rotation, and intraday character — all computed from existing data sources (Databento + FMP) at zero additional cost. Add operating conditions matching for future micro-strategy regime regions. Extend Observatory session vitals with regime dimensions.

**Session Breakdown:**
- Session 1: RegimeVector dataclass + RegimeClassifierV2 shell + config/regime.yaml + RegimeIntelligenceConfig Pydantic model
  - Creates: `config/regime.yaml`
  - Modifies: `argus/core/regime.py`, `argus/core/config.py`
  - Integrates: N/A (foundation)
- Session 2: BreadthCalculator — live breadth from Databento CandleEvent stream via Event Bus
  - Creates: `argus/core/breadth.py`
  - Modifies: None
  - Integrates: N/A (standalone, wired in S6)
- Session 3: MarketCorrelationTracker — rolling 20-day pairwise correlation, pre-market computation, file cache
  - Creates: `argus/core/market_correlation.py`
  - Modifies: None
  - Integrates: N/A (standalone, wired in S6)
- Session 4: SectorRotationAnalyzer — FMP `/stable/sector-performance`, circuit breaker on 403, sector classification
  - Creates: `argus/core/sector_rotation.py`
  - Modifies: None
  - Integrates: N/A (standalone, wired in S6)
- Session 5: IntradayCharacterDetector — SPY candle analysis at 9:35/10:00/10:30 AM ET, intraday character classification
  - Creates: `argus/core/intraday_character.py`
  - Modifies: None
  - Integrates: N/A (standalone, wired in S6)
- Session 6: Integration — compose RegimeClassifierV2 with all calculators + Orchestrator wiring + main.py startup + RegimeHistoryStore persistence
  - Creates: `argus/core/regime_history.py`
  - Modifies: `argus/core/regime.py` (V2 composition), `argus/core/orchestrator.py`, `argus/main.py`, `argus/core/events.py`
  - Integrates: S1 (RegimeVector + V2 shell), S2 (BreadthCalculator), S3 (MarketCorrelationTracker), S4 (SectorRotationAnalyzer), S5 (IntradayCharacterDetector)
- Session 7: BacktestEngine integration — `_compute_regime_tags()` extension with V2 (trend + vol only historically)
  - Creates: None
  - Modifies: `argus/backtest/engine.py`
  - Integrates: S1 (RegimeVector), S6 (V2 composition)
- Session 8: End-to-end integration tests + cleanup
  - Creates: None
  - Modifies: Test files only
  - Integrates: All prior sessions (end-to-end verification)
- Session 9: Operating conditions matching — `RegimeOperatingConditions` dataclass, range matching on RegimeVector, strategy YAML schema
  - Creates: None
  - Modifies: `argus/core/regime.py`, `argus/models/strategy.py`
  - Integrates: S1 (RegimeVector)
- Session 10: Observatory regime visualization — extend session vitals bar with RegimeVector dimensions
  - Creates: None
  - Modifies: 2–3 Observatory frontend files
  - Integrates: S6 (V2 via API/WS)
- Session 10f: Visual-review fixes — contingency, 0.5 session

**Key Decisions:**
- RegimeVector is a frozen dataclass, not a Pydantic model. It's a runtime value object, not a config type.
- Backward compatibility via `primary_regime: MarketRegime` field on RegimeVector. V2 delegates to V1 internally (no reimplementation). All existing `allowed_regimes` filtering unchanged.
- BreadthCalculator measures **intraday universe participation breadth** (1-min bars, 20-bar MA). Field renamed to `universe_breadth_score` to prevent confusion with traditional multi-day market breadth. Returns None during ramp-up (first ~10 minutes).
- `regime_confidence` = signal_clarity × data_completeness (two-factor decomposition).
- IntradayCharacterDetector uses concrete classification rules with configurable thresholds. Priority: Breakout > Reversal > Trending > Choppy.
- MarketCorrelationTracker computed during pre-market startup from FMP daily bars for top N symbols (ranked by avg daily volume from Universe Manager reference cache). File-based cache keyed by calendar date (ET).
- SectorRotationAnalyzer uses FMP `/stable/sector-performance` with circuit breaker on 403 (DEC-323 pattern). Graceful degradation to "mixed" if endpoint unavailable.
- Pre-market initialization runs correlation + sector concurrently via asyncio.gather() (~10-15s parallel).
- BacktestEngine uses V2 with all calculators = None (backtest mode). Trend + vol dimensions only.
- RegimeHistoryStore persists RegimeVector snapshots to regime_history.db (DEC-345 pattern). Sprint 28 (Learning Loop) arrives with regime history from day one.
- `MultiObjectiveResult.regime_results` keys unchanged (`MarketRegime.value` strings). RegimeVector is additional context.
- Config-gated via `regime_intelligence.enabled` with per-dimension enable/disable.
- Operating conditions matching is schema + logic only. No strategy uses it yet (Sprint 34+ consumers).

**Scope Boundaries:**
- IN: RegimeVector dataclass (6 dimensions), 4 new calculators, RegimeClassifierV2, config, Orchestrator integration, BacktestEngine integration, operating conditions matching, Observatory regime visualization
- OUT: ML-based regime classification, real-time correlation, VIX futures term structure, automatic strategy deactivation based on RegimeVector dimensions (Orchestrator still uses primary_regime), breadth/correlation/sector/intraday in historical backtest regime tagging, changes to `MultiObjectiveResult.regime_results` key structure

**Regression Invariants:**
- `RegimeClassifier.classify()` returns identical `MarketRegime` for identical inputs (V1 behavior preserved in V2)
- Orchestrator `allowed_regimes` filtering uses `primary_regime` (unchanged)
- `RegimeChangeEvent` still contains `old_regime`/`new_regime` as `MarketRegime.value` strings
- BacktestEngine `_compute_regime_tags()` returns identical results for existing test cases
- `MultiObjectiveResult.regime_results` key structure unchanged
- `regime_intelligence.enabled: false` → zero new code paths execute
- All existing 3,177 pytest + 620 Vitest tests pass
- No performance degradation in candle processing path
- Pre-market startup time increase bounded (< 30 seconds for correlation computation)

**File Scope:**
- Create: `config/regime.yaml`, `argus/core/breadth.py`, `argus/core/market_correlation.py`, `argus/core/sector_rotation.py`, `argus/core/intraday_character.py`, `argus/core/regime_history.py`
- Modify: `argus/core/regime.py`, `argus/core/config.py`, `argus/core/orchestrator.py`, `argus/core/events.py`, `argus/main.py`, `argus/backtest/engine.py`, `argus/models/strategy.py`, Observatory frontend files (2–3)
- Do not modify: `argus/analytics/evaluation.py`, `argus/analytics/comparison.py`, `argus/analytics/ensemble_evaluation.py`, `argus/data/databento_data_service.py` (BreadthCalculator subscribes via Event Bus, not by modifying the data service), `argus/strategies/*.py` (no strategy wiring this sprint), `argus/intelligence/*.py`, `argus/execution/*.py`

**Config Changes:**
- New file: `config/regime.yaml`
- New Pydantic model: `RegimeIntelligenceConfig` in `argus/core/config.py`
- Sub-models: `BreadthConfig`, `CorrelationConfig`, `SectorRotationConfig`, `IntradayConfig`
- Wired into `SystemConfig` as `regime_intelligence: RegimeIntelligenceConfig`
- YAML → Pydantic field mapping:
  - `regime_intelligence.enabled` → `RegimeIntelligenceConfig.enabled: bool = True`
  - `regime_intelligence.breadth.enabled` → `BreadthConfig.enabled: bool = True`
  - `regime_intelligence.breadth.ma_period` → `BreadthConfig.ma_period: int = 20`
  - `regime_intelligence.breadth.thrust_threshold` → `BreadthConfig.thrust_threshold: float = 0.80`
  - `regime_intelligence.breadth.min_symbols` → `BreadthConfig.min_symbols: int = 50`
  - `regime_intelligence.correlation.enabled` → `CorrelationConfig.enabled: bool = True`
  - `regime_intelligence.correlation.lookback_days` → `CorrelationConfig.lookback_days: int = 20`
  - `regime_intelligence.correlation.top_n_symbols` → `CorrelationConfig.top_n_symbols: int = 50`
  - `regime_intelligence.correlation.dispersed_threshold` → `CorrelationConfig.dispersed_threshold: float = 0.30`
  - `regime_intelligence.correlation.concentrated_threshold` → `CorrelationConfig.concentrated_threshold: float = 0.60`
  - `regime_intelligence.sector_rotation.enabled` → `SectorRotationConfig.enabled: bool = True`
  - `regime_intelligence.intraday.enabled` → `IntradayConfig.enabled: bool = True`
  - `regime_intelligence.intraday.first_bar_minutes` → `IntradayConfig.first_bar_minutes: int = 5`
  - `regime_intelligence.intraday.classification_times` → `IntradayConfig.classification_times: list[str] = ["09:35", "10:00", "10:30"]`
- Regression checklist item: "New config fields in regime.yaml verified against RegimeIntelligenceConfig Pydantic model (no silently ignored keys)"

**Test Strategy:**
- ~90 new pytest tests + ~6 new Vitest tests
- S1: ~12 (RegimeVector construction/serialization, V2 backward compat, config validation)
- S2: ~14 (BreadthCalculator accumulation, threshold crossings, edge cases)
- S3: ~10 (MarketCorrelationTracker matrix computation, cache, edge cases)
- S4: ~10 (SectorRotationAnalyzer classification, 403 degradation, leading/lagging)
- S5: ~12 (IntradayCharacterDetector all 4 character types, time gating, pre-market None)
- S6: ~10 (V2 full composition, Orchestrator integration, config-gate bypass)
- S7: ~8 (BacktestEngine regime tags with V2, historical consistency)
- S8: ~10 (end-to-end integration, stress tests, config permutations)
- S9: ~8 (operating conditions matching, range validation, edge cases)
- S10: ~6 Vitest (Observatory regime display, empty/None handling)

**Runner Compatibility:**
- Mode: Human-in-the-loop (recommended), runner config generated as backup
- Parallelizable sessions: S3 + S4 + S5 (after S2 completes; no shared file modifications)
- Estimated token budget: ~10 sessions × ~50K avg = ~500K tokens
- Runner-specific escalation notes: FMP sector performance 403 on Starter plan → does NOT halt, session continues with graceful degradation

**Dependencies:**
- Sprint 27.5 (Evaluation Framework) — complete ✅
- Databento feed (existing, no changes)
- FMP Starter plan (existing, sector performance endpoint — may or may not work)
- No external dependencies beyond existing subscriptions

**Escalation Criteria:**
- RegimeVector breaks `MultiObjectiveResult` serialization/deserialization
- BreadthCalculator causes measurable latency increase (> 1ms per candle) in data processing path
- FMP sector performance requires Premium plan AND sector rotation proves critical for regime quality
- Config-gate bypass doesn't fully isolate new code paths (any V2 code executes when disabled)
- BacktestEngine regime tags change for existing test cases (backward compatibility break)

**Doc Updates Needed:**
- `docs/project-knowledge.md` — new components, DEC references, test counts, sprint history
- `docs/architecture.md` — RegimeVector, calculators, V2 classifier
- `docs/decision-log.md` — DEC-369 through DEC-378 (reserved range)
- `docs/dec-index.md` — new entries
- `docs/sprint-history.md` — Sprint 27.6 entry
- `CLAUDE.md` — new modules, config, regime changes
- `docs/roadmap.md` — Sprint 27.6 marked complete

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session)
4. Escalation Criteria
5. Regression Checklist
6. Doc Update Checklist
7. Adversarial Review Input Package
8. Review Context File
9. Implementation Prompts ×10 (S1–S10)
10. Review Prompts ×10 (S1–S10)
11. Work Journal Handoff Prompt
