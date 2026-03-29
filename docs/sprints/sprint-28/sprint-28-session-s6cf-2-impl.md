# Sprint 28, Session S6cf-2: Trade Overlap Count + Dead Code Cleanup

## Pre-Flight Checks
1. Run: `python -m pytest tests/intelligence/learning/ -x -q` (expect 147 passed)
2. Run: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -5` (expect 680 passed)
3. Verify correct branch, S6cf-1 changes committed

## Objective
Two scoped fixes:
1. Add trade overlap count to CorrelationResult — closes S6c-F1 spec deviation (tooltip missing overlap count)
2. Remove dead reconciliation heuristic — closes S1-F2 (unreachable code in outcome_collector.py)

---

## Part A: Dead Code Removal (S1-F2)

### A6. Remove dead reconciliation heuristic

**File: `argus/intelligence/learning/outcome_collector.py`, lines 105–115**

The reconciliation detection heuristic checks `r.rejection_reason` on trade-sourced `OutcomeRecord`s, but trade records are always constructed with `rejection_reason=None` (line ~237 in `_collect_trades()`). The list comprehension always produces an empty list. The `if reco_trades:` block never triggers. This is dead code.

**Remove the entire block** (lines 105–115):
```python
        # Flag pre-Sprint-27.95 reconciliation artifacts     ← DELETE
        reco_trades = [                                        ← DELETE
            r for r in trades                                  ← DELETE
            if r.rejection_reason is not None                  ← DELETE
            and "reconciliation" in r.rejection_reason.lower() ← DELETE
        ]                                                      ← DELETE
        if reco_trades:                                        ← DELETE
            known_gaps.append(                                 ← DELETE
                f"{len(reco_trades)} reconciliation-sourced "  ← DELETE
                "trades may have synthetic close prices"       ← DELETE
            )                                                  ← DELETE
```

The remaining two heuristics (no counterfactual data, zero quality scores — lines 117–129) are valid and stay.

**Test impact:** The `test_data_quality_preamble_gaps` test in `test_outcome_collector.py` may test for the reconciliation gap message. If so, remove that assertion. If not, no test changes needed.

---

## Part B: Trade Overlap Count (S6c-F1)

This is a cross-layer change: backend analyzer → data model → serialization → TS interface → tooltip.

### B1. Compute overlap count per pair

**File: `argus/intelligence/learning/correlation_analyzer.py`**

In the main loop (lines 93–104), after computing the correlation, compute the overlap (number of aligned trading days used for the correlation):

```python
        overlap_counts: dict[tuple[str, str], int] = {}

        for i, strat_a in enumerate(active_strategies):
            for strat_b in active_strategies[i + 1:]:
                pair = (strat_a, strat_b)
                strategy_pairs.append(pair)

                corr = self._compute_pearson(
                    daily_pnl[strat_a], daily_pnl[strat_b]
                )
                correlation_matrix[pair] = corr

                # Count aligned trading days (union — missing days treated as 0)
                overlap_counts[pair] = len(
                    set(daily_pnl[strat_a].keys()) | set(daily_pnl[strat_b].keys())
                )

                if abs(corr) >= config.correlation_threshold:
                    flagged_pairs.append(pair)
```

Pass `overlap_counts` to the `CorrelationResult` constructor (line 112–118):
```python
        return CorrelationResult(
            strategy_pairs=strategy_pairs,
            correlation_matrix=correlation_matrix,
            flagged_pairs=flagged_pairs,
            overlap_counts=overlap_counts,          # ← ADD
            excluded_strategies=excluded_strategies,
            window_days=config.correlation_window_days,
        )
```

Also update the early-return empty result (line 80–86) to include `overlap_counts={}`.

### B2. Add `overlap_counts` to CorrelationResult model

**File: `argus/intelligence/learning/models.py`**

Add field to `CorrelationResult` dataclass (after `flagged_pairs`, before `excluded_strategies`):
```python
@dataclass(frozen=True)
class CorrelationResult:
    strategy_pairs: list[tuple[str, str]]
    correlation_matrix: dict[tuple[str, str], float]
    flagged_pairs: list[tuple[str, str]]
    overlap_counts: dict[tuple[str, str], int]     # ← ADD
    excluded_strategies: list[str]
    window_days: int
```

### B3. Update `to_dict()` serialization

**File: `argus/intelligence/learning/models.py`**, in `LearningReport.to_dict()` (around lines 195–209)

After the `flagged_pairs` serialization block, add overlap_counts serialization with the same `|` key pattern:
```python
            if isinstance(cr, dict) and "overlap_counts" in cr:
                oc = cr["overlap_counts"]
                cr["overlap_counts"] = {
                    f"{k[0]}|{k[1]}": v for k, v in oc.items()
                }
```

### B4. Update `from_dict()` deserialization

**File: `argus/intelligence/learning/models.py`**, in `LearningReport.from_dict()` (around lines 259–269)

After the `flagged_pairs` reconstruction, add overlap_counts reconstruction:
```python
            raw_overlap = cr_raw.get("overlap_counts", {})
            overlap_counts: dict[tuple[str, str], int] = {}
            if isinstance(raw_overlap, dict):
                for key_str, val in raw_overlap.items():
                    parts = key_str.split("|")
                    if len(parts) == 2:
                        overlap_counts[(parts[0], parts[1])] = int(val)
```

And add `overlap_counts=overlap_counts` to the `CorrelationResult` constructor call (line 263).

### B5. Update TypeScript interface

**File: `argus/ui/src/api/learningApi.ts`**

Add to the `CorrelationResult` interface:
```typescript
export interface CorrelationResult {
  strategy_pairs: [string, string][];
  correlation_matrix: Record<string, number>;
  flagged_pairs: [string, string][];
  overlap_counts: Record<string, number>;    // ← ADD (same "|" key format as matrix)
  excluded_strategies: string[];
  window_days: number;
}
```

### B6. Add overlap count to tooltip

**File: `argus/ui/src/components/learning/CorrelationMatrix.tsx`**

Three changes:

1. **Add `overlapDays` to `TooltipState`** (line 65):
   ```typescript
   interface TooltipState {
     x: number;
     y: number;
     stratA: string;
     stratB: string;
     value: number;
     flagged: boolean;
     overlapDays: number | null;   // ← ADD
   }
   ```

2. **Look up overlap count in the onMouseEnter handler** (around line 205). After setting `value` and `flagged`, compute overlap:
   ```typescript
   const overlapKey1 = pairKey(rowName, colName);
   const overlapKey2 = pairKey(colName, rowName);
   const overlapDays = correlationResult.overlap_counts?.[overlapKey1]
     ?? correlationResult.overlap_counts?.[overlapKey2]
     ?? null;
   ```
   Add `overlapDays` to the `setTooltip` object.

3. **Render overlap in tooltip** (around line 290, after the correlation value line):
   ```tsx
   {tooltip.overlapDays !== null && (
     <div className="text-argus-text-dim tabular-nums">
       Aligned days: {tooltip.overlapDays}
     </div>
   )}
   ```

### B7. Fix existing test mock data

**File: `argus/ui/src/components/learning/CorrelationMatrix.test.tsx`**

The `makeCorrelation` helper still uses `:` delimiter in `correlation_matrix` keys (leftover from pre-S6cf-1). Update to `|`:

```typescript
function makeCorrelation(overrides?: Partial<CorrelationResult>): CorrelationResult {
  return {
    strategy_pairs: [['orb_breakout', 'vwap_reclaim']],
    correlation_matrix: { 'orb_breakout|vwap_reclaim': 0.35 },   // ← FIX: : → |
    flagged_pairs: [],
    overlap_counts: { 'orb_breakout|vwap_reclaim': 15 },         // ← ADD
    excluded_strategies: [],
    window_days: 30,
    ...overrides,
  };
}
```

Also update backend test fixtures in `tests/intelligence/learning/test_correlation_analyzer.py` if they construct `CorrelationResult` directly — add `overlap_counts` field.

---

## Constraints

- Do NOT modify any strategy files, risk manager, orchestrator, order manager
- Do NOT modify config files
- Backend changes limited to: `outcome_collector.py`, `correlation_analyzer.py`, `models.py`
- Frontend changes limited to: `learningApi.ts`, `CorrelationMatrix.tsx`, `CorrelationMatrix.test.tsx`
- All existing tests must continue to pass (update mocks/fixtures as needed for new field)

## Test Targets

- All existing 147 learning pytest tests must pass (update fixtures for `overlap_counts`)
- All 680 Vitest tests must pass (update mock data for `overlap_counts` + fix `:` → `|` keys)
- Add 1–2 pytest tests:
  - `test_overlap_count_computed_per_pair` — verify `overlap_counts` populated with correct day counts
  - Optionally: `test_overlap_count_empty_result` — verify empty overlap_counts in early-return path
- Run `ruff check` on modified Python files

## Definition of Done

- [ ] A6: Dead reconciliation heuristic removed from `outcome_collector.py`
- [ ] B1: `overlap_counts` computed in `correlation_analyzer.py` main loop + early return
- [ ] B2: `overlap_counts` field added to `CorrelationResult` dataclass
- [ ] B3: `to_dict()` serializes `overlap_counts` with `|` key pattern
- [ ] B4: `from_dict()` deserializes `overlap_counts` with `|` key parsing
- [ ] B5: TS `CorrelationResult` interface includes `overlap_counts`
- [ ] B6: Tooltip shows "Aligned days: N"
- [ ] B7: Existing test mocks updated (`:` → `|` keys, `overlap_counts` field added)
- [ ] No regressions: all 147 pytest + 680 Vitest pass
- [ ] Close-out report
- [ ] @reviewer

## Session-Specific Review Focus (for @reviewer)

1. Verify `overlap_counts` uses union of dates (not intersection) — matching how `_compute_pearson` aligns data
2. Verify `to_dict()` / `from_dict()` round-trip for `overlap_counts` (same `|` key pattern as `correlation_matrix`)
3. Verify tooltip shows "Aligned days" only when `overlap_counts` is available (graceful null handling)
4. Verify dead code removal doesn't break any existing tests (check `test_data_quality_preamble_gaps`)
5. Verify CorrelationMatrix test mock uses `|` delimiter (not stale `:`)
6. Verify `ruff check` on modified files — zero new warnings

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
