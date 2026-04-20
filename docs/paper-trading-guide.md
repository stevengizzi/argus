# ARGUS — Paper Trading Validation Guide

> *Version 1.0 | February 16, 2026*
> *A practical, step-by-step guide for validating the Argus trading system on Alpaca paper trading. Keep this open on your desk during market hours.*

---

## 1. What Paper Trading Is and Why It Matters

Paper trading is simulated trading with fake money against real market data. Alpaca provides a dedicated paper trading environment that mirrors their live API — same endpoints, same WebSocket streams, same order types — but with a virtual account balance and no real money at risk.

This is not optional. Paper trading is the bridge between "all tests pass" and "I trust this system with real capital." You are validating that:

- The system runs without crashing for an entire trading session (9:30 AM – 4:00 PM ET)
- Orders that appear in your database match what Alpaca shows in their dashboard
- The ORB strategy identifies reasonable setups (not garbage stocks, not phantom breakouts)
- Risk limits actually prevent excessive exposure
- Stops, breakeven moves, and EOD flatten work as designed
- The system recovers gracefully from the inevitable weird things that happen with live data (gaps, halts, thin liquidity, WebSocket disconnections)

**Minimum validation period:** 3 trading days. **Recommended:** 5–10 trading days before considering any Phase 3 live work.

**Success criteria:** Zero crashes, zero unlogged trades, zero missed EOD flattens, risk limits never exceeded, and at least a few complete trade lifecycles observed (entry → stop management → exit).

---

## 2. Setting Up Your Alpaca Paper Trading Environment

### 2.1 Create Your Alpaca Account

1. Go to https://alpaca.markets and sign up for a free account.
2. After email verification, you'll land on the Alpaca dashboard.
3. You do NOT need to fund the account or provide banking info for paper trading.

### 2.2 Get Your Paper Trading API Keys

1. In the Alpaca dashboard, look for the "Paper Trading" toggle or environment selector. Make sure you're in the **Paper** environment, not Live.
2. Navigate to API Keys (usually under your account or a sidebar menu).
3. Click "Generate New Key" or "Regenerate."
4. You'll get two values:
   - **API Key ID** — looks like `PKXXXXXXXXXXXXXXXX`
   - **API Secret Key** — a longer alphanumeric string. **Copy this immediately.** Alpaca only shows it once. If you lose it, regenerate.
5. Note the **Base URL** for paper trading: `https://paper-api.alpaca.markets`

### 2.3 Configure Argus

Create a `.env` file in your project root (this file is gitignored — never commit it):

```env
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
ALPACA_API_SECRET=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

Verify your config files exist and are reasonable:

```
config/
├── system.yaml          # System-level config (health, logging)
├── risk.yaml            # Risk limits (daily loss, weekly loss, etc.)
├── broker.yaml          # Broker connection settings
├── orb_breakout.yaml    # ORB strategy parameters
├── scanner.yaml         # Scanner universe and filters
└── order_manager.yaml   # Position management settings
```

### 2.4 Set Up Monitoring (Optional but Recommended)

**Healthchecks.io (heartbeat monitoring):**
1. Go to https://healthchecks.io and create a free account.
2. Create a new check. Set the period to 2 minutes, grace period to 5 minutes.
3. Copy the ping URL (looks like `https://hc-ping.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
4. Add it to `config/system.yaml` under `health.heartbeat_url`.
5. When Argus is running, this URL gets pinged every 60 seconds. If pings stop, Healthchecks.io alerts you (email by default).

**Discord webhook (critical alerts):**
1. In Discord, go to a server you control → Server Settings → Integrations → Webhooks.
2. Create a webhook, name it "Argus Alerts", pick a channel.
3. Copy the webhook URL.
4. Add it to `config/system.yaml` under `health.alert_webhook_url`.
5. Argus will POST alerts here for circuit breakers, stale data, and system errors.

### 2.5 Verify Your Setup

Run the dry-run first:

```bash
python -m argus.main --dry-run
```

This should:
- Load all config files without errors
- Connect to Alpaca's paper trading API
- Report your account balance (Alpaca paper accounts typically start with $100,000)
- Initialize all components (you'll see log lines for each startup phase)
- Shut down cleanly without streaming data or placing orders

If this fails, check:
- `.env` file exists and has correct keys
- You're using paper trading keys, not live keys
- Your internet connection is working
- Alpaca's status page (https://status.alpaca.markets/) shows no outages

---

## 3. Your First Trading Day

### 3.1 Pre-Market (Before 9:30 AM ET)

**What time zone are you in?** All market times are Eastern Time (ET). Market hours are 9:30 AM – 4:00 PM ET. The operator is on the US East Coast (ET) — no timezone conversion needed.

**Start Argus 15–30 minutes before market open:**

```bash
python -m argus.main --paper
```

Watch the startup logs. You should see:
1. Config loaded
2. Database connected
3. Broker connected (account info printed)
4. Health monitor started
5. Risk Manager initialized (state reconstructed if not the first day)
6. Data service connected
7. Scanner running pre-market scan
8. Strategy initialized
9. Order Manager ready
10. Streaming started

**The scanner runs at startup.** It looks for stocks gapping up in pre-market. Check the logs for the watchlist — you should see something like:

```
INFO: AlpacaScanner found 5 candidates: TSLA (+3.2%), NVDA (+2.8%), ...
```

If the scanner finds zero candidates, that's possible on quiet mornings — the strategy simply won't trade that day. If it consistently finds zero, your scanner filters (min gap%, price range, volume) may be too restrictive.

### 3.2 Market Open (9:30 AM ET)

The first 15 minutes (9:30 – 9:45 AM ET) is the **opening range formation period** for the ORB strategy. Argus is watching but NOT trading during this window. It's building the opening range (high and low of the first N minutes, configured in `orb_breakout.yaml`).

In the logs, you should see candle events arriving every minute and the strategy tracking the opening range internally.

### 3.3 Active Trading Window (9:45 AM – 11:30 AM ET)

This is when the ORB strategy is active. If a stock breaks above its opening range high with confirmation (volume > 1.5x average, price > VWAP, candle close above OR high), the strategy generates a SignalEvent.

**What you'll see in logs for a trade:**

```
INFO: OrbBreakout signal: BUY TSLA @ 245.30 (stop 243.80, targets [247.30, 249.30])
INFO: RiskManager approved signal for TSLA (200 shares)
INFO: OrderManager placing bracket order for TSLA
INFO: AlpacaBroker order submitted: <order_id>
INFO: AlpacaBroker order filled: TSLA 200 @ 245.32
INFO: Position opened: TSLA 200 shares @ 245.32
```

After a position opens, the Order Manager monitors it via tick data:
- **T1 hit:** First profit target reached. Partial exit, stop moves to breakeven.
- **T2 hit:** Second profit target reached. Full exit. Trade complete.
- **Stop hit:** Price hits stop loss. Full exit at a loss.
- **Time stop:** Position held too long (configurable). Exit at market.
- **EOD flatten:** 3:50 PM ET. Any remaining positions are closed.

### 3.4 After Hours

After 4:00 PM ET (or when you stop Argus):
- Ctrl+C sends SIGINT for graceful shutdown
- Components shut down in reverse order
- All pending data is flushed to the database

---

## 4. Daily Validation Checklist

Run this every day after the trading session ends. This is the most important part of paper trading — you're building confidence that the system works correctly.

### 4.1 Compare Database to Alpaca Dashboard

**Open the Alpaca dashboard:** Go to https://app.alpaca.markets and make sure you're viewing your paper trading account. Navigate to Activity or Order History.

**Query your local database:**

```bash
sqlite3 data/argus.db
```

Useful queries:

```sql
-- All trades from today
SELECT * FROM trades WHERE date(entry_time) = date('now');

-- Summary: how many trades, total P&L
SELECT 
    COUNT(*) as num_trades,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(realized_pnl), 2) as total_pnl
FROM trades 
WHERE date(entry_time) = date('now');

-- Check for any open positions that should have been closed
SELECT * FROM trades WHERE exit_time IS NULL;

-- All daily summaries
SELECT * FROM strategy_daily_summary ORDER BY date DESC LIMIT 5;
```

**What to verify:**
- Every order shown in Alpaca's dashboard has a corresponding entry in your trades table
- Fill prices match (within a few cents — paper fills can have minor slippage)
- No "ghost" trades in the database that don't appear in Alpaca (would indicate a logging bug)
- No open positions remaining after EOD flatten (the `exit_time IS NULL` query should return nothing after market close)

### 4.2 Check Log Files

Logs are written to the structured JSON log file (location depends on your `logging_config`). Look for:

```bash
# Errors (anything unexpected)
grep '"level":"ERROR"' logs/argus.log | tail -20

# Warnings (might be fine, might indicate issues)
grep '"level":"WARNING"' logs/argus.log | tail -20

# Circuit breaker events (should be rare in paper trading)
grep 'circuit_breaker' logs/argus.log

# Stale data alerts (should only appear if data feed had issues)
grep 'stale_data' logs/argus.log

# Reconnection events (WebSocket dropped and recovered)
grep 'reconnect' logs/argus.log
```

### 4.3 Check Healthchecks.io

If you set up heartbeat monitoring, verify:
- Pings were consistent throughout market hours (no gaps longer than 2–3 minutes)
- If there are gaps, correlate with your log files to find what happened

### 4.4 Check Discord Alerts

If you set up Discord alerts, review any messages that came through. Common alerts:
- Circuit breaker triggered (hit daily loss limit)
- Stale data detected (no candle for a subscribed symbol in X seconds)
- Component health degraded (WebSocket reconnecting)

### 4.5 Evaluate Trade Quality (Subjective)

This is where your trading experience matters. Look at the trades the system took:
- Were these reasonable ORB setups? (Pull up the charts on TradingView or Alpaca's chart)
- Did the opening range form on a stock that was actually moving, or was it noise?
- Were stop placements sensible (below the opening range low)?
- Did any trades get stopped out immediately (possible sign of entering into resistance)?
- Were the gap stocks the scanner found actually interesting, or junk?

You're not judging profitability yet — 3 days is far too little data. You're judging whether the system is making *sensible decisions* based on the strategy logic.

---

## 5. What to Watch For (Common Issues)

### 5.1 No Trades Happening

Possible causes:
- **Scanner finding nothing:** Check your scanner config. If your min_gap_pct is too high or price range is too narrow, you might filter out everything on quiet days. Look at the scanner log output at startup.
- **No breakouts confirming:** The ORB strategy has three confirmation filters (candle close, volume, VWAP). On low-volatility days, stocks might form an opening range but never break out convincingly. This is the strategy working correctly — not trading is sometimes the right decision.
- **Risk Manager rejecting everything:** Check if you've hit daily loss limits from prior trades, or if the account is too small for the position sizes the strategy wants. Look for `OrderRejected` events in the logs.

If zero trades happen across 3+ trading days, something is probably misconfigured. Common culprits: scanner universe too small, gap thresholds too high, or position sizing requesting more shares than the account can afford.

### 5.2 Immediate Stop-Outs

If trades consistently get stopped out within seconds or a few minutes:
- The opening range might be too narrow (tight range = tight stop = easy to hit). Check `orb_breakout.yaml` for the opening range duration.
- The strategy might be entering on false breakouts (price pokes above OR high then reverses). The confirmation filters should catch most of these, but not all.
- Slippage on entry might be placing you further from the stop than expected.

### 5.3 WebSocket Disconnections

Alpaca's WebSocket streams occasionally drop, especially during high-volatility moments (ironically, exactly when you need them most). Argus has reconnection logic with exponential backoff. In the logs, you'll see:

```
WARNING: WebSocket disconnected. Reconnecting in 1s...
INFO: WebSocket reconnected.
```

Occasional disconnections (a few per day) are normal. Frequent disconnections (every few minutes) suggest a network issue on your end or an Alpaca outage.

**Concern:** If a disconnection happens while you have an open position, you temporarily lose tick-level monitoring. The broker-side bracket order (stop + take-profit) provides safety — those orders live on Alpaca's servers and execute regardless of your connection. You just lose the Order Manager's active management (stop-to-breakeven, time stops) during the outage.

### 5.4 EOD Flatten Not Firing

The EOD flatten is scheduled for 3:50 PM ET by default (configurable in `order_manager.yaml`). If positions remain after 4:00 PM:
- Check if the system was still running at 3:50 PM (maybe it crashed earlier)
- Check logs for EOD flatten attempts — it might have fired but the market-on-close order failed
- Verify the time zone handling is correct (the system uses the clock protocol, which should use ET for market operations)

**Manual cleanup:** If positions remain open after market close during paper trading, you can close them via the Alpaca dashboard directly. Click the position and hit "Close." This isn't a crisis for paper trading, but track it — it would be a problem with real money.

### 5.5 Database/Log Inconsistencies

If the database shows a trade that Alpaca doesn't, or vice versa:
- Check if the order was submitted but not filled (partial fills, rejected orders)
- Check if the WebSocket order update stream missed an event
- Check if the system crashed between order submission and fill logging

Document every inconsistency. These are the bugs that matter most for Phase 3.

---

## 6. The Alpaca Dashboard — What You're Looking At

### 6.1 Account Overview

Shows your paper account balance, equity, buying power, and today's P&L. The initial paper balance is typically $100,000 (Alpaca sets this; you can't change it, but it's enough for testing).

Key terms:
- **Equity:** Total account value (cash + market value of positions)
- **Buying Power:** How much you can buy. For a margin account (Alpaca paper default), this is typically 4x equity for day trades. Argus doesn't use margin (DEC-036), so it self-limits to cash available.
- **P&L Today:** Realized + unrealized gains/losses for the current session.

### 6.2 Positions

Shows currently open positions. During market hours, you should see positions appear here when Argus opens trades and disappear when they close. After market close, this should be empty (EOD flatten).

### 6.3 Orders

Shows order history. You'll see bracket orders appear as groups — a primary market order (the entry) with attached stop-loss and take-profit orders. Statuses:
- **New:** Order submitted, waiting to fill
- **Filled:** Order executed. The fill price and quantity are shown.
- **Partially Filled:** Only some shares filled (unusual for market orders on liquid stocks)
- **Canceled:** Order was canceled (by Argus or by you)
- **Rejected:** Alpaca rejected the order (insufficient buying power, invalid parameters, etc.)

### 6.4 Activity

A chronological log of all account activity — fills, dividends, transfers, etc. This is the most useful view for comparing against your database.

---

## 7. Recording Your Observations

Keep a daily log. This doesn't need to be fancy — a text file, a notebook, whatever works. For each trading day, record:

```
## Day N — [Date] — [Day of Week]

Market conditions: [Bullish/bearish/choppy? Any major news?]
Scanner results: [How many candidates? Were they reasonable?]
Trades taken: [Count, symbols]
Trades won/lost: [Count each]
Total P&L: [Dollar amount]
System uptime: [Did it run the full session? Any restarts?]

Issues found:
- [List any bugs, unexpected behavior, or concerns]

Configuration changes needed:
- [Any parameters that seem wrong based on today's observations]

Questions for later:
- [Anything you want to investigate or discuss]
```

This log becomes input for Phase 2 (backtesting parameter decisions) and Phase 3 (live trading readiness assessment).

---

## 8. When to Stop Paper Trading and Move Forward

Paper trading validation is complete when ALL of the following are true:

1. **Stability:** The system has run for 3+ full trading days with zero crashes and zero unhandled exceptions.
2. **Data integrity:** Every trade in the database matches Alpaca's records. No ghost trades, no missing trades.
3. **Risk compliance:** Daily loss limits, position sizing, and circuit breakers all work correctly. No limit was exceeded.
4. **Complete lifecycle:** You've observed at least one trade go through the full lifecycle: entry → stop management (breakeven move on T1) → exit (either T2, stop, time stop, or EOD flatten). Ideally, you've seen multiple exit types.
5. **EOD flatten:** Works correctly every day. No positions remain after market close.
6. **Recovery:** If any restarts happened (intentional or due to issues), the system reconstructed its state correctly — Risk Manager daily P&L was accurate, Order Manager recovered open positions.
7. **Monitoring:** Heartbeat pings are consistent. Alerts fire when they should.

You do NOT need to be profitable. Profitability in 3–5 days is statistically meaningless. You need the system to be *correct* — executing the strategy as designed, logging everything, and maintaining risk limits.

If issues are found, fix them, reset your validation counter, and run for another 3 days. Don't carry forward partial validation periods where known bugs existed.

---

## 9. Useful Commands Reference

```bash
# Start paper trading
python -m argus.main --paper

# Dry run (connect but don't trade)
python -m argus.main --dry-run

# Query the database
sqlite3 data/argus.db

# Today's trades
sqlite3 data/argus.db "SELECT * FROM trades WHERE date(entry_time) = date('now');"

# Open positions (should be empty after market close)
sqlite3 data/argus.db "SELECT * FROM trades WHERE exit_time IS NULL;"

# Total P&L for a date range
sqlite3 data/argus.db "SELECT ROUND(SUM(realized_pnl), 2) FROM trades WHERE entry_time >= '2026-02-16';"

# Check the logs for errors
grep '"level":"ERROR"' logs/argus.log

# Check scanner results
grep 'Scanner' logs/argus.log | head -20

# Check for rejected orders
grep 'rejected' logs/argus.log

# Watch logs in real time (while system runs)
tail -f logs/argus.log | python -m json.tool
```

---

## 10. Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| System won't start | Missing `.env` or bad API keys | Check `.env` values, regenerate keys if needed |
| "Connection refused" on startup | Alpaca outage or network issue | Check https://status.alpaca.markets/ |
| Scanner finds 0 stocks | Filters too restrictive or pre-market hasn't opened | Widen gap%/price/volume filters in `scanner.yaml` |
| No trades after hours of running | No breakouts confirming, or risk rejecting all signals | Check logs for SignalEvent and OrderRejected events |
| Trades in Alpaca but not in DB | Logging bug or crash between fill and log | Check logs around the fill timestamp for errors |
| Trades in DB but not in Alpaca | Should not happen — investigate immediately | This would indicate a serious bug in order submission |
| EOD flatten missed | System crashed before 3:50 PM ET | Check system uptime; manually close positions in Alpaca dashboard |
| Constant WebSocket disconnects | Network instability | Check your internet; consider a wired connection |
| "Insufficient buying power" | Position size too large for account | Check position sizing in ORB config; verify account balance |
| Circuit breaker triggered | Hit daily loss limit | Working as designed. Review the trades that caused the losses. |

---

*End of Paper Trading Validation Guide v1.0*
*Update this document based on discoveries during the validation period.*
