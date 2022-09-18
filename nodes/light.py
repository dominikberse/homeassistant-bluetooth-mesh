import asyncio

from core.node import Node

from bluetooth_mesh import models


class Light(Node):
    """
    Adds support for simple lights
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._onoff = False

    @property
    def onoff(self):
        return self._onoff

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
        client = app.elements[0][models.GenericOnOffClient]
        state = await client.get_light_status(
            [self.unicast], 
            self._app.app_keys[0][0], 
            send_interval=0.1)
        
        result = state[self.unicast]
        if not isinstance(result, BaseException):
            self._onoff = result['present_onoff']

    async def set_onoff_unack(self, onoff):
        client = self._app.elements[0][models.GenericOnOffClient]
        await client.set_onoff_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            onoff, 
            send_interval=0.1)
        self._onoff = onoff

    async def set_lightness_unack(self, lightness, transition_time=0.5):
        client = self._app.elements[0][models.LightLightnessClient]
        client.set_lightness_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            lightness, 
            transition_time,
            send_interval=0.1)