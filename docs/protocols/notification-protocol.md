# Protocol: Notification

**Context:** Autonomous Sprint Runner
**Referenced by:** DEC-279
**Output:** Mobile push notifications via ntfy.sh (+ optional Slack/email)

---

## Notification Tiers

| Tier | Priority | When | Example |
|------|----------|------|---------|
| HALTED | High (sound + vibration) | Runner cannot proceed without human input | "Sprint 23: HALTED at S3a. Review verdict: ESCALATE. Regression checklist failed." |
| SESSION_COMPLETE | Normal | Session implementation done + review CLEAR | "Sprint 23 S2a: CLEAR. Tests 1977 → 2012 (+35). Proceeding to S3a." |
| PHASE_TRANSITION | Low | A phase within a session starts or finishes | "Sprint 23 S2a: Review started." |
| WARNING | Low | Non-blocking issue logged | "Sprint 23 S2a: DRIFT-MINOR detected. Naming convention deviation in catalyst.py." |
| COMPLETED | Normal | Sprint run finished (success or with warnings) | "Sprint 23: COMPLETED. 8/8 sessions CLEAR. 47 new tests. Doc sync ready." |

## Per-Tier Configuration

Each tier can be independently enabled or disabled in `runner-config.yaml`:

```yaml
notifications:
  tiers:
    HALTED: true            # Always on — non-negotiable safety gate
    SESSION_COMPLETE: true   # Recommended: always on
    PHASE_TRANSITION: true   # First autonomous runs: on. Once trust established: off.
    WARNING: true            # Recommended: always on
    COMPLETED: true          # Always on
```

**Recommended progression:**
- First 2–3 autonomous sprints: all tiers enabled. PHASE_TRANSITION gives you
  a breadcrumb trail showing the system is alive and progressing.
- After trust is established: disable PHASE_TRANSITION. Keep everything else on.
- Never disable HALTED or COMPLETED.

## ntfy.sh Integration

### Setup (One-Time)

1. Install ntfy app on iPhone (App Store)
2. Subscribe to topic: `argus-sprint-runner` (or any private topic name)
3. Configure topic in `runner-config.yaml`:
   ```yaml
   notifications:
     primary:
       type: "ntfy"
       endpoint: "https://ntfy.sh/argus-sprint-runner"
   ```

### Message Format

```python
import requests

def send_notification(tier: str, title: str, body: str, config: dict):
    if not config["tiers"].get(tier, False):
        return  # Tier disabled

    priority_map = {
        "HALTED": "5",            # Max priority — sound + vibration
        "SESSION_COMPLETE": "3",  # Default priority
        "PHASE_TRANSITION": "2",  # Low priority — no sound
        "WARNING": "2",           # Low priority — no sound
        "COMPLETED": "3",         # Default priority
    }
    tag_map = {
        "HALTED": "warning,rotating_light",
        "SESSION_COMPLETE": "white_check_mark",
        "PHASE_TRANSITION": "arrow_forward",
        "WARNING": "information_source",
        "COMPLETED": "tada",
    }

    headers = {
        "Title": title,
        "Priority": priority_map[tier],
        "Tags": tag_map[tier],
    }

    # Only add action button for HALTED (link to run log)
    if tier == "HALTED" and config.get("run_log_url"):
        headers["Actions"] = f"view, Open Run Log, {config['run_log_url']}"

    requests.post(config["endpoint"], data=body, headers=headers)
```

### Message Templates

**HALTED:**
```
Title: 🚨 Sprint {sprint} HALTED at {session}
Body:  Reason: {halt_reason}
       Phase: {current_phase}
       Sessions completed: {completed}/{total}
       Run log: {run_log_path}
       Resume: python scripts/sprint-runner.py --resume
```

**SESSION_COMPLETE:**
```
Title: ✅ Sprint {sprint} {session}: CLEAR
Body:  Tests: {tests_before} → {tests_after} (+{new_tests})
       Proceeding to: {next_session}
       Progress: {completed}/{total} sessions
```

**PHASE_TRANSITION:**
```
Title: ▶️ Sprint {sprint} {session}: {phase_name}
Body:  {phase_description}
```

Phase transition events:
- "Implementation started"
- "Implementation complete — extracting close-out"
- "Review started"
- "Review complete — verdict: {verdict}"
- "Tier 2.5 triage started"
- "Tier 2.5 triage complete — recommendation: {recommendation}"
- "Conformance check complete — {conformance_verdict}"
- "Fix session {fix_id} started"
- "Fix session {fix_id} complete"
- "Doc sync started"
- "Doc sync complete"

**WARNING:**
```
Title: ℹ️ Sprint {sprint} {session}: {warning_type}
Body:  {warning_description}
       Action taken: {action} (logged, run continues)
```

**COMPLETED:**
```
Title: 🎉 Sprint {sprint} COMPLETED
Body:  Sessions: {completed}/{total} ({warnings} warnings)
       Tests: {test_before} → {test_after} (+{new_tests})
       Fix sessions inserted: {fix_count}
       Estimated cost: ${cost}
       Duration: {duration}
       Doc sync: {doc_sync_status}
```

## Quiet Hours

WARNING and PHASE_TRANSITION notifications are suppressed during configured
quiet hours. SESSION_COMPLETE notifications are suppressed during quiet hours.

HALTED and COMPLETED notifications always send regardless of quiet hours —
HALTED requires human action, COMPLETED is the signal that the run finished.

If quiet hours are active when a suppressed notification would fire, it is
queued and sent in a batch when quiet hours end.

## Reminder Escalation

If a HALTED notification goes unacknowledged (runner remains in HALTED state)
for `halted_reminder_minutes` (default: 60), a reminder is sent. Reminders
repeat at the configured interval until the runner is resumed or manually
stopped.

## Optional Redundancy Channels

### Slack Webhook

```yaml
secondary:
  - type: "slack"
    webhook_url: "https://hooks.slack.com/services/T.../B.../..."
```

### Email (via SMTP)

```yaml
secondary:
  - type: "email"
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    from: "argus-runner@gmail.com"
    to: "steven@example.com"
    use_tls: true
```

Redundancy channels receive all enabled-tier notifications. Quiet hours apply
to redundancy channels identically to the primary channel.

## Logging

All notifications (including suppressed ones) are logged in `run-state.json`
under `notifications_sent`:
```json
{
  "timestamp": "2026-03-07T14:30:00Z",
  "tier": "SESSION_COMPLETE",
  "message": "Sprint 23 S2a: CLEAR. Tests 1977 → 2012 (+35).",
  "channel": "ntfy",
  "delivered": true,
  "suppressed_by_quiet_hours": false
}
```
