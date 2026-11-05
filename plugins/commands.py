"""
Core Commands Module
Handles bot start workflows, group and private start payloads, force subscription verification,
database assignments, indexed channel lists, file deletion routines, and full settings management.
"""

import os
import logging
import random
import asyncio
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, SET_IMG, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, FORCE_IMG
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection
from plugins.pm_filter import auto_filter
import re
import json
import base64

logger = logging.getLogger(__name__)

BATCH_FILES = {}

# --------------------------------------------------------------------------- #
#  /start Command Handler (Group & Private Welcome & File Delivery)          #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command("start") & filters.incoming)
async def start_handler(client: Client, message):
    """
    Handles /start commands across group and private chats, manages user registration,
    force subscription checks, and file/batch delivery.
    """
    # Group Start Handler
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton('OTT Update Channel', url='https://t.me/cinema_flix_updates'),
            ],
            [
                InlineKeyboardButton('Movie Group', url='https://t.me/+iEbhY7mM4oE1OTVl'),
                InlineKeyboardButton('Main Group', url='https://t.me/Mallu_Movie_Hub_Group')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(
            script.START_TXT_GROUP.format(
                message.from_user.mention if message.from_user else message.chat.title, 
                temp.U_NAME, 
                temp.B_NAME
            ), 
            reply_markup=reply_markup
        )
        await asyncio.sleep(2) 
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            try:
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            except Exception as err:
                logger.error(f"Group Log Error: {err}")
            await db.add_chat(message.chat.id, message.chat.title)
        return 

    # Private User Registration Check
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        try:
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
        except Exception as err:
            logger.error(f"User Log Error: {err}")

    # Standard Private Start / No File Payload
    if len(message.command) != 2:
        grpid = await active_connection(str(message.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('✘ Close', callback_data='close_data'),
            InlineKeyboardButton('About 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if start_pic_enabled:
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                text=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        return

    # Force Subscription Check (/start with payload)
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("Make sure bot is admin in the ForceSub channel!")
            return
            
        btn = [[InlineKeyboardButton("📺 Join Channel 📺", url=invite_link.invite_link)]]

        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("🔁 Try Again 🔁", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
                
        await client.send_photo(
            chat_id=message.from_user.id,
            photo=FORCE_IMG,
            caption="<b>Please click the Join Channel button below and then click Try Again to get your file!</b>",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        grpid = await active_connection(str(message.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('✘ Close', callback_data='close_data'),
            InlineKeyboardButton('About 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if start_pic_enabled:
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await message.reply_text(
                text=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        return

    data = message.command[1]
    
    # Handle Private Settings Panel Redirect from Group
    if data.startswith("settings_"):
        grp_id = int(data.split("_")[1])
        user_id = message.from_user.id
        try:
            member = await client.get_chat_member(grp_id, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await message.reply("⚠️ You need to be an Admin of that group to change settings!")
        except Exception:
            return await message.reply("⚠️ Make sure I am present in that group and you are an admin!")

        settings = await get_settings(grp_id)
        title = "Group"
        try:
            chat = await client.get_chat(grp_id)
            if chat and chat.title:
                title = chat.title
        except Exception as err:
            logger.error(f"Error fetching chat title: {err}")

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{grp_id}#1'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Next ⇛', callback_data=f'set_group_menu#{grp_id}#2'),
                    InlineKeyboardButton('Close', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply_text(
                text=f"<b>⚙️ Private Settings Panel for {title} (Page 1/2)</b>",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        return

    # Handle Direct Channel Deep Link Search
    if data.startswith("search_"):
        search_query = data.split("search_", 1)[1].replace("_", " ")
        message.text = search_query
        await auto_filter(client, message)
        return

    # Handle Standard Deep Link Search
    if not "_" in data and not data.startswith("BATCH") and not data.startswith("DSTORE"):
        search_query = data.replace("_", " ")
        message.text = search_query
        await auto_filter(client, message)
        return

    # Handle Batch Files & Single Files Delivery
    try:
        pre, file_id = data.split('_', 1)
    except Exception:
        file_id = data
        pre = ""

    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("⏳ Please wait, processing batch files...")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file, 'r', encoding='utf-8') as file_data:
                    msgs = json.loads(file_data.read())
            except Exception:
                await sts.edit("❌ Failed to process batch file!")
                return await client.send_message(LOG_CHANNEL, "⚠️ UNABLE TO OPEN BATCH FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
            
        for msg in msgs:
            title = msg.get("title")
            size = get_size(int(msg.get("size", 0)))
            f_caption = msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(
                        file_name='' if title is None else title, 
                        file_size='' if size is None else size, 
                        file_caption='' if f_caption is None else f_caption
                    )
                except Exception as err:
                    logger.exception(err)
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                )
            except Exception as err:
                logger.warning(err, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return

    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("⏳ Please wait, processing stored batch...")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except Exception:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption = BATCH_FILE_CAPTION.format(
                            file_name=getattr(media, 'file_name', ''), 
                            file_size=getattr(media, 'file_size', ''), 
                            file_caption=getattr(msg, 'caption', '')
                        )
                    except Exception as err:
                        logger.exception(err)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as err:
                    logger.exception(err)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as err:
                    logger.exception(err)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
        
    files_ = await get_file_details(file_id, user_id=message.from_user.id)           
    if not files_:
        try:
            decoded_bytes = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
            pre, file_id = decoded_bytes.decode("ascii").split("_", 1)
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
            )
            filetype = msg.media
            file = getattr(msg, filetype.value)
            title = file.file_name
            size = get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(
                        file_name='' if title is None else title, 
                        file_size='' if size is None else size, 
                        file_caption=''
                    )
                except Exception:
                    pass
            await msg.edit_caption(f_caption)
            return
        except Exception:
            pass
        return await message.reply('❌ No such file exists!')
    
    files = files_[0]
    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(
                file_name='' if title is None else title, 
                file_size='' if size is None else size, 
                file_caption='' if f_caption is None else f_caption
            )
        except Exception as err:
            logger.exception(err)
    if f_caption is None:
        f_caption = f"{files.file_name}"
        
    file_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('🚸 Group', url="https://t.me/+iEbhY7mM4oE1OTVl"),
            InlineKeyboardButton('Delete 🗑️', callback_data='close_data')
        ],
        [
            InlineKeyboardButton(text=f'⚙️ File Size: {size}', callback_data='gxneo')
        ]
    ])

    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        reply_markup=file_keyboard,
        protect_content=True if pre == 'filep' else False,
    )


# --------------------------------------------------------------------------- #
#  /assign_db Command Handler (Admin Only - Auto Assign Paid DB with Dual Support) #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('assign_db') & filters.user(ADMINS))
async def assign_database_handler(client: Client, message):
    """
    Automatically assigns a free dedicated paid database slot supporting both User ID and Bot Username.
    """
    if len(message.command) < 2:
        return await message.reply(
            "<b>⚠️ Usage Error!</b>\n\n"
            "Please provide the User ID or Bot Username to assign a database.\n"
            "<b>Example:</b> <code>/assign_db MyMovieBot</code> (or User ID <code>123456789</code>)",
            parse_mode=enums.ParseMode.HTML
        )
    
    identifier = message.command[1].strip()
    
    # Check whether identifier is User ID (numeric) or Username (string)
    target_user_id = None
    target_username = None
    
    if identifier.isdigit():
        target_user_id = int(identifier)
    else:
        target_username = identifier.lstrip('@')

    from info import (
        PAID_DB_1, PAID_DB_2, PAID_DB_3, PAID_DB_4, PAID_DB_5,
        PAID_DB_6, PAID_DB_7, PAID_DB_8, PAID_DB_9, PAID_DB_10
    )
    
    paid_pool = [
        ("PAID_DB_1", PAID_DB_1), ("PAID_DB_2", PAID_DB_2), ("PAID_DB_3", PAID_DB_3),
        ("PAID_DB_4", PAID_DB_4), ("PAID_DB_5", PAID_DB_5), ("PAID_DB_6", PAID_DB_6),
        ("PAID_DB_7", PAID_DB_7), ("PAID_DB_8", PAID_DB_8), ("PAID_DB_9", PAID_DB_9),
        ("PAID_DB_10", PAID_DB_10)
    ]

    from database.ia_filterdb import db as main_db
    if not main_db:
        return await message.reply("❌ Main database connection error! Cannot proceed with assignment.")

    mapping_col = main_db["user_db_mappings"]
    
    # Check if this user_id or username already has an assigned slot
    query_filter = {"$or": []}
    if target_user_id:
        query_filter["$or"].append({"user_id": target_user_id})
    if target_username:
        query_filter["$or"].append({"username": target_username})
        
    existing = await mapping_col.find_one(query_filter) if query_filter["$or"] else None
    if existing:
        return await message.reply(
            f"<b>⚠️ Target <code>{identifier}</code> already has an assigned database slot!</b>\n"
            f"Slot Name: <code>{existing.get('slot_name')}</code>",
            parse_mode=enums.ParseMode.HTML
        )

    # Find already assigned URIs
    assigned_uris = set()
    async for doc in mapping_col.find({}):
        if "db_uri" in doc:
            assigned_uris.add(doc["db_uri"])

    # Find the next available free slot automatically
    free_slot_name = None
    free_slot_uri = None
    for slot_name, uri in paid_pool:
        if uri and uri not in assigned_uris:
            free_slot_name = slot_name
            free_slot_uri = uri
            break

    if not free_slot_uri:
        return await message.reply("❌ All Paid Database slots are currently full! Please add more slots in configuration.")

    try:
        await mapping_col.insert_one({
            "user_id": target_user_id,
            "username": target_username,
            "identifier": identifier,
            "slot_name": free_slot_name,
            "db_uri": free_slot_uri
        })
        
        await message.reply(
            f"<b>✅ Successfully Assigned Database!</b>\n\n"
            f"🎯 <b>Target:</b> <code>{identifier}</code>\n"
            f"📂 <b>Assigned Slot:</b> <code>{free_slot_name}</code>\n"
            f"🔗 <b>Status:</b> Dedicated database active!",
            parse_mode=enums.ParseMode.HTML
        )

        # Notify the clone bot if active
        try:
            from plugins.clone import ACTIVE_CLONES
            target_key = target_user_id if target_user_id else identifier
            if target_key in ACTIVE_CLONES:
                clone_bot_client = ACTIVE_CLONES[target_key]
                notification_text = (
                    f"<b>🎉 Congratulations! Your Dedicated Database is Now Active!</b>\n\n"
                    f"📂 <b>Assigned Slot:</b> <code>{free_slot_name}</code>\n"
                    f"🚀 Your bot has been successfully connected to your exclusive storage database.\n"
                    f"📊 You can now use the /status command here to check your database storage and file counts!"
                )
                
                close_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✘ Close", callback_data="close_data")]])
                await clone_bot_client.send_message(
                    chat_id=target_key,
                    text=notification_text,
                    reply_markup=close_keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
        except Exception as err:
            logger.error(f"Failed to send clone bot notification: {err}")

    except Exception as err:
        logger.error(f"Error saving DB mapping: {err}")
        await message.reply(f"❌ Failed to assign database: {err}")


# --------------------------------------------------------------------------- #
#  /channel Command Handler (Admin Only - View Indexed Channels)              #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info_handler(client: Client, message):
    """
    Lists all indexed channels or groups configured in the bot.
    """
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS configuration.")

    text = '📑 <b>Indexed Channels / Groups:</b>\n'
    for channel in channels:
        chat = await client.get_chat(channel)
        if chat.username:
            text += f'\n• @{chat.username}'
        else:
            text += f'\n• {chat.title or chat.first_name}'

    text += f'\n\n<b>Total Indexed Sources:</b> {len(channels)}'

    if len(text) < 4096:
        await message.reply(text, parse_mode=enums.ParseMode.HTML)
    else:
        file_path = 'Indexed_Channels.txt'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        await message.reply_document(file_path, caption="📁 <b>Indexed Channels List</b>", parse_mode=enums.ParseMode.HTML)
        os.remove(file_path)


# --------------------------------------------------------------------------- #
#  /logs Command Handler (Admin Only - Download Log File)                     #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file_handler(client: Client, message):
    """
    Sends the bot's system log file to administrators.
    """
    try:
        await message.reply_document('TelegramBot.log', caption="📋 <b>System Logs File</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        await message.reply(f"❌ <b>Error reading log file:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)


# --------------------------------------------------------------------------- #
#  /delete Command Handler (Admin Only - Delete File from DB)                 #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete_file_handler(client: Client, message):
    """
    Deletes a specific media file from the database in response to a replied message.
    """
    reply = message.reply_to_message
    if reply and reply.media:
        status_msg = await message.reply("⏳ Processing deletion...", quote=True)
    else:
        return await message.reply("⚠️ Please reply to a media file with /delete to remove it from the database!", quote=True)

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        return await status_msg.edit("❌ This is not a supported file format!")
    
    file_id, _ = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({'_id': file_id})
    if result.deleted_count:
        await status_msg.edit("✅ File successfully deleted from database!")
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
        })
        if result.deleted_count:
            await status_msg.edit("✅ File successfully deleted from database!")
        else:
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await status_msg.edit("✅ File successfully deleted from database!")
            else:
                await status_msg.edit("❌ File not found in database!")


# --------------------------------------------------------------------------- #
#  /deleteall Command Handler (Admin Only - Drop Database Index)              #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index_handler(client: Client, message):
    """
    Prompts confirmation to drop all indexed files from the database collection.
    """
    await message.reply_text(
        '⚠️ <b>WARNING:</b> This will delete all indexed files from the database.\nDo you want to continue?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text="✅ Yes, Delete All", callback_data="autofilter_delete")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="close_data")],
        ]),
        quote=True,
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm_handler(client: Client, query):
    """
    Executes dropping of the media collection after confirmation.
    """
    await Media.collection.drop()
    await query.answer('All indexed files have been successfully cleared!', show_alert=True)
    await query.message.edit('✅ Successfully deleted all indexed files from database.')


# --------------------------------------------------------------------------- #
#  /settings Command Handler (Group & Direct Private PM Full Menu)            #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('settings') & (filters.group | filters.private))
async def settings_handler(client: Client, message):
    """
    Displays group or private settings panel for administrators.
    """
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return
    
    chat_type = message.chat.type

    if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        chat_id = message.chat.id
        try:
            member = await client.get_chat_member(chat_id, userid)
            is_admin = member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
        except Exception:
            is_admin = False

        if not is_admin and userid not in ADMINS:
            warning_caption = (
                f"<b>👋 Hello {message.from_user.mention},\n\n"
                "❌ You do not have permission to use the <code>/settings</code> command!\n"
                "⚠️ Only group administrators are allowed to change these settings.</b>"
            )
            btn = [[InlineKeyboardButton("Delete 🗑️", callback_data="close_data")]]
            sent_msg = await message.reply_photo(
                photo=SET_IMG,
                caption=warning_caption,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            await asyncio.sleep(4)
            try:
                await sent_msg.delete()
                await message.delete()
            except Exception:
                pass
            return

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌐 Open Source (Group)", callback_data=f"set_group_menu#{chat_id}#1"),
                InlineKeyboardButton("🔒 Private Source (PM)", url=f"https://t.me/{client.me.username}?start=settings_{chat_id}")
            ],
            [
                InlineKeyboardButton("Close", callback_data="close_data")
            ]
        ])
        
        await message.reply_text(
            "<b>⚙️ Bot Settings Panel</b>\n\nChoose how you want to manage your settings:",
            reply_markup=buttons,
            quote=True,
            reply_to_message_id=message.id
        )
        return

    elif chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        title = "Group"
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grp_id)
                if chat and chat.title:
                    title = chat.title
                member = await client.get_chat_member(grp_id, userid)
                is_admin = member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
            except Exception:
                is_admin = False

            if not is_admin and userid not in ADMINS:
                return await message.reply("⚠️ You do not have permission to manage this group's settings!")

            settings = await get_settings(grp_id)
            if settings is not None:
                buttons = [
                    [
                        InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{grp_id}#1'),
                        InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{grp_id}#1')
                    ],
                    [
                        InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}#1'),
                        InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}#1')
                    ],
                    [
                        InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}#1'),
                        InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}#1')
                    ],
                    [
                        InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}#1'),
                        InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}#1')
                    ],
                    [
                        InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}#1'),
                        InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}#1')
                    ],
                    [
                        InlineKeyboardButton('Next ⇛', callback_data=f'set_group_menu#{grp_id}#2'),
                        InlineKeyboardButton('Close', callback_data='close_data')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                await message.reply_text(
                    text=f"<b>⚙️ Private Settings Panel for {title} (Page 1/2)</b>",
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            return
        else:
            await message.reply("⚠️ Please connect to any group first using /connect to manage group settings!")
            return


# --------------------------------------------------------------------------- #
#  Group & PM Settings Menu Pagination & Update Handlers                      #
# --------------------------------------------------------------------------- #

@Client.on_callback_query(filters.regex(r"^set_group_menu#"))
async def set_group_menu_callback_handler(client: Client, query):
    """
    Handles pagination for group settings panels (Page 1 and Page 2).
    """
    data_parts = query.data.split("#")
    grp_id_raw = data_parts[1]
    page = int(data_parts[2]) if len(data_parts) > 2 else 1
    
    user_id = query.from_user.id
    try:
        grp_id = int(grp_id_raw)
    except ValueError:
        grp_id = grp_id_raw

    if isinstance(grp_id, int):
        try:
            member = await client.get_chat_member(grp_id, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except Exception:
            pass

    settings = await get_settings(grp_id)
    title = "Group"
    if isinstance(grp_id, int):
        try:
            chat = await client.get_chat(grp_id)
            if chat and chat.title:
                title = chat.title
        except Exception as err:
            logger.error(f"Error fetching chat title: {err}")

    if settings is not None:
        if page == 1:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id}#1'),
                    InlineKeyboardButton('Single' if settings.get("button", True) else 'Double', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings.get("botpm", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("botpm", True) else '❌ No', callback_data=f'setgs#botpm#{settings.get("botpm", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("file_secure", False) else '❌ No', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("imdb", True) else '❌ No', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("spell_check", True) else '❌ No', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Next ⇛', callback_data=f'set_group_menu#{grp_id}#2'),
                    InlineKeyboardButton('Close', callback_data='close_data')
                ]
            ]
            text = f"<b>⚙️ Settings for {title} (Page 1/2)</b>"
        else:
            antilink = settings.get("antilink", False)
            start_pic = settings.get("start_pic", True)
            buttons = [
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("welcome", True) else '❌ No', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Goodbye', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("goodbye", False) else '❌ No', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Force Sub', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("forcesub", True) else '❌ No', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Anti-Link 🛡️', callback_data=f'setgs#antilink#{antilink}#{grp_id}#2'),
                    InlineKeyboardButton('✅ On' if antilink else '❌ Off', callback_data=f'setgs#antilink#{antilink}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Start Pic 🖼️', callback_data=f'setgs#start_pic#{start_pic}#{grp_id}#2'),
                    InlineKeyboardButton('✅ On' if start_pic else '❌ Off', callback_data=f'setgs#start_pic#{start_pic}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('⭅ Back', callback_data=f'set_group_menu#{grp_id}#1'),
                    InlineKeyboardButton('Close', callback_data='close_data')
                ]
            ]
            text = f"<b>⚙️ Settings for {title} (Page 2/2)</b>"

        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except MessageNotModified:
            pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^setgs"))
async def settings_update_callback_handler(client: Client, query):
    """
    Updates individual group settings when toggled via inline buttons.
    """
    data_parts = query.data.split("#")
    _, set_type, status, grp_id_raw, page_str = data_parts[0], data_parts[1], data_parts[2], data_parts[3], data_parts[4] if len(data_parts) > 4 else "1"
    page_num = int(page_str)

    user_id = query.from_user.id
    try:
        grp_id = int(grp_id_raw)
    except ValueError:
        grp_id = grp_id_raw

    if isinstance(grp_id, int):
        try:
            member = await client.get_chat_member(grp_id, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except Exception:
            pass

    new_status = False if status == "True" else True
    await save_group_settings(grp_id, set_type, new_status)

    settings = await get_settings(grp_id)
    title = "Group"
    if isinstance(grp_id, int):
        try:
            chat = await client.get_chat(grp_id)
            if chat and chat.title:
                title = chat.title
        except Exception as err:
            logger.error(f"Error fetching chat title: {err}")

    if settings is not None:
        if page_num == 1:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id}#1'),
                    InlineKeyboardButton('Single' if settings.get("button", True) else 'Double', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings.get("botpm", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("botpm", True) else '❌ No', callback_data=f'setgs#botpm#{settings.get("botpm", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("file_secure", False) else '❌ No', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("imdb", True) else '❌ No', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}#1'),
                    InlineKeyboardButton('✅ Yes' if settings.get("spell_check", True) else '❌ No', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id}#1')
                ],
                [
                    InlineKeyboardButton('Next ⇛', callback_data=f'set_group_menu#{grp_id}#2'),
                    InlineKeyboardButton('Close', callback_data='close_data')
                ]
            ]
            text = f"<b>⚙️ Settings for {title} (Page 1/2)</b>"
        else:
            antilink = settings.get("antilink", False)
            start_pic = settings.get("start_pic", True)
            buttons = [
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("welcome", True) else '❌ No', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Goodbye', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("goodbye", False) else '❌ No', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Force Sub', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}#2'),
                    InlineKeyboardButton('✅ Yes' if settings.get("forcesub", True) else '❌ No', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Anti-Link 🛡️', callback_data=f'setgs#antilink#{antilink}#{grp_id}#2'),
                    InlineKeyboardButton('✅ On' if antilink else '❌ Off', callback_data=f'setgs#antilink#{antilink}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('Start Pic 🖼️', callback_data=f'setgs#start_pic#{start_pic}#{grp_id}#2'),
                    InlineKeyboardButton('✅ On' if start_pic else '❌ Off', callback_data=f'setgs#start_pic#{start_pic}#{grp_id}#2')
                ],
                [
                    InlineKeyboardButton('⭅ Back', callback_data=f'set_group_menu#{grp_id}#1'),
                    InlineKeyboardButton('Close', callback_data='close_data')
                ]
            ]
            text = f"<b>⚙️ Settings for {title} (Page 2/2)</b>"

        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(text, reply_markup=reply_markup)
        except MessageNotModified:
            pass
    await query.answer('✅ Settings updated successfully!')


# --------------------------------------------------------------------------- #
#  /set_template Command Handler (Set Custom IMDB Template for Group)         #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('set_template'))
async def save_template_handler(client: Client, message):
    """
    Updates the custom IMDB template configuration for the current group.
    """
    sts = await message.reply("⏳ Checking template...")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply("⚠️ Anonymous admins cannot use this command directly. Use /connect in PM.")
        
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except Exception:
                return await message.reply_text("⚠️ Make sure I am present in your connected group!", quote=True)
        else:
            return await message.reply_text("⚠️ I am not connected to any groups!", quote=True)

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if st.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and str(userid) not in ADMINS:
        return await message.reply("⚠️ You need to be an administrator to change the template!")

    if len(message.command) < 2:
        return await sts.edit("❌ No template text provided!\n📌 <i>Usage:</i> <code>/set_template Your custom template text here</code>", parse_mode=enums.ParseMode.HTML)
        
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"✅ Successfully updated IMDB template for <b>{title}</b>:\n\n<code>{template}</code>", parse_mode=enums.ParseMode.HTML)
