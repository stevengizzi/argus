# Sprint 31.92 — Adversarial Review Round 3 — Findings

> Verdict author: Round 3 reviewer (Claude.ai conversation, full-scope per Outcome C)
> Date: 2026-04-29
> Outcome: **B** (Round produced revisions — 1 Critical + 5 High + 4 Medium + 2 Low)
> Decision 7 routing: **(a) primitive-semantics-class Critical → Phase A re-entry per Outcome C** — *flagged ambiguous-class per the input package's "encouraged to flag ambiguous-class findings explicitly and let the operator disposition the routing rather than self-routing" guidance; reviewer's recommended routing is (a), but operator may elect (b) with explicit log-entry and the proposed RSK in C-R3-1's "if (b) selected" branch.*
> A14 fired: **yes** (Round 3 produced ≥1 Critical of FAI's primitive-semantics class)
> FAI self-falsifiability clause: **TRIGGERED** (4th occurrence — Round 1 asyncio yield-gap / Round 2 `ib_async` cache freshness / Phase A Tier 3 callback-path bookkeeping atomicity / Round 3 `positionEndEvent` per-caller correlation)

---

## Critical findings

### C-R3-1 — `Broker.refresh_positions()` is implemented atop a session-global `positionEndEvent` with no per-caller correlation; concurrent callers can desynchronize without raising

**Severity:** Critical
**Primitive-semantics class:** **yes** (recommended) / **borderline** (operator may dispute)
**Affected FAI entries:** none — **new primitive-semantics surface** (`ib_async`'s session-global event correlation under concurrent callers; FAI #2 covers single-caller cache convergence across serial reconnect cycles, NOT concurrent caller correlation)

**Reviewer's argument:**

The `IBKRBroker.refresh_positions()` implementation reproduced verbatim in the input package § 7 is:

```python
async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
    end_event = asyncio.Event()
    def _on_position_end():
        end_event.set()
    self._ib.positionEndEvent += _on_position_end
    try:
        self._ib.reqPositions()
        await asyncio.wait_for(end_event.wait(), timeout=timeout_seconds)
    finally:
        self._ib.positionEndEvent -= _on_position_end
```

IBKR's `REQ_POSITIONS` API request carries **no `reqId` correlation token** (unlike `reqMktData` / `reqAccountUpdates` / order-related requests). It is a global "stream me all current positions" request. IBKR responds by emitting a sequence of `position()` callbacks followed by a single `positionEnd()` terminator. ib_async exposes these as `positionEvent` and `positionEndEvent` — **session-global subscription points with no per-caller correlation**.

Concrete failure trace under Sprint 31.92's design:

1. **t=0ms** — Coroutine A enters `refresh_positions()` for position P1 (AC2.5 suppression-timeout fallback firing on PCT-class locate-rejection).
   - `end_event_A = asyncio.Event()`
   - `positionEndEvent += _on_position_end_A`
   - `self._ib.reqPositions()` → IBKR begins streaming positions
   - `await wait_for(end_event_A.wait(), timeout=5.0)`

2. **t=2ms** — Coroutine B enters `refresh_positions()` for position P2 (different ManagedPosition, same suppression-storm cluster — entirely realistic given 22 shadow variants and the empirically-observed Apr 28 60-phantom-short cluster).
   - `end_event_B = asyncio.Event()`
   - `positionEndEvent += _on_position_end_B` (now 2 callbacks subscribed)
   - `self._ib.reqPositions()` — IBKR's behavior here is implementation-defined: typically de-duplicates while a stream is in flight (returns the SAME stream A is consuming) or restarts the stream.
   - `await wait_for(end_event_B.wait(), timeout=5.0)`

3. **t=15ms** — IBKR fires `positionEnd()` (terminating A's stream).
   - ib_async's `positionEndEvent` fires.
   - `_on_position_end_A` and `_on_position_end_B` BOTH fire.
   - `end_event_A.set()` AND `end_event_B.set()`.

4. **t=15ms+ε** — Both A's and B's `wait_for` return successfully. Both proceed to:
   ```python
   positions = self._broker.get_positions()  # local cache lookup
   ```

5. **The cache state at t=15ms reflects A's `reqPositions()` request response only.** B's `reqPositions()` was either de-duplicated (no second stream) or queued (second stream still in flight). B reads the cache as if synchronized with broker state for B's call — but B's call did NOT trigger an independent broker round-trip.

The downstream classification logic (Branch 1/2/3 in AC2.5) reads stale-for-B data. If P2's broker state CHANGED between A's reqPositions response (t=10ms) and B's intended-but-deduped reqPositions, B's classification is wrong:
- Branch 2 fires when broker shows expected-long, but the cache reflects pre-change state — false negative on a real phantom-short.
- Branch 1 fires when broker shows zero, but the cache hasn't refreshed — could mask an actual short.
- Branch 3 fires inappropriately, producing a false `phantom_short_retry_blocked` alert.

Branch 4 (`verification_stale: true`) does NOT catch this because `wait_for` returned **successfully** — there was no timeout, no exception. The defense-in-depth predicated on `refresh_positions()` raising-or-timing-out fails when the failure mode is "returned successfully but with cache that wasn't actually refreshed for THIS caller."

**Why this is FAI-class:**

The structural shape matches the three prior FAI-class misses exactly:

| Round | Missing primitive | Mechanism's implicit claim |
|-------|-------------------|---------------------------|
| 1 (asyncio yield-gap) | Single-event-loop serializes emit-side | The ceiling check + place call appear atomic |
| 2 (`ib_async` cache freshness) | `IB.positions()` is a broker round-trip | The cache reflects current broker state |
| Phase A T3 (callback-path atomicity) | Atomic-reserve protection covers ALL counter mutators | The L3 ceiling check reads consistent counter state |
| **Round 3 (`positionEndEvent` correlation)** | **`refresh_positions()` synchronizes broker round-trip per-caller** | **Each caller's `end_event` correlates with their own `reqPositions()` call** |

All four are: a runtime primitive's behavior whose violation silently produces the symptom class (stale classification → false alert OR missed phantom-short) the proposed fix claimed to address. None of the four are explicit in the spec; all four were assumed-without-justification.

The FAI's self-falsifiability clause states: *"If Round 3 (or any subsequent review) finds an additional primitive-semantics assumption load-bearing on the proposed mechanism not in this list, the inventory has failed — and the mechanism's adversarial-review verdict must be downgraded accordingly."* The clause has now been triggered for the **fourth** time.

**Why this might NOT be FAI-class (steelmanned for operator):**

The operator could reasonably argue:
- **(a) "concurrent callers of `refresh_positions()` aren't realistic at AC2.5 firing rates."** Counter: the Apr 28 paper-session debrief recorded **60 NEW phantom shorts** — these were observed clustering in time. AC2.5 timeout fallbacks on the 60 positions would have fired in clusters as their suppression windows expired together. Concurrent `refresh_positions()` calls under the empirically-falsifying scenario are not speculative.
- **(b) "ib_async's `positionEndEvent` may already serialize internally via Future."** Possible but unverified — and the spec doesn't reference the serialization. Even if ib_async does serialize, the unsynchronized callers will still reach `wait_for` returning successfully on someone else's `positionEnd`. Per-caller correlation is what's missing, regardless of whether ib_async serializes the underlying request.
- **(c) "this is an `ib_async` cache primitive — same class as FAI #2, not new."** The strongest steelman. FAI #2's text is: *"`ib_async`'s position cache catches up to broker state within `Broker.refresh_positions(timeout_seconds=5.0)` under all observed reconnect-window conditions."* The S3b spike measures `cache_staleness_p95_ms` etc. across N≥10 disconnect/reconnect cycles — **single-caller, serial cycles**. The spike does NOT exercise concurrent-caller behavior. Whether you call this an EXTENSION of FAI #2 or a NEW entry is a definitional question. Either way: the spec is silent on concurrent-caller behavior; the spike doesn't test it; the cross-layer test (CL-3) uses a single-caller fixture (`SimulatedBrokerWithRefreshTimeout`).

**Reviewer's recommendation on routing:** This is closer to a NEW entry than an extension of FAI #2 — FAI #2's falsifying spike (S3b) explicitly limits its scope to "reconnect-window axis only" (DEF-FAI-2-SCOPE) and Tier 3 item D documents the high-volume axis as out-of-scope. Concurrent callers are an axis-3 (different from steady-state high volume and from reconnect-window). **The cleanest disposition is FAI entry #10 added with a falsifying spike scheduled before sprint advances.**

If the operator elects (b) routing — **explicit ambiguous-class flag** — the RSK shape would be:

> **RSK-REFRESH-POSITIONS-CONCURRENT-CALLER (CRITICAL floor per Severity Calibration Rubric §"failure mode produces unrecoverable financial loss within single trading session"):** `Broker.refresh_positions()` is implemented atop a session-global `positionEndEvent` with no per-caller correlation. Under concurrent callers (realistic at AC2.5 timeout-fallback firing rates during locate-rejection storms — empirically observed Apr 28 with 60 NEW phantom shorts clustering), one caller's `wait_for` may return successfully on another caller's `positionEnd`, leading to stale-for-this-caller cache reads in Branch 1/2/3 classification. Branch 4's refresh-failure detection does NOT catch this case because `wait_for` returns successfully. Mitigation: add a single-flight serialization wrapper (asyncio.Lock guarding `refresh_positions` body) at L2 — see "Proposed fix shape" below.

**Proposed disposition:** **PARTIAL ACCEPT (different)** — FAI miss is real; routing depends on whether operator classifies as new entry (FAI #10 → Decision 7 (a) Phase A re-entry) or extension of FAI #2 (RSK + ship per Decision 7 (b)).

**Proposed fix shape:**

There are two structurally distinct fixes; reviewer recommends the first as primary:

**Fix A — Single-flight serialization on `IBKRBroker.refresh_positions()` (preferred):**

```python
class IBKRBroker(Broker):
    def __init__(self, ...):
        self._refresh_positions_lock = asyncio.Lock()
        self._cache_synchronized_at: float = 0.0  # monotonic timestamp

    async def refresh_positions(self, *, timeout_seconds: float = 5.0) -> None:
        async with self._refresh_positions_lock:
            # Coalesce: if cache was synchronized within the last N ms by
            # a previous caller, return immediately without re-fetching.
            now = time.monotonic()
            if now - self._cache_synchronized_at < 0.250:  # 250ms coalesce window
                return
            end_event = asyncio.Event()
            def _on_position_end():
                end_event.set()
            self._ib.positionEndEvent += _on_position_end
            try:
                self._ib.reqPositions()
                await asyncio.wait_for(end_event.wait(), timeout=timeout_seconds)
                self._cache_synchronized_at = time.monotonic()
            finally:
                self._ib.positionEndEvent -= _on_position_end
```

The lock serializes concurrent callers; the coalesce window means rapid-succession calls return cheaply on the second-and-onward call (the cache IS fresh per the first caller's broker round-trip). **Note:** the coalesce window must be MUCH shorter than the suppression-timeout fallback firing rate — 250ms is well below any reasonable suppression value.

**Fix B — Per-caller correlation via reqId-tagged subscription wrapper (heavier, less preferred):**

Track each caller's expected position-stream with a sequence counter; only resolve `end_event` when N positions have been observed since the lock was taken. More invasive; requires understanding ib_async's ordering guarantees for `positionEvent`. Reviewer does not recommend.

**Required additions to FAI / regression checklist:**

- **FAI entry #10 (NEW):** *"`refresh_positions()` synchronizes broker round-trip per-caller — concurrent callers each correctly correlate their `wait_for` return with their own `reqPositions()` invocation, OR the implementation explicitly serializes concurrent callers (single-flight pattern)."* Status: **unverified — falsifying spike scheduled.** The spike: spawn N=20 coroutines, each calling `refresh_positions()` near-simultaneously (≤10ms separation), each WITHOUT serialization mitigation; assert that at least one caller reads stale-for-its-call cache (mocked-await injection between A's reqPositions and B's reqPositions, with deterministic broker state-change between). Then with the serialization mitigation enabled, assert the race is no longer observable.
- **CL-7 cross-layer test (NEW per Decision 5 floor + this finding):** Composite — N=2 concurrent AC2.5 fallbacks, broker state mutated between callers, assert no stale classification via Branch 2.
- **Cumulative diff bound recalibration:** `argus/execution/ibkr_broker.py` adds ~30–50 LOC for the serialization wrapper; budget to be reflected in S3b.

**Routing implication if operator agrees with reviewer (a):** Phase A re-entry — Phase B re-run + Phase C re-revision + Round 4 full-scope. Adds ~3–4 days to sprint timeline; but the operator pre-commitment in Decision 7 binds.

**Routing implication if operator dispositions (b):** RSK-REFRESH-POSITIONS-CONCURRENT-CALLER at CRITICAL severity (per Severity Calibration Rubric — failure mode produces phantom-short = unrecoverable financial loss class). Sprint Abort Condition #N added. Sprint ships with the documented gap; operator daily-flatten mitigation extended; Sprint 31.94 reconnect-recovery work picks up the serialization fix as part of its `IBKRReconnectedEvent` consumer scope.

---

## High findings

### H-R3-1 — `time.time()` (wall-clock) used for `_locate_suppressed_until`; clock skew can prematurely release suppression OR indefinitely extend it

**Severity:** High
**Primitive-semantics class:** **borderline** (system-design choice between `time.time` vs `time.monotonic`; the underlying primitive *is* runtime behavior of the OS clock, but the choice between them is a system-design decision)
**Affected FAI entries:** none

**Reviewer's argument:**

AC2.3 specifies `_locate_suppressed_until[position.id] = time.time() + config.locate_suppression_seconds`. AC2.2's check is `now < self._locate_suppressed_until.get(position.id, 0.0)` where `now` is presumably also `time.time()`.

`time.time()` returns **wall-clock time**, not monotonic time. Wall-clock is subject to:
- **NTP step adjustments** (typically <1s, but possible to step >5s on first sync after long disconnect)
- **DST transitions** (affect timezone-aware time but not Unix timestamp — this is a non-issue for `time.time()`; flagging for completeness)
- **Manual operator clock adjustment** (rare but possible)
- **VM time-jump after suspend/resume** (servers don't typically suspend; non-issue for production)

With `locate_suppression_seconds` defaulting to 18000s (5hr) per the spec, even worst-case NTP step adjustment of 30s is negligible. **However**, the scenario that matters: if the system clock is set incorrectly at boot (e.g., RTC battery dead, NTP not yet synced), suppression entries set BEFORE NTP sync use a wrong wall-clock value. After NTP sync corrects the clock, suppression entries are either far-future (suppression effectively never expires) or far-past (suppression expires immediately).

The CRITICAL failure mode: clock corrects FORWARD (e.g., from RTC-default 2020 timestamp to actual 2026), and ALL existing suppression entries' `_until` values are now in the past. AC2.2 returns False unconditionally. The next SELL emit at any locate-suppressed position fires WITHOUT suppression — exactly the retry-storm condition Sprint 31.92 is designed to prevent.

This is operationally remote (NTP typically syncs at boot before ARGUS starts), but the failure mode produces phantom-short exposure (unrecoverable financial loss class per Severity Calibration Rubric).

**Why this is FAI-class (or not):**

Borderline. The primitive in question is `time.time()` semantics — a runtime primitive. The structural shape is similar to FAI entries (assumption about runtime primitive's behavior whose violation produces the symptom class). However, the choice of `time.time()` over `time.monotonic()` is a system-design choice (the FAI's "out of scope" list explicitly excludes "system-design choices"). I lean **NOT FAI-class**, but flag for operator disposition.

**Proposed disposition:** **ACCEPT** — change `time.time()` to `time.monotonic()` for suppression timeout (one-line fix at AC2.3 + AC2.2; spec-text clarification needed in Sprint Spec § Config Changes table for `locate_suppression_seconds` validator).

**Proposed fix shape:**

- Replace `time.time()` with `time.monotonic()` at all `_locate_suppressed_until` set/read sites (4 places per the 4 standalone-SELL exception handlers + the pre-emit suppression check + the AC2.5 timeout check).
- Add regression test: `test_locate_suppression_resilient_to_wall_clock_skew` — patch `time.time` to return a value far in the past, assert suppression entries unaffected (because they use `time.monotonic`).
- Update Sprint Spec § Config Changes table footnote: "Suppression timeout uses `time.monotonic()` for clock-skew resilience; the `locate_suppression_seconds` Pydantic field bounds (300–86400) are seconds in monotonic time, equivalent to wall-clock under normal operation."

**Cumulative diff impact:** ~5 LOC. Negligible.

---

### H-R3-2 — Decision 4 watchdog `auto`→`enabled` flip semantics not specified: atomicity, persistence, restart-survival all undefined

**Severity:** High
**Primitive-semantics class:** **borderline** (config-field mutation atomicity is a primitive question; storage choice is system-design)
**Affected FAI entries:** #4 (justification for measured-only depends on this auto-activation working correctly)

**Reviewer's argument:**

Decision 4 introduces `pending_sell_age_watchdog_enabled: Literal["auto", "enabled", "disabled"]` with the contract: *"`auto` mode flips to `enabled` on first observed `case_a_in_production` event."* AC2.7 references this and the FAI's justification log § entry #4 says: *"acceptable as measured-only because the M-R2-1 case-A watchdog (AC2.7) is auto-activated on first observed case-A in production paper trading per Decision 4."*

The spec does NOT specify:
1. **Where the post-flip state is stored.** In-memory Pydantic field mutation (volatile across restarts)? YAML write-back (filesystem race)? New SQLite column (schema migration — but SbC §"Do NOT modify" forbids `data/argus.db` schema changes)?
2. **What defines a "first observed `case_a_in_production` event."** Per-position? Per-symbol? Per-day? Globally? The Round 3 reviewer task list § Step 4 explicitly raises this question.
3. **Whether the flip survives ARGUS restart.** If in-memory only, every restart re-enters `auto` state until next case-A observation. If the case-A storm happened on Day 1 and ARGUS restarted on Day 2, Day 2 starts with watchdog disabled until another case-A is observed — exposing the same blind spot FAI #4's measured-only acceptance was justified by removing.
4. **Atomicity of the flip under concurrent observation.** If two coroutines both observe case-A near-simultaneously, both attempt the flip. Pydantic v2 BaseModel mutations call validators on assignment if model is configured to revalidate. With concurrent attribute sets, re-entrant validation could produce inconsistent state.

The spec's silence on these four questions means: the FAI #4 justification ("acceptable as measured-only because Decision 4 auto-activates the watchdog") rests on a mechanism whose semantics are not specified. The mechanism could in principle satisfy any of (in-memory / YAML / DB) implementations, but each has different failure modes.

**Why this is High not Critical:** the FAI #4 measured-only acceptance is conditional, and the spike (S1b) does NOT directly depend on Decision 4 — it just measures string variants. The fallback chain is: S1b's substring fingerprint catches case-B, AC2.7 watchdog catches case-A. If watchdog mechanism is broken, case-A goes uncaught. But case-A in production paper trading is itself rare (per Apr 28 trace, observed once on PCT). Risk is real but bounded.

**Why this is FAI-class (or not):**

Borderline. Config-field mutation atomicity IS a primitive-semantics surface (Python attribute mutation, Pydantic validator side-effects, OS filesystem semantics if YAML-backed). The structural shape — a primitive whose violation silently disables a load-bearing fallback — matches the FAI pattern. However, the spec doesn't even define the storage mechanism; until that's specified, "primitive-semantics" doesn't have a fixed surface to attach to. **Reviewer leans NOT FAI-class on the grounds that this is a specification gap before it's a primitive-semantics miss** — though the gap could promote to FAI-class once the storage choice is made.

**Proposed disposition:** **ACCEPT** — spec amendment required.

**Proposed fix shape:**

Sprint Spec § AC2.7 amended to specify:
- **Storage:** in-memory Pydantic field mutation only (no persistence). Restart resets to `auto`.
- **Event-definition:** "first observed `case_a_in_production`" = first time `_pending_sell_age_seconds` exceeds threshold AND no fill observed AND `_locate_suppressed_until[position.id]` is set, in any single ARGUS process lifetime. Globally, not per-position or per-symbol.
- **Atomicity:** the flip is a single attribute mutation guarded by `asyncio.Lock` in the watchdog detection path; re-entrant flips are no-ops (idempotent).
- **Logged transition:** a structured log line `event="watchdog_auto_to_enabled"` is emitted on flip, with `case_a_evidence: {position_id, symbol, age_seconds_at_flip}`.

RSK addition: **RSK-WATCHDOG-AUTO-FLIP-RESTART-LOSS (MEDIUM):** the auto-enabled state does not survive ARGUS restart. If a case-A storm happened pre-restart and ARGUS restarts during the storm, the post-restart process operates with watchdog disabled until another case-A observation. Mitigation: post-restart `reconstruct_from_broker` populates `is_reconstructed=True`, which under AC3.7 refuses ARGUS-emitted SELLs entirely, so the missing watchdog is moot for reconstructed positions; the residual risk is for NEW positions entered post-restart that hit case-A before the watchdog re-enables.

---

### H-R3-3 — `halt_entry_until_operator_ack=True` flag introduced but its consumer and clearing mechanism are not specified

**Severity:** High
**Primitive-semantics class:** **no** (specification gap)
**Affected FAI entries:** none

**Reviewer's argument:**

Tier 3 item C introduces `halt_entry_until_operator_ack=True` as a field on `ManagedPosition`, set when (H1 active) AND (`Broker.refresh_positions()` failure). Per AC2.5 Branch 4 and the Hypothesis Prescription H1 row, this is the structural defense for the FAI #2 + #5 cross-falsification path under H1.

The Sprint Spec § Cumulative diff bound mentions "+ `halt_entry_until_operator_ack` field threading" but does NOT specify:

1. **Who consumes the flag.** Presumably the entry-side Risk Manager (DEC-027, Check 0) or the Orchestrator. The spec doesn't enumerate which code path queries the flag and rejects entries.
2. **The granularity of the halt.** Per-`ManagedPosition` (current field location) means: only THIS position's entries are halted, but a NEW position on the same symbol can be entered. Is that the intent? Or should the halt be per-symbol or global?
3. **The ack mechanism.** The flag is named `halt_entry_until_operator_ack`. How does the operator ack? Through a CLI tool? A REST endpoint? The Web UI's AlertBanner? Manually editing SQLite (not persisted; would have to be in-memory mutation via debug shell)? The Sprint 31.91 Alert Observability subsystem (DEC-388) has an AlertAcknowledgmentModal — does that ack ALSO clear `halt_entry_until_operator_ack`? Or are they separate?
4. **Restart behavior.** The field is on `ManagedPosition` which is in-memory only (per SbC: `cumulative_pending_sell_shares` etc. are "in-memory `ManagedPosition` fields ONLY, NOT persisted to SQLite"). After restart + `reconstruct_from_broker`, the new ManagedPosition has `is_reconstructed=True` AND `halt_entry_until_operator_ack=False` (default). Is the halt cleared by virtue of the position being reconstructed? Or should reconstruct preserve halt state? Spec is silent.

This is a specification gap with downstream test-coverage implications. CL-3 (cross-layer test exercising H1 + refresh-fail) cannot fully assert the HALT-ENTRY semantic without specifying what the consumer does. The test is currently spec'd as "verify the H-R2-2 HALT-ENTRY posture catches the composite — position marked `halt_entry_until_operator_ack=True`; no further SELL attempts; no phantom short" — the "no further SELL attempts" assertion can be made (L3 ceiling refuses on `is_reconstructed`-style mechanism would handle this), but the "no further entries" implication is not tested because the consumer isn't specified.

**Why this is High not Critical:** the gap is in spec-text clarity, not in primitive-semantics. The mechanism CAN be made correct with a clean spec amendment.

**Proposed disposition:** **ACCEPT** — spec amendment required.

**Proposed fix shape:**

Sprint Spec § AC2.5 Branch 4 amended to specify:

- **Consumer:** RiskManager Check 0 (existing DEC-027 check 0 for `share_count ≤ 0`) extended to also reject entries when ANY ManagedPosition has `halt_entry_until_operator_ack=True` AND the entry signal is for the SAME `ManagedPosition.id`. (Per-position granularity preserved; new positions on same symbol unaffected.)
- **Ack mechanism:** new REST endpoint `POST /api/v1/positions/{position_id}/clear_halt` (no Web UI in this sprint per SbC §13; CLI tool sufficient — `scripts/clear_position_halt.py {position_id}`). Operator runs this AFTER inspecting position state via `scripts/ibkr_close_all_positions.py` (or whatever investigation step they take).
- **Restart behavior:** post-restart, `is_reconstructed=True` already refuses ALL ARGUS-emitted SELLs per AC3.7. The halt-entry flag is therefore subsumed by the broader refusal posture for reconstructed positions; the flag's purpose is the narrow window between Branch-4-firing and either fill-observation OR position-close. Halt state need NOT survive restart because the broader is_reconstructed refusal handles the post-restart case.
- **Logged transition:** structured log line `event="halt_entry_set"` on Branch 4 + H1 firing; `event="halt_entry_cleared"` on operator-ack via CLI.

Cumulative diff bound recalibration: ~20 LOC in `argus/risk/risk_manager.py` (extend Check 0) + ~30 LOC for the new endpoint + ~20 LOC for the CLI tool. Total ~70 LOC. Falls within the existing ~1150–1300 LOC OrderManager bound (these are NEW files, not OrderManager).

**Test coverage:** new test `test_risk_manager_check0_rejects_when_halt_entry_set` + new test `test_clear_halt_endpoint_requires_position_id_and_clears_flag`.

---

### H-R3-4 — AC4.6 dual-channel CRITICAL warning emits at startup only; not gated on operator acknowledgment, easily missed in auto-restart scenarios

**Severity:** High
**Primitive-semantics class:** **no** (system-design choice — startup-only warning vs. ack-gated halt)
**Affected FAI entries:** none

**Reviewer's argument:**

AC4.6 specifies dual-channel CRITICAL warning (ntfy.sh urgent + canonical-logger CRITICAL with phrase "DEC-386 ROLLBACK ACTIVE") when `bracket_oca_type != 1` AND `--allow-rollback` flag present. AC4.7 specifies exit-code-2 when the flag is absent. The dual-channel warning is captured at startup; the spec specifies log-capture testing in S4b.

Operational reality:
1. **ARGUS auto-restart loops.** If ARGUS is run under systemd, launchd, or supervisor with `--allow-rollback` baked into the unit file (e.g., during emergency rollback, the operator sets the flag and restarts; if they forget to remove it, every subsequent auto-restart fires the warning AND ARGUS proceeds).
2. **ntfy.sh notification fatigue.** The operator's ntfy.sh `argus_system_warnings` topic also receives other system warnings (e.g., disconnect events, holiday detection, DEC-388 alerts). A CRITICAL on startup competes for attention with the morning's scheduled-event noise.
3. **Log review cadence.** The canonical-logger CRITICAL stays in the log, but if the operator doesn't review logs every morning, the rollback persists silently across days. The `--allow-rollback` flag is a UX choice that signals "operator deliberately enabled this," but the per-startup re-confirmation is one-shot.

The Simulated Attack section (Step 6) explicitly raises this: *"Could a misbehaving operator-typed `--allow-rollback` flag (e.g., in a startup script copied across environments) silently downgrade ARGUS from DEC-386's 4-layer OCA enforcement to DEC-386 ROLLBACK ACTIVE state without operator awareness?"* Yes — the dual-channel warning fires every startup but operator may miss every startup.

The Tier 3 item C HALT-ENTRY pattern (`halt_entry_until_operator_ack=True`) was applied to AC2.5 Branch 4 + H1 active. The same pattern is NOT applied to AC4.6 — startup with rollback active does NOT halt-entry until ack.

**Why this is High not Critical:** rollback-active is itself a deliberate operator action; the design intent is to allow startup. Adding a HALT-ENTRY pattern would block emergency rollback's intended use case (operator deliberately enables to bypass DEC-386 OCA enforcement during an outage). The Future Regret risk is real but the design choice is defensible.

**Why this is FAI-class (or not):** **NOT** FAI-class — system-design choice (startup-only warning vs. ack-gated halt).

**Proposed disposition:** **ACCEPT (different)** — add intermediate operator-ack mechanism that doesn't block emergency rollback startup but DOES log the operator's continued awareness.

**Proposed fix shape:**

Sprint Spec § AC4.6 amended to add:

- **Startup-time interactive ack (default ON for non-CI environments; CI override via `--allow-rollback-skip-confirm`):** when `bracket_oca_type != 1` AND `--allow-rollback` AND interactive TTY detected, ARGUS prompts the operator: "DEC-386 ROLLBACK ACTIVE. Type 'I ACKNOWLEDGE ROLLBACK ACTIVE' to proceed:" — typing the exact phrase proceeds; anything else exits with code 3.
- **Periodic re-ack:** every 4 hours during runtime, the canonical-logger CRITICAL with phrase "DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — N hours since startup" fires. ntfy.sh fires on the same interval. Operator sees recurring alert; the "rollback persists silently for days" failure mode is bounded to 4-hour windows.
- **CI override:** `--allow-rollback-skip-confirm` CLI flag (separate from `--allow-rollback`) bypasses the interactive prompt for unattended starts. CI fixtures use BOTH flags. The CI-override flag itself is recorded in the dual-channel warning.

Add Edge Case to Reject (NEW #19): "`--allow-rollback-skip-confirm` used in production startup scripts. The flag exists for CI ONLY; production startup MUST require the interactive ack."

Cumulative diff impact: ~30 LOC in `argus/main.py` (interactive prompt + 4-hour periodic re-ack) + ~10 LOC in CI fixtures.

---

### H-R3-5 — AC3.1's enumeration of "5 transitions" + S4a-ii's enumeration of "5 callback paths" lacks an AST-level exhaustiveness guard analogous to FAI #8

**Severity:** High
**Primitive-semantics class:** **borderline** (the structural class is identical to FAI #8 — code-scan completeness — but for a different mechanism)
**Affected FAI entries:** **#8** (sibling-class extension), **#9** (the assumption FAI #9 protects depends on the enumeration being exhaustive)

**Reviewer's argument:**

AC3.1 enumerates 5 state transitions for the bookkeeping counters: place-time increment, cancel-time decrement, reject-time decrement, partial-fill transfer, full-fill transfer. The S4a-ii regression scope per FAI entry #9 covers 5 callsites: `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, plus the multi-attribute read in `_check_sell_ceiling` (technically 6 callsites).

The implicit claim: **these are the only callsites that mutate `cumulative_pending_sell_shares` and `cumulative_sold_shares`.** If a 6th (or 7th) callsite exists in production code now or is added in a future sprint, FAI #9's protection is silently incomplete.

Analogous primitive-semantics question to FAI #8 (which protects `is_stop_replacement=True` callers via AST callsite scan + reflective sub-tests):

- **FAI #8:** "the codebase scan for `is_stop_replacement=True` callers has no false-negative paths via reflective or aliased call patterns" — falsified at S4a-ii adversarial regression sub-tests.
- **Hypothetical FAI #11 (reviewer-proposed extension):** "the codebase scan for `cumulative_pending_sell_shares` / `cumulative_sold_shares` MUTATION sites is exhaustive — all sites that perform `+=` or `-=` on these attributes are within the AC3.1 enumeration."

**Concrete failure scenarios:**

1. **`_on_exec_details` callback:** ib_async exposes `execDetailsEvent` — fires on every execution. Some ARGUS implementations subscribe to BOTH `orderStatusEvent` (for state machine) AND `execDetailsEvent` (for execution accounting). If `_on_exec_details` exists in current ARGUS code and mutates either counter, it's an UNCOVERED bookkeeping path. The S4a-ii regression test will pass (it tests only the 5 enumerated callsites) and the protection will be incomplete.

2. **Future maintenance:** Sprint 31.93's component-ownership refactor (DEF-175/182/193/201/202) is in the Build Track Queue immediately after Sprint 31.92. If that refactor introduces new bookkeeping touchpoints (e.g., a unified `_record_execution()` helper), FAI #9's regression test won't grow with the surface.

3. **Test author drift:** test authors writing new tests that include test fixtures that mutate counters directly (`position.cumulative_sold_shares = 100`) — these aren't bookkeeping paths but they could escape the AST scan if structured as monkey-patched method assignments.

The fix is symmetric with FAI #8's approach: add an AST-level exhaustiveness guard.

**Why this is High not Critical:** the operational risk is bounded — even if a 6th callsite exists and isn't synchronously-protected, it would have to mutate counters BETWEEN reads and writes of an in-flight `_check_sell_ceiling` to cause the ceiling to admit a SELL it should refuse. The probability is non-zero but lower than the place-time race or the partial-fill race that FAI #9 explicitly covers.

**Why this is FAI-class (or not):** Sibling-class to FAI #8 (code-scan completeness for a specific assumption). I lean **borderline FAI-class** — strict reading of the self-falsifiability clause says "additional primitive-semantics assumption load-bearing on the proposed mechanism" — the mechanism's correctness depends on the enumeration being exhaustive, and the spec doesn't enforce that. The case for "not new class" rests on it being a sibling of FAI #8's pattern; the case for "new class" is that no FAI entry covers `cumulative_*_shares` callsite-scan exhaustiveness specifically.

Reviewer recommends operator disposition: if FAI is being amended for C-R3-1 anyway (Decision 7 (a) routing), add this as FAI #11 in the same revision pass. If C-R3-1 routes (b), add as RSK and ship.

**Proposed disposition:** **ACCEPT** — add AST-level exhaustiveness guard.

**Proposed fix shape:**

S4a-ii regression suite extended with a new test:

```python
def test_bookkeeping_callsite_enumeration_exhaustive():
    """AST scan asserts ALL `cumulative_pending_sell_shares` and 
    `cumulative_sold_shares` mutation sites in argus/execution/order_manager.py
    are within the FAI #9 protected callsite list.
    """
    expected_callsites = {
        "_reserve_pending_or_fail",
        "on_fill",
        "on_cancel",
        "on_reject",
        "_on_order_status",
        "reconstruct_from_broker",  # initialization, not a runtime mutation
    }
    src = inspect.getsource(OrderManager)
    tree = ast.parse(src)
    mutating_sites: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Attribute):
            if node.target.attr in {"cumulative_pending_sell_shares", "cumulative_sold_shares"}:
                # find enclosing function name
                enclosing_func = _find_enclosing_function(tree, node)
                mutating_sites.add(enclosing_func)
    extra = mutating_sites - expected_callsites
    assert not extra, f"FAI #9 incomplete: bookkeeping mutation in {extra} not in expected callsites"
```

Add corresponding entry to FAI as #11 (or #10 if C-R3-1 is dispositioned (b)):

> *"All sites in `argus/execution/order_manager.py` that mutate `cumulative_pending_sell_shares` or `cumulative_sold_shares` are enumerated in the FAI #9 protected callsite list. Falsifying spike: AST scan asserts no `AugAssign` to those attributes in functions outside the expected list."* Status: **unverified — falsifying spike scheduled in S4a-ii.**

Cumulative diff impact: ~40 LOC (the test + helper). Within budget.

---

## Medium findings

### M-R3-1 — S1a `worst_axis_wilson_ub` is computed across three axes individually but does not measure axis-COMBINATIONS

**Severity:** Medium
**Primitive-semantics class:** no (spike-quality concern)
**Affected FAI entries:** #3 (the spike scope is what FAI #3 falsifies; combination-axis is a known coverage gap)

**Reviewer's argument:**

Decision 1 specifies S1a's three adversarial axes for `modifyOrder` rejection-rate: (i) concurrent amends across N≥3 positions, (ii) amends during reconnect window, (iii) amends with stale order IDs. The Hypothesis Prescription's halt-or-proceed gate uses "**worst-axis** Wilson UB" — i.e., max across the three individually-measured axes.

Production reality: a Gateway reconnect during high-volume can trigger axis (i) AND axis (ii) simultaneously. The joint distribution's UB is NOT the max of the marginal UBs — it can be substantially higher (compound failure modes).

The spike does not test combinations. Sprint 31.92's mechanism selection (H2 vs H4 vs H1) is gated on worst-axis UB, which underestimates the joint-axis UB.

**Proposed disposition:** **ACCEPT** — extend S1a to include combination axes OR explicitly document that the worst-axis UB is a lower bound on the actual production UB.

**Proposed fix shape:**

Two options; reviewer recommends (a):
- **(a)** S1a strengthened with a 4th axis: (iv) concurrent amends across N≥3 positions DURING reconnect window (axes (i) ∪ (ii) joint). Halt-or-proceed gate uses `worst_axis_wilson_ub` across all 4 axes.
- **(b)** Document in DEC-390 Context section: "the H2 selection is gated on worst-axis Wilson UB across 3 marginal axes; joint-axis behavior is not measured. If observed production rejection rate exceeds the UB, mechanism shifts to H4 hybrid via the existing AC1.6 audit path."

Cumulative diff impact: option (a) ~50 LOC additional spike script, ~10 minutes additional spike runtime. Option (b) is documentation only.

---

### M-R3-2 — AC2.5 Branch 4 alert idempotency for `phantom_short_retry_blocked` across multiple session firings on the same position is not specified

**Severity:** Medium
**Primitive-semantics class:** no (specification gap)
**Affected FAI entries:** none

**Reviewer's argument:**

Edge Case to Reject #9 specifies: *"Suppression-window expiration emits at most ONE alert per `ManagedPosition.id` per session."* AC2.5 Branches 1/2/3 fire `phantom_short_retry_blocked` once per position per session (with the dict-clear-on-fire idempotency).

Branch 4 (`verification_stale: true`) ALSO fires `phantom_short_retry_blocked` (per AC2.5 spec: "publish `phantom_short_retry_blocked` alert with metadata `{verification_stale: True, ...}`"). If Branch 4 fires once, can it fire AGAIN on the same position?

Scenario: AC2.5 fallback fires on P1; refresh times out; Branch 4 fires; HALT-ENTRY set under H1; alert published; dict entry cleared. AC2.7 watchdog fires later on the same P1 (separate trigger); fallback re-fires; refresh times out again; Branch 4 fires again; HALT-ENTRY already set (idempotent); alert ALSO fires? Or is it suppressed by the per-session-once invariant?

The spec doesn't specify whether Branch 4 firings count toward the per-position-per-session alert idempotency. If they do, repeated refresh-failures on the same position produce only one alert ever — operator may miss continued failures. If they don't, alert spam during a refresh-failure storm.

**Proposed disposition:** **ACCEPT** — spec amendment.

**Proposed fix shape:**

Sprint Spec § AC2.5 amended to specify: "Branch 4 firings on the SAME `ManagedPosition.id` within a session are throttled — first Branch 4 firing publishes; subsequent firings within 1 hour are suppressed at the alert layer (logged INFO with `branch_4_throttled: true` metadata) but the HALT-ENTRY effect persists. The 1-hour throttle resets on `on_position_closed` or successful refresh observation."

Cumulative diff impact: ~30 LOC (throttle state in HealthMonitor or local state in OrderManager).

---

### M-R3-3 — Same-position concurrent `modify_order` calls under H2 not exercised by S1a (axis (i) tests across-position; same-position concurrency unverified)

**Severity:** Medium
**Primitive-semantics class:** **borderline** (depends on whether ARGUS code already serializes per-position trail-flatten)
**Affected FAI entries:** #3 (steady-state and adversarial sub-axes are tested per Decision 1, but same-position concurrent amends aren't)

**Reviewer's argument:**

S1a axis (i) tests "concurrent amends across N≥3 positions" — different `stop_id`s. H2's per-position behavior under same-position concurrent amends (e.g., trail-stop fires twice in 50ms because the price oscillates) is NOT tested.

If ARGUS code already serializes per-position via existing locking on `_trail_flatten`, this is moot. Without code inspection at HEAD, reviewer cannot confirm. The spec doesn't reference per-position serialization.

**Proposed disposition:** **PARTIAL ACCEPT** — verify existing serialization OR add same-position concurrent-amend axis to S1a.

**Proposed fix shape:**

S2a implementation prompt extended with a precondition check: "Verify `_trail_flatten` is guarded against same-position concurrent invocation (e.g., via `ManagedPosition._trail_flatten_in_progress` flag or asyncio.Lock). If not, surface to operator before implementing H2; concurrent same-position trail-flatten is NOT in S1a's scope and must be either prevented at the call-site or measured separately."

Cumulative diff impact: documentation + a precondition check; ≤10 LOC if mitigation needed.

---

### M-R3-4 — AC2.5 `refresh_positions()` followed by `get_positions()` cache-read: implicit assumption of no `await` between the two

**Severity:** Medium
**Primitive-semantics class:** **yes** (asyncio yield-gap class — analogous to FAI #1, but for the AC2.5 fallback path rather than the L3 ceiling path)
**Affected FAI entries:** **#1** (sibling pattern); **#2** (the `refresh_positions`-then-`get_positions` sequence depends on freshness lasting until the read)

**Reviewer's argument:**

AC2.5 Branch 1/2/3 classification reads from `broker.get_positions()` (synchronous local-cache lookup) AFTER `refresh_positions(timeout=5.0)` returns. If the implementation is:

```python
await self._broker.refresh_positions(timeout_seconds=5.0)
positions = self._broker.get_positions()  # synchronous, no yield
```

Then no other coroutine runs between the two — the cache-read sees the cache state at the moment refresh returned. Fine.

If the implementation has any `await` between (e.g., logging that does `await self.logger.ainfo(...)`):

```python
await self._broker.refresh_positions(timeout_seconds=5.0)
await self.logger.ainfo("refresh complete, querying positions")  # YIELDS!
positions = self._broker.get_positions()  # cache may have advanced
```

Then between the two, other coroutines run. The cache may be MORE fresh (some other position's state changed) — usually benign but can produce false-Branch-3 firings if a fill arrived for an unrelated position and the get_positions snapshot now shows a different state than expected.

The spec doesn't enforce no-await-between. The AST scan in S4a-ii covers only `_reserve_pending_or_fail`. AC2.5's `refresh-then-get` sequence is a structurally identical pattern but is unprotected.

**Proposed disposition:** **ACCEPT** — extend AST-no-await scan to cover the AC2.5 `refresh_positions`-then-`get_positions` sequence.

**Proposed fix shape:**

S4a-ii regression test extended to include a third pattern (in addition to FAI #1 and FAI #9): an AST scan that asserts no `ast.Await` between `await self._broker.refresh_positions(...)` and `self._broker.get_positions(...)` in the AC2.5 fallback function. This is more complex than the existing FAI #1 scan because it requires identifying a specific call-pattern across two consecutive statements; reviewer suggests extracting the read sequence into a helper:

```python
def _read_positions_post_refresh(self) -> list[Position]:
    """Synchronous read; helper exists to ensure no await between refresh and read."""
    return self._broker.get_positions()
```

Then the AST scan asserts the helper's body contains no Await. Same pattern as FAI #1.

Cumulative diff impact: ~15 LOC (helper + test). Negligible.

---

## Low findings

### L-R3-1 — Pydantic config field mutation atomicity for Decision 4's `auto`→`enabled` flip is implementation-implicit

**Severity:** Low
**Primitive-semantics class:** no (specification gap; partly subsumed by H-R3-2)
**Affected FAI entries:** #4 (justification depends)

**Reviewer's argument:** Subsumed in H-R3-2 (spec amendment for storage + atomicity + restart behavior). Listed separately because the Pydantic-specific concern is narrower: Pydantic v2 BaseModel attribute assignment may trigger validator re-execution if model is configured with `validate_assignment=True`. Concurrent flips would re-enter validation; the spec doesn't specify the model's configuration.

**Proposed disposition:** **ACCEPT** — covered by H-R3-2 fix shape; flag here for completeness.

---

### L-R3-2 — `--allow-rollback` flag persistence across systemd auto-restart is operator-process risk

**Severity:** Low
**Primitive-semantics class:** no (operator-process concern; per FAI scope-exclusion list)
**Affected FAI entries:** none

**Reviewer's argument:** Subsumed in H-R3-4 (interactive ack + periodic re-ack). The operator-process concern (flag persists in startup script across environments) is partially mitigated by the H-R3-4 fix's interactive-ack (forces operator presence at startup) and periodic-re-ack (forces operator awareness during runtime).

**Proposed disposition:** **ACCEPT** — covered by H-R3-4 fix shape.

---

## FAI cross-check summary

- **Completeness check:** **FAIL — C-R3-1 fires.** New primitive-semantics surface identified: `Broker.refresh_positions()` concurrent-caller correlation via `positionEndEvent`. Not covered by FAI #2 (single-caller cache convergence under reconnect cycles). Reviewer recommends adding as FAI #10 (or as extension of FAI #2 if operator dispositions narrowly). H-R3-5 also surfaces a borderline-class miss (sibling of FAI #8 — AST exhaustiveness for bookkeeping callsites) which reviewer recommends adding as FAI #11 in the same revision pass.

- **Status-rating audit:** **PASS** for entries #1, #3, #5, #6, #7, #8, #9 (each has a concrete falsifying spike scheduled in a real session per `session-breakdown.md` references). Entry #2 PASS conditional on Branch 4 fixture (S5c) actually exercising the failure mode — see CL-3 evaluation below. Entry #4 (measured-only) PASS conditional on H-R3-2 spec amendment landing — without the storage/atomicity/restart specification, the Decision 4 auto-activation justification is itself unverifiable.

- **Spike-quality check:** **PARTIAL PASS.** Entry #5's hard-gate (N=100, zero conflicts) is well-formed. Entry #1's mocked-await injection is mechanism-sensitive per Tier 3 item B. Entry #3's worst-axis Wilson UB has the M-R3-1 axis-combination gap. Entry #8's three reflective sub-tests (`**kw` / computed-flag / `getattr`) are well-formed. Entry #9 covers the 5 enumerated paths but H-R3-5 identifies the missing exhaustiveness guard.

- **Cross-Layer Composition Test count + CL-6 deferral:** **PASS for count** (5 tests above the floor; Decision 5 rationale documented per process-evolution lesson F.7). **PASS-with-noted-concern for CL-3 fixture validity:** the `SimulatedBrokerWithRefreshTimeout` fixture exercises Branch 4 in-process under SINGLE-caller refresh-timeout. **Reviewer concern:** CL-3 does not exercise the C-R3-1 concurrent-caller scenario. If C-R3-1 is dispositioned (a) and fixed via Fix A (single-flight serialization), CL-7 (NEW) should be added to exercise the serialization. If dispositioned (b), CL-3's single-caller scope is insufficient evidence that the production scenario is safe. Reviewer recommends CL-7 regardless of routing.

- **Synchronous-update invariant scope:** **PARTIAL PASS.** Regression invariant 23 covers the 5 enumerated paths + `_check_sell_ceiling` multi-attribute read per Tier 3 items A + B. M-R3-4 identifies the gap in AC2.5's `refresh_positions`-then-`get_positions` sequence not being covered by the same AST-no-await pattern. H-R3-5 identifies the gap in callsite-enumeration exhaustiveness.

- **Defense-in-depth probe:** **NEW FINDINGS — C-R3-1, H-R3-1, H-R3-2, H-R3-3, H-R3-5, M-R3-2, M-R3-3, M-R3-4.** Of these, C-R3-1 is the load-bearing primitive-semantics miss; H-R3-1 (clock-skew) and M-R3-4 (asyncio yield-gap in AC2.5) are FAI-adjacent; H-R3-2 / H-R3-3 / M-R3-2 are specification gaps; H-R3-5 is a sibling-class extension of FAI #8.

---

## Verdict and routing

**Outcome:** **B** — Round 3 produced revisions (1 Critical + 5 High + 4 Medium + 2 Low; A14 fired).

**Decision 7 routing:** **(a) primitive-semantics-class Critical → Phase A re-entry per Outcome C** — *recommended*; **(b) ambiguous-class flag** preserved per the input package's "encouraged to flag ambiguous-class findings explicitly" guidance.

The reviewer's recommendation is (a) because:
- C-R3-1's structural shape is identical to the three prior FAI-class misses (Round 1 / Round 2 / Phase A T3) — a primitive-semantics behavior load-bearing on the mechanism whose violation produces the symptom class the proposed fix claimed to address.
- The empirical scenario that triggers the failure (Apr 28-style 60-phantom-short cluster with concurrent AC2.5 fallbacks) is not speculative — it is the very scenario Sprint 31.92 is responding to.
- The FAI's self-falsifiability clause was authored precisely for this case (per process-evolution lesson F.6).
- Fix A (single-flight serialization) is straightforward and adds ≤50 LOC; the marginal sprint-cost of routing (a) is bounded.

The operator may legitimately disposition (b) on grounds that:
- C-R3-1 is an extension of FAI #2 rather than a new entry (definitional question).
- Sprint 31.92's daily-flatten mitigation continues; the residual phantom-short risk is bounded by operator action.
- Routing (a) extends the sprint by ~3–4 days (Phase B re-run + Phase C re-revision + Round 4 full-scope), which has cost given the cessation criterion #5 5-paper-session counter is gating live trading.

If operator dispositions (b), the RSK shape is reproduced verbatim in C-R3-1 above (RSK-REFRESH-POSITIONS-CONCURRENT-CALLER at CRITICAL severity per Severity Calibration Rubric §"failure mode produces unrecoverable financial loss within single trading session").

**Phase D status:**
- If (a): **NOT proceeding** — Phase A re-entry required (4th revision pass; Round 4 full-scope per protocols/adversarial-review.md v1.1.0 § Outcome C as amended 2026-04-29).
- If (b): **proceed to Phase D** with the C-R3-1 RSK + the High/Medium/Low findings folded into spec-text amendments per their respective fix shapes; the 5 High findings should be addressed in-spec-text BEFORE Phase D prompt generation (2-day spec amendment cycle), not deferred to in-sprint discovery.

**Round 4 required:**
- If (a): **yes — full scope** per Outcome C re-fire (5th time the FAI's self-falsifiability clause has been triggered would be the next escalation).
- If (b): **no** — sprint ships to implementation; mid-sprint Tier 3 review at S4a close-out (M-R2-5) provides the next checkpoint.

**Operator override:** N/A unless operator dispositions C-R3-1 routing differently from reviewer recommendation. Any override should be logged in the Round 3 disposition with explicit rationale; per Decision 7 verbatim, operator override is permitted but must be explicit and logged.

---

## Reviewer's closing note (per probing-sequence Step 6 — Simulated Attack reflection)

The Simulated Attack section of the input package raises three concerns about `--allow-rollback` flag misuse. H-R3-4's fix shape (interactive ack + periodic re-ack + CI-override flag separation) addresses all three. Reviewer adds one observation outside the formal findings: the dual-channel CRITICAL warning is a *notification mechanism*, not an *enforcement mechanism*. ARGUS's broader pattern (e.g., the Tier 3 item C `halt_entry_until_operator_ack=True` flag) demonstrates that enforcement mechanisms exist when the design wants them. AC4.6's choice of notification-only is defensible (emergency rollback intended use case) but is a **design pattern that doesn't compose with itself across the system** — some safety surfaces are halt-gated, others are warn-only. Future sprints might benefit from explicitly classifying each safety surface as halt-gated vs. warn-only and documenting the rationale per surface. Reviewer flags this as a process-evolution observation (not a finding) for sprint-close consideration.

---

## End of verdict

**Reviewer asserts:** Round 3 was conducted at full scope per `protocols/adversarial-review.md` v1.1.0 § Outcome C (the 2026-04-29 amendment supersedes Round 2 disposition's narrowest-scope recommendation). All 6 probing-sequence steps were applied (Assumption Mining + FAI cross-check / Failure Mode Analysis / Future Regret / Specification Gaps / Integration Stress / Simulated Attack). The FAI's self-falsifiability clause has been triggered for the fourth time; reviewer recommends Decision 7 (a) routing but flags the ambiguous-class possibility for operator disposition.

**Reviewer's confidence on C-R3-1's FAI-class designation:** **moderate-to-high** — the structural shape matches the three prior misses, the empirical scenario is not speculative, and the spec is silent on the relevant primitive. The borderline aspect is purely the definitional question of "extension of FAI #2" vs. "new FAI entry."
