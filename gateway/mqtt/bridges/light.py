from mqtt.bridge import HassMqttBridge
from mesh.nodes.light import Light


class GenericLightBridge(HassMqttBridge):
    """
    Generic bridge for lights
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def component(self):
        return "light"

    async def config(self, node):
        node_id = node.config.require("id")
        message = {
            "~": self._messenger.node_topic(self.component, node),
            "name": None,
            "unique_id": node_id,
            "command_topic": "~/set",
            "state_topic": "~/state",
            "schema": "json",
            "device": {
                "identifiers": [f"ble_mesh_{node.uuid}"],
                "name": node.config.optional("name") or node_id,
                "manufacturer": "Bluetooth Mesh",
            },
        }

        # Home Assistant expects supported_color_modes (legacy 'brightness'/'color_mode' flags were removed)
        if node.supports(Light.TemperatureProperty):
            message["supported_color_modes"] = ["color_temp"]
            message["brightness_scale"] = 50
        elif node.supports(Light.BrightnessProperty):
            message["supported_color_modes"] = ["brightness"]
            message["brightness_scale"] = 50
        else:
            message["supported_color_modes"] = ["onoff"]

        # retain, so Home Assistant rediscovers the light after its own restart
        await self._messenger.publish(self.component, node, "config", message, retain=True)

    async def _state(self, node, onoff):
        """
        Send a generic state message covering the nodes full state

        If the light is on, all properties are set to their retained state.
        If the light is off, properties are not passed at all.
        """
        message = {"state": "ON" if onoff else "OFF"}

        if onoff and node.supports(Light.BrightnessProperty):
            message["brightness"] = node.retained(Light.BrightnessProperty, 100)
        if onoff and node.supports(Light.TemperatureProperty):
            message["color_temp"] = node.retained(Light.TemperatureProperty, 100)
            message["color_mode"] = "color_temp"

        await self._messenger.publish(self.component, node, "state", message, retain=True)

    async def _mqtt_set(self, node, payload):
        if "color_temp" in payload:
            await node.set_mireds(payload["color_temp"])
        if "brightness" in payload:
            await node.set_brightness(payload["brightness"])
        if payload.get("state") == "ON":
            await node.turn_on()
        if payload.get("state") == "OFF":
            await node.turn_off()

    async def _notify_onoff(self, node, onoff):
        await self._state(node, onoff)

    async def _notify_brightness(self, node, brightness):
        await self._state(node, brightness > 0)
