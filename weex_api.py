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
    if TEST_MODE:
        logger.info(f"TEST_MODE: accepting UID {weex_uid} without API check")
        return True
    page = 1
    while True:
        data = await get_affiliate_uids(page=page)
        if not data:
            return False
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


async def get_user_trade_data(weex_uid, start_time=None, end_time=None):
    params = f"uid={weex_uid}"
    if start_time:
        params += f"&startTime={start_time}"
    if end_time:
        params += f"&endTime={end_time}"
    path = f"/api/v3/rebate/affiliate/getChannelUserTradeAndAsset?{params}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEEX_BASE_URL + path, headers=_headers("GET", path)) as resp:
                data = await resp.json(content_type=None)
                records = data.get("records", [])
                if records:
                    return records[0]
                return None
    except Exception as e:
        logger.error(f"WEEX API error (getChannelUserTradeAndAsset): {e}")
        return None


async def has_recent_activity(weex_uid, days=30):
    """
    Check if user traded in the last `days` days.
    Returns True (active), False (inactive), or None (API error).
    """
    if TEST_MODE:
        logger.debug(f"TEST_MODE: reporting UID {weex_uid} as active")
        return True
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (days * 86400 * 1000)
    record = await get_user_trade_data(weex_uid, start_time=start_ms, end_time=now_ms)
    if record is None:
        return None
    try:
        spot = float(record.get("spotTradingAmount", 0) or 0)
        futures = float(record.get("futuresTradingAmount", 0) or 0)
        return (spot + futures) > 0
    except (ValueError, TypeError):
        logger.warning(f"Could not parse trade data for UID {weex_uid}")
        return None
