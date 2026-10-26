from pyrogram import Client, filters
import datetime
import time
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages
import asyncio
        
@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_users(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        text='<b>Uɴɢᴀ Mᴇssᴀɢᴇ Aʜ Uɴɢᴀ Bᴏᴛ Usᴇʀs Kᴜ Sᴇɴᴅ Pᴀɴɴɪᴛᴜ Iʀᴜᴋᴜ... ⏳</b>'
    )
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    
    async for user in users:
        pti, sh = await broadcast_messages(int(user['id']), b_msg)
        if pti:
            success += 1
        elif pti == False:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        done += 1
        await asyncio.sleep(2)
        if not done % 20:
            await sts.edit(f"<b>User Broadcast in progress:\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}</b>")    
    
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(f"<b>User Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}</b>")


@Client.on_message(filters.command("gbroadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_chats(bot, message):
    chats = await db.get_all_chats()
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        text='<b>Gʀᴏᴜᴘs-ലേക്കുള്ള Mᴇssᴀɢᴇ Bʀᴏഡ്കാസ്റ്റ് ചെയ്ത് തുടങ്ങുന്നു... ⏳</b>'
    )
    start_time = time.time()
    total_chats = await db.total_chat_count()
    done = 0
    success = 0
    failed = 0
    
    async for chat in chats:
        chat_id = chat['id']
        try:
            await b_msg.copy(chat_id=chat_id)
            success += 1
        except Exception:
            failed += 1
        done += 1
        await asyncio.sleep(2)
        if not done % 20:
            await sts.edit(f"<b>Group Broadcast in progress:\n\nTotal Chats: {total_chats}\nCompleted: {done} / {total_chats}\nSuccess: {success}\nFailed: {failed}</b>")
            
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(f"<b>Group Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Chats: {total_chats}\nCompleted: {done} / {total_chats}\nSuccess: {success}\nFailed: {failed}</b>")
