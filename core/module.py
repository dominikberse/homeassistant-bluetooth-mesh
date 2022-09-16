

class Module:
    """
    Base class for all modules

    Defines interfaces that can be used to hide modules behind various views,
    like i.e. a command line interface or an HTTP interface.
    """

    def __init__(self):
        pass

    def initialize(self, app, store, config):
        """
        Do additional initialization after BLE layer is available
        """

        self.app = app
        self.store = store
        self.config = config

    def setup_cli(self, parser):
        """
        Setup argparse sub parser for direct CLI usage
        """
        pass

    async def handle_cli(self, args):
        """
        Run from CLI
        """
        pass