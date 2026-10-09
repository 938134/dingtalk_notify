"""Config flow for DingTalk Notify."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_RETRY,
    CONF_SECRET,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONFIG_ENTRY_MINOR_VERSION,
    CONFIG_ENTRY_VERSION,
    DEFAULT_RETRY,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_RETRY,
    MAX_TIMEOUT,
    MIN_RETRY,
    MIN_TIMEOUT,
    normalize_token,
    short_token,
)

CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_SECRET): cv.string,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_TIMEOUT, max=MAX_TIMEOUT)
        ),
        vol.Optional(CONF_RETRY, default=DEFAULT_RETRY): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_RETRY, max=MAX_RETRY)
        ),
    }
)


def _clean_credentials(
    user_input: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """Validate and normalize the credentials entered by the user.

    Returns the cleaned data, or an empty mapping plus the translation key of
    the error to show.

    DingTalk has no "ping" endpoint for custom robots, so there is nothing to
    handshake with. The only thing worth checking up front is that the user
    actually pasted usable credentials, and that a pasted webhook URL is
    reduced to its token.
    """
    token = normalize_token(user_input[CONF_TOKEN])
    if not token:
        return {}, "invalid_token"

    secret = (user_input.get(CONF_SECRET) or "").strip()
    if secret and " " in secret:
        return {}, "invalid_secret"

    return {CONF_TOKEN: token, CONF_SECRET: secret}, None


def _credentials_title(token: str) -> str:
    """Return the title of a config entry for a token."""
    return f"钉钉消息机器人 ({short_token(token)})"


class DingTalkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup and the reconfigure flow.

    Rotating the access token or the signing secret is handled by the
    reconfigure flow rather than by an options flow: they are connection
    credentials, not user preferences.
    """

    VERSION = CONFIG_ENTRY_VERSION
    MINOR_VERSION = CONFIG_ENTRY_MINOR_VERSION

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow started from the user interface."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data, error = _clean_credentials(user_input)
            if error is not None:
                errors["base"] = error
            else:
                await self.async_set_unique_id(data[CONF_TOKEN])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_credentials_title(data[CONF_TOKEN]), data=data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the reconfigure flow (token / secret rotation)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data, error = _clean_credentials(user_input)
            if error is not None:
                errors["base"] = error
            else:
                # The access token is the unique ID of the entry, and rotating
                # it is precisely the point of this flow. So instead of bailing
                # out on a unique ID mismatch, only refuse to point the entry at
                # a robot that is already configured somewhere else.
                for other in self._async_current_entries():
                    if other.entry_id != entry.entry_id and (
                        other.unique_id == data[CONF_TOKEN]
                    ):
                        return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=data[CONF_TOKEN],
                    title=_credentials_title(data[CONF_TOKEN]),
                    data_updates=data,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                CREDENTIALS_SCHEMA, {**entry.data, **(user_input or {})}
            ),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DingTalkOptionsFlow:
        """Return the options flow."""
        return DingTalkOptionsFlow()


class DingTalkOptionsFlow(OptionsFlowWithReload):
    """Handle the integration options.

    `OptionsFlowWithReload` reloads the entry when the options change, which is
    exactly what we need: the client is built with the timeout and retry count
    from the options. No `entry.add_update_listener` is required, and since the
    reloading methods of the reconfigure flow are not combined with a listener,
    the integration cannot be reloaded twice.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_TIMEOUT: self.config_entry.options.get(
                        CONF_TIMEOUT, DEFAULT_TIMEOUT
                    ),
                    CONF_RETRY: self.config_entry.options.get(CONF_RETRY, DEFAULT_RETRY),
                },
            ),
        )
