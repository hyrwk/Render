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
USER_COOLDOWN = {}  # لتتبع التوقيت لمنع السبام (كل 3 ثوانٍ)
LAST_SENT_BACKUP_ID = None  # لتتبع ومعرفة رسالة ملف التخزين القديمة لحذفها

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


# --- لوحة الإدارة والأوامر ---

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
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا: /block [User_ID]")
        return
    target_id = int(parts[1])
    blocked = load_json(BLOCKED_FILE, [])
    if target_id not in blocked:
        blocked.append(target_id)
        save_json(BLOCKED_FILE, blocked)
        bot.reply_to(message, f"🚫 تم حظر المستخدم {target_id} بنجاح.")
    else:
        bot.reply_to(message, "⚠️ المستخدم محظور مسبقاً.")

@bot.message_handler(commands=['unblock'])
def unblock_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا: /unblock [User_ID]")
        return
    target_id = int(parts[1])
    blocked = load_json(BLOCKED_FILE, [])
    if target_id in blocked:
        blocked.remove(target_id)
        save_json(BLOCKED_FILE, blocked)
        bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم {target_id}.")
    else:
        bot.reply_to(message, "⚠️ المستخدم ليس في قائمة الحظر.")

@bot.message_handler(commands=['maintenance'])
def toggle_maintenance(message):
    if message.from_user.id != ADMIN_ID:
        return
    settings = load_json(SETTINGS_FILE, {"maintenance": False})
    settings["maintenance"] = not settings.get("maintenance", False)
    save_json(SETTINGS_FILE, settings)
    status = "مفعل 🛠️ (البوت متوقف للمستخدمين)" if settings["maintenance"] else "معطل 🟢 (البوت يعمل طبيعياً)"
    bot.reply_to(message, f"⚙️ أصبحت حالة وضع الصيانة الآن:\n{status}")


# --- معالجة الأزرار الشفافة ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    user_id = call.from_user.id
    
    # 1. زر الإبلاغ عن مشكلة
    if call.data == 'report_issue':
        bot.answer_callback_query(call.id, "أرسل رسالتك الآن ✍️")
        bot.send_message(user_id, "✍️ أرسل رسالتك الآن موضحة مشكلتك، وسيتم تحويلها مباشرة إلى الإدارة للرد عليك بأقرب وقت:")
        bot.register_next_step_handler_by_chat_id(user_id, receive_user_issue)
        return

    # 2. أزرار حظر وإلغاء حظر المستخدمين (للأدمن)
    if call.data.startswith(('block_', 'unblock_')):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ عذراً، هذا الأمر للمشرف فقط.")
            return
        
        action, target_id_str = call.data.split('_')
        target_id = int(target_id_str)
        blocked = load_json(BLOCKED_FILE, [])
        
        if action == 'block':
            if target_id not in blocked:
                blocked.append(target_id)
                save_json(BLOCKED_FILE, blocked)
                bot.answer_callback_query(call.id, f"تم حظر المستخدم {target_id} 🚫")
                try:
                    bot.edit_message_caption(
                        chat_id=call.message.chat.id, 
                        message_id=call.message.message_id, 
                        caption=call.message.caption + "\n\n[ 🚫 تم حظر هذا المستخدم ]"
                    )
                except Exception:
                    pass
        elif action == 'unblock':
            if target_id in blocked:
                blocked.remove(target_id)
                save_json(BLOCKED_FILE, blocked)
                bot.answer_callback_query(call.id, f"تم إلغاء حظر المستخدم {target_id} ✅")
                try:
                    bot.edit_message_caption(
                        chat_id=call.message.chat.id, 
                        message_id=call.message.message_id, 
                        caption=call.message.caption + "\n\n[ ✅ تم إلغاء حظر هذا المستخدم ]"
                    )
                except Exception:
                    pass
        return

    # 3. أزرار الرد السريع على شكاوى المستخدمين (للأدمن)
    if call.data.startswith('reply_to_'):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ للمشرف فقط.")
            return
        target_uid = int(call.data.replace('reply_to_', ''))
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_ID, f"✍️ أكتب ردك الآن للمستخدم صاحب الآيدي: `{target_uid}`", parse_mode="Markdown")
        bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda msg: send_admin_reply_to_user(msg, target_uid))
        return

def receive_user_issue(message):
    user = message.from_user
    user_id = user.id
    issue_text = message.text
    
    if not issue_text:
        bot.reply_to(message, "⚠️ يرجى إرسال رسالة نصية بالمشكلة.")
        return
        
    bot.reply_to(message, "✅ تم إرسال مشكلتك إلى الإدارة بنجاح، سيتم الرد عليك قريباً.")
    
    username_str = f"@{user.username}" if user.username else "بدون يوزر"
    admin_msg = (
        "🚨 **شكوى أو مشكلة جديدة:**\n"
        f"👤 الاسم: {user.first_name}\n"
        f"🔗 اليوزر: {username_str}\n"
        f"🆔 الآيدي: {user_id}\n\n"
        f"💬 النص:\n{issue_text}"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💬 رد على المستخدم", callback_data=f"reply_to_{user_id}"))
    
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")

def send_admin_reply_to_user(message, target_uid):
    reply_text = message.text
    if not reply_text:
        bot.reply_to(message, "⚠️ الرد يجب أن يكون نصياً.")
        return
        
    try:
        bot.send_message(target_uid, f"📬 **رد من إدارة البوت:**\n\n{reply_text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ تم إرسال الرد إلى المستخدم بنجاح.")
    except Exception as e:
        bot.reply_to(message, f"❌ فشل إرسال الرد للمستخدم: {e}")


# --- استقبال الأوامر والصور ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    user_id = user.id
    track_user(user_id)
    
    markup = InlineKeyboardMarkup(row_width=1)
    btn_report = InlineKeyboardButton("🛠️ الإبلاغ عن مشكلة", callback_data="report_issue")
    btn_tutorial = InlineKeyboardButton("📺 شرح طريقة التركيب", url="https://youtu.be/jJv7YxHRirU?si=16WJMn0vcY0SB8QG")
    markup.add(btn_report, btn_tutorial)
    
    welcome_text = f"أهلاً بك يا {user.first_name} في بوت تحويل صور الأفاتار لـ PS4 🎮\nأرسل صورتك الآن لتتم معالجتها بسرعة."
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(content_types=['photo', 'document'])
def handle_image(message):
    user = message.from_user
    user_id = user.id
    
    track_user(user_id)
    
    # حماية من السبام (3 ثوانٍ)
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
            f"🆔 الآيدي: {user_id}"
        )
        
        markup = InlineKeyboardMarkup()
        btn_block = InlineKeyboardButton("🚫 حظر المستخدم", callback_data=f"block_{user_id}")
        btn_unblock = InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"unblock_{user_id}")
        markup.add(btn_block, btn_unblock)
        
        if original_photo_id:
            bot.send_photo(ADMIN_ID, original_photo_id, caption=admin_caption, reply_markup=markup)
        else:
            bot.send_message(ADMIN_ID, f"{admin_caption}\n(أرسل مستنداً وليس صورة مباشرة)", reply_markup=markup)
            
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        
    except Exception as e:
        add_conversion_stat(success=False)
        bot.reply_to(message, f"❌ حدث خطأ أثناء عملية المعالجة:\n{e}")

if __name__ == "__main__":
    print("Bot is running successfully with all features fully updated...")
    bot.infinity_polling()
