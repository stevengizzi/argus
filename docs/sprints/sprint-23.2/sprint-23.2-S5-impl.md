# Sprint 23.2, Session 5: Triage + Conformance + Cost

## Pre-Flight Checks
1. Read: `scripts/sprint_runner/main.py` (S3+S4 — find TODO triage/conformance/cost placeholders), `docs/protocols/tier-2.5-triage.md`, `docs/protocols/spec-conformance-check.md`, `docs/protocols/templates/tier-2.5-triage-prompt.md`, `docs/protocols/templates/spec-conformance-prompt.md`, `docs/protocols/templates/fix-prompt.md`
2. Run: `python -m pytest tests/ -x -q` — all passing

## Objective
Implement Tier 2.5 triage (subagent invocation + verdict parsing + fix session insertion), spec conformance check, and cost tracking with ceiling enforcement. Wire all three into the main loop.

## Requirements

1. **Create `scripts/sprint_runner/triage.py`**: Tier 2.5 triage.
   - `TriageManager(executor: ClaudeCodeExecutor, config: TriageConfig)`.
   - **`async run_triage(closeout: dict, verdict: dict | None, sprint_spec: str, spec_by_contradiction: str, session_breakdown: str) -> TriageVerdict`**: Build triage prompt from template + inputs. Invoke Claude Code subagent via executor. Parse TriageVerdict JSON. Return structured result.
   - **`generate_fix_prompt(issue: dict, sprint_spec: str) -> str`**: Generate a fix session implementation prompt from the fix-prompt template.
   - **Fix session insertion:** When triage returns INSERT_FIX, create a SessionPlanEntry and insert it into the run-state's session_plan after the current session. The fix session gets: auto-generated prompt, a corresponding review step, its own run-log directory.
   - **Max auto-fixes:** Track fix sessions inserted. If count exceeds `triage.max_auto_fixes`, halt regardless of triage recommendation.
   - Handle triage subagent failure gracefully: if Claude Code returns no parseable verdict, treat as HALT (conservative bias per protocol).

2. **Create `scripts/sprint_runner/conformance.py`**: Spec conformance check.
   - `ConformanceChecker(executor: ClaudeCodeExecutor, config: ConformanceConfig)`.
   - **`async check(sprint_spec: str, spec_by_contradiction: str, cumulative_diff: str, session_breakdown: str, closeout: dict) -> ConformanceVerdict`**: Build prompt from template. Invoke subagent. Parse verdict (CONFORMANT/DRIFT-MINOR/DRIFT-MAJOR).
   - Large diff handling: if cumulative diff > 50KB, summarize at file level.
   - Handle subagent failure: log WARNING and return CONFORMANT (defense-in-depth, not critical gate per protocol).

3. **Create `scripts/sprint_runner/cost.py`**: Cost tracking.
   - `CostTracker(config: CostConfig)`.
   - **`estimate_tokens(output: str) -> int`**: Rough estimation (~4 chars per token).
   - **`estimate_cost(input_tokens: int, output_tokens: int) -> float`**: Using configured rates.
   - **`update(session_id: str, output: str, run_state: RunState)`**: Update run_state.cost totals.
   - **`check_ceiling(run_state: RunState) -> bool`**: Return True if ceiling exceeded.

4. **Modify `scripts/sprint_runner/main.py`**: Wire in all three:
   - After CLEAR verdict: run conformance check. Route on verdict.
   - On CONCERNS verdict: run triage. Route on recommendation (INSERT_FIXES_THEN_PROCEED, HALT, PROCEED).
   - On CLEAR with scope_gaps or prior_session_bugs: also run triage.
   - At session boundary: update cost, check ceiling.
   - Fix session execution: inserted fix sessions go through the same loop.

## Constraints
- Do NOT modify anything under `argus/`. ALL subagent calls mocked. No live Claude Code invocations.
- Triage and conformance subagents are invoked via the same ClaudeCodeExecutor as implementation sessions.

## Test Targets
- `test_triage.py`: INSERT_FIX/DEFER/HALT/LOG_WARNING routing ×4, max_auto_fixes ×1, fix insertion into plan ×1, subagent failure → HALT ×1 (~7)
- `test_conformance.py`: CONFORMANT/DRIFT-MINOR/DRIFT-MAJOR routing ×3, large diff summary ×1, subagent failure → CONFORMANT ×1 (~5)
- `test_cost.py`: token estimation, cost calculation, ceiling check, accumulation across sessions (~4 — but these are simpler)
- Note: Also update test_loop.py to verify triage/conformance integration
- Minimum: 12 tests
- Command: `python -m pytest tests/sprint_runner/test_triage.py tests/sprint_runner/test_conformance.py tests/sprint_runner/test_cost.py -v`

## Definition of Done
- [ ] All three modules implemented and wired into main loop. All tests pass (≥12 new).

## Close-Out
Follow `.claude/skills/close-out.md`. Include structured JSON appendix.

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-23.2/review-context.md`
