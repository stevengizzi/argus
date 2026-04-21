# ARGUS Development Campaign — Master Sprint Plan

> **This document is a process template, not a rolling sprint queue.** It describes the
> workflow choreography (protocols, skills, agents) to invoke for each class of sprint. The
> live sprint queue and current status live in `docs/roadmap.md` and `CLAUDE.md` ("Active
> Sprint" section). Do not treat the per-sprint entries below as the current plan — they were
> written during Sprint 28 planning and represent the sprint cadence pattern, not current
> sprint allocations.
>
> From Sprint 21.5 to Full Vision — every step mapped
> March 29, 2026 | Based on Unified Vision Roadmap v2.8 + Metarepo Workflow System v1.2
> Last template refresh: Sprint 28 planning (2026-03-29). Current live sprint state as of
> 2026-04-21: between sprints; 22 shadow variants collecting CounterfactualTracker data; next
> planned sprint is 31B (Research Console / Variant Factory). See `CLAUDE.md` "Active Sprint"
> for authoritative state.

---

## 1. How to Use This Document

This document maps every sprint in the ARGUS roadmap to its exact workflow choreography. It does NOT contain the content of sprint specs, implementation prompts, or review prompts — those are generated fresh during each sprint's planning conversation using the metarepo templates. What this document provides is the **sequence of actions, protocols, skills, and agents** to invoke for each sprint, so you never have to think about *process* during execution.

**Before each sprint:** Find the sprint in this document. Read its entry. Follow the steps in order.

**Before each phase gate:** Find the gate protocol in Section 10. Run it.

**When something unexpected happens:** Check Section 2 (Sprint Type Cheat Sheets) for the standard response pattern, then check the sprint entry for any special handling.

**Key to annotations:**
- **[Claude.ai]** — Action happens in a Claude.ai conversation (this project or ARGUS project)
- **[Claude Code]** — Action happens in Claude Code against the ARGUS repo
- **[You]** — Manual action required from you (save a file, review a screenshot, make a judgment call)

**Metarepo artifacts referenced:**

| Category | Artifacts Used |
|----------|---------------|
| **Protocols** | `sprint-planning.md`, `adversarial-review.md`, `strategic-check-in.md`, `tier-3-review.md`, `codebase-health-audit.md`, `impromptu-triage.md`, `in-flight-triage.md` |
| **Templates** | `sprint-spec.md`, `spec-by-contradiction.md`, `implementation-prompt.md`, `review-prompt.md`, `design-summary.md`, `decision-entry.md` |
| **Skills** | `close-out.md`, `review.md`, `diagnostic.md`, `doc-sync.md`, `canary-test.md` |
| **Agents** | `@reviewer` (Tier 2 automated review) |

---

## 2. Sprint Type Cheat Sheets

Every sprint in this campaign is classified into one of four types. The type determines the base choreography. Sprint-specific entries in Sections 4–9 note any deviations.

### Type A: Backend-Dominant

**When:** Pure backend work, no meaningful UI changes, no architectural risk.
**Workflow modes:** Standard plan→build→review cycle.
**Estimated sessions:** 2–4

```
CHOREOGRAPHY:

1. [Claude.ai] Sprint Planning — protocol: sprint-planning.md
   Phase A: Think → Phase B: Design Summary → Phase C: Generate → Phase D: Verify
   [You] Save design summary + all artifacts immediately after each generation

1.5 [Claude.ai] Open Work Journal — paste handoff prompt from Phase D
    into a fresh conversation. Keep open for the duration of the sprint.
    Bring issues here as they arise. See: in-flight-triage.md

2. [Claude Code] Session 1 — paste implementation prompt
   → implementation → tests → close-out skill (close-out.md)
   [You] Save close-out report

3. [Claude Code] Tier 2 Review — fresh session or @reviewer agent
   → review skill (review.md) → CLEAR or ESCALATE
   If ESCALATE → go to step 6

4. [Claude Code] Session 2..N — repeat steps 2–3 for each session

5. [Claude Code] Doc Sync — skill: doc-sync.md
   → update all docs on checklist → produce sync report
   [You] Review sync report, approve any Tier A compressions

6. [Claude.ai] Tier 3 Review (if ESCALATE or sprint complete)
   — protocol: tier-3-review.md
   → PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE
```

---

### Type B: Mixed Backend + Frontend

**When:** Sprint has both backend logic AND a UI deliverable.
**Workflow modes:** Standard cycle for backend sessions + Iterative Judgment Loop for frontend sessions.
**Estimated sessions:** 4–8 (2–3 backend, 2–5 frontend)

```
CHOREOGRAPHY:

1. [Claude.ai] Sprint Planning — protocol: sprint-planning.md
   Phase A: Think (include visual spec for UI deliverables — describe
   layout, reference existing Command Center pages, note specific visual
   elements to verify after implementation)
   Flag: Iterative Judgment Loop for frontend sessions
   Phase B: Design Summary → Phase C: Generate → Phase D: Verify
   [You] Save design summary + all artifacts

1.5 [Claude.ai] Open Work Journal — paste handoff prompt from Phase D
    into a fresh conversation. See: in-flight-triage.md

2. [Claude Code] Backend Session(s) — paste implementation prompt
   → implementation → tests → close-out skill
   [You] Save close-out report

3. [Claude Code] Tier 2 Review per backend session → CLEAR or ESCALATE

4. [Claude Code] Frontend Session 1 — paste implementation prompt
   (prompt includes visual spec reference)
   → implementation → tests → screenshot
   [You] Take screenshot, compare to visual spec, note deviations
   → close-out skill (include visual deviations in Notes for Reviewer)

5. [Claude Code] Tier 2 Review for frontend — includes visual verification
   Reviewer checks: does screenshot match spec? Visual regressions on
   adjacent pages?

6. [Claude Code] Frontend Fix Session(s) — if deviations found
   → fix prompt addressing specific visual issues
   → screenshot → compare → close-out
   REPEAT steps 5–6 until visual spec is met (budget 1–3 fix sessions)

7. [Claude Code] Doc Sync — skill: doc-sync.md

8. [Claude.ai] Tier 3 Review — protocol: tier-3-review.md
```

**Key difference from Type A:** Frontend sessions are shorter and more numerous. The screenshot→compare→fix loop is built into the plan, not treated as a failure. Budget 2–3x sessions vs. equivalent backend work for the frontend portion.

---

### Type C: Architecture-Shifting

**When:** Sprint refactors core architecture, changes data models, introduces new integrations, or has a Roadmap Contradiction Note.
**Workflow modes:** Adversarial review (mandatory) + base Type A or B choreography.
**Estimated sessions:** 4–10 (varies widely)

```
CHOREOGRAPHY:

1. [Claude.ai] Sprint Planning — protocol: sprint-planning.md
   Phase A: Think (extra emphasis on edge cases, failure modes,
   integration points, migration paths)
   Flag: Adversarial Review (mandatory for Type C)
   Flag: Iterative Judgment Loop (if sprint includes UI)
   Phase B: Design Summary → Phase C: Generate → Phase D: Verify
   [You] Save design summary + all artifacts

1.5 [Claude.ai] Open Work Journal — paste handoff prompt from Phase D
    into a fresh conversation. See: in-flight-triage.md

2. [Claude.ai] Adversarial Review — protocol: adversarial-review.md
   *** SEPARATE conversation from planning ***
   Paste: Sprint Spec + Specification by Contradiction + Architecture doc
   Work through ALL probing angles:
     → Assumption mining
     → Failure mode analysis
     → Future regret (3-month and 6-month horizon)
     → Specification gaps
     → Integration stress
   Outcome A: "Confirmed — proceed" → continue to step 3
   Outcome B: Issues found → revise sprint package, re-run Phase C/D
   [You] Save adversarial review findings

3. [Claude Code] Session 1..N — implementation with close-out
   (same as Type A or Type B depending on UI involvement)

4. [Claude Code] Tier 2 Review per session → CLEAR or ESCALATE
   Escalation threshold is LOWER for Type C — err toward ESCALATE

5. [Claude Code] Doc Sync — skill: doc-sync.md
   Architecture document update is MANDATORY for Type C sprints

6. [Claude.ai] Tier 3 Review — protocol: tier-3-review.md
   *** MANDATORY for Type C (not conditional on ESCALATE) ***
   Extra focus: did the implementation match the adversarial review's
   confirmed design? Were any of the reviewed failure modes encountered?
```

**Key difference from Type A/B:** The adversarial review before implementation is non-negotiable. Tier 3 review is mandatory (not conditional). Architecture doc update is mandatory.

---

### Type D: Research / Experiment

**When:** The sprint's deliverable is validated knowledge, not (just) working code. Multi-day experiments, statistical analysis, go/no-go decisions.
**Workflow modes:** Research-sprint variant with stage gates and pre-defined success criteria.
**Estimated sessions:** 3–8 (implementation) + 1–2 (analysis)

```
CHOREOGRAPHY:

1. [Claude.ai] Sprint Planning — protocol: sprint-planning.md
   Phase A: Think — MUST define:
     → Research question (what are we trying to learn?)
     → Success criteria (what result means "go"?)
     → Failure criteria (what result means "no-go"?)
     → Methodology (how will we answer the question?)
     → Stage gates (checkpoints within the experiment)
   Phase B: Design Summary (include all criteria above)
   Phase C: Generate — Implementation prompts are organized by STAGE,
   not just by session. Each stage has its own success gate.
   Phase D: Verify
   [You] Save design summary + all artifacts

1.5 [Claude.ai] Open Work Journal — paste handoff prompt from Phase D
    into a fresh conversation. See: in-flight-triage.md

2. [Claude.ai] Adversarial Review — protocol: adversarial-review.md
   (RECOMMENDED for Type D — the methodology must be sound)
   Focus: Is the statistical approach valid? Are the success criteria
   meaningful? Could we fool ourselves with this methodology?

3. [Claude Code] Stage 1 Session(s) — implementation + close-out
   [You] Evaluate stage 1 results against stage gate criteria
   → Pass: proceed to stage 2
   → Fail: diagnose, possibly revise methodology

4. [Claude Code] Stage 2..N Session(s) — repeat with stage gates

5. [Claude Code] Tier 2 Review — at minimum after final stage
   Focus: methodology correctness, not just code correctness

6. [Claude Code] Doc Sync — skill: doc-sync.md

7. [Claude.ai] Analysis & Decision Conversation
   NOT a Tier 3 review — this is a dedicated decision conversation.
   Present results, evaluate against pre-defined criteria, make the
   go/no-go or findings decision. Log as DEC entry.

8. [Claude.ai] Tier 3 Review — protocol: tier-3-review.md
   Includes: does the decision change the roadmap? Update accordingly.
```

**Key difference from other types:** Stage gates within the sprint. Pre-defined success/failure criteria. A dedicated analysis conversation separate from the standard review. The goal is knowledge, not just code.

---

## 3. Campaign Overview

### 3.1 All Sprints at a Glance

| Sprint | Name | Type | Modes | Est. Sessions | Est. Days | Adversarial? | Gate After? | Status |
|--------|------|------|-------|---------------|-----------|--------------|-------------|--------|
| **Phase 5: Foundation Completion** | | | | | | | | |
| 21.5 | Live Integration | A | standard | 2–3 | 2 | No | No | ✅ |
| 21.7 | FMP Scanner Integration | B | iterative-judgment | 3–5 | 2 | No | No | ✅ |
| 22 | AI Layer MVP | B | adversarial, iterative-judgment | 4–6 | 3 | **Yes** | No | ✅ |
| 23 | NLP Catalyst + Universe Manager | B | iterative-judgment | 4–6 | 3 | No | No | ✅ |
| 24 | Setup Quality Engine + Dynamic Sizer | B | adversarial, iterative-judgment | 5–7 | 3–4 | **Yes** | **Phase 5 Gate** | ✅ |
| **Phase 6: Strategy Expansion** | | | | | | | | |
| 25 | The Observatory | B | iterative-judgment | 13–18 | 4–5 | No | No | ✅ |
| 26 | Red-to-Green + Pattern Library Foundation | B | iterative-judgment | 3–5 | 2–3 | No | No | ✅ |
| 27 | BacktestEngine Core | A | standard | 4–6 | 2 | No | No | ✅ |
| 21.6 | Backtest Re-Validation + Execution Logging | A | standard | 3–5 | 2 | No | No | ✅ |
| **27.5** | **Evaluation Framework** | **A** | **standard** | **6** | **2** | **No** | **No** | ✅ |
| **27.6** | **Regime Intelligence** | **A** | **standard** | **12** | **2** | **No** | **No** | ✅ |
| 27.65 | Market Session Safety + Operational Fixes | A | standard | 6 | 1 | No | No | ✅ |
| **27.7** | **Counterfactual Engine** | **A** | **standard** | **7** | **1** | **No** | **No** | ✅ |
| 27.75 | Paper Trading Operational Hardening | A | standard | 2 | 1 | No | No | ✅ |
| 27.8 | Operational Cleanup + Validation Tooling | A | standard | 3 | 1 | No | No | ✅ |
| 27.9 | VIX Regime Intelligence | A | standard | 6 | 1 | No | No | ✅ |
| 27.95 | Broker Safety + Overflow Routing | A | standard | 5 | 2 | No | No | ✅ |
| **28** | **Learning Loop V1** | **C** | **adversarial, iterative-judgment** | **10–11** | **4–5** | **Yes** | **No** | ✅ |
| **28.5** | **Exit Management** | **B** | **iterative-judgment** | **2–3** | **2** | **No** | **No** | ✅ |
| 29 | Pattern Expansion I | B | iterative-judgment | 3–5 | 2–3 | No | No | ✅ |
| 29.5 | Post-Session Operational Sweep | A | standard | 7 | 1 | No | No | ✅ |
| 32 | Parameterized Templates + Experiment Pipeline (merged 32+32.5) | C | adversarial, iterative-judgment | 8 | 5–7 | **Yes** | No | — |
| 31A | Pattern Expansion III | B | iterative-judgment | 5–7 | 3 | No | **Phase 6 Gate** | — |
| 30 | Short Selling Infrastructure + Parabolic Short (deferred) | B | iterative-judgment | 5–7 | 3 | No | No | — |
| 31.5 | Parallel Sweep Infrastructure | B | iterative-judgment | 3–5 | 2 | No | No | — |
| 31B | Research Console (deferred per DEC-379) | B | iterative-judgment | 3–5 | 2 | No | No | — |
| **Phase 7: Controlled Experiment** | | | | | | | | |
| 33 | Statistical Validation Framework | B | adversarial, iterative-judgment | 5–7 | 3–4 | **Yes** | No | — |
| **33.5** | **Adversarial Stress Testing** | **A** | **standard** | **5** | **3** | **No** | **No** | — |
| 34 | ORB Family Systematic Search | D | research, adversarial | 5–8 | 4–5 | **Yes** | No | — |
| 35 | Ensemble Performance Analysis | D | research | 3–5 | 2–3 | No | **Phase 8 GATE (GO/NO-GO)** | — |
| **Phase 9: Ensemble Scaling** | | | | | | | | |
| 36 | Cross-Family Search (VWAP + Momentum) | B | iterative-judgment | 5–7 | 4–5 | No | No | — |
| 37 | Cross-Family Search (Remaining) | B | iterative-judgment | 5–7 | 4–5 | No | No | — |
| 38a | Ensemble Orchestrator V2 (Backend) | C | adversarial | 4–6 | 3 | **Yes** | No | — |
| 38b | Synapse (Frontend) | B | iterative-judgment, research-first | 6–10 | 4 | No | No | — |
| 39a | Ensemble WebSocket Backend | A | standard | 2–4 | 2 | No | No | — |
| 39b | Real-Time Synapse + Page Evolutions | B | iterative-judgment | 6–10 | 4 | No | **Phase 9 Gate** | — |
| **Phase 10: Full Vision** | | | | | | | | |
| 40 | Learning Loop V2 (Ensemble Edition) | B | iterative-judgment | 4–6 | 4–5 | No | No | — |
| 41 | Continuous Discovery Pipeline | B | iterative-judgment | 4–6 | 3–4 | No | No | — |
| 42 | Performance Workbench | B | iterative-judgment | 5–8 | 4–5 | No | **Phase 10 Gate** | — |

**Totals:** ~35 sprints (including sub-sprints) | ~155–210 sessions | ~17–22 weeks estimated

*Note: 5 new sprint slots added by DEC-357/DEC-358 (Sprints 27.5, 27.6, 27.7, 32.5, 33.5). Sprint 32.5 merged into Sprint 32 per April 1, 2026 planning session — Sprint 32 now delivers both parameterized templates and experiment infrastructure. Impromptu sprints 27.65, 27.75, 27.8, 27.9, 27.95 added during Phase 6 for operational hardening. Sprint 28.5 (Exit Management) added during Sprint 28 planning. Sprint 28 reclassified from Type B to Type C with mandatory adversarial review (ConfigProposalManager introduces config modification pipeline).*

---

### 3.2 Estimated Calendar Timeline

Based on the roadmap's per-sprint duration estimates. Start date: March 5, 2026. Calendar dates are approximate — actual pace depends on session throughput and paper trading schedule.

| Sprint | Start (est.) | End (est.) | Notes |
|--------|-------------|------------|-------|
| 21.5 | Mar 5 | Mar 7 | ✅ Complete |
| 21.7 | Mar 7 | Mar 9 | ✅ Complete |
| 22 | Mar 10 | Mar 13 | ✅ Complete |
| 23 | Mar 13 | Mar 16 | ✅ Complete (includes 23.05–23.9) |
| 24 | Mar 13 | Mar 16 | ✅ Complete (includes 24.1, 24.5) |
| **Phase 5 Gate** | **Mar 17** | **Mar 17** | ✅ Strategic check-in complete |
| 25 | Mar 17 | Mar 18 | ✅ Complete (The Observatory) |
| 25.5–25.9 | Mar 18 | Mar 23 | ✅ Complete (operational fixes + resilience) |
| 26 | Mar 21 | Mar 22 | ✅ Complete (Red-to-Green + Pattern Library Foundation) |
| 27 | Mar 22 | Mar 22 | ✅ Complete (BacktestEngine Core) |
| **Amendments** | **Mar 23** | **Mar 23** | ✅ DEC-357, DEC-358 adopted |
| 21.6 | Mar 23 | Mar 23 | ✅ Complete (Backtest Re-Validation + Execution Logging) |
| **27.5** | **Mar 23** | **Mar 24** | ✅ Complete (Evaluation Framework) |
| **27.6** | **Mar 24** | **Mar 24** | ✅ Complete (Regime Intelligence — 12 sessions) |
| 27.65 | Mar 24 | Mar 25 | ✅ Complete (Market Session Safety) |
| **27.7** | **Mar 25** | **Mar 25** | ✅ Complete (Counterfactual Engine) |
| 27.75 | Mar 26 | Mar 26 | ✅ Complete (Paper Trading Hardening) |
| 27.8 | Mar 26 | Mar 26 | ✅ Complete (Operational Cleanup) |
| 27.9 | Mar 26 | Mar 26 | ✅ Complete (VIX Regime Intelligence) |
| 27.95 | Mar 26 | Mar 28 | ✅ Complete (Broker Safety + Overflow Routing) |
| **28** | **late Mar** | **early Apr** | **Learning Loop V1 (Type C, 10–11 sessions)** |
| **28.5** | **Apr** | **Apr** | **Exit Management (~2 days)** |
| 29 | Mar 30–31 | Mar 31 | ✅ Pattern Expansion I |
| 29.5 | Mar 31–Apr 1 | Apr 1 | ✅ Post-Session Operational Sweep |
| **32** | **Apr** | **Apr–May** | **Parameterized Templates + Experiment Pipeline (merged 32+32.5, 8 sessions)** |
| 31A | May | May | Pattern Expansion III |
| **Phase 6 Gate** | **May** | **May** | Strategic check-in + live trading decision gate |
| 30 | May–Jun | Jun | Short Selling + Parabolic Short (deferred) |
| 31.5 | Jun | Jun | Parallel Sweep Infrastructure |
| 33 | Jun | Jun | Statistical Validation Framework |
| **33.5** | **Jun** | **Jun** | **Adversarial Stress Testing (DEC-358)** |
| 34 | Jun–Jul | Jul | ORB Systematic Search; may need cloud burst |
| 35 | Jul | Jul | Ensemble Performance Analysis |
| **Phase 8 GATE** | **Jul** | **Jul** | **GO/NO-GO — pivotal decision** |
| 36–39b | Jul–Aug | Aug | Only if GO (Ensemble Scaling) |
| **Phase 9 Gate** | **Aug** | **Aug** | Strategic check-in + codebase health audit |
| 40–42 | Aug–Sep | Sep | Full Vision sprints |
| **Phase 10 Gate** | **Sep** | **Sep** | Final strategic check-in |

**Total calendar estimate:** ~20–24 weeks (March 5 – August/September 2026). Sprint 21.5 through 27.95 completed in ~24 calendar days (March 5–28, 2026). Future dates are approximate — actual pace depends on session throughput and paper trading schedule.

---

### 3.3 Dependency Map

```
Phase 5 (Linear Chain — each sprint depends on the previous):

  21.5 ──→ 21.7 ──→ 22 ──→ 23 ──→ 24
  (live)   (scanner) (AI)  (NLP)  (quality)
                                      │
                                      ▼
                                 PHASE 5 GATE

Phase 6 (Linear Chain — includes amendment infrastructure + operational sprints):

  25 ──→ 26 ──→ 27 ──→ 21.6 ──→ 27.5 ──→ 27.6 ──→ 27.65 ──→ 27.7 ──→ 27.75→27.8→27.9→27.95
  (obs)  (R2G)  (BE)   (reval)  (eval)   (regime) (safety)  (cntfct) (operational hardening)
                                                                                    │
                                                                                    ▼
                                              28 ──→ 28.5 ──→ 29 ──→ 29.5 ──→ 32 ──→ 31A
                                              (learn) (exit)  (exp-I) (ops)   (tmpl+registry) (exp-III)
                                                                                                     │
                                                                                                     ▼
                                                                                                PHASE 6 GATE
                                                                                                     │
                                                                                                     ▼
                                                                                          30 ──→ 31.5 ──→ 31B
                                                                                          (short) (sweep)  (console)

Phase 7 (Linear Chain):

  33 ──→ 33.5 ──→ 34
  (stats) (stress)  (ORB search)

Phase 8 (Linear Chain):

  33 ──→ 33.5 ──→ 34 ──→ 35
  (stats) (stress) (experiment) (analysis)
                                    │
                                    ▼
                               PHASE 8 GATE ★★★
                               (GO/NO-GO — everything after depends on this)
                                    │
                              ┌─────┴─────┐
                              │           │
                             GO        NO-GO
                              │           │
                              ▼           ▼
                         Phase 9    Continue Phase 6
                                    artisanal approach

Phase 9 (Linear with sub-sprint decomposition):

  36 ──→ 37 ──→ 38a ──→ 38b ──→ 39a ──→ 39b
  (VWAP)  (all)  (orch) (synapse) (ws)  (rt-synapse)
                                            │
                                            ▼
                                       PHASE 9 GATE

Phase 10 (Linear Chain):

  40 ──→ 41 ──→ 42
  (learn) (discover) (workbench)
                        │
                        ▼
                   PHASE 10 GATE (Full Vision)
```

**Cross-Phase Dependencies:**

| Dependency | Description |
|-----------|-------------|
| Phase 6 requires Phase 5 | Strategies need quality filtering (Sprint 24) and AI layer (Sprint 22) |
| 27.5 requires 27 | Evaluation Framework builds on BacktestEngine |
| 27.6 requires 27.5 | RegimeMetrics in MultiObjectiveResult designed for multi-dimensional vectors |
| 27.7 requires 27.6 | Counterfactual positions tagged with RegimeVector |
| 28 requires 27.95 | Learning Loop consumes evaluation framework (27.5), regime vectors (27.6), counterfactual data (27.7), and broker safety infrastructure (27.95) |
| 28.5 requires 28 | Exit Management acts on Learning Loop data about exit variance |
| 32 requires 27.5 + 27.7 | Sprint 32 (merged) consumes MultiObjectiveResult + CounterfactualTracker; templates define parameter space |
| 33.5 requires 32 | Stress testing is a PromotionPipeline gate (PromotionPipeline now in Sprint 32) |
| Phase 8 requires Phase 7 | The experiment (Sprint 34) needs sweeps (31), templates, and experiment infrastructure (all in Sprint 32) |
| 32 pulled forward into Phase 6 | Longs need parameter tuning before adding short selling (April 1 strategic review) |
| Phase 9 requires Phase 8 GO | If NO-GO, Phase 9 does not execute |
| Sprint 38b requires Three.js research | A mini-discovery session before implementation (see Sprint 38b choreography) |

**Potential Parallelism Windows:**

| Window | What Could Overlap | Conditions |
|--------|-------------------|------------|
| Phase 6 (post-gate) | Sprint 30 could overlap with Sprint 31.5/31B | After Phase 6 Gate, short selling and sweep infra are independent |
| Sprint 38a + 38b prep | Three.js mini-discovery during 38a implementation | Research conversation doesn't block backend work |
| Sprint 39a + 39b prep | Frontend planning during backend WebSocket work | Planning doesn't block implementation |

---

## 4. Phase 5: Foundation Completion (Sprints 21.5–24)

*Completes live integration, adds market data scanning, begins AI layer. Target: ~2–3 weeks.*

---

### Sprint 21.5: Live Integration (COMPLETE - March 5, 2026)

**Type:** A (Backend-Dominant) | **Modes:** Standard
**Duration:** ~2 days remaining | **Sessions:** 2–3
**Depends on:** Nothing (already in progress)
**Adversarial review:** No
**Delivers:** First full market day paper session, closeout procedures

**Choreography:**

Since this sprint is already in progress, pick up from current state:

1. **[Claude Code]** Complete remaining sessions (Blocks C+D per existing sprint package)
   → Implementation → tests → close-out skill (`close-out.md`)
   → **[You]** Save close-out reports

2. **[Claude Code]** Tier 2 Review per session
   → `review.md` skill or `@reviewer` agent in fresh session
   → CLEAR → proceed | ESCALATE → Tier 3

3. **[Claude Code]** Doc Sync — `doc-sync.md`
   → Update: Project Knowledge (live status), Decision Log, Risk Register (live trading risks), Sprint Roadmap
   → **[You]** Review sync report

4. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`
   → Sprint completion review
   → Focus: Are live integration procedures validated? Any risks from paper trading session results?

---

### Sprint 21.7: FMP Scanner Integration

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~2 days | **Sessions:** 3–5 (2 backend, 1–3 frontend)
**Depends on:** Sprint 21.5 complete (live system running)
**Adversarial review:** No
**Delivers:** FMP integration, dynamic symbol selection, Pre-Market Watchlist panel on Dashboard

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - FMP API integration design (authentication, rate limits, data format)
     - Symbol selection algorithm (volume spike, gap detection, catalyst tagging)
     - Pre-Market Watchlist panel layout on Dashboard (visual spec: where on page, what data shown, how symbols are grouped)
     - Session decomposition: backend FMP integration → backend symbol selector → frontend watchlist panel
   - Flag: Iterative Judgment Loop (watchlist panel is new UI)
   - **Phase B** — Design Summary → **[You]** save immediately
   - **Phase C** — Generate: Sprint Spec, Spec by Contradiction, Session Breakdown, Implementation Prompts (×3), Review Prompts (×3), Escalation Criteria, Regression Checklist, Doc Update Checklist
   - **Phase D** — Verify against design summary
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — FMP API integration + data pipeline
   → Implementation prompt → implementation → tests → close-out → **[You]** save

3. **[Claude Code]** Tier 2 Review — Session 1

4. **[Claude Code]** Session 2: Backend — Symbol selection algorithm
   → Close-out → **[You]** save

5. **[Claude Code]** Tier 2 Review — Session 2

6. **[Claude Code]** Session 3: Frontend — Pre-Market Watchlist panel
   → Implementation prompt includes visual spec from Phase A
   → Implementation → tests → **[You]** screenshot Dashboard
   → Compare to visual spec → note deviations → close-out (include deviations)

7. **[Claude Code]** Tier 2 Review — Session 3 (includes visual check)
   → If deviations: plan fix session

8. **[Claude Code]** Session 4 (if needed): Frontend fix session
   → Fix prompt addressing visual deviations → screenshot → close-out

9. **[Claude Code]** Doc Sync — `doc-sync.md`
   → Update: Decision Log (FMP integration decisions, DEC-258/259), Architecture doc (new scanner pipeline section), Project Knowledge

10. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion)

---

### Sprint 22: AI Layer MVP

**Type:** B (Mixed Backend + Frontend) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~3 days | **Sessions:** 4–6 (2–3 backend, 2–3 frontend)
**Depends on:** Sprint 21.7 complete
**Adversarial review:** **YES** — new external integration (Claude API), security-relevant (API keys), changes system architecture (AI layer added)
**Delivers:** Claude API integration, live Copilot pane, approval workflow for AI suggestions

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Claude API integration architecture (model selection, prompt construction, context injection)
     - API key management and security model
     - Copilot pane UX design (slide-out panel vs. dedicated page per DEC-170)
     - System state read-access architecture (what data does the AI see?)
     - Approval workflow for AI suggestions (how does the operator accept/reject?)
     - Failure modes: what happens when Claude API is down? Rate limited? Returns garbage?
     - Session decomposition: backend API integration → backend approval workflow → frontend Copilot pane
   - Flag: Adversarial Review (new external dependency, security-relevant)
   - Flag: Iterative Judgment Loop (Copilot pane is complex new UI)
   - Synthetic Stakeholder check: "Roleplay as the operator during a live trading session. What would frustrate you about the Copilot? What would be missing?"
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation** from planning
   - Paste: Sprint Spec + Spec by Contradiction + Architecture doc
   - **Specific focus areas for this sprint:**
     - API key storage and rotation — how are keys managed? Is there a fallback?
     - Claude API failure modes — timeout, rate limit, malformed response, context too large
     - Approval workflow edge cases — what if operator is away? Queue overflow? Stale suggestions?
     - Read-access boundaries — can the AI ever accidentally influence execution without approval?
     - Cost control — Claude API costs at trading-session frequency
   - Outcome: confirmed → proceed, or revisions → update sprint package
   - **[You]** Save adversarial findings

3. **[Claude Code]** Session 1: Backend — Claude API integration + context injection
   → Close-out → **[You]** save

4. **[Claude Code]** Tier 2 Review — Session 1

5. **[Claude Code]** Session 2: Backend — Approval workflow + system state read access
   → Close-out → **[You]** save

6. **[Claude Code]** Tier 2 Review — Session 2

7. **[Claude Code]** Session 3: Frontend — Copilot pane activation
   → Visual spec reference in prompt → implementation → **[You]** screenshot
   → Close-out (with visual assessment)

8. **[Claude Code]** Tier 2 Review — Session 3 (visual verification)

9. **[Claude Code]** Session 4+ (if needed): Copilot pane polish (iterative judgment loop)
   → Fix visual deviations → screenshot → close-out

10. **[Claude Code]** Doc Sync — `doc-sync.md`
    → Update: Architecture doc (new AI Layer section), Decision Log, Risk Register (Claude API dependency risk), Project Knowledge

11. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — new integration)
    → Extra focus: does the implementation match the adversarial-reviewed design?

---

### Sprint 23: NLP Catalyst + Universe Manager (DEC-263)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3 days | **Sessions:** 4–6 (2–3 backend, 2–3 frontend)
**Depends on:** Sprint 22 complete (uses Claude API for narrative generation)
**Adversarial review:** No (builds on proven Claude API integration from Sprint 22)
**Delivers:** Universe Manager with broad-universe monitoring (DEC-263), strategy-declared universe filters, SEC EDGAR + FMP catalyst pipeline, Pre-Market Intelligence Brief, catalyst badges, AI debrief narratives. May decompose into Sprint 23 + 23.5 during planning.

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Universe Manager architecture: subscription scope (3,000–5,000 symbols), symbol batching, memory budget
     - Strategy YAML `universe_filter` and `behavioral_triggers` schema design
     - IndicatorEngine full-universe computation model (DEC-263)
     - Early-exit evaluation routing for non-matching symbols
     - NLP pipeline architecture: SEC EDGAR + FMP data sources → Claude API analysis → catalyst tags
     - Pre-Market Intelligence Brief layout and content (visual spec: where accessible, what sections, how catalyst cards render)
     - Catalyst badge design for Pre-Market Watchlist panel (visual spec: badge shape, color, information density)
     - The Debrief page evolution (AI narrative generation)
     - DEC-164 requirements and constraints
     - Session decomposition: backend data pipeline → backend catalyst engine → frontend Intelligence Brief + badges → frontend Debrief narrative
   - Flag: Iterative Judgment Loop (Intelligence Brief is new visual, catalyst badges are new UI elements)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–2: Backend — NLP data pipeline + catalyst engine
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Session 3: Frontend — Pre-Market Intelligence Brief + catalyst badges
   → Visual spec reference → implementation → **[You]** screenshot → close-out

4. **[Claude Code]** Tier 2 Review — Session 3 (visual verification)

5. **[Claude Code]** Session 4: Frontend — Debrief narrative integration + polish
   → Screenshot → close-out

6. **[Claude Code]** Session 5+ (if needed): Fix sessions per iterative judgment loop

7. **[Claude Code]** Doc Sync — `doc-sync.md`
   → Update: Architecture doc (NLP pipeline), Decision Log, Project Knowledge

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion)

---

### Sprint 24: Setup Quality Engine + Dynamic Sizer

**Type:** B (Mixed Backend + Frontend) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 5–7 (3 backend, 2–4 frontend)
**Depends on:** Sprint 23 complete (quality scoring uses catalyst data)
**Adversarial review:** **YES** — changes the signal→execution pipeline, integrates with Risk Manager, affects trade decisions
**Delivers:** 0–100 quality scoring, AI-graded signals, dynamic position sizing, quality badges across Command Center

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Quality scoring algorithm design (what factors, what weights, how AI grading works)
     - Dynamic sizer integration with Risk Manager (how quality score maps to position size)
     - DEC-239 requirements
     - UI deliverables across FOUR pages (Trades, Orchestrator, Dashboard, Debrief) — visual spec for each
     - This is the highest UI surface area sprint in Phase 5 — budget accordingly
     - Session decomposition: backend quality engine → backend dynamic sizer + Risk Manager integration → frontend quality badges (Trades + Orchestrator) → frontend Dashboard quality distribution + Debrief scatter plot
   - Flag: Adversarial Review (touches signal→execution pipeline, Risk Manager integration)
   - Flag: Iterative Judgment Loop (UI across 4 pages)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Specific focus areas:**
     - Quality scoring edge cases — what happens at score boundaries (39 vs. 40, 84 vs. 85)?
     - Dynamic sizer failure modes — what if quality engine returns invalid score? What if Risk Manager and sizer disagree?
     - Signal pipeline timing — does quality scoring add latency to execution? Is that acceptable for day trading?
     - Integration stress — does the quality filter change existing strategy behavior? Regression risk to four active strategies?
   - Outcome: confirmed or revisions
   - **[You]** Save findings

3. **[Claude Code]** Session 1: Backend — Quality scoring engine
   → Close-out → **[You]** save

4. **[Claude Code]** Tier 2 Review — Session 1

5. **[Claude Code]** Session 2: Backend — Dynamic sizer + Risk Manager integration
   → Close-out → **[You]** save
   → **Canary test recommended:** Existing strategies must produce identical signals (before quality filtering) as they did pre-sprint

6. **[Claude Code]** Tier 2 Review — Session 2

7. **[Claude Code]** Session 3: Frontend — Quality badges on Trades + live scoring on Orchestrator
   → Visual spec reference → **[You]** screenshot both pages → close-out

8. **[Claude Code]** Tier 2 Review — Session 3 (visual verification on both pages)

9. **[Claude Code]** Session 4: Frontend — Dashboard Signal Quality Distribution + Debrief scatter plot
   → Visual spec reference → **[You]** screenshot both pages → close-out

10. **[Claude Code]** Tier 2 Review — Session 4 (visual verification)

11. **[Claude Code]** Session 5+ (if needed): Fix sessions for UI polish

12. **[Claude Code]** Doc Sync — `doc-sync.md`
    → Update: Architecture doc (quality engine, dynamic sizer), Decision Log, Risk Register, Project Knowledge
    → **This is the last sprint in Phase 5 — extra attention to doc currency**

13. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — pipeline change)
    → Verify: quality engine doesn't alter existing strategy behavior (only filters post-signal)

---

### Phase 5 Gate

**Trigger:** Sprint 24 complete
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression

**[Claude.ai]** Strategic Check-In Conversation:

1. **Progress review:** All 5 sprints delivered? AI layer working? Quality filtering visible? Paper trading running smoothly?
2. **Assumption audit:** Are Phase 5 assumptions still valid? FMP data sufficient? Claude API costs manageable? Quality scoring producing useful differentiation?
3. **Scope assessment:** Is the Phase 6 scope (strategy expansion) still correct? Do we need more or fewer strategies?
4. **Velocity calibration:** How many sessions per sprint on average? Were estimates accurate? Adjust Phase 6 estimates if needed.
5. **Risk review:** Any new risks? Has paper trading revealed issues? Historical data sufficiency — start thinking about this NOW for Phase 8.
6. **Decision patterns:** Review DECs from Phase 5. Any decisions causing friction?

**[Claude Code]** Documentation Compression:

1. Archive Phase 5 DECs into "Phase 5 Decision Archive" — remove from active Decision Log
2. Keep only cross-cutting DECs in active log
3. Update Architecture doc to reflect Phase 5 final state
4. Update Project Knowledge — compress Phase 5 status into "completed" summary
5. Run doc-sync Step 4 (Tier A Compression Check)

**[You]** Review and approve all compression changes.

**Output:** Updated roadmap, revised estimates for Phase 6, velocity adjustments, new RSK/DEC entries if needed.

---

## 5. Phase 6: Strategy Expansion — Artisanal (Sprints 25–31)

*Opens with The Observatory for operational visibility, then expands the strategy roster to 12+ hand-crafted patterns. Adds the Learning Loop for self-monitoring, exit management for P&L optimization, and parameterized strategy templates + experiment infrastructure (Sprints 32/32.5, pulled forward per April 1 strategic review). Includes infrastructure sprints 27.5–27.95 that transform Sprint 28 (Learning Loop V1) from basic weight tuning into intelligent system analysis. Short selling deferred to post-Phase 6 Gate. Target: ~7–9 weeks.*

---

### Sprint 25: The Observatory

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 13 implementation + 5 visual-fix contingency = up to 18
**Depends on:** Phase 5 Gate complete (Sprint 24.5 evaluation telemetry on main)
**Adversarial review:** No (read-only visualization layer, no architectural decisions affecting trading)
**Delivers:** Observatory page (Command Center page 8) with Funnel/Radar/Matrix/Timeline views, keyboard-first navigation, detail panel with live candlestick charts, session vitals, debrief mode

**Context:** Phase 5 Gate strategic check-in identified that the system has sophisticated evaluation telemetry but no way to observe pipeline behavior immersively. Operator couldn't tell why zero trades were occurring. Observatory addresses this — operational visibility is prerequisite to adding more strategies.

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - Sprint package generated March 17, 2026 (35 artifacts)
   - Full spec, session breakdown, 13 impl prompts, 13 review prompts
   - **[You]** Saved to `docs/sprints/sprint-25/`

2. **[Claude.ai]** Work Journal — paste `work-journal-handoff.md`

3. **[Claude Code]** S1: Backend — Observatory API endpoints (ObservatoryService, 4 REST routes)
   → Close-out + @reviewer → **[You]** update work journal

4. **[Claude Code]** S2: Backend — Observatory WebSocket (live pipeline updates)
   → Close-out + @reviewer → **[You]** update work journal

5. **[Claude Code]** S3: Frontend — Page shell, routing, keyboard system
   → Close-out + @reviewer → **[You]** visual review + update work journal
   → S3f (if visual fixes needed)

6. **[Claude Code]** S4a: Detail panel core + condition grid + strategy history
   → S4b: Candlestick chart + data hooks
   → Close-out + @reviewer → **[You]** visual review
   → S4f (if visual fixes needed)

7. **[Claude Code]** S5a: Matrix view core (condition heatmap)
   → S5b: Virtual scrolling + live sort + keyboard
   → Close-out + @reviewer → **[You]** visual review
   → S5f (if visual fixes needed)

8. **[Claude Code]** S6a: Three.js scene setup (tier discs, orbit controls)
   → S6b: Symbol particles (InstancedMesh, LOD labels, interactions)
   → Close-out + @reviewer → **[You]** visual review + **PERFORMANCE CHECK (30fps with 3K particles)**
   → S6f (if visual fixes needed)
   → **Human decision point:** Does the funnel feel right?

9. **[Claude Code]** S7: Radar view (camera animation from funnel to bottom-up)

10. **[Claude Code]** S8: Timeline view (strategy lanes, event marks)
    → S8f (if visual fixes needed)

11. **[Claude Code]** S9: Session vitals + debrief mode
    → S9f (if visual fixes needed)

12. **[Claude Code]** S10: Integration polish + keyboard refinement
    → Full suite test run → final @reviewer
    → **Human decision point:** Full walkthrough — does the experience match design intent?

13. **[Claude Code]** Doc Sync — `doc-sync.md`
    → Update: project-knowledge, architecture, roadmap, CLAUDE.md, sprint-history, dec-index, decision-log

---

### Sprint 26: Red-to-Green + Pattern Library Foundation

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~2–3 days | **Sessions:** 3–5 (2 backend, 1–3 frontend)
**Depends on:** Sprint 25 complete
**Adversarial review:** No (follows established strategy-addition pattern)
**Delivers:** Fifth active strategy, Pattern Library card, Orchestrator + Dashboard updates

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Red-to-Green strategy spec (state machine, entry/exit logic, parameters)
     - VectorBT sweep design (parameter ranges, optimization targets)
     - Replay Harness validation plan
     - Walk-forward methodology
     - Pattern Library card visual spec
     - Session decomposition: backend strategy + sweep → validation → frontend cards
   - Flag: Iterative Judgment Loop (Pattern Library card, Dashboard updates)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package (include `.claude/rules/backtesting.md` constraints)
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — Strategy implementation + VectorBT sweep
   → Close-out + @reviewer

3. **[Claude Code]** Session 2: Backend — Replay Harness validation + walk-forward
   → Close-out + @reviewer

4. **[Claude Code]** Session 3: Frontend — Pattern Library card + Orchestrator/Dashboard updates
   → Visual spec → **[You]** screenshot → close-out + @reviewer

5. **[Claude Code]** Session 4+ (if needed): Frontend fix sessions

6. **[Claude Code]** Doc Sync → **[Claude.ai]** Tier 3 Review

---

### Sprint 27: BacktestEngine Core ✅ COMPLETE (March 22, 2026)

SynchronousEventBus, HistoricalDataFeed (Databento OHLCV-1m + Parquet cache), BacktestEngine (production-code backtesting, bar-level fill model, multi-day orchestration, scanner simulation, strategy factory, CLI). Walk-forward `oos_engine` integration. 85 new pytest tests. 6 sessions, all CLEAR.

---

### Sprint 21.6: Backtest Re-Validation ✅ COMPLETE (March 23, 2026)

Re-validated all 7 strategies using BacktestEngine with Databento OHLCV-1m. ExecutionRecord logging for slippage calibration (DEC-358 §5.1). BacktestEngine risk_overrides (DEC-359). VectorBT dual file naming. Revalidation harness script. Full-universe Parquet cache populated (24,321 symbols, 153 months, 44.73 GB). +41 pytest tests.

---

### Sprint 27.5: Evaluation Framework ✅ COMPLETE (March 23–24, 2026)

MultiObjectiveResult, ConfidenceTier, EnsembleResult, RegimeMetrics. Comparison API (compare, pareto_frontier, soft_dominance, is_regime_robust). StrategySlippageModel calibration. +106 pytest tests. 6 sessions + 1 cleanup.

---

### Sprint 27.6: Regime Intelligence ✅ COMPLETE (March 24, 2026)

RegimeVector (6 dimensions, 18 fields). RegimeClassifierV2 composing V1 + 4 calculators (Breadth, Correlation, Sector Rotation, Intraday Character). RegimeHistoryStore (SQLite). Config-gated. Observatory wiring (Sprint 27.6.1). +171 tests (160 pytest + 11 Vitest). 12 sessions.

---

### Sprint 27.65: Market Session Safety ✅ COMPLETE (March 24–25, 2026)

Flatten-pending guard (DEC-363), graceful shutdown cancellation (DEC-364), periodic reconciliation (DEC-365), bracket amendment on slippage (DEC-366), optional concurrent limits (DEC-367), IntradayCandleStore (DEC-368). 6 sessions.

---

### Sprint 27.7: Counterfactual Engine ✅ COMPLETE (March 25, 2026)

TheoreticalFillModel (shared bar-level exit logic). CounterfactualTracker (shadow position tracking). CounterfactualStore (SQLite). SignalRejectedEvent. FilterAccuracy. Shadow strategy mode. +105 tests. 6 sessions + 1 cleanup. 0 new DECs.

---

### Sprint 27.75: Paper Trading Operational Hardening ✅ COMPLETE (March 26, 2026)

ThrottledLogger. Paper trading config overrides (10x risk reduction). Reconciliation logging consolidation.

---

### Sprint 27.8: Operational Cleanup + Validation Tooling ✅ COMPLETE (March 26, 2026)

ExitReason.RECONCILIATION. Config-gated orphan cleanup. Bracket exhaustion detection. Per-strategy health reporting. `scripts/validate_all_strategies.py` batch revalidation.

---

### Sprint 27.9: VIX Regime Intelligence ✅ COMPLETE (March 26, 2026)

VIXDataService (yfinance daily VIX+SPX, 5 derived metrics, SQLite cache). 4 VIX calculators. RegimeVector 6→11 fields. VixRegimeCard dashboard widget. REST endpoints. +75 tests.

---

### Sprint 27.95: Broker Safety + Overflow Routing ✅ COMPLETE (March 26–28, 2026)

Broker-confirmed reconciliation (DEC-369). Overflow routing to CounterfactualTracker (DEC-375). Stop resubmission cap (DEC-372). Bracket revision-rejected handling (DEC-373). Fill dedup (DEC-374). Startup zombie cleanup (DEC-376). 9 new DECs (DEC-369–377).

---

### Sprint 28: Learning Loop V1 ✅ COMPLETE (March 28–29, 2026)

**Type:** C (Architecture-Shifting) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Actual:** 2 days | **Sessions:** 14 (8 backend, 4 frontend, 2 visual-fix)
**Depends on:** Sprint 27.95 complete (Counterfactual Engine data accumulating, Evaluation Framework available, Quality Engine operational)
**Adversarial review:** **YES** — ConfigProposalManager introduces a config modification pipeline. Any module that can programmatically modify live trading configuration warrants adversarial review.
**Delivers:** OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningReport, LearningStore, LearningService, ConfigProposalManager, config change history, REST API (trigger + retrieve + approve/dismiss/revert), CLI entry point, auto post-session trigger, Performance page Learning Insights panel + Strategy Health Bands + Correlation Matrix, Dashboard summary card

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - OutcomeCollector design: unified read layer across trades, counterfactual_positions, quality_history
     - WeightAnalyzer: Spearman rank correlation per quality dimension vs P&L outcomes
     - ThresholdAnalyzer: missed-opportunity and correct-rejection rates per grade
     - CorrelationAnalyzer: pairwise strategy return correlation
     - ConfigProposalManager: YAML write pipeline with Pydantic validation, `max_change_per_cycle` guard, revert capability, config change history table
     - Auto post-session trigger: analysis runs after EOD flatten
     - Approval/dismiss UX with decision history for V2/V3 training data
     - Strategy Health Bands: observational only (no automated throttle/boost — deferred to Sprint 40)
     - Regime analysis: adaptive — overall always runs, per-regime when sample size >= configurable minimum
     - UI on Performance page: Learning Insights panel, Strategy Health Bands, Correlation Matrix heatmap
     - UI on Dashboard: summary card with pending recommendations count
     - Session decomposition: backend data layer → backend analyzers → backend config proposal + service → backend REST + CLI + trigger → frontend Performance page panels → frontend Dashboard card
   - Flag: Adversarial Review (config modification pipeline)
   - Flag: Iterative Judgment Loop (Performance page panels are significant new UI)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

1.5 **[Claude.ai]** Open Work Journal — paste handoff prompt from Phase D

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Specific focus areas:**
     - ConfigProposalManager safety: Can a single bad report cause dangerous config changes? Are guards sufficient?
     - Pydantic validation: What happens if proposed weights are invalid? Edge cases at min/max bounds?
     - `max_change_per_cycle` guard: Is ±0.10 per weight per report conservative enough?
     - Revert capability: Does revert restore exact previous state? Race conditions with session start?
     - Auto post-session trigger: What if analysis fails mid-run? Partial results?
     - Advisory-only enforcement: Is there any path where V1 automatically applies changes without human approval?
     - Data sufficiency: Spearman correlation needs meaningful sample sizes — what happens with 5 trades?
   - Outcome: confirmed → proceed, or revisions → update sprint package
   - **[You]** Save adversarial findings

3. **[Claude Code]** Sessions 1–2: Backend — OutcomeCollector + WeightAnalyzer + ThresholdAnalyzer + CorrelationAnalyzer
   → Close-out per session → Tier 2 review per session

4. **[Claude Code]** Sessions 3–4: Backend — LearningReport + LearningStore + LearningService + ConfigProposalManager
   → Close-out per session → Tier 2 review per session

5. **[Claude Code]** Sessions 5–6: Backend — REST API + CLI + auto post-session trigger + config change history
   → Close-out per session → Tier 2 review per session

6. **[Claude Code]** Session 7: Backend — Integration wiring + approval/dismiss lifecycle
   → Close-out → Tier 2 review

7. **[Claude Code]** Session 8: Frontend — Performance page Learning Insights panel + Strategy Health Bands + Correlation Matrix
   → Visual spec reference → **[You]** screenshot Performance page → close-out

8. **[Claude Code]** Tier 2 Review — Session 8 (visual verification)

9. **[Claude Code]** Session 9: Frontend — Dashboard summary card + polish
   → Visual spec → **[You]** screenshot Dashboard → close-out

10. **[Claude Code]** Session 10+ (if needed): Frontend fix sessions

11. **[Claude Code]** Doc Sync — `doc-sync.md`
    → **Architecture doc update is MANDATORY** (Learning Loop section, ConfigProposalManager)
    → Update: Decision Log, Project Knowledge

12. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C)
    → Focus: ConfigProposalManager safety, advisory-only enforcement, data sufficiency for recommendations

---

### Sprint 28.5: Exit Management

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~2 days | **Sessions:** 2–3
**Depends on:** Sprint 28 complete
**Adversarial review:** No (follows established Order Manager patterns)
**Delivers:** Trailing stops, partial profit-taking, regime-adaptive targets, time-based exit escalation

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Trailing stop mechanism: Order Manager integration, Risk Manager awareness
     - Partial profit-taking: split exit at T1/T2 with trail on remainder
     - Regime-adaptive targets: tighter in choppy regimes, wider in trending
     - Time-based exit escalation: progressive stop tightening with hold time
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — Trailing stop + partial profit-taking + escalation
   → Close-out → Tier 2 review

3. **[Claude Code]** Session 2: Backend — Integration + validation
   → Close-out → Tier 2 review

4. **[Claude Code]** Doc Sync → **[Claude.ai]** Tier 3 Review

---

### Sprint 29: Pattern Expansion I

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~2–3 days | **Sessions:** 4–6 (3–4 backend incl. PatternParam + 4 patterns, 1–2 frontend)
**Depends on:** Sprint 28.5 complete
**Adversarial review:** No
**Delivers:** 4 additional pattern modules (ABCD, Dip-and-Rip, HOD Break, Gap-and-Go per DEC-378), PatternParam structured type (DEF-088), Pattern Library cards. Optionally Pre-Market High Break.

**Choreography:**

1. **[Claude.ai]** Sprint Planning
2. **[Claude Code]** Sessions 1–3: One backend session per strategy
3. **[Claude Code]** Session 4: Frontend — Pattern Library cards
4. **[Claude Code]** Fix sessions (if needed)
5. **[Claude Code]** Doc Sync → **[Claude.ai]** Tier 3 Review

---

### Sprint 30: Short Selling Infrastructure + Pattern Expansion II

> **NOTE (April 1, 2026):** Sprint 30 deferred until after Phase 6 Gate. Sprint 32 (Parameterized Strategy Templates) pulled forward — long strategies need tuning before adding short selling. The choreography below remains valid; execution timing has shifted.

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3 days | **Sessions:** 3–5 (2–3 backend, 1–2 frontend)
**Depends on:** Sprint 29 complete
**Adversarial review:** No (short selling follows established Risk Manager patterns)
**Delivers:** Short selling infrastructure (locate/borrow tracking, inverted risk logic, uptick rule compliance), Parabolic Short strategy, 1–2 additional long patterns, Dashboard short exposure indicator activated

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Short selling infrastructure design: locate tracking, inverted risk logic (stop above entry, target below), short-specific Risk Manager rules, uptick rule compliance (SSR detection), short exposure limits
     - Parabolic Short strategy spec: parabolic extension detection, volume exhaustion, reversal candle patterns
     - 1–2 additional long pattern modules (ABCD Reversal, Sympathy Play, or others from planned roster) if velocity allows
     - Dashboard Short Exposure indicator activation (infrastructure built in Sprint 26)
     - Session decomposition: backend short selling infrastructure → backend Parabolic Short + additional patterns → frontend Pattern Library cards + short exposure activation
   - Flag: Iterative Judgment Loop (Parabolic Short card, short exposure indicator)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — Short selling infrastructure
   → Close-out → Tier 2 review

3. **[Claude Code]** Session 2: Backend — Parabolic Short + additional patterns (implementation + sweep + validation)
   → Close-out → Tier 2 review
   → Performance benchmarks in every prompt (backtesting.md rules)

4. **[Claude Code]** Session 3: Frontend — Pattern Library cards + short exposure indicator activation
   → Visual spec → **[You]** screenshot → close-out

5. **[Claude Code]** Tier 2 Review — Session 3 (visual verification)

6. **[Claude Code]** Session 4+ (if needed): Frontend fix sessions

7. **[Claude Code]** Doc Sync — `doc-sync.md`
   → Update: Architecture doc (short selling infrastructure section), Decision Log

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`

---

### Phase 6 Gate

**Trigger:** Sprint 31A complete (DEC-379)
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression + Codebase Health Audit

This is the most significant non-Phase-8 gate because **live trading with real capital could begin during or after Phase 6** (per roadmap).

**[Claude.ai]** Strategic Check-In Conversation:

1. **Progress review:** 15 long-only strategies active with parameterized templates? Learning Loop working? Experiment Registry producing controlled results? Correlation monitoring producing useful data? Evaluation Framework, Regime Intelligence, and Counterfactual Engine all operational?
2. **Paper trading assessment:** Sharpe > 2.0? Positive expectancy across strategies? No catastrophic drawdowns?
3. **Live trading readiness:** Are you confident enough in the system to deploy real capital? If yes → schedule live-minimum deployment during Phase 7 or Phase 8. Log as DEC entry. (CPA consultation removed per DEC-380; tax intelligence built into ARGUS as post-revenue automation.)
5. **Post-gate readiness:** Is the short selling infrastructure worth building now? Is the long-side performance sufficient? Are parameterized templates producing measurable improvements?
6. **Historical data sufficiency:** RESOLVED (DEC-358) — XNAS.ITCH + XNYS.PILLAR provide 96 months of OHLCV-1m at $0. No purchase needed.
7. **Velocity calibration:** Update session estimates for Phase 7–8 based on Phase 5–6 actuals.

**[Claude.ai]** Codebase Health Audit — `codebase-health-audit.md`
- First audit of the campaign (Phase 6 is ~sprint 27, meeting the "every 4–6 sprints" cadence)
- Focus: architectural coherence after adding 7+ strategies, test coverage, naming consistency, deferred item accumulation

**[Claude Code]** Documentation Compression:
- Archive Phase 5–6 DECs
- Update Architecture doc to Phase 6 final state
- Compress Project Knowledge
- Run Tier A Compression Check

**Output:** Updated roadmap, live-trading decision, velocity adjustments, codebase health report.

---

## 6. Phase 7: Infrastructure Unification (Sprint 32)

*Parameterized strategy templates and experiment infrastructure delivered across Sprint 32 (merged from original 32+32.5) and Sprint 32.5 (Experiment Pipeline Completion + Visibility). BacktestEngine already complete (Sprint 27). Research Console deferred to post-32 per DEC-379. Both sprints complete as of April 1, 2026.*

---

### Sprint 32: Parameterized Templates + Experiment Pipeline (merged 32+32.5)

> **STATUS (April 1, 2026): COMPLETE.** Sprint 32 delivered the core experiment pipeline. Sprint 32.5 delivered completion and visibility (exit params as variant dimensions, BacktestEngine all 7 patterns, Shadow Trades tab, Experiments 9th page, Allocation Intelligence vision). Phase 7 Gate now pending.
>
> **NOTE (April 1, 2026, planning):** Sprint 32 originally absorbed Sprint 32.5 scope per planning session. Sprint 32.5 was subsequently run as a separate 8-session sprint due to scope remaining after Sprint 32.

**Type:** C (Architecture-Shifting) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~5–7 days | **Sessions:** 8 (4–5 backend, 2–3 frontend)
**Depends on:** Sprint 29.5 complete
**Adversarial review:** **YES** — YAML→constructor wiring, variant spawning architecture, promotion evaluator autonomy. Strategies must see no behavioral difference when experiments disabled.
**Delivers:** YAML→constructor wiring, generic pattern factory, parameter fingerprint, VariantSpawner, ExperimentRegistry (SQLite), ExperimentRunner (backtest pre-filter), PromotionEvaluator (autonomous), PromotionCohort, ExperimentQueue, CLI + REST API. Config-gated via `experiments.enabled`.

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Template architecture: how does a template generate strategy instances that behave identically to hand-coded strategies?
     - Configuration schema design (YAML or dataclass — make the decision, log as DEC)
     - Parameter slots vs. filter slots — type system
     - Template validation (parameter ranges, filter compatibility)
     - Template registry (discovery, instantiation)
     - Refactoring plan: how are existing 10–11 strategies converted to templates without behavior change?
     - Pattern Library evolution visual spec: Template View (parameter ranges with sliders), Instance Browser, Template Explorer form
     - **Critical invariant:** The Risk Manager, Orchestrator, and Order Manager must see NO difference between a template-generated instance and a hand-coded strategy
     - Session decomposition: backend template system + schema → backend refactor existing strategies → backend validation (template instances produce identical results to originals) → frontend Pattern Library template gallery
   - Flag: Adversarial Review (strategy architecture refactor, Roadmap Contradiction Note)
   - Flag: Iterative Judgment Loop (Pattern Library evolves from gallery to template browser)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Specific focus areas:**
     - Template-to-instance contract: Does a template instance behave EXACTLY like the original strategy? How to prove it?
     - Schema flexibility vs. safety: Can a template configuration produce an invalid strategy? How is this prevented?
     - Refactoring risk: What happens to live paper trading during the refactor? Feature flags? Dual-path validation?
     - Future regret: Does this template architecture support the Phase 8 ensemble vision? Can it handle 500+ instantiations?
     - Integration stress: Does anything downstream (Risk Manager, Orchestrator, Order Manager) need to change?
   - Outcome: confirmed or revisions
   - **[You]** Save findings

3. **[Claude Code]** Session 1: Backend — Template system + configuration schema + registry
   → Close-out → **[You]** save

4. **[Claude Code]** Tier 2 Review — Session 1

5. **[Claude Code]** Session 2: Backend — Refactor existing strategies as templates
   → **Canary test:** Run all 10–11 strategies through both old path and template path, compare results exactly
   → Close-out → **[You]** save

6. **[Claude Code]** Tier 2 Review — Session 2

7. **[Claude Code]** Session 3: Backend — Template validation + edge cases
   → Close-out → **[You]** save

8. **[Claude Code]** Tier 2 Review — Session 3

9. **[Claude Code]** Session 4: Frontend — Pattern Library template gallery
   → Visual spec → **[You]** screenshot → close-out

10. **[Claude Code]** Tier 2 Review — Session 4 (visual verification)

11. **[Claude Code]** Session 5+ (if needed): Frontend polish

12. **[Claude Code]** Doc Sync — `doc-sync.md`
    → **Architecture doc update is MANDATORY** (strategy architecture section rewritten)
    → Create `.claude/rules/strategy-templates.md` — codify template system constraints


13. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C)

---

### Phase 7 Gate

**Trigger:** Sprint 32 complete (merged 32+32.5)
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression

**[Claude.ai]** Strategic Check-In Conversation:

1. **Progress review:** Templates validated? Experiment Registry operational? Promotion Pipeline stages tested? Anti-fragility logic wired?
2. **Data sufficiency:** RESOLVED (DEC-358). XNAS.ITCH + XNYS.PILLAR provide 96 months of OHLCV-1m at $0. Exchange-specific HistoricalDataFeed mode built in Sprint 33.5.
3. **Experiment pipeline calibration:** Confirm Sprint 32 cohort sizes, veto windows, and kill switch thresholds based on paper trading experience. Review overnight compute capacity — is sequential worker sufficient for Sprint 33, or should Sprint 31 parallelism be prioritized?
4. **Phase 8 readiness:** Is the BacktestEngine fast enough for the controlled experiment (Sprint 34)? Do the templates cover the ORB family adequately for systematic search?
5. **Velocity calibration:** Update estimates for Phase 8.
6. **Risk review:** Any new risks from Phase 7 implementation? Cloud burst infrastructure ready?

**[Claude Code]** Documentation Compression:
- Archive Phase 5–7 DECs
- Architecture doc updated to Phase 7 final state (BacktestEngine, templates, Research Console, Experiment Registry, Promotion Pipeline)
- Compress Project Knowledge
- Verify `.claude/rules/` files: `backtesting.md`, `backtest-engine.md`, `strategy-templates.md` all current

---

## 7. Phase 8: Controlled Experiment (Sprints 33–35)

*The proving ground. Everything before this is valuable regardless. Everything after depends on Sprint 34's results. Target: ~3 weeks (includes Sprint 33.5 stress testing).*

---

### Sprint 33: Statistical Validation Framework

**Type:** B (Mixed Backend + Frontend) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 5–7 (3 backend, 2–4 frontend)
**Depends on:** Phase 7 Gate complete
**Note:** Scope reduced from original plan — evaluation framework (Sprint 27.5), experiment storage (Sprint 32, merged from 32.5), and aggregate views already exist. Sprint 33 focuses purely on statistical methods.
**Adversarial review:** **YES** — if the statistical methodology is wrong, the entire Phase 8 experiment is worthless. This is the highest-stakes adversarial review in the campaign.
**Delivers:** FDR correction (Benjamini-Hochberg), minimum trade count thresholds, three-way data splits (96 months of data available), smoothness prior, Research Console Validation Dashboard

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - FDR correction implementation (Benjamini-Hochberg specifics)
     - Minimum trade count thresholds per micro-strategy (what's the floor?)
     - Three-way data split infrastructure (train / selection / validation) — exact date ranges based on available data
     - Smoothness prior design (neighboring parameter/filter cells must correlate — how is this measured? what threshold?)
     - Out-of-sample ensemble validation metrics
     - Walk-forward at ensemble level
     - Research Console Validation Dashboard visual spec: Data Split Visualizer (timeline bar), FDR Report View (p-value histogram), Smoothness Heatmap overlay (toggle raw vs. filtered)
     - Session decomposition: backend FDR + trade count thresholds → backend data split + smoothness prior → backend ensemble validation metrics → frontend Validation Dashboard
   - Flag: Adversarial Review (**critical** — statistical methodology correctness)
   - Flag: Iterative Judgment Loop (Validation Dashboard visualizations)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **This is the most important adversarial review in the campaign.** If the math is wrong here, Sprint 32's results are meaningless.
   - **Specific focus areas:**
     - FDR correction: Is Benjamini-Hochberg appropriate for correlated test statistics? (The micro-strategies ARE correlated.) Should we use Benjamini-Yekutieli instead?
     - Multiple comparisons: At 500K–2M combinations, even FDR correction may not be enough. What's the effective significance threshold?
     - Smoothness prior: Could this reject valid strategies that genuinely exist only in narrow parameter windows? Is it too aggressive or too lenient?
     - Data split integrity: Is there information leakage between train/selection/validation? How is this prevented?
     - Minimum trade count: Too low → noise passes. Too high → valid rare strategies get filtered. What's the right balance?
     - Base rate: Given the total number of tests, what's the expected number of false discoveries even WITH FDR correction? Is this acceptable?
   - Outcome: confirmed or revisions (revisions are LIKELY here — expect iteration)
   - **[You]** Save findings. If revisions, update sprint package before implementation.

3. **[Claude Code]** Session 1: Backend — FDR correction + trade count thresholds
   → Close-out → **[You]** save

4. **[Claude Code]** Tier 2 Review — Session 1

5. **[Claude Code]** Session 2: Backend — Three-way data split + smoothness prior
   → Close-out → **[You]** save

6. **[Claude Code]** Tier 2 Review — Session 2

7. **[Claude Code]** Session 3: Backend — Ensemble-level validation metrics + walk-forward
   → Close-out → **[You]** save

8. **[Claude Code]** Tier 2 Review — Session 3

9. **[Claude Code]** Session 4: Frontend — Data Split Visualizer + FDR Report View
   → Visual spec → **[You]** screenshot → close-out

10. **[Claude Code]** Session 5: Frontend — Smoothness Heatmap overlay
    → Visual spec → **[You]** screenshot (toggle raw vs. filtered) → close-out

11. **[Claude Code]** Tier 2 Reviews — Sessions 4–5 (visual verification)

12. **[Claude Code]** Doc Sync — `doc-sync.md`
    → Create `.claude/rules/statistical-validation.md` — codify validation constraints (FDR method, minimum trade counts, split methodology)

13. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — statistical foundation for Phase 8)

---

### Sprint 34: ORB Family Systematic Search

**Type:** D (Research / Experiment) | **Modes:** Research Sprint, Adversarial Review
**Duration:** ~4–5 days (compute-heavy) | **Sessions:** 5–8
**Depends on:** Sprint 33.5 complete
**Adversarial review:** **YES** — validating the experimental methodology before committing compute resources
**Delivers:** Either (a) a validated ensemble of 50–200 ORB micro-strategies that outperform hand-crafted, or (b) evidence that the approach doesn't work

**This is the most important sprint in the entire campaign.** The choreography follows Type D (Research) with explicit stage gates.

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md` **(Research Sprint Variant)**
   - **Phase A — Think:**
     - **Research question:** Does systematic parameter × filter search on the ORB Breakout template produce a validated micro-strategy ensemble that outperforms the hand-tuned ORB Breakout + ORB Scalp on out-of-sample data?
     - **Success criteria (define BEFORE the experiment):**
       - Ensemble Sharpe on out-of-sample > hand-crafted Sharpe on same period
       - Ensemble max drawdown on out-of-sample < hand-crafted max drawdown
       - At least 20 micro-strategies survive statistical validation
       - Smoothness prior confirms signal is not isolated spikes
       - P-value histogram shows spike near zero (real signal, not uniform noise)
     - **Failure criteria:**
       - Ensemble does not outperform hand-crafted on out-of-sample
       - Fewer than 10 micro-strategies survive validation
       - P-value histogram is uniform (no signal)
     - **Methodology:**
       - Stage 1: Coarse scan (vectorized, fast) — ~500K combinations screened
       - Stage 2: Focused BacktestEngine validation — ~50K surviving candidates
       - Stage 3: Statistical filtering (FDR, smoothness prior)
       - Stage 4: Ensemble out-of-sample validation
     - **Stage gates:**
       - After Stage 1: Do hot zones exist in the heatmap? If the landscape is flat → methodology concern, pause before Stage 2
       - After Stage 2: Do results cluster or are they random? If random → concern
       - After Stage 3: Do >10 candidates survive? If not → insufficient signal
       - After Stage 4: Success/failure against pre-defined criteria
     - **Compute plan:** Estimated hours, cloud burst configuration, cost estimate
     - Session decomposition: Session per stage (may need multiple sessions for Stage 1–2 if compute extends across days)
   - Flag: Research Sprint (stage gates, pre-defined criteria)
   - Flag: Adversarial Review (methodology validation)
   - **Phase B** — Design Summary → **[You]** save (include ALL criteria — this is your judgment anchor)
   - **Phase C** — Generate sprint package (implementation prompts organized by STAGE)
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Focus: the methodology, not the code.**
     - Could we fool ourselves with this methodology? What are the self-deception risks?
     - Are the success criteria too easy? Too hard?
     - Is the data split adequate for the number of tests being run?
     - Is Stage 1 (vectorized coarse scan) a valid proxy for Stage 2 (BacktestEngine)? Could it filter out real signal?
     - Are there look-ahead biases in the pipeline?
   - Outcome: confirmed or revisions
   - **[You]** Save findings

3. **[Claude Code]** Stage 1 Sessions: Coarse scan infrastructure + execution
   → Launch scan → monitor progress on Research Console
   → **[You]** At stage gate: examine heatmap. Do hot zones exist?
   → **Decision:** Proceed to Stage 2, or pause and diagnose
   → Close-out → **[You]** save

4. **[Claude Code]** Stage 2 Sessions: Focused BacktestEngine validation
   → Run surviving candidates through BacktestEngine
   → **[You]** At stage gate: examine clustering. Are results structured or random?
   → **Decision:** Proceed to Stage 3, or pause
   → Close-out → **[You]** save

5. **[Claude Code]** Stage 3 Session: Statistical filtering
   → Run FDR correction + smoothness prior
   → **[You]** At stage gate: examine FDR report, p-value histogram, smoothness overlay
   → **Decision:** Do >10 candidates survive? Proceed to Stage 4, or fail
   → Close-out → **[You]** save

6. **[Claude Code]** Stage 4 Session: Ensemble out-of-sample validation
   → Build ensemble from validated micro-strategies
   → Run on out-of-sample data
   → Compare to hand-crafted baseline
   → Close-out (include all metrics vs. pre-defined criteria) → **[You]** save

7. **[Claude Code]** Tier 2 Review — after Stage 4
   → Focus: methodology correctness (not just code), results vs. criteria

8. **[Claude Code]** Doc Sync — `doc-sync.md`

9. **[You]** Save all results, heatmaps, equity curves. These feed Sprint 35.

---

### Sprint 35: Ensemble Performance Analysis

**Type:** D (Research / Experiment) | **Modes:** Research Sprint
**Duration:** ~2–3 days | **Sessions:** 3–5
**Depends on:** Sprint 34 complete (uses Sprint 34 results as input)
**Adversarial review:** No (this is the analysis of already-collected results)
**Delivers:** Correlation Cluster Map, Regime Breakdown, Commission Impact Model, Go/No-Go Dashboard — and the **decision that determines the rest of the roadmap**

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md` **(Research Sprint Variant)**
   - **Phase A — Think:**
     - Analysis plan: correlation structure, capital efficiency, turnover/commissions, drawdown comparison, regime sensitivity
     - Go/No-Go Dashboard design: what metrics, what visual layout, what constitutes a clear visual verdict
     - Research Console Ensemble Analysis Suite visual spec: Correlation Cluster Map (force-directed graph), Regime Performance Breakdown (faceted chart), Commission Impact Model, Go/No-Go summary
     - Session decomposition: backend analysis engine (correlation, regime, commission models) → frontend visualization suite → analysis and decision
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — Correlation analysis + regime breakdown + commission model
   → Close-out → **[You]** save

3. **[Claude Code]** Tier 2 Review — Session 1

4. **[Claude Code]** Session 2: Frontend — Correlation Cluster Map + Regime Breakdown + Commission Impact + Go/No-Go Dashboard
   → Visual spec → **[You]** screenshot → close-out

5. **[Claude Code]** Tier 2 Review — Session 2 (visual verification)

6. **[Claude Code]** Session 3+ (if needed): Frontend polish

7. **[Claude Code]** Doc Sync — `doc-sync.md`

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint + phase completion)

---

### Phase 8 Gate — THE GO/NO-GO DECISION ★★★

**Trigger:** Sprint 35 complete
**Protocol:** Custom Gate Review (NOT a standard strategic check-in — this is bigger)

This is the pivotal decision of the entire campaign. Everything from Sprint 36 onward depends on the outcome.

**[Claude.ai]** Gate Review Conversation:

Start with:
```
"We are at the Phase 8 gate — the go/no-go decision for the ensemble vision.
Sprint 34 results and Sprint 35 analysis are complete. I need to make the
decision that determines whether we proceed to Phase 9 (ensemble scaling)
or continue with the Phase 6 artisanal approach.

Here are the results: [paste Sprint 34/35 key metrics]
Here are the pre-defined success criteria from Sprint 34 planning: [paste]
Here is the Go/No-Go Dashboard output: [paste or screenshot reference]"
```

**Work through:**

1. **Criteria evaluation:** For each pre-defined success criterion — met or not met? No ambiguity, no rationalization.
2. **Ensemble vs. hand-crafted comparison:** Sharpe, drawdown, win rate, profit factor — side by side.
3. **Statistical confidence:** Is the outperformance statistically significant? Or could it be noise?
4. **Regime robustness:** Does the ensemble work across regimes, or only in favorable conditions?
5. **Cost reality:** After commissions and turnover, is the edge real?
6. **Scaling feasibility:** If ORB works, will other families likely work too? Or are there ORB-specific reasons for success?

**Decision Outcomes:**

**GO:** The ensemble methodology is validated. Proceed to Phase 9.
- Log as DEC entry with full rationale and success metrics
- Update roadmap: Phase 9 sprints are active
- Sprint 36 planning begins immediately after the gate review

**NO-GO:** The ensemble methodology did not produce the desired results.
- Log as DEC entry with full rationale and failure analysis
- Decision fork:
  - **NO-GO (salvageable):** The methodology needs adjustment. Plan a revised Sprint 34 with specific changes. Phase 9 is delayed, not cancelled.
  - **NO-GO (fundamental):** The approach doesn't work for day trading. Phase 9 is cancelled. Continue Phase 6 artisanal approach. ARGUS remains strong — the ceiling is lower but the floor hasn't changed. BacktestEngine and Research Console remain valuable for individual strategy research.
- Update roadmap accordingly

**[You]** This decision cannot be delegated. Review the Gate Review conversation output, look at the Go/No-Go Dashboard, and make the call. Log it as a DEC entry.

---

## 8. Phase 9: Ensemble Scaling (Sprints 36–39)

*Extends the proven methodology across all families. Builds the Ensemble Orchestrator and Synapse. Target: ~3–4 weeks. ONLY executes if Phase 8 GO.*

---

### Sprint 36: Cross-Family Search (VWAP + Afternoon Momentum)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 5–7 (3 backend, 2–4 frontend)
**Depends on:** Phase 8 GO decision
**Adversarial review:** No (methodology proven in Sprint 33)
**Delivers:** VWAP and Afternoon Momentum micro-strategy ensembles, cross-family correlation analysis, Research Console Cross-Family View

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Apply Sprint 32 methodology to VWAP Reclaim and Afternoon Momentum templates
     - Same tiered sweep → statistical filtering → ensemble validation pipeline
     - Cross-family correlation analysis design
     - Research Console Cross-Family View visual spec: multi-family color-coded correlation cluster map, Family Contribution Chart (returns by family by regime)
     - Session decomposition: backend VWAP sweep + validation → backend Afternoon Momentum sweep + validation → backend cross-family correlation → frontend Cross-Family View + Contribution Chart
   - Flag: Iterative Judgment Loop (correlation map and contribution chart are new visualizations)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — VWAP sweep + statistical filtering + ensemble validation
   → Same stage-gate approach as Sprint 32 but compressed (methodology proven)
   → Close-out → **[You]** save

3. **[Claude Code]** Tier 2 Review — Session 1

4. **[Claude Code]** Session 2: Backend — Afternoon Momentum sweep + validation
   → Close-out → **[You]** save

5. **[Claude Code]** Tier 2 Review — Session 2

6. **[Claude Code]** Session 3: Backend — Cross-family correlation analysis
   → Close-out → **[You]** save

7. **[Claude Code]** Session 4: Frontend — Cross-Family View + Family Contribution Chart
   → Visual spec → **[You]** screenshot → close-out

8. **[Claude Code]** Tier 2 Review — Session 4 (visual verification)

9. **[Claude Code]** Session 5+ (if needed): Frontend polish

10. **[Claude Code]** Doc Sync — `doc-sync.md`

11. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion)
    → Focus: Are cross-family correlations low enough for ensemble diversification?

---

### Sprint 37: Cross-Family Search (Remaining Families)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 5–7 (3–4 backend, 2–3 frontend)
**Depends on:** Sprint 36 complete
**Adversarial review:** No
**Delivers:** All remaining family ensembles (Red-to-Green, Gap Fill, ABCD, etc.), full cross-family correlation map

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A:** Same pattern as Sprint 35 but for remaining families. Plan one backend session per family (or batch smaller families). Frontend: full strategy universe correlation map.
   - **Phase B–D:** Standard
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–3: Backend — Sweep + validate each remaining family
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Session 4: Frontend — Full correlation map update
   → Visual spec → **[You]** screenshot → close-out

4. **[Claude Code]** Tier 2 Review — Session 4 (visual verification)

5. **[Claude Code]** Session 5+ (if needed): Frontend polish

6. **[Claude Code]** Doc Sync — `doc-sync.md`

7. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`

---

### Sprint 38a: Ensemble Orchestrator V2 (Backend)

**Type:** C (Architecture-Shifting) | **Modes:** Adversarial Review
**Duration:** ~3 days | **Sessions:** 4–6
**Depends on:** Sprint 37 complete (needs all family ensembles)
**Adversarial review:** **YES** — replaces the core Orchestrator, handles hundreds of micro-strategies (Roadmap Contradiction Note: supersedes original Orchestrator V2 concept)
**Delivers:** Activation filtering, correlation-aware capital allocation, position consolidation, regime-dependent selection

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Activation filtering design: how are micro-strategy conditions evaluated? Pre-computed lookup tables?
     - Capital allocation across active micro-strategies: correlation-aware algorithm, shared capital pools for correlated strategies
     - Position consolidation: when 50 micro-strategies want to buy NVDA, how is the single position sized? How is aggregate conviction calculated?
     - Regime-dependent ensemble selection: how does the Learning Loop (Sprint 29) feed regime classification?
     - **Critical invariant:** The Orchestrator must handle 200–800 micro-strategies without latency impact on execution
     - Migration plan: how does the new Orchestrator replace the old one? Feature flags? Dual-path validation?
     - Session decomposition: activation filtering → capital allocation + position consolidation → regime integration + migration → validation
   - Flag: Adversarial Review (replaces core infrastructure, Roadmap Contradiction Note)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Specific focus areas:**
     - Latency: Does correlation-aware allocation add execution delay? Acceptable for day trading?
     - Position consolidation correctness: Is aggregate conviction mathematically sound? Edge cases (conflicting signals, partial fills)?
     - Migration safety: Can the old Orchestrator run alongside the new one for validation?
     - Scalability: What happens at 1,000+ micro-strategies? Memory, CPU, latency?
     - Failure modes: What if the correlation model is wrong? What if regime classification fails?
   - Outcome: confirmed or revisions
   - **[You]** Save findings

3. **[Claude Code]** Sessions 1–4: Backend implementation
   → Close-out per session → Tier 2 review per session
   → **Canary test before Session 1:** Capture current Orchestrator behavior on a reference set. After Sprint 38a, new Orchestrator must produce equivalent-or-better results.

4. **[Claude Code]** Doc Sync — `doc-sync.md`
   → **Architecture doc update MANDATORY** (Orchestrator section rewritten)

5. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C, core infrastructure replaced)

---

### Sprint 38b: Synapse (Frontend)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop, Research-First
**Duration:** ~4 days | **Sessions:** 6–10
**Depends on:** Sprint 38a complete (needs Ensemble Orchestrator for data), but Three.js research can happen during 38a
**Adversarial review:** No (frontend visualization, not architectural)
**Delivers:** Synapse page (page 10) — 3D strategy space, color/size/opacity encoding, correlation connections, navigation, grouping modes

**Special: Mini-Discovery before implementation.** The Synapse is the most visually complex component ARGUS has ever built. Before writing code, run a research conversation.

**Choreography:**

1. **[Claude.ai]** Mini-Discovery Conversation — (can overlap with Sprint 38a)
   - NOT a full discovery protocol — a focused research session on Three.js for data visualization
   - Explore: Three.js instanced mesh geometry for 500–800 nodes, spring physics for transitions, WebGL performance budgets, Zustand state management for 3D scene
   - Review examples of similar 3D data visualizations
   - Produce: Technical approach document (rendering strategy, state management, animation approach, performance targets)
   - **[You]** Save technical approach document

2. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:** (informed by mini-discovery output)
     - Three.js rendering architecture: instanced mesh for nodes, line geometry for correlations, shader-based color/opacity encoding
     - Grouping mode transitions: spring physics for smooth node rearrangement
     - Navigation: orbit controls, click-to-select, zoom-to-cluster
     - Info panel: slide-in on node click with micro-strategy details
     - REST endpoint for ensemble state (backend, coordinate with Sprint 38a)
     - **Performance target:** 60fps with 800 nodes, connections toggleable
     - Visual spec: detailed description of each grouping mode (by family, by time, by sector, by regime, by performance), color scheme, size encoding, opacity encoding
     - Session decomposition: backend REST endpoint → frontend scene setup + node rendering → frontend grouping modes + transitions → frontend navigation + info panel → frontend polish
   - Flag: Iterative Judgment Loop (**maximum** — 3D visualization requires extensive visual iteration)
   - Budget: 6–10 sessions (this is the most frontend-intensive sprint in the campaign)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

3. **[Claude Code]** Session 1: Backend — REST endpoint for ensemble state
   → Close-out → Tier 2 review

4. **[Claude Code]** Session 2: Frontend — Three.js scene setup + node rendering (basic)
   → **[You]** Screenshot: are nodes rendering? Correct positions? Correct colors?
   → Close-out

5. **[Claude Code]** Tier 2 Review — Session 2 (visual verification)

6. **[Claude Code]** Session 3: Frontend — Grouping modes + transition animations
   → **[You]** Screenshot/video each grouping mode. Transitions smooth?
   → Close-out

7. **[Claude Code]** Tier 2 Review — Session 3

8. **[Claude Code]** Session 4: Frontend — Correlation connections + navigation + info panel
   → **[You]** Screenshot: connections visible? Click-select working? Info panel content correct?
   → Close-out

9. **[Claude Code]** Tier 2 Review — Session 4

10. **[Claude Code]** Sessions 5–8: Frontend polish (iterative judgment loop)
    → Fix visual issues identified in screenshots
    → Performance testing (60fps with 800 nodes?)
    → Edge cases (empty constellation, single node, all nodes in one cluster)
    → Close-out per session

11. **[Claude Code]** Doc Sync — `doc-sync.md`

12. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`

---

### Sprint 39a: Ensemble WebSocket Backend

**Type:** A (Backend-Dominant) | **Modes:** Standard
**Duration:** ~2 days | **Sessions:** 2–4
**Depends on:** Sprint 38b complete
**Adversarial review:** No (WebSocket is well-understood pattern)
**Delivers:** WebSocket stream for ensemble state changes (activations, positions, allocations, health)

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A:** WebSocket architecture, event types, push frequency, reconnection handling
   - Standard Type A choreography
   - **Phase B–D:** Standard
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–3: Backend — WebSocket infrastructure + event pipeline
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Doc Sync — `doc-sync.md`

4. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion)

---

### Sprint 39b: Real-Time Synapse + Page Evolutions

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4 days | **Sessions:** 6–10
**Depends on:** Sprint 39a complete (needs WebSocket stream)
**Adversarial review:** No
**Delivers:** Real-time firing effects, timeline scrubber, Dashboard evolution (Ensemble Heartbeat, Family Activity Bars, Mini-Synapse), Orchestrator evolution (Activation Stream, Capital Treemap), Performance evolution (Contribution Attribution, Correlation Stability), Debrief evolution (ensemble narratives)

**This is the highest UI surface area sprint in the entire campaign — touching 5 pages + the Synapse.**

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Synapse real-time effects: firing pulse animation, holding glow, rejection flash, color encoding for P&L
     - Timeline scrubber: data model (store all events), playback controls, fast-forward compression
     - Dashboard evolution: Ensemble Heartbeat, Family Activity Bars, Mini-Synapse (simplified 2D) — visual specs for each
     - Orchestrator evolution: Activation Stream (real-time feed), Capital Allocation Treemap — visual specs
     - Performance evolution: Contribution Attribution (waterfall chart), Correlation Stability Monitor — visual specs
     - Debrief evolution: ensemble-scale AI narrative template
     - Session decomposition: frontend real-time firing + timeline scrubber (2–3 sessions) → frontend Dashboard evolution (1–2 sessions) → frontend Orchestrator evolution (1–2 sessions) → frontend Performance + Debrief evolution (1–2 sessions)
   - Flag: Iterative Judgment Loop (many visual components across many pages — maximum iteration expected)
   - Budget: 6–10 sessions with aggressive visual review after each
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–2: Frontend — Synapse real-time firing + timeline scrubber
   → **[You]** Screenshot/record: firing animation visible? Scrubber working? Performance acceptable?
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Session 3: Frontend — Dashboard evolution (Heartbeat, Activity Bars, Mini-Synapse)
   → **[You]** Screenshot Dashboard → close-out

4. **[Claude Code]** Session 4: Frontend — Orchestrator evolution (Activation Stream, Capital Treemap)
   → **[You]** Screenshot Orchestrator → close-out

5. **[Claude Code]** Session 5: Frontend — Performance + Debrief evolution
   → **[You]** Screenshot both pages → close-out

6. **[Claude Code]** Tier 2 Reviews — all sessions (visual verification)

7. **[Claude Code]** Sessions 6–8: Frontend polish across all pages
   → Close-out per session

8. **[Claude Code]** Doc Sync — `doc-sync.md`
   → **This is the last sprint in Phase 9 — extra attention to doc currency**

9. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint + phase completion)

---

### Phase 9 Gate

**Trigger:** Sprint 38b complete
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Codebase Health Audit (`codebase-health-audit.md`) + Documentation Compression

**[Claude.ai]** Strategic Check-In:
1. **Progress review:** Full ensemble operational in paper trading? Synapse working? All pages updated?
2. **Paper trading assessment at ensemble scale:** Are 20–60 micro-strategies activating per day as expected? Is the ensemble Sharpe tracking toward 3.0+?
3. **Performance assessment:** Is the system fast enough? Any latency issues with 200–800 micro-strategies?
4. **Phase 10 scope review:** Is the Learning Loop V2 scope still correct? Continuous Discovery Pipeline still needed?
5. **Velocity calibration:** Update estimates for Phase 10.

**[Claude.ai]** Codebase Health Audit — `codebase-health-audit.md`
- Second audit of the campaign (meeting "every 4–6 sprints" cadence)
- Focus: architectural coherence after massive scaling, test coverage on ensemble components, performance profiling, deferred debt accumulation

**[Claude Code]** Documentation Compression:
- Archive Phase 5–9 DECs (keep only active cross-cutting DECs)
- Architecture doc updated to Phase 9 final state
- Compress Project Knowledge
- Verify all `.claude/rules/` files current

**Output:** Updated roadmap, velocity adjustments, codebase health report, Phase 10 scope confirmation.

---

## 9. Phase 10: Full Vision (Sprints 39–41)

*The self-improving system. Ensemble learns, adapts, evolves. Target: ~2.5–3.5 weeks.*

---

### Sprint 40: Learning Loop V2 (Ensemble Edition)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 4–6 (2–3 backend, 2–3 frontend)
**Depends on:** Phase 9 Gate complete
**Adversarial review:** No (Learning Loop V1 exists from Sprint 29; V2 is an evolution, not a new architecture)
**Delivers:** Automated micro-strategy throttling/boosting, rolling recalibration, automatic retirement/promotion, Synapse lifecycle animations, Adaptation Timeline

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Throttle/boost automation: performance thresholds, response curves, risk limits
     - Rolling recalibration: frequency (every N trading days), methodology (re-run statistical validation on recent data)
     - Retirement criteria: when is a micro-strategy "dead"? Gradual vs. sudden?
     - Promotion pipeline: staging queue → human approval → activation
     - Synapse lifecycle animations: birth (fade in, grow), throttle (shrink), retirement (fade out, color shift to grey), boost (grow, brighten)
     - Adaptation Timeline visual spec: timeline showing additions, retirements, throttle/boost events, net ensemble metrics over time
     - Session decomposition: backend automation engine (throttle/boost/retire/promote) → backend recalibration pipeline → frontend lifecycle animations → frontend Adaptation Timeline
   - Flag: Iterative Judgment Loop (lifecycle animations are novel visual work)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–2: Backend — Automation engine + recalibration pipeline
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Session 3: Frontend — Synapse lifecycle animations
   → **[You]** Screenshot/record: birth animation visible? Decay visible? Retirement fade?
   → Close-out

4. **[Claude Code]** Session 4: Frontend — Adaptation Timeline on Research Console
   → **[You]** Screenshot → close-out

5. **[Claude Code]** Tier 2 Reviews — Sessions 3–4 (visual verification)

6. **[Claude Code]** Session 5+ (if needed): Polish

7. **[Claude Code]** Doc Sync — `doc-sync.md`

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`

---

### Sprint 41: Continuous Discovery Pipeline

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 4–6 (2–3 backend, 2–3 frontend)
**Depends on:** Sprint 39 complete (promotion pipeline needed for discoveries)
**Adversarial review:** No
**Delivers:** Overnight discovery background process, Discovery Feed, Staging Queue visualization (ghost nodes on Synapse), Discovery Heatmap, Morning intelligence brief integration

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Background discovery process: scheduling (overnight), parameter/filter space exploration strategy, validation pipeline
     - Discovery → staging → human review → activation flow
     - Morning intelligence brief integration: "Overnight Discovery" section
     - Discovery Feed visual spec: overnight results cards with approve/reject buttons
     - Staging Queue on Synapse: ghost nodes showing prospective positions
     - Discovery Heatmap visual spec: explored vs. unexplored vs. yielding regions of parameter space
     - Session decomposition: backend overnight pipeline + scheduling → backend staging queue + intelligence brief integration → frontend Discovery Feed + approve/reject UI → frontend ghost nodes + Discovery Heatmap
   - Flag: Iterative Judgment Loop (ghost nodes on Synapse, Discovery Heatmap)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–2: Backend — Discovery pipeline + staging + intelligence brief
   → Close-out per session → Tier 2 review per session

3. **[Claude Code]** Session 3: Frontend — Discovery Feed + approve/reject UI
   → **[You]** Screenshot → close-out

4. **[Claude Code]** Session 4: Frontend — Ghost nodes on Synapse + Discovery Heatmap
   → **[You]** Screenshot Synapse with ghost nodes + heatmap → close-out

5. **[Claude Code]** Tier 2 Reviews — Sessions 3–4 (visual verification)

6. **[Claude Code]** Session 5+ (if needed): Polish

7. **[Claude Code]** Doc Sync — `doc-sync.md`

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md`

---

### Sprint 42: Performance Workbench

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 5–8 (1 backend, 4–7 frontend)
**Depends on:** Sprint 40 complete
**Adversarial review:** No
**Delivers:** Customizable widget grid (react-grid-layout), drag/drop/resize, named layout tabs, full widget palette

**This sprint is almost entirely frontend.** Budget heavily for iterative visual work.

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - react-grid-layout integration
     - Widget palette design: which widgets, what data sources, what configurations
     - Two-stage build: Stage 1 = rearrangeable tab system, Stage 2 = full widget palette with drag-drop
     - Tab presets: "Morning Review," "Live Session," "Post-Session Analysis," "Weekly Deep Dive"
     - Session decomposition: backend widget data API (if needed) → frontend grid layout + tab system → frontend widget palette → frontend individual widget implementations (may need multiple sessions) → frontend polish
   - Flag: Iterative Judgment Loop (**maximum** — this is a UX-intensive sprint)
   - Budget: 5–8 sessions, mostly frontend
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package (Stage 1 and Stage 2 as separate session groups)
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — Widget data API endpoints (if not already covered by existing APIs)
   → Close-out → Tier 2 review

3. **[Claude Code]** Session 2: Frontend — react-grid-layout integration + tab system (Stage 1)
   → **[You]** Screenshot: can you create tabs? Rearrange widgets? Save layouts?
   → Close-out

4. **[Claude Code]** Session 3: Frontend — Widget palette UI (Stage 2)
   → **[You]** Screenshot: can you drag widgets onto tabs? Resize? Remove?
   → Close-out

5. **[Claude Code]** Sessions 4–6: Frontend — Individual widget implementations
   → Each session implements 3–4 widgets from the palette
   → **[You]** Screenshot after each session → close-out per session

6. **[Claude Code]** Tier 2 Reviews — all frontend sessions (visual verification)

7. **[Claude Code]** Sessions 7+ (if needed): Polish, edge cases, preset layouts

8. **[Claude Code]** Doc Sync — `doc-sync.md`
   → **This is the last sprint in Phase 10 — final doc currency check**

9. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint + phase completion)

---

### Phase 10 Gate (Full Vision)

**Trigger:** Sprint 41 complete
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Final Documentation Reconciliation

**[Claude.ai]** Strategic Check-In (Final):
1. **Full system review:** All 10 pages operational? Synapse live? Discovery pipeline running? Performance Workbench customizable?
2. **System performance:** Ensemble Sharpe on paper trading? Drawdown metrics? Comparison to Phase 6 artisanal baseline?
3. **Operational assessment:** Is the nightly workflow (review brief → approve discoveries → monitor session → review debrief) sustainable? Is it achieving the "few hours of active work per night" goal from the Day Trading Manifesto?
4. **Live trading with ensemble:** If not already live (from Phase 6 gate), is this the right time?
5. **Horizon items assessment:** Which Sprint 41+ items (Order Flow, options, multi-asset, Cython, multi-account, VR) are worth pursuing? Priority order?
6. **Architecture sustainability:** Can the system grow beyond current scale without rewrites?

**[Claude Code]** Final Documentation Reconciliation:
- All DECs archived and indexed
- Architecture doc reflects complete system
- Project Knowledge compressed to current-state-only
- All `.claude/rules/` files current
- Sprint Roadmap marked complete through Phase 10

**Output:** The system is operational. Future work tracked as Horizon Items with priority ordering.

---

## 10. Gate & Checkpoint Protocol Reference

Summary of all gates and checkpoints in the campaign, with exact protocols and timing.

| Gate | After Sprint | Protocol | Cadence Rule | Special Focus |
|------|-------------|----------|--------------|---------------|
| Phase 5 Gate | 24 | `strategic-check-in.md` + Doc Compression | Phase boundary | Paper trading health, Phase 6 readiness |
| Phase 6 Gate | 31 | `strategic-check-in.md` + `codebase-health-audit.md` + Doc Compression | Phase boundary + 4–6 sprint cadence | **CPA consultation, live trading decision** |
| Phase 7 Gate | 32 | `strategic-check-in.md` + Doc Compression | Phase boundary | **Data sufficiency RESOLVED (DEC-358). Confirm experiment pipeline thresholds.** |
| Phase 8 Gate | 35 | **Custom Gate Review** (see Section 7) | Phase boundary | **GO/NO-GO — pivotal campaign decision** |
| Phase 9 Gate | 39b | `strategic-check-in.md` + `codebase-health-audit.md` + Doc Compression | Phase boundary + 4–6 sprint cadence | Ensemble paper trading health, scale performance |
| Phase 10 Gate | 42 | `strategic-check-in.md` + Final Doc Reconciliation | Campaign completion | Full system review, horizon planning |

### Mid-Phase Check-Ins

If any phase runs longer than 5 sprints (Phase 6, Phase 9), run an informal mid-phase velocity check:
- Are session estimates holding?
- Is any work taking consistently longer than planned?
- Adjust remaining sprint estimates in this document.

This is NOT a full strategic check-in — it's a 15-minute calibration in a brief Claude.ai conversation.

---

## 11. Documentation Maintenance Schedule

### Per-Sprint (After Every Sprint)
- **[Claude Code]** Run `doc-sync.md` skill
  - Execute Doc Update Checklist from sprint package
  - Scan close-out reports for new DEC/RSK/DEF entries
  - Verify cross-reference integrity
  - Check `.claude/rules/` for needed updates
  - Produce sync report

### Per-Phase (At Every Phase Gate)
- **[Claude Code]** Documentation Compression
  - Archive completed-phase DECs → "Phase N Decision Archive"
  - Remove archived DECs from active Decision Log
  - Keep only active cross-cutting DECs in active log
  - Update Architecture doc to phase-final state
  - Compress Project Knowledge (remove completed-phase status details)
  - Run Tier A Compression Check (flag bloated sections)
  - **[You]** Review and approve all compressions

### Specific Phase Milestones
| After Phase | Doc Action |
|-------------|-----------|
| Phase 5 | First compression. Establish the archiving pattern. |
| Phase 6 | Major compression. CPA and live-trading DECs are high-priority entries. |
| Phase 7 | Architecture doc gets new major sections (BacktestEngine, Templates, Research Console). |
| Phase 8 | GO/NO-GO DEC is the most important entry in the entire project. Document thoroughly. |
| Phase 9 | Architecture doc rewrite (Ensemble Orchestrator supersedes original). Synapse documentation. |
| Phase 10 | Final reconciliation. All docs reflect complete system state. |

---

## 12. `.claude/rules/` Creation Schedule

Proactive rule creation prevents repeating mistakes. Create rules AFTER the sprint where the lesson was learned.

| After Sprint | Rule File | Content |
|-------------|-----------|---------|
| 29 | `backtest-engine.md` | BacktestEngine constraints, result equivalence requirements, performance benchmarks |
| 31 | `strategy-templates.md` | Template system constraints, configuration schema rules, instance validation requirements |
| 32 | `statistical-validation.md` | FDR method, minimum trade counts, data split methodology, smoothness prior parameters |
| 37a | `ensemble-orchestrator.md` | Orchestrator V2 constraints, activation filtering rules, position consolidation logic |
| 37b | `synapse.md` | Three.js performance budgets, node rendering constraints, grouping mode requirements |

Additionally, review existing rules at each phase gate:
- `backtesting.md` — still accurate after BacktestEngine introduction?
- `project.md` — still reflects current project constraints?
- `universal.md` — any new universal lessons?

---

## 13. Emergency Procedures

### Compaction Hits Mid-Sprint-Planning
1. If Design Summary (Phase B) was saved → start new conversation, paste Design Summary, continue from Phase C
2. If Design Summary was NOT saved → restart planning from Phase A. This is why Phase B exists. **Never skip it.**

### Compaction Hits Mid-Implementation
1. If session was near completion → new session, run close-out skill against current state
2. If session was mid-implementation → new session, prompt describes what's done and what remains
3. This is why sessions are scoped to 30–45 minutes

### Persistent Bug (2+ Failed Fixes)
- **[Claude Code]** Invoke `diagnostic.md` skill automatically
- Do NOT attempt a third ad-hoc fix. The diagnostic skill has 100% success rate vs. ~33% for ad-hoc.

### Impromptu Work (Unplanned Urgent Task)
- **[Claude.ai]** Protocol: `impromptu-triage.md`
  1. Reserve DEC/RSK/DEF numbers
  2. Assign sprint sub-number (e.g., 25.5)
  3. Generate: impact assessment, implementation prompt, review prompt
- **[Claude Code]** Implement with close-out + mandatory Tier 2 review
- **[Claude Code]** Doc sync BEFORE resuming planned sprint work. **Never carry two unsynced states.**

### Sprint Takes Significantly Longer Than Estimated
- If a sprint exceeds its estimate by >50%, pause and assess:
  - Is the scope too large? Split into sub-sprints.
  - Is the implementation approach wrong? Run a mini-adversarial review.
  - Is there a persistent bug? Invoke diagnostic skill.
- Update this document's timeline estimates for future sprints of the same type.

### Phase 8 NO-GO
- If the controlled experiment fails:
  1. Run the Phase 8 Gate Review as documented
  2. Determine: salvageable (methodology adjustment) or fundamental (approach doesn't work)
  3. If salvageable: plan a revised Sprint 32 with specific changes
  4. If fundamental: update roadmap. Phase 9–10 do not execute. Continue Phase 6 artisanal approach. ARGUS remains a strong multi-strategy trading system.
  5. BacktestEngine, Research Console, and statistical framework remain valuable for individual strategy research regardless of outcome.

---

## 14. Quick Reference: What Protocol, When

| I need to... | Use | Type |
|---|---|---|
| Start any sprint | `sprint-planning.md` (Phase A→B→C→D) | Protocol |
| Triage an issue mid-sprint | `in-flight-triage.md` (Work Journal conversation) | Protocol |
| Stress-test an architecture decision | `adversarial-review.md` (separate conversation) | Protocol |
| Implement a session | Paste implementation prompt (from `implementation-prompt.md`) | Template |
| End an implementation session | `close-out.md` | Skill |
| Review a session | `review.md` or `@reviewer` agent | Skill / Agent |
| Handle an ESCALATE | `tier-3-review.md` | Protocol |
| Sync docs after a sprint | `doc-sync.md` | Skill |
| Run a phase gate | `strategic-check-in.md` (+ `codebase-health-audit.md` at Phase 6 and 9 gates) | Protocol |
| Make the Phase 8 GO/NO-GO | Custom Gate Review (Section 7 of this document) | Custom |
| Handle a persistent bug | `diagnostic.md` (after 2nd failed fix) | Skill |
| Handle unplanned work | `impromptu-triage.md` | Protocol |
| Pre-test invariants | `canary-test.md` | Skill |
| Log a decision | `decision-entry.md` | Template |

---

*This document is the operational blueprint for the ARGUS development campaign from Sprint 21.5 through Sprint 40 (Full Vision). It references the Metarepo Workflow System v1.2 for all protocol, skill, agent, and template definitions. Update this document's timeline estimates as actual velocity data accumulates.*
