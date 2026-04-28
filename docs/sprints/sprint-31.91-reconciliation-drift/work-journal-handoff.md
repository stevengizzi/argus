# Sprint 31.91 — Work Journal Handoff (Post-Tier-3-#2 + Pre-Impromptu Doc-Sync)

> **For:** Work Journal conversation (Claude.ai), re-entered after Tier 3 #2 disposition + pre-impromptu doc-sync land on `main`.
> **Generated:** 2026-04-28.
> **Source:** Tier 3 #2 conversation (the conversation that produced the amended verdict + this pre-sync's prompts).

## TL;DR — what changed since your last register refresh

Your last register refresh was 2026-04-28 post-S5b at commit `07070e2`. Since then:

1. **Tier 3 #2 architectural review completed.** Verdict: PROCEED with conditions (amended). Verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md`. Original verdict generated, then amended after operator disposition reviewed routing.
2. **9 new DEFs filed** (DEF-217 through DEF-225). Routing details below.
3. **Workflow metarepo extended with two amendments** (per-file forward bumps, not a global version step): NEW `protocols/mid-sprint-doc-sync.md` v1.0.0 formalizing the multi-sync coordination pattern + structural-anchor amendment to `templates/implementation-prompt.md` (1.4.0 → 1.5.0) + cross-references in 7 other files. The metarepo uses per-file versioning; there is no single "metarepo version."
4. **Pre-impromptu doc-sync ran** (the commit you're seeing now). Updated CLAUDE.md, work-journal-register, sprint-spec; created 3 new impl prompts; amended Session 5c impl prompt; produced this handoff + a mechanical manifest.
5. **Sprint shape revised.** Three new impromptus inserted (A, B, C); Session 5c entry conditions tightened; DEC-388 materialization deferred to sprint-close.

## New session order (REVISED)

The sprint runs in this exact order from here:

1. ⏳ **Impromptu A — Alert Observability Hardening** (DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225)
   - Impl prompt: `sprint-31.91-impromptu-a-alert-hardening-impl.md`
   - Tier 2 inline within the implementing session.
   - Estimated test delta: +4-5 tests.
   - **Critical**: DEF-217 is HIGH severity (Databento alert_type string mismatch); MUST land before live transition.

2. ⏳ **Impromptu B — Databento Heartbeat Producer + DEF-217 End-to-End Validation** (DEF-221)
   - Impl prompt: `sprint-31.91-impromptu-b-databento-heartbeat-impl.md`
   - **Condition: Impromptu A landed CLEAR** (the validation test depends on DEF-217's fix).
   - Estimated test delta: +1 test (the new E2E producer-driven test).

3. ⏳ **Session 5c — `useAlerts` Hook + Dashboard Banner + DEF-220 Disposition**
   - Impl prompt: `sprint-31.91-session-5c-impl.md` (amended)
   - **Condition: Impromptus A and B both landed CLEAR.**
   - Includes DEF-220 disposition (recommend removal).

4. ⏳ **Impromptu C — Migration Framework Adoption Sweep** (DEF-223)
   - Impl prompt: `sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`
   - Mechanical work; ~200-300 LOC across 7 service files + 7 tests.
   - Estimated test delta: +28 tests (4 per DB × 7 DBs).

5. ⏳ **Session 5d** — toast notifications + acknowledgment UI flow (unchanged from prior plan).

6. ⏳ **Session 5e** — Observatory alerts panel + cross-page integration (unchanged from prior plan). **DEF-014 closes here.**

7. ⏳ **Sprint-close doc-sync** — reads `pre-impromptu-doc-sync-manifest.md` per `protocols/mid-sprint-doc-sync.md` v1.0.0 contract; writes DEC-385 + DEC-388; transitions all RESOLVED-IN-SPRINT DEFs.

## Updated state of `work-journal-register.md`

The on-disk register at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` is now authoritative for the new sprint shape. Key updates:

- **Last Refresh** table reflects 2026-04-28 post-Tier-3-#2-disposition.
- **Tier 3 #2** marked COMPLETE.
- **DEC-388** moved from "Materializes at S5e" to "Materializes at sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.0.0)".
- **DEFs section** has 9 new rows (DEF-217 through DEF-225).
- **Session Order section** revised (6 new rows for Tier 3 #2, pre-sync, Impromptu A, Impromptu B, Session 5c moved, Impromptu C inserted).
- **Carry-Forward Watchlist** updated: 7 items moved from "Future/DESIGN/OPPORTUNISTIC" status to "OPEN — Impromptu X" status.

When you re-enter the Work Journal, **trust the on-disk register** as authoritative. Refresh your in-conversation understanding from the file.

## File map — where everything lives

### Sprint folder (`docs/sprints/sprint-31.91-reconciliation-drift/`)
- `tier-3-review-2-verdict.md` — amended verdict (architectural + DEF routing decisions).
- `pre-impromptu-doc-sync-manifest.md` — mechanical handoff to sprint-close (read by sprint-close doc-sync).
- `work-journal-handoff.md` — this file (narrative handoff).
- `work-journal-register.md` — authoritative durable register (updated by this pre-sync).
- `sprint-spec.md` — amended (D15 + D16 + AC blocks + D9b extension).
- `sprint-31.91-impromptu-a-alert-hardening-impl.md` — NEW.
- `sprint-31.91-impromptu-b-databento-heartbeat-impl.md` — NEW.
- `sprint-31.91-impromptu-c-migration-framework-sweep-impl.md` — NEW.
- `sprint-31.91-session-5c-impl.md` — AMENDED (DEF-220 fold).

### ARGUS top-level
- `CLAUDE.md` — updated (9 new DEF rows + DEF-175 annotation).

### Workflow metarepo (separate clone; per-file versions)
- `protocols/mid-sprint-doc-sync.md` — NEW v1.0.0 (governs this sync's pattern).
- `templates/implementation-prompt.md` — 1.4.0 → 1.5.0 (structural-anchor format).
- `templates/doc-sync-automation-prompt.md` — 1.1.0 → 1.2.0 (manifest-reading at sprint-close).
- `templates/work-journal-closeout.md` — 1.3.0 → 1.4.0 (manifest acknowledgment requirement).
- `protocols/sprint-planning.md` — 1.1.0 → 1.2.0 (cross-reference + structural-anchor requirement).
- `protocols/in-flight-triage.md` — 1.2.0 → 1.3.0 (cross-reference).
- `protocols/tier-3-review.md` — 1.0.1 → 1.0.2 (cross-reference + manifest output requirement).
- `protocols/impromptu-triage.md` — 1.1.0 → 1.2.0 (cross-reference + DEF-state-change manifest requirement).
- `bootstrap-index.md` — header added at NEW v1.0.0 (Protocol Index + Conversation Type table entries for mid-sync).
- `schemas/structured-closeout-schema.md` — header added at NEW v1.0.0 (`mid_sprint_doc_sync_ref` field).

## How to proceed (Work Journal first actions)

1. **Acknowledge the handoff context.** Confirm you've read this document and understand the new sprint shape.
2. **Refresh your register-of-record** by reading `work-journal-register.md` from disk. Trust it over any in-conversation memory.
3. **Verify pre-sync landed correctly.** Run:
   ```bash
   git log -3 --oneline
   ls docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-*-impl.md
   ls docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md
   ```
   Confirm 3 new impl prompts + manifest + this handoff exist.
4. **Begin Impromptu A.** Read `sprint-31.91-impromptu-a-alert-hardening-impl.md` in full. Spawn a fresh Claude Code session for the implementer; pass the impl prompt verbatim. Apply per-session register discipline (refresh register after the impromptu's close-out).
5. **After Impromptu A's Tier 2 inline review CLEAR**: refresh register, proceed to Impromptu B.
6. **Continue through the new session order** through Sprint-close.

## Sprint-close coordination (forward-looking)

When all sessions through S5e have landed CLEAR, trigger sprint-close. The sprint-close doc-sync runs under `templates/doc-sync-automation-prompt.md` v1.2.0 (the version that introduced manifest-reading), which:

1. Reads ALL `*-doc-sync-manifest.md` files in the sprint folder (currently just `pre-impromptu-doc-sync-manifest.md`; future syncs may add more).
2. Verifies each claimed DEF transition's owning close-out landed CLEAR.
3. Applies transitions in manifest-listed order.
4. Writes DEC-385 + DEC-388 to `decision-log.md` per the deferred-text sources.
5. Updates `architecture.md` per the catalog freshness items.
6. Refreshes CLAUDE.md test count baseline.
7. Writes `sprint-history.md` entry covering Sprint 31.91 in full.
8. Close-out narrative includes "Mid-sprint doc-syncs in this sprint" section per `templates/work-journal-closeout.md` v1.4.0.

You don't need to remember any of this manually — it's all encoded in the manifest + the per-file workflow contracts (the metarepo doesn't have a single "workflow v1.3.0" version; each protocol/template carries its own version line). Sprint-close runs the standard automation; the magic is in the manifest reading.

## Critical reminders

- **DEF-217 is HIGH severity correctness defect** (Databento alert_type string mismatch). It MUST land in Impromptu A before any post-sprint operations. The DEF-221 fix in Impromptu B depends on DEF-217.
- **Daily-flatten cessation criteria unchanged.** Criterion #5 (5 paper-sessions clean post-seal) still applies. Operator continues `scripts/ibkr_close_all_positions.py` daily until all 5 criteria met.
- **DEC-385 + DEC-388 NOT yet written.** Both materialize at sprint-close per Pattern B. Don't try to write them now.
- **Workflow contracts are now binding.** Future impl prompts must use structural anchors per `templates/implementation-prompt.md` v1.5.0+. Future mid-sprint syncs must produce manifests per `protocols/mid-sprint-doc-sync.md` v1.0.0+.

## Cross-references

- **Tier 3 #2 conversation:** the Claude.ai conversation that produced the amended verdict + this pre-sync's prompts. Saved per usual conversation history.
- **Tier 3 #2 amended verdict:** `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md`.
- **Workflow metarepo amendment commit:** in claude-workflow repo at v1.3.0.
- **Pre-impromptu doc-sync commit (this commit):** identifiable in `git log -1` after the pre-sync lands.
- **Operator runbook (one-time use):** the runbook used to execute Tier 3 #2 disposition, no longer needed once we're past Step 4 of the runbook.

## Operator-facing one-paragraph summary (for re-entry into the Work Journal)

> Tier 3 #2 architectural review for Sprint 31.91 completed 2026-04-28 (PROCEED with conditions, amended). 9 new DEFs filed; 7 routed RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c), 1 to Session 5c (DEF-220), 1 deferred (DEF-222). Workflow metarepo extended with NEW `protocols/mid-sprint-doc-sync.md` v1.0.0 + structural-anchor amendment to `templates/implementation-prompt.md` (now v1.5.0) + cross-references in 7 other files (per-file forward bumps; no global version). Pre-impromptu doc-sync landed on `main`. Sprint shape revised: new order is Impromptu A → Impromptu B → S5c → Impromptu C → S5d → S5e → sprint-close. DEC-388 deferred to sprint-close (Pattern B). Resume by reading `sprint-31.91-impromptu-a-alert-hardening-impl.md` and beginning Impromptu A with a fresh Claude Code session.
