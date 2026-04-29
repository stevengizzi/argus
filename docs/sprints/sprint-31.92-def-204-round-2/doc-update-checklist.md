# Sprint 31.92: Doc Update Checklist

> **Phase C artifact 8/9 (revised post-Phase-B-re-run, 2026-04-29).** Three-phase
> doc update plan covering pre-sprint housekeeping (Phase A), mid-sprint Sprint
> Spec amendment (Phase B), and sprint-close (D14) doc-sync (Phase C). Each
> entry specifies the exact file, anchor, and patch text or skeleton.
>
> **Revision history:**
>
> - **Round 1 authored 2026-04-28** with Phase A (pre-sprint) confirm-only +
>   Phase B (Sprint Spec AC5.3 amendment) + Phase C (sprint-close, 10 doc-sync
>   items + 4 RSKs + lesson F.5).
> - **Round-1-revised 2026-04-29:** Phase B B1 patch updated for AC5.3 Pytest-
>   side-effect framing (M-3); B2 reframed as Design Summary alignment; DEC-390
>   entry skeleton in C2 expanded with H2 default mechanism + pending-reservation
>   L3 + `is_reconstructed` AC3.7 + AC4.6 startup warning; C7 architecture.md
>   additive content updated; C8 RSKs revised — RSK-DEC-390-AMEND remains
>   primary (H2 default), NEW RSK-DEC-390-CANCEL-AWAIT-LATENCY (H1/H4 fallback
>   path conditional), RSK-CEILING-FALSE-POSITIVE expanded for pending-
>   reservation race scenarios, NEW RSK-RECONSTRUCTED-POSITION-DEGRADATION
>   (Sprint 31.94 D3 dependency), NEW RSK-SUPPRESSION-LEAK; C9 pre-live
>   checklist additions for new fields; C10 lesson F.5 framing tightened for
>   "structural closure" pattern.
> - **Round 2 dispositioned 2026-04-29** (1C+5H+5M+3L; A14 fired triggering
>   Phase A re-entry per Outcome C).
> - **Phase A re-entry 2026-04-29:** FAI authored (8 entries) + 14 Round-2
>   dispositions re-validated + 3 procedural deviations identified.
> - **Phase A Tier 3 verdict REVISE_PLAN 2026-04-29:** FAI's self-falsifiability
>   clause fired — entry #9 (callback-path bookkeeping atomicity) missing;
>   H-R2-1 protection scope narrower than mechanism; ≥4 cross-layer composition
>   tests required; C-R2-1 + H-R2-2 coupling required; M-R2-1 auto-activation
>   recommended; M-R2-4 adversarial sub-spike recommended; FAI #5 N≥100
>   recommended; FAI #8 option (a) recommended. 6 DEFs + 2 RSKs filed.
> - **Phase B re-run + Phase C re-revision 2026-04-29 (this revision):**
>   Substantive vs Structural Rubric fired 5 of 8 triggers (mandatory re-run).
>   This doc-update-checklist incorporates all Tier 3 items A–E + all 7 settled
>   operator decisions + the new 13-session breakdown (was 10) + the
>   `Broker.refresh_positions()` ABC method + AC2.7 watchdog auto-activation +
>   AC4.7 `--allow-rollback` CLI gate + the 5 cross-layer composition tests
>   (CL-1 through CL-5) + the synchronous-update invariant extension to all
>   bookkeeping callback paths. C1 adds 6 DEFs to the CLAUDE.md DEF table; C8
>   adds 2 RSKs (RSK-FAI-COMPLETENESS, RSK-CROSS-LAYER-INCOMPLETENESS) to the
>   risk-register; C9 adds `pending_sell_age_watchdog_enabled` runtime-state
>   recording; C10 adds lesson F.6 (FAI completeness pattern) + lesson F.7
>   (CL-6 deferral rationale). Phase B B1 + B2 carried forward as historical
>   record — already folded into Phase C revised sprint-spec.md and design-
>   summary.md.

---

## Phase A — Pre-Sprint Housekeeping (CONFIRM-ONLY, already landed 2026-04-29)

The 7 cross-reference rename patches Claude recommended at Phase 0 were applied
by the operator on 2026-04-29 (confirmed via `git pull` against `main`). This
section is **verification-only** — do NOT re-apply patches.

### A1. CLAUDE.md — verify Phase 0 sprint renumbering applied

**Verification command (to run before Phase D):**
```bash
cd /home/claude/argus
grep -n "Sprint 31.92" CLAUDE.md | head -20
grep -n "Sprint 31.93" CLAUDE.md | head -20
grep -n "Sprint 31.94" CLAUDE.md | head -20
grep -n "Sprint 31.95" CLAUDE.md | head -20
```

Expected: Sprint 31.92 references the new DEF-204 Round 2 sprint; Sprint 31.93
references component-ownership; Sprint 31.94 references reconnect-recovery +
DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING; Sprint 31.95 references alpaca-
retirement.

### A2. docs/roadmap.md — verify Phase 0 cross-reference updates applied

**Verification command:**
```bash
grep -n "31.92\|31.93\|31.94\|31.95" docs/roadmap.md | head -30
```

Expected: Sprint sequencing reflects post-renumbering state; no references to
old (pre-Phase-0) numbering.

If verification reveals drift (e.g., partial application or merge conflict),
HALT before Phase D and reconcile cross-references with operator before
proceeding.

---

## Phase B — Mid-Sprint Sprint Spec Amendment (HISTORICAL — folded into Phase C revised spec)

> **Note (Phase B re-run revision, 2026-04-29):** The B1 + B2 amendments below
> were Round-1 mid-sprint amendments. **Both have been folded into the Phase C
> re-revised `sprint-spec.md` and `design-summary.md` directly** as part of
> the Phase B re-run + Phase C re-revision pass. They are preserved here as
> historical record so the audit trail of "what was amended when" remains
> intact. Mid-sprint amendment paths during sprint execution (if Tier 3 fires
> mid-sprint) follow the same pattern but apply against the Phase-C-revised
> baseline, not the Round-1 baseline.

### B1. Sprint Spec AC5.3 reframe (REVISED for Round-1 M-3 disposition; FOLDED into Phase C revised spec)

**File:** `docs/sprints/sprint-31.92-def204-round-2/sprint-spec.md`

**Anchor:** Under §"Acceptance Criteria" Deliverable 5, the AC5.3 line.

**Patch (find/replace):**

<old>
**AC5.3:** `scripts/validate_def204_round2_composite.py` produces `scripts/spike-results/sprint-31.92-validation-composite.json` with `phantom_shorts_observed: 0` AND `ceiling_violations_observed: 0` (under benign load) AND `ceiling_violations_correctly_blocked: ≥1` (under adversarial load). Run at S5b.
</old>
<new>
**AC5.3 (Pytest test with JSON side-effect):** Composite validation implemented as Pytest integration tests in `tests/integration/test_def204_round2_validation.py` (test names `test_composite_validation_zero_phantom_shorts_under_load`, `test_composite_validation_ceiling_blocks_under_adversarial_load`, `test_composite_validation_multi_position_same_symbol_cross_safety`). Test fixture writes `scripts/spike-results/sprint-31.92-validation-composite.json` BEFORE assertion. Daily CI workflow runs the test and the artifact mtime tracks freshness per regression invariant 18. Assertions: under benign synthetic-broker load, `phantom_shorts_observed == 0` AND `ceiling_violations_observed == 0`; under adversarial synthetic-broker load (forced over-flatten attempts at all 5 standalone-SELL emit sites), `ceiling_violations_correctly_blocked ≥ 1`; multi-position cross-safety preserved. **Amendment rationale (Round-1 M-3 disposition):** Round 1 reviewer correctly noted that Pytest tests don't have the 30-day freshness property of standalone JSON artifacts. The Pytest-with-side-effect pattern preserves session-budget discipline AND provides freshness via daily CI mtime tracking; restoring a standalone composite script would push S5b's compaction risk back over threshold.
</new>

### B2. Design Summary alignment (revised for Round-1 dispositions; FOLDED into Phase C revised design-summary)

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
- `scripts/spike-results/sprint-31.92-validation-composite.json` (new, autogenerated by Pytest test side-effect at S5b/S5c; daily CI updates mtime per AC5.3)
</new>

The existing `tests/integration/test_def204_round2_validation.py` line in the
design-summary's modify block is preserved unchanged.

**Note:** B1 and B2 were applied in the Phase C re-revision (this pass). New
mid-sprint amendments during execution (if Tier 3 fires mid-sprint per the
M-R2-5 schedule) would follow the same find-and-replace pattern against the
Phase-C-revised baseline.

---

## Phase C — Sprint-Close (D14) Doc-Sync (POST-S5c)

Apply these updates after S5c close-out lands cleanly on `main` and Tier 2
verdict is CLEAR. The doc-sync follows `protocols/mid-sprint-doc-sync.md`
Pattern B (deferred materialization at sprint-close) — DEC-390 is the
principal materialization. If Tier 3 escalates mid-sprint and produces
material findings, Pattern A applies and DEC-390 may materialize earlier.

### C1. CLAUDE.md — DEF-204 / DEF-212 status updates + DEF table additions (Tier 3) + active-sprint pointer

**Anchor 1:** §"Active Sprint" block (currently shows Sprint 31.92).

**Patch:** Replace active-sprint description with sprint-sealed close-out
summary; cross-reference to next sprint per build-track queue (Sprint 31.93
component-ownership).

**Anchor 2:** DEF-204 row in DEF table.

**Patch:**
<old>
| DEF-204 | CRITICAL | Phantom-short cascade — multi-mechanism (DEC-386 closes ~98%; residue under investigation) | Sprint 31.91 (partial) | RESOLVED-PENDING-PAPER-VALIDATION |
</old>
<new>
| DEF-204 | CRITICAL | Phantom-short cascade — multi-mechanism (DEC-386 L1+L2 close OCA-cancellation race; DEC-390 L1+L2 close trail/bracket concurrent-trigger race + locate-rejection retry storm; DEC-390 L3 ceiling with pending reservation + extended synchronous-update invariant on all bookkeeping callback paths + `is_reconstructed` refusal posture is structural defense-in-depth; DEC-390 L4 closes DEF-212 constant drift with operator-visible rollback gate) | Sprint 31.91 + Sprint 31.92 | RESOLVED-PENDING-PAPER-VALIDATION (transitions to RESOLVED at cessation criterion #5 satisfaction — 5 paper sessions clean post-Sprint-31.92 seal) |
</new>

**Anchor 3:** DEF-212 row in DEF table.

**Patch:**
<old>
| DEF-212 | LOW | `_OCA_TYPE_BRACKET = 1` constant in order_manager.py mirrors `IBKRConfig.bracket_oca_type`; lock-step enforced only by docstring | Sprint 31.91 Tier 3 #1 (Concern B) | OPEN |
</old>
<new>
| DEF-212 | LOW | `_OCA_TYPE_BRACKET = 1` constant in order_manager.py mirrors `IBKRConfig.bracket_oca_type`; lock-step enforced only by docstring | Sprint 31.91 Tier 3 #1 (Concern B); resolved Sprint 31.92 S4b | RESOLVED |
</new>

**Anchor 4:** DEF table — APPEND 6 NEW ROWS (Phase A Tier 3 filings).

**Patch (additive — append below existing DEF rows):**
```markdown
| DEF-FAI-CALLBACK-ATOMICITY | MEDIUM-HIGH | All bookkeeping update paths on `cumulative_pending_sell_shares` and `cumulative_sold_shares` (place-side increment, cancel/reject decrement, partial-fill transfer, full-fill transfer, `_check_sell_ceiling` multi-attribute read) execute synchronously between read and write across the entire transition. Round-1 C-1's atomic `_reserve_pending_or_fail` pattern was the reference implementation; Phase A Tier 3 identified that the AST-no-await guard + mocked-await injection regression must extend to every callback path that mutates the bookkeeping counters. | Sprint 31.91 Phase A Tier 3 (FAI entry #9); resolved Sprint 31.92 S4a-ii | RESOLVED |
| DEF-CROSS-LAYER-EXPANSION | MEDIUM | Cross-layer composition tests at floor (3) rather than coverage-comprehensive. DEC-386's empirical falsification on 2026-04-28 (60 phantom shorts via cross-layer composition path) justifies heightened bar; Phase C committed to 5 tests (CL-1 through CL-5) with CL-6 (rollback + locate-suppression interaction) deferred per Decision 5. | Sprint 31.92 Phase A Tier 3; resolved Sprint 31.92 S5c | RESOLVED |
| DEF-FAI-N-INCREASE | MEDIUM | FAI #5 cancel-then-SELL stress N=30 statistically weak; increase to N≥100 to give the H1 propagation atomicity assumption a meaningful failure floor. Operator-overridable on cost grounds. | Sprint 31.92 Phase A Tier 3 (Decision 2); resolved Sprint 31.92 S1a refinement | RESOLVED |
| DEF-FAI-2-SCOPE | MEDIUM | FAI #2 spike scope limited to reconnect-window axis; high-volume steady-state cache-refresh behavior under hundreds of variants explicitly OUT of Sprint 31.92 scope. Documentation-only at Sprint 31.92; implementation deferred to Sprint 31.94 reconnect-recovery work. | Sprint 31.92 Phase A Tier 3; documented Sprint 31.92 SbC §"Out of Scope"; implementation Sprint 31.94 | OPEN (documented out-of-scope; sprint-target Sprint 31.94) |
| DEF-FAI-8-OPTION-A | MEDIUM | H-R2-5 / FAI #8 chose option (a) adversarial regression sub-test rather than option (b) accept-and-document. S4a-ii adds 3 reflective-call sub-tests probing whether the AST-level scan for `is_stop_replacement=True` callers catches (a) `**kw` unpacking, (b) computed-value flag assignment, (c) `getattr` reflective access. | Sprint 31.92 Phase A Tier 3 (Decision 3); resolved Sprint 31.92 S4a-ii | RESOLVED |
| DEF-SIM-BROKER-TIMEOUT-FIXTURE | LOW | `SimulatedBroker.refresh_positions()` is no-op or instant-success; in-process tests cannot exercise Branch 4 (`verification_stale: true`) timeout path. New `SimulatedBrokerWithRefreshTimeout` fixture variant added at S5c — enables CL-3 cross-layer test AND a dedicated Branch 4 unit test. Fixture lives in test code only; production `SimulatedBroker` semantics unchanged. | Sprint 31.92 Phase A Tier 3 (Tier 3 item E); resolved Sprint 31.92 S5c | RESOLVED |
```

**Anchor 5:** Active sprint pointer (top of file, sprint progress section).

**Patch:** Update to point to Sprint 31.93 component-ownership as next active
sprint per build-track queue.

### C2. docs/decision-log.md — Write DEC-390 below

**Anchor:** Append after DEC-389 (Sprint 31.915 evaluation.db retention).

**Pattern:** B (Pattern A applies if Tier 3 fires mid-sprint at M-R2-5).

**DEC-390 entry skeleton (REVISED for Phase B re-run; populated at sprint-close):**

```markdown
### DEC-390 | Concurrent-Trigger Race Closure with Mechanism-Selected Path #1 + Position-Keyed Locate-Rejection Suppression with Broker-Verified Timeout (incl. Branch 4 + HALT-ENTRY Coupling) + Long-Only SELL-Volume Ceiling with Pending-Share Reservation (Synchronous-Update Invariant on All Bookkeeping Callback Paths) + Reconstructed-Position Refusal + AC2.7 Watchdog Auto-Activation + 5 Cross-Layer Composition Tests + DEF-212 Constant Drift Wiring with Dual-Channel Rollback Warning + `--allow-rollback` CLI Gate

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 (sealed {SPRINT_CLOSE_DATE}) |
| **Tier 3 verdicts** | Phase A Tier 3 (2026-04-29): REVISE_PLAN — FAI entry #9 + H-R2-1 protection scope extension + ≥4 cross-layer tests + C-R2-1↔H-R2-2 coupling + M-R2-1 auto-activation + M-R2-4 adversarial sub-spike + FAI #5 N≥100 + FAI #8 option (a). M-R2-5 mid-sprint Tier 3: {fired? PROCEED-with-conditions / not required — fill at close} |
| **Adversarial review** | Round 1 (2026-04-29): Outcome B (3 Critical + 4 High + 3 Medium); Round 2 (2026-04-29): 1C+5H+5M+3L (A14 fired triggering Phase A re-entry per Outcome C); Round 3 (post-Phase-B-re-run): {verdict at close} |
| **Context** | Sprint 31.91's DEC-386 claimed `~98%` closure of DEF-204 mechanism via OCA-Group Threading + Broker-Only Safety. Tier 3 #1 (2026-04-27) verdict PROCEED. **Empirically falsified 2026-04-28** by paper-session debrief: 60 NEW phantom shorts post-DEC-386 across two distinct uncovered paths — (Path #1) trail-stop / bracket-stop concurrent-trigger race; (Path #2) locate-rejection-as-held retry storm. DEC-386's `~98%` claim was made in good faith from data available at Tier 3 #1 (24-hour pre-paper-session window); the falsification is acknowledged here, DEC-386 itself preserved unchanged (leave-as-historical posture). **Round-1 adversarial review surfaced 3 Critical findings:** C-1 (asyncio yield-gap race in ceiling between emit and fill), C-2 (restart-safety hole for reconstructed positions), C-3 (H1 cancel-and-await reintroduces AMD-2's closed gap). All 3 dispositioned per `revision-rationale.md`. **Round 2 surfaced 1 Critical (C-R2-1: refresh-fail Branch 4) + 5 Highs.** A14 fired (Round 2 produced Critical of FAI's primitive-semantics class) triggering Phase A re-entry per Outcome C. **Phase A re-entry surfaced 8-entry FAI; Phase A Tier 3 verdict REVISE_PLAN identified missing entry #9 (callback-path bookkeeping atomicity).** Phase B re-run + Phase C re-revision (2026-04-29) materialized all Tier 3 items A–E + 7 settled operator decisions; Round 3 verdict pending at time of this DEC entry. |
| **Decision** | Adopt a 4-layer composition mirroring DEC-385/386's layered-decomposition pattern, with structural closure framing (NOT aggregate percentage claims) per process-evolution lesson F.5: **(L1 Path #1 mechanism, S2a + S2b)** — chosen mechanism per S1a spike (expanded with adversarial axes per Decision 1 + N=100 propagation atomicity per Decision 2): {ONE OF: H2 amend-stop-price via `modifyOrder` (PRIMARY DEFAULT — AMD-2 invariant PRESERVED) / H4 hybrid (try amend, fall back to cancel-and-await on rejection) / H1 cancel-and-await as last-resort (AMD-2 invariant SUPERSEDED by AMD-2-prime; unprotected window bounded by `cancel_propagation_timeout` ≤ 2s; AC1.6 operator-audit logging mandatory)}. Selected based on Phase A spike S1a (`scripts/spike-results/spike-def204-round2-path1-results.json`, dated {S1a_DATE}) which measured {SPIKE_S1a_FINDINGS}. **Halt-or-proceed gate uses worst-axis Wilson UB AND zero-conflict-stress at N=100 hard gate per H-R2-2 tightening (Decision 2):** if even 1 trial in 100 exhibits a bracket-child OCA conflict, locate suppression, or position state inconsistency, H1 is NOT eligible regardless of `modifyOrder` Wilson UB. Applied to `_trail_flatten`, `_resubmit_stop_with_retry` emergency-flatten branch, and {conditionally} `_escalation_update_stop`. **(L2 Path #2 fingerprint + position-keyed suppression + broker-verified timeout with Branch 4 + HALT-ENTRY coupling, S3a + S3b)** — Add `_LOCATE_REJECTED_FINGERPRINT = "contract is not available for short sale"` (case-insensitive substring per S1b spike) and `_is_locate_rejection(error: BaseException) -> bool` helper in `argus/execution/ibkr_broker.py`, mirroring DEC-386's `_is_oca_already_filled_error` pattern. Add `OrderManager._locate_suppressed_until: dict[ULID, float]` keyed by `ManagedPosition.id` (NOT symbol — cross-position safety per Round-1 H-2). `OrderManagerConfig.locate_suppression_seconds` default = {SPIKE_S1b_DERIVED_VALUE} (S1b p99+20% margin; hard floor 18000s if H6 ruled-out per spike's `recommended_locate_suppression_seconds` field). **NEW `Broker.refresh_positions(timeout_seconds: float = 5.0)` ABC method** introduced per Tier 3 item C / C-R2-1 disposition; `IBKRBroker.refresh_positions` impl invokes `ib_async` cache-refresh; `SimulatedBroker.refresh_positions` no-op or instant-success; `SimulatedBrokerWithRefreshTimeout` test fixture (S5c, DEF-SIM-BROKER-TIMEOUT-FIXTURE) exercises the timeout path. **Suppression-timeout fallback queries broker for actual position state via `refresh_positions()` BEFORE alert emission** — three branches plus Branch 4 per Tier 3 item C: (a) zero → log INFO "held order resolved cleanly"; (b) expected long → log INFO "no phantom short"; (c) unexpected state → publish DEC-385's existing `phantom_short_retry_blocked` SystemAlertEvent; (d) **Branch 4: `Broker.refresh_positions()` raises or times out → publish alert with `verification_stale: true` metadata flag (operator-triage signal)**. **HALT-ENTRY coupling per Tier 3 item C:** position is marked `halt_entry_until_operator_ack=True` if H1 is the active mechanism AND `Broker.refresh_positions()` raises or times out; no further SELL attempts on the position; operator-driven resolution. DEF-158's 3-branch side-check preserved verbatim — Path #2 detection is structurally upstream. Wire suppression detection at `place_order` exception in 4 standalone-SELL paths with pre-emit suppression check. **(L3 Long-only SELL-volume ceiling with pending-share reservation + extended synchronous-update invariant + reconstructed-position refusal + AC2.7 watchdog auto-activation + 5 cross-layer composition tests, S4a-i + S4a-ii + S5c)** — Add THREE fields on `ManagedPosition`: `cumulative_pending_sell_shares: int = 0` (incremented synchronously at place-time before `await`; decremented on cancel/reject; transferred to filled on fill — closes Round-1 C-1 asyncio yield-gap race), `cumulative_sold_shares: int = 0` (incremented at confirmed fill), and `is_reconstructed: bool = False` (set True in `reconstruct_from_broker`; ceiling check refuses ALL ARGUS-emitted SELLs on reconstructed positions per Round-1 C-2 conservative posture; closes restart-safety hole until Sprint 31.94 D3 lands). **Synchronous-update invariant extended per Tier 3 item A + B / FAI entry #9 / DEF-FAI-CALLBACK-ATOMICITY:** AST-no-await scan + mocked-await injection regression test applied to ALL bookkeeping callback paths — `_reserve_pending_or_fail` (reference implementation), `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, and `_check_sell_ceiling`'s multi-attribute read. AST scan extended with reflective-pattern coverage per Decision 3 / DEF-FAI-8-OPTION-A: `**kw` unpacking, computed-value flag assignment, `getattr` reflective access. `_check_sell_ceiling(position, requested_qty, is_stop_replacement: bool=False)` returns False iff `position.is_reconstructed OR (cumulative_pending_sell_shares + cumulative_sold_shares + requested_qty > shares_total)`. Stop-replacement ceiling exemption per H-R2-5 — exemption permitted ONLY at `_resubmit_stop_with_retry` normal-retry path. Guards at all 5 standalone-SELL emit sites: `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`. **Bracket placement (`place_bracket_order`) EXPLICITLY EXCLUDED** from ceiling check (Round-1 H-1: would block all bracket placements; OCA enforces atomic cancellation). Violations refuse the SELL, do NOT increment pending counter, emit `SystemAlertEvent(alert_type="sell_ceiling_violation", severity="critical")`, log CRITICAL. Config-gated via `OrderManagerConfig.long_only_sell_ceiling_enabled` (default `true`, fail-closed). New `POLICY_TABLE` entry (14th) for `sell_ceiling_violation`; AST policy-table exhaustiveness regression guard updated. **AC2.7 `_pending_sell_age_seconds` watchdog with auto-activation per Decision 4:** new config field `OrderManagerConfig.pending_sell_age_watchdog_enabled` (values `auto` / `enabled` / `disabled`; default `auto`). `auto` mode flips to `enabled` on first observed `case_a_in_production` event. NOT manual operator activation. Provides structural fallback for any unmodeled locate-rejection string variant. Runtime state recorded for operator visibility per pre-live transition checklist. **5 cross-layer composition tests CL-1 through CL-5 per Decision 5 / DEF-CROSS-LAYER-EXPANSION (S5c):** CL-1 (L1 fails → L3 catches), CL-2 (L4 fails → L2 catches), CL-3 (FAI #2 + FAI #5 cross-falsification → HALT-ENTRY catches), CL-4 (L1 + L2 → L3 catches), CL-5 (L2 + L3 → protective stop-replacement allowed AND Branch 4 doesn't false-fire). CL-6 (rollback + locate-suppression interaction) explicitly OUT of Sprint 31.92 scope per Decision 5; deferred with rationale documented in `docs/process-evolution.md` lesson F.7. **(L4 DEF-212 rider with operator-visible dual-channel rollback warning + `--allow-rollback` CLI gate, S4b)** — `OrderManager.__init__` accepts `bracket_oca_type: int` keyword argument; `argus/main.py` construction call site passes `config.ibkr.bracket_oca_type`; 4 occurrences of `_OCA_TYPE_BRACKET = 1` module constant replaced by `self._bracket_oca_type`; module constant deleted. Grep regression guard. **AC4.6 dual-channel CRITICAL warning per H-R2-4:** ntfy.sh `system_warning` AND canonical-logger CRITICAL on `bracket_oca_type != 1` ("DEC-386 ROLLBACK ACTIVE: bracket_oca_type=0. OCA enforcement on bracket children is DISABLED. DEF-204 race surface is REOPENED. Operator must restore to 1 and restart unless emergency rollback in progress."). **AC4.7 `--allow-rollback` CLI gate per H-R2-4:** ARGUS exits with code 2 at startup if `bracket_oca_type != 1` AND `--allow-rollback` flag absent. Defense-in-depth + audit trail (operator must explicitly opt in to rollback at every startup). `IBKRConfig.bracket_oca_type` Pydantic validator UNCHANGED — rollback escape hatch preserved per DEC-386 design intent. Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) DEFERRED to Sprint 31.93 (component-ownership scope). |
| **Rationale** | DEF-204's mechanism is composite: (Path #1) is a fill-side race that DEC-386 S1b OCA threading does NOT cover (concurrent triggers fire both legs before OCA cancellation can propagate); (Path #2) is a misclassification — IBKR's "contract not available for short sale" is a HOLD pending borrow, NOT a transient reject, and ARGUS's retry layer treats it as transient. Both paths produce phantom shorts that are observable but not preventable by Sprint 31.91's mechanism. The architectural fix at L1 + L2 is structural: DEC-386 enforces atomic OCA at the broker layer; DEC-390 L1 ensures only ONE leg can be in flight at once (H2 amend keeps bracket stop live with updated trigger price; H1/H4 fallback uses cancel-and-await with operator-audit logging); DEC-390 L2 detects the hold-pending-borrow state, suppresses retry-storm at position-keyed granularity, AND verifies broker state via the new `Broker.refresh_positions()` ABC before emitting alerts (eliminating false-positive class during reconnect events; Branch 4 covers refresh-failure case; HALT-ENTRY coupling under H1 + refresh-fail prevents phantom short on the unhappy path). L3 (ceiling with pending reservation) is structural defense-in-depth: the reservation pattern closes the asyncio yield-gap race (Round-1 C-1); the `is_reconstructed` refusal posture closes the restart-safety hole (Round-1 C-2) until Sprint 31.94 D3's policy decision lands; the synchronous-update invariant extended to all bookkeeping callback paths (Tier 3 item A + B + FAI entry #9 + DEF-FAI-CALLBACK-ATOMICITY) closes the broader primitive-semantics gap that the original C-1 disposition narrowed too tightly. AC2.7 watchdog auto-activation (Decision 4 + DEF-FAI-N-INCREASE forward-looking) provides the structural fallback if an unmodeled locate-rejection variant emerges. The 5 cross-layer composition tests (Decision 5 + DEF-CROSS-LAYER-EXPANSION) prove that the failure of any one layer is caught by another — which is the architectural defense against DEC-386's empirical falsification class (a mechanism that looks correct in isolation but composes catastrophically). L4 (DEF-212 wiring with dual-channel rollback warning + `--allow-rollback` CLI gate) is cosmetic technical debt cleanup that piggybacks on the OrderManager construction-site touches; the AC4.6/AC4.7 defense-in-depth ensures operators don't silently run with rollback enabled. The 4-layer layering across S2a–S5c makes each step self-contained and individually testable; regression-checklist invariants 13 + 14 + 15 + 16 + 17 + 18 + 19 + 20 + 21 + 22 + 23 + 24 + 25 + 26 + 27 collectively enforce monotonic safety. The Phase A spikes (S1a + S1b) and validation artifacts (S5a + S5b path1/path2 + composite via Pytest side-effect at S5c + cross-layer tests CL-1 through CL-5 at S5c) are the falsifiable foundation. **Critical framing per process-evolution lesson F.5:** DEC-390 explicitly does NOT make aggregate percentage closure claims (no "comprehensive," "complete," "fully closed," or "covers ~N%" language). Per regression invariant on validation artifact framing: AC5.1/AC5.2/AC5.5 validate IN-PROCESS LOGIC against SimulatedBroker; cessation criterion #5 (5 paper sessions clean post-seal) is the production-validation gate. **Process-evolution lesson F.6 (FAI completeness pattern):** Round 1 + Round 2 + Phase A Tier 3 each surfaced one primitive-semantics miss (asyncio yield-gap, ib_async cache freshness, callback-path bookkeeping atomicity); the FAI made entry #9's miss DETECTABLE during Phase A Tier 3 review; Round 3 full-scope cross-check is the next defense layer. |
| **Impact** | DEF-204's Path #1 + Path #2 mechanisms structurally closed by L1 + L2; remaining mechanism residue (broker-only events not flowing through OCA, operator manual orders, future API drift, unmodeled locate-rejection variants) is bounded by L3 ceiling with extended synchronous-update invariant + `is_reconstructed` refusal posture + AC2.7 watchdog auto-activation. The 5 cross-layer composition tests prove defense-in-depth catches single-layer failures. DEC-386's `~98%` claim is empirically REPLACED by DEC-390's structural closure framing + falsifiable validation artifacts. Operator daily-flatten mitigation cessation criteria #1+#2+#3 SATISFIED (via Sprint 31.91 + 31.92 cumulative); #4 (Sprint 31.92 sealed) MET at {SPRINT_CLOSE_DATE}; **#5 RESET TO 0/5** — 5 paper sessions clean post-Sprint-31.92 seal needed. Live-trading readiness requires: (1) Sprint 31.92 sealed cleanly; (2) ≥5 paper sessions clean post-seal (criterion #5 satisfied); (3) DEF-208 pre-live paper stress test under live-config simulation (Sprint 31.93 OR 31.94); (4) Sprint 31.91 §D7 gate criteria. Sprint 31.93 inherits Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation) + DEF-208 fixture infrastructure. Sprint 31.94 inherits DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound + reconnect-event coupling for L2 suppression dict (`IBKRReconnectedEvent` consumer; AC2.5 broker-verification is the structural mitigation Sprint 31.92 ships in lieu of the consumer) + **Sprint 31.94 D3 eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION** (boot-time adoption-vs-flatten policy retires the conservative refusal posture) + **DEF-FAI-2-SCOPE high-volume axis** (Sprint 31.94 reconnect-recovery scope). New risks filed: **RSK-DEC-390-AMEND** (PRIMARY if H2 selected; IBKR API version assumption) OR **RSK-DEC-390-CANCEL-AWAIT-LATENCY** (FALLBACK if H1 or H4-with-fallback-active; unprotected-window cost), **RSK-DEC-390-FINGERPRINT** (locate-rejection error string drift; quarterly re-validation flag), **RSK-CEILING-FALSE-POSITIVE** (pending-reservation state-transition completeness on ALL bookkeeping paths per Tier 3 item A + B; partial-fill aggregation; concurrent yield-gap race), **RSK-RECONSTRUCTED-POSITION-DEGRADATION** (time-bounded by Sprint 31.94 D3; severity rated MEDIUM-HIGH per Severity Calibration Rubric — operator daily-flatten empirically failed Apr 28 with 27 of 87 ORPHAN-SHORT detections from a missed run), **RSK-SUPPRESSION-LEAK** (dict GC bound; AC2.5 broker-verification mitigates false-positive alerts), **RSK-FAI-COMPLETENESS** (FAI's self-falsifiability clause triggered during Phase A Tier 3; Round 3 full-scope cross-check is the next defense layer), **RSK-CROSS-LAYER-INCOMPLETENESS** (cross-layer composition test count at 5 — above template floor; CL-6 explicitly deferred). 6 new DEFs filed at Phase A Tier 3 (DEF-FAI-CALLBACK-ATOMICITY, DEF-CROSS-LAYER-EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE, DEF-FAI-8-OPTION-A, DEF-SIM-BROKER-TIMEOUT-FIXTURE) — 5 resolved in-sprint at Sprint 31.92; DEF-FAI-2-SCOPE documented out-of-scope with sprint-target Sprint 31.94. |
| **Cross-References** | **DEFs:** DEF-204 (closed by mechanism — RESOLVED-PENDING-PAPER-VALIDATION at sprint-close; RESOLVED at criterion #5 satisfaction); DEF-212 (closed by L4 — RESOLVED); DEF-FAI-CALLBACK-ATOMICITY (Phase A Tier 3 entry #9; resolved S4a-ii); DEF-CROSS-LAYER-EXPANSION (Phase A Tier 3; resolved S5c); DEF-FAI-N-INCREASE (Phase A Tier 3 Decision 2; resolved S1a refinement); DEF-FAI-2-SCOPE (Phase A Tier 3; documented out-of-scope, Sprint 31.94 target); DEF-FAI-8-OPTION-A (Phase A Tier 3 Decision 3; resolved S4a-ii); DEF-SIM-BROKER-TIMEOUT-FIXTURE (Phase A Tier 3 item E; resolved S5c). **Predecessor DECs:** DEC-385 (Side-Aware Reconciliation Contract — preserved byte-for-byte; `phantom_short_retry_blocked` alert path reused at L2 broker-verified fallback; Branch 4 reuses same alert with `verification_stale: true` metadata); DEC-386 (OCA-Group Threading + Broker-Only Safety — preserved byte-for-byte; `~98%` claim empirically superseded by DEC-390's structural closure; `bracket_oca_type=0` rollback escape hatch preserved with new AC4.6 dual-channel startup CRITICAL warning + AC4.7 `--allow-rollback` CLI gate); DEC-388 (Alert Observability Architecture — `POLICY_TABLE` extended with 14th entry for `sell_ceiling_violation`; existing 13 entries unchanged). **Adjacent DECs:** DEC-117 (atomic bracket — preserved); DEC-364 (cancel_all_orders ABC — preserved, no extension); DEC-369 (broker-confirmed reconciliation — preserved; AC3.6 + AC3.7 ceiling+is_reconstructed compose additively); DEC-372 (stop retry caps — preserved; L1 mechanism applies to emergency-flatten branch); DEC-026 (ULID — `ManagedPosition.id` is the position-keyed suppression dict key per Round-1 H-2). **New ABC method:** `Broker.refresh_positions(timeout_seconds: float = 5.0)` introduced on `argus/execution/broker.py` per Tier 3 item C / C-R2-1 disposition. **Validation artifacts:** S1a spike `scripts/spike-results/spike-def204-round2-path1-results.json` (PROCEED, valid ≤30 days, expanded with adversarial axes per Decision 1 + N=100 propagation atomicity per Decision 2; new schema fields `adversarial_axes_results`, `worst_axis_wilson_ub`, `h1_propagation_n_trials=100`, `h1_propagation_zero_conflict_in_100: bool`); S1b spike `scripts/spike-results/spike-def204-round2-path2-results.json` (PROCEED, valid ≤30 days, hard-to-borrow microcap symbols measured per Round-1 M-1); S5a validation `scripts/spike-results/sprint-31.92-validation-path1.json` (`path1_safe: true`, in-process logic only); S5b validation `scripts/spike-results/sprint-31.92-validation-path2.json` (`path2_suppression_works: true`, in-process logic only); S5c composite Pytest `tests/integration/test_def204_round2_validation.py` + `scripts/spike-results/sprint-31.92-validation-composite.json` (Pytest-side-effect artifact, daily CI freshness per Round-1 M-3); S5c cross-layer composition tests CL-1 through CL-5 (`SimulatedBrokerWithRefreshTimeout` fixture exercises Branch 4 timeout path). **Diagnostic source:** `docs/debriefs/2026-04-28-paper-session-debrief.md`. **Risks:** RSK-DEC-390-AMEND (or RSK-DEC-390-CANCEL-AWAIT-LATENCY), RSK-DEC-390-FINGERPRINT, RSK-CEILING-FALSE-POSITIVE, RSK-RECONSTRUCTED-POSITION-DEGRADATION (rated MEDIUM-HIGH per Severity Calibration Rubric per design summary), RSK-SUPPRESSION-LEAK, RSK-FAI-COMPLETENESS (NEW Phase A Tier 3), RSK-CROSS-LAYER-INCOMPLETENESS (NEW Phase A Tier 3). **Time-bounded:** L2 suppression dict reconnect-event coupling deferred to Sprint 31.94; L3 `is_reconstructed` refusal posture eliminated by Sprint 31.94 D3; DEF-FAI-2-SCOPE high-volume axis Sprint 31.94. **Process-evolution lessons:** F.5 (structural closure framing vs aggregate percentage claims; sprint-close materialization Sprint 31.92), F.6 (FAI completeness pattern — Round 1 + Round 2 + Phase A Tier 3 = three primitive-semantics misses; Round 3 full-scope cross-check is the next defense layer; sprint-close materialization Sprint 31.92), F.7 (CL-6 deferral rationale — cross-layer test scope-shaping; sprint-close materialization Sprint 31.92). **Adversarial review:** Round 1 verdict + revision rationale at `docs/sprints/sprint-31.92-def204-round-2/{adversarial-review-findings.md, revision-rationale.md}`; Round 2 verdict at `docs/sprints/sprint-31.92-def204-round-2/round-2-disposition.md`; **Phase A Tier 3 verdict** at `docs/sprints/sprint-31.92-def204-round-2/tier-3-review-1-verdict.md`; Round 3 verdict at {path at close}. |
```

(Sprint-close authoring fills in `{SPRINT_CLOSE_DATE}`, `{Tier 3 verdict}`,
`{ONE OF: H2 amend / H4 hybrid / H1 cancel-and-await}`, `{S1a_DATE}`,
`{SPIKE_S1a_FINDINGS}`, `{SPIKE_S1b_DERIVED_VALUE}`, Round 3 verdict path,
and M-R2-5 mid-sprint Tier 3 outcome if fired.)

### C3. docs/dec-index.md — Add DEC-390 entry

**Anchor:** Append in DEC ordering (after DEC-389).

**Patch:**
```markdown
| DEC-390 | 2026-04-{TBD} | Sprint 31.92 | DEF-204 Round 2 — 4-layer composition (Path #1 mechanism + Path #2 with Branch 4 + HALT-ENTRY coupling + ceiling with extended synchronous-update invariant + reconstructed-position refusal + AC2.7 auto-activation + 5 cross-layer composition tests + DEF-212 wiring with dual-channel rollback warning + `--allow-rollback` CLI gate) | ACTIVE |
```

### C4. docs/sprint-history.md — Add Sprint 31.92 row + per-sprint detail block

**Anchor 1:** Append row to Sprint History table (sprint number ordering).

**Patch:**
```markdown
| 31.92 | DEF-204 Round 2 — concurrent-trigger race + locate-rejection retry storm + ceiling with pending reservation (extended synchronous-update invariant on all bookkeeping callback paths) + AC2.7 watchdog auto-activation + 5 cross-layer composition tests + DEF-212 rider with dual-channel rollback warning + `--allow-rollback` CLI gate | {DELTA_PYTEST}+{DELTA_VITEST}V | {SPRINT_DATES} | DEC-390 |
```

**Anchor 2:** Append per-sprint detail block at end of file.

**Patch (skeleton, populated at sprint-close):**
```markdown
## Sprint 31.92: DEF-204 Round 2

**Sealed:** {SPRINT_CLOSE_DATE}
**Sessions:** 13 (S1a + S1b spikes; S2a + S2b Path #1; S3a + S3b Path #2; S4a-i ceiling core; S4a-ii callback-path AST guard + reflective sub-tests; S4b DEF-212 rider + AC4.6 dual-channel + AC4.7 `--allow-rollback`; S5a + S5b path1/path2 validation; S5c cross-layer composition tests CL-1 through CL-5 + composite Pytest with JSON side-effect)
**Test delta:** +{DELTA_PYTEST} pytest, +{DELTA_VITEST} Vitest
**Adversarial review:** Round 1 (Outcome B, 3 Critical + 4 High + 3 Medium dispositioned per `revision-rationale.md`); Round 2 (1C+5H+5M+3L; A14 fired triggering Phase A re-entry per Outcome C); **Phase A Tier 3 verdict REVISE_PLAN** (`tier-3-review-1-verdict.md`); **Phase B re-run + Phase C re-revision** (this revision); Round 3 ({verdict})
**Tier 3 review (mid-sprint M-R2-5):** {if fired: PROCEED-with-conditions verdict at `docs/sprints/sprint-31.92-def204-round-2/tier-3-review-{N}-verdict.md` / else: N/A}

**Outcome:** DEF-204's Path #1 (trail/bracket concurrent-trigger race) and Path #2 (locate-rejection retry storm) structurally closed via DEC-390 L1 + L2. Long-only SELL-volume ceiling with pending-share reservation + extended synchronous-update invariant on all bookkeeping callback paths (per Phase A Tier 3 entry #9 / DEF-FAI-CALLBACK-ATOMICITY) + reconstructed-position refusal posture + AC2.7 watchdog auto-activation (L3) provides structural defense-in-depth. 5 cross-layer composition tests CL-1 through CL-5 (S5c) prove defense-in-depth catches single-layer failures. DEF-212 (`_OCA_TYPE_BRACKET` constant drift) closed via L4 wiring + AC4.6 dual-channel rollback warning + AC4.7 `--allow-rollback` CLI gate. DEF-204 status: RESOLVED-PENDING-PAPER-VALIDATION (transitions to RESOLVED at cessation criterion #5 — 5 paper sessions clean post-seal). DEC-386's `~98%` aggregate claim empirically replaced by DEC-390's structural closure framing per process-evolution lesson F.5.

**Key sessions:**
- S1a: Path #1 mechanism spike — measured H2 (modify_order) and H1 (cancel_all_orders await_propagation) against paper IBKR; expanded with adversarial axes per Decision 1 + N=100 propagation atomicity per Decision 2; selected mechanism: {H2/H4/H1}.
- S1b: Path #2 fingerprint + hold-pending-borrow window spike — measured against operator-curated hard-to-borrow microcap list (≥5 symbols × ≥10 trials); fingerprint string captured: `"contract is not available for short sale"`; suppression-window default derived: {SPIKE_S1b_DERIVED_VALUE}s.
- S2a + S2b: Path #1 implementation in `_trail_flatten` + `_resubmit_stop_with_retry` emergency-flatten branch + (conditionally) `_escalation_update_stop`; mechanism-conditional AMD-2 framing; AC1.6 operator-audit logging.
- S3a + S3b: Path #2 implementation — fingerprint helper + position-keyed suppression dict + 4-emit-site wire-up + `Broker.refresh_positions()` ABC method + broker-verified suppression-timeout fallback with three branches + Branch 4 (`verification_stale: true`) on refresh failure + HALT-ENTRY coupling under H1 + refresh-fail per Tier 3 item C.
- S4a-i: Long-only SELL-volume ceiling with pending reservation pattern + `is_reconstructed` flag + 5 emit-site guards + new POLICY_TABLE entry + AC2.7 watchdog auto-activation.
- S4a-ii: Synchronous-update invariant extended to all bookkeeping callback paths per Tier 3 item A + B / FAI entry #9 / DEF-FAI-CALLBACK-ATOMICITY — AST-no-await scan + mocked-await injection regression on `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, and `_check_sell_ceiling`'s multi-attribute read; reflective-pattern coverage per Decision 3 / DEF-FAI-8-OPTION-A.
- Mid-sprint Tier 3 review event (M-R2-5) between S4a-ii and S5a/S5b: {fired? outcome / not required}.
- S4b: DEF-212 rider — `OrderManager.__init__(bracket_oca_type)` wiring + 4 substitutions + module constant deletion + AC4.6 dual-channel CRITICAL warning + AC4.7 `--allow-rollback` CLI gate.
- S5a + S5b: Falsifiable in-process validation — path1.json + path2.json + composite Pytest with JSON side-effect + restart-during-active-position regression test.
- S5c: 5 cross-layer composition tests CL-1 through CL-5 + `SimulatedBrokerWithRefreshTimeout` test fixture (DEF-SIM-BROKER-TIMEOUT-FIXTURE).

**Inherited follow-ups:**
- Sprint 31.93: Tier 3 #1 Concern A (`_is_oca_already_filled_error` relocation); DEF-208 pre-live paper stress test fixture; component-ownership refactor.
- Sprint 31.94: DEF-211 D1+D2+D3 (sprint-gating); RSK-DEC-386-DOCSTRING bound; `IBKRReconnectedEvent` producer/consumer wiring (eliminates RSK-SUPPRESSION-LEAK reconnect blindness); D3 boot-time adoption-vs-flatten policy (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION); DEF-FAI-2-SCOPE high-volume axis implementation.
- Sprint 35+: DEF-209 extended scope (`Position.side`, `redundant_exit_observed`, `cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed` SQLite persistence — Learning Loop V2 prerequisite); per Phase A Tier 3 forward-filing, if SQLite persistence lands for bookkeeping counters, synchronous-update invariant (entry #9) extends to persistence layer (write-then-flush atomicity).

**RSKs filed:**
- RSK-DEC-390-AMEND (PRIMARY if H2 selected) OR RSK-DEC-390-CANCEL-AWAIT-LATENCY (FALLBACK if H1/H4 with H1 fallback active)
- RSK-DEC-390-FINGERPRINT
- RSK-CEILING-FALSE-POSITIVE (pending-reservation race scenarios — extended scope per Tier 3 item A + B)
- RSK-RECONSTRUCTED-POSITION-DEGRADATION (time-bounded by Sprint 31.94 D3; severity rated MEDIUM-HIGH per Severity Calibration Rubric)
- RSK-SUPPRESSION-LEAK (partially mitigated by AC2.5 broker-verification; full coupling deferred to Sprint 31.94)
- RSK-FAI-COMPLETENESS (NEW Phase A Tier 3; Round 3 full-scope cross-check is the next defense layer)
- RSK-CROSS-LAYER-INCOMPLETENESS (NEW Phase A Tier 3; CL-6 deferred per Decision 5)

**DEFs filed at Phase A Tier 3 (5 resolved in-sprint, 1 documented out-of-scope):**
- DEF-FAI-CALLBACK-ATOMICITY (resolved S4a-ii)
- DEF-CROSS-LAYER-EXPANSION (resolved S5c)
- DEF-FAI-N-INCREASE (resolved S1a refinement)
- DEF-FAI-2-SCOPE (documented out-of-scope; Sprint 31.94 target)
- DEF-FAI-8-OPTION-A (resolved S4a-ii)
- DEF-SIM-BROKER-TIMEOUT-FIXTURE (resolved S5c)

**Process-evolution lessons:** F.5 (structural closure framing vs aggregate percentage claims), F.6 (FAI completeness pattern — three primitive-semantics misses across Round 1 + Round 2 + Phase A Tier 3; Round 3 full-scope cross-check is the next defense layer), F.7 (CL-6 deferral rationale — cross-layer test scope-shaping). All three captured at sprint-close per `docs/process-evolution.md`; metarepo amendments to `protocols/sprint-planning.md` + `protocols/adversarial-review.md` + `protocols/tier-3-review.md` are RETRO-FOLD candidates for next campaign.
```

### C5. docs/roadmap.md — Sprint 31.92 close-out narrative + roadmap re-baseline

**Anchor 1:** Sprint 31.92 entry in roadmap timeline.

**Patch:** Mark sealed; cross-reference DEC-390; cross-reference Sprint 31.93
as next active sprint.

**Anchor 2:** Build-track queue re-baseline.

**Patch:**
- Sprint 31.93 (component-ownership) → next active.
- Sprint 31.94 (reconnect-recovery + DEF-211 D1+D2+D3 + RSK-DEC-386-DOCSTRING bound + DEF-FAI-2-SCOPE high-volume axis) → queued.
- Sprint 31.95 (alpaca-retirement) → queued.
- Sprint 31B (Research Console / Variant Factory) → queued post-31.95.

**Anchor 3:** Cessation criteria summary section (top-of-file or designated section).

**Patch:** Update cessation criteria for DEF-204 (criterion #5 reset to 0/5;
daily-flatten continues until satisfaction; criterion #6 Sprint 31.94 sealed
eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION).

### C6. docs/project-knowledge.md — DEF table sync + active sprint pointer

**Anchor 1:** DEF table in project-knowledge.md (mirror of CLAUDE.md DEF table).

**Patch:** Sync with C1 changes — DEF-204 row updated; DEF-212 row updated to
RESOLVED; 6 new DEF rows appended (DEF-FAI-CALLBACK-ATOMICITY, DEF-CROSS-LAYER-
EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE, DEF-FAI-8-OPTION-A,
DEF-SIM-BROKER-TIMEOUT-FIXTURE).

**Anchor 2:** Active sprint pointer.

**Patch:** Update to point to Sprint 31.93 component-ownership.

### C7. docs/architecture.md — §3.3 Broker abstraction additions + §3.7 OrderManager additions

#### C7.1. §3.3 Broker abstraction — `refresh_positions()` ABC method

**Anchor:** §3.3 Broker abstraction subsection.

**Patch (additive):**

```markdown
**Sprint 31.92 additions (DEC-390 L2):**
- **`Broker.refresh_positions(timeout_seconds: float = 5.0) -> None`** — new ABC method introduced per DEC-390 L2 / Phase A Tier 3 item C (C-R2-1 disposition). Forces a broker-side cache refresh and waits up to `timeout_seconds` for the refresh to complete. Used at suppression-timeout fallback to verify actual broker position state BEFORE alert emission, eliminating the false-positive alert class during reconnect events. Three branches plus Branch 4: (a) zero (held order resolved cleanly), (b) expected long (no phantom short), (c) unexpected state (publish `phantom_short_retry_blocked`), (d) Branch 4: refresh raises or times out (publish alert with `verification_stale: true` metadata flag). HALT-ENTRY coupling: position is marked `halt_entry_until_operator_ack=True` if H1 is the active mechanism AND `Broker.refresh_positions()` raises or times out.
- **`IBKRBroker.refresh_positions` impl** invokes `ib_async`'s cache-refresh primitive with timeout enforcement.
- **`SimulatedBroker.refresh_positions` impl** is no-op or instant-success (production semantics unchanged).
- **`SimulatedBrokerWithRefreshTimeout` test fixture** (`tests/execution/fixtures/simulated_broker_with_refresh_timeout.py`) subclasses `SimulatedBroker` and raises `asyncio.TimeoutError` from `refresh_positions()` for in-process Branch 4 testing (DEF-SIM-BROKER-TIMEOUT-FIXTURE).
```

#### C7.2. §3.7 Order Manager additions

**Anchor:** §3.7 Order Manager subsection.

**Patch (additive):**

```markdown
**Sprint 31.92 additions (DEC-390 L1 + L3 + L4):**
- **`ManagedPosition.cumulative_pending_sell_shares: int`** — per-position SELL-volume PENDING reservation, incremented synchronously at place-time before `await place_order(...)`, decremented on cancel/reject, transferred to `cumulative_sold_shares` on fill. Closes asyncio yield-gap race (Round-1 C-1). **Synchronous-update invariant extended to all bookkeeping callback paths per Phase A Tier 3 item A + B / FAI entry #9 / DEF-FAI-CALLBACK-ATOMICITY** — AST-no-await scan + mocked-await injection regression test applied to `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, and `_check_sell_ceiling`'s multi-attribute read.
- **`ManagedPosition.cumulative_sold_shares: int`** — per-position SELL-volume FILLED counter, incremented at confirmed SELL fill. In-memory only.
- **`ManagedPosition.is_reconstructed: bool`** — set `True` in `reconstruct_from_broker`. Ceiling check refuses ALL ARGUS-emitted SELLs on reconstructed positions until Sprint 31.94 D3's policy decision lands (RSK-RECONSTRUCTED-POSITION-DEGRADATION; severity rated MEDIUM-HIGH per Severity Calibration Rubric per Sprint 31.92 design summary). Operator-manual flatten via `scripts/ibkr_close_all_positions.py` is the only closing mechanism.
- **`ManagedPosition.halt_entry_until_operator_ack: bool`** (NEW per Tier 3 item C) — set `True` when H1 is the active mechanism AND `Broker.refresh_positions()` raises or times out at suppression-timeout fallback. Blocks all subsequent SELL attempts on the position; operator-driven resolution.
- **`OrderManager._locate_suppressed_until: dict[ULID, float]`** — POSITION-keyed (NOT symbol-keyed) suppression state for IBKR locate-rejection holds. Cross-position safety preserved (Round-1 H-2). Default suppression window {SPIKE_S1b_DERIVED_VALUE} (`OrderManagerConfig.locate_suppression_seconds`, S1b p99+20% margin).
- **AC2.5 broker-verification at suppression timeout** — calls new `broker.refresh_positions(timeout_seconds=5.0)` BEFORE alert emission. Three branches plus Branch 4 (`verification_stale: true`) on refresh failure per Tier 3 item C. HALT-ENTRY coupling under H1 + refresh-fail.
- **AC2.7 `_pending_sell_age_seconds` watchdog with auto-activation** (per Decision 4) — new config field `OrderManagerConfig.pending_sell_age_watchdog_enabled` (values `auto` / `enabled` / `disabled`; default `auto`). `auto` mode flips to `enabled` on first observed `case_a_in_production` event. Watchdog runtime state recorded for operator visibility per pre-live transition checklist.
- **`bracket_oca_type` flow** — `IBKRConfig.bracket_oca_type` (Pydantic field, range `[0, 1]`, default `1`) → `OrderManager.__init__(bracket_oca_type)` → `self._bracket_oca_type` (replaces former `_OCA_TYPE_BRACKET` module constant). **AC4.6 dual-channel CRITICAL warning** when `bracket_oca_type != 1` — ntfy.sh `system_warning` AND canonical-logger CRITICAL ("DEC-386 ROLLBACK ACTIVE: DEF-204 race surface is REOPENED"). **AC4.7 `--allow-rollback` CLI gate** — ARGUS exits with code 2 at startup if `bracket_oca_type != 1` AND `--allow-rollback` flag absent. Defense-in-depth + operator audit trail.
- **Path #1 mechanism** — Trail-stop / bracket-stop concurrent-trigger race closed via {H2 amend-stop-price PRIMARY DEFAULT — AMD-2 preserved / H4 hybrid amend-with-cancel-fallback / H1 cancel-and-await as last-resort — AMD-2 superseded by AMD-2-prime} per S1a-spike-selected (expanded with adversarial axes per Decision 1 + N=100 propagation atomicity per Decision 2). Operator-audit logging (AC1.6) on every cancel-and-await dispatch.
- **Path #2 detection** — IBKR rejection error string `"contract is not available for short sale"` fingerprinted via `_is_locate_rejection()` in `argus/execution/ibkr_broker.py`; position suppressed for `locate_suppression_seconds`; broker-verified suppression-timeout fallback eliminates false-positive alerts (Round-1 H-3); Branch 4 covers refresh-failure case.
```

### C8. docs/risk-register.md — File 7 RSKs (5 from Round-1-revised + 2 NEW from Phase A Tier 3)

#### C8.1. RSK-DEC-390-AMEND (PRIMARY — proposed, conditional on H2 selection by S1a)

```markdown
### RSK-DEC-390-AMEND | Path #1 H2 Amend-Stop-Price IBKR API Version Assumption

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene); conditional on H2 selection at S1a |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L1 selected H2 (amend bracket stop's price via `modifyOrder`) per S1a spike. The amend-stop-price path depends on IBKR's `modifyOrder` semantics being deterministic at sub-50ms latency. If a future IBKR API change introduces non-determinism (e.g., `modifyOrder` becomes async-acknowledged-but-eventually-applied), the mechanism degrades silently — phantom shorts may re-emerge without an explicit error. The dependency is on a single IBKR API call's behavior; ARGUS has no detection mechanism for "modify_order ack received but not actually applied." |
| **Mitigation** | (a) S2a regression test asserts mock `IBKRBroker.modify_order` was called BEFORE `place_order(SELL)` — any code-path bypass is caught immediately. (b) `docs/live-operations.md` paragraph documents the IBKR-API-version assumption + quarterly operational re-validation flag. (c) Cessation criterion #5 (5 paper sessions clean post-seal) is itself a continuous validation. (d) Spike artifact 30-day freshness check via A-class halt A13 — if `ib_async`/IBKR Gateway upgraded, both spikes re-run before paper trading resumes. (e) RSK-DEC-390-FINGERPRINT-class quarterly re-validation cadence. (f) S1a adversarial axes per Decision 1 stress modify_order under concurrent amends, reconnect window, stale order IDs — gives early signal of API-behavior drift. |
| **Trigger conditions** | (1) `ib_async` library version change. (2) IBKR Gateway version change. (3) Quarterly re-validation cycle (operator runs S1a script). (4) ANY paper-session phantom short matching Path #1 signature post-seal. |
| **Cross-References** | DEC-390 L1; AC1.2 (H2 path regression test); S1a spike artifact (expanded with adversarial axes per Decision 1); `docs/live-operations.md` (post-sprint paragraph); A-class halt A13. |
```

#### C8.2. RSK-DEC-390-CANCEL-AWAIT-LATENCY (FALLBACK — proposed, conditional on H1 or H4 selection by S1a; NEW per Round-1 C-3)

```markdown
### RSK-DEC-390-CANCEL-AWAIT-LATENCY | Path #1 H1 Cancel-and-Await Unprotected Window

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene); conditional on H1 OR H4-with-fallback-active selection at S1a |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L1 fell to H1 cancel-and-await (last-resort) OR H4 hybrid (with cancel-and-await fallback path) per S1a spike. The cancel-and-await branch supersedes AMD-2 invariant by AMD-2-prime — unprotected window bounded by `cancel_propagation_timeout` ≤ 2s per DEC-386 S1c. On volatile $7–15 microcap stocks during fast moves, 200ms can equate to $0.50–$1.00 of slippage. The trade-off is documented but real. **Round 2 H-R2-2 hard gate** (Decision 2): if even 1 trial in 100 (cancel-then-immediate-SELL stress at N=100) exhibits a bracket-child OCA conflict, locate suppression, or position state inconsistency, H1 is NOT eligible regardless of `modifyOrder` Wilson UB — this RSK does not file. **Tier 3 item C HALT-ENTRY coupling:** when H1 active AND `Broker.refresh_positions()` raises/times out at suppression-timeout fallback, position is marked `halt_entry_until_operator_ack=True`; no further SELL attempts; operator-driven resolution. This bounds the worst-case unprotected-window cost. |
| **Mitigation** | (a) AC1.6 operator-audit structured log fires on every cancel-and-await dispatch — operator can audit each occurrence post-session. (b) `docs/live-operations.md` paragraph documents the trade-off + when to escalate. (c) Sprint Spec mandates DEC-390 explicitly call out H1 as last-resort with rationale. (d) Cessation criterion #5 (5 paper sessions clean post-seal) catches catastrophic slippage in production. (e) HALT-ENTRY coupling under refresh-fail bounds compounding failure modes. |
| **Trigger conditions** | (1) Operator-observed slippage cluster on cancel-and-await dispatches (audit log surfaces this). (2) Quarterly re-validation cycle. (3) ANY paper-session phantom short matching Path #1 signature post-seal. |
| **Cross-References** | DEC-390 L1; AC1.6 operator-audit logging; AC2.5 HALT-ENTRY coupling under H1 + refresh-fail; S1a spike artifact (N=100 propagation per Decision 2); `docs/live-operations.md` (post-sprint paragraph); regression invariant 24. |
```

#### C8.3. RSK-DEC-390-FINGERPRINT (UNCONDITIONAL)

```markdown
### RSK-DEC-390-FINGERPRINT | Path #2 Locate-Rejection Error String Drift

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (operational hygiene) |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L2 detects IBKR's locate-rejection via case-insensitive substring match against `"contract is not available for short sale"` (captured by S1b spike). If IBKR changes this string (different `ib_async` version, different broker plumbing, different locale), locate-rejection detection silently fails → Path #2 retry storm re-emerges. The substring approach was selected at S3a because S1b spike confirmed string stability across ≥10 trials per symbol × ≥5 hard-to-borrow microcaps; if string drifts in production, fixture and production diverge but production falls through to existing CRITICAL-log path (NOT silent failure — the rejection still surfaces, just not classified). **Structural fallback:** AC2.7 watchdog with auto-activation per Decision 4 catches age-based pending-SELL anomalies regardless of fingerprint match. |
| **Mitigation** | (a) S5b validation re-runs against synthetic locate-rejection fixture; if string drifts, fixture and production diverge but production falls through to existing CRITICAL-log path. (b) Quarterly operational re-validation flag — operator runs S1b script against live paper IBKR every quarter and asserts string match. (c) CI check (added at S5b) that `scripts/spike-results/spike-def204-round2-path2-results.json` is < 90 days old. (d) A-class halt A13 fires if spike artifact >30 days old at first post-merge paper session. (e) AC2.7 watchdog auto-activates on first `case_a_in_production` event — structural fallback for unmodeled fingerprint variants. |
| **Trigger conditions** | (1) `ib_async` library version change. (2) IBKR Gateway version change. (3) Quarterly re-validation cycle. (4) Production observation: known hard-to-borrow symbol's SELL fails with rejection but `_is_locate_rejection()` returns False. (5) AC2.7 watchdog auto-activates (signal of fingerprint divergence). |
| **Cross-References** | DEC-390 L2; AC2.1 (fingerprint match test); AC2.7 (watchdog auto-activation per Decision 4); S1b spike artifact; `docs/live-operations.md` quarterly re-validation cadence; A-class halt A13. |
```

#### C8.4. RSK-CEILING-FALSE-POSITIVE (REVISED per Round-1 C-1 + Phase A Tier 3 item A + B)

```markdown
### RSK-CEILING-FALSE-POSITIVE | Long-Only SELL-Volume Ceiling False-Positive (Extended Synchronous-Update Invariant Scope)

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (mitigated by S5c composite test + 5 cross-layer composition tests + A-class halt A11) |
| **Severity** | MEDIUM |
| **Description** | DEC-390 L3 ceiling uses TWO-COUNTER reservation pattern (`cumulative_pending_sell_shares + cumulative_sold_shares ≤ shares_total`) per Round-1 C-1. **Synchronous-update invariant extended per Phase A Tier 3 item A + B / FAI entry #9 / DEF-FAI-CALLBACK-ATOMICITY** to all bookkeeping callback paths (place-side, cancel/reject decrement, partial-fill transfer, full-fill transfer, ceiling multi-attribute read). Edge cases: (a) broker fill callback arrives out-of-order, (b) partial-fill granularity differs between SimulatedBroker and IBKR, (c) `cumulative_pending_sell_shares` not decremented correctly on cancel/reject (would cause counter to drift upward over session), (d) the C-1 race scenario fires unexpectedly (two coroutines both pass ceiling because reservation didn't hold synchronously before `await`), (e) **NEW: any callback path beyond `_reserve_pending_or_fail` violates the synchronous-update invariant** (e.g., partial-fill transfer yields between `pending -= filled_qty` and `sold += filled_qty`, allowing another coroutine's ceiling check to see artificially-low total). Either could produce off-by-one transient state. |
| **Mitigation** | (a) AC3.1 enumerates all 5 state transitions explicitly; reviewer must verify each. (b) AC3.5 race test (`test_concurrent_sell_emit_race_blocked_by_pending_reservation`) is the canonical regression. (c) **NEW per S4a-ii: AST-no-await scan + mocked-await injection regression test applied to ALL bookkeeping callback paths** (`on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling`'s multi-attribute read) per DEF-FAI-CALLBACK-ATOMICITY. (d) **NEW per S4a-ii: reflective-pattern coverage** per Decision 3 / DEF-FAI-8-OPTION-A — `**kw` unpacking, computed-value flag assignment, `getattr` reflective access. (e) S5b composite stresses 5+ SELL emit sites with parametrized partial-fill scenarios. (f) **NEW per S5c: 5 cross-layer composition tests CL-1 through CL-5** prove that single-layer failure is caught by another layer. (g) A-class halt A11 fires on any false-positive observed in production paper trading; default disposition (per A11): audit which state transition leaked/under-decremented. (h) Reviewer mandate at S4a-ii: inspect diff for synchronous-before-await ordering on EVERY bookkeeping path; this is the architectural correctness contract. |
| **Trigger conditions** | (1) Production paper-session shows a legitimate SELL refused due to pending+sold+requested arithmetic. (2) Pending counter observed drifting upward over session (suggests cancel/reject path under-decrement). (3) Race test failure in CI. (4) Any paper-session phantom short traceable to a coroutine pair where both passed the ceiling check. (5) **NEW: AST-no-await scan regression on any bookkeeping callback path.** (6) **NEW: cross-layer composition test (CL-1 through CL-5) failure.** |
| **Cross-References** | DEC-390 L3; AC3.1 (state transitions, all 5); AC3.5 (race test); AC3.10 (extended synchronous-update invariant scope per Tier 3 item A + B); regression invariants 13 + 20 + 23 + 27; A-class halt A11; SbC §"Edge Cases to Reject" #1 (replaced from Round-1 wrong framing; revised in Phase B re-run). |
```

#### C8.5. RSK-RECONSTRUCTED-POSITION-DEGRADATION (REVISED per Round-2 H-R2-3 severity calibration; time-bounded by Sprint 31.94 D3)

```markdown
### RSK-RECONSTRUCTED-POSITION-DEGRADATION | `is_reconstructed=True` Refusal Posture Operational Cost

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN; **TIME-BOUNDED by Sprint 31.94 D3 seal** (boot-time adoption-vs-flatten policy retires the conservative posture) |
| **Severity** | **MEDIUM-HIGH** (rated per Severity Calibration Rubric per Sprint 31.92 design summary; operator daily-flatten empirically failed Apr 28 with 27 of 87 ORPHAN-SHORT detections from a missed run; closes structural restart-safety hole but with documented operational degradation) |
| **Description** | DEC-390 L3's `ManagedPosition.is_reconstructed: bool` flag (set `True` in `reconstruct_from_broker`) causes the ceiling check to refuse ALL ARGUS-emitted SELLs on reconstructed positions. This is a CONSERVATIVE posture chosen at Round-1 disposition C-2 (over the reviewer's proposed alternatives of reading `data/argus.db` trades table OR persisting counters to SQLite — both rejected as fragile/scope-violating). Operational consequence: until Sprint 31.94 D3 lands, reconstructed positions can ONLY be closed via `scripts/ibkr_close_all_positions.py` (operator manual, bypasses OrderManager). EOD flatten and time-stop paths on reconstructed positions are blocked. **2026-04-28 paper-session debrief evidence:** 27 of 87 ORPHAN-SHORT detections originated from a missed daily-flatten run, demonstrating that the operator-flatten mitigation has empirically failed at least once during the Sprint 31.91 → 31.92 transition window. **Sprint Abort Condition #7 trigger lowered from 4 weeks to 2 weeks** per Round-2 H-R2-3 severity calibration. |
| **Mitigation** | (a) `_startup_flatten_disabled` (IMPROMPTU-04) already blocks reconstruction entirely on most non-clean broker states, so the actual operational surface is small. (b) Operator daily-flatten script `scripts/ibkr_close_all_positions.py` is the structurally-acknowledged closing mechanism (acknowledged-as-empirically-fallible). (c) Sprint 31.94 D3's policy decision (boot-time adoption-vs-flatten policy) is sprint-gating for Sprint 31.94 itself — cannot be sealed without D3. (d) A-class halts A15 + A16 fire on any leak (SELL emitted on `is_reconstructed=True` position) OR sustained operational degradation (operator-manual flatten cannot keep up). (e) Sprint Abort Condition #7 covers the case where Sprint 31.94 D3 slips by >2 weeks. (f) **NEW per S5c: CL-2 cross-layer composition test** (L4 fails → L2 catches) provides defense-in-depth independent of `is_reconstructed` posture. |
| **Trigger conditions** | (1) Test failure: `test_restart_during_active_position_refuses_argus_sells` fails. (2) Production: any ARGUS-emitted SELL on `is_reconstructed=True` position (A15 fires). (3) Production: reconstructed positions accumulate AND operator daily-flatten cannot keep up (A16 fires). (4) Sprint 31.94 D3 ETA slips >2 weeks past Sprint 31.92 seal date (Sprint Abort Condition #7 fires; lowered from 4 weeks per Round-2 severity calibration). (5) Any second missed-run incident before Sprint 31.94 seal. |
| **Cross-References** | DEC-390 L3; AC3.6 (initialization); AC3.7 (refusal posture); AC5.4 (restart validation); regression invariant 19; A-class halts A15 + A16; Sprint Abort Condition #7 (lowered to 2 weeks); DEF-211 D3 (Sprint 31.94 sprint-gating); SbC §"Out of Scope" #5; `scripts/ibkr_close_all_positions.py` (operator-manual closing mechanism); `docs/debriefs/2026-04-28-paper-session-debrief.md` (empirical evidence of missed-run incident). |
```

#### C8.6. RSK-SUPPRESSION-LEAK (UNCONDITIONAL; PARTIALLY MITIGATED per Round-1 H-3 + Phase A Tier 3 item C Branch 4)

```markdown
### RSK-SUPPRESSION-LEAK | Locate-Suppression Dict GC Bound + Reconnect Blindness

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN (partially mitigated by AC2.5 broker-verification + Branch 4 + HALT-ENTRY coupling; full coupling deferred to Sprint 31.94) |
| **Severity** | LOW (operational; structural mitigation in place) |
| **Description** | DEC-390 L2's `OrderManager._locate_suppressed_until: dict[ULID, float]` accumulates entries; cleared on (a) fill callback for the position, (b) position close, (c) suppression-window timeout fallback per AC2.5. Mid-session IBKR Gateway reconnect would leave stale entries in the dict until the timeout fires (default 18000s = 5hr). AC2.5's broker-verification-at-timeout (Round-1 H-3) eliminates the false-positive alert class even when stale dict entries persist post-reconnect: when timeout fires, broker is queried for actual position state via the new `Broker.refresh_positions()` ABC method and (if expected-long observed) alert is suppressed and dict entry cleared. **Branch 4 per Phase A Tier 3 item C** covers refresh-failure case: alert published with `verification_stale: true` metadata flag; **HALT-ENTRY coupling** under H1 + refresh-fail blocks subsequent SELLs and demands operator resolution. Stale dict entries during the suppression window cause additional SELLs at the same `ManagedPosition` to be skipped — for the suppression-window duration, this is conservative-but-correct (the position will close via subsequent flatten-resubmit timeout via DEF-158's retry path, OR via the suppression-timeout broker-verification fallback). |
| **Mitigation** | (a) Existing OrderManager EOD teardown clears the dict (no inter-session leak). (b) Suppression-timeout fallback per AC2.5 with broker-verification clears stale entries on a per-position basis. (c) **NEW: Branch 4 per Phase A Tier 3 item C** ensures refresh-failure case still surfaces alert with `verification_stale: true` metadata. (d) **NEW: HALT-ENTRY coupling under H1 + refresh-fail** prevents compounding failure modes. (e) Sprint 31.94 will couple `IBKRReconnectedEvent` consumer to dict-clear when the producer lands. (f) S5b stress test asserts dict cleared at session-end. (g) `OrderManager._locate_suppressed_until` is bounded by `len(active_managed_positions)` — never grows unboundedly. |
| **Trigger conditions** | (1) S5b stress-test fails: dict not cleared at session-end. (2) Production: paper session reveals dict size growing across the session beyond reasonable ManagedPosition cardinality. (3) Production: stale dict entry causes a legitimate position's SELL to be skipped during suppression window AND broker-verification at timeout incorrectly classifies state. (4) **Branch 4 firing in production** (operator-triage signal — `verification_stale: true` alerts indicate refresh-failure events). |
| **Cross-References** | DEC-390 L2; AC2.2 (position-keyed suppression); AC2.5 (broker-verification at timeout, three branches + Branch 4); regression invariants 14 + 21 + 25; B-class halt B12 (broker-verification failure); Sprint 31.94 reconnect-recovery (full coupling). |
```

#### C8.7. RSK-FAI-COMPLETENESS (NEW per Phase A Tier 3)

```markdown
### RSK-FAI-COMPLETENESS | Falsifiable-Assumption Inventory First-Pass Miss Pattern

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN; mitigation in-sprint + bounded by Round 3 cycle |
| **Severity** | **MEDIUM** (per Phase A Tier 3 verdict; mitigation in-sprint via Phase B/C re-run + Round 3 full-scope cross-check) |
| **Description** | The 2026-04-29 protocol amendments (`templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory + § Hypothesis Prescription) installed the FAI as the structural defense against primitive-semantics misses. The defense itself missed an entry (callback-path bookkeeping atomicity / FAI entry #9) on first authoring during Phase A re-entry. The FAI's self-falsifiability clause fired at Phase A Tier 3, making the miss DETECTABLE before Round 3 review. **Three FAI-class primitive-semantics misses have now occurred:** Round 1 (asyncio yield-gap, dispositioned as C-1), Round 2 (`ib_async` cache freshness, dispositioned as C-R2-1), Phase A Tier 3 (callback-side state-transition atomicity, dispositioned as entry #9 / DEF-FAI-CALLBACK-ATOMICITY). The pattern of recurring first-pass FAI misses suggests Round 3 may surface a fourth. The FAI's self-falsifiability clause + Round 3's full-scope cross-check are the structural defenses; if Round 3 surfaces a Critical, **Outcome C re-fires** triggering another revision pass per Decision 7 (operator pre-commitment). |
| **Mitigation** | (a) Phase B/C re-run (this revision pass) materialized FAI entry #9 + extended H-R2-1 protection scope per Tier 3 verdict. (b) Round 3 full-scope cross-check is mandatory per Outcome C; FAI cross-check is explicit per `adversarial-review-input-package-round-3.md`. (c) **Decision 7 operator pre-commitment** binds Round 3 outcome: foundational primitive-semantics miss → another revision pass; any other Critical class → accept-as-known-limitation + RSK at appropriate severity. The pre-commitment is auditable (written before Round 3 runs). (d) Process-evolution lesson F.6 captures the pattern for next campaign's RETRO-FOLD candidates. (e) Three-outcome state machine in `protocols/adversarial-review.md` v1.1.0 routes Round 3 verdict deterministically. |
| **Trigger conditions** | (1) Round 3 produces a Critical finding of the FAI's primitive-semantics class (asyncio, ib_async, callback-path, or sibling). (2) Mid-sprint Tier 3 (M-R2-5) surfaces a new FAI-class miss. (3) Production paper trading reveals a primitive-semantics gap not in the inventory (post-seal). (4) Sprint 31.93 + 31.94 review cycles surface an FAI-class miss in inherited follow-up scope. |
| **Cross-References** | Phase A Tier 3 verdict (`tier-3-review-1-verdict.md`); FAI inventory (`falsifiable-assumption-inventory.md` — 9 entries with self-falsifiability clause); Decision 7 (Round 3 escalation pre-commitment, verbatim in `escalation-criteria.md`); `templates/sprint-spec.md` v1.2.0 § FAI; `protocols/adversarial-review.md` v1.1.0 § Outcome C; process-evolution lesson F.6; DEF-FAI-CALLBACK-ATOMICITY; DEF-FAI-N-INCREASE; DEF-FAI-2-SCOPE; DEF-FAI-8-OPTION-A. |
```

#### C8.8. RSK-CROSS-LAYER-INCOMPLETENESS (NEW per Phase A Tier 3)

```markdown
### RSK-CROSS-LAYER-INCOMPLETENESS | Cross-Layer Composition Test Coverage at 5 (CL-6 Deferred)

| Field | Value |
|-------|-------|
| **Sprint** | 31.92 |
| **Status** | OPEN; mitigated by 5-test commitment (above template floor); CL-6 explicitly deferred per Decision 5 |
| **Severity** | **MEDIUM** (per Phase A Tier 3 verdict; DEC-386's empirical falsification on 2026-04-28 justifies heightened bar; CL-6 deferral documented with rationale per process-evolution lesson F.7) |
| **Description** | DEC-390's 4-layer composition activates `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests (mandatory when DEC entries claim N≥3 layer defense). Phase A Tier 3 verdict required ≥4 cross-layer tests (above template floor of "at least one"). **Sprint 31.92 commits to 5 tests:** CL-1 (L1 fails → L3 catches), CL-2 (L4 fails → L2 catches), CL-3 (FAI #2 + FAI #5 cross-falsification → HALT-ENTRY catches), CL-4 (L1 + L2 → L3 catches), CL-5 (L2 + L3 → protective stop-replacement allowed AND Branch 4 doesn't false-fire). **CL-6 (rollback + locate-suppression interaction) is explicitly OUT of scope per Decision 5** — cross-layer between L4 rollback and L2 suppression dict is judged lower-priority than the chosen 5 because: (a) L4 rollback is binary (config-gated); (b) the dual-channel AC4.6 + AC4.7 `--allow-rollback` CLI gate make rollback an explicit operator action, not a silent failure; (c) the budget for S5c is bounded by compaction risk. Risk: a cross-layer failure mode at the L4↔L2 interaction is theoretically possible but judged operator-detectable (rollback is loud per AC4.6/AC4.7) and structurally bounded (dict-keying by ULID per Round-1 H-2 prevents cross-position contamination). |
| **Mitigation** | (a) 5 cross-layer tests committed at S5c (above Tier 3 floor of 4; above template floor of 1). (b) `SimulatedBrokerWithRefreshTimeout` test fixture (DEF-SIM-BROKER-TIMEOUT-FIXTURE) enables in-process Branch 4 testing for CL-3 + CL-5. (c) CL-6 deferral rationale captured in process-evolution lesson F.7 + SbC §"Out of Scope" #6. (d) Cessation criterion #5 (5 paper sessions clean post-seal) is the ultimate cross-layer composition test (production traffic). (e) Round 3 reviewer's FAI cross-check explicitly covers cross-layer composition test count + CL-6 deferral rationale. |
| **Trigger conditions** | (1) Production paper-session reveals a cross-layer failure mode at the L4↔L2 interaction (CL-6 surface). (2) Round 3 verdict requires CL-6 implementation (Outcome C re-fires; Decision 7 (b) class). (3) Mid-sprint Tier 3 (M-R2-5) surfaces a new cross-layer composition gap. (4) Sprint 31.94 reconnect-recovery surfaces an L2↔reconnect-event cross-layer interaction. |
| **Cross-References** | Phase A Tier 3 verdict (`tier-3-review-1-verdict.md`); Decision 5 (5 cross-layer tests + CL-6 deferral); SbC §"Out of Scope" #6; regression invariant 27; process-evolution lesson F.7; `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests; DEF-CROSS-LAYER-EXPANSION; DEF-SIM-BROKER-TIMEOUT-FIXTURE. |
```

### C9. docs/pre-live-transition-checklist.md — Add Sprint 31.92 gate criteria + new runtime-state recording

**Anchor:** Append a new subsection under §"Sprint 31.91 + 31.92 Gates" (rename
from existing "Sprint 31.91 Gates" if needed).

**Patch (additive, after the existing Sprint 31.91 gate criteria block):**

```markdown
#### Sprint 31.92 Gate Criteria

Before considering live trading transition post-Sprint-31.92:

1. **DEF-204 RESOLVED status reached** — i.e., RESOLVED-PENDING-PAPER-VALIDATION transitions to RESOLVED only after cessation criterion #5 (5 paper sessions clean post-Sprint-31.92 seal) is satisfied.
2. **DEF-212 RESOLVED status reached** — i.e., `_OCA_TYPE_BRACKET` constant deleted from `argus/execution/order_manager.py`; grep regression guard green; `OrderManager.__init__` accepts `bracket_oca_type: int`; `argus/main.py` construction site updated.
3. **All 4 spike + validation artifacts under `scripts/spike-results/` are committed and ≤30 days old**:
   - `spike-def204-round2-path1-results.json` (S1a; status=PROCEED; expanded with adversarial axes per Decision 1 + N=100 propagation atomicity per Decision 2)
   - `spike-def204-round2-path2-results.json` (S1b; status=PROCEED; hard-to-borrow microcap measurements per Round-1 M-1)
   - `sprint-31.92-validation-path1.json` (S5a; `path1_safe: true`)
   - `sprint-31.92-validation-path2.json` (S5b; `path2_suppression_works: true`; `broker_verification_at_timeout_works: true`; `branch_4_verification_stale_works: true` per Phase A Tier 3 item C)
4. **Composite Pytest test green and JSON artifact ≤24 hours old** — `tests/integration/test_def204_round2_validation.py::test_composite_validation_zero_phantom_shorts_under_load` passes; `scripts/spike-results/sprint-31.92-validation-composite.json` updated by daily CI workflow within last 24 hours.
5. **Restart-scenario test green** — `tests/integration/test_def204_round2_validation.py::test_restart_during_active_position_refuses_argus_sells` passes (regression invariant 19).
6. **5 cross-layer composition tests green** — CL-1, CL-2, CL-3, CL-4, CL-5 all pass at S5c per regression invariant 27 + Decision 5 / DEF-CROSS-LAYER-EXPANSION.
7. **Synchronous-update invariant regression test green on all bookkeeping callback paths** — AST-no-await scan + mocked-await injection regression test pass on `_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, and `_check_sell_ceiling`'s multi-attribute read per regression invariant 23 + DEF-FAI-CALLBACK-ATOMICITY. Reflective-pattern coverage tests pass per Decision 3 / DEF-FAI-8-OPTION-A.
8. **Branch 4 + HALT-ENTRY coupling test green** — `test_refresh_positions_timeout_publishes_verification_stale_alert` passes; `test_h1_active_plus_refresh_fail_marks_halt_entry_until_operator_ack` passes per regression invariants 24 + 25.
9. **AC2.7 watchdog runtime state recorded** — `pending_sell_age_watchdog_enabled` field's runtime state (`auto` / `enabled` / `disabled`) logged at startup AND on every state transition. **Operator audit:** confirm runtime state at first paper-session-clean post-seal — if state has flipped from `auto` → `enabled` automatically, that is the structural fallback firing on a `case_a_in_production` event (per Decision 4); investigate the underlying locate-rejection variant before live transition. State must be operator-acknowledged in the live-transition runbook.
10. **Path #1 mechanism re-spike** before live transition (DEC-386's `PATH_1_SAFE` discipline mirror) — operator runs `scripts/spike_def204_round2_path1.py` against current paper IBKR + current `ib_async` version; verifies S1a-recorded mechanism (H2 amend / H4 hybrid / H1 cancel-and-await) still operates within measurement bounds; verifies adversarial axes per Decision 1 still pass; verifies N=100 propagation atomicity per Decision 2 still passes (zero-conflict-stress hard gate per H-R2-2-tightened).
11. **Path #2 fingerprint re-validation** — operator runs `scripts/spike_def204_round2_path2.py` against current paper IBKR with operator-curated hard-to-borrow microcap list; verifies fingerprint string still matches; verifies suppression-window p99 measurement still within Pydantic field validator bounds [300, 86400] seconds.
12. **`bracket_oca_type=1` verified in live config** — emergency rollback escape hatch confirmed inactive (AC4.6 dual-channel CRITICAL warning would fire if `!= 1`; verify warning ABSENT in startup logs; verify `--allow-rollback` flag NOT passed in launchctl/systemd unit per AC4.7 — startup exit-code-2 prevents accidental rollback).
13. **`is_reconstructed` refusal posture documented in operator runbook** — operator aware that reconstructed positions can only be closed via `scripts/ibkr_close_all_positions.py` until Sprint 31.94 D3 lands; daily-flatten infrastructure verified operational; **acknowledge empirical failure of operator-flatten on 2026-04-28 (27 of 87 ORPHAN-SHORT detections from missed run)** and document at-most-2-weeks tolerance for Sprint 31.94 D3 ETA per Sprint Abort Condition #7 (lowered from 4 weeks per Round-2 H-R2-3 severity calibration).
14. **`Broker.refresh_positions()` ABC method documented in operator runbook** — operator aware that AC2.5 broker-verification-at-timeout uses this new method; Branch 4 (`verification_stale: true`) alerts indicate refresh-failure events and require operator-triage; HALT-ENTRY coupling under H1 + refresh-fail demands operator-driven resolution.
15. **Daily CI workflow for composite test verified live** — workflow file present in `.github/workflows/` (or equivalent); workflow execution history shows ≥7 consecutive daily green runs before live transition consideration.
16. **No outstanding A-class halt triggers** from Sprint 31.92 escalation criteria (especially A11, A15, A16, B12, plus NEW A-class triggers added per Decision 4 / Tier 3 item A / Tier 3 item C composite for synchronous-update invariant violation, Branch 4 + H1 active without HALT-ENTRY firing, AC2.7 `auto`-mode watchdog activation event).
17. **DEC-390 entry written** in `docs/decision-log.md` with all 4 layers, complete cross-references, structural-closure framing (NO aggregate percentage claims per process-evolution lesson F.5), and explicit reference to all Tier 3 items A–E + 7 settled operator decisions.
18. **Process-evolution lessons F.6 (FAI completeness) + F.7 (CL-6 deferral) materialized** in `docs/process-evolution.md`.
19. **Round 3 verdict materialized** in `docs/sprints/sprint-31.92-def204-round-2/`; if Round 3 surfaced a Critical of the FAI's primitive-semantics class, Decision 7 (a) operator pre-commitment fired (another revision pass) and the live-transition gate is suspended pending the new revision pass; otherwise Decision 7 (b) (any other Critical class accepted as known limitation + RSK at appropriate severity).
```

### C10. process-evolution.md — Lesson F.5 (preserved) + Lesson F.6 (NEW) + Lesson F.7 (NEW)

**Anchor:** Append after existing lessons F.1–F.4 in `docs/process-evolution.md`
(file is workflow-metarepo-mirrored; Sprint 31.92 sprint-close fold-in).

**Patch (additive — three lessons; F.5 preserved verbatim from Round-1; F.6 +
F.7 are NEW per Phase B re-run + Phase A Tier 3 verdict):**

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

---

### F.6 — FAI Completeness Pattern: Structural Defense Itself Is Subject to First-Pass Miss (Sprint 31.92 origin, 2026-04-29)

**Context:** Sprint 31.92 began with Round 1 adversarial review, which surfaced 3 Critical findings (asyncio yield-gap race in ceiling, restart-safety hole for reconstructed positions, H1 cancel-and-await reintroduces AMD-2's closed gap). All 3 were dispositioned. Round 2 adversarial review (against the revised plan) surfaced 1 Critical (C-R2-1: refresh-fail Branch 4 missing for AC2.5 broker-verification — a sibling-class miss to Round 1's asyncio yield-gap because both are primitive-semantics gaps in the asyncio / `ib_async` interaction layer). A14 fired (Round 2 produced Critical of FAI's primitive-semantics class) triggering Phase A re-entry per `protocols/adversarial-review.md` v1.1.0 § Outcome C.

**Phase A re-entry authored an 8-entry Falsifiable Assumption Inventory (FAI)** per the 2026-04-29 amendments to `templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory + § Hypothesis Prescription. The 2026-04-29 amendments installed the FAI as the structural defense against primitive-semantics misses — the explicit goal was to make assumption surfaces inventory-able and falsifiable BEFORE Round 3 review or production deployment.

**Phase A Tier 3 review fired the FAI's self-falsifiability clause.** The FAI itself was missing entry #9 (callback-path bookkeeping atomicity): all bookkeeping update paths on `cumulative_pending_sell_shares` and `cumulative_sold_shares` (place-side, cancel/reject decrement, partial-fill transfer, full-fill transfer, ceiling multi-attribute read) execute synchronously between read and write across the entire transition. Round-1 C-1's atomic `_reserve_pending_or_fail` pattern was the reference implementation, but the AST-no-await guard + mocked-await injection regression was scoped narrowly — the same guard needs to apply to every callback path that mutates the bookkeeping counters. The miss was a sibling-class to Round 1's and Round 2's misses (a primitive-semantics gap in the asyncio single-event-loop guarantee scope).

**Three FAI-class primitive-semantics misses have now occurred in Sprint 31.92:** Round 1 (asyncio yield-gap), Round 2 (`ib_async` cache freshness), Phase A Tier 3 (callback-path bookkeeping atomicity).

**Lesson:** **The structural defense (FAI authoring) is itself subject to first-pass miss; the protocol catches scale (multiple successive review tiers); each tier catches what the prior tier missed.** Specifically:

- ❌ **Anti-pattern (overconfident):** "We installed the FAI structural defense; we are now safe from primitive-semantics misses."
- ✅ **Pattern (multi-layer defense, with each layer expected to leak):** "We installed the FAI as the first structural defense; Phase A Tier 3 catches what spec-author misses; Round 3 full-scope cross-check catches what Phase A Tier 3 misses; production paper-session catches what Round 3 misses; cessation criterion #5 (5 paper sessions clean) is the ultimate validation."

**Why this matters:**

1. **No single review tier is sufficient.** Round 1 is per-author-spec-time; Round 2 is per-revision-time; Phase A Tier 3 is per-FAI-authoring-time; Round 3 is full-scope cross-check; mid-sprint Tier 3 (M-R2-5) is per-implementation-time; production paper-session is per-real-traffic-time. Each tier has a different perspective and catches different misses. Removing any tier compromises the defense in depth.

2. **The FAI is a defense-in-depth layer, not a silver bullet.** Round 1 caught one primitive-semantics miss; Round 2 caught a sibling; Phase A Tier 3 caught a third. The FAI's value isn't that it prevents misses — it's that it MAKES THEM DETECTABLE earlier in the cycle (Phase A Tier 3 vs production paper-session). Cost-of-detection escalates with each tier missed.

3. **Process-evolution incentive:** Spec-authors have implicit pressure to declare the FAI "complete" once authored. The self-falsifiability clause in `templates/sprint-spec.md` v1.2.0 explicitly guards against this — the FAI is provisional until Phase A Tier 3 + Round 3 cross-checks pass. Author should EXPECT misses and design the inventory to make them surface, not hide them.

4. **Round 3 full-scope cross-check is the next defense layer.** Per Outcome C, Round 3 proceeds at full scope (not narrowed) when Phase A re-entry + Phase A Tier 3 produce REVISE_PLAN. The FAI cross-check is mandatory at Round 3 per `adversarial-review-input-package-round-3.md`. Decision 7 operator pre-commitment (verbatim in `escalation-criteria.md`) bounds the worst-case revision pass count to one more: foundational primitive-semantics miss → another revision pass; any other Critical class → accept-as-known-limitation + RSK at appropriate severity.

**Operational application:**

- **`templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory** already includes the self-falsifiability clause (added at 2026-04-29 amendments). Lesson F.6 reinforces that the clause is LOAD-BEARING, not ceremonial — Phase A Tier 3 reviewers must actually probe whether the inventory has been falsified.

- **`protocols/adversarial-review.md` v1.1.0 § Probing Sequence** Step 1 ("Falsifiable assumptions inventory completeness") should explicitly include: "Does the inventory enumerate ALL primitive-semantics surfaces touched by the design, including sibling-class surfaces to known historical misses (asyncio yield-gap, ib_async cache freshness, callback-path bookkeeping atomicity)? If a sibling-class surface is touched but not in the inventory, the inventory has failed."

- **`protocols/tier-3-review.md` v1.1.0 § Phase A Tier 3 trigger #5** ("Adversarial review N≥2 with Critical-of-FAI-class") should explicitly route to Outcome C re-fire if Round 3 surfaces a Critical of FAI's primitive-semantics class. Decision 7 operator pre-commitment formalizes this.

- **Workflow metarepo RETRO-FOLD candidates:** at next campaign, fold the lesson F.6 framing into all three protocol files. NOT applied in-line at Sprint 31.92's sprint-close (cross-repo scope).

**Sprint 31.92 application:** Phase A Tier 3 verdict identified entry #9 + extended H-R2-1 protection scope before Round 3 ran. Phase B re-run + Phase C re-revision incorporated the missing entry + Tier 3 items A–E. Round 3 input package declares full scope per Outcome C (not narrowed) and includes the FAI cross-check explicitly. Decision 7 operator pre-commitment is verbatim in `escalation-criteria.md` for Round 3 reviewer's binding context.

**Cross-references:** RSK-FAI-COMPLETENESS (NEW per Phase A Tier 3); FAI inventory (`falsifiable-assumption-inventory.md` — 9 entries with self-falsifiability clause); Phase A Tier 3 verdict (`tier-3-review-1-verdict.md`); Decision 7 (Round 3 escalation pre-commitment, verbatim in `escalation-criteria.md`); 2026-04-28 paper-session debrief (the proximal trigger for Sprint 31.92 + the 2026-04-29 amendments + this Tier 3); `templates/sprint-spec.md` v1.2.0 § Falsifiable Assumption Inventory; `protocols/adversarial-review.md` v1.1.0 § Outcome C; `protocols/tier-3-review.md` v1.1.0; DEF-FAI-CALLBACK-ATOMICITY; DEF-FAI-N-INCREASE; DEF-FAI-2-SCOPE; DEF-FAI-8-OPTION-A.

**Capture notes:** Lesson F.6 captured in process-evolution.md at Sprint 31.92 sprint-close. Workflow-metarepo amendments to `protocols/adversarial-review.md` § Probing Sequence Step 1 + `protocols/tier-3-review.md` Phase A Tier 3 trigger #5 routing are RETRO-FOLD candidates for the next campaign — NOT applied in-line at Sprint 31.92's sprint-close.

---

### F.7 — Cross-Layer Composition Test Scope-Shaping: CL-6 Deferral Rationale (Sprint 31.92 origin, 2026-04-29)

**Context:** DEC-390's 4-layer composition (L1 Path #1 mechanism / L2 Path #2 + suppression + broker-verified timeout / L3 ceiling + reconstructed-position refusal / L4 DEF-212 wiring) activates `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests (mandatory when DEC entries claim N≥3 layer defense). Phase A Tier 3 verdict (operator decision 5) required ≥4 cross-layer tests (above template floor of "at least one"). Phase B re-run + Phase C re-revision committed to **5 cross-layer composition tests** (above Tier 3 floor): CL-1 (L1 fails → L3 catches), CL-2 (L4 fails → L2 catches), CL-3 (FAI #2 + FAI #5 cross-falsification → HALT-ENTRY catches), CL-4 (L1 + L2 → L3 catches), CL-5 (L2 + L3 → protective stop-replacement allowed AND Branch 4 doesn't false-fire).

**CL-6 (rollback + locate-suppression interaction) was identified as a candidate sixth test** but explicitly deferred per Decision 5. The reasoning:

1. **L4 rollback is binary (config-gated).** When `bracket_oca_type=0`, OCA enforcement is OFF for bracket children; when `=1`, OCA enforcement is ON. There is no in-between state, so the cross-layer interaction is two scenarios, not a continuous surface.

2. **AC4.6 dual-channel CRITICAL warning + AC4.7 `--allow-rollback` CLI gate make rollback an explicit operator action, not a silent failure.** ntfy.sh `system_warning` AND canonical-logger CRITICAL fire at startup if `bracket_oca_type != 1`. ARGUS exits with code 2 if `--allow-rollback` flag absent. Operators cannot accidentally rollback; the act is loud, audit-trailed, and defense-in-depth.

3. **Cross-position contamination is structurally bounded.** L2's suppression dict is keyed by `ManagedPosition.id` ULID (per Round-1 H-2), not by symbol. Even if rollback ON + locate-suppression interaction produced an unmodeled state, the suppression scope is per-position, not per-symbol — preventing fan-out across the active universe.

4. **Compaction-risk budget for S5c is bounded.** S5c already includes 5 cross-layer tests + `SimulatedBrokerWithRefreshTimeout` test fixture. Adding a 6th cross-layer test would push S5c's compaction risk score above threshold (the session as scoped is Medium 13.5; adding CL-6 would push it to High 14.5+), requiring a session split. The operational cost of split exceeds the marginal coverage gain because of (1) + (2) + (3).

**Lesson:** **Cross-layer composition tests are scope-shapeable; the test count should reflect coverage value vs compaction-risk cost. Sprint 31.92 commits to 5 (above template floor + above Tier 3 floor) with CL-6 deferred and rationale documented.** Specifically:

- ❌ **Anti-pattern:** "Test all N×N layer interaction pairs" (combinatorial explosion; compaction-risk overflow; diminishing marginal value).
- ✅ **Pattern:** "Identify cross-layer tests where (a) the failure-mode-of-one-layer is plausible AND (b) the next-layer-catch is the load-bearing safety property AND (c) the test is implementable within session compaction-risk budget. Defer cross-layer tests where any of these conditions fails, with documented rationale."

**Why this matters:**

1. **Cross-layer test coverage is not exhaustive by design.** DEC-386's empirical falsification (60 phantom shorts via cross-layer composition path) justifies a HEIGHTENED bar (5 tests > template floor of 1). But "heightened" is not "exhaustive" — the test count should reflect the highest-value cross-layer pairs.

2. **Rationale-documented deferrals are structurally sound; silent deferrals are not.** CL-6 deferred per Decision 5 with rationale captured here AND in SbC §"Out of Scope" #6. If a cross-layer failure mode at the L4↔L2 interaction surfaces in production, the deferral rationale is auditable — operator can re-evaluate (1) + (2) + (3) in light of the new evidence.

3. **Compaction-risk-driven scope-shaping is a legitimate planning constraint.** Pushing a session above compaction-risk threshold compromises the session itself (longer context, more tool calls, higher error rate). Splitting sessions adds coordination overhead. The 5-test commitment + CL-6 deferral is the compaction-risk-bounded choice.

**Operational application:**

- **`templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests** already specifies "at least one" floor; the lesson reinforces that the count should be scope-shaped, not maximized.

- **`protocols/sprint-planning.md` v1.3.0 § Phase A step 8** (compaction-risk re-validation) implicitly governs cross-layer test count via the compaction-risk threshold. Sprint 31.92's S5c at Medium 13.5 with 5 tests is the empirical example.

- **Round 3 reviewer's FAI cross-check** explicitly covers cross-layer composition test count + CL-6 deferral rationale (per `adversarial-review-input-package-round-3.md`).

**Sprint 31.92 application:** SbC §"Out of Scope" #6 explicitly lists CL-6 with rationale. RSK-CROSS-LAYER-INCOMPLETENESS captures the residual risk + trigger conditions. AC6.4 (if applicable) mandates the structural-closure framing for cross-layer test count. Cessation criterion #5 (5 paper sessions clean post-seal) is the ultimate cross-layer composition test (production traffic).

**Cross-references:** RSK-CROSS-LAYER-INCOMPLETENESS (NEW per Phase A Tier 3); Decision 5 (5 cross-layer tests + CL-6 deferral); SbC §"Out of Scope" #6; regression invariant 27; `templates/sprint-spec.md` v1.2.0 § Defense-in-Depth Cross-Layer Composition Tests; DEF-CROSS-LAYER-EXPANSION; DEF-SIM-BROKER-TIMEOUT-FIXTURE; `adversarial-review-input-package-round-3.md` § Round 3 reviewer's FAI-specific tasks.

**Capture notes:** Lesson F.7 captured in process-evolution.md at Sprint 31.92 sprint-close. Workflow-metarepo amendments to `templates/sprint-spec.md` § Defense-in-Depth Cross-Layer Composition Tests (scope-shaping guidance) are RETRO-FOLD candidates for the next campaign — NOT applied in-line at Sprint 31.92's sprint-close.
```

---

## Phase D — Sprint Cessation Tracker

After Sprint 31.92 seals, the following tracker is added to `CLAUDE.md` under
§"Active Sprint" → §"Cessation Criteria" (replacing Sprint 31.91's entry):

```markdown
### Cessation Criteria — DEF-204 (Post-Sprint-31.92)

DEF-204 transitions from RESOLVED-PENDING-PAPER-VALIDATION to RESOLVED when ALL of the following are satisfied:

1. ✅ Sprint 31.91 sealed (cumulative — 2026-04-28).
2. ✅ Sprint 31.92 sealed ({SPRINT_CLOSE_DATE}).
3. ✅ Sprint 31.92 spike artifacts + validation artifacts committed to `main` and ≤30 days old (4 spike+validation JSONs + 1 composite Pytest-side-effect artifact + 5 cross-layer composition tests).
4. ✅ DEC-390 written below in `docs/decision-log.md` with structural-closure framing per F.5 + explicit reference to Tier 3 items A–E + 7 settled operator decisions + lessons F.6 + F.7.
5. ⏸️ **5 paper sessions clean post-Sprint-31.92 seal** — counter starts at 0/5 on {SPRINT_CLOSE_DATE}. "Clean" defined: (a) zero NEW phantom shorts; (b) zero `phantom_short_retry_blocked` alerts attributable to false-positive (i.e., AC2.5 broker-verification correctly suppressed alerts during reconnects); (c) zero `sell_ceiling_violation` alerts unless attributable to a known operator-side trigger; (d) zero ARGUS-emitted SELLs on `is_reconstructed=True` positions (regression invariant 19); (e) operator daily-flatten executed successfully (no missed-run incidents — per 2026-04-28 empirical evidence, this is fallible); (f) zero Branch 4 `verification_stale: true` alerts firing without operator-acknowledged underlying refresh-failure event (per regression invariant 25); (g) AC2.7 watchdog in `auto` state (NOT auto-flipped to `enabled` — that would indicate a `case_a_in_production` event per regression invariant 26).
6. ⏸️ Sprint 31.94 sealed (eliminates RSK-RECONSTRUCTED-POSITION-DEGRADATION via D3 boot-time policy + addresses DEF-FAI-2-SCOPE high-volume axis).

Operator daily-flatten via `scripts/ibkr_close_all_positions.py` continues until criterion 5 is satisfied. **2026-04-28 empirical evidence: operator daily-flatten failed at least once (27 of 87 ORPHAN-SHORT detections from a missed run);** Sprint Abort Condition #7 (lowered to 2 weeks per Round-2 H-R2-3 severity calibration) covers second missed-run incident.

Live trading transition gated by criterion 5 + DEF-208 pre-live paper stress test (Sprint 31.93 OR 31.94 territory) + Round 3 verdict materialized (Decision 7 (b) class accepted-as-known-limitation OR Decision 7 (a) class triggered another revision pass).
```

---

## Sprint 31.92 Adversarial Review Round 3 reference

The full Sprint Spec (Phase B re-run revised) + Spec by Contradiction (Phase B
re-run revised) + Adversarial Review Input Package Round 3 form the Round 3
review input. **Round 3 scope is full per `protocols/adversarial-review.md`
v1.1.0 § Outcome C** — the Round 2 disposition's "narrowest possible scope"
recommendation is superseded by the 2026-04-29 amendment. See
`adversarial-review-input-package-round-3.md` for:

- Round framing (Round 3, full scope per Outcome C)
- Sprint context (Sprint 31.91 sealed; DEC-386 empirically falsified 2026-04-28; Round 1 + Round 2 + Phase A Tier 3 history)
- Round 1 + Round 2 + Phase A Tier 3 verdict summaries
- Decision 7 pre-commitment verbatim (binding context for Round 3 verdict authoring)
- The revised FAI table verbatim (9 entries) with self-falsifiability clause
- Round 3 reviewer's FAI-specific tasks (completeness check, status-rating audit, spike-quality check, Cross-Layer Composition Test check)
- Architecture document excerpts (§3.3 Broker abstraction, §3.7 Order Manager, §13 Alert Observability)
- DEC entry excerpts (DEC-385, DEC-386, DEC-388, DEC-117, DEC-369, DEC-372)
- Round 3 verdict template per `protocols/adversarial-review.md` v1.1.0
