"""
Main Bot Entry Point Module
Initializes the Pyrogram Client, sets up logging, loads banned entities,
ensures database indexes, starts the aiohttp web server, and manages bot lifecycle.
"""

import os
import logging
import logging.config
from typing import Union, Optional, AsyncGenerator

from aiohttp import web
from pyrogram import Client, __version__, types
from pyrogram.raw.all import layer

from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, LOG_STR
from utils import temp
from plugins import web_server

# Configure logging setup
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

PORT = int(os.environ.get("PORT", 8080))


class Bot(Client):
    """
    Custom Bot Client inheriting from Pyrogram Client to handle startup,
    shutdown, web server binding, and helper iterators.
    """
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        """
        Executes startup routines: loads banned users/chats, starts client,
        ensures media collection indexes, fetches bot info, and starts the web server.
        """
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        
        await super().start()
        await Media.ensure_indexes()
        
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username
        
        # Start aiohttp web server
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()
        
        logging.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started successfully on @{me.username}.")
        logging.info(LOG_STR)

    async def stop(self, *args):
        """
        Executes shutdown routines.
        """
        await super().stop()
        logging.info("Bot stopped successfully. Goodbye!")
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """
        Iterate through chat messages sequentially.
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1


# Instantiate and run the bot
app = Bot()
app.run()
