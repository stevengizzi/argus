# Sprint 14 — Session B Prompts (WebSocket + Integration + React)

Copy-paste each prompt sequentially into Claude Code.
This is a NEW Claude Code session — start fresh after Session A.

---

## Session B Grounding Prompt (Prompt 0 — paste first)

```
Sprint 14, Session B. Starting a fresh session.

Session A (6 prompts) completed all REST API endpoints. Before starting, ground yourself:

1. Read the sprint spec: cat docs/sprints/sprint_14_spec.md
2. Read the rules file: cat .claude/rules/sprint-14.md
3. Read these Session A files to understand the patterns established:
   - argus/api/dependencies.py (AppState shape)
   - argus/api/auth.py (auth pattern)
   - argus/api/server.py (app factory)
   - argus/api/routes/__init__.py (router aggregation)
   - argus/api/serializers.py (if exists — may not exist yet)
   - tests/api/conftest.py (test fixtures)
4. Run: python -m pytest tests/ --tb=no -q (confirm current test count, should be ~879)

Then confirm: "Session B grounded. [N] tests passing. Ready for Prompt 7."

Do not write any code yet — just read and confirm.
```

---

## Prompt 7: WebSocket Bridge

```
Sprint 14, Prompt 7 of 10 (Session B, prompt 1 of 4).

Refer to docs/sprints/sprint_14_spec.md Sections 4.6 and 4.7.

This prompt: Event serializer and WebSocket bridge.

Tasks:
1. Create argus/api/serializers.py per spec Section 4.7:
   - serialize_event(event) → dict: converts Event dataclasses to JSON-serializable dicts
   - Handle datetime → ISO string conversion recursively
   - Handle nested dataclasses (e.g., OrderApprovedEvent contains a SignalEvent)
   - Remove "sequence" from data payload (it goes in the wrapper)
   - Graceful fallback to __dict__ if asdict() fails

2. Create argus/api/websocket/live.py per spec Section 4.6. This is the most complex component:
   
   Classes:
   - ClientConnection: holds WebSocket ref, subscribed_types (None = all), send_queue (asyncio.Queue)
   - WebSocketBridge: singleton that subscribes to Event Bus, manages clients, handles throttling
   
   Key behaviors:
   - start(event_bus, order_manager, config): subscribe to all event types in EVENT_TYPE_MAP + TickEvent
   - TickEvent handling: only forward for symbols with open positions (check order_manager.get_managed_positions()), throttle to 1/sec/symbol using monotonic clock
   - _broadcast(): enqueue message to all interested clients (check wants_event)
   - Heartbeat loop: send system.heartbeat every ws_heartbeat_interval_seconds
   - Client management: add_client(), remove_client()
   
   WebSocket endpoint:
   - @ws_router.websocket("/ws/v1/live")
   - Auth via query param: ?token=<jwt>
   - Reject with close code 4001 if auth fails
   - Sender task per client (drains send_queue)
   - Receiver loop handles: ping → pong, subscribe → set filter, unsubscribe → remove filter
   - Clean up on disconnect (cancel sender task, remove client)
   
   Module-level: get_bridge() returns/creates singleton WebSocketBridge

3. Add ws_router to the app in server.py if not already done. The ws_router should be included WITHOUT the /api/v1 prefix — the WebSocket path is /ws/v1/live (not /api/v1/ws/v1/live).

4. Write tests/api/test_websocket.py (~12 tests) per spec Section 6.2:
   - Connect with valid/invalid/missing token
   - Event forwarding (publish event on EventBus → client receives)
   - Tick throttling (publish many TickEvents fast → client gets throttled amount)
   - Tick position filtering (ticks for non-position symbols filtered)
   - Subscribe/unsubscribe filtering
   - Ping/pong
   - Heartbeat (use short interval like 1 second in test)
   - Multiple clients
   
   For WebSocket tests, you'll need to:
   - Use httpx's WebSocket support, or use the starlette TestClient's websocket_connect()
   - Create a test AppState with real EventBus, publish events, and verify they arrive on the WebSocket
   - For tick tests, add mock ManagedPositions to the OrderManager so the position filter passes

All tests pass (existing ~879 + ~12 new = ~891).
```

---

## Prompt 8: Dev State + main.py Integration

```
Sprint 14, Prompt 8 of 10 (Session B, prompt 2 of 4).

Refer to docs/sprints/sprint_14_spec.md Sections 4.1 (dev state), 4.4 (standalone entry), and 4.9 (main.py integration).

This prompt: Mock dev state for frontend development and main.py Phase 11 integration.

Tasks:
1. Create argus/api/dev_state.py — an async factory function create_dev_state() that returns an AppState populated with realistic mock data:
   - Real EventBus (lightweight, no subscriptions needed)
   - Real TradeLogger connected to a temp SQLite database, seeded with ~20 sample trades spanning the last 30 days. Mix of wins (55%), losses (40%), breakeven (5%). Varying exit reasons (target_1, stop_loss, time_stop, eod). Multiple symbols (TSLA, NVDA, AAPL, AMD, META). strategy_id = "orb_breakout".
   - SimulatedBroker configured with $100K starting capital
   - Real HealthMonitor with all components set to HEALTHY
   - Real RiskManager with default config
   - Real OrderManager — inject 2-3 fake ManagedPosition objects so /positions returns data. Use realistic values (entry prices near current market, stops 1-2% below, T1/T2 at 1R/2R).
   - strategies dict with one entry: "orb_breakout" mapped to an OrbBreakoutStrategy instance (use default config from DEC-076 parameters: or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0). Set is_active=True. If the strategy constructor requires dependencies you can't easily provide, create a simple mock strategy class that duck-types the necessary attributes.
   - SystemClock
   - SystemConfig with api section populated (password_hash for "argus", jwt_secret_env pointing to an env var you set in the function)
   - start_time = time.time()

2. Create argus/api/__main__.py for standalone entry:
   ```
   python -m argus.api.server --dev
   python -m argus.api.server --dev --port 8000
   ```
   Per spec Section 4.4 standalone block. In --dev mode, call create_dev_state(), create the app, and run uvicorn directly.

3. Add Phase 11 to argus/main.py per spec Section 4.9:
   - After Phase 10 (data streaming), check config.api.enabled
   - If enabled: create AppState from existing component references, create app, start WebSocket bridge, start server via run_server()
   - Add to shutdown sequence: cancel api_task, stop ws_bridge
   - If not enabled: log "API server disabled" and skip
   - This must not break existing startup if config has no api section (ApiConfig defaults to enabled=True, so it will try to start — make sure it handles gracefully if jwt_secret env var is not set by just logging a warning)

4. Verify:
   - python -m pytest tests/ — all pass
   - python -m argus.api.server --dev — starts without errors, listens on port 8000
   - curl http://localhost:8000/api/v1/health (with auth) returns valid JSON
   - Ctrl+C shuts down cleanly

5. Update CLAUDE.md commands section — add the new commands:
   - python -m argus.api.setup_password
   - python -m argus.api.server --dev
   - python -m argus.api.server --dev --port 8000

All tests pass (~891 + any new integration tests you add).
```

---

## Prompt 9: React Scaffolding

```
Sprint 14, Prompt 9 of 10 (Session B, prompt 3 of 4).

Refer to docs/sprints/sprint_14_spec.md Section 5.

This prompt: Initialize and scaffold the React frontend project.

Tasks:
1. Initialize the React project in argus/ui/:
   ```bash
   cd argus/ui
   npm create vite@latest . -- --template react-ts
   npm install react-router-dom zustand @tanstack/react-query recharts lucide-react
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```
   Note: if npm is not available, install Node.js first (check if node/npm exist).

2. Configure per spec Section 5.2:
   - vite.config.ts with proxy for /api and /ws
   - tailwind.config.js with ARGUS dark theme colors (argus-bg, argus-surface, argus-border, argus-text, argus-text-dim, argus-accent, argus-success, argus-danger, argus-warning)
   - postcss.config.js
   - src/index.css with Tailwind directives + body styling

3. Create TypeScript types — src/api/types.ts per spec Section 5.3. All interfaces for API responses.

4. Create API client — src/api/client.ts per spec Section 5.4:
   - Fetch-based with JWT auth header injection
   - 401 handling (dispatch auth:expired event)
   - Methods: login, refresh, getAccount, getPositions, getTrades, getPerformance, getHealth, getStrategies

5. Create WebSocket client — src/api/ws.ts per spec Section 5.5:
   - Reconnecting WebSocket with exponential backoff
   - onMessage handler registration
   - subscribe/unsubscribe support
   - isConnected getter

6. Create Zustand stores per spec Section 5.6:
   - src/stores/auth.ts — token, isAuthenticated, login, logout, init (check localStorage)
   - src/stores/live.ts — connected, lastMessage, recentEvents, handlers

7. Create components:
   - src/components/ProtectedRoute.tsx — redirects to /login if not authenticated

8. Create pages:
   - src/pages/Login.tsx — dark-themed login form. Password input + submit. Error display. Redirect on success.
   - src/pages/ConnectionTest.tsx — developer validation page with:
     - Auth status section (token info)
     - API endpoint tester (button per endpoint, shows JSON response)
     - WebSocket status (green/red indicator, live event feed)
     - Quick system summary (equity, positions, health from API calls)

9. Create src/App.tsx with React Router:
   - /login → Login page
   - / → ProtectedRoute → ConnectionTest (Sprint 14), will become Dashboard in Sprint 15
   - /dev/connection → ConnectionTest (always accessible for debugging)

10. Update src/main.tsx to render App with router.

11. Add to .gitignore:
    - argus/ui/node_modules/
    - argus/ui/dist/

12. Verify:
    - cd argus/ui && npm run build — succeeds without errors
    - cd argus/ui && npm run dev — starts Vite dev server on 5173
    - In a separate terminal: python -m argus.api.server --dev
    - Open http://localhost:5173 — see login page
    - Login with password "argus" (the dev state password)
    - See ConnectionTest page, API calls return data, WebSocket connects

No Python tests in this prompt — this is frontend scaffolding. Verify with npm run build.
```

---

## Prompt 10: Cleanup + Final Verification

```
Sprint 14, Prompt 10 of 10 (Session B, prompt 4 of 4). FINAL PROMPT.

This prompt: Cleanup, lint, final verification, docs update.

Tasks:
1. Run ruff check on all new Python files. Fix any issues:
   ```
   ruff check argus/api/ argus/analytics/performance.py tests/api/ tests/analytics/
   ```

2. Verify all __init__.py exports are correct:
   - argus/api/__init__.py should export: create_app, AppState, run_server
   - argus/analytics/__init__.py should include performance module if it has exports
   - argus/api/routes/__init__.py should export api_router

3. Run the full test suite with verbose output:
   ```
   python -m pytest tests/ -v --tb=short
   ```
   Report the exact total test count. Target: ~890-910.

4. Verify zero regressions — all 811 original tests still pass. If any fail, fix them.

5. End-to-end smoke test:
   ```
   python -m argus.api.server --dev &
   sleep 2
   
   # Auth
   TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"password":"argus"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
   
   # Hit each endpoint
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/account | python -m json.tool
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/positions | python -m json.tool
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/trades | python -m json.tool
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/performance/month | python -m json.tool
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/health | python -m json.tool
   curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/strategies | python -m json.tool
   
   kill %1
   ```
   All 6 endpoints should return valid JSON with the expected shape.

6. Verify npm build still works:
   ```
   cd argus/ui && npm run build
   ```

7. Update CLAUDE.md:
   - Current State: "Sprint 14 (Command Center API) COMPLETE. [N] tests."
   - Components implemented: add API server entries (FastAPI, WebSocket bridge, JWT auth, PerformanceCalculator, dev state)
   - Commands: verify the new commands are listed
   - Dependencies: add fastapi, uvicorn, python-jose, passlib

8. Update docs/03_ARCHITECTURE.md Section 4 (API Server):
   - Add "Implementation Status: Sprint 14 ✅ COMPLETE" 
   - Add ApiConfig documentation
   - Add note about new dependencies

9. Provide a Docs Status summary:
   - Which docs were updated
   - Current test count
   - Any issues found and fixed
   - Confirmation of gate check items from spec Section 8

Sprint 14 is COMPLETE after this prompt.
```

---

## Post-Session B

After Prompt 10 completes:
1. Review the Docs Status output
2. `git add -A && git commit -m "sprint-14: Command Center API + React scaffolding complete"`
3. Push to GitHub
4. Sync Claude.ai project (click 'Sync now')
5. Remove `.claude/rules/sprint-14.md` (or leave it — won't hurt)
6. Copy the DEC-099–103 entries and other doc updates from `sprint_14_docs_sync.md` into the actual docs if Claude Code didn't already do them
7. Verify: open `http://localhost:5173`, login, confirm ConnectionTest page shows real data
