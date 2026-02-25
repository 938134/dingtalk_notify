# __init__.py
"""The DingTalk Notify integration."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import *
from .dingtalk import DingTalkClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DingTalk Notify from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # 创建客户端
    client = DingTalkClient(entry.data[CONF_TOKEN], entry.data.get(CONF_SECRET))
    hass.data[DOMAIN][entry.entry_id] = client

    # 监听选项变更
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # 转发到 notify 平台
    await hass.config_entries.async_forward_entry_setups(entry, ["notify"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 先卸载平台
    await hass.config_entries.async_forward_entry_unload(entry, "notify")
    
    # 关闭客户端
    if entry.entry_id in hass.data[DOMAIN]:
        client: DingTalkClient = hass.data[DOMAIN].pop(entry.entry_id)
        await client.close()
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener for config entry changes."""
    _LOGGER.info("DingTalk configuration updated, reloading entry")
    await hass.config_entries.async_reload(entry.entry_id)