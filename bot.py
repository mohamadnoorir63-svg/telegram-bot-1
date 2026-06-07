     import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN"

# 🗃 دیتابیس ساده
conn = sqlite3.connect("imposter.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS scores (
    user TEXT PRIMARY KEY,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0
)
""")
conn.commit()


# 🏠 همه روم‌ها
rooms = {}


def get_room(chat_id):
    if chat_id not in rooms:
        rooms[chat_id] = {
            "players": {},
            "alive": set(),
            "roles": {},
            "host": None,
            "started": False,
            "votes": {},
            "voted_users": set(),
            "killed": set()
        }
    return rooms[chat_id]


# 📊 ثبت امتیاز
def update_score(user, win):
    cur.execute("SELECT * FROM scores WHERE user=?", (user,))
    data = cur.fetchone()

    if not data:
        cur.execute("INSERT INTO scores (user, wins, losses) VALUES (?,0,0)", (user,))
        conn.commit()

    if win:
        cur.execute("UPDATE scores SET wins = wins + 1 WHERE user=?", (user,))
    else:
        cur.execute("UPDATE scores SET losses = losses + 1 WHERE user=?", (user,))

    conn.commit()


# 🎮 start menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Join", callback_data="join")],
        [InlineKeyboardButton("🚀 Start", callback_data="start")],
        [InlineKeyboardButton("🗳 Vote", callback_data="vote")],
        [InlineKeyboardButton("💀 Kill (Imposter)", callback_data="kill")],
        [InlineKeyboardButton("📊 Score", callback_data="score")]
    ]

    await update.message.reply_text(
        "🎮 Imposter Ultimate Game",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 🎯 buttons
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    chat_id = query.message.chat_id
    room = get_room(chat_id)

    # ➕ Join
    if query.data == "join":
        if room["started"]:
            await query.edit_message_text("❌ بازی شروع شده")
            return

        if room["host"] is None:
            room["host"] = user

        room["players"][user] = True

        await query.edit_message_text(f"✅ {user} joined\n👥 {list(room['players'].keys())}")


    # 🚀 Start game
    elif query.data == "start":
        if user != room["host"]:
            await query.edit_message_text("❌ فقط Host")
            return

        if len(room["players"]) < 4:
            await query.edit_message_text("⚠️ حداقل 4 نفر")
            return

        room["started"] = True
        room["alive"] = set(room["players"].keys())

        # 🎭 نقش‌ها
        p = list(room["players"].keys())
        imposter = random.choice(p)

        room["roles"][imposter] = "imposter"

        for pl in p:
            if pl != imposter:
                room["roles"][pl] = random.choice(["crewmate", "doctor", "detective"])

        await query.edit_message_text("🎮 Game Started!")


    # 🗳 vote
    elif query.data == "vote":
        if not room["started"]:
            return

        keyboard = [
            [InlineKeyboardButton(p, callback_data=f"v_{p}")]
            for p in room["alive"]
        ]

        await query.edit_message_text("🗳 Vote:", reply_markup=InlineKeyboardMarkup(keyboard))


    # 💀 kill (imposter)
    elif query.data == "kill":
        if room["roles"].get(user) != "imposter":
            await query.edit_message_text("❌ فقط Imposter")
            return

        targets = list(room["alive"])
        targets.remove(user)

        keyboard = [
            [InlineKeyboardButton(t, callback_data=f"k_{t}")]
            for t in targets
        ]

        await query.edit_message_text("💀 Kill target:", reply_markup=InlineKeyboardMarkup(keyboard))


    # 🗳 vote logic
    elif query.data.startswith("v_"):
        target = query.data.split("_")[1]

        if user in room["voted_users"]:
            return

        room["voted_users"].add(user)
        room["votes"][target] = room["votes"].get(target, 0) + 1

        await check_vote(chat_id, query)


    # 💀 kill logic
    elif query.data.startswith("k_"):
        target = query.data.split("_")[1]

        room["alive"].discard(target)
        room["killed"].add(target)

        await query.edit_message_text(f"💀 {target} killed")

        await check_end(chat_id, query)


# 🧠 vote check
async def check_vote(chat_id, query):
    room = rooms[chat_id]

    if len(room["voted_users"]) < len(room["alive"]):
        return

    eliminated = max(room["votes"], key=room["votes"].get)

    room["alive"].discard(eliminated)

    room["votes"] = {}
    room["voted_users"] = set()

    role = room["roles"].get(eliminated)

    if role == "imposter":
        await query.message.reply_text("🟥 Imposter eliminated! Crew wins 🎉")

        for p in room["players"]:
            update_score(p, True)

        reset(chat_id)
        return

    await query.message.reply_text(f"❌ {eliminated} eliminated")


# 🧠 check win
async def check_end(chat_id, query):
    room = rooms[chat_id]

    alive = room["alive"]

    imposters_alive = [p for p in alive if room["roles"].get(p) == "imposter"]

    if not imposters_alive:
        await query.message.reply_text("🟩 Crew wins!")

        for p in room["players"]:
            update_score(p, True)

        reset(chat_id)
        return

    if len(alive) <= 2:
        await query.message.reply_text("🟥 Imposter wins 😈")

        for p in room["players"]:
            update_score(p, False)

        reset(chat_id)


# 💬 chat
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room = get_room(update.message.chat_id)

    if room["started"]:
        await update.message.reply_text(f"💬 {update.effective_user.first_name}: {update.message.text}")


# 🔄 reset
def reset(chat_id):
    rooms[chat_id] = {
        "players": {},
        "alive": set(),
        "roles": {},
        "host": None,
        "started": False,
        "votes": {},
        "voted_users": set(),
        "killed": set()
    }


# ▶️ run
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🚀 Ultimate Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
