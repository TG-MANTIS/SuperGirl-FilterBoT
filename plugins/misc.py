"""
Miscellaneous Utilities & Information Module
Handles administrative utility commands such as checking user ID info,
detailed user profile inspection, and interactive IMDb movie/series search.
"""

import os
import time
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import IMDB_TEMPLATE, ADMINS
from utils import extract_user, get_file_id, get_poster, last_online

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.command('id') & filters.user(ADMINS))
async def show_user_or_chat_id_handler(client: Client, message):
    """
    Retrieves detailed Telegram ID information for private chats or groups/supergroups.
    """
    chat_type = message.chat.type
    
    if chat_type == "private":
        user_id = message.chat.id
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name or ""
        username = message.from_user.username or "None"
        dc_id = message.from_user.dc_id or ""
        
        await message.reply_text(
            f"<b>➲ First Name:</b> {first_name}\n"
            f"<b>➲ Last Name:</b> {last_name}\n"
            f"<b>➲ Username:</b> @{username}\n"
            f"<b>➲ Telegram ID:</b> <code>{user_id}</code>\n"
            f"<b>➲ Data Centre:</b> <code>{dc_id}</code>",
            quote=True
        )

    elif chat_type in ["group", "supergroup"]:
        response_text = f"<b>➲ Chat ID</b>: <code>{message.chat.id}</code>\n"
        
        if message.reply_to_message:
            response_text += (
                f"<b>➲ User ID</b>: <code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                f"<b>➲ Replied User ID</b>: <code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            response_text += f"<b>➲ User ID</b>: <code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            file_info = get_file_id(message)
            
        if file_info:
            response_text += f"<b>{file_info.message_type}</b>: <code>{file_info.file_id}</code>\n"
            
        await message.reply_text(response_text, quote=True)


@Client.on_message(filters.command(["info"]) & filters.user(ADMINS))
async def who_is_user_handler(client: Client, message):
    """
    Fetches comprehensive public profile information and display picture of a target user.
    """
    status_message = await message.reply_text("`Fetching user info...`")
    await status_message.edit("`Processing user info...`")
    
    from_user_id, _ = extract_user(message)
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        await status_message.edit(str(error))
        return
        
    if from_user is None:
        return await status_message.edit("❌ No valid user ID or message specified!")
        
    message_out_str = ""
    message_out_str += f"<b>➲ First Name:</b> {from_user.first_name}\n"
    last_name = from_user.last_name or "<b>None</b>"
    message_out_str += f"<b>➲ Last Name:</b> {last_name}\n"
    message_out_str += f"<b>➲ Telegram ID:</b> <code>{from_user.id}</code>\n"
    
    dc_id = from_user.dc_id or "[User Doesn't Have A Valid DP]"
    username = from_user.username or "<b>None</b>"
    
    message_out_str += f"<b>➲ Data Centre:</b> <code>{dc_id}</code>\n"
    message_out_str += f"<b>➲ Username:</b> @{username}\n"
    message_out_str += f"<b>➲ User Link:</b> <a href='tg://user?id={from_user.id}'><b>Click Here</b></a>\n"
    
    if message.chat.type in ("supergroup", "channel"):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = datetime.fromtimestamp(
                chat_member_p.joined_date or time.time()
            ).strftime("%Y.%m.%d %H:%M:%S")
            message_out_str += f"<b>➲ Joined this Chat on:</b> <code>{joined_date}</code>\n"
        except UserNotParticipant:
            pass
            
    close_button = InlineKeyboardMarkup([[InlineKeyboardButton('🔐 Close', callback_data='close_data')]])
    chat_photo = from_user.photo
    
    if chat_photo:
        try:
            local_user_photo = await client.download_media(message=chat_photo.big_file_id)
            await message.reply_photo(
                photo=local_user_photo,
                quote=True,
                reply_markup=close_button,
                caption=message_out_str,
                parse_mode="html",
                disable_notification=True
            )
            os.remove(local_user_photo)
        except Exception:
            await message.reply_text(
                text=message_out_str,
                reply_markup=close_button,
                quote=True,
                parse_mode="html",
                disable_notification=True
            )
    else:
        await message.reply_text(
            text=message_out_str,
            reply_markup=close_button,
            quote=True,
            parse_mode="html",
            disable_notification=True
        )
        
    await status_message.delete()


@Client.on_message(filters.command(["imdb", 'search']) & filters.user(ADMINS))
async def imdb_search_handler(client: Client, message):
    """
    Searches IMDb database for movies or series based on query text and returns matching results.
    """
    if ' ' in message.text:
        status_reply = await message.reply('🔍 Searching IMDb database...')
        _, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        
        if not movies:
            return await status_reply.edit("❌ No results found on IMDb!")
            
        inline_buttons = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} ({movie.get('year')})",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await status_reply.edit('🎬 <b>Here is what I found on IMDb:</b>', reply_markup=InlineKeyboardMarkup(inline_buttons), parse_mode="html")
    else:
        await message.reply('❌ <b>Please provide a movie or series name!</b>\n📌 <i>Usage:</i> <code>/imdb Avatar</code>', parse_mode="html")


@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback_handler(bot: Client, query: CallbackQuery):
    """
    Handles IMDb search result selection and displays formatted movie details with poster.
    """
    _, movie_id = query.data.split('#')
    imdb_data = await get_poster(query=movie_id, id=True)
    
    inline_buttons = []
    if imdb_data and imdb_data.get('url'):
        inline_buttons.append([InlineKeyboardButton(text=f"🔗 {imdb_data.get('title')} on IMDb", url=imdb_data['url'])])
        
    target_message = query.message.reply_to_message or query.message
    
    if imdb_data:
        caption_text = IMDB_TEMPLATE.format(
            query=imdb_data.get('title'),
            title=imdb_data.get('title'),
            votes=imdb_data.get('votes'),
            aka=imdb_data.get("aka"),
            seasons=imdb_data.get("seasons"),
            box_office=imdb_data.get('box_office'),
            localized_title=imdb_data.get('localized_title'),
            kind=imdb_data.get('kind'),
            imdb_id=imdb_data.get("imdb_id"),
            cast=imdb_data.get("cast"),
            runtime=imdb_data.get("runtime"),
            countries=imdb_data.get("countries"),
            certificates=imdb_data.get("certificates"),
            languages=imdb_data.get("languages"),
            director=imdb_data.get("director"),
            writer=imdb_data.get("writer"),
            producer=imdb_data.get("producer"),
            composer=imdb_data.get("composer"),
            cinematographer=imdb_data.get("cinematographer"),
            music_team=imdb_data.get("music_team"),
            distributors=imdb_data.get("distributors"),
            release_date=imdb_data.get('release_date'),
            year=imdb_data.get('year'),
            genres=imdb_data.get('genres'),
            poster=imdb_data.get('poster'),
            plot=imdb_data.get('plot'),
            rating=imdb_data.get('rating'),
            url=imdb_data.get('url'),
            **locals()
        )
    else:
        caption_text = "❌ No results found!"

    if imdb_data and imdb_data.get('poster'):
        try:
            await query.message.reply_photo(photo=imdb_data['poster'], caption=caption_text, reply_markup=InlineKeyboardMarkup(inline_buttons))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic_url = imdb_data.get('poster')
            fallback_poster = pic_url.replace('.jpg', "._V1_UX360.jpg")
            await query.message.reply_photo(photo=fallback_poster, caption=caption_text, reply_markup=InlineKeyboardMarkup(inline_buttons))
        except Exception as err:
            logger.exception(err)
            await query.message.reply(caption_text, reply_markup=InlineKeyboardMarkup(inline_buttons), disable_web_page_preview=False)
        try:
            await query.message.delete()
        except Exception:
            pass
    else:
        await query.message.edit_text(caption_text, reply_markup=InlineKeyboardMarkup(inline_buttons), disable_web_page_preview=False)
        
    await query.answer()
