# Sprint 31.92 Session 1a — Close-Out Report

**Session:** S1a — Path #1 Mechanism Spike (H2 modify_order rejection-rate + 4 adversarial axes + N=100 cancel-then-immediate-SELL HARD GATE)
**Phase:** A diagnostic spike
**Date authored:** 2026-04-30 (UTC)
**Self-assessment:** FLAGGED — script delivered; spike-execution gap blocks PROCEED-or-INCONCLUSIVE determination
**Context state:** GREEN

---

## Status Summary

The implementation deliverable for S1a is the spike script `scripts/spike_def204_round2_path1.py`. That script is delivered, dry-run-validated, and ready for operator execution.

**The Definition-of-Done items that depend on the spike actually running against paper IBKR Gateway are NOT met by this session and cannot be met without operator action.** The spike is `non-safe-during-trading`, requires market-CLOSED conditions, and includes two operator-orchestrated measurement axes (Mode B axis (ii) reconnect-window and axis (iv) joint-reconnect-concurrent) that cannot be automated. The session produces the script and the close-out; operator produces the JSON artifact + Tier 2 review.

This is a deliberate scope cut explicitly disclosed under **RULE-007** (no scope expansion) and **RULE-011** (honest self-assessment).

---

## Change Manifest

| Path | Edit Shape | LOC delta | Notes |
|------|-----------|-----------|-------|
| `scripts/spike_def204_round2_path1.py` | NEW | +998 | Argparse-driven async-main spike harness; all 4 measurement modes + decision rule + 14-key JSON emit. |
| `docs/sprints/sprint-31.92-def-204-round-2/session-1a-closeout.md` | NEW | +this file | This close-out. |

**Untouched (verified via `git status` + `git diff --stat HEAD`):**

- `argus/**/*` — entire production tree.
- `frontend/` — Vitest count baseline 913 unchanged.
- `tests/` — pytest baseline unchanged (zero new tests; spike adds zero pytest).
- `workflow/` — submodule untouched.
- All sealed/frozen artifacts under `docs/sprints/sprint-31.91-reconciliation-drift/` and `docs/sprints/sprint-31.915-evaluation-db-retention/`.

`scripts/spike_def204_round2_path2.py` is present untracked but is the parallel **S1b** spike (already authored in a prior preparation step); it is out of S1a scope and was NOT modified.

---

## Pre-Flight Grep-Verify (RULE-038)

| Anchor | Expected | Observed | Disposition |
|--------|----------|----------|-------------|
| `scripts/spike_ibkr_oca_late_add.py` reference structure | ~10 hits including `parse_args`, `main_async`, `_classify_outcome`, `_run_one_trial` | 11 hits, all expected names present | OK |
| `argus/execution/ibkr_broker.py` IBKRBroker + 3 methods | 4 hits | 4 hits at lines 104, 789, 1028, 1262 | OK |
| `argus/execution/order_manager.py` Path #1 hot-path | 3 hits | 3 hits at lines 956, 3551, 3668 | OK |
| `scripts/spike_def204_round2_path1.py` (target file) | absent → ready to create | absent | OK |
| `scripts/spike-results/spike-def204-round2-path1-results.json` | acceptable either way; spike overwrites | absent (spike not yet run) | EXPECTED |
| Sprint 31.91 + 31.915 SEALED at HEAD | grep "Sprint 31.915\|Sprint 31.91 SEALED" | grep returned no literal match | RESOLVED-VERIFIED via commit-history inspection: `210d2f9` (31.91 D14 doc-sync — sprint close-out), `15f6746` (31.915 anchor closeout), `f42e25c` (31.915 Tier 2 review CLEAR + closeout addendum). The grep pattern in the prompt mismatched literal commit-message text but the seals are present. RULE-038 disclosure: proceed against the actual structural anchors (commit history inspection authoritative). |

Branch: `main`. Working tree clean apart from the new path1 spike script. clientId=1 reserved for S1a per the prompt; clientId=2 reserved for parallel S1b execution.

---

## Implementation Notes

The script structurally mirrors `scripts/spike_ibkr_oca_late_add.py` (DEC-386 Phase A reference):

- argparse-driven entrypoint → `asyncio.run(main_async(args))`
- async-main pattern with `IBKRBroker.connect()` / `disconnect()` framing
- per-trial timing capture via `time.monotonic()`
- single JSON emit at end via `json.dump(..., default=str)`
- exit-code semantics: `0` PROCEED / `1` INCONCLUSIVE / `2+` connection or invocation error

Measurement modes implemented per Requirement 1:

| Mode | Purpose | Trial cadence |
|------|---------|---------------|
| **A** | H2 baseline `modify_order` round-trip latency + rejection rate + deterministic broker-side `auxPrice` propagation | ≥50 trials, serial; 500ms post-amend wait + `_verify_aux_price` against `broker._ib.openTrades()` |
| **B (i)** | Concurrent amends across N≥3 positions (open 3+, fire `modify_order` via `asyncio.gather()`) | ≥30 trials × ≥3 positions per trial; rejection counts contribute one event per amend |
| **B (ii)** | Amends during Gateway reconnect window — operator-orchestrated | up to ≥30 amends fired every ~500ms during the window; resumes on `RECONNECTED` stdin sentinel |
| **B (iii)** | Amends with stale order IDs (cancel a stop, then `modify_order` against the cancelled ULID) | ≥30 trials, serial |
| **B (iv)** | Joint reconnect+concurrent — operator-orchestrated | up to ≥30 concurrent-amend rounds × ≥3 positions during the window |
| **C** | H1 `cancel_all_orders(symbol, await_propagation=True)` round-trip latency | ≥50 trials, serial |
| **D** | N=100 cancel-then-immediate-SELL HARD GATE per Decision 2 | exactly 100 trials; conflict classifier inspects sell-result + post-positions for OCA, locate, position-state, gap-too-large signatures |

Wilson 95% upper-confidence bound computed per axis; `worst_axis_wilson_ub` is the maximum across the 4 axes (NOT mean/median — explicit per `_apply_decision_rule`). Decision rule reproduces the H-R2-2-tightened gate verbatim from the implementation prompt.

The script defaults to symbols `SPY,QQQ,IWM,XLF` for liquidity (none in ARGUS scanner). Operator may override via `--symbols`. Minimum 3 symbols enforced for axes (i) + (iv).

---

## Judgment Calls

1. **Script LOC ~998 vs prompt's "~280 LOC" directional estimate.** The four measurement modes (with two operator-orchestrated axes), the deterministic-propagation verification path, the conflict-signature classifier for Mode D, and the Wilson-UB-driven decision rule + JSON aggregator together demand more code than the reference (`spike_ibkr_oca_late_add.py` was 604 LOC for a 3-trial state machine). Per the prompt's load-bearing escape-hatch language ("explicitly authorized to deviate from the spec-prescribed measurement modes when an operational constraint warrants it"), the LOC delta is functional rather than scope-expansion. RULE-038 directional-estimate disclosure: `~280` was directional, actual is ~3.5×. Surfaced here.

2. **Mode B axis (ii) + (iv) operator-orchestration model.** The implementation prompt acknowledges these are operator-orchestrated. The script implements a single pause-and-prompt-stdin pattern per axis: (a) open the position(s) before prompting; (b) print a banner instructing the operator to disconnect IBKR Gateway; (c) loop firing amends every ~500ms until the operator types `RECONNECTED` + Enter on stdin; (d) cleanup. This compresses the "disconnect → many trials → reconnect" cycle into one Gateway-bounce per axis rather than ≥30 separate bounces, which is operationally tractable. The operator should expect to type `RECONNECTED` exactly twice across the full spike run.

3. **Private-attribute access in the spike (`broker._ib`, `broker._ulid_to_ibkr`, `broker._contracts`).** The deterministic-propagation check needs to query `openTrades()` and compare `auxPrice` directly; the spike connects this via `broker._ib.openTrades()`. This is a deliberate spike-only convenience and is forbidden in production code. The script docstring + comments mark these accesses explicitly. Production code under `argus/` does not change.

4. **Mode D conflict classifier — `cancel_to_sell_gap > 50ms` as a soft conflict.** The prompt requires the gap to be ≤10ms by design; reaching >50ms in practice means the cancel-await did not return promptly enough for the immediate-SELL semantics to be exercised, so the trial cannot falsify zero-conflict cleanly. Recording it as a conflict tightens the HARD GATE in the operator's favor. If the operator observes `cancel_to_sell_gap_too_large` as the dominant conflict signature in the spike output, that surfaces the more architectural concern (`cancel_all_orders` polling cadence in the broker, not H1 itself).

5. **`selected_mechanism == "h1_cancel_and_await"` operator-confirmation gate.** Per Requirement 5, if H1 is selected the operator's written confirmation is REQUIRED before S2a/S2b prompts may be generated. The script prints a banner reminder when H1 is selected and sets exit code to `0` (the gate is not enforced in code — it is a procedural requirement on the prompt-generation pipeline). Surfaced here so the operator does not miss it.

---

## Scope Verification

| Constraint | Verification |
|-----------|--------------|
| `git diff HEAD -- argus/` empty | `git status --short` shows ONLY `scripts/spike_def204_round2_path1.py` (and the unrelated path2 spike, untracked, out of S1a scope). |
| `git diff HEAD -- frontend/` empty | Same; frontend untouched. |
| `git diff HEAD -- tests/` empty | Same; tests untouched. |
| Vitest count = 913 | No frontend changes; baseline assumed unchanged. |
| Pytest count = baseline (5,269 / 5,279 per CLAUDE.md disclosure) | Pre-session running in background; result below. |
| DEC-385/386/388 surfaces unmodified | `argus/` not in diff at all. |
| No new pytest markers added | None added; no marker-validation needed. |
| No new config fields added | None added. |

The CLAUDE.md preamble notes Sprint 31.915 lifted the pytest baseline to **5,279** (DEF-231/232/233/234 added 10 new tests). The implementation prompt cites 5,269 as the baseline because the prompt was authored before Sprint 31.915 sealed. Per RULE-038 disclosure: re-measurement is authoritative; the live baseline is 5,279, NOT the 5,269 cited in the prompt. The "5,269 expected" line in the regression checklist is stale and must be read as "current baseline" instead.

---

## Test Results

Full suite ran in background during close-out authoring. Output captured separately; result attached in §"Close-Out Test Run" below.

The spike adds **zero** pytest tests (per Requirement; per Test Targets section of the implementation prompt). The validation surface is the JSON artifact's required-keys schema, which is verified by the operator after spike execution via the regression-checklist commands — NOT by pytest assertions.

Dry-run validation (no IBKR connection): `python scripts/spike_def204_round2_path1.py --account U24619949 --dry-run --symbols SPY,QQQ,IWM` → exit 0, log "DRY RUN — script structure validated, no IBKR connection made".

---

## Definition of Done — Per-Item Status

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Script exists (~280 LOC) and matches reference shape | **MET** | 998 LOC; deviation disclosed in Judgment Calls #1 |
| 2 | Script runs against paper IBKR Gateway → exit code | **PENDING-OPERATOR** | Non-safe-during-trading; operator must run pre-market or after-hours |
| 3 | JSON artifact has all 14 REQUIRED keys + `status: "PROCEED"` | **PENDING-OPERATOR** | Cannot exist without spike-run |
| 4 | If H1 selected: operator written confirmation captured | **CONDITIONAL-PENDING** | Trips only if spike outputs `h1_cancel_and_await`; banner reminder printed by script |
| 5 | `adversarial_axes_results` has all 4 axis keys with non-null `wilson_upper_bound_pct` | **PENDING-OPERATOR** | Verifiable post-run via regression-checklist command |
| 6 | `h1_propagation_n_trials == 100` HARD GATE | **PENDING-OPERATOR** | Default arg value is 100; deviation warning fires at log-level if operator overrides |
| 7 | Full pytest suite at 5,269 (or current 5,279 baseline) | **MET** (pending background-run completion below) | Spike adds zero pytest |
| 8 | CI green on session's final commit | **PENDING-OPERATOR** | After commit + push |
| 9 | Close-out report written to file | **MET** | This file |
| 10 | Tier 2 review @reviewer subagent + verdict CLEAR | **DEFERRED** | Cannot complete without JSON artifact (Definition-of-Done item 3); operator invokes after spike-run |

---

## Operator-Orchestrated Next Steps

The session ends at the boundary of what can be done without paper IBKR Gateway access. To close out the full Definition of Done, the operator must:

1. **Schedule a paper-hours window** (pre-market 04:00–09:00 ET or after-hours 16:00–20:00 ET; market must be CLOSED per non-safe-during-trading constraint).
2. **Verify paper Gateway accessible** at `127.0.0.1:4002`, account `U24619949`, clientId=1 free for the spike.
3. **Run the spike:**
   ```bash
   python scripts/spike_def204_round2_path1.py \
       --account U24619949 \
       --client-id 1 \
       --symbols SPY,QQQ,IWM,XLF \
       --num-trials-per-axis 50 \
       --n-stress-trials 100 \
       --output-json scripts/spike-results/spike-def204-round2-path1-results.json
   ```
4. **Be at the terminal during axes (ii) and (iv)** — the script prints a banner and pauses for `RECONNECTED` + Enter on stdin after a Gateway disconnect/reconnect cycle. Expect two such prompts across the run.
5. **Verify the JSON output** against the regression-checklist commands in the implementation prompt (14 required keys; `status: "PROCEED"`; `h1_propagation_n_trials == 100`; `adversarial_axes_results` has all 4 axis keys; spike artifact dated within last 24 hours).
6. **If `selected_mechanism == "h1_cancel_and_await"`:** record written confirmation per the existing tightened gate language before S2a/S2b prompts are generated. Surface to operator review.
7. **Commit the script + JSON artifact + close-out**, push to `main`, and verify CI green.
8. **Invoke the @reviewer subagent for Tier 2 review** — pass the review-context file, this close-out, and the diff range. The reviewer's checklist (Session-Specific Review Focus items 1–7) becomes evaluable once the JSON exists.

If the spike returns `status: INCONCLUSIVE`: **A-class halt A1 fires** — operator arranges Tier 3 review of an alternative mechanism before any S2a/S2b prompt is generated. Do not proceed under INCONCLUSIVE.

---

## Self-Assessment: FLAGGED

**Why FLAGGED, not CLEAN:**

- Per RULE-011, MINOR_DEVIATIONS or FLAGGED is required if any scope item was skipped, modified, or reinterpreted.
- The session does not produce the JSON artifact (a Definition-of-Done item). That gap is structurally unavoidable without paper IBKR Gateway access during a market-closed window.
- The Tier 2 review item is deferred for the same reason — its checklist depends on the JSON existing.
- The script LOC overshoot (~998 vs ~280) is a directional-estimate deviation per RULE-038.

**What CLEAN would have looked like:**

The script would have been ~280 LOC, the spike would have run during this session, the JSON artifact would have been emitted with `status: "PROCEED"`, the @reviewer would have produced a CLEAR verdict, and the session would have committed all three artifacts. None of those are achievable without paper-Gateway access; FLAGGED is the honest record.

---

## Close-Out Test Run

Full pytest suite ran against the spike-only diff (no production code changed):

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q
# 5279 passed, 39 warnings in 69.05s (0:01:09)
```

**Result: 5,279 passed.** Matches live baseline post-Sprint 31.915 (DEF-231/232/233/234 added 10 tests vs the prompt's stale 5,269 reference). Spike-only diff confirmed: zero pytest delta, zero new flakes. The 39 warnings include pre-existing DEF-192 (xdist resource-warning cluster) and DEF-201 (observatory_ws aiosqlite cross-loop transient) — both unchanged from baseline.

Pre-existing flake check: passes. No new flakes; no DEF-150 / DEF-167 / DEF-171 / DEF-190 / DEF-192 surfaced as failures (all pass under `-n auto` on this run). Sprint-level invariant 11 holds.

Sprint-level invariant 10 holds (5,279 ≥ baseline 5,279).
Sprint-level invariant 12 holds (zero diff under `frontend/`; Vitest count = 913 unchanged).
Sprint-level invariant 18 PENDING-OPERATOR-EXECUTION (spike artifact must be generated by operator).

---

```json:structured-closeout
{
  "session_id": "sprint-31.92-s1a",
  "self_assessment": "FLAGGED",
  "context_state": "GREEN",
  "judgment_calls": [
    "Script LOC ~998 vs prompt directional estimate ~280 (RULE-038 deviation disclosure; functional, not scope-expansion).",
    "Mode B axis (ii) + (iv) implemented as a single pause-and-prompt-stdin loop per axis (one Gateway-bounce per axis instead of 30).",
    "Private-attribute access in spike (broker._ib, broker._ulid_to_ibkr, broker._contracts) for deterministic-propagation verification — spike-only, production code unchanged.",
    "Mode D conflict classifier records cancel_to_sell_gap > 50ms as a conflict signature even though prompt's hard upper-bound is 10ms; tightens the gate in the operator's favor.",
    "selected_mechanism == h1_cancel_and_await requires operator written confirmation per tightened gate language (script prints banner reminder; not enforced in code).",
    "Pytest baseline cited as 5269 in the prompt is stale; live baseline is 5279 post-Sprint 31.915 per CLAUDE.md (RULE-038 re-measurement disclosure). Spike adds zero tests so baseline holds either way.",
    "Sprint-seal grep pattern in prompt did not literal-match commit messages; seals verified via commit-history inspection (210d2f9 / 15f6746 / f42e25c). RESOLVED-VERIFIED."
  ],
  "scope_violations": [],
  "deferred_items": [
    "Spike must be RUN by operator during paper-hours window (non-safe-during-trading; requires paper IBKR Gateway + market-CLOSED).",
    "JSON artifact scripts/spike-results/spike-def204-round2-path1-results.json autogenerated by the spike — pending operator execution.",
    "Tier 2 @reviewer review pending JSON artifact existence (Session-Specific Review Focus items 1–7 require the JSON).",
    "Operator written confirmation if selected_mechanism == h1_cancel_and_await."
  ],
  "artifacts": [
    "scripts/spike_def204_round2_path1.py",
    "scripts/spike-results/spike-def204-round2-path1-results.json",
    "docs/sprints/sprint-31.92-def-204-round-2/session-1a-closeout.md"
  ],
  "definition_of_done_status": {
    "script_exists": "MET",
    "script_runs_against_paper_gateway": "PENDING-OPERATOR",
    "json_artifact_with_14_keys_and_status_proceed": "PENDING-OPERATOR",
    "h1_operator_confirmation_if_selected": "CONDITIONAL-PENDING",
    "adversarial_axes_results_4_keys": "PENDING-OPERATOR",
    "h1_propagation_n_trials_eq_100": "PENDING-OPERATOR",
    "pytest_baseline_unchanged": "MET",
    "ci_green_on_final_commit": "PENDING-OPERATOR",
    "closeout_written_to_file": "MET",
    "tier_2_reviewer_verdict_clear": "DEFERRED"
  },
  "sprint_level_invariants": {
    "10_test_count_baseline_holds": "MET (5279 passed; live baseline 5279)",
    "11_pre_existing_flake_count_unchanged": "MET (39 warnings, all pre-existing DEF-192/DEF-201; zero new failures)",
    "12_frontend_immutability": "MET (zero diff under frontend/)",
    "18_spike_artifact_committed_and_fresh": "PENDING-OPERATOR-EXECUTION"
  },
  "selected_mechanism": null,
  "selected_mechanism_reason": "Spike not yet run; selection is contingent on operator-executed paper-Gateway measurements per Hypothesis Prescription decision rule."
}
```
