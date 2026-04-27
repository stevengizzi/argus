# Sprint 31.91, Session 2d: Operator Override API + Audit-Log + Always-Both-Alerts + Runbook

> **Track:** Side-Aware Reconciliation Contract (Sessions 2a → 2b.1 → 2b.2 → 2c.1 → 2c.2 → **2d**).
> **Position in track:** Sixth and final session. Adds operator-facing override capability + audit-log + the L3 always-both-alerts behavior + B22 runbook section.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full.** RULE-038, RULE-050, RULE-019, RULE-007.

2. Read these files to load context:
   - `argus/api/` directory — find existing reconciliation routes (`grep -rn "reconciliation\|router" argus/api/ | head -10`)
   - `argus/main.py` — startup log lines (find where the IMPROMPTU-04 startup invariant log appears; the new CRITICAL gated-symbols log line must be co-located)
   - Sessions 2c.1's `_phantom_short_gated_symbols` and persistence; 2c.2's auto-clear logic
   - `docs/live-operations.md` — current runbook structure (Session 2d adds the "Phantom-Short Gate Diagnosis and Clearance" section, B22 in doc-update-checklist)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D5 Session 2d portion + D8 (always-both-alerts L3, threshold L15)
   - `docs/sprints/sprint-31.91-reconciliation-drift/doc-update-checklist.md` B22 — runbook section structure

3. Run scoped tests:

   ```
   python -m pytest tests/execution/ tests/api/ -n auto -q
   ```

4. Verify branch: **`main`**.

5. Verify Sessions 2a-2c.2 deliverables on `main`:

   ```bash
   grep -n "_phantom_short_gated_symbols\|_phantom_short_clear_cycles" argus/execution/order_manager.py
   grep -n "broker_orphan_consecutive_clear_threshold" argus/core/config.py
   ```

6. **Pre-flight grep — locate existing API router pattern:**

   ```bash
   ls argus/api/routes/
   grep -n "router = APIRouter\|@router" argus/api/routes/*.py | head -20
   grep -n "reconciliation" argus/api/ -r
   ```

   Determine whether reconciliation routes already exist. If yes, the new endpoint joins the existing reconciliation router; if no, create a new file `argus/api/routes/reconciliation.py` mirroring the existing route-file pattern.

7. **Pre-flight grep — locate the IMPROMPTU-04 startup log line in `main.py`:**

   ```bash
   grep -n "IMPROMPTU-04\|startup invariant\|short position detected" argus/main.py
   ```

   The new "gated symbols at startup" CRITICAL log line goes near the existing startup invariant log line — same temporal location (post-rehydration, pre-event-bus subscription).

## Objective

Wrap up the side-aware reconciliation track by giving operators the ability to manually clear the phantom-short gate via REST API, with full audit-log forensics. Add the L3 disposition (no alert suppression — both aggregate AND per-symbol alerts always fire) with a configurable threshold per L15. Add the B22 runbook section to `docs/live-operations.md` so operators have a documented diagnosis-and-clearance procedure.

## Requirements

1. **Add the API endpoint `POST /api/v1/reconciliation/phantom-short-gate/clear`:**

   Request body:
   ```python
   class ClearPhantomShortGateRequest(BaseModel):
       symbol: str
       reason: str = Field(min_length=10, description="Operator's justification for manual gate clearance.")
   ```

   Response:
   ```python
   class ClearPhantomShortGateResponse(BaseModel):
       symbol: str
       cleared_at_utc: str
       cleared_at_et: str
       audit_id: int  # the autoincrementing PK from phantom_short_override_audit
       prior_engagement_source: str | None  # e.g. "reconciliation.broker_orphan_branch"
       prior_engagement_alert_id: str | None  # if known; populated if cross-referenced from HealthMonitor (Sessions 5a.1+)
   ```

   Handler logic:
   ```python
   @router.post("/phantom-short-gate/clear", response_model=ClearPhantomShortGateResponse)
   async def clear_phantom_short_gate(
       payload: ClearPhantomShortGateRequest,
       order_manager: Annotated[OrderManager, Depends(get_order_manager)],
   ) -> ClearPhantomShortGateResponse:
       symbol = payload.symbol.strip().upper()  # normalize

       # 404 if symbol not gated
       if symbol not in order_manager._phantom_short_gated_symbols:
           raise HTTPException(
               status_code=404,
               detail=f"Symbol {symbol} is not currently gated.",
           )

       # Compose the audit entry. prior_engagement_source/alert_id available
       # post-Session 5a.1; for now best-effort from local state.
       prior_source = "reconciliation.broker_orphan_branch"  # the only engagement source pre-5a.1
       prior_alert_id = None  # Session 5a.1 will allow HealthMonitor cross-ref

       async with aiosqlite.connect(order_manager._operations_db_path) as db:
           cursor = await db.execute(
               """
               INSERT INTO phantom_short_override_audit
               (timestamp_utc, timestamp_et, symbol, prior_engagement_source,
                prior_engagement_alert_id, reason_text, override_payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               """,
               (
                   utcnow_iso(),
                   etnow_iso(),
                   symbol,
                   prior_source,
                   prior_alert_id,
                   payload.reason,
                   json.dumps(payload.model_dump()),
               ),
           )
           audit_id = cursor.lastrowid
           await db.execute(
               "DELETE FROM phantom_short_gated_symbols WHERE symbol = ?",
               (symbol,),
           )
           await db.commit()

       # Update in-memory state AFTER persistence succeeds
       order_manager._phantom_short_gated_symbols.discard(symbol)
       order_manager._phantom_short_clear_cycles.pop(symbol, None)

       order_manager._logger.warning(
           "Phantom-short gate MANUALLY CLEARED for %s by operator. "
           "Reason: %r. Audit-id: %d.",
           symbol, payload.reason, audit_id,
       )

       return ClearPhantomShortGateResponse(
           symbol=symbol,
           cleared_at_utc=utcnow_iso(),
           cleared_at_et=etnow_iso(),
           audit_id=audit_id,
           prior_engagement_source=prior_source,
           prior_engagement_alert_id=prior_alert_id,
       )
   ```

   Notes:
   - Persistence-first ordering: write to SQLite, then update in-memory state. If the SQLite write fails, in-memory state is unchanged and the gate remains engaged — fail-closed.
   - The `audit_id` returned to the operator is the audit-log row PK; operator can later query the row to retrieve the full forensic context.

2. **Create the `phantom_short_override_audit` SQLite table:**

   ```sql
   CREATE TABLE IF NOT EXISTS phantom_short_override_audit (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp_utc TEXT NOT NULL,
       timestamp_et TEXT NOT NULL,
       symbol TEXT NOT NULL,
       prior_engagement_source TEXT,
       prior_engagement_alert_id TEXT,
       reason_text TEXT NOT NULL,
       override_payload_json TEXT NOT NULL
   );

   CREATE INDEX IF NOT EXISTS idx_psoa_symbol ON phantom_short_override_audit(symbol);
   CREATE INDEX IF NOT EXISTS idx_psoa_timestamp ON phantom_short_override_audit(timestamp_utc);
   ```

   Schema migration: if the project has a migration framework, register this as a new migration. If not, embed the `CREATE TABLE IF NOT EXISTS` in the OperationsStore initializer (or wherever Session 2c.1 created the `phantom_short_gated_symbols` table). Per RULE-007, do not introduce a new migration framework — Session 5a.2 owns that work per the design summary.

3. **CRITICAL startup log line** in `argus/main.py`:

   Find the existing IMPROMPTU-04 startup-invariant log location (pre-flight located it). Add IMMEDIATELY AFTER the rehydration call (which Session 2c.1 inserted):

   ```python
   if order_manager._phantom_short_gated_symbols:
       gated_list = sorted(order_manager._phantom_short_gated_symbols)
       logger.critical(
           "STARTUP: %d phantom-short gated symbol(s) rehydrated from prior session: %s. "
           "These symbols will reject new entries. See "
           "docs/live-operations.md 'Phantom-Short Gate Diagnosis and Clearance' "
           "for operator triage steps.",
           len(gated_list), gated_list,
       )
       # L3 always-both-alerts: per-symbol alerts fire below; aggregate alert
       # fires here if threshold met (configurable per L15).
       agg_threshold = config.reconciliation.phantom_short_aggregate_alert_threshold
       if len(gated_list) >= agg_threshold:
           agg_alert = SystemAlertEvent(
               severity="critical",
               source="startup",
               alert_type="phantom_short_startup_engaged",
               message=(
                   f"STARTUP: {len(gated_list)} phantom-short symbols rehydrated "
                   f"(threshold: {agg_threshold}). Operator triage required."
               ),
               metadata={
                   "gated_symbols": gated_list,
                   "count": len(gated_list),
                   "threshold": agg_threshold,
               },
           )
           event_bus.publish(agg_alert)

       # Per-symbol alerts ALWAYS fire (L3 — no suppression even when aggregate fires)
       for symbol in gated_list:
           per_symbol_alert = SystemAlertEvent(
               severity="critical",
               source="startup",
               alert_type="phantom_short",  # same taxonomy as Session 2b.1's reconciliation-source alert
               message=(
                   f"STARTUP: phantom-short gate rehydrated for {symbol}. "
                   f"Operator triage required."
               ),
               metadata={
                   "symbol": symbol,
                   "side": "SELL",
                   "detection_source": "startup.rehydration",
               },
           )
           event_bus.publish(per_symbol_alert)
   ```

   Notes on L3 always-both-alerts:
   - Aggregate alert fires when count >= threshold; per-symbol alerts ALSO fire.
   - L3 disposition: do not suppress per-symbol alerts because the aggregate fired. Operator needs both signals: the aggregate to know "many symbols are gated"; the per-symbol to triage each one.
   - Threshold is configurable via `phantom_short_aggregate_alert_threshold` (next requirement).

4. **Add config field `phantom_short_aggregate_alert_threshold: int = 10`** to `ReconciliationConfig`:

   ```python
   phantom_short_aggregate_alert_threshold: int = Field(
       default=10,
       ge=1,
       le=1000,
       description=(
           "When N or more symbols are gated at startup, an aggregate "
           "phantom_short_startup_engaged alert fires alongside the per-symbol "
           "alerts (L3 — both always fire). High-volume operators may raise "
           "to 20+ to reduce noise; low-volume operators (steady state post-fix) "
           "may lower to 5 to catch any resurgence early. Default 10 per L15 "
           "(Phase A revisit configurable threshold disposition)."
       ),
   )
   ```

   Update YAMLs.

5. **Add the runbook section to `docs/live-operations.md`** per B22 of doc-update-checklist:

   Section title: **"Phantom-Short Gate Diagnosis and Clearance"**

   Subsections (verbatim structure from `doc-update-checklist.md` B22):

   - **Symptom:** ARGUS startup logs CRITICAL line listing N gated symbols. Per-symbol `phantom_short` alerts and (if N >= threshold) aggregate `phantom_short_startup_engaged` alert in the alerts panel (Session 5e UI surface; pre-5e the alert events are visible in JSONL logs).

   - **Diagnosis steps:**
     1. Check actual broker state: `python scripts/ibkr_close_all_positions.py --dry-run` (or `ibkr_query_positions.py` if it exists; otherwise the close script's `--dry-run` flag prints positions before action).
     2. Cross-reference the gated-symbol list against broker state. If broker reports a SHORT for the gated symbol → confirmed phantom-short scenario; proceed to Clearance Option (a).
     3. If broker reports zero / long position → eventual-consistency gap or stale gate state; proceed to Clearance Option (b) or (c).

   - **Clearance options:**
     - **(a)** Run `scripts/ibkr_close_all_positions.py` to manually flatten the broker-side short. Then wait 5 reconciliation cycles (~5 minutes) for auto-clear (Session 2c.2's M4 default; was 3 in earlier drafts).
     - **(b)** Manual API clearance: `POST /api/v1/reconciliation/phantom-short-gate/clear` with `{"symbol": "AAPL", "reason": "operator manually flattened short via ibkr_close_all_positions.py at 09:31 ET"}`. Reason string must be ≥10 chars; logs to `phantom_short_override_audit`.
     - **(c)** UI clearance: navigate to Observatory alerts panel (Session 5e), click acknowledgment on the `phantom_short` alert. (Pre-5e, options (a) and (b) only.)

   - **Audit-log location:** `phantom_short_override_audit` table in `data/operations.db`. Schema: `(id, timestamp_utc, timestamp_et, symbol, prior_engagement_source, prior_engagement_alert_id, reason_text, override_payload_json)`. Persists across restarts. Query with `sqlite3 data/operations.db "SELECT * FROM phantom_short_override_audit ORDER BY id DESC LIMIT 10;"`.

   - **Persistence verification:** entries survive ARGUS restart. After clearance via (b) or (c), restart ARGUS and confirm: (i) gated symbol does NOT reappear in startup CRITICAL log; (ii) audit-log row remains queryable.

   - **Aggregate alert tuning** (per L15): the threshold for `phantom_short_startup_engaged` is `reconciliation.phantom_short_aggregate_alert_threshold` (default 10). Operators should tune based on observed phantom-short volume: high-volume operators may raise to 20+ to reduce noise; low-volume operators (post-fix steady state) may lower to 5 to catch any resurgence early.

   - **Cross-reference:** Sessions 2b.1 (broker-orphan branch detection), 2b.2 (Health integrity check + EOD Pass 2 alert taxonomy), 2c.1 (per-symbol gate + persistence + M5 rehydration), 2c.2 (auto-clear at 5 cycles).

6. **No edits to do-not-modify regions.** Standard list. Note: Session 2d's `main.py` edit is a SCOPED exception per invariant 15 (the startup gated-symbols log block IS Session 2d's contribution; reviewer verifies it's adjacent to Session 2c.1's rehydration insertion and does NOT touch the IMPROMPTU-04 startup invariant code).

   **CRITICAL boundary check:** Session 2c.1 already inserted code in `main.py`'s startup sequence. Session 2d adds MORE code IMMEDIATELY AFTER 2c.1's insertion. The combined block is the scoped exception. Do not let the block sprawl beyond what's strictly required.

## Tests (~6 new pytest)

1. **`test_phantom_short_gate_clear_endpoint_removes_symbol`**
   - Setup: `_phantom_short_gated_symbols = {"AAPL"}`; row in `phantom_short_gated_symbols` table.
   - POST `/api/v1/reconciliation/phantom-short-gate/clear` with `{"symbol": "AAPL", "reason": "manually flattened via close script"}`.
   - Assert: response status 200; `audit_id` populated.
   - Assert: in-memory state AAPL removed; SQLite row in `phantom_short_gated_symbols` deleted.
   - Assert: row in `phantom_short_override_audit` written with full schema.

2. **`test_phantom_short_gate_clear_audit_log_full_schema_persists`** (M3)
   - Same setup + clearance.
   - Restart ARGUS (or simulate by reconnecting to the SQLite file fresh).
   - Query `SELECT * FROM phantom_short_override_audit WHERE symbol='AAPL';`.
   - Assert: row present with all 8 columns populated (id, timestamp_utc, timestamp_et, symbol, prior_engagement_source, prior_engagement_alert_id, reason_text, override_payload_json).
   - Assert: `override_payload_json` parses to a dict with at least `{"symbol": "AAPL", "reason": "..."}`.

3. **`test_phantom_short_gate_clear_unknown_symbol_404`**
   - Setup: `_phantom_short_gated_symbols = {}`.
   - POST clearance for AAPL.
   - Assert: 404 status; response body contains "not currently gated".
   - Assert: NO audit-log row written (404 = no operation occurred).

4. **`test_aggregate_phantom_short_startup_alert_at_10_symbols_AND_individual_alerts_fire`** (L3)
   - Setup: pre-populate `phantom_short_gated_symbols` table with 10 symbols.
   - Trigger startup sequence (rehydration → CRITICAL log → alert emissions).
   - Assert: 1 aggregate `phantom_short_startup_engaged` alert published (L15 threshold 10 met).
   - Assert: 10 per-symbol `phantom_short` alerts ALSO published (L3 — no suppression).
   - Assert: total `SystemAlertEvent` count = 11 (1 aggregate + 10 per-symbol).

5. **`test_below_10_symbols_individual_alerts_only_no_aggregate`**
   - Setup: pre-populate 5 symbols (below threshold).
   - Trigger startup.
   - Assert: 0 aggregate alerts; 5 per-symbol alerts.

6. **`test_startup_log_line_lists_gated_symbols`**
   - Setup: pre-populate 3 symbols (TSLA, NVDA, AMD).
   - Trigger startup; capture log output.
   - Assert: CRITICAL log line contains `"3 phantom-short gated symbol(s)"` and lists the symbols sorted alphabetically (`['AMD', 'NVDA', 'TSLA']`).

## Definition of Done

- [ ] `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint accessible.
- [ ] `phantom_short_override_audit` table created with full schema.
- [ ] Audit-log entries persist across restarts (Test 2).
- [ ] L3 always-both-alerts at startup (Test 4).
- [ ] L15 configurable threshold (`phantom_short_aggregate_alert_threshold` default 10).
- [ ] CRITICAL startup log line listing gated symbols.
- [ ] `docs/live-operations.md` "Phantom-Short Gate Diagnosis and Clearance" section added per B22.
- [ ] 6 new tests; all passing.
- [ ] CI green; pytest baseline ≥ 5,144.
- [ ] All do-not-modify list items show zero `git diff` (with the scoped exception for `main.py` startup-block extension).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-2d-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "2d",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 6,
  "tests_total_after": <fill>,
  "files_modified": [
    "argus/api/routes/reconciliation.py",
    "argus/main.py",
    "argus/core/config.py",
    "docs/live-operations.md",
    "<test files>"
  ],
  "donotmodify_violations": 0,
  "tier_3_track": "side-aware-reconciliation-COMPLETE"
}
```

Cite in close-out:
- Whether the `phantom_short_override_audit` table was created via migration framework or inline `CREATE TABLE IF NOT EXISTS` (and if inline, where).
- The exact `main.py` line range of the startup log block (combined 2c.1 rehydration + 2d gated-symbols extension).
- Confirmation that `docs/live-operations.md` B22 section matches the structure in `doc-update-checklist.md`.

Note: After Session 2d lands, the **side-aware-reconciliation track is COMPLETE.** The next session is Session 3 (DEF-158 retry side-check), which is on a separate but parallel track (DEF-158 mirror). Session 3 does NOT depend on Sessions 2a-2d structurally; it depends only on Session 2b.1's `phantom_short` alert taxonomy.

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `session-2d-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **API endpoint authentication consistency.** Reviewer confirms the new endpoint follows the existing reconciliation-route auth pattern (or whatever auth pattern the project uses for sensitive operations). If no auth pattern exists yet, note as a deferred item — but the endpoint MUST not silently bypass any guard the rest of `/api/v1/reconciliation/*` uses.

2. **Audit-log schema captures full forensic detail (M3).** All 8 columns must be populated:
   - `id` (autoincrement PK)
   - `timestamp_utc` + `timestamp_et` (both required for live-trading forensics across DST)
   - `symbol` (normalized to uppercase)
   - `prior_engagement_source` ("reconciliation.broker_orphan_branch" pre-5a.1)
   - `prior_engagement_alert_id` (None pre-5a.1; populated post-5a.1 once HealthMonitor exposes alert IDs)
   - `reason_text` (operator's ≥10-char justification)
   - `override_payload_json` (full request body for forensic replay)

3. **Aggregation + individual alerts both fire (L3 — no suppression).** Tests 4 and 5 verify. Reviewer additionally inspects the alert-emission code in main.py and confirms there is NO `if aggregate_fired: skip per-symbol` branch.

4. **Persistence-first ordering in clearance.** SQLite write to audit-log + delete from gated-symbols table happens BEFORE in-memory state mutation. Reviewer confirms by reading the handler. Without persistence-first ordering, a SQLite write failure would leave in-memory state cleared but persistence still showing the gate engaged — a desync that reappears on restart.

5. **Single transaction for audit + delete.** Both writes happen within the same `aiosqlite` connection's `commit()`. Reviewer verifies; without single-transaction semantics, a crash between the audit INSERT and the gated-symbols DELETE would produce an audit row pointing to a still-gated symbol (operationally weird but not catastrophic; flag as a CONCERNS-tier issue if observed).

6. **Symbol normalization (uppercase, strip).** The handler normalizes `payload.symbol` to `.strip().upper()`. Reviewer confirms; without normalization, `"aapl"` and `"AAPL "` would be treated as different symbols from the operator's perspective.

7. **B22 runbook section completeness.** Reviewer reads `docs/live-operations.md` and confirms all 7 subsections from B22 (Symptom, Diagnosis, Clearance options a/b/c, Audit-log location, Persistence verification, Aggregate alert tuning, Cross-reference) are present.

8. **Main.py edit boundary.** The combined Session 2c.1 + 2d block in startup is the scoped exception. Reviewer verifies the block does NOT touch:
   - `check_startup_position_invariant()` (IMPROMPTU-04, do-not-modify)
   - Any other startup hook unrelated to the phantom-short gate

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 5:** PASS — expected ≥ 5,144.
- **Invariant 6 (`tests/test_main.py` 39+5):** PASS — Session 2d edits `main.py`, so this invariant is at risk.
- **Invariant 9 (IMPROMPTU-04 startup invariant unchanged):** PASS — Session 2d's main.py edit must not touch `check_startup_position_invariant()`.
- **Invariant 14:** Row "After Session 2d" — Recon detects shorts = "full + override API + audit + configurable threshold".
- **Invariant 15:** PASS with main.py scoped exception (combined 2c.1 + 2d block).

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (uncertain whether main.py edit crosses the IMPROMPTU-04 boundary).
- **C7** (existing API tests fail because the new route file changed router registration; reviewer should grep for ` register_router` and confirm the new file is registered without breaking existing routes).

---

*End Sprint 31.91 Session 2d implementation prompt.*
