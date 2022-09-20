import asyncio
import logging

from core.node import Node

from bluetooth_mesh import models


class Light(Node):
    """
    Adds support for simple lights
    """
    OnOffProperty = 'onoff'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def onoff(self):
        return self._get(Light.OnOffProperty)

    async def bind(self, app):
        await super().bind(app)

        # configure node
        client = app.elements[0][models.ConfigClient]
        await client.bind_app_key(
            self.unicast, net_index=0,
            element_address=self.unicast,
            app_key_index=app.app_keys[0][0],
            model=models.GenericOnOffServer)

        await asyncio.sleep(1.0)

        # get initial state
        await self.get_onoff()

    async def set_onoff_unack(self, onoff):
        self._set(Light.OnOffProperty, onoff)

        client = self._app.elements[0][models.GenericOnOffClient]
        await client.set_onoff_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            onoff, 
            send_interval=0.1)

    async def get_onoff(self):
        client = self._app.elements[0][models.GenericOnOffClient]
        state = await client.get_light_status(
            [self.unicast], 
            self._app.app_keys[0][0], 
            send_interval=0.1)
        
        result = state[self.unicast]
        if not isinstance(result, BaseException):
            self._set(Light.OnOffProperty, result['present_onoff'])

    async def set_lightness_unack(self, lightness, transition_time=0.5):
        client = self._app.elements[0][models.LightLightnessClient]
        client.set_lightness_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            lightness, 
            transition_time,
            send_interval=0.1)