# Sprint 27.6: Revision Rationale

> **Source:** Adversarial review conducted March 24, 2026
> **Verdict:** Outcome B — Issues found requiring spec changes
> **All revisions adopted as written.** No rejections.

---

## Critical Findings — All Adopted

| Finding | Change | Rationale |
|---------|--------|-----------|
| C1: `regime_confidence` formula undefined | Defined as `signal_clarity × data_completeness` with explicit thresholds per clarity level | Makes the metric deterministically testable. Two-factor decomposition cleanly separates "how clear is the classification?" from "how much data informed it?" |
| C2: BreadthCalculator timeframe semantics ambiguous | Renamed `breadth_score` → `universe_breadth_score`, clarified as intraday 1-min bar MA (not multi-day), added `min_bars_for_valid` ramp-up | Prevents fundamental confusion about what the metric measures. Ramp-up handling prevents meaningless scores in first ~10 minutes. |
| C3: IntradayCharacterDetector thresholds undefined | Added concrete classification rules with configurable thresholds, priority ordering, and test vectors | Makes "correct classification" testable. Priority ordering (Breakout > Reversal > Trending > Choppy) resolves overlap ambiguity. |

## Important Findings — All Adopted

| Finding | Change | Rationale |
|---------|--------|-----------|
| I1: BreadthCalculator ramp-up handling | Symbols only contribute after `min_bars_for_valid` bars; returns None until threshold met | Prevents garbage-in during early trading. 10-min blackout acceptable (ORB at 9:35+). |
| I2: "Top N by volume" ambiguous | Clarified: ranked by avg daily volume from Universe Manager reference cache | Zero additional API calls. Uses existing cached data. |
| I3: RegimeChangeEvent format unspecified | Added `regime_vector_summary: Optional[dict]` field with `RegimeVector.to_dict()` | Explicit format, backward compatible (existing consumers ignore it). ~500 bytes per event, negligible. |
| I4: V2 backward compat mechanism unclear | V2 delegates to V1 internally (holds V1 instance). Added golden-file parity test (100 days). | Delegation makes compatibility trivially provable. Golden file makes regression impossible to miss. |
| I5: V2 constructor for backtest mode | All calculator params Optional (default None). None → defaults for that dimension. | Clean backtest mode without special casing. Same constructor, different injection. |
| I6: Pre-market fetches sequential | `run_pre_market()` uses `asyncio.gather()` for correlation + sector concurrently. | ~10-15s parallel vs ~35s sequential. No reason to block. |
| I7: Cache invalidation unspecified | Cache keyed by calendar date (ET). Reuse if today, recompute if stale. Explicit schema. | Deterministic invalidation. No ambiguity about when to recompute. |

## New Deliverable — Adopted

| Item | Change | Rationale |
|------|--------|-----------|
| RegimeHistoryStore (§12) | SQLite persistence for RegimeVector snapshots in `data/regime_history.db`. 7-day retention. Fire-and-forget writes. | Sprint 28 (Learning Loop) needs regime history correlated with trade outcomes. Adding persistence now means Sprint 28 arrives with weeks of accumulated data from paper trading. Small implementation cost (~30-45 min in S6). Follows established patterns (DEC-345 evaluation.db, fire-and-forget writes). |

## Session Impact

No session count change. Persistence absorbed into S6 (13 compaction, still within bounds). Golden-file test absorbed into S8. Additional intraday config fields absorbed into S1. All sessions remain ≤ 13.

## Downstream Impact

- Sprint 28 (Learning Loop): Gets regime history from day one — can query `get_regime_at_time()` to correlate with trades.
- Sprint 27.7 (Counterfactual Engine): Can tag shadow positions with regime context.
- Sprint 34+ (micro-strategies): `RegimeOperatingConditions` schema unchanged by revisions.
