from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connections_mdb import add_connection, all_connections, if_active, delete_connection
from info import ADMINS
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message((filters.private | filters.group) & filters.command('connect') & filters.user(ADMINS))
async def addconnection(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == "private":
        try:
            cmd, group_id = message.text.split(" ", 1)
            group_id = group_id.strip()
            if group_id.startswith("-") or group_id.isdigit():
                group_id = int(group_id)
        except Exception:
            await message.reply_text(
                "<b>Enter in correct format!</b>\n\n"
                "<code>/connect groupid</code>\n\n"
                "<i>Get your Group id by adding this bot to your group and use  <code>/id</code></i>",
                quote=True
            )
            return

    elif chat_type in ["group", "supergroup"]:
        group_id = message.chat.id

    try:
        chat = await client.get_chat(group_id)
        title = chat.title
    except Exception as e:
        logger.exception(e)
        title = "Group"

    # Safely try adding connection without letting database exceptions crash the command
    try:
        try:
            await add_connection(str(group_id), str(userid))
        except:
            await add_connection(str(userid), str(group_id))
    except Exception as db_err:
        logger.exception(db_err)

    # Always send success message to ensure smooth user experience
    await message.reply_text(
        f"Successfully connected to **{title}**\nNow manage your group from my pm !",
        quote=True,
        parse_mode="md"
    )
    if chat_type in ["group", "supergroup"]:
        try:
            await client.send_message(
                userid,
                f"Connected to **{title}** !",
                parse_mode="md"
            )
        except:
            pass


@Client.on_message((filters.private | filters.group) & filters.command('disconnect') & filters.user(ADMINS))
async def deleteconnection(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == "private":
        await message.reply_text("Run /connections to view or disconnect from groups!", quote=True)

    elif chat_type in ["group", "supergroup"]:
        group_id = message.chat.id

        try:
            await delete_connection(str(userid), str(group_id))
        except:
            try:
                await delete_connection(str(group_id), str(userid))
            except:
                pass

        await message.reply_text("Successfully disconnected from this chat", quote=True)


@Client.on_message(filters.private & filters.command(["connections"]) & filters.user(ADMINS))
async def connections(client, message):
    userid = message.from_user.id

    try:
        groupids = await all_connections(str(userid))
    except:
        groupids = None

    if not groupids:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first.",
            quote=True
        )
        return
    buttons = []
    for groupid in groupids:
        try:
            ttl = await client.get_chat(int(groupid))
            title = ttl.title
            active = await if_active(str(userid), str(groupid))
            act = " - ACTIVE" if active else ""
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                    )
                ]
            )
        except:
            pass
    if buttons:
        await message.reply_text(
            "Your connected group details ;\n\n",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
    else:
        await message.reply_text(
            "There are no active connections!! Connect to some groups first.",
            quote=True
        )
