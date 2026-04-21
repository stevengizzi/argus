# Fix Session FIX-08-intelligence-experiments-learning: argus/intelligence — experiments + learning loop

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 18
**Files touched:** `argus/intelligence/experiments/config.py`, `argus/intelligence/experiments/promotion.py`, `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/learning/__init__.py`, `argus/intelligence/learning/config_proposal_manager.py`, `argus/intelligence/learning/learning_service.py`, `argus/intelligence/learning/models.py`, `argus/intelligence/learning/threshold_analyzer.py`, `argus/ui/src/features/learning/LearningInsightsPanel.ts`
**Safety tag:** `weekend-only`
**Theme:** Experiment pipeline (variant spawner, runner, promotion evaluator, store) and learning loop (outcome collector, weight analyzer, config proposal manager) findings.

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
marker (`audit(FIX-08): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/intelligence/experiments/runner.py`: 6 findings
- `argus/intelligence/experiments/promotion.py`: 2 findings
- `argus/intelligence/experiments/store.py`: 2 findings
- `argus/intelligence/learning/learning_service.py`: 2 findings
- `argus/intelligence/experiments/config.py`: 1 finding
- `argus/intelligence/learning/__init__.py`: 1 finding
- `argus/intelligence/learning/config_proposal_manager.py`: 1 finding
- `argus/intelligence/learning/models.py`: 1 finding
- `argus/intelligence/learning/threshold_analyzer.py`: 1 finding
- `argus/ui/src/features/learning/LearningInsightsPanel.ts`: 1 finding

## Findings to Fix

### Finding 1: `P1-D2-M02` [MEDIUM]

**File/line:** [runner.py:878-894](argus/intelligence/experiments/runner.py#L878-L894) vs [factory.py:206-259](argus/strategies/patterns/factory.py#L206-L259)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Two different fingerprint schemes coexist. Runner hashes `{"detection_params": {...}, "exit_overrides": {...}}`; factory (used by spawner) hashes `{"detection": {...}, "exit": {...}}`. Same semantic content, **different SHA-256 output**. For the detection-only path both produce identical hashes (single-level dict, same keys), but as soon as `exit_sweep_params` are introduced in a sweep, the grid-sweep fingerprint for a config will NOT match the spawner-produced fingerprint for the identical variant.

**Impact:**

> Dedup between grid-sweep experiments and manual variants breaks when exit overrides are present. `get_by_fingerprint` would fail to find the manual variant's fingerprint in a sweep-result table and vice versa. Currently latent (no variants use exit_overrides, `exit_sweep_params: null`).

**Suggested fix:**

> Unify both paths on `factory.compute_parameter_fingerprint`. Runner should build the canonical dict via the factory helper rather than ad-hoc.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 2: `P1-D2-L03` [LOW]

**File/line:** [runner.py:468-520](argus/intelligence/experiments/runner.py#L468-L520)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `workers > 1` branch catches `KeyboardInterrupt` and cleanly shuts down the executor with `cancel_futures=True`. A broad `Exception` raised inside `asyncio.as_completed(...)` (e.g. `aiosqlite.OperationalError` during `save_experiment`) would propagate past the try/else without `executor.shutdown(wait=False)`, leaving worker subprocesses running until the asyncio event loop exits.

**Impact:**

> Potential orphan subprocess on rare write-path exceptions during parallel sweeps. Not triggered during normal operation (fire-and-forget store swallows writes).

**Suggested fix:**

> Convert the `else: executor.shutdown(wait=True)` into a `finally:` that always runs. Or wrap the executor in a `with ProcessPoolExecutor(...) as executor:` context manager (which handles shutdown on any exit path).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 3: `P1-D2-L06` [LOW]

**File/line:** [experiments/runner.py:394-520](argus/intelligence/experiments/runner.py#L394-L520) vs [L525-L640](argus/intelligence/experiments/runner.py#L525-L640)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Parallel and sequential sweep paths have significant code duplication — both handle unsupported-pattern FAILED records, both build `ExperimentRecord` with the same field set, both call `save_experiment` in the same shape. Two places to update if the record shape evolves.

**Impact:**

> Refactor risk, not a bug.

**Suggested fix:**

> Extract a `_build_and_save_record(pattern_name, params, fingerprint, result, status, strategy_type, ...)` helper used by both paths.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 4: `P1-D2-C01` [COSMETIC]

**File/line:** [runner.py:91-103](argus/intelligence/experiments/runner.py#L91-L103)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_run_single_backtest` does heavy local aliasing (`_asyncio`, `_date`, `_Path`, `_BEConfig`, `_StrategyType`, `_BacktestEngine`) with `# noqa: PLC0415`. The comment in the exception fallback explains why (pickle/subprocess loading), but the aliasing style is noisy and duplicates the module-level imports that already exist.

**Impact:**

> Readability only.

**Suggested fix:**

> Remove the aliasing, keep the explanatory comment, and let the noqa apply to the function import block rather than every statement.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 5: `P1-D2-C05` [COSMETIC]

**File/line:** [runner.py:244](argus/intelligence/experiments/runner.py#L244)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `combos = list(itertools.product(*[param_ranges[k] for k in keys]))` materialises the entire cartesian product twice (once as combos, once in the list comprehension that follows). For large grids (near `_GRID_CAP = 500`) this is a minor memory blip.

**Impact:**

> Negligible.

**Suggested fix:**

> Iterate directly: `detection_grid = [dict(zip(keys, combo)) for combo in itertools.product(*(param_ranges[k] for k in keys))]`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 6: `DEF-123` [COSMETIC]

**File/line:** argus/intelligence/experiments/runner.py
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> build_parameter_grid() float accumulation

**Impact:**

> Cosmetic — already mitigated by round(v,6) + dedup

**Suggested fix:**

> Use numpy.arange or integer-stepping

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 7: `P1-D2-L02` [LOW]

**File/line:** [promotion.py:365-413](argus/intelligence/experiments/promotion.py#L365-L413)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_build_result_from_shadow` and `_count_shadow_trading_days` issue **two independent** `counterfactual_store.query(..., limit=1000)` calls per variant per pass. If a strategy has >1000 shadow positions, the two queries return the same 1000 rows (DESC order), so day-count and r_multiple-count remain consistent. But the second query is redundant I/O.

**Impact:**

> Minor DB I/O waste during promotion evaluation (N variants × 2 queries instead of N). No correctness issue today.

**Suggested fix:**

> Query once, compute both R-multiple list and unique day count from the returned rows. Avoids the second round-trip and future-proofs against the two limits ever diverging.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 8: `P1-D2-C04` [COSMETIC]

**File/line:** [promotion.py:118-128](argus/intelligence/experiments/promotion.py#L118-L128)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_evaluate_for_promotion` hand-constructs a new `VariantDefinition` with `mode="live"` to append to the in-memory `live_variants` list after each promotion, duplicating every field. `VariantDefinition` is frozen, but `dataclasses.replace(shadow_variant, mode="live")` would be one line.

**Impact:**

> Readability.

**Suggested fix:**

> Use `dataclasses.replace(shadow_variant, mode="live")`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 9: `P1-D2-L05` [LOW]

**File/line:** [experiments/store.py:765](argus/intelligence/experiments/store.py#L765)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> `_row_to_experiment` coerces `int(row["shadow_trades"])` directly. Column is `NOT NULL DEFAULT 0` in the DDL, so new rows are safe. Pre-DDL rows (none exist in production) would raise.

**Impact:**

> Theoretical only — no schema drift risk in the current DB.

**Suggested fix:**

> No action needed.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-08-intelligence-experiments-learning**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-08-intelligence-experiments-learning**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 10: `P1-D2-C06` [COSMETIC]

**File/line:** [experiments/store.py:150-157](argus/intelligence/experiments/store.py#L150-L157)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Idempotent `ALTER TABLE variants ADD COLUMN exit_overrides TEXT` swallows a bare `except Exception: pass`. Works in practice (SQLite raises on duplicate column), but hides other failure modes (permissions, disk full).

**Impact:**

> Reviewability only.

**Suggested fix:**

> Narrow to `except aiosqlite.OperationalError:` with a sanity check on the error message.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 11: `P1-D2-L04` [LOW]

**File/line:** [learning_service.py:93-104](argus/intelligence/learning/learning_service.py#L93-L104)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> `register_auto_trigger` subscribes to `SessionEndEvent` with no teardown path — no `unsubscribe` call at shutdown. In practice both `LearningService` and `EventBus` live for the process lifetime, so this is not a leak today. Flag for visibility only; if `LearningService` ever becomes per-session (e.g. rebuilt on config reload), the subscription leaks across reloads.

**Impact:**

> No active bug.

**Suggested fix:**

> If `LearningService` lifecycle ever changes, add an explicit unsubscribe in a `shutdown()` method.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-08-intelligence-experiments-learning**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-08-intelligence-experiments-learning**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 12: `P1-D2-L07` [LOW]

**File/line:** [learning_service.py:499](argus/intelligence/learning/learning_service.py#L499)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `rationale` f-string includes `rec.correlation_trade_source or rec.correlation_counterfactual_source` — if both are `None` this prints `None`. Rationale is human-facing only; cosmetic.

**Impact:**

> Rationale text on some proposals may show "correlation=None".

**Suggested fix:**

> Format with a defensive `correlation_trade_source or correlation_counterfactual_source or 0.0`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 13: `P1-D2-C02` [COSMETIC]

**File/line:** [config.py:70,80](argus/intelligence/experiments/config.py#L70-L80)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `ExperimentConfig.variants` is typed `dict[str, list[dict[str, Any]]]` — accepts any shape. Each variant_def is later validated inside the spawner, but invalid top-level keys (e.g. typo'd `varients:` → entire dict ignored) pass Pydantic because `variants` is the catch-all. `extra="forbid"` helps on keys, not on value shape.

**Impact:**

> Low-visibility config typos.

**Suggested fix:**

> Define a `VariantConfig` Pydantic model (`variant_id: str`, `mode: Literal["live","shadow"]`, `params: dict[str, Any]`, `exit_overrides: dict[str, float] \

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 14: `P1-D2-C03` [COSMETIC]

**File/line:** [learning/__init__.py:1-42](argus/intelligence/learning/__init__.py#L1-L42)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> `__init__.py` exports stores/service/models but **not** the three analyzers (`WeightAnalyzer`, `ThresholdAnalyzer`, `CorrelationAnalyzer`). Consumers (main.py, tests) import them by module path directly. Minor asymmetry.

**Impact:**

> Readability.

**Suggested fix:**

> Add analyzers to `__all__` and the import list, or document why they're not public API.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-08-intelligence-experiments-learning**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-08-intelligence-experiments-learning**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 15: `P1-D2-M05` [MEDIUM]

**File/line:** [config_proposal_manager.py:186-194, 424-452](argus/intelligence/learning/config_proposal_manager.py#L186-L194)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_redistribute_weights` proportionally adjusts non-changed weight dimensions to maintain sum-to-1.0, but the **redistribution deltas are never recorded** in `config_change_history`. Only the explicitly-changed dimension is persisted via `record_change`. `get_cumulative_drift(dim, window)` therefore undercounts drift on redistributed dimensions.

**Impact:**

> Cumulative drift guard is evadable: repeatedly promote dim A up while dims B/C/D/E silently drift down via redistribution, and the guard never trips for B/C/D/E. Over months this could push the weight vector far from the initial anchor without operator awareness.

**Suggested fix:**

> After applying each approved proposal, compute the actual delta for every redistributed dimension (compare pre- vs post-redistribution values) and call `record_change(..., source="learning_loop_redistribution", proposal_id=...)` for each. Drift guard then sees the full picture.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 16: `P1-D2-L01` [LOW]

**File/line:** [learning/models.py:409-423](argus/intelligence/learning/models.py#L409-L423)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_convert_datetimes` in `LearningReport.to_dict()` converts `isinstance(val, datetime)` only. A `date` (not `datetime`) field would slip through and cause `json.dumps` to fail at `learning_store.py:124` (no `default=str` there).

**Impact:**

> Latent serialization crash if a future `LearningReport` / nested dataclass field uses `date`. No current failure — present dataclasses use `datetime` only. Same failure class as DEF-151.

**Suggested fix:**

> Either widen the guard to `isinstance(val, (date, datetime))` (keep `datetime` first so `.isoformat()` picks the richer branch), or add `default=str` to the `json.dumps` call in `learning_store.save_report`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 17: `P1-D2-M04` [MEDIUM]

**File/line:** [threshold_analyzer.py:115-151](argus/intelligence/learning/threshold_analyzer.py#L115-L151), [learning_service.py:509-532](argus/intelligence/learning/learning_service.py#L509-L532)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `ThresholdAnalyzer._analyze_grade` can append **both** a "lower" and a "raise" `ThresholdRecommendation` for the same grade. `missed_opportunity_rate + correct_rejection_rate = 1.0` always, so when `missed > 0.50` both triggers fire. `_generate_proposals` then emits two `ConfigProposal` rows with the same `field_path` (`thresholds.<grade>`), one with value `current - 5.0` and one with `current + 5.0`. If an operator approves both, `apply_pending` applies them sequentially — second overwrites first and the drift guard sees twice the delta.

**Impact:**

> Confusing operator UX (two contradictory proposals to review), and a subtle bug if both are approved.

**Suggested fix:**

> Either (a) pick the stronger signal and emit exactly one recommendation per grade (e.g. `raise` when correct < 0.50, else `lower` when missed > 0.40); or (b) enforce at `apply_pending` that only one pending `thresholds.<grade>` proposal survives. Option (a) is cleaner.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

### Finding 18: `DEF-107` [COSMETIC]

**File/line:** argus/ui/src/features/learning/LearningInsightsPanel.tsx:388
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Unused raiseRec destructured variable

**Impact:**

> Harmless cosmetic dead code

**Suggested fix:**

> Delete the destructured variable

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-08-intelligence-experiments-learning**`.

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

### Vitest (frontend paths touched)

```bash
cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -10
# Record PASS count: __________
# Net delta: __________ (MUST be >= 0)
```

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-08-intelligence-experiments-learning** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-08-intelligence-experiments-learning**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-08): experiments + learning loop cleanup

Addresses audit findings:
- P1-D2-M02 [MEDIUM]: Two different fingerprint schemes coexist
- P1-D2-L03 [LOW]: 'workers > 1' branch catches 'KeyboardInterrupt' and cleanly shuts down the executor with 'cancel_futures=True'
- P1-D2-L06 [LOW]: Parallel and sequential sweep paths have significant code duplication — both handle unsupported-pattern FAILED records, 
- P1-D2-C01 [COSMETIC]: '_run_single_backtest' does heavy local aliasing ('_asyncio', '_date', '_Path', '_BEConfig', '_StrategyType', '_Backtest
- P1-D2-C05 [COSMETIC]: 'combos = list(itertools
- DEF-123 [COSMETIC]: build_parameter_grid() float accumulation
- P1-D2-L02 [LOW]: '_build_result_from_shadow' and '_count_shadow_trading_days' issue two independent 'counterfactual_store
- P1-D2-C04 [COSMETIC]: '_evaluate_for_promotion' hand-constructs a new 'VariantDefinition' with 'mode="live"' to append to the in-memory 'live_
- P1-D2-L05 [LOW]: '_row_to_experiment' coerces 'int(row["shadow_trades"])' directly
- P1-D2-C06 [COSMETIC]: Idempotent 'ALTER TABLE variants ADD COLUMN exit_overrides TEXT' swallows a bare 'except Exception: pass'
- P1-D2-L04 [LOW]: 'register_auto_trigger' subscribes to 'SessionEndEvent' with no teardown path — no 'unsubscribe' call at shutdown
- P1-D2-L07 [LOW]: 'rationale' f-string includes 'rec
- P1-D2-C02 [COSMETIC]: 'ExperimentConfig
- P1-D2-C03 [COSMETIC]: '__init__
- P1-D2-M05 [MEDIUM]: '_redistribute_weights' proportionally adjusts non-changed weight dimensions to maintain sum-to-1
- P1-D2-L01 [LOW]: '_convert_datetimes' in 'LearningReport
- P1-D2-M04 [MEDIUM]: 'ThresholdAnalyzer
- DEF-107 [COSMETIC]: Unused raiseRec destructured variable

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-08-intelligence-experiments-learning**`
- [ ] Vitest suite net delta >= 0
