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
        return 'light'

    async def config(self, node):
        await node.ready.wait()

        message = {
            '~': self._messenger.node_topic(self.component, node),
            "name": node.hass.optional('name'),
            "unique_id": node.hass.require('id'),
            "object_id": node.hass.require('id'),
            "cmd_t": "~/set",
            "stat_t": "~/state",
            "schema": "json",
            "brightness": False
        }

        if node.supports(Light.BrightnessProperty):
            message['bri_cmd_t'] = '~/bri_set'
            message['bri_stat_t'] = '~/bri_state'
            message['bri_scl'] = 100
            message['brightness'] = True

        await self._messenger.publish(self.component, node, 'config', message)

    async def _mqtt_set(self, node, payload):
        if payload['state'] == 'ON':
            await node.turn_on()
        if payload['state'] == 'OFF':
            await node.turn_off()
        if 'brightness' in payload:
            await node.set_lightness_unack(payload['brightness'])

    async def _mqtt_bri_set(self, node, payload):
        print(payload)

    async def _node_onoff(self, node, onoff):
        await self._messenger.publish(self.component, node, 'state', {
            'state': 'ON' if node.onoff else 'OFF'
        }, retain=True)

    async def _node_brightness(self, node, brightness):
        await self._messenger.publish(self.component, node, 'state', {
            'brightness': node.brightness
        }, retain=True)
