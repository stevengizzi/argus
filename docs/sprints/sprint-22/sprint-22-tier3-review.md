# Tier 3 Architectural Review: Sprint 22 — AI Layer MVP

**Date:** 2026-03-07
**Reviewer:** Claude.ai (Tier 3)
**Sprint:** 22 — AI Layer MVP + Copilot Activation
**Branch:** `sprint-22-ai-layer`
**Sessions reviewed:** 9 implementation + 5 fix sessions + 9 Tier 2 reviews

---

## 1. Sprint Goal Assessment

**Verdict: ACHIEVED — with 8 items requiring a cleanup session before close-out.**

All 12 deliverables from the Sprint Spec are implemented:

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 1 | Claude API integration module | ✅ Complete | 11 files in `argus/ai/`, ClaudeClient, PromptManager, SystemContextBuilder, ResponseCache, AIConfig |
| 2 | Tool definitions module | ✅ Complete | 5 tools, schema validation, TOOLS_REQUIRING_APPROVAL set |
| 3 | Persistent chat infrastructure | ✅ Complete | 3 SQLite tables, ConversationManager, UsageTracker |
| 4 | WebSocket streaming endpoint | ✅ Complete | WS `/ws/v1/ai/chat`, JWT auth, tool_use round-trips |
| 5 | Chat REST API | ✅ Complete | 6 REST endpoints + actions pending endpoint |
| 6 | Approval workflow | ✅ Complete | ActionProposal model, DB persistence, TTL, 4-condition re-check, Event Bus |
| 7 | AI content generation | ✅ Complete | DailySummaryGenerator, Dashboard insight endpoint |
| 8 | Live Copilot UI | ✅ Complete | Full chat interface, markdown rendering, XSS protection |
| 9 | Copilot integration | ✅ Complete | Context hooks on all 7 pages, keyboard shortcuts, reconnection |
| 10 | Action card UI | ✅ Complete | 6 status states, countdown, audio notifications, confirmation dialogs |
| 11 | Dashboard AI insight card | ✅ Complete | Auto-refresh during market hours, graceful degradation |
| 12 | Debrief integration | ✅ Complete | Learning Journal conversation browser, date/tag filtering |

**Test counts:**
- pytest: 1,972 (↑218 from 1,754 baseline)
- Vitest: 366 (↑70 from 296 baseline)
- Total new tests: 288 (vs. ~85 target — 3.4× the estimate)

**New code volume:** ~6,500 lines backend (`argus/ai/` + AI routes + WS handler), ~3,000+ lines frontend.

---

## 2. Scope Boundary Verification

All Spec by Contradiction boundaries held:

- `argus/strategies/` — **no changes** ✅
- `argus/core/orchestrator.py` — **no changes** ✅
- `argus/core/risk_manager.py` — **no changes** ✅
- `argus/execution/` — **no changes** ✅
- `argus/data/` — **no changes** ✅
- `argus/backtest/` — **no changes** ✅
- `argus/core/event_bus.py` — **no changes** ✅
- `argus/core/events.py` — **no changes** ✅
- Existing API routes — **signatures unchanged** ✅
- `/ws/v1/live` — **untouched** ✅

No escalation criteria were triggered across any of the 9 Tier 2 reviews.

---

## 3. Architectural Findings

### 3.1 CRITICAL: YAML Config Field Names Don't Match AIConfig Model

**Severity:** High — config values are silently ignored.

`config/system.yaml` uses field names that don't match `AIConfig`:

| YAML Field | AIConfig Field | Effect |
|------------|---------------|--------|
| `system_context_max_tokens: 2000` | `system_prompt_token_budget` (default: 1500) | YAML ignored, default 1500 used |
| `page_context_max_tokens: 1500` | `page_context_token_budget` (default: 2000) | YAML ignored, default 2000 used |
| `history_max_tokens: 4000` | `history_token_budget` (default: 8000) | YAML ignored, default 8000 used |
| `requests_per_minute: 20` | `rate_limit_requests_per_minute` (default: 10) | YAML ignored, default 10 used |
| `api_key_env: "ANTHROPIC_API_KEY"` | (no matching field) | YAML ignored |

Pydantic `BaseModel` silently ignores unknown fields by default. Every value in the YAML `ai:` section except `model` and `proposal_ttl_seconds` is being dropped. This means the system is running on code defaults, not the operator-specified config.

**Fix:** Rename YAML fields to match AIConfig exactly, or add `model_config = ConfigDict(populate_by_name=True)` with `Field(alias=...)` mappings.

### 3.2 AIService Built But Never Wired

**Severity:** Medium — dead code, 23K lines of `argus/ai/service.py`.

`AIService` was built in Session 3b as an orchestration layer with methods: `handle_chat()`, `handle_approve()`, `handle_reject()`, `get_insight()`. It's registered in `AppState` but never initialized in `server.py` and never called from any route. The routes call `ConversationManager`, `ActionManager`, and `ClaudeClient` directly.

This creates two problems: duplicated orchestration logic between routes and AIService, and a 23K-line file that serves no purpose.

**Fix (choose one):**
- **Option A (recommended):** Remove `service.py` and the `ai_service` field from `AppState`. The direct-call pattern in routes is working and simpler. Re-introduce when needed for Sprint 23 NLP pipeline.
- **Option B:** Wire `AIService` into routes. This is a larger change and risks regressions.

### 3.3 Model ID Inconsistency

**Severity:** Medium — contradicts DEC-098.

- `AIConfig` default: `claude-opus-4-5-20251101`
- `config/system.yaml` override: `claude-sonnet-4-20250514`
- DEC-098 mandates: Claude Opus

The YAML overrides the Opus default with Sonnet. Since DEC-098's rationale is "cost is trivial relative to trading capital," Opus should be used. The fix prompt should set the YAML to match the AIConfig default or use the latest Claude Opus model string.

### 3.4 Proposal State Lost on WebSocket Reconnect

**Severity:** Medium — user-reported issue (#4).

When WebSocket disconnects and reconnects, `syncConversationFromRest()` replaces messages from REST. Messages from REST include `tool_use_data` with `proposalId`, and `ActionCardList` creates proposal entries in the Zustand store from this data — but using stale defaults (status: `'pending'`, expiresAt: 5 minutes from NOW). The actual server-side proposal may have expired, been approved, or been rejected.

The `fetchPendingProposals()` API function exists in `api.ts` but is never called on reconnect.

**Fix:** After `syncConversationFromRest()`, call `fetchPendingProposals()` for the current conversation and update the proposals store with actual server-side status. For proposals that have been resolved (approved/rejected/expired), update their status in the store.

### 3.5 `system_live.yaml` Missing AI Section

**Severity:** Low-Medium — will matter at go-live.

The live trading config file has no `ai:` section. When transitioning to live trading with AI enabled, the operator will need to add this manually. If forgotten, AI will be disabled in live mode (safe failure, but confusing).

**Fix:** Add `ai:` section to `system_live.yaml` matching corrected `system.yaml` field names.

### 3.6 Code Hygiene Items

**Inline json import:** `import json as json_module` appears twice inside functions in `ai_chat.py` (lines 344, 423). Should be a top-level import.

**Debug comments:** `ai_chat.py` retains `# DEBUG:` comments (line 282) from the diagnostic session. The `logger.debug()` calls are fine (won't show in production), but the comments should be cleaned to `# Log stream events for diagnostics` or similar.

**f-string in logger:** `ai_chat.py:411` uses `logger.info(f"Stream cancelled...")` instead of `logger.info("Stream cancelled for conversation %s", conversation_id)`.

---

## 4. User-Reported Issues — Analysis and Fix Design

### 4.1 Smoother Streaming (User Note #1)

**Problem:** StreamingMessage re-renders on every token, causing markdown to re-parse on each character addition. This creates visual jitter as react-markdown rebuilds the DOM.

**Fix:** Implement a token buffer. Accumulate tokens in a buffer and flush to the Zustand store on a `requestAnimationFrame` cadence (~16ms). This batches multiple tokens per render while maintaining real-time feel. The `appendStreamingContent` action in the store should continue as-is; the buffering happens in the WebSocket handler.

Implementation: In `api.ts` `handleMessage`, instead of immediately calling `store.appendStreamingContent(data.content)` on each `token` event, accumulate in a local buffer string. On each `requestAnimationFrame`, if the buffer is non-empty, flush it to the store and clear the buffer. Cancel the rAF on stream end.

### 4.2 Ticker Formatting (User Note #2)

**Problem:** Stock tickers ($NVDA, AAPL, etc.) render as plain text in assistant responses.

**Fix:** Add a custom ReactMarkdown text component that detects ticker patterns (e.g., `/\$?[A-Z]{1,5}\b/` when preceded by `$` or when matching known market patterns) and wraps them in a styled `<span>`. The pattern should be conservative to avoid false positives — require `$` prefix (e.g., `$NVDA`) or limit to all-caps 1-5 letter words that appear near trading context.

Recommended approach: Add a custom `remark` plugin or use the `components` prop on ReactMarkdown to override the `text` node renderer. Apply to both `ChatMessage` and `StreamingMessage`.

Styling: Use a distinct background (e.g., `bg-argus-surface px-1 rounded font-mono text-argus-accent text-xs`) to visually distinguish tickers.

### 4.3 Duplicate Keyboard Shortcuts (User Note #3)

**Problem:** Both `c` (DEC-199, Sprint 21d) and `Cmd/Ctrl+K` (Sprint 22) toggle the Copilot panel.

**Recommendation:** Remove `c`. Keep `Cmd/Ctrl+K` because it's the standard "command palette" / "quick action" keyboard convention (used by VS Code, Slack, Notion, etc.), works even when focused in an input field, and won't conflict with future text-entry shortcuts. The `c` shortcut is non-standard and blocks the character from being used as a navigation shortcut later.

### 4.4 Action Card Disappears on Reconnect (User Note #4)

See finding 3.4 above. Fix: call `fetchPendingProposals()` during reconnection sync, update proposal store with server-side state.

### 4.5 Keyboard Shortcuts for Approve/Reject (User Note #5)

**Fix:** When an ActionCard is in `pending` state and the Copilot panel is focused:
- `Enter` or `y` → open Approve confirmation dialog
- `Escape` or `n` → open Reject dialog
- When a confirmation modal is open: `Enter` → confirm, `Escape` → cancel

Implementation: Add a `useEffect` with `keydown` listener in `ActionCard.tsx` that checks if the proposal is pending and the panel is open. Guard against conflicts with ChatInput by checking if the active element is a textarea.

### 4.6 Auto-Scroll for Action Cards (User Note #6)

**Problem:** The auto-scroll `useEffect` in `MessageList` triggers on `streamingContent` changes but not on message finalization (which is when ActionCards are added).

**Fix:** Add `messages.length` to the auto-scroll dependency array for the "scroll to bottom on new messages" effect. The existing `useEffect` at line 225 already scrolls on `[messages]` but it scrolls unconditionally; it should also respect `isNearBottomRef`. Update the logic: on new message, if user was near bottom, scroll to bottom.

### 4.7 Report Click-Through (User Note #7)

**Problem:** When `generate_report` executes, the ActionCard shows "Report generation queued" but doesn't link to the result.

**Fix:** The `generate_report` executor should return structured result data including the report content or a navigation path. The ActionCard's `executed` state for `generate_report` should render the report content inline (expandable) or a "View Report" link. In dev mode, this won't have real data since AI services aren't fully active — it requires a live Claude API response.

For the fix prompt: modify the `generate_report` ActionCard rendering to show a "View Report" expandable section when the result contains content, and modify the executor to include content in its response.

---

## 5. Live Testing Guidance

Yes — dev-mode testing validates the plumbing but not the actual AI behavior. The key differences in live:

1. **Real Claude API responses:** Streaming behavior, token latency, tool_use triggering, and response quality can only be assessed with live API calls. Dev mode uses the API key directly, but the data context is simulated.

2. **Real market data context:** The `SystemContextBuilder` and `useCopilotContext` hooks assemble real strategy states, positions, and performance data during live sessions. In dev mode, much of this is empty or mocked.

3. **Approval workflow end-to-end:** You need Claude to actually propose an action (via tool_use), see it appear as an ActionCard, approve it, and watch the 4-condition re-check + executor run. This requires real trading context.

**Recommended testing plan:**

Run during a paper trading session with `ANTHROPIC_API_KEY` set and `ai.enabled: true` in config. Paper mode (port 4002) gives real market data without financial risk. Test each tool type by prompting Claude explicitly: "I think ORB Breakout's allocation is too high — what do you suggest?" should trigger `propose_allocation_change`. Test the reject and timeout flows too.

Monitor `GET /api/v1/ai/usage` to validate cost tracking accuracy. Compare estimated costs against the Anthropic dashboard.

---

## 6. Consolidated Fix Prompt

> **This is a single Claude Code session prompt to address all issues before sprint close-out.**

---

### Sprint 22 Fix Session: Cleanup + User Issues

#### Pre-Flight Checks

Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-22/02-sprint-spec-v2.md`
   - `argus/ai/config.py`
   - `argus/ui/src/features/copilot/api.ts`
   - `argus/ui/src/features/copilot/CopilotPanel.tsx`
   - `argus/ui/src/features/copilot/ActionCard.tsx`
   - `argus/ui/src/features/copilot/ChatMessage.tsx`
   - `argus/ui/src/features/copilot/StreamingMessage.tsx`
   - `argus/ui/src/layouts/AppShell.tsx`
2. Run the test suite: `python -m pytest tests/ -x -q` — Expected: 1,972 tests, all passing
3. Run frontend tests: `cd argus/ui && npx vitest run` — Expected: 366 tests, all passing
4. Verify you are on branch: `sprint-22-ai-layer`

#### Objective

Fix 10 issues: 3 architectural bugs, 7 UX improvements from visual review. This is the final session before Sprint 22 close-out.

#### Requirements

**Fix 1: YAML Config Field Names (CRITICAL)**

In `config/system.yaml`, rename the `ai:` section fields to match `AIConfig` exactly:

```yaml
ai:
  model: "claude-opus-4-5-20251101"
  system_prompt_token_budget: 1500
  page_context_token_budget: 2000
  history_token_budget: 8000
  rate_limit_requests_per_minute: 20
  proposal_ttl_seconds: 300
  insight_refresh_interval_seconds: 60
  cost_per_million_input_tokens: 15.0
  cost_per_million_output_tokens: 75.0
```

Remove `api_key_env` (not a real config field — the key comes from env var via model validator). Set model to `claude-opus-4-5-20251101` per DEC-098 (Opus, not Sonnet). Add the same section to `config/system_live.yaml`.

Write a test in `tests/ai/test_config.py` that loads `config/system.yaml` and verifies all `ai:` fields are recognized by `AIConfig` (no silently ignored fields). Use `model_config = ConfigDict(extra='forbid')` consideration: if adding `extra='forbid'` to AIConfig would break other things, instead write the test to compare YAML keys against AIConfig field names.

**Fix 2: Remove Dead AIService Code**

Delete `argus/ai/service.py`. Remove the `AIService` import and `ai_service` field from `argus/api/dependencies.py` (AppState). Remove the `from argus.ai.service import AIService` TYPE_CHECKING import. Remove `ai_service` from `argus/ai/__init__.py` exports. Remove `tests/ai/test_service.py`.

**Fix 3: Code Hygiene in ai_chat.py**

In `argus/api/websocket/ai_chat.py`:
- Move `import json` to the top of the file (replace both inline `import json as json_module`). Change all `json_module.` references to `json.`.
- Change the `# DEBUG: Log all events to diagnose tool_use processing` comment (line 282) to `# Log stream events for diagnostics`.
- Change `logger.info(f"Stream cancelled for conversation {conversation_id}")` to `logger.info("Stream cancelled for conversation %s", conversation_id)`.

**Fix 4: Smoother Streaming with Token Buffer**

In `argus/ui/src/features/copilot/api.ts`, modify the `handleMessage` method:
- Add a private `tokenBuffer: string = ''` and `rafId: number | null = null` to the `CopilotWebSocketManager` class.
- In the `'token'` case, instead of directly calling `store.appendStreamingContent(data.content)`, append to `this.tokenBuffer` and schedule a `requestAnimationFrame` flush if one isn't already scheduled.
- The flush callback: if `tokenBuffer` is non-empty, call `store.appendStreamingContent(this.tokenBuffer)`, clear the buffer, and set `rafId = null`.
- In `'stream_end'`, flush any remaining buffer immediately (cancel any pending rAF, call appendStreamingContent with remaining buffer), then proceed with `finalizeStreamingMessage`.
- In `'error'` and disconnect handlers, also flush/clear the buffer.

**Fix 5: Ticker Visual Formatting**

Create a utility function `formatTickers` in `argus/ui/src/utils/format.ts` that takes a string and returns React elements with tickers styled differently. Alternatively (and more simply), add a custom `p` component override in the ReactMarkdown `components` prop used by both `ChatMessage.tsx` and `StreamingMessage.tsx`:

Create a shared component file `argus/ui/src/features/copilot/TickerText.tsx`:
```tsx
// Detect $TICKER patterns and wrap in styled spans
// Pattern: $ followed by 1-5 uppercase letters, at a word boundary
const TICKER_REGEX = /(\$[A-Z]{1,5})\b/g;

export function TickerText({ children }: { children: string }) {
  if (typeof children !== 'string') return <>{children}</>;
  
  const parts = children.split(TICKER_REGEX);
  if (parts.length === 1) return <>{children}</>;
  
  return (
    <>
      {parts.map((part, i) =>
        TICKER_REGEX.test(part) ? (
          <span key={i} className="px-1 py-0.5 bg-argus-surface rounded font-mono text-argus-accent text-xs font-medium">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}
```

In the ReactMarkdown `components` prop for both ChatMessage and StreamingMessage, override the `text` renderer (or the `p` component's children processing) to use `TickerText` for string children. Note: ReactMarkdown's custom components receive children, so apply the ticker formatting to text nodes within paragraphs and list items.

Reset the regex lastIndex before each use since it's global.

**Fix 6: Remove Duplicate 'c' Keyboard Shortcut**

In `argus/ui/src/layouts/AppShell.tsx`, remove the `'c'` key handler (lines 97-100):
```typescript
// Remove this block:
if (e.key === 'c') {
  toggleCopilot();
}
```

Keep the `Cmd/Ctrl+K` handler. Update any comments referencing `'c' for copilot`.

**Fix 7: Proposal Sync on Reconnect**

In `argus/ui/src/features/copilot/api.ts`, in the `syncConversationFromRest()` method, after syncing messages, fetch pending proposals:

```typescript
// After store.setMessages(messages):
try {
  const pendingResponse = await fetchPendingProposals(conversationId);
  if (pendingResponse?.proposals) {
    const store = useCopilotUIStore.getState();
    for (const proposal of pendingResponse.proposals) {
      store.setProposal({
        id: proposal.id,
        toolName: proposal.tool_name,
        toolInput: proposal.tool_input,
        status: proposal.status,
        expiresAt: proposal.expires_at,
      });
    }
  }
} catch (err) {
  console.error('CopilotWS: Failed to sync proposals', err);
}
```

Check the `PendingProposalsResponse` type and the actual response shape from `GET /api/v1/ai/actions/pending` to ensure the field names are correct.

**Fix 8: Keyboard Shortcuts for Action Cards**

In `argus/ui/src/features/copilot/ActionCard.tsx`, add a `useEffect` that listens for keyboard events when the proposal is in `pending` state:

```typescript
useEffect(() => {
  if (proposal.status !== 'pending') return;
  
  const handleKeyDown = (e: KeyboardEvent) => {
    // Don't capture if typing in textarea
    const target = e.target as HTMLElement;
    if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') return;
    
    if (e.key === 'y' || (e.key === 'Enter' && !showConfirm && !showReject)) {
      e.preventDefault();
      handleApproveClick();
    } else if (e.key === 'n') {
      e.preventDefault();
      handleRejectClick();
    }
  };
  
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [proposal.status, showConfirm, showReject]);
```

For the confirmation dialog, add Enter to confirm and Escape to cancel (these may already be handled by the dialog component — verify). Show keyboard hint text on the action buttons: "Y to approve · N to reject" in small text below the buttons.

**Fix 9: Auto-Scroll for Action Cards**

In `argus/ui/src/features/copilot/CopilotPanel.tsx`, the `MessageList` component's auto-scroll for new messages (line 225-231) scrolls unconditionally. Modify it to also respect the `isNearBottomRef` check, similar to the streaming scroll:

```typescript
// Auto-scroll to bottom on new messages (if user is near bottom)
useEffect(() => {
  const container = scrollContainerRef.current;
  if (container && isNearBottomRef.current) {
    container.scrollTop = container.scrollHeight;
  }
}, [messages, messages.length]);
```

The key change: add `messages.length` explicitly so React tracks the array length change (since the messages array reference changes on finalization). And add the `isNearBottomRef.current` guard (currently missing — existing code scrolls unconditionally on every messages change, which can be jarring if the user has scrolled up to review history).

**Fix 10: Report Click-Through in Action Cards**

In `argus/ui/src/features/copilot/ActionCard.tsx`, for the `generate_report` tool type in the `executed` state, render the result content if available:

```tsx
{proposal.status === 'executed' && proposal.toolName === 'generate_report' && proposal.result && (
  <div className="mt-2 p-2 bg-argus-bg rounded text-xs max-h-40 overflow-y-auto">
    <p className="text-argus-text-dim mb-1 font-medium">Generated Report:</p>
    <div className="prose prose-sm prose-invert max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
        {typeof proposal.result === 'string' ? proposal.result : JSON.stringify(proposal.result, null, 2)}
      </ReactMarkdown>
    </div>
  </div>
)}
```

This requires adding `ReactMarkdown`, `remarkGfm`, and `rehypeSanitize` imports to ActionCard.tsx. If the result is too large for inline display, add a "Show/Hide Report" toggle.

Also update the `ProposalState` type in `copilotUI.ts` to ensure `result` can hold string content (it may already be `string | Record<string, unknown> | undefined` — verify).

#### Constraints

- Do NOT modify: `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/data/`, `argus/backtest/`, `argus/core/event_bus.py`
- Do NOT modify existing API route signatures (only modify implementations)
- Do NOT modify existing test assertions (only add new tests or update tests affected by the changes above)

#### Test Targets

After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test that `config/system.yaml` `ai:` field names match AIConfig model fields
  2. Test token buffer flush behavior (mock rAF, verify batching)
  3. Test `TickerText` component renders tickers with correct styling
  4. Test that `fetchPendingProposals` is called during reconnection
  5. Test keyboard shortcuts (y/n) trigger approve/reject flows
  6. Test auto-scroll fires on message count change
- Minimum new test count: 6
- Backend test command: `python -m pytest tests/ -x -q`
- Frontend test command: `cd argus/ui && npx vitest run`

#### Definition of Done

- [ ] All 10 fixes implemented
- [ ] All existing tests pass (1,972 pytest + 366 Vitest, minus test_service.py removal)
- [ ] New tests written and passing
- [ ] No TypeScript errors in modified files
- [ ] YAML config verified to load correctly with corrected field names

#### Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Config loads without error | `python -c "from argus.core.config import load_config; load_config('config/system.yaml')"` |
| AI module imports cleanly | `python -c "from argus.ai import ClaudeClient, ActionManager"` (no AIService) |
| Streaming still works | Manual test: send message in Copilot, verify tokens appear |
| Shortcuts don't conflict | Press 'c' — should NOT open Copilot. Press Cmd+K — SHOULD open Copilot |
| Reconnection syncs proposals | Disconnect WS (toggle network), reconnect, verify ActionCards persist |
| Auto-scroll on ActionCard | Send message that triggers tool_use, verify ActionCard scrolls into view |

#### Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

---

## 7. Meta-Analysis: Sprint Cycle Procedure

### 7.1 What Went Well

1. **Adversarial review caught real issues.** The pre-implementation adversarial review identified the SSE/WebSocket contradiction and the JSON-in-text vs. tool_use decision — both would have caused significant rework mid-sprint.

2. **Session splitting prevented larger disasters.** The a/b session splits (2a/2b, 3a/3b, 4a/4b) were essential. Even with splitting, Sessions 3a and 3b compacted, which means they would have been unrecoverable as single sessions.

3. **Tier 2 reviews were consistently useful.** Every Tier 2 review caught accurate findings and produced correct verdicts. The structured review format worked.

4. **Test volume exceeded targets dramatically.** 288 new tests vs. 85 planned. This is good — the implementation sessions took testing seriously.

### 7.2 Problems Identified

**Problem 1: Fix sessions were unplanned and accumulated.**

5 fix sessions were run during the sprint (4a fix ×2, 3b fix, 2b fix, model ID fix). These were not anticipated in the session breakdown or compaction risk assessment. Each fix session consumed context window and developer time.

**Root cause:** Visual review items and integration bugs weren't discovered until later sessions. The fix sessions were reactive.

**Proposed protocol change:** Add a "Visual Review + Integration Fix" session slot after each frontend session pair (e.g., after 4a+4b, budget a 4c fix session). This is cheaper than running unplanned fix sessions that don't follow the standard prompt template. For the sprint-planning protocol, add to Phase A step 5 (compaction risk assessment):

> For frontend sessions that include visual review items, budget an additional 0.5-session fix allowance. If the visual review discovers no issues, the slot is not used. If it discovers issues, the fix session is already planned.

**Problem 2: Config field name mismatch escaped all reviews.**

9 Tier 2 reviews and the adversarial review all missed that the YAML config fields don't match the Pydantic model. This is because:
- The code review only checks that the YAML "parses without error" (it does — Pydantic silently ignores unknown fields)
- No test validates that YAML fields actually map to the model
- The adversarial review focused on architecture, not config plumbing

**Proposed protocol change:** Add to the Sprint Spec template a "Config Changes" section that explicitly maps new YAML fields to their Pydantic model fields. Add to the regression checklist template: "New config fields verified against Pydantic model (no silently ignored keys)." The implementation prompt template should include: "If adding new config fields, write a test that loads the YAML and verifies no keys are silently dropped."

**Problem 3: AIService was built but never integrated.**

Session 3b built `argus/ai/service.py` (a significant orchestration class), but no session was responsible for wiring it into the routes. The routes were already built (Session 2b) with direct calls to individual managers. The design summary listed AIService but didn't specify which session would wire it in.

**Proposed protocol change:** In Phase A of sprint planning, when decomposing sessions, explicitly answer: "For each module created, which session is responsible for integrating it into the calling code?" This is a dependency question that the current session breakdown doesn't require. Add to the Session Breakdown template:

> For each session, list: **Creates** (new files), **Modifies** (existing files), **Integrates** (which prior session's output does this session wire in).

**Problem 4: Compaction scoring was qualitative and under-predicted.**

Already addressed by DEC-275 (quantitative point-based scoring). The sprint-planning protocol templates in the project already reflect this change. No further action needed — this is a success story of the process self-correcting.

**Problem 5: Sprint-level test target was dramatically under-estimated.**

85 estimated vs. 288 actual. While over-delivering on tests is good, a 3.4× miss suggests the estimation model is wrong. The issue is that each session's test estimate was per-feature, but integration tests and edge case tests multiplied.

**Proposed protocol change:** When estimating session test counts in Phase A, apply a 2× multiplier for sessions that create new infrastructure (DB schemas, API routes, WebSocket handlers) because integration tests add up. Use `~5 per new file + ~3 per modified file + ~2 per API endpoint` as a baseline formula.

### 7.3 Summary of Proposed Protocol Changes

| Change | Affects | Priority |
|--------|---------|----------|
| Budget visual-review fix sessions for frontend sprints | sprint-planning.md, Phase A step 5 | High |
| "Config Changes" section in Sprint Spec template | sprint-spec.md | High |
| Config field ↔ Pydantic model validation in regression checklist | regression checklist template | High |
| "Integrates" column in Session Breakdown | sprint-planning.md, design-summary.md | Medium |
| Test count estimation formula | sprint-planning.md, Phase A | Low |

---

## 8. Doc Update Checklist (Copy-Paste Ready Content)

These doc updates should be done during a doc-sync session. I'm providing the content for the most critical updates; the rest should follow the existing templates.

### 8.1 `docs/decision-log.md` — New DEC Entries

**DEC-264:** Full DEC-170 Scope in Sprint 22
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Implement the full scope of DEC-170 (AI Copilot with approval workflow, context injection, persistent conversations, daily summaries, insight card, learning journal) in a single sprint rather than phasing across multiple sprints.

**Alternatives Rejected:**
1. Phase 1/Phase 2 split (chat only → approval workflow): Rejected because the approval workflow is the architecturally interesting part and testing it requires the full pipeline.
2. Backend-only sprint + frontend sprint: Rejected because validating the UX requires end-to-end testing in the same sprint cycle.

**Rationale:**
The Copilot shell was already built (Sprint 21d). The backend and frontend are tightly coupled for this feature — splitting would mean the shell sits unused for another sprint. Steven's "build complete, not phased" principle applies.

**Constraints:**
Sprint 22 is the largest sprint to date (9 sessions). Compaction risk managed via a/b session splits.

**Supersedes:** N/A
**Cross-References:** DEC-170, DEC-212

---

**DEC-265 (revised):** WebSocket for AI Chat Streaming
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Use WebSocket (`WS /ws/v1/ai/chat`) for AI chat streaming, not Server-Sent Events (SSE). JWT auth token sent in initial message, matching existing `/ws/v1/live` pattern.

**Alternatives Rejected:**
1. SSE (Server-Sent Events): Rejected because SSE is unidirectional (server→client only). WebSocket supports bidirectional communication needed for stream cancellation, and future server-initiated messages.
2. Long polling: Rejected — adds latency, complexity, and doesn't support streaming.

**Rationale:**
ARGUS already has WebSocket infrastructure (`/ws/v1/live`). Reusing the same transport and auth pattern reduces complexity. WebSocket also enables future features like server-initiated alerts (Sprint 23+).

**Constraints:**
Must coexist with existing `/ws/v1/live` endpoint. Separate router, separate connection set.

**Supersedes:** Original DEC-265 (which had SSE/WebSocket contradiction)
**Cross-References:** DEC-170, DEC-099

---

**DEC-266 (revised):** Calendar-Date Conversation Keying with Tags
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Key conversations by calendar date (not trading day) with an optional tag field. Valid tags: "pre-market", "session", "research", "debrief", "general" (default).

**Alternatives Rejected:**
1. Trading-day keying: Rejected because trading days have ambiguous boundaries (pre-market for Monday starts Sunday night) and weekend research conversations wouldn't belong to any trading day.
2. No tags: Rejected because filtering by conversation type is valuable for the Learning Journal.

**Rationale:**
Calendar date is unambiguous. Tags provide flexible categorization without rigid structure. Tags auto-assigned by page context (e.g., Dashboard → "session", Performance → "research").

**Constraints:**
Tag validation enforced in ConversationManager. Invalid tags raise ValueError.

**Supersedes:** Original DEC-266 (which only specified date keying, not tags)
**Cross-References:** DEC-170, DEC-268

---

**DEC-267:** Action Proposal TTL with DB Persistence
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Action proposals have a 5-minute TTL (configurable in AIConfig.proposal_ttl_seconds). Proposals are persisted to `ai_action_proposals` SQLite table. Expired proposals cleaned on startup and via periodic 30-second cleanup task.

**Alternatives Rejected:**
1. In-memory proposals: Rejected because proposals would be lost on restart, creating safety ambiguity (was it approved before the crash?).
2. Longer TTL (15 min): Rejected because market conditions change rapidly. 5 minutes is enough to review but short enough that stale proposals auto-expire.

**Rationale:**
DB persistence ensures audit trail and restart safety. Short TTL prevents stale approvals. Periodic cleanup prevents table growth.

**Constraints:**
Shares SQLite write lock with other AI tables and Trade Logger (RSK-NEW-5).

**Supersedes:** N/A
**Cross-References:** DEC-272, RSK-NEW-3, RSK-NEW-5

---

**DEC-268:** Per-Page Context Injection Hooks
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Each of the 7 Command Center pages provides context to the AI Copilot via a `useCopilotContext` hook. Context includes page name, selected entity (if any), and key visible data. Context is registered in the Zustand store and included in API calls.

**Alternatives Rejected:**
1. Global context only (no per-page): Rejected because Claude's responses are dramatically more useful when it knows what the operator is looking at.
2. URL-based inference: Rejected — fragile, doesn't capture selected entities or visible data.

**Rationale:**
The hook pattern is lightweight (2 lines per page), lazy-evaluated via useRef to prevent re-registration, and the context is attached at send-time (not continuously streamed).

**Constraints:**
Total page context must stay within 2,000-token budget.

**Supersedes:** N/A
**Cross-References:** DEC-170, DEC-273

---

**DEC-269:** Demand-Refreshed AI Insight Card
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Dashboard AI insight card is demand-refreshed: manual click or auto-refresh every 5 minutes during market hours. Cached response with configurable TTL. Graceful "AI not available" state when service is disabled.

**Alternatives Rejected:**
1. Always-on auto-refresh: Rejected — unnecessary API cost during non-market hours.
2. Push-based (server sends insight): Rejected — adds complexity; demand-pull is simpler and sufficient.

**Rationale:**
During market hours, insights are time-sensitive and worth refreshing. Outside market hours, manual refresh is sufficient.

**Constraints:**
Requires `useAIInsight` TanStack Query hook with conditional `refetchInterval`.

**Supersedes:** N/A
**Cross-References:** DEC-170, DEC-274

---

**DEC-270:** Markdown Rendering Stack
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Use `react-markdown` + `remark-gfm` + `rehype-sanitize` for rendering AI responses. XSS protection mandatory via rehype-sanitize.

**Alternatives Rejected:**
1. Rendering raw HTML: Rejected — XSS vulnerability.
2. Plain text only: Rejected — Claude's responses use markdown heavily (code blocks, tables, lists).
3. marked + DOMPurify: Rejected — react-markdown integrates better with React component model.

**Rationale:**
react-markdown is the standard React markdown library. remark-gfm adds GitHub-flavored markdown (tables, strikethrough). rehype-sanitize prevents XSS from any HTML in Claude's responses.

**Constraints:**
Bundle size impact: ~30-50KB gzipped (well under 200KB threshold).

**Supersedes:** N/A
**Cross-References:** DEC-170

---

**DEC-271:** Claude tool_use for Structured Action Proposals
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Use Claude's native `tool_use` API for structured action proposals. Tools are defined as JSON schemas passed in the API request. When Claude wants to propose an action, it emits a `tool_use` content block. Backend intercepts the block, creates an `ActionProposal`, returns a `tool_result`, and Claude continues its response.

**Alternatives Rejected:**
1. JSON-in-free-text parsing: Rejected per adversarial review finding C2. Fragile regex parsing of JSON embedded in natural language responses. Claude's native tool_use is purpose-built for this and dramatically more reliable.

**Rationale:**
tool_use is the Anthropic-recommended approach for structured outputs. It guarantees valid JSON matching the schema. The adversarial review correctly identified that rejecting tool_use in favor of manual parsing was the highest-risk design decision in the original spec.

**Constraints:**
Tool definitions must be included in every API call (adds to input token count).

**Supersedes:** N/A
**Cross-References:** DEC-272, DEC-273

---

**DEC-272:** Five-Type Closed Action Enumeration
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
MVP supports exactly 5 action types: `propose_allocation_change`, `propose_risk_param_change`, `propose_strategy_suspend`, `propose_strategy_resume`, `generate_report`. First 4 require approval. `generate_report` executes immediately.

**Alternatives Rejected:**
1. Open-ended actions (Claude proposes anything): Rejected — unbounded action space is a safety risk.
2. Fewer actions (just suspend/resume): Rejected — allocation and risk param changes are high-value for the operator.
3. More actions (annotate_trade, manual_rebalance): Rejected for MVP — annotate_trade is low value, manual_rebalance is high risk with unclear UX.

**Rationale:**
These 5 actions cover the operator's primary needs during a trading session. The closed enumeration ensures every possible AI action has been reviewed and has an executor with validation.

**Constraints:**
Unrecognized tool calls from Claude are logged and treated as errors (no ActionProposal created).

**Supersedes:** N/A
**Cross-References:** DEC-271, DEC-170

---

**DEC-273:** System Prompt Template with Token Budgets
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
System prompt template includes: ARGUS description, operator context, active strategy summaries, behavioral guardrails (advisory only, never recommend specific entries/exits, caveat uncertainty, reference actual data, never fabricate). Mandatory tool_use directive section instructs Claude to call tools immediately for configuration changes. Token budgets: system ≤1,500, page context ≤2,000, history ≤8,000, response ≤4,096.

**Alternatives Rejected:**
1. No system prompt (Claude defaults): Rejected — Claude needs domain context to be useful.
2. Minimal prompt (just "you are a trading assistant"): Rejected — behavioral guardrails are critical for safety.
3. Dynamic prompt construction (fetched from DB): Rejected for MVP — over-engineering. Prompts managed in code.

**Rationale:**
The system prompt is the most important safety mechanism in the AI layer. Explicit guardrails prevent Claude from recommending specific trades or fabricating data. The mandatory tool_use directive prevents Claude from narrating intent instead of calling tools.

**Constraints:**
Total context window budget: ~12,000 tokens for system + page + history. Remainder for response.

**Supersedes:** N/A
**Cross-References:** DEC-271, DEC-098

---

**DEC-274:** Per-Call Cost Tracking
**Date:** 2026-03-06
**Sprint:** Sprint 22

**Decision:**
Track token usage for every Claude API call in `ai_usage` table. Fields: conversation_id, timestamp, input_tokens, output_tokens, model, estimated_cost_usd. `GET /api/v1/ai/usage` returns daily and monthly totals. `GET /api/v1/ai/status` includes current-month spend and per-day average.

**Alternatives Rejected:**
1. Aggregate-only tracking (daily totals): Rejected — per-call granularity enables debugging of cost anomalies.
2. No cost tracking (rely on Anthropic dashboard): Rejected — operator needs in-app visibility without switching to another service.

**Rationale:**
Cost is trivial per DEC-098, but tracking from day one enables trend analysis and anomaly detection. The Anthropic dashboard has delayed reporting; in-app tracking is real-time.

**Constraints:**
Streaming responses estimate tokens from content length (4 chars ≈ 1 token). Not perfectly accurate but sufficient for cost estimation.

**Supersedes:** N/A
**Cross-References:** DEC-098, RSK-NEW-2

---

### 8.2 `docs/sprint-history.md` — Sprint 22 Entry

Add to the sprint history table:

```
| 22 | AI Layer MVP | 1972+366V | Mar 6 | DEC-264–274, DEC-275 |
```

Session detail:

```
**Sprint 22: AI Layer MVP + Copilot Activation (Mar 6, 2026)**
9 planned sessions + 5 fix sessions. Tests: 1,754→1,972 pytest, 296→366 Vitest.

Sessions:
- S1: AI Core Module (ClaudeClient, PromptManager, SystemContextBuilder, ResponseCache, AIConfig, tools.py) — 62 new tests
- S2a: Chat Persistence (ConversationManager, UsageTracker, 3 SQLite tables) — 35 new tests
- S2b: Chat API + WebSocket Streaming (6 REST endpoints, WS /ws/v1/ai/chat) — 30 new tests
- S3a: Approval Workflow (ActionProposal, ActionManager, approve/reject routes, Event Bus) — 32 new tests. COMPACTED.
- S3b: Action Executors + AI Content (5 executors, DailySummaryGenerator, AIService, insight endpoint) — 54 new tests. COMPACTED.
- S4a: Copilot Core Chat (CopilotPanel rewrite, ChatMessage, StreamingMessage, ChatInput) — 23 new tests
- S4b: Copilot Integration (useCopilotContext on 7 pages, Cmd/K shortcut, conversation history, reconnection) — 20 new tests
- S5: Action Cards + Approval UX (ActionCard component, 6 states, audio notifications, countdown) — 10 new tests
- S6: Dashboard AI Insight + Debrief (AIInsightCard, ConversationBrowser, Learning Journal) — 18 new tests

Fix sessions: S4a-fix (auto-focus, modifier keys, auto-scroll), S3b-fix (system prompt directiveness), S2b-fix (stream event extraction), model ID fix, frontend tool_use event fix.

Notable: Sessions 3a and 3b both compacted, leading to DEC-275 (compaction risk scoring system). AIService class built but not wired into routes (removed in cleanup).
```

### 8.3 `docs/project-knowledge.md` — Key Updates

Update the following sections:

**Current State:**
```
**Tests:** 1,957 pytest + 366 Vitest  (after fix session removes test_service.py: ~1,972 - 15 = ~1,957)
**Sprints completed:** 1 through 22
**Active sprint:** None (between sprints)
**Next sprint:** 23 (NLP Catalyst + Universe Manager)
```

Add to sprint history table:
```
| 22 | AI Layer MVP | 1972+366V | Mar 6 | DEC-264–275 |
```

Update monthly costs:
```
| Claude API (Sprint 22) | ~$35–50/mo est. | Active |
```

Add to Key Active Decisions:
```
**AI Layer:** DEC-264 (full scope Sprint 22), DEC-265 (WebSocket streaming), DEC-271 (tool_use for proposals), DEC-272 (5-type action enumeration), DEC-273 (system prompt + guardrails), DEC-274 (per-call cost tracking).
```

Update Architecture section — add AI Layer:
```
3. **AI Layer** (Sprint 22) — Claude API (Opus, DEC-098) via ClaudeClient wrapper; PromptManager with system prompt template and behavioral guardrails (DEC-273); SystemContextBuilder for per-page context injection (DEC-268); tool_use for structured action proposals (DEC-271) with 5 defined tools (DEC-272); ActionManager with DB-persisted proposals and 5-min TTL (DEC-267); 5 ActionExecutors with 4-condition pre-execution re-check; ConversationManager with calendar-date keying and tags (DEC-266); UsageTracker for per-call cost tracking (DEC-274); DailySummaryGenerator; ResponseCache. WS /ws/v1/ai/chat for streaming. All AI features degrade gracefully when ANTHROPIC_API_KEY unset.
```

### 8.4 `docs/risk-register.md` — New RSK Entries

```
RSK-NEW-1: Claude API Dependency
- Likelihood: Medium
- Impact: Low (trading engine independent)
- Mitigation: All AI features degrade gracefully. Trading engine operates identically with AI disabled.

RSK-NEW-2: API Cost Overrun
- Likelihood: Low
- Impact: Low (Opus pricing ~$15/1M input, $75/1M output)
- Mitigation: Rate limiting (10 req/min default), response caching, per-call cost tracking with usage endpoint.

RSK-NEW-3: Stale Approval Execution
- Likelihood: Medium
- Impact: Medium (executing outdated allocation/risk change)
- Mitigation: 5-min TTL, 4-condition pre-execution re-check (strategy state, regime, equity within 5%, no circuit breaker).

RSK-NEW-4: tool_use Hallucination
- Likelihood: Low
- Impact: Medium (invalid proposal created)
- Mitigation: Strict JSON schema validation, sane range bounds (allocation 0-100%, risk params within defined ranges), audit logging, human approval required.

RSK-NEW-5: aiosqlite Write Contention
- Likelihood: Low
- Impact: Low-Medium (latency spike on trade logging)
- Mitigation: Monitor during paper trading. AI tables use ai_ prefix, same DB file. If contention materializes, separate DB file for AI tables.
```

### 8.5 `CLAUDE.md` — AI Module Addition

Add to the project structure section:
```
argus/ai/           # AI Layer — Claude API integration
  client.py         # ClaudeClient wrapper (tool_use, rate limiting)
  config.py         # AIConfig Pydantic model
  prompts.py        # PromptManager, system prompt template
  context.py        # SystemContextBuilder (7 page types)
  conversations.py  # ConversationManager (SQLite persistence)
  usage.py          # UsageTracker (per-call cost tracking)
  actions.py        # ActionManager (proposal lifecycle)
  executors.py      # 5 ActionExecutors + ExecutorRegistry
  summary.py        # DailySummaryGenerator
  cache.py          # ResponseCache (TTL-based)
  tools.py          # 5 tool_use definitions
```

Add to commands section:
```
# AI Layer
ANTHROPIC_API_KEY="sk-..." python -m argus.api --dev  # Run with AI enabled
python -m pytest tests/ai/ -x -q                       # AI module tests only
```

---

## 9. Review Verdict

**PROCEED** — after the consolidated fix session is completed and doc sync is done.

The sprint achieved its architectural goals. The AI layer is properly isolated from the trading engine. The approval workflow provides safety through DB persistence, TTL expiry, and 4-condition re-check. All scope boundaries held. No escalation criteria were triggered.

The 8 items in the fix prompt are a mix of config bugs (YAML field names), dead code removal (AIService), and UX polish. None are architectural concerns. After the fix session:

1. Run fix session (consolidated prompt above)
2. Run Tier 2 review of fix session
3. Complete doc sync (DEC entries, sprint history, project knowledge, risk register, CLAUDE.md)
4. Merge `sprint-22-ai-layer` → `main`
5. Test during next paper trading session with live Claude API

**Next sprint:** Sprint 23 (NLP Catalyst + Universe Manager, DEC-263). The AI infrastructure built in Sprint 22 is the foundation — Sprint 23 extends it with new tools and monitoring capabilities.
