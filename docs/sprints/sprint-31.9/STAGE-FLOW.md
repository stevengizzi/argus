# Sprint 31.9 — Stage Flow

> Dependency DAG for the combined Audit Phase 3 + Debrief Impromptu campaign.
> 9 stages, 24 sessions total (22 Track A audit + 2 Track B impromptu).
> For narrative and scheduling context, see [README.md](./README.md).

---

## Legend

- **Track A** — Audit Phase 3 fix sessions (`FIX-00` through `FIX-21`). Prompts in `docs/audits/audit-2026-04-21/phase-3-prompts/`.
- **Track B** — Debrief Impromptu sessions (`IMPROMPTU-01`, `IMPROMPTU-02`). Prompts in this folder.
- **ARGUS DOWN** — paper trading paused, IBKR paper account flat, no open positions. All weekend-only sessions require this state.
- **ARGUS LIVE OK (safe-during-trading)** — sessions that do not touch execution/risk/data runtime paths and can land during market hours.
- **READ-ONLY** — sessions that write no source, config, or test files. Only docs artifacts.

Each stage is a barrier: all sessions in a stage must commit before the next stage begins.

---

## DAG

```
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 1   ARGUS DOWN (weekend, paper paused)                     │
│ Parallel: FIX-01 · FIX-11 · FIX-00 · FIX-15 · FIX-17 · FIX-20    │
│ Track A                                  (6 sessions)            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 2   ARGUS DOWN                                             │
│ Parallel: FIX-02 · FIX-03 · FIX-19 · FIX-12 · FIX-21             │
│ Track A                                  (5 sessions)            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 3   ARGUS DOWN                                             │
│ Parallel: FIX-04 · FIX-16 · FIX-14                               │
│ Track A                                  (3 sessions)            │
│                                                                  │
│ ★ FIX-04 unlocks IMPROMPTU-02 scoping eligibility (Stage 9A).    │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 4   ARGUS DOWN                                             │
│ Parallel: FIX-05 · FIX-18 · FIX-10                               │
│ Track A                                  (3 sessions)            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 5   ARGUS DOWN                                             │
│ Parallel: FIX-06 · FIX-07                                        │
│ Track A                                  (2 sessions)            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 6   ARGUS DOWN                                             │
│ Solo: FIX-08                                                     │
│ Track A                                  (1 session)             │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 7   ARGUS DOWN                                             │
│ Solo: FIX-09                                                     │
│ Track A                                  (1 session)             │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 8   ARGUS LIVE OK (safe-during-trading)                    │
│ Parallel:                                                        │
│   Track A: FIX-13        (closes DEF-150 time-of-day flake)      │
│   Track B: IMPROMPTU-01  (log + UI hygiene — F-01/F-05/F-06/F-08)│
│                                          (2 sessions)            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 9A  READ-ONLY                                              │
│ Solo: IMPROMPTU-02 scoping                                       │
│ Track B. Bracket amendment leak investigation.                   │
│ Writes only docs/sprints/sprint-31.9/. Produces:                 │
│   • impromptu-02-findings.md                                     │
│   • impromptu-02-fix.md   (overwrites placeholder)               │
│                                                                  │
│ ⚑ Eligibility: any time after Stage 3 completes.                 │
│   May run in parallel to Stages 4–8 without blocking them.       │
│   Listed here as 9A because it must complete before 9B.          │
│                                          (1 session)             │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 9B  ARGUS DOWN (weekend-only)                              │
│ Solo: IMPROMPTU-02 fix                                           │
│ Track B. Resolves F-03 (bracket amendment leak) +                │
│ F-04 (flatten retry invalidation) + F-10 (emergency flatten      │
│ frequency).                                                      │
│                                          (1 session)             │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                   ┌──────────────────────────────┐
                   │      CAMPAIGN CLOSE          │
                   │                              │
                   │  Work Journal produces       │
                   │  doc-sync prompt + narrative │
                   │  per workflow/templates/     │
                   │  work-journal-closeout.md.   │
                   │  Updates:                    │
                   │   • CLAUDE.md DEF table      │
                   │   • docs/decision-log.md     │
                   │   • sprint-31.9/README.md    │
                   │     (status: COMPLETE, SHA)  │
                   │   • debriefs/2026-04-21.md   │
                   │     (resolution section)     │
                   └──────────────────────────────┘
```

---

## Dependency summary

Hard mandatory edges (what blocks what):

| Predecessor | Successor | Reason |
|---|---|---|
| Stage 1 | Stage 2 | Standard sequential barrier |
| Stage 2 | Stage 3 | Standard sequential barrier |
| Stage 3 | Stage 4 | Standard sequential barrier |
| Stage 4 | Stage 5 | Standard sequential barrier |
| Stage 5 | Stage 6 | Standard sequential barrier |
| Stage 6 | Stage 7 | Standard sequential barrier |
| Stage 7 | Stage 8 | Standard sequential barrier |
| **Stage 3 (FIX-04 commit)** | **Stage 9A** | IMPROMPTU-02 scoping must read Order Manager with `entry_price=0` bug corrected, otherwise F-02 and F-03 symptoms are entangled in the trace |
| **Stage 8** | **Stage 9B** | IMPROMPTU-02 fix should land on a main with DEF-150 flake fixed (FIX-13) and log hygiene applied (IMPROMPTU-01) for clean post-fix validation |
| **Stage 9A** | **Stage 9B** | IMPROMPTU-02 fix prompt is generated by the scoping session; cannot run until that prompt exists |
| Stage 9B | Campaign Close | Standard |

Parallelization opportunities (non-blocking):

- **IMPROMPTU-02 scoping (9A)** can run concurrently with Stages 4 / 5 / 6 / 7 / 8. It writes only to `docs/sprints/sprint-31.9/` and reads source code at whatever state main happens to be in. Running it early (e.g., during Stage 4 or 5) gives the operator more time to review the findings before scheduling 9B.
- **Within each stage**, the parallel sessions listed have been pre-verified by the audit's Phase 2 review to have no file overlap. Run them concurrently.

---

## Session count breakdown

| Stage | Track A | Track B | Total | ARGUS state |
|---|---:|---:|---:|---|
| 1 | 6 | 0 | 6 | DOWN |
| 2 | 5 | 0 | 5 | DOWN |
| 3 | 3 | 0 | 3 | DOWN |
| 4 | 3 | 0 | 3 | DOWN |
| 5 | 2 | 0 | 2 | DOWN |
| 6 | 1 | 0 | 1 | DOWN |
| 7 | 1 | 0 | 1 | DOWN |
| 8 | 1 | 1 | 2 | **LIVE OK** |
| 9A | 0 | 1 | 1 | LIVE OK (read-only) |
| 9B | 0 | 1 | 1 | DOWN |
| **Total** | **22** | **3** | **24 + close** | — |

(Track B shows 3 sessions because IMPROMPTU-02 is counted as its scoping + fix; the fix-prompt placeholder isn't a session, just an artifact slot.)

---

## If a stage fails

Per the campaign escalation criteria in `WORK-JOURNAL-HANDOFF.md`:

- **Test regression (net pytest delta < 0)** — halt the stage, escalate to Work Journal, do not proceed to next stage until resolved.
- **CRITICAL finding in Tier 2 review** — same as above.
- **IMPROMPTU-02 scoping reveals the bug is not one root cause but several intertwined** — escalate to decide whether to split the fix into multiple sessions (possibly 9B1 + 9B2). The handoff's escalation criterion covers this explicitly.
- **Stage 8 parallel sessions conflict unexpectedly** — roll back IMPROMPTU-01 (it's the newer, less-tested of the two), finish FIX-13 solo, reschedule IMPROMPTU-01 to Stage 9A's time slot or 9B.

All halt/escalate decisions are logged as Outstanding review flags in the Work Journal running register.
