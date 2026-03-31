# Strategy: Gap-and-Go

**Sprint:** 29 (Session 5)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Continuation
**File:** `argus/strategies/patterns/gap_and_go.py`
**Config:** `config/strategies/gap_and_go.yaml`

## Overview
Gap-up continuation pattern. Detects stocks gapping up ≥3% from prior close, validates VWAP hold, offers two entry modes (first pullback, direct breakout). First pattern to use `set_reference_data()` hook for prior close.

## Operating Window
9:35 AM – 10:30 AM ET

## Detection Logic
1. Gap calculation from prior close via `set_reference_data()` — returns None when unavailable
2. Reject gaps below min_gap_percent threshold (default 3%)
3. VWAP hold validation (falls back to first candle open as proxy when VWAP unavailable)
4. Two entry modes: `first_pullback` (dip to support then resume) or `direct_breakout` (push through opening range high)
5. Volume confirmation

## Scoring (0–100)
Gap magnitude (30) + Volume (25) + VWAP hold (25) + Entry quality (20)

## Parameters
14 PatternParams. Categories: detection, filtering, trade.

## Exit Management
Trailing stop (percent-based), escalation phases. Override in strategy YAML.
