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
    ts = str(int(time.time()))
    return {
        "ACCESS-KEY": WEEX_API_KEY,
        "ACCESS-SIGN": _sign(ts, method, path, body),
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": WEEX_PASSPHRASE,
        "Content-Type": "application/json",
        "locale": "en-US",
    }


async def get_affiliate_uids(page=1, page_size=100):
    path = f"/api/v2/rebate/affiliate/getAffiliateUIDs?pageNo={page}&pageSize={page_size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEEX_BASE_URL + path, headers=_headers("GET", path)) as resp:
                data = await resp.json()
                logger.debug(f"WEEX getAffiliateUIDs page={page}: code={data.get('code')}")
                return data
    except Exception as e:
        logger.error(f"WEEX API error (getAffiliateUIDs): {e}")
        return None


async def check_uid_in_referrals(weex_uid):
    """Check all pages of affiliate UIDs to find the given UID."""
    if TEST_MODE:
        logger.info(f"TEST_MODE: accepting UID {weex_uid} without API check")
        return True
    page = 1
    while True:
        data = await get_affiliate_uids(page=page)
        if not data or data.get("code") != "00000":
            return False
        items = data.get("data", {}).get("resultList", [])
        if not items:
            return False
        for item in items:
            if str(item.get("uid")) == str(weex_uid):
                return True
        total = int(data.get("data", {}).get("totalCount", 0))
        if page * 100 >= total:
            break
        page += 1
    return False


async def get_user_trade_data(weex_uid):
    path = f"/api/v2/rebate/affiliate/getChannelUserTradeAndAsset?uid={weex_uid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEEX_BASE_URL + path, headers=_headers("GET", path)) as resp:
                data = await resp.json()
                if data.get("code") == "00000":
                    return data.get("data")
                logger.warning(f"WEEX trade data error for UID {weex_uid}: {data}")
                return None
    except Exception as e:
        logger.error(f"WEEX API error (getChannelUserTradeAndAsset): {e}")
        return None


async def has_recent_activity(weex_uid, days=30):
    """
    Returns True (active), False (inactive), or None (API error).
    NOTE: adjust field parsing below to match actual WEEX API response structure.
    """
    if TEST_MODE:
        logger.debug(f"TEST_MODE: reporting UID {weex_uid} as active")
        return True
    data = await get_user_trade_data(weex_uid)
    if data is None:
        return None
    try:
        trade_vol = float(data.get("tradeVol", 0) or 0)
        return trade_vol > 0
    except (ValueError, TypeError):
        logger.warning(f"Could not parse trade data for UID {weex_uid}")
        return None
