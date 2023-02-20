"""Mesh Node"""
import asyncio
import logging

from tools import Config


class Node:
    """
    Base class for Bluetooth Mesh nodes

    Abstracts from the Bluetooth Mesh architecture and provides a basic
    event interface for other application components.
    """

    def __init__(self, uuid, type, unicast, count, configured=False, config=None):  # pylint: disable=redefined-builtin
        self.uuid = uuid
        self.type = type
        self.unicast = unicast
        self.count = count
        self.configured = configured
        self.config = config or Config(config={})

        # event system for property changes
        self._retained = {}
        self._subscribers = set()
        # event system for node initialization
        self.ready = asyncio.Event()

    def __str__(self):
        id = self.config.optional("id")  # pylint: disable=redefined-builtin

        if id:
            return f"{id} ({self.uuid}, {self.unicast:04})"
        return f"{self.uuid} ({self.unicast:04})"

    async def bind(self, app):
        """
        Configure the node to work with the available mesh clients

        Subclasses can use this function to configure Bluetooth Mesh
        models on the remote node.
        """
        self._app = app  # pylint: disable=attribute-defined-outside-init

    def subscribe(self, subscriber, resend=True):
        """
        Subscribe to state changes
        """
        self._subscribers.add(subscriber)

        for property, value in self._retained.items():  # pylint: disable=redefined-builtin
            subscriber(self, property, value)
        logging.info(f"Subscribe resend : {resend}")

    def notify(self, property, value):  # pylint: disable=redefined-builtin
        """
        Notify all subscribers about state change
        """
        self._retained[property] = value

        for subscriber in self._subscribers:
            subscriber(self, property, value)

    def retained(self, property, fallback):  # pylint: disable=redefined-builtin
        """
        Get the latest value for that property
        """
        return self._retained.get(property, fallback)

    def print_info(self, additional=None):
        logging.info(
            f"\t{self.uuid}:\n"
            f"\t\ttype: {self.type}\n"
            f"\t\tunicast: {self.unicast} ({self.count})\n"
            f"\t\tconfigured: {self.configured}",
        )

        for key, value in self.config.items():
            logging.info(f"\t\t{key}: {value}")

        if additional:
            for key, value in additional.items():
                logging.info(f"\t\t{key}: {value}")

        logging.info("|___________________________|")

    def yaml(self):
        # UUID is used as key and does not need to be stored
        return {
            "type": self.type,
            "unicast": self.unicast,
            "count": self.count,
            "configured": self.configured,
        }
