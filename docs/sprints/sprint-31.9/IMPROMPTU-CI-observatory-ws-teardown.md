# Sprint 31.9 IMPROMPTU-CI: Observatory WS Teardown Race Triage

> Drafted Phase 2 (post-IMPROMPTU-04 landing). Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Finding addressed:**
- **DEF-200** (NEW this session) — `tests/api/test_observatory_ws.py::test_observatory_ws_sends_initial_state` fails on Linux CI (3 consecutive docs-only commits: `150da6b`, `053b6f8`, `c655cb3`; expected on `0623801` post-push). Symptom: `1 failed, 5025 passed` with a teardown-race signature. FIX-13a's 200ms-interval mitigation (`tests/api/test_observatory_ws.py:262-266`) addressed sibling `test_observatory_ws_independent_from_ai_ws` (DEF-193) but is insufficient margin for `sends_initial_state`, which exits the `with` block the earliest of the 12 observatory_ws tests.

**Hypothesis (unverified — diagnosis is Requirement 1 of this session):**
The production push loop in `argus/api/websocket/observatory_ws.py:117-118` starts each iteration with `await asyncio.sleep(interval_s)`. When `test_observatory_ws_sends_initial_state` exits its `with` block immediately after the first receive, the server task is either (a) still finalizing the pre-loop initial `send_json`, or (b) already in the `asyncio.sleep`. Starlette's `TestClient` portal teardown waits for the server task to exit cleanly. On Linux under xdist with a saturated event loop, the sleep's cancellation can take long enough to trip the teardown timeout.

**If the hypothesis holds**, the fix lives in production code (`observatory_ws.py`): replace the plain `asyncio.sleep` with a cancel-aware wait on a disconnect sentinel, OR restructure the loop so the initial send is inside the loop body and the first iteration runs with a zero-delay path.

**If the hypothesis is wrong**, this session's Requirement 1 diagnostic pass surfaces the real cause and Requirement 2 (fix) is re-scoped.

**Files likely touched:**
- `argus/api/websocket/observatory_ws.py` (production fix — likely)
- `tests/api/test_observatory_ws.py` (possibly — if test-side hardening is needed alongside the prod fix)
- `CLAUDE.md` — open DEF-200; if prod fix lands, strikethrough-close DEF-200
- `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` — log DEF-200 + its disposition
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — Stage 8.5 row for IMPROMPTU-CI

**Safety tag:** `safe-during-trading` — no runtime trading logic touched. Observatory WS is a diagnostic read-only UI feature; modifying its push loop doesn't affect orders, positions, or strategies. Paper trading can continue.

**Theme:** Close DEF-200 so every remaining IMPROMPTU-NN session can legitimately cite a green CI URL. Unblock the Phase 1b kickoffs (05/06/07/08), the campaign SPRINT-CLOSE, and IMPROMPTU-04's verdict upgrade from CONCERNS to CLEAR.

## Urgency & Ordering

This session is **inserted ahead of IMPROMPTU-05**. Reason: every Phase 1b
kickoff specifies "green CI URL cited in close-out (P25 rule)" as a Definition
of Done item. If CI is red at campaign-close, that rule is either violated
or rendered toothless. Neither is acceptable.

IMPROMPTU-04's push should already have landed commits `0623801` + `af7b899`
on `origin/main` by the time this session runs. If CI against `0623801` shows
**only** `test_observatory_ws_sends_initial_state` failing, hypothesis is
confirmed (same pre-existing red). If CI shows additional failures, escalate
before proceeding with this session's fix work — something else is happening.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading MAY continue.
```

### 2. Verify CI state + baseline

Look up the CI run for `0623801` (IMPROMPTU-04's code commit). Record URL.

Expected: exactly one failure, `tests/api/test_observatory_ws.py::test_observatory_ws_sends_initial_state`. If there's any OTHER failure, **stop here and report to the operator** — the baseline is not what's assumed and this session's scope is wrong.

```bash
git checkout main
git pull --ff-only
git log --oneline -5
# Expected: 0623801 (IMPROMPTU-04 code) and af7b899 (docs) in the most recent 5
git status  # Expected: clean
```

### 3. Local baseline

```bash
python -m pytest tests/api/test_observatory_ws.py -xvs -n 0 2>&1 | tail -40
# Expected: the failing test may pass locally (race is CI-specific). Note the outcome.

python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count: __________ (baseline)
```

The test may pass on your local machine because it doesn't reproduce on macOS / Windows / low-contention runners. CI Linux under xdist is the reliable failure surface. Do NOT conclude "it passes locally, so it's fine" — the diagnostic work goes on.

## Pre-Flight Context Reading

1. Read these files:
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"IMPROMPTU-CI" (this session is inserted into Stage 8.5)
   - `CLAUDE.md` DEF-193 entry (sibling test flake, Linux xdist timing)
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-review.md` §"Expected CI flake on DEF-193" and §"Concerns #2"
   - `tests/api/test_observatory_ws.py` full file — understand all 12 tests + the conftest pattern + the FIX-13a hardening comments
   - `argus/api/websocket/observatory_ws.py` full file — 248 lines; focus on the push loop at lines 100-200 and the auth flow at lines 40-100
   - `docs/sprints/sprint-31.9/FIX-13a-closeout.md` (or FIX-13a-CI-hotfix closeout) — what did FIX-13a do to these tests, and what was the acceptance criteria?

2. Run the following diagnostic commands to characterize the failure surface:
   ```bash
   # Which tests in this file have historically been unstable?
   git log --oneline -20 tests/api/test_observatory_ws.py

   # Recent changes to the production code?
   git log --oneline -10 argus/api/websocket/observatory_ws.py

   # What was the FIX-13a mitigation exactly?
   git show 1141e56 -- tests/api/test_observatory_ws.py
   git show 7573ea4 -- tests/api/test_observatory_ws.py
   git show 0d58ad9 -- tests/api/test_observatory_ws.py
   ```

## Objective

1. **Diagnose** the failure mode of `test_observatory_ws_sends_initial_state`
   with enough confidence to rule out the "random flake" hypothesis and point
   at a specific fix direction (production code vs test code vs neither).
2. **Fix** the underlying issue. Preference order: (a) production fix that
   makes all observatory_ws tests teardown-safe, (b) test-side hardening that
   generalizes FIX-13a's pattern, (c) skip-if-CI fallback with explicit DEF.
3. **Verify** CI goes green on 3 consecutive runs against the fix commit
   (flake-free threshold).
4. **Open and close DEF-200** within this session if possible; if not, land a
   partial fix + demote to MONITOR with a concrete follow-up plan.

## Requirements

### Requirement 1: Diagnose

1. **Reproduce the failure** on any Linux-like environment under xdist load. If local reproduction is impossible, rely on CI. Running with `-n 4` or `-n 8` on Linux is often enough; pairing with `asyncio-debug` mode helps surface unawaited-coroutine or pending-cancellation artifacts.

2. **Instrument the push loop** with temporary diagnostic logging (do not commit this — purely for session investigation):
   ```python
   # At the top of the push loop (observatory_ws.py ~line 117):
   logger.warning("PUSH_LOOP: iteration starting, interval=%.3fs", interval_s)
   try:
       await asyncio.sleep(interval_s)
   except asyncio.CancelledError:
       logger.warning("PUSH_LOOP: cancelled during sleep")
       raise
   ```
   Run the test with these logs captured (`-s` flag), observe whether the cancellation completes cleanly or hangs.

3. **Characterize the race**. Primary candidates:
   - **(a) Teardown race on `asyncio.sleep`**: server task parked in the sleep when client disconnects; cancellation takes > teardown timeout on Linux xdist.
   - **(b) Initial `send_json` not flushing**: server sends the initial `pipeline_update` but the TCP/WebSocket buffer isn't flushed before the test receives — TestClient's portal sees state inconsistency.
   - **(c) ObservatoryService database init race**: `observatory_service.get_pipeline_stages()` at line 101 queries a fresh SQLite connection; xdist-parallel tests can contend on WAL mode checkpoints.
   - **(d) Event loop starvation from xdist**: tests running in parallel processes saturate CPU; 200ms sleep drifts to 800ms+; TestClient gives up.

4. **Eliminate candidates via targeted experiments**. For each, design a minimal test or instrumentation that confirms or rules out.

5. **Produce a diagnostic report** — either as a markdown block in the close-out OR as a standalone file at `docs/sprints/sprint-31.9/IMPROMPTU-CI-diagnosis.md`. Include: which candidate is the root cause, evidence, why other candidates were ruled out, proposed fix direction.

If after reasonable investigation (≤45 min diagnostic budget) the root cause is genuinely uncertain, pick the candidate with the strongest evidence, proceed with a fix targeting that candidate, and document the uncertainty in the close-out. Perfect diagnosis is not required — a credible fix that empirically greens CI is the real acceptance criterion.

### Requirement 2: Fix

Based on the diagnosis, land a fix. Below are fix patterns by candidate; pick one or adapt:

**If candidate (a) teardown race on sleep:**
- Replace `await asyncio.sleep(interval_s)` with a cancel-aware wait on a disconnect-sentinel event:
  ```python
  # After `await websocket.accept()`:
  _disconnect_event = asyncio.Event()

  async def _watch_disconnect():
      try:
          await websocket.receive()
      except WebSocketDisconnect:
          _disconnect_event.set()

  _watcher_task = asyncio.create_task(_watch_disconnect())

  # Inside the push loop, replace sleep with:
  try:
      await asyncio.wait_for(_disconnect_event.wait(), timeout=interval_s)
      break  # Disconnect sentinel fired → exit loop
  except asyncio.TimeoutError:
      pass  # Normal interval expired → proceed with push
  ```
  This makes cancellation ~instant on disconnect. Drawback: an additional task per connection; acceptable given observatory WS is not a high-fanout endpoint.

**If candidate (b) flush race:**
- After the initial `send_json`, add `await asyncio.sleep(0)` to yield to the event loop and let the buffer flush before entering the push loop. Cheap; often sufficient.

**If candidate (c) DB init race:**
- Lazy-init the observatory service query on first push-iteration rather than pre-loop. Drawback: moves a guarantee (initial state always sent) out of the interface contract. Only adopt if evidence is strong.

**If candidate (d) xdist starvation:**
- This is an environmental issue; fix is test-side. Options: `@pytest.mark.timeout(60)` to cap patience; `asyncio.sleep(0.05)` instead of 0.2 for tighter margin; separate test runner for WS tests (`-n 0` or dedicated xdist group). Least preferred — this is a symptom-mitigation rather than root fix.

**Acceptance criteria for the fix:**
- `test_observatory_ws_sends_initial_state` passes 3 consecutive CI runs post-fix.
- All 11 other tests in `test_observatory_ws.py` still pass (no regression — including the DEF-193-prone `test_observatory_ws_independent_from_ai_ws`).
- Full pytest suite baseline + existing tests unaffected.

### Requirement 3: Regression protection

1. If the fix is in production code, add a regression test explicitly exercising the teardown path. Example:
   ```python
   async def test_observatory_ws_cancels_cleanly_on_immediate_disconnect():
       """DEF-200 regression: server task must exit cleanly when client
       disconnects before any push interval elapses."""
       # Establish connection, auth, disconnect IMMEDIATELY after receiving
       # initial pipeline_update. Assert the server task completes within a
       # short timeout (e.g., 500ms).
   ```

2. If the fix is test-side only (e.g., `@pytest.mark.timeout`), add a comment in the test file explaining why the timeout is there — explicit reference to DEF-200 + commit SHA.

3. Verify the new regression test FAILS on the pre-fix code (revert-proof) and PASSES on the fixed code.

### Requirement 4: DEF lifecycle

1. **Open DEF-200** in CLAUDE.md with a brief description pointing at IMPROMPTU-CI. Timestamp + commit SHA of the diagnosis commit.

2. **If the fix is confirmed green** in 3 consecutive CI runs, strikethrough-close DEF-200 in the same session. Reference the fix commit SHA.

3. **If the fix is empirically effective but uncertainty about mechanism remains**, close as RESOLVED-EMPIRICAL with a note inviting revisit if the flake recurs.

4. **If no fix lands** (e.g., root cause turns out to be Starlette-version-dependent and requires an upstream change), leave DEF-200 OPEN with a MONITOR tag + concrete followup: either pin a Starlette version, file an upstream issue, or defer to a named horizon sprint. Document in IMPROMPTU-CI-closeout explicitly — do NOT silently punt.

### Requirement 5: CI verification

1. After landing the fix, trigger at least 3 CI runs against the same commit SHA. Use a trivial whitespace-only follow-up commit if needed to re-trigger. Record all 3 URLs in the close-out.

2. Do not declare DEF-200 closed until 3 consecutive greens are observed. If run #2 or #3 flakes, return to diagnosis — the fix is incomplete.

3. If `test_observatory_ws_sends_initial_state` now passes consistently but another test in the file starts failing, that's a new signal — diagnose before calling it done.

## Constraints

- **Do NOT modify** any non-observatory-WS runtime code. The push loop + auth flow + related dependency injection are the only in-scope prod surfaces.
- **Do NOT suppress** the failure with `@pytest.mark.skip` or equivalent unless Requirement 4's "no fix lands" branch is explicitly reached. Suppression without a concrete follow-up plan is a campaign anti-pattern.
- **Do NOT modify** any other test file in `tests/api/`. The diagnosis may involve reading sibling tests; modifications must stay in `test_observatory_ws.py` + observatory_ws production code.
- **Do NOT bundle** fixes for DEF-193 (sibling flake) into this session unless the root cause is proven identical. DEF-193 has its own MONITOR status; keep scope tight.
- **Do NOT modify** the `workflow/` submodule (Universal RULE-018).
- Work directly on `main`.

## Test Targets

- **Pre-session:** baseline matches IMPROMPTU-04 close-out count (5,052 local / 5,025 on CI with `-m "not integration"`).
- **New tests:** +1 (regression test for the fixed teardown path) if production fix; 0 if test-side-only.
- **Post-session:** 5,053 local / 5,026 on CI.
- **CI verification:** 3 consecutive greens on the fix commit.

## Definition of Done

- [ ] Diagnostic report produced (either in close-out or as standalone diagnosis file)
- [ ] Fix implemented in the appropriate layer (production preferred)
- [ ] Regression test added (if production fix) — FAILS on revert, PASSES on fix
- [ ] `test_observatory_ws_sends_initial_state` passes 3 consecutive CI runs
- [ ] All 11 sibling tests in `test_observatory_ws.py` still pass (no new regression)
- [ ] DEF-200 opened + strikethrough-closed in CLAUDE.md (or demoted to MONITOR with followup plan if no fix landed)
- [ ] `RUNNING-REGISTER.md` — DEF-200 logged + disposition; Stage 8.5 row marked COMPLETE
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` — IMPROMPTU-CI row marked CLEAR
- [ ] 3 green CI URLs cited in the close-out (P25 rule — amplified to 3× for flake threshold)
- [ ] Close-out at `docs/sprints/sprint-31.9/IMPROMPTU-CI-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/IMPROMPTU-CI-review.md`
- [ ] IMPROMPTU-04 verdict upgrade: close-out addendum to `IMPROMPTU-04-closeout.md` and/or `IMPROMPTU-04-review.md` noting "CI green as of IMPROMPTU-CI fix — verdict upgrades from CONCERNS to CLEAR." This is separate from this session's own review.

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Fix applied at the correct layer (prod preferred) | Diff inspection |
| Regression test fails pre-fix, passes post-fix | Manual revert + pytest run |
| All 12 tests in `test_observatory_ws.py` pass | `pytest tests/api/test_observatory_ws.py -n auto` |
| No regression in `tests/api/` adjacent files | `pytest tests/api/ -n auto` |
| 3 consecutive CI greens against fix commit | CI dashboard |
| DEF-200 has a clear disposition | CLAUDE.md read |
| No scope creep into DEF-193's territory | diff inspection |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/IMPROMPTU-CI-closeout.md`

Include:
1. **Diagnosis section** — root cause, candidates ruled out, evidence
2. **Fix rationale** — why this specific approach was chosen over alternatives
3. **Before/after CI state** — 1 red run pre-fix + 3 green runs post-fix with URLs
4. **DEF-200 disposition** — OPEN/MONITOR/CLOSED with commit SHA
5. **IMPROMPTU-04 verdict addendum** — explicit statement that IMPROMPTU-04's CONCERNS verdict upgrades to CLEAR as of this session's landing
6. **Green CI URLs (3×)** for the fix commit

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Invoke @reviewer after close-out.

Provide:
1. Review context: this kickoff file + CLAUDE.md DEF-200 + DEF-193 entries + IMPROMPTU-04 review report
2. Close-out path: `docs/sprints/sprint-31.9/IMPROMPTU-CI-closeout.md`
3. Diff range: `git diff HEAD~N`
4. Test commands: `pytest tests/api/test_observatory_ws.py -n auto` + `pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified:
   - Any argus/ runtime file other than `observatory_ws.py`
   - Any test file other than `test_observatory_ws.py`
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation
   - `config/*.yaml`

The @reviewer writes to `docs/sprints/sprint-31.9/IMPROMPTU-CI-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify the diagnosis is credible.** The close-out's diagnostic report should rule out at least 2 of the 4 candidate root causes with evidence, not just assertion.
2. **Verify the fix actually fixes.** If production, read the diff against the specific failure mode claimed. If test-side, understand why the prior 200ms mitigation was insufficient and why the new mitigation is robust.
3. **Verify regression test is revert-proof** (if production fix was landed).
4. **Verify 3-consecutive-greens threshold was met.** One green CI is insufficient for a flake — three is the campaign's empirical threshold (FIX-13a used the same standard).
5. **Verify DEF-200 has clear disposition.** If closed, commit SHA cited. If open, followup plan explicit.
6. **Verify IMPROMPTU-04 verdict addendum is present** in either IMPROMPTU-04-closeout.md or IMPROMPTU-04-review.md (your pick of location; operator cares that it exists).
7. **Verify no DEF-193 scope creep.** DEF-193's sibling flake should still exist (unless this fix is proven to subsume it, in which case that's explicitly called out).

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0 or +1 (regression test if production fix)
- Vitest count unchanged
- No scope boundary violation
- CLAUDE.md DEF-200 entry exists (open or closed)

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- CI still red after fix (less than 3 greens observed)
- Fix is a silent `@pytest.mark.skip` without explicit "Requirement 4 no-fix branch" documentation
- Any DEF-193 regression (sibling test broken by this session's changes)
- Audit-report back-annotation modified
- New regression in `tests/api/` outside `test_observatory_ws.py`

## Post-Review Fix Documentation

Standard protocol.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **CI status:** RED → GREEN (3× verification)
4. **DEF-200 disposition** (CLOSED / MONITOR / OPEN)
5. **IMPROMPTU-04 verdict upgrade** (CONCERNS → CLEAR now eligible)
6. **Three green CI URLs**
7. One-line summary: `Session IMPROMPTU-CI complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. DEF-200: {disposition}. 3× CI green: {URLs}. IMPROMPTU-04 verdict now upgrades CONCERNS → CLEAR. Phase 1b cleared to run.`
