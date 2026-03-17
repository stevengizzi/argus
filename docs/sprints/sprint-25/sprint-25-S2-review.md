# Sprint 25, Session 2 — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-2-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `python -m pytest tests/api/test_observatory_ws.py -x -q`

## Do Not Modify
`argus/api/websocket/ai_chat.py`, all trading pipeline files

## Review Focus
1. Verify Observatory WS completely independent from AI chat WS (no shared state)
2. Verify push loop uses asyncio.sleep, not blocking sleep
3. Verify tier transition detection compares states without DB writes
4. Verify slow query handling — skip, don't queue
5. Verify JWT auth follows ai_chat.py pattern
6. Verify config-gating prevents mount when disabled

## Output
Write to: `docs/sprints/sprint-25/session-2-review.md`
