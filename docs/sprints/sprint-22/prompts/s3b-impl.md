# Sprint 22, Session 3b: Action Executors + AI Content

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ai/actions.py` (Session 3a)
   - `argus/ai/tools.py` (Session 1 — tool definitions)
   - `argus/ai/client.py` (Session 1)
   - `argus/ai/prompts.py` (Session 1)
   - `argus/ai/conversations.py` (Session 2a)
   - `argus/ai/usage.py` (Session 2a)
   - `argus/core/orchestrator.py` (read only — understand allocation/suspend/resume methods)
   - `argus/core/risk_manager.py` (read only — understand param update interface)
   - `argus/analytics/trade_logger.py` (read only — understand trade data access)
   - `argus/core/portfolio.py` (read only — understand equity/position access)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ≥1,794 tests (previous + Session 3a), all passing
3. Verify you are on the correct branch: `sprint-22-ai-layer`

## Objective
Implement the 5 action executors with validation and pre-execution re-check, the DailySummaryGenerator with explicit data assembly, the Dashboard insight endpoint, and the AIService orchestration class that ties all AI components together.

## Requirements

1. In `argus/ai/executors.py`, create the executor framework and 5 implementations:

   - Base: `ActionExecutor` ABC with:
     - `async def validate(tool_input: dict) -> tuple[bool, str]` — returns (valid, error_message)
     - `async def pre_execution_recheck(proposal: ActionProposal, app_state) -> tuple[bool, str]` — the 4-condition gate
     - `async def execute(proposal: ActionProposal, app_state) -> dict` — performs the action, returns result

   - **4-Condition Pre-Execution Re-Check** (shared by all executors requiring approval):
     1. Strategy exists and is in expected state (active for allocation/param changes; active for suspend; suspended for resume)
     2. Market regime classification unchanged since proposal creation (compare current regime to regime at `proposal.created_at`)
     3. Account equity within 5% of equity at proposal creation time (store equity snapshot in tool_input or proposal metadata)
     4. No circuit breaker currently active

     If any check fails: return `(False, "Execution blocked — {reason}")`. The ActionManager should call `fail_proposal(id, reason)`.

   - `AllocationChangeExecutor`:
     - Validate: strategy_id exists, new_allocation_pct in 0–100, sum of all allocations ≤ 100
     - Execute: call Orchestrator's allocation override method (READ the orchestrator code to find the correct method — likely involves updating runtime allocation config. Do NOT modify orchestrator.py source — call its public API.)
     - Result: `{strategy_id, old_allocation, new_allocation, effective: true}`

   - `RiskParamChangeExecutor`:
     - Validate: param_path exists in risk config, new_value within defined sane ranges:
       - `risk.daily_loss_limit_pct`: 1–10%
       - `risk.weekly_loss_limit_pct`: 2–15%
       - `risk.max_single_stock_pct`: 1–15%
       - `risk.per_trade_risk_pct`: 0.1–3%
       - Other params: reject with "Param not modifiable via AI"
     - Execute: update runtime risk config. Do NOT modify risk_manager.py source.
     - Result: `{param_path, old_value, new_value, effective: true}`

   - `StrategySuspendExecutor`:
     - Validate: strategy_id exists and is currently active
     - Execute: call Orchestrator's suspend method
     - Result: `{strategy_id, status: "suspended", reason}`

   - `StrategyResumeExecutor`:
     - Validate: strategy_id exists and is currently suspended
     - Execute: call Orchestrator's resume method
     - Result: `{strategy_id, status: "active", reason}`

   - `GenerateReportExecutor`:
     - No approval required (executes immediately)
     - No pre-execution re-check needed
     - Validate: report_type in allowed set
     - Execute: delegates to DailySummaryGenerator (below) or other generator based on type
     - Result: `{report_type, content: str, saved: true}`

   - `ExecutorRegistry`: maps tool_name → executor class. Used by AIService.

2. In `argus/ai/summary.py`, create `DailySummaryGenerator`:
   - `async def generate(date: str, app_state) -> str`:
     - Assembles data from app_state components:
       a. Today's trades from Trade Logger: entries, exits, P&L, R-multiples, hold durations
       b. Orchestrator decisions: regime classification, allocation changes, any suspensions
       c. Risk events: rejections, modifications (approve-with-modification), circuit breakers
       d. Performance context: daily P&L vs target, weekly running total, win rate
       e. Per-strategy breakdown: strategy name, trade count, P&L, win rate
     - Constructs a prompt with this data and sends to ClaudeClient
     - System prompt addition: "Generate a concise end-of-day trading summary. Be factual. Reference specific trades and numbers. Note any unusual patterns or concerns. Keep it under 500 words."
     - Returns the generated summary text
     - Records usage via UsageTracker (endpoint="summary")

   - `async def generate_insight(app_state) -> str`:
     - For Dashboard insight card
     - Lighter data assembly: current positions, daily P&L, regime, any active alerts
     - Shorter prompt: "Generate a brief (2-3 sentence) insight about the current trading session state. Be specific, not generic."
     - Uses ResponseCache — if cached and fresh, return cached
     - Records usage (endpoint="insight")

3. In `argus/ai/service.py`, create `AIService` — the main orchestration class:
   - Constructor takes all AI components (client, prompt_manager, context_builder, conversation_manager, usage_tracker, action_manager, executor_registry, summary_generator, cache)
   - `async def handle_chat(conversation_id, message, page, page_context, app_state) -> dict`:
     - Build system prompt + page context
     - Get/create conversation
     - Build message history
     - Call Claude API with tools
     - Handle tool_use: for each tool_use block, if requires approval → create proposal; if not → execute immediately
     - Persist messages, record usage
     - Return response with proposals
   - `async def handle_approve(proposal_id, app_state) -> dict`:
     - Get proposal, approve via ActionManager
     - Run pre-execution re-check
     - If re-check passes: execute via appropriate executor, mark executed
     - If re-check fails: mark failed with reason
     - Return result (which gets posted back to chat)
   - `async def handle_reject(proposal_id, reason) -> dict`
   - `async def get_insight(app_state) -> dict`
   - `async def generate_daily_summary(date, app_state) -> dict`

4. Add Dashboard insight endpoint to `argus/api/routes/ai.py`:
   - `GET /api/v1/ai/insight`:
     - JWT required
     - Returns: `{insight: str, generated_at: str, cached: bool}`
     - When AI disabled: `{insight: null, message: "AI not available"}`

5. Wire AIService into AppState and update routes to use it.

6. Add `ai:` section to config YAML files:
   ```yaml
   ai:
     model: "claude-opus-4-5-20250514"
     max_response_tokens: 4096
     system_prompt_token_budget: 1500
     page_context_token_budget: 2000
     history_token_budget: 8000
     max_history_messages: 20
     rate_limit_requests_per_minute: 10
     cache_ttl_seconds: 300
     proposal_ttl_seconds: 300
     insight_refresh_interval_seconds: 300
   ```
   (API key comes from env var, not config file)

## Constraints
- Do NOT modify: `argus/strategies/` (any file)
- Do NOT modify: `argus/core/orchestrator.py` source code. CALL its public methods only.
- Do NOT modify: `argus/core/risk_manager.py` source code. CALL its public methods only.
- Do NOT modify: `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`
- Executors must READ orchestrator/risk_manager to understand their public API, then CALL methods. If the public API does not expose what's needed (e.g., no "update allocation at runtime" method), create a minimal adapter in `argus/ai/executors.py` that interacts with config objects. Document what's needed and flag it in the close-out report.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/ai/test_executors.py`:
    - AllocationChangeExecutor: validate valid input, validate invalid strategy, validate allocation >100% total, re-check passes, re-check fails (regime changed, equity moved, circuit breaker)
    - RiskParamChangeExecutor: validate valid param, validate out-of-range, validate unknown param
    - StrategySuspendExecutor: validate active → suspend, validate already suspended → error
    - StrategyResumeExecutor: validate suspended → resume, validate already active → error
    - GenerateReportExecutor: validate valid report_type, validate unknown type
  - `tests/ai/test_summary.py`: DailySummaryGenerator with mocked trade data and mocked Claude API, insight generation with cache hit/miss
  - `tests/ai/test_service.py`: AIService.handle_chat basic flow (mocked), handle_approve with re-check pass/fail
- Minimum new test count: 15
- Test command: `python -m pytest tests/ai/ -x -q`

## Definition of Done
- [ ] 5 executors implemented with validation
- [ ] 4-condition pre-execution re-check implemented
- [ ] DailySummaryGenerator assembles data from all 5 sources
- [ ] Dashboard insight generation with caching
- [ ] AIService orchestrates all components
- [ ] Config YAML updated with `ai:` section
- [ ] All existing tests pass
- [ ] ≥15 new tests written and passing
- [ ] Executors do not modify orchestrator.py or risk_manager.py source

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Orchestrator source unchanged | `git diff argus/core/orchestrator.py` — empty or import-only |
| Risk Manager source unchanged | `git diff argus/core/risk_manager.py` — empty or import-only |
| Strategy files untouched | `git diff argus/strategies/` — empty |
| Existing config backward compat | Start with config missing `ai:` section — no errors |
| All existing tests pass | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
