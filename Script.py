class script(object):
    START_TXT = """<b>👋 Hey 🇮🇳 {},</b>
    
<i>Iam a</i> <b>autofilter bot</b> <i>I will give movies in your group and my pm! Also I can share files...</i>"""
    
    ABOUT_TXT = """<b>╭─── ✦ ABOUT ME ✦ ───╮</b>
<b>╭🤖  • My name - {}</b>
<b>╰👤  • Creator - <a href=https://t.me/TG_x_filter>🇮🇳 𝗛𝗘𝗗𝗗𝗬 ◢ ◤</b></a>
<b>╭🖥️  • Developer - Mantis</b>
<b>╰📚  • Library - Program</b> 
<b>╭📝  • Language - Python</b>
<b>╰🚀  • Bot Update - Click Here</b>
<b>╭🔋  • Database - MongoDB</b>
<b>╰📡  • Bot Server - Anywhere</b>
<b>╰─────────────────╯</b>
<b>👨‍💻 Managed By <a href=https://t.me/Mallu_Movie_Hub_Group>CINEMA FLIX</b></a>"""
    
    STATUS_TXT = """<b>📊 𝙂𝙇O𝘽𝘼𝙇 𝙎𝙏𝘼𝙏𝙐𝙎 𝘽𝙊𝘼𝙍𝘿 📊</b>

<b>📂 Database 1:</b>
   • Total Files: <code>{db1_count}</code>
   • Used Storage: <code>{db1_size}</code>

<b>📂 Database 2:</b>
   • Total Files: <code>{db2_count}</code>
   • Used Storage: <code>{db2_size}</code>

<b>📂 Database 3:</b>
   • Total Files: <code>{db3_count}</code>
   • Used Storage: <code>{db3_size}</code>

<b>👥 Total Members:</b> <code>{users}</code>
<b>💬 Total Chats:</b> <code>{chats}</code>"""
    
    LOG_TEXT_G = """#NewGroup
Group = {}(<code>{}</code>)
Total Members = <code>{}</code>
Added By - {}
"""
    LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Name - {}
"""

    # Updated Custom File Caption with Quality, Duration, Language, Subtitles, and IMDb Genres
    FILE_CAPTION = """<b>Hᴇʟʟᴏ 👋 {user_mention},!</b>

<b>📚 <code>{file_name}</code></b>

<b>⚙️ ꜰɪʟᴇ sɪᴢᴇ:</b> {file_size}

<b>╭────── • ◆ • ──────╮</b>
<b>📮 ᴊᴏɪɴ : <a href=https://t.me/CFOTTUPDATE>ᴄʜᴀɴɴᴇʟ</b></a>
<b>🔖 ᴍᴏᴠɪᴇs : <a href=https://t.me/Mallu_Movie_Hub_Group>ɢʀᴏᴜᴘ</b></a>
<b>╰────── • ◆ • ──────╯</b>
<b>🎗 ʝσιи • ѕнαяє • ѕυρρσят 🎗</b>
    
<b><a href=https://t.me/+iEbhY7mM4oE1OTVl>©️𝐓𝐞𝐚𝐦 𝐂𝐢𝐧𝐞𝐦𝐚 𝐅𝐢𝐥𝐱™️</b></a>"""

    START_TXT_GROUP = """ഹലോ {}\n\n• എന്താണ് സഹോദരന് വേണ്ടത്? സ്റ്റാർട്ട്‌ ആയപ്പോ ഒരു സുഖം കിട്ടി അല്ലേ.. 🤭😜\n\n• എന്തായാലും വന്നതല്ലേ. ഇവിടെ കാണുന്ന ചാനൽ & ഗ്രൂപ്പ് ൽ ഒക്കെ Join ചെയ്തേക്ക് 😎"""
