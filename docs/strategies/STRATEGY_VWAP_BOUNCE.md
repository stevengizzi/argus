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
1. Approach: price descends toward VWAP from above within lookback window
2. Touch: price reaches VWAP zone (within touch_zone_pct of VWAP)
3. Prior trend: at least min_trend_bars bars above VWAP before the approach
4. Bounce: current bar closes above VWAP with volume ≥ min_volume_ratio × avg volume

## Scoring (0–100)
VWAP proximity quality (30) + Bounce strength (25) + Volume confirmation (25) + Trend alignment (20)

## Parameters
12 PatternParams. Categories: detection, filtering, trade.

Key params: `touch_zone_pct`, `min_trend_bars`, `min_volume_ratio`, `lookback_bars`, `approach_bars`.

## Dependencies
- Requires `indicators["vwap"]` to be populated by IndicatorEngine (not self-contained).
- Pattern returns `PatternDetection(detected=False)` if VWAP unavailable in indicators dict.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.

## Sweep Results (Sprint 31A)
**24-symbol momentum set:** 154 trades (partial year), WR 40.3%, positive R but negative dollar P&L.
**Status:** Non-qualifying on momentum set — universe-aware re-sweep required (DEF-145). 24-symbol momentum set not representative for VWAP-bounce setups. Min_avg_volume 500K filter in `universe_filter.yaml` ensures representative universe for future sweeps.

## Notes
- VWAP dependency: requires IndicatorEngine to have computed VWAP before pattern evaluation.
- Prior uptrend validation: prevents false signals in downtrending stocks where VWAP acts as resistance.
- Operating window starts 30 minutes after open (10:30 AM) to allow VWAP to stabilize.
- Universe filter excludes low-volume names where VWAP-bounce setups lack statistical significance.
