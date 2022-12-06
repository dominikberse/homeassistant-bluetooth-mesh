class Model:
    def __init__(self, data):
        self._model_id = data.get("model_id")

    @property
    def model_id(self):
        return self._model_id


class Element:
    def __init__(self, data):
        self._data = data

        self._sig_models = list(map(Model, data.get("sig_models")))
        self._vendor_models = list(map(Model, data.get("vendor_models")))

    @property
    def sig_models(self):
        return self._sig_models

    @property
    def vendor_models(self):
        return self._vendor_models

    def supports(self, model):
        """
        Check if the element supports (contains) the given model
        """
        model_ids = model.MODEL_ID

        for sig_model in self._sig_models:
            if sig_model.model_id in model_ids:
                return True

        for vendor_model in self._vendor_models:
            if vendor_model.model_id in model_ids:
                return True

        return False


class Composition:
    def __init__(self, data):
        self._data = data

        self._elements = list(map(Element, data.get("elements")))

    def __str__(self):
        return str(self._data)

    @property
    def elements(self):
        return self._elements

    def element(self, index):
        return self._elements[index]
