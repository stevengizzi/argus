# Fix Session FIX-19-strategies: argus/strategies — pattern modules + base strategy

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 20
**Files touched:** `Throughout — scoring weights`, `[config/strategies/*.yaml](config/strategies/) — 9 files`, `argus/core/config.py`, `argus/strategies/afternoon_momentum.py`, `argus/strategies/base_strategy.py`, `argus/strategies/orb_base.py`, `argus/strategies/pattern_strategy.py`, `argus/strategies/patterns/base.py`, `argus/strategies/patterns/flat_top_breakout.py`, `argus/strategies/patterns/premarket_high_break.py`, `argus/strategies/patterns/vwap_bounce.py`, `argus/strategies/vwap_reclaim.py`, `config/strategies/abcd.yaml`
**Safety tag:** `weekend-only`
**Theme:** Strategy-layer findings: PatternModule ABC, PatternBasedStrategy wrapper, individual pattern files, BaseStrategy telemetry wiring (DEF-138 scope), strategy YAMLs.

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
marker (`audit(FIX-19): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/strategies/base_strategy.py`: 4 findings
- `argus/strategies/patterns/vwap_bounce.py`: 3 findings
- `argus/strategies/orb_base.py`: 2 findings
- `argus/strategies/vwap_reclaim.py`: 2 findings
- `Throughout — scoring weights`: 1 finding
- `[config/strategies/*.yaml](config/strategies/) — 9 files`: 1 finding
- `argus/core/config.py`: 1 finding
- `argus/strategies/afternoon_momentum.py`: 1 finding
- `argus/strategies/pattern_strategy.py`: 1 finding
- `argus/strategies/patterns/base.py`: 1 finding
- `argus/strategies/patterns/flat_top_breakout.py`: 1 finding
- `argus/strategies/patterns/premarket_high_break.py`: 1 finding
- `config/strategies/abcd.yaml`: 1 finding

## Findings to Fix

### Finding 1: `P1-B-M02` [MEDIUM]

**File/line:** [argus/strategies/base_strategy.py:323-388](argus/strategies/base_strategy.py#L323-L388) — infra exists; callers missing in all 15 strategies
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **DEF-138 scope**: `_track_symbol_evaluated`, `_track_signal_generated`, `_track_signal_rejected`, and `_maybe_log_window_summary` are defined in BaseStrategy and reset in `reset_daily_state()`, but grep shows **zero call sites outside BaseStrategy itself**. All 15 strategies need wire-up: ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, Red-to-Green, PatternBasedStrategy (covers all 10 pattern strategies in one place).

**Impact:**

> Window-summary log line (symbols evaluated / signals generated / rejections by reason) never emits — operators have no single-line view of strategy activity per day. Observability gap.

**Suggested fix:**

> One wire-up in `PatternBasedStrategy.on_candle()` covers all 10 patterns. Five per-file wire-ups for the standalone strategies. See dedicated "DEF-138 Remediation Scope" section below.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 2: `P1-B-L01` [LOW]

**File/line:** [argus/strategies/base_strategy.py:43-47](argus/strategies/base_strategy.py#L43-L47)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `StrategyMode` StrEnum is defined but has zero import sites under `argus/` (only base_strategy.py itself). `StrategyConfig.mode` at `config.py:753` is a plain `str` with a comment "StrategyMode", not the actual enum. Routing in `main.py:1704` compares the raw string.

**Impact:**

> Dead enum. Slight type-safety regression because `mode` isn't validated against enum values.

**Suggested fix:**

> Either (a) import and type the field as `mode: StrategyMode = StrategyMode.LIVE`, or (b) delete the enum. Option (a) gives validation; option (b) is less churn.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 3: `P1-B-L02` [LOW]

**File/line:** [argus/strategies/base_strategy.py:142-156](argus/strategies/base_strategy.py#L142-L156) + all overrides
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `calculate_position_size()` is an abstract method on BaseStrategy, overridden in all 6 strategy base/subclass files, but **only called from tests** (22 test references, zero production call sites). Quality Engine supplanted it via `share_count=0` + `DynamicPositionSizer` (Sprint 24 S6a).

**Impact:**

> Dead abstract interface surface. Mild maintenance tax — every new strategy implements a method that never runs in production.

**Suggested fix:**

> Mark `@abstractmethod` → plain concrete method returning 0 as default, document the legacy role, and move the real logic used in tests into test fixtures or a separate `LegacySizer` helper. Or preserve for the legacy-sizing bypass in `main.py:1718-1735` if that path is still supported.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 4: `P1-B-L03` [LOW]

**File/line:** [argus/strategies/base_strategy.py:134-140](argus/strategies/base_strategy.py#L134-L140) + `get_scanner_criteria` implementations
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `get_scanner_criteria()` is only invoked from `tests/test_integration_sprint3.py:164`. Production scanning flows through `config/universe_filters/*.yaml` via Universe Manager (Sprint 23+).

**Impact:**

> Dead interface, same class as L2.

**Suggested fix:**

> Same as L2 — demote from abstract to concrete default.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 5: `P1-B-M01` [MEDIUM]

**File/line:** [argus/strategies/patterns/vwap_bounce.py:104,180](argus/strategies/patterns/vwap_bounce.py#L104) + [argus/strategies/pattern_strategy.py:508-516](argus/strategies/pattern_strategy.py#L508-L516)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `VwapBouncePattern._signal_counts: dict[str, int]` accumulates per-symbol counts on the pattern instance. `reset_session_state()` exists on the pattern but is never called from `PatternBasedStrategy.reset_daily_state()`. Since ARGUS runs continuously across trading days, `_signal_counts` monotonically grows. After day 1, every symbol that hit `max_signals_per_symbol` (default 3) is permanently blocked.

**Impact:**

> Silent suppression of VWAP Bounce signals on previously-capped symbols on day N+1. Currently masked because VWAP Bounce is fresh (low symbol exposure). Will bite silently as shadow-mode data accumulates.

**Suggested fix:**

> Call `self._pattern.reset_session_state()` from `PatternBasedStrategy.reset_daily_state()` guarded by `hasattr(self._pattern, "reset_session_state")`. Add a test asserting counts reset.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 6: `P1-B-M08` [MEDIUM]

**File/line:** [argus/strategies/patterns/vwap_bounce.py:49-54, 104, 157, 170, 180](argus/strategies/patterns/vwap_bounce.py#L49)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `VwapBouncePattern` stores session state (`_signal_counts`) inside the pattern module, violating the stated invariant ("Patterns are pure detection logic" — `argus/strategies/patterns/base.py:96-105` and `pattern_strategy.py:7`). Every other pattern is stateless.

**Impact:**

> Architectural inconsistency. Makes test fixtures less reusable and couples pattern instance to session lifecycle. Related to M1 (the leak bug).

**Suggested fix:**

> Move the per-session cap into `PatternBasedStrategy` using `self._candle_store`/symbol context, or formalize a `SessionStatefulPattern` mixin if other patterns need the same hook. Not urgent as long as M1 is fixed.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 7: `P1-B-C03` [COSMETIC]

**File/line:** [argus/strategies/patterns/vwap_bounce.py:119](argus/strategies/patterns/vwap_bounce.py#L119)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `lookback_bars = 50` comment explains the arithmetic (30+5+5+3+headroom). Excellent. Other patterns with derived `lookback_bars` values would benefit from similar inline derivations.

**Impact:**

> Positive — replicate elsewhere.

**Suggested fix:**

> Add derivations where `lookback_bars` is a magic number.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 8: `P1-B-L08` [LOW]

**File/line:** [argus/strategies/orb_base.py:367-504](argus/strategies/orb_base.py#L367-L504)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> "Identical conditions in ORB-Breakout and ORB-Scalp" observation confirmed — and is correct by design. Both inherit `_check_breakout_conditions()` from `OrbBaseStrategy`. This is not a finding; logging it explicitly so the audit trail confirms the observation rather than leaving it ambiguous.

**Impact:**

> None. Correct DEC-120 extraction.

**Suggested fix:**

> No action.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-19-strategies**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-19-strategies**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 9: `P1-B-C02` [COSMETIC]

**File/line:** [argus/strategies/orb_base.py:388-401](argus/strategies/orb_base.py#L388-L401)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> In `_check_breakout_conditions`, the first failure records `"conditions_passed": 0` with reason `"No breakout"`. The structural check (close > OR high) is the first evaluated; if it fails, 0 conditions passed, which is accurate but reads awkwardly in telemetry.

**Impact:**

> Cosmetic.

**Suggested fix:**

> No change needed.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-19-strategies**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-19-strategies**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 10: `P1-B-M05` [MEDIUM]

**File/line:** [argus/strategies/vwap_reclaim.py:199-205](argus/strategies/vwap_reclaim.py#L199-L205)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `if not self._is_in_entry_window(event):` records a `TIME_WINDOW_CHECK` FAIL evaluation, but there is **no `return None`** — the code falls through into `_process_state_machine()`. Comparison with line 394-409 shows the actual entry gate lives inside `_check_reclaim_entry()`, so the behavior is intentional (state machine must track pullback progression before the entry window opens). However, the FAIL event fires on every out-of-window candle, producing telemetry noise.

**Impact:**

> `evaluation.db` is flooded with FAIL events that aren't semantically failures — they're "state machine processing, not evaluating entry." Matches the DEF-157 write-volume concern.

**Suggested fix:**

> Either suppress the FAIL (emit `INFO` with a different reason like "State machine still accumulating") or gate the record on `state.state == VwapState.BELOW_VWAP`. Add a comment at the fall-through explaining why no `return`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 11: `P1-B-M07` [MEDIUM]

**File/line:** [argus/strategies/vwap_reclaim.py:732-793](argus/strategies/vwap_reclaim.py#L732-L793)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> VWAP Reclaim's `_build_signal` also does not call `_has_zero_r`. Same rationale as M6.

**Impact:**

> Same as M6.

**Suggested fix:**

> Same as M6.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 12: `P1-B-C04` [COSMETIC]

**File/line:** Throughout — scoring weights
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Patterns vary: 30/30/25/15 (Bull Flag, Flat-Top, HOD Break post-detect), 35/25/20/20 (ABCD), 30/25/25/20 (Micro Pullback, Narrow Range Breakout, VWAP Bounce, Dip-and-Rip), 30/30/20/20 (Gap-and-Go). Project-knowledge memory claims "30/25/25/20" as a convention, but reality is divergent by design.

**Impact:**

> None — different patterns warrant different weightings. Update project-knowledge memory to stop implying a single convention.

**Suggested fix:**

> Reconcile claim in memory.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 13: `P1-B-L06` [LOW]

**File/line:** [config/strategies/*.yaml](config/strategies/) — 9 files
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Only `abcd.yaml` sets `pattern_class: "ABCDPattern"` explicitly. The other 9 pattern configs rely on `factory._resolve_pattern_name()`'s implicit `Config → Pattern` suffix rule at [argus/strategies/patterns/factory.py:286-292](argus/strategies/patterns/factory.py#L286-L292).

**Impact:**

> Minor style inconsistency; one convention per file would read cleaner. Current state works but creates a special case in code review.

**Suggested fix:**

> Either add `pattern_class:` to the other 9 or remove it from `abcd.yaml`. Removing is less churn.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 14: `P1-B-M03` [MEDIUM]

**File/line:** [argus/core/config.py:1216-1223](argus/core/config.py#L1216-L1223) + all `get_market_conditions_filter()` implementations
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `StrategyConfig.allowed_regimes` is a Pydantic YAML field, but **no strategy reads it**. Orchestrator calls `strategy.get_market_conditions_filter().allowed_regimes` at [argus/core/orchestrator.py:407-408](argus/core/orchestrator.py#L407-L408) and [:788-789](argus/core/orchestrator.py#L788-L789), and every strategy's `get_market_conditions_filter()` returns a hardcoded Python list. `config/strategies/abcd.yaml:20-24` is the only YAML that sets the field — and the setting has no effect.

**Impact:**

> Dead config surface. Operator-facing illusion of per-strategy regime tuning that doesn't work. Also, the Pydantic default (`["bullish_trending","bearish_trending","neutral","high_volatility"]`) uses `"neutral"` which is not a valid `MarketRegime` enum value (enum uses `"range_bound"`) — default is silently wrong.

**Suggested fix:**

> Either (a) have `get_market_conditions_filter()` read `self._config.allowed_regimes` and correct the default to `"range_bound"`, or (b) remove the field from `StrategyConfig`. Option (a) preferred — restores YAML-level control.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 15: `P1-B-M06` [MEDIUM]

**File/line:** [argus/strategies/afternoon_momentum.py:1015-1034](argus/strategies/afternoon_momentum.py#L1015-L1034)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Afternoon Momentum's `_build_breakout_signal` never calls `self._has_zero_r(...)` before returning the `SignalEvent`. Stop placement uses `midday_low * (1 - stop_buffer_pct)`, so `entry == target` is implausible in practice, but the guard exists for edge cases (DEC-???/Sprint 24) and every other strategy applies it.

**Impact:**

> Low probability of silent zero-R trade but inconsistent with ORB/R2G/PatternBasedStrategy. If a pathological symbol produces `entry ≈ t1`, the signal slips through.

**Suggested fix:**

> Add the guard after target calculation, consistent with ORB and R2G.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 16: `P1-B-M04` [MEDIUM]

**File/line:** [argus/strategies/pattern_strategy.py:497-506](argus/strategies/pattern_strategy.py#L497-L506)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `PatternBasedStrategy.get_market_conditions_filter()` hardcodes `["bullish_trending", "bearish_trending", "range_bound"]` — **missing `"high_volatility"`** that the 4 other standalone strategies include. This silently disables all 10 pattern strategies during high-volatility regimes, regardless of operator intent.

**Impact:**

> 10 of the 15 strategies sit out high-volatility regimes without an operator opt-in. May be the product of copy-paste from R2G (which also omits `high_volatility`) rather than a deliberate risk choice.

**Suggested fix:**

> Reconcile with M3 — honor `self._config.allowed_regimes` and set a sensible default that matches the 4 standalone strategies. Document the final list in the spec.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 17: `P1-B-C01` [COSMETIC]

**File/line:** [argus/strategies/patterns/base.py:161-172](argus/strategies/patterns/base.py#L161-L172)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `min_detection_bars` default body distinguishes deque capacity from detection eligibility. Only 3 of 10 patterns (`narrow_range_breakout`, `premarket_high_break`, `vwap_bounce`) override. The remaining 7 don't document that they intentionally equate the two.

**Impact:**

> Reader has to grep to discover which patterns need large history vs large detection windows.

**Suggested fix:**

> Add a one-line note in each of the 7 patterns' docstrings: "lookback_bars == min_detection_bars (default)." Or skip — the default is the intuitive case.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 18: `P1-B-L04` [LOW]

**File/line:** [argus/strategies/patterns/flat_top_breakout.py:256-265](argus/strategies/patterns/flat_top_breakout.py#L256-L265) vs [:294-310](argus/strategies/patterns/flat_top_breakout.py#L294-L310)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> The private `_confidence_score()` (used during `detect()`) weights components 25/25/25/25. The public `score()` weights 30/30/25/15. Two views of quality for the same pattern.

**Impact:**

> Confusing — a detected pattern's `confidence` and `score()` disagree on which components matter.

**Suggested fix:**

> Either align both weightings or document the divergence in the class docstring.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 19: `P1-B-L07` [LOW]

**File/line:** [argus/strategies/patterns/premarket_high_break.py](argus/strategies/patterns/premarket_high_break.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Pattern docstring does not document scoring weights; every other pattern's `score()` docstring carries the `- Component (weight): description` shape.

**Impact:**

> Inconsistency.

**Suggested fix:**

> Add the 4-component weight list to the `score()` docstring.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

### Finding 20: `P1-B-L05` [LOW]

**File/line:** [config/strategies/abcd.yaml:20-24](config/strategies/abcd.yaml#L20-L24)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Sole YAML that sets `allowed_regimes`. Value is `[bullish_trending, bearish_trending, neutral, high_volatility]` — but **`"neutral"` is not a valid `MarketRegime`** (see `argus/core/regime.py:57-60`). Silently ignored today because M3's override masks the field entirely.

**Impact:**

> When M3 is fixed, this YAML will throw or silently skip regime matching.

**Suggested fix:**

> Change `neutral` → `range_bound`. Also prompts a review of any other YAML that might have been authored against the wrong default.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-19-strategies**`.

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
| ... | ~~description~~ **RESOLVED FIX-19-strategies** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-19-strategies**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-19): strategies/ cleanup

Addresses audit findings:
- P1-B-M02 [MEDIUM]: DEF-138 scope: '_track_symbol_evaluated', '_track_signal_generated', '_track_signal_rejected', and '_maybe_log_window_su
- P1-B-L01 [LOW]: 'StrategyMode' StrEnum is defined but has zero import sites under 'argus/' (only base_strategy
- P1-B-L02 [LOW]: 'calculate_position_size()' is an abstract method on BaseStrategy, overridden in all 6 strategy base/subclass files, but
- P1-B-L03 [LOW]: 'get_scanner_criteria()' is only invoked from 'tests/test_integration_sprint3
- P1-B-M01 [MEDIUM]: 'VwapBouncePattern
- P1-B-M08 [MEDIUM]: 'VwapBouncePattern' stores session state ('_signal_counts') inside the pattern module, violating the stated invariant ("
- P1-B-C03 [COSMETIC]: 'lookback_bars = 50' comment explains the arithmetic (30+5+5+3+headroom)
- P1-B-L08 [LOW]: "Identical conditions in ORB-Breakout and ORB-Scalp" observation confirmed — and is correct by design
- P1-B-C02 [COSMETIC]: In '_check_breakout_conditions', the first failure records '"conditions_passed": 0' with reason '"No breakout"'
- P1-B-M05 [MEDIUM]: 'if not self
- P1-B-M07 [MEDIUM]: VWAP Reclaim's '_build_signal' also does not call '_has_zero_r'
- P1-B-C04 [COSMETIC]: Patterns vary: 30/30/25/15 (Bull Flag, Flat-Top, HOD Break post-detect), 35/25/20/20 (ABCD), 30/25/25/20 (Micro Pullback
- P1-B-L06 [LOW]: Only 'abcd
- P1-B-M03 [MEDIUM]: 'StrategyConfig
- P1-B-M06 [MEDIUM]: Afternoon Momentum's '_build_breakout_signal' never calls 'self
- P1-B-M04 [MEDIUM]: 'PatternBasedStrategy
- P1-B-C01 [COSMETIC]: 'min_detection_bars' default body distinguishes deque capacity from detection eligibility
- P1-B-L04 [LOW]: The private '_confidence_score()' (used during 'detect()') weights components 25/25/25/25
- P1-B-L07 [LOW]: Pattern docstring does not document scoring weights; every other pattern's 'score()' docstring carries the '- Component 
- P1-B-L05 [LOW]: Sole YAML that sets 'allowed_regimes'

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-19-strategies**`
