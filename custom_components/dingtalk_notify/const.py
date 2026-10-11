"""Constants for the DingTalk Notify integration.

This module must stay free of Home Assistant imports so every other module can
import from it without creating circular dependencies.

`NAME` and `VERSION` are loaded from `manifest.json` (same directory) at import
time. Bump the version in one place — manifest.json — and every module that
imports them picks up the new value automatically.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs, urlparse

DOMAIN: Final = "dingtalk_notify"

# --------------------------------------------------------------------------- #
# Name & version (single source of truth = manifest.json)
# --------------------------------------------------------------------------- #
try:
    _manifest_path = Path(__file__).parent / "manifest.json"
    with _manifest_path.open("r", encoding="utf-8") as _f:
        _manifest = json.load(_f)
    NAME: Final = _manifest.get("name") or "钉钉消息机器人"
    VERSION: Final = _manifest.get("version") or "0.0.0"
except Exception:  # pragma: no cover - defensive: manifest must always exist
    NAME = "钉钉消息机器人"
    VERSION = "0.0.0"

# --------------------------------------------------------------------------- #
# Config entry
# --------------------------------------------------------------------------- #
# The schema version of a config entry created by this version of the code.
CONFIG_ENTRY_VERSION: Final = 2
CONFIG_ENTRY_MINOR_VERSION: Final = 1

CONF_TOKEN: Final = "token"
CONF_SECRET: Final = "secret"

# Options (user tunables, stored in `ConfigEntry.options`).
CONF_TIMEOUT: Final = "timeout"
CONF_RETRY: Final = "retry"

DEFAULT_TIMEOUT: Final = 10
DEFAULT_RETRY: Final = 3
RETRY_BACKOFF: Final = 1.0

MIN_TIMEOUT: Final = 3
MAX_TIMEOUT: Final = 60
MIN_RETRY: Final = 0
MAX_RETRY: Final = 5

# --------------------------------------------------------------------------- #
# Device metadata
# --------------------------------------------------------------------------- #
MANUFACTURER: Final = "DingTalk"
MODEL: Final = "Custom robot webhook"

# --------------------------------------------------------------------------- #
# Extra attributes of the `dingtalk_notify.send_message` action.
#
# The standard `notify.send_message` action only carries `message` and `title`,
# so the DingTalk specific options need an action of their own.
# --------------------------------------------------------------------------- #
ATTR_AT_ALL: Final = "at_all"
ATTR_AT_MOBILES: Final = "at_mobiles"
ATTR_PIC_URL: Final = "pic_url"
ATTR_MESSAGE_URL: Final = "message_url"
ATTR_BUTTONS: Final = "buttons"
ATTR_BUTTON_LAYOUT: Final = "button_layout"
ATTR_SINGLE_TITLE: Final = "single_title"
ATTR_SINGLE_URL: Final = "single_url"


class MessageType(StrEnum):
    """A DingTalk message type.

    Every type is exposed as its own notify entity. The value doubles as the
    entity translation key, so it must stay snake_case.
    """

    TEXT = "text"
    MARKDOWN = "markdown"
    LINK = "link"
    ACTION_CARD = "action_card"


# The `msgtype` value the DingTalk API expects for each entity.
PAYLOAD_TYPE: Final[dict[MessageType, str]] = {
    MessageType.TEXT: "text",
    MessageType.MARKDOWN: "markdown",
    MessageType.LINK: "link",
    MessageType.ACTION_CARD: "actionCard",
}

# Message types as they were spelled by config entry version 1 ("actionCard").
LEGACY_MESSAGE_TYPES: Final[dict[str, MessageType]] = {
    "text": MessageType.TEXT,
    "markdown": MessageType.MARKDOWN,
    "link": MessageType.LINK,
    "actionCard": MessageType.ACTION_CARD,
}

WEBHOOK_PREFIX: Final = "https://oapi.dingtalk.com/robot/send"


def normalize_token(value: str) -> str:
    """Extract the access token from user input.

    The DingTalk console hands out a complete webhook URL, while the config flow
    asks for the token. Accepting both means users can paste whatever they have
    without having to dissect a URL first.
    """
    value = value.strip()
    if "access_token=" in value:
        query = urlparse(value).query or value
        if tokens := parse_qs(query).get("access_token"):
            return tokens[0].strip()
    return value


def short_token(token: str) -> str:
    """Return the last four characters of a token, for display purposes."""
    return token[-4:] if len(token) >= 4 else token
