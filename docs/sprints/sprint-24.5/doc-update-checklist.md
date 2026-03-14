# Sprint 24.5 — Doc Update Checklist

Documents to update after sprint completion (via doc-sync process).

## Required Updates

- [ ] **`docs/project-knowledge.md`**
  - Add Strategy Telemetry subsection under Architecture (between Quality Engine and Key Components)
  - Update test counts
  - Update sprint history table (add Sprint 24.5 row)
  - Update "Active sprint" / "Next sprint" in Current State
  - Add DEC-342 through DEC-3XX to Key Active Decisions
  - Add DEF-063, DEF-064, DEF-065 if created

- [ ] **`CLAUDE.md`**
  - Update "Active sprint" section
  - Update test counts
  - Update project structure comments (telemetry in strategies/)
  - Add any new DEF entries
  - Note operational fixes completed

- [ ] **`docs/dec-index.md`**
  - Add Phase M header (Strategy Observability, Sprint 24.5)
  - Add all new DEC entries (DEC-342 through DEC-3XX)

- [ ] **`docs/decision-log.md`**
  - Full DEC entries with rationale for each decision

- [ ] **`docs/sprint-history.md`**
  - Sprint 24.5 entry with session list, test delta, DECs

- [ ] **`docs/architecture.md`**
  - Add Strategy Telemetry subsection describing evaluation events,
    ring buffer, persistence, and REST endpoint
  - Note that evaluation events are NOT EventBus events (intentional)

## Conditional Updates

- [ ] **`docs/designs/candle-cache.md`** (if design doc produced in S6)
- [ ] **`docs/risk-register.md`** (if new RSK entries needed)
- [ ] **`docs/ui/ux-feature-backlog.md`** (remove Decision Stream if listed; add deferred items like virtual scrolling)
