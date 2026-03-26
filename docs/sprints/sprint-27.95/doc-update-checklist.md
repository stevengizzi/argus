# Sprint 27.95: Doc Update Checklist

## Documents to Update

- [ ] **`docs/project-knowledge.md`**
  - Sprint history table: add Sprint 27.95 row (name, test count, date, DECs)
  - Build Track Queue: mark 27.95 complete
  - Order Manager component description: reconciliation redesign, broker-confirmed tracking, stop retry cap, duplicate fill guard, overflow routing
  - Risk Manager section: note overflow check is downstream of RM
  - CounterfactualTracker section: add BROKER_OVERFLOW stage
  - Active Strategies section: no changes
  - Key Active Decisions: add new DECs
  - Active Constraints: note overflow routing mechanism

- [ ] **`docs/decision-log.md`**
  - New DECs for: reconciliation redesign (broker-confirmed, never auto-close confirmed), overflow routing (capacity-based routing to counterfactual), stop retry cap, bracket revision-rejected handling, duplicate fill dedup, startup zombie flatten, auto_cleanup_unconfirmed default false

- [ ] **`docs/dec-index.md`**
  - Add index entries for all new DECs

- [ ] **`docs/sprint-history.md`**
  - Full Sprint 27.95 entry with session details, scope, key changes

- [ ] **`docs/pre-live-transition-checklist.md`**
  - Add: `overflow.broker_capacity` — review and tune for live account equity
  - Add: `startup.flatten_unknown_positions` — confirm desired behavior for live
  - Add: `reconciliation.auto_cleanup_unconfirmed` — decide if unconfirmed cleanup should be enabled for live
  - Add: `max_stop_retries` — confirm default is appropriate for live latency

- [ ] **`CLAUDE.md`**
  - Update session context with Sprint 27.95 changes

- [ ] **`docs/live-operations.md`**
  - Note startup zombie flatten behavior
  - Note overflow routing and how to monitor (log messages, counterfactual DB)

## Documents NOT Updated (Confirmed No Changes)
- `docs/roadmap.md` — no roadmap changes
- `docs/architecture.md` — no architectural changes (operational fixes within existing architecture)
- `docs/risk-register.md` — no new risks added (existing RSK-022 covers IBKR Gateway)
- `docs/strategies/` — no strategy spec changes
- `docs/ui/ux-feature-backlog.md` — no UI changes
- `docs/amendments/` — no amendment proposals
