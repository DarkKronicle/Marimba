import logging
import traceback
from datetime import datetime

import discord
from discord.ext.commands import errors
from glocklib.context import Context

import bot as bot_global
from glocklib import bot

from bot.cogs import guild_config


startup_extensions = (
    'bot.cogs.guild_config',
    'bot.cogs.utility',
    'bot.cogs.random',
    'bot.games.game',
    'bot.mtg.magic',
    'bot.cogs.clip',
)
description = 'Fun bot'


async def get_prefix(bot_obj, message: discord.Message):
    user_id = bot_obj.user.id
    prefixes = ['x>', '<@!{0}> '.format(user_id)]
    space = ['x> ', '<@!{0}> '.format(user_id)]
    if message.guild is None:
        prefix = '>'
    else:
        prefix = await bot_obj.get_guild_prefix(message.guild)
        if prefix is None:
            prefix = '>'
    message_content: str = message.content
    if message_content.startswith('x> '):
        return space
    if message_content.startswith('{0} '.format(prefix)):
        space.append('{0} '.format(prefix))
        return space
    prefixes.append(prefix)
    return prefixes


class MarimbaBot(bot.Bot):

    def __init__(self, pool):

        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)

        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        super().__init__(
            pool,
            command_prefix=get_prefix,
            intents=intents,
            description=description,
            case_insensitive=True,
            owner_id=bot_global.config['owner_id'],
            allowed_mentions=allowed_mentions,
        )
        self.boot = datetime.now()
        for extension in startup_extensions:
            try:
                self.load_extension('{0}'.format(extension))

            except (discord.ClientException, ModuleNotFoundError):
                logging.warning('Failed to load extension {0}.'.format(extension))
                traceback.print_exc()

    async def get_guild_prefix(self, guild):
        settings = await guild_config.get_guild_settings(self, guild)
        if not settings:
            return '~'
        return settings.prefix

    async def on_ready(self):
        logging.info('Bot up and running!')

    def run(self):
        super().run(bot_global.config['bot_token'], reconnect=True)

    @discord.utils.cached_property
    def log(self):
        return self.get_channel(bot_global.config['log_channel'])

    async def on_command_error(self, ctx: Context, error, *, raise_err=True):
        try:
            await super().on_command_error(ctx, error, raise_err=raise_err)
        except Exception as new_exception:
            if isinstance(new_exception, errors.MissingRequiredArgument):
                await ctx.send(embed=ctx.create_embed(description="Missing argument!", error=True), delete_after=5)


