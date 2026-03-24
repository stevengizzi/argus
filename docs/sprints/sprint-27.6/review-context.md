# Sprint 27.6: Review Context File

> This file is shared by all session review prompts. Read it once at the start of each review.

---

## Review Instructions

You are conducting a Tier 2 code review. Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end, fenced with ` ```json:structured-verdict `.

---

## Sprint Spec

*(Full Sprint Spec embedded below — see `sprint-spec.md` for the authoritative copy)*

### Goal

Replace the single-dimension `MarketRegime` enum with a multi-dimensional `RegimeVector` that captures trend, volatility, breadth, correlation, sector rotation, and intraday character — all from existing data sources at zero additional cost. Foundational data-quality layer for the intelligence architecture (DEC-358 §3).

### Deliverables (Summary)

1. `RegimeVector` frozen dataclass — 6 dimensions + `primary_regime` + `regime_confidence` (signal_clarity × data_completeness)
2. `BreadthCalculator` — intraday universe participation breadth via 1-min CandleEvents. Field: `universe_breadth_score`. Returns None during ramp-up.
3. `MarketCorrelationTracker` — 20-day pairwise correlation from FMP daily bars, top N by avg daily volume from UM reference cache. Pre-market compute with asyncio.gather(). JSON cache keyed by date (ET).
4. `SectorRotationAnalyzer` — FMP `/stable/sector-performance`, circuit breaker on 403.
5. `IntradayCharacterDetector` — SPY 1-min candles, classification at 9:35/10:00/10:30 ET. Rules: Breakout > Reversal > Trending > Choppy. All thresholds configurable.
6. `RegimeClassifierV2` — composes all calculators. Delegates to V1 for primary_regime (no reimplementation). All calculators Optional (None → defaults). `run_pre_market()` with asyncio.gather().
7. Config: `config/regime.yaml` + `RegimeIntelligenceConfig`. Config-gated.
8. Orchestrator integration — V2 when enabled. `RegimeChangeEvent.regime_vector_summary: Optional[dict]`.
9. BacktestEngine — V2 with all calculators None. Trend+vol only. Golden-file parity with V1.
10. `RegimeOperatingConditions` + `matches_conditions()` — schema + logic, no strategy wiring.
11. Observatory regime visualization — session vitals bar extension.
12. `RegimeHistoryStore` — SQLite in `data/regime_history.db`. Fire-and-forget writes. 7-day retention.

### Key Acceptance Criteria

- `regime_confidence = signal_clarity × data_completeness`, clamped [0.0, 1.0]
- `universe_breadth_score` returns None until min_bars_for_valid (10) candles per symbol AND min_symbols (50) qualifying symbols
- V2 delegates to V1 internally for primary_regime — no reimplementation
- Golden-file parity: 100 days of SPY → V1 tags frozen as fixture → V2 must match bit-for-bit
- Config-gate: `enabled: false` → zero V2 code paths execute
- All calculator params Optional (None → neutral defaults) — backtest mode works
- Pre-market: correlation + sector run concurrently via asyncio.gather() < 20s
- Intraday classification: Breakout > Reversal > Trending > Choppy priority
- RegimeHistoryStore: fire-and-forget writes, write failures never disrupt classification

---

## Specification by Contradiction (Summary)

**Do NOT:**
- Implement ML-based regime classification
- Compute real-time correlation (pre-market only)
- Add VIX futures term structure
- Wire operating conditions into any strategy
- Change `MultiObjectiveResult.regime_results` key structure
- Add breadth/correlation/sector/intraday to historical backtest regime tagging
- Build Observatory deep-dive regime page
- Build RegimeVector history analytics/visualization (Sprint 28+)

**Do NOT modify:** `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `databento_data_service.py`, `strategies/*.py`, `intelligence/*.py`, `execution/*.py`, `ai/*.py`

**Do NOT refactor:** V1 `RegimeClassifier` (remains alongside V2 for config-gate bypass)

---

## Sprint-Level Regression Checklist

- [ ] V1 backward compatibility: V2 delegates to V1 for primary_regime. Same MarketRegime for same inputs.
- [ ] Golden-file parity: 100-day SPY fixture → V1 tags frozen → V2 identical.
- [ ] Orchestrator allowed_regimes unchanged — uses primary_regime.
- [ ] RegimeChangeEvent contract: old_regime/new_regime still str. regime_vector_summary is Optional (additive).
- [ ] BacktestEngine _compute_regime_tags() identical results for existing test data.
- [ ] MultiObjectiveResult unmodified (zero changes to evaluation.py, comparison.py, ensemble_evaluation.py).
- [ ] Config-gate isolation: enabled=false → no V2 instances, no Event Bus subscriptions, no FMP calls, V1 only.
- [ ] No candle processing degradation (BreadthCalculator O(1) per candle, < 1ms for 5,000 symbols).
- [ ] Pre-market startup bounded: correlation + sector < 20 seconds parallel (asyncio.gather).
- [ ] RegimeHistoryStore fire-and-forget: write failures don't affect reclassify_regime() return value or timing.
- [ ] New config fields in regime.yaml verified against Pydantic model (no silently ignored keys).
- [ ] All existing tests pass: 3,177 pytest + 620 Vitest.
- [ ] Do-not-modify files untouched.
- [ ] No circular imports among new modules.
- [ ] RegimeVector serialization roundtrip: from_dict(rv.to_dict()) == rv.

---

## Sprint-Level Escalation Criteria

Escalate to Tier 3 if:
1. RegimeVector breaks MultiObjectiveResult serialization/deserialization.
2. BreadthCalculator causes measurable latency increase (> 1ms per candle) in data processing.
3. Config-gate bypass is incomplete (any V2 code executes when disabled).
4. V2.classify() produces different MarketRegime from V1 for ANY test case.
5. Pre-market startup exceeds 60 seconds combined.
6. Circular imports between new modules and existing code.
7. Event Bus subscriber ordering issues from BreadthCalculator subscription.

Session-level halt: pre-flight failures, modifying "do not modify" files, compaction risk, scope creep beyond Modifies list.
