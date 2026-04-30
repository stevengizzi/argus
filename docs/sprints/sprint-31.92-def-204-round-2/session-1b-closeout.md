# Session 1b Close-Out — Sprint 31.92 Phase A Path #2 Spike (Locate-Rejection Fingerprint + Hard-to-Borrow Microcap Window)

```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 31.92 — Session 1b: Phase A diagnostic spike — IBKR locate-rejection fingerprint + hard-to-borrow microcap suppression-window calibration (Path #2)
**Date:** 2026-04-29
**Self-Assessment:** FLAGGED

> **FLAGGED rationale (load-bearing):** The session's CODE deliverable
> (`scripts/spike_def204_round2_path2.py`) is COMPLETE and validated via
> `--dry-run` + helper unit tests + AST parse. The session's EXECUTION
> deliverable (the auto-generated JSON artifact at
> `scripts/spike-results/spike-def204-round2-path2-results.json` with
> `status: PROCEED` AND a non-empty `fingerprint_string`) is **BLOCKED on
> operator action** — paper IBKR Gateway access (account U24619949,
> clientId=2), market-closed timing window, and the operator-curated ≥5
> hard-to-borrow microcap list (PCT-included) are all operator
> pre-conditions per the prompt's Pre-Flight Checks 2 + 7 + 8. This is a
> "FLAGGED" classification under the strict close-out criterion ("spec
> requirement partially met or skipped"), NOT a code quality issue.

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `scripts/spike_def204_round2_path2.py` | added | Phase A spike script per prompt §"Files to Modify" #1; modeled on the Sprint 31.91 precedent at `scripts/spike_ibkr_oca_late_add.py`. |
| `docs/sprints/sprint-31.92-def-204-round-2/session-1b-closeout.md` | added | This file (per close-out skill + prompt §"Close-Out"). |

> **NO production code modified.** `git diff HEAD -- argus/ frontend/ tests/ workflow/` returns 0 lines (verified at session close). All A-class halts (A4, A5) for production-tree modification do not fire. B-class halts B6 (do-not-modify), B8 (frontend) do not fire.
>
> The untracked file `scripts/spike_def204_round2_path1.py` originates from the parallel S1a session and is NOT part of this session's diff scope.

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:

- **Used raw `ib_async` directly rather than instantiating `IBKRBroker`.** The prompt's wording ("Force a SELL emission via direct `IBKRBroker.place_order(SELL, qty=<position_shares>)`") could be read either way; I followed the precedent at `scripts/spike_ibkr_oca_late_add.py` which uses raw `ib_async` (`ib.placeOrder()` + `ib.errorEvent`). Rationale: instantiating `IBKRBroker` requires `EventBus` + `IBKRConfig` wiring and pulls the entire ARGUS abstraction surface in; the spike's intent is "probing the broker exception surface" (per prompt §Requirements #1), which IS the `ib_async` errorEvent surface — `IBKRBroker.place_order()` only forwards what `ib_async` returns. The fingerprint extracted from raw `ib_async` is byte-for-byte identical to what `IBKRBroker.place_order()` would surface via `OrderCancelledEvent.reason` (see `argus/execution/ibkr_broker.py:438-447` — the rejection path stringifies the same `error_string`). No semantic difference; the precedent is the standard.

- **Watchdog cancellation path leaves the position cleanup to `_ensure_flat`.** The prompt specifies "cancel after `case_a_max_age_seconds` configurable window (default 30 seconds)" but does not specify the cleanup mechanism for held SELL orders that age out. I implemented this via the per-trial `finally: await _ensure_flat(ib, contract)` block: cancel any working SELL order on the symbol, then flatten the residual long via a fresh MARKET SELL. This mirrors the precedent's cleanup contract. If `_ensure_flat` itself fails (network blip, API error), the inner `try/except` swallows non-fatal errors — non-disruptive guarantee preserved.

- **Per-trial `TrialResult` rows excluded from the emitted JSON to keep the artifact tight.** The 16 required keys are aggregate-level; per-trial detail (error strings per trial, status histories, etc.) live only in the spike's stdout INFO logs during run-time. Operator-side debugging can be reconstructed from the captured log (see prompt §"Operator Notes"). Rationale: the artifact's required-keys schema in §Requirements #5 explicitly enumerates 16 aggregate keys; adding a per-trial array would expand the schema beyond what S3a/S3b consume.

- **Floor of 18000s applies even when H6 confirms with very short release windows.** When `release_p99_seconds × 1.2 < 18000`, the formula `min(86400, max(18000, p99 × 1.2))` correctly returns 18000. This is per spec (the 18000s floor is non-bypassable per AC2.5). Surfaced in the helper unit test (`H6-confirms: rec_locate=18000` even with p99=20.0s).

- **Fingerprint stability classification.** When all case-B observations contain the canonical `"contract is not available for short sale"` substring (case-insensitive), `fingerprint_string` is set to the canonical candidate and `fingerprint_stable=True`. When observations diverge, the longest common substring across observations is captured and `fingerprint_stable=False` — surfaces to S3a for substring-list broadening per AC2.1 fallback.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Req 1: Create `scripts/spike_def204_round2_path2.py` argparse-driven async script | DONE | `scripts/spike_def204_round2_path2.py` (~480 lines including docstrings; ~150 LOC of executable Python — matches prompt's "~150 LOC" target when docstrings/blanks excluded). Argparse: `--account`, `--client-id` (default 2), `--symbols` (required, must include PCT), `--trials-per-symbol` (default 10), `--output-json` (default `scripts/spike-results/spike-def204-round2-path2-results.json`), `--case-a-max-age-seconds` (default 30), `--dry-run`. `asyncio.run(main_async(args))` entry; serial per-symbol per-trial execution; emits one JSON; exit 0 PROCEED / 1 INCONCLUSIVE. |
| Req 1: Per-trial protocol — BUY long, force SELL, classify case A vs B | DONE | `_run_one_trial()` at `scripts/spike_def204_round2_path2.py:165-225`. BUY 1 share at market → wait for fill (≤10s) → place SELL → poll order status + `ib.errorEvent` capture for `case_a_max_age_seconds` (default 30s). |
| Req 1: Case A vs case B differentiation per FAI #6 / M-R2-1 | DONE | Case B = error within `CASE_B_RAISE_WINDOW_SECONDS` (2.0s) OR terminal status (Cancelled/Inactive) within 2s window. Case A = order pending >2s. Release event = case-A held order that subsequently fills before watchdog cancels. |
| Req 1: Substring fingerprint extraction with canonical-or-LCS fallback | DONE | `_compute_summary()` at `:233-258`. If all case-B strings contain `DEFAULT_FINGERPRINT_CANDIDATE` ("contract is not available for short sale"), use canonical; else compute longest common substring via `_longest_common_substring()` at `:107-122` and set `fingerprint_stable=False`. |
| Req 2: Compute `fingerprint_stable` across trials | DONE | Set True iff all case-B observations contain canonical substring. Helper unit test verified. |
| Req 3: Compute release-window quantiles (p50/p95/p99/max) | DONE | `_compute_summary()` at `:251-256` via `_percentile()` at `:101-104`. Set to None if zero release events. |
| Req 4: Compute `recommended_locate_suppression_seconds` per formula | DONE | `_compute_summary()` at `:253-258`. H6 confirms branch: `min(86400, max(18000, p99×1.2))`. H6 rules-out branch: 18000s with documented rationale. Floor 18000s, ceiling 86400s — matches Pydantic field validator bounds for S3a. |
| Req 5: Emit JSON with 16 REQUIRED keys at `scripts/spike-results/spike-def204-round2-path2-results.json` | DONE (script-side) | `_emit_json()` at `:330-352`. Schema check at write time raises `RuntimeError` if any of the 16 keys missing. **JSON artifact ITSELF cannot be produced in this session** — paper IBKR Gateway connection required; operator-orchestrated. Verified schema via `--dry-run` against `/tmp/spike-test-output.json`: all 16 keys present, no extras. |
| Req 5: Status determination (PROCEED / INCONCLUSIVE) | DONE | `_determine_status()` at `:261-275`. INCONCLUSIVE if PCT unreachable, OR `case_a_count==0 AND case_b_count==0`, OR fingerprint extraction failed when `case_b_count>0`, OR `<5 symbols AND zero case-B`. Otherwise PROCEED. |
| Req 6: Document H6 rules-out path | DONE | This close-out's "Notes for Reviewer" + script's docstring + helper unit test demonstrate H6 rules-out branch (18000s default, documented rationale). |
| Pre-Flight: read context files | DONE | Read `argus/execution/ibkr_broker.py` (focus: `_is_oca_already_filled_error`, `_on_error`, `place_order`); `argus/execution/order_manager.py` (anchors verified); `argus/execution/simulated_broker.py` (extensibility assessed); `docs/debriefs/2026-04-28-paper-session-debrief.md` (PCT trace context); `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` §"Hypothesis Prescription" (H5 + H6 confirms-if/rules-out); precedent `scripts/spike_ibkr_oca_late_add.py` (modeled-after). |
| Pre-Flight: structural-anchor grep-verify | DONE | `_is_oca_already_filled_error` at line 75 of ibkr_broker.py; `_on_error` at 344; `is_order_rejection` at 40, 438. `_check_flatten_pending_timeouts` at 3319, `_trail_flatten` at 3551, `_escalation_update_stop` at 3668, `_flatten_position` at 3751 of order_manager.py. SimulatedBroker class at 76, `place_order` at 197, `get_positions` at 538, `cancel_all_orders` at 629. All anchors resolve. |
| Pre-Flight: branch + Sprint sealing prereqs | DONE WITH NOTE | On `main`. Sprint 31.91 SEAL is at commit `210d2f9` (`docs(sprint-31.91): D14 doc-sync — sprint close-out ...`); Sprint 31.915 close at `f42e25c` (`docs(sprint-31.915): Tier 2 review CLEAR + closeout addendum`). The prompt's verbatim grep `grep -E "Sprint 31\.915\|Sprint 31\.91 SEALED"` returned no matches because seal-commit messages do not literally contain "SEALED" (case-sensitive uppercase) — they are conventional `docs(sprint-31.91): D14 doc-sync — sprint close-out` form. CLAUDE.md confirms both sprints SEALED and the CLAUDE.md narrative is authoritative. **RULE-038 disclosure:** I proceeded against the actual structural state (seal commits exist) rather than halt on the literal grep miss. |
| Pre-Flight: test baseline (DEC-328 — Session 2 of sprint, scoped) | DONE | `python -m pytest tests/execution/ -n auto -q` → 492 passed in 33.39s; 9 warnings (pre-existing, see DEF-192). |
| Final test gate (DEC-328 — full suite at every close-out) | DONE | `python -m pytest --ignore=tests/test_main.py -n auto -q` → 5,279 passed in 64.84s; 36 warnings (pre-existing per DEF-192). Baseline preserved exactly (matches CLAUDE.md's Sprint 31.915 close-out count). |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| `git diff HEAD -- argus/` returns empty | PASS | 0 lines. Spike modifies zero production code. A-class halts A4/A5 do not fire. |
| `git diff HEAD -- frontend/` returns empty | PASS | 0 lines. Invariant 12 + B8. |
| `git diff HEAD -- tests/` returns empty | PASS | 0 lines. Spike adds zero new tests. |
| `git diff HEAD -- workflow/` returns empty | PASS | 0 lines. RULE-018. |
| Pytest count = baseline (5,269 floor / 5,279 actual) | PASS | 5,279 passed (matches Sprint 31.915 close-out exactly per CLAUDE.md). Invariant 10 + B3. |
| Pre-existing flake count unchanged | PASS | 36 warnings (DEF-192 baseline). No new flake categories. Invariant 11 + B1. |
| JSON artifact has all 16 required keys | PASS (via --dry-run) | Validated via `python scripts/spike_def204_round2_path2.py --symbols PCT,ACHR,PDYN,HPK,MX --dry-run --output-json /tmp/spike-test-output.json` — all 16 keys present, no extras, PCT in `symbols_tested`, schema check at `_emit_json` raises if drift. **Live-execution check is operator-orchestrated.** |
| `symbols_tested` contains PCT | PASS (scaffolding) | Script enforces PCT presence at `main_async:299-302`: returns exit code 1 + log error if PCT missing. Live verification operator-side. |
| `recommended_locate_suppression_seconds` in [18000, 86400] | PASS (formula) | Formula `max(18000, min(86400, ...))` is bounded structurally. Helper unit test confirms 18000 floor under H6 rules-out. |
| `status: "PROCEED"` (not INCONCLUSIVE) | OPERATOR-PENDING | Cannot be verified in this session — requires live IBKR execution. **A2 halt firing is a live-spike outcome, not a code-deliverable issue.** |
| Spike artifact dated within last 24 hours | OPERATOR-PENDING | `spike_run_date` is set to ISO 8601 UTC at script-runtime via `_now_utc_iso()` at `:266`. Live-execution gates this check. |
| H6 rules-out documentation | DONE | This close-out's "Notes for Reviewer" + script docstring + helper unit test all surface the 18000s fallback rationale. |
| Vitest count unchanged at 913 | PASS | No frontend changes. Vitest not run (no scope), but invariant 12's by-construction check (zero frontend diff) is sufficient. |

### Test Results
- Tests run: 5,279 (full suite, `--ignore=tests/test_main.py`, `-n auto`)
- Tests passed: 5,279
- Tests failed: 0
- New tests added: 0 (per spec — spike session adds zero pytest tests; the JSON artifact's required-keys list IS the validation surface)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Pre-flight scoped baseline: `python -m pytest tests/execution/ -n auto -q` → 492 passed
- Helper unit checks: `_longest_common_substring`, `_percentile`, `_compute_summary`, `_determine_status` all pass H6-confirms + H6-rules-out branches.

### Unfinished Work
Items from the spec that were not completed, and why:

- **JSON artifact emission against live paper IBKR Gateway.** Cannot be produced in this session — requires (a) paper IBKR Gateway running on port 4002 with account U24619949 and clientId=2 (clientId=1 reserved for parallel S1a); (b) market closed (non-safe-during-trading per Pre-Flight Check 7); (c) operator-curated ≥5 hard-to-borrow microcap list with PCT included (Pre-Flight Check 2). All three conditions require operator action. The script itself is fully implemented + dry-run-validated; the operator's next step is to run it during after-hours and commit the resulting JSON.
- **Definition-of-Done items pending operator execution:**
  - Script runs against paper IBKR Gateway without crashing (operator-side)
  - JSON exists with `status: "PROCEED"` (operator-side)
  - `recommended_locate_suppression_seconds` value materialized (operator-side, gated on actual release-event observations)
  - `symbols_tested` contains PCT live (operator-side)
  - CI green on session's final commit (no commit yet — see "Notes for Reviewer")
  - Tier 2 @reviewer review (deferred — see "Notes for Reviewer")

### Notes for Reviewer

> **Critical handoff context:** This session is FLAGGED because the spike's
> EXECUTION deliverable (JSON with `status: PROCEED`) is **outside the
> implementer's reach**. Specifically:
>
> 1. The Claude Code session has no path to reach a live IBKR Gateway
>    (no paper Gateway running locally during the session window;
>    market hours not aligned with after-hours window in any case).
> 2. The spike is non-safe-during-trading (per prompt §Pre-Flight #7
>    + §Constraints).
> 3. The operator-curated symbol list is an operator pre-task, not a
>    Claude Code task.
>
> Per the close-out skill's strengthened "Do NOT stage, commit, or push
> if FLAGGED" rule, **I am NOT committing this session's diff or
> invoking the @reviewer subagent in this conversation turn.** The
> operator's next step is the operational sequence below.

**Operator next steps (ordered):**

1. **Read this close-out + the script** at `scripts/spike_def204_round2_path2.py`.
2. **Curate the hard-to-borrow microcap list** (≥5 symbols, PCT mandatory). The April 28 paper-session debrief §C9 lists the top-6 Path #2 symbols by share volume (PCT 3,837 / ACHR 402 / PDYN 400 / HPK 313 / MX 297 / NVD 252) — natural starting point. Document the curation rationale before the run.
3. **Verify the parallel S1a session has either completed or coordinated clientId budget** (S1a uses clientId=1; S1b uses clientId=2 by default).
4. **During pre-market or after-hours**, run:
   ```bash
   python scripts/spike_def204_round2_path2.py \
       --account U24619949 --client-id 2 \
       --symbols PCT,ACHR,PDYN,HPK,MX,NVD \
       --trials-per-symbol 10
   ```
5. **Inspect the auto-generated `scripts/spike-results/spike-def204-round2-path2-results.json`.** If `status: "PROCEED"`, commit (script + close-out + JSON) and proceed to Tier 2 review. If `status: "INCONCLUSIVE"`, A-class halt **A2** fires — surface to Tier 3 architectural review per Round-1 M-1 disposition.
6. **Tier 2 @reviewer review** can run AFTER the operator-side execution + commit, against the full diff (script + JSON + close-out).

**Specific spike behaviors to confirm during operator-side execution:**

- **PCT must produce ≥1 case-B observation** (canonical reference). If PCT produces only case-A across all 10 trials, this is meaningful per §Session-Specific Review Focus #4 — it suggests the locate-rejection-as-held-order path (Path #2's defining mechanism) reached us purely as case-A on PCT today, which is operationally informative for AC2.7 watchdog auto-activation.
- **Release-event observations** dictate H6 confirms vs rules-out. Either branch is acceptable per spec; `recommended_locate_suppression_seconds` formula handles both.
- **Schema-drift safety net:** `_emit_json` raises `RuntimeError` if any of the 16 required keys is missing. The script will fail fast rather than silently emit an incomplete JSON.

**Specific code review focus areas:**

- `_longest_common_substring` (`:107-122`) — quadratic complexity but bounded by trial count × string length (small numbers). Verified against 3-string LCS test in helper unit test.
- `_percentile` (`:101-104`) — uses `statistics.quantiles(..., method="inclusive")` which matches the canonical NumPy `percentile` semantics for default `linear` interpolation. Single-element input returns the element verbatim.
- `_run_one_trial` order-status polling loop (`:194-220`) — terminates on case-B (error within 2s window), case-A release (Filled), or watchdog timeout (case-A held). The 1-second buffer (`case_b_window_end + 1.0`) on terminal-status detection is a small grace period to absorb race between status flip and timestamp capture.
- `_ensure_flat` cleanup (`:148-163`) — best-effort; non-fatal exceptions swallowed. The "non-disruptive" guarantee is preserved.

### CI Verification
- CI run URL: NOT YET PUSHED (per FLAGGED gate)
- CI status: PENDING-OPERATOR-COMMIT

### Context State
GREEN — single-file script + close-out, well-bounded scope, no compaction risk.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.92",
  "session": "S1b",
  "verdict": "INCOMPLETE",
  "tests": {
    "before": 5279,
    "after": 5279,
    "new": 0,
    "all_pass": true
  },
  "files_created": [
    "scripts/spike_def204_round2_path2.py",
    "docs/sprints/sprint-31.92-def-204-round-2/session-1b-closeout.md"
  ],
  "files_modified": [],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [
    {
      "description": "JSON artifact at scripts/spike-results/spike-def204-round2-path2-results.json cannot be produced by the implementing session — requires live paper IBKR Gateway connection (account U24619949, clientId=2), market-closed timing, and the operator-curated >=5 hard-to-borrow microcap list (PCT mandatory). All three are operator pre-conditions per the prompt's Pre-Flight Checks 2, 7, and 8.",
      "category": "SUBSTANTIAL_GAP",
      "severity": "MEDIUM",
      "blocks_sessions": ["S3a", "S3b"],
      "suggested_action": "Operator runs scripts/spike_def204_round2_path2.py during after-hours against paper IBKR Gateway with curated symbol list. If the run produces status:PROCEED, commit the JSON + this close-out + the script in one commit; then invoke the @reviewer subagent for Tier 2. If status:INCONCLUSIVE, A-class halt A2 fires per Round-1 M-1 disposition — escalate to Tier 3 architectural review."
    }
  ],
  "prior_session_bugs": [],
  "deferred_observations": [
    "RULE-038 disclosure: prompt's Pre-Flight Check 8 grep `Sprint 31\\.915|Sprint 31\\.91 SEALED` returned no literal matches because seal-commit messages use the conventional 'D14 doc-sync — sprint close-out' phrasing rather than literal 'SEALED'. CLAUDE.md narrative is authoritative; both sprints are sealed at commits 210d2f9 (Sprint 31.91) and f42e25c (Sprint 31.915). Proceeded against actual structural state; flagged here for transparency.",
    "Per-trial detail (TrialResult rows) excluded from JSON to keep artifact tight to the 16 required aggregate keys. If S3a/S3b reviewers want per-trial granularity, the script's stdout INFO log is the source of record at run-time.",
    "Helper-level unit checks (_longest_common_substring, _percentile, _compute_summary, _determine_status) ran inline during development and pass both H6-confirms and H6-rules-out branches. NOT committed as pytest tests per prompt §Test Targets ('zero new tests')."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [
    "FLAGGED self-assessment: code deliverable complete; execution deliverable blocked on operator action. Per close-out skill, no commit/push/Tier-2 invocation in this turn — operator-orchestrated.",
    "Prompt's structural premise assumes the implementing session can run the spike during the same session window. Claude Code cannot reach a live IBKR Gateway; the session's reach ends at the script + dry-run validation."
  ],
  "implementation_notes": "Modeled directly on the Sprint 31.91 precedent at scripts/spike_ibkr_oca_late_add.py. Script uses raw ib_async (not the IBKRBroker abstraction) per the precedent and per the prompt's intent of probing the broker-level exception surface. JSON artifact is auto-generated at script-runtime via _emit_json() with a 16-key schema check that raises if drift. Status determination logic distinguishes (a) zero observations of either case (INCONCLUSIVE — symbols did not trigger locate behavior), (b) fingerprint-extraction failure (INCONCLUSIVE), (c) <5 symbols AND zero case-B (INCONCLUSIVE composite per spec), and (d) all other completed runs (PROCEED). H6 rules-out (zero release events) falls back to recommended_locate_suppression_seconds=18000 with documented rationale; H6 confirms uses min(86400, max(18000, p99 * 1.2)). All 16 required JSON keys present; none extra. Pre-flight test baseline 492/492 passing in tests/execution/; full close-out suite 5279/5279 passing. Zero production code modified."
}
```
