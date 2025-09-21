import logging

from enum import StrEnum
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorEntity
)
from homeassistant.components.sensor.const import SensorDeviceClass
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
    sensors = []
    for olarm_config in coordinator.data.olarm_conf_data.values():
        sensors.extend([
            OlarmStatusSensor(
                coordinator,
                alarm_device_id=olarm_config.id,
                device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-{olarm_config.serial_number}")}
                ),
            AlarmBatterySensor(
                coordinator,
                olarm_device_id=olarm_config.id,
                device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}")}
                ),
            AlarmACSensor(
                coordinator,
                olarm_device_id=olarm_config.id,
                device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}")}
                )

        ])
        sensors.extend([
            ZoneSensor(
                coordinator,
                olarm_device_id=olarm_config.id,
                sensor_id=zone.id,
                label=zone.label,
                type=zone.type,
                via_device=(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}"),
                device_identifier={(DOMAIN, f"{coordinator.data.controller_name}-alarm_system-{olarm_config.alarm_conf.id}-zonesensor-{zone.id}")}
            )
            for zone in olarm_config.alarm_conf.zone_conf
        ])

    # Create the sensors.
    async_add_entities(sensors)

class OlarmStatusSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Olarm Status Sensor."""

    _attr_has_entity_name = False
    _attr_translation_key = "devicestate"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_native_unit_of_measurement = None
    _attr_suggested_unit_of_measurement = None
    _attr_state_class = None

    def __init__(self, coordinator, alarm_device_id: str, device_identifier=dict[tuple[str,str]]) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.olarm_device_id = alarm_device_id
        self.name = "Device Status"
        self.device_identifier = device_identifier
        self._attr_unique_id = f"{DOMAIN}-{alarm_device_id}-Status Sensor"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        _LOGGER.debug("Get state for: %s", self.unique_id)
        match self.coordinator.get_olarm_status_by_id(
            self.olarm_device_id
        ):
            case "online":
                self._attr_native_value = SensorState.ONLINE
            case "offline":
                self._attr_native_value = SensorState.OFFLINE
            case "problem":
                self._attr_native_value = SensorState.PROBLEM
        _LOGGER.debug("State returned: %s", self._attr_native_value)
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
    def options(self):
        """Return the options of the sensor."""
        return [SensorState.ONLINE, SensorState.OFFLINE, SensorState.PROBLEM]


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AlarmBatterySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of a Olarm Status Sensor."""

    _attr_has_entity_name = False
    _attr_translation_key = "batterystate"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator, olarm_device_id: str, device_identifier=dict[tuple[str,str]]) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.olarm_device_id = olarm_device_id
        self.name = "Battery Status"
        self.device_identifier = device_identifier
        self._attr_unique_id = f"{DOMAIN}-{olarm_device_id}-Battery Sensor"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        _LOGGER.debug("Get state for: %s", self.unique_id)
        match bool(self.coordinator.get_battery_status_by_id(
            self.olarm_device_id
        )):
            case True:
                self._attr_is_on = True
            case False:
                self._attr_is_on = False
        _LOGGER.debug("State returned: %s", self._attr_is_on)
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
    def options(self):
        """Return the options of the sensor."""
        return [SensorState.ONLINE, SensorState.OFFLINE, SensorState.PROBLEM]


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

class AlarmACSensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of a Olarm Status Sensor."""

    _attr_has_entity_name = False
    _attr_translation_key = "acstate"
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, coordinator, olarm_device_id: str, device_identifier=dict[tuple[str,str]]) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.olarm_device_id = olarm_device_id
        self.name = "AC Status"
        self.device_identifier = device_identifier
        self._attr_unique_id = f"{DOMAIN}-{olarm_device_id}-AC Sensor"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        _LOGGER.debug("Get state for: %s", self.unique_id)
        match self.coordinator.get_ac_status_by_id(
            self.olarm_device_id
        ):
            case True:
                self._attr_is_on = True
            case False:
                self._attr_is_on = False
        _LOGGER.debug("State returned: %s", self._attr_is_on)
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
    def options(self):
        """Return the options of the sensor."""
        return [SensorState.ONLINE, SensorState.OFFLINE, SensorState.PROBLEM]


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
    

class ZoneSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Olarm Status Sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_native_unit_of_measurement = None
    _attr_suggested_unit_of_measurement = None
    _attr_state_class = None

    def __init__(self, coordinator, olarm_device_id: str, sensor_id,label,type, via_device=tuple[str,str],device_identifier=dict[tuple[str,str]]) -> None:
        """Initialise sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.olarm_device_id = olarm_device_id
        self.sensor_id = sensor_id
        self.via_device = via_device
        self.label = label
        self.type = type
        self.device_identifier = device_identifier
        self._attr_unique_id = f"{DOMAIN}-{olarm_device_id}-Sensor-{sensor_id}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        _LOGGER.debug("Get state for: %s", self.unique_id)
        match self.coordinator.get_zone_status_by_id(
            self.olarm_device_id, self.sensor_id
        ):
            case "a":
                self._attr_native_value = ZoneStatus.ACTIVE
            case "b":
                self._attr_native_value = ZoneStatus.BYPASSED
            case "c":
                self._attr_native_value = ZoneStatus.CLOSED
        _LOGGER.debug("State returned: %s", self._attr_native_value)
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        match self.type:
            case ZoneType.DOOR:
                return f"{self.sensor_id:0>2} Door - {self.label}"
            case ZoneType.WINDOW:
                return f"{self.sensor_id:0>2} Window - {self.label}"
            case ZoneType.PIR_INDOOR:
                return f"{self.sensor_id:0>2} Motion - {self.label}"
            case ZoneType.PIR_OUTDOOR:
                return f"{self.sensor_id:0>2} Motion - {self.label}"
            case ZoneType.PANIC_BOTTON:
                return f"{self.sensor_id:0>2} Panic - {self.label}"
            case ZoneType.PANIC_ZONE:
                return f"{self.sensor_id:0>2} Panic - {self.label}"
            case _:
                return f"{self.sensor_id:0>2} Zone - {self.label}"


    @property
    def translation_key(self):
        match self.type:
            case ZoneType.DOOR:
                return "doorsensor"
            case ZoneType.WINDOW:
                return "windowsensor"
            case ZoneType.PIR_INDOOR:
                return "indoormotionsensor"
            case ZoneType.PIR_OUTDOOR:
                return "outdoormotionsensor"
            case ZoneType.PANIC_BOTTON:
                return "panicbutton"
            case ZoneType.PANIC_ZONE:
                return "paniczone"
            case _:
                return "zonesensor"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # Identifiers are what group entities into the same device.
        # If your device is created elsewhere, you can just specify the indentifiers parameter.
        # If your device connects via another device, add via_device parameter with the indentifiers of that device.
        return DeviceInfo(
            identifiers=self.device_identifier,
            via_device=self.via_device,
            manufacturer="Unknown",
            name=self.name
        )


    @property
    def options(self):
        """Return the options of the sensor."""
        return [ZoneStatus.CLOSED, ZoneStatus.ACTIVE, ZoneStatus.BYPASSED]


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success