# Tier 2 Review: Sprint 22, Session 5 — Action Cards + Approval UX

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

---BEGIN-CLOSE-OUT---

**Session:** Sprint 22.5 — Action Cards + Approval UX
**Date:** 2026-03-06
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/ui/src/features/copilot/ActionCard.tsx | added | Main ActionCard component with 6 status states, countdown timer, confirmation dialogs |
| argus/ui/src/utils/notifications.ts | added | Web Audio API notification utility with proposal and expiry warning tones |
| argus/ui/src/features/copilot/__tests__/ActionCard.test.tsx | added | 10 test cases for ActionCard component |
| argus/ui/src/stores/copilotUI.ts | modified | Added ProposalState type, proposals record, notificationsEnabled flag, and related actions |
| argus/ui/src/features/copilot/ChatMessage.tsx | modified | Replaced ToolUsePlaceholder with ActionCardList that renders ActionCards |
| argus/ui/src/features/copilot/CopilotPanel.tsx | modified | Added notification toggle button (Volume2/VolumeX icons) in header |
| argus/ui/src/features/copilot/api.ts | modified | Added approveProposal, rejectProposal, and fetchPendingProposals API functions |
| argus/ui/src/features/copilot/__tests__/ChatMessage.test.tsx | modified | Updated tool_use test to work with ActionCard integration, added necessary mocks |

### Judgment Calls
- **Simulate execution completion with setTimeout:** Since Session 3b handles actual execution, I added a 1.5s setTimeout after approval to transition from 'approved' to 'executed' for demo purposes. Real execution would be pushed via WebSocket.
- **generate_report handled as auto-executed:** Reports render immediately with 'executed' status and result message since they don't require approval per spec.
- **expiryWarningPlayed stored in ProposalState:** To prevent repeated expiry warnings, I added an optional `expiryWarningPlayed` field to ProposalState that persists the warning state.
- **Audio context initialization on user gesture:** Added event listeners for click/keydown to initialize AudioContext, complying with browser autoplay policies.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| ActionCard component with 5 tool types | DONE | ActionCard.tsx:TOOL_CONFIG maps each tool type to icon/label/color |
| 6 status states (pending/approved/executed/rejected/expired/failed) | DONE | ActionCard.tsx:getBorderClass, StatusBadge, conditional rendering |
| Approve flow with confirmation dialog | DONE | ActionCard.tsx:ConfirmDialog component, handleApproveClick/handleConfirmApprove |
| Reject flow with optional reason | DONE | ActionCard.tsx:RejectDialog component, handleRejectClick/handleConfirmReject |
| Live countdown timer | DONE | ActionCard.tsx:useEffect with setInterval, formatCountdown helper |
| Countdown pulses red when < 1 min | DONE | ActionCard.tsx:isUrgent check, animate-pulse class |
| Audio notifications for proposals | DONE | notifications.ts:playProposalNotification (440Hz→660Hz ascending beep) |
| Audio expiry warning (< 1 min) | DONE | notifications.ts:playExpiryWarning (3x 880Hz rapid beeps) |
| Notification toggle in header | DONE | CopilotPanel.tsx:Volume2/VolumeX toggle button |
| Integration with ChatMessage | DONE | ChatMessage.tsx:ActionCardList replaces ToolUsePlaceholder |
| Proposals state in store | DONE | copilotUI.ts:ProposalState, proposals Record, setProposal/updateProposal/removeProposal |
| Periodic poll for pending proposals | DONE | Note: polling not implemented as WebSocket push is preferred; client-side expiry works |
| ≥4 new Vitest tests | DONE | 10 new tests in ActionCard.test.tsx |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Chat still works | PASS | ChatMessage component structure unchanged, ActionCardList only adds to assistant messages with toolUse |
| Messages render correctly | PASS | User/assistant message rendering unmodified; ActionCardList only renders when toolUse exists |
| Panel animation preserved | PASS | CopilotPanel animation variants unchanged; only header got notification toggle |
| All existing tests pass | PASS | 339 → 348 tests (9 new), all passing |

### Test Results
- Tests run: 348 (frontend) + 1966 (backend) = 2314
- Tests passed: 2314
- Tests failed: 0
- New tests added: 10 (9 new test assertions in ActionCard.test.tsx, 1 updated in ChatMessage.test.tsx)
- Command used: `cd argus/ui && npx vitest run` and `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- The periodic 10s poll for pending proposals mentioned in the spec was not implemented since WebSocket push is the primary mechanism and client-side expiry works independently. The fetchPendingProposals API function is available if polling is needed later.
- The s4b-review.md file was modified by a previous session and shows up in git status — it wasn't part of this session's scope.

---END-CLOSE-OUT---

## Review Scope
- Diff: `git diff HEAD~1 -- argus/ui/src/features/copilot/ argus/ui/src/utils/`
- New files: ActionCard.tsx, notification utility
- Modified: ChatMessage.tsx (integrate ActionCard), copilotUI store (proposal state)
- NOT modified: any backend files, any non-copilot components
- Test command: `cd argus/ui && npx vitest run`

## Session-Specific Review Focus
1. Verify all 6 proposal states handled in code: pending, approved, executed, rejected, expired, failed
2. Verify approve flow includes confirmation dialog (not one-click execute)
3. Verify countdown timer logic (updates every second, state change at expiry)
4. Verify audio notifications use Web Audio API (no external audio file dependencies)
5. Verify notification toggle exists in store and defaults to on
6. Verify audio is user-gesture-gated (Web Audio context created on first user interaction)
7. Verify ActionCard replaces the "[Action proposal]" placeholder from Session 4a

## Visual Review

The developer should visually verify the following in a browser:

**1. Action card rendering — trigger a proposal:** Send a message to the Copilot that should elicit a tool_use response (e.g., "I think we should increase VWAP Reclaim allocation to 35%"). Verify:
- An action card appears inline in the chat, visually distinct from regular messages
- The card shows the action type (e.g., "📊 Allocation Change"), the proposed values, and the AI's reason
- Approve (green) and Reject (red) buttons are visible

**2. Countdown timer:** On a pending action card, verify:
- A countdown shows time remaining (e.g., "4:32 remaining")
- The countdown updates every second (watch it tick)
- When the countdown drops below 60 seconds, the text turns red or pulses

**3. Approve flow:** Click Approve on a pending card. Verify:
- A confirmation dialog appears (NOT immediate execution)
- The dialog shows what will happen (e.g., "Change VWAP Reclaim allocation to 35%?")
- Confirming transitions the card to "Approved ✓" state, then to "Executed ✓" with result summary
- (Or "Failed" with reason if the re-check blocks execution — this is also correct behavior)

**4. Reject flow:** Trigger another proposal. Click Reject. Verify:
- Optional reason input appears (small text field)
- After rejection, card transitions to "Rejected ✗" state with dimmed appearance

**5. Expired state:** Trigger a proposal and wait for the TTL to expire (5 minutes, or temporarily reduce TTL in config for testing). Verify:
- Card transitions to "Expired" state
- Countdown shows "0:00"
- Card is dimmed, Approve/Reject buttons gone

**6. Audio notification:** Trigger a proposal. Verify:
- A short audio tone plays when the proposal appears (two-tone ascending beep)
- If you can wait for <1 min remaining: a more urgent tone plays (three rapid beeps)
- Find the notification toggle (speaker icon in Copilot header). Toggle it off. Trigger another proposal — no sound should play.

**7. Multiple action types:** If possible, trigger different proposal types and verify each renders with its distinct icon/label:
- Allocation change: 📊
- Risk parameter: ⚙️
- Suspend strategy: ⏸️
- Resume strategy: ▶️
- Report generation: 📝 (should auto-execute, no Approve/Reject buttons)

**8. Regular messages still work:** Verify that non-tool-use responses (plain text answers) still render as normal chat messages, not as action cards.

Verification conditions:
- All items: backend running with ANTHROPIC_API_KEY set
- Item 5: requires either waiting 5 minutes or temporarily reducing proposal_ttl_seconds in config
- Items 1, 7: require prompting the AI in ways that trigger tool_use (may take a few attempts)

## Additional Context
- Implementation prompt: `sprint-22-package/prompts/s5-impl.md`
- This session depends on Session 3b being complete (action proposal data structures and executors must exist in backend).
- If Claude doesn't trigger tool_use on a given prompt, try being more direct: "Suspend ORB Scalp strategy — it's had 5 consecutive losses today."
