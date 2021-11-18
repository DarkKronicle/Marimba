import discord
from discord.ext import menus

from bot.mtg.card_views import CardView


class SingleCardMenu(menus.Menu):
    """
    A menu that can go through different info of a card.
    """

    @classmethod
    def create_button_func(cls, view, *, doc):

        async def button_func(self, payload):
            await self.show_page(view)

        button_func.__doc__ = doc
        return button_func

    def __init__(self, card):
        super().__init__(check_embeds=True)
        self.card = card
        self.embed = discord.Embed(colour=discord.Colour.magenta())
        self.current_view = CardView.image
        buttons = [
            ("🗺️", CardView.image, "view the card image"),
            ("📘", CardView.text, "view a copy paste-able text format"),
            ("💸", CardView.prices, "view prices of the card"),
            ("🧾", CardView.legalities, "view the legalities of the card")
        ]

        for emoji, view, doc in buttons:
            self.add_button(menus.Button(emoji, self.create_button_func(view, doc=doc)))

    async def finalize(self, timed_out):
        try:
            await self.message.clear_reactions()
        except discord.HTTPException:
            pass

    @menus.button('*️⃣', position=menus.Last(0))
    async def show_help(self, payload):
        """shows this message"""
        embed = discord.Embed(title='Pages help', description='Hopefully this makes the buttons less confusing.',
                              colour=discord.Colour.purple())
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f'{emoji}: {button.action.__doc__}')

        embed.add_field(name='What do these reactions do?', value='\n'.join(messages), inline=False)
        await self.message.edit(content=None, embed=embed)

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.Last(2))
    async def stop_pages(self, payload):
        """stops the pagination session."""
        self.stop()

    async def format_page(self, view):
        self.embed = view.value(self.card)
        return self.embed

    async def _get_kwargs_from_page(self, view):
        value = await self.format_page(view)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {'content': value, 'embed': None}
        elif isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}

    async def show_page(self, view):
        self.current_view = view
        kwargs = await self._get_kwargs_from_page(view)
        await self.message.edit(**kwargs)

    async def send_initial_message(self, ctx, channel):
        kwargs = await self._get_kwargs_from_page(CardView.image)
        return await channel.send(**kwargs)
