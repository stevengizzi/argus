# Claude Code Prompt — ARGUS Pre-Impromptu Doc-Sync (Sprint 31.91)

> **Repo:** `argus` (https://github.com/stevengizzi/argus)
> **Workflow contract:** the metarepo state that includes `protocols/mid-sprint-doc-sync.md` v1.0.0 + `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment). The metarepo uses per-file versioning, not a global semantic version. Both must be live in the `claude-workflow` metarepo before this prompt runs (verify via the workflow-protocol-amendment-prompt-REVISED).
> **Triggering disposition:** Sprint 31.91 Tier 3 #2 amended verdict, 2026-04-28.
> **Mid-sync category** (per `protocols/mid-sprint-doc-sync.md` v1.3.0): Tier 3 verdict surfacing materializable items routed for in-sprint resolution.
>
> **What this prompt produces:**
> - 9 new DEF rows in `CLAUDE.md` (status: OPEN-with-routing).
> - DEF-175 annotation in `CLAUDE.md` (existing DEF, additional motivators).
> - Updated `work-journal-register.md` (new session order, DEF table additions, watchlist updates, DEC reservation transitions).
> - Amended `sprint-spec.md` (D15 + D16 deliverables, AC blocks, D9b policy table extension).
> - 3 NEW impl prompt files (Impromptu A, B, C) in v1.3.0 structural-anchor format.
> - AMENDED Session 5c impl prompt (DEF-220 fold).
> - NEW `pre-impromptu-doc-sync-manifest.md` (mechanical handoff to sprint-close).
> - NEW `work-journal-handoff.md` (narrative handoff to Work Journal conversation).
>
> **What this prompt does NOT do:**
> - Does NOT write `decision-log.md` (DEC-385 + DEC-388 deferred to sprint-close per Pattern B).
> - Does NOT transition any DEF status to RESOLVED (sprint-close owns transitions).
> - Does NOT update `sprint-history.md` (sprint-close owns).
> - Does NOT update `architecture.md` final verification (sprint-close owns).
> - Does NOT refresh CLAUDE.md test count baseline (sprint-close owns; final number isn't known yet).

---

## Pre-flight

You are operating against the `argus` repo in a Claude Code session. Verify clean starting state:

```bash
pwd  # Should be the argus repo root
git status  # Should be clean on main, no uncommitted changes
git log -5 --oneline  # Verify the most recent commit is the Tier 3 #2 verdict amendment
```

Expected most-recent commit message: `docs(sprint-31.91): amend Tier 3 #2 verdict per operator disposition` (or similar).

Verify the workflow metarepo is at v1.3.0:

```bash
cd workflow  # if the metarepo is a submodule, OR clone fresh
git log -3 --oneline  # Should include the mid-sprint-doc-sync amendment commit
ls protocols/mid-sprint-doc-sync.md  # Should exist
grep "workflow-version: 1.0.0" protocols/mid-sprint-doc-sync.md  # Should hit
grep "workflow-version: 1.5.0" templates/implementation-prompt.md  # Should hit (structural-anchor amendment)
cd -
```

If `protocols/mid-sprint-doc-sync.md` does not exist in the metarepo OR `templates/implementation-prompt.md` is not at 1.5.0+, **STOP**. The pre-sync depends on both for the new protocol and structural-anchor format. Run the (revised) workflow-metarepo amendment prompt first per the runbook.

Verify the amended Tier 3 #2 verdict is present:

```bash
grep "AMENDED 2026-04-28 post-operator-disposition" \
  docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md
# Expected: 1 hit
```

If not present, **STOP**. The verdict amendment must be on `main` first.

---

## Operating principles

This prompt operates under the metarepo state that includes `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment) and `protocols/mid-sprint-doc-sync.md` v1.0.0. Per the structural-anchor amendment:

- All edit locations are specified by structural anchors (function name, comment regex, section heading), NOT line numbers.
- Pre-flight grep-verify commands are provided for every anchor.
- If any grep-verify reveals drift (anchor not found OR returns unexpected hits), HALT and surface — do not guess.

Per the mid-sprint-doc-sync protocol (`protocols/mid-sprint-doc-sync.md`):

- DEF rows land in OPEN-with-routing status (not RESOLVED).
- DECs are NOT written by this sync (Pattern B deferral; DEC-385 + DEC-388 land at sprint-close).
- A manifest is the mandatory output, capturing every transition the sprint-close doc-sync will owe.

---

## Step 1 — Update `CLAUDE.md` DEF table

### Edit 1a — Add 10 DEF rows (1 backfill + 9 new)

**Anchor:** the DEF table in `CLAUDE.md` under the heading `## Open Defect Registry` (or `## DEFs` or similar — the actual heading varies; locate by the table containing existing DEF rows).

**Pre-flight grep-verify:**
```bash
grep -nE "^\| DEF-21[0-9] " CLAUDE.md
# Expected: rows for DEF-210 through DEF-215 at minimum. The highest existing row
# anchors the insertion point (insert AFTER it to maintain numerical order).
```

**Important context:** DEF-216 was an IMPROMPTU-10 hotfix (commit `c36a30c`) that resolved successfully but was never added to the DEF table as a row. This pre-sync includes a BACKFILL row for DEF-216 as the first of 10 inserted rows, followed by 9 new rows from Tier 3 #2 (DEF-217 through DEF-225).

**Sub-step 1a.1 — Read the IMPROMPTU-10 closeout to extract DEF-216's canonical description:**
```bash
cat docs/sprints/sprint-31.9/IMPROMPTU-10-closeout.md 2>/dev/null | head -100
git log -1 --format="%B" c36a30c
ls docs/sprints/sprint-31.91-reconciliation-drift/ | grep -iE "216|impromptu-10|hotfix"
```

From the closeout artifact's "Finding addressed" / "Defect summary" / equivalent section, extract DEF-216's:
- One-line summary (for column 2 "Item")
- Resolution attribution (commit SHA + which session/impromptu)
- Severity (likely MEDIUM-HIGH given operator-elevated trajectory per project context)

If the closeout does not exist OR does not contain a clear DEF-216 description, HALT and surface — better to leave DEF-216 unrecorded than backfill it incorrectly. The operator can address DEF-216 separately.

**Sub-step 1a.2 — Construct the DEF-216 backfill row** using ARGUS's 4-column schema with structured prefix:

```markdown
| DEF-216 | <one-line summary from closeout> | <originating session/sprint, e.g., "Sprint 31.91 IMPROMPTU-10 (2026-04-XX)"> | **Status:** RESOLVED-IN-SPRINT — Sprint 31.91 IMPROMPTU-10 — Severity: <X>. <Brief description of the defect from the closeout's Finding section, ~1-3 sentences>. Resolution attribution: commit `c36a30c`. |
```

Apply judgment: keep the Context column under ~400 characters total. If the closeout's description is much longer, summarize.

**Sub-step 1a.3 — After DEF-216 backfill, insert the 9 new Tier 3 #2 rows:**

After the existing highest DEF row (e.g., DEF-215) AND the new DEF-216 backfill row, insert in numerical order (using ARGUS's 4-column schema with structured prefix):

```markdown
| DEF-217 | Databento dead-feed alert_type producer/consumer string mismatch | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu A — Severity: HIGH. `argus/data/databento_data_service.py` Databento dead-feed emitter publishes `alert_type="max_retries_exceeded"` but auto-resolution policy table in `argus/core/alert_auto_resolution.py` keys on `"databento_dead_feed"`. Strings do not match; policy entry is dead code in production. MUST land before live transition. Routing: Impromptu A (alert observability hardening). |
| DEF-218 | EOD policy table missing entries (eod_residual_shorts + eod_flatten_failed) | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu A — Severity: MEDIUM. `eod_residual_shorts` + `eod_flatten_failed` alert types (emitted at `argus/execution/order_manager.py`) missing from auto-resolution policy table. Both sit ACTIVE indefinitely until operator ack. Suggested resolution: add explicit `PolicyEntry` rows; both `NEVER_AUTO_RESOLVE` + `operator_ack_required=True`. Routing: Impromptu A. |
| DEF-219 | Policy table exhaustiveness regression guard not test-enforced | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu A — Severity: MEDIUM. Policy table exhaustiveness invariant not enforced by tests. The hardcoded `expected = {...}` set in `test_policy_table_is_exhaustive` is a snapshot, not a regression guard against producer-side drift. Would have caught DEF-217 + DEF-218 at test time. Resolution: AST/tokenize-based regression guard scanning production for `SystemAlertEvent(alert_type=<literal>)` and asserting each literal is a policy-table key. Routing: Impromptu A (bundled with DEF-217 + DEF-218 fixes). |
| DEF-220 | `acknowledgment_required_severities` field has no consumer | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Session 5c — Severity: LOW. `AlertsConfig.acknowledgment_required_severities` field at `argus/core/config.py` has no consumer. Field is documentation-only. Per-alert-type `PolicyEntry.operator_ack_required` already encodes the equivalent control. Disposition decision: wire (gate at route or auto-resolve layer) OR remove (rely on per-alert-type field). Recommendation: removal. Routing: Session 5c (frontend session naturally opens AlertsConfig territory). |
| DEF-221 | DatabentoHeartbeatEvent producer wiring | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu B — Severity: MEDIUM. `DatabentoHeartbeatEvent` producer wiring — data-layer health poller emits the event consumed by `databento_dead_feed` auto-resolution predicate. No specific sprint home named in S5a.2 closeout. Pairs with DEF-217 (Impromptu A) for end-to-end auto-resolution validation with a real producer. Routing: Impromptu B (Databento heartbeat producer). |
| DEF-222 | Predicate-handler subscribe-before-rehydrate audit | Tier 3 #2 architectural review (2026-04-28) | **Status:** DEFERRED — gated on future producers — Severity: MEDIUM (latent). Predicate-handler subscriptions wired in `HealthMonitor.start()` BEFORE `rehydrate_alerts_from_db()`. Informational today: rehydration loop has no `await` points, no producers exist for the 3 deferred-emission events. When producers land for `ReconciliationCompletedEvent` / `IBKRReconnectedEvent` / `DatabentoHeartbeatEvent`, audit and likely defer `_subscribe_predicate_handlers()` to AFTER rehydration. Routing: sprint-gating on whichever producer-wiring sprint lands first (post-31.9-component-ownership / post-31.9-reconnect-recovery / data-layer). |
| DEF-223 | Migration framework adoption sweep across 7 SQLite DBs | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu C — Severity: LOW. Migration framework adoption sweep across the 7 ARGUS SQLite DBs other than `operations.db` (`catalyst.db`, `evaluation.db`, `regime_history.db`, `learning.db`, `vix_landscape.db`, `counterfactual.db`, `experiments.db`). Each DB's existing DDL works today; the sweep wraps each in a v1 Migration to establish migration framework as the canonical home for schema evolution. Mechanical work (~200 LOC + tests). Routing: Impromptu C. |
| DEF-224 | Duplicate `_AUDIT_DDL` between routes layer and migration framework | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu A — Severity: LOW. Duplicate `_AUDIT_DDL` between `argus/api/routes/alerts.py` (idempotent inline DDL on every acknowledge call) and `argus/data/migrations/operations.py` (canonical migration framework owner). Both are `CREATE TABLE IF NOT EXISTS` so coexistence is safe but the schema is defined twice. Resolution: delete from route layer; rely on migration framework's startup run. Routing: Impromptu A (cleanup bundled with hardening pass). |
| DEF-225 | `ibkr_auth_failure` lacks dedicated E2E auto-resolution test | Tier 3 #2 architectural review (2026-04-28) | **Status:** OPEN — Routing: Sprint 31.91 Impromptu A — Severity: LOW. Structurally covered today by Test 4 (same predicate shape: `IBKRReconnectedEvent` clears both `ibkr_disconnect` and `ibkr_auth_failure`); a dedicated test covering the `OrderFilledEvent` clearing leg would close the symmetry gap. Routing: Impromptu A (test-hygiene bundled with hardening pass). |
```

### Edit 1b — Annotate DEF-175

**Anchor:** the existing DEF-175 row in the same DEF table.

**Pre-flight grep-verify:**
```bash
grep -n "^| DEF-175 " CLAUDE.md
# Expected: 1 hit
```

**Edit shape:** in-place modification of the description column of the existing row. Find the row and APPEND the following text to the description column (preserve all existing content):

> Annotated 2026-04-28 by Tier 3 #2 disposition with two additional motivators: (a) Sprint 31.91 accumulated 6 main.py scoped exceptions across S2a/S2c.1/S2d/S5a.1/S5a.2 (× 2), indicating the lifespan/Phase-4 startup orchestration needs the same component-ownership refactor `api/server.py` does; (b) `HealthMonitor.set_order_manager()` exists at `argus/core/health.py` but is wired only by tests — production wiring deferred since S2b.2 across S5a.1/S5a.2/S5b without resolution. Both motivators land in the post-31.9-component-ownership sprint scope alongside the existing CatalystStorage / SetupQualityEngine / DynamicPositionSizer / ExperimentStore migration work.

### Verify

```bash
grep -E "^\| DEF-21[7-9] |^\| DEF-22[0-5] " CLAUDE.md | wc -l
# Expected: 9 (DEF-217 through DEF-225, except DEF-222 if it's not in the same table — verify each DEF row landed)

grep "annotated 2026-04-28 by Tier 3 #2" CLAUDE.md
# Expected: 1 hit (the DEF-175 annotation)
```

---

## Step 1.5 — Update `docs/project-knowledge.md`

The ARGUS project-knowledge document references "Workflow protocol version: 1.2.0" as if the metarepo has a single global version. The metarepo actually uses per-file versioning (verified by pre-flight investigation 2026-04-28). Update the reference.

### Edit 1.5a — Find and replace the workflow-version reference

**Anchor:** the line in `docs/project-knowledge.md` that mentions "Workflow protocol version" or "workflow-version" with reference to "1.2.0" or any other specific version.

**Pre-flight grep-verify:**
```bash
grep -nE "[Ww]orkflow.{0,20}version" docs/project-knowledge.md
# Expected: 1-3 hits; the load-bearing one mentions a specific version number
```

If the grep returns ZERO hits, the reference may have been removed by a prior edit; HALT and report.

If the grep returns hits, identify the load-bearing reference (typically in a "Tech Stack" or "Workflow" section with phrasing like "Workflow protocol version: X.Y.Z").

**Edit shape:** replace the version-specific reference with per-file pointer language. The exact existing text varies; the replacement should look like:

```markdown
**Workflow protocols:** ARGUS sprint workflow uses the `claude-workflow` metarepo (https://github.com/stevengizzi/claude-workflow). The metarepo uses per-file semantic versioning — each protocol/template/schema evolves on its own version line. Key protocols at the time of last sprint planning: `protocols/sprint-planning.md` (v1.2.0), `protocols/in-flight-triage.md` (v1.3.0), `protocols/mid-sprint-doc-sync.md` (v1.0.0, NEW 2026-04-28). See `bootstrap-index.md` in the metarepo for the canonical index. Cross-cutting amendments are tracked per-file in commit history rather than as a metarepo-wide version bump.
```

If the existing text is structurally different (e.g., a one-line bullet rather than a paragraph), adapt the replacement to match the surrounding format. The semantic content above is the load-bearing part.

### Edit 1.5b — Update any other stale workflow-version references

```bash
grep -nE "workflow.{0,5}v?1\.[0-9]\.[0-9]|workflow.{0,5}version.{0,20}1\.[0-9]" docs/project-knowledge.md
```

If hits remain after Edit 1.5a, address each one:
- If the reference is to a specific protocol's version (e.g., "in-flight-triage.md v1.2.0"), update to current version (e.g., v1.3.0 post-amendment).
- If the reference is to a global "workflow v1.2.0" framing, replace per the per-file pointer language above.

### Verify

```bash
grep -nE "[Ww]orkflow.{0,20}version" docs/project-knowledge.md
# Expected: hits exist but reference per-file versioning rather than a global version number

grep -nE "1\.2\.0" docs/project-knowledge.md
# Expected: any remaining 1.2.0 hits are now in legitimate per-protocol-version references
# (e.g., "sprint-planning.md (v1.2.0)") rather than a global "Workflow protocol version: 1.2.0" framing
```

---

## Step 2 — Update `work-journal-register.md`

This file at `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` is the authoritative record of sprint state. Mid-sprint sync updates it in place; the Work Journal conversation reads it on re-entry.

### Edit 2a — Refresh the "Last Refresh" header

**Anchor:** the `## Last Refresh` heading and the table immediately following.

**Pre-flight grep-verify:**
```bash
grep -A 8 "^## Last Refresh" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

Replace the table content with:

```markdown
| Field | Value |
|---|---|
| **Refreshed at** | 2026-04-28, post-Tier-3-#2-disposition pre-impromptu doc-sync |
| **Anchor commit** | `<HEAD after this sync's commits>` (pre-impromptu doc-sync); upstream of `75c125e` (S5b Tier 2) and the Tier 3 #2 verdict amendment |
| **Sessions complete** | 0, 1a, 1b, 1c, 2a, 2b.1, 2b.2, 2c.1, 2c.2 (+ DEF-216 hotfix), 2d, 3, 4, 5a.1, 5a.2, 5b |
| **Tier 3 reviews complete** | #1 (PROCEED), #2 (PROCEED with conditions; AMENDED 2026-04-28) |
| **Active session** | None — between sessions; **Impromptu A is next** per amended Tier 3 #2 verdict |
| **Sprint phase** | Backend SEALED post-Tier-3-#2; pre-frontend-hardening phase ACTIVE (Impromptus A+B+C land before S5c) |
| **Workflow protocol version** | 1.3.0 (mid-sprint doc-sync protocol + structural anchors); `tier-3-review.md` independently at 1.0.2 |
```

### Edit 2b — Replace the "Tier 3 #2 PHASE BOUNDARY" section

**Anchor:** the heading `## Tier 3 #2 PHASE BOUNDARY (Pre-Session-5c)`.

**Pre-flight grep-verify:**
```bash
grep -n "^## Tier 3 #2 PHASE BOUNDARY" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
# Expected: 1 hit
```

Replace the entire section (from the heading through the next `---` separator) with:

```markdown
## Tier 3 #2 — COMPLETE (Phase Boundary Resolved)

**Tier 3 #2 architectural review** completed 2026-04-28. Verdict: PROCEED with conditions (amended). Verdict artifact at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended version).

**Outcomes of Tier 3 #2:**

- Backend architecture sealed (no architectural concerns).
- DEC-388 materialization DEFERRED to sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.3.0); draft text in verdict.
- DEC-385 unchanged — remains scheduled for sprint-close write per existing plan.
- 9 new DEFs filed (DEF-217 through DEF-225), 7 routed RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c), 1 deferred (DEF-222), 1 routed via Session 5c (DEF-220).
- DEF-175 annotated with main.py + set_order_manager motivators.
- Workflow metarepo bumped to v1.3.0 (mid-sprint doc-sync protocol + structural-anchor amendment).

**Conditions for Session 5c entry (NEW — replaces prior "NONE"):**

- Impromptu A landed CLEAR (DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225 RESOLVED-IN-SPRINT).
- Impromptu B landed CLEAR (DEF-221 RESOLVED-IN-SPRINT; end-to-end Databento auto-resolution validated with the DEF-217 fix).

DEF-220 disposition is folded INTO Session 5c (not a precondition for entry).

**Pre-impromptu doc-sync manifest** at `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md` is the mechanical handoff to sprint-close per `protocols/mid-sprint-doc-sync.md` v1.0.0.
```

### Edit 2c — Update the DECs section

**Anchor:** the heading `## DECs` and the tables following.

**Pre-flight grep-verify:**
```bash
grep -A 30 "^## DECs" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md | head -40
```

Update the "Reserved (not yet materialized)" table row for DEC-388 to read:

```markdown
| DEC-388 | Alert observability architecture (resolves DEF-014). Backend complete at S5b; hardening complete after Impromptus A+B+C; frontend complete at S5e. Cross-references DEFs being resolved IN-SPRINT (DEF-217/218/219/220/221/223/224/225) plus deferred DEF-222 + DEF-014. | 5a.1+5a.2+5b + Impromptus A+B+C + 5c+5d+5e | **Sprint-close (Pattern B per `protocols/mid-sprint-doc-sync.md` v1.3.0)** — was Tier 3 #2; deferred per Tier 3 #2 amended verdict 2026-04-28 |
```

The DEC-385 row remains unchanged (was already scheduled for sprint-close).

### Edit 2d — Add 9 new DEF rows

**Anchor:** the `## DEFs` heading, then the `### Filed during Sprint 31.91` subsection's table.

**Pre-flight grep-verify:**
```bash
grep -n "^### Filed during Sprint 31.91" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

After the existing DEF-216 row in this table, append:

```markdown
| **DEF-217** | Tier 3 #2 Concern A | Databento dead-feed alert_type producer/consumer string mismatch (HIGH severity correctness defect; MUST land before live) | OPEN — Impromptu A | Sprint 31.91 Impromptu A |
| **DEF-218** | Tier 3 #2 Concern D | `eod_residual_shorts` + `eod_flatten_failed` missing from policy table | OPEN — Impromptu A | Sprint 31.91 Impromptu A |
| **DEF-219** | Tier 3 #2 Concern B | Policy table exhaustiveness regression guard not test-enforced | OPEN — Impromptu A | Sprint 31.91 Impromptu A |
| **DEF-220** | Tier 3 #2 Concern C / Item 4 | `acknowledgment_required_severities` field has no consumer (wire vs remove disposition) | OPEN — Session 5c | Sprint 31.91 Session 5c |
| **DEF-221** | Tier 3 #2 Concern F / Item 7 | `DatabentoHeartbeatEvent` producer wiring (data-layer health poller) | OPEN — Impromptu B | Sprint 31.91 Impromptu B |
| **DEF-222** | Tier 3 #2 Item 2 | Predicate-handler subscribe-before-rehydrate audit when producers land | DEFERRED — sprint-gating | Producer-wiring sprint TBD |
| **DEF-223** | Tier 3 #2 Item 8 | Migration framework adoption sweep across 7 other separate DBs | OPEN — Impromptu C | Sprint 31.91 Impromptu C |
| **DEF-224** | Tier 3 #2 Concern E | Duplicate `_AUDIT_DDL` between routes layer and migration framework | OPEN — Impromptu A | Sprint 31.91 Impromptu A |
| **DEF-225** | Tier 3 #2 Item 1 | `ibkr_auth_failure` dedicated E2E auto-resolution test | OPEN — Impromptu A | Sprint 31.91 Impromptu A |
```

### Edit 2e — Update the "Session Order" section

**Anchor:** the heading `## Session Order (Sequential — Strict)` and the numbered list following.

**Pre-flight grep-verify:**
```bash
grep -n "^## Session Order" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

Replace the section content (from heading through the next `---`) with:

```markdown
## Session Order (Sequential — Strict, REVISED post-Tier-3-#2)

1. ✅ Session 0 — CLEAR, commit `9b7246c`
2. ✅ Session 1a — CLEAR, commit `b25b419`
3. ✅ Session 1b — CLEAR, commit `6009397`
4. ✅ Session 1c — CLEAR, commit `49beae2`
5. ✅ **Tier 3 #1** — PROCEED, verdict commit `df48e31`. **DEC-386 materialized.**
6. ✅ Session 2a — CLEAR, commit `813fc3c`
7. ✅ Session 2b.1 — CLEAR, commit `4119608`
8. ✅ Session 2b.2 — CLEAR, commit `a6846c6`
9. ✅ Session 2c.1 — CLEAR, commit `0c034b3`
10. ✅ Session 2c.2 — CLEAR, commit `24320e5`
11. ✅ Impromptu hotfix DEF-216 — CLEAR, commit `c36a30c`
12. ✅ Session 2d — CLEAR, commit `93f56cd`. **DEC-385 materialized in code (write deferred to sprint-close).**
13. ✅ Session 3 — CLEAR, commit `a11c001`. **DEF-158 RESOLVED.**
14. ✅ Session 4 — CLEAR, barrier `da325a0`. **DEF-204 falsifiably validated.**
15. ✅ Session 5a.1 — CLEAR, commit `0236e27`. **DEF-213 + DEF-214 RESOLVED.**
16. ✅ Session 5a.2 — CLEAR, commit `9475d91`.
17. ✅ Session 5b — CLEAR_WITH_NOTES, commit `b324707`. **DEF-014 producer side RESOLVED; backend SEALED.**
18. ✅ **Tier 3 #2** — PROCEED with conditions (amended), verdict commit `<this sync's verdict-amendment commit>`. **9 new DEFs filed, 7 routed in-sprint.**
19. ✅ **Pre-impromptu doc-sync** — this commit; manifest at `pre-impromptu-doc-sync-manifest.md`.
20. ⏳ **Impromptu A** (alert observability hardening: DEF-217 + DEF-218 + DEF-219 + DEF-224 + DEF-225) — Tier 2 inline. Impl prompt: `sprint-31.91-impromptu-a-alert-hardening-impl.md`.
21. ⏳ **Impromptu B** (Databento heartbeat producer + DEF-217 end-to-end validation: DEF-221) — Tier 2 inline. Impl prompt: `sprint-31.91-impromptu-b-databento-heartbeat-impl.md`. **CONDITION: Impromptu A landed CLEAR.**
22. ⏳ **Session 5c** (`useAlerts` hook + Dashboard banner + DEF-220 disposition) — Tier 2 inline. Impl prompt: `sprint-31.91-session-5c-impl.md` (amended). **CONDITION: Impromptus A and B landed CLEAR.**
23. ⏳ **Impromptu C** (migration framework adoption sweep: DEF-223) — Tier 2 inline. Impl prompt: `sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`.
24. ⏳ Session 5d (toast + acknowledgment UI flow) — unchanged.
25. ⏳ Session 5e (Observatory alerts panel + cross-page integration) — unchanged. **DEF-014 closes here.**
26. ⏳ Sprint-close doc-sync — reads `pre-impromptu-doc-sync-manifest.md` per `protocols/mid-sprint-doc-sync.md` v1.0.0; writes DEC-385 + DEC-388; transitions all RESOLVED-IN-SPRINT DEFs.
```

### Edit 2f — Update the "Carry-Forward Watchlist" section

**Anchor:** the heading `## Carry-Forward Watchlist (Active)`.

**Pre-flight grep-verify:**
```bash
grep -n "^## Carry-Forward Watchlist" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
```

In the table, perform these in-place changes to existing rows:

- The "Tier 3 #2 architectural review" row: change Status to "✅ COMPLETE 2026-04-28; Lands in: pre-impromptu doc-sync (this commit)".
- Banner mount + Toast mount + alerts/{id}/audit endpoint rows: unchanged (still pending S5c-5e).

Then APPEND these new rows (replacing the rows that previously listed these as "Future" or "Watch"):

```markdown
| **DEF-217** Databento alert_type mismatch fix + end-to-end auto-resolution validation | OPEN — bundled in Impromptu A + Impromptu B | Sprint 31.91 in-sprint resolution |
| **DEF-218** EOD policy table additions | OPEN — Impromptu A | Sprint 31.91 in-sprint resolution |
| **DEF-219** Policy table exhaustiveness regression guard | OPEN — Impromptu A | Sprint 31.91 in-sprint resolution |
| **DEF-220** `acknowledgment_required_severities` disposition | OPEN — Session 5c | Sprint 31.91 in-sprint resolution |
| **DEF-221** `DatabentoHeartbeatEvent` producer wiring | OPEN — Impromptu B | Sprint 31.91 in-sprint resolution |
| **DEF-222** Predicate-handler subscribe-before-rehydrate audit | DEFERRED — gated on future producers | Producer-wiring sprint TBD |
| **DEF-223** Migration framework adoption sweep | OPEN — Impromptu C | Sprint 31.91 in-sprint resolution |
| **DEF-224** Duplicate `_AUDIT_DDL` cleanup | OPEN — Impromptu A | Sprint 31.91 in-sprint resolution |
| **DEF-225** `ibkr_auth_failure` dedicated E2E test | OPEN — Impromptu A | Sprint 31.91 in-sprint resolution |
| Workflow metarepo amendment v1.2.0 → v1.3.0 | ✅ COMPLETE 2026-04-28 | claude-workflow repo (separate flow) |
```

REMOVE rows that are now obsolete (the items they tracked are resolved or superseded by the new entries above):

- Any row mentioning `DatabentoHeartbeatEvent` producer wiring as DEFERRED → replaced by DEF-221 row above.
- Any row mentioning predicate-handler subscribe-before-rehydrate as DESIGN/Future → replaced by DEF-222 row above.
- Any row mentioning migration framework adoption as OPPORTUNISTIC → replaced by DEF-223 row above.
- Any row mentioning duplicate `_AUDIT_DDL` cleanup as LOW (cleanup) → replaced by DEF-224 row above.
- Any row mentioning `ibkr_auth_failure` dedicated E2E as LOW → replaced by DEF-225 row above.
- Any row mentioning `acknowledgment_required_severities` gate consumer wiring as DESIGN → replaced by DEF-220 row above.
- Any row mentioning compose policy with eod_residual/eod_flatten emitter pair as DESIGN → replaced by DEF-218 row above.

### Verify

```bash
grep -c "^| .DEF-21[7-9]\|^| .DEF-22[0-5]" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
# Expected: 18 (9 in DEFs table + 9 in carry-forward watchlist)

grep "Pattern B" docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
# Expected: 1+ hits (DEC-388 deferral reasoning)

grep "Impromptu A\|Impromptu B\|Impromptu C" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md | wc -l
# Expected: at least 12+ hits across session order, DEFs, watchlist
```

---

## Step 3 — Amend `sprint-spec.md`

### Edit 3a — Extend the D9b auto-resolution policy table

**Anchor:** in `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md`, the heading `#### D9b — WebSocket fan-out + persistence + auto-resolution policy + retention (Session 5a.2)` and the auto-resolution policy table within it.

**Pre-flight grep-verify:**
```bash
grep -n "^#### D9b" docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
grep -A 15 "Auto-resolution policy table" \
  docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md | head -20
```

Add two new rows to the policy table (extending from 8 alert types to 10), inserted after the existing `phantom_short_startup_engaged` row:

```markdown
| `eod_residual_shorts` | NEVER auto-resolves (forensic clarity for EOD-bounded short residue) | **Yes** (ack required) |
| `eod_flatten_failed` | NEVER auto-resolves (failed flatten requires operator attention) | **Yes** (ack required) |
```

Add a paragraph immediately after the table:

> **Note (added 2026-04-28 by Tier 3 #2 doc-sync):** the `eod_residual_shorts` + `eod_flatten_failed` rows reflect resolution of DEF-218 by Impromptu A. Until Impromptu A lands, these alert types are emitted by `argus/execution/order_manager.py` but lack policy-table entries. The exhaustiveness regression guard (DEF-219, also Impromptu A) ensures this kind of producer/consumer drift is caught at test time going forward.

### Edit 3b — Add D15 (Databento heartbeat producer) deliverable

**Anchor:** the heading `#### D14 — DEF-014 closure documentation (sprint-close, doc-sync)` (the last existing D-deliverable).

**Pre-flight grep-verify:**
```bash
grep -n "^#### D14" docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
```

After the D14 section content (and before the next `---` or `## Acceptance Criteria` heading), insert:

```markdown
#### D15 — Databento heartbeat producer + DEF-217 end-to-end validation (Impromptu B)

**Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition; resolves DEF-221 + validates DEF-217 fix end-to-end.

**Producer wiring:** add a periodic heartbeat-publishing task to `argus/data/databento_data_service.py` that publishes `DatabentoHeartbeatEvent(provider="databento")` when the data feed is healthy. The task fires on a configurable interval (default: every 30 seconds during market hours; idle when feed is in dead-feed reconnect-loop state). Configuration field added to `DatabentoConfig`: `heartbeat_publish_interval_seconds: float = 30.0`.

**Integration:** the existing dead-feed reconnect loop suppresses heartbeat emission while reconnecting; on successful reconnect, the heartbeat task resumes (giving the `databento_dead_feed` predicate's "3 consecutive healthy heartbeats" condition a path to fire).

**End-to-end validation tests** (in `tests/integration/test_alert_pipeline_e2e.py`, NEW class `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer`):
- Drive Databento feed into dead-feed state via the production `databento_data_service` reconnect-loop.
- Assert the production emitter publishes `SystemAlertEvent(alert_type="databento_dead_feed")` (post-DEF-217 fix).
- Drive feed recovery; assert 3 heartbeats fire; assert auto-resolution per policy table.
- This is the FIRST test in the suite that exercises the production Databento alert chain end-to-end without fabricating the SystemAlertEvent directly.

**Coupling note:** Impromptu B depends on Impromptu A having landed (DEF-217 fix; the validation test assumes the production emitter publishes `databento_dead_feed`, not `max_retries_exceeded`).

#### D16 — Migration framework adoption sweep (Impromptu C)

**Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition; resolves DEF-223.

**Scope:** wrap the existing schema DDL of the 7 ARGUS SQLite DBs other than `operations.db` into v1 Migration objects under the migration framework introduced by Session 5a.2:

- `data/catalyst.db` → new `argus/data/migrations/catalyst.py`
- `data/evaluation.db` → new `argus/data/migrations/evaluation.py`
- `data/regime_history.db` → new `argus/data/migrations/regime_history.py`
- `data/learning.db` → new `argus/data/migrations/learning.py`
- `data/vix_landscape.db` → new `argus/data/migrations/vix_landscape.py`
- `data/counterfactual.db` → new `argus/data/migrations/counterfactual.py`
- `data/experiments.db` → new `argus/data/migrations/experiments.py`

Each per-DB module follows the `argus/data/migrations/operations.py` pattern: `SCHEMA_NAME` constant, `_migration_001_up` body that wraps existing DDL, `_migration_001_down` advisory inverse, `MIGRATIONS: list[Migration]`. Each module's existing service code calls `apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)` at startup before any other DDL operation.

**Per-DB tests:** each new migration module gets a corresponding `tests/data/migrations/test_<schema_name>.py` covering: (a) v1 idempotence, (b) `schema_version` row present after apply, (c) existing-DB-without-framework still works (CREATE TABLE IF NOT EXISTS pattern preserves existing data).

**Mechanical scope:** estimated ~200-300 LOC across 7 module files + 7 test files. Bounded refactor; no behavior changes to existing DBs. The architectural value is consistency — future schema changes to any of the 7 DBs adopt the migration framework rather than ad-hoc DDL.
```

### Edit 3c — Add AC blocks for D15 and D16

**Anchor:** the heading `## Acceptance Criteria` (or wherever AC blocks live in the spec).

**Pre-flight grep-verify:**
```bash
grep -n "^#### AC for D14" docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
```

After the AC for D14 block, insert:

```markdown
#### AC for D15 — Databento heartbeat producer (Impromptu B)

- [ ] `DatabentoConfig.heartbeat_publish_interval_seconds` field present with default 30.0 and Pydantic constraints (gt=0, le=300).
- [ ] Heartbeat task spawned by `databento_data_service` start; cancelled by stop.
- [ ] Heartbeat suppressed during reconnect-loop; resumes on successful reconnect.
- [ ] `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` E2E test green (drives production emitter, NOT fabricated event).
- [ ] All existing Databento tests still pass (no regression).
- [ ] DEF-221 RESOLVED status; DEF-217 end-to-end validation confirmed.

#### AC for D16 — Migration framework adoption sweep (Impromptu C)

- [ ] 7 new migration modules under `argus/data/migrations/`: catalyst, evaluation, regime_history, learning, vix_landscape, counterfactual, experiments.
- [ ] Each module follows the `operations.py` pattern (SCHEMA_NAME, _migration_001_up, _migration_001_down, MIGRATIONS list).
- [ ] Each owning service calls `apply_migrations` at startup before other DDL.
- [ ] 7 corresponding test files; all green.
- [ ] Existing service tests for each DB still pass (no behavior regression).
- [ ] DEF-223 RESOLVED status.
```

### Verify

```bash
grep "^#### D15\|^#### D16\|^#### AC for D15\|^#### AC for D16" \
  docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
# Expected: 4 hits

grep "eod_residual_shorts\|eod_flatten_failed" \
  docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
# Expected: at least 4 hits (table rows + Note paragraph + AC references)
```

---

## Step 4 — CREATE Impromptu A impl prompt

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md`

Create with the following content **verbatim**:

```markdown
# Sprint 31.91 — Impromptu A Implementation Prompt: Alert Observability Hardening

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Tier 3 #2 verdict and Session 5c.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-217 (HIGH) + DEF-218 (MEDIUM) + DEF-219 (MEDIUM) + DEF-224 (LOW) + DEF-225 (LOW).
> **Tier 2 review:** inline within this implementing session.

## Pre-Flight

Before making any edits, run all grep-verify commands listed in "Files to Modify" below. Report any drift in the close-out under RULE-038. If any anchor cannot be located, HALT and request operator disposition.

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Concerns A, B, D, E + Item 1).
- `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md` (latest state).
- `argus/core/alert_auto_resolution.py` (in full — the policy table is the central artifact).
- `argus/data/databento_data_service.py` (in full — DEF-217 fix site).
- `argus/api/routes/alerts.py` (DEF-224 cleanup site).
- `tests/integration/test_alert_pipeline_e2e.py` (DEF-225 test addition site; existing test patterns).
- `tests/api/test_alerts_5a2.py` (existing policy-table test patterns).

## Scope

Five items, all touching the alert observability backend that Tier 3 #2 just sealed. Bundled into one impromptu because they share file context.

### Requirement 1 — DEF-217: Fix Databento alert_type string mismatch

**Anchor:** in `argus/data/databento_data_service.py`, the production `SystemAlertEvent` construction with `alert_type="max_retries_exceeded"`.

**Pre-flight grep-verify:**
```bash
grep -n 'alert_type="max_retries_exceeded"' argus/data/databento_data_service.py
# Expected: 1 hit (the dead-feed emitter)

grep -n 'alert_type="databento_dead_feed"' argus/core/alert_auto_resolution.py
# Expected: 1 hit (the policy table entry)
```

**Edit shape:** replace the literal string `"max_retries_exceeded"` with `"databento_dead_feed"` in the SystemAlertEvent construction.

**Justification:** the policy table at `argus/core/alert_auto_resolution.py` keys on `databento_dead_feed`; the spec D9b auto-resolution policy table also says `databento_dead_feed`. The `max_retries_exceeded` string is a pre-Sprint-31.91 emitter value that was missed during S5a.1's metadata migration. This fix aligns the producer string with the consumer policy.

### Requirement 2 — DEF-218: Add eod_residual_shorts + eod_flatten_failed to policy table

**Anchor:** in `argus/core/alert_auto_resolution.py`, the `build_policy_table` function's returned dictionary.

**Pre-flight grep-verify:**
```bash
grep -n "def build_policy_table" argus/core/alert_auto_resolution.py
grep -n '"phantom_short_startup_engaged":' argus/core/alert_auto_resolution.py
# Expected: 1 hit each
```

**Edit shape:** add two new `PolicyEntry` rows to the returned dict, after the `phantom_short_startup_engaged` entry. Both use `NEVER_AUTO_RESOLVE` predicate and `operator_ack_required=True`.

```python
        "eod_residual_shorts": PolicyEntry(
            alert_type="eod_residual_shorts",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. EOD-bounded "
                "short residue (Sprint 30 deferred residue); operator "
                "should review before next session."
            ),
        ),
        "eod_flatten_failed": PolicyEntry(
            alert_type="eod_flatten_failed",
            consumes_event_types=(),
            predicate=NEVER_AUTO_RESOLVE,
            operator_ack_required=True,
            description=(
                "NEVER auto-resolves; operator ack required. Failed EOD "
                "flatten — positions remain at session close, requires "
                "operator attention before next session."
            ),
        ),
```

### Requirement 3 — DEF-219: Add policy-table exhaustiveness regression guard

**New file:** `tests/api/test_policy_table_exhaustiveness.py`

The test scans production code (`argus/`) for `SystemAlertEvent(alert_type=<literal>)` and `SystemAlertEvent(...; alert_type=<literal>)` constructions, extracts the literal string values, and asserts each is a key in `build_policy_table(...)`.

**Implementation approach:** use Python's `ast` module to parse production source files and walk the AST for `Call` nodes where the func name matches `SystemAlertEvent`. For each such Call node, find the keyword argument `alert_type=` and extract the literal string value (only literal strings — `ast.Constant` nodes with `value` of type `str`). Reject computed `alert_type` values (non-literal) — the test should fail if any are encountered, with a message explaining that all alert_types must be statically resolvable.

**Test cases:**
1. `test_all_emitted_alert_types_have_policy_entries` — scans production code, builds the set of emitted alert_types, asserts each is a policy-table key.
2. `test_no_computed_alert_type_in_production` — asserts every `SystemAlertEvent(alert_type=...)` construction uses a string literal (not a variable, function call, etc.). Failure message points the maintainer at the structural-anchor amendment in `templates/implementation-prompt.md` v1.5.0.
3. `test_policy_table_has_no_orphan_entries` — the inverse direction: every policy-table key has at least one production emitter (test files excluded). This catches dead-code policy entries — which is what DEF-217 was, before the fix.

**Test scope:** scans `argus/` directory recursively, excludes `argus/core/alert_auto_resolution.py` itself (the policy table is the consumer, not a producer of its own keys), and excludes any `tests/` subdirectories.

### Requirement 4 — DEF-224: Remove duplicate _AUDIT_DDL from routes layer

**Anchor:** in `argus/api/routes/alerts.py`, the module-level `_AUDIT_DDL` string constant and the `_ensure_audit_table` helper function.

**Pre-flight grep-verify:**
```bash
grep -n "^_AUDIT_DDL\|^async def _ensure_audit_table" argus/api/routes/alerts.py
# Expected: 2 hits (the constant + the function)

grep -n "_ensure_audit_table" argus/api/routes/alerts.py
# Expected: definition + 2-3 call sites
```

**Edit shape:**
1. Delete the `_AUDIT_DDL` module constant.
2. Delete the `_ensure_audit_table` helper function.
3. Find each call site of `_ensure_audit_table(db)` and delete those lines too — the migration framework's startup `apply_migrations` call now owns the table creation.

**Verification that the framework owns it:** `argus/data/migrations/operations.py` migration v1's `_migration_001_up` includes `_ALERT_ACK_AUDIT_DDL`. This migration runs at HealthMonitor startup (before any route handler can be hit), so the table always exists by the time the routes execute.

### Requirement 5 — DEF-225: Add dedicated ibkr_auth_failure E2E test

**Anchor:** in `tests/integration/test_alert_pipeline_e2e.py`, after the existing `TestE2EIBKRDisconnectAutoResolution` class.

**Pre-flight grep-verify:**
```bash
grep -n "class TestE2EIBKRDisconnectAutoResolution" tests/integration/test_alert_pipeline_e2e.py
# Expected: 1 hit
```

**Edit shape:** add a new test class `TestE2EIBKRAuthFailureAutoResolution` with one test method exercising the `OrderFilledEvent` clearing leg of the `_ibkr_auth_success_predicate`:

```python
class TestE2EIBKRAuthFailureAutoResolution:
    """E2E test for ibkr_auth_failure auto-resolution via OrderFilledEvent.

    Closes the symmetry gap noted in S5b closeout — Test 4 covered
    the IBKRReconnectedEvent leg; this test covers the OrderFilledEvent
    leg of the same predicate. Surfaced as DEF-225 by Tier 3 #2.
    """

    async def test_ibkr_auth_failure_clears_on_order_filled(...):
        # 1. Emit SystemAlertEvent(alert_type="ibkr_auth_failure")
        # 2. Verify alert is ACTIVE via REST /alerts/active
        # 3. Verify WS push fires (alert_active)
        # 4. Publish OrderFilledEvent
        # 5. Verify alert auto-resolves (alert_auto_resolved WS push)
        # 6. Verify REST /alerts/active no longer lists it
        # 7. Verify audit_log row with audit_kind="auto_resolution"
```

Use the existing fixture pattern from `TestE2EIBKRDisconnectAutoResolution` for setup.

## Scope Boundaries (do-not-modify)

- `argus/execution/order_manager.py` — zero edits this impromptu.
- `argus/execution/ibkr_broker.py` — zero edits this impromptu.
- `argus/data/alpaca_data_service.py` — zero edits (DoD invariant from Sprint 31.91).
- `argus/main.py` — zero edits (no scoped exception this impromptu).
- The IMPROMPTU-04 fix range and OCA architecture (DEC-386) — invariant 15 still applies.

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session. The reviewer reads:
- This impl prompt.
- The diff produced.
- The new test file.
- `tier-3-review-2-verdict.md` (amended) for context.

Review focus areas:
1. DEF-217 fix is the minimal one-line change (no scope creep into other Databento territory).
2. DEF-218 policy entries follow the existing PolicyEntry shape (no novel fields).
3. DEF-219 regression guard handles edge cases (no false positives on test files; correct handling of `SystemAlertEvent` construction patterns; clear failure messages).
4. DEF-224 deletion is complete (no orphan references to `_AUDIT_DDL` or `_ensure_audit_table`).
5. DEF-225 test exercises the OrderFilledEvent leg specifically (not redundant with Test 4).

Verdict format: structured JSON per `schemas/structured-review-verdict-schema.md`.

## Definition of Done

- [ ] Requirement 1 (DEF-217 fix) landed; grep-verify post-fix confirms `databento_dead_feed` matches between emitter and policy.
- [ ] Requirement 2 (DEF-218 policy entries) landed; policy table now contains 10 entries; existing exhaustiveness test updated to match.
- [ ] Requirement 3 (DEF-219 regression guard) landed; new test file passes; running it WITHOUT requirements 1+2 in place would fail (verifying the guard actually catches drift).
- [ ] Requirement 4 (DEF-224 cleanup) landed; routes layer no longer defines DDL; routes' acknowledge calls still work via the migration framework's startup-time table creation.
- [ ] Requirement 5 (DEF-225 test) landed; new test passes; structurally distinct from Test 4 (exercises OrderFilledEvent leg, not IBKRReconnectedEvent).
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 4 (3 new tests in DEF-219 guard + 1 in DEF-225 + 0-1 in DEF-218 — the existing exhaustiveness test absorbs the 2 new policy entries).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-review.md`.

## Closeout requirements

The close-out must include the structured fields per `schemas/structured-closeout-schema.md` plus:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"` (per `protocols/mid-sprint-doc-sync.md` v1.0.0).
- DEF transitions claimed: DEF-217, DEF-218, DEF-219, DEF-224, DEF-225 → all "RESOLVED-IN-SPRINT, Impromptu A" (status transition applied at sprint-close per the manifest).
- Anchor commit SHA for the impromptu's implementation.
- Tier 3 track marker: `alert-observability` (continues from S5a.1+S5a.2+S5b).
```

(The full impromptu prompt is approximately 250 lines; the above is the substantive content. Save this verbatim.)

---

## Step 5 — CREATE Impromptu B impl prompt

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md`

Create with the following content **verbatim**:

```markdown
# Sprint 31.91 — Impromptu B Implementation Prompt: Databento Heartbeat Producer

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Impromptu A and Session 5c.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-221 (MEDIUM) + validates DEF-217 fix end-to-end.
> **Sprint-spec deliverable:** D15.
> **Tier 2 review:** inline within this implementing session.

## CONDITION FOR ENTRY

**Impromptu A must have landed CLEAR.** This impromptu's end-to-end validation test depends on DEF-217's fix (the production Databento emitter publishing `databento_dead_feed`, not `max_retries_exceeded`). If Impromptu A has not landed CLEAR per its Tier 2 review, HALT.

Pre-flight verification:
```bash
grep "DEF-217" docs/sprints/sprint-31.91-reconciliation-drift/impromptu-a-closeout.md
# Expected: hits in resolved-DEFs section

grep 'alert_type="databento_dead_feed"' argus/data/databento_data_service.py
# Expected: 1 hit (the post-Impromptu-A state)
```

If either check fails, HALT and route back to Impromptu A.

## Pre-Flight

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Concern F + Item 7).
- `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` (D15 deliverable + AC).
- `argus/data/databento_data_service.py` (in full — both the dead-feed reconnect loop AND the new heartbeat task site).
- `argus/core/events.py` (`DatabentoHeartbeatEvent` definition).
- `argus/core/alert_auto_resolution.py` (`_databento_heartbeat_predicate`).
- `tests/integration/test_alert_pipeline_e2e.py` (existing E2E patterns; the new test class lives here).
- `tests/data/test_databento_data_service.py` (existing data-service tests).

## Scope

Two items: producer wiring + end-to-end validation test.

### Requirement 1 — DEF-221: Add heartbeat-publishing task

**Config addition.** In `argus/core/config.py`, find the `DatabentoConfig` Pydantic model (anchor: `class DatabentoConfig`). Add a new field:

```python
heartbeat_publish_interval_seconds: float = Field(
    default=30.0,
    gt=0.0,
    le=300.0,
    description=(
        "Interval at which DatabentoDataService publishes "
        "DatabentoHeartbeatEvent when the feed is healthy. "
        "Suppressed during reconnect loop. "
        "Sprint 31.91 Impromptu B (DEF-221)."
    ),
)
```

**Producer wiring.** In `argus/data/databento_data_service.py`:

1. Add a private async method `_heartbeat_publish_loop` that runs while the feed is in HEALTHY state and publishes `DatabentoHeartbeatEvent(provider="databento")` every `heartbeat_publish_interval_seconds`. Suppressed during reconnect-loop state.

2. Spawn the task in the service's `start()` method (`asyncio.create_task(self._heartbeat_publish_loop())`); cancel in `stop()` with `CancelledError` suppression.

3. The task must check feed health via the service's existing health-state attribute (find by grep: `grep -n "_feed_healthy\|_is_healthy\|_state" argus/data/databento_data_service.py`); only publish when healthy.

**Pre-flight grep-verify for service health attribute:**
```bash
grep -nE "self\._(feed_healthy|is_healthy|state)" argus/data/databento_data_service.py
# Expected: 2-5 hits identifying the canonical health state attribute
```

If the service doesn't have a clean health-state attribute, HALT and request operator disposition — do NOT introduce a new state attribute as part of this impromptu.

### Requirement 2 — End-to-end validation test

**Anchor:** in `tests/integration/test_alert_pipeline_e2e.py`, after the existing `TestE2EDatabentoDeadFeed` class (or wherever Impromptu A's `TestE2EIBKRAuthFailureAutoResolution` was added — append at the end either way).

**New test class:** `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer`.

**Test method:** `test_databento_dead_feed_auto_resolves_via_real_heartbeats`. Steps:
1. Start `DatabentoDataService` with mocked Databento client that initially fails to connect (drives reconnect loop).
2. Drive the loop to retries-exhausted; verify production emitter publishes `SystemAlertEvent(alert_type="databento_dead_feed")` (NOT a fabricated event — this is the load-bearing assertion that DEF-217 was actually fixed).
3. Verify alert is ACTIVE via REST `/alerts/active`.
4. Mock recovery (Databento client now connects successfully); verify `_feed_healthy` flips to True.
5. Wait for ≥3 heartbeat intervals; verify `DatabentoHeartbeatEvent` published 3+ times.
6. Verify alert auto-resolves (WS push `alert_auto_resolved`; REST `/alerts/active` no longer lists; audit row `audit_kind="auto_resolution"`).

**Why this test matters:** every existing E2E test in this file fabricates `SystemAlertEvent(alert_type="...")` directly. This is the FIRST test that exercises the production Databento emitter chain end-to-end. It validates that DEF-217 + DEF-221 together produce a working auto-resolution pipeline.

## Scope Boundaries (do-not-modify)

- `argus/data/alpaca_data_service.py` — zero edits.
- `argus/execution/order_manager.py`, `argus/execution/ibkr_broker.py` — zero edits.
- `argus/main.py` — zero edits (the new task is owned by `DatabentoDataService.start()`, no main.py wiring needed).
- `argus/core/events.py` — `DatabentoHeartbeatEvent` already exists (S5a.2); zero edits.
- `argus/core/alert_auto_resolution.py` — `_databento_heartbeat_predicate` already exists; zero edits.
- The migration framework — zero edits (no schema changes).

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session.

Review focus areas:
1. The heartbeat task properly suppresses during reconnect-loop state (verify via test that drives the dead-feed state and confirms zero heartbeat publications during the reconnect window).
2. Task is properly cancelled in `stop()` — no orphan task leakage on service stop.
3. The end-to-end test is genuinely end-to-end (drives production code, NOT fabricated events).
4. Heartbeat interval is configurable (test patches the config to a small value for fast test execution).
5. No regression in existing Databento data-service tests.

Verdict format: structured JSON per `schemas/structured-review-verdict-schema.md`.

## Definition of Done

- [ ] `DatabentoConfig.heartbeat_publish_interval_seconds` field added with correct constraints.
- [ ] `_heartbeat_publish_loop` task implemented; spawned in `start()`; cancelled in `stop()`.
- [ ] Task suppression during reconnect-loop state implemented and tested.
- [ ] `TestE2EDatabentoDeadFeedAutoResolveWithRealProducer` test green; drives production emitter end-to-end.
- [ ] Existing Databento data-service tests still pass.
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 1 (the new E2E test).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-b-review.md`.

## Closeout requirements

Per `protocols/mid-sprint-doc-sync.md` v1.0.0 + the manifest pattern:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"`.
- DEF transitions claimed: DEF-221 → "RESOLVED-IN-SPRINT, Impromptu B".
- DEF cross-validation: DEF-217 end-to-end validation now confirmed (close-out should explicitly state "Impromptu B's TestE2EDatabentoDeadFeedAutoResolveWithRealProducer validates DEF-217 fix in production code path").
- Anchor commit SHA.
- Tier 3 track marker: `alert-observability`.
```

---

## Step 6 — CREATE Impromptu C impl prompt

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-c-migration-framework-sweep-impl.md`

Create with the following content **verbatim**:

```markdown
# Sprint 31.91 — Impromptu C Implementation Prompt: Migration Framework Adoption Sweep

> **Workflow contract:** authored under `templates/implementation-prompt.md` v1.5.0 (structural anchors); references `protocols/mid-sprint-doc-sync.md` v1.0.0 for closeout discipline.
> **Sprint:** 31.91 reconciliation-drift.
> **Position in track:** between Session 5c and Session 5d.
> **Triggered by:** Tier 3 #2 amended verdict 2026-04-28 disposition.
> **Resolves:** DEF-223 (LOW).
> **Sprint-spec deliverable:** D16.
> **Tier 2 review:** inline within this implementing session.

## CONDITION FOR ENTRY

Sessions through Session 5c must have landed CLEAR. (No specific dependency on Session 5c's content; the dependency is sequential — Impromptu C runs after S5c per the new session order.)

## Pre-Flight

Read the following inputs in full:
- This impl prompt.
- `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md` (amended; Item 8 + Concern not separately filed but sprint-spec D16).
- `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` (D16 deliverable + AC).
- `argus/data/migrations/__init__.py`, `framework.py`, `operations.py` — the existing reference pattern.
- For each of the 7 target DBs, the owning service file's existing DDL (find by grep, see Requirement details).

## Scope

Wrap each of the 7 ARGUS SQLite DBs (other than `operations.db`) in a v1 Migration object under the migration framework. Mechanical, low-risk; the architectural value is consistency.

The 7 target DBs:
1. `data/catalyst.db` — owned by `argus/intelligence/catalyst_storage.py`
2. `data/evaluation.db` — owned by `argus/evaluation/evaluation_event_store.py` (or similar; verify by grep)
3. `data/regime_history.db` — owned by `argus/regime/regime_history_store.py` (or similar; verify by grep)
4. `data/learning.db` — owned by `argus/learning/learning_service.py` (or similar; verify by grep)
5. `data/vix_landscape.db` — owned by `argus/regime/vix_data_service.py` (or similar; verify by grep)
6. `data/counterfactual.db` — owned by `argus/counterfactual/counterfactual_store.py` (or similar; verify by grep)
7. `data/experiments.db` — owned by `argus/experiments/experiment_store.py` (or similar; verify by grep)

**Pre-flight grep-verify (for each DB, identify owning service):**
```bash
for db in catalyst evaluation regime_history learning vix_landscape counterfactual experiments; do
    echo "=== $db.db ==="
    grep -rln "data/${db}\.db\|${db}\.db" argus/ --include="*.py" | head -3
done
```

If any DB cannot be associated with a clear owning service, HALT and request operator disposition.

### Requirement 1 — Per-DB migration modules

For each of the 7 DBs, create a new module at `argus/data/migrations/<schema_name>.py` following the `operations.py` template:

```python
"""Migration registry for ``data/<schema_name>.db`` (Sprint 31.91 Impromptu C).

The ``<schema_name>`` schema collects ARGUS's <description> tables.

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "<schema_name>"

# Wrap the existing service module's DDL constants here.
# (Copy verbatim from the owning service's DDL.)

_<SCHEMA>_TABLE_DDL = """..."""


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing <schema_name> schema."""
    await db.execute(_<SCHEMA>_TABLE_DDL)
    # ... additional tables ...


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP TABLE IF EXISTS <table_1>")
    # ... additional drops in reverse order ...


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: <schema_name> schema (existing "
            "tables wrapped into migration framework)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
```

### Requirement 2 — Wire each owning service to call apply_migrations

For each owning service, find the existing initialization code that creates tables (typically in an `_initialize_schema` or `_ensure_schema` method, or inline in `__init__` / `start`). The structural anchor is the first DDL execution in the owning service.

**Replace** the existing DDL execution with a call to `apply_migrations`:

```python
from argus.data.migrations import apply_migrations
from argus.data.migrations.<schema_name> import SCHEMA_NAME, MIGRATIONS

# ... in __init__ or start ...
async with aiosqlite.connect(self._db_path) as db:
    await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
```

The existing `CREATE TABLE IF NOT EXISTS` pattern preserves existing data, so applying v1 to a DB that pre-dates the framework is safe.

### Requirement 3 — Per-DB tests

For each of the 7 DBs, create a corresponding test at `tests/data/migrations/test_<schema_name>.py` following the existing test pattern in `tests/api/test_alerts_5a2.py` (the `test_apply_migrations_is_idempotent`, `test_schema_version_records_v1` shape).

Test cases per DB:
1. `test_<schema_name>_v1_creates_expected_tables` — apply v1; verify each table exists via `sqlite_master` query.
2. `test_<schema_name>_v1_is_idempotent` — apply v1 twice; verify no errors and `schema_version` row exists once.
3. `test_<schema_name>_v1_preserves_existing_data` — pre-create a row in the schema's main table; apply v1; verify the row still exists.
4. `test_<schema_name>_schema_version_recorded` — apply v1; verify `schema_version` table contains a row with `schema_name=<schema_name>` and `version=1`.

## Scope Boundaries (do-not-modify)

- `argus/data/migrations/__init__.py`, `framework.py`, `operations.py` — zero edits (the framework is now stable).
- `argus/main.py`, `argus/api/server.py` — zero edits this impromptu (services own their own migration calls).
- All non-data-storage code paths — zero edits.

## Behavioral invariants

After Impromptu C:
- All 8 ARGUS SQLite DBs are managed by the migration framework.
- Each owning service's `start()` or `__init__` calls `apply_migrations` before any other DDL.
- `schema_version` table exists in each DB with one row per DB.
- All existing service-level tests pass without modification (no behavior change).

## Tier 2 Review (inline)

After implementation, spawn a Tier 2 review subagent within this same Claude Code session.

Review focus areas:
1. Each per-DB migration module follows the operations.py template exactly (no novel patterns).
2. Each owning service's call site is in the right place (before any other DDL; idempotent on multi-start).
3. All existing service tests still pass (no regression).
4. The 7 new test files correctly cover the 4 invariants per DB.
5. Pre-existing data is preserved on framework adoption (test 3 per DB).

Verdict format: structured JSON.

## Definition of Done

- [ ] 7 new migration modules created under `argus/data/migrations/`.
- [ ] 7 owning services modified to call `apply_migrations` at startup.
- [ ] 7 new test files; all tests green.
- [ ] All existing service tests pass (no regression).
- [ ] Full test suite passes: `python -m pytest --ignore=tests/test_main.py -n auto -q`.
- [ ] Test count increases by approximately 28 (4 tests × 7 DBs).
- [ ] Tier 2 review verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-closeout.md`.
- [ ] Tier 2 review at `docs/sprints/sprint-31.91-reconciliation-drift/impromptu-c-review.md`.

## Closeout requirements

Per `protocols/mid-sprint-doc-sync.md` v1.0.0 + the manifest pattern:
- `mid_sprint_doc_sync_ref: "docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md"`.
- DEF transitions claimed: DEF-223 → "RESOLVED-IN-SPRINT, Impromptu C".
- Architecture catalog note: migration framework now spans all 8 ARGUS SQLite DBs (architecture.md update at sprint-close).
- Anchor commit SHA.
- Tier 3 track marker: `migration-framework-adoption` (new track marker for sprint-close attribution).
```

---

## Step 7 — Amend Session 5c impl prompt

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md`

**Anchor:** look for the existing Session 5c impl prompt's "Definition of Done" section or its scope/requirements section.

**Pre-flight grep-verify:**
```bash
ls docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md
grep -n "## Scope\|## Requirements\|## Definition of Done" \
  docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md
```

**Edit shape:** add a new requirement section (titled "Requirement N — DEF-220 disposition") to the existing Session 5c impl prompt. The exact insertion point is "after the last existing Requirement section, before the Definition of Done section." Verify the section structure first.

The new section content:

```markdown
### Requirement N — DEF-220 disposition: `acknowledgment_required_severities` field

**Anchor:** in `argus/core/config.py`, the `AlertsConfig` Pydantic model and its `acknowledgment_required_severities` field.

**Pre-flight grep-verify:**
```bash
grep -n "acknowledgment_required_severities" argus/core/config.py
# Expected: 1 hit (the field definition)

grep -rn "acknowledgment_required_severities" argus/ --include="*.py" | grep -v config.py
# Expected: 0 hits — the field has no consumers (this is the DEF)
```

**Disposition decision:** the recommendation per Tier 3 #2 is REMOVAL (the per-alert-type `PolicyEntry.operator_ack_required` already encodes the equivalent control). However, this session's frontend implementation may surface a use case for the field. Decide one of:

**Option A — Remove the field** (recommended if no frontend use case surfaces):
1. Delete the field from `AlertsConfig` in `argus/core/config.py`.
2. Update tests that reference the field to use `PolicyEntry.operator_ack_required` instead.
3. Search for any docs/sprint-spec references to the field and update accordingly.

**Option B — Wire the field** (only if Session 5c's frontend introduces a need):
1. Add a consumer in the route layer that gates auto-archive based on severity match against the field.
2. Add tests covering the gate behavior.
3. Document the composition with `PolicyEntry.operator_ack_required` (which takes precedence).

**Decision documentation:** Session 5c's close-out must explicitly state which option was chosen and why.

**DEF transition:** DEF-220 → "RESOLVED-IN-SPRINT, Session 5c (Option A: removal)" or "RESOLVED-IN-SPRINT, Session 5c (Option B: wired at <consumer site>)".
```

Also amend the Definition of Done section to add:

- [ ] DEF-220 disposition (Option A or Option B) decided and applied; close-out documents the choice.

And the Closeout Requirements section to add:
- DEF transition claimed: DEF-220 → "RESOLVED-IN-SPRINT, Session 5c".

### Verify

```bash
grep "DEF-220" docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md
# Expected: 3+ hits (the new requirement section + DoD line + closeout requirements)
```

---

## Step 8 — CREATE the pre-impromptu doc-sync manifest

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md`

This is the mechanical handoff to sprint-close per `protocols/mid-sprint-doc-sync.md` v1.0.0.

Create with the following content **verbatim** (substitute `<this commit's SHA>` with the actual commit SHA after committing — operator does this manually post-commit, OR the prompt can iterate after commit):

```markdown
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
```

---

## Step 9 — CREATE the work-journal handoff document

**File path:** `docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md`

This is the narrative handoff to the Work Journal conversation. Operator pastes this (or its summary section) into the Work Journal as the first message after re-entry.

Create with the following content **verbatim**:

```markdown
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
```

---

## Step 10 — Final verification

After all 9 edits land:

```bash
# 1. New files exist
ls docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-a-alert-hardening-impl.md \
   docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-b-databento-heartbeat-impl.md \
   docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-impromptu-c-migration-framework-sweep-impl.md \
   docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md \
   docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md
# Expected: 5 files, all exist

# 2. CLAUDE.md DEF rows (10 total: DEF-216 backfill + DEF-217 through DEF-225)
grep -cE "^\| DEF-216 |^\| DEF-21[7-9] |^\| DEF-22[0-5] " CLAUDE.md
# Expected: 10

# 2a. Structured Status prefix present in new rows (4-column schema, prefix in Context column)
grep -E "^\| DEF-21[7-9] |^\| DEF-22[0-5] " CLAUDE.md | grep -c "\*\*Status:\*\*"
# Expected: 9 (the 9 new Tier 3 #2 rows; DEF-216 backfill uses RESOLVED-IN-SPRINT prefix)

# 2b. DEF-216 backfill landed with RESOLVED status
grep -E "^\| DEF-216 " CLAUDE.md | grep -c "RESOLVED-IN-SPRINT"
# Expected: 1

# 3. work-journal-register.md updates
grep "Tier 3 #2 — COMPLETE" docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
grep "Pattern B" docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md
grep "Impromptu A\|Impromptu B\|Impromptu C" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-register.md | wc -l
# Expected: 1+ hits each, total 12+ Impromptu mentions

# 4. sprint-spec.md updates
grep "^#### D15\|^#### D16" docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md
# Expected: 2 hits

# 5. session-5c-impl.md amendment
grep "DEF-220" docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5c-impl.md
# Expected: 3+ hits

# 6. Manifest carries the per-file protocol-version marker
grep "protocol-version: protocols/mid-sprint-doc-sync.md v1.0.0" docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md
# Expected: 1 hit (the manifest's protocol-version marker per Patch 1f)

# 7. Handoff references the right artifacts
grep "tier-3-review-2-verdict\|pre-impromptu-doc-sync-manifest" \
  docs/sprints/sprint-31.91-reconciliation-drift/work-journal-handoff.md
# Expected: 2+ hits

# 8. project-knowledge.md updated
grep -nE "per-file semantic versioning|per-file pointer" docs/project-knowledge.md
# Expected: 1+ hits (the new pointer language landed)

grep -E "Workflow protocol version: 1\.2\.0" docs/project-knowledge.md
# Expected: ZERO hits (the stale global-version reference is gone)

# 9. No accidental cross-file contamination
git diff --stat HEAD~..HEAD  # If pre-sync is one commit
# OR
git diff --stat <pre-sync-base>..HEAD  # If multiple commits
# Expected: only the files listed in the manifest's "Files touched" table
# (now including docs/project-knowledge.md)
```

---

## Step 11 — Commit

The pre-sync can land as a single commit OR 2-3 logical commits depending on preference:

**Option A — Single commit (recommended for clarity):**

```bash
git add -A
git status  # Confirm only expected files
git commit -m "docs(sprint-31.91): pre-impromptu doc-sync — Tier 3 #2 disposition

Mid-sprint doc-sync per protocols/mid-sprint-doc-sync.md v1.0.0.
Triggered by Tier 3 #2 amended verdict (2026-04-28); operator disposition
routes 7 of 9 new DEFs as RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c)
+ 1 via Session 5c + 1 DEFERRED.

Files touched (11):
- CLAUDE.md: 10 DEF rows added (DEF-216 backfill from IMPROMPTU-10 commit c36a30c +
  DEF-217 through DEF-225 from Tier 3 #2); all in ARGUS's 4-column schema with
  structured Status/Routing/Severity prefix in Context column; DEF-175 annotated
- docs/project-knowledge.md: stale workflow-version reference replaced with
  per-file versioning pointer language (the metarepo uses per-file versioning,
  not a global version)
- work-journal-register.md: revised session order (6 new rows), 9 new DEF rows,
  carry-forward watchlist updated (7 items transitioned from Future to In-Sprint),
  DEC-388 deferral to sprint-close documented
- sprint-spec.md: D15 (Impromptu B) + D16 (Impromptu C) + AC blocks added;
  D9b auto-resolution policy table extended from 8 to 10 entries
- 3 NEW impl prompts in templates/implementation-prompt.md v1.5.0 structural-anchor format:
  * sprint-31.91-impromptu-a-alert-hardening-impl.md
  * sprint-31.91-impromptu-b-databento-heartbeat-impl.md
  * sprint-31.91-impromptu-c-migration-framework-sweep-impl.md
- AMENDED sprint-31.91-session-5c-impl.md: DEF-220 disposition fold
- NEW pre-impromptu-doc-sync-manifest.md (mechanical handoff to sprint-close)
- NEW work-journal-handoff.md (narrative handoff to Work Journal conversation)

Files NOT touched (deferred to sprint-close per Pattern B):
- decision-log.md (DEC-385, DEC-388 land at sprint-close)
- sprint-history.md (sprint-close concern)
- architecture.md final verification (sprint-close concern)
- pre-live-transition-checklist.md (DEF-217+221 entries land at sprint-close)
- CLAUDE.md test count baseline (final number not known yet)

Sprint shape post-disposition:
✅ S0–S5b backend SEALED → ⏳ Impromptu A → ⏳ Impromptu B → ⏳ S5c
→ ⏳ Impromptu C → ⏳ S5d → ⏳ S5e → ⏳ sprint-close.

Conditions for S5c entry: Impromptus A and B landed CLEAR.

Triggering verdict: docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-2-verdict.md
(amended 2026-04-28).

Manifest contract: protocols/mid-sprint-doc-sync.md v1.0.0.
Sprint-close doc-sync MUST read pre-impromptu-doc-sync-manifest.md before
applying transitions.
"
git push origin main
```

After commit, manually substitute `<this commit's SHA>` in the manifest with the actual SHA:

```bash
COMMIT_SHA=$(git rev-parse HEAD)
sed -i "s/<this commit's SHA>/${COMMIT_SHA}/" \
  docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md
git add docs/sprints/sprint-31.91-reconciliation-drift/pre-impromptu-doc-sync-manifest.md
git commit --amend --no-edit
git push --force-with-lease origin main
```

(Force-push is acceptable here only if the original commit hasn't been built upon by another collaborator — which it hasn't, since this is operator-driven and Sprint 31.91 is single-operator.)

**Option B — Two commits:** separate the docs-only edits (CLAUDE.md, work-journal-register, sprint-spec, manifest, handoff) from the impl-prompt creations (3 new + 1 amended). Functionally equivalent.

---

## Output

Report to the operator:

1. **Pre-sync commit SHA:** `<sha>`.
2. **Files touched (count):** 10.
3. **Workflow v1.3.0 compliance:** verified.
4. **Manifest produced:** `pre-impromptu-doc-sync-manifest.md`.
5. **Handoff produced:** `work-journal-handoff.md`.
6. **Push status:** clean push to origin/main.
7. **Next step per runbook:** Step 4 — return to the Work Journal conversation; paste the work-journal-handoff document (or its summary section) as the first message.

---

## Failure-stop conditions

HALT and surface to operator if any of these occur:

- A file's content does not match the expected structural anchor for an edit.
- The new impl prompt files cannot be created (e.g., file already exists with non-empty content).
- The grep verifications at any step fail.
- An edit accidentally touches a file outside the scope list.
- `git status` shows unexpected files modified.
- The manifest cannot be parsed against the `protocols/mid-sprint-doc-sync.md` v1.0.0 schema.
- The DEF table in CLAUDE.md cannot be located by the structural anchor (DEF-216 row).

In any halt, do NOT commit partial state.

---

*Pre-sync prompt generated 2026-04-28 alongside Sprint 31.91 Tier 3 #2 amended verdict.*
*Ordering: this prompt MUST run AFTER the workflow-metarepo amendment prompt has landed v1.3.0 in the metarepo.*
*Companion: `tier-3-review-2-verdict-AMENDED.md` (already committed in Step 1 of runbook), `workflow-protocol-amendment-prompt.md` (Step 2 of runbook), `tier-3-2-execution-runbook.md` (operator step-by-step).*
