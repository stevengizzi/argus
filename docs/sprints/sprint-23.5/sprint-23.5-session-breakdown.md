# Sprint 23.5: Session Breakdown

## Session Dependency Chain

```
S1 (models/config) → S2 (source clients) → S3 (classifier/storage) → S4 (API/briefing)
                                                                          ├─→ S5 (Dashboard + Orchestrator UI)
                                                                          └─→ S6 (Debrief UI) [parallelizable with S5]
                                                                               └─→ S6f (visual fixes, contingency)
```

---

## Session 1: Foundation — Models, CatalystEvent, Config

**Objective:** Establish the intelligence module foundation — data models, Event Bus event, Pydantic config.

| Column | Value |
|--------|-------|
| **Creates** | `argus/intelligence/__init__.py`, `argus/intelligence/models.py`, `argus/intelligence/config.py` |
| **Modifies** | `argus/core/events.py` (add CatalystEvent), `config/system.yaml` (add `catalyst:` section) |
| **Integrates** | N/A (foundation session) |
| **Parallelizable** | false |

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | +6 |
| Files modified | 2 | +2 |
| Pre-flight context reads | 3 (events.py, existing config, fmp_reference config pattern) | +3 |
| New tests to write | ~6 | +3 |
| Complex integration wiring | 0 | +0 |
| External API debugging | 0 | +0 |
| Large single file (>150 lines) | 0 | +0 |
| **Total** | | **14** |

**Risk level:** High (at threshold). Acceptable because no external APIs, no complex wiring — purely structural.

**Estimated tests:** ~6 (model construction, CatalystEvent fields, config validation, config YAML↔Pydantic match, enabled/disabled gating, default values)

---

## Session 2: Data Source Clients — SEC EDGAR, FMP News, Finnhub

**Objective:** Implement three CatalystSource client implementations for data ingestion.

| Column | Value |
|--------|-------|
| **Creates** | `argus/intelligence/sources/__init__.py` (CatalystSource ABC + CatalystRawItem), `argus/intelligence/sources/sec_edgar.py`, `argus/intelligence/sources/fmp_news.py`, `argus/intelligence/sources/finnhub.py` |
| **Modifies** | (none) |
| **Integrates** | S1 models (CatalystRawItem imported from models.py or defined in sources/__init__.py) |
| **Parallelizable** | false |

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 4 | +8 |
| Files modified | 0 | +0 |
| Pre-flight context reads | 4 (models.py from S1, fmp_reference.py pattern, fmp_scanner.py pattern, events.py) | +4 |
| New tests to write | ~18 | +9 |
| Complex integration wiring | 0 | +0 |
| External API debugging | 3 (SEC EDGAR + FMP + Finnhub — but all mocked in tests) | +3* |
| Large single file (>150 lines) | 1 (sec_edgar.py — CIK mapping + filing parsing) | +2 |
| **Total** | | **26** |

**Risk level:** Critical. However, all three clients follow the same ABC pattern and external APIs are mocked in tests (no live API calls). The +3 for external API debugging is conservative — these are well-documented REST APIs with predictable JSON responses.

**Runner auto-split trigger:** If S2 compacts before close-out, split into:
- S2a: CatalystSource ABC + SEC EDGAR client (~14 points)
- S2b: FMP News + Finnhub clients (~12 points)

**Estimated tests:** ~18 (SEC EDGAR: filing parsing ×2, CIK lookup, rate limit, 404 handling, empty response = 6; FMP News: news parsing ×2, press release parsing, dedup, error handling, empty = 6; Finnhub: news parsing ×2, recommendation parsing, rate limit, error handling, empty = 6)

---

## Session 3: Classifier + Storage + Pipeline Wiring

**Objective:** Build Claude API batch classifier with dynamic sizing, SQLite storage, and wire the full source→classify→store→publish pipeline.

| Column | Value |
|--------|-------|
| **Creates** | `argus/intelligence/classifier.py`, `argus/intelligence/storage.py` |
| **Modifies** | `argus/intelligence/__init__.py` (add CatalystPipeline class wiring sources → classifier → storage → Event Bus) |
| **Integrates** | S1 models + config, S2 source clients → classifier → storage → CatalystEvent publication |
| **Parallelizable** | false |

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | +4 |
| Files modified | 1 | +1 |
| Pre-flight context reads | 6 (models.py, config.py, sources/*.py, ai/client.py, ai/usage.py, events.py) | +6 |
| New tests to write | ~16 | +8 |
| Complex integration wiring | 1 (sources → dedup → classifier → storage → Event Bus) | +3 |
| External API debugging | 1 (Claude API — mocked) | +3 |
| Large single file (>150 lines) | 1 (classifier.py — batch logic + prompt + fallback + cache) | +2 |
| **Total** | | **27** |

**Risk level:** Critical. This is the most integration-dense session. However, the Claude API is mocked in tests and the pipeline wiring follows established patterns (similar to the AI Layer's ActionManager pipeline in Sprint 22).

**Runner auto-split trigger:** If S3 compacts, split into:
- S3a: CatalystClassifier + classification cache (~15 points)
- S3b: CatalystStorage + CatalystPipeline wiring (~12 points)

**Estimated tests:** ~16 (classifier: batch processing ×2, dynamic sizing, 8 categories, quality score range, cache hit, cache miss, fallback classifier, cost ceiling enforcement = 9; storage: CRUD ×4, schema validation, dedup = 5; pipeline: end-to-end wiring, Event Bus publication = 2)

---

## Session 4: API Routes + Briefing Generator

**Objective:** Expose catalyst data via REST endpoints and build Claude-powered pre-market intelligence brief generator.

| Column | Value |
|--------|-------|
| **Creates** | `argus/api/intelligence_routes.py`, `argus/intelligence/briefing.py` |
| **Modifies** | `argus/api/app.py` (register intelligence router), `argus/intelligence/config.py` (add briefing-specific config if needed) |
| **Integrates** | S3 storage → API endpoints; S3 classifier + storage → briefing generator → brief storage |
| **Parallelizable** | false |

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | +4 |
| Files modified | 2 | +2 |
| Pre-flight context reads | 6 (models.py, storage.py, classifier.py, ai/client.py, existing api/app.py, existing route patterns) | +6 |
| New tests to write | ~12 | +6 |
| Complex integration wiring | 1 (storage → API, classifier → briefing → storage) | +3 |
| External API debugging | 1 (Claude API for narrative — mocked) | +3 |
| Large single file (>150 lines) | 0 | +0 |
| **Total** | | **24** |

**Risk level:** Critical on paper, but the two halves (API routes and briefing generator) are loosely coupled — routes are standard FastAPI CRUD, briefing is a single Claude call with template.

**Runner auto-split trigger:** If S4 compacts, split into:
- S4a: API routes (~12 points)
- S4b: BriefingGenerator + briefing endpoints (~12 points)

**Estimated tests:** ~12 (API: GET catalysts/symbol, GET recent, GET briefing, GET history, POST generate, auth required, 404 handling = 7; briefing: generation with catalysts, generation without catalysts, cost tracking, markdown output, max_symbols limit = 5)

---

## Session 5: Frontend — Dashboard Catalyst Badges + Orchestrator Alert Panel

**Objective:** Surface catalyst data on two Command Center pages — badges on Dashboard watchlist and scrolling alert feed on Orchestrator.

| Column | Value |
|--------|-------|
| **Creates** | `argus/ui/src/hooks/useCatalysts.ts`, `argus/ui/src/components/CatalystBadge.tsx`, `argus/ui/src/components/CatalystAlertPanel.tsx` |
| **Modifies** | `argus/ui/src/pages/DashboardPage.tsx`, `argus/ui/src/pages/OrchestratorPage.tsx` |
| **Integrates** | S4 API endpoints (`/api/v1/catalysts/*`) → useCatalysts hook → UI components |
| **Parallelizable** | true (with S6 — disjoint Creates and Modifies lists, both consume S4 API) |

**Parallelizable justification:** S5 creates useCatalysts.ts, CatalystBadge.tsx, CatalystAlertPanel.tsx and modifies DashboardPage.tsx + OrchestratorPage.tsx. S6 creates IntelligenceBriefView.tsx, BriefingCard.tsx and modifies DebriefPage.tsx. Zero file overlap. Both only read from S4's API endpoints.

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 3 | +6 |
| Files modified | 2 | +2 |
| Pre-flight context reads | 4 (DashboardPage.tsx, OrchestratorPage.tsx, existing hooks, API types) | +4 |
| New tests to write | ~10 | +5 |
| Complex integration wiring | 0 | +0 |
| External API debugging | 0 | +0 |
| Large single file (>150 lines) | 0 | +0 |
| **Total** | | **17** |

**Risk level:** High. Two pages modified is the main driver. But both modifications are additive (inserting new components), not restructuring.

**Runner auto-split trigger:** If S5 compacts, split into:
- S5a: useCatalysts hook + CatalystBadge on Dashboard (~10 points)
- S5b: CatalystAlertPanel on Orchestrator (~7 points)

**Visual Review Items:**
1. Dashboard: catalyst badges appear next to watchlist entries with catalysts; no badges for symbols without catalysts; badge colors correspond to catalyst type
2. Orchestrator: alert panel scrolls with recent catalyst events; quality scores visible; empty state when no catalysts
3. Both pages: no layout shifts or regressions on existing panels

**Estimated tests:** ~10 Vitest (useCatalysts: loading, success, error, empty = 4; CatalystBadge: with data, without data, multiple types = 3; CatalystAlertPanel: with events, empty, auto-refresh = 3)

---

## Session 6: Frontend — Debrief Intelligence Brief View

**Objective:** Add intelligence brief browsing to the Debrief page — rendered markdown, date navigation, generate button.

| Column | Value |
|--------|-------|
| **Creates** | `argus/ui/src/components/IntelligenceBriefView.tsx`, `argus/ui/src/components/BriefingCard.tsx` |
| **Modifies** | `argus/ui/src/pages/DebriefPage.tsx` |
| **Integrates** | S4 briefing API endpoints (`/api/v1/premarket/briefing/*`) → Debrief UI |
| **Parallelizable** | true (with S5 — see S5 justification) |

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 | +4 |
| Files modified | 1 | +1 |
| Pre-flight context reads | 4 (DebriefPage.tsx, MarkdownRenderer.tsx, existing hooks, API types) | +4 |
| New tests to write | ~6 | +3 |
| Complex integration wiring | 0 | +0 |
| External API debugging | 0 | +0 |
| Large single file (>150 lines) | 0 | +0 |
| **Total** | | **12** |

**Risk level:** Medium. Single page, straightforward rendering.

**Visual Review Items:**
1. Debrief: intelligence brief renders as formatted markdown with section headers
2. Date navigation allows browsing past briefs; today's brief loads by default
3. "Generate Brief" button triggers generation; loading state during generation
4. Empty state shown when no brief exists for selected date
5. No layout regressions on existing Debrief tabs (Briefings, Documents, Journal)

**Estimated tests:** ~6 Vitest (IntelligenceBriefView: render brief, date navigation, empty state, generate button = 4; BriefingCard: markdown rendering, loading state = 2)

---

## Session 6f: Visual-Review Fixes (Contingency)

**Objective:** Address any visual deviations identified during S5/S6 visual review.

| Column | Value |
|--------|-------|
| **Creates** | (varies based on findings) |
| **Modifies** | (varies — limited to S5/S6 created/modified files) |
| **Integrates** | N/A |
| **Parallelizable** | false |

**Compaction Risk Scoring:** N/A — contingency session, scope determined by visual review findings.

**Estimated tests:** 0–2 (only if fixes require new test coverage)

---

## Summary Table

| Session | Scope | Score | Risk | Parallelizable | Est. Tests | Auto-Split |
|---------|-------|-------|------|----------------|------------|------------|
| S1 | Models + Config + CatalystEvent | 14 | High | false | ~6 | — |
| S2 | SEC EDGAR + FMP + Finnhub clients | 26 | Critical | false | ~18 | S2a/S2b |
| S3 | Classifier + Storage + Pipeline | 27 | Critical | false | ~16 | S3a/S3b |
| S4 | API Routes + Briefing Generator | 24 | Critical | false | ~12 | S4a/S4b |
| S5 | Dashboard + Orchestrator UI | 17 | High | **true** (∥ S6) | ~10 | S5a/S5b |
| S6 | Debrief Intelligence Brief | 12 | Medium | **true** (∥ S5) | ~6 | — |
| S6f | Visual fixes (contingency) | — | — | false | ~0–2 | — |
| **Total** | | | | | **~68** | |

**Note on high scores:** Sessions S2, S3, and S4 score above the 18+ "Critical — must split into 3+" threshold on paper. However, the scoring system was calibrated against Sprint 22 which had live API debugging and complex state management. All three sessions here use mocked external APIs in tests and follow established patterns (ABC clients, Claude API wrapper, FastAPI routes). The auto-split triggers in the runner config provide a safety net — if any session compacts, the runner automatically splits and resumes.
