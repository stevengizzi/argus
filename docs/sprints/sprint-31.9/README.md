# Sprint 31.9 — Health & Hardening Campaign

> **Status:** Planning complete, awaiting kickoff
> **Kickoff date:** 2026-04-21 (planning); execution begins next
> **Tracks:** Audit Phase 3 (22 sessions) + Debrief Impromptu (2 sessions)
> **Campaign identifier:** `sprint-31.9-health-and-hardening`

---

## What this campaign is

A **coordinated multi-session sprint** combining two independent bodies of work:

1. **Audit Phase 3** — 22 fix sessions (`FIX-00` through `FIX-21`) from the 2026-04-21 codebase audit. Already fully scoped and prompt-generated. Entry state frozen at baseline 4,934 pytest + 846 Vitest.

2. **Debrief Impromptu** — 2 new sessions (`IMPROMPTU-01`, `IMPROMPTU-02`) resolving bugs discovered during the April 21 market session that are **not** covered by audit Phase 3. Session prompts are in this folder.

The two tracks are managed as one campaign: one Work Journal conversation, one running register of DEFs/DECs, one campaign close-out, one baseline ledger.

## Why combine them

Before combining: the audit was planned, session prompts written, and kickoff imminent. The April 21 market session then surfaced new bugs that overlap with audit scope (execution-layer, bracket amendment, log hygiene) but weren't in the audit's Phase 1 findings. Rather than (a) running the audit, then a separate impromptu, then another close-out, or (b) injecting findings into audit sessions mid-flight and breaking their standalone-ness, we run them as one campaign with two tracks and a single authoritative close-out.

## Entry points — read these in order

1. **This README** — what the campaign is and how it's organized
2. **[`STAGE-FLOW.md`](./STAGE-FLOW.md)** — dependency DAG for all 9 stages and 24 sessions
3. **[`WORK-JOURNAL-HANDOFF.md`](./WORK-JOURNAL-HANDOFF.md)** — paste this into a new Claude.ai conversation to open the Work Journal that will coordinate all sessions
4. **[`../../audits/audit-2026-04-21/00-audit-plan.md`](../../audits/audit-2026-04-21/00-audit-plan.md)** — audit scope and methodology (Phases 1 and 2 already complete)
5. **[`../../audits/audit-2026-04-21/BASELINE.md`](../../audits/audit-2026-04-21/BASELINE.md)** — frozen baseline state at kickoff
6. **[`../../debriefs/2026-04-21.md`](../../debriefs/2026-04-21.md)** — the market session debrief that motivated the impromptu track

## Scope summary

### Track A — Audit Phase 3 (22 sessions)

Location: `docs/audits/audit-2026-04-21/phase-3-prompts/FIX-NN-*.md`

| Session | Safety | Stage |
|---|---|---|
| FIX-00 doc-sync obsoletes | safe-during-trading | 1 |
| FIX-01 quality pipeline + fingerprint infra | weekend-only | 1 |
| FIX-02 config drift (auto-resolved by FIX-01) | weekend-only | 2 |
| FIX-03 main.py lifecycle | weekend-only | 2 |
| FIX-04 execution (includes F-02 `entry_price=0` CRITICAL) | weekend-only | 3 |
| FIX-05 core: orchestrator + risk + regime | weekend-only | 4 |
| FIX-06 data layer | weekend-only | 5 |
| FIX-07 intelligence: catalyst + quality | weekend-only | 5 |
| FIX-08 intelligence: experiments + learning | weekend-only | 6 |
| FIX-09 backtest engine | weekend-only | 7 |
| FIX-10 backtest legacy cleanup | weekend-only | 4 |
| FIX-11 backend API | weekend-only | 1 |
| FIX-12 frontend | weekend-only | 2 |
| FIX-13 test hygiene (closes DEF-150) | **LIVE OK** | 8 |
| FIX-14 docs primary context | weekend-only | 3 |
| FIX-15 docs supporting | safe-during-trading | 1 |
| FIX-16 config consistency | weekend-only | 3 |
| FIX-17 Claude rules | safe-during-trading | 1 |
| FIX-18 deps & infra | weekend-only | 4 |
| FIX-19 strategies | weekend-only | 2 |
| FIX-20 sprint runner | safe-during-trading | 1 |
| FIX-21 ops cron | weekend-only | 2 |

Stage plan from `docs/audits/audit-2026-04-21/WORK-JOURNAL-HANDOFF.md` is unchanged.

### Track B — Debrief Impromptu (2 sessions + placeholder)

Location: this folder.

| Session | File | Safety | Runs at |
|---|---|---|---|
| IMPROMPTU-01 log + UI hygiene | [`impromptu-01-log-ui-hygiene.md`](./impromptu-01-log-ui-hygiene.md) | safe-during-trading | Parallel with Stage 8 (any time after Stage 7 completes so no merge conflict with FIX-12) |
| IMPROMPTU-02 scoping (read-only investigation) | [`impromptu-02-scoping.md`](./impromptu-02-scoping.md) | read-only | After Stage 3 (FIX-04 lands first — scoping reads post-F-02-fix code) |
| IMPROMPTU-02 fix | [`impromptu-02-fix.md`](./impromptu-02-fix.md) (placeholder) | weekend-only | Stage 9 — after IMPROMPTU-02 scoping produces findings and the fix prompt is generated |

**Findings resolved by IMPROMPTU-01:** F-01 log spam (CRITICAL ops), F-05 log truncation (cosmetic), F-06 MFE/MAE unit mismatch (MEDIUM), F-08 PRIORITY_BY_WIN_RATE warning pollution (LOW).

**Findings resolved by IMPROMPTU-02:** F-03 bracket amendment leak (CRITICAL), F-04 flatten retry against non-existent positions (HIGH), F-10 emergency flatten frequency (HIGH — likely same root cause as F-03).

**Findings resolved by Track A (reference):** F-02 `entry_price=0` — audit FIX-04 P1-C1-C01 handles it.

## Ordering and dependencies across both tracks

See **[STAGE-FLOW.md](./STAGE-FLOW.md)** for the full dependency DAG.

Quick reference of the hard constraints:

- **IMPROMPTU-02 scoping must follow FIX-04** so the investigation reads Order Manager with the `entry_price=0` bug already corrected. Otherwise F-02 symptoms and F-03 symptoms are entangled.
- **IMPROMPTU-01 must not overlap with FIX-12** (frontend session) because IMPROMPTU-01 touches `ShadowTradesTab.tsx`. Run IMPROMPTU-01 after Stage 2 completes.
- **Only Stage 8 and IMPROMPTU-02 scoping are safe during market hours.** Everything else is weekend-only.

## Baseline ledger

Frozen at Phase 3 kickoff:
- pytest: **4,934** (4,933 passing + 1 time-of-day flake DEF-150, resolved by FIX-13 at Stage 8)
- Vitest: **846**
- ARGUS state: paper trading active, 22 shadow variants, IBKR paper account U24619949, quality pipeline broken (DEF-082, DEF-142), overflow.broker_capacity divergent

Expected deltas:
- FIX-01 adds +4 pytest (fingerprint infra)
- IMPROMPTU-01 adds ~5–10 pytest + Vitest (log-format regression guards, R-multiple conversion test)
- IMPROMPTU-02 fix adds tests against bracket amendment regression (scope TBD post-scoping)
- FIX-13 resolves DEF-150 → post-campaign flake count is 0
- All other sessions: net delta ≥ 0

Post-campaign target: `~4,945+` pytest, `~850+` Vitest, 0 known flakes.

## DEF allocation guidance

Track which DEFs are opened/resolved by which session in the Work Journal's running register. Suggested DEF numbers (final allocation at operator discretion):

- **Expected opens from Track B:**
  - `DEF-NNN` log spam on pattern_strategy.py:298 (resolved same session, IMPROMPTU-01)
  - `DEF-NNN` MFE/MAE unit mismatch on counterfactual REST response (resolved same session, IMPROMPTU-01)
  - `DEF-NNN` bracket amendment leak in Order Manager (opened at IMPROMPTU-02 scoping; resolution at IMPROMPTU-02 fix)
  - `DEF-NNN` flatten retry invalidation semantics (opened at IMPROMPTU-02 scoping; resolution at IMPROMPTU-02 fix)
  - `DEF-NNN` PRIORITY_BY_WIN_RATE unfinished feature (promoted from "known unfinished" to DEF; status depends on IMPROMPTU-01 decision to gate/remove/finish)

- **Expected DEC from Track A:** `DEC-384` (FIX-01 Option B config merge semantics) is pre-allocated in the audit handoff.

## Close-out

At campaign close (post-IMPROMPTU-02):

1. Work Journal produces a **single filled-in doc-sync automation prompt** per `workflow/templates/work-journal-closeout.md`, embedding:
   - Sprint summary (campaign identifier, all 24 sessions, test deltas)
   - All DEFs assigned
   - All DECs tracked
   - Resolved items
   - Outstanding code-level items (post-campaign known-issues)

2. Standalone narrative covering:
   - How the two tracks interleaved (any conflicts, any surprises)
   - Bracket amendment root cause (from IMPROMPTU-02 scoping)
   - Post-campaign readiness for Sprint 31B (Research Console / Variant Factory)
   - Whether paper-trading validation data from April 21 can be retroactively trusted, or should be flagged in CounterfactualTracker as degraded

3. This README gets a status-line update: `**Status:** COMPLETE — <commit SHA>`.

## Changelog on this folder

- 2026-04-21: Campaign planned, folder created, Track B session prompts drafted.
