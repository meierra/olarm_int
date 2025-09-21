"""API Placeholder.

You should create your api seperately and have it hosted on PYPI.  This is included here for the sole purpose
of making this example code executable.
"""

from dataclasses import dataclass
from enum import IntEnum, StrEnum
import logging
import json
from random import choice, randrange
from aiohttp import ClientSession

from .const import BASE_URL, ActionId, AlarmArea, AlarmDevice, AlarmZone, DeviceType, OlarmDevice

_LOGGER = logging.getLogger(__name__)

class DeviceStatus(StrEnum):
    """Device status."""
    # Alarm states are
    OFFLINE = "offline"
    ONLINE = "online"
    PROBLEM = "problem"

class OlarmAPI:
    """Class for Olarm API."""

    def __init__(self, token: str, websession: ClientSession) -> None:
        """Initialise."""
        self.token = token
        self.session: ClientSession = websession
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.connected: bool = False

    @property
    def controller_name(self) -> str:
        """Return the name of the controller."""
        return "Olarm API"

    async def initial_connect(self) -> dict[str, any]:
        """Connect to api and download the list of devices."""
        resp = await self.session.request("GET", f"{BASE_URL}devices", headers=self.headers)
        match resp.status:
            case 403:
                raise APIAuthError("Error connecting to api. Invalid username or password.")
            case 429:
                raise APIConnectionError("Error connecting to api. Too many requests.")
            case 200:
                self.connected = True
                data = await resp.json()
                return { "userId" : data["userId"], "devices":
                        [await self.polulate_dataclass_from_api(device_data) for device_data in data['data']]}
        raise APIConnectionError("Unkown error connecting to api.")

    def disconnect(self) -> bool:
        """Disconnect from api."""
        self.connected = False
        return True

    async def get_device(self, deviceId :str) -> OlarmDevice | None:
        """Get a single device from api."""
        resp = await self.session.request("GET", f"{BASE_URL}devices/{deviceId}", headers=self.headers)
        match resp.status:
            case 200:
                self.connected = True
                device_data = await resp.json()
                return await self.polulate_dataclass_from_api(device_data)
            case 403:
                raise APIAuthError("Error connecting to api. Invalid username or password.")
            case 429:
                raise APIConnectionError("Error connecting to api. Too many requests.")
        return None

    async def send_action(self, deviceId :str, action: ActionId, action_id: int) -> bool:
        """Get a single device from api."""
        action_data = { "actionCmd": action, "actionNum": action_id }
        resp = await self.session.request("POST", f"{BASE_URL}devices/{deviceId}/actions", headers=self.headers, data=json.dumps(action_data))
        _LOGGER.debug("send_action %s, response %s", action, await resp.json())
        match resp.status:
            case 200:
                resp_data = await resp.json()
                if resp_data["actionStatus"] == "OK":
                    return True
                raise APIActionError(f"Olarm API error message - {resp_data}")
            case 403:
                raise APIAuthError("Error connecting to api. Invalid username or password.")
            case 429:
                raise APIConnectionError("Error connecting to api. Too many requests.")

    async def polulate_dataclass_from_api(self, device_data: dict[str, any]) -> OlarmDevice:
        # Polulate Zone data
        # Get Zone Count
        count_zones = device_data["deviceProfile"].get("zonesLimit", 0)
        count_areas = device_data["deviceProfile"].get("areasLimit", 0)

        zones = [
            AlarmZone(
                id=item + 1,
                label=device_data["deviceProfile"]["zonesLabels"][item],
                type=device_data["deviceProfile"]["zonesTypes"][item],
                status=device_data["deviceState"]["zones"][item],
                timestamp=device_data["deviceState"]["zonesStamp"][item],
            )
            for item in range(count_zones)
        ]
        areas = [
            AlarmArea(
                id=item + 1,
                label=device_data["deviceProfile"]["areasLabels"][item],
                status=device_data["deviceState"]["areas"][item],
                trigger_zones=list(map(int,device_data["deviceState"]["areasDetail"][item])),
                timestamp=device_data["deviceState"]["areasStamp"][item],
            )
            for item in range(count_areas)
        ]

        alarm_detail = AlarmDevice(
            id=device_data["deviceId"],
            label=device_data["deviceName"],
            alarm_make=device_data["deviceAlarmType"],
            alarm_make_detail=device_data["deviceAlarmTypeDetail"],
            battery=(device_data["deviceState"]["power"]["Batt"]=="1"),
            mains=(device_data["deviceState"]["power"]["AC"]=="1"),
            alarm_areas=areas,
            alarm_zones=zones)

        return OlarmDevice(
            id=device_data["deviceId"],
            label=device_data["deviceName"],
            serial_number=device_data["deviceSerial"],
            type=device_data["deviceType"],
            status=device_data["deviceStatus"],
            timezone=device_data.get("deviceTimezone"),
            firmware_version=device_data.get("deviceFirmware"),
            alarm_detail=alarm_detail)

    def get_device_unique_id(self, deviceSerial: str, device_type: DeviceType) -> str:
        """Return a unique device id."""
        if device_type == DeviceType.ALARM_SYSTEM:
            return f"{self.controller_name}_Alarm_{deviceSerial}"
        return f"{self.controller_name}_Z{deviceSerial}"

    def get_device_name(self, deviceName: str, device_type: DeviceType) -> str:
        """Return the device name."""
        if device_type == DeviceType.ALARM_SYSTEM:
            return f"{self.controller_name}_Alarm_{deviceName}"
        return f"OtherSensor_{deviceName}"

class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""

class APIActionError(Exception):
    """Exception class for action error."""
