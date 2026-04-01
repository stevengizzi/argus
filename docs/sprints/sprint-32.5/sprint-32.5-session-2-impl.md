# Sprint 32.5, Session 2: DEF-132 Spawner + Runner Grid Expansion

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/spawner.py`
   - `argus/intelligence/experiments/runner.py`
   - `argus/intelligence/experiments/config.py` (updated in S1 — ExitSweepParam, VariantDefinition.exit_overrides)
   - `argus/strategies/patterns/factory.py` (updated in S1 — expanded fingerprint)
   - `argus/core/config.py` (ExitManagementConfig — read-only reference)
   - `config/exit_management.yaml` (read-only reference)
2. Run the scoped test baseline (DEC-328 — Session 2+):
   ```
   cd /Users/stevengizzi/argus && python -m pytest tests/intelligence/experiments/ -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on branch: `main` (S1 merged)
4. Create working branch: `git checkout -b sprint-32.5-session-2`

## Objective
Wire the exit_overrides data model into the spawner and runner so that variants can be spawned with exit overrides applied and experiment grids can include exit parameter dimensions.

## Requirements

1. **In `argus/intelligence/experiments/spawner.py`:**
   - In `_apply_variant_params()` (or equivalent method that configures a spawned strategy): when `variant_definition.exit_overrides` is non-None, apply the overrides into the strategy's exit config via the existing `strategy_exit_overrides` deep merge path (Sprint 28.5 infrastructure)
   - Use the existing `deep_update()` utility from `core/config.py` (or wherever it lives — find it)
   - When computing fingerprint for deduplication, pass `exit_overrides` to `compute_parameter_fingerprint()`
   - Ensure the spawner registers the expanded fingerprint with Orchestrator

2. **In `argus/intelligence/experiments/runner.py`:**
   - Expand `generate_parameter_grid()` to optionally include exit sweep dimensions from `ExperimentConfig.exit_sweep_params`
   - Each `ExitSweepParam` defines a dot-path (e.g., `"trailing_stop.atr_multiplier"`), min, max, step
   - Generate the cross-product of detection params × exit params
   - Each grid point becomes a dict with `{"detection_params": {...}, "exit_overrides": {...}}`
   - When exit_sweep_params is None or empty, grid generation is identical to current behavior (detection-only)
   - When running each grid point, pass exit_overrides to variant construction

## Constraints
- Do NOT modify: `core/config.py`, `core/exit_math.py`, `core/events.py`, any strategy files, `counterfactual.py`
- Do NOT change: the deep_update() function behavior — use it as-is
- Do NOT change: the existing grid generation for detection params — extend it additively
- Do NOT change: existing spawner behavior when exit_overrides is None

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **Spawner exit override apply:** spawn variant with exit_overrides → verify strategy config has overrides applied
  2. **Deep merge precedence:** exit_overrides applied via deep_update() produce expected merged config
  3. **Grid with exit dims:** ExperimentConfig with exit_sweep_params → grid includes exit dimension cross-product
  4. **Grid without exit dims:** ExperimentConfig without exit_sweep_params → grid identical to current
  5. **Combined grid size:** detection grid (N points) × exit grid (M points) = N×M total grid points
  6. **Integration spawn+fingerprint:** spawned variant with exit_overrides has expanded fingerprint
  7. **Integration run+exit grid:** runner with exit_sweep_params produces results for each grid point
  8. **Exit override conflict:** exit_overrides that overlap with existing strategy config → deep_update() last-write-wins (verify, not prevent)
- Minimum new test count: 8
- Test command (scoped): `python -m pytest tests/intelligence/experiments/ -x -q`

## Definition of Done
- [ ] Spawner applies exit_overrides via deep merge
- [ ] Spawner uses expanded fingerprint
- [ ] Runner grid includes exit dimensions when configured
- [ ] Grid is detection-only when exit_sweep_params absent
- [ ] Cross-product grid size correct
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Spawner without exit_overrides unchanged | Spawn variant with exit_overrides=None, verify identical behavior |
| Grid without exit_sweep_params unchanged | Generate grid with no exit params, compare to pre-change output |
| Fingerprint dedup still works | Spawn duplicate detection-only variant, verify dedup |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to:**
docs/sprints/sprint-32.5/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-32.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-32.5/session-2-closeout.md`
3. The diff range: `git diff main...HEAD`
4. The test command (scoped): `python -m pytest tests/intelligence/experiments/ -x -q`
5. Files that should NOT have been modified: `core/events.py`, `core/config.py`, `core/exit_math.py`, `execution/order_manager.py`, `intelligence/counterfactual.py`, any strategy files

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix findings, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify spawner uses deep_update() correctly (not custom merge logic)
2. Verify grid cross-product math: N detection × M exit = N×M points
3. Verify exit_overrides=None path is truly identical to pre-change spawner behavior
4. Verify fingerprint passed to Orchestrator registration includes exit_overrides
5. Verify ExitSweepParam dot-path resolution is tested (e.g., "trailing_stop.atr_multiplier" → nested dict)

## Sprint-Level Regression Checklist (for @reviewer)

### Fingerprint Backward Compatibility
- [ ] compute_parameter_fingerprint() with exit_overrides=None → identical hash
- [ ] Different exit_overrides → different fingerprints
- [ ] Deterministic hashing

### Config Backward Compatibility
- [ ] experiments.yaml without exit fields loads
- [ ] ExperimentConfig extra="forbid" rejects unknown keys

### BacktestEngine Existing Patterns
- [ ] bull_flag and flat_top_breakout unchanged

### Config Gating
- [ ] experiments.enabled=false → features disabled

### Test Suite Health
- [ ] All pre-existing pytest pass
- [ ] All pre-existing Vitest pass

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. Fingerprint backward incompatibility
2. ExperimentConfig extra="forbid" conflict
3. BacktestEngine reference data requires architectural changes
4. Trade Log tab breaks existing page
5. 9th page navigation breaks shortcuts

### Scope Reduction Triggers
1. CounterfactualStore query >2s → pagination
2. ABCD backtest >5 min → document limitation
