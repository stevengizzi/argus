# Sprint 23.6: Doc Update Checklist

Complete after all sessions are done. Each item is a specific update to a specific document.

## Decision Log (`docs/decision-log.md`)

- [ ] **DEC-308:** CatalystPipeline initialization deferred to Sprint 23.6 (not wired in 23.5). Rationale: config-gated activation pattern; components built first, integration second.
- [ ] **DEC-309:** Catalyst data stored in separate `catalyst.db` SQLite file. Rationale: isolation from trading data, independent lifecycle, avoids WAL contention.
- [ ] **DEC-310:** CatalystConfig added to SystemConfig. Rationale: follows AIConfig/UniverseManagerConfig pattern; enables lifespan handler access.
- [ ] **DEC-311:** Post-classification semantic dedup by (symbol, category, time_window). Rationale: reduces duplicate classifications and storage without NLP infrastructure. Configurable window (default 30 min).
- [ ] **DEC-312:** Batch-then-publish ordering in CatalystPipeline. Rationale: data persistence before notification; failed publishes don't lose data.
- [ ] **DEC-313:** FMP canary test at startup. Rationale: early warning for API schema changes (RSK-031 mitigation).
- [ ] **DEC-314:** Reference data file cache for incremental warm-up. Rationale: reduces ~27min warm-up to ~2-5min. JSON file, atomic writes, per-symbol staleness.
- [ ] **DEC-315:** Intelligence polling loop via asyncio task. Rationale: market-hours-aware scheduling, graceful shutdown, symbols from Universe Manager or watchlist.

## DEC Index (`docs/dec-index.md`)

- [ ] Add DEC-308 through DEC-315 with status ACTIVE

## Risk Register (`docs/risk-register.md`)

- [ ] **RSK-031:** Elevate likelihood from MEDIUM to HIGH. Add note: "Materialized in Sprint 23.3. FMP canary test (DEC-313) provides early warning."
- [ ] **RSK-048 (new):** External API concentration risk. MEDIUM likelihood, HIGH impact. Three free/cheap APIs (FMP, Finnhub, SEC EDGAR) for intelligence; FMP single point of failure for Universe Manager + Catalyst news. Mitigation: graceful degradation per source, canary test.

## Deferred Items

- [ ] **DEF-025:** Mark as RESOLVED (reference data cache implemented in Sprint 23.6)
- [ ] **DEF-036:** Confirm still open (intelligence router prefix — not addressed in 23.6)
- [ ] **DEF-039:** Partially resolved (cli.py extracted; further decomposition deferred)
- [ ] **DEF-041 (new):** Fuzzy/embedding-based catalyst dedup. Target: Sprint 28+.
- [ ] **DEF-042 (new):** Conformance check reliability audit (if fallback counter shows frequent failures).

## Project Knowledge (`docs/project-knowledge.md`)

- [ ] Sprint 23.6 entry in Sprint History table
- [ ] Update "Current State" section (test counts, active sprint)
- [ ] Update Architecture > Intelligence Layer subsection with: startup factory, polling loop, reference data cache
- [ ] Update Monthly Costs if any new cost implications
- [ ] Update Active Constraints if warm-up constraint changes

## Architecture (`docs/architecture.md`)

- [ ] Add Intelligence Layer initialization lifecycle (startup factory → lifespan wiring → polling loop)
- [ ] Add reference data cache to Data Service section
- [ ] Add intelligence polling to Event Bus / scheduling section

## Sprint History (`docs/sprint-history.md`)

- [ ] Sprint 23.6 entry with sessions, test deltas, key decisions

## CLAUDE.md

- [ ] Update deferred items (DEF-025 resolved, new DEFs added)
- [ ] Update test count after sprint completion
