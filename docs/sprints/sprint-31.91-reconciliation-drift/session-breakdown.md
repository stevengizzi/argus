# Sprint 31.91: Session Breakdown (REVISED 3rd pass — 18 sessions)

> **Phase C artifact 3/7 (revised 3rd pass).** Per-session scope,
> dependencies, compaction risk scoring, pre-flight reads, test list,
> definition of done, and Tier 2 review focus. Companion to `sprint-spec.md`,
> `spec-by-contradiction.md`, and `PHASE-D-OPEN-ITEMS.md`.

## Session Overview

**18 sessions, sequential execution. Two Tier 3 architectural reviews
(after 1c and after 5b).** All sessions either touch
`argus/execution/order_manager.py` or its dependents (Sessions 0–4 +
5a.1 + 5a.2 + 5b backend), or share frontend infrastructure (Sessions
5c–5e). No parallelization.

| # | Session | Reviewer | Compaction Score | Notes |
|---|---------|----------|-----------------:|-------|
| 0 | `cancel_all_orders(symbol, await_propagation)` API extension | Backend safety | **7** | AlpacaBroker DeprecationWarning per L1 |
| 1a | Bracket OCA grouping + Error 201 defensive | Backend safety | **9.5** | Per-bracket ULID derivation |
| 1b | Standalone-SELL OCA threading + Error 201 graceful | Backend safety | **9** | 4 paths incl. `_flatten_position` |
| 1c | Broker-only paths safety + reconstruct docstring | Backend safety | **9** | `await_propagation=True` sites |
| **— Tier 3 architectural review #1 (after 1c) — OCA-architecture seal — Scope: Sessions 0 + 1a + 1b + 1c (per third-pass LOW #17) —** | | | | |
| 2a | Reconciliation contract refactor | Backend safety | **10.5** | Line refs `:1505-1535` |
| 2b.1 | Broker-orphan + cycle infra | Backend safety | **8** | M2 lifecycle |
| 2b.2 | Four count-filter sites + one alert-alignment site | Backend safety | **10** | Two patterns per third-pass HIGH #2 |
| 2c.1 | Gate state + handler + SQLite persistence | Backend safety | **9** | M5 |
| 2c.2 | Clear-threshold + auto-clear (default 5) | Backend safety | **6** | M4 |
| 2d | Override API + audit-log + always-both-alerts + configurable threshold | Backend safety | **9** | M3 + L3 + LOW #15 |
| 3 | DEF-158 retry side-check + severity fix | Backend safety | **6** | Unchanged |
| 4 | Mass-balance categorized + IMSR replay | Backend safety | **7** | H2 + H4 |
| **5a.1** | **HealthMonitor consumer + REST endpoints + acknowledgment (atomic + idempotent)** | Backend safety | **8** | Per third-pass HIGH #1 split; MEDIUM #10 |
| **5a.2** | **WebSocket fan-out + SQLite persistence + auto-resolution policy table + retention/migration** | Backend safety | **9** | Per third-pass HIGH #1 split; MEDIUM #9 |
| 5b | IBKR emitters + E2E + behavioral Alpaca check | Backend safety | **9** | MEDIUM #13 behavioral assertion |
| **— Tier 3 architectural review #2 (after 5b) — alert observability backend seal — Scope: Sessions 5a.1 + 5a.2 + 5b —** | | | | |
| 5c | `useAlerts` hook + Dashboard banner | **Frontend** | **9** | TanStack Query + WebSocket |
| 5d | Toast + acknowledgment UI flow | **Frontend** | **8** | Click-to-acknowledge |
| 5e | Observatory panel + cross-page integration | **Frontend** | **8** | Layout-level mounting |

**Tier 3 review #1** fires after Session 1c (OCA-architecture-complete:
**API extension + bracket + standalone + broker-only paths + restart
safety**) before the data-model change in Session 2a ships. **Scope
includes Session 0** per third-pass LOW #17 — the `cancel_all_orders`
API contract is part of the OCA architecture, and reviewing without it
would be incomplete.

**Tier 3 review #2** fires after Session 5b (alert-observability-backend
complete: HealthMonitor consumer + REST + acknowledgment in 5a.1,
WebSocket + persistence + auto-resolution in 5a.2, all backend emitters
in 5b) before the frontend builds on this API contract in Sessions
5c–5e.

**Phase C-1 third-pass adversarial review** has fired. Verdict:
Conditional CLEAR with 5 HIGH + 14 MEDIUM/LOW findings. HIGH findings
addressed in this revision. MEDIUM/LOW findings either applied at
spec-level (D9a/D9b atomic+idempotent, retention/migration; D10
behavioral Alpaca check; LOW #15 configurable threshold; LOW #17 Tier
3 #1 scope; configurable aggregate alert threshold) or captured in
`PHASE-D-OPEN-ITEMS.md` for in-flight Phase D inclusion.

---

## Session 0 — `cancel_all_orders(symbol, await_propagation)` API Extension

### Scope (1 sentence)

Extend `Broker.cancel_all_orders()` ABC with optional `symbol` and
`await_propagation` parameters; update `IBKRBroker`, `SimulatedBroker`
implementations; AlpacaBroker raises `DeprecationWarning` (L1).

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `CancelPropagationTimeout` exception class (in `argus/execution/broker.py`) |
| **Modifies** | `argus/execution/broker.py` (ABC); `argus/execution/ibkr_broker.py` (impl); `argus/execution/alpaca_broker.py` (DeprecationWarning); `argus/execution/simulated_broker.py` (impl); test files (~6 new tests) |
| **Integrates** | N/A — foundational |

### Pre-Flight Reads (5 files)

1. `argus/execution/broker.py:143` — current ABC signature.
2. `argus/execution/ibkr_broker.py:1086` — current impl.
3. `argus/execution/alpaca_broker.py` — current impl (read for DeprecationWarning placement).
4. `argus/execution/simulated_broker.py:629` — current impl.
5. `sprint-spec.md` D1 acceptance criteria.

### Tests (~6 new pytest)

1. `test_cancel_all_orders_no_args_preserves_dec364`
2. `test_cancel_all_orders_symbol_filter`
3. `test_cancel_all_orders_await_propagation_polls_until_empty`
4. `test_cancel_all_orders_await_propagation_timeout_raises`
5. `test_alpaca_broker_cancel_all_orders_raises_deprecation_warning`
6. `test_ibkr_broker_cancel_all_orders_symbol_filter_uses_open_orders`

### Definition of Done

- [ ] Signature accepts `symbol: str | None = None, *, await_propagation: bool = False`
- [ ] All 3 implementations updated; AlpacaBroker raises `DeprecationWarning`
- [ ] DEC-364 contract preserved
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- DEC-364 contract preservation
- `await_propagation` polling timeout edge cases
- AlpacaBroker DeprecationWarning style (per L1 — minimal, not throwaway functional code)

---

## Session 1a — Bracket OCA Grouping + Error 201 Defensive

### Scope (1 sentence)

Set `ocaGroup = f"oca_{parent_ulid}"` and `ocaType=1` on bracket children;
add `oca_group_id` field to `ManagedPosition`; defensive Error
201/OCA-filled handling on T1/T2 placement.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/ibkr_broker.py` (bracket children placement ~lines 731-782); `argus/execution/order_manager.py` (`ManagedPosition` dataclass); `argus/execution/simulated_broker.py` (mock OCA support); `argus/core/config.py` (`IBKRConfig.bracket_oca_type: int = Field(default=1, ge=0, le=1)`); YAMLs; test files (~8 new tests) |
| **Integrates** | N/A |

### Pre-Flight Reads (5 files)

1. `argus/execution/ibkr_broker.py` — `place_bracket_order` method.
2. `argus/execution/order_manager.py:74` — `ManagedPosition`.
3. `argus/execution/simulated_broker.py` — `place_order` method.
4. `argus/core/config.py:639` — `IBKRConfig`.
5. `sprint-spec.md` D2 acceptance criteria.

### Tests (~8 new pytest)

1. `test_bracket_children_carry_oca_group`
2. `test_bracket_oca_group_id_persists_to_managed_position`
3. `test_managed_position_oca_group_id_default_none`
4. `test_re_entry_after_close_gets_new_oca_group`
5. `test_bracket_oca_type_config_accepts_only_0_or_1`
6. `test_dec117_rollback_with_oca_type_1_cancels_partial_children`
7. `test_oca_group_deterministic_from_parent_ulid` (per M1)
8. **NEW**: `test_t1_t2_placement_error_201_oca_filled_handled_gracefully` — distinguishes from generic Error 201; logs INFO; rollback fires; no orphaned OCA-A members

### Definition of Done

- [ ] Bracket children carry `ocaGroup == oca_group_id` and `ocaType == 1`
- [ ] `oca_group_id = f"oca_{parent_ulid}"` deterministic
- [ ] `ManagedPosition.oca_group_id: str | None = None` added
- [ ] `bracket_oca_type` accepts 0 or 1 only
- [ ] Error 201/OCA-filled handled defensively (INFO not ERROR)
- [ ] DEC-117 rollback test passes with ocaType=1
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- ocaType=1 vs `parentId` linkage compatibility
- OCA group ID derivation determinism
- Error 201 distinguishing logic (OCA-filled vs generic)
- Re-entry produces new OCA groups

---

## Session 1b — Standalone-SELL OCA Threading + Error 201 Graceful

### Scope (1 sentence)

Thread `oca_group_id` into `_trail_flatten`, `_escalation_update_stop`,
`_resubmit_stop_with_retry`, AND `_flatten_position`; graceful Error
201/OCA-filled handling on these paths.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` — 4 functions; test files (~8 new tests) |
| **Integrates** | Session 1a's `oca_group_id` field |

### Pre-Flight Reads (4 files)

1. `argus/execution/order_manager.py:2451` — `_trail_flatten`.
2. `argus/execution/order_manager.py:2552` — `_escalation_update_stop`.
3. `argus/execution/order_manager.py:778` — `_resubmit_stop_with_retry`.
4. `argus/execution/order_manager.py:2620` — `_flatten_position`.

### Tests (~8 new pytest)

1. `test_trail_flatten_threads_oca_group`
2. `test_escalation_update_stop_threads_oca_group`
3. `test_resubmit_stop_with_retry_threads_oca_group`
4. `test_flatten_position_threads_oca_group`
5. `test_oca_threading_falls_through_when_oca_group_id_none`
6. `test_race_window_two_paths_same_oca_group`
7. `test_no_sell_without_oca_when_managed_position_has_oca` (grep guard)
8. **NEW**: `test_standalone_sell_error_201_oca_filled_logged_info_not_error` — graceful handling; ManagedPosition marked redundant_exit; DEF-158 retry NOT triggered

### Definition of Done

- [ ] All 4 SELL paths thread `oca_group_id`
- [ ] Error 201/OCA-filled handled gracefully
- [ ] Generic Error 201 still treated as ERROR
- [ ] Grep regression guard in place
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- All 4 paths thread correctly
- Error 201 distinguishing logic
- DEF-199 A1 fix still detects phantom shorts (anti-regression)

---

## Session 1c — Broker-Only Paths Safety + Reconstruct Docstring

### Scope (1 sentence)

Integrate `cancel_all_orders(symbol, await_propagation=True)` into
`_flatten_unknown_position`, `_drain_startup_flatten_queue`,
`reconstruct_from_broker()`; add contract docstring to
`reconstruct_from_broker()` per B3.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` — 3 functions; test files (~6 new tests + ~1 mock update) |
| **Integrates** | Session 0's API extension |

### Pre-Flight Reads (5 files)

1. `argus/execution/order_manager.py:1920` — `_flatten_unknown_position`.
2. `argus/execution/order_manager.py:2021` — `_drain_startup_flatten_queue`.
3. `argus/execution/order_manager.py:1813` — `reconstruct_from_broker`.
4. `argus/execution/order_manager.py:1705-1755` — EOD Pass 2 loop.
5. `argus/execution/broker.py` — confirm Session 0 API.

### Tests (~6 new pytest)

1. `test_flatten_unknown_position_calls_cancel_all_orders_first`
2. `test_drain_startup_flatten_queue_calls_cancel_all_orders_first`
3. `test_reconstruct_from_broker_calls_cancel_all_orders_per_symbol`
4. `test_eod_pass2_stale_oca_cleared_before_sell`
5. `test_reconstruct_orphaned_oca_cleared`
6. `test_cancel_propagation_timeout_aborts_sell_and_emits_alert`

### Definition of Done

- [ ] All 3 functions invoke `cancel_all_orders(symbol, await_propagation=True)` before SELL
- [ ] Timeout (`CancelPropagationTimeout`) aborts SELL + emits alert
- [ ] `reconstruct_from_broker()` docstring documents startup-only contract + future-caller requirements per B3
- [ ] DEC-369 broker-confirmed immunity preserved
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- `cancel_all_orders` is BEFORE SELL placement
- `await_propagation=True` correctly blocks until empty
- Timeout abort path emits alert (not just logs)
- Reconstruct docstring is precise about future-caller requirements

---

## **🔻 TIER 3 ARCHITECTURAL REVIEW #1 FIRES HERE 🔻**

**Trigger:** Session 1c lands cleanly on `main` + Tier 2 CLEAR + green CI.

**Scope (per third-pass LOW #17):** Combined diff of **Sessions 0 +
1a + 1b + 1c** on main. Reviews the OCA-architecture-complete state
(API contract from Session 0 + bracket-side OCA + standalone-SELL
threading + broker-only safety + restart safety) before the data-model
change in Session 2a ships. **Including Session 0 in scope** is
material — the `cancel_all_orders(symbol, await_propagation)` API
contract is part of the OCA architecture, and Session 1c consumes the
`await_propagation=True` semantics to make the broker-only paths safe.

**Verdict:** CLEAR → proceed to 2a. CONCERNS → revisions before 2a.
ESCALATE → halt sprint, operator re-planning.

See `escalation-criteria.md` §A1 for full Tier 3 scope.

---

## Session 2a — Reconciliation Contract Refactor

### Scope (1 sentence)

Create `ReconciliationPosition` frozen dataclass; change
`reconcile_positions` signature to `dict[str, ReconciliationPosition]`;
update `argus/main.py:1505-1535` call site to consume `Position.side`.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `ReconciliationPosition` frozen dataclass (in `argus/execution/order_manager.py` near line 124) |
| **Modifies** | `argus/execution/order_manager.py`; `argus/main.py:1505-1535`; test files (~5 new + ~3 mock updates) |
| **Integrates** | Existing `Position.side` field |

### Pre-Flight Reads (6 files)

1. `argus/execution/order_manager.py:124` — area for new dataclass.
2. `argus/execution/order_manager.py` — current `reconcile_positions`.
3. `argus/main.py:1505-1535` — current call site.
4. `argus/models/trading.py:153-173` — `Position`.
5. `argus/execution/ibkr_broker.py:935-946` — `get_positions()`.
6. Existing reconciliation tests in `tests/`.

### Tests (~5 new + ~3 mock updates)

1. `test_reconciliation_position_dataclass_frozen_round_trip`
2. `test_reconcile_positions_signature_typed_dict`
3. `test_main_call_site_builds_typed_dict_from_broker_positions`
4. `test_argus_orphan_branch_unchanged_with_typed_contract`
5. `test_reconcile_positions_with_pos_missing_side_attribute_fails_closed`

### Definition of Done

- [ ] `ReconciliationPosition` dataclass with `frozen=True`
- [ ] `reconcile_positions` signature accepts typed dict
- [ ] `main.py` call site updated
- [ ] Existing ARGUS-orphan branch behavior preserved
- [ ] DEC-369 immunity preserved
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- Information end-to-end (`Position.side` → typed contract → orphan loop)
- Frozen dataclass immutability
- Defensive fail-closed when `side=None`

---

## Session 2b.1 — Broker-Orphan SHORT Branch + `phantom_short` Alert + Cycle Infrastructure

### Scope (1 sentence)

Add broker-orphan branch to orphan loop; emit `phantom_short` and
`stranded_broker_long` alerts; build `_broker_orphan_long_cycles`
infrastructure with M2 lifecycle (cleanup, exponential-backoff re-alert,
session reset).

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` (orphan loop + new state field + lifecycle); `argus/core/config.py` (1 new flag); YAMLs; test files (~6 new tests) |
| **Integrates** | Session 2a's typed contract; existing `SystemAlertEvent` |

### Pre-Flight Reads (5 files)

1. `argus/execution/order_manager.py:3038-3039` — orphan loop check.
2. `argus/core/events.py:405` — `SystemAlertEvent`.
3. `argus/core/config.py:229` — `ReconciliationConfig`.
4. Existing `_broker_confirmed` patterns (DEC-369/370).
5. `sprint-spec.md` D5 (2b.1 portion).

### Tests (~6 new pytest)

1. `test_broker_orphan_short_emits_phantom_short_alert`
2. `test_broker_orphan_short_alert_payload_shape`
3. `test_broker_orphan_alert_config_flag_disables`
4. `test_broker_orphan_long_cycle_1_warning_only`
5. `test_broker_orphan_long_cycle_3_emits_stranded_alert`
6. **M2 lifecycle**: `test_broker_orphan_long_cycles_cleanup_on_zero_exponential_backoff_session_reset`

### Definition of Done

- [ ] Broker-orphan SHORT branch emits `phantom_short` alert
- [ ] LONG cycle 1–2 warning; cycle 3+ `stranded_broker_long`
- [ ] M2 lifecycle: cleanup on broker-zero (5 cycles), exp-backoff (3→6→12→24, capped hourly), session reset
- [ ] `broker_orphan_alert_enabled` config flag
- [ ] DEC-369 + DEC-370 preserved
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- Alert payload shape correctness
- Cycle counter resets on broker-zero observation
- Exponential backoff calculation
- Session reset clears stale state

---

## Session 2b.2 — Four Count-Filter Sites + One Alert-Alignment Site (B5 Pattern, Two-Pattern Reframe per HIGH #2)

### Scope (1 sentence)

Apply two distinct patterns: **(A) side-aware count filter** at
margin-circuit reset, Risk Manager max-concurrent #1 + #2, and Health
integrity check (4 sites, all long-only filtering); **(B) alert
taxonomy alignment** at EOD Pass 2 short detection (no filter; existing
detection gets additional `phantom_short` alert emission for taxonomy
consistency).

### Reframe rationale (per third-pass HIGH #2)

The earlier framing — "three sites with the same side-aware-filter
pattern" — was wrong on count and on uniformity. Counting correctly:
4 filter sites + 1 alert-alignment site. Pattern-wise, the 4 filter
sites apply long-only filtering to broker-state reads driving safety
decisions; the alert-alignment site adds a `SystemAlertEvent` emission
to existing `logger.error` detection that already correctly identifies
the short. These are different changes with different test surfaces; a
Tier 2 reviewer reading "same pattern uniformly applied" might verify
filters were added correctly at all sites and miss that EOD Pass 2 has
a different obligation.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` (margin circuit reset ~1492 — Pattern A; EOD Pass 2 short detection ~1734 — Pattern B); `argus/core/risk_manager.py` (~335 + ~771 — Pattern A); `argus/core/health.py` (~443-450 — Pattern A); test files (~9 new tests grouped by pattern) |
| **Integrates** | Session 2b.1's `phantom_short` alert taxonomy |

### Pre-Flight Reads (6 files)

1. `argus/execution/order_manager.py:1492` — margin circuit reset (Pattern A).
2. `argus/execution/order_manager.py:~1734` — EOD Pass 2 short detection (Pattern B).
3. `argus/core/risk_manager.py:335` — max-concurrent-positions site #1 (Pattern A).
4. `argus/core/risk_manager.py:771` — max-concurrent-positions site #2 (Pattern A).
5. `argus/core/health.py:443-450` — daily integrity check (Pattern A — hybrid: filter + alert routing).
6. `PHASE-A-REVISIT-FINDINGS.md` §A3 — B5 audit-row analysis.

### Tests (~9 new pytest, grouped by pattern)

**Pattern A — count-filter tests:**
1. `test_margin_circuit_reset_uses_longs_only`
2. `test_margin_circuit_reset_logs_breakdown`
3. `test_risk_manager_max_concurrent_positions_uses_longs_only_335`
4. `test_risk_manager_max_concurrent_positions_uses_longs_only_771`
5. `test_risk_manager_phantom_shorts_dont_consume_position_cap`
6. `test_health_integrity_check_long_orphan_no_stop_emits_existing_alert`
7. `test_health_integrity_check_short_routes_to_phantom_short_alert`
8. `test_health_integrity_check_log_breakdown_longs_protected_shorts_phantom`

**Pattern B — alert-alignment test:**
9. `test_eod_pass2_short_detection_emits_phantom_short_alert_alongside_existing_logger_error`

### Definition of Done

- [ ] **Pattern A:** All 4 broker-state read sites use long-only
      filter; log breakdown lines on each site; phantom shorts don't
      inflate counts that drive safety decisions.
- [ ] **Pattern B:** EOD Pass 2 short detection emits `phantom_short`
      alert alongside existing `logger.error`; alert taxonomy consistent
      with Sessions 2b.1 (reconciliation orphan branch) and 5a.2
      (auto-resolution policy table).
- [ ] Health check side-aware (Pattern A hybrid): longs without stops
      → existing alert; shorts → `phantom_short` alert via 2b.1's
      taxonomy.
- [ ] CI green; Tier 2 CLEAR.

### Tier 2 Review Focus

- **Pattern recognition:** Reviewer confirms the two patterns are
  applied at the correct sites; no Pattern A site missing the filter;
  no Pattern B site silently changed to filter-only.
- **B5 regression test** (phantom shorts don't lock out legitimate
  longs).
- **Alert taxonomy consistency** between Pattern B (EOD Pass 2),
  Pattern A hybrid (Health integrity check), and Session 2b.1
  (reconciliation orphan branch). All three should produce alerts
  consumed by Session 5a.2's auto-resolution policy table the same
  way.
- **Health + broker-orphan double-fire** (per third-pass MEDIUM #8 —
  carried forward to Phase D prompt for operator decision): when a
  broker-orphan long has no stop, both 2b.1's `stranded_broker_long`
  alert and 2b.2's existing "Integrity Check FAILED" alert may fire
  for the same condition. Spec is silent on dedup; reviewer should
  flag for operator dedup-or-document decision.

---

## Session 2c.1 — Per-Symbol Gate State + Handler + SQLite Persistence

### Scope (1 sentence)

Add `_phantom_short_gated_symbols: set[str]` state; gate
`OrderApprovedEvent` handler; SQLite persistence to `data/operations.db`
`phantom_short_gated_symbols` table; rehydrate on startup BEFORE event
processing.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `phantom_short_gated_symbols` SQLite table (in `data/operations.db` schema migration) |
| **Modifies** | `argus/execution/order_manager.py` (state + handler + persistence); `argus/main.py` (rehydration order on startup); `argus/core/config.py` (1 new flag); YAMLs; test files (~6 new tests) |
| **Integrates** | Session 2b.1's broker-orphan branch (gate engages on detection) |

### Pre-Flight Reads (5 files)

1. `argus/execution/order_manager.py` — `OrderApprovedEvent` handler (search for `on_approved`).
2. `argus/main.py` — startup sequence (where reconciliation hooks attach).
3. `data/operations.db` schema or comparable SQLite manager.
4. `argus/core/events.py` — `OrderApprovedEvent`.
5. `sprint-spec.md` D5 (2c.1 portion).

### Tests (~6 new pytest)

1. `test_phantom_short_gate_engages_on_broker_orphan_short`
2. `test_gate_blocks_order_approved_for_gated_symbol`
3. `test_gate_does_not_block_other_symbols`
4. `test_phantom_short_gated_symbols_persist_to_sqlite`
5. **M5**: `test_gate_state_rehydrated_on_restart_before_event_processing`
6. `test_gate_state_survives_argus_restart_blocks_entries`

### Definition of Done

- [ ] `_phantom_short_gated_symbols` state field
- [ ] Handler rejects gated symbols
- [ ] Per-symbol granularity verified
- [ ] SQLite persistence; rehydrates on startup BEFORE event processing (M5)
- [ ] `broker_orphan_entry_gate_enabled` config flag
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- Rehydration ordering on startup (BEFORE event processing, not after)
- SQLite transactions atomic
- Per-symbol granularity holds

---

## Session 2c.2 — Clear-Threshold + Auto-Clear (Default 5)

### Scope (1 sentence)

Add `broker_orphan_consecutive_clear_threshold` config field with
**default 5** (was 3, per M4 cost-of-error asymmetry); implement
auto-clear logic.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` (clear-counter logic); `argus/core/config.py` (1 new field); YAMLs; test files (~4 new tests) |
| **Integrates** | Session 2c.1's gate state |

### Pre-Flight Reads (4 files)

1. `argus/execution/order_manager.py` — Session 2c.1 gate state.
2. `argus/core/config.py:229` — `ReconciliationConfig`.
3. DEC-370 reference (existing `_reconciliation_miss_count` pattern).
4. `sprint-spec.md` D5 (2c.2 portion).

### Tests (~4 new pytest)

1. `test_gate_clears_after_5_consecutive_zero_cycles`
2. `test_gate_persists_through_transient_broker_zero_resets_counter`
3. `test_clear_threshold_config_loadable_default_5`
4. `test_clear_threshold_configurable_override`

### Definition of Done

- [ ] 5-cycle clear-threshold (default; configurable)
- [ ] Counter resets on re-detection (preventing premature clear)
- [ ] Config field loads with default 5
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- Default value matches M4 disposition (5 not 3)
- Cost-of-error asymmetry rationale documented in code comment
- Counter-reset edge cases

---

## Session 2d — Operator Override API + Audit-Log + Always-Both-Alerts

### Scope (1 sentence)

`POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint with
audit-log per M3 schema; CRITICAL startup log line; always-fire-both-alerts
per L3 (no suppression); `docs/live-operations.md` runbook section.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | New API route handler; `phantom_short_override_audit` SQLite table |
| **Modifies** | API router registration; `argus/main.py` (startup log line); `docs/live-operations.md`; test files (~6 new tests) |
| **Integrates** | Session 2c.1's `_phantom_short_gated_symbols` state |

### Pre-Flight Reads (5 files)

1. `argus/api/` — existing reconciliation routes.
2. `argus/main.py` — startup sequence.
3. Session 2c.1's gate state accessor.
4. `docs/live-operations.md` — current runbook structure.
5. `sprint-spec.md` D5 (2d portion).

### Tests (~6 new pytest)

1. `test_phantom_short_gate_clear_endpoint_removes_symbol`
2. `test_phantom_short_gate_clear_audit_log_full_schema_persists` (M3)
3. `test_phantom_short_gate_clear_unknown_symbol_404`
4. `test_aggregate_phantom_short_startup_alert_at_10_symbols_AND_individual_alerts_fire` (L3)
5. `test_below_10_symbols_individual_alerts_only_no_aggregate`
6. `test_startup_log_line_lists_gated_symbols`

### Definition of Done

- [ ] API endpoint accessible; accepts JSON body; returns audit response
- [ ] Audit-log entry persists across restarts (M3 schema)
- [ ] Aggregate alert at ≥10 + always-fire-both-alerts (L3)
- [ ] Startup CRITICAL log line
- [ ] `docs/live-operations.md` runbook section added
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- API endpoint authentication consistency
- Audit-log schema captures full forensic detail (M3)
- Aggregation + individual alerts both fire (L3 — no suppression)

---

## Session 3 — DEF-158 Retry Side-Check + Severity Fix

### Scope (1 sentence)

Apply IMPROMPTU-04's 3-branch pattern to
`_check_flatten_pending_timeouts` at line 2384;
`phantom_short_retry_blocked` severity critical.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/order_manager.py` — `_check_flatten_pending_timeouts` (~lines 2299-2406); test files (~5 new + ~2 mock updates) |
| **Integrates** | Side-reading idiom; mirror of IMPROMPTU-04 EOD A1 |

### Pre-Flight Reads (4 files)

1. `argus/execution/order_manager.py:2299-2406`.
2. `argus/execution/order_manager.py:1670-1750` — IMPROMPTU-04 EOD A1 (do-not-modify).
3. `sprint-spec.md` D6 acceptance.
4. `argus/core/events.py:405` — `SystemAlertEvent`.

### Tests (~5 new + ~2 mock updates)

1. `test_def158_retry_long_position_flattens_normally`
2. `test_def158_retry_short_position_blocks_and_alerts_critical`
3. `test_def158_retry_unknown_side_blocks_and_logs_error`
4. `test_def158_retry_qty_mismatch_long_uses_broker_qty`
5. `test_phantom_short_retry_blocked_alert_severity_is_critical`

### Definition of Done

- [ ] 3-branch logic; BUY preserves; SELL emits critical alert; unknown errors out
- [ ] All 3 branches clear flatten-pending
- [ ] DEF-199 A1 + DEF-158 normal case anti-regression
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- IMPROMPTU-04 pattern mirror (ERROR log + skip)
- Alert severity matches 2b.1's `phantom_short`
- Flatten-pending cleared in all branches

---

## Session 4 — Mass-Balance Categorized + IMSR Replay

### Scope (1 sentence)

`scripts/validate_session_oca_mass_balance.py` produces categorized
variance report (H2); IMSR replay using
`logs/argus_20260424.jsonl` directly (H4); update
`pre-live-transition-checklist.md` with revised live-enable gate.

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `scripts/validate_session_oca_mass_balance.py`; `tests/integration/test_imsr_replay.py` |
| **Modifies** | `docs/pre-live-transition-checklist.md`; `docs/protocols/market-session-debrief.md` (Phase 7 slippage watch) |
| **Integrates** | All prior sessions are validation targets |

### Pre-Flight Reads (4 files)

1. `logs/argus_20260424.jsonl` (operator-supplied; verify available).
2. `argus/backtest/engine.py` — BacktestEngine entry point.
3. `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` — IMSR forensic timeline (reference only).
4. `docs/pre-live-transition-checklist.md` — current structure.

### Tests (~5 new pytest)

1. `test_mass_balance_script_clean_session_zero_unaccounted_leak_exits_0` (H2)
2. `test_mass_balance_script_categorizes_expected_partial_fill_no_flag` (H2)
3. `test_mass_balance_script_categorizes_eventual_consistency_lag_no_flag` (H2)
4. `test_mass_balance_script_unaccounted_leak_exits_1` (H2)
5. `test_imsr_replay_with_post_fix_code_position_zero_at_eod` (H4 — uses real Apr 24 .jsonl)

### Definition of Done

- [ ] Mass-balance script produces categorized variance report
- [ ] Exit code 0 if zero `unaccounted_leak`; non-zero otherwise
- [ ] IMSR replay uses real Apr 24 log; asserts EOD position = 0
- [ ] `pre-live-transition-checklist.md` lists 3 live-enable gate criteria (NO disconnect-reconnect — moved to 31.93)
- [ ] `market-session-debrief.md` Phase 7 has slippage watch
- [ ] DEF-208 + DEF-209 filed
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- H2 categorization definitions precise
- IMSR replay test runs against real log (not synthetic)
- Live-enable gate criteria unambiguous and verifiable
- Phase 7 slippage watch item clear

---

## Session 5a.1 — HealthMonitor Consumer + REST Endpoints + Acknowledgment (Atomic + Idempotent)

### Scope (1 sentence)

`HealthMonitor` subscribes to `SystemAlertEvent` and maintains
in-memory active-alert state; REST endpoints
(`GET /api/v1/alerts/active`, `/history`,
`POST /alerts/{id}/acknowledge`); acknowledgment flow with atomic
state-change-and-audit-log + idempotency (200/404/409 per third-pass
MEDIUM #10).

### Reviewer

**Backend safety.**

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | API alerts router (NEW file in `argus/api/routes/`); `alert_acknowledgment_audit` SQLite table; `AlertsConfig` Pydantic model (NEW) |
| **Modifies** | `argus/core/health.py` (HealthMonitor consumer expansion — in-memory state); `argus/main.py` (HealthMonitor consumer init); `argus/core/config.py` (`AlertsConfig`); YAMLs; test files (~7 new tests) |
| **Integrates** | All `SystemAlertEvent` emitters (Databento pre-existing, IBKR-pending Session 5b, Sessions 2b/3 phantom_short) — **subscription only**; the persistence + auto-resolution work lands in 5a.2 |

### Pre-Flight Reads (5 files)

1. `argus/core/health.py` — current `HealthMonitor`.
2. `argus/core/events.py:405` — `SystemAlertEvent`.
3. `argus/api/routes/` — existing route patterns (for new alerts router).
4. `argus/main.py` — HealthMonitor instantiation site.
5. `sprint-spec.md` D9a acceptance criteria.

### Tests (~7 new pytest + ~1 mock update)

1. `test_health_monitor_subscribes_to_system_alert_event`
2. `test_health_monitor_maintains_active_alert_state_in_memory`
3. `test_get_alerts_active_returns_current_state`
4. `test_get_alerts_history_returns_within_window`
5. `test_post_alert_acknowledge_atomic_transition_writes_audit` — both state change AND audit-log write succeed atomically; rollback on either failure
6. `test_post_alert_acknowledge_idempotent_200_for_already_acknowledged` — second acknowledge returns 200 with original acknowledger info; still writes duplicate-ack audit row
7. `test_post_alert_acknowledge_404_for_unknown_id` — no audit-log row written
8. `test_post_alert_acknowledge_409_for_auto_resolved_writes_late_ack_audit` — race resolution: alert auto-resolved before acknowledge fires; still writes late-ack audit row

### Definition of Done

- [ ] HealthMonitor consumes `SystemAlertEvent` and maintains
      in-memory state.
- [ ] REST `GET /alerts/active` + `/history` functional.
- [ ] REST `POST /alerts/{id}/acknowledge` writes audit-log entry.
- [ ] **Atomic transition** (per MEDIUM #10): state change AND audit-log
      write in single SQLite transaction; rollback on failure.
- [ ] **Idempotency** (per MEDIUM #10): 200 / 404 / 409 paths all
      tested; 200 and 409 paths still write audit-log row.
- [ ] **Race resolution**: first writer wins; second sees 409.
- [ ] `AlertsConfig` `acknowledgment_required_severities: ["critical"]`
      default loadable.
- [ ] CI green; Tier 2 CLEAR.

### Tier 2 Review Focus

- **Atomic transition correctness**: failure midway through the SQLite
  transaction must not leave alert state and audit-log out of sync.
- **Idempotency edge cases**: rapid-fire double-clicks; operator
  acknowledging from two browser tabs simultaneously.
- **HealthMonitor consumer doesn't lose alerts under load** (Event Bus
  drop-counter check from existing patterns).
- **No-operator case** doesn't deadlock the system: acknowledgment
  required for `phantom_short_retry_blocked` and
  `cancel_propagation_timeout` (per 5a.2 policy table) means banner
  may stay visible indefinitely if operator absent. Acceptable
  behavior; verify it matches the policy table.

---

## Session 5a.2 — WebSocket Fan-Out + SQLite Persistence + Auto-Resolution Policy Table + Retention/Migration

### Scope (1 sentence)

`WS /ws/v1/alerts` real-time fan-out; `alert_state` SQLite-backed for
restart recovery; **per-alert-type auto-resolution policy table** (per
HIGH #1) with predicates evaluated on relevant Event Bus events;
**retention policy** (per MEDIUM #9) for audit-log + archived alerts;
**schema-version table + migration framework** for `data/operations.db`
(NEW; first migration framework in ARGUS).

### Reviewer

**Backend safety.**

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | WebSocket alerts handler (NEW file in `argus/ws/`); `alert_state` SQLite table; `data/operations.db` schema-version table + migration registry; VACUUM scheduling background task |
| **Modifies** | `argus/core/health.py` (rehydration on startup; auto-resolution predicates); `argus/main.py` (rehydration ordering — BEFORE Event Bus subscription); `argus/core/config.py` (extend `AlertsConfig` with `auto_resolve_on_condition_cleared`, `audit_log_retention_days`, `archived_alert_retention_days`); YAMLs; test files (~7 new tests + ~1 mock update) |
| **Integrates** | Session 5a.1's HealthMonitor in-memory state (now persistence-backed); all Event Bus events used by auto-resolution predicates (`ReconciliationCompletedEvent`, `IBKRReconnectedEvent`, `DatabentoHeartbeatEvent`, etc.) |

### Pre-Flight Reads (5 files)

1. Session 5a.1 deliverables (HealthMonitor in-memory state model).
2. `argus/ws/` existing WebSocket handler patterns (Arena, Observatory).
3. Sprint 31.8 S2 evaluation.db VACUUM-via-asyncio.to_thread pattern (reference for VACUUM strategy).
4. `data/operations.db` current schema (or initial creation if not present).
5. `sprint-spec.md` D9b acceptance criteria.

### Tests (~7 new pytest + ~1 mock update)

1. `test_ws_alerts_pushes_state_changes_realtime`
2. `test_ws_alerts_pushes_acknowledgment_state_change`
3. `test_alert_state_persists_to_sqlite_for_restart_recovery`
4. `test_alert_state_rehydrated_before_event_bus_subscription`
5. `test_auto_resolution_policy_phantom_short_5_cycles_zero_shares`
6. `test_auto_resolution_policy_phantom_short_retry_blocked_never_auto`
7. `test_auto_resolution_policy_cancel_propagation_timeout_never_auto`
8. `test_auto_resolution_policy_databento_dead_feed_3_healthy_heartbeats`
9. `test_audit_log_retention_forever_default`
10. `test_archived_alert_retention_90_days_default_purges_older`
11. `test_operations_db_schema_version_table_records_initial_migration`
12. `test_vacuum_scheduled_via_asyncio_to_thread_pattern`

(Note: this exceeds the ~7 estimate above. Some of these can fold; I've
listed the full set so the reviewer sees the surface. Test count remains
~7-8 in the design summary table.)

### Definition of Done

- [ ] `WS /ws/v1/alerts` pushes state changes (new alert,
      acknowledgment, auto-resolution).
- [ ] `alert_state` SQLite table persists active + archived alerts.
- [ ] Rehydration on startup BEFORE Event Bus subscription.
- [ ] **Per-alert-type auto-resolution policy table** (per HIGH #1)
      implemented; all 8 alert types have predicates AND tests.
- [ ] **Retention policy** (per MEDIUM #9): audit-log forever default;
      archived alerts 90 days default; both configurable.
- [ ] **VACUUM strategy** mirrors Sprint 31.8 S2 evaluation.db pattern.
- [ ] **Schema-version table + migration registry** in
      `data/operations.db`; first migration loads under framework;
      framework documented for future schema changes.
- [ ] CI green; Tier 2 CLEAR.

### Tier 2 Review Focus

- **Auto-resolution predicate correctness**: each predicate fires
  exactly when its cleared-condition is met, not earlier (premature
  resolution) and not later (missed resolution).
- **Rehydration ordering**: state must rehydrate BEFORE Event Bus
  subscription, or alerts emitted during the rehydration window are
  lost.
- **WebSocket fan-out reconnect resilience design** — frontend (5c)
  builds on this; the backend must support disconnect-reconnect
  recovery gracefully.
- **Migration framework**: schema_version table indexed correctly;
  migration registry pluggable for future use; rollback strategy on
  migration failure documented.
- **Retention policy + VACUUM**: tables grow then prune; VACUUM doesn't
  block event loop; aiosqlite limitation acknowledged (close → sync
  VACUUM via `asyncio.to_thread` → reopen, per Sprint 31.8 S2).
- **`phantom_short` auto-resolution alignment with 2c.2 gate-clear**:
  both use 5-cycle threshold; reviewer should verify they share the
  config field rather than duplicate it.

---

## Session 5b — IBKR Emitter TODOs + End-to-End Integration Tests + Behavioral Alpaca Check

### Scope (1 sentence)

Resolve `argus/execution/ibkr_broker.py:453` and `:531` emitter TODOs;
write end-to-end integration tests covering all 4+ emitter sites
through the full pipeline (5a.1 REST/ack + 5a.2 WebSocket/persistence);
**Alpaca emitter site explicitly EXCLUDED with behavioral
anti-regression assertion** (per third-pass MEDIUM #13).

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None |
| **Modifies** | `argus/execution/ibkr_broker.py` (2 emitter TODO sites); test files (~8 new tests + ~2 mock updates) |
| **Integrates** | Sessions 5a.1 (HealthMonitor consumer + REST + acknowledgment) and 5a.2 (WebSocket + persistence + auto-resolution policy table) |

### Pre-Flight Reads (5 files)

1. `argus/execution/ibkr_broker.py:453` — IBKR Gateway disconnect/reconnect failure TODO.
2. `argus/execution/ibkr_broker.py:531` — IBKR API auth/permission failure TODO.
3. `argus/execution/ibkr_broker.py` — full file (understand emitter context).
4. Sessions 5a.1 + 5a.2 deliverables (HealthMonitor consumer, REST/WS contract, auto-resolution policy).
5. `sprint-spec.md` D10 acceptance.

### Tests (~8 new pytest + ~2 mock updates)

1. `test_ibkr_disconnect_reconnect_failure_emits_system_alert`
2. `test_ibkr_auth_permission_failure_emits_system_alert`
3. **E2E**: `test_e2e_databento_dead_feed_emit_consume_rest_ws_ack`
4. **E2E**: `test_e2e_ibkr_disconnect_emit_consume_rest_ws_ack_auto_resolution`
5. **E2E**: `test_e2e_phantom_short_emit_consume_rest_ws_ack_5_cycle_auto_resolution`
6. **E2E**: `test_e2e_acknowledgment_writes_audit_persists_restart`
7. **E2E**: `test_e2e_phantom_short_retry_blocked_never_auto_resolves` (per 5a.2 policy table)
8. **Behavioral anti-regression** (per MEDIUM #13): `test_alpaca_data_service_does_not_emit_system_alert_events` —
   ```python
   def test_alpaca_data_service_does_not_emit_system_alert_events():
       """Sprint 31.91 boundary: Alpaca emitter site stays unwired
       until Sprint 31.94 retires the broker by deletion."""
       import inspect
       import argus.data.alpaca_data_service as mod
       src = inspect.getsource(mod)
       assert "SystemAlertEvent" not in src, (
           "Alpaca data service should not emit SystemAlertEvent — "
           "queued for retirement in Sprint 31.94 (DEF-178/183)."
       )
   ```
   This replaces the earlier line-number-based textual check which was
   brittle to innocuous edits anywhere in the file. The behavioral
   assertion is robust to refactors and enforces the actual constraint
   (no emission, regardless of where in the file).

### Definition of Done

- [ ] IBKR emitter TODO at `:453` resolved (disconnect/reconnect failure)
- [ ] IBKR emitter TODO at `:531` resolved (auth/permission failure)
- [ ] **Behavioral anti-regression** (per MEDIUM #13) passes
- [ ] All 4+ emitter sites tested end-to-end via Sessions 5a.1 + 5a.2
      pipeline
- [ ] Auto-resolution policy table (5a.2) verified end-to-end for at
      least 3 alert types
- [ ] CI green; Tier 2 CLEAR

### Tier 2 Review Focus

- E2E test coverage of full pipeline (emit → consume → REST → WS →
  ack → audit → auto-resolution)
- **Alpaca emitter behavioral anti-regression** correctness — robust
  to file refactors; enforces constraint at semantic level not lexical
- Emit/consume timing edge cases (rapid emissions, duplicate emissions)
- Auto-resolution predicates from 5a.2 fire correctly for live
  end-to-end scenarios

---

## **🔻 TIER 3 ARCHITECTURAL REVIEW #2 FIRES HERE 🔻**

**Trigger:** Session 5b lands cleanly on `main` + Tier 2 CLEAR + green CI.

**Scope:** Combined diff of **Sessions 5a.1 + 5a.2 + 5b** on main.
Reviews the alert-observability-backend-complete state:
- 5a.1: HealthMonitor consumer + REST endpoints + acknowledgment flow
  (atomic + idempotent transitions)
- 5a.2: WebSocket fan-out + SQLite persistence + restart recovery +
  per-alert-type auto-resolution policy table + retention/migration
  framework
- 5b: All backend emitters wired (IBKR×2 from this sprint + Databento
  pre-existing + phantom_short emitters from Sessions 2b.1/2b.2/3) +
  E2E integration tests

before the frontend builds on this API contract in Sessions 5c–5e.

**Verdict:** CLEAR → proceed to 5c. CONCERNS → revisions before 5c.
ESCALATE → halt sprint, operator re-planning.

See `escalation-criteria.md` §A1.5 for full Tier 3 #2 scope.

---

## Session 5c — `useAlerts` Hook + Dashboard Banner

### Scope (1 sentence)

`frontend/src/hooks/useAlerts.ts` (TanStack Query + WebSocket hybrid);
`frontend/src/components/AlertBanner.tsx` (Dashboard banner with
acknowledgment); pattern mirrors existing `useObservatory` /
`useArena` hooks.

### Reviewer

**Frontend** (different focus from backend safety reviewer used in
Sessions 0–4 + 5a–5b).

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `frontend/src/hooks/useAlerts.ts`; `frontend/src/components/AlertBanner.tsx`; corresponding Vitest spec files |
| **Modifies** | `frontend/src/pages/Dashboard.tsx` (banner mount); test files (~10 new Vitest tests) |
| **Integrates** | Session 5a's REST endpoints + WebSocket |

### Pre-Flight Reads (5 files)

1. `frontend/src/hooks/useObservatory.ts` (existing pattern reference).
2. `frontend/src/hooks/useArena.ts` (existing pattern reference).
3. `frontend/src/pages/Dashboard.tsx` (mount site).
4. Session 5a's REST + WebSocket API contract.
5. `sprint-spec.md` D11 acceptance.

### Tests (~10 new Vitest)

1. `useAlerts hook fetches initial state via REST`
2. `useAlerts hook subscribes to WebSocket on mount`
3. `useAlerts hook handles WebSocket disconnect with REST fallback`
4. `useAlerts hook handles WebSocket reconnect with state refetch`
5. `AlertBanner renders for active critical alert`
6. `AlertBanner renders correct severity styling (critical = red)`
7. `AlertBanner renders correct severity styling (warning = yellow)`
8. `AlertBanner acknowledgment button calls REST endpoint`
9. `AlertBanner disappears within 1s of acknowledgment`
10. `AlertBanner disappears within 1s of auto-resolution`

### Definition of Done

- [ ] `useAlerts` hook with WebSocket + TanStack Query hybrid
- [ ] Reconnect resilience (WebSocket disconnect → REST fallback → reconnect → resync)
- [ ] `AlertBanner` renders for any active critical alert
- [ ] Acknowledgment posts to REST
- [ ] Banner disappears on ack or auto-resolution within 1s
- [ ] Vitest coverage ≥90% for new code
- [ ] CI green; Tier 2 CLEAR (frontend reviewer)

### Tier 2 Review Focus

- Hook state machine (loading / connected / disconnected / error)
- Reconnect resilience: REST fallback during disconnect, refetch on reconnect
- WebSocket subscription cleanup on unmount
- Severity styling consistency with existing UI patterns
- Acknowledgment flow error handling (network failure, 404, etc.)
- Accessibility (ARIA roles, keyboard navigation)

---

## Session 5d — Toast Notification System + Acknowledgment UI Flow

### Scope (1 sentence)

`AlertToast` component pops up on any page when new critical alert
arrives via WebSocket; `AlertAcknowledgmentModal` requires reason text
before acknowledgment; toast queue handles multiple alerts.

### Reviewer

**Frontend.**

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | `frontend/src/components/AlertToast.tsx`; `frontend/src/components/AlertAcknowledgmentModal.tsx`; corresponding Vitest spec files |
| **Modifies** | Test files (~8 new Vitest tests) |
| **Integrates** | Session 5c's `useAlerts` hook |

### Pre-Flight Reads (4 files)

1. Session 5c's `useAlerts` hook (consumer).
2. Existing toast patterns in frontend (if any) for consistency.
3. Existing modal patterns (e.g., trade detail panel).
4. `sprint-spec.md` D12 acceptance.

### Tests (~8 new Vitest)

1. `AlertToast appears on new critical alert via WebSocket`
2. `AlertToast persists until acknowledged or auto-dismissed`
3. `AlertToast click opens AlertAcknowledgmentModal`
4. `AlertAcknowledgmentModal requires reason text before submit`
5. `AlertAcknowledgmentModal cancellable (alert stays active)`
6. `AlertAcknowledgmentModal successful submit shows audit-log entry`
7. `AlertToast queue stacks multiple alerts oldest-first dismissed when >5`
8. `AlertToast network failure on acknowledge shows retry option`

### Definition of Done

- [ ] Toast pops up on any page for new critical alert
- [ ] Persists until acknowledged or auto-dismissed
- [ ] Modal requires reason text
- [ ] Modal cancellable
- [ ] Toast queue handles overflow
- [ ] Vitest coverage ≥90%
- [ ] CI green; Tier 2 CLEAR (frontend reviewer)

### Tier 2 Review Focus

- Toast queue behavior under burst (multiple alerts arriving quickly)
- Modal accessibility (focus trap, escape key, ARIA)
- Acknowledgment audit-log entry visibility on success
- Error handling: network failure, validation failure, 409 conflict (already-acknowledged)
- Z-index layering with existing UI elements

---

## Session 5e — Observatory Alerts Panel + Cross-Page Integration

### Scope (1 sentence)

Observatory page gains alerts panel (active + historical, sortable /
filterable); `AlertBanner` and `AlertToast` mounted at Layout level for
cross-page persistence; integration tests assert banner persistence
across navigation.

### Reviewer

**Frontend.**

### Creates / Modifies / Integrates

| Aspect | Detail |
|--------|--------|
| **Creates** | None (panel is sub-component within Observatory) |
| **Modifies** | `frontend/src/pages/Observatory.tsx` (alerts panel addition); `frontend/src/components/Layout.tsx` (banner + toast cross-page mount); test files (~8 new Vitest + ~2 integration tests) |
| **Integrates** | Sessions 5c (banner, useAlerts) + 5d (toast, modal) |

### Pre-Flight Reads (5 files)

1. `frontend/src/pages/Observatory.tsx` — current page structure.
2. `frontend/src/components/Layout.tsx` — current layout component.
3. Sessions 5c + 5d components (consumed at Layout level).
4. Existing data-table / filter patterns in frontend.
5. `sprint-spec.md` D13 acceptance.

### Tests (~8 new Vitest + 2 integration)

1. `Observatory alerts panel renders active alerts`
2. `Observatory alerts panel renders historical alerts with date-range picker`
3. `Observatory alerts panel sort by severity / source / symbol`
4. `Observatory alerts panel filter by severity / source / symbol`
5. `Observatory alerts panel acknowledgment audit trail visible per alert`
6. `Observatory alerts panel click-through to detailed alert view`
7. **Integration**: `AlertBanner persists across page navigation Dashboard → TradeLog → Performance` (regression invariant 17)
8. **Integration**: `AlertToast appears on TradeLog page when new alert arrives`
9. `AlertBanner clears within 1s on acknowledgment from any page`
10. `AlertBanner clears within 1s on auto-resolution from any page`

### Definition of Done

- [ ] Observatory alerts panel functional (active + historical, sort, filter)
- [ ] `AlertBanner` mounted at Layout level (visible all 10 pages)
- [ ] `AlertToast` mounted at Layout level
- [ ] Banner cross-page persistence asserted via integration test
- [ ] Toast cross-page behavior asserted
- [ ] Vitest coverage ≥90%
- [ ] CI green; Tier 2 CLEAR (frontend reviewer)

### Tier 2 Review Focus

- Layout-level mounting doesn't break existing page-specific layouts
- Banner and toast don't conflict (z-index, positioning)
- Observatory panel performance with large historical dataset (pagination?)
- Date-range picker UX
- Cross-page integration tests reliable (no flakes)

---

## Sequential Execution

```
Session 0 (cancel_all_orders API)
        │
        ▼
Session 1a (bracket OCA + Error 201 defensive)
        │
        ▼
Session 1b (standalone-SELL OCA + Error 201 graceful)
        │
        ▼
Session 1c (broker-only paths + reconstruct docstring)
        │
        ▼ ── Tier 3 review #1 (OCA architecture seal — scope: 0+1a+1b+1c per LOW #17)
        │
Session 2a (recon contract refactor)
        │
        ▼
Session 2b.1 (broker-orphan + cycle infra)
        │
        ▼
Session 2b.2 (4 count-filter sites + 1 alert-alignment — two patterns per HIGH #2)
        │
        ▼
Session 2c.1 (gate + handler + persistence)
        │
        ▼
Session 2c.2 (clear-threshold default 5)
        │
        ▼
Session 2d (override API + audit + always-both-alerts + configurable threshold)
        │
        ▼
Session 3 (DEF-158 retry side-check)
        │
        ▼
Session 4 (mass-balance + IMSR replay)
        │
        ▼
Session 5a.1 (HealthMonitor + REST + atomic+idempotent ack — per HIGH #1 split)
        │
        ▼
Session 5a.2 (WebSocket + persistence + auto-resolution policy + retention/migration — per HIGH #1 split + MEDIUM #9)
        │
        ▼
Session 5b (IBKR emitters + E2E + behavioral Alpaca check — per MEDIUM #13)
        │
        ▼ ── Tier 3 review #2 (alert observability backend seal — scope: 5a.1+5a.2+5b)
        │
Session 5c (useAlerts hook + banner) [FRONTEND REVIEWER per HIGH #3]
        │
        ▼
Session 5d (toast + ack UI) [FRONTEND REVIEWER per HIGH #3]
        │
        ▼
Session 5e (Observatory panel + cross-page) [FRONTEND REVIEWER per HIGH #3]
```

Strictly sequential; each session's Tier 2 review must clear before the
next begins. CI must be green before the next begins (RULE-050).

---

## Test Tiering (DEC-328)

Per protocol §"Apply test suite tiering":

| Stage | Test command |
|-------|--------------|
| Sprint pre-flight (before Session 0) | Full pytest + Vitest |
| Each backend session close-out (0–4 + 5a.1 + 5a.2 + 5b) | Full pytest |
| Each backend session Tier 2 review | Scoped pytest (`tests/execution/` etc.) |
| **Tier 3 review #1** (after 1c, scope: 0+1a+1b+1c) | Full pytest |
| **Tier 3 review #2** (after 5b, scope: 5a.1+5a.2+5b) | Full pytest + Vitest |
| Each frontend session close-out (5c–5e) | Full Vitest + scoped pytest (regression baseline) |
| Each frontend session Tier 2 review | Scoped Vitest (focused on touched files) |
| Sprint final (Session 5e Tier 2) | Full pytest + full Vitest |

Reduces full-suite runs from ~36 (2× per session for 18 sessions) to
~22 (per-session close-out + 2 Tier 3 + final review). Frontend
sessions use Vitest primarily; pytest baseline runs to ensure backend
regressions don't sneak in.

---

*End Sprint 31.91 Session Breakdown (revised 3rd pass — 18-session shape;
HIGH #1 5a-split + HIGH #2 2b.2-reframe + LOW #17 Tier 3 #1 scope expanded
+ MEDIUM #13 behavioral Alpaca check).*
