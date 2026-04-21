# Strategy: ABCD

**Sprint:** 29 (Sessions 6a + 6b)
**Type:** PatternModule via PatternBasedStrategy
**Family:** Harmonic
**File:** `argus/strategies/patterns/abcd.py`
**Config:** `config/strategies/abcd.yaml`
**Mode:** `shadow` (demoted Sprint 32.9; awaits parameter optimization via shadow variants and O(n³) swing-detection fix per DEF-122)
**Status:** PROVISIONAL — no backtest validation yet; pre-Databento sweeps do not satisfy DEC-132. Live promotion requires shadow-variant evidence per the Incubator Pipeline (DEC-382).

## Overview
Harmonic ABCD pattern detection. Identifies swing points (local peaks/valleys), validates Fibonacci retracement at B (38.2–61.8%) and optionally C, checks leg ratio in price and time dimensions, calculates completion zone for entry. Highest parameterization density — ideal Sprint 32 candidate.

## Operating Window
10:00 AM – 3:00 PM ET

## Detection Logic
1. Swing detection: local highs/lows with configurable lookback and ATR minimum size
2. ABCD point identification: A (swing low) → B (swing high) → C (retracement) → D (completion)
3. Fibonacci validation: BC retracement within 38.2–61.8% of AB
4. Leg ratio: CD/AB price ratio and time ratio within configurable bounds
5. Completion zone: current price within tolerance % of projected D level
6. Incomplete patterns (AB-BC without CD) return None

## Scoring (0–100)
Fibonacci precision (35) + Symmetry (25) + Volume (20) + Trend alignment (20)

## Parameters
13 PatternParams. Categories: detection, scoring, trade.

## Notes
- Internal ATR calculation when not provided via indicators dict
- O(n³) swing detection — needs optimization before Sprint 32 parameter sweeps (DEF-122)
- Score metadata (`cd_bc_volume_ratio`, `trend_aligned`) default to conservative values until enrichment added

## Exit Management
Trailing stop (ATR-based), escalation phases. Override in strategy YAML.
