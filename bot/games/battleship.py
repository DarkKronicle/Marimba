import asyncio
import random

import discord

from bot.util import base_game

alphabet = list('abcdefghijklmnopqrstuvwxyz')


class BattleShipInstance(base_game.BaseGameUser):

    def __init__(self, parent, user, dm, bot, *, board_size=(9, 9), ships=None):
        super().__init__(parent, user)
        if ships is None:
            ships = [5, 4, 3, 3, 2]
        self.board_size = board_size
        self.channel = dm
        self.bot = bot
        self.ships = ships
        self.board = []
        self.other = []
        for y in range(board_size[1]):
            line = []
            for x in range(board_size[0]):
                line.append(0)
            self.board.append(line)
            self.other.append(line.copy())

    def _get_value(self, num):
        if num == 0:
            return '⚫'
        if num == 1:
            return '🔵'
        if num == 2:
            return '⚪'
        if num == 3:
            return '🔴'

    def _get_num_emoji(self, num):
        num = str(num)
        if len(num) > 1:
            num = num[-1]
        return '{0}️⃣'.format(num)

    letter_to_emoji = {
        'a': '🇦',
        'b': '🇧',
        'c': '🇨',
        'd': '🇩',
        'e': '🇪',
        'f': '🇫',
        'g': '🇬',
        'h': '🇭',
        'i': '🇮',
        'j': '🇯',
        'k': '🇰',
        'l': '🇱',
        'm': '🇲',
        'n': '🇳',
    }

    def _get_letter_emoji(self, char):
        if char in self.letter_to_emoji:
            return self.letter_to_emoji[char]
        return '🇦'

    async def send_own_board(self):
        lines = ['🛳️' + ''.join([self._get_num_emoji(num) for num in range(1, self.board_size[0] + 1)])]
        for y in range(self.board_size[1]):
            chars = [self._get_letter_emoji(alphabet[y])]
            for x in range(self.board_size[0]):
                chars.append(self._get_value(self.board[x][y]))
            lines.append(''.join(chars))
        embed = discord.Embed()
        embed.set_author(name='Your board')
        embed.description = '{0}\n\n🔵 is where your ships are. ⚫ is blank space.'.format('\n'.join(lines))
        await self.channel.send(embed=embed)

    async def send_other_board(self):
        lines = ['🛳️' + ''.join([self._get_num_emoji(num) for num in range(1, self.board_size[0] + 1)])]
        for y in range(self.board_size[1]):
            chars = [self._get_letter_emoji(alphabet[y])]
            for x in range(self.board_size[0]):
                val = self.other[x][y]
                if val != 0:
                    val += 1
                chars.append(self._get_value(val))
            lines.append(''.join(chars))
        embed = discord.Embed()
        embed.set_author(name='Attack board')
        embed.description = '{0}\n\n🔴 is where you **hit**. ⚪ is where you **missed**.'.format('\n'.join(lines))
        await self.channel.send(embed=embed)

    async def send_info_board(self, result):
        if result == 2:
            result = 'Hit!'
        else:
            result = 'miss!'
        other = self.parent._not_turn()
        board = []
        for x in range(self.board_size[0]):
            line = []
            for y in range(self.board_size[1]):
                val = other.board[x][y]
                opponent_val = self.other[x][y]
                hit = opponent_val == 2
                if not hit and val != 0:
                    line.append(1)
                elif opponent_val == 0:
                    line.append(0)
                else:
                    line.append(opponent_val + 1)
            board.append(line)
        lines = ['🛳️' + ''.join([self._get_num_emoji(num) for num in range(1, self.board_size[0] + 1)])]
        for y in range(self.board_size[1]):
            chars = [self._get_letter_emoji(alphabet[y])]
            for x in range(self.board_size[0]):
                val = board[x][y]
                chars.append(self._get_value(val))
            lines.append(''.join(chars))
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name="Opponent's Attack board")
        embed.description = '{0}\n{1}\n\n🔴 is where they **hit**. ⚪ is where they **missed**. 🔵 is where your ship is **located**.'.format('\n'.join(lines), result)
        await other.channel.send(embed=embed)

    def msg_check(self):
        def response(message):
            if message.channel.id != self.channel.id:
                return False
            if message.author.id != self.user.id:
                return False
            return True
        return response

    async def setup(self):

        for ship in self.ships:
            ship_str = '🔴' + ('🔵' * (ship - 1))
            ship_message = 'Where do you want: \n\n{0}\n\nSpecify coordinates using red dot as base. For rotation use `-` (horizontal) or `|` (vertical) (rotates around red dot). Example (`A3-`)'
            ship_message = ship_message.format(ship_str)
            await self.channel.send(ship_message)
            while True:
                await self.send_own_board()
                try:
                    message = await self.bot.wait_for('message', timeout=60, check=self.msg_check())
                except:
                    await self.channel.send('Timed out!')
                    return await self.parent.timeout()
                x, y, direction = self.get_coords(message.content, get_direction=True)
                if x is None:
                    await self.channel.send('Incorrect formatting! Try again. (Example: `A7-`)', delete_after=10)
                    continue
                if not self.put_ship(x, y, direction, ship):
                    await self.channel.send('That conflicts with another ship or boundary! Try again.', delete_after=10)
                    continue
                break
            await self.send_own_board()
        await self.channel.send("Done! Waiting for everyone to finish...")

    directions = {
        '|': (0, 1),
        '-': (1, 0),
    }

    def get_coords(self, string, *, get_direction=False):
        try:
            num = int(string[1]) - 1
        except:
            if get_direction:
                return None, None, None
            return None, None
        try:
            index = alphabet.index(string[0].lower())
        except:
            if get_direction:
                return None, None, None
            return None, None
        if num < 0 or num >= self.board_size[0]:
            if get_direction:
                return None, None, None
            return None, None
        if index < 0 or index >= self.board_size[1]:
            if get_direction:
                return None, None, None
            return None, None
        if get_direction:
            try:
                return num, index, self.directions[string[2]]
            except:
                return None, None, None

        return num, index

    def put_ship(self, x, y, direction, size):
        if x < 0 or x >= self.board_size[0]:
            return False
        if y < 0 or y >= self.board_size[1]:
            return False
        if self.board[x][y] != 0:
            return False
        mess_x = x
        mess_y = y
        try:
            for i in range(size - 1):
                mess_x += direction[0]
                mess_y += direction[1]
                if self.board[mess_x][mess_y] != 0:
                    return False
        except IndexError:
            return False
        mess_x = x
        mess_y = y
        self.board[mess_x][mess_y] = 1
        for i in range(size - 1):
            mess_x += direction[0]
            mess_y += direction[1]
            self.board[mess_x][mess_y] = 1
        return True

    def win(self):
        hit = 0
        for y in range(self.board_size[1]):
            for x in range(self.board_size[0]):
                if self.other[x][y] == 2:
                    hit += 1
        amount = 0
        other_play = self.parent._not_turn().board
        for y in range(self.board_size[1]):
            for x in range(self.board_size[0]):
                if other_play[x][y] != 0:
                    amount += 1
        return hit >= amount

    def attack(self, x, y):
        try:
            if self.other[x][y] != 0:
                return None
        except:
            return None
        point = self.parent.get_other(x, y) + 1
        self.other[x][y] = point
        return point

    async def turn(self):
        await self.send_other_board()
        await self.channel.send('Where do you want to attack? (Specify coordinates i.e. `D5`)')
        x, y = None, None
        result = None
        while True:
            try:
                message = await self.bot.wait_for('message', timeout=60, check=self.msg_check())
            except:
                await self.channel.send('Timed out!')
                await self.parent.timeout()
                return None, None, None
            x, y = self.get_coords(message.content)
            if x is None:
                await self.channel.send('Incorrect formatting! Try again. (Example: `A7`)', delete_after=10)
                continue
            result = self.attack(x, y)
            if not result:
                await self.channel.send('You have already attacked there! Try again.', delete_after=10)
                continue
            break
        if self.win():
            await self.channel.send('You win!')
            await self.parent.end(self.user)
        return x, y, result


class BattleShip(base_game.BaseGame):

    def __init__(self, ctx, owner, on_end, dimensions, ships, moves=1):
        super().__init__(ctx, owner)
        self.started = False
        self.turn = None
        self.on_end = on_end
        self.dimensions = dimensions
        self.moves = moves
        self.ships = [5, 4, 3, 3, 2][:ships]

    def _not_turn(self):
        for instance in self.instances:
            if instance.user.id != self.turn.user.id:
                return instance
        return self.turn

    def get_other(self, x, y):
        return self._not_turn().board[x][y]

    async def on_message(self, message):
        # Battle ship doesn't need to do anything
        pass

    async def timeout(self):
        await self.ctx.send('Timed out! Unfortunate!')
        for u in self.instances:
            await u.channel.send('Timed out! Unfortunate!')
        await self.end(None)

    async def add_user(self, user):
        try:
            dm = await user.create_dm()
        except:
            return await self.ctx.send("Couldn't create a DM channel!", error=True)
        self.instances.append(BattleShipInstance(self, user, dm, self.ctx.bot, board_size=self.dimensions, ships=self.ships))

    async def remove_user(self, user):
        pass

    async def end(self, winner):
        await self.cleanup()
        if winner:
            await self._not_turn().channel.send("You lost!")
        else:
            await self._not_turn().channel.send('You won!')
        if winner:
            await self.ctx.send('{0} won!'.format(winner.mention))
        else:
            self.ctx.send('{0}'.format(self._not_turn().user.mention))
        self.started = False

    async def setup_user(self, instance):
        await instance.setup()

    async def setup(self):
        await self.add_user(self.owner)
        await asyncio.wait([self.setup_user(instance) for instance in self.instances])
        self.turn = random.choice(self.instances)

    async def loop(self):
        while True:
            for i in range(self.moves):
                x, y, result = await self.turn.turn()
                if not self.started:
                    return
                if result == 1:
                    await self.turn.channel.send("Miss!")
                elif result == 2:
                    await self.turn.channel.send("Hit!")
                await self.turn.send_info_board(result)
            self.turn = self._not_turn()

    async def start(self):
        await self.setup()
        for instance in self.instances:
            await instance.channel.send('Starting now!')
        await self.ctx.send('Starting! Go check your DMs!')
        self.started = True
        await self.loop()

    async def handle_join(self, ctx):
        await ctx.send(embed=ctx.create_embed("You can't join battleship mid game!", error=True))
        return False


    async def cleanup(self):
        if self.on_end:
            self.on_end(self)
