"""
Core Broadcast Management Module
Handles asynchronous user and group broadcasts with real-time statistics,
block/deletion tracking, and exception safety.
"""

import os
import logging
import datetime
import time
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_users_handler(client: Client, message: Message):
    """
    Broadcasts a replied message to all registered users in the database
    with live progress tracking and failure/block auditing.
    """
    users_cursor = await db.get_all_users()
    broadcast_message = message.reply_to_message
    
    status_msg = await message.reply_text(
        text="<b>📢 User Broadcast Initiated...\n⏳ Processing queue, please wait.</b>",
        parse_mode=enums.ParseMode.HTML
    )
    
    start_time = time.time()
    total_users = await db.total_users_count()
    
    completed_count = 0
    blocked_count = 0
    deleted_count = 0
    failed_count = 0
    success_count = 0
    
    async for user_record in users_cursor:
        user_id = int(user_record.get("id"))
        status, reason = await broadcast_messages(user_id, broadcast_message)
        
        if status:
            success_count += 1
        elif status is False:
            if reason == "Blocked":
                blocked_count += 1
            elif reason == "Deleted":
                deleted_count += 1
            elif reason == "Error":
                failed_count += 1
                
        completed_count += 1
        await asyncio.sleep(2)  # Rate limiting to prevent flood waits
        
        # Update progress every 20 users
        if completed_count % 20 == 0:
            progress_text = (
                f"<b>📊 User Broadcast in Progress:</b>\n\n"
                f"👥 <b>Total Users:</b> <code>{total_users:,}</code>\n"
                f"⏳ <b>Completed:</b> <code>{completed_count} / {total_users}</code>\n"
                f"✅ <b>Success:</b> <code>{success_count}</code>\n"
                f"🚫 <b>Blocked:</b> <code>{blocked_count}</code>\n"
                f"🗑️ <b>Deleted Accounts:</b> <code>{deleted_count}</code>"
            )
            try:
                await status_msg.edit_text(progress_text, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass

    elapsed_time = datetime.timedelta(seconds=int(time.time() - start_time))
    
    completion_text = (
        f"<b>✅ User Broadcast Completed Successfully!</b>\n\n"
        f"⏱️ <b>Time Elapsed:</b> <code>{elapsed_time}</code>\n"
        f"👥 <b>Total Target Users:</b> <code>{total_users:,}</code>\n"
        f"📨 <b>Successfully Delivered:</b> <code>{success_count}</code>\n"
        f"🚫 <b>Blocked Users:</b> <code>{blocked_count}</code>\n"
        f"🗑️ <b>Deleted Accounts:</b> <code>{deleted_count}</code>\n"
        f"❌ <b>Failed Deliveries:</b> <code>{failed_count}</code>"
    )
    
    try:
        await status_msg.edit_text(completion_text, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to edit final user broadcast status: {e}")


@Client.on_message(filters.command("gbroadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_chats_handler(client: Client, message: Message):
    """
    Broadcasts a replied message to all connected groups and channels
    in the database with real-time progress logging.
    """
    chats_cursor = await db.get_all_chats()
    broadcast_message = message.reply_to_message
    
    status_msg = await message.reply_text(
        text="<b>📢 Group/Channel Broadcast Initiated...\n⏳ Dispatching payloads...</b>",
        parse_mode=enums.ParseMode.HTML
    )
    
    start_time = time.time()
    total_chats = await db.total_chat_count()
    
    completed_count = 0
    success_count = 0
    failed_count = 0
    
    async for chat_record in chats_cursor:
        chat_id = chat_record.get("id")
        try:
            await broadcast_message.copy(chat_id=chat_id)
            success_count += 1
        except Exception as err:
            logger.warning(f"Failed to broadcast to chat {chat_id}: {err}")
            failed_count += 1
            
        completed_count += 1
        await asyncio.sleep(2)  # Rate limiting
        
        # Update progress every 20 chats
        if completed_count % 20 == 0:
            progress_text = (
                f"<b>📊 Group Broadcast in Progress:</b>\n\n"
                f"💬 <b>Total Chats:</b> <code>{total_chats:,}</code>\n"
                f"⏳ <b>Completed:</b> <code>{completed_count} / {total_chats}</code>\n"
                f"✅ <b>Success:</b> <code>{success_count}</code>\n"
                f"❌ <b>Failed:</b> <code>{failed_count}</code>"
            )
            try:
                await status_msg.edit_text(progress_text, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
            
    elapsed_time = datetime.timedelta(seconds=int(time.time() - start_time))
    
    completion_text = (
        f"<b>✅ Group Broadcast Completed Successfully!</b>\n\n"
        f"⏱️ <b>Time Elapsed:</b> <code>{elapsed_time}</code>\n"
        f"💬 <b>Total Chats:</b> <code>{total_chats:,}</code>\n"
        f"📨 <b>Successfully Delivered:</b> <code>{success_count}</code>\n"
        f"❌ <b>Failed Deliveries:</b> <code>{failed_count}</code>"
    )
    
    try:
        await status_msg.edit_text(completion_text, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to edit final group broadcast status: {e}")
