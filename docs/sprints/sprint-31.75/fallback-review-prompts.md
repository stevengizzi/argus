# Sprint 31.75 — Fallback Tier 2 Review Prompts

> Use these ONLY if the @reviewer subagent invocation fails.
> Primary path: @reviewer is invoked at the end of each implementation session.

---

## Tier 2 Review: Sprint 31.75, Session 1

### Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

**Write the review report to:**
docs/sprints/sprint-31.75/session-1-review.md

### Review Context
Read: `docs/sprints/sprint-31.75/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-31.75/session-1-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/strategies/patterns/test_gap_and_go.py tests/backtest/ tests/intelligence/experiments/test_runner.py -x -q`
- Files NOT modified: `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/core/events.py`, `argus/intelligence/experiments/store.py`, any `ui/` files

### Session-Specific Review Focus
1. GapAndGo minimum risk guard fires BEFORE PatternDetection is returned
2. DEF-153 fingerprint registration happens AFTER strategy creation in _setup()
3. _run_single_backtest passes computed fingerprint hash, not hardcoded string
4. No changes to OrderManager._close_managed_position()
5. min_risk_per_share PatternParam has min_value > 0

---

## Tier 2 Review: Sprint 31.75, Session 2

### Instructions
Same as above. **Write to:** docs/sprints/sprint-31.75/session-2-review.md

### Review Context
Read: `docs/sprints/sprint-31.75/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-31.75/session-2-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/strategies/patterns/test_vwap_bounce.py tests/strategies/patterns/test_factory.py -x -q`
- Files NOT modified: `base.py`, `pattern_strategy.py`, any other pattern file, any `ui/` files

### Session-Specific Review Focus
1. `_signal_counts` is per-instance dict, NOT class variable
2. Entry price from LAST follow-through bar, not bounce bar
3. Approach distance check uses bars BEFORE touch
4. `lookback_bars >= max(min_detection_bars)` for all valid param combos
5. `max_signals_per_symbol` defaults ≤ 5
6. Existing tests fixed by adjusting fixtures, not weakening new checks

---

## Tier 2 Review: Sprint 31.75, Session 3a

### Instructions
Same as above. **Write to:** docs/sprints/sprint-31.75/session-3a-review.md

### Review Context
Read: `docs/sprints/sprint-31.75/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-31.75/session-3a-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/data/ -x -q`
- Files NOT modified: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/store.py`, any pattern files

### Session-Specific Review Focus
1. Persistent DB check uses `duckdb_views()` system table
2. `:memory:` mode truly unchanged when persist_path is None
3. `rebuild()` drops and recreates VIEW
4. `--rebuild` exits without running sweeps
5. `.duckdb.wal` also in .gitignore
6. Consistent path handling (forward slashes / Path objects)

---

## Tier 2 Review: Sprint 31.75, Session 3b (FINAL)

### Instructions
Same as above. **Write to:** docs/sprints/sprint-31.75/session-3b-review.md

### Review Context
Read: `docs/sprints/sprint-31.75/review-context.md`

### Tier 1 Close-Out Report
Read: `docs/sprints/sprint-31.75/session-3b-closeout.md`

### Review Scope
- Diff: `git diff HEAD~1`
- Test command (FINAL — full suite): `python -m pytest tests/ -x -q -n auto`
- Files NOT modified: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/store.py`, `argus/data/historical_query_service.py`, any pattern files, `config/universe_filters/bull_flag.yaml`

### Session-Specific Review Focus
1. `resolve_sweep_symbols.py` reuses single HistoricalQueryService in --all-patterns
2. `run_sweep_batch.sh` uses `> logfile 2>&1` (no tee)
3. Batch script uses `|| continue` for error isolation
4. `bull_flag_trend.yaml` has DIFFERENT criteria from `bull_flag.yaml`
5. No frontend imports or modifications
6. `run_sweep_batch.sh` compatible with macOS bash 3.2
