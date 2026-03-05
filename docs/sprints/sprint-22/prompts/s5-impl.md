# Sprint 22, Session 5: Action Cards + Approval UX

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ui/src/features/copilot/ChatMessage.tsx` (Session 4a — tool_use placeholder)
   - `argus/ui/src/features/copilot/CopilotPanel.tsx` (Session 4a/4b)
   - `argus/ui/src/stores/copilotUI.ts` (Session 4a/4b)
   - `argus/ai/tools.py` (Session 1 — tool definitions for reference)
   - `argus/ai/actions.py` (Session 3a — proposal states)
   - `argus/api/routes/ai.py` (approve/reject endpoints)
2. Run: `cd argus/ui && npx vitest run`
   Expected: ≥308 tests (previous + Sessions 4a/4b), all passing
3. Run: `python -m pytest tests/ -x -q`
   Expected: ≥1,809 tests, all passing
4. Verify branch: `sprint-22-ai-layer`

## Objective
Build the ActionCard component that renders AI-proposed actions from tool_use data, with Approve/Reject buttons, visual states, approval confirmation, audio notifications, and expiry countdown.

## Requirements

1. **Create ActionCard component** (`argus/ui/src/features/copilot/ActionCard.tsx`):
   - Renders inline within the chat message list (replaces the "[Action proposal]" placeholder from Session 4a)
   - Props: `proposal: { id: string, toolName: string, toolInput: Record<string, any>, status: string, expiresAt: string, result?: Record<string, any>, failureReason?: string }`
   - **Visual layout by tool type:**
     - `propose_allocation_change`: "📊 Allocation Change" — shows strategy name, current → proposed allocation %, reason
     - `propose_risk_param_change`: "⚙️ Risk Parameter" — shows param path, current → proposed value, reason
     - `propose_strategy_suspend`: "⏸️ Suspend Strategy" — shows strategy name, reason
     - `propose_strategy_resume`: "▶️ Resume Strategy" — shows strategy name, reason
     - `generate_report`: "📝 Report" — shows report type (no approval needed, auto-executed)
   - **Status states:**
     - `pending`: Card with amber border. Shows Approve (green) and Reject (red) buttons. Countdown timer showing time until expiry (e.g., "4:32 remaining"). Countdown pulses red when < 1 min.
     - `approved`: Card with green border. "Approved ✓" badge. Buttons replaced with "Executing..." spinner while execution runs.
     - `executed`: Card with green border. "Executed ✓" badge. Shows result summary (e.g., "VWAP Reclaim allocation changed: 25% → 35%").
     - `rejected`: Card with gray border. "Rejected ✗" badge. Dimmed appearance.
     - `expired`: Card with gray border. "Expired" badge. Dimmed. Countdown shows "0:00".
     - `failed`: Card with red border. "Failed" badge. Shows failure reason (e.g., "Execution blocked — regime changed since proposal").

2. **Approve flow:**
   - Click Approve → confirmation dialog: "Execute [action description]? This will take effect immediately."
   - Confirmation → POST /api/v1/ai/actions/{id}/approve
   - On success: transition to 'approved' then 'executed' (with spinner between)
   - On 410 (expired): transition to 'expired' state, show toast "Proposal expired"
   - On 409 (already resolved): show current status
   - On failure: transition to 'failed' with reason

3. **Reject flow:**
   - Click Reject → optional reason input (small text field, can be empty)
   - POST /api/v1/ai/actions/{id}/reject
   - Transition to 'rejected'

4. **Audio notifications (per S1 resolution):**
   - Create notification utility (`argus/ui/src/utils/notifications.ts` or similar):
     - `playProposalNotification()` — plays a short, non-intrusive sound when a new action proposal appears
     - `playExpiryWarning()` — plays a more urgent sound when proposal has < 1 min remaining
     - Use Web Audio API to generate simple tones (no audio file dependency):
       - Proposal notification: two-tone ascending beep (440Hz → 660Hz, 100ms each)
       - Expiry warning: three rapid beeps (880Hz, 80ms each with 50ms gaps)
     - `notificationsEnabled: boolean` in copilot store (default: true)
     - Respect user preference: add toggle in CopilotPanel header (small speaker icon)

5. **Countdown timer:**
   - For pending proposals, show a live countdown from `expiresAt`
   - Update every second
   - At < 60 seconds: text turns red, countdown pulses
   - At < 60 seconds: trigger `playExpiryWarning()` once (not every second)
   - At 0: transition to 'expired' state client-side (also confirmed by server)

6. **Integration with ChatMessage:**
   - In `ChatMessage.tsx`, replace the "[Action proposal]" placeholder
   - When a message has `toolUse` data, render ActionCard(s) after the message text
   - A single assistant message can contain multiple tool_use blocks → multiple ActionCards

7. **State management:**
   - Add to copilot store:
     - `proposals: Record<string, ProposalState>` — keyed by proposal ID
     - `updateProposal(id: string, update: Partial<ProposalState>)` action
   - WebSocket `tool_use` events create proposal entries in the store
   - REST approve/reject responses update proposal state
   - Periodic poll (every 10s) for pending proposals to catch server-side expiry

## Constraints
- Do NOT modify: any backend files
- Do NOT modify: components outside the copilot feature directory (except adding the notification utility)
- Do NOT modify: existing audio/notification systems if any exist
- Do NOT use browser Notification API (not relevant for in-app alerts)
- Audio must be user-gesture-gated (Web Audio context created on first user interaction, per browser policy)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `argus/ui/src/features/copilot/__tests__/ActionCard.test.tsx`:
    - Renders pending state with Approve/Reject buttons
    - Renders executed state with result
    - Renders expired state dimmed
    - Renders failed state with reason
    - Approve click shows confirmation dialog
    - Countdown displays and updates
    - Different visual for each tool type
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] ActionCard renders for all 5 tool types
- [ ] All 6 status states render correctly
- [ ] Approve flow with confirmation dialog
- [ ] Reject flow with optional reason
- [ ] Live countdown timer with expiry warning
- [ ] Audio notifications for proposals and expiry
- [ ] Notification toggle in CopilotPanel header
- [ ] Integration with ChatMessage (replaces placeholder)
- [ ] All existing tests pass
- [ ] ≥4 new Vitest tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Chat still works | Send message, see response stream, no regressions |
| Messages render correctly | Existing messages (no tool_use) display as before |
| Panel animation preserved | Open/close still animated |
| All existing tests pass | `cd argus/ui && npx vitest run` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
[See 06-regression-checklist.md]

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
[See 05-escalation-criteria.md]
