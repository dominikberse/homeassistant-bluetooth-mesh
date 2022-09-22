import asyncio
import logging
import secrets
import argparse
import uuid

from contextlib import AsyncExitStack, suppress

from bluetooth_mesh.application import Application, Element
from bluetooth_mesh.crypto import ApplicationKey, DeviceKey, NetworkKey
from bluetooth_mesh.messages.config import GATTNamespaceDescriptor
from bluetooth_mesh import models

from tools import Config, Store, Tasks
from mesh import Node, NodeManager
from mqtt import HassMqttMessenger

from modules.provisioner import ProvisionerModule
from modules.scanner import ScannerModule
from modules.manager import ManagerModule

from mesh.nodes.light import Light


logging.basicConfig(level=logging.INFO)


MESH_MODULES = {
    "prov": ProvisionerModule(),
    "scan": ScannerModule(),
    "mgmt": ManagerModule(),
}


NODE_TYPES = {
    'generic': Node,
    'light': Light,
}


class MainElement(Element):
    """
    Represents the main element of the application node
    """
    LOCATION = GATTNamespaceDescriptor.MAIN
    MODELS = [
        models.ConfigClient,
        models.HealthClient,
        models.GenericOnOffClient,
        models.LightLightnessClient,
        models.LightCTLClient,
    ]


class MqttGateway(Application):

    COMPANY_ID = 0x05F1  # The Linux Foundation
    PRODUCT_ID = 1
    VERSION_ID = 1
    ELEMENTS = {
        0: MainElement,
    }
    CRPL = 32768
    PATH = "/org/hass/mesh"

    def __init__(self, loop):
        super().__init__(loop)

        self._store = Store(location='../store.yaml')
        self._config = Config('../config.yaml')
        self._nodes = {}
        
        self._messenger = None

        self._app_keys = None
        self._dev_key = None
        self._primary_net_key = None
        self._new_keys = set()

        # load mesh modules
        for name, module in MESH_MODULES.items():
            module.initialize(self, self._store.section(name), self._config)

        self._initialize()

    @property
    def dev_key(self):
        if not self._dev_key:
            raise Exception('Device key not ready')
        return self._dev_key

    @property
    def primary_net_key(self):
        if not self._primary_net_key:
            raise Exception('Primary network key not ready')
        return 0, self._primary_net_key

    @property
    def app_keys(self):
        if not self._app_keys:
            raise Exception('Application keys not ready')
        return self._app_keys

    @property
    def nodes(self):
        return self._nodes

    def _load_key(self, keychain, name):
        if name not in keychain:
            logging.info(f'Generating {name}...')
            keychain[name] = secrets.token_hex(16)
            self._new_keys.add(name)
        try:
            return bytes.fromhex(keychain[name])
        except:
            raise Exception('Invalid device key')

    def _initialize(self):
        keychain = self._store.get('keychain') or {}
        local = self._store.section('local')
        nodes = self._store.section('nodes')

        # load or set application parameters
        self.address = local.get('address', 1)
        self.iv_index = local.get('iv_index', 5)

        # load or generate keys
        self._dev_key = DeviceKey(self._load_key(keychain, 'device_key'))
        self._primary_net_key = NetworkKey(self._load_key(keychain, 'network_key'))
        self._app_keys = [
                # currently just a single application key supported
                (0, 0, ApplicationKey(self._load_key(keychain, 'app_key'))),
            ]

        # initialize node manager
        self._nodes = NodeManager(nodes, NODE_TYPES)
        for node in self._nodes.all():
            # append Home Assistant specific configuration
            node.config = self._config.node_config(node.uuid)

        # initialize MQTT messenger
        self._messenger = HassMqttMessenger(self._config, self._nodes)

        # persist changes
        self._store.set('keychain', keychain)
        self._store.persist()

    async def _import_keys(self):

        if 'app_key' in self._new_keys:
            # import application key into daemon
            await self.management_interface.import_app_key(*self.app_keys[0])    
            logging.info('Imported app key')

        if 'primary_net_key' in self._new_keys:
            # register primary network key as subnet key
            await self.management_interface.import_subnet(0, self.primary_net_key[1])
            logging.info('Imported primary net key as subnet key')

        # update application key for client models
        client = self.elements[0][models.GenericOnOffClient]
        await client.bind(self.app_keys[0][0])
        client = self.elements[0][models.LightLightnessClient]
        await client.bind(self.app_keys[0][0])
        client = self.elements[0][models.LightCTLClient]
        await client.bind(self.app_keys[0][0])

    async def _try_bind_node(self, node):
        try:
            await node.bind(self)
            logging.info(f'Bound node {node}')
            node.ready.set()
        except:
            logging.exception(f'Failed to bind node {node}')
        
    def scan_result(self, rssi, data, options):
        MESH_MODULES['scan']._scan_result(rssi, data, options)

    def request_prov_data(self, count):
        return MESH_MODULES['prov']._request_prov_data(count)

    def add_node_complete(self, uuid, unicast, count):
        MESH_MODULES['prov']._add_node_complete(uuid, unicast, count)

    def add_node_failed(self, uuid, reason):
        MESH_MODULES['prov']._add_node_failed(uuid, reason)

    def shutdown(self, tasks):
        self._messenger.shutdown()

    async def run(self, args):
        async with AsyncExitStack() as stack:
            tasks = await stack.enter_async_context(Tasks())

            # connect to daemon
            await stack.enter_async_context(self)
            await self.connect()

            # leave network
            if args.leave:
                await self.leave()
                self._nodes.reset()
                self._nodes.persist()
                return

            # reload all keays
            if args.reload:
                self._new_keys.add('primary_net_key')
                self._new_keys.add('app_key')

            try:
                # set overall application key
                await self.add_app_key(*self.app_keys[0])
            except:
                logging.exception(f'Failed to set app key {self._app_keys[0][2].bytes.hex()}')

                # try to re-add application key
                await self.delete_app_key(self.app_keys[0][0], self.app_keys[0][1])
                await self.add_app_key(*self.app_keys[0])

            # configure all keys
            await self._import_keys()

            # run user task if specified
            if 'handler' in args:
                await args.handler(args)
                return

            # initialize all nodes
            for node in self._nodes.all():
                tasks.spawn(self._try_bind_node(node), f'bind {node}')

            # start MQTT task
            tasks.spawn(self._messenger.run(self), 'run messenger')

            # wait for all tasks
            await tasks.gather()

def main():
    loop = asyncio.get_event_loop()
    app = MqttGateway(loop)

    parser = argparse.ArgumentParser()
    parser.add_argument('--leave', action='store_true')
    parser.add_argument('--reload', action='store_true')

    # module specific CLI interfaces
    subparsers = parser.add_subparsers()
    for name, module in MESH_MODULES.items():
        subparser = subparsers.add_parser(name)
        subparser.set_defaults(handler=module.handle_cli)
        module.setup_cli(subparser)

    args = parser.parse_args()

    with suppress(KeyboardInterrupt):
        loop.run_until_complete(app.run(args))

if __name__ == '__main__':
    main()
