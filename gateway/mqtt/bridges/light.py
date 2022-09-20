from mqtt.bridge import HassMqttBridge


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
        await self._messenger.publish(self.component, node, 'config', {
            '~': self._messenger.node_topic(self.component, node),
            "name": node.hass.optional('name'),
            "unique_id": node.hass.require('id'),
            "object_id": node.hass.require('id'),
            "cmd_t": "~/set",
            "stat_t": "~/state",
            "schema": "json",
            "brightness": True
        })

    async def state(self, node):
        await self._messenger.publish(self.component, node, 'state', {
            'state': 'ON' if node.onoff else 'OFF'
        }, retain=True)

    async def _mqtt_set(self, node, payload):
        await node.set_onoff_unack(payload['state'] == 'ON')

    async def _node_onoff(self, node, onoff):
        await self.state(node)
