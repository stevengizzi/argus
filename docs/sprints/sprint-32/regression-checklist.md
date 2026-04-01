# Sprint 32: Regression Checklist

## Critical Invariants

| # | Check | How to Verify | Session |
|---|-------|---------------|---------|
| R1 | All 12 existing strategies instantiate at startup | `python -c "from argus.main import ArgusApp; ..."` or startup log inspection — all 12 strategy IDs appear | S3, S5 |
| R2 | Existing YAML configs with no detection param changes still load | Load each of the 7 pattern YAML configs through their Pydantic model — no validation errors | S1 |
| R3 | Pattern constructor default values unchanged | For each pattern: `SomePattern()` (no args) produces the same instance as before. Factory with default config produces identical behavior. | S2, S3 |
| R4 | PatternBacktester supports bull_flag, flat_top_breakout, abcd (pre-existing) | Run `_create_pattern_by_name()` (or replacement) for these 3 patterns — same behavior as before | S3 |
| R5 | PatternBacktester now also supports dip_and_rip, hod_break, gap_and_go, premarket_high_break (DEF-121 resolution) | Run factory for all 4 new patterns via backtester path | S3 |
| R6 | Shadow mode routing (Sprint 27.7) still works | Strategy with `mode: "shadow"` in config → signals route to CounterfactualTracker, not broker | S5 |
| R7 | CounterfactualTracker handles shadow signals from variants | Shadow variant generates signal → CounterfactualTracker receives SignalRejectedEvent with `rejection_stage="shadow"` | S5, S7 |
| R8 | Non-PatternModule strategies completely untouched | `git diff` shows zero changes to: `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py` | All |
| R9 | Test suite passes | Full suite: `python -m pytest tests/ -n auto -q` → 4,200+ pass, 0 fail. Vitest: `cd argus/ui && npx vitest run` → 700+ pass | All close-outs |
| R10 | Config validation rejects invalid values | Set `pole_min_bars: -5` in bull_flag.yaml → Pydantic validation error at startup | S1 |
| R11 | `experiments.enabled: false` (default) → system unchanged | With experiments disabled, startup behavior is identical to pre-sprint. No extra strategies registered, no experiment DB created, no API endpoints active. | S8 |
| R12 | Paper trading overrides (Sprint 29.5) unaffected | `daily_loss_limit_pct`, `weekly_loss_limit_pct`, `throttler_suspend_enabled`, `orb_family_mutual_exclusion` values unchanged in their respective configs | All |
| R13 | New config fields verified against Pydantic model (no silently ignored keys) | Programmatic test: for each pattern, compare YAML keys against Pydantic model_fields — zero unrecognized keys | S1, S8 |
| R14 | Parameter fingerprint is deterministic | Same config → same hash across process restarts. Verified by test. | S2 |
| R15 | trades table schema migration backward compatible | Existing trade records still queryable after `config_fingerprint` column added (NULL for historical trades) | S3 |
| R16 | Orchestrator registration API unchanged | `orchestrator.register_strategy()` accepts variant strategies with no code changes to orchestrator.py | S5 |

## Post-Sprint Verification

After all 8 sessions, before doc sync:

1. Full test suite: `python -m pytest tests/ -n auto -q` — all pass
2. Vitest: `cd argus/ui && npx vitest run` — all pass (should be unchanged)
3. Start ARGUS with `experiments.enabled: false` — normal startup, 12 strategies
4. Start ARGUS with `experiments.enabled: true` + sample variant config — 12+ strategies, variants registered
5. `git diff` against pre-sprint commit confirms no changes to protected files
