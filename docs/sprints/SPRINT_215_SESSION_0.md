# Sprint 21.5 — Session 0: Pre-Flight Setup

> **Do all of this BEFORE opening Claude Code for Session 1.**
> Estimated time: 45–90 minutes (most of it is waiting for downloads/approvals).
> You'll need: a web browser, a credit card, your IBKR login credentials, and a terminal.

---

## Part 1: Databento (~15 minutes)

### 1.1 Create Account + Subscribe

1. Go to **https://databento.com/signup**
2. Create an account (email + password, or Google OAuth)
3. You'll get **$125 in free historical data credits** on signup — these are for pay-as-you-go historical queries and are separate from the subscription
4. Navigate to **https://databento.com/pricing** (or Billing → Plans in the portal)
5. Subscribe to **US Equities Standard — $199/month**
   - This gives you: unlimited live data for all US equities datasets, 10 concurrent live sessions, L0–L2 schemas, historical OHLCV-1s/1m included
   - You'll need a credit card on file
   - Subscription is monthly, cancel anytime
6. **Important:** After subscribing, you may need to complete a short exchange licensing questionnaire for XNAS.ITCH (Nasdaq TotalView-ITCH). Databento will walk you through this in the portal under **Live Data** or **Licensing**. Answer honestly — you're using it for personal/proprietary algorithmic trading, non-display use, not redistributing. This is typically auto-approved.

### 1.2 Get Your API Key

1. In the Databento portal, go to **Settings → API Keys** (or look for a "Keys" section)
2. Click **Create API Key**
3. Name it something like `argus-production`
4. **Copy the key immediately** — it starts with `db-` and is shown only once
5. Store it somewhere safe temporarily (password manager, secure note) — you'll put it in `.env` in Part 4

### 1.3 Verify Access (Optional but Recommended)

Quick sanity check from your terminal that the key works:

```bash
pip install databento
python -c "
import databento as db
client = db.Historical('YOUR_API_KEY_HERE')
# This should return without error — just tests auth
datasets = client.metadata.list_datasets()
print(f'Access confirmed. {len(datasets)} datasets available.')
"
```

If this prints a count, you're good. If it errors with 401/403, double-check the key.

### 1.4 Do NOT Activate Live Data Yet

Live streaming sessions count against your 10-session limit and cost nothing extra, but there's no reason to start one until Session 1. The subscription just needs to be active.

---

## Part 2: Anthropic API Account (~10 minutes)

> This is for Sprint 22 (AI Layer), not Sprint 21.5. But since you're setting everything up, do it now so it's ready.

### 2.1 Create Developer Account

1. Go to **https://console.anthropic.com/**
2. Click **Sign Up** (use Google, Microsoft, Apple, or email)
3. Complete onboarding — select **Individual**, skip optional fields if you want
4. You'll land on the Anthropic Console dashboard

**Note:** This is a separate account from your Claude Pro subscription. The Console is for API access (pay-as-you-go). Your Claude Pro chat subscription is unrelated.

### 2.2 Add Credits

1. In the Console, go to **Billing** (left sidebar)
2. Add a payment method (credit card)
3. Add initial credits: **$25 is plenty to start** (you can always add more)
   - Per DEC-098, ARGUS will use Claude Opus for all API calls, estimated ~$35–50/month at full usage
   - During Sprint 22 development/testing, you'll use far less
4. Alternatively, if you see a "claim free credits" option with phone verification, do that first — it may give you $5–10 to start

### 2.3 Generate API Key

1. In the Console, click **API Keys** (left sidebar, near bottom)
2. Click **Create Key**
3. Name it `argus-ai-layer`
4. **Copy the key immediately** — starts with `sk-ant-` and is shown only once
5. Store it securely alongside your Databento key

### 2.4 Where This Key Goes

You won't need this until Sprint 22, but when you do, it'll go in `.env` as:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

For now, just have it stored safely. Session 1 of Sprint 21.5 won't reference it.

---

## Part 3: IB Gateway (~20 minutes)

### 3.1 Download IB Gateway

1. Go to **https://www.interactivebrokers.com/en/trading/ibgateway-stable.php**
2. Download the **Stable** version for your OS:
   - **macOS:** `.dmg` installer
   - **Windows:** `.exe` installer  
   - **Linux:** `.sh` installer
3. Use the **Stable** version, not "Latest" (Latest is beta/preview)

### 3.2 Install

- **macOS:** Open `.dmg`, drag to Applications. IB Gateway will be in `/Applications/` or `~/Applications/`
- **Windows:** Run installer, accept defaults. Installs to `C:\Jts\ibgateway\`
- **Linux:** `chmod +x ibgateway-stable-standalone-linux-x64.sh && ./ibgateway-stable-standalone-linux-x64.sh` — accept defaults

**Prerequisite:** IB Gateway requires **Java**. The installer bundles its own JRE, so you typically don't need to install Java separately. If the installer complains about Java, install OpenJDK 11+.

### 3.3 First Launch + Paper Trading Login

1. Launch IB Gateway
2. At the login screen:
   - **API Type:** Select **IB API** (not FIX)
   - **Username:** Your IBKR username (same as Client Portal login)
   - **Password:** Your IBKR password
3. **Critical:** Look for a **"Paper Trading"** or **"Live Trading"** toggle/dropdown
   - Select **Paper Trading**
   - The title bar should say "Paper Trading" after login
4. Click **Log In**
5. You may be prompted for two-factor authentication (IBKR Mobile app or security device)
6. After login, you should see a minimal status window showing:
   - Connection status (green = connected)
   - Account ID — should start with **"DU"** (paper) not "U" (live)
   - Server: paper trading server

### 3.4 Configure API Settings

1. In IB Gateway, go to **Configure → Settings → API → Settings** (menu path may vary slightly by version)
2. Verify/set these settings:
   - **Enable ActiveX and Socket Clients:** ✅ Checked
   - **Socket port:** `4002` (this is the paper trading default — do NOT use 4001)
   - **Allow connections from localhost only:** ✅ Checked (security)
   - **Read-Only API:** ❌ Unchecked (ARGUS needs to place orders)
   - **Master API client ID:** Leave blank or set to match IBKR_CLIENT_ID (1)
3. Click **Apply** or **OK**

### 3.5 Verify Paper Account ID

After logging in, note your paper trading account ID. It should look like `DU1234567` (the "DU" prefix confirms paper trading). You'll see this in the Gateway status window or in the account info section. **Write this down** — you'll want to verify it matches what IBKRBroker reports in Session 6.

### 3.6 Leave Gateway Running (or Close for Now)

You don't need Gateway running until Session 6. You can close it now and re-launch when you get to Phase B. But if you want to leave it running to confirm it stays stable, that's fine too.

**Note on Gateway restarts:** IB Gateway will auto-disconnect once per day for maintenance (typically around midnight ET on weekdays, earlier on weekends). When you're actively running ARGUS during US market hours, the nightly restart happens while markets are closed, so it's not a problem. ARGUS has reconnection logic built in (Sprint 13).

---

## Part 4: Project Environment Setup (~15 minutes)

### 4.1 Create `.env` File

In your ARGUS project root (same directory as `config/`, `argus/`, etc.):

```bash
# Create .env file (this should already be in .gitignore — verify!)
cat > .env << 'EOF'
# === Databento (Sprint 21.5, Session 1+) ===
DATABENTO_API_KEY=db-xxxxxxxxxxxxxxxxxxxx

# === IBKR (Sprint 21.5, Session 6+) ===
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1

# === API Auth (already configured if you've run Command Center) ===
ARGUS_JWT_SECRET=your-random-secret-string-here
ARGUS_PASSWORD_HASH=your-bcrypt-hash-here

# === Anthropic API (Sprint 22 — not needed yet) ===
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
EOF
```

**Replace the placeholder values:**
- `DATABENTO_API_KEY` → paste your real Databento key from Part 1.2
- `ARGUS_JWT_SECRET` → if you already have one from Sprint 14+, reuse it. Otherwise generate: `python -c "import secrets; print(secrets.token_hex(32))"`
- `ARGUS_PASSWORD_HASH` → if you already have one, reuse it. Otherwise generate: `python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"`
- `ANTHROPIC_API_KEY` → leave commented out for now, uncomment in Sprint 22

### 4.2 Verify `.gitignore`

```bash
# Check that .env is gitignored
grep -n "\.env" .gitignore
```

You should see `.env` listed. If not, add it:
```bash
echo ".env" >> .gitignore
```

**Never commit `.env` to git.** It contains API keys and secrets.

### 4.3 Verify Python Dependencies

```bash
# Make sure databento client is installed
pip install databento --break-system-packages

# Make sure python-dotenv is installed (Session 1 may add this to requirements.txt formally)
pip install python-dotenv --break-system-packages

# Verify ib_async is installed (should be from Sprint 13)
python -c "import ib_async; print('ib_async OK')"

# Verify databento is installed
python -c "import databento; print('databento OK')"

# Verify dotenv is installed  
python -c "import dotenv; print('dotenv OK')"
```

### 4.4 Verify Git State

```bash
cd /path/to/argus
git status          # Should be clean (no uncommitted changes)
git log --oneline -5  # Should show Sprint 21d as most recent work
```

If you have uncommitted changes from Sprint 21d, commit them now. Sprint 21.5 Session 1 should start from a clean state.

### 4.5 Create `.env.example` (Claude Code will formalize this, but having it now helps)

```bash
cat > .env.example << 'EOF'
# ARGUS Environment Variables
# Copy this file to .env and fill in real values
# NEVER commit .env to git

# Databento Market Data (required for live mode)
DATABENTO_API_KEY=db-your-key-here

# Interactive Brokers (required for live mode)
IBKR_HOST=127.0.0.1
IBKR_PORT=4002          # 4002 = paper trading, 4001 = live (USE 4002)
IBKR_CLIENT_ID=1

# API Authentication
ARGUS_JWT_SECRET=generate-a-random-string
ARGUS_PASSWORD_HASH=generate-with-bcrypt

# Anthropic API — AI Layer (Sprint 22+)
# ANTHROPIC_API_KEY=sk-ant-your-key-here
EOF
```

---

## Part 5: Verification Checklist

Run through this before opening Claude Code for Session 1. Every box should be checked.

### Databento
- [ ] Databento account created at databento.com
- [ ] US Equities Standard subscription active ($199/month)
- [ ] Exchange licensing questionnaire completed (if prompted)
- [ ] API key generated and copied (starts with `db-`)
- [ ] API key stored in `.env` as `DATABENTO_API_KEY`
- [ ] `databento` Python package installed
- [ ] (Optional) Quick auth test passed

### Anthropic API
- [ ] Console account created at console.anthropic.com
- [ ] Credits added ($25+ or free credits claimed)
- [ ] API key generated and copied (starts with `sk-ant-`)
- [ ] API key stored securely (goes in `.env` for Sprint 22, commented out for now)

### Interactive Brokers
- [ ] IB Gateway (Stable) downloaded and installed
- [ ] Successfully logged in to **paper trading** account
- [ ] Paper account ID noted (starts with "DU")
- [ ] API settings configured: Socket Clients enabled, port 4002, localhost only, Read-Only OFF
- [ ] `ib_async` Python package installed (from Sprint 13)

### Project Environment
- [ ] `.env` file created with `DATABENTO_API_KEY`, `IBKR_*`, `ARGUS_JWT_SECRET`, `ARGUS_PASSWORD_HASH`
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` created (committed to git is fine — no real secrets)
- [ ] `python-dotenv` installed
- [ ] Git state clean, Sprint 21d is latest commit
- [ ] Sprint 21.5 spec file saved locally for reference during sessions

### You Have On Hand
- [ ] Sprint 21.5 spec (the full spec document with all 15 session prompts)
- [ ] This Session 0 checklist (for reference during sessions)
- [ ] Databento portal URL bookmarked (for checking connection status, data explorer)
- [ ] IBKR Client Portal bookmarked (for checking paper account positions if needed)

---

## Part 6: What to Expect in Session 1

Once everything above is done, open Claude Code and paste the Session 1 prompt from the Sprint 21.5 spec. Session 1 will:

1. Create `config/system_live.yaml` (you don't need to create this manually)
2. Formalize `.env.example` in the codebase
3. Add `--config` CLI flag to `main.py` if not already present
4. Wire `python-dotenv` loading into the startup sequence
5. Attempt to connect DatabentoDataService to the live Databento API using your key
6. Debug any connection issues

**You do NOT need IB Gateway running for Sessions 1–5.** Gateway is only needed starting Session 6.

**You DO need Databento subscription active for Session 1.** The system will attempt a real API connection.

**Market hours are NOT required for Sessions 1–3.** These can be done anytime — they test connection, data normalization, and historical data. Sessions 4–5 are better during market hours but can work with historical replay. Session 11 MUST be during market hours.

---

## Quick Reference: What's Needed When

| Session | Databento Sub | Databento Key in .env | IB Gateway Running | Market Hours |
|---------|:---:|:---:|:---:|:---:|
| 1–2 | ✅ | ✅ | ❌ | Optional |
| 3 | ✅ | ✅ | ❌ | Optional |
| 4–5 | ✅ | ✅ | ❌ | Preferred |
| 6–9 | ✅ | ✅ | ✅ | Optional (orders work anytime on paper) |
| 10 | ✅ | ✅ | ✅ | Optional |
| 11 | ✅ | ✅ | ✅ | **REQUIRED** |
| 12 | ✅ | ✅ | ✅ | Preferred (live data makes verification meaningful) |
| 13–15 | ✅ | ✅ | ✅ | Sessions 13–14 **REQUIRED**, 15 optional |

---

## Troubleshooting Common Issues

**Databento "license not found" error:**
You may need to complete the exchange licensing questionnaire in the portal before XNAS.ITCH live data works. Go to databento.com → Live Data → look for any pending questionnaires.

**IB Gateway won't connect / "Login failed":**
- Verify username/password match Client Portal login
- Make sure you selected "Paper Trading" mode, not "Live"
- Check if two-factor auth is required (IBKR Mobile app)
- IBKR servers have scheduled maintenance windows (typically brief, late night ET)

**IB Gateway "port already in use":**
Another instance of Gateway or TWS is running. Close it first, or use a different client ID.

**`databento` package import error:**
Make sure you installed it in the correct Python environment (the one ARGUS uses). Check `which python` and `pip install databento` in that environment.

**`.env` not being loaded:**
`python-dotenv` loads from the current working directory. Make sure you run ARGUS from the project root, or Session 1 will wire the path explicitly.
