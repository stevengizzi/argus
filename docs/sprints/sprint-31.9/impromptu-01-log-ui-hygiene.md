# IMPROMPTU-01 — Log hygiene + UI unit fixes

> Generated from 2026-04-21 market session debrief. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Findings addressed:** 4 (F-01, F-05, F-06, F-08 from `docs/debriefs/2026-04-21.md`)
**Files touched:**
- `argus/strategies/pattern_strategy.py` (F-01 — log level change)
- `argus/analytics/trade_logger.py` (F-05 — ULID truncation width)
- `argus/api/routes/counterfactual.py` (F-06 — add MFE/MAE R-multiple computation)
- `argus/ui/src/api/types.ts` (F-06 — add new fields to TypeScript type)
- `argus/ui/src/features/trades/ShadowTradesTab.tsx` (F-06 — display new R fields)
- `argus/ui/src/features/trades/ShadowTradesTab.test.tsx` (F-06 — update test fixtures)
- `argus/core/risk_manager.py` or wherever `PRIORITY_BY_WIN_RATE is not fully implemented` is emitted (F-08 — downgrade log level)
- `tests/strategies/test_pattern_strategy.py` or nearest (F-01 — regression test)
- `tests/analytics/test_trade_logger.py` (F-05 — format test)
- `tests/api/test_counterfactual_route.py` (F-06 — REST response shape test)

**Safety tag:** `safe-during-trading`
**Theme:** Four unrelated hygiene fixes that together close out the MEDIUM/COSMETIC findings from the April 21 debrief. All four touch non-runtime paths (log emissions, REST response formatting, UI display) and can land during market hours without risk.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading can be running. These changes do NOT affect signal/order flow.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK for safe-during-trading"
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
cd argus/ui && npx vitest run --reporter=dot 2>&1 | tail -5 && cd -
# Record PASS counts here:
#   pytest: __________ (baseline)
#   vitest: __________ (baseline)
```

**Expected baseline:** at least 4,933 pytest passing (+1 DEF-150 flake possible) + 846 Vitest. If the campaign is mid-flight, the baseline will be higher — use the Work Journal's current-stage baseline. If divergent, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the message format in "Commit" below. If stopping midway, commit partial progress with `audit(IMPROMPTU-01): WIP — <reason>`.

## Implementation Order

Apply in this order to minimize file churn:

1. **F-08** (single-line log level change in risk_manager — lowest risk, warms up)
2. **F-05** (single-line change in trade_logger.py — trivial)
3. **F-01** (log level change in pattern_strategy.py — add regression test)
4. **F-06** (backend R-multiple computation + frontend display — most touch points)

## Findings to Fix

### Finding 1: F-01 log spam — `pattern_strategy.py:298`

**Severity:** CRITICAL (ops — 84% of log volume)
**File/line:** `argus/strategies/pattern_strategy.py:298`
**Current code:**

```python
if bar_count >= min_partial:
    logger.info(
        "%s: evaluating %s with partial history (%d/%d)",
        self.strategy_id,
        symbol,
        bar_count,
        lookback,
    )
    self.record_evaluation(
        symbol,
        EvaluationEventType.ENTRY_EVALUATION,
        EvaluationResult.FAIL,
        f"Warming up ({bar_count}/{lookback}) — partial history",
        metadata={
            "reduced_confidence": True,
            "bars_available": bar_count,
            "bars_required": lookback,
        },
    )
```

**Problem:** On the 2026-04-21 session, this single `logger.info` emitted 782,273 lines — 84.4% of the entire 182 MB log. With 30 strategies × 6,366 symbols × N warm-up candles the cardinality is unbounded. The `record_evaluation()` call on the next line already captures the same event in `evaluation.db` with `reduced_confidence: True` metadata; the `logger.info` is redundant duplicate instrumentation.

**Fix:** Downgrade to `logger.debug`:

```python
if bar_count >= min_partial:
    logger.debug(
        "%s: evaluating %s with partial history (%d/%d)",
        self.strategy_id,
        symbol,
        bar_count,
        lookback,
    )
    # record_evaluation call unchanged
```

**Regression test:** Add a test to `tests/strategies/test_pattern_strategy.py` (or nearest existing test file for `PatternBasedStrategy`) that captures log output at INFO level during a simulated warm-up for a single symbol and asserts **zero** INFO-level "partial history" lines. The `record_evaluation()` call should still fire (verify via a mock or by querying the eval store if test uses one).

**Commit bullet:** `- F-01: Drop INFO "partial history" spam from pattern_strategy.py:298 to DEBUG. Was 84% of 2026-04-21 log volume. DEF-NNN opened and resolved in this commit.`

---

### Finding 2: F-05 log truncation artifact — `trade_logger.py:113`

**Severity:** COSMETIC
**File/line:** `argus/analytics/trade_logger.py:113`
**Current code:**

```python
logger.info(
    "Logged trade %s: %s %s %s %.2f -> %.2f (%s)",
    trade.id[:8],  # <-- too short
    trade.strategy_id,
    ...
)
```

**Problem:** ULIDs encode a millisecond timestamp in their first 10 characters. `trade.id[:8]` truncates to ~1-second resolution, so multiple trades closing within the same second share the first 8 chars. On 2026-04-21, 79 trade-ID prefixes appeared in 2+ log lines — one prefix (`01KPR53R`) appeared across 10 trades. This is purely cosmetic in the log (DB stores the full 26-char ULID) but looks like a duplicate-ID bug during debrief reading.

**Fix:** Change to `trade.id[:12]` (covers ~1ms resolution — distinguishable). Do not change anywhere else — `trade.id` is written in full to the `trades.id` column.

**Regression test:** Add a trivial test in `tests/analytics/test_trade_logger.py` that captures the log output of `log_trade()` on a known ULID and asserts the prefix width is 12 chars.

**Commit bullet:** `- F-05: Widen trade_logger ULID truncation 8→12 chars for log disambiguation. Cosmetic only — DB stores full ULID.`

---

### Finding 3: F-06 MFE/MAE unit mismatch on Shadow Trades UI

**Severity:** MEDIUM
**Files:**
- `argus/api/routes/counterfactual.py` (and/or `argus/intelligence/counterfactual_store.py`)
- `argus/ui/src/api/types.ts`
- `argus/ui/src/features/trades/ShadowTradesTab.tsx` (lines 477, 480)
- `argus/ui/src/features/trades/ShadowTradesTab.test.tsx`

**Problem:** Backend stores `max_favorable_excursion` and `max_adverse_excursion` as **dollar amounts** (computed as `bar_high - entry_price` and `entry_price - bar_low` in `counterfactual.py:487-494`). Frontend `ShadowTradesTab.tsx:477,480` passes those values to `RMultipleCell`, which formats as `${value.toFixed(2)}R`. A $0.004 excursion displays as `+0.00R`. Operator observed this as "MFE and MAE both set to +0.00R" on 2026-04-21.

**Fix (chosen approach):** Add computed R-multiple fields to the REST response. Leave the dollar fields in the payload too (some consumers may want them later, and shadow-store schema is unchanged).

#### Backend changes

In `argus/api/routes/counterfactual.py` at the `get_counterfactual_positions` response serialization point (where each position dict is returned), enrich each dict with:

```python
def _enrich_with_r_multiples(pos: dict) -> dict:
    """Add mfe_r_multiple and mae_r_multiple computed fields.

    Returns the position dict with two additional keys; does not mutate.
    R-multiple is excursion divided by per-share risk.
    Returns None if risk cannot be computed (zero or negative risk).
    """
    entry = pos.get("entry_price")
    stop = pos.get("stop_price")
    mfe = pos.get("max_favorable_excursion")
    mae = pos.get("max_adverse_excursion")

    risk_per_share = None
    if entry is not None and stop is not None and entry > stop:
        risk_per_share = entry - stop

    mfe_r = mfe / risk_per_share if (mfe is not None and risk_per_share and risk_per_share > 0) else None
    mae_r = mae / risk_per_share if (mae is not None and risk_per_share and risk_per_share > 0) else None

    return {**pos, "mfe_r_multiple": mfe_r, "mae_r_multiple": mae_r}
```

Apply to every position returned by the `/counterfactual/positions` endpoint (list comprehension at line ~119–125 in the current file).

**Do not modify the DB schema or `_row_to_dict`** — this is a view-layer enrichment only.

#### Frontend changes

In `argus/ui/src/api/types.ts`, extend the counterfactual position type:

```typescript
// existing fields retained
max_adverse_excursion: number | null;
max_favorable_excursion: number | null;

// new fields from IMPROMPTU-01:
mfe_r_multiple: number | null;
mae_r_multiple: number | null;
```

In `argus/ui/src/features/trades/ShadowTradesTab.tsx`:

Line 477 was: `<RMultipleCell value={trade.max_favorable_excursion} />`
Change to: `<RMultipleCell value={trade.mfe_r_multiple} />`

Line 480 was: `<RMultipleCell value={trade.max_adverse_excursion} />`
Change to: `<RMultipleCell value={trade.mae_r_multiple} />`

Also update the sort keys around line 414 and line 422 (`onSort('max_favorable_excursion')` → `onSort('mfe_r_multiple')`, and same for `max_adverse_excursion` → `mae_r_multiple`).

#### Test changes

Update `argus/ui/src/features/trades/ShadowTradesTab.test.tsx`:

Line 82 was: `max_adverse_excursion: -0.3,`
Line 83 was: `max_favorable_excursion: 1.2,`

Add alongside (keep the dollar values — they're still in the response payload):

```typescript
max_adverse_excursion: -0.3,
max_favorable_excursion: 1.2,
mae_r_multiple: -0.5,   // -0.3 / 0.6 risk per share (hypothetical)
mfe_r_multiple: 2.0,    //  1.2 / 0.6
```

Update any assertions that scanned the rendered MFE/MAE columns.

Add a new backend test in `tests/api/test_counterfactual_route.py`:

- A position with entry=100, stop=98, MFE=$4, MAE=$1 should have `mfe_r_multiple: 2.0` and `mae_r_multiple: 0.5`.
- A position with entry=100, stop=100 (zero risk) should have `mfe_r_multiple: null`.
- A position with missing stop_price should have `mfe_r_multiple: null`.

**Commit bullet:** `- F-06: Add mfe_r_multiple and mae_r_multiple to /counterfactual/positions response. Frontend ShadowTradesTab now renders R-multiples correctly instead of dollar values mislabeled as R. DEF-NNN opened and resolved.`

---

### Finding 4: F-08 `PRIORITY_BY_WIN_RATE is not fully implemented` warning pollution

**Severity:** LOW
**File/line:** grep for the exact string — likely in `argus/core/risk_manager.py` or `argus/core/orchestrator.py`. Use:

```bash
grep -rn "PRIORITY_BY_WIN_RATE is not fully implemented" argus/
```

**Problem:** This warning fires 108 times per session when cross-strategy duplicate-stock conflicts hit an unfinished priority-resolution branch. It's a known unfinished feature and the warning is noise during debrief.

**Fix:** Downgrade to `logger.debug`. Leave a `# TODO(sprint-31.9-or-later): finalize PRIORITY_BY_WIN_RATE or remove` comment. Do not attempt to finish the feature in this session — that's out of scope.

**Regression test:** If there's an existing unit test asserting this log line fires at WARNING level, update it to DEBUG. Otherwise no new test needed (DEBUG-level logs are environmental, not behavioral).

**Commit bullet:** `- F-08: Downgrade "PRIORITY_BY_WIN_RATE is not fully implemented" from WARNING to DEBUG. Known unfinished feature, warning was only polluting logs.`

---

## Post-Implementation Verification

### Tests

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
cd argus/ui && npx vitest run --reporter=dot 2>&1 | tail -5 && cd -
```

**Expected:** pytest baseline + 2–3 new tests (F-01 regression + F-05 format + backend F-06); Vitest unchanged or +1 (F-06 fixture update). Net delta ≥ +3.

### Spot-check log emission (optional but recommended)

If ARGUS is running (paper mode), tail the JSONL log for 30 seconds and grep:

```bash
tail -n 10000 logs/argus_YYYYMMDD.jsonl | grep "partial history" | wc -l
# Expected: 0 (F-01 resolved)

tail -n 10000 logs/argus_YYYYMMDD.jsonl | grep "PRIORITY_BY_WIN_RATE" | wc -l
# Expected: 0 (F-08 resolved)
```

### Scope verification checklist

- [ ] No file outside the Scope list was modified
- [ ] pytest net delta ≥ +3 (F-01 regression + F-05 format + F-06 backend)
- [ ] Vitest net delta ≥ 0
- [ ] No runtime/execution path (`argus/execution/*`, `argus/core/orchestrator.py` signal flow, `argus/strategies/pattern_strategy.py` detection logic) was modified — only log calls
- [ ] `grep -rn "logger.info" argus/strategies/pattern_strategy.py | grep -i "partial"` returns nothing
- [ ] 4 new DEF numbers added to CLAUDE.md DEF table, each with status RESOLVED and commit SHA

---

## Commit

Single commit message:

```
audit(IMPROMPTU-01): log hygiene + UI unit fixes

Part of Sprint 31.9 Health & Hardening campaign (Track B, session 1/2).
Safe-during-trading. Resolves F-01, F-05, F-06, F-08 from
docs/debriefs/2026-04-21.md.

- F-01: Drop INFO "partial history" spam from pattern_strategy.py:298 to
  DEBUG. Was 84% (~150 MB) of 2026-04-21 session log volume. DEF-NNN.
- F-05: Widen trade_logger ULID truncation 8→12 chars for log
  disambiguation. Cosmetic only — DB stores full ULID.
- F-06: Add mfe_r_multiple and mae_r_multiple to /counterfactual/positions
  response. Frontend ShadowTradesTab renders R-multiples instead of
  dollar values mislabeled as R. DEF-NNN.
- F-08: Downgrade "PRIORITY_BY_WIN_RATE is not fully implemented"
  WARNING → DEBUG. Known unfinished feature. DEF-NNN (promoted from
  known-unfinished tracking).

Tests: pytest +3 (partial_history_at_debug, ulid_prefix_width_12,
r_multiple_enrichment_on_counterfactual_response). Vitest +0.
Baseline → post: <record actual numbers in close-out>
```

Replace `DEF-NNN` placeholders with the numbers you assigned. The Work Journal handoff says the operator will allocate them; confirm with the Work Journal before committing if unsure.

## Close-out

Follow `workflow/claude/skills/close-out.md`. Produce the close-out report bracketed by `---BEGIN-CLOSE-OUT---` / `---END-CLOSE-OUT---`. Run `@reviewer` for Tier 2, produce bracketed review report. Paste both into the Work Journal conversation.
