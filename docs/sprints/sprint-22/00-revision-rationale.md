# Sprint 22 — Adversarial Revision Rationale

> Decisions made on each Critical and Significant finding from the adversarial review.

---

## C1: SSE vs. WebSocket → **WebSocket**

**Decision:** WebSocket for AI chat streaming. New endpoint `WS /ws/v1/ai/chat`.

**Rationale:** ARGUS already has WebSocket infrastructure (`/ws/v1/live`). Adding SSE creates a second streaming mechanism to maintain permanently. The architecture doc already lists `WS /api/v1/ai/chat`. WebSocket also supports bidirectional communication needed for stream cancellation (client sends cancel frame) and future server-initiated messages (Sprint 23+ proactive alerts).

**DEC-265 revised:** WebSocket for AI chat streaming (was SSE). Reuses existing WS infrastructure patterns.

---

## C2: JSON-in-Text Parsing → **Claude tool_use**

**Decision:** Use Claude's native `tool_use` API for structured action proposals.

**Rationale:** The adversarial review correctly identified that JSON-in-text parsing is fragile. The original rationale against tool_use ("avoids coupling to API features that may change") was weak — tool_use has been stable since GA, is the officially supported mechanism for structured output, and Sprint 23's NLP pipeline will need it anyway. Building a fragile parser now and retrofitting tool_use in Sprint 23 is more total work.

**Flow:** Define tools matching each allowed action type. Claude responds with tool_use blocks when proposing actions. Backend intercepts tool_use, creates ActionProposal, returns tool_result ("Awaiting operator approval"). Claude continues its response. Frontend renders tool_use results as action cards.

**DEC-271 new:** Claude tool_use for structured action proposals. Replaces JSON-in-text parsing (Spec-by-Contradiction item 3 reversed).

---

## C3: System Prompt → **Defined template with token budgets**

**Decision:** System prompt template with explicit sections, behavioral guardrails, and token budgets.

**Prompt structure:** `[system prompt ≤1,500 tokens] + [page context ≤2,000 tokens] + [conversation history ≤8,000 tokens] + [user message]`. Total input budget ~12,000 tokens worst case, well within Opus 200K window with ample room for response.

**Behavioral guardrails:** Advisory only — never recommend specific entries/exits. Always caveat uncertainty. Reference actual data when available. Never fabricate position or P&L data. Identify as ARGUS AI Copilot.

**DEC-273 new:** System prompt template requirements with token budgets and behavioral guardrails.

---

## C4: Action Types → **5-type closed enumeration**

**Decision:** Five allowed action types for Sprint 22 MVP, each with schema and validation.

| Action Type | tool_use Function | Schema | Routes Through |
|---|---|---|---|
| `strategy_allocation_override` | `propose_allocation_change` | `{strategy_id, new_allocation_pct}` | Orchestrator |
| `risk_param_update` | `propose_risk_param_change` | `{param_path, new_value, old_value}` | Risk Manager config |
| `strategy_suspend` | `propose_strategy_suspend` | `{strategy_id, reason}` | Orchestrator |
| `strategy_resume` | `propose_strategy_resume` | `{strategy_id, reason}` | Orchestrator |
| `generate_report` | `generate_report` | `{report_type, params}` | DailySummaryGenerator |

Validation: allocations bounded by 0–100%, must sum to ≤100% across strategies. Risk params bounded by sane ranges defined in AIConfig. Suspend/resume only for strategies in valid state. Unrecognized tool calls treated as errors.

Note: `annotate_trade` and `manual_rebalance` from the original spec are deferred. Annotation is low-value for MVP. Manual rebalance is high-risk with no clear approval UX.

**DEC-272 new:** Closed 5-type action enumeration for Sprint 22 MVP.

---

## C5: Cost Tracking → **ai_usage table + endpoint**

**Decision:** Track input_tokens, output_tokens, and estimated cost per API call. New `ai_usage` table. New `GET /api/v1/ai/usage` endpoint.

**DEC-274 new:** Per-call cost tracking from day one.

---

## S1: Proposal Notifications → **Audio alert + expiry warning**

Action proposal cards trigger a configurable audio notification. Proposals with < 1 minute remaining trigger a second alert. Implemented in Session 5 (Action Cards frontend).

---

## S2: Proposal Persistence → **ai_action_proposals table**

Proposals persisted to DB. On startup, expire any proposals older than TTL. Enables post-hoc analysis. Implemented in Session 3a.

---

## S3: Token Budget → **Defined in C3 above**

Max conversation history: 20 most recent messages OR ~8,000 tokens, whichever is smaller. System prompt ≤1,500 tokens. Page context ≤2,000 tokens. Response budget ≤4,096 tokens (configurable).

---

## S4: Streaming Reconnection → **Re-fetch + reconnect**

On WebSocket disconnect: client re-fetches current conversation via REST API, replaces any partial message with persisted version, reconnects WebSocket. If a stream was in progress, the partial response in the UI is replaced by the full persisted version once available. Implemented in Session 4b.

---

## S5: Conversation Keying → **Calendar date + tag**

**DEC-266 revised:** Conversations keyed by calendar date (not trading day). Optional `tag` field for filtering: "pre-market", "session", "research", "debrief", "general". Supports weekend research and non-trading-day use.

---

## S6: DailySummaryGenerator Inputs → **Explicit data assembly**

Data assembly defined:
- Today's trades: entries, exits, P&L, R-multiples, hold durations
- Orchestrator decisions: regime classification, allocation changes, suspensions
- Risk events: rejections, modifications, circuit breakers
- Performance context: daily/weekly target comparison, running stats
- Strategy breakdown: per-strategy win rate, P&L, trade count

---

## S7: Approval Re-Check → **4-condition gate**

Before executing an approved action:
1. Strategy still exists and is in expected state (active/suspended)
2. Market regime classification unchanged since proposal generation
3. Account equity hasn't moved >5% since proposal
4. No circuit breaker active

Any check failure → execution blocked with explanation returned to chat.

---

## Minor Observations (folded into session prompts)

1. `rehype-sanitize` alongside `react-markdown` → Session 4a
2. Bundle size check after first frontend session → Session 4a
3. Messages render oldest-first in chat → Session 4a
4. Dev mode: "AI not configured" state (no key) / simulated data note (with key) → Session 1 + 4a
5. aiosqlite write contention monitoring note → Session 2a
