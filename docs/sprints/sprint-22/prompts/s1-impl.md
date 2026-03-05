# Sprint 22, Session 1: AI Core Module

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/core/config.py`
   - `argus/ai/__init__.py` (if exists; may be empty)
   - `argus/api/dependencies.py` (for AppState pattern)
   - `docs/architecture.md` (AI Layer section if any, or note its absence)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ≥1,754 tests, all passing
3. Run frontend tests: `cd argus/ui && npx vitest run`
   Expected: ≥296 tests, all passing
4. Verify you are on the correct branch: `git checkout -b sprint-22-ai-layer`

## Objective
Create the foundational `argus/ai/` module: ClaudeClient wrapper with tool_use support, PromptManager with a defined system prompt template and token budgets, SystemContextBuilder for per-page context assembly, ResponseCache, AIConfig Pydantic model, and tool_use function definitions for the 5 allowed action types.

## Requirements

1. In `argus/ai/config.py`, create `AIConfig(BaseModel)` with:
   - `enabled: bool = False` (AI disabled by default when no key)
   - `api_key: str = ""` (populated from env var ANTHROPIC_API_KEY)
   - `model: str = "claude-opus-4-5-20250514"` (DEC-098)
   - `max_response_tokens: int = 4096`
   - `system_prompt_token_budget: int = 1500`
   - `page_context_token_budget: int = 2000`
   - `history_token_budget: int = 8000`
   - `max_history_messages: int = 20`
   - `rate_limit_requests_per_minute: int = 10`
   - `rate_limit_tokens_per_minute: int = 50000`
   - `cache_ttl_seconds: int = 300` (5 min)
   - `proposal_ttl_seconds: int = 300` (5 min)
   - `insight_refresh_interval_seconds: int = 300` (5 min)
   - `cost_per_million_input_tokens: float = 15.0` (Opus pricing)
   - `cost_per_million_output_tokens: float = 75.0`
   - Auto-detect: set `enabled = True` when `api_key` is non-empty.

2. In `argus/core/config.py`, add `ai: AIConfig = AIConfig()` to the root config model. Ensure existing config files without an `ai:` section still parse correctly (AIConfig defaults applied).

3. In `argus/ai/client.py`, create `ClaudeClient`:
   - Constructor takes `AIConfig`. If not enabled, all methods return graceful "AI not available" responses.
   - `async def send_message(messages: list[dict], system: str, tools: list[dict] | None = None, stream: bool = False) -> dict | AsyncGenerator`:
     - Uses `anthropic.AsyncAnthropic` client
     - Includes `tools` parameter when provided (tool_use support)
     - Returns full response dict for non-streaming, async generator of events for streaming
     - Handles rate limiting with exponential backoff (3 retries, then error)
     - Handles API errors gracefully (return structured error, never raise to caller)
     - Tracks token usage: extract `usage.input_tokens` and `usage.output_tokens` from response
     - Returns `(response, usage_record)` tuple where usage_record is `{input_tokens, output_tokens, model, estimated_cost_usd}`
   - `async def send_with_tool_results(messages: list[dict], system: str, tools: list[dict], tool_results: list[dict]) -> dict | AsyncGenerator`:
     - For continuing a conversation after tool_use (append tool_result messages and re-call)
   - All methods are no-ops when `enabled is False`.
   - No API calls at import time. No API calls in constructor.

4. In `argus/ai/tools.py`, define the 5 tool_use function definitions:
   ```python
   ARGUS_TOOLS = [
       {
           "name": "propose_allocation_change",
           "description": "Propose changing a strategy's capital allocation percentage. Requires operator approval before execution.",
           "input_schema": {
               "type": "object",
               "properties": {
                   "strategy_id": {"type": "string", "description": "Strategy identifier (e.g., 'orb_breakout', 'vwap_reclaim')"},
                   "new_allocation_pct": {"type": "number", "description": "New allocation percentage (0-100)", "minimum": 0, "maximum": 100},
                   "reason": {"type": "string", "description": "Brief rationale for the change"}
               },
               "required": ["strategy_id", "new_allocation_pct", "reason"]
           }
       },
       {
           "name": "propose_risk_param_change",
           "description": "Propose changing a risk management parameter. Requires operator approval.",
           "input_schema": {
               "type": "object",
               "properties": {
                   "param_path": {"type": "string", "description": "Dot-notation path to the parameter (e.g., 'risk.daily_loss_limit_pct')"},
                   "new_value": {"type": "number", "description": "Proposed new value"},
                   "old_value": {"type": "number", "description": "Current value for confirmation"},
                   "reason": {"type": "string", "description": "Brief rationale"}
               },
               "required": ["param_path", "new_value", "old_value", "reason"]
           }
       },
       {
           "name": "propose_strategy_suspend",
           "description": "Propose suspending an active strategy. Requires operator approval.",
           "input_schema": {
               "type": "object",
               "properties": {
                   "strategy_id": {"type": "string", "description": "Strategy to suspend"},
                   "reason": {"type": "string", "description": "Why the strategy should be suspended"}
               },
               "required": ["strategy_id", "reason"]
           }
       },
       {
           "name": "propose_strategy_resume",
           "description": "Propose resuming a suspended strategy. Requires operator approval.",
           "input_schema": {
               "type": "object",
               "properties": {
                   "strategy_id": {"type": "string", "description": "Strategy to resume"},
                   "reason": {"type": "string", "description": "Why the strategy should be resumed"}
               },
               "required": ["strategy_id", "reason"]
           }
       },
       {
           "name": "generate_report",
           "description": "Generate and save a report to the Debrief. Does not require approval — executes immediately.",
           "input_schema": {
               "type": "object",
               "properties": {
                   "report_type": {"type": "string", "enum": ["daily_summary", "strategy_analysis", "risk_review"], "description": "Type of report to generate"},
                   "params": {"type": "object", "description": "Optional parameters (e.g., date range, strategy filter)"}
               },
               "required": ["report_type"]
           }
       }
   ]
   ```
   Also create a `TOOLS_REQUIRING_APPROVAL` set: `{"propose_allocation_change", "propose_risk_param_change", "propose_strategy_suspend", "propose_strategy_resume"}`. The `generate_report` tool executes immediately without approval.

5. In `argus/ai/prompts.py`, create `PromptManager`:
   - `build_system_prompt() -> str`: Constructs the system prompt from template. Content:
     ```
     You are the ARGUS AI Copilot, an AI assistant integrated into the ARGUS automated day trading system.

     ## About ARGUS
     ARGUS is a fully automated multi-strategy day trading system for US equities, operated by a single trader based in Taipei, Taiwan. Trading occurs during US market hours (9:30 AM–4:00 PM ET, which is 10:30 PM–5:00 AM Taipei time). The system is designed to generate household income for the operator's family.

     ## Active Strategies
     [Dynamically populated from config: strategy name, window, hold time, key mechanic for each active strategy]

     ## Current Configuration
     [Dynamically populated: risk limits, allocation percentages, regime classification]

     ## Your Role
     - You are ADVISORY ONLY. You help the operator understand system behavior, analyze performance, and propose configuration changes.
     - You NEVER recommend specific trade entries or exits. You do not tell the operator to buy or sell specific stocks.
     - You ALWAYS caveat uncertainty. If you are unsure about data or analysis, say so explicitly.
     - You reference ACTUAL portfolio data, trade history, and system state when available. NEVER fabricate positions, P&L figures, or trade data.
     - When proposing actions (allocation changes, parameter updates, strategy suspend/resume), use the provided tools. The operator must approve all proposals before execution.
     - You can generate reports (daily summaries, strategy analysis, risk reviews) which are saved to the Debrief for later review.

     ## Behavioral Guardrails
     - Do not provide generic financial advice. Your knowledge is specific to ARGUS and its strategies.
     - Do not speculate about market direction. Focus on what the data shows.
     - If asked about something outside your context (e.g., a stock not in the universe, a strategy not implemented), say so.
     - Be concise but thorough. The operator is checking in during overnight hours and values efficient communication.
     ```
   - `build_page_context(page: str, context_data: dict) -> str`: Formats page-specific context within the 2,000-token budget. Truncates data if exceeding budget.
   - `build_conversation_messages(history: list, user_message: str, system: str, page_context: str) -> tuple[str, list[dict]]`: Assembles the final message list. Returns `(system_prompt_with_context, messages)`. Applies history truncation: most recent `max_history_messages` OR messages fitting within `history_token_budget`, whichever is smaller. Token estimation: ~4 chars per token as rough heuristic.
   - The system prompt template is a string constant in the module (not loaded from file). Templates can be versioned in code.

6. In `argus/ai/context.py`, create `SystemContextBuilder`:
   - `async def build_context(page: str, context_data: dict, app_state) -> dict`: Assembles full context payload by combining page context with system-wide state.
   - System-wide state includes: current regime classification, account equity, daily P&L, active strategy count, any active circuit breakers, current time (ET and Taipei).
   - Per-page context varies by page name. Define context schemas for all 7 pages:
     - Dashboard: portfolio summary, positions, daily P&L, regime
     - Trades: recent trades (last 20), filters applied
     - Performance: performance metrics, selected timeframe
     - Orchestrator: strategy allocations, regime, schedule state
     - Pattern Library: selected pattern, pattern stats
     - Debrief: today's summary data, selected conversation
     - System: system health, connection states, config
   - Returns a dict that PromptManager will format into text.

7. In `argus/ai/cache.py`, create `ResponseCache`:
   - Simple TTL-based dict cache keyed by `(endpoint, params_hash)`.
   - `async def get(key: str) -> dict | None`
   - `async def set(key: str, value: dict, ttl: int | None = None)`
   - `async def invalidate(key: str)`
   - Used primarily for Dashboard insight caching.

8. In `argus/ai/__init__.py`, export all public classes.

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`
- Do NOT make API calls at import time or in constructors
- Do NOT require ANTHROPIC_API_KEY to be set for imports or config parsing
- The `anthropic` package must be imported lazily (only when ClaudeClient methods are called) or handled gracefully if not installed

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/ai/test_client.py`: ClaudeClient with mocked anthropic SDK (send_message, streaming, error handling, rate limit backoff, disabled mode returns graceful response, usage tracking)
  - `tests/ai/test_prompts.py`: PromptManager system prompt generation, page context formatting, history truncation (>20 messages, >8K tokens), token budget enforcement
  - `tests/ai/test_context.py`: SystemContextBuilder for each page type, system-wide state assembly
  - `tests/ai/test_cache.py`: ResponseCache get/set/invalidate, TTL expiry
  - `tests/ai/test_config.py`: AIConfig defaults, enabled auto-detection, config without `ai:` section backward compat
  - `tests/ai/test_tools.py`: Tool definitions valid JSON schema, TOOLS_REQUIRING_APPROVAL set correct
- Minimum new test count: 12
- Test command: `python -m pytest tests/ai/ -x -q`

## Definition of Done
- [ ] All 7 new files created in `argus/ai/`
- [ ] AIConfig added to root config with backward compat
- [ ] System prompt template contains all required sections (ARGUS description, strategies, guardrails)
- [ ] Tool definitions for all 5 action types with valid schemas
- [ ] All existing tests pass
- [ ] ≥12 new tests written and passing
- [ ] `from argus.ai import ClaudeClient, PromptManager, SystemContextBuilder` works without API key set
- [ ] Config file without `ai:` section parses without error

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing config files parse | Start system with existing config — no errors |
| No import side effects | `python -c "from argus.ai import ClaudeClient"` succeeds with no API key |
| All existing tests pass | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md — paste full content here when assembling final prompt]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md — paste full content here when assembling final prompt]
