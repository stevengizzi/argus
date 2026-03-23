# Sprint 21.6: Escalation Criteria

## Tier 3 Escalation Triggers

Escalate to Claude.ai for Tier 3 review if ANY of the following occur:

### During Sessions 1–2 (Execution Logging)

1. **ExecutionRecord schema conflicts with DEC-358 §5.1 spec.** If the amendment's field definitions are ambiguous or require architectural interpretation beyond what the spec states, escalate before implementing. Do not invent fields or reinterpret the spec.

2. **OrderManager fill handler changes affect order routing behavior.** If adding execution record logging requires changes to the fill routing logic (not just adding logging after the existing logic), escalate. The fire-and-forget guarantee must be absolute.

3. **Database migration breaks existing tables.** If the `CREATE TABLE IF NOT EXISTS` for `execution_records` causes schema conflicts or WAL contention with existing tables, escalate.

### During Session 3 (Validation Harness)

4. **Walk-forward `run_fixed_params_walk_forward()` does not support one or more strategies with `oos_engine="backtest_engine"`.** If any strategy type fails to run through the BacktestEngine OOS path, escalate before implementing a workaround. The walk-forward engine should handle all 7 strategies as of Sprint 27.

5. **Strategy YAML config parameters cannot be mapped to walk-forward fixed params.** If the mapping from YAML config keys to `WalkForwardConfig` fixed-param fields is ambiguous for any strategy, escalate.

### During Human Step / Session 4 (Results Analysis)

6. **More than 3 strategies produce zero trades.** One strategy with zero trades is a scanner simulation issue to investigate. More than 3 suggests a systemic data or configuration problem — escalate for architectural review.

7. **More than 3 strategies show significant divergence from provisional baselines** (Sharpe diff > 0.5 OR win rate diff > 10pp OR profit factor diff > 0.5). Widespread divergence may indicate that the provisional Alpaca-era backtests had a systematic bias. Escalate before making parameter changes.

8. **Any strategy's WFE drops below 0.1 on Databento data** (not just below 0.3). A WFE near zero suggests fundamental strategy validity concerns, not just parameter tuning. Escalate for strategic assessment.

9. **BacktestEngine produces dramatically different trade counts than VectorBT for the same strategy and date range** (>5× difference). This suggests a potential bug in BacktestEngine's strategy factory or fill model rather than a data-source difference. Escalate.

## Non-Escalation Items (Handle In-Session)

- Single strategy producing zero trades → investigate scanner params, document finding
- WFE between 0.1 and 0.3 → mark as below threshold, recommend re-optimization, continue
- Minor metric divergence within thresholds → expected, document and proceed
- Databento download timeout → retry, use existing cache if available
- Test failures in new code → fix in-session
