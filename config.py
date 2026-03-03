import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID = int(os.getenv("GROUP_ID", "0"))

WEEX_API_KEY = os.getenv("WEEX_API_KEY", "")
WEEX_API_SECRET = os.getenv("WEEX_API_SECRET", "")
WEEX_PASSPHRASE = os.getenv("WEEX_PASSPHRASE", "")
WEEX_BASE_URL = os.getenv("WEEX_BASE_URL", "https://api-spot.weex.com")
WEEX_REFERRAL_LINK = os.getenv("WEEX_REFERRAL_LINK", "")

TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))
INACTIVITY_DAYS = int(os.getenv("INACTIVITY_DAYS", "30"))
INACTIVITY_ACTION = os.getenv("INACTIVITY_ACTION", "flag")  # "ban" or "flag"
VERIFY_RATE_LIMIT = int(os.getenv("VERIFY_RATE_LIMIT", "5"))
TEST_MODE = os.getenv("TEST_MODE", "false").lower() in ("1", "true", "yes")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://data/db.sqlite3")

TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
