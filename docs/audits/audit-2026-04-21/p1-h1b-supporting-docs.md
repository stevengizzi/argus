# Audit: Supporting Documentation (everything except the 3 primary context files)
**Session:** P1-H1b
**Date:** 2026-04-21
**Scope:** All `.md` files under `docs/` except CLAUDE.md, project-knowledge.md, architecture.md, and the `docs/sprints/` artifact trail.
**Files examined:** 51 (15 strategy docs + 13 top-level + 15 subdirectory + 8 archived; plan expected 50 but `docs/archived/` has 8 files, not 7 — extra is `argus_unified_vision_roadmap.md`).
**Safety tag (all findings):** `safe-during-trading` — no runtime code touched. Phase 3 fix sessions are pure doc edits.

---

## Executive Summary

1. **The docs estate is in materially better health than expected** after 89 sprints. Six governance docs (decision-log, dec-index, sprint-history, roadmap, risk-register, project-bible) are all **CURRENT** — sync is tight, no orphaned DECs, no stale risk reviews that block anything. Compression is the primary need (covered by P1-H1a); deletion is rarely needed.
2. **One doc is structurally obsolete: [docs/paper-trading-guide.md](docs/paper-trading-guide.md).** 33 Alpaca references, `--paper` flag, `ALPACA_BASE_URL`, Alpaca dashboard validation — every procedural section assumes a broker that was demoted to incubator-only by DEC-086 over a year ago. Anyone following this guide will fail. **Recommend: rewrite for IBKR paper or delete and replace with a thin pointer to [docs/live-operations.md](docs/live-operations.md#paper-trading).**
3. **One doc is a historical artifact that should be frozen: [docs/process-evolution.md](docs/process-evolution.md).** Narrative stops at Sprint 21.5 (Feb 27, 2026); missing Sprints 22–31.85 (~52 days, ~40 sprints & sub-sprints). Either freeze with an explicit "Historical Reference Only — through Sprint 21.5" header or refresh through Sprint 31.85.
4. **Two amendment docs never flipped from "Proposal — not yet adopted" to "Adopted".** [docs/amendments/roadmap-amendment-experiment-infrastructure.md](docs/amendments/roadmap-amendment-experiment-infrastructure.md) proposed Sprint 27.5 + 32.5 (both shipped ✓). [docs/amendments/roadmap-amendment-intelligence-architecture.md](docs/amendments/roadmap-amendment-intelligence-architecture.md) proposed Sprint 27.6 + 27.7 + 33.5 (27.6 + 27.7 shipped ✓; 33.5 pending). Header status is stale.
5. **DEC-360 (bearish_trending regime) doc lag.** Code has `bearish_trending` in every strategy's `allowed_regimes`; **zero strategy docs mention `bearish_trending`** (verified via grep). Three docs — [STRATEGY_AFTERNOON_MOMENTUM.md](docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md), [STRATEGY_BULL_FLAG.md](docs/strategies/STRATEGY_BULL_FLAG.md), [STRATEGY_RED_TO_GREEN.md](docs/strategies/STRATEGY_RED_TO_GREEN.md) — list narrower regime sets and need explicit updates.
6. **Broken cross-references — 3 high-visibility + 43 sprint-history.** Two supersession references in [docs/roadmap.md:6](docs/roadmap.md#L6) point at wrong directories (missing `archived/` prefix). Same pair repeats in [docs/decision-log.md:2907](docs/decision-log.md#L2907). A third reference points at a never-created `docs/argus_master_sprint_plan.md`. Across `docs/sprints/`, 43 sprint files still reference old numeric-prefix filenames (`01_PROJECT_BIBLE.md`, etc.) that were renamed to kebab-case. Low operator impact (sprint/ is artifact trail) but silently broken if grepped.
7. **All 8 archived docs are correctly inert.** No active DEC or DEF cites an archived version as authoritative. `docs/archived/10_PHASE3_SPRINT_PLAN.md` is the only one still referenced by historical sprint files (Sprints 1–21.5), but none after 21.5 — supersession by `roadmap.md` is complete.

---

## Section 1 — Per-File Verdict Table (all 51 files)

Verdicts: **CURRENT** / **STALE-SALVAGE** (stale but salvageable with targeted updates) / **STALE-REWRITE** (needs major rewrite) / **FREEZE** (freeze as historical artifact) / **ARCHIVE** (move to `docs/archived/`) / **OK-ARCHIVED** (correctly in `docs/archived/`).

### Top-level docs (13)

| File | Size | Last Meaningful Update | Verdict | Top Issue |
|---|---:|---|---|---|
| [project-bible.md](docs/project-bible.md) | 40 KB | Feb 20 v1.0 / Apr 20 refresh | **CURRENT** | §4.2 strategy roster missing Micro Pullback, VWAP Bounce, Narrow Range Breakout; §4.3 incubator pipeline uses old 10-stage terminology instead of DEC-382 shadow-first. Not invariant violation, just list drift. |
| [roadmap.md](docs/roadmap.md) | 105 KB | Apr 5 v3.5 | **CURRENT** | Line 6 has 2 broken supersession refs (missing `archived/` prefix). Build-track aligned with CLAUDE.md; DEC refs valid. |
| [decision-log.md](docs/decision-log.md) | 412 KB | Apr 20 | **CURRENT** | DEC-001 → DEC-383; all 5 supersessions marked. Line 2907 has same 2 broken refs as roadmap.md + 1 never-existed file. |
| [dec-index.md](docs/dec-index.md) | 39 KB | Apr 20 | **CURRENT** | Perfect 1:1 sync with decision-log; superseded DECs marked with ○ consistently. |
| [sprint-history.md](docs/sprint-history.md) | 228 KB | Apr 20 | **CURRENT** | Fully updated through Sprint 31.85. No missing sprints. |
| [sprint-campaign.md](docs/sprint-campaign.md) | 111 KB | Apr 1 | **STALE-SALVAGE** | Header says "Updated: Sprint 28 complete, Sprint 28.5 next" — 21 days + ~15 sprints stale. Doc is a *process template*, not a sprint queue, so role separation is correct, but the header misleads. |
| [risk-register.md](docs/risk-register.md) | 71 KB | Apr 20 | **CURRENT** | 17 ASM + 63 RSK entries. 1 past-due review date (ASM-015 Feb 26) but marked CLOSED Feb 28 with DEC-236. No unresolved stale entries. |
| [live-operations.md](docs/live-operations.md) | 21 KB | Apr 20 v1.3 | **CURRENT** | Matches `scripts/start_live.sh` + Sprint 32.9 state. Databento + IBKR paper. |
| [paper-trading-guide.md](docs/paper-trading-guide.md) | 20 KB | Feb 16 v1.0 | **STALE-REWRITE** | **CRITICAL drift.** 33 Alpaca references; `python -m argus.main --paper` flag (Alpaca-specific legacy); `ALPACA_BASE_URL=https://paper-api.alpaca.markets`; Alpaca dashboard validation. Whole doc presumes the demoted broker. |
| [pre-live-transition-checklist.md](docs/pre-live-transition-checklist.md) | 11 KB | Apr 2 | **CURRENT** | All Sprint 27.75 paper overrides (10× risk, throttle disabled, $10 floor) documented; signal_cutoff_time 15:30 documented. No Alpaca refs. |
| [process-evolution.md](docs/process-evolution.md) | 13 KB | Mar 6 | **FREEZE** | Stops at Sprint 21.5. Missing Sprints 22–31.85 (~52 days). Historical narrative that never got a lifecycle decision. Freeze with explicit header, or refresh. |
| [strategy-template.md](docs/strategy-template.md) | 6 KB | Feb 15 | **CURRENT** | Still the template for all 15 strategy docs. Missing optional sections for Shadow Mode status, Experiment Variant ID, Quality Grade calibration — non-blocking but would improve variant tracking (e.g. Dip-and-Rip's 2 shadow variants have no template field). |
| [ibc-setup.md](docs/ibc-setup.md) | 7.6 KB | Apr 1 | **CURRENT** | Current, IBKR-only. Minor: does not mention the Sprint 32.75 post-reconnect 3s hardcoded delay (documented in pre-live-checklist instead). |

### Strategy docs (15) — detail in Section 2

| File | Verdict | Top Issue |
|---|---|---|
| [STRATEGY_ABCD.md](docs/strategies/STRATEGY_ABCD.md) | STALE-SALVAGE | Stub; no PROVISIONAL marker; Sprint 32.9 shadow demotion aware |
| [STRATEGY_AFTERNOON_MOMENTUM.md](docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md) | STALE-REWRITE | Regime section omits bearish_trending (DEC-360) |
| [STRATEGY_BULL_FLAG.md](docs/strategies/STRATEGY_BULL_FLAG.md) | STALE-REWRITE | Regime section omits bearish_trending |
| [STRATEGY_DIP_AND_RIP.md](docs/strategies/STRATEGY_DIP_AND_RIP.md) | STALE-SALVAGE | Stub; no mention of 2 shadow variants (v2/v3) in experiments.yaml |
| [STRATEGY_FLAT_TOP_BREAKOUT.md](docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md) | STALE-SALVAGE | Aware of Sprint 32.9 shadow demotion; backtest placeholder unfilled |
| [STRATEGY_GAP_AND_GO.md](docs/strategies/STRATEGY_GAP_AND_GO.md) | STALE-SALVAGE | Stub; notes pre-DEF-152 sweep invalid; no updated validation |
| [STRATEGY_HOD_BREAK.md](docs/strategies/STRATEGY_HOD_BREAK.md) | STALE-SALVAGE | Stub; no backtest results; no PROVISIONAL caveat |
| [STRATEGY_MICRO_PULLBACK.md](docs/strategies/STRATEGY_MICRO_PULLBACK.md) | STALE-SALVAGE | Stub; Sprint 31A S3 aware; 24-sym sweep noted non-qualifying |
| [STRATEGY_NARROW_RANGE_BREAKOUT.md](docs/strategies/STRATEGY_NARROW_RANGE_BREAKOUT.md) | STALE-SALVAGE | Stub; Sprint 31A S5 aware; 2-trade sweep noted |
| [STRATEGY_ORB_BREAKOUT.md](docs/strategies/STRATEGY_ORB_BREAKOUT.md) | **CURRENT** | Most comprehensive; PROVISIONAL caveat present; extensive WFE |
| [STRATEGY_ORB_SCALP.md](docs/strategies/STRATEGY_ORB_SCALP.md) | STALE-SALVAGE | VectorBT results mixed; no walk-forward; PROVISIONAL present |
| [STRATEGY_PREMARKET_HIGH_BREAK.md](docs/strategies/STRATEGY_PREMARKET_HIGH_BREAK.md) | STALE-SALVAGE | Stub; no backtest validation |
| [STRATEGY_RED_TO_GREEN.md](docs/strategies/STRATEGY_RED_TO_GREEN.md) | STALE-REWRITE | Regime section omits bearish_trending (code has it hardcoded) |
| [STRATEGY_VWAP_BOUNCE.md](docs/strategies/STRATEGY_VWAP_BOUNCE.md) | STALE-SALVAGE | Stub; DEF-154 param rework documented; no PROVISIONAL |
| [STRATEGY_VWAP_RECLAIM.md](docs/strategies/STRATEGY_VWAP_RECLAIM.md) | STALE-SALVAGE | Full template; backtest placeholders unfilled; PROVISIONAL present |

### Subdirectory docs (15)

| File | Verdict | Top Issue |
|---|---|---|
| [amendments/roadmap-amendment-experiment-infrastructure.md](docs/amendments/roadmap-amendment-experiment-infrastructure.md) | **STALE-SALVAGE** | Header says "Proposal — not yet adopted" but 27.5 + 32.5 shipped |
| [amendments/roadmap-amendment-intelligence-architecture.md](docs/amendments/roadmap-amendment-intelligence-architecture.md) | **STALE-SALVAGE** | Same "not yet adopted" stamp; 27.6 + 27.7 shipped; 33.5 pending |
| [architecture/allocation-intelligence-vision.md](docs/architecture/allocation-intelligence-vision.md) | **CURRENT** | Vision doc (DEF-133); Phase 1 ~Sprint 34-35 target; aligned |
| [backtesting/BACKTEST_RUN_LOG.md](docs/backtesting/BACKTEST_RUN_LOG.md) | **ARCHIVE** | Final entry Run 8 (Feb 17). Pre-live artifact, 63 days stale |
| [backtesting/DATA_INVENTORY.md](docs/backtesting/DATA_INVENTORY.md) | **ARCHIVE** | Feb 17. Describes Alpaca IEX feed; superseded by Databento + Sprint 31.85 parquet-cache-layout.md |
| [backtesting/PARAMETER_VALIDATION_REPORT.md](docs/backtesting/PARAMETER_VALIDATION_REPORT.md) | **CURRENT** | ORB validation; extended walk-forward; DEC-076 params still live |
| [guides/autonomous-process-guide.md](docs/guides/autonomous-process-guide.md) | **CURRENT** | Autonomous runner infra; mode valid though rarely used. Scripts still exist |
| [guides/human-in-the-loop-process-guide.md](docs/guides/human-in-the-loop-process-guide.md) | **CURRENT** | Primary active mode |
| [operations/parquet-cache-layout.md](docs/operations/parquet-cache-layout.md) | **CURRENT** | Sprint 31.85 canonical reference; operator repoint documented |
| [protocols/README.md](docs/protocols/README.md) | **CURRENT** | Stub pointing at `workflow/protocols/` submodule — correct pattern |
| [protocols/market-session-debrief.md](docs/protocols/market-session-debrief.md) | **CURRENT** | 7-phase runbook; Sprint 32.9 additions (margin circuit, signal cutoff, shadow phase) present |
| [research/argus_execution_broker_research_report.md](docs/research/argus_execution_broker_research_report.md) | **CURRENT** | DEC-086 artifact; still informative as background. Mark "Archaeological" but keep |
| [research/argus_market_data_research_report.md](docs/research/argus_market_data_research_report.md) | **CURRENT** | DEC-082 artifact; reframing rationale still load-bearing |
| [ui/performance-workbench-brief.md](docs/ui/performance-workbench-brief.md) | **CURRENT** | DEC-229 design brief; deferred, waiting dependencies |
| [ui/ux-feature-backlog.md](docs/ui/ux-feature-backlog.md) | **CURRENT** | Canonical UI/UX inventory; Sprint 32.8 updates present |

### Archived docs (8) — detail in Section 9

| File | Verdict | Note |
|---|---|---|
| [archived/02_PROJECT_KNOWLEDGE.md](docs/archived/02_PROJECT_KNOWLEDGE.md) | **OK-ARCHIVED** | Superseded by `docs/project-knowledge.md` |
| [archived/07_PHASE1_SPRINT_PLAN.md](docs/archived/07_PHASE1_SPRINT_PLAN.md) | **OK-ARCHIVED** | Superseded by `sprint-history.md` |
| [archived/09_PHASE2_SPRINT_PLAN.md](docs/archived/09_PHASE2_SPRINT_PLAN.md) | **OK-ARCHIVED** | Superseded by `sprint-history.md` |
| [archived/10_PHASE3_SPRINT_PLAN.md](docs/archived/10_PHASE3_SPRINT_PLAN.md) | **OK-ARCHIVED-W/NOTE** | Still referenced by 43 historical sprint files (1-21.5); add "Last active: Sprint 21.5" note in archived index |
| [archived/ARGUS_Expanded_Roadmap.md](docs/archived/ARGUS_Expanded_Roadmap.md) | **OK-ARCHIVED** | Superseded by `roadmap.md` (DEC-375) |
| [archived/argus-retrofit-advisory.md](docs/archived/argus-retrofit-advisory.md) | **OK-ARCHIVED** | Completed advisory |
| [archived/argus-retrofit-execution-guide.md](docs/archived/argus-retrofit-execution-guide.md) | **OK-ARCHIVED** | Completed guide |
| [archived/argus_unified_vision_roadmap.md](docs/archived/argus_unified_vision_roadmap.md) | **OK-ARCHIVED** | Not in audit plan (plan listed 7; disk has 8). Superseded by `roadmap.md` (DEC-375) |

---

## Section 2 — 15-Row Strategy-Doc Matrix

| Strategy | Template OK | Params Match Code | Mode Matches Config | Sprint 31A/32.9 Aware | PROVISIONAL Caveat | Verdict |
|---|---|---|---|---|---|---|
| ABCD | stub | partial | shadow ✓ | yes (32.9 demotion) | missing | STALE-SALVAGE |
| Afternoon Momentum | full | good | live ✓ | no | present | STALE-REWRITE (regime) |
| Bull Flag | full | good | live ✓ | partial | present | STALE-REWRITE (regime) |
| Dip-and-Rip | stub | partial | live ✓ | yes | missing | STALE-SALVAGE |
| Flat-Top Breakout | full | good | shadow ✓ | yes (32.9 demotion) | present | STALE-SALVAGE |
| Gap-and-Go | stub | partial | live ✓ | yes (DEF-152) | partial | STALE-SALVAGE |
| HOD Break | stub | partial | live ✓ | no | missing | STALE-SALVAGE |
| Micro Pullback | stub | partial | live ✓ | yes (31A S3) | partial | STALE-SALVAGE |
| Narrow Range Breakout | stub | partial | live ✓ | yes (31A S5) | partial | STALE-SALVAGE |
| ORB Breakout | full | good | live ✓ | no | present | **CURRENT** |
| ORB Scalp | full | good | live ✓ | no | present | STALE-SALVAGE |
| Pre-Market High Break | stub | partial | live ✓ | no | missing | STALE-SALVAGE |
| Red-to-Green | full | good | live ✓ | no | present | STALE-REWRITE (regime) |
| VWAP Bounce | stub | good (DEF-154) | live ✓ | yes (DEF-154) | missing | STALE-SALVAGE |
| VWAP Reclaim | full | good | live ✓ | no | present | STALE-SALVAGE |

### Template Drift
Two distinct formats — intentional, not drift. 7 full-template docs (pre-Sprint 29 era, with Backtest Results sections) and 8 stub docs (PatternModule era, minimal format). Both formats internally consistent. Recommendation: leave the bifurcation; the stubs were appropriate for patterns shipped without full backtest campaigns.

### Missing / Orphaned Coverage
**Perfect coverage.** All 10 PatternModule patterns in [argus/strategies/patterns/](argus/strategies/patterns/) have docs. All 3 non-pattern strategies (ORB Breakout, ORB Scalp, Afternoon Momentum) + Red-to-Green + VWAP Reclaim have docs. No orphaned docs, no missing docs. (Note: VWAP Reclaim is a standalone [BaseStrategy](argus/strategies/vwap_reclaim.py) subclass, not in `patterns/` — intentional per DEC-136.)

### Bearish_Trending Regime Gap (DEC-360)
Grep confirms **zero strategy docs mention `bearish_trending`**. Code has it in every strategy's `allowed_regimes` list. Three docs with explicit regime language need updating:

1. [STRATEGY_AFTERNOON_MOMENTUM.md](docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md) — Market Conditions section lists "Bullish Trending, High Volatility"; code allows bearish_trending + range_bound.
2. [STRATEGY_BULL_FLAG.md](docs/strategies/STRATEGY_BULL_FLAG.md) — lists "Bullish Trending, Range-Bound"; PatternBasedStrategy base allows bearish_trending.
3. [STRATEGY_RED_TO_GREEN.md](docs/strategies/STRATEGY_RED_TO_GREEN.md) — lists "Bullish Trending, Range-Bound"; code hardcodes `["bullish_trending", "bearish_trending", "range_bound"]`.

### PROVISIONAL / DEC-132 Caveat Coverage
Full-template docs 6/6 present. Stub docs 0/8 present (or partial). Severity is lower for stubs (no backtest to provisionalize) but consistency is worth fixing.

---

## Section 3 — decision-log.md ↔ dec-index.md Consistency (Q3)

### Highest DEC Number
- `decision-log.md` highest entry: **DEC-383** ✓
- `dec-index.md` highest entry: **DEC-383** ✓
- CLAUDE.md claim: **383 DECs total (DEC-382/383 added Sprint 31.75)** ✓
- All three match. No DEC drift.

### Superseded Markers
| DEC | dec-index marker | decision-log Status | Aligned? |
|---|---|---|---|
| DEC-031 | ○ Superseded by DEC-083 | Superseded by DEC-083 | ✓ |
| DEC-089 | ○ Superseded by DEC-248 | Superseded by DEC-248 | ✓ |
| DEC-097 | ○ Superseded by DEC-143/161 | Superseded by DEC-143/161 | ✓ |
| DEC-165 | ○ Superseded by DEC-237 | Superseded by DEC-237 | ✓ |
| DEC-234 | ○ Superseded by DEC-248 | Superseded by DEC-248 | ✓ |
| DEC-004 | ● Active | Active | ✓ (project-knowledge.md previously listed this as superseded; actually active per DEC-380 reframe) |

### Missing / Orphaned
**None.** No DEC referenced in one file missing from the other. Both files have the same 383 rows.

### Consistency Verdict
**PASS.** The index-log pair is the healthiest doc pair in the repo. Phase 3 effort: zero.

---

## Section 4 — sprint-history.md ↔ sprint-campaign.md Role Separation (Q4)

**sprint-history.md** is retrospective (what happened). **sprint-campaign.md** is process-template / choreography (how we run a sprint), **not** a rolling sprint queue. Role separation is intact; there is no drift of completed sprints into the campaign file or future plans into the history file.

### Missing Sprints from sprint-history.md
None. All Sprint 31.x (31A, 31A.5, 31A.75, 31.5, 31.75, 31.8, 31.85) and Sprint 32.9 are present.

### Stale Content in sprint-campaign.md
- Header: "Updated: Sprint 28 complete (Learning Loop V1), Sprint 28.5 next" — 21 days + ~15 sprints stale.
- Impact: low (document is a process template, not a sprint queue). Fix: one-line header update.

### Role Separation Verdict
**PASS-WITH-STALE-HEADER.** Structural separation clean; header needs a touch.

---

## Section 5 — risk-register.md Staleness (Q5)

**17 ASM + 63 RSK = 80 total entries.**

### Past-Due Review Dates
- **ASM-015** (IBKR account status) — Review Date Feb 26, 2026 → **PAST DUE but marked CLOSED Feb 28 (DEC-236)**. No action.

### Entries Mitigated by Shipped Work (but still appearing as open)
- **RSK-006** (Edge Decay) — Status Open; partially mitigated by Sprint 28 Learning Loop but full mitigation waits on Performance Workbench (Sprint 40+). Keep open.
- **RSK-007** (Data Quality Issues) — Status Open; substantially mitigated by Databento EQUS.MINI (DEC-248). Consider closing or re-scoping.
- **RSK-018** (News Scanner Signal-to-Noise) — Status Open; mitigated by Sprint 23 Catalyst Pipeline. Consider closing.
- **RSK-028** (Mean-Reversion Tail Risk) — Status Open; mitigated by Sprint 28.5 Exit Management. Consider closing.

### Orphan / Superseded ASMs
None obvious. Earliest entries (ASM-001 PDT Reform, ASM-002 Alpaca Reliability) are appropriately framed with "Low priority — incubator only" or "Monthly until resolved."

### Verdict
**PASS.** Risk register is actively maintained. 3-4 RSK entries are candidates for close/re-scope in the next doc-sync pass (not blocking).

---

## Section 6 — Operations Docs Cross-Consistency (Q6)

### live-operations.md ↔ paper-trading-guide.md ↔ pre-live-transition-checklist.md

**CRITICAL CONTRADICTION: Broker identity.**

- **live-operations.md** — Databento (data) + IBKR (execution). Uses `./scripts/start_live.sh`, IB Gateway port 4002 (paper) / 4001 (live). Current.
- **pre-live-transition-checklist.md** — Databento + IBKR. Documents DEC-083 (IBKR as sole execution). Current.
- **paper-trading-guide.md** — **Alpaca**. 33 Alpaca references. §2 "Create Your Alpaca Account"; §2.3 `ALPACA_API_KEY`, `ALPACA_BASE_URL=https://paper-api.alpaca.markets`; startup `python -m argus.main --paper` (Alpaca-specific legacy flag); validation steps reference Alpaca dashboard + Activity history. **Entire doc obsolete.**

### Sprint 27.75 Paper-Trading Overrides
- 10× risk reduction (A+: 0.002–0.003 vs live 0.02–0.03) — documented in pre-live-checklist line 16 ✓
- Throttle disabled (`suspension_sharpe_threshold: -999.0`) — line 28 ✓
- $10 min risk floor (`min_position_risk_dollars: 10`) — line 40 ✓
- All three align with `config/system.yaml` and CLAUDE.md Sprint 27.75 block.

### start_live.sh Pre-Flight Check Count
- live-operations.md describes 4 pre-flight checks ✓
- `scripts/start_live.sh` lines 46–72: 4 checks (.env, IB Gateway port 4002, DATABENTO_API_KEY, no existing process) ✓
- Match.

### Verdict
**CRITICAL: paper-trading-guide.md is structurally obsolete and must be rewritten or replaced.** Phase 3 fix session required.

---

## Section 7 — Amendments Absorption Verdict (Q7)

Both amendments were proposed in Claude.ai strategic planning conversations (March 23, 2026) as roadmap additions. Both have since shipped (in whole or in substantial part) yet neither document was updated to mark adoption.

### roadmap-amendment-experiment-infrastructure.md
- Proposes: Sprint 27.5 (Evaluation Framework) + Sprint 32.5 (Experiment Registry + Promotion Pipeline).
- CLAUDE.md confirms: **27.5 ✅** (MultiObjectiveResult, EnsembleResult, Pareto dominance, tiered confidence); **32.5 ✅** (Partitioned SQLite registry, cohort-based promotion, simulated-paper screening, overnight experiment queue, kill switches, anti-fragility).
- Document header still says "Status: Proposal — not yet adopted (v2 revision)". **Stale.**

### roadmap-amendment-intelligence-architecture.md
- Proposes: Sprint 27.6 (RegimeVector) + Sprint 27.7 (Counterfactual Engine) + Sprint 33.5 (Adversarial Stress Testing).
- CLAUDE.md confirms: **27.6 ✅** (RegimeVector replaces MarketRegime enum); **27.7 ✅** (Shadow position tracking for rejected signals); **33.5 PENDING** (DEC 396–402 reserved, sprint not yet started).
- Document header still says "Status: Proposal — not yet adopted". **Stale.**

### Verdict
**Both amendments absorbed.** Update headers to "Adopted — Shipped as DEC-357 and subsequent sprints" (experiment) and "Adopted — 27.6 + 27.7 shipped; 33.5 pending" (intelligence). Keep in place (not archived) because they contain fuller rationale than the final sprint plans preserved in sprint-history.

---

## Section 8 — Research / Backtesting / Guides / Protocols / UI Verdicts

### Research (Q8)
Both reports (`argus_execution_broker_research_report.md`, `argus_market_data_research_report.md`) drove **load-bearing decisions (DEC-082, DEC-086)** that are still active. They explain *why* IBKR over Alpaca and *why* Databento over IQFeed — reasoning that is non-obvious and continues to shape the data/execution stack. **Keep both.** Recommend adding "Archaeological Record — decision artifact" banner to the top so readers know these are not active proposals.

### Backtesting (Q9)
- **BACKTEST_RUN_LOG.md** — Final entry Run 8 (Feb 17, 2026). Pre-live artifact. **ARCHIVE.**
- **DATA_INVENTORY.md** — Feb 17, 2026. Describes Alpaca IEX feed (deprecated). Superseded by Databento + Sprint 31.85 `parquet-cache-layout.md`. **ARCHIVE.**
- **PARAMETER_VALIDATION_REPORT.md** — Feb 17 baseline + Feb 20 extended walk-forward (Sprint 11). DEC-076 params are still the live ORB params. **KEEP.**

### Guides (Q10)
Both autonomous and human-in-the-loop modes are still operational. Autonomous runner infra (`scripts/sprint-runner.py`) exists and ran through Sprint 23.2 S3–S6. Human-in-the-loop is the primary active mode per CLAUDE.md. Both docs **CURRENT**.

### Protocols (Q11)
- **README.md** — Correct stub pointing at `workflow/protocols/` submodule. **KEEP.**
- **market-session-debrief.md** — 7-phase runbook. Sprint 32.9 additions (margin circuit, signal cutoff, shadow/counterfactual phases) are present. Active operational doc. **KEEP.**

### UI (Q12)
- **performance-workbench-brief.md** — DEC-229 design brief, deferred until Performance page visualizations complete. Valid, waiting on implementation. **KEEP.**
- **ux-feature-backlog.md** — Canonical UI/UX inventory. Sprint 32.8 deferred items present. Actively referenced during sprint planning. **KEEP.**

### allocation-intelligence-vision.md
- DEF-133 Apr 1 2026 vision (Sprint 32.5 S8). Phase 1 ~Sprint 34-35, Phase 2 ~Sprint 38+. Aligned with roadmap. **KEEP.**

---

## Section 9 — Archived Folder Confirmation (PF-08)

**Plan expected 7 files; disk has 8.** Extra is `argus_unified_vision_roadmap.md`, which is correctly superseded by roadmap.md per DEC-375.

| File | Type | Superseded By | Active DEC/DEF ref? | Verdict |
|---|---|---|---|---|
| 02_PROJECT_KNOWLEDGE.md | Project context snapshot (Mar 3) | `project-knowledge.md` (v4.5 Apr 20) | None | **OK-ARCHIVED** |
| 07_PHASE1_SPRINT_PLAN.md | Phase 1 plan (Feb 16) | `sprint-history.md` | None | **OK-ARCHIVED** |
| 09_PHASE2_SPRINT_PLAN.md | Phase 2 plan (Feb 16) | `sprint-history.md` | None | **OK-ARCHIVED** |
| 10_PHASE3_SPRINT_PLAN.md | Phase 3 active sprint plan (Feb 19) | `roadmap.md` + `sprint-history.md` | **43 historical sprint files (Sprints 1–21.5)** reference this as authoritative. None after 21.5. | **OK-ARCHIVED-with-note** (add "Last active: Sprint 21.5, superseded by roadmap.md at DEC-375" banner) |
| ARGUS_Expanded_Roadmap.md | Original vision doc (Feb 26) | `roadmap.md` (DEC-375) | `decision-log.md:2907` cites as consolidated — but with broken path (see Section 11) | **OK-ARCHIVED** |
| argus-retrofit-advisory.md | Metarepo retrofit planning (Mar 4) | — (task-specific, completed) | None | **OK-ARCHIVED** |
| argus-retrofit-execution-guide.md | Step-by-step retrofit procedures | — | None | **OK-ARCHIVED** |
| argus_unified_vision_roadmap.md | Unified vision v2 (Mar 5) | `roadmap.md` (DEC-375) | `decision-log.md:2907` + `roadmap.md:6` cite as consolidated (both refs broken — see Section 11) | **OK-ARCHIVED** |

### PF-08 Verdict
**All 8 files are correctly inert.** No active DEC or DEF entry treats an archived file as authoritative. One (`10_PHASE3_SPRINT_PLAN.md`) is still referenced by historical sprint artifacts — add a one-line banner at its top explaining when it was last active.

---

## Section 10 — Cross-Reference Integrity (Q14)

### Broken docs-internal References

| Source | Line | Target | Actual Location | Impact |
|---|---|---|---|---|
| [docs/roadmap.md](docs/roadmap.md) | 6 | `docs/research/ARGUS_Expanded_Roadmap.md` | `docs/archived/ARGUS_Expanded_Roadmap.md` | HIGH (canonical doc) |
| [docs/roadmap.md](docs/roadmap.md) | 6 | `docs/argus_unified_vision_roadmap.md` | `docs/archived/argus_unified_vision_roadmap.md` | HIGH (canonical doc) |
| [docs/roadmap.md](docs/roadmap.md) | 6 | `docs/10_PHASE3_SPRINT_PLAN.md` | `docs/archived/10_PHASE3_SPRINT_PLAN.md` | HIGH (canonical doc) |
| [docs/decision-log.md](docs/decision-log.md) | 2907 | `docs/research/ARGUS_Expanded_Roadmap.md` | `docs/archived/ARGUS_Expanded_Roadmap.md` | MEDIUM |
| [docs/decision-log.md](docs/decision-log.md) | 2907 | `docs/argus_unified_vision_roadmap.md` | `docs/archived/argus_unified_vision_roadmap.md` | MEDIUM |
| [docs/decision-log.md](docs/decision-log.md) | 2907 | `docs/argus_master_sprint_plan.md` | **NEVER EXISTED** | LOW (listed as consolidated but was a placeholder) |
| [docs/sprints/*.md](docs/sprints/) (43 files) | various | `docs/01_PROJECT_BIBLE.md` | `docs/project-bible.md` | LOW (artifact trail) |
| [docs/sprints/*.md](docs/sprints/) (43 files) | various | `docs/03_ARCHITECTURE.md` | `docs/architecture.md` | LOW |
| [docs/sprints/*.md](docs/sprints/) (43 files) | various | `docs/04_STRATEGY_TEMPLATE.md` | `docs/strategy-template.md` | LOW |
| [docs/sprints/*.md](docs/sprints/) (43 files) | various | `docs/05_DECISION_LOG.md` | `docs/decision-log.md` | LOW |

### Confirmed-OK References
- [docs/backtesting/DATA_INVENTORY.md](docs/backtesting/DATA_INVENTORY.md) — exists ✓ (prior P1-H1a flagged as VERIFY)
- [docs/backtesting/BACKTEST_RUN_LOG.md](docs/backtesting/BACKTEST_RUN_LOG.md) — exists ✓
- [docs/backtesting/PARAMETER_VALIDATION_REPORT.md](docs/backtesting/PARAMETER_VALIDATION_REPORT.md) — exists ✓
- [.claude/skills/doc-sync.md](.claude/skills/doc-sync.md) — exists ✓ (symlink to workflow/claude/skills/doc-sync.md; CLAUDE.md:257 reference resolves)

### External Links (sampled, not fetched)
No malformed URLs found in 10-link sample. Valid Databento (`https://databento.com/signup`, `https://databento.com/pricing`), Anthropic (`https://console.anthropic.com/`), GitHub, localhost dev-server URLs. No deprecated paths in the sample.

### Phase 3 Fix Estimate
- **Three-line fix** in roadmap.md:6 + decision-log.md:2907 (prepend `archived/` to 2 paths each + delete reference to never-existed file).
- **Separate global search-replace task** in `docs/sprints/` for the 43 historical filename references (LOW priority — artifact trail only).

---

## Section 11 — Phase 3 Fix-Session Estimate

Grouped by file-overlap + safety (all `safe-during-trading`):

| Session | Files | Scope | Est. Effort |
|---|---|---|---|
| **A** | `docs/paper-trading-guide.md` | Full rewrite for IBKR paper trading, or delete + replace with pointer to live-operations.md | 2–3 h |
| **B** | `docs/process-evolution.md` | Freeze with "Historical Reference Only" header, **or** refresh through Sprint 31.85 | 1–2 h |
| **C** | `docs/amendments/*.md` (2 files) | Flip headers from "Proposal — not yet adopted" to "Adopted — shipped as [DEC refs]" | 15 min |
| **D** | `docs/strategies/STRATEGY_{AFTERNOON_MOMENTUM,BULL_FLAG,RED_TO_GREEN}.md` | Add bearish_trending to Market Conditions section (DEC-360 alignment) | 30 min |
| **E** | `docs/strategies/*.md` (8 stub docs) | Add explicit PROVISIONAL / DEC-132 caveat to stub-format strategy docs | 45 min |
| **F** | `docs/roadmap.md`, `docs/decision-log.md` | Fix 5 broken cross-references (+ drop never-existed file ref) | 15 min |
| **G** | `docs/backtesting/{BACKTEST_RUN_LOG,DATA_INVENTORY}.md` | Move to `docs/archived/`; update any inbound refs | 30 min |
| **H** | `docs/research/*.md` (2 files) | Prepend "Archaeological Record — decision artifact" banner | 15 min |
| **I** | `docs/sprint-campaign.md` | Header touch-up (Sprint 28 → Sprint 31.85) | 10 min |
| **J** | `docs/risk-register.md` | Review + close 3-4 RSK entries mitigated by shipped sprints (RSK-007, RSK-018, RSK-028) | 30 min |
| **K** | `docs/project-bible.md` | Add 3 newer patterns to §4.2 roster; refresh §4.3 pipeline wording to DEC-382 shadow-first | 30 min |
| **L** | `docs/sprints/*.md` (43 files) | Global search-replace of `01_PROJECT_BIBLE.md` / `03_ARCHITECTURE.md` / `04_STRATEGY_TEMPLATE.md` / `05_DECISION_LOG.md` to current kebab-case names | 30 min (scripted) |

Total estimated effort: **~8–10 hours** across 12 discrete fix sessions. Safety distribution: **100% safe-during-trading**. All can run during market hours.

---

## Positive Observations

1. **Decision-log ↔ dec-index sync is pristine.** 383 DECs, 5 supersessions marked identically in both files. Most mature doc pair in the repo.
2. **risk-register.md is actively maintained.** 80 entries with per-entry review dates, close-out tracking, and linkage to resolving DECs. Only 1 past-due review (already closed).
3. **sprint-history.md is fully current through Sprint 31.85** despite the rapid cadence (89 sprints/sub-sprints in ~53 active days). This is the structural backbone of all doc-sync efforts.
4. **The archived folder discipline is working.** All 8 files are correctly inert with no active DEC/DEF citing them as authoritative. Even the one still-referenced file (`10_PHASE3_SPRINT_PLAN.md`) is only cited by historical sprint artifacts, not by current docs or code.
5. **parquet-cache-layout.md (Sprint 31.85)** is a model for how new canonical operational docs should be written — tight, versioned, with explicit ownership handoff between tools and operators.
6. **market-session-debrief.md** stays tightly calibrated to engine changes — Sprint 32.9 additions (margin circuit, signal cutoff, shadow/counterfactual phases) are already reflected. Operational docs often drift; this one does not.
7. **ux-feature-backlog.md** is the canonical UI/UX inventory and gets referenced during sprint planning. It accepts additions (Sprint 32.8 deferred items are captured) without becoming a dumping ground. Good lifecycle model to replicate.
8. **Strategy-doc coverage is complete and accurate on mode/config.** Every strategy in code has a doc; every doc describes a strategy in code. The 13-live/2-shadow split matches `config/strategies/*.yaml` `mode` fields exactly.
9. **DEC-086 and DEC-082 research reports** remain informative even though their decisions shipped long ago. The non-obvious reasoning (PFOF reliability on Alpaca; "strategy research lab" reframe for Databento) is still load-bearing context whenever data/execution re-evaluation comes up.
10. **The two amendments** — while they have stale "not yet adopted" headers — preserve decision rationale in fuller form than the terser sprint-history entries. This is the right place for "why we committed to experiment infrastructure" or "why regime intelligence became vector-valued." Worth keeping after the status fix.
11. **The autonomous vs human-in-the-loop guides** present a live dual-mode architecture honestly. Neither has been prematurely archived despite autonomous mode being rarely used.

---

## Statistics

- **Files deep-read:** 28 (the 13 top-level + 15 subdirectory docs were read deeply)
- **Files skimmed:** 23 (15 strategy docs cross-read for template + regime + mode; 8 archived first-50-lines for content confirmation)
- **Total findings:** 27 actionable items
  - **CRITICAL:** 1 (paper-trading-guide.md — obsolete broker)
  - **MEDIUM:** 10 (process-evolution freeze decision, 2 amendment headers, 3 strategy regime sections, 5 broken cross-refs)
  - **LOW:** 12 (8 stub-doc PROVISIONAL captions, sprint-campaign header, 3-4 RSK re-scope, project-bible roster update, 2 research report banners, 2 backtesting archives, 43 sprint-file filename refs [grouped as 1 action])
  - **COSMETIC:** 4 (strategy-template optional sections, ibc-setup 3s delay note, archived index note for 10_PHASE3, fix never-existed file ref in decision-log)
- **Safety distribution:** **100% safe-during-trading** (27/27). Zero weekend-only, zero deferred-to-defs.
- **Estimated Phase 3 fix effort:** **~8–10 hours across 12 discrete doc-edit sessions.** All can batch into 2-3 longer sessions if operator prefers to handle them as weekday afternoon work alongside trading.

---

## Context State

**GREEN.** Five parallel audit agents completed cleanly; no compaction hit. All findings cross-verified against live filesystem before writing (paper-trading-guide Alpaca count, strategy doc bearish_trending grep, roadmap.md:6 supersession path, `.claude/skills/doc-sync.md` existence, archived folder file count). This report is safe to consume directly in Phase 2 without spot-checks, though spot-checking the 3 STALE-REWRITE strategy docs against live `argus/strategies/` code is recommended before Phase 3 Session D.
