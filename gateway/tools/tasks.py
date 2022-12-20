import asyncio
import logging


class Tasks:
    """
    Simple task pool
    """

    def __init__(self, name="root"):
        self._name = name
        self._tasks = set()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._invoke_shutdown()

        # wait until finished before exiting
        for task in self._tasks:
            if not task.done():
                await task

        logging.debug(f"{self._name} finalized")

    def _invoke_shutdown(self):
        logging.info(f"{self._name}: invoke shutdown...")

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
            logging.debug(f"{self._name}: spawning task to {name}...")
        try:
            await task
        except asyncio.CancelledError:
            # graceful exit
            logging.debug(f"{self._name}: {name} cancelled")
            return
        except:
            logging.exception(f"{self._name}: {name} failed")
            # force cancellation of all tasks
            # depending on the configuration, this should lead to service restart
            raise
        if name:
            logging.debug(f"{self._name}: {name} completed")

    def spawn(self, task, name=None):
        self._tasks.add(
            asyncio.create_task(
                self._runner(task, name),
                name=name or f"self._name + {len(self._tasks)}",
            )
        )

    async def gather(self):
        logging.info(f"{self._name}: awaiting {len(self._tasks)} tasks")

        # wait until all tasks are completed or an exception is caught
        await asyncio.gather(*self._tasks)
