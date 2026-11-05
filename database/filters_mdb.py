"""
Group Filters Management Module
Handles adding, finding, retrieving, deleting, and counting custom manual text filters
per group using MongoDB collections.
"""

import pymongo
from pyrogram import enums
from info import DATABASE_URI, DATABASE_NAME
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]


async def add_filter(grp_id, text, reply_text, btn, file, alert):
    """
    Adds or updates a custom text filter for a specific group.
    """
    mycol = mydb[str(grp_id)]
    
    data = {
        'text': str(text),
        'reply': str(reply_text),
        'btn': str(btn),
        'file': str(file),
        'alert': str(alert)
    }

    try:
        mycol.update_one({'text': str(text)}, {"$set": data}, upsert=True)
    except Exception:
        logger.exception('Some error occurred while adding filter!', exc_info=True)
             
     
async def find_filter(group_id, name):
    """
    Finds and returns filter details for a given keyword in a group.
    """
    mycol = mydb[str(group_id)]
    query = mycol.find({"text": name})
    
    try:
        reply_text, btn, fileid, alert = None, None, None, None
        for file in query:
            reply_text = file.get('reply')
            btn = file.get('btn')
            fileid = file.get('file')
            alert = file.get('alert', None)
        return reply_text, btn, alert, fileid
    except Exception:
        return None, None, None, None


async def get_filters(group_id):
    """
    Retrieves all filter keywords configured for a group.
    """
    mycol = mydb[str(group_id)]
    texts = []
    
    try:
        query = mycol.find()
        for file in query:
            text = file.get('text')
            if text:
                texts.append(text)
    except Exception:
        pass
    return texts


async def delete_filter(message, text, group_id):
    """
    Deletes a specific filter keyword from a group collection.
    """
    mycol = mydb[str(group_id)]
    myquery = {'text': text}
    query_count = mycol.count_documents(myquery)
    
    if query_count == 1:
        mycol.delete_one(myquery)
        await message.reply_text(
            f"<b>✅ Filter '<code>{text}</code>' successfully deleted.</b>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text("<b>❌ Could not find that filter!</b>", quote=True, parse_mode=enums.ParseMode.HTML)


async def del_all(message, group_id, title):
    """
    Drops the entire filter collection for a group.
    """
    if str(group_id) not in mydb.list_collection_names():
        await message.edit_text(f"<b>⚠️ No filters found to remove in <b>{title}</b>!</b>", parse_mode=enums.ParseMode.HTML)
        return

    mycol = mydb[str(group_id)]
    try:
        mycol.drop()
        await message.edit_text(f"<b>✅ All filters have been successfully removed from <b>{title}</b>!</b>", parse_mode=enums.ParseMode.HTML)
    except Exception:
        await message.edit_text("<b>❌ An error occurred while clearing filters!</b>", parse_mode=enums.ParseMode.HTML)
        return


async def count_filters(group_id):
    """
    Counts total filters present in a group collection.
    """
    mycol = mydb[str(group_id)]
    try:
        count = mycol.count_documents({})
        return count if count > 0 else False
    except Exception:
        return False


async def filter_stats():
    """
    Calculates total collections and total filters across all groups.
    """
    collections = mydb.list_collection_names()

    if "CONNECTION" in collections:
        collections.remove("CONNECTION")
    if "user_db_mappings" in collections:
        collections.remove("user_db_mappings")

    totalcount = 0
    for collection in collections:
        mycol = mydb[collection]
        try:
            count = mycol.count_documents({})
            totalcount += count
        except Exception:
            pass

    totalcollections = len(collections)
    return totalcollections, totalcount
