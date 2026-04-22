# Audit: Primary Context Documents (CLAUDE.md + project-knowledge.md + architecture.md)
**Session:** P1-H1a
**Date:** 2026-04-21
**Scope:** Line-level compression audit of the three docs loaded into every Claude Code / Claude.ai session.
**Files examined:** 3 deep (CLAUDE.md 436L, project-knowledge.md 447L, architecture.md 2,819L) + 6 cross-reference (decision-log.md, dec-index.md, sprint-history.md, docs/architecture/, docs/amendments/, docs/operations/)
**Safety tag (all findings):** `safe-during-trading` — documentation edits touch no runtime code.

---

## FIX-14 Resolution (2026-04-22)

All 20 findings (H1A-01 through H1A-20) addressed by FIX-14-docs-primary-context (see `docs/sprints/sprint-31.9/FIX-14-closeout.md`).

**Line-count delta:**
- CLAUDE.md: 450 → 418 (−32, −7%) — conservative cut; DEF table detail preserved as load-bearing, prompt-relevant signal for active sessions.
- project-knowledge.md: 447 → 314 (−133, −30%) — aggressive trim (Key Components megalines compressed, Key Active Decisions subsections deduped against `dec-index.md`, Sprint History collapsed to last 20 rows, File Structure + Build Track + completed-infrastructure megalines pointed at canonical sources).
- architecture.md: 2,839 → ~2,746 (−93, −3%) — high-value removals applied (§10 NotificationService spec replaced by Deferred Components pointer, §11 "Shadow System" parallel-process concept removed as superseded by `StrategyMode.SHADOW`, §16 Tech Stack Summary replaced by pointer, §12 Config Files collapsed to pointer, stale "Future Module: intelligence" block removed, stale "Not yet implemented" Sprint 14 block removed, 2FA stale claim fixed, "Seven pages" → "Ten pages", version footer updated). H1A-18 (§3.9 startup phase sequence) was already resolved by FIX-03 — verified and marked `RESOLVED-VERIFIED`. H1A-19's aggressive target (~1,500 lines) deferred — see close-out notes.

**Sprint-31.9 campaign hygiene preserved:** DEF-172, DEF-173 strikethrough entries and DEF-175 live entry (all from IMPROMPTU 2026-04-22) untouched by this session. Impromptu changes verified post-edit via `grep -nE "DEF-(172|173|175)"`.

**Scope adherence:** Only the three files listed in the Scope block were modified. `workflow/` submodule + `docs/sprints/post-31.9-component-ownership/*` untouched.

---

## Executive Summary

1. **Architecture.md (2,819L) is the #1 compression target.** It is ~40–50% narrative archaeology (sprint-tagged mini-changelogs inside every section, resolved DEFs written up in the present tense, a "Future Module: `argus/intelligence/`" section talking about work completed 9+ months ago). Target trim: ~1,100 lines (-39%). Biggest single win: §3.4.x strategy write-ups duplicate `docs/strategies/STRATEGY_*.md` — replace 150 lines with a pointer table.
2. **CLAUDE.md (436L) violates its own "<=150 lines" rule (`.claude/rules/doc-updates.md` line 49) by ~3×.** Current bloat sources: 7 "Follow-on" sprint paragraphs (89L, belongs in sprint-history.md) and 153-row DEF table with 80 resolved strikethroughs. Target: ~210L (-52%). Keep the DEF table, but prune resolved DEFs to a one-line count-and-link to sprint-history.
3. **project-knowledge.md (447L) has two single-megalines each >20 KB** (L105 "Build Track Queue" and L130 "Completed infrastructure") that are prose dumps of the full build history. Each renders as a single paragraph in Claude's context. Target: ~260L (-42%) by splitting these megalines into structured bullets and pushing sprint archaeology to sprint-history.md.
4. **Total reduction available: 3,702 → 2,080 lines (~44%)** with no information loss — all removed content relocates to existing destinations (sprint-history.md, decision-log.md, docs/strategies/, docs/architecture/allocation-intelligence-vision.md). Conservative; aggressive compression could reach ~1,850.
5. **One active stale claim** — `architecture.md:2353` says "JWT authentication with 2FA" but 2FA has never been implemented (DEC-102 / DEC-351 ship single-factor JWT + bcrypt). Also ~15 sections describe components as "Not yet implemented" / "Planned for Sprint 24+" that have since shipped.

---

## Q1 — Cross-Document Duplication Matrix

Line refs use `L:start-end`. Numeric ranges from the deep reads above.

| Topic | CLAUDE.md | project-knowledge.md | architecture.md | Authoritative | Duplication to remove |
|---|---|---|---|---|---|
| Tech stack (Python, FastAPI, React, Databento, IBKR) | L:54 | L:170-178 | L:2788-2816 (§16) + L:1859-1874 (frontend table) + L:2110-2118 (§6.1) | project-knowledge.md L:170-178 | arch.md §16 (26 rows) + §6.1 is redundant with L:1859-1874; cut §16 entirely, cut §6.1 first 8 bullets |
| Repo structure / module map | L:59-96 | L:182-204 | — (implicit throughout) | **CLAUDE.md L:59-96** | project-knowledge.md L:182-204 duplicates with less detail — replace with "see CLAUDE.md" |
| Active strategies (15) | L:52 (one-line list) | L:213-231 (full table) | L:437-552 (§3.4.1–3.4.7 strategy-by-strategy) | project-knowledge.md L:213-231 table | arch.md §3.4.1–§3.4.7 (L:437-552, ~116L) duplicates 7 rows of that table; replace with a 2-line pointer to `docs/strategies/STRATEGY_*.md` |
| Sprint workflow / two-Claude / runner | — | L:342-379 | — | project-knowledge.md | — (not duplicated) |
| Risk Manager modification rules | L:188-194 | L:153 | L:585-645 (§3.5) | arch.md §3.5 for technical detail; CLAUDE.md for rule summary | project-knowledge.md L:153 is a one-line reprise — OK to keep |
| Regime classifier v2 (8 calculators) | — | L:149 | L:711-772 (§3.6.1, 62L) | arch.md §3.6.1 | project-knowledge.md L:149 is single-line summary — OK. But arch.md §3.6.1 replicates DEC-357/358 + the VIX config snippet which belongs in config doc |
| Event bus semantics | L:176-180 | L:161 | L:87-151 (§3.1, 65L) | arch.md §3.1 | CLAUDE.md + project-knowledge.md are one-line summaries — OK. Arch.md §3.1 event-type list at L:95-150 duplicates `core/events.py`; trim to "see core/events.py for current Event types" |
| Order Manager flatten paths | — | L:162 (megaline) | L:774-914 (§3.7, 141L) | arch.md §3.7 | project-knowledge.md L:162 megaline replicates ~40% of arch.md §3.7 — slash L:162 to pointer |
| Intelligence Layer / Quality Engine | L:54 | L:143 | L:1382-1444 (§3.11 + §3.Y) | project-knowledge.md L:143 | arch.md §3.11 narrative + sprint tags belong in decision log / sprint history |
| Experiment Pipeline | L:53 | L:164 (megaline) | L:2641-2785 (§15, 144L) | arch.md §15 (well-structured) | project-knowledge.md L:164 is a ~4KB single-line dump of §15 — replace with pointer |
| Learning Loop V1 | — | L:160 | L:1566-1643 (§3.11 subsection, 78L) | arch.md §3.11 subsection | project-knowledge.md L:160 is 2-paragraph megaline — OK to stay if split into bullets |
| Counterfactual Tracker | L:54 | L:159 | L:1469-1520 (§3.11 subsection) | arch.md §3.11 subsection | project-knowledge.md L:159 is a 2-paragraph megaline of the same content |
| BacktestEngine vs legacy VectorBT | L:222-227 | L:157 | L:1904-2001 (§5.1–§5.1.6, 97L) | arch.md §5.1.6 + §5.1–§5.1.5 as pointers | Arch.md §5.1–§5.1.5 writes up each of 5 legacy VectorBT files individually — collapse to a "VectorBT: 5 legacy files, see source" table |
| Universe Manager | L:201-203 | L:155 | L:1002-1069 (§3.7d, 68L) | arch.md §3.7d | — (not materially duplicated) |
| IntradayCandleStore | — | L:154 | L:874 (inline in §3.7) + elsewhere | project-knowledge.md L:154 | arch.md only sparsely references it — arguably under-documented |
| HistoricalQueryService | L:54 | L:166 | L:1130-1180 (§3.8.2, 51L) | arch.md §3.8.2 | project-knowledge.md L:166 is a verbose retread of §3.8.2 |
| 22-variant shadow fleet | L:50 | L:164 (end) | — | CLAUDE.md L:50 as current status | project-knowledge.md L:164 restates — replace with pointer |
| Sprint 31.75 cleanup tracker items | L:12 (follow-on paragraph) | L:105 (within megaline) | — | Ideally sprint-history.md | CLAUDE.md L:10-18 "Follow-on" paragraphs all belong in sprint-history.md |
| Open DEFs (authoritative table) | **L:263-416** | — | — | **CLAUDE.md L:263-416** (authoritative) | — (not duplicated — this is the right placement) |
| NYSE Holiday Calendar | L:54 | L:151 | L:1110-1126 (§3.8.1) | arch.md §3.8.1 | project-knowledge.md L:151 restates 90% of §3.8.1 |
| VIX Data Service | L:54 | L:150 | L:194 (inline) + L:763-772 (config block) | project-knowledge.md L:150 | arch.md VIX content scattered across 3 sections — consolidation opportunity |
| 7-page vs 10-page frontend drift | L:55 (10 pages) | L:140 (10 pages) | L:1810-1812 ("Seven pages delivered"), L:1814 ("Pages" section lists 10) | **STALE** in arch.md | arch.md L:1810 self-contradicts — "seven pages" + subsequent 10-page list |
| Two-tier design principles (DEC-109) | L:237 | — | — | CLAUDE.md | — |

**New atoms found during reading:**
- **Config file inventory** — CLAUDE.md L:90 is a one-line summary; arch.md §12 L:2435-2458 is a stale config-file tree (missing `historical_query.yaml`, `learning_loop.yaml`, `exit_management.yaml`, `counterfactual.yaml`, `experiments.yaml`, `overflow.yaml`, `vix_regime.yaml`). Arch.md §12 should be deleted or regenerated.
- **Accounting + Notifications scaffolding** — arch.md §10 (L:2400-2415) documents `NotificationService` in full as though implemented; confirmed empty by `argus/notifications/__init__.py` only. Same for `argus/accounting/` referenced in arch.md §2 data-flow diagram (L:57).
- **Future Module: `argus/intelligence/`** at arch.md L:2096-2104 — describes the intelligence module as "Not yet implemented" even though §3.11 already documents the shipped implementation 600+ lines earlier.

---

## Q2 — CLAUDE.md Line-Level Triage

| Lines | Content summary | Action | Destination |
|---|---|---|---|
| 1-4 | Title + "last updated" header | KEEP | — |
| 6-8 | Active sprint one-liner | KEEP (rewrite weekly) | — |
| 10 | Sprint 31.85 follow-on paragraph | RELOCATE | sprint-history.md |
| 12 | Sprint 31.75 follow-on paragraph | RELOCATE | sprint-history.md |
| 14 | Sprint 31.8 follow-on paragraph | RELOCATE | sprint-history.md |
| 16 | Apr 3-5 impromptu paragraph | RELOCATE | sprint-history.md |
| 18 | Sprint 31.5 "Last completed" paragraph | TRIM to 1 line | sprint-history.md (full) |
| 20-24 | Sprint 31A.75 / 31A.5 / 31A "Previous" paragraphs | RELOCATE | sprint-history.md |
| 26-37 | Roadmap amendments + build track | TRIM. Keep "Next: 31B" one-liner + link to roadmap.md | roadmap.md |
| 34 | Build track with 23 strikethrough entries | RELOCATE entire line | roadmap.md (authoritative) |
| 39-46 | Known Issues | KEEP — operational | — |
| 45-46 | Resolved issues with strikethrough | REMOVE | — (resolved, clutter) |
| 48-55 | Current State bullets | KEEP but TRIM. L:54 Infrastructure bullet is 4 KB of inline narrative — break into structured bullets or relocate feature inventory to project-knowledge.md | project-knowledge.md |
| 54 | Infrastructure megaline (~4.1KB in one line) | SPLIT into ~20 shorter bullets or move most to project-knowledge.md | project-knowledge.md L:130 area |
| 57-96 | Project Structure tree | KEEP — authoritative | — |
| 98-152 | Commands block | KEEP — operational | — |
| 154-157 | Environment variables | KEEP | — |
| 159-172 | Code Style | KEEP but consider pointing at `.claude/rules/code-style.md` | .claude/rules/code-style.md (already authoritative) |
| 174-233 | Architectural Rules (7 sub-sections) | KEEP. These are load-bearing rules Claude should see on every session. | — |
| 235-244 | UI/UX Rules | KEEP — short and load-bearing | — |
| 246-253 | Testing section | TRIM. Point to `.claude/rules/testing.md` (already authoritative) | .claude/rules/testing.md |
| 255-257 | Documentation Sync | KEEP | — |
| 259-262 | Deferred Items preamble | KEEP | — |
| 263-416 | **DEF table (153 rows)** | KEEP ACTIVE DEFs + COLLAPSE RESOLVED. ~80 resolved entries (strikethrough rows) contain full problem descriptions that belong in sprint-history.md. Replace each resolved row with one-line `~~DEF-NNN~~ Brief name — RESOLVED Sprint X (see sprint-history)`. | sprint-history.md for the detail |
| 265-273, 277, 279-280, 282, 287, 290-291, 300-301, 305-309, 314-326, 337-340, 348-350, 354-355, 374, 377, 382-385, 387-396, 398-402, 406-410, 412 | Resolved DEFs with full multi-line contextual detail | COLLAPSE each to 1 line | sprint-history.md |
| 265, 266, 269 | DEF-001/002/005 done ~19 sprints ago | REMOVE | — (archaeological) |
| 418-435 | Reference table | KEEP — load-bearing index | — |

**CLAUDE.md target: ~210L (-52%).** Keep all authoritative sections (Project Structure, Commands, Architectural Rules, UI/UX, DEF table structure, Reference index). Cut: sprint follow-on paragraphs (89L), build track line (1 big line), infrastructure megaline (split or relocate), resolved DEFs (80 rows × average 1.5L saved = ~120L).

---

## Q3 — project-knowledge.md Line-Level Triage

| Lines | Content summary | Action | Destination |
|---|---|---|---|
| 1-5 | Header + pointers | KEEP | — |
| 7-10 | "What Is ARGUS" | KEEP | — |
| 12-17 | Current State bullets | KEEP | — |
| 19-101 | **Sprint History table (83 rows)** | TRIM. Keep the last 10-15 rows for recent context; collapse rows pre-Sprint 25 to a single "Sprints 1-24: see sprint-history.md" entry. | sprint-history.md (already has all 83 rows) |
| 21-60 | Sprint 1-24 rows | COLLAPSE to a pointer | sprint-history.md |
| 103 | "Build Track Queue" | KEEP header | — |
| 105 | **Megaline #1: ~4 KB of build track history in one paragraph** | SPLIT into ~30 bullets OR collapse to a 5-line "most recent sprints" summary + pointer to roadmap.md | roadmap.md |
| 107-109 | Validation Track | KEEP — operational | — |
| 111-132 | Expanded Vision + completed infrastructure | TRIM. L:130 is the second megaline (~3.5 KB in one paragraph) listing every shipped feature — this duplicates the CLAUDE.md L:54 "Current State" bullet | — |
| 130 | **Megaline #2: completed infrastructure paragraph** | SPLIT into structured list or point to CLAUDE.md L:54 | CLAUDE.md already has the list |
| 132 | "Next" paragraph | KEEP one-liner, drop restated "DEF-161 resolved" etc. (already in DEF table) | — |
| 136-204 | Architecture section | TRIM. Most bullets duplicate arch.md. Keep 3-tier list + Key Components header as anchor; defer detail | architecture.md |
| 138-144 | Three-Tier System (5 sub-bullets, each 2-3KB) | TRIM each to 2-3 lines + pointer to arch.md section | architecture.md §3.x |
| 146-169 | **Key Components megalines** (strategies, patterns, observatory, regime, VIX, market calendar, orchestrator, risk manager, data service, universe manager, broker, backtesting, evaluation, counterfactual, learning loop, event bus, order manager, exit management, experiment pipeline, historical query, arena) — each a single ~2-4KB paragraph | TRIM each to 3-4 bullets. Current form is unreadable megaline dumps. Detail belongs in arch.md. | architecture.md |
| 147 | Strategies megaline (3.7 KB) | TRIM | arch.md §3.4.x |
| 154 | Data Service megaline (2.9 KB) | TRIM | arch.md §3.2 |
| 162 | Order Manager megaline (4.4 KB) | TRIM | arch.md §3.7 |
| 164 | Experiment Pipeline megaline (5.2 KB) | TRIM | arch.md §15 |
| 170-178 | Tech Stack | KEEP | — |
| 180-204 | File Structure tree | REMOVE — duplicates CLAUDE.md L:59-96 | CLAUDE.md |
| 206-207 | Naming Conventions | KEEP | — |
| 210-231 | Active Strategies table | KEEP — useful summary | — |
| 231 end | Cross-strategy paragraph | KEEP | — |
| 233-234 | Pipeline Stages | KEEP | — |
| 238-240 | Risk Limits | KEEP | — |
| 244-268 | Active Constraints | KEEP — operational | — |
| 263-265 | Sweep qualification constraints (multi-sprint) | TRIM. "Sweep representativeness PARTIALLY RESOLVED → RESOLVED via Sprint 31.85" is archaeology | sprint-history.md |
| 272-282 | Monthly Costs table | KEEP | — |
| 286-338 | **Key Active Decisions sections (14 subsections, 50+ lines)** | TRIM drastically. Each subsection lists 5-15 DEC numbers — `docs/dec-index.md` already exists and is authoritative. Replace with "See `docs/dec-index.md`" + maybe top 5 most-cited DECs | dec-index.md |
| 290, 292, 294, 296, 298, 300, 302, 304, 306, 308, 310, 312, 314, 316, 318, 320, 322, 324, 326, 328, 330, 332, 334, 336, 338 | Per-sprint DEC listings | REMOVE all | dec-index.md |
| 342-379 | Workflow section | TRIM. Runner description is 12 lines of detail that belong in `workflow/protocols/autonomous-sprint-runner.md` | workflow/protocols/ |
| 382-404 | Reference Documents table | KEEP | — |
| 406-441 | Key Learnings | KEEP — durable insights that need to stay visible. But these grow unbounded — establish a cap (e.g., 20 entries) and move older learnings to sprint-history.md | — |
| 407, 408, 409 | Learning Loop V1 advisory note (3 bullets) | KEEP | — |
| 420-424 | Sprint 31A-era learnings (lookback_bars, PMH, 24-sym set) | RELOCATE — these are sprint-specific; Key Learnings should be timeless | sprint-history.md Sprint 31A section |
| 427-441 | Sprint 31.85 learnings (10 bullets) | KEEP 2-3; relocate other sprint-specific ones | sprint-history.md Sprint 31.85 |
| 443 end | Communication Style | KEEP | — |

**project-knowledge.md target: ~260L (-42%).** Major cuts: sprint history table (-65L), 2 megalines (-80L condensed), DEC subsections (-50L), file structure (-22L), Key Components megaline dumps (-60L).

---

## Q4 — architecture.md Section-Level Triage (2,819 lines)

| Section | Lines | Keep / Trim / Relocate / Remove | Target Lines | Rationale |
|---|---|---|---|---|
| §1 System Tiers | L:8-23 (16) | KEEP | 16 | Entry-point taxonomy |
| §2 High-Level Data Flow diagram | L:25-81 (57) | TRIM. ASCII diagram at L:27-81 references "Accounting" + "Notifications Service" boxes that are empty scaffolding (verified `__init__.py` only). Remove dead boxes. | 45 | Technical accuracy |
| §3 Module Specifications header | L:85 | KEEP | 1 | — |
| §3.1 Event Bus | L:87-151 (65) | TRIM. Event-type list at L:95-150 reproduces `core/events.py` — will drift. Replace 55 lines of event sigs with pointer + 8 category examples | 30 | Single source of truth |
| §3.2 Data Service | L:152-234 (83) | TRIM. IndicatorEngine subsection + "Time-aware indicator warm-up" narrative (L:231-233) is sprint-tagged archaeology | 50 | — |
| §3.2b Data Flow Architecture ASCII | L:235-289 (55) | KEEP the diagram; TRIM the config narrative at L:275-287 (DEC-tag dense) | 30 | Diagram is load-bearing |
| §3.3 Broker Abstraction | L:290-323 (34) | KEEP | 34 | — |
| §3.3b Clock Protocol | L:325-338 (14) | KEEP | 14 | — |
| §3.3c IBKRBroker | L:340-366 (27) | TRIM. Last paragraph L:366 is sprint archaeology. | 20 | — |
| §3.4 Base Strategy | L:368-435 (68) | KEEP interface; TRIM inline method docstring prose | 50 | — |
| §3.4.1 ORB Family | L:437-450 (14) | KEEP — real reference content | 14 | — |
| §3.4.2 VWAP Reclaim | L:452-460 (9) | RELOCATE entire section | `docs/strategies/STRATEGY_VWAP_RECLAIM.md` | Already exists |
| §3.4.3 Afternoon Momentum | L:462-470 (9) | RELOCATE | STRATEGY_AFTERNOON_MOMENTUM.md | Already exists |
| §3.4.4 PatternModule Subsystem | L:472-520 (49) | KEEP (ABC + PatternBasedStrategy); TRIM `@dataclass` code blocks to signatures | 30 | — |
| §3.4.5 Red-to-Green | L:521-531 (11) | RELOCATE | STRATEGY_RED_TO_GREEN.md | Already exists |
| §3.4.6 Bull Flag | L:533-541 (9) | RELOCATE | STRATEGY_BULL_FLAG.md | Already exists |
| §3.4.7 Flat-Top Breakout | L:543-551 (9) | RELOCATE | STRATEGY_FLAT_TOP_BREAKOUT.md | Already exists |
| **(MISSING: §3.4.x for ABCD, GapAndGo, HODBreak, DipAndRip, PreMarketHighBreak, MicroPullback, VwapBounce, NarrowRangeBreakout)** | — | — | — | Arch.md is 2 sprints behind — 8 newer patterns undocumented. Better to replace all §3.4.x with a pointer table. |
| §3.4.8 Strategy Evaluation Telemetry | L:553-583 (31) | TRIM. Reference content is fine; L:562 sprint tag + L:583 sprint-specific "AfMo restructured" note are archaeology. | 20 | — |
| §3.5 Risk Manager | L:585-645 (61) | KEEP — load-bearing | 55 | Cut YAML snippet if repeated in config doc |
| §3.6 Orchestrator | L:647-709 (63) | TRIM. L:698-699 DEF-074 reference + sprint-tagged notes. Constructor signature + Supporting Components + Lifecycle are real reference. | 45 | — |
| §3.6.1 Regime Intelligence V2 | L:711-772 (62) | KEEP — genuinely load-bearing. TRIM inline YAML config samples (duplicate `config/regime.yaml`). | 45 | — |
| §3.7 Order Manager | L:774-914 (141) | TRIM hard. L:837 (Sprint 28.75 DEF-112 paragraph), L:879-880 (Sprint 28.5 AMD-7 block), ExecutionRecord dataclass at L:843-862 — all can compress. | 75 | — |
| §3.7b AlpacaScanner | L:916-955 (40) | REMOVE — Alpaca is incubator-only per DEC-086. Collapse to 3-line "AlpacaScanner: legacy incubator, see source" | 3 | — |
| §3.7c FMPScannerSource | L:957-1000 (44) | TRIM. 60% is YAML field descriptions. | 20 | — |
| §3.7d Universe Manager | L:1002-1069 (68) | KEEP (current + load-bearing); TRIM L:1069 "Implementation Status" sprint archaeology | 55 | — |
| §3.8 Health Monitor | L:1071-1108 (38) | KEEP | 35 | — |
| §3.8.1 NYSE Holiday Calendar | L:1110-1126 (17) | KEEP | 17 | — |
| §3.8.2 Historical Query Service | L:1130-1180 (51) | KEEP (current, load-bearing). TRIM L:1173-1179 "Phase 2 integration roadmap" which is aspirational | 40 | — |
| §3.9 System Entry Point | L:1183-1210 (28) | TRIM. The 12-phase list is wrong per P1-A1 finding M1 (code has 17 phases). Either REGENERATE to match main.py or REDUCE to "see main.py" | 10 | Drift risk |
| §3.10 Trade Logger schema | L:1212-1376 (165) | TRIM dramatically. 165 lines of SQL CREATE TABLE is essentially copying `argus/analytics/trade_log.py`. Replace with ER-diagram summary + pointer to source. | 30 | — |
| §3.10b Debrief Export | L:1378-1380 (3) | KEEP | 3 | — |
| §3.11 Intelligence Layer (catalyst, quality, counterfactual, exit mgmt, learning loop, etc.) | L:1382-1644 (263) | TRIM. This is 263 lines covering 6+ subsystems. Keep interface signatures, cut sprint tags / DEC enumeration / YAML duplicates. | 150 | — |
| §3.11 OrderFlowAnalyzer | L:1397-1407 (11) | REMOVE — explicitly post-revenue, not implemented. Move to a "Deferred components" note at bottom | 2 | — |
| §3.11 Catalyst details | L:1409-1467 (59) | TRIM sprint-tagged sub-paragraphs | 35 | — |
| §3.11 Counterfactual | L:1469-1520 (52) | TRIM | 30 | — |
| §3.11 Exit Management | L:1522-1549 (28) | TRIM | 20 | — |
| §3.11 PreMarketEngine "NOT YET IMPLEMENTED" | L:1551-1558 (8) | REMOVE — stale Sprint 23.5 note | 0 | — |
| §3.11 Learning Loop V1 | L:1566-1643 (78) | TRIM. Reduce 8 REST endpoint docstrings to a table | 45 | — |
| §3.Y AI Copilot | L:1645-1659 (15) | KEEP | 15 | — |
| §3.Z Sprint Runner | L:1661-1669 (9) | KEEP | 9 | — |
| §4 Command Center API | L:1672-1806 (135) | TRIM. "Implementation Status (Sprint 14)" header is stale — "Not yet implemented" block at L:1689-1697 lists features shipped since Sprint 14. REST endpoint list is load-bearing. | 80 | — |
| §4 "Not yet implemented" (Sprint 14) | L:1689-1697 | REMOVE — all shipped | 0 | Stale |
| §4 REST endpoint listing | L:1699-1783 (85) | KEEP — load-bearing. Verify each endpoint exists (several have sprint dates but may be current) | 80 | — |
| §4 WebSocket | L:1785-1798 (14) | KEEP | 14 | — |
| §4 Authentication | L:1800-1806 (7) | KEEP | 7 | — |
| §4.1 Command Center Frontend | L:1808-1902 (95) | TRIM. L:1810 says "Seven pages delivered" but §4.1 Pages section lists 10. Fix header, trim page-by-page prose that duplicates project-knowledge.md + CLAUDE.md | 50 | — |
| §5 Backtesting Toolkit header | L:1904-1906 (3) | KEEP | 3 | — |
| §5.1 VectorBT base | L:1908-1930 (23) | TRIM | 15 | — |
| §5.1.1–5.1.5 (5 VectorBT variants) | L:1932-1951 (20) | COLLAPSE to one 4-row table | 6 | — |
| §5.1.6 BacktestEngine | L:1953-2001 (49) | KEEP — load-bearing current content | 40 | — |
| §5.2 Replay Harness | L:2003-2034 (32) | TRIM (remove sprint tags, "from Sprint 3", etc.) | 22 | — |
| §5.3 Walk-Forward | L:2036-2044 (9) | KEEP | 9 | — |
| §5.4 Performance Metrics | L:2046-2054 (9) | KEEP | 9 | — |
| §5.5 Report Generator | L:2056-2062 (7) | KEEP | 7 | — |
| §5.6 Directory Structure | L:2064-2094 (31) | TRIM. Duplicates CLAUDE.md project tree. | 10 | — |
| **§ Future Module: `argus/intelligence/`** | L:2096-2104 (9) | **REMOVE ENTIRELY — STALE.** Says "Not yet implemented" for a module that has 30+ files shipping as of Sprint 28. | 0 | — |
| §6 Command Center (Tier 2) | L:2108-2165 (58) | TRIM heavily. L:2120-2142 "Dashboard Pages" reproduces content from §4.1. Keep only technology stack summary. | 20 | — |
| §6.3 Mobile Access (DEC-080) | L:2144-2164 (21) | KEEP | 21 | — |
| §7 AI Layer | L:2168-2342 (175) | TRIM. WebSocket protocol + REST endpoint listings are load-bearing; in-line code blocks are verbose. | 95 | — |
| §7.2 Module structure | L:2182-2197 (16) | KEEP | 16 | — |
| §7.3 Claude Client code block | L:2199-2216 (18) | TRIM to signature + 1 line | 5 | — |
| §7.4 Context Builder code block | L:2218-2243 (26) | TRIM to signature + 1 line | 6 | — |
| §7.5–§7.7 | L:2245-2292 (48) | TRIM code blocks; keep semantics | 25 | — |
| §7.8 WebSocket streaming | L:2294-2311 (18) | KEEP (protocol ref) | 18 | — |
| §7.9 REST Endpoints | L:2313-2325 (13) | KEEP | 13 | — |
| §7.10 Frontend Components | L:2327-2340 (14) | KEEP | 14 | — |
| §8 Security Architecture | L:2344-2368 (25) | TRIM. **L:2353 "JWT with 2FA" is stale** — no 2FA has ever shipped. Remove "with 2FA". L:2346 "age-encrypted or SOPS" is aspirational; actual is `.env` per current implementation. | 18 | Stale claims |
| §9 Deployment Architecture | L:2372-2396 (25) | TRIM. Aspirational (AWS EC2, systemd, Nginx, UptimeRobot) — actual is Steven's local Mac. Mark clearly as "target architecture" or remove. | 10 | Aspirational |
| **§10 Notification Service** | L:2400-2415 (16) | **REMOVE ENTIRELY — DEAD CODE.** `argus/notifications/` contains only `__init__.py` (verified). The abstraction is only referenced via `HealthMonitor` webhook field. | 0 | — |
| **§11 Shadow System** | L:2425-2431 (7) | **REMOVE — SUPERSEDED.** "Shadow System" as a parallel process concept was replaced by StrategyMode enum + CounterfactualTracker (Sprint 27.7). Retaining creates a conceptual conflict. | 0 | — |
| **§12 Configuration Files** | L:2435-2458 (24) | TRIM or REMOVE. Lists 5 of 12 actual YAML files. Missing `historical_query.yaml`, `learning_loop.yaml`, `exit_management.yaml`, `counterfactual.yaml`, `experiments.yaml`, `overflow.yaml`, `vix_regime.yaml`, `quality_engine.yaml`, `regime.yaml`. Collapse to "see `config/` directory" or regenerate. | 8 | — |
| §13 Observatory Subsystem | L:2462-2534 (73) | TRIM frontend prose (L:2495-2527 is design narrative) | 40 | — |
| §13.5 The Arena | L:2536-2578 (43) | KEEP — recent, load-bearing | 40 | — |
| §14 Evaluation Framework | L:2581-2637 (57) | KEEP — load-bearing reference | 50 | — |
| §15 Experiment Pipeline | L:2641-2785 (145) | TRIM. Well-structured but verbose; collapse sub-section narratives to interface signatures. | 80 | — |
| §15.10 Allocation Intelligence Vision | L:2740-2748 (9) | RELOCATE — is a summary of `docs/architecture/allocation-intelligence-vision.md` | docs/architecture/ (already exists) |
| §15.11 Config YAML sample | L:2750-2765 (16) | REMOVE — duplicates `config/experiments.yaml` | 0 | — |
| §15.12 Directory Structure | L:2767-2784 (18) | REMOVE — duplicates CLAUDE.md + `argus/intelligence/experiments/` speaks for itself | 0 | — |
| **§16 Technology Stack Summary** | L:2788-2816 (29) | **REMOVE** — duplicates project-knowledge.md §Tech Stack + CLAUDE.md frontend bullets. Also contains aspirational items ("consider PostgreSQL for scale", "Firebase/Telegram"). | 0 | — |
| End-of-doc version footer | L:2819 | KEEP + update version | 1 | — |

**PF-10 — architecture.md target line count: ~1,750 lines (-38%).**
Justification: The doc has three kinds of content.
1. **Genuinely load-bearing reference** (~1,500L target): Event Bus semantics, Data Service interface + IndicatorEngine, Broker ABC, Clock, Base Strategy, Risk Manager, Orchestrator + Regime V2, Order Manager core, Universe Manager, Health Monitor + Market Calendar, Historical Query Service, Trade Logger schema (trimmed to summary), Intelligence Layer interfaces, AI Layer WS + REST + module structure, Walk-forward + BacktestEngine, Observatory + Arena, Evaluation Framework, Experiment Pipeline — all keep with 30-50% trim.
2. **Per-strategy mini-docs** (relocated): §3.4.2–§3.4.7 (~60L) move wholesale to `docs/strategies/STRATEGY_*.md` which already exist. Arch.md keeps a 15-line pointer table.
3. **Dead / stale / duplicate content** (deleted or relocated, ~650L): §10 NotificationService (dead), §11 Shadow System (superseded), §16 Tech Stack Summary (duplicate), "Future Module: intelligence" block (stale), §12 config files list (stale), §5.6 Directory Structure (duplicate), Alpaca* sections (incubator-only), "Not yet implemented" Sprint 14 blocks, Sprint tag archaeology throughout.

Aggressive-but-defensible target: ~1,500L (-47%). Conservative: 1,750L (-38%). Report target reflects conservative.

---

## Q5 — Stale Content List

- **architecture.md:2353** — "Dashboard protected by JWT authentication with 2FA". **No 2FA has ever been implemented.** DEC-102 shipped single-factor password + JWT; DEC-351 (Sprint 25.8) hardened to 401 response with bcrypt. Remove "with 2FA".
- **architecture.md:1183-1210 (§3.9)** — "12-phase startup sequence" enumeration. Per P1-A1 finding M1, actual main.py runs 17 phases (adds 8.5, 10.25, 10.3, 10.5, 10.7). Silently wrong on 5 items and wrong about L:1199 "Set viable universe on DataService" Phase 10.5 (actual 10.5 is now Event Routing).
- **architecture.md:1810** — "Seven pages delivered with responsive design" (Sprint 21d). Actual is **10 pages** (Arena added Sprint 32.75, Experiments Sprint 32.5, Observatory Sprint 25). The same section at L:1814-1832 correctly lists 10 pages; the header is internally contradictory.
- **architecture.md:1676-1697** — "Implementation Status (Sprint 14) — Not yet implemented" list includes PUT strategies, pause/resume, Orchestrator status, Risk status, Emergency controls, Approval workflow, Learning journal, Claude API integration. **All have shipped** between Sprints 15 and 28. This section misleads any new-contributor Claude session about what exists.
- **architecture.md:1551-1558 (§3.11 PreMarketEngine)** — "NOT YET IMPLEMENTED. Status: Planned for Sprint 24+". The catalyst pipeline + briefing generation shipped Sprint 23.5. This content is 7 months stale.
- **architecture.md:2096-2104 (§ Future Module: intelligence)** — "Not yet implemented" block for a module with 30+ source files plus subpackages (intelligence/learning/, intelligence/experiments/, intelligence/catalyst/) that shipped across Sprints 22–28.
- **architecture.md:2400-2415 (§10 NotificationService)** — Full interface spec for a class that has never been implemented. `argus/notifications/` is `__init__.py` only (verified). `HealthMonitor` uses an inline webhook URL, not this abstraction.
- **architecture.md:2425-2431 (§11 Shadow System)** — "A parallel instance of the full trading engine running in paper mode" as a separate process. Superseded by StrategyMode (LIVE/SHADOW) on BaseStrategy + CounterfactualTracker (Sprint 27.7). The §11 concept was never built; keeping it creates conceptual conflict with the actual shadow mode.
- **architecture.md:2435-2458 (§12 Configuration Files)** — YAML file listing is incomplete. Missing: `counterfactual.yaml`, `exit_management.yaml`, `experiments.yaml`, `historical_query.yaml`, `learning_loop.yaml`, `overflow.yaml`, `quality_engine.yaml`, `regime.yaml`, `vix_regime.yaml`. Contains `brokers.yaml` which I do not see in `config/`.
- **architecture.md:2372-2396 (§9 Deployment)** — "Production: AWS EC2 t3.medium us-east-1, Ubuntu 24 LTS, systemd, Nginx reverse proxy, SQLite on VPS, backed up daily to S3". Actual deployment is Steven's local Mac (macOS 23.4.0 per env). Should be marked "Target production architecture (post-revenue)".
- **architecture.md:2788-2816 (§16 Technology Stack Summary)** — Row "Database: SQLite (production: consider PostgreSQL for scale)" — aspirational. Row "Deployment: AWS EC2 / systemd / Nginx" — same issue as above. Row "Notifications: Firebase/Telegram Bot API/SendGrid/Discord Webhook" — references unimplemented NotificationService.
- **architecture.md:2819** — Version footer reads "v1.3 (updated Sprint 28 — Learning Loop V1)". Since Sprint 28, the doc has been updated for at least Sprints 28.5, 28.75, 29, 29.5, 32, 32.5, 32.75, 32.8, 32.9, 31A, 31A.5, 31A.75, 31.5, 31.75, 31.85 — so the version marker is ~18 sprints stale.
- **project-knowledge.md:392** — "All 381 DEC entries with full rationale (no new DECs in Sprints 32–32.9 ...)". Actual count is 383 (DEC-382/383 added Sprint 31.75). Matches CLAUDE.md L:422.
- **project-knowledge.md:394** — "Complete sprint history (1–29.5 + 32–31A.75 + sub-sprints)". Missing 31.5, 31.75, 31.8, 31.85.
- **project-knowledge.md:105 (Build Track)** — Multiple "planned for Sprint 34" / "Sprint 36+" references embedded in the middle of a multi-kilobyte paragraph — hard to spot drift.
- **CLAUDE.md:424** — "Complete sprint history (1–29.5 + 32–31A.5 + sub-sprints)". Same stale range issue.
- **CLAUDE.md:422** — "383 DEC entries with full rationale (no new DECs in Sprints 32–31A.5, 31.8, or 31.85 — all design decisions followed established patterns)". Technically correct but parenthetical is archaeology; will age poorly.
- **CLAUDE.md:102** — `# Full suite (~4,858 tests, ~114s with xdist)`. Actual per the same file L:51 is 4,934 tests. Test count drifts every sprint.
- **CLAUDE.md:33** — "DEC ranges reserved: 396–402 (33.5)". Only 383 DECs exist today; 33.5 has not started. Fine but worth flagging the pre-allocation.
- **project-knowledge.md:152 (Orchestrator bullet)** — references DEF-074 "Dual regime recheck path" as open. P1-A1 finding M10 confirms it is still open, so this is CURRENT not stale. No action.

---

## Q6 — Forward-Looking Content

- **CLAUDE.md:27-33** (Roadmap Amendments adopted March 23, 2026) — Adopts 5 sprint slots (27.5 ✅, 27.6 ✅, 27.7 ✅, 32.5 ✅, 33.5 pending). 4 of 5 shipped. **Action:** Replace the adoption block with a single line "See `docs/amendments/` for adopted amendments". Keep 33.5 reference in the DEC range reservation table if anywhere.
- **CLAUDE.md:34** (Build Track) — Mixes completed sprints (21 strikethroughs) with planned sprints (30, 31B, 33, 33.5, 34, 35–41). **Action:** Trim strikethroughs (move to sprint-history.md); keep only upcoming.
- **project-knowledge.md:105** (megaline Build Track) — Same issue; also embeds DEC-380/DEC-238/DEC-353/DEC-358 references mid-paragraph.
- **project-knowledge.md:115-118** (Three phases of repertoire growth) — Sprint 32 (shipped), ~Sprint 33 (planned), Sprint 36+ (planned). **Action:** Mark phases 2/3 as PLANNED explicitly.
- **architecture.md:1383-1386 (§3.11 header)** — "These are distinct from core trading engine modules" — accurate. OK.
- **architecture.md:1397-1407 (§3.11 OrderFlowAnalyzer)** — Labeled "POST-REVENUE (DEC-238)". Correctly forward-looking. **Action:** Move to a dedicated "§X Deferred Components" appendix so reference readers don't confuse with shipped Intelligence Layer.
- **architecture.md:1551-1558 (§3.11 PreMarketEngine)** — Labeled "NOT YET IMPLEMENTED. Status: Planned for Sprint 24+". Has been superseded; should be REMOVED, not relocated.
- **architecture.md:2096-2104 (§ Future Module: argus/intelligence/)** — STALE (see Q5). REMOVE.
- **architecture.md:2740-2748 (§15.10 Allocation Intelligence Vision)** — Phase 1 (~Sprint 34–35), Phase 2 (~Sprint 38+). **Action:** Compress to 3-line pointer; full vision already in `docs/architecture/allocation-intelligence-vision.md`.
- **architecture.md:2372-2396 (§9 Deployment Architecture)** — "Production" section describes aspirational deployment. **Action:** Rename to "§9 Target Deployment (post-revenue)" and mark current as "Local-only".
- **architecture.md:2344-2368 (§8 Security)** — "Production: consider AWS Secrets Manager or HashiCorp Vault" — aspirational. Fine if marked. Currently presented as current.
- **architecture.md:2788-2816 (§16)** — "Database: SQLite (production: consider PostgreSQL for scale)" — aspirational phrasing. Remove the parenthetical or put in a separate scaling section.
- **project-knowledge.md:282** — `Databento Plus (live L2/L3) | $1,399/mo | Post-revenue (DEC-238)`. Correctly marked. OK.

---

## Q7 — Relative Link / Path Audit

Spot-checked links. Status:

- **CLAUDE.md:33** — `docs/amendments/roadmap-amendment-experiment-infrastructure.md` → **EXISTS** ✓
- **CLAUDE.md:33** — `docs/amendments/roadmap-amendment-intelligence-architecture.md` → **EXISTS** ✓
- **CLAUDE.md:227** — `.claude/rules/backtesting.md` → **EXISTS** (loaded at session start) ✓
- **CLAUDE.md:257** — `.claude/skills/doc-sync.md` → not verified — Claude Code skills live at workflow/; file may or may not exist. VERIFY in Phase 3.
- **CLAUDE.md:418-435 (Reference table)** — All 13 docs referenced:
  - `docs/decision-log.md` ✓ (4701L)
  - `docs/dec-index.md` ✓ (506L)
  - `docs/sprint-history.md` ✓ (2909L)
  - `docs/pre-live-transition-checklist.md` ✓
  - `docs/process-evolution.md` ✓
  - `docs/live-operations.md` ✓
  - `docs/strategies/STRATEGY_*.md` ✓ (15 files)
  - `docs/risk-register.md` ✓
  - `docs/project-bible.md` ✓
  - `docs/architecture.md` ✓
  - `docs/roadmap.md` ✓
  - `docs/sprint-campaign.md` ✓
  - `docs/ui/ux-feature-backlog.md` ✓
  - `.claude/rules/` directory exists ✓
- **project-knowledge.md:385-403 (Reference table)** — All verified present except:
  - `docs/protocols/market-session-debrief.md` ✓ (verified)
- **project-knowledge.md:338** — `docs/amendments/` ✓
- **project-knowledge.md:394** — `docs/sprint-history.md` ✓
- **project-knowledge.md:417** — no broken link, but text references "Sprint 32 found 7 such discrepancies" — not verifiable in a doc audit. VERIFY Phase 3 if Phase 3 touches strategy template validation.
- **architecture.md:1069** — `docs/amendments/` — ✓
- **architecture.md:1183** (§3.9 points to main.py) — conceptual; main.py exists.
- **architecture.md:2087** — `docs/backtesting/DATA_INVENTORY.md` — **BROKEN?** VERIFY — doc listing shows `docs/backtesting/` but I did not enumerate files there.
- **architecture.md:2087** — `docs/backtesting/BACKTEST_RUN_LOG.md` — same VERIFY.
- **architecture.md:2087** — `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` — same VERIFY.
- **architecture.md:2168** — "Implemented in Sprint 22 (March 2026). See DEC-264 through DEC-274." — DEC references exist in decision-log.md ✓
- **architecture.md:2740** — `docs/architecture/allocation-intelligence-vision.md` — ✓ exists.
- **project-knowledge.md:249** — `docs/ibc-setup.md` — ✓ exists.
- **project-knowledge.md:265** — `docs/operations/parquet-cache-layout.md` — ✓ exists.

**Broken or suspect references:**
1. VERIFY `docs/backtesting/DATA_INVENTORY.md`, `docs/backtesting/BACKTEST_RUN_LOG.md`, `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` (architecture.md:2087) — not confirmed existing in my doc enum.
2. `.claude/skills/doc-sync.md` (CLAUDE.md:257) — skill referenced but not confirmed present in project .claude/ (may live in workflow submodule).
3. **architecture.md:1816** — No broken reference but footer says "1712 pytest + 257 Vitest tests" — stale count (current: 4,934 + 846).

No evidence of widespread broken cross-references. The docs are generally well-maintained linkwise; the problems are content volume and staleness, not structural rot.

---

## Q8 — Proposed Target State

| File | Current | Conservative Target | Aggressive Target | Primary cuts |
|---|---:|---:|---:|---|
| CLAUDE.md | 436 | **210** (-52%) | 175 (-60%) | Follow-on sprint paragraphs (89L) → sprint-history.md; build track strikethroughs → roadmap.md; infrastructure megaline L:54 → project-knowledge.md; ~80 resolved DEFs collapsed to 1-line each (-120L); TBC rules sections → `.claude/rules/` pointers |
| project-knowledge.md | 447 | **260** (-42%) | 225 (-50%) | Sprint history table rows 1-60 (Sprints 1-24) → sprint-history.md pointer; 2 megalines (L:105, L:130) split into bullets or moved to CLAUDE.md/roadmap.md; Key Active Decisions sections (L:286-338) → dec-index.md; file structure tree → CLAUDE.md pointer; Key Components megalines → trimmed to 3-bullet summaries pointing at architecture.md |
| architecture.md | 2,819 | **1,750** (-38%) | 1,500 (-47%) | §3.4.2–§3.4.7 strategy mini-docs (-60L) → STRATEGY_*.md (already exist); §10 NotificationService (-16L) remove; §11 Shadow System (-7L) remove; §16 Tech Stack Summary (-29L) remove duplicate; §12 Config Files (-24L) remove stale; "Future Module: intelligence" (-9L) remove; "Not yet implemented" Sprint 14 block (-9L) remove; §3.10 trade log SQL schema (-135L → pointer to source); Trim all sprint-tagged narrative throughout; Clarify aspirational sections (§8, §9) |
| **Total** | **3,702** | **2,220** (-40%) | 1,900 (-49%) | |

**Reduction delivered in target state: ~1,480 lines removed (-40%).**

Rationale for the conservative vs aggressive split:
- Conservative target preserves code blocks + config snippets + method signatures where they provide load-bearing reference. Aggressive target additionally converts all code blocks to one-line signatures + "see source".
- Preference: conservative. Aggressive loses some onboarding value.

---

## Positive Observations

1. **CLAUDE.md DEF table structure** (L:263-416) is the right home for active issue tracking. 73 active DEFs visible at-a-glance is exactly what a Claude session needs to check before touching adjacent code. Only the *mixing* of resolved+active in one table is problematic.
2. **CLAUDE.md Architectural Rules section** (L:174-233) is dense, high-signal, and load-bearing. Nearly every session benefits from seeing the Event Bus / Risk / Data / Config rules as bullets. Keep as-is.
3. **CLAUDE.md Project Structure tree** (L:59-96) is the single best module map in the repo — specific enough to route file lookups, concise enough to scan. Project-knowledge.md L:180-204 duplicates this with less detail; the CLAUDE.md version should be authoritative.
4. **architecture.md §1–§3 core module specifications** (Event Bus, DataService, Broker, Clock, Base Strategy) are genuinely well-written reference material — canonical for how to build adapters and new strategies. These should stay.
5. **architecture.md §3.6.1 Regime Intelligence** (L:711-772) is an example of how a sprint-era feature should be documented — structured, interface-first, minimal sprint tagging. Replicate this style elsewhere.
6. **architecture.md §13 Observatory** + **§13.5 Arena** + **§14 Evaluation Framework** + **§15 Experiment Pipeline** — all recent additions, well-structured, appropriate density. Can trim but don't replicate old-style narrative drift.
7. **project-knowledge.md "Key Learnings" section** (L:406-441) captures durable insights not found in any other doc (e.g., "`getattr(pos, 'qty', 0)` silently returns 0 on Position objects"). These are the kind of gotcha-bullets that save Phase 3 sessions from re-discovering the same bugs. Should be preserved and growth-managed (rolling cap + graduation to sprint-history.md).
8. **project-knowledge.md "Active Strategies" table** (L:213-231) is the canonical 15-strategy inventory. Compact, unambiguous, includes window/hold/mechanic. Keep.
9. **The link hygiene is strong.** Of 40+ cross-references I sampled, 38 resolved correctly. The repo has not drifted into broken-link rot — the compression audit can proceed with confidence that relocation targets actually exist.
10. **Explicit "superseded" markers in project-knowledge.md:338** (DEC-031/089/097/165/234 listed by supersession chain) is a pattern that prevents zombie context. Worth replicating wherever a decision pivots.

---

## Statistics

- Files deep-read: **3** (CLAUDE.md 436L, project-knowledge.md 447L, architecture.md 2,819L = 3,702 total)
- Files cross-referenced: **6** (decision-log.md, dec-index.md, sprint-history.md, docs/architecture/ listing, docs/amendments/ listing, docs/operations/ listing) + argus/accounting/ + argus/notifications/ scaffolding checks
- Total findings: **actionable triage items across 3 docs**
  - Q1 duplication matrix: **21 topic atoms** mapped, ~13 with actionable de-dup
  - Q2 CLAUDE.md: **13 triage rows** (~15 distinct actions)
  - Q3 project-knowledge.md: **14 triage rows** with specific line ranges
  - Q4 architecture.md: **60+ sections** triaged (~30 KEEP, 20 TRIM, 8 RELOCATE, 5 REMOVE)
  - Q5 stale content: **15 specific instances** cited with line numbers
  - Q6 forward-looking: **10 items** flagged
  - Q7 links: **~40 sampled**, 3 VERIFY items, 0 confirmed-broken
- Reduction target: **1,480 lines (−40% of 3,702)** — conservative; aggressive path yields −49%.
- Safety distribution: **100% safe-during-trading** (no runtime code touched).
- Estimated Phase 3 fix effort: **4 sessions** (sized by destination, not by doc):
  - **Session A (weekday, ~45 min):** CLAUDE.md compression — cut follow-on paragraphs, prune resolved DEFs to one-liners, move infrastructure megaline.
  - **Session B (weekday, ~45 min):** project-knowledge.md compression — trim sprint table, split 2 megalines, cut Key Active Decisions subsections, trim Key Components megalines.
  - **Session C (weekday, ~60 min):** architecture.md removals — §10 NotificationService, §11 Shadow System, §16 Tech Stack Summary, §12 Config Files, "Future Module" block, "Not yet implemented" block, Alpaca* sections, relocate §3.4.2–§3.4.7 strategy docs (verify STRATEGY_*.md completeness first).
  - **Session D (weekday, ~90 min):** architecture.md rewrite — §3.9 startup phases (align to main.py 17-phase reality, coordinates with P1-A1 M1), §3.10 trade log schema (compress to ER diagram), §4.1 seven→ten pages, §8.2 remove "2FA", §9 mark deployment aspirational, update footer version.

All findings safe to commit changes via normal PR during market hours. No runtime touched.
