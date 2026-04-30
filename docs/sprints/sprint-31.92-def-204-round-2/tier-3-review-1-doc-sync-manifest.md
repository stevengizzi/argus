# Tier 3 Review #1 Doc-Sync Manifest (Sprint 31.92)

## Triggering event

Sprint 31.92 Tier 3 Architectural Review #1 returned **REVISE_PLAN** on 2026-04-30 (verdict at `tier-3-review-1-verdict.md`) after S1a spike returned `status: INCONCLUSIVE`. The verdict surfaced six DEFs (verdict-side DEF-213–218; renumbered DEF-236–241 per `tier-3-review-1-verdict-renumbering-corrections.md` after CLAUDE.md cross-check) + three new RSKs + a Pattern B DEC-389 reservation + spec amendments to `sprint-spec.md`, `spec-by-contradiction.md`, `falsifiable-assumption-inventory.md`, and `escalation-criteria.md`. This mid-sync materializes the Pattern A items (in-flight session prerequisites); the Pattern B items (DEC-389 / DEC-390 / project-knowledge.md) defer to Sprint 31.92 D14 sprint-close doc-sync per the verdict's §Documentation Reconciliation item 9–11.

## Files touched (with structural anchors, not line numbers)

| File | Change shape | Sprint-close transition owed |
|---|---|---|
| `docs/sprints/sprint-31.92-def-204-round-2/sprint-spec.md` | (a) §Hypothesis Prescription "halt-or-proceed gate language" updated to bind on `axis_i_wilson_ub` (axis (i) only), with axes (ii)/(iv) demoted to informational and axis (iii) deleted, per DEC-389 amended rule. (b) FAI #3 row in inline `## Falsifiable Assumption Inventory` table amended to reflect loose reading. | Sprint-close: confirm DEC-389 materialization references the spec-side rule encoding verbatim. |
| `docs/sprints/sprint-31.92-def-204-round-2/spec-by-contradiction.md` | (a) Edge Case 2 reference to "Decision 1" updated to point to DEC-389 amended rule. (b) Out-of-Scope item 27 appended under §"NEW Out-of-Scope items per Tier 3 verdict + 7 settled operator decisions (2026-04-29)" subsection (NOTE: verdict §Documentation Reconciliation item 1 attributed item 27 to `sprint-spec.md`, but sprint-spec.md has no Out-of-Scope numbered list; the canonical home is spec-by-contradiction.md §"Out of Scope" where item 26 currently terminates the list). | Sprint-close: verify DEC-389 materialization's "supersedes" cross-reference resolves cleanly to item 27. |
| `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md` | FAI #3 amended to reflect axis (i)-binding + axes (ii)/(iv) informational + axis (iii) deleted, per DEC-389. | Sprint-close: regenerate the inline FAI table copy in `sprint-spec.md` if FAI text drifts further (zero divergence today). |
| `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md` | A1 amended: "spike returned INCONCLUSIVE under DEC-389 amended rule" (the new threshold). | Sprint-close: confirm escalation criteria language matches DEC-389 final materialization. |
| `CLAUDE.md` §DEF table | Six new rows appended after DEF-235: DEF-236 (Mode A propagation measurement bug), DEF-237 (side-blind `_flatten()` in S1a harness), DEF-238 (axis (ii)/(iv) instrumentation no fail-loud), DEF-239 (`ibkr_close_all_positions.py` audit; status RESOLVED-VERIFIED-NO-FIX 2026-04-30), DEF-240 (S1b sister-spike same bug class), DEF-241 (Sprint 31.94 reconnect-recovery dependency on informational axes). | Sprint-close: DEF-236/237/238/240 transition OPEN→RESOLVED-IN-SPRINT after spike v2 close-out. DEF-239 is already terminal. DEF-241 transitions to OPEN-CROSS-SPRINT (sprint home: 31.94) at sprint-close. |
| `docs/risk-register.md` | Three new named-RSK entries appended after RSK-DEF-203: RSK-DEC389-31.94-COUPLING, RSK-MODE-D-CONTAMINATION-RECURRENCE, RSK-VERDICT-VS-FAI-3-COMPATIBILITY. Each follows the existing named-RSK schema (RSK-DEF-204 / RSK-DEC-386-DOCSTRING / RSK-DEF-203 are the templates). NOTE: verdict §Documentation Reconciliation item 6 attributed entries to a "CLAUDE.md §RSK table" which does not exist; CLAUDE.md only references RSKs inline within DEF rows or prose. Full prose lands in `docs/risk-register.md` only — this is the canonical RSK store per `.claude/rules/doc-updates.md` Numbering Hygiene. The "Last updated" footer is refreshed to 2026-04-30. | Sprint-close: confirm the three RSKs' Status fields against actual sprint outcomes (RSK-DEC389-31.94-COUPLING transitions to time-bounded by Sprint 31.94 design Phase B; RSK-MODE-D-CONTAMINATION-RECURRENCE transitions to RESOLVED or escalated based on spike v2; RSK-VERDICT-VS-FAI-3-COMPATIBILITY transitions to RESOLVED if axis (i) UB clean, or revisited if straddling H2/H4 threshold). |

## DECs the mid-sync DEFERRED to sprint-close

| DEC | Reason for deferral | Cross-reference text source for sprint-close |
|---|---|---|
| DEC-389 | Pattern B per verdict §Output item 10 ("use Pattern B when in doubt"). Architectural narrative depends on spike v2 outcome (H2 vs H4 vs H1 selection) AND S2a/S2b prompt composability. Materializes after spike v2 close-out. | Verdict §"DEC Entries" DEC-389 block (full narrative + sprint-close gate criteria); spec-by-contradiction.md §"Out of Scope" item 27 (this manifest's edit); sprint-spec.md §Hypothesis Prescription amended halt-or-proceed gate language (this manifest's edit). |
| DEC-390 | Reserved for sprint-close 4-layer DEF-204 architectural closure. DEC-389 is a subset; DEC-390 builds on it. Independent of this mid-sync; pre-existing reservation per Sprint 31.92 sprint plan. | Sprint 31.92 sprint-spec.md §Scope Deliverable 6 ("DEC-390 materialization (sprint-close)"). |

## DEF transitions OWED at sprint-close

| DEF | Current status (this manifest) | Target status (sprint-close) | Source of resolution |
|---|---|---|---|
| DEF-236 (Mode A propagation measurement bug) | OPEN — routed to spike v2 (Cat A.1 fix) | RESOLVED-IN-SPRINT | Spike v2 close-out: Mode A `propagation_ok` rate ≥ 48/50 under unconstrained Gateway. |
| DEF-237 (side-blind `_flatten()` in S1a harness) | OPEN — routed to spike v2 (Cat A.2 fix) | RESOLVED-IN-SPRINT | Spike v2 close-out: Mode D N=100 `zero_conflict_in_100 == true` OR no `position_state_inconsistency: shares=N` for unbounded N. |
| DEF-238 (axis (ii)/(iv) instrumentation no fail-loud) | OPEN — routed to spike v2 (Cat B.3 fix) | RESOLVED-IN-SPRINT | Spike v2 close-out: spike fails LOUD on operator-skipped Gateway disconnect; `instrumentation_warning` JSON tag present when applicable. |
| DEF-239 (`ibkr_close_all_positions.py` audit) | RESOLVED-VERIFIED-NO-FIX 2026-04-30 | (terminal — no transition) | Already audited; audit note at `docs/sprints/sprint-31.92-def-204-round-2/def-216-audit-resolved-verified.md` (filename historical to verdict-side DEF-216; renumbering note at file head cross-references DEF-239). |
| DEF-240 (S1b sister-spike same bug class) | OPEN — routed to S1b execution (Cat A.1 + A.2 applied) | RESOLVED-IN-SPRINT | S1b spike close-out: Cat A.1 + A.2 applied to `scripts/spike_def204_round2_path2.py` before operator execution. |
| DEF-241 (Sprint 31.94 reconnect-recovery dependency on informational axes) | OPEN — CROSS-SPRINT | (no transition at 31.92 sprint-close; remains OPEN — sprint home: 31.94) | Sprint 31.94 Phase B DEC entry must explicitly cross-check against DEC-389 informational axes; transition handled by Sprint 31.94. |

## Architecture / catalog freshness items DEFERRED to sprint-close

| Surface | Status | Action at sprint-close |
|---|---|---|
| `docs/decision-log.md` | NOT touched at this mid-sync | DEC-389 full entry materialized at 31.92 D14 doc-sync; DEC-390 references DEC-389. |
| `docs/dec-index.md` | NOT touched at this mid-sync | DEC-389 + DEC-390 added at 31.92 D14 doc-sync. |
| `docs/project-knowledge.md` | NOT touched at this mid-sync | Most-cited foundational decisions list amended; sprint-history table updated at 31.92 D14 doc-sync. |
| `docs/architecture.md` | NOT touched at this mid-sync (no architectural change at production-code surface — rule amendment is spec-side only) | No action at sprint-close. |
| `docs/pre-live-transition-checklist.md` | NOT touched at this mid-sync (no pre-live config change) | No action at sprint-close. |
| `docs/process-evolution.md` | NOT touched at this mid-sync (no new process lesson; F.5 percentage-claim discipline already present) | No action at sprint-close. |
| `scripts/spike_def204_round2_path1.py` | NOT touched in this commit per operator instruction (Cat A and Cat B land in Unit 3 + Unit 4 separately) | Out of mid-sync scope; Cat A.1/A.2/B.1/B.2/B.3 fixes are operator-driven via Unit 3 + Unit 4 commits; old commit `c1b4bf2` preserved as the contaminated reference. |

## Renumbering provenance (verdict-side ↔ CLAUDE.md-side)

| Verdict-side | CLAUDE.md-side | Title | Sprint home |
|---|---|---|---|
| DEF-213 | DEF-236 | Mode A propagation measurement bug (Cat A.1) | 31.92 (sprint-internal) |
| DEF-214 | DEF-237 | Side-blind `_flatten()` in S1a harness (Cat A.2) | 31.92 (sprint-internal) |
| DEF-215 | DEF-238 | Axis (ii)/(iv) instrumentation no fail-loud (Cat B.3) | 31.92 (sprint-internal) |
| DEF-216 | DEF-239 | `ibkr_close_all_positions.py` audit | 31.92 (sprint-internal) — RESOLVED-VERIFIED-NO-FIX 2026-04-30 |
| DEF-217 | DEF-240 | S1b sister-spike same bug class | 31.92 (sprint-internal) |
| DEF-218 | DEF-241 | Sprint 31.94 reconnect-recovery dependency on informational axes | 31.94 (cross-sprint) |

Canonical mapping document: `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-1-verdict-renumbering-corrections.md` (commit `7a7c544`, 2026-04-30).

## Documentation Reconciliation discrepancies surfaced (verdict text vs repo reality)

These are not corrections to the verdict (which is point-in-time historical) but provenance notes for the sprint-close reviewer:

1. **Verdict §Documentation Reconciliation item 1** attributes "Out-of-Scope item 27" to `sprint-spec.md`. `sprint-spec.md` has no Out-of-Scope numbered list. The canonical home is `spec-by-contradiction.md` §"Out of Scope" (item 26 currently terminates the list). Item 27 lands there.
2. **Verdict §Documentation Reconciliation item 6** attributes the three new RSKs to a "CLAUDE.md §RSK table". CLAUDE.md has no RSK table. The canonical home is `docs/risk-register.md`. Full prose lands there only.
3. **Verdict §Documentation Reconciliation items 4 and 5** specified line numbers (L853–866 in sprint-spec.md and L804 FAI #3). Per RULE-038 (session-start grep-verification of factual claims), structural anchors (section names + table row identifiers) are used in this manifest instead of line numbers, since line numbers drift across edits.

## DEC-389 numbering collision (escalation to sprint-close attention)

**Collision detected at this mid-sync.** The verdict reserves `DEC-389` for the S1a Decision-Rule Amendment (Pattern B sprint-close materialization). However, `DEC-389` was **already materialized** at Sprint 31.915 sprint-close on 2026-04-28 for `Config-Driven evaluation.db Retention` (per `docs/dec-index.md:522` and CLAUDE.md "Last updated" header at L4 / DEF-234 row).

**Same root cause as the DEF-213–218 collision** (handled by `tier-3-review-1-verdict-renumbering-corrections.md`, commit `7a7c544`): the Tier 3 reviewer (fresh Claude.ai conversation) extrapolated DEC numbers from the sprint-handoff prompt's anticipated ceiling without grep-verifying against the live `dec-index.md`. The handoff prompt at Sprint 31.92 kickoff (pre-Sprint-31.915) listed DEC-388 as the highest existing; Sprint 31.915 sealed two days before the verdict was authored and consumed DEC-389 in the interim.

**Impact:**
- The verdict's text uses "DEC-389" throughout for the rule amendment.
- This mid-sync's edits to `sprint-spec.md` / `spec-by-contradiction.md` / `falsifiable-assumption-inventory.md` / `escalation-criteria.md` / `risk-register.md` (RSK-DEC389-31.94-COUPLING, RSK-VERDICT-VS-FAI-3-COMPATIBILITY) ALL reference "DEC-389 amended rule" verbatim per the verdict, for historical fidelity (matching the renumbering-corrections pattern).
- The verdict also reserves "DEC-390" for sprint-close 4-layer DEF-204 architectural closure. `dec-index.md` shows DEC-390 currently unassigned, so the DEC-390 reservation is still valid — but it presumes DEC-389 stays put.

**Resolution owed at sprint-close (D14 doc-sync) — Pattern B materialization:**
- Sprint 31.92 D14 doc-sync MUST re-cross-check the live `dec-index.md` at sprint-close time and pick fresh DEC numbers for both the rule amendment AND the 4-layer architectural closure.
- Recommended renumbering (subject to live `dec-index.md` re-verification at sprint-close):
  - Verdict-side `DEC-389` (rule amendment) → `DEC-391` (or next available).
  - Verdict-side `DEC-390` (4-layer architectural closure) → `DEC-392` (or next available).
- The renumbering will require a sprint-close doc-sync sweep across all Pattern A files this mid-sync touched, plus the to-be-materialized `decision-log.md` / `dec-index.md` / `project-knowledge.md` entries themselves.
- Recommend producing a `sprint-close-renumbering-corrections.md` artifact (analogue of `tier-3-review-1-verdict-renumbering-corrections.md`) that records the DEC-389 / DEC-390 → final mapping for cross-reference durability.

**Why not renumber at this mid-sync:** Per user instruction, Pattern B files (`decision-log.md`, `dec-index.md`, `project-knowledge.md`) are not touched at this mid-sync — DEC materialization is sprint-close work. Renumbering the verdict-side DEC-389 across Pattern A files now would create a free-floating "DEC-391" reference with no decision-log entry to ground it for the rest of the sprint, which is worse than the verdict-side reference because future readers between now and sprint-close cannot resolve "DEC-391" to anything. Verdict-side text is the path of least confusion until sprint-close materializes the final DEC numbers.

**Process-evolution implication:** The Tier 3 briefing prompt's sprint-context block should include both "Highest existing DEF number" AND "Highest existing DEC number" so the reviewer can extrapolate from the live ceiling rather than the sprint-handoff anticipated ceiling. (Captured in `tier-3-review-1-verdict-renumbering-corrections.md` for the DEF angle; this manifest extends the recommendation to DECs.)

## Workflow version compliance

This manifest was produced under `protocols/mid-sprint-doc-sync.md` version 1.0.0 (introduced 2026-04-28; reference: `workflow/protocols/mid-sprint-doc-sync.md`). Sprint-close doc-sync MUST run under a metarepo state that includes this protocol version or higher.

## Linked artifacts

- Triggering verdict: `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-1-verdict.md`
- Renumbering corrections: `docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-1-verdict-renumbering-corrections.md` (commit `7a7c544`)
- DEF-239 audit note: `docs/sprints/sprint-31.92-def-204-round-2/def-216-audit-resolved-verified.md` (filename historical to verdict-side DEF-216; renumbering header note added)
- Spike v1 contaminated artifact: `scripts/spike-results/spike-def204-round2-path1-results.json` (operator-executed 2026-04-30T14:13Z; commit `c1b4bf2`)
- Impl prompts produced (if any): None at this mid-sync. S2a + S2b prompt generation remains halted until clean spike v2 JSON lands AND DEC-389's amended rule is encoded in the spec.
