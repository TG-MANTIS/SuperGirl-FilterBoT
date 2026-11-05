"""
Core Group Connection Management Module
Handles secure linking/unlinking between users and Telegram groups/channels,
allowing administrators to manage group settings directly from private messages.
"""

import logging
from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connections_mdb import add_connection, all_connections, if_active, delete_connection
from info import ADMINS

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message((filters.private | filters.group) & filters.command('connect'))
async def connect_group_handler(client: Client, message):
    """
    Links a user to a target group/channel for private management and auto-filtering.
    Supports both direct group command usage and private PM with group ID.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use: <code>/connect {message.chat.id}</code> in my private messages.",
            parse_mode=enums.ParseMode.HTML
        )
        
    chat_type = message.chat.type

    # If invoked in private chat, extract group ID from command arguments
    if chat_type == enums.ChatType.PRIVATE:
        try:
            _, group_id = message.text.split(" ", 1)
        except ValueError:
            await message.reply_text(
                "<b>❌ Invalid Command Format!</b>\n\n"
                "📌 <b>Usage:</b> <code>/connect &lt;group_id&gt;</code>\n\n"
                "💡 <i>Tip: Add me to your group and type <code>/id</code> to get your Group ID.</i>",
                quote=True,
                parse_mode=enums.ParseMode.HTML
            )
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id

    # Verify if the executing user has administrative privileges in the target group
    try:
        member_status = await client.get_chat_member(group_id, user_id)
        if (
            member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
            and user_id not in ADMINS
            and str(user_id) not in [str(admin) for admin in ADMINS]
        ):
            await message.reply_text("❌ <b>You must be an administrator in the specified group to connect!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            return
    except Exception as err:
        logger.exception(err)
        await message.reply_text(
            "❌ <b>Invalid Group ID or Connection Failed!</b>\n\n"
            "💡 <i>Make sure I am added to your target group and have proper permissions.</i>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # Verify if the bot itself is an administrator in the target group
    try:
        bot_member = await client.get_chat_member(group_id, "me")
        if bot_member.status == enums.ChatMemberStatus.ADMINISTRATOR:
            chat_info = await client.get_chat(group_id)
            group_title = chat_info.title

            is_connected = await add_connection(str(group_id), str(user_id))
            if is_connected:
                await message.reply_text(
                    f"✅ <b>Successfully connected to:</b> <b>{group_title}</b>\n\n"
                    f"<i>You can now manage your group directly from my PM! 🚀</i>",
                    quote=True,
                    parse_mode=enums.ParseMode.HTML
                )
                if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
                    try:
                        await client.send_message(
                            user_id,
                            f"🔗 <b>Successfully linked with group:</b> <b>{group_title}</b> !",
                            parse_mode=enums.ParseMode.HTML
                        )
                    except Exception:
                        pass
            else:
                await message.reply_text(
                    "⚠️ <b>You are already connected to this chat!</b>",
                    quote=True,
                    parse_mode=enums.ParseMode.HTML
                )
        else:
            await message.reply_text("⚠️ <b>Please promote me as an administrator in your group first!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
            
    except Exception as err:
        logger.exception(err)
        await message.reply_text("❌ <b>An unexpected error occurred! Please try again later.</b>", quote=True, parse_mode=enums.ParseMode.HTML)
        return


@Client.on_message((filters.private | filters.group) & filters.command('disconnect'))
async def disconnect_group_handler(client: Client, message):
    """
    Unlinks an active group connection from the user's management panel.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply(
            f"⚠️ <b>Anonymous admin detected!</b>\n"
            f"Please use <code>/disconnect</code> directly inside the connected group.",
            parse_mode=enums.ParseMode.HTML
        )
        
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        await message.reply_text(
            "📌 <b>Please use the /connections command in PM to view and manage your connected groups!</b>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id

        try:
            member_status = await client.get_chat_member(group_id, user_id)
            if (
                member_status.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
                and user_id not in ADMINS
                and str(user_id) not in [str(admin) for admin in ADMINS]
            ):
                return
        except Exception:
            return

        is_disconnected = await delete_connection(str(user_id), str(group_id))
        if is_disconnected:
            await message.reply_text("✅ <b>Successfully disconnected from this chat!</b>", quote=True, parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("❌ <b>This chat is not connected to me!</b>\nUse <code>/connect</code> to link it.", quote=True, parse_mode=enums.ParseMode.HTML)


@Client.on_message(filters.private & filters.command(["connections"]))
async def list_connections_handler(client: Client, message):
    """
    Displays an interactive list of all active group connections linked to the user.
    """
    user_id = message.from_user.id

    group_ids = await all_connections(str(user_id))
    if not group_ids:
        await message.reply_text(
            "📂 <b>No active connections found!</b>\n"
            "<i>Connect to some groups first using <code>/connect</code>.</i>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
        return

    group_buttons = []
    for group_id in group_ids:
        try:
            chat_info = await client.get_chat(int(group_id))
            group_title = chat_info.title
            
            is_active_session = await if_active(str(user_id), str(group_id))
            active_badge = " [ACTIVE]" if is_active_session else ""
            
            group_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📌 {group_title}{active_badge}",
                        callback_data=f"groupcb:{group_id}:{active_badge}"
                    )
                ]
            )
        except Exception:
            pass

    if group_buttons:
        await message.reply_text(
            "📋 <b>Your Connected Group Dashboard:</b>\n\n"
            "<i>Select a group below to configure or manage:</i>",
            reply_markup=InlineKeyboardMarkup(group_buttons),
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            "📂 <b>No active connections found!</b>\n"
            "<i>Connect to some groups first using <code>/connect</code>.</i>",
            quote=True,
            parse_mode=enums.ParseMode.HTML
        )
