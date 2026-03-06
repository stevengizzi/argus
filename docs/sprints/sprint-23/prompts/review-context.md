# Sprint 23: Review Context File

**Instructions:** You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any files. Follow the review skill in `.claude/skills/review.md`.

This file is referenced by all Sprint 23 session review prompts. It contains the complete Sprint Spec, Specification by Contradiction, Regression Checklist, and Escalation Criteria.

---

## Sprint Spec

### Sprint 23: Universe Manager

**Goal:** Replace the static pre-market watchlist (15 symbols from FMP Scanner) with a Universe Manager that monitors the broad US equity universe via Databento ALL_SYMBOLS, caches FMP reference data (sector, market cap, float) for viable symbols, and routes candle events to strategies based on declarative `universe_filter` YAML configs. Infrastructure foundation for DEC-263.

**Deliverables:**
1. FMP Reference Data Client (`argus/data/fmp_reference.py`)
2. Universe Manager (`argus/data/universe_manager.py`)
3. Universe Filter Config Schema (UniverseFilterConfig + UniverseManagerConfig Pydantic models)
4. Strategy Filter Declarations (universe_filter YAML for all 4 strategies)
5. Routing Table + Event Integration (symbol→strategy routing, fast-path discard)
6. Main.py Startup Integration (config-gated, backward compatible)
7. Databento ALL_SYMBOLS Activation
8. API Endpoints (GET /api/v1/universe/status, GET /api/v1/universe/symbols)
9. Dashboard Universe Panel

**Key Decisions:**
- ALL_SYMBOLS Databento subscription, filter in software
- FMP Starter plan ($22/mo) sufficient — batch Company Profile + Share Float
- Cold-start indicators (no warm-up for broad universe)
- Config-gated: `universe_manager.enabled: true/false`
- Backward compatible: replay/backtest modes unchanged

**Config Changes:**
- system.yaml: new `universe_manager` section (UniverseManagerConfig)
- strategies/*.yaml: new `universe_filter` sections (UniverseFilterConfig)

**Files that should NOT be modified by any session:**
- `argus/ai/` (entire AI layer)
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/execution/` (Order Manager, brokers)
- `argus/analytics/` (Trade Logger, Performance Calculator)
- `argus/strategies/*.py` (strategy Python code — only YAML configs change)
- `argus/backtest/` (backtesting infrastructure)

---

## Specification by Contradiction

**Out of Scope:**
1. NLP Catalyst Pipeline (SEC EDGAR, FMP news, Claude API) — Sprint 23.5
2. Pre-Market Intelligence Brief — Sprint 23.5
3. Catalyst badges in UI — Sprint 23.5
4. AI-generated debrief narratives — Sprint 23.5
5. Intraday re-scanning / dynamic universe expansion — Sprint 23.5+
6. Indicator warm-up for broad universe — deferred
7. FMP plan upgrade — not needed
8. Finnhub integration — deferred
9. Strategy `behavioral_triggers` config — Sprint 24+
10. Strategy code changes — only YAML configs change

**Edge Cases to Reject:**
- FMP batch endpoint unavailable on Starter → fall back to sequential, log warning, ESCALATE
- Databento ALL_SYMBOLS failure → fall back to scanner symbols, ESCALATE
- Memory >500MB above baseline → log warning, ESCALATE
- Missing FMP reference data fields → treat as "no data", symbol passes filter checks on missing fields
- Strategy filter matches zero symbols → log warning, strategy active but receives no candles
- Mid-day IPOs/resumed halts → discarded (no reference data), intraday expansion out of scope

**Do NOT modify:** argus/ai/, orchestrator.py, risk_manager.py, execution/, analytics/, strategies/*.py, backtest/
**Do NOT optimize:** IndicatorEngine speed
**Do NOT refactor:** Existing scanner classes
**Do NOT add:** WebSocket for universe updates, catalyst sources, order flow, strategy correlation

---

## Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | All existing pytest tests pass | `python -m pytest tests/ -x -q` — 1,977+ passing |
| R2 | All existing Vitest tests pass | `cd argus/ui && npx vitest run` — 377+ passing |
| R3 | Ruff linting passes | `python -m ruff check argus/` |
| R4 | System starts with UM disabled using existing flow | Logs show scanner path, NOT UniverseManager |
| R5 | System starts with UM enabled using UM flow | Logs show UniverseManager path |
| R6–R9 | All 4 strategy configs load with universe_filter | Load each config, print universe_filter |
| R10 | ORB same-symbol mutual exclusion intact | `pytest -k "orb" -k "exclusion"` |
| R11 | Strategy YAML keys match Pydantic model fields | Dedicated YAML↔model test |
| R12 | Databento ALL_SYMBOLS mode active (UM enabled) | Check subscription logs |
| R13 | Fast-path discard for non-viable symbols | Unit test |
| R14 | Candles for viable symbols processed | Unit test |
| R15 | Databento backward compat (UM disabled) | Unit test |
| R16–R19 | Config loading + no silently ignored keys | Dedicated tests |
| R20–R22 | UI pages load without errors | Visual verification |
| R23 | AI Copilot functional | Visual: send message, verify response |
| R24 | Backtesting/replay unaffected | `pytest -k "replay"` |
| R25 | Risk Manager unchanged | `pytest -k "risk"` |
| R26 | Existing API endpoints unchanged | `pytest -k "api"` |

---

## Escalation Criteria

**ESCALATE if ANY of these are true:**

1. Candle routing adds >50μs per event
2. FMP reference data fetch takes >5 minutes for 4,000 symbols
3. Memory overhead >500MB above baseline
4. Startup time increase >5 minutes with UM enabled
5. Any existing strategy test fails after Session 4b
6. ORB mutual exclusion broken
7. Strategies receive candles for non-matching symbols
8. Strategies miss candles for matching symbols
9. Databento ALL_SYMBOLS causes session errors
10. Backtesting/replay modes affected
11. AI Copilot degraded
12. Session requires modifying "Do not modify" files
13. Config field mismatch (YAML key silently ignored by Pydantic)
