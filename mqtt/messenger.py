import json
import logging

from asyncio_mqtt.client import Client, MqttError

from mqtt.modules import light


MQTT_MODULES = {
    'light': light.LightModule,
}


class Messenger:
    def __init__(self, config, nodes):
        self._config = config
        self._nodes = nodes
        self._modules = {}
        self._paths = {}

        self._topic = config.optional('mqtt.topic', 'mqtt_mesh')

        # initialize modules
        for name, constructor in MQTT_MODULES.items():
            self._modules[name] = constructor(self)

        for node in self._nodes.all():
            # gives the unique object id used in Home Assistant
            path = node.hass.optional('id')
            # retrieve a compatible module for this node type
            module = self._modules.get(node.type)

            if path and module:
                logging.info(f'Node {node} registered for MQTT')
                self._paths[path] = (node, module)
            else:
                logging.warning(f'Node {node} not accessible over MQTT')

    async def publish(self, node, path, client, topic, message):
        await client.publish(
            f'homeassistant/{node.type}/{self._topic}/{path}/{topic}', 
            json.dumps(message).encode())


    async def run(self, app):
        async with Client(self._config.require('mqtt.broker')) as client:

            # send configuration messages for all nodes
            for path, (node, module) in self._paths.items():
                message = module.config(node)
                await self.publish(node, path, client, 'config', {
                    '~': f'homeassistant/{node.type}/{self._topic}/{path}',
                    **message
                })
                await self.publish(node, path, client, 'state', module.state(node))

            # listen for node messages
            async with client.filtered_messages(f'homeassistant/+/{self._topic}/#') as messages:
                await client.subscribe("homeassistant/#")
                async for message in messages:
                    _, nodetype, _, path, command = message.topic.split('/')
                    content = json.loads(message.payload.decode())

                    logging.info(f'Received message on {message.topic}:\n{content}')

                    try:
                        node, module = self._paths[path]
                        response = await module.handle(node, command, content)

                        if response:
                            await self.publish(node, path, client, 'state', response)
                    except:
                        logging.exception('Failed to handle message')

