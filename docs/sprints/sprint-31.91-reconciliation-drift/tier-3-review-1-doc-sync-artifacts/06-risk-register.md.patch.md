# Doc-Sync Patch 6 — `docs/risk-register.md`

**Purpose:** (a) Update the existing RSK-DEF-204 entry to reflect post-Session-1c state (mitigation expanded, status downgraded from "OPEN" to "PARTIALLY MITIGATED"). (b) Insert new RSK-DEC-386-DOCSTRING entry covering the time-bounded `reconstruct_from_broker` STARTUP-ONLY contract.

**Anchor verification (must hold before applying):**
- Line 1037: `### RSK — Upstream Cascade Mechanism (DEF-204)`
- Line 1050: `| **Cross-references** | DEF-204 (CLAUDE.md DEF table); IMPROMPTU-11 mechanism diagnostic (\`docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md\`); Apr 24 debrief §A2/§C12 (\`docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md\`); post-31.9-reconciliation-drift DISCOVERY (\`docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md\`). |`
- Line 1052: `---`
- Line 1054: `### RSK — Risk Manager WARNING-Spam Throttling Gap (DEF-203)`
- Line 1071: `*End of Risk & Assumptions Register v1.7*`

---

## Patch A — Update existing RSK-DEF-204 to reflect Session 1c landing

### Find (the full DEF-204 RSK block, lines 1037–1050):

```
### RSK — Upstream Cascade Mechanism (DEF-204)

| Field | Value |
|-------|-------|
| **ID** | RSK-DEF-204 |
| **Date Identified** | 2026-04-24 |
| **Category** | Operational Safety — Critical |
| **Severity** | Critical |
| **Likelihood** | Confirmed (3 successive paper-session debriefs Apr 22–24) |
| **Description** | Bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, allow multi-leg fill races. ARGUS's exit-side accounting is also side-blind in 3 surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info; DEF-158 retry path side-blind). On Apr 24 paper trading: 44 symbols / 14,249 shares of unintended short positions accumulated through gradual reconciliation-mismatch drift over a 6-hour session. Today's raw upstream cascade is ~2.0× worse than yesterday's pre-doubling magnitude despite the lightest network stimulus of the three debriefed days. |
| **Mitigation (in effect)** | Operator runs `scripts/ibkr_close_all_positions.py` daily at session close. IMPROMPTU-04's A1 fix (DEF-199) correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert. `ArgusSystem._startup_flatten_disabled` invariant (`check_startup_position_invariant()` in `argus/main.py`) gates `OrderManager.reconstruct_from_broker()` on any non-BUY broker side at boot. |
| **Owner** | post-31.9-reconciliation-drift sprint (3 sessions, all-three-must-land-together, adversarial review required at every session boundary). |
| **Status** | **OPEN — mitigation in effect; fix scoped and scheduled.** Not safe for live trading until post-31.9-reconciliation-drift lands. |
| **Cross-references** | DEF-204 (CLAUDE.md DEF table); IMPROMPTU-11 mechanism diagnostic (`docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`); Apr 24 debrief §A2/§C12 (`docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`); post-31.9-reconciliation-drift DISCOVERY (`docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`). |
```

### Replace with:

```
### RSK — Upstream Cascade Mechanism (DEF-204)

| Field | Value |
|-------|-------|
| **ID** | RSK-DEF-204 |
| **Date Identified** | 2026-04-24 |
| **Category** | Operational Safety — Critical |
| **Severity** | Critical (downgrading toward Medium as Sprint 31.91 lands) |
| **Likelihood** | Confirmed (3 successive paper-session debriefs Apr 22–24); pending falsifiable re-test post-Sprint-31.91 close via mass-balance script |
| **Description** | Bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, allow multi-leg fill races. ARGUS's exit-side accounting is also side-blind in 3 surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info; DEF-158 retry path side-blind). On Apr 24 paper trading: 44 symbols / 14,249 shares of unintended short positions accumulated through gradual reconciliation-mismatch drift over a 6-hour session. |
| **Mitigation (in effect)** | (1) **Sprint 31.91 Sessions 0+1a+1b+1c LANDED 2026-04-27 (DEC-386, Tier 3 review #1 PROCEED).** The 4-layer OCA architecture closes the bracket-internal fill race that produced ~98% of the blast radius per IMPROMPTU-11 (bracket children now in OCA group with `ocaType=1`; standalone-SELL paths thread the same group; broker-only paths cancel-then-SELL with propagation-await; `_handle_oca_already_filled` short-circuits redundant SELLs). (2) Operator continues daily `scripts/ibkr_close_all_positions.py` flatten — required throughout the sprint window until ≥3 paper sessions with zero `unaccounted_leak` mass-balance rows + zero `phantom_short`/`cancel_propagation_timeout` alerts. (3) IMPROMPTU-04's A1 fix (DEF-199) continues to refuse to amplify any residual short at EOD (1.00× signature, zero doubling) — second-line defense. (4) `ArgusSystem._startup_flatten_disabled` invariant continues to gate `OrderManager.reconstruct_from_broker()` on any non-BUY broker side at boot — third-line defense. **Remaining work in flight:** Sessions 2a–2d (side-aware reconciliation contract; DEC-385 reserved) close the secondary detection-blindness mechanism; Session 3 closes the DEF-158 retry side-blindness; Session 4 delivers the falsifiable mass-balance validation; Sessions 5a.1–5e make the new alerts visible in the Command Center. |
| **Owner** | Sprint 31.91 (`sprint-31.91-reconciliation-drift`; 18 sessions across the OCA architecture / reconciliation contract / DEF-158 retry side-check / mass-balance / alert observability tracks). |
| **Status** | **PARTIALLY MITIGATED — primary mechanism (~98%) closed by Sessions 0+1a+1b+1c; secondary mechanism + falsifiable validation + alert observability in flight via remaining 14 Sprint 31.91 sessions.** Not yet safe for live trading. Live-trading consideration unblocked only after: (a) Sprint 31.91 sealed; (b) ≥3 paper sessions with zero `unaccounted_leak`/`phantom_short`/`cancel_propagation_timeout` indicators; (c) Session 5a.1 (HealthMonitor consumer) lands so alerts are Command-Center-visible; (d) pre-live paper stress test under live-config simulation passes (gate 3a per Sprint Spec §D7 HIGH #4). See `docs/pre-live-transition-checklist.md` §"Sprint 31.91 — OCA Architecture & Reconciliation Drift" for the full gate list. |
| **Cross-references** | DEF-204 (CLAUDE.md DEF table); DEC-386 (decision-log.md, 2026-04-27); IMPROMPTU-11 mechanism diagnostic (`docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`); Apr 24 debrief §A2/§C12 (`docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`); Sprint 31.91 sprint spec (`docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md`); Tier 3 review #1 (this conversation 2026-04-27); RSK-DEC-386-DOCSTRING (sibling — `reconstruct_from_broker` STARTUP-ONLY contract). |
```

---

## Patch B — Insert new RSK-DEC-386-DOCSTRING entry between RSK-DEF-204 and RSK-DEF-203

### Find (the separator + start of the next block at lines 1052–1054):

```
---

### RSK — Risk Manager WARNING-Spam Throttling Gap (DEF-203)
```

### Replace with:

```
---

### RSK — `reconstruct_from_broker` STARTUP-ONLY Docstring Contract (DEC-386)

| Field | Value |
|-------|-------|
| **ID** | RSK-DEC-386-DOCSTRING |
| **Date Identified** | 2026-04-27 (Sprint 31.91 Tier 3 review #1) |
| **Category** | Architectural Safety — Time-Bounded Contract |
| **Severity** | Medium |
| **Likelihood** | Low (no current trigger path exists; ARGUS does not support mid-session reconnect) |
| **Description** | Sprint 31.91 Session 1c added a contractual STARTUP-ONLY docstring to `argus/execution/order_manager.py::reconstruct_from_broker()` documenting that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — because the unconditional `cancel_all_orders(symbol, await_propagation=True)` invocation is correct ONLY at startup (clears yesterday's stale OCA siblings); a mid-session reconnect would WIPE OUT today's working bracket children that must be preserved. The do-not-modify list for Session 1c forbade modifying `argus/main.py:1081` (the only existing call site), so the parameter could not be introduced unilaterally in Session 1c. **There is no compile-time or runtime gate today** — only a docstring. A future maintainer skim-reading the function while implementing reconnect-recovery could miss the docstring, wire a reconnect path through `reconstruct_from_broker`, and silently destroy live bracket protection. |
| **Mitigation (in effect)** | (1) **ARGUS does not currently support mid-session reconnect at all.** The function has exactly one caller (`argus/main.py:1081`, gated by `_startup_flatten_disabled`). No existing reconnect path can trip the contract today. (2) DEF-211 (CLAUDE.md DEF table) is filed as a **Sprint 31.93 sprint-gating item** — Sprint 31.93 (DEF-194/195/196 reconnect-recovery) is structurally forced to touch this function, and its spec MUST include the `ReconstructContext` introduction or it cannot be sealed. (3) Architecture doc §3.7 OCA Architecture block (added 2026-04-27 doc-sync) cross-references the docstring at spec level so the contract is visible outside the source file. |
| **Owner** | Sprint 31.93 (DEF-194/195/196 reconnect-recovery) — sprint-gating item per DEF-211. |
| **Status** | **OPEN — time-bounded by Sprint 31.93.** If Sprint 31.93 slips significantly, reassess: extract the STARTUP-only invariant into a runtime gate via a separate small impromptu before implementing any reconnect work. |
| **Cross-references** | DEC-386 (Sprint 31.91 OCA architecture); DEF-211 (Sprint 31.93 ReconstructContext parameter — sprint-gating); DEF-194/195/196 (reconnect-recovery family); Tier 3 review #1 Focus Area 2 (this conversation 2026-04-27); `argus/execution/order_manager.py::reconstruct_from_broker()` docstring; `docs/architecture.md` §3.7 OCA Architecture block. |

---

### RSK — Risk Manager WARNING-Spam Throttling Gap (DEF-203)
```

---

## Patch C — Update version footer

### Find:

```
*End of Risk & Assumptions Register v1.7*
```

### Replace with:

```
*End of Risk & Assumptions Register v1.8*
*Last updated: 2026-04-27 (Sprint 31.91 Tier 3 review #1 doc-sync — RSK-DEF-204 status update + RSK-DEC-386-DOCSTRING entry)*
```

---

## Application notes

- Three surgical replacements:
  - **A:** rewrite RSK-DEF-204 in-place to reflect post-Session-1c reality (status changed from OPEN to PARTIALLY MITIGATED, mitigation expanded with the 4-layer OCA architecture summary).
  - **B:** insert RSK-DEC-386-DOCSTRING entry between RSK-DEF-204 and RSK-DEF-203, preserving the existing `---` separator structure.
  - **C:** bump the version footer from v1.7 to v1.8 with the date stamp.
- The downgrade language ("Severity: Critical (downgrading toward Medium as Sprint 31.91 lands)") is intentionally hedged. The actual downgrade to Medium happens at Sprint 31.91 sprint close + ≥3 paper sessions clean. Until then, the practical operational severity is still Critical because the compensating control is operator-manual.
- No other RSK entries are touched.
