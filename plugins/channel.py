"""
Core Channel Media Indexing Module
Automatically captures incoming documents, videos, and audio files from 
configured source channels and securely indexes them into the database.
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from info import CHANNELS
from database.ia_filterdb import save_file

logger = logging.getLogger(__name__)

# Media filter supporting documents, videos, and audio files
MEDIA_TYPES_FILTER = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(CHANNELS) & MEDIA_TYPES_FILTER)
async def incoming_channel_media_handler(client: Client, message: Message):
    """
    Listens to designated source channels, extracts media payloads,
    and indexes them into the database for auto-filtering.
    """
    target_media = None
    detected_media_type = None

    # Iterate through supported media types to extract the active object
    for media_category in ("document", "video", "audio"):
        media_object = getattr(message, media_category, None)
        if media_object is not None:
            target_media = media_object
            detected_media_type = media_category
            break

    if not target_media:
        return

    try:
        # Attach required attributes for database storage mapping
        target_media.file_type = detected_media_type
        target_media.caption = message.caption

        # Save/Index the media file into the filter database
        await save_file(target_media)
        logger.debug(f"Successfully indexed {detected_media_type} from channel ID: {message.chat.id}")

    except Exception as err:
        logger.error(f"Failed to index incoming media file from channel {message.chat.id}: {err}", exc_info=True)
