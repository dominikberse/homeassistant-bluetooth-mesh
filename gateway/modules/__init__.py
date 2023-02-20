"""Module"""


class Module:
    """
    Base class for application modules

    Defines interfaces that can be used to hide modules behind various views,
    like i.e. a command line interface or an HTTP or MQTT interface.
    """

    def __init__(self):
        pass

    def initialize(self, app, store, config):
        """
        Do additional initialization after Bluetooth layer is available
        """

        self.app = app  # pylint: disable=attribute-defined-outside-init
        self.store = store  # pylint: disable=attribute-defined-outside-init
        self.config = config  # pylint: disable=attribute-defined-outside-init

    def setup_cli(self, parser):
        """
        Setup argparse sub parser for direct CLI usage
        """

    async def handle_cli(self, args):
        """
        Run from CLI
        """
