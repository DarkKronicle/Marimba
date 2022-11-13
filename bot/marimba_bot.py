import logging
import math
import traceback
import typing
from datetime import datetime

import discord
from bot.core.context import Context

import bot as bot_global

from discord.ext import commands

from bot.cogs import guild_config


startup_extensions = (
    'bot.cogs.guild_config',
    'bot.cogs.utility',
    'bot.cogs.random',
    'bot.games.game',
    'bot.mtg.magic',
    'bot.cogs.clip',
    'bot.cogs.graph',
)
description = 'Fun bot'


async def get_prefix(bot_obj, message: discord.Message):
    return ['$', 'x>']


class MarimbaBot(commands.Bot):

    def __init__(self, pool, **kwargs):
        self.debug = bot_global.config.get('debug', False)
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
        self.pool = pool
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
            message_content=True,
        )
        super().__init__(
            command_prefix='&' if not self.debug else '$',
            intents=intents,
            case_insensitive=True,
            owner_id=523605852557672449,
            allowed_mentions=allowed_mentions,
            tags=False,
            **kwargs,
        )
        self.boot = datetime.now()
        self.loops = {}
        self.on_load = []

    async def setup_hook(self) -> None:
        for extension in startup_extensions:
            try:
                await self.load_extension(extension)
            except (discord.ClientException, ModuleNotFoundError):
                logging.warning('Failed to load extension {0}.'.format(extension))
                traceback.print_exc()

    async def get_guild_prefixes(self, guild):
        settings = await guild_config.get_guild_settings(self, guild)
        if not settings:
            return ['>']
        return settings.prefix.split(',')

    async def get_guild_prefix(self, guild):
        prefixes = await self.get_guild_prefixes(guild)
        return ', '.join(prefixes)

    async def on_ready(self):
        logging.info('Bot up and running!')

    def run(self):
        super().run(bot_global.config['bot_token'], reconnect=True)

    @discord.utils.cached_property
    def log(self):
        return self.get_channel(bot_global.config['log_channel'])

    async def get_context(self, origin: typing.Union[discord.Interaction, discord.Message], /, *, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def on_command_error(self, ctx, error, *, raise_err=True):  # noqa: WPS217
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.CommandOnCooldown):
            if await self.is_owner(ctx.author):
                # We don't want the owner to be on cooldown.
                await ctx.reinvoke()
                return
            # Let people know when they can retry
            embed = ctx.create_embed(
                title='Command On Cooldown!',
                description='This command is currently on cooldown. Try again in `{0}` seconds.'.format(math.ceil(error.retry_after)),
                error=True,
            )
            await ctx.delete()
            await ctx.send(embed=embed, delete_after=5)
            return
        if raise_err:
            raise error
