# Olarm Integration for Home Assistant

[Olarm](https://www.olarm.com/) manufactures components that integrate with existing Alarm Systems, Electric Fences, Gates & Doors and CCTV Cameras, providing remote control and visibility.

[Home Assistant](https://www.home-assistant.io/) is a Open source home automation that puts local control and privacy first. Powered by a worldwide community of tinkerers and DIY enthusiasts.

This integration uses the standard Olarm provided API and Webhook functionality to provide access to your Alarm system from Home Assistant

### Current Status and Thinking

This is a early, work-in-progess build of the integration and has a base implementation of the solution
- Initial configuration will setup the API and start the update loop (currently hard coded at 15 seconds) **Please note as of yet, no devices will be added to Home Assistant**
- Options are then available for
    - Selecting devices **Due to the limits on the API, the integration will only poll devices that you enable under this option**
    - Enabling Webhooks **The integration attempts to show the correct enpoint that will be used to receive the webhook, but as you need to make the webhook available externally, you will need to figure out the correct firewall rules and external facing address for the integration**
        - The Olarm webhooks only support status updates on events related to Areas e.g.:
            - Arm
            - Disarm
            - Alarm
        - No support from Olarm currently on Zone/Devices e.g.:
            - Zone Active
            - Zone bypass
            - etc.

## Known issues

### One
There are different status' for different Alarm devices and mapping needs to be done beteween the status from Olarm and the status in Home Assistant this is currently done for my alarm type via a dictionary mapping in Python:
action_map = {"ids_x64" : {ActionId.ZONE_UNBYPASS: ActionId.ZONE_BYPASS,
                           ActionId.AREA_STAY: ActionId.AREA_STAY,
                           ActionId.AREA_SLEEP: ActionId.AREA_STAY_2}}

The code will look through this dictionary and set status, or activate status based on this mappting, before falling backk to a default, this means that the functionality works for people with the same Alarm system as me, as I get feedback it should be easy to expand this out for new device types.

### Two
Home Assistant has states for Home, Away, Night, Vaction, Custom Bypass, these do not clearly map to certain alarm devices e.g. away, partarm1, partarm2, partarm3, partarm4, so I have made a mapping according to my needs, I would like to add configuration options to allow for manual setup of the mapping in order to make the system better capable of supporting alternate needs

### Roadmap

- [x] Basic integration and foundation
- [x] Basic Webhook functionality
- [ ] Version 0.1
    - [ ] Better error handing
    - [ ] Code refactor/cleanup
    - [ ] HACs integration
    - [ ] Documentation improvement
- [ ] More config options e.g.:
    - [ ] Manual polling interval 
    - [ ] Config options to support manual device mapping between Olarm and Home Assistant status
- [ ] MQTT support (There **is a existing** MQTT end-point for Olarm and some rumours on availability, this is out of my control (right now I get authentication issues connecting), but I have been doing some early testing/playing with what is currently available)

# Thanks
This is my first attempt at a integration for Home Assistant, it's been a steep learning curve but the climd was helped by:
- Mark P - for his awesome example integrations (https://community.home-assistant.io/t/working-example-of-ha-integration/730465)
- Raine Pretorius - for a existing Olarm integration that provided inspiration that this was possible (https://github.com/rainepretorius/olarm-ha-integration)
- The maintainers of the IFTTT integration (https://next.home-assistant.io/integrations/ifttt) from where I figured out some undocumented webhook functionality