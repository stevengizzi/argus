# Sprint 27.6: Escalation Criteria

## Tier 3 Architectural Review Triggers

Escalate to Tier 3 if any of the following occur during implementation:

1. **RegimeVector breaks MultiObjectiveResult serialization.** If adding RegimeVector as metadata to regime_results, or changing any serialization path, causes existing MultiObjectiveResult tests to fail → HALT. This touches the evaluation framework's data contract.

2. **BreadthCalculator causes measurable latency in candle processing.** If per-candle update exceeds 1ms for 5,000 symbols, the Event Bus subscription pattern may need rethinking (e.g., batch processing, separate asyncio task). This would be an architectural change.

3. **Config-gate bypass is incomplete.** If `regime_intelligence.enabled: false` still causes V2 code to execute (imports, instantiation, Event Bus subscriptions), the isolation design needs review. The gate must be absolute.

4. **RegimeClassifierV2 backward compatibility fails.** If V2.classify() produces different MarketRegime for same inputs as V1 for ANY test case → HALT. This is a fundamental contract violation.

5. **Pre-market startup time exceeds 60 seconds.** If MarketCorrelationTracker + SectorRotationAnalyzer combined add > 60s to startup, the pre-market timing needs architectural review (parallel computation, lazy loading, or pre-market phase restructuring).

6. **Circular imports between new modules.** If breadth.py / market_correlation.py / sector_rotation.py / intraday_character.py create circular import chains with regime.py, orchestrator.py, or main.py → session halt for dependency restructuring.

7. **Event Bus subscription for BreadthCalculator creates subscriber ordering issues.** If BreadthCalculator receiving candles via Event Bus interferes with strategy candle processing (ordering, timing, backpressure) → architectural review of subscriber isolation.

## Session-Level Halt Criteria

Any session should halt (not escalate) if:

- Pre-flight test suite has failures unrelated to the current session's changes
- A file listed in "Do not modify" is being changed
- Compaction risk is becoming apparent (context window pressure, losing track of changes)
- More than 2 files beyond the session's Modifies list need changes (scope creep signal)

## Cost Ceiling

$5/day default Anthropic API ceiling. No Anthropic API calls in this sprint (all computation is local or FMP/Databento). The ceiling applies only to the AI Copilot running in the background during development.
