# Sprint 24: Doc Update Checklist

Update after all post-sprint fixes resolve, so test counts are captured in a single pass.

## Architecture (`docs/architecture.md`)

- [ ] Section 3.1 Event Types: Add `pattern_strength`, `signal_context`, `quality_score`, `quality_grade` to SignalEvent definition. Add QualitySignalEvent definition.
- [ ] Section 3.X Intelligence Layer: Update SetupQualityEngine from planned → implemented. Document `score_setup()` interface with actual parameters. Document `record_quality_history()`. Document on-demand catalyst lookup.
- [ ] Section 3.X Intelligence Layer: Update DynamicPositionSizer from planned → implemented. Document `calculate_shares()` interface.
- [ ] Section 3.X Intelligence Layer: Update CatalystPipeline with firehose mode. Document `firehose` parameter on source `fetch_catalysts()`. Document Finnhub general news + SEC EDGAR EFTS changes.
- [ ] Section 3.X Intelligence Layer: Update startup.py with `create_quality_components()` factory.
- [ ] Section 3.X Intelligence Layer: Document quality_history table schema.
- [ ] API Routes section: Add quality endpoints (GET /quality/{symbol}, /quality/history, /quality/distribution).
- [ ] File Structure: Update `argus/intelligence/` to include `quality_engine.py` and `position_sizer.py`.
- [ ] Signal flow diagram: Update to include Quality Engine + Sizer between signal generation and Risk Manager.

## Decision Log (`docs/decision-log.md`)

- [ ] Add DEC-330 through DEC-XXX (all decisions made during Sprint 24)
- [ ] Each DEC with full rationale, alternatives considered, cross-references
- [ ] Update "Next DEC" footer

## DEC Index (`docs/dec-index.md`)

- [ ] Add Phase L section (Setup Quality Engine + Dynamic Sizer)
- [ ] Add all Sprint 24 DEC entries with status indicators

## Risk Register (`docs/risk-register.md`)

- [ ] RSK-057+: Any new risks identified during implementation
- [ ] Update existing RSK-044 (quality scoring differentiation) with Sprint 24 findings
- [ ] Update existing RSK-045 (dynamic sizing amplification) with actual tier configuration

## Project Knowledge (`docs/project-knowledge.md`)

- [ ] Sprint 24 in sprint history table with test counts and key DECs
- [ ] Update "Tests" count
- [ ] Update "Sprints completed" line
- [ ] Update "Active sprint" / "Next sprint" lines
- [ ] Update Build Track Queue (Sprint 24 → complete, Sprint 25 → next)
- [ ] Update Architecture section: mention Quality Engine, Dynamic Sizer, firehose pipeline
- [ ] Update Key Components: add Quality Engine, Position Sizer descriptions
- [ ] Update Key Active Decisions section with Sprint 24 DECs
- [ ] Update Intelligence Layer description with firehose and on-demand

## Sprint History (`docs/sprint-history.md`)

- [ ] Full Sprint 24 entry: scope delivered, session details, test counts, decisions, notes

## Roadmap (`docs/roadmap.md`)

- [ ] Sprint 24 status → ✅ COMPLETE with date and scope summary
- [ ] Phase 5 Gate trigger noted
- [ ] Update velocity baseline if needed
- [ ] Update current state section (test counts, strategies, infrastructure)

## CLAUDE.md

- [ ] Update "Active sprint" → None / next sprint
- [ ] Update "Next sprint" → 25
- [ ] Update test counts
- [ ] Update infrastructure list (add Quality Engine, Dynamic Sizer)
- [ ] Add any new known issues
- [ ] Update project structure section if directory changes

## Sprint Campaign (`docs/sprint-campaign.md`)

- [ ] Sprint 24 status → ✅ COMPLETE with actual session count and notes

## Config Files

- [ ] `config/system.yaml` — quality_engine section present and correct
- [ ] `config/system_live.yaml` — quality_engine section present and correct

## Strategy Spec Sheets (if pattern_strength logic warrants documentation)

- [ ] `docs/strategies/STRATEGY_ORB_BREAKOUT.md` — document pattern strength factors
- [ ] `docs/strategies/STRATEGY_ORB_SCALP.md` — document pattern strength factors
- [ ] `docs/strategies/STRATEGY_VWAP_RECLAIM.md` — document pattern strength factors
- [ ] `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md` — document pattern strength factors

## Project Bible (`docs/project-bible.md`)

- [ ] Section 19 (Setup Quality Engine): Update from planned to implemented, note V1 status with Historical Match stub
- [ ] Section 19.3 (Quality Grades): Confirm grade-to-tier table matches implementation
