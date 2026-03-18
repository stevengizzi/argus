# Sprint 25.5: Doc Update Checklist

## Documents to Update After Sprint Completion

- [ ] **`docs/project-knowledge.md`**
  - Sprint history table: add Sprint 25.5 row with test count, date, key DECs
  - Current State: update test count, active sprint, next sprint
  - Key Components > Strategies: note that watchlists are populated from UM routing table when UM enabled
  - Key Components > Universe Manager: note that routing table feeds strategy watchlists (closing the loop on the original intent)

- [ ] **`docs/sprint-history.md`**
  - Add Sprint 25.5 entry with full session details, test delta, and root cause narrative

- [ ] **`CLAUDE.md`**
  - Update test counts
  - Note watchlist wiring fix and health warning addition

- [ ] **`docs/decision-log.md`**
  - New DEC entry: watchlist population from Universe Manager routing (rationale: closing the gap between UM routing and strategy-level gating; list→set conversion for O(1) lookups at 2,100+ symbol scale)
  - New DEC entry: zero-evaluation health warning (rationale: prevent future silent failures where strategies receive candles but don't process them)

- [ ] **`docs/dec-index.md`**
  - Add new DEC entries to the index

- [ ] **`docs/risk-register.md`**
  - Note: the 10-day silent failure (March 7–18) demonstrates the need for pipeline-level health checks beyond component-level status. The zero-eval warning partially addresses this.

## Documents NOT Updated (No Changes)
- `docs/architecture.md` — no architectural changes
- `docs/roadmap.md` — no roadmap changes
- `docs/project-bible.md` — no goal/vision changes
- `docs/live-operations.md` — no operational procedure changes
- Strategy spec sheets — no strategy logic changes
