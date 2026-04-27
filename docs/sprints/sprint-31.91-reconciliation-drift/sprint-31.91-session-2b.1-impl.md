# Sprint 31.91, Session 2b.1: Broker-Orphan SHORT Branch + `phantom_short` Alert + Cycle Infrastructure

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → **2b.1** → 2b.2 → 2c.1 → 2c.2 → 2d).
> **Position in track:** Second session. Consumes Session 2a's typed contract; adds the broker-orphan branch + alert taxonomy + cycle-counter infrastructure.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-050 (CI green), RULE-019 (test-count must not decrease), and RULE-007 (out-of-scope discoveries) all apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py:3038-3039` — current orphan-loop check (where the new broker-orphan branch attaches; verify line)
   - `argus/execution/order_manager.py` — Session 2a's `ReconciliationPosition` dataclass (~:124) and updated `reconcile_positions` signature/body
   - `argus/core/events.py:405` — `SystemAlertEvent` definition (verify field shape)
   - `argus/core/config.py:229` — `ReconciliationConfig` Pydantic model (where new flag goes)
   - DEC-369 / DEC-370 — broker-confirmed immunity logic (search via `grep -n "_broker_confirmed" argus/execution/order_manager.py`)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D5 acceptance criteria (Session 2b.1 portion specifically — broker-orphan branch + alert + cycle infrastructure)

3. Run the scoped test baseline (DEC-328 — Session 3+ of sprint, scoped is fine):

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

   Expected: all passing (Session 2a's close-out confirmed full suite).

4. Verify you are on the correct branch: **`main`**.

5. Verify Session 2a's deliverables are present on `main`:

   ```bash
   grep -n "class ReconciliationPosition" argus/execution/order_manager.py
   grep -n "reconcile_positions" argus/execution/order_manager.py | head -3
   grep -n "ReconciliationPosition" argus/main.py
   ```

   All three must match. If not, halt — Session 2a has not landed.

6. **Pre-flight grep — verify `_broker_confirmed` immunity is intact (anti-regression check):**

   ```bash
   grep -n "_broker_confirmed" argus/execution/order_manager.py
   ```

   Read the existing patterns. Session 2b.1's broker-orphan branch must NOT trigger on broker-confirmed positions; the immunity logic must remain untouched.

7. **Pre-flight grep — verify the orphan-loop site has not drifted:**

   ```bash
   grep -n -B 2 -A 5 "orphan" argus/execution/order_manager.py | head -40
   ```

   Confirm the loop body around `:3038-3039` is the iteration point where Session 2a's typed-dict consumption flows. If line drift > 5, halt and reconcile.

## Objective

Add the broker-orphan branch to the reconciliation orphan loop. "Broker-orphan" means: ARGUS has no `_managed_positions[symbol]` BUT the broker reports a non-zero position for that symbol. This is the inverse of the existing ARGUS-orphan branch (ARGUS thinks it has it; broker says it doesn't).

The branch dispatches by `side`:
- **Broker-orphan SHORT** (broker reports a SELL/short position ARGUS doesn't know about) → CRITICAL `phantom_short` alert. This is the DEF-204 detection signal.
- **Broker-orphan LONG cycle 1–2** → WARNING log only (transient state likely; could be eventual-consistency lag from a fill ARGUS hasn't processed yet).
- **Broker-orphan LONG cycle ≥3** → `stranded_broker_long` alert (warning severity; exponential-backoff re-alert: 3 → 6 → 12 → 24 cycles, capped at hourly per M2 disposition).

The cycle-counter infrastructure (`_broker_orphan_long_cycles: dict[str, int]`) tracks the consecutive-cycle counter per symbol with M2 lifecycle:
- Cleanup on broker-zero observation (the orphan resolves; counter clears).
- Exponential backoff for re-alerts (avoid alert spam on a long-running orphan).
- Session reset (counter clears on session start, not on ARGUS restart — restart preservation per Session 2c.1 SQLite persistence; THIS session does not yet persist the counter).

Session 2b.1 does NOT yet implement the per-symbol entry gate (Session 2c.1) or the side-aware count-filter sites (Session 2b.2). After Session 2b.1, ARGUS *detects* phantom shorts and *emits the alert*, but does NOT yet block new entries on the gated symbol. The detection-without-blocking interim state is intentional — Session 2b.2's count-filter sites need the alert taxonomy from 2b.1 to be in place first.

## Requirements

1. **Add `_broker_orphan_long_cycles: dict[str, int]` state field** to `OrderManager.__init__()`:

   ```python
   # Sprint 31.91 Session 2b.1: per-symbol consecutive-cycle counter for
   # broker-orphan LONG positions. Used for cycle-3 stranded_broker_long
   # alert escalation with exponential backoff. NOT persisted in 2b.1
   # (Session 2c.1 adds SQLite persistence for the gate state, not this
   # counter — counter is session-scoped per M2).
   self._broker_orphan_long_cycles: dict[str, int] = {}

   # Sprint 31.91 Session 2b.1: tracks the last alert-cycle count for
   # exponential-backoff re-alerting (3 → 6 → 12 → 24, capped at 60 to
   # produce roughly hourly cap if a cycle is ~1 minute).
   self._broker_orphan_last_alerted_cycle: dict[str, int] = {}
   ```

2. **Extend the orphan loop body in `reconcile_positions`** (around `:3038-3039` per DISCOVERY; verify):

   The existing loop iterates over either `_managed_positions` or `broker_positions` (or both); identify the iteration that surfaces broker-side symbols. Add a new branch:

   ```python
   # NEW (Session 2b.1): broker-orphan branch
   for symbol, recon_pos in broker_positions.items():
       if symbol in self._managed_positions:
           continue  # not an orphan — managed position exists

       # Skip broker-confirmed paths immune via DEC-369/DEC-370.
       # (Defensive: this should never trigger because broker-confirmed
       # positions are always in _managed_positions, but the explicit
       # check makes the immunity invariant audit-grep-friendly.)
       if self._is_broker_confirmed_immune(symbol):
           continue  # use whichever helper exists; if none, this branch
                     # is a no-op because the prior check filtered already.

       # Branch on side
       if recon_pos.side == OrderSide.SELL:
           # Phantom short — DEF-204 detection signal
           self._handle_broker_orphan_short(symbol, recon_pos)
           # Reset the long counter for safety (symbol could flip in pathological cases)
           self._broker_orphan_long_cycles.pop(symbol, None)
           self._broker_orphan_last_alerted_cycle.pop(symbol, None)
       elif recon_pos.side == OrderSide.BUY:
           # Long orphan — increment counter and decide WARNING vs alert
           cycle = self._broker_orphan_long_cycles.get(symbol, 0) + 1
           self._broker_orphan_long_cycles[symbol] = cycle
           self._handle_broker_orphan_long(symbol, recon_pos, cycle)
       else:
           # Defensive: ReconciliationPosition.__post_init__ rejects None,
           # so this branch is unreachable in practice. Log if hit.
           self._logger.error(
               "Broker-orphan with unrecognized side for %s: side=%r. "
               "ReconciliationPosition __post_init__ should have rejected this.",
               symbol, recon_pos.side,
           )

   # NEW (Session 2b.1): clear the long-cycle counter for symbols that
   # are no longer in broker_positions (orphan resolved at broker side).
   resolved_symbols = set(self._broker_orphan_long_cycles.keys()) - set(broker_positions.keys())
   for symbol in resolved_symbols:
       self._broker_orphan_long_cycles.pop(symbol, None)
       self._broker_orphan_last_alerted_cycle.pop(symbol, None)
       self._logger.info("Broker-orphan LONG resolved (broker reports zero): %s", symbol)
   ```

   Notes:
   - The `_is_broker_confirmed_immune` helper may not exist; if Session 2a left the immunity check inline in `reconcile_positions`, mirror the same pattern. Per RULE-007, do NOT extract a new helper unless the spec requires.
   - The branch ordering matters: SHORT before LONG ensures the unbounded-risk path takes the alert-emission code path before any state-pruning logic runs.

3. **Implement `_handle_broker_orphan_short(symbol, recon_pos)`:**

   ```python
   def _handle_broker_orphan_short(
       self, symbol: str, recon_pos: "ReconciliationPosition"
   ) -> None:
       """Emit phantom_short alert. Sprint 31.91 Session 2b.1 (D5). Gate
       engagement deferred to Session 2c.1.
       """
       if not self._config.reconciliation.broker_orphan_alert_enabled:
           return  # config-gated; allow operator to disable for testing

       self._logger.critical(
           "BROKER ORPHAN SHORT DETECTED: %s shares=%d. Broker reports short "
           "position ARGUS has no managed_positions entry for. This is the "
           "DEF-204 signature — investigate via scripts/ibkr_close_all_positions.py "
           "and check Sprint 31.91 runbook (live-operations.md Phantom-Short "
           "Gate Diagnosis).",
           symbol, recon_pos.shares,
       )

       alert = SystemAlertEvent(
           severity="critical",
           source="reconciliation",
           alert_type="phantom_short",
           # Use whichever payload-shape pattern the existing SystemAlertEvent
           # callers use (the spec says symbol/shares/side as payload fields,
           # but the actual schema may use a `metadata` dict).
           # Verify against argus/core/events.py:405.
           message=(
               f"Broker reports short position for {symbol} that ARGUS has "
               f"no managed_positions entry for. Shares: {recon_pos.shares}."
           ),
           metadata={
               "symbol": symbol,
               "shares": recon_pos.shares,
               "side": "SELL",
               "detection_source": "reconciliation.broker_orphan_branch",
           },
       )
       self._event_bus.publish(alert)  # use whichever publish API the existing
                                        # SystemAlertEvent emitters use.
   ```

4. **Implement `_handle_broker_orphan_long(symbol, recon_pos, cycle)` with M2 exponential-backoff:**

   ```python
   def _handle_broker_orphan_long(
       self, symbol: str, recon_pos: "ReconciliationPosition", cycle: int
   ) -> None:
       """Long-orphan handler. Sprint 31.91 Session 2b.1 (D5, M2 lifecycle):
       - cycle 1-2: WARNING log only
       - cycle >= 3: emit stranded_broker_long alert with exp-backoff re-alert
         (3 -> 6 -> 12 -> 24, capped at 60 cycles which is ~hourly).
       """
       if not self._config.reconciliation.broker_orphan_alert_enabled:
           return

       if cycle < 3:
           self._logger.warning(
               "Broker-orphan LONG cycle %d for %s shares=%d. Likely transient "
               "(eventual-consistency lag from a recent fill ARGUS has not "
               "yet processed). Will alert at cycle 3.",
               cycle, symbol, recon_pos.shares,
           )
           return

       # Cycle >= 3: check exp-backoff schedule
       last_alerted = self._broker_orphan_last_alerted_cycle.get(symbol, 0)
       # M2 exponential backoff: alert at cycles 3, 6, 12, 24, 48, then every 60
       # (60 is the hourly cap if reconciliation runs ~once per minute).
       schedule = [3, 6, 12, 24, 48]
       should_alert = False
       if last_alerted == 0:
           should_alert = (cycle == 3)
       else:
           # Find the next scheduled cycle after last_alerted
           next_in_schedule = next(
               (c for c in schedule if c > last_alerted), None
           )
           if next_in_schedule is not None:
               should_alert = (cycle >= next_in_schedule)
           else:
               # Past the schedule: hourly cap (every 60 cycles after last)
               should_alert = (cycle - last_alerted >= 60)

       if not should_alert:
           return

       self._broker_orphan_last_alerted_cycle[symbol] = cycle
       alert = SystemAlertEvent(
           severity="warning",
           source="reconciliation",
           alert_type="stranded_broker_long",
           message=(
               f"Broker reports long position for {symbol} that ARGUS has "
               f"no managed_positions entry for, persisting across {cycle} "
               f"reconciliation cycles. Shares: {recon_pos.shares}. Operator "
               f"should investigate (eventual-consistency window has elapsed)."
           ),
           metadata={
               "symbol": symbol,
               "shares": recon_pos.shares,
               "side": "BUY",
               "consecutive_cycles": cycle,
               "detection_source": "reconciliation.broker_orphan_branch",
           },
       )
       self._event_bus.publish(alert)
   ```

5. **Add config field `broker_orphan_alert_enabled: bool = True`** to `ReconciliationConfig` in `argus/core/config.py:229`:

   ```python
   class ReconciliationConfig(BaseModel):
       # ... existing fields ...

       # Sprint 31.91 Session 2b.1
       broker_orphan_alert_enabled: bool = Field(
           default=True,
           description=(
               "When True, the reconciliation broker-orphan branch emits "
               "phantom_short and stranded_broker_long alerts. Disable only "
               "for controlled testing — production should always be True."
           ),
       )
   ```

   Update relevant YAMLs (`config/system_live.yaml`, `config/system_paper.yaml`, `config/system_dev.yaml` — verify which exist) with the new field at the explicit `True` value (don't rely on the default; explicit > implicit for safety-critical config).

6. **Session reset (per M2):** the counter and last-alerted maps must clear on session start. Find the existing session-start hook in `OrderManager` (likely `on_session_start` or similar) and add:

   ```python
   def on_session_start(self) -> None:
       # ... existing reset logic ...
       self._broker_orphan_long_cycles.clear()
       self._broker_orphan_last_alerted_cycle.clear()
   ```

   If no such hook exists, the SessionStartEvent subscriber must be located and the reset added. Per RULE-007, do not invent a new hook structure.

7. **DEC-369 / DEC-370 broker-confirmed immunity preserved.** Confirm the existing `_broker_confirmed=True` positions are still skipped by the orphan loop. Run pre-existing immunity tests.

8. **No edits to do-not-modify regions.** Specifically:
   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix)
   - `argus/main.py` (Session 2a's call-site edit was the scoped exception; 2b.1 should not touch main.py)
   - `argus/models/trading.py` Position class
   - `argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`
   - `argus/core/risk_manager.py`, `argus/core/health.py` (Session 2b.2 modifies; not 2b.1)
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule

## Tests (~6 new pytest)

1. **`test_broker_orphan_short_emits_phantom_short_alert`**
   - Setup: `_managed_positions` empty for AAPL; `broker_positions = {"AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.SELL, shares=100)}`.
   - Trigger `reconcile_positions(broker_positions)`.
   - Assert: `SystemAlertEvent` with `alert_type="phantom_short"`, `severity="critical"` published exactly once.
   - Assert: CRITICAL log line contains "BROKER ORPHAN SHORT DETECTED" and the symbol.

2. **`test_broker_orphan_short_alert_payload_shape`**
   - Same setup as Test 1; capture the published `SystemAlertEvent`.
   - Assert: `metadata["symbol"] == "AAPL"`, `metadata["shares"] == 100`, `metadata["side"] == "SELL"`, `metadata["detection_source"] == "reconciliation.broker_orphan_branch"`, `source == "reconciliation"`.

3. **`test_broker_orphan_alert_config_flag_disables`**
   - Setup as Test 1, but with `config.reconciliation.broker_orphan_alert_enabled = False`.
   - Assert: NO alert published; NO CRITICAL log line.
   - This guards against accidentally hard-coding the alert path.

4. **`test_broker_orphan_long_cycle_1_warning_only`**
   - Setup: long orphan AAPL on first cycle.
   - Trigger `reconcile_positions` once.
   - Assert: WARNING log line emitted (cycle 1); NO `stranded_broker_long` alert.
   - Assert: `_broker_orphan_long_cycles["AAPL"] == 1`.

5. **`test_broker_orphan_long_cycle_3_emits_stranded_alert`**
   - Setup: long orphan AAPL persists for 3 reconciliation cycles.
   - Trigger `reconcile_positions` 3 times in succession (mock the loop or call the method directly thrice with the same `broker_positions`).
   - Assert: 1 `stranded_broker_long` alert (severity=warning) emitted on the 3rd cycle, NOT the 1st or 2nd.
   - Assert: alert payload `metadata["consecutive_cycles"] == 3`.

6. **`test_broker_orphan_long_cycles_cleanup_on_zero_exponential_backoff_session_reset`** (M2 lifecycle)
   - Composite test exercising all three M2 sub-behaviors:
     - **Cleanup on broker-zero:** orphan AAPL persists 3 cycles → alert fires at cycle 3 → broker reports zero on cycle 4 → counter clears for AAPL → no alert on cycle 5.
     - **Exp-backoff:** orphan MSFT persists indefinitely → alerts at cycles 3, 6, 12, 24, 48; NO alert at cycles 4, 5, 7-11, 13-23, 25-47.
     - **Session reset:** orphan TSLA persists 5 cycles → SessionStartEvent fires → counter clears for TSLA → alert re-fires at cycle 3 from new session start.
   - Assert each sub-behavior independently. This test is the M2 lifecycle anchor.

## Definition of Done

- [ ] `_broker_orphan_long_cycles` and `_broker_orphan_last_alerted_cycle` state fields initialized in `OrderManager.__init__`.
- [ ] Broker-orphan branch added to the reconciliation orphan loop.
- [ ] `_handle_broker_orphan_short` emits `phantom_short` alert with full metadata.
- [ ] `_handle_broker_orphan_long` implements cycles 1–2 WARNING / cycle ≥3 alert with M2 exp-backoff (3→6→12→24→48→every 60).
- [ ] Counter cleanup on broker-zero observation.
- [ ] Counter session-reset hook wired.
- [ ] `broker_orphan_alert_enabled` config field added with default `True`; YAML files updated.
- [ ] DEC-369 / DEC-370 broker-confirmed immunity preserved.
- [ ] 6 new tests; all passing.
- [ ] CI green (scoped suite).
- [ ] All do-not-modify list items show zero `git diff`.
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.1-closeout.md`.

## Close-Out Report

Write `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.1-closeout.md` with the standard structure (Files modified / Tests added / git diff --stat / Test evidence / Do-not-modify audit / Discovered Edge Cases / Deferred Items / Verdict JSON). Verdict JSON:

```json
{
  "session": "2b.1",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": <fill>,
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/config.py",
    "config/system_live.yaml",
    "config/system_paper.yaml",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation"
}
```

## Tier 2 Review Invocation

Standard pattern. Provide @reviewer with the review-context.md, close-out path, diff range, scoped test command (`python -m pytest tests/execution/ -n auto -q`), and the do-not-modify list above. Reviewer template: **backend safety reviewer** (`templates/review-prompt.md`). Review report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2b.1-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Alert payload shape correctness.** Read `argus/core/events.py:405` to confirm the actual `SystemAlertEvent` schema; verify the alerts emitted by 2b.1 match exactly. Mismatch = silently broken downstream consumers (HealthMonitor in 5a.1).
2. **Cycle counter resets on broker-zero.** Test 6 verifies; reviewer additionally inspects the `resolved_symbols` cleanup loop and confirms it runs every reconciliation cycle (not just on a specific event).
3. **Exponential backoff calculation.** Walk through the schedule: cycles 3, 6, 12, 24, 48, then every 60 thereafter. Verify the `last_alerted` lookup logic doesn't misfire if `last_alerted` is between schedule entries.
4. **Session reset clears stale state.** Test 6's session-reset sub-behavior is the verification. Reviewer confirms the SessionStartEvent subscriber (or equivalent hook) is wired.
5. **DEC-369 / DEC-370 immunity preserved.** Run pre-existing immunity tests. Inspect the orphan-branch entry conditions: a `_broker_confirmed=True` position should never enter the broker-orphan branch (it's in `_managed_positions`, so the `if symbol in self._managed_positions: continue` guards it).
6. **Config gate works.** Test 3 verifies; reviewer confirms the gate is at the entry point of both handlers (`_handle_broker_orphan_short` and `_handle_broker_orphan_long`), not just one.
7. **No coupling to Session 2c.1's gate state.** Session 2b.1 emits the alert; it does NOT yet engage the per-symbol entry gate. Reviewer confirms `_phantom_short_gated_symbols` is NOT modified anywhere in 2b.1's diff.
8. **Health + broker-orphan double-fire (third-pass MEDIUM #8 cross-reference).** This session lays the foundation for the double-fire that will be addressed in Session 2b.2 with operator-decided Option C (hybrid: both alerts fire, Health alert message cross-references the active `stranded_broker_long`). 2b.1's job is to ensure the `stranded_broker_long` alert is queryable — i.e., HealthMonitor in 5a.1 will be able to look up active alerts by symbol. Reviewer confirms the alert metadata includes `symbol` so 2b.2's Health-alert cross-reference can find it.

## Sprint-Level Regression Checklist (for @reviewer)

Of particular relevance to Session 2b.1:

- **Invariant 5 (5,080 baseline holds):** PASS — expected ≥ 5,119 (entry baseline 5,113 + 6 new tests).
- **Invariant 8 (Risk Manager Check 0 unchanged):** PASS — `risk_manager.py` zero edits in 2b.1.
- **Invariant 14 (Monotonic-safety property):** Row "After Session 2b.1" — Recon detects shorts = "partial (alert only)". Gate engagement and side-aware count filters are still NO; those land in 2c.1 and 2b.2.
- **Invariant 15 (do-not-modify list):** PASS — no scoped exception in 2b.1.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A3** (post-merge paper session phantom-short accumulation) — 2b.1 is the first session after which a paper-session debrief should show the alert firing on phantom-short detection. Operator's daily `ibkr_close_all_positions.py` continues to mitigate; the alert is now observable.
- **B1, B3, B4, B6** — standard halt conditions.
- **C7** (false-positive on a legitimate broker-orphan that ARGUS just hasn't processed yet — eventual-consistency lag) — the cycle-1-2 WARNING handling is the bound; if false-positives still occur at cycle 3+, that's an out-of-scope discovery that requires operator dispositioning of the cycle threshold.

---

*End Sprint 31.91 Session 2b.1 implementation prompt.*
