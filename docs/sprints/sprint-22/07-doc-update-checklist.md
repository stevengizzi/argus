# Sprint 22: Doc Update Checklist

After all sessions complete:

- [ ] `docs/architecture.md` — Add AI Layer section (Tier 3): ClaudeClient, PromptManager, SystemContextBuilder, tool_use architecture, ConversationManager, ActionManager, executors. Add `WS /ws/v1/ai/chat` endpoint. Add ai_conversations, ai_messages, ai_usage, ai_action_proposals table schemas. Document tool_use flow (Claude → tool_use block → ActionProposal → tool_result → continuation). Document graceful degradation architecture.

- [ ] `docs/decision-log.md` — Add DEC-264 through DEC-274 (11 entries) with full rationale:
  - DEC-264: Full DEC-170 scope in Sprint 22
  - DEC-265 (revised): WebSocket for AI chat (not SSE)
  - DEC-266 (revised): Calendar-date keying with tags
  - DEC-267: Proposal TTL 5 min + DB persistence
  - DEC-268: Per-page context injection hooks
  - DEC-269: Demand-refreshed insight card
  - DEC-270: react-markdown + remark-gfm + rehype-sanitize
  - DEC-271: Claude tool_use for structured proposals
  - DEC-272: 5-type closed action enumeration
  - DEC-273: System prompt template + token budgets
  - DEC-274: Per-call cost tracking

- [ ] `docs/dec-index.md` — Add all 11 new DEC entries with status and one-line summaries.

- [ ] `docs/project-knowledge.md` — Update: current state (Sprint 22 complete), test counts (~1,819 pytest + ~316 Vitest), sprint history table (add Sprint 22 row), monthly costs (add Claude API ~$35–50/mo as Active), key active decisions (add DEC-265–274), architecture section (add AI Layer), file structure (add `argus/ai/` details).

- [ ] `CLAUDE.md` — Update: active sprint, add AI module to project structure section, add AI-related commands (test commands, config paths), note ANTHROPIC_API_KEY requirement, add tool_use architecture summary for Claude Code context.

- [ ] `docs/sprint-history.md` — Add Sprint 22 entry with: session-by-session summary, test count deltas, key decisions, notable implementation details.

- [ ] `config/system.yaml` — Add `ai:` section with all AIConfig defaults (model, token budgets, TTL, rate limits, cost rates).

- [ ] `config/system_live.yaml` — Add `ai:` section matching system.yaml with any live-specific overrides.

- [ ] `docs/live-operations.md` — Add ANTHROPIC_API_KEY to required environment variables. Document AI Copilot operational procedures (cost monitoring, conversation management).

- [ ] `docs/roadmap.md` — Update Sprint 22 status to complete. Note any scope adjustments or deferred items discovered during implementation.

- [ ] `docs/risk-register.md` — Add RSK entries for Claude API dependency, cost overrun, stale approval, tool_use hallucination, aiosqlite contention.
