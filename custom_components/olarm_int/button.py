import logging

from enum import StrEnum
from homeassistant.components.button import (
    ButtonEntity
)
from homeassistant.helpers.device_registry import DeviceInfo, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OlarmConfigEntry
from .const import DOMAIN, ZoneType, ZoneStatus

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import OlarmCoordinator

_LOGGER = logging.getLogger(__name__)

class SensorState(StrEnum):
    """Sensor States."""
    ONLINE = "Online"
    OFFLINE = "Offline"
    PROBLEM = "Problem"

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OlarmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Olarm Sensorls based on coordinator update."""
    _LOGGER.debug("Sensors - async_setup_entry")
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: OlarmCoordinator = config_entry.runtime_data.coordinator

    # Enumerate all the binary sensors in your data value from your DataUpdateCoordinator and add an instance of your binary sensor class
    # to a list for each one.
    # This maybe different in your specific case, depending on how your data is structured
    buttons = []
    for olarm_config in coordinator.data.olarm_conf_data.values():
        buttons.extend([
            BypassButton(
                coordinator,
                olarm_device_id=olarm_config.id,
                zone_id=zone.id,
                label=zone.label,
                type=zone.type,
                device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}")}
            )
            for zone in olarm_config.alarm_conf.zone_conf
        ])

    # Create the sensors.
    async_add_entities(buttons)

class BypassButton(ButtonEntity, CoordinatorEntity):
    """Representation of a Alarm Zone Bypass Button."""

    def __init__(
        self,
        coordinator: OlarmCoordinator,
        olarm_device_id: str,
        zone_id: str,
        label: str,
        type,
        device_identifier: set[tuple[str, str]],
    ) -> None:
        """Initialize the buttonr."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.olarm_device_id = olarm_device_id
        self.zone_id = zone_id
        self.zone_label = label
        self.type = type
        self.device_identifier = device_identifier
        self._attr_unique_id = f"{DOMAIN}-{olarm_device_id}-bypass-{zone_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        match self.type:
            case ZoneType.DOOR:
                return f"{self.zone_id:0>2} Door - {self.zone_label} - Bypass"
            case ZoneType.WINDOW:
                return f"{self.zone_id:0>2} Window - {self.zone_label} - Bypass"
            case ZoneType.PIR_INDOOR:
                return f"{self.zone_id:0>2} Motion - {self.zone_label} - Bypass"
            case ZoneType.PIR_OUTDOOR:
                return f"{self.zone_id:0>2} Motion - {self.zone_label} - Bypass"
            case ZoneType.PANIC_BOTTON:
                return f"{self.zone_id:0>2} Panic - {self.zone_label} - Bypass"
            case ZoneType.PANIC_ZONE:
                return f"{self.zone_id:0>2} Panic - {self.zone_label} - Bypass"
            case _:
                return f"{self.zone_id:0>2} Zone - {self.zone_label} - Bypass"


    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Button Pressed - %s", self.name)
        await self.coordinator.zone_bypass_toggle(self.olarm_device_id, self.zone_id)
        #await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers parameter.
        # If your device connects via another device, add via_device parameter with the indentifiers of that device.
        return DeviceInfo(
            identifiers=self.device_identifier
        )
