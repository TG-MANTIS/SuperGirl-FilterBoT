"""
Users and Chats Database Module
Handles asynchronous MongoDB operations for user registrations, ban states,
group chat statuses, settings configurations, and database statistics.
"""

import motor.motor_asyncio
from info import (
    DATABASE_NAME, DATABASE_URI, IMDB, IMDB_TEMPLATE, 
    MELCOW_NEW_USERS, P_TTI_SHOW_OFF, SINGLE_BUTTON, 
    SPELL_CHECK_REPLY, PROTECT_CONTENT
)

class Database:
    """
    Manages users and chats collections using Motor async driver.
    """
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups

    def new_user(self, id, name):
        """
        Generates a new user document dictionary.
        """
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )

    def new_group(self, id, title):
        """
        Generates a new group document dictionary.
        """
        return dict(
            id=id,
            title=title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )
    
    async def add_user(self, id, name):
        """
        Adds a new user to the database.
        """
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        """
        Checks if a user exists in the database.
        """
        user = await self.col.find_one({'id': int(id)})
        return bool(user)
    
    async def total_users_count(self):
        """
        Returns the total count of registered users.
        """
        count = await self.col.count_documents({})
        return count
    
    async def remove_ban(self, id):
        """
        Removes ban status from a user.
        """
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        """
        Bans a user with a specified reason.
        """
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        """
        Retrieves the ban status of a user.
        """
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id': int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        """
        Returns a cursor for all users.
        """
        return self.col.find({})
    
    async def delete_user(self, user_id):
        """
        Deletes a user from the database.
        """
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        """
        Retrieves lists of banned user IDs and disabled chat IDs.
        """
        users = self.col.find({'ban_status.is_banned': True})
        chats = self.grp.find({'chat_status.is_disabled': True})
        b_chats = [chat['id'] async for chat in chats]
        b_users = [user['id'] async for user in users]
        return b_users, b_chats

    async def add_chat(self, chat, title):
        """
        Adds a new group chat to the database.
        """
        chat_doc = self.new_group(chat, title)
        await self.grp.insert_one(chat_doc)
    
    async def get_chat(self, chat):
        """
        Retrieves chat status for a specific group.
        """
        chat_doc = await self.grp.find_one({'id': int(chat)})
        return False if not chat_doc else chat_doc.get('chat_status')
    
    async def re_enable_chat(self, id):
        """
        Re-enables a disabled group chat.
        """
        chat_status = dict(
            is_disabled=False,
            reason="",
        )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
        
    async def update_settings(self, id, settings):
        """
        Updates settings for a specific group chat.
        """
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})
    
    async def get_settings(self, id):
        """
        Retrieves settings for a group chat, falling back to defaults if not set.
        """
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'goodbye': False,
            'forcesub': True,
            'template': IMDB_TEMPLATE
        }
        chat = await self.grp.find_one({'id': int(id)})
        if chat:
            return chat.get('settings', default)
        return default
    
    async def disable_chat(self, chat, reason="No Reason"):
        """
        Disables a group chat with a specified reason.
        """
        chat_status = dict(
            is_disabled=True,
            reason=reason,
        )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})
    
    async def total_chat_count(self):
        """
        Returns the total count of registered group chats.
        """
        count = await self.grp.count_documents({})
        return count
    
    async def get_all_chats(self):
        """
        Returns a cursor for all group chats.
        """
        return self.grp.find({})

    async def get_db_size(self):
        """
        Returns the data storage size of the database.
        """
        stats = await self.db.command("dbstats")
        return stats.get('dataSize', 0)


db = Database(DATABASE_URI, DATABASE_NAME)
