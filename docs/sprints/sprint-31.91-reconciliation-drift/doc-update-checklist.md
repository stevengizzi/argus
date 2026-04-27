# Sprint 31.91: Doc Update Checklist

> **Phase C artifact 6/7.** Two-phase doc update plan: (A) cross-reference
> rename patches that should land BEFORE Session 1a begins (so the sprint
> proceeds with consistent naming), and (B) post-sprint doc syncs that follow
> Session 3 close-out. Each item specifies the file, a surgical sed/find-replace
> patch where applicable, and the rationale. Sealed historical artifacts
> (sprint-31.9/, synthesis-2026-04-26/, audits/) are explicitly EXCLUDED from
> rename patches per RULE-053 architectural-seal verification.

## Phase A — Cross-Reference Rename Patches (PRE-sprint)

These updates land BEFORE Session 1a begins so the sprint runs with consistent
naming. The folder renames themselves were already committed and pushed by the
operator (commit pushed 2026-04-27); these items update cross-references that
still point to the old `post-31.9-*` paths.

**Sealed-file exclusions (per RULE-053):** Do NOT touch any file under:
- `docs/sprints/sprint-31.9/` (campaign sealed 2026-04-24)
- `docs/sprints/synthesis-2026-04-26/` (sprint sealed at workflow `e23a3c4`)
- `docs/audits/audit-2026-04-21/` (audit sealed)

If a sealed file references the old path, that's a historical record — leave it
alone. The cross-reference is correct AT THE TIME of the sealed artifact.

### A1. CLAUDE.md

```bash
# Replace post-31.9-* references in CLAUDE.md.
# Verify count first: grep -c 'post-31\.9-' CLAUDE.md
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  CLAUDE.md
# Verify post: grep -c 'post-31\.9-' CLAUDE.md should return 0
```

**Rationale:** CLAUDE.md is the Claude Code session context. Old paths cause
session prompts to point at moved directories.

### A2. docs/project-knowledge.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  docs/project-knowledge.md
```

**Rationale:** This is the Claude.ai planning context. Same reason as A1.

### A3. docs/architecture.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  docs/architecture.md
```

**Rationale:** The DEF-204 callout at line 855 references the old path twice.
This update + a related text refresh in Phase B (post-sprint) covers the
architecture doc.

### A4. docs/project-bible.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  docs/project-bible.md
```

### A5. docs/risk-register.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  docs/risk-register.md
```

**Rationale:** RSK-DEF-204 at line 1037 references the old path in
Cross-references and Owner fields.

### A6. docs/roadmap.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  docs/roadmap.md
```

### A7. docs/sprint-history.md

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  docs/sprint-history.md
```

### A8. The four DISCOVERY.md files

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  -e 's|post-31\.9-component-ownership|sprint-31.92-component-ownership|g' \
  -e 's|post-31\.9-reconnect-recovery-and-rejectionstage|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-reconnect-recovery|sprint-31.93-reconnect-recovery|g' \
  -e 's|post-31\.9-alpaca-retirement|sprint-31.94-alpaca-retirement|g' \
  docs/sprints/sprint-31.91-reconciliation-drift/DISCOVERY.md \
  docs/sprints/sprint-31.92-component-ownership/DISCOVERY.md \
  docs/sprints/sprint-31.93-reconnect-recovery/DISCOVERY.md \
  docs/sprints/sprint-31.94-alpaca-retirement/DISCOVERY.md
```

The DISCOVERY headers themselves should also be updated. Manual edits required:

- `docs/sprints/sprint-31.91-reconciliation-drift/DISCOVERY.md:1`:
  `# Sprint \`post-31.9-reconciliation-drift\` Discovery Notes`
  → `# Sprint \`sprint-31.91-reconciliation-drift\` Discovery Notes`
- `docs/sprints/sprint-31.91-reconciliation-drift/DISCOVERY.md:15`:
  `- **Sprint ID:** \`post-31.9-reconciliation-drift\``
  → `- **Sprint ID:** \`sprint-31.91-reconciliation-drift\``
- Analogous updates in the other 3 DISCOVERY headers (the sed above handles
  the body references; the literal `# Sprint` H1 may need manual edit if the
  sed didn't catch it due to escaping).

### A9. design-summary.md self-reference

```bash
sed -i \
  -e 's|post-31\.9-reconciliation-drift|sprint-31.91-reconciliation-drift|g' \
  docs/sprints/sprint-31.91-reconciliation-drift/design-summary.md
```

The design summary already uses the new name in its title and body, but it
mentions the old name once in the header parenthetical "(renamed from
post-31.9-reconciliation-drift)" — that mention is intentional historical
record and should be PRESERVED. After running the sed, manually re-add
"(renamed from post-31.9-reconciliation-drift)" to the Sprint ID line if it
was clobbered.

### A10. Verification step

```bash
# After all renames, this should return 0:
grep -rn 'post-31\.9-' docs/ CLAUDE.md \
  --exclude-dir=sprint-31.9 \
  --exclude-dir=synthesis-2026-04-26 \
  --exclude-dir=audits \
  | grep -v 'renamed from post-31\.9' \
  | wc -l
```

If non-zero, manually inspect remaining occurrences.

### A11. Commit

```bash
git add CLAUDE.md docs/
git commit -m "docs(sprint-31.91): cross-reference rename — post-31.9-* → sprint-31.9{1..4}-*

Updates active doc-tree references to align with the folder rename committed
in [previous commit SHA]. Sealed historical artifacts (sprint-31.9/,
synthesis-2026-04-26/, audits/audit-2026-04-21/) are intentionally NOT
modified per RULE-053 architectural-seal verification.

Refs: sprint-31.91 doc-update-checklist.md §A
"
```

---

## Phase B — Post-Sprint Doc Syncs (POST-Session-3)

These updates land in a follow-on doc-sync session after Session 3 closes out.
The doc-sync session uses `templates/doc-sync-automation-prompt.md` and
references this Phase B section. **Surgical find-and-replace instructions are
written against actual current file content** per project preferences.

### B1. CLAUDE.md — DEF-204 status update

**Find:** the DEF-204 entry in the DEFs table (currently lists DEF-204 as OPEN
with mechanism IDENTIFIED).

**Replace with:** DEF-204 status update to CLOSED. Suggested text:

```markdown
| DEF-204 | CLOSED in Sprint 31.91 | Upstream cascade of unintended short positions
(reconciliation drift, IMPROMPTU-11 mechanism diagnosis). Resolved by sprint-31.91:
bracket OCA grouping (DEC-386), side-aware reconciliation contract with
phantom-short detection + per-symbol entry gate (DEC-385), and side-aware DEF-158
retry path (mirrors IMPROMPTU-04 3-branch pattern). 4 deliverables across 6
sessions; final paper-session debrief showed zero phantom-short accumulation. |
```

The exact field structure depends on CLAUDE.md's existing DEF-table shape; the
doc-sync session should grep-verify the actual format before replacing.

### B2. CLAUDE.md — Sprint history entries

**Find:** the sprint history table (under "## Recent Sprints" or similar).

**Add after Sprint 31.9:** Six rows for sessions 1a, 1b, 2a, 2b, 2c, 3 of
Sprint 31.91. Format follows existing convention.

### B3. CLAUDE.md — Active sprint update

**Find:** "**Active sprint:** Between sprints. **Sprint 31.9 ... sealed on
2026-04-24.**"

**Replace with:** "**Active sprint:** Between sprints. **Sprint 31.91
(Reconciliation Drift) sealed on [date].** DEF-204 CLOSED. Operator daily
flatten mitigation can be discontinued; live trading consideration unblocked
pending 3-paper-session evidence per DISCOVERY."

### B4. docs/decision-log.md — DEC-385 entry

**Append:**

```markdown
## DEC-385 — Side-aware reconciliation contract (Sprint 31.91)

**Date:** [Sprint 31.91 close date]
**Status:** Active
**Family:** DEC-369 (broker-confirmed positions never auto-closed)

**Decision:** `OrderManager.reconcile_positions()` consumes `dict[str,
ReconciliationPosition]` (frozen dataclass with `symbol`, `side`, `shares`)
instead of `dict[str, float]`. The orphan loop handles BOTH directions:
ARGUS-orphan (preserved existing behavior) and broker-orphan. Broker-orphan
with `side == OrderSide.SELL` (phantom short) emits
`SystemAlertEvent(alert_type="phantom_short")` and engages a per-symbol entry
gate that blocks `OrderApprovedEvent` for that symbol until the broker
reconciles to zero shares.

**Rationale:** DEF-204 forensic analysis (IMPROMPTU-11) identified that the
pre-31.91 reconciliation contract stripped `Position.side` at the call site
(`main.py:1520-1531` used `getattr(pos, "shares", 0)` returning unsigned
shares), making it structurally impossible for `reconcile_positions` to
distinguish a long-orphan from a phantom-short. The contract refactor flows
side end-to-end so the orphan loop can branch correctly. Per-symbol entry gate
prevents new entries from compounding an existing phantom short while
operator dispositions the alert.

**Alternatives considered:**
- Add `Position.broker_side: OrderSide` field. Rejected — `Position.side`
  already exists at `argus/models/trading.py:160` and is correctly populated;
  adding `broker_side` would be redundant.
- Use `tuple[OrderSide, int]` instead of a named dataclass. Rejected —
  positional destructuring is a silent-bug class (RULE-042-adjacent).
- Keep abs-value contract; add side-aware logic inside `reconcile_positions`.
  Rejected — fixes the symptom but leaves the side-stripped data flow intact;
  any future caller of the function would still get unsigned data.

**Scope (6 sessions, post 2nd revision):** 2a (typed-contract refactor),
2b.1 (broker-orphan SHORT branch + `phantom_short` alert +
`_broker_orphan_long_cycles` lifecycle), 2b.2 (three side-aware sites:
margin-circuit reset + Risk Manager max-concurrent-positions check +
EOD Pass 2 short detection alert + Health daily integrity check),
2c.1 (per-symbol entry gate state + handler + SQLite persistence per
M5), 2c.2 (5-cycle clear-threshold per M4 cost-of-error asymmetry; was
3 in original plan), 2d (operator override API + audit-log per M3 +
always-fire-both-alerts per L3 + runbook). Companion to DEC-386
(OCA-group threading + broker-only paths safety) and DEC-388 (alert
observability resolving DEF-014).

**Cross-references:** DEC-369; DEC-370; DEC-367 (per-symbol gate pattern
mirror); DEC-388 (alert observability — `phantom_short` alerts surface
through this sprint's new HealthMonitor consumer + WebSocket + REST + UI);
DEF-204; RSK-DEF-204; IMPROMPTU-11 mechanism diagnostic.
```

### B5. docs/decision-log.md — DEC-386 entry

**Append:**

```markdown
## DEC-386 — OCA-group threading on bracket children + standalone SELLs (Sprint 31.91)

**Date:** [Sprint 31.91 close date]
**Status:** Active
**Family:** DEC-117 (atomic bracket orders)

**Decision:** Every bracket placed by `IBKRBroker.place_bracket_order` sets
`ocaGroup` (per-bracket ULID) + `ocaType=1` ("Cancel with block") on the stop,
T1, and T2 children. The bracket's `oca_group_id` is threaded through
`ManagedPosition.oca_group_id` and read by `_trail_flatten`,
`_escalation_update_stop`, and `_resubmit_stop_with_retry` so all SELL Orders
for one ARGUS position carry the same `ocaGroup`. IBKR's matching engine
cancels redundant siblings atomically when one fills.

**Rationale:** DEF-204 forensic analysis (IMPROMPTU-11 H1+H7, ~98% of blast
radius) identified that bracket children placed via `parentId` only had
race-prone implicit OCA-like behavior, and that standalone SELL orders from
trail/escalation/resubmit-stop paths shared no OCA group with bracket children.
Multi-leg fill races produced 14,249 unexpected short shares across 44 symbols
on Apr 24 paper trading. Explicit OCA grouping closes the race window at the
broker level rather than relying on async cancel propagation from ARGUS.

**Alternatives considered:**
- Continue relying on IBKR's `parentId` implicit OCA. Rejected — empirically
  loose in IBKR paper trading per IMPROMPTU-11.
- Use `ocaType=2` ("Reduce with block") instead of 1. Rejected — ocaType=2's
  reduce-quantity semantics would mean a T1 partial fill silently reduces
  T2's remaining quantity. ARGUS's bracket model places T1 and T2 at
  distinct full-quantity price targets, so quantity-reduction on partial
  fills is wrong. Native IBKR `parentId` linkage handles partial-fill
  T2-stays-alive orthogonally; ocaType=1 adds atomic cancellation when an
  OCA member fills FULLY (not partially). The two mechanisms are
  orthogonal and complementary.
- Use `ocaType=3` ("Reduce, no block"). Rejected — non-blocking
  cancellation reintroduces the race window the fix is supposed to close.
- Synchronous cancel-then-place for trail/escalation paths (no OCA). Rejected
  — adds latency to every exit decision; doesn't close the race window
  reliably.
- Make `bracket_oca_type` config accept 1/2/3. Rejected — operator footgun
  on a safety-critical setting. Config accepts only 0 (disabled, rollback
  escape hatch) or 1 (on, default).

**Scope (4 sessions):** Sessions 0 (`Broker.cancel_all_orders(symbol,
await_propagation)` API extension with `CancelPropagationTimeout`
exception), 1a (bracket OCA + Error 201/OCA-filled defensive handling
on T1/T2 placement per Phase A spike `PATH_1_SAFE` finding), 1b
(standalone-SELL OCA threading across 4 paths including
`_flatten_position` + Error 201/OCA-filled graceful handling on these
paths), 1c (broker-only paths safety: `_flatten_unknown_position`,
`_drain_startup_flatten_queue`, `reconstruct_from_broker()` use
`cancel_all_orders(symbol, await_propagation=True)` to clear stale OCA
siblings; `reconstruct_from_broker()` gains contract docstring per B3
flagging the function as STARTUP-ONLY today and requiring
context-awareness for any future caller). Companion to DEC-385
(side-aware reconciliation contract).

**Cross-references:** DEC-117; DEC-364 (`cancel_all_orders` ABC, extended
in Session 0); DEC-372 (stop retry caps — preserved unchanged); DEC-388
(alert observability — Sprint 31.91's bracket / standalone-SELL /
broker-only paths emit `phantom_short` and `cancel_propagation_timeout`
alerts that surface through the new HealthMonitor consumer chain);
DEF-204; RSK-DEF-204; IMPROMPTU-11 mechanism diagnostic.
```

### B5.5. docs/decision-log.md — DEC-388 entry (NEW; alert observability)

**Append:**

```markdown
## DEC-388 — Alert observability architecture (Sprint 31.91)

**Date:** [Sprint 31.91 close date]
**Status:** Active
**Family:** none — first formal alert-observability decision; supersedes
DEF-014's "TODO: wire emitters" placeholders.

**Decision:** `HealthMonitor` (`argus/core/health.py`) is the canonical
consumer of `SystemAlertEvent` emissions. It maintains active-alert
state in-memory + SQLite-backed (`alert_acknowledgment_audit` table in
`data/operations.db`) for restart recovery, and exposes that state via:
- `GET /api/v1/alerts/active` — current state (initial-load + WebSocket
  reconnect recovery)
- `GET /api/v1/alerts/history?since=<ts>` — historical alerts
- `POST /api/v1/alerts/{alert_id}/acknowledge` — operator
  acknowledgment with audit-log entry
- `WS /ws/v1/alerts` — real-time fan-out of state changes

Alert lifecycle: `active` → `acknowledged` → (auto-resolved on
condition-cleared) → `archived`. Auto-resolution on
condition-cleared is opt-in per severity via
`alerts.acknowledgment_required_severities` config.

The frontend (`frontend/src/hooks/useAlerts.ts`) subscribes to the
WebSocket with TanStack Query as an initial-state + reconnect-recovery
layer. UI surfaces:
- `AlertBanner` mounted at Layout level → visible across all 10
  Command Center pages while any critical alert is active
- `AlertToast` mounted at Layout level → pops up on any page when new
  critical alert arrives; queues if multiple
- Observatory alerts panel → active + historical view with sort /
  filter / acknowledgment audit trail

**Rationale:** DEF-014 had been open since the initial alerting work
identified the consumer-side gap. The Sprint 31.91 phantom-short alerts
(DEC-385) are by definition critical safety events that need to reach
the operator within seconds, not via log-grep. Rather than ship 31.91
with a CLI-tool stop-gap and defer the proper UI to a follow-on sprint,
the operator chose to fold the entire alert-observability resolution
into 31.91 (Sessions 5a–5e). This produces a single live-enable gate
with no "wait for another sprint" caveats.

**Alternatives considered:**
- Keep DEF-014 deferred; ship Sprint 31.91 with a CLI-tool stop-gap
  (`scripts/poll_critical_alerts.py`). Rejected — the CLI tool is a
  workaround that operator would have to remember to run. The reviewer's
  framing was right: an alert that says you have unbounded short
  exposure should be impossible to miss.
- Resolve DEF-014 in a separate post-Sprint-31.91 sprint. Rejected on
  end-to-end timeline: option (1) Sprint 31.91 5–6 weeks +
  follow-on sprint 3–4 weeks = 8–10 weeks total; option (4) Sprint
  31.91 7–8 weeks (all work) = 7–8 weeks total. (4) is shorter
  end-to-end + removes cross-sprint context switching + yields a
  single live-enable gate.
- Use Server-Sent Events (SSE) instead of WebSocket. Rejected — ARGUS
  already has WebSocket fan-out infrastructure for Arena and
  Observatory streams; reusing the pattern reduces operational
  complexity.
- Wire IBKR emitter TODOs but defer Alpaca emitter TODO. Accepted —
  Alpaca emitter at `argus/data/alpaca_data_service.py:593` gets
  resolved by deletion in Sprint 31.94 (Alpaca retirement). Wiring it
  in 31.91 would be 3 weeks of lifespan for throwaway code.

**Scope (6 sessions, post 3rd revision):** Sessions 5a.1 (HealthMonitor
consumer + REST endpoints + acknowledgment flow with atomic + idempotent
transitions per third-pass MEDIUM #10), 5a.2 (WebSocket fan-out + SQLite
persistence + restart recovery + per-alert-type auto-resolution policy
table per third-pass HIGH #1 + retention/migration framework per
third-pass MEDIUM #9), 5b (IBKR emitter TODOs at `:453` and `:531`
resolved + end-to-end integration tests + behavioral anti-regression
test for Alpaca emitter per third-pass MEDIUM #13; Alpaca emitter
explicitly excluded), 5c (frontend `useAlerts` hook + Dashboard
banner), 5d (toast + acknowledgment UI flow), 5e (Observatory alerts
panel + cross-page integration via Layout-level mounting). Companion
to DEC-385 (provides the `phantom_short` alerts that this architecture
surfaces) and DEC-386 (provides the `cancel_propagation_timeout`
alerts).

**Cross-references:** DEF-014 (CLOSED by this DEC); DEC-385 (provides
phantom_short emitters); DEC-386 (provides cancel_propagation_timeout
emitters); IBKR emitter TODOs at `argus/execution/ibkr_broker.py:453`
and `:531` (resolved by Session 5b); Alpaca emitter TODO at
`argus/data/alpaca_data_service.py:593` (explicitly NOT resolved in
this sprint; resolved by deletion in Sprint 31.94).
```

### B6. docs/dec-index.md

**Append:**

```markdown
- ● **DEC-385**: Side-aware reconciliation contract — `dict[str,
  ReconciliationPosition]` (symbol, side, shares); broker-orphan branch with
  phantom-short alert + per-symbol entry gate; consumes existing `Position.side`.
- ● **DEC-386**: OCA-group threading — explicit `ocaGroup` + `ocaType=1` on
  bracket children + standalone SELL paths (trail-flatten, escalation-stop,
  resubmit-stop, _flatten_position); threaded via `ManagedPosition.oca_group_id`;
  broker-only paths use `cancel_all_orders(symbol, await_propagation=True)`.
- ● **DEC-388**: Alert observability architecture — HealthMonitor consumer +
  WebSocket fan-out (`/ws/v1/alerts`) + REST endpoints
  (`/api/v1/alerts/active|history|{id}/acknowledge`) + audit-log persistence;
  frontend `useAlerts` hook + Layout-level banner + toast + Observatory panel.
  Resolves DEF-014.
```

### B7. docs/sprint-history.md — Sprint 31.91 entry

**Append:** Full sprint entry with sessions 0, 1a, 1b, 1c, 2a, 2b.1,
2b.2, 2c.1, 2c.2, 2d, 3, 4, 5a.1, 5a.2, 5b, 5c, 5d, 5e (18 sessions); test
deltas (~+102 pytest, +34 Vitest); key decisions (DEC-385, DEC-386,
DEC-388); paper-session evidence; **DEF-014 marked CLOSED**;
**DEF-204 marked CLOSED**; new DEFs filed: DEF-208 (SimulatedBroker OCA
semantics), DEF-209 (analytics historical-record side preservation).

### B8. docs/risk-register.md — RSK-DEF-204 transition

**Find:** the RSK-DEF-204 entry at line 1037.

**Replace `Status` field:** `**OPEN — mitigation in effect; fix scoped and
scheduled.**` → `**CLOSED — Sprint 31.91 (DEF-204 fix) sealed [date]. Final
paper-session debrief confirmed zero phantom-short accumulation. Live trading
consideration unblocked pending 3-paper-session evidence accumulation per
DISCOVERY.**`

### B9. docs/architecture.md — DEF-204 callout update

**Find:** the DEF-204 callout block at `docs/architecture.md:855`.

**Replace:** `> **Known issue (DEF-204, identified Apr 24, 2026 — IMPROMPTU-11
mechanism diagnostic).**...` → A CLOSED reference:

```markdown
> **Resolved (DEF-204, closed in Sprint 31.91, [date]).** The
> bracket-children OCA-race + standalone-SELL no-OCA mechanism (DEC-386), the
> side-blind reconciliation contract (DEC-385), and the DEF-158 retry side-blind
> path (mirrors IMPROMPTU-04 3-branch) are all addressed. Bracket children
> carry explicit `ocaGroup` + `ocaType=1`; standalone SELL paths thread the
> same OCA group via `ManagedPosition.oca_group_id`; reconciliation flows
> typed `ReconciliationPosition` with `side` end-to-end and emits
> `SystemAlertEvent(alert_type="phantom_short")` + engages a per-symbol entry
> gate on broker-orphan-short detection; DEF-158 retry rejects phantom-short
> SELLs with ERROR + alert. See `docs/sprints/sprint-31.91-reconciliation-drift/`
> for full sprint detail.
```

### B10. docs/architecture.md — §3.7 Order Manager refresh

Add a new sub-section under §3.7:

```markdown
**Sprint 31.91 additions (DEF-204 fix):**
- `ManagedPosition.oca_group_id: str | None` — populated when position is
  created from a bracket entry fill; threaded through trail-flatten,
  escalation-stop, and resubmit-stop paths so all SELL orders for one
  position share the same IBKR OCA group.
- `ReconciliationPosition` frozen dataclass replaces the old `dict[str, float]`
  reconciliation contract; flows `side` + `shares` end-to-end.
- Broker-orphan branch in `reconcile_positions` orphan loop: emits
  `SystemAlertEvent(alert_type="phantom_short")` and engages per-symbol entry
  gate on phantom-short detection. Independent flags: `broker_orphan_alert_enabled`,
  `broker_orphan_entry_gate_enabled`.
- `_check_flatten_pending_timeouts` 3-branch side-check: BUY → flatten; SELL →
  ERROR + skip + alert; unknown → ERROR + skip. Mirrors IMPROMPTU-04 EOD
  Pass 1/2 fix shape.
```

### B11. docs/architecture.md — §3.3c IBKRBroker refresh

Add a brief note:

```markdown
**Sprint 31.91 additions:** `place_bracket_order` sets explicit `ocaGroup`
(per-bracket ULID) + `ocaType=1` on the stop, T1, and T2 children.
Configurable via `ibkr.bracket_oca_type` (default 1).
```

### B12. docs/project-knowledge.md — Sprint 31.91 closeout reference

**Find:** the "Active sprint" section.

**Replace:** Move 31.91 from "Active sprint" to closed; mark 31.92 as the next
active sprint per build-track queue.

### B13. docs/project-knowledge.md — Active Constraints update

**Append to Active Constraints:**

```markdown
- **OCA-grouping on bracket children (Sprint 31.91 DEC-386):**
  `ibkr.bracket_oca_type: 1` (default). Bracket children + standalone-SELL
  paths share an explicit OCA group; setting `bracket_oca_type: 0` reverts to
  pre-31.91 behavior (race-prone, not safe — escape hatch only).
- **Phantom-short detection (Sprint 31.91 DEC-385):**
  `reconciliation.broker_orphan_alert_enabled: true` (default). When broker
  has a SELL position ARGUS doesn't track, emits
  `SystemAlertEvent(alert_type="phantom_short", severity="critical")`.
- **Phantom-short entry gate (Sprint 31.91 DEC-385):**
  `reconciliation.broker_orphan_entry_gate_enabled: true` (default). When
  phantom short is detected, blocks new entries for that symbol until broker
  reconciles to zero. Independent of alert flag.
```

### B14. docs/roadmap.md — Build-track queue update

**Find:** the build-track queue's first entry (currently sprint-31.91).

**Update:** Mark 31.91 as completed; promote 31.92 to "next planned".

### B15. docs/pre-live-transition-checklist.md — Confirm new flags + live-enable gate criteria

**Note:** Session 4 delivers the live-enable gate criteria as part of in-sprint
work, not at sprint close. This doc-sync item only verifies the flag-default
section; the criteria section is already in the file before the doc-sync runs.

**Append a section verifying:**
- `ibkr.bracket_oca_type: 1` in production config
- `reconciliation.broker_orphan_alert_enabled: true` in production config
- `reconciliation.broker_orphan_entry_gate_enabled: true` in production config
- `reconciliation.broker_orphan_consecutive_clear_threshold: 3` in production config

### B16. CLAUDE.md DEF table — DEF-204 closure citation

Update the DEF-204 row in CLAUDE.md's DEF table to mark CLOSED with citation
to Sprint 31.91 + DEC-385 + DEC-386.

### B17. CLAUDE.md DEF table — DEF-208 entry (NEW)

**Append (in DEF table appropriate location):**

```markdown
| **DEF-208** | OPEN | SimulatedBroker should simulate OCA-group cancellation semantics matching ocaType=1 to align backtest fill behavior with live. Until then, post-31.91 backtest T2-hit rates are upper bounds — strategies whose backtests show high T2-hit rates will likely underperform live. Track in roadmap.md as Sprint 35+ Learning Loop V2 prerequisite (since Learning Loop V2 consumes backtest data). | Sprint 31.91 (filed at close per Adversarial Review Finding #8) |
```

### B18. CLAUDE.md DEF table — DEF-209 entry (NEW)

**Append:**

```markdown
| **DEF-209** | OPEN | `analytics/debrief_export.py` and any other historical-record writers must preserve `Position.side` to support side-aware Learning Loop V2 promotion/demotion decisions. Today the export records `Position.shares` (abs) without side; if Learning Loop V2 (Sprint 35+) consumes this data, it can misattribute trade direction. Required before Learning Loop V2 begins consuming historical debrief data. | Sprint 31.91 (filed at close per Adversarial Review Finding #10) |
```

### B19. docs/architecture.md — §3.3 Broker Abstraction (cancel_all_orders signature)

**Find** in `### 3.3 Broker Abstraction (`execution/broker.py`)`:
```
    async def cancel_all_orders(self) -> int:
```

**Replace with:**
```
    async def cancel_all_orders(self, symbol: str | None = None) -> int:
```

Plus add 1 sentence after the interface block:

> **Sprint 31.91 extension (Session 0, DEC-386):** `cancel_all_orders`
> accepts an optional `symbol` parameter. When provided, only that symbol's
> working orders are cancelled. When `None`, preserves DEC-364 contract
> (cancel everything). Used by Sessions 1c and 4 to clear stale OCA
> siblings before placing SELL orders on broker-only paths.

### B20. docs/architecture.md — §3.7 Order Manager (DEF-204 callout becomes CLOSED)

**Find** the DEF-204 known-issue callout block (search for `**Known issue
(DEF-204`).

**Replace with a CLOSED reference:**

> **DEF-204 (CLOSED in Sprint 31.91, 2026-XX-XX).** The bracket-children OCA
> race + standalone-SELL no-OCA mechanism, the side-blind reconciliation
> contract, and the DEF-158 retry side-blind path were all closed by
> Sprint 31.91's 18-session fix (DEC-385 + DEC-386 + DEC-388). Operator
> daily-flatten mitigation is no longer load-bearing; live-trading
> consideration unblocked per pre-live-transition-checklist.md gate
> criteria. See
> `docs/sprints/sprint-31.91-reconciliation-drift/SPRINT-31.91-SUMMARY.md`
> for the full closure trace.

### B20.5. docs/architecture.md — §14 Alert Observability (NEW SECTION; added at sprint close)

**Action:** Add a new top-level section titled "§14 Alert Observability"
to `docs/architecture.md`. Position after §13 (Observatory).

**Content (skeleton — final form filled in during sprint-close doc-sync):**

```markdown
## §14 Alert Observability (Sprint 31.91, DEC-388)

`SystemAlertEvent` is the canonical safety-critical event type emitted
by ARGUS components when an operator should be notified. The
observability pipeline is:

1. **Emitter** — any component publishing `SystemAlertEvent` to the
   Event Bus. Existing emitter sites:
   - `argus/data/databento_data_service.py` (dead-feed detection,
     pre-existing)
   - `argus/execution/ibkr_broker.py:453` (Gateway disconnect /
     reconnect failure, Sprint 31.91 Session 5b)
   - `argus/execution/ibkr_broker.py:531` (API auth / permission
     failure, Sprint 31.91 Session 5b)
   - `argus/execution/order_manager.py` (phantom_short branch +
     phantom_short_retry_blocked + cancel_propagation_timeout +
     stranded_broker_long, Sprint 31.91 Sessions 2b/3/1c)
   - `argus/core/health.py` (Health daily integrity check phantom_short
     side-aware emission, Sprint 31.91 Session 2b.2)
   - `argus/data/alpaca_data_service.py:593` — TODO unresolved by
     design; resolved by deletion in Sprint 31.94 (Alpaca retirement).

2. **Consumer** — `argus/core/health.py::HealthMonitor`. Subscribes to
   `SystemAlertEvent` on the Event Bus. Maintains active-alert state
   in-memory + SQLite-backed (`alert_acknowledgment_audit` table) for
   restart recovery.

3. **Surfaces** — three customer-facing surfaces:
   - REST: `GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`,
     `POST /api/v1/alerts/{alert_id}/acknowledge`
   - WebSocket: `WS /ws/v1/alerts` real-time fan-out
   - Frontend: `useAlerts` hook + `AlertBanner` (Layout-level) +
     `AlertToast` (Layout-level) + Observatory alerts panel

4. **Lifecycle:** `active` → `acknowledged` (operator action via REST) →
   (auto-resolved on condition-cleared) → `archived`. Auto-resolution
   on condition-cleared is per-severity opt-in via
   `alerts.acknowledgment_required_severities` config.

5. **Reference pattern for new emitters:** publish `SystemAlertEvent`
   with appropriate severity. The HealthMonitor consumer auto-discovers
   the new alert type. No emitter-side observability wiring needed
   beyond the publish call.

Resolves DEF-014.
```

**Anti-regression note:** Alpaca emitter site at
`argus/data/alpaca_data_service.py:593` is intentionally listed as
"TODO unresolved by design" — Sprint 31.94 retires Alpaca by deletion.
Session 5b's `test_alpaca_emitter_site_unchanged` test asserts the TODO
comment is still present at `:593` post-31.91.

### B21. docs/protocols/market-session-debrief.md — Phase 7 slippage watch item (added by Session 4)

**Note:** This is delivered IN-SPRINT (Session 4), not at sprint close.
This doc-sync item only verifies the addition is present.

**Verify:** `docs/protocols/market-session-debrief.md` Phase 7 (Synthesis)
section contains a watch item:

> **Bracket-stop slippage check (Sprint 31.91 D8 acceptance criterion):**
> compare mean slippage on bracket-stop fills vs pre-31.91 baseline; flag
> if mean degrades by >$0.02 on $7–15 share price universe. Triggers
> evaluation of `bracket_oca_type: 0` rollback (preserves Session 1b
> standalone-SELL OCA threading while disabling bracket-children OCA).

### B22. docs/live-operations.md — Phantom-short runbook (added by Session 2d)

**Note:** Session 2d delivers this section IN-SPRINT, not at sprint close.
This doc-sync item only verifies it exists.

**Verify:** `docs/live-operations.md` contains a section titled
"Phantom-Short Gate Diagnosis and Clearance" with subsections:
- **Symptom:** ARGUS startup logs CRITICAL line listing N gated symbols
- **Diagnosis steps:** check broker positions; check
  `_phantom_short_gated_symbols`
- **Clearance options:**
  (a) Run `scripts/ibkr_close_all_positions.py` then wait 5
      reconciliation cycles (was 3 — updated per M4 cost-of-error
      asymmetry); (b) `POST
      /api/v1/reconciliation/phantom-short-gate/clear` with
      `{"symbol": "...", "reason": "..."}`; (c) UI: navigate to
      Observatory alerts panel, click acknowledgment on the
      `phantom_short` alert (Sessions 5d/5e deliver the UI surface)
- **Audit-log location:** `phantom_short_override_audit` table in
  `data/operations.db` (M3 schema:
  `(timestamp_utc, timestamp_et, symbol, prior_engagement_source,
  prior_engagement_alert_id, reason_text, override_payload_json)`).
- **Persistence:** entries survive ARGUS restart. Querying after restart
  returns the entry with full payload.
- **Aggregate alert tuning** (per third-pass LOW #15): the threshold at
  which the aggregate `phantom_short_startup_engaged` alert fires
  alongside per-symbol alerts is configurable via
  `reconciliation.phantom_short_aggregate_alert_threshold` (default
  `10`). Operators should tune based on observed phantom-short volume:
  high-volume operators may raise to 20+ to reduce noise; low-volume
  operators (post-fix steady state) may lower to 5 to catch any
  resurgence early.

### B22.5. docs/live-operations.md — Restart-required rollback note (added by Session 1a; per H1)

**Note:** Session 1a delivers this section IN-SPRINT (alongside
`bracket_oca_type` config introduction).

**Verify:** `docs/live-operations.md` contains a section titled "Bracket
OCA Rollback (RESTART-REQUIRED)" stating:

> **`ibkr.bracket_oca_type: 0`** disables bracket-children OCA grouping,
> restoring pre-Sprint-31.91 behavior on the bracket side. Standalone-SELL
> OCA threading (DEC-386 Session 1b) is independent and remains active.
>
> **Mid-session config flip is NOT supported.** Flipping `bracket_oca_type`
> while ARGUS is running produces an inconsistent cohort of in-flight
> positions: existing bracket children carry the old `ocaType` value at the
> broker, while new bracket placements use the new value.
>
> **Correct rollback procedure:**
> 1. Halt ARGUS via standard shutdown.
> 2. Edit `system_live.yaml` (or active config) to set
>    `ibkr.bracket_oca_type: 0`.
> 3. Restart ARGUS. `reconstruct_from_broker()` rehydrates positions from
>    the broker; the new config applies uniformly to subsequent bracket
>    placements.
> 4. Operator daily-flatten mitigation should be re-enabled until the
>    rollback condition is resolved.
>
> Triggered by post-merge slippage debrief: mean bracket-stop fill slippage
> degrades by >$0.02 on $7–15 share universe (Session 4 acceptance
> criterion).

### B23. docs/live-operations.md — Alert acknowledgment runbook (added by Session 5a)

**Note:** Session 5a delivers this section IN-SPRINT, not at sprint close.
This doc-sync item only verifies it exists.

**Verify:** `docs/live-operations.md` contains a section titled "Alert
Acknowledgment Runbook" with subsections:
- **Where alerts surface:** Dashboard banner (any active critical alert);
  toast notification on any page when a new critical alert arrives;
  Observatory alerts panel (active + historical view).
- **How to acknowledge:** click the acknowledgment button in any of the
  three surfaces; modal opens; provide reason text; submit.
- **What acknowledgment does:** writes audit-log entry to
  `alert_acknowledgment_audit` table; updates alert state to
  `acknowledged`; banner / toast disappears within 1s.
- **Auto-resolution:** alerts auto-resolve when underlying condition
  clears (e.g., `phantom_short` for symbol X resolves after broker
  reconciles to zero shares for X for 5 cycles). No operator action
  needed in this case; UI updates within 1s.
- **Restart recovery:** if ARGUS restarts while alerts are active,
  HealthMonitor rehydrates alert state from SQLite.
  `GET /api/v1/alerts/active` returns the rehydrated state. Frontend
  recovers via WebSocket reconnect + `useAlerts` REST refetch.
- **Audit-log query:** `SELECT * FROM alert_acknowledgment_audit ORDER BY
  timestamp_utc DESC LIMIT 50;` against `data/operations.db`.

### B24. CLAUDE.md DEF table — DEF-014 marked CLOSED

**Find:** the DEF-014 row in the CLAUDE.md DEF table (search for
`DEF-014`).

**Replace `Status` field:** OPEN → `CLOSED — Sprint 31.91 (DEC-388,
Sessions 5a–5e). HealthMonitor consumer + WebSocket fan-out + REST
endpoint + acknowledgment flow + Dashboard banner + toast +
Observatory alerts panel + cross-page integration delivered. See
docs/decision-log.md DEC-388.`

**Anti-regression:** verify the Alpaca emitter TODO at
`argus/data/alpaca_data_service.py:593` is **NOT** included in the
DEF-014 closure scope. Sprint 31.94 (Alpaca retirement) resolves that
TODO by deletion.

### B25. CLAUDE.md DEF table — DEF-204 marked CLOSED

**Find:** the DEF-204 row in the CLAUDE.md DEF table.

**Replace `Status` field:** OPEN → `CLOSED — Sprint 31.91 (DEC-385 +
DEC-386, Sessions 0–4). 18-session fix; bracket OCA + standalone-SELL
OCA + broker-only safety + side-aware reconciliation + per-symbol entry
gate + DEF-158 retry side-check + mass-balance categorized + IMSR replay.
3+ paper sessions zero unaccounted_leak; live-trading consideration
unblocked.`

### B26. CLAUDE.md DEF table — new DEFs filed at sprint close

**Append to DEF table:**

```markdown
| DEF-208 | OPEN | execution | SimulatedBroker should simulate OCA-group cancellation semantics matching ocaType=1 to align backtest fill behavior with live. Until resolved, post-31.91 backtest T2-hit rates are upper bounds. Spike script `scripts/spike_ibkr_oca_late_add.py` partially mitigates for OCA mechanism specifically. |
| DEF-209 | OPEN | analytics | `analytics/debrief_export.py` and other historical-record writers must preserve `Position.side` to support side-aware Learning Loop V2. |
| DEF-210 | OPEN | api | `POST /api/v1/system/suspend` endpoint to allow live-rollback policy automation per third-pass HIGH #4. Live-enable gate criterion 3b currently uses operator-manual halt as fallback; DEF-210 makes this automatable on `phantom_short*` or `phantom_short_retry_blocked` alert during the first-day-live window. |
| DEF-211 | OPEN | observability | Side-aware breakdown in post-flatten verification log line at `order_manager.py:1729` per third-pass LOW #14. Current "Remaining symbols: [...]" log conflates EOD-flatten failures with phantom-short residue. Not safety-critical (informational only, no order placed); operator-experience improvement. |
```

### B27. docs/architecture.md — §13 Observatory refresh (alerts panel addition)

**Find:** §13 Observatory section header.

**Append after existing §13 content:**

> **Sprint 31.91 (DEC-388) addition:** Observatory page gains an alerts
> panel (active + historical view, sortable / filterable, acknowledgment
> audit trail visible per alert). See §14 Alert Observability for the
> full architecture.

### B28. docs/live-operations.md — Spike script trigger registry (PRE-Session-4 deliverable per third-pass HIGH #5)

**Note:** Session 4 delivers this section IN-SPRINT (alongside the
mass-balance script). Doc-sync only verifies presence. This section is
ALSO a Phase D prerequisite — see `escalation-criteria.md` §A13.

**Verify:** `docs/live-operations.md` contains a section titled "OCA
Late-Add Spike Script — Trigger Registry" with subsections:

> **Purpose:** `scripts/spike_ibkr_oca_late_add.py` is the live-IBKR
> regression check for the OCA-architecture seal (DEC-386). Sprint 31.91
> made the IBKR matching engine's OCA late-add behavior load-bearing on
> `PATH_1_SAFE` (rejection of late-add OCA siblings with Error 201 once
> any group member has filled). Without periodic re-validation, an IBKR
> API change or `ib_async` library upgrade could silently invalidate the
> seal.
>
> **Triggers (re-run the spike before the listed events):**
> - **Live-trading transition** — live-enable gate item; spike result
>   ≤30 days old required (regression invariant 22).
> - **`ib_async` library version upgrade** — both before (baseline) and
>   after (verify upgrade preserves behavior).
> - **IBKR API version change** (TWS / Gateway upgrade) — same
>   before/after pattern.
> - **Monthly during paper-trading windows** — calendar reminder; spike
>   result file dated within last 30 days.
>
> **Procedure:**
> 1. Verify IBKR Gateway is running on port 4002 (paper account
>    U24619949).
> 2. Run `python scripts/spike_ibkr_oca_late_add.py --output-dir
>    scripts/spike-results/`.
> 3. Inspect the produced `spike-results-YYYYMMDD.json` — verdict must
>    be `PATH_1_SAFE`.
> 4. Commit the result file (small JSON; not gitignored — historical
>    record).
>
> **Failure handling:**
> - `PATH_1_SAFE` → all good; record date for next re-run gate.
> - `PATH_2_RACE` (late-add same-batch siblings reject inconsistently)
>   → OCA-architecture seal degraded but not invalidated; Tier 3 review
>   to assess; rollback to `bracket_oca_type: 0` may be needed
>   (RESTART-REQUIRED per H1).
> - `PATH_3_LATE_FILL` (late-add post-fill submissions ACCEPTED — i.e.,
>   IBKR no longer rejects) → OCA-architecture seal INVALIDATED;
>   immediate halt of live trading; rollback to `bracket_oca_type: 0`
>   required; Tier 3 review of new mechanism behavior; possible Sprint
>   31.91-followup needed.
> - Connection errors → not a verdict; retry with verified Gateway
>   connectivity.

### B29. workflow metarepo — Frontend reviewer template (PRE-Session-5c prerequisite per third-pass HIGH #3)

**Note:** This update lives in the **`stevengizzi/claude-workflow`
metarepo**, not the ARGUS repo. It is a Phase D prerequisite — Session
5c cannot begin without it. See `escalation-criteria.md` §A11.

**Action:** Author `templates/review-prompt-frontend.md` in the
metarepo with the following structure:

```markdown
# Tier 2 @reviewer Prompt — Frontend Sessions

## When to use this template

Use this template instead of `templates/review-prompt.md` when the
session under review is a frontend-focused session:
- Touches `frontend/src/**` primarily
- Adds Vitest tests (not pytest)
- Implements UI components, hooks, page-level integrations, or
  layout-level mountings

For mixed sessions (frontend + backend), use BOTH templates and have
the reviewer alternate focus.

## Checklist (frontend-flavored)

The reviewer must verify each of the following:

### State machine completeness
- [ ] All states reachable from initial state
- [ ] No dead-end states (every state has a valid transition or
      terminal status)
- [ ] State transitions are deterministic (same input → same next state)
- [ ] Loading / error / empty / data states all handled

### Reconnect / disconnect resilience
- [ ] WebSocket disconnect is detected within bounded time
- [ ] On disconnect: graceful fallback (e.g., REST polling, cached state)
- [ ] On reconnect: state refetch + WebSocket resubscription
- [ ] No alerts / events lost in the disconnect window (via REST recovery)

### Acknowledgment race handling (when applicable)
- [ ] Double-click / rapid-fire request idempotency
- [ ] Two-tab race resolution (first-writer-wins or explicit conflict)
- [ ] Stale acknowledgment after auto-resolution (409 handling)

### Accessibility
- [ ] ARIA roles correct (button, dialog, alert, status)
- [ ] Keyboard navigation (Tab, Enter, Escape) functional
- [ ] Focus trap in modals; focus restoration on close
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader announcement order sensible

### Cross-page persistence (when applicable)
- [ ] Component mounted at Layout level, not page level
- [ ] State survives page navigation (visible across pages)
- [ ] No duplicate mount on rapid navigation
- [ ] State clears within 1s of underlying-condition change

### Z-index / layout interactions
- [ ] No overlap with existing UI elements at any breakpoint
- [ ] Stacking order correct under multiple-alert burst
- [ ] Mobile / narrow viewport considered

### Vitest coverage thresholds
- [ ] ≥90% line coverage for new components
- [ ] ≥80% branch coverage for new hooks
- [ ] All state transitions tested
- [ ] All error paths tested

## Reviewer entity

The frontend reviewer is **the same `@reviewer` Tier 2 subagent** used
for backend safety reviews, but invoked with this template instead of
the backend-flavored one. The session implementation prompt flags which
template applies. Operator selects the template at session-kickoff time.
```

**Verify (post-author):** `git ls-files` in the metarepo shows
`templates/review-prompt-frontend.md` exists; commit message references
Sprint 31.91 HIGH #3.

---

## Phase B Doc-Sync Session Outline

The follow-on doc-sync session uses this prompt structure:

1. Pre-flight: clone fresh ARGUS repo to ensure operations target current
   `main` HEAD.
2. Read this Doc Update Checklist (Phase B section, items B1–B29).
3. For each B1–B29 item, grep-verify the FIND target exists, apply the
   surgical patch, verify post-condition.
4. Items B22, B22.5, B23, B28 are IN-SPRINT deliverables; doc-sync only
   verifies they're present. Items B24–B26 close DEF-014 + DEF-204 in
   CLAUDE.md and file DEF-208/209/210/211. Item B29 lives in the
   workflow metarepo (separate commit).
5. Run pytest + Vitest smoke test (no functional changes; should pass with
   zero delta).
6. Commit the doc updates as a single commit:
   `docs(sprint-31.91): post-sprint doc-sync — DEF-204 + DEF-014 CLOSED, DEC-385/386/388 added,
   architecture §14 alert observability + risk + project-knowledge updated, DEF-208/209/210/211 filed,
   spike-script trigger registry + alert acknowledgment runbook present`.
7. Tier 2 review (reviewer-writes-file pattern).
8. Separate metarepo commit (B29) by operator before Session 5c.

---

## Verification Grep Commands

After Phase A patches:
```bash
grep -rn 'post-31\.9-' docs/ CLAUDE.md \
  --exclude-dir=sprint-31.9 \
  --exclude-dir=synthesis-2026-04-26 \
  --exclude-dir=audits \
  | grep -v 'renamed from post-31\.9' \
  | wc -l    # should be 0
```

After Phase B doc-sync:
```bash
grep -c 'DEF-204' CLAUDE.md docs/decision-log.md docs/dec-index.md docs/risk-register.md docs/architecture.md
# Each should show DEF-204 in CLOSED context, not OPEN

grep -c 'DEF-014' CLAUDE.md docs/decision-log.md docs/dec-index.md docs/architecture.md
# Each should show DEF-014 in CLOSED context, not OPEN

grep -c 'DEC-385\|DEC-386\|DEC-388' docs/decision-log.md docs/dec-index.md docs/architecture.md
# Should show entries in all three files for all three DECs

grep -c 'DEF-208\|DEF-209' CLAUDE.md
# Should show DEF-208 and DEF-209 newly filed in CLAUDE.md DEF table
```

---

*End Sprint 31.91 Doc Update Checklist (revised 3rd pass — 18-session shape;
DEF-014 fully resolved; DEC-388 alert observability added; B22.5 + B23 +
B24–B27 + B28 + B29 added; DEF-210 + DEF-211 filed).*
