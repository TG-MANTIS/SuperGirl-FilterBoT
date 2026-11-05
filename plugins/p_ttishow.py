"""
Group & User Management Module
Handles new chat additions, bot leaving logic, group disabling/enabling,
user banning/unbanning systems, and database statistics retrieval for administrators.
"""

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid
from info import ADMINS, LOG_CHANNEL, SUPPORT_CHAT, MELCOW_NEW_USERS
from database.users_chats_db import db
from database.ia_filterdb import Media
from utils import get_size, temp, get_settings
from Script import script
from pyrogram.errors import ChatAdminRequired

"""---------------------------------------------------------------------------------"""

@Client.on_message(filters.new_chat_members & filters.group)
async def save_group_handler(client: Client, message):
    """
    Manages bot addition to new groups, registers group details in database,
    and checks if the group is blacklisted/banned.
    """
    new_members_list = [member.id for member in message.new_chat_members]
    
    if temp.ME in new_members_list:
        if not await db.get_chat(message.chat.id):
            total_members = await client.get_chat_members_count(message.chat.id)
            inviter_mention = message.from_user.mention if message.from_user else "Anonymous" 
            
            try:
                await client.send_message(
                    LOG_CHANNEL, 
                    script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total_members, inviter_mention)
                )
            except Exception:
                pass
                
            await db.add_chat(message.chat.id, message.chat.title)
            
        if message.chat.id in temp.BANNED_CHATS:
            support_buttons = [[
                InlineKeyboardButton('💬 Support Here 💬', url=f'https://t.me/{SUPPORT_CHAT}')
            ]]
            reply_markup = InlineKeyboardMarkup(support_buttons)
            
            warning_msg = await message.reply(
                text='<b>❌ CHAT NOT ALLOWED!</b>\n\n'
                     '<i>My administrators have restricted me from working in this group. '
                     'If you want to know more, please contact our support team.</i>',
                reply_markup=reply_markup,
            )

            try:
                await warning_msg.pin()
            except Exception:
                pass
                
            await client.leave_chat(message.chat.id)
            return
            
        welcome_buttons = [[
            InlineKeyboardButton('ℹ️ Help', url=f"https://t.me/{temp.U_NAME}?start=help"),
            InlineKeyboardButton('Updates 📣', url='https://t.me/cinema_flix_updates')
        ]]
        reply_markup = InlineKeyboardMarkup(welcome_buttons)
        
        await message.reply_text(
            text=f"<b>Thank you for adding me to {message.chat.title} ❣️\n\n"
                 f"If you have any questions or doubts about using me, feel free to contact support.</b>",
            reply_markup=reply_markup
        )
    else:
        pass


@Client.on_message(filters.command('leave') & filters.user(ADMINS))
async def leave_chat_handler(client: Client, message):
    """
    Allows administrators to force the bot to leave a specific chat ID.
    """
    if len(message.command) == 1:
        return await message.reply("❌ <b>Please provide a chat ID!</b>\n📌 <i>Usage:</i> <code>/leave -100xxxxxxxxxx</code>", parse_mode=enums.ParseMode.HTML)
        
    chat_input = message.command[1]
    try:
        target_chat = int(chat_input)
    except ValueError:
        target_chat = chat_input
        
    try:
        support_buttons = [[
            InlineKeyboardButton('💬 Support Here 💬', url=f'https://t.me/{SUPPORT_CHAT}')
        ]]
        reply_markup = InlineKeyboardMarkup(support_buttons)
        
        await client.send_message(
            chat_id=target_chat,
            text='<b>Hello Friends,\nMy administrator has instructed me to leave this group. '
                 'If you wish to add me again, please contact our support group.</b>',
            reply_markup=reply_markup,
        )

        await client.leave_chat(target_chat)
        await message.reply(f"✅ <b>Successfully left the chat:</b> <code>{target_chat}</code>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        await message.reply(f"❌ <b>Error occurred:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('disable') & filters.user(ADMINS))
async def disable_chat_handler(client: Client, message):
    """
    Disables a specific group chat and adds it to the banned chats list.
    """
    if len(message.command) == 1:
        return await message.reply("❌ <b>Please provide a chat ID!</b>", parse_mode=enums.ParseMode.HTML)
        
    command_parts = message.text.split(None)
    if len(command_parts) > 2:
        reason = message.text.split(None, 2)[2]
        target_chat = message.text.split(None, 2)[1]
    else:
        target_chat = message.command[1]
        reason = "No reason provided"
        
    try:
        chat_id_int = int(target_chat)
    except ValueError:
        return await message.reply("❌ <b>Please provide a valid numeric chat ID!</b>", parse_mode=enums.ParseMode.HTML)
        
    chat_record = await db.get_chat(chat_id_int)
    if not chat_record:
        return await message.reply("❌ <b>Chat not found in database!</b>", parse_mode=enums.ParseMode.HTML)
        
    if chat_record.get('is_disabled'):
        return await message.reply(f"⚠️ <b>This chat is already disabled!</b>\nReason: <code>{chat_record.get('reason')}</code>", parse_mode=enums.ParseMode.HTML)
        
    await db.disable_chat(chat_id_int, reason)
    if chat_id_int not in temp.BANNED_CHATS:
        temp.BANNED_CHATS.append(chat_id_int)
        
    await message.reply("✅ <b>Chat successfully disabled!</b>", parse_mode=enums.ParseMode.HTML)
    
    try:
        support_buttons = [[
            InlineKeyboardButton('💬 Support Here 💬', url=f'https://t.me/{SUPPORT_CHAT}')
        ]]
        reply_markup = InlineKeyboardMarkup(support_buttons)
        
        await client.send_message(
            chat_id=chat_id_int, 
            text=f'<b>Hello Friends,\nMy administrator has instructed me to leave this group.\n'
                 f'Reason:</b> <code>{reason}</code>',
            reply_markup=reply_markup
        )
        await client.leave_chat(chat_id_int)
    except Exception as err:
        await message.reply(f"❌ <b>Error occurred while leaving chat:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('enable') & filters.user(ADMINS))
async def re_enable_chat_handler(client: Client, message):
    """
    Re-enables a previously disabled group chat.
    """
    if len(message.command) == 1:
        return await message.reply("❌ <b>Please provide a chat ID!</b>", parse_mode=enums.ParseMode.HTML)
        
    chat_input = message.command[1]
    try:
        chat_id_int = int(chat_input)
    except ValueError:
        return await message.reply("❌ <b>Please provide a valid numeric chat ID!</b>", parse_mode=enums.ParseMode.HTML)
        
    chat_status = await db.get_chat(chat_id_int)
    if not chat_status:
        return await message.reply("❌ <b>Chat not found in database!</b>", parse_mode=enums.ParseMode.HTML)
        
    if not chat_status.get('is_disabled'):
        return await message.reply("⚠️ <b>This chat is not currently disabled.</b>", parse_mode=enums.ParseMode.HTML)
        
    await db.re_enable_chat(chat_id_int)
    if chat_id_int in temp.BANNED_CHATS:
        temp.BANNED_CHATS.remove(chat_id_int)
        
    await message.reply("✅ <b>Chat successfully re-enabled!</b>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('stats') & filters.incoming & filters.user(ADMINS))
async def get_database_stats_handler(client: Client, message):
    """
    Retrieves overall database statistics including total users, chats, media files, and storage size.
    """
    status_msg = await message.reply("📊 <b>Fetching database statistics...</b>")
    
    total_users = await db.total_users_count()
    total_chats = await db.total_chat_count()
    total_files = await Media.count_documents()
    
    db_size_bytes = await db.get_db_size()
    free_space_bytes = 536870912 - db_size_bytes
    
    formatted_size = get_size(db_size_bytes)
    formatted_free = get_size(max(0, free_space_bytes))
    
    await status_msg.edit(script.STATUS_TXT.format(total_files, total_users, total_chats, formatted_size, formatted_free))


@Client.on_message(filters.command('ban') & filters.user(ADMINS))
async def ban_user_handler(client: Client, message):
    """
    Bans a specific user from using the bot.
    """
    if len(message.command) == 1:
        return await message.reply("❌ <b>Please provide a user ID or username!</b>", parse_mode=enums.ParseMode.HTML)
        
    command_parts = message.text.split(None)
    if len(command_parts) > 2:
        reason = message.text.split(None, 2)[2]
        user_identifier = message.text.split(None, 2)[1]
    else:
        user_identifier = message.command[1]
        reason = "No reason provided"
        
    try:
        if user_identifier.lstrip('-').isnumeric():
            user_identifier = int(user_identifier)
    except ValueError:
        pass
        
    try:
        target_user = await client.get_users(user_identifier)
    except PeerIdInvalid:
        return await message.reply("❌ <b>Invalid user! Make sure I have interacted with this user before.</b>", parse_mode=enums.ParseMode.HTML)
    except IndexError:
        return await message.reply("❌ <b>This appears to be a channel, please specify a valid user.</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        return await message.reply(f"❌ <b>Error occurred:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)
        
    ban_status = await db.get_ban_status(target_user.id)
    if ban_status.get('is_banned'):
        return await message.reply(f"⚠️ {target_user.mention} <b>is already banned!\nReason:</b> <code>{ban_status.get('ban_reason')}</code>", parse_mode=enums.ParseMode.HTML)
        
    await db.ban_user(target_user.id, reason)
    if target_user.id not in temp.BANNED_USERS:
        temp.BANNED_USERS.append(target_user.id)
        
    await message.reply(f"✅ Successfully banned {target_user.mention}!", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('unban') & filters.user(ADMINS))
async def unban_user_handler(client: Client, message):
    """
    Unbans a previously banned user.
    """
    if len(message.command) == 1:
        return await message.reply("❌ <b>Please provide a user ID or username!</b>", parse_mode=enums.ParseMode.HTML)
        
    command_parts = message.text.split(None)
    if len(command_parts) > 2:
        reason = message.text.split(None, 2)[2]
        user_identifier = message.text.split(None, 2)[1]
    else:
        user_identifier = message.command[1]
        reason = "No reason provided"
        
    try:
        if user_identifier.lstrip('-').isnumeric():
            user_identifier = int(user_identifier)
    except ValueError:
        pass
        
    try:
        target_user = await client.get_users(user_identifier)
    except PeerIdInvalid:
        return await message.reply("❌ <b>Invalid user! Make sure I have interacted with this user before.</b>", parse_mode=enums.ParseMode.HTML)
    except IndexError:
        return await message.reply("❌ <b>This appears to be a channel, please specify a valid user.</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        return await message.reply(f"❌ <b>Error occurred:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)
        
    ban_status = await db.get_ban_status(target_user.id)
    if not ban_status.get('is_banned'):
        return await message.reply(f"⚠️ {target_user.mention} <b>is not currently banned.</b>", parse_mode=enums.ParseMode.HTML)
        
    await db.remove_ban(target_user.id)
    if target_user.id in temp.BANNED_USERS:
        temp.BANNED_USERS.remove(target_user.id)
        
    await message.reply(f"✅ Successfully unbanned {target_user.mention}!", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users_handler(client: Client, message):
    """
    Retrieves and lists all users saved in the database. Sends as a document if too long.
    """
    status_msg = await message.reply("📋 <b>Fetching list of users from database...</b>")
    users_cursor = await db.get_all_users()
    
    output_text = "<b>Users Saved In Database:</b>\n\n"
    async for user_item in users_cursor:
        output_text += f"• <a href='tg://user?id={user_item['id']}'>{user_item['name']}</a>"
        if user_item.get('ban_status', {}).get('is_banned'):
            output_text += " <i>(Banned)</i>"
        output_text += "\n"
        
    try:
        await status_msg.edit_text(output_text, parse_mode=enums.ParseMode.HTML)
    except MessageTooLong:
        with open('users_list.txt', 'w+', encoding='utf-8') as outfile:
            outfile.write(output_text)
        await message.reply_document('users_list.txt', caption="📁 <b>Complete List of Users</b>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats_handler(client: Client, message):
    """
    Retrieves and lists all chats saved in the database. Sends as a document if too long.
    """
    status_msg = await message.reply("📋 <b>Fetching list of chats from database...</b>")
    chats_cursor = await db.get_all_chats()
    
    output_text = "<b>Chats Saved In Database:</b>\n\n"
    async for chat_item in chats_cursor:
        output_text += f"📌 <b>Title:</b> <code>{chat_item['title']}</code>\n🆔 <b>ID:</b> <code>{chat_item['id']}</code>"
        if chat_item.get('chat_status', {}).get('is_disabled'):
            output_text += " <i>(Disabled)</i>"
        output_text += "\n\n"
        
    try:
        await status_msg.edit_text(output_text, parse_mode=enums.ParseMode.HTML)
    except MessageTooLong:
        with open('chats_list.txt', 'w+', encoding='utf-8') as outfile:
            outfile.write(output_text)
        await message.reply_document('chats_list.txt', caption="📁 <b>Complete List of Chats</b>", parse_mode=enums.ParseMode.HTML)
