"""
Core Inline Search Management Module
Handles inline queries from users, manages search results pagination,
subscription verification, and custom caption formatting.
"""

import logging
from pyrogram import Client, emoji, filters
from pyrogram.errors.exceptions.bad_request_400 import QueryIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument, InlineQuery
from database.ia_filterdb import get_search_results
from utils import is_subscribed, get_size, temp
from info import CACHE_TIME, AUTH_USERS, AUTH_CHANNEL, CUSTOM_FILE_CAPTION

logger = logging.getLogger(__name__)
cache_time = 0 if AUTH_USERS or AUTH_CHANNEL else CACHE_TIME

async def inline_users_filter(query: InlineQuery) -> bool:
    """
    Validates whether the user is authorized to perform inline searches.
    """
    if AUTH_USERS:
        if query.from_user and query.from_user.id in AUTH_USERS:
            return True
        else:
            return False
            
    if query.from_user and query.from_user.id not in temp.BANNED_USERS:
        return True
        
    return False


@Client.on_inline_query()
async def inline_search_handler(client: Client, query: InlineQuery):
    """
    Processes incoming inline queries, fetches matching files from database,
    and returns formatted cached document results with pagination support.
    """
    if not await inline_users_filter(query):
        return await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='Access Denied!',
            switch_pm_parameter="hehe"
        )

    if AUTH_CHANNEL and not await is_subscribed(client, query):
        return await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text='You have to subscribe my channel to use the bot!',
            switch_pm_parameter="subscribe"
        )

    search_query = query.query.strip()
    file_type = None

    if '|' in search_query:
        search_query, file_type = search_query.split('|', maxsplit=1)
        search_query = search_query.strip()
        file_type = file_type.strip().lower()

    offset = int(query.offset or 0)
    reply_markup = get_reply_markup(query=search_query)
    
    files, next_offset, total = await get_search_results(
        search_query,
        file_type=file_type,
        max_results=10,
        offset=offset
    )

    query_results = []

    for file in files:
        title = file.file_name
        size = get_size(file.file_size)
        f_caption = file.caption

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name='' if title is None else title,
                    file_size='' if size is None else size,
                    file_caption='' if f_caption is None else f_caption
                )
            except Exception as err:
                logger.exception(err)
                f_caption = f_caption

        if f_caption is None:
            f_caption = f"{file.file_name}"

        query_results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=f_caption,
                description=f'Size: {get_size(file.file_size)}\nType: {file.file_type}',
                reply_markup=reply_markup
            )
        )

    if query_results:
        switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
        if search_query:
            switch_pm_text += f" for {search_query}"
            
        try:
            await query.answer(
                results=query_results,
                is_personal=True,
                cache_time=cache_time,
                switch_pm_text=switch_pm_text,
                switch_pm_parameter="start",
                next_offset=str(next_offset)
            )
        except QueryIdInvalid:
            pass
        except Exception as err:
            logger.exception(str(err))
    else:
        switch_pm_text = f"{emoji.CROSS_MARK} No results"
        if search_query:
            switch_pm_text += f' for "{search_query}"'

        await query.answer(
            results=[],
            is_personal=True,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="okay"
        )


def get_reply_markup(query: str) -> InlineKeyboardMarkup:
    """
    Generates inline keyboard markup for quick re-searching.
    """
    buttons = [
        [
            InlineKeyboardButton('Search Again 🔍', switch_inline_query_current_chat=query)
        ]
    ]
    return InlineKeyboardMarkup(buttons)
