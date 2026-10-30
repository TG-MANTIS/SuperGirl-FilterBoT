# --------------------------------------------------------------------------- #
#  Mantis Bots™ - Ultimate Anti-Flood, Security & Anti-Spam Plugin           #
# --------------------------------------------------------------------------- #

import re
import logging
import asyncio
from pyrogram import Client, filters, enums
from utils import get_settings
from info import ADMINS

logger = logging.getLogger(__name__)

# Comprehensive list of adult, spam, mms and paid service keywords to block instantly
SPAM_KEYWORDS = [
    "video call", "paid service", "whatsapp girls", "hot chat", 
    "sex chat", "adult group", "18+ group", "sex video", "nude",
    "dating chat", "online service", "private call", "viper chat",
    "hot video", "sex", "xxx", "bhabhi", "aunty chat", "deshi viral",
    "mms", "fuck", "horny", "romance chat", "night chat", "call girl",
    "paid service available", "service available", "xxx available",
    "mms available", "mms girl", "hot girls", "hot girl", "video paid service",
    "sex chat available", "video call available", "adult video"
]

# 1. Anti-Bot Security: Prevent normal users from adding unauthorized bots
@Client.on_message(filters.group & filters.new_chat_members)
async def antibot_handler(client, message):
    try:
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        
        # Check if anti-link/protection is enabled in settings
        if settings.get("antilink", False):
            for member in message.new_chat_members:
                if member.is_bot:
                    added_by = message.from_user
                    if not added_by:
                        return
                    
                    try:
                        user_member = await client.get_chat_member(chat_id, added_by.id)
                        is_admin = user_member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
                    except:
                        is_admin = False
                    
                    # If added by a normal user (not admin), kick/ban the bot instantly
                    if not is_admin and added_by.id not in ADMINS:
                        await client.ban_chat_member(chat_id, member.id)
                        warning_msg = await message.reply(
                            f"<b>🛡️ Security Alert:\n{added_by.mention}, normal members are not allowed to add bots here! Bot <code>{member.first_name}</code> has been removed.</b>"
                        )
                        await asyncio.sleep(5)
                        await warning_msg.delete()
                        await message.delete()
    except Exception as e:
        logger.error(f"Anti-Bot Security Error: {e}")


# 2. Anti-Link, Username & Anti-Spam Handler
@Client.on_message(filters.group & filters.incoming & ~filters.user(ADMINS))
async def antiflood_handler(client, message):
    if not message.text and not message.caption:
        return
    
    text = message.text or message.caption
    text_lower = text.lower()
    
    # Check for web, telegram links, or @usernames
    has_link = bool(re.search(r'(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+|instagram\.com/\S+|facebook\.com/\S+|chat\.whatsapp\.com/\S+|youtu\.be/\S+|youtube\.com/\S+)', text, re.IGNORECASE))
    has_username = bool(re.search(r'(^|\s)@[a-zA-Z0-9_]{5,32}(\s|$)', text))
    
    # Check for specific adult and paid service spam keywords
    has_spam_text = any(keyword in text_lower for keyword in SPAM_KEYWORDS)
    
    # If protection is enabled in settings
    if has_link or has_username or has_spam_text:
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        
        # Works only if Anti-Link/Protection is turned 'On' in settings menu
        if settings.get("antilink", False):
            try:
                member = await client.get_chat_member(chat_id, message.from_user.id)
                if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                    return
            except:
                pass
            
            try:
                # Delete spam/link message instantly
                await message.delete()
                
                # Send warning message
                warning_text = f"<b>⚠️ Hey {message.from_user.mention},\nLinks, usernames and adult/promotional messages are not allowed here!</b>"
                warning_msg = await message.reply(warning_text)
                
                await asyncio.sleep(4)
                await warning_msg.delete()
            except Exception as e:
                logger.error(f"Anti-Flood / Anti-Spam Error: {e}")
