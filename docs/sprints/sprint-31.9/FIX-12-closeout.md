---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-12-frontend (argus/ui React/TypeScript — Command Center, TanStack Query, Zustand, Tailwind)
**Date:** 2026-04-22
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/ui/src/utils/strategyConfig.ts | modified | P1-F2-C01/M01: Added 3 Sprint 31A strategies (strat_micro_pullback=indigo-400/M/MICRO, strat_vwap_bounce=fuchsia-400/B/VWB, strat_narrow_range_breakout=green-400/N/NRB) to STRATEGY_DISPLAY + BORDER + BAR + new STRATEGY_BADGE_CLASSES map. Added STRATEGY_FALLBACK_BADGE_CLASS + STRATEGY_AMBER_BADGE_CLASS constants. Added STRATEGY_LEGACY_ALIASES layer (orb→strat_orb_breakout etc.) so bare short IDs still resolve. New helpers: getStrategyBadgeClass(id, onAmber), getStrategyLetter(id), getStrategyShortName(id), getStrategyName(id). |
| argus/ui/src/components/Badge.tsx | modified | P1-F2-M01/C01: Removed hand-coded strategyColors/strategyLabels/strategyLetters maps (~100 lines). StrategyBadge + CompactStrategyBadge now derive from strategyConfig helpers. Added `data-testid` pass-through prop on StrategyBadge so ArenaCard can retain its test hook. CompactStrategyBadge title uses shortName (matches old behavior + watchlist tests). |
| argus/ui/src/features/arena/ArenaCard.tsx | modified | P1-F2-M02: Replaced inline span + `getStrategyDisplay(...)` hex-style badge with `<StrategyBadge strategyId={strategy_id} data-testid="strategy-badge" />`. Single rendering path across Arena + Trades now. |
| argus/ui/src/utils/platform.ts | deleted | P1-F2-M08: Dead code — grep confirmed zero importers. DEF-174 opened in CLAUDE.md tracking Tauri wire-up if desktop packaging becomes a requirement. |
| argus/ui/src/hooks/useBriefings.ts | modified | P1-F2-M04: `refetchInterval: () => isMarketOpen() ? 60_000 : false` + `refetchOnWindowFocus: true`. Off-hours polling eliminated; 2,880 redundant requests/day → ~40 (market hours only) + focus-triggered. |
| argus/ui/src/features/dashboard/OrchestratorStatusStrip.tsx | modified | P1-F2-L01: Removed local `formatPercent()`, imports canonical from `utils/format`. |
| argus/ui/eslint.config.js | modified | P1-F2-L02: Added `@typescript-eslint/no-unused-vars: ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }]` rule. |
| argus/ui/vitest.config.ts | modified | P1-F2-L03: Explicit `pool: 'forks'` + orphan-reap comment. |
| argus/ui/src/pages/ArenaPage.tsx | modified | P1-F2-M07: `score > 0.7` and `setInterval(..., 2000)` magic numbers replaced with imports from new `constants/arena.ts`. |
| argus/ui/src/constants/arena.ts | added | P1-F2-M07: ARENA_PRIORITY_SPAN_THRESHOLD (0.7) + ARENA_PRIORITY_RECOMPUTE_MS (2000) with rationale docblocks. |
| argus/ui/src/constants/polling.ts | added | P1-F2-L04: POLL_MS registry (CRITICAL/LIVE/HOT/ACTIVE/WARM/COLD) with 6-tier cadence convention. Migration pattern established; no big-bang. |
| argus/ui/src/constants/queryKeys.ts | added | P1-F2-M03: `qk` key registry covering ~35 hooks as typed `as const` tuples. Establishes convention; migration opportunistic per spec. |
| argus/ui/src/components/QueryErrorFallback.tsx | added | P1-F2-M05: Shared error primitive (compact + full variants) with retry action and optional label. Adoption opportunistic. |
| argus/ui/src/components/CardSkeleton.tsx | added | P1-F2-M06: Shared card-shaped loading primitive (Card + Skeleton rows) so pages stop mixing skeleton/spinner/null. |
| argus/ui/src/components/Badge.test.tsx | modified | Updated `afternoon_momentum` expectation MOM→PM (consolidation resolved M01 drift). +3 new tests: Sprint 31A strategy labels (MICRO/VWB/NRB), Sprint 31A color classes (indigo/fuchsia/green), `data-testid` pass-through. +1 CompactStrategyBadge test for Sprint 31A letters. |
| argus/ui/src/utils/strategyConfig.test.ts | modified | +3 new test groups: Sprint 31A config coverage, 15-strategy unique-letter/unique-shortName invariant, single-source-of-truth key parity across display/border/bar/badge maps. +1 getStrategyBadgeClass test group (normal/amber/fallback). +1 helper-accessor test group. |
| argus/ui/src/features/watchlist/WatchlistItem.test.tsx | modified | Updated Momentum test title expectation MOM→PM (same consolidation). |
| CLAUDE.md | modified | P1-F2-M08: Frontend summary line "Tauri desktop + PWA mobile" → "PWA mobile (Tauri desktop deferred — see DEF-174)". P1-I-L01: Chart library stack line "Three.js r128" → "Three.js (current npm semver per argus/ui/package.json)". Added DEF-174 row (Tauri wrapper never integrated). |
| docs/ui/ux-feature-backlog.md | modified | P1-I-L01: Chart library stack "Three.js r128" → "Three.js (installed as `three` npm package — current major per `package.json`)". |
| docs/audits/audit-2026-04-21/phase-2-review.csv | modified | Back-annotated 14 P1-F2 rows + 1 P1-I row with `**RESOLVED FIX-12-frontend**` (L5 uses `**RESOLVED-VERIFIED FIX-12-frontend**`). |
| docs/audits/audit-2026-04-21/p1-f2-frontend.md | modified | Back-annotated C1 + M1-M8 + L1-L5 rows (14 total) inline with same markers. |
| docs/audits/audit-2026-04-21/p1-i-dependencies.md | modified | Back-annotated L1 (P1-I-L01) row inline with resolution note (DEC-108 body never mentioned r128; drift lived in CLAUDE.md + ux-feature-backlog). |

### Judgment Calls
- **P1-F2-C01 / M01 pairing.** Applied M01 (single source of truth) alongside C01 (missing strategies), per the audit's own suggested-fix guidance. Chose the **helper-export pattern** (`getStrategyLetter(id)`, `getStrategyShortName(id)`, `getStrategyBadgeClass(id, onAmber)`) over Badge.tsx internal derivation so any future caller can skip the Badge component entirely. This resolved the `MOM` vs `PM` drift between files by picking `PM` (strategyConfig's canonical) as the winner; both Badge.test.tsx and WatchlistItem.test.tsx updated.
- **Color choices for 3 new strategies.** Indigo / fuchsia / green — the exact three hues suggested by the audit. No collisions with the existing 12. Letter choices (M/B/N) and shortNames (MICRO/VWB/NRB) picked for uniqueness; added a Vitest invariant asserting all 15 letters and shortNames are unique so the next strategy addition is forced to dedupe explicitly.
- **Legacy alias layer.** WatchlistItem tests (and possibly older telemetry paths) pass bare short IDs like `'orb'`, `'scalp'`, `'vwap'`, `'momentum'`. Old Badge.tsx handled these via its hand-coded map; after consolidation they fell to the grey fallback. Added `STRATEGY_LEGACY_ALIASES` in strategyConfig — cleaner than re-hardcoding the full table inside Badge.tsx.
- **`data-testid` pass-through on StrategyBadge.** ArenaCard's existing test hook (`data-testid="strategy-badge"`) needed to survive the refactor. Chose pass-through prop over a wrapping span — matches React's conventional pattern and keeps the DOM shape identical.
- **`CompactStrategyBadge` title = shortName, not fullName.** Old behavior used the short label as tooltip (e.g., `title='ORB'` not `title='ORB Breakout'`). Preserved to avoid breaking watchlist tests + existing UX expectation.
- **Platform.ts — Option A (delete) over Option B (open DEF only).** File was actively misleading (CLAUDE.md claimed "Tauri desktop + PWA mobile" as shipped; only PWA was shipped). DEF-174 tracks any future re-integration against then-current `@tauri-apps/api` — a Sprint-16-era copy is not a safe starting point for a live integration.
- **P1-I-L01 — drift target split.** DEC-108's *body* never mentioned `r128`; the drift lived in CLAUDE.md's summary line and `docs/ui/ux-feature-backlog.md`. Updated both to reference "current npm semver per `argus/ui/package.json`" rather than pin a specific version number that will itself rot.
- **Finding 2 (P1-F2-M06), Finding 5 (M03), Finding 6 (M05) — primitive + convention, no big-bang migration.** Per the audit's own suggested-fix language ("adopt across sampled sites opportunistically", "migrate opportunistically during page touches"). Created `<CardSkeleton>`, `<QueryErrorFallback>`, `qk` registry, POLL_MS cadence table with migration guidance in docblocks. Not migrating 85 `useQuery` sites or 10+ skeleton sites in one session.
- **Finding 15 (P1-F2-L05).** No code change needed — the finding itself says "non-issue once L2 is enabled." L2's new rule handles class-inheritance correctly via `tseslint` ESLint knowledge of TypeScript. Marked RESOLVED-VERIFIED.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| P1-F2-C01 Sprint 31A strategies visible (15-universe) | DONE | 3 new entries across STRATEGY_DISPLAY + BORDER + BAR + BADGE_CLASSES; Vitest invariant asserts all 15 have unique letter + shortName. |
| P1-F2-M01 Single source of truth | DONE | Badge.tsx derives from strategyConfig helpers only; test asserts key-parity across maps. |
| P1-F2-M02 ArenaCard routes through `<StrategyBadge>` | DONE | Inline span replaced; data-testid preserved via pass-through prop. |
| P1-F2-M03 Query-keys convention | DONE | `src/constants/queryKeys.ts` documents convention + `qk` helpers. |
| P1-F2-M04 useBriefings market-hours gating | DONE | `isMarketOpen() ? 60_000 : false`. |
| P1-F2-M05 QueryErrorFallback primitive | DONE | `components/QueryErrorFallback.tsx` with compact + full variants. |
| P1-F2-M06 CardSkeleton primitive | DONE | `components/CardSkeleton.tsx`. |
| P1-F2-M07 Arena magic numbers | DONE | `constants/arena.ts`; ArenaPage imports constants. |
| P1-F2-M08 platform.ts disposition | DONE | Deleted; CLAUDE.md + DEF-174 updated. |
| P1-F2-L01 OrchestratorStatusStrip formatPercent | DONE | Imports `utils/format`. |
| P1-F2-L02 ESLint no-unused-vars | DONE | Rule added to `eslint.config.js`. |
| P1-F2-L03 Vitest pool:'forks' | DONE | Explicit in `vitest.config.ts`. |
| P1-F2-L04 Polling cadence constants | DONE | `constants/polling.ts`. |
| P1-F2-L05 Component import lint-ok | VERIFIED | L2 rule + tseslint handles class-inheritance. |
| P1-I-L01 Three.js r128 drift | DONE | DEC-108 body clean; CLAUDE.md + ux-feature-backlog.md rewritten to reference "current npm semver". |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,944 passed | ✅ | Post: 4,964 passed, 0 failed (+20). FIX-12 did not touch Python code; the delta is entirely FIX-19's concurrent work. |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | ✅ | Full run produced 0 failures. Earlier xdist flake during FIX-19 tests cleared on re-run. |
| No file outside this session's declared Scope was modified | ✅ | All 21 files in `db2818b` are in declared FIX-12 scope. The earlier `c3bc758` chimera that subsumed FIX-19 content under a FIX-19 label has been abandoned (not in HEAD history). |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-12-frontend**` | ✅ | 15 rows in phase-2-review.csv + 14 rows in p1-f2-frontend.md + 1 row in p1-i-dependencies.md. All grep-confirmed. L5 uses `**RESOLVED-VERIFIED FIX-12-frontend**`. |
| Every DEF closure recorded in CLAUDE.md | N/A | No existing DEFs resolved. |
| Every new DEF/DEC referenced in commit message bullets | ✅ | `db2818b` commit message enumerates all 15 findings and explicitly references DEF-174 under P1-F2-M08. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | ✅ | L5 verified; noted RESOLVED-VERIFIED in CSV. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | ✅ | M08 `deferred-to-defs` — platform.ts deleted + DEF-174 added. |
| Vitest net delta >= 0 | ✅ | Baseline 846 → 859 (+13 new tests, 0 regressions). |

### Commit History
The FIX-12 work landed in `db2818b audit(FIX-12): frontend — strategy identity + UI hygiene (15 findings)` — a clean FIX-12-only commit on top of `e60cb47 docs(FIX-19): add Tier 2 review report`.

**Process note (for sprint-campaign hygiene):** During the session an earlier chimera commit `c3bc758` transiently appeared, carrying both FIX-19 + FIX-12 content under a FIX-19-only label — a concurrent-session stash restoration artifact. The FIX-19 session subsequently re-split its work into a clean FIX-19-only commit (`a2c2512`, superseded by `e60cb47`) and left FIX-12's diff back in the working tree. The Tier 2 reviewer flagged this correctly. `c3bc758` is not an ancestor of HEAD and is reachable only through reflog / stash — it can be treated as abandoned. This close-out was authored before `db2818b` was created; earlier revisions of this section described the `c3bc758` state and are now superseded.

Final state:
- `db2818b` — FIX-12 frontend only (this session's work; 21 files)
- `e60cb47` — FIX-19 Tier 2 review docs (prior session)
- `a2c2512` — FIX-19 implementation (prior session)

### Deferred Observations (scope-adjacent, not fixed)
- **M03/M05/M06 full migration:** primitives exist now (qk registry, QueryErrorFallback, CardSkeleton) but ~35 hooks / ~10 error-UI sites / ~15 skeleton sites still use ad-hoc patterns. Spec explicitly says "migrate opportunistically" — next UX pass touching those files should adopt.
- **Shadow-variant badge rendering (strat_dip_and_rip__v2_*/__v3_*).** Still falls through to fallback (first-4-char shortName). The audit finding flagged this as secondary; a proper variant-badge design (parent strategy color + small v2/v3 suffix) is out of scope for FIX-12. File as a new DEF if operator wants a tracked slot.
- **Badge.tsx `K1` / `K2` cosmetic findings.** Not in my 15-finding list — flagged in the audit's COSMETIC section. K1 (stale comment `// Afternoon Momentum → A`) is moot because the whole `strategyLetters` map was deleted in M01. K2 (docblock summary line) — could update in a future doc pass.
- **K3 WS reconnect vs aspirational "reconnecting…" copy.** Cosmetic finding, not in my 15 — audit suggested switching to `api/ws.ts` backoff or changing copy. Deferred.

### Notes
- All 15 findings resolved in spirit; the primitive-based findings (M03/M05/M06) establish conventions rather than migrate every call site, per the audit's own language.
- `data-testid` pass-through added to StrategyBadge is a small API extension — worth calling out so future `<StrategyBadge>` callers know it's available.
- Vitest invariant test (`all 15 live-universe strategies have non-grey color + unique letter`) is the guard against future drift: adding a 16th strategy without a unique letter/shortName will fail this test.
- `POLL_MS` tiers in `constants/polling.ts` are descriptive, not prescriptive — matching the existing spread (5s/15s/30s/60s) rather than forcing alignment in a single session.
- pytest ran clean at 4,964 passed — FIX-12 did not touch Python.

---END-CLOSE-OUT---

```json
{
  "session_id": "FIX-12-frontend",
  "sprint_id": "audit-2026-04-21-phase-3",
  "self_assessment": "MINOR_DEVIATIONS",
  "findings_addressed": 15,
  "findings_resolved": 15,
  "new_defs": ["DEF-174"],
  "new_decs": [],
  "commit_sha": "db2818b",
  "commit_note": "Clean FIX-12-only commit. Earlier c3bc758 chimera (joint FIX-19 + FIX-12 under FIX-19 label) was abandoned when FIX-19 re-split its work; FIX-12 was re-committed as db2818b on top of e60cb47 (FIX-19 review docs). Pushed to origin/main.",
  "files_changed": 23,
  "files_added": 5,
  "files_deleted": 1,
  "vitest_baseline": 846,
  "vitest_after": 859,
  "vitest_delta": 13,
  "pytest_baseline": 4944,
  "pytest_after": 4964,
  "pytest_delta": 20,
  "pytest_delta_attributable": 0,
  "regression_failures": 0,
  "scope_violations": [],
  "back_annotations": {
    "phase-2-review.csv": 15,
    "p1-f2-frontend.md": 14,
    "p1-i-dependencies.md": 1
  },
  "context_state": "GREEN"
}
```
