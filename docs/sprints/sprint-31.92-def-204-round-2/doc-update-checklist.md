# Sprint 31.92: Doc Update Checklist

> **Phase C artifact 7/8 (revised post-Round-1).** Three-phase doc update plan
> covering pre-sprint housekeeping (Phase A), mid-sprint Sprint Spec amendment
> (Phase B), and sprint-close (D14) doc-sync (Phase C). Each entry specifies
> the exact file, anchor, and patch text or skeleton.
>
> **Revision history:** Round 1 authored 2026-04-28 with Phase A (pre-sprint) confirm-only + Phase B (Sprint Spec AC5.3 amendment) + Phase C (sprint-close, 10 doc-sync items + 4 RSKs + lesson F.5). Round-1-revised 2026-04-29: Phase B B1 patch updated for AC5.3 Pytest-side-effect framing (M-3); B2 reframed as Design Summary alignment; DEC-390 entry skeleton in C2 expanded with H2 default mechanism + pending-reservation L3 + `is_reconstructed` AC3.7 + AC4.6 startup warning; C7 architecture.md additive content updated; C8 RSKs revised — RSK-DEC-390-AMEND remains primary (H2 default), NEW RSK-DEC-390-CANCEL-AWAIT-LATENCY (H1/H4 fallback path conditional), RSK-CEILING-FALSE-POSITIVE expanded for pending-reservation race scenarios, NEW RSK-RECONSTRUCTED-POSITION-DEGRADATION (Sprint 31.94 D3 dependency), NEW RSK-SUPPRESSION-LEAK; C9 pre-live checklist additions for new fields; C10 lesson F.5 framing tightened for "structural closure" pattern.

---

## Phase A — Pre-Sprint Housekeeping (CONFIRM-ONLY, already landed 2026-04-29)

The 7 cross-reference rename patches Claude recommended at Phase 0 were applied by the operator on 2026-04-29 (confirmed via `git pull` against `main`). This section is **verification-only** — do NOT re-apply patches.

### A1. CLAUDE.md — verify Phase 0 sprint renumbering applied

**Verification command (to run before Phase D):**
```bash
cd /home/claude/argus
grep -n "Sprint 31.92" CLAUDE.md | head -20
grep -n "Sprint 31.93" CLAUDE.md | head -20
grep -n "Sprint 31.94" CLAUDE.md | head -20
grep -n "Sprint 31.95" CLAUDE.md | head -20
```

Expected: Sprint 31.92 references the new DEF-204 Round 2 sprint; Sprint 31.93 references component-ownership; Sprint 31.94 references reconnect-recovery + DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING; Sprint 31.95 references alpaca-retirement.

### A2. docs/roadmap.md — verify Phase 0 cross-reference updates applied

**Verification command:**
```bash
grep -n "31.92\|31.93\|31.94\|31.95" docs/roadmap.md | head -30
```

Expected: Sprint sequencing reflects post-renumbering state; no references to old (pre-Phase-0) numbering.

If verification reveals drift (e.g., partial application or merge conflict), HALT before Phase D and reconcile cross-references with operator before proceeding.

---

## Phase B — Mid-Sprint Sprint Spec Amendment (BEFORE Phase D prompt generation)

### B1. Sprint Spec AC5.3 reframe (REVISED for Round-1 M-3 disposition)

**File:** `docs/sprints/sprint-31.92-def204-round-2/sprint-spec.md`

**Anchor:** Under §"Acceptance Criteria" Deliverable 5, the AC5.3 line.

**Patch (find/replace):**

<old>
**AC5.3:** `scripts/validate_def204_round2_composite.py` produces `scripts/spike-results/sprint-31.92-validation-composite.json` with `phantom_shorts_observed: 0` AND `ceiling_violations_observed: 0` (under benign load) AND `ceiling_violations_correctly_blocked: ≥1` (under adversarial load). Run at S5b.
</old>
<new>
**AC5.3 (Pytest test with JSON side-effect):** Composite validation implemented as Pytest integration tests in `tests/integration/test_def204_round2_validation.py` (test names `test_composite_validation_zero_phantom_shorts_under_load`, `test_composite_validation_ceiling_blocks_under_adversarial_load`, `test_composite_validation_multi_position_same_symbol_cross_safety`). Test fixture writes `scripts/spike-results/sprint-31.92-validation-composite.json` BEFORE assertion. Daily CI workflow runs the test and the artifact mtime tracks freshness per regression invariant 18. Assertions: under benign synthetic-broker load, `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`; under adversarial synthetic-broker load (forced over-flatten attempts at all 5 standalone-SELL emit sites), `ceiling_violations_correctly_blocked ≥ 1`; multi-position cross-safety preserved. **Amendment rationale (Round-1 M-3 disposition):** Round 1 reviewer correctly noted that Pytest tests don't have the 30-day freshness property of standalone JSON artifacts. The Pytest-with-side-effect pattern preserves session-budget discipline AND provides freshness via daily CI mtime tracking; restoring a standalone composite script would push S5b's compaction risk back over threshold.
</new>

### B2. Design Summary alignment (revised for Round-1 dispositions)

**File:** `docs/sprints/sprint-31.92-def204-round-2/design-summary.md`

**Anchor:** §"File Scope" → "Modify" block.

**Patch (find/replace):**

<old>
- `scripts/validate_def204_round2_{path1,path2,composite}.py` (new, S5a + S5b)
- `scripts/spike-results/sprint-31.92-validation-{path1,path2,composite}.json` (new, S5a + S5b)
</old>
<new>
- `scripts/validate_def204_round2_path1.py` (new, S5a)
- `scripts/validate_def204_round2_path2.py` (new, S5b)
- `scripts/spike-results/sprint-31.92-validation-{path1,path2}.json` (new, autogenerated + committed)
- `scripts/spike-results/sprint-31.92-validation-composite.json` (new, autogenerated by Pytest test side-effect at S5b; daily CI updates mtime per AC5.3)
</new>

The existing `tests/integration/test_def204_round2_validation.py` line in the design-summary's modify block is preserved unchanged.

**Note:** B1 and B2 should be applied in the same commit so Sprint Spec, Design Summary, and Doc Update Checklist stay synchronized.

---

## Phase C — Sprint-Close (D14) Doc-Sync (POST-S5b)

Apply these updates after S5b close-out lands cleanly on `main` and Tier 2 verdict is CLEAR. The doc-sync follows `protocols/mid-sprint-doc-sync.md` Pattern B (deferred materialization at sprint-close) — DEC-390 is the principal materialization. If Tier 3 escalates mid-sprint and produces material findings, Pattern A applies and DEC-390 may materialize earlier.

### C1. CLAUDE.md — DEF-204 / DEF-212 status updates + active-sprint pointer

**Anchor 1:** §"Active Sprint" block (currently shows Sprint 31.92).

**Patch:** Replace active-sprint description with sprint-sealed close-out summary; cross-reference to next sprint per build-track queue (Sprint 31.93 component-ownership).

**Anchor 2:** DEF-204 row in DEF table.

**Patch:**
<old>
| DEF-204 | CRITICAL | Phantom-short cascade — multi-mechanism (DEC-386 closes ~98%; residue under investigation) | Sprint 31.91 (partial) | RESOLVED-PENDING-PAPER-VALIDATION |
</old>
<new>
| DEF-204 | CRITICAL | Phantom-short cascade — multi-mechanism (DEC-386 L1+L2 close OCA-cancellation race; DEC-390 L1+L2 close trail/bracket concurrent-trigger race + locate-rejection retry storm; DEC-390 L3 ceiling with pending reservation + `is_reconstructed` refusal posture is structural defense-in-depth) | Sprint 31.91 + Sprint 31.92 | RESOLVED-PENDING-PAPER-VALIDATION (transitions to RESOLVED at cessation criterion #5 satisfaction — 5 paper sessions clean post-Sprint-31.92 seal) |
</new>

**Anchor 3:** DEF-212 row in DEF table.

**Patch:**
<old>
| DEF-212 | LOW | `_OCA_TYPE_BRACKET = 1` constant in order_manager.py mirrors `IBKRConfig.bracket_oca_type`; lock-step enforced only by docstring | Sprint 31.91 Tier 3 #1 (Concern B) | OPEN |
</old>
<new>
| DEF-212 | LOW | `_OCA_TYPE_BRACKET = 1` constant in order_manager.py mirrors `IBKRConfig.bracket_oca_type`; lock-step enforced only by docstring | Sprint 31.91 Tier 3 #1 (Concern B); resolved Sprint 31.92 S4b | RESOLVED |
</new>

**Anchor 4:** Active sprint pointer (top of file, sprint progress section).

**Patch:** Update to point to Sprint 31.93 component-ownership as next active sprint per build-track queue.

### C2. docs/decision-log.md — Write DEC-390 below

**Anchor:** Append after DEC-389 (Sprint 31.915 evaluation.db retention).

**Pattern:** B (Pattern A applies if Tier 3 fires mid-sprint).

**DEC-390 entry skeleton (REVISED for Round-1 dispositions; populated at sprint-close):**

```markdown
### DEC-390 | Concurrent-Trigger Race Closure with Mechanism-Selected Path #1 + Position-Keyed Locate-Rejection Suppression with Broker-Verified Timeout + Long-Only SELL-Volume Ceiling with Pending-Share Reservation + DEF-212 Constant Drift Wiring

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 (sealed {SPRINT_CLOSE_DATE}) |
| **Tier 3 verdict** | {Tier 3 fired? PROCEED-with-conditions / not required — fill at close} |
| **Adversarial review** | Round 1 (2026-04-29): Outcome B (3 Critical + 4 High + 3 Medium); Round 2 (post-revision): {verdict at close} |
| **Context** | Sprint 31.91's DEC-386 claimed `~98%` closure of DEF-204 mechanism via OCA-Group Threading + Broker-Only Safety. Tier 3 #1 (2026-04-27) verdict PROCEED. **Empirically falsified 2026-04-28** by paper-session debrief: 60 NEW phantom shorts post-DEC-386 across two distinct uncovered paths — (Path #1) trail-stop / bracket-stop concurrent-trigger race; (Path #2) locate-rejection-as-held retry storm. DEC-386's `~98%` claim was made in good faith from data available at Tier 3 #1 (24-hour pre-paper-session window); the falsification is acknowledged here, DEC-386 itself preserved unchanged (leave-as-historical posture). **Round-1 adversarial review surfaced 3 Critical findings:** C-1 (asyncio yield-gap race in ceiling between emit and fill), C-2 (restart-safety hole for reconstructed positions), C-3 (H1 cancel-and-await reintroduces AMD-2's closed gap). All 3 dispositioned per `revision-rationale.md`; Round 2 verdict pending at time of this DEC entry. |
| **Decision** | Adopt a 4-layer composition mirroring DEC-385/386's layered-decomposition pattern, with structural closure framing (NOT aggregate percentage claims) per process-evolution lesson F.5: **(L1 Path #1 mechanism, S2a + S2b)** — chosen mechanism per S1a spike: {ONE OF: H2 amend-stop-price via `modifyOrder` (PRIMARY DEFAULT — AMD-2 invariant PRESERVED) / H4 hybrid (try amend, fall back to cancel-and-await on rejection) / H1 cancel-and-await as last-resort (AMD-2 invariant SUPERSEDED by AMD-2-prime; unprotected window bounded by `cancel_propagation_timeout` ≤ 2s; AC1.6 operator-audit logging mandatory)}. Selected based on Phase A spike S1a (`scripts/spike-results/spike-def204-round2-path1-results.json`, dated {S1a_DATE}) which measured {SPIKE_S1a_FINDINGS}. Applied to `_trail_flatten`, `_resubmit_stop_with_retry` emergency-flatten branch, and {conditionally} `_escalation_update_stop`. **(L2 Path #2 fingerprint + position-keyed suppression + broker-verified timeout, S3a + S3b)** — Add `_LOCATE_REJECTED_FINGERPRINT = "contract is not available for short sale"` (case-insensitive substring per S1b spike) and `_is_locate_rejection(error: BaseException) -> bool` helper in `argus/execution/ibkr_broker.py`, mirroring DEC-386's `_is_oca_already_filled_error` pattern. Add `OrderManager._locate_suppressed_until: dict[ULID, float]` keyed by `ManagedPosition.id` (NOT symbol — cross-position safety per Round-1 H-2). `OrderManagerConfig.locate_suppression_seconds` default = {SPIKE_S1b_DERIVED_VALUE} (S1b p99+20% margin; hard floor 18000s if H6 ruled-out per spike's `recommended_locate_suppression_seconds` field). Wire suppression detection at `place_order` exception in 4 standalone-SELL paths with pre-emit suppression check. **Suppression-timeout fallback queries broker for actual position state BEFORE alert emission** (Round-1 H-3): if broker shows zero, log INFO "held order resolved cleanly"; if broker shows expected long, log INFO "no phantom short"; if broker shows unexpected state, publish DEC-385's existing `phantom_short_retry_blocked` SystemAlertEvent. Broker-verification failure path falls through to alert with `verification_failed: true` metadata flag (operator-triage signal). DEF-158's 3-branch side-check preserved verbatim — Path #2 detection is structurally upstream. **(L3 Long-only SELL-volume ceiling with pending-share reservation, S4a)** — Add THREE fields on `ManagedPosition`: `cumulative_pending_sell_shares: int = 0` (incremented synchronously at place-time before `await`; decremented on cancel/reject; transferred to filled on fill — closes Round-1 C-1 asyncio yield-gap race), `cumulative_sold_shares: int = 0` (incremented at confirmed fill), and `is_reconstructed: bool = False` (set True in `reconstruct_from_broker`; ceiling check refuses ALL ARGUS-emitted SELLs on reconstructed positions per Round-1 C-2 conservative posture; closes restart-safety hole until Sprint 31.94 D3 lands). `_check_sell_ceiling(position, requested_qty)` returns False iff `position.is_reconstructed OR (cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty > shares_total)`. Guards at all 5 standalone-SELL emit sites: `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`. **Bracket placement (`place_bracket_order`) EXPLICITLY EXCLUDED** from ceiling check (Round-1 H-1: would block all bracket placements; OCA enforces atomic cancellation). Violations refuse the SELL, do NOT increment pending counter, emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical")`, log CRITICAL. Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`, fail-closed). New `POLICY_TABLE` entry (14th) for `sell_ceiling_violation`; AST policy-table exhaustiveness regression guard updated. **(L4 DEF-212 rider with operator-visible rollback warning, S4b)** — `OrderManager.__init__` accepts `bracket_oca_type: int` keyword argument; `argus/main.py` construction call site passes `config.ibkr.bracket_oca_type`; 4 occurrences of `_OCA_TYPE_BRACKET = 1` module constant replaced by `self._bracket_oca_type`; module constant deleted. Grep regression guard. **Startup CRITICAL log** when `bracket_oca_type != 1` (Round-1 H-4): "DEC-386 ROLLBACK ACTIVE: bracket_oca_type=0. OCA enforcement on bracket children is DISABLED. DEF-204 race surface is REOPENED. Operator must restore to 1 and restart unless emergency rollback in progress." `IBKRConfig.bracket_oca_type` Pydantic validator UNCHANGED — rollback escape hatch preserved per DEC-386 design intent. Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) DEFERRED to Sprint 31.93 (component-ownership scope). |
| **Rationale** | DEF-204's mechanism is composite: (Path #1) is a fill-side race that DEC-386 S1b OCA threading does NOT cover (concurrent triggers fire both legs before OCA cancellation can propagate); (Path #2) is a misclassification — IBKR's "contract not available for short sale" is a HOLD pending borrow, NOT a transient reject, and ARGUS's retry layer treats it as transient. Both paths produce phantom shorts that are observable but not preventable by Sprint 31.91's mechanism. The architectural fix at L1 + L2 is structural: DEC-386 enforces atomic OCA at the broker layer; DEC-390 L1 ensures only ONE leg can be in flight at once (H2 amend keeps bracket stop live with updated trigger price; H1/H4 fallback uses cancel-and-await with operator-audit logging); DEC-390 L2 detects the hold-pending-borrow state, suppresses retry-storm at position-keyed granularity, and verifies broker state before emitting alerts (eliminating false-positive class during reconnect events). L3 (ceiling with pending reservation) is structural defense-in-depth: the reservation pattern closes the asyncio yield-gap race (Round-1 C-1); the `is_reconstructed` refusal posture closes the restart-safety hole (Round-1 C-2) until Sprint 31.94 D3's policy decision lands. L4 (DEF-212 wiring with operator-visible rollback warning) is cosmetic technical debt cleanup that piggybacks on the OrderManager construction-site touches; the startup CRITICAL warning ensures operators don't silently run with rollback enabled. The 4-layer layering across S2a–S5b makes each step self-contained and individually testable; regression-checklist invariants 13 + 14 + 15 + 16 + 17 + 18 + 19 + 20 + 21 + 22 collectively enforce monotonic safety. The Phase A spikes (S1a + S1b) and validation artifacts (S5a + S5b path1/path2 + composite via Pytest side-effect) are the falsifiable foundation. **Critical framing per process-evolution lesson F.5:** DEC-390 explicitly does NOT make aggregate percentage closure claims (no "comprehensive," "complete," "fully closed," or "covers ~N%" language). Per regression invariant on validation artifact framing: AC5.1/AC5.2 validate IN-PROCESS LOGIC against SimulatedBroker; cessation criterion #5 (5 paper sessions clean post-seal) is the production-validation gate. |
| **Impact** | DEF-204's Path #1 + Path #2 mechanisms structurally closed by L1 + L2; remaining mechanism residue (broker-only events not flowing through OCA, operator manual orders, future API drift) is bounded by L3 ceiling with `is_reconstructed` refusal posture. DEC-386's `~98%` claim is empirically REPLACED by DEC-390's structural closure framing + falsifiable validation artifacts. Operator daily-flatten mitigation cessation criteria #1+#2+#3 SATISFIED (via Sprint 31.91 + 31.92 cumulative); #4 (Sprint 31.92 sealed) MET at {SPRINT_CLOSE_DATE}; **#5 RESET TO 0/5** — 5 paper sessions clean post-Sprint-31.92 seal needed. Live-trading readiness requires: (1) Sprint 31.92 sealed cleanly; (2) ≥5 paper sessions clean post-seal (criterion #5 satisfied); (3) DEF-208 pre-live paper stress test under live-config simulation (Sprint 31.93 OR 31.94); (4) Sprint 31.91 §D7 gate criteria. Sprint 31.93 inherits Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) + DEF-208 fixture infrastructure. Sprint 31.94 inherits DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound + reconnect-event coupling for L2 suppression dict (`IBKRReconnectedEvent` consumer; AC2.5 broker-verification is the structural mitigation Sprint 31.92 ships in lieu of the consumer) + **Sprint 31.94 D3 eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION** (boot-time adoption-vs-flatten policy retires the conservative refusal posture). New risks filed: **RSK-DEC-390-AMEND** (PRIMARY if H2 selected; IBKR API version assumption) OR **RSK-DEC-390-CANCEL-AWAIT-LATENCY** (FALLBACK if H1 or H4-with-fallback-active; unprotected-window cost), **RSK-DEC-390-FINGERPRINT** (locate-rejection error string drift; quarterly re-validation flag), **RSK-CEILING-FALSE-POSITIVE** (pending-reservation state-transition completeness; partial-fill aggregation; concurrent yield-gap race), **RSK-RECONSTRUCTED-POSITION-DEGRADATION** (time-bounded by Sprint 31.94 D3), **RSK-SUPPRESSION-LEAK** (dict GC bound; AC2.5 broker-verification mitigates false-positive alerts). |
| **Cross-References** | **DEFs:** DEF-204 (closed by mechanism — RESOLVED-PENDING-PAPER-VALIDATION at sprint-close; RESOLVED at criterion #5 satisfaction); DEF-212 (closed by L4 — RESOLVED). **Predecessor DECs:** DEC-385 (Side-Aware Reconciliation Contract — preserved byte-for-byte; `phantom_short_retry_blocked` alert path reused at L2 broker-verified fallback); DEC-386 (OCA-Group Threading + Broker-Only Safety — preserved byte-for-byte; `~98%` claim empirically superseded by DEC-390's structural closure; `bracket_oca_type=0` rollback escape hatch preserved with new AC4.6 startup CRITICAL warning); DEC-388 (Alert Observability Architecture — `POLICY_TABLE` extended with 14th entry for `sell_ceiling_violation`; existing 13 entries unchanged). **Adjacent DECs:** DEC-117 (atomic bracket — preserved); DEC-364 (cancel_all_orders ABC — preserved, no extension); DEC-369 (broker-confirmed reconciliation — preserved; AC3.6 + AC3.7 ceiling+is_reconstructed compose additively); DEC-372 (stop retry caps — preserved; L1 mechanism applies to emergency-flatten branch); DEC-026 (ULID — `ManagedPosition.id` is the position-keyed suppression dict key per Round-1 H-2). **Validation artifacts:** S1a spike `scripts/spike-results/spike-def204-round2-path1-results.json` (PROCEED, valid ≤30 days); S1b spike `scripts/spike-results/spike-def204-round2-path2-results.json` (PROCEED, valid ≤30 days, hard-to-borrow microcap symbols measured per Round-1 M-1); S5a validation `scripts/spike-results/sprint-31.92-validation-path1.json` (`path1_safe: true`, in-process logic only); S5b validation `scripts/spike-results/sprint-31.92-validation-path2.json` (`path2_suppression_works: true`, in-process logic only); S5b composite Pytest `tests/integration/test_def204_round2_validation.py` + `scripts/spike-results/sprint-31.92-validation-composite.json` (Pytest-side-effect artifact, daily CI freshness per Round-1 M-3). **Diagnostic source:** `docs/debriefs/2026-04-28-paper-session-debrief.md`. **Risks:** RSK-DEC-390-AMEND (or RSK-DEC-390-CANCEL-AWAIT-LATENCY), RSK-DEC-390-FINGERPRINT, RSK-CEILING-FALSE-POSITIVE, RSK-RECONSTRUCTED-POSITION-DEGRADATION, RSK-SUPPRESSION-LEAK. **Time-bounded:** L2 suppression dict reconnect-event coupling deferred to Sprint 31.94; L3 `is_reconstructed` refusal posture eliminated by Sprint 31.94 D3. **Process-evolution lesson F.5:** "Empirical aggregate claims (e.g., DEC-386's `~98%`) invite empirical falsification when paper-session reality contradicts the claim. Structural closures + falsifiable validation artifacts replace aggregate percentages. Captured at Sprint 31.92 sprint-close for next campaign's RETRO-FOLD." **Adversarial review:** Round 1 verdict + revision rationale at `docs/sprints/sprint-31.92-def204-round-2/{adversarial-review-findings.md, revision-rationale.md}`; Round 2 verdict at {path at close}. **Tier 3 verdict artifact:** {if Tier 3 #1 fired mid-sprint: `docs/sprints/sprint-31.92-def204-round-2/tier-3-review-{N}-verdict.md`; else: N/A — adversarial Tier 2 covered architectural review at Phase C-1 Rounds 1+2}. |
```

(Sprint-close authoring fills in `{SPRINT_CLOSE_DATE}`, `{Tier 3 verdict}`, `{ONE OF: H2 amend / H4 hybrid / H1 cancel-and-await}`, `{S1a_DATE}`, `{SPIKE_S1a_FINDINGS}`, `{SPIKE_S1b_DERIVED_VALUE}`, Round 2 verdict path.)

### C3. docs/dec-index.md — Add DEC-390 entry

**Anchor:** Append in DEC ordering (after DEC-389).

**Patch:**
```markdown
| DEC-390 | 2026-04-{TBD} | Sprint 31.92 | DEF-204 Round 2 — 4-layer composition (Path #1 mechanism + Path #2 fingerprint + ceiling with pending reservation + DEF-212 wiring) | ACTIVE |
```

### C4. docs/sprint-history.md — Add Sprint 31.92 row + per-sprint detail block

**Anchor 1:** Append row to Sprint History table (sprint number ordering).

**Patch:**
```markdown
| 31.92 | DEF-204 Round 2 — concurrent-trigger race + locate-rejection retry storm + ceiling with pending reservation + DEF-212 rider | {DELTA_PYTEST}+{DELTA_VITEST}V | {SPRINT_DATES} | DEC-390 |
```

**Anchor 2:** Append per-sprint detail block at end of file.

**Patch (skeleton, populated at sprint-close):**
```markdown
## Sprint 31.92: DEF-204 Round 2

**Sealed:** {SPRINT_CLOSE_DATE}
**Sessions:** 10 (S1a + S1b spikes; S2a + S2b Path #1; S3a + S3b Path #2; S4a ceiling; S4b DEF-212 rider; S5a + S5b validation)
**Test delta:** +{DELTA_PYTEST} pytest, +{DELTA_VITEST} Vitest
**Adversarial review:** Round 1 (Outcome B, 3 Critical + 4 High + 3 Medium dispositioned per `revision-rationale.md`); Round 2 ({verdict})
**Tier 3 review:** {if fired: PROCEED-with-conditions verdict at `docs/sprints/sprint-31.92-def204-round-2/tier-3-review-{N}-verdict.md` / else: N/A — Phase C-1 Rounds 1+2 adversarial covered architectural review}

**Outcome:** DEF-204's Path #1 (trail/bracket concurrent-trigger race) and Path #2 (locate-rejection retry storm) structurally closed via DEC-390 L1 + L2. Long-only SELL-volume ceiling with pending-share reservation + reconstructed-position refusal posture (L3) provides structural defense-in-depth. DEF-212 (`_OCA_TYPE_BRACKET` constant drift) closed via L4 wiring + operator-visible rollback warning. DEF-204 status: RESOLVED-PENDING-PAPER-VALIDATION (transitions to RESOLVED at cessation criterion #5 — 5 paper sessions clean post-seal). DEC-386's `~98%` aggregate claim empirically replaced by DEC-390's structural closure framing per process-evolution lesson F.5.

**Key sessions:**
- S1a: Path #1 mechanism spike — measured H2 (modify_order) and H1 (cancel_all_orders await_propagation) against paper IBKR; selected mechanism: {H2/H4/H1}.
- S1b: Path #2 fingerprint + hold-pending-borrow window spike — measured against operator-curated hard-to-borrow microcap list (≥5 symbols × ≥10 trials); fingerprint string captured: `"contract is not available for short sale"`; suppression-window default derived: {SPIKE_S1b_DERIVED_VALUE}s.
- S2a + S2b: Path #1 implementation in `_trail_flatten` + `_resubmit_stop_with_retry` emergency-flatten branch + (conditionally) `_escalation_update_stop`.
- S3a + S3b: Path #2 implementation — fingerprint helper + position-keyed suppression dict + 4-emit-site wire-up + broker-verified suppression-timeout fallback.
- S4a: Long-only SELL-volume ceiling with pending reservation pattern + `is_reconstructed` flag + 5 emit-site guards + new POLICY_TABLE entry.
- S4b: DEF-212 rider — `OrderManager.__init__(bracket_oca_type)` wiring + 4 substitutions + module constant deletion + AC4.6 startup CRITICAL warning.
- S5a + S5b: Falsifiable in-process validation — path1.json + path2.json + composite Pytest with JSON side-effect + restart-during-active-position regression test.

**Inherited follow-ups:**
- Sprint 31.93: Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation); DEF-208 pre-live paper stress test fixture; component-ownership refactor.
- Sprint 31.94: DEF-211 D1+D2+D3 (sprint-gating); RSK-DEC-386-DOCSTRING bound; `IBKRReconnectedEvent` producer/consumer wiring (eliminates RSK-SUPPRESSION-LEAK reconnect blindness); D3 boot-time adoption-vs-flatten policy (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION).
- Sprint 35+: DEF-209 extended scope (`Position.side`, `redundant_exit_observed`, `cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed` SQLite persistence — Learning Loop V2 prerequisite).

**RSKs filed:**
- RSK-DEC-390-AMEND (PRIMARY if H2 selected) OR RSK-DEC-390-CANCEL-AWAIT-LATENCY (FALLBACK if H1/H4 with H1 fallback active)
- RSK-DEC-390-FINGERPRINT
- RSK-CEILING-FALSE-POSITIVE
- RSK-RECONSTRUCTED-POSITION-DEGRADATION (time-bounded by Sprint 31.94 D3)
- RSK-SUPPRESSION-LEAK (partially mitigated by AC2.5 broker-verification; full coupling deferred to Sprint 31.94)

**Process-evolution lesson:** F.5 (structural closure framing vs aggregate percentage claims) — captured at sprint-close per `docs/process-evolution.md`; metarepo amendments to `protocols/sprint-planning.md` + `protocols/adversarial-review.md` + `protocols/tier-3-review.md` are RETRO-FOLD candidates for next campaign.
```

### C5. docs/roadmap.md — Sprint 31.92 close-out narrative + roadmap re-baseline

**Anchor 1:** Sprint 31.92 entry in roadmap timeline.

**Patch:** Mark sealed; cross-reference DEC-390; cross-reference Sprint 31.93 as next active sprint.

**Anchor 2:** Build-track queue re-baseline.

**Patch:**
- Sprint 31.93 (component-ownership) → next active.
- Sprint 31.94 (reconnect-recovery + DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound) → queued.
- Sprint 31.95 (alpaca-retirement) → queued.
- Sprint 31B (Research Console / Variant Factory) → queued post-31.95.

**Anchor 3:** Cessation criteria summary section (top-of-file or designated section).

**Patch:** Update cessation criteria for DEF-204 (criterion #5 reset to 0/5; daily-flatten continues until satisfaction).

### C6. docs/project-knowledge.md — DEF table sync + active sprint pointer

**Anchor 1:** DEF table in project-knowledge.md (mirror of CLAUDE.md DEF table).

**Patch:** Sync with C1 changes — DEF-204 row updated; DEF-212 row updated to RESOLVED.

**Anchor 2:** Active sprint pointer.

**Patch:** Update to point to Sprint 31.93 component-ownership.

### C7. docs/architecture.md — §3.7 OrderManager additions

**Anchor:** §3.7 Order Manager subsection.

**Patch (additive):**

```markdown
**Sprint 31.92 additions (DEC-390):**
- **`ManagedPosition.cumulative_pending_sell_shares: int`** — per-position SELL-volume PENDING reservation, incremented synchronously at place-time before `await place_order(...)`, decremented on cancel/reject, transferred to `cumulative_sold_shares` on fill. Closes asyncio yield-gap race (Round-1 C-1).
- **`ManagedPosition.cumulative_sold_shares: int`** — per-position SELL-volume FILLED counter, incremented at confirmed SELL fill. In-memory only.
- **`ManagedPosition.is_reconstructed: bool`** — set `True` in `reconstruct_from_broker`. Ceiling check refuses ALL ARGUS-emitted SELLs on reconstructed positions until Sprint 31.94 D3's policy decision lands (RSK-RECONSTRUCTED-POSITION-DEGRADATION). Operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism.
- **`OrderManager._locate_suppressed_until: dict[ULID, float]`** — POSITION-keyed (NOT symbol-keyed) suppression state for IBKR locate-rejection holds. Cross-position safety preserved (Round-1 H-2). Default suppression window {SPIKE_S1b_DERIVED_VALUE} (`OrderManagerConfig.locate_suppression_seconds`, S1b p99+20% margin).
- **AC2.5 broker-verification at suppression timeout** — queries `broker.get_positions()` BEFORE alert emission. Three branches: zero (held order resolved), expected-long (no phantom short), unexpected (publish `phantom_short_retry_blocked`). Eliminates false-positive alerts during reconnect events without requiring `IBKRReconnectedEvent` consumer (Sprint 31.94 territory).
- **`bracket_oca_type` flow** — `IBKRConfig.bracket_oca_type` (Pydantic field, range `[0, 1]`, default `1`) → `OrderManager.__init__(bracket_oca_type)` → `self._bracket_oca_type` (replaces former `_OCA_TYPE_BRACKET` module constant). **Startup CRITICAL warning** when `bracket_oca_type != 1` ("DEC-386 ROLLBACK ACTIVE: DEF-204 race surface is REOPENED").
- **Path #1 mechanism** — Trail-stop / bracket-stop concurrent-trigger race closed via {H2 amend-stop-price PRIMARY DEFAULT — AMD-2 preserved / H4 hybrid amend-with-cancel-fallback / H1 cancel-and-await as last-resort — AMD-2 superseded by AMD-2-prime} per S1a-spike-selected. Operator-audit logging (AC1.6) on every cancel-and-await dispatch.
- **Path #2 detection** — IBKR rejection error string `"contract is not available for short sale"` fingerprinted via `_is_locate_rejection()` in `argus/execution/ibkr_broker.py`; position suppressed for `locate_suppression_seconds`; broker-verified suppression-timeout fallback eliminates false-positive alerts (Round-1 H-3).
```

### C8. docs/risk-register.md — File 5 RSKs (REVISED per Round-1)

#### C8.1. RSK-DEC-390-AMEND (PRIMARY — proposed, conditional on H2 selection by S1a)

```markdown
### RSK-DEC-390-AMEND | Path #1 H2 Amend-Stop-Price IBKR API Version Assumption

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene); conditional on H2 selection at S1a |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L1 selected H2 (amend bracket stop's price via `modifyOrder`) per S1a spike. The amend-stop-price path depends on IBKR's `modifyOrder` semantics being deterministic at sub-50ms latency. If a future IBKR API change introduces non-determinism (e.g., `modifyOrder` becomes async-acknowledged-but-eventually-applied), the mechanism degrades silently — phantom shorts may re-emerge without an explicit error. The dependency is on a single IBKR API call's behavior; ARGUS has no detection mechanism for "modify_order ack received but not actually applied." |
| **Mitigation** | (a) S2a regression test asserts mock `IBKRBroker.modify_order` was called BEFORE `place_order(SELL)` — any code-path bypass is caught immediately. (b) `docs/live-operations.md` paragraph documents the IBKR-API-version assumption + quarterly operational re-validation flag. (c) Cessation criterion #5 (5 paper sessions clean post-seal) is itself a continuous validation. (d) Spike artifact 30-day freshness check via A-class halt A13 — if `ib_async`/IBKR Gateway upgraded, both spikes re-run before paper trading resumes. (e) RSK-DEC-390-FINGERPRINT-class quarterly re-validation cadence. |
| **Trigger conditions** | (1) `ib_async` library version change. (2) IBKR Gateway version change. (3) Quarterly re-validation cycle (operator runs S1a script). (4) ANY paper-session phantom short matching Path #1 signature post-seal. |
| **Cross-References** | DEC-390 L1; AC1.2 (H2 path regression test); S1a spike artifact; `docs/live-operations.md` (post-sprint paragraph); A-class halt A13. |
```

#### C8.2. RSK-DEC-390-CANCEL-AWAIT-LATENCY (FALLBACK — proposed, conditional on H1 or H4 selection by S1a; NEW per Round-1 C-3)

```markdown
### RSK-DEC-390-CANCEL-AWAIT-LATENCY | Path #1 H1 Cancel-and-Await Unprotected Window

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene); conditional on H1 OR H4-with-fallback-active selection at S1a |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L1 fell to H1 cancel-and-await (last-resort) OR H4 hybrid (with cancel-and-await fallback path) per S1a spike. The cancel-and-await branch supersedes AMD-2 invariant by AMD-2-prime — unprotected window bounded by `cancel_propagation_timeout` ≤ 2s per DEC-386 S1c. On volatile $7–15 microcap stocks during fast moves, 200ms can equate to $0.50–$1.00 of slippage. The trade-off is documented but real. |
| **Mitigation** | (a) AC1.6 operator-audit structured log fires on every cancel-and-await dispatch — operator can audit each occurrence post-session. (b) `docs/live-operations.md` paragraph documents the trade-off + when to escalate. (c) Sprint Spec mandates DEC-390 explicitly call out H1 as last-resort with rationale. (d) Cessation criterion #5 (5 paper sessions clean post-seal) catches catastrophic slippage in production. |
| **Trigger conditions** | (1) Operator-observed slippage cluster on cancel-and-await dispatches (audit log surfaces this). (2) Quarterly re-validation cycle. (3) ANY paper-session phantom short matching Path #1 signature post-seal. |
| **Cross-References** | DEC-390 L1; AC1.6 operator-audit logging; S1a spike artifact; `docs/live-operations.md` (post-sprint paragraph). |
```

#### C8.3. RSK-DEC-390-FINGERPRINT (UNCONDITIONAL)

```markdown
### RSK-DEC-390-FINGERPRINT | Path #2 Locate-Rejection Error String Drift

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene) |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L2 detects IBKR's locate-rejection via case-insensitive substring match against `"contract is not available for short sale"` (captured by S1b spike). If IBKR changes this string (different `ib_async` version, different broker plumbing, different locale), locate-rejection detection silently fails → Path #2 retry storm re-emerges. The substring approach was selected at S3a because S1b spike confirmed string stability across ≥10 trials per symbol × ≥5 hard-to-borrow microcaps; if string drifts in production, fixture and production diverge but production falls through to existing CRITICAL-log path (NOT silent failure — the rejection still surfaces, just not classified). |
| **Mitigation** | (a) S5b validation re-runs against synthetic locate-rejection fixture; if string drifts, fixture and production diverge but production falls through to existing CRITICAL-log path. (b) Quarterly operational re-validation flag — operator runs S1b script against live paper IBKR every quarter and asserts string match. (c) CI check (added at S5b) that `scripts/spike-results/spike-def204-round2-path2-results.json` is < 90 days old. (d) A-class halt A13 fires if spike artifact >30 days old at first post-merge paper session. |
| **Trigger conditions** | (1) `ib_async` library version change. (2) IBKR Gateway version change. (3) Quarterly re-validation cycle. (4) Production observation: known hard-to-borrow symbol's SELL fails with rejection but `_is_locate_rejection()` returns False. |
| **Cross-References** | DEC-390 L2; AC2.1 (fingerprint match test); S1b spike artifact; `docs/live-operations.md` quarterly re-validation cadence; A-class halt A13. |
```

#### C8.4. RSK-CEILING-FALSE-POSITIVE (REVISED per Round-1 C-1 disposition)

```markdown
### RSK-CEILING-FALSE-POSITIVE | Long-Only SELL-Volume Ceiling False-Positive

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (mitigated by S5b composite test + A-class halt A11) |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L3 ceiling uses TWO-COUNTER reservation pattern (`cumulative_pending_sell_shares + cumulative_sold_shares ≤ shares_total`) per Round-1 C-1. Edge cases: (a) broker fill callback arrives out-of-order, (b) partial-fill granularity differs between SimulatedBroker and IBKR, (c) `cumulative_pending_sell_shares` not decremented correctly on cancel/reject (would cause counter to drift upward over session), (d) the C-1 race scenario fires unexpectedly (two coroutines both pass ceiling because reservation didn't hold synchronously before `await`). Either could produce off-by-one transient state. |
| **Mitigation** | (a) AC3.1 enumerates all 5 state transitions explicitly; reviewer must verify each. (b) AC3.5 race test (`test_concurrent_sell_emit_race_blocked_by_pending_reservation`) is the canonical regression. (c) S5b composite stresses 5+ SELL emit sites with parametrized partial-fill scenarios. (d) A-class halt A11 fires on any false-positive observed in production paper trading; default disposition (per A11): audit which state transition leaked/under-decremented. (e) Reviewer mandate at S4a: inspect diff for synchronous-before-await ordering; this is the architectural correctness contract. |
| **Trigger conditions** | (1) Production paper-session shows a legitimate SELL refused due to pending+sold+requested arithmetic. (2) Pending counter observed drifting upward over session (suggests cancel/reject path under-decrement). (3) Race test failure in CI. (4) Any paper-session phantom short traceable to a coroutine pair where both passed the ceiling check. |
| **Cross-References** | DEC-390 L3; AC3.1 (state transitions); AC3.5 (race test); regression invariants 13 + 20; A-class halt A11; SbC §"Edge Cases to Reject" #1 (replaced from Round-1 wrong framing). |
```

#### C8.5. RSK-RECONSTRUCTED-POSITION-DEGRADATION (NEW per Round-1 C-2 disposition; time-bounded by Sprint 31.94 D3)

```markdown
### RSK-RECONSTRUCTED-POSITION-DEGRADATION | `is_reconstructed=True` Refusal Posture Operational Cost

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN; **TIME-BOUNDED by Sprint 31.94 D3 seal** (boot-time adoption-vs-flatten policy retires the conservative posture) |
| **Severity** | MEDIUM (operational; closes structural restart-safety hole) |
| **Description** | DEC-390 L3's `ManagedPosition.is_reconstructed: bool` flag (set `True` in `reconstruct_from_broker`) causes the ceiling check to refuse ALL ARGUS-emitted SELLs on reconstructed positions. This is a CONSERVATIVE posture chosen at Round-1 disposition C-2 (over the reviewer's proposed alternatives of reading `data/argus.db` trades table OR persisting counters to SQLite — both rejected as fragile/scope-violating). Operational consequence: until Sprint 31.94 D3 lands, reconstructed positions can ONLY be closed via `scripts/ibkr_close_all_positions.py` (operator manual, bypasses OrderManager). EOD flatten and time-stop paths on reconstructed positions are blocked. |
| **Mitigation** | (a) `_startup_flatten_disabled` (IMPROMPTU-04) already blocks reconstruction entirely on most non-clean broker states, so the actual operational surface is small. (b) Operator daily-flatten script `scripts/ibkr_close_all_positions.py` is the structurally-acknowledged closing mechanism. (c) Sprint 31.94 D3's policy decision (boot-time adoption-vs-flatten policy) is sprint-gating for Sprint 31.94 itself — cannot be sealed without D3. (d) A-class halts A15 + A16 fire on any leak (SELL emitted on `is_reconstructed=True` position) OR sustained operational degradation (operator-manual flatten cannot keep up). (e) Sprint Abort Condition #7 covers the case where Sprint 31.94 D3 slips by >4 weeks. |
| **Trigger conditions** | (1) Test failure: `test_restart_during_active_position_refuses_argus_sells` fails. (2) Production: any ARGUS-emitted SELL on `is_reconstructed=True` position (A15 fires). (3) Production: reconstructed positions accumulate AND operator daily-flatten cannot keep up (A16 fires). (4) Sprint 31.94 D3 ETA slips >4 weeks past Sprint 31.92 seal date (Sprint Abort Condition #7 fires). |
| **Cross-References** | DEC-390 L3; AC3.6 (initialization); AC3.7 (refusal posture); AC5.4 (restart validation); regression invariant 19; A-class halts A15 + A16; Sprint Abort Condition #7; DEF-211 D3 (Sprint 31.94 sprint-gating); SbC §"Out of Scope" #5; `scripts/ibkr_close_all_positions.py` (operator-manual closing mechanism). |
```

#### C8.6. RSK-SUPPRESSION-LEAK (UNCONDITIONAL; PARTIALLY MITIGATED per Round-1 H-3)

```markdown
### RSK-SUPPRESSION-LEAK | Locate-Suppression Dict GC Bound + Reconnect Blindness

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (partially mitigated by AC2.5 broker-verification; full coupling deferred to Sprint 31.94) |
| **Severity** | LOW (operational; structural mitigation in place) |
| **Description** | DEC-390 L2's `OrderManager._locate_suppressed_until: dict[ULID, float]` accumulates entries; cleared on (a) fill callback for the position, (b) position close, (c) suppression-window timeout fallback per AC2.5. Mid-session IBKR Gateway reconnect would leave stale entries in the dict until the timeout fires (default 18000s = 5hr). AC2.5's broker-verification-at-timeout (Round-1 H-3) eliminates the false-positive alert class even when stale dict entries persist post-reconnect: when timeout fires, broker is queried for actual position state and (if expected-long observed) alert is suppressed and dict entry cleared. Stale dict entries during the suppression window cause additional SELLs at the same `ManagedPosition` to be skipped — for the suppression-window duration, this is conservative-but-correct (the position will close via subsequent flatten-resubmit timeout via DEF-158's retry path, OR via the suppression-timeout broker-verification fallback). |
| **Mitigation** | (a) Existing OrderManager EOD teardown clears the dict (no inter-session leak). (b) Suppression-timeout fallback per AC2.5 with broker-verification clears stale entries on a per-position basis. (c) Sprint 31.94 will couple `IBKRReconnectedEvent` consumer to dict-clear when the producer lands. (d) S5b stress test asserts dict cleared at session-end. (e) `OrderManager._locate_suppressed_until` is bounded by `len(active_managed_positions)` — never grows unboundedly. |
| **Trigger conditions** | (1) S5b stress-test fails: dict not cleared at session-end. (2) Production: paper session reveals dict size growing across the session beyond reasonable ManagedPosition cardinality. (3) Production: stale dict entry causes a legitimate position's SELL to be skipped during suppression window AND broker-verification at timeout incorrectly classifies state. |
| **Cross-References** | DEC-390 L2; AC2.2 (position-keyed suppression); AC2.5 (broker-verification at timeout); regression invariant 14; B-class halt B12 (broker-verification failure); Sprint 31.94 reconnect-recovery (full coupling). |
```

### C9. docs/pre-live-transition-checklist.md — Add Sprint 31.92 gate criteria

**Anchor:** Append a new subsection under §"Sprint 31.91 + 31.92 Gates" (rename from existing "Sprint 31.91 Gates" if needed).

**Patch (additive, after the existing Sprint 31.91 gate criteria block):**

```markdown
#### Sprint 31.92 Gate Criteria

Before considering live trading transition post-Sprint-31.92:

1. **DEF-204 RESOLVED status reached** — i.e., RESOLVED-PENDING-PAPER-VALIDATION transitions to RESOLVED only after cessation criterion #5 (5 paper sessions clean post-Sprint-31.92 seal) is satisfied.
2. **DEF-212 RESOLVED status reached** — i.e., `_OCA_TYPE_BRACKET` constant deleted from `argus/execution/order_manager.py`; grep regression guard green; `OrderManager.__init__` accepts `bracket_oca_type: int`; `argus/main.py` construction site updated.
3. **All 4 spike + validation artifacts under `scripts/spike-results/` are committed and ≤30 days old**:
   - `spike-def204-round2-path1-results.json` (S1a; status=PROCEED)
   - `spike-def204-round2-path2-results.json` (S1b; status=PROCEED; hard-to-borrow microcap measurements per Round-1 M-1)
   - `sprint-31.92-validation-path1.json` (S5a; `path1_safe: true`)
   - `sprint-31.92-validation-path2.json` (S5b; `path2_suppression_works: true`; `broker_verification_at_timeout_works: true`)
4. **Composite Pytest test green and JSON artifact ≤24 hours old** — `tests/integration/test_def204_round2_validation.py::test_composite_validation_zero_phantom_shorts_under_load` passes; `scripts/spike-results/sprint-31.92-validation-composite.json` updated by daily CI workflow within last 24 hours.
5. **Restart-scenario test green** — `tests/integration/test_def204_round2_validation.py::test_restart_during_active_position_refuses_argus_sells` passes (regression invariant 19).
6. **Path #1 mechanism re-spike** before live transition (DEC-386's `PATH_1_SAFE` discipline mirror) — operator runs `scripts/spike_def204_round2_path1.py` against current paper IBKR + current `ib_async` version; verifies S1a-recorded mechanism (H2 amend / H4 hybrid / H1 cancel-and-await) still operates within measurement bounds.
7. **Path #2 fingerprint re-validation** — operator runs `scripts/spike_def204_round2_path2.py` against current paper IBKR with operator-curated hard-to-borrow microcap list; verifies fingerprint string still matches; verifies suppression-window p99 measurement still within Pydantic field validator bounds [300, 86400] seconds.
8. **`bracket_oca_type=1` verified in live config** — emergency rollback escape hatch confirmed inactive (AC4.6 startup CRITICAL warning would fire if `!= 1`; verify warning ABSENT in startup logs).
9. **`is_reconstructed` refusal posture documented in operator runbook** — operator aware that reconstructed positions can only be closed via `scripts/ibkr_close_all_positions.py` until Sprint 31.94 D3 lands; daily-flatten infrastructure verified operational.
10. **Daily CI workflow for composite test verified live** — workflow file present in `.github/workflows/` (or equivalent); workflow execution history shows ≥7 consecutive daily green runs before live transition consideration.
11. **No outstanding A-class halt triggers** from Sprint 31.92 escalation criteria (especially A11, A15, A16, B12).
12. **DEC-390 entry written** in `docs/decision-log.md` with all 4 layers, complete cross-references, structural-closure framing (NO aggregate percentage claims per process-evolution lesson F.5).
```

### C10. process-evolution.md — Lesson F.5 (NEW; structural-closure framing pattern)

**Anchor:** Append after existing lessons F.1–F.4 in `docs/process-evolution.md` (file is workflow-metarepo-mirrored; Sprint 31.92 sprint-close fold-in).

**Patch (additive — full new lesson body):**

```markdown
### F.5 — Structural Closure Framing vs Aggregate Percentage Claims (Sprint 31.92 origin, 2026-04-29)

**Context:** Sprint 31.91's DEC-386 (Tier 3 #1 verdict 2026-04-27, PROCEED) made the empirical claim "DEF-204's primary mechanism (~98% of blast radius per IMPROMPTU-11) closed by Sessions 1a + 1b." This claim was made in good faith from the data available — IMPROMPTU-11's mass-balance attribution analysis was rigorous, and the Tier 3 reviewer accepted the framing. **24 hours later** (2026-04-28), a paper session produced 60 NEW phantom shorts via two distinct uncovered mechanism paths (Path #1 trail/bracket race; Path #2 locate-rejection retry storm). Neither path was hypothetically ruled out by DEC-386 — they were structurally outside its coverage. The `~98%` claim was empirically falsified. Sprint 31.92 is the response sprint.

**Lesson:** **DEC entries claiming closure should use structural framing, not aggregate percentage claims.** Specifically:

- ❌ **Anti-pattern:** "DEC-XXX closes ~N% of mechanism Y's blast radius" / "DEC-XXX comprehensively addresses..." / "DEC-XXX fully closes..." / "DEC-XXX completely resolves..."
- ✅ **Pattern:** "DEC-XXX closes mechanism Y at architectural layer L₁; falsifiable validation artifact at `scripts/spike-results/path/to/artifact.json` confirms the in-process invariant; cessation criterion N (M paper sessions clean post-seal) is the production-validation gate."

**Why this matters:**

1. **Aggregate percentages invite empirical falsification at any single counterexample.** `~98%` becomes "this claim was wrong" the moment one phantom short surfaces — even if the ARCHITECTURAL closure was correct in all cases the claim covered. Structural framing ("closes mechanism Y") is robust to discovering ADDITIONAL mechanisms; the architectural claim about Y stays true even when mechanism Z is found uncovered.

2. **Tier 3 reviewers cannot easily falsify aggregate claims at review-time.** "What's your evidence for the ~98% number?" is answerable but is not the right question; the right question is "what mechanisms ARE NOT covered, and how would we know?" Structural framing forces enumeration of uncovered mechanisms.

3. **Process-evolution incentive:** Authors of DEC entries face implicit pressure to make strong claims (closure feels like progress). Structural framing redirects the strength claim from quantity ("~98%") to architectural specificity ("mechanism Y at layer L₁"), which is the actually load-bearing property.

**Operational application:**

- **Sprint-planning protocol (this metarepo's `protocols/sprint-planning.md`):** Phase B Step 3 "Decision Log entry" template should include explicit framing guidance — bullet point: "DEC entries describing mechanism closure use architectural framing (mechanism + layer + falsifiable artifact + production gate). DO NOT use aggregate percentage claims (`~N%`) — these invite empirical falsification at any single counterexample."

- **Adversarial-review protocol (this metarepo's `protocols/adversarial-review.md`):** Probing Sequence Step 4 "Specification Gaps" should include the prompt: "Does this DEC make any aggregate percentage closure claim? If yes, what mechanism is the percentage measuring, and what's the evidence — and what mechanisms are excluded from the percentage that could be sources of empirical falsification?"

- **Tier 3 review protocol (this metarepo's `protocols/tier-3-review.md`):** Probing should include: "What mechanisms are NOT covered by this architectural decision, and how would the operator know if one of them surfaced in production?"

**Sprint 31.92 application:** DEC-390's entry text deliberately uses "L1 closes Path #1 mechanism / L2 closes Path #2 mechanism / L3 + AC3.7 reconstructed-position refusal provide structural defense-in-depth / L4 closes constant-drift hygiene" framing. AC6.3 mandates this framing. SbC §"Edge Cases to Reject" #17 explicitly forbids aggregate percentage language in DEC-390 draft text — reviewer halts on tokens like "comprehensive," "complete," "fully closed," "covers ~N%."

**Cross-references:** DEC-386 (the falsified claim); DEC-390 (the corrected pattern); 2026-04-28 paper-session debrief (the falsifying evidence); SbC §"Edge Cases to Reject" #17; AC6.3.

**Capture notes:** Lesson F.5 captured in process-evolution.md at Sprint 31.92 sprint-close. Workflow-metarepo amendments to `protocols/sprint-planning.md`, `protocols/adversarial-review.md`, `protocols/tier-3-review.md` are RETRO-FOLD candidates for the next campaign — NOT applied in-line at Sprint 31.92's sprint-close (cross-repo scope).
```

---

## Phase D — Sprint Cessation Tracker

After Sprint 31.92 seals, the following tracker is added to `CLAUDE.md` under §"Active Sprint" → §"Cessation Criteria" (replacing Sprint 31.91's entry):

```markdown
### Cessation Criteria — DEF-204 (Post-Sprint-31.92)

DEF-204 transitions from RESOLVED-PENDING-PAPER-VALIDATION to RESOLVED when ALL of the following are satisfied:

1. ✅ Sprint 31.91 sealed (cumulative — 2026-04-28).
2. ✅ Sprint 31.92 sealed ({SPRINT_CLOSE_DATE}).
3. ✅ Sprint 31.92 spike artifacts + validation artifacts committed to `main` and ≤30 days old.
4. ✅ DEC-390 written below in `docs/decision-log.md`.
5. ⏸️ **5 paper sessions clean post-Sprint-31.92 seal** — counter starts at 0/5 on {SPRINT_CLOSE_DATE}. "Clean" defined: (a) zero NEW phantom shorts; (b) zero `phantom_short_retry_blocked` alerts attributable to false-positive (i.e., AC2.5 broker-verification correctly suppressed alerts during reconnects); (c) zero `sell_ceiling_violation` alerts unless attributable to a known operator-side trigger; (d) zero ARGUS-emitted SELLs on `is_reconstructed=True` positions (regression invariant 19); (e) operator daily-flatten executed successfully (no missed-run incidents).
6. ⏸️ Sprint 31.94 sealed (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION via D3 boot-time policy).

Operator daily-flatten via `scripts/ibkr_close_all_positions.py` continues until criterion 5 is satisfied.

Live trading transition gated by criterion 5 + DEF-208 pre-live paper stress test (Sprint 31.93 OR 31.94 territory).
```

---

## Sprint 31.92 Adversarial Review Round 2 reference

The full Sprint Spec (revised) + Spec by Contradiction (revised) + Adversarial Review Input Package (revised, Round 2 framing) form the Round 2 review input. Round 2's scope is narrower than Round 1: validate the revisions specifically, not the original design. See `adversarial-review-input-package.md` (revised) §"Round 2 framing" for the targeted scrutiny questions.