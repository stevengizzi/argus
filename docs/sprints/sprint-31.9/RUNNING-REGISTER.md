# Sprint 31.9 Running Register

> Canonical snapshot of campaign state: session verdicts, DEF/DEC register,
> outstanding items, deferred pickups, and next-stage plan. Rebuild this file
> at every stage barrier. Survives compaction — read this file to hydrate
> a fresh Claude.ai conversation.
>
> **Last updated:** 2026-04-22 — Stage 5 complete
> **Campaign HEAD:** `7b70390` (FIX-07 single commit; post-barrier becomes current HEAD)
> **Workflow submodule:** `942c53a`
> **Baseline tests:** 5,029 pytest + 859 Vitest (local) / 5,028+ pytest + 859 Vitest (CI, -m "not integration"), 0 failures

---

## Campaign overview

- **Identifier:** `sprint-31.9-health-and-hardening`
- **Artifacts directory:** `docs/sprints/sprint-31.9/`
- **Key docs:** `README.md`, `STAGE-FLOW.md`, `WORK-JOURNAL-HANDOFF.md`, this register
- **Session count:** 24 planned across 9 stages (Track A: 22 FIX-NN sessions; Track B: 2 IMPROMPTU sessions)
- **Operator:** Steven Gizzi (two-Claude workflow: Claude.ai planning + Claude Code implementation, git bridge)
- **Account under test:** IBKR paper U24619949 (paper paused during weekend-only sessions)

---

## Stage status

| Stage | Sessions | Status |
|---|---|---|
| Stage 1 | FIX-00 + FIX-15 + FIX-17 + FIX-20 + FIX-01 + FIX-11 + Stage 1 sweep | ✅ COMPLETE |
| Stage 2 Pass 1 | FIX-02 (config drift via DEC-384 extension) | ✅ CLEAR |
| Stage 2 Pass 2 | FIX-03 (main.py lifecycle — biggest session of campaign to date) | ✅ CONCERNS → RESOLVED in-session |
| **Stage 2 Pass 3** | **FIX-12 + FIX-19 + FIX-21 (parallel)** | ✅ **ALL CLEAR** |
| IMPROMPTU (between 2 and 3) | DEF-172 verify + DEF-173 fix + DEF-175 open | ✅ CLEAR |
| Stage 3 Wave 1 | FIX-14 + FIX-16 | ✅ CLEAR (prior sessions) |
| Stage 3 Wave 2 | FIX-04 (Rule-4 serial, order_manager.py) | ✅ CLEAR |
| Stage 4 Wave 1 | FIX-10 + FIX-18 (parallel) | ✅ CLEAR |
| Stage 4 Wave 2 | FIX-05 solo | ✅ CLEAR |
| **Stage 4** | **(complete)** | **✅ COMPLETE** |
| Stage 5 Wave 1 | FIX-06 (data layer) | ✅ CLEAR |
| Stage 5 Wave 2 | FIX-07 (intelligence/catalyst/quality) | ✅ CLEAR |
| **Stage 5** | **(complete)** | **✅ COMPLETE** |
| Stage 6 | FIX-08 solo | ⏸ PENDING |
| Stage 7 | FIX-09 solo | ⏸ PENDING |
| Stage 8 | FIX-13 + IMPROMPTU-01 (LIVE OK parallel) | ⏸ PENDING |
| Stage 9A | IMPROMPTU-02 scoping (read-only) | ⏸ PENDING |
| Stage 9B | IMPROMPTU-02 fix (weekend-only) | ⏸ PENDING |

---

## Session history (Stage 1 + Stage 2)

| Session | Commit(s) | Self-assessment | Tier 2 verdict | Test delta | Notes |
|---|---|---|---|---|---|
| FIX-00 (doc-sync obsoletes) | `bac4c06` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-15 (supporting docs) | `9dd44f2` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-17 (.claude/rules refresh) | `451b444` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-20 (sprint runner) | `9737e52` + submodule `942c53a` | MINOR_DEVIATIONS | CLEAR | +0 | Stage 1; disk-full recovery (ENOSPC) |
| FIX-01 (catalyst DB + DEC-384) | `59bb100` | MINOR_DEVIATIONS | CLEAR | +11 | Stage 1; crisis recovery — initial FLAGGED turned out to be stash misread |
| FIX-11 (backend API) | `fc7eb7c` | MINOR_DEVIATIONS | CONCERNS (accepted) | net -2 | Stage 1; lifespan extraction + dev mode retirement |
| Stage 1 sweep | `f3b0464` | CLEAN | CLEAR | 0 | Doc cleanup + DEF logging |
| FIX-02 (overflow.yaml via DEC-384) | `9454df5` + `b23459b` | CLEAN | CLEAR | +3 | Stage 2 Pass 1; first registry extension |
| FIX-03 (main.py lifecycle) | `80af45b` + strikethrough follow-up + `3ad46fa` | MINOR_DEVIATIONS | CONCERNS → RESOLVED | -1 (intentional deletions) | Stage 2 Pass 2; 31 findings, main.py shrunk 2,469 → 2,291 lines |
| FIX-21 (ops cron) | `8ccac67` + `3a6c71d` | CLEAN | CLEAR | 0 (docs-only) | Stage 2 Pass 3 |
| FIX-19 (strategies) | `a2c2512` + `e60cb47` | MINOR_DEVIATIONS | CLEAR | +18 | Stage 2 Pass 3 |
| FIX-12 (frontend) | `db2818b` + `f57a965` | MINOR_DEVIATIONS | CLEAR | Vitest +13 | Stage 2 Pass 3 |
| IMPROMPTU-def172-173-175 | `873738a` | MINOR_DEVIATIONS | CLEAR | +1 | Between Stage 2 and Stage 3; DEF-172 verify-close, DEF-173 code fix, DEF-175 opened + DISCOVERY.md seeded |
| FIX-14 (primary Claude context docs) | `8c36bef` + `f57d7fc` | CLEAN | CLEAR | 0 | Stage 3 Wave 1 |
| FIX-16 (config consistency sweep) | `563ae13` + `942cf05` | MINOR_DEVIATIONS | CLEAR | +19 | Stage 3 Wave 1 |
| FIX-04 (execution layer) | `b2c55e5` + `4cfd8b4` | MINOR_DEVIATIONS | CLEAR | +1 | Stage 3 Wave 2 (Rule-4 serial). 2 CRITICAL + 7 MEDIUM + 10 LOW. Both CRITICALs landed with gold-standard revert-and-fail proof by Tier 2. F11 P1-D1-M03 deferred (DEF-177 — cross-domain RejectionStage edit outside scope); F10 partial (DEF-176 — test-migration blocker). |
| FIX-10 (backtest legacy cleanup) | `675bf78` + `3efac5a` | CLEAN | CLEAR | 0 (docs-only) | Stage 4 Wave 1 (parallel with FIX-18). 3 findings, trivial. |
| FIX-18 (deps + infra hardening) | `7aabb96` + `5fe4d1d` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 4 Wave 1 (parallel with FIX-10). 15 findings (2 CVE + 9M + 4L + 2 cosmetic). CI workflow (`.github/workflows/ci.yml`) introduced. Cleanup tracker #2 + #3 RESOLVED. |
| HOTFIX pytest-xdist | `d261e7b` + `a896985` | — | — | 0 | Post-FIX-18: CI surfaced missing `pytest-xdist` in `[dev]` extras. Declared + annotated FIX-18 follow-up. |
| HOTFIX clean-install | `793d4fd` | — | — | 0 | First full CI run unmasked 4 clean-install bugs (submodule init, seaborn for report generator, jwt→jose shim in one test, walk-forward integration marking). All fixed. |
| FIX-05 (core: orchestrator + risk + regime) | `4590859` + `2fec7ca` + `f0283d3` | CLEAN | CLEAR | +10 | Stage 4 Wave 2. 37 findings (2 CRITICAL + 18 MEDIUM + 17 LOW). Both CRITICALs landed with regression tests exercising uncovered lines. Closed DEF-091/092/104/163/170. Opened DEF-182 (weekly reconciliation). |
| FIX-06 (data layer) | `4ea09a7` + `49fef3b` | MINOR_DEVIATIONS | CLEAR | +17 | Stage 5 Wave 1. 26 findings (1 CRITICAL + 8 MEDIUM + rest LOW/COSMETIC). F25 CRITICAL resolved via FIX-16-compatible overlay path (spec option (b) moot post-FIX-16); three-layer revert-proof regression defense. SystemAlertEvent added to core/events.py as documented scope expansion. DEF-037/165 closed; DEF-014 PARTIAL (emitter side landed; HealthMonitor subscription awaits P1-A1 M9); DEF-032 re-verified; DEF-183 opened (Alpaca retirement). |
| FIX-07 (intelligence/catalyst/quality) | `7b70390` | MINOR_DEVIATIONS | CLEAR | +12 | Stage 5 Wave 2 (serial). 23 findings (7 MEDIUM + rest LOW, no CRITICAL). Finding 5 (RejectionStage split) deferred to DEF-184, coordinated with DEF-177. Two scope expansions ratified: `argus/core/protocols.py` (new file, FIX-06 precedent) + `argus/intelligence/learning/models.py` (actual DEF-106 location; spec cited wrong file). DEC-311 received Amendment 1 (kept[-1] dedup anchor pinned via option (c) — preserves in-flight paper-trading counts). DEF-096 + DEF-106 closed; DEF-184 opened. |

Baseline progression: 4,934 (pre-campaign) → 4,858 (actual pytest at campaign start after FIX-03's CLAUDE.md strikethrough) → 4,944 (post-FIX-11) → 4,946 (post-FIX-02) → 4,964 (post-Stage-2) → 4,965 (post-IMPROMPTU-def172-173-175) → 4,984 (post-FIX-16) → 4,985 (post-FIX-04, holds through Stage 4 Wave 1 + hotfixes) → 5,000 (post-FIX-05) → 5,017 (post-FIX-06) → **5,029 (post-FIX-07)**. Vitest: 846 → **859**.

---

## DEF register (sprint-campaign-scoped items)

### Resolved this campaign

| DEF # | Description | Session | Commit |
|---|---|---|---|
| DEF-034 | `SessionResult.review_verdict` Pydantic warning | FIX-20 | `9737e52` |
| DEF-048 + 049 | `test_main.py` env leak (autouse fixture applied; remaining isolation failure is pre-existing, out of DEF-046 pattern scope) | FIX-03 | `80af45b` |
| DEF-074 | Dual regime recheck path consolidation | FIX-03 | `80af45b` |
| DEF-082 | `CatalystStorage` pointed at `argus.db` instead of `catalyst.db` | FIX-01 | `59bb100` |
| DEF-093 | `main.py` duplicate orchestrator YAML load + `_latest_regime_vector` typing | FIX-03 | `80af45b` |
| DEF-097 | Monthly cache update cron (`populate_historical_cache.py --update`) | FIX-21 | `8ccac67` |
| DEF-142 | `quality_engine.yaml` / `system*.yaml` drift | FIX-01 (via DEC-384) | `59bb100` |
| DEF-162 | Monthly re-consolidation cron (`consolidate_parquet_cache.py --resume`) — paired with DEF-097 | FIX-21 | `8ccac67` |
| DEF-172 | Duplicate `CatalystStorage` instances — RESOLVED-VERIFIED (behavioral): dual close paths both fire; SQLite WAL enables safe concurrent reads; structural dedup deferred to DEF-175 | IMPROMPTU-def172-173-175 | `873738a` |
| DEF-173 | `LearningStore.enforce_retention()` never called — RESOLVED: wired in `argus/api/server.py::_init_learning_loop` mirroring FIX-03's ExperimentStore pattern; +1 regression test | IMPROMPTU-def172-173-175 | `873738a` |
| DEF-091 | Public accessors for V1 RegimeClassifier + VIXDataService private attrs — `compute_trend_score()` + `vol_low_threshold`/`vol_high_threshold` properties on V1; `config` property on VIXDataService | FIX-05 | `4590859` |
| DEF-092 | Unused Protocol types in `argus/core/regime.py` — four orphaned Protocol classes deleted | FIX-05 | `4590859` |
| DEF-104 | Dual ExitReason enums drift risk — `argus.core.events.ExitReason` now re-exports from `argus.models.trading` (single source of truth) | FIX-05 | `4590859` |
| DEF-163 | Timezone-boundary + hardcoded-date Python tests — ET alignment in `test_get_todays_pnl_excludes_unrecoverable`, ET capture in `test_history_store_migration`, relative `computed_at` in `_make_vector()`. Vitest side remains under DEF-167 (FIX-13). | FIX-05 | `4590859` |
| DEF-170 | VIX regime calculators inert in production — `RegimeClassifierV2.attach_vix_service()` re-instantiates all four VIX calculators from the injected service | FIX-05 | `4590859` |
| DEF-032 | `criteria_list` parameter ignored on FMP scanner — RESOLVED-VERIFIED: DEF-032 still accurate; inline pointer comment added at call site | FIX-06 | `4ea09a7` |
| DEF-037 | FMP API key redaction in error logs — `_redact()` helper threaded through 4 FMP network-error log sites | FIX-06 | `4ea09a7` |
| DEF-165 | DuckDB conn close hang when CREATE VIEW interrupted — `self._conn.interrupt()` before `.close()` | FIX-06 | `4ea09a7` |
| DEF-096 | Protocol type for duck-typed candle store + store references — `argus/core/protocols.py` with `CandleStoreProtocol` + `CounterfactualStoreProtocol` | FIX-07 | `7b70390` |
| DEF-106 | `models.py from_dict()` assert isinstance batch — 8 sites in `intelligence/learning/models.py` + 1 in `routes/counterfactual.py` converted to `if not isinstance: raise TypeError` | FIX-07 | `7b70390` |

### Partially resolved

| DEF # | Description | Status | Owner |
|---|---|---|---|
| DEF-167 | Vitest hardcoded-date decay | PARTIAL (FIX-11 addressed some; broader sweep pending) | FIX-13 (Stage 8) |
| DEF-014 | SystemAlertEvent for dead data feed — PARTIAL: emitter side wired at `databento_data_service._run_with_reconnection()` with max-retries-exceeded emission; HealthMonitor subscription + Command Center alert-pane surface await P1-A1 M9 expansion. 3 additional TODO emitter sites at `ibkr_broker.py:453,531` and `alpaca_data_service.py:593` remain (execution/data layer, cross-domain). | PARTIAL (FIX-06 emitter side) | P1-A1 M9 (subscription) + execution-layer session (remaining emitters) |

### Open with planned owner

| DEF # | Description | Priority | Owner |
|---|---|---|---|
| DEF-168 | `docs/architecture.md` API catalog drift | LOW | P1-H1a (not yet scheduled as FIX-NN) |
| DEF-169 | `--dev` mode retired (informational only) | INFO | Ongoing (no owner needed) |
| DEF-171 | `test_all_ulids_mapped_bidirectionally` xdist flake | LOW | **FIX-13 (Stage 8)** |
| DEF-174 | Tauri desktop wrapper never integrated; `platform.ts` deleted as misleading dead code | LOW / opportunistic | Deferred (only if desktop packaging becomes a requirement) |
| DEF-175 | Component ownership consolidation — `CatalystStorage`, `SetupQualityEngine`, `DynamicPositionSizer`, `ExperimentStore`, `LearningStore` constructed in both `main.py` and `api/server.py` lifespan phases; broader pattern behind DEF-172/173 | MEDIUM | **Dedicated post-Sprint-31.9 sprint** (~2–3 sessions). Pre-sprint discovery at `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`. Blocked on Sprint 31.9 closure. |
| DEF-176 | Full removal of deprecated `OrderManager(auto_cleanup_orphans=...)` kwarg — FIX-04 added DeprecationWarning; 3 reconciliation test files still pass the kwarg and were outside FIX-04 scope | LOW | Opportunistic / next execution-layer cleanup sprint |
| DEF-177 | `RejectionStage.MARGIN_CIRCUIT` — FIX-04 P1-D1-M03 deferred; requires cross-domain edit (intelligence/counterfactual.py enum + counterfactual_positions schema + order_manager.py:485 emitted stage) that exceeded FIX-04's execution-only scope | MEDIUM | **Dedicated cross-domain session, must coordinate with DEF-184** (both want to modify the same RejectionStage enum in orthogonal directions) |
| DEF-178 | `alpaca-py` still in core `[project.dependencies]` despite DEC-086 demoting Alpaca to incubator-only — FIX-18 left constraint in place with inline pointer; full fix moves to `[project.optional-dependencies].incubator` + feature-detect at 4 call sites | LOW | Opportunistic / execution-layer cleanup sprint |
| DEF-179 | `python-jose` → `PyJWT` migration — FIX-18 bumped bound to `>=3.4.0,<4` to mitigate CVE-2024-33663 (fixed in 3.4.0); full migration is single-session weekend work across 5 import sites + 2 test fixtures | LOW — CVE already mitigated | Opportunistic / next API-layer cleanup sprint |
| DEF-180 | No Python lockfile — CI workflow from FIX-18 P1-I-M06 installs from version ranges; lockfile (`uv.lock` recommended) would give CI + operator identical resolved trees | LOW-MEDIUM | Dedicated single-session sprint (~30-60 min) |
| DEF-181 | Node 20 deprecation in GitHub Actions — `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4` all run on Node.js 20 which will be forced to Node.js 24 on 2026-06-02 and removed 2026-09-16. First CI runs on 2026-04-22 surfaced the warning. | LOW | Before 2026-06-02 — bump action pins in `.github/workflows/ci.yml` |
| DEF-182 | Weekly reconciliation full implementation — `HealthMonitor._run_weekly_reconciliation()` has been a placeholder since Sprint 5; FIX-05 upgraded log level and pointed at this DEF. Full fix needs broker `get_order_history(days=7)` pairing with `TradeLogger.get_trades_by_date_range(...)` + discrepancy alerts. | LOW | Opportunistic / operations sprint |
| DEF-183 | Full Alpaca code+test retirement — delete `alpaca_data_service.py`, `alpaca_scanner.py`, associated tests, and config branches; simplify `main.py:301-317` / `:339-346` to a single live path. Pairs with DEF-178 (dependency-removal half). | LOW | Opportunistic / execution-layer cleanup sprint |
| DEF-184 | `RejectionStage` → `RejectionStage` + `TrackingReason` split — shadow-mode and overflow routing aren't really "rejections." Current `RejectionStage.SHADOW` appears in `FilterAccuracy.by_stage` breakdowns as a rejection category, which is semantically wrong. Touches the enum, FilterAccuracy cut logic, REST serialization on `/counterfactual/accuracy`, `counterfactual_positions.rejection_stage` SQLite schema, and every `SignalRejectedEvent(stage=SHADOW)` emission site. | MEDIUM | **Dedicated cross-domain session, must coordinate with DEF-177** (both want to modify RejectionStage in orthogonal directions) |
| DEF-185 | Analytics-layer `assert isinstance` anti-pattern (DEF-106 follow-on) — 5 remaining sites in `analytics/ensemble_evaluation.py` × 3 + `intelligence/learning/outcome_collector.py` × 2. | LOW | Opportunistic / next analytics-layer cleanup sprint |

---

## DEC register (this campaign)

| DEC # | Description | Session(s) | Status |
|---|---|---|---|
| DEC-384 | `load_config()` standalone YAML overlay (Option B); `_STANDALONE_SYSTEM_OVERLAYS` registry in `argus/core/config.py` | FIX-01 (landed), FIX-02 (first extension with `overflow.yaml`) | ✅ LANDED |

---

## Outstanding code-level items (not DEF-tracked)

Items too small/cosmetic to promote to DEF, but worth surfacing at the appropriate session kickoff:

| Item | Location | Severity | Target pickup |
|---|---|---|---|
| `TestOverflowConfigYamlAlignment` no-op after system.yaml overflow removal | `tests/intelligence/test_config.py` | INFO | FIX-13 test-hygiene (Stage 8) |
| RSK-NEW-5 dangling reference in two AI module comments | `argus/ai/conversations.py`, `argus/ai/usage.py` | LOW | FIX-07 intelligence (Stage 5) — candidate |
| Cosmetic X1–X6 (sprint/DEC/AMD archaeology comments) | `argus/main.py` | INFO | Future comment-only pass |
| `tests/test_main.py` stale mocks (DEF-049 isolation — pre-existing, covers older subsystems) | `tests/test_main.py` | INFO | Broader refresh unlikely before FIX-13 |
| `populate_historical_cache.py` `CANDIDATE_CACHE_DIRS` LaCie legacy entries | `scripts/populate_historical_cache.py:70-75` | INFO | Opportunistic when that script is next touched |
| Shadow-variant badge rendering (`strat_dip_and_rip__v2_*`/`v3_*` still greyed out) | `argus/ui/src/utils/strategyConfig.ts` + `Badge.tsx` | LOW | New DEF if operator wants a slot; else opportunistic |
| 5 remaining DEF-138 rejection-reason labels (`chase_protection`, `volume_insufficient`, `quality_below_threshold`, `terminal_state`, `max_positions`) | Various strategy files | LOW | Sprint 33+ observability |
| M03/M05/M06 frontend primitive migration (~35 useQuery callers / ~10 error-UI sites / ~15 skeleton sites) | `argus/ui/src/` | INFO | Opportunistic during future page touches |
| Audit spec-prompt file-path drift posture (FIX-12 had `.ts` vs `.tsx` systemic drift; FIX-19 had `Throughout` + wildcard entries) | `docs/audits/audit-2026-04-21/phase-3-prompts/` | INFO | Ongoing — verify targets in every kickoff |

---

## Campaign-wide process notes and learnings

**Parallel execution risk profile (Pass 3 findings)**
1. **c3bc758 chimera incident.** During Pass 3, FIX-19's session momentarily created an intermediate commit that swept FIX-12's working-tree edits under a FIX-19 label. The session reset it locally before pushing; never touched origin. Outcome clean, but margin was thinner than desired. Future parallel batches should add a hard pre-commit `git diff --name-only --cached` check against declared scope.
2. **Working-tree noise contaminates pytest re-runs during review.** FIX-21's reviewer ran pytest 3 times with (1, 15, 13) failures respectively, all explained by concurrent uncommitted FIX-19 test work. Resolution: `git stash -u` + re-run → clean. For campaign post-mortem: reviewer skills should default to `git stash -u` before pytest when working tree is dirty, restore after.
3. **Rule of thumb:** Docs-only sessions parallelize freely. Code sessions on shared high-value paths must serialize. File-disjoint code sessions can parallelize with caveats above.

**Kickoff prompt hygiene**
- **Path drift:** Audit prompts predate some file reorganizations (FIX-20 `models.py` → `state.py`; FIX-12 `.ts` vs `.tsx`; FIX-19 "Throughout" + wildcard entries). Always grep-verify file paths before editing.
- **Baseline staleness:** Every FIX-NN prompt says "Expected baseline: 4,934". Campaign has moved past this baseline repeatedly; kickoffs must correct with current HEAD baseline.
- **DEF naming collisions:** Audit uses DEF-NNN labels internally that may or may not correspond to CLAUDE.md-tracked DEFs. FIX-19's "DEF-138 scope" is audit-internal; CLAUDE.md's DEF-138 is a different Sprint 32.8 item. Kickoffs should disambiguate explicitly.

**Review mechanism reliability**
- FIX-03 got CONCERNS verdict exclusively because reviewer grep-verified CLAUDE.md DEF-074/093 strikethroughs that close-out claimed were present. This catch is load-bearing; all future sessions must grep-verify DEF strikethroughs before commit.
- Tier 2 review catches what Tier 1 self-review misses. Keep the pair.

**Structural patterns to preserve**
- FIX-01's DEC-384 registry pattern (`_STANDALONE_SYSTEM_OVERLAYS` in `argus/core/config.py`) is the canonical standalone-overlay pattern. Extend via tuple entry + flat bare-fields YAML (not wrapped). FIX-02 was the first extension.
- FIX-12's helper-export pattern (`getStrategyLetter(id)`, `getStrategyShortName(id)`) over consumer-side derivation is the canonical single-source-of-truth pattern for frontend config consolidation.
- FIX-19's legacy alias layer (`STRATEGY_LEGACY_ALIASES` in `strategyConfig.ts`) is the canonical pattern for supporting old bare short IDs (`'orb'` → `'strat_orb_breakout'`) without hardcoding a second map.

---

## Stage 3 complete (2026-04-22)

All three Stage 3 sessions landed cleanly. Executed in two waves:
- **Wave 1 (parallel):** FIX-14 (docs) + FIX-16 (config) — both CLEAR
- **Wave 2 (solo Rule-4 serial):** FIX-04 (execution) — CLEAR with gold-standard revert-and-fail proof

Plus the IMPROMPTU-def172-173-175 session between Stage 2 and Stage 3 (DEF-172 RESOLVED-VERIFIED, DEF-173 RESOLVED, DEF-175 opened for post-31.9 sprint).

Test progression: 4,965 → 4,984 (FIX-16 +19) → 4,985 (FIX-04 +1). Vitest unchanged at 859.

## Stage 4 Wave 1 complete (2026-04-22)

FIX-10 + FIX-18 landed in parallel, both CLEAR. FIX-18 introduced the first `.github/workflows/ci.yml`, which triggered two hotfix cycles:

1. **`d261e7b` + `a896985`** — CI run surfaced that `pytest-xdist` was missing from `[dev]` extras (local envs had it via system pip; clean install did not). Declared in `pyproject.toml`, FIX-18 close-out annotated.
2. **`793d4fd`** — First fully passing CI after clean-install bugs: (a) git submodule init missing, (b) seaborn missing for report generator import, (c) one `jwt` import shim missing in a test under jose-3.5 line, (d) walk-forward validation needed `@pytest.mark.integration` marking.

## CI infrastructure status

First fully passing CI run achieved at commit `793d4fd`:

- **pytest:** 4,977 passing + 0 failing + 0 errors (CI runs with `-m "not integration"`)
- **Vitest:** 859 passing + 0 failing
- **Known-flake DEFs:** none fired (DEF-150, DEF-163 × 2, DEF-167, DEF-171 — all four dormant)
- **Workflow file:** `.github/workflows/ci.yml` (added by FIX-18 P1-I-M06)
- **Clean-install bugs unmasked and fixed:** pytest-xdist in `[dev]`, submodule init, seaborn, jwt-import shim, walk-forward integration marking
- **Known deprecation warning:** Node 20 on three GitHub Actions — tracked as **DEF-181** (June 2, 2026 deadline)

## Stage 4 complete (2026-04-22)

Stage 4 sealed with FIX-05 Wave 2 CLEAR. Both waves landed with zero scope violations:
- **Wave 1 (parallel):** FIX-10 (backtest legacy, 0 tests) + FIX-18 (deps + CI workflow, +0 tests, two hotfix cycles)
- **Wave 2 (solo):** FIX-05 (core orchestrator/risk/regime, +10 tests, 5 DEFs closed, 1 opened)

FIX-05 closed DEF-091, DEF-092, DEF-104, DEF-163 (Python-side), and DEF-170 via `attach_vix_service()` re-instantiation. DEF-182 (Weekly reconciliation stub) opened as an opportunistic operations-sprint item.

Post-Stage-4 expected CI baseline: 4,992 pytest (+15 over 793d4fd's 4,977 after FIX-05's +10 + FIX-16's +19 minus integration filter adjustments) + 859 Vitest.

## Stage 5 preview (FIX-06 + FIX-07 next)

Next up: FIX-06 (data layer) + FIX-07 (intelligence layer). See the master tracker at `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` for the full remaining-session + DEF matrix.

---

## Snapshot maintenance protocol

This document is the external survival buffer for the campaign state. **Update at every stage barrier** (ideally as the last step before closing a stage):

1. Edit this file in `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`
2. Update `Last updated`, `Campaign HEAD`, baseline tests at top
3. Update the Stage status table
4. Add rows to Session history for any new sessions
5. Move DEFs between register sections as status changes
6. Commit with message `docs(sprint-31.9): update running register — <stage>`

The goal is that anyone (or any fresh Claude.ai conversation) can read this file and know exactly where the campaign stands without reading every prior close-out and review document.

**Hydration pattern for a fresh Claude.ai conversation:** paste this file contents + attach the most recent FIX-NN close-out and review — that plus project knowledge is enough to resume.
