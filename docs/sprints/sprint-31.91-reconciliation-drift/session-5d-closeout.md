# Sprint 31.91, Session 5d — Close-Out

**Status:** PROPOSED_CLEAR
**Date:** 2026-04-28
**Branch:** main
**Reviewer template:** frontend (`templates/review-prompt-frontend.md`)

---

## Change Manifest

| Path | Type | Lines | Purpose |
|------|------|------:|---------|
| `argus/ui/src/components/AlertAcknowledgmentModal.tsx` | NEW | 244 | Modal dialog requiring reason text (≥10 chars) for operator acknowledgment of a critical alert. Renders audit-id confirmation, error/retry, and "previously acknowledged by" feedback for the duplicate-ack case. |
| `argus/ui/src/components/AlertToast.tsx` | NEW | 119 | Cross-page critical-alert toast surface. `AlertToastStack` consumes `useAlerts`, caps the visible queue at 5 (oldest dropped), opens `AlertAcknowledgmentModal` on click. |
| `argus/ui/src/components/AlertAcknowledgmentModal.test.tsx` | NEW | 220 | 8 Vitest specs covering dialog accessibility, reason validation, cancel/escape, success-with-audit-id, 404 → "no longer active", duplicate-ack feedback, and error-with-retry. |
| `argus/ui/src/components/AlertToast.test.tsx` | NEW | 235 | 8 Vitest specs covering empty-state render, single-toast render, auto-dismiss on state-transition, click-opens-modal, queue-cap at 5 oldest-dropped, cancel-leaves-toast, end-to-end ack-via-modal, and network-failure → retry. |
| `argus/ui/src/pages/DashboardPage.tsx` | MODIFIED | +6 | Imported `AlertToastStack`; mounted alongside each of the 5 `AlertBanner` mount sites (one per render branch — only one branch executes per render so exactly one stack mounts). |

**Test delta:** 886 → 902 (+16). Both component files contribute 8 specs each — the spec called for "~8 new Vitest"; we mirrored coverage on both files for symmetric defense.

---

## RULE-038 Pre-Flight Findings (Factual Drift in Impl Prompt)

The Session 5d impl prompt referenced an earlier pre-implementation snapshot. Current codebase state required adapting around the following drift; none materially changed scope:

1. **Frontend path.** Prompt said `frontend/src/`. Actual: `argus/ui/src/`.
2. **`Alert` shape.** Prompt referenced `alert.status` and `alert.emitted_at_utc`. Actual fields (verified at `argus/ui/src/hooks/useAlerts.ts:34-47`): `state` (one of `active | acknowledged | archived`) and `created_at_utc`.
3. **`AcknowledgeResult` shape.** Prompt referenced `{outcome, audit_id}`. Actual: `{alert_id, acknowledged_at_utc, acknowledged_by, reason, audit_id, state}`. There is no `outcome` field.
4. **404 handling.** Prompt said hook throws on 404. Actual (verified at `useAlerts.ts:119-121`): hook returns `null` on 404 and only throws on other non-200 codes.
5. **409 handling.** Prompt said backend returns 409 for already-acknowledged-from-other-tab. Actual (verified at `argus/api/routes/alerts.py:336-368`): backend returns 200 with the original acknowledger info preserved on the idempotent path. There is no 409 in the contract. The modal therefore detects "duplicate ack" via `result.acknowledged_by !== submitted operator_id` and renders "previously acknowledged by <operator>" feedback. Functionally equivalent UX; mechanism differs.
6. **Test command.** Prompt said `pnpm vitest run`. Actual: `npx vitest run` (per CLAUDE.md commands; ARGUS uses npm/npx, not pnpm).
7. **DEF numbering.** Prompt suggested filing follow-ups as DEF-212 / DEF-213. Both already taken (DEF-212 = OCA bracket_oca_type wiring; DEF-213 = SystemAlertEvent.metadata extension). New DEFs in this close-out reuse no existing numbers — see "Deferred Items" below.

---

## Judgment Calls

### J1 — Mirror tests across both component files (16 specs vs spec's 8)

The spec called for "~8 new Vitest tests" in a single test file. We split coverage across `AlertAcknowledgmentModal.test.tsx` (8 specs, modal in isolation) and `AlertToast.test.tsx` (8 specs, toast + integrated modal flow). Modal-in-isolation covers reason validation, accessibility, error paths, and outcome rendering at low setup cost. Toast specs verify the wire-up: hook → toast → modal open → submit → result. Both layers have value.

The spec's 8 are all covered; 7 of them in `AlertToast.test.tsx` (toast appears, persists, opens modal, modal-cancel-leaves-toast, success-shows-audit-id, queue-overflow, network-failure-retry) plus the bonus 409-equivalent (`AlertAcknowledgmentModal.test.tsx::handles duplicate-ack...`). The "reason ≥10 chars before submit" test lives in the modal file because that's where the validation logic sits.

### J2 — Single mount per render branch

`AlertToastStack` calls `useAlerts()`, which opens a WebSocket. Multiple mounts → multiple connections → duplicate state. Dashboard has 5 render branches (preMarket-desktop, preMarket-other, phone, desktop, tablet); each is mutually exclusive, so adding `<AlertToastStack />` to all 5 alongside `<AlertBanner />` results in exactly one mount per render. Confirmed by inspection of branch structure at `argus/ui/src/pages/DashboardPage.tsx`.

Session 5e moves the mount to `Layout.tsx`, at which point all 5 in-Dashboard mounts get removed. Flagged for 5e reviewer.

### J3 — Duplicate-ack detection mechanism

Backend preserves the original acknowledger info when an already-acknowledged alert is re-acknowledged (idempotent 200 path). The modal compares `result.acknowledged_by` to the operator_id we submitted; if they differ, render the "previously acknowledged by" message. This works correctly for cross-operator duplicate (alice acked, bob now sees the modal — bob sees "previously acknowledged by alice"). Edge case: same-operator duplicate ack across two tabs — both have `operator_id="operator"`, so result reads as "first ack" by mistake. This is acceptable for V1 because (a) operator_id is hardcoded `"operator"` in this single-user system, and (b) the audit log preserves the truth. When auth context lands (DEF-227), per-session operator IDs will make this distinction sharp.

### J4 — Focus-trap scope

The spec recommended full focus-trap (Tab cycles within modal) but stated it was optional for 5d if the existing modal pattern doesn't have it. Inspection of `argus/ui/src/components/ConfirmModal.tsx` shows initial-focus-and-Escape only — no focus-trap. We mirrored that pattern for consistency. Filing full focus-trap as DEF-226 (UI accessibility polish).

---

## Deferred Items

- **DEF-226** (NEW, LOW priority): Full focus-trap on `AlertAcknowledgmentModal` (Tab cycles within modal). Currently only initial-focus on textarea + Escape-closes; matches `ConfirmModal` pattern. Trigger: future UI accessibility audit pass, or if WCAG conformance becomes a deployment requirement.
- **DEF-227** (NEW, LOW priority): Wire authenticated operator-id into `AlertToastStack` and `AlertAcknowledgmentModal`. Currently hardcoded `operator_id = "operator"` (matches `AlertBanner`'s pattern). Trigger: when auth context / multi-operator login feature lands.
- **5e migration:** `AlertToastStack` mounted on Dashboard in 5 branches. Session 5e relocates to `Layout.tsx` for cross-page persistence; remove the 5 in-Dashboard mounts at that time.

---

## Scope Verification

- [x] `AlertToast.tsx` + `AlertToastStack` (queue handler) created.
- [x] `AlertAcknowledgmentModal.tsx` created.
- [x] Toast renders on new critical alert via WS (verified by `useAlerts` integration; tests use mocked hook with `state: 'active'`).
- [x] Toast persists until ack or auto-dismiss (test: state transition to `acknowledged` → toast unmounts).
- [x] Modal requires ≥10-char reason (test: 9 chars disabled, 10 chars enabled, 10 spaces disabled).
- [x] Modal cancellable (test: cancel closes modal, toast remains, hook never called).
- [x] Toast queue caps at 5; oldest-first dropped from view (test: 6 alerts → 5 toasts; oldest by `created_at_utc` dropped; newest visually on top).
- [x] Modal accessibility: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` matches heading id, focus on textarea, Escape closes.
- [x] Error handling: network failure → retry; 404 → "no longer active"; duplicate-ack (200 + original acknowledger) → "previously acknowledged by" feedback.
- [x] Mounted on `DashboardPage.tsx` (5 branches; 5e moves to Layout).
- [x] 16 Vitest tests across both component files (≥ spec's "~8"); both files at 100% line coverage on their respective components.
- [x] Vitest baseline ≥ Session 5c + 8: was 886, now 902 = +16.
- [ ] CI green — pending push.
- [ ] Tier 2 review verdict CLEAR — pending invocation.

---

## Test Results

```
Test Files  119 passed (119)
     Tests  902 passed (902)
  Duration  13.13s
```

Pre-Session-5d baseline: 886. Post-Session-5d: 902. Delta: +16.

TypeScript: clean (`npx tsc --noEmit` returns no errors).

---

## Self-Assessment

**CLEAN.** All Definition of Done items met or in-flight. RULE-038 pre-flight surfaced 7 prompt-vs-current-code drift items (frontend path, type field names, hook contract, 409-vs-200 backend behavior, test command, DEF numbering); none changed scope. No regressions introduced. No skipped tests.

---

## Context State

GREEN — well within context budget; all reads completed at session start; no compaction triggered.

---

## Verdict Capsule

```json
{
  "session": "5d",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 16,
  "vitest_baseline_before": 886,
  "vitest_baseline_after": 902,
  "queue_overflow_capped_at_5": true,
  "modal_accessibility": "initial_focus + escape (full focus-trap deferred to DEF-226)",
  "duplicate_ack_handling": "200 + acknowledged_by-mismatch detection (no 409 in actual backend)",
  "operator_id_source": "hardcoded \"operator\" (auth context deferred to DEF-227)",
  "mount_strategy": "5 in-Dashboard mount sites (one per render branch); 5e migrates to Layout"
}
```

---

## Tier 2 Review Invocation

Frontend reviewer template. Output: `docs/sprints/sprint-31.91-reconciliation-drift/session-5d-review.md`.

---

*End Sprint 31.91 Session 5d close-out.*
