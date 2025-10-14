"""Notify platform for DingTalk Notify."""
from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.notify import NotifyEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType
from .const import *

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 4 separate devices (always)."""
    client = hass.data[DOMAIN][entry.entry_id]
    suffix = short_token(entry.data[CONF_TOKEN])
    entities = []

    for msg_type in OPTION_MSG_TYPES:
        dev_ident = {(DOMAIN, f"{entry.entry_id}_{msg_type}")}
        device_name = f"{MANUFACTURER} - {MSG_TYPE_NAME[msg_type]} ({suffix})"
        dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers=dev_ident,
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type=DeviceEntryType.SERVICE,
            sw_version=entry.version,
        )
        entities.append(DingTalkNotifyEntity(entry, client, msg_type, suffix, dev_ident))

    async_add_entities(entities)

class DingTalkNotifyEntity(NotifyEntity):
    """DingTalk Notify Entity (1 per device)."""

    def __init__(self, entry: ConfigEntry, client, msg_type: str, suffix: str, dev_ident: set) -> None:
        self._entry = entry
        self._client = client
        self._msg_type = msg_type
        self._attr_unique_id = f"{suffix}_{msg_type}"
        self._attr_name = None
        self._attr_icon = {
            MSG_TEXT: "mdi:file-document-outline",
            MSG_MARKDOWN: "mdi:language-markdown",
            MSG_LINK: "mdi:link-variant",
            MSG_ACTIONCARD: "mdi:card-outline",
        }[msg_type]
        self._attr_device_info = {"identifiers": dev_ident}

    async def async_send_message(self, message: str, title: str | None = None, **kwargs) -> None:
        at = kwargs.get("data", {}).get("at", {"isAtAll": False})
        payload: dict = {"at": at}

        if self._msg_type == MSG_TEXT:
            payload.update({"msgtype": "text", "text": {"content": f"{title or ''}\n{message}".strip()}})
        elif self._msg_type == MSG_MARKDOWN:
            payload.update({"msgtype": "markdown", "markdown": {"title": title or "", "text": f"## {title or ''}\n\n{message}"}})
        elif self._msg_type == MSG_LINK:
            link_data = kwargs.get("data", {})
            payload.update({"msgtype": "link", "link": {"title": title or "", "text": message, "picUrl": link_data.get("picUrl", ""), "messageUrl": link_data.get("messageUrl", "")}})
        elif self._msg_type == MSG_ACTIONCARD:
            card_data = kwargs.get("data", {})
            payload.update({"msgtype": "actionCard", "actionCard": {"title": title or "", "text": message, "picUrl": card_data.get("picUrl", ""), "singleTitle": card_data.get("singleTitle", ""), "singleURL": card_data.get("singleURL", ""), "btnOrientation": card_data.get("btnOrientation", "0"), "btns": card_data.get("btns", [])}})

        await self._client.send(payload)