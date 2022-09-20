class Node:
    """
    Base class for Bluetooth Mesh nodes

    Provides a basic implementation to manage node states and
    allow to subscribe for state changes.
    """

    def __init__(self, uuid, type, unicast, count):
        self.uuid = uuid
        self.type = type
        self.unicast = unicast
        self.count = count
        self.hass = None

        self._subscribers = set()
        self._state = {}

    def __str__(self):
        id = self.hass and self.hass.optional('id')
        
        if id:
            return f'{id} ({self.uuid}, {self.unicast:04})' 
        return f'{self.uuid} ({self.unicast:04})'

    def _get(self, property):
        """
        Get property from state
        """
        return self._state.get(property)
    
    def _set(self, property, value):
        """
        Set state property and notify about change
        """
        if self._state.get(property) == value:
            return
        if value is None:
            del self._state[property]
        else:
            self._state[property] = value
        self.notify(property, value)

    async def bind(self, app):
        """
        Configure the node to work with the available mesh clients
        """
        self._app = app

    def subscribe(self, subscriber):
        """
        Subscribe to state changes
        """
        self._subscribers.add(subscriber)

    def notify(self, property, value):
        """
        Notify all subscribers about state change
        """
        for subscriber in self._subscribers:
            subscriber(self, property, value)

    def print_info(self):
        print(
            f'\t{self.uuid}:\n'
            f'\t\ttype: {self.type}\n'
            f'\t\tunicast: {self.unicast} ({self.count})\n'
        )

    def yaml(self):
        # UUID is used as key and does not need to be stored
        return {
            'type': self.type,
            'unicast': self.unicast,
            'count': self.count,
        }