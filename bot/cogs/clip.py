import discord
import typing
from discord.ext import commands
from bot.util import embed_utils
from glocklib import database as db, checks, paginator

# Based off of https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/tags.py
# MPL v2
from glocklib.context import Context


class ClipPageEntry:
    __slots__ = ('id', 'name')

    def __init__(self, entry):
        self.id = entry['id']
        self.name = entry['name']

    def __str__(self):
        return '{0.name} (ID: {0.id})'.format(self)


class ClipPages(paginator.SimplePages):
    def __init__(self, entries, *, per_page=15, embed=None):
        converted = [ClipPageEntry(entry) for entry in entries]
        super().__init__(converted, per_page=per_page, embed=embed)


class ClipTable(db.Table, table_name='clips'):
    id = db.Column(db.Integer(auto_increment=True), unique=True, index=True)

    name = db.Column(db.String(), index=True)
    content = db.Column(db.String())

    owner_id = db.Column(db.Integer(big=True))
    location_id = db.Column(db.Integer(big=True), index=True)
    created_at = db.Column(db.Datetime(), default="now() at time zone 'utc'")
    uses = db.Column(db.Integer(), default=0)

    @classmethod
    def create_table(cls, *, overwrite=False):
        statement = super().create_table(overwrite=overwrite)

        # create the indexes
        sql = (
            'CREATE INDEX IF NOT EXISTS clips_name_trgm_idx ON clips USING GIN (name gin_trgm_ops);\n'
            'CREATE INDEX IF NOT EXISTS clips_name_lower_idx ON clips (LOWER(name));\n'
            'CREATE UNIQUE INDEX IF NOT EXISTS clips_uniq_idx ON clips (LOWER(name), location_id);'
        )

        return statement + '\n' + sql


class ClipName(commands.clean_content):

    async def convert(self, ctx, argument):
        cleaned = await super().convert(ctx, argument)
        lower = cleaned.lower().strip()

        if not lower:
            raise commands.BadArgument('A name must be specified')

        if len(lower) > 100:
            raise commands.BadArgument('The name must be at most 100 characters.')

        word, _, _ = lower.partition(' ')
        clip_command = ctx.bot.get_command('clip')
        if word in clip_command.all_commands:
            raise commands.BadArgument('Clip name starts with a command word.')
        return lower


class Clips(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_clip(self, name, *location_ids, connection=None):
        con = connection or self.bot.pool
        if len(location_ids) > 0:
            location_id = ' or '.join(['location_id = {0}'.format(loc_id) for loc_id in location_ids])
        else:
            location_id = 'location_id IS NULL'
        command = 'SELECT id, name, content, owner_id, created_at, uses FROM clips WHERE LOWER(name) = $1 AND ({0});'.format(location_id)
        entry = await con.fetchrow(command, name)
        if entry:
            return entry
        all_command = 'SELECT name FROM clips WHERE ({0}) AND name % $1 ORDER BY similarity(name, $1) DESC LIMIT 3;'
        all_command = all_command.format(location_id)
        entries = await con.fetch(all_command, name)
        if len(entries) == 0:
            raise commands.BadArgument('Clip not found.')
        names = '\n'.join([entry['name'] for entry in entries])
        raise commands.BadArgument('Clip not found. Did you mean:\n\n{0}'.format(names))

    @commands.group(name='clip', aliases=['note', 'c'], invoke_without_command=True)
    async def clip(self, ctx: Context, *, name: ClipName):
        """
        Fetches a clip and displays it. It looks for the clip in your personal repository and then in the guild repository.

        Examples:
            clip help
            clip pog
        """
        loc_ids = [ctx.author.id]
        if ctx.guild:
            loc_ids.append(ctx.guild.id)
        try:
            clip = await self.get_clip(name, *loc_ids, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await self.send_clip_content(ctx, clip)
        update = 'UPDATE clips SET uses = uses + 1 WHERE id = {0};'.format(clip['id'])
        await ctx.db.execute(update)

    @clip.command(name='stats', aliases=['about', 'info'])
    async def stats(self, ctx: Context, *, name: ClipName):
        """
        Returns stats about a clip. Checks your private repository and then the guild repository.
        """
        loc_ids = [ctx.author.id]
        if ctx.guild:
            loc_ids.append(ctx.guild.id)
        try:
            clip = await self.get_clip(name, *loc_ids, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))
        return await ctx.send(embed=await self.get_clip_stats(ctx, clip))

    @clip.command(name='list')
    async def people_list(self, ctx: Context, *, user: typing.Optional[discord.User] = None):
        title = ''
        if user and user.id == ctx.author.id:
            if ctx.guild:
                condition = 'owner_id = {0} AND location_id = {1}'.format(ctx.author.id, ctx.guild.id)
                title = 'Clips from {1} created by {0}'.format(str(ctx.author), str(ctx.guild.name))
            else:
                condition = 'owner_id = {0} AND location_id = {0}'.format(ctx.author.id)
                title = 'Personal Clips'
        elif user:
            if not ctx.guild:
                return await ctx.send(embed=ctx.create_embed('You have to be in a guild to select someone else!', error=True))
            condition = 'owner_id = {0} AND location_id = {1}'.format(user.id, ctx.guild.id)
            title = 'Clips from {1} created by {0}'.format(str(ctx.author), str(ctx.guild.name))
        elif ctx.guild:
            condition = 'location_id = {0}'.format(ctx.guild.id)
            title = 'Clips from {0}'.format(str(ctx.guild.name))
        else:
            condition = 'location_id = {0}'.format(ctx.author.id)
            title = 'Personal Clips'
        command = 'SELECT id, name FROM clips WHERE {0};'.format(condition)
        entries = await ctx.db.fetch(command)
        if len(entries) == 0:
            return await ctx.send(embed=ctx.create_embed('No clips found!'))
        embed = ctx.create_embed(title=title)
        if ctx.guild:
            embed.set_footer(text='To view personal clips DM me this command!')
        page = ClipPages(entries, embed=embed)
        try:
            await page.start(ctx)
        except:
            pass

    @clip.group(name='me', aliases=['self'], invoke_without_command=True)
    async def clip_me(self, ctx: Context, *, name: ClipName):
        """
        Fetches a clip from your personal repository and displays it.

        Examples:
            me boi
            me alive
        """
        try:
            clip = await self.get_clip(name, ctx.author.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await self.send_clip_content(ctx, clip)
        update = 'UPDATE clips SET uses = uses + 1 WHERE id = {0};'.format(clip['id'])
        await ctx.db.execute(update)

    @clip_me.command(name='new')
    async def create_me(self, ctx: Context, name: ClipName, *, content):
        """
        Create's a new clip in your private repository.

        Examples:
            new pog POGGERS LET'S GOOOOOO
            new alive Are you alive @Chronos?
        """
        find = None
        try:
            find = await self.get_clip(name, ctx.author.id, connection=ctx.db)
        except commands.BadArgument:
            pass
        if find:
            return await ctx.send(embed=ctx.create_embed('Clip `{0}` already exists for you!'.format(name), error=True))
        command = 'INSERT INTO clips(name, content, owner_id, location_id) VALUES ($1, $2, $3, $4);'
        await ctx.db.execute(command, name, content, ctx.author.id, ctx.author.id)
        await ctx.send(embed=ctx.create_embed('Clip created!'))

    @clip_me.command(name='edit')
    async def edit_me(self, ctx: Context, name: ClipName, *, content):
        """
        Edit's a clip in your personal repository.

        Examples:
            edit alive Do you be alive @Chronos?
            edit pog This is just 9/10 pog
        """
        try:
            clip = await self.get_clip(name, ctx.author.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        command = 'UPDATE clips SET content = $1 WHERE id = $2;'
        await ctx.db.execute(command, content, clip['id'])
        await ctx.send(embed=ctx.create_embed('Deleted clip {0}!'.format(clip['name'])))
        await ctx.send(embed=ctx.create_embed('Edited!'))

    @clip_me.command(name='delete')
    async def delete_me(self, ctx: Context, *, name: ClipName):
        """
        Delete's a clip from your personal repository.

        Examples:
            delete alive
            delete pog
        """
        try:
            clip = await self.get_clip(name, ctx.author.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        command = 'DELETE FROM clips WHERE id = $1;'
        await ctx.db.execute(command, clip['id'])
        await ctx.send(embed=ctx.create_embed('Deleted clip {0}!'.format(clip['name'])))

    @clip_me.command(name='stats')
    async def stats_me(self, ctx: Context, *, name: ClipName):
        """
        Retrieves information about a personal clip.

        Examples:
            stats alive
            stats pog
        """
        try:
            clip = await self.get_clip(name, ctx.author.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await ctx.send(embed=await self.get_clip_stats(ctx, clip))

    @clip.group(name='guild', aliases=['server'], invoke_without_command=True)
    @commands.guild_only()
    async def clip_guild(self, ctx: Context, *, name: ClipName):
        """
        Fetch's a clip from the server repository.

        Examples:
            guild shutup
            guild welcome
        """
        try:
            clip = await self.get_clip(name, ctx.guild.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await self.send_clip_content(ctx, clip)
        update = 'UPDATE clips SET uses = uses + 1 WHERE id = {0};'.format(clip['id'])
        await ctx.db.execute(update)

    @clip_guild.command(name='new')
    async def create_guild(self, ctx: Context, name: ClipName, *, content):
        find = None
        try:
            find = await self.get_clip(name, ctx.guild.id, connection=ctx.db)
        except commands.BadArgument:
            pass
        if find:
            return await ctx.send(embed=ctx.create_embed('Clip `{0}` already exists for the guild! Use `edit` if you own it!'.format(name), error=True))
        command = 'INSERT INTO clips(name, content, owner_id, location_id) VALUES ($1, $2, $3, $4);'
        await ctx.db.execute(command, name, content, ctx.author.id, ctx.guild.id)
        await ctx.send(embed=ctx.create_embed('Clip created!'))

    @clip_guild.command(name='edit')
    async def edit_guild(self, ctx: Context, name: ClipName, *, content):
        try:
            clip = await self.get_clip(name, ctx.guild.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        if clip['owner_id'] != ctx.author.id and not await checks.raw_is_admin(ctx):
            return await ctx.send(embed=ctx.create_embed("You can't edit that clip!", error=True))
        command = 'UPDATE clips SET content = $1 WHERE id = $2;'
        await ctx.db.execute(command, content, clip['id'])
        await ctx.send(embed=ctx.create_embed('Edited!'))

    @clip_guild.command(name='delete')
    async def delete_guild(self, ctx: Context, *, name: ClipName):
        try:
            clip = await self.get_clip(name, ctx.guild.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        if clip['owner_id'] != ctx.author.id and not await checks.raw_is_admin(ctx):
            return await ctx.send(embed=ctx.create_embed("You can't delete that clip!", error=True))
        command = 'DELETE FROM clips WHERE id = $1;'
        await ctx.db.execute(command, clip['id'])
        await ctx.send(embed=ctx.create_embed('Deleted clip {0}!'.format(clip['name'])))

    @clip_guild.command(name='stats')
    async def stats_guild(self, ctx: Context, *, name: ClipName):
        """
        Retrieves information about a guild clip.

        Examples:
            stats alive
            stats pog
        """
        try:
            clip = await self.get_clip(name, ctx.guild.id, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await ctx.send(embed=await self.get_clip_stats(ctx, clip))

    @clip.group(name='global', aliases=['public'], invoke_without_command=True)
    @checks.is_manager_or_perms()
    async def clip_global(self, ctx: Context, *, name: ClipName):
        """
        Fetch's a clip from the public repository.

        Examples:
            global clips
            global funnymeme
        """
        try:
            clip = await self.get_clip(name, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await self.send_clip_content(ctx, clip)
        update = 'UPDATE clips SET uses = uses + 1 WHERE id = {0};'.format(clip['id'])
        await ctx.db.execute(update)

    @clip_global.command(name='list')
    async def global_list(self, ctx: Context, *, user: typing.Optional[discord.User] = None):
        title = ''
        if user:
            condition = 'owner_id = {0} AND location_id IS NULL'.format(user.id)
            title = 'Global Clips created by {0}'.format(str(user))
        else:
            condition = 'location_id IS NULL'.format(ctx.author.id)
            title = 'Global Clips'
        command = 'SELECT id, name FROM clips WHERE {0};'.format(condition)
        entries = await ctx.db.fetch(command)
        if len(entries) == 0:
            return await ctx.send(embed=ctx.create_embed('No clips found!'))
        embed = ctx.create_embed(title=title)
        page = ClipPages(entries, embed=embed)
        try:
            await page.start(ctx)
        except:
            pass

    @clip_global.command(name='new')
    async def create_global(self, ctx: Context, name: ClipName, *, content):
        find = None
        try:
            find = await self.get_clip(name, connection=ctx.db)
        except commands.BadArgument:
            pass
        if find:
            return await ctx.send(embed=ctx.create_embed('Clip `{0}` already exists globally! Use `edit` if you own it!'.format(name), error=True))
        command = 'INSERT INTO clips(name, content, owner_id) VALUES ($1, $2, $3);'
        await ctx.db.execute(command, name, content, ctx.author.id)
        await ctx.send(embed=ctx.create_embed('Clip created!'))

    @clip_global.command(name='edit')
    async def edit_global(self, ctx: Context, name: ClipName, *, content):
        try:
            clip = await self.get_clip(name, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        if clip['owner_id'] != ctx.author.id and not await self.bot.is_owner(ctx.author):
            return await ctx.send(embed=ctx.create_embed("You can't edit that clip!", error=True))
        command = 'UPDATE clips SET content = $1 WHERE id = $2;'
        await ctx.db.execute(command, content, clip['id'])
        await ctx.send(embed=ctx.create_embed('Edited!'))

    @clip_global.command(name='delete')
    async def delete_global(self, ctx: Context, *, name: ClipName):
        try:
            clip = await self.get_clip(name, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        if clip['owner_id'] != ctx.author.id and not await self.bot.is_owner(ctx.author):
            return await ctx.send(embed=ctx.create_embed("You can't delete that clip!", error=True))
        command = 'DELETE FROM clips WHERE id = $1;'
        await ctx.db.execute(command, clip['id'])
        await ctx.send(embed=ctx.create_embed('Deleted clip {0}!'.format(clip['name'])))

    @clip_global.command(name='stats')
    async def stats_global(self, ctx: Context, *, name: ClipName):
        """
        Retrieves information about a global clip.

        Examples:
            stats alive
            stats pog
        """
        try:
            clip = await self.get_clip(name, connection=ctx.db)
        except commands.BadArgument as e:
            return await ctx.send(embed=ctx.create_embed(e))

        await ctx.send(embed=await self.get_clip_stats(ctx, clip))

    async def get_clip_stats(self, ctx, clip):

        # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/tags.py#L747
        rank_command = """SELECT (
                       SELECT COUNT(*)
                       FROM clips second
                       WHERE (second.uses, second.id) >= (first.uses, first.id)
                         AND second.location_id = first.location_id
                   ) AS rank
                   FROM clips first
                   WHERE first.id=$1
                """

        rank = await ctx.db.fetchrow(rank_command, clip['id'])

        embed = ctx.create_embed(title=clip['name'])
        embed.timestamp = clip['created_at']
        embed.add_field(name='Uses', value=str(clip['uses']))
        embed.add_field(name='Owner', value='<@{0}>'.format(clip['owner_id']))

        if rank:
            embed.add_field(name='Rank', value=str(rank['rank']))

        user = self.bot.get_user(clip['owner_id']) or (await self.bot.fetch_user(clip['owner_id']))
        if user:
            embed.set_thumbnail(url=user.avatar_url)
        return embed

    async def send_clip_content(self, ctx, clip):
        content = clip['content']
        if not content.startswith('EMBED'):
            return await ctx.send(content)
        try:
            embed_content = content[5:]
            embed = embed_utils.deserialize_string(embed_content)
        except:
            return await ctx.send(content)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Clips(bot))
