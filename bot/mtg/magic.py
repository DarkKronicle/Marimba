import asyncio
import re

import discord
import scrython
from scrython.cards.cards_object import CardsObject

from bot.cogs import guild_config
from bot.mtg.card_search import CardSearch, CardPrintsSource
from bot.mtg.magic_page import SingleCardMenu
from bot.util import queue as async_queue, queue

from discord.ext import commands, menus
from glocklib.context import Context
import rules


class Searched(CardsObject):

    def __init__(self, json, **kwargs):
        super().__init__(_url="", **kwargs)
        self.scryfallJson = json


class MagicCard(commands.Converter):

    def __init__(self, queue, *, raise_again=True):
        self.queue = queue
        self.raise_again = raise_again

    async def convert(self, ctx: Context, argument):
        async with ctx.typing():
            async with async_queue.QueueProcess(self.queue):
                try:
                    card = scrython.cards.Named(fuzzy=argument)
                    await card.request_data(loop=ctx.bot.loop)
                except scrython.foundation.ScryfallError as e:
                    if self.raise_again:
                        raise e
                    await asyncio.sleep(0.1)
                    auto = scrython.cards.Autocomplete(q=argument)
                    await auto.request_data(loop=ctx.bot.loop)
                    searches = auto.data()
                    if len(searches) > 10:
                        searches = searches[:10]
                    if len(searches) == 0:
                        extra = ". Maybe use the search command to view other cards."
                    else:
                        extra = ". Did you mean:\n" + "\n".join(searches)
                    raise commands.BadArgument(e.error_details['details'] + extra)
        return card


class Magic(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queue = async_queue.SimpleQueue(self.bot, 0.5)

    @commands.group(name='magic', aliases=['mtg', 'm'], invoke_without_command=True)
    async def magic(self, ctx: Context, *, search: str):
        if ctx.invoked_subcommand:
            return
        try:
            card = await MagicCard(self.queue).convert(ctx, search)
        except commands.BadArgument as e:
            return await ctx.send(e)
        pages = SingleCardMenu(card)
        await pages.start(ctx)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if message.author.id == self.bot.user.id:
            # No recursion
            return
        settings = await guild_config.get_guild_settings(self.bot, message.guild)
        if settings.mtg_inline == '' or settings.mtg_inline is None:
            return
        try:
            cards = [f.group(1) for f in re.finditer(settings.mtg_inline, message.content)]
            if len(cards) == 0:
                return
            ctx = await self.bot.get_context(message)
            card = await MagicCard(self.queue).convert(ctx, cards[0])
            pages = SingleCardMenu(card)
            await pages.start(ctx)
        except:
            pass

    @magic.command(name="search")
    async def search(self, ctx: Context, *, card=None):
        """
        Search for cards. Use https://scryfall.com/docs/syntax for complex formatting.
        """
        if card is None:
            return await ctx.send_help('mtg search')
        await self.trigger_search(ctx, card)

    async def trigger_search(self, ctx, query):
        async with ctx.typing():
            async with queue.QueueProcess(queue=self.queue):
                try:
                    cards = scrython.cards.Search(q=query)
                    await cards.request_data()
                except scrython.foundation.ScryfallError as e:
                    return await ctx.send(e.error_details["details"])
        if len(cards.data()) == 0:
            return await ctx.send("No cards with that name found.")
        try:
            p = CardSearch([Searched(c) for c in cards.data()], query, embed=ctx.create_embed())
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)
            return

    @magic.command(name="collectors", aliases=["cr"])
    async def collectors_card(self, ctx: Context, set_code: str = None, *, code: int = None):
        """
        Gets a card based off of it's collecters number.
        """
        if code is None:
            return await ctx.send_help('mtg cr')
        if set_code is None:
            return await ctx.send_help('mtg cr')
        async with ctx.typing():
            async with queue.QueueProcess(queue=self.queue):
                try:
                    card = scrython.cards.Collector(code=code, collector_number=code)
                    await card.request_data(loop=ctx.bot.loop)
                except scrython.foundation.ScryfallError as e:
                    raise commands.BadArgument(e.error_details['details'])
        pages = SingleCardMenu(card)
        await pages.start(ctx)

    @magic.command(name="random")
    async def random(self, ctx: Context):
        """
        Gets a card based off of it's name.
        """
        async with ctx.typing():
            async with queue.QueueProcess(queue=self.queue):
                card = scrython.cards.Random()
                await card.request_data(loop=ctx.bot.loop)

        pages = SingleCardMenu(card)
        await pages.start(ctx)

    @magic.command(name="key")
    async def key(self, ctx: Context):
        """
        Shows what symbols Xylo uses for MTG
        """
        message = "🇺 - Uncommon\n🇨 - Common\n🇷 - Rare\n🇲 - Mythic\n✨ - Foil\n💵 - Promo\n📘 - Story\n⛔ - Reserved"
        embed = ctx.create_embed(
            title="Marimba Symbols",
            description=message
        )
        await ctx.send(embed=embed)

    @magic.command(name="prints", aliases=['print', 'p'])
    async def prints(self, ctx: Context, *, card_name):
        card = await MagicCard(self.queue).convert(ctx, card_name)
        if card is None:
            return await ctx.send(embed=ctx.create_embed('Invalid card!', error=True))
        kwargs = {
            'q': 'oracleid:{0}'.format(card.oracle_id()),
            'order': 'released',
            'unique': 'prints',
        }
        async with ctx.typing():
            async with queue.QueueProcess(queue=self.queue):
                try:
                    cards = scrython.cards.Search(**kwargs)
                    await cards.request_data()
                except scrython.foundation.ScryfallError as e:
                    print("rip!")
                    return await ctx.send(e.error_details["details"])
        if len(cards.data()) == 0:
            return await ctx.send("No cards with that name found.")
        try:
            p = CardSearch([Searched(c) for c in cards.data()], card.name(), embed=ctx.create_embed(), source=CardPrintsSource)
            await p.start(ctx)
        except menus.MenuError as e:
            await ctx.send(e)

    @magic.command(name="define")
    async def define(self, ctx: Context, *, keyword=None):
        """
        Defines a keyword using MTG Rules
        """
        if keyword is None:
            return await ctx.send('mtg define')
        gloss = rules.lookup(keyword)
        if gloss is None:
            return await ctx.send("Nothing was found!")
        embed = discord.Embed(
            title=keyword,
            description=gloss,
            colour=discord.Colour.dark_grey()
        )
        await ctx.send(embed=embed)

    @magic.command(name="notes")
    async def notes(self, ctx: Context, *, card=None):
        """
        Gets a card based off of it's name.
        """
        # TODO make this a menu since there can be lots of info.
        if card is None:
            return await ctx.send_help('mtg notes')
        async with ctx.typing():
            card = await MagicCard(queue=self.queue, raise_again=False).convert(ctx, card)
            if card is None:
                return await ctx.send_help('mtg notes')
            async with queue.QueueProcess(self.queue):
                rulings = scrython.Id(id=card.id())
                await rulings.request_data()
            await ctx.send(embed=rulings_embed(card, rulings))


def setup(bot):
    bot.add_cog(Magic(bot))
