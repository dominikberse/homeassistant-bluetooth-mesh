"""MQTT Light Bridge"""
from mesh.nodes.light import (
    BLE_MESH_MAX_LIGHTNESS,
    BLE_MESH_MAX_TEMPERATURE,
    BLE_MESH_MAX_MIRED,
    BLE_MESH_MIN_MIRED,
    Light,
)
from mqtt.bridge import HassMqttBridge


class GenericLightBridge(HassMqttBridge):
    """
    Generic bridge for lights
    """

    def __init__(self, *args, **kwargs):
        self.brightness_min = 0
        self.brightness_max = 100
        super().__init__(*args, **kwargs)

    @property
    def component(self):
        return "light"

    async def config(self, node):
        color_modes = set()

        # Brightness Config
        brightness_min = node.config.optional("brightness_min")
        brightness_max = node.config.optional("brightness_max")
        if brightness_min:
            self.brightness_min = brightness_min
        if brightness_max:
            self.brightness_max = brightness_max

        message = {
            "dev": {
                "ids": [node.config.require("id")],
                "name": f"{node.config.optional('name')}-{node.config.require('id')}",
                "sw": "1.0",
                "mf": "BLE MESH",
                "mdl": node.config.optional("type"),
            },
            "~": self._messenger.node_topic(self.component, node),
            "name": node.config.optional("name"),
            "unique_id": node.config.require("id"),
            "object_id": node.config.require("id"),
            "command_topic": "~/set",
            "state_topic": "~/state",
            "schema": "json",
        }

        if node.supports(Light.BrightnessProperty):
            message["brightness_scale"] = 100  # brightness_max // 100 ?
            message["brightness"] = True

        if node.supports(Light.TemperatureProperty):
            color_modes.add("color_temp")
            # convert from Kelvin to mireds
            # TODO: look up max/min values from device
            message["min_mireds"] = node.config.optional("mireds_min", BLE_MESH_MIN_MIRED)
            message["max_mireds"] = node.config.optional("mireds_max", BLE_MESH_MAX_MIRED)

        if color_modes:
            message["color_mode"] = True
            message["supported_color_modes"] = list(color_modes)

        await self._messenger.publish(self.component, node, "config", message, retain=True)

    async def _state(self, node, onoff):
        """
        Send a generic state message covering the nodes full state

        If the light is on, all properties are set to their retained state.
        If the light is off, properties are not passed at all.
        """
        message = {"state": "ON" if onoff else "OFF"}

        if onoff and node.supports(Light.BrightnessProperty):
            message["brightness"] = (
                int(node.retained(Light.BrightnessProperty, BLE_MESH_MAX_LIGHTNESS)) / self.brightness_max * 100
            )

        if onoff and node.supports(Light.TemperatureProperty):
            message["color_temp"] = node.retained(Light.TemperatureProperty, BLE_MESH_MAX_TEMPERATURE)

        await self._messenger.publish(self.component, node, "state", message, retain=True)

    async def _mqtt_set(self, node, payload):
        if "color_temp" in payload:
            await node.mireds_to_kelvin(payload["color_temp"], ack=node.config.optional("ack"),is_tuya=node.config.optional("tuya_temp",False))

        if "brightness" in payload:
            brightness = int(payload["brightness"])
            desired_brightness = int(brightness * self.brightness_max / 100)
            if desired_brightness > BLE_MESH_MAX_LIGHTNESS:
                desired_brightness = BLE_MESH_MAX_LIGHTNESS
            await node.set_brightness(brightness=desired_brightness, ack=node.config.optional("ack"))

        if payload.get("state") == "ON":
            await node.turn_on(ack=node.config.optional("ack"))

        if payload.get("state") == "OFF":
            await node.turn_off(ack=node.config.optional("ack"))

    async def _notify_onoff(self, node, onoff):
        await self._state(node, onoff)

    async def _notify_brightness(self, node, brightness):
        await self._state(node, brightness > 0)
