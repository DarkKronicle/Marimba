import discord
from discord.ext import menus


class Refresh(menus.Menu):

    def __init__(self, func, *, embed=None, get_func=None, allowed_mentions=False):
        self.embed = embed
        check_embed = embed is None
        self.allowed_mentions = allowed_mentions
        self.get_func = get_func
        if not self.get_func:
            def get_message(ctx):
                if self.embed:
                    return ctx.create_embed(func(ctx))
                return func(ctx)
            self.get_func = get_message
        super().__init__(clear_reactions_after=True, check_embeds=check_embed, delete_message_after=False)

    async def send_initial_message(self, ctx, channel):
        data = self.get_func(ctx)
        if self.allowed_mentions:
            allowed_mentions = discord.AllowedMentions(users=False, everyone=False, roles=False)
        else:
            allowed_mentions = None
        if isinstance(data, discord.Embed):
            return await ctx.send(embed=data, allowed_mentions=allowed_mentions)
        return await ctx.send(data, allowed_mentions=allowed_mentions)

    @menus.button('🔄', position=menus.First(0))
    async def send_search(self, payload):
        data = self.get_func(self.ctx)
        if isinstance(data, discord.Embed):
            return await self.message.edit(embed=data)
        return await self.message.edit(content=data)


class SelectOption(menus.Menu):

    def __init__(self, key, starting_text, *, delete_after=True, embed=None):
        super().__init__(check_embeds=True, delete_message_after=delete_after)
        self.embed = embed
        if self.embed is None:
            self.embed = discord.Embed(title='Choose wisely...')
        self.starting_text = starting_text
        self.result = None
        self.key = key
        for emoji, data in self.key.items():
            self.add_button(menus.Button(emoji, SelectOption.create_button_func(data[1], data[0])))

    @classmethod
    def create_button_func(cls, name, num):

        async def button_func(self, payload):
            self.result = num
            self.stop()

        button_func.__doc__ = name
        return button_func

    async def send_initial_message(self, ctx, channel):
        embed = self.embed
        messages = []
        for (reaction, button) in self.buttons.items():
            messages.append('{0} - {1.action.__doc__}'.format(reaction, button))
        embed.description = '{0}\n\n{1}'.format(self.starting_text, '\n'.join(messages))
        return await channel.send(embed=embed)

    async def start(self, ctx, *, channel=None, wait=None):
        if wait is None:
            wait = True
        await super().start(ctx, channel=channel, wait=wait)
        return self.result

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        """Cancel"""
        self.result = None
        self.stop()


class ConfigMenu(menus.Menu):

    @classmethod
    def create_button_func(cls, name, desc):

        before, sep, after = desc.partition('\n')
        if after:
            question = after
        else:
            question = before

        async def button_func(self, payload):
            answer = await self.ctx.ask(question)
            if answer:
                self.answers[name] = answer

        button_func.__doc__ = before
        return button_func

    def __init__(self, *, options, embed=None):
        super().__init__(check_embeds=True, delete_message_after=True, timeout=300)
        self.embed = embed
        self.reactions = [item[0] for item in options]
        self.names = [item[1] for item in options]
        self.descriptions = [item[2] for item in options]
        self.answers = {}
        if len(set(self.names)) != len(self.names):
            raise menus.MenuError("There can't be duplicate names!")
        if len(set(self.reactions)) != len(self.reactions):
            raise menus.MenuError("There can't be duplicate reactions!")
        for i in range(len(self.names)):
            self.add_button(menus.Button(
                self.reactions[i],
                self.create_button_func(self.names[i], self.descriptions[i]))
            )

    @menus.button('✅', position=menus.First(0))
    async def send_search(self, payload):
        """Finishes the config"""
        self.stop()

    async def ask(self, ctx, *, default=None):
        await self.start(ctx, wait=True)
        if default is not None:
            for name in self.names:
                if name not in self.answers:
                    self.answers[name] = default
        return self.answers

    async def finalize(self, timed_out):
        try:
            await self.message.delete()
        except discord.HTTPException:
            pass

    async def send_initial_message(self, ctx, channel):
        if not self.embed:
            self.embed = ctx.create_embed()
        messages = []
        for (reaction, button) in self.buttons.items():
            messages.append('{0} - {1.action.__doc__}'.format(reaction, button))

        self.embed.add_field(name='What do these reactions do?', value='\n'.join(messages), inline=False)
        return await ctx.send(embed=self.embed)
