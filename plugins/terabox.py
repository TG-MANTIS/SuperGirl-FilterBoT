"""
Independent Terabox Downloader Plugin Module
Handles Terabox links in private chats, downloads media within size limits,
and sends them back to users with professional status updates and safety instructions.
"""

import os
import time
import asyncio
import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Supported Terabox Domains
TERABOX_DOMAINS = [
    "terabox.com",
    "1024terabox.com",
    "teraboxapp.com",
    "nephobox.com",
    "4funbox.com",
    "mirrobox.com",
    "freeterabox.com"
]

# File size limit (200MB tailored for free-tier hosting like Render)
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB in bytes
DOWNLOAD_DIRECTORY = "downloads/"

# Ensure download directory exists
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

def is_terabox_link(text: str) -> bool:
    """Checks if the given text contains any valid Terabox domain link."""
    if not text:
        return False
    return any(domain in text.lower() for domain in TERABOX_DOMAINS)

async def progress_bar(current, total, message, start_time, action_text="Downloading"):
    """Generates and updates a live progress bar for downloading/uploading."""
    now = time.time()
    diff = now - start_time
    if round(diff % 3.0) == 0 or current == total:
        percentage = current * 100 / total if total > 0 else 0
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff)
        
        filled_blocks = int(percentage // 10)
        bar = "🟩" * filled_blocks + "⬜" * (10 - filled_blocks)
        
        progress_str = (
            f"<b>📥 {action_text} Terabox Content...</b>\n\n"
            f"[{bar}] <b>{percentage:.1f}%</b>\n\n"
            f"<b>📁 Done:</b> {current / (1024 * 1024):.2f} MB / {total / (1024 * 1024):.2f} MB\n"
            f"<b>⚡ Speed:</b> {speed / (1024 * 1024):.2f} MB/s\n"
            f"<b>⏱️ Time:</b> {elapsed_time}s"
        )
        try:
            await message.edit_text(progress_str, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass

# 'group=-1' ensures this intercepts links before other primary filters
@Client.on_message(filters.private & filters.text & ~filters.command(["start", "help", "font"]), group=-1)
async def terabox_private_handler(client: Client, message):
    """Intercepts private messages, detects Terabox links, and processes them entirely."""
    user_text = message.text.strip()
    
    # Check if the message contains a Terabox link
    if not is_terabox_link(user_text):
        return  # Ignore non-terabox texts so other filters work normally

    # Send initial status message
    status_msg = await message.reply_text(
        "<b>🔍 Analyzing Terabox link... Please wait.</b>",
        parse_mode=enums.ParseMode.HTML
    )

    file_path = None
    try:
        await asyncio.sleep(1)
        await status_msg.edit_text(
            "<b>⚙️ Processing media content from Terabox...</b>",
            parse_mode=enums.ParseMode.HTML
        )
        
        # =========================================================================
        # 🛠️ TERABOX LINK EXTRACTION LOGIC
        # ഇവിടെ താങ്കൾ ടെറാബോക്സ് ലിങ്ക് അയക്കുമ്പോൾ അതിനുള്ളിലെ ഡയറക്ട് ഫയൽ URL 
        # (Direct Download Link) എടുത്തു തരുന്ന API അല്ലെങ്കിൽ കോഡ് നൽകേണ്ടതുണ്ട്.
        # =========================================================================
        
        # ഉദാഹരണത്തിന്:
        # direct_media_url = await get_direct_terabox_link(user_text)
        direct_media_url = None  # നിലവിൽ ഇത് പ്ലേസ്‌ഹോൾഡർ ആണ്
        
        if not direct_media_url:
            # താങ്കൾ API അല്ലെങ്കിൽ സ്ക്രാപ്പിംഗ് മെത്തേഡ് സെറ്റ് ചെയ്യുന്നതുവരെ 
            # യൂസർക്ക് മനസ്സിലാകാൻ ഒരു ചെറിയ നോട്ടീസ് നൽകാം:
            await status_msg.edit_text(
                "<b>⚠️ Terabox Direct Link API is not configured yet.</b>\n\n"
                "<i>Please add your Terabox extraction API or scraping logic into the plugin code!</i>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        # 📥 Downloading the file using aiohttp
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_media_url) as resp:
                if resp.status == 200:
                    file_path = os.path.join(DOWNLOAD_DIRECTORY, f"terabox_{message.from_user.id}.mp4")
                    total_size = int(resp.headers.get("Content-Length", 0))
                    
                    if total_size > MAX_FILE_SIZE:
                        await status_msg.edit_text(
                            "<b>❌ File size exceeds the 200MB limit for free-tier hosting!</b>",
                            parse_mode=enums.ParseMode.HTML
                        )
                        return

                    downloaded = 0
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            await progress_bar(downloaded, total_size, status_msg, start_time, "Downloading")

        # 📤 Uploading media back to the user
        if file_path and os.path.exists(file_path):
            await status_msg.edit_text("<b>📤 Uploading file to Telegram...</b>", parse_mode=enums.ParseMode.HTML)
            upload_start_time = time.time()
            
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=(
                    f"<b>📚 Terabox Downloaded Content</b>\n\n"
                    f"<i>💡 Note: Please do not try to watch or download this file directly here. "
                    f"Instead, please forward this file to your Saved Messages, and then you can safely watch or download it from there!</i>\n\n"
                    f"<b>[©️𝐓𝐞𝐚𝐦 𝐂𝐢𝐧𝐞𝐦𝐚 𝐅𝐢𝐥𝐱™️](https://t.me/+iEbhY7mM4oE1OTVl)</b>"
                ),
                parse_mode=enums.ParseMode.HTML,
                progress=progress_bar,
                progress_args=(status_msg, upload_start_time, "Uploading")
            )
            await status_msg.delete()

    except Exception as err:
        await status_msg.edit_text(
            f"<b>❌ Failed to process Terabox link.</b>\n\n<i>Error: {str(err)}</i>",
            parse_mode=enums.ParseMode.HTML
        )
    finally:
        # Clean up local file after sending
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
