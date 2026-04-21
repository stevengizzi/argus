# Audit: `argus/main.py` (system entry point / wire-up)
**Session:** P1-A1
**Date:** 2026-04-21
**Scope:** `argus/main.py` — the 2,462-line Phase 1-12 startup/shutdown wire-up file.
**Files examined:** 1 deep / ~5 skimmed (architecture.md, core/config.py, core/orchestrator.py, core/health.py, strategies/pattern_strategy.py — cross-referenced only to verify claims)

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C1 | [main.py:2117-2183](argus/main.py#L2117-L2183) | `_reconstruct_strategy_state()` — 66-line method is **defined but never called**. The `start()` method docstring at [main.py:195](argus/main.py#L195) lists "Strategies (with mid-day reconstruction if applicable)" as a responsibility, and Phase 9's inline comment at [main.py:973](argus/main.py#L973) says "If mid-day restart, strategies reconstruct their own state" — but the actual reconstruction path (fetch today's historical bars, replay through `strategy.on_candle()`) is orphaned. Mid-day restart currently relies on whatever state `orchestrator.run_pre_market()` builds, not this code. | Either this mid-day replay was intentionally superseded by orchestrator pre-market logic (in which case 66 lines of dead wire-up is confusingly present and claims to handle scenarios it does not), or a real mid-day-restart recovery path has been silently disabled. Needs operator disposition. | Confirm whether mid-day reconstruction is handled elsewhere. If yes, **delete** the method and update `start()` docstring + Phase 9 comment. If no, **wire** it into Phase 9 (call `await self._reconstruct_strategy_state(warmup_symbols)` after `orchestrator.run_pre_market()`). | weekend-only |

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M1 | [docs/architecture.md:1183-1210](docs/architecture.md#L1183-L1210) vs [main.py:204-1361](argus/main.py#L204-L1361) | **Startup-sequence drift.** `architecture.md` §3.9 lists a 12-phase sequence with sub-phases 7.5, 9.5, 10.5. Actual main.py has **17 phases** (adds 8.5 Regime V2, 10.25 Quality, 10.3 Telemetry, 10.5 Event Routing, 10.7 Counterfactual), and **10.5 semantics have shifted**: docs say "Set viable universe on DataService", code at 10.5 is now "Event Routing" while the "Set viable universe" call moved into Phase 11 ([main.py:1211-1217](argus/main.py#L1211-L1217)). | Architecture.md is the canonical entry point for new contributors and for agent context; its startup description is silently wrong in 5 places. Any new-contributor session using it as ground truth will build an incorrect mental model. | Rewrite `architecture.md` §3.9 to match the current phase table: enumerate 8.5, 10.25, 10.3, 10.5 (Event Routing), 10.7. Update `main.py`'s own `start()` docstring ([main.py:186-198](argus/main.py#L186-L198)) which also lists only 12 phases. | safe-during-trading |
| M2 | [main.py:739](argus/main.py#L739), [main.py:792](argus/main.py#L792) | **Triple load of `orchestrator.yaml`.** `load_config()` already parses it into `self._config.orchestrator` at [main.py:206](argus/main.py#L206) (via [core/config.py:1359](argus/core/config.py#L1359)). Phase 8.5 reads the file again at line 739 (`orchestrator_yaml_pre`) to construct `OrchestratorConfig` for the V2 regime classifier. Phase 9 reads it a **third** time at line 792 (`orchestrator_yaml`) for the Orchestrator itself. DEF-093 noted the "duplicate"; this session confirms it is a triple load. | Three parse sites means three places a YAML-key drift can introduce divergence. Phase 8.5's `orchestrator_config_pre` sees exactly the same file but the independent parse makes it look like a separate config domain. | Use `self._config.orchestrator` everywhere. Delete the ad-hoc re-parses at lines 739-740 and 792-793. | weekend-only |
| M3 | [main.py:2117](argus/main.py#L2117) → nobody / [main.py:2185-2359](argus/main.py#L2185-L2359) shutdown | **`_catalyst_storage` and `regime_history_store` never closed at shutdown.** `CatalystStorage` is `.initialize()`d at [main.py:1114](argus/main.py#L1114); `RegimeHistoryStore` at [main.py:785](argus/main.py#L785). Neither has a `.close()` call in `shutdown()`. `Orchestrator.stop()` ([core/orchestrator.py:146-154](argus/core/orchestrator.py#L146-L154)) does not close the regime-history store it was passed. | SQLite connections rely on process teardown to close. Recent sprints (31.8 S2) specifically called out unclosed/unVACUUMed SQLite as an incident class. Counterfactual + eval stores are both explicitly closed; these two are not — asymmetric. | Add `await self._catalyst_storage.close()` (if method exists) before step 6 (DB close) in `shutdown()`. For `regime_history_store`, either store it on `self` and close it in `shutdown()`, or have `Orchestrator.stop()` close it. | weekend-only |
| M4 | [main.py:534](argus/main.py#L534), [main.py:553](argus/main.py#L553), [main.py:572](argus/main.py#L572), [main.py:591](argus/main.py#L591), [main.py:610](argus/main.py#L610), [main.py:629](argus/main.py#L629), [main.py:651](argus/main.py#L651), [main.py:670](argus/main.py#L670), [main.py:689](argus/main.py#L689), [main.py:710](argus/main.py#L710) | **10 direct writes to `PatternBasedStrategy._config_fingerprint`** — a private attribute. The class has a public `config_fingerprint` property getter at [pattern_strategy.py:136](argus/strategies/pattern_strategy.py#L136) but no setter. Assignment reaches inside via the underscore-prefixed name. | Encapsulation violation; brittle to any refactor of `PatternBasedStrategy`. If the attribute is renamed, 10 call sites break silently (no type error — just an orphan attribute). | Add a `set_config_fingerprint()` method or accept `config_fingerprint` as a constructor kwarg on `PatternBasedStrategy`. Then update the 10 sites. | weekend-only |
| M5 | [main.py:522-715](argus/main.py#L522-L715) | **~200 lines of copy-paste for PatternBasedStrategy loading.** Ten near-identical 18-line blocks for Bull Flag / Flat-Top / Dip-and-Rip / HOD / ABCD / Gap-and-Go / PMH / Micro Pullback / VWAP Bounce / Narrow Range. All differ only in (strategy_name, yaml_filename, loader_function). The list is repeated again verbatim at [main.py:857-906](argus/main.py#L857-L906) for variant spawning, and a **third** time in the `orchestrator.register_strategy` cascade at [main.py:820-839](argus/main.py#L820-L839). | Adding the 11th pattern requires editing ~4 locations in Phase 8 + Phase 9 spawner + register cascade. High drift surface. DEF-144 already acknowledged a factory pattern exists (`build_pattern_from_config`) — only half-applied. | Define a single tuple list `[(name, yaml_filename, loader), ...]` at the top of Phase 8, iterate once to produce `dict[str, PatternBasedStrategy | None]`, then re-iterate the same dict for registration and variant-spawning. Cuts ~150 lines and collapses the cascade to one loop. | weekend-only |
| M6 | [main.py:1744-1745](argus/main.py#L1744-L1745) | **Silent catalyst-lookup failures.** `except Exception: logger.debug("Catalyst lookup failed for %s", signal.symbol)` — at INFO default level, repeated DB failures produce zero visible output, yet the failure path silently degrades signal quality scoring (catalysts default to empty list, lowering `catalyst_quality` score contribution). | During a real catalyst DB outage, operators see no warning. Quality pipeline keeps running with systematically lower quality scores, potentially filtering viable signals. | Raise to `logger.warning(..., exc_info=True)` at least on first N failures, then fall back to rate-limited via `ThrottledLogger` (already available per Sprint 27.75). | weekend-only |
| M7 | [main.py:1115-1116](argus/main.py#L1115-L1116) | **CatalystStorage init error masked.** `except Exception: logger.warning("CatalystStorage not available for quality pipeline")` — no `exc_info`, no actual exception text. The string "not available" is ambiguous (import error? DB lock? disk full?). | Fail-to-start of quality-pipeline catalyst data is invisible in logs. Contrast with [main.py:948-953](argus/main.py#L948-L953) (experiment spawner) and [main.py:2071](argus/main.py#L2071) (SessionEndEvent), which both pass `exc_info=True`. | Add `exc_info=True` to the `logger.warning()` call. | weekend-only |
| M8 | [main.py:1134-1136](argus/main.py#L1134-L1136) | **Telemetry store wired to strategies AFTER `run_pre_market()`.** Phase 10.3 sets `strategy.eval_buffer.set_store(self._eval_store)` for each strategy, but this occurs *after* `orchestrator.run_pre_market()` ran at line 974 (which in mid-day restart scenarios replays historical bars through strategies that may emit evaluation events). Any evaluations emitted during pre-market reconstruction are written to an in-memory ring buffer with no store attached. | Mid-day restart loses early-session evaluation history until the next buffer flush. Low probability in practice (reconstruction is historical; most telemetry happens live). | Move the `set_store()` loop to run before `orchestrator.run_pre_market()` — after `eval_store.initialize()` but before orchestrator start. Create telemetry store earlier in the sequence (Phase 2.5 alongside DB). | weekend-only |
| M9 | [main.py:279-295](argus/main.py#L279-L295), [main.py:981-995](argus/main.py#L981-L995), etc. | **Inconsistent health-monitor coverage.** Core components register with `health_monitor.update_component()` (event_bus, database, broker, risk_manager, data_service, scanner, strategy, orchestrator, order_manager, api_server). But these subsystems do NOT: QualityEngine (Phase 10.25), EvaluationEventStore (Phase 10.3), IntradayCandleStore (10.5), CounterfactualTracker (10.7), RegimeClassifierV2 (8.5), UniverseManager (7.5). | Operators' `/api/v1/health` endpoint shows subset of reality. If counterfactual tracker fails, healthcheck is green. | Add `health_monitor.update_component(...)` calls for each optional subsystem at its Phase entry with HEALTHY/DEGRADED based on `if xxx_config.enabled`. | weekend-only |
| M10 | [main.py:1369-1371](argus/main.py#L1369-L1371) + [core/orchestrator.py:665-705](argus/core/orchestrator.py#L665-L705) | **Dual regime-reclassification poll confirmed (DEF-074).** `main.py._run_regime_reclassification` (300s sleep) and `Orchestrator._poll_loop` (internal cadence) both call `reclassify_regime()`. CLAUDE.md notes this is idempotent/benign but still "redundant". Two polls means two log lines per 5-minute tick at steady state. | Log noise; redundant DB writes to `regime_history.db` if `persist_history=True`; small wasted CPU. Not currently harmful. | Choose one. Since Orchestrator owns the regime classifier, `Orchestrator._poll_loop` is the natural home. Delete `_run_regime_reclassification` + the `_regime_task` asyncio.create_task. Removes ~55 lines. | weekend-only |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L1 | [main.py:1161-1176](argus/main.py#L1161-L1176) | **Closure-captured CandleEvent subscribers unreachable for unsubscribe.** `_breadth_on_candle` and `_intraday_on_candle` are async wrappers defined locally inside `start()`, subscribed to the event bus, but never retained on `self`. `shutdown()` has no path to unsubscribe them. Academic since we shut down the whole process, but pattern-wise blocks clean event-bus teardown. | Event bus holds dangling closures. Complicates any future "restart-in-place" feature. | Store the wrapper refs on `self` (e.g. `self._breadth_candle_handler`), so `shutdown()` can unsubscribe. | weekend-only |
| L2 | [main.py:1142-1176](argus/main.py#L1142-L1176) | **Phase 10.25, 10.3, 10.5, 10.7 have no `logger.info("[X.Y/12] ...")` entry log.** Phase 1-12 and 7.5, 8.5, 9.5 all log a single-line phase-entry marker; 10.25 / 10.3 / 10.5 (Event Routing) / 10.7 log nothing phase-level. Only per-component init logs fire. | Operators reading startup logs can't tell which phase a failure occurred in when one of these sub-phases errors. | Add one-line `logger.info("[10.25/12] Initializing quality pipeline...")` etc. for consistency. | safe-during-trading |
| L3 | [main.py:161](argus/main.py#L161), [main.py:163](argus/main.py#L163) | **Bare generics** — `self._cached_watchlist: list = []` and `self._strategies: dict = {}`. Project rule ([.claude/rules/code-style.md:177](.claude/rules/code-style.md)): "Use parameterized generics: `dict[str, Any]`, `list[str]`, not bare `dict`, `list`". | Pylance warning surface; inconsistent with rest of file which parameterizes. | Change to `self._cached_watchlist: list[Any] = []` and `self._strategies: dict[str, BaseStrategy] = {}`. | safe-during-trading |
| L4 | [main.py:160](argus/main.py#L160) | **`self._config: object \| None`** — opaque. `ArgusConfig` is defined in [core/config.py:680](argus/core/config.py#L680); field could be typed precisely. Same rule violation as L3. | Type checker cannot verify `self._config.orchestrator.signal_cutoff_enabled` etc. Every access is `getattr`-defensive despite the config being guaranteed present after Phase 1. | Add `from argus.core.config import ArgusConfig` (or under `TYPE_CHECKING`) and type as `ArgusConfig \| None`. | safe-during-trading |
| L5 | [main.py:181](argus/main.py#L181), [main.py:1689](argus/main.py#L1689) | **`_cutoff_logged` never reset across trading days.** The one-shot flag is set `True` on first post-cutoff signal but never cleared at session rollover. A multi-day run (e.g. over a weekend with the system left up) would never re-log "cutoff active" on Monday. | Cosmetic — affects only the informational log, not the cutoff behaviour (which still runs every tick). Multi-day process runs are not the norm. | Reset to `False` at daily rollover (tie to `orchestrator.run_pre_market` or a daily task). | weekend-only |
| L6 | [main.py:1473](argus/main.py#L1473) vs [main.py:1489](argus/main.py#L1489) | **Asymmetric sleep placement in background loops.** `_evaluation_health_check_loop` sleeps at end of iteration (fires immediately at boot); `_run_regime_reclassification` sleeps first (skips boot tick). Both document identical cadence patterns but behave differently. | Minor surprise for operators expecting uniform "every N seconds" cadence. Not wrong, just unexpected. | Pick one convention and apply uniformly. Sleep-first avoids a boot-time burst of checks before dependencies are fully warm. | weekend-only |
| L7 | [main.py:1142](argus/main.py#L1142) | **"Phase 10.5 Event Routing" phase number conflicts with `architecture.md`'s "Phase 10.5 Set viable universe on DataService".** Same ordinal used for two different responsibilities. | Confusion when reading either doc in isolation. | Pick fresh numbering (e.g. 10.4 Event Routing) and update architecture.md in one pass. Part of M1. | weekend-only |
| L8 | [main.py:221](argus/main.py#L221) | **Inline reference to `RSK-NEW-5`** — an ID not found anywhere else in the repo (risk register uses `A-XXX`/`R-XXX` per [.claude/rules/doc-updates.md](.claude/rules/doc-updates.md)). | Dangling ID. Either stale or never registered. | Either register in `docs/risk-register.md` with a proper RSK- or R- ID, or remove the comment. | safe-during-trading |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| X1 | [main.py:160](argus/main.py#L160) | Comment `# Store config for API access` on `self._config` is misleading — config is used throughout `start()`, `_process_signal()`, `shutdown()`, not just the API. | Misleading. | Drop the trailing comment or change to `# System configuration (ArgusConfig)`. | safe-during-trading |
| X2 | [main.py:164-181](argus/main.py#L164-L181) | **Sprint-tag archaeology in attribute comments.** 11 attribute declarations carry inline `# Sprint 23:` / `# Sprint 24:` / `# Sprint 27.65:` / etc. sprint markers. Per [CLAUDE.md](CLAUDE.md) style: "Don't reference the current task, fix, or callers." | Noise. Sprint provenance lives in git blame and sprint history. | Delete the sprint tags; keep only substantive comments (e.g. the DEC-362 reference on `_bg_refresh_task` is substantive; "Sprint 24: Quality pipeline components" is not). | safe-during-trading |
| X3 | [main.py:1152](argus/main.py#L1152), [main.py:1628](argus/main.py#L1628) | **Inline DEC references** — `# Subscribe to CandleEvents and route to active strategies (DEC-125)`. DEC-125 is recorded in `docs/decision-log.md`; inline tag adds noise. Same style as X2. | Noise. | Drop the DEC tag or convert to a single leading docstring line. | safe-during-trading |
| X4 | [main.py:1045-1053](argus/main.py#L1045-L1053) | **"AMD-10" marker** in comment. AMD-10 is sprint-internal (amendment-10) archaeology. | Noise. | Rewrite as "Warn on legacy trailing-stop fields — superseded by exit_management.yaml" without the amendment tag. | safe-during-trading |
| X5 | [main.py:1015](argus/main.py#L1015), [main.py:1026](argus/main.py#L1026), [main.py:1595](argus/main.py#L1595), [main.py:1605](argus/main.py#L1605) | Multiple "Sprint 27.65 S3" / "Sprint 31A S2" sprint-session archaeology tags inside Phase 9.5 and background refresh. | Noise. | Strip sprint tags from inline comments; keep the semantic content. | safe-during-trading |
| X6 | [main.py:196-197](argus/main.py#L196-L197) | `start()` docstring lists **12 phases**, body runs **17 phases**. Self-contradicting within the same file (separate from M1 which is about architecture.md). | Doc rot inside the implementation. | Update the 12-step list in the docstring to match actual phases or point to a single source of truth ("see PHASES.md" or similar). | safe-during-trading |

---

## Pre-Flagged Items Answered

- **PF-01** `argus/accounting/` is dead. Confirmed: **not imported anywhere in main.py** (and, verified via `grep from argus.accounting`, not imported anywhere in `argus/`). Defer to P1-A2 for full tree scan, but main.py has nothing to clean up here.
- **PF-02** `argus/notifications/` is dead. Same result: not imported in main.py. Notification behaviour goes through `HealthMonitor.send_warning_alert()` ([main.py:1402](argus/main.py#L1402), [main.py:2204](argus/main.py#L2204)), which lives in `core/health.py`, not in the dead `notifications/` package. Defer to P1-A2.
- **Phase 9.5 reference-data wiring for PMH + GapAndGo (Sprint 31A S2).** Confirmed at [main.py:1025-1036](argus/main.py#L1025-L1036). The wiring is generic (`isinstance(strategy, PatternBasedStrategy)`) — all PatternBasedStrategy instances get `initialize_reference_data()` called, not just PMH/GapAndGo. Patterns that don't use reference data are expected to handle an empty/irrelevant dict gracefully. The parallel R2G path at [main.py:1016-1023](argus/main.py#L1016-L1023) uses a different method (`initialize_prior_closes()`) because `RedToGreenStrategy` predates the PatternModule ABC. The duplicate structure is noted in M5 (copy-paste). Clean grafting, not a hack — the main smell is that two separate reference-data wiring paths exist for what is conceptually the same "hydrate prior closes" operation.

---

## Audit Questions — Consolidated Answers

**1. Architectural Coherence**
1.1 Drift confirmed (M1). 5 phases documented, 17 in code.
1.2 Phase 9 has grown to include Orchestrator init + strategy registration cascade + experiment variant spawner + pre-market run + per-strategy health — ~165 lines doing 5 distinct jobs. Phase 10 conflates OrderManager init + fingerprint wiring + RiskManager cross-link. M5 addresses the worst of it.
1.3 `universe_manager.enabled`, `regime_intelligence.enabled`, `quality_engine.enabled`, `counterfactual.enabled`, `experiments.enabled`, `overflow.enabled`, `ai.enabled`, `api.enabled`, `signal_cutoff_enabled` — all gated. Drift is in docs (M1), not gating.

**2. Dead Wire-up**
2.1 `_reconstruct_strategy_state` method (C1). No import-level deadwood.
2.2 All imports used.
2.3 No `_deprecated_`/`_legacy_`/`_v1_` naming. One "AMD-10" marker for legacy trailing-stop fields warning (X4).

**3. Error Handling & Logging**
3.1 No truly silent excepts. One DEBUG-level swallow (M6). Two excepts missing `exc_info=True` (M7).
3.2 Mostly consistent `logger.info/%s/%d` style. No f-strings in logs.
3.3 No `print()` calls.
3.4 Phase-entry logging inconsistent (L2).

**4. Config Gating**
4.1 All optional subsystems gated. Patterns are mixed (`if config.X.enabled`, `use_universe_manager = config.X.enabled and broker_source != SIMULATED`, `if bypass:`) but all correct.
4.2 No dependency-order bugs observed. `load_config()` runs first in Phase 1.
4.3 Inconsistent but not broken — see M5 refactor opportunity.

**5. Shutdown Symmetry**
Gaps: `_catalyst_storage.close()` and `regime_history_store.close()` missing (M3). Closure-captured subscribers unreachable (L1). DEC-371 RECONCILIATION exit reason lives in OrderManager — out of main.py scope. DEC-363 `_flatten_pending` handled inside OrderManager. DEC-369 `_broker_confirmed` same. All background asyncio tasks have cancellation paths (lines 2267-2286 — well done).

**6. Lifespan Handler Safety (Sprint 31.8 S1)**
`_wait_for_port` correctly gates API health. Other blocking-risk init calls observed:
- `await fmp_client.fetch_stock_list()` at [main.py:405](argus/main.py#L405) — HTTP with internal timeouts (inside FMPReferenceClient). Bounded.
- `await self._universe_manager.build_viable_universe(...)` at [main.py:420](argus/main.py#L420) — processes the stock list; may be large under `trust_cache=False`. Under `trust_cache=True` (default per DEC-362) fast path, OK.
- `await self._order_manager.reconstruct_from_broker()` at [main.py:1089](argus/main.py#L1089) — blocks on broker `get_positions()`. Bounded by broker timeouts.
- No asyncio.to_thread() calls observed in main.py (all init is awaitable). The Sprint 31.8 concern (Parquet scan in lifespan) lives in `api/server.py`, not here.

**7. Sprint Archaeology**
X2, X3, X4, X5: Sprint tags, DEC tags, AMD-10 marker. No TODO / FIXME / XXX / HACK found. No commented-out code.

**8. Pre-Flagged Items** — answered above.

---

## Positive Observations

1. **Background-task cancellation batch at [main.py:2267-2286](argus/main.py#L2267-L2286)** — consolidates 5 heterogeneous background tasks into a single cancel+gather loop with named reporting. Clean pattern; replicate for the V2 regime subscribers if L1 is addressed.
2. **`_wait_for_port` defensive port probe at [main.py:1407-1434](argus/main.py#L1407-L1434)** — pattern-of-record for any future network-bound lifespan init. Replaces fire-and-forget `create_task(server.serve())` with a real readiness signal (DEF-155 root-cause fix).
3. **Graceful degradation pattern in Universe Manager init ([main.py:386-446](argus/main.py#L386-L446))** — multi-step fallback (FMP stock list fails → scanner symbols; viable set empty → warmup with scanner symbols; whole UM fails → `use_universe_manager = False`). Each degradation logs at `warning`/`error` with context. Worth replicating for any future "optional external data source" wire-up.
4. **Shadow-mode routing at [main.py:1700-1715](argus/main.py#L1700-L1715)** — crisp: one `getattr()` read of `strategy.config.mode`, early-return for shadow with a SignalRejectedEvent publish, no branching in the live path. Keeps the hot path narrow.
5. **Quality-pipeline bypass predicate at [main.py:1718-1722](argus/main.py#L1718-L1722)** — single `bypass` boolean encodes three orthogonal conditions (SIMULATED broker, quality disabled, quality engine None). Readable; avoids three nested ifs.
6. **Per-strategy exit-management override scanning at [main.py:1060-1068](argus/main.py#L1060-L1068)** — reads every `config/strategies/*.yaml`, extracts the `exit_management` block, builds a `strategy_id → overrides` dict. Good extensibility: adding a new strategy with exit overrides requires zero change to main.py.
7. **Auto-shutdown → SessionEndEvent → Learning Loop chain at [main.py:2009-2115](argus/main.py#L2009-L2115)** — event-driven session rollover with delayed shutdown, promotion evaluator running after SessionEndEvent publishes (so learning loop sees the event first). Good causal ordering.
8. **Counterfactual retention enforcement at boot ([main.py:1202-1204](argus/main.py#L1202-L1204))** — called once per startup, not on a timer. Simple, idempotent, cheap.

---

## Statistics

- Files deep-read: 1 (main.py)
- Files skimmed for cross-reference: 5 (architecture.md §3.9 + Phase refs; core/config.py `load_config` + `ArgusConfig`; core/orchestrator.py `stop`/`_poll_loop`; core/health.py `start`; strategies/pattern_strategy.py `_config_fingerprint`)
- Total findings: **20** (1 critical, 10 medium, 8 low, 6 cosmetic) — note: C1 + M1-M10 + L1-L8 + X1-X6 = 1 + 10 + 8 + 6 = 25 rows; some L findings overlap domains. Raw row count = 25.
- Safety distribution: 9 safe-during-trading / 16 weekend-only / 0 read-only-no-fix-needed / 0 deferred-to-defs
- Estimated Phase 3 fix effort: **3 sessions**
  - Session A (weekend, ~60 min): M2 (triple YAML load), M5 (strategy-loading refactor), M10 (regime poll consolidation), L1 (subscriber refs on self), C1 (reconstruct method disposition) — all touch Phase 8 / Phase 9 / shutdown, same file-overlap group.
  - Session B (weekend, ~30 min): M3 (shutdown close symmetry), M4 (config_fingerprint setter), M7/M6 (logging levels + exc_info), M8 (telemetry store earlier), M9 (health coverage), L5 (cutoff reset), L6 (sleep symmetry).
  - Session C (weekday, ~20 min): M1 (architecture.md rewrite) + all cosmetic (X1-X6) + L2/L3/L4/L7/L8 — documentation/comment-only changes, safe during trading.
