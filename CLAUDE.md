# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot for WEEX cryptocurrency exchange affiliate trial funnel. **Bot-first flow**: users start with the bot (not the group), get a 7-day trial, receive a group invite link, and must verify their WEEX account via button-based UI to retain access. Background jobs handle trial expiry and reminders.

## Running the Bot

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in values

# Database migrations
aerich upgrade

# Run directly
python main.py

# Production management (uses nohup + PID file)
./bot.sh start|stop|restart|status|logs|update
```

**TEST_MODE=true** in `.env` bypasses WEEX API calls — all UID verifications return success. Use for local testing without affiliate API access.

## Architecture

**Framework:** aiogram 3.0+ (async Telegram bot framework) with Tortoise ORM (async, SQLite), APScheduler, and aiogram FSM for verify flow state.

**Entry point:** `main.py` — initializes DB, registers routers, starts scheduler, begins polling. `allowed_updates` includes `callback_query`.

### Handler Router Order (matters — evaluated sequentially)

Defined in `handlers/__init__.py`:
1. **`handlers/group.py`** — Chat join requests and member updates (auto-approve trial/verified, decline kicked)
2. **`handlers/commands.py`** — /start, /help, /verify fallback, all callback query handlers (start_trial, how_it_works, verify_uid, cancel_verify), and FSM state handler for UID input
3. **`handlers/admin.py`** — Admin commands (filtered by `ADMIN_ID`): /stats, /status, /reset, /kick, /users, /unflag
4. **`handlers/relay.py`** — DM relay between users and admin (catch-all with `StateFilter(None)`, must stay last)

### User Flow (Bot-First)

1. User opens bot → Welcome screen with "Start Free Trial" / "How It Works" buttons
2. "Start Free Trial" → creates user record, shows group invite link + WEEX link
3. User joins group → auto-approved by group handler
4. Reminders sent at: 1h, day 2, day 5, 24h before expiry, 2h before expiry
5. "Verify My UID" → FSM sets `awaiting_uid` state → user pastes UID → bot verifies via WEEX API
6. Verified → permanent access. Unverified after trial → kicked, but can still verify and rejoin.

### Core Modules

- **`config.py`** — All settings from `.env`. Key vars: `BOT_TOKEN`, `ADMIN_ID`, `GROUP_ID`, `GROUP_INVITE_LINK`, `WEEX_API_KEY/SECRET/PASSPHRASE`, `TRIAL_DAYS` (default 7), `TEST_MODE`.
- **`models.py`** — Tortoise ORM: `User` (telegram_id, status, weex_uid, join_time, verified_time, verify_attempts, bot_started, last_reminder) and `RelayMessage`.
- **`weex_api.py`** — WEEX V3 affiliate API with HMAC-SHA256 signing. `check_uid_in_referrals()` returns `True`/`False`/`None` (None = API error, don't punish user).
- **`scheduler.py`** — `check_trial_expiry()` (hourly) and `send_reminders()` (hourly). Inactivity logic is disabled.
- **`utils.py`** — Loguru setup + DB init with safe migration for `last_reminder` column.

### User Status Flow

`trial` → (verify) → `verified`
`trial` → (expiry) → `kicked` → (verify later) → `verified` + unban + rejoin link

### Key Patterns

- **Button-based UI** — InlineKeyboardMarkup everywhere, no slash commands for regular users.
- **FSM for verify** — `VerifyState.awaiting_uid` state captures next message as UID. Relay handler uses `StateFilter(None)` to avoid catching UID input.
- **API error safety** — `check_uid_in_referrals` returns None on API failure; bot shows retry message instead of rejecting.
- **Reminder tracking** — `last_reminder` integer field (1-5) ensures each reminder sent once, survives restarts.

## Database

SQLite at `data/db.sqlite3`. `init_db()` auto-adds `last_reminder` column via ALTER TABLE for existing DBs. For new installs, `generate_schemas(safe=True)` handles everything.
