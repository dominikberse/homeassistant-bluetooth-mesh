# homeassistant-bluetooth-mesh

This project aims to integrate Bluetooth Mesh devices into Home Assistant directly.

The project is in a development state. The current approach is to use the Home Assistant MQTT integration on the Home Assistant side. Then for every Bluetooth Mesh device type a _bridge_ class is implemented, that maps the node's functionality to a Home Assistant device class.

## Poject State

The basic requirements for this setup are already implemented:

- MQTT integration using `asyncio_mqtt`
- Bluetooth Mesh integration using `bluetooth_mesh`
- Mechanisms to allow easy communication between both ends

Additionally a command line interface for easy scanning and provisioning is available.

### Devices

Currently the following bridges are implemented:

- _Generic Light Bridge_: Maps a basic Bluetooth Mesh light to a Home Assistant Light. Supports on / off, brightness and color temperature. Since I do not have Bluetooth Mesh RGB Leds at hand, I do not plan on supporting them. The implementation should basically follow the color temperature though.

### Roadmap

- Check relay setup
- Dockerize application
- Provide as HACS integration
- Extend README

## Setup

Setting up the application can be tricky. The easy part is to install the Python requirements using `pip3 install -r requirements.txt`, the hard part is the setup BlueZ with `meshctl` support. Additionally create a `config.yaml` file inside the main folder, which looks like this:

```
mqtt:
  broker: <mqtt_broker>
  node_id: mqtt_mesh
mesh:
  <hass_device_id>:
    uuid: <bluetooth_mesh_device_uuid>
    name: <hass_device_name>
    type: light             # thats it for now
    [relay: <true|false>]   # whether this node should act as relay
  ...
```

With that available, you should be able to run the application from the `gateway` folder (best to try `python3 gateway.py scan` first).

### Provisioning a device

**Make sure you know how to reset your device in case something goes wrong here.** Also it might be neccessary to edit the `store.yaml` by hand in case something fails.

The command line interface is still a little messy, but the workflow to add a device is as follows:

- `python3 gateway.py scan`: Scan for unprovisioned devices
- `python3 gateway.py prov add <uuid>`: Provision a device _or_
- `python3 gateway.py prov add`: Provision all device from config file
- `python3 gateway.py prov config <uuid>`: Configure device (set application keys) to work with this gateway

Now:

- `python3 gateway.py list`: Should include the newly provisioned devices

To remove a device use:

- `python3 gateway.py prov reset <uuid>`

### Running the gateway

Calling `python3 gateway.py` without further arguments will start the MQTT gateway and keep it alive. All provisioned devices should be discovered by Home Assistant and become available. If not, check the Home Assistant MQTT integration.
