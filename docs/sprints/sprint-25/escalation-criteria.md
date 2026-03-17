# Sprint 25: Escalation Criteria

## Automatic Halt Triggers

1. **Three.js performance below 30fps** with 3,000+ symbol particles on a mid-range machine (e.g., M1 MacBook Air). If instanced meshes alone do not achieve this, HALT and escalate before continuing with S6b or S7. Resolution may require WebGL instancing optimization, LOD aggressiveness tuning, or reducing particle count with sampling.

2. **Bundle size increase exceeds 500KB gzipped** for the Observatory code-split chunk (excluding Three.js itself, which is already in the bundle). Escalate to investigate tree-shaking, code splitting boundaries, or dependency reduction.

3. **WebSocket endpoint causes measurable degradation** to existing `/ws/v1/ai/chat` Copilot endpoint — increased latency, dropped messages, or connection instability. HALT S2 and investigate shared resource contention.

4. **Any modification discovered necessary to strategy logic, Event Bus, evaluation telemetry schema, or trading pipeline**. The Observatory must be read-only. If a required data point cannot be obtained without modifying the pipeline, HALT and escalate to Tier 3 review for architectural decision.

5. **Non-Observatory page load time increases by more than 100ms** due to bundle changes, route changes, or shared state. Code-splitting must fully isolate Observatory dependencies.

## Judgment Escalation Triggers

6. **Matrix virtual scrolling introduces visible jank** on scroll with 200+ rows. May need to switch virtualization library or approach. Flag in close-out, attempt fix in session fix slot before escalating.

7. **Candlestick chart (Lightweight Charts) conflicts with Three.js** — both use canvas/WebGL. If rendering artifacts or context conflicts occur, flag and investigate. Lightweight Charts uses 2D canvas; Three.js uses WebGL — they should not conflict, but escalate if they do.

8. **Keyboard shortcut conflicts with browser or OS shortcuts.** Some key combinations (e.g., `Ctrl+[`) may be intercepted by the browser. If documented shortcuts cannot be bound, propose alternatives in close-out.

9. **Dev mode mock data insufficient** for meaningful visual testing. If the evaluation telemetry dev data doesn't produce realistic funnel populations, escalate to create a richer dev data generator before continuing with visual sessions.

## Human Decision Points

10. **After S6b (Funnel particles working):** Visual checkpoint — does the funnel feel right? Is the spatial metaphor working? The developer should assess before proceeding to S7 (Radar).

11. **After S10 (integration polish):** Full walkthrough. The developer should run ARGUS in dev mode and navigate all 4 views, exercise all keyboard shortcuts, and verify the experience meets the design intent from the strategic check-in conversation.
