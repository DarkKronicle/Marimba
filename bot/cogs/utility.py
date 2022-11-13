import aiohttp
import discord
import typing
from discord.ext import commands
import emoji
from discord.ext.commands import BucketType
from bot.util import paginator
from bot.core.context import Context


class ReplyConverter(commands.Converter):

    async def convert(self, ctx: Context, argument):
        try:
            message = await commands.MessageConverter().convert(ctx, argument)
        except:
            pass
        else:
            if message:
                return message
        args = argument.split(' ')
        if not args:
            raise commands.BadArgument('No channel specified')
        try:
            channel = await commands.TextChannelConverter().convert(ctx, args[0])
        except:
            raise commands.BadArgument('Channel {0} could not be found'.format(args[0]))
        args.pop(0)
        if not args:
            obj = discord.Object(channel.last_message_id + 1)
            msg = await channel.history(limit=1, before=obj).next()
            if not msg:
                raise commands.BadArgument("Couldn't fetch last message in {0}. Try message ID.".format(channel.mention))
            return msg
        try:
            message_id = int(args[0])
        except:
            raise commands.BadArgument('{0} has to be an integer!'.format(args[0]))
        obj = discord.Object(message_id + 1)
        msg = await channel.history(limit=1, before=obj).next()
        if not msg:
            raise commands.BadArgument("Couldn't fetch message in {0}. Try message link.".format(channel.mention))
        return msg


class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(1, 5, type=commands.BucketType.user)
    @commands.command(name='ping')
    async def ping(self, ctx):
        """
        Pings the bot and gets the millisecond delay.
        """
        time0 = ctx.message.created_at
        sent = await ctx.send('Pinging')
        time1 = sent.created_at
        dif1 = round((time1 - time0).total_seconds() * 1000)
        await sent.edit(content='Pong! Pinging time was {0}ms'.format(dif1))

    @commands.command(name='regional')
    async def regional(self, ctx, *, character: str):
        try:
            character = int(character)
            await ctx.send('{0}️⃣'.format(character))
        except:
            pass
        return await ctx.send(emoji.emojize(':regional_indicator_{0}:'.format(character[0])))

    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @commands.command(name='user')
    async def user(self, ctx: Context, user: discord.Member = None):
        """
        Get's information about a user.

        Examples:
            user
            user DarkKronicle
        """
        if user is None:
            user = ctx.author
        pfp = user.avatar_url
        embed = ctx.create_embed(title=str(user))
        embed.set_image(url=pfp)
        description = 'Created: `{0.created_at}`'.format(user)
        embed.description = description
        await ctx.send(embed=embed)

    @commands.command(name='roles')
    @commands.guild_only()
    @commands.cooldown(1, 10, type=commands.BucketType.user)
    async def roles(self, ctx: Context, user: typing.Optional[discord.Member] = None):
        """
        Displays the roles a user has.

        Examples:
            roles @DarkKronicle
            roles Fury
            roles
        """
        if not user:
            user = ctx.author
        entries = []
        for role in user.roles:
            role: discord.Role
            entries.append('{0}\n```\n  Colour: {2}\n  Members: {3}\n  id {1}\n```'
                           .format(role.mention, role.id, str(role.colour), len(role.members)))
        page = paginator.SimplePages(entries, embed=ctx.create_embed(title='Roles for {0}'.format(str(user))),
                                     per_page=5)
        try:
            await page.start(ctx)
        except:
            pass

    @commands.command(name='newmembers', aliases=['freshmeat', 'fresh'])
    @commands.guild_only()
    async def new_members(self, ctx: Context):
        members_sorted = list(sorted(ctx.guild.members, key=lambda member: member.joined_at, reverse=True))
        if not members_sorted:
            return await ctx.send(embed=ctx.create_embed('No members...'))
        if len(members_sorted) > 10:
            members_sorted = members_sorted[:10]
        description = '\n'.join(
            ['`{0}` {1}'.format(member.joined_at.strftime('%m/%d %H:%M'), member.mention) for member in members_sorted]
        )
        await ctx.send(embed=ctx.create_embed(description))

    @commands.cooldown(1, 10, BucketType.user)
    @commands.command(name='aaa')
    async def aaa(self, ctx: Context, *, url: str):
        """
        Simplifies a URL
        """
        txt = None
        if not url.startswith('https://'):
            url = 'https://{0}'.format(url)
        await ctx.trigger_typing()
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.com/a?url={0}'.format(url)) as r:
                if r.status == 200:
                    txt = await r.text()
        if txt is None:
            return await ctx.send(embed=ctx.create_embed('Something went wrong!', error=True), delete_after=5)
        await ctx.send(embed=ctx.create_embed(txt))


async def setup(bot):
    await bot.add_cog(Utility(bot))
