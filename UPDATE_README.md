# Bot Update — v2.0

## What Changed

This is a full rework of the bot flow and user experience. The bot is now **bot-first** instead of group-first.

### New User Flow

1. User opens the bot and taps /start
2. Bot shows a welcome screen with "Start Free Trial" and "How It Works" buttons
3. User taps "Start Free Trial" — trial begins, bot shows buttons: Join Private Group, Open WEEX Link, Verify My UID
4. User joins the private group through the bot's link
5. Bot sends automatic reminders during the trial (5 total — see below)
6. User taps "Verify My UID", pastes their WEEX UID as a plain number
7. Bot verifies the UID through WEEX API — if valid, user gets permanent access
8. If user does not verify before trial ends — bot removes them from the group
9. Removed users can still open the bot, verify their UID, and get a rejoin link

### Reminder Schedule (automatic)

- 1 hour after trial starts
- Day 2
- Day 5
- 24 hours before expiry
- 2 hours before expiry

Each reminder includes "Open WEEX Link" and "Verify My UID" buttons.

### What Was Disabled

- **Inactivity checking is fully removed.** The bot will not remove or flag users based on trading activity. Only unverified users are removed after trial expiry. This was disabled because the WEEX activity API had parsing/version issues and was causing false positives (verified users being flagged incorrectly).
- **INACTIVITY_DAYS and INACTIVITY_ACTION** settings are no longer used and can be removed from .env.

### Bugs Fixed

- **WEEX API error handling** — if the WEEX API is temporarily unavailable, the bot now shows "try again later" instead of rejecting the UID. Previously an API timeout would count as "UID not found".
- **All endpoints use WEEX API v3** — no more v2/v3 mismatch issues.
- **Verified users are fully protected** — they are never touched by the scheduler, never removed by mistake.
- **Duplicate UID prevention** works correctly across all flows.
- **Relay no longer intercepts verify input** — when a user is typing their UID, the message goes to verification, not to admin relay.

### UI Changes

- No slash commands required for regular users — everything is button-based
- All screens follow "one screen, one action" principle
- Users always have a clear next step with visible buttons

---

## Files to Replace

Replace ALL of these files on your server via FileZilla:

```
main.py
config.py
models.py
utils.py
weex_api.py
scheduler.py
handlers/commands.py
handlers/admin.py
handlers/group.py
handlers/relay.py
```

---

## New .env Variable

Add this line to your `.env` file:

```
GROUP_INVITE_LINK=https://t.me/+your_group_invite_link
```

This is the invite link to your private Telegram group. The bot gives this link to users after they start their trial. You can get it from your group settings — Invite Links.

You can also remove these lines from .env (no longer used):

```
INACTIVITY_DAYS=30
INACTIVITY_ACTION=flag
```

---

## Restart Command

Stop the current bot process:

```bash
ps aux | grep main.py
```

Find the process ID (second column) and kill it:

```bash
kill -9 <PID>
```

Start the bot again:

```bash
cd ~/shah-weex-bot
nohup .venv/bin/python main.py > /dev/null 2>&1 &
```

No database migration commands needed. The bot will update the database automatically on startup.

---

## Test Checklist

After replacing files, adding GROUP_INVITE_LINK to .env, and restarting:

- Open bot, tap /start — see welcome screen with 2 buttons
- Tap "How It Works" — see explanation, tap back to "Start Free Trial"
- Tap "Start Free Trial" — see trial started screen with 3 buttons (Join Group, Open WEEX, Verify)
- Tap "Join Private Group" — opens group invite link
- Tap "Verify My UID" — bot asks for UID
- Paste a valid WEEX UID — bot confirms verification
- Tap /start again after verification — see "verified, permanent access"
- Test with a new user who does NOT verify — after trial expires (TRIAL_DAYS), bot removes them from group
- After removal, user opens bot — sees "verify to rejoin" with buttons
- If removed user verifies — bot unbans them and shows "Rejoin Private Group" button
- Send a random message to bot (not during verify) — message is forwarded to admin
- Admin replies to forwarded message — reply is delivered back to user
- Run /stats — see clear stats with live group member count
- Run /users — see trial users with pagination
- Reminders are sent automatically during trial (check logs)
- Verified users are never removed or flagged

---

## Admin Commands (unchanged)

- `/stats` — group statistics with live member count
- `/status <user_id>` — detailed user info
- `/reset <user_id>` — reset user trial (new 7 days, unban)
- `/kick <user_id>` — manual remove
- `/users` — list trial users (paginated)
- `/users verified` — list verified users
- `/unflag <user_id|all>` — unflag users

