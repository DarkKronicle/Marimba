import asyncio
import traceback
import urllib

import aiohttp

from bot.marimba_bot import MarimbaBot, startup_extensions
from glocklib import database as db
import bot as bot_storage
from glocklib.config import Config
from pathlib import Path
import importlib
import logging

import scrython
from scrython.foundation import FoundationObject, ScryfallError


class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.http')

    def filter(self, record):
        if record.levelname == 'WARNING' and 'We are being rate limited.' in record.msg:
            return False
        return True


logging.getLogger().setLevel(logging.INFO)
logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.client').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.http').addFilter(RemoveNoise())


async def create_tables(connection):
    for table in db.Table.all_tables():
        try:
            await table.create(connection=connection)
        except Exception:     # noqa: E722
            logging.warning('Failed creating table {0}'.format(table.tablename))
            traceback.print_exc()


async def database(pool):

    cogs = startup_extensions

    for cog in cogs:
        try:
            importlib.import_module('{0}'.format(cog))
        except Exception:     # noqa: E722
            logging.warning('Could not load {0}'.format(cog))
            traceback.print_exc()
            return

    logging.info('Preparing to create {0} tables.'.format(len(db.Table.all_tables())))

    async with pool.acquire() as con:
        await create_tables(con)


def patch_scrython():
    """
    Scrython and discord.py don't really like to share asyncio loops. To fix this I change where it uses loops to
    just use async functions that can be called whenever. Not just in the __init__. There's probably a better fix
    but this one prevents the most hassle and works well with discord commands.
    Scrython is under the MIT license https://github.com/NandaScott/Scrython
    """
    def new_init(self, _url, override=False, **kwargs):
        self.params = {
            'format': kwargs.get('format', 'json'), 'face': kwargs.get('face', ''),
            'version': kwargs.get('version', ''), 'pretty': kwargs.get('pretty', '')
        }

        self.encodedParams = urllib.parse.urlencode(self.params)
        self._url = 'https://api.scryfall.com/{0}&{1}'.format(_url, self.encodedParams)

        if override:
            self._url = _url

    async def get_request(self, client, url, **kwargs):
        async with client.get(url, **kwargs) as response:
            return await response.json()

    async def request_data(self, *, loop=None):
        async with aiohttp.ClientSession(loop=loop) as client:
            self.scryfallJson = await self.get_request(client, self._url)
        if self.scryfallJson['object'] == 'error':
            raise ScryfallError(self.scryfallJson, self.scryfallJson['details'])

    FoundationObject.__init__ = new_init
    FoundationObject.request_data = request_data
    FoundationObject.get_request = get_request


def run_bot():
    bot_storage.config = Config(Path('./config.toml'))
    loop = asyncio.get_event_loop()
    log = logging.getLogger()
    kwargs = {
        'command_timeout': 60,
        'max_size': 20,
        'min_size': 20,
    }
    url = 'postgresql://{1}:{2}@localhost/{0}'.format(
        bot_storage.config['postgresql_name'],
        bot_storage.config['postgresql_user'],
        bot_storage.config['postgresql_password'],
    )
    try:
        pool = loop.run_until_complete(db.Table.create_pool(url, **kwargs))
        loop.run_until_complete(database(pool))
    except Exception as e:
        log.exception('Could not set up PostgreSQL. Exiting.')
        return
    patch_scrython()
    bot = MarimbaBot(pool)
    bot.run()


if __name__ == '__main__':
    run_bot()

