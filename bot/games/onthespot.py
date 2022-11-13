import asyncio
import itertools
import random
from collections import Counter

import discord

from bot.util.base_game import BaseGame, BaseGameUser


def bool_to_emoji(result):
    if result is False:
        return '❌'
    return '✅'


class OnTheSpotUser(BaseGameUser):

    def __init__(self, parent, user, channel):
        super().__init__(parent, user)
        self.points = 0
        self.channel = channel

    def create_embed(self, description=None, *, colour=discord.Colour.purple()):
        embed = discord.Embed(description=description, colour=colour)
        embed.set_footer(text='On The Spot!')
        return embed

    def msg_check(self, dm=True, *, converter=None):
        def response(message):
            if dm:
                if message.channel.id != self.channel.id:
                    return False
            else:
                if message.channel.id != self.parent.ctx.channel.id:
                    return False
            if message.author.id != self.user.id:
                return False
            if converter:
                try:
                    converter(message)
                    return True
                except:
                    return False
            return True
        return response

    async def get_response(self, question):
        embed = self.create_embed()
        embed.description = 'Send your response to the question here!\n\n`{0}`'.format(question)
        await self.channel.send(embed=embed)
        message = await self.parent.ctx.bot.wait_for('message', timeout=180, check=self.msg_check())
        await self.channel.send(embed=self.create_embed(
            'Submitted! Return to <#{0}>.'.format(self.parent.ctx.channel.id),
            colour=discord.Colour.green(),
        ))
        await self.parent.remove_waiting(self)
        if message is None:
            return None
        return message.content

    async def get_vote(self, min_num, max_num):

        def check_vote(msg):
            num = int(msg.content)
            if num < min_num or num > max_num:
                raise ValueError()

        try:
            message = await self.parent.ctx.bot.wait_for('message', timeout=60, check=self.msg_check(dm=False, converter=check_vote))
        except:
            return None
        try:
            await message.delete()
        except:
            pass
        await self.parent.remove_waiting(self)
        return int(message.content)


class OnTheSpot(BaseGame):

    def __init__(self, ctx, owner, on_end, deck):
        super().__init__(ctx, owner)
        self.on_end = on_end
        self.started = False
        self.deck = deck
        self.pairs = []
        self.pair_index = 0
        self.waiting = {}
        self.waiting_message = None

    def create_embed(self, description=None, *, colour=discord.Colour.purple()):
        embed = discord.Embed(description=description, colour=colour)
        embed.set_footer(text='On The Spot!')
        return embed

    async def on_message(self, message):
        pass

    async def timeout(self):
        await self.end(None)
        await self.ctx.send('Timed out!')

    async def add_user(self, user):
        channel = await user.create_dm()
        self.instances.append(OnTheSpotUser(self, user, channel))

    async def remove_user(self, user):
        instance = None
        for i in self.instances:
            if i.user.id == user.id:
                instance = i
                break
        self.instances.remove(instance)

    async def loop(self):
        while self.started:
            await self.turn()

    async def remove_waiting(self, instance):
        if instance in self.waiting:
            self.waiting[instance] = True
            await self.update_waiting(self.create_embed())

    async def update_waiting(self, embed):
        lines = ['{1} {0}'.format(instance.user.display_name, bool_to_emoji(value)) for instance, value in self.waiting.items()]
        embed.description = '\n'.join(lines)

        if self.waiting_message is None:
            self.waiting_message = await self.ctx.send(embed=embed)
        else:
            await self.waiting_message.edit(embed=embed)

    async def turn(self):
        self.pair_index = (self.pair_index + 1) % len(self.pairs)
        users = self.pairs[self.pair_index]
        self.waiting = dict.fromkeys(users, False)
        self.waiting_message = None
        await self.update_waiting(self.create_embed())
        other = [user for user in self.instances if user not in users]
        card = self.deck.draw()[0]
        try:
            results = await asyncio.gather(*[user.get_response(card) for user in users])
        except discord.Forbidden:
            await self.ctx.send("Someone doesn't have DM's turned on!")
            await self.end(None)
            return
        results = list(zip(users, results))
        # Don't want anything to be ordered...
        random.shuffle(results)
        options_text = '\n'.join(['{0}. {1}'.format(i + 1, result[1]) for i, result in enumerate(results)])
        await self.ctx.send(embed=discord.Embed(
            author='Answers',
            description='```\n{0}```\n\n{1}'.format(card, options_text),
        ))
        await self.ctx.send('Vote for your favorite answer using the number! (i.e. `2`)')
        votes = Counter()
        max_vote = len(results)
        self.waiting_message = None
        self.waiting = dict.fromkeys(other, False)
        await self.update_waiting(self.create_embed())
        vote_results = await asyncio.gather(*[user.get_vote(1, max_vote) for user in other])
        for v in vote_results:
            if v is not None:
                votes[v] += 1
        most_common = votes.most_common(1)[0][0]
        win_index = most_common - 1
        if list(votes.values()).count(most_common) > 1:
            await self.ctx.send("There was a tie! No one get's any points!")
        else:
            winner = results[win_index][0]
            await self.ctx.send('{0} received a point with {1} votes!\n`{2}`'.format(winner.user.mention, votes.most_common(1)[0][1], results[win_index][1]))
            winner.points += 1
            if winner.points >= 5:
                await self.end(winner.user)
        await self.display_scoreboard()

    async def display_scoreboard(self):
        lines = []
        for instance in self.instances:
            lines.append('{0}: **{1}**'.format(instance.user.display_name, instance.points))
        embed = self.create_embed(description='\n'.join(lines), colour=discord.Colour.gold())
        embed.set_author(name='Leaderboard')
        embed.set_footer(text='On The Spot!')
        await self.ctx.send(embed=embed)

    async def end(self, winner):
        self.started = False
        if winner:
            await self.ctx.send('{0} won!'.format(winner.mention))
        else:
            await self.ctx.send('Stalement!')

    async def setup(self):
        await self.add_user(self.owner)
        max_ask = len(self.instances) - 1
        n = 2
        if max_ask > 2:
            answer = await self.ctx.ask('How many people do you want to answer at a time? (Lowest 2, highest {0})'.format(max_ask))
            try:
                answer = int(answer)
            except:
                pass
            else:
                n = answer
        self.pairs = list(itertools.combinations(self.instances, n))
        random.shuffle(self.pairs)
        self.pair_index = 0

    async def start(self):
        await self.ctx.send('Starting!')
        await self.setup()
        self.started = True
        await self.loop()

    async def handle_join(self, ctx):
        if self.started:
            return await ctx.send(embed=ctx.create_embed("You can't join mid game!", error=True))
        await self.add_user(ctx.author)
        await ctx.send(embed=ctx.create_embed('Added!'))

    async def cleanup(self):
        if self.on_end:
            self.on_end(self)
