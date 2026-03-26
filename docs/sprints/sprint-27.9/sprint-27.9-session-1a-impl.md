# Sprint 27.9, Session 1a: Config Model + VIXDataService Skeleton

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/config/system_config.py`
   - `argus/data/databento_data_service.py` (pattern reference for data service structure)
   - `argus/core/regime_history.py` (pattern reference for SQLite persistence)
   - `config/regime.yaml` (pattern reference for config structure)
2. Run the test baseline (full suite — Session 1 of sprint):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -x -q
   ```
   Expected: ~3,542 tests, all passing
3. Verify you are on the correct branch: `main` (or create `sprint-27.9`)
4. **Pre-Session 1a verification:** Run this quick test to check FMP index coverage:
   ```python
   import requests
   # Replace with actual API key from config
   r = requests.get("https://financialmodelingprep.com/stable/historical-price-full/%5EVIX?apikey=YOUR_KEY&serietype=line&from=2024-01-01")
   print(r.status_code, r.text[:200] if r.ok else r.text)
   ```
   If 403 or empty: `fmp_fallback_enabled` stays `false` (default). Proceed with yfinance only. Note the result in the close-out report.

## Objective
Create the VixRegimeConfig Pydantic model with all boundary sub-models, the YAML config file, wire into SystemConfig, and build the VIXDataService skeleton with SQLite persistence (no yfinance yet — synthetic data for testing).

## Requirements

1. **Create `argus/data/vix_config.py`** (~80 lines):
   - `VolRegimeBoundaries` Pydantic model: `calm_max_x: float = 1.0`, `calm_max_y: float = 0.50`, `transition_max_x: float = 1.3`, `transition_max_y: float = 0.70`, `crisis_min_y: float = 0.85`
   - `TermStructureBoundaries` Pydantic model: `contango_threshold: float = 1.0`, `low_high_percentile_split: float = 0.50`
   - `VRPBoundaries` Pydantic model: `compressed_max: float = 0.0`, `normal_max: float = 50.0`, `elevated_max: float = 150.0`
   - `VixRegimeConfig` Pydantic model with all fields from the Sprint Spec Config Changes table. Include validators: `vol_short_window < vol_long_window`, `max_staleness_days >= 1`, `history_years >= 1`, `update_interval_seconds >= 60`.
   - Enum definitions: `VolRegimePhase`, `VolRegimeMomentum`, `TermStructureRegime`, `VRPTier` — all as string enums for JSON serialization.

2. **Create `config/vix_regime.yaml`** (~50 lines):
   - All fields from VixRegimeConfig with default values.
   - Comments explaining each boundary parameter.

3. **Modify `argus/config/system_config.py`**:
   - Import VixRegimeConfig.
   - Add `vix_regime: VixRegimeConfig = VixRegimeConfig()` field to SystemConfig.

4. **Create `argus/data/vix_data_service.py`** (skeleton ~120 lines):
   - `VIXDataService` class with `__init__(self, config: VixRegimeConfig, db_path: str = "data/vix_landscape.db")`.
   - SQLite schema: `vix_daily` table with columns: `date TEXT PRIMARY KEY, vix_open REAL, vix_high REAL, vix_low REAL, vix_close REAL, spx_open REAL, spx_high REAL, spx_low REAL, spx_close REAL, vol_of_vol_ratio REAL, vix_percentile REAL, term_structure_proxy REAL, realized_vol_20d REAL, variance_risk_premium REAL`.
   - `_init_db()` — create table if not exists, WAL mode.
   - `persist_daily(rows: list[dict])` — batch INSERT OR REPLACE with atomic transaction.
   - `load_from_db() -> pd.DataFrame` — load all rows, return as DataFrame.
   - `get_latest_daily() -> Optional[dict]` — return last completed trading day's data with `data_date` field. If `is_stale`, return dict with `data_date` and `vix_close` but None for all derived metrics. Returns None entirely if no data.
   - `is_ready: bool` property — True after initial load complete.
   - `is_stale: bool` property — True when last data_date is more than `max_staleness_days` trading days ago. Use `pd.bdate_range` to count business days.
   - `_last_trading_day() -> date` — helper returning last completed US trading day (if before 4:15 PM ET today, return yesterday's trading day; if weekend/holiday, return Friday/last business day).
   - **Do NOT implement yfinance fetch methods yet.** Leave `fetch_historical()` and `fetch_incremental()` as stubs that raise `NotImplementedError`. Session 1b adds these.

5. **Create `tests/data/test_vix_data_service.py`** (5 tests):
   - `test_config_yaml_matches_pydantic_model`: Load `config/vix_regime.yaml`, verify all keys recognized by `VixRegimeConfig.model_fields` — no silently ignored fields.
   - `test_config_validators`: Test that invalid configs raise ValidationError (e.g., `vol_short_window > vol_long_window`).
   - `test_persist_and_load_roundtrip`: Insert synthetic rows via `persist_daily()`, load via `load_from_db()`, verify data integrity.
   - `test_staleness_logic`: Insert data from 5 business days ago, verify `is_stale` returns True. Insert today's data, verify `is_stale` returns False.
   - `test_get_latest_daily_weekend`: Insert Friday data, mock current date as Saturday, verify `get_latest_daily()` returns Friday's data with correct `data_date`.

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/strategies/*.py`, `argus/execution/`, `argus/backtest/`, `argus/ai/`
- Do NOT add yfinance as a dependency yet (Session 1b)
- Do NOT implement derived metric computation yet (Session 1b)
- SQLite DB path: `data/vix_landscape.db` (follows DEC-345 separate DB pattern)
- Use `aiosqlite` for async SQLite access (matches existing ARGUS pattern) OR synchronous `sqlite3` if the service's methods are sync (VIXDataService operates on daily data — sync is fine). Choose whichever matches the existing regime_history.py pattern.

## Config Validation
Write a test that loads the YAML config file and verifies all keys under `vix_regime` are recognized by the Pydantic model:
1. Load `config/vix_regime.yaml` and extract the `vix_regime` keys (including nested boundary keys)
2. Compare against `VixRegimeConfig.model_fields.keys()` and nested model fields
3. Assert no keys present in YAML that are absent from the model

Expected mapping:

| YAML Key | Model Field |
|----------|-------------|
| `enabled` | `enabled` |
| `yahoo_symbol_vix` | `yahoo_symbol_vix` |
| `yahoo_symbol_spx` | `yahoo_symbol_spx` |
| `vol_short_window` | `vol_short_window` |
| `vol_long_window` | `vol_long_window` |
| `percentile_window` | `percentile_window` |
| `ma_window` | `ma_window` |
| `rv_window` | `rv_window` |
| `update_interval_seconds` | `update_interval_seconds` |
| `history_years` | `history_years` |
| `max_staleness_days` | `max_staleness_days` |
| `fmp_fallback_enabled` | `fmp_fallback_enabled` |
| `momentum_window` | `momentum_window` |
| `momentum_threshold` | `momentum_threshold` |
| `vol_regime_boundaries.*` | `VolRegimeBoundaries.*` |
| `term_structure_boundaries.*` | `TermStructureBoundaries.*` |
| `vrp_boundaries.*` | `VRPBoundaries.*` |

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests: 5 in `tests/data/test_vix_data_service.py`
- Minimum new test count: 5
- Test command: `python -m pytest tests/data/test_vix_data_service.py -x -q`

## Definition of Done
- [ ] VixRegimeConfig + boundary sub-models created with validators
- [ ] vix_regime.yaml created with all defaults and comments
- [ ] SystemConfig wired with VixRegimeConfig field
- [ ] VIXDataService skeleton with SQLite persistence (persist/load/staleness/get_latest)
- [ ] 5 tests written and passing
- [ ] Config validation test confirms YAML↔Pydantic alignment
- [ ] FMP ^VIX endpoint test result noted in close-out
- [ ] All existing tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| SystemConfig still loads existing configs | `python -m pytest tests/ -k "config" -x -q` |
| No import errors in existing modules | `python -c "from argus.config.system_config import SystemConfig"` |
| R13: Config YAML keys match Pydantic model | Config validation test |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27.9/session-1a-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.9/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.9/session-1a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/data/test_vix_data_service.py -x -q`
5. Files that should NOT have been modified: `argus/core/events.py`, `argus/strategies/`, `argus/execution/`, `argus/backtest/`, `argus/ai/`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report per the implementation
prompt template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify VixRegimeConfig validators reject invalid combinations
2. Verify SQLite schema uses WAL mode
3. Verify `is_stale` uses business day counting, not calendar days
4. Verify `get_latest_daily()` returns None (not stale data) when staleness exceeded
5. Verify no yfinance import anywhere (Session 1b scope)

## Sprint-Level Regression Checklist (for @reviewer)
R1: `primary_regime` identical | R2: Construction with original fields | R3: matches_conditions None=match-any | R4: to_dict 11 fields | R5: History reads pre-sprint rows | R6: Strategy activation unchanged | R7: Quality scores unchanged | R8: Position sizes unchanged | R9: Briefing valid without VIX | R10: Server starts (enabled) | R11: Server starts (disabled) | R12: Existing 6 dims unchanged | R13: Config YAML↔Pydantic | R14: Dashboard loads (disabled) | R15: Existing API endpoints

*Note: R1–R12, R14–R15 are not yet testable in this session (infrastructure not built). R13 is the primary regression check for Session 1a.*

## Sprint-Level Escalation Criteria (for @reviewer)
1. yfinance fetch failure → ESCALATE | 2. primary_regime breaks → ESCALATE | 3. Existing calculator changes → ESCALATE | 4. Strategy activation changes → ESCALATE | 5. Quality/sizing changes → ESCALATE | 6. SINDy creep → ESCALATE | 7. Server startup fails → ESCALATE
