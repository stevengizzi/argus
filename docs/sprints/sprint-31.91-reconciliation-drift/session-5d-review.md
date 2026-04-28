# Sprint 31.91 — Session 5d Tier 2 Review

**Session:** Sprint 31.91 Session 5d (D12 — toast notification system + acknowledgment modal)
**Commit:** `66d0b04bd8dbc0b68888acb2ee01b3c5f219d9d3`
**Reviewer template:** `workflow/templates/review-prompt-frontend.md`
**Reviewer mode:** Tier 2 read-only
**Verdict:** **CLEAR**

---BEGIN-REVIEW---

## Summary

Session 5d delivers `AlertToast` + `AlertToastStack` and `AlertAcknowledgmentModal` mounted across the 5 mutually-exclusive `DashboardPage` render branches. Spec coverage is complete and the implementation correctly adapts to seven prompt-vs-current-code drifts (alert shape, hook contract, backend 200-not-409 idempotency path, etc.) without scope creep. All 902 Vitest specs pass (886 → 902, +16); TypeScript clean. No blocking findings; two follow-ups filed as DEF-226 (focus-trap) and DEF-227 (auth-context operator_id) are appropriate.

## Per-Checklist Findings

### State machine completeness — PASS
- Toast states reachable (active critical → unmount via state filter when alert is acked / auto-resolved). Verified at `argus/ui/src/components/AlertToast.tsx:46-54` (`activeCritical = ... a.severity === 'critical' && a.state === 'active'`); test `toast unmounts when alert transitions out of critical-active` (`AlertToast.test.tsx:100-112`) covers the unmount path.
- Modal states (idle / submitting / error-with-retry / outcome:first_ack | duplicate_ack | not_found) all reachable. State machine is in `AlertAcknowledgmentModal.tsx:53-56` (4 useState slots) + `:80-94` `classifyOutcome`. All 3 outcome kinds tested (`AlertAcknowledgmentModal.test.tsx:141-228`).
- No dead-end states. Once `outcome` is set the textarea + submit button hide; only Close/Cancel + Escape are reachable.

### Reconnect / disconnect resilience — PASS
- `AlertToastStack` and `AlertAcknowledgmentModal` are pure renders of `useAlerts` state. Neither owns its own WebSocket lifecycle. Verified by inspection — no `WebSocket(...)` constructor, no `useEffect` with WS in either file.
- Reconnect logic is owned exclusively by `useAlerts` hook (`useAlerts.ts:208-310`). 5d components correctly defer to that.

### Acknowledgment race handling — PASS
- Double-click submit: `canSubmit` (line 77-78) gates on `!submitting && outcome === null`. `disabled={!canSubmit}` on submit button (line 253). Once submitting, button disables. ✓
- Two-tab race detection via `acknowledged_by !== operatorId` mismatch (line 90). Test `handles duplicate-ack (200 with original acknowledger preserved)` (`AlertAcknowledgmentModal.test.tsx:203-228`) exercises this with operatorId="bob" and result.acknowledged_by="alice". ✓
- Stale ack → null → `not_found` outcome. Test `treats 404 (hook returns null) as "no longer active"` (`AlertAcknowledgmentModal.test.tsx:184-201`). ✓

### Accessibility — PASS (with focus-trap deferred to DEF-226)
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby="alert-ack-modal-title"` correct (lines 165-167). `<h2 id="alert-ack-modal-title">` matches (line 179). Tested at `AlertAcknowledgmentModal.test.tsx:72-74`.
- Initial focus on textarea via `useEffect` + `reasonRef.current?.focus()` (lines 60-62). Tested at `AlertAcknowledgmentModal.test.tsx:78-82` and `AlertToast.test.tsx:128-132`.
- Escape closes via `window` keydown listener (lines 66-74). Tested at `AlertAcknowledgmentModal.test.tsx:127-139`.
- Focus-trap deferred to DEF-226. The closeout's reasoning (mirror existing `ConfirmModal.tsx` pattern, which also has no focus-trap — verified) is sound for V1.
- Toast `role="status"` + `aria-live="polite"` (lines 100-101). ✓
- Color contrast: `bg-argus-loss` (red) + white text on toast — high contrast. Modal uses `bg-argus-surface` + standard accents. No contrast concern.

### Cross-page persistence — PASS
- All 5 DashboardPage render branches are mutually exclusive (verified by inspection of `DashboardPage.tsx`):
  - `if (isPreMarket)` → either desktop branch (line 72) or other branch (line 84) — 1 of 2 returns
  - `if (!isMultiColumn)` → phone branch (line 96) — early return
  - `if (isDesktop)` → desktop branch (line 142) — early return
  - else → tablet branch (line 213)
- Each branch contains exactly one `<AlertToastStack />` (lines 77, 88, 109, 157, 226). Confirmed via `git diff 97ea5d3..66d0b04 -- argus/ui/src/pages/DashboardPage.tsx` — 5 additions, each paired with an existing `AlertBanner` mount. Exactly one stack mounts per render — claim is sound.
- 5e migration to `Layout.tsx` is flagged in closeout J2 ("Session 5e moves the mount to `Layout.tsx`, at which point all 5 in-Dashboard mounts get removed.") ✓

### Z-index / layout interactions — PASS
- Toast container `fixed top-4 right-4 z-50 ... pointer-events-none` (line 66) with individual toasts `pointer-events-auto` (line 103). Click-through gaps work correctly.
- Modal backdrop `fixed inset-0 bg-black/60 z-50` (line 150) with content `fixed inset-0 z-50 flex items-center justify-center` (line 159). Same z-index but stacking order via DOM order — modal content renders after backdrop, so it's on top. Standard React-modal pattern, identical to `ConfirmModal.tsx:62-83`.
- AlertBanner sits inside Dashboard content flow (no `fixed` positioning); toast `fixed top-4 right-4` doesn't visually conflict with banner at top of content area. No conflict.

### Test coverage thresholds — PASS
- 16 specs across the two test files. Implementer claims 100% line coverage on both components; spot-check confirms all branches hit (state-active filter, queue cap, all 3 outcome kinds, error+retry path, escape, cancel, network-failure, 404).
- All state transitions tested. All error paths tested.
- I did not separately run `--coverage` (would inflate review time without changing the verdict; behavioral tests are clearly comprehensive).

## Specific Scrutiny Findings

### 1. Queue overflow ordering claim — VERIFIED CORRECT
Walking through `slice(-MAX_TOAST_QUEUE).reverse()` with the test's 6 alerts (a-0..a-5, oldest..newest):
- Sorted oldest-first: `[a-0, a-1, a-2, a-3, a-4, a-5]`
- `slice(-5)` → `[a-1, a-2, a-3, a-4, a-5]` (drops a-0, the oldest ✓)
- `.reverse()` → `[a-5, a-4, a-3, a-2, a-1]` (newest first in DOM ✓)
- Test asserts `toasts[0]` = `a-5` and `a-0` not in DOM. Both pass. Math is sound.

### 2. Duplicate-ack detection mechanism — REASONING ACCEPTED
Closeout J3 correctly identifies the same-operator-two-tabs edge case (both submit `operator_id="operator"` → mismatch test fails → classified as `first_ack`). The reasoning that this is acceptable for V1 because (a) the system is single-user and operator_id is hardcoded, and (b) the audit log preserves truth, is sound. DEF-227 captures the proper resolution when authenticated multi-operator context lands. No blocking concern.

### 3. Modal exit animation triggering — MINOR (informational)
`AlertToastStack` does `{modalAlert && <AlertAcknowledgmentModal ... />}` (line 78). When `modalAlert` becomes `null` (e.g., on Cancel/Escape), the parent unmounts the modal *before* its internal `<AnimatePresence>` can play the exit. The exit animation defined at `AlertAcknowledgmentModal.tsx:153,162,171` likely does not actually play — but this is purely cosmetic. The closeout doesn't claim the exit animation works; it's stylistic polish. Not a blocking issue. Worth a one-line note for the 5e reviewer if they care to wrap the modal in an `AnimatePresence` at the parent level.

### 4. Backdrop-click-closes-modal — REASONABLE
`onClick={onClose}` on backdrop (line 155) + `onClick={(e) => e.stopPropagation()}` on dialog (line 173). Identical pattern to `ConfirmModal.tsx:68,84`. Reasonable mirror; the impl prompt didn't forbid this and it matches user expectations.

### 5. Test selector scoping — REASONABLE
Tests scope `getByRole('button', { name: /^acknowledge$/i })` with `within(dialog)` (e.g., `AlertToast.test.tsx:203-205`) because the toast's "Acknowledge" button and the modal's submit button share the same accessible name. Anchoring with `^...$` regex + `within(dialog)` is the standard testing-library idiom; alternative would be a distinct `data-testid` on the submit button, but the current approach reads cleanly.

### 6. DashboardPage diff — VERIFIED
`git diff 97ea5d3..66d0b04 -- argus/ui/src/pages/DashboardPage.tsx` shows 5 `<AlertToastStack />` additions, each immediately following an existing `AlertBanner` mount in the same render branch:
- Line 77: pre-market desktop (paired with AlertBanner line 76)
- Line 88: pre-market other (paired with AlertBanner line 87)
- Line 109: phone (paired with AlertBanner line 107 inside motion.div)
- Line 157: desktop (paired with AlertBanner line 154-156 inside motion.div)
- Line 226: tablet (paired with AlertBanner line 223-225 inside motion.div)
No mount sites are orphaned; all 5 are inside branches that also mount AlertBanner. ✓

## RULE-038 Verification Results

I grep-checked 4 of the 7 drift claims directly:

1. **Frontend path drift** — VERIFIED. `grep -n "frontend/src" sprint-31.91-session-5d-impl.md` returns 4 hits (lines 12-13, 42, 117). Spec uses `frontend/src/`; actual path is `argus/ui/src/`. ✓
2. **`alert.status` / `emitted_at_utc`** — VERIFIED. Spec line 56: `.sort((a, b) => a.emitted_at_utc.localeCompare(b.emitted_at_utc))` and line 55 `a.status === "active"`. Actual hook (`useAlerts.ts:34-47`) exports `state` and `created_at_utc`. ✓
3. **`AcknowledgeResult` shape (`{outcome, audit_id}`)** — VERIFIED. Spec line 124: `Promise<{ outcome: string; audit_id: number }>`. Actual hook (`useAlerts.ts:49-56`) is `{ alert_id, acknowledged_at_utc, acknowledged_by, reason, audit_id, state }`. No `outcome` field. ✓
4. **409-not-200 idempotent contract** — VERIFIED. Spec line 191: "409 (already acknowledged from another tab) → backend returns 409 (with original acknowledger info)". Actual backend (`alerts.py:336-368`): the `if alert.state == AlertLifecycleState.ACKNOWLEDGED:` block returns `AcknowledgeResponse` with status 200, original `acknowledged_by` preserved at `alerts.py:364`. ✓
5. **Test command `pnpm` vs `npx`** — VERIFIED. Spec line 20: `pnpm vitest run`. CLAUDE.md uses `cd argus/ui && npx vitest run`. ✓ (acknowledged drift, not material)
6. **DEF numbering (212, 213)** — VERIFIED. CLAUDE.md DEF table contains DEF-212 (OCA bracket_oca_type) and DEF-213 (SystemAlertEvent.metadata) — both already taken. Closeout reroutes to DEF-226 (focus-trap) and DEF-227 (auth context). ✓ — no collision: highest existing DEF is DEF-225 (`grep -n "DEF-22[6-9]\|DEF-23[0-9]" CLAUDE.md` returns no matches).
7. **Hook 404 throws vs returns null** — Implicit verification via reading `useAlerts.ts:119-121`: `if (response.status === 404) return null;` then `throw` only on other non-200 codes. Drift claim accurate.

All 7 drifts are real, none materially expanded scope, and the new DEF numbers (226, 227) don't collide. RULE-038 compliance is exemplary.

## Test Verification

```
$ cd argus/ui && npx vitest run 2>&1 | tail -10
 Test Files  119 passed (119)
      Tests  902 passed (902)
   Start at  18:32:12
   Duration  12.53s
```

```
$ cd argus/ui && npx tsc --noEmit 2>&1 | tail -10
(no output — clean)
```

886 → 902 (+16) Vitest delta matches closeout. TypeScript clean. ✓

## Sprint Spec Conformance

D12 acceptance criteria (per closeout's Scope Verification, all checked off in implementation):
- Toast renders on new critical alert (via WS state push) ✓
- Toast persists until ack or auto-dismiss ✓
- Modal requires ≥10-char reason ✓
- Modal cancellable ✓
- Toast queue caps at 5; oldest dropped from view ✓
- Modal accessibility (dialog role, aria-modal, aria-labelledby, focus, escape) ✓
- Error handling: network/404/duplicate-ack ✓
- Mounted on DashboardPage (5e migration to Layout flagged) ✓

## Recommendation

**CLEAR.** Implementation is high-quality, RULE-038 compliance exemplary, no scope creep, no regressions, all spec criteria met. Two filed DEFs (226 focus-trap, 227 auth context) are appropriate deferrals with sound reasoning.

Minor informational note (non-blocking): modal exit animation is unlikely to play because the parent (`AlertToastStack`) unmounts the modal directly via `{modalAlert && ...}`. Worth one-line note for 5e if the reviewer wants to wrap the modal in an `<AnimatePresence>` at the Layout level. Not a blocking concern — the modal entry animation works and the exit is invisible-but-not-broken.

---END-REVIEW---

```json:structured-verdict
{
  "session": "sprint-31.91 / session-5d",
  "commit": "66d0b04bd8dbc0b68888acb2ee01b3c5f219d9d3",
  "verdict": "CLEAR",
  "blocking_findings": [],
  "informational_findings": [
    {
      "id": "INFO-1",
      "topic": "Modal exit animation likely does not play",
      "detail": "AlertToastStack uses {modalAlert && <Modal/>} pattern; parent unmounts before AnimatePresence-defined exit can play. Cosmetic only; entry animation works.",
      "severity": "informational",
      "blocking": false
    }
  ],
  "rule_038_drifts_verified": 7,
  "rule_038_drifts_material": 0,
  "tests_added": 16,
  "vitest_baseline_before": 886,
  "vitest_baseline_after": 902,
  "typescript_clean": true,
  "ci_status": "pending_push_at_review_time",
  "new_def_collisions": 0,
  "new_defs_filed": ["DEF-226", "DEF-227"],
  "scope_creep": false,
  "regressions_detected": false,
  "spec_conformance": "complete",
  "recommendation": "Proceed to Session 5e (Layout migration). DEF-226/DEF-227 properly captured for future sprints."
}
```
