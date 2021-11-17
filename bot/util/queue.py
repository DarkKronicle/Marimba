import asyncio


class QueueProcess:
    """
    Helper class for easily doing stuff inside and outside of the queue.
    """

    def __init__(self, queue):
        self.queue = queue

    async def __aenter__(self):
        await self.queue.wait_until_complete()
        self.queue.occupied = True

    async def __aexit__(self, *args):
        self.queue.occupied = False


class SimpleQueue:
    """
    A class for only allowing a certain process to be running at once. Useful for limiting api calls to once every half
    second.
    """

    def __init__(self, bot, sleep_for, *, refresh=0.1):
        self.occupied = False
        self.sleep_for = sleep_for
        self.waiting = []
        self.running = False
        self.refresh = refresh
        self.bot = bot

    async def inc_loop(self):
        self.running = True
        while self.running:
            if not self.occupied:
                await asyncio.sleep(self.sleep_for)
                self.waiting.pop(0)
                if len(self.waiting) == 0:
                    self.running = False
                    break
                self.occupied = True
            await asyncio.sleep(self.refresh)

    async def wait_until_complete(self):
        key = self.get_key()
        self.waiting.append(key)
        if not self.running:
            self.running = True
            self.bot.loop.create_task(self.inc_loop())
        while True:
            if key not in self.waiting:
                return
            await asyncio.sleep(self.refresh)

    def get_key(self):
        for i in range(10000):
            if i not in self.waiting:
                return i
        raise IndexError("There are too many objects in the queue!")
