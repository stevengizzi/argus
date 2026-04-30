# Tier 2 Review: Sprint 31.92, Session S3b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s3b-path2-emit-sites-and-broker-verified-fallback-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-050** (CI green required), **RULE-051** (mechanism-vs-symptom validation — FAI #10's pair-wise comparison is the falsification, not a single-mode test), **RULE-053** (architectural-seal verification — DEC-117 / DEC-364 / DEC-369 / DEC-372 / DEC-385 / DEC-386 / DEC-388 / DEF-158 3-branch side-check all sealed; `argus/main.py:1081` and surrounding phase-orchestration sealed under A-class halt **A12**).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s3b-path2-emit-sites-and-broker-verified-fallback-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — the corresponding impl prompt references `session-s3b-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~2..HEAD` (covers BOTH the implementation commit AND the FAI #10 materialization commit; confirm exact range against the close-out's commit list).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/order_manager/ tests/execution/test_ibkr_broker.py argus/api/ tests/api/ -n auto -q
  ```
  (Plus the new `tests/execution/test_ibkr_broker_concurrent_callers.py` file under the `tests/execution/` umbrella, exercised by the first scoped path.)
- **Files that should NOT have been modified:**
  - `argus/main.py` beyond the OrderManager construction-call-site `selected_mechanism=...` keyword addition. **Any other `argus/main.py` change fires A-class halt A12.**
  - `argus/execution/order_manager.py` DEF-158 3-branch side-check region inside `_check_flatten_pending_timeouts` (BUY/SELL/unknown — preserve verbatim per regression invariant 8 / SbC §"Edge Cases to Reject" #13). A-class halt **A5** fires if a 4th branch is added.
  - `argus/execution/order_manager.py` DEF-199 A1 fix region (SbC §"Do NOT modify" — invariant 1 / A-class halt **A12**).
  - `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond the single-line `is_reconstructed = True` addition (S4a-i AC3.7).
  - `argus/execution/ibkr_broker.py::place_bracket_order` OCA threading (DEC-386 S1a preserved byte-for-byte).
  - `argus/execution/ibkr_broker.py::_handle_oca_already_filled` (DEC-386 S1b preserved verbatim).
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` (relocation deferred to Sprint 31.93 — SbC §"Out of Scope" #4).
  - SimulatedBroker existing fill-model semantics, immediate-fill behavior, OCA simulation — only ADD `refresh_positions` no-op (SbC §"Do NOT modify" #2 / SbC §"Out of Scope" #18).
  - The DEC-385 `phantom_short_retry_blocked` SystemAlertEvent emitter source — reuse verbatim, conditional on AC2.5 case (c) + Branch 4.
  - `argus/models/trading.py` (existing baseline; `ManagedPosition.halt_entry_until_operator_ack` field addition is in scope at S3b but no other `models/trading.py` changes).
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `frontend/`, `argus/ui/` (zero UI scope — regression invariant 12 / B-class halt B8).
  - `workflow/` submodule (Universal RULE-018).

## Session-Specific Review Focus

1. **AC2.3 / AC2.4 wire-up at 4 emit sites.** Verify all 4 standalone-SELL emit sites in `argus/execution/order_manager.py` (`_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts` retry-SELL path, `_escalation_update_stop`) are wrapped with:
   - `_is_locate_suppressed(position, time.monotonic())` pre-check (skips SELL emission when suppressed).
   - `_is_locate_rejection(error)` exception handler (sets `_locate_suppressed_until[position.id]` + logs INFO, no SystemAlertEvent at suppression-set time).
   The 6 S3b-path-2 tests (1–5 above + canonical-site test 5) cover the wire-up. Per AC2.3, suppression-set is silent; alerts fire only at AC2.5 timeout-verification (Branches 3 + 4).

2. **AC2.5 three-branch + Branch 4 + HALT-ENTRY coupling correctness (per Tier 3 item C).** Verify:
   - **Branch 1** (broker-zero) clears `_locate_suppressed_until[position.id]`; INFO log; **no alert**.
   - **Branch 2** (expected-long with shares ≥ remaining) clears the dict entry; INFO log; **no alert**.
   - **Branch 3** (unexpected: short OR divergent qty) publishes `phantom_short_retry_blocked` via the **existing DEC-385 emitter** (NOT a new emitter); metadata `{position_id, symbol, broker_side, broker_shares, expected_remaining}`; clears the dict entry.
   - **Branch 4** (refresh-failure) publishes the SAME alert with `verification_stale: True` metadata; does NOT clear the dict entry; **HALT-ENTRY fires ONLY when `_selected_mechanism == "h1_cancel_and_await"`** (per Tier 3 item C — coupled to the H1 mechanism active state). Test 11 (`test_branch_4_throttle_one_per_hour_per_position`) covers the coupling AND the throttle.

3. **Fix A single-flight serialization at `IBKRBroker.refresh_positions()` per Round 3 C-R3-1.** Verify:
   - `_refresh_positions_lock` is `asyncio.Lock`, NOT `threading.Lock`.
   - The post-acquisition re-check inside the `async with` block prevents the lost-update race (coroutine B awaiting the lock while A synchronizes; B should coalesce on A's just-recorded timestamp).
   - `_last_refresh_synchronized_at` is updated AFTER `wait_for` succeeds, NOT before.
   - The 250ms constant lives at module scope as `_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS` (grep-discoverable; verify `grep -n "_REFRESH_POSITIONS_COALESCE_WINDOW_SECONDS" argus/execution/ibkr_broker.py` returns 1 hit).

4. **FAI #10 falsifying spike correctness (per RULE-051 — mechanism signature, not symptom aggregate).** Verify `tests/execution/test_ibkr_broker_concurrent_callers.py::test_concurrent_callers_serialized_by_single_flight_lock`:
   - Spawns N=20 coroutines calling `refresh_positions()` near-simultaneously (≤10ms separation via `asyncio.gather`).
   - Injects a mocked-await delay between A's `reqPositions()` call and the `positionEnd` event firing; deterministically mutates broker state between A's and B's effective synchronization points.
   - **Mode (a) — without mitigation** (monkey-patch the lock to a no-op): asserts at least one caller observes stale-for-this-caller state (race observable).
   - **Mode (b) — with mitigation enabled** (default code path): asserts every caller observes fresh state (race NOT observable).
   - The pair-wise comparison is what falsifies FAI #10; a single-mode test is insufficient.
   - File hard-capped at ≤80 LOC per session-breakdown § Final mitigation.
   - **If the regression test failed, FAI #10 materialization MUST NOT have happened — Sprint Abort Condition #9 fires.**

5. **M-R3-2 Branch 4 throttle (1-hour cooldown per position).** Test 11 must verify:
   - First firing publishes `phantom_short_retry_blocked` with `verification_stale: true`.
   - Second firing within 1-hour window is suppressed at alert layer (logged INFO with `branch_4_throttled: true`).
   - HALT-ENTRY effect persists across both firings.
   - Synthetic clock advance past 1-hour window → third firing publishes alert again.
   Verify `grep -n "_branch4_last_alert_at" argus/execution/order_manager.py` returns ≥3 hits (init, set, clear).

6. **H-R3-3 RiskManager Check 0 extension + halt-clear endpoint (test 9 + test 10).**
   - **Test 9** (`test_risk_manager_check0_rejects_when_halt_entry_set`) must verify per-position granularity per AC2.8: an entry signal for a DIFFERENT `ManagedPosition.id` on the same symbol is NOT rejected. Per-position granularity is the load-bearing property; per-symbol blocking would over-rotate.
   - **Test 10** (`test_clear_halt_endpoint_requires_position_id_and_clears_flag`) must use the `client` fixture from `tests/api/conftest.py`; valid `POST /api/v1/positions/{id}/clear_halt` clears the flag and emits `event="halt_entry_cleared"` log line; invalid returns 404.

7. **H-R3-1 `time.monotonic()` substitution exhaustiveness.** Run a grep for `time.time()` against the diff; flag any remaining call sites in suppression-timeout-related code paths. Verify `grep -nE "time\.time\(\)" argus/execution/order_manager.py` returns zero hits in suppression-timeout-related code paths. The `OrderManagerConfig.locate_suppression_seconds` validator footnote should reference monotonic-time semantics. Test 12 (`test_locate_suppression_resilient_to_wall_clock_skew`) injects a synthetic backwards wall-clock jump and asserts the suppression check is unaffected.

8. **M-R3-4 `_read_positions_post_refresh` helper.** Verify the helper method exists on `OrderManager`; it serves as the AST-no-await scan extension hook for S4a-ii. Regression invariant 30.

9. **FAI #10 materialization in close-out + inventory.** Verify per D15 of `doc-update-checklist.md`:
   - The doc commit happened **AFTER** the implementation commit AND only when `test_concurrent_callers_serialized_by_single_flight_lock` was green.
   - `falsifiable-assumption-inventory.md` preamble updated `## Inventory (9 entries)` → `## Inventory (10 entries)`.
   - The verbatim FAI #10 row from `round-3-disposition.md` § 6.1 was appended to the main inventory table.
   - The pending-FAI-#10 entry was REMOVED from the "Pending FAI extensions committed in `round-3-disposition.md`" subsection (FAI #11 still pending).
   - Status field marked `**falsified — green S3b spike (commit: <SHA>)**` with the cross-reference: `Cross-layer falsification: scheduled in S5c CL-7 (status will flip to falsified at S5c close).`

10. **Construction-surface modification scope.** `argus/main.py` must show ONLY the OrderManager keyword-argument addition (passing `selected_mechanism=...`). Any other `argus/main.py` change is A-class halt **A12**.

11. **`SimulatedBroker.refresh_positions` no-op-only.** Search for any code in `argus/execution/simulated_broker.py` that mutates state in `refresh_positions` — if found, this is the exact behavior SbC §"Out of Scope" #18 prohibits.

12. **`halt_entry_until_operator_ack` field-ownership clarity.** S3b adds the field to `ManagedPosition`; S4a-i references it. Verify the field is added EXACTLY ONCE (S3b OR S4a-i, not both); the close-out should disclose which session owns the addition. If S4a-i has not landed, S3b owns it; if S4a-i lands first via reordering, S3b should reference the existing field.

13. **DEF-158 3-branch side-check verbatim preservation.** Per A-class halt **A5** — the most critical regression check. Inspect the `_check_flatten_pending_timeouts` body line-by-line; verify that:
    - The BUY → resubmit branch is unchanged.
    - The SELL → alert+halt branch is unchanged.
    - The unknown → halt branch is unchanged.
    - The Path #2 NEW detection sits at the `place_order` exception (NOT inside the side-check switch).

## Additional Context

This is the most complex implementation session in the sprint. S3b wires Path #2 detection into 4 emit sites, lands the AC2.5 broker-verified-at-timeout fallback with three branches + Branch 4 (refresh-failure) + HALT-ENTRY coupling under H1 (per Tier 3 item C), introduces Fix A single-flight serialization at `IBKRBroker.refresh_positions()` (per Round 3 C-R3-1 — the operator-override-binding contract), substitutes `time.monotonic()` per H-R3-1, and extends the RiskManager with Check 0 + halt-clear endpoint per H-R3-3.

**Per Sprint Abort Condition #9:** if `test_concurrent_callers_serialized_by_single_flight_lock` returns the race observable WITH the mitigation enabled, the operator override is empirically retracted and Phase A re-entry retroactively reactivates. The pair-wise comparison test IS the binding contract on the Round 3 operator override.

The diff is large and crosses production boundaries (`argus/api/routes/positions.py` halt-clear endpoint + `scripts/clear_position_halt.py` CLI tool); read the close-out's "Files Modified" section carefully and confirm each change against the impl prompt's allowed-edit list.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S3b is ✓-mandatory at S3b for invariants **5, 6, 7, 8, 9, 10, 11, 12, 14, 21, 24, 28, 30, 31, 32, 34** (mostly ESTABLISHES) and ✓ partial for **25**.

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S3b: A-class halts **A4** (DEC-385/386/388 surface modified beyond additive points), **A5** (DEF-158 3-branch side-check modified — the most critical S3b check), **A6** (CONCERNS/ESCALATE verdict), **A12** (`argus/main.py:1081` surfaces touched beyond the keyword-argument addition), **A13** (artifact >30 days at first paper session — operational), **A14** (Round 3 operator override invoked, Fix A spike failure routes to Sprint Abort Condition #9), **A17** (synchronous-update invariant violation — not S3b's primary surface but defensive), **A18** (Branch 4 + H1 active without HALT-ENTRY firing — ESTABLISHES at S3b); B-class halts **B1**, **B3**, **B4**, **B5**, **B6**, **B7** (FAI #10 spike could plausibly add latency; benchmark and decide whether to mock the propagation), **B8**, **B12** (AC2.5 broker-verification-at-timeout fails or returns stale data); C-class halts **C1**, **C5**, **C6**, **C12** (`--allow-rollback` flag verification deferred to S4b — informational at S3b).
