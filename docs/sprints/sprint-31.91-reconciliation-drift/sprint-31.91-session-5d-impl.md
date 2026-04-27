# Sprint 31.91, Session 5d: Toast Notification System + Acknowledgment UI Flow

> **Track:** Alert Observability Frontend (Session 5c → **5d** → 5e).
> **Position in track:** Second frontend session. Adds the cross-page-immediate notification primitive (toast) and the modal-driven acknowledgment flow (reason text required, audit-log feedback). Builds directly on 5c's `useAlerts` hook.
> **Reviewer:** **Frontend** (`templates/review-prompt-frontend.md`).

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md`.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - Session 5c's `frontend/src/hooks/useAlerts.ts` (consumer for 5d's components).
   - Existing toast / modal patterns in the frontend. Locate via `grep -rn "Toast\|Modal" frontend/src/components/`. If existing patterns exist (e.g., a generic `Toast` from a UI library OR a hand-rolled one), MIRROR them — don't introduce a second toast paradigm.
   - `frontend/src/components/TradeDetailPanel.tsx` (or sibling) — existing modal pattern for focus-trap, escape-key, ARIA.
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D12 + AC-D12 (lines ~468-487, 691+).

3. Run baseline:

   ```
   pnpm vitest run
   ```

   Expected: green at Session 5c's count.

4. Branch: **`main`**.

## Objective

Two components + a queue:

1. **`AlertToast.tsx`** — pops up on ANY page (via cross-page mount in 5e) when a new critical alert arrives via WebSocket. Persists until acknowledged or auto-dismissed on condition-cleared. Click-to-acknowledge opens `AlertAcknowledgmentModal`.

2. **`AlertAcknowledgmentModal.tsx`** — modal dialog requiring reason text (min 10 chars per backend validation). Posts to `POST /api/v1/alerts/{alert_id}/acknowledge`. Shows audit-log entry on success. Cancellable (alert stays active).

3. **Toast queue** — multiple critical alerts arriving simultaneously stack visually; oldest-first dismissed when queue exceeds 5.

## Requirements

### `AlertToast.tsx`

```tsx
// frontend/src/components/AlertToast.tsx
import { useState } from "react";
import { useAlerts, type Alert } from "../hooks/useAlerts";
import { AlertAcknowledgmentModal } from "./AlertAcknowledgmentModal";

const MAX_TOAST_QUEUE = 5;

export function AlertToastStack() {
  const { alerts, acknowledge } = useAlerts();
  const [modalAlert, setModalAlert] = useState<Alert | null>(null);

  // Critical alerts in active state, sorted oldest-first
  const activeCritical = alerts
    .filter(a => a.severity === "critical" && a.status === "active")
    .sort((a, b) => a.emitted_at_utc.localeCompare(b.emitted_at_utc));

  // Display newest-first up to MAX_TOAST_QUEUE
  // (oldest-first dismissed when queue >5; visually stack newest-on-top)
  const visible = activeCritical.slice(-MAX_TOAST_QUEUE).reverse();

  return (
    <>
      <div
        role="region"
        aria-label="Alert notifications"
        className="fixed top-4 right-4 z-50 flex flex-col gap-2 ..."
      >
        {visible.map(alert => (
          <AlertToast
            key={alert.alert_id}
            alert={alert}
            onAcknowledge={() => setModalAlert(alert)}
          />
        ))}
      </div>
      {modalAlert && (
        <AlertAcknowledgmentModal
          alert={modalAlert}
          onClose={() => setModalAlert(null)}
          onSubmit={async (reason, operator_id) => {
            const result = await acknowledge(modalAlert.alert_id, reason, operator_id);
            setModalAlert(null);
            return result;
          }}
        />
      )}
    </>
  );
}

interface AlertToastProps {
  alert: Alert;
  onAcknowledge: () => void;
}

function AlertToast({ alert, onAcknowledge }: AlertToastProps) {
  return (
    <div role="status" aria-live="polite" className="bg-red-600 text-white p-3 rounded shadow-lg ...">
      <div className="font-bold">{alert.alert_type}</div>
      <div className="text-sm">{alert.message}</div>
      <button onClick={onAcknowledge} className="mt-2 ...">
        Acknowledge
      </button>
    </div>
  );
}
```

**Auto-dismiss on auto-resolve:** the toast is a pure render of `useAlerts` filtered state. When the backend auto-resolves an alert, the WebSocket pushes `alert_auto_resolved` → hook state updates → component re-renders → toast unmounts. Same mechanism as 5c's banner.

**Queue overflow behavior:** when `> MAX_TOAST_QUEUE` critical alerts are active, only the newest 5 are visible; the oldest are dropped from view (not from underlying state — the backend still has them; they appear in Observatory panel in 5e). This is the operator-comfort decision: 6+ simultaneous critical toasts is operationally a panic state, and showing all of them helps no one. Document this in close-out.

### `AlertAcknowledgmentModal.tsx`

```tsx
// frontend/src/components/AlertAcknowledgmentModal.tsx
import { useEffect, useRef, useState } from "react";
import { type Alert } from "../hooks/useAlerts";

interface Props {
  alert: Alert;
  onClose: () => void;
  onSubmit: (reason: string, operator_id: string) => Promise<{ outcome: string; audit_id: number }>;
}

export function AlertAcknowledgmentModal({ alert, onClose, onSubmit }: Props) {
  const [reason, setReason] = useState("");
  const [operator_id] = useState("operator");  // TODO: from auth context once login lands
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditId, setAuditId] = useState<number | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { reasonRef.current?.focus(); }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const canSubmit = reason.trim().length >= 10 && !submitting;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await onSubmit(reason, operator_id);
      setAuditId(result.audit_id);
    } catch (e: any) {
      setError(e?.message ?? "Acknowledge failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="ack-modal-title" className="fixed inset-0 ...">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 id="ack-modal-title">Acknowledge Alert</h2>
        <p>{alert.alert_type}: {alert.message}</p>
        <label>
          Reason (required, ≥10 characters):
          <textarea
            ref={reasonRef}
            value={reason}
            onChange={e => setReason(e.target.value)}
            minLength={10}
            maxLength={500}
            className="w-full ..."
          />
        </label>
        <div className="text-sm text-gray-500">{reason.trim().length}/500</div>
        {error && <div role="alert" className="text-red-600">{error}. <button onClick={handleSubmit}>Retry</button></div>}
        {auditId && <div role="status" className="text-green-600">Acknowledged (audit ID: {auditId})</div>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose}>Cancel</button>
          <button disabled={!canSubmit} onClick={handleSubmit}>Acknowledge</button>
        </div>
      </div>
    </div>
  );
}
```

**Focus trap:** for 5d, focus the textarea on mount and handle Escape key. A full focus-trap implementation (Tab cycles within modal) is recommended but optional for 5d if the existing modal pattern in the codebase doesn't have it. Document in close-out which approach is taken.

**Error handling:**
- Network failure → `error` state → "Retry" button.
- 404 (alert auto-resolved before click) → backend returns 404 → hook throws → `error` state. Show "Alert no longer active" message.
- 409 (already acknowledged from another tab) → backend returns 409 (with original acknowledger info) → hook returns the JSON (per 5c hook contract). The modal should treat 409 as success (with a note "Already acknowledged by <other operator>").

The hook's `acknowledge` function throws on non-200 responses. Verify 5c's hook contract specifically: does it throw on 409, or treat 200 + 409 as success? Per 5c's pseudocode: `if (!r.ok && r.status !== 200 && r.status !== 409) throw ...`. So 200 and 409 don't throw; 404 and other errors do. Align modal logic accordingly: 409 returns success-ish JSON; modal shows the original-ack info.

### Wire from `AlertToast` to `AlertAcknowledgmentModal`

The wiring lives in `AlertToastStack` above. The toast doesn't render the modal directly; it lifts state up to `AlertToastStack`, which renders one modal at a time.

### Mount

The toast stack and modal are mounted in 5e's `Layout.tsx` for cross-page presence. For Session 5d, mount on `Dashboard.tsx` alongside `AlertBanner`:

```tsx
// In Dashboard.tsx (temporary; 5e moves to Layout):
<AlertBanner />
<AlertToastStack />
```

## Tests (~8 new Vitest)

1. **`AlertToast appears on new critical alert via WebSocket`** — render `AlertToastStack`; trigger WS message `alert_active` with critical severity; assert toast rendered with alert message text.

2. **`AlertToast persists until acknowledged or auto-dismissed`** — render with critical alert; assert visible; trigger `alert_acknowledged` WS message; assert toast unmounted.

3. **`AlertToast click opens AlertAcknowledgmentModal`** — render with critical alert; click "Acknowledge" button; assert modal rendered; assert focus on textarea.

4. **`AlertAcknowledgmentModal requires reason text before submit`** — open modal; assert submit button disabled; type 9 chars; submit still disabled; type 10th char; submit enabled.

5. **`AlertAcknowledgmentModal cancellable (alert stays active)`** — open modal; click cancel; assert modal closed; assert toast still visible (alert still active in hook state).

6. **`AlertAcknowledgmentModal successful submit shows audit-log entry`** — open modal; type reason; submit; mock backend returns `{outcome: "first_ack", audit_id: 42}`; assert success message visible with audit ID 42.

7. **`AlertToast queue stacks multiple alerts oldest-first dismissed when >5`** — render with 6 critical alerts (varying emitted_at_utc); assert exactly 5 toasts rendered; assert the oldest (smallest emitted_at_utc) is the one missing; assert newest at top of visual stack.

8. **`AlertToast network failure on acknowledge shows retry option`** — open modal; mock fetch to throw; submit; assert error message + retry button visible; click retry; assert second fetch attempt.

**Bonus:** `AlertAcknowledgmentModal handles 409 already-acknowledged-from-other-tab` — open modal; mock backend to return 200 with `outcome: "duplicate_ack"` and original acknowledger info; submit; assert success message includes "previously acknowledged by <operator>".

**Coverage target:** ≥90%.

## Definition of Done

- [ ] `AlertToast.tsx` + `AlertToastStack` (queue handler) + `AlertAcknowledgmentModal.tsx` created.
- [ ] Toast renders on new critical alert via WS.
- [ ] Toast persists until ack or auto-dismiss.
- [ ] Modal requires ≥10-char reason.
- [ ] Modal cancellable.
- [ ] Toast queue caps at 5; oldest-first dropped from view.
- [ ] Modal accessibility: `role="dialog"`, `aria-modal`, focus on textarea, Escape closes.
- [ ] Error handling: network failure → retry; 404 → "no longer active"; 409 → success-with-prior-ack-info.
- [ ] Mounted on `Dashboard.tsx` (temporary; 5e moves to Layout).
- [ ] 8 (or 9 with bonus) Vitest tests; ≥90% coverage.
- [ ] CI green; Vitest baseline ≥ Session 5c + 8.
- [ ] Tier 2 review (frontend reviewer template) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-5d-closeout.md`.

## Close-Out Report

Standard structure plus:

- **Toast queue overflow rationale:** document the operator-comfort decision (5+ simultaneous critical toasts is panic state; cap visual to 5; underlying state intact for Observatory panel).
- **Focus-trap decision:** state whether 5d implements full focus-trap or only initial-focus-and-Escape. If full trap is deferred, file as DEF-212 (UI accessibility polish).
- **409 handling decision:** state how the modal renders the duplicate-ack response (with prior acknowledger info).

```json
{
  "session": "5d",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 8,
  "vitest_coverage_pct": "<TBD>",
  "queue_overflow_capped_at_5": true,
  "modal_accessibility": "initial_focus + escape (full focus-trap deferred to DEF-212 if applicable)"
}
```

## Tier 2 Review Invocation

Frontend reviewer template.

Reviewer output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5d-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Toast queue under burst.** Reviewer mentally simulates: 10 critical alerts arrive within 100ms via WS deltas. Test 7 covers the visual cap; reviewer also verifies no flicker (alerts appear, then re-sort, then drop) — the sort-on-render in `AlertToastStack` should be stable.

2. **Modal accessibility.** Reviewer reads the modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` matches the heading id, focus on textarea on mount, Escape closes. Tab cycling within modal is desirable but optional for 5d.

3. **Error handling completeness.** Reviewer verifies all 3 cases (network failure, 404, 409) have visible UI feedback; no case results in a blank modal that just hangs.

4. **Z-index layering.** Toast `z-50`. Modal `z-50` or higher. Banner from 5c at top of viewport. No conflict — but reviewer should verify against existing UI z-index conventions.

5. **Mount-on-Dashboard.tsx is temporary.** Same as 5c's banner — 5e relocates both to Layout. Reviewer verifies 5d's close-out flags this.

6. **Hook's 409-doesn't-throw contract.** Verified by reading 5c's `useAlerts.acknowledge` and confirming the modal's submit handler behavior matches.

7. **`operator_id` placeholder.** Currently hardcoded `"operator"`. Per RULE-007, file as DEF-213 (auth context integration once login feature lands) — do NOT integrate auth in this session.

## Sprint-Level Regression Checklist

- **Invariant 5:** PASS — expected ≥ Session 5c + 8.
- **Invariant 14:** Row "After Session 5d" — Alert observability frontend = "useAlerts + banner + toast + modal".

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 frontend reviewer CONCERNS or ESCALATE).
- **B1, B3, B4, B6** — standard.
- **C7** (existing modal patterns conflict with the new acknowledgment modal — z-index, focus-trap, escape-key handling collide with each other).

---

*End Sprint 31.91 Session 5d implementation prompt.*
