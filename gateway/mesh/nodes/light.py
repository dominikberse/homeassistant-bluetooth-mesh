"""Mesh Nodes Light"""
import logging

from bluetooth_mesh import models

from .generic import Generic

# https://developer.nordicsemi.com/nRF_Connect_SDK/doc/1.9.99-dev1/nrf/libraries/bluetooth_services/mesh/light_ctl_srv.html?highlight=65535%20light#states
BLE_MESH_MIN_LIGHTNESS = 0
BLE_MESH_MAX_LIGHTNESS = 65535
BLE_MESH_MIN_TEMPERATURE = 800  # Kelvin
BLE_MESH_MAX_TEMPERATURE = 20000  # Kelvin
BLE_MESH_MIN_MIRED = 50
BLE_MESH_MAX_MIRED = 1250


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

    def supports(self, property):  # pylint: disable=redefined-builtin
        logging.debug(f"Supports: {self._features}")
        return property in self._features

    async def turn_on(self):
        await self.set_onoff_unack(True, transition_time=0)

    async def turn_off(self):
        await self.set_onoff_unack(False, transition_time=0)

    async def set_brightness(self, brightness):
        if self._is_model_bound(models.LightLightnessServer):
            await self.set_lightness_unack(brightness, transition_time=0)
        elif self._is_model_bound(models.LightCTLServer):
            await self.set_ctl_unack(brightness=brightness)

    async def kelvin(self, temperature):
        if self._is_model_bound(models.LightCTLServer):
            logging.info(f"{temperature} Kelvin")
            await self.set_ctl_unack(temperature)

    async def mireds_to_kelvin(self, temperature):
        if self._is_model_bound(models.LightCTLServer):
            kelvin = 1000000 // temperature
            logging.info(f"{temperature} mired = {kelvin} Kelvin")
            await self.set_ctl_unack(kelvin)

    async def bind(self, app):
        await super().bind(app)

        if await self.bind_model(models.GenericOnOffServer):
            self._features.add(Light.OnOffProperty)
            await self.get_onoff()

        if await self.bind_model(models.LightLightnessServer):
            self._features.add(Light.OnOffProperty)
            self._features.add(Light.BrightnessProperty)
            await self.get_lightness()
            await self.get_lightness_range()

        if await self.bind_model(models.LightCTLServer):
            self._features.add(Light.TemperatureProperty)
            self._features.add(Light.BrightnessProperty)
            await self.get_ctl()
            await self.get_light_temperature_range()

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
            logging.info(f"Get OnOff: {state}")
            self.notify(Light.OnOffProperty, result["present_onoff"])

    async def set_lightness_unack(self, lightness, **kwargs):
        if lightness > BLE_MESH_MAX_LIGHTNESS:
            lightness = BLE_MESH_MAX_LIGHTNESS
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
            logging.info(f"Get Lightness: {state}")
            self.notify(Light.BrightnessProperty, result["present_lightness"])

    async def get_lightness_range(self):
        client = self._app.elements[0][models.LightLightnessClient]
        state = await client.get_lightness_range([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            logging.info(f"Get Lightness Range: {state}")

    async def set_ctl_unack(self, temperature=None, brightness=None, **kwargs):
        if temperature and temperature < BLE_MESH_MIN_TEMPERATURE:
            temperature = BLE_MESH_MIN_TEMPERATURE
        elif temperature and temperature > BLE_MESH_MAX_TEMPERATURE:
            temperature = BLE_MESH_MAX_TEMPERATURE
        if brightness and brightness > BLE_MESH_MAX_LIGHTNESS:
            brightness = BLE_MESH_MAX_LIGHTNESS

        if temperature:
            self.notify(Light.TemperatureProperty, temperature)
        else:
            temperature = self.retained(Light.TemperatureProperty, BLE_MESH_MAX_TEMPERATURE)

        if brightness:
            self.notify(Light.BrightnessProperty, temperature)
        else:
            brightness = self.retained(Light.BrightnessProperty, BLE_MESH_MAX_LIGHTNESS)

        client = self._app.elements[0][models.LightCTLClient]
        await client.set_ctl_unack(self.unicast, self._app.app_keys[0][0], temperature, brightness, **kwargs)

    async def get_ctl(self):
        client = self._app.elements[0][models.LightCTLClient]
        state = await client.get_ctl([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            logging.info(f"Get CTL: {state}")

    async def get_light_temperature_range(self):
        client = self._app.elements[0][models.LightCTLClient]
        state = await client.get_light_temperature_range([self.unicast], self._app.app_keys[0][0])

        result = state[self.unicast]
        if result is None:
            logging.warning(f"Received invalid result {state}")
        elif not isinstance(result, BaseException):
            logging.info(f"Get Light Temperature Range: {state}")
