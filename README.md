# Bluetooth Mesh for Home Assistant

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
  [username: <username>]
  [password: <password>]
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

From there, it might be neccessary to stop the running python process (`ps`/`pkill` are not installed in the image):

```
kill $(grep -l "gateway.py" /proc/[0-9]*/cmdline | cut -d/ -f3)
```

I placed the configuration files in `/config`, so you need to add `--basedir /config` to every command. So for example the scan command would look like this:

```
python3 gateway.py --basedir /config scan
```

Once you are done, switch back to the host system (simply `exit`) and recreate the container for the changes to take effect.
Prefer recreating over `docker compose restart`: images built before the `entrypoint.sh` fix leave a stale `/run/dbus/pid` behind, and D-Bus then fails to start after a restart.

```
docker compose up -d --force-recreate
```

### Persistent state (important)

The container keeps state that **must survive** recreating the container or rebuilding the image. `docker-compose.yaml` mounts it from the `docker/` folder:

| Host path (`docker/…`) | Container path | Content |
|---|---|---|
| `config/` | `/config` | `config.yaml` (your settings) and `store.yaml` (provisioned nodes, keys, addresses) |
| `mesh/` | `/var/lib/bluetooth/mesh` | `bluetooth-meshd` node state: **device keys of the provisioned devices**, sequence numbers, replay protection |
| `token/` | `/root/.cache/bluetooth-mesh` | attach token of the gateway's local mesh node |
| `machine-id` (file) | `/etc/machine-id` (read only) | pins the identity of the gateway's local mesh node |

Why this matters:

- **Device keys only exist in `mesh/`.** `store.yaml` does not contain them. If `mesh/` is lost, the gateway can no longer configure the devices (binding fails with a composition data timeout and nothing is published to MQTT). The only fix is to factory-reset every device and provision it again.
- **The local node UUID is derived from `/etc/machine-id`** (`uuid5(machine-id, "/org/hass/mesh")`). Every newly built image has a different machine-id, so without the pinned file each rebuild creates a new local node without the device keys. Create the file once before the first start, for example `cat /proc/sys/kernel/random/uuid | tr -d - > docker/machine-id`, and never change it.
- **Sequence numbers must never go backwards.** Devices drop messages from address `0001` whose sequence number is lower than one they have already seen. Never delete `mesh/` while devices are still provisioned.
- The directories are created by root inside the container. Edit them via `docker compose exec app …` or a root shell, not as a normal user.
- Docker bind mounts don't work on paths containing `:` (for example GVFS/SMB mounts like `smb-share:server=…`), and dockerd may not be able to read such mounts at all. In that case keep the state in a local directory (for example `~/hass-ble-mesh/`) and adjust the volume paths.

### Building and running a prebuilt image

The image is built from the **local source tree**: the build context is the repository root (`context: ..` in `docker-compose.yaml`), so local changes to `gateway/` end up in the image. Windows line endings (CRLF) in the scripts are stripped during the build.

Build and push to your own registry (from the repository root):

```
docker build -f docker/Dockerfile -t <registry>/homeassistant-bluetooth-mesh:latest .
docker push <registry>/homeassistant-bluetooth-mesh:latest
```

A registry served over plain HTTP must be listed under `insecure-registries` in `/etc/docker/daemon.json` on every host that pushes or pulls (needs root, then restart docker).

Run the image without compose (equivalent to `docker-compose.yaml`):

```
docker run -d -t --name hass-ble-mesh --privileged --network host --restart unless-stopped \
  -v ~/hass-ble-mesh/config:/config \
  -v ~/hass-ble-mesh/mesh:/var/lib/bluetooth/mesh \
  -v ~/hass-ble-mesh/token:/root/.cache/bluetooth-mesh \
  -v ~/hass-ble-mesh/machine-id:/etc/machine-id:ro \
  <registry>/homeassistant-bluetooth-mesh:latest
```

To apply config changes or a new image, recreate the container (`docker rm -f hass-ble-mesh`, then the `docker run` above). The base image is `python:3.10-bookworm`; Debian bullseye is end-of-life and its package mirrors no longer work.

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
1. Recreate the container (or restart the gateway) so the new device is bridged to MQTT.

The gateway publishes a retained MQTT discovery message per light on `homeassistant/light/<node_id>/<id>/config`, including a `device` block, so each light appears in Home Assistant under the MQTT integration's devices.

- To list all provisioned devices use `python3 gateway.py prov list`.
- You can remove and reset a device with `python3 gateway.py prov --uuid <uuid> reset`.
