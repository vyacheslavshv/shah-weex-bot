import hmac
import hashlib
import base64
import time

import aiohttp
from loguru import logger

from config import WEEX_API_KEY, WEEX_API_SECRET, WEEX_PASSPHRASE, WEEX_BASE_URL, TEST_MODE


def _sign(timestamp, method, path, body=""):
    message = f"{timestamp}{method.upper()}{path}{body}"
    mac = hmac.new(WEEX_API_SECRET.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def _headers(method, path, body=""):
    ts = str(int(time.time() * 1000))
    return {
        "ACCESS-KEY": WEEX_API_KEY,
        "ACCESS-SIGN": _sign(ts, method, path, body),
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": WEEX_PASSPHRASE,
        "Content-Type": "application/json",
        "locale": "en-US",
    }


async def get_affiliate_uids(page=1, page_size=100):
    """Fetch affiliate UIDs from WEEX V3 API. Returns parsed JSON or None on error."""
    path = f"/api/v3/rebate/affiliate/getAffiliateUIDs?page={page}&pageSize={page_size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEEX_BASE_URL + path, headers=_headers("GET", path)) as resp:
                data = await resp.json(content_type=None)
                logger.debug(f"WEEX getAffiliateUIDs page={page}: total={data.get('total')}")
                return data
    except Exception as e:
        logger.error(f"WEEX API error (getAffiliateUIDs): {e}")
        return None


async def check_uid_in_referrals(weex_uid):
    """
    Check if a WEEX UID is in the affiliate referral list.
    Returns True (found), False (not found), or None (API error).
    """
    if TEST_MODE:
        logger.info(f"TEST_MODE: accepting UID {weex_uid} without API check")
        return True
    page = 1
    while True:
        data = await get_affiliate_uids(page=page)
        if data is None:
            logger.warning(f"WEEX API returned None for page {page} — treating as API error")
            return None
        items = data.get("channelUserInfoItemList", [])
        if not items:
            return False
        for item in items:
            if str(item.get("uid")) == str(weex_uid):
                return True
        total = int(data.get("total", 0))
        pages = int(data.get("pages", 1))
        if page >= pages:
            break
        page += 1
    return False
