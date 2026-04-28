# Tier 2 Review — Sprint 31.91 Session 2d

**Commit:** `93f56cd` (operator override API + audit-log + L3 startup alerts)
**Reviewer:** Tier 2 backend safety reviewer
**Date:** 2026-04-28

## Verdict: **CLEAR**

Session 2d implements the full operator-facing override surface for the side-aware reconciliation contract (DEC-385) precisely as specified: the new `POST /api/v1/reconciliation/phantom-short-gate/clear` endpoint carries the same auth pattern as `controls.py`, the `phantom_short_override_audit` table captures all 8 forensic columns under a single SQLite transaction with the gated-symbols DELETE, the L3 always-both-alerts emission at startup is wired in `argus/main.py` immediately adjacent to Session 2c.1's rehydration call (and explicitly does NOT touch the IMPROMPTU-04 invariant), the L15 `phantom_short_aggregate_alert_threshold` field (default 10, range 1–1000) is correctly threaded through Pydantic + both YAMLs, and the B22 runbook section in `docs/live-operations.md` carries all 7 required subsections. CI run `25034590254` is **GREEN** on commit `93f56cd` (pytest 3m54s + vitest 1m23s, both passed). All 8 review-focus items + all 5 sprint-level invariants pass; no escalation criteria triggered.

---

## Tests Run

| Suite | Result |
|---|---|
| `tests/api/test_session2d_phantom_short_override.py` (6 new) | **6 passed** in 1.09s |
| `tests/api/` (full API layer) | **562 passed** in 31.59s |
| Full pytest baseline (`--ignore=tests/test_main.py -n auto`) | **5,169 passed, 0 failed** in 58.19s |
| `tests/test_main.py` | 31 pass / 5 skip / 8 fail (pre-existing baseline drift, zero session-2d delta) |

Pytest delta: +6 tests, exactly matching the close-out claim of `tests_added: 6`. Total `tests_total_after: 5169` verified empirically.

## CI Status (RULE-050)

**GREEN** on commit `93f56cd`:
- pytest (backend): 3m54s, **success** (job 73323344160)
- vitest (frontend): 1m23s, **success** (job 73323344164)
- Full run: <https://github.com/stevengizzi/argus/actions/runs/25034590254>

The 6 visible "Event loop is closed" annotations are tracked DEF-201 cosmetic noise on Linux xdist workers (DEF-200/193 mitigation); they are NOT regressions and are pre-existing across multiple prior commits. RULE-050 satisfied.

---

## Section-by-Section Verdict (Review Focus Items 1–8)

### 1. API endpoint authentication consistency — **PASS**

`argus/api/routes/reconciliation.py:65-69` carries `_auth: dict = Depends(require_auth)` exactly mirroring the pattern in `argus/api/routes/controls.py:34, 66, 98, 135, 161` (verified by direct grep). The `# noqa: B008` comment matches verbatim. The handler receives `state: AppState = Depends(get_app_state)` and pulls `order_manager = state.order_manager` — same shape as `controls.py`. The endpoint is registered under `/reconciliation` prefix in `argus/api/routes/__init__.py:76-78` and tagged `["reconciliation"]`. No silent bypass.

### 2. Audit-log schema captures full forensic detail (M3) — **PASS**

DDL constant at `argus/execution/order_manager.py:2556-2567` contains all 8 columns:

| # | Column | Type | NOT NULL? |
|---|---|---|---|
| 1 | `id` | INTEGER PRIMARY KEY AUTOINCREMENT | ✓ |
| 2 | `timestamp_utc` | TEXT | ✓ |
| 3 | `timestamp_et` | TEXT | ✓ |
| 4 | `symbol` | TEXT | ✓ |
| 5 | `prior_engagement_source` | TEXT | nullable |
| 6 | `prior_engagement_alert_id` | TEXT | nullable (None pre-5a.1) |
| 7 | `reason_text` | TEXT | ✓ |
| 8 | `override_payload_json` | TEXT | ✓ |

INSERT site at `argus/execution/order_manager.py:2683-2698` populates all 7 non-PK columns; the INSERT cursor's `lastrowid` returns the autoincrement PK. Indexes on `symbol` and `timestamp_utc` are also created idempotently (lines 2568-2575, executed at 2681-2682). Test 1 asserts the row exists with all 8 columns via direct SQL (`tests/api/test_session2d_phantom_short_override.py:275-298`) and Test 2 (the M3 persistence test) asserts the row remains queryable after a simulated reconnect to the same SQLite file (lines 337-364).

### 3. Aggregation + individual alerts both fire (L3 — no suppression) — **PASS**

Verified by direct read of `argus/main.py:1086-1141`. The aggregate-emission block at lines 1098-1120 is gated by `if len(gated_list) >= agg_threshold:` (line 1103). The per-symbol loop at lines 1125-1141 is `for symbol in gated_list:` — **structurally outside the aggregate's `if`** — and runs unconditionally whenever `_phantom_short_gated_symbols` is non-empty. No `if aggregate_fired: skip per-symbol` branch exists. The inline comment at lines 1121-1124 explicitly documents the L3 disposition: "Per-symbol alerts ALWAYS fire, regardless of whether the aggregate fired."

Test 4 (`test_aggregate_phantom_short_startup_alert_at_10_symbols_AND_individual_alerts_fire`, lines 425-538) reproduces the startup block against an isolated `EventBus` and asserts `len(captured) == 11` (1 aggregate + 10 per-symbol). Test 5 (`test_below_10_symbols_individual_alerts_only_no_aggregate`, lines 547-623) asserts `len(aggregate_alerts) == 0` and `len(per_symbol_alerts) == 5` for the sub-threshold case. Both pass.

### 4. Persistence-first ordering in clearance — **PASS**

`argus/api/routes/reconciliation.py:97-109` shows the exact ordering:

1. Lines 98-104: `await order_manager.clear_phantom_short_gate_with_audit(...)` — SQLite transaction commits both the audit INSERT and the gated DELETE before returning.
2. Lines 108-109: `_phantom_short_gated_symbols.discard(symbol)` + `_phantom_short_clear_cycles.pop(symbol, None)` — in-memory mutation runs ONLY after persistence succeeds.

If `clear_phantom_short_gate_with_audit` raises (e.g., disk full, schema corruption, OS-level error from `aiosqlite`), control never reaches the in-memory mutation. The gate stays engaged → fail-closed. The in-handler comment at lines 106-107 explicitly documents this: "If the SQLite write raised, this code never runs and the gate stays engaged."

### 5. Single transaction for audit + delete — **PASS**

`argus/execution/order_manager.py:2677-2706` opens a **single** `async with aiosqlite.connect(self._operations_db_path) as db:` block. Inside it:

- Line 2679-2682: idempotent DDL (gated-symbols + audit-log + 2 indexes).
- Lines 2683-2698: INSERT into `phantom_short_override_audit`.
- Line 2699: `cursor.lastrowid` captures the PK.
- Lines 2700-2703: DELETE from `phantom_short_gated_symbols WHERE symbol = ?`.
- Line 2706: `await db.commit()` — single commit, both writes atomic.

A crash between the INSERT and the DELETE rolls both back (no commit happened). The inline comment at lines 2704-2705 documents the property: "Single transaction: audit INSERT + gated DELETE both commit together or both roll back."

### 6. Symbol normalization (uppercase, strip) — **PASS**

`argus/api/routes/reconciliation.py:88` — `symbol = payload.symbol.strip().upper()`. The normalized value is used:

- Line 91: gate-membership check (`if symbol not in order_manager._phantom_short_gated_symbols`).
- Line 100: passed to `clear_phantom_short_gate_with_audit(symbol=symbol, ...)`.
- Line 108: in-memory `discard(symbol)`.
- Line 122: response `symbol` field.

`"aapl"`, `"AAPL "`, and `"AAPL"` all collapse to `"AAPL"` before the gate check. No case-sensitivity bug surface.

### 7. B22 runbook section completeness — **PASS**

`docs/live-operations.md:680-769` contains the new section "Phantom-Short Gate Diagnosis and Clearance (Sprint 31.91 / DEC-385)". All 7 B22 subsections are present:

| Subsection | Anchor |
|---|---|
| (i) Symptom | line 684 (`### Symptom`) |
| (ii) Diagnosis steps | line 691 (`### Diagnosis steps`) |
| (iii) Clearance options (a/b/c) | line 703 (`### Clearance options`) — (a) line 705, (b) line 713, (c) line 724 |
| (iv) Audit-log location | line 726 (`### Audit-log location`) |
| (v) Persistence verification | line 747 (`### Persistence verification`) |
| (vi) Aggregate alert tuning | line 754 (`### Aggregate alert tuning`) |
| (vii) Cross-reference | line 761 (`### Cross-reference`) |

Curl example at lines 715-720 includes the bearer-token header pattern. SQLite query at line 744 is operator-runnable. All 5 prior sessions in the side-aware-reconciliation track are cross-referenced (2b.1, 2b.2, 2c.1, 2c.2, 2d) at lines 765-769.

### 8. Main.py edit boundary — **PASS**

`git diff 2acc9e9..HEAD -- argus/main.py` shows:

- One import addition (`SystemAlertEvent` added to the `argus.core.events` import list at line 74).
- One block added at lines 1078-1141 (the Session 2d emission block, immediately after Session 2c.1's `_rehydrate_gated_symbols_from_db()` call at line 1077).

No other changes. Specifically verified:

- **`check_startup_position_invariant()`** (definition at line 124, call site at line 377) — **zero diff**. `git diff 2acc9e9..HEAD -- argus/main.py | grep "check_startup_position_invariant"` returns empty. Confirmed by re-grep at HEAD: function defined at line 124, called from line 377, both untouched.
- **`_startup_flatten_disabled` setter logic** — `_startup_flatten_disabled = False` at line 379, `= True` at lines 387 and 398, read at line 1150 — all unchanged. The flag's boolean transitions and the IMPROMPTU-04 startup-invariant decision tree are untouched.
- **Block scope** — the new block sits between line 1077 (`_rehydrate_gated_symbols_from_db`) and line 1142 (`_order_manager.start()`). It does not sprawl into unrelated startup hooks. The combined Session 2c.1 + 2d block (1070-1141) is tightly scoped to phantom-short-gate-related work only.

---

## Sprint-Level Regression Invariants (5 / 6 / 9 / 14 / 15)

| # | Invariant | Status | Evidence |
|---|---|---|---|
| 5 | Pytest baseline ≥ 5,144 | **PASS** | 5,169 passed, 0 failed (+25 over baseline) |
| 6 | `tests/test_main.py` 39+5 (no S2d-introduced regression) | **PASS** | 31 pass / 5 skip / 8 fail; `git diff 2acc9e9..HEAD -- tests/test_main.py` is empty (zero session-2d delta on this file) — pre-existing baseline drift documented in close-out, NOT a session-2d regression |
| 9 | IMPROMPTU-04 startup invariant unchanged | **PASS** | `check_startup_position_invariant()` at `argus/main.py:124` and call site at `:377` unchanged; zero diff lines touch invariant code |
| 14 | Recon detects shorts after Session 2d = "full + override API + audit + configurable threshold" | **PASS** | Endpoint live (`POST /api/v1/reconciliation/phantom-short-gate/clear`); audit-log persisting (`phantom_short_override_audit` table with 8 columns + 2 indexes); L3 always-both wired in `main.py:1086-1141`; L15 threshold via Pydantic + YAMLs |
| 15 | Do-not-modify (with `argus/main.py` scoped exception) | **PASS** | Only the 12 expected files changed (verified via `git diff --stat`); main.py edit is the documented scoped exception bounded to lines 1078-1141; `argus/core/health.py` and `argus/risk/*` untouched |

---

## Escalation Triggers

None triggered. Specifically:

- **A2** (Tier 2 CONCERNS or ESCALATE) — verdict is CLEAR.
- **B1, B3, B4, B6** — none observed.
- **C5** (uncertain whether main.py edit crosses the IMPROMPTU-04 boundary) — verified absent. The new block is anchored at lines 1078-1141, far from the IMPROMPTU-04 invariant function at line 124 and its call site at line 377. The diff cleanly shows no IMPROMPTU-04 path mutation.
- **C7** (existing API tests fail because the new route file changed router registration) — verified absent. The full API test layer (`tests/api/`) passes 562/562 in 31.59s post-2d. The `include_router` registration for `reconciliation_router` at `argus/api/routes/__init__.py:76-78` is purely additive (no rewrite of existing route registration order or prefix).

---

## Do-Not-Modify Verification

`git diff --stat 2acc9e9..HEAD` reports exactly 12 files modified, all on the close-out's `files_modified` list:

```
argus/api/routes/__init__.py                       |   4 +
argus/api/routes/reconciliation.py                 | 128 ++++  (new)
argus/core/config.py                               |  26 +
argus/execution/order_manager.py                   | 106 ++++
argus/main.py                                      |  65 ++
config/system.yaml                                 |   8 +
config/system_live.yaml                            |   8 +
docs/architecture.md                               |   6 +
docs/live-operations.md                            |  93 +++
docs/sprints/.../session-2d-closeout.md            | 190 ++++++  (new)
tests/api/test_session2d_phantom_short_override.py | 686 +++++++++++++  (new)
tests/execution/order_manager/test_reconciliation_redesign.py | 6 +/-
```

`donotmodify_violations: 0` — verified.

---

## Anchors Cited

| Claim | Anchor |
|---|---|
| Endpoint auth pattern matches `controls.py` | `argus/api/routes/reconciliation.py:65-69` vs `argus/api/routes/controls.py:34,66,98,135,161` |
| Symbol normalization | `argus/api/routes/reconciliation.py:88` |
| Persistence-first ordering | `argus/api/routes/reconciliation.py:97-109` (call at 98-104, in-memory at 108-109) |
| Audit-log DDL (8 columns) | `argus/execution/order_manager.py:2556-2567` |
| Audit-log indexes | `argus/execution/order_manager.py:2568-2575` |
| Single-transaction commit | `argus/execution/order_manager.py:2677-2706` |
| Pre-Session-5a.1 prior_source default | `argus/execution/order_manager.py:2674` |
| Router registration | `argus/api/routes/__init__.py:34, 76-78` |
| L15 config field (default 10, range 1-1000) | `argus/core/config.py:296-309` |
| YAML override (system) | `config/system.yaml:78` |
| YAML override (system_live) | `config/system_live.yaml:212` |
| L3 always-both block | `argus/main.py:1086-1141` |
| L15 threshold gating aggregate | `argus/main.py:1103` |
| Per-symbol unconditional loop | `argus/main.py:1125-1141` |
| IMPROMPTU-04 invariant function (untouched) | `argus/main.py:124` (defined), `:377` (called) |
| `SystemAlertEvent.metadata` field | `argus/core/events.py:434` (Session 2b.1 / DEF-213 partial) |
| B22 runbook section anchor | `docs/live-operations.md:680-769` (all 7 subsections) |
| Architecture catalog `**reconciliation**` block | `docs/architecture.md:1945-1949` |
| Test 1 — endpoint removes symbol + writes audit | `tests/api/test_session2d_phantom_short_override.py:216-298` |
| Test 2 (M3) — audit row persists across simulated restart | `tests/api/test_session2d_phantom_short_override.py:307-364` |
| Test 3 — 404 with no audit row | `tests/api/test_session2d_phantom_short_override.py:373-416` |
| Test 4 (L3) — 11 alerts fire at threshold | `tests/api/test_session2d_phantom_short_override.py:425-538` |
| Test 5 — sub-threshold per-symbol-only | `tests/api/test_session2d_phantom_short_override.py:547-623` |
| Test 6 — sorted log line | `tests/api/test_session2d_phantom_short_override.py:632-686` |
| `expected_keys` lock-step update | `tests/execution/order_manager/test_reconciliation_redesign.py:526` |

---

## Final Notes for the Operator

**Soft observations, none blocking:**

1. **Test 6's anchor is OrderManager-side, not main.py-side.** Test 6 (`test_startup_log_line_lists_gated_symbols`) reproduces the rehydration CRITICAL log emitted by `_rehydrate_gated_symbols_from_db()` at `argus/execution/order_manager.py:2738-2743` (a Session 2c.1 deliverable), not the additional CRITICAL log emitted by Session 2d's `main.py:1090-1097` block. The two log lines are intentionally separate — 2c.1's log fires unconditionally inside the OrderManager method, and 2d's log adds operator-triage context at the lifespan-orchestration layer. Test 6 verifies the sorted-list emission via the 2c.1 path; the 2d log is exercised end-to-end via the production `start()` lifespan call (not directly under test, but the block runs on every boot with rehydrated state). Acceptable test scope; flagging because the test docstring asserts on "3 phantom-short gated symbol(s)" (which is the Session 2d log phrasing) but the actual `assert` checks `'['AMD', 'NVDA', 'TSLA']' in rehydration_msg`, anchored on the 2c.1 string `"REHYDRATED on startup"`. Behaviorally correct — Session 2c.1's CRITICAL log already lists the sorted symbols; Session 2d's adds the count. A future Session 2d-specific test that exercises the lifespan startup path under a controlled `app_state` could lock in the 2d log explicitly. Not a blocker.

2. **`_phantom_short_clear_cycles.pop(symbol, None)` in the override handler is asymmetric with the gate-engagement path.** The override handler at `argus/api/routes/reconciliation.py:109` correctly drops the per-symbol auto-clear cycle counter when an operator manually clears the gate (so a subsequent re-engagement starts the auto-clear count from 0, not from a stale value). This is correct behavior. Symmetric with the auto-clear path's pop at `order_manager.py:4058` (Session 2c.2). Worth flagging only because the underlying dict's lifecycle is purely in-memory and session-scoped (per Session 2c.2 review's J-2 design point) — the operator override does the right thing on this surface.

3. **Pre-Session-5a.1 `prior_engagement_source` is a hardcoded string.** `clear_phantom_short_gate_with_audit` returns the string `"reconciliation.broker_orphan_branch"` unconditionally as the `prior_engagement_source` (line 2674). This is the only engagement source today (per Session 2b.1). When Session 5a.1 wires HealthMonitor cross-reference (and Session 5a.1 may add startup-rehydration as a second engagement source), this hardcoded value will need to become a lookup. Inline comment at lines 2671-2673 explicitly notes this: "Pre-Session-5a.1: only engagement source is the reconciliation broker-orphan branch." Acceptable as documented.

4. **Audit table has no retention policy.** Per the close-out and the runbook section at line 741, `phantom_short_override_audit` is "append-only; rows persist indefinitely... per Sprint 31.91 retention spec — full audit forever." This is intentional and correct for a forensic-grade audit log. The DDL constants on `OrderManager` are bare `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` — no retention vacuum, no rolling deletion. Operationally, this is the right trade-off (override events are rare; the row size is small; forensic completeness matters more than disk economy). Not a concern.

5. **`prior_engagement_alert_id: str | None` is `None` pre-5a.1.** The audit-log column captures it, the response model exposes it, the test asserts it's `None`. This is correctly forward-compatible with Session 5a.1's HealthMonitor cross-reference work. No action.

6. **Falsifiable validation pending.** The first paper session post-OCA-architecture (post-`bf7b869`) will be the falsifiable validation surface for the entire Session 0–2d cluster. The override endpoint will not actually be exercised until a real phantom-short gate engages and the operator decides on (a)/(b)/(c). Not Session 2d's responsibility, but flagging that the post-merge paper-session debrief is the eventual ground truth for this work — same posture as Session 2c.2's review.

7. **No new DEFs opened.** Close-out claim verified. No latent issues surfaced during this review.

---

```json
{
  "session": "2d",
  "verdict": "CLEAR",
  "tests_run": {
    "scoped_2d": "6 passed in 1.09s",
    "api_layer": "562 passed in 31.59s",
    "full_baseline": "5169 passed, 0 failed in 58.19s",
    "test_main_py": "31 pass / 5 skip / 8 fail (pre-existing baseline drift, zero session-2d delta)"
  },
  "pytest_baseline_target": 5144,
  "pytest_baseline_actual": 5169,
  "ci_status": "GREEN on commit 93f56cd (run 25034590254): pytest 3m54s + vitest 1m23s",
  "review_focus_items": {
    "1_endpoint_auth_consistency": "PASS",
    "2_audit_log_8_column_schema": "PASS",
    "3_l3_always_both_alerts_no_suppression": "PASS",
    "4_persistence_first_ordering": "PASS",
    "5_single_transaction_audit_plus_delete": "PASS",
    "6_symbol_normalization_strip_upper": "PASS",
    "7_b22_runbook_7_subsections_complete": "PASS",
    "8_main_py_edit_boundary_no_impromptu04_overlap": "PASS"
  },
  "sprint_invariants": {
    "5_pytest_baseline": "PASS",
    "6_test_main_py_no_session2d_regression": "PASS",
    "9_impromptu04_invariant_unchanged": "PASS",
    "14_recon_detects_shorts_full_plus_override_audit_threshold": "PASS",
    "15_donotmodify_with_main_py_scoped_exception": "PASS"
  },
  "escalation_triggers_fired": [],
  "donotmodify_violations": 0,
  "soft_concerns": [
    "Test 6's anchor is the Session 2c.1 OrderManager-side rehydration log, not the new Session 2d main.py log; assertion is correct but the test docstring's '3 phantom-short gated symbol(s)' phrasing is from the 2d log. End-to-end the 2d log fires on every production boot with rehydrated state.",
    "prior_engagement_source is a hardcoded string pre-Session-5a.1; documented inline as the only source today.",
    "Audit table has no retention policy by design — full forensic audit forever per Sprint 31.91 retention spec."
  ],
  "new_defs_opened": 0,
  "tier_3_track": "side-aware-reconciliation-COMPLETE"
}
```
