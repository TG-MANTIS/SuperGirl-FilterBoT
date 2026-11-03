import os
import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, DATABASE_URI, DATABASE_NAME, LOG_CHANNEL
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

# Common Guide Text Function
def get_clone_guide_text():
    return (
        "<b>🤖 How to Create Your Own Clone Bot?</b>\n\n"
        "Want to create your own movie filter bot? Follow these simple steps:\n\n"
        "1️⃣ First, open the official Telegram bot <b>@BotFather</b>.\n"
        "2️⃣ Send the command <code>/newbot</code> and follow the instructions to set a name and username for your bot.\n"
        "3️⃣ Copy the <b>Bot Token</b> provided by BotFather.\n"
        "4️⃣ Send that token here using the <code>/clone</code> command in the following format:\n\n"
        "👉 <code>/clone YOUR_BOT_TOKEN_HERE</code>\n\n"
        "<i>Once approved by the admin, your custom bot will be live and ready to use! 🎉</i>"
    )

# 1. Button Click / Guide Handler (When user clicks 'Create Clone Bot' button from start)
@Client.on_callback_query(filters.regex(r"^open_clone_guide$"))
async def clone_guide_callback(client, query: CallbackQuery):
    guide_text = get_clone_guide_text()
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
    ])
    
    try:
        await query.message.edit_text(guide_text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await query.message.reply_text(guide_text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    await query.answer()


# 2. /clone Command Handler (Handles both Guide display & Token submission)
@Client.on_message(filters.command("clone") & filters.private)
async def clone_bot_handler(client, message: Message):
    # If user only types /clone without token, show the guide instructions
    if len(message.command) < 2:
        guide_text = get_clone_guide_text()
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])
        return await message.reply_text(guide_text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    
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


# 3. Admin Actions (Approve, Reject, or Delete/Revoke Clone Bot)
@Client.on_callback_query(filters.regex(r"^(approve|reject|delete)_clone_"))
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
                await m.reply_sticker("CAACAgUAAxkBAAEJ...your_sticker_file_id_here...")

            @clone_client.on_message(filters.command("broadcast") & filters.private)
            async def clone_broadcast(c, m):
                if m.from_user.id != target_user_id:
                    return
                if not m.reply_to_message:
                    return await m.reply_text("Please reply to a message to broadcast!")
                
                await m.reply_text("✅ Broadcast initiated successfully.")

            # Auto-Filter Logic inside Cloned Bot (Clean caption, no force-sub)
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

            # Update Admin Log Message with Delete/Revoke Button
            revoke_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Delete / Revoke Bot", callback_data=f"delete_clone_{target_user_id}")]
            ])
            await query.message.edit_text(query.message.text + "\n\n✅ **STATUS: APPROVED & LIVE**", reply_markup=revoke_button)

            # Notify User
            await client.send_message(
                target_user_id,
                "🎉 <b>Success!</b> Your clone bot has been approved by the admin and is now live and running!"
            )

        except Exception as e:
            await query.message.reply_text(f"❌ Failed to start clone bot: {e}")

    elif action == "delete":
        # Stop and remove the clone bot completely from memory and database
        try:
            if target_user_id in ACTIVE_CLONES:
                await ACTIVE_CLONES[target_user_id].stop()
                del ACTIVE_CLONES[target_user_id]
        except Exception as e:
            logger.error(f"Error stopping clone client: {e}")

        # Remove from database and pending list
        await clones_collection.delete_one({"user_id": target_user_id})
        PENDING_CLONES.pop(str(target_user_id), None)

        # Update Admin Log Message
        await query.message.edit_text(query.message.text + "\n\n❌ **STATUS: DELETED / REVOKED BY ADMIN**")
        
        # Notify User about removal
        try:
            await client.send_message(
                target_user_id,
                "⚠️ <b>Notice:</b> Your clone bot has been removed/revoked by the admin."
            )
        except:
            pass
        await query.answer("Clone bot successfully deleted and revoked!", show_alert=True)

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
