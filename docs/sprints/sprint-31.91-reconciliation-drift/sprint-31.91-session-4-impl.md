# Sprint 31.91, Session 4: Mass-Balance Categorized + IMSR Replay + Spike Script Freshness + Live-Enable Gate

> **Track:** Validation infrastructure (single-session). Validates all prior sessions; gates the pre-live transition.
> **Position in sprint:** Last backend-safety-track session before the alert-observability track (5a.1+). All prior reconciliation + DEF-158 work is on `main` by Session 4's start.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full.** RULE-038, RULE-050, RULE-019, RULE-007.

2. Read these files to load context:
   - `logs/argus_20260424.jsonl` (operator-supplied; verify available at the path; the IMSR replay test depends on this file existing)
   - `argus/backtest/engine.py` — BacktestEngine entry point (the IMSR replay re-runs through it with post-fix code)
   - `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` — IMSR forensic timeline (reference only; understand what the post-fix replay should produce)
   - `docs/pre-live-transition-checklist.md` — current structure (Session 4 expands the live-enable gate criteria per HIGH #4)
   - `docs/protocols/market-session-debrief.md` — current 7-phase structure (Session 4 adds slippage watch to Phase 7)
   - `docs/live-operations.md` — current structure (Session 4 adds B28 spike trigger registry)
   - `scripts/spike_ibkr_oca_late_add.py:50, :506` — Item 7 line references (filename convention fix)
   - `docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md` invariant 22 — Item 7 third surgical fix
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` D7 — Session 4 acceptance criteria
   - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-D-OPEN-ITEMS.md` Items 1, 4, 7 — Phase D folded-in additions for this session

3. Run the scoped test baseline:

   ```
   python -m pytest tests/integration/ tests/scripts/ -n auto -q
   ```

4. Verify branch: **`main`**.

5. **Pre-flight: verify `logs/argus_20260424.jsonl` exists and is readable.**

   ```bash
   ls -la logs/argus_20260424.jsonl
   wc -l logs/argus_20260424.jsonl  # expect thousands of lines for a paper-trading session
   ```

   If the file is missing, **HALT** — Session 4 cannot proceed without the real IMSR replay artifact (per H4 disposition: no synthetic fallback). Operator must restore the file before Session 4 starts.

6. **Pre-flight (Item 1 — IMPROMPTU-04 row #4 current-consumer grep verification, MEDIUM #6):**

   ```bash
   grep -rn 'debrief_export\|debrief_csv' argus/ frontend/src/ \
     --include='*.py' --include='*.ts' --include='*.tsx' \
     | grep -v '^analytics/debrief_export.py:'
   ```

   For each consumer found:
   - **If consumer uses the data for decision-making** (e.g., `if pnl > threshold`, gating logic, alert emission, position sizing), **flag for in-sprint expansion of the fix to preserve `Position.side` through the export** — halt Session 4 and escalate.
   - **If consumer is display-only** (Debrief page UI, AI insight cards consuming for visualization, DailySummaryGenerator narrative text), **document in Session 4 close-out's "Discovered Edge Cases" section** with one line per consumer. No code change in this session.

   The goal is to confirm DEF-209's "FUTURE consumers" framing is correct — i.e., NO current consumer makes side-dependent decisions that would silently break under side-stripped CSVs. If a current consumer DOES make such decisions, that's an out-of-scope discovery requiring escalation.

7. **Pre-flight (Item 7 — spike script filename three-way mismatch):**

   ```bash
   ls scripts/spike-results/ 2>/dev/null
   grep -n "spike-results-" scripts/spike_ibkr_oca_late_add.py | head -10
   grep -n "spike-results-\|fromisoformat" docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md
   ```

   Confirm the three-way convention mismatch (Unix epoch in `:506` default, ISO with dashes in `:50` docstring, compact date in invariant 22 parser). The target convention is **ISO with dashes** (`spike-results-YYYY-MM-DD.json`) — Session 4 fixes all three sources.

## Objective

Session 4 produces three categories of validation infrastructure, all gated on prior-session deliverables:

- **Mass-balance categorized variance script** (`scripts/validate_session_oca_mass_balance.py`) consumes `logs/argus_YYYYMMDD.jsonl` and produces a 3-category variance report per H2 + Item 4 precedence rules. Exit 0 if zero `unaccounted_leak`; exit 1 otherwise. The script is the operator's primary "did this session leak?" forensic tool.
- **IMSR replay test** (`tests/integration/test_imsr_replay.py`) replays the real Apr 24 log through BacktestEngine with post-fix code; asserts EOD position is 0 (not the −200 the original session produced). H4 disposition: NO synthetic fallback; if the real log is missing, the test errors. This is the structural verification that the prior 31.91 work fixes the IMSR scenario.
- **Documentation updates** for live-enable gating (HIGH #4 decomposed criteria), spike script trigger registry (HIGH #5 / B28), Phase 7 slippage watch (D8 acceptance), and Item 7 spike-script filename standardization.

DEF-208 (Adversarial #1: live-trading test fixture missing) and DEF-209 (debrief_export side-stripping for FUTURE consumers) are filed as deferred items and tracked in `CLAUDE.md`.

## Requirements

### Part 1: Mass-Balance Script (`scripts/validate_session_oca_mass_balance.py`)

Create the script with this docstring header (verbatim — Item 4's specification):

```python
#!/usr/bin/env python3
"""validate_session_oca_mass_balance.py — categorized variance report

Sprint 31.91 D7 (mass-balance) + PHASE-D-OPEN-ITEMS Item 4 (precedence).

Categorization rules (precedence order, strongest evidence wins):

1. expected_partial_fill: a SELL was placed (order_id known) and
   broker reports same-quantity fill OR working order outstanding.
2. eventual_consistency_lag: ARGUS-side accounting lags broker-side
   by ≤2 reconciliation cycles (≤120s; one cycle for snapshot,
   one for propagation).
3. unaccounted_leak: shares in broker SELL stream not attributable
   to either of the above. FLAG and exit non-zero.

Precedence: when a row could fit multiple categories, classify into
the strongest-evidence category:
  expected_partial_fill > eventual_consistency_lag > unaccounted_leak

Known-gap registry (rows that should NOT be flagged):
  - IMSR pending=None case: fill callback with no _pending_orders entry
    → classify as unaccounted_leak unless DEF-XXX reference is logged
    in the row's "notes" field. Prevents silent classification drift.

Cross-session boundary handling: filter logs by session-id (extract
from log timestamp range against pre-loaded sessions table). Reject
rows that span session boundaries with reason="boundary_ambiguous".

Usage:
    python scripts/validate_session_oca_mass_balance.py logs/argus_YYYYMMDD.jsonl

Exit codes:
    0 — zero unaccounted_leak rows; session is clean
    1 — one or more unaccounted_leak rows; session has unexplained variance
    2 — input file missing or unparseable
"""
```

Implementation:

- Argument parsing: `argparse` for the input log file path.
- Read JSONL line-by-line; filter to events relevant to mass balance: order placement, fill callbacks, reconciliation cycle outputs, EOD flatten events.
- For each broker SELL event in the log, walk the precedence categorization:
  1. **`expected_partial_fill`:** the event has a matching `order_id` in the same session's order-placement events; quantity matches or working-order metadata explains the partial.
  2. **`eventual_consistency_lag`:** the event lacks an `order_id` match BUT a reconciliation cycle within 120s (≤2 cycles) of the event timestamp shows ARGUS-side state catching up.
  3. **`unaccounted_leak`:** the event matches neither. FLAG.
- Cross-session boundary handling: extract session-id from log timestamp range; reject events spanning boundaries with `reason="boundary_ambiguous"` (do NOT silently flag as unaccounted_leak).
- IMSR pending=None case: a fill callback with no `_pending_orders` entry → flag as `unaccounted_leak` UNLESS the row's "notes" field contains a `DEF-XXX` reference (operator-acknowledged known gap).
- Output: print categorized report to stdout; one line per row; summary count at the end. Exit code per spec.

Output format (suggested):

```
== Mass-Balance Variance Report (Apr 24 2026 session) ==
expected_partial_fill: 12 rows
eventual_consistency_lag: 3 rows
unaccounted_leak: 0 rows  ← session is clean
boundary_ambiguous: 0 rows
known_gaps_acknowledged: 1 row (DEF-178 reference)

Exit code: 0
```

### Part 2: IMSR Replay Integration Test

Create `tests/integration/test_imsr_replay.py`:

```python
"""IMSR (Sprint 31.9 IMPROMPTU-11) replay regression test.

Sprint 31.91 D7 / H4 disposition: replay the real Apr 24 2026 paper-
trading session log through BacktestEngine harness with post-fix code;
assert IMSR EOD position is 0 (not -200 as the original session ended).

NO synthetic-recreation fallback. If logs/argus_20260424.jsonl is
missing, this test errors (not skips) — the file is operator-supplied
and required for sprint sign-off.
"""

import json
import pytest
from pathlib import Path

LOG_PATH = Path("logs/argus_20260424.jsonl")


@pytest.fixture(scope="module")
def imsr_replay_log() -> list[dict]:
    if not LOG_PATH.exists():
        pytest.fail(
            f"IMSR replay log missing at {LOG_PATH}. Sprint 31.91 H4 "
            f"disposition: NO synthetic fallback; operator must restore "
            f"the real Apr 24 paper-session log before Session 4 ships."
        )
    with LOG_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def test_imsr_replay_with_post_fix_code_position_zero_at_eod(imsr_replay_log):
    """H4 disposition. Replay through BacktestEngine; assert IMSR EOD = 0."""
    # 1. Initialize BacktestEngine with post-31.91 code (the engine
    #    is on `main`; this test runs against current code).
    # 2. Replay the log events through the engine harness.
    # 3. At EOD, query the engine's position state for IMSR.
    # 4. Assert position is 0.
    # ... implementation specific to BacktestEngine API ...
    from argus.backtest.engine import BacktestEngine

    engine = BacktestEngine(...)  # use existing harness pattern; verify API
    for event in imsr_replay_log:
        engine.process_event(event)  # or whatever the replay entry point is

    eod_position = engine.get_position_at_eod("IMSR")
    assert eod_position == 0, (
        f"IMSR EOD position post-replay should be 0 (post-fix); got "
        f"{eod_position}. Original Apr 24 session ended at -200 (the bug). "
        f"If this assertion fails, Sprint 31.91's reconciliation contract "
        f"refactor + broker-orphan branch is NOT closing the IMSR scenario."
    )
```

Notes:
- The `BacktestEngine` API integration is project-specific. Read `argus/backtest/engine.py` to determine the exact replay entry point. Per RULE-007, do NOT introduce a new harness — reuse the existing one.
- The test is in `tests/integration/` (NOT `tests/unit/`) because it depends on a real artifact and is slow.

### Part 3: Mass-Balance Script Tests (~5 new + Item 4's 3)

1. **`test_mass_balance_script_clean_session_zero_unaccounted_leak_exits_0`** (H2)
2. **`test_mass_balance_script_categorizes_expected_partial_fill_no_flag`** (H2)
3. **`test_mass_balance_script_categorizes_eventual_consistency_lag_no_flag`** (H2)
4. **`test_mass_balance_script_unaccounted_leak_exits_1`** (H2)
5. **`test_mass_balance_precedence_partial_fill_wins_over_lag`** (Item 4)
6. **`test_mass_balance_session_boundary_rejection`** (Item 4)
7. **`test_mass_balance_imsr_pending_none_classified_unaccounted_unless_def_referenced`** (Item 4)

Use synthetic JSONL fixtures (small, hand-crafted log files in `tests/fixtures/mass_balance/*.jsonl`); these tests do NOT consume the real Apr 24 log (that's Test 8 below).

### Part 4: IMSR Replay Test (Test 8)

8. **`test_imsr_replay_with_post_fix_code_position_zero_at_eod`** (H4 — uses real Apr 24 log; defined above in Part 2)

### Part 5: Documentation Updates

#### 5a. `docs/pre-live-transition-checklist.md` — Decomposed Live-Enable Gate (HIGH #4)

Replace the existing "Live-enable readiness" section (or wherever the gating criteria currently live) with:

```markdown
## Live-Enable Gate Criteria (Sprint 31.91 — decomposed per HIGH #4)

ARGUS may be transitioned from paper to live trading ONLY when ALL of the
following criteria are met:

### Gate 1 — Multi-session paper validation
**≥3 consecutive paper-trading sessions with both:**
- Zero `unaccounted_leak` rows in `validate_session_oca_mass_balance.py` output
- Zero `phantom_short` alerts (any source: reconciliation, EOD Pass 2, Health, startup)

### Gate 2 — Pre-live paper stress test (Gate 3a per spec D7)
**≥1 paper-trading session under live-config simulation:**
- Paper-trading data-capture overrides removed
- Risk limits restored to production values
- Overflow capacity restored
- ≥10 entries placed during the session (sufficient activity for confidence)
- Zero `phantom_short` alerts
- Zero `unaccounted_leak` mass-balance rows
- Zero `phantom_short_retry_blocked` alerts

### Gate 3 — Live rollback policy (Gate 3b per spec D7)
**First live trading session caps:**
- Position size: $50–$500 notional
- Single operator-selected symbol
- Any `phantom_short*` or `phantom_short_retry_blocked` alert during the
  session triggers immediate suspension via operator-manual halt
  (formal `POST /api/v1/system/suspend` deferred — DEF-210)

After session-end clean (zero alerts; mass-balance clean), expand to
standard sizing on day 2.

### Note on disconnect-reconnect testing
Disconnect-reconnect resilience testing is **deferred to Sprint 31.93**
and is NOT a Sprint 31.91 live-enable gate criterion.
```

#### 5b. `docs/protocols/market-session-debrief.md` Phase 7 — Slippage Watch (D8 acceptance)

Add to Phase 7 (the existing diagnostic phase or a new sub-phase):

```markdown
### Phase 7.X — Bracket-stop slippage check (Sprint 31.91 D8 acceptance)

Compare mean bracket-stop fill slippage on $7-$15 share universe against
pre-31.91 baseline. Threshold: ≤$0.02 degradation.

If degradation exceeds $0.02:
1. Trigger restart-required rollback evaluation per `live-operations.md`
   (the `bracket_oca_type: 0` config flip is restart-required per H1).
2. Investigate whether ocaType=1's 50–200ms cancellation propagation cost
   is producing bracket-stop fills at worse prices than the pre-31.91
   ocaType=2 architecture.
3. Document findings; decide whether rollback is warranted.
```

#### 5c. `docs/live-operations.md` — B28 Spike Script Trigger Registry (HIGH #5)

Add a new section "Spike Script Trigger Registry" with this content:

```markdown
## Spike Script Trigger Registry (Sprint 31.91 HIGH #5 / B28)

`scripts/spike_ibkr_oca_late_add.py` validates the OCA-architecture
behavior against the live IBKR API. Re-run the spike under any of the
following conditions; failure to return `PATH_1_SAFE` invalidates the
OCA-architecture seal and triggers Tier 3 architectural review.

### Re-run triggers
1. **Before any live-trading transition** (one of the live-enable gates).
2. **Before AND after any `ib_async` library version upgrade.**
3. **Before AND after any IBKR API version change** (TWS/Gateway upgrade).
4. **Monthly during paper-trading windows** — ensures no silent IBKR-side
   API behavior drift between live-enable transitions.

### Spike result file format
- Filename: `spike-results-YYYY-MM-DD.json` (ISO date with dashes)
- Location: `scripts/spike-results/`
- Freshness: file must be dated within the last 30 days when in
  paper-trading mode (enforced by regression invariant 22)

### Failure response
- Spike returns NOT `PATH_1_SAFE` → OCA-architecture seal INVALIDATED.
- Halt all live-trading preparation; trigger Tier 3 architectural review.
- Document the failure mode in the result file's `failure_reason` field.

### Cross-reference
- Spike script: `scripts/spike_ibkr_oca_late_add.py`
- Path safety analysis: `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-A-REVISIT-FINDINGS.md`
- Regression invariant: `docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md` invariant 22
```

### Part 6: Item 7 — Spike Script Filename Standardization (3 surgical fixes + 2 tests)

Three surgical edits + two tests:

#### Fix 1: `scripts/spike_ibkr_oca_late_add.py:506` — default output

```python
# BEFORE:
out_path = args.output or f"spike-results-{int(time.time())}.json"

# AFTER:
import datetime
out_dir = "scripts/spike-results"
os.makedirs(out_dir, exist_ok=True)
out_path = args.output or os.path.join(
    out_dir, f"spike-results-{datetime.date.today().isoformat()}.json"
)
```

#### Fix 2: `scripts/spike_ibkr_oca_late_add.py:50` — docstring example

If the docstring example currently shows ISO-with-dashes already, no fix needed (it's the target convention). If different, update to `spike-results-2026-04-27.json`.

#### Fix 3: `regression-checklist.md` invariant 22 — date parser

```python
# BEFORE (compact YYYYMMDD parsing):
date_str = latest[len("spike-results-"):-len(".json")]
latest_date = datetime.date.fromisoformat(
    f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
)

# AFTER (ISO-with-dashes parsing — direct):
date_str = latest[len("spike-results-"):-len(".json")]
latest_date = datetime.date.fromisoformat(date_str)
```

#### Item 7 Tests

9. **`test_spike_script_default_output_is_iso_date_in_spike_results_dir`**
   - Run `python scripts/spike_ibkr_oca_late_add.py --dry-run` (or whatever flag exists for not actually placing IBKR orders); assert the default output path is `scripts/spike-results/spike-results-YYYY-MM-DD.json` matching today's date.

10. **`test_invariant_22_date_parser_handles_iso_format_with_dashes`**
    - Construct test fixtures: `spike-results-2026-04-25.json` (ISO with dashes); assert the date parser extracts `date(2026, 4, 25)` correctly.

### Part 7: File DEF-208 + DEF-209

In `CLAUDE.md`, add to the "Open DEFs" section (or wherever DEF tracking lives):

- **DEF-208** — Adversarial review #1 finding: live-trading test fixture missing (the existing test suite has no live-trading harness; gating live transition requires a fixture that simulates the live config + risk limits without actual IBKR connectivity). Track for Sprint 31.92 or 31.93.
- **DEF-209** — Future consumer protection for `analytics/debrief_export.py:336` side-stripping: when Learning Loop V2 (Sprint 35+) consumes the debrief CSV for decision-making, the side stripping must be lifted (or a new side-preserving export path added). Current consumers (Item 1 verification) are display-only; FUTURE consumers need this fix. Track for Sprint 35+.

## Definition of Done

- [ ] `scripts/validate_session_oca_mass_balance.py` exists; produces categorized variance report; H2 + Item 4 precedence rules implemented; cross-session boundary handling; IMSR pending=None known-gap handling.
- [ ] Mass-balance script returns exit 0 if zero `unaccounted_leak`; non-zero otherwise.
- [ ] `tests/integration/test_imsr_replay.py` created; consumes real `logs/argus_20260424.jsonl`; asserts IMSR EOD position = 0 post-replay.
- [ ] 7 mass-balance tests + 1 IMSR replay test + 2 spike-filename tests = 10 new tests (some Phase D Items folded in beyond the 5 spec'd).
- [ ] `docs/pre-live-transition-checklist.md` decomposed live-enable gate criteria added (Gates 1, 2, 3 per HIGH #4 + spec D7).
- [ ] `docs/protocols/market-session-debrief.md` Phase 7 slippage watch added.
- [ ] `docs/live-operations.md` B28 spike trigger registry added.
- [ ] `scripts/spike_ibkr_oca_late_add.py` filename convention standardized (ISO with dashes; output dir `scripts/spike-results/`).
- [ ] `regression-checklist.md` invariant 22 date parser updated.
- [ ] DEF-208, DEF-209 filed in `CLAUDE.md`.
- [ ] Item 1 (debrief_export consumer grep) verified; results documented in close-out.
- [ ] CI green; pytest baseline ≥ 5,159 (5,149 entry + 10 new tests).
- [ ] All do-not-modify list items show zero `git diff`.
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-4-closeout.md`.

## Close-Out Report

Standard structure. Verdict JSON:

```json
{
  "session": "4",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 10,
  "tests_total_after": <fill>,
  "files_created": [
    "scripts/validate_session_oca_mass_balance.py",
    "tests/integration/test_imsr_replay.py"
  ],
  "files_modified": [
    "docs/pre-live-transition-checklist.md",
    "docs/protocols/market-session-debrief.md",
    "docs/live-operations.md",
    "scripts/spike_ibkr_oca_late_add.py",
    "docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md",
    "CLAUDE.md"
  ],
  "phase_d_items_folded_in": ["Item 1", "Item 4", "Item 7"],
  "defs_filed": ["DEF-208", "DEF-209"],
  "donotmodify_violations": 0
}
```

In "Discovered Edge Cases":
- Document Item 1's grep results: list each `debrief_export` consumer found and classify display-only vs decision-making.
- Cite the IMSR replay assertion result (was it 0? was it -200? if the test failed, that's a mechanism failure that escalates).
- Cite the mass-balance script's exit code on the Apr 24 log (probably exit 0 for a clean session).

## Tier 2 Review Invocation

Standard pattern. Backend safety reviewer template. Review report at `session-4-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **H2 categorization definitions precise.** Reviewer reads the script docstring (the verbatim Item 4 specification block) and confirms:
   - Three categories with precedence: `expected_partial_fill > eventual_consistency_lag > unaccounted_leak`.
   - 120s eventual-consistency window is ≤ 2 reconciliation cycles (the bound is operationally documented).
   - Cross-session boundary handling rejects spanning rows (does not silently flag as `unaccounted_leak`).
   - IMSR pending=None known-gap handling reads the row's "notes" field for `DEF-XXX` references.

2. **IMSR replay test runs against real log (not synthetic).** Reviewer confirms:
   - The `pytest.fail(...)` (not `pytest.skip`) when the file is missing — H4 disposition is no synthetic fallback.
   - The replay loops through every event in the real log.
   - The EOD position assertion is `== 0`, not `>= 0` (the original session ended at -200; assertion of `== 0` is the structural fix verification).

3. **Live-enable gate criteria unambiguous and verifiable.** Each gate criterion is operationally testable:
   - Gate 1: count of paper sessions; mass-balance exit code; alert log inspection. Verifiable.
   - Gate 2: live-config simulation has 5 sub-criteria (overrides removed, risk limits restored, overflow restored, ≥10 entries, zero alerts). Each is verifiable.
   - Gate 3: position size cap + symbol selection are operational settings; alert-triggered halt is a documented procedure (DEF-210 deferred).

4. **Phase 7 slippage watch item clear.** The threshold ($0.02) and rollback path (restart-required `bracket_oca_type: 0`) are both documented. Reviewer confirms the rollback documentation cross-references `docs/live-operations.md` H1 RESTART-REQUIRED rollback.

5. **Item 1 verification documented.** Reviewer reads "Discovered Edge Cases" and confirms each `debrief_export` consumer is classified display-only or decision-making. Any decision-making consumer = ESCALATE per pre-flight instruction.

6. **Item 7 three surgical fixes consistent.** Reviewer greps `spike-results-` across the codebase and confirms ISO-with-dashes is the only convention remaining:
   ```bash
   grep -rn 'spike-results-' .
   ```
   No Unix epoch references; no compact-date parser; everything points to `spike-results-YYYY-MM-DD.json`.

7. **DEF-208 + DEF-209 filed.** Reviewer reads `CLAUDE.md`'s Open DEFs section and confirms both entries are present with the descriptions above.

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 5:** PASS — expected ≥ 5,159.
- **Invariant 22 (spike-results freshness):** updated parser; verify backward-compatibility on transition.
- **Invariant 14:** Row "After Session 4" — Mass-balance validated = YES; Recon detects shorts = full; DEF-158 retry = YES.
- **Invariant 15:** PASS — no scoped exceptions.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A5** (IMSR replay test fails — the structural fix did not actually close the IMSR scenario).
- **A6** (Item 1 grep finds a current decision-making consumer of debrief_export — the side-stripping issue is not future-only as DEF-209 frames it).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (Apr 24 log not available — H4 disposition halts; do not synthesize).

---

*End Sprint 31.91 Session 4 implementation prompt.*
