# Sprint 23: Doc Update Checklist

Run doc-sync skill after all implementation sessions complete. Verify each item is addressed.

## Tier A Documents (Claude Context — Must Stay Current)

| Document | What to Update | Priority |
|----------|---------------|----------|
| `docs/project-knowledge.md` | Add Sprint 23 to sprint history table. Update "Current State" section (test counts, active sprint). Add Universe Manager to Architecture section (key components). Add UniverseManagerConfig to Config Changes. Update Build Track Queue (mark Sprint 23 complete). Reserve DEC numbers for new decisions. | HIGH |
| `CLAUDE.md` | Add Universe Manager context: what it does, how it's configured, key files. Add `argus/data/fmp_reference.py` and `argus/data/universe_manager.py` to file inventory. Note ALL_SYMBOLS Databento mode. | HIGH |
| `docs/architecture.md` | Add §3.2c Universe Manager section: FMPReferenceClient, UniverseManager, routing table, filter schema. Update §3.2b Data Flow Architecture diagram to show Universe Manager in the live trading path. Update §3.2 DataService section to note ALL_SYMBOLS mode and fast-path discard. Add UniverseFilterConfig to §3.x config section. | HIGH |

## Tier B Documents (Reference — Update When Changed)

| Document | What to Update | Priority |
|----------|---------------|----------|
| `docs/decision-log.md` | New DEC entries (reserve DEC-277+): (1) Universe Manager architecture (wraps scanner, config-gated), (2) ALL_SYMBOLS subscription approach, (3) UniverseFilterConfig schema design, (4) Cold-start indicators decision, (5) FMP batch reference data approach. Each with full rationale per template. | HIGH |
| `docs/dec-index.md` | Add index entries for all new DECs from this sprint. | HIGH |
| `docs/sprint-history.md` | Add Sprint 23 entry: session count, test delta, key decisions, date range. | MEDIUM |
| `docs/roadmap.md` | Mark Sprint 23 as ✅ COMPLETE with date and summary. Update "Current state" in §3 (Velocity Baseline). Update cost table if FMP usage changes. | MEDIUM |
| `docs/risk-register.md` | Update RSK-046 (broad-universe throughput) with empirical data from Sprint 23 paper trading. Add any new risks discovered during implementation. | MEDIUM |
| `docs/strategies/STRATEGY_ORB_BREAKOUT.md` | Add universe_filter section documenting declared filter values. | LOW |
| `docs/strategies/STRATEGY_ORB_SCALP.md` | Add universe_filter section. | LOW |
| `docs/strategies/STRATEGY_VWAP_RECLAIM.md` | Add universe_filter section. | LOW |
| `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md` | Add universe_filter section. | LOW |

## Config Files (Updated During Implementation)

| File | What Changed | Verify |
|------|-------------|--------|
| `config/system.yaml` | New `universe_manager:` section | Keys match UniverseManagerConfig fields |
| `config/strategies/orb_breakout.yaml` | New `universe_filter:` section | Keys match UniverseFilterConfig fields |
| `config/strategies/orb_scalp.yaml` | New `universe_filter:` section | Keys match UniverseFilterConfig fields |
| `config/strategies/vwap_reclaim.yaml` | New `universe_filter:` section | Keys match UniverseFilterConfig fields |
| `config/strategies/afternoon_momentum.yaml` | New `universe_filter:` section | Keys match UniverseFilterConfig fields |

## Verification

After doc-sync:
- [ ] All Tier A documents reflect Sprint 23 completion
- [ ] All new DEC entries have full rationale (no TBD fields)
- [ ] DEC index is current
- [ ] Architecture doc Data Flow diagram includes Universe Manager path
- [ ] CLAUDE.md mentions Universe Manager and new file paths
- [ ] All config YAML↔Pydantic field names verified in docs
- [ ] No stale references to "static watchlist" in updated docs (replaced with "Universe Manager" where applicable)
- [ ] Sprint roadmap shows Sprint 23 complete, Sprint 23.5 as NEXT
