# Doc-Sync Patch 9 — `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md` (AMENDED v3 — DEF-214 EOD verification scope added)

**Purpose:** Amend the Session 5a.1 impl prompt to (a) note in the header that the prompt was amended post-planning by Tier 3 review #1 + Apr 27 paper-session debrief; (b) add Pre-Flight Checks for both `SystemAlertEvent.metadata` field existence AND the EOD verification path; (c) insert a new **Requirement 0 (DEF-213: schema extension + atomic emitter migration)** AND a new **Requirement 0.5 (DEF-214: EOD verification timing race + side-aware classification + distinct alert paths)** BEFORE the existing Requirement 1 (no renumbering of existing requirements 1–N — Requirements 0 and 0.5 are inserts, preserving every downstream cross-reference).

**Amendment history:**
- v1: original Patch 9 — DEF-213 only (`SystemAlertEvent.metadata` schema + atomic emitter migration as conditional Requirement 0).
- **v3 (current): adds DEF-214 scope** — EOD verification fix (poll-until-flat-with-timeout + side-aware classification + distinct alert paths) lands in 5a.1 alongside DEF-213, as Requirement 0.5. The two are sequenced because 0.5 depends on 0 (the new distinct alert types `eod_flatten_failed` and `eod_residual_shorts` use the `metadata` field that 0 introduces).

**Why this amendment is in scope for Tier 3 doc-sync:** Two structural gaps were identified.

**Gap 1 (DEF-213):** The 5a.1 impl prompt at lines 123 and 153 already references `event.metadata` on `SystemAlertEvent`, but the field doesn't exist on the current schema (`argus/core/events.py:405` has no `metadata` field). Session 1c's close-out §7 explicitly noted this gap. Without this amendment, the future 5a.1 implementer would either (a) discover the gap mid-implementation and have to scope-expand on the fly, or (b) work around it by parsing message strings, which forecloses Sessions 5b/5c/5d's structured-metadata access.

**Gap 2 (DEF-214):** The EOD flatten verification at `argus/execution/order_manager.py:~1729` fires CRITICAL with a synchronous poll BEFORE fills complete (timing race) AND conflates broker-only SHORTs that ARGUS intentionally does not flatten with longs whose flatten is in flight (side-blind classification). The Apr 27 paper-session debrief Finding 1 (debrief at `docs/debriefs/2026-04-27-paper-session-debrief.md`) provides the evidence: 42 long flatten orders submitted at 15:50:04, CRITICAL fired at 15:50:04, IBKR confirmed at 16:13 that all 42 longs DID close. Without this amendment, every EOD post-Sprint-31.91-seal fires a false-positive CRITICAL through the alert pipeline (HealthMonitor consumer + Session 5c banner + Session 5d toast), immediately polluting the alert-observability investment the entire 5-session subsprint is making.

**Anchor verification (must hold before applying):**
- Line 1: `# Sprint 31.91, Session 5a.1: HealthMonitor Consumer + REST Endpoints + Acknowledgment (Atomic + Idempotent)`
- Line 6: `## Pre-Flight Checks`
- Line 17: `   - All \`SystemAlertEvent\` emitter sites (subscription targets):`
- Line 63: `## Requirements`
- Line 65: `1. **Create \`AlertsConfig\` Pydantic model** in \`argus/core/config.py\`:`
- Line 524: end of file

---

## Patch A — Add amendment header note immediately after line 4 (the position-in-track blockquote)

### Find:

```
# Sprint 31.91, Session 5a.1: HealthMonitor Consumer + REST Endpoints + Acknowledgment (Atomic + Idempotent)

> **Track:** Alert Observability (Sessions 5a.1 → 5a.2 → 5b → 5c → 5d → 5e). Resolves DEF-014.
> **Position in track:** First session. Backend half-1 of alert observability per HIGH #1 split. Gates Tier 3 architectural review #2 after Session 5b lands.

## Pre-Flight Checks
```

### Replace with:

```
# Sprint 31.91, Session 5a.1: HealthMonitor Consumer + REST Endpoints + Acknowledgment (Atomic + Idempotent)

> **Track:** Alert Observability (Sessions 5a.1 → 5a.2 → 5b → 5c → 5d → 5e). Resolves DEF-014.
> **Position in track:** First session. Backend half-1 of alert observability per HIGH #1 split. Gates Tier 3 architectural review #2 after Session 5b lands.

> **Amendment 2026-04-27 (Tier 3 review #1 + Apr 27 paper-session debrief, additive only):** This prompt was amended post-planning to address two structural gaps. **(a) Tier 3 Concern C (DEF-213):** the consumer code at lines 123 and 153 references `event.metadata` on `SystemAlertEvent`, but the field doesn't exist on the current schema. The amendment adds Pre-Flight Check 7 (verify field existence) and Requirement 0 (schema extension + atomic emitter migration) BEFORE the existing Requirement 1. **(b) Apr 27 paper-session debrief Finding 1 (DEF-214):** the EOD flatten verification at `argus/execution/order_manager.py:~1729` fires a synchronous-poll false-positive CRITICAL that will pollute every EOD's alert pipeline once the HealthMonitor consumer + Session 5c banner + 5d toast are live. The amendment adds Pre-Flight Check 8 (locate EOD verification path) and Requirement 0.5 (poll-until-flat-with-timeout + side-aware classification + distinct alert paths) AFTER Requirement 0. Both inserts preserve existing requirement numbers 1–N to keep downstream cross-references stable. No semantic change to the existing 5a.1 consumer/REST/acknowledgment design — the amendments add the schema work and EOD-emitter cleanup that the consumer surface needs to function without immediate alert-fatigue. Per Sprint 31.91 `PHASE-D-OPEN-ITEMS.md` convention for Tier-3-driven additive scope clarifications, no re-running of adversarial review is required for these amendments. See verdict artifact `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` and DEF-213 + DEF-214 in CLAUDE.md.

## Pre-Flight Checks
```

---

## Patch B — Add a new pre-flight check (item 7) for SystemAlertEvent.metadata field existence

### Find (the end of the existing pre-flight check 6):

```
6. **Pre-flight grep — locate the HealthMonitor instantiation in `main.py`:**

   ```bash
   grep -n "HealthMonitor\|health_monitor" argus/main.py | head -10
   grep -n "subscribe\|register" argus/main.py | head -20
   ```

   The consumer init is the scoped exception in invariant 15. Identify the exact line where HealthMonitor is constructed; the SystemAlertEvent subscription line goes immediately after.

## Objective
```

### Replace with:

```
6. **Pre-flight grep — locate the HealthMonitor instantiation in `main.py`:**

   ```bash
   grep -n "HealthMonitor\|health_monitor" argus/main.py | head -10
   grep -n "subscribe\|register" argus/main.py | head -20
   ```

   The consumer init is the scoped exception in invariant 15. Identify the exact line where HealthMonitor is constructed; the SystemAlertEvent subscription line goes immediately after.

7. **Pre-flight grep — verify `SystemAlertEvent.metadata` field exists (DEF-213, Tier 3 Concern C):**

   ```bash
   grep -n "metadata\|SystemAlertEvent" argus/core/events.py | head -20
   ```

   The current `SystemAlertEvent` schema at `argus/core/events.py:405` has 4 fields: `source`, `alert_type`, `message`, `severity`. **No `metadata` field exists.** The 5a.1 consumer code at this prompt's lines 123 and 153 references `event.metadata`, which assumes the field has been added.

   **If `metadata: dict[str, Any] | None` is NOT present in `SystemAlertEvent`, do Requirement 0 (below) BEFORE proceeding to any other requirement.** If the field IS present (i.e., a prior session added it), skip Requirement 0 and proceed to Requirement 1.

   **Also enumerate the current emitter sites that need migration if you are doing Requirement 0:**

   ```bash
   grep -rn "SystemAlertEvent(" argus/ --include="*.py" | grep -v "_test\|tests/"
   ```

   Expected emitter sites at this Tier 3 gate (commit `bf7b869`):
   - `argus/data/databento_data_service.py` — pre-existing dead-feed emitter
   - `argus/execution/order_manager.py` — Session 1c's `_emit_cancel_propagation_timeout_alert` helper at `:2114-2152`, called from three sites: `_flatten_unknown_position` at `:1969`, `_drain_startup_flatten_queue` at `:2078`, `reconstruct_from_broker` at `:2226`

   Sessions 2b.1, 2b.2, 2c.1, 2d, 3 will add additional emitters during their own implementation. Those sessions land BEFORE 5a.1 in sprint order, so by the time 5a.1 runs, those emitter sites are also present and must be enumerated and migrated.

8. **Pre-flight grep — locate the EOD flatten verification path (DEF-214, Apr 27 Finding 1):**

   ```bash
   grep -n "after both passes\|positions remain\|EOD flatten" argus/execution/order_manager.py | head -20
   ```

   The Apr 27 paper-session debrief Finding 1 documented a synchronous-poll false-positive CRITICAL at this verification site. The current implementation polls `_managed_positions` and broker state at the same wall-clock second as flatten-order submission, BEFORE fills complete, and conflates broker-only SHORTs (intentionally not flattened — Sprint 30 deferred) with longs whose flatten is in flight. Identify:

   - The verification entry point (typically the Pass 2 epilogue in `eod_flatten()` or `_eod_flatten_pass2()`).
   - The exact `logger.critical(...)` call site that emits the "N positions remain after both passes" line.
   - The data structure used to enumerate "remaining positions" (likely a snapshot of `_managed_positions` + broker `get_positions()`).

   **Without DEF-214's fix landing in this session, every EOD post-Sprint-31.91-seal will fire false-positive CRITICAL through the alert pipeline you are building (HealthMonitor consumer → 5c banner → 5d toast).** Do Requirement 0.5 (below) AFTER Requirement 0 (the metadata schema must exist before the new alert types `eod_flatten_failed` / `eod_residual_shorts` can be emitted with structured side/shares/category fields).

## Objective
```

---

## Patch C — Insert new Requirement 0 BEFORE the existing Requirement 1

### Find:

```
## Requirements

1. **Create `AlertsConfig` Pydantic model** in `argus/core/config.py`:
```

### Replace with:

```
## Requirements

0. **(DEF-213, conditional on Pre-Flight Check 7 finding the field absent) Extend `SystemAlertEvent` schema with `metadata` field and atomically migrate all existing emitters.**

   **If Pre-Flight Check 7 confirmed `SystemAlertEvent.metadata` already exists, SKIP this requirement and proceed to Requirement 1.** Otherwise:

   **0.1 — Schema extension** at `argus/core/events.py:405` (or wherever `SystemAlertEvent` is defined):

   ```python
   class SystemAlertEvent(BaseEvent):
       """System-level alert event for cross-cutting operational concerns.

       Sprint 31.91 Session 5a.1 (DEF-213): added optional structured
       `metadata` field for typed consumer access. Emitters SHOULD populate
       metadata structurally rather than encoding into the message string;
       consumers (HealthMonitor, auto-resolution policy in 5b, frontend
       banner in 5c) read from `metadata` when present.
       """
       source: str
       alert_type: str
       message: str
       severity: str
       metadata: dict[str, Any] | None = None  # Sprint 31.91 S5a.1 (DEF-213)
   ```

   Add `from typing import Any` to the imports if not already present.

   **0.2 — Atomic emitter migration.** Update each existing emitter to populate `metadata` with structured fields. The migration MUST happen in the same commit as the schema extension so consumers never see a mixed schema.

   **Site 1: Databento dead-feed emitter** at `argus/data/databento_data_service.py`. Identify the existing `SystemAlertEvent(...)` construction (grep for it). Add a `metadata={...}` kwarg populated with the structured fields the dead-feed currently encodes into the message string (typically things like `last_tick_time`, `staleness_seconds`, etc. — read the existing message-string interpolation to identify the fields). Keep the `message` field for human-readable presentation; metadata is for typed consumers.

   **Site 2: `_emit_cancel_propagation_timeout_alert` helper** at `argus/execution/order_manager.py:2114-2152`. Update the helper signature to populate metadata atomically:

   ```python
   async def _emit_cancel_propagation_timeout_alert(
       self,
       *,
       source: str,
       stage: str,
       symbol: str,
       shares: int,
   ) -> None:
       """Emit a critical SystemAlertEvent for a cancel-propagation timeout.

       Sprint 31.91 Session 1c (D4) — shared emission helper for the three
       broker-only safety paths. Updated 2026-04-27 in Session 5a.1 (DEF-213)
       to populate structured metadata for HealthMonitor consumer access.
       """
       message = (
           f"cancel_all_orders did not propagate within timeout for "
           f"{symbol} (shares={shares}, stage={stage}). Position "
           f"remains at broker untouched. Manual flatten required: "
           f"scripts/ibkr_close_all_positions.py."
       )
       try:
           await self._event_bus.publish(
               SystemAlertEvent(
                   source=source,
                   alert_type="cancel_propagation_timeout",
                   message=message,
                   severity="critical",
                   metadata={
                       "symbol": symbol,
                       "shares": shares,
                       "stage": stage,
                   },
               )
           )
       except Exception:  # pragma: no cover - defensive
           logger.exception(
               "Failed to publish cancel_propagation_timeout "
               "SystemAlertEvent for %s",
               symbol,
           )
   ```

   The three call sites (`_flatten_unknown_position` at `:1969`, `_drain_startup_flatten_queue` at `:2078`, `reconstruct_from_broker` at `:2226`) need NO change — they already pass the `source`/`stage`/`symbol`/`shares` kwargs, and the helper populates metadata internally.

   **Sites 3+: Sessions 2b.1, 2b.2, 2c.1, 2d, 3 emitters.** These sessions land BEFORE 5a.1 in sprint order. By the time 5a.1 runs, those emitter sites exist and must be enumerated via the grep in Pre-Flight Check 7 and migrated to populate metadata. Each `phantom_short`/`phantom_short_retry_blocked`/etc. alert should populate the same conceptual fields (symbol, shares, stage, side, mechanism, etc. — whatever the alert's structured payload would naturally contain). **Do not skip emitters discovered during the grep**; atomic migration means all of them, in the same commit.

   **0.3 — Test for the schema extension and migration:** add a test in `tests/core/test_events.py` (or wherever `SystemAlertEvent` is tested) verifying:

   ```python
   def test_system_alert_event_has_optional_metadata_field():
       """Sprint 31.91 S5a.1 (DEF-213): metadata is optional dict[str, Any]."""
       evt = SystemAlertEvent(
           source="test",
           alert_type="test_alert",
           message="test message",
           severity="info",
       )
       assert evt.metadata is None  # default

       evt2 = SystemAlertEvent(
           source="test",
           alert_type="test_alert",
           message="test message",
           severity="info",
           metadata={"symbol": "AAPL", "shares": 100},
       )
       assert evt2.metadata == {"symbol": "AAPL", "shares": 100}
   ```

   And verify each migrated emitter populates metadata, e.g.:

   ```python
   async def test_cancel_propagation_timeout_alert_populates_metadata():
       """Sprint 31.91 S5a.1 (DEF-213): _emit_cancel_propagation_timeout_alert
       populates structured metadata for HealthMonitor consumer."""
       # ... mock event_bus, capture published event ...
       await order_manager._emit_cancel_propagation_timeout_alert(
           source="test",
           stage="flatten_unknown",
           symbol="AAPL",
           shares=100,
       )
       published = mock_event_bus.published_events[0]
       assert isinstance(published, SystemAlertEvent)
       assert published.metadata == {
           "symbol": "AAPL",
           "shares": 100,
           "stage": "flatten_unknown",
       }
   ```

   The exact test file location and existing fixture patterns should match what's already in the test suite for `SystemAlertEvent` and `_emit_cancel_propagation_timeout_alert` (the latter has tests added in Session 1c — extend those rather than duplicating).

   **0.4 — Verify no remaining message-string-only encoding paths.** After migration, run:

   ```bash
   grep -rn "SystemAlertEvent(" argus/ --include="*.py" | grep -v "_test\|tests/" | grep -v "metadata="
   ```

   Expected: zero results (every `SystemAlertEvent(...)` construction call site populates `metadata=...`).

   **0.5 — Acceptance criterion (sub-step within Requirement 0; distinct from the new top-level Requirement 0.5 below):** After Requirement 0 is complete, the consumer code in Requirement 2 below (lines 142-164 of this prompt, `on_system_alert_event` handler) accesses `event.metadata` directly without any defensive `getattr` or message-string parsing fallback. The existing Requirement 2 code at line 153 (`metadata=event.metadata or {}`) is the correct pattern: read metadata if present, fall back to empty dict for older emitters that haven't been migrated yet. After atomic migration in Requirement 0, the `or {}` fallback is defensive only.

0.5. **(DEF-214, Apr 27 paper-session debrief Finding 1) Fix EOD flatten verification: poll-until-flat-with-timeout + side-aware classification + distinct alert paths.**

   **Prerequisite:** Requirement 0 must be complete (the new alert types in this requirement use the `metadata` field that 0 introduces). If Requirement 0 was skipped because `SystemAlertEvent.metadata` already exists, you can proceed with this requirement directly.

   **Background:** the current EOD flatten verification at `argus/execution/order_manager.py:~1729` (located in Pre-Flight Check 8) emits a single `logger.critical("EOD flatten: N positions remain after both passes: [...]")` with three coupled defects:

   1. **Timing race.** The verification polls `_managed_positions` and broker state at the same wall-clock second as flatten-order submission, BEFORE fills complete. Apr 27 evidence: 42 long flatten orders submitted at 15:50:04, CRITICAL fired at 15:50:04 listing 85 positions remaining, IBKR confirmed at 16:13 that all 42 longs DID close.
   2. **Side-blind classification.** The "remaining" list conflates longs whose flatten is in flight with broker-only SHORTs that ARGUS intentionally does NOT flatten (Sprint 30 short-selling deferred; current safety posture is alert-and-skip on shorts via Session 2b.1's `phantom_short`).
   3. **Conflated CRITICAL emission.** Even after fixing (1) and (2), the actual-failure case (a long that genuinely failed to flatten after timeout) and the expected-residue case (intentionally-skipped shorts) currently flow through the same `logger.critical()` path.

   **0.5.1 — Replace synchronous poll with poll-until-flat-with-timeout (~30 LOC).**

   Replace the verification block with a polling loop. Suggested shape:

   ```python
   async def _verify_eod_flatten_complete(self) -> tuple[list[str], list[ManagedPosition]]:
       """Poll broker until long flattens settle or timeout.

       Sprint 31.91 Session 5a.1 (DEF-214): replaces the prior synchronous
       single-poll verification that fired false-positive CRITICAL before
       fills completed.

       Returns (residual_short_symbols, failed_long_positions). The two
       populations have distinct semantics: residual shorts are EXPECTED
       (Sprint 30 deferred), failed longs are ACTUAL FAILURES.
       """
       deadline = time.monotonic() + self._config.eod_verify_timeout_seconds  # default 30s
       poll_interval_seconds = self._config.eod_verify_poll_interval_seconds  # default 1.0
       failed_longs: list[ManagedPosition] = []
       residual_shorts: list[str] = []

       while time.monotonic() < deadline:
           broker_positions = await self._broker.get_positions()
           # Side-aware classification:
           # - Longs in _managed_positions that still appear at broker = potentially failing flatten.
           # - Broker positions where shares < 0 (or side=='short') = expected residue.
           failed_longs = [
               mp for mp in self._managed_positions.values()
               if any(bp.symbol == mp.symbol and bp.shares > 0 for bp in broker_positions)
           ]
           residual_shorts = [
               bp.symbol for bp in broker_positions if bp.shares < 0
           ]

           if not failed_longs:
               break  # all long flattens confirmed; only expected residue remains
           await asyncio.sleep(poll_interval_seconds)

       return residual_shorts, failed_longs
   ```

   **Add config fields** to `OrderManagerConfig` (or wherever EOD config lives in the existing 5a.1 prompt):

   ```python
   eod_verify_timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0)
   eod_verify_poll_interval_seconds: float = Field(default=1.0, ge=0.5, le=5.0)
   ```

   Update `config/system.yaml` and `config/system_live.yaml` with the new defaults.

   **0.5.2 — Distinct alert emissions (~20 LOC).**

   At the end of EOD flatten Pass 2, after `_verify_eod_flatten_complete()` returns:

   ```python
   residual_shorts, failed_longs = await self._verify_eod_flatten_complete()

   # Expected residue: residual shorts (Sprint 30 deferred). INFO/WARNING-level alert.
   if residual_shorts:
       await self._event_bus.publish(
           SystemAlertEvent(
               source="OrderManager.eod_flatten",
               alert_type="eod_residual_shorts",
               message=(
                   f"EOD flatten: {len(residual_shorts)} broker-only short positions "
                   f"remain after Pass 2 (intentional — Sprint 30 short-selling deferred). "
                   f"Operator manual flatten via scripts/ibkr_close_all_positions.py recommended."
               ),
               severity="warning",
               metadata={
                   "residual_short_symbols": sorted(residual_shorts),
                   "count": len(residual_shorts),
                   "category": "expected_residue",
               },
           )
       )

   # Actual failure: longs that did NOT flatten within timeout. CRITICAL-level alert.
   if failed_longs:
       logger.critical(
           "EOD flatten FAILURE: %d long positions did not close within %.1fs timeout: %s",
           len(failed_longs),
           self._config.eod_verify_timeout_seconds,
           sorted(mp.symbol for mp in failed_longs),
       )
       await self._event_bus.publish(
           SystemAlertEvent(
               source="OrderManager.eod_flatten",
               alert_type="eod_flatten_failed",
               message=(
                   f"EOD flatten FAILURE: {len(failed_longs)} long position(s) did not close "
                   f"within {self._config.eod_verify_timeout_seconds:.1f}s timeout. Manual "
                   f"intervention required: scripts/ibkr_close_all_positions.py."
               ),
               severity="critical",
               metadata={
                   "failed_long_symbols": sorted(mp.symbol for mp in failed_longs),
                   "count": len(failed_longs),
                   "timeout_seconds": self._config.eod_verify_timeout_seconds,
                   "category": "actual_failure",
               },
           )
       )

   # Clean case: no failed longs, no residual shorts. INFO log only; no alert.
   if not failed_longs and not residual_shorts:
       logger.info("EOD flatten verification complete: all positions flat at broker.")
   ```

   **0.5.3 — Tests (~30 LOC).**

   Extend `tests/execution/test_order_manager.py` (or wherever EOD flatten is tested) with three scenarios:

   - `test_eod_verify_clean_no_alert`: no longs and no shorts at broker after submission → INFO log, no `SystemAlertEvent` published.
   - `test_eod_verify_residual_shorts_warning`: 0 longs, N shorts at broker → exactly one `eod_residual_shorts` `SystemAlertEvent` with severity=warning, `metadata["category"] == "expected_residue"`, no critical log.
   - `test_eod_verify_failed_longs_critical`: longs still at broker after timeout → exactly one `eod_flatten_failed` `SystemAlertEvent` with severity=critical, `metadata["category"] == "actual_failure"`, AND a `logger.critical` call.
   - `test_eod_verify_polls_until_flat`: longs at broker for first 2 polls then absent → no `SystemAlertEvent` published (long flattens settled within timeout).

   Use `freezegun` or a controllable clock fixture to drive `time.monotonic()` deterministically. Mock `self._broker.get_positions()` with a side-effect list that simulates fills landing.

   **0.5.4 — Acceptance criterion (sub-step within Requirement 0.5):** the prior synchronous `logger.critical("N positions remain after both passes")` line is removed entirely. The new emissions go through `SystemAlertEvent` (per the metadata field added in Requirement 0). The HealthMonitor consumer in Requirement 2 receives the new alert types automatically (it subscribes to `SystemAlertEvent` regardless of `alert_type`); Session 5b's auto-resolution policy and Session 5c's banner will read the structured `metadata["category"]` field to route `eod_residual_shorts` to lower-severity UI surfaces vs. `eod_flatten_failed` to the critical-banner surface.

1. **Create `AlertsConfig` Pydantic model** in `argus/core/config.py`:
```

---

## Application notes

- **Four surgical replacements** (Patch A header note + Patch B pre-flight checks 7 AND 8 + Patch C Requirement 0 AND 0.5). The existing Requirements 1-N are NOT renumbered; Requirements 0 and 0.5 are inserts. This preserves every cross-reference elsewhere in the prompt that says "see Requirement 5" / "Requirement 3 above" / etc.
- **Two structural gaps closed by this amendment:** DEF-213 (`SystemAlertEvent.metadata` schema doesn't exist; consumer code already references it) and DEF-214 (EOD verification synchronous-poll false-positive CRITICAL would pollute the alert pipeline 5a.1 is building). Both are sprint-gating for 5a.1 — without them, 5a.1 either fails to compile or ships a self-defeating alert pipeline.
- **Conditional Requirement 0:** the requirement's "If absent, do this; if present, skip" structure handles the case where a future amendment to a prior session adds the field before 5a.1 lands. As of commit `bf7b869`, the field is absent and Requirement 0 is required.
- **Requirement 0.5 has no conditional skip** because the EOD verification timing race + side-blind classification exists in pre-OCA and post-OCA code regardless of whether OCA ships first; the false-positive CRITICAL fires identically. The fix must land before 5a.1's HealthMonitor consumer goes live.
- **Sites 3+ enumeration for Requirement 0:** the patch deliberately doesn't list specific 2b.1/2b.2/2c.1/2d/3 emitter sites because those sessions haven't planned/landed yet, so the grep enumeration in Pre-Flight Check 7 is the correct mechanism. Each future session's emitter will need to populate metadata from day one — Session 5a.1 sets the precedent.
- **Test scope is small for both:** Requirement 0 ~35 LOC of tests + ~50 LOC of migration. Requirement 0.5 ~30 LOC of tests + ~50 LOC of poll-loop + alert-emission code. Combined ~165 LOC across `events.py`, `databento_data_service.py`, `order_manager.py`, `config.py`, and tests — within 5a.1's compaction budget.
- **DEF-214 EOD verification implementation is independent of OCA architecture state.** The poll-until-flat-with-timeout fix is a logging/alerting refinement at the EOD verification site; it works identically before and after Sessions 0-1c land. The Apr 27 evidence (which ran PRE-OCA) already demonstrates the false-positive CRITICAL behavior; OCA architecture neither validates nor invalidates the fix.

Four surgical replacements. No other lines in the 5a.1 impl prompt are touched.
