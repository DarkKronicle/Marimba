import random

import asyncio
import discord

from bot.util import base_game


class AnagramUser(base_game.BaseGameUser):

    def __init__(self, parent, user):
        super().__init__(parent, user)
        self.points = 0


class AnagramGame(base_game.BaseGame):

    def __init__(self, word_storage, ctx, owner, end):
        super().__init__(ctx, owner)
        self.on_end = end
        self.anagram = list(word_storage.get_anagram_word(9))
        random.shuffle(self.anagram)
        self.anagram = ''.join(self.anagram)
        self.anagrams = list(word_storage.anagram(self.anagram, min_length=4))
        self.started = False

    async def on_message(self, message):
        if not self.started:
            return
        if message.content.lower() in self.anagrams:
            self.anagrams.remove(message.content.lower())
            instance = self.user_in(message.author)
            instance.points += 1
            await message.add_reaction('👍')
        else:
            await message.delete()

    async def timeout(self):
        await self.ctx.send('Timed out!')

    async def add_user(self, user):
        self.instances.append(AnagramUser(self, user))

    async def remove_user(self, user):
        pass

    async def end(self, winner):
        if winner:
            await self.ctx.send('{0} won!'.format(winner.mention))
        else:
            await self.ctx.send('Stalemate!')
        self.on_end(self)

    async def start(self):
        await self.add_user(self.owner)
        await self.ctx.send(embed=discord.Embed(
            title='Anagrams',
            description='Find the anagrams in `{0}` that are 4 characters or longer.\n\nYou have 90 seconds!'.format(self.anagram),
        ))
        self.started = True
        await asyncio.sleep(90)
        winner = await self.display_scoreboard()
        if len(self.anagrams) > 100:
            random.shuffle(self.anagrams)
            self.anagrams = self.anagrams[:100]
        await self.ctx.send(embed=discord.Embed(title='Missed words', description='```\n{0}```'.format(', '.join(self.anagrams))))
        await self.end(winner)

    async def display_scoreboard(self):
        lines = []
        max_points = 0
        max_user = None
        for instance in self.instances:
            if instance.points > max_points:
                max_user = instance.user
                max_points = instance.points
            lines.append('{0}: **{1}**'.format(instance.user.display_name, instance.points))
        embed = discord.Embed(description='\n'.join(lines), colour=discord.Colour.gold())
        embed.set_author(name='Leaderboard')
        embed.set_footer(text='Anagrams!')
        await self.ctx.send(embed=embed)
        return max_user

    async def handle_join(self, ctx):
        if not self.started:
            await self.add_user(ctx.author)
            return await ctx.send(embed=ctx.create_embed('Added!'))
        return await ctx.send(embed=ctx.create_embed("The game has already started!", error=True))
