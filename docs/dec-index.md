# ARGUS — Decision Index

> 358 decisions (DEC-001 through DEC-358)
> Generated: March 23, 2026 | Source: `docs/decision-log.md`
> Legend: ● Active | ○ Superseded | △ Amended | ✗ Duplicate entry


## Phase A — Core Engine (Sprints 1–5)

- ● **DEC-001**: System Name — ARGUS
- ● **DEC-002**: Primary Programming Language — Python 3.11+
- △ **DEC-003**: Brokerage Architecture — broker-agnostic abstraction (amended by DEC-083)
- ● **DEC-004**: Primary Broker for Phase 1 — Alpaca
- ● **DEC-005**: Market Data Strategy
- ● **DEC-006**: Backtesting Framework
- ● **DEC-007**: Database Technology — SQLite via aiosqlite
- ● **DEC-008**: UI Platform — Tauri + PWA
- ● **DEC-009**: Claude's Role — co-captain with approval gate
- ● **DEC-010**: Asset Class Priority — US Stocks → Crypto → Forex → Futures
- ● **DEC-011**: Trading Direction — long only for V1
- ● **DEC-012**: ORB Stop Placement
- ● **DEC-013**: Risk Management Structure — three-level gating
- ● **DEC-014**: Deployment Infrastructure
- ● **DEC-015**: Notification Channels
- ● **DEC-016**: Capital Growth & Withdrawal Model
- ● **DEC-017**: Shadow Paper Trading System
- ● **DEC-018**: Strategy Incubator Pipeline — 10 stages
- ● **DEC-019**: Market Regime Classification V1
- ● **DEC-020**: Simulation & Stress Testing
- ● **DEC-021**: Learning Journal
- ● **DEC-022**: Two-Claude Workflow with Git as Bridge
- ● **DEC-023**: Documentation Update Protocol
- ● **DEC-024**: GitHub Repo Connected to Claude.ai
- ● **DEC-025**: Event Bus Ordering — FIFO per subscriber, monotonic sequence numbers
- ● **DEC-026**: Trade ID Format — ULIDs
- ● **DEC-027**: Risk Manager Modification — approve-with-modification, never modify stops/entry
- ● **DEC-028**: Strategy Statefulness — daily-stateful, session-stateless
- ● **DEC-029**: Data Delivery — Event Bus sole streaming mechanism
- ● **DEC-030**: Order Manager — event-driven + 5s fallback poll + EOD flatten
- ○ **DEC-031**: IBKR Adapter Phase Deferral — superseded by DEC-083
- ● **DEC-032**: Configuration Validation — Pydantic BaseModel, YAML → Pydantic
- ● **DEC-033**: Event Bus Type-Only Subscription (V1)
- ● **DEC-034**: Async Database Access — aiosqlite
- ● **DEC-035**: Sprint 2 Micro-Decisions
- ● **DEC-036**: SimulatedBroker Has No Margin Model
- ● **DEC-037**: Cash Reserve Uses Start-of-Day Equity
- ● **DEC-038**: Sprint 3 Micro-Decisions
- ● **DEC-039**: Sprint 4a Micro-Decisions
- ● **DEC-040**: Order Manager Stop Management — Cancel and Resubmit
- ● **DEC-041**: EOD Flatten Scheduling — Fallback Poll
- ● **DEC-042**: TradeLogger Integration — Direct Call from Order Manager
- ● **DEC-043**: AlpacaScanner Universe — Static Config
- ● **DEC-044**: Exit Rules Delivery — Prices from Signal, Time/Trail from Config
- ● **DEC-045**: Sprint 5 Micro-Decisions

## Phase B — Backtesting (Sprints 6–11)

- ● **DEC-046**: Backtrader Removal — Replay Harness + VectorBT sufficient
- ● **DEC-047**: Walk-Forward Validation — mandatory, WFE > 0.3, 70/30 split
- ● **DEC-048**: Parquet File Granularity
- ● **DEC-049**: Historical Data Time Zone — UTC storage
- ● **DEC-050**: Split-Adjusted Prices for Backtesting
- ● **DEC-051**: Alpaca Free Tier Rate Limit Handling
- ● **DEC-052**: Scanner Simulation — gap computation from prev_close to day_open
- ● **DEC-053**: Synthetic Tick Generation — 4 ticks per bar, worst-case ordering
- ● **DEC-054**: Fixed Slippage Model — $0.01/share for V1
- ● **DEC-055**: BacktestDataService — step-driven, controlled by ReplayHarness
- ● **DEC-056**: Backtest Database Naming Convention
- ● **DEC-057**: VectorBT Open-Source for Parameter Sweeps
- ● **DEC-058**: VectorBT Gap Scan Pre-Filter
- ● **DEC-059**: Per-Symbol VectorBT Sweeps with Aggregation
- ● **DEC-060**: Dual Visualization for Parameter Sweeps
- ● **DEC-061**: Strategy Timezone Conversion at Consumer
- ● **DEC-062**: max_range_atr_ratio Added to VectorBT Sweep
- ● **DEC-063**: VectorBT Fallback — Pure NumPy/Pandas (numba issues)
- ● **DEC-064**: VectorBT ATR Filter Bug Fix
- ● **DEC-065**: ATR Sweep Threshold Adjustment — old thresholds produced identical buckets
- ● **DEC-066**: Walk-Forward Optimization Metric — Sharpe with min_trades floor
- ● **DEC-067**: Report Format — HTML only with Plotly
- ● **DEC-068**: Report Chart Library — Plotly primary, matplotlib fallback
- ● **DEC-069**: Cross-Validation Implementation (DEF-009)
- ● **DEC-070**: Legacy Slow Function Removal (DEF-010)
- ● **DEC-071**: News & Catalyst Intelligence — Three-Tier Architecture
- ● **DEC-072**: Walk-Forward Fixed-Params Mode
- ● **DEC-073**: Sprint 10 Walk-Forward Results — Inconclusive (Scenario C)
- ● **DEC-074**: Cross-Validation Mismatch — RESOLVED (3 bugs fixed)
- ● **DEC-075**: Disable max_range_atr_ratio for Phase 3
- ● **DEC-076**: Phase 3 ORB Parameter Recommendations
- ✗ **DEC-076**: Phase 3 ORB Parameter Recommendations *(duplicate entry — same content, different wording)*
- ● **DEC-077**: Phase Restructure — Comprehensive Validation Phase
- ● **DEC-078**: Fix earliest_entry — changed 09:45 to 09:35

## Phase C — Infrastructure Pivot (Sprints 12–13)

- ● **DEC-079**: Parallel Development Tracks — Build + Validation separation
- ● **DEC-080**: Command Center Delivery — web + desktop + mobile from single codebase
- ● **DEC-081**: IEX Data Feed Limitation — only 2–3% of volume
- ● **DEC-082**: Market Data Architecture — Databento Standard $199/mo primary
- ● **DEC-083**: Execution Broker — direct IBKR adoption, no phased migration
- ● **DEC-084**: Sprint Resequencing — data + broker adapters before Command Center
- ● **DEC-085**: Historical Data — Databento source, Parquet cache
- ● **DEC-086**: Alpaca Role Reduction — strategy incubator only
- ● **DEC-087**: Databento Subscription Timing — defer until adapter ready
- ● **DEC-088**: DatabentoDataService Threading — callbacks on reader thread, `call_soon_threadsafe()`
- ○ **DEC-089**: Default Dataset XNAS.ITCH — superseded by DEC-248 (EQUS.MINI)
- ● **DEC-090**: DataSource Enum for Provider Selection
- ● **DEC-091**: Shared Databento Normalization Utility — `databento_utils.py`
- ● **DEC-092**: IndicatorEngine Extraction (resolves DEF-013)
- ● **DEC-093**: Native IBKR Bracket Orders with T1/T2 Support
- ● **DEC-094**: BrokerSource Enum and IBKRConfig
- ● **DEC-095**: DEF-016 Evaluation — atomic bracket refactor deferred

## Phase D — Command Center + Strategies (Sprints 14–20)

- ● **DEC-096**: Sprint Resequencing — Empowerment MVP
- ○ **DEC-097**: Databento Activation Timing — superseded by DEC-143/161
- ● **DEC-098**: AI Layer Model Selection — Claude Opus, separate API account
- ● **DEC-099**: API Server Lifecycle — in-process Phase 11
- ● **DEC-100**: API Dependency Injection — AppState + FastAPI Depends()
- ● **DEC-101**: WebSocket Event Filtering — curated list, tick throttling
- ● **DEC-102**: Authentication — single-user JWT with bcrypt
- ● **DEC-103**: Monorepo Structure — argus/api/ + argus/ui/
- ● **DEC-104**: Chart Libraries — Lightweight Charts + Recharts (extended by DEC-215)
- ● **DEC-105**: Responsive Breakpoints — <640px / 640–1023px / ≥1024px
- ● **DEC-106**: UI/UX Feature Backlog Document
- ● **DEC-107**: Sprint 16 UX Enhancements — motion, sparklines, polish
- ● **DEC-108**: Sprint 21 Scope — CC Analytics & Strategy Lab
- ● **DEC-109**: Design North Star — "Bloomberg Terminal meets modern fintech"
- ● **DEC-110**: Animation Library — Framer Motion + CSS transitions
- ● **DEC-111**: Control Endpoints — strategy pause/resume, emergency flatten/pause
- ● **DEC-112**: CSV Trade Export — StreamingResponse, 10K row limit
- ● **DEC-113**: Regime Classification V1 Data Source — SPY realized vol as VIX proxy
- ● **DEC-114**: Orchestrator Allocation — equal weight V1
- ● **DEC-115**: Continuous Regime Monitoring
- ● **DEC-116**: Strategy Correlation Tracker — infrastructure now, allocation later
- ● **DEC-117**: DEF-016 Resolution — atomic bracket orders in Order Manager
- ● **DEC-118**: Pre-Market Scheduling — self-contained poll loop
- ● **DEC-119**: Single-Strategy Allocation Cap — 40% max, intentional idle capital
- ● **DEC-120**: OrbBaseStrategy ABC — shared ORB family base
- ● **DEC-121**: ALLOW_ALL Duplicate Stock Policy
- ● **DEC-122**: Per-Signal Time Stop — time_stop_seconds on SignalEvent
- ● **DEC-123**: ORB Scalp Trade Management — 0.3R target, 120s hold
- ● **DEC-124**: Risk Manager ↔ Order Manager Reference
- ● **DEC-125**: CandleEvent Routing via EventBus
- ● **DEC-126**: Sector Exposure Deferred (DEF-020)
- ● **DEC-127**: ORB Scalp VectorBT — directional guidance only (bar resolution insufficient)
- ● **DEC-128**: Three-Way Position Filter
- ● **DEC-129**: Positions UI Zustand Store
- ● **DEC-130**: Frontend Testing — Vitest
- ● **DEC-131**: Session Summary Card Dev Override
- ● **DEC-132**: Pre-Databento Backtests Require Re-Validation
- ● **DEC-133**: CapitalAllocation — track+fill donut with bars toggle
- ● **DEC-134**: Dashboard 3-Card Second Row
- ● **DEC-135**: Orchestrator Status API — deployment state enrichment
- ● **DEC-136**: VwapReclaimStrategy — standalone from BaseStrategy
- ● **DEC-137**: VWAP Reclaim Scanner — reuse ORB gap watchlist
- ● **DEC-138**: VWAP Reclaim State Machine — 5 states
- ● **DEC-139**: VWAP Reclaim Stop — pullback swing low
- ● **DEC-140**: VWAP Reclaim Position Sizing — minimum risk floor
- ● **DEC-141**: VWAP Reclaim Cross-Strategy — ALLOW_ALL
- ● **DEC-142**: Watchlist Sidebar in Sprint 19
- ● **DEC-143**: Databento Activation Deferred to Sprint 20
- ● **DEC-144**: VectorBT VWAP Reclaim Sweep Architecture — precompute+vectorize
- ● **DEC-145**: Walk-Forward VWAP Reclaim Dispatch
- ● **DEC-146**: VWAP Reclaim Backtest Results — provisional (DEC-132)
- ● **DEC-147**: Watchlist Sidebar Responsive Architecture
- ● **DEC-148**: VectorBT ↔ Live State Machine Divergences harmonized
- ● **DEC-149**: VectorBT Performance Rule — precompute+vectorize mandated
- ● **DEC-150**: Watchlist UX — sparklines removed, VWAP distance metric
- ● **DEC-151**: Keyboard Shortcuts — 1–4 nav, w watchlist
- ● **DEC-152**: Afternoon Momentum — standalone from BaseStrategy
- ● **DEC-153**: Consolidation Detection — high/low channel + ATR filter
- ● **DEC-154**: Afternoon Momentum Scanner — gap watchlist reuse
- ● **DEC-155**: Afternoon Momentum State Machine — 5 states
- ● **DEC-156**: Afternoon Momentum Entry — 8 simultaneous conditions
- ● **DEC-157**: Afternoon Momentum Stop/Target — T1=1.0R, T2=2.0R, dynamic time stop
- ● **DEC-158**: Trailing Stop Deferred to V2 (DEF-024)
- ● **DEC-159**: Afternoon Momentum EOD — force close 3:45 PM
- ● **DEC-160**: Cross-Strategy — ALLOW_ALL, time-separated
- ● **DEC-161**: Databento Activation Deferred to Sprint 21
- ● **DEC-162**: VectorBT Afternoon Momentum Divergences Harmonized

## Phase E — Seven-Page Architecture + Live (Sprints 21+)

- ● **DEC-163**: Expanded Vision — AI-enhanced, 15+ patterns
- ● **DEC-164**: Catalyst Data — free sources first (EDGAR, Finnhub, FMP)
- ○ **DEC-165**: L2 for Watchlist Symbols — superseded by DEC-237
- △ **DEC-166**: Short Selling — Sprint 27 (amended by DEC-238/240)
- ● **DEC-167**: Pattern Library — batch build, parallel validation
- ● **DEC-168**: UI Integration Principle — intelligence visible everywhere
- ● **DEC-169**: Seven-Page Architecture (all 7 built)
- ● **DEC-170**: Contextual AI Copilot — Claude on every page
- ● **DEC-171**: Sprint 21 Split — 4 sub-sprints
- ● **DEC-172**: Strategy Metadata in Config YAML
- ● **DEC-173**: Pipeline Stage in Config
- ● **DEC-174**: Strategy Family Classification
- ● **DEC-175**: Strategy Spec Sheets as Markdown
- ● **DEC-176**: Backtest Tab — structured placeholder
- ● **DEC-177**: SlideInPanel Extraction + Symbol Detail
- ● **DEC-178**: Fundamentals Deferred to Sprint 23
- ● **DEC-179**: Incubator Pipeline Responsive Design
- ● **DEC-180**: Keyboard Shortcuts 1–5
- ● **DEC-181**: Auto-Discover Strategy Spec Sheets
- ● **DEC-182**: Z-Index Layering Hierarchy
- ● **DEC-183**: Compact Chart Prop Pattern
- ● **DEC-184**: Document Modal Reader
- ● **DEC-185**: Arrow Key Navigation in Pattern Library
- ● **DEC-186**: Orchestrator Page — vertical flow layout
- ● **DEC-187**: Throttle Override Design
- ● **DEC-188**: Strategy Coverage Timeline — custom SVG
- ● **DEC-189**: Mobile Navigation with 6 Pages
- ● **DEC-190**: Session Phase Computation
- ● **DEC-191**: Regime Input Display — client-side scoring
- ● **DEC-192**: Orchestrator Hero Row Layout
- ● **DEC-193**: Strategy Display Config Consolidation
- ● **DEC-194**: Decision Log Newest-First
- ● **DEC-195**: Regime Gauge Redesign
- ● **DEC-196**: Journal Entry Types
- ● **DEC-197**: Briefings Table Schema
- ● **DEC-198**: Research Library — hybrid filesystem + database
- ● **DEC-199**: Navigation — 7 pages, shortcuts 1–7 (amends DEC-189/180/151)
- ● **DEC-200**: Search — LIKE over FTS5
- ● **DEC-201**: Journal Trade Linking
- ● **DEC-202**: ApiError Class — HTTP status preservation
- ● **DEC-203**: Batch Trade Fetch Endpoint
- ● **DEC-204**: Dashboard Scope Refinement — ambient awareness
- ● **DEC-205**: Performance Page Expansion — 5 tabs, 8 visualizations
- ● **DEC-206**: Trade Activity Heatmap — D3
- ● **DEC-207**: Portfolio Treemap — D3
- ● **DEC-208**: Comparative Period Overlay
- ● **DEC-209**: Trade Replay Mode
- ● **DEC-210**: System Page Cleanup
- ● **DEC-211**: Navigation Restructure — sidebar dividers, mobile More sheet
- ● **DEC-212**: AI Copilot Shell — CopilotPanel + CopilotButton + store
- ● **DEC-213**: Pre-Market Dashboard Layout
- ● **DEC-214**: Goal Tracking Config
- ● **DEC-215**: Chart Library Assignments — D3 modules + Recharts + Custom SVG + LC
- ● **DEC-216**: Mobile Primary Tabs — 5+More
- ● **DEC-217**: Copilot Button Positioning
- ● **DEC-218**: Performance Tab Organization
- ● **DEC-219**: StrategyDeploymentBar — per-strategy capital deployment
- ● **DEC-220**: GoalTracker — pace dashboard
- ● **DEC-221**: Dashboard 3-Card Row — MarketStatus + TodayStats + SessionTimeline
- ● **DEC-222**: Dashboard Aggregate Endpoint
- ● **DEC-223**: useSummaryData Hook Disabling Pattern
- ● **DEC-224**: Unified Diverging Color Scale
- ● **DEC-225**: Dynamic Text Color — WCAG luminance
- ● **DEC-226**: Correlation Matrix — single-letter strategy labels
- ● **DEC-227**: Performance Desktop Layout Density
- ● **DEC-228**: Performance Tab Keyboard Shortcuts
- ● **DEC-229**: Performance Workbench — deferred
- ● **DEC-230**: Sprint 21.5 — Live Integration Sprint
- ● **DEC-231**: Separate Config for Live — `system_live.yaml`
- ● **DEC-232**: IB Gateway (not TWS)
- ● **DEC-233**: All 4 Strategies Active from First Live Session
- ○ **DEC-234**: Databento XNAS First, Add XNYS — superseded by DEC-248
- ● **DEC-235**: Sprint 21.6 — Backtest Re-Validation separated
- ● **DEC-236**: IBKR Account Approved — U24619949
- ● **DEC-237**: Standard Plan = L0+L1 Only — supersedes DEC-165
- ● **DEC-238**: Order Flow Model Deferred to Post-Revenue
- ● **DEC-239**: Setup Quality Engine — 5 dimensions in V1
- ● **DEC-240**: Sprint Roadmap Renumbered — Order Flow removed
- ● **DEC-241**: Databento API — instrument_id direct attribute
- ● **DEC-242**: Databento Symbology — built-in `symbology_map`
- ● **DEC-243**: Databento Prices — fixed-point format (1e9 scale)
- ● **DEC-244**: Databento Historical — ~15-minute intraday lag
- ● **DEC-245**: flatten_all() SMART Routing Fix
- ● **DEC-246**: get_open_orders() Broker ABC Method
- ● **DEC-247**: Scanner Resilience — historical data lag handling
- ● **DEC-248**: EQUS.MINI Confirmed — all US exchanges, one feed
- △ **DEC-249**: Concentration Limit — approve-with-modification, 0.25R floor — amended by DEC-251 (absolute $100 floor replaces ratio)
- ● **DEC-250**: Metarepo Workflow Retrofit
- ● **DEC-251**: Replace 0.25R Ratio Floor with Absolute Minimum Risk Floor
- ● **DEC-252**: Round Order Prices to Tick Size Before IBKR Submission
- ● **DEC-253**: Add Data Heartbeat Logging
- ● **DEC-254**: Auto-Shutdown After EOD Flatten
- ● **DEC-255**: Downgrade IBKR Maintenance Errors Outside Market Hours
- ● **DEC-256**: Add Symbol Field to PositionClosedEvent
- ● **DEC-257**: Hybrid Multi-Source Data Architecture — Databento streaming + FMP scanning
- ● **DEC-258**: FMP Starter for Pre-Market Scanning ($22/mo)
- ● **DEC-259**: Sprint 21.7 — FMP Scanner Integration
- ● **DEC-260**: Data Provider Evaluation — IQFeed, dxFeed, Exegy, Finnhub, QuantConnect rejected
- ● **DEC-261**: ORB Family Same-Symbol Mutual Exclusion — ClassVar prevents dual-fire
- ● **DEC-262**: Roadmap Consolidation — Unified Strategic Direction
- ● **DEC-263**: Full-Universe Strategy-Specific Monitoring Architecture
- ● **DEC-264**: Full DEC-170 Scope in Sprint 22 — AI Copilot complete in single sprint
- ● **DEC-265**: WebSocket for AI Chat Streaming — bidirectional, JWT auth
- ● **DEC-266**: Calendar-Date Conversation Keying with Tags — pre-market, session, research, debrief, general
- ● **DEC-267**: Action Proposal TTL with DB Persistence — 5-min expiry, SQLite storage
- ● **DEC-268**: Per-Page Context Injection Hooks — useCopilotContext on all 7 pages
- ● **DEC-269**: Demand-Refreshed AI Insight Card — auto-refresh during market hours
- ● **DEC-270**: Markdown Rendering Stack — react-markdown + remark-gfm + rehype-sanitize
- ● **DEC-271**: Claude tool_use for Structured Action Proposals — native API over JSON parsing
- ● **DEC-272**: Five-Type Closed Action Enumeration — 4 approval + 1 immediate
- ● **DEC-273**: System Prompt Template with Token Budgets — guardrails + context limits
- ● **DEC-274**: Per-Call Cost Tracking — ai_usage table, real-time monitoring
- ● **DEC-275**: Compaction Risk Scoring System — quantitative point-based session sizing
- ● **DEC-276**: AI Timestamps Standardized on ET — naive ET strings, no UTC storage
- ● **DEC-277**: Fail-Closed on Missing Reference Data — system filters and routing exclude symbols with None prev_close/avg_volume

## Phase F — Autonomous Sprint Runner (Sprint 23.1)

- ● **DEC-278**: Autonomous Sprint Runner Architecture — Python orchestrator, deterministic state machine, CLI invocation
- ● **DEC-279**: Notification via ntfy.sh — mobile push notifications, 5 priority tiers
- ● **DEC-280**: Structured Close-Out Appendix — machine-parseable JSON appended to close-out reports
- ● **DEC-281**: Structured Review Verdict — machine-parseable JSON with CLEAR/CONCERNS/ESCALATE
- ● **DEC-282**: Tier 2.5 Automated Triage Layer — Claude Code triage session for scope gaps and prior-session bugs
- ● **DEC-283**: Spec Conformance Check at Session Boundaries — cumulative diff vs sprint spec
- ● **DEC-284**: Run-Log Architecture — all output to disk immediately, JSONL append-only
- ● **DEC-285**: Git Hygiene Protocol — per-session commits, checkpoints, rollback on escalate
- ● **DEC-286**: Runner Retry Policy — 2 retries for transient failures, LLM-compliance differentiation
- ● **DEC-287**: Cost Tracking and Ceiling — token usage tracking, configurable cost ceiling
- ● **DEC-288**: Dynamic Test Baseline Patching — adjust pre-flight test counts based on prior session
- ● **DEC-289**: Session Parallelizable Flag — planning-time flag for agent teams enablement
- ● **DEC-290**: Claude.ai Role in Autonomous Mode — exception handler and strategic layer
- ● **DEC-291**: Independent Test Verification — runner runs tests to verify close-out claims
- ● **DEC-292**: Pre-Session File Existence Validation — verify prior session Creates exist
- ● **DEC-293**: Compaction Detection Heuristic — track output size, flag compaction-likely sessions
- ● **DEC-294**: Session Boundary Diff Validation — git diff vs planned Creates/Modifies
- ● **DEC-295**: Exponential Retry Backoff — 4× multiplier, rate-limit detection
- ● **DEC-296**: Planning-Time Mode Declaration — autonomous/human-in-the-loop/undecided
- ● **DEC-297**: Review Context File Hash Verification — SHA-256 integrity check
- ● **DEC-298**: FMP Stable API Migration — Legacy v3/v4 → Stable Endpoints
- ● **DEC-299**: Full-Universe Input Pipe via FMP Stock-List — ~8,000 symbols → ~3,000–4,000 viable

## Phase G — NLP Catalyst Pipeline (Sprint 23.5)

- ● **DEC-300**: Config-Gated Catalyst Pipeline Feature Flag — `catalyst.enabled` (default: false)
- ● **DEC-301**: Rule-Based Fallback Classifier — keyword matching when Claude API unavailable/ceiling reached
- ● **DEC-302**: Headline Hash Deduplication — SHA-256 of symbol+headline+source, UNIQUE constraint
- ● **DEC-303**: Daily Cost Ceiling Enforcement — $5/day via UsageTracker, fallback on breach
- ● **DEC-304**: Three-Source Architecture — SECEdgarSource, FMPNewsSource, FinnhubSource
- ● **DEC-305**: TanStack Query Hooks — useCatalysts, useIntelligenceBriefings, useIntelligenceBriefing
- ● **DEC-306**: Finnhub Free Tier for News — company news + analyst recommendations, 60 calls/min
- ● **DEC-307**: Intelligence Brief View — fourth tab in The Debrief, BriefingCard component

## Phase H — Pipeline Integration + Warm-Up Optimization (Sprint 23.6)

- ● **DEC-308**: CatalystPipeline Initialization Deferred — build in 23.5, integrate in 23.6
- ● **DEC-309**: Separate catalyst.db SQLite — isolation from trading data
- ● **DEC-310**: CatalystConfig in SystemConfig — lifespan handler access
- ● **DEC-311**: Semantic Deduplication — (symbol, category, time_window) grouping
- ● **DEC-312**: Batch-Then-Publish Ordering — persist before notify
- ● **DEC-313**: FMP Canary Test — early warning for API schema changes
- ● **DEC-314**: Reference Data File Cache — JSON cache, incremental warm-up
- ● **DEC-315**: Intelligence Polling Loop — asyncio task, market-hours-aware intervals

## Phase I — Startup Scaling Fixes (Sprint 23.7)

- ● **DEC-316**: Time-Aware Indicator Warm-Up — skip pre-market, lazy per-symbol mid-session
- ● **DEC-317**: Periodic Reference Cache Saves — every 1,000 symbols + on shutdown signal
- ● **DEC-318**: API Server Port Guard + Double-Bind Fix — removed duplicate WS bridge start, socket check

## Phase J — Intelligence Pipeline Live QA Fixes (Sprint 23.8)

- ● **DEC-319**: asyncio.wait_for 120s Safety Timeout — wraps pipeline gather, prevents indefinite hang
- ● **DEC-320**: Polling Task Health Monitoring — done_callback + app_state reference, makes crashes visible
- ● **DEC-321**: Intelligence Pipeline Symbol Scope — scanner watchlist (not full universe), capped fallback
- ● **DEC-322**: Source-Level Socket Timeouts — validated sock_connect=10, sock_read=20 on all sources
- ● **DEC-323**: FMP News Circuit Breaker — 401/403 disables source for cycle, resets next cycle
- ● **DEC-324**: Cost Ceiling Enforcement — per-call daily cost check, fallback on breach, cycle cost logging
- ● **DEC-325**: Classifier usage_tracker None Guards — validated, silent degradation when AI disabled
- ● **DEC-326**: Databento Lazy Warm-Up End Clamp — now - 600s buffer, skip if clamped end < start
- ● **DEC-327**: Intelligence Pipeline Firehose Architecture — deferred to Sprint 24 design; per-symbol polling replaced by watchlist scoping as interim fix
- ● **DEC-328**: Test Suite Tiering — full suite at sprint entry + close-outs + final review; scoped tests for mid-sprint pre-flights and non-final reviews

## Phase K — Frontend + Test Cleanup (Sprint 23.9)

- ● **DEC-329**: Gate Frontend Intelligence Hooks on Pipeline Health Status — `usePipelineStatus` hook gates catalyst/briefing TanStack queries on health endpoint pipeline component; fail-closed default

## Phase L — Setup Quality Engine (Sprint 24)

- ● **DEC-330**: SignalEvent Enrichment Fields + ORB Pattern Strength — `pattern_strength`, `signal_context`, `quality_score`, `quality_grade` on SignalEvent; `_calculate_pattern_strength()` on OrbBaseStrategy; QualitySignalEvent
- ● **DEC-331**: VWAP/AfMo Pattern Strength + Order Manager share_count=0 Guard — `_calculate_pattern_strength()` for VWAP Reclaim and Afternoon Momentum; all strategies emit `share_count=0`; OM early-return on zero shares
- ● **DEC-332**: Firehose Source Refactoring (DEC-327 Implementation) — `firehose: bool` parameter on CatalystSource.fetch_catalysts(); Finnhub single general news call; SEC EDGAR EFTS search
- ● **DEC-333**: SetupQualityEngine 5-Dimension Scoring — pattern strength, catalyst quality, volume profile, historical match, regime alignment; SetupQuality dataclass; QualityEngineConfig
- ● **DEC-334**: DynamicPositionSizer + Config Models with Validators — grade-to-risk-tier mapping; QualityWeightsConfig, QualityThresholdsConfig, QualityRiskTiersConfig Pydantic models
- ● **DEC-335**: Config Wiring + quality_engine.yaml + quality_history Table — QualityEngineConfig in SystemConfig; standalone + embedded YAML; 20-column DB table with 4 indexes
- ● **DEC-336**: Pipeline Wiring + RM Check 0 + Quality History Recording — `_process_signal()` extraction in main.py; Risk Manager rejects `share_count ≤ 0`; QualitySignalEvent published; bypass modes
- ● **DEC-337**: Quality Pipeline Integration Tests + Error Paths — 12 integration tests covering engine exception, missing catalyst/RVOL, regimes, bypasses; test_main.py hang fix
- ● **DEC-338**: Server Quality Component Init + Firehose Pipeline Wiring — quality engine initialization in server lifespan; `firehose: true` default for polling loop; health component registration
- ● **DEC-339**: Quality API Routes (3 Endpoints) — `GET /{symbol}` latest score, `GET /history` paginated, `GET /distribution` grade distribution; quality router registered
- ● **DEC-340**: Quality UI — QualityBadge + Hooks + Trades Integration — QualityBadge component with grade coloring + tooltip; 3 TanStack Query hooks; quality column in Trades; Setup Quality in TradeDetailPanel
- ● **DEC-341**: Quality UI — Dashboard + Orchestrator + Performance + Debrief Panels — QualityDistributionCard (donut), SignalQualityPanel (histogram), RecentSignals list, QualityGradeChart (grouped bars), QualityOutcomeScatter (scatter + trend line); shared GRADE_COLORS/GRADE_ORDER constants

## Phase M — Strategy Observability (Sprint 24.5)

- ● **DEC-342**: Strategy Evaluation Telemetry — in-memory ring buffer (maxlen=1000), no EventBus integration, ET naive timestamps per DEC-276, REST endpoint GET /strategies/{id}/decisions, SQLite persistence with 7-day retention, StrategyDecisionStream frontend component

## Phase N — Universe Manager Watchlist Wiring Fix (Sprint 25.5)

- ● **DEC-343**: Watchlist Population from UM Routing — `set_watchlist(symbols, source="universe_manager")` after `build_routing_table()` in Phase 9.5; `_watchlist` list→set for O(1) lookups; external API unchanged
- ● **DEC-344**: Zero-Evaluation Health Warning — `HealthMonitor.check_strategy_evaluations()` detects populated watchlist + zero evaluations after operating window + 5 min grace; DEGRADED status; self-corrects; 60s asyncio task during market hours

## Phase O — Bug Sweep (Sprint 25.6)

- ● **DEC-345**: Evaluation Telemetry DB Separation — EvaluationEventStore writes to `data/evaluation.db`; store created in main.py Phase 10.3; server.py conditional creation; health check reuses store; write warning rate-limiting (60s)
- ● **DEC-346**: Periodic Regime Reclassification — `Orchestrator.reclassify_regime()` public method; 300s periodic task in main.py with market hours guard; sleep-first pattern; SPY unavailability retains current regime

## Phase P — Post-Session Operational Fixes (Sprint 25.7)

- ● **DEC-347**: FMP Daily Bars for Regime Classification — `fetch_daily_bars()` via FMP stable historical-price-eod endpoint
- ● **DEC-348**: Automated Debrief Data Export at Shutdown — `debrief_export.py` produces `logs/debrief_YYYYMMDD.json`
- ● **DEC-349**: Performance Throttler Zero-Trade-History Guard — early return `ThrottleAction.NONE` on empty history
- ● **DEC-350**: Entry Evaluation conditions_passed Metadata — `conditions_passed`/`conditions_total` in ORB ENTRY_EVALUATION events

## Phase Q — API Auth + Close-Position Fix (Sprint 25.8)

- ● **DEC-351**: API Auth 401 for Unauthenticated Requests — `HTTPBearer(auto_error=False)` + explicit 401 with `WWW-Authenticate` header
- ● **DEC-352**: Close-Position Endpoint Routes Through OrderManager — `OrderManager.close_position(symbol)` for single-symbol teardown

## Phase 5 Gate — Strategic Check-In (March 2026)

- ● **DEC-353**: Historical data purchase deferred indefinitely — Standard plan includes free OHLCV-1m
- ● **DEC-354**: Phase 6 compression — BacktestEngine pulled to Sprint 27
- ● **DEC-355**: Gate 2 paper trading day counter reset (~4 valid days)
- ● **DEC-356**: FMP Premium upgrade deferred until Learning Loop data

## Amendment Adoption — Strategic Decision Session (March 2026)

- ● **DEC-357**: Experiment Infrastructure Amendment — Adopted. Sprints 27.5 (Evaluation Framework) + 32.5 (Experiment Registry + Promotion Pipeline + Anti-Fragility). Mods: API-based veto, SQLite interim storage for Sprint 28. DEC ranges reserved: 359–368, 386–395.
- ● **DEC-358**: Intelligence Architecture Amendment — Adopted. Sprints 27.6 (Regime Intelligence) + 27.7 (Counterfactual Engine) + 33.5 (Adversarial Stress Testing). Execution Quality mods to 21.6 + 27.5. Historical data confirmed: XNAS.ITCH + XNYS.PILLAR OHLCV-1m back to May 2018 at $0. DEC ranges reserved: 369–378, 379–385, 396–402.
