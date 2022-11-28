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
- (done) Dockerize application
- Provide as HACS integration
- Extend README

## (Hopefully) easy setup

The repository provides a docker container, that will setup BlueZ with mesh support and run the gateway. However, due to the use of the bluetooth hardware, I can not guarantee that it is working everywhere. For now I tested it on a Raspberry Pi 4 with Raspberry Pi OS 2022-09-22 (bullseye). If you are able to run it on other hardware just notify me as I will try to keep track of compatible setups.

- If you have a blank Raspberry Pi you need to install docker and git first.

- Clone the repository and create a `config.yaml` file under `docker/config/`:

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

- **It is very important to disable bluetooth on the host system!** This is neccessary, because the bluetooth-mesh service needs exclusive access to the bluetooth device.

```
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth
```

- Start the container using docker compose and grab a coffee. This took one and a half hours for me to complete on a Raspberry Pi 4. It might seem stuck when compiling numpy, but this actually takes half an hour.

```
docker compose build
docker compose up -d
```

Note that the container currently runs `/bin/bash` in the foreground, because the gateway exits if no nodes are provisioned. This will change in the future (I plan on implementing a simple web interface for provisioning). Also, there might be an error message on the very first startup. It should be gone on the second try.

### Using the command line within docker

Since the web interface is not yet available, you need to use the command line to scan and provision devices. With the container running, you can access the command line inside the docker container from the host system using:

```
docker compose exec app /bin/bash
```

From there, it might be neccessary to stop the running python process.

```
ps -ef | grep gateway
kill <PID>
```

I placed the configuration files in `/config`, so you need to add `--basedir /config` to every command. So for example the scan command would look like this:

```
python3 gateway.py --basedir /config scan
```

Once you are done, switch back to the host system (simply `exit`) and restart the container for the changes to take effect.

```
docker compose restart
```

## Manual setup

If you do not want to use the docker image or for some reason it is not compatible, you can try to setup everything manually. However, this can be a little tricky.

After cloning the repository, the easy part is to install the Python requirements using `pip3 install -r requirements.txt` (probably inside a virtual environment). The hard part is the get the `bluetooth-mesh` service running. This usually requires to build BlueZ from scratch and replace the available BlueZ installation. Have a look at the docker installation scripts, they should be a good starting point on what you need to do.

Once you get it running, it might be neccessary to stop the default `bluetooth` service first and ensure that your bluetooth device (probably `hci0`) is not locked. Place the configuration file (see docker installation) inside the main folder and name it `config.yaml`.

With that available, you should be able to run the application from the `gateway` folder (try `python3 gateway.py scan` first).

### Running the gateway

Calling `python3 gateway.py` without further arguments will start the MQTT gateway and keep it alive. All provisioned devices should be discovered by Home Assistant and become available. If not, check the Home Assistant MQTT integration. If no devices are provisioned, the application will exit.

## Provisioning a device

**Make sure you know how to reset your device in case something goes wrong here.** Also it might be neccessary to edit the `store.yaml` by hand in case something fails.

_Remember that you need to add the `--basedir /config` switch after `gateway.py` if you are using the command line within docker._

1. Scan for unprovisioned devices with `python3 gateway.py scan`.
1. Create an entry for the device(s) you want to add in the `config.yaml`.
1. Provision the device with `python3 gateway.py prov --uuid <uuid> add`.
1. Configure the device with `python3 gateway.py prov --uuid <uuid> config`.
   _Do not skip this step, otherwise the device is not part of the application network and it will not respond properly._

- To list all provisioned devices use `python3 gateway.py list`.
- You can remove and reset a device with `python3 gateway.py prov --uuid <uuid> reset`.
