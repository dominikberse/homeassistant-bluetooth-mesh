"""Config"""
import logging

import yaml
from exceptions import ConfigException


class Config:
    def __init__(self, filename=None, config=None):
        self._filename = filename

        # load user configuration
        if self._filename:
            with open(self._filename, "r", encoding="utf-8") as config_file:
                self._config = yaml.safe_load(config_file)

        elif config is not None:
            self._config = config

        else:
            raise ConfigException(f"Invalid config initialization: {config}")

    def _get(self, path, section, info):
        if "." in path:
            prefix, remainder = path.split(".", 1)
            subsection = self._get(prefix, section, info)
            return self._get(remainder, subsection, info)

        if path not in section:
            if "raise" in info:
                raise info["raise"]
            return info["fallback"]

        return section[path]

    def require(self, path):
        return self._get(
            path,
            self._config,
            {
                "raise": Exception(f"{path} missing in config"),
            },
        )

    def optional(self, path, fallback=None):
        return self._get(
            path,
            self._config,
            {
                "fallback": fallback,
            },
        )

    def node_config(self, uuid):
        """
        Get config for given node
        """
        mesh = self.optional("mesh", None) or {}

        for node_id, info in mesh.items():
            if info.get("uuid") == str(uuid):
                return Config(config={"id": node_id, **info})

        logging.warning(f"Missing configuration for node {uuid}")
        return Config(config={})

    def items(self):
        return self._config.items()
