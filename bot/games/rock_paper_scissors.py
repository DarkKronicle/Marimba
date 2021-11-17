import asyncio
import copy

from bot.util import base_game, paginator


class RegularTournament:

    def __init__(self, names):
        self.names = names
        self.n = len(self.names)

    def get_name(self, n):
        return self.names[n]

    def result(self, previous, other):
        if isinstance(previous, str):
            previous = self.names.indexof(previous)
        if isinstance(other, str):
            other = self.names.indexof(other)
        return self.defeat(previous, other)

    def defeat(self, previous, other):
        return self.eulerian_check(previous, other)

    def eulerian_check(self, previous, other):
        if previous == 0 and other == self.n - 1:
            dif = 1
        elif previous == self.n - 1 and other == 0:
            dif = -1
        else:
            dif = previous - other
        if 1 >= dif >= -1:
            if dif == 0:
                return False
            if dif == -1:
                return True
            if dif == 1:
                return False
        return None

    @classmethod
    def rps(cls):
        return cls(['paper', 'rock', 'scissors'])


class RPSPlayer(base_game.BaseGameUser):

    def __init__(self, parent, user, game, channel):
        super().__init__(parent, user)
        self.channel = channel
        self.game = game

    async def get_rps(self, ctx):
        key = {
            '🖐️': (0, 'paper'),
            '✊': (1, 'rock'),
            '✌️': (2, 'scissors'),
        }
        previous_channel = ctx.channel
        msg = copy.copy(ctx.message)
        channel = self.channel
        msg.channel = channel
        msg.author = self.user
        msg.content = "None..."
        new_ctx = await ctx.bot.get_context(msg, cls=type(ctx))
        selection = await paginator.SelectOption(key, 'Rock paper or scissors?').start(new_ctx, )
        await self.channel.send("Go back to {0} to see the result!".format(previous_channel.mention))
        return selection


class RPSGame(base_game.BaseGame):

    def __init__(self, ctx, owner):
        super().__init__(ctx, owner)
        self.game = RegularTournament.rps()

    async def on_message(self, message):
        pass

    async def timeout(self):
        await self.ctx.send('Timed out!')

    async def add_user(self, user):
        try:
            channel = await user.create_dm()
        except:
            return await self.ctx.send("Can't DM you!")
        self.instances.append(RPSPlayer(self, user, self.game, channel))

    async def remove_user(self, user):
        instance = None
        for i in self.instances:
            if i.user.id == user.id:
                instance = i
                break
        await self.instances.remove(instance)
        await self.end(self.instances[0].user)

    async def end(self, winner):
        if winner is not None:
            await self.ctx.send('{0} won!'.format(winner.mention))
        else:
            await self.ctx.send('Stalemate!')

    async def start(self):
        await self.add_user(self.owner)
        coros = [instance.get_rps(self.ctx) for instance in self.instances]
        results = await asyncio.gather(*coros)
        one_win = self.game.result(results[0], results[1])
        await self.ctx.send(embed=self.ctx.create_embed('{0} chose: {1}\n\n{2} chose: {3}'.format(
            self.instances[0].user.mention,
            self.game.get_name(results[0]),
            self.instances[1].user.mention,
            self.game.get_name(results[1])
        )))
        if results[0] == results[1]:
            await self.end(None)
        elif one_win:
            await self.end(self.instances[0].user)
        else:
            await self.end(self.instances[1].user)

    async def handle_join(self, ctx):
        await self.ctx.send("You can't join RPS mid game!")
        return False
