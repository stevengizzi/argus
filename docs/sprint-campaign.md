# ARGUS Development Campaign — Master Sprint Plan

> From Sprint 21.5 to Full Vision — every step mapped
> March 5, 2026 | Based on Unified Vision Roadmap v2 + Metarepo Workflow System v1.2

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

| Sprint | Name | Type | Modes | Est. Sessions | Est. Days | Adversarial? | Gate After? |
|--------|------|------|-------|---------------|-----------|--------------|-------------|
| **Phase 5: Foundation Completion** | | | | | | | |
| 21.5 | Live Integration | A | standard | 2–3 | 2 | No | No |
| 21.7 | FMP Scanner Integration | B | iterative-judgment | 3–5 | 2 | No | No |
| 22 | AI Layer MVP | B | adversarial, iterative-judgment | 4–6 | 3 | **Yes** | No |
| 23 | NLP Catalyst + Pre-Market Engine | B | iterative-judgment | 4–6 | 3 | No | No |
| 24 | Setup Quality Engine + Dynamic Sizer | B | adversarial, iterative-judgment | 5–7 | 3–4 | **Yes** | **Phase 5 Gate** |
| **Phase 6: Strategy Expansion** | | | | | | | |
| 25 | The Observatory | B | iterative-judgment | 13–18 | 4–5 | No | No |
| 26 | Red-to-Green + Pattern Library Foundation | B | iterative-judgment | 3–5 | 2–3 | No | No |
| 27 | Pattern Expansion I | B | iterative-judgment | 5–7 | 4–5 | No | No |
| 28 | Short Selling Infrastructure + Pattern Expansion II | B | iterative-judgment | 3–5 | 3 | No | No |
| 29 | Learning Loop V1 | B | iterative-judgment | 3–5 | 3 | No | **Phase 6 Gate** |
| **Phase 7: Infrastructure Unification** | | | | | | | |
| 30 | BacktestEngine Core + Research Console | C | adversarial, iterative-judgment | 6–8 | 4 | **Yes** | No |
| 31 | Parallel Sweep Infrastructure | B | iterative-judgment | 5–7 | 3–4 | No | No |
| 32 | Parameterized Strategy Templates | C | adversarial, iterative-judgment | 5–7 | 3–4 | **Yes** | **Phase 7 Gate** |
| **Phase 8: Controlled Experiment** | | | | | | | |
| 33 | Statistical Validation Framework | B | adversarial, iterative-judgment | 5–7 | 3–4 | **Yes** | No |
| 34 | ORB Family Systematic Search | D | research, adversarial | 5–8 | 4–5 | **Yes** | No |
| 35 | Ensemble Performance Analysis | D | research | 3–5 | 2–3 | No | **Phase 8 GATE (GO/NO-GO)** |
| **Phase 9: Ensemble Scaling** | | | | | | | |
| 36 | Cross-Family Search (VWAP + Momentum) | B | iterative-judgment | 5–7 | 4–5 | No | No |
| 37 | Cross-Family Search (Remaining) | B | iterative-judgment | 5–7 | 4–5 | No | No |
| 38a | Ensemble Orchestrator V2 (Backend) | C | adversarial | 4–6 | 3 | **Yes** | No |
| 38b | Synapse (Frontend) | B | iterative-judgment, research-first | 6–10 | 4 | No | No |
| 39a | Ensemble WebSocket Backend | A | standard | 2–4 | 2 | No | No |
| 39b | Real-Time Synapse + Page Evolutions | B | iterative-judgment | 6–10 | 4 | No | **Phase 9 Gate** |
| **Phase 10: Full Vision** | | | | | | | |
| 40 | Learning Loop V2 (Ensemble Edition) | B | iterative-judgment | 4–6 | 4–5 | No | No |
| 41 | Continuous Discovery Pipeline | B | iterative-judgment | 4–6 | 3–4 | No | No |
| 42 | Performance Workbench | B | iterative-judgment | 5–8 | 4–5 | No | **Phase 10 Gate** |

**Totals:** 23 sprints (including sub-sprints) | ~105–155 sessions | ~13–17 weeks estimated

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
| 25 | Mar 17 | Mar 22 | The Observatory (~4–5 days, 13–18 sessions) |
| 26 | Mar 23 | Mar 26 | Red-to-Green + Pattern Library Foundation |
| 27 | Mar 26 | Mar 31 | Pattern Expansion I |
| 28 | Mar 31 | Apr 3 | Short Selling + Pattern Expansion II |
| 29 | Apr 3 | Apr 6 | Learning Loop V1 |
| **Phase 6 Gate** | **Apr 6** | **Apr 7** | Strategic check-in + CPA consultation gate |
| 30 | Apr 8 | Apr 12 | BacktestEngine + Research Console |
| 31 | Apr 12 | Apr 16 | Parallel Sweep Infrastructure |
| 32 | Apr 16 | Apr 20 | Parameterized Strategy Templates |
| **Phase 7 Gate** | **Apr 20** | **Apr 21** | Strategic check-in + data sufficiency decision |
| 33 | Apr 22 | Apr 26 | Statistical Validation Framework |
| 34 | Apr 26 | May 1 | ORB Systematic Search; may need cloud burst |
| 35 | May 1 | May 4 | Ensemble Performance Analysis |
| **Phase 8 GATE** | **May 4** | **May 5** | **GO/NO-GO — pivotal decision** |
| 36 | May 6 | May 11 | Only if GO |
| 37 | May 11 | May 16 | Only if GO |
| 38a | May 16 | May 19 | Adversarial review adds ~0.5 day |
| 38b | May 19 | May 23 | Three.js mini-discovery before implementation |
| 39a | May 23 | May 25 | |
| 39b | May 25 | May 29 | |
| **Phase 9 Gate** | **May 29** | **May 30** | Strategic check-in + codebase health audit |
| 40 | May 31 | Jun 5 | |
| 41 | Jun 5 | Jun 9 | |
| 42 | Jun 9 | Jun 14 | |
| **Phase 10 Gate** | **Jun 14** | **Jun 15** | Final strategic check-in |

**Total calendar estimate:** ~15 weeks (March 5 – June 15)

---

### 3.3 Dependency Map

```
Phase 5 (Linear Chain — each sprint depends on the previous):

  21.5 ──→ 21.7 ──→ 22 ──→ 23 ──→ 24
  (live)   (scanner) (AI)  (NLP)  (quality)
                                      │
                                      ▼
                                 PHASE 5 GATE

Phase 6 (Linear Chain):

  25 ──→ 26 ──→ 27 ──→ 28
  (R2G)  (exp-I) (short+exp-II) (learning loop)
                                      │
                                      ▼
                                 PHASE 6 GATE
                                 (CPA consultation gate — live trading may begin)

Phase 7 (Linear Chain, CAN partially overlap with late Phase 6):

  29 ──→ 30 ──→ 31
  (engine) (sweep) (templates)
                      │
                      ▼
                 PHASE 7 GATE
                 (data sufficiency decision — resolve RSK before Phase 8)

Phase 8 (Linear Chain):

  32 ──→ 33 ──→ 34
  (stats) (experiment) (analysis)
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

  35 ──→ 36 ──→ 37a ──→ 37b ──→ 38a ──→ 38b
  (VWAP)  (all)  (orch) (synapse) (ws)  (rt-synapse)
                                            │
                                            ▼
                                       PHASE 9 GATE

Phase 10 (Linear Chain):

  39 ──→ 40 ──→ 41
  (learn) (discover) (workbench)
                        │
                        ▼
                   PHASE 10 GATE (Full Vision)
```

**Cross-Phase Dependencies:**

| Dependency | Description |
|-----------|-------------|
| Phase 6 requires Phase 5 | Strategies need quality filtering (Sprint 24) and AI layer (Sprint 22) |
| Phase 7 can overlap Phase 6 | Sprint 29 (BacktestEngine) only needs existing strategies to test against — could start after Sprint 26–27. The roadmap sequences them serially for simplicity, but parallelism is possible if velocity is ahead of schedule. |
| Phase 8 requires Phase 7 | The experiment (Sprint 33) needs BacktestEngine (29), sweeps (30), and templates (31) |
| Phase 9 requires Phase 8 GO | If NO-GO, Phase 9 does not execute |
| Sprint 33 requires data sufficiency | The Phase 7 gate must resolve the historical data risk (RSK from roadmap) before Sprint 32 begins |
| Sprint 37b requires Three.js research | A mini-discovery session before implementation (see Sprint 37b choreography) |

**Potential Parallelism Windows:**

| Window | What Could Overlap | Conditions |
|--------|-------------------|------------|
| Phase 6 + Phase 7 start | Sprint 29 could overlap with Sprint 27–28 | Only if Phase 6 is on track and you have bandwidth |
| Sprint 37a + 37b prep | Three.js mini-discovery during 37a implementation | Research conversation doesn't block backend work |
| Sprint 38a + 38b prep | Frontend planning during backend WebSocket work | Planning doesn't block implementation |

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

## 5. Phase 6: Strategy Expansion — Artisanal (Sprints 25–28)

*Adds strategies one at a time. Each hand-designed, backtested, validated. Includes short selling infrastructure. Target: ~2–3 weeks.*

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

### Sprint 27: Pattern Expansion I

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~4–5 days | **Sessions:** 5–7 (3–4 backend, 2–3 frontend)
**Depends on:** Sprint 26 complete
**Adversarial review:** No
**Delivers:** 2–3 additional pattern modules (Dip-and-Rip, HOD Break, Gap-and-Go), Pattern Library cards, Dashboard Short Exposure indicator (infrastructure prep)

**Choreography:**

1. **[Claude.ai]** Sprint Planning
2. **[Claude Code]** Sessions 1–3: One backend session per strategy
3. **[Claude Code]** Session 4: Frontend — Pattern Library cards + Short Exposure indicator
4. **[Claude Code]** Fix sessions (if needed)
5. **[Claude Code]** Doc Sync → **[Claude.ai]** Tier 3 Review

---

### Sprint 28: Short Selling Infrastructure + Pattern Expansion II

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3 days | **Sessions:** 3–5 (2–3 backend, 1–2 frontend)
**Depends on:** Sprint 27 complete
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

### Sprint 29: Learning Loop V1

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3 days | **Sessions:** 3–5 (2 backend, 1–3 frontend)
**Depends on:** Sprint 28 complete
**Adversarial review:** No
**Delivers:** LearningDatabase, PostTradeAnalyzer, throttle/boost recommendations, Orchestrator health bands, Performance correlation matrix

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - LearningDatabase design: stores all scored setups (traded and untraded), outcomes, quality scores, regime context
     - PostTradeAnalyzer: correlates quality scores with outcomes, weekly batch retraining of Quality Engine weights
     - Throttle/boost recommendation logic: performance-aware throttling, strategies that underperform historical baseline get throttled, outperformers get boosted
     - Orchestrator health panel visual spec: horizontal health bands per strategy, throttle/boost action cards
     - Performance page correlation matrix visual spec: heatmap with warning indicators for high correlation
     - Session decomposition: backend LearningDatabase + PostTradeAnalyzer → backend throttle/boost engine → frontend health panel + correlation matrix
   - Flag: Iterative Judgment Loop (two significant new UI components)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Session 1: Backend — LearningDatabase + PostTradeAnalyzer
   → Close-out → Tier 2 review

3. **[Claude Code]** Session 2: Backend — Throttle/boost engine + correlation monitoring
   → Close-out → Tier 2 review

4. **[Claude Code]** Session 3: Frontend — Orchestrator health bands + throttle/boost cards + Performance correlation matrix
   → Visual spec → **[You]** screenshot Orchestrator + Performance → close-out

5. **[Claude Code]** Tier 2 Review — Session 3 (visual verification)

6. **[Claude Code]** Session 4+ (if needed): Frontend fix sessions

7. **[Claude Code]** Doc Sync — `doc-sync.md`
   → **This is the last sprint in Phase 6 — extra attention to doc currency**
   → Update: all strategy documentation, Learning Loop architecture, Performance page capabilities

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion + phase completion)

---

### Phase 6 Gate

**Trigger:** Sprint 28 complete
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression + Codebase Health Audit

This is the most significant non-Phase-8 gate because **live trading with real capital could begin during or after Phase 6** (per roadmap).

**[Claude.ai]** Strategic Check-In Conversation:

1. **Progress review:** 10–11 strategies active? Learning Loop working? Correlation monitoring producing useful data?
2. **Paper trading assessment:** Sharpe > 2.0? Positive expectancy across strategies? No catastrophic drawdowns? If yes → CPA consultation gate is met.
3. **CPA consultation decision:** Is it time to consult with a CPA about tax implications of live trading? Log as DEC entry.
4. **Live trading readiness:** Are you confident enough in the system to deploy real capital? If yes → schedule live-minimum deployment during Phase 7 or Phase 8. Log as DEC entry.
5. **Phase 7 readiness:** Is the BacktestEngine direction clear? Are the existing strategies ready to be templatized?
6. **Historical data sufficiency:** This is the time to decide whether to acquire deeper history (Databento 5–10 year purchase). The decision MUST be made before Phase 8 begins. Create a DEC entry and potentially a RSK entry. If data purchase is needed, start the process now.
7. **Velocity calibration:** Update session estimates for Phase 7–8 based on Phase 5–6 actuals.

**[Claude.ai]** Codebase Health Audit — `codebase-health-audit.md`
- First audit of the campaign (Phase 6 is ~sprint 27, meeting the "every 4–6 sprints" cadence)
- Focus: architectural coherence after adding 7+ strategies, test coverage, naming consistency, deferred item accumulation

**[Claude Code]** Documentation Compression:
- Archive Phase 5–6 DECs
- Update Architecture doc to Phase 6 final state
- Compress Project Knowledge
- Run Tier A Compression Check

**Output:** Updated roadmap, CPA decision, live-trading decision, data-purchase decision, velocity adjustments, codebase health report.

---

## 6. Phase 7: Infrastructure Unification (Sprints 29–31)

*Builds the BacktestEngine, sweeps, and template system. Research infrastructure in parallel with live trading. Target: ~2–2.5 weeks.*

---

### Sprint 30: BacktestEngine Core + Research Console

**Type:** C (Architecture-Shifting) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~4 days | **Sessions:** 6–8 (3–4 backend, 3–4 frontend)
**Depends on:** Phase 6 Gate complete
**Adversarial review:** **YES** — new parallel execution path (BacktestEngine), must produce identical results to existing Replay Harness, introduces Research Console (page 9)
**Delivers:** SynchronousEventBus, BacktestEngine, HistoricalDataFeed, ResultsCollector, Research Console (page 9: Run Manager, Result Comparison, Run Configuration)

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - SynchronousEventBus architecture (direct dispatch, no async overhead)
     - BacktestEngine orchestrator design (strategy classes + IndicatorEngine + SimulatedBroker wiring)
     - HistoricalDataFeed adapter for Databento stored data
     - ResultsCollector (trades + equity curves)
     - **Critical requirement:** Results must match Replay Harness exactly — define validation criteria
     - Research Console (page 9) visual spec: Run Manager layout, Result Comparison side-by-side, Run Configuration form
     - Session decomposition: backend event bus → backend engine + data feed + collector → backend validation against Replay Harness → frontend Research Console Run Manager → frontend Result Comparison + Run Configuration
   - Flag: Adversarial Review (new execution path with correctness requirement)
   - Flag: Iterative Judgment Loop (Research Console is an entirely new page)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude.ai]** Adversarial Review — `adversarial-review.md`
   - **SEPARATE conversation**
   - **Specific focus areas:**
     - Result equivalence: How will you prove BacktestEngine results match Replay Harness? What tolerance? What test cases?
     - Event ordering: Does synchronous dispatch guarantee deterministic execution? Edge cases?
     - SimulatedBroker fidelity: fill assumptions, slippage model, commission model
     - Data feed edge cases: gaps in Databento data, market hours boundaries, holidays
     - Performance: target speed (5–10x Replay Harness) — what if it's slower?
   - Outcome: confirmed or revisions
   - **[You]** Save findings

3. **[Claude Code]** Session 1: Backend — SynchronousEventBus + BacktestEngine core
   → Close-out → **[You]** save

4. **[Claude Code]** Tier 2 Review — Session 1

5. **[Claude Code]** Session 2: Backend — HistoricalDataFeed + ResultsCollector + validation
   → **Canary test:** Run same strategy through both Replay Harness and BacktestEngine, compare results
   → Close-out → **[You]** save

6. **[Claude Code]** Tier 2 Review — Session 2

7. **[Claude Code]** Sessions 3–4: Frontend — Research Console (Run Manager, Result Comparison, Run Configuration)
   → Visual spec reference → **[You]** screenshot after each session → close-out per session

8. **[Claude Code]** Tier 2 Reviews — Sessions 3–4 (visual verification)

9. **[Claude Code]** Session 5+ (if needed): Frontend polish

10. **[Claude Code]** Doc Sync — `doc-sync.md`
    → **Architecture doc update is MANDATORY** (new BacktestEngine section, Research Console page)
    → Create `.claude/rules/backtest-engine.md` — codify BacktestEngine constraints and patterns

11. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C)
    → Focus: result equivalence validated? Architecture sound for Phase 8 sweep demands?

---

### Sprint 31: Parallel Sweep Infrastructure

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 5–7 (2–3 backend, 3–4 frontend)
**Depends on:** Sprint 29 complete (needs BacktestEngine)
**Adversarial review:** No (builds on Sprint 29's reviewed architecture)
**Delivers:** Multiprocessing harness, parameter grid spec, worker pool, Research Console upgrades (Sweep Manager, Heatmap, 3D Parameter Landscape)

**Choreography:**

1. **[Claude.ai]** Sprint Planning — `sprint-planning.md`
   - **Phase A — Think:**
     - Multiprocessing architecture (worker pool, parameter distribution, result aggregation)
     - Parameter grid specification format
     - Cloud burst configuration (high-core-count instance for sweep days)
     - Progress monitoring pipeline
     - **Acceptance criteria:** 1,000 combinations × 10 symbols < 2 hours on 8-core. Results identical to sequential.
     - Research Console upgrades visual spec: Sweep Manager (parameter range sliders, estimated time, live progress), Heatmap (interactive, click-to-drill), 3D Parameter Landscape (Plotly surface plot — already available in frontend stack)
     - Session decomposition: backend multiprocessing + grid + workers → backend progress monitoring + cloud config → frontend Sweep Manager → frontend Heatmap + 3D Landscape
   - Flag: Iterative Judgment Loop (three significant new visualizations)
   - **Phase B** — Design Summary → **[You]** save
   - **Phase C** — Generate sprint package
   - **Phase D** — Verify
   - **[You]** Save all artifacts

2. **[Claude Code]** Sessions 1–2: Backend — Multiprocessing harness + grid spec + workers + progress + cloud config
   → Close-out per session → Tier 2 review per session
   → Performance benchmark in prompt: 1,000 combos × 10 symbols < 2 hours

3. **[Claude Code]** Session 3: Frontend — Sweep Manager UI
   → Visual spec → **[You]** screenshot → close-out

4. **[Claude Code]** Session 4: Frontend — Heatmap + 3D Parameter Landscape
   → Visual spec → **[You]** screenshot → close-out

5. **[Claude Code]** Tier 2 Reviews — Sessions 3–4 (visual verification)

6. **[Claude Code]** Session 5+ (if needed): Frontend polish

7. **[Claude Code]** Doc Sync — `doc-sync.md`

8. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (sprint completion)

---

### Sprint 32: Parameterized Strategy Templates

**Type:** C (Architecture-Shifting) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 5–7 (3 backend, 2–4 frontend)
**Depends on:** Sprint 30 complete
**Adversarial review:** **YES** — significant refactor of strategy architecture (Roadmap Contradiction Note). Strategies become templates. Risk Manager, Orchestrator, Order Manager must see no difference.
**Delivers:** Template system, template configuration schema, template registry, existing strategies refactored as templates, Pattern Library evolution to template gallery

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
    → **This is the last sprint in Phase 7 — extra attention to doc currency**

13. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C + phase completion)

---

### Phase 7 Gate

**Trigger:** Sprint 31 complete
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression

**[Claude.ai]** Strategic Check-In Conversation:

1. **Progress review:** BacktestEngine working? Results match Replay Harness? Templates validated? Research Console operational?
2. **Data sufficiency decision:** This MUST be resolved now, before Phase 8 begins.
   - How much historical data is available? Is 35 months enough for three-way splits?
   - Decision: purchase deeper Databento history? Use synthetic augmentation? Accept lower granularity?
   - Log as DEC entry. If purchase needed, initiate immediately — this is on the Phase 8 critical path.
3. **Phase 8 readiness:** Is the BacktestEngine fast enough for the controlled experiment (Sprint 32)? Do the templates cover the ORB family adequately for systematic search?
4. **Velocity calibration:** Update estimates for Phase 8.
5. **Risk review:** Any new risks from Phase 7 implementation? Cloud burst infrastructure ready?

**[Claude Code]** Documentation Compression:
- Archive Phase 5–7 DECs
- Architecture doc updated to Phase 7 final state (BacktestEngine, templates, Research Console)
- Compress Project Knowledge
- Verify `.claude/rules/` files: `backtesting.md`, `backtest-engine.md`, `strategy-templates.md` all current

**Critical output:** Data sufficiency DEC entry. This gates Phase 8.

---

## 7. Phase 8: Controlled Experiment (Sprints 32–34)

*The proving ground. Everything before this is valuable regardless. Everything after depends on Sprint 33's results. Target: ~2–2.5 weeks.*

---

### Sprint 33: Statistical Validation Framework

**Type:** B (Mixed Backend + Frontend) | **Modes:** Adversarial Review, Iterative Judgment Loop
**Duration:** ~3–4 days | **Sessions:** 5–7 (3 backend, 2–4 frontend)
**Depends on:** Phase 7 Gate complete (including data sufficiency decision)
**Adversarial review:** **YES** — if the statistical methodology is wrong, the entire Phase 8 experiment is worthless. This is the highest-stakes adversarial review in the campaign.
**Delivers:** FDR correction (Benjamini-Hochberg), minimum trade count thresholds, three-way data splits, smoothness prior, Research Console Validation Dashboard

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
**Depends on:** Sprint 32 complete
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

9. **[You]** Save all results, heatmaps, equity curves. These feed Sprint 34.

---

### Sprint 35: Ensemble Performance Analysis

**Type:** D (Research / Experiment) | **Modes:** Research Sprint
**Duration:** ~2–3 days | **Sessions:** 3–5
**Depends on:** Sprint 33 complete (uses Sprint 33 results as input)
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

**Trigger:** Sprint 34 complete
**Protocol:** Custom Gate Review (NOT a standard strategic check-in — this is bigger)

This is the pivotal decision of the entire campaign. Everything from Sprint 34 onward depends on the outcome.

**[Claude.ai]** Gate Review Conversation:

Start with:
```
"We are at the Phase 8 gate — the go/no-go decision for the ensemble vision.
Sprint 33 results and Sprint 34 analysis are complete. I need to make the
decision that determines whether we proceed to Phase 9 (ensemble scaling)
or continue with the Phase 6 artisanal approach.

Here are the results: [paste Sprint 33/34 key metrics]
Here are the pre-defined success criteria from Sprint 33 planning: [paste]
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
- Sprint 34 planning begins immediately after the gate review

**NO-GO:** The ensemble methodology did not produce the desired results.
- Log as DEC entry with full rationale and failure analysis
- Decision fork:
  - **NO-GO (salvageable):** The methodology needs adjustment. Plan a revised Sprint 33 with specific changes. Phase 9 is delayed, not cancelled.
  - **NO-GO (fundamental):** The approach doesn't work for day trading. Phase 9 is cancelled. Continue Phase 6 artisanal approach. ARGUS remains strong — the ceiling is lower but the floor hasn't changed. BacktestEngine and Research Console remain valuable for individual strategy research.
- Update roadmap accordingly

**[You]** This decision cannot be delegated. Review the Gate Review conversation output, look at the Go/No-Go Dashboard, and make the call. Log it as a DEC entry.

---

## 8. Phase 9: Ensemble Scaling (Sprints 35–38)

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
**Depends on:** Sprint 35 complete
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
**Depends on:** Sprint 36 complete (needs all family ensembles)
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
   → **Canary test before Session 1:** Capture current Orchestrator behavior on a reference set. After Sprint 37a, new Orchestrator must produce equivalent-or-better results.

4. **[Claude Code]** Doc Sync — `doc-sync.md`
   → **Architecture doc update MANDATORY** (Orchestrator section rewritten)

5. **[Claude.ai]** Tier 3 Review — `tier-3-review.md` (**mandatory** — Type C, core infrastructure replaced)

---

### Sprint 38b: Synapse (Frontend)

**Type:** B (Mixed Backend + Frontend) | **Modes:** Iterative Judgment Loop, Research-First
**Duration:** ~4 days | **Sessions:** 6–10
**Depends on:** Sprint 37a complete (needs Ensemble Orchestrator for data), but Three.js research can happen during 37a
**Adversarial review:** No (frontend visualization, not architectural)
**Delivers:** Synapse page (page 10) — 3D strategy space, color/size/opacity encoding, correlation connections, navigation, grouping modes

**Special: Mini-Discovery before implementation.** The Synapse is the most visually complex component ARGUS has ever built. Before writing code, run a research conversation.

**Choreography:**

1. **[Claude.ai]** Mini-Discovery Conversation — (can overlap with Sprint 37a)
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
     - REST endpoint for ensemble state (backend, coordinate with Sprint 37a)
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
**Depends on:** Sprint 37b complete
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
**Depends on:** Sprint 38a complete (needs WebSocket stream)
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
| Phase 6 Gate | 28 | `strategic-check-in.md` + `codebase-health-audit.md` + Doc Compression | Phase boundary + 4–6 sprint cadence | **CPA consultation, live trading decision, data purchase decision** |
| Phase 7 Gate | 31 | `strategic-check-in.md` + Doc Compression | Phase boundary | **Data sufficiency resolution (MUST happen before Phase 8)** |
| Phase 8 Gate | 34 | **Custom Gate Review** (see Section 7) | Phase boundary | **GO/NO-GO — pivotal campaign decision** |
| Phase 9 Gate | 38b | `strategic-check-in.md` + `codebase-health-audit.md` + Doc Compression | Phase boundary + 4–6 sprint cadence | Ensemble paper trading health, scale performance |
| Phase 10 Gate | 41 | `strategic-check-in.md` + Final Doc Reconciliation | Campaign completion | Full system review, horizon planning |

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
