import yaml


class Config:
    def __init__(self, filename):
        self._filename = filename

        # load user configuration
        with open(self._filename, 'r') as config_file:
            self._config = yaml.safe_load(config_file)