"""Interfaces with the Integration 101 Template api sensors."""

from enum import StrEnum
import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
)

from homeassistant.components.alarm_control_panel.const import AlarmControlPanelState, AlarmControlPanelEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from propcache.api import cached_property

from . import OlarmConfigEntry
from .const import DOMAIN, ALARM_DEVICE_TO_HASS, AreaConf, AreaState, AreaStatus, DeviceType
from .coordinator import OlarmCoordinator, AlarmArea, AlarmDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OlarmConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Alarm Control Panel!"""

    _LOGGER.debug("Alarm Control Panel - async_setup_entry")
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: OlarmCoordinator = config_entry.runtime_data.coordinator

    # Enumerate all the binary sensors in your data value from your DataUpdateCoordinator and add an instance of your binary sensor class
    # to a list for each one.
    # This maybe different in your specific case, depending on how your data is structured
    alarm_control_panels = []

    for olarm_config in coordinator.data.olarm_conf_data.values():
        for area_config in olarm_config.alarm_conf.area_conf:
            match ALARM_DEVICE_TO_HASS.get(olarm_config.alarm_conf.alarm_make, None):
                case "IDXControlPanel":
                    _LOGGER.debug("First entity to setup: %s", area_config.id)
                    alarm_control_panels.append(OlarmControlledPanel(coordinator, area_config, alarm_device_id=olarm_config.id ,device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}")} ))
                case _:
                    _LOGGER.warning("Unsupported alarm type %s for device %s",olarm_config.alarm_conf.alarm_make, area_config.id)
                    alarm_control_panels.append(OlarmControlledPanel(coordinator, area_config, alarm_device_id=olarm_config.id ,device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}")} ))

    # Create the binary sensors.
    async_add_entities(alarm_control_panels)


class OlarmControlledPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Implementation of a Olarm controlled Panel."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OlarmCoordinator, area_config: AreaConf, alarm_device_id: str, device_identifier=dict[tuple[str,str]]) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.area_state: AreaState | None = None
        self.area_conf: AreaConf = area_config
        self.device_identifier = device_identifier
        self.alarm_device_id = alarm_device_id
        self.coordinator = coordinator

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        _LOGGER.debug("Get state for: %s", self.unique_id)
        self.area_state = self.coordinator.get_area_by_id(
            self.alarm_device_id, self.area_conf.id
        )
        _LOGGER.debug("State returned: %s", self.area_state)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers parameter.
        # If your device connects via another device, add via_device parameter with the indentifiers of that device.
        return DeviceInfo(
            identifiers=self.device_identifier
        )

    @property
    def name(self):
        """Name of the entity."""
        return self.area_conf.label

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm control panel entity state."""
        if self.area_state is not None:
            _LOGGER.debug("Get Alarm State: %s", self.area_state.status)
            match self.area_state.status:
                case "notready" | "disarm":
                    return AlarmControlPanelState.DISARMED
                case "arm":
                    return AlarmControlPanelState.ARMED_AWAY
                case "sleep" | "stay" | "partarm1" | "partarm2" | "partarm3" | "partarm4":
                    return AlarmControlPanelState.ARMED_HOME
                case "alarm" | "fire" | "emergency":
                    _LOGGER.debug("Return Alarm State: %s", AlarmControlPanelState.TRIGGERED)
                    return AlarmControlPanelState.TRIGGERED
                case "countdown":
                    return AlarmControlPanelState.PENDING
        return None

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""
        return (AlarmControlPanelEntityFeature.ARM_AWAY |
                AlarmControlPanelEntityFeature.ARM_HOME |
                AlarmControlPanelEntityFeature.TRIGGER)

    @property
    def code_arm_required(self) -> bool:
        """Return if code is required for arm actions."""
        return False

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        # All entities must have a unique id.  Think carefully what you want this to be as
        # changing it later will cause HA to create new entities.
        return f"{DOMAIN}-{self.alarm_device_id}-Area-{self.area_conf.id}"

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        _LOGGER.debug("Alarm Control Panel - Disarm area %s", self.area_conf.id)
        await self.coordinator.area_disarm(self.alarm_device_id, self.area_conf.id)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        _LOGGER.debug("Alarm Control Panel - Arm Home area %s", self.area_conf.id)
        await self.coordinator.area_arm_home(self.alarm_device_id, self.area_conf.id)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        _LOGGER.debug("Alarm Control Panel - Arm Away area %s", self.area_conf.id)
        await self.coordinator.area_arm_away(self.alarm_device_id, self.area_conf.id)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        _LOGGER.debug("Alarm Control Panel - Arm Night area %s", self.area_conf.id)
        await self.coordinator.area_arm_night(self.alarm_device_id, self.area_conf.id)