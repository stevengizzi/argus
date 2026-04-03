# Sprint 31A: Doc Update Checklist

## Documents to Update

### CLAUDE.md
- [ ] DEF-143: mark RESOLVED with resolution summary
- [ ] DEF-144: mark RESOLVED with resolution summary
- [ ] New DEF items logged during sprint (DEF-145+ range)
- [ ] Test counts updated (pytest → ~4,725, Vitest → 846)
- [ ] Active sprint line updated (31A → next sprint in queue)
- [ ] Strategy count updated: 15 base strategies (12 existing + 3 new)
- [ ] Experiment pipeline: variant count updated with sweep results

### docs/project-knowledge.md
- [ ] Sprint history table: add Sprint 31A row with test counts, date, key DECs
- [ ] Build track queue: mark 31A complete, advance pointer
- [ ] Active Strategies table: add rows for Micro Pullback (#13), VWAP Bounce (#14), Narrow Range Breakout (#15)
- [ ] Architecture > Key Components > Pattern Library: add descriptions of 3 new patterns
- [ ] Architecture > Key Components > PatternModule base: document `min_detection_bars` property
- [ ] Expanded Vision > Completed infrastructure: update experiment pipeline status with sweep results
- [ ] File Structure: add new pattern files to patterns/ listing
- [ ] Current State: update test counts, strategy count, variant count
- [ ] Key Learnings: add PMH lookback_bars root cause finding
- [ ] Key Learnings: add reference data wiring gap finding (PMH/GapAndGo)

### docs/sprint-history.md
- [ ] Sprint 31A entry with: goal, session list, test delta, key fixes, new patterns, sweep results
- [ ] Session-level detail: S1–S6 scopes and outcomes

### docs/roadmap.md
- [ ] Sprint 31A marked complete
- [ ] Next sprint in queue (30 or 31.5) highlighted as active

### docs/dec-index.md
- [ ] Any new DEC entries from this sprint (unlikely — all decisions follow established patterns)
- [ ] Verify no DEC number collisions

### docs/strategies/ (per-strategy spec sheets)
- [ ] Create `docs/strategies/STRATEGY_MICRO_PULLBACK.md`
- [ ] Create `docs/strategies/STRATEGY_VWAP_BOUNCE.md`
- [ ] Create `docs/strategies/STRATEGY_NARROW_RANGE_BREAKOUT.md`

### config/experiments.yaml
- [ ] Sweep results committed (this is both code and documentation — sweep results are the variant definitions)

## Documents NOT Updated (Out of Scope)
- `docs/architecture.md` — No architectural changes (patterns follow established ABC)
- `docs/risk-register.md` — No new risks identified
- `docs/live-operations.md` — No operational procedure changes
- `docs/ui/ux-feature-backlog.md` — No UI changes (strategy identity assignments deferred)
- `docs/pre-live-transition-checklist.md` — No new paper-trading overrides
