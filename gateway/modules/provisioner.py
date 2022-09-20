import asyncio
import logging

from uuid import UUID

from bluetooth_mesh import models

from core.module import Module


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
        self._base_address = self.store.get('base_address', 4)
        self.store.persist()

    def setup_cli(self, parser):
        parser.add_argument('task')
        parser.add_argument('--uuid', default=None)

    async def handle_cli(self, args):
        if args.task == 'list':
            self.print_node_list()
            return

        if args.task == 'config' and args.uuid is None:
            for node in self.app.nodes.all():
                await self._configure(node.uuid, node.unicast)
            return

        try:
            uuid = UUID(args.uuid)
        except:
            print('Invalid uuid')
            return

        if args.task == 'add':
            await self._provision(uuid)
            self.print_node_list()
            return

        node = self.app.nodes.get(uuid)
        if node is None:
            print('Unknown node')
            return
        
        if args.task == 'config':
            await self._configure(uuid, node.unicast)
            return

        if args.task == 'reset':
            await self._reset(uuid, node.unicast)
            self.print_node_list()
            return

        print(f'Unknown task {args.task}')

    def print_node_list(self):
        """
        Print user friendly node list
        """

        print(f'\nMesh contains {len(self.app.nodes)} node(s):')
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
        logging.info(f'Provisioning {count} new address(es)')

        prov_data = [0, self._base_address]
        self._base_address += count

        self.store.set('base_address', self._base_address)
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

        self.app.nodes.create(_uuid, {
            'type': 'generic',
            'unicast': unicast,
            'count': count,
        })
        self.app.nodes.persist()

        logging.info(f'Provisioned {_uuid} as {unicast} ({count})')
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

        logging.error(f'Failed to provision {_uuid}:\n{reason}')
        self.provisioning_done.set()

    async def _provision(self, uuid):
        logging.info(f'Provisioning node {uuid}...')

        # provision new node
        await self.app.management_interface.add_node(uuid)
        await self.provisioning_done.wait()

    async def _configure(self, uuid, address):
        logging.info(f'Configuring node {uuid}...')

        client = self.app.elements[0][models.ConfigClient]

        # add application key
        try:
            status = await client.add_app_key(
                address, net_index=0,
                app_key_index=self.app.app_keys[0][0],
                net_key_index=self.app.app_keys[0][1],
                app_key=self.app.app_keys[0][2]
            )
        except:
            logging.exception(f'Failed to add app key for node {uuid}')

            status = await client.delete_app_key(
                address, net_index=0,
                app_key_index=self.app.app_keys[0][0],
                net_key_index=self.app.app_keys[0][1]
            )
            status = await client.add_app_key(
                address, net_index=0,
                app_key_index=self.app.app_keys[0][0],
                net_key_index=self.app.app_keys[0][1],
                app_key=self.app.app_keys[0][2]
            )

    async def _reset(self, uuid, address):
        logging.info(f'Resetting node {uuid} (address)...')

        client = self.app.elements[0][models.ConfigClient]

        await client.node_reset(
            address, net_index=0
        )

        self.app.nodes.delete(str(uuid))
        self.app.nodes.persist()