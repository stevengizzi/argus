# Fix Session FIX-05-core-orchestrator-risk-regime: argus/core — orchestrator, risk manager, regime, event bus

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 37
**Files touched:** `argus/accounting/__init__.py`, `argus/core/__init__.py`, `argus/core/clock.py`, `argus/core/config.py`, `argus/core/event_bus.py`, `argus/core/events.py`, `argus/core/health.py`, `argus/core/logging_config.py`, `argus/core/market_correlation.py`, `argus/core/orchestrator.py`, `argus/core/regime.py`, `argus/core/regime_history.py`, `argus/core/risk_manager.py`, `argus/core/sync_event_bus.py`, `config/vix_regime.yaml`, `docs/architecture.md`, `tests/analytics/test_def159_entry_price_known.py`, `tests/core/test_regime_vector_expansion.py`, `tests/core/test_risk_manager.py`
**Safety tag:** `weekend-only`
**Theme:** Core-module findings: Orchestrator lifecycle, Risk Manager guards, Regime Intelligence typing, delete dead accounting/ + notifications/ packages, event bus internals.

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
marker (`audit(FIX-05): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/core/regime.py`: 7 findings
- `argus/core/risk_manager.py`: 6 findings
- `argus/core/event_bus.py`: 3 findings
- `argus/core/events.py`: 3 findings
- `tests/core/test_regime_vector_expansion.py`: 3 findings
- `argus/core/orchestrator.py`: 2 findings
- `argus/accounting/__init__.py`: 1 finding
- `argus/core/__init__.py`: 1 finding
- `argus/core/clock.py`: 1 finding
- `argus/core/config.py`: 1 finding
- `argus/core/health.py`: 1 finding
- `argus/core/logging_config.py`: 1 finding
- `argus/core/market_correlation.py`: 1 finding
- `argus/core/regime_history.py`: 1 finding
- `argus/core/sync_event_bus.py`: 1 finding
- `config/vix_regime.yaml`: 1 finding
- `docs/architecture.md`: 1 finding
- `tests/analytics/test_def159_entry_price_known.py`: 1 finding
- `tests/core/test_risk_manager.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-A2-M07` [MEDIUM]

**File/line:** [argus/core/regime.py:91-194](argus/core/regime.py#L91-L194) + consumers
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> **7 `RegimeVector` fields are computed + persisted but never consumed by trading logic.** `opening_drive_strength`, `first_30min_range_ratio`, `vwap_slope`, `direction_change_count`, `leading_sectors`, `lagging_sectors`, `breadth_thrust` are populated by calculators, included in `to_dict()` for serialization, and stored in `regime_history.db`. Grep shows zero references outside `core/regime*.py`, `core/intraday_character.py`, `core/sector_rotation.py`, and their tests. No strategy YAML populates corresponding `operating_conditions` (defaults are match-any/None).

**Impact:**

> The V2 framework pays to compute these every cycle (intraday task + historical persistence), but no decision depends on them. When the planned consumers (Research Console, strategy regime-sensitivity filters) arrive they may find the field semantics are wrong because nothing has been exercising them.

**Suggested fix:**

> Document explicitly that these fields are "pre-provisioned for future decision consumers." Prefer either (a) a Deferred Items entry noting the planned consumer + sprint, or (b) make computation lazy / gated on `regime_intelligence.persist_history` so non-persisting deployments don't pay the cost.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-05-core-orchestrator-risk-regime**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-05-core-orchestrator-risk-regime**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 2: `P1-A2-M10` [MEDIUM]

**File/line:** [argus/core/regime.py:682-707](argus/core/regime.py#L682-L707)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`RegimeClassifierV2` reaches into `VIXDataService` private attributes.** `vix_config: VixRegimeConfig = vix_data_service._config` — private attribute access to extract boundary configs, then passes the inner fields (`vol_regime_boundaries`, `momentum_window`, `momentum_threshold`, `term_structure_boundaries`, `vrp_boundaries`) to four calculators. DEF-091 tracks this but is LOW-priority; flagging here because V2 wiring is now on the hot path (every `reclassify_regime()` call touches this classifier).

**Impact:**

> Breakage surface: any rename of `_config` on `VIXDataService` silently breaks V2 classification without a type error. Private-access style violates the encapsulation rule in [architecture.md §3.2](docs/architecture.md#L192-L194).

**Suggested fix:**

> Expose a public accessor or named properties on `VIXDataService` (`vix_boundaries`, `momentum_settings`, etc.) and pass those. Prefer constructor-injection of the 4 calculators from the wiring site (main.py) rather than internal instantiation inside `RegimeClassifierV2.__init__`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 3: `P1-A2-L01` [LOW]

**File/line:** [argus/core/regime.py:343-376](argus/core/regime.py#L343-L376)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **4 unused Protocol classes** — `BreadthCalculator`, `CorrelationCalculator`, `SectorRotationCalculator`, `IntradayCalculator`. All four declare `compute(self, indicators: RegimeIndicators) -> …` signatures that do **not** match the actual concrete implementations (e.g. concrete `BreadthCalculator` in `core/breadth.py` takes `on_candle(event: CandleEvent)` not `compute(indicators)`). RegimeClassifierV2 switched to concrete types (Sprint 27.6 S6) leaving the Protocols orphaned. DEF-092 tracks this.

**Impact:**

> Protocol definitions mislead anyone trying to implement a new calculator. Type checker cannot use them to enforce a contract because none of the concrete classes satisfy them.

**Suggested fix:**

> Delete all four Protocol classes from `regime.py`. If cross-module type narrowing is still desired, define Protocols that match the **actual** duck-typed interfaces (`on_candle` + `get_breadth_snapshot` etc.) next to the calculators.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 4: `P1-A2-L09` [LOW]

**File/line:** [argus/core/regime.py:153-157](argus/core/regime.py#L153-L157), [argus/core/regime.py:337-340](argus/core/regime.py#L337-L340), [argus/core/vix_calculators.py:56](argus/core/vix_calculators.py#L56)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Typing style inconsistency: `Optional[X]` vs `X \

**Impact:**

> None`.** New-style `X \

**Suggested fix:**

> None` used for original (Sprint 27.6) regime fields; Sprint 27.9 VIX fields reverted to `Optional[VolRegimePhase]`. Project style prefers new-style (Python 3.10+, `from __future__ import annotations` present).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 5: `P1-A2-L15` [LOW]

**File/line:** [argus/core/regime.py:776-777](argus/core/regime.py#L776-L777), [argus/core/regime.py:940-941](argus/core/regime.py#L940-L941)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`RegimeClassifierV2` accesses private `_compute_trend_score` and `_config` of V1.** `raw_trend = self._v1_classifier._compute_trend_score(indicators)` and `self._v1_classifier._config.vol_low_threshold`. Same DEF-091 pattern as M10 but V1→V2 direction.

**Impact:**

> Breakage surface on V1 rename.

**Suggested fix:**

> Expose `compute_trend_score()` (public) and `vol_low_threshold` / `vol_high_threshold` properties on V1, or pass the relevant thresholds into V2 via constructor.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 6: `DEF-091` [MEDIUM]

**File/line:** argus/core/regime.py + argus/api/routes/vix.py
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> V1/V2 RegimeClassifier private-attribute access + VIXDataService private attrs

**Impact:**

> Private-attr reach-in at 7+ sites; any rename breaks silently

**Suggested fix:**

> Public accessors: attach_vix_service(), compute_trend_score_public(), _config → property (P1-A2 M10 + L15 + P1-F1 #4)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 7: `DEF-092` [LOW]

**File/line:** argus/core/regime.py:343-376
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Unused Protocol types (4 classes, signatures mismatched)

**Impact:**

> Dead code; signatures do not match concrete implementations

**Suggested fix:**

> Delete 4 Protocol classes (BreadthCalculator, CorrelationCalculator, SectorRotationCalculator, IntradayCalculator)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 8: `P1-A2-M01` [MEDIUM]

**File/line:** [argus/core/risk_manager.py:128-148](argus/core/risk_manager.py#L128-L148) vs [docs/architecture.md:585-608](docs/architecture.md#L585-L608)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Risk Manager class docstring and public-method surface are stale.** Class docstring claims `"Phase 1 implements account-level checks only"` but the live code runs cross-strategy checks 4.5a (concentration, DEC-249) and 4.5b (duplicate stock, DEC-121). Architecture.md §3.5 documents four public methods on `RiskManager`: `evaluate_signal`, `on_position_update`, `check_circuit_breakers`, `daily_integrity_check`. Actual class exposes only two of these (`evaluate_signal`, `daily_integrity_check`); circuit-breaker and position-update logic became private (`_check_circuit_breaker_after_close`, `_on_position_closed`).

**Impact:**

> New-contributor or agent sessions reading the docstring / arch doc build an inaccurate mental model of the risk surface. A reviewer might look for `on_position_update` on the public API and not find it.

**Suggested fix:**

> Rewrite class docstring to enumerate current levels (defensive guard → circuit breaker → daily loss → weekly loss → max concurrent → concentration → duplicate → cash reserve → buying power → PDT). Update architecture.md §3.5 to match actual public surface, or re-expose the two private methods as public hooks.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 9: `P1-A2-M02` [MEDIUM]

**File/line:** [argus/core/risk_manager.py:205-230](argus/core/risk_manager.py#L205-L230)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Check numbering gap.** The docstring enumerates checks as `1. … 2. … 3. … 4. … 4.5a. … 4.5b. … 5. … 6. … 7.`, and the code adds a **Check 0** (`share_count <= 0` defensive guard, Sprint 24). That makes 10 checks at 8 ordinal slots. The `4.5a`/`4.5b` notation is a Sprint-24 retrofit; adding Check 0 without renumbering compounds the awkwardness.

**Impact:**

> Cognitive load every time someone has to reason about evaluation order. Non-obvious that Check 0 runs before the circuit breaker.

**Suggested fix:**

> Renumber checks 0–9 contiguously OR document the intended grouping (defensive / circuit / daily / cross-strategy / cash / buying-power / PDT) and drop the decimal IDs. Keep docstring and inline comments aligned.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 10: `P1-A2-L13` [LOW]

**File/line:** [argus/core/risk_manager.py:533-589](argus/core/risk_manager.py#L533-L589)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`PRIORITY_BY_WIN_RATE` duplicate-stock policy is documented-as-V1-simplified but hard-rejects like `BLOCK_ALL`.** Branch logs a warning every time and returns the same rejection message. No win-rate comparison implemented; has been in this state since Sprint 17.

**Impact:**

> Policy field exists in config/schema but picking `PRIORITY_BY_WIN_RATE` behaves identically to picking `BLOCK_ALL`. Config surface is misleading.

**Suggested fix:**

> Either implement the win-rate comparison (requires TradeLogger.get_strategy_win_rate, which may already exist) or remove the enum value + raise a `ValueError` at config load. Current system allows `ALLOW_ALL` (active default per DEC-121/160), so removing `PRIORITY_BY_WIN_RATE` is low-risk.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 11: `P1-G1-C01` [CRITICAL]

**File/line:** [argus/core/risk_manager.py:618-638](argus/core/risk_manager.py#L618-L638)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Post-close circuit-breaker trigger path is uncovered.** `_check_circuit_breaker_after_close()` is one of only two code paths that flip `_circuit_breaker_active=True` (the other is inline in `evaluate_signal()`). Lines 621, 627-634 are uncovered per `--cov-report=term-missing`. Existing `test_daily_loss_limit_triggers_circuit_breaker` at [test_risk_manager.py:314](tests/core/test_risk_manager.py#L314) sets `_daily_realized_pnl` directly and calls `evaluate_signal()` — it never exercises the position-close path that enters `record_realized_pnl()`. A silent regression that broke the post-close breaker would not be caught by any test.

**Impact:**

> The post-close path is how the breaker actually fires in live trading (realized P&L only exists after closes). Uncovered failure-mode branch in safety-critical code.

**Suggested fix:**

> Add a regression test that closes losing positions via `record_realized_pnl()` cumulatively past the daily limit, then asserts (a) `CircuitBreakerEvent` published, (b) `_circuit_breaker_active` true, (c) subsequent signals rejected. Also covers the `return` at line 621 (already-triggered early-exit).

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 12: `P1-G1-C02` [CRITICAL]

**File/line:** [argus/core/risk_manager.py:386-394](argus/core/risk_manager.py#L386-L394), [argus/core/risk_manager.py:405-421](argus/core/risk_manager.py#L405-L421)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Two rejection paths in position-sizing are uncovered.** Both ranges are the "reduce-to-fit → still-below-min-risk-floor → reject" branches for the cash-reserve and buying-power checks. Per `risk-rules.md`: "If ANY of these are false, the order MUST be rejected." The reject branch under DEC-249-style approve-with-modification floor (0.25R) is the specific invariant that keeps undersized reductions from being silently accepted. Happy-path reductions (lines 383-384, 420-421) are covered; the reject-after-reduction branch is not.

**Impact:**

> Legit rejection-reason coverage gap per `testing.md` §Safety-Critical ("every approval path, every rejection path"). A change to `_below_min_risk_floor()` or the reduction math could silently turn rejects into accepts for a corner case.

**Suggested fix:**

> Add two parametrized tests: (1) cash reserve so low the reduced shares violate `min_position_risk_dollars`, (2) buying power so low the reduced shares violate same. Assert `OrderRejectedEvent` with the specific reason substring.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 13: `P1-G1-M08` [MEDIUM]

**File/line:** [argus/core/risk_manager.py:733](argus/core/risk_manager.py#L733)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `run_integrity_check()` branch `if account.equity <= 0: issues.append(...)` is uncovered. Simple check but a zero-equity broker state is a real failure mode.

**Impact:**

> Low; function is an auxiliary diagnostic.

**Suggested fix:**

> Add a 3-line test that constructs a broker returning `Account(equity=0)` and asserts the returned `IntegrityReport.passed is False`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 14: `P1-A2-L02` [LOW]

**File/line:** [argus/core/event_bus.py:87-116](argus/core/event_bus.py#L87-L116) vs [docs/architecture.md:91](docs/architecture.md#L91)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **"FIFO delivery per subscriber" guarantee is weaker than advertised.** `publish()` assigns a monotonic sequence under a lock, then `asyncio.create_task(...)` per handler. Two rapid publishes schedule their handler tasks FIFO on the loop, but with `await` points inside handlers the execution order can interleave (task A pauses, task B runs, task A resumes). The claim is accurate for "enqueue order" but not for "handler-observed order of events."

**Impact:**

> Subtle risk if any handler's logic depends on seeing event N fully processed before event N+1 arrives. Current handlers appear to tolerate interleaving but the invariant is unwritten.

**Suggested fix:**

> Either (a) tighten the code: per-subscriber asyncio.Queue with a single-consumer task (true FIFO), or (b) loosen the docs: document that sequence-number order is preserved but handler-level serialization is the handler's responsibility. Option (b) is lower-risk.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 15: `P1-A2-L03` [LOW]

**File/line:** [argus/core/event_bus.py:154-161](argus/core/event_bus.py#L154-L161)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`EventBus.reset()` clears `_pending` without cancelling tasks.** `self._pending.clear()` discards the tracking set but leaves in-flight handler tasks running in the background. Comment says "Intended for testing only" but if a test runs publish → reset → assertions, orphan tasks can fire after the test has torn down fixtures.

**Impact:**

> Flaky tests in isolation. Low blast radius because most tests `await bus.drain()` before reset.

**Suggested fix:**

> Either cancel pending tasks before clear (`for t in self._pending: t.cancel()`) or raise `RuntimeError` if `_pending` is non-empty at reset time.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 16: `P1-A2-L06` [LOW]

**File/line:** [argus/core/event_bus.py:56-67](argus/core/event_bus.py#L56-L67)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`subscribe()` type parameter `T` is unused.** `subscribe(event_type: type[T], handler: EventHandler)` — `T` isn't referenced in the handler signature (which takes `Any`). The TypeVar achieves nothing; type checkers cannot verify the handler's parameter matches the event type.

**Impact:**

> Missed type-safety opportunity. Not a defect, but when DEC documentation claims "type-only subscription" (DEC-033), the type side is superficial.

**Suggested fix:**

> Define `EventHandler[T] = Callable[[T], Coroutine[Any, Any, None]]` generic alias, then `subscribe(event_type: type[T], handler: EventHandler[T])`. Will surface handler signature mismatches at Pylance time.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 17: `P1-A2-L14` [LOW]

**File/line:** [argus/core/events.py:312](argus/core/events.py#L312)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`CircuitBreakerEvent.level` defaults to `CircuitBreakerLevel.ACCOUNT`.** The default is load-bearing nowhere, and a `CircuitBreakerEvent` constructed without explicit `level` is always about the account — which is almost always the case in the codebase, but masks mistakes where a strategy-level or cross-strategy-level breaker should have been emitted.

**Impact:**

> Possible silent misattribution in future code.

**Suggested fix:**

> Remove the default so callers must specify `level=...` explicitly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 18: `P1-D1-M07` [MEDIUM]

**File/line:** [core/events.py:211](argus/core/events.py#L211)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`SignalRejectedEvent.rejection_stage` docstring lists stage values as `"QUALITY_FILTER", "POSITION_SIZER", "RISK_MANAGER", "SHADOW", "BROKER_OVERFLOW"` (uppercase)** but the actual `RejectionStage` StrEnum uses lowercase values (`"quality_filter"`, `"position_sizer"`, etc.) and all five emission sites emit lowercase strings. `main.py:_on_signal_rejected_for_counterfactual` then calls `RejectionStage(event.rejection_stage)` which would **raise** if anyone followed the docstring and emitted uppercase. Docstring also omits `"margin_circuit"` (proposed per M3).

**Impact:**

> Trap for a future contributor who reads the docstring and emits uppercase — silently collapses all those rejections via the event-bus exception path.

**Suggested fix:**

> Rewrite the docstring to match enum values (lowercase) and reference `RejectionStage` by name.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 19: `DEF-104` [MEDIUM]

**File/line:** argus/core/events.py + argus/models/trading.py
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Dual ExitReason enums must be kept in sync

**Impact:**

> Historical source of 336 Pydantic validation errors (Sprint 27.8)

**Suggested fix:**

> Consolidate to single enum in models/trading.py; re-export from events.py

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 20: `P1-G1-M06` [MEDIUM]

**File/line:** [tests/core/test_regime_vector_expansion.py:36](tests/core/test_regime_vector_expansion.py#L36)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **DEF-163 date-decay root cause identified.** `_make_vector()` helper still hardcodes `computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` as its default. Sprint 32.8 fix only replaced the explicit date in `test_history_store_migration` (which overrides `computed_at=datetime.now(UTC)` at line 302). Every *other* test that calls `_make_vector()` without override still uses March 26 2026 — if retention policy ever deletes rows older than 30 days, those tests will fail deterministically after 2026-04-25. This is the "second hardcoded constant" CLAUDE.md speculated about.

**Impact:**

> Tests currently pass (retention horizon in `RegimeHistoryStore.cleanup_old_snapshots()` isn't being invoked in these tests), so this is latent — it will bite when either retention-aware testing is added or the default is trusted for some date-comparison assertion.

**Suggested fix:**

> Replace the hardcoded default at line 36 with `datetime.now(UTC) - timedelta(hours=1)` (slightly-in-the-past so tests that compare against "now" don't race).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 21: `P1-G2-M01` [MEDIUM]

**File/line:** [tests/core/test_regime_vector_expansion.py:236-314](tests/core/test_regime_vector_expansion.py#L236-L314)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`test_history_store_migration` is NOT an xdist race — it is a UTC-vs-ET timezone boundary bug.** See full characterization in §7 below. The test captures `old_date`/`new_date` using `datetime.now(UTC)` (lines 245, 247) but `RegimeHistoryStore.record()` internally computes `trading_date` using `.astimezone(_ET)` at [regime_history.py:128-130](argus/core/regime_history.py#L128-L130). During the ~4h window when ET date ≠ UTC date (8 PM ET EDT / 7 PM ET EST until midnight UTC), the test fails deterministically: (a) the query for "UTC yesterday" matches both the manually-inserted old row AND the newly-recorded row because ET-today equals UTC-yesterday, (b) the query for "UTC today" matches zero rows because no record has trading_date = ET-tomorrow. Cleanup tracker #4 (Sprint 31.75) and multiple sprint close-outs describe this as an "xdist race"; it is not — it's timezone drift that presents as flake because different test runs hit the boundary window at different times.

**Impact:**

> Mislabeled bug category sends future fixers on a wild goose chase for parallelism issues. Also: this test currently guards the RegimeHistoryStore migration path from Sprint 27.9 — letting it rot means the migration becomes untested. Reconfirmed pre-existing during Sprint 31.85.

**Suggested fix:**

> Replace `datetime.now(UTC)` at lines 245, 247, 302 with `datetime.now(UTC).astimezone(ZoneInfo("America/New_York"))` — then the captured `old_date`/`new_date` will match the store's internal ET-based trading_date and the test will pass deterministically regardless of time-of-day. Also update CLAUDE.md Known Issues entry: re-classify from "xdist race" to "timezone boundary".

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 22: `P1-G2-L01` [LOW]

**File/line:** [tests/core/test_regime_vector_expansion.py:36](tests/core/test_regime_vector_expansion.py#L36)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_make_vector()` hardcodes `computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)` as default** — confirms G1 M6. Not every caller passes `computed_at=` override, so tests like `test_construction_with_all_fields` store March 26 2026 as their timestamp. Latent until a retention cleanup is added or a test starts asserting on "recent" timestamps.

**Impact:**

> Latent; will bite when retention-aware tests are written.

**Suggested fix:**

> Replace with `datetime.now(UTC) - timedelta(hours=1)` (slightly-in-the-past lookback so any "now"-based assertion stays valid).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 23: `P1-A2-M04` [MEDIUM]

**File/line:** [argus/core/orchestrator.py:276-325](argus/core/orchestrator.py#L276-L325) vs [argus/core/orchestrator.py:717-759](argus/core/orchestrator.py#L717-L759)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Regime classification logic duplicated between `run_pre_market()` and `reclassify_regime()`.** Both paths (a) fetch SPY bars, (b) run V1 `compute_indicators()` + `classify()`, (c) update `_current_indicators` / `_current_regime` / `_last_regime_check` / `_spy_unavailable_count`, (d) compute V2 vector and fire-and-forget `_regime_history.record()`, (e) publish `RegimeChangeEvent` if regime changed. Same ~25-line block open-coded twice.

**Impact:**

> Any change to regime bookkeeping (new counter, new event field, new side effect) must be applied in two places. DEF-074 already tracks a related "dual poll" concern; this is the underlying code-level duplication.

**Suggested fix:**

> Extract `_compute_and_apply_regime(spy_bars)` helper; have both `run_pre_market` and `reclassify_regime` call it. `run_pre_market` then owns only the pre-market-specific steps (strategy reconstruction, allocation, activation).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 24: `P1-A2-L08` [LOW]

**File/line:** [argus/core/orchestrator.py:129](argus/core/orchestrator.py#L129)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_latest_regime_vector: object \

**Impact:**

> None`** — duck-typed to avoid a `RegimeVector` import. The `TYPE_CHECKING` block at [line 36-42](argus/core/orchestrator.py#L36-L42) imports `RegimeHistoryStore`, `DataService`, `VIXDataService`, `Broker`, `BaseStrategy` — adding `RegimeVector` to that same block would eliminate the duck-type. DEF-093 tracks this.

**Suggested fix:**

> `latest_regime_vector_summary` property must use `hasattr(x, "to_dict")` instead of proper typing. Same pattern reproduced in `reclassify_regime` at [line 770-772](argus/core/orchestrator.py#L770-L772).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 25: `P1-A2-M09` [MEDIUM]

**File/line:** [argus/accounting/__init__.py](argus/accounting/__init__.py), [argus/notifications/__init__.py](argus/notifications/__init__.py)
**Safety:** `weekend-only` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **PF-01 + PF-02 confirmed dead.** Both packages contain only a 1-line `__init__.py`. Grep `argus\.(accounting\

**Impact:**

> notifications)` across `argus/` and `tests/` returns zero hits (only match is in the earlier P1-A1 audit report). Notification behaviour now lives in `HealthMonitor.send_*_alert()` ([core/health.py:506-522](argus/core/health.py#L506-L522)); accounting was never populated.

**Suggested fix:**

> Scaffolding from Sprint 1 pre-planning that never landed. Visual clutter in the package tree; a new contributor naturally looks there first for accounting / alerts and finds nothing.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 26: `P1-A2-M05` [MEDIUM]

**File/line:** [argus/core/__init__.py:3-21](argus/core/__init__.py#L3-L21)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Partial re-export surface.** Only 7 symbols exported — `AfternoonMomentumConfig`, `BrokerSource`, `DataSource`, `IBKRConfig`, `VwapReclaimConfig` + 2 loaders. Missing every strategy config from Sprint 26 onward (Red-to-Green, Bull Flag, Flat-Top, Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, PMH, Micro Pullback, VWAP Bounce, Narrow Range) and every non-broker infra config (RiskConfig, HealthConfig, OrchestratorConfig, ExitManagementConfig, etc.).

**Impact:**

> Inconsistent: looks like a curated public surface but the curation stopped. Downstream code uses fully-qualified `argus.core.config.XxxConfig` imports to work around it.

**Suggested fix:**

> Either (a) delete the re-export (let callers use fully-qualified paths — easier to keep accurate) or (b) re-export all `*Config` + loaders uniformly. Option (a) is lower-maintenance.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 27: `P1-A2-L05` [LOW]

**File/line:** [argus/core/clock.py:107-113](argus/core/clock.py#L107-L113)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`FixedClock.today()` ignores timezone.** Returns `self._time.date()` directly; `SystemClock.today()` correctly does `datetime.now(self._timezone).date()`. Architecture.md §3.3b documents `today() → date: In configured timezone`. For a `FixedClock(datetime(2026, 4, 21, 3, 0, UTC))`, production would return 2026-04-20 (ET date at 11 PM prior day) while the test helper returns 2026-04-21.

**Impact:**

> Tests may pass while production diverges on date-boundary edges. Test-only utility, but the semantic drift hides the real behaviour.

**Suggested fix:**

> Add optional `timezone` kwarg to `FixedClock.__init__`, default to `America/New_York`, have `today()` call `self._time.astimezone(self._timezone).date()`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 28: `P1-A2-M06` [MEDIUM]

**File/line:** [argus/core/config.py:1260](argus/core/config.py#L1260), [argus/core/config.py:1598](argus/core/config.py#L1598), [argus/core/config.py:1636](argus/core/config.py#L1636), [argus/core/config.py:1669-1720](argus/core/config.py#L1669-L1720)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Sprint-31A strategy configs appended after the loader section divider.** The file's layout is: (1) enums, (2) infra configs, (3) strategy configs, (4) loader functions. Sprint 31A's `MicroPullbackConfig` is placed at line 1260 (inside section 3, correct), but `VwapBounceConfig` (1598) and `NarrowRangeBreakoutConfig` (1636) are placed **after** the section divider ([config.py:1296-1298](argus/core/config.py#L1296-L1298)) intermingled with loaders. The corresponding `load_micro_pullback_config` / `load_vwap_bounce_config` / `load_narrow_range_breakout_config` are dumped at the end of the file (1669, 1686, 1703) instead of following the existing loader order.

**Impact:**

> 1,751-line file is already past the refactor threshold; organizational drift compounds it. Future adds either perpetuate the disorder or trigger a large reflow.

**Suggested fix:**

> Group all strategy configs in the strategy-config block; group all loaders in the loader block. Optionally collapse the 15 mechanical `load_<strategy>_config` functions into a single `load_strategy_config(path, model_cls)` helper driven by a `{strategy_name: config_cls}` registry — ~250 lines become ~20.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 29: `P1-A2-L11` [LOW]

**File/line:** [argus/core/health.py:393](argus/core/health.py#L393) + [argus/core/health.py:480-494](argus/core/health.py#L480-L494)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **Weekly reconciliation is a stub.** `_run_weekly_reconciliation()` logs `"Weekly reconciliation: TODO — implement full comparison"` and only fetches the account as a liveness check. Wired into the integrity loop since Sprint 5 and still unimplemented ~90 sprints later.

**Impact:**

> The feature that "compares trade log with broker records" — a documented architectural responsibility ([architecture.md:1093](docs/architecture.md#L1093)) — doesn't happen. Silent no-op every Saturday at 9 AM.

**Suggested fix:**

> Either implement the comparison against `self._broker.get_order_history(days=7)` + `self._trade_logger.get_trades_by_date_range(...)`, or disable the scheduled path and open a tracked DEF explicitly. Current state is the worst of both.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 30: `P1-A2-L10` [LOW]

**File/line:** [argus/core/logging_config.py:67](argus/core/logging_config.py#L67), [argus/core/logging_config.py:109](argus/core/logging_config.py#L109)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Naive `datetime.now()` in log machinery.** `ConsoleFormatter.format()` uses `datetime.now().strftime("%H:%M:%S")` (no timezone), and log file name uses `datetime.now().strftime("%Y%m%d")`. Project convention (DEC-276 + universal rules) is ET for user-facing times and UTC for machine logs. `JsonFormatter` correctly uses `datetime.now(UTC)`.

**Impact:**

> Console log timestamps drift between developer machines in different timezones; log files rotate on machine-local date not UTC date.

**Suggested fix:**

> Console: use `datetime.now(ZoneInfo("America/New_York")).strftime(...)`. File name: use `datetime.now(UTC).strftime("%Y%m%d")`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 31: `P1-A2-L12` [LOW]

**File/line:** [argus/core/market_correlation.py:20](argus/core/market_correlation.py#L20)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`import asyncio` after third-party imports.** Stdlib `asyncio` is imported on line 20 after `aiohttp`-adjacent imports; project style (code-style.md) requires stdlib-before-third-party-before-local. Ultra-minor but a lint rule exists.

**Impact:**

> Lint surface.

**Suggested fix:**

> Move `import asyncio` into the stdlib block at the top.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 32: `P1-A2-M08` [MEDIUM]

**File/line:** [argus/core/regime_history.py:28-47](argus/core/regime_history.py#L28-L47) vs [docs/architecture.md:746](docs/architecture.md#L746)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **SQLite table name drift.** Code creates `CREATE TABLE IF NOT EXISTS regime_snapshots` but architecture.md §3.6.1 claims the schema is `"regime_history table with id, computed_at, vector_json, primary_regime, regime_confidence, vix_close REAL (nullable)"`. Additionally, the documented columns don't match actual schema (`id, timestamp, trading_date, primary_regime, regime_confidence, trend_score, trend_conviction, volatility_level, volatility_direction, universe_breadth_score, breadth_thrust, avg_correlation, correlation_regime, sector_rotation_phase, intraday_character, regime_vector_json, vix_close` — 17 columns vs ~6 documented).

**Impact:**

> Operators running ad-hoc SQL against `regime_history.db` using the documented table/column names will get "no such table" / "no such column" errors.

**Suggested fix:**

> Update architecture.md §3.6.1 schema block to match current `regime_snapshots` DDL. Include the computed field list and `vix_close` migration note.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 33: `P1-A2-L04` [LOW]

**File/line:** [argus/core/sync_event_bus.py:41-55](argus/core/sync_event_bus.py#L41-L55)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`SyncEventBus` silently omits subscribe/unsubscribe debug logs present in `EventBus`.** `EventBus.subscribe` logs `Subscribed %s to %s`; `SyncEventBus.subscribe` does not. Similarly for `unsubscribe`. Both otherwise share the public surface.

**Impact:**

> When debugging a backtest, subscription lifecycle is invisible. Mild inconsistency.

**Suggested fix:**

> Mirror the debug log lines verbatim. Or extract a shared `_BusBase` and remove the duplication entirely.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 34: `P1-C2-2` [MEDIUM]

**File/line:** [config/vix_regime.yaml](config/vix_regime.yaml) (all lines) + [config/system_live.yaml:161](config/system_live.yaml#L161)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Standalone `vix_regime.yaml` never loaded at runtime** (same drift class as Finding #1). Confirmed by [docs/sprint-history.md:2170](docs/sprint-history.md#L2170) — `load_config()` doesn't read it. `system_live.yaml` `vix_regime:` block only contains `enabled: true`; all thresholds come from `VixRegimeConfig` Pydantic defaults. Comment in `system_live.yaml:161` ("Detailed params in vix_regime.yaml") is misleading.

**Impact:**

> Operator editing `vix_regime.yaml` expects tuning; changes do nothing.

**Suggested fix:**

> Option A: add `vix_regime.yaml` to `load_config()` and merge into `SystemConfig.vix_regime` (same approach as Finding #1). Option B: delete `vix_regime.yaml`, move the commented threshold docs inline into `system_live.yaml`. Option C: update `system_live.yaml:161` comment to note the file is documentation-only.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 35: `P1-A2-M03` [MEDIUM]

**File/line:** [docs/architecture.md:95-150](docs/architecture.md#L95-L150) vs [argus/core/events.py:1-537](argus/core/events.py#L1-L537)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Event-type inventory drift.** Architecture.md §3.1 lists events that do not exist (`LearningInsightEvent` at line 149) and omits events that do: `ShutdownRequestedEvent` ([events.py:357](argus/core/events.py#L357)), `DataStaleEvent`/`DataResumedEvent` ([events.py:374-396](argus/core/events.py#L374-L396)), `AccountUpdateEvent` ([events.py:405](argus/core/events.py#L405)), `SessionEndEvent` ([events.py:504](argus/core/events.py#L504)). Additionally, `UniverseUpdateEvent` is documented as `(viable_count, routing_table_size, cache_age_minutes, per_strategy_counts)` but actual dataclass has two fields: `viable_count, total_fetched` ([events.py:483-495](argus/core/events.py#L483-L495)).

**Impact:**

> Canonical event catalog is silently wrong. Any developer consulting §3.1 to pick subscribers or publish events gets misinformation. A `LearningInsightEvent` referenced in DEC planning (if any) is uncallable.

**Suggested fix:**

> Regenerate the §3.1 event table from `grep @dataclass.*frozen events.py`. Delete `LearningInsightEvent` reference. Correct `UniverseUpdateEvent` field list.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 36: `DEF-163` [LOW]

**File/line:** tests/analytics/test_def159_entry_price_known.py + tests/core/test_regime_vector_expansion.py + 4 Vitest files
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Timezone-boundary bugs + hardcoded Vitest dates (NOT date-decay)

**Impact:**

> (a) UTC/ET mismatch in PnL test; (b) second hardcoded default at line 36; (c) 4 Vitest fixtures with hardcoded dates

**Suggested fix:**

> Fix timezone in log_trade / ET-normalize exit_time; replace hardcoded default; Vitest date fixtures → new Date(Date.now()-N*DAY). UPDATE DEF ROW.

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

### Finding 37: `P1-G2-M06` [MEDIUM]

**File/line:** [tests/core/test_risk_manager.py:289, 306, 323, 346, 423-425, 502](tests/core/test_risk_manager.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **11+ tests mutate RiskManager private attributes (`rm._circuit_breaker_active`, `rm._daily_realized_pnl`, `rm._weekly_realized_pnl`, `rm._pdt_tracker.record_day_trade(...)`, `rm._trades_today`).** This is brittle-setup (Q3.2) + excessive-mocking-via-backdoor (Q2.3). A refactor of RiskManager's internal state shape (e.g., `_daily_realized_pnl → _account_state.daily_pnl`) breaks every test that pokes internals without any public-API change. The tests are effectively testing a specific internal layout, not behavior.

**Impact:**

> Latent maintenance cost. Refactors to RiskManager become larger than they should because the test suite has a private-attribute coupling surface. Also makes the rejection-path tests (G1 C1/C2) harder to add cleanly — the new tests would follow the same anti-pattern.

**Suggested fix:**

> Introduce public test-only methods or a `@classmethod` builder: `RiskManager.with_daily_pnl(-3000.0)` for test setup. Or drive state through published `PositionClosedEvent`s (which already works — see `test_position_closed_updates_daily_pnl` at [line 437](tests/core/test_risk_manager.py#L437)). Gradually migrate each `rm._foo = ...` callsite to event-driven setup.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`.

## Post-Session Verification (before commit)

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
| ... | ~~description~~ **RESOLVED FIX-05-core-orchestrator-risk-regime** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-05-core-orchestrator-risk-regime**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-05` (full ID: `FIX-05-core-orchestrator-risk-regime`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-05-core-orchestrator-risk-regime**` | | |
| Every DEF closure recorded in CLAUDE.md | | |
| Every new DEF/DEC referenced in commit message bullets | | |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | | |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | | |

### Output format

Render the close-out inside a fenced markdown code block (triple backticks
with `markdown` language hint) bracketed by `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---` markers, followed by the `json:structured-closeout`
JSON appendix. Exact format per the close-out.md skill.

The operator will copy this block into the Work Journal conversation on
Claude.ai. Do NOT summarize or modify the format — the conversation parses
these blocks by structure.

### Self-assessment gate

Per close-out.md:
- **CLEAN:** all findings resolved, no unexpected decisions, all tests pass, all regression checks pass
- **MINOR_DEVIATIONS:** all findings addressed but minor judgment calls needed
- **FLAGGED:** any partial finding, test failures, regression check failures, scope exceeded, architectural concerns

**Proceed to the Commit section below UNLESS self-assessment is FLAGGED.**
If FLAGGED, pause. Surface the flag to the operator with a clear
description. Do not push. Wait for operator direction.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-05): core/ cleanup (orchestrator + risk + regime)

Addresses audit findings:
- P1-A2-M07 [MEDIUM]: 7 'RegimeVector' fields are computed + persisted but never consumed by trading logic
- P1-A2-M10 [MEDIUM]: 'RegimeClassifierV2' reaches into 'VIXDataService' private attributes
- P1-A2-L01 [LOW]: 4 unused Protocol classes — 'BreadthCalculator', 'CorrelationCalculator', 'SectorRotationCalculator', 'IntradayCalculato
- P1-A2-L09 [LOW]: Typing style inconsistency: 'Optional[X]' vs 'X \
- P1-A2-L15 [LOW]: 'RegimeClassifierV2' accesses private '_compute_trend_score' and '_config' of V1
- DEF-091 [MEDIUM]: V1/V2 RegimeClassifier private-attribute access + VIXDataService private attrs
- DEF-092 [LOW]: Unused Protocol types (4 classes, signatures mismatched)
- P1-A2-M01 [MEDIUM]: Risk Manager class docstring and public-method surface are stale
- P1-A2-M02 [MEDIUM]: Check numbering gap
- P1-A2-L13 [LOW]: 'PRIORITY_BY_WIN_RATE' duplicate-stock policy is documented-as-V1-simplified but hard-rejects like 'BLOCK_ALL'
- P1-G1-C01 [CRITICAL]: Post-close circuit-breaker trigger path is uncovered
- P1-G1-C02 [CRITICAL]: Two rejection paths in position-sizing are uncovered
- P1-G1-M08 [MEDIUM]: 'run_integrity_check()' branch 'if account
- P1-A2-L02 [LOW]: "FIFO delivery per subscriber" guarantee is weaker than advertised
- P1-A2-L03 [LOW]: 'EventBus
- P1-A2-L06 [LOW]: 'subscribe()' type parameter 'T' is unused
- P1-A2-L14 [LOW]: 'CircuitBreakerEvent
- P1-D1-M07 [MEDIUM]: 'SignalRejectedEvent
- DEF-104 [MEDIUM]: Dual ExitReason enums must be kept in sync
- P1-G1-M06 [MEDIUM]: DEF-163 date-decay root cause identified
- P1-G2-M01 [MEDIUM]: 'test_history_store_migration' is NOT an xdist race — it is a UTC-vs-ET timezone boundary bug
- P1-G2-L01 [LOW]: '_make_vector()' hardcodes 'computed_at=datetime(2026, 3, 26, 14, 0, 0, tzinfo=UTC)' as default — confirms G1 M6
- P1-A2-M04 [MEDIUM]: Regime classification logic duplicated between 'run_pre_market()' and 'reclassify_regime()'
- P1-A2-L08 [LOW]: '_latest_regime_vector: object \
- P1-A2-M09 [MEDIUM]: PF-01 + PF-02 confirmed dead
- P1-A2-M05 [MEDIUM]: Partial re-export surface
- P1-A2-L05 [LOW]: 'FixedClock
- P1-A2-M06 [MEDIUM]: Sprint-31A strategy configs appended after the loader section divider
- P1-A2-L11 [LOW]: Weekly reconciliation is a stub
- P1-A2-L10 [LOW]: Naive 'datetime
- P1-A2-L12 [LOW]: 'import asyncio' after third-party imports
- P1-A2-M08 [MEDIUM]: SQLite table name drift
- P1-A2-L04 [LOW]: 'SyncEventBus' silently omits subscribe/unsubscribe debug logs present in 'EventBus'
- P1-C2-2 [MEDIUM]: Standalone 'vix_regime
- P1-A2-M03 [MEDIUM]: Event-type inventory drift
- DEF-163 [LOW]: Timezone-boundary bugs + hardcoded Vitest dates (NOT date-decay)
- P1-G2-M06 [MEDIUM]: 11+ tests mutate RiskManager private attributes ('rm

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Tier 2 Review (REQUIRED after commit — follows `workflow/claude/skills/review.md`)

After the commit above is pushed, invoke the Tier 2 reviewer in this same
session:

```
@reviewer

Please follow workflow/claude/skills/review.md to review the changes from
this session.

Inputs:
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-05-core-orchestrator-risk-regime)
- **Close-out report:** the ---BEGIN-CLOSE-OUT--- block produced before commit
- **Regression checklist:** the 8 campaign-level checks embedded in the close-out
- **Escalation criteria:** trigger ESCALATE verdict if ANY of:
  - any CRITICAL severity finding
  - pytest net delta < 0
  - scope boundary violation (file outside declared Scope modified)
  - different test failure surfaces (not the expected DEF-150 flake)
  - Rule-4 sensitive file touched without authorization
  - audit-report back-annotation missing or incorrect
  - (FIX-01 only) Step 1G fingerprint checkpoint failed before pipeline edits proceeded

Produce the ---BEGIN-REVIEW--- block with verdict CLEAR / CONCERNS /
ESCALATE, followed by the json:structured-verdict JSON appendix. Do NOT
modify any code.
```

The reviewer produces its report in the format specified by review.md
(fenced markdown block, `---BEGIN-REVIEW---` markers, structured JSON
verdict). The operator copies this block into the Work Journal conversation
alongside the close-out.

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** (for Work Journal paste)
2. **The review markdown block** (for Work Journal paste)
3. **A one-line summary:** `Session FIX-05 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-05-core-orchestrator-risk-regime**`
