"""
Core Filter Management Module
Allows administrators to add, view, delete, and purge keyword filters 
for connected groups and channels with robust permission checks.
"""

import io
import logging
from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.filters_mdb import (
    add_filter,
    get_filters,
    delete_filter,
    count_filters
)
from database.connections_mdb import active_connection
from utils import get_file_id, parser, split_quotes
from info import ADMINS

logger = logging.getLogger(__name__)


@Client.on_message(filters.command(['filter', 'add']) & filters.incoming & filters.user(ADMINS))
async def add_filter_handler(client: Client, message):
    """
    Adds a new keyword filter with text, media, or inline buttons
    to the target active group or current chat.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use: <code>/connect {message.chat.id}</code> in my private messages.",
            parse_mode=enums.ParseMode.HTML
        )
        
    chat_type = message.chat.type
    command_args = message.text.html.split(None, 1)

    # Resolve target group ID based on chat context
    if chat_type == enums.ChatType.PRIVATE:
        active_group_id = await active_connection(str(user_id))
        if active_group_id is not None:
            grp_id = active_group_id
            try:
                chat_info = await client.get_chat(active_group_id)
                title = chat_info.title
            except Exception:
                await message.reply_text("❌ <b>Make sure I am still present in your target group!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
                return
        else:
            await message.reply_text("❌ <b>You are not connected to any groups! Use /connect first.</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    # Verify admin privileges
    try:
        member_status = await client.get_chat_member(grp_id, user_id)
        if (
            member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
            and user_id not in ADMINS
            and str(user_id) not in [str(admin) for admin in ADMINS]
        ):
            return
    except Exception:
        return

    if len(command_args) < 2:
        await message.reply_text(
            "<b>❌ Incomplete Command Format!</b>\n\n"
            "📌 <i>Usage:</i> <code>/filter keyword reply_text</code>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
        return

    extracted_parts = split_quotes(command_args[1])
    filter_keyword = extracted_parts[0].lower()

    if not message.reply_to_message and len(extracted_parts) < 2:
        await message.reply_text("❌ <b>Please provide some content or text to save your filter!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
        return

    file_id = None
    reply_text = ""
    btn = "[]"
    alert = None

    # Parse payload based on message type (Reply / Direct text / Media)
    if (len(extracted_parts) >= 2) and not message.reply_to_message:
        reply_text, btn, alert = parser(extracted_parts[1], filter_keyword)
        if not reply_text:
            await message.reply_text("❌ <b>You cannot have buttons alone, please include some text!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return

    elif message.reply_to_message and message.reply_to_message.reply_markup:
        try:
            markup = message.reply_to_message.reply_markup
            btn = markup.inline_keyboard
            media_msg = get_file_id(message.reply_to_message)
            if media_msg:
                file_id = media_msg.file_id
                reply_text = message.reply_to_message.caption.html if message.reply_to_message.caption else ""
            else:
                reply_text = message.reply_to_message.text.html if message.reply_to_message.text else ""
                file_id = None
        except Exception:
            reply_text = ""
            btn = "[]"
            file_id = None

    elif message.reply_to_message and message.reply_to_message.media:
        try:
            media_msg = get_file_id(message.reply_to_message)
            file_id = media_msg.file_id if media_msg else None
            if message.reply_to_message.sticker:
                reply_text, btn, alert = parser(extracted_parts[1], filter_keyword)
            else:
                caption_text = message.reply_to_message.caption.html if message.reply_to_message.caption else ""
                reply_text, btn, alert = parser(caption_text, filter_keyword)
        except Exception:
            reply_text = ""
            btn = "[]"
            alert = None

    elif message.reply_to_message and message.reply_to_message.text:
        try:
            file_id = None
            reply_text, btn, alert = parser(message.reply_to_message.text.html, filter_keyword)
        except Exception:
            reply_text = ""
            btn = "[]"
            alert = None
    else:
        return

    # Save filter into database
    await add_filter(grp_id, filter_keyword, reply_text, btn, file_id, alert)

    await message.reply_text(
        f"✅ <b>Filter successfully added!</b>\n\n"
        f"🔑 <b>Keyword:</b> <code>{filter_keyword}</code>\n"
        f"📍 <b>Target Group:</b> <b>{title}</b>",
        quote=True,
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(filters.command(['viewfilters', 'filters']) & filters.incoming & filters.user(ADMINS))
async def get_all_filters_handler(client: Client, message):
    """
    Retrieves and lists all active keyword filters configured for the target chat.
    Sends as a document file if the list exceeds Telegram message length limits.
    """
    chat_type = message.chat.type
    user_id = message.from_user.id if message.from_user else None
    
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use: <code>/connect {message.chat.id}</code> in PM.",
            parse_mode=enums.ParseMode.HTML
        )
        
    if chat_type == enums.ChatType.PRIVATE:
        active_group_id = await active_connection(str(user_id))
        if active_group_id is not None:
            grp_id = active_group_id
            try:
                chat_info = await client.get_chat(active_group_id)
                title = chat_info.title
            except Exception:
                await message.reply_text("❌ <b>Make sure I am still present in your target group!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
                return
        else:
            await message.reply_text("❌ <b>You are not connected to any groups! Use /connect first.</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    try:
        member_status = await client.get_chat_member(grp_id, user_id)
        if (
            member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
            and user_id not in ADMINS
            and str(user_id) not in [str(admin) for admin in ADMINS]
        ):
            return
    except Exception:
        return

    filter_texts = await get_filters(grp_id)
    filter_count = await count_filters(grp_id)
    
    if filter_count and filter_count > 0:
        filter_list_content = f"📋 Total active filters in {title} : {filter_count}\n\n"
        for text in filter_texts:
            filter_list_content += f" ×  {text}\n"

        if len(filter_list_content) > 4096:
            with io.BytesIO(str.encode(filter_list_content.replace("`", ""))) as keyword_file:
                keyword_file.name = "filter_keywords.txt"
                await message.reply_document(
                    document=keyword_file,
                    caption=f"📁 <b>Complete Filter List for {title}</b>",
                    quote=True,
                    parse_mode=enums.ParseMode.HTML
                )
            return
    else:
        filter_list_content = f"📂 <b>There are no active filters configured in {title}!</b>"

    await message.reply_text(
        text=f"<b>{filter_list_content}</b>",
        quote=True,
        parse_mode=enums.ParseMode.HTML
    )
        

@Client.on_message(filters.command('del') & filters.incoming & filters.user(ADMINS))
async def delete_filter_handler(client: Client, message):
    """
    Deletes a specific keyword filter from the database.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use: <code>/connect {message.chat.id}</code> in PM.",
            parse_mode=enums.ParseMode.HTML
        )
        
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        active_group_id = await active_connection(str(user_id))
        if active_group_id is not None:
            grp_id = active_group_id
            try:
                chat_info = await client.get_chat(active_group_id)
                title = chat_info.title
            except Exception:
                await message.reply_text("❌ <b>Make sure I am still present in your target group!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
                return
        else:
            await message.reply_text("❌ <b>You are not connected to any groups! Use /connect first.</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    try:
        member_status = await client.get_chat_member(grp_id, user_id)
        if (
            member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
            and user_id not in ADMINS
            and str(user_id) not in [str(admin) for admin in ADMINS]
        ):
            return
    except Exception:
        return

    try:
        _, query_text = message.text.split(" ", 1)
    except ValueError:
        await message.reply_text(
            "<b>❌ Missing Filter Name!</b>\n\n"
            "📌 <i>Usage:</i> <code>/del &lt;filter_name&gt;</code>\n"
            "💡 Use <code>/viewfilters</code> to see all available filters.",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
        return

    clean_query = query_text.lower().strip()
    await delete_filter(message, clean_query, grp_id)
        

@Client.on_message(filters.command('delall') & filters.incoming & filters.user(ADMINS))
async def delete_all_filters_confirmation_handler(client: Client, message):
    """
    Triggers an interactive confirmation prompt to delete all filters in the target group.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use: <code>/connect {message.chat.id}</code> in PM.",
            parse_mode=enums.ParseMode.HTML
        )
        
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        active_group_id = await active_connection(str(user_id))
        if active_group_id is not None:
            grp_id = active_group_id
            try:
                chat_info = await client.get_chat(active_group_id)
                title = chat_info.title
            except Exception:
                await message.reply_text("❌ <b>Make sure I am still present in your target group!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
                return
        else:
            await message.reply_text("❌ <b>You are not connected to any groups! Use /connect first.</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    try:
        member_status = await client.get_chat_member(grp_id, user_id)
        if (
            member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
            and user_id not in ADMINS
            and str(user_id) not in [str(admin) for admin in ADMINS]
        ):
            return
    except Exception:
        return

    if (member_status.status == enums.ChatMemberStatus.OWNER) or (user_id in ADMINS) or (str(user_id) in [str(a) for a in ADMINS]):
        confirmation_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(text="✅ YES, DELETE ALL", callback_data="delallconfirm")],
            [InlineKeyboardButton(text="❌ CANCEL", callback_data="delallcancel")]
        ])
        
        await message.reply_text(
            f"⚠️ <b>Warning: Dangerous Action!</b>\n\n"
            f"This will permanently delete <b>ALL filters</b> from <b>{title}</b>.\n"
            f"Do you want to continue?",
            reply_markup=confirmation_buttons,
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
