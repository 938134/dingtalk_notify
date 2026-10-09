"""The DingTalk Notify integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Final

import voluptuous as vol

from homeassistant import loader
from homeassistant.components.notify import ATTR_MESSAGE, ATTR_TITLE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    selector,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.service import (
    async_register_platform_entity_service,
    async_set_service_schema,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_AT_ALL,
    ATTR_AT_MOBILES,
    ATTR_BUTTON_LAYOUT,
    ATTR_BUTTONS,
    ATTR_MESSAGE_URL,
    ATTR_PIC_URL,
    ATTR_SINGLE_TITLE,
    ATTR_SINGLE_URL,
    CONF_RETRY,
    CONF_SECRET,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONFIG_ENTRY_VERSION,
    DEFAULT_RETRY,
    DEFAULT_TIMEOUT,
    DOMAIN,
    LEGACY_MESSAGE_TYPES,
    MANUFACTURER,
    MODEL,
    short_token,
)
from .dingtalk import DingTalkClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.NOTIFY]

LEGACY_CONFIG_ENTRY_VERSION = 1


@dataclass
class DingTalkData:
    """Runtime data of a DingTalk Notify config entry."""

    client: DingTalkClient
    device_info: DeviceInfo


# Typed config entry: `entry.runtime_data` is a `DingTalkData`.
type DingTalkConfigEntry = ConfigEntry[DingTalkData]


# --------------------------------------------------------------------------- #
# The `dingtalk_notify.send_message` action
#
# `notify.send_message` only accepts `message` and `title`, which is not enough
# to drive DingTalk's `link` and `actionCard` messages (they need a URL and
# buttons). This action carries those extra options.
#
# The integration deliberately ships no `services.yaml`. Home Assistant has no
# way to put the *shape* of an action (its selectors and target) into the
# translation files - those only carry strings - so the description is
# registered from here with `async_set_service_schema` instead, the public
# helper Core's own `script` integration uses for the same job. It normalises
# `target` exactly as a `services.yaml` would, and `selector.validate_selector`
# below normalises the selectors the same way, so the UI is identical. All the
# human readable text still lives in `translations/*.json`.
# --------------------------------------------------------------------------- #
SERVICE_SEND_MESSAGE = "send_message"

# Keys of the button dictionaries accepted by `buttons`.
ATTR_BUTTON_TITLE = "title"
ATTR_BUTTON_URL = "url"

SEND_MESSAGE_SCHEMA: dict[vol.Marker, Any] = {
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_AT_ALL, default=False): cv.boolean,
    vol.Optional(ATTR_AT_MOBILES, default=list): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_PIC_URL): cv.string,
    vol.Optional(ATTR_MESSAGE_URL): cv.string,
    vol.Optional(ATTR_BUTTONS, default=list): vol.All(
        cv.ensure_list,
        [
            vol.Schema(
                {
                    vol.Required(ATTR_BUTTON_TITLE): cv.string,
                    vol.Required(ATTR_BUTTON_URL): cv.string,
                }
            )
        ],
    ),
    vol.Optional(ATTR_BUTTON_LAYOUT, default="0"): vol.In(["0", "1"]),
    vol.Optional(ATTR_SINGLE_TITLE): cv.string,
    vol.Optional(ATTR_SINGLE_URL): cv.string,
}


# The selector of a plain single line text field, normalised once and reused.
_TEXT: Final = selector.validate_selector({"text": None})

# UI description of the action, the equivalent of a `services.yaml`. Each
# selector is run through `selector.validate_selector` so the frontend receives
# exactly the configuration it would have received from a YAML file.
SEND_MESSAGE_DESCRIPTION: Final[dict[str, Any]] = {
    "fields": {
        ATTR_MESSAGE: {
            "required": True,
            "selector": selector.validate_selector({"text": {"multiline": True}}),
        },
        ATTR_TITLE: {"selector": _TEXT},
        ATTR_AT_ALL: {"selector": selector.validate_selector({"boolean": None})},
        ATTR_AT_MOBILES: {
            "selector": selector.validate_selector({"text": {"multiple": True}}),
        },
        ATTR_PIC_URL: {"selector": _TEXT},
        ATTR_MESSAGE_URL: {"selector": _TEXT},
        ATTR_BUTTONS: {
            "selector": selector.validate_selector(
                {
                    "object": {
                        "multiple": True,
                        "label_field": ATTR_BUTTON_TITLE,
                        "fields": {
                            ATTR_BUTTON_TITLE: {
                                "required": True,
                                "selector": _TEXT,
                            },
                            ATTR_BUTTON_URL: {
                                "required": True,
                                "selector": _TEXT,
                            },
                        },
                    }
                }
            )
        },
        ATTR_BUTTON_LAYOUT: {
            # The labels come from the `selector` section of the translations.
            "selector": selector.validate_selector(
                {
                    "select": {
                        "translation_key": ATTR_BUTTON_LAYOUT,
                        "options": ["0", "1"],
                    }
                }
            )
        },
        ATTR_SINGLE_TITLE: {"selector": _TEXT},
        ATTR_SINGLE_URL: {"selector": _TEXT},
    },
    "target": {"entity": {"domain": Platform.NOTIFY.value}},
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration.

    The action is registered here rather than in `async_setup_entry` so it
    always exists: automations referencing it can be validated even when no
    config entry is loaded. The schema is handed over as a plain mapping,
    `async_register_platform_entity_service` wraps it in
    `cv.make_entity_service_schema` and resolves `entity_id` for us.
    """
    async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        entity_domain=Platform.NOTIFY,
        schema=SEND_MESSAGE_SCHEMA,
        func="async_send_message",
    )
    # Describe the action for the frontend. Registering it here means the
    # description is in place before the frontend asks for it, and it also
    # keeps the integration out of `async_get_all_descriptions`' "missing
    # services.yaml" path entirely.
    async_set_service_schema(
        hass, DOMAIN, SERVICE_SEND_MESSAGE, SEND_MESSAGE_DESCRIPTION
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DingTalkConfigEntry) -> bool:
    """Set up DingTalk Notify from a config entry."""
    options = entry.options
    client = DingTalkClient(
        hass,
        token=entry.data[CONF_TOKEN],
        secret=entry.data.get(CONF_SECRET),
        timeout=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        retries=options.get(CONF_RETRY, DEFAULT_RETRY),
    )

    integration = await loader.async_get_integration(hass, DOMAIN)
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=MODEL,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://github.com/938134/dingtalk_notify",
    )
    # `sw_version` has to be a plain `str`. `integration.version` is an
    # `AwesomeVersion`, and `AwesomeVersion` subclasses `str`, so it slips past
    # the device registry's `isinstance(value, str)` guard and only raises
    # later, when the registry compares it against a device whose `sw_version`
    # is still `None`:
    #     AwesomeVersion.__ne__(None) -> _ensure_awesome_version(None)
    #     -> AwesomeVersionCompareException: Not a valid AwesomeVersion object
    # The field is left out entirely when the manifest carries no version, so
    # nothing is ever compared against `None`.
    if integration.version is not None:
        device_info["sw_version"] = str(integration.version)

    entry.runtime_data = DingTalkData(client=client, device_info=device_info)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DingTalkConfigEntry) -> bool:
    """Unload a config entry.

    Nothing else needs cleaning up: the aiohttp session belongs to Home
    Assistant and `runtime_data` is discarded with the entry.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry created by an older version of the integration."""
    if entry.version > CONFIG_ENTRY_VERSION:
        # The entry was created by a newer version than the one running now.
        _LOGGER.error(
            "Cannot migrate %s from version %s, this integration supports up to"
            " version %s",
            entry.title,
            entry.version,
            CONFIG_ENTRY_VERSION,
        )
        return False

    if entry.version == LEGACY_CONFIG_ENTRY_VERSION:
        _async_migrate_v1_to_v2(hass, entry)

    return True


def _async_migrate_v1_to_v2(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Rewrite registries created by version 1.

    Version 1 derived entity unique IDs from the last four characters of the
    access token and created one device per message type. Two robots whose
    tokens share a suffix therefore collided, and rotating the token orphaned
    every entity. Version 2 keys both registries off the config entry ID and
    uses a single device per robot.
    """
    legacy_suffix = short_token(entry.data[CONF_TOKEN])

    entity_registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if reg_entry.domain != Platform.NOTIFY:
            continue
        for legacy_type, msg_type in LEGACY_MESSAGE_TYPES.items():
            if reg_entry.unique_id != f"{legacy_suffix}_{legacy_type}":
                continue
            try:
                entity_registry.async_update_entity(
                    reg_entry.entity_id,
                    new_unique_id=f"{entry.entry_id}_{msg_type.value}",
                )
            except ValueError:
                # The target unique ID is already taken; keeping the entity as
                # it is, is better than failing the whole migration.
                _LOGGER.warning(
                    "Could not migrate unique ID of %s, target already exists",
                    reg_entry.entity_id,
                )
            break

    device_registry = dr.async_get(hass)
    for legacy_type in LEGACY_MESSAGE_TYPES:
        legacy_device = device_registry.async_get_device(
            identifiers={(DOMAIN, f"{entry.entry_id}_{legacy_type}")}
        )
        if legacy_device is not None:
            device_registry.async_remove_device(legacy_device.id)

    hass.config_entries.async_update_entry(entry, version=CONFIG_ENTRY_VERSION)
    _LOGGER.debug("Migrated %s to version %s", entry.title, CONFIG_ENTRY_VERSION)
