# Strategy: Narrow Range Breakout

**Sprint:** 31A (Session 5)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Breakout / Volatility Expansion
**File:** `argus/strategies/patterns/narrow_range_breakout.py`
**Config:** `config/strategies/narrow_range_breakout.yaml`
**Universe filter:** `config/universe_filters/narrow_range_breakout.yaml` (min_avg_volume: 300K)

## Overview
Detects intraday narrowing range (volatility contraction) followed by a breakout above the consolidation high with volume expansion. Self-contained ATR computation (no external indicator dependency). Long-only gate: only fires when price is above the lookback midpoint. Targets stocks coiling before a directional move.

## Operating Window
10:00 AM – 3:00 PM ET

## Detection Logic
1. Consolidation scan: lookback_bars of narrowing successive bar ranges (ATR contraction)
2. Range qualification: consolidation range ≤ max_range_atr_ratio × ATR
3. Long-only gate: current price > midpoint of consolidation range
4. Breakout: current bar closes above consolidation high with volume ≥ min_volume_ratio × avg volume

## Scoring (0–100)
Range contraction quality (30) + Breakout strength (25) + Volume expansion (25) + Position above midpoint (20)

## Parameters
12 PatternParams. Categories: detection, filtering, trade.

Key params: `lookback_bars`, `max_range_atr_ratio`, `min_volume_ratio`, `atr_period`, `min_contraction_bars`.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.

## Sweep Results (Sprint 31A)
**24-symbol momentum set:** 2 trades (partial year).
**Status:** Pattern-universe mismatch — 24-symbol momentum set is not representative for narrow-range setups (high-momentum stocks rarely consolidate into narrow ranges). Universe-aware re-sweep required (DEF-145). Min_avg_volume 300K filter (lower than other patterns) reflects that narrow-range setups appear across a broader liquidity spectrum.

## Notes
- Self-contained ATR: does not require `indicators` dict to provide ATR values.
- Long-only gate: uses consolidation midpoint as a directional filter to avoid breakdowns.
- Lower volume threshold (300K vs 500K for other patterns): narrow-range setups can be meaningful at lower liquidity levels.
- The near-zero trade count on the momentum set is expected and is a data point, not a bug — the pattern targets a different universe profile.
