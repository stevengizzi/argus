# Sprint 31.75 — Sweep Infrastructure Hardening

## Review Context File

> Shared context for all Tier 2 reviews in Sprint 31.75.
> This file is referenced by each session's review prompt.

---

## Sprint Spec (Summary)

**Sprint 31.75** fixes three data-corrupting bugs (DEF-152, DEF-153, DEF-154),
adds DuckDB persistence for fast symbol resolution, and delivers the tooling
needed for reliable overnight full-universe parameter sweeps.

### Sessions

| Session | Scope | Key Deliverables |
|---------|-------|-----------------|
| S1 | DEF-152 + DEF-153 bug fixes | GapAndGo min risk guard, BacktestEngine fingerprint wiring |
| S2 | DEF-154 VWAP Bounce rework | Signal density controls, approach/bounce quality params |
| S3a | DuckDB persistence | Persistent DB mode on HistoricalQueryService, config changes |
| S3b | Sweep tooling scripts | resolve_sweep_symbols.py, run_sweep_batch.sh, bull_flag_trend.yaml |
| S4 | Full-universe sweeps | Operational — overnight compute (no code) |
| S5 | Analysis + promotions | sweep_summary_final.md, experiments.yaml updates |

### Invariants

1. All existing 4,858 pytest + 846 Vitest tests must pass after every session.
2. Live trading pipeline (OrderManager fingerprint registry, signal processing,
   exit management) must not be modified.
3. `:memory:` DuckDB mode must remain functional (backward compatible).
4. No frontend changes.
5. No changes to non-PatternModule strategies (ORB, VWAP Reclaim, AfMo, R2G).
6. PatternModule ABC interface (`detect()`, `score()`, `get_default_params()`)
   must not change signature.
7. `ExperimentStore` schema must not change (DEF-151 already fixed).
8. `run_experiment.py` CLI must remain backward-compatible (all existing flags
   continue to work identically).

---

## Specification by Contradiction

### What This Sprint Is NOT

1. **NOT a pattern detection rework.** S2 (VWAP Bounce) adds signal density
   controls but does not redesign the detection algorithm. The approach→touch→bounce
   sequence remains the core logic.

2. **NOT a fingerprint schema change.** DEF-153 wires the *existing* fingerprint
   through the *existing* OrderManager registry. No new columns, no schema
   migration, no new models.

3. **NOT a full-universe sweep sprint.** S4 is operational work using the tools
   built in S1–S3. If S4 reveals new bugs, those are tracked as new DEFs, not
   fixed in this sprint.

4. **NOT a Research Console sprint.** DuckDB persistence (S3a) is a prerequisite
   for Sprint 31B but does not include any REST endpoints, frontend pages, or
   interactive query features.

5. **NOT a live pipeline change.** The BacktestEngine fingerprint fix (DEF-153)
   explicitly avoids touching the live `_process_signal()` path. The fix works
   through the *same* OrderManager registry the live path uses, but the
   registration call is only added in BacktestEngine setup.

### Boundary Conditions

- If GapAndGo's min risk guard filters out >50% of previously-passing signals
  on the default params, the threshold is too aggressive. Target: <10% of
  default-param signals filtered.
- If VWAP Bounce rework produces <0.1 or >5 signals/symbol/day on the test
  universe, the parameters need re-tuning. Target: 0.5–3 signals/symbol/day.
- If DuckDB persistent mode is >2x slower than `:memory:` on subsequent opens,
  the implementation needs a cache warming step. Target: <5s cold open of
  persisted DB.

---

## Sprint-Level Regression Checklist

| # | Invariant | How to Verify |
|---|-----------|---------------|
| 1 | Full pytest suite passes | `python -m pytest tests/ -x -q -n auto` |
| 2 | Full Vitest suite passes | `cd ui && npx vitest run --reporter=verbose 2>&1 \| tail -20` |
| 3 | GapAndGo default params still produce detections | Run existing `test_gap_and_go.py` — detection tests must pass |
| 4 | VWAP Bounce default params produce detections | Run existing `test_vwap_bounce.py` — detection tests must pass |
| 5 | BacktestEngine runs complete without error | Run `test_runner.py` — BacktestEngine integration paths pass |
| 6 | ExperimentStore reads/writes work | Run `test_store.py` — all CRUD operations pass |
| 7 | `run_experiment.py --dry-run` works | `python scripts/run_experiment.py --pattern bull_flag --dry-run` exits 0 |
| 8 | HistoricalQueryService `:memory:` mode works | Run historical query tests — existing tests pass unchanged |
| 9 | Pattern factory builds all 10 patterns | Run `test_factory.py` — all pattern construction tests pass |
| 10 | PatternParam cross-validation passes | Run existing cross-validation tests in pattern test files |

---

## Sprint-Level Escalation Criteria

Escalate to Tier 3 (human review required) if ANY of:

1. **Live pipeline modification:** Any change to `_process_signal()` in `main.py`,
   `OrderManager._handle_entry_fill()`, `OrderManager._close_managed_position()`,
   or the `_fingerprint_registry` lookup in the live close path (line ~2612).
2. **Schema change:** Any modification to SQLite table schemas in `trade_logger.py`,
   `experiment_store.py`, or any `*_store.py` file.
3. **PatternModule ABC change:** Any modification to the abstract interface in
   `argus/strategies/patterns/base.py` (method signatures, new abstract methods).
4. **Config model backward incompatibility:** Any Pydantic model change that would
   reject existing YAML configs (removed fields, tightened validators).
5. **Test count regression:** Net test count decreases from 4,858 pytest + 846 Vitest.
6. **Cross-session file conflict:** A session modifies a file listed in another
   session's "Do NOT modify" constraint.
