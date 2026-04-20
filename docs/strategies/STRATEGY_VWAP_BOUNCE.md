# Strategy: VWAP Bounce

**Sprint:** 31A (Session 4)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Continuation / Mean Reversion
**File:** `argus/strategies/patterns/vwap_bounce.py`
**Config:** `config/strategies/vwap_bounce.yaml`
**Universe filter:** `config/universe_filters/vwap_bounce.yaml` (min_avg_volume: 500K)

## Overview
Detects stocks approaching VWAP from above (uptrend continuation), touching or briefly dipping below VWAP, then bouncing with volume confirmation. Requires VWAP from the shared `indicators` dict (provided by IndicatorEngine). Targets stocks with established intraday uptrends using VWAP as dynamic support.

## Operating Window
10:30 AM – 3:00 PM ET

## Detection Logic
1. Prior trend: at least min_prior_trend_bars (default 15) bars with close above VWAP, avg distance above VWAP ≥ min_price_above_vwap_pct
2. Approach distance gate (DEF-154): at least one bar in 10-bar window before touch had close ≥ VWAP × (1 + min_approach_distance_pct) — filters oscillation noise
3. Touch: candle low within vwap_touch_tolerance_pct of VWAP (slight undershoot allowed)
4. Bounce: min_bounce_bars consecutive closes above VWAP, first bounce bar volume ≥ min_bounce_volume_ratio × recent avg
5. Follow-through (DEF-154): min_bounce_follow_through_bars additional bars above VWAP after bounce; entry at last follow-through bar
6. Signal cap (DEF-154): max_signals_per_symbol per session (default 3)

## Scoring (0–100)
VWAP proximity quality (30) + Bounce strength (25) + Volume confirmation (25) + Trend alignment (20)

## Parameters
14 PatternParams. Categories: detection, filtering, trade, scoring.

Key params: `vwap_approach_distance_pct`, `vwap_touch_tolerance_pct`, `min_bounce_bars`, `min_prior_trend_bars` (default 15), `min_bounce_volume_ratio`.

New signal density controls (Sprint 31.75 S2, DEF-154):
- `min_approach_distance_pct` (0.3%): price must be meaningfully above VWAP before approach counts
- `min_bounce_follow_through_bars` (2): bars after bounce must close above VWAP; entry at last follow-through bar
- `max_signals_per_symbol` (3): per-session cap with `reset_session_state()` method

## Defaults (Updated Sprint 31.75)
- `lookback_bars`: 50 (was 30)
- `min_prior_trend_bars`: 15 (was 10)
- `min_approach_distance_pct`: 0.003 (new)
- `min_bounce_follow_through_bars`: 2 (new)
- `max_signals_per_symbol`: 3 (new)

## Dependencies
- Requires `indicators["vwap"]` to be populated by IndicatorEngine (not self-contained).
- Pattern returns `PatternDetection(detected=False)` if VWAP unavailable in indicators dict.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.

## Sweep Results (Sprint 31A)
**24-symbol momentum set:** 154 trades (partial year), WR 40.3%, positive R but negative dollar P&L.
**Status:** Non-qualifying on momentum set — universe-aware re-sweep required (DEF-145). 24-symbol momentum set not representative for VWAP-bounce setups. Min_avg_volume 500K filter in `universe_filter.yaml` ensures representative universe for future sweeps.

**Status update (Sprint 31.75):** DEF-154 resolved. Signal density controls added. Previous sweep axes were inadequate (2–22 signals/symbol/day). 2 shadow variants deployed for CounterfactualTracker validation: v1 (density-controlled defaults) and v2 (stricter approach: 0.5% distance, 20 trend bars, 3 follow-through bars).

## Notes
- VWAP dependency: requires IndicatorEngine to have computed VWAP before pattern evaluation.
- Prior uptrend validation: prevents false signals in downtrending stocks where VWAP acts as resistance.
- Operating window starts 30 minutes after open (10:30 AM) to allow VWAP to stabilize.
- Universe filter excludes low-volume names where VWAP-bounce setups lack statistical significance.
