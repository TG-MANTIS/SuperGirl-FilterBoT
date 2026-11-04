import os
import logging
import asyncio
import re
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

# Regex pattern to match Telegram Bot Token (e.g. 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)
TOKEN_REGEX = re.compile(r'\d{8,10}:[a-zA-Z0-9_-]{35}')

# Common Guide Text Function
def get_clone_guide_text():
    return (
        "<b>🤖 How to Create Your Own Clone Bot?</b>\n\n"
        "Want to create your own movie filter bot? You can submit your bot token in <b>two easy ways</b>:\n\n"
        "1️⃣ **Forward Method (Easiest):** Simply forward the success message you received from <b>@BotFather</b> directly here!\n"
        "2️⃣ **Direct Method:** Or copy your Bot Token from @BotFather and send it here using the <code>/clone</code> command or directly.\n\n"
        "👉 <i>Example:</i> <code>/clone YOUR_BOT_TOKEN</code> (or just send the token/forward message directly)\n\n"
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


# Helper function to process token submission
async def process_token_submission(client, message: Message, text_to_check: str):
    match = TOKEN_REGEX.search(text_to_check)
    if not match:
        guide_text = get_clone_guide_text()
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])
        return await message.reply_text(
            "❌ <b>Invalid Bot Token found!</b> Please make sure you send a valid token or forward the correct message from @BotFather.\n\n" + guide_text,
            reply_markup=buttons,
            parse_mode=enums.ParseMode.HTML
        )
    
    bot_token = match.group(0)
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    await message.reply_text(
        "⏳ <b>Request Received!</b>\n\n"
        "Your clone bot request has been submitted successfully and is currently under review.\n"
        "Please wait up to <b>24 hours</b> for admin approval. Once approved, your bot will be activated automatically!"
    )

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

    PENDING_CLONES[str(user_id)] = bot_token

    try:
        if LOG_CHANNEL:
            await client.send_message(LOG_CHANNEL, log_text, reply_markup=buttons)
    except Exception as e:
        logger.error(f"Failed to send clone request to log channel: {e}")


# 2. /clone Command Handler
@Client.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(client, message: Message):
    if len(message.command) < 2:
        guide_text = get_clone_guide_text()
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])
        return await message.reply_text(guide_text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    
    await process_token_submission(client, message, message.text)


# 3. Direct Text / Forwarded Message Token Handler
@Client.on_message(filters.private & ~filters.command(["start", "clone", "help", "settings"]))
async def direct_token_handler(client, message: Message):
    text_content = message.text or message.caption or ""
    if TOKEN_REGEX.search(text_content):
        await process_token_submission(client, message, text_content)


# 4. Admin Actions (Approve, Reject, or Delete/Revoke Clone Bot)
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
            clone_client = Client(
                f"clone_{target_user_id}",
                api_id=int(os.environ.get("API_ID", 0)),
                api_hash=os.environ.get("API_HASH", ""),
                bot_token=bot_token
            )
            
            @clone_client.on_message(filters.command("start") & filters.private)
            async def clone_start(c, m):
                await m.reply_text("👋 Hello! I am your custom clone filter bot. Send me any movie name to search.")

            # Welcome Message Handler with Auto-Delete & Italic Deleted Notice
            @clone_client.on_message(filters.new_chat_members)
            async def welcome_new_member(c, m):
                for new_member in m.new_chat_members:
                    welcome_text = f"Hello {new_member.mention}, welcome to our group! ✨"
                    sent_msg = await m.reply_text(welcome_text)
                    await asyncio.sleep(3)
                    try:
                        await sent_msg.delete()
                        del_notice = await m.reply_text("_🗑️ This message was deleted_")
                        await asyncio.sleep(2)
                        await del_notice.delete()
                    except Exception:
                        pass

            # Auto-Filter Logic inside Cloned Bot with Admin Check & Smart Promotion
            @clone_client.on_message(filters.group & filters.text & filters.incoming)
            async def clone_auto_filter(c, m):
                if m.text.startswith("/"):
                    return
                
                # Check if bot is admin in this chat
                try:
                    bot_member = await c.get_chat_member(m.chat.id, (await c.get_me()).id)
                    is_admin = bot_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
                except Exception:
                    is_admin = True # Fallback if permission check fails

                # If bot is NOT admin, send Smart Promotion message and auto-delete after 4 seconds
                if not is_admin:
                    user_mention = m.from_user.mention if m.from_user else "User"
                    movie_name = m.text
                    
                    promo_text = (
                        f"Hello <b>{user_mention}</b>,\n\n"
                        f"I cannot provide the movie <b>\"{movie_name}\"</b> here because the group owner has <b>not made me an admin</b> in this group yet! ⚠️\n\n"
                        f"Don't worry! To get any movie instantly, please join our official main group below. It is 24/7 active and our main bot will give you any file you request!\n\n"
                        f"👉 Join Main Group: <b>@LutappiUpdates</b>"
                    )
                    buttons = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Join Main Movie Group", url="https://t.me/LutappiUpdates")]
                    ])
                    
                    promo_msg = await m.reply_text(promo_text, reply_markup=buttons)
                    await asyncio.sleep(4)
                    try:
                        await promo_msg.delete()
                        del_notice = await m.reply_text("_🗑️ This message was deleted_")
                        await asyncio.sleep(2)
                        await del_notice.delete()
                    except Exception:
                        pass
                    return

                # Normal Bot Functionality if Admin
                query_text = m.text.lower().strip()
                if 2 < len(query_text) < 100:
                    files, offset, total_results = await get_search_results(query_text, offset=0, filter=True)
                    
                    # Spelling Check / Suggestions if no results found
                    if not files:
                        alt_query = query_text.split()[0] if " " in query_text else query_text[:4]
                        alt_files, _, alt_total = await get_search_results(alt_query, offset=0, filter=True)
                        
                        if alt_files:
                            suggestions = []
                            seen = set()
                            for f in alt_files:
                                name = f.file_name
                                if name not in seen:
                                    seen.add(name)
                                    suggestions.append(name)
                                    if len(suggestions) >= 3:
                                        break
                            
                            sugg_btns = [
                                [InlineKeyboardButton(text=f"🎬 {sug}", callback_data=f'clone_file#{f.file_id}')]
                                for sug, f in zip(suggestions, alt_files[:3])
                            ]
                            sugg_btns.append([InlineKeyboardButton("Delete 🗑️", callback_data="close_data")])
                            
                            sugg_msg = await m.reply_text(
                                f"<b>❌ No results found for \"<code>{m.text}</code>\".\n👉 Did you mean one of these?</b>",
                                reply_markup=InlineKeyboardMarkup(sugg_btns)
                            )
                            asyncio.create_task(auto_delete_message(sugg_msg, 15))
                            return
                        else:
                            no_res_msg = await m.reply_text(
                                f"<b>❌ Sorry, no files found for \"<code>{m.text}</code>\"!\nPlease check the spelling or request an admin.</b>",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Delete 🗑️", callback_data="close_data")]])
                            )
                            asyncio.create_task(auto_delete_message(no_res_msg, 10))
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
                    
                    max_pages = (total_results + 9) // 10
                    
                    if total_results > 10:
                        btn.append([
                            InlineKeyboardButton("Delete 🗑️", callback_data="close_data"),
                            InlineKeyboardButton(f"1/{max_pages}", callback_data="pages"),
                            InlineKeyboardButton("NEXT ⏩", callback_data=f"clone_next_{query_text}_1")
                        ])
                    else:
                        btn.append([InlineKeyboardButton("Delete 🗑️", callback_data="close_data")])
                    
                    user_mention = m.from_user.mention if m.from_user else "User"
                    
                    res_msg = await m.reply_text(
                        f"<b>📂 Requested by: {user_mention}\n🎬 Results for: <code>{m.text}</code></b>",
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                    asyncio.create_task(auto_delete_message(res_msg, 300))

            # Helper function for background auto-deletion of messages
            async def auto_delete_message(message: Message, delay: int):
                await asyncio.sleep(delay)
                try:
                    await message.delete()
                except Exception:
                    pass

            # Pagination Next/Back Callback for Cloned Bots
            @clone_client.on_callback_query(filters.regex(r"^clone_(next|back)_"))
            async def clone_paginate_handler(c, q):
                data_parts = q.data.split("_")
                action = data_parts[1]
                query_text = data_parts[2]
                page = int(data_parts[3])
                
                offset = page * 10
                files, _, total_results = await get_search_results(query_text, offset=offset, filter=True)
                
                if not files:
                    return await q.answer("No more files found!", show_alert=True)
                
                btn = [
                    [
                        InlineKeyboardButton(
                            text=f"🔗 {get_size(file.file_size)} {file.file_name}",
                            callback_data=f'clone_file#{file.file_id}'
                        )
                    ]
                    for file in files[:10]
                ]
                
                max_pages = (total_results + 9) // 10
                
                if page == 0:
                    nav_buttons = [
                        InlineKeyboardButton("Delete 🗑️", callback_data="close_data"),
                        InlineKeyboardButton(f"1/{max_pages}", callback_data="pages"),
                        InlineKeyboardButton("NEXT ⏩", callback_data=f"clone_next_{query_text}_1")
                    ]
                elif page < max_pages - 1:
                    nav_buttons = [
                        InlineKeyboardButton("⏪ BACK", callback_data=f"clone_back_{query_text}_{page - 1}"),
                        InlineKeyboardButton(f"{page + 1}/{max_pages}", callback_data="pages"),
                        InlineKeyboardButton("NEXT ⏩", callback_data=f"clone_next_{query_text}_{page + 1}")
                    ]
                else:
                    nav_buttons = [
                        InlineKeyboardButton("⏪ BACK", callback_data=f"clone_back_{query_text}_{page - 1}"),
                        InlineKeyboardButton(f"{page + 1}/{max_pages}", callback_data="pages"),
                        InlineKeyboardButton("Delete 🗑️", callback_data="close_data")
                    ]
                
                btn.append(nav_buttons)
                
                try:
                    await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
                except Exception:
                    pass
                await q.answer()

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

            await clones_collection.update_one(
                {"user_id": target_user_id},
                {"$set": {"token": bot_token, "status": "approved"}},
                upsert=True
            )

            revoke_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Delete / Revoke Bot", callback_data=f"delete_clone_{target_user_id}")]
            ])
            await query.message.edit_text(query.message.text + "\n\n✅ **STATUS: APPROVED & LIVE**", reply_markup=revoke_button)

            await client.send_message(
                target_user_id,
                "🎉 <b>Success!</b> Your clone bot has been approved by the admin and is now live and running!"
            )

        except Exception as e:
            await query.message.reply_text(f"❌ Failed to start clone bot: {e}")

    elif action == "delete":
        try:
            if target_user_id in ACTIVE_CLONES:
                await ACTIVE_CLONES[target_user_id].stop()
                del ACTIVE_CLONES[target_user_id]
        except Exception as e:
            logger.error(f"Error stopping clone client: {e}")

        await clones_collection.delete_one({"user_id": target_user_id})
        PENDING_CLONES.pop(str(target_user_id), None)

        await query.message.edit_text(query.message.text + "\n\n❌ **STATUS: DELETED / REVOKED BY ADMIN**")
        
        try:
            await client.send_message(
                target_user_id,
                "⚠️ <b>Notice:</b> Your clone bot has been removed/revoked by the admin."
            )
        except:
            pass
        await query.answer("Clone bot successfully deleted and revoked!", show_alert=True)

    else:
        PENDING_CLONES.pop(str(target_user_id), None)
        await query.message.edit_text(query.message.text + "\n\n❌ **STATUS: REJECTED**")
        try:
            await client.send_message(
                target_user_id,
                "❌ <b>Sorry!</b> Your clone bot request has been rejected by the admin."
            )
        except:
            pass
