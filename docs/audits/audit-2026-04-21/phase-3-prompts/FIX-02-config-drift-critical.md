# Fix Session FIX-02-config-drift-critical: Config drift — overflow broker_capacity

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 2
**Files touched:** `config/overflow.yaml`, `config/system.yaml`
**Safety tag:** `weekend-only`
**Theme:** Resolves the overflow.broker_capacity divergence (config/overflow.yaml says 50, config/system_live.yaml says 30, runtime uses 30). Restores the Sprint 32.9 S3 intended cap.

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
marker (`audit(FIX-02): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `config/overflow.yaml`: 1 finding
- `config/system.yaml`: 1 finding

## Findings to Fix

### Finding 1: `P1-D1-C03` [CRITICAL]

**File/line:** [config/overflow.yaml](config/overflow.yaml) vs [config/system_live.yaml:177](config/system_live.yaml#L177)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Overflow `broker_capacity` divergence.** `config/overflow.yaml` has `broker_capacity: 50` (Sprint 32.9 S3 reduction from 60, tracked by `tests/test_overflow_routing.py:472`). `config/system_live.yaml` has `broker_capacity: 30`. Runtime reads `config.system.overflow.broker_capacity`, which is loaded exclusively from `system_live.yaml` per `load_config()` — so the live cap is **30**, not 50. CLAUDE.md claims "overflow.yaml `broker_capacity: 50`" and "overflow broker_capacity 60→50 (Sprint 32.9 S3)". The tested file is not the live file.

**Impact:**

> Signals start routing to counterfactual shadow tracking at 30 open positions instead of 50. In a session with >30 simultaneous live positions (the Sprint 32.9 stress case), 20 additional entries that Sprint 32.9 intended to *permit* are being diverted to shadow. All downstream filter-accuracy / promotion-eligibility metrics are skewed. Related: `CLAUDE.md` also says `max_concurrent_positions: 50` in `risk_limits.yaml` — which then has *more* risk headroom than the overflow gate will let the Order Manager consume.

**Suggested fix:**

> Same fix pattern as C2: either sync the `overflow.broker_capacity` value in `system_live.yaml` (and `system.yaml`) to `50`, or have `load_config()` merge standalone `config/overflow.yaml` over the `system:` overflow block. Add a parity test.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-02-config-drift-critical**`.

### Finding 2: `H2-D05` [MEDIUM]

**File/line:** config/system.yaml + config/overflow.yaml vs config/risk_limits.yaml
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> overflow.broker_capacity: system.yaml 30, overflow.yaml 50; risk_limits max_concurrent_positions: 50. 20-position window where signals silently drop to counterfactual tracking

**Impact:**

> HIGH severity operational drift; signals routed to shadow instead of broker

**Suggested fix:**

> Sync overflow.broker_capacity to 50 in system.yaml OR merge standalone YAML in load_config

**Audit notes:** Overflow broker_capacity divergence — primary driver of FIX-02

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-02-config-drift-critical**`.

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
| ... | ~~description~~ **RESOLVED FIX-02-config-drift-critical** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-02-config-drift-critical**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-02): config drift: overflow broker_capacity

Addresses audit findings:
- P1-D1-C03 [CRITICAL]: Overflow 'broker_capacity' divergence
- H2-D05 [MEDIUM]: overflow

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-02-config-drift-critical**`
