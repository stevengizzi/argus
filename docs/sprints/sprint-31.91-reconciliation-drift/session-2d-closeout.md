# Sprint 31.91 — Session 2d Close-Out

> **Track:** Side-Aware Reconciliation Contract (2a → 2b.1 → 2b.2 → 2c.1 → 2c.2 → **2d**).
> **Position in track:** Sixth and final session. Wraps up the side-aware reconciliation track with the operator-facing override API + audit-log + L3 always-both-alerts at startup + L15 configurable threshold + B22 runbook section. After Session 2d the side-aware-reconciliation track is **COMPLETE.**

---

## ---BEGIN-CLOSE-OUT---

```json
{
  "session": "2d",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": 5169,
  "files_modified": [
    "argus/api/routes/reconciliation.py",
    "argus/api/routes/__init__.py",
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/system.yaml",
    "config/system_live.yaml",
    "docs/architecture.md",
    "docs/live-operations.md",
    "tests/api/test_session2d_phantom_short_override.py",
    "tests/execution/order_manager/test_reconciliation_redesign.py"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation-COMPLETE",
  "audit_table_creation": "inline CREATE TABLE IF NOT EXISTS in OrderManager.clear_phantom_short_gate_with_audit()",
  "main_py_block_lines": "1070-1141",
  "l15_threshold_default": 10
}
```

---

## Self-Assessment

**CLEAR.** Spec executed as written; no scope drift. Two minor structural choices worth flagging for the reviewer:

1. **Audit-table DDL placement.** The spec leaves the choice between (a) embedding `CREATE TABLE IF NOT EXISTS phantom_short_override_audit` in the OperationsStore initializer and (b) introducing a migration framework. Per RULE-007 (migration framework belongs to Session 5a.2), I chose (a) — the DDL is a constant on `OrderManager` (`_PHANTOM_SHORT_OVERRIDE_AUDIT_DDL` + two index DDLs) and runs idempotently inside the new `clear_phantom_short_gate_with_audit()` method's transaction. Mirrors the Session 2c.1 pattern for `phantom_short_gated_symbols` exactly. No new migration framework introduced.

2. **Endpoint handler lives outside `OrderManager`.** The spec's pseudocode put the SQLite work directly inside the route handler. I extracted the persistence work into a new `OrderManager.clear_phantom_short_gate_with_audit(symbol, reason, override_payload_json)` method so the route file stays a thin adapter and the audit-log + gated DELETE single-transaction guarantee lives in the same module that owns the gate's other persistence calls. The route still owns: payload validation (Pydantic), 404 short-circuit, in-memory state mutation (post-persistence), and operator-WARNING logging. This keeps the SQL surface co-located with the rest of `OrderManager`'s phantom-short persistence and makes the single-transaction property easy to grep-verify.

## Change Manifest

### `argus/core/config.py`
- Added `phantom_short_aggregate_alert_threshold: int = 10` field on `ReconciliationConfig` with `ge=1, le=1000` Pydantic bounds. Field description documents L3 always-fire-both disposition + L15 configurable threshold rationale.

### `argus/execution/order_manager.py`
- Added `_PHANTOM_SHORT_OVERRIDE_AUDIT_DDL` constant (CREATE TABLE) + `_PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_SYMBOL` + `_PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_TIMESTAMP` constants on `OrderManager`. All idempotent (`IF NOT EXISTS`).
- Added `clear_phantom_short_gate_with_audit(symbol, reason, override_payload_json) -> tuple[int, str | None, str | None]` method. Persistence-first: audit INSERT + gated DELETE in single `aiosqlite.commit()` (single transaction). Returns `(audit_id, prior_engagement_source, prior_engagement_alert_id)`. `prior_engagement_source` is `"reconciliation.broker_orphan_branch"` pre-Session-5a.1 (the only engagement source); `prior_engagement_alert_id` is `None` until Session 5a.1 wires HealthMonitor cross-reference.

### `argus/api/routes/reconciliation.py` (new file)
- New route module with single endpoint `POST /api/v1/reconciliation/phantom-short-gate/clear`.
- Pydantic request model `ClearPhantomShortGateRequest`: `symbol: str (min_length=1)`, `reason: str (min_length=10)`. Min-length-10 enforces non-trivial justification; mirrors spec.
- Pydantic response model `ClearPhantomShortGateResponse`: `symbol`, `cleared_at_utc`, `cleared_at_et`, `audit_id`, `prior_engagement_source`, `prior_engagement_alert_id`.
- Handler logic:
  1. Normalize symbol via `.strip().upper()` (spec requirement; without normalization "aapl" and "AAPL " would be treated as different symbols).
  2. Fast 404 if symbol not in `_phantom_short_gated_symbols`. NO audit-log row written for 404 case.
  3. Call `order_manager.clear_phantom_short_gate_with_audit(...)` — SQLite transaction commits both writes atomically.
  4. Mutate in-memory state AFTER persistence succeeds: `_phantom_short_gated_symbols.discard(symbol)` + `_phantom_short_clear_cycles.pop(symbol, None)`. SQLite write failure (which would raise) leaves in-memory state unchanged → fail-closed.
  5. Operator-visible WARNING log line with audit_id.
- Auth pattern matches `argus/api/routes/controls.py`: `_auth: dict = Depends(require_auth)` on the handler.

### `argus/api/routes/__init__.py`
- Imported and registered `reconciliation_router` under `/reconciliation` prefix with `tags=["reconciliation"]`.

### `argus/main.py`
- Added `SystemAlertEvent` to the `argus.core.events` import.
- Inserted Session 2d's startup-emission block IMMEDIATELY AFTER Session 2c.1's `await self._order_manager._rehydrate_gated_symbols_from_db()` line (lines 1078-1141 in the post-edit file). The combined 2c.1 + 2d block runs from line 1070 (Session 2c.1's preamble comment) through line 1141 (last per-symbol alert publish), terminating immediately before `await self._order_manager.start()` at line 1142.
- The block:
  1. Reads the `phantom_short_aggregate_alert_threshold` from `config.system.reconciliation`.
  2. Logs CRITICAL with the count + sorted gated-symbol list + runbook pointer.
  3. **L15-gated aggregate alert:** if `len(gated_list) >= agg_threshold`, publishes a `SystemAlertEvent(alert_type="phantom_short_startup_engaged", source="startup", severity="critical")` with structured `metadata` (gated_symbols, count, threshold).
  4. **L3 always-both-alerts:** unconditionally publishes one `SystemAlertEvent(alert_type="phantom_short", source="startup", severity="critical")` per gated symbol with `metadata={"symbol": ..., "side": "SELL", "detection_source": "startup.rehydration"}`. Per-symbol alerts ALWAYS fire — there is NO `if aggregate_fired: skip per-symbol` branch.
- The IMPROMPTU-04 startup invariant function (`check_startup_position_invariant` at line 124) is **untouched**. The new block is in `ArgusSystem.start()` Phase 9.x order-manager wiring, not anywhere near the invariant function.

### `config/system.yaml`, `config/system_live.yaml`
- Added explicit `phantom_short_aggregate_alert_threshold: 10` under the `reconciliation:` block in both YAMLs with operator-facing comment block (L3 always-fire-both + L15 tunability rationale).

### `docs/architecture.md`
- Added a `**reconciliation**` block to the §4 REST endpoint catalog (alphabetically placed between `quality` and `session`) listing the new `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint. Catalog freshness gate (`scripts/generate_api_catalog.py --verify`) passes.

### `docs/live-operations.md`
- Added a new top-level section **"Phantom-Short Gate Diagnosis and Clearance (Sprint 31.91 / DEC-385)"** placed before the existing OCA Architecture section. Contains all 7 subsections required by B22:
  - **Symptom** (CRITICAL log line + per-symbol + aggregate alerts).
  - **Diagnosis steps** (`scripts/ibkr_close_all_positions.py --dry-run` → cross-reference broker state).
  - **Clearance options** (a) auto-clear via flatten + 5 cycles, (b) manual API clearance with curl example, (c) UI clearance (Sessions 5d/5e).
  - **Audit-log location** (full schema + sqlite3 query example).
  - **Persistence verification** (restart + grep + audit row remains).
  - **Aggregate alert tuning** (per L15, default 10, high-vol → 20+, low-vol → 5).
  - **Cross-reference** (Sessions 2b.1, 2b.2, 2c.1, 2c.2, 2d).

### `tests/api/test_session2d_phantom_short_override.py` (new file)
- 6 new pytest tests, all passing.
  1. `test_phantom_short_gate_clear_endpoint_removes_symbol` — POST → 200, in-memory cleared, gated row deleted, audit row written with full schema.
  2. `test_phantom_short_gate_clear_audit_log_full_schema_persists` (M3) — clearance + reconnect to SQLite file fresh; audit row persists with all 8 columns populated.
  3. `test_phantom_short_gate_clear_unknown_symbol_404` — 404 with "not currently gated" detail; NO audit-log row written.
  4. `test_aggregate_phantom_short_startup_alert_at_10_symbols_AND_individual_alerts_fire` (L3) — 10 gated symbols → 1 aggregate + 10 per-symbol alerts (total 11). Reproduces main.py's startup-emission block against an isolated EventBus.
  5. `test_below_10_symbols_individual_alerts_only_no_aggregate` — 5 gated symbols → 0 aggregate + 5 per-symbol alerts. Threshold gates only the aggregate.
  6. `test_startup_log_line_lists_gated_symbols` — 3 gated (TSLA, NVDA, AMD) → CRITICAL log line contains sorted list `['AMD', 'NVDA', 'TSLA']`.

### `tests/execution/order_manager/test_reconciliation_redesign.py`
- Updated the `expected_keys` set in `test_reconciliation_config_fields_recognized` to include the new `phantom_short_aggregate_alert_threshold` field. Lock-step update with the model field; identical to how Sessions 2b.1/2c.1/2c.2 extended the same set.

## Pre-Flight Checks (RULE-038)

Verified before any edits:
- `grep -n "_phantom_short_gated_symbols\|_phantom_short_clear_cycles" argus/execution/order_manager.py` returned matches at lines 413, 424, 537, 2405-2407, 2518-2547, 2611-2637, 4014-4058 — Session 2c.1/2c.2 deliverables on `main`.
- `grep -n "broker_orphan_consecutive_clear_threshold" argus/core/config.py` confirmed line 272 — Session 2c.2 deliverable on `main`.
- `argus/api/routes/` listing showed 30 existing route files; no `reconciliation.py` existed (greenfield create).
- `grep -n "@router.websocket\|router = APIRouter\|@router" argus/api/routes/*.py` confirmed the canonical route pattern (matches `controls.py` exactly).
- `grep -n "rehydrat" argus/main.py` confirmed Session 2c.1's rehydration call at line 1077; Session 2d's block inserts immediately after (line 1078+).
- `grep -n "check_startup_position_invariant" argus/main.py` confirmed function defined at line 124, called from `ArgusSystem.start()` at line 377 — both untouched by Session 2d edits.

## Definition of Done — Full Checklist

- [x] `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint accessible — Test 1 verifies 200 status.
- [x] `phantom_short_override_audit` table created with full schema — DDL idempotent in `OrderManager.clear_phantom_short_gate_with_audit`.
- [x] Audit-log entries persist across restarts — Test 2 reconnects to SQLite file fresh + asserts row queryable.
- [x] L3 always-both-alerts at startup — Test 4 verifies 1 aggregate + 10 per-symbol when count = threshold.
- [x] L15 configurable threshold (`phantom_short_aggregate_alert_threshold` default 10) — Pydantic model + YAMLs + Test 5 verifies sub-threshold behavior (no aggregate, but per-symbol still fires).
- [x] CRITICAL startup log line listing gated symbols — Test 6 asserts on log content; sorted alphabetically.
- [x] `docs/live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" section added per B22 — all 7 subsections present + verified by inspection.
- [x] 6 new tests; all passing — `tests/api/test_session2d_phantom_short_override.py`.
- [x] CI green; pytest baseline ≥ 5,144 — full-suite run (excluding `tests/test_main.py`) reports **5,169 passed**, 0 failed, 34 warnings.
- [x] All do-not-modify list items show zero `git diff` (with the scoped exception for `main.py` startup-block extension) — `argus/core/health.py`, `argus/risk/*`, IMPROMPTU-04 invariant function all untouched.
- [ ] Tier 2 review verdict CLEAR — pending; review prompt at `session-2d-review.md` (next operator step).
- [x] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-2d-closeout.md` — this file.

## Sprint-Level Regression Checklist

- **Invariant 5 (pytest baseline ≥ 5,144):** PASS — 5,169 passed.
- **Invariant 6 (`tests/test_main.py` 39+5):** Pre-existing baseline drift — 31 pass / 5 skip / 8 fail BOTH before AND after Session 2d (verified via `git stash` + re-run). Zero delta from Session 2d. The 8 failing tests are not new regressions and not within Session 2d's scope; documented in CLAUDE.md DEF-048 lineage.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — `check_startup_position_invariant()` at `argus/main.py:124` and its call site at `:377` unchanged. Verified via grep.
- **Invariant 14 (Recon detects shorts after Session 2d):** "full + override API + audit + configurable threshold" — endpoint live, audit-log persisting, L3 + L15 wired. PASS.
- **Invariant 15 (do-not-modify):** PASS with `argus/main.py` scoped exception (combined 2c.1 + 2d startup block at lines 1070-1141, tightly scoped, does NOT touch IMPROMPTU-04 invariant function).

## Session-Specific Reviewer Focus (echoes from spec §"Session-Specific Review Focus")

1. **API endpoint authentication consistency.** `POST /api/v1/reconciliation/phantom-short-gate/clear` carries `_auth: dict = Depends(require_auth)`. Pattern matches `argus/api/routes/controls.py` exactly.

2. **Audit-log schema captures full forensic detail (M3).** All 8 columns:
   - `id` (autoincrement PK)
   - `timestamp_utc` + `timestamp_et` (both required)
   - `symbol` (uppercase-normalized at handler boundary)
   - `prior_engagement_source` (`"reconciliation.broker_orphan_branch"` pre-5a.1)
   - `prior_engagement_alert_id` (None pre-5a.1)
   - `reason_text` (≥10-char operator justification, Pydantic-validated)
   - `override_payload_json` (full request body)

3. **Aggregation + individual alerts both fire (L3 — no suppression).** Tests 4 and 5 verify behavior. Reviewer should grep `argus/main.py` for `if aggregate_fired` or similar — the `for symbol in gated_list:` per-symbol loop runs unconditionally.

4. **Persistence-first ordering in clearance.** `argus/api/routes/reconciliation.py` handler calls `clear_phantom_short_gate_with_audit(...)` BEFORE mutating `_phantom_short_gated_symbols`. The SQL transaction commits both writes (audit INSERT + gated DELETE) before the in-memory state changes; on SQL failure the in-memory state stays engaged → fail-closed.

5. **Single transaction for audit + delete.** `clear_phantom_short_gate_with_audit` opens a single `async with aiosqlite.connect(...)` block, runs DDLs + INSERT + DELETE, then a single `commit()`. A crash between the INSERT and the DELETE rolls both back.

6. **Symbol normalization (uppercase, strip).** Handler does `payload.symbol.strip().upper()` BEFORE the gate-membership check + before passing to `clear_phantom_short_gate_with_audit`. Reviewer can grep the route file for `.strip().upper()`.

7. **B22 runbook section completeness.** All 7 subsections (Symptom, Diagnosis, Clearance options a/b/c, Audit-log location, Persistence verification, Aggregate alert tuning, Cross-reference) present in `docs/live-operations.md`.

8. **Main.py edit boundary.** Combined 2c.1 + 2d block at lines 1070-1141. Does NOT touch:
   - `check_startup_position_invariant()` (line 124-161, unchanged)
   - `_startup_flatten_disabled` setter logic (lines 376-400, unchanged)
   - Any other startup hook unrelated to the phantom-short gate.

## Test Delta

- New tests: 6 (Session 2d).
- Modified tests: 1 (`test_reconciliation_config_fields_recognized` updated set in `test_reconciliation_redesign.py` — lock-step with the new model field; not a count-changing edit).
- Pytest pre-Session-2d (per Session 2c.2 closeout): 5,163.
- Pytest post-Session-2d: **5,169** (delta +6, matches new test count).

## Doc Sync Considerations (Phase B)

This session's runbook + architecture catalog updates land IN-SPRINT (B22 + the new `**reconciliation**` block in §4 REST catalog), not at sprint close. The sprint-close doc-sync (Phase B) will:
- B22: verify presence (already there post-Session-2d).
- Update CLAUDE.md to reflect Session 2d landed (active sprint state, DEF-204 closure trace gains the 2d citation).
- DEC-385's session-scope text already lists 2d in the design summary; confirms it carries through.

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `docs/sprints/sprint-31.91-reconciliation-drift/session-2d-review.md`.

---

*Side-aware-reconciliation track is **COMPLETE** after Session 2d. Sessions 3 (DEF-158 retry side-check) and 4 (mass-balance + IMSR replay) are on parallel tracks — Session 3 depends only on Session 2b.1's `phantom_short` alert taxonomy; Session 4 depends on the full DEF-204 fix bundle for IMSR replay validation.*
