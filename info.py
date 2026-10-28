import re
from os import environ
from Script import script

# Regex pattern for validating ID strings
id_pattern = re.compile(r'^.\d+$')

def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

# --------------------------------------------------------------------------- #
#  Bot Core Configuration & Credentials                                      #
# --------------------------------------------------------------------------- #
SESSION = environ.get('SESSION', 'Media_search')
API_ID = int(environ['API_ID'])
API_HASH = environ['API_HASH']
BOT_TOKEN = environ['BOT_TOKEN']

# --------------------------------------------------------------------------- #
#  Bot General Settings                                                      #
# --------------------------------------------------------------------------- #
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', False))
PICS = (environ.get('PICS', 'https://envs.sh/te8.jpg https://envs.sh/te7.jpg')).split()
FORCE_IMG = environ.get('FORCE_IMG', "https://graph.org/file/495474c424c774e2fa7b5-15e6a76e4bec7f6fc7.jpg")
NOR_IMG = environ.get('NOR_IMG', "https://envs.sh/PvY.jpg")
SET_IMG = environ.get('SET_IMG', "https://envs.sh/RCE.jpg") 


# --------------------------------------------------------------------------- #
#  Admins, Authorized Channels & Users                                       #
# --------------------------------------------------------------------------- #
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '').split()]
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '0').split()]
auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []

auth_channel = environ.get('AUTH_CHANNEL')
auth_grp = environ.get('AUTH_GROUP')
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None
AUTH_GROUPS = [int(ch) for ch in auth_grp.split()] if auth_grp else None

# --------------------------------------------------------------------------- #
#  Database Configuration (MongoDB)                                          #
# --------------------------------------------------------------------------- #
DATABASE_URI = environ.get('DATABASE_URI', "")
DATABASE_NAME = environ.get('DATABASE_NAME', "Rajappan")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Telegram_files')

# --------------------------------------------------------------------------- #
#  External Links & Portals                                                  #
# --------------------------------------------------------------------------- #
FILMS_LINK = environ.get('FILMS_LINK', 'https://t.me/cinema_filx_updates')

# --------------------------------------------------------------------------- #
#  Advanced Features & Customizations                                        #
# --------------------------------------------------------------------------- #
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', 0))
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'cinema_filx_updates')

# OMDb API Key for Advanced IMDb / OMDb Fallback Search
OMDB_API_KEY = environ.get('OMDB_API_KEY', "")

P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "False")), False)
IMDB = is_enabled((environ.get('IMDB', "True")), True)
SINGLE_BUTTON = is_enabled((environ.get('SINGLE_BUTTON', "False")), False)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.FILE_CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)

IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", "<b><i>️🧿 𝘔𝘰𝘷𝘪𝘦 𝘕𝘢𝘮𝘦 : {search}\n\n🛡𝘙𝘦𝘲𝘶𝘦𝘴𝘵𝘦𝘥 𝘉𝘺 : {message.from_user.mention}\n🧩𝘎𝘳𝘰𝘶𝘱 : {message.chat.title}</i></b>")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)

INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))
FILE_STORE_CHANNEL = [int(ch) for ch in (environ.get('FILE_STORE_CHANNEL', '')).split()]
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "True")), True)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), False)
PUBLIC_FILE_STORE = is_enabled((environ.get('PUBLIC_FILE_STORE', "True")), True)

# --------------------------------------------------------------------------- #
#  Startup Logger String Generation                                          #
# --------------------------------------------------------------------------- #
LOG_STR = "Current Customized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled, Bot will be showing imdb details for your queries.\n" if IMDB else "IMDB Results are disabled.\n")
LOG_STR += ("P_TTI_SHOW_OFF found, Users will be redirected to send /start to Bot PM instead of sending file directly\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF is disabled, files will be sent in PM instead of sending start.\n")
LOG_STR += ("SINGLE_BUTTON is Found, filename and file size will be shown in a single button instead of two separate buttons\n" if SINGLE_BUTTON else "SINGLE_BUTTON is disabled, filename and file size will be shown as different buttons\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION enabled with value {CUSTOM_FILE_CAPTION}, your files will be sent along with this customized caption.\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION Found, Default captions of file will be used.\n")
LOG_STR += ("Long IMDB storyline enabled.\n" if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION is disabled, Plot will be shorter.\n")
LOG_STR += ("Spell Check Mode Is Enabled, bot will be suggesting related movies if movie not found\n" if SPELL_CHECK_REPLY else "SPELL_CHECK_REPLY Mode disabled\n")
LOG_STR += (f"MAX_LIST_ELM Found, long list will be shortened to first {MAX_LIST_ELM} elements\n" if MAX_LIST_ELM else "Full List of casts and crew will be shown in imdb template, restrict them by adding a value to MAX_LIST_ELM\n")
LOG_STR += f"Your current IMDB template is {IMDB_TEMPLATE}"
