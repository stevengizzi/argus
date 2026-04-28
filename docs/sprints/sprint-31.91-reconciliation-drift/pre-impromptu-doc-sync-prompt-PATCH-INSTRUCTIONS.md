# Patch Instructions — ARGUS Pre-Impromptu Doc-Sync Prompt

> **Target file:** `pre-impromptu-doc-sync-prompt.md` (the 1,461-line prompt produced earlier).
> **Reason for patches:** the original prompt referenced a global "workflow v1.3.0" framing that doesn't match the metarepo's per-file versioning model. Investigation revealed the metarepo evolves files independently. The patches reframe version references and add a missing edit (project-knowledge.md update).
> **Apply BEFORE running the ARGUS pre-sync prompt against Claude Code.**
> **Apply method:** open the prompt in a text editor; perform the search-and-replace operations below; save. Then proceed with runbook Step 3 as before.

---

## Patch 1 — Reframe global "workflow v1.3.0" references

**Where:** throughout the prompt, the phrase "workflow v1.3.0" appears as a global version. This needs to be reframed as "the workflow contract that includes `protocols/mid-sprint-doc-sync.md` v1.0.0."

### Patch 1a — Top-of-prompt metadata

**FIND** (in the metadata header at the top of the prompt):

```
> **Workflow contract:** v1.3.0 (must be live in `claude-workflow` metarepo before this prompt runs).
```

**REPLACE WITH:**

```
> **Workflow contract:** the metarepo state that includes `protocols/mid-sprint-doc-sync.md` v1.0.0 + `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment). The metarepo uses per-file versioning, not a global semantic version. Both must be live in the `claude-workflow` metarepo before this prompt runs (verify via the workflow-protocol-amendment-prompt-REVISED).
```

### Patch 1b — Pre-flight check

**FIND:**

```bash
cd workflow  # if the metarepo is a submodule, OR clone fresh
git log -1 --oneline  # Should be the v1.3.0 amendment commit
grep "workflow-version: 1.3.0" protocols/mid-sprint-doc-sync.md  # Should hit
cd -
```

**REPLACE WITH:**

```bash
cd workflow  # if the metarepo is a submodule, OR clone fresh
git log -3 --oneline  # Should include the mid-sprint-doc-sync amendment commit
ls protocols/mid-sprint-doc-sync.md  # Should exist
grep "workflow-version: 1.0.0" protocols/mid-sprint-doc-sync.md  # Should hit
grep "workflow-version: 1.5.0" templates/implementation-prompt.md  # Should hit (structural-anchor amendment)
cd -
```

### Patch 1c — "If the metarepo is NOT at v1.3.0" sentence

**FIND:**

```
If the metarepo is NOT at v1.3.0, **STOP**. The pre-sync depends on the v1.3.0 contract for the new protocol and structural-anchor format. Run the workflow-metarepo amendment prompt first per the runbook.
```

**REPLACE WITH:**

```
If `protocols/mid-sprint-doc-sync.md` does not exist in the metarepo OR `templates/implementation-prompt.md` is not at 1.5.0+, **STOP**. The pre-sync depends on both for the new protocol and structural-anchor format. Run the (revised) workflow-metarepo amendment prompt first per the runbook.
```

### Patch 1d — Operating principles section

**FIND:**

```
This prompt operates under workflow v1.3.0. Per the structural-anchor amendment:
```

**REPLACE WITH:**

```
This prompt operates under the metarepo state that includes `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment) and `protocols/mid-sprint-doc-sync.md` v1.0.0. Per the structural-anchor amendment:
```

**FIND:**

```
Per the mid-sprint-doc-sync protocol (`protocols/mid-sprint-doc-sync.md`):
```

(unchanged — this reference is correct)

### Patch 1e — Manifest content (inside the embedded manifest template)

**FIND** (inside the manifest content embedded in Step 8):

```
## Workflow version compliance

This manifest was produced under workflow v1.3.0 (mid-sprint-doc-sync protocol + structural-anchor amendment). Sprint-close doc-sync MUST run under workflow v1.3.0 or higher. If sprint-close runs under an earlier version, the discrepancy MUST be explicitly disclosed and the manifest MUST be re-validated against the current version's contract.
```

**REPLACE WITH:**

```
## Workflow version compliance

This manifest was produced under `protocols/mid-sprint-doc-sync.md` v1.0.0 (introduced 2026-04-28) and `templates/implementation-prompt.md` v1.5.0 (structural-anchor amendment, 2026-04-28). The metarepo uses per-file versioning. Sprint-close doc-sync MUST run against a metarepo state where `protocols/mid-sprint-doc-sync.md` exists at v1.0.0 or higher AND `templates/doc-sync-automation-prompt.md` is at v1.2.0 or higher (the version that introduced the manifest-reading step). If sprint-close runs under an earlier metarepo state, the discrepancy MUST be explicitly disclosed.
```

### Patch 1f — Manifest top-of-file comment

**FIND** (in the manifest's HTML comments):

```
<!-- workflow-version: 1.3.0 -->
<!-- Manifest type: pre-impromptu doc-sync (Sprint 31.91 Tier 3 #2 disposition) -->
```

**REPLACE WITH:**

```
<!-- protocol-version: protocols/mid-sprint-doc-sync.md v1.0.0 -->
<!-- Manifest type: pre-impromptu doc-sync (Sprint 31.91 Tier 3 #2 disposition) -->
```

### Patch 1g — Handoff document — "Workflow metarepo bumped to v1.3.0"

**FIND** (in the work-journal-handoff.md content embedded in Step 9):

```
3. **Workflow metarepo bumped to v1.3.0** with two amendments: structural-anchor requirement for impl prompts + new `protocols/mid-sprint-doc-sync.md` formalizing the multi-sync coordination pattern.
```

**REPLACE WITH:**

```
3. **Workflow metarepo extended with two amendments** (per-file forward bumps, not a global version step): NEW `protocols/mid-sprint-doc-sync.md` v1.0.0 formalizing the multi-sync coordination pattern + structural-anchor amendment to `templates/implementation-prompt.md` (1.4.0 → 1.5.0) + cross-references in 7 other files. The metarepo uses per-file versioning; there is no single "metarepo version."
```

### Patch 1h — Handoff document — workflow metarepo file list

**FIND** (in the handoff's "Workflow metarepo (separate clone, v1.3.0)" subsection):

```
### Workflow metarepo (separate clone, v1.3.0)
- `protocols/mid-sprint-doc-sync.md` — NEW protocol (governs this sync's pattern).
- `templates/implementation-prompt.md` — UPDATED (structural-anchor format).
- `templates/doc-sync-automation-prompt.md` — UPDATED (manifest-reading at sprint-close).
- `templates/work-journal-closeout.md` — UPDATED (manifest acknowledgment requirement).
- 4 protocols UPDATED with cross-references: `sprint-planning.md`, `in-flight-triage.md`, `tier-3-review.md`, `impromptu-triage.md`.
- `bootstrap-index.md` — UPDATED (Protocol Index + Conversation Type table entries for mid-sync).
```

**REPLACE WITH:**

```
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
```

### Patch 1i — Handoff document — "Workflow v1.3.0 contracts are now binding"

**FIND** (in the "Critical reminders" section of the handoff):

```
- **Workflow v1.3.0 contracts are now binding.** Future impl prompts must use structural anchors. Future mid-sprint syncs must produce manifests.
```

**REPLACE WITH:**

```
- **Workflow contracts are now binding.** Future impl prompts must use structural anchors per `templates/implementation-prompt.md` v1.5.0+. Future mid-sprint syncs must produce manifests per `protocols/mid-sprint-doc-sync.md` v1.0.0+.
```

### Patch 1j — Handoff document — operator-facing summary paragraph

**FIND** (the one-paragraph summary at the bottom of the handoff):

```
> Tier 3 #2 architectural review for Sprint 31.91 completed 2026-04-28 (PROCEED with conditions, amended). 9 new DEFs filed; 7 routed RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c), 1 to Session 5c (DEF-220), 1 deferred (DEF-222). Workflow metarepo bumped to v1.3.0 (mid-sprint doc-sync protocol + structural-anchor amendment). Pre-impromptu doc-sync landed on `main`. Sprint shape revised: new order is Impromptu A → Impromptu B → S5c → Impromptu C → S5d → S5e → sprint-close. DEC-388 deferred to sprint-close (Pattern B). Resume by reading `sprint-31.91-impromptu-a-alert-hardening-impl.md` and beginning Impromptu A with a fresh Claude Code session.
```

**REPLACE WITH:**

```
> Tier 3 #2 architectural review for Sprint 31.91 completed 2026-04-28 (PROCEED with conditions, amended). 9 new DEFs filed; 7 routed RESOLVED-IN-SPRINT (Impromptus A+B+C + Session 5c), 1 to Session 5c (DEF-220), 1 deferred (DEF-222). Workflow metarepo extended with NEW `protocols/mid-sprint-doc-sync.md` v1.0.0 + structural-anchor amendment to `templates/implementation-prompt.md` (now v1.5.0) + cross-references in 7 other files (per-file forward bumps; no global version). Pre-impromptu doc-sync landed on `main`. Sprint shape revised: new order is Impromptu A → Impromptu B → S5c → Impromptu C → S5d → S5e → sprint-close. DEC-388 deferred to sprint-close (Pattern B). Resume by reading `sprint-31.91-impromptu-a-alert-hardening-impl.md` and beginning Impromptu A with a fresh Claude Code session.
```

---

## Patch 2 — Add a NEW Step 1.5 for `project-knowledge.md`

**Insertion point:** between the existing Step 1 and Step 2 of the ARGUS pre-sync prompt.

**Why:** the ARGUS repo's `project-knowledge.md` (likely at `docs/project-knowledge.md`) contains a stale workflow-version reference (specifically `Workflow protocol version: 1.2.0 (per-session register discipline formalized)` per the project-knowledge document this conversation operates from). The pre-sync should update it to reflect the per-file versioning reality.

### Patch 2 content — insert this block between Step 1 and Step 2

**FIND** (the line that ends Step 1 — likely a horizontal rule or the start of Step 2):

```
---

## Step 2 — Update `work-journal-register.md`
```

**REPLACE WITH:**

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
```

(Continues from there with the existing Step 2 content unchanged.)

---

## Patch 3 — Add `project-knowledge.md` to the Final Verification step

### Patch 3 content

**FIND** (in Step 10 — Final verification, near the existing verification commands):

```
# 8. No accidental cross-file contamination
git diff --stat HEAD~..HEAD  # If pre-sync is one commit
# OR
git diff --stat <pre-sync-base>..HEAD  # If multiple commits
# Expected: only the files listed in the manifest's "Files touched" table
```

**REPLACE WITH:**

```
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

## Patch 4 — Add `project-knowledge.md` to the manifest's "Files touched" table

### Patch 4 content

**FIND** (in the manifest content embedded in Step 8 — the "Files touched by this pre-sync" table):

```markdown
| File | Change shape | Sprint-close transition owed |
|---|---|---|
| `CLAUDE.md` | 9 new DEF rows added (DEF-217 through DEF-225); DEF-175 row annotated with main.py + set_order_manager motivators. | Each new DEF row's Status column transitions OPEN → RESOLVED-IN-SPRINT per its routing; DEF-175 row remains OPEN (existing scope, post-31.9-component-ownership sprint owns). |
```

**REPLACE WITH:**

```markdown
| File | Change shape | Sprint-close transition owed |
|---|---|---|
| `CLAUDE.md` | 9 new DEF rows added (DEF-217 through DEF-225); DEF-175 row annotated with main.py + set_order_manager motivators. | Each new DEF row's Status column transitions OPEN → RESOLVED-IN-SPRINT per its routing; DEF-175 row remains OPEN (existing scope, post-31.9-component-ownership sprint owns). |
| `docs/project-knowledge.md` | Stale "Workflow protocol version: 1.2.0" reference replaced with per-file versioning pointer language; cross-references to current per-protocol versions added. | None (pointer language is forward-compatible; sprint-close should NOT need to re-edit). |
```

---

## Patch 5 — Add `project-knowledge.md` to the commit message

### Patch 5 content

**FIND** (in Step 11 — Commit, the commit message body):

```
Files touched (10):
- CLAUDE.md: 9 new DEF rows (DEF-217 through DEF-225) + DEF-175 annotation
- work-journal-register.md: revised session order (6 new rows), 9 new DEF rows,
  carry-forward watchlist updated (7 items transitioned from Future to In-Sprint),
  DEC-388 deferral to sprint-close documented
```

**REPLACE WITH:**

```
Files touched (11):
- CLAUDE.md: 9 new DEF rows (DEF-217 through DEF-225) + DEF-175 annotation
- docs/project-knowledge.md: stale workflow-version reference replaced with
  per-file versioning pointer language (the metarepo uses per-file versioning,
  not a global version)
- work-journal-register.md: revised session order (6 new rows), 9 new DEF rows,
  carry-forward watchlist updated (7 items transitioned from Future to In-Sprint),
  DEC-388 deferral to sprint-close documented
```

---

## Verification after applying patches

After applying all 5 patches to `pre-impromptu-doc-sync-prompt.md`, verify the prompt's internal consistency:

```bash
# In whatever directory holds your local copy of the prompt:

# 1. No remaining global "v1.3.0" references
grep -nE "workflow v1\.3\.0|workflow-version: 1\.3\.0" pre-impromptu-doc-sync-prompt.md
# Expected: only references in the manifest content that explicitly disclose per-file
# versioning OR none at all

# 2. New per-file references are present
grep -nE "v1\.5\.0|v1\.0\.0|per-file" pre-impromptu-doc-sync-prompt.md | head -10
# Expected: multiple hits (1.5.0 for impl-prompt template, 1.0.0 for new protocol,
# "per-file" in pointer language)

# 3. project-knowledge.md is mentioned
grep -nE "project-knowledge\.md" pre-impromptu-doc-sync-prompt.md
# Expected: 4+ hits (Step 1.5 + verification + manifest table + commit message)

# 4. Step 1.5 is present
grep -nE "^## Step 1\.5" pre-impromptu-doc-sync-prompt.md
# Expected: 1 hit
```

If all four checks pass, the patched prompt is ready to run per runbook Step 3.

---

## What to do if patches don't apply cleanly

If a FIND target doesn't match exactly (e.g., subtle whitespace differences, or the original prompt's text drifted in your local copy):

1. **Don't force the patch.** Find the closest match manually and apply the semantic intent.
2. **Verify the final state** matches the verification checks above regardless of patch application path.
3. **The semantic invariants are:** (a) no global "workflow v1.3.0" framing remains; (b) per-file version references replace it; (c) Step 1.5 for `project-knowledge.md` exists; (d) the manifest, handoff, verification, and commit message all reference `project-knowledge.md`.

If any patch genuinely cannot be applied (the FIND target doesn't exist at all in the prompt), STOP and report — the prompt may have been edited from a different source.

---

## Updated runbook step

The `tier-3-2-execution-runbook.md` Step 3 instructions should be amended to read:

> ### Step 3 — Run the (PATCHED) ARGUS pre-impromptu doc-sync prompt
>
> Apply patches per `pre-impromptu-doc-sync-prompt-PATCH-INSTRUCTIONS.md` first, then run the patched prompt.
> The patched prompt now also updates `docs/project-knowledge.md` (Step 1.5) and references the actual per-file workflow versions (no global v1.3.0 framing).

If you prefer, regenerate the runbook with this change inline; otherwise just keep both files together when executing.

---

*Patch instructions generated 2026-04-28 after pre-flight investigation revealed metarepo uses per-file versioning.*
*Apply BEFORE running the ARGUS pre-sync against Claude Code.*
*Companion: `workflow-protocol-amendment-prompt-REVISED.md` (run first, against the metarepo).*
