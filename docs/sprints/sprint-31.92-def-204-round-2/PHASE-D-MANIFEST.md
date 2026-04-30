# Sprint 31.92 — Phase D Manifest

> **Phase D artifact summary** per `protocols/sprint-planning.md` v1.3.0 § Phase D.
> Authored 2026-04-29 against the Phase C re-sealed (post-Round-3) artifact set
> (HEAD `08052b2` + S5c score correction `ff945c8`).
>
> This is a summary manifest — NOT a runner config. (Runner config is only
> generated for autonomous mode; Sprint 31.92 is HITL.)

---

## Artifacts Generated (26 files)

### 1. Shared Review Context (1 file)

| Filename | Scope |
|----------|-------|
| `review-context.md` | Single shared file embedding sprint-spec.md + spec-by-contradiction.md + regression-checklist.md + escalation-criteria.md verbatim. Read-only context for all 12 Tier 2 reviewers. ~3,056 lines. |

### 2. Implementation Prompts (12 files; one per session)

| Filename | Session | Scope (≤15 words) |
|----------|---------|-------------------|
| `sprint-31.92-s1a-spike-path1-impl.md` | S1a | Path #1 mechanism spike: `modify_order` rejection-rate + 4 adversarial axes + N=100 cancel-then-SELL stress |
| `sprint-31.92-s1b-spike-path2-impl.md` | S1b | Path #2 fingerprint + hard-to-borrow microcap window spike (case-A vs case-B differentiation) |
| `sprint-31.92-s2a-path1-trail-flatten-impl.md` | S2a | Path #1 fix in `_trail_flatten` per S1a-selected mechanism + M-R3-3 precondition check |
| `sprint-31.92-s2b-path1-emergency-flatten-impl.md` | S2b | Path #1 in `_resubmit_stop_with_retry` emergency-flatten + H-R2-2 HALT-ENTRY tests |
| `sprint-31.92-s3a-path2-helpers-and-config-impl.md` | S3a | Path #2 fingerprint + position-keyed dict + 4 OrderManagerConfig fields + `time.monotonic()` |
| `sprint-31.92-s3b-path2-emit-sites-and-broker-verified-fallback-impl.md` | S3b | Path #2 wire-up + AC2.5 refresh-then-verify + Branch 4 + HALT-ENTRY coupling + Fix A serialization + FAI #10 |
| `sprint-31.92-s4a-i-ceiling-with-pending-reservation-impl.md` | S4a-i | Long-only SELL-volume ceiling + atomic `_reserve_pending_or_fail` + AC2.7 watchdog auto-activation |
| `sprint-31.92-s4a-ii-callback-atomicity-and-reflective-call-ast-impl.md` | S4a-ii | Synchronous-update invariant on all bookkeeping callback paths + FAI #8 reflective + FAI #11 callsite-enumeration |
| `sprint-31.92-s4b-def212-rider-with-startup-warning-and-allow-rollback-impl.md` | S4b | DEF-212 wiring + AC4.6 dual-channel + AC4.7 `--allow-rollback` + interactive ack + periodic re-ack |
| `sprint-31.92-s5a-validation-path1-impl.md` | S5a | Path #1 in-process falsifiable validation against SimulatedBroker |
| `sprint-31.92-s5b-validation-path2-composite-and-restart-impl.md` | S5b | Path #2 + composite + restart-during-active-position validation |
| `sprint-31.92-s5c-cross-layer-composition-tests-impl.md` | S5c | CL-1..CL-5 + CL-7 cross-layer composition tests + `SimulatedBrokerWithRefreshTimeout` fixture |

### 3. Review Prompts (12 files; one per session)

| Filename | Session | Scope |
|----------|---------|-------|
| `sprint-31.92-s1a-spike-path1-review.md` | S1a | Tier 2 review: JSON schema completeness, mechanism-selection consistency, FAI #3 + #5 falsification |
| `sprint-31.92-s1b-spike-path2-review.md` | S1b | Tier 2 review: fingerprint stability, case-A vs case-B differentiation, H6 rules-out path |
| `sprint-31.92-s2a-path1-trail-flatten-review.md` | S2a | Tier 2 review: AC1.1–AC1.6 mechanism-conditional + M-R3-3 precondition + cross-session field shape |
| `sprint-31.92-s2b-path1-emergency-flatten-review.md` | S2b | Tier 2 review: AC1.3 emergency-branch extension + H-R2-2 HALT-ENTRY + DEC-372 backoff preservation |
| `sprint-31.92-s3a-path2-helpers-and-config-review.md` | S3a | Tier 2 review: AC2.1 + AC2.2 helpers + 4 config fields + Decision 4 watchdog Pydantic + YAML/Pydantic alignment |
| `sprint-31.92-s3b-path2-emit-sites-and-broker-verified-fallback-review.md` | S3b | Tier 2 review: AC2.3–AC2.8 + Fix A serialization + FAI #10 materialization + Tier 3 item C coupling |
| `sprint-31.92-s4a-i-ceiling-with-pending-reservation-review.md` | S4a-i | Tier 2 review: AC3.1–AC3.9 ceiling + H-R2-1 atomic + AC2.7 watchdog + POLICY_TABLE 14th entry |
| `sprint-31.92-s4a-ii-callback-atomicity-and-reflective-call-ast-review.md` | S4a-ii | Tier 2 review: callback atomicity + FAI #8 + FAI #11 + M-R3-4 helper + FAI #11 materialization. **M-R2-5 trigger session.** |
| `sprint-31.92-s4b-def212-rider-with-startup-warning-and-allow-rollback-review.md` | S4b | Tier 2 review: AC4.1–AC4.7 + H-R3-4 interactive ack + periodic re-ack + `_OCA_TYPE_BRACKET` deletion |
| `sprint-31.92-s5a-validation-path1-review.md` | S5a | Tier 2 review: AC5.1 in-process logic correctness + JSON artifact schema |
| `sprint-31.92-s5b-validation-path2-composite-and-restart-review.md` | S5b | Tier 2 review: AC5.2 + AC5.3 + AC5.4 restart + composite + deferred coverage |
| `sprint-31.92-s5c-cross-layer-composition-tests-review.md` | S5c | **Tier 2 review (FINAL session — full suite):** AC5.6 cross-layer + Branch 4 fixture + sprint-seal precondition |

### 4. Operational / Handoff Artifacts (1 file)

| Filename | Scope |
|----------|-------|
| `work-journal-handoff.md` | Self-contained handoff for the Claude.ai work-journal-tracking conversation. Sprint goal, scope summary, 12-session breakdown, dependency chain, "Do not modify" file list, issue category definitions, escalation triggers, reserved DEC-390 + 8 DEFs (6 Tier-3-class + DEF-204 + DEF-212) + 10 RSKs (5 sprint-class + 2 Tier-3-class + 3 Round-3-class). |

---

## Session Dependency Chain

```
[Sprint 31.91 SEALED + Sprint 31.915 SEALED — verified at HEAD]
                                  │
                                  ▼
                      ┌───────────┴───────────────────┐
                      │                               │
                   S1a spike                       S1b spike
                   (mechanism)                     (fingerprint +
                                                    suppression window)
                      │                               │
                      └─── G1: Operator confirms ─────┘
                           selected_mechanism            G2: Operator confirms
                                  │                       recommended_locate_
                                  │                       suppression_seconds
                                  ▼                       │
                              S2a impl                    ▼
                              (per H2/H4/H1)         S3a impl
                                  │                  (helpers + config)
                                  ▼                       │
                              S2b impl                    ▼
                              (+ H-R2-2 HALT-ENTRY)  S3b impl
                                  │                  (broker-verified
                                  │                   AC2.5 + Branch 4 +
                                  │                   HALT-ENTRY +
                                  │                   Fix A serialization)
                                  │                       │
                                  └───────────┬───────────┘
                                              ▼
                                       S4a-i ceiling
                                       (atomic _reserve_pending_or_fail
                                        + AC2.7 auto-activation)
                                              │
                                              ▼
                              S4a-ii callback atomicity + AST
                              (FAI #9 + FAI #8 + FAI #11
                               + M-R3-4 helper)
                                              │
                                              │  G3: Tier 2 verdict CLEAR
                                              ▼
                              ┌─── M-R2-5 Mid-Sprint Tier 3 ───┐
                              │   (architectural-closure        │
                              │    cross-validation; PROCEED → │
                              │    continue; REVISE_PLAN /     │
                              │    PAUSE_AND_INVESTIGATE →     │
                              │    halt sprint)                │
                              └─────────────────┬───────────────┘
                                              ▼
                                       G4: PROCEED verdict
                                              │
                                              ▼
                                         S4b DEF-212
                                         (+ AC4.6 dual-channel
                                          + AC4.7 --allow-rollback
                                          + H-R3-4 interactive ack +
                                          periodic re-ack +
                                          --allow-rollback-skip-confirm)
                                              │
                                              ▼
                                      S5a path1 validation
                                              │
                                              ▼
                          S5b path2 + composite + restart validation
                                              │
                                              ▼
                          S5c cross-layer composition tests + Branch 4 fixture
                          (FINAL — full-suite green is sprint-seal precondition)
                                              │
                                              ▼
                                  Sprint 31.92 SEAL + DEC-390 materialization
```

**Critical-path notes:**
- **S1a + S1b** can run in parallel if operator splits IBKR clientId budget (clientId=1 for S1a, clientId=2 for S1b); otherwise sequential. Both gate G1/G2 operator-confirmation events.
- **S2a + S2b** run sequentially after S1a+G1.
- **S3a + S3b** run sequentially after S1b+G2.
- The two branches (S2a/S2b and S3a/S3b) MUST merge before S4a-i because S4a-i's ceiling guards every SELL emit site touched by Path #1 AND Path #2.
- **S4a-ii follows S4a-i** (atomic-reserve reference pattern dependency).
- **M-R2-5 fires AFTER S4a-ii close-out + Tier 2 verdict CLEAR, BEFORE S4b begins** (separate Claude.ai conversation; estimated ~100–150K tokens).
- **S4b → S5a → S5b → S5c strictly sequential.**
- All 8 implementation/validation sessions write to `argus/execution/order_manager.py` (except S4a-ii whose preferred outcome is zero production-code change), so merge-discipline is required at S4a-i entry.

**Recommended sequencing for human-in-the-loop (operator-stated default):** strictly sequential `S1a → S1b → S2a → S2b → S3a → S3b → S4a-i → S4a-ii → [M-R2-5] → S4b → S5a → S5b → S5c`. The graph permits parallelism at S1a/S1b but the workflow is safer serialized given the file overlap.

---

## Operator-Confirmation Gates (4 gates)

| Gate | Trigger | Confirms | Unblocks | Encoded In |
|------|---------|----------|----------|------------|
| **G1** | S1a JSON artifact `scripts/spike-results/spike-def204-round2-path1-results.json` committed to `main` | `selected_mechanism` ∈ {h2_amend, h4_hybrid, h1_cancel_and_await} per Hypothesis Prescription decision rule + worst-axis Wilson UB + h1_propagation_zero_conflict_in_100 hard gate | S2a + S2b impl prompt finalization | S2a + S2b prompts have **PENDING OPERATOR CONFIRMATION** preamble |
| **G2** | S1b JSON artifact `scripts/spike-results/spike-def204-round2-path2-results.json` committed to `main` | `recommended_locate_suppression_seconds` value (or 18000s fallback if H6 ruled out) + `fingerprint_string` | S3a impl prompt finalization | S3a prompt has **PENDING OPERATOR CONFIRMATION** preamble |
| **G3** | S4a-ii close-out + Tier 2 verdict CLEAR | All four S4a-ii deliverables green: AC3.1 callback-path atomicity (FAI #9), FAI #11 callsite-enumeration AST, FAI #8 reflective sub-tests, M-R3-4 helper AST scan | M-R2-5 mid-sprint Tier 3 review invocation | S4a-ii Tier 2 review prompt's Additional Context section flags M-R2-5 trigger |
| **G4** | M-R2-5 Tier 3 verdict | PROCEED (continue to S4b) / REVISE_PLAN (halt; re-plan affected sessions) / PAUSE_AND_INVESTIGATE (halt sprint) | S4b + S5a + S5b + S5c | S4b impl prompt's Pre-Flight + Dependencies cite "M-R2-5 verdict CLEAR (PROCEED)" as required precondition |

---

## Mid-Sprint Tier 3 Review Insertion Point

**M-R2-5 fires:**
- **AFTER** S4a-ii close-out + Tier 2 review verdict CLEAR (or CONCERNS_RESOLVED).
- **BEFORE** S4b implementation begins.
- **Per** Round 2 disposition M-R2-5 + Round 3 disposition § 1.3 reinforcement (the M-R2-5 mid-sprint Tier 3 review is the proportional re-review for the C-R3-1 Fix A operator-override per Decision 7 (b)).

**Scope:** Architectural closure of DEC-390's 4-layer structure post-S4a-ii. Cross-validation of:
- Pending-reservation pattern (H-R2-1 atomic method).
- Ceiling guard at 5 standalone-SELL emit sites.
- `is_reconstructed` refusal posture (AC3.7).
- Callback-path atomicity invariant per Tier 3 items A + B / FAI entry #9 (NEW post-Phase-A-Tier-3-verdict).
- Reflective-call AST coverage per Decision 3 / FAI #8 option (a) (NEW post-Phase-A-Tier-3-verdict).
- AC2.7 watchdog auto-activation per Decision 4.

**This is distinct from the Phase A Tier 3 review #1 already conducted on 2026-04-29** (verdict REVISE_PLAN; outcome was Phase B re-run + Round 3 full-scope adversarial review). M-R2-5 is the second Tier 3 review event of the sprint.

**Tier 3 reviewer:** fresh Claude.ai conversation (separate from the Work Journal conversation). Sprint-cost estimated ~100–150K tokens.

**Inputs:** S4a-i + S4a-ii close-out reports; revised sprint package (sprint-spec.md + spec-by-contradiction.md + regression-checklist.md + escalation-criteria.md + falsifiable-assumption-inventory.md + revision-rationale.md + round-3-disposition.md + phase-b-rerun-note.md); cumulative diff on `argus/execution/order_manager.py` at this checkpoint (target ~600–800 LOC, well below the recalibrated ~1200–1350 cumulative bound per Round 3 disposition § 7.1).

**Outputs:** `tier-3-review-2-verdict.md` (file authored at sprint folder root by the Tier 3 reviewer; verdict ∈ {PROCEED, REVISE_PLAN, PAUSE_AND_INVESTIGATE}).

---

## Phase D Verification Checklist

Before commit, the operator should verify:

- [x] `review-context.md` exists and is the verbatim concatenation of Phase C artifacts (sprint-spec + spec-by-contradiction + regression-checklist + escalation-criteria).
- [x] 12 implementation prompts exist with naming pattern `sprint-31.92-{session-id}-impl.md`.
- [x] 12 review prompts exist with naming pattern `sprint-31.92-{session-id}-review.md`.
- [x] `work-journal-handoff.md` exists.
- [x] All artifacts are flat in `docs/sprints/sprint-31.92-def-204-round-2/` (no subdirectories).
- [x] Each impl prompt conforms to `templates/implementation-prompt.md` v1.5.0 structure including the structural-anchor block per the 2026-04-28 amendment.
- [x] Each review prompt conforms to `templates/review-prompt.md` v1.2.0 structure.
- [x] S2a + S2b + S3a impl prompts open with **PENDING OPERATOR CONFIRMATION** preamble.
- [x] S3b impl prompt's Close-Out section directs FAI #10 materialization per `doc-update-checklist.md` D15.
- [x] S4a-ii impl prompt's Close-Out section directs FAI #11 materialization per `doc-update-checklist.md` D16.
- [x] S4a-ii Tier 2 review prompt's Additional Context flags M-R2-5 mid-sprint Tier 3 trigger event (separate Claude.ai conversation).
- [x] S5c impl + review prompts use full suite per DEC-328 final-review tier.

---

## Stop Conditions Encountered (None)

No blocking discrepancies surfaced during Phase D authoring. Soft RULE-038 disclosures noted by sub-agents for downstream visibility:

- **AC1.4 numbering quirk** — folded into AC1.3's text rather than appearing as standalone bullet; prompts cite "AC1.4" as the spec does (canonical reference for AMD-8 + AMD-4 guards property).
- **`config/order_management.yaml` path** — S3a's grep-verify directs implementer to confirm actual YAML overlay path; close-out reports actual path used.
- **`argus/risk/risk_manager.py` vs `argus/core/risk_manager.py`** — Round 3 disposition § 7.1 cited `argus/risk/risk_manager.py`; actual ARGUS structure puts risk manager at `argus/core/risk_manager.py`. S3b prompt directs implementer to grep-verify and use actual layout.
- **`argus/api/v1/positions.py` vs `argus/api/routes/positions.py`** — Round 3 disposition § 7.1 cited `argus/api/v1/positions.py`; actual ARGUS structure puts routes at `argus/api/routes/`. S3b prompt directs implementer to use actual layout.
- **S5c session-breakdown.md compaction-score drift** — disposition's "11 → 11.5" expectation reconciled to actual scoring table at "13 → 13.5"; preserved Medium-tier (≤13.5) classification; absolute baseline number is the only drift.

These do not block Phase D and are documented in the corresponding impl prompts' RULE-038 disclosure sections for the implementer to surface in close-out.

---

## Sprint Stats (Phase D Outputs)

| Metric | Value |
|--------|------:|
| Implementation prompts | 12 |
| Review prompts | 12 |
| Shared review-context.md | 1 (~3,056 lines) |
| Work journal handoff | 1 (~250 lines) |
| Phase D manifest (this file) | 1 |
| **Total artifacts** | **27** |
| Sprint sessions (implementation/spike/validation) | 12 |
| Mid-sprint Tier 3 review events | 1 (M-R2-5) |
| Operator-confirmation gates | 4 (G1–G4) |
| Reserved DEC | 1 (DEC-390) |
| Anticipated DEFs | 8 (DEF-204 RESOLVED-PENDING-PAPER + DEF-212 RESOLVED + 6 Tier-3-class) |
| Reserved RSKs | 10 (5 sprint-class unconditional + 2 conditional + 2 Tier-3-class + 1 Round-3-class CRITICAL) |

---

*End Phase D manifest.*
