"""Notify platform for DingTalk Notify."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DingTalkConfigEntry
from .const import (
    ATTR_AT_ALL,
    ATTR_AT_MOBILES,
    ATTR_BUTTON_LAYOUT,
    ATTR_BUTTONS,
    ATTR_MESSAGE_URL,
    ATTR_PIC_URL,
    ATTR_SINGLE_TITLE,
    ATTR_SINGLE_URL,
    DOMAIN,
    PAYLOAD_TYPE,
    MessageType,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DingTalkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the notify entities of one robot."""
    async_add_entities( 
        DingTalkNotifyEntity(entry, msg_type) for msg_type in MessageType
    )


class DingTalkNotifyEntity(NotifyEntity):
    """Send messages through one DingTalk custom robot.

    One entity per message type, all grouped under a single device. The entity
    names come from the translation keys (`text`, `markdown`, `link`,
    `action_card`) and are prefixed with the device name.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, entry: DingTalkConfigEntry, msg_type: MessageType) -> None:
        """Initialize the entity."""
        self._client = entry.runtime_data.client
        self._msg_type = msg_type
        self._attr_unique_id = f"{entry.entry_id}_{msg_type.value}"
        self._attr_translation_key = msg_type.value
        self._attr_device_info = entry.runtime_data.device_info

    @override
    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
        **options: Any,
    ) -> None:
        """Send a message.

        Reached from two directions:

        * `notify.send_message`, which passes `message` and `title` only, and
        * `dingtalk_notify.send_message`, which additionally passes the
          DingTalk specific options declared in `SEND_MESSAGE_SCHEMA`.
        """
        await self._client.async_send(self._build_payload(message, title, options))

    def _build_payload(
        self,
        message: str,
        title: str | None,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the DingTalk payload for this entity's message type.

        Options that do not apply to the entity's message type are ignored, so
        one automation can target several entities of the same robot.
        """
        msg_type = self._msg_type
        payload: dict[str, Any] = {
            "msgtype": PAYLOAD_TYPE[msg_type],
            "at": {
                "isAtAll": bool(options.get(ATTR_AT_ALL, False)),
                "atMobiles": list(options.get(ATTR_AT_MOBILES) or []),
            },
        }

        if msg_type is MessageType.TEXT:
            payload["text"] = {
                "content": f"{title}\n{message}" if title else message,
            }

        elif msg_type is MessageType.MARKDOWN:
            # `title` is shown in the notification preview, `text` is the body.
            # The body additionally carries the title as a second level heading.
            # DingTalk does not add it by itself, and dropping it would silently
            # change the rendering of every existing markdown automation, so the
            # prefix is kept even though it duplicates the preview title.
            payload["markdown"] = {
                "title": title or "",
                "text": f"## {title or ''}\n\n{message}",
            }

        elif msg_type is MessageType.LINK:
            if not (message_url := options.get(ATTR_MESSAGE_URL)):
                raise ServiceValidationError(
                    "A DingTalk link message requires a message URL",
                    translation_domain=DOMAIN,
                    translation_key="link_url_required",
                )
            payload["link"] = {
                "title": title or "",
                "text": message,
                "picUrl": options.get(ATTR_PIC_URL) or "",
                "messageUrl": message_url,
            }

        else:  # MessageType.ACTION_CARD
            buttons = list(options.get(ATTR_BUTTONS) or [])
            single_title = options.get(ATTR_SINGLE_TITLE)
            single_url = options.get(ATTR_SINGLE_URL)
            if not buttons and not (single_title and single_url):
                raise ServiceValidationError(
                    "A DingTalk action card requires buttons, or a single button",
                    translation_domain=DOMAIN,
                    translation_key="card_action_required",
                )
            payload["actionCard"] = {
                "title": title or "",
                "text": message,
                "picUrl": options.get(ATTR_PIC_URL) or "",
                "btnOrientation": options.get(ATTR_BUTTON_LAYOUT, "0"),
                "btns": buttons,
                "singleTitle": single_title or "",
                "singleURL": single_url or "",
            }

        return payload
