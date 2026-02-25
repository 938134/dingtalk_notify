"""Config flow for DingTalk Notify."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_TOKEN, CONF_SECRET, short_token

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_SECRET): cv.string,
    }
)

class DingTalkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_TOKEN])
            self._abort_if_unique_id_configured()
            title = f"钉钉消息机器人 ({short_token(user_input[CONF_TOKEN])})"
            return self.async_create_entry(title=title, data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return DingTalkOptionsFlow(config_entry)


class DingTalkOptionsFlow(config_entries.OptionsFlow):
    """Options flow for DingTalk Notify."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry  # 使用私有变量存储

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # 创建新的数据字典，保留必要的字段
            new_data = {
                CONF_TOKEN: user_input[CONF_TOKEN],
                CONF_SECRET: user_input.get(CONF_SECRET, ""),
            }
            
            # 更新配置项
            self.hass.config_entries.async_update_entry(
                self._config_entry,  # 使用私有变量
                data=new_data,
                options=self._config_entry.options,  # 保留原有options
            )
            
            # 返回选项流完成
            return self.async_create_entry(title="", data={})

        # 显示表单时使用当前的数据
        current_data = self._config_entry.data  # 使用私有变量
        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN, default=current_data.get(CONF_TOKEN, "")): str,
                vol.Optional(CONF_SECRET, default=current_data.get(CONF_SECRET, "")): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)