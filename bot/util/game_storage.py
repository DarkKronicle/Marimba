class Game:

    def __init__(self, game_obj, guild, channel, game_id):
        self.game_obj = game_obj
        self.guild_id = guild
        self.channel_id = channel
        self.game_id = game_id

    def get_players(self):
        players = []
        for instance in self.game_obj.instances:
            players.append(instance.user)
        return players

    def __contains__(self, item):
        if not isinstance(item, int):
            return False
        if item in [player.id for player in self.get_players()]:
            return True
        if item == self.channel_id:
            return True
        if item == self.guild_id:
            return True
        return False

    async def handle_join(self, ctx):
        await self.game_obj.handle_join(ctx)


class GameStorage:

    def __init__(self):
        self.num = 0
        self.games = {}

    def create_game(self, game, guild_id, channel_id):
        self.num += 1
        obj = Game(game, guild_id, channel_id, self.num)
        self.games[self.num] = obj
        return obj

    def get(self, game_id):
        return self.games.get(game_id)

    def get_from_game(self, game):
        for g in self.games.values():
            if g.game_obj == game:
                return g
        return None

    def end_game(self, game):
        game = self.get_from_game(game)
        if game:
            return self.end(game.game_id)
        return None

    def get_channel(self, channel_id):
        for game in self.games.values():
            if game.channel_id == channel_id:
                return game
        return None

    def end(self, game):
        self.games.pop(game)
        if not self.games:
            self.num = 0

    def __contains__(self, item):
        for game in self.games.values():
            if item in game:
                return True
        return False

    async def handle_join(self, ctx):
        for game in self.games.values():
            if ctx.channel.id in game:
                return await game.handle_join(ctx)
