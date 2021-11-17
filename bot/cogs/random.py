import re
import datetime
from pathlib import Path

import asyncio

import aiohttp
import discord
import typing
from discord.ext import commands
import random
import sys

from glocklib.context import Context

from bot.util import paginator
from bot.util.json_reader import JsonReader


def seed_func(seed, func, *args, **kwargs):
    random.seed(seed)
    value = func(*args, **kwargs)
    new_seed = random.randrange(sys.maxsize)
    random.seed(new_seed)
    return value


def seed_int(seed, min_num, max_num):
    return seed_func(seed, random.randint, min_num, max_num)


def seed_choice(seed, options):
    return seed_func(seed, random.choice, options)


def get_ceil(data, num):
    options = list(sorted([(int(key), value) for key, value in data.items()], key=lambda item: item[0], reverse=True))
    for value, key in options:
        if value <= num:
            return key
    return options[-1][1]


class Random(commands.Cog):

    keys = {
        1: 'singleQuotes',
        2: 'doubleQuotes',
        3: 'tripleQuotes',
        4: 'quadQuotes',
        5: 'pentaQuotes',
        6: 'hexaQuotes',
    }

    ADD_REGEX = re.compile(r'^[A-Za-z0-9 ]{2}')

    def __init__(self, bot):
        self.bot = bot
        self.quotes = JsonReader(Path('storage/incorrect_quotes.json'))
        self.random_data = JsonReader(Path('storage/random.json'))
        self.cache = {}
        self.last_type: datetime.datetime = None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        await self._add_message(message)
        await self._send_out_of_context(message)

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        if (self.last_type is None or (when - self.last_type).total_seconds() > 120) and random.random() < 0.1:
            self.last_type = when
            async with channel.typing():
                await asyncio.sleep(3)

    async def _add_message(self, message):
        if message.guild.id not in self.cache:
            self.cache[message.guild.id] = []
        text = message.clean_content
        if not text or message.channel.is_nsfw():
            return

        if len(text) > 100:
            return

        if not self.ADD_REGEX.search(text):
            return

        self.cache[message.guild.id].append(text)
        if len(self.cache[message.guild.id]) > 20:
            i = random.randint(0, 19)
            self.cache[message.guild.id].pop(i)

    async def _send_out_of_context(self, message):
        if message.author.bot:
            return
        num = random.random()
        if num < 0.05:
            await self.out_of_context(message)

    async def out_of_context(self, message):
        if len(self.cache[message.guild.id]) > 0:
            selection = random.choice(self.cache[message.guild.id])
        else:
            return
        ctx = await self.bot.get_context(message, cls=self.bot.context)
        if selection:
            async with ctx.typing():
                await asyncio.sleep(1)
                await message.channel.send(selection)

    @commands.command(name='incorrectquote', aliases=['quote'])
    async def incorrect_quote(self, ctx: Context, *names):
        if not names:
            return await ctx.send(embed=ctx.create_embed('You have to specify at least one person!'))
        names = list(names)
        random.shuffle(names)
        num = len(names)
        if num not in self.keys:
            return await ctx.send(embed=ctx.create_embed("That amount of people aren't allowed!"))
        key = self.keys[num]
        quotes = self.quotes[key]['shipping'] + self.quotes[key]['nonshipping']

        def get_quote(msg_ctx):
            quote = random.choice(quotes).replace('  ', '\n')
            for i in range(num):
                quote = quote.replace('[p{0}]'.format(i + 1), '**{0}**'.format(names[i]))
            return quote

        menu = paginator.Refresh(get_quote)
        await menu.start(ctx)

    @commands.command(name='inspirobot')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def inspirobot(self, ctx: Context):
        url = 'http://inspirobot.me/api?generate=true'
        text = None
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    text = await r.text('utf-8')
        if not text:
            return await ctx.send(embed=ctx.create_embed('Something went wrong!', error=True))
        embed = ctx.create_embed()
        embed.set_image(url=text)
        await ctx.send(embed=embed)

    @commands.command(name='rate')
    async def rate(self, ctx: Context, *, user: discord.Member = None):
        if not user:
            user = ctx.author
        if await self.bot.is_owner(user):
            return await ctx.send('Now this may be kinda lame, but I am legally obligated to say this guy is 1000/10. *woooo*')
        if user.id == self.bot.user.id:
            return await ctx.send("You're asking about me??? I would say I'm *pretty pog*.")
        num = seed_int(user.id, 0, 10)
        choice = seed_choice(user.id, get_ceil(self.random_data['rate'], num))
        await ctx.send(choice.format(num=num, person=user.display_name))

    def simp_percent(self, person, target):
        return seed_int(person.id - target.id, 0, 100)

    def compat_level(self, person, target):
        return seed_int(person.id + target.id, 0, 50)

    @commands.command(name='simp')
    @commands.guild_only()
    async def simp(self, ctx: Context, user1: discord.Member = None, *, user2: typing.Optional[discord.Member] = None):
        if user1 is None:
            user1 = ctx.author
        if user2 is None:
            # Simp the most
            highest = -1
            highest_user = None
            for member in ctx.guild.members:
                percent = self.simp_percent(user1, member)
                if percent > highest:
                    highest = percent
                    highest_user = member
            return await ctx.send('{0} simps for {1} the most. A total of **{2}%**'.format(
                user1.display_name,
                highest_user.display_name,
                highest,
            ))
        percent = self.simp_percent(user1, user2)
        await ctx.send('{0} simps for {1} a total of **{2}%**.'.format(
            user1.display_name,
            user2.display_name,
            percent,
        ))

    @commands.command(name='compatibility', aliases=['ship', 'compat'])
    @commands.guild_only()
    async def compat(self, ctx: Context, user1: discord.Member = None, *, user2: typing.Optional[discord.Member] = None):
        if user1 is None:
            user1 = ctx.author
        if user2 is None:
            # Simp the most
            highest = -1
            highest_user = None
            for member in ctx.guild.members:
                level = self.compat_level(user1, member)
                if level > highest:
                    highest = level
                    highest_user = member
            return await ctx.send('{0} is most compatible with {1}! A total of **{2}/50**'.format(
                user1.display_name,
                highest_user.display_name,
                highest,
            ))
        level = self.compat_level(user1, user2)
        await ctx.send(seed_choice(user1.id + user2.id, get_ceil(self.random_data['compat'], level)).format(
            person1=user1.display_name,
            person2=user2.display_name,
            level=level,
        ))


def setup(bot):
    bot.add_cog(Random(bot))
