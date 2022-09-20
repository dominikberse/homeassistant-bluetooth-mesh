import asyncio
import logging


class Tasks:
    """
    Simple task pool

    TODO: This class can be extended in order to manage failed tasks.
    Currently failed tasks are logged but otherwise ignored.
    """

    def __init__(self):
        self._tasks = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._shutdown()

    async def _shutdown(self):
        for task in self._tasks:
            if task.done():
                continue
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

    async def _runner(self, task):
        logging.info('Spawning task...')
        try:
            await task
        except:
            logging.exception('Task failed')
        logging.info('Task completed')

    def spawn(self, task):
        self._tasks.add(asyncio.create_task(self._runner(task)))

    async def gather(self):
        logging.info(f'Awaiting {len(self._tasks)} tasks')
        await asyncio.gather(*self._tasks)