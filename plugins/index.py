"""
Core Channel & Group Indexing Module
Allows administrators and moderators to securely index media files from target
channels or groups into the filter database with live progress tracking and cancellation support.
"""

import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import ADMINS
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()


@Client.on_callback_query(filters.regex(r'^index'))
async def index_callback_handler(client: Client, query):
    """
    Handles callback queries for accepting, rejecting, or cancelling indexing tasks.
    """
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("⚠️ Indexing process cancelled by admin.", show_alert=True)
        
    _, action_type, chat_id_str, last_msg_id_str, requester_user_id = query.data.split("#")
    
    if action_type == 'reject':
        await query.message.delete()
        try:
            await client.send_message(
                int(requester_user_id),
                f"❌ <b>Your index submission for chat <code>{chat_id_str}</code> has been declined by our moderators.</b>",
                reply_to_message_id=int(last_msg_id_str),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        return

    if lock.locked():
        return await query.answer("⚠️ Another indexing task is currently running. Please wait until it completes.", show_alert=True)
        
    status_message = query.message

    await query.answer("⏳ Initializing indexing queue...", show_alert=True)
    
    if int(requester_user_id) not in ADMINS:
        try:
            await client.send_message(
                int(requester_user_id),
                f"✅ <b>Your index submission for chat <code>{chat_id_str}</code> has been accepted by our moderators and will be processed soon.</b>",
                reply_to_message_id=int(last_msg_id_str),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
            
    await status_message.edit_text(
        "🚀 <b>Starting Database Indexing...</b>\n<i>Please wait while files are being fetched.</i>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('❌ Cancel Indexing', callback_data='index_cancel')]]
        ),
        parse_mode=enums.ParseMode.HTML
    )
    
    try:
        resolved_chat_target = int(chat_id_str)
    except ValueError:
        resolved_chat_target = chat_id_str
        
    await index_files_to_db(int(last_msg_id_str), resolved_chat_target, status_message, client)


@Client.on_message((filters.forwarded | (filters.regex(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text) & filters.private & filters.incoming)
async def request_index_handler(client: Client, message):
    """
    Receives channel/group links or forwarded messages and initiates an index request.
    """
    if message.text:
        link_regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = link_regex.match(message.text)
        if not match:
            return await message.reply("❌ <b>Invalid link specified! Please send a valid Telegram message link.</b>", parse_mode=enums.ParseMode.HTML)
            
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
            
    elif message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return

    try:
        await client.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply("❌ <b>Private channel/group detected! Please make me an administrator there before indexing.</b>", parse_mode=enums.ParseMode.HTML)
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("❌ <b>Invalid username or link specified!</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        logger.exception(err)
        return await message.reply(f"❌ <b>Error occurred:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)
        
    try:
        sample_msg = await client.get_messages(chat_id, last_msg_id)
    except Exception:
        return await message.reply("❌ <b>Access denied! Please ensure I am added as an administrator in that target channel.</b>", parse_mode=enums.ParseMode.HTML)
        
    if sample_msg.empty:
        return await message.reply("❌ <b>Target message is empty or inaccessible. Make sure I have proper admin rights.</b>", parse_mode=enums.ParseMode.HTML)

    if message.from_user.id in ADMINS:
        action_buttons = [
            [
                InlineKeyboardButton('✅ Yes, Start Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
            ],
            [
                InlineKeyboardButton('❌ Close', callback_data='close_data'),
            ]
        ]
        return await message.reply(
            f"📌 <b>Do you want to index this channel/group?</b>\n\n"
            f"💬 <b>Chat ID / Username:</b> <code>{chat_id}</code>\n"
            f"🔢 <b>Last Message ID:</b> <code>{last_msg_id}</code>",
            reply_markup=InlineKeyboardMarkup(action_buttons),
            parse_mode=enums.ParseMode.HTML
        )

    # Generate invite link for private chats if requested by non-admin users
    if isinstance(chat_id, int):
        try:
            invite_obj = await client.create_chat_invite_link(chat_id)
            chat_invite_link = invite_obj.invite_link
        except ChatAdminRequired:
            return await message.reply("❌ <b>I need the 'Generate Invite Link' administrator permission in that chat to process this request.</b>", parse_mode=enums.ParseMode.HTML)
    else:
        chat_invite_link = f"@{message.forward_from_chat.username}"

    moderator_buttons = [
        [
            InlineKeyboardButton('✅ Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],
        [
            InlineKeyboardButton('❌ Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
        ]
    ]
    
    log_channel_text = (
        f"📥 <b>#IndexRequest Received</b>\n\n"
        f"👤 <b>Requested By:</b> {message.from_user.mention} (<code>{message.from_user.id}</code>)\n"
        f"💬 <b>Chat ID / Username:</b> <code>{chat_id}</code>\n"
        f"🔢 <b>Last Message ID:</b> <code>{last_msg_id}</code>\n"
        f"🔗 <b>Invite Link:</b> {chat_invite_link}"
    )
    
    try:
        await client.send_message(LOG_CHANNEL, log_channel_text, reply_markup=InlineKeyboardMarkup(moderator_buttons), parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        logger.error(f"Failed to send index request to log channel: {err}")

    await message.reply("✅ <b>Thank you for your contribution! Please wait for our moderators to review and verify your request.</b>", parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number_handler(client: Client, message):
    """
    Sets the starting offset (skip number) for file indexing operations.
    """
    if ' ' in message.text:
        _, skip_value = message.text.split(" ", 1)
        try:
            skip_int = int(skip_value)
        except ValueError:
            return await message.reply("❌ <b>Please provide a valid numeric value for skip offset!</b>", parse_mode=enums.ParseMode.HTML)
            
        temp.CURRENT = skip_int
        await message.reply(f"✅ <b>Successfully set indexing skip offset to:</b> <code>{skip_int}</code>", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply("❌ <b>Please provide a number! Usage:</b> <code>/setskip 100</code>", parse_mode=enums.ParseMode.HTML)


async def index_files_to_db(lst_msg_id, chat, status_msg, client):
    """
    Background worker that iterates through channel messages and indexes media files into the database.
    """
    total_files_saved = 0
    duplicate_count = 0
    error_count = 0
    deleted_count = 0
    no_media_count = 0
    unsupported_count = 0
    
    async with lock:
        try:
            current_message_index = temp.CURRENT
            temp.CANCEL = False
            
            async for msg_item in client.iter_messages(chat, lst_msg_id, temp.CURRENT):
                if temp.CANCEL:
                    cancel_report = (
                        f"⚠️ <b>Indexing Process Cancelled Successfully!</b>\n\n"
                        f"💾 <b>Saved Files:</b> <code>{total_files_saved}</code>\n"
                        f"🔄 <b>Duplicates Skipped:</b> <code>{duplicate_count}</code>\n"
                        f"🗑️ <b>Deleted Messages Skipped:</b> <code>{deleted_count}</code>\n"
                        f"🚫 <b>Non-Media Skipped:</b> <code>{no_media_count + unsupported_count}</code> (Unsupported: <code>{unsupported_count}</code>)\n"
                        f"❌ <b>Errors Occurred:</b> <code>{error_count}</code>"
                    )
                    await status_msg.edit_text(cancel_report, parse_mode=enums.ParseMode.HTML)
                    return
                    
                current_message_index += 1
                
                # Update progress every 20 messages
                if current_message_index % 20 == 0:
                    cancel_markup = InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel Indexing', callback_data='index_cancel')]])
                    progress_text = (
                        f"📊 <b>Indexing in Progress...</b>\n\n"
                        f"🔍 <b>Fetched Messages:</b> <code>{current_message_index}</code>\n"
                        f"💾 <b>Successfully Saved:</b> <code>{total_files_saved}</code>\n"
                        f"🔄 <b>Duplicates Skipped:</b> <code>{duplicate_count}</code>\n"
                        f"🗑️ <b>Deleted Skipped:</b> <code>{deleted_count}</code>\n"
                        f"🚫 <b>Non-Media Skipped:</b> <code>{no_media_count + unsupported_count}</code> (Unsupported: <code>{unsupported_count}</code>)\n"
                        f"❌ <b>Errors:</b> <code>{error_count}</code>"
                    )
                    try:
                        await status_msg.edit_text(progress_text, reply_markup=cancel_markup, parse_mode=enums.ParseMode.HTML)
                    except Exception:
                        pass
                        
                if msg_item.empty:
                    deleted_count += 1
                    continue
                elif not msg_item.media:
                    no_media_count += 1
                    continue
                elif msg_item.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported_count += 1
                    continue
                    
                media_payload = getattr(msg_item, msg_item.media.value, None)
                if not media_payload:
                    unsupported_count += 1
                    continue
                    
                media_payload.file_type = msg_item.media.value
                media_payload.caption = msg_item.caption
                
                save_status, save_code = await save_file(media_payload)
                if save_status:
                    total_files_saved += 1
                elif save_code == 0:
                    duplicate_count += 1
                elif save_code == 2:
                    error_count += 1
                    
        except Exception as err:
            logger.exception(err)
            try:
                await status_msg.edit_text(f"❌ <b>Indexing Error Occurred:</b>\n<code>{err}</code>", parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
        else:
            completion_report = (
                f"✅ <b>Indexing Completed Successfully!</b>\n\n"
                f"💾 <b>Total Files Saved:</b> <code>{total_files_saved}</code>\n"
                f"🔄 <b>Duplicate Files Skipped:</b> <code>{duplicate_count}</code>\n"
                f"🗑️ <b>Deleted Messages Skipped:</b> <code>{deleted_count}</code>\n"
                f"🚫 <b>Non-Media Messages Skipped:</b> <code>{no_media_count + unsupported_count}</code> (Unsupported: <code>{unsupported_count}</code>)\n"
                f"❌ <b>Errors Encountered:</b> <code>{error_count}</code>"
            )
            try:
                await status_msg.edit_text(completion_report, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
