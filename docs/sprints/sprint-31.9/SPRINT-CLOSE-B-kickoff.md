# Sprint 31.9 SPRINT-CLOSE-B — Core Project Doc Sync

> Drafted post-TEST-HYGIENE-01. Paste into a fresh Claude Code session on `main`.
> This prompt is **standalone** — do not read other session prompts in this campaign.
> **Ceremonial close, part B** — core project doc sync.
>
> **Sibling session:** SPRINT-CLOSE-A (`docs/sprints/sprint-31.9/SPRINT-CLOSE-A-campaign-artifacts.md`)
> **MUST run before this session.** SPRINT-CLOSE-A produces `SPRINT-31.9-SUMMARY.md`,
> which this session references as the canonical source for Sprint 31.9 statistics.
> If SPRINT-CLOSE-A has not landed (verified by checking for the SUMMARY file's existence + CLEAR review verdict),
> STOP and run SPRINT-CLOSE-A first.

## Scope

SPRINT-CLOSE-A landed campaign-internal artifacts (summary, DISCOVERY stubs, SEAL banners). Now sync 9 core project docs to reflect Sprint 31.9's outcomes. This is **substantive content addition**, not just pointer updates.

**Files touched (9):**

1. `CLAUDE.md` — Active sprint pointer + Tests count + Sprints completed list + DEF entries roll-forward
2. `docs/sprint-history.md` — NEW Sprint 31.9 section + Sprint Statistics block update + total-decisions correction
3. `docs/project-knowledge.md` — header + Tests + Sprints completed + Active sprint + recent-sprint sections
4. `docs/architecture.md` — Sprint 31.9 architectural deltas (IMPROMPTU-04 startup invariant, IMPROMPTU-10 retention task, IMPROMPTU-11 mechanism findings)
5. `docs/decision-log.md` — Sprint 31.9 entry under DEC-range reservation pattern (no new DECs); DEF roll-forward annotations if applicable
6. `docs/dec-index.md` — NEW Sprint 31.9 section (parallels existing per-sprint sections like Sprint 31.8)
7. `docs/roadmap.md` — post-31.9-reconciliation-drift insertion + Sprint 31.9 closure annotations
8. `docs/sprint-campaign.md` — Sprint 31.9 campaign-close pattern documented as part of operational evolution
9. `docs/project-bible.md` — strategic-significance update reflecting A1 validation + DEF-204 mechanism work
10. `docs/risk-register.md` — DEF-204 RSK entry; DEF-203 monitor entry

(That's 10 files, but #5 may end up with no edits if no DEF roll-forward is needed at that level — verify and skip if so.)

**EXPLICITLY NOT touched:**
- `docs/process-evolution.md` — **FROZEN by design** (Apr 21 freeze marker; Sprints 22+ explicitly excluded). P26/P27 retrospective candidates land in `sprint-history.md`'s Sprint 31.9 section instead, queued for next campaign's RETRO-FOLD.
- Anything inside `docs/sprints/sprint-31.9/` — those were sealed by SPRINT-CLOSE-A
- Anything inside `docs/sprints/post-31.9-*/` — DISCOVERY stubs were created by SPRINT-CLOSE-A
- Any `argus/` runtime code, test, or config
- The `workflow/` submodule

**Safety tag:** `safe-during-trading` — documentation only.

**Theme:** Bring the project's permanent documentation set in line with Sprint 31.9's outcomes. This is the doc-sync that keeps `project-knowledge.md` from going stale, makes `roadmap.md` reflect the new reconciliation-drift horizon, and adds DEF-204 to `risk-register.md` so future audits see the safety-critical item explicitly.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
```

### 2. SPRINT-CLOSE-A landed verification

```bash
# SPRINT-CLOSE-A's outputs must exist
ls -la docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
ls -la docs/sprints/post-31.9-reconnect-recovery-and-rejectionstage/DISCOVERY.md
ls -la docs/sprints/post-31.9-alpaca-retirement/DISCOVERY.md
ls -la docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md
ls -la docs/sprints/sprint-31.9/SPRINT-CLOSE-A-closeout.md
ls -la docs/sprints/sprint-31.9/SPRINT-CLOSE-A-review.md

# SPRINT-CLOSE-A's review verdict must be CLEAR
grep -E "Verdict.*CLEAR|verdict.*CLEAR" docs/sprints/sprint-31.9/SPRINT-CLOSE-A-review.md
# Expected: at least 1 hit
```

If any SPRINT-CLOSE-A artifact is missing or its review is not CLEAR, STOP. Run SPRINT-CLOSE-A first.

### 3. CI readiness

```bash
git log --oneline origin/main -1
# Expected: SPRINT-CLOSE-A commit on top
```

CI must be green. If red, investigate before proceeding.

### 4. Branch & workspace

```bash
git checkout main && git pull --ff-only
git status  # Expected: clean
```

### 5. process-evolution.md freeze marker confirmation

```bash
head -10 docs/process-evolution.md | grep "FROZEN"
# Expected: 1 hit. If absent, the freeze marker has been removed and SPRINT-CLOSE-B
# scope must be reconsidered. STOP and ask operator.
```

## Pre-Flight Context Reading

**Required reading order:**

1. `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` — canonical campaign summary from SPRINT-CLOSE-A. **This is the primary source for Sprint 31.9 statistics, DEF list, and session list.** All numbers in SPRINT-CLOSE-B's edits must trace back to this document.
2. Each of the 4 DISCOVERY.md files in `docs/sprints/post-31.9-*/` — needed for roadmap.md updates.

**For each core doc to be modified, read it first to understand its existing structure:**

3. `CLAUDE.md` — current "Active sprint" + "Tests" lines (header section)
4. `docs/sprint-history.md` — find existing "Sprint Statistics" block at end + look at the most recent Sprint section's structure (Sprint 31.85 or 31.8) as the template
5. `docs/project-knowledge.md` — header banner + "Tests" + "Sprints completed" + "Active sprint" sections; also recent-sprint annotations scattered through the body
6. `docs/architecture.md` — find sections that touch on order_manager, evaluation.db retention, or startup; these are likely candidate sites for Sprint 31.9 deltas (IMPROMPTU-04 startup invariant + IMPROMPTU-10 retention)
7. `docs/decision-log.md` — find the existing per-sprint DEC-range-reservation entries (e.g., the Sprint 31.8 / 31.85 entries showing "no new DECs" pattern)
8. `docs/dec-index.md` — find the existing Sprint 31.8 section showing the "no new DECs" entry format
9. `docs/roadmap.md` — find Sprint 31.9 references (already mentions `post-31.9-component-ownership` as entry-criteria-pending) + locate the Phase X / Sprint horizon structure
10. `docs/sprint-campaign.md` — read end-to-end; it's a smaller doc and Sprint 31.9 should add a clearly-anchored entry
11. `docs/project-bible.md` — find the strategy-roster section ("As of Sprint 31.85, the live roster is...") — Sprint 31.9 didn't change the roster, but does add context about A2/C12 mechanism work
12. `docs/risk-register.md` — find existing RSK entry format; new DEF-204 entry follows the same structure

## Final Statistics — Source of Truth

**Pull these from `SPRINT-31.9-SUMMARY.md` (created by SPRINT-CLOSE-A):**

- Final HEAD SHA on `origin/main`
- Final pytest: 5,080
- Final Vitest: 866
- DEFs closed during campaign: 24 (verify exact list from SUMMARY)
- DEFs opened during campaign: 6 (DEF-201, 202, 203, 204, 205, 206)
- New DECs: 0
- Total sessions: 11 named + 3 paper-session debriefs

**Pull these from independent sources (do not rely on SUMMARY):**

- Pre-campaign pytest baseline: from `CLAUDE.md` git history at IMPROMPTU-04's first commit, OR from `docs/sprint-history.md`'s "Sprint 31.85" Sprint Statistics line ("4,934+846V")
- Calendar dates: from `git log --since=2026-04-22 --pretty='%ad' --date=short` first/last entries
- Total decisions count: should be 384 (DEC-001 through DEC-384, last entry is DEC-384 added in pre-31.9 FIX-01 audit). Note: `docs/sprint-history.md` Sprint Statistics line currently says "383" — this is wrong and needs correction in Requirement 2 below.

## Requirements

### Requirement 1: Update CLAUDE.md

Surgical updates to the header section.

**1a. "Active sprint" line.** Find:

```
- **Active sprint:** Between sprints. 22 shadow variants deployed via `config/experiments.yaml`. Parquet consolidation script delivered (Sprint 31.85); operator activation of consolidated cache pending. Next: Sprint 31B. DEF-175 (component ownership consolidation) queued for a dedicated post-31.9 sprint.
```

Replace with:
```
- **Active sprint:** Between sprints. **Sprint 31.9 (Health & Hardening campaign-close) sealed on {date}.** 22 shadow variants deployed via `config/experiments.yaml`. Parquet consolidation script delivered (Sprint 31.85); operator activation of consolidated cache pending. **Next sprint:** operator-decided ordering between (a) `post-31.9-reconciliation-drift` (CRITICAL safety per DEF-204 mechanism identified by IMPROMPTU-11), (b) `post-31.9-component-ownership` (DEF-175/182/193/201/202), (c) `post-31.9-reconnect-recovery-and-rejectionstage` (DEF-194/195/196/177/184), (d) `post-31.9-alpaca-retirement` (DEF-178/183), (e) Sprint 31B (Research Console / Variant Factory). Operational mitigation in effect until DEF-204 lands: operator runs `scripts/ibkr_close_all_positions.py` daily.
```

**1b. "Tests" line.** Find:

```
- **Tests:** 5,080 pytest (--ignore=tests/test_main.py) + 39 pass / 5 skip on tests/test_main.py + 866 Vitest. Known flakes: DEF-150 (...) + DEF-167 (...) + DEF-171 (...) + DEF-190 (...) + DEF-192 (...). All batched into FIX-13 or IMPROMPTU-06. Treat as pre-existing.
```

Update by adding TEST-HYGIENE-01's resolution of DEF-205 explicitly. Replace with:
```
- **Tests:** 5,080 pytest (--ignore=tests/test_main.py) + 39 pass / 5 skip on tests/test_main.py + 866 Vitest. Sprint 31.9 net delta: +146 pytest, +20 Vitest. Known flakes: DEF-150 (time-of-day arithmetic, first 2 min of every hour) + DEF-167 (Vitest hardcoded-date scan) + DEF-171 (ibkr_broker xdist) + DEF-190 (pyarrow/xdist register_extension_type race) + DEF-192 (runtime warning cleanup debt, ~25–27 warnings, xdist-order-dependent within categories). DEF-205 (pytest date-decay sibling of DEF-167) RESOLVED by TEST-HYGIENE-01 on {date}. Treat all listed flakes as pre-existing.
```

**1c. "Sprints completed" / sprint list.** Find the line listing all completed sprints. Append `+ 31.9 (Campaign-Close: Health & Hardening)` to the count, and update the per-sprint count if needed.

The current line ends `... + 31.85 (34 full sprints + 45 sub-sprints + 10 impromptus)`. Update count notation to reflect Sprint 31.9 as a campaign-close phase rather than a sub-sprint — recommend using existing pattern: `... + 31.85 + 31.9 (35 full sprints incl. campaign-close phase + 45 sub-sprints + 10 impromptus + 11 campaign-close sessions + 3 paper-session debriefs)` — but adapt to fit existing prose style after reading the line in full.

**1d. Add P26 + P27 retrospective candidates as a new line in the Key Active Decisions section.** Find an appropriate anchor (likely near other meta-process notes or just below the most recent Sprint 31.85 entry). Add:

```
**Sprint 31.9 retrospective candidates (queued for next campaign's RETRO-FOLD):** P26 (mechanism-signature-vs-symptom-aggregate validation principle, origin Apr 24 debrief discrimination of DEF-199 closed vs DEF-204 new) + P27 (CI-discipline drift when red is "known cosmetic," origin Sprint 31.9's 6-commit CI-red streak Apr 22–24). Captured in `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` §Campaign Lessons; will fold into the workflow metarepo at the next RETRO-FOLD.
```

### Requirement 2: Update sprint-history.md

**2a. Insert a new Sprint 31.9 section.** Insert **before** the existing `## Sprint Statistics` section (which is currently at end of file). Use the same structure as the existing Sprint 31.85 section as a template.

Section content:

~~~markdown
## Sprint 31.9 — Health & Hardening Campaign-Close (April 22 – {end date}, 2026)

**Type:** Campaign (11 named sessions + 3 paper-session debriefs across {N} calendar days) | **Tests:** +146 pytest (4,934 → 5,080), +20 Vitest (846 → 866) | **New DEFs:** 6 (DEF-201–206) | **DEFs resolved:** 24 (DEF-048, 049, 152, 153, 154, 158, 161, 164, 166, 168, 169, 176, 179, 180, 181, 185, 189, 191, 193, 197, 198, 199, 200, 205) | **New DECs:** 0 (established-pattern campaign) | **All Tier 2 verdicts:** CLEAR

The campaign began as audit-2026-04-21 Phase 3 follow-on work + an Apr 22 paper-session post-mortem after a 51-symbol short-doubling cascade flipped the paper account at session close. Across the campaign, IMPROMPTU-04's A1 fix was implemented and validated through three successive paper-session debriefs (Apr 22, 23, 24); IMPROMPTU-11 then traced an upstream cascade mechanism (DEF-204) that A1 had been masking; and RETRO-FOLD captured 25 P-lessons into the `claude-workflow` metarepo.

### Sessions

11 named sessions:
- **IMPROMPTU-04** (Apr 22) — A1 short-flip fix + C1 log downgrade + startup position invariant. Closed DEF-199.
- **IMPROMPTU-CI** (Apr 22–23) — Observatory WebSocket teardown race fix; resolved IMPROMPTU-04's CONCERNS verdict via 3 consecutive green CI runs. Closed DEF-200, DEF-193.
- **IMPROMPTU-05** (Apr 23) — Deps & infra: PyJWT migration from python-jose (DEF-179); uv-based lockfile (DEF-180); Node 24 readiness for GitHub Actions (DEF-181). Closed DEF-179, 180, 181.
- **IMPROMPTU-06** (Apr 23) — Test-debt: legacy `auto_cleanup_orphans` kwarg removal (DEF-176), 5 type-guard tests (DEF-185), test_main.py xdist failures repaired (DEF-048/049, with DEF-192 PARTIAL extended). Closed DEF-048, 049, 166, 176, 185.
- **IMPROMPTU-07** (Apr 23) — Doc-hygiene + UI: boot grace config (DEF-164), DEF-189 param-name-map, DEF-191 SQLite UTC NOTE, DEF-198 boot-phase-count correction, F-05/F-06/F-08 from Apr 21 audit. Closed DEF-164, 169, 189, 191, 198.
- **IMPROMPTU-08** (Apr 23) — architecture.md API catalog regeneration via `scripts/generate_api_catalog.py` + 4 freshness tests. Closed DEF-168.
- **IMPROMPTU-10** (Apr 23) — evaluation.db periodic 4-hour retention task (DEF-197 priority elevated MEDIUM→HIGH per Apr 23 trajectory; pulled forward from post-31.9-component-ownership). Closed DEF-197.
- **RETRO-FOLD** (Apr 23) — P1–P25 metarepo fold-in across 5 metarepo files (13 RULE entries + close-out/review skills + sprint-planning protocol + implementation-prompt template). Cross-repo session: 4 argus commits + 3 metarepo commits.
- **IMPROMPTU-11** (Apr 24) — A2/C12 cascade mechanism diagnostic (read-only). 8 hypotheses evaluated against 2,225 Apr 24 broker fills; IMSR forensic anchor traced through 3 brackets. DEF-204 mechanism IDENTIFIED; fix scope routed to new `post-31.9-reconciliation-drift` named horizon. P26 retrospective candidate captured.
- **IMPROMPTU-09** (Apr 24) — Apr 22/23/24 verification sweep across 9 gaps. 6 CONFIRMED + 1 REFUTED (opens DEF-206 — catalyst-events blank-symbol upstream defect, NOT a FIX-01 regression) + 1 INCONCLUSIVE-but-code-correct + 1 cross-ref to DEF-195. DEF-206 opened.
- **TEST-HYGIENE-01** (Apr 24) — Mechanical date-decay fix: `_seed_position()` and `_seed_cf_position()` converted to dynamic patterns. CI green restored after 6-commit red streak. Closed DEF-205.

3 paper-session debriefs (each driving subsequent campaign work):
- **Apr 22** debrief — Surfaced DEF-194/195/196/197/198/199 (the bucket from which IMPROMPTU-04 + IMPROMPTU-07 + IMPROMPTU-10 derived their scope).
- **Apr 23** debrief — Reproduced A1 cascade with 51 symbols / 13,898 shares; routed to integration commit opening DEF-202/203 + annotating DEF-195/196/197.
- **Apr 24** debrief — Validated A1 fix held (44/44 detected + refused, zero doublings); discovered upstream cascade independent of A1, opening DEF-204.

### Strategic Outcomes

- **A1 short-flip cascade fixed and validated** with mathematical signature: 2.00× doubling (DEF-199 days) → 1.00× (post-fix days).
- **DEF-204 mechanism IDENTIFIED.** Bracket children placed via `parentId` only with no explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, account for ~98% of blast radius. Fix scope is 3 sessions, all-three-must-land-together.
- **Mechanism-signature-vs-symptom-aggregate principle established** as P26 retrospective candidate (origin Apr 24 debrief).
- **CI discipline restored** after 6-commit red streak.

### Sprint 31.9 Statistics

- **Total sessions:** 11 named + 3 paper-session debriefs = 14 total
- **Calendar days (active):** {N} (Apr 22 – {end date})
- **Files created:** {count}
- **Files modified:** {count}
- **Argus commits:** {count} (`{first SHA}..{last SHA}`)
- **Metarepo commits:** 3 (RETRO-FOLD: `63be1b6` + `ac3747a` + `edf69a5`)
- **All Tier 2 verdicts:** CLEAR (some with CONCERNS→resolved in-session)

### Retrospective Candidates for Next Campaign

- **P26 candidate:** Validate fix against the mechanism signature (e.g., 2.00× doubling ratio), not the symptom aggregate (e.g., "shorts at EOD"). Origin: Apr 24 debrief discrimination of DEF-199 (closed) vs DEF-204 (new). Captured in IMPROMPTU-11 §Retrospective Candidate.
- **P27 candidate:** When CI turns red for a known cosmetic reason, explicitly log that assumption at each subsequent commit rather than treating it as silent ambient noise. The test is "if a genuine regression slipped in, would I still notice?" Origin: 6-commit CI-red streak Apr 22–24.

Both queued for next campaign's RETRO-FOLD.
~~~

**2b. Update Sprint Statistics block.** Find the existing "Sprint Statistics" block at the end of the file. Apply these surgical changes:

- **Total sprints line:** add Sprint 31.9 to the breakdown. Current text: `**Total sprints:** 34 full + 45 sub-sprints (12.5, 17.5, ...) + 10 impromptus (...)`. Update to reflect 31.9 as a campaign-close phase: `**Total sprints:** 35 full + 45 sub-sprints (12.5, 17.5, ...) + 10 impromptus (...) + 1 campaign-close (Sprint 31.9: 11 named sessions + 3 paper-session debriefs)`.
- **Total sessions line:** bump count by 14 (11 + 3). If the current count is "555+", update accordingly.
- **Total tests line:** Update from `4,934 pytest + 846 Vitest = 5,780 total` to `5,080 pytest + 866 Vitest = 5,946 total`.
- **Total decisions line:** Currently says `383 (DEC-001 through DEC-383)`. **This is wrong** — DEC-384 was added in the pre-31.9 FIX-01 audit (Apr 21). Update to `384 (DEC-001 through DEC-384; no new DECs in Sprint 31.9 — campaign followed established patterns)`. Add the Sprint 31.9 sub-mention to the existing list of "no new DECs in Sprints..." enumeration.
- **Calendar days line:** extend range. Currently says `~53 (Feb 14 – Apr 5, 2026 + Apr 14, Apr 20, 2026)`. Update to `~62 (Feb 14 – Apr 5, 2026 + Apr 14, Apr 20, 2026 + Apr 22 – {end date}, 2026)` — adjust to actual range.

### Requirement 3: Update project-knowledge.md

**3a. Header banner.** Find:

```
> *Tier A operational context for Claude Code and Claude.ai. Last updated: April 20, 2026 (Sprint 31.85 doc sync — Parquet cache consolidation, DEF-161 resolved).*
```

Replace `April 20, 2026 (Sprint 31.85 doc sync...)` with `{end date}, 2026 (Sprint 31.9 campaign-close — A1 short-flip fix validated, DEF-204 mechanism identified)`.

**3b. Tests line.** Mirror the CLAUDE.md update from Requirement 1b.

**3c. Sprints completed.** Mirror the CLAUDE.md update from Requirement 1c. Add Sprint 31.9 to the list.

**3d. Active sprint line.** Mirror the CLAUDE.md update from Requirement 1a.

**3e. Recent-sprint section, if any (lower in the file).** project-knowledge.md may have a "Sprint History (Summary)" or similar table. Find it and add a Sprint 31.9 row matching the existing table format. Refer to sprint-history.md's Sprint 31.9 section for the row content.

### Requirement 4: Update architecture.md

Sprint 31.9 produced 3 architecturally-relevant deltas. Apply each to the appropriate architecture.md section:

**4a. IMPROMPTU-04 startup invariant.** Find a section discussing system startup or component lifecycle (likely §Phase 0–10 startup sequence). Add a sub-bullet or paragraph noting the new `_enforce_startup_position_invariant()` helper installed at `argus/main.py` (cite line range only if it can be verified from a fresh `grep -n` against current main; otherwise reference the function name without line numbers). Note that the helper is gated and runs at startup if broker positions exist.

**4b. IMPROMPTU-10 evaluation.db periodic retention.** Find the section discussing `EvaluationEventStore` or strategy telemetry persistence. Add a paragraph: "The store now spawns a periodic retention task in `EvaluationEventStore.initialize()` (4-hour cadence, gated by shutdown signal) that calls `cleanup_old_events()`. This handles the multi-day session case where startup-only retention couldn't keep up with ~5 GB/day ingestion (DEF-197, IMPROMPTU-10, Sprint 31.9)."

**4c. IMPROMPTU-11 mechanism findings (informational, not a fix).** Find the section discussing Order Manager bracket orders or reconciliation. Add a NOTE block: "**Known issue (DEF-204, identified Apr 24).** Bracket children are placed via `parentId` only without explicit `ocaGroup`; combined with standalone SELL orders from trail/escalation paths that share no OCA group with bracket children, this allows multi-leg fill races that produce ~98% of the unexpected-short blast radius observed during Apr 24 paper trading. Fix scoped to the `post-31.9-reconciliation-drift` named horizon (3 sessions, all-three-must-land-together). See `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` for the full forensic analysis."

These additions are anchored to existing sections; do not create new top-level architecture.md sections. If a natural anchor doesn't exist, fall back to inserting in the closest relevant section with a clear cross-reference to the IMPROMPTU close-out.

### Requirement 5: Update decision-log.md

decision-log.md uses a per-sprint pattern for "no new DECs" entries. Search for the existing Sprint 31.85 entry (e.g., grep for `Sprint 31.85` and find the "no new DECs" annotation). Use it as the template for a new Sprint 31.9 entry.

Insert the new Sprint 31.9 section in chronological order (after Sprint 31.85's entry):

~~~markdown
## Sprint 31.9 — Campaign-Close: Health & Hardening (April 22 – {end date}, 2026)

No new DECs across the 11 named sessions and 3 paper-session debriefs. All design decisions followed established patterns:

- **IMPROMPTU-04** A1 short-flip fix used the existing CRITICAL-alert + flatten-refusal pattern from earlier safety work (DEC-369 / DEC-370 broker-confirmed-positions framework).
- **IMPROMPTU-CI** observatory WebSocket teardown followed the existing `_listener_task` cancel-await idiom from other WebSocket handlers.
- **IMPROMPTU-05** lockfile work followed standard `uv pip compile` patterns; PyJWT migration was a like-for-like API replacement.
- **IMPROMPTU-06** test-debt cleanup applied existing IMPROMPTU-04-style 3-branch type-guards.
- **IMPROMPTU-07** boot grace config followed the standard `OrderManagerConfig` field-addition pattern.
- **IMPROMPTU-08** architecture.md catalog regeneration is a new tool, but the implementation is standard FastAPI introspection — no novel decision required.
- **IMPROMPTU-10** periodic retention task used the standard `asyncio.create_task` + `_shutdown` flag pattern (mirroring `_run_polling_loop` in `argus/main.py`).
- **RETRO-FOLD** is the second campaign-close retro fold-in (first was post-Sprint-21 era); pattern was established earlier.
- **IMPROMPTU-11** is read-only diagnostic; no design decisions made.
- **IMPROMPTU-09** is read-only verification; no design decisions made.
- **TEST-HYGIENE-01** mechanical date conversion followed the FIX-13a (DEF-167) Vitest-side precedent exactly.

DEC range allocation: none reserved or consumed for Sprint 31.9. (Established-pattern campaign.)

DEFs opened: DEF-201, 202, 203, 204, 205, 206 (now-closed: DEF-205). Routed to named horizons (DEF-201/202 → component-ownership; DEF-204 → reconciliation-drift; DEF-203 → MONITOR-only; DEF-206 → opportunistic catalyst-layer touch).
~~~

### Requirement 6: Update dec-index.md

dec-index.md uses the same per-sprint pattern (verified via Sprint 31.8 entry). Add Sprint 31.9 entry in the same chronological location.

**6a. Header.** dec-index.md header currently reads `> 384 decisions (DEC-001 through DEC-384)`. **No update needed** — Sprint 31.9 added zero DECs.

**6b. Sprint 31.9 section.** Insert after the Sprint 31.8 section (which is the existing latest):

~~~markdown
## Sprint 31.9 — Campaign-Close (April 22 – {end date}, 2026)

No new DECs across 11 named sessions + 3 paper-session debriefs. All design decisions followed established patterns. See `docs/decision-log.md` Sprint 31.9 entry for per-session rationale. Sprint outcomes summarized in `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md`.
~~~

### Requirement 7: Update roadmap.md

**7a. Sprint 31.9 closure annotation.** Find references to Sprint 31.9 in roadmap.md (currently appears in passing as "Entry criteria include Sprint 31.9 closure" for component-ownership). Update to reflect that Sprint 31.9 has now closed; entry criteria for component-ownership is therefore satisfied (modulo the operator's safety-priority decision about which post-31.9 horizon runs first).

**7b. Insert post-31.9-reconciliation-drift in horizons section.** Find the existing post-31.9 horizon listings (search for `post-31.9-component-ownership` / `post-31.9-alpaca-retirement` / `post-31.9-reconnect-recovery-and-rejectionstage`). Add a new horizon entry for `post-31.9-reconciliation-drift` with:
- DEF-204 (CRITICAL safety, mechanism IDENTIFIED)
- 3 sessions, all-three-must-land-together
- Adversarial review required
- See `docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`
- Likely takes precedence over Sprint 31B in build-track ordering due to safety priority

**7c. Update build-track queue narrative.** roadmap.md likely has a section discussing build-track queue ordering. Update to reflect that Sprint 31.9 is closed and 4 post-31.9 horizons (component-ownership, reconnect-recovery-and-rejectionstage, alpaca-retirement, reconciliation-drift) are queued alongside Sprint 31B with operator-decided ordering.

### Requirement 8: Update sprint-campaign.md

sprint-campaign.md last mentions Sprint 31.5. Sprint 31.9 represents a new operational pattern worth documenting: the **campaign-close** model with safe-during-trading discipline + 3 paper-session debriefs as evidence-gathering tools + IMPROMPTU-CI as a CI-restoration session pattern.

Add a new section near the end (or wherever the most recent operational pattern is documented):

~~~markdown
## Sprint 31.9 — Campaign-Close Pattern Evolution

Sprint 31.9 (April 22 – {end date}, 2026) ran as a campaign-close, a multi-session bundle that:

- Maintained `safe-during-trading` discipline across most sessions (only IMPROMPTU-04 + TEST-HYGIENE-01 touched runtime-relevant code; all others were pure docs/tests/diagnostic)
- Used **3 paper-session debriefs** (Apr 22, 23, 24) as the primary evidence-gathering mechanism — each debrief drove subsequent session scope
- Pioneered **IMPROMPTU-CI** as a mid-campaign session pattern: a focused fix dedicated to restoring CI-green when prior session(s) shipped CONCERNS verdicts that needed live-data validation
- Demonstrated **mechanism-signature validation** through Apr 24 debrief (proving DEF-199 closed via 1.00× signature vs prior 2.00×, while simultaneously identifying DEF-204 as a different mechanism that A1 had been masking)

Key operational insights captured as P26/P27 retrospective candidates for next campaign's RETRO-FOLD. See `docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` and `docs/sprint-history.md` for details.
~~~

### Requirement 9: Update project-bible.md

project-bible.md is the strategic-level "what and why" doc. Sprint 31.9's strategic significance:
- The IMPROMPTU-04 / Apr 24 validation arc proves the disciplined-validation approach works (the system's safety mechanisms can be evolved through clear-evidence campaigns).
- DEF-204's mechanism identification demonstrates ARGUS's diagnostic capability matures.

**9a. Find the strategy-roster mention.** Currently reads (~):

```
As of Sprint 31.85, the live roster is 13 + 2 shadow (ABCD, Flat-Top Breakout demoted to shadow mode in Sprint 32.9 pending optimization).
```

Update `Sprint 31.85` → `Sprint 31.9 (post-campaign-close)`. Roster itself is unchanged by Sprint 31.9.

**9b. If a "Recent Operational Milestones" or similar section exists, add an entry.** If no such section exists, do NOT create one — project-bible.md's structure is intentionally philosophical, and adding new sections risks drift.

### Requirement 10: Update risk-register.md

**10a. Add new RSK entry for DEF-204.** Use existing RSK entry format. Insert in the Risks section, parallel to the DEF-161 / DuckDB-materialization entry that already exists:

~~~markdown
### RSK — Upstream Cascade Mechanism (DEF-204)

| Field | Value |
|---|---|
| **ID** | RSK-DEF-204 |
| **Category** | Operational Safety — Critical |
| **Description** | Bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, allow multi-leg fill races. ARGUS's exit-side accounting is also side-blind in 3 surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info; DEF-158 retry path side-blind). On Apr 24 paper trading: 44 symbols / 14,249 shares of unintended short positions accumulated through gradual reconciliation-mismatch drift over a 6-hour session. Today's raw upstream cascade is ~2.0× worse than yesterday's pre-doubling magnitude despite the lightest network stimulus of the three debriefed days. |
| **Mitigation (in effect)** | Operator runs `scripts/ibkr_close_all_positions.py` daily at session close. IMPROMPTU-04's A1 fix correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert. |
| **Owner** | post-31.9-reconciliation-drift sprint (3 sessions, all-three-must-land-together, adversarial review required). |
| **Status** | OPEN — mitigation in effect; fix scoped and scheduled. Not safe for live trading until post-31.9-reconciliation-drift lands. |
| **Cross-references** | DEF-204 (CLAUDE.md); IMPROMPTU-11 mechanism diagnostic; Apr 24 debrief §A2/§C12. |
~~~

**10b. Add new RSK entry for DEF-203 (lower priority, tracked for completeness).** Format similar to above but Operational Hygiene category, MEDIUM (or LOW) priority. Body:

> `max_concurrent_positions` WARNING spam not throttled — 10,729 events on Apr 24, 8,996 on Apr 23. WARNING-level emit from `argus/core/risk_manager.py` without ThrottledLogger wrapping. MONITOR-only — fix queued for next `argus/core/risk_manager.py` touch (likely as part of post-31.9-reconnect-recovery-and-rejectionstage's DEF-195 work).

## Constraints

- **Do NOT modify** any argus runtime code, test, or config
- **Do NOT touch** `docs/process-evolution.md` (FROZEN)
- **Do NOT touch** anything inside `docs/sprints/sprint-31.9/` (sealed by SPRINT-CLOSE-A)
- **Do NOT touch** anything inside `docs/sprints/post-31.9-*/` (DISCOVERY stubs sealed by SPRINT-CLOSE-A)
- **Do NOT touch** the `workflow/` submodule
- **Do NOT change** existing decisions or DEFs that aren't part of Sprint 31.9. If you find errors in older content, NOTE them in the close-out but do not fix them.
- **Do NOT add new DECs** — Sprint 31.9 is established-pattern.
- Work directly on `main`.

## Test Targets

- pytest full suite unchanged at 5,080 (no code changes)
- Vitest unchanged at 866
- CI remains green

## Definition of Done

- [ ] CLAUDE.md "Active sprint", "Tests", "Sprints completed" lines updated; P26/P27 candidates noted
- [ ] sprint-history.md has new Sprint 31.9 section; Sprint Statistics block updated; total decisions corrected to 384
- [ ] project-knowledge.md header banner + Tests + Sprints completed + Active sprint updated
- [ ] architecture.md has Sprint 31.9 deltas (startup invariant + retention task + DEF-204 mechanism note)
- [ ] decision-log.md has Sprint 31.9 "no new DECs" entry
- [ ] dec-index.md has Sprint 31.9 entry parallel to Sprint 31.8 format
- [ ] roadmap.md has post-31.9-reconciliation-drift horizon listed; Sprint 31.9 closure annotated
- [ ] sprint-campaign.md has Sprint 31.9 campaign-close pattern documented
- [ ] project-bible.md strategy-roster mention bumped to Sprint 31.9
- [ ] risk-register.md has DEF-204 + DEF-203 RSK entries
- [ ] Close-out at `docs/sprints/sprint-31.9/SPRINT-CLOSE-B-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/SPRINT-CLOSE-B-review.md`
- [ ] Final green CI URL cited
- [ ] **process-evolution.md NOT MODIFIED** (verify via `git diff docs/process-evolution.md` empty)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| All 9 core docs updated (or explicitly skipped with rationale) | `git diff --name-only docs/*.md \| sort` matches expected list |
| process-evolution.md untouched | `git diff docs/process-evolution.md` empty |
| No sprint-31.9 directory file modified | `git diff docs/sprints/sprint-31.9/` empty |
| No post-31.9 directory file modified | `git diff docs/sprints/post-31.9-*/` empty |
| Total-decisions count corrected from 383 to 384 in sprint-history.md | grep `384 (DEC-001 through DEC-384` |
| dec-index.md header still says "384 decisions" (unchanged) | grep `> 384 decisions` |
| risk-register.md has 2 new RSK entries (DEF-204 + DEF-203) | grep `RSK-DEF-204` |
| roadmap.md has post-31.9-reconciliation-drift mention | grep `post-31.9-reconciliation-drift` |
| Cross-references to SPRINT-31.9-SUMMARY.md present in updated docs | grep `SPRINT-31.9-SUMMARY` across modified docs |
| No `argus/` or `tests/` or `config/` modified | `git diff argus/ tests/ config/` empty |
| Statistics in updates match SPRINT-31.9-SUMMARY.md | Cross-validate test counts, DEF lists, etc. |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/SPRINT-CLOSE-B-closeout.md`

Include:
1. **Files modified:** list of 9 (or 10) core docs touched, with 1-line summary of each change
2. **Files explicitly NOT modified:** confirm process-evolution.md frozen status respected; sprint-31.9/ + post-31.9-*/ directories untouched
3. **Statistics cross-validation:** confirm numbers in updated docs match SPRINT-31.9-SUMMARY.md (any discrepancies require correction or explicit note)
4. **Total-decisions correction:** confirm sprint-history.md updated from "383" to "384" with rationale
5. **DEF-204 RSK entry:** confirm risk-register.md has the new entry
6. **Final green CI URL**
7. **Closing statement:** Sprint 31.9 is now SEALED at all levels (campaign-internal via SPRINT-CLOSE-A + project-wide via SPRINT-CLOSE-B). Build-track unblocked.
8. **Next-session note:** SPRINT-CLOSE-B is the final session of Sprint 31.9. Operator's next decision is which post-31.9 horizon (or Sprint 31B) runs first.

## Tier 2 Review (Mandatory — @reviewer subagent, standard profile)

Provide:
1. This kickoff
2. Close-out path
3. Diff range
4. Files that should NOT have been modified:
   - `docs/process-evolution.md` (FROZEN)
   - Anything inside `docs/sprints/sprint-31.9/` (sealed by SPRINT-CLOSE-A)
   - Anything inside `docs/sprints/post-31.9-*/` (DISCOVERY stubs from SPRINT-CLOSE-A)
   - Any `argus/` code, test, or config file
   - Any pre-existing session close-out, review, or debrief
   - The `workflow/` submodule

## Session-Specific Review Focus (for @reviewer)

1. **Verify process-evolution.md untouched.** This is the cleanest scope-boundary check. `git diff docs/process-evolution.md` must be empty.
2. **Verify sprint-31.9 + post-31.9 sealed dirs untouched.** `git diff docs/sprints/sprint-31.9/ docs/sprints/post-31.9-*/` must be empty.
3. **Verify statistics consistency.** Each updated doc that cites Sprint 31.9 stats (test count, DEF list, sprint count) must match SPRINT-31.9-SUMMARY.md. Spot-check 3 numbers across 3 different docs.
4. **Verify total-decisions corrected to 384** in sprint-history.md.
5. **Verify DEF-204 RSK entry present** with the agreed-upon format and mitigation language.
6. **Verify roadmap.md insertion** of post-31.9-reconciliation-drift horizon.
7. **Verify no new DECs were added** anywhere in decision-log.md or dec-index.md (campaign was zero-DEC).
8. **Verify cross-references work.** Updated docs that reference SPRINT-31.9-SUMMARY.md or DISCOVERY.md files should use correct paths.
9. **Verify CI green** for the SPRINT-CLOSE-B commit.

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- process-evolution.md modified
- sprint-31.9/ or post-31.9-*/ files modified
- Any argus/tests/config file modified
- Any new DEC added
- Statistics in updated docs contradict SPRINT-31.9-SUMMARY.md without documented rationale
- DEF-204 RSK entry missing or contains wrong mitigation
- post-31.9-reconciliation-drift not added to roadmap.md
- Sprint 31.9 marked as having added new DECs (it didn't)
- total-decisions still says 383 in sprint-history.md
- Pre-existing content removed (only additions are in scope)

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Files modified summary:** list of 9 or 10 core docs touched
4. **Sealed status:** Sprint 31.9 now sealed at all 3 levels — campaign artifacts (SPRINT-CLOSE-A), project docs (SPRINT-CLOSE-B), CI green
5. **Build-track decision point:** operator chooses next sprint from {post-31.9-reconciliation-drift, post-31.9-component-ownership, post-31.9-reconnect-recovery-and-rejectionstage, post-31.9-alpaca-retirement, Sprint 31B}. Recommend reconciliation-drift first per safety priority.
6. Final green CI URL
7. One-line summary: `Sprint 31.9 SPRINT-CLOSE-B complete. 9 core project docs synced. Sprint 31.9 fully SEALED. Operator decides next-sprint priority. CI: {URL}.`
