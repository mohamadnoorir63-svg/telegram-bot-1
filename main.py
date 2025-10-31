from pyrogram import Client, filters
import os

# 🧩 متغیرهای محیطی از Render
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

# ✨ ساخت کلاینت Pyrogram
app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# 🚀 وقتی استارت شد
@app.on_message(filters.me & filters.command("ping", prefixes=["!", "/", ""]))
async def ping(_, msg):
    await msg.reply_text("🏓 Pong! یوزربات فعاله ✅")

@app.on_message(filters.me & filters.text)
async def echo(_, msg):
    if msg.text.lower() == "سلام":
        await msg.reply_text("سلام رفیق 😄 من آنلاینم!")

print("✅ Userbot started and listening for messages...")
app.run()
