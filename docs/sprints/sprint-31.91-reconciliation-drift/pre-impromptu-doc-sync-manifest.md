<!-- protocol-version: protocols/mid-sprint-doc-sync.md v1.0.0 -->
<!-- Manifest type: pre-impromptu doc-sync (Sprint 31.91 Tier 3 #2 disposition) -->
<!-- Generated: 2026-04-28 -->

# Pre-Impromptu Doc-Sync Manifest (Sprint 31.91)

## Triggering event

Sprint 31.91 Tier 3 #2 architectural review (PROCEED with conditions, AMENDED 2026-04-28) surfaced 9 new DEFs and required workflow metarepo amendments. Operator disposition (2026-04-28) routed 7 of the 9 DEFs as RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c) and 1 via Session 5c (DEF-220), with 1 deferred (DEF-222). DEC-388 materialization deferred to sprint-close per Pattern B.

This manifest is the mechanical handoff to the sprint-close doc-sync, which will read it and apply the OPEN→RESOLVED transitions on each DEF after the owning session/impromptu close-outs land CLEAR.

Verdict artifact: `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended).

## Files touched by this pre-sync

| File | Change shape | Sprint-close transition owed |
|---|---|---|
| `CLAUDE.md` | 10 DEF rows added: DEF-216 backfill (RESOLVED, IMPROMPTU-10 commit `c36a30c`) + DEF-217 through DEF-225 (OPEN with routing). All rows reshape Status/Routing/Severity into the existing 4-column table's Context column as a structured `**Status:** <X> — Routing: <Y> — Severity: <Z>.` prefix. DEF-175 row annotated with main.py + set_order_manager motivators. | Each new OPEN DEF row's Context "Status:" field transitions OPEN → RESOLVED-IN-SPRINT per its routing at sprint-close; DEF-216 row already at RESOLVED (backfill); DEF-175 row remains OPEN. |
| `docs/project-knowledge.md` | Stale "Workflow protocol version: 1.2.0" reference replaced with per-file versioning pointer language; cross-references to current per-protocol versions added. | None (pointer language is forward-compatible; sprint-close should NOT need to re-edit). |
| `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` | Last Refresh table updated; Tier 3 #2 PHASE BOUNDARY section replaced with "Tier 3 #2 — COMPLETE"; DECs section updated (DEC-388 deferral to sprint-close); 9 new DEF rows in DEFs table; Session Order section revised with 6 new rows (Tier 3 #2 + pre-sync + Impromptu A + Impromptu B + Session 5c + Impromptu C); Carry-Forward Watchlist updated to reflect new DEF routings. | Final Last Refresh update at sprint-close; final test count refresh; final DEC reservation transitions; archive of register at sprint-close. |
| `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` | D9b auto-resolution policy table extended from 8 → 10 entries (eod_residual_shorts + eod_flatten_failed); D15 deliverable added (Impromptu B); D16 deliverable added (Impromptu C); AC blocks for D15 and D16 added. | No further sprint-close updates expected (the spec is now complete for the revised sprint shape). |
| `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md` | NEW FILE | None (impl prompts are static once created). |
| `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md` | NEW FILE | None. |
| `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-c-migration-framework-sweep-impl.md` | NEW FILE | None. |
| `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md` | Amended: new requirement section for DEF-220 disposition; DoD updated; Closeout Requirements updated. | None (impl prompt is static once amended). |
| `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md` | NEW FILE (narrative handoff to Work Journal conversation) | None (the handoff is a one-time artifact). |
| `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` | NEW FILE (this file) | This manifest is consumed by sprint-close; sprint-close should reference it. |

## DECs DEFERRED to sprint-close (Pattern B)

| DEC | Reason for deferral | Cross-reference text source for sprint-close |
|---|---|---|
| **DEC-385** | Materialized in code at S2d 2026-04-02; write to `decision-log.md` deferred per existing plan. Pre-sync did not write because narrative is reconciliation-track concern, not in-scope for Tier 3 #2. | `docs/sprints/sprint-31.91-reconciliation-drift/session-2d-closeout.md` + Tier 3 #1 verdict for cross-references. |
| **DEC-388** | Cross-references DEFs being resolved by subsequent sessions (DEF-217/218/219/220/221/223/224/225). Writing now would document architecture-with-known-defects state. Defer to sprint-close after all RESOLVED-IN-SPRINT DEFs land. | Draft text in `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended), section "DEC-388 draft text for sprint-close doc-sync consumption". |

## DEF transitions OWED at sprint-close

| DEF | Current status (after this pre-sync) | Target status (sprint-close) | Source of resolution |
|---|---|---|---|
| **DEF-014** | OPEN — producer side resolved at S5b | RESOLVED (full closure at S5e + frontend) | S5e close-out commit |
| **DEF-213** | RESOLVED-IN-CODE at S5a.1 (atomic-migration half) | Confirmed RESOLVED | S5a.1 close-out commit (already landed) |
| **DEF-214** | RESOLVED-IN-CODE at S5a.1 | Confirmed RESOLVED | S5a.1 close-out commit (already landed) |
| **DEF-217** | OPEN, routed to Impromptu A | RESOLVED-IN-SPRINT (Impromptu A) | Impromptu A close-out commit |
| **DEF-218** | OPEN, routed to Impromptu A | RESOLVED-IN-SPRINT (Impromptu A) | Impromptu A close-out commit |
| **DEF-219** | OPEN, routed to Impromptu A | RESOLVED-IN-SPRINT (Impromptu A) | Impromptu A close-out commit |
| **DEF-220** | OPEN, routed to Session 5c | RESOLVED-IN-SPRINT (Session 5c) | Session 5c close-out commit |
| **DEF-221** | OPEN, routed to Impromptu B | RESOLVED-IN-SPRINT (Impromptu B) | Impromptu B close-out commit |
| **DEF-222** | DEFERRED, gated on future producers | DEFERRED (no transition this sprint) | n/a (cross-sprint) |
| **DEF-223** | OPEN, routed to Impromptu C | RESOLVED-IN-SPRINT (Impromptu C) | Impromptu C close-out commit |
| **DEF-224** | OPEN, routed to Impromptu A | RESOLVED-IN-SPRINT (Impromptu A) | Impromptu A close-out commit |
| **DEF-225** | OPEN, routed to Impromptu A | RESOLVED-IN-SPRINT (Impromptu A) | Impromptu A close-out commit |

## Architecture / catalog freshness items DEFERRED to sprint-close

| Surface | Status (after this pre-sync) | Action at sprint-close |
|---|---|---|
| `architecture.md` "alerts" catalog block | Already populated by S5a.1 | Verify still current after Impromptu A's policy table extension; add migration framework adoption note (Impromptu C). |
| `architecture.md` `WS /ws/v1/alerts` block | Already populated by S5a.2 | Verify still current. |
| `architecture.md` migration framework section | Mentions only `operations.db` adoption | Extend to all 8 DBs after Impromptu C. |
| `architecture.md` auto-resolution policy table | 8 entries documented | Extend to 10 entries after Impromptu A. |
| `pre-live-transition-checklist.md` | DEF-217 + DEF-221 not yet on checklist | Add gating items: "DEF-217 RESOLVED status verified" + "DEF-221 RESOLVED status verified" (both implicitly done via Impromptu A+B; checklist entries make explicit). |
| `sprint-history.md` | Sprint 31.91 entry not yet written | Write at sprint-close covering all 17 sessions + 4 impromptus + 2 Tier 3 reviews. |
| CLAUDE.md test count baseline | Currently cites `5,080` | Refresh at sprint-close to actual final count after all impromptus + S5c-5e land. |

## Workflow version compliance

This manifest was produced under `protocols/mid-sprint-doc-sync.md` v1.0.0 (introduced 2026-04-28) and `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment, 2026-04-28). The metarepo uses per-file versioning. Sprint-close doc-sync MUST run against a metarepo state where `protocols/mid-sprint-doc-sync.md` exists at v1.0.0 or higher AND `templates/doc-sync-automation-prompt.md` is at v1.2.0 or higher (the version that introduced the manifest-reading step). If sprint-close runs under an earlier metarepo state, the discrepancy MUST be explicitly disclosed.

## Linked artifacts

- **Triggering verdict:** `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended 2026-04-28).
- **Workflow metarepo amendment commit:** in claude-workflow repo at v1.3.0.
- **Impl prompts produced:** `sprint-31.91-impromptu-a-alert-hardening-impl.md`, `sprint-31.91-impromptu-b-databento-heartbeat-impl.md`, `sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`. Existing `sprint-31.91-session-5c-impl.md` amended.
- **Work-journal-handoff (narrative):** `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md`.
- **Anchor commit for this pre-sync:** `<this commit's SHA>` (post-commit substitution by operator).

## Sprint-close consumption checklist

When sprint-close doc-sync runs, it must:

1. Read this manifest in full.
2. Verify each DEF transition's owning session/impromptu close-out exists and landed CLEAR. If any owning close-out is missing or NOT CLEAR, the corresponding DEF transition is SKIPPED and surfaced to operator.
3. For each transition applied, cite both this manifest AND the owning close-out commit SHA in the sprint-close commit message.
4. Write DEC-385 + DEC-388 to `decision-log.md` per the deferred-text sources above.
5. Apply the architecture.md updates per the catalog freshness table.
6. Refresh CLAUDE.md test count baseline.
7. Write the sprint-history.md entry.
8. The sprint-close close-out narrative must include a "Mid-sprint doc-syncs in this sprint" section per `templates/work-journal-closeout.md` v1.3.0.
