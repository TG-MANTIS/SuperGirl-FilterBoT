"""
PM & Group Auto-Filter and Media Delivery Module
Handles automated search queries, pagination, language/quality filters,
IMDB integration, spell-check notifications, and manual group filters.
"""

import asyncio
import re
import ast
import math
import random
from datetime import datetime
import pytz
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, LOG_CHANNEL, PICS, NOR_IMG, FILMS_LINK
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results, get_databases_stats
from database.filters_mdb import del_all, find_filter, get_filters
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PM_BUTTONS = {}
BUTTONS = {}

NON_IMG = """<b>👋 Hello {user_mention},</b>

<b>❌ <i>Could not find <code>{mv_rqst}</code> in our database!</i></b>

<b><u>📌 Possible Reasons:</u></b>

1️⃣ <b><u>Spelling Mistake:</u></b>
   • Please check the spelling and try again, or use the <b>Google</b> / <b>IMDb</b> buttons below to find the correct title.

2️⃣ <b><u>OTT Release:</u></b>
   • The movie/series might not be released on OTT platforms yet. (Theater prints are not available).

3️⃣ <b><u>Database:</u></b>
   • The file has not been added to our database yet.

💡 <b><u>Search Format:</u></b> <code>Movie Name Year</code> (Eg: <i>Lucifer 2019</i>)"""


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter_handler(client: Client, message):
    is_manual = await manual_filters(client, message)
    if is_manual is False:
        await auto_filter(client, message)


@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_text_handler(client: Client, message):
    content = message.text
    user_name = message.from_user.first_name
    user_id = message.from_user.id
    
    if content.startswith("/") or content.startswith("#"):
        return  
        
    try:
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=f"<b>#PM_MSG\n\n★ Name : {user_name}\n\n★ ID : {user_id}\n\n★ Message : {content}</b>"
        ) 
    except Exception:
        pass
    
    await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page_handler(client: Client, query: CallbackQuery):
    _, req_user_id, key, offset_str = query.data.split("_")
    
    if int(req_user_id) not in [query.from_user.id, 0]:
        return await query.answer("⚠️ This is not your search request!", show_alert=True)
        
    try:
        offset = int(offset_str)
    except ValueError:
        offset = 0
        
    search_query = BUTTONS.get(key)
    if not search_query:
        return await query.answer("⚠️ Session expired! Please submit your search request again.", show_alert=True)

    files, n_offset, total = await get_search_results(search_query, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except ValueError:
        n_offset = 0

    if not files:
        return
    
    chat_id = query.message.chat.id
    
    if query.message.chat.type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(query.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else await get_settings(chat_id)
    else:
        settings = await get_settings(chat_id)
    
    pre = 'filep' if settings.get('file_secure', False) else 'file'
    is_series = bool(re.search(r's\d+e\d+|season|episode|ep\d+|bbhin|bigg boss', search_query, enums.RegExFlag.IGNORECASE if hasattr(enums, 'RegExFlag') else re.IGNORECASE)) or any(re.search(r's\d+e\d+|season|episode|ep\d+', f.file_name, re.IGNORECASE) for f in files)
    
    if is_series:
        btn = []
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            se_match = re.search(r'(s\d+\s*e\d+|season\s*\d+|ep\s*\d+)', f_name, re.IGNORECASE)
            se_tag = f"[{se_match.group(0).upper()}] " if se_match else ""
            
            btn.append([
                InlineKeyboardButton(
                    text=f"⚡ {f_size} ◾ {se_tag}{f_name}", callback_data=f'{pre}#{file.file_id}'
                )
            ])
    else:
        if settings.get('button', True):
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"⚡ {get_size(file.file_size)} ◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                    ),
                ]
                for file in files
            ]
        else:
            btn = [
                [
                    InlineKeyboardButton(
                        text=f"⚡ {get_size(file.file_size)}",
                        callback_data=f'files_#{file.file_id}',
                    ),
                    InlineKeyboardButton(
                        text=f"◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                    ),
                ]
               for file in files
            ] 

    btn.insert(0, 
        [
            InlineKeyboardButton(f'☂️ {search_query} ', 'dupe')
        ]
    )
    btn.insert(1, 
        [
            InlineKeyboardButton('LΔΠGUΔGΣ', callback_data=f'lang_menu#{req_user_id}#{key}'),
            InlineKeyboardButton('QUΔLITY', callback_data=f'qual_menu#{req_user_id}#{key}')
        ]
    )
    
    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
        
    if n_offset == 0 and off_set is not None:
        btn.append(
            [InlineKeyboardButton("⏮️ ᗷΔCK", callback_data=f"next_{req_user_id}_{key}_{off_set}"),
             InlineKeyboardButton("DΣLΣTΣD 🗑️", callback_data="close_data")]
        )
    elif off_set is None and n_offset != 0 and n_offset is not None:
        btn.append(
            [InlineKeyboardButton("🗑️ DΣLΣTΣD", callback_data="close_data"),
             InlineKeyboardButton("ΠΣXT ⏭️", callback_data=f"next_{req_user_id}_{key}_{n_offset}")]
        )
    elif off_set is not None and n_offset != 0 and n_offset is not None:
        btn.append(
            [
                InlineKeyboardButton("⏮️ ᗷΔCK", callback_data=f"next_{req_user_id}_{key}_{off_set}"),
                InlineKeyboardButton("ΠΣXT ⏭️", callback_data=f"next_{req_user_id}_{key}_{n_offset}")
            ],
        )
    else:
        btn.append(
            [InlineKeyboardButton("DΣLΣTΣD 🗑️", callback_data="close_data")]
        )

    total_pages = math.ceil(int(total) / 10) if total else 1
    current_page = math.ceil(offset / 10) + 1

    if query.message.caption:
        old_html = query.message.caption.html
    elif query.message.text:
        old_html = query.message.text.html
    else:
        old_html = ""

    if re.search(r'📕 Pᴀɢᴇ :</b>\s*\d+\s*/\s*\d+', old_html):
        updated_caption = re.sub(
            r'(📕 Pᴀɢᴇ :</b>\s*)\d+\s*/\s*\d+',
            rf'\g<1>{current_page} / {total_pages}',
            old_html
        )
    else:
        updated_caption = f"{old_html}\n\n<b>📕 Pᴀɢᴇ :</b> {current_page} / {total_pages}"

    try:
        if query.message.photo:
            await query.message.edit_caption(
                caption=updated_caption[:1024],
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
        else:
            await query.message.edit_text(
                text=updated_caption,
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^(lang_menu|qual_menu|filter_apply|back_main_search)#"))
async def filter_menu_handler(client: Client, query: CallbackQuery):
    data = query.data.split("#")
    action, req_user_id, key = data[0], data[1], data[2]
    
    if int(req_user_id) not in [query.from_user.id, 0]:
        return await query.answer("⚠️ This is not for you!", show_alert=True)
        
    search_query = BUTTONS.get(key)
    if not search_query:
        return await query.answer("⚠️ Session expired! Please search again.", show_alert=True)

    if action == "lang_menu":
        buttons = [
            [
                InlineKeyboardButton("Malayalam", callback_data=f"filter_apply#{req_user_id}#{key}#Malayalam"),
                InlineKeyboardButton("Tamil", callback_data=f"filter_apply#{req_user_id}#{key}#Tamil")
            ],
            [
                InlineKeyboardButton("Telugu", callback_data=f"filter_apply#{req_user_id}#{key}#Telugu"),
                InlineKeyboardButton("Kannada", callback_data=f"filter_apply#{req_user_id}#{key}#Kannada")
            ],
            [
                InlineKeyboardButton("Hindi", callback_data=f"filter_apply#{req_user_id}#{key}#Hindi"),
                InlineKeyboardButton("English", callback_data=f"filter_apply#{req_user_id}#{key}#English")
            ],
            [
                InlineKeyboardButton("Japanese", callback_data=f"filter_apply#{req_user_id}#{key}#Japanese"),
                InlineKeyboardButton("Korean", callback_data=f"filter_apply#{req_user_id}#{key}#Korean")
            ],
            [
                InlineKeyboardButton("Chinese", callback_data=f"filter_apply#{req_user_id}#{key}#Chinese"),
                InlineKeyboardButton("Punjabi", callback_data=f"filter_apply#{req_user_id}#{key}#Punjabi")
            ],
            [
                InlineKeyboardButton("Marathi", callback_data=f"filter_apply#{req_user_id}#{key}#Marathi"),
                InlineKeyboardButton("Dual Audio", callback_data=f"filter_apply#{req_user_id}#{key}#Dual Audio")
            ],
            [
                InlineKeyboardButton("Multi Audio", callback_data=f"filter_apply#{req_user_id}#{key}#Multi Audio"),
                InlineKeyboardButton("Other", callback_data=f"filter_apply#{req_user_id}#{key}#Other")
            ],
            [
                InlineKeyboardButton("⏮️ ᗷΔCK", callback_data=f"back_main_search#{req_user_id}#{key}"),
                InlineKeyboardButton("DΣLΣTΣD 🗑️", callback_data="close_data")
            ]
        ]
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

    elif action == "qual_menu":
        buttons = [
            [
                InlineKeyboardButton("480p", callback_data=f"filter_apply#{req_user_id}#{key}#480p"),
                InlineKeyboardButton("720p", callback_data=f"filter_apply#{req_user_id}#{key}#720p")
            ],
            [
                InlineKeyboardButton("1080p", callback_data=f"filter_apply#{req_user_id}#{key}#1080p"),
                InlineKeyboardButton("2160p (4K)", callback_data=f"filter_apply#{req_user_id}#{key}#2160p")
            ],
            [
                InlineKeyboardButton("⏮️ ᗷΔCK", callback_data=f"back_main_search#{req_user_id}#{key}"),
                InlineKeyboardButton("DΣLΣTΣD 🗑️", callback_data="close_data")
            ]
        ]
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

    elif action == "back_main_search":
        files, _, total_results = await get_search_results(search_query, offset=0, filter=True)
        
        chat_id = query.message.chat.id
        if query.message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
            settings = await get_settings(int(grpid)) if grpid else await get_settings(chat_id)
        else:
            settings = await get_settings(chat_id)

        pre = 'filep' if settings.get('file_secure', False) else 'file'
        is_series = bool(re.search(r's\d+e\d+|season|episode|ep\d+|bbhin|bigg boss', search_query, re.IGNORECASE)) or any(re.search(r's\d+e\d+|season|episode|ep\d+', f.file_name, re.IGNORECASE) for f in files)
        
        if is_series:
            btn = []
            for file in files[:10]:
                f_name = file.file_name
                f_size = get_size(file.file_size)
                se_match = re.search(r'(s\d+\s*e\d+|season\s*\d+|ep\s*\d+)', f_name, re.IGNORECASE)
                se_tag = f"[{se_match.group(0).upper()}] " if se_match else ""
                btn.append([InlineKeyboardButton(text=f"⚡ {f_size} ◾ {se_tag}{f_name}", callback_data=f'{pre}#{file.file_id}')])
        else:
            if settings.get('button', True):
                btn = [[InlineKeyboardButton(text=f"⚡ {get_size(file.file_size)} ◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}')] for file in files[:10]]
            else:
                btn = [[
                    InlineKeyboardButton(text=f"⚡ {get_size(file.file_size)}", callback_data=f'{pre}#{file.file_id}'),
                    InlineKeyboardButton(text=f"◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}')
                ] for file in files[:10]]

        btn.insert(0, [
            InlineKeyboardButton(f'☂️ {search_query} ', 'dupe')
        ])
        btn.insert(1, [
            InlineKeyboardButton('LΔΠGUΔGΣ', callback_data=f'lang_menu#{req_user_id}#{key}'),
            InlineKeyboardButton('QUΔLITY', callback_data=f'qual_menu#{req_user_id}#{key}')
        ])
        
        if total_results > 10:
            btn.append([
                InlineKeyboardButton(text="ΠΣXT ⏭️", callback_data=f"next_{req_user_id}_{key}_10"),
                InlineKeyboardButton(text="DΣLΣTΣD 🗑️", callback_data="close_data")
            ])
        else:
            btn.append([
                InlineKeyboardButton(text="DΣLΣTΣD 🗑️", callback_data="close_data")
            ])
            
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()

    elif action == "filter_apply":
        target = data[3]
        all_files, _, _ = await get_search_results(search_query, offset=0, filter=False)
        filtered_files = []

        lang_patterns = {
            "Malayalam": [r"malayalam", r"\bmal\b", r"\bmlm\b"],
            "Tamil": [r"tamil", r"\btam\b"],
            "Telugu": [r"telugu", r"\btel\b"],
            "Kannada": [r"kannada", r"\bkan\b"],
            "Hindi": [r"hindi", r"\bhin\b"],
            "English": [r"english", r"\beng\b", r"\bengsub\b"],
            "Japanese": [r"japanese", r"\bjapan\b", r"\bjpn\b"],
            "Korean": [r"korean", r"\bkor\b"],
            "Chinese": [r"chinese", r"\bchi\b", r"\bmandarin\b"],
            "Punjabi": [r"punjabi", r"\bpun\b"],
            "Marathi": [r"marathi", r"\bmar\b"]
        }

        for f in all_files:
            fname = f.file_name.lower()
            
            if target == "Dual Audio":
                matched_langs = sum(1 for _, patterns in lang_patterns.items() if any(re.search(p, fname) for p in patterns))
                if "dual" in fname or "dual audio" in fname or matched_langs >= 2 or "+" in fname:
                    filtered_files.append(f)
            
            elif target == "Multi Audio":
                matched_langs = sum(1 for _, patterns in lang_patterns.items() if any(re.search(p, fname) for p in patterns))
                if "multi" in fname or "multi audio" in fname or matched_langs >= 3:
                    filtered_files.append(f)
            
            elif target in lang_patterns:
                patterns = lang_patterns[target]
                if any(re.search(p, fname) for p in patterns):
                    filtered_files.append(f)
            
            else:
                if target.lower() in fname:
                    filtered_files.append(f)
        
        if not filtered_files:
            return await query.answer("❌ No files found matching this filter!", show_alert=True)
            
        chat_id = query.message.chat.id
        if query.message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
            settings = await get_settings(int(grpid)) if grpid else await get_settings(chat_id)
        else:
            settings = await get_settings(chat_id)

        pre = 'filep' if settings.get('file_secure', False) else 'file'
        btn = []
        for file in filtered_files[:10]:
            f_size = get_size(file.file_size)
            btn.append([InlineKeyboardButton(text=f"⚡ {f_size} ◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}')])
            
        btn.insert(0, [
            InlineKeyboardButton(f"🔮 ᖴILTΣRΣD: {target}", callback_data="pages")
        ])
        btn.append([
            InlineKeyboardButton("⏮️ ᗷΔCK", callback_data=f"back_main_search#{req_user_id}#{key}"),
            InlineKeyboardButton("DΣLΣTΣD 🗑️", callback_data="close_data")
        ])
        
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer(f"Filtered by {target}!", show_alert=False)


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
                except Exception:
                    return await query.message.edit_text("⚠️ Make sure I'm present in your connected group!", quote=True)
            else:
                return await query.message.edit_text(
                    "⚠️ I'm not connected to any groups!\nCheck /connections or connect to any group.",
                    quote=True
                )
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title
        else:
            return

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("⚠️ You need to be the Group Owner or an Admin to do that!", show_alert=True)
            
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            try:
                await query.message.reply_to_message.delete()
            except Exception:
                pass
            await query.message.delete()
        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except Exception:
                    pass
            else:
                await query.answer("⚠️ You are not authorized to do this!", show_alert=True)
                
    elif "groupcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title

        stat = "CONNECT" if act == "" else "DISCONNECT"
        cb = "connectcb" if act == "" else "disconnect"

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
        
    elif "connectcb" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))
        if mkact:
            await query.message.edit_text(f"✅ Connected to **{title}**", parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await query.message.edit_text('❌ Some error occurred while connecting!', parse_mode=enums.ParseMode.MARKDOWN)
            
    elif "disconnect" in query.data:
        await query.answer()
        group_id = query.data.split(":")[1]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))
        if mkinact:
            await query.message.edit_text(f"✅ Disconnected from **{title}**", parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await query.message.edit_text('❌ Some error occurred!', parse_mode=enums.ParseMode.MARKDOWN)
            
    elif "deletecb" in query.data:
        await query.answer()
        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))
        if delcon:
            await query.message.edit_text("✅ Successfully deleted connection.")
        else:
            await query.message.edit_text('❌ Some error occurred!', parse_mode=enums.ParseMode.MARKDOWN)
            
    elif "backcb" in query.data:
        await query.answer()
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        
        if not groupids:
            return await query.message.edit_text("⚠️ There are no active connections! Connect to some groups first.")
            
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append([InlineKeyboardButton(text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}")])
            except Exception:
                pass
                
        if buttons:
            await query.message.edit_text("<b>Your connected group details:</b>\n\n", reply_markup=InlineKeyboardMarkup(buttons))
            
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        _, _, alerts, _ = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)].replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
            
    elif query.data.startswith("set_group_menu#"):
        data_parts = query.data.split("#")
        grp_id = int(data_parts[1])
        page = int(data_parts[2]) if len(data_parts) > 2 else 1
        
        user_id = query.from_user.id
        try:
            member = await client.get_chat_member(grp_id, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except Exception:
            pass

        settings = await get_settings(grp_id)
        chat = await client.get_chat(grp_id)
        title = chat.title

        if settings is not None:
            if page == 1:
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
                text = f"<b>⚙️ Group Settings for {title} (Page 1/2)</b>"
            else:
                antilink = settings.get("antilink", False)
                start_pic = settings.get("start_pic", True)
                buttons = [
                    [
                        InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}#2'),
                        InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}#2')
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
                text = f"<b>⚙️ Group Settings for {title} (Page 2/2)</b>"

            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            except MessageNotModified:
                pass
        await query.answer()
        
    elif query.data.startswith("setgs"):
        _, set_type, status, grp_id, page = query.data.split("#")
        grpid = int(grp_id)
        page_num = int(page)

        user_id = query.from_user.id
        try:
            member = await client.get_chat_member(grpid, user_id)
            if not (member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR] or user_id in ADMINS):
                return await query.answer("⚠️ You need to be an Admin to change settings!", show_alert=True)
        except Exception:
            pass

        new_status = False if status == "True" else True
        await save_group_settings(grpid, set_type, new_status)

        settings = await get_settings(grpid)
        chat = await client.get_chat(grpid)
        title = chat.title

        if settings is not None:
            if page_num == 1:
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
                text = f"<b>⚙️ Group Settings for {title} (Page 1/2)</b>"
            else:
                antilink = settings.get("antilink", False)
                start_pic = settings.get("start_pic", True)
                buttons = [
                    [
                        InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}#2'),
                        InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}#2')
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
                text = f"<b>⚙️ Group Settings for {title} (Page 2/2)</b>"

            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            except MessageNotModified:
                pass
        await query.answer('✅ Settings updated successfully!')
        
    elif query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('⚠️ No such file exists!', show_alert=True)
            
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        chat_id = query.message.chat.id
        
        user = query.from_user
        user_mention = user.mention if user else "Friend"
        user_name = user.first_name if user else "User"
        
        if query.message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
            settings = await get_settings(int(grpid)) if grpid else await get_settings(chat_id)
        else:
            settings = await get_settings(chat_id)
        
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name='' if title is None else title,
                    file_size='' if size is None else size,
                    file_caption='' if f_caption is None else f_caption,
                    user_mention=user_mention,
                    user_name=user_name
                )
            except Exception as e:
                logger.exception(e)
                
        if f_caption is None or f_caption == "":
            f_caption = f"{title}"

        try:
            if settings.get("forcesub", True) and AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm'] and query.message.chat.type != enums.ChatType.PRIVATE:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
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
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False,
                    reply_markup=file_keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
                await query.answer('📤 Sending file...', show_alert=False)
        except UserIsBlocked:
            await query.answer('⚠️ Please unblock the bot in PM first!', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
            
    elif query.data.startswith("checksub"):
        chat_id = query.message.chat.id
        if query.message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
            settings = await get_settings(int(grpid)) if grpid else await get_settings(chat_id)
        else:
            settings = await get_settings(chat_id)
            
        if settings.get("forcesub", True) and AUTH_CHANNEL and not await is_subscribed(client, query):
            return await query.answer("⚠️ Please subscribe to our channel first!", show_alert=True)
            
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('⚠️ No such file exists!', show_alert=True)
            
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        
        user = query.from_user
        user_mention = user.mention if user else "Friend"
        user_name = user.first_name if user else "User"
        
        try:
            thank_text = f"<b>✨ Thank you for joining our update channel, {user_mention}!\n\n👇 Here is your requested file:</b>"
            await client.send_message(
                chat_id=query.from_user.id,
                text=thank_text,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name='' if title is None else title,
                    file_size='' if size is None else size,
                    file_caption='' if f_caption is None else f_caption,
                    user_mention=user_mention,
                    user_name=user_name
                )
            except Exception as e:
                logger.exception(e)
                
        if f_caption is None or f_caption == "":
            f_caption = f"{title}"
            
        await query.answer('📤 Sending file...', show_alert=False)
        
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
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False,
            reply_markup=file_keyboard,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "pages":
        await query.answer()
        
    elif query.data == "start":
        grpid = await active_connection(str(query.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('✘ Close', callback_data='close_data'),
            InlineKeyboardButton('About 〄', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if start_pic_enabled:
            try:
                await query.message.edit_media(
                    media=InputMediaPhoto(random.choice(PICS), caption=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME)),
                    reply_markup=reply_markup
                )
            except Exception:
                await query.message.delete()
                await client.send_photo(
                    chat_id=query.message.chat.id,
                    photo=random.choice(PICS),
                    caption=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            try:
                await query.message.edit_text(
                    text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await client.send_message(
                    chat_id=query.message.chat.id,
                    text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                
    elif query.data == "about":
        grpid = await active_connection(str(query.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='start'),
            InlineKeyboardButton('⏍ Status ⏍', callback_data='stats'),
            InlineKeyboardButton('Close ✘', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if start_pic_enabled:
            try:
                await query.message.edit_media(
                    media=InputMediaPhoto(random.choice(PICS), caption=script.ABOUT_TXT.format(temp.B_NAME)),
                    reply_markup=reply_markup
                )
            except Exception:
                await query.message.delete()
                await client.send_photo(
                    chat_id=query.message.chat.id,
                    photo=random.choice(PICS),
                    caption=script.ABOUT_TXT.format(temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            try:
                await query.message.edit_text(
                    text=script.ABOUT_TXT.format(temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await client.send_message(
                    chat_id=query.message.chat.id,
                    text=script.ABOUT_TXT.format(temp.B_NAME),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='about'),
            InlineKeyboardButton('Refresh ✦', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        db_stats = await get_databases_stats()
        db_data = {stat['db_index']: {'count': stat['count'], 'size': get_size(stat['size'])} for stat in db_stats}
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        
        if query.from_user.id in ADMINS:
            status_text = script.STATUS_TXT.format(
                db1_count=db_data.get(1, {}).get('count', 0),
                db1_size=db_data.get(1, {}).get('size', '0 KB'),
                db2_count=db_data.get(2, {}).get('count', 0),
                db2_size=db_data.get(2, {}).get('size', '0 KB'),
                db3_count=db_data.get(3, {}).get('count', 0),
                db3_size=db_data.get(3, {}).get('size', '0 KB'),
                users=users,
                chats=chats
            )
            await query.message.edit_text(text=status_text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.answer("⚠️ This feature is only for administrators!", show_alert=True)
            
    elif query.data == "rfrsh":
        await query.answer("🔄 Refreshing database stats...")
        grpid = await active_connection(str(query.from_user.id))
        settings = await get_settings(int(grpid)) if grpid else None
        start_pic_enabled = settings.get("start_pic", True) if settings else True

        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='about'),
            InlineKeyboardButton('Refresh ✦', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        
        db_stats = await get_databases_stats()
        db_data = {stat['db_index']: {'count': stat['count'], 'size': get_size(stat['size'])} for stat in db_stats}
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        
        if query.from_user.id in ADMINS:
            status_text = script.STATUS_TXT.format(
                db1_count=db_data.get(1, {}).get('count', 0),
                db1_size=db_data.get(1, {}).get('size', '0 KB'),
                db2_count=db_data.get(2, {}).get('count', 0),
                db2_size=db_data.get(2, {}).get('size', '0 KB'),
                db3_count=db_data.get(3, {}).get('count', 0),
                db3_size=db_data.get(3, {}).get('size', '0 KB'),
                users=users,
                chats=chats
            )
            if start_pic_enabled:
                try:
                    await client.edit_message_media(
                        query.message.chat.id, 
                        query.message.id, 
                        InputMediaPhoto(random.choice(PICS), caption=status_text),
                        reply_markup=reply_markup
                    )
                    return
                except Exception:
                    pass
            await query.message.edit_text(text=status_text, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            await query.answer("⚠️ This feature is only for administrators!", show_alert=True)


async def auto_filter(client: Client, msg, spoll=False):
    if not spoll:
        message = msg
        chat_id = message.chat.id
        
        if not message.text:
            return

        if message.text.startswith("/"):
            return  
            
        if message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(message.from_user.id))
            settings = await get_settings(int(grpid)) if grpid is not None else await get_settings(chat_id)
        else:
            settings = await get_settings(chat_id)

        if len(message.text) > 100:
            return
            
        search = message.text
        files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
        if not files:
            if settings.get("spell_check", True):
                if message.chat.type == enums.ChatType.PRIVATE:
                    user_mention = message.from_user.mention if message.from_user else "Friend"
                    msg_text = (
                        f"<b>Hey {user_mention} 👋</b>\n\n"
                        f"<b>❗ <i>No Results found for <code>{message.text}</code>..</i> 🥹</b>\n\n"
                        f"<i>Please check the spelling or use the buttons below to find the correct title!</i>"
                    )
                    search_query = message.text.replace(" ", "+")
                    btn = [[
                        InlineKeyboardButton(text="🔎 GOOGLΣ", url=f"https://google.com/search?q={search_query}"),
                        InlineKeyboardButton(text="🔮 IMDᗷ", url=f"https://imdb.com/find?q={search_query}")
                    ]]
                    sent_msg = await message.reply_text(text=msg_text, reply_markup=InlineKeyboardMarkup(btn))
                    await asyncio.sleep(5)
                    try:
                        await sent_msg.delete()
                        await message.delete()
                    except Exception:
                        pass
                    return
                else:
                    return await advantage_spell_chok(msg)
            else:
                return
    else:
        chat_id = msg.message.chat.id
        settings = await get_settings(chat_id) if msg.message.chat.type != enums.ChatType.PRIVATE else (
            await get_settings(int(grpid)) if (grpid := await active_connection(str(msg.message.from_user.id))) is not None else await get_settings(chat_id)
        )
        message = msg.message.reply_to_message  
        search, files, offset, total_results = spoll
        
    pre = 'filep' if settings.get('file_secure', False) else 'file'
    is_series = bool(re.search(r's\d+e\d+|season|episode|ep\d+|bbhin|bigg boss', search, re.IGNORECASE)) or any(re.search(r's\d+e\d+|season|episode|ep\d+', f.file_name, re.IGNORECASE) for f in files)
    
    if is_series:
        btn = []
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            se_match = re.search(r'(s\d+\s*e\d+|season\s*\d+|ep\s*\d+)', f_name, re.IGNORECASE)
            se_tag = f"[{se_match.group(0).upper()}] " if se_match else ""
            btn.append([InlineKeyboardButton(text=f"⚡ {f_size} ◾ {se_tag}{f_name}", callback_data=f'{pre}#{file.file_id}')])
    else:
        if settings.get('button', True):
            btn = [[InlineKeyboardButton(text=f"⚡ {get_size(file.file_size)} ◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}')] for file in files]
        else:
            btn = [[
                InlineKeyboardButton(text=f"⚡ {get_size(file.file_size)}", callback_data=f'{pre}#{file.file_id}'),
                InlineKeyboardButton(text=f"◾ {file.file_name}", callback_data=f'{pre}#{file.file_id}')
            ] for file in files]   

    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    BUTTONS[key] = search
    
    btn.insert(0, [
        InlineKeyboardButton(f'☂️ {search} ', 'dupe')
    ])
    btn.insert(1, [
        InlineKeyboardButton('LΔΠGUΔGΣ', callback_data=f'lang_menu#{req}#{key}'),
        InlineKeyboardButton('QUΔLITY', callback_data=f'qual_menu#{req}#{key}')
    ])

    if offset != "" and int(total_results) > 10:
        btn.append([
            InlineKeyboardButton(text="ΠΣXT ⏭️", callback_data=f"next_{req}_{key}_{offset}"),
            InlineKeyboardButton(text="DΣLΣTΣD 🗑️", callback_data="close_data")
        ])
    else:
        btn.append([
            InlineKeyboardButton(text="DΣLΣTΣD 🗑️", callback_data="close_data")
        ])

    total_pages = math.ceil(int(total_results) / 10) if total_results else 1

    imdb = await get_poster(search, file=(files[0]).file_name) if settings.get("imdb", True) else None
    if imdb:
        TEMPLATE = settings.get('template', IMDB_TEMPLATE) or IMDB_TEMPLATE
        try:
            cap = TEMPLATE.format(
                query=search, title=imdb['title'], votes=imdb['votes'], aka=imdb["aka"],
                seasons=imdb["seasons"], box_office=imdb['box_office'], localized_title=imdb['localized_title'],
                kind=imdb['kind'], imdb_id=imdb["imdb_id"], cast=imdb["cast"], runtime=imdb['runtime'],
                countries=imdb["countries"], certificates=imdb["certificates"], languages=imdb["languages"],
                director=imdb['director'], writer=imdb['writer'], producer=imdb['producer'], composer=imdb['composer'],
                cinematographer=imdb['cinematographer'], music_team=imdb['music_team'], distributors=imdb['distributors'],
                release_date=imdb['release_date'], year=imdb['year'], genres=imdb['genres'], poster=imdb['poster'],
                plot=imdb['plot'], rating=imdb['rating'], url=imdb['url'], **locals()
            )
        except Exception as e:
            logger.exception(e)
            cap = f"<b>🎬 {imdb['title']} ({imdb['year']})</b>\n\n<b>⭐ Rating :</b> {imdb['rating']}\n<b>🎭 Genres :</b> {imdb['genres']}\n\n{imdb['plot']}"
        cap += f"\n\n<b>📕 Pᴀɢᴇ :</b> 1 / {total_pages}"
    else:
        IST = pytz.timezone('Asia/Kolkata')
        now = datetime.now(IST)
        
        current_time = now.strftime("%I:%M:%S %p")
        current_day = now.strftime("%A")
        current_date = now.strftime("%d-%m-%Y")
        
        user_mention = message.from_user.mention if message.from_user else "Friend"
        
        cap = (
            f"<b>╭⎋ • Hᴇʏ 👋 {user_mention}💝,\n"
            f"╰⎋ • Tɪᴛʟᴇ : {search}</b>"
            f"\n\n"
            f"<b>⌚ Tɪᴍᴇ :</b> {current_time}\n"
            f"<b>☁️ Dᴀʏ :</b> {current_day}\n"
            f"<b>📅 Dᴀᴛᴇ :</b> {current_date}\n"
            f"<b>📕 Pᴀɢᴇ :</b> 1 / {total_pages}"
            f"\n\n"
            f"<b>{message.chat.title}</b>"
        )

    if imdb and imdb.get('poster'):
        try:
            sent_message = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            poster = imdb.get('poster').replace('.jpg', "._V1_UX360.jpg")
            sent_message = await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            sent_message = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    else:
        chosen_photo = NOR_IMG
        if isinstance(chosen_photo, list):
            photo_to_send = random.choice(chosen_photo)
        else:
            photo_to_send = chosen_photo

        try:
            sent_message = await message.reply_photo(
                photo=photo_to_send,
                caption=cap[:1024],
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            sent_message = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        
    if spoll:
        await msg.message.delete()

    async def delete_after_delay():
        await asyncio.sleep(300)
        
        user = message.from_user
        user_mention = user.mention if user else "Friend"
        movie_title = search
        
        try:
            await sent_message.delete()
        except Exception:
            pass

        try:
            await message.delete()
        except Exception:
            pass

        try:
            notify_text = (
                f"<b>========{{{user_mention}}}===========\n\n"
                f"𝖸𝗈𝗎𝗋 𝖱𝖾𝗊𝗎𝖾𝗌ᴛ <u>[{movie_title}]</u> 𝖧𝖺𝗌 𝖡𝖾𝖾𝗇 𝖣𝖾𝗅𝖾𝗍𝖾𝖽 🗑 \n"
                f"(𝖣𝗎𝖾 𝖳𝗈 𝖠𝗏𝗈𝗂𝖽 𝖢𝗈𝗉𝗒𝗋𝗂𝗀𝗁𝗍𝗌 𝖨𝗌𝗌𝗎𝖾😌)\n"
                f"==============================\n"
                f"𝖨𝖥 𝖸𝖮𝖴 𝖶𝖠𝖭𝖳 𝖳𝖧𝖠𝖳 𝖥𝖨𝖫𝖤, 𝖱𝖤𝗤𝖴𝖤𝖲𝖳 𝖠𝖦𝖠𝖨𝗭\n"
                f"==============================</b>"
            )
            
            photo_url = "https://envs.sh/RCE.jpg"
            photo_msg = None
            try:
                photo_msg = await client.send_photo(
                    chat_id=message.chat.id,
                    photo=photo_url,
                    caption=notify_text
                )
            except Exception:
                photo_msg = await client.send_message(
                    chat_id=message.chat.id,
                    text=notify_text
                )
            
            await asyncio.sleep(10)
            
            if photo_msg:
                try:
                    await photo_msg.delete()
                except Exception:
                    pass
            
        except Exception:
            pass

    asyncio.create_task(delete_after_delay())


async def advantage_spell_chok(msg):
    mv_rqst = msg.text
    search = msg.text.replace(" ", "+")
    btn = [[
        InlineKeyboardButton(text="🔎 GOOGLΣ", url=f"https://google.com/search?q={search}"),
        InlineKeyboardButton(text="🔮 IMDᗷ", url=f"https://imdb.com/find?q={search}")
    ]]
    
    user_mention = msg.from_user.mention if msg.from_user else "Friend"
    
    await msg.reply_photo(
        photo="https://envs.sh/RCE.jpg", 
        caption=NON_IMG.format(user_mention=user_mention, mv_rqst=mv_rqst),
        reply_markup=InlineKeyboardMarkup(btn)
    )
    await msg.delete()
    return


async def manual_filters(client: Client, message, text=False):
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
                                group_id, reply_text, disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button), reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id, fileid, caption=reply_text or "", reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn) if btn else []
                        await message.reply_cached_media(
                            fileid, caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button), reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
