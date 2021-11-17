class BaseGameUser:

    def __init__(self, parent, user):
        self.parent = parent
        self.user = user


class BaseGame:

    def __init__(self, ctx, owner):
        self.started = False
        self.ctx = ctx
        self.owner = owner
        self.instances = []

    async def setup(self):
        await self.add_user(self.owner)

    def user_in(self, user):
        user_id = user.id
        for i in self.instances:
            if i.user.id == user_id:
                return i
        return None

    async def on_message(self, message):
        raise NotImplementedError()

    async def timeout(self):
        raise NotImplementedError()

    async def add_user(self, user):
        raise NotImplementedError()

    async def remove_user(self, user):
        raise NotImplementedError()

    async def end(self, winner):
        raise NotImplementedError()

    async def start(self):
        raise NotImplementedError()

    async def handle_join(self, ctx):
        raise NotImplementedError()
