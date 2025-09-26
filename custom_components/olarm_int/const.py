"""Constants for the Olarm Integration integration."""

from enum import StrEnum, IntEnum
from dataclasses import dataclass
from typing import Final

DOMAIN = "olarm_int"


class DeviceType(StrEnum):
    """Device types."""
    TEMP_SENSOR = "temp_sensor"
    DOOR_SENSOR = "door_sensor"
    ALARM_AREA = "alarm_area"
    ALARM_SYSTEM = "alarm_system"
    OTHER = "other"

class ZoneType(IntEnum):
    """Zone types."""
    PIR_INDOOR = 20
    PIR_OUTDOOR = 21
    DOOR = 10
    WINDOW = 11
    NOT_APPLICABLE = 0
    NOT_USED = 90
    PANIC_BOTTON = 50
    PANIC_ZONE = 51

class ZoneStatus(StrEnum):
    """Device status."""
    CLOSED = "closed"
    ACTIVE = "active"
    BYPASSED = "bypassed"

class AreaStatus(StrEnum):
    """Device status."""
    # Alarm states are
    NOT_READY = "notready"
    DISARMED = "disarm"
    ARMED = "arm"
    SLEEP = "sleep"
    STAY = "stay"
    ALARM = "alarm"
    FIRE = "fire"
    EMERGENCY = "emergency"
    COUNTDOWN = "countdown"


# @dataclass
# class CoordAlarmZone:
#     """Alarm Zone class."""
#     id: int
#     label: str
#     identifier: {tuple[str, str]}
#     via_device: tuple[str, str] | None = None
#     timestamp: float | None = None

# @dataclass
# class CoordAlarmArea:
#     """Alarm Area class."""
#     id: str
#     label: str
#     identifier: {tuple[str, str]}
#     via_device: tuple[str, str] | None = None

# @dataclass
# class CoordAlarmDevice:
#     """Device Type Info class."""
#     id: str
#     label: str
#     alarm_make: str
#     identifier: {tuple[str, str]}
#     via_device: tuple[str, str] | None = None
#     alarm_make_detail: str | None = None


# @dataclass
# class CoordOlarmDevice:
#     """Olarm Device class."""
#     id: str
#     label: str
#     serial_number: str
#     type: str
#     identifier: {tuple[str, str]}
#     via_device: tuple[str, str] | None = None

### API Data Classes ###
@dataclass
class AlarmZone:
    """Alarm Zone class."""
    id: int
    label: str
    type: int
    status: str
    timestamp: float | None = None

@dataclass
class AlarmArea:
    """Alarm Area class."""
    id: str
    label: str
    status: str | None = None
    trigger_zones: list[int] | None = None
    timestamp: float | None = None

@dataclass
class AlarmDevice:
    """Device Type Info class."""
    id: str
    label: str
    alarm_make: str
    alarm_make_detail: str | None = None
    battery: bool | None = None
    mains: bool | None = None
    alarm_areas: list[AlarmArea] | None = None
    alarm_zones: list[AlarmZone] | None = None

@dataclass
class OlarmDevice:
    """Olarm Device class."""
    id: str
    label: str
    serial_number: str
    type: DeviceType
    status: str | None = None # Offline, Online, Problem
    timezone: str | None = None
    firmware_version: str | None = None
    alarm_detail: AlarmDevice | None = None

### coordinator Data Classes ###
@dataclass
class ZoneState:
    """Hold the state of a zone device."""
    status: str
    timestamp: float | None = None

@dataclass
class AreaState:
    """Hold the state of an alarm area."""
    status: str
    trigger_zones: list[int] | None = None
    timestamp: float | None = None

@dataclass
class AlarmState:
    """Hold the state of an alarm device."""
    zones: dict[int, ZoneState] | None = None
    areas: dict[int, AreaState] | None = None
    battery_ok: bool | None = None
    ac_ok: bool | None = None

@dataclass
class OlarmState:
    """Hold the state of an olarm device."""
    firmware_version: str | None = None
    status: str | None = None # Offline, Online, Problem
    timezone: str | None = None
    alarm: AlarmState | None = None

@dataclass
class ZoneConf:
    """Hold the config of a zone device."""
    id: int
    label: str
    type: int

@dataclass
class AreaConf:
    """Hold the config of an alarm area."""
    id: str
    label: str

@dataclass
class AlarmConf:
    """Hold the config of an alarm device."""
    id: str
    label: str
    serial_number: str
    alarm_make: str
    alarm_make_detail: str
    zone_conf: list[ZoneConf] | None = None
    area_conf: list[AreaConf] | None = None

@dataclass
class OlarmConf:
    """Hold the config of an olarm device."""
    id: str
    label: str
    serial_number: str
    type: str
    firmware_version: str
    alarm_conf: AlarmConf | None = None

### Constants for the API ###
BASE_URL: Final = "https://apiv4.olarm.co/api/v4/"
DEFAULT_SCAN_INTERVAL = 15  # in seconds
OLARM_DIGEST_ALG: Final = 'sha1'
OLARM_DIGEST_HEADER: Final = "x-olarm-signature"

### Constants for config flow ###
CONF_WEBHOOK_SECRET: Final = "webhook_secret"

### Constants for options flow ###
CONF_SELECTED: Final = "selected"
CONF_WEBHOOK_ENABLED: Final = "webhook_enabled"

### Map alarm make to HASS device class ###
ALARM_DEVICE_TO_HASS = {
    "ids_x64": "IDXControlPanel"
    }


'''
["area-disarm", "area-stay", "area-sleep", "area-arm", "area-part-arm-{partNumber}", "zone-bypass", "zone-unbypass"]
["pgm-open", "pgm-close", "pgm-pulse", "ukey-activate"] - only if alarm system support PGMs / Utility Keys
["max-io-open", "max-io-close", "max-io-pulse"] - only Olarm MAX support IOs
'''

class ActionId(StrEnum):
    """Action Ids from Olarm API."""
    ZONE_BYPASS = "zone-bypass"
    ZONE_UNBYPASS = "zone-unbypass"
    AREA_DISARM = "area-disarm"
    AREA_STAY = "area-stay"
    AREA_STAY_2 = "area-stay-2"
    AREA_STAY_3 = "area-stay-3"
    AREA_STAY_4 = "area-stay-4"
    AREA_SLEEP = "area-sleep"
    AREA_ARM = "area-arm"
    AREA_PART_ARM_1 = "area-part-arm-1"
    AREA_PART_ARM_2 = "area-part-arm-2"
    AREA_PART_ARM_3 = "area-part-arm-3"
    AREA_PART_ARM_4 = "area-part-arm-4"


### Map Olarm api actions to alarm types ###
action_map = {"ids_x64" : {ActionId.ZONE_UNBYPASS: ActionId.ZONE_BYPASS,
                           ActionId.AREA_STAY: ActionId.AREA_STAY,
                           ActionId.AREA_SLEEP: ActionId.AREA_STAY_2}}


class WebHookActions(StrEnum):
    """Webhook Actions from Olarm API."""
    ZONE_ALARM = "zone_alarm"
    AREA = "area"

class WebHookStates(StrEnum):
    DISARMED = "disarm"
    ALARM = "alarm"
    STAYARM1 = "stayarm1"
    STAYARM2 = "stayarm2"
    STAYARM3 = "stayarm3"
    STAYARM4 = "stayarm4"
