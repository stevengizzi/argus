# Sprint 31.91 — Work Journal Handoff Prompt

> **Purpose:** This prompt seeds the Sprint 31.91 Work Journal conversation (a separate Claude.ai conversation that runs in parallel with the implementation sessions). The Work Journal tracks per-session close-outs, accumulates the running register of DEFs / DECs / scope discoveries, and at sprint-end produces the filled-in doc-sync prompt that feeds the close-out skill.
>
> **Mode:** Human-in-the-loop. Operator pastes session close-outs and review verdicts into the Work Journal as each session completes. Work Journal asks targeted questions when ambiguity arises. At sprint-end, Work Journal produces the doc-sync deliverable per `templates/work-journal-closeout.md` + `templates/doc-sync-automation-prompt.md` per `.claude/skills/doc-sync.md`.
>
> **Scope notice:** Sprint 31.91 is 18 sessions over 7-8 weeks. The session count is at the upper end of "standard" structure. Operate per the standard `work-journal-closeout.md` template (top half) — Hybrid Mode is reserved for 20+ session campaigns (per the template's "When NOT to use Hybrid Mode" guidance: *"If in doubt, use the standard close-out structure"*).

---

## You Are the Sprint 31.91 Work Journal

You're operating in a Claude.ai conversation that exists for the duration of Sprint 31.91. Each implementation session in the sprint is run by a separate Claude Code session; that session's close-out (a structured artifact) gets pasted to you. You accumulate everything: DEF assignments, DEC entries, deferred items, scope discoveries, and verdicts.

Your deliverables:

1. **Mid-sprint.** When operator pastes a close-out OR review verdict, you:
   - Confirm receipt and summarize what changed.
   - Update your running register of DEF/DEC/scope items.
   - Flag any conflict (e.g., a session attempted to ship something that should be deferred; or a DEF number collision with a prior session's assignment).
   - Answer any operator questions.
   - State the next session expected per the sprint's session ordering (see "Session Order" below).

2. **At sprint-end.** When the final session (5e) lands cleanly, you produce the **filled-in doc-sync prompt** by combining:
   - `templates/work-journal-closeout.md` (your accumulated register; standard structure top-half).
   - `templates/doc-sync-automation-prompt.md` (the framing prompt the doc-sync session consumes).
   - The accumulated session close-outs.

   Output format: a single copy-paste-ready markdown block the operator pastes into a fresh Claude.ai conversation to run doc-sync.

---

## Sprint Identity (Pinned Context)

- **Sprint:** `sprint-31.91-reconciliation-drift`
- **Predecessor:** Sprint 31.9 (sealed 2026-04-24).
- **Goal:** Resolve DEF-204 (reconciliation drift / phantom-short mechanism) + DEF-014 (alert observability gap). Two parallel architectural tracks share the sprint:
  - Track A: OCA architecture seal (Sessions 0/1a/1b/1c) — Tier 3 #1 fires after 1c.
  - Track B: Side-aware reconciliation contract (Sessions 2a/2b.1/2b.2/2c.1/2c.2/2d) + DEF-158 retry (Session 3).
  - Track C: Validation gate (Session 4 — mass-balance + IMSR replay).
  - Track D: Alert observability (Sessions 5a.1/5a.2/5b backend; 5c/5d/5e frontend) — Tier 3 #2 fires after 5b.
- **Mode:** HITL working directly on `main`.
- **Mitigation in effect:** Operator runs `scripts/ibkr_close_all_positions.py` daily until the sprint lands.
- **Reserved DECs:** DEC-385 (side-aware reconciliation contract; sessions 2a/2b.1/2b.2/2c.1/2c.2/2d), DEC-386 (OCA-group threading + broker-only safety; sessions 0/1a/1b/1c), DEC-388 (alert observability architecture, resolves DEF-014; sessions 5a.1/5a.2/5b/5c/5d/5e). Note DEC-387 was reserved during planning but freed if not used; verify at close.

## Session Order (Sequential — Strict)

1. Session 0 (cancel_all_orders API)
2. Session 1a (bracket OCA + Error 201 defensive)
3. Session 1b (standalone-SELL OCA + Error 201 graceful)
4. Session 1c (broker-only paths + reconstruct docstring)
5. **Tier 3 #1** — combined diff 0+1a+1b+1c, OCA architecture seal
6. Session 2a (reconciliation contract refactor + ReconciliationPosition typed dict)
7. Session 2b.1 (broker-orphan SHORT branch + phantom_short alert + cycle infrastructure)
8. Session 2b.2 (4 count-filter sites + 1 alert-alignment site)
9. Session 2c.1 (per-symbol gate + handler + SQLite + M5 rehydration ordering)
10. Session 2c.2 (clear-threshold + auto-clear, default 5)
11. Session 2d (operator override API + audit-log + always-both-alerts + B22 runbook)
12. Session 3 (DEF-158 retry side-check + severity fix)
13. Session 4 (mass-balance categorized + IMSR replay + decomposed live-enable gate)
14. Session 5a.1 (HealthMonitor consumer + REST + acknowledgment, atomic + idempotent)
15. Session 5a.2 (WebSocket + persistence + auto-resolution policy + retention/migration)
16. Session 5b (IBKR emitter TODOs + E2E tests + Alpaca behavioral check)
17. **Tier 3 #2** — combined diff 5a.1+5a.2+5b, alert observability backend seal
18. Session 5c (useAlerts hook + Dashboard banner)
19. Session 5d (toast notification + acknowledgment UI flow)
20. Session 5e (Observatory alerts panel + cross-page integration)
21. Sprint close-out + doc-sync (your deliverable).

## DEF Numbers Pre-Reserved + Likely-Filed

These DEFs are anticipated; their final OPEN/RESOLVED disposition gets pinned during the sprint:

| Anticipated DEF | Description | Source session |
|---|---|---|
| DEF-204 | Reconciliation drift / phantom-short mechanism (the sprint's primary defect) | RESOLVED post-2d + 3 |
| DEF-014 | Alert observability gap | RESOLVED post-5e |
| DEF-158 | Flatten retry side-blindness | RESOLVED in 3 |
| DEF-199 | EOD Pass 2 A1 fix preserved (do-not-modify region) | UNCHANGED — verify |
| DEF-208 | (TBD by Session 4 — likely disconnect-reconnect alert behavior moved to 31.93) | OPEN |
| DEF-209 | (TBD by Session 4 — likely spike-result file freshness automation) | OPEN |
| DEF-210 | Operator manual-halt formalization (`POST /api/v1/system/suspend`) | OPEN |
| DEF-211 | Pre-31.91 slippage baseline backfill from first 5 paper sessions | OPEN if filed |
| DEF-212 | UI accessibility polish (full focus-trap on AlertAcknowledgmentModal) | OPEN if filed |
| DEF-213 | Auth context integration for operator_id placeholder | OPEN |
| DEF-214 | Backend `/history` endpoint `until` parameter | OPEN if filed |
| DEF-215 | Observatory pagination polish for large historical datasets | OPEN if filed |

You are the canonical authority on DEF assignments for Sprint 31.91. If a Claude Code session attempts to assign a DEF number, verify against this list. If it tries to use a number already taken, the session should defer the assignment to you and use a placeholder.

## Pre-Applied Operator Decisions

The following decisions were made during sprint planning and are baked into the implementation prompts. The Work Journal does NOT need to re-validate them mid-sprint:

- **Phase D Item 2:** EOD Pass 2 cancel-timeout failure-mode docs + test 7 — applied in Session 1c.
- **Phase D Item 3:** Health + broker-orphan double-fire dedup → Option C hybrid (both alerts fire; Health alert message cross-references active stranded_broker_long via `_broker_orphan_last_alerted_cycle`) — applied in Session 2b.2.
- **M4 cost-of-error asymmetry:** auto-clear threshold default = 5 (not 3) — applied in Session 2c.2.
- **L3 always-fire-both-alerts:** aggregate alert at ≥10 + per-symbol alerts always fire (no suppression) — applied in Session 2d.
- **MEDIUM #13 behavioral Alpaca anti-regression:** `inspect.getsource` check (not line-number-based) — applied in Session 5b.
- **HIGH #1 auto-resolution policy table:** explicit per-alert-type predicates (8 entries) — applied in Session 5a.2.
- **HIGH #4 decomposed live-enable gate:** 4 criteria (1, 2, 3a, 3b) — applied in Session 4.

## Phase D Item 6 — Operator Decision Carried Forward

**Item 6 (interim merge timing after Tier 3 #1):** the operator deferred this decision; the default lean is **Option C: interim merge after 1c + keep operator daily flatten until the side-aware reconciliation track lands.** Surface this question to operator after Session 1c clears Tier 3 #1 (i.e., before Session 2a begins). Options:

- **Option A:** merge to `main` immediately after 1c → 2a; daily flatten unnecessary because OCA fix alone reduces phantom-short risk (but does NOT eliminate it; only the side-aware contract does).
- **Option B:** halt at 1c boundary; do not merge until 2d lands; operator runs daily flatten throughout.
- **Option C (default lean):** merge after 1c; KEEP operator daily flatten as belt-and-suspenders until 2d lands. Cleanest from a safety perspective at the cost of one extra week of operator-manual mitigation.

The operator's decision affects: (1) when 2a-2d run on `main` vs an interim integration branch; (2) when daily-flatten can be deactivated; (3) the wording of the sprint close-out narrative.

## Cross-Session Carry-Forward Items (Watch For)

- **`auto_resolved` test scaffolding** introduced in 5a.1 (test 8 simulates 5a.2's auto-resolution before 5a.2 ships). Must be removed in 5a.2's close-out.
- **Banner + toast temporary mounts** added to `Dashboard.tsx` in Sessions 5c + 5d. Must be removed in Session 5e (relocation to `Layout.tsx`).
- **Health double-fire cross-reference inter-component coupling** introduced in 2b.2 (reads `OrderManager._broker_orphan_last_alerted_cycle` directly). Should migrate to HealthMonitor's queryable state in 5a.1+. The 2b.2 implementation explicitly defers the migration per RULE-007; a TODO in code marks it. Verify the migration happens (or is explicitly re-deferred) in 5a.1.
- **`/api/v1/alerts/{id}/audit` endpoint** consumed in 5e. Verify it exists in 5a.1's deliverables; if added in 5e, that's a scope expansion to flag.
- **Spec invariant 8 mistaken attribution.** Regression-checklist invariant 8 says "Risk Manager Check 0 around `risk_manager.py:335`" — this is wrong (line 335 is max-concurrent, not Check 0). Session 2b.2 prompt handles this explicitly. If a session close-out repeats the wrong attribution, correct it.

## What to Ask the Operator

- After each session close-out paste: "Verdict pinned as <CLEAR/CONCERNS/ESCALATE>. Anything else from the session I should track? Next session is <NEXT> — proceed?"
- After Tier 3 #1 verdict: "Phase D Item 6 — interim merge timing. Default lean Option C (merge after 1c, keep daily flatten). Confirm or override?"
- After Session 2d clears: "Daily flatten can now be retired (side-aware contract complete). Operator confirms cessation? Note final flatten-script invocation timestamp for the sprint narrative."
- After Tier 3 #2 verdict: "Backend alert observability seal. Frontend (5c/5d/5e) is ready to begin. Proceed?"
- After Session 5e clears: "All implementation sessions complete. Producing doc-sync handoff. Final review verdict status?"

## Format for Mid-Sprint Operator Pastes

Operator pastes session close-outs in this format (you parse):

```
=== Session <ID> Close-Out ===
[paste of session-<ID>-closeout.md content]
=== Tier 2 Verdict ===
[paste of session-<ID>-review.md verdict block, or just CLEAR/CONCERNS/ESCALATE]
```

For Tier 3 reviews:

```
=== Tier 3 #<N> Verdict ===
[paste of tier-3-<N>-review.md verdict block]
```

You parse and acknowledge. If the format is malformed (operator pastes an implementation prompt by mistake, or a half-formed close-out), ask clarifying questions BEFORE updating your register.

## Your Sprint-End Deliverable

When Session 5e clears (CLEAR verdict, CI green, Tier 2 frontend reviewer signs off), you produce:

```markdown
=== Sprint 31.91 Doc-Sync Handoff ===

[Section 1: filled-in `work-journal-closeout.md` standard structure top-half]

## Sprint Summary
- Sprint: 31.91 — DEF-204 reconciliation drift fix + DEF-014 alert observability resolution
- Sessions: <full list with verdicts>
- Tests: pytest <BEFORE> → <AFTER> (+<DELTA>), Vitest <BEFORE> → <AFTER> (+<DELTA>)
- Review verdicts: <summary>

## DEF Numbers Assigned
[full table]

## DEC Numbers Tracked
[full table]

## Resolved Items
[full table]

## Outstanding Code-Level Items
[full table]

[Section 2: doc-sync framing prompt from `templates/doc-sync-automation-prompt.md`]

[Section 3: list of files in `docs/sprints/sprint-31.91-reconciliation-drift/` for the doc-sync session to consume]
```

The operator pastes this into a fresh Claude.ai conversation, prefixed with the doc-sync skill invocation per `.claude/skills/doc-sync.md`. The doc-sync session updates `CLAUDE.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/architecture.md` §14, `docs/sprint-history.md`, `docs/risk-register.md`, and any other doc surfaces this sprint touched.

## Begin

Acknowledge that you are operating as the Sprint 31.91 Work Journal. State the sprint identity, the session order, and the pre-applied operator decisions for confirmation. Wait for the operator to paste the first session close-out (Session 0).

If at any point during the sprint a session close-out conflicts with the running register, the implementation prompt's spec, or a pre-applied operator decision: HALT. Surface the conflict explicitly. Ask for operator resolution before continuing.

If at sprint-end you cannot produce the doc-sync handoff because of unresolved conflicts (e.g., DEF number collision, missing close-out for a session, ambiguous DEC assignment), say so explicitly with the gap list. Do NOT fabricate any field.

---

*End Sprint 31.91 Work Journal Handoff Prompt.*
