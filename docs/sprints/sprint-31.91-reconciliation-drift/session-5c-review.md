# Sprint 31.91 — Session 5c Tier 2 Review

**Reviewer:** Frontend reviewer (Tier 2 automated review, `templates/review-prompt-frontend.md`).
**Subject:** Session 5c implementation — `useAlerts` hook + `AlertBanner` on Dashboard + DEF-220 disposition (Option A — removal).
**Diff under review:** commit `3197472` against pre-session HEAD `140ccd8`.
**Close-out:** `docs/sprints/sprint-31.91-reconciliation-drift/session-5c-closeout.md`.
**Implementation prompt:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md`.

---

## Verdict

**CLEAR_WITH_NOTES** — recommend operator proceed to Session 5d.

The implementation matches spec intent at every load-bearing point. Three judgment calls disclosed in the close-out (reconnect-gated refetch, JWT auth alignment, field-name alignment with backend wire format) all flow from grep-verified backend reality vs the impl prompt's illustrative sketch — RULE-038 posture, all justified. DEF-220 Option A (removal) matches the Tier 3 #2 verdict's pre-recommendation. CI green on `3197472` (both vitest and pytest jobs success per `gh run view 25078777514`). Vitest baseline 866 → 886 (+20) verified by independent local rerun (`117 passed (117) | 886 passed (886) | 12.68s`).

The "_with notes_" qualifier captures three minor observations: (a) absence of explicit WS-reconnect logic (the hook relies on REST polling indefinitely after a disconnect — matches `useArenaWebSocket` precedent and the spec sketch, but worth noting); (b) untested 5xx ack-error path (intentional — error UI lands in 5d's modal); (c) untested `getToken() === null` early-return branch (operationally fires only when JWT cleared mid-session). None block the verdict; all are documented in the close-out.

---

## Per-Deliverable Verdict

| Deliverable | Verdict | Evidence |
|---|---|---|
| **D1** — `useAlerts.ts` (TanStack Query + WebSocket hybrid) | CLEAR | 324 LOC; mirrors `useArenaWebSocket` JWT-first pattern. All 6 WS message types handled. Reconnect-gated refetch via `wasDisconnectedRef`. REST fallback at 5s on `disconnected`/`error`. WebSocket cleanup on unmount handles both `OPEN` and `CONNECTING` readyStates. Field shape matches backend `_alert_to_payload`. |
| **D2** — `AlertBanner.tsx` (critical-only banner on Dashboard) | CLEAR | 91 LOC. Renders only `severity === 'critical' && state === 'active'`. `bg-red-600 border-red-700 text-white` consistent with `ActionCard.tsx`'s destructive-action surface idiom. `role="alert"` + `aria-live="assertive"`. Real `<button>` element, keyboard-focusable. Sort by `created_at_utc` for headline; "+N more" for stacking. Disappearance via WS-driven cache update. |
| **D3** — Dashboard mount sites | CLEAR | 5 mount sites in `DashboardPage.tsx` covering pre-market desktop, pre-market non-desktop, phone, desktop, tablet branches. Zero references in `argus/ui/src/layouts/` (5e relocation scope preserved). Banner uses `staggerItem` motion variant where surrounding layout uses motion. |
| **D4** — DEF-220 disposition (Option A — removal) | CLEAR | `AlertsConfig.acknowledgment_required_severities` removed from `argus/core/config.py:228-239` (replaced with disposition comment). Removed from `config/system.yaml:221-228` and `config/system_live.yaml:227-233` (alerts block now `{}` with explanatory comment). `grep -rn "acknowledgment_required_severities" argus tests config` returns ONLY the disposition-comment lines (3 hits in 3 files, all comments). Zero production-code or test consumers left. Matches Tier 3 #2 verdict line 142 ("removed at S5c per DEF-220 disposition"). |
| **D5** — Tests (target ≥10) | CLEAR | 20 new tests added (10 hook + 10 component). Spec target ≥+10 exceeded by 10. |

---

## Findings — Session-Specific Review Focus

### F1. Hook state machine (focus area #1) — CLEAR_WITH_NOTE

**Trace:** `loading` → `auth_success` → `connected` → `onclose`/`onerror` → `disconnected`/`error` → another `auth_success` → `connected` (with REST refetch since `wasDisconnectedRef.current === true`).

**Verified:**
- Initial state: `loading` (line 190).
- `getToken() === null` → `error` + early return (line 213). Terminal — no WS opened.
- `new WebSocket()` throws → `error` + early return (line 225). Terminal.
- `auth_success` → `connected` (line 244). Conditional refetch (line 250-253) on prior-disconnect.
- `onerror` → `wasDisconnectedRef.current = true` AND `error` (lines 292-293).
- `onclose` → `wasDisconnectedRef.current = true` AND `disconnected` (lines 297-298).
- After `error`-then-`onclose` (typical browser sequence), state ends at `disconnected` (overwritten by `onclose`). Either way, `wasDisconnectedRef.current === true`.
- After a subsequent `auth_success`, state goes to `connected` AND the refetch fires AND `wasDisconnectedRef` clears. **No state can persist as `error` after a successful subsequent `auth_success`.** ✓

**NOTE (non-blocking):** The hook has NO explicit reconnect logic. The `useEffect` runs once; `new WebSocket()` is called once. If the WebSocket disconnects, that connection instance is dead — browsers do NOT auto-reconnect WebSocket. The "reconnect" the close-out describes is the test-fixture re-firing `onopen`+`auth_success` on the same mock instance. In production, after a real disconnect, the hook will rely on REST polling (5s interval) for new alerts indefinitely until the page is reloaded. This:
1. Matches `useArenaWebSocket.ts` (also no reconnect logic) — established pattern.
2. Matches the spec sketch (also no reconnect logic).
3. Is operationally acceptable because alerts still arrive at 5s polling intervals.
4. Could be revisited in 5e or post-31.91 (e.g., exponential-backoff retry loop on close).

This is a NOTE, not a CONCERN — the implementation faithfully follows the spec sketch and matches existing precedent.

### F2. REST/WS race ordering on reconnect (focus area #2) — CLEAR

The reconnect path: `auth_success` arrives → `setConnectionStatus('connected')` AND `void refetch()`. Backend immediately follows with a `snapshot` frame (alerts_ws.py lines 88-101). Both update the same `['alerts', 'active']` query cache via `setQueryData` — last-write-wins.

**Edge case examined:** REST returns `[A, B]` and WS snapshot returns `[A, B, C]` for an alert C that arrived during the disconnect window. Both pull from `health_monitor.get_active_alerts()` (in-memory state) at slightly different times, but C is in BOTH because it persists in HealthMonitor across the disconnect. The cache converges to `[A, B, C]` regardless of arrival order. ✓

The WS `snapshot` filters via `isVisible` (drops `archived`); REST `/api/v1/alerts/active` already returns only `ACTIVE+ACKNOWLEDGED` (alerts.py docstring confirms). Same content. No fight between them. ✓

Test 5 specifically verifies `archived` alerts are filtered out at the cache layer (line 200, `state: 'archived'`).

### F3. WebSocket cleanup on unmount (focus area #3) — CLEAR

`useEffect` cleanup (lines 301-309):
```ts
return () => {
  wsRef.current = null;
  if (
    ws.readyState === WebSocket.OPEN ||
    ws.readyState === WebSocket.CONNECTING
  ) {
    ws.close(1000, 'useAlerts unmount');
  }
};
```

Both `OPEN` and `CONNECTING` are handled. `CLOSING`/`CLOSED` skip the close (correct — would be a no-op anyway). StrictMode double-mount in dev would correctly close the first WS before opening the second. ✓

Test 10 verifies `close()` is called on unmount.

### F4. Acknowledgment error handling (focus area #4) — CLEAR

`postAcknowledge` paths (lines 116-122):
- 200 → returns `AcknowledgeResult` (idempotent path; backend returns 200 for duplicate-ack per `alerts.py:336-368`, NOT 409 as the impl prompt suggested — close-out judgment-call #3 correctly noted this).
- 404 → returns `null`.
- Other status (4xx including 422 validation, 5xx) → `throw new Error(...)`.
- Network failure: `fetch` rejection propagates.

Banner's `handleAck` (`AlertBanner.tsx:47-58`) wraps in `try/catch/finally`. The `finally` clears `acking` regardless of success/failure. The `catch` swallows (intentional — error UI lands in 5d's modal). ✓

**NOTE (non-blocking):** The 5xx-throw branch is not exercised behaviorally by any test (close-out lines 306-311 acknowledge this). Test 9 covers the 404 path; the 200/idempotent path is implicit in test 8 (both first call and second call return 200). The throw-path is type-safe (`Promise<AcknowledgeResult | null>` cannot include thrown errors) but has no behavioral assertion. Given that the error UI is explicitly deferred to 5d, this is intentional scope shrinkage and acceptable.

### F5. Severity styling consistency (focus area #5) — CLEAR

AlertBanner uses `bg-red-600 border border-red-700 text-white` (line 65 of AlertBanner.tsx).

Compared against existing patterns:
- `Badge.tsx:43`: `text-red-500 bg-red-500/15` (crisis BADGE — opacity-modified, indicator).
- `CatalystBadge.tsx:37`: `text-red-400 bg-red-400/20` (regulatory CATALYST badge).
- `ActionCard.tsx:302,559`: `bg-red-600 hover:bg-red-500 text-white` (destructive-action BUTTON).

The banner is an action-required surface (not a badge/indicator), so `bg-red-600` matches `ActionCard.tsx`'s destructive-action idiom — same shade, same opacity, same `text-white`. The opacity-modified shades on `Badge`/`CatalystBadge` are for compact category indicators where saturation would overwhelm the surrounding card; AlertBanner's mission is to demand attention, so solid red is correct.

This is consistent with the existing UI pattern hierarchy.

### F6. Accessibility (focus area #6) — CLEAR

- `role="alert"` on root element (line 63). ✓
- `aria-live="assertive"` on root element (line 64). ✓ (bonus — assistive-tech announcement on append)
- `<AlertTriangle aria-hidden="true">` (line 68). ✓
- Acknowledge button: real `<button type="button">` (lines 81-82), keyboard-focusable, native semantics.
- Test 4: `screen.getByRole('alert')` verifies the role.
- Test 9: `expect(button.tagName).toBe('BUTTON')` and `expect(button).not.toHaveAttribute('disabled')` verifies keyboard-focusability.
- Disabled state during ack (lines 83, 86) shows "Acknowledging…" with `disabled:opacity-60 disabled:cursor-not-allowed`.

WCAG AA contrast: white text on `bg-red-600` (#dc2626) provides ~4.83:1 contrast — passes AA for normal text. Acknowledge button (`bg-white text-red-700`, ~10.4:1) passes AAA.

### F7. Banner-on-Dashboard temporary placement (focus area #7) — CLEAR

`grep -rn "AlertBanner" argus/ui/src` returns:
- 1 production file: `argus/ui/src/components/AlertBanner.tsx` (the component itself).
- 1 mounting file: `argus/ui/src/pages/DashboardPage.tsx` (5 mount sites for the 4 layout branches × pre-market/non-pre-market).
- 0 references in `argus/ui/src/layouts/` (the canonical home for cross-page persistence in Session 5e).
- 1 test file (`AlertBanner.test.tsx`).

Close-out lines 81-84, 354-355 explicitly note 5e relocation. The Dashboard mount comment at line 149 reads:
```
{/* Critical alert banner — temporary placement; 5e moves to Layout */}
```

5e scope preserved. ✓

---

## Other Verifications

### V1. WebSocket contract verified end-to-end

| WS message | Backend producer | Frontend handler |
|---|---|---|
| `auth_success` | `alerts_ws.py:88-91` | `case 'auth_success'` (line 243) |
| `snapshot` | `alerts_ws.py:97-101` | `case 'snapshot'` (line 256) — applies `isVisible` filter |
| `alert_active` | `health.py:550-553` (`on_system_alert_event`) | `case 'alert_active'` (line 264) — `upsertAlert` |
| `alert_acknowledged` | `health.py:652-655` (`persist_acknowledgment_after_commit`) | `case 'alert_acknowledged'` (line 265) — `upsertAlert` |
| `alert_auto_resolved` | `health.py:917-920` (`_auto_resolve`) | `case 'alert_auto_resolved'` (line 266) — `upsertAlert` |
| `alert_archived` | NOT EMITTED today (documented in `alerts_ws.py:14`) | `case 'alert_archived'` (line 273) — defensive `removeAlert` |

`grep -n "alert_archived" argus/core/health.py` returns zero hits — confirming the close-out's claim that no producer exists today. The frontend handler is defensive forward-compat, which is fine.

### V2. Field-name alignment with backend wire format

Frontend `Alert` interface (useAlerts.ts:34-47) matches backend `AlertResponse` (alerts.py:50-67) and `_alert_to_payload` (health.py:125-153) field-for-field:
- `alert_id`, `alert_type`, `severity`, `source`, `message`, `metadata`
- `state` (NOT `status` — implementer correctly aligned with backend's `AlertLifecycleState` enum)
- `created_at_utc` (NOT `emitted_at_utc` — implementer correctly aligned)
- `acknowledged_at_utc`, `acknowledged_by`, `archived_at_utc`, `acknowledgment_reason`

The spec sketch in the impl prompt (lines 53-66) used `status` and `emitted_at_utc` — RULE-038-compliant grep-verification surfaced the mismatch. Close-out judgment-call #3 (lines 140-151) discloses the deviation.

`AlertState` union drops `auto_resolved` (the backend's `AlertLifecycleState` has only active/acknowledged/archived; auto-resolution transitions to `archived` and is differentiated by WS message type, not by state value). This is correct.

### V3. JWT auth pattern matches `useArenaWebSocket`

`useAlerts.ts:230-232`:
```ts
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'auth', token }));
};
```

Compared to `useArenaWebSocket.ts:209-216`:
```ts
ws.onopen = () => {
  const token = getToken();
  if (!token) {
    ws.close();
    return;
  }
  ws.send(JSON.stringify({ type: 'auth', token }));
};
```

Same pattern. The `useAlerts` version captures `token` once at effect-entry (line 209) and reads it inside `onopen` from the closure — which is a slightly different approach but functionally equivalent for the duration of one connection. Acceptable.

### V4. Vitest baseline independently verified

`cd argus/ui && npx vitest run` ran locally:
```
Test Files  117 passed (117)
     Tests  886 passed (886)
  Duration  12.68s
```

Matches close-out claim exactly (866 → 886 = +20 vs spec target +10). No flakes observed. ✓

### V5. Backend tests not broken by DEF-220 removal

Earlier `grep -rn "acknowledgment_required_severities" tests/` returned zero hits — close-out claim confirmed. CI's `pytest (backend)` job completed `success` per `gh run view 25078777514`. No regressions from the field removal.

### V6. RULE-050 (CI green on session-final commit) — SATISFIED

- Run ID: `25078777514`
- Commit SHA: `319747244a7b11fd20084568904f12af85e79295` (matches Session 5c anchor)
- Overall: `completed / success`
- `vitest (frontend)`: `completed / success`
- `pytest (backend)`: `completed / success`
- URL: `https://github.com/stevengizzi/argus/actions/runs/25078777514`

---

## Disposition of Implementer's Judgment Calls

The close-out flagged THREE judgment calls (none labeled MINOR_DEVIATION; all framed as RULE-038-compliant grep-verified deviations from the impl prompt's illustrative sketch):

| # | Judgment call | Disposition |
|---|---|---|
| 1 | Reconnect-gated refetch via `wasDisconnectedRef` (vs unconditional `refetch()` in spec sketch) | **ACCEPTED** — eliminates wasteful double-fetch on initial connect (snapshot already provides authoritative state), preserves last-write-wins for the recovery case. Test 4 explicitly verifies the gating works. |
| 2 | JWT auth on the WS connection (not in spec sketch) | **ACCEPTED** — the actual backend (`alerts_ws.py:75-86`) requires `{type: "auth", token}` as the first frame and closes 4001 if absent. Spec sketch was illustrative; implementer correctly followed RULE-038 by reading the actual producer. |
| 3 | Field-name alignment with backend wire format (`state`/`created_at_utc` vs spec's `status`/`emitted_at_utc`) | **ACCEPTED** — RULE-038-compliant. The backend's actual REST and WS shapes both use `state`/`created_at_utc`; spec sketch was illustrative. |

All three are deviations from the spec's *illustrative sketch*, not from spec *intent*. The spec explicitly says "Mirror this structure" referring to existing hooks like `useObservatory.ts` (which doesn't exist in this codebase — only `useObservatoryKeyboard.ts`); the implementer correctly used `useArenaWebSocket.ts` as the actual mirror reference, since that's the live precedent. RULE-011 satisfied.

---

## Sprint-Level Regression Checklist

| Invariant | Status | Note |
|---|---|---|
| Invariant 5 (Vitest baseline ≥ prior) | PASS | 866 → 886 (+20), exceeds spec target +10. Verified by independent rerun. |
| Invariant 14 (alert observability — frontend started) | PASS | `useAlerts` hook + Dashboard banner landed. New files exist; close-out claim supportable. |
| Invariant 15 (do-not-modify boundaries) | PASS | Modified files exactly match the close-out's scope claim: 4 new (hook, component, 2 test files), 4 modified (`DashboardPage.tsx`, `core/config.py`, both YAMLs). No edits to backend alerts code, HealthMonitor, REST routes, or WebSocket handler. |
| Invariant 17 (banner persistence) — partial | PASS in-scope | Banner renders on Dashboard. Cross-page persistence is 5e scope; verified 5c didn't silently land it at Layout level. |

---

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 frontend reviewer CONCERNS or ESCALATE) — NOT triggered. Verdict is CLEAR_WITH_NOTES.
- **B1, B3, B4, B6** — none triggered.
- **C7** (existing Vitest tests fail because the new fetch / WebSocket mocks broaden a global test-setup fixture) — NOT triggered. New mocks scoped via `vi.stubGlobal` / `vi.unstubAllGlobals` in `beforeEach`/`afterEach`. Full Vitest 866 → 886 with no regressions.

---

## Final Verdict + Recommended Next Action

**Verdict: CLEAR_WITH_NOTES.** The "_with notes_" qualifier captures three minor observations, none blocking:

1. **No explicit WS-reconnect logic** (F1 NOTE). The hook relies on REST polling (5s interval) after a disconnect. Matches `useArenaWebSocket` precedent and the spec sketch. Worth revisiting in a follow-up if operator observes alert-delivery latency post-disconnect.
2. **5xx ack-error path not behaviorally tested** (F4 NOTE). Intentional — error UI lands in 5d's modal per spec.
3. **`getToken() === null` early-return branch not tested** (close-out lines 312-316). Operationally fires only when JWT cleared mid-session; acceptable.

**Recommended next action:** Operator should:

1. The session is already committed as `3197472` and CI is green. No additional commit needed for the implementation.
2. Stage and commit this review verdict as a `chore(sprint-31.91)` commit per established sprint cadence.
3. Proceed to **Session 5d** (toast surface for non-critical severities).

**No remediation required.** The implementation matches spec intent at every load-bearing point that was verifiable against the actual codebase state (RULE-038), and the deviations from spec text (illustrative sketch vs actual backend wire format) were necessary, disclosed, and architecturally sound.

---

```json
{
  "session": "5c",
  "tier2_verdict": "CLEAR_WITH_NOTES",
  "deliverables": {
    "D1_useAlerts_hook": "CLEAR",
    "D2_AlertBanner_component": "CLEAR",
    "D3_dashboard_mount_sites": "CLEAR",
    "D4_def_220_disposition_option_a": "CLEAR",
    "D5_tests": "CLEAR (20 added, target ≥10)"
  },
  "review_focus_findings": {
    "F1_state_machine": "CLEAR_WITH_NOTE (no explicit WS reconnect; matches precedent)",
    "F2_rest_ws_race_ordering": "CLEAR",
    "F3_websocket_cleanup_on_unmount": "CLEAR",
    "F4_ack_error_handling": "CLEAR (5xx behavior path is type-safe but not behaviorally tested; deferred to 5d modal)",
    "F5_severity_styling_consistency": "CLEAR (matches ActionCard.tsx destructive-action idiom)",
    "F6_accessibility": "CLEAR (role=alert + aria-live=assertive + native button)",
    "F7_banner_dashboard_only": "CLEAR (zero references in argus/ui/src/layouts/)"
  },
  "ci_run_id": 25078777514,
  "ci_commit_sha": "319747244a7b11fd20084568904f12af85e79295",
  "ci_status": "completed",
  "ci_conclusion": "success",
  "ci_jobs": {
    "vitest_frontend": "success",
    "pytest_backend": "success"
  },
  "vitest_baseline_post_session_independently_verified": 886,
  "def_220_removal_grep_verified": true,
  "ws_contract_aligned_with_5a2_verified": true,
  "judgment_calls_disposition": {
    "1_reconnect_gated_refetch": "ACCEPTED",
    "2_jwt_auth_alignment": "ACCEPTED",
    "3_field_name_alignment_state_created_at_utc": "ACCEPTED"
  },
  "remediation_required": false,
  "next_action": "operator_proceed_to_session_5d"
}
```

---

*End Sprint 31.91 Session 5c Tier 2 review.*
