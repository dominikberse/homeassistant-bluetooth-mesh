import asyncio
import secrets
import logging
import yaml 

from contextlib import suppress
from uuid import UUID

from bluetooth_mesh.application import Application, Element
from bluetooth_mesh.crypto import ApplicationKey, DeviceKey, NetworkKey
from bluetooth_mesh.messages.config import GATTNamespaceDescriptor
from bluetooth_mesh.models import ConfigClient, HealthClient, GenericOnOffServer, GenericOnOffClient, LightLightnessClient


logging.basicConfig(level=logging.DEBUG)


class MainElement(Element):
    LOCATION = GATTNamespaceDescriptor.MAIN
    MODELS = [
        ConfigClient,
        HealthClient,
        GenericOnOffClient,
        LightLightnessClient,
    ]


class SampleApplication(Application):
    COMPANY_ID = 0x0136  # Silvair
    PRODUCT_ID = 1
    VERSION_ID = 1
    ELEMENTS = {
        0: MainElement,
    }
    CRPL = 32768
    PATH = "/org/hass/mesh"

    def __init__(self, loop):
        super().__init__(loop)

        self.added = asyncio.Event()
        self.unprovisioned = set()
        self.mesh = {}

    @property
    def dev_key(self):
        return DeviceKey(self.mesh['config']['device_key'])

    @property
    def primary_net_key(self):
        return 0, NetworkKey(self.mesh['config']['primary_net_key'])

    @property
    def app_keys(self):
        return [
            (0, 0, ApplicationKey(self.mesh['config']['app_key'])),
        ]

    def scan_result(self, rssi, data, options):
        try:
            device = UUID(bytes=data[:16])
            self.unprovisioned.add(device)
            logging.info(f'Found unprovisioned: {device}')
        except:
            logging.exception('Failed to retrieve UUID')

    def request_prov_data(self, count):
        """
        This method is implemented by a Provisioner capable application
        and is called when the remote device has been fully
        authenticated and confirmed.

        :param count: consecutive unicast addresses the remote device is requesting
        :return:
            :param unet_index: Subnet index of the net_key
            :param uunicast: Primary Unicast address of the new node
        """
        logging.info(f'Provisioning {count} unicast addresses')

        current_index = self.mesh['config']['unicast_index']
        self.mesh['config']['unicast_index'] = current_index + count
        return [0, current_index]

    def add_node_complete(self, uuid, unicast, count):
        """
        This method is called when the node provisioning initiated
        by an AddNode() method call successfully completed.

        :param uuid: 16 byte remote device UUID
        :param unicast: primary address that has been assigned to the new node, and the address of it's config server
        :param count: number of unicast addresses assigned to the new node
        :return:
        """
        device = UUID(bytes=uuid)
        self.mesh['nodes'][str(device)] = {
            'unicast': unicast,
            'count': count,
        }

        logging.info(f'Provisioned {device} as {unicast} ({count})')
        self.added.set()

    def add_node_failed(self, uuid, reason):
        logging.info(f'Failed to provision {UUID(bytes=uuid)}:\n{reason}')
        self.added.set()

    async def scan(self):
        logging.info('Scanning unprovisioned')
        await self.management_interface.unprovisioned_scan()
        await asyncio.sleep(5.0)
        logging.info('Done')

    async def configure(self, addr):
        client = self.elements[0][ConfigClient]

        try:
            status = await client.add_app_key(
                addr, net_index=0,
                app_key_index=self.app_keys[0][0],
                net_key_index=self.app_keys[0][1],
                app_key=self.app_keys[0][2]
            )
        except:
            status = await client.delete_app_key(
                addr, net_index=0,
                app_key_index=self.app_keys[0][0],
                net_key_index=self.app_keys[0][1]
            )
            logging.info(f'Failed to add client app key')

        # print(status)

        #assert status == StatusCode.SUCCESS, \
        #    f'Cannot add application key: {status}'

        status = await client.bind_app_key(
            addr, net_index=0,
            element_address=addr,
            app_key_index=self.app_keys[0][0],
            model=GenericOnOffServer
        )

        print(status)

        #assert status == StatusCode.SUCCESS, \
        #    f'Cannot bind application key: {status}'

    def state_changed(self, *args, **kwargs):
        print(args)
        print(kwargs)

    async def run(self):

        # load configuration
        with open('mesh.yaml', 'r') as config:
            self.mesh = yaml.safe_load(config)

        # initial configuration
        config = self.mesh.get('config') or {}
        if 'primary_net_key' not in config:
            config['primary_net_key'] = bytes.fromhex('179ecafc982f71f3854f63ce9c8a9080')
        if 'device_key' not in config:
            config['device_key'] = bytes.fromhex('f41f8e6b286d3b1a6700f308d22acc2f')
        if 'app_key' not in config:
            config['app_key'] = secrets.token_bytes(16)
        if 'unicast_index' not in config:
            config['unicast_index'] = 4
        self.mesh['config'] = config

        print(config['device_key'].hex())
        print(config['primary_net_key'].hex())

        if self.mesh.get('nodes') is None:
            self.mesh['nodes'] = {}

        # base configuration
        self.address = 1
        self.iv_index = 5

        print(self.app_keys)
        print(self.app_keys[0][2].bytes.hex())

        async with self:
            try:
                await self.connect()
                # await self.delete_app_key(0, 0)
                await self.add_app_key(*self.app_keys[0])
                await self.scan()
            
                if 'subnet_key' not in self.mesh['config']:
                    # generate default subnet key
                    self.mesh['config']['subnet_key'] = self.mesh['config']['primary_net_key']
                    # register subnet key
                    try:
                        await self.management_interface.import_subnet(0, self.primary_net_key[1])
                    except:
                        logging.info('Subnet already exists, trying to reconfigure')

                        await self.management_interface.delete_subnet(0)
                        await self.management_interface.import_subnet(0, self.primary_net_key[1])

                    await self.management_interface.import_app_key(*self.app_keys[0])

                uuid = 'ecce3aa9-3915-5236-b795-4a2bb919b83f'

                if uuid not in self.mesh['nodes']:
                    await self.management_interface.add_node(UUID(uuid))
                    await self.added.wait()

                address = self.mesh['nodes'][uuid]['unicast']
                await self.configure(address)

                # 
                # 
                # 

                client = self.elements[0][GenericOnOffClient]
                await client.bind(self.app_keys[0][0])
                await client.set_onoff_unack(address, self.app_keys[0][0], 0, send_interval=0.5)
                await asyncio.sleep(5.0)
                await client.set_onoff_unack(address, self.app_keys[0][0], 1, delay=1.0, send_interval=0.5)
            except:
                logging.exception('Failed to setup mesh')
                
            # await asyncio.sleep(5.0)
            # await self.management_interface.delete_remote_node(0x0004, 1)
            # await self.leave()

        # store configuration
        with open('mesh.yaml', 'w') as config:
            yaml.dump(self.mesh, config)


def main():
    loop = asyncio.get_event_loop()
    app = SampleApplication(loop)

    with suppress(KeyboardInterrupt):
        loop.run_until_complete(app.run())


if __name__ == '__main__':
    main()