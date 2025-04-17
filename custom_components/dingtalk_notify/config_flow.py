import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_TOKEN, CONF_SECRET

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_SECRET): cv.string,
    }
)

class DingTalkNotifyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DingTalk Notify."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
    
        if user_input is not None:
            if not user_input[CONF_TOKEN]:
                errors["base"] = "invalid_token"
            else:
                # 获取已存在的配置条目
                existing_entries = self.hass.config_entries.async_entries(DOMAIN)
                if existing_entries:
                    title = existing_entries[0].translations.get("title", "DingTalk Notify")
                else:
                    title = "DingTalk Notify"
                return self.async_create_entry(title=title, data=user_input)
    
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DingTalkNotifyOptionsFlow(config_entry)

class DingTalkNotifyOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for DingTalk Notify."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOKEN,
                        default=self.config_entry.data.get(CONF_TOKEN),
                    ): cv.string,
                    vol.Optional(
                        CONF_SECRET,
                        default=self.config_entry.data.get(CONF_SECRET),
                    ): cv.string,
                }
            ),
        )
