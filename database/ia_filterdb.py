import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_URI_2, DATABASE_URI_3, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --------------------------------------------------------------------------- #
#  Dynamic Multiple Database Initialization (1 to 3 Optional Databases)       #
# --------------------------------------------------------------------------- #

db_uris = [DATABASE_URI]
if DATABASE_URI_2:
    db_uris.append(DATABASE_URI_2)
if DATABASE_URI_3:
    db_uris.append(DATABASE_URI_3)

clients = []
dbs = []
instances = []

for idx, uri in enumerate(db_uris, start=1):
    if uri:
        try:
            client_inst = AsyncIOMotorClient(uri)
            db_inst = client_inst[DATABASE_NAME]
            instance_inst = Instance.from_db(db_inst)
            clients.append(client_inst)
            dbs.append(db_inst)
            instances.append(instance_inst)
            logger.info(f"Database {idx} connected successfully!")
        except Exception as e:
            logger.error(f"Failed to connect Database {idx}: {e}")

# Fallback primary client/db if list is somehow empty
db = dbs[0] if dbs else None
instance = instances[0] if instances else None

# Register Media model for all connected database instances
media_classes = []
for inst in instances:
    @inst.register
    class Media(Document):
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
    media_classes.append(Media)


async def save_file(media):
    """Save file in database across multiple available URIs dynamically"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    
    success = False
    status_code = 2
    
    # Try saving in each available database instance sequentially
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
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to Database {idx}')
            return True, 1
        except DuplicateKeyError:
            logger.warning(f'{getattr(media, "file_name", "NO_FILE")} is already saved in Database {idx}')
            return False, 0
        except Exception as e:
            # If db is full or storage limit reached, try next database if available
            logger.warning(f'Could not save in Database {idx} (might be full/error): {e}. Trying next...')
            continue

    return success, status_code


async def get_search_results(query, file_type=None, max_results=7, offset=0, filter=False):
    """For given query return results combined from all connected databases"""

    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], '', 0

    if USE_CAPTION_FILTER:
        query_filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        query_filter = {'file_name': regex}

    if file_type:
        query_filter['file_type'] = file_type

    all_files = []
    total_results = 0

    # Aggregate results from all active database instances
    for idx, MediaModel in enumerate(media_classes, start=1):
        try:
            count = await MediaModel.count_documents(query_filter)
            total_results += count
            
            cursor = MediaModel.find(query_filter)
            cursor.sort('$natural', -1)
            files = await cursor.to_list(length=100) # Fetch recent matching files from each db
            all_files.extend(files)
        except Exception as e:
            logger.error(f"Error searching in Database {idx}: {e}")

    # Sort combined results by natural order (recent first)
    all_files.sort(key=lambda x: str(getattr(x, 'file_id', '')), reverse=True)

    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''

    # Apply pagination slice on combined results
    paginated_files = all_files[offset:offset + max_results]

    return paginated_files, next_offset, total_results


async def get_file_details(query):
    """Find file details across all connected database instances"""
    filter_query = {'file_id': query}
    for MediaModel in media_classes:
        try:
            cursor = MediaModel.find(filter_query)
            filedetails = await cursor.to_list(length=1)
            if filedetails:
                return filedetails
        except Exception:
            continue
    return []


async def get_databases_stats():
    """Get individual file count and storage size for each connected database"""
    stats = []
    for idx, (MediaModel, db_inst) in enumerate(zip(media_classes, dbs), start=1):
        try:
            count = await MediaModel.count_documents({})
            db_stats = await db_inst.command("dbStats")
            storage_size = db_stats.get("dataSize", 0)
            stats.append({
                "db_index": idx,
                "count": count,
                "size": storage_size
            })
        except Exception as e:
            logger.error(f"Error fetching stats for Database {idx}: {e}")
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
    """Return file_id, file_ref"""
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
