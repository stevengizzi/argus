# Sprint 27: Escalation Criteria

These conditions should trigger an immediate halt and Tier 3 review or human consultation:

## Architecture Escalations
1. **SynchronousEventBus produces different handler dispatch order than production EventBus for the same subscription set.** The SyncBus must dispatch handlers in subscription order (FIFO), matching the production bus. If ordering diverges, strategies may behave differently in backtest vs live.
2. **Bar-level fill model produces clearly incorrect results** — e.g., a trade shows profit when the bar OHLC makes profit impossible, or a stop loss is reported as triggered when the bar's low never reached the stop price. This indicates a logic error in the fill priority model.
3. **Strategy behavior differs between BacktestEngine and direct unit test invocation** — e.g., `on_candle()` returns a signal in a unit test but not when called through the engine with identical inputs. This suggests the engine is corrupting state or event routing.

## Data Escalations
4. **Databento `metadata.get_cost()` returns non-zero for OHLCV-1m on EQUS.MINI.** This would invalidate the DEC-353 assumption that historical data is free. Halt and investigate — may require reassessing Sprint 27 scope.
5. **Databento OHLCV-1m data has significant gaps** (>5% missing bars for active symbols during market hours). This affects backtest validity. Document gaps and assess whether they're concentrated in specific time periods.

## Performance Escalations
6. **BacktestEngine is slower than the Replay Harness on equivalent data.** The entire justification for the engine is speed. If synchronous dispatch doesn't deliver the expected speedup, the SyncEventBus design needs revisiting.
7. **BacktestEngine produces ≥50% more or fewer trades than Replay Harness on identical data.** Directional equivalence allows divergence, but a 50%+ gap suggests a fundamental logic error, not a fill-model difference.

## Integration Escalations
8. **Any existing walk_forward.py CLI mode produces different output after Sprint 27 changes.** The walk-forward modification must be purely additive. Any change to existing behavior is a regression.
9. **Any existing backtest test fails** — including VectorBT, Replay Harness, PatternBacktester, or data_fetcher tests. Sprint 27 modifies only config.py and walk_forward.py in existing files; all others are new. If existing tests break, something unexpected happened.

## Process Escalations
10. **Session compaction occurs before completing core deliverables.** If any session hits compaction while the session's primary deliverable is incomplete, halt and report. The design summary should be sufficient to regenerate context.
