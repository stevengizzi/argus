# Sprint 31.91 — DEF Disposition Matrix (Sprint-Close Reference)

> **Purpose:** Confidence-graded routing for every open carry-forward item from Sprint 31.91, intended to be consumed by the D14 doc-sync. This is the answer to "everything gets documented really well so it can be picked up later."
>
> **Routing confidence levels:**
> - **CONFIDENT** — clear technical or sequencing rationale ties this to a specific named sprint
> - **PROBABLE** — strong reason to expect this lands in a particular sprint, but not strictly required
> - **OPPORTUNISTIC** — genuinely event-triggered or hygiene work; route opportunistically
> - **BLOCKED** — depends on infrastructure that doesn't exist yet
>
> **Source documents:** This matrix synthesizes carry-forwards from the work-journal-register, all per-session closeouts, all Tier 2 reviews, and the `userMemories` cleanup tracker.

**Generated:** 2026-04-28, post-Session-5e + post-catalog-hotfix, pre-D14
**Anchor commit:** `4c737d5` on `main`

---

## Section A — DEFs Filed In-Sprint That Remain OPEN

### DEF-222 — Predicate-handler subscribe-before-rehydrate audit
**Source:** Tier 3 #2 Item 2 (S5a.2 reviewer F1)
**Routing confidence:** **CONFIDENT** — bounded by a specific producer-landing event
**Routing target:** **Whichever sprint introduces the FIRST production producer for `ReconciliationCompletedEvent`, `IBKRReconnectedEvent`, OR `DatabentoHeartbeatEvent`.**

**Why this is confident:** The race condition is theoretical until producers exist. The moment ANY of the three producer-wiring sprints lands, this audit MUST fire as a pre-merge gate per the amended Tier 3 #2 verdict. The expected first trigger is the **`post-31.9-reconnect-recovery` sprint** (DEF-194/195/196) which would wire `IBKRReconnectedEvent`. Second-most-likely is the **`post-31.9-component-ownership` sprint** for `ReconciliationCompletedEvent`. Either way, it must land before producer wiring is sealed.

**Specific work required when triggered:**
1. Audit `_subscribe_predicate_handlers()` ordering in `argus/core/health.py` against rehydrate timing in `argus/main.py:425`
2. Defer `_subscribe_predicate_handlers()` to AFTER `rehydrate_alerts_from_db()` if a real race window emerges
3. Update `protocols/market-session-debrief.md` Phase 3 if needed

---

### DEF-226 — Full focus-trap on AlertAcknowledgmentModal
**Source:** S5d closeout J4
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First UI accessibility audit OR if WCAG conformance becomes a deployment requirement**

**Why opportunistic:** Currently mirrors `ConfirmModal.tsx` pattern (initial-focus + Escape only). Doing this cleanly requires either (a) treating both modals together (accessibility refactor, ~1 hour) or (b) deepening the inconsistency the reviewer flagged. Neither has a sharp trigger.

**Specific work required when triggered:**
1. Decide library (`focus-trap-react` is industry standard) vs. hand-rolled
2. Apply to BOTH `AlertAcknowledgmentModal` and `ConfirmModal` for consistency
3. Add Vitest specs that Tab cycles within modal, doesn't escape to background
4. Consider whether `AlertDetailView` (read-only, no inputs) needs the same treatment

---

### DEF-227 — Authenticated operator-id wiring into Toast/Modal
**Source:** S5d closeout J3
**Routing confidence:** **BLOCKED**
**Routing target:** **First sprint that introduces auth context / multi-operator login infrastructure**

**Why blocked:** Auth context doesn't exist yet. Currently `operator_id = "operator"` is hardcoded across `AlertBanner`, `AlertToastStack`, `AlertAcknowledgmentModal`. This change is mechanical when auth context exists; pointless before.

**Specific work required when triggered:**
1. Replace 3 hardcoded `"operator"` references with `useAuth()` or equivalent context hook
2. Update Vitest specs to mock the auth context
3. Closes the same-operator-two-tabs duplicate-ack edge case (S5d closeout J3) automatically

---

### DEF-228 — Backend `/api/v1/alerts/history` `until` query parameter
**Source:** S5e closeout J3
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First future backend-alerts session OR if bandwidth on wide-window queries becomes a complaint**

**Why opportunistic:** Currently client-side filters upper bound (`useAlertHistory` calls `/history?since=<from>` and applies `created_at_utc <= range.to`). Functionally correct, just slightly wasteful. Single-operator system means bandwidth waste is irrelevant.

**Specific work required when triggered:**
1. Add `until: str | None = None` parameter to `get_alert_history` in `argus/api/routes/alerts.py:253`
2. Mirror `since` parsing pattern (RFC3339 / ISO-8601 timestamp validation)
3. Update `HealthMonitor.get_alert_history()` signature
4. Frontend `useAlertHistory` switches from client-side filter to passing `until=<range.to>` — call site doesn't change shape
5. Add 1 backend pytest + update existing 3 Vitest specs

**Estimated effort:** ~30 min

---

### DEF-229 — Observatory pagination virtualization for AlertsPanel
**Source:** S5e closeout
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First time observed slowness or operator complaint**

**Why opportunistic:** No data exists yet — Sprint 31.91 paper trading hasn't generated production alerts of significant volume. Adding `@tanstack/react-virtual` against zero rows is premature optimization without a benchmark.

**Specific work required when triggered:**
1. Profile `AlertsPanel`'s `AlertsTable` body render with realistic dataset (e.g., 6 months × N alerts)
2. Add `@tanstack/react-virtual` to `argus/ui/package.json`
3. Refactor `AlertsTable` body to use `useVirtualizer` hook
4. Update Vitest specs for virtual scrolling behavior

---

### DEF-230 — Audit-loading state and error-toast for `useAlertAuditTrail`
**Source:** S5e closeout
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First time a transient `/audit` GET failure surfaces operationally OR a UI polish session**

**Why opportunistic:** Audit endpoint is read-only and idempotent; transient failures recover via React-Query's automatic retry. Currently network failure renders as "no acknowledgment audit entries" — semantically wrong but operationally invisible because the endpoint is reliable.

**Specific work required when triggered:**
1. Thread `error` through `useAlertAuditTrail` hook return shape
2. Update `AlertDetailView` audit-trail rendering branch to distinguish empty (no rows) from error (failure)
3. Add Vitest spec for error-state rendering
4. Update existing 8 `AlertsPanel.test.tsx` specs that assume audit-empty placeholder is the only error surface

---

## Section B — Pre-Existing DEFs Touched This Sprint (NO Status Change)

### DEF-208 — Live-trading test fixture missing
**Source:** Sprint 31.91 S4 spec Phase D Item 1 grep
**Status:** OPEN; future session
**Routing confidence:** **CONFIDENT**
**Routing target:** **Sprint that begins live trading transition OR `post-31.9-live-enable` work**

**Why confident:** A "live-trading test fixture" only matters when tests need to assert behavior under live broker conditions. That moment is structurally tied to live-enable Gate 3 work (Phase 3a/b/c per S4's decomposed live-enable gate).

**Specific work required when triggered:** Per S4's filing — fixture for live-trading test isolation; details in S4 spec Phase D Item 1.

---

### DEF-209 (extended) — `Position.side` AND `ManagedPosition.redundant_exit_observed` persistence
**Source:** Tier 3 #1 + S4 verification
**Status:** Sprint 35+ horizon
**Routing confidence:** **CONFIDENT**
**Routing target:** **Sprint 35 or later** per Tier 3 #1 amendment

**Why confident:** Already explicitly routed to Sprint 35+ at Tier 3 #1 disposition.

---

### DEF-211 (extended) — D1+D2+D3 scope
**Source:** Pre-existing + Apr 27 Findings 3+4
**Status:** Sprint 31.93
**Routing confidence:** **CONFIDENT (sprint-gating)**
**Routing target:** **Sprint 31.93** (first post-31.91 sprint)

**Why confident:** Explicitly sprint-gating per Tier 3 #2 disposition. Includes RSK-DEC-386-DOCSTRING bound (D1), `max_concurrent_positions` broker-only-longs counting (D3), and IMPROMPTU-04 boot-time reconciliation policy (D2).

**Specific work required:**
- D1: Convert `reconstruct_from_broker()` STARTUP-ONLY contract from docstring to runtime gate (closes RSK-DEC-386-DOCSTRING)
- D2: Boot-time reconciliation policy + IMPROMPTU-04 gate refinement
- D3: `max_concurrent_positions` accounting fix (counts broker-only longs incorrectly)

---

### DEF-212 — `_OCA_TYPE_BRACKET = 1` constant drift risk
**Source:** Tier 3 #1 Concern B
**Status:** Sprint 31.92
**Routing confidence:** **CONFIDENT**
**Routing target:** **Sprint 31.92**

**Why confident:** Already routed at Tier 3 #1 disposition.

---

### DEF-215 — Reconciliation per-cycle log spam
**Source:** Apr 27 debrief Finding 2
**Status:** DEFERRED with sharp revisit trigger
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First time log volume becomes a debugging-friction complaint OR adjacent work in `argus/execution/order_manager.py` reconciliation paths**

**Why opportunistic:** The "sharp revisit trigger" was filed as: revisit if reconciliation log volume materially impedes debugging during a paper-session debrief. Until that happens, leave alone.

---

### DEF-014 (PRIMARY DEFECT) — Alert observability gap
**Status:** ✅ **FULLY RESOLVED via Session 5e** (anchor commit `7efd0a0`)
**Routing target:** N/A — close at D14

---

### DEF-158 — Flatten retry side-blindness
**Status:** ✅ **RESOLVED via S3** (commit `a11c001`)
**Routing target:** N/A — close at D14

---

### DEF-213 — `SystemAlertEvent.metadata` schema gap
**Status:** ✅ **FULLY RESOLVED** (schema half S2b.1 + atomic-migration half S5a.1)
**Routing target:** N/A — close at D14

---

### DEF-214 — EOD verification timing race + side-blind classification
**Status:** ✅ **RESOLVED via S5a.1**
**Routing target:** N/A — close at D14

---

### DEF-216 — `test_get_regime_summary` ET-midnight rollover race
**Status:** ✅ **RESOLVED via impromptu hotfix** `c36a30c`
**Routing target:** N/A — close at D14

---

### DEF-217 / DEF-218 / DEF-219 / DEF-224 / DEF-225
**Status:** ✅ **RESOLVED-IN-SPRINT via Impromptu A** (anchor `e78a994`)
**Routing target:** N/A — close at D14

---

### DEF-220 — `acknowledgment_required_severities` consumer wiring
**Status:** ✅ **RESOLVED-IN-SPRINT via Session 5c (Option A: REMOVAL)** (anchor `3197472`)
**Routing target:** N/A — close at D14

---

### DEF-221 — `DatabentoHeartbeatEvent` producer wiring
**Status:** ✅ **RESOLVED-IN-SPRINT via Impromptu B** (anchor `8efa72e`)
**Routing target:** N/A — close at D14

---

### DEF-223 — Migration framework adoption sweep
**Status:** ✅ **RESOLVED-IN-SPRINT via Impromptu C** (anchor `3fefda8`)
**Routing target:** N/A — close at D14

---

## Section C — Reviewer-Filed Carry-Forward Items (Not Yet DEFs)

These were flagged by Tier 2 reviewers across sessions but didn't rise to DEF-worthy. Documented here so they don't disappear.

### S5a.2 reviewer F2 — Duplicate `_AUDIT_DDL` in `argus/api/routes/alerts.py`
**Status:** ✅ **ALREADY RESOLVED via Impromptu A** (verified by grep at this matrix's authorship — no `_AUDIT_DDL` constant remains in routes layer)
**Routing target:** N/A — sprint-close cleans up the stale "outstanding" register entry

---

### S5a.2 reviewer F3 — Best-effort SQLite write with WARNING-only log on failure
**Status:** Defensive-design choice consistent with DEC-345 fire-and-forget pattern
**Routing confidence:** **OPPORTUNISTIC** — only revisit if SQLite write failures are observed in production
**Routing target:** **Future hygiene session if EvaluationEventStore adopts a different pattern AND we want consistency**

---

### S5a.1 reviewer F8 — Alerts REST routes have no rate limiting (JWT-only)
**Status:** ACCEPTABLE for V1
**Routing confidence:** **OPPORTUNISTIC** — only revisit if alert volume escalates unexpectedly
**Routing target:** **Per-route throttle could land alongside DEF-228 backend-alerts session**

---

### S5b reviewer F2 — `ibkr_auth_failure` E2E coverage gap
**Status:** ✅ **CLOSED via Impromptu A's DEF-225** (`TestE2EIBKRAuthFailureAutoResolution` exercises `OrderFilledEvent` clearing leg)
**Routing target:** N/A

---

### S5d reviewer INFO-1 — Modal exit animation likely does not play
**Source:** `{X && <Modal/>}` pattern unmounts before Framer Motion `AnimatePresence` exit can fire
**Status:** Cosmetic only; entry animation works
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future UI polish sprint, ideally bundling with DEF-226 focus-trap work**

**Why bundle:** Both DEF-226 and this one touch the same modal-shell concerns. A single accessibility-and-motion-polish sprint addresses both with one pass through `ConfirmModal` + `AlertAcknowledgmentModal` + `AlertDetailView`.

---

### S5e reviewer INFO-1 — `AlertDetailView` modal exit animation likely does not play
**Status:** Same pattern as S5d INFO-1; carry-over
**Routing target:** Same — bundle with DEF-226 focus-trap work

---

### S5e reviewer INFO-2 — `AlertDetailView` and `AlertToastStack` share z-50
**Status:** Working as intended (last-render-wins via DOM order)
**Routing target:** N/A — accepted as V1 behavior

---

### S5b carry-forward — Conftest fixture duplication ~50 LOC
**Source:** S5b Judgment Call 3 (intentional; avoids regression in 25+ unrelated tests)
**Status:** Filed as eligible for future test-hygiene session
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future test-hygiene session OR `post-31.9-component-ownership` work** (the right time to refactor shared fixtures is when the consuming tests are being touched anyway)

---

### S5b carry-forward — `phantom_short_startup_engaged` 24h-elapsed branch E2E
**Source:** S5b closeout matrix gap analysis
**Status:** Would require time-mocking inside the predicate; deferred
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future test-hygiene session bundled with other time-mocking-required tests**

---

### Impromptu B reviewer Concern 2 — `_log_post_start_symbology_size` task lifecycle
**Status:** Pre-existing pattern; not introduced by Impromptu B
**Routing confidence:** **CONFIDENT (sibling-class)**
**Routing target:** **`post-31.9-component-ownership` sprint** — explicitly identified as DEF-202 sibling-class issue (long-lived task lifecycle hygiene)

**Why confident:** The component-ownership sprint is where DEF-175/182/193/201/202 land; this is structurally adjacent.

---

### Impromptu B reviewer Concern 3 — Suppression test depends on `start()` not resetting `_stale_published`
**Status:** Production-side docstring is canonical guard
**Routing target:** N/A — no remediation needed

---

### Impromptu C reviewer LOW #1 — CounterfactualStore `variant_id` ALTER bare-except
**Source:** Pre-existing pattern from before FIX-08 narrowed-catch convention
**Routing confidence:** **CONFIDENT (sibling-class)**
**Routing target:** **`post-31.9-component-ownership` sprint** OR a dedicated SQLite-pattern-alignment hygiene session

**Why confident-ish:** Component-ownership work touches CounterfactualStore construction; aligning the bare-except to FIX-08 pattern is a natural co-located change. Could also wait for any sprint that touches `argus/intelligence/counterfactual_store.py` for substantive reasons.

---

### Impromptu C reviewer LOW #2 — 4 legacy ALTER fallback paths lack dedicated unit tests
**Source:** Pre-existing gap; only `catalyst_events.fetched_at` has dedicated regression coverage
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future test-hygiene session OR future migration v2 work that retires the legacy ALTER blocks** (per Impromptu C reviewer Concern A — `ALTER TABLE ADD COLUMN IF NOT EXISTS` via PRAGMA `table_info` pre-check)

**Specific gap-tests needed:**
- `counterfactual_positions.variant_id` legacy ALTER
- `counterfactual_positions.scoring_fingerprint` legacy ALTER
- `variants.exit_overrides` legacy ALTER
- `regime_snapshots.vix_close` legacy ALTER

---

### Impromptu C reviewer LOW #3 — VIXDataService sync `_init_db()` test-API compromise
**Status:** Defensible compromise; pure test-only scenario
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future refactor that converts the sync test API to async OR provides a sync-mode framework path**

---

### Impromptu C reviewer Concern A — Future migration v2 ALTER retirement opportunity
**Source:** Reviewer concern noting that legacy ALTER blocks could be retired via migration v2 with `ALTER TABLE ADD COLUMN IF NOT EXISTS` (PRAGMA `table_info` pre-check)
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Whichever sprint first needs a schema change in any of the 7 affected DBs** — that's the natural moment to retire the post-`apply_migrations` legacy block AND register a v2 migration

**Why opportunistic:** Pre-creating v2 migrations across 7 DBs without a triggering schema need would be premature.

---

## Section D — Sprint-31.91-Specific Code-Level Items (Not DEF-Worthy)

These were tracked sprint-wide as "outstanding" but are mostly informational, accepted by review, or pre-existing.

### S0 — `asyncio.get_event_loop().time()` in IBKR polling loop
**Routing target:** **When Python floor bumps to 3.12+** (unscoped sprint)

---

### S2c.1 — `OrderManager.stop()` does not await `_pending_gate_persist_tasks`
**Source:** S2c.1 review concern #2
**Routing confidence:** **CONFIDENT (sibling-class)**
**Routing target:** **`post-31.9-component-ownership` sprint** — graceful-shutdown lifecycle hygiene is the same concern family as DEF-202 sibling

---

### S2c.1 — `rejection_stage="risk_manager"` overload for `phantom_short_gate`
**Routing confidence:** **CONFIDENT**
**Routing target:** **DEF-177 cross-domain enum work sprint** — explicitly tied to DEF-177's enum split

---

### S2c.2 — `_phantom_short_clear_cycles` reset_daily_state symmetry
**Routing target:** **Future alignment session opportunistically**

---

### S2c.2 — LONG-shares branch not directly exercised by 4 new auto-clear tests
**Routing target:** **Future test-hygiene session**

---

### S2d — Test 6 anchors on S2c.1's rehydration log not S2d's lifespan log
**Status:** Behaviorally correct, small docstring/anchor mismatch
**Routing target:** **OPPORTUNISTIC** — fix when the file is touched for substantive reasons

---

### S2d — `prior_engagement_source` hardcoded
**Status:** Partially addressed at S5a.2 via threshold provider injection
**Routing target:** **OPPORTUNISTIC** — full alignment with persisted IDs in future session

---

### S2d — Audit table `phantom_short_override_audit` has no retention policy by design
**Status:** Intentional (forensic-grade audit log)
**Routing target:** N/A — accepted by design

---

### S2b.2 — Pass 1 retry SELL detection at `:1777` consistency gap
**Routing target:** **OPPORTUNISTIC** — fix when `argus/execution/order_manager.py:1777` area is touched for substantive reasons

---

### S2b.2 — Spec do-not-modify line range `:1670-1750` for `order_manager.py` doesn't actually contain SELL-detection branching
**Status:** Spec-anchor discrepancy
**Routing target:** **CONFIDENT** — Future impl prompts should reference structural anchors not line numbers (per S5d's RULE-038 drift count of 7, this is a recurring problem worth a process improvement note in `process-evolution.md`)

---

### S4 closeout — Mass-balance script regex doesn't pick up trail/escalation SELL placements
**Status:** Conservative-correct flagging
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **First time the operator's symbol-trace workflow becomes friction OR adjacent work in `scripts/validate_session_oca_mass_balance.py`**

---

### S4 closeout — `Position closed` log line lacks share count
**Status:** Test-side reconstruction; not a runtime-code dependency
**Routing target:** **OPPORTUNISTIC** — Logger improvement opportunistic

---

### S4 closeout — `Order filled:` log line lacks symbol/side
**Status:** Same as above
**Routing target:** **OPPORTUNISTIC**

---

### S4 closeout — Mass-balance script flags 195 `unaccounted_leak` rows on Apr 24 cascade log
**Status:** Expected (validation surface; Apr 24 IS the known-bad cascade reference)
**Routing target:** N/A — by design

---

### S4 reviewer Focus Area 6 minor — Item 7 historical references in HISTORICAL/FROZEN docs preserve compact-YYYYMMDD or Unix-epoch
**Status:** Intentional preservation
**Routing target:** **OPPORTUNISTIC** — opportunistic doc-hygiene pass

---

### S5a.1 reviewer F7 — EOD verify polling residual_shorts last-snapshot semantics inline comment
**Status:** Optional doc-hygiene
**Routing target:** **OPPORTUNISTIC**

---

### S5c — RULE-038 judgment calls J1-J3 acknowledged
**Status:** Reviewer-accepted
**Routing target:** N/A — closed at review

---

### S5d — Same-operator-two-tabs duplicate-ack edge case
**Status:** V1 acceptable (audit log preserves truth)
**Routing target:** **CONFIDENT — closed automatically when DEF-227 (auth context) lands**

---

### S5d — 5 in-Dashboard `AlertToastStack` mount sites
**Status:** ✅ **RESOLVED via Session 5e** (relocated to `AppShell.tsx`)
**Routing target:** N/A — close at D14

---

### Sprint 31.75 cleanup tracker (from `userMemories`) — Unreachable `else` branch in BacktestEngine fingerprint registration
**Routing confidence:** **OPPORTUNISTIC**
**Routing target:** **Future hygiene session OR opportunistically when BacktestEngine is touched for substantive reasons**

**Note:** Trivial 5-min fix. Could ride along with any future BacktestEngine work.

---

### Sprint 31.75 cleanup tracker — SQL f-string interpolation for numeric fields in `resolve_sweep_symbols.py`
**Routing confidence:** **CONFIDENT**
**Routing target:** **Sprint 31.5** (Parallel Sweep Infrastructure) — that sprint owns sweep tooling and would naturally touch this script

**Why confident:** Sprint 31.5 is in the build queue and explicitly covers the sweep tooling layer; this fix is in scope.

---

### Sprint 31.75 cleanup tracker — Hardcoded view name coupling in `resolve_sweep_symbols.py`
**Routing confidence:** **CONFIDENT**
**Routing target:** **Sprint 31.5** (same rationale as above)

---

### Sprint 31.75 cleanup tracker — Pre-existing xdist race condition in `test_history_store_migration`
**Routing confidence:** **CONFIDENT**
**Routing target:** **Future xdist-flakes-targeted hygiene session** — bundles naturally with DEF-150 / DEF-167 / DEF-171 / DEF-190 / DEF-192 family

**Why confident:** All xdist flakes share a single test-engineering domain; addressing them piecemeal is wasteful. They're best handled as a focused hygiene sprint.

---

## Section E — Pre-Existing Flakes (Track Separately, NOT Sprint-31.91 Scope)

For completeness — these are tracked outside Sprint 31.91 but worth listing here so D14 doesn't accidentally try to close them:

| Flake | Description |
|---|---|
| **DEF-150** | Time-of-day arithmetic, first 2 min of every hour |
| **DEF-167** | Vitest hardcoded-date scan |
| **DEF-171** | `ibkr_broker` xdist race |
| **DEF-190** | `pyarrow`/xdist `register_extension_type` race |
| **DEF-192** | Runtime warning cleanup debt (~25-27 warnings, xdist-order-dependent within categories) |
| **DEF-205** | Pytest date-decay sibling of DEF-167 (RESOLVED by TEST-HYGIENE-01 on 2026-04-24) |

**Routing target for the OPEN flakes:** **Dedicated xdist-flakes hygiene sprint** at operator's discretion. None of these are sprint-gating.

---

## Section F — Process-Improvement Observations (For `process-evolution.md` D14 Update)

### F.1 — DEC-328 full-suite verification gap at Tier 1 boundaries
**Surfaced by:** Post-S5e catalog freshness hotfix (`4c737d5`)
**Observation:** S5e Tier 2 reviewer + S5e closeout both reported scoped tests (`test_alerts.py 12→15` + Vitest `902→913`) without running full pytest. The catalog freshness gate (`tests/docs/test_architecture_api_catalog_freshness.py`, DEF-168 regression guard) only fires on full suite, so the missing audit endpoint in `docs/architecture.md` slipped through to CI.
**Routing confidence:** **CONFIDENT — next sprint planning**
**Routing target:** **Sprint planning conversation for Sprint 31.92 or whichever sprint is next**
**Suggested resolution:**
- Tighten DEC-328 with explicit "full suite required at Tier 1 boundary" language
- OR add a CI-side guard that fires on PR boundaries regardless of session-local test scope
- OR amend `templates/work-journal-closeout.md` to require explicit declaration of "full suite verified" vs "scoped only"

### F.2 — Spec line-number drift (RULE-038 surface area)
**Observation:** Sprints 31.91's RULE-038 drift count was substantial:
- S5b: 2 stale line numbers (`:453` actual `~:570`; `:531` actual `~:416-420`)
- S2b.2: spec line range `:1670-1750` for `order_manager.py` didn't contain claimed SELL-detection branching
- S5d: 7 prompt-vs-current-code drifts disclosed
- S5e: 6 prompt-vs-current-code drifts disclosed

**Routing confidence:** **CONFIDENT — `templates/implementation-prompt.md` v1.5.0 already adopted structural-anchor amendment 2026-04-28**
**Routing target:** **Already addressed in workflow metarepo at v1.3.0 (per-file).** Ongoing reinforcement in next sprint planning.

### F.3 — Per-session register discipline absorbed 18 refreshes without conversation drift
**Observation:** The per-session register discipline formalized at S2a (workflow v1.2.0) held firm through 18 refreshes covering 25 implementation sessions + 2 in-sprint hotfixes.
**Routing target:** N/A — pattern is working. Worth highlighting in `process-evolution.md` D14 update.

### F.4 — Bookkeeping discipline (8 consecutive sessions clean)
**Observation:** S5a.2 + S5b + Impromptu A + Impromptu B + S5c + Impromptu C + S5d + S5e closeouts cited `tests_added` matching actual delta. RULE-038 sub-bullet feedback from S5a.1's +21 vs +18 cosmetic discrepancy was internalized cleanly.
**Routing target:** N/A — pattern is working.

---

## Section G — Routing Confidence Summary

| Confidence | Count | Items |
|---|---|---|
| **CONFIDENT** | 8 | DEF-211 (Sprint 31.93), DEF-212 (Sprint 31.92), DEF-209 (Sprint 35+), DEF-208 (live-enable transition), DEF-222 (first producer-wiring sprint), Sprint 31.75 SQL f-string + view-name to Sprint 31.5, Process F.1 to next sprint planning |
| **CONFIDENT (sibling-class)** | 3 | Impromptu B Concern 2 + Impromptu C LOW #1 + S2c.1 OrderManager.stop() — all to `post-31.9-component-ownership` |
| **OPPORTUNISTIC** | 16 | DEF-226, DEF-228, DEF-229, DEF-230, DEF-215, plus 11 reviewer/code-level items where the trigger is genuinely event-driven |
| **BLOCKED** | 1 | DEF-227 (waits for auth context) |
| **N/A — RESOLVED THIS SPRINT** | 12 | DEF-014, DEF-158, DEF-213, DEF-214, DEF-216, DEF-217, DEF-218, DEF-219, DEF-220, DEF-221, DEF-223, DEF-224, DEF-225 |

---

## D14 Doc-Sync Action Items (Generated From This Matrix)

When D14 doc-sync runs, it should:

1. **Apply 13 RESOLVED-IN-SPRINT transitions to CLAUDE.md DEF table** (DEF-014, DEF-158, DEF-213, DEF-214, DEF-216, DEF-217, DEF-218, DEF-219, DEF-220, DEF-221, DEF-223, DEF-224, DEF-225) per `pre-impromptu-doc-sync-manifest.md`

2. **Update remaining DEF rows** in CLAUDE.md with explicit routing per Section A above:
   - DEF-222 → "Routes to first sprint introducing a producer for `ReconciliationCompletedEvent`/`IBKRReconnectedEvent`/`DatabentoHeartbeatEvent`"
   - DEF-226 → "Future UI accessibility audit pass; bundle with S5d/S5e modal exit-animation INFO findings"
   - DEF-227 → "BLOCKED on auth context infrastructure"
   - DEF-228, DEF-229, DEF-230 → "OPPORTUNISTIC; clear technical scope per S5e closeout § Deferred Items"

3. **Add 5 new DEF entries to CLAUDE.md** (DEF-226, DEF-227, DEF-228, DEF-229, DEF-230) with routing language above

4. **Add Section F.1 + F.2 entries** to `process-evolution.md`:
   - DEC-328 full-suite-at-Tier-1 process gap (catalog hotfix lesson)
   - RULE-038 drift surface area (already addressed; reinforcement)

5. **Verify all "sibling-class" routings** by cross-referencing with the named target sprint's known scope:
   - `post-31.9-component-ownership` should explicitly absorb: Impromptu B Concern 2, Impromptu C LOW #1, S2c.1 OrderManager.stop()
   - Sprint 31.5 should explicitly absorb: 31.75 SQL f-string + view-name coupling

6. **Surface this matrix file (`def-disposition-matrix.md`) in `sprint-history.md`** as the canonical Sprint 31.91 carry-forward reference

---

*End Sprint 31.91 DEF Disposition Matrix.*
