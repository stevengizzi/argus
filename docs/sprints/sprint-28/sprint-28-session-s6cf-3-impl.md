# Sprint 28, Session S6cf-3: Strategy Health Bands — Real Data

## Pre-Flight Checks
1. Run: `python -m pytest tests/intelligence/learning/ -x -q` (expect ~149 passed)
2. Run: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -5` (expect 680 passed)
3. Verify correct branch, S6cf-2 changes committed

## Objective
Replace the StrategyHealthBands placeholder heuristic with real per-strategy metrics (Sharpe, win rate, expectancy) computed from OutcomeRecords in the LearningService pipeline. Cross-layer: models → service → API type → component.

---

## Part A: Backend Data Model

### A1. Add StrategyMetricsSummary dataclass

**File: `argus/intelligence/learning/models.py`**

Add a new frozen dataclass after `DataQualityPreamble` (after line 82) and before `WeightRecommendation`:

```python
@dataclass(frozen=True)
class StrategyMetricsSummary:
    """Per-strategy trailing performance metrics.

    Computed from OutcomeRecords during learning analysis.
    Trade-sourced records used preferentially; combined if insufficient.

    Attributes:
        strategy_id: Strategy identifier.
        sharpe: Annualized Sharpe ratio (daily P&L basis), or None if < 5 trading days.
        win_rate: Proportion of trades with positive P&L.
        expectancy: Mean R-multiple if available, else mean P&L.
        trade_count: Number of records used.
        source: "trade", "combined", or "insufficient".
    """

    strategy_id: str
    sharpe: float | None
    win_rate: float
    expectancy: float
    trade_count: int
    source: str
```

### A2. Add strategy_metrics to LearningReport

**File: `argus/intelligence/learning/models.py`**

Add field to `LearningReport` dataclass (line ~183, after `correlation_result`, before `version`):

```python
    correlation_result: CorrelationResult | None
    strategy_metrics: dict[str, StrategyMetricsSummary]   # ← ADD (keyed by strategy_id)
    version: int = 1
```

**Important:** Give it a default value so existing serialized reports without this field can still deserialize. Use `field(default_factory=dict)`:

```python
from dataclasses import dataclass, asdict, field
...
    strategy_metrics: dict[str, StrategyMetricsSummary] = field(default_factory=dict)
```

Note: `field` import from dataclasses was previously removed in S6cf-1 as unused. It needs to be restored for `default_factory`.

### A3. Update `to_dict()` serialization

**File: `argus/intelligence/learning/models.py`**, in `LearningReport.to_dict()`

`asdict()` already handles this automatically — `strategy_metrics` is a `dict[str, dataclass]` which `asdict()` converts to `dict[str, dict[str, ...]]`. **No special serialization needed.** The existing `_convert_datetimes(d)` call will process any nested datetimes (there are none in StrategyMetricsSummary, so it's a no-op).

Verify this by checking that `asdict()` on a LearningReport with populated `strategy_metrics` produces the expected `{strategy_id: {sharpe: ..., win_rate: ..., ...}}` structure.

### A4. Update `from_dict()` deserialization

**File: `argus/intelligence/learning/models.py`**, in `LearningReport.from_dict()`

Before the `return cls(...)` block (around line 286), add:

```python
        # Parse strategy metrics (backward-compatible: empty dict if absent)
        raw_metrics = d.get("strategy_metrics", {})
        strategy_metrics: dict[str, StrategyMetricsSummary] = {}
        if isinstance(raw_metrics, dict):
            for sid, m in raw_metrics.items():
                if isinstance(m, dict):
                    strategy_metrics[str(sid)] = StrategyMetricsSummary(
                        strategy_id=str(m.get("strategy_id", sid)),
                        sharpe=float(m["sharpe"]) if m.get("sharpe") is not None else None,
                        win_rate=float(m["win_rate"]),
                        expectancy=float(m["expectancy"]),
                        trade_count=int(m["trade_count"]),
                        source=str(m.get("source", "trade")),
                    )
```

And add `strategy_metrics=strategy_metrics` to the `return cls(...)` constructor call.

### A5. Export StrategyMetricsSummary

**File: `argus/intelligence/learning/__init__.py`**

Add `StrategyMetricsSummary` to the imports and `__all__` list.

---

## Part B: Service Computation

### B1. Compute per-strategy metrics in LearningService

**File: `argus/intelligence/learning/learning_service.py`**

Add a private method `_compute_strategy_metrics`:

```python
    @staticmethod
    def _compute_strategy_metrics(
        records: list[OutcomeRecord],
    ) -> dict[str, StrategyMetricsSummary]:
        """Compute per-strategy trailing performance metrics.

        Uses trade-sourced records preferentially per Amendment 3 spirit.
        Falls back to combined (trade + counterfactual) if fewer than
        5 trade records for a strategy.

        Args:
            records: All OutcomeRecords from the collection window.

        Returns:
            Dict of strategy_id → StrategyMetricsSummary.
        """
        from collections import defaultdict
        from zoneinfo import ZoneInfo

        _ET = ZoneInfo("America/New_York")

        # Group by strategy
        trade_by_strategy: dict[str, list[OutcomeRecord]] = defaultdict(list)
        all_by_strategy: dict[str, list[OutcomeRecord]] = defaultdict(list)
        for r in records:
            all_by_strategy[r.strategy_id].append(r)
            if r.source == "trade":
                trade_by_strategy[r.strategy_id].append(r)

        result: dict[str, StrategyMetricsSummary] = {}

        for strategy_id, all_recs in all_by_strategy.items():
            trade_recs = trade_by_strategy.get(strategy_id, [])

            # Source selection: trade if >= 5 records, else combined
            if len(trade_recs) >= 5:
                working = trade_recs
                source = "trade"
            elif len(all_recs) >= 5:
                working = all_recs
                source = "combined"
            else:
                result[strategy_id] = StrategyMetricsSummary(
                    strategy_id=strategy_id,
                    sharpe=None,
                    win_rate=0.0,
                    expectancy=0.0,
                    trade_count=len(all_recs),
                    source="insufficient",
                )
                continue

            # Win rate
            wins = sum(1 for r in working if r.pnl > 0)
            win_rate = wins / len(working)

            # Expectancy: use r_multiple where available, else raw P&L
            r_multiples = [r.r_multiple for r in working if r.r_multiple is not None]
            if len(r_multiples) >= len(working) * 0.5:
                # Majority have R-multiples, use them
                expectancy = sum(r_multiples) / len(r_multiples)
            else:
                # Fall back to mean P&L
                expectancy = sum(r.pnl for r in working) / len(working)

            # Sharpe: annualized from daily P&L
            daily_pnl: dict[date, float] = defaultdict(float)
            for r in working:
                et_date = r.timestamp.astimezone(_ET).date()
                daily_pnl[et_date] += r.pnl

            sharpe: float | None = None
            if len(daily_pnl) >= 5:
                import numpy as np
                daily_values = list(daily_pnl.values())
                mean_daily = np.mean(daily_values)
                std_daily = np.std(daily_values, ddof=1)
                if std_daily > 0:
                    sharpe = float(mean_daily / std_daily * np.sqrt(252))

            result[strategy_id] = StrategyMetricsSummary(
                strategy_id=strategy_id,
                sharpe=sharpe,
                win_rate=win_rate,
                expectancy=expectancy,
                trade_count=len(working),
                source=source,
            )

        return result
```

**Important design notes:**
- Sharpe uses `ddof=1` (sample std) and requires ≥5 trading days. Returns None if insufficient.
- Win rate is straightforward: count(pnl > 0) / total.
- Expectancy prefers R-multiples if ≥50% of records have them, otherwise mean P&L.
- Source selection: ≥5 trade records → "trade", ≥5 total → "combined", else "insufficient".
- The `date` import and `numpy` import are already available in the module (numpy is used by analyzers — verify, else add import).

### B2. Wire into _execute_analysis pipeline

**File: `argus/intelligence/learning/learning_service.py`**, in `_execute_analysis()`

After Step 4 (data quality preamble, line 220) and before Step 5 (weight analyzer, line 222), add:

```python
        # Step 4.5: Compute per-strategy metrics
        strategy_metrics = self._compute_strategy_metrics(records)
```

Then pass it to the LearningReport constructor (line 244–254):

```python
        report = LearningReport(
            report_id=str(ULID()),
            generated_at=now,
            analysis_window_start=start_date,
            analysis_window_end=end_date,
            data_quality=data_quality,
            weight_recommendations=enriched_weight_recs,
            threshold_recommendations=threshold_recs,
            correlation_result=correlation_result,
            strategy_metrics=strategy_metrics,       # ← ADD
            version=1,
        )
```

Also add `StrategyMetricsSummary` to the imports at the top of the file:
```python
from argus.intelligence.learning.models import (
    ...
    StrategyMetricsSummary,
)
```

---

## Part C: Frontend

### C1. Add TS interface

**File: `argus/ui/src/api/learningApi.ts`**

Add interface (after `CorrelationResult`, before `DataQualityPreamble`):

```typescript
export interface StrategyMetricsSummary {
  strategy_id: string;
  sharpe: number | null;
  win_rate: number;
  expectancy: number;
  trade_count: number;
  source: string;
}
```

Add to `LearningReport` interface:

```typescript
export interface LearningReport {
  ...
  correlation_result: CorrelationResult | null;
  strategy_metrics: Record<string, StrategyMetricsSummary>;   // ← ADD
  version: number;
}
```

### C2. Replace StrategyHealthBands placeholder with real data

**File: `argus/ui/src/components/learning/StrategyHealthBands.tsx`**

This is the key change. Replace the entire `extractStrategyMetrics` function (lines 66–102) and update the component to read from `report.strategy_metrics`:

1. **Remove** the `extractStrategyMetrics` function entirely (lines 66–102).

2. **Remove** the `WeightRecommendation` import (line 14) — no longer needed.

3. **Add** import for `StrategyMetricsSummary`:
   ```typescript
   import type { LearningReport, StrategyMetricsSummary } from '../../api/learningApi';
   ```

4. **Replace** the `strategies` useMemo (lines 105–108) with:
   ```typescript
   const strategies: StrategyMetrics[] = useMemo(() => {
     if (!report?.strategy_metrics) return [];
     return Object.values(report.strategy_metrics).map((m) => ({
       strategyId: m.strategy_id,
       sharpe: m.sharpe,
       winRate: m.win_rate,
       expectancy: m.expectancy,
       tradeCount: m.trade_count,
     }));
   }, [report]);
   ```

5. **Update** the strategy name display (line 137). The current code does `strategy.strategyId.replace(/_/g, ' ')`. With real strategy IDs like `strat_orb_breakout`, apply the same abbreviation pattern as CorrelationMatrix:
   ```typescript
   {strategy.strategyId
     .replace(/^strat_/i, '')
     .replace(/_/g, ' ')
     .split(' ')
     .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
     .join(' ')}
   ```
   Or extract a shared `formatStrategyName` helper if preferred.

6. **Update empty state logic** (line 111). Currently checks `!report || strategies.length === 0`. Keep as-is — this now correctly shows the empty state when `strategy_metrics` is empty (which happens when no records exist or all strategies have insufficient data).

### C3. Update StrategyHealthBands tests

**File: `argus/ui/src/components/learning/StrategyHealthBands.test.tsx`**

The tests currently create reports with weight recommendations to drive the placeholder heuristic. Update to use `strategy_metrics` instead:

1. **Remove** `makeWeightRec` helper function.
2. **Update** `makeReport` to accept `strategy_metrics` instead of `weightRecs`:
   ```typescript
   function makeReport(
     metrics: Record<string, StrategyMetricsSummary> = {}
   ): LearningReport {
     return {
       report_id: 'r1',
       generated_at: '2026-03-28T12:00:00Z',
       analysis_window_start: '2026-03-01',
       analysis_window_end: '2026-03-28',
       data_quality: { ... },
       weight_recommendations: [],
       threshold_recommendations: [],
       correlation_result: null,
       strategy_metrics: metrics,
       version: 1,
     };
   }
   ```

3. **Update** the mock data test to use `strategy_metrics`:
   ```typescript
   it('renders strategy bars with real metrics', () => {
     const report = makeReport({
       strat_orb_breakout: {
         strategy_id: 'strat_orb_breakout',
         sharpe: 1.82,
         win_rate: 0.55,
         expectancy: 0.42,
         trade_count: 80,
         source: 'trade',
       },
       strat_vwap_reclaim: {
         strategy_id: 'strat_vwap_reclaim',
         sharpe: 0.95,
         win_rate: 0.48,
         expectancy: 0.15,
         trade_count: 45,
         source: 'trade',
       },
     });

     render(<StrategyHealthBands report={report} />);
     expect(screen.getByTestId('health-bands')).toBeInTheDocument();
     expect(screen.getByText('Orb Breakout')).toBeInTheDocument();
     expect(screen.getByText('Vwap Reclaim')).toBeInTheDocument();
     expect(screen.getByText('80 trades')).toBeInTheDocument();
     expect(screen.getByText('45 trades')).toBeInTheDocument();
   });
   ```

4. **Update** empty state test to use empty `strategy_metrics`:
   ```typescript
   it('renders empty state when report has no strategy metrics', () => {
     const report = makeReport({});
     render(<StrategyHealthBands report={report} />);
     expect(screen.getByTestId('health-bands-empty')).toBeInTheDocument();
   });
   ```

---

## Part D: Test Fixture Updates

Any test that constructs a `LearningReport` needs the `strategy_metrics` field. Since it has `default_factory=dict`, the backend fixtures should work without changes if they use keyword arguments. But verify and update as needed:

- `tests/intelligence/learning/test_models.py` — round-trip test fixture
- `tests/intelligence/learning/test_learning_store.py` — report fixture  
- `tests/intelligence/learning/test_learning_service.py` — mock report construction

For the learning service tests, the `_execute_analysis` will now call `_compute_strategy_metrics`, so the mock setup may need adjustment. Since `_compute_strategy_metrics` is a `@staticmethod`, it doesn't need mocking — it operates on the records that are already mocked.

### New backend test

Add to `tests/intelligence/learning/test_learning_service.py`:

```python
def test_strategy_metrics_computed():
    """Verify _compute_strategy_metrics produces correct values."""
    records = [
        _make_outcome(strategy_id="strat_a", pnl=100.0, r_multiple=1.0, source="trade"),
        _make_outcome(strategy_id="strat_a", pnl=-50.0, r_multiple=-0.5, source="trade"),
        _make_outcome(strategy_id="strat_a", pnl=200.0, r_multiple=2.0, source="trade"),
        _make_outcome(strategy_id="strat_a", pnl=-30.0, r_multiple=-0.3, source="trade"),
        _make_outcome(strategy_id="strat_a", pnl=80.0, r_multiple=0.8, source="trade"),
    ]
    result = LearningService._compute_strategy_metrics(records)
    assert "strat_a" in result
    m = result["strat_a"]
    assert m.trade_count == 5
    assert m.win_rate == pytest.approx(3 / 5)  # 3 positive out of 5
    assert m.source == "trade"
    assert m.expectancy == pytest.approx(0.6)  # mean of [1.0, -0.5, 2.0, -0.3, 0.8]
    # Sharpe: None because < 5 trading days (all same day if timestamps equal)
    # OR a real value if timestamps span 5+ days — depends on fixture timestamps
```

Adjust the test based on how `_make_outcome` sets timestamps. If all outcomes share the same timestamp, Sharpe will be None (< 5 daily observations from a single day). For a Sharpe test, create records spanning 5+ distinct ET dates.

---

## Constraints

- Do NOT modify any strategy files, risk manager, orchestrator, order manager
- Do NOT modify config files
- Backend changes limited to: `models.py`, `learning_service.py`, `__init__.py`
- Frontend changes limited to: `learningApi.ts`, `StrategyHealthBands.tsx`, `StrategyHealthBands.test.tsx`
- Test fixture updates in: `test_models.py`, `test_learning_store.py`, `test_learning_service.py` (as needed)
- All existing tests must continue to pass

## Test Targets

- All existing learning pytest tests must pass (update fixtures for `strategy_metrics`)
- All 680 Vitest tests must pass (update `makeReport` in StrategyHealthBands tests)
- Add 1–2 pytest tests for `_compute_strategy_metrics` (win rate, expectancy, source selection)
- Run `ruff check` on modified Python files

## Definition of Done

- [ ] `StrategyMetricsSummary` dataclass in `models.py`
- [ ] `strategy_metrics` field on `LearningReport` with `default_factory=dict`
- [ ] `from_dict()` deserializes `strategy_metrics` (backward-compatible: empty dict if absent)
- [ ] `_compute_strategy_metrics` in `LearningService` with source preference, win rate, expectancy, Sharpe
- [ ] Wired into `_execute_analysis` pipeline (Step 4.5)
- [ ] TS `StrategyMetricsSummary` interface + `strategy_metrics` on `LearningReport`
- [ ] StrategyHealthBands reads from `report.strategy_metrics` (placeholder heuristic removed)
- [ ] Strategy name display uses `strat_` prefix stripping
- [ ] Tests updated: StrategyHealthBands Vitest + backend pytest fixtures
- [ ] No regressions: all pytest + Vitest pass
- [ ] Close-out report
- [ ] @reviewer

## Session-Specific Review Focus (for @reviewer)

1. Verify `StrategyMetricsSummary` fields match what StrategyHealthBands expects (sharpe, win_rate, expectancy, trade_count)
2. Verify `_compute_strategy_metrics` source selection: ≥5 trade → "trade", ≥5 combined → "combined", else "insufficient"
3. Verify Sharpe uses `ddof=1` (sample std) and requires ≥5 trading days
4. Verify expectancy prefers R-multiples (≥50% availability) over raw P&L
5. Verify `default_factory=dict` ensures backward compatibility for old serialized reports
6. Verify StrategyHealthBands renders real metric values (not correlation proxies)
7. Verify `ruff check` on modified files — zero new warnings

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
