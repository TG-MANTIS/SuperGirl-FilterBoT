# hello support tem Mantis Bots™
import asyncio
import re
import ast
import math
import random
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, LOG_CHANNEL, PICS, NOR_IMG, FILMS_LINK
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logger.ERROR)

PM_BUTTONS = {}
BUTTONS = {}
SPELL_CHECK = {}

# Spell check message for movies/series with spelling mistakes or available on search
NON_IMG = """<b><i>👋Hello {user_mention}</i></b>\n\n<b>❝ <i>Use the Button Below to Search on Google or IMDB And Copy the Correct Movie/Series Name And Paste.</i></b>\n\n<b>❝ <i>Don't Ask Movies/Series that Are Not Released in OTT Platform.</i></b>\n\n<b>❝ <i>Try to Ask in [ Name, Year ] This Fromat.</i></b>\n\n<i><b><u>⚠️ Don't Use: ➲ [+:;'*!-&.. etc</i></b></u>"""

# OTT Not Released / Theater only message for content not found in database
OTT_NOT_RELEASED_TXT = """<b><i>👋Hello {user_mention}</i></b>\n\n<b>❌ <i>Requested Title : <code>{mv_rqst}</code></i></b>\n\n<b>❝ <i>ഈ മൂവി/സീരീസ് നിലവിൽ തിയേറ്ററിൽ/ഉറവിടത്തിൽ മാത്രമാണ് ഉള്ളത്. ഫയലുകൾ ലഭ്യമാക്കാൻ സാധിക്കില്ല.</i></b>"""


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)

# Enabled auto filter in bot's private chat
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_text(bot, message):
    content = message.text
    user = message.from_user.first_name
    user_id = message.from_user.id
    if content.startswith("/") or content.startswith("#"): return  # ignore commands and hashtags
    if user_id in ADMINS: return # ignore admins
    
    await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<b>#PM_MSG\n\n★Name : {user}\n\n★ID : {user_id}\n\n★Message : {content}</b>"
    ) 
    
    await auto_filter(bot, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(f"മോനെ {query.from_user.first_name} ഇത് നിനക്കുലതല്ല 🤭\n\n{query.message.reply_to_message.from_user.first_name} ന്റെ റിക്വസ്റ്റ് ആണ് ഇത് 🙂\n\nRequest your own😘\n\n© Cinemaflix™", show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer("അല്ലയോ മഹാൻ താങ്കൾ ക്ലിക്ക് ചെയ്തത് പഴയ മെസ്സേജ് ആണ് വേണമെങ്കിൽ ഒന്നും കൂടെ റിക്വസ്റ്റ് ചെയ് 😉\n\nYou are using this for one of my old message, please send the request again.", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    
    chat_id = query.message.chat.id
    settings = await get_settings(chat_id)
    
    # --- [MODIFIED PART: DUAL BUTTON PATTERN FOR SERIES VS MOVIES IN NEXT PAGE] ---
    is_series = bool(re.search(r's\d+e\d+|season|episode|ep\d+|bbhin|bigg boss', search, re.IGNORECASE)) or any(re.search(r's\d+e\d+|season|episode|ep\d+', f.file_name, re.IGNORECASE) for f in files)
    
    if is_series:
        btn = []
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            # Extract Season & Episode if available
            se_match = re.search(r'(s\d+\s*e\d+|season\s*\d+|ep\s*\d+)', f_name, re.IGNORECASE)
            se_tag = f"[{se_match.group(0).upper()}] " if se_match else ""
            
            btn.append([
                InlineKeyboardButton(
                    text=f"[{f_size}] {se_tag}{f_name}", callback_data=f'files#{file.file_id}'
                )
            ])
    else:
        if settings['button']:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"🔗 {get_size(file.file_size)}  {file.file_name}", callback_data=f'files#{file.file_id}'
                    ),
                ]
                for file in files
            ]
        else:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"{file.file_name}", callback_data=f'files#{file.file_id}'
                    ),
                    InlineKeyboardButton(
                        text=f"🔗 {get_size(file.file_size)}",
                        callback_data=f'files_#{file.file_id}',
                    ),
                ]
               for file in files
            ] 
    # --- [MODIFIED PART END] ---

    btn.insert(0, 
        [
            InlineKeyboardButton(f'🎬 {search} 🎬', 'dupe')     
        ]
    )
    
    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⭅ Bᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f" {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("Dᴇʟᴇᴛᴇ 🗑️", callback_data="close_data")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton("❖ Pᴀɢᴇꜱ", callback_data="pages"),
             InlineKeyboardButton(f" {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("Nᴇxᴛ ⇛", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⭅ Bᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f" {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("Nᴇxᴛ ⇛", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("okDa", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer("You are clicking on an old button which is expired.", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('Checking for Movie in database...💡')
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit('movie not for my database..!')
            await asyncio.sleep(10)
            await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('♥️hello Bro Bro Please Share And Support')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('♥️hello Bro Please Share And Support')

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('♥️hello Bro Please Share And Support')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Buddy Don't Touch Others Property 😁!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer('♥️hello Bro Please Share And Support')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer('♥️hello Bro Please Share And Support')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('Done.!👍')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('♥️hello Bro Please Share And Support')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('♥️hello Bro Please Share And Support')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer( 'No such file exist😔. ')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        
        chat_id = query.message.chat.id
        settings = await get_settings(chat_id)
        
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm'] and query.message.chat.type != enums.ChatType.PRIVATE:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False,
                    reply_markup=InlineKeyboardMarkup(
                        [
                         [
                          InlineKeyboardButton('💥 Gʀᴏᴜᴩ', url="https://t.me/+iEbhY7mM4oE1OTVl"),
                          InlineKeyboardButton('Dᴇʟᴇᴛᴇ ⚠️', callback_data='close_data')
                          ],[
                          InlineKeyboardButton(text=f'⚙️ Fɪʟᴇ Sɪᴢᴇ 【 {size} 】⚙️', callback_data='gxneo')
                         ]
                        ]
                    )
                )
                await query.answer('Check PM, I have sent files in pm', show_alert=True)
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("I Like Your Smartness, But Don't Be Oversmart Okay", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.😬.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                  InlineKeyboardButton('💥 Gʀᴏᴜᴩ', url="https://t.me/+iEbhY7mM4oE1OTVl"),
                  InlineKeyboardButton('Dᴇʟᴇᴛᴇ ⚠️', callback_data='close_data')
                  ],[
                  InlineKeyboardButton(text=f'⚙️ Fɪʟᴇ Sɪᴢᴇ 【 {size} 】⚙️', callback_data='gxneo')
                 ]
                ]
            )
        )
    elif query.data == "pages":
        await query.answer()
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('✘ Cʟᴏꜱᴇ', callback_data='close_data'),
            InlineKeyboardButton('Aʙᴏᴜᴛ 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('🔙 Bᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('⏍ Sᴛᴀᴛᴜꜱ ⏍', callback_data='stats'),
            InlineKeyboardButton('Cʟᴏꜱᴇ ✘', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('🔙 Bᴀᴄᴋ', callback_data='about'),
            InlineKeyboardButton('Rᴇꜰʀᴇꜱʜ ✦', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        if query.from_user.id in ADMINS:
            await query.message.edit_text(text=script.STATUS_TXT.format(total, users, chats, monsize, free), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.answer("🔮 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧 🔮\n\nIt's only for my admins\n\n©𝐓𝐞𝐚𝐦 𝐂𝐢𝐧𝐞𝐦𝐚 𝐅𝐢𝐥𝐱™️", show_alert=True)
            await query.message.edit_text(text="നോക്കി നിന്നോ ഇപ്പോൾ കിട്ടും 😏", reply_markup=reply_markup)
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('🔙 Bᴀᴄᴋ', callback_data='about'),
            InlineKeyboardButton('Rᴇꜰʀᴇꜱʜ ✦', callback_data='rfrsh')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )    
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        if query.from_user.id in ADMINS:
            await query.message.edit_text(text=script.STATUS_TXT.format(total, users, chats, monsize, free), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.answer("🔮 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧 🔮\n\nIt's only for my admins\n\n©𝐓𝐞𝐚𝐦 𝐂𝐢𝐧𝐞𝐦𝐚 𝐅𝐢𝐥𝐱™️", show_alert=True)
            await query.message.edit_text(text="umfi അല്ലെ 😂 എത്ര നോക്കി നിന്നാലും നിനക്ക് കാണാൻ പറ്റില്ല 😎", reply_markup=reply_markup)
    elif query.data.startswith("set_group_menu#"):
        _, grp_id = query.data.split("#")
        grpid = int(grp_id)
        
        user_id = query.from_user.id
        try:
            member = await client.get_chat_member(grpid, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except:
            pass

        settings = await get_settings(grpid)
        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button', callback_data=f'setgs#button#{settings["button"]}#{str(grpid)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double', callback_data=f'setgs#button#{settings["button"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grpid)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grpid)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grpid)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('Spell Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grpid)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grpid)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grpid)}')
                ],
                [
                    InlineKeyboardButton('🔒 Close Menu', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(f"<b>⚙️ Group Settings for {query.message.chat.title}</b>", reply_markup=reply_markup)
        await query.answer()
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = int(grp_id)

        user_id = query.from_user.id
        try:
            member = await client.get_chat_member(grpid, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except:
            pass

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('🔒 Close Menu', callback_data='close_data')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer('Done.!👍')


async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_theater_only_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    pre = 'filep' if settings['file_secure'] else 'file'
    
    # --- [MODIFIED PART: DUAL BUTTON PATTERN FOR SERIES VS MOVIES] ---
    # Detect if search query or file names contain series pattern (e.g. S01E01, season, episode, bigg boss, etc.)
    is_series = bool(re.search(r's\d+e\d+|season|episode|ep\d+|bbhin|bigg boss', search, re.IGNORECASE)) or any(re.search(r's\d+e\d+|season|episode|ep\d+', f.file_name, re.IGNORECASE) for f in files)
    
    if is_series:
        btn = []
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            # Extract Season & Episode if available
            se_match = re.search(r'(s\d+\s*e\d+|season\s*\d+|ep\s*\d+)', f_name, re.IGNORECASE)
            se_tag = f"[{se_match.group(0).upper()}] " if se_match else ""
            
            btn.append([
                InlineKeyboardButton(
                    text=f"[{f_size}] {se_tag}{f_name}", callback_data=f'{pre}#{file.file_id}'
                )
            ])
    else:
        if settings["button"]:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"🔗 {get_size(file.file_size)} {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                    ),
                ]
                for file in files
            ]
        else:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"{file.file_name}",
                        callback_data=f'{pre}#{file.file_id}',
                    ),
                    InlineKeyboardButton(
                        text=f"🔗 {get_size(file.file_size)}",
                        callback_data=f'{pre}#{file.file_id}',
                    ),
                ]
                for file in files
            ]   
    # --- [MODIFIED PART END] ---

    btn.insert(0, 
        [
            InlineKeyboardButton(f'🎬 {search} 🎬', 'dupe')
        ]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton("❖ Pᴀɢᴇꜱ", callback_data="pages"),
             InlineKeyboardButton(text=f" 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="Nᴇxᴛ ⇛", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="Dᴇʟᴇᴛᴇ 🗑️", callback_data="close_data")]
        )

    imdb = None
    if settings.get("imdb", True):
        try:
            imdb = await get_poster(search, file=(files[0]).file_name)
        except Exception as e:
            logger.exception(e)
            imdb = None

    TEMPLATE = settings.get('template') or IMDB_TEMPLATE
    if imdb:
        try:
            cap = TEMPLATE.format(
                query=search,
                title=imdb.get('title', search),
                votes=imdb.get('votes', 'N/A'),
                aka=imdb.get("aka", 'N/A'),
                seasons=imdb.get("seasons", 'N/A'),
                box_office=imdb.get('box_office', 'N/A'),
                localized_title=imdb.get('localized_title', 'N/A'),
                kind=imdb.get('kind', 'movie'),
                imdb_id=imdb.get("imdb_id", 'N/A'),
                cast=imdb.get("cast", 'N/A'),
                runtime=imdb.get("runtime", 'N/A'),
                countries=imdb.get("countries", 'N/A'),
                certificates=imdb.get("certificates", 'N/A'),
                languages=imdb.get("languages", 'N/A'),
                director=imdb.get("director", 'N/A'),
                writer=imdb.get("writer", 'N/A'),
                producer=imdb.get("producer", 'N/A'),
                composer=imdb.get("composer", 'N/A'),
                cinematographer=imdb.get("cinematographer", 'N/A'),
                music_team=imdb.get("music_team", 'N/A'),
                distributors=imdb.get("distributors", 'N/A'),
                release_date=imdb.get('release_date', 'N/A'),
                year=imdb.get('year', 'N/A'),
                genres=imdb.get('genres', 'N/A'),
                poster=imdb.get('poster', ''),
                plot=imdb.get('plot', 'N/A'),
                rating=imdb.get('rating', 'N/A'),
                url=imdb.get('url', ''),
                **locals()
            )
        except Exception as err:
            logger.exception(err)
            cap = f"<b>🎬 Rᴇǫᴜᴇsᴛᴇᴅ Mᴏᴠɪᴇ Nᴀᴍᴇ :</b><code>{search}</code>\n\n<b><u>‼️ Note : Files Sended To PM Check In Private</u></b>"
    else:
        cap = f"<b>🎬 Rᴇǫᴜᴇsᴛᴇᴅ Mᴏᴠɪᴇ Nᴀᴍᴇ :</b><code>{search}</code>\n\n<b><u>‼️ Note : Files Sended To PM Check In Private</u></b>"

    if imdb and imdb.get('poster'):
        try:
            hehe = await message.reply_photo(photo=imdb.get('poster'), caption=cap, reply_markup=InlineKeyboardMarkup(btn))
            await asyncio.sleep(9999)
            await hehe.delete()
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            fmsg = await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
    if spoll:
        await msg.message.delete()

# Standard spell check function with Google & IMDb buttons
async def advantage_spell_chok(msg):
    mv_rqst = msg.text
    search = msg.text.replace(" ", "+")
    btn = [[
        InlineKeyboardButton(
            text="🔎 𝗚𝗼𝗼𝗴𝗹𝗲 🔍",
            url=f"https://google.com/search?q={search}"
        ),
        InlineKeyboardButton(
            text="🔮 𝗜𝗠𝗗𝗕 🔮",
            url=f"https://imdb.com/find?q={search}")

    ]]
    
    user_mention = msg.from_user.mention if msg.from_user else "My Friend"
    spl = await msg.reply_photo(
            photo="https://envs.sh/RCE.jpg", 
            caption=NON_IMG.format(user_mention=user_mention, mv_rqst=mv_rqst),
            reply_markup=InlineKeyboardMarkup(btn)
    )
    
    await asyncio.sleep(99)
    await spl.delete()
    await msg.delete()
    return

# OTT Not Released / Theater only check function
async def advantage_theater_only_chok(msg):
    mv_rqst = msg.text
    user_mention = msg.from_user.mention if msg.from_user else "My Friend"
    btn = [[
        InlineKeyboardButton(text="Dᴇʟᴇᴛᴇ 🗑️", callback_data="close_data")
    ]]
    spl = await msg.reply_photo(
            photo=NOR_IMG, 
            caption=OTT_NOT_RELEASED_TXT.format(user_mention=user_mention, mv_rqst=mv_rqst),
            reply_markup=InlineKeyboardMarkup(btn)
    )
    await asyncio.sleep(99)
    await spl.delete()
    await msg.delete()
    return

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(button) if 'button' in locals() else []
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
