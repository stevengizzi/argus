# Sprint 23.5: Doc Update Checklist

Run doc-sync after all sessions complete and all reviews pass. Every item must be addressed before the sprint is considered complete.

## Architecture Document (`docs/architecture.md`)

- [ ] Section 3.11 Intelligence Layer — Update CatalystService from planned spec to implemented:
  - CatalystPipeline class with source→classify→store→publish pipeline
  - CatalystSource ABC with 3 implementations (SEC EDGAR, FMP News, Finnhub)
  - CatalystClassifier with dynamic batching, fallback, cache, cost ceiling
  - CatalystStorage with catalyst_events and intelligence_briefs tables
  - BriefingGenerator with Claude narrative generation
  - CatalystEvent on Event Bus (published, no subscribers yet)
- [ ] Section 4 API — Add intelligence endpoints (catalysts, briefing) to implemented list
- [ ] Update Module Specifications with actual interfaces (method signatures, event fields)

## Project Knowledge (`docs/project-knowledge.md`)

- [ ] "Current State" — Update test counts, sprint count, active sprint
- [ ] "Sprint History" table — Add Sprint 23.5 row
- [ ] "Build Track Queue" — Update Sprint 23.5 status from NEXT to ✅ COMPLETE
- [ ] "Architecture > Key Components" — Add CatalystPipeline entry under intelligence
- [ ] "Monthly Costs" — Add row for Finnhub (free tier, $0/mo)
- [ ] "Active Constraints" — Add SEC EDGAR rate limit (10 req/sec with User-Agent)
- [ ] "Key Active Decisions" — Add new DEC references

## Decision Log (`docs/decision-log.md`)

New DEC entries to create (reserve DEC-298 through ~DEC-305):
- [ ] DEC-298: Finnhub REST inclusion — free tier supplementary source, REST only (no WebSocket)
- [ ] DEC-299: Dynamic batch classification sizing — Claude decides batch grouping, max_batch_size cap
- [ ] DEC-300: Daily cost ceiling for catalyst classification — $5/day default, UsageTracker enforcement
- [ ] DEC-301: CatalystSource ABC pattern — pluggable data sources, config-driven enable/disable
- [ ] DEC-302: Briefing manual-trigger only — no automated PreMarketEngine in this sprint
- [ ] DEC-303: Config-gated default-disabled — `catalyst.enabled: false`, full backward compatibility
- [ ] DEC-304: Rule-based fallback classifier — keyword matching when Claude API unavailable
- [ ] DEC-305: Headline hash deduplication — SHA-256 of lowercase stripped headline, first source wins

## DEC Index (`docs/dec-index.md`)

- [ ] Add all new DEC entries (DEC-298 through ~DEC-305) under appropriate phase section

## Sprint History (`docs/sprint-history.md`)

- [ ] Add Sprint 23.5 entry with: session count, test count delta, key decisions, scope delivered

## Roadmap (`docs/roadmap.md`)

- [ ] Update Sprint 23.5 entry: status NEXT → ✅ COMPLETE, add delivered scope summary
- [ ] Update Sprint 24 dependencies note: "Sprint 23.5 complete — CatalystPipeline available for Quality Engine integration"
- [ ] Section 13 Command Center Evolution table — Mark Sprint 23.5 UI deliverables as complete (Dashboard catalyst badges, Orchestrator catalyst alert panel, Debrief Intelligence Brief view)
- [ ] Section 4 Velocity Baseline — Update current state test counts

## CLAUDE.md

- [ ] Update test counts
- [ ] Add `argus/intelligence/` to file structure description
- [ ] Add `FINNHUB_API_KEY` to environment variables list
- [ ] Add `catalyst:` config section to configuration notes
- [ ] Note CatalystPipeline in "What's new" section

## Risk Register (`docs/risk-register.md`)

- [ ] RSK-NEW-1: Finnhub free tier reliability — REST API may have stale data (Low likelihood, Low impact — supplementary source)
- [ ] RSK-NEW-2: Claude API classification cost — unpredictable headline volume, mitigated by daily ceiling
- [ ] RSK-NEW-3: SEC EDGAR rate limiting — may block aggressive polling, mitigated by rate limiter + User-Agent

## UX Feature Backlog (`docs/ui/ux-feature-backlog.md`)

- [ ] Mark as complete: Dashboard catalyst badges
- [ ] Mark as complete: Orchestrator catalyst alert panel
- [ ] Mark as complete: Debrief Intelligence Brief view

## Strategy Documentation

- [ ] No changes needed — strategies are not modified in this sprint

## .claude/rules/

- [ ] Review existing rules — no new rules needed for this sprint (intelligence module follows established patterns)
- [ ] Verify `project.md` still accurate after adding intelligence module
