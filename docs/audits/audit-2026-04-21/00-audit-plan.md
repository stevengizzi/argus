# ARGUS Codebase & Documentation Audit — Plan

**Date:** 2026-04-21
**Trigger:** Pre-Sprint 31B systematic health check after 89 sprints/sub-sprints/impromptus over ~53 active dev days. First audit since project inception.
**Extends:** `workflow/protocols/codebase-health-audit.md` (v1.0.0). The base protocol is a single Claude.ai conversation covering 6 dimensions; this campaign adapts it to **18 read-only Claude Code sessions + 1 Claude.ai DEF triage**.

---

## Three-Phase Structure

### Phase 1 — Read-only audit (this document)
18 Claude Code sessions examine the codebase and produce structured findings reports at `docs/audits/audit-2026-04-21/p1-*.md`. No code, config, or doc modifications. Plus 1 Claude.ai DEF triage for the 65 open DEFs.

### Phase 2 — Human review gate (operator-driven)
Steven reads all 19 findings reports, classifies every finding as fix-now / defer / ignore, and populates the Phase 2 Review spreadsheet. Output feeds Phase 3.

### Phase 3 — Targeted fix sessions (generated after Phase 2)
Fix prompts generated mechanically from approved findings, grouped by file overlap, routed by safety tag (`safe-during-trading` vs `weekend-only`). Each session runs full pytest + Vitest before and after. Net test count must not decrease.

---

## Output Location

All findings committed to `docs/audits/audit-2026-04-21/` on **main branch** (read-only work, no risk of merge conflicts).

Each session's file is named `p1-<id>-<domain>.md` (e.g., `p1-a1-main-py.md`).

---

## Common Findings Report Format

Every session's findings file MUST follow this structure:

```markdown
# Audit: <Domain Name>
**Session:** P1-<ID>
**Date:** 2026-04-21
**Scope:** <1-line summary>
**Files examined:** <N deep / M skimmed>

## CRITICAL Findings
<Items that actively break things, cause silent data loss, violate core invariants, or expose execution/risk code to regression. Paper trading is live — anything touching live position management is critical.>

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|

## MEDIUM Findings
<Items that slow development velocity, accumulate debt, or risk regression but don't immediately break things.>

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|

## LOW Findings
<Items that should be fixed eventually but don't block anything.>

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|

## COSMETIC Findings
<Style, naming, minor doc issues. Fix opportunistically.>

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|

## Positive Observations
<Things working well that should be preserved and possibly replicated elsewhere. NEVER leave this section empty — after 90 sprints, at least some patterns are worth naming.>

## Statistics
- Files deep-read: N
- Files skimmed: N
- Total findings: N (X critical, Y medium, Z low, W cosmetic)
- Safety distribution: A safe-during-trading / B weekend-only / C read-only-no-fix-needed / D deferred-to-defs
- Estimated Phase 3 fix effort: X sessions
```

### Severity Definitions

| Severity | Criterion |
|----------|-----------|
| **CRITICAL** | Active bug, silent data loss, security risk, violated core invariant, or regression risk in execution/risk/data paths |
| **MEDIUM** | Slows development, accumulates debt, risks future regression, inconsistent with established patterns |
| **LOW** | Should be fixed but non-urgent |
| **COSMETIC** | Style, naming, typos, minor doc issues |

### Safety Tag Definitions

Every finding MUST carry one of these tags. The tag drives Phase 3 scheduling.

| Tag | Meaning | Phase 3 Routing |
|-----|---------|-----------------|
| `safe-during-trading` | Fix can land during market hours without risk. Docs, comments, config comments, dead code in non-runtime paths, test fixes, linting, rule updates. | Weekday sessions |
| `weekend-only` | Fix touches execution/, core/, data/, strategies/, intelligence/, main.py, or active API routes. Must run when paper trading is paused (ideally before market open Sunday evening). | Weekend sessions |
| `read-only-no-fix-needed` | Observation only. Nothing to change — e.g., an emergent pattern that should be documented in project-knowledge.md but doesn't need a code fix. | Doc-sync pass |
| `deferred-to-defs` | Finding is legitimate but should become a new DEF entry rather than be fixed in Phase 3. | CLAUDE.md DEF table update |

**Conservative default:** If safety is ambiguous, tag `weekend-only`. The cost of waiting until Sunday is a few days; the cost of breaking live paper trading is real data loss.

---

## Session List (18 Claude Code + 1 Claude.ai)

| ID | Domain | Deep-Read | Skim | Notes |
|----|--------|----------:|-----:|-------|
| **P1-A1** | `main.py` dedicated audit | 1 | 0 | 2,462 lines; THE wire-up file; deserves its own session |
| **P1-A2** | Core engine (rest) | 9 | 13 | orchestrator, risk_manager, regime, event_bus, market_calendar, etc. |
| **P1-B** | Strategies & patterns | 6 | 16 | 5 standalone strategies + 10 PatternModule + base classes + telemetry |
| **P1-C1** | Execution | 4 | 5 | order_manager (3K lines) gets dedicated attention |
| **P1-C2** | Data layer | 6 | 12 | Databento, FMP, UM, HistoricalQueryService, IntradayCandleStore |
| **P1-D1** | Catalyst + Quality + Counterfactual | 8 | 4 | classifier, briefing, quality_engine, position_sizer, counterfactual |
| **P1-D2** | Experiments + Learning Loop | 6 | 8 | pattern factory, runner, spawner, promotion, learning analyzers |
| **P1-E1** | Production backtest | 5 | 5 | engine.py, historical_data_feed, replay_harness |
| **P1-E2** | Legacy backtest dead-code scan | 8 | 0 | walk_forward + 6 VectorBT files + report_generator — import-graph analysis |
| **P1-F1** | Backend API | 4 | 34 | dev_state (2,338L) + 30 routes + 4 websockets |
| **P1-F2** | Frontend | sample | 404 | Pattern audit across 10-page Command Center |
| **P1-G1** | Test coverage gaps | tool | 321 | Run pytest-cov, analyze report |
| **P1-G2** | Test quality (sampling) | ~25 | 321 | Tautological, brittle, slow, excessive mocking |
| **P1-H1a** | Primary context compression | 3 | 0 | CLAUDE.md, project-knowledge.md, architecture.md |
| **P1-H1b** | Supporting docs audit | sample | 50 | Strategy docs, amendments, research, archived, guides |
| **P1-H2** | Config consistency (YAML ↔ Pydantic) | 2 | 44 | 44 YAMLs cross-referenced against 7 config modules |
| **P1-H3** | Claude rules, skills, agents | 16 | 0 | `.claude/rules/` (8) + `.claude/skills/` (5) + `.claude/agents/` (3) |
| **P1-I** | Dependencies & infra | 2 | few | `pyproject.toml`, `package.json`, `.env.example`, CI configs |
| **P1-H4** | DEF triage (Claude.ai) | — | — | 65 open DEFs → obsolete / superseded / promotable / correctly deferred |

### Why the split grew from your original 9 → 18

| Original | Revised split | Reason |
|----------|---------------|--------|
| P1-A (core, 30 files) | A1 (main.py alone) + A2 (rest of core) | main.py is 2,462 lines of wire-up — deserves undivided attention. Core also contains `config.py` at 1,751L which gets read in H2 with a different lens. |
| P1-C (execution+data, 20 files) | C1 (execution) + C2 (data) | order_manager.py is 3,036 lines. Reading it alongside databento_data_service.py (1,256L) and fmp_reference.py (1,181L) in one session guarantees compaction. |
| P1-D (intelligence, 25 files) | D1 (catalyst/quality/counterfactual) + D2 (experiments/learning) | Three independent subsystems; splitting makes cross-subsystem drift visible and avoids context overflow. 32 total intelligence/ files. |
| P1-E (backtest, 15 files) | E1 (production) + E2 (legacy dead-code scan) | E2 is import-graph analysis (grep-heavy), E1 is architectural review. Different work modes. 17,122 total backtest/ lines. |
| P1-F (API+frontend, 400+ files) | F1 (backend API) + F2 (frontend) | Two entirely different idioms; ~40 backend route/websocket files + `dev_state.py` (2,338L) alone justify F1. |
| P1-G (tests, 321 files) | G1 (coverage gaps) + G2 (test quality) | G1 runs tools; G2 samples and reads. Different work modes. |
| P1-H (docs+config+rules+DEFs, 110+ files + 65 DEFs) | H1a + H1b + H2 + H3 + H4 | Four distinct audit targets jammed together in original plan. Primary context files (CLAUDE.md, project-knowledge.md, architecture.md) are Steven's explicit top priority and warrant dedicated attention. |

---

## Pre-Identified Findings (from the survey clone)

These emerged from surveying the actual repo before writing the plan. They're logged here so the relevant session prompts can confirm and expand on them rather than rediscover.

| Pre-flag | Where to Confirm |
|----------|-------------------|
| **PF-01** `argus/accounting/` contains only `__init__.py` — dead scaffolding | P1-A2 |
| **PF-02** `argus/notifications/` contains only `__init__.py` — dead scaffolding | P1-A2 |
| **PF-03** `argus/core/config.py` is 1,751 lines — biggest undeclared audit target in core | P1-A2 (skim), P1-H2 (deep) |
| **PF-04** `argus/backtest/` is 17,122 lines across 20 files — bigger than handoff indicated | P1-E1, P1-E2 |
| **PF-05** `.claude/agents/` exists (3 files) — not mentioned in handoff | P1-H3 |
| **PF-06** `argus/data/service.py` — abstraction of unclear provenance; may be superseded | P1-C2 |
| **PF-07** Alpaca code (`alpaca_broker.py`, `alpaca_data_service.py`, `alpaca_scanner.py`) — DEC-086 demoted Alpaca to incubator only; verify any production call path | P1-C1, P1-C2 |
| **PF-08** `docs/archived/` has 7 files with explicit "superseded" intent — confirm they're truly inert | P1-H1b |
| **PF-09** DEF entries live in `CLAUDE.md` as a table with `~~strikethrough~~` for resolved, not `RESOLVED` keyword | P1-H4 methodology |
| **PF-10** `docs/architecture.md` is 2,819 lines — itself a likely compression target, not just a reference | P1-H1a |

---

## Cleanup Tracker Items (from Sprint 31.75)

These are already known and will be confirmed + expanded in the relevant sessions. Each session prompt references the items that fall within its scope.

| # | Item | File | Target Session |
|---|------|------|----------------|
| 1 | Unreachable `else` branch in fingerprint registration | `argus/backtest/engine.py:372` | P1-E1 |
| 2 | SQL f-string interpolation for numeric Pydantic fields | `scripts/resolve_sweep_symbols.py:211-216` | — (scripts/ is not in primary scope; flag in P1-E2 if surfaced) |
| 3 | `_count_cache_symbols()` hardcodes `'historical'` view name | `scripts/resolve_sweep_symbols.py:171` | — (same as above) |
| 4 | Pre-existing `test_history_store_migration` xdist failure | `tests/core/test_regime_vector_expansion.py` | P1-G2 |

**Note on scripts/ coverage:** `scripts/` is a 31-file directory (sweep tooling, consolidation, migrations, diagnostics). It's not assigned a dedicated session — most files are small operational scripts, and deep audit would be disproportionate. The two specific cleanup items above should be confirmed in Phase 2 triage directly from the tracker rather than via session. If Phase 2 reveals broader concern about scripts/ hygiene, add a sibling session P1-J.

---

## Parallelization Guidance

All 18 CC sessions are read-only with no shared state; any number can run concurrently. Practical limits: local CPU cores, Claude Code daily token budget, your ability to supervise.

**Suggested tmux groupings (4 windows × 4-5 sessions/day over 4-5 days):**

| Window | Day 1 | Day 2 | Day 3 | Day 4 |
|--------|-------|-------|-------|-------|
| W1 | P1-A1 | P1-A2 | P1-D1 | P1-H1a |
| W2 | P1-B | P1-C1 | P1-D2 | P1-H1b |
| W3 | P1-C2 | P1-E1 | P1-F1 | P1-H2 |
| W4 | P1-E2 | P1-F2 | P1-G1 | P1-H3 |

G2 and I go in any open slot on day 4-5.

**Sequencing constraints:**
- **P1-G1 before P1-G2:** Coverage report informs which files G2 should sample.
- **P1-H1a before P1-H1b:** Supporting docs audit needs the primary-context findings to avoid duplicate flagging.
- **P1-H4 (DEF triage) anytime** — runs in Claude.ai, not in tmux.

Everything else is fully independent.

---

## Constraints (All Sessions)

- **No modifications** to any code file, config file, doc file, YAML, JSON, or `.claude/` file. The ONLY writes allowed are:
  1. The findings report at `docs/audits/audit-2026-04-21/p1-<id>-<domain>.md`
  2. The git commit of that file
- **No test runs that write to live DBs.** Paper trading is live. If a session wants coverage data, it runs against a clean fixture DB or uses `--collect-only`.
- **No running of execution paths.** No IBKR connections, no Databento streams, no live API calls.
- **Sprint docs (`docs/sprints/`) are read-only artifact trail** — read but never modify.
- **`workflow/` submodule is out of scope** — separate repo, separate audit cadence.

---

## Commit Discipline

Each session commits exactly one file with a commit message of this form:

```
audit(P1-<ID>): <domain> findings report

Part of codebase audit 2026-04-21. Read-only session.
Findings: <X critical, Y medium, Z low, W cosmetic>.
```

Example:
```
audit(P1-A1): main.py findings report

Part of codebase audit 2026-04-21. Read-only session.
Findings: 3 critical, 11 medium, 7 low, 4 cosmetic.
```

---

## Handoff to Phase 2

When all 18 CC sessions + DEF triage are complete, `docs/audits/audit-2026-04-21/` contains 19 findings reports. The Phase 2 Review Template (separate file) is then populated — one row per finding, operator decision per row — and becomes the authoritative input to Phase 3 fix-session generation.

---

## Handoff to Phase 3

Phase 3 fix-session prompts are generated from the Phase 2 review output using the Phase 3 Fix Generation Rules (separate file). The rules enforce:
- Grouping findings by file overlap to minimize regression surface
- Routing by safety tag (safe-during-trading → weekday, weekend-only → weekend)
- Full test baseline run before and after each session
- Test count preservation (net change ≥ 0)

---

## Success Criteria for the Campaign

- 18 findings reports committed to `main`
- DEF triage completed; CLAUDE.md DEF table updated with re-classifications
- Phase 2 Review spreadsheet fully populated with operator decisions
- Phase 3 fix sessions generated, prioritized, and scheduled against safe/weekend slots
- Net test count preserved or increased after Phase 3 completes
- Sprint 31B proceeds on a materially cleaner foundation than the pre-audit state
