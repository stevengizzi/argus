# Audit: Claude Rules, Skills, Agents
**Session:** P1-H3
**Date:** 2026-04-21
**Scope:** `.claude/rules/` (8 files, ARGUS-local), `.claude/skills/` (5 files, symlinks to `workflow/`), `.claude/agents/` (3 files, symlinks to `workflow/`)
**Files examined:** 16 deep / 0 skimmed

## Pre-Read Note / Audit-Prompt Corrections
- All 5 files in [.claude/skills/](.claude/skills/) and all 3 in [.claude/agents/](.claude/agents/) are **symlinks into the `workflow/` submodule**, not ARGUS-local files. Per [workflow/claude/rules/universal.md](workflow/claude/rules/universal.md#L1-L7) and the audit plan ("`workflow/` submodule is out of scope"), these files cannot be modified from this repo — changes flow metarepo → projects, not the reverse. Findings for skills/agents are tagged `deferred-to-defs` or `read-only-no-fix-needed` and re-scoped as metarepo recommendations rather than in-repo fixes.
- A 9th rules symlink exists and was excluded from scope: `.claude/rules/universal.md` → [workflow/claude/rules/universal.md](workflow/claude/rules/universal.md). It is loaded into context alongside the 8 ARGUS-local rules and its RULE-001 … RULE-037 IDs are cross-referenced in this report.
- `[.claude/rules/code-style.md](.claude/rules/code-style.md)` is listed in the audit scope at 8 files. There are exactly 8 ARGUS-local `.md` files in `.claude/rules/` plus the `universal.md` symlink — count matches.

---

## 1. `sprint_14_rules.md` — Specific Verdict

**Verdict: DELETE or RENAME.** The filename brands the file as a Sprint-14 artifact (Sprint 14 shipped ~Feb 2026; active sprint is 31.85). Sprint-specific file names in `.claude/rules/` violate the intent of the directory (long-lived guidance, not per-sprint notes).

The *content* is not entirely Sprint-14-specific — several conventions (AppState DI, `HTTPBearer` + `Depends(require_auth)` auth pattern, `/api/v1/` prefix, `response_model=` paginated shape) did become load-bearing conventions carried through to Sprint 31.85. But the file is outdated as a reference:

- `[sprint_14_rules.md:7-8](.claude/rules/sprint_14_rules.md#L7-L8)` lists **11 AppState fields**. Actual [AppState dataclass in argus/api/dependencies.py:92-130](argus/api/dependencies.py#L92-L130) has **34 fields** (added across Sprints 22, 23.5, 23.6, 24, 24.5, 25, 25.6, 27.5–27.9, 28, 31A.5, 32, 32.5). Any AI assistant reading this file to understand AppState gets a ~Sprint-14 snapshot.
- `[sprint_14_rules.md:49-63](.claude/rules/sprint_14_rules.md#L49-L63)` lists 13 WebSocket event-type mappings. Actual mappings now include `arena_tick_price` (Sprint 32.8), observatory push events, counterfactual updates, etc. The mapping table is a stale partial.
- `[sprint_14_rules.md:36-47](.claude/rules/sprint_14_rules.md#L36-L47)` documents TradeLogger query methods that still exist — **this portion is current**.
- `[sprint_14_rules.md:82-84](.claude/rules/sprint_14_rules.md#L82-L84)` says `ApiConfig lives in argus/config/ (or wherever existing configs are).` — the vague "or wherever" itself signals the file was a scratch pad that was promoted without editing.

**Recommendation: RENAME → `api-conventions.md`, rewrite to reflect current AppState, keep the durable Sprint-14-originated patterns (auth, route file pattern, response conventions, TradeLogger interface), drop the stale partial enumerations.** The alternative (DELETE) is also defensible since the durable content overlaps with architecture.md's API section and the surviving conventions are now covered by the 29-route consistency audit in [p1-f1-backend-api.md](docs/audits/audit-2026-04-21/p1-f1-backend-api.md). RENAME is preferred because the file does encode conventions that newcomers benefit from having in one place.

---

## 2. Per-File Verdict Table

| # | File | Stale References | Contradictions vs. current | Verdict |
|---|------|---|---|---|
| 1 | [`.claude/rules/architecture.md`](.claude/rules/architecture.md) | L45 references `notifications/service.py` as a "critical abstraction" — the file does not exist; only [argus/notifications/__init__.py](argus/notifications/__init__.py) (1 line). L54 references `docs/ARCHITECTURE.md` (uppercase) — stylistically inconsistent with `docs/architecture.md` used elsewhere (works on macOS HFS+ case-insensitive, would fail on case-sensitive Linux CI). | No direct contradictions; absent sections on fire-and-forget, config-gating, separate-DB, trust-cache-on-startup. | **NEEDS-UPDATE** |
| 2 | [`.claude/rules/backtesting.md`](.claude/rules/backtesting.md) | References only VectorBT (`vectorbt_orb.py`, `vectorbt_vwap_reclaim.py` — both exist but are now secondary). No mention of [argus/backtest/engine.py](argus/backtest/engine.py) (BacktestEngine, Sprint 27+), [argus/backtest/vectorbt_pattern.py](argus/backtest/vectorbt_pattern.py) (PatternBacktester), DuckDB HistoricalQueryService, or the Sprint 31.75 shadow-first validation pivot (DEC-382). L39 "29-symbol, 35-month sweep should complete in under 30 seconds" is a pre-Databento benchmark. | `DEC-382` (shadow-first validation, 22 shadow variants deployed) is the current strategic posture — the rule file still reads as "exhaustive VectorBT grid sweep is the primary workflow," which is explicitly superseded. | **NEEDS-UPDATE** |
| 3 | [`.claude/rules/code-style.md`](.claude/rules/code-style.md) | None. Pylance/typing guidance is current. | None. Absent guidance on `json.dumps(default=str)` (DEF-151 lesson), `datetime.now(ZoneInfo("America/New_York"))` (DEC-276), ThrottledLogger (Sprint 27.75), `pathlib` enforcement (CLAUDE.md L272 rule), `from __future__ import annotations`, Python version pin. | **NEEDS-UPDATE** (additive) |
| 4 | [`.claude/rules/doc-updates.md`](.claude/rules/doc-updates.md) | L3 "six living documents" — the project maintains ≥10 living docs today (project-knowledge, roadmap, sprint-campaign, sprint-history, pre-live-transition-checklist, live-operations, process-evolution, risk-register, decision-log, architecture, project-bible, CLAUDE.md). L49 "Do not let CLAUDE.md grow beyond ~150 lines" — current [CLAUDE.md](CLAUDE.md) is ~275 lines. | Overlaps with `workflow/claude/skills/doc-sync.md` skill with no cross-reference. Missing: the `~~strikethrough~~` convention for resolved DEF entries (used in CLAUDE.md's DEF table but not codified anywhere), DEF/DEC/RSK duplicate-number check, Work Journal reconciliation. | **NEEDS-UPDATE** |
| 5 | [`.claude/rules/risk-rules.md`](.claude/rules/risk-rules.md) | None (durable content). | Missing: margin circuit breaker (DEC-367 / Sprint 32.9), broker-confirmed reconciliation safety (DEC-369), pre-EOD signal cutoff (3:30 PM ET, Sprint 32.9), non-bypassable-validation posture (Sprint 31.85 principle — see Missing Rules 4.4), `getattr(pos, "qty")` anti-pattern (DEF-139/140). L54 says `3:55 PM EST` — should be ET (EDT/EST depending on DST). | **NEEDS-UPDATE** (additive) |
| 6 | [`.claude/rules/sprint_14_rules.md`](.claude/rules/sprint_14_rules.md) | AppState enumeration: 11 listed, 34 actual. WS event map: partial snapshot. Sprint-number-in-filename is itself an anti-pattern. | Content is not contradicted by current code, just badly incomplete as an enumeration. | **DELETE or RENAME** (see §1) |
| 7 | [`.claude/rules/testing.md`](.claude/rules/testing.md) | L55 shows `python -m pytest tests/ -x --tb=short` as the full-suite command; L84 shows the correct current command `python -m pytest --ignore=tests/test_main.py -n auto -q` (per DEC-328). **Two conflicting commands in one file.** The L55 instruction fails to use `-n auto`/ignore test_main.py and will ship misleading guidance to any agent reading the top half. | Missing Vitest guidance: unmocked WS hangs, `testTimeout: 10_000` / `hookTimeout: 10_000` (DEF-138 / Sprint 32.8 lesson in project-knowledge.md L414). Missing: net-non-negative test count invariant (audit-plan §Handoff). | **NEEDS-UPDATE** |
| 8 | [`.claude/rules/trading-strategies.md`](.claude/rules/trading-strategies.md) | L17 says "Short selling deferred to Sprint 27 (DEC-166)"; `[decision-log.md:1828](docs/decision-log.md#L1828)` pegs DEC-166 at **Sprint 28** (date 2026-02-26). Short selling is still deferred (we're at 31.85, no short infra landed) — the rule is correct in spirit but the sprint number is wrong. | Missing: PatternModule conventions (`get_default_params()` returns `list[PatternParam]`, fingerprint = SHA-256 of detection params only), regime gating (DEC-360 — `bearish_trending` added to `allowed_regimes` of all 7 strategies to prevent dead sessions), shadow mode (StrategyMode enum, DEC-375 overflow routing), quality pipeline bypass semantics, 15-strategy current roster. | **NEEDS-UPDATE** |
| 9 | [`.claude/skills/canary-test.md`](.claude/skills/canary-test.md) → `workflow/...` | None. Generic procedure, no ARGUS-specific content. | None. | **CURRENT** |
| 10 | [`.claude/skills/close-out.md`](.claude/skills/close-out.md) → `workflow/...` | None. The `---BEGIN-CLOSE-OUT---` / `json:structured-closeout` format matches the Sprint 31.85 close-outs produced by the autonomous runner. | None. | **CURRENT** |
| 11 | [`.claude/skills/diagnostic.md`](.claude/skills/diagnostic.md) → `workflow/...` | None. Matches `universal.md` RULE-030 (two-fix retry limit). | None. | **CURRENT** |
| 12 | [`.claude/skills/doc-sync.md`](.claude/skills/doc-sync.md) → `workflow/...` | L63: "`.claude/rules/` Sync ... DEF/DEC/RSK numbering gaps." The corresponding ARGUS-side rule ([doc-updates.md](.claude/rules/doc-updates.md)) doesn't cross-reference this skill. | Minor role overlap with doc-updates.md rule (per-session discipline vs. post-sprint sync). Not a contradiction. | **CURRENT** (metarepo) |
| 13 | [`.claude/skills/review.md`](.claude/skills/review.md) → `workflow/...` | None. `---BEGIN-REVIEW---` / `json:structured-verdict` format matches the Tier 2 reports produced in Sprint 31.85. | None. | **CURRENT** |
| 14 | [`.claude/agents/builder.md`](.claude/agents/builder.md) → `workflow/...` | L1 status: "Future -- for use with Agent Teams orchestration." Builder agent has not been activated; all implementation sessions to date use the human-in-the-loop Sprint Runner or direct Claude Code sessions. | The agent has no frontmatter block (unlike `reviewer.md` which does), so it cannot be invoked as a subagent today. Consistent with "Future" status. | **CURRENT** (dormant) |
| 15 | [`.claude/agents/doc-sync-agent.md`](.claude/agents/doc-sync-agent.md) → `workflow/...` | Same "Future" status. No frontmatter. | Doc-sync is currently done manually following the [doc-sync skill](.claude/skills/doc-sync.md). Consistent. | **CURRENT** (dormant) |
| 16 | [`.claude/agents/reviewer.md`](.claude/agents/reviewer.md) → `workflow/...` | **Has frontmatter** (`name: reviewer`, `tools: [Read, Bash, Glob, Grep]`, `model: opus`) — active subagent. Procedure matches [review skill](.claude/skills/review.md). | None. The per-project-knowledge mandate ("Tier 2 `@reviewer` subagent" in Sprint 31.85 close-outs) matches this file. | **CURRENT** (active) |

---

## 3. Rules / Skills / Agents Role Separation

**Verdict: mostly clean, with one small overlap and one structural observation.**

- **Rules (long-lived coding/review guidance):** architecture.md, backtesting.md, code-style.md, doc-updates.md, risk-rules.md, testing.md, trading-strategies.md. All read as "what to do / not do" — correct category.
- **Skills (reusable procedures):** canary-test.md, close-out.md, diagnostic.md, doc-sync.md, review.md. All read as "how to run a specific workflow" — correct category.
- **Agents (subagent prompts):** builder.md, doc-sync-agent.md, reviewer.md. Each defines a constrained subagent identity. Correct category.

**Overlap — doc-updates rule vs. doc-sync skill.** `doc-updates.md` covers per-session doc hygiene (pre-commit doc audit). `doc-sync.md` covers post-sprint comprehensive doc sync. Different triggers, non-overlapping — but neither cross-references the other. An operator (or agent) reading either file in isolation would be uncertain which applies to their context. **Fix: add a "see also" header to both.**

**Observation — sprint_14_rules.md is a *rule* file that's really a *reference catalog*.** It's neither a rule (what to do) nor a procedure (how) — it's a crib sheet documenting the ambient conventions of the API layer. The closest fit is a rule with a better name (`api-conventions.md`). See §1.

**No agent prompt contradicts rules/ content.** [reviewer.md](.claude/agents/reviewer.md) explicitly defers to the review skill; builder/doc-sync-agent explicitly defer to their respective skills. No embedded duplication of rules.

---

## 4. Missing Rules — Pattern-by-Pattern Recommendations

The audit prompt identified 10 operationally critical patterns to check. Verdict per pattern:

| # | Pattern | Already in rules? | Recommendation |
|---|---------|---|---|
| 4.1 | **Fire-and-forget write pattern** (counterfactual_store, regime_history, experiment_store, eval event store all use it) | No | **ADD** to `architecture.md` → "Async Discipline" subsection. One paragraph: write-errors must surface (WARNING log rate-limited per DEC-345), never swallow silently. Cross-ref DEF-151 (silent dataclass serialization failure as the anti-pattern). |
| 4.2 | **DEC-345 separate-DB pattern** (argus.db / catalyst.db / evaluation.db / counterfactual.db / experiments.db / regime_history.db / learning.db / vix_landscape.db) | No | **ADD** to `architecture.md` → "Database Access" subsection. When contention risk exists, create a new SQLite DB file, not a new table in argus.db. Reference DEC-309 (catalyst precedent) and DEC-345 (evaluation precedent). |
| 4.3 | **Config-gating pattern** (enabled: false default; standalone YAML files MUST be wired into SystemConfig as Pydantic submodels) | Partial (architecture.md "Configuration is External") | **EXPAND** the existing section. Add: every new feature YAML (`config/*.yaml`) MUST have a matching Pydantic model in [argus/core/config.py](argus/core/config.py); default `enabled: false`; must be wired as a field on `SystemConfig`. Anti-pattern: YAML that's read directly from disk inside a feature module. |
| 4.4 | **Non-bypassable validation pattern** (Sprint 31.85 `test_no_bypass_flag_exists` grep-guard; no `--skip-validation` flag, no swallowed `except ValueError`, atomic rename unreachable on validation failure) | No | **ADD** as a new subsection in `risk-rules.md` AND cross-reference from `testing.md`. This is a *design-posture* rule, not just a code-style rule: validation is non-bypassable by construction, not by flag default. Reference DEF-151 (what the posture prevents) and the `test_no_bypass_flag_exists` pattern as the canonical invariant test. |
| 4.5 | **Fail-closed on missing reference data** (DEC-277 — `None` `prev_close`/`avg_volume` excluded at system filter level) | No | **ADD** to `trading-strategies.md` → "Data and Events" subsection. One sentence: semantic filters (`min_price`, `min_volume`) require data to evaluate; absence of data is not a pass condition. Applies at UniverseManager and any new filter layer. |
| 4.6 | **Trust-cache-on-startup pattern** (DEC-362 — non-blocking startup with background refresh) | No | **ADD** to `architecture.md` → "Async Discipline" subsection. One bullet: lifespan handlers must never call synchronous I/O that blocks indefinitely (project-knowledge L430). Load from cache at startup, schedule a background refresh. Reference `_wait_for_port()` and `trust_cache_on_startup: true` patterns. |
| 4.7 | **ThrottledLogger for high-volume log lines** (Sprint 27.75, argus/utils/throttled_logger.py) | No | **ADD** to `code-style.md` → "Logging" subsection. When a log line can fire >1×/sec in normal operation (flatten-pending retry, IBKR 399 repricing, portfolio snapshot miss), use ThrottledLogger with a per-key suppression window. Reference DEC-363 / DEF-113 / DEF-114. |
| 4.8 | **`json.dumps(..., default=str)` for dataclass serialization** (DEF-151) | No | **ADD** to `code-style.md` → new "Serialization" subsection. Always pass `default=str` when serializing any dataclass that *might* contain `datetime` / `date` / `Decimal`. Round-trip-test new write paths. Reference DEF-151 (143 Night-1 sweep grid points silently lost). |
| 4.9 | **`getattr(pos, "qty")` anti-pattern** (DEF-139/140 — Position uses `shares`; Order uses `qty`) | No | **ADD** to `architecture.md` (or new `domain-model.md` rule). Position and Order are distinct types with different fields: Position has `shares`, Order has `qty`. Never use `getattr(x, 'qty', 0)` on a value whose type you haven't verified. If Position model changes in the future, this rule should be updated or removed. |
| 4.10 | **ET timestamps everywhere except user-facing display** (DEC-276 — canonical import `from zoneinfo import ZoneInfo`, `ZoneInfo("America/New_York")`) | No | **ADD** to `code-style.md` → new "Time and Timezones" subsection. ET is canonical for market-session reasoning; UTC is canonical for inter-system comms (HTTP timestamps, DB audit fields). Reference DEC-061 (market-hours-always-ET) and DEC-276 (AI layer ET). Flag the existing single-file drift in [argus/api/routes/counterfactual.py:94](argus/api/routes/counterfactual.py#L94) (see p1-f1 MEDIUM #6). |

**Bonus — Question 13 (Compaction risk scoring, DEC-275):** not documented in `.claude/` anywhere. Project-knowledge.md L379 references it; no rule file codifies the 7-factor scoring table (files created ×2, files modified ×1, context reads ×1, new tests ×0.5, integration wiring +3, external API debug +3, large files ×2) or the thresholds (0–8 Low / 9–13 Medium / 14–17 High must-split / 18+ Critical). **RECOMMEND:** since compaction scoring lives in the sprint-planning protocol (workflow submodule) rather than per-session coding guidance, the right home is `workflow/protocols/sprint-planning.md`, not `.claude/rules/`. Leave `.claude/rules/` alone and flag for metarepo (see §11 agents findings).

---

## 5. `code-style.md` — Deep Findings

- **Python version pin** — not stated. The project uses Python 3.11+ per `pyproject.toml` and project-knowledge.md L170. **Add a one-liner:** "Target Python: 3.11+." This matters when type-hint syntax choices differ (e.g., `X | None`, `list[int]` vs. `List[int]`).
- **`pathlib` vs `os.path`** — CLAUDE.md L272 says "Use pathlib for file paths, not os.path" as a project rule. Not echoed in `code-style.md`. **Add.**
- **`asyncio` idioms** — `asyncio.sleep` (not `time.sleep`), `asyncio.to_thread` for blocking I/O, `call_soon_threadsafe()` for cross-thread event bus bridge (DEC-088) are all project-critical but only architecture.md covers them at a high level. Consider consolidating the asyncio rules into one subsection of `code-style.md`.
- **Type-hint posture** — L8 says "Every function must have complete type hints. No exceptions." This is *stricter* than the audit prompt's question 5.3 ("required, encouraged, optional?"). **Current answer is REQUIRED.** Good — but check for contradiction with Universal RULE-001 (execute-what-prompt-specifies) if a prompt ever requests a lighter touch. No action needed; the rule is clear.
- **Logger pattern** — L84 "Logger per module: `logger = logging.getLogger(__name__)`" — matches the codebase uniformly. ✅
- **Enums vs string literals** — ExitReason example (L66-75) is slightly stale: the current `ExitReason` enum in [argus/core/events.py](argus/core/events.py) has ~12 members including `RECONCILIATION` (DEC-371) and `TRAILING_STOP`. The listed 7 are a subset. **Minor — either expand or clearly mark as illustrative.**

---

## 6. `doc-updates.md` — Deep Findings

- **"Six living documents" (L3)** — stale. Current count ≥10. Rewrite opening paragraph.
- **"Do not let CLAUDE.md grow beyond ~150 lines" (L49)** — CLAUDE.md is currently ~275 lines; rule self-violates. Either update the threshold (300 lines?) or flag CLAUDE.md for compression (see P1-H1a).
- **DEF `~~strikethrough~~` convention** — CLAUDE.md's DEF table marks resolved items with `~~DEF-NNN~~ | ~~...~~`. This is unique and load-bearing; a doc-sync agent needs to know not to delete resolved rows. **ADD to doc-updates.md.**
- **DEF/DEC/RSK duplicate-number guard** — [workflow doc-sync skill L46-54](.claude/skills/doc-sync.md#L46-L54) enforces this at sprint boundaries. `doc-updates.md` doesn't mention it as a per-session concern. Cross-ref the skill.
- **Sprint close-out doc requirements** — not covered. The per-session doc audit (L8-14) ends at "flag what needs updating" but doesn't explain when the operator commits those updates or who owns them. Either add, or explicitly defer to the doc-sync skill.

---

## 7. `risk-rules.md` — Deep Findings

- **Numbering 0, 1, 2, 3** — the audit prompt asks if the numbering is preserved. The file does not use that convention; it uses prose sections ("Order Flow — The Mandatory Path", "Circuit Breakers are Non-Overridable", "Position Sizing Invariants", "Stop Loss Rules", "End of Day", "Logging Requirements"). No numbered gates to preserve. This appears to be a convention from a different document (possibly the Risk Manager implementation itself — see [argus/core/risk_manager.py](argus/core/risk_manager.py) "check 0, 1, 2, 3" naming). **If the numbering was ever intended as the public gate contract, add a new section mapping check names to rule intent.** Otherwise the prompt question is inapplicable.
- **Fail-closed semantics** — L20 ("If code exists that places a broker order without passing through the Risk Manager, it is a critical bug") and L40 ("If ANY of these are false, the order MUST be rejected") both enforce fail-closed. ✅
- **Clock injection (DEF-001 / DEC-087)** — not documented. BaseStrategy and RiskManager both accept an injected `Clock`; tests use `FixedClock`. This is a safety-critical pattern (deterministic time in backtests and tests) and deserves a bullet. **ADD.**
- **Missing operational safety items (see §2):** margin circuit breaker (DEC-367), broker-confirmed reconciliation (DEC-369), pre-EOD signal cutoff (Sprint 32.9), non-bypassable validation posture (4.4 above).
- **`3:55 PM EST` (L54)** — should be `3:55 PM ET`. EST is the winter offset; during DST the market closes at 3:55 PM EDT. ARGUS uses `ZoneInfo("America/New_York")` which handles both; the rule text should too.

---

## 8. `testing.md` — Deep Findings

- **Command inconsistency (L55 vs L84)** — **this is the most actionable finding in the file.** Top-of-file says `python -m pytest tests/ -x --tb=short`; bottom-of-file says `python -m pytest --ignore=tests/test_main.py -n auto -q`. The L55 form predates DEC-328 (Sprint 23.8 test tiering) and predates DEF-048 (test_main.py ignore). A newcomer reading the file top-to-bottom gets contradictory guidance. **Fix: delete L51-L61 ("Always run the full test suite ...") OR replace with a pointer to the standard commands block at L81-L91.**
- **xdist tiering (DEC-328)** — L82-88 covers it correctly: full at sprint-entry + closeouts + final review, scoped elsewhere. ✅
- **Vitest guidance** — missing. Project-knowledge.md L414 has the entire rationale: unmocked `useArenaWebSocket` or similar hooks that create real WS in jsdom hang fork workers; `vi.mock()` at test file top; `testTimeout: 10_000` / `hookTimeout: 10_000` in `vitest.config.ts` as a safety net. **ADD a "Vitest (frontend tests)" section.** Reference DEF-138 (resolved) as the incident.
- **Test baseline preservation** — audit-plan constraint "Net test count must not decrease" is the Phase 3 invariant. Not in the rules file. **ADD** — "Every code-modifying session must end with pytest count ≥ previous count." Exceptions (e.g., deleting a pre-existing failing test) require flagging in the close-out.
- **Piped `tail` with xdist warning (L65-79)** — codified from Sprint 31.75 (and Universal RULE-037 covers the related process-accumulation concern). ✅
- **Sequential (`pgrep` / `pkill` / investigate) recovery procedure (L93-102)** — very good content, matches Universal RULE-037. ✅

---

## 9. `trading-strategies.md` — Deep Findings

- **9.1 — PatternModule conventions.** Missing. Rules that should be codified (all from Sprint 29 DEC-378 and Sprints 32–32.8):
  - `get_default_params()` returns `list[PatternParam]` (frozen dataclass with 8 fields).
  - Detection-param fingerprint is SHA-256 first 16 hex of canonical JSON (sorted keys, compact separators) of *detection params only* — non-detection fields (strategy_id, name, enabled, operating_window) are excluded (project-knowledge.md L417).
  - `min_detection_bars` property on PatternModule defaults to `lookback_bars` but can be overridden — `lookback_bars` is deque *capacity*, `min_detection_bars` is detection *eligibility window* (project-knowledge.md L422).
  - PatternParam `min_value`/`max_value` range must not be narrower than the Pydantic field `ge`/`le` bound (Sprint 32 cross-validation tests found 7 such discrepancies — project-knowledge.md L416).
- **9.2 — Regime gating.** Missing. DEC-360 added `bearish_trending` to `allowed_regimes` on all 7 legacy strategies to prevent dead sessions. Any new strategy must declare its `allowed_regimes` list.
- **9.3 — Zero-R signal guard.** Partially covered: L40 cross-references DEC-249 (0.25R floor). Missing: the *upstream* zero-R guard (signals with `entry == stop` must be rejected at strategy level — DEC-251 / DEF-152 Sprint 31.75 S1 lesson).
- **9.4 — Telemetry wire-up (BaseStrategy StrategyEvaluationBuffer + EvaluationEventStore, Sprints 24.5–25.6).** Not in the rule — should be. Every new BaseStrategy implementation must emit ENTRY_EVALUATION events via the ring buffer for Observatory + decision-stream UI. Since Sprint 31A onward this has been a mandatory convention.
- **9.5 — Current 15-strategy roster.** Not in the rule. CLAUDE.md already lists it ("13 live + 2 shadow"). Duplicating it in the rule would invite drift. **Don't add it; cross-reference CLAUDE.md's `## Current State` section instead.**
- **Sprint number error (L17)** — "Short selling deferred to Sprint 27" — DEC-166 says Sprint 28. Fix the reference.

---

## 10. Skills — Procedural Accuracy

All 5 skill files (symlinks to `workflow/`) were read end-to-end against the current codebase and Sprint 31.85 operational practice.

| File | Are steps executable today? | Commands / paths that would break | Verdict |
|------|---|---|---|
| [canary-test.md](.claude/skills/canary-test.md) | Yes. Step 1 "Run the existing test suite" has no command prescribed — it defers to the operator / runner. Steps 2–6 are pure procedure. | None. | CURRENT |
| [close-out.md](.claude/skills/close-out.md) | Yes. The structured output format (`---BEGIN-CLOSE-OUT---` + `json:structured-closeout`) is exactly what the Sprint Runner parses today. | None. | CURRENT |
| [diagnostic.md](.claude/skills/diagnostic.md) | Yes. Matches Universal RULE-030 / RULE-031 / RULE-033 for diagnostic-first. | None. | CURRENT |
| [doc-sync.md](.claude/skills/doc-sync.md) | Yes. The Work Journal reconciliation (L22-29) is active and matches Sprint 31.85's impromptu doc-sync. L58 "Tier A Compression Check" and L65 ".claude/rules/ Sync" both still current. | None. | CURRENT |
| [review.md](.claude/skills/review.md) | Yes. The `---BEGIN-REVIEW---` + `json:structured-verdict` format matches recent Tier 2 outputs. Step 1.3 "`git diff HEAD~1`" is a reasonable default; sprint reviews often use explicit ranges. | None. | CURRENT |

**No skill is procedurally broken.** One observation: all 5 skills are ~generic workflow templates. They don't reference `argus/` paths, `config/` layout, or any ARGUS-specific tooling. This is intentional (they're shared metarepo assets) but the one-hop mental cost of "does this apply to ARGUS specifically?" is real. **No action — this is the correct tradeoff for the metarepo model.**

---

## 11. Agents — Prompt Integrity

| File | Consistent with its matching skill? | Active / Dormant | Notes |
|------|---|---|---|
| [builder.md](.claude/agents/builder.md) | Yes (defers to close-out skill + canary-test skill). No frontmatter — cannot be invoked as subagent in current Claude Code. | Dormant ("Future") | L16 "You MUST NOT modify `.claude/rules/` or `.claude/agents/`" — matches universal RULE-018 ("The source of truth for planning-layer docs is Claude.ai ... Claude Code owns code and code-adjacent docs"). ✅ |
| [doc-sync-agent.md](.claude/agents/doc-sync-agent.md) | Yes (defers to doc-sync skill). No frontmatter. | Dormant ("Future") | Correctly declares autonomy boundaries for DEC/RSK/DEF creation and flags Tier A compression for human approval. ✅ |
| [reviewer.md](.claude/agents/reviewer.md) | Yes (defers to review skill). Has frontmatter — **active subagent**. | Active | L20-28 describes the invocation contract. Matches the project-knowledge mandate that Tier 2 review is a fresh-context subagent. ✅ |

**No agent prompt contradicts the rules in `.claude/rules/`.** `builder.md` L16 reaffirms universal RULE-018's metarepo guard; `doc-sync-agent.md` L15 reaffirms the same boundary for code; `reviewer.md` L37-44 explicitly blocks state-mutating git commands. Consistent.

**One observation for the metarepo:** the asymmetry between `reviewer.md` (has frontmatter) and `builder.md` / `doc-sync-agent.md` (no frontmatter) is structural. The reviewer agent is the only one that can be invoked today via `Agent(subagent_type='reviewer')` or the `@reviewer` mention. If builder and doc-sync-agent are ever activated, they'll need frontmatter too. **Flag for metarepo** — not in scope for this audit.

---

## 12. Cross-Reference Integrity (Broken References)

Scanned each rule / skill / agent for file-path references and verified them.

| Source | Reference | Actual State | Severity |
|--------|-----------|---|---|
| [architecture.md:43](.claude/rules/architecture.md#L43) | `data/service.py` | Exists (3,052B, 96L). ✅ | OK |
| [architecture.md:45](.claude/rules/architecture.md#L45) | `notifications/service.py` (as a "critical abstraction") | **Does not exist** — only `__init__.py` (62 bytes, 1 line). NotificationService is a bill-of-materials stub that has never been implemented. | **MEDIUM — broken** |
| [architecture.md:41](.claude/rules/architecture.md#L41) | `execution/broker.py` | Exists (4,647B). ✅ | OK |
| [architecture.md:54](.claude/rules/architecture.md#L54) | `docs/ARCHITECTURE.md` (uppercase) | Actual file is `docs/architecture.md` (lowercase). Works on macOS (HFS+ case-insensitive). **Will fail on case-sensitive Linux CI** or any `git mv` rename attempt. | **LOW — stylistic / portability** |
| [backtesting.md:5](.claude/rules/backtesting.md#L5) | `vectorbt_orb.py`, `vectorbt_vwap_reclaim.py` | Both exist in [argus/backtest/](argus/backtest/). ✅ | OK |
| [sprint_14_rules.md:6](.claude/rules/sprint_14_rules.md#L6) | `argus/api/dependencies.py` | Exists. AppState fields listed are stale (11 → 34). | MEDIUM (enumeration rot — see §2 row 6) |
| [sprint_14_rules.md:18](.claude/rules/sprint_14_rules.md#L18) | `tests/api/conftest.py` | Exists ✅. Fixture names (api_config, jwt_secret, app_state, client, auth_headers) match actual test fixtures (spot-checked). | OK |
| [doc-updates.md:19](.claude/rules/doc-updates.md#L19) | Example "DEC-025 ... Event Bus" | DEC-025 is an actual entry (Event Bus FIFO, DEC-025). ✅ | OK |
| [doc-updates.md:33](.claude/rules/doc-updates.md#L33) | `docs/risk-register.md` | Exists. ✅ | OK |
| [trading-strategies.md:17](.claude/rules/trading-strategies.md#L17) | `DEC-166 ... Sprint 27` | DEC-166 actually says Sprint 28. **Semantic mismatch**, not a broken reference (the DEC exists). | **LOW — factual error** |
| [testing.md:7-9](.claude/rules/testing.md#L7-L9) | `tests/core/`, `tests/strategies/`, `tests/execution/` paths | All three directories exist. ✅ | OK |
| `.claude/skills/*` | All 5 files are symlinks into `workflow/claude/skills/` | All symlinks resolve. ✅ | OK |
| `.claude/agents/*` | All 3 files are symlinks into `workflow/claude/agents/` | All symlinks resolve. ✅ | OK |
| [close-out.md:102](.claude/skills/close-out.md#L102) | `.claude/skills/close-out.md` (self-reference via builder/reviewer) | Resolves via symlink. ✅ | OK |

**Tally: 1 broken path (architecture.md L45 → notifications/service.py), 1 portability issue (architecture.md L54 uppercase), 1 semantic error (trading-strategies.md L17 Sprint 27→28). All other references intact.**

---

## 13. Compaction Risk Scoring Integration (DEC-275)

DEC-275 (quantitative 7-factor compaction risk scoring) is documented in:
- [docs/decision-log.md:3093-3104](docs/decision-log.md#L3093-L3104) — rationale.
- [docs/project-knowledge.md:379](docs/project-knowledge.md#L379) — summary reference.
- `workflow/protocols/sprint-planning.md` — operational use.

It is **not referenced in `.claude/rules/`** anywhere.

**Should it be?** The scoring is applied during *sprint planning* (deciding whether to split a session), not during *implementation* (what a Claude Code session executes). The natural home is the workflow submodule's sprint-planning protocol, which already has it. Adding it to `.claude/rules/` would duplicate the metarepo content.

**Recommendation: NO ACTION in `.claude/rules/`.** The current placement (workflow submodule + decision log + project-knowledge) is correct. Add a single line to [universal.md](.claude/rules/universal.md) RULE-025 cross-referencing DEC-275 if the metarepo ever refreshes that file. **Flag for metarepo** — not in scope for this audit.

---

## 14. Aggregate Action Table

Severity values map to audit protocol: CRITICAL (breaks things), MEDIUM (drift/debt), LOW (eventually), COSMETIC. Safety tag: all `.claude/` changes are `safe-during-trading` (doc-only, no runtime), except items deferred to the workflow metarepo which are `read-only-no-fix-needed` from this repo's perspective.

| # | Action | File | Severity | Rationale | Safety |
|---|--------|------|---------|-----------|--------|
| 1 | **UPDATE** | [architecture.md:45](.claude/rules/architecture.md#L45) | MEDIUM | ~~Remove or mark aspirational the `notifications/service.py` abstraction. File does not exist beyond `__init__.py` stub. Either build the abstraction or remove the claim.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 2 | **UPDATE** | [architecture.md:54](.claude/rules/architecture.md#L54) | LOW | ~~`docs/ARCHITECTURE.md` → `docs/architecture.md` (lowercase). Portability to case-sensitive filesystems.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 3 | **ADD section** | [architecture.md](.claude/rules/architecture.md) | MEDIUM | ~~New subsections for: fire-and-forget writes (4.1), separate-DB pattern (4.2), config-gating expansion (4.3), trust-cache-on-startup (4.6), domain-model `shares` vs `qty` (4.9).~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 4 | **UPDATE** | [backtesting.md](.claude/rules/backtesting.md) | MEDIUM | ~~Add BacktestEngine section (Sprint 27+), PatternBacktester, shadow-first validation (DEC-382), DuckDB consolidated cache context. Qualify or remove the "29-symbol, 35-month < 30s" benchmark.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 5 | **ADD section** | [code-style.md](.claude/rules/code-style.md) | MEDIUM | ~~New subsections for: Serialization (`default=str`, 4.8), Time/Timezones (ET vs UTC, 4.10), ThrottledLogger (4.7). Add Python 3.11 target + pathlib enforcement. Mark the ExitReason example as illustrative or refresh to current enum.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 6 | **UPDATE** | [doc-updates.md:3](.claude/rules/doc-updates.md#L3) | MEDIUM | ~~"Six living documents" → current count / pointer to reference table.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 7 | **UPDATE** | [doc-updates.md:49](.claude/rules/doc-updates.md#L49) | LOW | ~~CLAUDE.md size threshold (~150 lines) is self-violated. Raise to 300 or flag CLAUDE.md for compression (defer decision to P1-H1a).~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 8 | **ADD** | [doc-updates.md](.claude/rules/doc-updates.md) | MEDIUM | ~~Document the `~~strikethrough~~` DEF-resolution convention in CLAUDE.md. Cross-reference doc-sync skill. Add DEF/DEC/RSK duplicate-number guard.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 9 | **ADD section** | [risk-rules.md](.claude/rules/risk-rules.md) | MEDIUM | ~~Margin circuit breaker (DEC-367), broker-confirmed reconciliation (DEC-369), pre-EOD signal cutoff (3:30 PM ET), non-bypassable validation posture (4.4), `shares` vs `qty` anti-pattern (4.9), clock-injection pattern. Fix `EST` → `ET` at L54.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 10 | **DELETE or RENAME** | [sprint_14_rules.md](.claude/rules/sprint_14_rules.md) | MEDIUM | ~~Sprint-numbered filename. If RENAME → `api-conventions.md` and rewrite AppState/WS-event-map to current state; if DELETE → verify its durable content is captured in architecture.md / p1-f1-backend-api audit / code. Operator choice.~~ **RESOLVED FIX-17-claude-rules** (renamed to api-conventions.md) | safe-during-trading |
| 11 | **UPDATE** | [testing.md:51-61](.claude/rules/testing.md#L51-L61) | MEDIUM | ~~Delete or rewrite the obsolete "`python -m pytest tests/ -x --tb=short`" block. Contradicts the correct DEC-328 commands at L82-88 in the same file.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 12 | **ADD section** | [testing.md](.claude/rules/testing.md) | MEDIUM | ~~Vitest section (unmocked WS hangs, `testTimeout: 10_000`, `vi.mock()`), net-non-negative test count invariant (audit-plan handoff), non-bypassable validation cross-ref to risk-rules (4.4).~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 13 | **UPDATE** | [trading-strategies.md:17](.claude/rules/trading-strategies.md#L17) | LOW | ~~"Sprint 27" → "Sprint 28" (DEC-166 actual).~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 14 | **ADD sections** | [trading-strategies.md](.claude/rules/trading-strategies.md) | MEDIUM | ~~PatternModule conventions (9.1), regime gating (9.2), zero-R upstream guard (9.3), BaseStrategy telemetry wire-up (9.4), fail-closed on missing reference data (4.5). Cross-reference CLAUDE.md for current 15-strategy roster (9.5) — don't duplicate.~~ **RESOLVED FIX-17-claude-rules** | safe-during-trading |
| 15 | **METAREPO** | [workflow/claude/agents/builder.md](.claude/agents/builder.md) & [doc-sync-agent.md](.claude/agents/doc-sync-agent.md) | LOW | Add frontmatter blocks when/if these agents are activated (currently marked "Future"). Symmetry with [reviewer.md](.claude/agents/reviewer.md). | read-only-no-fix-needed |
| 16 | **METAREPO** | [workflow/claude/skills/doc-sync.md](.claude/skills/doc-sync.md) | LOW | Add `## See also` pointing to per-project doc-update rules (e.g., `.claude/rules/doc-updates.md` equivalents). Bidirectional visibility. | read-only-no-fix-needed |

**Phase 3 effort estimate: 2 focused sessions.**
- Session 1 (rules refresh): items 1–4, 5, 8, 9, 11, 12, 13, 14. Mechanical rewriting. ~60–90 min.
- Session 2 (sprint_14 decision): item 10. Requires operator decision (DELETE vs RENAME) before execution. ~30 min if RENAME, ~15 min if DELETE.
- Items 6, 7: batch with Session 1.
- Items 15, 16: metarepo — flagged, not in scope.

---

## Positive Observations

- **Universal.md is excellent.** The [workflow/claude/rules/universal.md](workflow/claude/rules/universal.md) rule set (37 RULEs across 8 categories) is concise, empirically-derived, and cross-project. It gives the ARGUS-local rules a clean layer to build on. RULE-037 ("Before relaunching any long-running background command, verify the original process is no longer running") is exemplary — it's specific, cites an actual Sprint 31.9 incident, and prescribes the exact remedy (`pgrep -fl` / `pkill -f ... && sleep 2`). [testing.md](.claude/rules/testing.md) L93-L102 mirrors it project-specifically.
- **Reviewer subagent is well-scoped.** [reviewer.md](.claude/agents/reviewer.md) is the only agent with frontmatter; it's read-only by construction (tools restricted to `Read, Bash, Glob, Grep`); it's explicitly a fresh-context invocation; and it blocks state-mutating commands (L37-44). This is the single most load-bearing `.claude/` file for review integrity, and it's tight.
- **Role separation between rules/skills/agents is clean.** Over 16 files, only one small overlap (doc-updates rule ↔ doc-sync skill) and one mis-categorized file (sprint_14_rules.md is a reference catalog in rule's clothing). No agent prompt contradicts any rule. No skill embeds rules. No rule hides a procedure. That's a healthy set.
- **Skill format is production-proven.** The `---BEGIN-CLOSE-OUT---` / `json:structured-closeout` format in [close-out.md](.claude/skills/close-out.md) and the `---BEGIN-REVIEW---` / `json:structured-verdict` format in [review.md](.claude/skills/review.md) are exactly what the Sprint Runner parses in production. No drift between the skill spec and runner ingestion contract.
- **Testing.md bottom half is excellent.** L63-L110 (xdist pipe-to-tail hazard, standard commands, hanging-test recovery procedure, wall-clock-bound async tests) are all encoded from real Sprint 31.75/31.85 incidents. The quality of this content makes the L51-L61 contradiction with the obsolete `-x --tb=short` command stand out even more — it's obvious the top half was never rewritten when the bottom half was added.
- **Code-style Pylance section is rigorous.** [code-style.md](.claude/rules/code-style.md) L88-L109 gives precise guidance on parameterized generics, typed row objects, narrow-before-use, `# type: ignore` hygiene, and matching config return types. This is much tighter than most codebases achieve.
- **Architecture rules are load-bearing.** [architecture.md](.claude/rules/architecture.md)'s "Strategies are isolated modules" (L7-L18), "Event Bus is the Backbone" (L20-L24), and "Abstraction Layers" (L37-L47) are the durable contract that 89 sprints have preserved. Even the broken `notifications/service.py` reference is trivial to fix; the structural correctness of the rules is the win.
- **Content provenance from real incidents.** Most rule content is traceable to a specific DEC or DEF (DEC-028, DEC-027, DEC-088, DEC-117, DEC-122, DEC-132, DEC-149, DEC-152, DEC-247, DEC-248, DEC-249, DEC-328). This is the correct posture — rules should be distilled lessons, not abstract ideals.

---

## Statistics
- Files deep-read: **16** (8 rules + 5 skills + 3 agents, all examined end-to-end)
- Files skimmed: **0**
- Total findings: **16** (0 critical, 10 medium, 5 low, 1 cosmetic)
- Safety distribution: **14 safe-during-trading / 0 weekend-only / 2 read-only-no-fix-needed / 0 deferred-to-defs**
- Estimated Phase 3 fix effort: **2 sessions** (1 rules-refresh + 1 sprint_14 decision)

---

## Appendix — Links

- Base protocol: [workflow/protocols/codebase-health-audit.md](workflow/protocols/codebase-health-audit.md)
- Audit plan: [docs/audits/audit-2026-04-21/00-audit-plan.md](docs/audits/audit-2026-04-21/00-audit-plan.md)
- Sibling findings: [p1-a1](docs/audits/audit-2026-04-21/p1-a1-main-py.md), [p1-a2](docs/audits/audit-2026-04-21/p1-a2-core-rest.md), [p1-b](docs/audits/audit-2026-04-21/p1-b-strategies-patterns.md), [p1-c1](docs/audits/audit-2026-04-21/p1-c1-execution.md), [p1-c2](docs/audits/audit-2026-04-21/p1-c2-data-layer.md), [p1-d1](docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md), [p1-d2](docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md), [p1-e1](docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md), [p1-e2](docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md), [p1-f1](docs/audits/audit-2026-04-21/p1-f1-backend-api.md), [p1-f2](docs/audits/audit-2026-04-21/p1-f2-frontend.md), [p1-i](docs/audits/audit-2026-04-21/p1-i-dependencies.md)
- Upstream cross-refs: DEC-028, DEC-088, DEC-117, DEC-122, DEC-132, DEC-149, DEC-166, DEC-181, DEC-248, DEC-249, DEC-275, DEC-276, DEC-277, DEC-309, DEC-328, DEC-345, DEC-349, DEC-360, DEC-362, DEC-363, DEC-367, DEC-369, DEC-371, DEC-375, DEC-382, DEF-048, DEF-091, DEF-113, DEF-114, DEF-138, DEF-139, DEF-140, DEF-151.
