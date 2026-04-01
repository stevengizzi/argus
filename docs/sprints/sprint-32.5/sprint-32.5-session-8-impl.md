# Sprint 32.5, Session 8: DEF-133 Vision Document + Doc-Sync

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/architecture.md` (understand current architecture doc structure)
   - `docs/roadmap.md` (understand current roadmap)
   - `docs/project-knowledge.md` (this sprint will update it)
   - `CLAUDE.md` (this sprint will update it)
   - `docs/sprint-history.md` (for sprint entry format)
   - `docs/decision-log.md` (check max DEC number, review format)
   - `docs/dec-index.md` (check format)
   - `docs/sprint-campaign.md` (check format)
   - All close-out reports from this sprint: `docs/sprints/sprint-32.5/session-*-closeout.md`
   - All review reports from this sprint: `docs/sprints/sprint-32.5/session-*-review.md`
2. Run the FULL test baseline (DEC-328 — final session):
   ```
   cd /Users/stevengizzi/argus && python -m pytest -x -n auto -q 2>&1 | tee /tmp/s8-preflight.txt
   cd /Users/stevengizzi/argus/argus/ui && npx vitest run 2>&1 | tee /tmp/s8-preflight-vitest.txt
   ```
   Expected: ~4,441 pytest passing, ~708 Vitest (1 pre-existing failure)
3. Verify you are on branch: `main`
4. Create working branch: `git checkout -b sprint-32.5-session-8`

## Objective
Write the Adaptive Capital Intelligence architectural vision document (DEF-133) and perform full doc-sync for Sprint 32.5.

## Requirements

### Part 1: DEF-133 Vision Document

Create `docs/architecture/allocation-intelligence-vision.md` with these 9 sections:

1. **Problem Statement:** Why the current stacked guardrail model (Risk Manager → DynamicPositionSizer → overflow routing → Orchestrator regime filtering) is suboptimal. Each layer applies independent logic; the system asks "does this violate limits?" when it should ask "what is the optimal capital to deploy?"

2. **Vision:** Single unified `AllocationIntelligence` service. Continuous sizing output instead of approve/reject binary. Takes full system state as input.

3. **Six Input Dimensions:**
   - Edge estimation with uncertainty (Kelly criterion with confidence intervals, not arbitrary tiers)
   - Portfolio-level risk in real-time (correlation, concentration as continuous functions)
   - Opportunity cost (capital allocation across competing signals)
   - Temporal awareness (time-of-day adjustment, continuous not binary)
   - Self-awareness of recent performance (smooth drawdown response)
   - Variant track record with recency weighting

4. **Phased Implementation Roadmap:**
   - Phase 0 (current, Sprint 32): Equal allocation + hard limits
   - Phase 1 (~Sprint 34-35): Kelly-inspired sizing with uncertainty-aware edge estimation, within existing Risk Manager
   - Phase 2 (~Sprint 38+): Full AllocationIntelligence replacing stacked guardrails

5. **Data Requirements:** What the system needs to observe before each phase can begin (trade count thresholds, counterfactual data volume, regime cycle diversity)

6. **Architectural Sketch:** Where AllocationIntelligence sits, what it replaces, what it preserves. Diagram or structured description of component relationships.

7. **Interface Design:** What replaces approve/reject/modify. Continuous sizing output with metadata (confidence, edge estimate, portfolio impact).

8. **Hard Floor Definition:** Circuit breakers remain non-overridable catastrophic protection. Define the boundary between "AllocationIntelligence decides" and "hard floor enforces."

9. **Relationship to Existing Components:** How AllocationIntelligence interacts with Risk Manager, Quality Engine, Learning Loop, Experiment Pipeline, Orchestrator.

### Part 2: Doc-Sync

Update all canonical documents. For each document, read the current content first, then apply surgical updates based on Sprint 32.5 deliverables.

**Aggregate from close-out reports:**
- Actual test counts from each session
- Any new DECs or DEFs created during implementation
- Actual files created/modified
- Any scope changes or deferred items

**Documents to update:**

1. `docs/project-knowledge.md` — Sprint 32.5 in history table, test counts, build track queue, experiment pipeline section (exit params, all 7 patterns, UI, 9th page), new endpoints, DEF closures (131/132/133/134), new DEF items
2. `CLAUDE.md` — test counts, DEF closures, new DEFs, max DEC/DEF numbers, 9th page
3. `docs/roadmap.md` — 32.5 complete, next sprint queue advancement
4. `docs/sprint-history.md` — Sprint 32.5 entry
5. `docs/decision-log.md` — any new DECs (compile from close-outs)
6. `docs/dec-index.md` — index entries for new DECs
7. `docs/architecture.md` — experiment pipeline expansion, 9th page, new endpoints, vision doc reference
8. `docs/sprint-campaign.md` — 32.5 complete

## Constraints
- Do NOT modify: any source code files (this is a docs-only session)
- Do NOT fabricate test counts or DEC/DEF numbers — extract actual values from close-out reports
- Do NOT change the vision document after doc-sync begins (write vision first, then doc-sync)
- The vision document must be self-contained (readable without other ARGUS docs)

## Test Targets
- No new tests in this session (docs only)
- Full suite must still pass (verified in pre-flight)
- Test command (final session, full suite): `python -m pytest -x -n auto -q && cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Vision document created with all 9 sections
- [ ] project-knowledge.md updated
- [ ] CLAUDE.md updated
- [ ] roadmap.md updated
- [ ] sprint-history.md updated
- [ ] decision-log.md updated (if new DECs)
- [ ] dec-index.md updated (if new DECs)
- [ ] architecture.md updated
- [ ] sprint-campaign.md updated
- [ ] All tests still pass (verified in pre-flight, no code changes)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-8-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-8-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command (FINAL session — full suite): `cd /Users/stevengizzi/argus && python -m pytest -x -n auto -q && cd argus/ui && npx vitest run`
5. Files NOT modified: any source code files (*.py, *.ts, *.tsx, *.yaml)

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify vision document covers all 9 required sections
2. Verify vision document is self-contained (no dangling references)
3. Verify doc-sync test counts match actual close-out reports (not planning estimates)
4. Verify DEF closures match actual sprint deliverables (131, 132, 133, 134)
5. Verify new DEF items (if any) have sequential numbers from max DEF
6. Verify build track queue in project-knowledge.md shows 32.5 complete
7. Verify no source code files were modified

## Sprint-Level Regression Checklist (for @reviewer)

### Full Sprint Verification (Final Session)
- [ ] All pytest pass (full suite)
- [ ] All Vitest pass (full suite)
- [ ] No source code files modified in this session
- [ ] Documentation internally consistent (test counts, DEC/DEF numbers match across docs)
- [ ] Vision document readable as standalone architecture document

## Sprint-Level Escalation Criteria (for @reviewer)
Same as sprint-level criteria in review-context.md. Additionally:
- If doc-sync reveals inconsistencies between close-out reports and actual code state → flag for resolution before merge.
