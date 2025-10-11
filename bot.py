# -*- coding: utf-8 -*-
# Persian AntiLink Manager - Full Persian Edition (part 1/2)
# نوشته شده برای محمد 👑 - سبک خودمونی
# اجرا روی Render یا Railway به عنوان worker

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

# ------------------ 🔒 سیستم قفل ------------------
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
    bot.reply_to(m, f"🔒 قفل {key} فعال شد، دیگه کسی نمی‌تونه اون نوع پیامو بفرسته.")

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

# ------------------ 🔗 حذف لینک‌ها ------------------
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
            warn = bot.send_message(m.chat.id, f"🚫 {m.from_user.first_name} لینک ممنوعه دیگه 😅")
            time.sleep(3)
            bot.delete_message(m.chat.id, warn.id)
        except:
            pass# ------------------ 🚫 بن / میوت / اخطار ------------------

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
    bot.reply_to(m, "⚠️ من ادمین نیستم یا اجازه‌ی محدود کردن ندارم 😅")
    return False

# 🚫 بن
@bot.message_handler(func=lambda m: cmd_text(m).startswith("بن"))
def ban_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return bot.reply_to(m, "فقط مدیرای گروه می‌تونن بن کنن 😎")
    if not bot_can_restrict(m):
        return

    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن روی پیام اون فرد تا بنش کنم 😁")
    if is_admin(m.chat.id, target) or is_sudo(target):
        return bot.reply_to(m, "😏 نمی‌تونی مدیر یا سودو رو بن کنی!")

    d = load_data()
    gid = str(m.chat.id)
    d["banned"].setdefault(gid, [])
    if target in d["banned"][gid]:
        return bot.reply_to(m, "این کاربر قبلاً بن شده بود 😅")
    d["banned"][gid].append(target)
    save_data(d)

    try:
        bot.ban_chat_member(m.chat.id, target)
        bot.send_message(m.chat.id, f"🚫 کاربر <a href='tg://user?id={target}'>بن شد</a> ❌", parse_mode="HTML")
    except:
        bot.reply_to(m, "نتونستم بنش کنم 😕 شاید ادمین نباشم.")

# ✅ آزاد از بن
@bot.message_handler(func=lambda m: cmd_text(m).startswith("آزاد"))
def unban_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return bot.reply_to(m, "فقط مدیر می‌تونه آزاد کنه 😁")
    if not bot_can_restrict(m):
        return

    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا از بن دربیارمش.")
    d = load_data()
    gid = str(m.chat.id)
    if target not in d["banned"].get(gid, []):
        return bot.reply_to(m, "این بنده خدا اصلاً بن نبود 😅")
    d["banned"][gid].remove(target)
    save_data(d)
    bot.unban_chat_member(m.chat.id, target)
    bot.send_message(m.chat.id, "✅ از بن دراومد 😄")

# 🔇 سکوت
@bot.message_handler(func=lambda m: cmd_text(m).startswith("ساکت"))
def mute_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    if not bot_can_restrict(m):
        return

    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا ساکتش کنم 😅")

    if is_admin(m.chat.id, target) or is_sudo(target):
        return bot.reply_to(m, "😏 نمی‌تونی مدیر یا سودو رو ساکت کنی.")

    d = load_data()
    gid = str(m.chat.id)
    d["muted"].setdefault(gid, [])
    if target in d["muted"][gid]:
        return bot.reply_to(m, "از قبل ساکت بود 😅")
    d["muted"][gid].append(target)
    save_data(d)
    bot.restrict_chat_member(m.chat.id, target, permissions=types.ChatPermissions(can_send_messages=False))
    bot.send_message(m.chat.id, f"🔇 کاربر <a href='tg://user?id={target}'>ساکت شد</a> 🤐", parse_mode="HTML")

# 🔊 آزاد از سکوت
@bot.message_handler(func=lambda m: cmd_text(m).startswith("بازکردن سکوت"))
def unmute_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    if not bot_can_restrict(m):
        return

    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا از سکوت دربیارمش 😅")

    d = load_data()
    gid = str(m.chat.id)
    if target not in d["muted"].get(gid, []):
        return bot.reply_to(m, "این کاربر ساکت نبود 😅")
    d["muted"][gid].remove(target)
    save_data(d)
    bot.restrict_chat_member(m.chat.id, target, permissions=types.ChatPermissions(can_send_messages=True))
    bot.send_message(m.chat.id, "🔊 سکوتش برداشته شد 😄")

# ⚠️ اخطار
@bot.message_handler(func=lambda m: cmd_text(m).startswith("اخطار"))
def warn_user(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    target = target_user(m)
    if not target:
        return bot.reply_to(m, "ریپلای کن تا اخطار بدم 😁")
    if is_admin(m.chat.id, target) or is_sudo(target):
        return bot.reply_to(m, "به مدیر یا سودو نمی‌تونم اخطار بدم 😅")

    d = load_data()
    gid = str(m.chat.id)
    d["warns"].setdefault(gid, {})
    d["warns"][gid][str(target)] = d["warns"][gid].get(str(target), 0) + 1
    count = d["warns"][gid][str(target)]
    save_data(d)

    msg = f"⚠️ کاربر اخطار شماره {count} گرفت."
    if count >= 3:
        try:
            bot.ban_chat_member(m.chat.id, target)
            msg += "\n🚫 بعد از ۳ اخطار، بن شد 😬"
            d["warns"][gid][str(target)] = 0
            save_data(d)
        except:
            msg += "\n⚠️ نتونستم بنش کنم."
    bot.send_message(m.chat.id, msg)

# ------------------ 🚫 فیلتر کلمات ------------------
@bot.message_handler(func=lambda m: cmd_text(m).startswith("افزودن فیلتر"))
def add_filter(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    parts = cmd_text(m).split(" ", 2)
    if len(parts) < 3:
        return bot.reply_to(m, "مثال: افزودن فیلتر فحش 😅")
    word = parts[2].strip()
    gid = str(m.chat.id)
    d = load_data()
    d["filters"].setdefault(gid, [])
    if word in d["filters"][gid]:
        return bot.reply_to(m, "این کلمه از قبل فیلتره 😅")
    d["filters"][gid].append(word)
    save_data(d)
    bot.reply_to(m, f"🚫 کلمه <b>{word}</b> فیلتر شد 👌", parse_mode="HTML")

@bot.message_handler(func=lambda m: cmd_text(m).startswith("حذف فیلتر"))
def del_filter(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    parts = cmd_text(m).split(" ", 2)
    if len(parts) < 3:
        return bot.reply_to(m, "مثال: حذف فیلتر فحش 😅")
    word = parts[2].strip()
    gid = str(m.chat.id)
    d = load_data()
    if word not in d.get("filters", {}).get(gid, []):
        return bot.reply_to(m, "این کلمه تو فیلتر نیست 😅")
    d["filters"][gid].remove(word)
    save_data(d)
    bot.reply_to(m, f"✅ کلمه <b>{word}</b> از فیلتر حذف شد.", parse_mode="HTML")

@bot.message_handler(func=lambda m: cmd_text(m) == "فیلترها")
def list_filters(m):
    gid = str(m.chat.id)
    d = load_data()
    lst = d.get("filters", {}).get(gid, [])
    if not lst:
        return bot.reply_to(m, "هیچ فیلتری نداری 😄")
    text = "\n".join([f"• {x}" for x in lst])
    bot.reply_to(m, f"🚫 لیست فیلترها:\n{text}", parse_mode="HTML")

@bot.message_handler(content_types=["text"])
def check_filter(m):
    d = load_data()
    gid = str(m.chat.id)
    if is_admin(m.chat.id, m.from_user.id) or is_sudo(m.from_user.id):
        return
    filters = d.get("filters", {}).get(gid, [])
    if not filters:
        return
    for word in filters:
        if word in cmd_text(m):
            try:
                bot.delete_message(m.chat.id, m.id)
                warn = bot.send_message(m.chat.id, f"🚫 کلمه '{word}' فیلتره {m.from_user.first_name} 😅")
                time.sleep(2)
                bot.delete_message(m.chat.id, warn.id)
            except:
                pass
            break

# ------------------ 📊 آمار و ادمین ------------------
@bot.message_handler(func=lambda m: cmd_text(m) == "آمار")
def stats(m):
    if not (is_admin(m.chat.id, m.from_user.id) or is_sudo(m.from_user.id)):
        return
    d = load_data()
    users = len(set(d.get("users", [])))
    groups = len(d.get("welcome", {}))
    bot.reply_to(m, f"📊 آمار کلی ربات:\n👤 کاربران: {users}\n👥 گروه‌ها: {groups}")

@bot.message_handler(func=lambda m: cmd_text(m) == "ایدی")
def show_id(m):
    bot.reply_to(m, f"🆔 آیدی شما: <code>{m.from_user.id}</code>", parse_mode="HTML")

# ------------------ 🚀 اجرای مداوم ------------------
if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except:
        pass
    print("🚀 ربات ضد لینک فارسی روشن شد 😎")
    bot.infinity_polling(skip_pending=True)
