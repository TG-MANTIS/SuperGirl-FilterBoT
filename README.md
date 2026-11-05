തീർച്ചയായും! താങ്കൾക്ക് ഒരൊറ്റ README.md ഫയലിൽ തന്നെ മെയിൻ ബോട്ട്, ക്ലോൺ ബോട്ട്, മാസ്റ്റർ ബ്രോഡ്കാസ്റ്റിന്റെ 3 രീതികൾ, കൂടാതെ ബാക്കി എല്ലാ ഡീറ്റെയിൽസും വിശദമായി ഒട്ടും ഒഴിവാക്കാതെ ഫുൾ ആയി കാണാൻ പാകത്തിലുള്ള ആ കംപ്ലീറ്റ് കോഡ് താഴെ നൽകുന്നു.
ഇത് കോപ്പി ചെയ്ത് താങ്കളുടെ പ്രൊജക്റ്റിലെ README.md ഫയലിൽ പൂർണ്ണമായി പേസ്റ്റ് ചെയ്താൽ, ഫയൽ ഓപ്പൺ ചെയ്യുമ്പോൾ തന്നെ എല്ലാ കാര്യങ്ങളും ഡീറ്റെയിൽഡ് ആയി ഒരൊറ്റ സ്ഥലത്ത് കാണാൻ സാധിക്കും:
<p align="center">
  <img src="https://envs.sh/X0_.jpg" width="120px" alt="Bot Logo">
</p>

<h1 align="center">🤖 L U T A P P I   M A N A G E R</h1>

<p align="center">
  <b>Complete Bot Dashboard, Commands & Setup Guide</b><br>
  <i>Powered by Pyrogram & Motor (MongoDB)</i>
</p>

---

## 📖 0. Introduction & Overview
This repository contains a modular Telegram bot architecture designed for automated bot cloning, multi-tier database mapping, subscription flows, and advanced master broadcasting tools. Everything is neatly categorized below for easy reference and management.

---

## 👑 1. Main Bot Commands & Usage
> *ഇത് താങ്കൾ **മെയിൻ ബോട്ടിന്റെ** ചാറ്റിൽ ചെയ്യേണ്ടതും ഉപയോഗിക്കേണ്ടതുമായ കമാൻഡുകളാണ്.*

### 🛠️ General Commands (Admin & Users)
```bash
/start         - Launch and initialize the main bot in private chat
/help          - Open the interactive help dashboard and information menu
/settings      - Configure bot preferences, toggles, and user settings
/clone [TOKEN] - Submit your @BotFather token to request a custom clone bot

📢 Main Bot Broadcast System (Admin Only)
> മെയിൻ ബോട്ട് യൂസർമാർക്കും ഗ്രൂപ്പുകൾക്കും മാത്രം മെസ്സേജ് അയക്കാനുള്ള സംവിധാനം.
> 
/broadcast     - Broadcast a replied message to all registered main bot users (PM)
/gbroadcast    - Broadcast a replied message to all connected main bot groups/chats

⚙️ 2. Cloned Bot Commands & Usage
> ഇത് താങ്കൾ ക്ലോൺ ചെയ്തെടുത്ത ബോട്ടുകളിൽ യൂസർമാർക്കും ഗ്രൂപ്പ് അഡ്മിൻമാർക്കും ലഭിക്കുന്ന കമാൻഡുകളാണ്.
> 
/start         - Start your custom cloned bot (Automatically triggers a welcome sticker)
/status        - Check database & storage statistics (Supports Free Tier vs. Paid Dedicated DB Tier)
/connect       - Link a group to your clone bot (Must be used inside the group by a Group Admin)

🚀 3. Master Broadcast Commands (Admin Only)
> ക്ലോൺ ചെയ്ത എല്ലാ ബോട്ടുകളിലേക്കും ഒരേസമയം മെസ്സേജ് അയക്കാനുള്ള മാസ്റ്റർ ബ്രോഡ്കാസ്റ്റ് സിസ്റ്റം.
> ⚠️ Important Note: അഡ്മിൻ ഏതെങ്കിലും ഒരു മെസ്സേജിന് Reply (ഉത്തരം) നൽകിയ ശേഷമേ താഴെ പറയുന്ന കമാൻഡുകൾ ഉപയോഗിക്കാൻ പാടുള്ളൂ. അയക്കുന്ന എല്ലാ മെസ്സേജുകളും കൃത്യം 24 മണിക്കൂറിനു ശേഷം ഓട്ടോമാറ്റിക് ആയി ഡിലീറ്റ് (Auto-Delete) ആകുന്നതാണ്.
> 
1️⃣ Method 1: PM Only (പ്രൈവറ്റ് ചാറ്റിലേക്ക് മാത്രം)
> എല്ലാ ക്ലോൺ ബോട്ട് യൂസർമാരുടെയും പ്രൈവറ്റ് ചാറ്റിലേക്ക് മാത്രം മെസ്സേജ് പോകും.
> 
/master_broadcast pm

2️⃣ Method 2: Group Only (കണക്ട് ചെയ്ത ഗ്രൂപ്പുകളിലേക്ക് മാത്രം)
> യൂസർമാർ അവരുടെ ക്ലോൺ ബോട്ട് അഡ്മിൻ ആക്കി കണക്ട് ചെയ്തിട്ടുള്ള എല്ലാ ഗ്രൂപ്പുകളിലേക്കും (ആ ബോട്ട് വഴി മാത്രം) മെസ്സേജ് പോകും. (ഗ്രൂപ്പിലുള്ളവർക്ക് ഇത് ആ യൂസറുടെ സ്വന്തം ബോട്ട് അയച്ചതാണെന്നേ തോന്നു).
> 
/master_broadcast group

3️⃣ Method 3: All (പ്രൈവറ്റ് ചാറ്റിലേക്കും ഗ്രൂപ്പുകളിലേക്കും ഒരുമിച്ച്)
> പ്രൈവറ്റ് ചാറ്റിലേക്കും കണക്ട് ചെയ്ത എല്ലാ ഗ്രൂപ്പുകളിലേക്കും ഒരേസമയം ഒരേപോലെയുള്ള മെസ്സേജുകൾ പോകും.
> 
/master_broadcast all

🔒 4. Automated Workflows & Guard Systems
> ബോട്ടിൽ ബാക്ക്‌ഗ്രൗണ്ടിൽ വർക്ക് ചെയ്യുന്ന പ്രധാനപ്പെട്ട ഓട്ടോമാറ്റിക് ഫീച്ചറുകൾ.
> 
 * 🔄 Subscription & Token Flow:
   * യൂസർമാർ /clone വഴി ടോക്കൻ അയക്കുമ്പോൾ ബോട്ട് ഓട്ടോമാറ്റിക്കായി സബ്‌സ്‌ക്രിപ്ഷൻ ഫീ ആവശ്യപ്പെടുകയും, താഴെ ~Mantis||℡🇮🇳 ബട്ടൺ വഴി @dxtgfilter-ലേക്ക് നയിക്കുകയും ചെയ്യും.
 * 🛡️ Admin Approval & Log System:
   * വരുന്ന ക്ലോൺ റിക്വസ്റ്റുകൾ അഡ്മിന്റെ LOG_CHANNEL-ലേക്ക് ✅ Approve, ❌ Reject, കൂടാതെ 🗑️ Delete / 🔄 Reset ബട്ടണുകളോടെ എത്തും.
 * ⚠️ Group Anti-Spam / Promo Guard:
   * ക്ലോൺ ബോട്ട് അഡ്മിൻ ആക്കാത്ത ഗ്രൂപ്പുകളിൽ ആരെങ്കിലും മൂവി ചോദിച്ചാൽ, ബോട്ട് വാണിങ് മെസ്സേജും ഒപ്പം 🔗 Join Main Movie Group (https://t.me/Mallu_Movie_Hub_Group) ബട്ടണും ഓട്ടോമാറ്റിക്കായി കാണിക്കും.
<p align="center">
<b>Designed with 🖤 for Professional Telegram Bot Management & Automation</b>
</p>

---

ഇപ്പോൾ ഈ ഫുൾ കോഡ് താങ്കളുടെ `README.md` ഫയലിൽ കൊടുത്തു കഴിഞ്ഞാൽ, ആ ഫയൽ തുറക്കുന്ന ആർക്കും മെയിൻ ബോട്ട്, ക്ലോൺ ബോട്ട്, മാസ്റ്റർ ബ്രോഡ്കാസ്റ്റിന്റെ മൂന്ന് രീതികൾ, ബാക്കി എല്ലാ ഡീറ്റെയിൽസും ഒരൊറ്റ പേജിൽ വളരെ വ്യക്തമായി കാണാനും കോപ്പി ചെയ്യാനും സാധിക്കും! 👍
http://googleusercontent.com/lmdx_content/nTaGpavbdRqNOgnTxOexCLhVIzoluPiOSvTMnOXwYomoPuMfHWFNyMZtqISIHGduzKbxwJthejZJIssdJEECTinewzuahytcoMlkKgFftQCBERdDWZSTmQnBXAbLFpSfohdZaDFUFZEjCLvtFJPldpDNFNOoIAxbjDSCwFYfObciJzcfrRKNQYAVBBssxIFEEzlQVQGrbfTPGqVnYJSIbcSgBLZCfgEJSYbKwRzKxKVKAzHF258142

