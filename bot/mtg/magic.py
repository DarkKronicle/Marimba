import asyncio
import scrython

from bot.mtg import card_views
from bot.util import queue as async_queue

from discord.ext import commands
from glocklib.context import Context


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
        await ctx.send(embed=card_views.card_image_embed(card))


def setup(bot):
    bot.add_cog(Magic(bot))
