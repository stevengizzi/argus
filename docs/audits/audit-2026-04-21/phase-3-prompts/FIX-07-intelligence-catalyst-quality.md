# Fix Session FIX-07-intelligence-catalyst-quality: argus/intelligence — catalysts, quality engine, counterfactual

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 23
**Files touched:** `argus/api/routes/counterfactual.py`, `argus/api/routes/learning.py`, `argus/intelligence/__init__.py`, `argus/intelligence/briefing.py`, `argus/intelligence/classifier.py`, `argus/intelligence/counterfactual.py`, `argus/intelligence/filter_accuracy.py`, `argus/intelligence/position_sizer.py`, `argus/intelligence/quality_engine.py`, `argus/intelligence/sources/sec_edgar.py`, `argus/intelligence/startup.py`, `argus/models/trading.py`, `argus/strategies/pattern_strategy.py`, `docs/architecture.md`
**Safety tag:** `weekend-only`
**Theme:** Catalyst pipeline, quality engine, and counterfactual tracker findings. Note: scoring-context fingerprint work is in FIX-01, not here.

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
marker (`audit(FIX-07): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/intelligence/counterfactual.py`: 5 findings
- `argus/intelligence/briefing.py`: 3 findings
- `argus/api/routes/counterfactual.py`: 2 findings
- `argus/intelligence/__init__.py`: 2 findings
- `argus/intelligence/filter_accuracy.py`: 2 findings
- `argus/api/routes/learning.py`: 1 finding
- `argus/intelligence/classifier.py`: 1 finding
- `argus/intelligence/position_sizer.py`: 1 finding
- `argus/intelligence/quality_engine.py`: 1 finding
- `argus/intelligence/sources/sec_edgar.py`: 1 finding
- `argus/intelligence/startup.py`: 1 finding
- `argus/models/trading.py`: 1 finding
- `argus/strategies/pattern_strategy.py`: 1 finding
- `docs/architecture.md`: 1 finding

## Findings to Fix

### Finding 1: `P1-D1-M11` [MEDIUM]

**File/line:** [intelligence/counterfactual.py:232-237](argus/intelligence/counterfactual.py#L232-L237)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Zero-R guard uses float equality.** `if signal.entry_price == signal.stop_price: return None` — exact `==` comparison on floats. In practice Databento prices are fixed-point scaled by 1e9 so the division should land cleanly, but any strategy that arithmetically *derives* a stop from entry (e.g. `stop = entry - 0.10`) can produce a representation where entry != stop but `risk_per_share ≈ 1e-15`. The downstream `_close_position()` at line 617 then divides by near-zero risk_per_share and produces an R-multiple of 1e15.

**Impact:**

> Could poison an R-multiple average or filter-accuracy breakdown with an implausibly large outlier. Not observed in test data but classical float-equality hazard.

**Suggested fix:**

> Replace with `if abs(signal.entry_price - signal.stop_price) < 0.0001: return None`. Tune epsilon to sub-penny tolerance.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 2: `P1-D1-L05` [LOW]

**File/line:** [intelligence/counterfactual.py:199](argus/intelligence/counterfactual.py#L199)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `self._store: object \

**Impact:**

> None = None  # CounterfactualStore, set via set_store()` — duck-typed to avoid circular import. Same Protocol-type suggestion pattern as DEF-096.

**Suggested fix:**

> Loses static-type checking on `write_open` / `write_close` calls.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 3: `P1-D1-L06` [LOW]

**File/line:** [intelligence/counterfactual.py:315-344](argus/intelligence/counterfactual.py#L315-L344) + [counterfactual.py:655-660](argus/intelligence/counterfactual.py#L655-L660)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `asyncio.get_running_loop().create_task(...)` fire-and-forget creates orphan tasks whose exceptions are swallowed by the event loop's default handler. `CounterfactualStore._warn` catches write failures at the SQL layer, but a task that raises before hitting `try` inside `write_*` would disappear silently.

**Impact:**

> Low risk — `write_open`/`write_close` have outer try/except blocks, but any transient import / attribute error outside that block would be invisible.

**Suggested fix:**

> Wrap the `create_task(…)` in a helper that attaches `.add_done_callback(…)` to log exceptions, matching the `_poll_task_done` pattern from `api/server.py:194`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 4: `P1-D1-L10` [LOW]

**File/line:** [intelligence/counterfactual.py:262-265](argus/intelligence/counterfactual.py#L262-L265)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `metadata.get("regime_vector_snapshot") # type: ignore[union-attr]` — `metadata` is `dict[str, object] \

**Impact:**

> None` and the preceding `if metadata and "regime_vector_snapshot" in metadata` already narrows it. The `type: ignore` is probably unnecessary after the narrow.

**Suggested fix:**

> Cosmetic Pylance noise.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 5: `P1-D1-L14` [LOW]

**File/line:** [intelligence/counterfactual.py:40-47](argus/intelligence/counterfactual.py#L40-L47)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `RejectionStage` enum has `SHADOW = "shadow"` alongside true rejection stages. Shadow-mode routing is not really a *rejection* — it's a strategy-mode routing decision that produces a counterfactual track. The semantic mismatch is cosmetic but shows up in `FilterAccuracy` reports where "shadow" appears as a rejection category.

**Impact:**

> Conceptually confusing; a shadow-mode variant's filter accuracy is not really about *filtering*.

**Suggested fix:**

> Split into `RejectionStage` (true rejections) + `TrackingReason` (shadow, overflow). `FilterAccuracy` would then exclude shadow by default. Non-trivial refactor.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 6: `P1-D1-L07` [LOW]

**File/line:** [intelligence/briefing.py:245-247](argus/intelligence/briefing.py#L245-L247), [intelligence/classifier.py:297-299](argus/intelligence/classifier.py#L297-L299)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Both blocks: `except Exception as e: logger.error(…, e)` — no `exc_info`. Same pattern as P1-A1 M7.

**Impact:**

> Silent degradation of Claude paths; fallback brief or fallback classifier is used with no stack trace.

**Suggested fix:**

> `logger.error(…, e, exc_info=True)`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 7: `P1-D1-L08` [LOW]

**File/line:** [intelligence/briefing.py:265-270](argus/intelligence/briefing.py#L265-L270)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_group_by_category` hardcodes the eight category keys. `CatalystClassification.VALID_CATEGORIES` in `models.py:70-84` is the source of truth. Two drift-prone lists.

**Impact:**

> Add a 9th category in models and briefing's grouping silently routes it to `"other"`.

**Suggested fix:**

> Iterate `sorted(CatalystClassification.VALID_CATEGORIES)` to build the `grouped` dict.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 8: `P1-D1-L09` [LOW]

**File/line:** [intelligence/briefing.py:284](argus/intelligence/briefing.py#L284)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_build_prompt` accepts `date: str` but uses it only on line 296. The prompt otherwise has no date context beyond the user's opening sentence. Minor; consider mentioning the date in more spots or dropping the param if unused.

**Impact:**

> Cosmetic.

**Suggested fix:**

> N/A or expand prompt.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 9: `P1-F1-6` [MEDIUM]

**File/line:** [argus/api/routes/counterfactual.py:94](argus/api/routes/counterfactual.py#L94), [counterfactual.py:124](argus/api/routes/counterfactual.py#L124)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`/counterfactual/positions` returns `timestamp` in ET**; every other route file returns UTC (60+ occurrences audited). `/counterfactual/accuracy` correctly uses UTC-derived ISO strings. Drift is within a single file.

**Impact:**

> Frontend code that uniformly parses `timestamp` as UTC will mis-display by 4-5 hours. Probably already accounted for client-side, but the inconsistency is a foot-gun.

**Suggested fix:**

> Change the two `datetime.now(_ET).isoformat()` calls to `datetime.now(UTC).isoformat()`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 10: `P1-F1-7` [MEDIUM]

**File/line:** [argus/api/routes/counterfactual.py:201-213](argus/api/routes/counterfactual.py#L201-L213)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`assert isinstance(b, FilterAccuracyBreakdown)` in production deserialization.** Same anti-pattern flagged in DEF-106 (S6cf-1 review), now recurring. Python `-O` optimization strips asserts — the isinstance check disappears.

**Impact:**

> Production-disabled guard; future `-O` runs silently accept any object into `BreakdownResponse(...)`.

**Suggested fix:**

> Replace with `if not isinstance(b, FilterAccuracyBreakdown): raise TypeError(...)`. Extend DEF-106 scope or close-out with a batch fix.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 11: `P1-D1-M09` [MEDIUM]

**File/line:** [intelligence/__init__.py:146-158](argus/intelligence/__init__.py#L146-L158) + [intelligence/startup.py:303-308](argus/intelligence/startup.py#L303-L308)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Double-wrapped `asyncio.wait_for(120)` safety net.** `CatalystPipeline.run_poll()` already wraps the `gather(*fetch_tasks)` call with a 120s timeout (DEC-319). `run_polling_loop()` then wraps the same `pipeline.run_poll(...)` call with a **second** 120s timeout. If sources are slow-but-not-stuck the outer timeout can fire while the inner wait is still running; the outer `asyncio.TimeoutError` handler at `startup.py:326` logs `.critical()` but cannot distinguish whether the inner timeout or the outer fired.

**Impact:**

> Confusing diagnostics on slow polls. Not functionally incorrect.

**Suggested fix:**

> Pick one layer to own the timeout. `CatalystPipeline.run_poll()` is the natural owner because it has source visibility. Remove the outer `wait_for(120)` in `run_polling_loop()` and keep the inner.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 12: `P1-D1-M12` [MEDIUM]

**File/line:** [intelligence/__init__.py:259-317](argus/intelligence/__init__.py#L259-L317)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Semantic dedup anchors to `kept[-1]` not sliding cluster midpoint.** Within each `(symbol, category)` group, the walk compares each new catalyst to the *last kept* item, keeping whichever has higher `quality_score`. If items arrive as A(score=70, t=0) → B(score=50, t=20) → C(score=60, t=40) with window=30, A wins over B, then C is compared to A (diff=40 > 30) and C is also kept — even though C is only 20min after B's *original* timestamp and would have been in-window against B. DEC-311 is ambiguous about the intended semantics.

**Impact:**

> Undercounts dedup when quality scores decrease within a window. Over-counts when scores increase. Marginal effect in practice — catalysts within 30-min windows have similar scores — but behaviour is not well-defined against the DEC.

**Suggested fix:**

> Decide on intended semantics and add a test: either (a) cluster-midpoint anchor, or (b) sliding-window anchor to first-seen in cluster, or (c) current `kept[-1]` anchor (explicitly documented). Update DEC-311 body to match.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 13: `P1-D1-L03` [LOW]

**File/line:** [intelligence/filter_accuracy.py:106](argus/intelligence/filter_accuracy.py#L106)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> "Correct rejection" is defined as `theoretical_pnl <= 0`. Breakeven counts as "correct". Most interpretations of "filter accuracy" would consider breakeven inconclusive, not correct.

**Impact:**

> Marginal effect. Shifts reported accuracy slightly upward.

**Suggested fix:**

> Either `< 0` (strict) or document the choice in the dataclass docstring and in the `/counterfactual/accuracy` REST contract.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 14: `P1-D1-L04` [LOW]

**File/line:** [intelligence/filter_accuracy.py:159](argus/intelligence/filter_accuracy.py#L159)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `min_sample_count: int = 10` default is hardcoded. Learning Loop V1 uses its own minimum sample configuration in `config/learning_loop.yaml`. The two should probably share a definition or at least reference each other — both inform "is this breakdown trustworthy?"

**Impact:**

> Minor divergence risk if the Learning Loop's threshold is tuned upward but filter-accuracy's stays at 10.

**Suggested fix:**

> Pull both values from `config/learning_loop.yaml` (e.g. `learning_loop.min_sample_count`) or add a `config/filter_accuracy.yaml`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 15: `P1-F1-5` [MEDIUM]

**File/line:** [argus/api/routes/learning.py](argus/api/routes/learning.py) (8 endpoints), [experiments.py](argus/api/routes/experiments.py) (5), [historical.py](argus/api/routes/historical.py) (4), [counterfactual.py:60](argus/api/routes/counterfactual.py#L60), [vix.py](argus/api/routes/vix.py) (2), [ai.py:521](argus/api/routes/ai.py#L521), [strategies.py:382](argus/api/routes/strategies.py#L382), [auth.py:132](argus/api/routes/auth.py#L132)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **~22 of ~99 endpoints lack `response_model=`** and return bare `dict`. All newer routes (Sprint 27.7+) skip response_model; older routes (Sprint 14-25) use it consistently.

**Impact:**

> (1) OpenAPI docs show untyped responses — harder for frontend to generate types. (2) No server-side response validation. (3) Breaks the pattern new contributors see; encourages drift.

**Suggested fix:**

> For each bare-`dict` endpoint, define a matching `*Response` Pydantic model in the same file and wire `response_model=...`. Many already build inline TypedDicts-in-spirit — extraction is mechanical.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 16: `P1-D1-L12` [LOW]

**File/line:** [intelligence/classifier.py:237-244](argus/intelligence/classifier.py#L237-L244)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `"Classification cycle cost"` log aggregates per-batch cost but is scoped to a **single call to `classify_batch()`**, not a full polling cycle. A single poll processes one batch per source, so if multiple sources flowed through the same `classify_batch()` call this log would be correct; in practice each `classify_batch()` call is one batch of headlines and the word "cycle" is slightly inaccurate.

**Impact:**

> Log-semantics minor.

**Suggested fix:**

> Rename to "Classification batch cost".

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 17: `P1-D1-L02` [LOW]

**File/line:** [intelligence/position_sizer.py:188-189](argus/intelligence/position_sizer.py#L188-L189)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_risk_tier_from_grade()` is a direct alias: `return grade`. `SetupQuality.risk_tier` is therefore always equal to `SetupQuality.grade`. Every downstream consumer that reads `risk_tier` is just reading `grade` under a different name. Either rename or add a clear comment.

**Impact:**

> Confusing API surface. Suggests a separate concept exists (risk tier vs grade) when it does not.

**Suggested fix:**

> Either delete `risk_tier` from `SetupQuality` and have consumers read `grade`, or document that they are canonically equal in V1.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 18: `P1-D1-M10` [MEDIUM]

**File/line:** [intelligence/quality_engine.py:127-136](argus/intelligence/quality_engine.py#L127-L136)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`_score_catalyst_quality()` cutoff is always UTC-now minus 24h**, regardless of the catalysts' `published_at` TZ. If `published_at` is ET-naive, the path at line 131 reattaches `tzinfo=UTC` — which is wrong (the data is ET per `storage.py:228`). A catalyst published at 09:30 ET will appear at the comparator as 09:30 UTC = 05:30 ET — offsetting the cutoff window by 4 hours depending on DST.

**Impact:**

> Edge-case distortion of the "last 24 hours" filter. Probably not material because most catalysts in the DB *do* carry an explicit tzinfo (set in source parsers), but any legacy row with naive timestamps will be misfiltered.

**Suggested fix:**

> Change `.replace(tzinfo=UTC)` to `.replace(tzinfo=_ET)` (importing the existing `_ET = ZoneInfo("America/New_York")`), to match the ET convention used everywhere else in the intelligence layer.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 19: `P1-D1-L13` [LOW]

**File/line:** [intelligence/sources/sec_edgar.py:50](argus/intelligence/sources/sec_edgar.py#L50), etc.
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_TICKERS_URL`, `_SUBMISSIONS_URL`, `_FILING_URL`, `_EFTS_SEARCH_URL` are hardcoded strings on the class, not in YAML. Fine for now (SEC URLs never change) but contradicts the global rule that "All tunable parameters live in YAML" from `.claude/rules/architecture.md`.

**Impact:**

> Philosophical consistency only.

**Suggested fix:**

> Leave as-is; add a class-docstring note that SEC URLs are SEC-owned constants, not operator-tunable.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 20: `P1-D1-L11` [LOW]

**File/line:** [intelligence/startup.py:223-237](argus/intelligence/startup.py#L223-L237)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `shutdown_intelligence()` closes `pipeline` and `storage` but does NOT stop the `polling_task`. The polling task is held by `api/server.py`'s lifespan (via `app_state.intelligence_polling_task`), and the lifespan handler does cancel it — but `shutdown_intelligence()`'s docstring says "stops the pipeline and closes storage connections" with no caveat.

**Impact:**

> Misleading docstring. Shutdown ordering is actually fine because the lifespan cancels before this is called.

**Suggested fix:**

> Document ordering in the docstring; assert polling task is already cancelled as a precondition.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 21: `DEF-106` [LOW]

**File/line:** argus/models/trading.py + argus/api/routes/counterfactual.py
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> from_dict() contains ~8 assert statements in production + 1 new site

**Impact:**

> assert isinstance strips under python -O; guard disappears

**Suggested fix:**

> Replace all assert isinstance with if/raise TypeError (P1-F1 #7 extends scope)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 22: `DEF-096` [LOW]

**File/line:** argus/strategies/pattern_strategy.py + argus/intelligence/counterfactual.py
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Duck-typed candle store + store references (object + hasattr)

**Impact:**

> No type safety; silent drift if symbols renamed

**Suggested fix:**

> Define CandleStoreProtocol + CounterfactualStoreProtocol in argus/core/protocols.py

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

### Finding 23: `P1-D1-M08` [MEDIUM]

**File/line:** [docs/architecture.md:1409-1428](docs/architecture.md#L1409-L1428)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Architecture.md §3.11 describes an `intelligence/catalyst/` subdirectory that does not exist.** Paths cited — `intelligence/catalyst/pipeline.py`, `intelligence/catalyst/classifier.py`, `intelligence/catalyst/storage.py`, `intelligence/catalyst/briefing.py`, `intelligence/catalyst/sources/sec_edgar.py`, etc. — are stale. Actual layout is flat (`intelligence/classifier.py`, `intelligence/storage.py`, `intelligence/briefing.py`, `intelligence/sources/sec_edgar.py`) and `CatalystPipeline` is defined in `intelligence/__init__.py`, not `pipeline.py`.

**Impact:**

> New-contributor or agent reading `architecture.md` cannot navigate the code. Same doc-drift class as P1-A1 M1.

**Suggested fix:**

> Rewrite §3.11 path references. Recommend inlining the actual layout from `argus/intelligence/` rather than hand-maintaining twice.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-07-intelligence-catalyst-quality**`.

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
| ... | ~~description~~ **RESOLVED FIX-07-intelligence-catalyst-quality** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-07-intelligence-catalyst-quality**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-07` (full ID: `FIX-07-intelligence-catalyst-quality`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-07-intelligence-catalyst-quality**` | | |
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
audit(FIX-07): intelligence layer (catalysts + quality + counterfactual)

Addresses audit findings:
- P1-D1-M11 [MEDIUM]: Zero-R guard uses float equality
- P1-D1-L05 [LOW]: 'self
- P1-D1-L06 [LOW]: 'asyncio
- P1-D1-L10 [LOW]: 'metadata
- P1-D1-L14 [LOW]: 'RejectionStage' enum has 'SHADOW = "shadow"' alongside true rejection stages
- P1-D1-L07 [LOW]: Both blocks: 'except Exception as e: logger
- P1-D1-L08 [LOW]: '_group_by_category' hardcodes the eight category keys
- P1-D1-L09 [LOW]: '_build_prompt' accepts 'date: str' but uses it only on line 296
- P1-F1-6 [MEDIUM]: '/counterfactual/positions' returns 'timestamp' in ET; every other route file returns UTC (60+ occurrences audited)
- P1-F1-7 [MEDIUM]: 'assert isinstance(b, FilterAccuracyBreakdown)' in production deserialization
- P1-D1-M09 [MEDIUM]: Double-wrapped 'asyncio
- P1-D1-M12 [MEDIUM]: Semantic dedup anchors to 'kept[-1]' not sliding cluster midpoint
- P1-D1-L03 [LOW]: "Correct rejection" is defined as 'theoretical_pnl <= 0'
- P1-D1-L04 [LOW]: 'min_sample_count: int = 10' default is hardcoded
- P1-F1-5 [MEDIUM]: ~22 of ~99 endpoints lack 'response_model=' and return bare 'dict'
- P1-D1-L12 [LOW]: '"Classification cycle cost"' log aggregates per-batch cost but is scoped to a single call to 'classify_batch()', not a 
- P1-D1-L02 [LOW]: '_risk_tier_from_grade()' is a direct alias: 'return grade'
- P1-D1-M10 [MEDIUM]: '_score_catalyst_quality()' cutoff is always UTC-now minus 24h, regardless of the catalysts' 'published_at' TZ
- P1-D1-L13 [LOW]: '_TICKERS_URL', '_SUBMISSIONS_URL', '_FILING_URL', '_EFTS_SEARCH_URL' are hardcoded strings on the class, not in YAML
- P1-D1-L11 [LOW]: 'shutdown_intelligence()' closes 'pipeline' and 'storage' but does NOT stop the 'polling_task'
- DEF-106 [LOW]: from_dict() contains ~8 assert statements in production + 1 new site
- DEF-096 [LOW]: Duck-typed candle store + store references (object + hasattr)
- P1-D1-M08 [MEDIUM]: Architecture

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
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-07-intelligence-catalyst-quality)
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
3. **A one-line summary:** `Session FIX-07 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-07-intelligence-catalyst-quality**`
