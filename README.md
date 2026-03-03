# WEEX Affiliate Trial Bot

Telegram bot for managing a WEEX affiliate trial funnel with automatic verification and chat relay.

## How it works

1. User joins the Telegram group
2. Bot sends a DM with trial info and referral link (7-day trial by default)
3. User registers on WEEX via the referral link and gets a UID
4. User sends `/verify <UID>` to the bot — bot checks the WEEX affiliate API
5. If UID is found under the referral tree → permanent access
6. If trial expires without verification → auto-kick (hourly check)
7. Verified users with no trading activity for 30+ days → flagged or kicked (daily check)

Chat relay: users DM the bot, messages are forwarded to the admin. Admin replies by replying to the forwarded message.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with your values

aerich init-db
python main.py
```

## Configuration (.env)

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `ADMIN_ID` | Your Telegram user ID (numeric) |
| `GROUP_ID` | Target group/supergroup ID (numeric, starts with -100) |
| `WEEX_API_KEY` | WEEX API key |
| `WEEX_API_SECRET` | WEEX API secret |
| `WEEX_PASSPHRASE` | WEEX API passphrase |
| `WEEX_BASE_URL` | WEEX API base URL (default: `https://api.weex.com`) |
| `WEEX_REFERRAL_LINK` | Your WEEX referral registration link |
| `TRIAL_DAYS` | Trial period in days (default: 7) |
| `INACTIVITY_DAYS` | Days without trading before action (default: 30) |
| `INACTIVITY_ACTION` | `flag` (notify admin) or `ban` (auto-kick) |
| `VERIFY_RATE_LIMIT` | Max /verify attempts per hour (default: 5) |

## Bot commands

### User commands (private chat)
- `/start` — show trial status and instructions
- `/verify <weex_uid>` — verify WEEX account
- `/help` — list commands

### Admin commands (private chat)
- `/stats` — group statistics
- `/status <user_id>` — detailed user info
- `/reset <user_id>` — reset trial (unban + new trial period)
- `/kick <user_id>` — manual kick/ban
- `/users` — list all trial users with days remaining

### Chat relay
- Users send any message to the bot → forwarded to admin
- Admin replies to the forwarded message → delivered back to the user

## Project structure

```
├── main.py           # Entry point
├── config.py         # Environment variables
├── models.py         # Database models (User, RelayMessage)
├── utils.py          # Logging setup, DB init
├── weex_api.py       # WEEX affiliate API client
├── scheduler.py      # Periodic jobs (trial expiry, inactivity)
├── handlers/
│   ├── __init__.py   # Router registration
│   ├── group.py      # Group join/leave events
│   ├── commands.py   # /start, /verify, /help
│   ├── admin.py      # Admin commands
│   └── relay.py      # DM relay
├── requirements.txt
├── .env.example
└── pyproject.toml    # Aerich config
```

## Database migrations

Uses Tortoise ORM + Aerich.

```bash
# first time
aerich init-db

# after model changes
aerich migrate
aerich upgrade
```

## Notes

- The bot must be an **admin** in the target group to receive join events and kick members.
- After joining the group, the bot sends 1 welcome DM. For continued messaging, the user must press `/start` in the bot's private chat.
- Re-joining the group does **not** reset the trial. Only `/reset` by admin does.
- One Telegram account can only be linked to one WEEX UID (enforced).
- WEEX API signature follows the Bitget-style HMAC-SHA256 pattern. Adjust `weex_api.py` if the actual API differs.
