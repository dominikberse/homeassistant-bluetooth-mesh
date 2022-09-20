import logging
import asyncio

from uuid import UUID

from . import Module


class ScannerModule(Module):
    """
    Handle all scan related tasks
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._unprovisioned = set()

    def _scan_result(self, rssi, data, options):
        """
        The method is called from the bluetooth-meshd daemon when a
        unique UUID has been seen during UnprovisionedScan() for
        unprovsioned devices.
        """

        try:
            uuid = UUID(bytes=data[:16])
            self._unprovisioned.add(uuid)
            logging.info(f'Found unprovisioned node: {uuid}')
        except:
            logging.exception('Failed to retrieve UUID')
    
    async def handle_cli(self, args):
        await self.scan()

        # print user friendly results
        print(f'\nFound {len(self._unprovisioned)} nodes:')
        for uuid in self._unprovisioned:
            print(f'\t{uuid}')

    async def scan(self):
        logging.info('Scanning for unprovisioned devices...')
        
        await self.app.management_interface.unprovisioned_scan(seconds=10)
        await asyncio.sleep(10.0)
