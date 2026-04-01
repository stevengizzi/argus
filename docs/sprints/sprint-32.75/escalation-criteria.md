# Sprint 32.75: Escalation Criteria

## Tier 3 Escalation Triggers

1. **Arena chart performance unacceptable.** If 30 simultaneous TradingView Lightweight Charts instances produce >200ms frame times in Chrome on a standard desktop, the grid approach may need architectural rethinking (virtual scrolling, canvas-based rendering, or a fundamentally different visualization). Escalate before attempting performance micro-optimizations.

2. **TradingView LC `update()` API inadequate for live candle formation.** If the library's `update()` method for modifying the current candle produces visual artifacts, flickering, or requires workarounds that compromise code quality, escalate to evaluate alternative chart libraries (e.g., direct canvas rendering, D3-based custom charts).

3. **Arena WebSocket message volume causes backend event loop pressure.** If the Arena WS handler's event bus subscriptions (PositionUpdatedEvent for every open position, CandleEvent for every symbol) measurably degrade the main trading pipeline's event delivery latency, escalate. The Arena must never impact trading operations.

4. **Post-reconnect delay causes position state corruption.** If the 3-second delay or retry logic interferes with broker-confirmed position tracking (DEC-369), position open flows, or EOD flatten timing, revert the change immediately and escalate.

5. **Orchestrator P&L fix reveals deeper trade-to-strategy attribution gap.** If querying trade_logger per strategy reveals that trade records don't reliably carry strategy_id (e.g., null or incorrect attribution), this indicates a systemic data integrity issue that may require Order Manager changes beyond sprint scope.

## Session-Level Halt Conditions

- Any session producing >5 test failures in pre-existing tests → halt, investigate regression
- Any session that cannot complete within its compaction risk budget → halt at first sign of compaction, close out partial work
- S11 (Arena Live Data) scoring 17.5: if mid-session the implementer judges that requestAnimationFrame batching AND stats bar live updates cannot both fit without compaction, defer stats bar live updates to S12 and close out
