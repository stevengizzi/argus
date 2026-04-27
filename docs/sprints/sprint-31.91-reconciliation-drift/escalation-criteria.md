# Sprint 31.91: Sprint-Level Escalation Criteria

> **Phase C artifact 4/7.** Specific, evaluable trigger conditions that halt
> the sprint and require operator + reviewer attention before proceeding.
> Embedded into every implementation prompt so the implementer knows when to
> halt rather than push through.

## Trigger Conditions (Halt Conditions)

Each row below specifies a concrete trigger and the required response. If ANY
trigger fires, the implementer halts the session, posts to the work-journal
conversation, and waits for operator + reviewer disposition before proceeding.

### A. Mandatory Halts (Tier 3 architectural review automatically fires)

| # | Trigger | Required Response |
|---|---------|-------------------|
| A1 | **Session 1c lands cleanly on `main` and Tier 2 verdict = CLEAR.** | Operator arranges Tier 3 architectural review #1. **Scope (per third-pass LOW #17): combined diff of Sessions 0 + 1a + 1b + 1c** — the API contract introduced in Session 0 is part of the OCA architecture; reviewing without it would be incomplete. Tier 3 must verdict CLEAR. Mandatory checkpoint — not optional. |
| A1.5 | **Session 5b lands cleanly on `main` and Tier 2 verdict = CLEAR.** | Operator arranges Tier 3 architectural review #2 of the alert-observability-backend. **Scope: combined diff of Sessions 5a.1 + 5a.2 + 5b** (HealthMonitor consumer + REST + atomic+idempotent acknowledgment in 5a.1; WebSocket + persistence + auto-resolution policy + retention/migration in 5a.2; all backend emitters + E2E + behavioral Alpaca check in 5b). Tier 3 must verdict CLEAR. Mandatory checkpoint — frontend in 5c–5e builds on this API contract. |
| A2 | **Any Tier 2 review on any session produces verdict = CONCERNS or ESCALATE.** | Halt. Operator + Tier 2 reviewer disposition the finding before next session begins. If CONCERNS → typically iterate within the same session. If ESCALATE → operator decides whether to revert that session's commit or fix forward. |
| A3 | **Paper-session debrief on the day after a session merge shows ANY phantom-short accumulation** (vs zero expected for the post-fix state). | Halt sprint. Revert the most recently merged session's commit on `main`. Tier 3 architectural review of why the test layer didn't catch the regression. Re-plan the session (likely with new tests added) before re-attempting. |
| A4 | **Session implementation discovers that the OCA-group ID lifecycle interacts with re-entry in a way the lifecycle tests didn't model** (e.g., race between `is_fully_closed` flag and a new bracket placement on the same symbol). | Halt mid-session. Document the discovered interaction in the close-out's "Discovered Edge Cases" section. Tier 3 review of whether the spec needs revision. |
| A5 | **Session 1a's bracket OCA grouping causes ANY change to DEC-117 atomic-bracket end-to-end behavior** (parent-fails-children-cancel pattern, or transmit-flag semantics). | Halt. The do-not-modify boundary on DEC-117 was crossed. Operator decides whether to refine the OCA-grouping approach to preserve DEC-117 or accept a DEC-117 amendment. |
| A6 | **Session 2c's per-symbol entry gate enters a state from which it cannot self-clear** (e.g., a symbol that was gated remains gated for >5 reconciliation cycles after the broker reports zero shares for it, exceeding the 3-cycle clear-threshold by a margin that suggests the counter logic is broken). | Halt. The deadlock concern called out in Phase A's adversarial focus areas materialized despite the 3-cycle clear-threshold defense. Tier 3 review of the gate-clear logic before Session 2d/3 begins. |
| A7 | **Session 4's mass-balance script reports imbalance >5 shares/symbol on a clean post-merge paper session.** | Halt sprint. The mechanism signature (mass-balance per IMPROMPTU-11) is the falsifiable validation; if it fails post-merge, the fix is incomplete. Tier 3 review of which session's coverage was insufficient. |
| A8 | **Bracket placement performance regresses beyond the documented 50–200ms fill-latency cost on cancelling siblings** (e.g., observed paper-session slippage on bracket-stop fills degrades by >$0.05 mean on the $7–15 share universe vs pre-Sprint-31.91 baseline). | Halt. Tier 3 evaluates whether to roll back to `bracket_oca_type: 0` (preserves Session 1b's standalone-SELL OCA threading while disabling bracket-children OCA) or accept the cost. **Note (H1):** rollback is RESTART-REQUIRED — mid-session flip not supported. |
| A9 | **WebSocket fan-out reconnect loses alert state without REST recovery** (Session 5a/5c). Frontend reconnects after disconnect but does not refetch active state via `GET /api/v1/alerts/active`, OR backend does not re-emit alerts that fired during the disconnect window. | Halt. Tier 3 review of the WebSocket reconnect resilience design. This is alert observability invariant 18; failure here means a critical alert can be silently missed. |
| A10 | **Frontend banner fails to persist across page navigation** while a critical alert is active (Session 5e). | Halt. Banner cross-page persistence is regression invariant 17. Failure indicates Layout-level mounting is incorrect; tier 2 frontend reviewer should catch this but if it slips through, escalate. |
| A11 | **Frontend reviewer template not authored in workflow metarepo before Session 5c begins** (per third-pass HIGH #3). | Halt before Session 5c. The "Tier 2 CLEAR (frontend reviewer)" line in 5c–5e DoD is unactionable without `templates/review-prompt-frontend.md` (or equivalent) in the metarepo specifying: state-machine completeness; reconnect/disconnect resilience; acknowledgment race handling; accessibility (ARIA, keyboard, focus trap); cross-page persistence; z-index/layout interactions; Vitest coverage thresholds; clarification of which reviewer entity runs the frontend review. Operator authors the template before 5c proceeds. |
| A12 | **Live-enable gate criterion 3a (pre-live paper stress test under live-config simulation) OR 3b (live rollback policy) unmet** at the live-trading transition decision point (per third-pass HIGH #4). | Halt live-trading consideration. The decomposed gate criteria (per HIGH #4) replace the prior ambiguous "first-day-live monitored validation" with two named criteria: 3a is gate-before-live (pre-live paper stress test under live-config simulation; ≥1 session; zero phantom_short alerts; zero unaccounted_leak rows); 3b is the live rollback policy ($50–$500 notional cap; phantom_short* trigger → operator-manual halt; expand to standard sizing on day 2 only after session-end clean). Both must be met. **Note:** formal `POST /api/v1/system/suspend` deferred to DEF-210; until DEF-210 lands, 3b's "immediate suspension" is operator-manual. |
| A13 | **Spike script `scripts/spike_ibkr_oca_late_add.py` result file dated >30 days old when transitioning to live trading or upgrading `ib_async`/IBKR API/Gateway** (per third-pass HIGH #5). | Halt the trigger event (live transition / upgrade). Operator re-runs the spike. If returns `PATH_1_SAFE`: proceed. If anything else (`PATH_2_RACE`, `PATH_3_LATE_FILL`, error): the OCA-architecture seal is invalidated; operator decides between rollback to `bracket_oca_type: 0` (RESTART-REQUIRED per H1) or Tier 3 review of new mechanism behavior. |

### B. Mandatory Halts (Tier 3 not required, but operator + Tier 2 reviewer must disposition)

| # | Trigger | Required Response |
|---|---------|-------------------|
| B1 | **Pre-existing flake count increases.** Specifically: any of DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 fail more frequently than baseline OR a NEW intermittent failure appears that doesn't have a DEF entry yet (RULE-041). | Halt. File DEF entry with symptom + repro hint + xdist worker context. Operator decides whether to fix in this sprint or defer. |
| B2 | **Test count goes DOWN** (regression: existing tests deleted or skipped without explanation). | Halt. RULE-019 violation. Implementer explains in close-out which tests were deleted and why; operator + Tier 2 reviewer assess. |
| B3 | **Pytest baseline ends below 5,080** at the close-out of any session. | Halt. The new tests are additive; existing baseline must hold. Investigate which test broke and either fix or revert. |
| B4 | **CI fails on the session's final commit and the failure is NOT a documented pre-existing flake.** | Halt per RULE-050. Do not proceed to next session until CI green is achieved. RULE-052: if CI is red for a known-cosmetic reason, log that assumption explicitly at each subsequent commit. |
| B5 | **DISCOVERY's line-number anchors drift more than 5 lines from the spec values during pre-flight grep-verify.** | Halt mid-pre-flight. Re-anchor the session's surgical edits against actual current line numbers. RULE-038 grep-verify discipline; mark the finding as RESOLVED-VERIFIED if the change is already in place, or flag the discrepancy in the close-out. |
| B6 | **A do-not-modify-list file appears in the session's `git diff`.** | Halt. RULE-004 violation. Revert the unintended change before close-out. If the change is necessary, escalate to operator (the do-not-modify list itself needs amendment). |
| B7 | **Test runtime degrades >2× from baseline** (full suite or scoped) OR a single test's runtime exceeds 60 seconds. | Halt and investigate. Per RULE-037, verify no orphaned background processes are inflating runtime. May be a pyarrow/xdist (DEF-190) recurrence; document in close-out. |

### C. Soft Halts (Continue with extra caution + close-out flag)

| # | Trigger | Required Response |
|---|---------|-------------------|
| C1 | **Implementer notices a bug or improvement opportunity OUTSIDE the current session's scope.** | Document in close-out under "Deferred Items" (RULE-007). Do NOT fix in this session. |
| C2 | **First fix attempt fails and a second approach emerges.** | Per RULE-008, allow ONE additional approach attempt without operator approval; if that also fails, halt and request guidance. |
| C3 | **Two failed fix attempts on the same bug.** | Switch to diagnostic-first mode (RULE-030). Build a minimal repro outside the application code. Close-out marks Context State YELLOW. |
| C4 | **Context State trending YELLOW** (long conversation, many file reads, many edits). | Per RULE-027, proactively checkpoint: commit, run scoped tests, produce partial close-out, suggest continuing in a fresh session. Compaction-induced regressions cost more than session-split overhead. |
| C5 | **Implementer is uncertain whether a change crosses the do-not-modify boundary** (e.g., a refactor that touches order_manager.py near but not in the protected line range). | Pause; consult the SbC do-not-modify list explicitly; if still uncertain, escalate to operator before making the change. Better to halt than to silently regress. |
| C6 | **Phase A's grep-verified line numbers drift 1–5 lines from spec.** | Continue (small drift is RULE-038-acknowledged); document the actual line numbers in the close-out for the next session's reference. |
| C7 | **A test layer's grep regression guard (Session 1b's "no SELL without OCA") false-positives on a legitimate exempt site.** | Add an explicit `# OCA-EXEMPT: <reason>` comment at the exempt site (the regression guard accepts this); document in close-out. Do NOT remove the regression guard. |

## Escalation Targets

For each halt, the escalation flows as follows:

- **Code-level questions** (does this approach work?): Tier 2 reviewer (the
  @reviewer subagent in the same session) is first-line; operator is second-line.
- **Spec-level questions** (does this still match the Sprint Spec?):
  Operator + sprint-planning conversation are required.
- **Architectural questions** (does this change a DEC?): Tier 3 reviewer in a
  separate Claude.ai conversation, with operator dispositioning the verdict.
- **Safety questions** (does this risk paper-trading regressions or live
  trading consideration?): Operator + Tier 3 reviewer; pause paper trading if
  in doubt.

## Sprint Abort Conditions

The sprint as a whole is aborted (not just an individual session) if ANY of:

1. **Two or more A-class halts within the same week.** Indicates the spec or
   the underlying mechanism understanding is wrong; the sprint needs replanning.
2. **DEF-204 mechanism turns out to be different from IMPROMPTU-11's diagnosis.**
   E.g., a paper session shows phantom shorts even after Session 1a's bracket
   OCA fix lands. RULE-051 (mechanism-signature-vs-symptom) — investigate
   whether IMPROMPTU-11's mechanism diagnosis was wrong (DEBUNKED status per
   campaign-orchestration.md §7) before continuing.
3. **Operator paper-trading mitigation breaks** (e.g.,
   `scripts/ibkr_close_all_positions.py` fails or is unsafe for some reason).
   The sprint depends on this mitigation continuing throughout the sprint
   window. If it breaks, sprint pauses until mitigation is restored.
4. **An unrelated upstream sprint changes a key file** (`order_manager.py`,
   `ibkr_broker.py`, `main.py`) in a way that conflicts with this sprint's
   surgical edits. The sprint pauses for rebase + impact assessment.

## Final-Session Sprint Closure Checks

When Session 3 (the final session) closes out, the close-out report MUST verify:

- [ ] All 4 Sprint Spec deliverables have all acceptance criteria green.
- [ ] All Sprint-Level Regression Checklist items verified.
- [ ] DEF-204 status update prepared for CLAUDE.md (CLOSED with citation chain).
- [ ] DEC-385 + DEC-386 entries drafted for `decision-log.md`.
- [ ] RSK-DEF-204 transition prepared for `risk-register.md`.
- [ ] `architecture.md` §3.7 + §3.3 updates drafted (the DEF-204 callout at
      `architecture.md:855` becomes a CLOSED reference).
- [ ] Cross-reference rename updates from artifact 6 (Doc Update Checklist)
      verified complete.

These checks gate the sprint-close phase, not just Session 3. The doc-sync
follow-on is a separate session per RULE-014; this sprint's Session 3
**writes the doc-update files** (with surgical patches) but the actual file
edits land in a follow-on doc-sync session per the existing
post-sprint-doc-sync-prompt pattern.

---

*End Sprint 31.91 Escalation Criteria.*
