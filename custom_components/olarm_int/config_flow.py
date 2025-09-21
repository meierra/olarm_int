"""Config flow for the Olarm Integration integration."""

from __future__ import annotations

import logging
from typing import Any

from .helpers import get_entity_configuration
import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, ConfigEntry, OptionsFlow
from homeassistant.const import CONF_API_TOKEN, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector
from homeassistant.helpers.network import get_url
from homeassistant.components import webhook


from .const import DOMAIN, CONF_WEBHOOK_SECRET, CONF_WEBHOOK_ENABLED, OlarmConf, AlarmConf, ZoneConf, AreaConf
from .olarm_api import OlarmAPI, APIAuthError, APIConnectionError, OlarmDevice

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.
    api = OlarmAPI(data[CONF_API_TOKEN], async_get_clientsession(hass))
    try:
        api_data = await api.initial_connect()
        device_data = await get_entity_configuration(api_data['devices'])
        # If you cannot connect, raise CannotConnect
        # If the authentication is wrong, raise InvalidAuth
    except APIAuthError as err:
        raise InvalidAuth from err
    except APIConnectionError as err:
        raise CannotConnect from err

    _LOGGER.debug("Validate Input - returned data %s", device_data)
    return {"title": f"Integration - Olarm ({api_data['userId']})", "devices": device_data}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Olarm Integration."""

    VERSION = 1

    _input_data: dict[str, Any]

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input | {"devices" : info['devices']})

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class OptionsFlowHandler(OptionsFlow):

    def __init__(self) -> None:
        """Initialize options flow."""
        self.options = {}

    async def async_step_init(self, user_input=None):
        """Handle options flow.

        Display an options menu
        option ids relate to step function name
        Also need to be in strings.json and translation files.
        """

        return self.async_show_menu(
            step_id="init",
            menu_options=["select_devices","register_webhook"]
        )

    async def async_step_select_devices(self, user_input=None):
        """Handle menu option 2 flow.

        In this option, we show how to use dynamic data in a selector.
        """
        config_data = self.config_entry.data
        option_data = self.config_entry.options
        ## debug
        _LOGGER.debug("select_devices - Config data: %s", config_data)
        _LOGGER.debug("select_devices - Option data: %s", option_data)

        if user_input is not None:
            option_data = option_data | user_input
            _LOGGER.debug("select_devices - Updated Option data: %s", option_data)
            return self.async_create_entry(title="", data=option_data)

        data_schema = vol.Schema(
            {vol.Optional(OlarmConf(**device).id, default=option_data.get( OlarmConf(**device).id ,False)): selector({"boolean" : {}}) for device in config_data["devices"]}
        )

        ### Define the data_description for more user friendly names
        data_description = { OlarmConf(**device).id : OlarmConf(**device).label for device in config_data["devices"]}
        _LOGGER.info("Data Descriptions: %s", data_description)

        return self.async_show_form(step_id="select_devices", data_schema=data_schema, description_placeholders=data_description)

    async def async_step_register_webhook(self, user_input=None):
        """Handle menu option 2 flow.

        In this option, we show how to use dynamic data in a selector.
        """
        option_data = self.config_entry.options

        _LOGGER.debug("register_webhook - saved webhook_id %s", option_data.get(CONF_WEBHOOK_ID))
        _LOGGER.debug("register_webhook - saved webhook_enabled %s", option_data.get(CONF_WEBHOOK_ENABLED))
        _LOGGER.debug("register_webhook - saved webhook_secret %s", option_data.get(CONF_WEBHOOK_SECRET))
        ## Generate a webhook id if not already done
        webhook_id = option_data.get(CONF_WEBHOOK_ID,webhook.async_generate_id())

        if user_input is not None:

            option_data = option_data | {CONF_WEBHOOK_ID: webhook_id} | user_input
            _LOGGER.debug("register_webhook - webhook_id %s", option_data.get(CONF_WEBHOOK_ID))
            _LOGGER.debug("register_webhook - webhook_enabled %s", option_data.get(CONF_WEBHOOK_ENABLED))
            _LOGGER.debug("register_webhook - webhook_secret %s", option_data.get(CONF_WEBHOOK_SECRET))
            return self.async_create_entry(
                title="",
                data=option_data,
                )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_ENABLED, default=option_data.get(CONF_WEBHOOK_ENABLED,False)): selector({"boolean" : {}}),
                vol.Optional(CONF_WEBHOOK_SECRET): str,
            }
        )

        base_url = URL(get_url(self.hass))
        assert base_url.host

        return self.async_show_form(
            step_id="register_webhook",
            data_schema=data_schema,
            description_placeholders={
                "path": webhook.async_generate_path(webhook_id),
                "server": base_url.host,
                "port": str(base_url.port),
            },
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
