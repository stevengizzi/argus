# ARGUS — Process Evolution [FROZEN]

> **FROZEN 2026-04-21 — historical reference only, narrative ends at Sprint 21.5 (2026-02-27).**
> The workflow-evolution story captured here covers Phases A through E (Sprints 1–21.5) as of
> early March 2026. Sprints 22 through 31.85 (~52 days, ~40 sprints + sub-sprints) are
> intentionally NOT continued in this document; the workflow has since stabilized around the
> patterns documented in `workflow/` (the metarepo submodule) and in `docs/sprint-history.md`.
> See those for current-era process. Preserved in place as a snapshot of the early-phase
> process evolution that established the patterns still in use today.
>
> How the ARGUS development workflow evolved across five phases and 21+ sprints.
> Derived from meta-analysis conducted March 3, 2026.

---

## Origins

ARGUS traces to September 26, 2025, when Steven shared his Day Trading Manifesto — a plan to build a day trading system generating household income. A second conversation on October 29, 2025 deepened the financial modeling. Active development began February 14, 2026 with the workflow setup and Sprint 1.

The project uses a **two-Claude architecture**: Claude.ai (strategic design, code review, documentation) and Claude Code (implementation, testing). Git serves as the bridge. This separation was established from day one (DEC-022) and proved to be the project's velocity multiplier.

---

## Phase A — Raw Execution (Sprints 1–5, Feb 14–16)

The workflow existed but was informal. The intended cycle: sprint planning → micro-decisions → implementation spec → Claude Code session prompts → implementation → code review → polish → doc update → next sprint.

**Adherence was remarkably high.** Every sprint had a planning conversation, a spec, implementation via Claude Code, a transcript-based code review, and documentation sync. This discipline was established through repetition.

**Key invention: Handoff documents.** The Sprint 2 review hit context limits, forcing the creation of handoff documents to carry context between conversations. This pattern evolved into structured packages by Phase D.

**Key invention: DEF-NNN tracking.** Deferred items tracking was invented during the Sprint 2 review, preventing scope creep while preserving context for future work.

**Outcome:** Phase 1 completed in 2 days vs. the original 4-week estimate. The 362-test core engine established the foundation for everything that followed.

---

## Phase B — Backtesting Maturity (Sprints 6–11, Feb 16–17)

Code review became formal with structured checklists. The "gate check" concept emerged — don't proceed until validation passes.

**Crisis: Sprint 8 (VectorBT performance).** The initial implementation used `iterrows()` and took 4+ hours for a parameter sweep. Caught during review, but the fix cascaded: optimization session → ATR bug discovery → parameter threshold recalibration. A 2-conversation sprint became a 4-conversation odyssey. Root cause: the implementation spec didn't include performance benchmarks as a gate check. This directly led to the DEC-149 precompute+vectorize mandate in later sprints.

**Key discovery: ATR calculation divergence.** VectorBT uses daily-bar ATR; production uses 1-minute-bar ATR with Wilder smoothing, producing 5–10x ratio differences. The `max_range_atr_ratio` parameter from VectorBT sweeps doesn't transfer to production. This was the project's first major "assumption invalidated" moment.

**Lesson learned:** Every implementation spec should include "this should complete in < X seconds" where applicable. Performance benchmarks became a standard gate check.

---

## Phase C — Infrastructure Pivot (Sprints 12–13, Feb 21–22)

The market data and broker research conversations (Feb 18–20) established a new pattern: **deep research → comprehensive report → documentation sync → then implementation.** These were the most valuable non-coding sessions in the project.

**Key decisions:** Databento selected as primary data provider (DEC-082), Interactive Brokers as sole live execution broker (DEC-083). Both decisions prevented months of rework — the Alpaca IEX data limitation (2–3% of volume, DEC-081) would have undermined all signal validation.

**Retrospective insight:** These infrastructure decisions should have been made before building on Alpaca for 10 sprints. Starting with "what data provider and broker will we actually use in production" would have saved the Alpaca adapter work. The deep research conversations were worth 10x their time investment.

**GitHub sync limitation discovered (Feb 22):** Claude's GitHub integration only synced documentation files, not source code. This forced making the repo public for code reviews — a workaround that became standard practice and significantly improved review efficiency.

---

## Phase D — Sprint Packages (Sprints 14–20, Feb 23–26)

The workflow organically evolved into its most mature pre-retrofit pattern.

**Key evolution: Sprint packages.** By Sprint 18+, "kickoff prompts" became comprehensive self-contained packages: spec + session prompts + review plans + handoff briefs + doc updates, all produced in one conversation. This cut the number of conversations per sprint roughly in half. Sprints 19, 20, and 21a–21d each produced complete self-contained packages.

**Frontend demanded different feedback loops.** Backend sprints followed clean plan→build→review cycles. Frontend required iterative design→screenshot→fix→re-screenshot loops. Sprint 15 and 16 reviews became hybrid design-review-fix sessions. This was productive drift — visual work inherently demands tighter iteration. Accepting this rather than fighting it produced better results.

**Boundary blurring was mostly productive.** The "ARGUS monthly returns feasibility" conversation (Feb 26) started as returns discussion and evolved into the DEC-163 expanded vision — transforming ARGUS from 5 strategies to 15+ with AI enhancement. This was scope expansion masquerading as discussion, but it was the right call.

**Split sprint pattern became standard.** Sprint 4 → 4a/4b, Sprint 17 → 17+17.5, Sprint 18 → 18+18.5+18.75, Sprint 21 → 21a/21b/21c/21d. Always productive — kept individual sprints focused and reviewable.

**Estimate accuracy improved dramatically.** Early sprints were consistently beaten (Phase 1: 2 days vs. 4-week estimate). By Sprint 14+, session counts were accurate to ±1. Major miss: Sprint 21d at 14 sessions — UX backlog scope was genuinely hard to estimate.

---

## Phase E — Operational Maturity (Sprints 21a–21.5, Feb 27–)

Live integration introduced a new workflow dimension: real market sessions alongside development.

**Sprint 21.5 "battle plan" concept:** Combining multiple sessions into a market-day plan, with sessions structured around market hours. Development sessions during Asian hours, validation during US market open.

**Document sync overhead at scale.** By Sprint 21d, a doc sync conversation produced 1,000+ lines of copy-paste content across 6 files. This prompted the metarepo retrofit — the manual copy-paste workflow was the project's largest remaining friction point.

**Decision Log as superpower.** 249 entries in 17 days is extraordinary. Decisions never got relitigated because they were always documented. This is the single most valuable artifact in the project.

---

## Phase F — Sprint Package Refinements (Sprint 22, March 2026)

Sprint 22 (AI Layer MVP) was the first sprint fully planned under the metarepo workflow. Three process failures during planning and implementation exposed gaps in the protocols.

**Problem 1: Adversarial review invalidated prompts that were already generated.** The Sprint 22 planning conversation generated all 18 prompts (9 implementation + 9 review) before the adversarial review ran. The adversarial review then found 5 critical issues — SSE replaced by WebSocket, JSON-in-text parsing replaced by tool_use, action types unspecified, system prompt undefined, cost tracking absent. Every prompt had to be regenerated. **Fix:** `sprint-planning.md` now splits artifact generation into two phases. Phase C generates spec-level artifacts (spec, spec-by-contradiction, session breakdown, checklists). Phase C-1 is an explicit adversarial review gate. Phase D generates prompts only after specs are finalized. Prompts are never generated twice.

**Problem 2: Review prompts were 26KB each with 24KB of duplicated content.** Each review prompt embedded the full Sprint Spec, Spec-by-Contradiction, regression checklist, and escalation criteria — identical across all 9 files. This created a maintenance hazard (fixing a spec error meant updating 6+ remaining files) and was wasteful. **Fix:** `review-prompt.md` now uses a reference-based structure. A single Review Context File contains all shared content. Each session review prompt is a small file (~1.5KB) pointing Claude Code to the context file, with only the session-specific scope, focus items, and close-out placeholder.

**Problem 3: Compaction risk assessment was qualitative and under-calibrated.** Sessions 3a (rated "Medium-Low") and 3b (rated "Medium") both compacted. Session 3b compacted before reaching 50% of its requirements. The qualitative "Low / Medium / High" rating based on "files created, files modified, integration surface area" missed the dominant factors: pre-flight context reads and test count. **Fix (DEC-275):** Replaced with a point-based scoring system covering 7 factors. Thresholds: ≤13 proceed, 14+ must split. Retrospective scoring confirmed: Session 3a scored 15 (would have been caught), Session 3b scored 23 (would have been caught and split into 3). Close-out reports now log compaction events with planning score and failure point for ongoing threshold calibration.

**Additional refinement: Visual review in prompts.** Frontend sessions (4a–6) had visual verification items buried in code-level regression checklists with no separation. Added explicit `## Visual Review` sections to both `implementation-prompt.md` and `review-prompt.md` templates. Backend-only sessions omit the section entirely. Frontend sessions list exactly what to check in a browser, what "correct" looks like, and what app state is needed for verification.

---

## Recurring Friction Points

### VectorBT Performance and Divergence (Sprints 8, 19, 20)
Every new strategy's VectorBT sweep hit the same problem: initial implementations too slow, needed vectorization, then had divergences from live strategy behavior. The `.claude/rules/backtesting.md` mandate helped but didn't eliminate the fundamental tension: VectorBT approximates strategy behavior for speed, creating inherent divergence from the live state machine.

### Context Window Limits
Multiple conversations hit context limits and needed continuation in fresh chats. The Sprint 2 review hit this first, leading to handoff documents. The two-Claude workflow fundamentally routes around this but adds overhead.

### UI Iteration Cycles
Frontend work consistently required more back-and-forth than backend work. A code review would surface CSS issues visible only in screenshots, requiring fix prompts, then re-review. This isn't a process problem — it's inherent to visual development.

### Documentation Sync Overhead
While docs were well-maintained, the time spent on doc updates grew as the project grew. By Sprint 21d, this prompted the metarepo retrofit to automate and restructure documentation workflows.

### Claude Infrastructure Issues (Feb 28, Mar 2)
Container failures and 503 errors interrupted review sessions. Platform issues, not workflow issues, but they disrupted momentum.

---

## Top Insights (Ranked by Impact)

1. **The two-Claude workflow achieved genuine 10x velocity, but documentation is the load-bearing wall.** The system works because both Claudes share context through docs. When docs drift, velocity drops. When docs are current, each sprint starts at full speed.

2. **Sprint packages (spec + prompts + reviews + handoffs in one conversation) cut overhead by ~40%.** Every new project should start with this pattern from day one.

3. **Code review via direct repo access is non-negotiable at scale.** The transition from transcript-based review to repo-cloning review (Sprint 14+) was transformative. Transcript parsing consumed 30–60% of review context; repo access uses almost none.

4. **Visual/UI work demands fundamentally different feedback loops.** Backend: plan→build→review. Frontend: design→screenshot→fix→re-screenshot. Accepting this produces better results.

5. **Infrastructure decisions should be made before building on provisional foundations.** The Alpaca → Databento pivot (Sprint 12) and Alpaca → IBKR pivot (Sprint 13) represented provisional work. Deep research conversations were worth 10x their time.

---

## What Changed with the Metarepo Retrofit (DEC-250)

As of March 4, 2026, ARGUS adopts a structured workflow system:

- **Three-tier review system:** Close-out review (automated checks), Tier 2 implementation review (Claude Code), Tier 3 architectural review (Claude.ai)
- **Universal rules:** `.claude/rules/universal.md` codifies development standards
- **Sprint planning protocol:** Formal spec generation with session decomposition
- **Documentation tiers:** Tier A (operational context in Claude.ai Project Knowledge + `.claude/`) and Tier B (human-readable history in `docs/`)
- **Sprint numbering:** Continues from current (next sprint is 22)

---

## Phase G — Mid-Sprint Doc-Sync + Per-Session Register Discipline (Sprint 31.91, April 22–28, 2026)

Sprint 31.91 surfaced four process-improvement observations (F.1–F.4) that should inform the next campaign's RETRO-FOLD into the workflow metarepo. The observations were captured live in the sprint folder's `def-disposition-matrix.md` Section F and are reproduced here for cross-sprint persistence.

### F.1 — DEC-328 full-suite-at-Tier-1 process gap

**Surfaced by:** Post-S5e catalog freshness hotfix (`4c737d5`).

**Observation:** S5e Tier 2 reviewer + S5e closeout both reported scoped tests (`test_alerts.py` 12→15 + Vitest 902→913) without running full pytest. The catalog freshness gate (`tests/docs/test_architecture_api_catalog_freshness.py`, DEF-168 regression guard) only fires on full suite, so the missing audit endpoint in `docs/architecture.md` slipped through to CI on the S5e final commit `7efd0a0`. CI surfaced the failure on the next push; hotfix `4c737d5` regenerated the catalog row in a single mechanical commit. DEC-328 mandates "full suite required at sprint entry, each close-out, and final review" — scoped-only at Tier 1 boundary (S5e closeout) was the gap.

**Resolution path (next sprint planning):**

- Tighten DEC-328 with explicit "full suite required at Tier 1 boundary" language; OR
- Add a CI-side guard that fires on PR boundaries regardless of session-local test scope; OR
- Amend `templates/work-journal-closeout.md` to require explicit declaration of "full suite verified" vs "scoped only" — with mandatory full-suite-required at sprint-final-session boundary.

**Carry-forward target:** Next sprint planning conversation (Sprint 31.92 likely).

### F.2 — RULE-038 drift surface area (already addressed)

**Surfaced by:** Sprint 31.91's RULE-038 drift counts ranged from 2 (S5b: 2 stale line numbers) to 7 (S5d: 7 prompt-vs-current-code drifts).

**Observation:** Specific drift instances included (S5b) line-number references `:453` actual `~:570` and `:531` actual `~:416-420`; (S2b.2) spec line range `:1670-1750` for `order_manager.py` didn't actually contain claimed SELL-detection branching; (S5d) frontend path `frontend/src/` vs actual `argus/ui/src/`, `Layout.tsx` vs actual `AppShell.tsx`, hook contract drifts, 404 handling drift, 409-vs-200 backend behavior drift, test command drift, DEF numbering collisions; (S5e) similar layout-file drifts plus `/audit` endpoint pre-existence (triggered halt-and-fix), DEF numbering collisions (resolved via reviewer grep).

**Resolution:** Already addressed in workflow metarepo at `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment 2026-04-28) — implementation prompts now reference structural anchors (function names, class names, config keys) rather than line numbers, which drift. Ongoing reinforcement in next sprint planning recommended.

### F.3 — Per-session register discipline (pattern working)

**Observation:** The per-session register discipline formalized at S2a (workflow v1.2.0 — `protocols/in-flight-triage.md` § "Per-Session Register Discipline") held firm through 18 register refreshes covering 25 implementation sessions + 2 in-sprint hotfixes. Zero conversation drift across the entire sprint despite accumulated context from multiple Tier 3 reviews + amended verdicts + 9 mid-sprint DEF assignments. The `work-journal-register.md` is refreshed after every session close-out AND every Tier 3 verdict; even sessions that don't materially change the register receive a refresh with updated test counts, commit SHAs, and timestamps. Git history of the register file is the session-grain audit trail.

**Carry-forward:** N/A — pattern is working; document as positive case study for future sprint-planning reference. Recommend reuse for any sprint with ≥10 sessions, multiple Tier 3 reviews, or significant cross-session context dependencies.

### F.4 — Bookkeeping discipline (8 consecutive sessions clean)

**Observation:** S5a.2 + S5b + Impromptu A + Impromptu B + S5c + Impromptu C + S5d + S5e closeouts cited `tests_added` matching actual delta. S5a.1's +21 vs +18 cosmetic discrepancy was a one-off; RULE-038 sub-bullet feedback was internalized cleanly across the trailing 8 sessions.

**Carry-forward:** N/A — pattern is working; document as positive reinforcement. The pattern indicates that close-out skill discipline can be sustained across long sprints when reviewer + register both serve as bookkeeping anchors.

---

## Phase H — DEC-388 Alert Observability Pattern (Sprint 31.91)

Sprint 31.91 introduced the multi-emitter consumer pattern as the canonical reference for any future ARGUS subsystem requiring end-to-end observability. The pattern is documented as `docs/architecture.md` §14 Alert Observability Subsystem and is summarized as DEC-388 in the decision log. Key architectural choices that future similar subsystems should consider reusing:

1. **Per-emitter-type policy table** — decouples producers from consumers via a single registry of `PolicyEntry` rows mapping alert-type strings to predicate functions. Producer code only needs to publish `SystemAlertEvent(alert_type=<key>)`; consumer code dispatches via the table. AST-based regression guard at `tests/api/test_policy_table_exhaustiveness.py` enforces that every producer-side string literal appears as a table key.

2. **Migration framework as universal SQLite owner** — Sprint 31.91 introduced the framework at S5a.2 for `data/operations.db`, then extended it at Impromptu C to all 8 ARGUS SQLite DBs (sprint-spec D16 fulfilled). Each per-DB module follows the `argus/data/migrations/operations.py` template; each owning service's `initialize()` calls `apply_migrations()`; `schema_version` table tracks versions. Future DB schema evolution belongs in this framework, not in ad-hoc inline ALTERs.

3. **Pattern B sprint-close DEC materialization** — when a DEC's cross-references would otherwise document architecture-with-known-defects state (because the resolving sessions land later in-sprint), defer materialization to sprint-close. Sprint 31.91 deferred DEC-388 from Tier 3 #2 to D14 sprint-close because it cross-referenced 8 DEFs being resolved by Impromptus A+B+C and S5c. Pattern B is documented in `protocols/mid-sprint-doc-sync.md` v1.0.0.

4. **Cross-page mount at AppShell layer** — frontend observability surfaces (banners, toast stacks) belong at the layout layer (`AppShell.tsx`) rather than per-page. Sprint 31.91's S5e relocated 5 in-Dashboard banner mounts + 5 in-Dashboard toast mounts to `AppShell.tsx`; regression invariant 17 structurally pinned by `AppShell.alerts.test.tsx:163` (Dashboard → TradeLog → Performance navigation, banner persists across all transitions). This pattern protects against the "operator misses critical alert because they navigated to a different page" failure mode.

The retrofit preserves the core two-Claude workflow that drove the project's velocity while adding structure to prevent the documentation sync overhead that was becoming the primary bottleneck.
