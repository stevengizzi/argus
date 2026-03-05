# Sprint 22: Escalation Criteria

Trigger a Tier 3 review if ANY of the following occur:

1. **Trading safety breach**: Any code path where AI output could modify strategy signals, bypass Risk Manager gating, or alter execution without explicit human approval.

2. **Approval workflow bypass**: Any scenario where an action executes without passing through the approve endpoint and 4-condition re-check gate.

3. **File scope violation**: Any modification to files in `argus/strategies/`, `argus/core/orchestrator.py` (core logic), `argus/core/risk_manager.py` (core logic), `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, or existing API route signatures.

4. **Existing WebSocket disruption**: Any change to `/ws/v1/live` behavior or connection handling.

5. **tool_use false positive**: Claude's tool_use produces an ActionProposal that was not intentionally requested by the operator, and the validation layer fails to catch it.

6. **Memory/resource leak**: WebSocket streaming handler or Claude API client shows evidence of resource leak under sustained use (multiple conversations in a session).

7. **AI hallucination in data**: AI-generated content (daily summary, insight card, or chat response) includes fabricated trade data, positions, or P&L figures not present in the actual database.

8. **Performance degradation**: Any existing endpoint's response time increases by >50% after AI module integration, OR existing test suite runtime increases by >20%.

9. **Cost anomaly**: Token usage per conversation significantly exceeds estimates (>3x the budgeted token counts), suggesting prompt/context construction error.

10. **Graceful degradation failure**: System behavior changes in ANY way when ANTHROPIC_API_KEY is unset compared to pre-Sprint 22 baseline.

11. **Authentication gap**: Any AI endpoint (REST or WebSocket) accessible without valid JWT.

12. **Event schema conflict**: New AI events conflict with or alter behavior of existing Event Bus subscribers.
