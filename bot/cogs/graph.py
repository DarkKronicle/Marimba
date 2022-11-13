import base64
import io

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from bot.core.context import Context
import re


class Graph(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(1, 15, BucketType.user)
    @commands.group(name='graph', aliases=['g'], invoke_without_command=True)
    async def graph(self, ctx: Context, *, name: str):
        # https://mermaid-js.github.io/mermaid/#/Tutorials?id=python-integration-with-mermaid-js
        await self.send_mermaid(ctx, name)

    async def send_mermaid(self, ctx: Context, name):
        contents = re.findall(r'```.+```', name, re.DOTALL)
        await ctx.trigger_typing()
        if contents:
            g = contents[0][3:-3]
        else:
            g = name
        g = g.lstrip('\n').lstrip(' ').rstrip('\n').rstrip(' ')
        base64_bytes = base64.b64encode(g.encode("ascii"))
        base64_string = base64_bytes.decode("ascii")
        img_bytes = None
        async with aiohttp.ClientSession() as session:
            async with session.get('https://mermaid.ink/img/{0}'.format(base64_string)) as r:
                if r.status == 200:
                    img_bytes = io.BytesIO(await r.read())
        if img_bytes is None:
            return await ctx.send(embed=ctx.create_embed("Something went wrong!", error=True))
        f = discord.File(fp=img_bytes, filename="mermaid.png")
        await ctx.send(file=f)


async def setup(bot):
    await bot.add_cog(Graph(bot))
