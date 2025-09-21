"""DataUpdateCoordinator for Olarm Integration."""

from dataclasses import dataclass
from datetime import timedelta
import json
import hmac
from aiohttp import ClientSession
import logging

from homeassistant.components.device_tracker import config_entry
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_API_TOKEN, CONF_WEBHOOK_ID

from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.aiohttp import web

from .olarm_api import APIConnectionError, OlarmAPI, APIAuthError, DeviceType, APIActionError
from .const import DEFAULT_SCAN_INTERVAL, CONF_WEBHOOK_ENABLED, OLARM_DIGEST_HEADER, OLARM_DIGEST_ALG, CONF_WEBHOOK_SECRET, ActionId, WebHookActions, WebHookStates, ZoneState, AreaState, AlarmState, OlarmConf, OlarmState, action_map
from .helpers import get_entity_configuration

_LOGGER = logging.getLogger(__name__)


###TODO move the device lookup to options to allow devices to change without redoing config flow
@dataclass
class AlarmZone:
    """Alarm Zone class."""
    id: int
    label: str
    type: int
    status: str
    identifier: {tuple[str, str]}
    via_device: tuple[str, str] | None = None
    timestamp: float | None = None

@dataclass
class AlarmArea:
    """Alarm Area class."""
    id: str
    label: str
    identifier: {tuple[str, str]}
    via_device: tuple[str, str] | None = None
    status: str | None = None
    trigger_zones: list[int] | None = None
    timestamp: float | None = None

@dataclass
class AlarmDevice:
    """Device Type Info class."""
    id: str
    label: str
    alarm_make: str
    identifier: {tuple[str, str]}
    via_device: tuple[str, str] | None = None
    alarm_make_detail: str | None = None
    battery: bool | None = None
    mains: bool | None = None


@dataclass
class OlarmDevice:
    """Olarm Device class."""
    id: str
    label: str
    serial_number: str
    type: str
    identifier: {tuple[str, str]}
    via_device: tuple[str, str] | None = None
    firmware_version: str | None = None
    status: str | None = None # Offline, Online, Problem
    timezone: str | None = None

@dataclass
class OlarmAPIData:
    """Class to hold api data."""
    controller_name: str
    olarm_conf_data: dict[str, OlarmConf] | None = None
    olarm_state_data: dict[str, OlarmState] | None = None


class OlarmCoordinator(DataUpdateCoordinator):
    """My example coordinator."""

    data: OlarmAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry,  websession: ClientSession) -> None:
        """Initialize coordinator."""

        _LOGGER.debug("Init coordinator")
        # Set variables from values entered in config flow setup
        self.last_update_success = None
        self.token = config_entry.data[CONF_API_TOKEN]
        self.webhook_id = config_entry.options.get(CONF_WEBHOOK_ID, None)
        self.webhook_enabled = config_entry.options.get(CONF_WEBHOOK_ENABLED, False)
        self.webhook_secret = config_entry.options.get(CONF_WEBHOOK_SECRET, "")
        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        self.devices_to_track = [device["id"] for device in config_entry.data["devices"] if config_entry.options.get(device["id"], False)]

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            # Method to call on every update interval.
            update_method=self.async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            # Using config option here but you can just use a value.
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # Initialise your api here
        self.api = OlarmAPI(self.token, websession)


    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("coordinator - Update data")
        try:
            device_data = [await self.api.get_device(device) for device in self.devices_to_track]
        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        except Exception as err:
            # This will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        _LOGGER.debug("coordinator - data for %i devices received", len(device_data))
        _LOGGER.debug("coordinator - Translate data")

        ### New
        olarm_state_data = await self.get_olarm_state_data(device_data)
        olarm_conf_data = await get_entity_configuration(device_data)

        self.last_update_success = True

        # What is returned here is stored in self.data by the DataUpdateCoordinator
        return OlarmAPIData(self.api.controller_name, olarm_conf_data, olarm_state_data)

    # async def get_entity_configuration(self, olarm_devices = list[OlarmDevice]) -> list[OlarmConf]:
    #     """Return the entity configuration for the devices."""
    #     # Return a list of entity configuration data
    #     _LOGGER.debug("coordinator - create olarm configuration entries")
    #     return await get_entity_configuration(olarm_devices)

    async def get_olarm_state_data(self, olarm_devices = dict[str,OlarmDevice]) -> list[OlarmState]:
        # Return a list of entity configuration data
        _LOGGER.debug("coordinator - create olarm state entries")
        return { device.id :OlarmState(
            firmware_version=device.firmware_version,
            status=device.status,
            timezone=device.timezone,
            alarm=AlarmState(
                zones={ zone.id : ZoneState(
                    status=zone.status,
                    timestamp=zone.timestamp
                    ) for zone in device.alarm_detail.alarm_zones},
                areas={ area.id : AreaState(
                    status=area.status,
                    trigger_zones=area.trigger_zones,
                    timestamp=area.timestamp
                    ) for area in device.alarm_detail.alarm_areas},
                battery_ok = device.alarm_detail.battery,
                ac_ok = device.alarm_detail.mains,
            )
        ) for device in olarm_devices}

    def get_device_by_id(
        self, deviceId: int, deviceType: DeviceType, via_device : tuple[str, str] | None = None ) -> OlarmDevice | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        if deviceType == DeviceType.ALARM_AREA:
            try:
                return self.data.alarm_areas[via_device][deviceId - 1]
            except IndexError:
                _LOGGER.error("coordinator - Area %s did not retrieve data", deviceId)
                _LOGGER.debug("coordinator - Areas belonging to device searched %s", via_device)
                _LOGGER.debug("coordinator - Areas available  %i", len(self.data.alarm_areas.get(via_device, [])))
                return None
        return None

    def get_alarm_make_by_id(
        self, device: str) -> str:
        """Return device by device id."""
        # Return the alarm make for the device
        try:
            return self.data.olarm_conf_data[device].alarm_conf.alarm_make
        except KeyError:
            _LOGGER.error("coordinator - Device %s does not have a alarm make details", device)
            return None

    def get_area_by_id(
        self, alarm_id : str, device_id: int) -> OlarmDevice | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        _LOGGER.debug("coordinator - Areas belonging to device searched %s", alarm_id)
        _LOGGER.debug("coordinator - Areas available  %i", len(self.data.olarm_state_data[alarm_id].alarm.areas))
        try:
            return self.data.olarm_state_data[alarm_id].alarm.areas[device_id]
        except IndexError | KeyError:
            _LOGGER.error("coordinator - Area %s did not retrieve data", device_id)
            return None

    async def zone_bypass_toggle(self, device : str, zone : int) -> bool:
        """Bypass a zone."""
        _LOGGER.debug("coordinator - Toggle bypass Zone:%s on device %s", zone, device)
        match self.get_zone_status_by_id(device, zone):
            case "b":
                try:
                    action : ActionId = action_map["ids_x64"][ActionId.ZONE_UNBYPASS]
                except KeyError:
                    action = ActionId.ZONE_UNBYPASS
                try:
                    result = await self.api.send_action(device, action, zone)
                    if result:
                        self.data.olarm_state_data[device].alarm.zones[zone].status = "c"
                except (APIAuthError, APIConnectionError, APIActionError) as err:
                    _LOGGER.error("coordinator - Unable to remove bypass on %s Zone %s", device, zone)
                    _LOGGER.error(err)
                    return False
            case "a" | "c":
                try:
                    action : ActionId = action_map["ids_x64"][ActionId.ZONE_BYPASS]
                except KeyError:
                    action = ActionId.ZONE_BYPASS
                try:
                    result = await self.api.send_action(device, action, zone)
                    if result:
                        self.data.olarm_state_data[device].alarm.zones[zone].status = "c"
                except (APIAuthError, APIConnectionError, APIActionError) as err:
                    _LOGGER.error("coordinator - Unable to bypass %s Zone %s", device, zone)
                    _LOGGER.error(err)
                    return False
        self.async_update_listeners()
        return True

    async def area_arm_away(self, device : str, area : int) -> bool:
        """Arm a area"""
        _LOGGER.debug("coordinator - Toggle Arm Area:%s on device %s", area, device)
        try:
            action : ActionId = action_map["ids_x64"][ActionId.AREA_ARM]
        except KeyError:
                action = ActionId.AREA_ARM
        try:
            await self.api.send_action(device, action, area)
        except (APIAuthError, APIConnectionError, APIActionError) as err:
            _LOGGER.error("coordinator - Unable to arm device %s area %s", device, area)
            _LOGGER.error(err)
            return False
        return True

    async def area_disarm(self, device : str, area : int) -> bool:
        """Disarm a area"""
        _LOGGER.debug("coordinator - Toggle Disarm Area:%s on device %s", area, device)
        try:
            action : ActionId = action_map[self.get_alarm_make_by_id(device)][ActionId.AREA_DISARM]
        except KeyError:
                action = ActionId.AREA_DISARM
        try:
            await self.api.send_action(device, action, area)
        except (APIAuthError, APIConnectionError, APIActionError) as err:
            _LOGGER.error("coordinator - Unable to disarm device %s area %s", device, area)
            _LOGGER.error(err)
            return False
        return True

    async def area_arm_home(self, device : str, area : int) -> bool:
        """Arm a area - Home"""
        _LOGGER.debug("coordinator - Toggle arm Area (Home):%s on device %s", area, device)
        try:
            action : ActionId = action_map[self.get_alarm_make_by_id(device)][ActionId.AREA_STAY]
        except KeyError:
                action = ActionId.AREA_STAY
        try:
            await self.api.send_action(device, action, area)
        except (APIAuthError, APIConnectionError, APIActionError) as err:
            _LOGGER.debug("coordinator - Action: %s ", action)
            _LOGGER.error("coordinator - Unable to arm device (Home) %s area %s", device, area)
            _LOGGER.error(err)
            return False
        return True

    async def area_arm_night(self, device : str, area : int) -> bool:
        """Arm a area - Night"""
        _LOGGER.debug("coordinator - Toggle arm Area (Night):%s on device %s", area, device)
        try:
            action : ActionId = action_map[self.get_alarm_make_by_id(device)][ActionId.AREA_SLEEP]
        except KeyError:
                action = ActionId.AREA_SLEEP
        try:
            await self.api.send_action(device, action, area)
        except (APIAuthError, APIConnectionError, APIActionError) as err:
            _LOGGER.debug("coordinator - Action: %s ", action)
            _LOGGER.error("coordinator - Unable to arm device (Night) %s area %s", device, area)
            _LOGGER.error(err)
            return False
        return True

    def get_olarm_status_by_id(
        self, device_id : str) -> OlarmDevice | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return self.data.olarm_state_data[device_id].status
        except IndexError | KeyError:
            _LOGGER.error("coordinator - Olarm (%s) could not get status", device_id)
            return None

    def get_zone_status_by_id(
        self, olarm_id : str, device_id: int) -> str | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return self.data.olarm_state_data[olarm_id].alarm.zones[device_id].status
        except IndexError | KeyError:
            _LOGGER.error("coordinator - Olarm (%s) could not get status zone %s", olarm_id,device_id)
            return None

    def get_battery_status_by_id(
        self, device_id : str) -> OlarmDevice | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return self.data.olarm_state_data[device_id].alarm.battery_ok
        except IndexError | KeyError:
            _LOGGER.error("coordinator - Olarm (%s) could not get status", device_id)
            return None

    def get_ac_status_by_id(
        self, device_id : str) -> OlarmDevice | None:
        """Return device by device id."""
        # Called by the binary sensors and sensors to get their updated data from self.data
        try:
            return self.data.olarm_state_data[device_id].alarm.ac_ok
        except IndexError | KeyError:
            _LOGGER.error("coordinator - Olarm (%s) could not get status", device_id)
            return None

    def get_alarm_device_by_identifier(
        self, identifier: tuple[str, str]) -> AlarmDevice | None:
        """Return alarm device by identifier."""
        try:
            for alarmdevice in self.data.alarm_devices:
                if identifier in alarmdevice.identifier:
                    return alarmdevice
        except KeyError:
            return None

    def get_olarm_conf_data(self) -> list[dict[str, any]]:
        """Return list of devices."""
        _LOGGER.debug("coordinator - returning list of Olarm devices : %i", len(self.data.olarm_conf_data))
        return self.data.olarm_conf_data

    async def async_handle_webhook(self, hass: HomeAssistant, webhook_id: str, request: web.Request) -> None:
        """Handle webhook callback."""
        body = await request.text()

        try:
            data = json.loads(body) if body else {}
        except ValueError:
            _LOGGER.error(
                "Received invalid data from Olarm. Data needs to be formatted as JSON: %s",
                body,
            )
            return

        # Generate MAC on the received message body and compare to the received MAC
        received_mac_hex = request.headers.get(OLARM_DIGEST_HEADER, "")
        calculated_hmac_object = hmac.new(self.webhook_secret.encode('utf-8'), json.dumps(data,separators=(',', ':')).encode('utf-8'), digestmod=OLARM_DIGEST_ALG)
        calculated_mac_hex = OLARM_DIGEST_ALG + "=" + calculated_hmac_object.hexdigest()

        if not hmac.compare_digest(calculated_mac_hex, received_mac_hex):
            _LOGGER.error(
                "Olarm Webhook - Recieved data is signed by a different key, check Secret key config: expected (%s) got (%s)",
                calculated_mac_hex, received_mac_hex
            )
            _LOGGER.error(
                "Olarm Webhook - Raw Body: %s)",
                json.dumps(data,separators=(',', ':')).encode('utf-8')
            )
            return

        if not isinstance(data, dict):
            _LOGGER.error(
                "Received invalid data from Olarm. Data needs to be a dictionary: %s", data
            )
            return

        ### Upadate state based on the data received
        device_id = data.get("deviceId", None)
        event_action = data.get("eventAction", None)
        event_state = data.get("eventState", None)
        event_num = data.get("eventNum", None)
        event_time = data.get("eventTime", None)
        event_msg = data.get("eventMsg", "")

        match event_action:
            case WebHookActions.ZONE_ALARM:
                match event_state:
                    case WebHookStates.ALARM:
                        """Zone has been triggered, but we don't know the area, so set all areas to alarmed"""
                        for area in self.data.olarm_state_data[device_id].alarm.areas.values():
                            area.status = "alarm"
                            area.timestamp = event_time
                            area.trigger_zones.append(event_num)
            case WebHookActions.AREA:
                match event_state:
                    case WebHookStates.DISARMED:
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].status = "disarm"
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].timestamp = event_time
                    case WebHookStates.STAYARM1:
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].status = "partarm1"
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].timestamp = event_time
                    case WebHookStates.STAYARM2:
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].status = "partarm2"
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].timestamp = event_time
                    case WebHookStates.STAYARM3:
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].status = "partarm3"
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].timestamp = event_time
                    case WebHookStates.STAYARM4:
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].status = "partarm4"
                        self.data.olarm_state_data[device_id].alarm.areas[event_num].timestamp = event_time

        self.async_update_listeners()
        return
