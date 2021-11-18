import io

import aiohttp
import discord
import typing
from discord.ext import commands
import emoji
from discord.ext.commands import BucketType
from glocklib import paginator
from glocklib.context import Context

from bot.util import embed_utils


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

    @commands.group(name='embed', invoke_without_command=True)
    async def embed_command(self, ctx: Context, *, embed_data):
        try:
            embed = embed_utils.deserialize_string(embed_data)
        except Exception as e:
            return await ctx.send(embed=ctx.create_embed(e, title='Invalid embed!', error=True))
        await ctx.send(embed=embed)

    @embed_command.command(name='create')
    async def embed_create(self, ctx: Context):
        try:
            answers = await embed_utils.get_creation_menu().ask(ctx, default='')
        except:
            return await ctx.send(embed=ctx.create_embed('Timed out!', error=True))
        if len(answers['title']) == 0 and len(answers['description']) == 0:
            return await ctx.send(embed=ctx.create_embed("Title and description can't be none!", error=True))

        embed = embed_utils.embed_from_answers(answers)
        await ctx.send(embed=embed, reference=ctx.message)
        serial = embed_utils.serialize(embed)
        file = io.StringIO()
        file.write(serial)
        file.seek(0)
        discord_file = discord.File(file, filename='embed.json')
        await ctx.send("Here's the serialized data!", file=discord_file)

    @commands.command(name='reply', aliases=['r', 'respond'])
    @commands.guild_only()
    async def reply(self, ctx: Context, msg: ReplyConverter):
        """
        Mentions a message from anywhere in the guild.

        Clicking on the title will take you to the original message.

        Examples:
            quote #general
            quote <channel_id>--<message_id>
            quote #general <message_id>
            quote <message_link>
        """
        msg: discord.Message
        if msg.guild.id != ctx.guild.id:
            return await ctx.send(embed=ctx.create_embed('The message has to be in this guild!', error=True))
        if msg.channel.is_nsfw() and not ctx.channel.is_nsfw():
            return await ctx.send(embed=ctx.create_embed("Can't respond to a NSFW message in a normal channel!"))

        embed = discord.Embed()
        if isinstance(msg.author, discord.Member):
            embed.colour = msg.author.colour

        link = msg.jump_url
        embed.set_author(name='{0} mentions:'.format(str(ctx.author)), url=link)
        embed.set_footer(
            text='{0} in #{1}'.format(msg.author, msg.channel),
            icon_url=msg.author.avatar_url,
        )
        embed.timestamp = msg.created_at
        text = msg.content
        if not text:
            if msg.embeds:
                for e in msg.embeds:
                    if e.description:
                        text = e.description
                        break
            if not text:
                text = 'Nothing...'
        if len(text) > 200:
            text = text[:97] + '...'
        embed.description = '\n\n{0}'.format(text)
        await ctx.send(embed=embed)
        await ctx.delete()

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


def setup(bot):
    bot.add_cog(Utility(bot))
