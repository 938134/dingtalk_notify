"""DingTalk network client."""
from __future__ import annotations
import logging
import aiohttp
import hmac
import hashlib
import base64
import time
import urllib.parse
from tenacity import retry, stop_after_attempt, wait_exponential
from .const import DEFAULT_TIMEOUT, RETRY_TIMES

_LOGGER = logging.getLogger(__name__)

class DingTalkClient:
    """DingTalk robot client."""

    def __init__(self, token: str, secret: str | None = None) -> None:
        self._token = token
        self._secret = secret
        self._session = aiohttp.ClientSession()

    def _sign(self) -> tuple[str, str]:
        ts = str(round(time.time() * 1000))
        if not self._secret:
            return ts, ""
        secret_enc = self._secret.encode()
        string_to_sign = f"{ts}\n{self._secret}"
        hmac_code = hmac.new(secret_enc, string_to_sign.encode(), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return ts, sign

    @retry(stop=stop_after_attempt(RETRY_TIMES), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def send(self, payload: dict) -> None:
        ts, sign = self._sign()
        url = f"https://oapi.dingtalk.com/robot/send?access_token={self._token}&timestamp={ts}&sign={sign}"
        async with self._session.post(url, json=payload, timeout=DEFAULT_TIMEOUT) as resp:
            data = await resp.json()
            if data.get("errcode"):
                _LOGGER.warning("DingTalk error: %s", data)

    async def close(self) -> None:
        await self._session.close()