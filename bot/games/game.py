import asyncio

import typing

import discord
from discord.ext import commands
from bot.util import paginator
from bot.core.context import Context

from bot.games.anagrams import AnagramGame
from bot.games.battleship import BattleShip
from bot.games.connect_four import ConnectFour
from bot.games.onthespot import OnTheSpot
from bot.games.rock_paper_scissors import RPSGame
from bot.util.game_storage import GameStorage
from bot.util.onthespot_deck import OnTheSpotDeckHolder
from bot.util.word_storage import WordStorage


class Games(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.games = GameStorage()
        self.ots_decks = OnTheSpotDeckHolder()
        self.word_storage = WordStorage()

    @commands.Cog.listener()
    async def on_message(self, message):
        game = self.games.get_channel(message.channel.id)
        if not game:
            return
        if game.game_obj.user_in(message.author):
            await game.game_obj.on_message(message)

    @commands.group(name='battleship')
    @commands.guild_only()
    async def battleship(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help('battleship')

    @battleship.command(name='start')
    async def battle_start(self, ctx: Context, other: discord.Member, dimensions: int = 9, ships: int = 5, moves: int = 1):
        if dimensions > 9 or dimensions < 5:
            return await ctx.send(embed=ctx.create_embed('Dimensions cannot be that!', error=True))
        if ships > 5 or ships < 1:
            return await ctx.send(embed=ctx.create_embed('Ships cannot be that!', error=True))
        if moves < 1 or moves > 10:
            return await ctx.send(embed=ctx.create_embed('Moves cannot be that!', error=True))
        if ctx.channel.id in self.games:
            return await ctx.send(embed=ctx.create_embed("There's already a game in this channel!", error=True))
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You're already in a game!", error=True))
        if other.id in self.games:
            return await ctx.send(embed=ctx.create_embed("That person is already in a game!", error=True))
        result = await ctx.ask('Does {0} accept battleship from {1}? (Say `yes` or `no`)'.format(other.mention, ctx.author.mention), author_id=other.id)
        if not result or result.lower() != 'yes':
            return await ctx.send(embed=ctx.create_embed('Cancelled!', error=True))
        ship = BattleShip(ctx, ctx.author, self.end, (dimensions, dimensions), ships, moves)
        self.games.create_game(ship, ctx.guild.id, None)
        await ship.add_user(other)
        await ship.start()

    @commands.group(name='rps')
    @commands.guild_only()
    async def rps(self, ctx, *, other: discord.Member):
        if ctx.invoked_subcommand is None:
            result = await ctx.ask(
                'Does {0} accept rock paper scissors from {1}? (Say `yes` or `no`)'.format(other.mention,
                                                                                           ctx.author.mention),
                author_id=other.id)
            if not result or result.lower() != 'yes':
                return await ctx.send(embed=ctx.create_embed('Cancelled!', error=True))
            rps = RPSGame(ctx, ctx.author)
            await rps.add_user(other)
            await rps.start()

    @rps.command(name='start')
    async def rps_start(self, ctx: Context, *, other: discord.Member):
        result = await ctx.ask('Does {0} accept rock paper scissors from {1}? (Say `yes` or `no`)'.format(other.mention, ctx.author.mention), author_id=other.id)
        if not result or result.lower() != 'yes':
            return await ctx.send(embed=ctx.create_embed('Cancelled!', error=True))
        rps = RPSGame(ctx, ctx.author)
        await rps.add_user(other)
        await rps.start()

    @commands.group(name='onthespot', aliases=['ots'])
    async def on_the_spot(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help('onthespot')

    @on_the_spot.command(name='start')
    async def on_the_spot_start(self, ctx: Context):
        if ctx.channel.id in self.games or ctx.author.id in self.games:
            return await ctx.send("Only one game at a time!")
        ots = OnTheSpot(ctx, ctx.author, self.end, self.ots_decks['base'])
        self.games.create_game(ots, ctx.guild.id, ctx.channel.id)
        await ctx.send(
            embed=ctx.create_embed('Waiting one minute to start On The Spot! Do `{0}join` to join!'.format(ctx.prefix))
        )
        await asyncio.sleep(60)
        await ots.start()

    @commands.group(name='connectfour', aliases=['c4'])
    @commands.guild_only()
    async def connect_four(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help('connectfour')

    @connect_four.command(name='start')
    async def c4_start(self, ctx: Context, width: typing.Optional[int] = 9, height: typing.Optional[int] = 7):
        if ctx.channel.id in self.games:
            game = self.games.get_channel(ctx.channel.id).game_obj
            if game.started:
                return await ctx.send(embed=ctx.create_embed("You're already hosting a game!"))
            if not isinstance(game, ConnectFour):
                return await ctx.send(embed=ctx.create_embed("There's already a game in this channel!", error=True))
            if ctx.author.id == game.owner.id:
                return await game.start()
            else:
                return await ctx.send(embed=ctx.create_embed("You aren't in charge of the game!"))
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't be in multiple games!", error=True))
        if width < 2 or height < 2:
            return await ctx.send(embed=ctx.create_embed('Too small dimensions!', error=True))
        if width > 20 or height > 20:
            return await ctx.send(embed=ctx.create_embed('Too big dimensions!'))
        c4 = ConnectFour(ctx, ctx.author, self.end, dimensions=(width, height))
        self.games.create_game(c4, ctx.guild.id, ctx.channel.id)
        await ctx.send(
            embed=ctx.create_embed('Waiting one minute to start...\nDo `{0}join` to enter!'.format(ctx.prefix))
        )
        await asyncio.sleep(60)
        if not c4.started and ctx.channel.id in self.games:
            await c4.start()

    @commands.command(name='join')
    async def c4_join(self, ctx: Context):
        if ctx.channel.id not in self.games:
            return await ctx.send(embed=ctx.create_embed("There is no game in this channel!", error=True))
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You're already part of a game!", error=True))
        await self.games.handle_join(ctx)

    @commands.group(name='anagram', aliases=['anagrams'], invoke_without_command=True)
    async def anagram(self, ctx: Context, *, word: typing.Optional[str] = None):
        if ctx.invoked_subcommand is not None:
            return
        await self.find_anagrams(ctx, word)

    @anagram.command(name='find')
    async def anagram_find(self, ctx: Context, *, word: typing.Optional[str] = None):
        await self.find_anagrams(ctx, word)

    @anagram.command(name='multiword')
    async def anagram_multiword(self, ctx: Context, *, word: typing.Optional[str] = None):
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game!", error=True))
        if ctx.channel.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game! DM me to get anagrams.", error=True))
        if word is None:
            word = self.word_storage.get_anagram_word(8)
        if len(word) > 30:
            return await ctx.send('30 characters is the max!')
        if len(word) < 4:
            return await ctx.send('Has to be at least 4 length!')
        anagrams = self.word_storage.anagram(word, min_length=4, multi_word=True)
        if len(anagrams) < 1:
            return await ctx.send('No anagrams found!')
        embed = ctx.create_embed(title='Anagrams for {0}'.format(word))
        pages = paginator.SimplePages(anagrams, embed=embed)
        await pages.start(ctx)

    @anagram.command(name='exact')
    @commands.is_owner()
    async def anagram_multiword(self, ctx: Context, *, word: typing.Optional[str] = None):
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game!", error=True))
        if ctx.channel.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game! DM me to get anagrams.", error=True))
        if word is None:
            word = self.word_storage.get_anagram_word(8)
        if len(word) > 30:
            return await ctx.send('30 characters is the max!')
        if len(word) < 4:
            return await ctx.send('Has to be at least 4 length!')
        anagrams = self.word_storage.anagram(word, multi_word=True, exact=True)
        if len(anagrams) < 1:
            return await ctx.send('No anagrams found!')
        embed = ctx.create_embed(title='Anagrams for {0}'.format(word))
        pages = paginator.SimplePages(anagrams, embed=embed)
        await pages.start(ctx)

    async def find_anagrams(self, ctx: Context, word):
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game!", error=True))
        if ctx.channel.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't find anagrams in the middle of a game! DM me to get anagrams.", error=True))
        if word is None:
            word = self.word_storage.get_anagram_word(8)
        if len(word) > 50:
            return await ctx.send('50 characters is the max!')
        if len(word) < 4:
            return await ctx.send('Has to be at least 4 length!')
        anagrams = self.word_storage.anagram(word, min_length=4)
        if len(anagrams) < 1:
            return await ctx.send('No anagrams found!')
        embed = ctx.create_embed(title='Anagrams for {0}'.format(word))
        pages = paginator.SimplePages(anagrams, embed=embed)
        await pages.start(ctx)

    @anagram.command(name='start')
    async def anagram_start(self, ctx: Context):
        if ctx.channel.id in self.games:
            game = self.games.get_channel(ctx.channel.id).game_obj
            if game.started:
                return await ctx.send(embed=ctx.create_embed("You're already hosting a game!"))
            if not isinstance(game, AnagramGame):
                return await ctx.send(embed=ctx.create_embed("There's already a game in this channel!", error=True))
            if ctx.author.id == game.owner.id:
                return await game.start()
            else:
                return await ctx.send(embed=ctx.create_embed("You aren't in charge of the game!"))
        if ctx.author.id in self.games:
            return await ctx.send(embed=ctx.create_embed("You can't be in multiple games!", error=True))
        ana = AnagramGame(self.word_storage, ctx, ctx.author, self.end)
        self.games.create_game(ana, ctx.guild.id, ctx.channel.id)
        await ctx.send(
            embed=ctx.create_embed('Waiting one minute to start...\nDo `{0}join` to enter!'.format(ctx.prefix))
        )
        await asyncio.sleep(60)
        if not ana.started and ctx.channel.id in self.games:
            await ana.start()

    def end(self, game):
        self.games.end_game(game)


async def setup(bot):
    await bot.add_cog(Games(bot))
