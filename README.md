# WEEX Affiliate Trial Bot

Telegram bot for managing a WEEX affiliate trial funnel with automatic verification and chat relay.

## How it works

1. User clicks your group invite link (with admin approval enabled)
2. Bot auto-approves and sends a welcome DM with trial info + your WEEX referral link
3. User registers on WEEX, gets their UID, sends `/verify <UID>` to the bot
4. Bot checks the WEEX affiliate API — if UID is found, user gets permanent access
5. If trial expires (default 7 days) without verification — auto-kick
6. Verified users with no trading activity for 30+ days — flagged or kicked (configurable)
7. Users can DM the bot — messages are forwarded to you. Reply to answer them.

## Server setup (first time)

Run these commands one by one on your Linux server:

```bash
# 1. Install required packages
sudo apt update && sudo apt install -y git python3 python3-venv

# 2. Download the bot
cd /home
git clone https://github.com/vyacheslavshv/shah-weex-bot.git
cd shah-weex-bot

# 3. Create virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. Create your config file
cp .env.example .env
nano .env
```

In `nano`, fill in your values (see the table below). When done: **Ctrl+O** → Enter to save, **Ctrl+X** to exit.

```bash
# 5. Test the bot (Ctrl+C to stop)
.venv/bin/python main.py

# 6. If everything works, start in background
./bot.sh start
```

## .env configuration

| Variable | What to put |
|---|---|
| `BOT_TOKEN` | Token from @BotFather |
| `ADMIN_ID` | Your Telegram user ID (number). Get it from @userinfobot |
| `GROUP_ID` | Your group ID (number, starts with -100). Get it from @userinfobot in the group |
| `WEEX_API_KEY` | Your WEEX API key (from affiliates.weex.com → API settings) |
| `WEEX_API_SECRET` | Your WEEX API secret |
| `WEEX_PASSPHRASE` | Your WEEX API passphrase |
| `WEEX_REFERRAL_LINK` | Your WEEX referral link, e.g. `https://www.weex.com/en/register?vipCode=fsyz` |
| `TRIAL_DAYS` | Trial period in days (default: 7) |
| `INACTIVITY_DAYS` | Days without trading before action (default: 30) |
| `INACTIVITY_ACTION` | `flag` (notify you) or `ban` (auto-kick inactive users) |

## Managing the bot

```bash
./bot.sh start     # Start the bot in background
./bot.sh stop      # Stop the bot
./bot.sh restart   # Restart the bot
./bot.sh status    # Check if the bot is running
./bot.sh logs      # View live logs (Ctrl+C to exit)
./bot.sh update    # Pull latest code + restart (for updates)
```

## Updating the bot

When I push an update, run:

```bash
cd /home/shah-weex-bot
./bot.sh update
```

This pulls the new code, installs any new dependencies, and restarts the bot. Your `.env` settings are preserved.

## Telegram group setup

1. Create a bot via @BotFather, get the token
2. Add the bot to your group as **admin** (needs permissions: ban users, invite users)
3. In group settings → Invite Links → create a link with **"Request admin approval"** enabled
4. Share this invite link with users (not a regular link — must be the one with approval)

## Bot commands

**User commands** (private chat with bot):
- `/start` — show trial status
- `/verify <weex_uid>` — verify WEEX account
- `/help` — list commands

**Admin commands** (private chat with bot):
- `/stats` — group statistics
- `/status <user_id>` — check user info
- `/reset <user_id>` — reset trial (unban + new trial)
- `/kick <user_id>` — manual kick/ban
- `/users` — list trial users
- `/unflag <user_id>` — set a flagged user back to verified
- `/unflag all` — unflag all flagged users at once

**Chat relay**: users DM the bot, you receive forwarded messages. Reply to a forwarded message to respond.

## Project structure

```
├── main.py           # Entry point
├── config.py         # Environment variables
├── models.py         # Database models (User, RelayMessage)
├── utils.py          # Logging, DB init
├── weex_api.py       # WEEX affiliate API client
├── scheduler.py      # Trial expiry + inactivity checks
├── bot.sh            # Start/stop/restart/update script
├── handlers/
│   ├── group.py      # Group join events
│   ├── commands.py   # /start, /verify, /help
│   ├── admin.py      # Admin commands
│   └── relay.py      # DM relay
├── .env.example      # Config template
└── requirements.txt
```
