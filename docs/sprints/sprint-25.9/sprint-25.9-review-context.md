# Sprint 25.9 — Review Context

## Sprint Overview
**Sprint:** 25.9 — Operational Resilience Fixes
**Type:** Impromptu (unplanned operational fixes)
**Origin:** Dead market session March 23 2026 + FMP cache incident same day
**Sessions:** 2
**DEC range:** 360–362

## Sprint Spec (Compact)

### Problem Statement
March 23 2026 exposed two classes of operational failure:
1. **Dead session:** `bearish_trending` regime blocked all 7 strategies simultaneously. Zero evaluations, zero signals, zero trades across 3+ hours of runtime.
2. **Missed market open:** Monday boot with Friday's FMP reference cache triggered a 100-minute full re-fetch. A mid-fetch kill exposed a data-destructive checkpoint bug that overwrote 37,658 cached entries with 7,000 partial entries.

### Scope
- **E1 (DEC-360):** Add `bearish_trending` to all 7 strategies' `allowed_regimes`. Add zero-active-strategy WARNING in Orchestrator.
- **E2:** Regime reclassification results logged at INFO level (currently DEBUG-only when unchanged).
- **E4:** "Watching N symbols" display reflects actual monitored universe when Universe Manager is enabled.
- **B1 (DEC-361):** Cache checkpoint saves merge fresh data into existing cache instead of replacing.
- **B2 (DEC-362):** Trust cache on startup — load cache immediately, refresh stale entries in background. Resolves DEF-063.

### Out of Scope
- B3 (calendar TTL) — moot with B2; 72h config already applied
- E3/DEF-064 (warm-up failures) — only affects mid-session boot; pre-market boot skips warm-up
- E5 (FMP rate limit cascade) — resolves naturally with B2
- A-series (data infrastructure) — separate sprint
- Any UI changes
- Any strategy logic changes beyond allowed_regimes

## Specification by Contradiction

| If we get this wrong... | The consequence is... |
|-------------------------|----------------------|
| E1: Add bearish_trending but break other regime checks | Strategies activate in ALL regimes, bypassing regime filtering entirely |
| E1: Zero-active warning fires spuriously | Log noise during normal operation (e.g., pre-market when no strategies should be active) |
| E2: Regime logging too verbose | Log spam every 5 minutes with unchanged regime values |
| B1: Merge logic wrong — duplicates or drops entries | Cache corruption; worse than current bug |
| B1: Merge doesn't handle concurrent access | Two processes writing cache simultaneously → data loss |
| B2: Background refresh crashes silently | System trades on stale cache indefinitely with no visibility |
| B2: Routing table rebuild during market hours disrupts active strategies | Strategies lose watchlists or get stale routing mid-session |
| B2: trust_cache_on_startup=false doesn't revert to blocking behavior | Config option is a no-op, breaking backward compatibility |

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| All 7 strategies still respond to regime changes | Test: strategy deactivates in a regime NOT in its allowed list |
| Regime filtering still works for non-bearish regimes | Test: strategy with only `bullish_trending` is inactive in `range_bound` |
| Zero-active warning only fires during market hours | Test: no warning during pre-market or post-market phases |
| Cache checkpoint doesn't lose existing entries | Test: partial fetch + checkpoint → original entries still present |
| Cache load at startup is non-blocking when trust=true | Test: startup completes without waiting for FMP API |
| Cache load at startup IS blocking when trust=false | Test: backward-compatible behavior |
| Background refresh task starts and runs | Test: log output shows refresh task lifecycle |
| Background refresh doesn't crash on FMP errors | Test: simulate FMP 429/500 during refresh |
| Routing table swap is atomic | Test: no intermediate state where routing table is empty |
| Full test suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |

## Sprint-Level Escalation Criteria
Escalate to Tier 3 if:
1. Changes to startup sequence (main.py Phases 7–9.5) affect component initialization order
2. Background refresh introduces a new asyncio task lifecycle pattern not used elsewhere in the codebase
3. Cache merge logic requires file locking or cross-process synchronization
4. Any change to Risk Manager, Order Manager, or Event Bus behavior
5. Strategy changes go beyond `allowed_regimes` (e.g., modifying signal logic, entry conditions, position sizing)
