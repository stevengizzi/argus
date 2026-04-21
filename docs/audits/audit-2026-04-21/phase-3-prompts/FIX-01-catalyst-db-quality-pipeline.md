# Fix Session FIX-01-catalyst-db-quality-pipeline: Quality pipeline repair + scoring-context fingerprint

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 9
**Files touched:** `argus/intelligence/quality_engine.py`, `argus/main.py`, `config/quality_engine.yaml`, `config/system_live.yaml`
**Safety tag:** `weekend-only`
**Theme:** Repairs the two-part quality-scoring regression active since Sprint 32.9 (CatalystStorage pointed at the wrong DB; quality_engine.yaml values never reaching runtime), AND lands scoring-context fingerprint infrastructure first so pre-fix and post-fix shadow data remain distinguishable in CounterfactualTracker.

> **SPECIAL SCOPE EXTENSION:** this session also lands scoring-context
> fingerprint infrastructure (new module, schema migration, 4 new tests)
> BEFORE touching the quality pipeline. See Section "Scoring-Context
> Fingerprint" below. This is not a CSV finding — it is architectural
> prerequisite for the pipeline edits to avoid losing track of pre-fix vs
> post-fix shadow data in CounterfactualTracker.

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
marker (`audit(FIX-01): WIP — <reason>`) rather than leaving
uncommitted changes.

## Scoring-Context Fingerprint Infrastructure (LAND FIRST)

**Rationale.** 22 shadow variants are currently collecting CounterfactualTracker
data against the broken quality scoring pipeline. When the pipeline fixes in
this session land (catalyst DB path + quality recalibration), the scoring
distribution will shift meaningfully:
- `catalyst_quality` starts producing real variance instead of constant 50.0
- `historical_match` drops to 0% weight (currently 15% × 50.0 = constant +7.5)
- A+/A/B/C grade thresholds properly recalibrate (Sprint 32.9 values)

PromotionEvaluator must be able to distinguish pre-fix and post-fix shadow
data so it does not mix scoring contexts when comparing variants. Landing the
fingerprint infrastructure FIRST (before the behavioral fixes) ensures pre-fix
data carries one fingerprint and post-fix data carries a different one —
clean separation with no hand-annotation.

**Design pattern.** Mirror the two existing SHA-256 fingerprint patterns already
in ARGUS:
1. `compute_parameter_fingerprint()` in `argus/strategies/patterns/factory.py`
   (detection-params fingerprint for PatternModule variants).
2. `config_fingerprint` column on the `trades` table (written by
   OrderManager at trade close, introduced Sprint 31.75 DEC-383).

Same algorithm (SHA-256 of canonical JSON with sorted keys + compact
separators, first 16 hex chars). Same write-at-event-time posture. Same
optional-filter semantics on the reader side.

### Step 1A — Create `argus/intelligence/quality/scoring_fingerprint.py`

New module, single public function. Put it in a new sub-package
`argus/intelligence/quality/` if that directory does not already exist
(grep first — if quality_engine.py is in a flat `intelligence/` dir, place
the new module at `argus/intelligence/scoring_fingerprint.py` and reconcile
with the operator post-session).

```python
# argus/intelligence/quality/scoring_fingerprint.py
"""Scoring-context fingerprint for CounterfactualTracker.

Produces a 16-char SHA-256 hex fingerprint over the currently-active
QualityEngine configuration (weights + thresholds + risk tiers). Used to
tag shadow positions so PromotionEvaluator can separate pre-fix and
post-fix data when the quality pipeline changes.
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.core.config import QualityEngineConfig


def compute_scoring_fingerprint(quality_config: QualityEngineConfig) -> str:
    """Return a 16-character hex SHA-256 fingerprint of the scoring config.

    Serializes weights + thresholds + risk_tiers as canonical JSON
    (sorted keys, compact separators) and hashes. Identical to the
    detection-params pattern in argus/strategies/patterns/factory.py.
    """
    payload = {
        "weights": quality_config.weights.model_dump(mode="json"),
        "thresholds": quality_config.thresholds.model_dump(mode="json"),
        "risk_tiers": quality_config.risk_tiers.model_dump(mode="json"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

**Acceptance:** Module imports cleanly, no circular imports, function returns
a 16-char lowercase hex string.

### Step 1B — Schema migration on `counterfactual_positions`

Add idempotent migration to `CounterfactualStore.__init__` (in
`argus/intelligence/counterfactual_store.py`) that adds a
`scoring_fingerprint TEXT` column if it does not already exist.

```python
# Inside CounterfactualStore._ensure_schema() (or equivalent init method),
# AFTER the existing table creation / existing ALTER migrations:

async with db.execute(
    "SELECT name FROM pragma_table_info('counterfactual_positions') "
    "WHERE name = 'scoring_fingerprint'"
) as cur:
    row = await cur.fetchone()
if row is None:
    await db.execute(
        "ALTER TABLE counterfactual_positions "
        "ADD COLUMN scoring_fingerprint TEXT"
    )
    await db.commit()
```

Follow the exact error-handling pattern of existing `CounterfactualStore`
migrations. Keep the migration in a private `_ensure_schema()` method if
that matches the existing file structure.

**Acceptance:** Running against a pre-existing `counterfactual.db`
(with the old schema) succeeds and adds the column. Running a second
time is a no-op. Fresh DB creation includes the column from the start.

### Step 1C — Wire into `CounterfactualTracker.on_signal_rejected()`

Add a `scoring_fingerprint: str | None` field to the `ShadowPosition`
dataclass (default `None` for backwards-compat on in-memory instances).
In `on_signal_rejected`, compute the current fingerprint from the live
QualityEngine config at position-open time and persist it to the new
column on write.

- The QualityEngineConfig reference is available via
  `self._quality_config` (or whatever handle CounterfactualTracker
  already holds — if none, wire one via constructor injection from
  `main.py` at the same site that constructs CounterfactualTracker).
- Compute the fingerprint once per `on_signal_rejected` call, not once
  per tracker instance: the quality config could change mid-session
  once ConfigProposalManager ships autonomous application (Sprint 40+).

**Acceptance:** New shadow positions write a non-null
`scoring_fingerprint`. Existing shadow positions retain NULL.

### Step 1D — Add startup log line

In `CounterfactualTracker.__init__` (or its equivalent init method),
emit an INFO-level log with the current fingerprint after the
QualityEngine config is attached:

```python
from argus.intelligence.quality.scoring_fingerprint import compute_scoring_fingerprint

fingerprint = compute_scoring_fingerprint(self._quality_config)
logger.info(
    "CounterfactualTracker initialized with scoring fingerprint %s",
    fingerprint,
)
```

**Acceptance:** Log line appears once per server startup when
counterfactual + quality are both enabled.

### Step 1E — Optional filter on PromotionEvaluator

Add `scoring_fingerprint: str | None = None` parameter to every public
variant-comparison method on `PromotionEvaluator` (minimum:
`evaluate_for_promotion`, `evaluate_for_demotion`, or equivalents
that read shadow-position data). When set, filter the query used to
load shadow positions to only those matching the fingerprint. When
`None` (default), behavior is unchanged.

**Acceptance:** Default-argument invocation (no fingerprint) returns
the same result as before the change. Explicit-fingerprint invocation
returns only matching positions.

### Step 1F — Test coverage

New file `tests/intelligence/test_scoring_fingerprint.py` with 4 tests:

1. **Stability** — Two calls with the same config object return the
   same fingerprint.
2. **Sensitivity** — A weight delta of 0.01 (e.g. bumping
   `weights.pattern_strength` from 0.30 to 0.31) produces a different
   fingerprint.
3. **Round-trip persistence** — Write a shadow position with a known
   fingerprint, read it back via CounterfactualStore's query API,
   confirm the fingerprint matches.
4. **PromotionEvaluator filter** — Seed two shadow positions with
   different fingerprints. Assert that the filtered query returns
   only the matching one.

Use in-memory SQLite (`:memory:`) or a `tmp_path`-based DB so tests
are isolated.

**Acceptance:** All 4 tests pass. Suite net delta is +4 pytest
(before any of the later findings are applied).

### Step 1G — Baseline test run (FINGERPRINT CHECKPOINT)

After Steps 1A–1F, run the full suite BEFORE touching the catalyst DB
path or quality config. The suite should:
- Net delta: +4 (the 4 new tests).
- Zero regressions: pre-existing failures stay pre-existing; no new ones.

If either condition fails, pause and triage before proceeding to the
scoring-impacting fixes below. **DO NOT** proceed to the findings
section until this checkpoint is clean — otherwise any test failure
in the pipeline fixes will be confounded with fingerprint-infra bugs.

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q
# Expected: PASS count = baseline + 4
```

## Quality-Config Fix: Option A vs Option B (OPERATOR CHOICE REQUIRED)

Findings `P1-D1-C02` / `DEF-142` / `H2-D01` / `H2-D02` / `H2-D03` / `H2-DEAD05`
all resolve to the same root cause: `config/quality_engine.yaml` holds the
Sprint 32.9 recalibrated weights + thresholds, but `load_config()` only
reads from `system.yaml` and `system_live.yaml`. The standalone
`quality_engine.yaml` is dead. Two fix paths; operator picks one before
this session runs:

**Option A — Sync values into the live YAMLs (simple, explicit).**
Copy the 12 fields from `config/quality_engine.yaml` into the
`quality_engine:` block of both `config/system_live.yaml` and
`config/system.yaml`:

- `weights.pattern_strength: 0.375`
- `weights.catalyst_quality: 0.25`
- `weights.volume_profile: 0.275`
- `weights.historical_match: 0.0`
- `weights.regime_alignment: 0.10`
- `thresholds.a_plus: 72`
- `thresholds.a: 66`
- `thresholds.b_plus: 61`
- `thresholds.b: 56`
- `thresholds.b_minus: 51`
- `thresholds.c_plus: 46`
- `thresholds.c: 40`

After copying, delete `config/quality_engine.yaml` (or leave it with a
`# DEAD — values live in system*.yaml` header, per operator preference).

**Option B — Teach `load_config()` to merge standalone YAMLs.**
Extend `load_config()` in `argus/core/config.py` so that if a
`config/{section}.yaml` file exists (e.g. `config/quality_engine.yaml`,
`config/overflow.yaml`), its contents are merged over the corresponding
`system_live.yaml` block with explicit precedence: standalone > live > base.
This gracefully handles future standalone files (notably, FIX-02's
`config/overflow.yaml` situation becomes automatically resolved by the
same change).

**Operator instruction:** Fill in which option before this session runs:

> - [ ] Option A (sync values into system_live.yaml + system.yaml)
> - [ ] Option B (extend load_config() to merge standalone YAMLs)

If left blank, **Option A is the default** — it is smaller-blast-radius
and does not introduce new config-loading semantics.

The same operator choice also resolves FIX-02's overflow.broker_capacity
divergence. Use the SAME option for both sessions to keep the codebase
consistent. If Option B is chosen here, FIX-02 becomes trivial (the
overflow.yaml merge is free). If Option A is chosen, FIX-02 syncs
broker_capacity into system_live.yaml.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. **Scoring-Context Fingerprint Infrastructure** (see dedicated section above, Steps 1A–1G)
2. **Baseline checkpoint** after Step 1G — suite delta +4, zero regressions
3. **Catalyst-DB path fix** (Finding `P1-D1-C01` / `DEF-082`)
4. **Quality config activation** (Findings `P1-D1-C02` / `DEF-142` / `H2-D01` / `H2-D02` / `H2-D03` / `H2-DEAD05`) — apply Operator-selected Option A or B
5. **Historical-match stub hardening** (Finding `P1-D1-L01`)
6. **Post-session verification + commit**

**Per-file finding counts (edit hotspots):**

- `config/quality_engine.yaml`: 5 findings
- `argus/main.py`: 2 findings
- `argus/intelligence/quality_engine.py`: 1 finding
- `config/system_live.yaml`: 1 finding

## Findings to Fix

### Finding 1: `P1-D1-C02` [CRITICAL]

**File/line:** [config/quality_engine.yaml](config/quality_engine.yaml) vs [config/system_live.yaml:119-145](config/system_live.yaml#L119-L145) / [core/config.py:1321-1372](argus/core/config.py#L1321-L1372)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Sprint 32.9 quality-engine recalibration is not loaded at runtime.** `config/quality_engine.yaml` (pattern=0.375, catalyst=0.25, volume=0.275, historical=0.0, regime=0.10; thresholds 72/66/61/56/51/46/40) exists only for `ConfigProposalManager` validation. Live runtime uses `ArgusConfig.system.quality_engine`, populated from the `quality_engine:` block in `system_live.yaml` — which still has the **pre-recalibration** values (pattern=0.30, catalyst=0.25, volume=0.20, historical=0.15, regime=0.10; thresholds 90/80/70/60/50/40/30). `load_config()` reads only `system.yaml`/`system_live.yaml`, never merges `config/quality_engine.yaml`. CLAUDE.md's "Sprint 32.9 additions: quality_engine.yaml historical_match weight → 0…" is therefore misleading — the file was updated but the *running system* still honors the old `system_live.yaml` values.

**Impact:**

> This is the single largest functional discrepancy surfaced by the audit. Every scoring/grading path in paper-trading since Sprint 32.9 has been running old weights: `historical_match` (a constant-50 stub) contributes 15% of composite, and grade thresholds require 90/80/70/… points for A+/A/A-, which is unreachable under the actual 35–77 observed score range per the recalibration notes. Result: under the *intended* Sprint 32.9 calibration almost every signal would grade A+/A; under the *actual* live config virtually everything grades B because the thresholds are calibrated to the wrong score distribution. **This explains DEF-142 ("grade compression to B") that Sprint 32.9 was supposed to resolve.**

**Suggested fix:**

> Option A: copy the eight fields (`weights.*` and `thresholds.*`) from `config/quality_engine.yaml` into the `quality_engine:` block of `config/system_live.yaml` and `config/system.yaml`. Option B: change `load_config()` to also merge `config/quality_engine.yaml` (and `config/overflow.yaml`, `config/counterfactual.yaml`, etc.) with an explicit precedence rule. Option A is the minimum fix; Option B closes the split-source class of bugs. Add a parity test: `assert raw_system["quality_engine"] == yaml.load("config/quality_engine.yaml")`.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 2: `H2-D01` [CRITICAL]

**File/line:** config/quality_engine.yaml vs config/system_live.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Sprint 32.9 pattern_strength weight (0.375) in quality_engine.yaml NOT loaded at runtime; runtime uses system.yaml 0.30

**Impact:**

> Part of DEF-142 confirmed empirical grade compression

**Suggested fix:**

> Option A: Copy weights to system_live.yaml + system.yaml. Option B: Merge standalone YAMLs in load_config() with explicit precedence

**Audit notes:** Part of DEF-142 fix bundle (confirmed empirically)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 3: `H2-D02` [CRITICAL]

**File/line:** config/quality_engine.yaml vs config/system_live.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> historical_match weight: system.yaml 0.15, quality_engine.yaml 0.0. system.yaml wins; historical_match still consuming 15% of grade weight despite being constant-50 stub

**Impact:**

> Part of DEF-142

**Suggested fix:**

> Same fix as H2-D01

**Audit notes:** Part of DEF-142 fix bundle (confirmed empirically)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 4: `H2-D03` [CRITICAL]

**File/line:** config/quality_engine.yaml vs config/system_live.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> A+ threshold: system.yaml 90, quality_engine.yaml 72. system.yaml wins; signals cluster in B grade (DEF-142 original symptom)

**Impact:**

> Part of DEF-142

**Suggested fix:**

> Same fix as H2-D01

**Audit notes:** Part of DEF-142 fix bundle (confirmed empirically)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 5: `H2-DEAD05` [MEDIUM]

**File/line:** config/quality_engine.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Dead YAML — root cause of DEF-142 confirmed here

**Impact:**

> Primary driver of H2-D01/D02/D03

**Suggested fix:**

> Fix via H2-D01 merge; consider deleting standalone file afterward

**Audit notes:** Part of DEF-142 fix bundle (confirmed empirically)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 6: `P1-D1-C01` [CRITICAL]

**File/line:** [main.py:1112-1113](argus/main.py#L1112-L1113) vs [intelligence/startup.py:92-93](argus/intelligence/startup.py#L92-L93)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Quality engine's `CatalystStorage` is pointed at the wrong database.** Phase 10.25 creates `CatalystStorage(str(Path(config.system.data_dir) / "argus.db"))` for the quality pipeline's catalyst lookup. The catalyst **pipeline** (classifier + briefing + polling loop) creates a *separate* `CatalystStorage(Path(data_dir) / "catalyst.db")` in `intelligence/startup.py:92` — and *that* is where all 12,114 ingested catalysts live. Verified: `sqlite3 data/argus.db 'SELECT COUNT(*) FROM catalyst_events'` → **0**; `sqlite3 data/catalyst.db 'SELECT COUNT(*) FROM catalyst_events'` → **12114**. `CatalystStorage.initialize()` helpfully creates the empty `catalyst_events` table in `argus.db` via `CREATE TABLE IF NOT EXISTS`, masking the misconfiguration at startup.

**Impact:**

> **`catalyst_quality` dimension is effectively disabled for every signal in live trading.** `quality_engine.py:_score_catalyst_quality()` queries the empty table, finds no recent rows, and returns the `50.0` neutral default for **every** signal. This is the real root cause of DEF-082 ("catalyst_quality always 50.0 — expected when no catalysts"). The pipeline is ingesting catalysts fine; the quality engine is just reading from the wrong file. Any quality-based sizing / filtering decision that should have been lifted by a genuine catalyst is silently degraded. Paper-trading variants are all trained against this corrupt scoring dimension.

**Suggested fix:**

> In `main.py:1108-1117`, switch to `db_path = Path(config.system.data_dir) / "catalyst.db"`. Better: reuse the instance that `intelligence/startup.py` already built via `app_state.catalyst_storage` (see `argus/api/server.py:156`) rather than creating a second connection to the same DB file. Add an assertion or migration: detect `argus.db.catalyst_events` with `rowcount > 0` on boot and WARN (it will always be a leftover from this bug).

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 7: `DEF-082` [CRITICAL]

**File/line:** argus/main.py:1113
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> catalyst_quality always 50.0 — actually reading wrong DB (P1-D1 C1)

**Impact:**

> Quality pipeline catalyst_quality is effectively disabled for every signal

**Suggested fix:**

> Fix CatalystStorage path: argus.db → catalyst.db (P1-D1 C1)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 8: `P1-D1-L01` [LOW]

**File/line:** [intelligence/quality_engine.py:154-155](argus/intelligence/quality_engine.py#L154-L155)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_score_historical_match()` is a stub returning hardcoded `50.0`. Known (documented in `config/quality_engine.yaml` comment). With `system_live.yaml`'s `historical_match: 0.15`, this stub still contributes a **flat 7.5** to every signal's composite score — effectively a bias, not a no-op. Once C2 is fixed to set `historical_match: 0.0` live, the stub is dormant and can be `return 0.0` to make the dormancy unambiguous.

**Impact:**

> Slight score inflation today. Zero impact once C2 is fixed.

**Suggested fix:**

> After C2, change `return 50.0` to `return 0.0` (or raise `NotImplementedError` with a guard on the weight) so nobody accidentally re-enables the weight without implementing the method.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

### Finding 9: `DEF-142` [CRITICAL]

**File/line:** config/system_live.yaml + config/system.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Sprint 32.9 quality recalibration never activated at runtime (CONFIRMED empirical)

**Impact:**

> Grade compression: 97% of signals grade B, zero A-grades, max composite 67.0 vs A- threshold 70

**Suggested fix:**

> Copy weights/thresholds from config/quality_engine.yaml into system_live.yaml (Option A) OR merge standalone YAMLs in load_config (Option B)

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`.

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
| ... | ~~description~~ **RESOLVED FIX-01-catalyst-db-quality-pipeline** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-01-catalyst-db-quality-pipeline**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-01` (full ID: `FIX-01-catalyst-db-quality-pipeline`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**` | | |
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
audit(FIX-01): quality pipeline repair + scoring context fingerprint

Catalyst DB path corrected (DEF-082 P1-D1 C1): CatalystStorage now points at
catalyst.db (12,114 rows) instead of argus.db (0 rows). catalyst_quality
dimension is no longer constant 50.0.

Quality recalibration activated (DEF-142 + H2-D01/D02/D03/DEAD05): quality
weights and thresholds from Sprint 32.9 now reach runtime via
<operator-selected approach: Option A or Option B>. Grade distribution
expected to spread properly; A-grade tier now reachable.

Scoring context fingerprint infrastructure added:
- new argus/intelligence/quality/scoring_fingerprint.py
- counterfactual_positions.scoring_fingerprint column
- CounterfactualTracker captures at position-open
- PromotionEvaluator optional filter parameter
- 4 new tests in tests/intelligence/test_scoring_fingerprint.py

This commit changes the live scoring pipeline. Pre-fix shadow data in
CounterfactualTracker is preserved but carries the pre-fix fingerprint;
post-fix data carries the new fingerprint. PromotionEvaluator comparisons
should filter by fingerprint until operator decides cross-context rules.

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
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
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-01-catalyst-db-quality-pipeline)
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
3. **A one-line summary:** `Session FIX-01 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Scoring-context fingerprint checkpoint clean (Step 1G) BEFORE pipeline edits
- [ ] Operator choice (Option A or B) recorded in the commit message body
- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-01-catalyst-db-quality-pipeline**`
