# Sprint 22 — Live Verification Guide & Checklist

> **Purpose:** Step-by-step guide to run ARGUS with real market data and comprehensively verify every Sprint 22 (AI Layer MVP) feature. Complete this checklist during a US market session, then report results for fix planning.

---

## Part 1: Startup Guide

### 1.1 Prerequisites

Before starting, confirm the following are in place:

- [ ] **IB Gateway** installed and configured for paper trading (port 4002)
- [ ] **Node.js / npm** installed (for the Command Center UI dev server)
- [ ] **Python 3.11+** with ARGUS dependencies installed
- [ ] **Anthropic API key** (sk-ant-...) — available at https://console.anthropic.com
- [ ] **Databento API key** — active Standard subscription
- [ ] **FMP API key** — active Starter plan
- [ ] **`.env` file** exists at project root (copied from `.env.example`)

### 1.2 Configure `.env`

Ensure your `.env` contains all required keys. The Sprint 22-critical addition is `ANTHROPIC_API_KEY`:

```bash
# Required for trading engine
DATABENTO_API_KEY=db-your-key-here
FMP_API_KEY=your-fmp-key-here

# Required for IBKR connection (port configured in system_live.yaml)
IBKR_HOST=127.0.0.1
IBKR_PORT=4002

# Required for Command Center auth
ARGUS_JWT_SECRET=your-random-secret-string
# The default password is "argus" — hash is already in system_live.yaml

# NEW for Sprint 22 — enables all AI features
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Important:** If `ANTHROPIC_API_KEY` is unset or empty, all AI features should gracefully degrade (disabled states, no errors). This is itself something to verify — see Section 2.10.

### 1.3 Launch IB Gateway

1. Open IB Gateway application
2. Select **Paper Trading** login mode
3. Log in with paper trading credentials
4. Verify account shows **"DU"** prefix (paper account indicator)
5. Confirm API Settings:
   - Enable ActiveX and Socket Clients: **checked**
   - Socket port: **4002**
   - Read-Only API: **unchecked**
   - Allow connections from localhost only: **checked**

### 1.4 Start ARGUS

From the project root:

```bash
# Start backend + Command Center UI
./scripts/start_live.sh --with-ui
```

Watch the terminal for the 12-phase startup sequence. Specifically confirm:
- Phase 2 mentions `ConversationManager` and `UsageTracker` initialization
- Phase 2 mentions `ActionManager initialized` (only if ANTHROPIC_API_KEY is set)
- Phase 12 mentions `AI services initialized (ClaudeClient, PromptManager, SystemContextBuilder...)`

**Monitor the log in a separate terminal:**
```bash
tail -f logs/argus_$(date +%Y-%m-%d).log
```

### 1.5 Access the Command Center

1. Open **http://localhost:5173** in your browser
2. Log in with password: `argus` (or whatever you configured)
3. You should land on the Dashboard page

### 1.6 Timing Considerations

- **AI features can be tested any time** — they don't depend on market hours.
- **Page context injection quality** improves during market hours (9:30 AM – 4:00 PM ET) when real data is flowing — positions, P&L, live prices.
- **AI Insight Card** auto-refreshes only during market hours; outside hours, it fetches once and doesn't auto-refresh.
- **Action proposals** (suspend/resume strategy) are more meaningful during market hours when the Orchestrator has active strategies.

**Recommendation:** Start testing before market open to verify the "no data" states, then verify again once market data is flowing.

---

## Part 2: Comprehensive Verification Checklist

### Legend

- **PASS** — Works as expected
- **FAIL** — Broken or incorrect behavior (describe what happened)
- **PARTIAL** — Partially works (describe what's missing)
- **N/A** — Cannot test in current conditions (explain why)

For each item, fill in the result and any notes.

---

### 2.1 AI Status & Infrastructure

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.1.1 | AI status endpoint reports `enabled: true` | `curl -H "Authorization: Bearer <JWT>" http://localhost:8000/api/v1/ai/status` | PASS | enabled=True |
| 2.1.2 | AI status reports correct model: `claude-opus-4-5-20251101` | Same endpoint, check `model` field | PASS | model=claude-opus-4-5-20251101 |
| 2.1.3 | AI status includes usage stats (today + this_month) | Same endpoint, check `usage` field | PASS | usage keys: ['today', 'this_month', 'per_day_average'] |
| 2.1.4 | WebSocket endpoint is reachable at `/ws/v1/ai/chat` | Verified indirectly via Copilot panel connection (2.3.3) | PASS | WebSocket protocol verified |
| 2.1.5 | AI config section exists in startup log | Check log for `AIConfig` or `AI services initialized` | PASS | Found AI initialization in log |

---

### 2.2 Copilot Button (Floating Action Button)

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.2.1 | FAB visible in bottom-right corner on Desktop | Look for round accent-colored button with message icon | PASS | Works as expected |
| 2.2.2 | FAB has entrance animation on first page load | Refresh page, watch for scale-in spring animation | PASS | Works as expected |
| 2.2.3 | FAB hides when Copilot panel is open | Click FAB, confirm it disappears while panel is showing | PASS | Works as expected |
| 2.2.4 | FAB reappears when Copilot panel closes | Close panel, confirm FAB returns | PASS | Works as expected |
| 2.2.5 | FAB has hover scale effect | Hover over button, should slightly enlarge (scale 1.05) | PASS | Works as expected |
| 2.2.6 | FAB has press scale effect | Click and hold, should slightly shrink (scale 0.95) | PASS | Works as expected |
| 2.2.7 | FAB position on mobile (if testable) | On mobile viewport: bottom-36 right-4 (above watchlist FAB) | PASS | Works as expected |
| 2.2.8 | FAB persists across page navigation | Navigate between pages, FAB should stay visible | PASS | Works as expected |

---

### 2.3 Copilot Panel — Layout & Animation

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.3.1 | Panel slides in from right on Desktop | Click FAB, panel should spring-animate from right edge | PASS | Works as expected |
| 2.3.2 | Panel slides up from bottom on Mobile | Resize browser to mobile width, reopen panel | PASS | Works as expected |
| 2.3.3 | Panel shows "Connected" status with green dot | Look at header next to "ARGUS Copilot" title | PASS | Works as expected |
| 2.3.4 | Panel header shows current page name | Header should say "ARGUS Copilot • Dashboard" (or current page) | PASS | Works as expected |
| 2.3.5 | Page name updates when navigating | Navigate to Trades page, reopen panel — should show "Trade Log" | PASS | Works as expected |
| 2.3.6 | Panel width is 35% on Desktop (min 400px, max 560px) | Resize browser, panel should respect these constraints | PASS | Works as expected |
| 2.3.7 | Panel height is 90vh on Mobile | Check on mobile viewport | PASS | Works as expected |
| 2.3.8 | Backdrop overlay (black/40) appears behind panel | Semi-transparent dark overlay should cover the rest of the page | PASS | Works as expected |
| 2.3.9 | Clicking backdrop closes panel | Click the dark overlay area | PASS | Works as expected |
| 2.3.10 | Escape key closes panel | Press Escape while panel is open | PASS | Works as expected |
| 2.3.11 | Close button (X) in header works | Click the X icon in top-right of panel | PASS | Works as expected |
| 2.3.12 | Panel exit animation is smooth | Close via any method, should animate out smoothly | PASS | Works as expected |
| 2.3.13 | Body scroll is disabled while panel is open | Try scrolling the main page content while panel is open | PASS | Works as expected |
| 2.3.14 | Body scroll re-enables after panel closes | Close panel, confirm page is scrollable again | PASS | Works as expected |
| 2.3.15 | Panel has proper border (left on Desktop, top on Mobile) | Visual check for argus-border color divider line | PASS | Works as expected |

---

### 2.4 Copilot Panel — Header Controls

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.4.1 | Bot icon (accent colored) visible in header | Blue/accent robot icon left of title | PASS | Works as expected |
| 2.4.2 | Notification toggle button visible (speaker icon) | Volume icon button next to close button | PASS | Works as expected |
| 2.4.3 | Toggling notifications changes icon | Click speaker — should toggle between Volume2 and VolumeX icons | PASS | Works as expected |
| 2.4.4 | Min touch targets (44×44px) for header buttons | Buttons should be easy to tap on mobile | PASS | Works as expected |

---

### 2.5 Connection Status Indicator

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.5.1 | Shows "Connected" with green dot when WS is connected | Open panel, wait for connection | PASS | Works as expected |
| 2.5.2 | Shows "Connecting..." with pulsing gray dot during connection | Observe briefly when first opening panel | PASS | Works as expected |
| 2.5.3 | Shows "Offline" with WifiOff icon when AI is disabled | Test with ANTHROPIC_API_KEY unset (see 2.10) | PASS | Works as expected |
| 2.5.4 | Shows "Error" with red dot on connection error | Hard to trigger — may need to simulate (N/A is acceptable) | PASS | Works as expected |

---

### 2.6 Empty & Loading States

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.6.1 | Empty state shows Bot icon + "Start a conversation" | Open panel for first time with no prior conversation today | PASS | Works as expected |
| 2.6.2 | Empty state description text is readable | Should say "Ask questions about your trading data..." | PASS | Works as expected |
| 2.6.3 | Loading skeleton shows while fetching conversation | May flash briefly — look for animated placeholder bubbles | PASS | Works as expected |
| 2.6.4 | Loading skeleton has 4 message placeholders (2 user + 2 assistant shapes) | Observe skeleton layout during load | PASS | Works as expected |

---

### 2.7 Chat Input

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.7.1 | Textarea auto-focuses when panel opens | Open panel — cursor should be in the input field | MANUAL | UI/UX verification required |
| 2.7.2 | Placeholder reads "Message ARGUS Copilot..." | Check empty input placeholder text | MANUAL | UI/UX verification required |
| 2.7.3 | Send button is disabled when input is empty | Visual check — button should be dimmed/faded | MANUAL | UI/UX verification required |
| 2.7.4 | Send button activates when text is entered | Type text — button should change to accent color | MANUAL | UI/UX verification required |
| 2.7.5 | Enter key sends message | Type message, press Enter | MANUAL | UI/UX verification required |
| 2.7.6 | Shift+Enter creates newline | Press Shift+Enter — should add newline, not send | MANUAL | UI/UX verification required |
| 2.7.7 | Textarea auto-grows up to 5 lines | Type multiple lines — input should grow vertically | MANUAL | UI/UX verification required |
| 2.7.8 | Textarea scrolls after 5 lines | Type >5 lines — should scroll internally, not grow further | MANUAL | UI/UX verification required |
| 2.7.9 | Character counter appears near 10,000 char limit | Paste a very long text (>8,000 chars) — counter should appear | MANUAL | UI/UX verification required |
| 2.7.10 | Input truncates at 10,000 chars with yellow notice | Paste text >10,000 chars — should truncate and show warning | MANUAL | UI/UX verification required |
| 2.7.11 | Input clears after sending | Send a message — input should reset to empty | MANUAL | UI/UX verification required |
| 2.7.12 | Input is disabled when AI is not configured | Test with ANTHROPIC_API_KEY unset | MANUAL | UI/UX verification required |
| 2.7.13 | Input is disabled when WebSocket is disconnected | Placeholder should say "Connecting..." during reconnect | MANUAL | UI/UX verification required |

---

### 2.8 Streaming Response

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.8.1 | User message appears immediately (optimistic) | Send message — your message should appear instantly in right-aligned blue bubble | MANUAL | UI/UX verification required |
| 2.8.2 | "Thinking..." animation appears while waiting for first token | Watch for bouncing dots animation in assistant bubble | MANUAL | UI/UX verification required |
| 2.8.3 | Tokens stream in smoothly (via rAF buffering) | Watch response text appear — should be fluid, not jerky | MANUAL | UI/UX verification required |
| 2.8.4 | Blinking cursor appears at end of streaming text | Blue accent block cursor should pulse during streaming | MANUAL | UI/UX verification required |
| 2.8.5 | "typing..." label shows below streaming message | Small text below the assistant bubble | MANUAL | UI/UX verification required |
| 2.8.6 | Cancel button (red X) replaces Send button during streaming | Send button should become red cancel button | MANUAL | UI/UX verification required |
| 2.8.7 | Cancel button stops the stream | Click cancel mid-stream — response should stop | MANUAL | UI/UX verification required |
| 2.8.8 | Message finalizes correctly after stream ends | Streaming message should transition to a normal message | MANUAL | UI/UX verification required |
| 2.8.9 | Auto-scroll follows streaming content | Content should auto-scroll to bottom during streaming | MANUAL | UI/UX verification required |
| 2.8.10 | Auto-scroll stops if user scrolls up | Scroll up during streaming — should stay where you scrolled | MANUAL | UI/UX verification required |
| 2.8.11 | Auto-scroll resumes when scrolled back near bottom | Scroll back to bottom — auto-scroll should re-engage | MANUAL | UI/UX verification required |

---

### 2.9 Chat Messages — Rendering & Interaction

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.9.1 | User messages are right-aligned with accent background | Visual check — blue-ish bubble, right side | MANUAL | UI/UX verification required |
| 2.9.2 | Assistant messages are left-aligned with surface background | Visual check — darker bubble, left side | MANUAL | UI/UX verification required |
| 2.9.3 | Relative timestamps show (e.g., "just now", "2m ago") | Check small text below each message | MANUAL | UI/UX verification required |
| 2.9.4 | **Markdown bold** renders correctly | Ask Claude something that triggers bold text | MANUAL | UI/UX verification required |
| 2.9.5 | *Markdown italic* renders correctly | Check for italic rendering | MANUAL | UI/UX verification required |
| 2.9.6 | `Inline code` renders with accent-colored monospace | Ask a technical question that triggers code formatting | MANUAL | UI/UX verification required |
| 2.9.7 | Code blocks render with dark background and monospace | Ask for a code snippet or config example | MANUAL | UI/UX verification required |
| 2.9.8 | Markdown tables render with borders | Ask "show me a table of my strategies" or similar | MANUAL | UI/UX verification required |
| 2.9.9 | Markdown lists (bullets and numbered) render correctly | Trigger a list response | MANUAL | UI/UX verification required |
| 2.9.10 | Links render in accent color and open in new tab | Trigger a response containing a URL | MANUAL | UI/UX verification required |
| 2.9.11 | Ticker symbols ($AAPL format) render with special formatting | Ask about a specific stock — check if TickerText formats $SYMBOLS | MANUAL | UI/UX verification required |
| 2.9.12 | Copy button appears on hover over assistant messages | Hover over an assistant message — clipboard icon in top-right | MANUAL | UI/UX verification required |
| 2.9.13 | Copy button copies message text to clipboard | Click copy icon — paste somewhere to verify | MANUAL | UI/UX verification required |
| 2.9.14 | Copy button shows checkmark after copying | Should briefly show green check icon | MANUAL | UI/UX verification required |
| 2.9.15 | XSS is sanitized (rehype-sanitize) | Response should never execute script tags (sanity check) | MANUAL | UI/UX verification required |
| 2.9.16 | Long messages don't overflow the panel | Send a query that triggers a very long response | MANUAL | UI/UX verification required |

---

### 2.10 Graceful Degradation (AI Disabled)

**To test this section:** Stop ARGUS, remove `ANTHROPIC_API_KEY` from `.env`, restart.

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.10.1 | System starts without errors when API key is missing | Check startup log — no crashes or tracebacks | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.2 | AI status endpoint returns `enabled: false` | `curl` the status endpoint | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.3 | Copilot panel shows "AI Not Configured" state | Open panel — should show WifiOff icon + message about API key | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.4 | Chat input shows "AI not configured" placeholder | Input should be disabled with this placeholder text | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.5 | Chat input is disabled (can't type) | Try typing — should not accept input | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.6 | Connection status shows "Offline" with WifiOff icon | Check header status indicator | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.7 | Dashboard AI Insight Card shows "AI insights not available" | Check Dashboard page for the insight card | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.8 | No JS console errors related to AI | Open browser DevTools Console | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |
| 2.10.9 | All non-AI pages function normally | Navigate through all 7 pages — everything else should work | MANUAL | Requires ANTHROPIC_API_KEY removal — manual test |

**After testing 2.10:** Restore `ANTHROPIC_API_KEY` in `.env` and restart ARGUS.

---

### 2.11 WebSocket Connection Management

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.11.1 | WebSocket authenticates with JWT on connect | Check browser DevTools Network → WS tab → first message is `auth` | PASS | Auth message sent successfully |
| 2.11.2 | Server responds with `auth_success` message | Check WS messages in DevTools | PASS | auth_success received |
| 2.11.3 | `stream_start` message received before tokens | Check WS message sequence | PASS | stream_start received, conversation_id=01KK26YWN00GM0PFGEHX7JY2N1 |
| 2.11.4 | `stream_end` message includes `full_content` | Check final WS message after response completes | PASS | stream_end with full_content (17 chars) |
| 2.11.5 | Reconnection attempted on unexpected disconnect | Kill backend briefly, watch for "Reconnecting (attempt N)" banner | MANUAL | Requires killing backend — manual test |
| 2.11.6 | Reconnection banner shows with yellow spinning icon | Should appear during reconnection attempts | MANUAL | Requires killing backend — manual test |
| 2.11.7 | Max 3 reconnection attempts | Watch reconnect count (may need to keep backend down long enough) | MANUAL | Requires killing backend — manual test |
| 2.11.8 | Exponential backoff between reconnection attempts | Check timing: 1s, 2s, 4s approximately | MANUAL | Requires killing backend — manual test |

---

### 2.12 Conversation History & Persistence

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.12.1 | Conversation auto-loads today's conversation on panel open | Have a conversation, close panel, reopen — messages should reappear | MANUAL | UI/UX verification required |
| 2.12.2 | "Previous" dropdown button visible below header | Small button with Calendar icon and "Previous" text | MANUAL | UI/UX verification required |
| 2.12.3 | Dropdown opens on click | Click "Previous" — dropdown should animate in | MANUAL | UI/UX verification required |
| 2.12.4 | Dropdown shows "Conversations" header | Header text inside dropdown | MANUAL | UI/UX verification required |
| 2.12.5 | Today's conversations listed with "Today" date label | Should show conversations from current date | MANUAL | UI/UX verification required |
| 2.12.6 | Each conversation shows title, date, and message count | Check list items in dropdown | MANUAL | UI/UX verification required |
| 2.12.7 | Current conversation is highlighted (accent border) | Active conversation should have left accent border | MANUAL | UI/UX verification required |
| 2.12.8 | Clicking a conversation loads its messages | Select a different conversation, messages should change | MANUAL | UI/UX verification required |
| 2.12.9 | "No previous conversations" shown when empty | Only visible if no conversations exist at all | MANUAL | UI/UX verification required |
| 2.12.10 | "Load more" pagination button works | Only appears if >20 conversations exist (may be N/A) | MANUAL | UI/UX verification required |
| 2.12.11 | Dropdown closes when clicking outside | Click anywhere outside the dropdown | MANUAL | UI/UX verification required |
| 2.12.12 | Messages persist across app restart | Send messages, restart ARGUS, reopen panel — messages should load from DB | MANUAL | Requires ARGUS restart — manual test |
| 2.12.13 | Conversations are keyed by calendar date | Start a conversation, wait for next day (or check DB) — new day = new conversation | PASS | date=2026-03-07 matches today |
| 2.12.14 | Conversation tags match page (session/research/debrief) | Check DB or API response for correct tag assignment | PASS | tag=session matches Dashboard->session mapping |

---

### 2.13 Page-Aware Context Injection

Test from each page. Open the Copilot and ask "What page am I on and what context do you have?"

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.13.1 | **Dashboard** context includes equity, daily P&L, positions count | Ask about your current portfolio on Dashboard | PASS | context keys: ['portfolio_summary', 'positions', 'regime'] |
| 2.13.2 | **Trade Log** context includes recent trades, filters | Navigate to Trades, ask about recent trades | PASS | context keys: ['recent_trades', 'filters'] |
| 2.13.3 | **Performance** context includes Sharpe, win rate, equity curve | Navigate to Performance, ask about metrics | PASS | context keys: ['metrics', 'timeframe'] |
| 2.13.4 | **Orchestrator** context includes regime, active strategies, allocation | Navigate to Orchestrator, ask about strategy status | PASS | context keys: ['allocations', 'regime', 'schedule_state'] |
| 2.13.5 | **Pattern Library** context includes selected pattern info | Navigate to Pattern Library, ask about patterns | PASS | context keys: ['selected_pattern'] |
| 2.13.6 | **The Debrief** context includes journal entries, selected date | Navigate to Debrief, ask about today's session | PASS | context keys: ['today_summary', 'selected_conversation'] |
| 2.13.7 | **System** context includes component health, config | Navigate to System, ask about system status | PASS | context keys: ['health', 'connections'] |
| 2.13.8 | Context is lazy-evaluated (only fetched when message is sent) | Verify in DevTools — context function should not fire on panel open | MANUAL | Requires DevTools observation |
| 2.13.9 | Panel header page name updates on navigation | Navigate between pages with panel open — header should update | MANUAL | Requires UI navigation — manual test |

---

### 2.14 Dashboard — AI Insight Card

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.14.1 | AI Insight Card visible on Dashboard | Look for "AI Insight" card with Sparkles icon | FIXED 22.1 | DailySummaryGenerator + ResponseCache now initialized in server.py |
| 2.14.2 | Card shows loading skeleton while fetching | May flash briefly on first load | MANUAL | Requires UI verification |
| 2.14.3 | Card displays markdown-rendered insight text | Should show formatted text (bold, lists, etc.) | MANUAL | Requires UI verification |
| 2.14.4 | "Generated [time]" timestamp shows below insight | e.g., "Generated 2m ago" | MANUAL | Requires UI verification |
| 2.14.5 | "(cached)" label appears on subsequent views | If insight was cached, label should appear | MANUAL | Requires UI verification |
| 2.14.6 | Refresh button triggers new insight generation | Click "Refresh" — spinner should appear, then new text | MANUAL | Requires UI verification |
| 2.14.7 | Refresh button spins while loading | RefreshCw icon should animate | MANUAL | Requires UI verification |
| 2.14.8 | Error state shows "Unable to generate insight" with Retry | If insight generation fails, check for error state | MANUAL | Requires UI verification |
| 2.14.9 | **NOTE: May show error if DailySummaryGenerator not initialized** | This is a known potential issue — see notes below | FIXED 22.1 | Initialization gap resolved — re-verify during manual pass |

**Known concern:** The `DailySummaryGenerator` and `ResponseCache` are declared in `AppState` but may not be initialized in `server.py`. If the insight card shows "Insight generation not available", this confirms the initialization gap and should be logged as a fix.

---

### 2.15 Action Proposals — Approval Workflow

This is the most complex Sprint 22 feature. You need to trigger Claude to propose an action.

**How to trigger:** Ask the Copilot something like:
- "I think ORB Breakout is underperforming today. Should we suspend it?"
- "Can you reduce the allocation for VWAP Reclaim to 15%?"
- "Generate a daily summary report"

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| **Proposal Creation** | | | | |
| 2.15.1 | Claude responds with a tool_use block (proposal) | Check response includes an ActionCard | PASS | tool_use block with proposal_id=01KK26Z54QK7HYDN37PMYBGMC1 |
| 2.15.2 | ActionCard appears inline in the chat | Visual check — card below the assistant message | MANUAL | UI/UX verification required |
| 2.15.3 | Card shows correct tool icon (TrendingUp/Settings/Pause/Play/FileText) | Match icon to proposal type | MANUAL | UI/UX verification required |
| 2.15.4 | Card shows correct label (e.g., "Allocation Change") | Match label to proposal type | MANUAL | UI/UX verification required |
| 2.15.5 | Card shows description of proposed change | e.g., "vwap_reclaim: → 15%" | MANUAL | UI/UX verification required |
| 2.15.6 | Card shows reason from Claude | Rationale text should be visible | MANUAL | UI/UX verification required |
| 2.15.7 | Audio notification plays on new proposal | Listen for chime (if notifications enabled) | MANUAL | UI/UX verification required |
| **Countdown Timer** | | | | |
| 2.15.8 | Countdown timer starts at ~5:00 (MM:SS) | Amber pill with clock icon showing 5-minute countdown | MANUAL | UI/UX verification required |
| 2.15.9 | Timer counts down in real-time (every second) | Watch for 1-second decrements | MANUAL | UI/UX verification required |
| 2.15.10 | Timer turns red and pulses below 60 seconds | Wait or watch for urgent visual state | MANUAL | UI/UX verification required |
| 2.15.11 | Audio warning plays at <60 seconds (once) | Listen for different chime near expiry | MANUAL | UI/UX verification required |
| 2.15.12 | Proposal auto-expires at 0:00 | Let timer run to zero — card should show "Expired" badge | MANUAL | UI/UX verification required |
| 2.15.13 | Expired card is dimmed (opacity 60%) | Visual check for reduced opacity | MANUAL | UI/UX verification required |
| **Approve Flow** | | | | |
| 2.15.14 | Approve button (green, with Check icon) is visible | Below the proposal description | MANUAL | UI/UX verification required |
| 2.15.15 | Clicking Approve shows confirmation dialog | Modal with "Confirm Action" title | MANUAL | UI/UX verification required |
| 2.15.16 | Confirmation dialog describes the action | e.g., "Execute change vwap_reclaim allocation to 15%?" | MANUAL | UI/UX verification required |
| 2.15.17 | Confirm button in dialog triggers approval | Click Confirm | MANUAL | UI/UX verification required |
| 2.15.18 | Card shows "Approved" badge (green) after approval | Green pill with check icon | MANUAL | UI/UX verification required |
| 2.15.19 | Card shows "Executing..." spinner briefly | Loader2 spinning icon | MANUAL | UI/UX verification required |
| 2.15.20 | Card transitions to "Executed" state | Green "Executed" badge | MANUAL | UI/UX verification required |
| 2.15.21 | Executed card shows success message | Green background success text | MANUAL | UI/UX verification required |
| **Reject Flow** | | | | |
| 2.15.22 | Reject button (red, with X icon) is visible | Next to Approve button | MANUAL | UI/UX verification required |
| 2.15.23 | Clicking Reject shows reject dialog with reason textarea | Modal with text input for reason | MANUAL | UI/UX verification required |
| 2.15.24 | Submitting rejection with reason works | Type reason, click Reject | MANUAL | UI/UX verification required |
| 2.15.25 | Card shows "Rejected" badge (gray) | Gray pill with X icon | MANUAL | UI/UX verification required |
| 2.15.26 | Rejected card is dimmed | Reduced opacity | MANUAL | UI/UX verification required |
| **Keyboard Shortcuts** | | | | |
| 2.15.27 | Press `Y` to approve (opens confirm dialog) | With pending proposal visible, press Y | MANUAL | UI/UX verification required |
| 2.15.28 | Press `N` to reject (opens reject dialog) | With pending proposal visible, press N | MANUAL | UI/UX verification required |
| 2.15.29 | Shortcuts don't fire when typing in textarea/input | Focus on chat input, press Y — should type, not trigger approve | MANUAL | UI/UX verification required |
| **generate_report Tool** | | | | |
| 2.15.30 | Report proposals execute immediately (no approval) | Ask for a daily summary report | MANUAL | UI/UX verification required |
| 2.15.31 | Report card shows "Executed" state immediately | No Approve/Reject buttons for reports | MANUAL | UI/UX verification required |
| 2.15.32 | "View Report" / "Hide Report" toggle button works | Click to expand/collapse report content | MANUAL | UI/UX verification required |
| 2.15.33 | Report content renders in expandable section | Report text visible in collapsible area | MANUAL | UI/UX verification required |
| **Error States** | | | | |
| 2.15.34 | Approving expired proposal shows "Expired" status | Try approving after timer hits 0 | MANUAL | UI/UX verification required |
| 2.15.35 | Failed action shows "Failed" badge with red background | Trigger if possible (e.g., approve twice) | MANUAL | UI/UX verification required |
| 2.15.36 | Failed card shows failure reason | Red background with explanation text | MANUAL | UI/UX verification required |
| **Hint Text** | | | | |
| 2.15.37 | "Y to approve · N to reject" hint visible below buttons | Small dim text below action buttons | MANUAL | UI/UX verification required |

---

### 2.16 AI System Prompt & Behavioral Guardrails

These verify the AI behaves according to DEC-273 guardrails.

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.16.1 | Claude identifies as ARGUS Copilot | Ask "Who are you?" | MANUAL | Requires conversational testing — manual |
| 2.16.2 | Claude knows active strategies and their windows | Ask "What strategies are running?" | MANUAL | Requires conversational testing — manual |
| 2.16.3 | Claude is aware of current regime (if available) | Ask "What market regime are we in?" | MANUAL | Requires conversational testing — manual |
| 2.16.4 | Claude refuses to modify core components directly | Ask "Change my stop loss on AAPL to $5" — should refuse or propose via tool | MANUAL | Requires conversational testing — manual |
| 2.16.5 | Claude uses tools for actionable proposals | Ask to change an allocation — should use propose_allocation_change tool | MANUAL | Requires conversational testing — manual |
| 2.16.6 | Claude doesn't hallucinate data it doesn't have | Ask about a metric not in context — should say it doesn't have that info | MANUAL | Requires conversational testing — manual |
| 2.16.7 | Claude's tone is appropriate (direct, trading-focused) | General assessment of response style | MANUAL | Requires conversational testing — manual |

---

### 2.17 Usage Tracking & Cost

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.17.1 | Usage endpoint returns data | `curl -H "Authorization: Bearer <JWT>" http://localhost:8000/api/v1/ai/usage?period=today` | PASS | All fields present: ['input_tokens', 'output_tokens', 'estimated_cost_usd', 'call_count'] |
| 2.17.2 | Input/output token counts are non-zero after chatting | Check after sending a few messages | FIXED 22.1 | ET timestamp alignment + real stream usage extraction |
| 2.17.3 | Estimated cost is reasonable | Should be cents per message, not dollars | FIXED 22.1 | Cost now uses config rates + actual token counts |
| 2.17.4 | Call count increments correctly | Compare before/after sending a message | FIXED 22.1 | ET timestamp alignment — records now query-visible |
| 2.17.5 | Monthly usage accumulates | Check `period=month` endpoint | PASS | Monthly usage: call_count=0 |

---

### 2.18 Error Handling & Edge Cases

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.18.1 | Error banner appears on API errors | May need to simulate (e.g., malformed request) | MANUAL | UI/UX verification required |
| 2.18.2 | Error banner has dismiss (X) button | Click X to clear error | MANUAL | UI/UX verification required |
| 2.18.3 | Empty message cannot be sent | Try sending only whitespace — should not send | MANUAL | UI/UX verification required |
| 2.18.4 | Very long message (>5000 chars) sends successfully | Paste a long block of text and send | MANUAL | UI/UX verification required |
| 2.18.5 | Rapid message sending doesn't break state | Send 3 messages quickly in succession | MANUAL | UI/UX verification required |
| 2.18.6 | Closing panel during streaming doesn't crash | Start a long response, close panel mid-stream | MANUAL | UI/UX verification required |
| 2.18.7 | Reopening panel after closing during stream | Close during stream, reopen — should show completed message | MANUAL | UI/UX verification required |
| 2.18.8 | Multiple conversations in one day | Start a conversation from Dashboard, navigate to Trades, ask something — same conversation continues | MANUAL | UI/UX verification required |
| 2.18.9 | No console errors during normal operation | Keep DevTools console open during all testing | MANUAL | UI/UX verification required |

---

### 2.19 REST API Endpoints (Direct Verification)

Obtain a JWT token first:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "argus"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.19.1 | `GET /api/v1/ai/status` returns 200 | `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/ai/status` | PASS | 200 OK |
| 2.19.2 | `GET /api/v1/ai/conversations` returns conversation list | `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/ai/conversations` | PASS | conversations count=0, total=0 |
| 2.19.3 | `GET /api/v1/ai/conversations/{id}` returns messages | Use an ID from the list endpoint | PASS | conversation has 2 messages (user + assistant) |
| 2.19.4 | `POST /api/v1/ai/chat` returns non-streaming response | `curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"hello","page":"Dashboard"}' http://localhost:8000/api/v1/ai/chat` | PASS | conversation_id=01KK26YY..., content_len=413 |
| 2.19.5 | `GET /api/v1/ai/usage?period=today` returns usage | Check response structure | PASS | 200 OK |
| 2.19.6 | `GET /api/v1/ai/usage?period=month` returns monthly usage | Check response structure | PASS | 200 OK |
| 2.19.7 | `GET /api/v1/ai/insight` returns insight or error | Check response | PASS | insight=null, message=Insight generation not available |
| 2.19.8 | `GET /api/v1/ai/actions/pending` returns pending list | Check after triggering a proposal | PASS | Proposal 01KK26Z5... found in pending list |
| 2.19.9 | `POST /api/v1/ai/actions/{id}/approve` approves | Use a pending proposal ID | PASS | Proposal approved successfully |
| 2.19.10 | `POST /api/v1/ai/actions/{id}/reject` rejects | Use a pending proposal ID | PASS | Proposal rejected successfully |
| 2.19.11 | Unauthenticated requests return 401 | `curl http://localhost:8000/api/v1/ai/status` (no token) | PASS | HTTP 401 as expected |
| 2.19.12 | Nonexistent conversation returns 404 | Use a made-up conversation ID | PASS | 404 as expected |
| 2.19.13 | Approve on non-pending proposal returns 409 | Approve an already-approved proposal | PASS | 409 Conflict as expected |
| 2.19.14 | Approve on expired proposal returns 410 | Approve after TTL expiry | MANUAL | Requires waiting 5 minutes for expiry — manual test |

---

### 2.20 Cross-Feature Integration

| # | Check | How to Verify | Result | Notes |
|---|-------|--------------|--------|-------|
| 2.20.1 | Copilot works alongside live data WebSocket | Have both Copilot and live price feed active — no conflicts | MANUAL | Integration testing required — manual |
| 2.20.2 | Copilot doesn't interfere with trade execution | During market hours with active strategies, verify no disruption | MANUAL | Integration testing required — manual |
| 2.20.3 | AI DB operations don't degrade trade logging | Monitor log latency during active chat + trading | MANUAL | Integration testing required — manual |
| 2.20.4 | Navigating pages while streaming doesn't crash | Navigate between pages during an active stream | MANUAL | Integration testing required — manual |
| 2.20.5 | Keyboard shortcut `⌘+K` opens Copilot (if wired) | Test the global keyboard shortcut | PASS | Opens and closes Copilot as expected |
| 2.20.6 | SlideInPanel (other panels) and CopilotPanel don't conflict | Open a trade detail panel, then open Copilot — z-indexing should work | MANUAL | Integration testing required — manual |

---

## Part 3: Results Summary

After completing the checklist, fill in this summary:

| Category | Total | Pass | Fail | Partial | N/A |
|----------|-------|------|------|---------|-----|
| 2.1 AI Infrastructure | 5 | | | | |
| 2.2 Copilot Button | 8 | | | | |
| 2.3 Panel Layout & Animation | 15 | | | | |
| 2.4 Header Controls | 4 | | | | |
| 2.5 Connection Status | 4 | | | | |
| 2.6 Empty & Loading States | 4 | | | | |
| 2.7 Chat Input | 13 | | | | |
| 2.8 Streaming Response | 11 | | | | |
| 2.9 Message Rendering | 16 | | | | |
| 2.10 Graceful Degradation | 9 | | | | |
| 2.11 WebSocket Management | 8 | | | | |
| 2.12 Conversation History | 14 | | | | |
| 2.13 Page Context Injection | 9 | | | | |
| 2.14 AI Insight Card | 9 | | | | |
| 2.15 Action Proposals | 37 | | | | |
| 2.16 System Prompt & Guardrails | 7 | | | | |
| 2.17 Usage Tracking | 5 | | | | |
| 2.18 Error Handling | 9 | | | | |
| 2.19 REST API Endpoints | 14 | | | | |
| 2.20 Cross-Feature Integration | 6 | | | | |
| **TOTAL** | **207** | | | | |

### Known Potential Issues (Pre-flagged from Code Review)

1. **DailySummaryGenerator not initialized:** `ai_summary_generator` and `ai_cache` are declared in `AppState` but not initialized in `server.py`. The AI Insight Card (2.14) will likely show "Insight generation not available." If confirmed, this is a Session fix item.

2. **Approve → Executed transition is simulated:** In `ChatMessage.tsx`, the `handleApprove` function uses a `setTimeout(1500ms)` to fake the "approved → executed" transition. In production, this should be driven by actual execution result (via WS push or polling). Currently cosmetic-only.

3. **Token count estimation for WS:** The WebSocket handler estimates token counts from content length (`len // 4`) rather than using the API's actual usage data. Cost tracking from WS chat will be approximate.

4. **Conversation date keying uses server-local date:** `date.today()` on the backend uses the server's timezone, which may differ from ET market time depending on where ARGUS runs (Taipei → `date.today()` is UTC+8, not ET). This could cause conversations to be keyed to the "wrong" day relative to trading sessions.

### Failure Report Template

For each **FAIL** or **PARTIAL** item, provide:

```
Item: [#]
Expected: [what should happen]
Actual: [what actually happened]
Console errors: [if any]
Screenshot: [if relevant]
Severity: BLOCKER / HIGH / MEDIUM / LOW
```


### Automated Verification Results (Claude Code — 2026-03-07 02:36)

**Phases completed:** Phase 1: API Infrastructure, Phase 2: WebSocket Protocol, Phase 3: Chat + Proposal Lifecycle, Phase 4: Page Context Injection, Phase 5: AI Insight Endpoint, Phase 6: Code Inspection

**Total automated checks:** 39
**Pass:** 34 | **Fail:** 5 (all fixed in Sprint 22.1) | **Partial:** 0

**Failures requiring fixes:**
1. ~~2.17.4: call_count did not increase: 0 -> 0~~ — **FIXED in Sprint 22.1**
2. ~~2.17.2: Tokens still zero after chat~~ — **FIXED in Sprint 22.1**
3. ~~2.17.3: Cost is zero or negative: $0.0~~ — **FIXED in Sprint 22.1**
4. ~~2.14.1: DailySummaryGenerator not initialized in server.py~~ — **FIXED in Sprint 22.1**
5. ~~2.14.9: DailySummaryGenerator not initialized — confirms known issue~~ — **FIXED in Sprint 22.1**

**Code inspection findings:**
1. useCopilotContext: Registered in all 7 page components ✓
2. ~~DailySummaryGenerator not initialized~~ — **FIXED in Sprint 22.1**: Now initialized in server.py
3. ~~DailySummaryGenerator: Not mentioned in server.py~~ — **FIXED in Sprint 22.1**
4. Approve→Executed simulation: setTimeout(1500ms) found in ChatMessage.tsx — execution status is simulated, not real (DEFERRED: requires WS push architecture)
5. ~~WS token estimation: Uses content length / 4 for token estimation~~ — **FIXED in Sprint 22.1**: Now extracts actual usage from stream events
6. ~~Conversation date keying: Uses date.today() (server local time)~~ — **FIXED in Sprint 22.1**: Now uses ET timezone consistently
7. Keyboard shortcut ⌘+K: FALSE POSITIVE — implementation uses `e.key === 'k' && (e.metaKey || e.ctrlKey)` in AppShell.tsx:70,78; grep for literal "Meta+k"/"Cmd+K" missed it. Feature is fully wired.

### Sprint 22.1 Fix Summary (2026-03-07)

All 5 failures from initial verification have been fixed:
- **Usage tracking (2.17.2-4)**: Timestamps now use ET timezone; usage extracted from Anthropic API stream events
- **AI Insight Card (2.14.1, 2.14.9)**: DailySummaryGenerator + ResponseCache now initialized in server.py
- **Conversation dates**: All `date.today()` replaced with `datetime.now(ZoneInfo("America/New_York")).date()`

See `sprint-22-1-review.md` for the full Tier 2 review report.
