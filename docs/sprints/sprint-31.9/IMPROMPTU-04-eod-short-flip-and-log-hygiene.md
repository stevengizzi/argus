# Sprint 31.9 IMPROMPTU-04: EOD Short-Flip Safety + Log Hygiene + Startup Invariant

> Generated 2026-04-23 from the April 22 paper session debrief (`docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md`) + Apr 21 F-01 residual. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign.

## Scope

**Findings addressed:**
- **DEF-199** (CLAUDE.md + debrief §A1) — `_flatten_unknown_position()` systematically doubles short positions at EOD. CRITICAL safety.
- **Debrief §C1** — `argus/strategies/pattern_strategy.py:318` emits INFO-level log per-candle × per-strategy × per-symbol during warm-up; 87% of log volume on Apr 22 (and on Apr 21 — same bug = Apr 21 F-01, rediscovered).
- **New startup invariant** (debrief §A1 recommended) — after broker connect, assert all returned positions have `side == OrderSide.BUY`. If any are `SELL`, emit ERROR log and block auto-startup-cleanup flatten pending operator acknowledgement. ARGUS is currently long-only; an unexpected short at startup is a red flag.

**Files touched:**
- `argus/execution/order_manager.py` — A1 side-check at 2 sites (`:1707` EOD Pass 2, `:1684` EOD Pass 1 retry)
- `argus/strategies/pattern_strategy.py` — C1 log level downgrade at `:318`
- `argus/main.py` — Startup invariant inserted after `self._broker.connect()` (around `:303`)
- Test files:
  - `tests/execution/order_manager/test_sprint295.py` — extend `test_eod_flatten_broker_only_positions` + add new short-side regression tests
  - `tests/strategies/patterns/test_pattern_strategy.py` — add log-level regression test (if file doesn't exist, create)
  - New regression test file(s) for startup invariant (location TBD based on existing main.py test patterns)

**Safety tag:** **`safe-during-trading`** — the session work itself (edits + tests + commits + Tier 2 review) does not touch the running ARGUS process. Code changes on disk do not hot-reload. The new code only takes effect when the operator stops + restarts ARGUS (see "Post-Session ARGUS Restart Timing" at the bottom of this kickoff). You MAY run this session while ARGUS is actively paper-trading.

**Theme:** Three fixes that together unblock future paper trading sessions from the DEF-199 risk: A1 safety, C1 log volume, and a startup invariant. The A1 fix is the central artifact; C1 is folded in because it's a one-line trivial fix and bundling keeps both in one Tier-2-reviewed commit series. The startup invariant is a defense-in-depth addition recommended by the debrief.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MAY be running — this session is safe-during-trading.
# Code changes don't hot-reload into a running process; the fix takes
# effect only after the operator restarts ARGUS (see end of this prompt).
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — also fine"

# If ARGUS is running on the buggy commit right now, that's expected and
# doesn't block this session. The bug remains active in the running
# process until restart, so the operator should plan the restart timing
# per the "Post-Session ARGUS Restart Timing" section below.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline:** 5,039 pytest local (5,026 on CI with `-m "not integration"`) + 859 Vitest. Three pre-existing failures acceptable on CI (2 date-decay DEF-163-family + 1 flaky DEF-150 — both resolved in FIX-13a; any new failures must be investigated).

If your baseline count diverges materially (e.g., ±5 tests from planning-time estimate), pause and investigate before proceeding. In particular:
- If tests are FAILING that weren't failing on 2026-04-23 at HEAD `053b6f8` (or whatever HEAD includes the Phase 1a commit + this kickoff), investigate before touching production code.
- If tests are MISSING (delta is strongly negative), re-clone to check for stash misread.

### 3. Branch & workspace

```bash
# Work directly on main — matches campaign pattern (FIX-01..FIX-13c all
# landed on main). Do NOT create a feature branch.
git checkout main
git pull --ff-only

# Confirm you are at or ahead of the expected campaign HEAD.
git log --oneline -5
# Expected: 053b6f8 (debrief triage) or later Phase 1a commits.

# Verify clean working tree. If there are uncommitted changes, stash
# them explicitly before proceeding.
git status
# Expected: "nothing to commit, working tree clean"
```

### 4. Read the debrief triage

Before touching any code, read `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` §A1 carefully. The root cause is spelled out in 4 numbered steps (lines 58–84). The fix outline (lines 89–118) is the starting point — with the improvements noted in Requirements below.

## Pre-Flight Context Reading

1. Read these files to load context:
   - `docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` — A1 root-cause proof (deterministic 2.00× ratio, 50/51 positions)
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"Category 1 IMPROMPTU-04" — scope bounds
   - `CLAUDE.md` DEF-199 entry (lines 426) — canonical DEF description + fix proposal
   - `argus/execution/order_manager.py` — the EOD flatten logic (`_eod_flatten`, `_flatten_unknown_position`, lines ~1600–2000)
   - `argus/execution/ibkr_broker.py:925-950` — the `get_positions()` Position construction with `side` + `abs(shares)`
   - `argus/models/trading.py` around line 164 — the `Position.shares: int = Field(ge=1)` constraint
   - `argus/strategies/pattern_strategy.py` around line 318 — the C1 log line
   - `argus/main.py:295-320` — Phase 3 broker connect where startup invariant will be inserted

2. Grep-verify all `get_positions()` call sites in `argus/`:
   ```bash
   grep -rn "broker\.get_positions\|await.*get_positions" argus/ | grep -v "^argus/tests"
   ```
   Read each result. Note which ones assume `qty > 0` implies long. Confirm in the close-out which sites carry the same blind spot and document disposition (fixed vs intentionally-different).

## Objective

Close DEF-199 with a side-check in the EOD Pass 2 + Pass 1-retry filters, plus
a startup invariant that catches any unexpected short at broker-connect time.
Downgrade the warm-up spam log at `pattern_strategy.py:318` to DEBUG.
Regression-test all three fixes including a revert-proof test for the A1 path.

## Requirements

1. **A1 fix at `argus/execution/order_manager.py:1707`** (EOD Pass 2).
   Replace the unconditional `_flatten_unknown_position` call with a side-aware
   branch:
   ```python
   for pos in broker_positions:
       symbol = getattr(pos, "symbol", str(pos))
       qty = int(getattr(pos, "shares", 0))
       side = getattr(pos, "side", None)
       if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
           if side == OrderSide.BUY:
               p2_submitted += 1
               logger.warning(
                   "EOD flatten: closing untracked long broker position "
                   "%s (%d shares)",
                   symbol,
                   qty,
               )
               await self._flatten_unknown_position(
                   symbol, qty, force_execute=True,
               )
           elif side == OrderSide.SELL:
               # ARGUS is currently long-only. An untracked short should NOT
               # be auto-flattened — a SELL would double it. Emit ERROR and
               # skip; operator must manually cover or investigate.
               logger.error(
                   "EOD flatten: DETECTED UNEXPECTED SHORT POSITION %s "
                   "(%d shares). NOT auto-covering. Investigate and cover "
                   "manually via scripts/ibkr_close_all_positions.py.",
                   symbol,
                   qty,
               )
           else:
               logger.error(
                   "EOD flatten: position %s has unknown side (%r, qty=%d). "
                   "Skipping auto-flatten.",
                   symbol, side, qty,
               )
   ```
   Import `OrderSide` from `argus.models.trading` at the top of the file if
   not already imported. Use the existing import site — do not create a
   duplicate.

2. **A1 fix at `argus/execution/order_manager.py:1684`** (EOD Pass 1 retry).
   Same pattern. The current block:
   ```python
   for sym in timed_out:
       retry_qty = broker_qty_map.get(sym, 0)
       if retry_qty > 0:
           logger.warning(...)
           await self._flatten_unknown_position(
               sym, retry_qty, force_execute=True
           )
   ```
   must be extended with a side check. Build `broker_side_map` alongside
   `broker_qty_map` from the `retry_positions` call, and apply the same
   three-branch logic as in Requirement 1 (BUY → flatten, SELL → log ERROR
   + skip, unknown → log ERROR + skip). The SELL branch message should
   reference the specific context (EOD Pass 1 retry, not Pass 2).

3. **Startup invariant in `argus/main.py`** (insert after `self._broker.connect()`).
   After the existing line:
   ```python
   account = await self._broker.get_account()
   logger.info("Broker connected. Account equity: %s", ...)
   ```
   add a new invariant block:
   ```python
   # --- Post-connect startup invariant: long-only position check ---
   # ARGUS is currently long-only. If the broker reports any short positions
   # at connect time, something has gone wrong upstream (prior session zombie,
   # manual trade, or a bug like DEF-199 that flipped positions short). Do not
   # proceed with auto-startup-cleanup (which would SELL and double any short).
   try:
       startup_positions = await self._broker.get_positions()
       unexpected_shorts = [
           p for p in startup_positions
           if getattr(p, "side", None) == OrderSide.SELL
       ]
       if unexpected_shorts:
           symbols = [
               f"{getattr(p, 'symbol', '?')}({getattr(p, 'shares', '?')})"
               for p in unexpected_shorts
           ]
           logger.error(
               "STARTUP INVARIANT VIOLATED: broker returned %d short "
               "position(s) at connect: %s. ARGUS is long-only; auto "
               "startup-cleanup flatten DISABLED for this session. "
               "Investigate and cover manually before next startup.",
               len(unexpected_shorts),
               ", ".join(symbols),
           )
           self._startup_flatten_disabled = True
       else:
           self._startup_flatten_disabled = False
   except Exception as e:
       # Fail-closed: if we can't verify, disable auto-cleanup to be safe.
       logger.error(
           "STARTUP INVARIANT check failed (%s). Disabling auto "
           "startup-cleanup flatten for this session.", e,
       )
       self._startup_flatten_disabled = True
   ```
   Then wire `self._startup_flatten_disabled` into the `ArgusSystem` attribute
   init and into wherever `_flatten_unknown_position` is called from the
   startup-cleanup path (not the EOD path — different consumers). Grep for
   `startup_flatten_queue` or `_drain_startup_flatten_queue` in
   `argus/execution/order_manager.py` to find the integration point.

   If the plumbing for `_startup_flatten_disabled` into the Order Manager's
   startup-cleanup path is non-trivial (requires constructor signature
   changes to multiple sites), document the complication in the close-out
   and use the simplest path: skip the `_drain_startup_flatten_queue` call
   in `argus/main.py` when `self._startup_flatten_disabled` is True. The
   invariant is still enforced; the plumbing is just lighter.

4. **C1 fix at `argus/strategies/pattern_strategy.py:318`**.
   Change `logger.info` to `logger.debug`:
   ```python
   if bar_count >= min_partial:
       logger.debug(  # was: logger.info
           "%s: evaluating %s with partial history (%d/%d)",
           self.strategy_id,
           symbol,
           bar_count,
           lookback,
       )
       self.record_evaluation(
           ...
       )
   ```
   No other changes. DEF-138 window summaries already provide INFO-level
   "not-silent-during-warm-up" visibility; this line is pure verbosity.

## Constraints

- **Do NOT modify** any other part of `argus/execution/order_manager.py` except lines `:1684` and `:1707` (plus the `OrderSide` import if needed). In particular, do NOT touch `_flatten_unknown_position` itself, the bracket amendment flow, stop-retry logic, or the reconciliation code path. Those live in post-31.9-reconnect-recovery-and-rejectionstage scope (DEF-196, DEF-194, DEF-195).
- **Do NOT modify** `argus/execution/ibkr_broker.py:925-950` — the `abs(int(ib_pos.position))` pattern is *correct*; the long/short information lives on `pos.side` as designed. Changing `ibkr_broker.py` to return signed shares would require changing `Position.shares: int = Field(ge=1)` in `models/trading.py`, which has broad downstream impact.
- **Do NOT modify** `argus/models/trading.py` — the `Field(ge=1)` constraint is the intentional invariant. The bug is at the consumer, not the model.
- **Do NOT modify** the `_drain_startup_flatten_queue` or `_flatten_unknown_position` implementations themselves. The side-check goes in the *filter* (the decision point), not in the flatten implementation — that keeps the blast radius of this change minimal.
- **Do NOT modify** `argus/strategies/pattern_strategy.py` other than the one `logger.info` → `logger.debug` change at `:318`. In particular, do NOT change the condition or the arguments or the record_evaluation call.
- **Do NOT touch** the `workflow/` submodule (Universal RULE-018).
- **Do NOT modify** any FIX-NN audit doc back-annotations. This session is DEF-based (DEF-199) and debrief-based, not audit-based.
- **Do NOT bundle in other DEFs** (e.g., DEF-177 MARGIN_CIRCUIT, DEF-176 kwarg removal). Those are in other sessions' scope.
- **Do NOT run live trading or paper trading** during or after this session until Tier 2 adversarial review passes and operator confirms.

## Canary Tests

Before making any production-code changes, run the canary-test skill at
`.claude/skills/canary-test.md` with these tests:

**Canary 1 — prove the A1 bug reproduces on Pass 2:**
- Build a test in `tests/execution/order_manager/test_def199_eod_short_flip.py` (new file)
- Mock `IBKRBroker.get_positions()` returning `[Position(symbol="FAKE", side=OrderSide.SELL, shares=100, ...)]`
- Populate `_managed_positions = {}` (FAKE is untracked)
- Call `_eod_flatten`
- **Current (pre-fix) expected result:** test demonstrates a SELL order fires for FAKE (doubling it to short -200). This proves the bug.
- **Post-fix expected result:** assertion flips — no SELL order fires; an ERROR log is emitted instead.

The test should be structured so reverting the fix causes the test to FAIL with a specific, easy-to-read message. This is the P6 gold-standard revert-and-fail proof.

**Canary 2 — prove the A1 bug reproduces on Pass 1 retry:**
- Same pattern for `:1684`. Build a test that forces a Pass 1 timeout with a short broker position and assert the retry does not SELL.

**Canary 3 — prove the C1 log-level fix works:**
- In `tests/strategies/patterns/test_pattern_strategy.py`, use `caplog` with `logging.INFO` level
- Configure a PatternBasedStrategy with a partial history and trigger `on_candle`
- **Post-fix expected result:** no record with message matching `"evaluating.*with partial history"` at INFO or above. (The log still fires at DEBUG, but caplog with INFO filter should see zero.)

**Canary 4 — prove the startup invariant blocks auto-cleanup on unexpected short:**
- In whichever test file covers `ArgusSystem` startup (look at `tests/test_main.py` or equivalent), mock `broker.get_positions()` to return a SELL-side position
- Assert `self._startup_flatten_disabled == True` after `startup()` completes
- Confirm an ERROR-level log was emitted
- Confirm `_drain_startup_flatten_queue` was NOT called (or was called but was a no-op due to the flag)

Only proceed to production code changes after all 4 canary tests are written
and the CURRENT (pre-fix) state shows them FAILING in the expected way (i.e.,
A1/A2 show the bad SELL, C1 shows the INFO line, invariant shows no
`_startup_flatten_disabled` attribute or it's False when it should be True).

## Test Targets

After implementation:
- All existing tests pass (5,039 baseline → at least 5,039 after)
- 4 canary tests flip to passing
- Expected test delta: **+4 to +7** (4 canary + 1-3 additional edge cases for the side-check: `side=None`, empty positions list, mix of long+short)
- Test command:
  ```bash
  # Scoped (during dev):
  python -m pytest tests/execution/order_manager/ tests/strategies/patterns/ -xvs -n 0

  # Full suite (at close-out):
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Definition of Done

- [ ] All 4 requirements implemented
- [ ] All existing tests pass
- [ ] 4 canary tests written; each FAILS when the corresponding fix is reverted (gold-standard revert-proof)
- [ ] Grep-audit of `get_positions()` call sites complete; close-out documents each site as (a) fixed by this change, (b) intentionally different (with rationale), or (c) a follow-up item logged as a new DEF
- [ ] `CLAUDE.md` DEF-199 entry updated with strikethrough + commit SHA + resolution description
- [ ] `docs/sprints/sprint-31.9/RUNNING-REGISTER.md` updated: move DEF-199 to "Resolved this campaign" table with IMPROMPTU-04 owner + commit SHA; update "Last updated" + "Campaign HEAD"
- [ ] `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` updated: move DEF-199 row to "Already resolved during campaign"; mark Stage 9A row as CLEAR (or CONCERNS_RESOLVED) with date
- [ ] Close-out report written to `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
- [ ] Tier 2 **adversarial** review completed via @reviewer subagent; review report at `docs/sprints/sprint-31.9/IMPROMPTU-04-review.md`
- [ ] Green CI run URL cited in the close-out (P25 rule — do not proceed to the next session before CI green is verified)

## Regression Checklist (Session-Specific)

After implementation, verify each of these invariants:

| Check | How to Verify |
|-------|---------------|
| Position with `side=BUY, shares=100` still gets flattened by EOD Pass 2 | Canary 1 variant: assert SELL order fires for long position |
| Position with `side=SELL, shares=100` does NOT get flattened by EOD Pass 2 | Canary 1: assert no SELL order fires; ERROR log emitted |
| Position with `side=None, shares=100` is skipped with ERROR log | Edge-case test |
| EOD Pass 1 retry respects same side check | Canary 2 |
| `pattern_strategy.py:318` no longer fires at INFO | Canary 3 |
| `pattern_strategy.py:318` still fires at DEBUG (log content preserved) | Additional assertion in Canary 3 |
| Startup invariant blocks cleanup on unexpected short | Canary 4 |
| Startup invariant passes when all positions are long (no-op path) | Additional assertion in Canary 4 |
| Startup invariant fails-closed on `get_positions()` exception | Edge-case test |
| No other `get_positions()` call site was missed | Grep-audit documented in close-out |
| Order Manager bracket amendment flow unchanged | No diff in the stop-cancel-retry or bracket-revision code paths (`git diff` review) |
| `IBKRBroker.get_positions()` signature + `abs(int(...))` pattern unchanged | Explicit constraint verified |
| `Position.shares: int = Field(ge=1)` unchanged | Explicit constraint verified |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the full
report (including the structured JSON appendix) to it, and commit it.

Include in the close-out:
1. **Revert-proof evidence table** for each of the 3 fixes (A1 Pass 2, A1 Pass 1, C1, invariant), with pytest output showing the test fails pre-fix and passes post-fix.
2. **Grep-audit of `get_positions()`** — enumerate every call site found, document disposition for each (fixed, intentionally-different, new DEF).
3. **Side-effect audit** — confirm no changes to bracket amendment, stop-retry, reconciliation, or `get_positions()` signature paths.
4. **Green CI run URL** for the final commit SHA (P25 rule; do not produce the close-out until CI has run green).
5. **Paper-trading readiness attestation** — explicit statement that the operator can now resume paper trading with this commit as the running HEAD.

## Tier 2 Review (Mandatory — @reviewer subagent, ADVERSARIAL profile)

After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the **Tier 2 adversarial review** within this same session.

Provide the @reviewer with:
1. **Review context:** this kickoff file + the debrief §A1 + the canary tests
2. **Close-out report path:** `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
3. **Diff range:** `git diff HEAD~N` where N = number of commits landed in this session
4. **Test command:** `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. **Files that should NOT have been modified:**
   - `argus/execution/ibkr_broker.py` (any line)
   - `argus/models/trading.py` (any line, especially line 164)
   - `argus/execution/order_manager.py` lines OTHER than `:1684`, `:1707`, and any necessary import additions
   - `argus/strategies/pattern_strategy.py` lines OTHER than `:318`
   - Any workflow/ submodule file
   - Any audit-2026-04-21 doc back-annotation

The @reviewer will produce its review report (including a structured JSON
verdict fenced with ```json:structured-verdict) and write it to:
`docs/sprints/sprint-31.9/IMPROMPTU-04-review.md`

## Session-Specific Review Focus (for @reviewer)

1. **Adversarial: try to break the A1 fix.** Hypothesize at least 3 scenarios where the fix could still fail (e.g., `side` attribute is wrong type, `Position` object is a mock with `side=MagicMock()` instead of real enum, etc.) and verify the fix handles each. If it doesn't, escalate.
2. **Verify the revert-proof tests are real.** Temporarily (mentally — do NOT commit) revert each fix and confirm the corresponding test would fail in a clear, informative way. "The test passes after revert" = escalation.
3. **Grep-verify the call-site audit.** Independently run `grep -rn "broker\.get_positions\|await.*get_positions" argus/` and compare against the close-out's enumeration. Any missing site is a regression risk.
4. **Verify no drift into out-of-scope paths.** Diff against HEAD~N and confirm no lines changed in bracket amendment, stop-retry, reconciliation, or `IBKRBroker` paths.
5. **Verify the startup invariant integration point.** Confirm `_startup_flatten_disabled` (or the equivalent disable mechanism) is actually wired into the code path that would otherwise trigger `_drain_startup_flatten_queue`. A flag that's set but never read is a silent failure.
6. **Verify the CLAUDE.md DEF-199 strikethrough is actually there** and the commit SHA is correct (not the kickoff-drafting SHA, not HEAD before the session started). This is the FIX-03 lesson — close-out claims must match source-of-truth state.
7. **Verify green CI.** Pull the CI run URL from the close-out and confirm the run is green against the final commit. If not green, ESCALATE immediately — do not accept "CI is running" or "will verify later."

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta ≥ +4 (4 canary tests; +7 if edge-cases included)
- No new pre-existing-failure regressions
- Vitest count unchanged at 859 (this session touches no UI)
- No scope boundary violation (see "Files that should NOT have been modified" above)
- No Rule-4 sensitive file touched without authorization
- Audit-report back-annotation not applicable (DEF-199 is a CLAUDE.md DEF, not an audit finding)
- CLAUDE.md DEF-199 strikethrough landed and grep-verified

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE verdict if ANY of:
- Any of the 4 canary tests fail or the revert-proof structure is weak (test passes even after revert)
- pytest net delta < +4
- Scope boundary violation: `ibkr_broker.py`, `models/trading.py`, `workflow/`, or any order_manager line other than `:1684`/`:1707` modified
- Rule-4 sensitive file touched without authorization (the A1 fix IS Rule-4 sensitive but the kickoff authorizes touching `:1684` and `:1707` explicitly — any other line in `order_manager.py` requires escalation)
- Different test failure surfaces than the expected DEF-150 flake
- Audit-report back-annotation modified (not in scope for this session)
- `get_positions()` call-site audit is incomplete or missing from close-out
- Green CI URL missing from close-out or CI is red
- Startup invariant flag is set but not read (silent no-op)
- Any Apr 22 debrief §A1 root-cause element (abs() in `ibkr_broker`, Field(ge=1) in `models/trading`, EOD Pass 1/Pass 2 filter) is contested or rewritten — the debrief is the specification for this session
- Operator's no-go-until-fixed commitment is at risk (e.g., you are uncertain the fix is safe enough to resume paper trading)

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix findings in-session, update both
the close-out and the review per the template's "Post-Review Fix Documentation"
section. For IMPROMPTU-04 specifically:
- If CONCERNS are about the A1 fix itself (missing branch, wrong enum, etc.), fixes are IN SCOPE
- If CONCERNS are about out-of-scope files (e.g., "you should also fix `ibkr_broker.py`"), the fix is OUT OF SCOPE — log a new DEF and defer
- ESCALATE findings must NOT be fixed without human review — the safety-critical nature of A1 means operator sign-off is required on any scope expansion

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** — full content for Work Journal paste
2. **The review markdown block** — full content for Work Journal paste
3. **Revert-proof evidence summary** — one line per canary test confirming the gold-standard
4. **Grep-audit summary** — count of `get_positions()` call sites + dispositions
5. **Green CI URL** — explicit link
6. **One-line summary:** `Session IMPROMPTU-04 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: 5,039 → {post}. CI: {URL}. Paper trading: CLEARED TO RESUME / BLOCKED ({reason}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai conversation.
Items (3) through (6) are for terminal visibility and human decision.

The operator must affirmatively acknowledge the "paper trading: cleared to
resume" line before the next paper session runs. If the line reads "BLOCKED,"
do not run paper trading until the blocker is resolved.

## Post-Session ARGUS Restart Timing

This section is for the OPERATOR, not Claude Code. Ignore during session execution.

The fix doesn't take effect until ARGUS is stopped + restarted. Between "commit
lands on main" and "ARGUS restarts with new code," the bug remains active in
the running process. Plan the restart window carefully:

| Timing | Safety | Notes |
|---|---|---|
| **After next EOD, before next market open** | ✅ Best | Clean state; no open positions; no in-flight signals. Restart → new code loaded → next session protected. |
| **During weekend (Sat/Sun)** | ✅ Best (equivalent) | Same clean state. Safe if IMPROMPTU-04 lands Fri post-market. |
| **Any time with zero open managed positions + no pending signals** | ✅ Safe | Pre-market pre-open, lunchtime lulls, etc. Verify state first. |
| **Mid-session with open positions** | ⚠️ Unnecessary risk | Restart reconnects Databento + IBKR through a fresh session window — the same window that caused the Apr 22 cascade. Zero safety benefit; potential fresh exposure. Avoid unless the bug is actively firing. |
| **EOD in progress** | ❌ Avoid | Worst case: the restart interrupts EOD flatten mid-sequence. Positions can end in inconsistent state. Wait for EOD to complete (or for the bug to fire one more time) before restarting. |

If ARGUS is running on the buggy code at the time IMPROMPTU-04 lands and paper
trading continues through the next EOD on the old code, the A1 bug CAN fire
one more time — that's the status quo before the fix was available. In that
case, the operator should be ready to run `python scripts/ibkr_close_all_positions.py`
as before, then restart with the new code afterward.

After restart, verify the fix is loaded by tailing `logs/argus_YYYYMMDD.jsonl`
for:
- Absence of the `"evaluating .* with partial history"` INFO spam (C1)
- Presence of the new startup-invariant log line (either confirming
  "all positions are long" or raising the red-flag ERROR)
- On the next EOD, presence of "closing untracked LONG broker position"
  (A1 new wording) rather than "closing untracked broker position" (pre-fix wording)

If any of these signals are missing, you are running on the old code — check
that `git log --oneline -1` at the ARGUS working-tree HEAD matches the
IMPROMPTU-04 final commit SHA.
