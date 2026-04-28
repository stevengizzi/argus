# Doc-Sync Patch 1 — `docs/decision-log.md` (AMENDED v3 — Apr 27 debrief findings folded into DEC-386 Impact + Cross-Refs)

**Purpose:** Insert DEC-386 (OCA-group threading + broker-only safety) under a new `## Sprint 31.91` section, between the existing Sprint 31.9 section and the file footer. Update the footer's "Next DEC" line.

**Amendment history:**
- v1: original DEC-386 entry from initial Tier 3 verdict.
- v2: cross-references row updated to include DEF-213.
- **v3 (current): Impact + Cross-References rows updated** to fold in Apr 27 paper-session debrief findings — DEF-211 extended scope (D1+D2+D3 per Apr 27 Findings 3+4), DEF-214 (Apr 27 Finding 1 — EOD verification timing race), DEF-215 (Apr 27 Finding 2 — reconciliation log spam, deferred). Apr 27 debrief path added to cross-references. Note that Apr 27 ran PRE-OCA (Sessions 0-1c had not yet landed at `bf7b869`); Apr 27 evidence is therefore another DEF-204 manifestation on pre-fix code, not a test of OCA architecture.

**Anchor verification (must hold before applying):**
- `docs/decision-log.md` line 4715 contains `## Sprint 31.9 — Campaign-Close: Health & Hardening (April 22 – April 24, 2026)` (verified at this Tier 3 review's commit `bf7b869`).
- The file ends at line 4739 with footer `*Last updated: 2026-04-24 (Sprint 31.9 SPRINT-CLOSE-B — campaign-close no-new-DECs entry)*`.
- DEC-385 is RESERVED for the Sprint 31.91 side-aware reconciliation contract (Sessions 2a/2b.1/2b.2/2c.1/2c.2/2d). Sessions 0/1a/1b/1c only consume DEC-386.

---

## Patch A — Replace footer block (3 lines → ~30 lines)

### Find (exact match):

```
*End of Decision Log v1.0*
*Next DEC: 385*
*Last updated: 2026-04-24 (Sprint 31.9 SPRINT-CLOSE-B — campaign-close no-new-DECs entry)*
```

### Replace with (the new Sprint 31.91 OCA-architecture section, then updated footer):

```
---

## Sprint 31.91 — Reconciliation Drift / Phantom-Short Fix + Alert Observability (April 27, 2026 onward)

DEC range allocation: DEC-385–DEC-388 reserved during Sprint 31.91 planning. Allocation:

- **DEC-385** — RESERVED for the side-aware reconciliation contract (Sessions 2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d). Will be written at the close of Session 2d.
- **DEC-386** — OCA-group threading + broker-only safety (Sessions 0 / 1a / 1b / 1c). Written below following Tier 3 architectural review #1 (CLEAR, 2026-04-27). Verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`.
- **DEC-387** — RESERVED (placeholder; allocation TBD during Session 3 / Session 4 planning if a non-trivial design decision surfaces).
- **DEC-388** — RESERVED for alert observability architecture (Sessions 5a.1 / 5a.2 / 5b / 5c / 5d / 5e). Resolves DEF-014. Will be written at the close of Session 5e.

### DEC-386 | OCA-Group Threading + Broker-Only Safety

| Field | Value |
|-------|-------|
| **Date** | 2026-04-27 |
| **Sessions** | Sprint 31.91 — Sessions 0, 1a, 1b, 1c |
| **Final commit (Tier 3 gate)** | `bf7b869` (`docs(sprint-31.91): session 1c Tier 2 review verdict (CLEAR)`) |
| **Tier 3 verdict** | PROCEED (combined diff of Sessions 0+1a+1b+1c reviewed against `tier-3-review.md` protocol; verdict 2026-04-27 documented at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`). |
| **Context** | DEF-204's IMPROMPTU-11 mechanism diagnostic identified that bracket children were placed via `parentId` only, with no `ocaGroup`/`ocaType` set — combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group, this allowed multi-leg fill races accounting for ~98% of the unexpected-short blast radius observed in the Apr 22–24 paper-session debriefs (44 symbols / 14,249 unintended short shares on Apr 24 alone). Three additional broker-only SELL paths (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`) had no defense against stale yesterday OCA-group siblings firing against today's flatten SELL. Operator daily flatten via `scripts/ibkr_close_all_positions.py` was the only mitigation. |
| **Decision** | Adopt a 4-layer OCA architecture: (1) **API contract (Session 0)** — extend `Broker.cancel_all_orders()` ABC to accept `symbol: str \| None` and keyword-only `await_propagation: bool` arguments; introduce `CancelPropagationTimeout` exception; preserve DEC-364 no-args contract verbatim across `IBKRBroker`, `SimulatedBroker`, `AlpacaBroker` (the latter as a `DeprecationWarning` stub queued for Sprint 31.94 retirement). (2) **Bracket OCA (Session 1a)** — set `ocaGroup = f"oca_{parent_ulid}"` and `ocaType = config.ibkr.bracket_oca_type` (default 1) on each bracket child (stop, T1, T2) at `IBKRBroker.place_bracket_order`; persist `oca_group_id` on `ManagedPosition`; the parent (entry) Order is intentionally NOT in the OCA group. New `IBKRConfig.bracket_oca_type` Pydantic field constrained to `[0, 1]` (ocaType=2 architecturally wrong; ocaType=0 is RESTART-REQUIRED rollback escape hatch). Defensive `_is_oca_already_filled_error` helper distinguishes IBKR Error 201 / "OCA group is already filled" (SAFE) from generic Error 201 (margin, price-protection, etc.) at the rollback layer; cancellation still fires (DEC-117 invariant), only log severity differs. (3) **Standalone-SELL OCA (Session 1b)** — thread `ManagedPosition.oca_group_id` onto every SELL Order placed by the four standalone-SELL paths (`_trail_flatten`, `_escalation_update_stop`, `_submit_stop_order` / `_resubmit_stop_with_retry`, `_flatten_position`); `oca_group_id is None` falls through to legacy no-OCA behavior for `reconstruct_from_broker`-derived positions; graceful Error 201 / OCA-filled handling sets `ManagedPosition.redundant_exit_observed = True`, logs INFO, and short-circuits the DEF-158 retry path. Grep regression guard `test_no_sell_without_oca_when_managed_position_has_oca` enforces threading discipline; legitimate broker-only paths are exempted via the canonical `# OCA-EXEMPT: <reason>` comment. (4) **Broker-only safety (Session 1c)** — invoke `cancel_all_orders(symbol=..., await_propagation=True)` BEFORE the SELL/wire on each of the three broker-only paths; on `CancelPropagationTimeout` (2s budget exceeded), abort the SELL/wire, emit a critical `SystemAlertEvent(alert_type="cancel_propagation_timeout")`, and let the operator manually flatten via `scripts/ibkr_close_all_positions.py`. `reconstruct_from_broker()` gains a contractual STARTUP-ONLY docstring documenting that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — the unconditional cancel is correct ONLY at startup. |
| **Alternatives** | (A) `ocaType=2` ("Reduce with block") — rejected: Phase A spike (`scripts/spike_ibkr_oca_late_add.py`, `PATH_1_SAFE` 2026-04-25) confirmed `ocaType=1` is the IBKR-enforced atomic-cancellation semantics; ocaType=2 has different reduction semantics inappropriate for ARGUS's bracket model. (B) Place the parent (entry) order INTO the OCA group along with the children — rejected: an entry-fill would then OCA-cancel its own protection legs, defeating the bracket. (C) `BrokerOnlySell` marker class via structural typing — rejected for this sprint scope: would require extensive type changes across `Broker.place_order`, `OrderManager`, and every test that constructs an `Order`; the grep regex + `# OCA-EXEMPT:` marker is the surgical choice. Long-horizon revisit deferred to post-Sprint-35. (D) Add `ReconstructContext` parameter to `reconstruct_from_broker()` now — rejected: would require touching `argus/main.py:1081` (do-not-modify-list for this sprint) and would couple Session 1c to Sprint 31.93 (DEF-194/195/196 reconnect-recovery), which is the natural sprint to introduce the parameter alongside the actual reconnect-recovery work. Docstring contract is the bridging mechanism. (E) Place the SELL without verifying broker-side cancellation propagation — rejected: a stale OCA sibling firing against the SELL would create an unbounded phantom short. The 2s `await_propagation` budget plus abort-on-timeout is the asymmetric-risk-aware default (bounded leaked-long preferable to unbounded phantom-short). |
| **Rationale** | DEF-204's mechanism is a fill-side race that is structurally invisible to ARGUS's exit accounting (the redundant standalone SELLs and the bracket children do not share a cancellation group at the broker, so when one fires the other is still live). The fix is at the broker layer, not the accounting layer — IBKR's native OCA-group enforcement does the atomic cancellation, eliminating the race. ARGUS's accounting then has fewer cases to handle (the redundant SELL fails with the SAFE OCA-filled signature, which the new `_handle_oca_already_filled` short-circuit absorbs cleanly). Layering the architecture across 4 sessions (rather than monolithic) was a deliberate choice: each session lands a self-contained safety property (the regression-checklist invariant 14 monotonic-safety matrix verifies row-by-row that each session strictly adds capability without removing any). The Phase A spike's `PATH_1_SAFE` outcome is the falsifiable validation that IBKR enforces ocaType=1 atomic cancellation pre-submit. |
| **Impact** | DEF-204's primary mechanism (~98% of blast radius per IMPROMPTU-11) closed by Sessions 1a + 1b. Secondary mechanism (detection blindness in reconcile / DEF-158 retry path / EOD Pass 2) closed by Sessions 2a–2d + 3 (still in flight). Mass-balance validation (Session 4) is the falsifiable end-to-end gate. Live-trading readiness requires: (1) all of Sprint 31.91 lands cleanly; (2) ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows; (3) zero `phantom_short` alerts across those sessions; (4) Session 5a.1 (HealthMonitor consumer for `SystemAlertEvent`) lands so `cancel_propagation_timeout` alerts are visible in the Command Center, not just logs (per Tier 3 review's Focus Area 1 caveat); (5) pre-live paper stress test under live-config simulation (gate criterion 3a per Sprint Spec §D7 HIGH #4). Sprint 31.92 (component-ownership refactor) inherits two follow-ups: relocate `_is_oca_already_filled_error` from `ibkr_broker.py` to `broker.py` (Tier 3 Concern A) and wire `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` to replace the `_OCA_TYPE_BRACKET = 1` module constant (Tier 3 Concern B / DEF-212). Sprint 31.93 (reconnect-recovery) inherits DEF-211's three coupled deliverables (D1 `ReconstructContext` parameter, D2 IMPROMPTU-04 startup invariant gate refactor, D3 boot-time adoption-vs-flatten policy decision) — extended-scope per Apr 27 paper-session debrief Findings 3+4. Sprint 35+ horizon (Learning Loop V2) inherits `ManagedPosition.redundant_exit_observed` persistence (Tier 3 Concern D — folded into DEF-209). Session 5a.1 itself inherits two sprint-gating items: (a) `SystemAlertEvent.metadata: dict[str, Any]` schema extension and atomic emitter migration (Tier 3 Concern C / DEF-213); (b) EOD verification timing race + side-aware classification + distinct alert paths (Apr 27 debrief Finding 1 / DEF-214) — both folded into 5a.1 impl prompt as Requirement 0 and Requirement 0.5 respectively. DEF-215 (reconciliation per-cycle log spam, Apr 27 debrief Finding 2) is deferred with sharp revisit trigger; symptom of upstream condition that Sprint 31.91 itself eliminates. |
| **Cross-References** | DEF-204 (CLAUDE.md DEF table; mechanism diagnostic at `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`); DEC-117 (atomic-bracket invariant — preserved); DEC-364 (cancel_all_orders no-args contract — extended, not modified); DEC-369 (broker-confirmed immunity — preserved); DEC-372 (stop retry caps — preserved); DEC-385 (side-aware reconciliation contract — Sessions 2a-d, in flight); DEC-388 (alert observability — Sessions 5a.1/5a.2/5b/5c/5d/5e, in flight); DEF-209 (Position.side + redundant_exit_observed persistence — Sprint 35+); DEF-211 (Sprint 31.93 sprint-gating — three coupled deliverables D1+D2+D3 per Apr 27 Findings 3+4); DEF-212 (Sprint 31.92 IBKRConfig wiring into OrderManager); DEF-213 (Session 5a.1 SystemAlertEvent.metadata schema + atomic emitter migration — sprint-gating); DEF-214 (Session 5a.1 EOD verification timing race + side-aware classification + distinct alert paths — sprint-gating, Apr 27 debrief Finding 1); DEF-215 (deferred — reconciliation per-cycle log spam, Apr 27 debrief Finding 2); DEF-194/195/196 (reconnect-recovery — Sprint 31.93); RSK-DEC-386-DOCSTRING (docstring contract on `reconstruct_from_broker` is time-bounded by Sprint 31.93). Phase A spike: `scripts/spike_ibkr_oca_late_add.py` + `scripts/spike-results/spike-results-2026-04-25.json` (`PATH_1_SAFE`, valid ≤30 days per regression invariant 22). Tier 3 review verdict artifact: `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`. Apr 27 paper-session debrief: `docs/debriefs/2026-04-27-paper-session-debrief.md` (read-only diagnostic; ran PRE-OCA — Sessions 0-1c had not yet landed). |
| **Status** | Active. |

---

*End of Decision Log v1.0*
*Next DEC: 387 (385 reserved for Sessions 2a-d; 386 written above; 388 reserved for Sessions 5a.1–5e)*
*Last updated: 2026-04-27 (Sprint 31.91 Tier 3 review #1 doc-sync — DEC-386 OCA-group threading + broker-only safety; DEF-213 added to cross-refs)*
```

---

## Application notes

This patch:
1. Adds the `## Sprint 31.91` section header with explicit DEC-385/386/387/388 reservation map.
2. Writes DEC-386 in the canonical 8-row table format used by DEC-382/383/384.
3. Cross-References row includes DEF-209/211/212/213 (all four forcing-function DEFs surfaced by Tier 3) AND points at the verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` (created by Patch 9 of this doc-sync).
4. Replaces the file footer to advance "Next DEC" past 386 and update the date stamp.

Apply with: read lines 4737-4739, replace as above, write file. No other lines in `decision-log.md` are touched.
