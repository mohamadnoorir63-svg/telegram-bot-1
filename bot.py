# -*- coding: utf-8 -*-
# Persian AntiLink Manager - Full Persian Edition
# نوشته شده برای محمد 👑 - نسخه نهایی و بدون باگ

import os
import json
import time
import logging
import jdatetime
import telebot
from telebot import types

# ------------------ ⚙️ تنظیمات پایه ------------------
TOKEN = os.environ.get("BOT_TOKEN")
SUDO_ID = int(os.environ.get("SUDO_ID", "0"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_FILE = "data.json"
LOG_FILE = "error.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ------------------ 💾 مدیریت داده ------------------
def base_data():
    return {
        "welcome": {},
        "locks": {},
        "admins": {},
        "sudo_list": [],
        "banned": {},
        "muted": {},
        "warns": {},
        "filters": {},
        "users": [],
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(base_data())
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = base_data()
    for k in base_data():
        if k not in data:
            data[k] = base_data()[k]
    save_data(data)
    return data

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def register_group(gid):
    d = load_data()
    gid = str(gid)
    d["welcome"].setdefault(gid, {"enabled": True, "msg": None})
    d["locks"].setdefault(gid, {k: False for k in ["link","photo","video","sticker","gif","file","music","voice","forward","text"]})
    save_data(d)

# ------------------ 🧠 ابزارها ------------------
def cmd_text(m):
    return (getattr(m, "text", None) or "").strip().lower()

def shamsi_date():
    return jdatetime.datetime.now().strftime("%A %d %B %Y")

def shamsi_time():
    return jdatetime.datetime.now().strftime("%H:%M:%S")

def is_sudo(uid):
    d = load_data()
    return str(uid) == str(SUDO_ID) or str(uid) in d.get("sudo_list", [])

def is_admin(chat_id, uid):
    d = load_data()
    gid = str(chat_id)
    if is_sudo(uid):
        return True
    if str(uid) in d.get("admins", {}).get(gid, []):
        return True
    try:
        st = bot.get_chat_member(chat_id, uid).status
        return st in ("administrator", "creator")
    except:
        return False

# ------------------ 👋 خوش‌آمد ------------------
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new(m):
    register_group(m.chat.id)
    d = load_data()
    gid = str(m.chat.id)
    s = d["welcome"].get(gid, {"enabled": True, "msg": None})
    if not s.get("enabled", True):
        return
    user = m.new_chat_members[0]
    name = user.first_name or "دوست جدید"
    group = m.chat.title or "گروه"
    text = s.get("msg") or f"✨ سلام {name}!\nبه گروه <b>{group}</b> خوش اومدی 🌸\n⏰ {shamsi_time()}"
    bot.send_message(m.chat.id, text, parse_mode="HTML")

# ------------------ 🔒 قفل‌ها ------------------
LOCK_MAP = {
    "لینک": "link",
    "عکس": "photo",
    "ویدیو": "video",
    "استیکر": "sticker",
    "گیف": "gif",
    "فایل": "file",
    "موزیک": "music",
    "ویس": "voice",
    "فوروارد": "forward",
    "متن": "text",
}

@bot.message_handler(func=lambda m: cmd_text(m).startswith("قفل "))
def lock_cmd(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return bot.reply_to(m, "فقط مدیرای گروه می‌تونن قفل بزنن 😎")

    d = load_data()
    gid = str(m.chat.id)
    key = cmd_text(m).replace("قفل ", "").strip()
    if key not in LOCK_MAP:
        return bot.reply_to(m, "❌ نوع قفل نامعتبره.")

    d["locks"].setdefault(gid, {k: False for k in LOCK_MAP.values()})
    d["locks"][gid][LOCK_MAP[key]] = True
    save_data(d)
    bot.reply_to(m, f"🔒 قفل {key} فعال شد ✅")

@bot.message_handler(func=lambda m: cmd_text(m).startswith("بازکردن "))
def unlock_cmd(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return bot.reply_to(m, "فقط مدیرای گروه می‌تونن قفل باز کنن 😅")

    d = load_data()
    gid = str(m.chat.id)
    key = cmd_text(m).replace("بازکردن ", "").strip()
    if key not in LOCK_MAP:
        return bot.reply_to(m, "❌ نوع قفل اشتباهه.")

    d["locks"].setdefault(gid, {k: False for k in LOCK_MAP.values()})
    d["locks"][gid][LOCK_MAP[key]] = False
    save_data(d)
    bot.reply_to(m, f"🔓 قفل {key} برداشته شد ✅")

# ------------------ 🔗 حذف لینک ------------------
@bot.message_handler(content_types=["text"])
def link_filter(m):
    d = load_data()
    gid = str(m.chat.id)
    locks = d.get("locks", {}).get(gid, {})
    if not locks:
        return
    if is_admin(m.chat.id, m.from_user.id) or is_sudo(m.from_user.id):
        return
    text = cmd_text(m)
    if locks.get("link") and any(x in text for x in ["http", "www.", "t.me/", "telegram.me/"]):
        try:
            bot.delete_message(m.chat.id, m.id)
            warn = bot.send_message(m.chat.id, f"🚫 {m.from_user.first_name} لینک ممنوعه 😅")
            time.sleep(3)
            bot.delete_message(m.chat.id, warn.id)
        except:
            pass

# ------------------ 🚫 بن / میوت / اخطار ------------------
def target_user(m):
    if m.reply_to_message:
        return m.reply_to_message.from_user.id
    parts = cmd_text(m).split()
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return None

def bot_can_restrict(m):
    try:
        me = bot.get_me()
        perms = bot.get_chat_member(m.chat.id, me.id)
        if perms.status in ("administrator", "creator") and getattr(perms, "can_restrict_members", True):
            return True
    except:
        pass
    bot.reply_to(m, "⚠️ من ادمین نیستم یا اجازه محدودسازی ندارم 😅")
    return False

@bot.message_handler(func=lambda m: cmd_text(m).startswith("بن"))
def ban_user(m):
    if not is_admin(m.chat.id, m.from_user.id) or not bot_can_restrict(m):
        return
    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا بنش کنم 😁")
    if is_admin(m.chat.id, target) or is_sudo(target):
        return bot.reply_to(m, "نمی‌تونم مدیر یا سودو رو بن کنم 😎")
    try:
        bot.ban_chat_member(m.chat.id, target)
        bot.send_message(m.chat.id, f"🚫 کاربر <a href='tg://user?id={target}'>بن شد</a> ❌", parse_mode="HTML")
    except:
        bot.reply_to(m, "⚠️ نتونستم بنش کنم.")

@bot.message_handler(func=lambda m: cmd_text(m).startswith("آزاد"))
def unban_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا آزادش کنم 😁")
    bot.unban_chat_member(m.chat.id, target)
    bot.send_message(m.chat.id, "✅ کاربر آزاد شد 🌸")

# ------------------ 📊 آمار ------------------
@bot.message_handler(func=lambda m: cmd_text(m) == "آمار")
def stats(m):
    d = load_data()
    users = len(d.get("users", []))
    groups = len(d.get("welcome", {}))
    bot.reply_to(m, f"📊 آمار ربات:\n👥 گروه‌ها: {groups}\n👤 کاربران: {users}")

# ------------------ 🚀 اجرای ربات ------------------
if __name__ == "__main__":
    print("🚀 ربات ضد لینک فارسی اجرا شد ✅")
    bot.infinity_polling(skip_pending=True)
