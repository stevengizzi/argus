# Sprint 27 — Work Journal Handoff

> Paste this into a fresh Claude.ai conversation to create the Sprint 27 Work Journal.
> Open this conversation BEFORE starting Session 1 and bring issues to it throughout the sprint.

---

## Sprint Context

**Sprint 27: BacktestEngine Core**
**Goal:** Build a production-code backtesting engine running real ARGUS strategy code against Databento OHLCV-1m historical data via synchronous event dispatch. ≥5x speed over Replay Harness. Backend only, no UI.

**Execution Mode:** Human-in-the-loop
**Estimated sessions:** 6
**Test baseline:** 2,925 pytest + 620 Vitest
**Expected new tests:** ~80

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | SyncEventBus + BacktestEngineConfig | `sync_event_bus.py` | `config.py` | 11.5 |
| S2 | HistoricalDataFeed | `historical_data_feed.py` | — | 13 |
| S3 | Engine setup + strategy factory | `engine.py` (partial) | — | 14 |
| S4 | Bar loop + fill model | — | `engine.py` | 11.5 |
| S5 | Multi-day + results + CLI | — | `engine.py` | 11.5 |
| S6 | Walk-forward integration + equiv | — | `walk_forward.py` | 10.5 |

## Session Dependency Chain

```
S1 (SyncBus + Config) ──┐
                         ├──→ S3 (Engine setup) → S4 (Bar loop) → S5 (Multi-day + CLI) → S6 (WF + equiv)
S2 (HistoricalDataFeed) ─┘
```

S1 and S2 are parallelizable. S3–S6 are strictly sequential.

## Do Not Modify

These files must remain unchanged throughout Sprint 27:
- `argus/core/event_bus.py`
- `argus/backtest/replay_harness.py`
- `argus/backtest/backtest_data_service.py`
- `argus/backtest/vectorbt_*.py`
- `argus/backtest/tick_synthesizer.py`
- All files in `argus/strategies/`, `argus/ui/`, `argus/api/`, `argus/ai/`, `argus/intelligence/`
- `config/system.yaml`, `config/system_live.yaml`

## Issue Category Definitions

When issues are reported, classify them as:

1. **In-session bug:** Bug introduced and discovered within the same session. Fix in-session. No DEF entry needed.
2. **Prior-session bug:** Bug from a previous session discovered in the current session. If it blocks current work, fix now and log. If non-blocking, create DEF entry.
3. **Scope gap:** Something the sprint spec should have covered but didn't. Evaluate: is it blocking? If yes, fix and document. If no, create DEF entry.
4. **Feature idea:** Something valuable but not in scope. Always DEF entry. Never implement during this sprint.

## Escalation Triggers

Halt and escalate if any of these occur:
1. SyncEventBus handler dispatch order differs from production EventBus
2. Bar-level fill model produces clearly incorrect results
3. Strategy behavior differs in BacktestEngine vs direct unit test
4. Databento `metadata.get_cost()` returns non-zero for OHLCV-1m
5. BacktestEngine slower than Replay Harness
6. ≥50% trade count divergence from Replay Harness on identical data
7. Any existing walk_forward.py CLI mode changes output
8. Any existing backtest test fails
9. Session compaction before core deliverables complete

## Reserved Numbers

- **DEC range:** DEC-357 through DEC-365
- **DEF range:** DEF-089 (already assigned: in-memory ResultsCollector for Sprint 32), DEF-090+

## Work Journal Responsibilities

As the Sprint 27 Work Journal, you:
1. Track session progress (which sessions are complete, test counts)
2. Classify and track issues using the categories above
3. Assign DEF/DEC numbers from the reserved ranges
4. Maintain a running log of decisions and deferred items
5. At sprint close, produce the filled-in doc-sync prompt with all close-out data embedded

## Adversarial Review Items (Already Incorporated)

These were identified during planning and already incorporated into the sprint spec:
- **AR-1:** Engine/fill model metadata recorded in output (S5)
- **AR-2:** Bar-level fill model limitation for scalping strategies documented (S5)
- **AR-3:** Fail-closed on cost validation failure, with bypass flag (S2)
- **AR-4:** `oos_engine` field in WindowResult and WalkForwardResult (S6)
