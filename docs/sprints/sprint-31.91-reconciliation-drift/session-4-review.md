# Sprint 31.91 — Session 4 Tier 2 Review

> Date: 2026-04-28
> Reviewer: Tier 2 (read-only)
> Barrier commit: `da325a0` (initial `c1ebbbb` + hotfix `da325a0`)
> Baseline: `c330a01`

---BEGIN-REVIEW---

```json:structured-verdict
{
  "session": "4",
  "verdict": "CLEAR",
  "ci_status_at_barrier_commit": "GREEN",
  "barrier_commit": "da325a0",
  "tests_total_observed": 5184,
  "scope_violations": [],
  "do_not_modify_violations": [],
  "rule_compliance": {
    "RULE-001 (prompt adherence)": "PASS",
    "RULE-002 (flag don't rationalize)": "PASS",
    "RULE-007 (scope expansion)": "PASS",
    "RULE-011 (honest self-assessment)": "PASS",
    "RULE-019 (tests passing at close)": "PASS",
    "RULE-038 (session-start grep verification)": "PASS",
    "RULE-050 (CI verification)": "PASS"
  },
  "discovered_edge_cases_acceptable": true,
  "deviations_acknowledged_at_appropriate_level": true
}
```

## Summary

Session 4 delivered the Sprint 31.91 validation infrastructure as specified: a 462-LOC mass-balance categorized variance script with full H2 + Item 4 precedence implementation, an IMSR replay integration test against the real Apr 24 paper-session log with RULE-051 mechanism-signature anchors, three docs surfaces updated (live-enable gates, Phase 7.4 slippage watch, B28 spike trigger registry), and the Item 7 three-source filename standardization. Two MINOR_DEVIATIONS were flagged appropriately (RULE-002): the BacktestEngine `process_event()` API anticipated by the spec doesn't exist on the production engine, and the spec referenced `:506` for the spike-script default-output line whose actual location was `:509`. Both deviations were resolved without scope expansion (RULE-007 compliant) and without weakening verification contracts. CI is GREEN on `da325a0` after a hotfix commit `da325a0` correctly marked the IMSR replay test `@pytest.mark.integration` so it's excluded from CI's `-m "not integration"` filter (CI doesn't have the operator-supplied 29-MB log; the in-test `pytest.fail`-on-missing contract is preserved for operator-local runs).

## Per-Focus-Area Findings

### Focus Area 1: H2 categorization definitions precise — PASS

`scripts/validate_session_oca_mass_balance.py` lines 1-36 contain the verbatim docstring from the spec. The implementation matches:

- **Three categories with precedence** (`categorize_event`, lines 304-360): `expected_partial_fill > eventual_consistency_lag > unaccounted_leak` — the categorizer returns at the first matching precedence level.
- **120s eventual-consistency window** (line 51 module constant `EVENTUAL_CONSISTENCY_WINDOW_SECONDS = 120`, with inline comment "<=2 reconciliation cycles. Each cycle is nominally 60s"). Documented as ≤2 cycles per the spec.
- **Cross-session boundary handling** (lines 286-321): `_detect_session_boundaries` infers session window from min/max timestamps; events outside that window classify as `boundary_ambiguous` (line 321) — does NOT silently fall through to `unaccounted_leak`. Verified by `test_mass_balance_session_boundary_rejection`.
- **IMSR pending=None known-gap escape** (lines 65-68 + 353-356): `BrokerSellEvent.has_def_reference()` regex-matches `DEF-\d+` against the row's `notes` field; matching rows classify as `known_gaps_acknowledged`. Verified by `test_mass_balance_imsr_pending_none_classified_unaccounted_unless_def_referenced` Sub-cases A (no DEF → leak) and B (DEF tag → known_gaps_acknowledged).

### Focus Area 2: IMSR replay test runs against real log — PASS

`tests/integration/test_imsr_replay.py` correctly:

- Uses `pytest.fail(...)` (line 92) on missing log, NOT `pytest.skip`. H4 disposition preserved.
- Loops through every event in the real log via `_extract_position_lifecycle` and `_has_mechanism_signature`.
- Asserts `eod_position == 0` (line 175), not `>= 0`.
- The `pytestmark = pytest.mark.integration` (line 76, added by hotfix) is the operator-local-vs-CI distinction. The H4 in-test contract is unchanged; the marker only changes default CI collection (test runs operator-locally where the file is present).

I ran the test locally (with the Apr 24 log present at `logs/argus_20260424.jsonl`, 29 MB, dated Apr 24 16:42); it passes. Mechanism-signature anchors verified — both `01KQ04FRMCBGMQ57NG41NPY0N9` (DEF-158 retry SELL ULID, RULE-051) and `DETECTED UNEXPECTED SHORT POSITION IMSR` (IMPROMPTU-04 EOD marker) are present in the log. The lifecycle walk reaches and stays at 0 under post-fix code on `main` (Sessions 1a-1c OCA + 2a-2d side-aware reconciliation + Session 3 retry side-check).

### Focus Area 3: Live-enable gate criteria unambiguous and verifiable — PASS

`docs/pre-live-transition-checklist.md` lines 203-240 add the decomposed gates section:

- **Gate 1** (4 sub-criteria): paper-session count is countable, `validate_session_oca_mass_balance.py` exit code is observable, alert log inspection is operator-procedure-defined. Adds `cancel_propagation_timeout` as a 4th criterion beyond what the spec listed — strengthens the gate.
- **Gate 2** (7 sub-criteria): paper-trading data-capture overrides removed, risk limits restored, overflow restored, ≥10 entries, zero of three alert types, zero `unaccounted_leak`. Each is verifiable.
- **Gate 3**: $50–$500 notional cap, single operator-selected symbol, alert-triggered halt with explicit DEF-210 deferral note.
- **Disconnect-reconnect** explicitly deferred to Sprint 31.93.

The gates land cleanly above the existing Sprint 31.91 detailed checklists (which become the per-gate verification subsections). No conflict.

### Focus Area 4: Phase 7 slippage watch item clear — PASS

`docs/protocols/market-session-debrief.md` lines 773-789 add Phase 7.4. Threshold `≤$0.02 degradation` documented; rollback path explicitly cross-references `live-operations.md §"OCA Architecture Operations"` (which exists at line 773 in that file with the RESTART-REQUIRED procedure at line 777). The H1 disposition (mid-session flip unsupported) is correctly cited. Persistent-degradation language correctly distinguishes a single-session blip from a rollback trigger.

### Focus Area 5: Item 1 verification documented — PASS

The closeout's "Pre-flight verification (per spec) — Item 1" section (lines 73-85) documents:
- Grep ran with the spec's exact pattern.
- Only hit was `argus/main.py:2266` (the writer call site, NOT a CSV consumer).
- Frontend grep extended to `argus/ui/src/` (the actual frontend tree) since `frontend/` referenced in spec doesn't exist — also empty.
- Classification: zero current consumers; DEF-209's "FUTURE consumers" framing correct.

I re-ran the grep and confirm: only `argus/main.py:2266` matches, and inspection (lines 2264-2272) shows it's the export call site inside the shutdown sequence (`from argus.analytics.debrief_export import export_debrief_data`). No decision-making consumer exists. **A6 escalation criterion is NOT triggered.**

### Focus Area 6: Item 7 three surgical fixes consistent — PASS (with one minor note)

I ran the focus-area-6 grep:

```bash
grep -rn 'spike-results-' . --include='*.py' --include='*.md' --include='*.json' \
  | grep -v 'node_modules\|\.pytest_cache\|workflow/' \
  | grep -v 'PHASE-D-OPEN-ITEMS.md'
```

Findings:

- All load-bearing surfaces use ISO-with-dashes:
  - `scripts/spike_ibkr_oca_late_add.py:50,519,589` — ISO-with-dashes
  - `docs/live-operations.md:842,852,854` — ISO-with-dashes
  - `docs/pre-live-transition-checklist.md:279` — ISO-with-dashes
  - `docs/sprints/sprint-31.91-reconciliation-drift/regression-checklist.md:413,440,441` — ISO-with-dashes; parser is direct `fromisoformat(date_str)`.
- No `int(time.time())` references remain in the spike script (`grep -n "int(time.time())" scripts/spike_ibkr_oca_late_add.py` returns empty).
- Legacy references survive only in HISTORICAL/FROZEN documents (acceptable per spec scope):
  - `docs/sprints/sprint-31.91-reconciliation-drift/PHASE-A-REVISIT-FINDINGS.md:20` (`spike-results-1777301262.json` — historical record of the actual file produced by the Apr 27 spike run)
  - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md:291` and `doc-update-checklist.md:888` (`spike-results-YYYYMMDD.json`)
  - `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/05-pre-live-transition-checklist.md.patch.md:75` and `07-live-operations.md.patch.md:102,110,112` (frozen patch artifacts from Tier 3 review #1, 2026-04-27)

These historical/patch artifacts pre-date Item 7's standardization and are documentation of prior states. Spec scope was the three load-bearing sources (script, docstring, invariant 22 parser); all three are correctly fixed. I do not consider these residual references a CONCERN — they are appropriately "frozen" historical context. If a future reviewer wants total elimination, that would be an opportunistic doc-hygiene pass, not a Session 4 deficiency.

### Focus Area 7: DEF-208 + DEF-209 filed — PASS

`CLAUDE.md` at the line inserted between DEF-207 and DEF-209 contains the new DEF-208 entry (verified via `git diff c330a01..da325a0 -- CLAUDE.md`). DEF-209 was already present (filed during Tier 3 review #1, 2026-04-27); the closeout correctly notes "no insert needed" — `defs_filed: ["DEF-208"]` + `defs_already_present: ["DEF-209"]`. Both entries match the spec's prescribed framing (DEF-208: live-trading test fixture missing; DEF-209: future-consumer protection for `analytics/debrief_export.py:336` side-stripping).

## Sprint-Level Regression Checks

- **Invariant 5 (pytest baseline ≥ 5,159):** PASS. I independently ran `python -m pytest --ignore=tests/test_main.py -m "not integration" -n auto -q` and observed `5170 passed`; without the integration filter, `5184 passed`. Closeout's claims (5,170 CI / 5,184 operator-local) are accurate. +10 vs prior baseline (5174 in operator-local frame; 7 mass-balance + 2 spike-filename + 1 IMSR replay).
- **Invariant 14 ("After Session 4" row):**
  - Mass-balance validated = YES (script + 7 synthetic-fixture tests + smoke-tested against the real Apr 24 log; exit code 1 against the cascade log is correct).
  - Recon detects shorts = full (Sessions 2b.1 broker-orphan branch + 2b.2 Health both already on `main`, verified by closeout).
  - DEF-158 retry = YES (Session 3 already on `main`).
- **Invariant 15:** PASS (no scoped exceptions).
- **Invariant 22 (spike-results freshness):** parser updated to `fromisoformat(date_str)` directly; the `f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"` reconstruction is gone. Behavioral test `test_invariant_22_date_parser_handles_iso_format_with_dashes` exercises the new convention.

## Acceptance of Flagged Deviations

### Deviation 1: BacktestEngine event-replay API mismatch — MINOR_DEVIATIONS, accepted

The spec anticipated `engine.process_event(event)` / `engine.get_position_at_eod(symbol)` event-replay surface; the production `BacktestEngine` only has `async def run() -> BacktestResult` over Parquet bar data. Additionally, IMSR has no Apr 2026 cached Parquet (latest `2026-02.parquet`).

The implementer correctly applied:
- **RULE-007** (no new harness): did not introduce a parallel replay engine.
- **RULE-002** (flag don't rationalize): explicitly flagged the mismatch in the closeout's "Discovered Edge Cases" and in the test's docstring.
- **RULE-051** (mechanism signature, not symptom aggregate): added `DEF_158_RETRY_ULID` and `EOD_PHANTOM_SHORT_MARKER` as preconditions before the assertion runs — without both, the test fails before reaching the EOD-position check, so the test cannot drift to passing on a different log.
- **H4 disposition**: `pytest.fail` on missing log is preserved (line 92).
- **Equivalent verification surface**: ARGUS's internal `Position opened` / `Position closed` log events are what `OrderManager._managed_positions` reports; `get_position_at_eod` semantics are correctly approximated by this in-process accounting walk.

The assertion `eod_position == 0` is preserved. The verification contract is functionally equivalent. Accept as MINOR_DEVIATIONS, NOT ESCALATE.

### Deviation 2: Spec line drift `:506` → `:509` — MINOR_DEVIATIONS, accepted

RULE-038 path-drift between spec authoring and execution. The implementer applied the surgical fix at the correct line (`:509` in the actual source); pre-Unix-epoch form is gone (`grep` returns empty). Documented in closeout's "Pre-flight verification — Item 7" table. Accept as MINOR_DEVIATIONS, NOT ESCALATE.

## Escalation Criteria Disposition

- **A2** (Tier 2 produces CONCERNS or ESCALATE): NOT triggered. Verdict is CLEAR.
- **A5** (IMSR replay test fails): NOT triggered. Test passes locally with both mechanism-signature anchors present.
- **A6** (debrief_export current decision-making consumer): NOT triggered. Item 1 grep returned only the writer call site.
- **B1, B3, B4, B6**: not triggered (no scope expansion, no do-not-modify violations, no new-dependency without approval, no source-tree damage).
- **C5** (Apr 24 log not available): NOT triggered. Log present at `logs/argus_20260424.jsonl` (29 MB, Apr 24 16:42).

## CI Verification (RULE-050)

- Run `25053110113` on barrier commit `da325a0` — **success** (pytest backend ✓, vitest frontend ✓, both jobs at completed/success). 4m0s wall-clock.
- Prior run `25052801978` on `c1ebbbb` — failure with "ERROR tests/integration/test_imsr_replay.py::test_imsr_replay_with_post_fix_code_position_zero_at_eod - Failed: IMSR replay log missing at logs/argus_20260424.jsonl". This is the H4 contract firing on a CI runner that doesn't have the operator-supplied 29-MB log. The hotfix `da325a0` adds `pytestmark = pytest.mark.integration` so CI's `-m "not integration"` filter excludes the test; the in-test `pytest.fail` contract still fires for operator-local runs without the file.

The hotfix is the correct fix posture: an operator-only artifact should not gate CI. The H4 disposition (no synthetic fallback; errors not skips) is preserved for the operator-local execution context where the test is intended to run.

## Recommendation

**Verdict: CLEAR.**

Session 4 delivers:
- 4 created files, 6 modified files, 0 do-not-modify violations.
- 10 new tests (7 mass-balance + 2 spike-filename + 1 IMSR replay), all passing locally; 5,170 CI-visible tests / 5,184 operator-local tests, both ≥ 5,159 threshold.
- 3 docs surfaces updated per spec (decomposed live-enable gates, Phase 7.4 slippage watch, B28 spike trigger registry).
- 2 DEFs filed (DEF-208 newly inserted; DEF-209 already present and verified).
- Item 1 grep verification correctly shows DEF-209 is future-consumer-only.
- Item 7 three-source filename standardization complete on all load-bearing surfaces.
- 2 minor deviations correctly flagged with RULE-002 transparency and RULE-007 scope discipline.
- CI green on barrier commit; prior CI red was the IMSR-replay-on-missing-log signal that was correctly handled by the integration-marker hotfix.

No issues meeting CONCERNS or ESCALATE thresholds were observed. Proceed to next session (Session 5a.1, gated by DEF-213 + DEF-214 inclusion as documented in CLAUDE.md).

---END-REVIEW---
