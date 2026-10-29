import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated
from utils import get_settings

logger = logging.getLogger(__name__)

@Client.on_chat_member_updated()
async def welcome_goodbye_handler(client: Client, update: ChatMemberUpdated):
    chat = update.chat
    
    # -------------------------------------------------------------------------
    #  1. Welcome Message Handler (Triggers when any member or bot joins)
    # -------------------------------------------------------------------------
    if update.new_chat_member:
        user = update.new_chat_member.user
        
        # Skip if the bot itself joined the group
        if user.id == (await client.get_me()).id:
            return
            
        try:
            settings = await get_settings(chat.id)
            # Check if welcome settings is enabled (True) in database
            if settings and settings.get("welcome", False):
                welcome_text = f"<b>👋 Hello {user.mention},\n\nWelcome to {chat.title}! 🎉</b>"
                sent_msg = await client.send_message(chat.id, welcome_text)
                
                # Auto delete welcome message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except:
                    pass
        except Exception as e:
            logger.exception(e)

    # -------------------------------------------------------------------------
    #  2. Goodbye Message Handler (Triggers when any member or bot leaves)
    # -------------------------------------------------------------------------
    elif update.old_chat_member:
        user = update.old_chat_member.user
        
        # Skip if the bot itself was removed or left
        if user.id == (await client.get_me()).id:
            return
            
        try:
            settings = await get_settings(chat.id)
            # Check if goodbye settings is enabled (True) in database
            if settings and settings.get("goodbye", False):
                goodbye_text = f"<b>👋 {user.mention} has left the group! 🚶‍♂️</b>"
                sent_msg = await client.send_message(chat.id, goodbye_text)
                
                # Auto delete goodbye message after 5 seconds
                await asyncio.sleep(5)
                try:
                    await sent_msg.delete()
                except:
                    pass
        except Exception as e:
            logger.exception(e)
