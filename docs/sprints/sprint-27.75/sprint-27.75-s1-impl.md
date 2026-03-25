# Sprint 27.75, Session 1: Backend — Log Rate-Limiting + Paper Trading Config

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/project-knowledge.md`
   - `argus/core/config.py` (OrchestratorConfig, RiskConfig, AccountRiskConfig)
   - `config/system_live.yaml`
   - `config/quality_engine.yaml`
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Expected: ~3,517 tests, all passing
3. Verify you are on branch: `main`

## Objective
Implement rate-limited logging for 4 high-volume warning sources that generated 3,500+ log lines in a single session, and adjust paper-trading configuration to disable performance throttling and reduce position sizing so capital isn't exhausted by 30+ concurrent positions.

## Context
During the March 25, 2026 market session, the JSONL log grew to 16,878 lines with 3,583 warnings/errors. The top contributors were:
- IBKR error 399 "repriced" warnings: ~1,502 (same symbol repriced every ~1s)
- Risk Manager cash-reserve / concentration rejections: ~414 (same reason logged every minute)
- Position reconciliation per-symbol lines: ~1,000+ (32 individual lines × 79 reconciliation checks)
- IBKR error 202 duplicates: ~456 (same orderId canceled 2-3x)

Separately, 4 of 7 strategies were suspended after 5 consecutive losses, and VWAP Reclaim was throttled by the PerformanceThrottler. During paper trading, this throttling prevents data collection. The account also exhausted its $950K capital in 6 minutes due to risk tiers sized for live trading (0.5–3% per trade), leaving no room for concurrent positions.

## Requirements

### Part A: Rate-Limited Logging (4 sources)

1. **Create `argus/utils/log_throttle.py`** — a reusable rate-limited logger utility:
   - `ThrottledLogger` class wrapping Python's `logging.Logger`
   - `warn_throttled(key: str, message: str, interval_seconds: float = 60.0)` method
   - Tracks last emission time per key in a dict
   - Suppressed messages counted; on next emission, appends "(N suppressed)" to message
   - Thread-safe (use `threading.Lock`)
   - `reset()` method to clear all throttle state
   - Standalone `get_throttled_logger(name: str) -> ThrottledLogger` factory

2. **In `argus/execution/ibkr_broker.py`** — throttle IBKR error 399 and error 202:
   - Error 399 ("repriced so as not to cross"): rate-limit per symbol, 1 per 60s per symbol
   - Error 202 ("Order Canceled"): rate-limit per orderId, log once per orderId only
   - Error 10148 ("cannot be cancelled"): rate-limit per orderId, log once per orderId only
   - Use `ThrottledLogger` with key = `f"ibkr_399_{symbol}"` / `f"ibkr_202_{order_id}"` / `f"ibkr_10148_{order_id}"`

3. **In `argus/core/risk_manager.py`** — throttle rejection warnings:
   - "cash reserve would be violated": rate-limit 1 per 60s (key: `"cash_reserve_violated"`)
   - "concentration-reduced shares ... below $100 floor": rate-limit 1 per 60s (key: `"concentration_floor"`)
   - "cash-reserve-reduced shares ... below $100 floor": rate-limit 1 per 60s (key: `"cashreserve_floor"`)
   - On each suppressed message, increment a counter; next emission includes suppressed count

4. **In `argus/execution/order_manager.py`** — consolidate reconciliation logging:
   - Replace the loop that emits one WARNING per mismatched symbol with a single consolidated line
   - Format: `"Position reconciliation: {N} mismatch(es) — {first_3_symbols}... (ARGUS vs IBKR)"`
   - Keep full per-symbol detail at DEBUG level (not WARNING)
   - The summary line remains at WARNING level

### Part B: Paper Trading Configuration

5. **In `config/quality_engine.yaml`** — add a `paper_trading_overrides` section:
   - This section is NOT loaded automatically — it documents the values to set for paper mode
   - Instead, directly modify the main `risk_tiers` values for paper trading:
     - `a_plus: [0.002, 0.003]` (was [0.02, 0.03] — 10x reduction)
     - `a: [0.0015, 0.002]` (was [0.015, 0.02])
     - `a_minus: [0.001, 0.0015]` (was [0.01, 0.015])
     - `b_plus: [0.00075, 0.001]` (was [0.0075, 0.01])
     - `b: [0.0005, 0.00075]` (was [0.005, 0.0075])
     - `b_minus: [0.00025, 0.0005]` (was [0.0025, 0.005])
     - `c_plus: [0.00025, 0.00025]` (was [0.0025, 0.0025])
   - Add a YAML comment block explaining the 10x reduction rationale for paper trading

6. **In `config/system_live.yaml`** — disable performance throttling for paper trading:
   - Under the `orchestrator:` section, add/set: `consecutive_loss_throttle: 999`
   - Under the `orchestrator:` section, add/set: `suspension_sharpe_threshold: -999.0`
   - Under the `orchestrator:` section, add/set: `suspension_drawdown_pct: 0.50`
   - Add YAML comments explaining these are paper-trading values and should be restored for live

7. **In `config/system_live.yaml`** — reduce min_position_risk_dollars for paper:
   - Under `risk: account:`, set `min_position_risk_dollars: 10.0` (was 100.0)
   - This prevents the concentration-floor rejection storm (133 rejections today from $100 floor with tiny positions)
   - Add YAML comment noting paper-trading override

## Constraints
- Do NOT modify any strategy logic (strategies/, patterns/)
- Do NOT modify the Orchestrator suspension logic itself — only the config thresholds
- Do NOT modify any frontend code
- Do NOT change the Risk Manager's check logic — only add log throttling around existing warnings
- `ThrottledLogger` must be purely additive — existing log calls still work if not migrated
- Position reconciliation must still log per-symbol detail at DEBUG level for diagnostics

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `tests/utils/test_log_throttle.py`:
     - `test_first_message_always_emits` — first call to warn_throttled passes through
     - `test_duplicate_within_interval_suppressed` — second call within 60s is suppressed
     - `test_message_after_interval_emits` — call after interval passes through with suppressed count
     - `test_different_keys_independent` — two keys don't interfere
     - `test_suppressed_count_in_message` — "(5 suppressed)" appended after suppression
     - `test_reset_clears_state` — after reset(), first message emits again
     - `test_thread_safety` — concurrent calls don't crash (use threading)
  2. `tests/execution/test_ibkr_log_throttle.py`:
     - `test_error_399_throttled_per_symbol` — verify same symbol doesn't repeat within 60s
     - `test_error_202_logged_once_per_order` — verify same orderId logged once
  3. `tests/core/test_risk_manager_log_throttle.py`:
     - `test_cash_reserve_warning_throttled` — verify only 1 warning per 60s
     - `test_concentration_floor_warning_throttled` — verify only 1 warning per 60s
  4. `tests/execution/test_order_manager_reconciliation_log.py`:
     - `test_reconciliation_summary_single_line` — verify consolidated WARNING
     - `test_reconciliation_detail_at_debug` — verify per-symbol at DEBUG
- Minimum new test count: 12
- Test command: `python -m pytest tests/utils/test_log_throttle.py tests/execution/test_ibkr_log_throttle.py tests/core/test_risk_manager_log_throttle.py tests/execution/test_order_manager_reconciliation_log.py -x -q`

## Definition of Done
- [ ] `ThrottledLogger` utility created and tested
- [ ] IBKR error 399/202/10148 warnings rate-limited
- [ ] Risk Manager cash-reserve/concentration warnings rate-limited
- [ ] Position reconciliation consolidated to single WARNING line
- [ ] `quality_engine.yaml` risk tiers reduced 10x for paper trading
- [ ] `system_live.yaml` throttle thresholds disabled for paper trading
- [ ] `system_live.yaml` min_position_risk_dollars reduced to $10
- [ ] All existing tests pass
- [ ] New tests written and passing (≥12)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing log messages still work | `grep -r "logger.warning" argus/core/risk_manager.py` shows calls still present |
| Config validates | `python -c "from argus.core.config import SystemConfig; SystemConfig.from_yaml('config/system_live.yaml')"` |
| Quality engine config validates | `python -c "from argus.core.config import QualityEngineConfig; import yaml; QualityEngineConfig(**yaml.safe_load(open('config/quality_engine.yaml')))"` |
| Risk tiers are reduced | `python -c "import yaml; d=yaml.safe_load(open('config/quality_engine.yaml')); assert d['risk_tiers']['a_plus'][0] < 0.01"` |
| Throttle disabled | `python -c "import yaml; d=yaml.safe_load(open('config/system_live.yaml')); assert d['orchestrator']['consecutive_loss_throttle'] > 100"` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27.75/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-27.75/review-context.md
2. The close-out report path: docs/sprints/sprint-27.75/session-1-closeout.md
3. The diff range: git diff HEAD~1
4. The test command: `python -m pytest tests/utils/test_log_throttle.py tests/execution/test_ibkr_log_throttle.py tests/core/test_risk_manager_log_throttle.py tests/execution/test_order_manager_reconciliation_log.py -x -q`
5. Files that should NOT have been modified: `argus/strategies/`, `argus/ui/`, `argus/backtest/`, `argus/intelligence/counterfactual*.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail per the template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify ThrottledLogger is thread-safe (Lock usage)
2. Verify existing WARNING log calls in risk_manager.py are preserved (not removed) — only wrapped with throttling
3. Verify reconciliation still emits per-symbol detail at DEBUG level
4. Verify config changes are YAML-valid and load without errors
5. Verify risk tier values are exactly 10x reduction (not accidentally 100x or 1x)
6. Verify no strategy code was modified

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| Tests pass | `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto` |
| Config loads | `python -c "from argus.core.config import SystemConfig; SystemConfig.from_yaml('config/system_live.yaml')"` |
| No strategy changes | `git diff HEAD~1 -- argus/strategies/` shows no changes |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if any existing test fails
- ESCALATE if strategy logic was modified
- ESCALATE if Risk Manager check logic (approve/reject decisions) was changed, not just logging
- ESCALATE if ThrottledLogger could silently swallow the FIRST occurrence of a warning
