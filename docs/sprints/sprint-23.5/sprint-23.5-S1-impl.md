# Sprint 23.5, Session 1: Foundation — Models, CatalystEvent, Config

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` (existing event classes — follow the pattern)
   - `config/system.yaml` (existing config structure — add alongside `universe_manager:`)
   - `argus/data/fmp_reference.py` (lines 1–80, FMPReferenceConfig pattern for Pydantic config)
   - `argus/ai/config.py` (AIConfig pattern)
2. Run the test suite: `cd argus && python -m pytest tests/ -x -q`
   Expected: 2,101+ tests, all passing
3. Verify you are on the correct branch: `git checkout -b sprint-23.5`
4. Verify `argus/intelligence/` directory does NOT exist yet

## Objective
Establish the intelligence module foundation: data models, CatalystEvent on the Event Bus, and Pydantic config model for the `catalyst:` section in system.yaml. This session creates the structural skeleton that all subsequent sessions build on.

## Requirements

1. **Create `argus/intelligence/__init__.py`**: Empty init file establishing the intelligence module package. Add a module docstring: "Intelligence layer — AI-enhanced trading intelligence components (Sprint 23.5+)."

2. **Create `argus/intelligence/models.py`**: Data models for the catalyst pipeline:
   - `CatalystRawItem`: Dataclass for raw items from data sources before classification. Fields: `headline: str`, `symbol: str`, `source: str` (e.g., "sec_edgar", "fmp_news", "finnhub"), `source_url: str | None`, `filing_type: str | None` (e.g., "8-K", "Form 4"), `published_at: datetime`, `fetched_at: datetime`, `metadata: dict[str, Any]` (source-specific extra fields).
   - `CatalystClassification`: Dataclass for classification output. Fields: `category: str` (one of: "earnings", "insider_trade", "sec_filing", "analyst_action", "corporate_event", "news_sentiment", "regulatory", "other"), `quality_score: float` (0–100), `summary: str` (one-sentence trading-relevant summary), `trading_relevance: str` (one of: "high", "medium", "low", "none"), `classified_by: str` (one of: "claude", "fallback"), `classified_at: datetime`.
   - `ClassifiedCatalyst`: Dataclass combining raw item + classification. Fields: all CatalystRawItem fields + all CatalystClassification fields + `headline_hash: str` (SHA-256 of lowercase stripped headline).
   - `IntelligenceBrief`: Dataclass for generated briefs. Fields: `date: str` (YYYY-MM-DD), `brief_type: str` (e.g., "premarket"), `content: str` (markdown), `symbols_covered: list[str]`, `catalyst_count: int`, `generated_at: datetime`, `generation_cost_usd: float`.
   - Include a `compute_headline_hash(headline: str) -> str` utility function.
   - All datetime fields should use `ZoneInfo("America/New_York")` per DEC-276 (ET timestamps for AI layer).

3. **Create `argus/intelligence/config.py`**: Pydantic config models:
   - `SECEdgarConfig`: `enabled: bool = True`, `filing_types: list[str] = ["8-K", "4"]`, `user_agent_email: str = ""` (required when enabled — SEC fair access policy), `rate_limit_per_second: float = 10.0`.
   - `FMPNewsConfig`: `enabled: bool = True`, `api_key_env_var: str = "FMP_API_KEY"`, `endpoints: list[str] = ["stock_news", "press_releases"]`.
   - `FinnhubConfig`: `enabled: bool = True`, `api_key_env_var: str = "FINNHUB_API_KEY"`, `rate_limit_per_minute: int = 60`.
   - `SourcesConfig`: `sec_edgar: SECEdgarConfig = SECEdgarConfig()`, `fmp_news: FMPNewsConfig = FMPNewsConfig()`, `finnhub: FinnhubConfig = FinnhubConfig()`.
   - `BriefingConfig`: `model: str | None = None` (None inherits from `ai.model`), `max_symbols: int = 30`.
   - `CatalystConfig`: `enabled: bool = False`, `polling_interval_premarket_seconds: int = 900`, `polling_interval_session_seconds: int = 1800`, `max_batch_size: int = 20`, `daily_cost_ceiling_usd: float = 5.0`, `classification_cache_ttl_hours: int = 24`, `sources: SourcesConfig = SourcesConfig()`, `briefing: BriefingConfig = BriefingConfig()`.
   - All models extend `pydantic.BaseModel` following the existing Pydantic config pattern.

4. **Modify `argus/core/events.py`**: Add CatalystEvent class following the existing event pattern:
   ```python
   class CatalystEvent(Event):
       """A classified catalyst event for a symbol."""
       symbol: str
       catalyst_type: str  # category from classification
       quality_score: float  # 0-100
       headline: str
       summary: str
       source: str  # "sec_edgar", "fmp_news", "finnhub"
       source_url: str | None
       filing_type: str | None
       published_at: datetime
       classified_at: datetime
   ```
   Place it after the existing event classes, before ShutdownRequestedEvent.

5. **Modify `config/system.yaml`**: Add the `catalyst:` section after `universe_manager:`:
   ```yaml
   # NLP Catalyst Pipeline (Sprint 23.5 — DEC-164)
   # Ingests news/filings from SEC EDGAR, FMP, Finnhub.
   # Classifies catalyst quality via Claude API.
   # Set enabled: true to activate. Requires FINNHUB_API_KEY for Finnhub source.
   catalyst:
     enabled: false          # Start disabled — operator activates when ready
     polling_interval_premarket_seconds: 900   # 15 minutes
     polling_interval_session_seconds: 1800    # 30 minutes
     max_batch_size: 20
     daily_cost_ceiling_usd: 5.0
     classification_cache_ttl_hours: 24
     sources:
       sec_edgar:
         enabled: true
         filing_types:
           - "8-K"
           - "4"
         user_agent_email: ""     # Required: your email for SEC fair access
         rate_limit_per_second: 10.0
       fmp_news:
         enabled: true
         api_key_env_var: "FMP_API_KEY"
         endpoints:
           - "stock_news"
           - "press_releases"
       finnhub:
         enabled: true
         api_key_env_var: "FINNHUB_API_KEY"
         rate_limit_per_minute: 60
     briefing:
       model: null             # null inherits from ai.model (Claude Opus)
       max_symbols: 30
   ```

## Constraints
- Do NOT modify: `argus/ai/*`, `argus/strategies/*`, `argus/core/risk_manager.py`, `argus/core/orchestrator.py`, `argus/execution/*`, `argus/data/*`, `argus/analytics/*`
- Do NOT add any Event Bus subscribers for CatalystEvent
- Do NOT import or depend on any external HTTP libraries (no aiohttp, no requests) — those come in Session 2
- Follow existing naming conventions: snake_case files, PascalCase classes, UPPER_SNAKE_CASE constants

## Test Targets
After implementation:
- Existing tests: all 2,101+ must still pass
- New tests to write in `tests/intelligence/test_models.py` and `tests/intelligence/test_config.py`:
  1. CatalystRawItem construction with all fields
  2. CatalystClassification with valid category values
  3. CatalystClassification rejects invalid category
  4. compute_headline_hash produces consistent SHA-256
  5. CatalystConfig loads from default values
  6. Config validation test: load system.yaml catalyst section, verify all keys match CatalystConfig.model_fields.keys() (no silently ignored keys)
- Minimum new test count: 6
- Test command: `python -m pytest tests/intelligence/ -v`

## Config Validation
Write a test that loads the YAML config file and verifies all keys under the `catalyst` section are recognized by the CatalystConfig Pydantic model. Specifically:
1. Load `config/system.yaml` and extract the `catalyst` keys (recursively)
2. Compare against `CatalystConfig` model fields (recursively through nested models)
3. Assert no keys are present in YAML that are absent from the model

Expected mapping:

| YAML Key | Model Field |
|----------|-------------|
| catalyst.enabled | CatalystConfig.enabled |
| catalyst.polling_interval_premarket_seconds | CatalystConfig.polling_interval_premarket_seconds |
| catalyst.polling_interval_session_seconds | CatalystConfig.polling_interval_session_seconds |
| catalyst.max_batch_size | CatalystConfig.max_batch_size |
| catalyst.daily_cost_ceiling_usd | CatalystConfig.daily_cost_ceiling_usd |
| catalyst.classification_cache_ttl_hours | CatalystConfig.classification_cache_ttl_hours |
| catalyst.sources.sec_edgar.enabled | SECEdgarConfig.enabled |
| catalyst.sources.sec_edgar.filing_types | SECEdgarConfig.filing_types |
| catalyst.sources.sec_edgar.user_agent_email | SECEdgarConfig.user_agent_email |
| catalyst.sources.sec_edgar.rate_limit_per_second | SECEdgarConfig.rate_limit_per_second |
| catalyst.sources.fmp_news.enabled | FMPNewsConfig.enabled |
| catalyst.sources.fmp_news.api_key_env_var | FMPNewsConfig.api_key_env_var |
| catalyst.sources.fmp_news.endpoints | FMPNewsConfig.endpoints |
| catalyst.sources.finnhub.enabled | FinnhubConfig.enabled |
| catalyst.sources.finnhub.api_key_env_var | FinnhubConfig.api_key_env_var |
| catalyst.sources.finnhub.rate_limit_per_minute | FinnhubConfig.rate_limit_per_minute |
| catalyst.briefing.model | BriefingConfig.model |
| catalyst.briefing.max_symbols | BriefingConfig.max_symbols |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass (2,101+ pytest)
- [ ] New tests written and passing (≥6)
- [ ] Config validation test passing
- [ ] `catalyst.enabled: false` — system operates identically to pre-sprint
- [ ] Ruff linting passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| CatalystEvent is additive to events.py | `git diff argus/core/events.py` shows only additions, no modifications to existing classes |
| No subscribers for CatalystEvent | `grep -r "subscribe.*CatalystEvent" argus/` returns 0 matches |
| Config default is disabled | Load system.yaml, assert `catalyst.enabled` is `false` |
| No protected files modified | `git diff --name-only` shows only intelligence/ files, core/events.py, config/system.yaml |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from sprint-23.5-review-context.md (file path: `docs/sprints/sprint-23.5/review-context.md`)

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from sprint-23.5-review-context.md
