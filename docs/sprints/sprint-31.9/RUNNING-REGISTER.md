# Sprint 31.9 Running Register

> Canonical snapshot of campaign state: session verdicts, DEF/DEC register,
> outstanding items, deferred pickups, and next-stage plan. Rebuild this file
> at every stage barrier. Survives compaction — read this file to hydrate
> a fresh Claude.ai conversation.
>
> **Last updated:** 2026-04-22, end of Stage 2 (Pass 3 barrier closed)
> **Campaign HEAD:** `f57a965` (docs FIX-12) / code HEAD `db2818b`
> **Workflow submodule:** `942c53a`
> **Baseline tests:** 4,964 pytest + 859 Vitest + 0 failures (at f57a965)

---

## Campaign overview

- **Identifier:** `sprint-31.9-health-and-hardening`
- **Artifacts directory:** `docs/sprints/sprint-31.9/`
- **Key docs:** `README.md`, `STAGE-FLOW.md`, `WORK-JOURNAL-HANDOFF.md`, this register
- **Session count:** 24 planned across 9 stages (Track A: 22 FIX-NN sessions; Track B: 2 IMPROMPTU sessions)
- **Operator:** Steven Gizzi (two-Claude workflow: Claude.ai planning + Claude Code implementation, git bridge)
- **Account under test:** IBKR paper U24619949 (paper paused during weekend-only sessions)

---

## Stage status

| Stage | Sessions | Status |
|---|---|---|
| Stage 1 | FIX-00 + FIX-15 + FIX-17 + FIX-20 + FIX-01 + FIX-11 + Stage 1 sweep | ✅ COMPLETE |
| Stage 2 Pass 1 | FIX-02 (config drift via DEC-384 extension) | ✅ CLEAR |
| Stage 2 Pass 2 | FIX-03 (main.py lifecycle — biggest session of campaign to date) | ✅ CONCERNS → RESOLVED in-session |
| **Stage 2 Pass 3** | **FIX-12 + FIX-19 + FIX-21 (parallel)** | ✅ **ALL CLEAR** |
| Stage 3 | FIX-04 (Rule-4 serial, order_manager.py) + FIX-16 + FIX-14 | ⏸ PENDING |
| Stage 4 | FIX-05 (core: orchestrator+risk+regime) + FIX-18 + FIX-10 | ⏸ PENDING |
| Stage 5 | FIX-06 (data) + FIX-07 (intelligence) | ⏸ PENDING |
| Stage 6 | FIX-08 solo | ⏸ PENDING |
| Stage 7 | FIX-09 solo | ⏸ PENDING |
| Stage 8 | FIX-13 + IMPROMPTU-01 (LIVE OK parallel) | ⏸ PENDING |
| Stage 9A | IMPROMPTU-02 scoping (read-only) | ⏸ PENDING |
| Stage 9B | IMPROMPTU-02 fix (weekend-only) | ⏸ PENDING |

---

## Session history (Stage 1 + Stage 2)

| Session | Commit(s) | Self-assessment | Tier 2 verdict | Test delta | Notes |
|---|---|---|---|---|---|
| FIX-00 (doc-sync obsoletes) | `bac4c06` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-15 (supporting docs) | `9dd44f2` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-17 (.claude/rules refresh) | `451b444` | MINOR_DEVIATIONS | CLEAR | 0 | Stage 1 |
| FIX-20 (sprint runner) | `9737e52` + submodule `942c53a` | MINOR_DEVIATIONS | CLEAR | +0 | Stage 1; disk-full recovery (ENOSPC) |
| FIX-01 (catalyst DB + DEC-384) | `59bb100` | MINOR_DEVIATIONS | CLEAR | +11 | Stage 1; crisis recovery — initial FLAGGED turned out to be stash misread |
| FIX-11 (backend API) | `fc7eb7c` | MINOR_DEVIATIONS | CONCERNS (accepted) | net -2 | Stage 1; lifespan extraction + dev mode retirement |
| Stage 1 sweep | `f3b0464` | CLEAN | CLEAR | 0 | Doc cleanup + DEF logging |
| FIX-02 (overflow.yaml via DEC-384) | `9454df5` + `b23459b` | CLEAN | CLEAR | +3 | Stage 2 Pass 1; first registry extension |
| FIX-03 (main.py lifecycle) | `80af45b` + strikethrough follow-up + `3ad46fa` | MINOR_DEVIATIONS | CONCERNS → RESOLVED | -1 (intentional deletions) | Stage 2 Pass 2; 31 findings, main.py shrunk 2,469 → 2,291 lines |
| FIX-21 (ops cron) | `8ccac67` + `3a6c71d` | CLEAN | CLEAR | 0 (docs-only) | Stage 2 Pass 3 |
| FIX-19 (strategies) | `a2c2512` + `e60cb47` | MINOR_DEVIATIONS | CLEAR | +18 | Stage 2 Pass 3 |
| FIX-12 (frontend) | `db2818b` + `f57a965` | MINOR_DEVIATIONS | CLEAR | Vitest +13 | Stage 2 Pass 3 |

Baseline progression: 4,934 (pre-campaign) → 4,858 (actual pytest at campaign start after FIX-03's CLAUDE.md strikethrough) → 4,944 (post-FIX-11) → 4,946 (post-FIX-02) → **4,964 (post-Stage-2)**. Vitest: 846 → **859**.

---

## DEF register (sprint-campaign-scoped items)

### Resolved this campaign

| DEF # | Description | Session | Commit |
|---|---|---|---|
| DEF-034 | `SessionResult.review_verdict` Pydantic warning | FIX-20 | `9737e52` |
| DEF-048 + 049 | `test_main.py` env leak (autouse fixture applied; remaining isolation failure is pre-existing, out of DEF-046 pattern scope) | FIX-03 | `80af45b` |
| DEF-074 | Dual regime recheck path consolidation | FIX-03 | `80af45b` |
| DEF-082 | `CatalystStorage` pointed at `argus.db` instead of `catalyst.db` | FIX-01 | `59bb100` |
| DEF-093 | `main.py` duplicate orchestrator YAML load + `_latest_regime_vector` typing | FIX-03 | `80af45b` |
| DEF-097 | Monthly cache update cron (`populate_historical_cache.py --update`) | FIX-21 | `8ccac67` |
| DEF-142 | `quality_engine.yaml` / `system*.yaml` drift | FIX-01 (via DEC-384) | `59bb100` |
| DEF-162 | Monthly re-consolidation cron (`consolidate_parquet_cache.py --resume`) — paired with DEF-097 | FIX-21 | `8ccac67` |

### Partially resolved

| DEF # | Description | Status | Owner |
|---|---|---|---|
| DEF-167 | Vitest hardcoded-date decay | PARTIAL (FIX-11 addressed some; broader sweep pending) | FIX-13 (Stage 8) |

### Open with planned owner

| DEF # | Description | Priority | Owner |
|---|---|---|---|
| DEF-168 | `docs/architecture.md` API catalog drift | LOW | P1-H1a (not yet scheduled as FIX-NN) |
| DEF-169 | `--dev` mode retired (informational only) | INFO | Ongoing (no owner needed) |
| DEF-170 | VIX regime calculators inert in production (RegimeClassifierV2 built pre-VIX; `attach_vix_service` doesn't rewire calculators) | MEDIUM | **FIX-05 (Stage 4)** |
| DEF-171 | `test_all_ulids_mapped_bidirectionally` xdist flake | LOW | **FIX-13 (Stage 8)** |
| DEF-174 | Tauri desktop wrapper never integrated; `platform.ts` deleted as misleading dead code | LOW / opportunistic | Deferred (only if desktop packaging becomes a requirement) |

### Open with NO NATURAL OWNER — gap to resolve

| DEF # | Description | Priority | Blocker |
|---|---|---|---|
| **DEF-172** | Duplicate `CatalystStorage` instances — close-path symmetry restored by FIX-03; full dedup requires `argus/api/server.py` lifespan consolidation | LOW | Requires `argus/api/server.py` lifespan session. FIX-11 (Stage 1) already consumed that scope and is closed. No Stage 2–8 session has this file in scope. |
| **DEF-173** | `LearningStore.enforce_retention()` never called — `ExperimentStore` side wired by FIX-03; `LearningStore` constructed in `argus/api/server.py` lifespan | LOW | Same as DEF-172. |

**Recommended resolution paths** (decide at Stage 3 gate):
- **Option A (preferred):** Schedule a 30-min impromptu session between Stage 3 and Stage 4 covering only `argus/api/server.py` lifespan — closes both DEFs together.
- **Option B:** Verify whether IMPROMPTU-02 (Stage 9B) scope organically touches api/server.py. If yes, bundle there.
- **Option C:** Accept as long-lived open DEFs, close as post-campaign work.

---

## DEC register (this campaign)

| DEC # | Description | Session(s) | Status |
|---|---|---|---|
| DEC-384 | `load_config()` standalone YAML overlay (Option B); `_STANDALONE_SYSTEM_OVERLAYS` registry in `argus/core/config.py` | FIX-01 (landed), FIX-02 (first extension with `overflow.yaml`) | ✅ LANDED |

---

## Outstanding code-level items (not DEF-tracked)

Items too small/cosmetic to promote to DEF, but worth surfacing at the appropriate session kickoff:

| Item | Location | Severity | Target pickup |
|---|---|---|---|
| `TestOverflowConfigYamlAlignment` no-op after system.yaml overflow removal | `tests/intelligence/test_config.py` | INFO | FIX-13 test-hygiene (Stage 8) |
| RSK-NEW-5 dangling reference in two AI module comments | `argus/ai/conversations.py`, `argus/ai/usage.py` | LOW | FIX-07 intelligence (Stage 5) — candidate |
| Cosmetic X1–X6 (sprint/DEC/AMD archaeology comments) | `argus/main.py` | INFO | Future comment-only pass |
| `tests/test_main.py` stale mocks (DEF-049 isolation — pre-existing, covers older subsystems) | `tests/test_main.py` | INFO | Broader refresh unlikely before FIX-13 |
| `populate_historical_cache.py` `CANDIDATE_CACHE_DIRS` LaCie legacy entries | `scripts/populate_historical_cache.py:70-75` | INFO | Opportunistic when that script is next touched |
| Shadow-variant badge rendering (`strat_dip_and_rip__v2_*`/`v3_*` still greyed out) | `argus/ui/src/utils/strategyConfig.ts` + `Badge.tsx` | LOW | New DEF if operator wants a slot; else opportunistic |
| 5 remaining DEF-138 rejection-reason labels (`chase_protection`, `volume_insufficient`, `quality_below_threshold`, `terminal_state`, `max_positions`) | Various strategy files | LOW | Sprint 33+ observability |
| M03/M05/M06 frontend primitive migration (~35 useQuery callers / ~10 error-UI sites / ~15 skeleton sites) | `argus/ui/src/` | INFO | Opportunistic during future page touches |
| Audit spec-prompt file-path drift posture (FIX-12 had `.ts` vs `.tsx` systemic drift; FIX-19 had `Throughout` + wildcard entries) | `docs/audits/audit-2026-04-21/phase-3-prompts/` | INFO | Ongoing — verify targets in every kickoff |

---

## Campaign-wide process notes and learnings

**Parallel execution risk profile (Pass 3 findings)**
1. **c3bc758 chimera incident.** During Pass 3, FIX-19's session momentarily created an intermediate commit that swept FIX-12's working-tree edits under a FIX-19 label. The session reset it locally before pushing; never touched origin. Outcome clean, but margin was thinner than desired. Future parallel batches should add a hard pre-commit `git diff --name-only --cached` check against declared scope.
2. **Working-tree noise contaminates pytest re-runs during review.** FIX-21's reviewer ran pytest 3 times with (1, 15, 13) failures respectively, all explained by concurrent uncommitted FIX-19 test work. Resolution: `git stash -u` + re-run → clean. For campaign post-mortem: reviewer skills should default to `git stash -u` before pytest when working tree is dirty, restore after.
3. **Rule of thumb:** Docs-only sessions parallelize freely. Code sessions on shared high-value paths must serialize. File-disjoint code sessions can parallelize with caveats above.

**Kickoff prompt hygiene**
- **Path drift:** Audit prompts predate some file reorganizations (FIX-20 `models.py` → `state.py`; FIX-12 `.ts` vs `.tsx`; FIX-19 "Throughout" + wildcard entries). Always grep-verify file paths before editing.
- **Baseline staleness:** Every FIX-NN prompt says "Expected baseline: 4,934". Campaign has moved past this baseline repeatedly; kickoffs must correct with current HEAD baseline.
- **DEF naming collisions:** Audit uses DEF-NNN labels internally that may or may not correspond to CLAUDE.md-tracked DEFs. FIX-19's "DEF-138 scope" is audit-internal; CLAUDE.md's DEF-138 is a different Sprint 32.8 item. Kickoffs should disambiguate explicitly.

**Review mechanism reliability**
- FIX-03 got CONCERNS verdict exclusively because reviewer grep-verified CLAUDE.md DEF-074/093 strikethroughs that close-out claimed were present. This catch is load-bearing; all future sessions must grep-verify DEF strikethroughs before commit.
- Tier 2 review catches what Tier 1 self-review misses. Keep the pair.

**Structural patterns to preserve**
- FIX-01's DEC-384 registry pattern (`_STANDALONE_SYSTEM_OVERLAYS` in `argus/core/config.py`) is the canonical standalone-overlay pattern. Extend via tuple entry + flat bare-fields YAML (not wrapped). FIX-02 was the first extension.
- FIX-12's helper-export pattern (`getStrategyLetter(id)`, `getStrategyShortName(id)`) over consumer-side derivation is the canonical single-source-of-truth pattern for frontend config consolidation.
- FIX-19's legacy alias layer (`STRATEGY_LEGACY_ALIASES` in `strategyConfig.ts`) is the canonical pattern for supporting old bare short IDs (`'orb'` → `'strat_orb_breakout'`) without hardcoding a second map.

---

## Stage 3 preview

Per STAGE-FLOW.md:

| Session | Scope | Safety | Parallelism |
|---|---|---|---|
| FIX-04 | `argus/execution/order_manager.py` cleanup | weekend-only | Rule-4 serial (solo) |
| FIX-16 | TBD — need to read prompt | TBD | TBD |
| FIX-14 | TBD — need to read prompt | TBD | TBD |

**Recommended order:** FIX-04 solo first (Rule-4 serial; unlocks IMPROMPTU-02 scoping). Read FIX-16 and FIX-14 prompts after FIX-04 lands; decide parallelism based on file-overlap analysis.

**Pre-Stage-3 decisions needed:**
1. Handle DEF-172 + DEF-173 via impromptu session before Stage 3? (Option A from above.)
2. Kick off FIX-04 immediately, or pause for operator rest?

---

## Snapshot maintenance protocol

This document is the external survival buffer for the campaign state. **Update at every stage barrier** (ideally as the last step before closing a stage):

1. Edit this file in `docs/sprints/sprint-31.9/RUNNING-REGISTER.md`
2. Update `Last updated`, `Campaign HEAD`, baseline tests at top
3. Update the Stage status table
4. Add rows to Session history for any new sessions
5. Move DEFs between register sections as status changes
6. Commit with message `docs(sprint-31.9): update running register — <stage>`

The goal is that anyone (or any fresh Claude.ai conversation) can read this file and know exactly where the campaign stands without reading every prior close-out and review document.

**Hydration pattern for a fresh Claude.ai conversation:** paste this file contents + attach the most recent FIX-NN close-out and review — that plus project knowledge is enough to resume.
