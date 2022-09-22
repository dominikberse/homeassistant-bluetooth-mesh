import asyncio
import logging

from mesh import Node
from mesh.composition import Composition, Element

from bluetooth_mesh import models


class Generic(Node):
    """
    Generic Bluetooth Mesh node

    Provides additional functionality compared to the very basic Node class,
    like composition model helpers and node configuration.
    """
    OnlineProperty = 'online'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # stores the node's composition data
        self._composition = None
        # lists all bound model
        self._bound_models = set()

    def _is_model_bound(self, model):
        """
        Check if the given model is supported and bound
        """
        return model in self._bound_models

    async def fetch_composition(self):
        """
        Fetch the composition data 

        This data contains information about the node's capabilities.
        Use the helper functions to retrieve information.
        """
        client = self._app.elements[0][models.ConfigClient]
        data = await client.get_composition_data([self.unicast], net_index=0)
        # TODO: multi page composition data support
        page_zero = data.get(self.unicast, {}).get('zero')
        self._composition = Composition(page_zero)

    async def bind(self, app):
        await super().bind(app)

        # short delay to avoid irritations
        await asyncio.sleep(1.0)

        # update the composition data
        await self.fetch_composition()
        
        logging.debug(f'Node composition:\n{self._composition}')

    async def bind_model(self, model):
        """
        Bind the given model to the application key

        If the node supports the given model, it is bound to the appliaction key
        and listed within the supported models. 

        If the node does not support the given model, the request is skipped.
        """

        if self._composition is None:
            logging.info(f'No composition data for {self}')
            return False

        element = self._composition.element(0)
        if not element.supports(model):
            logging.info(f'{self} does not support {model}')
            return False
        
        # configure model
        client = self._app.elements[0][models.ConfigClient]
        await client.bind_app_key(
            self.unicast, net_index=0,
            element_address=self.unicast,
            app_key_index=self._app.app_keys[0][0],
            model=model)
        self._bound_models.add(model)

        logging.info(f'{self} bound {model}')
        return True
