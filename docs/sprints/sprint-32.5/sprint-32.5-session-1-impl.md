# Sprint 32.5, Session 1: DEF-132 Data Model + Fingerprint Expansion

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/config.py`
   - `argus/strategies/patterns/factory.py` (focus on `compute_parameter_fingerprint()`)
   - `argus/intelligence/experiments/store.py`
   - `argus/core/config.py` (ExitManagementConfig, TrailingStopConfig, ExitEscalationConfig — read-only reference)
   - `config/exit_management.yaml` (read-only reference for exit param structure)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   cd /Users/stevengizzi/argus && python -m pytest -x -n auto -q 2>&1 | tee /tmp/s1-preflight.txt
   cd /Users/stevengizzi/argus/argus/ui && npx vitest run 2>&1 | tee /tmp/s1-preflight-vitest.txt
   ```
   Expected: ~4,405 pytest passing, ~700 Vitest (1 pre-existing failure in GoalTracker.test.tsx)
3. Verify you are on branch: `main`
4. Create working branch: `git checkout -b sprint-32.5-session-1`

## Objective
Expand the experiment pipeline's variant definition to include exit management parameters, and expand the parameter fingerprint to include exit params so that two variants differing only in exit configuration receive distinct fingerprints.

## Requirements

1. **In `argus/intelligence/experiments/config.py`:**
   - Add `ExitSweepParam` Pydantic model: `name: str`, `path: str` (dot-delimited config path, e.g. `"trailing_stop.atr_multiplier"`), `min_value: float`, `max_value: float`, `step: float`
   - Add `exit_overrides: dict[str, Any] | None = None` field to `VariantDefinition`
   - Add `exit_sweep_params: list[ExitSweepParam] | None = None` field to `ExperimentConfig`
   - Maintain `extra="forbid"` on `ExperimentConfig` — verify the new fields don't conflict

2. **In `argus/strategies/patterns/factory.py`:**
   - Expand `compute_parameter_fingerprint()` signature to accept optional `exit_overrides: dict[str, Any] | None = None`
   - When `exit_overrides` is None or empty dict: produce **identical hash** to current implementation (backward compat). This means: if no exit overrides, hash only the detection params as today.
   - When `exit_overrides` is non-empty: produce namespaced canonical JSON `{"detection": {sorted detection params}, "exit": {sorted exit overrides}}` and SHA-256 hash it. Use `json.dumps(obj, sort_keys=True, separators=(',', ':'))` for canonical form.
   - CRITICAL: capture the golden hash of at least one known detection-only input BEFORE making changes (canary test), and verify it is unchanged after.

3. **In `argus/intelligence/experiments/store.py`:**
   - Add `exit_overrides TEXT` column to `variant_definitions` table (nullable, stores JSON-serialized dict)
   - Handle schema migration: if column doesn't exist on startup, add it (ALTER TABLE pattern used elsewhere in the codebase)
   - Serialize/deserialize exit_overrides via `json.dumps`/`json.loads` in save/load methods

## Constraints
- Do NOT modify: `core/config.py`, `core/exit_math.py`, `core/events.py`, any strategy files
- Do NOT change: the existing `compute_parameter_fingerprint()` behavior for detection-only variants
- Do NOT change: ExperimentConfig `extra="forbid"` setting
- Do NOT modify: the write path or subscription logic in counterfactual.py

## Canary Tests
Before making changes, capture golden hashes:
- Call `compute_parameter_fingerprint()` with a known set of detection params (e.g., BullFlag defaults) and record the exact hash string
- After changes, verify this exact hash is unchanged

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **Golden hash backward compat:** known detection params → known fingerprint (pre-computed)
  2. **Fingerprint with exit_overrides:** detection + exit_overrides → different hash than detection-only
  3. **Empty exit equals no exit:** `exit_overrides={}` produces same hash as `exit_overrides=None`
  4. **VariantDefinition serialization:** roundtrip VariantDefinition with exit_overrides through JSON
  5. **ExitSweepParam validation:** valid and invalid ExitSweepParam constructions
  6. **Store schema migration:** variant with exit_overrides saved and loaded correctly
- Minimum new test count: 6
- Test command (scoped): `python -m pytest tests/intelligence/experiments/ -x -q`

## Config Validation
Write a test that verifies ExperimentConfig accepts `exit_sweep_params` field:
1. Construct ExperimentConfig with `exit_sweep_params=[ExitSweepParam(...)]`
2. Verify it doesn't raise ValidationError
3. Construct ExperimentConfig without `exit_sweep_params`
4. Verify it defaults to None
5. Construct ExperimentConfig with an unrecognized key → verify ValidationError (extra="forbid" check)

## Definition of Done
- [ ] ExitSweepParam model defined
- [ ] VariantDefinition has exit_overrides field
- [ ] ExperimentConfig has exit_sweep_params field
- [ ] Fingerprint backward compatible (golden hash unchanged)
- [ ] Fingerprint expanded for exit overrides
- [ ] ExperimentStore handles exit_overrides column
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Golden hash unchanged | Canary test with pre-computed hash |
| ExperimentConfig extra="forbid" still works | Test with unrecognized key → ValidationError |
| experiments.yaml loads without exit fields | Load existing config file, no errors |
| Existing experiment store data loads | Query existing variant_definitions, no errors |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-32.5/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-32.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-32.5/session-1-closeout.md`
3. The diff range: `git diff main...HEAD`
4. The test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/strategies/patterns/ -x -q`
5. Files that should NOT have been modified: `core/events.py`, `core/regime.py`, `execution/order_manager.py`, `intelligence/counterfactual.py`, any strategy files under `strategies/` (except `patterns/factory.py`), `core/exit_math.py`, `core/config.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this session,
update both the close-out and review files per the post-review fix documentation
protocol in the implementation prompt template.

## Session-Specific Review Focus (for @reviewer)
1. Verify `compute_parameter_fingerprint()` with `exit_overrides=None` produces byte-identical hash to the pre-expansion function
2. Verify `exit_overrides={}` is treated identically to `exit_overrides=None` (not as a non-empty dict)
3. Verify the canonical JSON uses `sort_keys=True` and compact separators for deterministic hashing
4. Verify ExperimentStore schema migration handles both fresh DB and existing DB with data
5. Verify `extra="forbid"` is preserved on ExperimentConfig

## Sprint-Level Regression Checklist (for @reviewer)

### Fingerprint Backward Compatibility
- [ ] compute_parameter_fingerprint() with exit_overrides=None → identical hash to pre-expansion
- [ ] exit_overrides={} → identical hash to exit_overrides=None
- [ ] Different exit_overrides → different fingerprints
- [ ] Deterministic: same inputs → same hash regardless of dict ordering

### Config Backward Compatibility
- [ ] experiments.yaml without exit_overrides loads without error
- [ ] experiments.yaml without exit_sweep_params loads without error
- [ ] ExperimentConfig extra="forbid" still rejects unknown keys
- [ ] New config fields verified against Pydantic model
- [ ] Existing variant definitions in experiments.db load

### BacktestEngine Existing Patterns
- [ ] bull_flag backtest identical before/after
- [ ] flat_top_breakout backtest identical before/after

### Config Gating
- [ ] experiments.enabled=false → experiment endpoints return 503
- [ ] experiments.enabled=false → spawner/evaluator skip

### REST API Compatibility
- [ ] All 4 existing experiment endpoints unchanged
- [ ] Counterfactual accuracy endpoint unchanged

### Test Suite Health
- [ ] All pre-existing pytest pass (4,405 baseline)
- [ ] All pre-existing Vitest pass (700 baseline, 1 known failure)

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. Fingerprint backward incompatibility (golden hash test fails)
2. ExperimentConfig extra="forbid" conflict with exit_overrides
3. BacktestEngine reference data requires changes beyond backtest_engine.py
4. Trade Log tab breaks existing page architecture
5. 9th page navigation breaks keyboard shortcut scheme

### Scope Reduction Triggers
1. CounterfactualStore query >2s on 90-day data → add pagination
2. ABCD backtest >5 min for single-symbol/month → document limitation
