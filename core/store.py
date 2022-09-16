import yaml


class Store:
    """
    Provides a simple database structure
    """
    
    def __init__(self, delegate=None, location=None, data=None):
        self._location = location
        self._delegate = delegate

        if self._location:
            with open(self._location, 'r') as store_file:
                self._data = yaml.safe_load(store_file)
        else:
            self._data = data

        if self._data is None:
            self._data = {}

    def persist(self):
        if self._delegate:
            # persist using parent location
            self._delegate.persist()

        if self._location:
            # persist to actual location
            with open(self._location, 'w') as store_file:
                yaml.dump(self._data, store_file)

    def section(self, name):
        """
        Return a new sub-store that will persist to same location
        """
        if name not in self._data:
            self._data[name] = {}

        return Store(delegate=self, data=self._data[name])

    def get(self, name, fallback=None):
        if name not in self._data:
            self._data[name] = fallback
        return self._data[name]

    def set(self, name, value):
        self._data[name] = value

    def has(self, name):
        return name in self._data

    def delete(self, name):
        del self._data[name]

    def reset(self):
        self._data = {}

    def items(self):
        return self._data.items()
