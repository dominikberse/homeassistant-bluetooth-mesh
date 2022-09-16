import asyncio
import logging
import secrets
import yaml 
import argparse

from contextlib import suppress
from uuid import UUID

from bluetooth_mesh.application import Application, Element
from bluetooth_mesh.crypto import ApplicationKey, DeviceKey, NetworkKey
from bluetooth_mesh.messages.config import GATTNamespaceDescriptor
from bluetooth_mesh import models

from core.store import Store
from core.config import Config

from modules.provisioner import ProvisionerModule
from modules.scanner import ScannerModule


logging.basicConfig(level=logging.DEBUG)


MODULES = {
    "prov": ProvisionerModule(),
    "scan": ScannerModule(),
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

        self._store = Store(location='store.yaml')
        self._config = Config('config.yaml')
        self._nodes = {}

        self._app_keys = None
        self._dev_key = None
        self._primary_net_key = None
        self._new_keys = set()

        # load modules
        for name, module in MODULES.items():
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
            return bytes.fromhex(keychain['device_key'])
        except:
            raise Exception('Invalid device key')

    def _initialize(self):
        keychain = self._store.get('keychain') or {}
        local = self._store.section('local')
        self._nodes = self._store.section('nodes')

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

        # persist changes
        self._store.set('keychain', keychain)
        self._store.persist()

    async def _import_keys(self):
        if 'primary_net_key' in self._new_keys:
            # register primary network key as subnet key
            await self.management_interface.import_subnet(0, self.primary_net_key[1])

        if 'app_key' in self._new_keys:
            # TODO: check whether this step is actually neccessary
            await self.management_interface.import_app_key(*self.app_keys[0])    
            # TODO: check whether this needs to be done always
            await self.add_app_key(*self.app_keys[0])

    def scan_result(self, rssi, data, options):
        MODULES['scan']._scan_result(rssi, data, options)

    def request_prov_data(self, count):
        return MODULES['prov']._request_prov_data(count)

    def add_node_complete(self, uuid, unicast, count):
        MODULES['prov']._add_node_complete(uuid, unicast, count)

    def add_node_failed(self, uuid, reason):
        MODULES['prov']._add_node_failed(uuid, reason)

    async def run(self, args):
        async with self:

            # connect to daemon
            await self.connect()

            # reset everything
            if args.reset:
                await self.leave()
                self._store.reset()
                self._store.persist()
                return

            # configure all keys
            await self._import_keys()

            # run user task if specified
            if args.handler:
                await args.handler(args)
                return

            if task == 'set_onoff':
                nodes = self._store.get('nodes') or {}
                if uuid not in nodes:
                    logging.error('Unknown node')
            
                client = self.elements[0][models.ConfigClient]

                status = await client.bind_app_key(
                    nodes[uuid]['unicast'], net_index=0,
                    element_address=nodes[uuid]['unicast'],
                    app_key_index=self.app_keys[0][0],
                    model=models.GenericOnOffServer
                )

                client = self.elements[0][models.GenericOnOffClient]

                await client.bind(self.app_keys[0][0])
                await client.set_onoff_unack(
                    nodes[uuid]['unicast'], 
                    self.app_keys[0][0], 
                    int(value), 
                    send_interval=0.5)

                return

            # run main task


def main():
    loop = asyncio.get_event_loop()
    app = MqttGateway(loop)

    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')

    # module specific CLI interfaces
    subparsers = parser.add_subparsers()
    for name, module in MODULES.items():
        subparser = subparsers.add_parser(name)
        subparser.set_defaults(handler=module.handle_cli)
        module.setup_cli(subparser)

    args = parser.parse_args()

    with suppress(KeyboardInterrupt):
        loop.run_until_complete(app.run(args))

if __name__ == '__main__':
    main()