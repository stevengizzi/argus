# Sprint 31.91 — Session 5e Tier 2 Review

**Session:** Sprint 31.91 Session 5e (D13 — Observatory alerts panel + cross-page mount + scope-expansion `/audit` endpoint)
**Commit:** `7efd0a0b6d09730f81f97e5216a5c3ca248ccf96`
**Reviewer template:** `workflow/templates/review-prompt-frontend.md`
**Reviewer mode:** Tier 2 read-only
**Verdict:** **CLEAR**

---BEGIN-REVIEW---

## Summary

Session 5e delivers the final implementation deliverable of Sprint 31.91: the Observatory `AlertsPanel` (active + historical browsing surface with filters, sorts, date-range picker, and detail modal), the cross-page `AlertBanner` + `AlertToastStack` mount in `AppShell.tsx` (replacing 5 per-branch mounts in `DashboardPage`), AND a scope-expanded backend `GET /api/v1/alerts/{alert_id}/audit` endpoint added per the spec's halt-and-fix directive (lines 124–132). 121 Vitest files / 913 specs pass (902 → 913, +11; spec target ≥912 — exceeded by 1). 15 pytest specs in `tests/api/test_alerts.py` pass (12 → 15, +3). TypeScript clean. RULE-038 drift handling exemplary — six factual drifts in the impl prompt resolved without scope creep. RULE-007 scope expansion explicitly acknowledged and analyzed. Three new DEFs (228/229/230) collision-free.

## Per-Checklist Findings

### State machine completeness — PASS
- **AlertsPanel:** loading / empty / data states all reachable. `AlertsTable` empty branch at `AlertsPanel.tsx:124-132` renders distinct test-id'd empty marker; data branch renders the table. Active and history tables share the same component, so both inherit the same state machine. No error state on `useAlertHistory` is surfaced — captured under DEF-230 for follow-up.
- **AlertDetailView:** isLoading exposed via `useAlertAuditTrail` (`AlertsPanel.tsx:251`), audit-empty state at `:337-345` test ("renders audit-empty placeholder"). Modal close paths via Close button + backdrop click — both tested.
- **No dead-end states.** Detail modal closable via Close button (`onClose` prop) and backdrop `onClick={onClose}` (`AlertsPanel.tsx:262`); inner content stops propagation (`:266`). Standard React-modal idiom.
- **Sort + filter state:** all 4 sort keys (severity / source / symbol / created_at_utc) and all 3 filter dimensions reachable from tests at `AlertsPanel.test.tsx:185` (sort) and `:243` (filter).

### Reconnect / disconnect resilience — N/A (correctly delegated)
The spec note in this review's instructions correctly identifies that `AlertsPanel` reuses the existing `useAlerts` hook unchanged — WS lifecycle is owned by 5c's hook (`useAlerts.ts:96-340`). Two new sub-hooks (`useAlertHistory`, `useAlertAuditTrail`) are pure REST via TanStack Query — they don't own a WS lifecycle. No new resilience surface to verify.

### Cross-page persistence — PASS (structural pin verified)
- `AppShell.tsx:128-131` mounts `AlertBanner` (wrapped in z-40 sticky div) + `AlertToastStack` outside the `<Outlet>` so navigation re-renders the route element but not the alert mounts. Verified by reading `AppShell.tsx` lines 110–145 — both mounts sit before the `<main>` outlet.
- Regression invariant 17 pin: `AppShell.alerts.test.tsx:163-184` — three `act(() => navigateRef!('/path'))` calls, each followed by `expect(screen.getByRole('alert')).toBeInTheDocument()`. The test will fail if the mount is reverted to a per-page mount. This is the structural pin the spec called for.
- `DashboardPage.tsx` cleanup verified: `grep -n "AlertBanner\|AlertToastStack" argus/ui/src/pages/DashboardPage.tsx` returns ZERO matches. All 5 prior mount sites removed.
- `AppShell.test.tsx:27-28` adds two pre-existing test isolations (`vi.mock('../components/AlertBanner', () => ({ AlertBanner: () => null }))` + same for AlertToast) so the existing keyboard-shortcut tests don't pull in `useAlerts` requiring a `QueryClientProvider` ancestor. Sound.

### Z-index / layout interactions — PASS (with one minor observation)
Sketched stacking order:
- `AlertBanner` wrapper: `z-40` (`AppShell.tsx:128`) with `absolute top-0 left-0 right-0 px-4 pt-2 min-[1024px]:left-16` — sits above page content but below all `z-50` overlays.
- `AlertToastStack`: `fixed top-4 right-4 z-50` (`AlertToast.tsx:66`) with `pointer-events-none` on the container and `pointer-events-auto` on individual toasts — click-through gaps work.
- `AlertAcknowledgmentModal`: backdrop `fixed inset-0 bg-black/60 z-50` (`AlertAcknowledgmentModal.tsx:150`) + content wrapper `fixed inset-0 z-50` (`:159`).
- `AlertDetailView` (5e): `fixed inset-0 z-50 flex items-center justify-center bg-black/60` (`AlertsPanel.tsx:261`) with content stop-propagation at `:266`.

Modal-on-toast-on-banner ordering is correct: banner z-40 (always below); toast/modal both z-50 with last-render-wins via DOM order. Detail modal mounts later than toast (because the toast is rendered at AppShell level, the detail modal is rendered inside the Observatory page) — so detail-modal-on-toast works. AlertAcknowledgmentModal also covers toasts (modal is rendered as a sibling to the toast container in `AlertToastStack` only when `modalAlert !== null`, but the modal's `fixed inset-0` covers the entire viewport regardless).

**Minor observation (informational, non-blocking):** `AlertDetailView` at z-50 will overlap with `AlertToastStack` (also z-50) if both happen simultaneously (rare — operator opens detail modal AND a new critical alert arrives). DOM order favors the detail modal because it's mounted in the route subtree (`Observatory`) which renders later than `AppShell`'s toast mount. This is the same coexistence pattern Session 5d already had between the acknowledgment modal and toasts — accepted as V1 behavior.

### Test coverage thresholds — PASS
- 8 AlertsPanel specs (verified by `grep "^  it" AlertsPanel.test.tsx | wc -l` = 8) — matches spec target of 8.
- 3 AppShell.alerts integration specs — exceeds spec's 2 by 1 (closeout discloses this delta).
- 3 backend audit-trail specs (`TestGetAlertAuditTrail`: ordered return / empty list / 401 auth).
- Total Vitest delta: +11 (902 → 913). Closeout reports same. Total spec count target was Session 5d + 10 = 912; actual is 913.

### `/audit` endpoint scope expansion — RULE-007 acknowledgment ACCEPTED
**Per the spec's halt-and-fix directive at lines 124–132:** "If no GET endpoint exists, halt this session, file as a small fix-it task (likely 5-line addition to argus/api/routes/alerts.py), apply, then resume 5e."

The implementation correctly:
1. Verified pre-existence via the spec-prescribed grep — confirmed absent.
2. Added `AuditEntryResponse` Pydantic model + `GET /{alert_id}/audit` handler (~57 LOC additions per close-out's change manifest, verified via `git diff --stat`).
3. Added 3 backend tests covering ordered return, empty list (unknown id), and 401 auth.
4. Used `id AS audit_id` SQL aliasing at `argus/api/routes/alerts.py:303` to bridge the schema column name (`id`) to the wire field name (`audit_id`) used by `AcknowledgeResponse.audit_id` semantics. The aliasing is documented in an inline comment at `:299-300`.
5. Closeout RULE-007 acknowledgment at lines 49–63 explicitly flags this as a scope expansion and frames the bundled-vs-Impromptu-D evaluation for the reviewer.

**Reviewer evaluation of the bundled approach:** ACCEPTED.
- The spec itself directed halt-and-fix-and-resume rather than carve-out into a separate Impromptu D.
- The endpoint is purely additive — no existing handler, schema, migration, or test was modified.
- Without it, the frontend's `AlertDetailView` audit-trail rendering would ship with a broken contract for one round-trip (the hook would fetch a 404).
- The split into a separate Impromptu D would have introduced session-ordering complexity for ~5 lines of router code, ~10 lines of Pydantic, and ~90 lines of tests. The bundled approach is proportionate to the work.
- 3 backend tests at appropriate granularity (positive case, empty case, auth gate); follows existing `TestPostAlertAcknowledge*` patterns.

### Observatory mount approach (J1) — ACCEPTED
The closeout's J1 judgment call (toggle overlay vs 5th view) is sound. The Observatory's keyboard-shortcut hook (`useObservatoryKeyboard.ts`) and view-tab UI (`SessionVitalsBar`) form a tight 4-view abstraction; adding a 5th view would have invaded 5 files for what is structurally a side-panel concern, not a primary view. The toggle at `data-testid="observatory-alerts-toggle"` (`ObservatoryPage.tsx:169`) keeps the panel closed by default — existing Observatory tests are not affected by the new `useAlerts` / `useAlertHistory` hook side effects. Reviewer confirms this aligns with the spec's reviewer-focus item 3 ("if 5e renders an empty state, that's not wrong").

### Date-range default (J2) — ACCEPTED
Default = last 7 days, UTC day boundaries (`AlertsPanel.tsx:55-60` `defaultHistoryRange()`). UTC is correct because the alert ledger is UTC-anchored (`Alert.created_at_utc`); converting to ET for the picker would have introduced a display/storage divergence. 7-day window is a reasonable practical default for session-recovery / post-mortem use cases. Aligns with spec's reviewer-focus item 4.

### Backend `/history` `until` deferral (J3) — ACCEPTED
Per spec line 98, the backend's `/history` endpoint supports `since` only; `to` is filtered client-side via `all.filter((a) => a.created_at_utc <= range.to)` at `useAlerts.ts:377`. When the backend grows `until`, the call site does not change (the filter becomes a no-op). DEF-228 captures the follow-up correctly.

## Specific Scrutiny Findings

### 1. RULE-038 drift handling — EXEMPLARY
Six factual drifts in the impl prompt, all caught and resolved without scope creep:
1. Path drift: `frontend/src/` → `argus/ui/src/` (resolved by closeout RULE-038 #1).
2. Layout file: `Layout.tsx` → `AppShell.tsx` (resolved by RULE-038 #2; route shell is structurally identical for the spec's intent).
3. Page count: spec said "10 pages" — verified accurate (RULE-038 #3).
4. Test command: `pnpm` → `npx` (cosmetic, RULE-038 #4).
5. `/audit` endpoint pre-existence: did NOT exist (RULE-038 #5; halt-and-fix triggered).
6. DEF numbering: spec suggested DEF-214/215, both taken; rerouted to DEF-228/229/230 (RULE-038 #6).

All six drifts disclosed in the closeout's "RULE-038 Pre-Flight Findings" block. Same exemplary pattern Session 5d demonstrated.

### 2. `id AS audit_id` aliasing — VERIFIED CORRECT
The schema column name in `argus/data/migrations/operations.py` is `id` (auto-increment PK). The wire field name in `AuditEntryResponse` is `audit_id` to match `AcknowledgeResponse.audit_id` (set in 5a.1's acknowledge response). The SELECT at `:303` aliases `id AS audit_id`, then constructs `AuditEntryResponse(audit_id=row["audit_id"], ...)` at `:313-314`. Inline comment at `:299-300` documents the rationale. The closeout's claim at line 58 is accurate. Aliasing is the correct shape — no need to rename either side.

### 3. Cross-page integration test reliability — VERIFIED
`AppShell.alerts.test.tsx:127-146` uses `MemoryRouter` + nested `<Routes>` with plain `<div>` route elements. Pattern mirrors `AppShell.test.tsx`'s existing keyboard tests. Heavy-dependency mocks (`Sidebar`, `MobileNav`, `live store`, `copilotUI store`, `SymbolDetailPanel`, `CopilotPanel`/`CopilotButton`) all mirror `AppShell.test.tsx:14-50` — no one-off custom harness. `useAlerts` is mocked at module level via `vi.mock` with a stateful `mockState.alerts` reassignable between tests. `useNavigate` captured via `<CaptureNavigate />` ref-capture pattern — clean idiom.

### 4. Toast appearance test (rerender pattern) — REASONABLE
The "AlertToast appears on TradeLog page" test at `:186-220` uses a `rerender(<MemoryRouter ...>)` pattern after mutating `mockState.alerts`. This is a common idiom in the codebase for module-level mock stores (see e.g., `AlertBanner.test.tsx`). Slightly verbose because the entire MemoryRouter tree is re-passed, but functionally correct and tests pass deterministically.

### 5. Backend test seeding via direct INSERT — REASONABLE
`TestGetAlertAuditTrail` uses direct `INSERT` against `alert_acknowledgment_audit` rather than going through the acknowledge handler. This isolates the audit-trail-fetch from the acknowledge-side state machine and matches the existing `_migrate_operations_db` helper pattern. Sound deterministic seeding.

### 6. DEF numbering hygiene — VERIFIED
- DEF-228 / DEF-229 / DEF-230: `grep -n "DEF-22[8-9]\|DEF-230" CLAUDE.md` returns zero matches. Highest in CLAUDE.md is DEF-225.
- DEF-226 / DEF-227 already filed by Session 5d's Work Journal register at `work-journal-register.md:146-147` — closeout correctly notes the avoided collision.
- The closeout's "first draft incorrectly reused those numbers; corrected before commit" disclosure (line 252) is honest and matches the actual final state.

### 7. Modal exit animation observation (carry-over from 5d review) — STILL APPLIES (informational)
Same pattern as 5d's `AlertToastStack`: `AlertsPanel.tsx:301-304` does `{selectedAlert && <AlertDetailView .../>}` so the modal unmounts directly when `selectedAlert` becomes null. If the panel ever wraps `<AlertDetailView>` in `<AnimatePresence>`, the exit animation would play. This is the same cosmetic-only observation flagged in 5d's review; not a blocking concern.

## RULE-038 Verification Results

I directly grep-checked the key claims:

1. **`/audit` endpoint exists at `routes/alerts.py:281`** — VERIFIED. `grep -n "audit\|alert_acknowledgment_audit\|AuditEntryResponse" argus/api/routes/alerts.py` shows the route at line 281, the Pydantic model at line 101, and the SQL query with `id AS audit_id` at line 303.

2. **`AlertBanner` + `AlertToastStack` mount in `AppShell.tsx`** — VERIFIED. `grep -n "AlertBanner\|AlertToastStack" argus/ui/src/layouts/AppShell.tsx` returns 4 matches: imports at lines 21–22, mounts at lines 129 (banner inside z-40 wrapper) and 131 (toast).

3. **`AlertBanner` + `AlertToastStack` NOT in `DashboardPage.tsx`** — VERIFIED. Grep returns zero matches. The diff `git diff --stat 1c08bf0..7efd0a0` confirms `argus/ui/src/pages/DashboardPage.tsx | 23 -` (23 lines removed, no insertions).

4. **`AppShell.alerts.test.tsx::AlertBanner persists across page navigation` exists** — VERIFIED. `grep -n "persists across page navigation" argus/ui/src/layouts/AppShell.alerts.test.tsx` matches at line 163.

5. **DEF-226/227 in 5d work journal register** — VERIFIED. `grep -rn "DEF-226\|DEF-227" docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` returns matches at lines 146–147.

6. **DEF-228/229/230 absent from CLAUDE.md** — VERIFIED. `grep "DEF-22[8-9]\|DEF-230" CLAUDE.md` returns zero matches.

## Test Verification

```
$ cd argus/ui && npx vitest run 2>&1 | tail -3
 Test Files  121 passed (121)
      Tests  913 passed (913)
   Duration  14.61s
```

```
$ python -m pytest tests/api/test_alerts.py -q
............... 15 passed in 3.30s
```

```
$ cd argus/ui && npx tsc --noEmit
(no output — clean)
```

Vitest 902 → 913 (+11) matches closeout. Pytest 12 → 15 (+3) on test_alerts.py matches closeout. TypeScript clean. ✓

## Sprint Spec Conformance (D13)

D13 acceptance criteria all met:
- AlertsPanel.tsx with active + historical tables ✓
- Filters (severity / source / symbol) ✓
- Sortable headers (4 sort keys) ✓
- Date-range picker with sensible default ✓
- Detail modal with metadata + audit trail ✓
- AlertBanner + AlertToastStack mounted at AppShell layer ✓
- 5 DashboardPage temporary mounts removed ✓
- Cross-page persistence test (regression invariant 17) ✓
- 8 component Vitest specs + 3 integration specs ✓
- CI green; Vitest baseline ≥ Session 5d + 10 ✓
- Doc-sync (D14) FILED as follow-up (5 items: DEC-388, DEF-014 closure, architecture.md §14, dec-index update, sprint summary) ✓

## Recommendation

**CLEAR.** Implementation is complete, RULE-038 + RULE-007 compliance exemplary, scope expansion explicitly justified and proportionate, no regressions, all spec criteria met. Three filed DEFs (228 backend `until`, 229 panel virtualization, 230 audit-error toast) are appropriate deferrals with clear triggers.

The bundled `/audit` endpoint addition is the right call given the spec's halt-and-fix directive, the additive nature of the change, and the proportionality of work (a separate Impromptu D would have been overhead for ~57 LOC of router code + 90 LOC of tests). This is exactly the case the halt-and-fix exception in RULE-007 was designed for.

Sprint 31.91 implementation track is now COMPLETE. Sessions 0 / 1a / 1b / 1c / 2a / 2b.1 / 2b.2 / 2c.1 / 2c.2 / 2d / 3 / 4 / 5a.1 / 5a.2 / 5b / 5c / 5d / 5e + Impromptus A / B / C all delivered. Next steps: sprint-level close-out via Work Journal handoff + doc-sync (D14 — DEC-388, DEF-014 closure, architecture.md §14).

Minor informational note (carry-over from 5d): `AlertDetailView` modal exit animation (if any was intended via Framer Motion) won't play because `AlertsPanel` unmounts the modal directly. Same cosmetic-only observation as 5d's modal exit. Non-blocking.

---END-REVIEW---

```json:structured-verdict
{
  "session": "sprint-31.91 / session-5e",
  "commit": "7efd0a0b6d09730f81f97e5216a5c3ca248ccf96",
  "verdict": "CLEAR",
  "blocking_findings": [],
  "informational_findings": [
    {
      "id": "INFO-1",
      "topic": "AlertDetailView modal exit animation likely does not play",
      "detail": "AlertsPanel uses {selectedAlert && <AlertDetailView/>} pattern; parent unmounts directly without AnimatePresence wrapper. Cosmetic-only; carry-over from same pattern in 5d's AlertAcknowledgmentModal.",
      "severity": "informational",
      "blocking": false
    },
    {
      "id": "INFO-2",
      "topic": "AlertDetailView and AlertToastStack share z-50",
      "detail": "Both at z-50 with last-render-wins via DOM order. Detail modal mounts in Observatory route subtree (renders after AppShell-level toasts), so coexistence is correct. Same coexistence pattern as 5d's acknowledgment-modal vs toasts.",
      "severity": "informational",
      "blocking": false
    }
  ],
  "rule_038_drifts_verified": 6,
  "rule_038_drifts_material": 0,
  "rule_007_scope_expansion": {
    "occurred": true,
    "site": "argus/api/routes/alerts.py — GET /{alert_id}/audit + AuditEntryResponse model + 3 tests",
    "explicitly_acknowledged_in_closeout": true,
    "spec_authorized_via_halt_and_fix": true,
    "reviewer_evaluation": "ACCEPTED — purely additive, proportionate to scope, alternative (separate Impromptu D) would have been overhead for ~150 LOC"
  },
  "tests_added_vitest": 11,
  "tests_added_pytest": 3,
  "vitest_baseline_before": 902,
  "vitest_baseline_after": 913,
  "vitest_target": 912,
  "vitest_target_met": true,
  "pytest_test_alerts_before": 12,
  "pytest_test_alerts_after": 15,
  "typescript_clean": true,
  "ci_status": "tests verified locally; CI run for 7efd0a0 to be confirmed by operator on next sprint-runner pre-flight",
  "new_def_collisions": 0,
  "new_defs_filed": ["DEF-228", "DEF-229", "DEF-230"],
  "scope_creep": false,
  "regressions_detected": false,
  "spec_conformance": "complete",
  "cross_page_invariant_17_verified": true,
  "audit_endpoint_existed_pre_5e": false,
  "audit_endpoint_added_in_5e": true,
  "sprint_implementation_complete": true,
  "recommendation": "Proceed to sprint-level close-out via Work Journal handoff + doc-sync (D14 — DEC-388, DEF-014 closure, architecture.md §14)."
}
```
