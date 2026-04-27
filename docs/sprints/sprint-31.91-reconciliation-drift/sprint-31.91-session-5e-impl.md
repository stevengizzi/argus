# Sprint 31.91, Session 5e: Observatory Alerts Panel + Cross-Page Integration

> **Track:** Alert Observability Frontend (Session 5c → 5d → **5e**). Final session of the sprint.
> **Position in sprint:** Last implementation session. Closes Sprint 31.91. Adds the historical-alert browsing surface (Observatory panel) and relocates 5c's banner + 5d's toast stack to Layout level so they're visible across all 10 Command Center pages.
> **Reviewer:** **Frontend** (`templates/review-prompt-frontend.md`).

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md`.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - Sessions 5c + 5d deliverables (`useAlerts`, `AlertBanner`, `AlertToastStack`, `AlertAcknowledgmentModal`).
   - `frontend/src/pages/Observatory.tsx` — current page structure (alerts panel addition).
   - `frontend/src/components/Layout.tsx` — current layout (banner + toast cross-page mount; **read carefully**, this is the only structural mod across this sprint that touches Layout).
   - Existing data-table / filter patterns in frontend (e.g., trade log table). Reuse the patterns; don't introduce a new one.
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D13 + AC-D13 + D14 (sprint-close doc-sync).

3. Run baseline:

   ```
   pnpm vitest run
   ```

   Expected: green at Session 5d's count.

4. Branch: **`main`**.

## Objective

Three deliverables:

1. **Observatory alerts panel** — sub-component within `Observatory.tsx`. Active alerts (sortable, filterable). Historical alerts (date-range picker). Acknowledgment audit trail visible per alert. Click-through to detailed alert view.

2. **Cross-page mount of `AlertBanner` and `AlertToastStack` at Layout level** — relocate from `Dashboard.tsx`; remove the temporary mounts; mount in `Layout.tsx` so they persist across all 10 pages.

3. **Integration tests** — banner persistence across navigation; toast appearance on non-Dashboard pages.

## Requirements

### Observatory Alerts Panel

`frontend/src/components/AlertsPanel.tsx` (new):

```tsx
import { useState } from "react";
import { useAlerts, useAlertHistory, type Alert } from "../hooks/useAlerts";

export function AlertsPanel() {
  const { alerts: activeAlerts } = useAlerts();
  const [historyRange, setHistoryRange] = useState<{from: string; to: string}>(...);
  const { data: historyAlerts = [] } = useAlertHistory(historyRange);

  const [sortKey, setSortKey] = useState<"severity" | "source" | "symbol" | "emitted_at_utc">("emitted_at_utc");
  const [filterSeverity, setFilterSeverity] = useState<string | "all">("all");
  const [filterSource, setFilterSource] = useState<string | "all">("all");
  const [filterSymbol, setFilterSymbol] = useState<string>("");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const filteredActive = applyFilters(activeAlerts, {filterSeverity, filterSource, filterSymbol});
  const sortedActive = sortAlerts(filteredActive, sortKey);

  return (
    <div className="...">
      <h2>Alerts</h2>
      <div className="filters">{/* severity, source, symbol filters */}</div>
      <div className="active-section">
        <h3>Active ({sortedActive.length})</h3>
        <AlertsTable alerts={sortedActive} onSelectAlert={setSelectedAlert} sortKey={sortKey} onSortChange={setSortKey} />
      </div>
      <div className="history-section">
        <h3>History</h3>
        <DateRangePicker value={historyRange} onChange={setHistoryRange} />
        <AlertsTable alerts={historyAlerts} onSelectAlert={setSelectedAlert} sortKey={sortKey} onSortChange={setSortKey} />
      </div>
      {selectedAlert && (
        <AlertDetailView
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}
    </div>
  );
}
```

`useAlertHistory` is a NEW hook — extends 5c's `useAlerts` with date-range fetching:

```typescript
// In frontend/src/hooks/useAlerts.ts (extend, don't fork)
export function useAlertHistory(range: {from: string; to: string}) {
  return useQuery<Alert[]>({
    queryKey: ["alerts", "history", range.from, range.to],
    queryFn: () => fetch(`/api/v1/alerts/history?since=${range.from}&until=${range.to}`).then(r => r.json()),
  });
}
```

(If the backend's `/history` endpoint doesn't yet support `until` parameter, file as DEF-214 and extend in a follow-up; for 5e, use `since=<from>` only and filter `to` client-side.)

`AlertDetailView` shows full event payload + acknowledgment audit trail:

```tsx
function AlertDetailView({ alert, onClose }: { alert: Alert; onClose: () => void }) {
  const { data: auditTrail } = useQuery({
    queryKey: ["alert", alert.alert_id, "audit"],
    queryFn: () => fetch(`/api/v1/alerts/${alert.alert_id}/audit`).then(r => r.json()),
  });
  return (
    <div role="dialog" aria-modal="true" className="...">
      <h3>{alert.alert_type}</h3>
      <pre>{JSON.stringify(alert.metadata, null, 2)}</pre>
      <h4>Audit Trail</h4>
      {auditTrail?.map((entry, i) => (
        <div key={i}>
          {entry.timestamp_utc} · {entry.acknowledgment_outcome} · {entry.operator_id} · {entry.reason}
        </div>
      ))}
      <button onClick={onClose}>Close</button>
    </div>
  );
}
```

The `/api/v1/alerts/{id}/audit` endpoint needs to exist on the backend. **Verify in 5a.1 deliverables; if missing, extend 5a.1's router.** Per RULE-007, do NOT silently add a backend endpoint in a frontend session — file the gap and EITHER ship a follow-up impromptu OR halt and amend. Most likely: 5a.1 already has a way to query `alert_acknowledgment_audit` rows by `alert_id`; the GET endpoint is a thin wrapper that may or may not exist.

Check by running:

```bash
grep -n "alert_acknowledgment_audit\|/audit" argus/api/routes/alerts.py
```

If no GET endpoint exists, halt this session, file as a small fix-it task (likely 5-line addition to `argus/api/routes/alerts.py`), apply, then resume 5e.

### Layout-Level Mount (`frontend/src/components/Layout.tsx`)

Mount `AlertBanner` + `AlertToastStack` at the layout level. Remove the temporary mounts from `Dashboard.tsx`.

```tsx
// frontend/src/components/Layout.tsx
import { AlertBanner } from "./AlertBanner";
import { AlertToastStack } from "./AlertToastStack";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AlertBanner />
      <Header />
      <main>{children}</main>
      <Footer />
      <AlertToastStack />
    </>
  );
}
```

The exact structural location (before/after Header, etc.) depends on existing Layout's structure. Read the file. Banner SHOULD be at the very top of the visible area (above any header/nav) so it doesn't get visually buried; toast can be anywhere in the tree since it's positioned absolutely.

In `Dashboard.tsx`, REMOVE the temporary mounts added in Sessions 5c and 5d:

```tsx
// REMOVE these (Sessions 5c + 5d temporary mounts):
// <AlertBanner />
// <AlertToastStack />
```

### Doc-Sync (D14 — Sprint Close)

This session is the last implementation session. Per spec D14, sprint-close doc-sync includes:

- `CLAUDE.md` DEF table marks **DEF-014** as CLOSED with citation: `Resolved by Sprint 31.91 Sessions 5a.1 + 5a.2 + 5b + 5c + 5d + 5e + DEC-388 (alert observability decision, file at sprint-close)`.
- `docs/architecture.md` gains §14 (alert observability) describing the HealthMonitor consumer + WebSocket fan-out + REST endpoint architecture as a reference pattern for future emitters.
- `docs/decision-log.md` gains DEC-388 (Alert observability architecture, ARGUS's first multi-emitter observability subsystem; HealthMonitor as central consumer; per-alert-type auto-resolution policy table; SQLite-backed restart recovery; resolves DEF-014).
- `docs/dec-index.md` updates with DEC-388.

Doc-sync is a separate operational concern from this implementation session — file as a **doc-sync follow-up** to be performed after Tier 2 CLEAR + sprint-close-out lands. Reference: `.claude/skills/doc-sync.md` for the close-out skill.

## Tests (~8 new Vitest + 2 integration)

1. `Observatory alerts panel renders active alerts` — render Observatory; provide hook with active alerts; assert table rows.

2. `Observatory alerts panel renders historical alerts with date-range picker` — render; set date range; assert REST `/history?since=...` called; assert results rendered.

3. `Observatory alerts panel sort by severity / source / symbol` — render with mixed alerts; click each sort header; assert sort order. (Three assertions, can fold into a single test.)

4. `Observatory alerts panel filter by severity / source / symbol` — render; apply filters; assert filtered set.

5. `Observatory alerts panel acknowledgment audit trail visible per alert` — click alert row; modal opens; mock `/audit` endpoint; assert audit entries rendered.

6. `Observatory alerts panel click-through to detailed alert view` — click row; assert detail modal renders alert metadata + audit trail.

7. **Integration: `AlertBanner persists across page navigation Dashboard → TradeLog → Performance`** (regression invariant 17). Render `<App>`; emit critical alert; navigate Dashboard → TradeLog (via React Router); assert banner still visible; navigate to Performance; still visible. **This is the structural pin for cross-page mount.**

8. **Integration: `AlertToast appears on TradeLog page when new alert arrives`** — render; navigate to TradeLog; emit critical alert (post-mount); assert toast appears.

9. `AlertBanner clears within 1s on acknowledgment from any page` — render; navigate to TradeLog; emit critical; ack via banner; assert banner unmounted.

10. `AlertBanner clears within 1s on auto-resolution from any page` — same shape; trigger `alert_auto_resolved` WS message; assert unmounted.

**Coverage target:** ≥90%.

## Definition of Done

- [ ] `AlertsPanel.tsx` + `AlertDetailView` + `useAlertHistory` extension created.
- [ ] Active alerts: sortable + filterable.
- [ ] Historical alerts: date-range picker functional; REST `/history` consumed.
- [ ] Audit trail visible per alert (consumes `/alerts/{id}/audit` endpoint; verified to exist in 5a.1 OR extended).
- [ ] `AlertBanner` mounted at Layout level; visible all 10 pages.
- [ ] `AlertToastStack` mounted at Layout level.
- [ ] Temporary mounts in `Dashboard.tsx` removed.
- [ ] Banner cross-page persistence asserted (regression invariant 17).
- [ ] 8 component Vitest tests + 2 integration tests; all green.
- [ ] CI green; Vitest baseline ≥ Session 5d + 10.
- [ ] Tier 2 review (frontend reviewer template) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5e-closeout.md`.
- [ ] **Sprint close-out file** at `docs/sprints/sprint-31.91-reconciliation-drift/sprint-close-out.md` — produced by the work journal handoff process; this session's close-out only handles 5e itself.
- [ ] Doc-sync (D14) FILED as follow-up task; not performed in this session.

## Close-Out Report

Standard structure plus:

- **`/audit` endpoint verification:** state explicitly whether the endpoint existed in 5a.1 OR was added in this session. If added in this session, that's a scope expansion that needs explicit acknowledgment in the close-out (RULE-007 mandate).
- **Cross-page invariant verification:** describe the integration test approach — full `<App>` render with `MemoryRouter`, navigation calls, WebSocket message injection. State explicitly that test 7 is the regression pin for invariant 17.
- **Doc-sync filing:** DEC-388 + DEF-014 closure + architecture.md §14 listed as follow-up tasks.
- **Sprint completion:** this is the last implementation session. State that the sprint is now ready for sprint-close-out + Work Journal handoff.

```json
{
  "session": "5e",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 10,
  "vitest_coverage_pct": "<TBD>",
  "cross_page_invariant_17_verified": true,
  "audit_endpoint_existed_pre_5e": "<TBD>",
  "sprint_implementation_complete": true,
  "next_step": "operator runs work-journal-closeout; doc-sync to follow"
}
```

## Tier 2 Review Invocation

Frontend reviewer template.

Reviewer output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5e-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Layout-level mount doesn't break existing page layouts.** Reviewer renders each of the 10 Command Center pages (in dev OR in test) and verifies no visual regression from the banner being above the existing header. If the Layout was previously edge-to-edge, the banner pushes content down — confirm acceptable.

2. **Banner z-index and toast z-index don't conflict.** Reviewer reads CSS / Tailwind classes; sketches the layered z-stack. Banner `top: 0` (sticky); toast `top: 4 right: 4` (fixed); modal `inset-0` (fixed full-screen). All `z-50`. Last-renders-wins for same z; verify the modal-on-toast-on-banner ordering is correct.

3. **Observatory panel performance with large historical dataset.** If the operator queries 6 months of history with thousands of alerts, does the panel pagination handle it? For 5e this is acceptable to defer — file as DEF-215 (Observatory pagination polish) — but reviewer should confirm at least the table doesn't crash on 1000+ rows.

4. **Date-range picker UX.** Defaults to "last 7 days"? Or empty? Reviewer asks: what happens on first render with no range set? Default to last 7 days is a reasonable choice; if 5e renders an empty state, that's not wrong but should be documented.

5. **Cross-page integration tests reliable.** The integration tests use `MemoryRouter` + `renderWithProviders` (or equivalent). Reviewer verifies the test setup mirrors existing integration tests in the codebase, NOT a one-off custom harness.

6. **Doc-sync filing accurate.** Reviewer reads the close-out's "deferred to doc-sync" list; verifies DEC-388 + DEF-014 + architecture.md §14 are all listed.

7. **`/audit` endpoint scope.** If it was added in 5e (not pre-existing), reviewer flags the scope expansion explicitly in the verdict. Tier 2 may CLEAR with note OR raise CONCERNS depending on whether the addition was minimal.

## Sprint-Level Regression Checklist

- **Invariant 5:** PASS — expected ≥ Session 5d + 10.
- **Invariant 17 (banner cross-page persistence):** PASS — test 7 is the structural pin.
- **Invariant 14:** Final row "After Session 5e" — Alert observability = "FULL: backend + frontend + cross-page".

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 frontend reviewer CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard.
- **C7** (existing Layout tests fail because the new banner mount changes the rendered DOM tree).
- **B6** (the `/audit` endpoint doesn't exist in 5a.1 deliverables — halt session, file fix-it task, resume).

---

*End Sprint 31.91 Session 5e implementation prompt.*
