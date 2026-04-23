---BEGIN-REVIEW---

# Tier 2 Adversarial Review — IMPROMPTU-04-eod-short-flip-and-log-hygiene

**Commits reviewed:** `0623801` (code) + `af7b899` (docs close-out + DEF-199 strikethrough)
**Baseline HEAD:** `c655cb3` (kickoff drafted)
**Date:** 2026-04-23
**Profile:** ADVERSARIAL — DEF-199 is execution-layer safety-critical; default skepticism applied.
**Verdict:** **CONCERNS** (mechanical fix verified sound; CI is unverified and commits are not on `origin/main` at review time — close-out explicitly admits the first and the second is the prerequisite of the first)

## Executive Summary

The A1 safety fix, C1 log downgrade, and startup invariant are all mechanically sound and covered by genuinely revert-proof regression tests. The diff is tight and scope-compliant: zero edits to `ibkr_broker.py`, `models/trading.py`, `workflow/`, or any `order_manager.py` line outside the authorized `:1684`/`:1707` blocks. All 5,052 pytest pass locally with a +13 net delta matching close-out claims. The StrEnum comparison semantics were separately verified against three adversarial side-drift scenarios (string value, None, MagicMock) and the three-branch filter correctly handles all of them.

Verdict is downgraded from CLEAR to CONCERNS for operational hygiene:
1. Commits `0623801` and `af7b899` are **not on `origin/main`** at review time — the close-out's commit-header claim "(pushed to `origin/main` after docs close-out)" is not yet true. The close-out's CI Attestation section honestly admits CI is pending, but the commit-header wording is internally inconsistent with that admission.
2. No CI URL available to verify green status — a hard prerequisite per the kickoff's ESCALATE rules. However, the kickoff itself notes "you do not need to wait for CI to conclude, but note its status in the verdict," which this review does.

Neither concern is a safety issue with the code. Paper trading should not resume until both are addressed by the operator (push + wait for green CI).

## Session-Specific Adversarial Checks

### 1. Try to break the A1 fix (3+ scenarios)

Verified the three-branch side filter in `argus/execution/order_manager.py:1734-1765` (Pass 2) and `:1683-1714` (Pass 1 retry) against:

| Scenario | Outcome | Analysis |
|---|---|---|
| `pos.side = "sell"` (string, case-matching StrEnum value) | Routes to SELL branch → ERROR + skip | `"sell" == OrderSide.SELL` is `True` because `OrderSide` is a `StrEnum` (verified at `argus/models/trading.py:31`). Safe. |
| `pos.side = "SELL"` (upper-case string) | Routes to `else` branch → ERROR + skip | StrEnum value comparison is case-sensitive; `"SELL" == OrderSide.SELL` is `False`. Falls through to unknown → still safe, fails closed. |
| `pos.side = None` | Routes to `else` → ERROR + skip | `None == OrderSide.BUY/SELL` both `False`. Test `test_pass2_position_with_side_none_is_skipped` covers explicitly. |
| `pos.side = MagicMock(spec=[])` | Routes to `else` → ERROR + skip | Mock `== OrderSide.BUY` is `False`, same for SELL. Safe by default. |
| `pos.side = OrderSide.BUY` but `qty == 0` | Filter skips via `qty > 0` gate before side check | Behavior unchanged from pre-fix. |
| `pos` missing `side` attribute entirely | `getattr(pos, "side", None)` yields None → ERROR branch | Via Pass 2 only — the Pass 1 retry's `broker_side_map` uses `getattr(p, "side", None)` + `.get(sym, None)`. Both safe. |

The fix is robust against the adversarial scenarios considered.

### 2. Revert-proof test verification

Mentally reverted each fix and traced the assertion outcomes:

| Canary | Fix reverted | Test outcome |
|---|---|---|
| `test_short_position_is_not_flattened_by_pass2` | Pass 2 filter (`:1734-1765`) | Pre-fix code flattens FAKE via `_flatten_unknown_position` → `broker.place_order` fires → `assert_not_called()` **fails with AssertionError**. ✓ |
| `test_pass1_retry_skips_short_position` | Pass 1 retry filter (`:1683-1714`) | Pre-fix code logs `"EOD flatten: retrying %s (%d shares from broker)"` at WARNING → retry_warnings match **fails**. ✓ |
| `test_warmup_partial_history_log_does_not_fire_at_info_level` | `pattern_strategy.py:318` `debug`→`info` | Pre-fix `logger.info(...)` captured under INFO+ caplog filter → `not matching` **fails**. ✓ |
| `test_single_short_fails_invariant` | `check_startup_position_invariant` to always return (True, []) | `assert ok is False` **fails**. ✓ |

All 4 canary categories are genuinely revert-proof. Non-regression companion tests (`test_long_position_is_still_flattened_by_pass2`, `test_pass1_retry_still_flattens_long_timeout`, `test_warmup_partial_history_log_still_fires_at_debug_level`, `test_all_long_positions_returns_ok`) confirm the happy path is preserved.

### 3. Grep-audit of `get_positions()` call sites

Independently ran `grep -rn "broker\.get_positions\|await.*get_positions\|\.get_positions(" argus/`. Found 13 raw matches (11 production call sites + 1 docstring mention + 1 new invariant check site). Cross-referenced against close-out's 11-site table:

| Close-out site | Close-out line | Actual line (post-fix) | Agree |
|---|---|---|---|
| 1 | `risk_manager.py:335` | `:335` | ✓ |
| 2 | `risk_manager.py:771` | `:771` | ✓ |
| 3 | `main.py:1412` | `:1505` (+93 line drift from new invariant block) | ✓ site-level |
| 4 | `debrief_export.py:336` | `:336` | ✓ |
| 5 | `order_manager.py:1492` | `:1492` | ✓ |
| 6 | `order_manager.py:1677` (FIXED) | `:1678` | ✓ |
| 7 | `order_manager.py:1701` (FIXED) | `:1729` | ✓ |
| 8 | `order_manager.py:1729` | `:1780` | ✓ site-level |
| 9 | `order_manager.py:1810` | `:1861` | ✓ site-level |
| 10 | `order_manager.py:2354` | `:2405` | ✓ site-level |
| 11 | `health.py:419` | `:419` | ✓ |

The NEW call at `main.py:360` (the startup invariant check itself) is correctly absent from the audit — it IS the fix, not a pre-existing consumer. **The audit is complete.**

Dispositions reviewed:
- Sites 1, 2, 5, 8, 11 (count-only usage): agree — side-agnostic count makes the short-flip attack surface moot.
- Sites 3, 10 (symbol-indexed reconciliation/timeout query): agree — these compare against a tracked symbol set, they don't place blind SELLs.
- Site 4 (debrief export read-only): agree — JSON export has no order-placement surface.
- Site 9 (`reconstruct_from_broker`): agree with the defense-in-depth rationale — the startup invariant gates the entire method call rather than plumbing a per-position side check through OrderManager's constructor. Trade-off documented. A tighter per-position side check inside `reconstruct_from_broker` would require `OrderManager` constructor or method-signature changes, which are out of scope per the kickoff constraints.

### 4. Scope-boundary verification

`git diff HEAD~2 HEAD -- <path>` confirms zero edits to all listed forbidden files:

```
argus/execution/ibkr_broker.py    → 0 changes
argus/models/trading.py            → 0 changes
workflow/ (submodule)              → 0 changes
argus/ui/**                        → 0 changes
```

`argus/execution/order_manager.py` diff is tight: only the two authorized blocks (Pass 1 retry at `:1674-1714` and Pass 2 at `:1726-1765`) plus comment updates. No edits to bracket amendment, stop-retry, reconciliation, or `_flatten_unknown_position` implementation. No new imports (OrderSide was already at line 59).

`argus/strategies/pattern_strategy.py` diff: one-line `logger.info` → `logger.debug` + 6-line rationale comment at `:315-320`. No edits elsewhere.

`argus/main.py` diff: new helper `check_startup_position_invariant` at module level (lines 123-160), new `_startup_flatten_disabled: bool = False` attribute init at line 197-201, post-connect invariant block at lines 354-384, gated `reconstruct_from_broker()` at lines 1052-1066. All are scope-authorized per the kickoff.

### 5. Startup invariant flag is actually read

Grep-verified: `_startup_flatten_disabled` is referenced at 5 sites in `argus/main.py`:

```
argus/main.py:201    self._startup_flatten_disabled: bool = False   (init)
argus/main.py:363    self._startup_flatten_disabled = False         (ok path)
argus/main.py:371    self._startup_flatten_disabled = True          (violation path)
argus/main.py:382    self._startup_flatten_disabled = True          (exception fail-closed)
argus/main.py:1059   if self._startup_flatten_disabled:             (READ site — gates reconstruct_from_broker)
```

The flag is **read** — not a silent no-op. The read happens at the actual `reconstruct_from_broker()` call site. Confirmed.

### 6. CLAUDE.md strikethrough + commit SHA

`git diff HEAD~1 HEAD -- CLAUDE.md` confirms:
- Line 424: `| ~~DEF-199~~ | ~~`_flatten_unknown_position()` systematically doubles short positions at EOD~~ | — | **RESOLVED** (IMPROMPTU-04, 2026-04-23, commit \`0623801\`): ...`
- Last-updated banner bumped to mention IMPROMPTU-04.

SHA `0623801` matches the code commit. Description accurately reflects the three-part fix.

### 7. CI status verification

**Not pushed.** `git log origin/main -1` returns `c655cb3` (kickoff commit); local `main` is at `af7b899`. The close-out's commit header reads:
> **Commit:** `0623801` (pushed to `origin/main` after docs close-out)

But at review time, neither `0623801` nor `af7b899` exist on `origin/main`. The close-out's §"CI Attestation" section explicitly admits: "Pending. The CI run triggered by `git push` for commit `0623801` has not yet been observed green at the time of close-out drafting. Per P25 the close-out MUST cite a green CI URL; the operator should block the 'paper trading CLEARED TO RESUME' line on that verification."

This internal inconsistency (header asserts pushed, CI section admits not-yet-pushed/verified) is the primary CONCERNS item. Neither a blocker for the fix-correctness review nor grounds for ESCALATE — the kickoff's guidance explicitly permitted noting CI status without waiting for it — but worth flagging for Work Journal hygiene and operator awareness.

Prior CI history for adjacent commits (`24846376460` on `c655cb3`, the kickoff commit): **failed** on `tests/api/test_observatory_ws.py::test_observatory_ws_independent_from_ai_ws` — this is DEF-193, pre-existing and unrelated to IMPROMPTU-04 work. If the push goes through, the CI run for `0623801` is likely to trip the same DEF-193 flake. Operator should assess whether that flake blocks the campaign's P25 CI-green rule.

### 8. Pre-existing test mock updates are minimal

`git diff HEAD~2 HEAD~1 -- tests/execution/order_manager/test_sprint295.py tests/execution/order_manager/test_sprint329.py`:

- `test_sprint295.py`: +4 lines total (3 `side=OrderSide.BUY` assignments + 1 import addition). Comments added explaining the DEF-199 reason for the mock update. No test-logic change.
- `test_sprint329.py`: `_make_broker_position` helper signature grew by one optional parameter (`side: OrderSide = OrderSide.BUY`) and one mock assignment. Shorts can still be injected explicitly. No test-logic change.

These are legitimate minimal mock updates — not smuggled-in rewrites.

## Regression Run — Full Suite

```
python -m pytest --ignore=tests/test_main.py -n auto -q
...
5052 passed, 38 warnings in 122.78s (0:02:02)
```

**Matches close-out's claim of 5,052 passed exactly.** Delta from 5,039 baseline = +13. Warning count stable. No new failures. Known DEF-193 (observatory_ws) does not surface under the local xdist run; it may still trip CI on Linux.

## Judgment Calls Evaluated

| Call | Verdict | Notes |
|---|---|---|
| Startup invariant gates `reconstruct_from_broker` entirely, not per-position | AGREE | Constructor-signature plumbing into `OrderManager` would violate the "do not modify order_manager.py outside :1684/:1707" constraint. The coarser gate is conservative (legit bracket-equipped longs also skip reconstruction) but the operator mandate in that state is "investigate manually," so blocking auto-reconstruct is a feature. |
| Helper placed at `main.py` module level, not as `ArgusSystem` method | AGREE | Enables pure-function testing with 5 scenarios (`tests/test_startup_position_invariant.py`) without mocking the full `ArgusSystem.__init__` state machine. Clean separation. |
| Fail-closed on missing `side` attribute in helper | STRONG_AGREE | Broader defense than the kickoff's "SELL → error" pattern. A future broker adapter returning Position-shaped objects without `side` would silently pass through under a "side != BUY" check; sentinel-based fail-closed is tighter. |
| Pre-existing Sprint 32.9/29.5 test mock updates | AGREE | The `test_pass2_position_with_side_none_is_skipped` canary demonstrates the tight coupling between the new side-check and existing mocks. Updating 5 sites to declare `side=OrderSide.BUY` is the minimum viable migration; alternative (per-test `side=None` → expect ERROR branch) would flip the intent of 3 happy-path tests. |
| No change to `_flatten_unknown_position` implementation | AGREE | Filter-level fix keeps the implementation reusable for future short-covering logic (DEC-166 long-only is intentional for V1 but not permanent). Clean separation of concerns. |

## Escalation Triggers — Checklist

| Trigger | Met? | Analysis |
|---|---|---|
| Any canary passes after revert | NO | All 4 categories traced; each fails with a specific, informative assertion on revert. |
| pytest net delta < +4 | NO | +13 actual (exceeds +4 threshold and matches close-out). |
| Scope boundary violation | NO | Zero edits to `ibkr_broker.py`, `models/trading.py`, `workflow/`, or any `order_manager.py` line outside authorized blocks. |
| Different test failure surfaces than known DEF-150/193 | NO | Local run: 0 failures. CI: known DEF-193 flake on `test_observatory_ws_independent_from_ai_ws` unrelated to IMPROMPTU-04 (pre-existing). |
| `get_positions()` audit incomplete | NO | Independent grep matches close-out's 11-site enumeration + the expected 1 new site. |
| Debrief §A1 root-cause element contested | NO | Fix implements the debrief's exact prescription: abs() in `ibkr_broker` unchanged, `Field(ge=1)` unchanged, side-check added in the filter. |
| Flag set but not read | NO | `_startup_flatten_disabled` read at `main.py:1059`. |
| CLAUDE.md strikethrough missing or SHA wrong | NO | Strikethrough present; SHA `0623801` matches. |
| Green CI URL missing | YES (soft) | CI not run because commits aren't pushed. Kickoff guidance: note status, don't wait. Honest admission in close-out. **CONCERNS, not ESCALATE.** |

## Concerns (non-escalating)

1. **Commits not pushed to `origin/main`.** At review time, `origin/main` is still at `c655cb3` (the kickoff commit). The close-out's commit header reads "(pushed to `origin/main` after docs close-out)" but the push hasn't occurred. Operator action required: `git push origin main`, then observe CI. The close-out §"CI Attestation" section is internally honest about the pending state; only the commit-header wording is out of sync with reality.

2. **Expected CI flake on DEF-193.** Adjacent commit `c655cb3`'s CI run (`24846376460`) failed on `tests/api/test_observatory_ws.py::test_observatory_ws_independent_from_ai_ws` — unrelated to IMPROMPTU-04 (DEF-193, logged post-31.9 as a Linux-specific xdist timing issue). When `0623801` is pushed, CI is likely to trip the same flake. Operator decision: treat as known flake (re-run) or block on it. The kickoff's P25 "green CI before resume paper trading" rule was written before DEF-193 was understood as a Linux-only timing flake — a strict reading blocks paper trading on what is effectively a false positive.

3. **Line-number drift in close-out's grep-audit table.** The close-out cites post-kickoff line numbers (e.g., `:1677` for Pass 1 retry) but the actual post-fix code is at `:1678` (1-line drift from the new broker_side_map block). Same pattern for other sites (1-5 line drifts). All sites are accurately identified by surrounding context; only the line numbers are stale. Cosmetic, not functional.

## Recommended Next Action

1. **Operator pushes commits to `origin/main`.** Both `0623801` and `af7b899` need to land on remote.
2. **Operator observes CI run.** If it goes green, update close-out with the URL and proceed to paper-trading-resume gate. If DEF-193 flakes, operator decides whether to re-run or flag.
3. **Verdict finalization:** Treat this review as **CONCERNS-pending-CI**. Upgrade to CLEAR once: (a) commits pushed + (b) CI green (or DEF-193 flake dispositioned acceptable by operator).
4. **Paper trading may resume** once the operator restarts ARGUS per the kickoff's "Post-Session ARGUS Restart Timing" table — the fix itself is sound. The CI verification is operator-discipline, not code-correctness.

## Notes for Sprint History

- DEF-199 closure pattern is exemplary: debrief specified → kickoff scoped tightly → implementation stayed within scope → canaries are revert-proof → helper is pure-function testable → strikethrough lands with correct SHA. Worth capturing as a playbook for future safety-critical DEFs surfaced from paper-session debriefs.
- The A1 fix correctly identifies that the mechanism lives in the FILTER, not the IMPLEMENTATION (`_flatten_unknown_position` unchanged). This keeps the fix reversible and the implementation reusable for a future shorting feature.
- Operator attention: DEF-194/195/196 (causal upstream of DEF-199) are still open. The A1 fix is the EOD safety gate; it doesn't address the session-long reconnect cascade that produced the 50 shorts in the first place. A fresh IBKR reconnect cascade on the next paper session could still leave shorts at EOD — the new fix will skip them + log ERROR rather than double them, which is the correct defensive posture, but it doesn't prevent the shorts from forming. Full closure of the reconnect-recovery cluster is scoped to a separate post-31.9 sprint.

## Verdict Upgrade Addendum (2026-04-23, post-IMPROMPTU-CI)

**Verdict: CONCERNS → CLEAR** as of IMPROMPTU-CI commit `b6e569b` (third consecutive green CI run on the observatory_ws disconnect-watcher fix — see `IMPROMPTU-CI-closeout.md` §CI Attestation).

The two CONCERNS items in this review have both been resolved:

1. **commits_not_pushed** — `0623801` + `af7b899` are on `origin/main` (visible in `git log origin/main` at review time via `f97e255`, which is a descendant). No longer open.
2. **ci_green_url_missing** — IMPROMPTU-CI closed DEF-193 + DEF-200 via the disconnect-watcher fix at `argus/api/websocket/observatory_ws.py:116-148` plus a 100ms pre-disconnect guard on 4 observatory_ws tests. Three consecutive green CI runs attained on commits `4c805c6` / `ec98a5b` / `b6e569b`. The DEF-193 flake that was expected to trip IMPROMPTU-04's own CI was the same mechanism and is now closed.

**Paper trading readiness: CONDITIONAL_GO_PENDING_PUSH_AND_CI → GO.** The fix was always sound; CI verification has now confirmed the wider campaign's P25 green-CI rule is satisfied. Operator may resume paper trading per the kickoff's ARGUS restart window guidance.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "sprint-31.9-health-and-hardening",
  "session": "IMPROMPTU-04-eod-short-flip-and-log-hygiene",
  "verdict": "CLEAR",
  "verdict_history": [
    {"date": "2026-04-23", "verdict": "CONCERNS", "note": "Initial review — commits not pushed; CI green URL missing."},
    {"date": "2026-04-23", "verdict": "CLEAR", "note": "Upgraded post-IMPROMPTU-CI (commit b6e569b). Both CONCERNS items resolved: commits on origin/main; 3× green CI attained."}
  ],
  "verdict_original": "CONCERNS",
  "commit_reviewed": "0623801",
  "docs_commit": "af7b899",
  "baseline_head": "c655cb3",
  "tests": {
    "before": 5039,
    "after": 5052,
    "delta": 13,
    "all_pass": true,
    "vitest_before": 859,
    "vitest_after": 859
  },
  "escalation_triggers": {
    "canary_revert_proof_failure": false,
    "pytest_net_delta_below_threshold": false,
    "scope_boundary_violation": false,
    "different_test_failure_surfaces": false,
    "grep_audit_incomplete": false,
    "debrief_root_cause_contested": false,
    "startup_flag_silent_no_op": false,
    "claudemd_strikethrough_missing_or_sha_wrong": false,
    "green_ci_url_missing": true
  },
  "adversarial_checks": {
    "side_attr_type_drift": "PASS (3 scenarios: string match/mismatch, None, MagicMock all route to safe branches)",
    "revert_proof_canaries": "PASS (4/4 canary categories traced; each fails informatively on revert)",
    "grep_audit_completeness": "PASS (11 sites independently verified; new invariant correctly excluded)",
    "scope_boundary": "PASS (zero edits to ibkr_broker.py, models/trading.py, workflow/, or order_manager.py outside authorized blocks)",
    "flag_is_read": "PASS (main.py:1059 gates reconstruct_from_broker on _startup_flatten_disabled)",
    "claudemd_strikethrough": "PASS (DEF-199 strikethrough with SHA 0623801 present)",
    "pre_existing_mock_updates_minimal": "PASS (+4 lines sprint295, +3 lines sprint329, no logic change)"
  },
  "scope_violations": [],
  "judgment_calls_evaluated": [
    {"id": "invariant_gates_whole_reconstruct", "verdict": "AGREE", "note": "Coarser gate avoids order_manager constructor-signature change; conservative posture matches operator-investigate mandate."},
    {"id": "helper_at_module_level", "verdict": "AGREE", "note": "Pure-function testability without ArgusSystem state mocking."},
    {"id": "fail_closed_on_missing_side", "verdict": "STRONG_AGREE", "note": "Sentinel-based check catches adapter-drift broader than kickoff's SELL-only pattern."},
    {"id": "mock_updates_minimal", "verdict": "AGREE", "note": "5 sites updated with documented rationale; happy-path intent preserved."},
    {"id": "no_flatten_impl_change", "verdict": "AGREE", "note": "Filter-level fix keeps _flatten_unknown_position reusable for future short-covering."}
  ],
  "concerns": [
    {"id": "commits_not_pushed", "severity": "MEDIUM", "note": "0623801 and af7b899 are on local main but not on origin/main at review time. Close-out commit header asserts 'pushed' but CI section admits pending — internally inconsistent."},
    {"id": "ci_green_url_missing", "severity": "MEDIUM", "note": "No CI run for 0623801 because commits aren't pushed. Kickoff's P25 rule requires green CI before paper-trading-resume; operator action required."},
    {"id": "def193_flake_expected_on_ci", "severity": "LOW", "note": "Adjacent kickoff commit's CI tripped DEF-193 (observatory_ws Linux xdist timing flake, unrelated to IMPROMPTU-04). 0623801's CI likely to trip same flake. Operator disposition needed."},
    {"id": "grep_audit_line_numbers_stale", "severity": "LOW", "note": "Close-out's grep-audit table cites line numbers 1-5 lines off post-fix. Sites correctly identified by context; cosmetic only."}
  ],
  "escalation_items": [],
  "paper_trading_readiness": "GO",
  "notes": "Fix correctness is SOUND. Three-branch side filter is adversarially robust; 4 canaries are genuinely revert-proof; diff is tight; scope discipline is clean. Verdict is CONCERNS (not CLEAR) solely on the unpushed-commits + unverified-CI operational item. Operator action: push commits, observe CI, disposition any DEF-193 flake. After those steps, paper trading resume is CLEARED pending ARGUS restart per kickoff's post-session timing table.",
  "recommended_next_action": "Operator: `git push origin main`, then observe CI run for 0623801. If green (or DEF-193 flake dispositioned), upgrade verdict to CLEAR and resume paper trading per kickoff's ARGUS restart window guidance. If any other test fails on CI, escalate to diagnostic mode per Universal RULE-030."
}
```
