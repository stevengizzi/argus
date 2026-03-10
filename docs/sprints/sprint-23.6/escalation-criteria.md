# Sprint 23.6: Escalation Criteria

Escalate to Tier 3 architectural review if any of the following occur:

1. **Lifecycle integration failure:** Pipeline initialization in server.py lifespan cannot cleanly follow the AI service initialization pattern (conditional init → yield → cleanup). This would indicate an architectural mismatch that needs design-level resolution.

2. **Config loading failure:** Adding `catalyst: CatalystConfig` to `SystemConfig` breaks existing config loading (e.g., Pydantic validation rejects existing system.yaml files that lack the `catalyst` section). Default factory should prevent this, but if it doesn't, the config model hierarchy needs review.

3. **Test destabilization:** Any session causes >5 pre-existing tests to fail (not counting the session's own new tests). This suggests an unintended behavioral change.

4. **Runner behavior change:** Any existing runner test changes outcome after S5 refactoring. S5 must be behavior-neutral; any deviation is a regression.

5. **Cache corruption propagation:** Reference data cache layer (S4a) introduces test flakiness from filesystem operations, or a corrupt cache file causes anything worse than a WARNING + full-fetch fallback.

6. **Polling loop interference:** Polling task interferes with existing Event Bus subscribers, WebSocket bridge, or creates asyncio task lifecycle issues during shutdown.

7. **Storage migration failure:** `ALTER TABLE ADD COLUMN fetched_at` fails on existing catalyst.db files, or existing data becomes unreadable after schema change.

8. **Cross-session dependency breakage:** A fix in one session breaks an assumption in a dependent session that cannot be resolved within the current session's scope boundary.
