# Sprint 29 — Batch Fix Close-Out

## Summary
Addressed 5 LOW-severity findings from Tier 2 reviews across Sprint 29 sessions S3–S7. All fixes are cosmetic, documentation, or dead-code removal with no behavioral impact.

## Files Modified

| File | Fixes Applied |
|------|--------------|
| `argus/core/config.py` | Fix 1 |
| `argus/strategies/patterns/hod_break.py` | Fix 2, 3, 5 |
| `argus/strategies/patterns/abcd.py` | Fix 3 |
| `argus/strategies/patterns/premarket_high_break.py` | Fix 4, 5 |
| `argus/strategies/patterns/dip_and_rip.py` | Fix 5 |
| `argus/strategies/patterns/gap_and_go.py` | Fix 5 |
| `tests/strategies/patterns/test_hod_break.py` | Fix 3, 5 |
| `tests/strategies/patterns/test_abcd.py` | Fix 3 |

## Per-Fix Summary

### Fix 1: Align DipAndRipConfig Pydantic defaults with YAML
- **What:** Changed `DipAndRipConfig.target_1_r` default from `1.0` to `1.5` and `target_2_r` from `2.0` to `2.5`
- **Why:** YAML (`config/strategies/dip_and_rip.yaml`) specifies 1.5 and 2.5; mismatched Pydantic defaults create confusion

### Fix 2: Add clarifying comment on HOD Break dual scoring weights
- **What:** Updated `_compute_confidence()` docstring to explain the intentional difference between its 25/25/25/25 weights and `score()`'s 30/25/25/20 weights
- **Why:** Undocumented difference could lead to accidental "alignment" in future changes

### Fix 3: Remove `min_score_threshold` dead code
- **What:** Removed `min_score_threshold` parameter from HOD Break and ABCD (constructor, `self._` attribute, `get_default_params()`)
- **Why:** Parameter stored but never checked in `detect()` — misleading dead code

#### Full Audit Results

| Pattern | Has `min_score_threshold`? | Enforced in `detect()`? | Action |
|---------|---------------------------|------------------------|--------|
| Dip-and-Rip | No | N/A | None needed |
| HOD Break | Yes | No | **Removed** |
| Gap-and-Go | Yes | Yes (line 227) | Kept |
| ABCD | Yes | No | **Removed** |
| PM High Break | Yes | Yes (line 342) | Kept |

**Note:** The S5 review flagged Gap-and-Go as dead code, but the actual code *does* enforce `min_score_threshold` at line 227 (`if self._min_score_threshold > 0 and confidence < self._min_score_threshold: return None`). Same for PM High Break. Only HOD Break and ABCD were truly dead.

#### Test Changes
- `test_hod_break.py`: param count assertion `12` → `11`
- `test_abcd.py`: param count assertion `>= 14` → `>= 13`

### Fix 4: Deduplicate PM High Break scoring logic
- **What:** Replaced `score()` body with delegation to `_compute_confidence()`, extracting metadata values and passing them as arguments
- **Why:** `score()` and `_compute_confidence()` had identical 4-component formulas (PM quality, volume, gap context, VWAP distance); if one was updated without the other, they'd silently diverge

### Fix 5: Fix PatternParam category labels for trade-level params
- **What:** Changed `category` from "detection"/"scoring" to "trade" for stop/target params across 4 patterns

#### Full Audit Results

| Pattern | Param | Old Category | New Category |
|---------|-------|-------------|-------------|
| Dip-and-Rip | `stop_buffer_atr_mult` | detection | **trade** |
| Dip-and-Rip | `target_ratio` | detection | **trade** |
| HOD Break | `stop_buffer_atr_mult` | detection | **trade** |
| HOD Break | `target_ratio` | scoring | **trade** |
| HOD Break | `target_1_r` | scoring | **trade** |
| HOD Break | `target_2_r` | scoring | **trade** |
| Gap-and-Go | `target_ratio` | detection | **trade** |
| PM High Break | `stop_buffer_atr_mult` | detection | **trade** |
| PM High Break | `target_ratio` | scoring | **trade** |
| PM High Break | `target_1_r` | scoring | **trade** |
| PM High Break | `target_2_r` | scoring | **trade** |
| ABCD | `stop_buffer_atr_mult` | trade | *(already correct)* |
| ABCD | `target_extension` | trade | *(already correct)* |

#### Test Changes
- `test_hod_break.py`: `valid_categories` set updated to include `"trade"`

## Test Delta
- **Baseline:** 4,178 passed
- **Final:** 4,178 passed (0 added, 0 removed)
- **Pattern suite:** 240 passed

## Constraints Verified
- No modifications to: `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `ui/`, `api/`, `ai/`, `intelligence/`, `patterns/base.py`, `pattern_strategy.py`
- No detection or scoring *behavior* changed
- All existing tests pass

## Self-Assessment
**CLEAN** — All 5 fixes applied exactly as specified. One deviation from the prompt: Gap-and-Go's `min_score_threshold` was kept because the code actually enforces it (contrary to the review's "confirmed dead code" claim). This is the conservative, correct choice.

## Context State
**GREEN** — Session well within context limits.
