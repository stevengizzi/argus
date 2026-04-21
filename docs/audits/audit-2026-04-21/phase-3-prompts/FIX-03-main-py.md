# Fix Session FIX-03-main-py: main.py — lifecycle, imports, type hints, dead wiring

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 31
**Files touched:** `argus/core/orchestrator.py`, `argus/intelligence/experiments/spawner.py`, `argus/intelligence/experiments/store.py`, `argus/main.py`, `docs/architecture.md`, `tests/test_main.py`
**Safety tag:** `weekend-only`
**Theme:** Targeted fixes across argus/main.py (and a handful of call-site modules) spanning dead code removal, import ordering, type-hint tightening, and the DEC-275 copy-paste collapse for pattern loading.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MUST be paused. No open positions. No active alerts.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline (expected for weekend-only)"

# If paper trading is running, STOP before proceeding:
#   ./scripts/stop_live.sh
# Confirm zero open positions at IBKR paper account U24619949 via Command Center.
# This session MAY touch production paths. Do NOT run during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-03): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/main.py`: 26 findings
- `argus/core/orchestrator.py`: 1 finding
- `argus/intelligence/experiments/spawner.py`: 1 finding
- `argus/intelligence/experiments/store.py`: 1 finding
- `docs/architecture.md`: 1 finding
- `tests/test_main.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-A1-C01` [CRITICAL]

**File/line:** [main.py:2117-2183](argus/main.py#L2117-L2183)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_reconstruct_strategy_state()` — 66-line method is **defined but never called**. The `start()` method docstring at [main.py:195](argus/main.py#L195) lists "Strategies (with mid-day reconstruction if applicable)" as a responsibility, and Phase 9's inline comment at [main.py:973](argus/main.py#L973) says "If mid-day restart, strategies reconstruct their own state" — but the actual reconstruction path (fetch today's historical bars, replay through `strategy.on_candle()`) is orphaned. Mid-day restart currently relies on whatever state `orchestrator.run_pre_market()` builds, not this code.

**Impact:**

> Either this mid-day replay was intentionally superseded by orchestrator pre-market logic (in which case 66 lines of dead wire-up is confusingly present and claims to handle scenarios it does not), or a real mid-day-restart recovery path has been silently disabled. Needs operator disposition.

**Suggested fix:**

> Confirm whether mid-day reconstruction is handled elsewhere. If yes, **delete** the method and update `start()` docstring + Phase 9 comment. If no, **wire** it into Phase 9 (call `await self._reconstruct_strategy_state(warmup_symbols)` after `orchestrator.run_pre_market()`).

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 2: `P1-A1-M02` [MEDIUM]

**File/line:** [main.py:739](argus/main.py#L739), [main.py:792](argus/main.py#L792)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Triple load of `orchestrator.yaml`.** `load_config()` already parses it into `self._config.orchestrator` at [main.py:206](argus/main.py#L206) (via [core/config.py:1359](argus/core/config.py#L1359)). Phase 8.5 reads the file again at line 739 (`orchestrator_yaml_pre`) to construct `OrchestratorConfig` for the V2 regime classifier. Phase 9 reads it a **third** time at line 792 (`orchestrator_yaml`) for the Orchestrator itself. DEF-093 noted the "duplicate"; this session confirms it is a triple load.

**Impact:**

> Three parse sites means three places a YAML-key drift can introduce divergence. Phase 8.5's `orchestrator_config_pre` sees exactly the same file but the independent parse makes it look like a separate config domain.

**Suggested fix:**

> Use `self._config.orchestrator` everywhere. Delete the ad-hoc re-parses at lines 739-740 and 792-793.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 3: `P1-A1-M03` [MEDIUM]

**File/line:** [main.py:2117](argus/main.py#L2117) → nobody / [main.py:2185-2359](argus/main.py#L2185-L2359) shutdown
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`_catalyst_storage` and `regime_history_store` never closed at shutdown.** `CatalystStorage` is `.initialize()`d at [main.py:1114](argus/main.py#L1114); `RegimeHistoryStore` at [main.py:785](argus/main.py#L785). Neither has a `.close()` call in `shutdown()`. `Orchestrator.stop()` ([core/orchestrator.py:146-154](argus/core/orchestrator.py#L146-L154)) does not close the regime-history store it was passed.

**Impact:**

> SQLite connections rely on process teardown to close. Recent sprints (31.8 S2) specifically called out unclosed/unVACUUMed SQLite as an incident class. Counterfactual + eval stores are both explicitly closed; these two are not — asymmetric.

**Suggested fix:**

> Add `await self._catalyst_storage.close()` (if method exists) before step 6 (DB close) in `shutdown()`. For `regime_history_store`, either store it on `self` and close it in `shutdown()`, or have `Orchestrator.stop()` close it.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 4: `P1-A1-M04` [MEDIUM]

**File/line:** [main.py:534](argus/main.py#L534), [main.py:553](argus/main.py#L553), [main.py:572](argus/main.py#L572), [main.py:591](argus/main.py#L591), [main.py:610](argus/main.py#L610), [main.py:629](argus/main.py#L629), [main.py:651](argus/main.py#L651), [main.py:670](argus/main.py#L670), [main.py:689](argus/main.py#L689), [main.py:710](argus/main.py#L710)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **10 direct writes to `PatternBasedStrategy._config_fingerprint`** — a private attribute. The class has a public `config_fingerprint` property getter at [pattern_strategy.py:136](argus/strategies/pattern_strategy.py#L136) but no setter. Assignment reaches inside via the underscore-prefixed name.

**Impact:**

> Encapsulation violation; brittle to any refactor of `PatternBasedStrategy`. If the attribute is renamed, 10 call sites break silently (no type error — just an orphan attribute).

**Suggested fix:**

> Add a `set_config_fingerprint()` method or accept `config_fingerprint` as a constructor kwarg on `PatternBasedStrategy`. Then update the 10 sites.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 5: `P1-A1-M05` [MEDIUM]

**File/line:** [main.py:522-715](argus/main.py#L522-L715)
**Safety:** `weekend-only` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **~200 lines of copy-paste for PatternBasedStrategy loading.** Ten near-identical 18-line blocks for Bull Flag / Flat-Top / Dip-and-Rip / HOD / ABCD / Gap-and-Go / PMH / Micro Pullback / VWAP Bounce / Narrow Range. All differ only in (strategy_name, yaml_filename, loader_function). The list is repeated again verbatim at [main.py:857-906](argus/main.py#L857-L906) for variant spawning, and a **third** time in the `orchestrator.register_strategy` cascade at [main.py:820-839](argus/main.py#L820-L839).

**Impact:**

> Adding the 11th pattern requires editing ~4 locations in Phase 8 + Phase 9 spawner + register cascade. High drift surface. DEF-144 already acknowledged a factory pattern exists (`build_pattern_from_config`) — only half-applied.

**Suggested fix:**

> Define a single tuple list `[(name, yaml_filename, loader), ...]` at the top of Phase 8, iterate once to produce `dict[str, PatternBasedStrategy

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 6: `P1-A1-M06` [MEDIUM]

**File/line:** [main.py:1744-1745](argus/main.py#L1744-L1745)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Silent catalyst-lookup failures.** `except Exception: logger.debug("Catalyst lookup failed for %s", signal.symbol)` — at INFO default level, repeated DB failures produce zero visible output, yet the failure path silently degrades signal quality scoring (catalysts default to empty list, lowering `catalyst_quality` score contribution).

**Impact:**

> During a real catalyst DB outage, operators see no warning. Quality pipeline keeps running with systematically lower quality scores, potentially filtering viable signals.

**Suggested fix:**

> Raise to `logger.warning(..., exc_info=True)` at least on first N failures, then fall back to rate-limited via `ThrottledLogger` (already available per Sprint 27.75).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 7: `P1-A1-M07` [MEDIUM]

**File/line:** [main.py:1115-1116](argus/main.py#L1115-L1116)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **CatalystStorage init error masked.** `except Exception: logger.warning("CatalystStorage not available for quality pipeline")` — no `exc_info`, no actual exception text. The string "not available" is ambiguous (import error? DB lock? disk full?).

**Impact:**

> Fail-to-start of quality-pipeline catalyst data is invisible in logs. Contrast with [main.py:948-953](argus/main.py#L948-L953) (experiment spawner) and [main.py:2071](argus/main.py#L2071) (SessionEndEvent), which both pass `exc_info=True`.

**Suggested fix:**

> Add `exc_info=True` to the `logger.warning()` call.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 8: `P1-A1-M08` [MEDIUM]

**File/line:** [main.py:1134-1136](argus/main.py#L1134-L1136)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Telemetry store wired to strategies AFTER `run_pre_market()`.** Phase 10.3 sets `strategy.eval_buffer.set_store(self._eval_store)` for each strategy, but this occurs *after* `orchestrator.run_pre_market()` ran at line 974 (which in mid-day restart scenarios replays historical bars through strategies that may emit evaluation events). Any evaluations emitted during pre-market reconstruction are written to an in-memory ring buffer with no store attached.

**Impact:**

> Mid-day restart loses early-session evaluation history until the next buffer flush. Low probability in practice (reconstruction is historical; most telemetry happens live).

**Suggested fix:**

> Move the `set_store()` loop to run before `orchestrator.run_pre_market()` — after `eval_store.initialize()` but before orchestrator start. Create telemetry store earlier in the sequence (Phase 2.5 alongside DB).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 9: `P1-A1-M09` [MEDIUM]

**File/line:** [main.py:279-295](argus/main.py#L279-L295), [main.py:981-995](argus/main.py#L981-L995), etc.
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Inconsistent health-monitor coverage.** Core components register with `health_monitor.update_component()` (event_bus, database, broker, risk_manager, data_service, scanner, strategy, orchestrator, order_manager, api_server). But these subsystems do NOT: QualityEngine (Phase 10.25), EvaluationEventStore (Phase 10.3), IntradayCandleStore (10.5), CounterfactualTracker (10.7), RegimeClassifierV2 (8.5), UniverseManager (7.5).

**Impact:**

> Operators' `/api/v1/health` endpoint shows subset of reality. If counterfactual tracker fails, healthcheck is green.

**Suggested fix:**

> Add `health_monitor.update_component(...)` calls for each optional subsystem at its Phase entry with HEALTHY/DEGRADED based on `if xxx_config.enabled`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 10: `P1-A1-M10` [MEDIUM]

**File/line:** [main.py:1369-1371](argus/main.py#L1369-L1371) + [core/orchestrator.py:665-705](argus/core/orchestrator.py#L665-L705)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Dual regime-reclassification poll confirmed (DEF-074).** `main.py._run_regime_reclassification` (300s sleep) and `Orchestrator._poll_loop` (internal cadence) both call `reclassify_regime()`. CLAUDE.md notes this is idempotent/benign but still "redundant". Two polls means two log lines per 5-minute tick at steady state.

**Impact:**

> Log noise; redundant DB writes to `regime_history.db` if `persist_history=True`; small wasted CPU. Not currently harmful.

**Suggested fix:**

> Choose one. Since Orchestrator owns the regime classifier, `Orchestrator._poll_loop` is the natural home. Delete `_run_regime_reclassification` + the `_regime_task` asyncio.create_task. Removes ~55 lines.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 11: `P1-A1-L01` [LOW]

**File/line:** [main.py:1161-1176](argus/main.py#L1161-L1176)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Closure-captured CandleEvent subscribers unreachable for unsubscribe.** `_breadth_on_candle` and `_intraday_on_candle` are async wrappers defined locally inside `start()`, subscribed to the event bus, but never retained on `self`. `shutdown()` has no path to unsubscribe them. Academic since we shut down the whole process, but pattern-wise blocks clean event-bus teardown.

**Impact:**

> Event bus holds dangling closures. Complicates any future "restart-in-place" feature.

**Suggested fix:**

> Store the wrapper refs on `self` (e.g. `self._breadth_candle_handler`), so `shutdown()` can unsubscribe.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 12: `P1-A1-L02` [LOW]

**File/line:** [main.py:1142-1176](argus/main.py#L1142-L1176)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Phase 10.25, 10.3, 10.5, 10.7 have no `logger.info("[X.Y/12] ...")` entry log.** Phase 1-12 and 7.5, 8.5, 9.5 all log a single-line phase-entry marker; 10.25 / 10.3 / 10.5 (Event Routing) / 10.7 log nothing phase-level. Only per-component init logs fire.

**Impact:**

> Operators reading startup logs can't tell which phase a failure occurred in when one of these sub-phases errors.

**Suggested fix:**

> Add one-line `logger.info("[10.25/12] Initializing quality pipeline...")` etc. for consistency.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 13: `P1-A1-L03` [LOW]

**File/line:** [main.py:161](argus/main.py#L161), [main.py:163](argus/main.py#L163)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Bare generics** — `self._cached_watchlist: list = []` and `self._strategies: dict = {}`. Project rule ([.claude/rules/code-style.md:177](.claude/rules/code-style.md)): "Use parameterized generics: `dict[str, Any]`, `list[str]`, not bare `dict`, `list`".

**Impact:**

> Pylance warning surface; inconsistent with rest of file which parameterizes.

**Suggested fix:**

> Change to `self._cached_watchlist: list[Any] = []` and `self._strategies: dict[str, BaseStrategy] = {}`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 14: `P1-A1-L04` [LOW]

**File/line:** [main.py:160](argus/main.py#L160)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`self._config: object \

**Impact:**

> None`** — opaque. `ArgusConfig` is defined in [core/config.py:680](argus/core/config.py#L680); field could be typed precisely. Same rule violation as L3.

**Suggested fix:**

> Type checker cannot verify `self._config.orchestrator.signal_cutoff_enabled` etc. Every access is `getattr`-defensive despite the config being guaranteed present after Phase 1.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 15: `P1-A1-L05` [LOW]

**File/line:** [main.py:181](argus/main.py#L181), [main.py:1689](argus/main.py#L1689)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`_cutoff_logged` never reset across trading days.** The one-shot flag is set `True` on first post-cutoff signal but never cleared at session rollover. A multi-day run (e.g. over a weekend with the system left up) would never re-log "cutoff active" on Monday.

**Impact:**

> Cosmetic — affects only the informational log, not the cutoff behaviour (which still runs every tick). Multi-day process runs are not the norm.

**Suggested fix:**

> Reset to `False` at daily rollover (tie to `orchestrator.run_pre_market` or a daily task).

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 16: `P1-A1-L06` [LOW]

**File/line:** [main.py:1473](argus/main.py#L1473) vs [main.py:1489](argus/main.py#L1489)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Asymmetric sleep placement in background loops.** `_evaluation_health_check_loop` sleeps at end of iteration (fires immediately at boot); `_run_regime_reclassification` sleeps first (skips boot tick). Both document identical cadence patterns but behave differently.

**Impact:**

> Minor surprise for operators expecting uniform "every N seconds" cadence. Not wrong, just unexpected.

**Suggested fix:**

> Pick one convention and apply uniformly. Sleep-first avoids a boot-time burst of checks before dependencies are fully warm.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 17: `P1-A1-L07` [LOW]

**File/line:** [main.py:1142](argus/main.py#L1142)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **"Phase 10.5 Event Routing" phase number conflicts with `architecture.md`'s "Phase 10.5 Set viable universe on DataService".** Same ordinal used for two different responsibilities.

**Impact:**

> Confusion when reading either doc in isolation.

**Suggested fix:**

> Pick fresh numbering (e.g. 10.4 Event Routing) and update architecture.md in one pass. Part of M1.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 18: `P1-A1-L08` [LOW]

**File/line:** [main.py:221](argus/main.py#L221)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Inline reference to `RSK-NEW-5`** — an ID not found anywhere else in the repo (risk register uses `A-XXX`/`R-XXX` per [.claude/rules/doc-updates.md](.claude/rules/doc-updates.md)).

**Impact:**

> Dangling ID. Either stale or never registered.

**Suggested fix:**

> Either register in `docs/risk-register.md` with a proper RSK- or R- ID, or remove the comment.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 19: `P1-C1-M03` [MEDIUM]

**File/line:** [main.py:94](argus/main.py#L94)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `from argus.execution.alpaca_broker import AlpacaBroker` is an **unconditional module-top import**, while `IBKRBroker` and `SimulatedBroker` are lazy-imported inside the `broker_source` branches at L245 and L260. Inconsistent pattern, and forces `alpaca-py>=0.30` to be installed on every deployment even when the broker is IBKR.

**Impact:**

> Deployment weight (minor). Also an undocumented dependency contract — if alpaca-py ever has a breaking release, IBKR-only deploys will crash at startup even though they don't use Alpaca.

**Suggested fix:**

> Move the Alpaca import inside its `elif` branch matching the pattern of IBKR/Simulated. Optional follow-on: add a `main.py` assertion that `BrokerSource.ALPACA` cannot be combined with `config/system_live.yaml` (reinforces DEC-086's "incubator only").

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 20: `P1-D1-M01` [MEDIUM]

**File/line:** [main.py:1113](argus/main.py#L1113), [main.py:2185-2359](argus/main.py#L2185-L2359)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Quality-pipeline `CatalystStorage` is never closed in shutdown.** Phase 10.25 creates + initializes the connection; shutdown flow closes `_db`, `_eval_store`, `_counterfactual_store`, and the intelligence-pipeline storage (via `shutdown_intelligence()`), but not `self._catalyst_storage`. Related to P1-A1 M3.

**Impact:**

> Unclosed SQLite connection on teardown; contributes to the Sprint 31.8 S2 VACUUM-incident class. If C1 is fixed by pointing at `catalyst.db`, this still leaks a second handle to the same DB file.

**Suggested fix:**

> Prefer to reuse `app_state.catalyst_storage` (from `api/server.py`) rather than opening a second connection. If that is not feasible, add `await self._catalyst_storage.close()` to `shutdown()` before the generic DB close.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 21: `P1-D1-M02` [MEDIUM]

**File/line:** [main.py:1115-1116](argus/main.py#L1115-L1116)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **CatalystStorage init error masked** — `except Exception: logger.warning("CatalystStorage not available for quality pipeline")`, no `exc_info`, no actual exception text. The message is ambiguous ("unavailable" could mean disk full, DB lock, import error, etc.). Identical pattern already flagged in P1-A1 M7 for the same 2-line block.

**Impact:**

> During a real catalyst DB outage, operators see a cryptic warning and an all-B quality-grade distribution for the session. Fail-to-open is impossible to distinguish from "table just empty".

**Suggested fix:**

> Add `exc_info=True`. Better: log the actual `db_path` in the warning so operators can spot the C1-class misconfiguration quickly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 22: `P1-D1-M06` [MEDIUM]

**File/line:** [main.py:1705](argus/main.py#L1705), [main.py:1772](argus/main.py#L1772), [main.py:1810](argus/main.py#L1810), [main.py:1866](argus/main.py#L1866), [main.py:1882](argus/main.py#L1882)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Inconsistent `_counterfactual_enabled` access pattern.** Shadow-mode path uses bare `self._counterfactual_enabled`; the other four rejection-emission sites use `getattr(self, '_counterfactual_enabled', False)`. The attribute is always set in Phase 10.7, so this is not an actual bug today — but a future refactor that reorders Phase init could AttributeError from line 1705 while the other sites degrade gracefully.

**Impact:**

> Low-probability divergence; one of five sites would behave differently than the other four if the attribute ever went missing.

**Suggested fix:**

> Pick one convention. Since the attribute is guaranteed present after `__init__`, drop the `getattr` guards and use `self._counterfactual_enabled` everywhere.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 23: `P1-D1-M13` [MEDIUM]

**File/line:** [main.py:1107-1117](argus/main.py#L1107-L1117) + [api/server.py:156](argus/api/server.py#L156)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Two `CatalystStorage` instances active concurrently in live mode.** Even once C1 is fixed to point both at `data/catalyst.db`, there are still two `aiosqlite.Connection` objects writing/reading the same file (WAL-protected but wasteful). One built by `main.py` for the quality pipeline, one built by `intelligence/startup.py` for the catalyst pipeline + API routes.

**Impact:**

> Unnecessary resource duplication; the second connection's WAL checkpoints can delay the first's reads. Mild.

**Suggested fix:**

> Have main.py's quality pipeline reuse `intelligence_components.storage` passed through the API-server lifespan. Cleanest implementation: move quality-pipeline init into `api/server.py` lifespan alongside the catalyst pipeline, with the shared storage injected.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 24: `P1-G1-M02` [MEDIUM]

**File/line:** [argus/main.py](argus/main.py) (1,096 statements, 874 missed = **20% coverage**)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> `main.py` is the lowest-coverage non-zero module. Most lines are Phase 1-12 startup, most of which is exercised only by `test_main.py` (which is excluded from `-n auto` per DEF-048). Without its integration paths, much of the file only gets touched via narrowly scoped fixtures.

**Impact:**

> Already partially acknowledged (DEF-048 + P1-A1 findings). Coverage number dominates the overall 82% but is somewhat misleading — `main.py` IS integration-tested, just not under xdist. Worth an explicit note so the 82% headline isn't misread.

**Suggested fix:**

> Not a gap to close in P1-G1 directly; align with P1-A1 recommendations. Consider running `test_main.py` in a separate non-xdist pass in CI and merging coverage reports.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-03-main-py**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-03-main-py**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 25: `DEF-074` [MEDIUM]

**File/line:** argus/main.py + argus/core/orchestrator.py
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Dual regime recheck path consolidation

**Impact:**

> Both main.py and Orchestrator._poll_loop call reclassify_regime

**Suggested fix:**

> Delete main.py._run_regime_reclassification; Orchestrator owns cadence (P1-A1 M10)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 26: `DEF-093` [MEDIUM]

**File/line:** argus/main.py:739+792
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Duplicate orchestrator YAML load + _latest_regime_vector typing

**Impact:**

> Triple-load of orchestrator.yaml; _latest_regime_vector uses object|None

**Suggested fix:**

> Use self._config.orchestrator everywhere; type as RegimeVector|None via TYPE_CHECKING

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 27: `P1-A2-L07` [LOW]

**File/line:** [argus/core/orchestrator.py:717-797](argus/core/orchestrator.py#L717-L797) + [argus/main.py — `_run_regime_reclassification`]
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Triple regime-recheck cadence.** `Orchestrator._poll_loop` calls `_run_regime_recheck` on its own cadence (line 704), which internally calls `reclassify_regime`. `main.py._run_regime_reclassification` also calls `reclassify_regime` on a 300s cadence. Both are idempotent but write to `regime_history.db` and publish `RegimeChangeEvent` — duplicated side effects. DEF-074 tracks this; P1-A1 M10 already flagged it from the main.py side.

**Impact:**

> Log noise + duplicate DB writes. Harmless today, but more scheduling paths to maintain than necessary.

**Suggested fix:**

> Pick one. Since Orchestrator owns the classifier, `Orchestrator._poll_loop` should own the cadence. Delete `main.py._run_regime_reclassification` and the associated task bookkeeping.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 28: `P1-D2-M01` [MEDIUM]

**File/line:** [spawner.py:259](argus/intelligence/experiments/spawner.py#L259), [main.py:841-953](argus/main.py#L841-L953), [main.py:1060-1086](argus/main.py#L1060-L1086)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Variant `_exit_overrides` set on strategy instance by spawner but **never wired to OrderManager**. `OrderManager._strategy_exit_overrides` is constructed from `config/strategies/*.yaml` files BEFORE variant spawning; no code path reads `variant_strategy._exit_overrides` and registers it. Any variant with `exit_overrides:` in experiments.yaml would silently get default exit config.

**Impact:**

> DEF-132 exit-override dimension is incomplete end-to-end. Currently latent — no variant uses `exit_overrides:` in `config/experiments.yaml`, so nothing is actively misconfigured. But the feature is documented as shipped in Sprint 32.5 and the first time someone sets `exit_overrides:` they'll get a silent failure.

**Suggested fix:**

> Add a registration method on `OrderManager` (e.g. `register_strategy_exit_override(strategy_id, overrides)`) that also invalidates `_exit_config_cache[strategy_id]`. Call it from main.py for each spawned variant whose `_exit_overrides` is not None. Alternatively, fold variant exit overrides into `strategy_exit_overrides` before OrderManager construction (more invasive because spawning currently happens after OrderManager is built).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 29: `P1-D2-M03` [MEDIUM]

**File/line:** [experiments/store.py:695](argus/intelligence/experiments/store.py#L695), [learning/learning_store.py:215](argus/intelligence/learning/learning_store.py#L215), vs [main.py:1202](argus/main.py#L1202)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `enforce_retention` exists on `ExperimentStore` (90 days default) and `LearningStore` (90 days from `report_retention_days`) but is **never called at boot or on any schedule** in `argus/`. Only `counterfactual_store.enforce_retention` is wired.

**Impact:**

> `data/experiments.db` and `data/learning.db` grow unbounded. Over time, `list_experiments` and `list_reports` pagination degrades, and backups grow. No active failure, just slow accretion.

**Suggested fix:**

> Call `experiment_store.enforce_retention(max_age_days=90)` and `learning_store.enforce_retention(learning_loop_config.report_retention_days)` in the relevant startup phases of `main.py`, mirroring the counterfactual pattern.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 30: `P1-A1-M01` [MEDIUM]

**File/line:** [docs/architecture.md:1183-1210](docs/architecture.md#L1183-L1210) vs [main.py:204-1361](argus/main.py#L204-L1361)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Startup-sequence drift.** `architecture.md` §3.9 lists a 12-phase sequence with sub-phases 7.5, 9.5, 10.5. Actual main.py has **17 phases** (adds 8.5 Regime V2, 10.25 Quality, 10.3 Telemetry, 10.5 Event Routing, 10.7 Counterfactual), and **10.5 semantics have shifted**: docs say "Set viable universe on DataService", code at 10.5 is now "Event Routing" while the "Set viable universe" call moved into Phase 11 ([main.py:1211-1217](argus/main.py#L1211-L1217)).

**Impact:**

> Architecture.md is the canonical entry point for new contributors and for agent context; its startup description is silently wrong in 5 places. Any new-contributor session using it as ground truth will build an incorrect mental model.

**Suggested fix:**

> Rewrite `architecture.md` §3.9 to match the current phase table: enumerate 8.5, 10.25, 10.3, 10.5 (Event Routing), 10.7. Update `main.py`'s own `start()` docstring ([main.py:186-198](argus/main.py#L186-L198)) which also lists only 12 phases.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

### Finding 31: `DEF-048+049` [MEDIUM]

**File/line:** tests/test_main.py
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Additional test_main.py xdist failures + isolation failure

**Impact:**

> 4 tests fail under -n auto + test_orchestrator_uses_strategies_from_registry fails in isolation

**Suggested fix:**

> Apply DEF-046 pattern: empty ANTHROPIC_API_KEY env + explicit ai.enabled=false

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-03-main-py**`.

## Post-Session Verification

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-03-main-py** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-03-main-py**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-03): main.py cleanup

Addresses audit findings:
- P1-A1-C01 [CRITICAL]: '_reconstruct_strategy_state()' — 66-line method is defined but never called
- P1-A1-M02 [MEDIUM]: Triple load of 'orchestrator
- P1-A1-M03 [MEDIUM]: '_catalyst_storage' and 'regime_history_store' never closed at shutdown
- P1-A1-M04 [MEDIUM]: 10 direct writes to 'PatternBasedStrategy
- P1-A1-M05 [MEDIUM]: ~200 lines of copy-paste for PatternBasedStrategy loading
- P1-A1-M06 [MEDIUM]: Silent catalyst-lookup failures
- P1-A1-M07 [MEDIUM]: CatalystStorage init error masked
- P1-A1-M08 [MEDIUM]: Telemetry store wired to strategies AFTER 'run_pre_market()'
- P1-A1-M09 [MEDIUM]: Inconsistent health-monitor coverage
- P1-A1-M10 [MEDIUM]: Dual regime-reclassification poll confirmed (DEF-074)
- P1-A1-L01 [LOW]: Closure-captured CandleEvent subscribers unreachable for unsubscribe
- P1-A1-L02 [LOW]: Phase 10
- P1-A1-L03 [LOW]: Bare generics — 'self
- P1-A1-L04 [LOW]: 'self
- P1-A1-L05 [LOW]: '_cutoff_logged' never reset across trading days
- P1-A1-L06 [LOW]: Asymmetric sleep placement in background loops
- P1-A1-L07 [LOW]: "Phase 10
- P1-A1-L08 [LOW]: Inline reference to 'RSK-NEW-5' — an ID not found anywhere else in the repo (risk register uses 'A-XXX'/'R-XXX' per [
- P1-C1-M03 [MEDIUM]: 'from argus
- P1-D1-M01 [MEDIUM]: Quality-pipeline 'CatalystStorage' is never closed in shutdown
- P1-D1-M02 [MEDIUM]: CatalystStorage init error masked — 'except Exception: logger
- P1-D1-M06 [MEDIUM]: Inconsistent '_counterfactual_enabled' access pattern
- P1-D1-M13 [MEDIUM]: Two 'CatalystStorage' instances active concurrently in live mode
- P1-G1-M02 [MEDIUM]: 'main
- DEF-074 [MEDIUM]: Dual regime recheck path consolidation
- DEF-093 [MEDIUM]: Duplicate orchestrator YAML load + _latest_regime_vector typing
- P1-A2-L07 [LOW]: Triple regime-recheck cadence
- P1-D2-M01 [MEDIUM]: Variant '_exit_overrides' set on strategy instance by spawner but never wired to OrderManager
- P1-D2-M03 [MEDIUM]: 'enforce_retention' exists on 'ExperimentStore' (90 days default) and 'LearningStore' (90 days from 'report_retention_da
- P1-A1-M01 [MEDIUM]: Startup-sequence drift
- DEF-048+049 [MEDIUM]: Additional test_main

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions
- [ ] Commit pushed to `main` with the exact message format above
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-03-main-py**`
