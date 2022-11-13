from bot.util import checks
from bot.util import database as db
from bot.core.context import Context
from discord.ext import commands
from bot.util import cache
import re


async def get_guild_settings(bot, guild):
    """Get's basic guild settings information."""
    cog = bot.get_cog('GuildConfig')
    if cog is None:
        return GuildSettings.get_default(guild)
    return await cog.get_settings(guild.id)


class GuildConfigTable(db.Table, table_name='guild_config'):
    guild_id = db.Column(db.Integer(big=True), unique=True, index=True)
    prefix = db.Column(db.String(length=12), default='x>')  # noqa: WPS432
    mtg_inline = db.Column(db.String(), default='')


class GuildSettings:
    __slots__ = ('guild', 'prefix', 'mtg_inline')

    def __init__(self, guild, prefix, mtg_inline):
        self.guild = guild
        self.prefix = prefix
        self.mtg_inline = mtg_inline

    @classmethod
    def get_default(cls, guild):
        return cls(guild, '>,$', '')


async def get_guild_settings(bot, guild):
    """Get's basic guild settings information."""
    cog = bot.get_cog('GuildConfig')
    if cog is None:
        return GuildSettings.get_default(guild)
    return await cog.get_settings(guild.id)


class GuildConfig(commands.Cog):
    """Configure and view server settings."""

    def __init__(self, bot):
        self.bot = bot

    @cache.cache()
    async def get_settings(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None
        command = 'SELECT prefix, mtg_inline FROM guild_config WHERE guild_id = {0};'
        command = command.format(guild_id)
        async with db.MaybeAcquire(pool=self.bot.pool) as con:
            entry = await con.fetchrow(command)
        if entry is None:
            return GuildSettings.get_default(guild)
        return GuildSettings(guild, entry['prefix'], entry['mtg_inline'])

    @commands.command(name='!prefix')
    @checks.is_manager()
    async def prefix(self, ctx: Context, *, prefix: str = None):
        """
        Change's the server's prefix. The global prefix m$ will always be accessible.
        Examples:
              !prefix ~
              !prefix {}
        """
        if prefix is None or len(prefix) > 6 or len(prefix) < 1:
            return await ctx.send('You need to specify a prefix of max length 6 and minimum length 1!')
        command = 'INSERT INTO guild_config(guild_id, prefix) VALUES ({0}, $1) ON CONFLICT (guild_id) DO UPDATE SET prefix = EXCLUDED.prefix;'  # noqa: WPS323
        command = command.format(str(ctx.guild.id))
        async with db.MaybeAcquire(pool=self.bot.pool) as con:
            await con.execute(command, prefix)
        self.get_settings.invalidate(self, ctx.guild.id)
        await ctx.send(embed=ctx.create_embed(description='Updated prefix to `{0}`'.format(prefix)))

    @commands.command(name='prefix')
    async def _prefix(self, ctx: Context):
        """
        Displays the server's current prefix.
        """
        data = await self.get_settings(ctx.guild.id)
        if data is None:
            prefix = 'm$'
        else:
            prefix = data.prefix
        await ctx.send(embed=ctx.create_embed(description='Current prefix is: `{0}`'.format(prefix)))

    @commands.command(name='!mtgregex')
    @checks.is_manager()
    async def mtg_regex(self, ctx: Context, *, regex: str = None):
        if regex is None:
            return await ctx.send(embed=ctx.create_embed('You have to provide regex! An example for would be `;(.*?);`. Make sure the first group captures card name!'))
        try:
            re.compile(regex)
        except:
            return await ctx.send(embed=ctx.create_embed('That regex is invalid!', error=True))
        command = 'INSERT INTO guild_config(guild_id, mtg_inline) VALUES ({0}, $1) ON CONFLICT (guild_id) DO UPDATE SET mtg_inline = EXCLUDED.mtg_inline;'
        command = command.format(str(ctx.guild.id))
        async with db.MaybeAcquire(pool=self.bot.pool) as con:
            await con.execute(command, regex)
        self.get_settings.invalidate(self, ctx.guild.id)
        await ctx.send(embed=ctx.create_embed('Updated mtg inline to `{0}`.'.format(regex)))


async def setup(bot):
    await bot.add_cog(GuildConfig(bot))
