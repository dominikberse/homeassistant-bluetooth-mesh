import asyncio
import logging

from uuid import UUID

from bluetooth_mesh import models

from . import Module


class ProvisionerModule(Module):
    """
    Provide provisioning functionality
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.provisioning_done = asyncio.Event()

    def initialize(self, app, store, config):
        super().initialize(app, store, config)

        # ensure new devices are provisioned correctly
        self._base_address = self.store.get("base_address", 4)
        self.store.persist()

    def setup_cli(self, parser):
        parser.add_argument("task")
        parser.add_argument("--uuid", default=None)

    async def handle_cli(self, args):
        if args.task == "list":
            self.print_node_list()
            return

        # configure all provisioned
        if args.task == "config" and args.uuid is None:
            for node in self.app.nodes.all():
                if not node.configured:
                    await self._configure(node)

            self.print_node_list()
            return

        # provision nodes from configuration
        if args.task == "add" and args.uuid is None:
            for _, info in self.app._config.require("mesh").items():
                uuid = UUID(info["uuid"])
                if not self.app.nodes.has(uuid):
                    await self._provision(uuid)

            self.print_node_list()
            return

        # reset nodes from configuration
        if args.task == "reset" and args.uuid is None:
            for node in list(self.app.nodes.all()):
                if node.config.optional("id", None) is None:
                    await self._reset(node)

            self.print_node_list()
            return

        try:
            uuid = UUID(args.uuid)
        except (TypeError, ValueError):
            print("Invalid uuid")
            return

        if args.task == "add":
            await self._provision(uuid)
            self.print_node_list()
            return

        node = self.app.nodes.get(uuid)
        if node is None:
            print("Unknown node")
            return

        if args.task == "config":
            await self._configure(node)
            return

        if args.task == "reset":
            await self._reset(node)
            self.print_node_list()
            return

        print(f"Unknown task {args.task}")

    def print_node_list(self):
        """
        Print user friendly node list
        """

        print(f"\nMesh contains {len(self.app.nodes)} node(s):")
        for node in self.app.nodes.all():
            node.print_info()

    def _request_prov_data(self, count):
        """
        This method is implemented by a Provisioner capable application
        and is called when the remote device has been fully
        authenticated and confirmed.

        :param count: consecutive unicast addresses the remote device is requesting
        :return:
            :param unet_index: Subnet index of the net_key
            :param uunicast: Primary Unicast address of the new node
        """
        logging.info(f"Provisioning {count} new address(es)")

        prov_data = [0, self._base_address]
        self._base_address += count

        self.store.set("base_address", self._base_address)
        self.store.persist()

        return prov_data

    def _add_node_complete(self, uuid, unicast, count):
        """
        This method is called when the node provisioning initiated
        by an AddNode() method call successfully completed.

        :param uuid: 16 byte remote device UUID
        :param unicast: primary address that has been assigned to the new node, and the address of it's config server
        :param count: number of unicast addresses assigned to the new node
        """
        _uuid = UUID(bytes=uuid)

        self.app.nodes.create(
            _uuid,
            {
                "type": "generic",
                "unicast": unicast,
                "count": count,
            },
        )
        self.app.nodes.persist()

        logging.info(f"Provisioned {_uuid} as {unicast} ({count})")
        self.provisioning_done.set()

    def _add_node_failed(self, uuid, reason):
        """
        This method is called when the node provisioning initiated by
        AddNode() has failed. Depending on how far Provisioning
        proceeded before failing, some cleanup of cached data may be
        required.

        :param uuid: 16 byte remote device UUID
        :param reason: reason for provisioning failure
        """
        _uuid = UUID(bytes=uuid)

        logging.error(f"Failed to provision {_uuid}:\n{reason}")
        self.provisioning_done.set()

    async def _provision(self, uuid):
        logging.info(f"Provisioning node {uuid}...")

        # provision new node
        self.provisioning_done.clear()
        await self.app.management_interface.add_node(uuid)
        await self.provisioning_done.wait()

    async def _configure(self, node):
        logging.info(f"Configuring node {node}...")

        client = self.app.elements[0][models.ConfigClient]

        # add application key
        try:
            status = await client.add_app_key(
                node.unicast,
                net_index=0,
                app_key_index=self.app.app_keys[0][0],
                net_key_index=self.app.app_keys[0][1],
                app_key=self.app.app_keys[0][2],
            )
        except:
            logging.exception(f"Failed to add app key for node {node}")

            status = await client.delete_app_key(
                node.unicast, net_index=0, app_key_index=self.app.app_keys[0][0], net_key_index=self.app.app_keys[0][1]
            )
            status = await client.add_app_key(
                node.unicast,
                net_index=0,
                app_key_index=self.app.app_keys[0][0],
                net_key_index=self.app.app_keys[0][1],
                app_key=self.app.app_keys[0][2],
            )

        # update friend state
        if node.config.optional("relay", False):
            status = await client.set_relay(
                node.unicast,
                net_index=0,
                relay=True,
                retransmit_count=2,
            )

        # try to set node type from Home Assistant
        node.type = node.config.optional("type", node.type)

        node.configured = True
        self.app.nodes.persist()

    async def _reset(self, node):
        logging.info(f"Resetting node {node}...")

        client = self.app.elements[0][models.ConfigClient]

        await client.node_reset(node.unicast, net_index=0)

        self.app.nodes.delete(str(node.uuid))
        self.app.nodes.persist()
