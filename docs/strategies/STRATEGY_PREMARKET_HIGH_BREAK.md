# Strategy: Pre-Market High Break

**Sprint:** 29 (Session 7, stretch scope)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Breakout
**File:** `argus/strategies/patterns/premarket_high_break.py`
**Config:** `config/strategies/premarket_high_break.yaml`
**Mode:** `live`
**Status:** PROVISIONAL — no backtest validation yet; backtest pending. Universe-aware sweep required once the `consolidate_parquet_cache.py` derived cache is activated operationally. Operates under DEC-132 provisional regime.

## Overview
Detects breakouts above the pre-market high. PM high computed from candle deque (4:00–9:30 AM ET via timestamp conversion), validated with PM volume qualification and hold-bar confirmation. Uses `set_reference_data()` for gap context scoring from prior close.

## Operating Window
9:35 AM – 10:30 AM ET

## Detection Logic
1. Split candles into PM (before 9:30 AM ET) and market (after 9:30 AM ET) via timezone conversion
2. Compute PM high from `candle.high` field (not close)
3. Reject if insufficient PM candles or PM volume below threshold
4. Breakout: market candle closes above PM high + margin
5. Volume confirmation: breakout volume ≥ ratio × avg PM volume
6. Hold confirmation: min_hold_bars consecutive closes above PM high

## Scoring (0–100)
PM quality (30) + Volume (25) + Gap context (25) + VWAP distance (20)

## Parameters
13 PatternParams. Categories: detection, filtering, trade.

## Notes
- No external API calls — PM high purely from candle deque data
- Depends on EQUS.MINI extended-hours candle accumulation in IntradayCandleStore
- Only fires for stocks with sufficient pre-market activity (primarily volatile names)

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.
