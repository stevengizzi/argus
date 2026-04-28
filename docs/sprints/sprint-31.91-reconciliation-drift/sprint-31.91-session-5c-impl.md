# Sprint 31.91, Session 5c: `useAlerts` Hook + Dashboard Banner

> **Track:** Alert Observability Frontend (Sessions **5c** → 5d → 5e). Builds on the 5a.1 + 5a.2 + 5b backend contract (REST + WebSocket + auto-resolution policy).
> **Position in track:** First frontend session. Establishes the data hook + the most visible UI primitive (banner). The next two sessions add toast + cross-page integration on top.
> **Reviewer:** **Frontend** (different focus from backend safety reviewer used for Sessions 0-4 + 5a-5b). Use `templates/review-prompt-frontend.md`.

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md`.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - `frontend/src/hooks/useObservatory.ts` — existing TanStack Query + WebSocket hybrid pattern. **Mirror this structure.** Don't invent a new pattern.
   - `frontend/src/hooks/useArena.ts` — second reference for the hybrid pattern; useful for reconnect-resilience comparison.
   - `frontend/src/pages/Dashboard.tsx` — current page structure (banner mounts here).
   - `frontend/src/components/` — existing component conventions (file naming, prop shapes, Tailwind class organization, Vitest spec layout).
   - Session 5a.1 + 5a.2 deliverables on `main`: REST endpoints (`GET /api/v1/alerts/active`, `GET /api/v1/alerts/history`, `POST /api/v1/alerts/{id}/acknowledge`); WebSocket `/ws/v1/alerts` with 4 message types (`snapshot`, `alert_active`, `alert_acknowledged`, `alert_auto_resolved`, `alert_archived`). Verify by reading the actual backend code, NOT by assuming.
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D11 + AC-D11 (lines ~446-466, 680+).
   - **Tier 3 #2 verdict** at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-2-review.md` — must be CLEAR before this session begins. If CONCERNS or ESCALATE, halt.

3. Run baseline:

   ```
   pnpm vitest run
   ```

   Expected: green at Session 5b's count.

4. Branch: **`main`**.

## Objective

Two deliverables:

1. **`frontend/src/hooks/useAlerts.ts`** — TanStack Query + WebSocket hybrid hook. Initial state via REST; real-time updates via WebSocket; reconnect-resilient (REST fallback during disconnect; refetch on reconnect).

2. **`frontend/src/components/AlertBanner.tsx`** — persistent banner at top of Dashboard for ANY active critical alert. Severity-coded styling (critical = red, warning = yellow). Acknowledgment button calls REST. Disappears within 1s of acknowledgment OR auto-resolution.

The banner mounts on Dashboard.tsx in this session; cross-page mounting at Layout level lands in Session 5e.

## Requirements

### `useAlerts` Hook

Mirror the `useObservatory` hybrid pattern. Sketch:

```typescript
// frontend/src/hooks/useAlerts.ts
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

export type AlertSeverity = "critical" | "warning" | "info";
export type AlertStatus = "active" | "acknowledged" | "auto_resolved" | "archived";

export interface Alert {
  alert_id: string;
  alert_type: string;
  severity: AlertSeverity;
  source: string;
  message: string;
  metadata: Record<string, unknown>;
  emitted_at_utc: string;
  emitted_at_et: string;
  status: AlertStatus;
  acknowledged_by?: string;
  acknowledged_at_utc?: string;
}

export type ConnectionStatus = "loading" | "connected" | "disconnected" | "error";

export function useAlerts() {
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("loading");
  const wsRef = useRef<WebSocket | null>(null);

  // Initial state via REST (TanStack Query). Used during disconnect as fallback.
  const { data: alerts = [], refetch } = useQuery<Alert[]>({
    queryKey: ["alerts", "active"],
    queryFn: () => fetch("/api/v1/alerts/active").then(r => r.json()),
    // Polling fallback ONLY during WebSocket disconnect
    refetchInterval: connectionStatus === "disconnected" ? 5000 : false,
  });

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/v1/alerts`);
    wsRef.current = ws;
    ws.onopen = () => {
      setConnectionStatus("connected");
      refetch(); // Resync on reconnect
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") {
        queryClient.setQueryData(["alerts", "active"], msg.alerts);
      } else if (msg.type === "alert_active") {
        queryClient.setQueryData<Alert[]>(["alerts", "active"], (prev = []) =>
          [...prev, msg.alert]
        );
      } else if (msg.type === "alert_acknowledged" || msg.type === "alert_auto_resolved") {
        queryClient.setQueryData<Alert[]>(["alerts", "active"], (prev = []) =>
          prev.map(a => a.alert_id === msg.alert.alert_id ? msg.alert : a)
        );
      } else if (msg.type === "alert_archived") {
        queryClient.setQueryData<Alert[]>(["alerts", "active"], (prev = []) =>
          prev.filter(a => a.alert_id !== msg.alert_id)
        );
      }
    };
    ws.onclose = () => setConnectionStatus("disconnected");
    ws.onerror = () => setConnectionStatus("error");
    return () => ws.close();
  }, [queryClient, refetch]);

  const acknowledge = async (alert_id: string, reason: string, operator_id: string) => {
    const r = await fetch(`/api/v1/alerts/${alert_id}/acknowledge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason, operator_id }),
    });
    if (!r.ok && r.status !== 200 && r.status !== 409) {
      throw new Error(`Acknowledge failed: ${r.status}`);
    }
    return r.json();
  };

  return { alerts, connectionStatus, acknowledge };
}
```

**Reconnect resilience details:**
- WebSocket disconnect → `connectionStatus = "disconnected"` → REST refetchInterval kicks in at 5s.
- WebSocket reconnect → `onopen` fires → `connectionStatus = "connected"` + `refetch()` immediately resyncs state. The REST snapshot supersedes any deltas missed during disconnect; this is correct because the backend's WebSocket `snapshot` message + REST `/active` both return identical state.
- Component unmount → `ws.close()` in cleanup.

### `AlertBanner` Component

```tsx
// frontend/src/components/AlertBanner.tsx
import { useAlerts } from "../hooks/useAlerts";

export function AlertBanner() {
  const { alerts, acknowledge } = useAlerts();
  const criticalActive = alerts.filter(
    a => a.severity === "critical" && a.status === "active"
  );

  if (criticalActive.length === 0) return null;

  // Top alert by emitted_at_utc; if multiple, show count + most recent
  const top = criticalActive[criticalActive.length - 1];
  const others = criticalActive.length - 1;

  return (
    <div role="alert" className="bg-red-600 text-white px-4 py-3 ...">
      <div className="flex items-center gap-4">
        <span className="font-bold uppercase">Critical</span>
        <span>{top.message}</span>
        {others > 0 && <span className="text-red-200">+{others} more</span>}
        <button
          onClick={() => acknowledge(top.alert_id, "Acknowledged from Dashboard banner", "operator")}
          className="ml-auto bg-white text-red-700 px-3 py-1 rounded ..."
        >
          Acknowledge
        </button>
      </div>
    </div>
  );
}
```

**Severity styling (Tailwind v4 classes):**
- `critical` → `bg-red-600 text-white` border-red-700
- `warning` → `bg-yellow-500 text-black` border-yellow-600
- `info` → not displayed in banner; toast-only (5d).

**Disappearance within 1s:** when WebSocket pushes `alert_acknowledged` or `alert_auto_resolved`, TanStack Query cache updates → component re-renders → if no critical-active alerts remain, banner unmounts. The 1s budget covers WebSocket round-trip + React re-render; no additional logic needed if the WebSocket contract is honored.

**Mount on Dashboard.tsx** — single line:

```tsx
// In Dashboard.tsx, at the top of the component's render:
<AlertBanner />
```

This is a temporary mount for 5c; Session 5e moves it to `Layout.tsx` for cross-page persistence.

## Tests (~10 new Vitest)

1. **`useAlerts hook fetches initial state via REST`** — mock fetch; render hook in `renderHook`; assert REST call to `/api/v1/alerts/active`; assert returned alerts.

2. **`useAlerts hook subscribes to WebSocket on mount`** — mock WebSocket constructor; render hook; assert `new WebSocket("ws://.../ws/v1/alerts")` called.

3. **`useAlerts hook handles WebSocket disconnect with REST fallback`** — render; trigger `ws.onclose`; assert `connectionStatus === "disconnected"`; advance fake timers 5s; assert REST refetch called.

4. **`useAlerts hook handles WebSocket reconnect with state refetch`** — render; trigger `ws.onclose` then `ws.onopen` (simulate reconnect); assert REST refetch called within `onopen` handler; assert `connectionStatus === "connected"`.

5. **`AlertBanner renders for active critical alert`** — provide hook with `[{severity: "critical", status: "active", ...}]`; render; assert banner visible; assert message text.

6. **`AlertBanner renders correct severity styling (critical = red)`** — provide critical alert; render; assert root element has `bg-red-600` class.

7. **`AlertBanner renders correct severity styling (warning = yellow)`** — extend the hook contract to allow `warning` severity in banner OR explicitly only render `critical` in banner (per spec D11; warning may stay toast-only). **Operator decision needed if not yet specified — default: only critical in banner.** If decision is "only critical", this test instead asserts `warning` alerts are NOT rendered in banner (toast-only). Document the chosen interpretation in close-out.

8. **`AlertBanner acknowledgment button calls REST endpoint`** — render with critical alert; click ack button; assert fetch called with `POST /api/v1/alerts/{id}/acknowledge` and JSON body containing reason + operator_id.

9. **`AlertBanner disappears within 1s of acknowledgment`** — render with critical alert; trigger WS message `alert_acknowledged` (mutate hook state); assert banner NOT rendered after re-render (within Vitest's synchronous fake-timer model, the test is "after state update, banner gone").

10. **`AlertBanner disappears within 1s of auto-resolution`** — same shape; trigger `alert_auto_resolved` WS message; assert banner gone.

**Coverage target:** ≥90% for new code per spec D11 acceptance.

### Requirement N — DEF-220 disposition: `acknowledgment_required_severities` field

**Anchor:** in `argus/core/config.py`, the `AlertsConfig` Pydantic model and its `acknowledgment_required_severities` field.

**Pre-flight grep-verify:**
```bash
grep -n "acknowledgment_required_severities" argus/core/config.py
# Expected: 1 hit (the field definition)

grep -rn "acknowledgment_required_severities" argus/ --include="*.py" | grep -v config.py
# Expected: 0 hits — the field has no consumers (this is the DEF)
```

**Disposition decision:** the recommendation per Tier 3 #2 is REMOVAL (the per-alert-type `PolicyEntry.operator_ack_required` already encodes the equivalent control). However, this session's frontend implementation may surface a use case for the field. Decide one of:

**Option A — Remove the field** (recommended if no frontend use case surfaces):
1. Delete the field from `AlertsConfig` in `argus/core/config.py`.
2. Update tests that reference the field to use `PolicyEntry.operator_ack_required` instead.
3. Search for any docs/sprint-spec references to the field and update accordingly.

**Option B — Wire the field** (only if Session 5c's frontend introduces a need):
1. Add a consumer in the route layer that gates auto-archive based on severity match against the field.
2. Add tests covering the gate behavior.
3. Document the composition with `PolicyEntry.operator_ack_required` (which takes precedence).

**Decision documentation:** Session 5c's close-out must explicitly state which option was chosen and why.

**DEF transition:** DEF-220 → "RESOLVED-IN-SPRINT, Session 5c (Option A: removal)" or "RESOLVED-IN-SPRINT, Session 5c (Option B: wired at <consumer site>)".

## Definition of Done

- [ ] `useAlerts.ts` mirrors `useObservatory.ts` hybrid pattern.
- [ ] Reconnect resilience: REST fallback active during disconnect; refetch on reconnect.
- [ ] WebSocket subscription cleanup on unmount (no leaks).
- [ ] `AlertBanner.tsx` renders for any active critical alert.
- [ ] Severity-coded styling per Tailwind v4 conventions.
- [ ] Acknowledgment posts to REST with reason + operator_id body.
- [ ] Banner disappears within 1s of ack OR auto-resolve.
- [ ] Mounted on `Dashboard.tsx` (temporary placement; 5e moves to Layout).
- [ ] 10 Vitest tests; ≥90% coverage on new code.
- [ ] Operator decision documented: warning severity in banner OR toast-only (default: toast-only).
- [ ] DEF-220 disposition (Option A or Option B) decided and applied; close-out documents the choice.
- [ ] CI green; Vitest baseline ≥ Session 5b + 10.
- [ ] Tier 2 review (frontend reviewer template) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5c-closeout.md`.

## Close-Out Report

Standard structure plus:

- **WebSocket contract verification:** cite the backend's actual WS message shapes (from 5a.2's `argus/ws/alerts.py`) and confirm the frontend hook handles all of them.
- **Banner severity-rendering decision:** state explicitly which severities render in banner (default: critical only). If warning is also rendered, document the styling.
- **Coverage report:** paste Vitest coverage summary for `useAlerts.ts` + `AlertBanner.tsx`.
- **DEF transition claimed:** DEF-220 → "RESOLVED-IN-SPRINT, Session 5c" (transition applied at sprint-close per `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`).

```json
{
  "session": "5c",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 10,
  "vitest_coverage_pct": "<TBD>",
  "reconnect_resilience_verified": true,
  "ws_contract_aligned_with_5a2": true
}
```

## Tier 2 Review Invocation

Frontend reviewer template (`templates/review-prompt-frontend.md`).

Reviewer output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5c-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Hook state machine.** Reviewer reads the `connectionStatus` transitions: `loading` (initial) → `connected` (`onopen`) → `disconnected` (`onclose`) → reconnect → `connected`. Verify no state can persist as `error` after a successful subsequent reconnect.

2. **Reconnect resync uses REST, not WS replay.** When `onopen` fires after a disconnect, the hook calls `refetch()` (REST). The backend's WS `snapshot` message will ALSO arrive shortly after; both update the same TanStack Query cache; last-write-wins. Verify these don't fight each other (e.g., REST returns `[A, B]`, then WS snapshot returns `[A, B, C]` for an alert that arrived during the disconnect window — the cache should end up with `[A, B, C]`, not `[A, B]`).

3. **WebSocket cleanup on unmount.** `ws.close()` in `useEffect` cleanup. Otherwise, multiple component mounts (e.g., StrictMode double-render in dev) leak connections.

4. **Acknowledgment error handling.** What happens on 404 (alert auto-resolved before click)? On 409 (already acknowledged from another tab)? On network failure? The hook returns the JSON; the banner currently doesn't surface errors. For 5c this is acceptable; error UI lands in 5d's modal. Reviewer verifies the hook doesn't crash on non-200/409 responses.

5. **Severity styling consistency.** Tailwind v4 classes match existing UI patterns (e.g., other "alert"-style banners in the codebase, if any). If existing patterns use different red shades, align to those.

6. **Accessibility.** `role="alert"` is on the banner element. Acknowledge button is a real `<button>`, keyboard-focusable. Test 5 should verify role; if not, ask reviewer to add ARIA-roles assertion.

7. **Banner-on-Dashboard.tsx is temporary.** Reviewer verifies the close-out explicitly notes 5e relocates the banner to Layout. If 5c silently lands the banner in two places, that's a CONCERN.

## Sprint-Level Regression Checklist

- **Invariant 5 (Vitest baseline):** PASS — expected ≥ Session 5b + 10.
- **Invariant 17 (banner persistence) — partial:** PASS in-scope (banner renders on Dashboard); cross-page persistence verified in 5e.
- **Invariant 14:** Row "After Session 5c" — Alert observability frontend = "useAlerts hook + Dashboard banner".

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 frontend reviewer CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard.
- **C7** (existing Vitest tests fail because the new fetch / WebSocket mocks broaden a global test-setup fixture).

---

*End Sprint 31.91 Session 5c implementation prompt.*
