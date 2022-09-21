import asyncio
import logging

from .generic import Generic

from bluetooth_mesh import models


class Light(Generic):
    """
    Adds support for light nodes 
    """
    OnOffProperty = 'onoff'
    BrightnessProperty = 'brightness'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def onoff(self):
        return self._get(Light.OnOffProperty)

    @property
    def brightness(self):
        return self._get(Light.BrightnessProperty)

    def supports(self, property):
        if property == Light.OnOffProperty:
            return True
        if property == Light.BrightnessProperty:
            return self._bound(models.LightLightnessServer)

    async def turn_on(self):
        if self._bound(models.LightLightnessServer):
            await self.set_lightness_unack(100)
        await self.set_onoff_unack(True)

    async def turn_off(self):
        if self._bound(models.LightLightnessServer):
            await self.set_lightness_unack(0)
        await self.set_onoff_unack(False)

    async def bind(self, app):
        await super().bind(app)

        # bind available node models to application
        if await self.bind_model(models.GenericOnOffServer):
            await self.get_onoff()
        if await self.bind_model(models.LightLightnessServer):
            await self.get_lightness()

        # node is now available
        self.ready.set()

    async def set_onoff_unack(self, onoff):
        self._set(Light.OnOffProperty, onoff)

        client = self._app.elements[0][models.GenericOnOffClient]
        await client.set_onoff_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            onoff)

    async def get_onoff(self):
        client = self._app.elements[0][models.GenericOnOffClient]
        state = await client.get_light_status(
            [self.unicast], 
            self._app.app_keys[0][0])
        
        result = state[self.unicast]
        if result is None:
            logging.warn(f'Received invalid result {state}')
        elif not isinstance(result, BaseException):
            self._set(Light.OnOffProperty, result['present_onoff'])

    async def set_lightness_unack(self, lightness, transition_time=0.5):
        self._set(Light.OnOffProperty, lightness > 0)

        client = self._app.elements[0][models.LightLightnessClient]
        await client.set_lightness_unack(
            self.unicast, 
            self._app.app_keys[0][0], 
            lightness, 
            transition_time)

    async def get_lightness(self):
        client = self._app.elements[0][models.LightLightnessClient]
        state = await client.get_lightness(
            [self.unicast], 
            self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warn(f'Received invalid result {state}')
        elif not isinstance(result, BaseException):
            self._set(Light.BrightnessProperty, result['present_lightness'])
