# Sprint 22, Session 2a: Chat Persistence Layer

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ai/config.py` (created Session 1)
   - `argus/ai/__init__.py` (created Session 1)
   - `argus/analytics/trade_logger.py` (for DB initialization pattern)
   - `argus/api/dependencies.py` (for AppState pattern)
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ≥1,766 tests (1,754 + Session 1 additions), all passing
3. Verify you are on the correct branch: `sprint-22-ai-layer`

## Objective
Create the chat persistence layer: database tables for conversations, messages, and API usage tracking. Build ConversationManager (CRUD + pagination) and UsageTracker. Conversations are keyed by calendar date with optional tags.

## Requirements

1. In `argus/ai/conversations.py`, create `ConversationManager`:
   - DB table `ai_conversations`:
     ```sql
     CREATE TABLE IF NOT EXISTS ai_conversations (
         id TEXT PRIMARY KEY,          -- ULID
         date TEXT NOT NULL,            -- Calendar date YYYY-MM-DD (not trading day)
         tag TEXT DEFAULT 'general',    -- pre-market, session, research, debrief, general
         title TEXT DEFAULT '',         -- Auto-generated or user-set title
         message_count INTEGER DEFAULT 0,
         created_at TEXT NOT NULL,      -- ISO timestamp
         updated_at TEXT NOT NULL       -- ISO timestamp
     );
     CREATE INDEX IF NOT EXISTS idx_conversations_date ON ai_conversations(date);
     CREATE INDEX IF NOT EXISTS idx_conversations_tag ON ai_conversations(tag);
     ```
   - DB table `ai_messages`:
     ```sql
     CREATE TABLE IF NOT EXISTS ai_messages (
         id TEXT PRIMARY KEY,           -- ULID
         conversation_id TEXT NOT NULL,
         role TEXT NOT NULL,            -- 'user', 'assistant'
         content TEXT NOT NULL,         -- Message text
         tool_use_data TEXT,            -- JSON: tool_use blocks from assistant response (if any)
         page_context TEXT,             -- JSON: page context at time of message (for user msgs)
         is_complete BOOLEAN DEFAULT 1, -- False for partial/interrupted streams
         created_at TEXT NOT NULL,
         FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
     );
     CREATE INDEX IF NOT EXISTS idx_messages_conversation ON ai_messages(conversation_id);
     ```
   - Methods:
     - `async def create_conversation(date: str, tag: str = "general") -> dict`
     - `async def get_conversation(conversation_id: str) -> dict | None`
     - `async def list_conversations(date_from: str | None, date_to: str | None, tag: str | None, limit: int = 50, offset: int = 0) -> list[dict]`
     - `async def add_message(conversation_id: str, role: str, content: str, tool_use_data: dict | None = None, page_context: dict | None = None, is_complete: bool = True) -> dict`
     - `async def get_messages(conversation_id: str, limit: int = 50, offset: int = 0) -> list[dict]` — returns oldest-first ordering
     - `async def mark_message_complete(message_id: str, final_content: str)`
     - `async def update_conversation_title(conversation_id: str, title: str)`
     - `async def get_or_create_today_conversation(tag: str = "session") -> dict` — returns existing conversation for today + tag, or creates new one
   - Constructor takes `db_path: str` (same SQLite file as trade logger)
   - `async def initialize()` — creates tables if not exist
   - All JSON fields serialized with `json.dumps` / deserialized with `json.loads`
   - ULID generation using existing `python-ulid` pattern

2. In `argus/ai/usage.py`, create `UsageTracker`:
   - DB table `ai_usage`:
     ```sql
     CREATE TABLE IF NOT EXISTS ai_usage (
         id TEXT PRIMARY KEY,           -- ULID
         conversation_id TEXT,          -- nullable (for non-chat API calls like insight)
         timestamp TEXT NOT NULL,       -- ISO timestamp
         input_tokens INTEGER NOT NULL,
         output_tokens INTEGER NOT NULL,
         model TEXT NOT NULL,
         estimated_cost_usd REAL NOT NULL,
         endpoint TEXT DEFAULT 'chat',  -- chat, insight, summary
         FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
     );
     CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON ai_usage(timestamp);
     CREATE INDEX IF NOT EXISTS idx_usage_conversation ON ai_usage(conversation_id);
     ```
   - Methods:
     - `async def record_usage(conversation_id: str | None, input_tokens: int, output_tokens: int, model: str, estimated_cost_usd: float, endpoint: str = "chat")`
     - `async def get_daily_usage(date: str) -> dict` — returns `{input_tokens, output_tokens, estimated_cost_usd, call_count}`
     - `async def get_monthly_usage(year: int, month: int) -> dict` — returns `{input_tokens, output_tokens, estimated_cost_usd, call_count, daily_breakdown: list}`
     - `async def get_usage_summary() -> dict` — returns `{today, this_month, per_day_average}`
   - Constructor takes `db_path: str`
   - `async def initialize()` — creates table if not exist

3. Ensure table creation happens on system startup. Follow the existing pattern used by Trade Logger for DB initialization. Add `initialize()` calls to the appropriate startup sequence (likely in `argus/api/server.py` lifespan or similar).

4. Note on aiosqlite write contention: AI tables share the SQLite write lock with Trade Logger. This is acceptable for current load. Add a comment in the code noting this for future monitoring: `# NOTE: Shares SQLite write lock with Trade Logger. Monitor latency during active trading + chat. See RSK-NEW-5.`

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`
- Do NOT modify: existing API route signatures
- Do NOT modify: Trade Logger's DB operations or table schemas
- DB tables must be CREATE IF NOT EXISTS — backward compatible with existing DBs

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/ai/test_conversations.py`: create conversation, list with filters (date range, tag), add messages (user + assistant), get messages with pagination (oldest-first), mark incomplete → complete, get_or_create_today, title update, tool_use_data serialization/deserialization
  - `tests/ai/test_usage.py`: record usage, daily aggregation, monthly aggregation with daily breakdown, usage summary, empty state returns zeros
- Minimum new test count: 10
- Test command: `python -m pytest tests/ai/ -x -q`

## Definition of Done
- [ ] ai_conversations, ai_messages, ai_usage tables created on startup
- [ ] ConversationManager CRUD operations work
- [ ] Conversations keyed by calendar date with tag field
- [ ] Messages returned oldest-first
- [ ] UsageTracker records and aggregates usage
- [ ] System starts with existing DB (no ai_* tables) — tables auto-created
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing DB compatible | Start with pre-Session-2a DB file — no errors |
| Trade Logger unaffected | Existing trade logging tests pass |
| No schema conflicts | Verify ai_* table names don't conflict with existing tables |
| All existing tests pass | `python -m pytest tests/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
