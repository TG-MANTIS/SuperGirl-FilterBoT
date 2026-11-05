import os
import logging
import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from info import ADMINS, DATABASE_URI, DATABASE_NAME, LOG_CHANNEL
from database.ia_filterdb import get_search_results, get_file_details, get_databases_stats, main_media_classes
from database.users_chats_db import db as main_users_db
from utils import get_size

logger = logging.getLogger(__name__)

# MongoDB Connection for Cloned Bots
db_client = AsyncIOMotorClient(DATABASE_URI)
db = db_client[DATABASE_NAME]
clones_collection = db["cloned_bots"]
clone_connections_collection = db["clone_connections"]
mapping_col = db["user_db_mappings"]

# Store active clone clients in memory
ACTIVE_CLONES = {}

# Dictionary to temporarily store token requests
PENDING_CLONES = {}

# Regex pattern to match Telegram Bot Token
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

# /clone Command Handler
@Client.on_message(filters.command("clone") & filters.private)
async def clone_command_handler(client, message: Message):
    if len(message.command) < 2:
        guide_text = get_clone_guide_text()
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
        ])
        return await message.reply_text(guide_text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
    
    await process_token_submission(client, message, message.text)

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

# Direct Text / Forwarded Message Token Handler
@Client.on_message(filters.private & ~filters.command(["start", "clone", "help", "settings"]))
async def direct_token_handler(client, message: Message):
    text_content = message.text or message.caption or ""
    if TOKEN_REGEX.search(text_content):
        await process_token_submission(client, message, text_content)

# Admin Actions (Approve, Reject, Delete/Revoke, and Reset/Restore Clone Bot)
@Client.on_callback_query(filters.regex(r"^(approve|reject|delete|reset)_clone_"))
async def clone_approval_callback(client, query: CallbackQuery):
    if query.from_user.id not in ADMINS:
        return await query.answer("You are not authorized!", show_alert=True)

    data = query.data.split("_")
    action = data[0]
    target_user_id = int(data[2])

    if action in ["approve", "reset"]:
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
            
            # Start command handler - Sends only sticker as requested
            @clone_client.on_message(filters.command("start") & filters.private)
            async def clone_start(c, m):
                try:
                    await c.send_sticker(
                        chat_id=m.chat.id,
                        sticker="CAACAgUAAxkBAALO6Grr6XPfQWheI1mr0XVfn4LNTz1RAAIrAAO8ljUq9-AkUFoHiMQ9BA"
                    )
                except Exception as e:
                    logger.error(f"Failed to send start sticker: {e}")

            # Dual-Mode Status Command Handler (Paid vs Free)
            @clone_client.on_message(filters.command("status") & filters.private)
            async def clone_status_handler(c, m):
                stats_msg = await m.reply("📊 Fetching database statistics... Please wait.")
                try:
                    user_mapping = await mapping_col.find_one({"user_id": target_user_id})
                    
                    def readable_size(size_in_bytes):
                        if size_in_bytes == 0:
                            return "0 MB"
                        units = ["B", "KB", "MB", "GB", "TB"]
                        i = 0
                        while size_in_bytes >= 1024 and i < len(units) - 1:
                            size_in_bytes /= 1024.0
                            i += 1
                        return f"{size_in_bytes:.2f} {units[i]}"

                    close_keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("✘ Cʟᴏꜱᴇ", callback_data="close_data")]]
                    )

                    if user_mapping:
                        slot_name = user_mapping.get("slot_name", "Paid Slot")
                        stats_data = await get_databases_stats(user_id=target_user_id)
                        total_files = sum(st.get("count", 0) for st in stats_data)
                        total_size_bytes = sum(st.get("size", 0) for st in stats_data)
                        storage_used = readable_size(total_size_bytes)
                        
                        status_text = (
                            f"<b>💎 Dedicated Database Status (Paid Tier)</b>\n\n"
                            f"👤 <b>Bot Owner ID:</b> <code>{target_user_id}</code>\n"
                            f"📂 <b>Assigned Slot:</b> <code>{slot_name}</code>\n"
                            f"📁 <b>Total Files in Your DB:</b> <code>{total_files:,}</code>\n"
                            f"💾 <b>Storage Used:</b> <code>{storage_used}</code>\n"
                            f"🟢 <b>Status:</b> Active & Running smoothly!"
                        )
                        await stats_msg.edit_text(status_text, parse_mode=enums.ParseMode.HTML, reply_markup=close_keyboard)
                    else:
                        total_global_files = 0
                        for MediaModel in main_media_classes:
                            try:
                                count = await MediaModel.count_documents({})
                                total_global_files += count
                            except:
                                pass
                        
                        total_users = 0
                        total_chats = 0
                        try:
                            total_users = await main_users_db.total_users_count()
                            total_chats = await main_users_db.total_chat_count()
                        except Exception as e:
                            logger.error(f"Error fetching user/chat counts in clone status: {e}")
                        
                        try:
                            db_stats = await db.command("dbStats")
                            main_size_bytes = db_stats.get("dataSize", 0)
                            main_storage = readable_size(main_size_bytes)
                        except:
                            main_storage = "N/A"

                        status_text = (
                            f"<b>📊 Bot Storage Statistics (Free Tier)</b>\n\n"
                            f"🌐 <b>Global Files Available:</b> <code>{total_global_files:,}</code>\n"
                            f"👥 <b>Total Bot Users:</b> <code>{total_users:,}</code>\n"
                            f"💬 <b>Total Connected Chats:</b> <code>{total_chats:,}</code>\n"
                            f"💾 <b>Global DB Storage:</b> <code>{main_storage}</code>\n\n"
                            f"💡 <i>Want your own dedicated database slot? Contact the admin to upgrade!</i>"
                        )
                        await stats_msg.edit_text(status_text, parse_mode=enums.ParseMode.HTML, reply_markup=close_keyboard)

                except Exception as e:
                    logger.error(f"Error in clone status: {e}")
                    await stats_msg.edit_text("❌ Failed to retrieve statistics.")

            # Auto-Connect Command Handler for Group Admins (/connect)
            @clone_client.on_message(filters.command("connect") & filters.group)
            async def clone_connect_handler(c, m):
                try:
                    member = await c.get_chat_member(m.chat.id, m.from_user.id)
                    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and m.from_user.id not in ADMINS:
                        return await m.reply_text("❌ Only group admins can connect this bot!")
                except Exception:
                    pass

                chat_id = m.chat.id
                chat_title = m.chat.title

                await clone_connections_collection.update_one(
                    {"bot_id": target_user_id, "chat_id": chat_id},
                    {"$set": {"chat_title": chat_title}},
                    upsert=True
                )

                await m.reply_text(
                    f"✅ <b>Successfully Connected!</b>\n\n"
                    f"📍 <b>Group:</b> <code>{chat_title}</code>\n"
                    f"🔗 <b>Chat ID:</b> <code>{chat_id}</code>\n\n"
                    f"<i>This group is now successfully linked with your clone bot! 🎉</i>",
                    parse_mode=enums.ParseMode.HTML
                )

            # Welcome Message Handler with Auto-Delete
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

            # Auto-Filter Logic inside Cloned Bot with Dynamic DB Support
            @clone_client.on_message(filters.group & filters.text & filters.incoming)
            async def clone_auto_filter(c, m):
                if m.text.startswith("/"):
                    return
                
                try:
                    bot_member = await c.get_chat_member(m.chat.id, (await c.get_me()).id)
                    is_admin = bot_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
                except Exception:
                    is_admin = True

                if not is_admin:
                    user_mention = m.from_user.mention if m.from_user else "User"
                    movie_name = m.text
                    
                    promo_text = (
                        f"Hello <b>{user_mention}</b>,\n\n"
                        f"I cannot provide the movie <b>\"{movie_name}\"</b> here because I am <b>not made an admin</b> in this group yet! ⚠️\n\n"
                        f"👉 Join Main Group: <b>@LutappiUpdates</b>"
                    )
                    buttons = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Join Main Movie Group", url="https://t.me/LutappiUpdates")]
                    ])
                    
                    promo_msg = await m.reply_text(promo_text, reply_markup=buttons)
                    await asyncio.sleep(4)
                    try:
                        await promo_msg.delete()
                    except Exception:
                        pass
                    return

                query_text = m.text.lower().strip()
                if 2 < len(query_text) < 100:
                    files, offset, total_results = await get_search_results(query_text, offset=0, filter=True, user_id=target_user_id)
                    
                    if not files:
                        no_res_msg = await m.reply_text(
                            f"<b>❌ Sorry, no files found for \"<code>{m.text}</code>\"!</b>",
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

            async def auto_delete_message(message: Message, delay: int):
                await asyncio.sleep(delay)
                try:
                    await message.delete()
                except Exception:
                    pass

            @clone_client.on_callback_query(filters.regex(r"^clone_(next|back)_"))
            async def clone_paginate_handler(c, q):
                data_parts = q.data.split("_")
                query_text = data_parts[2]
                page = int(data_parts[3])
                
                offset = page * 10
                files, _, total_results = await get_search_results(query_text, offset=offset, filter=True, user_id=target_user_id)
                
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
                files_ = await get_file_details(file_id, user_id=target_user_id)
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

            action_buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗑️ Delete / Revoke", callback_data=f"delete_clone_{target_user_id}"),
                    InlineKeyboardButton("🔄 Reset Bot", callback_data=f"reset_clone_{target_user_id}")
                ]
            ])
            
            msg_prefix = "♻️ **STATUS: RESET & RESTORED (Free Mode)**" if action == "reset" else "✅ **STATUS: APPROVED & LIVE**"
            await query.message.edit_text(query.message.text + f"\n\n{msg_prefix}", reply_markup=action_buttons)

            # Send restart/restore notification directly to user's clone bot private chat
            try:
                restart_notice = (
                    "🎉 <b>Great News! Your Bot Has Been Restarted & Restored!</b>\n\n"
                    "🚀 Your custom clone bot is now back online and running smoothly.\n"
                    "✨ You can start using your bot normally now!"
                )
                close_btn = InlineKeyboardMarkup([[InlineKeyboardButton("✘ Cʟᴏꜱᴇ", callback_data="close_data")]])
                await clone_client.send_message(target_user_id, restart_notice, reply_markup=close_btn, parse_mode=enums.ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to send restart notification to user: {e}")

            await query.answer("Bot successfully activated and user notified!", show_alert=True)

        except Exception as e:
            await query.message.reply_text(f"❌ Failed to start clone bot: {e}")

    elif action == "delete":
        try:
            if target_user_id in ACTIVE_CLONES:
                await ACTIVE_CLONES[target_user_id].stop()
                del ACTIVE_CLONES[target_user_id]
        except Exception as e:
            logger.error(f"Error stopping clone client: {e}")

        paid_mapping = await mapping_col.find_one({"user_id": target_user_id})
        if paid_mapping and "db_uri" in paid_mapping:
            paid_uri = paid_mapping["db_uri"]
            try:
                paid_client_temp = AsyncIOMotorClient(paid_uri)
                paid_db_name = paid_uri.split("/")[-1].split("?")[0] or "cluster0"
                await paid_client_temp.drop_database(paid_db_name)
                logger.info(f"Successfully dropped/refreshed Paid DB for user {target_user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh paid database for user {target_user_id}: {e}")
            
            await mapping_col.delete_one({"user_id": target_user_id})

        await clones_collection.delete_one({"user_id": target_user_id})

        action_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Reset & Restore Bot", callback_data=f"reset_clone_{target_user_id}")]
        ])
        await query.message.edit_text(query.message.text + "\n\n❌ **STATUS: SUSPENDED / REVOKED BY ADMIN**", reply_markup=action_buttons)
        
        try:
            suspend_text = (
                "⚠️ <b>Notice: Your Bot Has Been Suspended!</b>\n\n"
                "❌ Your custom clone bot has been temporarily stopped and removed by the admin.\n"
                "💡 <i>If you think this was a mistake or wish to continue using our service, please contact the admin/owner to sort it out.</i>"
            )
            temp_token = PENDING_CLONES.get(str(target_user_id)) or (await clones_collection.find_one({"user_id": target_user_id}) or {}).get("token")
            if temp_token:
                temp_notify_client = Client(f"notify_{target_user_id}", api_id=int(os.environ.get("API_ID", 0)), api_hash=os.environ.get("API_HASH", ""), bot_token=temp_token)
                await temp_notify_client.start()
                await temp_notify_client.send_message(target_user_id, suspend_text, parse_mode=enums.ParseMode.HTML)
                await temp_notify_client.stop()
        except Exception as e:
            logger.error(f"Failed to send suspension notification to user: {e}")

        await query.answer("Clone bot successfully suspended, database refreshed, and user notified!", show_alert=True)

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
