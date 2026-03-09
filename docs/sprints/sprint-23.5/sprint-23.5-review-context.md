# Sprint 23.5: Review Context File

This file is shared across all Tier 2 review prompts. It contains the full Sprint Spec, Specification by Contradiction, Regression Checklist, and Escalation Criteria. Individual review prompts reference this file by path rather than duplicating this content.

---

## Review Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end, fenced with ```json:structured-verdict. See the review skill for the full schema and requirements.

---

## Sprint Spec

### Sprint 23.5: NLP Catalyst Pipeline

**Goal:** Build the NLP Catalyst Pipeline — ARGUS's first intelligence module. Ingest news and filings from SEC EDGAR, FMP, and Finnhub; classify catalyst quality via Claude API with dynamic batch sizing; emit CatalystEvents on the Event Bus; generate pre-market intelligence briefs; and surface catalysts in the Command Center (Dashboard badges, Orchestrator alert panel, Debrief intelligence brief view). Config-gated with default disabled for backward compatibility.

**Deliverables:**
1. CatalystEvent + data models + Pydantic config (intelligence module foundation)
2. CatalystSource ABC + 3 client implementations (SEC EDGAR, FMP News, Finnhub)
3. CatalystClassifier (Claude API batch classification, dynamic sizing, fallback, cache, cost ceiling)
4. CatalystPipeline + storage (source→classify→store→publish pipeline, SQLite tables)
5. REST API endpoints (catalysts by symbol, recent, briefings CRUD)
6. BriefingGenerator (Claude-powered narrative, 5 sections, stored to Debrief)
7. Dashboard catalyst badges (colored pills on watchlist entries)
8. Orchestrator catalyst alert panel (scrolling feed with quality scores)
9. Debrief Intelligence Brief view (markdown rendering, date navigation)

**Config Changes:** 14 new fields under `catalyst.*` namespace in system.yaml, all mapping to CatalystConfig Pydantic model. Default: `catalyst.enabled: false`.

**Key Constraints:**
- DEC-164: Free sources first (SEC EDGAR, FMP Starter, Finnhub free)
- DEC-098: Claude Opus for all API calls
- DEC-170: AI layer strict separation — never modify strategies, Risk Manager, Orchestrator
- DEC-274: Per-call cost tracking via UsageTracker
- DEC-029: Event Bus sole streaming mechanism

---

## Specification by Contradiction

**Out of Scope:**
1. Automated PreMarketEngine scheduler (Sprint 24)
2. SignalEvent enrichment with catalyst data (Sprint 24)
3. Dynamic position sizing (Sprint 24)
4. Real-time sub-second news processing
5. Finnhub WebSocket
6. Intraday catalyst re-scanning with Databento subscription adds
7. FMP plan upgrade
8. SEC EDGAR full-text filing analysis
9. Catalyst-driven Orchestrator behavior changes
10. CatalystEvent subscribers (no component subscribes in this sprint)

**Do NOT Modify:** `argus/ai/*`, `argus/strategies/*`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/*`, `argus/data/universe_manager.py`, `argus/data/fmp_scanner.py`, `argus/data/fmp_reference.py`, `argus/data/databento_data_service.py`, `argus/analytics/*`

**Do NOT Add:** Event Bus subscribers for CatalystEvent. WebSocket endpoint for catalyst streaming. AI Copilot integration with catalyst data.

**Edge Cases to Reject:** Symbol not in viable list (return empty). CIK not found (skip SEC source). Malformed Claude response (fallback classifier). Cost ceiling reached (queue unclassified). Duplicate headlines (dedup by hash). No catalysts for brief (generate "no catalysts" message). Extremely long headline (truncate to 500 chars).

---

## Sprint-Level Regression Checklist

### Core System Integrity
- R1: All existing 2,101+ pytest tests pass: `python -m pytest tests/ -x -q`
- R2: All existing 392+ Vitest tests pass: `cd argus/ui && npx vitest run`
- R3: No modifications to protected files (check `git diff --name-only`)
- R4: No CatalystEvent subscribers registered (`grep -r "subscribe.*CatalystEvent"`)
- R5: Event Bus behavior unchanged — CatalystEvent is additive only
- R6: Ruff linting passes: `ruff check .`

### Config Integrity
- R7: Config YAML↔Pydantic match test passes (no silently ignored keys)
- R8: System operates identically with `catalyst.enabled: false`
- R9: Missing API key degradation works (each source independently disableable)

### API Integrity
- R10: Existing API endpoints unchanged
- R11: JWT authentication on all new endpoints
- R12: Correct error codes (empty list for no catalysts, 404 for missing brief)

### AI Layer Integrity
- R13: AI Copilot fully functional — no modifications to `argus/ai/`
- R14: UsageTracker integration for classifier costs
- R15: Daily cost ceiling enforcement

### Data Integrity
- R16: Universe Manager read-only consumption
- R17: FMP Scanner independent (different class, different endpoints, no shared state)
- R18: SQLite tables isolated from existing tables

### Frontend Integrity
- R19: Dashboard existing panels unchanged
- R20: Orchestrator existing panels unchanged
- R21: Debrief existing tabs unchanged
- R22: No conditional rendering anti-pattern

### Test Coverage
- R23: New test count ≥50 (target ~68)
- R24: All external APIs mocked in tests
- R25: Config validation test exists

---

## Sprint-Level Escalation Criteria

### Automatic ESCALATE
1. Do-not-modify boundary violation
2. CatalystEvent subscriber added (none allowed this sprint)
3. Strategy behavior change detected
4. Existing test regression (2,101 pytest + 392 Vitest)
5. Storage schema conflict with existing AI tables
6. Config namespace collision

### Conditional ESCALATE
7. Classification quality: >30% "other" on 20+ headline sample
8. Cost modeling: >$0.10 per batch of 20 headlines
9. Test count below 50 (target ~68)
10. Session compaction without auto-split
11. SEC EDGAR User-Agent non-compliance
12. Graceful degradation failure

### Runner HALT
13. Live API calls in tests
14. Two consecutive session failures
15. Auto-split sub-session scores 14+
