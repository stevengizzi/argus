# Sprint 21.6: Doc Update Checklist

## Documents Requiring Updates After Sprint Completion

### Always Updated
- [ ] **`docs/project-knowledge.md`** — Update sprint history table (add Sprint 21.6 row with test counts, date, key DECs if any), update test counts in Current State section, update build track queue (strike through 21.6), update "Active Constraints" if DEC-132 status changes
- [ ] **`docs/sprint-history.md`** — Add Sprint 21.6 entry with full scope description, session details, and key outcomes
- [ ] **`CLAUDE.md`** — Update test counts, note DEC-132 validation status, add any new DEF items discovered

### Sprint-Specific Updates
- [ ] **`config/strategies/orb_breakout.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/orb_scalp.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/vwap_reclaim.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/afternoon_momentum.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/red_to_green.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/bull_flag.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`config/strategies/flat_top_breakout.yaml`** — `backtest_summary` section updated (Session 4)
- [ ] **`docs/decision-log.md`** — Add new DEC entries (DEC-359–361 range) if parameter changes were made or architectural decisions arose. If no new DECs, add a note under Sprint 21.6 header: "No new architectural decisions. Validation-only sprint."
- [ ] **`docs/dec-index.md`** — Add any new DEC index entries

### Conditional Updates (Only If Parameter Changes Needed)
- [ ] **`docs/strategies/STRATEGY_*.md`** — Update any strategy spec sheets whose parameters changed. Include old and new values with rationale.
- [ ] **`docs/risk-register.md`** — Add RSK entries if validation revealed new risks (e.g., strategy underperformance on Databento data)
- [ ] **`docs/roadmap.md`** — Update if validation results change the priority or scope of downstream sprints (e.g., if a strategy needs re-optimization before Learning Loop)

### Created by This Sprint
- [ ] **`docs/sprints/sprint-21.6/validation-report.md`** — Final validation comparison report (Session 4 deliverable)
- [ ] **`argus/execution/execution_record.py`** — New module (ensure docstring references DEC-358 §5.1)

### Architecture Doc
- [ ] **`docs/architecture.md`** — Add ExecutionRecord to the Order Manager section description. Mention `execution_records` table in the database schema section. This is a small additive update (1-2 sentences each location).
