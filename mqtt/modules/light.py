import asyncio
import logging

from mqtt.module import MessengerModule


class LightModule(MessengerModule):
    """
    Home Assistant compatible MQTT module for lights
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def config(self, node):
        return {
            "name": node.hass.optional('name'),
            "unique_id": node.hass.require('id'),
            "object_id": node.hass.require('id'),
            "cmd_t": "~/set",
            "stat_t": "~/state",
            "schema": "json",
            "brightness": True
        }

    def state(self, node):
        return {
            'state': 'ON' if node.onoff else 'OFF'
        }

    async def handle(self, node, command, payload):
        """
        Handle a specific MQTT command
        """
        if command == 'set':
            await node.set_onoff_unack(payload['state'] == 'ON')
            return self.state(node)
