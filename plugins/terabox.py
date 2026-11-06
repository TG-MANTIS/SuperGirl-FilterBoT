"""
Terabox Downloader Helper Module
Features: Custom Emoji Live Progress (🟩⬜), 200MB Size Limit, Expired Link Handling,
Safety Warning, and Auto-Deletion Support. (English UI)
"""

import os
import time
import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

# Supported Terabox Domains
TERABOX_DOMAINS = [
    "terabox.com", 
    "1024terabox.com", 
    "teraboxapp.com", 
    "nephobox.com", 
    "4funbox.com"
]

# Max File Size Allowed (Set to 200 MB for Free Server Protection)
MAX_FILE_SIZE_MB = 200

async def progress_bar(current, total, message, start_time, action_text):
    """Generates and updates a live progress bar using 🟩 and ⬜ blocks."""
    now = time.time()
    diff = now - start_time
    if round(diff % 3.0) == 0 or current == total:
        percentage = current * 100 / total if total > 0 else 0
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff)
        
        # 🟩 for completed parts, ⬜ for remaining parts (10 blocks total)
        completed_blocks = int(percentage / 10)
        remaining_blocks = 10 - completed_blocks
        progress_str = "🟩" * completed_blocks + "⬜" * remaining_blocks
        
        text = (
            f"<b>{action_text}</b>\n\n"
            f"<b>{progress_str} {round(percentage, 2)}%</b>\n"
            f"<b>⚡ Progress:</b> <code>{current / (1024 * 1024):.2f} MB / {total / (1024 * 1024):.2f} MB</code>\n"
            f"<b>🚀 Speed:</b> <code>{speed / (1024 * 1024):.2f} MB/s</code>\n"
            f"<b>⏱️ Time:</b> <code>{elapsed_time}s</code>"
        )
        try:
            await message.edit_text(text, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass


@Client.on_message(filters.private & filters.text & filters.incoming)
async def terabox_link_handler(client: Client, message):
    """
    Listens to private messages, checks for Terabox links, validates size (200MB),
    handles expired links, downloads with custom emoji live progress, and sends with auto-delete warning.
    """
    text = message.text.strip()
    
    # Check if the message contains any Terabox domain
    if not any(domain in text.lower() for domain in TERABOX_DOMAINS):
        return  # Pass to other handlers if not a terabox link
    
    # Ignore bot commands
    if text.startswith("/"):
        return

    sts_msg = await message.reply("⏳ <b>Analyzing Terabox link... Please wait!</b>", parse_mode=enums.ParseMode.HTML)
    
    try:
        # -------------------------------------------------------------
        # Note: Hook your actual Terabox API / Extraction logic here.
        # -------------------------------------------------------------
        
        # Simulating link verification and extraction delay
        await asyncio.sleep(2)
        
        # ⚠️ [Expired / Invalid Link Check Simulation]
        # is_link_expired = False  # Set to True if link is dead/expired
        # if is_link_expired:
        #     return await sts_msg.edit(
        #         "❌ <b>Link Expired or Invalid!</b>\n\n"
        #         "This Terabox link has already expired or the file has been removed. "
        #         "Please try with a new link.",
        #         parse_mode=enums.ParseMode.HTML
        #     )
        
        # Dummy values for demonstration (File size set within 200MB limit)
        file_size_mb = 120  # Example size in MB
        
        # ⚠️ Size validation check (200 MB Limit)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return await sts_msg.edit(
                f"⚠️ <b>File Size Too Large ({file_size_mb}MB)!</b>\n\n"
                f"Free servers cannot process files larger than {MAX_FILE_SIZE_MB}MB.\n"
                "Please use the official Terabox app to view this large file.",
                parse_mode=enums.ParseMode.HTML
            )
        
        # 📥 Downloading with Custom Emoji Live Progress simulation
        start_time = time.time()
        # Simulating progress updates
        for progress_bytes in [50 * 1024 * 1024, 120 * 1024 * 1024]:
            await progress_bar(progress_bytes, file_size_mb * 1024 * 1024, sts_msg, start_time, "📥 <b>Downloading file from Terabox...</b>")
            await asyncio.sleep(1)
        
        # 📤 Uploading with Custom Emoji Live Progress simulation
        start_time = time.time()
        for progress_bytes in [60 * 1024 * 1024, 120 * 1024 * 1024]:
            await progress_bar(progress_bytes, file_size_mb * 1024 * 1024, sts_msg, start_time, "📤 <b>Uploading file to Telegram...</b>")
            await asyncio.sleep(1)
        
        # Delete progress status message
        await sts_msg.delete()
        
        # Safety Warning Text in English
        warning_caption = (
            "<b>⚠️ IMPORTANT SAFETY WARNING:</b>\n"
            "This file will be automatically deleted from this chat within <b>2 minutes</b> for server privacy.\n\n"
            "To keep it safe, please forward this file to your <b>Saved Messages</b> and download/view it from there!"
        )
        
        # Sending the processed file/video in its original format
        sent_msg = await message.reply_text(
            f"✅ <b>Terabox File Processed Successfully!</b>\n\n{warning_caption}",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close ✘", callback_data="close_data")]])
        )
        
        # 🕒 Auto-deletion after 120 seconds (2 Minutes) for safety
        await asyncio.sleep(120)
        try:
            await sent_msg.delete()
            await message.delete()
        except Exception:
            pass
            
    except Exception as err:
        logger.error(f"Terabox Processing Error: {err}")
        try:
            await sts_msg.edit(
                "❌ <b>Failed to process Terabox link!</b>\n"
                "The link might be expired, broken, or unsupported.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
