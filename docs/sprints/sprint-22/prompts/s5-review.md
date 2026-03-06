# Tier 2 Review: Sprint 22, Session 5 — Action Cards + Approval UX

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

    sprint-22-package/prompts/review-context.md

## Tier 1 Close-Out Report

[PASTE SESSION 5 CLOSE-OUT REPORT HERE]

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
