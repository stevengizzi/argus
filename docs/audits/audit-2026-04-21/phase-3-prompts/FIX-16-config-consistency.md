# Fix Session FIX-16-config-consistency: config/ — cross-YAML consistency

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 19
**Files touched:** `argus/core/config.py`, `config/counterfactual.yaml`, `config/experiments.yaml`, `config/learning_loop.yaml`, `config/overflow.yaml`, `config/regime.yaml`, `config/scanner.yaml`, `config/strategies/*.yaml (12 of 15)`, `config/strategies/*.yaml (13 of 15)`, `config/strategies/*.yaml (9 non-ABCD pattern strategies)`, `config/strategies/*.yaml (all 15)`, `config/system.yaml`, `config/vix_regime.yaml`
**Safety tag:** `weekend-only`
**Theme:** Config-file consistency: system.yaml vs system_live.yaml, strategy YAMLs, universe_filters/, learning_loop.yaml, counterfactual.yaml. Focus: drift, unused fields, schema divergence.

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
marker (`audit(FIX-16): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/core/config.py`: 4 findings
- `config/experiments.yaml`: 2 findings
- `config/learning_loop.yaml`: 2 findings
- `config/regime.yaml`: 2 findings
- `config/counterfactual.yaml`: 1 finding
- `config/overflow.yaml`: 1 finding
- `config/scanner.yaml`: 1 finding
- `config/strategies/*.yaml (12 of 15)`: 1 finding
- `config/strategies/*.yaml (13 of 15)`: 1 finding
- `config/strategies/*.yaml (9 non-ABCD pattern strategies)`: 1 finding
- `config/strategies/*.yaml (all 15)`: 1 finding
- `config/system.yaml`: 1 finding
- `config/vix_regime.yaml`: 1 finding

## Findings to Fix

### Finding 1: `DEF-109` [LOW]

**File/line:** argus/core/config.py (OrderManagerConfig)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> V1 trailing stop config dead code

**Impact:**

> enable_trailing_stop + trailing_stop_atr_multiplier no longer referenced post-Sprint 28.5

**Suggested fix:**

> Delete fields; batch with P1-H2 config-consistency cleanup

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 2: `H2-S06` [MEDIUM]

**File/line:** argus/core/config.py (ScannerConfig) vs config/scanner.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> ScannerConfig Pydantic only has scanner_type/static_symbols; 3 nested scanner blocks in YAML silently dropped. Pydantic class not used at runtime but tested via test_config.py

**Impact:**

> Test coverage of a config path that does not match production

**Suggested fix:**

> Either delete ScannerConfig Pydantic class OR extend it to cover nested blocks

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 3: `H2-H10` [MEDIUM]

**File/line:** argus/core/config.py:300 (ApiConfig.password_hash)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Hidden-ish default empty string; if operator boots with system.yaml (Alpaca incubator), password empty and JWT login broken

**Impact:**

> High operational importance hidden default

**Suggested fix:**

> Add explicit documentation OR fail-loud-on-empty in ApiConfig validator

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 4: `H2-H11` [MEDIUM]

**File/line:** argus/core/config.py:753 (StrategyConfig.mode)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Uses str not StrategyMode enum; misspellings (e.g. "Shadow" capitalized) silently routed live

**Impact:**

> Silent shadow-mode escape

**Suggested fix:**

> Change type to StrategyMode enum; Pydantic validates

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 5: `H2-S02` [CRITICAL]

**File/line:** config/experiments.yaml (whole file)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Variant params not validated against target pattern — any typo silently dropped

**Impact:**

> 22-variant shadow fleet collecting data; any typo (e.g. min_gap_pct vs min_gap_percent) invisible

**Suggested fix:**

> Add spawn-time validation in VariantSpawner: check each params.* key against get_pattern_class(pattern_name)().get_default_params() field names; fail loudly on mismatch

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 6: `H2-S04` [MEDIUM]

**File/line:** config/experiments.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Variants list-element dict shape not validated; extra="forbid" promise at top level broken

**Impact:**

> Related to H2-S02

**Suggested fix:**

> Fix together with H2-S02

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 7: `H2-H13` [MEDIUM]

**File/line:** config/system*.yaml + config/learning_loop.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> No learning_loop section in any system YAML; Learning Loop uses all Pydantic defaults, not learning_loop.yaml values

**Impact:**

> Standalone YAML is dead; operator tuning ignored

**Suggested fix:**

> Either wire learning_loop.yaml into load_config OR move values into system_live.yaml

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 8: `H2-DEAD01` [MEDIUM]

**File/line:** config/learning_loop.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Dead YAML — no loader references it

**Impact:**

> Operator-editable file has no runtime effect

**Suggested fix:**

> Fix via H2-H13 (wire into load_config) OR delete file

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 9: `H2-H15` [MEDIUM]

**File/line:** config/regime.yaml + config/system*.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> No regime_intelligence section in any system YAML; regime uses all Pydantic defaults. Defaults luckily match standalone but channel is broken

**Impact:**

> Same class of bug as H2-H13

**Suggested fix:**

> Wire regime.yaml into load_config OR move values into system_live.yaml

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 10: `H2-DEAD02` [MEDIUM]

**File/line:** config/regime.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Dead YAML — no loader references it (values duplicate standalone defaults)

**Impact:**

> Same as H2-DEAD01

**Suggested fix:**

> Fix via H2-H15 OR delete

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 11: `H2-DEAD04` [MEDIUM]

**File/line:** config/counterfactual.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Dead YAML (values duplicate system_live.yaml)

**Impact:**

> Low risk but file exists with no effect

**Suggested fix:**

> Delete OR wire into load_config

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 12: `H2-DEAD03` [MEDIUM]

**File/line:** config/overflow.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Dead YAML; runtime reads config.system.overflow from system.yaml. Has broker_capacity: 50 while runtime config has 30 (D-05)

**Impact:**

> Source of D-05 drift

**Suggested fix:**

> Fix via H2-D05 merge strategy OR delete

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 13: `H2-S10` [LOW]

**File/line:** config/scanner.yaml (fmp_scanner.min_volume)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Field exists with default 500000 but annotated "Reserved for future use (Sprint 23+); current FMP endpoints do not return volume"

**Impact:**

> Cosmetic but confusing — operator tunes min_volume to no effect

**Suggested fix:**

> Delete the field until Sprint 23+ follows through

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 14: `H2-S01` [CRITICAL]

**File/line:** config/strategies/*.yaml (12 of 15)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `benchmarks.min_sharpe` YAML key silently dropped — Pydantic field is `min_sharpe_ratio`. 12 strategy benchmark configs affected; orb_breakout/orb_scalp/red_to_green use the correct key

**Impact:**

> Benchmark gates use Pydantic default 0.0, not configured 0.3

**Suggested fix:**

> Rename YAML key `min_sharpe` → `min_sharpe_ratio` in all 12 affected strategy YAMLs

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 15: `H2-S09` [LOW]

**File/line:** config/strategies/*.yaml (13 of 15)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> 13 strategies have no operating_conditions section; "not yet constrained" comment indicates deliberate deferral

**Impact:**

> Config-design debt signal; no regime gating on most strategies

**Suggested fix:**

> Decide: either activate regime gating per strategy OR remove the TODO comments as "won't do"

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 16: `H2-S08` [MEDIUM]

**File/line:** config/strategies/*.yaml (9 non-ABCD pattern strategies)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> pattern_class field silently dropped on non-ABCD strategies; only ABCDConfig has the field

**Impact:**

> Operator could add pattern_class to any pattern YAML thinking it overrideable; it is not

**Suggested fix:**

> Either add pattern_class to all pattern *Config classes OR remove from ABCDConfig

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 17: `H2-S03` [MEDIUM]

**File/line:** config/strategies/*.yaml (all 15)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> 7 extra fields in backtest_summary block (data_source, universe_size, etc.) silently dropped

**Impact:**

> Documentary fields dropped; frontend uses only basic fields

**Suggested fix:**

> Either extend BacktestSummaryConfig Pydantic OR remove undocumented fields from YAMLs

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 18: `H2-D06` [MEDIUM]

**File/line:** config/system.yaml vs config/historical_query.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> cache_dir divergence: system.yaml data/databento_cache (non-consolidated), historical_query.yaml data/databento_cache_consolidated (correct)

**Impact:**

> Operator repoint pending — known item per project-knowledge

**Suggested fix:**

> Update system.yaml and system_live.yaml cache_dir to consolidated path (if/when operator decides)

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

### Finding 19: `H2-DEAD06` [MEDIUM]

**File/line:** config/vix_regime.yaml
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Dead YAML (values duplicate Pydantic defaults which happen to match)

**Impact:**

> Similar to H2-H16

**Suggested fix:**

> Wire OR delete

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-16-config-consistency**`.

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
| ... | ~~description~~ **RESOLVED FIX-16-config-consistency** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-16-config-consistency**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-16): config/ consistency sweep

Addresses audit findings:
- DEF-109 [LOW]: V1 trailing stop config dead code
- H2-S06 [MEDIUM]: ScannerConfig Pydantic only has scanner_type/static_symbols; 3 nested scanner blocks in YAML silently dropped
- H2-H10 [MEDIUM]: Hidden-ish default empty string; if operator boots with system
- H2-H11 [MEDIUM]: Uses str not StrategyMode enum; misspellings (e
- H2-S02 [CRITICAL]: Variant params not validated against target pattern — any typo silently dropped
- H2-S04 [MEDIUM]: Variants list-element dict shape not validated; extra="forbid" promise at top level broken
- H2-H13 [MEDIUM]: No learning_loop section in any system YAML; Learning Loop uses all Pydantic defaults, not learning_loop
- H2-DEAD01 [MEDIUM]: Dead YAML — no loader references it
- H2-H15 [MEDIUM]: No regime_intelligence section in any system YAML; regime uses all Pydantic defaults
- H2-DEAD02 [MEDIUM]: Dead YAML — no loader references it (values duplicate standalone defaults)
- H2-DEAD04 [MEDIUM]: Dead YAML (values duplicate system_live
- H2-DEAD03 [MEDIUM]: Dead YAML; runtime reads config
- H2-S10 [LOW]: Field exists with default 500000 but annotated "Reserved for future use (Sprint 23+); current FMP endpoints do not retur
- H2-S01 [CRITICAL]: 'benchmarks
- H2-S09 [LOW]: 13 strategies have no operating_conditions section; "not yet constrained" comment indicates deliberate deferral
- H2-S08 [MEDIUM]: pattern_class field silently dropped on non-ABCD strategies; only ABCDConfig has the field
- H2-S03 [MEDIUM]: 7 extra fields in backtest_summary block (data_source, universe_size, etc
- H2-D06 [MEDIUM]: cache_dir divergence: system
- H2-DEAD06 [MEDIUM]: Dead YAML (values duplicate Pydantic defaults which happen to match)

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-16-config-consistency**`
