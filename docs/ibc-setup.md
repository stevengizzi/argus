# IBC Setup Guide — ARGUS

> IBC (Interactive Brokers Controller) automates IB Gateway startup and keeps it
> running across reboots. This guide covers installation, configuration, macOS
> auto-start via launchd, and verification.
>
> **See also:** [pre-live-transition-checklist.md](pre-live-transition-checklist.md)
> documents the Sprint 32.75 post-reconnect 3-second hardcoded delay in the IBKR
> broker client. That behavior is enforced in code (not configurable from IBC)
> but is noted here for operator awareness when correlating reconnect events
> with Gateway restarts.

---

## Prerequisites

- IB Gateway installed (download from [interactivebrokers.com/en/trading/ibgateway-stable.php](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php))
- Java 11+ (bundled with IB Gateway; no separate install needed)
- macOS 12+ (Monterey or later recommended)
- Paper trading credentials for initial setup; live credentials for production

---

## 1. Download and Extract IBC

1. Download the latest IBC release from the official GitHub repository:
   [github.com/IbcAlpha/IBC/releases](https://github.com/IbcAlpha/IBC/releases)
   Choose the `.zip` asset (not the source code archive).

2. Create the IBC directory and extract:

   ```bash
   mkdir -p ~/ibc
   unzip ~/Downloads/IBC-<version>.zip -d ~/ibc
   chmod +x ~/ibc/ibc.sh ~/ibc/scripts/*.sh
   ```

3. Verify the contents:

   ```bash
   ls ~/ibc/
   # Expected: ibc.sh, IBCAlpha.jar, config.ini, scripts/, logs/
   ```

---

## 2. Configure IBC (`config.ini`)

Copy the template and edit it:

```bash
cp ~/ibc/config.ini.sample ~/ibc/config.ini
```

Edit `~/ibc/config.ini` with the values below. **Do not store real credentials
in this file** — use environment variable references (see Security Notes).

### Minimum Required Settings

```ini
# IBC Configuration — Paper Trading Profile
# See full reference: https://github.com/IbcAlpha/IBC/blob/master/userguide.md

[IBController]

# --- Login Credentials ---
# IMPORTANT: Use environment variable substitution — never hardcode credentials.
# IBC supports ${ENV_VAR} syntax in config.ini.
IbLoginId=${IBKR_USERNAME}
IbPassword=${IBKR_PASSWORD}

# --- Trading Mode ---
# Set to "paper" for paper trading, "live" for live trading.
TradingMode=paper

# --- Gateway vs TWS ---
# Use "gateway" to launch IB Gateway (headless, preferred for automated trading).
# Use "tws" to launch TWS (full desktop app, not recommended for automation).
FIXLoginId=
FIXPassword=

# --- Auto-Login ---
# IBC logs in automatically on startup.
AcceptIncomingConnectionRequest=accept
AcceptNonBrokerageAccountWarning=yes

# --- Session Handling ---
# Automatically reconnect if connection drops.
ReloginAfterSecondFactorAuthenticationTimeout=yes
SecondFactorAuthenticationExitInterval=60

# --- IB Gateway Path ---
# Full path to the IB Gateway installation directory.
IbDir=/Applications/Trader Workstation/

# --- API Settings ---
# Bind to localhost only (never expose to network).
# Port must match system_live.yaml ibkr.port (default: 4001 paper, 4002 live).
# These settings mirror what IB Gateway exposes — not set by IBC itself.
# Configure the API port within IB Gateway's application settings.

# --- Logging ---
LogComponents=never
```

### Common Settings Reference

| Setting | Paper Trading | Live Trading |
|---------|--------------|--------------|
| `TradingMode` | `paper` | `live` |
| IB Gateway port | `4001` | `4002` |
| `IbDir` | `/Applications/Trader Workstation/` | Same |

---

## 3. Set Credentials via Environment Variables

Never store IBKR credentials in `config.ini` or any committed file. Use
environment variables loaded from a `.env` file outside the repo:

```bash
# ~/.argus_secrets (NOT inside the argus/ repo directory)
export IBKR_USERNAME="your_ibkr_username"
export IBKR_PASSWORD="your_ibkr_password"
```

Load these in your shell profile or via the launchd plist `EnvironmentVariables`
section (see Section 4).

---

## 4. Auto-Start via launchd (macOS)

The launchd plist template lives at `scripts/ibc/com.argus.ibgateway.plist`.
Copy it to the user LaunchAgents directory and load it:

```bash
# Copy template
cp scripts/ibc/com.argus.ibgateway.plist ~/Library/LaunchAgents/

# Edit the plist to set your actual paths and credentials
# (see template comments for required substitutions)
nano ~/Library/LaunchAgents/com.argus.ibgateway.plist

# Load the agent (starts immediately and on every login)
launchctl load ~/Library/LaunchAgents/com.argus.ibgateway.plist

# Verify it loaded
launchctl list | grep argus
```

### Managing the launchd Agent

```bash
# Stop IB Gateway (graceful)
launchctl unload ~/Library/LaunchAgents/com.argus.ibgateway.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.argus.ibgateway.plist
launchctl load   ~/Library/LaunchAgents/com.argus.ibgateway.plist

# View logs
tail -f /tmp/ibgateway.stdout.log
tail -f /tmp/ibgateway.stderr.log
```

---

## 5. Verification Steps

After IBC starts IB Gateway, verify the setup:

### 5.1 Confirm IBC is Running

```bash
ps aux | grep -i "ibgateway\|IBCAlpha"
# Should show one IBCAlpha.jar process and one IBController process
```

### 5.2 Confirm IB Gateway API is Listening

```bash
# Paper trading default port
nc -zv 127.0.0.1 4001
# Expected: Connection to 127.0.0.1 port 4001 [tcp] succeeded!
```

### 5.3 Test ARGUS Connection (dry-run)

```bash
python -m argus.main --dry-run --config config/system_live.yaml
# Look for: "Connected to IB Gateway at 127.0.0.1:4001"
# No orders should be placed in dry-run mode
```

### 5.4 Confirm Paper Account Number

```bash
# Check that ARGUS connects to the expected account
grep "account" logs/argus_*.log | tail -5
# Expected: account=U24619949 (paper) or Uxxxxxxxx (live — keep private)
```

---

## 6. Security Notes

### Credential Storage

- **Never** put credentials in `config.ini` as plain text
- **Never** commit credentials to git (`.gitignore` covers `.env` files, but
  check with `git status` before committing)
- Use `${ENV_VAR}` substitution in `config.ini` and set variables via:
  - A `.env` file outside the repo, sourced in `.zshrc`/`.bash_profile`
  - The launchd plist `EnvironmentVariables` section (preferred for background processes)
  - macOS Keychain (most secure — retrieve via `security find-generic-password`)

### File Permissions

```bash
# config.ini should be readable only by your user
chmod 600 ~/ibc/config.ini

# IBC log directory
chmod 700 ~/ibc/logs/
```

### Network Exposure

- IB Gateway API binds to `127.0.0.1` only by default — do not change this
- If running ARGUS on a remote machine, use an SSH tunnel rather than exposing
  the API port directly:
  ```bash
  ssh -L 4001:127.0.0.1:4001 user@remote-host
  ```

### API Key Rotation

- If credentials are compromised, rotate immediately via the IBKR web portal
- Update environment variables and restart IBC
- ARGUS will reconnect automatically via `_reconnect()` with exponential backoff

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| IBC exits immediately | Wrong `IbDir` path | Check with `ls "/Applications/Trader Workstation/"` |
| Login fails | Wrong credentials or 2FA | Verify env vars; check if IB requires SMS/app 2FA |
| Port not listening | IB Gateway API not enabled | Enable via Gateway: Configure → API → Settings → Enable ActiveX and Socket Clients |
| ARGUS sees 0 positions after reconnect | IBKR sync delay | Sprint S5 adds 3s delay + 1 retry — should auto-resolve |
| `launchctl list` shows exit code 78 | Missing IB Gateway path | Correct `ProgramArguments` in plist |

---

## 8. Upgrading IBC

1. Download the new release
2. Stop the current agent: `launchctl unload ~/Library/LaunchAgents/com.argus.ibgateway.plist`
3. Back up `config.ini`: `cp ~/ibc/config.ini ~/ibc/config.ini.bak`
4. Extract the new release over the existing directory
5. Restore `config.ini`: `cp ~/ibc/config.ini.bak ~/ibc/config.ini`
6. Reload: `launchctl load ~/Library/LaunchAgents/com.argus.ibgateway.plist`

---

*Last updated: Sprint 32.75 Session 5 (April 1, 2026)*
