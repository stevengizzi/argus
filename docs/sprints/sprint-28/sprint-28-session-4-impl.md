# Sprint 28, Session 4: ConfigProposalManager + Config Change History

**⚠️ PARALLELIZABLE with Sessions 3a→3b.** S4 creates ONLY `config_proposal_manager.py` and `config/learning_loop.yaml`. Zero file overlap with S3a/S3b. Both converge at S5.

## Pre-Flight Checks
1. Read: `argus/intelligence/learning/models.py` (S1 — LearningLoopConfig, ConfigProposal), `config/quality_engine.yaml`, `argus/intelligence/quality_engine.py` (QualityEngineConfig Pydantic model), `docs/sprints/sprint-28/sprint-28-adversarial-review-output.md` (Amendments 1, 2, 6, 9)
2. Run: `python -m pytest tests/intelligence/learning/ -x -q`
3. Verify correct branch

## Objective
Build the ConfigProposalManager that bridges UI approval to YAML config changes with full safety guardrails. Create the `config/learning_loop.yaml` config file. **Per Amendment 1: NO in-memory config reload. Changes apply at startup only.**

## Requirements

1. **Create `argus/intelligence/learning/config_proposal_manager.py`:**
   - `ConfigProposalManager` class
   - Constructor takes: `LearningLoopConfig`, `LearningStore`, `quality_engine_yaml_path` (default `config/quality_engine.yaml`)
   - **`apply_pending()` — called at application startup only (Amendment 1):**
     1. Query store for all APPROVED proposals ordered by approval timestamp
     2. Read current quality_engine.yaml
     3. Apply proposals sequentially, tracking cumulative drift per dimension
     4. **Cumulative drift guard (Amendment 2):** If applying next proposal would exceed `max_cumulative_drift` for any dimension (over rolling `cumulative_drift_window_days`), stop. Remaining proposals stay APPROVED for next cycle.
     5. Validate cumulative result through QualityEngineConfig Pydantic model
     6. If validation fails → CRITICAL log, all proposals stay APPROVED, YAML unchanged
     7. **Atomic write (Amendment 9):** Backup to `quality_engine.yaml.bak`, write to tempfile, `os.rename()` to target
     8. Update applied proposals to APPLIED status, record in config_change_history
   - **`validate_proposal(proposal) -> tuple[bool, str]`:**
     - Check `max_change_per_cycle`
     - Check weight sum-to-1.0 (with proportional redistribution of other weights)
     - If redistribution would push any weight below 0.01 → reject
     - Return (valid, explanation)
   - **`apply_single_change(field_path, new_value)` — for reverts:**
     - Read current YAML, apply single change, validate through Pydantic
     - Atomic write (backup + tempfile + rename)
     - Record in config_change_history with source="revert"
     - Takes effect on next restart
   - **`get_cumulative_drift(dimension, window_days) -> float`:**
     - Query config_change_history for changes to this dimension in window
     - Return cumulative absolute drift
   - **Startup YAML parse check:** If quality_engine.yaml fails to parse on startup, log CRITICAL and raise (application should refuse to start — Amendment 1).

2. **Create `config/learning_loop.yaml`:**
   - All 13 config fields with defaults (per Review Context File final list)
   - Comments explaining each field
   - Header noting this is Sprint 28 config

3. **Add config reload preparation to quality_engine.py:**
   - Add a class method or function that re-reads quality_engine.yaml and returns a fresh QualityEngineConfig instance. This is NOT used at runtime in V1 — it's used by `apply_pending()` for validation only, and by tests. The actual QE instance in the running application is NOT swapped.

## Constraints
- Do NOT modify `main.py`, `server.py`, or any API files (S5)
- Do NOT modify any strategy files
- Do NOT implement in-memory config reload (Amendment 1 — changes at restart only)
- ConfigProposalManager writes ONLY to `quality_engine.yaml` — no other config files

## Config Validation
Write a test that:
1. Loads `config/learning_loop.yaml`
2. Constructs LearningLoopConfig from the loaded dict
3. Asserts all 13 YAML keys are recognized by the Pydantic model
4. Asserts no silently ignored fields

## Test Targets
- `test_config_proposal_manager.py`: apply_pending happy path (single proposal), apply_pending with multiple proposals, cumulative drift guard (stops at limit), max_change_per_cycle rejection, weight sum-to-1.0 enforcement, weight below 0.01 rejection, Pydantic validation failure (YAML unchanged), atomic write (tempfile + rename), backup creation, revert via apply_single_change, YAML parse failure raises, config validation test
- Minimum: 12 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] ConfigProposalManager with apply_pending() for startup-only application
- [ ] Cumulative drift guard (Amendment 2)
- [ ] Atomic write: backup + tempfile + os.rename (Amendment 9)
- [ ] YAML parse failure → CRITICAL + raise (Amendment 1)
- [ ] No in-memory config reload (Amendment 1)
- [ ] config/learning_loop.yaml created with all 13 fields
- [ ] Config validation test passing
- [ ] ≥12 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-4-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify NO in-memory config reload exists (Amendment 1)
2. Verify atomic write pattern: backup → tempfile → os.rename (not direct write)
3. Verify cumulative drift guard queries change history correctly
4. Verify weight redistribution maintains sum-to-1.0
5. Verify YAML parse failure raises exception (not silent fallback)
6. Verify config/learning_loop.yaml has all 13 fields matching LearningLoopConfig model

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
