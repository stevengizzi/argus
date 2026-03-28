# Sprint 28: Escalation Criteria

Escalate to Tier 3 review if any of the following conditions are observed during implementation or Tier 2 review:

## Critical (Immediate Escalation)

1. **ConfigProposalManager writes invalid YAML.** If a successful Pydantic validation is followed by a config file that the application cannot load, the validation-before-write safety contract is broken. Stop and escalate — this is a data safety issue.

2. **Config reload causes scoring regression.** If applying an approved proposal changes Quality Engine scoring behavior in ways not explained by the proposal's content (e.g., other weights shift unexpectedly, grades change for setups that weren't affected by the proposed change), the config reload mechanism has a bug. Stop and escalate.

3. **Auto post-session trigger blocks or delays shutdown.** If the asyncio timeout is not effective and the analysis prevents clean application shutdown, this is a production safety issue. Escalate.

4. **Analysis produces mathematically impossible results.** Spearman correlation outside [-1, 1], negative accuracy rates, sample counts that don't sum correctly. This indicates a fundamental computation error. Escalate.

## Significant (Escalate After 1 Failed Fix Attempt)

5. **OutcomeCollector returns mismatched data.** If trade records and counterfactual records for the same symbol/time are inconsistent in ways not explained by the different data sources (e.g., different quality scores for the same signal ID), there may be a data integrity issue.

6. **LearningStore fails to persist reports.** If SQLite writes consistently fail (not transient WAL contention), the DEC-345 separate-DB pattern may have an issue.

7. **Config change history has gaps.** If an applied change doesn't appear in the history table, the audit trail contract is broken.

8. **Frontend proposal mutations don't update UI.** If approve/dismiss clicks succeed on the API but the UI doesn't reflect the change (TanStack Query cache invalidation issue), this affects the core V1 value proposition (human-in-the-loop approval).

## Informational (Log but Don't Escalate)

9. **All recommendations are INSUFFICIENT_DATA.** Expected during early paper trading with sparse data. Log for awareness but continue.

10. **Per-regime analysis produces different recommendations than overall.** Expected — different market conditions may warrant different calibrations. This is the system working correctly.

11. **Historical_match dimension flagged as non-discriminating.** Expected — this dimension is stubbed at 50. Log for awareness.
