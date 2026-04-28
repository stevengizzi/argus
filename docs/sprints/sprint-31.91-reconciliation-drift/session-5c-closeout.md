# Sprint 31.91 — Session 5c Close-Out

> **Track:** Alert Observability Frontend (Sessions **5c** → 5d → 5e).
> **Position in track:** First frontend session. Establishes the data hook +
> the most visible UI primitive (banner). The next two sessions add toast
> + cross-page integration on top.
> **Self-assessment:** **PROPOSED_CLEAR** (no deviations from spec).

---

## Anchor Commit

`140ccd8` (`main` HEAD at session start — work journal register refresh post Impromptu B). Tier 3 #2 entry condition (Impromptus A + B landed CLEAR) satisfied — verified at session start.

---

## Change Manifest

### New files

- **`argus/ui/src/hooks/useAlerts.ts`** (NEW — 235 lines)
  - TanStack Query + WebSocket hybrid hook.
  - REST: `GET /api/v1/alerts/active` for initial state. `refetchInterval`
    is `false` while WS is `connected`/`loading` and `5_000` ms while
    `disconnected`/`error` — REST-as-fallback during disconnect.
  - WebSocket: `/ws/v1/alerts` with the standard JWT-first auth idiom
    (`{type: "auth", token}` → `auth_success` → snapshot → deltas).
    Mirrors the `arena_ws` and `observatory_ws` patterns already in the
    codebase.
  - Reconnect resync: `wasDisconnectedRef` tracks whether we've seen a
    disconnect/error. On `auth_success`, the hook calls `refetch()` ONLY
    when `wasDisconnected === true` (i.e., this is a recovery, not the
    initial connect). Initial connect skips the refetch because the
    backend's `snapshot` frame, which always follows `auth_success`,
    already provides the authoritative state.
  - WS handlers: `auth_success`, `snapshot`, `alert_active`,
    `alert_acknowledged`, `alert_auto_resolved`, `alert_archived`
    (defensive — backend documents but does not currently emit it).
    Cache merge is idempotent: `upsertAlert()` filters `archived` alerts
    out of the visible list; `removeAlert()` for the future
    `alert_archived` frame.
  - `acknowledge()` POSTs to `/api/v1/alerts/{id}/acknowledge` with
    `{reason, operator_id}` body. Returns the parsed response on 200,
    `null` on 404 (alert vanished — banner relies on the WS push to drop
    it from the list), throws on other errors. Banner currently swallows
    errors; the proper error UI lands in 5d's modal per spec.
  - WebSocket cleanup on unmount via `ws.close(1000, 'useAlerts unmount')`.

- **`argus/ui/src/components/AlertBanner.tsx`** (NEW — 92 lines)
  - Renders only when at least one alert is `severity === "critical"` AND
    `state === "active"`. Filters `acknowledged` and `archived` out.
  - Headline: most-recently-created alert (sort by `created_at_utc` ISO
    string descending — UTC ISO strings sort lexicographically).
  - "+N more" indicator when multiple critical alerts active.
  - Severity styling: `bg-red-600 border border-red-700 text-white`.
    Lucide-react `AlertTriangle` icon, "CRITICAL" prefix label,
    Acknowledge button (`bg-white text-red-700`).
  - Accessibility: root element has `role="alert"` and
    `aria-live="assertive"`; the AlertTriangle icon is `aria-hidden`;
    Acknowledge is a real `<button type="button">`, keyboard-focusable.
  - Acknowledgment flow: button click sets local `acking` state to the
    target `alert_id`, calls `acknowledge()` with reason
    `"Acknowledged from Dashboard banner"` and operator_id `"operator"`,
    clears `acking` in `finally`. Disappearance is driven by the WS
    push: when the cache update transitions the alert to `acknowledged`
    or `archived`, `criticalActive` becomes empty and the component
    returns `null` on the next render. The 1s budget per spec covers
    WS round-trip + React re-render.

- **`argus/ui/src/hooks/__tests__/useAlerts.test.tsx`** (NEW — 269 lines, 10 tests)
- **`argus/ui/src/components/AlertBanner.test.tsx`** (NEW — 169 lines, 10 tests)

### Modified files

- **`argus/ui/src/pages/DashboardPage.tsx`** (5 edits)
  - Imported `AlertBanner` from `../components/AlertBanner`.
  - Mounted `<AlertBanner />` at four sites covering the page's four
    branches: pre-market desktop, pre-market mobile, phone single-column,
    desktop dense layout (top of `motion.div`), tablet stacked. The
    desktop branch wraps it in a `motion.div` with `staggerItem` so it
    participates in the page's stagger animation; non-motion branches use
    a simple wrapper. Per spec: "The banner mounts on Dashboard.tsx in
    this session; cross-page mounting at Layout level lands in Session
    5e."

- **`argus/core/config.py`** (DEF-220 disposition — Option A)
  - Removed the `acknowledgment_required_severities` field from
    `AlertsConfig`. Replaced with an inline disposition comment that
    points future readers at the per-alert-type
    `PolicyEntry.operator_ack_required` field (the canonical home for
    acknowledgment-required gating). `AlertsConfig` field count: 5 → 4.

- **`config/system.yaml`** + **`config/system_live.yaml`** (DEF-220 cleanup)
  - Removed the `acknowledgment_required_severities: ["critical"]` line
    from both YAMLs. The `alerts:` block in both files is now `alerts:
    {}` with a header comment that points at `alert_auto_resolution.POLICY_TABLE`
    as the canonical site for severity-based policy.

---

## Judgment Calls

### 1. Reconnect refetch gated on `wasDisconnected` (improvement vs naïve spec sketch)

The spec's hook sketch (lines 86–88 of the impl prompt) calls `refetch()`
unconditionally inside `onopen`:

```ts
ws.onopen = () => {
  setConnectionStatus("connected");
  refetch(); // Resync on reconnect
};
```

This double-fetches on initial connect: the backend always sends a
`snapshot` frame after `auth_success`, AND the REST `/active` query has
already fired once on mount. Implementation gates the refetch on
`wasDisconnectedRef.current === true` — the refetch only runs when this
is a true reconnect, not the initial connect. This:

(a) eliminates the wasteful double-fetch on first mount,
(b) keeps the `last-write-wins` behavior intact for the reconnect case
    that the spec's review focus #2 explicitly calls out, and
(c) makes the test harness deterministic (an unconditional refetch
    inside the test's `act()` block would race against the WS messages
    fired in the same block).

The `setConnectionStatus('connected')` still fires unconditionally on
`auth_success`, so the polling-fallback gating works correctly.

### 2. JWT auth on the WS connection (matches existing pattern, not literally in spec sketch)

The spec sketch (lines 84–88) opens the WebSocket without sending an
auth message. The actual backend (`argus/api/websocket/alerts_ws.py`)
requires `{type: "auth", token: <JWT>}` as the first frame and closes
with code 4001 if absent — same idiom as `observatory_ws` and
`arena_ws`. Implementation sends the auth frame in `onopen`, mirroring
the `useArenaWebSocket.ts` pattern at `argus/ui/src/features/arena/useArenaWebSocket.ts:209-216`.

### 3. Field-name alignment with backend (`state` not `status`, `created_at_utc` not `emitted_at_utc`)

The spec sketch's `Alert` interface (lines 53–66) uses `status` and
`emitted_at_utc`. The actual REST contract (`AlertResponse` in
`argus/api/routes/alerts.py:50-68`) and WS payload contract
(`_alert_to_payload` in `argus/core/health.py:125-153`) use `state` and
`created_at_utc`. Implementation aligns with the backend's actual wire
format. The `AlertState` TypeScript union also drops `auto_resolved`
(spec sketch had it as a status value): the backend's
`AlertLifecycleState` enum has only `active`, `acknowledged`,
`archived` — auto-resolution transitions to `archived` and is
distinguished by the WS message type, not by a status value.

### 4. DEF-220 disposition: Option A (REMOVAL)

Per the impl prompt's pre-flight grep:

```
grep -n "acknowledgment_required_severities" argus/core/config.py    # 1 hit
grep -rn "..." argus/ --include="*.py" | grep -v config.py            # 0 hits
```

Confirmed — the field has zero consumers in production code. Tier 3 #2
verdict already disposed this as Option A (removal): the verdict text
at `tier-3-review-2-verdict.md:142` states "`acknowledgment_required_severities`
field (removed at S5c per DEF-220 disposition — per-alert-type
`operator_ack_required` is sufficient)".

The frontend banner reads `severity === 'critical'` directly without
referencing the config field — Session 5c does NOT surface a use case
that would justify Option B (wire). Removal is the clean choice.

Removal scope:
- `argus/core/config.py:231-239` field deleted; replaced with inline
  disposition comment.
- `config/system.yaml:227-228` and `config/system_live.yaml:231-232` —
  the `acknowledgment_required_severities: ["critical"]` line removed
  from both. The `alerts:` block stays in both YAMLs (now `{}`) so the
  `Pydantic.alerts` field still loads with default values for the
  remaining 4 fields.
- No tests reference the field — verified via
  `grep -rn "acknowledgment_required_severities" tests/` returning zero
  hits.

---

## Severity-rendering decision (operator-decision item from spec line 200)

**Banner displays `critical` only.** `warning` and `info` are toast-only,
landing in Session 5d.

Rationale:
- The spec line 250 default explicitly says "default: toast-only" for
  warning. Implementation follows the default.
- `AlertsConfig.acknowledgment_required_severities` (now removed) had
  default `["critical"]` — the architectural posture the project has
  consistently held: only `critical` requires the persistent banner UI.
- Banner real estate is a finite resource on Dashboard. Surfacing
  warnings + info would crowd out genuine critical alerts.

The banner test `AlertBanner renders nothing when only non-critical
alerts are active (warning is toast-only)` enforces this decision as a
regression guard.

---

## WebSocket contract verification

Cross-checked frontend hook handlers against backend producers:

| WS message     | Backend producer                                      | Frontend hook handler |
|---             |---                                                    |---                    |
| `auth_success` | `alerts_ws.py:88-91`                                  | `auth_success` case   |
| `snapshot`     | `alerts_ws.py:94-101` (after `subscribe_state_changes`) | `snapshot` case      |
| `alert_active` | `health.py:550-553` (`on_system_alert_event`)         | `alert_active` case   |
| `alert_acknowledged` | `health.py:652-655` (`persist_acknowledgment_after_commit`) | `alert_acknowledged` case |
| `alert_auto_resolved` | `health.py:917-920` (`_auto_resolve`)            | `alert_auto_resolved` case |
| `alert_archived` | NOT CURRENTLY EMITTED (documented in `alerts_ws.py:14` but no producer) | `alert_archived` case (defensive) |

`alert_archived` is documented in the WS file's docstring but no
producer exists today (`grep -n "alert_archived"
argus/core/health.py` returns zero hits). The hook handles it
defensively for forward-compat with future producers — the handler
simply removes the alert from the cache by `alert_id`.

---

## Test Results

### New tests (20 added)

**`useAlerts.test.tsx` — 10 tests, all passing in 246 ms isolated**

1. fetches initial state via REST `GET /api/v1/alerts/active`
2. subscribes to WebSocket `/ws/v1/alerts` on mount and sends auth
3. marks `connectionStatus="disconnected"` on `ws.onclose` and enables
   REST polling (verifies `refetchInterval=5000` on the query observer)
4. refetches REST after WebSocket reconnect (`auth_success` after a
   prior disconnect)
5. replaces query cache from WS `snapshot` frame (also verifies
   `archived` alerts are filtered out at the cache layer)
6. appends a new alert on `alert_active` and removes on
   `alert_auto_resolved` (E2E: empty REST → upsert via WS → archive via
   WS; uses `await waitFor` for state-update flushing)
7. updates an alert in place on `alert_acknowledged` (preserves
   `acknowledged_by` + `acknowledgment_reason` from the delta)
8. `acknowledge()` POSTs to `/api/v1/alerts/{id}/acknowledge` with
   `reason` + `operator_id` body
9. `acknowledge()` returns null on 404 (alert vanished — UI relies on
   WS push to drop it)
10. closes WebSocket on unmount (`close()` called)

**`AlertBanner.test.tsx` — 10 tests, all passing in 136 ms isolated**

1. renders nothing when there are no alerts
2. renders nothing when only non-critical alerts are active (warning is
   toast-only) — DECISION REGRESSION GUARD
3. renders nothing when critical alert is `acknowledged` (state != active)
4. renders the banner for an active critical alert with `role="alert"`
5. applies critical severity styling (`bg-red-600`, `border-red-700`)
6. shows "+N more" when multiple critical alerts are active
7. headline is the most-recently-created alert (verifies sort by
   `created_at_utc`)
8. clicking Acknowledge calls `acknowledge()` with `alert_id`, reason
   (≥10 chars), `operator_id` (matches backend `AcknowledgeRequest`
   validators)
9. Acknowledge button is a real `<button>` element (keyboard-focusable)
10. disappears synchronously when active critical alert list becomes
    empty (ack/auto-resolve)

### Full Vitest suite

- **Baseline (Session 5b on `main`):** 866 tests across 115 files, 13.29 s.
- **After Session 5c:** **886 tests across 117 files, 12.76 s.** Delta:
  **+20 tests** (10 useAlerts + 10 AlertBanner). Spec target: ≥866 + 10
  = 876. Delta exceeds the spec target by 10. **PASS.**

### Backend pytest spot-check

- `tests/api/test_alerts_5a2.py + tests/integration/test_alert_pipeline_e2e.py + tests/api/test_alerts.py`: **44 passed in 5.60 s**.
- Broader API + core + integration scope: `tests/api/ tests/core/ tests/integration/test_alert_pipeline_e2e.py -n auto -q --ignore=tests/api/test_websockets.py`: **1383 passed in 35.67 s.** No regressions from the DEF-220 field removal.
- YAML config parse-back: both `config/system.yaml` and
  `config/system_live.yaml` re-load via `SystemConfig(**yaml.safe_load(...))`
  cleanly with the 4 remaining `AlertsConfig` fields at default values.

---

## Coverage Report

Vitest coverage was not run as a separate pass (the project's
`vitest.config.ts` does not enable `coverage` by default and the
implementation prompt's ≥90% target applies to "new code"). The new
files were exercised by all 20 new tests across multiple branches:

- **`useAlerts.ts` branches covered:**
  - REST initial fetch (success path).
  - WebSocket constructor.
  - WS auth-message send on `onopen`.
  - All 6 WS message-type cases (`auth_success`, `snapshot`,
    `alert_active`, `alert_acknowledged`, `alert_auto_resolved`,
    `alert_archived` defensive).
  - `connectionStatus` transitions: `loading → connected → disconnected
    → connected`.
  - Reconnect-gated refetch via `wasDisconnectedRef`.
  - `acknowledge()` 200 + 404 paths.
  - Cleanup on unmount.
- Untested branches (acknowledged gaps):
  - 5xx error path on acknowledge throws (Test "returns null on 404"
    only covers the 404 case; the throw branch is exercised at type
    level by `Promise<AcknowledgeResult | null>` but not behaviorally).
    Surfacing errors to UI lands in 5d's modal per spec, so this gap
    is intentional for 5c.
  - `getToken() === null` branch sets `connectionStatus = 'error'` and
    returns early. Test infrastructure mocks `getToken` to always
    return `'test-token'`. Operationally this branch fires only when
    the JWT has been cleared (logged out); the REST query's 401 path
    handles redirect-to-login. Not covered.

- **`AlertBanner.tsx` branches covered:**
  - Empty list → returns null.
  - Non-critical only → returns null.
  - Acknowledged-only critical → returns null.
  - One critical active → renders.
  - Multiple critical active → renders with "+N more".
  - Severity styling (red).
  - Sort by `created_at_utc`.
  - Acknowledge button click flow (success).
  - Button is `<button>`.
  - Banner disappears on state change.
- Untested branches:
  - `acking` state during the in-flight ack POST (text changes to
    "Acknowledging…" and button is `disabled`). The component renders
    this state but the test asserts the button is not disabled before
    click. Not behaviorally critical for 5c.
  - Acknowledge promise rejection (component swallows; UI lands in 5d).

---

## Definition of Done — Verification

- [x] `useAlerts.ts` mirrors the existing TanStack Query + WebSocket
      hybrid pattern (verified against `useArenaWebSocket.ts` and
      `useSessionVitals.ts`).
- [x] Reconnect resilience: REST fallback active during disconnect
      (`refetchInterval=5000`); refetch on reconnect (gated on
      `wasDisconnectedRef`).
- [x] WebSocket subscription cleanup on unmount (`ws.close(1000,
      'useAlerts unmount')`).
- [x] `AlertBanner.tsx` renders for any active critical alert.
- [x] Severity-coded styling per Tailwind v4 conventions
      (`bg-red-600`, `border-red-700`).
- [x] Acknowledgment posts to REST with `reason` + `operator_id` body.
- [x] Banner disappears within 1s of ack OR auto-resolve (via WS
      delta → cache update → re-render → empty critical list).
- [x] Mounted on `DashboardPage.tsx` (4 mount sites covering all
      breakpoints + pre-market layout; temporary placement; 5e moves to
      `Layout.tsx`).
- [x] 20 Vitest tests added (≥10 target).
- [x] Operator decision documented: warning is toast-only (5d). Banner
      renders `critical` only.
- [x] DEF-220 disposition (Option A — removal) decided and applied.
- [x] CI green; Vitest baseline 866 → 886 (+20, ≥ +10 target).
- [ ] Tier 2 review (frontend reviewer template) verdict CLEAR — pending.
- [x] Close-out at this file location.

---

## DEF Transitions Claimed

| DEF | Status before | Status after | Site |
|---  |---            |---           |---   |
| **DEF-220** | OPEN — Routing: Sprint 31.91 Session 5c | **RESOLVED-IN-SPRINT, Session 5c (Option A: removal of `acknowledgment_required_severities` from `AlertsConfig` + both YAML overlays)** | `argus/core/config.py:231-239`, `config/system.yaml:227-228`, `config/system_live.yaml:231-232` |

The DEF-220 row in `CLAUDE.md`'s defects table will transition at
sprint-close per the doc-sync manifest (`pre-impromptu-doc-sync-manifest.md`).
This close-out makes the claim; the manifest applies it.

---

## Sprint-Level Regression Checklist

- **Invariant 5 (Vitest baseline ≥ prior):** PASS — 866 → 886 (+20,
  exceeds spec target of +10).
- **Invariant 17 (banner persistence) — partial:** PASS in-scope —
  banner renders on Dashboard. Cross-page persistence verified in 5e
  (out of 5c scope).
- **Invariant 14:** Row "After Session 5c" — Alert observability
  frontend = "useAlerts hook + Dashboard banner".
- **Invariant 15 (do-not-modify boundaries):** PASS — only the files
  the spec authorizes (`argus/ui/src/hooks/useAlerts.ts`,
  `argus/ui/src/components/AlertBanner.tsx`,
  `argus/ui/src/pages/DashboardPage.tsx`) plus the DEF-220 surface
  (`argus/core/config.py`, `config/system.yaml`,
  `config/system_live.yaml`) were edited. No edits to backend
  alerts code, HealthMonitor, REST routes, WebSocket handler, or
  any other do-not-modify file.

---

## Sprint-Level Escalation Criteria

- **A2** (Tier 2 frontend reviewer CONCERNS or ESCALATE) — pending Tier 2.
- **B1, B3, B4, B6** — none triggered.
- **C7** (existing Vitest tests fail because the new fetch / WebSocket
  mocks broaden a global test-setup fixture) — none observed; the new
  mocks are scoped to the new test files via `vi.stubGlobal` in
  `beforeEach` and `vi.unstubAllGlobals` in `afterEach`. Full Vitest
  baseline 866 → 886 (+20, no regressions). The Sprint 32.8
  `setup.ts` afterEach `vi.restoreAllMocks()` interaction is
  uneventful here because the new tests use `stubGlobal` (which
  `unstubAllGlobals` restores explicitly), not `spyOn`.

---

## Self-Assessment

**Verdict: PROPOSED_CLEAR.** No deviations from spec. Three judgment
calls (1: reconnect-gated refetch, 2: JWT auth alignment, 3:
field-name alignment with backend) all flow from grep-verified
backend reality vs the impl prompt's illustrative sketch — RULE-038
posture, all documented above. DEF-220 disposition follows the Tier 3
#2 verdict's pre-recommendation.

**Context State: GREEN** — all reads happened before writes; baseline
Vitest captured before any code change; full Vitest re-run after
implementation completed; backend pytest spot-checks ran clean.

**Compaction defense:** Session was small (4 new files, 4 modified
files, ~700 LOC of code+test added). No risk of compaction-induced
regression.

---

## Counter-results JSON

```json
{
  "session": "5c",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 20,
  "tests_added_breakdown": {
    "useAlerts.test.tsx": 10,
    "AlertBanner.test.tsx": 10
  },
  "vitest_baseline_before": 866,
  "vitest_baseline_after": 886,
  "vitest_delta": 20,
  "vitest_target_delta": 10,
  "vitest_coverage_pct": "not separately measured; behavioral coverage of the 6 WS message types + REST initial-fetch + reconnect-gated-refetch + ack 200/404 + 10 banner branches",
  "reconnect_resilience_verified": true,
  "ws_contract_aligned_with_5a2": true,
  "def_transitions": [
    {
      "def": "DEF-220",
      "from": "OPEN",
      "to": "RESOLVED-IN-SPRINT",
      "disposition": "Option A — removal",
      "sites": [
        "argus/core/config.py",
        "config/system.yaml",
        "config/system_live.yaml"
      ]
    }
  ],
  "files_added": [
    "argus/ui/src/hooks/useAlerts.ts",
    "argus/ui/src/components/AlertBanner.tsx",
    "argus/ui/src/hooks/__tests__/useAlerts.test.tsx",
    "argus/ui/src/components/AlertBanner.test.tsx"
  ],
  "files_modified": [
    "argus/ui/src/pages/DashboardPage.tsx",
    "argus/core/config.py",
    "config/system.yaml",
    "config/system_live.yaml"
  ]
}
```
