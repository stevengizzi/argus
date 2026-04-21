# Fix Session FIX-12-frontend: argus/ui — React/TypeScript frontend

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 15
**Files touched:** `../../argus/ui/package.json`, `Same sample as M5`, ``argus/ui/eslint.config.js``, ``hooks/*.ts` — polling cadence`, ``hooks/*.ts`, `features/*/hooks/*.ts` (~85 `useQuery` call s`, ``hooks/*` — sampled 5 query hooks across pages`, `argus/ui/src/components/Badge.ts`, `argus/ui/src/features/arena/ArenaCard.ts`, `argus/ui/src/features/dashboard/OrchestratorStatusStrip.ts`, `argus/ui/src/hooks/useBriefings.ts`, `argus/ui/src/pages/ArenaPage.ts`, `argus/ui/src/pages/PerformancePage.ts`, `argus/ui/src/utils/platform.ts`, `argus/ui/src/utils/strategyConfig.ts`, `argus/ui/vitest.config.ts`
**Safety tag:** `safe-during-trading`
**Theme:** Frontend findings across React/TypeScript (Command Center pages, TanStack Query hooks, Zustand stores, Tailwind classes).

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Verify paper trading is stable (no active alerts in session debrief).
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK for safe-during-trading"

# This session is safe-during-trading. Code paths touched here do NOT
# affect live signal/order flow. You may proceed during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-12): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `../../argus/ui/package.json`: 1 finding
- `Same sample as M5`: 1 finding
- ``argus/ui/eslint.config.js``: 1 finding
- ``hooks/*.ts` — polling cadence`: 1 finding
- ``hooks/*.ts`, `features/*/hooks/*.ts` (~85 `useQuery` call s`: 1 finding
- ``hooks/*` — sampled 5 query hooks across pages`: 1 finding
- `argus/ui/src/components/Badge.ts`: 1 finding
- `argus/ui/src/features/arena/ArenaCard.ts`: 1 finding
- `argus/ui/src/features/dashboard/OrchestratorStatusStrip.ts`: 1 finding
- `argus/ui/src/hooks/useBriefings.ts`: 1 finding
- `argus/ui/src/pages/ArenaPage.ts`: 1 finding
- `argus/ui/src/pages/PerformancePage.ts`: 1 finding
- `argus/ui/src/utils/platform.ts`: 1 finding
- `argus/ui/src/utils/strategyConfig.ts`: 1 finding
- `argus/ui/vitest.config.ts`: 1 finding

## Findings to Fix

### Finding 1: `P1-I-L01` [LOW]

**File/line:** [argus/ui/package.json:40](../../../argus/ui/package.json#L40) vs [docs/decision-log.md](../../../docs/decision-log.md)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Documentation drift:** DEC-108 mentions Three.js r128 but `package.json` installs `three@^0.183.2`. Either DEC-108 was written before the Three.js migrated to semver (they did, circa r154) and never updated, or the docs are stale. Code is correct.

**Impact:**

> Cosmetic doc drift.

**Suggested fix:**

> Update DEC-108 to reference `three@0.183` or "current major" instead of "r128".

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 2: `P1-F2-M06` [MEDIUM]

**File/line:** Same sample as M5
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Loading states mix Skeleton components (TradesPage, BriefingEditor), spinner overlays (UniverseStatusCard), and silent null (Debrief sub-sections, Observatory views). No shared skeleton system.

**Impact:**

> Project-knowledge lesson from Sprint 17.5: "no conditional skeleton/content swaps — always render same DOM structure." Current mix violates this in places (TradesPage returns a different tree while loading vs loaded).

**Suggested fix:**

> Pick one pattern per component type (cards → skeleton; tables → skeleton rows; charts → ghost axes). Codify in a `<CardSkeleton>` primitive.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 3: `P1-F2-L02` [LOW]

**File/line:** `argus/ui/eslint.config.js`
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> ESLint flat config uses `tseslint.configs.recommended` but does not explicitly enable `no-unused-vars` / `@typescript-eslint/no-unused-vars` as `error`. Unused imports are not caught at lint time.

**Impact:**

> No unused-import regressions detected in this audit's sample, but the guardrail isn't present.

**Suggested fix:**

> Add `'@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }]` to the config.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 4: `P1-F2-L04` [LOW]

**File/line:** `hooks/*.ts` — polling cadence
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `useAccount` refetches every 5s ([hooks/useAccount.ts:18](argus/ui/src/hooks/useAccount.ts#L18)), `usePositions` every 15s ([hooks/usePositions.ts:19](argus/ui/src/hooks/usePositions.ts#L19)), Observatory resources range 5s–60s with no coordination ([features/observatory/hooks/useSymbolDetail.ts](argus/ui/src/features/observatory/hooks/useSymbolDetail.ts)). All are authenticated JWT requests.

**Impact:**

> Steady-state API chatter. Not a correctness issue.

**Suggested fix:**

> Document expected cadence per data type in a central constants file; align where there's no reason for variance.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 5: `P1-F2-M03` [MEDIUM]

**File/line:** `hooks/*.ts`, `features/*/hooks/*.ts` (~85 `useQuery` call sites)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Query-key shape is inconsistent. Examples: `['account']` ([hooks/useAccount.ts:15](argus/ui/src/hooks/useAccount.ts#L15)), `['catalysts', 'symbol', symbol]` ([hooks/useCatalysts.ts:153](argus/ui/src/hooks/useCatalysts.ts#L153)), `['observatory', 'closest-misses', tierKey, date]` ([features/observatory/hooks/useMatrixData.ts:61](argus/ui/src/features/observatory/hooks/useMatrixData.ts#L61)). Some have a domain prefix, some don't. No enforced convention.

**Impact:**

> Makes targeted cache invalidation error-prone — `queryClient.invalidateQueries({ queryKey: ['briefings'] })` will miss anything keyed differently. Not actively broken, but a regression surface as pages grow.

**Suggested fix:**

> Document a keying convention in a query-keys module (e.g., `const qk = { account: () => ['account'] as const, catalystsBySymbol: (s: string) => ['catalysts', 'symbol', s] as const }`), migrate opportunistically during page touches.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 6: `P1-F2-M05` [MEDIUM]

**File/line:** `hooks/*` — sampled 5 query hooks across pages
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Error UI is ad-hoc. `TradesPage.tsx` renders inline red text; `AIInsightCard.tsx`/`UniverseStatusCard.tsx` render custom Error-component subtrees; `DailyPnlCard.tsx` silently returns `null` on error; Observatory views generally render null. No shared error primitive or error boundary at the page level.

**Impact:**

> Inconsistent UX when something fails — some cards show a useful message, others just vanish. Hides real backend issues during a session.

**Suggested fix:**

> Add a shared `<QueryErrorFallback error={e} onRetry={refetch}>` primitive; wrap each page's card grid in an `<ErrorBoundary>`; adopt across sampled sites opportunistically.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 7: `P1-F2-M01` [MEDIUM]

**File/line:** [components/Badge.tsx:28-120](argus/ui/src/components/Badge.tsx#L28) vs [utils/strategyConfig.ts:29-163](argus/ui/src/utils/strategyConfig.ts#L29)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Two independent sources of truth for strategy identity. `Badge.tsx` hardcodes `strategyColors`, `strategyLabels`, `strategyLetters` for 12 strategies; `strategyConfig.ts` duplicates the same metadata for the same 12 with its own color hexes and Tailwind class lists. No imports between them. The maps already disagree — e.g., `Badge.tsx` prints `"MOM"` for afternoon_momentum, `strategyConfig.ts` prints `"PM"`.

**Impact:**

> Silent drift. Any color/label change requires simultaneous edits in both files; missing one produces inter-page inconsistency (see M2). Root cause of C1 — each new strategy needs to be added in 2 places.

**Suggested fix:**

> Pick `strategyConfig.ts` as canonical. Refactor `Badge.tsx` `strategyColors`/`strategyLabels`/`strategyLetters` to derive from `STRATEGY_DISPLAY` (e.g., build lookup maps at module load, keep Tailwind class mappings in the config). Alternatively, export helpers like `getStrategyLetter(id)` from strategyConfig and have Badge.tsx call them.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 8: `P1-F2-M02` [MEDIUM]

**File/line:** [features/arena/ArenaCard.tsx:127-136](argus/ui/src/features/arena/ArenaCard.tsx#L127) vs [features/trades/TradeTable.tsx](argus/ui/src/features/trades/TradeTable.tsx)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> ArenaCard renders the strategy badge inline via `getStrategyDisplay(strategy_id)` with an explicit hex color style; TradeTable/Trade Log renders it via the `<StrategyBadge>` component from `Badge.tsx` (Tailwind class-based). Both derive from different sources (M1), so the same strategy can look different across pages.

**Impact:**

> Visual inconsistency across pages; future color changes only land in one surface.

**Suggested fix:**

> After M1 consolidation, route all badge rendering through one component (`<StrategyBadge>`) and have ArenaCard use it.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 9: `P1-F2-L01` [LOW]

**File/line:** [features/dashboard/OrchestratorStatusStrip.tsx:26-28](argus/ui/src/features/dashboard/OrchestratorStatusStrip.tsx#L26)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Local `formatPercent()` helper defined inline; duplicates `utils/format.ts` `formatPercent`. Divergence risk if global helper changes.

**Impact:**

> Cosmetic; currently both do the same thing.

**Suggested fix:**

> Import from `utils/format` and delete the local copy.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 10: `P1-F2-M04` [MEDIUM]

**File/line:** [hooks/useBriefings.ts:27](argus/ui/src/hooks/useBriefings.ts#L27)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `useBriefings()` polls `/debrief/briefings` every 30s regardless of market hours. Other live-data hooks (`useCatalystsBySymbol`, `useRecentCatalysts`) use `isMarketHours() ? X : false`. This is user-authored journal content that rarely changes — 30s polling outside trading hours is pure overhead.

**Impact:**

> Wasted requests, JWT-authenticated, hitting the API 2880× per day off-hours for no user benefit. Not a correctness issue.

**Suggested fix:**

> Gate on `isMarketHours()` or raise to a much longer interval; briefing list realistically only changes when the user edits it (no push needed).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 11: `P1-F2-M07` [MEDIUM]

**File/line:** [pages/ArenaPage.tsx:99](argus/ui/src/pages/ArenaPage.tsx#L99)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Priority-score threshold for 2-column card spanning is hardcoded: `score > 0.7 ? 2 : 1`. No config or store lookup. The recompute interval (`2000`) on line 106 is also a magic number.

**Impact:**

> If Arena attention tuning moves to config, UI won't pick it up. Low blast radius today (Arena only).

**Suggested fix:**

> Hoist to a `constants/arena.ts` or pull from a future `arena.yaml`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 12: `P1-F2-L05` [LOW]

**File/line:** [pages/PerformancePage.tsx:23](argus/ui/src/pages/PerformancePage.tsx#L23)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `Component` imported from React used only as a class base (line ~69–93 class ChartErrorBoundary), never referenced directly in JSX of the file. Functionally correct but lint-adjacent.

**Impact:**

> None.

**Suggested fix:**

> Non-issue once L2 is enabled with appropriate config — ESLint understands class inheritance usage.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 13: `P1-F2-M08` [MEDIUM]

**File/line:** [utils/platform.ts:10-96](argus/ui/src/utils/platform.ts#L10)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> `isTauri()`/`isPWA()`/platform-detection helpers exist but are not imported anywhere in `argus/ui/src/`. No `@tauri-apps/*` imports, no `invoke()`/`listen()` calls. `CLAUDE.md` still lists "Tauri desktop + PWA mobile" as shipped.

**Impact:**

> Dead or speculative infrastructure. Either Tauri was deferred and should be documented as such, or the helpers are being held for later integration and should be flagged in the deferred-items table. Not broken — just misaligned with stated architecture.

**Suggested fix:**

> Either delete `platform.ts` (and update CLAUDE.md to say "PWA; Tauri deferred") or open a DEF tracking Tauri wire-up.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 14: `P1-F2-C01` [CRITICAL]

**File/line:** [utils/strategyConfig.ts:29-126](argus/ui/src/utils/strategyConfig.ts#L29-L126) + [components/Badge.tsx:16,28-45,83-120](argus/ui/src/components/Badge.tsx#L16)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> The three Sprint 31A strategies — `strat_micro_pullback`, `strat_vwap_bounce`, `strat_narrow_range_breakout` — are NOT registered in either source of strategy identity. Both `STRATEGY_DISPLAY` (strategyConfig.ts) and `strategyColors`/`strategyLabels`/`strategyLetters` (Badge.tsx) stop at 12 strategies. Live universe has 15.

**Impact:**

> Any trade, signal, or Arena card from these strategies renders with the grey fallback (`#6b7280`) and an auto-title-cased name like "Micro Pullback"/letter "M"/shortName "MICR". Visually they look like unknown/unrecognized strategies instead of first-class ones. Affects Dashboard tables, Trade Log badges, Arena cards, Performance breakdowns, Orchestrator signal rows — everywhere a strategy_id is rendered. The 2 Dip-and-Rip shadow variants (`strat_dip_and_rip__v2_*`/`__v3_*`) also fall through to the same grey path.

**Suggested fix:**

> Add three entries to `STRATEGY_DISPLAY`, `STRATEGY_BORDER_CLASSES`, `STRATEGY_BAR_CLASSES`, and the three `Badge.tsx` maps. Pick unused Tailwind hues (e.g., indigo, fuchsia, green). While at it, resolve M1 (single source of truth) so this regression is impossible going forward.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

### Finding 15: `P1-F2-L03` [LOW]

**File/line:** [vitest.config.ts:7-15](argus/ui/vitest.config.ts#L7)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `pool` / `poolOptions` not set — Vitest default is `forks`, but making it explicit prevents silent regressions on Vitest upgrades.

**Impact:**

> None today.

**Suggested fix:**

> Add `pool: 'forks'` explicitly. Optional: add a short comment pointing at `pkill -f "vitest/dist/workers"` for when workers orphan.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-12-frontend**`.

## Post-Session Verification

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Vitest (frontend paths touched)

```bash
cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -10
# Record PASS count: __________
# Net delta: __________ (MUST be >= 0)
```

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-12-frontend** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-12-frontend**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-12): frontend cleanup

Addresses audit findings:
- P1-I-L01 [LOW]: Documentation drift: DEC-108 mentions Three
- P1-F2-M06 [MEDIUM]: Loading states mix Skeleton components (TradesPage, BriefingEditor), spinner overlays (UniverseStatusCard), and silent n
- P1-F2-L02 [LOW]: ESLint flat config uses 'tseslint
- P1-F2-L04 [LOW]: 'useAccount' refetches every 5s ([hooks/useAccount
- P1-F2-M03 [MEDIUM]: Query-key shape is inconsistent
- P1-F2-M05 [MEDIUM]: Error UI is ad-hoc
- P1-F2-M01 [MEDIUM]: Two independent sources of truth for strategy identity
- P1-F2-M02 [MEDIUM]: ArenaCard renders the strategy badge inline via 'getStrategyDisplay(strategy_id)' with an explicit hex color style; Trad
- P1-F2-L01 [LOW]: Local 'formatPercent()' helper defined inline; duplicates 'utils/format
- P1-F2-M04 [MEDIUM]: 'useBriefings()' polls '/debrief/briefings' every 30s regardless of market hours
- P1-F2-M07 [MEDIUM]: Priority-score threshold for 2-column card spanning is hardcoded: 'score > 0
- P1-F2-L05 [LOW]: 'Component' imported from React used only as a class base (line ~69–93 class ChartErrorBoundary), never referenced direc
- P1-F2-M08 [MEDIUM]: 'isTauri()'/'isPWA()'/platform-detection helpers exist but are not imported anywhere in 'argus/ui/src/'
- P1-F2-C01 [CRITICAL]: The three Sprint 31A strategies — 'strat_micro_pullback', 'strat_vwap_bounce', 'strat_narrow_range_breakout' — are NOT r
- P1-F2-L03 [LOW]: 'pool' / 'poolOptions' not set — Vitest default is 'forks', but making it explicit prevents silent regressions on Vitest

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions
- [ ] Commit pushed to `main` with the exact message format above
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-12-frontend**`
- [ ] Vitest suite net delta >= 0
