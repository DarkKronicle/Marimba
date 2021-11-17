import random

import asyncio

import discord

from bot.util import base_game


class ConnectFourInstance(base_game.BaseGameUser):

    def __init__(self, parent, user, value):
        super().__init__(parent, user)
        self.value = value


class ConnectFour(base_game.BaseGame):

    def __init__(self, ctx, owner, on_end, *, dimensions=(9, 7)):
        super().__init__(ctx, owner)
        self.turn = None
        self.answer = None
        self.board = None
        self.dimensions = dimensions
        self.order = []
        self.on_end = on_end

    async def on_message(self, message):
        if not self.started:
            return
        if message.author.id != self.turn.user.id:
            return
        try:
            self.answer = int(message.content)
        except ValueError:
            return
        await message.delete()

    async def timeout(self):
        self.started = False
        await self.ctx.send('The game timed out!')
        await self.cleanup()

    async def loop(self):
        i = 0
        while self.answer is None:
            i += 1
            await asyncio.sleep(1)
            # 3 Minutes until timeout
            if i >= 180:
                await self.timeout()
        await self.advance()

    async def advance(self):
        if self.answer <= 0:
            self.answer = None
            return await self.ctx.send("Can't less than or equal to 0.", delete_after=5)
        if self.answer > self.dimensions[0]:
            self.answer = None
            return await self.ctx.send("Can't be greater than {0}".format(self.dimensions[0]), delete_after=5)
        column = self.board[self.answer - 1]
        one_free = False
        for c in column:
            if c == 0:
                one_free = True
                break
        if not one_free:
            self.answer = None
            return await self.ctx.send('That column is full!', delete_after=5)
        for i in range(len(column)):
            if column[i] == 0:
                column[i] = self.turn.value
                break
        self.answer = None
        await self.check()
        if self.started:
            self.next_user()
        if self.started:
            await self.send_board()

    directions = (
        ((0, 1), (0, -1)),
        ((1, 0), (-1, 0)),
        ((1, 1), (-1, -1)),
        ((-1, 1), (1, -1)),
    )

    async def check(self):
        # We already know what we're looking for
        value = self.turn.value
        max_added = 0
        one_free = False
        max_y = self.dimensions[1] - 1
        max_x = self.dimensions[0] - 1
        for y in range(max_y + 1):
            for x in range(max_x + 1):
                val = self.board[x][y]
                if val == 0:
                    one_free = True
                if val != value:
                    # No need to check
                    continue
                for dirs in self.directions:
                    cur_value = 1
                    for direction in dirs:
                        cur_x = x
                        cur_y = y
                        while True:
                            cur_x += direction[0]
                            cur_y += direction[1]
                            if not (0 <= cur_x <= max_x and 0 <= cur_y <= max_y):
                                break
                            if self.board[cur_x][cur_y] == value:
                                cur_value += 1
                                max_added = max(max_added, cur_value)
                            else:
                                break

        if max_added >= 4:
            self.started = False
            await self.end(self.turn)
        elif not one_free:
            await self.end(None)

    def next_user(self):
        index = self.order.index(self.turn) + 1
        self.turn = self.order[index % len(self.order)]

    def _get_value(self, num):
        if num == 0:
            return '⚫'
        if num == 1:
            return '🔴'
        if num == 2:
            return '🔵'
        if num == 3:
            return '⚪'
        if num == 4:
            return '🟣'

    def _get_num_emoji(self, num):
        num = str(num)
        if len(num) > 1:
            num = num[-1]
        return '{0}️⃣'.format(num)

    async def send_board(self):
        horizontal = [''.join([self._get_num_emoji(r) for r in range(1, self.dimensions[0] + 1)])]
        embed = discord.Embed()
        for i in range(self.dimensions[1]):
            value = []
            for j in range(self.dimensions[0]):
                value.append(self._get_value(self.board[j][i]))
            horizontal.append(''.join(value))
        horizontal.reverse()
        if self.started:
            embed.description = '{0}\n\n{2} {1} turn! Send the column in the next 60 seconds. '.format(
                '\n'.join(horizontal),
                self.turn.user.mention,
                self._get_value(self.turn.value),
            )
        else:
            # Have to put stuff after the board to maintain formatting
            embed.description = '{0}\n\n The game ended! This is the final board! Do `{1}connectfour start` for a new one!'.format('\n'.join(horizontal), self.ctx.prefix)
        await self.ctx.send(embed=embed)

    async def start(self):
        await self.ctx.send(embed=self.ctx.create_embed('Starting!'))
        await self.setup()
        self.started = True
        for user in self.instances:
            self.order.append(user)
        random.shuffle(self.order)
        await self.send_board()
        while self.started:
            await self.loop()

    async def end(self, winner):
        self.started = False
        await self.send_board()
        if winner:
            await self.ctx.send('**{0} won!**'.format(self.turn.user.mention))
        else:
            await self.ctx.send('Stalemate!')
        await self.cleanup()

    async def add_user(self, user):
        if len(self.instances) > 2:
            return False
        self.instances.append(ConnectFourInstance(self, user, len(self.instances) + 1))
        return True

    async def remove_user(self, user):
        i = None
        for instance in self.instances:
            if instance.user.id == user.id:
                i = instance
        if i:
            self.instances.remove(i)
            if len(self.instances) < 1:
                await self.end(None)

    async def setup(self):
        await self.add_user(self.owner)
        self.turn = random.choice(self.instances)
        self.board = []
        for i in range(self.dimensions[0]):
            layer = []
            for j in range(self.dimensions[1]):
                layer.append(0)
            self.board.append(layer)

    async def cleanup(self):
        self.on_end(self)

    async def handle_join(self, ctx):
        if self.started:
            await ctx.send(embed=ctx.create_embed("This game has already started!", error=True))
            return False
        if self.user_in(ctx.author):
            await ctx.send(embed=ctx.create_embed("You're already in the game!", error=True))
            return False
        await self.add_user(ctx.author)
        await ctx.send(embed=ctx.create_embed('Added!', title='Connect Four'))
        return True
