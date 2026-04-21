# Strategy: Dip-and-Rip

**Sprint:** 29 (Session 3)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Reversal
**File:** `argus/strategies/patterns/dip_and_rip.py`
**Config:** `config/strategies/dip_and_rip.yaml`
**Mode:** `live` (base strategy); 2 shadow variants active (see below)
**Status:** PROVISIONAL — backtest evidence from 24-symbol momentum set (April 2025); universe-aware re-sweep pending (DEF-145). Shadow variants collecting CounterfactualTracker data.

## Shadow Variants (Sprint 31A sweep, deployed via `config/experiments.yaml`)

| Variant ID | Sharpe | Win Rate | Notes |
|---|---|---|---|
| `strat_dip_and_rip__v2_tight_dip_quality` | 1.996 | 45.6% | Tighter dip-quality thresholds |
| `strat_dip_and_rip__v3_strict_volume` | 2.628 | 45.0% | Stricter recovery-volume ratio |

Both variants run in shadow mode alongside the live base strategy. See
`docs/project-knowledge.md` and CLAUDE.md "Experiment Variants" for the promotion queue.

## Overview
Detects sharp intraday dips followed by rapid recovery with volume confirmation and VWAP/support level interaction. Differentiated from Red-to-Green: intraday dip only (no gap-based), dip must occur after 9:35 AM ET.

## Operating Window
9:45 AM – 11:30 AM ET

## Detection Logic
1. Scan for dip: configurable % or ATR-based decline within lookback window
2. Reject dips with low timestamp (before 9:35 AM ET)
3. Validate recovery: price recovers within max_recovery_ratio of dip duration
4. Volume confirmation: recovery volume ≥ min_recovery_volume_ratio × dip volume
5. Level interaction: proximity to VWAP or support levels

## Scoring (0–100)
Dip magnitude (30) + Recovery velocity (25) + Volume (25) + Level interaction (20)

## Parameters
10 PatternParams. Categories: detection, filtering, trade.

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.
