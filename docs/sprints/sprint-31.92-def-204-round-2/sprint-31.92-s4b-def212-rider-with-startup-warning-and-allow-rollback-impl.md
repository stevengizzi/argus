# Sprint 31.92, Session S4b: DEF-212 Rider + AC4.6 Dual-Channel Startup Warning + AC4.7 `--allow-rollback` CLI Gate per H-R2-4 + Interactive Ack + Periodic Re-Ack + CI-Override Flag per Round 3 H-R3-4

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt. Particularly load-bearing for S4b: RULE-038 (grep-verify discipline against pre-flight claims), RULE-039 (staged risky-edit flow for the multi-site `_OCA_TYPE_BRACKET` substitution), RULE-050 (CI green precondition), RULE-053 (architectural-seal verification — DEC-386 4-layer OCA architecture is a sealed defense; AC4.5 byte-for-byte preservation is the seal).

2. Read these files to load context:
   - `argus/execution/order_manager.py` — anchor by the module-level `_OCA_TYPE_BRACKET` constant declaration AND the 4 `ocaType=_OCA_TYPE_BRACKET` use sites at OCA-thread sites. Verify count via grep before editing per protocol §"Implementation prompts: structural anchors over line numbers". **Absolute line numbers are DIRECTIONAL ONLY** per protocol v1.2.0+; structural anchors bind.
   - `argus/main.py` — anchor by class name `ArgusSystem` + the `OrderManager(...)` construction call site. Also anchor by the existing argparse / entry-point function (search for `argparse.ArgumentParser` or the equivalent CLI-flag parsing site).
   - `argus/core/config.py::IBKRConfig::bracket_oca_type` — existing Pydantic field per DEC-386 S1a (anchor by class name + field name). **Validator is UNCHANGED in S4b** — runtime-flippability per DEC-386 design intent is preserved; only the consumer side gains construction-time wiring.
   - `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Acceptance Criteria" Deliverable 4 (AC4.1–AC4.7) and §"Defense-in-Depth Cross-Layer Composition Tests" CL-2.
   - `docs/sprints/sprint-31.92-def-204-round-2/spec-by-contradiction.md` §"Do NOT modify" — particularly the `IBKRConfig.bracket_oca_type` Pydantic validator preservation clause.
   - `docs/sprints/sprint-31.92-def-204-round-2/round-3-disposition.md` §3.4 H-R3-4 (interactive ack + periodic re-ack + CI-override flag separation) and §"New Edge Case to Reject" SbC #19.

3. Run the test baseline (DEC-328 — Session 8 of 13 of sprint, **scoped** because S4b is non-final):

   ```
   python -m pytest tests/execution/order_manager/ tests/test_main.py -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S4a-ii's close-out and re-confirmed by M-R2-5's verdict-precondition test pass).

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** below. For each entry, run the verbatim grep-verify command and confirm the anchor still resolves to the expected location. If drift is detected, disclose under RULE-038 in the close-out and proceed against the actual structural anchors. If the anchor is not found at all, HALT and request operator disposition rather than guess.

   ```bash
   # Verify _OCA_TYPE_BRACKET sites — expect 5 hits (1 declaration + 4 use sites)
   grep -n "_OCA_TYPE_BRACKET" argus/execution/order_manager.py
   # Expected:
   #   1 declaration at module level (e.g., `_OCA_TYPE_BRACKET: int = 1`)
   #   4 use sites of form `order.ocaType = _OCA_TYPE_BRACKET`
   # If count != 5, B-class halt B11 fires (see Sprint-Level Escalation Criteria below).

   # Verify the OrderManager(...) construction call site in main.py — expect 1 hit
   grep -n "OrderManager(" argus/main.py
   # Expected: 1 construction call site (separate from imports / type-annotations).

   # Verify the existing IBKRConfig.bracket_oca_type field — expect 1 class + 1 field hit
   grep -n "class IBKRConfig\|bracket_oca_type" argus/core/config.py
   # Expected: at least the class definition + the field definition; the field is pre-existing per DEC-386.
   ```

6. Verify M-R2-5 mid-sprint Tier 3 verdict is CLEAR (PROCEED) before S4b begins:

   ```bash
   ls docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md && \
     grep -n "PROCEED" docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md | head -3
   ```

   If the verdict file is absent OR the verdict is REVISE_PLAN / PAUSE_AND_INVESTIGATE, **HALT** — S4b cannot begin until M-R2-5 clears.

## Objective

Wire the existing `IBKRConfig.bracket_oca_type` Pydantic field through `OrderManager.__init__` as a constructor keyword argument, eliminating the `_OCA_TYPE_BRACKET = 1` module constant in favor of `self._bracket_oca_type` at the 4 OCA-thread sites, and add an operator-visible safety gate at startup (dual-channel CRITICAL emission + `--allow-rollback` CLI flag + interactive ack + periodic re-ack + `--allow-rollback-skip-confirm` CI override) so that a rollback to `bracket_oca_type=0` cannot occur silently. DEF-212 closure (constant drift wiring) and AC4.6 + AC4.7 + Round 3 H-R3-4 amendments are delivered together because all touch the same `OrderManager.__init__` + `argus/main.py` surface.

## Requirements

1. **Extend `OrderManager.__init__` signature** in `argus/execution/order_manager.py` to accept `bracket_oca_type: int` keyword argument and store it on the instance:

   ```python
   def __init__(
       self,
       *,
       event_bus: EventBus,
       broker: Broker,
       clock: Clock,
       config: OrderManagerConfig,
       trade_logger: TradeLogger,
       db_manager: DBManager,
       broker_source: BrokerSource,
       reconciliation_config: ReconciliationConfig,
       startup_config: StartupConfig,
       exit_config: ExitManagementConfig,
       strategy_exit_overrides: dict[str, ExitOverride] | None = None,
       operations_db_path: str,
       bracket_oca_type: int,  # NEW — DEF-212 wiring per AC4.1
   ) -> None:
       ...
       self._bracket_oca_type: int = bracket_oca_type
   ```

   The argument is **keyword-only** (no default) — callers MUST pass it explicitly. This preserves call-site auditability and surfaces missing-arg breakage at construction time, not at first OCA emission. (AC4.1)

2. **Replace the 4 `_OCA_TYPE_BRACKET` use sites** with `self._bracket_oca_type`:

   ```python
   # Before (4 sites in order_manager.py at OCA-thread emission points):
   order.ocaType = _OCA_TYPE_BRACKET

   # After:
   order.ocaType = self._bracket_oca_type
   ```

   Use the staged risky-edit flow per RULE-039: (1) read-only exploration to confirm the 4 site list; (2) produce a structured findings report listing file:line for each site + the planned edit; (3) write the report to `docs/sprints/sprint-31.92-def-204-round-2/s4b-edit-manifest.md`; (4) **HALT** and surface the report; (5) apply edits exactly as listed. (AC4.3)

3. **Delete the module constant** `_OCA_TYPE_BRACKET: int = 1` from `argus/execution/order_manager.py` AFTER all 4 use sites have been migrated. The deletion is the AC4.3 signal — invariant 15 establishes here. (AC4.3)

4. **Update `argus/main.py` `OrderManager(...)` construction call site** to thread the config field through:

   ```python
   self._order_manager = OrderManager(
       event_bus=self._event_bus,
       broker=self._broker,
       clock=self._clock,
       config=order_manager_config,
       trade_logger=self._trade_logger,
       db_manager=self._db,
       broker_source=self._config.system.broker_source,
       reconciliation_config=reconciliation_config,
       startup_config=startup_config,
       exit_config=exit_config,
       strategy_exit_overrides=strategy_exit_overrides,
       operations_db_path=str(
           Path(config.system.data_dir) / "operations.db"
       ),
       bracket_oca_type=config.ibkr.bracket_oca_type,  # NEW per AC4.2
   )
   ```

   This is the **ONLY permitted modification** to `argus/main.py:1081` per spec-by-contradiction §"Do NOT modify" exception clause for S4b. Do NOT modify any surrounding initialization logic. (AC4.2)

5. **Add `--allow-rollback` CLI flag parsing** to `argus/main.py`'s entry point. The flag is a boolean store-true with no value:

   ```python
   parser.add_argument(
       "--allow-rollback",
       action="store_true",
       default=False,
       help=(
           "REQUIRED to start ARGUS when bracket_oca_type != 1. "
           "Without this flag, ARGUS exits with code 2 and a stderr "
           "FATAL banner. With this flag plus a TTY, ARGUS prompts "
           "for the exact phrase 'I ACKNOWLEDGE ROLLBACK ACTIVE' "
           "before proceeding. CI environments use "
           "--allow-rollback-skip-confirm to bypass the interactive "
           "prompt."
       ),
   )
   parser.add_argument(
       "--allow-rollback-skip-confirm",
       action="store_true",
       default=False,
       help=(
           "Bypass the interactive rollback ack for unattended (CI) "
           "starts. REQUIRES --allow-rollback to also be present. "
           "MUST NOT be used in production startup scripts (SbC §19)."
       ),
   )
   ```

   (AC4.7; H-R3-4 CI override)

6. **Implement the `--allow-rollback` gate logic** in `argus/main.py`'s startup path, immediately after config load and before `OrderManager` construction:

   ```python
   if config.ibkr.bracket_oca_type != 1:
       if not args.allow_rollback:
           # AC4.7 path (a): exit code 2 + stderr FATAL banner
           sys.stderr.write(
               "\n[FATAL] DEC-386 ROLLBACK REQUESTED WITHOUT --allow-rollback FLAG.\n"
               "        config.ibkr.bracket_oca_type=%d. Refusing to start.\n"
               % config.ibkr.bracket_oca_type
           )
           sys.exit(2)
       # AC4.7 path (b) + AC4.6 dual-channel emission
       _emit_dec386_rollback_critical(config.ibkr.bracket_oca_type)
       # H-R3-4: interactive ack required when TTY detected, unless skip-confirm
       if sys.stdin.isatty() and not args.allow_rollback_skip_confirm:
           prompt = "I ACKNOWLEDGE ROLLBACK ACTIVE"
           print(
               f"DEC-386 ROLLBACK ACTIVE. Type exactly the phrase below to "
               f"proceed (anything else exits with code 3):\n{prompt}\n> ",
               end="",
               flush=True,
           )
           response = sys.stdin.readline().rstrip("\n")
           if response != prompt:
               sys.stderr.write(
                   "[FATAL] Rollback ack phrase mismatch. Exiting (code 3).\n"
               )
               sys.exit(3)
       # H-R3-4: schedule periodic re-ack every 4 hours during runtime
       self._schedule_periodic_rollback_reack(
           config.ibkr.bracket_oca_type
       )
   # else: bracket_oca_type == 1 → --allow-rollback flag is a no-op (AC4.7)
   ```

   The exact placement (function vs. method; module-level helper vs. instance method) is a judgment call to preserve `argus/main.py`'s existing architecture; document the choice in the close-out's "Judgment Calls" section. (AC4.6, AC4.7, H-R3-4)

7. **Implement the dual-channel emission helper** `_emit_dec386_rollback_critical(bracket_oca_type: int) -> None`:

   ```python
   def _emit_dec386_rollback_critical(bracket_oca_type: int) -> None:
       """Dual-channel CRITICAL emission per AC4.6 / H-R2-4.

       Emits the rollback warning to BOTH:
       - ntfy.sh `system_warning` urgent (topic: argus_system_warnings)
       - Canonical-logger CRITICAL with phrase "DEC-386 ROLLBACK ACTIVE"
       """
       message = (
           f"DEC-386 ROLLBACK ACTIVE: bracket_oca_type={bracket_oca_type}. "
           f"OCA enforcement on bracket children is DISABLED. "
           f"DEF-204 race surface is REOPENED. "
           f"Operator must restore to 1 and restart unless emergency "
           f"rollback in progress."
       )
       logger.critical(message)
       _publish_ntfy_system_warning(message, topic="argus_system_warnings")
   ```

   The `_publish_ntfy_system_warning` helper either already exists in the ARGUS notifications path (verify via grep) OR is a thin shim around `requests.post("https://ntfy.sh/argus_system_warnings", ...)` with `Priority: urgent`. Preserve whichever pattern ARGUS already uses for ntfy.sh emissions; if no precedent exists, add a minimal urlopen-based shim. (AC4.6)

8. **Implement the periodic re-ack loop** per H-R3-4:

   ```python
   def _schedule_periodic_rollback_reack(self, bracket_oca_type: int) -> None:
       """Periodic re-ack: every 4 hours, re-emit dual-channel CRITICAL
       with phrase 'DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE
       — N hours since startup'."""
       startup_monotonic = time.monotonic()
       async def _reack_loop():
           while True:
               await asyncio.sleep(4 * 3600)  # 4 hours
               hours_elapsed = int(
                   (time.monotonic() - startup_monotonic) / 3600
               )
               message = (
                   f"DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — "
                   f"{hours_elapsed} hours since startup. "
                   f"bracket_oca_type={bracket_oca_type}."
               )
               logger.critical(message)
               _publish_ntfy_system_warning(
                   message, topic="argus_system_warnings"
               )
       self._reack_task = asyncio.create_task(_reack_loop())
   ```

   The task is held on the `ArgusSystem` instance so it survives until shutdown. (AC4.6, H-R3-4)

## Files to Modify

For each file the session edits, specify:

- **`argus/execution/order_manager.py`**:
  - **Anchor 1:** module-level `_OCA_TYPE_BRACKET` constant declaration.
    - Edit shape: deletion (after the 4 use sites are migrated to `self._bracket_oca_type`).
    - Pre-flight grep-verify:
      ```
      $ grep -n "^_OCA_TYPE_BRACKET" argus/execution/order_manager.py
      # Expected: 1 hit (the declaration). Directional only.
      ```
  - **Anchor 2:** 4 use sites of `order.ocaType = _OCA_TYPE_BRACKET`.
    - Edit shape: replacement of `_OCA_TYPE_BRACKET` → `self._bracket_oca_type` at each site.
    - Pre-flight grep-verify:
      ```
      $ grep -n "ocaType = _OCA_TYPE_BRACKET" argus/execution/order_manager.py
      # Expected: 4 hits. If != 4, B-class halt B11 fires.
      ```
  - **Anchor 3:** `OrderManager.__init__` method signature.
    - Edit shape: insertion of `bracket_oca_type: int` keyword-only parameter + assignment to `self._bracket_oca_type`.
    - Pre-flight grep-verify:
      ```
      $ grep -n "def __init__" argus/execution/order_manager.py | head -10
      # Expected: at least 1 hit on OrderManager class (multiple if other classes share name).
      ```

- **`argus/main.py`**:
  - **Anchor 1:** the existing `OrderManager(...)` construction call site.
    - Edit shape: insertion of `bracket_oca_type=config.ibkr.bracket_oca_type` kwarg in the existing kwarg list.
    - Pre-flight grep-verify:
      ```
      $ grep -n "OrderManager(" argus/main.py
      # Expected: 1 construction call site (excluding imports / type annotations).
      ```
  - **Anchor 2:** the existing argparse parser setup site.
    - Edit shape: insertion of `--allow-rollback` and `--allow-rollback-skip-confirm` `add_argument` calls.
    - Pre-flight grep-verify:
      ```
      $ grep -n "argparse.ArgumentParser\|add_argument" argus/main.py | head -10
      # Expected: existing argparse usage. Insert new args alongside.
      ```
  - **Anchor 3:** the startup/lifespan path immediately after config load and before `OrderManager` construction.
    - Edit shape: insertion of the `--allow-rollback` gate logic + dual-channel emission call + interactive-ack prompt + periodic re-ack scheduling.
    - Pre-flight grep-verify:
      ```
      $ grep -n "load_config\|config.ibkr" argus/main.py | head -10
      # Expected: anchors near the config-load surface.
      ```

Line numbers MAY appear as directional cross-references but are NEVER the sole anchor. **All line numbers cited in this prompt are DIRECTIONAL ONLY per protocol v1.2.0+.**

## Constraints

- **Do NOT modify:**
  - `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA threading) — preserve byte-for-byte. AC4.5 must hold.
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used by Path #1's existing short-circuit; NOT modified, NOT relocated.
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path).
  - `argus/execution/order_manager.py::reconstruct_from_broker` body (Sprint 31.94 D1's surface).
  - `argus/execution/order_manager.py::reconcile_positions` Pass 1/2 (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check at lines ~3424–3489 (DEF-158).
  - `argus/main.py::check_startup_position_invariant` (Sprint 31.94 D2).
  - `argus/main.py::_startup_flatten_disabled` (Sprint 31.94 D2).
  - `argus/core/config.py::IBKRConfig.bracket_oca_type` Pydantic validator — runtime-flippability preserved per DEC-386 design intent.
  - `argus/core/health.py` consumer + `POLICY_TABLE`.
  - `argus/api/routes/alerts.py`, `argus/api/websocket/alerts_ws.py`.
  - `argus/frontend/...` (entire frontend; Vitest stays at 913).
  - `data/operations.db` schema, `data/argus.db` schemas.
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md` (preserve per Phase A leave-as-historical decision).
  - The `workflow/` submodule (RULE-018).

- **Do NOT change:**
  - DEC-386 OCA threading semantics. The OCA-threading SEMANTICS must remain identical — only the source of `ocaType` value changes from module constant to instance attribute. (Invariant 6)
  - DEC-117 atomic-bracket invariants. AC4.5 byte-for-byte preservation is the seal. (Invariant 1)
  - The four standalone `cancel_all_orders(symbol, await_propagation=True)` callers wired by DEC-386 S0/S1c.
  - The pre-existing `--allow-rollback` flag absent path — the flag is NEW in S4b; if the grep-verify above shows it already exists, HALT (rare, but possible if a parallel sprint added it).

- **Do NOT add:**
  - A second config field. AC4.2 wires the existing `IBKRConfig.bracket_oca_type`; do not introduce `bracket_oca_type_v2` or similar.
  - A custom alert channel beyond ntfy.sh + canonical-logger. AC4.6 dual-channel is the contract.
  - A persistence path for the periodic re-ack timer state. The re-ack is in-memory; restart re-emits the startup-time CRITICAL.
  - `--allow-rollback-skip-confirm` consumption by production startup scripts. SbC §19 explicitly rejects this.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

S4b does not require operator pre-check. The DEF-212 wiring + AC4.6 dual-channel + AC4.7 `--allow-rollback` gate + H-R3-4 interactive ack semantics are committed-to in `sprint-spec.md` §"Acceptance Criteria" Deliverable 4 and `round-3-disposition.md` §3.4.

## Canary Tests

Before making any changes, run these canary tests to confirm baseline behavior:

- `test_dec386_oca_invariants_preserved_byte_for_byte` (or whatever the existing DEC-386 OCA-threading regression is named) — confirms DEC-386 S1a/S1b behavior pre-S4b.
- `test_bracket_order_places_three_children_under_parent` — confirms DEC-117 parent-child structure pre-S4b.

These set the "before" baseline for the after-implementation regression check.

## Risky Batch Edit — Staged Flow

S4b's `_OCA_TYPE_BRACKET` substitution is a 4-site multi-call refactor. Execute the session in five explicit phases per RULE-039 + protocol v1.2.0:

1. **Read-only exploration** of `argus/execution/order_manager.py` around each of the 5 grep hits (1 declaration + 4 use sites). No edits.
2. **Produce a structured findings report:** exact site list (file:line), the planned edit per site, the verification-grep that will run after the edits.
3. **Write the report** to `docs/sprints/sprint-31.92-def-204-round-2/s4b-edit-manifest.md`. Include the exact diff each site will produce.
4. **Halt.** Surface the report to the operator and wait for confirmation. Operator confirms by either replying "proceed" OR by editing the manifest with corrections.
5. **Apply edits** exactly as listed in the confirmed manifest.

The same staged flow applies to the `argus/main.py` insertion (CLI flag parsing + gate logic + dual-channel helper + periodic re-ack scheduling). Document both stages in the close-out's "Edit Manifest" section.

## Test Targets

After implementation:

- **Existing tests:** all must still pass.
- **New tests in `tests/execution/order_manager/test_def212_oca_type_wiring.py`:**

  1. `test_order_manager_init_accepts_bracket_oca_type` (AC4.1)
     - Construct `OrderManager(..., bracket_oca_type=1)` and `OrderManager(..., bracket_oca_type=0)` separately; assert both succeed and `_bracket_oca_type` instance attribute matches.
  2. `test_no_oca_type_bracket_constant_remains_in_module` — **grep regression guard** (AC4.3 / invariant 15)
     - Read `argus/execution/order_manager.py` source; assert ZERO occurrences of the literal `_OCA_TYPE_BRACKET`. Mental-revert sanity check: re-introducing the constant string into the source MUST fail this test.
  3. `test_bracket_oca_type_1_threads_through_to_bracket_children` — preserves DEC-386 S1a default behavior
     - Mock IBKR; place a bracket; assert all 3 children Order objects have `ocaType == 1`.
  4. `test_bracket_oca_type_lockstep_preserved_under_rollback` — parametrized over the 4 OCA-thread sites with `bracket_oca_type ∈ {0, 1}` (AC4.4 / invariant 16)
     - Test docstring explicitly: "ocaType=0 disables OCA enforcement and reopens DEF-204; this test asserts the rollback path is consistent, not that the rollback is operationally safe."
     - Asserts that flipping from 1 to 0 produces consistent `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence). 4 sites × {0, 1} = 8 effective parametrize cases.
  5. `test_main_py_call_site_passes_config_field` (AC4.2)
     - Inspect `argus/main.py` source for the `OrderManager(...)` construction kwargs; assert the literal `bracket_oca_type=config.ibkr.bracket_oca_type` (or semantically equivalent) appears in the kwarg list.
  6. `test_startup_dual_channel_warning_emitted_when_bracket_oca_type_zero_with_allow_rollback` (AC4.6)
     - Instantiate ARGUS startup path with `config.ibkr.bracket_oca_type=0` AND `--allow-rollback` flag set AND `--allow-rollback-skip-confirm` set (to bypass TTY prompt in test); capture log output AND mock the ntfy.sh emission.
     - Assert: canonical-logger CRITICAL line contains exact phrase `"DEC-386 ROLLBACK ACTIVE"`.
     - Assert: ntfy.sh `system_warning` urgent emission fires with topic `argus_system_warnings`.
     - **Both channels must fire** — silent suppression of either is the failure mode C11 catches.
  7. `test_startup_exits_2_with_fatal_banner_when_bracket_oca_type_zero_without_allow_rollback` (AC4.7)
     - Instantiate ARGUS startup path with `config.ibkr.bracket_oca_type=0` AND `--allow-rollback` flag ABSENT; assert process exits with code 2; assert stderr contains exact phrase `"DEC-386 ROLLBACK REQUESTED WITHOUT --allow-rollback FLAG. Refusing to start."`.
  8. `test_dec386_oca_invariants_preserved_byte_for_byte` — bonus regression (AC4.5)
     - Confirms DEC-386 S1a/S1b OCA-threading + atomic-bracket invariants survive S4b edit pass. The test exists pre-S4b; this row asserts it remains green at S4b close-out.
  9. `test_startup_interactive_ack_required_when_rollback_active_and_tty` (H-R3-4 / invariant 33)
     - Mock `sys.stdin.isatty()` returning True; mock `sys.stdin.readline()` returning `"I ACKNOWLEDGE ROLLBACK ACTIVE\n"`; instantiate startup with `bracket_oca_type=0` + `--allow-rollback`; assert ARGUS proceeds (does not exit).
  10. `test_startup_exits_3_when_rollback_active_and_tty_and_wrong_phrase` (H-R3-4 / invariant 33)
      - Same setup as test 9 but `readline()` returns `"yes\n"` (or any non-matching string); assert exit code 3.
  11. `test_startup_skip_confirm_flag_bypasses_interactive_ack_for_ci` (H-R3-4 / invariant 33)
      - `--allow-rollback-skip-confirm` flag present + `bracket_oca_type=0` + `--allow-rollback` flag present; mock `isatty()` returning True (to ensure skip-confirm overrides TTY detection); assert ARGUS proceeds without prompt; **assert canonical-logger CRITICAL emission still fires** (CI evidence trail preserved).
  12. `test_periodic_reack_emits_every_4h_when_rollback_active` (H-R3-4 / invariant 33)
      - Mock `asyncio.sleep` to advance synthetic-time by 4 hours; assert that on each 4-hour boundary, the canonical-logger CRITICAL emission fires with phrase "DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — N hours since startup" AND ntfy.sh emission fires.

  **Effective test count: 12 logical / ~14 effective with parametrize** (test 4 is parametrized × 4 sites × {0, 1} = 8 effective cases; tests 1, 6 also have minor parametrization).

- **Test command** (scoped per DEC-328, S4b is non-final):

  ```
  python -m pytest tests/execution/order_manager/ tests/test_main.py -n auto -q
  ```

## Config Validation

S4b consumes the existing `IBKRConfig.bracket_oca_type` field (per DEC-386 S1a). No new config field is added. Therefore no config-validation test is required at S4b. Verify that `config/system.yaml` and `config/system_live.yaml` already contain `ibkr.bracket_oca_type: 1` explicitly (DEC-386 S1a contract); if absent, file under "Deferred Items" rather than fix in S4b.

## Marker Validation (N/A this session)

S4b does not add pytest markers.

## Visual Review (N/A this session)

S4b is backend-only. No frontend changes per invariant 12 (frontend immutability).

## Definition of Done

- [ ] `OrderManager.__init__` accepts `bracket_oca_type: int` keyword arg (AC4.1).
- [ ] `argus/main.py` construction call site passes `bracket_oca_type=config.ibkr.bracket_oca_type` (AC4.2).
- [ ] Module constant `_OCA_TYPE_BRACKET` deleted; 4 use sites migrated to `self._bracket_oca_type` (AC4.3 / invariant 15).
- [ ] `bracket_oca_type` lock-step preserved under rollback (AC4.4 / invariant 16).
- [ ] DEC-386 OCA invariants preserved byte-for-byte (AC4.5).
- [ ] Dual-channel CRITICAL emission on rollback start (AC4.6 / H-R2-4).
- [ ] `--allow-rollback` gate: exit code 2 + stderr FATAL banner when absent and rollback requested (AC4.7).
- [ ] `--allow-rollback-skip-confirm` CI override flag implemented (H-R3-4 / invariant 33).
- [ ] Interactive ack at startup when TTY detected (H-R3-4).
- [ ] Periodic re-ack every 4 hours emits dual-channel CRITICAL (H-R3-4).
- [ ] All 12 new tests passing.
- [ ] Edit manifest produced and confirmed (RULE-039 staged-flow gate).
- [ ] CI green on the session's final commit (RULE-050).
- [ ] Tier 2 review via @reviewer subagent — verdict CLEAR (or CONCERNS_RESOLVED).
- [ ] Close-out report written to file.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `_OCA_TYPE_BRACKET` constant deleted; zero occurrences in source | `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` returns `0` (invariant 15) |
| 4 OCA-thread sites use `self._bracket_oca_type` | `grep -c "ocaType = self._bracket_oca_type" argus/execution/order_manager.py` returns `4` |
| `OrderManager(...)` construction in `main.py` passes `bracket_oca_type` | `grep -n "bracket_oca_type=config.ibkr.bracket_oca_type" argus/main.py` returns 1 hit |
| `argus/execution/ibkr_broker.py::place_bracket_order` byte-for-byte unchanged | `git diff HEAD~1 -- argus/execution/ibkr_broker.py` shows zero edits in the bracket-placement region |
| `IBKRConfig.bracket_oca_type` Pydantic validator unchanged | `git diff HEAD~1 -- argus/core/config.py` shows zero edits in the validator (invariant 6 specific edge) |
| `argus/main.py::check_startup_position_invariant` unchanged | `git diff HEAD~1 -- argus/main.py` shows zero edits in that function (Sprint 31.94 boundary) |
| `argus/main.py::_startup_flatten_disabled` unchanged | grep + diff verify |
| Frontend immutability holds | `git diff HEAD~1 -- 'argus/ui/'` returns empty (invariant 12) |
| Pytest baseline ≥ 5,269 (target after S4b: ~5,332–5,357) | `python -m pytest --ignore=tests/test_main.py -n auto -q \| tail -3` (close-out skill runs full suite) |
| Pre-existing flake count unchanged | DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 all still skip/pass per baseline (invariant 11) |
| ntfy.sh emission and canonical-logger CRITICAL both fire under `bracket_oca_type=0` + `--allow-rollback` | Test 6 asserts both; manual smoke if needed |
| Exit code 2 + stderr FATAL banner under `bracket_oca_type=0` + flag absent | Test 7 asserts |
| Exit code 3 when TTY detected and wrong ack phrase | Test 10 asserts |
| Periodic re-ack emits at 4-hour boundary | Test 12 asserts via mocked `asyncio.sleep` |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4b-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full report (including the structured JSON appendix) to it, and commit it.

The close-out MUST include:
- The edit manifest produced at the staged-flow Halt step (link or inline).
- A "Judgment Calls" section noting the placement of the `--allow-rollback` gate logic + dual-channel helper + periodic re-ack scheduling within `argus/main.py`'s existing architecture (function vs. method; module-level vs. instance helper).
- Any RULE-038 disclosures if pre-flight grep-verify revealed drift from spec line numbers.
- Cumulative-diff line count tracking: `git diff <session-base>..HEAD -- argus/execution/order_manager.py | wc -l` and `git diff <session-base>..HEAD -- argus/main.py | wc -l`.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.92-def-204-round-2/session-s4b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (S4b is non-final → scoped per DEC-328): `python -m pytest tests/execution/order_manager/ tests/test_main.py -n auto -q`
5. Files that should NOT have been modified (full do-not-modify list above):
   - `argus/execution/ibkr_broker.py` (DEC-386 S1a/S1b OCA threading + helper preservation)
   - `argus/execution/order_manager.py::_handle_oca_already_filled`
   - `argus/execution/order_manager.py::reconstruct_from_broker` body (Sprint 31.94 D1)
   - `argus/execution/order_manager.py::reconcile_positions` Pass 1/2
   - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check
   - `argus/main.py::check_startup_position_invariant`
   - `argus/main.py::_startup_flatten_disabled`
   - `argus/core/config.py::IBKRConfig.bracket_oca_type` Pydantic validator
   - `argus/core/health.py`, `argus/api/routes/alerts.py`, `argus/api/websocket/alerts_ws.py`
   - Frontend
   - DB schemas
   - DEC-385 / DEC-386 / DEC-388 entries in decision-log
   - The `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.92-def-204-round-2/session-s4b-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, you MUST update the artifact trail so it reflects reality:

1. **Append a "Post-Review Fixes" section to the close-out report file.** Include a table of finding → fix → commit hash.
2. **Append a "Resolved" annotation to the review report file.** Update the structured verdict JSON `"verdict"` to `"CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **Constant deletion completeness.** `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` MUST return 0 post-S4b. Any docstring or comment that historically referenced the constant must use `# OCA-EXEMPT: <reason>` per protocol if retained for context.

2. **4-site migration consistency.** All 4 OCA-thread sites must use `self._bracket_oca_type`. The lock-step test (test 4) parametrized over 4 sites is the structural assertion; verify it covers all 4 sites enumerated by the pre-S4b grep.

3. **DEC-386 byte-for-byte preservation (AC4.5).** `argus/execution/ibkr_broker.py::place_bracket_order` must show ZERO edits. The OCA-threading semantics flow through `OrderManager` only; `ibkr_broker.py`'s bracket-placement contract is untouched.

4. **`OrderManager.__init__` keyword-only argument.** The new `bracket_oca_type` parameter must be keyword-only (no default). This forces call-site auditability — verify the construction site in `argus/main.py` passes the value explicitly.

5. **Dual-channel emission both fires under rollback (AC4.6).** Test 6 asserts both channels fire. Reviewer must verify the implementation calls BOTH `logger.critical(...)` AND `_publish_ntfy_system_warning(...)`. A logging-only implementation is the C11 failure mode.

6. **Exit code precision (AC4.7 + H-R3-4).** Three distinct exit codes: 2 (no `--allow-rollback`), 3 (interactive ack wrong phrase), 0 (success / `bracket_oca_type=1` no-op). Verify each test asserts the exact integer.

7. **Interactive ack TTY detection (H-R3-4).** The interactive prompt MUST only fire when `sys.stdin.isatty()` returns True AND `--allow-rollback-skip-confirm` is absent. The skip-confirm flag is the CI escape hatch; production startup MUST NOT use it (SbC §19).

8. **Periodic re-ack runtime task survival.** The 4-hour periodic re-ack task must be held on `ArgusSystem` (or the equivalent owning surface) so it is not garbage-collected mid-runtime. Verify the task is not left as a dangling local.

9. **`argus/main.py:1081` exception-clause respect.** SbC §"Do NOT modify" allows S4b to modify the `OrderManager(...)` construction call site to add `bracket_oca_type=...`. Reviewer must verify the modification is SCOPED to that single kwarg insertion + the new gate-logic block + the new CLI flag parsing — no surrounding logic is touched.

10. **Edit manifest exists and was confirmed.** Per RULE-039, the staged-flow Halt step requires an edit manifest at `docs/sprints/sprint-31.92-def-204-round-2/s4b-edit-manifest.md`. Reviewer verifies the manifest exists and that the actual diff matches the manifest's planned edits.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S4b per the Per-Session Verification Matrix:

- **Invariant 1 (DEC-117 atomic bracket):** PASS — AC4.5 byte-for-byte preservation; `argus/execution/ibkr_broker.py::place_bracket_order` shows zero edits.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS — preserved.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS — OCA-threading semantics preserved; only the source of `ocaType` value changes from module constant to instance attribute.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS — preserved.
- **Invariant 10 (test count baseline ≥ 5,269):** PASS — target at S4b: 5,332–5,357.
- **Invariant 11 (pre-existing flake count):** PASS — DEF-150/167/171/190/192 unchanged.
- **Invariant 12 (frontend immutability):** PASS — zero `argus/ui/` edits.
- **Invariant 15 (NEW — `_OCA_TYPE_BRACKET` constant deleted):** ESTABLISHES — grep-guard test 2 enforces.
- **Invariant 16 (AC4.4 OCA-type lock-step):** ESTABLISHES — parametrized test 4 enforces.
- **Invariant 33 (NEW per Round 3 H-R3-4 — interactive ack + CI-override flag separation):** ESTABLISHES — tests 9, 10, 11, 12 enforce.

▢-soft (trust test suite unless suspicious diff): invariants 13, 19, 20, 22.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to S4b:

- **A4 (DEC-385/386/388 do-not-modify violation):** halt + revert if `argus/execution/ibkr_broker.py::place_bracket_order` OR DEC-386 helpers OR `_handle_oca_already_filled` OR `reconcile_positions` Pass 1/2 modified.
- **A10 (mechanism breaks DEC-117 atomic-bracket invariants):** halt; the do-not-modify boundary on DEC-117 was crossed.
- **B11 (`_OCA_TYPE_BRACKET` count mismatch on grep):** halt at S4b pre-flight if `grep -c "_OCA_TYPE_BRACKET"` returns ≠ 5 (1 declaration + 4 use sites). Re-anchor symbolically and proceed only after operator confirms the actual occurrence count matches the intended replacement scope.
- **C11 (startup CRITICAL warning silent log destination):** verify dual-channel emission per H-R2-4 / AC4.6 is fully wired (ntfy.sh AND canonical-logger). Both emissions captured at startup; tested via log-capture fixture in test 6. If either channel is silently filtered → investigate log-handler config.
- **C12 (`--allow-rollback` flag verification):** continue with extra scrutiny. AC4.7 has two paths: flag present (test 6) + flag absent (test 7). Both paths need explicit regression tests.
- **B1, B3, B4, B6, B8** — standard halt conditions.

### Verification Grep Precision

When running verification greps:
- Use `grep -c` (count) for the `_OCA_TYPE_BRACKET` constant-deletion check; expected value is 0 post-S4b.
- Use `grep -n` (line-number) for the 4 use-site migration check; expected value is 4 hits matching `ocaType = self._bracket_oca_type`.
- For dual-channel emission verification: scan only the helper `_emit_dec386_rollback_critical` body, not docstrings; the rejection rationale (in the warning message itself) names the prior pattern (`"DEC-386 ROLLBACK ACTIVE"`) — that is not a reintroduction.

---

*End Sprint 31.92 Session S4b implementation prompt.*
