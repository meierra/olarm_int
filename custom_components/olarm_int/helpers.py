from .const import OlarmConf, AlarmConf, ZoneConf, AreaConf, OlarmDevice

async def get_entity_configuration(olarm_devices = list[OlarmDevice]) -> dict[str, OlarmConf]:
    """Return the entity configuration for the devices."""
    # Return a list of entity configuration data
    return {device.id : OlarmConf(
        id=device.id,
        label=device.label,
        serial_number=device.serial_number,
        type=device.type,
        firmware_version=device.firmware_version,
        alarm_conf=AlarmConf(
            id=device.alarm_detail.id,
            label=device.alarm_detail.label,
            serial_number=device.serial_number,
            alarm_make=device.alarm_detail.alarm_make,
            alarm_make_detail=device.alarm_detail.alarm_make_detail,
            zone_conf=[ZoneConf(
                id=zone.id,
                label=zone.label,
                type=zone.type
                ) for zone in device.alarm_detail.alarm_zones],
            area_conf=[AreaConf(
                id=area.id,
                label=area.label
                ) for area in device.alarm_detail.alarm_areas]
        )
    ) for device in olarm_devices}
