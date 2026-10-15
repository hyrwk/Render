import os
import json
import time
from pathlib import Path
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from main import convert_image

# --- الإعدادات الأساسية ---
TOKEN = "8474006270:AAFIGxrQEA5pxj1GWEtH4itc-tZCx1HasQo"
ADMIN_ID = 6949720185
bot = telebot.TeleBot(TOKEN)

# ملفات تخزين البيانات محلياً
USERS_FILE = "users.json"
BLOCKED_FILE = "blocked.json"
STATS_FILE = "stats.json"
SETTINGS_FILE = "settings.json"
USER_COOLDOWN = {}  
LAST_SENT_BACKUP_ID = None  

# --- دوال مساعدة لإدارة البيانات ---
def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def track_user(user_id):
    users = load_json(USERS_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)
        update_admin_users_backup()
        return True
    return False

def update_admin_users_backup():
    global LAST_SENT_BACKUP_ID
    if not os.path.exists(USERS_FILE):
        return
        
    try:
        if LAST_SENT_BACKUP_ID:
            try:
                bot.delete_message(ADMIN_ID, LAST_SENT_BACKUP_ID)
            except Exception:
                pass
        
        with open(USERS_FILE, 'rb') as f:
            sent_msg = bot.send_document(
                ADMIN_ID, 
                f, 
                caption="📂 **تحديث ملف المستخدمين (users.json):**\nانضم مستخدم جديد وتم تحديث الملف تلقائياً.",
                parse_mode="Markdown"
            )
            LAST_SENT_BACKUP_ID = sent_msg.message_id
    except Exception as e:
        print(f"Error sending backup: {e}")

def add_conversion_stat(success=True):
    stats = load_json(STATS_FILE, {"success": 0, "failed": 0})
    if success:
        stats["success"] += 1
    else:
        stats["failed"] += 1
    save_json(STATS_FILE, stats)

def is_maintenance_mode():
    settings = load_json(SETTINGS_FILE, {"maintenance": False})
    return settings.get("maintenance", False)


# --- أوامر الإدارة ---

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = load_json(USERS_FILE, [])
    blocked = load_json(BLOCKED_FILE, [])
    stats = load_json(STATS_FILE, {"success": 0, "failed": 0})
    
    text = (
        "📊 لوحة إحصائيات البوت:\n\n"
        f"👥 إجمالي المستخدمين: {len(users)}\n"
        f"✅ عمليات التحويل الناجحة: {stats['success']}\n"
        f"❌ عمليات التحويل الفاشلة: {stats['failed']}\n"
        f"🚫 عدد المحظورين: {len(blocked)}"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        return
    text_to_broadcast = message.text.replace("/broadcast", "").strip()
    if not text_to_broadcast:
        bot.reply_to(message, "⚠️ أكتب النص بعد الأمر هكذا:\n/broadcast رسالتك هنا")
        return
    
    users = load_json(USERS_FILE, [])
    success_count = 0
    failed_count = 0
    
    for uid in users:
        try:
            bot.send_message(uid, f"📢 إشعار من الإدارة:\n\n{text_to_broadcast}")
            success_count += 1
        except Exception:
            failed_count += 1
            
    bot.reply_to(message, f"✅ تمت الإذاعة بنجاح!\n- وصل إلى: {success_count} مستخدم\n- فشل الإرسال لـ: {failed_count} مستخدم")

@bot.message_handler(commands=['block'])
def block_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا:\n`/block [User_ID]`", parse_mode="Markdown")
        return
    try:
        target_id = int(parts[1])
        blocked = load_json(BLOCKED_FILE, [])
        if target_id not in blocked:
            blocked.append(target_id)
            save_json(BLOCKED_FILE, blocked)
            bot.reply_to(message, f"🚫 تم حظر المستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ المستخدم محظور مسبقاً.")
    except ValueError:
        bot.reply_to(message, "⚠️ يرجى كتابة آيدي صحيح للمستخدم.")

@bot.message_handler(commands=['unblock'])
def unblock_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا:\n`/unblock [User_ID]`", parse_mode="Markdown")
        return
    try:
        target_id = int(parts[1])
        blocked = load_json(BLOCKED_FILE, [])
        if target_id in blocked:
            blocked.remove(target_id)
            save_json(BLOCKED_FILE, blocked)
            bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم `{target_id}`.", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ المستخدم ليس في قائمة الحظر.")
    except ValueError:
        bot.reply_to(message, "⚠️ يرجى كتابة آيدي صحيح للمستخدم.")

@bot.message_handler(commands=['reply'])
def reply_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا:\n`/reply [User_ID] [الرد هنا]`", parse_mode="Markdown")
        return
    try:
        target_id = int(parts[1])
        reply_text = parts[2]
        bot.send_message(target_id, f"📬 **رد من إدارة البوت:**\n\n{reply_text}", parse_mode="Markdown")
        bot.reply_to(message, f"✅ تم إرسال الرد إلى المستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ فشل إرسال الرد: {e}")

@bot.message_handler(commands=['maintenance'])
def toggle_maintenance(message):
    if message.from_user.id != ADMIN_ID:
        return
    settings = load_json(SETTINGS_FILE, {"maintenance": False})
    settings["maintenance"] = not settings.get("maintenance", False)
    save_json(SETTINGS_FILE, settings)
    status = "مفعل 🛠️ (البوت متوقف للمستخدمين)" if settings["maintenance"] else "معطل 🟢 (البوت يعمل طبيعياً)"
    bot.reply_to(message, f"⚙️ أصبحت حالة وضع الصيانة الآن:\n{status}")


# --- استقبال الأوامر والنصوص والصور ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    user_id = user.id
    track_user(user_id)
    
    markup = InlineKeyboardMarkup(row_width=1)
    btn_tutorial = InlineKeyboardButton("📺 شرح طريقة التركيب", url="https://youtu.be/jJv7YxHRirU?si=16WJMn0vcY0SB8QG")
    markup.add(btn_tutorial)
    
    welcome_text = (
        f"أهلاً بك يا {user.first_name} في بوت تحويل صور الأفاتار لـ PS4 🎮\n\n"
        "📥 أرسل صورتك الآن لتتم معالجتها بسرعة.\n"
        "🛠️ للإبلاغ عن مشكلة أو مراسلة الإدارة، أرسل الأمر:\n"
        "/report متبوعاً برسالتك (مثال:\n`/report عندي مشكلة في التحويل`)"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report_command(message):
    user_id = message.from_user.id
    text_parts = message.text.replace("/report", "").strip()
    
    if not text_parts:
        bot.reply_to(message, "⚠️ يرجى كتابة رسالتك أو مشكلتك بعد الأمر هكذا:\n`/report رسالتك هنا`", parse_mode="Markdown")
        return
        
    user = message.from_user
    bot.reply_to(message, "✅ تم إرسال مشكلتك إلى الإدارة بنجاح، سيتم الرد عليك قريباً.")
    
    username_str = f"@{user.username}" if user.username else "بدون يوزر"
    admin_msg = (
        "🚨 **شكوى أو مشكلة جديدة:**\n"
        f"👤 الاسم: {user.first_name}\n"
        f"🔗 اليوزر: {username_str}\n"
        f"🆔 الآيدي: `{user_id}`\n\n"
        f"💬 النص:\n{text_parts}\n\n"
        "💡 **للرد على المستخدم:**\n"
        f"`/reply {user_id} ردك هنا`"
    )
    
    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'document'])
def handle_image(message):
    user = message.from_user
    user_id = user.id
    
    track_user(user_id)
    
    current_time = time.time()
    if user_id in USER_COOLDOWN and user_id != ADMIN_ID:
        elapsed = current_time - USER_COOLDOWN[user_id]
        if elapsed < 3:
            bot.reply_to(message, "⏳ يرجى الانتظار 3 ثوانٍ قبل إرسال صورة أخرى لمنع الضغط على السيرفر.")
            return
    USER_COOLDOWN[user_id] = current_time
    
    blocked = load_json(BLOCKED_FILE, [])
    if user_id in blocked:
        bot.reply_to(message, "❌ عذراً، أنت محظور من استخدام هذا البوت.")
        return
        
    if is_maintenance_mode() and user_id != ADMIN_ID:
        bot.reply_to(message, "🛠️ البوت خاضع للصيانة المؤقتة حالياً، يرجى المحاولة لاحقاً.")
        return
    
    try:
        processing_msg = bot.reply_to(message, "⏳ جاري معالجة الصورة وتحويلها...")
        
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            original_photo_id = message.photo[-1].file_id
        else:
            file_info = bot.get_file(message.document.file_id)
            original_photo_id = None
            
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = Path("temp_input.png")
        output_path = Path("avatar.xavatar")
        input_path.write_bytes(downloaded_file)
        
        convert_image(str(input_path), str(output_path))
        add_conversion_stat(success=True)
        
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تفضل ملف الـ xavatar الخاص بك جاهزاً!")
            
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        username_str = f"@{user.username}" if user.username else "بدون يوزر"
        admin_caption = (
            "📥 عملية تحويل جديدة:\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🔗 اليوزر: {username_str}\n"
            f"🆔 الآيدي: `{user_id}`\n\n"
            "🛠️ **أوامر الإدارة السريعة:**\n"
            f"• للحظر: `/block {user_id}`\n"
            f"• لفك الحظر: `/unblock {user_id}`"
        )
        
        if original_photo_id:
            bot.send_photo(ADMIN_ID, original_photo_id, caption=admin_caption, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, f"{admin_caption}\n(أرسل مستنداً وليس صورة مباشرة)", parse_mode="Markdown")
            
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        
    except Exception as e:
        add_conversion_stat(success=False)
        bot.reply_to(message, f"❌ حدث خطأ أثناء عملية المعالجة:\n{e}")

if __name__ == "__main__":
    print("Bot is running successfully with text commands only...")
    bot.infinity_polling()
