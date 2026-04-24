# Sprint 31.9 IMPROMPTU-09: Verification Sweep (9 Apr 22 + Apr 23 Debrief Gaps)

> Drafted Phase 2. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign. **Read-only** — no code changes land in this session.

## Scope

**Finding addressed:**
The Apr 22 paper session debrief (`docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md`) identified 8 verification gaps, and the Apr 23 debrief added a 9th (VG-9, VIX DB-side wiring confirmation) — claims made during triage that require evidence from a subsequent paper session or from read-only inspection. This session walks through all 9, runs the queries/greps/inspections, and produces a verification report. May open new DEFs; does NOT modify code.

**Dependencies:**
- **IMPROMPTU-04 must have landed** (A1 fix + startup invariant + C1 log downgrade) — some verification items require running with the A1 fix present.
- **At least one paper session must have run** with the IMPROMPTU-04 fix in effect. Multiple sessions is better, but one is the minimum.

**Files touched:**
- `docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md` (NEW — the main deliverable)
- `CLAUDE.md` — new DEFs opened if verification surfaces them
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — IMPROMPTU-09 row complete; new DEFs logged
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 9C row for IMPROMPTU-09

**Safety tag:** `safe-during-trading` — purely read-only inspection. Paper trading continues.

**Theme:** Convert the Apr 22 debrief's 8 "needs verification" claims into either confirmed-resolved, confirmed-pending, or confirmed-different-than-claimed. The campaign should not close with open verification debt.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading continues.
```

### 2. Verify dependencies

```bash
# Confirm IMPROMPTU-04 landed:
git log --oneline --grep "IMPROMPTU-04" 2>/dev/null | head -3
# Expected: at least one commit mentioning IMPROMPTU-04

# Confirm CLAUDE.md has DEF-199 strikethrough:
grep "~~DEF-199~~" CLAUDE.md | head -1
# Expected: a strikethrough line

# Confirm there's a paper session log after IMPROMPTU-04 landed:
ls -lt logs/argus_*.jsonl 2>/dev/null | head -5
# Expected: at least one dated after IMPROMPTU-04's commit date
```

If any of these dependencies are missing, pause and discuss with the operator before proceeding. Running this session without IMPROMPTU-04 in place means half the verification items can't be answered.

### 3. Branch & workspace

```bash
git checkout main
git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

1. Read these files:
   - `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` — the triage doc that spawned the first 8 gaps. Look for a "Verification gaps" section or equivalent; if not explicitly sectioned, gaps are scattered inline throughout the debrief.
   - `docs/sprints/sprint-31.9/debrief-2026-04-23-triage.md` §B1 — VIX wiring confirmation gap (VG-9, added post-April-23 debrief).
   - `docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md` — **pre-populates evidence for 4 of 9 gaps** (VG-1 A1 fire-test: debrief §A1 CONFIRMED; VG-2 startup invariant: debrief §B6 INCONCLUSIVE-unexercised; VG-8 C1 downgrade: debrief §B4 CONFIRMED 86% log reduction; VG-9 VIX wiring state: debrief §B1 CONFIRMED at boot, DB-side query still needed). IMPROMPTU-09 validates each debrief claim against DB/log evidence rather than re-performing debrief work.
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-09" — check if the plan enumerates the 9 gaps with specific verification tactics.
   - `CLAUDE.md` — DEF-194/195/196/197/198/199 entries (Apr 22 debrief's bucket A1/B1-8/C1-8 findings)
   - `docs/protocols/market-session-debrief.md` — the debrief protocol itself; understand the 7-phase structure

2. Compile the canonical list of 9 gaps (8 from Apr 22 + VG-9 from Apr 23 §B1). If they're not explicitly enumerated in the debrief, infer from the triage notes by looking for phrases like "needs verification," "pending paper session," "to confirm," "assumed but unverified." Enumerate them in the verification report's §1.

## Objective

Produce a verification report that, for each of the 9 gaps (8 from Apr 22 +
VG-9 from Apr 23 §B1), records:
- **Claim** (what the triage asserted)
- **Verification method** (SQL query, log grep, paper session observation, or code inspection)
- **Evidence** (the actual query/grep output or log excerpt)
- **Conclusion** (CONFIRMED / REFUTED / INCONCLUSIVE / NEW-DEF-OPENED)
- **Follow-up** (close the related DEF / open a new DEF / no action)

Do NOT modify production code, tests, or configs. Do NOT re-run existing
revalidations. Do NOT edit the debrief triage document itself — only add
cross-references to the new verification report.

**Note on evidence reuse:** The Apr 24 debrief has substantively pre-answered gaps VG-1, VG-2, VG-8, and provided preliminary evidence for VG-9. IMPROMPTU-09's job for these gaps is *not* to redo the work — it's to verify the debrief's claims hold against independent DB queries (for VG-9: actual `regime_history.db` SELECT) and to confirm the log-side evidence cited in the debrief actually exists in the form described (reviewer cross-check discipline). The Apr 22 gaps remain fully open — today's debrief doesn't cover those.

## Requirements

### Requirement 1: Enumerate the 9 gaps

In the verification report (`IMPROMPTU-09-verification-report.md`), open with a flat table of all 9 gaps, each with a unique ID (VG-1 through VG-9, for "Verification Gap"). Note: VG-1–VG-8 derive from the April 22 debrief triage; VG-9 was added post-April-23 debrief (see Pre-Flight Context Reading above).

If the count differs from 9 after rigorous reading (could be 8 or 10 or more
depending on how you split inline gaps), record the actual count + why you
deviated from the planning-time estimate. Don't force 9.

**VG-9 — VIX dimensions populated in `regime_history.db`.**
- **Claim (Apr 23 debrief §B1):** FIX-05 / DEF-170 `VIXDataService` wiring log-confirmed at startup (`VIXDataService wired into Orchestrator (forwarded to RegimeClassifierV2 if present)` + `ready=True, stale=False`). Downstream DB-side verification not yet performed.
- **Verification method (B — SQL):** Read-only SQL against `data/regime_history.db` — `SELECT MIN(vix_close), MAX(vix_close), AVG(vix_close), COUNT(*) FROM regime_history WHERE date(timestamp) = '2026-04-23';` (or whichever date the next post-IMPROMPTU-04 paper session produces).
- **Expected:** `MIN` and `MAX` both non-null; `COUNT(*)` > 0. If all rows have `vix_close IS NULL`, FIX-05 regression — open a new DEF.

### Requirement 2: For each gap, verify

Structure: one section per gap. Apply the appropriate verification method based on the gap's nature. Common methods:

**Method A — SQL query against production DBs (read-only):**
```bash
# Examples:
sqlite3 data/argus.db ".schema trades"
sqlite3 data/argus.db "SELECT strategy_id, COUNT(*) FROM trades WHERE exit_time >= '2026-04-23' GROUP BY strategy_id;"
sqlite3 data/counterfactual.db "SELECT ... "
```

All DBs should be queried in read-only mode. Use `sqlite3 -readonly` if available, or simply never issue `INSERT`/`UPDATE`/`DELETE`/`DROP`.

**Method B — Log grep:**
```bash
# Examples:
grep -c "Startup invariant" logs/argus_20260424.jsonl
grep "STARTUP INVARIANT VIOLATED" logs/argus_*.jsonl
jq 'select(.level == "ERROR") | .message' logs/argus_20260424.jsonl | head -20
```

Use `jq` for structured logs; `grep` for quick scans.

**Method C — Code inspection:**
- Read the relevant source file
- Verify a claimed code path exists and behaves as the debrief described
- Use `git blame` to confirm the current shape is what was actually deployed on Apr 22

**Method D — Paper session observation:**
- Some gaps only answer after the system runs with the IMPROMPTU-04 fix for a session
- Look for the presence/absence of specific log lines, trade patterns, or position states

**Method E — Configuration verification:**
```bash
python -c "import yaml; print(yaml.safe_load(open('config/risk_limits.yaml')))"
```

### Requirement 3: For each gap, produce a verification entry

```markdown
## VG-1: [Gap description from debrief]

**Claim (debrief):** [Exact quote or paraphrase from debrief]

**Verification method:** [A/B/C/D/E + brief description]

**Evidence:**
[Query output, grep output, or code excerpt. Be concrete.]

**Conclusion:** [CONFIRMED / REFUTED / INCONCLUSIVE / NEW-DEF-OPENED]

**Follow-up:** [Action — close DEF-NNN / open DEF-NNN / no action / defer to post-31.9-X sprint]

**Related DEFs:** [Cross-refs to any affected CLAUDE.md entries]
```

### Requirement 4: Handle inconclusive verifications

Some gaps may not be verifiable within this session. Example: "the A1 fix prevents short-flip cascade in real paper sessions" needs multiple paper sessions to see enough reconnect events. For INCONCLUSIVE gaps:

1. Document the method attempted + what's missing
2. Propose a concrete follow-up (e.g., "re-run this verification at SPRINT-CLOSE after 2 more paper sessions")
3. Open a MONITOR-tagged DEF if the gap represents standing operational concern
4. Do NOT force a CONFIRMED/REFUTED conclusion from thin evidence

### Requirement 5: Handle surprises

If verification surfaces something unexpected (e.g., "the A1 fix appears to have introduced a new log spam pattern," or "DEF-197 evaluation.db size is actually larger than reported"), open a new DEF on the spot:

1. Assign next sequential number (DEF-201, DEF-202, etc.)
2. Add entry to CLAUDE.md with description + reproduction
3. Note in the verification entry + add to the RUNNING-REGISTER
4. Do NOT attempt to fix in this session — triage-only

### Requirement 6: Summary roll-up

End the report with a summary table:

```markdown
## Summary

| VG | Conclusion | New DEF | Close DEF | Followup |
|----|-----------|---------|-----------|----------|
| VG-1 | CONFIRMED | — | DEF-195 | none |
| VG-2 | INCONCLUSIVE | DEF-201 (MONITOR) | — | re-verify at SPRINT-CLOSE |
| ... | ... | ... | ... | ... |

**Aggregate:** N confirmed, N refuted, N inconclusive, N new DEFs opened, N DEFs closed.
```

## Constraints

- **Do NOT modify** any argus code, config, test, or doc — except:
  - Creating the verification report file (new)
  - Updating CLAUDE.md if new DEFs are opened or existing DEFs are confirmed ready-to-close
  - Updating RUNNING-REGISTER + CAMPAIGN-COMPLETENESS-TRACKER with session outcomes
- **Do NOT re-run** any pattern sweep, revalidation, backtest, or paper session. Verification is observational, not experimental.
- **Do NOT execute** SQL that writes to any DB.
- **Do NOT edit** the Apr 22 debrief triage document itself. Cross-reference from the new report.
- **Do NOT open** DEFs speculatively. Only if verification produces concrete evidence of a defect.
- **Do NOT close** any DEF that IMPROMPTU-09 verification didn't conclusively confirm as resolved. If DEF-195 looks resolved but evidence is thin, keep it OPEN + note in the report.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- Work directly on `main`.

## Test Targets

- No new tests
- No test runs needed (this session is read-only)
- pytest full suite IS run at close-out as a "nothing drifted" sanity check — must match the IMPROMPTU-CI / IMPROMPTU-04-5-6-7-8 latest baseline.

## Definition of Done

- [ ] Verification report at `docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md`
- [ ] All 9 (or N) gaps (8 from Apr 22 debrief + VG-9 from Apr 23 §B1) have an explicit entry with evidence
- [ ] Summary table with aggregate counts
- [ ] Any new DEFs opened in CLAUDE.md + RUNNING-REGISTER
- [ ] Any existing DEFs marked CLOSED-VERIFIED with this session's commit SHA
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` — IMPROMPTU-09 row marked CLEAR
- [ ] No production code modified (`git diff argus/` returns zero)
- [ ] No config modified (`git diff config/` returns zero)
- [ ] No test modified (`git diff tests/` returns zero)
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-09-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-09-review.md`
- [ ] Green CI URL cited (full suite still passes)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Verification report has N entries matching the enumerated gap count | Count sections in the report |
| Each entry has method + evidence + conclusion + followup | Per-section read |
| No `argus/` code modified | `git diff argus/` empty |
| No config modified | `git diff config/` empty |
| No test modified | `git diff tests/` empty |
| Summary table aggregate matches per-entry conclusions | Sum check |
| New DEFs (if any) appear in CLAUDE.md AND RUNNING-REGISTER | Grep cross-ref |
| Closed DEFs (if any) have strikethrough + commit SHA | Grep CLAUDE.md |
| Full pytest suite still passes post-session | `pytest --ignore=tests/test_main.py -n auto -q` |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/IMPROMPTU-09-closeout.md`

Include:
1. **Gap count:** actual N vs planned 8 + why any deviation
2. **Aggregate result table** (from Requirement 6)
3. **Newly opened DEFs** with IDs + one-line descriptions
4. **Closed DEFs** with IDs + closure rationale
5. **Items deferred** to SPRINT-CLOSE or later
6. **Green CI URL** for the session commit (the verification report commit)

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out.

Provide:
1. Review context: this kickoff + debrief triage doc + CLAUDE.md DEF entries
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-09-closeout.md`
3. Verification report path: `docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md`
4. Diff range: `git diff HEAD~N`
5. Files that should NOT have been modified:
   - Any argus/ code file
   - Any config/ file
   - Any tests/ file
   - The Apr 22 debrief triage doc (`docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md`)
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-09-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify read-only discipline.** `git diff` should show ONLY: new verification report, CLAUDE.md, RUNNING-REGISTER, CAMPAIGN-COMPLETENESS-TRACKER. Any other modified file is an escalation.
2. **Verify each gap's evidence is concrete.** A conclusion of "CONFIRMED" without an accompanying SQL output, grep result, or code excerpt is inadmissible. Push back.
3. **Verify INCONCLUSIVE gaps have follow-up plans.** An INCONCLUSIVE label with "TBD" or no plan = ESCALATE.
4. **Verify new DEFs are specific and reproducible.** A vague DEF like "things seem slow" without reproduction steps = push back.
5. **Verify closed DEFs have SHA-tracked closure rationale.** Each should reference the IMPROMPTU-09 commit SHA + specific evidence line.
6. **Verify the gap count deviation (if any) is justified.** Going from 8 to 7 or 10 is fine IF reasoned.
7. **Verify green CI URL for the session commit.**

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0 (no new tests, no deletions)
- Vitest count unchanged
- No scope boundary violation
- CLAUDE.md DEF additions (if any) exist and are self-consistent

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Any argus/ or tests/ or config/ file modified
- Any DEF closed without supporting evidence in the report
- Any new DEF opened without reproduction steps
- The Apr 22 debrief triage doc modified
- Fewer than half the gaps have concrete evidence
- Full pytest suite broken post-session
- Audit-report back-annotation modified

## Post-Review Fix Documentation

Standard protocol.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Verification report path** — operator should open + read the verification report directly
4. **New DEFs opened** (if any) — brief list
5. **Closed DEFs** (if any) — brief list
6. Green CI URL
7. One-line summary: `Session IMPROMPTU-09 complete. Close-out: {verdict}. Review: {verdict}. N gaps verified. {M} new DEFs, {K} closed. Report: docs/sprints/sprint-31.9/IMPROMPTU-09-verification-report.md. CI: {URL}.`
