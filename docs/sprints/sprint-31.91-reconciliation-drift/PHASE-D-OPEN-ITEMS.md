# Sprint 31.91: Phase D Open Items

> **Phase C → Phase D bridge artifact.** Captures third-pass adversarial
> review MEDIUM/LOW findings that were intentionally deferred to Phase D
> implementation-prompt level (per the reviewer's gradient: HIGH at Phase
> B/C; MEDIUM/LOW at Phase D prompts or in-flight amendments). This list
> exists so nothing is silently dropped during the 7–8 week sprint
> execution.
>
> Companion: `adversarial-review-input-package.md` §10.5;
> `sprint-spec.md`; `session-breakdown.md`.

## Why this file exists

The third-pass review surfaced 14 MEDIUM/LOW findings beyond the 5 HIGH.
Of those:
- **6 were addressed at Phase C artifact level** (#9, #10, #11, #13, #15,
  #17 — see Adversarial Review Input Package §10.2 disposition table)
- **2 were filed as new DEFs** (#14 → DEF-211; HIGH #4 part → DEF-210)
- **6 were deferred to Phase D** (#6, #7, #8, #12, #16, #18 — captured here)
- **1 became a regression invariant** (#19 — captured in regression-checklist
  as yellow-flag)

A **7th item** was added post-revision when the Phase A spike result file
relocation surfaced a three-way naming convention mismatch between the
spike script's runtime default, its docstring example, and regression
invariant 22's date-parser logic. This wasn't a third-pass finding —
it surfaced during the operator's post-commit walkthrough.

The 7 Phase D items are listed below. Each has an explicit
session-prompt assignment so the Phase D author can find them when
writing prompts.

## Operator decisions log

Decisions made before Phase D begins:

- **Item 3 (Health + broker-orphan double-fire dedup):** Operator chose
  **Option C — hybrid double-fire with cross-reference in Health alert
  message**. Both alerts fire (preserves both safety signals at
  different cadences); Health check's message includes "see also:
  stranded_broker_long active since [ts]" so operator triages once
  and sees both contexts. Rationale: collapses operator triage to a
  single mental act ("yeah, this is the orphan I already know about")
  while keeping defense in depth.

- **Item 6 (Interim merge after Session 1c):** Deferred. Operator
  revisits ~1 week before Session 1c lands. Default leaning toward
  **Option C — interim merge but keep daily flatten** (defense in
  depth; shadow variants get cleaner data sooner without dropping the
  manual safety net).

---

## Item 1 — IMPROMPTU-04 row #4 current-consumer grep verification (MEDIUM #6)

**Disposition:** Phase D Session 4 implementation prompt addition.

**Background:** `analytics/debrief_export.py:336` strips
`Position.side` when writing the debrief CSV. DEF-209 covers FUTURE
consumers (Learning Loop V2, Sprint 35+). The third-pass reviewer asked
about CURRENT consumers — the export feeds:
- The Debrief page (Command Center page 7 — UI consumer; visualizes
  side-stripped P&L; possibly fine because it's read-only display)
- `DailySummaryGenerator` (AI Layer, Sprint 22 — consumes performance
  metrics; may pull from debrief_export)
- AI insight cards (Sprint 22 — what data source?)

**Action in Session 4 implementation prompt:**

Add a pre-flight grep step:

```bash
# In Session 4 pre-flight, before writing the mass-balance script:
grep -rn 'debrief_export\|debrief_csv' argus/ frontend/src/ \
  --include='*.py' --include='*.ts' --include='*.tsx' \
  | grep -v '^analytics/debrief_export.py:'
```

For each consumer found, the implementation prompt instructs Claude
Code to:
1. Inspect the consumer's usage pattern (display vs. decision-making).
2. If decision-making (e.g., `if pnl > threshold`), flag for
   in-sprint expansion of the fix to preserve `side`.
3. If display-only, document the verification result in Session 4
   close-out's "Discovered Edge Cases" section.

**Priority:** Must complete during Session 4. Don't ship Session 4
without the verification.

---

## Item 2 — EOD Pass 2 cancel-timeout failure-mode documentation (MEDIUM #7)

**Disposition:** Phase D Session 1c implementation prompt addition +
runbook addition (already in B22.5 of doc-update-checklist for
restart-required rollback context).

**Background:** Session 1c adds
`cancel_all_orders(symbol, await_propagation=True)` before SELL on
`_flatten_unknown_position` (used by EOD Pass 2). On
`CancelPropagationTimeout`, the SELL is aborted and a
`cancel_propagation_timeout` alert fires. Net effect: EOD Pass 2 may
now leave a phantom long un-flattened on cancel-timeout, trading
"definitely-incorrect SELL" for "possibly-leaked long until next
session."

**Action in Session 1c implementation prompt:**

Add explicit failure-mode documentation to the Session 1c spec:

> **Failure mode change for EOD Pass 2 cancel-before-SELL:** prior
> behavior placed the SELL unconditionally; Session 1c gates SELL
> placement on successful `cancel_all_orders(symbol,
> await_propagation=True)`. On 2s cancel-timeout: the SELL is aborted,
> `cancel_propagation_timeout` alert fires, and the position remains
> at the broker as a phantom long with no working stop. **This is the
> intended trade-off** — incorrect SELLs were the bug we're fixing
> (phantom shorts compound risk); leaked longs are exposure-with-stop-of-zero
> (also bad, but bounded by the underlying long position size, vs.
> phantom shorts which create unbounded short exposure).
>
> **Operator response:** when `cancel_propagation_timeout` alert fires
> for an EOD-flatten path symbol, manually flatten via
> `scripts/ibkr_close_all_positions.py` before the next session begins.

Also add a Session 1c test:
```python
def test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short():
    """MEDIUM #7: cancel-timeout escape hatch in _flatten_unknown_position
    leaves position un-flattened (intended trade-off) but does NOT place
    incorrect SELL that would create a phantom short."""
```

**Priority:** Must complete during Session 1c. Add to runbook addition
in `docs/live-operations.md` Phantom-Short Gate Diagnosis section
(B22 in doc-update-checklist).

---

## Item 3 — Health + broker-orphan double-fire dedup decision (MEDIUM #8)

**Disposition:** Phase D operator decision before Session 2b.2 starts;
Tier 2 review focus item in Session 2b.2.

**Background:** Two subsystems can detect the same condition (broker-orphan
long with no stop):
- **2b.1 broker-orphan branch**: emits `stranded_broker_long` at cycle ≥3
- **2b.2 Health integrity check**: emits "Integrity Check FAILED" critical
  alert (existing behavior preserved for longs)

Both alerts are critical. Operator gets two alerts for one condition.

**Action — operator decision required before Session 2b.2 starts:**

Choose one:

(a) **Make alerts mutually exclusive** — Health check skips
broker-orphan symbols already firing `stranded_broker_long`. Implementation:
2b.2's Health integrity check queries 2b.1's
`_broker_orphan_long_cycles` state; symbols with cycle ≥3 are excluded
from the missing-stop count.

(b) **Document intentional double-fire** — both alerts have different
cadences (2b.1 fires per reconciliation cycle; Health check fires once
daily) and different operator semantics ("you have an orphan that's
stranding" vs. "your daily integrity check found a no-stop position").
Document in `live-operations.md` runbook why both fire.

(c) **Hybrid** — Health check still fires (operator wants the daily
sanity check) but with a callout in the alert message indicating
"see also: stranded_broker_long alert active for this symbol."

**Recommendation:** option (c) — preserves both signals (different
cadences) without making operator triage harder.

**Priority:** Operator decides before Session 2b.2 starts. Decision
flows into Session 2b.2 implementation prompt.

**Reviewer focus:** Tier 2 reviewer for 2b.2 verifies the chosen
behavior is consistent with operator decision.

---

## Item 4 — Mass-balance category precedence rules + 120s window + known-gap registry + boundary handling (MEDIUM #12)

**Disposition:** Phase D Session 4 implementation prompt addition.

**Background:** The H2 categories (`expected_partial_fill`,
`eventual_consistency_lag`, `unaccounted_leak`) are conceptually clear
but operationally underspecified. Edge cases:

1. Partial fill + lag: working order outstanding AND reconciliation cycle
   hasn't caught up.
2. Unfilled with lag: SELL placed but not yet filled, reconciliation runs
   in the gap.
3. IMSR pending=None case: fill callback fires but `_pending_orders`
   doesn't have the order_id (DEBUG-only logging at order_manager.py:592).
4. Out-of-session entries: log file rotation timing.
5. Eventual-consistency time window: cutoff?

**Action in Session 4 implementation prompt:**

The mass-balance script must include in its docstring:

```python
"""validate_session_oca_mass_balance.py — categorized variance report

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
"""
```

Add 3 tests:
1. `test_mass_balance_precedence_partial_fill_wins_over_lag`
2. `test_mass_balance_session_boundary_rejection`
3. `test_mass_balance_imsr_pending_none_classified_unaccounted_unless_def_referenced`

**Priority:** Must complete during Session 4.

---

## Item 5 — Session 2a mock-update estimate verification (LOW #16)

**Disposition:** Phase D Session 2a pre-flight.

**Background:** Session 2a estimates "test files (~5 new + ~3 mock
updates)" for the `dict[str, float]` → `dict[str, ReconciliationPosition]`
refactor. This is an estimate, not a count. If wrong, 2a's compaction
score (10.5) is wrong.

**Action in Session 2a implementation prompt:**

Add a pre-flight grep step BEFORE the impl work begins:

```bash
# Session 2a pre-flight: enumerate all callers of reconcile_positions(
grep -rn 'reconcile_positions(' argus/ tests/

# Also enumerate Mock(spec=OrderManager) patterns
grep -rn 'Mock(spec=OrderManager)\|Mock\(\s*OrderManager' tests/

# Also enumerate test fixtures that build the input dict
grep -rn 'reconcile_positions=\|reconcile_positions :' tests/
```

For each match found, the implementation prompt instructs Claude Code
to:
1. Add to a "discovered call-sites" list at the top of the close-out.
2. If count exceeds 5 mock updates, flag for compaction-score
   re-evaluation and consider mid-session split (5 mock updates
   roughly equals +0.5 compaction units).

**Priority:** Run BEFORE writing the contract refactor. If count
suggests 2a will breach 14 compaction, halt and revise.

---

## Item 6 — Interim merge after 1c (operator decision; LOW #18)

**Disposition:** Phase D operator architectural decision before Session
2a starts.

**Background:** 7–8 weeks with operator daily-flatten as the only
safety net is long. After Session 1c (Tier 3 #1 CLEAR), the OCA
architecture prevents NEW phantom-short creation. Sessions 2-5 add
detection/gating of EXISTING phantom shorts (and observability).
Prevention is more valuable than detection.

If the operator merges to a paper-trading branch after 1c lands, the
operator's daily-flatten dependency drops by an order of magnitude
during 2a-2d (~2-3 weeks). Cost: 2a's contract refactor is
incompatible with the orphan branch in 2b.1, so the orphan loop is in
a transitional state during this period.

**Action — operator decision before Session 2a starts:**

Choose one:

(a) **Continue strict sequential execution** — no interim merge; daily
flatten continues for full 7-8 weeks. Reviewer's recommended default.

(b) **Interim merge after 1c** — paper-trading runs against post-1c
code; daily flatten can be relaxed (operator's call). Sessions 2a-2d
implement reconciliation+gate work in transitional state. Re-merge at
2d or 5b.

(c) **Hybrid** — paper-trading runs against post-1c code with
daily-flatten still in effect (defense in depth); reduces operator
fatigue without committing to the transitional-state risk.

**Recommendation:** option (c) — captures most of the prevention
benefit without the transitional-state risk.

**Priority:** Operator decides before Session 2a starts. Decision
informs operator's daily routine for 7-8 week window.

---

## Item 7 — Spike script filename convention three-way mismatch (post-3rd-pass discovery)

**Disposition:** Phase D Session 4 implementation prompt addition.

**Background:** During the post-revision walkthrough of the Phase A
spike result file, a three-way convention mismatch surfaced between
the spike script's runtime behavior, its docstring example, and the
regression invariant that polices result freshness. None of the three
agree on filename format:

| Source | Format | Example |
|---|---|---|
| `scripts/spike_ibkr_oca_late_add.py:506` (default output if `--output` not passed) | Unix epoch timestamp | `spike-results-1777301262.json` |
| `scripts/spike_ibkr_oca_late_add.py:50` (docstring example) | ISO date with dashes | `spike-results-2026-04-27.json` |
| `regression-checklist.md` invariant 22 (date-parsing test logic) | Compact date without dashes | `spike-results-20260427.json` |

The Phase A spike run on ~2026-04-25 produced
`spike-results-1777301262.json` (default Unix-timestamp form), which
was relocated post-revision to
`scripts/spike-results/spike-results-2026-04-25.json` (ISO
docstring-style form). Regression invariant 22's date-parser would
NOT match either of those forms — it expects 8-digit YYYYMMDD with no
dashes.

**Action in Session 4 implementation prompt:**

Standardize on **ISO date with dashes** (`spike-results-YYYY-MM-DD.json`)
across all three sources. Rationale: human-readable, sortable, what
the operator naturally reaches for inspecting the directory; matches
the existing relocated file. Two surgical fixes + one regression
update:

1. **`scripts/spike_ibkr_oca_late_add.py:506`** — change default from
   Unix timestamp to ISO date:
   ```python
   # Before:
   out_path = args.output or f"spike-results-{int(time.time())}.json"
   # After:
   out_path = args.output or f"spike-results-{datetime.date.today().isoformat()}.json"
   ```
   Also update default to write into `scripts/spike-results/` rather
   than current working directory (matches B28 trigger registry):
   ```python
   out_dir = "scripts/spike-results"
   os.makedirs(out_dir, exist_ok=True)
   out_path = args.output or os.path.join(
       out_dir, f"spike-results-{datetime.date.today().isoformat()}.json"
   )
   ```

2. **`regression-checklist.md` invariant 22 test** — update date-parser
   to expect ISO format:
   ```python
   # Before:
   date_str = latest[len("spike-results-"):-len(".json")]
   latest_date = datetime.date.fromisoformat(
       f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
   )
   # After:
   date_str = latest[len("spike-results-"):-len(".json")]
   latest_date = datetime.date.fromisoformat(date_str)
   ```

3. **`docs/live-operations.md` B28 trigger registry** — verify the
   procedure section uses the ISO format example. The existing draft
   already does (`spike-results-YYYY-MM-DD.json`), so this is just a
   verification step.

**Tests to add in Session 4:**

1. `test_spike_script_default_output_is_iso_date_in_spike_results_dir` —
   asserts `--output` not passed produces
   `scripts/spike-results/spike-results-YYYY-MM-DD.json`.
2. `test_invariant_22_date_parser_handles_iso_format_with_dashes` —
   asserts the freshness check correctly parses both forms during
   transition window (allow legacy filenames already committed for at
   least one sprint).

**Backward compatibility:** the existing
`scripts/spike-results/spike-results-2026-04-25.json` (relocated from
the Phase A revisit run) is already in the target format. No legacy
file rename needed.

**Priority:** Must complete during Session 4. The Session 4 close-out
should grep `spike-results-` references across the codebase to confirm
consistency.

---

## Phase D author checklist

When writing Phase D implementation prompts, for each session prompt
verify:

- [ ] Session 1c: Item 2 (cancel-timeout failure-mode doc + test) included
- [ ] Session 2a: Item 5 (pre-flight grep) included
- [ ] Session 2b.2: Item 3 (operator's dedup decision incorporated — operator chose **Option C: hybrid double-fire with cross-reference in Health alert message**) included; Tier 2 review focus mentions
- [ ] Session 4: Item 1 (debrief_export grep verification) included
- [ ] Session 4: Item 4 (mass-balance precedence + window + registry + boundary) included
- [ ] Session 4: **Item 7 (spike script filename convention alignment — 3 surgical fixes + 2 tests)** included
- [ ] Operator decision before Session 2a (Item 6) made and documented in work journal — operator deferred decision; revisit when Session 1c is ~1 week from landing

If a Phase D prompt is missing any of these items, the Tier 2 reviewer
should flag it as a non-CLEAR observation pointing back to this file.

---

*End Sprint 31.91 Phase D Open Items.*
