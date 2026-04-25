<!-- 📦 ARCHIVED: This plan document was the working master during Sprint 31.9 campaign-close.
     It has been superseded by SPRINT-31.9-SUMMARY.md. Preserved here for historical reference.
     Do not update further. -->

# Sprint 31.9 Campaign-Close Plan

<!-- last-updated: 2026-04-23 (Phase 2 drafted — IMPROMPTU-CI inserted + IMPROMPTU-09/RETRO-FOLD/SPRINT-CLOSE kickoffs landed) -->
<!-- canonical-source: true — companion to CAMPAIGN-COMPLETENESS-TRACKER.md; this doc
     captures the session plan, the Loop-Closure Matrix, and reboot instructions.
     When the two conflict, this file governs. -->

## Purpose

This document is the single source of truth for the final phase of the Sprint
31.9 Health & Hardening campaign. It captures:

1. The full disposition of every open DEF, every non-DEF outstanding item, every
   debrief finding, and every campaign-close meta-item (retrospective fold,
   final summary, register seal, tracker archive) — **98 items total**.
2. The 8-session execution plan that closes these items.
3. Per-session summary cards (scope, safety tag, dependencies, Tier 2 profile).
4. The three post-Sprint-31.9 sprints that remain as named-horizon work.
5. Acceptance criteria for "campaign complete."
6. Context-reboot instructions for resuming from a fresh Claude.ai conversation.

This doc is written so that a fresh Claude.ai conversation with no memory of
the campaign can read this plus `RUNNING-REGISTER.md` + the latest close-out
report and know exactly where the campaign stands and what to do next.

---

## Definition: Campaign Complete / Clean Slate

The campaign is complete when every item below is in one of four states:

1. **RESOLVED** — strikethrough in CLAUDE.md with commit SHA.
2. **SCHEDULED** — assigned to a named remaining Sprint 31.9 session (IMPROMPTU-04
   through SPRINT-CLOSE as listed below).
3. **NAMED-HORIZON DEFERRED** — assigned to a specific named future sprint
   (post-31.9-component-ownership, post-31.9-reconnect-recovery-and-rejectionstage,
   post-31.9-alpaca-retirement, Sprint 30 / 31B / 33 / 33.5 / 34 / 34–35 / 36+).
4. **MONITOR-ONLY** — explicitly acknowledged with a concrete trigger condition
   (not "someday") and rationale for non-action.

No item stays in "opportunistic / no dedicated session" limbo. That bucket is
the graveyard this plan eliminates.

"Clean slate" in operational terms means every open item has a concrete
destination. It does NOT mean every DEF is resolved — items in Category 3
remain open but scheduled; items in Category 4 remain open but monitored.
Once the 3 post-31.9 sprints run, the build track resumes at Sprint 30 → 31B
→ 33 → 33.5 → 34–35 → 36+.

---

## Loop-Closure Matrix

Organized by disposition. Cross-ref CLAUDE.md Deferred Items table for full
DEF descriptions. Items bolded inline are the ones being materially changed
by this campaign (resolved or newly routed); items not bolded are legacy DEFs
with pre-existing trigger conditions that are simply being re-confirmed.

### Category 1 — SCHEDULED to Sprint 31.9 sessions (28 items across 8 sessions)

#### IMPROMPTU-04 — Safety Critical (blocks next paper session)

Serial only. Tier 2 adversarial review REQUIRED.

| Item | Source |
|---|---|
| **DEF-199** — `_flatten_unknown_position()` doubles shorts | CLAUDE.md; Apr 22 debrief §A1 |
| **Apr 22 debrief §C1** — `pattern_strategy.py:318` `logger.info` → `logger.debug` | Apr 22 debrief §C1 |
| **Apr 21 debrief F-01** — same log-level finding as §C1 (subsumed) | Apr 21 debrief F-01 |
| **New startup invariant** — assert broker positions `side == BUY` after connect | Debrief §A1 fix outline (recommended) |

#### IMPROMPTU-05 — Dependency & Infrastructure Bundle

Safe-during-trading; single solo session.

| Item | Source |
|---|---|
| **DEF-180** — Python lockfile via uv | CLAUDE.md |
| **DEF-181** — Node 20 GitHub Actions deprecation (hard deadline 2026-06-02) | CLAUDE.md |
| **DEF-179** — `python-jose` → `PyJWT` migration | CLAUDE.md |
| Non-DEF — `populate_historical_cache.py` LaCie `CANDIDATE_CACHE_DIRS` legacy entries | RUNNING-REGISTER Outstanding items |

#### IMPROMPTU-06 — Test-Debt & Warning-Cleanup Bundle

Safe-during-trading; test-only.

| Item | Source |
|---|---|
| **DEF-176** — `auto_cleanup_orphans` kwarg removal (3 test files) | CLAUDE.md |
| **DEF-185** — Analytics-layer `assert isinstance` anti-pattern (5 sites) | CLAUDE.md |
| **DEF-192 PARTIAL remainder** — 4 of 5 warning categories | CLAUDE.md |
| **DEF-166** — `test_speed_benchmark` flaky under pytest-cov | CLAUDE.md |
| **DEF-048** — `test_main.py` xdist failures (4 tests, `load_dotenv`/`AIConfig` race) | CLAUDE.md |
| **DEF-049** — `test_orchestrator_uses_strategies_from_registry` isolation | CLAUDE.md |
| Non-DEF — `TestOverflowConfigYamlAlignment` no-op | RUNNING-REGISTER Outstanding items |
| Non-DEF — `tests/test_main.py` stale mocks | RUNNING-REGISTER Outstanding items |

DEF-192 category (v) TestBaseline pytest-collection stays MONITOR — blocked on
workflow submodule per RULE-018; addressed in upstream metarepo commit, not argus.

#### IMPROMPTU-07 — Doc-Hygiene + Small Ops + UI Bug Fixes Bundle

Safe-during-trading. Scope grew from original estimate due to Apr 21 placeholder
residuals (F-05, F-06, F-08). If scope exceeds ~2 hours, split to 07a / 07b.

| Item | Source |
|---|---|
| **DEF-198** — Boot phase labels `/12` vs `/17` documentation mismatch | CLAUDE.md; debrief §B4 + §C6 |
| **DEF-189** — `revalidate_strategy.py:383` config_overrides param-name mismatch | CLAUDE.md |
| **DEF-164** — Late-night boot collides with after-hours auto-shutdown | CLAUDE.md |
| **DEF-191** — Latent SQL-side UTC normalization in `get_todays_pnl` (doc-only) | CLAUDE.md |
| **DEF-169** — `--dev` mode retired (reclassify as doc-only close) | CLAUDE.md |
| **Apr 21 debrief F-05** — `trade.id[:8]` ULID log-truncation width `[:8]`→`[:12]` | Apr 21 debrief F-05 |
| **Apr 21 debrief F-06** — MFE/MAE unit mismatch (backend stores $, frontend displays R) | Apr 21 debrief F-06 |
| **Apr 21 debrief F-08** — `PRIORITY_BY_WIN_RATE is not fully implemented` WARNING → DEBUG | Apr 21 debrief F-08 |
| Non-DEF — Cosmetic X1–X6 (main.py sprint/DEC/AMD archaeology comments) | RUNNING-REGISTER Outstanding items |
| Non-DEF — Shadow-variant badge rendering (`v2_*`/`v3_*` greyed out) | RUNNING-REGISTER Outstanding items |
| Doc reconciliation — CLAUDE.md "22 shadow variants" vs actual 15 | Debrief §B2 |

DEF-189 re-run of past contaminated revalidations is **named-horizon deferred
to Sprint 33 Statistical Validation** — not in IMPROMPTU-07 scope. The bug
fix lands here; the decision framework for acting on re-run results belongs
to Sprint 33+.

#### IMPROMPTU-08 — `architecture.md` API Catalog Regeneration

Solo session. May require a small FastAPI-introspection tooling pass.

| Item | Source |
|---|---|
| **DEF-168** — `architecture.md` API catalog drift (≥10 mismatches) | CLAUDE.md; audit P1-H1a |

Split from IMPROMPTU-07 because the regeneration may exceed the doc-hygiene
session's typical scope. Safe-during-trading.

#### IMPROMPTU-09 — April 22 Debrief Verification Sweep

Read-only session. Must run AFTER IMPROMPTU-04 lands (so A1-related verifications
capture post-fix state). Produces a new artifact:
`docs/sprints/sprint-31.9/debrief-2026-04-22-verification.md`.

| Item | Source |
|---|---|
| Verify FIX-01 `catalyst_quality` non-constant (SQL against `quality_history`) | Debrief §B3 + §Open Verification Gaps |
| Verify quality grade distribution shift post-Sprint-32.9 recalibration | Debrief §Open Verification Gaps |
| Verify daily cost ceiling enforcement (DEC-324) via `catalyst.db` | Debrief §Open Verification Gaps |
| Verify first-event sentinels (OHLCV unmapped/resolved, trade resolved) via grep | Debrief §Open Verification Gaps |
| Verify IntradayCandleStore initialization via grep | Debrief §Open Verification Gaps |
| Verify 11 `_init_*` lifespan phases (FIX-11) — also feeds DEF-198 disposition | Debrief §Open Verification Gaps |
| Verify concentration limit enforcement on BITO 8% | Debrief §C3 + §Open Verification Gaps |
| End-to-end trace of AAL short-flip (proof of DEF-196 mechanism) | Debrief §Open Verification Gaps |

**Risk**: if any verification fails, new DEF may open mid-flight. Plan
accommodates one additional micro-session before SPRINT-CLOSE if that happens.

#### RETRO-FOLD — P1–P25 into workflow/ metarepo

Docs-only, parallelizable with any other session.

| Item | Source |
|---|---|
| P1–P11 fold into `workflow/` metarepo protocols | CAMPAIGN-COMPLETENESS-TRACKER lines 161–171 |
| P12–P23 fold (additions post-P11) | Same, lines 172–183 |
| **P24** (sys.modules-level mock for optional deps) | Added by FIX-13c hotfix |
| **P25** (CI results must be verified green before next session) | Added by FIX-13c hotfix |

#### SPRINT-CLOSE — final serial session, runs last

| Item | Source |
|---|---|
| Write `SPRINT-31.9-SUMMARY.md` | Acceptance criterion |
| Mark `RUNNING-REGISTER.md` SEALED with final HEAD SHA + date | Acceptance criterion |
| Archive `CAMPAIGN-COMPLETENESS-TRACKER.md` → `docs/sprints/archive/sprint-31.9-campaign-tracker.md` | Acceptance criterion |
| Archive this file (`CAMPAIGN-CLOSE-PLAN.md`) → `docs/sprints/archive/` | New acceptance criterion |
| Archive Apr 21 impromptu-01/02 placeholder files (scope rehomed) | New — documented above |
| Final CLAUDE.md doc-sync — strike IMPROMPTU-04..09 resolved DEFs | DEC-275 discipline |
| Draft `docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md` | Handoff for named future sprint |
| Draft `docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md` | Handoff for named future sprint |
| Update `docs/sprints/post-31.9-component-ownership/DISCOVERY.md` — add DEF-182, DEF-193, ~~DEF-197~~ (resolved in IMPROMPTU-10), **DEF-202 (replaces C7)**, DEF-014 HealthMonitor | Existing scope expansion |
| Create `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md` — NEW sprint directory; seed with DEF-204 + IMPROMPTU-11 mechanism findings + IMSR forensic anchor + adversarial-review profile | NEW named horizon |

### Category 2 — NAMED-HORIZON DEFERRED (33 items)

Each is scheduled to a specific named future sprint. Not part of this campaign.

| Named Horizon | Items |
|---|---|
| **post-31.9-component-ownership** | DEF-175 (core), DEF-182 (weekly reconciliation stub), DEF-193 (Observatory WS disconnect detection), ~~DEF-197~~ (**pulled forward to IMPROMPTU-10** per Apr 23 trajectory), **DEF-202 (post-shutdown hang, subsumes Apr 22 §C7 + Apr 23 §C9)**, DEF-014 HealthMonitor subscription |
| **post-31.9-reconnect-recovery-and-rejectionstage** | DEF-177 (`RejectionStage.MARGIN_CIRCUIT`), DEF-184 (RejectionStage/TrackingReason split), DEF-194 (IBKR stale position cache), DEF-195 (`max_concurrent_positions` divergence + BITO 8% concentration), DEF-196 (32 DEC-372 stop-retry-exhaustion cascade), DEF-014 IBKR emitter TODOs (`ibkr_broker.py:453,531`), Apr 21 debrief F-04 (flatten-retry against non-existent positions) |
| **post-31.9-reconciliation-drift** (NEW — added post-Apr-24 debrief) | DEF-204 (A2/C12 upstream cascade mechanism — CRITICAL safety). Fix requires careful `argus/execution/order_manager.py` reconciliation / bracket-leg accounting changes with adversarial review. Not safe-during-trading. Mechanism identified in IMPROMPTU-11 (Sprint 31.9 Stage 9C). IMSR forensic anchor: `ARGUS=200 vs IBKR=100` flatten-qty mismatch. Cross-references DEF-158 (dup-SELL prevention — the detection mechanism working correctly), DEF-196 (stop-retry cascade — different family). Operator mitigation via daily `ibkr_close_all_positions.py` pending fix. |
| **post-31.9-alpaca-retirement** | DEF-178 (`alpaca-py` to `[incubator]` extras), DEF-183 (full Alpaca code+test retirement), DEF-014 Alpaca emitter TODO (`alpaca_data_service.py:593`) |
| **Sprint 30 Short Selling** | DEF-128 (IBKR err 404 multi-position qty divergence prevention) |
| **Sprint 31B Research Console** | DEF-147 (DuckDB Research Console backend) |
| **Sprint 33 Statistical Validation** | DEF-095 (submit-before-cancel bracket amendment) [+ Apr 21 F-03], DEF-098 (Dashboard trade count inconsistency), DEF-099 PARTIAL (ghost positions), DEF-105 (reconciliation inflate total_trades), DEF-122 (ABCD swing detection O(n³)), DEF-186 (BacktestEngine private-attr reach-in remainder), DEF-187 (walk-forward IS migration), DEF-189 rerun (contaminated revalidations re-run) |
| **Sprint 33.5 Adversarial Stress Testing** | DEF-095 (live trading hardening — natural fit with stress testing) |
| **Sprint 34 FRED Macro** | DEF-148 (FRED macro regime service), DEF-149 (FRED VIX backup) |
| **Sprint 34–35 Adaptive Capital Intelligence Phase 1** | DEF-017 (performance-weighted allocation V2), DEF-126 (regime-strategy interaction profiles), DEF-044 PARTIAL (regime-aware strategy behavior), DEF-023 PARTIAL (watchlist endpoint remaining fields) |
| **Sprint 36+ Continuous Discovery** | DEF-125 (time-of-day signal conditioning) |
| **Next major main.py/data-layer session** | DEF-064 (warm-up 78% failure rate mid-session boot) |

### Category 3 — MONITOR-ONLY (33 items; explicit trigger conditions)

Items stay open in CLAUDE.md. Trigger conditions are concrete and verifiable
at the appropriate future moment.

| Item | Trigger condition | Rationale for current non-action |
|---|---|---|
| DEF-006 Backtrader | Replay >1 hr for 6mo data | Replay Harness performance adequate |
| DEF-007 Pre-market scanner data | Scanner accuracy bottleneck | FMP Starter sufficient |
| DEF-011 IQFeedDataService | Specific feature needs forex/breadth | Cost $160–250/mo; no dependent feature |
| DEF-012 Databento L2 depth | Strategy requires order-book depth | MBP-10 available; no strategy requires |
| DEF-018 PARTIAL real-time VIX | Daily-VIX latency insufficient | Daily works for current strategies |
| DEF-019 Breadth indicators | Gated on DEF-011 | Dependent |
| DEF-020 Sector exposure check | IQFeed OR fundamentals | 5% single-stock cap provides cover |
| DEF-021 Sub-bar backtest for ORB Scalp | Tick data OR Scalp paper divergence | Neither fired |
| DEF-022 VwapBaseStrategy ABC | Second VWAP strategy designed | Only one today |
| DEF-025 Shared Consolidation base | Second consolidation strategy | Only one today |
| DEF-028 CalendarPnlView strategy filter | Performance Workbench OR explicit user request | Workaround exists |
| DEF-031 Orders table persistence | Post-hoc forensics needed | Not required for paper |
| DEF-032 FMPScannerSource criteria_list | Quality Engine demands it | Re-verified FIX-06; inline pointer added |
| DEF-033 Approve→Executed via WS | Next UI polish pass | Cosmetic; 1500ms setTimeout works |
| DEF-035 FMP Premium upgrade | Batch-quote speed bottleneck | Deferred until Learning Loop data (DEC-356) |
| DEF-038 Fuzzy catalyst dedup | High duplicate volume | Rule-based (DEC-311) handles common case |
| DEF-039 Runner conformance audit | `conformance_fallback_count` >2/sprint | Hasn't fired |
| DEF-040 Runner main.py decomposition | Exceeds ~2,500 lines | Currently 2,067 |
| DEF-047 Bulk catalyst endpoint | Catalyst API latency regression | Not observed |
| DEF-084 Full test suite runtime optimization | Continuous | FIX-13b closed largest offenders |
| DEF-094 ORB Scalp time-stop dominance | 5+ sessions data | Paper audit deferred (DEC-381) |
| DEF-100 IBKR paper repricing storm | Live impact | Paper-specific; Sprint 27.75 throttling mitigates |
| DEF-103 yfinance reliability | 5+ sessions monitor | Cache + fallback mitigate |
| DEF-108 R2G `atr_value=None` | R2G refactor opportunity | Percent fallback works |
| DEF-110 Exit reason misattribution | Observable impact | Cosmetic; position closes correctly |
| DEF-127 Virtual scrolling trades table | 1000-row limit insufficient | Currently 250-row display |
| DEF-135 Full visual verification Shadow Trades + Experiments | 20+ days paper data | Blocked on data |
| DEF-160 Shutdown race bracket-cancel + stop-retry | Observable impact | Cosmetic; may be subsumed by DEF-158 |
| DEF-174 Tauri desktop wrapper | Desktop packaging product requirement | Never asked for |
| DEF-192 category (v) TestBaseline pytest-collection | Workflow metarepo commit | Blocked on RULE-018 |
| Non-DEF — RSK-NEW-5 dangling references in 2 AI module comments | Opportunistic AI-layer touch | Cosmetic |
| Non-DEF — 5 remaining DEF-138 rejection-reason labels | Sprint 33+ observability | Scoped there |
| Non-DEF — M03/M05/M06 frontend primitive migration | Future page touches | Legitimately opportunistic (~35 + ~10 + ~15 sites, no active UI work) |

### Category 4 — RESOLVED-this-campaign (already landed before Phase 1a)

Listed in CAMPAIGN-COMPLETENESS-TRACKER.md §"Already resolved during campaign"
and in RUNNING-REGISTER.md §"DEF register — Resolved this campaign." Not
re-listed here to avoid drift.

### Matrix totals

- Category 1 (SCHEDULED to Sprint 31.9): **28 items** across 8 sessions
- Category 2 (NAMED-HORIZON DEFERRED): **33 items** across 11 named horizons
- Category 3 (MONITOR-ONLY): **33 items** with explicit trigger conditions
- Category 4 (RESOLVED, pre-Phase-1a): ≈ **50 items** (see tracker for detail)
- **Total reconciled: 144 items**

Discrepancy from the 98 count in Phase 1a planning (70 open DEFs + 4 PARTIAL
+ 9 non-DEF + 8 verification gaps + 6 campaign-close items + 1 doc-reconciliation)
reflects additional granularity in Category 1 (one plan-item often decomposes
into multiple tracker rows) and Category 3 (non-DEF Outstanding items now
inventoried individually). The Matrix above is authoritative.

---

## Session Plan

### Execution order

```
IMPROMPTU-04   safety (A1 + C1 + startup invariant)          [BLOCKS PAPER TRADING]
├─ then any order (file-disjoint, parallelizable):
│  IMPROMPTU-05   deps & infra (DEF-180/181/179)            ✅ LANDED
│  IMPROMPTU-06   test-debt (DEF-176/185/192/166/048/049)   ✅ LANDED
│  IMPROMPTU-07   doc-hygiene + UI fixes                    ✅ LANDED
│  IMPROMPTU-08   architecture.md catalog regen             ✅ LANDED
├─ inserted post-Apr-23 debrief (DEF-197 priority elevation MEDIUM→HIGH):
│  IMPROMPTU-10   evaluation.db retention diagnostic + fix (DEF-197)   ✅ LANDED
├─ parallelizable:
│  RETRO-FOLD     P1-P25 into workflow/ metarepo                        ✅ LANDED
├─ inserted post-Apr-24 debrief (DEF-204 CRITICAL — cascade mechanism):
│  IMPROMPTU-11   A2/C12 cascade mechanism diagnostic (read-only)        ✅ LANDED
├─ after IMPROMPTU-11 + Apr 24 paper session + three debriefs available:
│  IMPROMPTU-09   Apr 22 + Apr 23 + Apr 24 verification sweep (9 gaps, read-only; 4 pre-populated)
├─ inserted post-IMPROMPTU-11 (DEF-205 LOW — pytest date-decay):
│  TEST-HYGIENE-01   pytest date-decay fix (12 hardcoded date conversions)
└─ runs LAST, after all above:
   SPRINT-CLOSE   summary + seal + archive + 4 DISCOVERY.md (post-31.9-reconciliation-drift NEW)
```

### Parallelism rules

- **IMPROMPTU-04 is strict solo.** No concurrent writes to
  `argus/execution/*` or `argus/strategies/pattern_strategy.py`. Tier 2
  adversarial review is the quality gate. No same-day landing of 05/06/07/08
  on overlapping files.
- **IMPROMPTU-05/06/07/08 are file-disjoint** and can parallelize subject to
  the c3bc758 chimera lesson (pre-commit `git diff --name-only --cached`
  check against declared scope). Recommended: run serially to spread Tier 2
  review load.
- **IMPROMPTU-09 is read-only** — no merge risk with any concurrent session.
- **RETRO-FOLD touches only `workflow/` submodule + one tracker edit** —
  fully parallelizable with any argus-side session.
- **SPRINT-CLOSE must run last.** All argus commits complete before drafting
  the summary begins.

### Per-session summary cards

| Session | Safety tag | Scope files | Tier 2 profile | Depends on |
|---|---|---|---|---|
| IMPROMPTU-04 | safe-during-trading (code changes don't hot-reload; post-session restart controls cutover) | `argus/execution/order_manager.py`, `argus/strategies/pattern_strategy.py`, `argus/main.py`, tests | **Adversarial** | — |
| IMPROMPTU-CI | safe-during-trading (observatory WS is diagnostic read-only UI; teardown-race fix doesn't touch trading) | `argus/api/websocket/observatory_ws.py`, `tests/api/test_observatory_ws.py` | Standard | IMPROMPTU-04 pushed + CI observed red on `test_observatory_ws_sends_initial_state` |
| IMPROMPTU-05 | safe-during-trading | `pyproject.toml`, `.github/workflows/ci.yml`, `argus/api/auth.py`, `argus/api/websocket/*.py`, tests | Standard | IMPROMPTU-CI CI green |
| IMPROMPTU-06 | safe-during-trading | `tests/execution/order_manager/*`, `tests/analytics/`, `argus/analytics/ensemble_evaluation.py`, `argus/intelligence/learning/outcome_collector.py`, `argus/execution/order_manager.py` (kwarg removal only), test infra | Standard | — |
| IMPROMPTU-07 | safe-during-trading | `argus/main.py`, `scripts/revalidate_strategy.py`, `argus/analytics/trade_logger.py`, `argus/api/routes/counterfactual.py`, `argus/ui/src/features/trades/ShadowTradesTab.tsx`, `argus/ui/src/api/types.ts`, `argus/ui/src/utils/strategyConfig.ts`, `argus/ui/src/features/*/Badge.tsx`, `argus/core/risk_manager.py`, docs | Standard | — |
| IMPROMPTU-08 | safe-during-trading | `docs/architecture.md` + possibly new `scripts/regenerate_api_catalog.py` | Standard | — |
| IMPROMPTU-10 | safe-during-trading | `argus/strategies/telemetry_store.py`, possibly `argus/main.py`, `tests/strategies/test_telemetry_store.py`, docs | Standard | — (file-disjoint with all other campaign sessions) |
| IMPROMPTU-11 | safe-during-trading | read-only: `argus/execution/order_manager.py`, `logs/argus_20260424.jsonl`, the three debriefs; writes `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` + register/tracker | Standard | — (file-disjoint with IMPROMPTU-09 — can parallelize) |
| IMPROMPTU-09 | read-only | new `docs/sprints/sprint-31.9/debrief-2026-04-22-verification.md`; reads `data/argus.db`, `data/catalyst.db`, `logs/argus_20260423.jsonl` (next session log) | None (read-only) | IMPROMPTU-04 landed + one paper session |
| TEST-HYGIENE-01 | safe-during-trading | `tests/intelligence/test_filter_accuracy.py`, `tests/api/test_counterfactual_api.py`, docs | Standard | After IMPROMPTU-09 (file-disjoint with IMPROMPTU-09; no shared file overlap) |
| RETRO-FOLD | docs-only | `workflow/` submodule; `CAMPAIGN-COMPLETENESS-TRACKER.md` | None (docs) | — |
| SPRINT-CLOSE | docs-only | `docs/sprints/sprint-31.9/*`, `docs/sprints/archive/`, `docs/sprints/post-31.9-*/DISCOVERY.md`, `CLAUDE.md` final doc sync | Standard (final verification) | All above |

---

## Post-31.9 Sprint Horizons

After campaign close, the three post-31.9 sprints run in sequence. Each gets
its own DISCOVERY.md drafted during SPRINT-CLOSE.

1. **post-31.9-component-ownership** — 2–3 sessions. Discovery doc exists at
   `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`, needs update
   during SPRINT-CLOSE to incorporate DEF-182, DEF-193, (DEF-197 resolved in
   IMPROMPTU-10), DEF-014 HealthMonitor subscription, DEF-202 (replaces C7,
   subsumes Apr 23 §C9).
2. **post-31.9-reconnect-recovery-and-rejectionstage** — 2–3 sessions. Discovery
   drafted during SPRINT-CLOSE. Covers DEF-177, DEF-184, DEF-194, DEF-195,
   DEF-196, DEF-014 IBKR TODOs, Apr 21 F-04.
3. **post-31.9-alpaca-retirement** — 1–2 sessions. Discovery drafted during
   SPRINT-CLOSE. Covers DEF-178, DEF-183, DEF-014 Alpaca TODO.

---

## Acceptance Criteria

The campaign is complete when ALL of the following hold:

- [ ] IMPROMPTU-04 through SPRINT-CLOSE have landed with CLEAR or MINOR_DEVIATIONS
      (or CONCERNS_RESOLVED) verdict from Tier 2 review.
- [ ] Every DEF in Category 1 is strikethrough in CLAUDE.md with commit SHA.
- [ ] Every DEF in Category 2 is annotated in CLAUDE.md with its named-horizon
      sprint label.
- [ ] Every item in Category 3 has its trigger condition explicitly stated in
      CLAUDE.md.
- [ ] CI remains green throughout. Every session close-out cites a green CI
      run URL for the session's final commit (P25 rule).
- [ ] Every audit-2026-04-21 finding has a "FIX-NN Resolution" or
      "RESOLVED FIX-NN" annotation in its Phase 2 audit doc (p1-*.md) or
      Phase 3 prompt (FIX-NN-*.md). *Already confirmed at Phase 1a drafting;
      SPRINT-CLOSE re-verifies*.
- [ ] P1–P25 retrospective items folded into `workflow/` metarepo.
- [ ] `SPRINT-31.9-SUMMARY.md` written and committed.
- [ ] `RUNNING-REGISTER.md` carries a `SEALED` marker with final HEAD SHA + date.
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` moved to
      `docs/sprints/archive/sprint-31.9-campaign-tracker.md`.
- [ ] This file moved to `docs/sprints/archive/sprint-31.9-campaign-close-plan.md`.
- [ ] Three post-31.9 sprint DISCOVERY.md files exist and each is linked from
      the final summary doc.

---

## Context-Reboot Instructions

If this conversation hits a context limit and you need to resume campaign work
in a fresh Claude.ai conversation, paste the following at conversation start:

1. **This file** (`docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md`) — full context.
2. **`docs/sprints/sprint-31.9/RUNNING-REGISTER.md`** — current campaign state.
3. **Most recent IMPROMPTU-NN close-out + review artifacts** — what just landed.
4. **The kickoff for the NEXT session to run** — e.g.,
   `docs/sprints/sprint-31.9/IMPROMPTU-05-deps-infra.md`.

The project knowledge files (`bootstrap-index.md`, `ARGUS — Project Knowledge`,
`My Day Trading Manifesto`) remain in the Claude.ai project and do not need
to be pasted.

Starter prompt template for a reboot:

> I'm resuming Sprint 31.9 campaign-close work in a fresh conversation. The
> master plan is in `CAMPAIGN-CLOSE-PLAN.md` (pasted). Current campaign state
> is in `RUNNING-REGISTER.md` (pasted). The last session to land was
> [IMPROMPTU-NN]; its close-out + review are pasted. The next session to run
> is [IMPROMPTU-MM]; its kickoff is at `docs/sprints/sprint-31.9/IMPROMPTU-MM-*.md`.
>
> Next action: [draft IMPROMPTU-MM kickoff / verify IMPROMPTU-NN landed
> correctly / produce SPRINT-CLOSE summary / etc.].

---

## Document Maintenance

- **Update this file** at every session barrier. Move items from Category 1
  to "RESOLVED this campaign" in the tracker when they close.
- **Do NOT duplicate content** between this file and RUNNING-REGISTER.md
  or CAMPAIGN-COMPLETENESS-TRACKER.md. This file is the plan; those files are
  the operational state.
- **When this file and the tracker disagree**, this file governs.
- **At SPRINT-CLOSE**, this file moves to `docs/sprints/archive/` alongside
  the tracker and the Apr 21 impromptu-01/02 placeholder files.
