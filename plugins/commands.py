# --------------------------------------------------------------------------- #
#  Mantis Bots™ - Start, Settings & Core Commands Core File                    #
# --------------------------------------------------------------------------- #

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
async def start(client, message):
    # Group Start Handler
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
            [
                InlineKeyboardButton('𝐎𝐭𝐭 𝐔𝐩𝐝𝐚𝐭𝐞 𝐂𝐡𝐚𝐧𝐧𝐞𝐥', url='https://t.me/cinema_flix_updates'),
            ],
            [
                InlineKeyboardButton('𝐌𝐨𝐯𝐢𝐞 𝐆𝐫𝐨𝐮𝐩', url='https://t.me/+iEbhY7mM4oE1OTVl'),
                InlineKeyboardButton('𝐌𝐚𝐢𝐧 𝐆𝐫𝐨𝐮𝐩', url='https://t.me/Mallu_Movie_Hub_Group')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT_GROUP.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) 
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            try:
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            except Exception as e:
                logger.error(f"Group Log Error: {e}")
            await db.add_chat(message.chat.id, message.chat.title)
        return 

    # Private User Registration Check
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        try:
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
        except Exception as e:
            logger.error(f"User Log Error: {e}")

    # Standard Private Start / No File Payload (Checking connected group settings for start_pic)
    if len(message.command) != 2:
        grpid = await active_connection(str(message.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', callback_data='close_data'),
            InlineKeyboardButton('Aʙᴏᴜᴛ 〄', callback_data='about')
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
            logger.error("Make sure Bot is admin in Forcesub channel")
            return
        btn = [
            [
                InlineKeyboardButton(
                    "📺 Jᴏɪɴ Cʜᴀɴ𝗻𝗲𝗹 📺", url=invite_link.invite_link
                )
            ]
        ]

        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("🔁 Tʀʏ Aɢ𝗮𝗶𝗻 🔁", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("🔁 Tʀʏ Aɢ𝗮𝗶𝗻 🔁", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        await client.send_photo(
            chat_id=message.from_user.id,
            photo=FORCE_IMG,
            caption="**Please click the Join Channel button below and then click Try Again to get your file!**",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        grpid = await active_connection(str(message.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', callback_data='close_data'),
            InlineKeyboardButton('Aʙᴏᴜᴛ 〄', callback_data='about')
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
        except:
            return await message.reply("⚠️ Make sure I am present in that group and you are an admin!")

        settings = await get_settings(grp_id)
        
        title = "Group"
        try:
            chat = await client.get_chat(grp_id)
            if chat and chat.title:
                title = chat.title
        except Exception as e:
            logger.error(f"Error fetching chat title: {e}")

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

    # Handle Deep Link Search
    if not "_" in data and not data.startswith("BATCH") and not data.startswith("DSTORE"):
        search_query = data.replace("_", " ")
        message.text = search_query
        await auto_filter(client, message)
        return

    # Handle Batch Files & Single Files Delivery
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""

    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("Please wait...")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs = json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size = get_size(int(msg.get("size", 0)))
            f_caption = msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption = BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption = f_caption
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
                logger.warning(f"Floodwait of {e.x} sec.")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                )
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return

    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("Please wait...")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media.value)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption = BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
        
    files_ = await get_file_details(file_id, user_id=message.from_user.id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(b_string) % 4))).decode("ascii")).split("_", 1) if False else ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
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
                    f_caption = CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            await msg.edit_caption(f_caption)
            return
        except:
            pass
        return await message.reply('No such file exists.')
    
    files = files_[0]
    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"
        
    file_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('🚸 Group', url="https://t.me/+iEbhY7mM4oE1OTVl"),
                InlineKeyboardButton('Delete 🗑️', callback_data='close_data')
            ],
            [
                InlineKeyboardButton(text=f'⚙️ File Size: {size}', callback_data='gxneo')
            ]
        ]
    )

    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        reply_markup=file_keyboard,
        protect_content=True if pre == 'filep' else False,
    )


# --------------------------------------------------------------------------- #
#  /status Command Handler (Dual Mode: Paid Users vs Free Users Stats)        #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('status') & filters.private)
async def bot_status_handler(client, message):
    user_id = message.from_user.id
    stats_msg = await message.reply("📊 Fetching statistics... Please wait.")
    
    try:
        from database.ia_filterdb import db as main_db, get_databases_stats, main_media_classes
        
        if not main_db:
            return await stats_msg.edit_text("❌ Database connection error!")
        
        mapping_col = main_db["user_db_mappings"]
        user_mapping = await mapping_col.find_one({"user_id": user_id})
        
        # Helper function to format size
        def readable_size(size_in_bytes):
            if size_in_bytes == 0:
                return "0 MB"
            units = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            while size_in_bytes >= 1024 and i < len(units) - 1:
                size_in_bytes /= 1024.0
                i += 1
            return f"{size_in_bytes:.2f} {units[i]}"

        # Close Button Markup
        close_keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✘ Cʟᴏꜱᴇ", callback_data="close_data")]]
        )

        # ------------------------------------------------------------- #
        # CASE 1: PAID USER (Dedicated DB Stats)                        #
        # ------------------------------------------------------------- #
        if user_mapping:
            slot_name = user_mapping.get("slot_name", "Paid Slot")
            stats_data = await get_databases_stats(user_id=user_id)
            
            total_files = 0
            total_size_bytes = 0
            
            for st in stats_data:
                total_files += st.get("count", 0)
                total_size_bytes += st.get("size", 0)
            
            storage_used = readable_size(total_size_bytes)
            
            status_text = (
                f"<b>💎 Dedicated Database Status (Paid Tier)</b>\n\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
                f"📂 <b>Assigned Slot:</b> <code>{slot_name}</code>\n"
                f"📁 <b>Total Files in Your DB:</b> <code>{total_files:,}</code>\n"
                f"💾 <b>Storage Used:</b> <code>{storage_used}</code>\n"
                f"🟢 <b>Status:</b> Active & Running smoothly!"
            )
            await stats_msg.edit_text(status_text, parse_mode=enums.ParseMode.HTML, reply_markup=close_keyboard)
            return

        # ------------------------------------------------------------- #
        # CASE 2: FREE / NORMAL USER (Main Global DB & Users Stats)     #
        # ------------------------------------------------------------- #
        else:
            total_global_files = 0
            for MediaModel in main_media_classes:
                try:
                    count = await MediaModel.count_documents({})
                    total_global_files += count
                except:
                    pass
            
            total_users = 0
            total_chats = 0
            try:
                total_users = await db.total_users_count()
                total_chats = await db.total_chat_count()
            except Exception as e:
                logger.error(f"Error fetching user/chat counts: {e}")
            
            try:
                db_stats = await main_db.command("dbStats")
                main_size_bytes = db_stats.get("dataSize", 0)
                main_storage = readable_size(main_size_bytes)
            except:
                main_storage = "N/A"

            status_text = (
                f"<b>📊 Bot Statistics (Free Tier)</b>\n\n"
                f"🌐 <b>Global Files Available:</b> <code>{total_global_files:,}</code>\n"
                f"👥 <b>Total Bot Users:</b> <code>{total_users:,}</code>\n"
                f"💬 <b>Total Connected Chats:</b> <code>{total_chats:,}</code>\n"
                f"💾 <b>Global DB Storage:</b> <code>{main_storage}</code>\n\n"
                f"💡 <i>Want your own dedicated database? Contact the admin to upgrade!</i>"
            )
            await stats_msg.edit_text(status_text, parse_mode=enums.ParseMode.HTML, reply_markup=close_keyboard)
            return

    except Exception as e:
        logger.error(f"Error in status command for user {user_id}: {e}")
        await stats_msg.edit_text("❌ Failed to retrieve statistics. Please try again later.")


# --------------------------------------------------------------------------- #
#  /assign_db Command Handler (Admin Only - Assign Paid DB Slot)             #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('assign_db') & filters.user(ADMINS))
async def assign_database(client, message):
    if len(message.command) < 2:
        return await message.reply(
            "<b>⚠️ Usage Error!</b>\n\n"
            "Please provide the User ID to assign a database.\n"
            "<b>Example:</b> <code>/assign_db 123456789</code>",
            parse_mode=enums.ParseMode.HTML
        )
    
    try:
        target_user_id = int(message.command[1])
    except ValueError:
        return await message.reply("⚠️ Invalid User ID! Please provide a valid numeric Telegram User ID.")

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

    existing = await mapping_col.find_one({"user_id": target_user_id})
    if existing:
        return await message.reply(
            f"<b>⚠️ User ID <code>{target_user_id}</code> already has an assigned database slot!</b>\n"
            f"Slot Name: <code>{existing.get('slot_name')}</code>",
            parse_mode=enums.ParseMode.HTML
        )

    assigned_uris = set()
    async for doc in mapping_col.find({}):
        if "db_uri" in doc:
            assigned_uris.add(doc["db_uri"])

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
            "slot_name": free_slot_name,
            "db_uri": free_slot_uri
        })
        await message.reply(
            f"<b>✅ Successfully Assigned Database!</b>\n\n"
            f"👤 <b>User ID:</b> <code>{target_user_id}</code>\n"
            f"📂 <b>Assigned Slot:</b> <code>{free_slot_name}</code>\n"
            f"🔗 <b>Status:</b> Dedicated database active!",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error saving DB mapping: {e}")
        await message.reply(f"❌ Failed to assign database: {e}")


# --------------------------------------------------------------------------- #
#  /channel Command Handler (Admin Only - View Indexed Channels)              #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


# --------------------------------------------------------------------------- #
#  /logs Command Handler (Admin Only - Download Log File)                     #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))


# --------------------------------------------------------------------------- #
#  /delete Command Handler (Admin Only - Delete File from DB)                 #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not a supported file format!')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({'_id': file_id})
    if result.deleted_count:
        await msg.edit('File successfully deleted from database!')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
        })
        if result.deleted_count:
            await msg.edit('File successfully deleted from database!')
        else:
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('File successfully deleted from database!')
            else:
                await msg.edit('File not found in database!')


# --------------------------------------------------------------------------- #
#  /deleteall Command Handler (Admin Only - Drop Database Index)              #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue?',
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(text="✅YES", callback_data="autofilter_delete")],
                [InlineKeyboardButton(text="CANCEL🗑️", callback_data="close_data")],
            ]
        ),
        quote=True,
    )

@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer('All indexed files have been successfully cleared!', show_alert=True)
    await message.message.edit('Successfully deleted all the indexed files.')


# --------------------------------------------------------------------------- #
#  /settings Command Handler (Group & Direct Private PM Full Menu)            #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('settings') & (filters.group | filters.private))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return
    
    chat_type = message.chat.type

    if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        chat_id = message.chat.id
        try:
            member = await client.get_chat_member(chat_id, userid)
            is_admin = member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
        except:
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
            except:
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
            except:
                is_admin = False

            if not is_admin and userid not in ADMINS:
                await message.reply("⚠️ ഈ കമാൻഡ് ഉപയോഗിക്കാൻ നിങ്ങൾക്ക് അനുവാദമില്ല!")
                return

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
async def set_group_menu_handler(client, query):
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
        except:
            pass

    settings = await get_settings(grp_id)
    
    title = "Group"
    if isinstance(grp_id, int):
        try:
            chat = await client.get_chat(grp_id)
            if chat and chat.title:
                title = chat.title
        except Exception as e:
            logger.error(f"Error fetching chat title: {e}")

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
async def settings_update_handler(client, query):
    data_parts = query.data.split("#")
    ident = data_parts[0]
    set_type = data_parts[1]
    status = data_parts[2]
    grp_id_raw = data_parts[3]
    page = int(data_parts[4]) if len(data_parts) > 4 else 1

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
        except:
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
        except Exception as e:
            logger.error(f"Error fetching chat title: {e}")

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

        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(text, reply_markup=reply_markup)
        except MessageNotModified:
            pass
    await query.answer('Done.!👍')


# --------------------------------------------------------------------------- #
#  /set_template Command Handler (Set Custom IMDB Template for Group)         #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template...")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are an anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input Provided!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to:\n\n{template}")
