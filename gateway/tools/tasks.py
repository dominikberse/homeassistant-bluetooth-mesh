import asyncio
import logging


class Tasks:
    """
    Simple task pool
    """

    def __init__(self):
        self._tasks = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._invoke_shutdown()

        # wait until finished before exiting
        await self.gather()

    def _invoke_shutdown(self):
        logging.info("Invoke shutdown...")

        for task in self._tasks:
            if task.done():
                continue

            try:
                # invoke tasks cancellation
                task.cancel()
            except asyncio.CancelledError:
                pass

    async def _runner(self, task, name):
        if name:
            logging.debug(f"Spawning task to {name}...")
        try:
            await task
        except asyncio.CancelledError:
            # graceful exit
            logging.debug(f"{name} cancelled")
            return
        except:
            logging.exception(f"{name} failed")
            # force cancellation of all tasks
            # depending on the configuration, this should lead to service restart
            raise
        if name:
            logging.debug(f"{name} completed")

    def spawn(self, task, name=None):
        self._tasks.add(asyncio.create_task(self._runner(task, name)))

    async def gather(self):
        logging.info(f"Awaiting {len(self._tasks)} tasks")

        # wait until all tasks are completed or an exception is caught
        await asyncio.gather(*self._tasks)
