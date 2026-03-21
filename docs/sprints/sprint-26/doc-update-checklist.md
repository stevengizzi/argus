# Sprint 26: Doc Update Checklist

All document updates are performed in a doc-sync session after the sprint completes.

## Documents to Update

| # | Document | Sections to Update | What Changes |
|---|----------|--------------------|-------------|
| 1 | `docs/project-knowledge.md` | Sprint History table, Build Track Queue, Current State (tests, strategies, active sprint), Architecture (Strategies, Key Components), Active Strategies table, Active Decisions | Add Sprint 26 row, update test counts (→~2,891+~619), update strategy count (→7), add PatternModule/PatternBasedStrategy to architecture, add R2G/BullFlag/FlatTop to Active Strategies, add new DEC entries, update next sprint to 27 |
| 2 | `CLAUDE.md` | Active Sprint, Current State, Project Structure, Known Issues, DEF items | Update tests, strategy count, add patterns/ to project structure, add any new DEFs, update active sprint → 27 |
| 3 | `docs/architecture.md` | Strategy section, Key Components | Add PatternModule ABC description, PatternBasedStrategy, patterns/ package, R2G state machine overview |
| 4 | `docs/roadmap.md` | Sprint 26 section, Current State | Mark Sprint 26 complete, update current state, update strategy count |
| 5 | `docs/sprint-history.md` | Sprint table | Add Sprint 26 entry with session details, test counts, DEC range |
| 6 | `docs/decision-log.md` | Decision entries | Add DEC-357 through DEC-3XX (PatternModule ABC, PatternBasedStrategy, R2G design, Bull Flag, Flat-Top, etc.) |
| 7 | `docs/dec-index.md` | Index table | Add new DEC entries with status |
| 8 | `docs/strategies/STRATEGY_RED_TO_GREEN.md` | (new file) | Full strategy spec sheet following template |
| 9 | `docs/strategies/STRATEGY_BULL_FLAG.md` | (new file) | Pattern spec sheet |
| 10 | `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md` | (new file) | Pattern spec sheet |
| 11 | `docs/risk-register.md` | New risk entry | RSK-055: R2G reversal strategy catching-falling-knives risk |
| 12 | `docs/ui/ux-feature-backlog.md` | Pattern Library section | Mark "3 new cards" as complete, add any discovered UI improvements as backlog items |

## Strategy Spec Sheets (Created During Sprint)

These are created during implementation sessions, not doc-sync:
- `docs/strategies/STRATEGY_RED_TO_GREEN.md` — Full spec following template in STRATEGY_ORB_BREAKOUT.md. Includes: identity, description, market conditions, operating window, scanner criteria, entry criteria (state machine), exit rules, position sizing, holding duration, risk limits, performance benchmarks, backtest results (from S7), cross-strategy interaction, universe filter, version history, notes.
- `docs/strategies/STRATEGY_BULL_FLAG.md` — Pattern detection spec. Includes: identity, description, detection criteria (pole, flag, breakout), scoring formula, default entry/exit rules, backtest results (from S8), universe filter.
- `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md` — Pattern detection spec. Same structure as Bull Flag.

## Config Files (Created During Sprint)

- `config/strategies/red_to_green.yaml` — S2
- `config/strategies/bull_flag.yaml` — S5
- `config/strategies/flat_top_breakout.yaml` — S6
