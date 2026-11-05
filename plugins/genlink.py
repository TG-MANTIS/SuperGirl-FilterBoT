"""
Core Link & Batch Link Generation Module
Enables administrators to generate secure direct shareable links and bulk batch links
for media files and documents with robust validation and logging support.
"""

import re
import os
import json
import base64
import logging
from pyrogram import filters, Client, enums
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from info import ADMINS, LOG_CHANNEL, FILE_STORE_CHANNEL, PUBLIC_FILE_STORE
from database.ia_filterdb import unpack_new_file_id
from utils import temp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def allowed_access_filter(_, __, message):
    """
    Validates if the user is authorized to generate file store links.
    """
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False

@Client.on_message(filters.command(['link', 'plink']) & filters.create(allowed_access_filter) & filters.user(ADMINS))
async def generate_single_link_handler(client: Client, message):
    """
    Generates a secure, shareable deep-link for a replied media file or document.
    """
    replied_message = message.reply_to_message
    if not replied_message:
        return await message.reply("❌ <b>Please reply to a media message to generate a shareable link!</b>", parse_mode=enums.ParseMode.HTML)
        
    file_type = replied_message.media
    if file_type not in ["video", "audio", "document"]:
        return await message.reply("❌ <b>Unsupported media type! Please reply to a video, audio, or document.</b>", parse_mode=enums.ParseMode.HTML)
        
    if message.has_protected_content and message.chat.id not in ADMINS:
        return await message.reply("okDa")
        
    try:
        media_object = getattr(replied_message, file_type)
        file_id, _ = unpack_new_file_id(media_object.file_id)
        
        prefix_string = 'filep_' if message.text.lower().strip() == "/plink" else 'file_'
        prefix_string += file_id
        
        encoded_string = base64.urlsafe_b64encode(prefix_string.encode("ascii")).decode().strip("=")
        
        response_text = (
            f"🔗 <b>Successfully Generated Link:</b>\n\n"
            f"<code>https://t.me/{temp.U_NAME}?start={encoded_string}</code>"
        )
        await message.reply(response_text, parse_mode=enums.ParseMode.HTML)
        
    except Exception as err:
        logger.error(f"Failed to generate single link: {err}")
        await message.reply("❌ <b>An unexpected error occurred while generating the link.</b>", parse_mode=enums.ParseMode.HTML)
    
    
@Client.on_message(filters.command(['batch', 'pbatch']) & filters.create(allowed_access_filter) & filters.user(ADMINS))
async def generate_batch_link_handler(client: Client, message):
    """
    Generates a bulk batch sharing link for multiple media messages between a specified range.
    """
    if " " not in message.text:
        return await message.reply(
            "<b>❌ Incorrect Command Format!</b>\n\n"
            "📌 <i>Usage:</i> <code>/batch &lt;first_link&gt; &lt;last_link&gt;</code>\n"
            "💡 <i>Example:</i> <code>/batch https://t.me/YourChannel/10 https://t.me/YourChannel/20</code>",
            parse_mode=enums.ParseMode.HTML
        )
        
    command_parts = message.text.strip().split(" ")
    if len(command_parts) != 3:
        return await message.reply(
            "<b>❌ Incorrect Command Format!</b>\n\n"
            "📌 <i>Usage:</i> <code>/batch &lt;first_link&gt; &lt;last_link&gt;</code>",
            parse_mode=enums.ParseMode.HTML
        )
        
    command_prefix, first_link, last_link = command_parts
    
    # Regex pattern to parse Telegram message links
    link_regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    
    first_match = link_regex.match(first_link)
    if not first_match:
        return await message.reply("❌ <b>Invalid starting link specified!</b>", parse_mode=enums.ParseMode.HTML)
        
    f_chat_id = first_match.group(4)
    f_msg_id = int(first_match.group(5))
    if f_chat_id.isnumeric():
        f_chat_id = int(("-100" + f_chat_id))

    last_match = link_regex.match(last_link)
    if not last_match:
        return await message.reply("❌ <b>Invalid ending link specified!</b>", parse_mode=enums.ParseMode.HTML)
        
    l_chat_id = last_match.group(4)
    l_msg_id = int(last_match.group(5))
    if l_chat_id.isnumeric():
        l_chat_id = int(("-100" + l_chat_id))

    if f_chat_id != l_chat_id:
        return await message.reply("❌ <b>Chat IDs do not match between the provided links!</b>", parse_mode=enums.ParseMode.HTML)
        
    try:
        resolved_chat = await client.get_chat(f_chat_id)
        chat_id = resolved_chat.id
    except ChannelInvalid:
        return await message.reply("❌ <b>Private channel/group detected! Make me an administrator there to index files.</b>", parse_mode=enums.ParseMode.HTML)
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("❌ <b>Invalid link or username specified!</b>", parse_mode=enums.ParseMode.HTML)
    except Exception as err:
        return await message.reply(f"❌ <b>Error occurred:</b> <code>{err}</code>", parse_mode=enums.ParseMode.HTML)

    status_message = await message.reply(
        "⏳ <b>Batch Link Generation Initiated...</b>\n"
        "<i>This may take a moment depending on the number of messages.</i>",
        parse_mode=enums.ParseMode.HTML
    )
    
    # If the chat belongs to dedicated file store channels
    if chat_id in FILE_STORE_CHANNEL:
        string_payload = f"{f_msg_id}_{l_msg_id}_{chat_id}_{command_prefix.lower().strip()}"
        encoded_base64 = base64.urlsafe_b64encode(string_payload.encode("ascii")).decode().strip("=")
        return await status_message.edit_text(
            f"✅ <b>Batch Link Generated Successfully!</b>\n\n"
            f"<code>https://t.me/{temp.U_NAME}?start=DSTORE-{encoded_base64}</code>",
            parse_mode=enums.ParseMode.HTML
        )

    progress_format = (
        "📊 <b>Batch Processing in Progress...</b>\n\n"
        "📦 <b>Total Messages:</b> <code>{total}</code>\n"
        "✅ <b>Processed:</b> <code>{current}</code>\n"
        "⏳ <b>Remaining:</b> <code>{rem}</code>\n"
        "⚙️ <b>Status:</b> <code>{sts}</code>"
    )

    extracted_media_list = []
    valid_message_count = 0
    total_messages_range = l_msg_id - f_msg_id

    async for msg in client.iter_messages(f_chat_id, l_msg_id, f_msg_id):
        valid_message_count += 1
        if msg.empty or msg.service or not msg.media:
            continue
            
        try:
            file_type = msg.media
            media_file = getattr(msg, file_type)
            file_caption = getattr(msg, 'caption', '')
            if file_caption:
                file_caption = file_caption.html
                
            if media_file:
                file_metadata = {
                    "file_id": media_file.file_id,
                    "caption": file_caption,
                    "title": getattr(media_file, "file_name", ""),
                    "size": media_file.file_size,
                    "protect": command_prefix.lower().strip() == "/pbatch",
                }
                og_msg_counter = len(extracted_media_list) + 1
                extracted_media_list.append(file_metadata)
        except Exception:
            pass
            
        if valid_message_count % 20 == 0:
            try:
                remaining_count = total_messages_range - valid_message_count
                await status_message.edit_text(
                    progress_format.format(
                        total=total_messages_range,
                        current=valid_message_count,
                        rem=max(0, remaining_count),
                        sts="Archiving Messages..."
                    ),
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass

    temp_json_filename = f"batchmode_{message.from_user.id}.json"
    
    with open(temp_json_filename, "w+", encoding="utf-8") as json_file:
        json.dump(extracted_media_list, json_file)
        
    try:
        log_post = await client.send_document(
            LOG_CHANNEL,
            temp_json_filename,
            file_name="Batch_Payload.json",
            caption="⚠️ <b>Generated batch payload for file store system.</b>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as err:
        logger.error(f"Failed to upload batch JSON to log channel: {err}")
        if os.path.exists(temp_json_filename):
            os.remove(temp_json_filename)
        return await status_message.edit_text("❌ <b>Failed to upload batch payload to log channel.</b>", parse_mode=enums.ParseMode.HTML)
        
    if os.path.exists(temp_json_filename):
        os.remove(temp_json_filename)
        
    file_id_packed, _ = unpack_new_file_id(log_post.document.file_id)
    
    completion_text = (
        f"✅ <b>Batch Link Generated Successfully!</b>\n\n"
        f"📦 <b>Total Files Contained:</b> <code>{len(extracted_media_list)}</code>\n\n"
        f"🔗 <b>Shareable Link:</b>\n"
        f"<code>https://t.me/{temp.U_NAME}?start=BATCH-{file_id_packed}</code>"
    )
    
    await status_message.edit_text(completion_text, parse_mode=enums.ParseMode.HTML)
