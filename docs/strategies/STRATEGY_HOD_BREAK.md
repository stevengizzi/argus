# Strategy: HOD Break

**Sprint:** 29 (Session 4)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Breakout
**File:** `argus/strategies/patterns/hod_break.py`
**Config:** `config/strategies/hod_break.yaml`
**Mode:** `live`
**Status:** PROVISIONAL — no backtest validation yet; no walk-forward evidence. Backtest pending. Operates under DEC-132 provisional regime until a universe-aware sweep with DuckDB-pre-filtered Parquet cache produces statistically significant evidence.

## Overview
Tracks dynamic high-of-day, detects consolidation near HOD with ATR-based range check, confirms breakout with volume and hold-bar duration. Primary midday signal coverage provider.

## Operating Window
10:00 AM – 3:30 PM ET

## Detection Logic
1. Dynamic HOD tracking across all candles (updated per bar)
2. Consolidation detection: range ≤ ATR × threshold, ≥50% bars near HOD
3. Breakout: close above breakout threshold with volume ≥ ratio × avg consolidation volume
4. Hold confirmation: min_hold_bars consecutive closes above breakout threshold
5. Multi-test resistance scoring (HOD touch count)

## Scoring (0–100)
Consolidation quality (30) + Volume (25) + HOD touches (25) + VWAP distance (20)

## Parameters
11 PatternParams. Categories: detection, scoring, trade.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.
