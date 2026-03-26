# Sprint 27.95 — Work Journal Handoff

> Paste this into a fresh Claude.ai conversation to create the Sprint Work Journal.
> Open this conversation before starting Session 1a and bring issues to it throughout the sprint.

---

## Sprint Context

**Sprint:** 27.95 — Broker Safety + Overflow Routing
**Goal:** Fix reconciliation position-destruction bug, add dynamic overflow routing to CounterfactualTracker, and harden order management failure modes from March 26 market session.
**Execution Mode:** Human-in-the-loop
**Baseline Tests:** ~3,610 pytest + 645 Vitest (0 failures)

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| 1a | Reconciliation redesign (broker-confirmed, miss counter) | — | order_manager.py, config models | 13 |
| 1b | Trade logger reconciliation close fix | — | trade_logger.py | 6.5 |
| 2 | Order mgmt hardening (stop retry cap, revision-rejected, fill dedup) | — | order_manager.py | 12 |
| 4 | Startup zombie cleanup + script chmod | — | main.py/server.py, script, config models | 10 |
| 3a | Overflow config + RejectionStage enum | overflow.yaml | events.py, config models | 10 |
| 3b | Overflow routing in _process_signal() | — | main.py | 11 |
| 3c | Overflow → CounterfactualTracker wiring + integration tests | — | Minimal (counterfactual.py if needed) | 8 |

## Session Dependency Chain
```
1a → 1b → 2 → 4 → 3a → 3b → 3c
```
All sessions depend on 1a. Sessions 1b, 2, and 4 build on the reconciliation redesign. Sessions 3a–3c are the overflow routing chain.

## "Do Not Modify" File List
- `argus/strategies/` — all strategy files
- `argus/backtest/` — BacktestEngine, VectorBT, replay harness
- `argus/ui/` — all frontend files
- `argus/ai/` — AI layer
- `argus/data/` — data service, indicators, universe manager
- `argus/analytics/evaluation.py` — evaluation framework

## Issue Category Definitions
When issues arise during implementation, classify them as:

1. **In-session bug** — Bug in code written during this session. Fix immediately. No DEF needed.
2. **Prior-session bug** — Bug in code from a previous session in this sprint. Fix in current session if small and within scope. Log as DEF if fixing would exceed scope.
3. **Pre-existing bug** — Bug that existed before this sprint. Log as DEF. Do NOT fix unless it blocks sprint work.
4. **Scope gap** — Something the sprint spec didn't account for. If small and critical for the deliverable, fix and note. If large, log as DEF and flag for triage.
5. **Feature idea** — Enhancement that would be nice but isn't in scope. Log as DEF for future consideration.

## Escalation Triggers
Escalate to Tier 3 / halt sprint if:
1. Reconciliation change breaks position lifecycle tests (undocumented coupling)
2. Overflow routing blocks signals that should reach broker
3. `_process_signal()` flow change breaks quality pipeline or risk manager
4. Stop resubmission cap causes unprotected positions
5. Startup flatten closes positions that should be kept
6. Pre-flight test failures not present at sprint entry
7. Test hang (>10 minutes)
8. Signal count divergence after `_process_signal()` modification

## Reserved Number Ranges
- **DEC:** Next available after current max (check `docs/dec-index.md` at sprint start)
- **DEF:** Next available after current max (check `CLAUDE.md` at sprint start)
- **RSK:** No new risks expected; use next available if needed

## Work Journal Responsibilities
Throughout the sprint:
- Track session progress (started, in-progress, complete, review verdict)
- Classify issues as they arise (use categories above)
- Assign DEF numbers for deferred items
- Track DEC numbers for decisions made during implementation
- At sprint close: produce the Work Journal Close-Out (using template from `workflow/templates/work-journal-closeout.md`) and then produce the doc-sync prompt with close-out data embedded

## Key Context from Log Analysis
The following issues were identified from the March 26 market session log (`argus_20260326.jsonl`):
- 371 positions opened, 336 destroyed by reconciliation, 29 normal exits
- First reconciliation wipe: 51 seconds after first entry (60 positions in one wave)
- 303 "no matching position" warnings (real IBKR exits arriving after reconciliation killed position)
- 239 of 336 killed positions later received exit fills from IBKR (proving they were real)
- RDW: 68 stop resubmissions in 50 seconds (infinite retry loop)
- 36 "Revision rejected" bracket amendment failures
- 37 orders with duplicate fill callbacks
- 336 ERROR "Failed to log trade" from reconciliation closes
- 8 zombie RECO positions from prior session (BTU, ADPT, ZURA, QID, YOU, VNDA, INDV, VERA)
- Account went to -$603K available cash (margin blown)
- ORB Scalp: 208 positions, $3.8M total deployed into $935K account
