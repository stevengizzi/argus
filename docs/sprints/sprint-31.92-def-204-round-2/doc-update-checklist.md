# Sprint 31.92: Doc Update Checklist

> **Phase C artifact 7/8.** Three-phase doc update plan: (A) pre-sprint
> housekeeping verification (Phase 0 cross-reference patches landed
> 2026-04-29 — confirm-only, no new patches), (B) mid-sprint Sprint Spec
> amendment for AC5.3 (must land before Phase D prompt generation), and
> (C) sprint-close (D14) doc-sync that follows S5b close-out. Each item
> specifies the file, surgical sed/find-replace patches where applicable,
> structural-anchor patches for narrative content, and rationale.
>
> **Sealed-file exclusions (per RULE-053):** Do NOT touch any file under:
> - `docs/sprints/sprint-31.91-reconciliation-drift/` (sealed 2026-04-28)
> - `docs/sprints/sprint-31.915-evaluation-db-retention/` (sealed)
> - `docs/sprints/sprint-31.9/` (campaign sealed 2026-04-24)
> - `docs/sprints/synthesis-2026-04-26/` (sealed)
> - `docs/audits/audit-2026-04-21/` (sealed)
> - `docs/debriefs/2026-04-28-paper-session-debrief.md` (read-only diagnostic)
>
> If a sealed file references something this checklist updates, that's a
> historical record — leave it alone. The cross-reference is correct AT
> THE TIME of the sealed artifact.

---

## Phase A — Pre-Sprint Housekeeping (CONFIRM-ONLY, already landed 2026-04-29)

The 7 cross-reference rename patches Claude recommended at Phase 0 were applied
by the operator on 2026-04-29 (confirmed via `git pull` against `main`). This
section is **verification-only** — do NOT re-apply patches. Run the verifications
below before Phase D prompt generation to confirm the state is what Phase A
assumed.

### A1. CLAUDE.md verification

```bash
# Active-sprint pointer mentions Sprint 31.92 with DEF-204 Round 2 framing.
grep -n 'Sprint 31.92.*DEF-204 Round 2' CLAUDE.md | head -2
# Expected: 2 hits (line 8 + line 22).

# DEF-208/211/212/215 routing columns updated to new sprint numbers.
grep -n 'Sprint 31.93\|Sprint 31.94\|Sprint 31.95' CLAUDE.md | wc -l
# Expected: ≥6 hits.

# DEF-211 routing references "Sprint 31.94" (not "Sprint 31.93").
grep -c 'DEF-211.*Sprint 31\.94\|Sprint 31\.94.*DEF-211' CLAUDE.md
# Expected: ≥1.

# DEF-212 routing references "Sprint 31.92 (DEF-204 Round 2)".
grep -c 'DEF-212.*Sprint 31\.92.*DEF-204 Round 2' CLAUDE.md
# Expected: ≥1.
```

If any verification fails, halt before Phase D and re-issue the original Phase 0
patch.

### A2. docs/roadmap.md verification

```bash
# Sprint 31.92 heading reflects DEF-204 Round 2 framing.
grep -n '#### Sprint 31\.92.*DEF-204 Round 2' docs/roadmap.md
# Expected: 1 hit at line ~676.

# Sprint 31.93/31.94/31.95 headings present.
grep -E '#### Sprint 31\.(93|94|95)' docs/roadmap.md | wc -l
# Expected: 3 hits.

# Old "post-31.9-*" sprint section headers either renamed or annotated as redirects.
grep -n '^#### post-31\.9-' docs/roadmap.md
# Expected: ≤1 hit (the `post-31.9-reconnect-recovery-and-rejectionstage` legacy
# anchor; body should redirect "→ now consolidated into Sprint 31.94").
```

### A3. Stale forward-pointers in DEC-385/386/388 (NO PATCH — leave-as-historical)

Per Phase A decision (2026-04-29), DEC-385/386/388 forward-pointers ("Sprint 31.92
inherits…", "Sprint 31.93 inherits…") are NOT amended in-place. The historical
record is preserved; DEC-390 (sprint-close) carries the forward-resolution.

```bash
# Confirm forward-pointers still present (they should be — leave-as-historical).
grep -c 'Sprint 31\.92 (component-ownership)\|Sprint 31\.93 (reconnect-recovery)\|Sprint 31\.94 (component-ownership)' docs/decision-log.md
# Expected: matches DEC-385/386/388's original forward-references; counts unchanged from pre-Phase-0 state.
```

If the operator decides AT SPRINT-CLOSE to amend DEC-385/386/388 forward-pointers
in-place, do so as a Phase C amendment item below. Until then: do not touch.

---

## Phase B — Mid-Sprint Sprint Spec Amendment (BEFORE Phase D prompt generation)

### B1. Sprint Spec AC5.3 — Composite validation reframed as Pytest integration test

**Discovered during:** Phase C session-breakdown scoring (artifact #4). S5b's compaction risk score forced demoting the standalone `validate_def204_round2_composite.py` script to a Pytest integration test (`test_composite_validation_*` in `tests/integration/test_def204_round2_validation.py`). The Sprint Spec's AC5.3 still reads as standalone-script.

**File:** `docs/sprints/sprint-31.92-def204-round-2/sprint-spec.md`

**Anchor:** Under §"Acceptance Criteria" Deliverable 5, the AC5.3 line.

```bash
# Locate before patching:
grep -n 'AC5.3' docs/sprints/sprint-31.92-def204-round-2/sprint-spec.md
```

**Patch (find/replace):**

<old>
**AC5.3:** `scripts/validate_def204_round2_composite.py` produces `scripts/spike-results/sprint-31.92-validation-composite.json` with `phantom_shorts_observed: 0` AND `ceiling_violations_observed: 0` (under benign load) AND `ceiling_violations_correctly_blocked: ≥1` (under adversarial load). Run at S5b.
</old>
<new>
**AC5.3:** Composite validation implemented as Pytest integration tests in `tests/integration/test_def204_round2_validation.py` (test names `test_composite_validation_zero_phantom_shorts_under_load` and `test_composite_validation_ceiling_blocks_under_adversarial_load`) — assertions: under benign synthetic-broker load, `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`; under adversarial synthetic-broker load (forced over-flatten attempts at all 5+ SELL emit sites), `ceiling_violations_correctly_blocked ≥ 1`. Run at S5b. **Amendment rationale (Phase C session-breakdown):** the standalone composite script was demoted to integration tests for compaction-risk discipline; Pytest-based assurance is functionally equivalent and avoids a 4th validation script with its own JSON-schema discipline. The two single-path validation scripts (`validate_def204_round2_path1.py` and `validate_def204_round2_path2.py`) and their JSON artifacts ARE preserved (AC5.1 and AC5.2 unchanged) because they serve as 30-day-freshness operational artifacts per regression invariant 18.
</new>

**Also update §"Deliverables" item 5:**

<old>
5. **Falsifiable end-to-end validation** — Synthetic SimulatedBroker scenarios for Path #1 (concurrent-trigger race), Path #2 (locate-rejection storm with held-order release), and composite (all 5+ SELL emit sites under load + ceiling enabled) produce ZERO phantom shorts. Validation scripts produce JSON artifacts under `scripts/spike-results/sprint-31.92-validation-{path1,path2,composite}.json`.
</old>
<new>
5. **Falsifiable end-to-end validation** — Synthetic SimulatedBroker scenarios for Path #1 (concurrent-trigger race) and Path #2 (locate-rejection storm with held-order release) produce ZERO phantom shorts; composite scenario (all 5+ SELL emit sites under load + ceiling enabled) is asserted via Pytest integration tests. Validation scripts produce JSON artifacts under `scripts/spike-results/sprint-31.92-validation-{path1,path2}.json`. (No standalone `*-composite.json` artifact; composite validation is in-suite.)
</new>

**Update §"Session Count Estimate":** No change to session count (still 10).

**Verified by:** Operator before Phase D prompt generation. The amendment lands as a single commit with message `[sprint-31.92] sprint-spec: amend AC5.3 — composite validation via Pytest, not standalone script`.

### B2. Doc Update Checklist self-amendment (this file)

After B1 lands, this checklist needs a one-line update to remove the now-obsolete `validate_def204_round2_composite.py` reference. The change is:

<old>
- `scripts/validate_def204_round2_{path1,path2,composite}.py` (new, S5a + S5b)
- `scripts/spike-results/sprint-31.92-validation-{path1,path2,composite}.json` (new, S5a + S5b)
</old>
<new>
- `scripts/validate_def204_round2_path1.py` (new, S5a)
- `scripts/validate_def204_round2_path2.py` (new, S5b)
- `scripts/spike-results/sprint-31.92-validation-path1.json` (new, S5a, autogenerated + committed)
- `scripts/spike-results/sprint-31.92-validation-path2.json` (new, S5b, autogenerated + committed)
- `tests/integration/test_def204_round2_validation.py` (new, extended at S5b for composite — replaces standalone composite script)
</new>

(In the `design-summary.md` Phase B artifact, similar amendment.)

**Note:** B1 and B2 should be applied in the same commit so the spec and the doc-update-checklist stay synchronized.

---

## Phase C — Sprint-Close (D14) Doc-Sync (POST-S5b)

Apply these updates after S5b close-out lands cleanly on `main` and Tier 2 verdict is CLEAR. The doc-sync follows `protocols/mid-sprint-doc-sync.md` Pattern B (deferred materialization at sprint-close) — DEC-390 is the principal materialization. If Tier 3 escalates mid-sprint and produces material findings, Pattern A applies and DEC-390 may materialize earlier.

### C1. CLAUDE.md — DEF-204 / DEF-212 status updates + active-sprint pointer

#### C1.1. DEF-204 row → RESOLVED-PENDING-PAPER-VALIDATION

Per SbC §"Edge Cases to Reject" #14, DEF-204 is NOT marked fully RESOLVED at sprint-merge — only after cessation criterion #5 (5 paper sessions clean post-Sprint-31.92 seal) is satisfied.

**Anchor:** The DEF-204 row in the `## DEFs` table.

**Patch:**

<old>
| DEF-204 | **CRITICAL SAFETY — Upstream cascade of unexpected shorts, independent of DEF-199.** [...] | IMPROMPTU-11 ✅ DIAGNOSTIC COMPLETE (Sprint 31.9 Stage 9C, 2026-04-24); fix → `post-31.9-reconciliation-drift` (new named horizon sprint, post-campaign) | **CRITICAL SAFETY** — fix must land before live trading. DEF-204 remains OPEN — fix deferred to `post-31.9-reconciliation-drift` per IMPROMPTU-11 kickoff scope (adversarial review + non-safe-during-trading constraint apply). |
</old>
<new>
| DEF-204 | **CRITICAL SAFETY — Upstream cascade of unexpected shorts, independent of DEF-199.** [previous body preserved verbatim through "Cross-refs:..."] **MECHANISM IDENTIFIED (IMPROMPTU-11, 2026-04-24)** [body preserved through end of mechanism diagnosis]. **PARTIAL CLOSURE (Sprint 31.91, DEC-385 + DEC-386 + DEC-388, 2026-04-28):** ~98% of mechanism closed via OCA-Group Threading + Side-Aware Reconciliation. **EMPIRICALLY FALSIFIED 2026-04-28** (60 NEW phantom shorts during paper session — Path #1 trail-stop/bracket-stop concurrent-trigger race + Path #2 locate-rejection-as-held retry storm). Diagnostic at `docs/debriefs/2026-04-28-paper-session-debrief.md`. **MECHANISM CLOSURE COMPLETED (Sprint 31.92, DEC-390, {SPRINT_CLOSE_DATE}):** four-layer composition — L1 Path #1 cancel-and-await mechanism (or amend per S1a spike); L2 Path #2 locate-rejection fingerprint + suppression; L3 long-only SELL-volume ceiling; L4 DEF-212 rider. Falsifiable validation artifacts at `scripts/spike-results/sprint-31.92-validation-path{1,2}.json`. | Sprint 31.92 ✅ MECHANISM CLOSED (DEC-390); DEF-204 marked **RESOLVED-PENDING-PAPER-VALIDATION** at sprint-seal. **OPERATIONAL CLOSURE PENDING:** cessation criterion #5 (5 paper sessions clean post-Sprint-31.92 seal) — in progress, 0/5 at sprint-close. | **CRITICAL SAFETY** — Sprint 31.92 mechanism closure landed; live trading remains gated by cessation criterion #5 + Sprint 31.91 §D7 pre-live paper stress test under live-config simulation (DEF-208 — separately scoped). |
</new>

(Implementer: replace `{SPRINT_CLOSE_DATE}` with the actual D14 date, format `YYYY-MM-DD`.)

#### C1.2. DEF-212 row → RESOLVED

**Anchor:** The DEF-212 row.

**Patch:**

<old>
| DEF-212 | **Sprint 31.93 component-ownership refactor MUST wire `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` and replace the `_OCA_TYPE_BRACKET = 1` module constant.** [...]
</old>
<new>
| ~~DEF-212~~ | ~~Sprint 31.92 (DEF-204 Round 2) MUST wire `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` and replace the `_OCA_TYPE_BRACKET = 1` module constant.~~ | ✅ **RESOLVED** (Sprint 31.92 S4b, {SPRINT_CLOSE_DATE}, DEC-390 L4): `OrderManager.__init__` now accepts `bracket_oca_type: int` keyword argument; `argus/main.py` construction site passes `config.ibkr.bracket_oca_type`; the 4 occurrences of `_OCA_TYPE_BRACKET` module constant in `argus/execution/order_manager.py` replaced by `self._bracket_oca_type`; the module constant deleted. Grep regression guard `tests/execution/order_manager/test_def212_oca_type_wiring.py::test_no_oca_type_bracket_constant_remains_in_module` enforces deletion. Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) remains DEFERRED to Sprint 31.93 (component-ownership scope per SbC §"Out of Scope" #4). |
</new>

#### C1.3. Active-sprint pointer (lines 8 + 22) — clear Sprint 31.92, advance to next horizon

**Anchor:** Lines 8 + 22 in `CLAUDE.md`.

**Patch (line 8):**

<old>
**None — between sprints.** Sprint 31.91 sealed at D14 doc-sync 2026-04-28. [...] Next named horizons: **Sprint 31.92 (DEF-204 Round 2 — Path #1 trail-stop/bracket-stop concurrent-trigger race + Path #2 locate-rejection-as-held retry storm + DEF-212 rider)**, [...]
</old>
<new>
**None — between sprints.** Sprint 31.92 sealed at D14 doc-sync {SPRINT_CLOSE_DATE}. **Cessation criterion #5 counter RESET to 0/5** for the new post-Sprint-31.92 paper-session window — operator continues to run `scripts/ibkr_close_all_positions.py` daily until criterion #5 satisfied (5 paper sessions clean post-Sprint-31.92 seal). 22 shadow variants still collecting CounterfactualTracker data. **Next named horizons:** Sprint 31B (Research Console / Variant Factory), Sprint 31.93 (`post-31.9-component-ownership` — DEF-175/182/193/201/202; absorbs Tier 3 #1 Concern A `_is_oca_already_filled_error` relocation + DEF-208 live-trading test fixture), Sprint 31.94 (DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound + DEF-194/195/196 reconnect-recovery — likely first DEF-222 audit firing surface), Sprint 31.95 (`post-31.9-alpaca-retirement` — DEF-178/183).
</new>

**Similar update at line 22** — clear "Sprint 31.92" from the next-named-horizons list and replace the `## Active sprint` long-form block to reference Sprint 31.92's seal status. (Implementer: produce surgical find-and-replace at sprint-close based on actual file state.)

### C2. docs/decision-log.md — Write DEC-390 below

**Anchor:** Append after DEC-389 (Sprint 31.915 evaluation.db retention).

**Pattern:** B (Pattern A applies if Tier 3 fires mid-sprint). Per `protocols/mid-sprint-doc-sync.md` v1.0.0.

**DEC-390 entry skeleton** (template — populated at sprint-close with actual mechanism choice, validation artifact paths, and cross-references):

```markdown
### DEC-390 | Concurrent-Trigger Race Closure + Locate-Rejection Hold Detection + Long-Only SELL-Volume Ceiling

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 (sealed {SPRINT_CLOSE_DATE}) |
| **Tier 3 verdict** | {Tier 3 fired? PROCEED-with-conditions / not required — fill at close} |
| **Context** | Sprint 31.91's DEC-386 claimed `~98%` closure of DEF-204 mechanism via OCA-Group Threading + Broker-Only Safety. Tier 3 #1 (2026-04-27) verdict PROCEED. **Empirically falsified 2026-04-28** by paper-session debrief (`docs/debriefs/2026-04-28-paper-session-debrief.md`): 60 NEW phantom shorts post-DEC-386 across two distinct uncovered paths — (Path #1) trail-stop / bracket-stop concurrent-trigger race; canonical trace BITU 13:36→13:41 producing 182-share phantom short via simultaneous fire of trail-flatten market and bracket-stop trigger price. (Path #2) locate-rejection-as-held retry storm; canonical trace PCT producing 3,837-share phantom short via IBKR returning `"contract is not available for short sale"` (held-pending-borrow) followed by ARGUS retry loop and IBKR's batch release of queued held orders. DEC-386's `~98%` claim was made in good faith from data available at Tier 3 #1 (24-hour pre-paper-session window); the falsification is acknowledged here, DEC-386 itself preserved unchanged (leave-as-historical posture). |
| **Decision** | Adopt a 4-layer composition mirroring DEC-385/386's layered-decomposition pattern: **(L1 Path #1 mechanism, S2a + S2b)** — chosen mechanism: {ONE OF: cancel-and-await before SELL using DEC-386 S0's `cancel_all_orders(symbol, await_propagation=True)` infrastructure / amend bracket stop's price via `modifyOrder` / hybrid amend-with-fallback}. Selected based on Phase A spike S1a (`scripts/spike-results/spike-def204-round2-path1-results.json`, dated {S1a_DATE}) which measured {SPIKE_S1a_FINDINGS}. Applied to `_trail_flatten`, `_resubmit_stop_with_retry` emergency-flatten branch, and {conditionally} `_escalation_update_stop`. AMD-2 invariant ("sell before cancel") in `_trail_flatten` {INTENTIONALLY MODIFIED if H1; PRESERVED if H2}. **(L2 Path #2 fingerprint + suppression, S3a + S3b)** — Add `_LOCATE_REJECTED_FINGERPRINT = "contract is not available for short sale"` (case-insensitive substring) and `_is_locate_rejection(error: BaseException) -> bool` helper in `argus/execution/ibkr_broker.py`, mirroring DEC-386's `_is_oca_already_filled_error` pattern. Add `OrderManager._locate_suppressed_until: dict[str, float]` symbol-keyed suppression state with `OrderManagerConfig.locate_suppression_seconds` (default 300s, validated by S1b spike at p99 release window {SPIKE_S1b_FINDINGS}). Wire suppression detection at `place_order` exception in 4 standalone-SELL paths (`_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts`, `_escalation_update_stop`) with pre-emit suppression check. Suppression-timeout fallback publishes existing DEC-385 `phantom_short_retry_blocked` SystemAlertEvent (no new alert type). DEF-158's 3-branch side-check (BUY → resubmit / SELL → alert+halt / unknown → halt) preserved verbatim — Path #2 detection is structurally upstream. **(L3 Long-only SELL-volume ceiling, S4a)** — Add `ManagedPosition.cumulative_sold_shares: int = 0` field (per-position, NOT per-symbol; AC3.4); increment in `on_fill` for confirmed SELL fills. Add `_check_sell_ceiling(position, requested_qty) -> bool` helper. Guard at all 5+ SELL emit sites: assert `cumulative_sold_shares + requested_qty ≤ shares_total` BEFORE `place_order(SELL)`. Violations refuse the SELL, emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical")`, log CRITICAL. Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`, fail-closed). New `POLICY_TABLE` entry (14th) for `sell_ceiling_violation` (`operator_ack_required=True`, `auto_resolution_predicate=None`); AST policy-table exhaustiveness regression guard updated. **(L4 DEF-212 rider, S4b)** — `OrderManager.__init__` accepts `bracket_oca_type: int` keyword argument; `argus/main.py` construction call site passes `config.ibkr.bracket_oca_type`; 4 occurrences of `_OCA_TYPE_BRACKET = 1` module constant replaced by `self._bracket_oca_type`; module constant deleted. Grep regression guard. Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) explicitly DEFERRED to Sprint 31.93 (component-ownership scope). |
| **Rationale** | DEF-204's mechanism is composite: (Path #1) is a fill-side race that DEC-386 S1b OCA threading does NOT cover (concurrent triggers fire both legs before OCA cancellation can propagate); (Path #2) is a misclassification — IBKR's "contract not available for short sale" is a HOLD pending borrow, NOT a transient reject, and ARGUS's retry layer treats it as transient. Both paths produce phantom shorts that are observable but not preventable by Sprint 31.91's mechanism. The architectural fix at L1 + L2 is structural: DEC-386 enforces atomic OCA at the broker layer; DEC-390 L1 ensures only ONE leg can be in flight at once on the trail-stop / emergency-flatten paths; DEC-390 L2 detects the hold-pending-borrow state and suppresses retry-storm SELL emission. L3 (ceiling) is structural defense-in-depth — even if a future yet-unidentified Path #3 surfaces, L3 prevents the resulting over-flatten from materializing. L4 (DEF-212 wiring) is cosmetic technical debt cleanup that piggybacks on the OrderManager construction-site touches. The 4-layer layering across S2a–S5b makes each step self-contained and individually testable; the regression-checklist invariant 13 + 14 + 15 + 16 + 17 + 18 collectively enforce monotonic safety. The Phase A spike's S1a + S1b PROCEED outcomes are the falsifiable foundation; the S5a + S5b validation artifacts are the falsifiable end-to-end gate. |
| **Impact** | DEF-204's Path #1 + Path #2 mechanisms structurally closed by L1 + L2; remaining mechanism residue (broker-only events not flowing through OCA, operator manual orders, future API drift) is bounded by L3 ceiling. DEC-386's `~98%` claim is empirically REPLACED by DEC-390's two-path-specific closures + structural defense; no aggregate percentage claim made (per process-evolution lesson F.5 — empirical claims invite falsification; structural closures + falsifiable validation artifacts replace them). Operator daily-flatten mitigation cessation criteria #1+#2+#3 SATISFIED (via Sprint 31.91 + 31.92 cumulative); #4 (Sprint 31.92 sealed) MET at {SPRINT_CLOSE_DATE}; **#5 RESET TO 0/5** — 5 paper sessions clean post-Sprint-31.92 seal needed. Live-trading readiness requires: (1) Sprint 31.92 sealed cleanly; (2) ≥5 paper sessions clean post-seal (criterion #5 satisfied); (3) DEF-208 pre-live paper stress test under live-config simulation (Sprint 31.93 OR 31.94); (4) Sprint 31.91 §D7 gate criteria. Sprint 31.93 inherits DEF-212 Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation). Sprint 31.94 inherits DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound + reconnect-event coupling for L2 suppression dict (locate-suppression dict's reconnect-blindness flagged in SbC §"Edge Cases to Reject" #5). New risks filed: RSK-DEC-390-AMEND (if H2 amend mechanism selected; IBKR API version assumption), RSK-DEC-390-FINGERPRINT (locate-rejection error string drift; quarterly re-validation flag), RSK-CEILING-FALSE-POSITIVE (fill-callback ordering / partial-fill aggregation), RSK-SUPPRESSION-LEAK (dict GC bound to EOD teardown — adequate for paper, acceptable for live with reconnect-recovery). |
| **Cross-References** | **DEFs:** DEF-204 (closed by mechanism — RESOLVED-PENDING-PAPER-VALIDATION at sprint-close, RESOLVED at criterion #5 satisfaction); DEF-212 (closed by L4 — RESOLVED). **Predecessor DECs:** DEC-385 (Side-Aware Reconciliation Contract — preserved byte-for-byte; `phantom_short_retry_blocked` alert path reused at L2 fallback); DEC-386 (OCA-Group Threading + Broker-Only Safety — preserved byte-for-byte; `~98%` claim empirically superseded by DEC-390's structural closure); DEC-388 (Alert Observability Architecture — `POLICY_TABLE` extended with 14th entry for `sell_ceiling_violation`; existing 13 entries unchanged). **Adjacent DECs:** DEC-117 (atomic bracket — preserved); DEC-364 (cancel_all_orders ABC — preserved, no extension); DEC-369 (broker-confirmed reconciliation — preserved; AC3.5 ceiling initialization composes additively); DEC-372 (stop retry caps — preserved; L1 cancel-and-await applies to emergency-flatten branch). **Validation artifacts:** S1a spike `scripts/spike-results/spike-def204-round2-path1-results.json` (PROCEED, valid ≤30 days); S1b spike `scripts/spike-results/spike-def204-round2-path2-results.json` (PROCEED, valid ≤30 days); S5a validation `scripts/spike-results/sprint-31.92-validation-path1.json` (`path1_safe: true`); S5b validation `scripts/spike-results/sprint-31.92-validation-path2.json` (`path2_suppression_works: true`); S5b composite Pytest `tests/integration/test_def204_round2_validation.py` (green). **Diagnostic source:** `docs/debriefs/2026-04-28-paper-session-debrief.md`. **Risks:** RSK-DEC-390-AMEND, RSK-DEC-390-FINGERPRINT, RSK-CEILING-FALSE-POSITIVE, RSK-SUPPRESSION-LEAK. **Time-bounded:** L2 suppression dict reconnect-event coupling deferred to Sprint 31.94 — locate-suppression dict will need to clear on `IBKRReconnectedEvent` once that producer lands. **Process-evolution lesson F.5:** "Empirical aggregate claims invite empirical falsification; structural closures + falsifiable validation artifacts replace aggregate percentages." Captured for next campaign's RETRO-FOLD. **Tier 3 verdict artifact:** {if Tier 3 #1 fired mid-sprint: `docs/sprints/sprint-31.92-def204-round-2/tier-3-review-{N}-verdict.md`; else: N/A — adversarial Tier 2 covered architectural review at Phase C-1}. |
```

(Sprint-close authoring fills in `{SPRINT_CLOSE_DATE}`, `{Tier 3 verdict}`, `{ONE OF: cancel-and-await/amend/hybrid}`, `{S1a_DATE}`, `{SPIKE_S1a_FINDINGS}`, `{SPIKE_S1b_FINDINGS}`. The DEC-390 entry as written above is the authoring template; verbatim text inserts post-spike-completion.)

### C3. docs/dec-index.md — Add DEC-390 entry

**Anchor:** Append in chronological order after DEC-389.

```markdown
| DEC-390 | Concurrent-Trigger Race Closure + Locate-Rejection Hold Detection + Long-Only SELL-Volume Ceiling | ACTIVE | Sprint 31.92 ({SPRINT_CLOSE_DATE}) | DEF-204, DEF-212, DEC-385, DEC-386, DEC-388 |
```

### C4. docs/sprint-history.md — Add Sprint 31.92 row

**Anchor:** Append after Sprint 31.91 / 31.915 row.

```markdown
| 31.92 | DEF-204 Round 2 (Path #1 trail-stop/bracket-stop race + Path #2 locate-rejection hold + ceiling + DEF-212 rider) | {pytest count}+{Vitest count}V | {sprint dates} | DEC-390 |
```

(Plus per-sprint detail subsection following the §"Sprint 31.91 — Reconciliation Drift" pattern: 10 sessions enumerated, key findings, validation artifacts cited.)

### C5. docs/roadmap.md — Sprint 31.92 close-out narrative + horizon shift

**Anchor:** The `#### Sprint 31.92 — DEF-204 Round 2 (...)` section header (already in place from Phase 0).

**Patch:** Replace the section body (currently a placeholder per Phase 0 Edit 8 minimal-patch) with full close-out narrative:

```markdown
#### Sprint 31.92 — DEF-204 Round 2 (Trail-Stop / Bracket-Stop Race + Locate-Rejection Hold + DEF-212 Rider)

**Status:** SEALED {SPRINT_CLOSE_DATE}. DEC-390 materialized at sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0).

**Goal:** Close the two uncovered DEF-204 mechanism paths surfaced by the 2026-04-28 paper-session debrief — Path #1 (trail-stop / bracket-stop concurrent-trigger race; canonical trace BITU 13:41 producing 182-share phantom short) and Path #2 (locate-rejection-as-held retry storm; canonical trace PCT producing 3,837-share phantom short) — plus a structural long-only SELL-volume ceiling on `ManagedPosition` as defense-in-depth, plus the DEF-212 `_OCA_TYPE_BRACKET` constant-drift rider. Resolves residual ~2% of DEF-204's mechanism that DEC-386 did not cover.

**Sessions:** 10 ({COUNT_S1a-S5b}). 2 spike sessions (S1a + S1b) gated Phase D impl prompts for the Path #1 and Path #2 mechanism choices. 8 implementation/validation sessions delivered the 4-layer DEC-390 architecture.

**Key DECs:** DEC-390 (4-layer Concurrent-Trigger Race Closure + Locate-Rejection Hold Detection + Long-Only SELL-Volume Ceiling).

**State after:** DEF-204 RESOLVED-PENDING-PAPER-VALIDATION; DEF-212 RESOLVED. Cessation criterion #5 RESET to 0/5 — operator continues `scripts/ibkr_close_all_positions.py` daily until 5 paper sessions clean post-Sprint-31.92 seal. Sprint 31.93 inherits Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) + DEF-208 live-trading test fixture. Sprint 31.94 inherits DEF-211 D1+D2+D3 + DEF-194/195/196 reconnect-recovery + locate-suppression dict's reconnect-event coupling.

**Adversarial review:** {fired? what was found? include if applicable}.

**Sprint folder canonical artifacts:** `docs/sprints/sprint-31.92-def204-round-2/{design-summary.md, sprint-spec.md, spec-by-contradiction.md, session-breakdown.md, escalation-criteria.md, regression-checklist.md, doc-update-checklist.md, adversarial-review-input-package.md}` plus 10 session closeouts + 10 session reviews + (if applicable) Tier 3 verdict artifact(s) + 2 spike-results JSONs + 2 validation-results JSONs.

**Process-evolution lesson F.5 (proposed):** Empirical aggregate claims (e.g., DEC-386's `~98%` mechanism closure) invite empirical falsification when paper-session reality contradicts the claim. Structural closures (DEC-390's 4 layers) + falsifiable validation artifacts (S5a + S5b JSONs + composite Pytest) replace aggregate percentage claims. Captured for next campaign's RETRO-FOLD.
```

### C6. docs/project-knowledge.md — DEF table sync + Sprint 31.92 row

**Anchor:** The `## Current State` block + `### Sprint History (Summary)` table.

**Patch:** Mirror the CLAUDE.md updates from C1.1 + C1.2 (DEF-204 + DEF-212 status) + add Sprint 31.92 row to history table. Surgical find-and-replace; same structural anchors.

### C7. docs/architecture.md — §3.7 OrderManager additions

**Anchor:** §3.7 Order Manager block.

**Additive content (NOT a structural rewrite — per SbC §"Out of Scope" #17):**

```markdown
**Sprint 31.92 additions (DEC-390):**
- **`ManagedPosition.cumulative_sold_shares: int`** — per-position SELL-volume running sum, incremented in `on_fill` for confirmed SELL fills. Enables long-only SELL-volume ceiling (`cumulative_sold_shares ≤ shares_total`). In-memory only (NOT persisted; `reconstruct_from_broker`-derived positions initialize to 0). Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`).
- **`OrderManager._locate_suppressed_until: dict[str, float]`** — symbol-keyed suppression state for IBKR locate-rejection holds. Set when `_is_locate_rejection()` matches; checked before SELL emit at all 4 standalone-SELL paths; cleared on fill callback OR window expiry. Default suppression window 300s (`OrderManagerConfig.locate_suppression_seconds`).
- **`bracket_oca_type` flow** — `IBKRConfig.bracket_oca_type` (Pydantic field, range `[0, 1]`, default `1`) → `OrderManager.__init__(bracket_oca_type)` → `self._bracket_oca_type` (replaces former `_OCA_TYPE_BRACKET` module constant). Operator-flipped to 0 produces consistent `ocaType=0` on bracket children AND standalone-SELL OCA threading (no divergence).
- **Path #1 mechanism** — Trail-stop / bracket-stop concurrent-trigger race closed via {cancel-and-await before SELL on `_trail_flatten` + `_resubmit_stop_with_retry` emergency path / amend bracket stop's price via `modifyOrder`} (S1a-spike-selected). AMD-2 invariant {INTENTIONALLY MODIFIED if H1 / PRESERVED if H2}.
- **Path #2 detection** — IBKR rejection error string `"contract is not available for short sale"` fingerprinted via `_is_locate_rejection()` in `argus/execution/ibkr_broker.py`; symbol suppressed for `locate_suppression_seconds`; suppression-timeout fallback publishes `phantom_short_retry_blocked` (DEC-385 reuse).
```

### C8. docs/risk-register.md — File 4 new RSKs + DEC-386 status update

#### C8.1. RSK-DEC-390-AMEND (CONDITIONAL — only if S1a selected H2)

```markdown
### RSK-DEC-390-AMEND | Path #1 Amend-Stop-Price IBKR API Version Assumption

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene) |
| **Severity** | LOW |
| **Description** | DEC-390 L1 selected H2 (amend bracket stop's price via `modifyOrder`) per S1a spike. The amend-stop-price path depends on IBKR's `modifyOrder` semantics being deterministic at sub-50ms latency. If a future IBKR API change introduces non-determinism (e.g., amend acknowledgment delay, amend-rejection rate increase), the mechanism degrades silently — phantom shorts may re-emerge without an explicit error. |
| **Mitigation** | (a) S2a regression test asserts mock `IBKRBroker.modify_order` was called BEFORE `place_order(SELL)` — any code-path bypass is caught immediately. (b) `docs/live-operations.md` paragraph documents the IBKR-API-version assumption + quarterly operational re-validation flag. (c) Cessation criterion #5 (5 paper sessions clean post-seal) is itself a continuous validation. |
| **Trigger conditions** | (1) IBKR Gateway upgrade. (2) `ib_async` library upgrade. (3) Quarterly re-validation cycle. (4) ANY paper-session phantom short matching Path #1 signature post-seal. |
| **Cross-References** | DEC-390 L1; S1a spike artifact; `docs/live-operations.md` (post-sprint paragraph). |
```

(File ONLY if H2 selected. If H1 cancel-and-await selected, this RSK is N/A — replace with RSK-DEC-390-CANCEL-AWAIT-LATENCY about the 50–200ms unprotected gap acceptance.)

#### C8.2. RSK-DEC-390-FINGERPRINT (UNCONDITIONAL)

```markdown
### RSK-DEC-390-FINGERPRINT | Locate-Rejection Error-String Drift

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene) |
| **Severity** | LOW–MEDIUM |
| **Description** | `_is_locate_rejection()` substring fingerprint depends on IBKR's exact rejection error string `"contract is not available for short sale"`. If IBKR changes this string in a future API update, locate-rejection detection silently fails — Path #2 retry storm re-emerges. The substring approach was selected at S3a because S1b spike confirmed string stability across 50+ trials, BUT future API changes are uncontrolled. |
| **Mitigation** | (a) S5b validation re-runs against synthetic locate-rejection fixture; if string drifts, fixture and production code diverge but production code path falls through to existing CRITICAL-log path (NOT silent failure — observable via the existing post-fix debugging cycle). (b) Quarterly operational re-validation flag — operator runs `scripts/spike_def204_round2_path2.py` against live paper IBKR every quarter and asserts string match. (c) CI check (added at S5b) that `scripts/spike-results/spike-def204-round2-path2-results.json` is < 90 days old. |
| **Trigger conditions** | (1) IBKR Gateway upgrade. (2) `ib_async` library upgrade. (3) Quarterly re-validation cycle. (4) ANY paper-session phantom short matching Path #2 signature post-seal. (5) Spike artifact age ≥ 90 days. |
| **Cross-References** | DEC-390 L2; S1b spike artifact; A-class halt A13 (escalation-criteria.md). |
```

#### C8.3. RSK-CEILING-FALSE-POSITIVE (UNCONDITIONAL)

```markdown
### RSK-CEILING-FALSE-POSITIVE | Long-Only SELL-Volume Ceiling False-Positive on Fill-Callback Ordering

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (mitigated by S5b composite test + A-class halt A11) |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L3 ceiling (`cumulative_sold_shares ≤ shares_total`) increments in `on_fill` for confirmed SELL fills. Edge cases: (a) broker fill callback arrives out-of-order (e.g., bracket-stop fill arrives after trail-flatten fill due to network reordering), or (b) partial-fill granularity differs between SimulatedBroker and IBKR (e.g., 100-share fill arrives as 50+50 in two callbacks vs single 100). Either could produce off-by-one transient state where a legitimate SELL is refused. |
| **Mitigation** | (a) AC3.1 increments AT confirmed fill (not at order placement); partial-fill aggregation in `on_fill` already handles existing T1/T2 paths. (b) S5b composite Pytest stresses 5+ SELL emit sites with parametrized partial-fill scenarios. (c) A-class halt A11 fires if any false-positive observed in production paper trading; Tier 3 reviews fix path (default option (a) tighten fill-callback aggregation). |
| **Trigger conditions** | (1) Production paper-session WARN/ERROR log line `sell_ceiling_violation` for a position with sound long-history. (2) Operator-reported "SELL was refused but I haven't sold anything yet" diagnostic. |
| **Cross-References** | DEC-390 L3; AC3.1; A-class halt A11; SbC §"Adversarial Review Reference" item #5. |
```

#### C8.4. RSK-SUPPRESSION-LEAK (UNCONDITIONAL)

```markdown
### RSK-SUPPRESSION-LEAK | Locate-Suppression Dict GC Bound to EOD Teardown

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN — adequate for paper trading; couples with Sprint 31.94 reconnect-recovery |
| **Severity** | LOW |
| **Description** | `OrderManager._locate_suppressed_until: dict[str, float]` accumulates symbol entries; entries clear on (a) fill callback, (b) suppression-timeout fallback publication, or (c) EOD OrderManager teardown. If a symbol is suppressed BUT no subsequent SELL emit fires for it during the session AND the timeout never matches a housekeeping-loop tick, the dict entry persists until EOD. Mid-session reconnect would also leave entries (Sprint 31.94 surface — locate-dict reconnect-event coupling deferred). |
| **Mitigation** | (a) Suppression-timeout fallback (AC2.5) explicitly clears the dict entry on alert publication. (b) `_check_flatten_pending_timeouts` housekeeping loop runs at fixed cadence (existing 60s default per `flatten_pending_timeout_seconds`); timeout detection is bounded. (c) EOD teardown (existing) clears dict. (d) S5b stress test asserts dict cleared at session-end. |
| **Trigger conditions** | (1) Mid-session reconnect (Sprint 31.94 reconnect-recovery couples this RSK to `IBKRReconnectedEvent` consumer logic). (2) Operator-observed dict size > 100 entries mid-session (informational; no production harm). |
| **Cross-References** | DEC-390 L2; SbC §"Edge Cases to Reject" #5; Sprint 31.94 deferred-coupling note. |
```

#### C8.5. DEC-386 status annotation

**Anchor:** The DEC-386 row in `docs/risk-register.md` (if present; otherwise add a brief entry).

**Patch:**

<old>
{whatever existing DEC-386 risk row is — Phase A flagged "preserve as-is" but does need a status annotation referencing DEC-390}
</old>
<new>
**DEC-386 status annotation (added by Sprint 31.92 doc-sync):** DEC-386's `~98%` mechanism-closure claim was empirically falsified 2026-04-28 (60 phantom shorts in single paper session). DEC-390 (Sprint 31.92) closes the two uncovered paths structurally + adds defense-in-depth ceiling. DEC-386 itself preserved unchanged (leave-as-historical). No risk register action required for DEC-386 specifically; cross-reference DEC-390 for current closure state.
</new>

### C9. docs/pre-live-transition-checklist.md — Verify ceiling defaults

**Anchor:** The `## Config Restoration` block.

**Add item:**

```markdown
- [ ] `OrderManagerConfig.long_only_sell_ceiling_enabled` set to `true` in `config/system_live.yaml` (default true; verify operator hasn't overridden during paper trading).
- [ ] `OrderManagerConfig.long_only_sell_ceiling_alert_on_violation` set to `true` (default true; same).
- [ ] `OrderManagerConfig.locate_suppression_seconds` set to operator-validated value (default 300s post-S1b spike; if operator widened to e.g. 600s, ensure documented).
- [ ] `IBKRConfig.bracket_oca_type` set to `1` (DEC-386 + DEC-390 default; do NOT enable `0` rollback for live trading).
- [ ] `scripts/spike-results/spike-def204-round2-path{1,2}-results.json` artifacts dated < 30 days; if older, re-run spikes (A-class halt A13).
- [ ] Cessation criterion #5 satisfied: 5 consecutive paper sessions clean post-Sprint-31.92 seal (zero phantom_short or sell_ceiling_violation alerts).
```

### C10. docs/process-evolution.md — Capture lesson F.5

**Anchor:** Append after F.4.

```markdown
### F.5 — Empirical aggregate claims invite empirical falsification

**Origin:** Sprint 31.92 retrospective (DEF-204 Round 2). Sprint 31.91's DEC-386 made a `~98% mechanism closure` claim at Tier 3 #1 (2026-04-27). 24 hours later (2026-04-28 paper session), 60 NEW phantom shorts surfaced two distinct uncovered paths — falsifying the aggregate claim. Sprint 31.92's DEC-390 deliberately AVOIDS aggregate percentage claims; instead, each layer (L1/L2/L3/L4) is structurally closed with falsifiable validation artifacts (S1a/S1b spike JSONs + S5a/S5b validation JSONs + S5b composite Pytest). The composition is the closure, not a percentage.

**Workflow implication:** When authoring DEC entries for safety-critical mechanism closures, prefer (a) structural closures with named coverage surfaces, (b) falsifiable validation artifacts with documented expiry windows, over (c) aggregate confidence claims. Aggregate claims tempt empirical falsification because production reality is a richer distribution than test fixtures. The DEC author's confidence is a private signal; the DEC reader needs structural assurance + a falsification protocol if reality diverges.

**Captured at:** Sprint 31.92 sprint-close ({SPRINT_CLOSE_DATE}). Folds into next campaign's RETRO-FOLD.
```

---

## Phase D — Cessation Criterion #5 Counter Reset (post-D14)

After D14 doc-sync lands, the cessation-criterion #5 counter resets to 0/5. Operator continues running `scripts/ibkr_close_all_positions.py` daily. Each subsequent paper session is evaluated against the criterion (zero `phantom_short` alerts AND zero `sell_ceiling_violation` alerts AND zero `phantom_short_retry_blocked` alerts during session). At 5/5, DEF-204 transitions from RESOLVED-PENDING-PAPER-VALIDATION to RESOLVED, and the operator daily-flatten mitigation can be retired (or kept as belt-and-braces — operator decision).

**Cessation tracking artifact:** `docs/operations/cessation-criterion-5-counter.md` (NEW — created at sprint-close, updated after each paper session post-merge). Format:

```markdown
# Cessation Criterion #5 — Sprint 31.92 Post-Seal Counter

Tracks 5 consecutive paper sessions clean post-Sprint-31.92 seal ({SPRINT_CLOSE_DATE}). Criterion definition: ZERO `phantom_short`, `sell_ceiling_violation`, OR `phantom_short_retry_blocked` alerts during the session.

| Date | Session ID | Phantom Shorts | Ceiling Violations | Locate Retry Blocks | Counter | Notes |
|------|-----------|---------------:|-------------------:|--------------------:|--------:|-------|
| TBD | session-1 | 0 | 0 | 0 | 1/5 | (post-merge first session) |
| ... | | | | | | |
```

(Counter resets to 0 if any session shows non-zero alerts; criterion reset triggers debrief.)

---

## Summary

**Phase A (pre-sprint):** ✅ COMPLETE. Verification-only. Operator applied 7 cross-reference patches 2026-04-29.

**Phase B (mid-sprint, before Phase D):** ⏸️ PENDING. AC5.3 amendment to Sprint Spec + this doc-update-checklist self-amendment. Single commit.

**Phase C (sprint-close, post-S5b):** ⏸️ PENDING. 10 doc-sync items. DEC-390 written below per Pattern B. 4 new RSKs filed. Lesson F.5 captured. Cessation-criterion counter reset to 0/5. Tracking artifact created.

**Phase D (post-seal operational):** ⏸️ PENDING. Operator runs cessation-criterion-5 counter post-merge until 5/5 satisfied; DEF-204 transitions RESOLVED-PENDING-PAPER-VALIDATION → RESOLVED.