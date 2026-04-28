# Sprint 31.91, Session 2b.1 — Close-Out Report

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → **2b.1** → 2b.2 → 2c.1 → 2c.2 → 2d).
> **Position in track:** Second session — broker-orphan branch + alert taxonomy + cycle-counter infrastructure.
> **Verdict:** PROPOSED_CLEAR (pending Tier 2).
> **Date:** 2026-04-27.

## Summary

Adds the broker-orphan branch to `OrderManager.reconcile_positions`. A
**broker-orphan** is a symbol the broker reports a non-zero position for
that ARGUS has no `_managed_positions` entry for. The branch dispatches
by `recon_pos.side`:

- **SELL (broker-orphan SHORT)** → CRITICAL `phantom_short`
  `SystemAlertEvent`. This is the DEF-204 detection signal. ARGUS is
  long-only; a broker-side short is an OCA-leak signature or external
  intervention.
- **BUY (broker-orphan LONG)** → cycle-counter increment + cycle-1/2
  WARNING (likely transient eventual-consistency lag) → cycle ≥ 3
  `stranded_broker_long` alert with **M2 exponential-backoff** schedule
  `[3, 6, 12, 24, 48]` then every 60 cycles thereafter (~hourly cap if
  reconciliation runs ~once per minute).

State infrastructure: two new per-symbol dicts on `OrderManager` —
`_broker_orphan_long_cycles` (consecutive-cycle count) and
`_broker_orphan_last_alerted_cycle` (exp-backoff bookkeeping). Both
clear on broker-zero observation (orphan resolved at broker side) and
on session reset (`reset_daily_state`).

Session 2b.1 is **detection-only**. It does NOT yet:
- Block new entries on a phantom-short-gated symbol (Session 2c.1).
- Wire side-aware count-filter reads at the four
  `broker_positions[sym]` consumer sites (Session 2b.2).

The existing ARGUS-orphan branch (internal > 0, broker == 0) is
preserved untouched. DEC-369 / DEC-370 broker-confirmed immunity is
preserved by construction — the new branch's
`if symbol in self._managed_positions: continue` guard filters out any
position ARGUS owns (broker-confirmed positions live in
`_managed_positions`, so they never reach the orphan-handling branch).

The implementation also adds an optional
`metadata: dict[str, Any] | None = None` field to `SystemAlertEvent`
(DEF-213 partial). Session 2b.1's two new emitters populate `metadata`
structurally with `symbol`, `shares`, `side`, `consecutive_cycles`,
`detection_source` so HealthMonitor (Session 5a.1) and frontend
consumers can read typed keys instead of parsing message strings.
Session 5a.1's Pre-Flight Check 7 explicitly accommodates this prior
addition ("If the field IS present, skip Requirement 0"); migration of
the pre-existing emitters (Databento dead-feed,
`_emit_cancel_propagation_timeout_alert`) remains in 5a.1's scope.

## Files Modified

| File | Change | Approx. line range |
|------|--------|---------|
| `argus/core/events.py` | `SystemAlertEvent` gains optional `metadata: dict[str, Any] \| None = None` field (DEF-213 partial; matches DEF-213's suggested shape so 5a.1 Pre-Flight 7 detects "field already present" and skips Requirement 0). | `:425-433` |
| `argus/core/config.py` | `ReconciliationConfig` gains `broker_orphan_alert_enabled: bool = True` field. | `:240-247` |
| `config/system_live.yaml` | Explicit `broker_orphan_alert_enabled: true` (explicit > implicit for safety-critical config). | `:192-194` |
| `config/system.yaml` | Explicit `broker_orphan_alert_enabled: true`. | `:58-60` |
| `argus/execution/order_manager.py` | `+_broker_orphan_long_cycles` + `+_broker_orphan_last_alerted_cycle` state on `__init__`; `+_handle_broker_orphan_short` + `+_handle_broker_orphan_long` async helpers; broker-orphan branch + cleanup-on-zero loop appended to `reconcile_positions`; counter clear in `reset_daily_state`. | init at `:364-378`; helpers at `:2204-2335`; reset_daily_state at `:3408-3413`; orphan branch at `:3645-3697` |
| `tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py` | NEW — 6 tests covering the broker-orphan branch + alert taxonomy + M2 lifecycle. | `+475 LOC` |
| `tests/execution/order_manager/test_reconciliation_log.py` | Filter `summary_messages` by the `Position reconciliation:` prefix to preserve original test intent — the per-symbol-mismatch summary remains a single line, but the new branch's cycle-1 long-orphan WARNINGs are a separate log family. | `:51-67` |
| `tests/execution/order_manager/test_reconciliation_redesign.py` | `test_reconciliation_config_fields_recognized` updated `expected_keys` set to include the new `broker_orphan_alert_enabled` field. | `:498-518` |

## Tests Added

All six tests live in
`tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py`.
The tests are revert-proof for the Session 2b.1 changes — the branch
ordering, the alert taxonomy, the cycle-counter lifecycle.

1. **`test_broker_orphan_short_emits_phantom_short_alert`** —
   Protects: a broker-orphan SHORT emits exactly one CRITICAL
   `phantom_short` `SystemAlertEvent` and a `BROKER ORPHAN SHORT`
   CRITICAL log line containing the symbol. Reverting the SELL branch
   (or downgrading the alert severity) makes this test fail.

2. **`test_broker_orphan_short_alert_payload_shape`** —
   Protects: `metadata` carries `symbol`, `shares=100`, `side="SELL"`,
   `detection_source="reconciliation.broker_orphan_branch"`. Reverting
   the metadata wiring (or shifting the encoding into the message
   string) makes this test fail.

3. **`test_broker_orphan_alert_config_flag_disables`** —
   Protects: `broker_orphan_alert_enabled=False` suppresses both the
   alert event and the CRITICAL log line. Removing the gate at the
   handler entry point makes this test fail.

4. **`test_broker_orphan_long_cycle_1_warning_only`** —
   Protects: cycle 1 emits a `Broker-orphan LONG cycle 1` WARNING and
   no `stranded_broker_long` alert; the counter increments to 1.
   Reverting the cycle-N < 3 early-return makes this test fail.

5. **`test_broker_orphan_long_cycle_3_emits_stranded_alert`** —
   Protects: 3 successive cycles produce exactly one
   `stranded_broker_long` alert at cycle 3 with metadata
   `consecutive_cycles=3`, `severity="warning"`. Reverting the cycle ≥
   3 emission gate makes this test fail.

6. **`test_broker_orphan_long_cycles_cleanup_on_zero_exponential_backoff_session_reset`** —
   Composite M2-lifecycle anchor with three sub-behaviors:
   - **Cleanup on broker-zero:** AAPL persists 3 cycles → alert at
     cycle 3 → broker reports zero → counter clears for AAPL.
   - **Exp-backoff:** MSFT persists 50 cycles → alerts fire at exactly
     `{3, 6, 12, 24, 48}`, no spurious fires at any other cycle.
   - **Session reset:** TSLA persists 5 cycles (alert at 3) →
     `reset_daily_state()` → counters empty → re-running the orphan
     re-fires at cycle 3 of the new session.

   Reverting any of the three M2 sub-behaviors makes this test fail at
   the corresponding sub-assertion.

## git diff --stat

```
 argus/core/config.py                                           |   8 +
 argus/core/events.py                                           |  10 +
 argus/execution/order_manager.py                               | 202 +++++++++++++++++++++
 config/system.yaml                                             |   3 +
 config/system_live.yaml                                        |   3 +
 tests/execution/order_manager/test_reconciliation_log.py       |  20 +-
 tests/execution/order_manager/test_reconciliation_redesign.py  |  11 +-
 tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py | 475 + (new file)
 8 files changed, 724 insertions(+), 8 deletions(-)
```

## Test Evidence

**Scoped suite (per DEC-328 — Session 3+ scoped is fine):**

```
$ python -m pytest tests/execution/ -n auto -q
…
468 passed, 2 warnings in 6.50s
```

Baseline (pre-2b.1): 462 passing. Delta: +6 (the six new
`test_session2b1_broker_orphan_alerts.py` tests). RULE-019 satisfied.

**Full suite (verifying no broader regressions, also satisfies the
sprint's Test Baseline Invariant 5):**

```
$ python -m pytest --ignore=tests/test_main.py -n auto -q
…
5139 passed, 23 warnings in 55.11s
```

Session 2a's close-out reported `tests_total_after: 5133`. Session
2b.1 delta: +6 → 5139. Baseline invariant 5,080 ≤ 5,139 satisfied.
Pre-existing flakes (DEF-150 / DEF-167 / DEF-171 / DEF-190 / DEF-192)
are unaffected; the run finishes green.

**Six new tests (isolated):**

```
$ python -m pytest tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py -v
…
6 passed in 0.05s
```

## Do-not-modify Audit

| Region | Edits? |
|---|---|
| `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) | **0** — diff hunks land at `:361-376` (init), `:2185-2202` (helpers prepended just below `_emit_cancel_propagation_timeout_alert`), `:3261-3267` (`reset_daily_state`), `:3490-3545` (orphan branch in `reconcile_positions`). All four ranges sit OUTSIDE the protected block. |
| `argus/main.py` | **0** — Session 2a's call-site edit was its scoped exception; 2b.1 leaves `main.py` untouched. The reconciliation contract is consumed via Session 2a's existing typed dict. |
| `argus/models/trading.py` `Position` class | **0** |
| `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py` | **0** |
| `argus/core/risk_manager.py`, `argus/core/health.py` | **0** (Session 2b.2's territory) |
| `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md` | **0** |
| `workflow/` submodule | **0** |

## Discovered Edge Cases

1. **`SystemAlertEvent` schema gap (DEF-213 partial — anticipated).** The
   spec acknowledged that the consumer code in 5a.1 references
   `event.metadata` while the schema doesn't yet have the field. 5a.1's
   Pre-Flight Check 7 explicitly handles "field already present" by
   skipping Requirement 0 and proceeding to Requirement 1. The
   `dict[str, Any] | None = None` shape adopted here matches DEF-213's
   suggested shape exactly, so 5a.1's atomic migration of the two
   pre-existing emitters (Databento dead-feed at
   `argus/data/databento_data_service.py:279`,
   `_emit_cancel_propagation_timeout_alert` at `order_manager.py:2163`)
   can proceed unchanged. **No semantic conflict; no scope creep.**

2. **EventBus dispatch is async-via-`asyncio.create_task`.** The first
   round of tests passed cycle-1 / cycle-2 cases (the WARNING fired
   synchronously) but failed on cycle-3 alert capture because the
   subscriber task hadn't run yet. Resolution: a
   `_reconcile_and_drain(om, broker_positions)` test helper that runs
   `await om._event_bus.drain()` after each `reconcile_positions` call.
   This mirrors the pattern used by `test_broker_only_paths_safety.py`
   (`tests/execution/test_broker_only_paths_safety.py:359, :421`).

3. **Two pre-existing tests required minimal updates** (regression
   acknowledgments, not source-of-truth changes):
   - `test_reconciliation_log.py::test_reconciliation_summary_single_line`
     filters the WARNING-message list by the `Position reconciliation:`
     prefix to preserve its original intent (per-symbol-mismatch
     summary collapses to a single line). The new branch's cycle-1
     long-orphan WARNINGs are a different log family; they don't
     compromise the per-symbol consolidation contract that this test
     enforces.
   - `test_reconciliation_redesign.py::test_reconciliation_config_fields_recognized`
     updates `expected_keys` to include the new
     `broker_orphan_alert_enabled` field. The test's purpose is to
     enforce the canonical field set; the canonical set grew by one.

## Deferred Items

None opened. Session 2b.1's scope is fully closed:
- All six tests green.
- Full-suite green at 5139.
- DEC-369 / DEC-370 immunity preserved by construction.
- Atomic schema extension (`SystemAlertEvent.metadata`) complete; 5a.1
  inherits the unchanged migration scope for pre-existing emitters.

Items already filed elsewhere that this session does NOT yet address
(intentionally — they're in downstream sessions):
- **Session 2b.2** — side-aware count-filter reads at the four
  `broker_positions[sym]` consumer sites (Risk Manager max-concurrent
  cap, HealthMonitor reconciliation-cycle handlers, etc.).
- **Session 2c.1** — per-symbol entry gate (block new entries on
  `phantom_short`-detected symbols) + SQLite persistence of gate state
  for restart preservation.
- **Session 5a.1** — HealthMonitor consumer subscription + the Databento
  / `_emit_cancel_propagation_timeout_alert` emitter migrations to
  populate `metadata` structurally.

## Verdict JSON

```json
{
  "session": "2b.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": 5139,
  "files_modified": [
    "argus/core/events.py",
    "argus/core/config.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "argus/execution/order_manager.py",
    "tests/execution/order_manager/test_reconciliation_log.py",
    "tests/execution/order_manager/test_reconciliation_redesign.py",
    "tests/execution/order_manager/test_session2b1_broker_orphan_alerts.py"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation"
}
```
