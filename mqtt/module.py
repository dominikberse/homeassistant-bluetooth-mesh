class MessengerModule:
    """
    Base class for all MQTT messenger modules
    """

    def __init__(self, messenger):
        self._messenger = messenger

    def config(self, node):
        """
        Get discovery message
        """
        pass

    def state(self, node):
        """
        Get state message
        """
        pass

    async def handle(self, node, command, payload):
        """
        Handle a specific MQTT command
        """
        pass