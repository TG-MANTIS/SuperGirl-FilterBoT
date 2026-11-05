"""
Welcome & Goodbye Module
Handles automated greeting messages for new members and farewell messages
for members leaving group chats based on database configuration settings.
"""

import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated
from utils import get_settings

logger = logging.getLogger(__name__)


@Client.on_chat_member_updated()
async def welcome_goodbye_handler(client: Client, update: ChatMemberUpdated):
    """
    Manages chat member updates to send auto-deleting welcome and goodbye messages.
    """
    chat = update.chat
    
    # -------------------------------------------------------------------------
    #  1. Welcome Message Handler
    # -------------------------------------------------------------------------
    if update.new_chat_member:
        user = update.new_chat_member.user
        
        # Skip if the bot itself joined the group
        if user.id == (await client.get_me()).id:
            return
            
        try:
            settings = await get_settings(chat.id)
            if settings and settings.get("welcome", False):
                welcome_text = f"<b>👋 Hello {user.mention},\n\nWelcome to {chat.title}! 🎉</b>"
                sent_msg = await client.send_message(chat.id, welcome_text)
                
                # Auto delete welcome message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
        except Exception as err:
            logger.exception(err)

    # -------------------------------------------------------------------------
    #  2. Goodbye Message Handler
    # -------------------------------------------------------------------------
    elif update.old_chat_member:
        user = update.old_chat_member.user
        
        # Skip if the bot itself left or was removed
        if user.id == (await client.get_me()).id:
            return
            
        try:
            settings = await get_settings(chat.id)
            if settings and settings.get("goodbye", False):
                goodbye_text = f"<b>👋 {user.mention} has left the group! 🚶‍♂️</b>"
                sent_msg = await client.send_message(chat.id, goodbye_text)
                
                # Auto delete goodbye message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
        except Exception as err:
            logger.exception(err)
