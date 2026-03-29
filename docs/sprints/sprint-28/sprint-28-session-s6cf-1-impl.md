# Sprint 28, Session S6cf-1: Batch Findings + Visual Review Fixes

## Pre-Flight Checks
1. Run: `python -m pytest tests/intelligence/learning/ -x -q` (expect 147 passed)
2. Run: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -5` (expect 680 passed)
3. Verify correct branch

## Objective
Address accumulated code findings from S1–S5 reviews, fix a functional bug in the correlation matrix, and resolve three visual review issues on the Learning tab. Surgical fix session — no new features, no architectural changes.

---

## Part A: Code Findings Fixes

### A1. Remove unused import (S1-F1)

**File: `argus/intelligence/learning/models.py`, line 12**
- Remove `import json`. It is unused in this file. (JSON parsing is only in `outcome_collector.py`.)
- Note: S2b-F1 (unused `ConfidenceLevel` import in `correlation_analyzer.py`) was already resolved before commit — verified in fresh clone.

### A2. Fix import ordering (S4-F2)

**File: `argus/intelligence/quality_engine.py`, line 21**
- `import yaml` is placed between the local imports `from argus.core.regime import MarketRegime` (line 20) and `from argus.intelligence.config import QualityEngineConfig` (line 23), breaking stdlib/third-party → local grouping.
- Move `import yaml` to line 11 area, after `import json` and `import logging` (the other stdlib/third-party imports), before the `from argus.*` block starting at line 18.

### A3. Replace `assert` with proper guards (S4-F4, S5-F2)

**File: `argus/intelligence/learning/config_proposal_manager.py`**

Two locations:

1. **Line 105** in `_read_yaml()`:
   ```python
   # REPLACE:
   assert isinstance(parsed, dict)
   # WITH:
   if not isinstance(parsed, dict):
       raise ValueError(f"Expected YAML to parse as dict, got {type(parsed).__name__}")
   ```

2. **Line 254** in `validate_proposal()`:
   ```python
   # REPLACE:
   assert isinstance(weights, dict)
   # WITH:
   if not isinstance(weights, dict):
       raise ValueError(f"Expected weights to be a dict, got {type(weights).__name__}")
   ```

**File: `argus/api/routes/learning.py`**

Three locations — lines 285, 335, 397 (after `get_proposal()` calls in approve/dismiss/revert endpoints):
```python
# REPLACE each:
assert updated is not None
# WITH:
if updated is None:
    raise HTTPException(status_code=500, detail="Proposal update failed unexpectedly")
```
`HTTPException` is already imported from `fastapi` (verify at top of file).

### A4. Document test assumption (S4-F3)

**File: `tests/intelligence/learning/test_config_proposal_manager.py`, line 322**

Add a comment above `proposed_value=200.0`:
```python
# Relies on QualityThresholdsConfig validating values in [0, 100] range.
# If that validator is ever relaxed, this test needs a different invalid value.
proposed_value=200.0,  # > 100, Pydantic will reject
```

### A5. Document stale current_value behavior (S4-F5)

**File: `argus/intelligence/learning/config_proposal_manager.py`**

In `apply_pending()` method, near line 167 where the drift guard checks `proposal.current_value`:
```python
# NOTE: When processing multiple proposals in a single batch, later proposals
# use current_value from analysis time, not post-prior-proposal values.
# This is conservative by design — drift may be overcounted, never undercounted.
proposed_delta = abs(proposal.proposed_value - proposal.current_value)
```

---

## Part B: Functional Bug Fix

### B1. CRITICAL: Correlation matrix key delimiter mismatch

**The correlation matrix is completely non-functional.** The backend serializes `correlation_matrix` keys with `|` delimiter (e.g., `"strat_bull_flag|strat_orb_scalp"`) in `models.py` `to_dict()` (line ~414). The frontend's `pairKey()` function in `CorrelationMatrix.tsx` (line 41) uses `:` delimiter. Every lookup fails → all cells render as dark grey.

**File: `argus/ui/src/components/learning/CorrelationMatrix.tsx`, line 41**
```typescript
// REPLACE:
return `${a}:${b}`;
// WITH:
return `${a}|${b}`;
```

This one-character fix makes the entire heatmap functional.

---

## Part C: Visual Review Fixes

### C1. Correlation matrix axis labels clipped (VR-1)

**File: `argus/ui/src/components/learning/CorrelationMatrix.tsx`**

**Root cause:** The `shortenName` function (line 56) strips `_strategy` **suffix** but actual strategy IDs have `strat_` **prefix** (e.g., `strat_bull_flag`, `strat_flat_top_breakout`). So the function does nothing, and labels come out as "Strat Bull Flag", "Strat Flat Top Breakout" etc. — too long for `labelWidth = 80`.

**Fix (two changes):**

1. **Replace `shortenName` function** (lines 55–63):
   ```typescript
   /** Shorten strategy name for axis labels. */
   function shortenName(name: string): string {
     return name
       .replace(/^strat_/i, '')      // Strip "strat_" PREFIX (the actual pattern)
       .replace(/^strategy_/i, '')   // Also handle "strategy_" prefix if present
       .replace(/_/g, ' ')
       .split(' ')
       .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
       .join(' ');
   }
   ```
   Results: "Bull Flag", "Flat Top Breakout", "Orb Breakout", "Orb Scalp", "Red To Green", "Vwap Reclaim", "Afternoon Momentum". Longest is "Afternoon Momentum" (18 chars) and "Flat Top Breakout" (17 chars).

2. **Increase `labelWidth`** (line 115) from `80` to `120`:
   ```typescript
   const labelWidth = 120;
   ```
   And increase `labelHeight` (line 116) from `60` to `80` for the rotated column labels:
   ```typescript
   const labelHeight = 80;
   ```

**Verification:** All 7 strategy names should be fully readable on both axes. Tooltip should still show the full original name (it already does via `stratA`/`stratB` in tooltip state).

### C2. Conflicting threshold recommendations display (VR-2)

**File: `argus/ui/src/components/learning/LearningInsightsPanel.tsx`**

**Problem:** When both A12 conditions fire for the same grade, two identical-looking cards appear with the same React key (`key={rec.grade}`), and `proposalsByField` loses one proposal since both share the same `field_path` (`thresholds.b`).

**Fix — three changes:**

**Change 1: Build multi-proposal map and conflict groups.**

After the existing `proposalsByField` useMemo (line 67–75), add:

```typescript
// Group proposals by field_path (handles same-grade conflicts where
// proposalsByField Map loses one due to key collision)
const proposalsByFieldMulti = useMemo(() => {
  const map = new Map<string, ConfigProposal[]>();
  if (proposalsData?.proposals) {
    for (const proposal of proposalsData.proposals) {
      const existing = map.get(proposal.field_path) ?? [];
      existing.push(proposal);
      map.set(proposal.field_path, existing);
    }
  }
  return map;
}, [proposalsData]);

// Separate normal vs conflicting threshold recommendations
const { normalThresholds, conflictingThresholds } = useMemo(() => {
  if (!activeReport?.threshold_recommendations) {
    return { normalThresholds: [], conflictingThresholds: [] };
  }
  const byGrade = new Map<string, ThresholdRecommendation[]>();
  for (const rec of activeReport.threshold_recommendations) {
    const existing = byGrade.get(rec.grade) ?? [];
    existing.push(rec);
    byGrade.set(rec.grade, existing);
  }
  const normal: ThresholdRecommendation[] = [];
  const conflicting: {
    grade: string;
    lower: ThresholdRecommendation;
    raise: ThresholdRecommendation;
    lowerProposal: ConfigProposal | undefined;
    raiseProposal: ConfigProposal | undefined;
  }[] = [];

  for (const [grade, recs] of byGrade) {
    if (recs.length === 2) {
      const lower = recs.find((r) => r.recommended_direction === 'lower');
      const raise = recs.find((r) => r.recommended_direction === 'raise');
      if (lower && raise) {
        const fieldPath = `quality_engine.thresholds.${grade}`;
        const allProposals = proposalsByFieldMulti.get(fieldPath) ?? [];
        conflicting.push({
          grade,
          lower,
          raise,
          lowerProposal: allProposals.find(
            (p) => p.proposed_value < p.current_value
          ),
          raiseProposal: allProposals.find(
            (p) => p.proposed_value > p.current_value
          ),
        });
        continue;
      }
    }
    normal.push(...recs);
  }
  return { normalThresholds: normal, conflictingThresholds: conflicting };
}, [activeReport?.threshold_recommendations, proposalsByFieldMulti]);
```

**Change 2: Update the `pendingCount` calculation** (around line 166) to account for the split:

```typescript
const pendingCount =
  weight_recommendations.length +
  normalThresholds.length +
  conflictingThresholds.length;
```

**Change 3: Replace the threshold rendering section** (lines 286–309).

Render `normalThresholds` with existing `ThresholdRecommendationCard`, and `conflictingThresholds` with a combined card:

```tsx
{/* Threshold Recommendations */}
{(normalThresholds.length > 0 || conflictingThresholds.length > 0) && (
  <div>
    <h4 className="text-xs font-medium text-argus-text-dim uppercase tracking-wide mb-2">
      Threshold Recommendations (
      {normalThresholds.length + conflictingThresholds.length})
    </h4>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {/* Normal (single-direction) threshold cards */}
      {normalThresholds.map((rec) => {
        const fieldPath = `quality_engine.thresholds.${rec.grade}`;
        const proposal = proposalsByField.get(fieldPath);
        return (
          <ThresholdRecommendationCard
            key={`${rec.grade}-${rec.recommended_direction}`}
            recommendation={rec}
            proposalId={proposal?.proposal_id ?? ''}
            status={proposal?.status ?? 'PENDING'}
            humanNotes={proposal?.human_notes ?? null}
            onApprove={handleApprove}
            onDismiss={handleDismiss}
            onRevert={handleRevert}
          />
        );
      })}

      {/* Conflicting (same-grade, both directions) combined cards */}
      {conflictingThresholds.map(
        ({ grade, lower, raise: raiseRec, lowerProposal, raiseProposal }) => (
          <div
            key={`conflict-${grade}`}
            className="rounded-lg border border-amber-500/30 bg-argus-surface-1 p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-argus-text">
                Grade {grade.toUpperCase()}
              </span>
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-400/10 text-amber-400">
                Conflicting
              </span>
            </div>

            <div className="grid grid-cols-2 gap-x-4 text-sm">
              <div className="text-argus-text-dim">Missed opp. rate</div>
              <div className="text-right text-argus-text">
                {(lower.missed_opportunity_rate * 100).toFixed(1)}%
              </div>
              <div className="text-argus-text-dim">Correct rej. rate</div>
              <div className="text-right text-argus-text">
                {(lower.correct_rejection_rate * 100).toFixed(1)}%
              </div>
              <div className="text-argus-text-dim">Sample size</div>
              <div className="text-right text-argus-text">
                {lower.sample_size}
              </div>
            </div>

            <p className="text-xs text-gray-400">
              High missed opportunity rate suggests lowering, but low correct
              rejection rate suggests raising. Manual review recommended.
            </p>

            {/* Action buttons — only show when both proposals are PENDING */}
            {lowerProposal?.status === 'PENDING' &&
              raiseProposal?.status === 'PENDING' && (
                <div className="flex gap-2 pt-1">
                  <button
                    className="text-xs px-3 py-1 rounded border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10"
                    onClick={() =>
                      lowerProposal &&
                      handleApprove(lowerProposal.proposal_id)
                    }
                  >
                    Approve Lower
                  </button>
                  <button
                    className="text-xs px-3 py-1 rounded border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10"
                    onClick={() =>
                      raiseProposal &&
                      handleApprove(raiseProposal.proposal_id)
                    }
                  >
                    Approve Raise
                  </button>
                  <button
                    className="text-xs px-3 py-1 rounded text-gray-400 hover:text-gray-300"
                    onClick={() => {
                      if (lowerProposal)
                        handleDismiss(lowerProposal.proposal_id);
                      if (raiseProposal)
                        handleDismiss(raiseProposal.proposal_id);
                    }}
                  >
                    Dismiss Both
                  </button>
                </div>
              )}

            {/* Show resolved state if proposals are no longer pending */}
            {(lowerProposal?.status && lowerProposal.status !== 'PENDING') && (
              <div className="text-xs text-argus-text-dim">
                Lower: {lowerProposal.status}
              </div>
            )}
            {(raiseProposal?.status && raiseProposal.status !== 'PENDING') && (
              <div className="text-xs text-argus-text-dim">
                Raise: {raiseProposal.status}
              </div>
            )}
          </div>
        )
      )}
    </div>
  </div>
)}
```

### C3. Empty weight recommendations placeholder (VR-4)

**File: `argus/ui/src/components/learning/LearningInsightsPanel.tsx`**

Currently the weight section is conditionally rendered only when `weight_recommendations.length > 0` (line 259). Add an else branch:

After the closing `</div>` of the weight recommendations block (after line 282), and before the threshold section:
```tsx
{weight_recommendations.length === 0 && (
  <div>
    <h4 className="text-xs font-medium text-argus-text-dim uppercase tracking-wide mb-2">
      Weight Recommendations
    </h4>
    <p className="text-sm text-argus-text-dim py-3">
      No weight adjustments recommended — insufficient significant
      correlations between quality dimensions and trade outcomes. More
      trading data will improve signal strength.
    </p>
  </div>
)}
```

### C4. Strategy Health empty state message (VR-3, partial fix)

**File: `argus/ui/src/components/learning/StrategyHealthBands.tsx`, line 117**

The current message says "Strategy health data will appear after the first analysis" — misleading when analysis has been run but `weight_recommendations` is empty (which is the actual condition triggering the empty state at line 111).

Replace:
```typescript
Strategy health data will appear after the first analysis
```
With:
```typescript
{!report
  ? 'Strategy health data will appear after the first analysis'
  : 'Not enough data for strategy health metrics yet'}
```

This shows the correct message based on whether analysis has been run.

---

## Constraints

- Do NOT modify any backend analysis logic (analyzers, service, store)
- Do NOT modify any strategy files, risk manager, orchestrator, order manager
- Do NOT modify existing test files from S1–S5 (add new tests only if needed)
- Do NOT touch `config/learning_loop.yaml` or `config/system_live.yaml`
- Part A changes are backend Python; Parts B/C are frontend TypeScript/React
- All existing tests must continue to pass

## Test Targets

- All 147 existing learning pytest tests must pass
- All 680 existing Vitest tests must pass
- Add 1–2 Vitest tests for the conflicting threshold card if time permits:
  - Test: conflicting recommendations for same grade render single combined card
  - Test: "Dismiss Both" fires two dismiss calls
- Run `ruff check argus/intelligence/learning/ argus/intelligence/quality_engine.py argus/api/routes/learning.py` after Part A to confirm lint fixes

## Definition of Done

- [ ] A1: Unused `import json` removed from `models.py`
- [ ] A2: `import yaml` in correct position in `quality_engine.py`
- [ ] A3: All 5 `assert` statements replaced with `if/raise` (2 in config_proposal_manager.py, 3 in learning.py)
- [ ] A4: Test assumption documented in `test_config_proposal_manager.py`
- [ ] A5: Stale current_value behavior documented in `config_proposal_manager.py`
- [ ] B1: Correlation matrix `pairKey` uses `|` delimiter (functional fix)
- [ ] C1: Correlation matrix labels readable — `shortenName` strips `strat_` prefix, `labelWidth=120`, `labelHeight=80`
- [ ] C2: Same-grade conflicting threshold recs render as single combined card with amber "Conflicting" badge
- [ ] C2: `proposalsByFieldMulti` handles duplicate `field_path` entries
- [ ] C2: "Approve Lower" / "Approve Raise" / "Dismiss Both" buttons wired correctly
- [ ] C2: No duplicate React keys
- [ ] C3: Empty weight recommendations show header + placeholder message
- [ ] C4: Strategy Health empty state message context-aware
- [ ] All existing tests pass (147 pytest, 680 Vitest)
- [ ] Close-out report
- [ ] @reviewer

## Session-Specific Review Focus (for @reviewer)

1. Verify `pairKey` uses `|` delimiter and matrix cells now show colors (not all grey)
2. Verify all 5 `assert` replacements use correct exception types (ValueError for YAML parsing, HTTPException for routes)
3. Verify correlation matrix labels are fully readable — no clipping on either axis
4. Verify conflicting threshold card shows both Approve buttons with correct proposal IDs
5. Verify "Dismiss Both" calls `handleDismiss` for both proposals
6. Verify empty weight placeholder appears only when report exists but recommendations are empty
7. Verify `ruff check` on modified Python files — zero new warnings
8. Verify no duplicate React keys in threshold section

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
