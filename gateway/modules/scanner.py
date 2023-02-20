"""Scanner"""
import asyncio
import logging
from uuid import UUID

from exceptions import ScanException

from . import Module


class ScannerModule(Module):
    """
    Handle all scan related tasks
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._unprovisioned = set()

    def _scan_result(self, rssi, data, options):  # pylint: disable=unused-argument
        """
        The method is called from the bluetooth-meshd daemon when a
        unique UUID has been seen during UnprovisionedScan() for
        unprovsioned devices.
        """

        try:
            uuid = UUID(bytes=data[:16])
            self._unprovisioned.add(uuid)
            logging.info(f"Found unprovisioned node: {uuid}")
            logging.info(f"Options not used: {options}")
        except ScanException as exp:
            logging.exception(f"Failed to retrieve UUID: {exp}")

    async def handle_cli(self, args):
        await self.scan()
        # print user friendly results
        logging.info(f"Found {len(self._unprovisioned)} nodes:")
        for uuid in self._unprovisioned:
            logging.info(f"UUID => {uuid}")

    async def scan(self):
        logging.info("Scanning for unprovisioned devices...")
        await self.app.management_interface.unprovisioned_scan(seconds=10)
        await asyncio.sleep(10.0)
