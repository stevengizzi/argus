# Sprint 23.5: Escalation Criteria

These criteria trigger a Tier 3 architectural review or runner HALT. They are embedded in every implementation prompt and review prompt.

## Automatic ESCALATE (Tier 2 reviewer must escalate)

1. **Do-not-modify boundary violation:** Any modification to files in the protected list: `argus/ai/*`, `argus/strategies/*`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/*`, `argus/data/universe_manager.py`, `argus/data/fmp_scanner.py`, `argus/data/fmp_reference.py`, `argus/data/databento_data_service.py`, `argus/analytics/*`.

2. **Event Bus subscriber added:** CatalystEvent is defined and published in this sprint, but NO component should subscribe to it. If any subscriber registration for CatalystEvent is found, ESCALATE — the Quality Engine (Sprint 24) is the intended first subscriber.

3. **Strategy behavior change detected:** Any change to strategy signal generation, entry/exit logic, or Risk Manager approval flow. The catalyst pipeline must be completely decoupled from the trading execution path.

4. **Existing test regression:** Any of the 2,101 existing pytest or 392 existing Vitest tests fail.

5. **Storage schema conflict:** New SQLite tables (`catalyst_events`, `intelligence_briefs`) conflict with or alter existing AI layer tables (`ai_conversations`, `ai_messages`, `ai_proposals`, `ai_usage`).

6. **Config namespace collision:** New `catalyst.*` config fields collide with or alter existing config namespaces (`ai.*`, `universe_manager.*`, `api.*`).

## Conditional ESCALATE (Tier 2 reviewer uses judgment)

7. **Classification quality concern:** If test fixtures show Claude API classifier producing >30% "other" category on a diverse sample of ≥20 headlines, the classification prompt may need revision. ESCALATE if the implementer attempted a prompt fix without logging the change.

8. **Cost modeling mismatch:** If estimated per-classification cost in tests exceeds $0.10 per batch (20 headlines), the cost model may be wrong. ESCALATE for cost review.

9. **Test count below target:** If total new tests fall below 50 (target ~68), the sprint may have coverage gaps. CONCERNS if 40–50, ESCALATE if below 40.

10. **Session compaction without auto-split:** If a session compacts and the runner does not auto-split (or auto-split fails), HALT for manual intervention.

11. **SEC EDGAR User-Agent non-compliance:** SEC requires a specific User-Agent header format with contact email. If the SEC EDGAR client does not include this header, ESCALATE — SEC may block the IP.

12. **Graceful degradation failure:** If disabling any single data source (SEC EDGAR, FMP, Finnhub) or unsetting any API key causes the pipeline to crash rather than degrade gracefully, ESCALATE.

## Runner HALT Conditions

13. **Live API calls in tests:** Any test making actual HTTP requests to SEC EDGAR, FMP, Finnhub, or Claude API endpoints. All external calls must be mocked.

14. **Two consecutive session failures:** If two sessions in a row produce CONCERNS or ESCALATE verdicts, HALT for human review.

15. **Auto-split produces session scoring 14+:** If an auto-split sub-session still scores 14+ on compaction risk, HALT — the decomposition was insufficient.
