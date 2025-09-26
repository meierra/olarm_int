"""The Olarm Integration integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import logging

from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr

from .coordinator import OlarmCoordinator, OlarmDevice

_LOGGER = logging.getLogger(__name__)

# Platforms required to be set up for this integration.
# A Alarm Control Panel is mapped to each Area defined in Olarm
_PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.SENSOR, Platform.BUTTON]

type OlarmConfigEntry = ConfigEntry[RuntimeData]

@dataclass
class RuntimeData:
    """Class to hold your data."""
    coordinator: DataUpdateCoordinator

# TODO Update entry annotation
async def async_setup_entry(hass: HomeAssistant, config_entry: OlarmConfigEntry) -> bool:
    """Set up Olarm Integration from a config entry."""

    # Setup the coordinator to manage data updates from the Olarm API
    coordinator = OlarmCoordinator(hass, config_entry, async_get_clientsession(hass))

    # Test to see if api initialised correctly, else raise ConfigNotReady to make HA retry setup
    _LOGGER.debug("Check Coordinator connected")
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.api.connected:
        raise ConfigEntryNotReady

    # Initialise a listener for config flow options changes.
    # This will be removed automatically if the integraiton is unloaded.
    # See config_flow for defining an options setting that shows up as configure
    # on the integration.
    # If you do not want any config flow options, no need to have listener.
    _LOGGER.debug("Add listener for options update")
    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    # Add the coordinator and update listener to config runtime data to make
    # accessible throughout your integration
    config_entry.runtime_data = RuntimeData(coordinator)

    # Create device registry entries for Olarm devices & attached alarm systems
    # This done so that we can link sensors, buttons and alarm control panels to the Olarm device or Alarm Device
    for olarmdevice in coordinator.get_olarm_conf_data().values():
        await _async_add_devices_to_registry(hass, config_entry.entry_id, coordinator.data.controller_name, olarmdevice)

    # Call async_setup method for each platform:
    # Platform.ALARM_CONTROL_PANEL alarm_control_panel.py -> async_setup_entry
    # Platform.SENSOR sensor.py -> async_setup_entry
    # Platform.BUTTON button.py -> async_setup_entry
    await hass.config_entries.async_forward_entry_setups(config_entry, _PLATFORMS)

    # Return true to denote a successful setup.
    return True

async def _async_add_devices_to_registry(hass, entry_id :str, controller_name: str, olarm_device : OlarmDevice) -> None:
    """Add Olarm and associated devices to the device registry."""
    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry_id,
    #     connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
        identifiers={(DOMAIN, f"{controller_name}-{olarm_device.serial_number}")},
        manufacturer="Olarm",
    #     suggested_area="Kitchen",
        name=olarm_device.label,
        model=olarm_device.type,
    #     model_id=config.modelid,
        sw_version=olarm_device.firmware_version,
    #     hw_version=config.hwversion,
    )
    device_registry.async_get_or_create(
        config_entry_id=entry_id,
    #     connections={(dr.CONNECTION_NETWORK_MAC, config.mac)},
        identifiers={(DOMAIN, f"{controller_name}-alarm_system-{olarm_device.alarm_conf.id}")},
        via_device=(DOMAIN, f"{controller_name}-{olarm_device.serial_number}"),
        manufacturer="Unknown",
    #     suggested_area="Kitchen",
        name=f"{olarm_device.alarm_conf.label} (Alarm System)",
        model=f"{olarm_device.alarm_conf.alarm_make} - {olarm_device.alarm_conf.alarm_make_detail}",
    #     model_id=config.modelid,
        sw_version="Unknown",

    #     hw_version=config.hwversion,
    )

async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # Reload the integration when the options change.
    # await config_entry.runtime_data.coordinator.async_options_updated()
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Delete device if selected from UI."""
    # Adding this function shows the delete device option in the UI.
    # Remove this function if you do not want that option.
    # You may need to do some checks here before allowing devices to be removed.
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: OlarmConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when you remove your integration or shutdown HA.
    # If you have created any custom services, they need to be removed here too.

    # Unload platforms and return result
    return await hass.config_entries.async_unload_platforms(config_entry, _PLATFORMS)
