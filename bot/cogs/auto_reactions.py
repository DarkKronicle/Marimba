from discord.ext import commands
from glocklib import database as db


class AutoReactionsTable(db.Table, table_name='auto_reactions'):
    id = db.Column(db.Integer(auto_increment=True), unique=True, index=True)
    guild_id = db.Column(db.Integer(big=True))


class AutoReactions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(AutoReactions(bot))
