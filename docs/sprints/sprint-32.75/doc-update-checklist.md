# Sprint 32.75: Doc Update Checklist

## Documents to Update

### project-knowledge.md
- [ ] Add Arena page to Command Center page list (9 pages, was 8)
- [ ] Update strategy identity section (all 12 strategies with unique colors/badges)
- [ ] Add Arena REST endpoints to API documentation
- [ ] Add Arena WebSocket channel to WS documentation
- [ ] Update overflow.broker_capacity to 60 (was 30)
- [ ] Add post-reconnect delay to IBKRBroker section
- [ ] Add end-of-window logging to BaseStrategy section
- [ ] Add IBC documentation reference
- [ ] Update test counts
- [ ] Add sprint to Sprint History table
- [ ] Update Build Track Queue
- [ ] Add new DEF items (DEF-135 through DEF-139)

### architecture.md
- [ ] Add Arena page architecture section
- [ ] Add `/ws/v1/arena` WebSocket channel specification
- [ ] Add Arena REST API endpoints
- [ ] Update frontend file structure with arena/ feature directory

### CLAUDE.md
- [ ] Add Arena page files to file listing
- [ ] Add new config notes (broker_capacity)
- [ ] Add new files: arena.py, arena_ws.py, ArenaPage.tsx, MiniChart.tsx, ArenaCard.tsx, etc.
- [ ] Update active strategy identity information

### roadmap.md
- [ ] Update Build Track Queue (mark 32.75 complete)
- [ ] Add Arena to completed infrastructure list

### sprint-history.md
- [ ] Add Sprint 32.75 entry with session details, test delta, key changes

### docs/live-operations.md
- [ ] Add IBC setup reference (link to docs/ibc-setup.md)
- [ ] Update reconnection behavior documentation (post-reconnect delay)

### docs/pre-live-transition-checklist.md
- [ ] Add note: `overflow.broker_capacity` was raised to 60 for paper trading; evaluate appropriate value for live trading
- [ ] Add note: post-reconnect delay is 3s; evaluate if this needs adjustment for live

### docs/ui/ux-feature-backlog.md
- [ ] Mark completed items: Arena page, strategy identity, Dashboard layout changes
- [ ] Add new items: DEF-135 through DEF-139

## New Documents Created
- [ ] `docs/ibc-setup.md` — IBC installation, configuration, credential management, launchd setup
- [ ] `scripts/ibc/com.argus.ibgateway.plist` — Template launchd plist for IB Gateway auto-restart
