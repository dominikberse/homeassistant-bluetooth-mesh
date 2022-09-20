import json
import logging

from asyncio_mqtt.client import Client, MqttError
from contextlib import AsyncExitStack

from core.tasks import TaskContextManager
from core.node import Node

from mqtt.modules import light


MQTT_MODULES = {
    'light': light.LightModule,
}


class HassMqtt:
    """
    Provides home assistant specific MQTT functionality

    Manages a set of modules for specific device types and 
    manages tasks to receive and handle incoming messages.
    """
    def __init__(self, config, nodes):
        self._config = config
        self._nodes = nodes
        self._modules = {}
        self._paths = {}

        self._client = Client(self._config.require('mqtt.broker'))
        self._topic = config.optional('mqtt.topic', 'mqtt_mesh')

        # initialize modules
        for name, constructor in MQTT_MODULES.items():
            self._modules[name] = constructor(self)

    @property
    def client(self):
        return self._client

    @property
    def topic(self):
        return self._topic

    def node_topic(self, component, node):
        """
        Return base topic for a specific node
        """
        if isinstance(node, Node):
            node = node.hass.require('id')

        return f'homeassistant/{component}/{self._topic}/{node}'

    def filtered_messages(self, component, node, topic='#'):
        """
        Shorthand to get messages for a specific node
        """
        return self._client.filtered_messages(
            f'{self.node_topic(component, node)}/{topic}')

    async def publish(self, component, node, topic, message, **kwargs):
        """
        Send a state update for a specific nde
        """
        await self._client.publish(
            f'{self.node_topic(component, node)}/{topic}', 
            json.dumps(message).encode(), **kwargs)

    async def run(self, app):
        async with AsyncExitStack() as stack:
            tasks = await stack.enter_async_context(TaskContextManager())

            # connect to MQTT broker
            await stack.enter_async_context(self._client)

            # spawn tasks for every node
            for node in self._nodes.all():
                module = self._modules.get(node.type)

                if module is None:
                    logging.warning(f'No MQTT module for node {node}')
                    return

                tasks.spawn(module.listen(node))
                # send node configuration for MQTT discovery
                await module.config(node)
            
            # global subscription to messages
            await self._client.subscribe("homeassistant/#")

            # wait for all tasks
            await tasks.gather()
