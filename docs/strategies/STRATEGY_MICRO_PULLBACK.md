# Strategy: Micro Pullback

**Sprint:** 31A (Session 3)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Continuation / Pullback
**File:** `argus/strategies/patterns/micro_pullback.py`
**Config:** `config/strategies/micro_pullback.yaml`
**Universe filter:** `config/universe_filters/micro_pullback.yaml` (min_avg_volume: 500K)

## Overview
Detects EMA-based impulse moves followed by shallow pullbacks and bounce entries. Self-contained EMA computation (no external indicator dependency). Targets stocks with established momentum making brief pauses before continuation.

## Operating Window
10:00 AM – 2:00 PM ET

## Detection Logic
1. Impulse detection: price move ≥ min_impulse_pct above EMA within lookback window
2. Pullback validation: price retraces to within max_pullback_ratio of the impulse leg
3. Bounce confirmation: current bar closes above the pullback low with volume ≥ min_volume_ratio × avg volume
4. Trend filter: EMA slope confirms uptrend direction

## Scoring (0–100)
Impulse strength (30) + Pullback quality (25) + Volume confirmation (25) + Trend alignment (20)

## Parameters
12 PatternParams. Categories: detection, filtering, trade.

Key params: `ema_period`, `min_impulse_pct`, `max_pullback_ratio`, `min_volume_ratio`, `lookback_bars`.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.

## Sweep Results (Sprint 31A)
**24-symbol momentum set:** 417 trades (partial year), WR 49.6%, avg_R +0.0046 (breakeven).
**Status:** Non-qualifying on momentum set — universe-aware re-sweep required (DEF-145). Min_avg_volume 500K filter in `universe_filter.yaml` ensures representative universe for future sweeps.

## Notes
- Self-contained EMA: does not require `indicators` dict to provide EMA values.
- Operating window avoids the volatile first 30 minutes and the last 90 minutes of trading.
- Universe filter excludes low-volume names where micro pullbacks lack statistical significance.
