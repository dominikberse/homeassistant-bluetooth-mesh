"""Node Light Module"""
import logging

from bluetooth_mesh import models

from .generic import Generic


class Light(Generic):
    """
    Generic interface for light nodes

    Tracks the available feature of the light. Currently supports
        - GenericOnOffServer
            - turn on and off
        - LightLightnessServer
            - set brightness
        - LightCTLServer
            - set color temperature

    For now only a single element is supported.
    """

    OnOffProperty = "onoff"
    BrightnessProperty = "brightness"
    TemperatureProperty = "temperature"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._features = set()

    def supports(self, property):
        return property in self._features

    async def turn_on(self):
        await self.set_onoff_unack(True, transition_time=0.5)

    async def turn_off(self):
        await self.set_onoff_unack(False, transition_time=0.5)

    async def set_brightness(self, brightness):
        if self._is_model_bound(models.LightLightnessServer):
            await self.set_lightness_unack(brightness, transition_time=0.5)
        elif self._is_model_bound(models.LightCTLServer):
            await self.set_ctl_unack(brightness=brightness)

    async def set_kelvin(self, temperature):
        if self._is_model_bound(models.LightCTLServer):
            await self.set_ctl_unack(temperature)

    async def set_mireds(self, temperature):
        if self._is_model_bound(models.LightCTLServer):
            await self.set_ctl_unack(1000000 // temperature)

    async def bind(self, app):
        await super().bind(app)

        if await self.bind_model(models.GenericOnOffServer):
            self._features.add(Light.OnOffProperty)
            await self.get_onoff()

        if await self.bind_model(models.LightLightnessServer):
            self._features.add(Light.OnOffProperty)
            self._features.add(Light.BrightnessProperty)
            await self.get_lightness()

        if await self.bind_model(models.LightCTLServer):
            self._features.add(Light.TemperatureProperty)
            self._features.add(Light.BrightnessProperty)
            await self.get_ctl()

    async def set_onoff_unack(self, onoff, **kwargs):
        self.notify(Light.OnOffProperty, onoff)

        client = self._app.elements[0][models.GenericOnOffClient]
        await client.set_onoff_unack(self.unicast, self._app.app_keys[0][0], onoff, **kwargs)

    async def get_onoff(self):
        client = self._app.elements[0][models.GenericOnOffClient]
        state = await client.get_light_status([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            self.notify(Light.OnOffProperty, result["present_onoff"])

    async def set_lightness_unack(self, lightness, **kwargs):
        self.notify(Light.BrightnessProperty, lightness)

        client = self._app.elements[0][models.LightLightnessClient]
        await client.set_lightness_unack(self.unicast, self._app.app_keys[0][0], lightness, **kwargs)

    async def get_lightness(self):
        client = self._app.elements[0][models.LightLightnessClient]
        state = await client.get_lightness([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            self.notify(Light.BrightnessProperty, result["present_lightness"])

    async def set_ctl_unack(self, temperature=None, brightness=None, **kwargs):
        if temperature:
            self.notify(Light.TemperatureProperty, temperature)
        else:
            temperature = self.retained(Light.TemperatureProperty, 255)
        if brightness:
            self.notify(Light.BrightnessProperty, temperature)
        else:
            brightness = self.retained(Light.BrightnessProperty, 100)

        client = self._app.elements[0][models.LightCTLClient]
        await client.set_ctl_unack(self.unicast, self._app.app_keys[0][0], temperature, brightness, **kwargs)

    async def get_ctl(self):
        client = self._app.elements[0][models.LightCTLClient]
        state = await client.get_ctl([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            print(result)
