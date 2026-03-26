# Sprint 27.9, Session 2c: Strategy YAML Config Updates

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/regime.py` (RegimeOperatingConditions — see matches_conditions for field names)
   - `config/strategies/orb_breakout.yaml` (pattern reference for strategy config structure)
   - `config/regime.yaml`
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/core/ -x -q
   ```
   Expected: all passing

## Objective
Update all 7 strategy YAML configs with conservative defaults for new RegimeVector dimensions. Verify match-any semantics ensure zero behavior change. Add VIX calculator enable flag to regime.yaml.

## Requirements

1. **Examine each strategy YAML** to understand existing `operating_conditions` or `allowed_regimes` structure. The new VIX dimensions should be added in a way consistent with the existing pattern.

2. **Update all 7 strategy YAML configs** (`config/strategies/*.yaml`):
   - If strategies use explicit `operating_conditions` blocks: add the 4 new dimension fields with `null` or omit them entirely (both produce match-any via `matches_conditions()`).
   - If strategies use a simpler `allowed_regimes` list: document in close-out that the match-any semantics are handled at the RegimeOperatingConditions level, not in the YAML.
   - **The key invariant:** With these config changes, every strategy that activated before this sprint must still activate under the same conditions. No strategy should be blocked by a new VIX dimension.
   - Add a comment in each YAML: `# VIX regime dimensions: not yet constrained (match-any). Activate post-Sprint 28.`

3. **Verify via test:** Write a simple verification script or test that:
   - Loads each strategy's config
   - Constructs a RegimeVector with the VIX fields set to various values (CALM, CRISIS, etc.)
   - Confirms the strategy's operating conditions match for ALL VIX dimension values (match-any)
   - Confirms match/no-match behavior for existing dimensions is UNCHANGED

## Constraints
- Do NOT modify `argus/strategies/*.py` source code — YAML config changes only
- Do NOT add restrictive VIX conditions to any strategy
- Do NOT change any existing operating condition values

## Test Targets
- Existing tests: all must still pass
- New verification: informal test or script confirming match-any semantics
- Test command: `python -m pytest tests/core/ tests/strategies/ -x -q`

## Definition of Done
- [ ] All 7 strategy YAMLs updated (or confirmed no change needed if match-any is implicit)
- [ ] Match-any semantics verified for all VIX dimensions across all strategies
- [ ] No strategy activation behavior changes
- [ ] All existing tests pass
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-2c-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R6: All 7 strategies activate same as before | Verification test: all strategies match with any VIX dim value |
| No strategy source code modified | `git diff argus/strategies/` → only tests modified or empty |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-2c-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-2c-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/core/ tests/strategies/ -x -q`
5. Do-not-modify: `argus/strategies/*.py` (source code), `argus/core/regime.py`, `argus/execution/`, `argus/data/`

## Session-Specific Review Focus (for @reviewer)
1. Verify NO strategy source code (.py files) was modified — only YAML configs
2. Verify every strategy's operating conditions produce match-any for all 4 new VIX dimensions
3. Verify existing operating condition values (allowed_regimes, etc.) are UNCHANGED in diff

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as in review-context.md. R6 is primary for this session.

## Sprint-Level Escalation Criteria (for @reviewer)
#4 (strategy activation changes) most relevant. If any strategy no longer activates under conditions it previously activated under → ESCALATE.
