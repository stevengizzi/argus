# Sprint 22: Regression Checklist

After each session, verify ALL of the following. Any failure is a blocking issue.

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | All existing pytest pass | `cd /path/to/argus && python -m pytest tests/ -x -q` — expect ≥1,754 passing |
| R2 | All existing Vitest pass | `cd argus/ui && npx vitest run` — expect ≥296 passing |
| R3 | Strategy signal purity | Grep `argus/strategies/` in `git diff` — must be empty. No strategy files modified. |
| R4 | Core orchestrator unchanged | Grep `argus/core/orchestrator.py` in `git diff` — only allowed change: importing from `argus/ai/` in wiring (Session 3b+), never modifying allocation/regime/scheduling logic. |
| R5 | Core risk manager unchanged | Grep `argus/core/risk_manager.py` in `git diff` — only allowed: new import for executor routing (Session 3b+), never modifying gating/approve-with-modification logic. |
| R6 | Execution path unchanged | Grep `argus/execution/` in `git diff` — must be empty. |
| R7 | Data pipeline unchanged | Grep `argus/data/` in `git diff` — must be empty. |
| R8 | Event Bus internals unchanged | Grep `argus/core/event_bus.py` in `git diff` — must be empty. |
| R9 | Existing API signatures preserved | No existing route in `argus/api/routes/` has changed method, path, request body, or response schema. New routes only in `ai.py`. |
| R10 | Existing WebSocket unchanged | `argus/api/ws/` — existing live WS handler untouched. New `ai_chat.py` is additive only. |
| R11 | JWT auth on all new endpoints | Every new REST endpoint requires valid JWT. New WebSocket requires JWT in initial message. Verify with missing/invalid token → 401/403. |
| R12 | Graceful AI-disabled mode | Unset ANTHROPIC_API_KEY, start system. Verify: Dashboard renders (insight card shows "AI not available"), Debrief renders (journal shows empty state), Copilot shows "AI not configured", all non-AI endpoints work normally. |
| R13 | No import side effects | `from argus.ai import ...` does not trigger Claude API calls, does not require ANTHROPIC_API_KEY at import time, does not modify global state. |
| R14 | Config backward compat | System starts with existing config YAML that has no `ai:` section (defaults applied, AI disabled). |
| R15 | DB backward compat | System starts with existing DB that lacks ai_* tables (tables created on startup, no migration errors). |
