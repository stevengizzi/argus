# Sprint 25.6 — Work Journal Handoff

> Paste this into a fresh Claude.ai conversation to create the Sprint 25.6 Work Journal.

---

We are beginning Sprint 25.6 ("Bug Sweep") for ARGUS. This is the Work Journal conversation for tracking session progress, classifying issues, and producing the sprint close-out handoff.

## Sprint Context

**Goal:** Fix all operational bugs discovered during the March 19, 2026 live trading session — the first session after Sprint 25.5 watchlist wiring fix. Nine DEF items (065–073) plus regime stagnation finding and log hygiene.

**Current state:** Sprint 25.5 delivered watchlist wiring fix. March 19 session confirmed full pipeline working (28 trades executed). But uncovered: telemetry DB contention (Observatory unusable, 1.3 GB log bloat), regime never reclassified after startup, multiple Trades/Orchestrator/Dashboard UX issues.

**Test counts at sprint entry:** ~2,765 pytest + ~599 Vitest

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | Telemetry store DB separation + log hygiene (DEF-065/066) | None | telemetry_store.py, main.py, server.py | 12.5 Medium |
| S2 | Periodic regime reclassification | None | orchestrator.py, main.py | 7 Low |
| S3 | Trades page fixes (DEF-067/068/069/073) | None | TradesPage.tsx + hooks | 8 Low |
| S4 | Orchestrator timeline fixes (DEF-070/071) | None | StrategyCoverageTimeline.tsx | 6 Low |
| S5 | Dashboard layout restructure (DEF-072) | None | DashboardPage.tsx + components | 8 Low |
| S5f | Visual review fixes (contingency) | TBD | TBD | TBD |

## Dependency Chain

```
S1 → S2 (both touch main.py)
S3, S4, S5 — independent of each other and of S1/S2
S5f — after S3/S4/S5 visual review
```

Recommended sequence: S1 → S2 → S3 → S4 → S5 → S5f

## Do Not Modify

- `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`
- `catalyst_pipeline.py`, `db/manager.py`
- Strategy files: `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `base_strategy.py`

## Issue Categories

- **Cat 1 (In-session bug):** Bug introduced by the current session's changes. Fix in same session.
- **Cat 2 (Prior-session bug):** Bug from a previous session in this sprint. Fix in next session or defer.
- **Cat 3 (Scope gap):** Missing requirement not in the sprint spec. Evaluate: small enough to absorb, or DEF it.
- **Cat 4 (Feature idea):** Enhancement beyond sprint scope. Always DEF.

## Escalation Triggers

1. DB separation causes data corruption in `argus.db`
2. Regime reclassification unexpectedly excludes strategies
3. Frontend changes require unplanned backend API changes
4. Test count drops by more than 5

## Reserved Numbers

- **DEC:** DEC-345, DEC-346 reserved (DB separation, regime reclassification)
- **DEF:** DEF-074+ available if new deferred items discovered
- **RSK:** No new risk items expected

## My Role

I track issues as they come in from implementation sessions, classify them, assign DEF/DEC numbers, and at sprint close produce the doc-sync handoff with all tracked items embedded.

What session are you kicking off?
