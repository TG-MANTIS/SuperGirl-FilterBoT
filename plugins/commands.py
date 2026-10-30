# --------------------------------------------------------------------------- #
#  Mantis Bots™ - Start, Settings & Core Commands Core File                    #
# --------------------------------------------------------------------------- #

import os
import logging
import random
import asyncio
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, SET_IMG, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION, PROTECT_CONTENT, FORCE_IMG
from utils import get_settings, get_size, is_subscribed, save_group_settings, temp
from database.connections_mdb import active_connection
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

    # Standard Private Start / No File Payload
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', callback_data='close_data'),
            InlineKeyboardButton('Aʙᴏᴜᴛ 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
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
                btn.append([InlineKeyboardButton("🔁 Tʀʏ Aɢᴀɪ𝗻 🔁", callback_data=f"{pre}#{file_id}")])
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
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', callback_data='close_data'),
            InlineKeyboardButton('Aʙᴏᴜᴛ 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
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
        chat = await client.get_chat(grp_id)
        title = chat.title

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{grp_id}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('Goodbye', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings.get("goodbye", False) else '❌ No', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('Force Sub', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}'),
                    InlineKeyboardButton('✅ Yes' if settings.get("forcesub", True) else '❌ No', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}')
                ],
                [
                    InlineKeyboardButton('🔒 Close Menu', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply_text(
                text=f"<b>⚙️ Private Settings Panel for {title}</b>",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
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
        
    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
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
        
    buttons = [
        [
            InlineKeyboardButton('💥 Gʀᴏᴜᴩ', url="https://t.me/+iEbhY7mM4oE1OTVl"),
            InlineKeyboardButton('Dᴇʟᴇᴛᴇ ⚠️', callback_data='close_data')
        ],
        [
            InlineKeyboardButton(text=f'⚙️ Fɪʟᴇ Sɪᴢᴇ 【 {size} 】⚙️', callback_data='gxneo')
        ]
    ]
    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        reply_markup=InlineKeyboardMarkup(buttons),
        protect_content=True if pre == 'filep' else False,
    )


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
                [InlineKeyboardButton(text="YES", callback_data="autofilter_delete")],
                [InlineKeyboardButton(text="CANCEL", callback_data="close_data")],
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
#  /settings Command Handler (Group & Private PM Support with Admin Check)    #
# --------------------------------------------------------------------------- #

@Client.on_message(filters.command('settings') & (filters.group | filters.private))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return
    
    chat_type = message.chat.type

    # 1. Group / Supergroup Settings Handler
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
            await asyncio.sleep(2)
            try:
                await sent_msg.delete()
                await message.delete()
            except:
                pass
            return

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌐 Open Source (Group)", callback_data=f"set_group_menu#{chat_id}"),
                InlineKeyboardButton("🔒 Private Source (PM)", url=f"https://t.me/{client.me.username}?start=settings_{chat_id}")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close_data")
            ]
        ])
        
        await message.reply_text(
            "<b>⚙️ Bot Settings Panel</b>\n\nChoose how you want to manage your settings:",
            reply_markup=buttons,
            quote=True,
            reply_to_message_id=message.id
        )

    # 2. Private Chat (PM) Settings Handler
    elif chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grp_id)
                title = chat.title
                member = await client.get_chat_member(grp_id, userid)
                is_admin = member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
            except:
                is_admin = False

            if not is_admin and userid not in ADMINS:
                warning_msg = await message.reply("⚠️ You do not have admin rights or permissions in the connected group!")
                await asyncio.sleep(3)
                try:
                    await warning_msg.delete()
                    await message.delete()
                except:
                    pass
                return

            settings = await get_settings(grp_id)
            if settings is not None:
                buttons = [
                    [
                        InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{grp_id}'),
                        InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No', callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('Goodbye', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings.get("goodbye", False) else '❌ No', callback_data=f'setgs#goodbye#{settings.get("goodbye", False)}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('Force Sub', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}'),
                        InlineKeyboardButton('✅ Yes' if settings.get("forcesub", True) else '❌ No', callback_data=f'setgs#forcesub#{settings.get("forcesub", True)}#{grp_id}')
                    ],
                    [
                        InlineKeyboardButton('🔒 Close Menu', callback_data='close_data')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                await message.reply_text(
                    text=f"<b>⚙️ Private Settings Panel for {title}</b>",
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            return
        else:
            warning_msg = await message.reply("⚠️ You are not connected to any group right now!\n\nPlease go to your group, connect first, and then use `/settings` in PM.")
            await asyncio.sleep(4)
            try:
                await warning_msg.delete()
                await message.delete()
            except:
                pass
            return


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
