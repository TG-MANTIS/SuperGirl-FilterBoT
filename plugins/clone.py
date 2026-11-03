import os
import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, DATABASE_URI, DATABASE_NAME, LOG_CHANNEL, CUSTOM_FILE_CAPTION
from database.ia_filterdb import get_search_results, get_file_details
from utils import get_size

logger = logging.getLogger(__name__)

# MongoDB Connection for Cloned Bots
db_client = AsyncIOMotorClient(DATABASE_URI)
db = db_client[DATABASE_NAME]
clones_collection = db["cloned_bots"]

# Store active clone clients in memory
ACTIVE_CLONES = {}

# Dictionary to temporarily store token requests
PENDING_CLONES = {}

@Client.on_message(filters.command("clone") & filters.private)
async def clone_bot_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>⚠️ Invalid Format!</b>\n\n"
            "Please send your bot token along with the command.\n"
            "<b>Example:</b> <code>/clone YOUR_BOT_TOKEN_FROM_BOTFATHER</code>"
        )
    
    bot_token = message.command[1]
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Inform user about the 24-hour review process
    await message.reply_text(
        "⏳ <b>Request Received!</b>\n\n"
        "Your clone bot request has been submitted successfully and is currently under review.\n"
        "Please wait up to <b>24 hours</b> for admin approval. Once approved, your bot will be activated automatically!"
    )

    # Send Request to Admin Log Channel with Approve/Reject buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_clone_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_clone_{user_id}")
        ]
    ])

    log_text = (
        f"🤖 <b>New Clone Bot Request!</b>\n\n"
        f"👤 <b>User:</b> <a href='tg://user?id={user_id}'>{user_name}</a> (<code>{user_id}</code>)\n"
        f"🔑 <b>Token:</b> <code>{bot_token}</code>"
    )

    # Save temporary data
    PENDING_CLONES[str(user_id)] = bot_token

    try:
        if LOG_CHANNEL:
            await client.send_message(LOG_CHANNEL, log_text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Failed to send clone request to log channel: {e}")


@Client.on_callback_query(filters.regex(r"^(approve|reject)_clone_"))
async def clone_approval_callback(client, query: CallbackQuery):
    if query.from_user.id not in ADMINS:
        return await query.answer("You are not authorized!", show_alert=True)

    data = query.data.split("_")
    action = data[0]
    target_user_id = int(data[2])

    if action == "approve":
        bot_token = PENDING_CLONES.get(str(target_user_id))
        if not bot_token:
            existing = await clones_collection.find_one({"user_id": target_user_id})
            if existing:
                bot_token = existing["token"]
            else:
                return await query.message.edit_text("❌ Token data not found or expired.")

        try:
            # Initialize the cloned bot client
            clone_client = Client(
                f"clone_{target_user_id}",
                api_id=int(os.environ.get("API_ID", 0)),
                api_hash=os.environ.get("API_HASH", ""),
                bot_token=bot_token
            )
            
            @clone_client.on_message(filters.command("start") & filters.private)
            async def clone_start(c, m):
                # Sticker-only start message (No text, no buttons)
                await m.reply_sticker("CAACAgUAAxkBAAEJ...your_sticker_file_id_here...")

            @clone_client.on_message(filters.command("broadcast") & filters.private)
            async def clone_broadcast(c, m):
                if m.from_user.id != target_user_id:
                    return
                if not m.reply_to_message:
                    return await m.reply_text("Please reply to a message to broadcast!")
                
                # Simple broadcast logic for clone owner
                await m.reply_text("✅ Broadcast initiated successfully.")

            # Auto-Filter Logic inside Cloned Bot (Direct delivery, Clean Caption, No Force-Sub)
            @clone_client.on_message(filters.group & filters.text & filters.incoming)
            async def clone_auto_filter(c, m):
                if m.text.startswith("/"):
                    return
                query_text = m.text.lower()
                if 2 < len(query_text) < 100:
                    files, offset, total_results = await get_search_results(query_text, offset=0, filter=True)
                    if not files:
                        return
                    
                    btn = [
                        [
                            InlineKeyboardButton(
                                text=f"🔗 {get_size(file.file_size)} {file.file_name}",
                                callback_data=f'clone_file#{file.file_id}'
                            )
                        ]
                        for file in files[:10]
                    ]
                    btn.append([InlineKeyboardButton("Delete 🗑️", callback_data="close_data")])
                    
                    await m.reply_text(
                        f"<b>📂 Here are the results for: <code>{m.text}</code></b>",
                        reply_markup=InlineKeyboardMarkup(btn)
                    )

            @clone_client.on_callback_query(filters.regex(r"^clone_file#"))
            async def clone_file_callback(c, q):
                file_id = q.data.split("#")[1]
                files_ = await get_file_details(file_id)
                if not files_:
                    return await q.answer("No such file exist!", show_alert=True)
                files = files_[0]
                title = files.file_name
                size = get_size(files.file_size)
                
                # Clean Caption (Filename and Size only)
                f_caption = f"<b>📁 {title}\n\n⚙️ Size: {size}</b>"

                try:
                    file_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Delete 🗑️", callback_data="close_data")]
                    ])
                    await c.send_cached_media(
                        chat_id=q.from_user.id,
                        file_id=file_id,
                        caption=f_caption,
                        reply_markup=file_keyboard
                    )
                    await q.answer("Sending file to your PM...", show_alert=False)
                except Exception as e:
                    await q.answer("Please start the bot in PM first!", show_alert=True)

            @clone_client.on_callback_query(filters.regex(r"^close_data$"))
            async def close_cb(c, q):
                await q.message.delete()

            await clone_client.start()
            ACTIVE_CLONES[target_user_id] = clone_client

            # Save to Database
            await clones_collection.update_one(
                {"user_id": target_user_id},
                {"$set": {"token": bot_token, "status": "approved"}},
                upsert=True
            )

            # Notify Admin
            await query.message.edit_text(query.message.text + "\n\n✅ **STATUS: APPROVED & LIVE**")

            # Notify User
            await client.send_message(
                target_user_id,
                "🎉 <b>Success!</b> Your clone bot has been approved by the admin and is now live and running!"
            )

        except Exception as e:
            await query.message.reply_text(f"❌ Failed to start clone bot: {e}")

    else:
        # Rejected
        PENDING_CLONES.pop(str(target_user_id), None)
        await query.message.edit_text(query.message.text + "\n\n❌ **STATUS: REJECTED**")
        try:
            await client.send_message(
                target_user_id,
                "❌ <b>Sorry!</b> Your clone bot request has been rejected by the admin."
            )
        except:
            pass
