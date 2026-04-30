# Sprint 31.92, Session 3a: Path #2 Fingerprint + Position-Keyed Suppression Dict + 4 OrderManagerConfig Fields

> **⚠️ PENDING OPERATOR CONFIRMATION**
>
> This prompt is finalized only when:
> 1. S1b JSON artifact at `scripts/spike-results/spike-def204-round2-path2-results.json` is committed to `main` AND
> 2. Operator confirms in writing the `recommended_locate_suppression_seconds` value from S1b's spike output (the value is baked into the Pydantic field's default at code-generation time per the H6 / sprint-spec § Config Changes contract; if H6 RULES OUT, default falls to 18000s with documented rationale per the spec) AND
> 3. The exact substring fingerprint string from S1b (typically `"contract is not available for short sale"`) is captured in the JSON's fingerprint field for verbatim copy into `_LOCATE_REJECTED_FINGERPRINT`.
>
> The Pre-Flight Checks below assume the spike artifact is present. If absent, halt and surface to operator.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-039 (risky batch edit staging), RULE-050 (CI green) apply. The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt.

2. Read these files to load context (4 reads — consolidated per Round-1-revised
   option δ; the `ManagedPosition` definition is covered as part of reading
   `OrderManager.__init__`):
   - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` (reference
     pattern for the new `_is_locate_rejection` helper; mirrors DEC-386's helper
     shape — accepts `BaseException`, performs case-insensitive substring match;
     anchor by helper name)
   - `argus/execution/order_manager.py::OrderManager.__init__` and
     `ManagedPosition` dataclass definition (locate where the
     `_locate_suppressed_until` dict goes; `position.id` is a ULID per DEC-026;
     anchor by class names + method name)
   - `argus/core/config.py::OrderManagerConfig` + `IBKRConfig` (Pydantic
     patterns; the 4 new fields land on `OrderManagerConfig`; anchor by class
     names)
   - `scripts/spike-results/spike-def204-round2-path2-results.json` (S1b output
     — `recommended_locate_suppression_seconds` field + exact fingerprint string
     are the binary gates)

3. Run the test baseline (DEC-328 — Session 5+ of sprint, scoped):

   ```
   python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py -n auto -q
   ```

   Expected: all passing (full suite was confirmed by S2b's close-out).
   Note: In autonomous mode, the expected test count is dynamically adjusted
   by the runner based on the previous session's actual results.

4. Verify you are on the correct branch: **`main`**.

5. **Run the structural-anchor grep-verify commands** from the "Files to Modify"
   section below. For each entry, run the verbatim grep-verify command and confirm
   the anchor still resolves to the expected location. If drift is detected,
   disclose under RULE-038 in the close-out and proceed against the actual
   structural anchors. If the anchor is not found at all, HALT and request
   operator disposition rather than guess.

6. **Verify S1b artifact present and PROCEED:**

   ```bash
   test -f scripts/spike-results/spike-def204-round2-path2-results.json && \
     python -c "
   import json,sys
   r=json.load(open('scripts/spike-results/spike-def204-round2-path2-results.json'))
   ok = (r.get('status')=='PROCEED' and 'recommended_locate_suppression_seconds' in r)
   secs = r.get('recommended_locate_suppression_seconds', 0)
   in_range = (300 <= secs <= 86400)
   print(f'status={r.get(\"status\")}, secs={secs}, in_range={in_range}')
   sys.exit(0 if ok and in_range else 1)
   " \
     && echo "S1b artifact OK" \
     || { echo "S1b artifact missing or out-of-range — HALT"; exit 1; }
   ```

   Read the JSON's `recommended_locate_suppression_seconds` value AND the exact
   fingerprint substring string. Both are baked into production code at this
   session:
   - The fingerprint string becomes the value of the new
     `_LOCATE_REJECTED_FINGERPRINT` constant in `argus/execution/ibkr_broker.py`.
   - The seconds value becomes the Pydantic field default for
     `OrderManagerConfig.locate_suppression_seconds`.

   If the seconds value is OUTSIDE the validator range [300, 86400] — escalation
   B9 fires (release window > 86400s) and the session halts. If H6 ruled out (no
   release events observed), the JSON should encode a fallback value of 18000s
   per the spec's H6 rules-out path; the Pydantic field default uses that value.

## Objective

Add the Path #2 detection helper + position-keyed suppression state + 4 new
`OrderManagerConfig` fields. NO emit-site wiring — that is S3b's responsibility.
This session lays down the helpers that S3b consumes.

Specifically:
1. Add `_LOCATE_REJECTED_FINGERPRINT` substring constant (verbatim from S1b
   spike) and `_is_locate_rejection()` helper in `argus/execution/ibkr_broker.py`,
   mirroring DEC-386's `_is_oca_already_filled_error` pattern.
2. Add `OrderManager._locate_suppressed_until: dict[ULID, float]` position-keyed
   suppression state and `_is_locate_suppressed(position, now)` helper using
   `time.monotonic()` (per H-R3-1).
3. Add **four** new `OrderManagerConfig` fields:
   - `locate_suppression_seconds` (S1b-driven default; range [300, 86400];
     monotonic-time semantics per H-R3-1 footnote).
   - `long_only_sell_ceiling_enabled` (default `True`).
   - `long_only_sell_ceiling_alert_on_violation` (default `True`).
   - `pending_sell_age_watchdog_enabled` (default `"auto"`;
     `Literal["auto", "enabled", "disabled"]`; per Decision 4).

## Requirements

1. **In `argus/execution/ibkr_broker.py`**, add the substring constant and
   `_is_locate_rejection()` helper near the existing
   `_is_oca_already_filled_error` helper:

   ```python
   # Captured by S1b spike — verbatim string from IBKR error payload on
   # locate-rejection of hard-to-borrow microcap symbols. Substring match,
   # case-insensitive via str(error).lower().
   _LOCATE_REJECTED_FINGERPRINT = "<exact-string-from-S1b-JSON>"


   def _is_locate_rejection(error: BaseException) -> bool:
       """Parses IBKR error to distinguish locate-rejection (hard-to-borrow,
       Path #2 surface) from other 201-class errors (margin, OCA-already-filled,
       price-protection).

       S1b spike (scripts/spike_def204_round2_path2.py) confirmed the exact
       substring `_LOCATE_REJECTED_FINGERPRINT`. Mirrors DEC-386's
       `_is_oca_already_filled_error` shape — accepts BaseException,
       case-insensitive substring match.

       Args:
           error: Any exception caught at place_order(SELL) emit sites.

       Returns:
           True iff the error message contains the locate-rejection fingerprint
           substring (case-insensitive); False otherwise.
       """
       msg = str(error).lower()
       return _LOCATE_REJECTED_FINGERPRINT.lower() in msg
   ```

   Both the constant and the helper live at module scope (NOT inside a class),
   matching DEC-386's existing helper placement.

2. **In `argus/execution/order_manager.py`**, in `OrderManager.__init__`, add
   the position-keyed suppression dict:

   ```python
   # Position-keyed locate-rejection suppression state per Round-1 H-2
   # (cross-position safety preserved). Keyed by ManagedPosition.id (ULID
   # per DEC-026). Values are absolute monotonic-time deadlines per H-R3-1
   # (time.monotonic() + locate_suppression_seconds).
   self._locate_suppressed_until: dict[ULID, float] = {}
   ```

   Then add the `_is_locate_suppressed` helper as a method on `OrderManager`:

   ```python
   def _is_locate_suppressed(self, position: ManagedPosition, now: float) -> bool:
       """Returns True iff the position is currently within its
       locate-rejection suppression window (per AC2.2).

       Keyed by ManagedPosition.id ULID (NOT symbol — cross-position safety
       per Round-1 H-2). The `now` parameter is monotonic time per Round 3
       H-R3-1; suppression-timeout comparisons are wall-clock-skew-resilient.

       Args:
           position: The managed position checked for suppression.
           now: Current monotonic time (typically time.monotonic() at call site).

       Returns:
           True iff now < self._locate_suppressed_until.get(position.id, 0.0).
       """
       return now < self._locate_suppressed_until.get(position.id, 0.0)
   ```

   **Do NOT add emit-site wiring at this session.** S3b wires the helpers into
   the 4 standalone-SELL paths (`_flatten_position`, `_trail_flatten`,
   `_check_flatten_pending_timeouts`, `_escalation_update_stop` exception
   handlers). This session establishes the surface; the next session consumes it.

3. **In `argus/core/config.py::OrderManagerConfig`**, add the 4 new fields.
   The `<spike_value>` placeholder below is replaced verbatim with the value
   from S1b's `recommended_locate_suppression_seconds` field at code-generation
   time. If H6 ruled out, `<spike_value>` is `18000` per the H6 rules-out path:

   ```python
   from typing import Literal


   class OrderManagerConfig(BaseModel):
       # ... existing fields preserved verbatim ...

       locate_suppression_seconds: int = Field(
           default=<spike_value>,
           ge=300,
           le=86400,
           description=(
               "Seconds to suppress further SELL emissions on a "
               "locate-rejected ManagedPosition. Bounds [300, 86400] "
               "are seconds in monotonic time per H-R3-1 footnote; "
               "equivalent to wall-clock under normal operation. Default "
               "is the S1b spike's measured p99 hold-pending-borrow "
               "release window plus 20%, with hard floor 18000s (5hr) "
               "if H6 ruled out (no release events observed)."
           ),
       )

       long_only_sell_ceiling_enabled: bool = Field(
           default=True,
           description=(
               "Fail-closed gate for the long-only SELL-volume ceiling "
               "(AC3.8). When False, _check_sell_ceiling returns True "
               "unconditionally — for explicit operator override during "
               "emergency rollback ONLY. No third state."
           ),
       )

       long_only_sell_ceiling_alert_on_violation: bool = Field(
           default=True,
           description=(
               "Whether _check_sell_ceiling refusals emit "
               "sell_ceiling_violation SystemAlertEvent (AC3.3 / AC3.9 "
               "POLICY_TABLE entry — manual operator-ack only). "
               "Defaults True."
           ),
       )

       pending_sell_age_watchdog_enabled: Literal["auto", "enabled", "disabled"] = Field(
           default="auto",
           description=(
               "AC2.7 watchdog activation mode (per Decision 4). "
               "'auto' (default) flips to 'enabled' on first observed "
               "case_a_in_production event in production paper trading; "
               "'enabled' fires watchdog when pending-SELL age exceeds "
               "threshold AND no fill observed; 'disabled' suppresses "
               "watchdog entirely. Storage is in-memory only per H-R3-2; "
               "auto→enabled flip is asyncio.Lock-guarded; restart "
               "resets to 'auto'."
           ),
       )
   ```

   Per session-breakdown.md final scope (lines 567–584), the **Pydantic-surface
   tests for the ceiling fields** (`long_only_sell_ceiling_enabled`,
   `long_only_sell_ceiling_alert_on_violation`) and for `pending_sell_age_watchdog_enabled`
   land at S4a-i, NOT this session. This session ADDS the fields to the model
   AND tests only `locate_suppression_seconds` Pydantic validation (test 6 below).

4. **In `config/order_management.yaml`** (or wherever the operator-facing
   `OrderManagerConfig` YAML overlay lives — verify the exact path during
   pre-flight): surface the new `pending_sell_age_watchdog_enabled` field with
   its default value `auto`. Per Decision 4, the field is operator-visible
   so operators can manually flip to `enabled` or `disabled` if desired.

   The other 3 fields (`locate_suppression_seconds`,
   `long_only_sell_ceiling_enabled`, `long_only_sell_ceiling_alert_on_violation`)
   are also added to the YAML overlay if convention dictates, but the Pydantic
   defaults are sufficient — the YAML override is operationally for operator
   adjustments, not for sprint-time configuration. Verify the project's
   convention during pre-flight; surface only what the convention requires.

5. **Tests — create
   `tests/execution/order_manager/test_def204_round2_path2.py`** (~100 LOC for
   6 tests; will grow at S3b). The 6 tests at this session:

   - `test_is_locate_rejection_matches_canonical_string` — exact string from
     S1b spike; assert `_is_locate_rejection(SomeException(<exact-string>))`
     returns True (AC2.1).
   - `test_is_locate_rejection_case_insensitive` — assert returns True for
     UPPERCASE, lowercase, MixedCase variants of the fingerprint substring.
   - `test_is_locate_rejection_returns_false_for_other_201_errors` — assert
     returns False for canonical 201 messages (margin: "margin requirement not
     met"; OCA-already-filled: "OCA group is already filled"; price-protection:
     similar).
   - `test_is_locate_suppressed_position_keyed_returns_true_within_window` —
     uses `position.id` (ULID) as key + `time.monotonic()` per H-R3-1; constructs
     a `ManagedPosition` (with appropriate fixture); sets
     `om._locate_suppressed_until[position.id] = time.monotonic() + 300`;
     asserts `om._is_locate_suppressed(position, time.monotonic())` returns True
     (AC2.2).
   - `test_is_locate_suppressed_returns_false_after_window_expiry` — same setup;
     advance `now` past the deadline (e.g., `now = time.monotonic() + 301` after
     setting deadline to `time.monotonic() + 300`); assert returns False.
   - `test_locate_suppression_seconds_pydantic_validation` — config field range
     [300, 86400]; assert `OrderManagerConfig(locate_suppression_seconds=299)`
     raises `ValidationError`; assert `OrderManagerConfig(locate_suppression_seconds=86401)`
     raises `ValidationError`; assert `OrderManagerConfig(locate_suppression_seconds=300)`
     and `OrderManagerConfig(locate_suppression_seconds=86400)` succeed; assert
     the default value matches `<spike_value>` from S1b.

   **Per session-breakdown.md mitigation (lines 567–584):** Pydantic tests for
   the **ceiling fields** + the **`pending_sell_age_watchdog_enabled` field's
   Pydantic surface** + **auto-mode flip semantics** all land at S4a-i, not
   this session. S3a's tests cover only `_LOCATE_REJECTED_FINGERPRINT` +
   suppression dict + `locate_suppression_seconds` Pydantic surface.

6. **Config Validation test** (mandatory; see § "Config Validation" below):
   write a test that loads `config/system_live.yaml` + `config/order_management.yaml`
   and asserts no keys under `order_manager.*` are absent from
   `OrderManagerConfig.model_fields.keys()`. Per regression-checklist.md "New
   `OrderManagerConfig` fields verified against Pydantic model" item.

## Files to Modify

For each file the session edits, specify:

1. **`argus/execution/ibkr_broker.py`** (MODIFY):
   - Anchor: function `_is_oca_already_filled_error` (existing module-level
     helper). The new `_LOCATE_REJECTED_FINGERPRINT` constant + new
     `_is_locate_rejection` helper land near it (typically immediately after).
   - Edit shape: insertion (constant + helper, ~15 LOC).
   - Pre-flight grep-verify:
     ```
     $ grep -n "def _is_oca_already_filled_error\|_OCA_ALREADY_FILLED_FINGERPRINT" argus/execution/ibkr_broker.py
     # Expected: ≥2 hits (helper + constant). The new helper + new constant
     # mirror this placement; do NOT relocate either DEC-386 helper.
     $ grep -n "_LOCATE_REJECTED_FINGERPRINT\|_is_locate_rejection" argus/execution/ibkr_broker.py
     # Expected: 0 hits pre-session.
     ```

2. **`argus/execution/order_manager.py`** (MODIFY):
   - Anchor (PRIMARY): `OrderManager.__init__` (the dict initialization site).
   - Anchor (SECONDARY): `OrderManager` class body (the new
     `_is_locate_suppressed` method site — placement near related helpers like
     `_handle_oca_already_filled`).
   - Edit shape: insertion (1-line dict init + helper method, ~15 LOC total).
   - Pre-flight grep-verify:
     ```
     $ grep -n "class OrderManager" argus/execution/order_manager.py
     # Expected: exactly 1 hit. (Directional only — verify the class still
     # exists at the structural anchor.)
     $ grep -n "def __init__" argus/execution/order_manager.py | head -3
     # Expected: ≥1 hit; the OrderManager.__init__ is the one near the class
     # declaration. (Use the class anchor to disambiguate from other __init__s
     # in the file.)
     $ grep -n "_locate_suppressed_until\|_is_locate_suppressed" argus/execution/order_manager.py
     # Expected: 0 hits pre-session.
     ```

3. **`argus/core/config.py`** (MODIFY):
   - Anchor: class `OrderManagerConfig`. The 4 new fields land at the bottom
     of the class body (preserving existing field ordering per SbC §"Do NOT
     refactor").
   - Edit shape: insertion (4 Pydantic Field declarations, ~30 LOC).
   - Pre-flight grep-verify:
     ```
     $ grep -n "class OrderManagerConfig" argus/core/config.py
     # Expected: exactly 1 hit.
     $ grep -n "locate_suppression_seconds\|long_only_sell_ceiling_enabled\|pending_sell_age_watchdog_enabled" argus/core/config.py
     # Expected: 0 hits pre-session.
     ```

4. **`config/order_management.yaml`** (MODIFY):
   - Anchor: top-level YAML key `order_manager:` (or whatever the existing top-
     level key is; verify during pre-flight).
   - Edit shape: insertion (`pending_sell_age_watchdog_enabled: "auto"` under
     the `order_manager:` block, plus the other 3 fields if convention dictates).
   - Pre-flight grep-verify:
     ```
     $ test -f config/order_management.yaml && head -5 config/order_management.yaml
     # Expected: file exists; first key is order_manager: (verify).
     # If file does NOT exist, locate the actual YAML overlay with a grep:
     $ grep -rn "order_manager:" config/*.yaml | head -5
     # Identify the actual file; document the path used in the close-out.
     ```

5. **`tests/execution/order_manager/test_def204_round2_path2.py`** (NEW FILE):
   - Anchor: file does not exist yet; create at the specified path under the
     existing `tests/execution/order_manager/` directory.
   - Edit shape: insertion (new file ≤150 LOC for 6 logical tests).
   - Pre-flight grep-verify:
     ```
     $ ls -la tests/execution/order_manager/test_def204_round2_path2.py 2>&1 | head -1
     # Expected: "No such file or directory" (file does not yet exist).
     ```

6. **`tests/core/test_config_yaml_pydantic_alignment.py`** (NEW FILE OR EXTEND):
   - Anchor: if a similar config-validation test file already exists (e.g.,
     `tests/core/test_config.py` or `tests/test_config_validation.py`), EXTEND
     it with one new test. Otherwise, create a new file. Verify during
     pre-flight.
   - Edit shape: insertion of one config-validation test asserting YAML keys
     under `order_manager.*` are a subset of `OrderManagerConfig.model_fields.keys()`.
   - Pre-flight grep-verify:
     ```
     $ grep -rn "OrderManagerConfig.*model_fields" tests/ | head -5
     # If existing tests already exercise this pattern, extend the existing file.
     # If 0 hits, create a new file at tests/core/test_config_yaml_pydantic_alignment.py.
     ```

## Constraints

- Do NOT modify:
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` and
    `_OCA_ALREADY_FILLED_FINGERPRINT` — re-used by Path #1's existing
    short-circuit; NOT modified, NOT relocated (relocation deferred to Sprint
    31.93 per SbC §"Out of Scope" #4).
  - `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA
    threading).
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b
    SAFE-marker path).
  - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface).
  - `argus/execution/order_manager.py::_resubmit_stop_with_retry`,
    `_escalation_update_stop` (S2b's surfaces).
  - `argus/execution/order_manager.py::reconstruct_from_broker` (Sprint 31.94 D1).
  - `argus/execution/order_manager.py::reconcile_positions` (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch
    side-check (DEF-158 fix anchor `a11c001`) — preserved verbatim per
    regression invariant 8.
  - `argus/execution/order_manager.py::_check_sell_ceiling`,
    `_reserve_pending_or_fail` — these are S4a-i's surfaces.
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces).
  - `argus/models/trading.py::Position` class.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py` — `HealthMonitor` consumer + `POLICY_TABLE` (S4a-i
    adds the 14th entry).
  - `argus/core/config.py::IBKRConfig::bracket_oca_type` — already exists; AC4
    only changes the consumer side at S4b.
  - The `workflow/` submodule (Universal RULE-018).
  - Frontend (`argus/ui/`, `frontend/`) — Vitest must remain at 913.

- Do NOT change:
  - DEC-117, DEC-364, DEC-372, DEC-385, DEC-386, DEC-388 (regression invariants
    1, 2, 4, 5, 6, 7).
  - `OrderManagerConfig` field ordering or class structure beyond ADDING the 4
    new fields (per SbC §"Do NOT refactor").
  - `IBKRConfig` (no changes this session — `bracket_oca_type` exists; S4b is
    its consumer).

- Do NOT add:
  - Emit-site wiring in any of the 4 standalone-SELL paths (`_flatten_position`,
    `_trail_flatten`, `_check_flatten_pending_timeouts`,
    `_escalation_update_stop`). That is S3b's responsibility.
  - The `_check_sell_ceiling` or `_reserve_pending_or_fail` methods. Those are
    S4a-i's surfaces.
  - The `cumulative_pending_sell_shares`, `cumulative_sold_shares`,
    `is_reconstructed`, `halt_entry_until_operator_ack` fields on
    `ManagedPosition`. Those are S4a-i's surfaces.
  - A new alert type. The `phantom_short_retry_blocked` alert is reused per
    DEC-385 L4. The `sell_ceiling_violation` alert is added at S4a-i.
  - A new helper module under `argus/execution/`. The 2 new helpers
    (`_is_locate_rejection` in `ibkr_broker.py`,
    `_is_locate_suppressed` in `order_manager.py`) live in their respective
    existing modules.
  - The `Broker.refresh_positions()` ABC method. That is S3b's surface.
  - Any new pytest markers.

- Do NOT cross-reference other session prompts. This prompt is standalone.

## Operator Choice (N/A this session)

Session 3a does not require operator pre-check beyond the PENDING OPERATOR
CONFIRMATION preamble (which already gates on S1b's
`recommended_locate_suppression_seconds` value). The fingerprint string + the
seconds value are data-driven from the spike, not operator-judgment calls.

## Canary Tests (if applicable)

Before making any changes, run the canary-test skill in
`.claude/skills/canary-test.md` with these tests to confirm baseline behavior:

- A pre-existing `OrderManagerConfig` Pydantic test (e.g.,
  `test_order_manager_config_defaults`) — confirms the existing field surface
  pre-Session-3a; the new 4 fields will be additive.
- A pre-existing `_is_oca_already_filled_error` regression test (or
  equivalent) — confirms the helper pattern that `_is_locate_rejection`
  mirrors.

These set the "before" baseline.

## Test Targets

After implementation:

- Existing tests: all must still pass (regression invariant 10; baseline
  ≥5,269 pytest plus S2a's +6/+7 + S2b's +7).
- New tests (6 logical) in
  `tests/execution/order_manager/test_def204_round2_path2.py` per Requirement 5.
- One new config-validation test (Requirement 6).
- Minimum new test count: **6** (S3a delta is +6 per regression checklist
  line 156).
- Test command (scoped per DEC-328):

  ```
  python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py -n auto -q
  ```

  Plus the config-validation test path:

  ```
  python -m pytest tests/core/ -n auto -q
  ```

## Config Validation

This session adds 4 new fields to `OrderManagerConfig`. Per regression-checklist.md
"New `OrderManagerConfig` fields verified against Pydantic model" item, write a
test that loads the YAML config files and verifies all keys under the relevant
section are recognized by the Pydantic model:

1. Load `config/system_live.yaml` AND `config/order_management.yaml` (or
   whichever YAML files the operator-facing overlay lives in; verify during
   pre-flight).
2. Extract the keys under `order_manager.*` (or the equivalent top-level key).
3. Compare against `OrderManagerConfig.model_fields.keys()`.
4. Assert no keys are present in YAML that are absent from the model
   (these would be silently ignored by Pydantic and use defaults instead of
   operator-specified values).

```python
def test_order_manager_yaml_keys_subset_of_pydantic_model():
    """Sprint 31.92 Session 3a: verify the YAML overlay's order_manager keys
    are a subset of OrderManagerConfig's Pydantic field names; otherwise
    operator-specified YAML values silently fall through to model defaults
    (silent-drop class)."""
    import yaml
    from argus.core.config import OrderManagerConfig

    # Verify config/system_live.yaml:
    with open("config/system_live.yaml") as fh:
        cfg = yaml.safe_load(fh) or {}
    om_cfg = cfg.get("order_manager", {})
    yaml_keys = set(om_cfg.keys())
    model_fields = set(OrderManagerConfig.model_fields.keys())
    extra = yaml_keys - model_fields
    assert not extra, (
        f"config/system_live.yaml has order_manager keys not in "
        f"OrderManagerConfig: {extra}"
    )

    # Same for config/order_management.yaml:
    import os
    if os.path.exists("config/order_management.yaml"):
        with open("config/order_management.yaml") as fh:
            cfg2 = yaml.safe_load(fh) or {}
        om_cfg2 = cfg2.get("order_manager", cfg2)  # may be top-level
        yaml_keys2 = set(om_cfg2.keys()) if isinstance(om_cfg2, dict) else set()
        extra2 = yaml_keys2 - model_fields
        assert not extra2, (
            f"config/order_management.yaml has order_manager keys not in "
            f"OrderManagerConfig: {extra2}"
        )
```

Expected mapping (the 4 new fields):

| YAML Path | Pydantic Field | Default | Validator |
|-----------|---------------|---------|-----------|
| `order_manager.locate_suppression_seconds` | `OrderManagerConfig.locate_suppression_seconds` | `<spike_value>` (S1b spike — typically 18000 if H6 ruled out) | `Field(default=<spike_value>, ge=300, le=86400)` (footnote: bounds in monotonic time per H-R3-1) |
| `order_manager.long_only_sell_ceiling_enabled` | `OrderManagerConfig.long_only_sell_ceiling_enabled` | `True` | `Field(default=True)` |
| `order_manager.long_only_sell_ceiling_alert_on_violation` | `OrderManagerConfig.long_only_sell_ceiling_alert_on_violation` | `True` | `Field(default=True)` |
| `order_management.pending_sell_age_watchdog_enabled` | `OrderManagerConfig.pending_sell_age_watchdog_enabled` | `"auto"` | `Field(default="auto")` with `Literal["auto", "enabled", "disabled"]` |

## Marker Validation (N/A this session)

Session 3a does not add pytest markers.

## Risky Batch Edit — Staged Flow (N/A this session)

Session 3a's edit footprint is small (4 modified files + 1 or 2 new test files;
no cross-file rename or move). A risky-batch-edit staged flow is not required.

## Visual Review (N/A this session)

No UI changes. Backend-only session.

## Definition of Done

- [ ] S1b artifact verification (Pre-Flight #6) passed; fingerprint string +
      seconds value extracted.
- [ ] `_LOCATE_REJECTED_FINGERPRINT` constant + `_is_locate_rejection()`
      helper added to `argus/execution/ibkr_broker.py` near
      `_is_oca_already_filled_error`.
- [ ] `OrderManager._locate_suppressed_until: dict[ULID, float]` added to
      `OrderManager.__init__`.
- [ ] `OrderManager._is_locate_suppressed(position, now)` helper added.
- [ ] 4 new `OrderManagerConfig` fields added with correct defaults +
      validators per Requirement 3.
- [ ] `config/order_management.yaml` (or equivalent) updated with
      `pending_sell_age_watchdog_enabled` (and other 3 fields per project
      convention).
- [ ] All 6 new tests in `tests/execution/order_manager/test_def204_round2_path2.py`
      written and passing.
- [ ] Config-validation test (mandatory per § Config Validation above) written
      and passing — verifies YAML→Pydantic alignment with no silent-drop class.
- [ ] All existing pytest baseline still passing (≥5,269 plus S2a + S2b
      additions).
- [ ] Vitest count = 913 (regression invariant 12).
- [ ] `_is_locate_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT`
      unchanged (DEC-386 reuse, not relocation; regression invariant 6).
- [ ] DEF-158 3-branch side-check verbatim (regression invariant 8 — even
      though this session does NOT touch that surface, the regression must
      hold).
- [ ] No do-not-modify list file appears in `git diff HEAD~1`.
- [ ] CI green on session's final commit (RULE-050).
- [ ] Close-out report written to file.
- [ ] Tier 2 review completed via @reviewer subagent.

## Regression Checklist (Session-Specific)

After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| `_LOCATE_REJECTED_FINGERPRINT` constant value matches S1b JSON exact-string | grep + manual cross-check against `scripts/spike-results/spike-def204-round2-path2-results.json` fingerprint field |
| `_is_locate_rejection` returns True for canonical string + case variants | Tests 1+2 green |
| `_is_locate_rejection` returns False for other 201 errors | Test 3 green |
| `_is_locate_suppressed` returns True within window using `time.monotonic()` | Test 4 green |
| `_is_locate_suppressed` returns False after window expiry | Test 5 green |
| `OrderManagerConfig.locate_suppression_seconds` Pydantic validation enforces [300, 86400] | Test 6 green |
| `OrderManagerConfig.locate_suppression_seconds` default matches S1b `recommended_locate_suppression_seconds` | Test 6 green; close-out documents the actual value baked in |
| 4 new `OrderManagerConfig` fields present | grep `model_fields` enumeration |
| YAML→Pydantic alignment: no silent-drop class | Config-validation test green |
| `_is_oca_already_filled_error` and `_OCA_ALREADY_FILLED_FINGERPRINT` unchanged | `git diff HEAD~1 -- argus/execution/ibkr_broker.py` shows only ADDITIONS, no MODIFICATIONS to existing helpers |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_handle_oca_already_filled` empty | DEC-386 S1b preserved |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_trail_flatten` empty | S2a's surface unchanged |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_resubmit_stop_with_retry` empty | S2b's surface unchanged |
| `git diff HEAD~1 -- argus/execution/order_manager.py::reconstruct_from_broker` empty | Sprint 31.94 D1 surface untouched |
| `git diff HEAD~1 -- argus/execution/order_manager.py::_check_flatten_pending_timeouts` lines ~3424–3489 empty | DEF-158 3-branch side-check verbatim (regression invariant 8) |
| `git diff HEAD~1 -- argus/main.py` empty | Sprint 31.94 D1+D2 surfaces untouched |
| `git diff HEAD~1 -- frontend/` and `argus/ui/` empty | Frontend immutability (regression invariant 12) |
| Vitest count unchanged at 913 | `cd argus/ui && npx vitest run --reporter=basic` |
| Pre-existing flake count unchanged | CI run: DEF-150, DEF-167, DEF-171, DEF-190, DEF-192 (regression invariant 11) |

## Close-Out

After all work is complete, follow the close-out skill in
`.claude/skills/close-out.md`.

The close-out report MUST include:

1. **A "S1b Spike Output Consumed" section** explicitly citing the
   `recommended_locate_suppression_seconds` value baked into the Pydantic
   default AND the verbatim fingerprint string copied into
   `_LOCATE_REJECTED_FINGERPRINT`. This section is consumed by S3b's
   pre-flight read.
2. **A "Helpers Established for S3b" section** listing the new helpers
   (`_is_locate_rejection`, `_is_locate_suppressed`) with their signatures,
   so S3b can wire them into the 4 standalone-SELL paths without
   re-discovering the helper shape.
3. **A "YAML Overlay Path" section** documenting the actual YAML file path
   used for `pending_sell_age_watchdog_enabled` (in case the project's
   convention diverged from the prompt's `config/order_management.yaml`
   default).
4. **A structured JSON appendix** at the end, fenced with
   ` ```json:structured-closeout `.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/session-3a-closeout.md
```

Do NOT just print the report in the terminal. Create the file, write the full
report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file:
   `docs/sprints/sprint-31.92-def-204-round-2/review-context.md`
2. The close-out report path:
   `docs/sprints/sprint-31.92-def-204-round-2/session-3a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped per DEC-328; non-final session):
   `python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py tests/core/ -n auto -q`
5. Files that should NOT have been modified:
   - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error`,
     `_OCA_ALREADY_FILLED_FINGERPRINT`, `place_bracket_order`
   - `argus/execution/order_manager.py::_handle_oca_already_filled`
   - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface)
   - `argus/execution/order_manager.py::_resubmit_stop_with_retry`,
     `_escalation_update_stop` (S2b's surfaces)
   - `argus/execution/order_manager.py::reconstruct_from_broker`
   - `argus/execution/order_manager.py::reconcile_positions`
   - `argus/execution/order_manager.py::_check_flatten_pending_timeouts`
     (lines ~3424–3489 — DEF-158 3-branch side-check)
   - `argus/execution/order_manager.py::_check_sell_ceiling`,
     `_reserve_pending_or_fail` (S4a-i)
   - `argus/main.py`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `argus/core/health.py`
   - `argus/core/config.py::IBKRConfig` (no changes this session)
   - `argus/ui/`, `frontend/`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template
(`templates/review-prompt.md` from the workflow metarepo).

The @reviewer will produce its review report (including a structured JSON
verdict fenced with ` ```json:structured-verdict `) and write it to:

```
docs/sprints/sprint-31.92-def-204-round-2/session-3a-review.md
```

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same
session, update the artifact trail per the implementation-prompt template
§"Post-Review Fix Documentation". Append "Post-Review Fixes" to the close-out
file and "Post-Review Resolution" to the review file. Update the verdict JSON
to `CONCERNS_RESOLVED`.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.
ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **`_LOCATE_REJECTED_FINGERPRINT` value verbatim from S1b JSON.** Verify the
   constant's value matches the spike's `fingerprint` field exactly, including
   case + whitespace. The substring match is case-insensitive at runtime per
   AC2.1, but the constant should be stored exactly as captured for forensic
   clarity. The close-out's "S1b Spike Output Consumed" section must cite the
   exact value.

2. **`time.monotonic()` semantics, NOT `time.time()`.** Per H-R3-1, the
   suppression dict keys are deadlines in monotonic time. Verify
   `_is_locate_suppressed` accepts `now: float` representing `time.monotonic()`
   AND the docstring explicitly cites monotonic-time semantics. Verify test 4
   uses `time.monotonic()` to construct both deadlines and the `now` argument.

3. **Helper placement parity with DEC-386.** Verify
   `_LOCATE_REJECTED_FINGERPRINT` + `_is_locate_rejection` are placed adjacent
   to (typically immediately after) `_OCA_ALREADY_FILLED_FINGERPRINT` +
   `_is_oca_already_filled_error` in `argus/execution/ibkr_broker.py`. Module
   scope, NOT inside a class.

4. **Position-keyed (NOT symbol-keyed) suppression.** Per Round-1 H-2 +
   regression invariant 14 specific edges, `_locate_suppressed_until` keys are
   `position.id` (ULID per DEC-026), NOT `position.symbol`. Verify the dict
   declaration's type annotation is `dict[ULID, float]` AND the helper accesses
   `position.id` (not `position.symbol`). Cross-position safety on the same
   symbol is the load-bearing property.

5. **Pydantic field validators correct + spike value baked.** Verify the 4 new
   `OrderManagerConfig` fields:
   - `locate_suppression_seconds`: `ge=300, le=86400`; default matches S1b
     spike's value (cross-check against the JSON).
   - `long_only_sell_ceiling_enabled`: `default=True` — fail-closed.
   - `long_only_sell_ceiling_alert_on_violation`: `default=True`.
   - `pending_sell_age_watchdog_enabled`: `Literal["auto", "enabled", "disabled"]`
     with `default="auto"` per Decision 4.

6. **Config validation test catches silent-drop class.** Verify the new test
   asserts YAML keys under `order_manager.*` are a subset of
   `OrderManagerConfig.model_fields.keys()`. Mental-revert: temporarily add a
   typo'd YAML key (e.g., `locate_supression_seconds` — note misspelling); the
   test should FAIL. The reviewer can request the close-out cite the
   mental-revert verification.

7. **No emit-site wiring (S3b's surface).** Verify the diff in
   `argus/execution/order_manager.py` does NOT touch any of `_flatten_position`,
   `_trail_flatten`, `_check_flatten_pending_timeouts`, or
   `_escalation_update_stop` exception handlers. The helpers exist but are NOT
   yet consumed by emit-site code; that's S3b.

8. **No production code touches `_check_sell_ceiling` or
   `_reserve_pending_or_fail`** (S4a-i's surface). Verify the diff does NOT
   add either method, even as a stub.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

Of particular relevance to Session 3a (✓-mandatory invariants per the
per-session verification matrix at line 619):

- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** ✓ — preserved
  byte-for-byte.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** ✓ — `_is_oca_already_filled_error`
  + `_OCA_ALREADY_FILLED_FINGERPRINT` UNCHANGED. The new helpers are siblings,
  not modifications.
- **Invariant 8 (DEF-158 3-branch side-check verbatim):** ✓ — preserved.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** ✓.
- **Invariant 10 (test count ≥ baseline):** ✓ — pytest delta is +6 per regression
  checklist line 156.
- **Invariant 11 (pre-existing flake count):** ✓.
- **Invariant 12 (frontend immutability; Vitest = 913):** ✓.
- **Invariant 14 (Path #2 fingerprint + position-keyed dict):** ✓ ESTABLISHES —
  Session 3a is the establishing session for this invariant per the matrix.
  Specifically: `test_is_locate_rejection_matches_canonical_string` (sub-test 1)
  and `test_is_locate_suppressed_position_keyed_returns_true_within_window`
  (sub-test 2) of regression invariant 14. Sub-tests 3+ land at S3b.
- **Invariant 26 (NEW per Decision 4) — AC2.7 watchdog Pydantic validation:**
  ✓ — the `pending_sell_age_watchdog_enabled` field is added at S3a; Pydantic
  surface tests for the field and auto-mode flip semantics land at S4a-i.
  S3a's role is FIELD ADDITION; the per-session matrix (line 646) marks S3a's
  invariant 26 cell as ✓.

## Sprint-Level Escalation Criteria (for @reviewer)

The full Sprint-Level Escalation Criteria is in
`docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`.

Of particular relevance to Session 3a:

- **A2** — Spike S1b returns `status: INCONCLUSIVE` (e.g., locate-rejection
  string varies non-deterministically OR fewer than 5 hard-to-borrow microcap
  symbols actually got held during paper hours). Halt; Tier 3 reviews
  alternatives. Per Pre-Flight #6, this should be pre-empted before the
  session begins; defensive trigger.
- **A4** — any session's diff modifies a DEC-385/386/388 surface listed in SbC
  "Do NOT modify" beyond explicit byte-for-byte preservation OR explicit
  additive points. Halt; revert; escalate.
- **B1** — pre-existing flake count increases. Halt; file DEF.
- **B3** — pytest baseline ends below 5,269. Halt.
- **B4** — CI fails on session's final commit and is NOT a documented
  pre-existing flake. Halt per RULE-050.
- **B5** — structural anchor mismatch during pre-flight grep-verify. Halt
  mid-pre-flight; re-anchor.
- **B6** — do-not-modify list file in session's `git diff`. Halt; revert.
- **B9** — Path #2 spike S1b's hold-pending-borrow release window p99
  measurement exceeds the spec-bounded ceiling of 86400s (24hr). Halt at S3a
  impl. Per Pre-Flight #6, this should be pre-empted; defensive trigger. If
  fired: operator + Tier 2 disposition (raise validator ceiling via DEC
  amendment OR accept that broker-verification at suppression-timeout is the
  dominant code path within 24hr per H6 RULES-OUT path).
- **A6** — Tier 2 verdict CONCERNS or ESCALATE. Operator + Tier 2 disposition.
- **C1** — implementer notices a bug or improvement opportunity outside scope.
  Document under "Deferred Items" (RULE-007).
- **C5** — implementer is uncertain whether a change crosses the do-not-modify
  boundary. Pause; consult SbC.
- **C8** — S1b spike output JSON schema does not exactly match the schema
  specified in the spec. Continue. Document the actual schema in the close-out.
  The downstream impl prompts at S3b consume the JSON; minor schema deviations
  are acceptable as long as the gating fields
  (`recommended_locate_suppression_seconds`, exact fingerprint string,
  `case_a_observed`, etc.) are present and meaningful.
- **C10** — operator-curated hard-to-borrow microcap list at S1b includes < 5
  symbols, OR none triggered locate-rejection. Continue with documented caveat
  per H6 RULES-OUT path; default falls to 18000s.

### Verification Grep Precision

When kickoffs include verification grep commands, prefer the more precise patterns:

- **Section counting:** use `^## [1-9]\.` rather than `^## [0-9]`.
- **Human-authored content with TitleCase:** use `grep -i`.
- **Token-presence checks across rejection-framed content:** scan only validation
  logic, not docstrings/rationale blocks. A rejection rationale that names the
  token is not a reintroduction.

---

*End Sprint 31.92 Session 3a implementation prompt.*
