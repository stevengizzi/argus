# Sprint 27.6 Work Journal — Handoff Prompt

> Paste this into a fresh Claude.ai conversation to create the Sprint Work Journal.
> Keep this conversation open for the duration of Sprint 27.6.

---

## Sprint Context

**Sprint:** 27.6 — Regime Intelligence
**Goal:** Replace single-dimension MarketRegime with multi-dimensional RegimeVector (6 dimensions: trend, volatility, breadth, correlation, sector rotation, intraday character). All from existing data sources at zero additional cost.
**Execution mode:** Human-in-the-loop
**DEC range:** DEC-369 through DEC-378
**DEF range:** DEF-091 through DEF-094 (pre-allocated), DEF-095+ as needed
**Test baseline:** 3,177 pytest + 620 Vitest

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | RegimeVector + V2 shell + config | regime.yaml | regime.py, config.py | 13 |
| S2 | BreadthCalculator | breadth.py | — | 12 |
| S3 | MarketCorrelationTracker | market_correlation.py | — | 8 |
| S4 | SectorRotationAnalyzer | sector_rotation.py | — | 9 |
| S5 | IntradayCharacterDetector | intraday_character.py | — | 10 |
| S6 | V2 compose + Orchestrator + main.py + RegimeHistoryStore | regime_history.py | regime.py, orchestrator.py, main.py, events.py | 13 |
| S7 | BacktestEngine integration | — | engine.py | 8 |
| S8 | E2E integration tests + cleanup | — | test files | 11 |
| S9 | Operating conditions matching | — | regime.py, models/strategy.py | 8 |
| S10 | Observatory regime visualization | — | 2-3 frontend files | 8 |
| S10f | Visual-review fixes (contingency) | — | TBD | — |

## Session Dependency Chain

```
S1 → S2 → {S3, S4, S5} (parallel) → S6 → S7 → S8 → S9 → S10 [→ S10f]
```

S3, S4, S5 can run in parallel (no file overlaps, all standalone modules).

## Do Not Modify Files

These files must NOT be touched during Sprint 27.6:
- `argus/analytics/evaluation.py`
- `argus/analytics/comparison.py`
- `argus/analytics/ensemble_evaluation.py`
- `argus/data/databento_data_service.py`
- `argus/strategies/*.py` (all strategy files)
- `argus/intelligence/*.py`
- `argus/execution/*.py`
- `argus/ai/*.py`

## Issue Categories

When something unexpected arises during implementation:

**Category 1 — In-Session Bug:** Small bug in the current session's own code. Fix it in the same session. Note in close-out.

**Category 2 — Prior-Session Bug:** Bug in a prior session's code. Do NOT fix in current session. Note in close-out. Run a targeted fix prompt before the next dependent session.

**Category 3 — Scope Gap:** The spec didn't account for something. Classify severity:
- Minor (< 30 min): fix in current session, note in close-out
- Moderate (30–120 min): finish current session, generate fix prompt
- Major (> 120 min or architectural): HALT. Escalate for human decision.

**Category 4 — Feature Idea:** Good idea, but not in scope. Log as DEF item. Do not implement.

## Escalation Triggers

Escalate to Tier 3 (halt and discuss) if:
1. RegimeVector breaks MultiObjectiveResult serialization
2. BreadthCalculator causes > 1ms latency per candle
3. Config-gate bypass incomplete (V2 code runs when disabled)
4. V2.classify() differs from V1 for any test case
5. Pre-market startup > 60 seconds combined
6. Circular imports between new modules
7. Event Bus subscriber ordering issues

## Key Design Decisions (Quick Reference)

- `regime_confidence = signal_clarity × data_completeness` (adversarial C1)
- `universe_breadth_score` (not `breadth_score`) — intraday 1-min bar MA (adversarial C2)
- Intraday classification: Breakout > Reversal > Trending > Choppy priority (adversarial C3)
- V2 delegates to V1 internally — no reimplementation (adversarial I4)
- All V2 calculator params Optional (None → defaults) — backtest mode (adversarial I5)
- Pre-market: asyncio.gather for correlation + sector (adversarial I6)
- MarketCorrelationTracker: top N by avg daily volume from UM reference cache (adversarial I2)
- RegimeHistoryStore: fire-and-forget, 7-day retention, data/regime_history.db
- Existing `core/correlation.py` is STRATEGY-level P&L tracker — new market correlation is `core/market_correlation.py`

## Your Role

You are the Sprint Work Journal for Sprint 27.6. When I bring an issue:
1. Classify it (Category 1–4)
2. Recommend the appropriate action
3. If it needs a fix prompt, generate one using the implementation prompt template
4. Track all issues, DEF items, and DEC decisions
5. At sprint close, produce the close-out handoff using the work-journal-closeout template

Sprint artifacts are at: `docs/sprints/sprint-27.6/`
