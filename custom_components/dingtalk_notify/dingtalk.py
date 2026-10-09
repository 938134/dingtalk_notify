"""Client for the DingTalk custom robot webhook.

The client deliberately re-uses Home Assistant's shared aiohttp session:

* no session is leaked when an entry is reloaded,
* the user's proxy / SSL settings configured in Home Assistant are honoured,
* connections are pooled and closed by Home Assistant itself.
"""

from __future__ import annotations

import asyncio
from base64 import b64encode
import hashlib
import hmac
from http import HTTPStatus
import logging
import time
from typing import Any
from urllib.parse import quote_plus

from aiohttp import ClientError, ClientSession, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
 
from .const import (
    DEFAULT_RETRY,
    DEFAULT_TIMEOUT,
    DOMAIN,
    RETRY_BACKOFF,
    WEBHOOK_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

SUCCESS_CODE = 0


class DingTalkError(HomeAssistantError):
    """Base class for errors raised by this integration."""


class DingTalkConnectionError(DingTalkError):
    """Raised when the webhook could not be reached."""


class DingTalkResponseError(DingTalkError):
    """Raised when DingTalk accepted the request but rejected the message."""


class DingTalkClient:
    """Send messages to one DingTalk custom robot."""

    def __init__(
        self,
        hass: HomeAssistant,
        token: str,
        secret: str | None = None,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRY,
    ) -> None:
        """Initialize the client."""
        self._session: ClientSession = async_get_clientsession(hass)
        self._token = token
        self._secret = secret or None
        self._timeout = ClientTimeout(total=timeout)
        self._retries = max(retries, 0)

    def _build_url(self) -> str:
        """Return the signed webhook URL.

        The signature follows DingTalk's documented scheme: the timestamp and
        the secret are joined with a newline, HMAC-SHA256 signed with the
        secret, base64 encoded and form-urlencoded.
        """
        timestamp = str(round(time.time() * 1000))
        if self._secret is None:
            return f"{WEBHOOK_PREFIX}?access_token={self._token}&timestamp={timestamp}"

        digest = hmac.new(
            self._secret.encode(),
            f"{timestamp}\n{self._secret}".encode(),
            digestmod=hashlib.sha256,
        ).digest()
        sign = quote_plus(b64encode(digest).decode())
        return (
            f"{WEBHOOK_PREFIX}?access_token={self._token}"
            f"&timestamp={timestamp}&sign={sign}"
        )

    async def async_send(self, payload: dict[str, Any]) -> None:
        """Post a message payload, retrying transient failures.

        Transport failures and HTTP 5xx responses are retried with a linear
        backoff. Anything DingTalk itself rejects (non-zero `errcode`, HTTP 4xx)
        is reported immediately, because resending it would not help and would
        risk posting the same message twice.
        """
        url = self._build_url()

        for attempt in range(self._retries + 1):
            if attempt:
                await asyncio.sleep(RETRY_BACKOFF * attempt)
                _LOGGER.debug(
                    "Retrying DingTalk webhook request (attempt %s/%s)",
                    attempt + 1,
                    self._retries + 1,
                )

            try:
                async with self._session.post(
                    url, json=payload, timeout=self._timeout
                ) as response:
                    status = response.status
                    try:
                        body = await response.json(content_type=None)
                    except ValueError:
                        # Not JSON at all (an HTML error page, for example).
                        # Reported below as an unexpected response instead of
                        # leaking a raw JSONDecodeError to the caller.
                        body = None
            except (ClientError, TimeoutError) as err:
                if attempt == self._retries:
                    raise DingTalkConnectionError(
                        f"Unable to reach the DingTalk webhook: {err}",
                        translation_domain=DOMAIN,
                        translation_key="cannot_connect",
                        translation_placeholders={"error": str(err)},
                    ) from err
                continue

            if status >= HTTPStatus.INTERNAL_SERVER_ERROR:
                if attempt == self._retries:
                    raise DingTalkConnectionError(
                        f"The DingTalk webhook returned HTTP {status}",
                        translation_domain=DOMAIN,
                        translation_key="http_error",
                        translation_placeholders={"status": str(status)},
                    )
                continue

            if status >= HTTPStatus.BAD_REQUEST:
                raise DingTalkResponseError(
                    f"The DingTalk webhook returned HTTP {status}",
                    translation_domain=DOMAIN,
                    translation_key="http_error",
                    translation_placeholders={"status": str(status)},
                )

            if not isinstance(body, dict):
                raise DingTalkResponseError(
                    "The DingTalk webhook returned an unexpected response",
                    translation_domain=DOMAIN,
                    translation_key="unexpected_response",
                )

            if (errcode := body.get("errcode", SUCCESS_CODE)) != SUCCESS_CODE:
                errmsg = body.get("errmsg") or ""
                raise DingTalkResponseError(
                    f"DingTalk rejected the message ({errcode}): {errmsg}",
                    translation_domain=DOMAIN,
                    translation_key="api_error",
                    translation_placeholders={
                        "code": str(errcode),
                        "message": errmsg,
                    },
                )

            _LOGGER.debug("DingTalk message delivered")
            return
