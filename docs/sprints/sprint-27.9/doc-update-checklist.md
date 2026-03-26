# Sprint 27.9: Doc Update Checklist

## Documents Requiring Updates

| Document | Section(s) | What Changes |
|----------|-----------|-------------|
| `docs/project-knowledge.md` | Current State (tests, sprint history), Architecture (Regime Intelligence section), Active Strategies (no change — config-only), Config Changes, Key Active Decisions, Monthly Costs (no cost change) | Add VIXDataService to architecture, update RegimeVector description (6→11 fields), add VIX calculators, update test counts, add sprint to history table, add DEC-369–37x to decisions section |
| `docs/architecture.md` | Regime Intelligence section, Data Services section | Add VIXDataService component, update RegimeClassifierV2 description (4→8 calculators), add VIX REST endpoints, update RegimeVector field list |
| `docs/decision-log.md` | New entries | DEC-369 through DEC-37x (entries generated during implementation) |
| `docs/dec-index.md` | Index table | Add new DEC entries |
| `docs/sprint-history.md` | Sprint history table | Add Sprint 27.9 row with session details, test delta, key DECs |
| `CLAUDE.md` | Deferred items section | Add any new DEF items from sprint (SINDy, VIX Landscape page, etc.) |
| `docs/roadmap.md` | Build track queue | Mark Sprint 27.9 complete, update queue position |
| `docs/risk-register.md` | New entries | RSK-NEW: yfinance reliability |

## Documents NOT Changed

| Document | Why |
|----------|-----|
| `docs/strategies/STRATEGY_*.md` | No strategy logic changes — config-only YAML updates |
| `docs/live-operations.md` | No operational procedure changes |
| `docs/pre-live-transition-checklist.md` | No paper-trading-specific config changes |
| `docs/ui/ux-feature-backlog.md` | Dashboard widget is delivered, not backlog |
| `docs/protocols/market-session-debrief.md` | No debrief procedure changes |

## Config Files Changed

| File | Change |
|------|--------|
| `config/vix_regime.yaml` | NEW — full VIX regime config |
| `config/regime.yaml` | Updated — new calculator enable flags |
| `config/strategies/*.yaml` (×7) | Updated — conservative defaults for new RegimeVector dimensions |
