# Sprint 24.1 — Escalation Criteria

These conditions, if encountered during implementation, should trigger an immediate halt and Tier 3 review or developer consultation.

## Critical Escalations (Halt immediately)

1. **Order Manager behavioral change:** Any test involving position lifecycle (entry fill, stop execution, T1/T2 fills, position closing) fails after Session 1a modifications. This indicates the ManagedPosition changes affected execution logic, not just data passthrough.

2. **Schema migration data loss:** ALTER TABLE ADD COLUMN causes data corruption or loss of existing trade records. (Extremely unlikely with SQLite, but if it happens, halt.)

3. **Quality pipeline wiring regression:** After Session 1a, the quality engine bypass path (BrokerSource.SIMULATED or enabled=false) no longer works correctly — signals fail to pass through, or share_count is incorrectly set.

4. **E2E test reveals architectural deficiency (S2):** The ArgusSystem e2e test reveals that the quality pipeline cannot be exercised without live external services (Databento, IBKR), indicating a mocking gap that requires architectural changes to the init path.

## Warning Escalations (Proceed with caution, document in close-out)

5. **EFTS URL broken:** SEC EDGAR EFTS endpoint returns 4xx/5xx without a `q` parameter. Document the response and proposed fix, but do not redesign the SEC EDGAR source architecture. If the fix is more than a URL parameter change, defer to a future sprint.

6. **TypeScript errors exceed 22:** Running `tsc --noEmit` reveals more errors than the known 22. Fix only the pre-existing 22; document any new errors introduced by other sessions and defer.

7. **CardHeaderProps icon type requires upstream component change:** If fixing the `icon` prop error requires modifying a shared Card component used across many pages, assess blast radius. If >5 files would be affected by the type change, isolate the fix with a local type override instead.

8. **Frontend layout breaks mobile rendering:** If the Orchestrator 3-column layout or Debrief tab removal causes layout issues on mobile/PWA, defer mobile fixes and document the issue.

## Not Escalations (Expected, handle in-session)

- Existing trades returning NULL for quality columns — expected, frontend handles with "—"
- ManagedPosition quality fields defaulting to empty/zero on non-quality-engine paths — expected by design
- Minor TypeScript type adjustments beyond the 22 known errors — fix if trivial, otherwise defer
