import asyncio
import logging

from mesh import Node

from bluetooth_mesh import models


class Generic(Node):
    """
    Adds support for generic nodes 
    """
    OnlineProperty = 'online'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._composition = None
        self._supports = set()

    @property
    def online(self):
        return self._get(Generic.OnlineProperty)
        
    def _bound(self, model):
        """
        Check if the given feature is supported
        """
        return model in self._supports

    def _element(self, index):
        if self._composition is None:
            return None
            
        return self._composition.get('elements')[index]

    def _models(self, element=0, models='sig_models'):
        element = self._element(element)
        if element is None:
            return False

        return element.get(models)

    async def bind(self, app):
        await super().bind(app)
        await asyncio.sleep(1.0)

        # get composition data
        client = self._app.elements[0][models.ConfigClient]
        data = await client.get_composition_data([self.unicast], net_index=0)
        # TODO: multi page composition data support
        self._composition = data.get(self.unicast, {}).get('zero')

        # debugging info about composition data
        logging.debug(self._composition)

        # node is assumed to be online
        self._set(Generic.OnlineProperty, True)

    async def bind_model(self, model):

        # find all supported models
        for feature in self._models():
            if feature.model_id in model.MODEL_ID:
                self._supports.add(model)

                # configure model
                client = self._app.elements[0][models.ConfigClient]
                await client.bind_app_key(
                    self.unicast, net_index=0,
                    element_address=self.unicast,
                    app_key_index=self._app.app_keys[0][0],
                    model=model)

                logging.info(f'{self} supports {model}')
                return True

        logging.info(f'{self} lacks {model}')
        return False