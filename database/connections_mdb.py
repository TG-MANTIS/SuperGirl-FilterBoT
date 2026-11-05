"""
Database Connections Management Module
Handles user-to-group connection mappings, active group states, 
retrieval of all connected groups, and connection deletions using MongoDB.
"""

import pymongo
from info import DATABASE_URI, DATABASE_NAME
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]
mycol = mydb['CONNECTION']


async def add_connection(group_id, user_id):
    """
    Adds a new group connection for a specific user.
    """
    query = mycol.find_one(
        { "_id": user_id },
        { "_id": 0, "active_group": 0 }
    )
    if query is not None:
        group_ids = [x["group_id"] for x in query["group_details"]]
        if group_id in group_ids:
            return False

    group_details = {
        "group_id": group_id
    }

    data = {
        '_id': user_id,
        'group_details': [group_details],
        'active_group': group_id,
    }

    if mycol.count_documents({"_id": user_id}) == 0:
        try:
            mycol.insert_one(data)
            return True
        except Exception:
            logger.exception('Some error occurred while adding connection!', exc_info=True)
    else:
        try:
            mycol.update_one(
                {'_id': user_id},
                {
                    "$push": {"group_details": group_details},
                    "$set": {"active_group": group_id}
                }
            )
            return True
        except Exception:
            logger.exception('Some error occurred while updating connection!', exc_info=True)


async def active_connection(user_id):
    """
    Retrieves the currently active group ID for a user.
    """
    query = mycol.find_one(
        { "_id": user_id },
        { "_id": 0, "group_details": 0 }
    )
    if not query:
        return None

    group_id = query.get('active_group')
    return int(group_id) if group_id is not None else None


async def all_connections(user_id):
    """
    Retrieves a list of all connected group IDs for a user.
    """
    query = mycol.find_one(
        { "_id": user_id },
        { "_id": 0, "active_group": 0 }
    )
    if query is not None:
        return [x["group_id"] for x in query["group_details"]]
    else:
        return None


async def if_active(user_id, group_id):
    """
    Checks if a specific group is currently active for a user.
    """
    query = mycol.find_one(
        { "_id": user_id },
        { "_id": 0, "group_details": 0 }
    )
    return query is not None and query.get('active_group') == group_id


async def make_active(user_id, group_id):
    """
    Sets a specific group as the active connection for a user.
    """
    update = mycol.update_one(
        {'_id': user_id},
        {"$set": {"active_group": group_id}}
    )
    return update.modified_count != 0


async def make_inactive(user_id):
    """
    Clears the active group connection for a user.
    """
    update = mycol.update_one(
        {'_id': user_id},
        {"$set": {"active_group": None}}
    )
    return update.modified_count != 0


async def delete_connection(user_id, group_id):
    """
    Deletes a group connection from a user's profile and manages active group fallback.
    """
    try:
        update = mycol.update_one(
            {"_id": user_id},
            {"$pull": {"group_details": {"group_id": group_id}}}
        )
        if update.modified_count == 0:
            return False
            
        query = mycol.find_one(
            { "_id": user_id },
            { "_id": 0 }
        )
        
        if query and len(query.get("group_details", [])) >= 1:
            if query.get('active_group') == group_id:
                group_list = query["group_details"]
                prvs_group_id = group_list[len(group_list) - 1]["group_id"]

                mycol.update_one(
                    {'_id': user_id},
                    {"$set": {"active_group": prvs_group_id}}
                )
        else:
            mycol.update_one(
                {'_id': user_id},
                {"$set": {"active_group": None}}
            )
        return True
    except Exception as e:
        logger.exception(f'Some error occurred while deleting connection! {e}', exc_info=True)
        return False
