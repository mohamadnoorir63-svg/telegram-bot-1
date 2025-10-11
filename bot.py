# -*- coding: utf-8 -*-
import os
import json
import time
import telebot
import jdatetime
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN")
SUDO_ID = int(os.environ.get("SUDO_ID", "0"))
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def cmd_text(m):
    return (getattr(m, "text", "") or "").strip().lower()

def is_admin(chat_id, uid):
    try:
        st = bot.get_chat_member(chat_id, uid).status
        return st in ["administrator", "creator"]
    except:
        return False

def is_sudo(uid):
    return uid == SUDO_ID

def shamsi_date():
    return jdatetime.datetime.now().strftime("%Y/%m/%d")

def shamsi_time():
    return jdatetime.datetime.now().strftime("%H:%M:%S")

# ======================== شروع دستورات ========================

@bot.message_handler(func=lambda m: cmd_text(m) == "آمار")
def stats(m):
    d = load_data()
    users = len(d.get("users", []))
    groups = len(d.get("groups", []))
    bot.reply_to(m, f"📊 آمار کلی:\n👥 گروه‌ها: {groups}\n👤 کاربران: {users}")

@bot.message_handler(func=lambda m: cmd_text(m) == "ساعت")
def saat(m):
    bot.reply_to(m, f"🕓 {shamsi_time()} - {shamsi_date()}")

@bot.message_handler(func=lambda m: cmd_text(m) == "لینک گروه")
def group_link(m):
    try:
        link = bot.export_chat_invite_link(m.chat.id)
        bot.reply_to(m, f"🔗 لینک گروه:\n{link}")
    except:
        bot.reply_to(m, "⚠️ من اجازه ساخت لینک ندارم.")# ================= 🔒 سیستم ضد لینک =================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def anti_link(m):
    text = m.text or ""
    if any(x in text for x in ["http", "www.", "t.me/", "telegram.me/"]):
        try:
            bot.delete_message(m.chat.id, m.id)
            bot.send_message(m.chat.id, f"🚫 ارسال لینک در گروه ممنوع است!\n👤 {m.from_user.first_name}")
        except:
            pass

# ================= 👋 خوش‌آمدگویی =================

@bot.message_handler(content_types=["new_chat_members"])
def welcome(m):
    user = m.new_chat_members[0]
    name = user.first_name
    bot.send_message(m.chat.id, f"🌸 خوش اومدی {name}!\nلطفاً قوانین گروه رو رعایت کن 🌺")

# ================= ⚙️ مدیریت ادمین =================

@bot.message_handler(func=lambda m: cmd_text(m).startswith("افزودن مدیر"))
def add_admin(m):
    if not is_sudo(m.from_user.id):
        return
    if not m.reply_to_message:
        return bot.reply_to(m, "⚠️ روی پیام کاربر ریپلای کن تا مدیرش کنم.")
    target = m.reply_to_message.from_user.id
    d = load_data()
    gid = str(m.chat.id)
    d.setdefault("admins", {}).setdefault(gid, [])
    if target not in d["admins"][gid]:
        d["admins"][gid].append(target)
        save_data(d)
        bot.reply_to(m, f"✅ کاربر {target} مدیر شد.")
    else:
        bot.reply_to(m, "ℹ️ این کاربر قبلاً مدیر بوده.")

@bot.message_handler(func=lambda m: cmd_text(m).startswith("حذف مدیر"))
def del_admin(m):
    if not is_sudo(m.from_user.id):
        return
    if not m.reply_to_message:
        return bot.reply_to(m, "⚠️ روی پیام کاربر ریپلای کن تا از مدیرها حذف بشه.")
    target = m.reply_to_message.from_user.id
    d = load_data()
    gid = str(m.chat.id)
    if target in d.get("admins", {}).get(gid, []):
        d["admins"][gid].remove(target)
        save_data(d)
        bot.reply_to(m, f"🗑️ مدیر {target} حذف شد.")
    else:
        bot.reply_to(m, "❌ این کاربر مدیر نیست.")

# ================= 🚫 فیلتر کلمات =================

@bot.message_handler(func=lambda m: cmd_text(m).startswith("افزودن فیلتر "))
def add_filter(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    word = cmd_text(m).replace("افزودن فیلتر ", "").strip()
    if not word:
        return bot.reply_to(m, "⚠️ لطفاً کلمه‌ای برای فیلتر وارد کن.")
    d = load_data()
    gid = str(m.chat.id)
    d.setdefault("filters", {}).setdefault(gid, [])
    if word in d["filters"][gid]:
        return bot.reply_to(m, "ℹ️ این کلمه از قبل فیلتر شده.")
    d["filters"][gid].append(word)
    save_data(d)
    bot.reply_to(m, f"🚫 کلمه <b>{word}</b> فیلتر شد.", parse_mode="HTML")

@bot.message_handler(func=lambda m: cmd_text(m).startswith("حذف فیلتر "))
def del_filter(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    word = cmd_text(m).replace("حذف فیلتر ", "").strip()
    d = load_data()
    gid = str(m.chat.id)
    if word not in d.get("filters", {}).get(gid, []):
        return bot.reply_to(m, "❌ این کلمه در فیلتر نیست.")
    d["filters"][gid].remove(word)
    save_data(d)
    bot.reply_to(m, f"✅ کلمه <b>{word}</b> از فیلتر حذف شد.", parse_mode="HTML")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def filter_check(m):
    d = load_data()
    gid = str(m.chat.id)
    filters = d.get("filters", {}).get(gid, [])
    if not filters or is_admin(m.chat.id, m.from_user.id):
        return
    text = cmd_text(m)
    for w in filters:
        if w in text:
            try:
                bot.delete_message(m.chat.id, m.id)
                bot.send_message(m.chat.id, f"🚫 کلمه <b>{w}</b> فیلتر شده است!", parse_mode="HTML")
                break
            except:
                pass

# ================= ✅ پایان =================

print("🚀 ربات ضد لینک فارسی اجرا شد ✅")
bot.infinity_polling(timeout=30, long_polling_timeout=10)
