# Sprint 28.75: Post-Session Operational + UI Fixes (Impromptu)

**Type:** Impromptu triage (post-market-session findings)
**Urgency:** URGENT — must be resolved before next market session
**Current sprint:** Between sprints (28.5 complete, 29 next planned)
**Sprint sub-number:** 28.75
**Triggered by:** March 30, 2026 market session debrief

---

## Impact Assessment

### What triggered this

The March 30, 2026 market session (first session with Sprint 28.5 exit
management + VIX regime active) revealed:
- Sprint 28.5 trailing stops and exit escalation never fired (0 trail events
  in 820 trades) — likely because `trailing_stop.enabled` was changed from
  `false` to `true` mid-session; ARGUS only loads config at startup
- A flatten-pending market order hung for 2+ hours (SWMR), generating 2,003
  retry log lines
- 80 emergency flattens from stop retry exhaustion
- Multiple frontend display bugs (win rate, closed positions cap, stats freezing)

### Files modified

**Session 1 (Backend):**
- `argus/execution/order_manager.py` — flatten timeout, trail verification, log rate-limiting
- `argus/utils/throttled_logger.py` — may need new throttle keys
- `tests/execution/test_order_manager*.py` — new tests

**Session 2 (Frontend + API):**
- `argus/ui/src/features/dashboard/VixRegimeCard.tsx` — sizing fix
- `argus/ui/src/features/dashboard/TodayStats.tsx` — win rate fix
- `argus/ui/src/features/dashboard/OpenPositions.tsx` — closed tab limit + P&L column
- `argus/ui/src/pages/TradesPage.tsx` — stats fix + Avg R
- `argus/ui/src/features/trades/TradeStatsBar.tsx` — consume new stats endpoint
- `argus/ui/src/hooks/useTrades.ts` — refetchOnWindowFocus
- `argus/api/routes/` — new /api/v1/trades/stats endpoint
- `argus/api/routes/dashboard.py` — win rate investigation

### Regression risk

- **Session 1:** Order Manager changes touch the critical path. Flatten timeout
  adds a cancel+resubmit cycle interacting with `_flatten_pending` guard. Must
  verify guard correctly tracks new order ID after resubmission.
- **Session 2:** Frontend-only (except new API endpoint). No risk to trading engine.

### Conflicts with planned work?

None. Between sprints. Sprint 29 (Pattern Expansion I) has zero file overlap.

### New DEF items

| DEF | Description | Session |
|-----|-------------|---------|
| DEF-111 | Trail stops not firing (config timing) | S1 |
| DEF-112 | Flatten-pending orders hang indefinitely | S1 |
| DEF-113 | "flatten already pending" log spam | S1 |
| DEF-114 | "IBKR portfolio snapshot missing" log spam | S1 |
| DEF-115 | Closed positions tab capped at 50 | S2 |
| DEF-116 | TodayStats win rate 0% | S2 |
| DEF-117 | Trades page stats freeze + filter bug (subsumes DEF-102) | S2 |
| DEF-118 | Avg R missing from Trades page | S2 |
| DEF-119 | Open positions P&L column + colored exit price | S2 |
| DEF-120 | VixRegimeCard fills viewport | S2 |

DEC range reserved: DEC-382 through DEC-384 (may not all be needed).

---

## Compaction Risk Assessment

| Factor | Session 1 | Session 2 |
|--------|-----------|-----------|
| Files created | 1 (test file) → 1pt | 1 (stats route) → 1pt |
| Files modified | 2-3 (OM, config, utils) → 2pt | 6-8 (components, hooks, routes) → 3pt |
| Context reads | 5 (OM, config, exit_math, yaml, CLAUDE.md) → 2pt | 8 (dashboard, trades, components) → 3pt |
| Tests | 7+ new → 2pt | 6+ new → 2pt |
| Integration wiring | Low (within OM) → 1pt | Medium (new API endpoint) → 2pt |
| External API debugging | None → 0pt | None → 0pt |
| Large files | OM is ~2000 lines → 1pt | None → 0pt |
| **Total** | **9 (Medium)** | **11 (Medium)** |

Both sessions within ≤13 Medium threshold. No splitting needed.

---

## Execution Checklist

1. **Create branch:** `git checkout -b sprint-28.75 main`
2. **Create review context:** Copy `sprint-28.75-review-context.md` to
   `docs/sprints/sprint-28.75/review-context.md` in the repo
3. **Run Session 1** (backend fixes) — paste Session 1 prompt into Claude Code
4. **Paste Session 1 close-out + review** back to Work Journal conversation
5. **Run Session 2** (frontend fixes) — paste Session 2 prompt into Claude Code
6. **Paste Session 2 close-out + review** back to Work Journal conversation
7. **Doc sync** — generate and run doc-sync prompt in Work Journal conversation
8. **Merge:** `git checkout main && git merge sprint-28.75`
