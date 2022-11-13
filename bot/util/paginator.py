import contextlib

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


class Pages(menus.MenuPages):

    def __init__(self, source, **kwargs):
        super().__init__(source, check_embeds=True, **kwargs)

    async def finalize(self, timed_out):
        with contextlib.suppress(discord.HTTPException):
            await self.message.clear_reactions()


class ImagePaginatorSource(menus.ListPageSource):

    def __init__(self, embed, images):
        super().__init__(images, per_page=1)
        self.embed: discord.Embed = embed
        self.images = images

    async def format_page(self, menu, page):
        image, fp = page
        maximum = self.get_max_pages()
        embed = self.embed.copy()
        if maximum > 1:
            embed.set_footer(
                text='Page {0}/{1} ({2} images)'.format(menu.current_page + 1, maximum, str(len(self.entries))),
            )
        embed.set_image(url='attachment://{0}'.format(image.filename))
        # Make sure we're good to read
        image.fp = io.BytesIO(fp.read())
        fp.seek(0)
        image.fp.seek(0)
        return {'embed': embed, 'file': image}

    async def finalize(self, time_out):
        for image, fp in self.images:
            image.fp.close()
            fp.close()


class ImagePaginator(Pages):

    def __init__(self, embed, images):
        self.images = images
        self.image_files = []
        self.continued = False
        for image_index, image in enumerate(self.images):
            self.image_files.append((discord.File(fp=image, filename='graph{0}.png'.format(image_index)), image))
        super().__init__(ImagePaginatorSource(embed, self.image_files))

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(self.current_page)
        kwargs = await self._get_kwargs_from_page(page)
        return await channel.send(**kwargs)

    async def show_page(self, page_number):
        self.current_page = page_number
        await self.message.delete()
        self.message = None
        self.continued = True
        await self.start(self.ctx)

    async def start(self, ctx, *, channel=None, wait=False):
        await super().start(ctx, channel=channel, wait=wait)

    async def finalize(self, timed_out):
        if not self.continued:
            await self.source.finalize(timed_out)
        await super().finalize(timed_out)
        self.continued = False


class Prompt(menus.Menu):

    def __init__(self, starting_text, *, delete_after=True):
        super().__init__(check_embeds=True, delete_message_after=delete_after)
        self.starting_text = starting_text
        self.result = None

    async def send_initial_message(self, ctx, channel):
        embed = ctx.create_embed(self.starting_text)
        return await ctx.send(embed=embed)

    async def start(self, ctx, *, channel=None, wait=None):
        if wait is None:
            wait = True
        return await super().start(ctx, channel=channel, wait=wait)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()


class SimplePageSource(menus.ListPageSource):

    def __init__(self, entries, *, per_page=15, numbers=True):
        super().__init__(entries, per_page=per_page)
        self.numbers = numbers

    async def format_page(self, menu, entries):
        pages = []
        if self.per_page > 1:
            for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
                if self.numbers:
                    pages.append(f"**{index + 1}.** {entry}")
                else:
                    pages.append(str(entry))
        else:
            if self.numbers:
                pages.append(f"**{menu.current_page + 1}.** {entries}")
            else:
                pages.append(str(entries))

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries.)"
            menu.embed.set_footer(text=footer)

        menu.embed.description = '\n'.join(pages)
        return menu.embed


class SimplePages(Pages):

    def __init__(self, entries, *, per_page=10, embed=discord.Embed(colour=discord.Colour.purple()), numbers=True):
        super().__init__(SimplePageSource(entries, per_page=per_page, numbers=numbers))
        self.embed = embed
        self.entries = entries
