"""
Interactive Filter Database Module
Manages multi-database asynchronous connections (Main and Paid pools),
umongo document models, file indexing, saving, searching, and file details retrieval.
"""

import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import (
    DATABASE_URI, DATABASE_URI_2, DATABASE_URI_3, 
    DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER,
    PAID_DB_1, PAID_DB_2, PAID_DB_3, PAID_DB_4, PAID_DB_5,
    PAID_DB_6, PAID_DB_7, PAID_DB_8, PAID_DB_9, PAID_DB_10
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
#  Dynamic Multiple Database Initialization (Main & Paid Pools)               #
# --------------------------------------------------------------------------- #

main_db_uris = [DATABASE_URI]
if DATABASE_URI_2:
    main_db_uris.append(DATABASE_URI_2)
if DATABASE_URI_3:
    main_db_uris.append(DATABASE_URI_3)

main_clients = []
main_dbs = []
main_instances = []

for idx, uri in enumerate(main_db_uris, start=1):
    if uri:
        try:
            client_inst = AsyncIOMotorClient(uri)
            db_inst = client_inst[DATABASE_NAME]
            instance_inst = Instance.from_db(db_inst)
            main_clients.append(client_inst)
            main_dbs.append(db_inst)
            main_instances.append(instance_inst)
            logger.info(f"Main Database {idx} connected successfully!")
        except Exception as err:
            logger.error(f"Failed to connect Main Database {idx}: {err}")

# Fallback primary client/db
db = main_dbs[0] if main_dbs else None
instance = main_instances[0] if main_instances else None

# Paid Database Pool Mapping (1 to 10)
paid_db_uris = {
    1: PAID_DB_1, 2: PAID_DB_2, 3: PAID_DB_3, 4: PAID_DB_4, 5: PAID_DB_5,
    6: PAID_DB_6, 7: PAID_DB_7, 8: PAID_DB_8, 9: PAID_DB_9, 10: PAID_DB_10
}

paid_clients_cache = {}
paid_dbs_cache = {}
paid_instances_cache = {}

def get_paid_db_instance(db_uri):
    """
    Dynamically retrieves or creates a connection for a Paid DB URI.
    """
    if not db_uri:
        return None, None, None
    if db_uri in paid_dbs_cache:
        return paid_clients_cache[db_uri], paid_dbs_cache[db_uri], paid_instances_cache[db_uri]
    
    try:
        client = AsyncIOMotorClient(db_uri)
        database = client[DATABASE_NAME]
        inst = Instance.from_db(database)
        
        paid_clients_cache[db_uri] = client
        paid_dbs_cache[db_uri] = database
        paid_instances_cache[db_uri] = inst
        logger.info("Successfully connected to a Paid Database slot!")
        return client, database, inst
    except Exception as err:
        logger.error(f"Failed to connect Paid Database URI: {err}")
        return None, None, None

# Register Media model for Main database instances
main_media_classes = []
for inst in main_instances:
    @inst.register
    class MainMedia(Document):
        file_id = fields.StrField(attribute='_id')
        file_ref = fields.StrField(allow_none=True)
        file_name = fields.StrField(required=True)
        file_size = fields.IntField(required=True)
        file_type = fields.StrField(allow_none=True)
        mime_type = fields.StrField(allow_none=True)
        caption = fields.StrField(allow_none=True)

        class Meta:
            indexes = ('$file_name', )
            collection_name = COLLECTION_NAME
    main_media_classes.append(MainMedia)


async def get_user_assigned_db_uri(user_id):
    """
    Fetches the assigned paid database URI for a specific user from the mapping collection.
    """
    if not db:
        return None
    try:
        mapping_col = db["user_db_mappings"]
        record = await mapping_col.find_one({"user_id": int(user_id)})
        if record and "db_uri" in record:
            return record["db_uri"]
    except Exception as err:
        logger.error(f"Error fetching DB mapping for user {user_id}: {err}")
    return None


async def get_media_model_for_user(user_id=None):
    """
    Returns the appropriate Media model and database instance based on user assignment.
    """
    if user_id:
        paid_uri = await get_user_assigned_db_uri(user_id)
        if paid_uri:
            _, paid_db, paid_inst = get_paid_db_instance(paid_uri)
            if paid_inst:
                class PaidMedia(Document):
                    file_id = fields.StrField(attribute='_id')
                    file_ref = fields.StrField(allow_none=True)
                    file_name = fields.StrField(required=True)
                    file_size = fields.IntField(required=True)
                    file_type = fields.StrField(allow_none=True)
                    mime_type = fields.StrField(allow_none=True)
                    caption = fields.StrField(allow_none=True)

                    class Meta:
                        indexes = ('$file_name', )
                        collection_name = COLLECTION_NAME
                
                try:
                    paid_inst.register(PaidMedia)
                except Exception:
                    pass
                return [PaidMedia], paid_db

    return main_media_classes, db


async def save_file(media, user_id=None):
    """
    Saves a media file into the appropriate database (Main DBs or User's Assigned Paid DB).
    """
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    
    media_classes, _ = await get_media_model_for_user(user_id)
    success = False
    status_code = 2
    
    for idx, MediaModel in enumerate(media_classes, start=1):
        try:
            file = MediaModel(
                file_id=file_id,
                file_ref=file_ref,
                file_name=file_name,
                file_size=media.file_size,
                file_type=media.file_type,
                mime_type=media.mime_type,
                caption=media.caption.html if media.caption else None,
            )
        except ValidationError:
            logger.exception(f'Error occurred while creating file model for DB {idx}')
            continue
        
        try:
            await file.commit()
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved successfully!')
            return True, 1
        except DuplicateKeyError:
            logger.warning(f'{getattr(media, "file_name", "NO_FILE")} is already saved in database.')
            return False, 0
        except Exception as err:
            logger.warning(f'Could not save file: {err}. Trying next...')
            continue

    return success, status_code


async def get_search_results(query, file_type=None, max_results=7, offset=0, filter=False, user_id=None):
    """
    Searches for media files matching the query across the appropriate database.
    """
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        return [], '', 0

    if USE_CAPTION_FILTER:
        query_filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        query_filter = {'file_name': regex}

    if file_type:
        query_filter['file_type'] = file_type

    media_classes, _ = await get_media_model_for_user(user_id)
    all_files = []
    total_results = 0

    for idx, MediaModel in enumerate(media_classes, start=1):
        try:
            count = await MediaModel.count_documents(query_filter)
            total_results += count
            
            cursor = MediaModel.find(query_filter)
            cursor.sort('$natural', -1)
            files = await cursor.to_list(length=100)
            all_files.extend(files)
        except Exception as err:
            logger.error(f"Error searching in database {idx}: {err}")

    all_files.sort(key=lambda x: str(getattr(x, 'file_id', '')), reverse=True)

    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''

    paginated_files = all_files[offset:offset + max_results]
    return paginated_files, next_offset, total_results


async def get_file_details(query, user_id=None):
    """
    Retrieves file details using file ID across active database instances.
    """
    filter_query = {'file_id': query}
    media_classes, _ = await get_media_model_for_user(user_id)
    for MediaModel in media_classes:
        try:
            cursor = MediaModel.find(filter_query)
            filedetails = await cursor.to_list(length=1)
            if filedetails:
                return filedetails
        except Exception:
            continue
    return []


async def get_databases_stats(user_id=None):
    """
    Retrieves individual file counts and storage size statistics.
    """
    stats = []
    media_classes, target_db = await get_media_model_for_user(user_id)
    for idx, MediaModel in enumerate(media_classes, start=1):
        try:
            count = await MediaModel.count_documents({})
            db_stats = await target_db.command("dbStats")
            storage_size = db_stats.get("dataSize", 0)
            stats.append({
                "db_index": idx,
                "count": count,
                "size": storage_size
            })
        except Exception as err:
            logger.error(f"Error fetching stats for DB {idx}: {err}")
            stats.append({
                "db_index": idx,
                "count": 0,
                "size": 0
            })
    return stats


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """
    Unpacks and decodes a Telegram file ID into file_id and file_ref strings.
    """
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

# --- Compatibility alias for other plugins expecting 'Media' ---
Media = main_media_classes[0] if main_media_classes else None
