---BEGIN-REVIEW---

# Tier 2 Review — IMPROMPTU-CI (observatory WS teardown race triage)

**Commits reviewed:** `a50ac8d` (production fix + 2 regression tests) → `4cccf90` (final docs), full range `f97e255..4cccf90`
**Baseline HEAD:** `f97e255` (Phase 2 campaign-close kickoffs)
**Date:** 2026-04-23
**Profile:** STANDARD (diagnostic + test-infra patch; not safety-critical per kickoff)
**Verdict:** **CLEAR**

## Executive Summary

The disconnect-watcher production fix at `argus/api/websocket/observatory_ws.py:116-148` matches the
kickoff's candidate-(a) prescription exactly: `asyncio.Event` sentinel + `_watch_disconnect()` task
that awaits `websocket.receive()` + `asyncio.wait_for(_disconnect_event.wait(), timeout=interval_s)`
racing the interval + watcher cancel-and-drain in `finally`. All 4 structural markers from §What-to-verify
item 2 are wired correctly (lines 52, 126, 128-136, 138, 141-148, 251-256).

Two regression tests land: a grep-guard with 5 assertions (all matching live fix markers, revert-proof on
every platform) and a behavioral timing test (revert-proof on Linux/xdist only — macOS TestClient cancels
cleanly pre-fix; this is honestly documented). Net pytest delta is exactly +2.

Three CI runs on the final fix commits (`4c805c6` / `ec98a5b` / `b6e569b`) are independently verified
green via `gh run view`. The pre-session baseline `2290401` is verified red. The 3× flake threshold is met.

DEF-200 is newly added to CLAUDE.md and strikethrough-closed in the same session. DEF-193 is converted
from open → strikethrough-closed with the same-commit same-signature identity proof documented in the
close-out's §Scope Expansion. The bundling decision is properly authorized by the kickoff's Constraint-4
proven-identical-root-cause clause.

IMPROMPTU-04's review carries a verdict addendum upgrading CONCERNS → CLEAR, with a `verdict_history` array
and `verdict_original: "CONCERNS"` preserved in the structured JSON.

Scope boundaries are clean. The session's three deviations (DEF-193 bundling, test-side tactical mitigation
after round-1 flakes, behavioral test's own pre-disconnect guard in round 2) are explicitly documented.

## Session-Specific Checks

### 1. Diagnosis credibility

The close-out's §Diagnosis rules out **3 of the 4** candidates from the kickoff with actual evidence,
not just assertion (kickoff required ≥ 2):

| Candidate | Disposition | Evidence |
|---|---|---|
| (a) teardown race on sleep | **CONFIRMED** | Baseline CI run `24848146684` shows both `test_observatory_ws_sends_initial_state` (gw1) AND `test_observatory_ws_independent_from_ai_ws` (gw4) crashing with identical `aiosqlite/core.py:66 → _connection_worker_thread → call_soon_threadsafe → RuntimeError: Event loop is closed` stacktrace. This is the exact fingerprint of a server task still parked in an `asyncio.sleep` when the event loop closes. |
| (b) initial `send_json` flush race | **RULED OUT** | Both failing tests successfully received `auth_success` + initial `pipeline_update` before crashing. If the flush was the race, the initial send would never arrive. Evidence is in the failure logs themselves. |
| (c) DB init race | **RULED OUT** | Tests that pass on the same CI run (`test_observatory_ws_pipeline_update_format`, `test_observatory_ws_tier_transition_detected`) all share the same `_build_observatory_app` DB init path. Init race would affect ≥ half the file uniformly; observed behavior affects only the 2 tests that exit `with` block earliest. |
| (d) xdist starvation | **RULED OUT as root cause** | Starvation amplifies timing sensitivity but does not produce the specific aiosqlite thread stacktrace. FIX-13a-CI-hotfix already tried the "tighten the margin" symptom mitigation with `ws_update_interval_ms=200` and was insufficient for `sends_initial_state` — empirical evidence the root cause is mechanism-level, not timing-budget-level. |

Candidate (a) is supported by both the stacktrace fingerprint AND the DEF-193 prose in CLAUDE.md (pre-existing,
authored by FIX-13a-CI-hotfix) which independently names the fix: "wrap push loop in `asyncio.wait_for(websocket.receive(), timeout=interval)`".
Cross-source corroboration is strong.

**Credible diagnosis.** ✓

### 2. Fix actually fixes

Verified all 4 structural markers from §What-to-verify item 2 at `argus/api/websocket/observatory_ws.py`:

| Marker | Line(s) | Present? |
|---|---|---|
| (a) `_disconnect_event = asyncio.Event()` | 126 | ✓ |
| (b) `_watch_disconnect()` helper awaits `websocket.receive()` | 128-136 (helper definition); `await websocket.receive()` at line 130 | ✓ |
| (c) Push loop races event via `asyncio.wait_for(_disconnect_event.wait(), timeout=interval_s)` | 141-148 — exact idiom including the `except asyncio.TimeoutError: pass` fallthrough | ✓ |
| (d) Watcher task cancelled + drained in `finally` | 251-256 — `_watcher_task.cancel()` + `await _watcher_task` inside `try/except (CancelledError, Exception)` | ✓ |

One additional implementation detail worth noting: `_watcher_task: asyncio.Task[None] | None = None`
init at line 52 **before** the outer `try` block sidesteps the `UnboundLocalError` risk that would
otherwise trigger if auth fails before the watcher is created — the `finally` block's `if _watcher_task is not None`
check is a clean no-op in that case. This is called out in the close-out §Fix Rationale and is correct.

**Fix matches the kickoff's candidate-(a) prescription exactly.** ✓

### 3. Revert-proof regression tests

Two tests added at `tests/api/test_observatory_ws.py` after `test_observatory_ws_graceful_disconnect`:

**(a) `test_observatory_ws_has_disconnect_watcher_sentinel`** (grep-guard, lines 624-682): 5 assertions,
each checked against the live source. I verified each marker is present in the current `observatory_ws.py`:

| Assertion | Lives at | Match |
|---|---|---|
| `"_disconnect_event = asyncio.Event()" in source` | line 126 | ✓ |
| `"_watch_disconnect" in source` | line 128 (helper def) | ✓ |
| `"await websocket.receive()" in source` | line 130 (inside helper) | ✓ |
| `"asyncio.wait_for(" in source` | line 143 | ✓ |
| `"_disconnect_event.wait()" in source` | line 144 | ✓ |

If the fix were reverted to `while True: await asyncio.sleep(interval_s)`, all 5 assertions would fail
simultaneously with clear error messages. Revert-proof on every platform (no timing dependence). The
close-out claims this was stash-and-run verified during the session, which matches what I would expect
a careful implementer to do.

**(b) `test_observatory_ws_disconnect_cancels_push_loop_promptly`** (behavioral, lines 541-621):
5-second push interval via `ws_update_interval_ms=5000`. The test exits the `with` block and asserts
`_active_connections` drains within 2 seconds. Pre-fix, the server task would be parked in
`asyncio.sleep(5.0)` for the full 5s (or crash the worker on Linux xdist). Post-fix, the disconnect
sentinel fires on close-frame receipt and the loop exits in milliseconds.

Revert-proof property limited to Linux/xdist (macOS's starlette TestClient cancels cleanly even without
the watcher) — honestly documented in the test's docstring and in the close-out §Notes for Reviewer.
The grep-guard companion covers the universal case.

**Both tests are revert-proof where claimed; the limitations are honestly documented.** ✓

### 4. 3-consecutive-greens threshold met

Verified via `gh run view` against the close-out's §CI Attestation claim:

| Run ID | Commit | Title | Conclusion |
|---|---|---|---|
| `24848146684` | `2290401` | IMPROMPTU-04 Tier 2 review (baseline) | **failure** (pre-session RED confirmed) |
| `24851067204` | `4c805c6` | apply cross-loop aiosqlite guard to all initial-only tests | **success** |
| `24851072630` | `ec98a5b` | retrigger round 4 run 2 | **success** |
| `24851073257` | `b6e569b` | retrigger round 4 run 3 | **success** |

**3 consecutive greens attained on commits `4c805c6` / `ec98a5b` / `b6e569b`.** The flake threshold is
met. The final docs-only commit `4cccf90`'s CI run (`24851365895`) is in-progress at review time — this
is acceptable because the 3× greens are on the actual fix commits, and `4cccf90` touches only docs.

The close-out's honest narration of rounds 1–4 (each round's specific fail mode + the targeted mitigation
applied in the next commit) is a strong signal of careful iteration rather than stochastic retry. Round 2's
flake on the behavioral test's own race, and round 3's flake on `pipeline_update_format` still tripping the
post-initial prep queries at 10s interval, are the kind of discoveries a mitigation-first approach would
reveal. ✓

### 5. DEF-200 + DEF-193 disposition

**DEF-200** is newly added to CLAUDE.md's DEF table AND strikethrough-closed in the same commit. The entry
cites the IMPROMPTU-CI commit range, explains the mechanism (aiosqlite cross-loop callback → worker crash),
names the fix location (`argus/api/websocket/observatory_ws.py:116-148`), and lists both regression guards.

**DEF-193** is converted from open → strikethrough-closed. The entry cites the same IMPROMPTU-CI session
and the same fix location; the shared root cause is justified in the close-out's §Scope Expansion via
the same-commit same-signature CI evidence (both tests crashed their xdist worker on run `24848146684`
with identical aiosqlite stacktrace). The kickoff's Constraint-4 explicitly permits bundling when
root cause is proven identical.

**CAMPAIGN-COMPLETENESS-TRACKER.md** properly:
- Adds Stage 8.5 row for IMPROMPTU-CI (✅ CLEAR)
- Adds DEF-200 + DEF-193 rows to "already resolved during campaign"
- Strikethroughs DEF-193 in the post-31.9 Component Ownership named-horizon block with annotation
  `[closed IMPROMPTU-CI]` — satisfying the "DEF-193 removed from post-31.9 horizon" escalation check.

**Both DEFs have clear, commit-SHA-anchored dispositions.** ✓

### 6. IMPROMPTU-04 verdict addendum

Present at `docs/sprints/sprint-31.9/IMPROMPTU-04-review.md` lines 191-200 (textual addendum) and
lines 204-264 (structured JSON). Verified:

- JSON `verdict: "CLEAR"` ✓
- JSON `verdict_history: [{"...": "CONCERNS", ...}, {"...": "CLEAR", ...}]` with two entries ✓
- JSON `verdict_original: "CONCERNS"` preserved ✓
- Textual addendum explicitly resolves both concerns (commits_not_pushed + ci_green_url_missing) with
  reference to IMPROMPTU-CI commit `b6e569b` and the 3 CI run IDs ✓
- `paper_trading_readiness` updated from `CONDITIONAL_GO_PENDING_PUSH_AND_CI` → `GO` in the textual
  section (the JSON field at line 261 still reads the pre-upgrade value, but the textual prose supersedes
  and this is a minor cosmetic drift — not grounds for ESCALATE) ✓

**Addendum present and properly structured.** ✓ (minor note below in Concerns)

### 7. No scope boundary violation

`git diff f97e255..4cccf90 --name-only`:

```
CLAUDE.md
argus/api/websocket/observatory_ws.py           ← ONLY runtime file
docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md
docs/sprints/sprint-31.9/IMPROMPTU-04-review.md  ← verdict addendum (explicitly authorized by kickoff)
docs/sprints/sprint-31.9/IMPROMPTU-CI-closeout.md  ← this session's close-out
docs/sprints/sprint-31.9/RUNNING-REGISTER.md
tests/api/test_observatory_ws.py                ← ONLY test file
```

- No `argus/` file outside `observatory_ws.py` ✓
- No `tests/api/` file outside `test_observatory_ws.py` ✓
- No `workflow/` submodule changes ✓
- No `config/*.yaml` changes ✓
- No audit-2026-04-21 back-annotation doc touched ✓ (verified via `| grep -i audit` returning empty)

**Scope boundaries clean.** ✓

### 8. Test suite delta

Verified via `git diff f97e255..4cccf90 -- tests/api/test_observatory_ws.py | grep -E "^\+(async )?def test_"`:

```
+async def test_observatory_ws_disconnect_cancels_push_loop_promptly(
+def test_observatory_ws_has_disconnect_watcher_sentinel() -> None:
```

Exactly 2 new test functions. No test files outside `test_observatory_ws.py` were modified. No tests
removed. Net delta +2 matches the close-out's 5,052 → 5,054 claim.

Local confirmation: `python -m pytest tests/api/test_observatory_ws.py -n 4 -q` → **14 passed in 5.10s**
(12 pre-existing + 2 new). No regressions in the file itself.

**Test delta matches claim exactly.** ✓

### 9. Three scope deviations honestly documented

All three deviations from the close-out's §Self-Assessment `MINOR_DEVIATIONS` rationale are explicitly
documented, not swept under the rug:

| Deviation | Location in close-out | Honesty rating |
|---|---|---|
| **D1 — DEF-193 bundled with DEF-200** | §Scope Expansion (full section + "Proven-identical disposition" sub-header); §Scope Verification table row; §Notes for Reviewer bullet 2 | HIGH — the kickoff's Constraint-4 clause is named verbatim, and the identity proof (same CI run, same commit, same stacktrace fingerprint, adjacent tests) is specific and verifiable |
| **D2 — test-side tactical mitigation** | §CI Attestation rounds 1–4 narrative table; Change Manifest row for `test_observatory_ws.py`; §Unfinished Work bullet 1 | HIGH — each round's specific fail mode and the mitigation applied is traced. Close-out explicitly flags the `ws_update_interval_ms=10000` bump on 3 initial-only tests as a test-infrastructure band-aid (not a production-code fix) and gives the proper DEF-worthy follow-on scope (aiosqlite per-loop connection refactor) as a post-31.9 Component Ownership hygiene item |
| **D3 — behavioral test's own pre-disconnect guard** | §CI Attestation round 2 row (`c3c1f9c` observation: "my new behavioral test itself occasionally tripped the cross-loop aiosqlite race; sleep lets server finish post-initial prep queries before disconnect"); test comment at lines 583-592 of `test_observatory_ws.py`; §Notes for Reviewer | HIGH — the reasoning is explicit about what the guard does and does NOT mask (it ensures the disconnect-watcher is the only thing under test, rather than racing the fixture's post-initial prep queries) |

**All three deviations are documented with specificity.** ✓

## Concerns (non-escalating)

1. **IMPROMPTU-04 review JSON `paper_trading_readiness` field staleness.** The textual addendum at line
   200 correctly upgrades `CONDITIONAL_GO_PENDING_PUSH_AND_CI → GO`, but the JSON field at line 261 still
   reads the pre-upgrade value. The textual prose supersedes for operator clarity; the JSON field is a
   minor machine-readable drift that could be resolved in a future doc-sync pass. Not grounds for ESCALATE
   and not worth a commit on its own.

2. **4cccf90 docs-only commit CI run still in-progress at review time.** Run `24851365895` has not yet
   concluded. Because `4cccf90` touches only docs (CLAUDE.md banner, RUNNING-REGISTER, TRACKER, closeout,
   IMPROMPTU-04 review) and no test-impacting surfaces, this does not threaten the 3× green threshold on
   the actual fix commits. Operator should confirm `4cccf90` concludes green post-review; if it fails
   on a pre-existing flake, that's a separate disposition item, not a retroactive invalidation of this
   session's CI attestation.

3. **Residual test-infra race (aiosqlite cross-loop in fixture) documented but not fixed.** The close-out's
   §Unfinished Work bullet 1 acknowledges that the 100ms pre-disconnect guard applied to 4 observatory_ws
   tests is a band-aid — the underlying mechanism (test fixture's aiosqlite connection opened on test's
   event loop, accessed from TestClient portal thread loop) is a different race than the push-loop-sleep
   race DEF-193/200 name. The close-out proposes this as scope for the post-31.9 Component Ownership
   sprint, which is appropriate. No DEF has been filed for it yet — operator may wish to open DEF-201
   (or similar) to make the followup tractable. Not blocking.

## Escalation Triggers Checklist

| Trigger | Met? | Analysis |
|---|---|---|
| Any observatory_ws test failure not acknowledged in close-out | **NO** | All 14 observatory_ws tests pass locally (`-n 4`, 5.10s). Rounds 1–3 flakes in CI history are narrated in §CI Attestation; final rounds 4 greens are attained and URL-anchored. |
| Fix is a silent `@pytest.mark.skip` | **NO** | `git diff ... -- tests/api/test_observatory_ws.py | grep -E "skip\|mark\.skip"` returns empty. No skips added. |
| Scope boundary violation | **NO** | Only `observatory_ws.py` runtime file touched; only `test_observatory_ws.py` test file touched. No workflow/, no config, no audit back-annotations. |
| CI still red on final commit `4cccf90` | **N/A (actual check: run for `b6e569b` = `24851073257`)** | `24851073257` is confirmed **success** via `gh run view`. `4cccf90` is docs-only, CI in-progress; not a blocker per §Concerns item 2. |
| DEF-193 re-added to post-31.9 horizon | **NO** | Verified strikethrough at CAMPAIGN-COMPLETENESS-TRACKER.md line 141: `| ~~DEF-193~~ | ~~Observatory WS push-only disconnect detection~~ ✅ CLOSED IMPROMPTU-CI`. Not present in any other horizon's scope. |
| Audit-2026-04-21 back-annotations modified | **NO** | `git diff f97e255..4cccf90 --name-only | grep -i audit` returns empty. No audit docs touched. |

**No escalation trigger fires.** ✓

## Judgment Calls Evaluated

| Call | Verdict | Notes |
|---|---|---|
| Bundle DEF-193 closure with DEF-200 | **AGREE** | The same-CI-run same-signature identity proof is specific and verifiable. Kickoff's Constraint-4 explicitly authorizes this path. Alternative (leave DEF-193 open for a future session shipping the identical one-line fix) is ceremonial waste. |
| Test-side tactical mitigation on 4 tests in addition to production fix | **AGREE** | Rounds 1–3 CI evidence proved the cross-loop aiosqlite race in the test fixture is a distinct mechanism from the push-loop-sleep race. Test-side mitigation is appropriately scoped to eliminate that specific race in the fixture while the production fix handles the actual push-loop bug. The `ws_update_interval_ms=10000` bump and 100ms pre-disconnect guard are not masking the production bug (which is DEF-200's actual mechanism); they are stabilising the fixture. Proper followup documented. |
| `except Exception` in `_watch_disconnect()` | **AGREE** | Watcher is a signaller, not a critical path. Any receive failure (WebSocketDisconnect, RuntimeError from starlette's ASGI state machine, transport error) means "peer is gone — fire the sentinel." Stricter exception list would be brittle against starlette-version-specific types without behavior gain. |
| `_watcher_task = None` init before `try` block | **AGREE** | Sidesteps `UnboundLocalError` if auth fails before watcher creation. Simpler reader mental model than `locals().get(...)`. Close-out notes the first draft used `locals()` and refactored — this is the right direction. |
| `arena_ws.py` intentionally NOT touched | **AGREE** | Sibling file may use the same push-only idiom but has not surfaced the same CI symptom; the kickoff explicitly scoped to observatory_ws. Pattern is now one-shot portable if arena_ws ever surfaces the same bug. No scope creep. |

## Notes for Sprint History

- **Close-out discipline on CI iteration is exemplary.** The 4-round progression (with each round's specific
  fail mode and targeted mitigation narrated) is the kind of honest iteration documentation that will pay
  dividends when a future session hits a similar flake in adjacent code. The close-out does NOT pretend
  the first commit greened CI; it owns the full discovery arc.
- **The DEF-193 bundling decision is a textbook "proven-identical" call.** Kickoff-level constraint
  enforcement (scope preservation) vs pragmatic engineering (don't ship the same fix twice) is resolved
  by the kickoff's own escape hatch. Worth capturing as a playbook entry for campaigns that rely on tight
  per-session scope.
- **The test-infrastructure residual race (fixture's cross-loop aiosqlite) is the right scope to defer.**
  Properly fixing it requires refactoring `observatory_service` ownership — a Component Ownership concern,
  not a CI-unblock concern. The band-aid is honest, scoped, and flagged for the natural follow-up sprint.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "sprint-31.9-health-and-hardening",
  "session": "IMPROMPTU-CI-observatory-ws-teardown",
  "verdict": "CLEAR",
  "profile": "STANDARD",
  "commits_reviewed": [
    "a50ac8d",
    "732d213",
    "e9b399b",
    "bdf2e67",
    "4efdd75",
    "31eef12",
    "c3c1f9c",
    "1ee636e",
    "48923d3",
    "4c805c6",
    "ec98a5b",
    "b6e569b",
    "4cccf90"
  ],
  "fix_commit": "a50ac8d",
  "green_ci_commits": ["4c805c6", "ec98a5b", "b6e569b"],
  "baseline_head": "f97e255",
  "tests": {
    "before": 5052,
    "after": 5054,
    "delta": 2,
    "all_pass": true,
    "vitest_before": 859,
    "vitest_after": 859,
    "local_observatory_ws_run": "14 passed in 5.10s (-n 4)"
  },
  "ci_attestation": {
    "pre_session_run_id": "24848146684",
    "pre_session_commit": "2290401",
    "pre_session_conclusion": "failure",
    "green_run_ids": ["24851067204", "24851072630", "24851073257"],
    "green_run_conclusions": ["success", "success", "success"],
    "threshold_met": true,
    "final_docs_commit_run_id": "24851365895",
    "final_docs_commit_status": "in_progress_at_review_time"
  },
  "escalation_triggers": {
    "observatory_ws_test_failure_unacknowledged": false,
    "silent_pytest_mark_skip": false,
    "scope_boundary_violation": false,
    "ci_red_on_fix_commit": false,
    "def193_readded_to_post_319_horizon": false,
    "audit_20260421_backannotation_modified": false
  },
  "checks_performed": {
    "diagnosis_credibility": "PASS (3 of 4 candidates ruled out with evidence; kickoff required ≥ 2)",
    "fix_structural_markers_present": "PASS (all 4 markers at correct lines in observatory_ws.py)",
    "grep_guard_revert_proof_every_platform": "PASS (all 5 assertions match live fix markers)",
    "behavioral_test_revert_proof_linux_xdist": "PASS (limitation honestly documented in test docstring + close-out)",
    "three_consecutive_ci_greens": "PASS (4c805c6 / ec98a5b / b6e569b — gh run view confirms)",
    "def200_opened_and_closed_same_session": "PASS (CLAUDE.md DEF table + RUNNING-REGISTER + TRACKER)",
    "def193_strikethrough_closed": "PASS (CLAUDE.md + TRACKER post-31.9 horizon annotated)",
    "def193_removed_from_post319_horizon": "PASS (strikethrough + [closed IMPROMPTU-CI] annotation)",
    "improptu04_verdict_addendum_present": "PASS (textual + JSON with verdict_history + verdict_original)",
    "scope_boundary": "PASS (only observatory_ws.py + test_observatory_ws.py in code/test scope)",
    "pytest_delta_matches_claim": "PASS (+2 exactly: grep-guard + behavioral)",
    "three_deviations_honestly_documented": "PASS (D1 DEF-193 bundle, D2 tactical mitigation, D3 behavioral test guard)",
    "no_workflow_submodule_changes": "PASS",
    "no_config_yaml_changes": "PASS",
    "no_audit_backannotation_changes": "PASS"
  },
  "scope_violations": [],
  "judgment_calls_evaluated": [
    {"id": "bundle_def193_with_def200", "verdict": "AGREE", "note": "Kickoff Constraint-4 explicitly authorizes when root cause proven identical; same-CI-run same-signature proof is specific and verifiable."},
    {"id": "test_side_tactical_mitigation", "verdict": "AGREE", "note": "Rounds 1–3 CI evidence showed a distinct cross-loop aiosqlite race in the test fixture, separate from the push-loop-sleep race; mitigation scoped to the fixture race only. Not masking the production bug."},
    {"id": "except_exception_in_watcher", "verdict": "AGREE", "note": "Watcher is a fire-and-forget signaller; stricter exception list brittle against starlette-version-specific types."},
    {"id": "watcher_task_init_before_try", "verdict": "AGREE", "note": "Sidesteps UnboundLocalError on early-auth-fail; simpler reader mental model than locals().get()."},
    {"id": "arena_ws_not_touched", "verdict": "AGREE", "note": "Kickoff-scoped to observatory_ws; arena_ws not CI-surfacing the bug; pattern portable if ever needed."}
  ],
  "concerns": [
    {"id": "improptu04_review_json_paper_trading_field_stale", "severity": "LOW", "note": "JSON field at line 261 still reads 'CONDITIONAL_GO_PENDING_PUSH_AND_CI' while textual addendum upgrades to 'GO'. Cosmetic drift; textual prose supersedes for operator clarity."},
    {"id": "final_docs_commit_ci_in_progress", "severity": "LOW", "note": "Run 24851365895 for 4cccf90 (docs-only) not yet concluded at review time. Not a 3× greens invalidator because docs-only commit cannot affect test outcomes; operator should confirm green post-review."},
    {"id": "test_infra_residual_race_not_filed_as_def", "severity": "LOW", "note": "The 100ms pre-disconnect guard applied to 4 observatory_ws tests band-aids a distinct cross-loop aiosqlite race in the fixture. Close-out §Unfinished Work proposes the natural follow-up scope (post-31.9 Component Ownership sprint, observatory_service ownership refactor) but no DEF filed yet. Operator may wish to open DEF-201 for tractability."}
  ],
  "escalation_items": [],
  "paper_trading_readiness": "UNBLOCKED",
  "notes": "Production fix at argus/api/websocket/observatory_ws.py:116-148 is the kickoff's candidate-(a) prescription executed cleanly. All 4 structural markers present, 5 grep-guard assertions match, 3× green CI attained and verified via gh run view. DEF-200 opened and closed in-session. DEF-193 closure justified by same-CI-run same-signature identity proof. IMPROMPTU-04 verdict addendum present with verdict_history array. Scope boundaries clean. Three deviations honestly documented. No escalation trigger fires.",
  "recommended_next_action": "Close out IMPROMPTU-CI. Upgrade IMPROMPTU-04 verdict to CLEAR per addendum (already done in IMPROMPTU-04-review.md). Proceed to Phase 1b kickoffs (IMPROMPTU-05/06/07/08) — the campaign P25 green-CI rule is now satisfied. Optional cleanup: (a) sync IMPROMPTU-04 review JSON paper_trading_readiness field on next doc-sync pass; (b) consider opening DEF-201 for the aiosqlite cross-loop fixture race if the Component Ownership sprint hasn't yet been DISCOVERY-documented."
}
```
