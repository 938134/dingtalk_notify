from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client, device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
import logging

from .const import (
    DOMAIN,
    SERVICE_SEND_TEXT,
    SERVICE_SEND_MARKDOWN,
    SERVICE_SEND_LINK,
    SERVICE_SEND_ACTIONCARD,
    CONF_TOKEN,
    CONF_SECRET,
)
from .dingtalk import DingTalkNotify

_LOGGER = logging.getLogger(__name__)

# 定义每种消息类型的服务参数验证模式
SEND_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Exclusive("isAtAll", "at"): cv.boolean,
        vol.Exclusive("atMobiles", "at"): vol.All(cv.ensure_list, [cv.string]),
    }
)

SEND_MARKDOWN_SCHEMA = vol.Schema(
    {
        vol.Optional("title", default="消息标题"): cv.string,
        vol.Required("message"): cv.string,
        vol.Optional("picUrl", default=""): cv.string,
        vol.Exclusive("isAtAll", "at"): cv.boolean,
        vol.Exclusive("atMobiles", "at"): vol.All(cv.ensure_list, [cv.string]),
    }
)

SEND_LINK_SCHEMA = vol.Schema(
    {
        vol.Optional("title", default=""): cv.string,
        vol.Required("message"): cv.string,
        vol.Optional("picurl", default=""): cv.string,
        vol.Optional("messageurl", default=""): cv.string,
        vol.Exclusive("isAtAll", "at"): cv.boolean,
        vol.Exclusive("atMobiles", "at"): vol.All(cv.ensure_list, [cv.string]),
    }
)

SEND_ACTIONCARD_SCHEMA = vol.Schema(
    {
        vol.Optional("title", default=""): cv.string,
        vol.Required("message"): cv.string,
        vol.Optional("picurl", default=""): cv.string,
        vol.Optional("singleTitle", default=""): cv.string,
        vol.Optional("singleURL", default=""): cv.string,
        vol.Optional("btnOrientation", default="0"): cv.string,
        vol.Optional("btns", default=[]): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("title"): cv.string,
                        vol.Required("actionURL"): cv.string,
                    }
                )
            ],
        ),
        vol.Exclusive("isAtAll", "at"): cv.boolean,
        vol.Exclusive("atMobiles", "at"): vol.All(cv.ensure_list, [cv.string]),
    }
)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the DingTalk component."""
    hass.data.setdefault(DOMAIN, {
        'service_counter': 0,
        'entries': {}
    })
    return True

def _format_markdown_message(title: str, message: str, picurl: str) -> str:
    """格式化 Markdown 消息内容"""
    formatted_title = f"# 【{title}】"
    if picurl:
        return (
            f"![screenshot]({picurl})\n\n"
            f"{formatted_title}\n\n"
            f"{message.replace('\n', '  \n')}"
        )
    else:
        return (
            f"{formatted_title}\n\n"
            f"{message.replace('\n', '  \n')}"
        )

def process_at_params(call: ServiceCall) -> dict:
    """处理 at 参数并返回 at 配置字典。"""
    return {
        "atMobiles": call.data.get("atMobiles", []),
        "isAtAll": call.data.get("isAtAll", False),
    }

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DingTalk Notify from a config entry."""
    token = entry.data[CONF_TOKEN]
    secret = entry.data.get(CONF_SECRET)
    dingtalk = DingTalkNotify(token, secret)
    
    # 注册设备（使用最新API）
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer="DingTalk",
        name=f"{DOMAIN}-{token[-6:]}",
        entry_type=DeviceEntryType.SERVICE,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dingtalk

    async def send_text_message(call: ServiceCall) -> None:
        """Handle the service call for text message."""
        params = {
            "msgtype": "text",
            "text": {"content": call.data.get("message", "")},
            "at": process_at_params(call),
        }
        try:
            await dingtalk.send_message(**params)
        except Exception as e:
            _LOGGER.error(f"Failed to send text message: {e}")

    async def send_markdown_message(call: ServiceCall) -> None:
        """Handle the service call for markdown message."""
        title = call.data.get("title", "").strip()
        message = call.data.get("message", "").strip()
        picUrl = call.data.get("picUrl", "").strip()
        if not message:
            _LOGGER.error("Content is required for markdown message.")
            return
        params = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": _format_markdown_message(title, message, picUrl),
            },
            "at": process_at_params(call),
        }
        try:
            await dingtalk.send_message(**params)
        except Exception as e:
            _LOGGER.error(f"Failed to send markdown message: {e}")

    async def send_link_message(call: ServiceCall) -> None:
        """Handle the service call for link message."""
        title = call.data.get("title", "").strip()
        message = call.data.get("message", "").strip()
        picUrl = call.data.get("picurl", "").strip()
        messageUrl = call.data.get("messageurl", "").strip()
        if not messageUrl:
            _LOGGER.error("Message URL is required for link message.")
            return
        params = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": message,
                "picUrl": picUrl,
                "messageUrl": messageUrl,
            },
            "at": process_at_params(call),
        }
        try:
            await dingtalk.send_message(**params)
        except Exception as e:
            _LOGGER.error(f"Failed to send link message: {e}")

    async def send_actioncard_message(call: ServiceCall) -> None:
        """Handle the service call for actioncard message."""
        title = call.data.get("title", "").strip()
        message = call.data.get("message", "").strip()
        picUrl = call.data.get("picurl", "").strip()
        singleTitle = call.data.get("singleTitle", "").strip()
        singleURL = call.data.get("singleURL", "").strip()
        btnOrientation = call.data.get("btnOrientation", "0").strip()
        btns = call.data.get("btns", [])
        if not btns:
            _LOGGER.error("Buttons are required for actioncard message.")
            return
        params = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": message,
                "picUrl": picUrl,
                "singleTitle": singleTitle,
                "singleURL": singleURL,
                "btnOrientation": btnOrientation,
                "btns": btns,
            },
            "at": process_at_params(call),
        }
        try:
            await dingtalk.send_message(**params)
        except Exception as e:
            _LOGGER.error(f"Failed to send actioncard message: {e}")

    # 注册服务
    hass.services.async_register(DOMAIN, SERVICE_SEND_TEXT, send_text_message, schema=SEND_TEXT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_MARKDOWN, send_markdown_message, schema=SEND_MARKDOWN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_LINK, send_link_message, schema=SEND_LINK_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_ACTIONCARD, send_actioncard_message, schema=SEND_ACTIONCARD_SCHEMA)
    
    hass.data[DOMAIN]['service_counter'] = 4
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # 注销服务
    for service in [SERVICE_SEND_TEXT, SERVICE_SEND_MARKDOWN, SERVICE_SEND_LINK, SERVICE_SEND_ACTIONCARD]:
        hass.services.async_remove(DOMAIN, service)
    
    # 清理设备
    device_registry = dr.async_get(hass)
    if device := device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)}):
        device_registry.async_remove_device(device.id)
    
    # 清理数据
    hass.data[DOMAIN].pop(entry.entry_id, None)
    hass.data[DOMAIN]['service_counter'] = 0
    
    return True