import os
import json
from pathlib import Path
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from main import convert_image

# --- الإعدادات الأساسية ---
TOKEN = "8474006270:AAFIGxrQEA5pxj1GWEtH4itc-tZCx1HasQo"  # ضع توكن البوت الخاص بك هنا
ADMIN_ID = 6949720185          # استبدل هذا الرقم بالآيدي (معرف الحساب) الخاص بك كأدمن
bot = telebot.TeleBot(TOKEN)

# ملفات تخزين البيانات محلياً
USERS_FILE = "users.json"
BLOCKED_FILE = "blocked.json"
STATS_FILE = "stats.json"
SETTINGS_FILE = "settings.json"

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


# --- أوامر لوحة الإدارة ---

# 1. إحصائيات الاستخدام الحية
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    users = load_json(USERS_FILE, [])
    blocked = load_json(BLOCKED_FILE, [])
    stats = load_json(STATS_FILE, {"success": 0, "failed": 0})
    
    text = (
        "📊 **لوحة إحصائيات البوت:**\n\n"
        f"👥 إجمالي المستخدمين: {len(users)}\n"
        f"✅ عمليات التحويل الناجحة: {stats['success']}\n"
        f"❌ عمليات التحويل الفاشلة: {stats['failed']}\n"
        f"🚫 عدد المحظورين: {len(blocked)}"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

# 2. نظام الإذاعة (البث الجماعي)
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text_to_broadcast = message.text.replace("/broadcast", "").strip()
    if not text_to_broadcast:
        bot.reply_to(message, "⚠️ أكتب النص بعد الأمر هكذا:\n`/broadcast رسالتك هنا`", parse_mode="Markdown")
        return
    
    users = load_json(USERS_FILE, [])
    success_count = 0
    failed_count = 0
    
    for uid in users:
        try:
            bot.send_message(uid, f"📢 **إشعار من الإدارة:**\n\n{text_to_broadcast}", parse_mode="Markdown")
            success_count += 1
        except Exception:
            failed_count += 1
            
    bot.reply_to(message, f"✅ تمت الإذاعة بنجاح!\n- وصل إلى: {success_count} مستخدم\n- فشل الإرسال لـ: {failed_count} مستخدم")

# 3. إدارة الحظر اليدوية بالأوامر
@bot.message_handler(commands=['block'])
def block_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا: `/block [User_ID]`", parse_mode="Markdown")
        return
    
    target_id = int(parts[1])
    blocked = load_json(BLOCKED_FILE, [])
    if target_id not in blocked:
        blocked.append(target_id)
        save_json(BLOCKED_FILE, blocked)
        bot.reply_to(message, f"🚫 تم حظر المستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ المستخدم محظور مسبقاً.")

@bot.message_handler(commands=['unblock'])
def unblock_user_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استعمل الأمر هكذا: `/unblock [User_ID]`", parse_mode="Markdown")
        return
    
    target_id = int(parts[1])
    blocked = load_json(BLOCKED_FILE, [])
    if target_id in blocked:
        blocked.remove(target_id)
        save_json(BLOCKED_FILE, blocked)
        bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم `{target_id}`.", parse_mode="Markdown")
    else:
        bot.reply_to(message, "⚠️ المستخدم ليس في قائمة الحظر.")

# 4. وضع الصيانة
@bot.message_handler(commands=['maintenance'])
def toggle_maintenance(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    settings = load_json(SETTINGS_FILE, {"maintenance": False})
    settings["maintenance"] = not settings.get("maintenance", False)
    save_json(SETTINGS_FILE, settings)
    
    status = "مفعل 🛠️ (البوت متوقف للمستخدمين)" if settings["maintenance"] else "معطل 🟢 (البوت يعمل طبيعياً)"
    bot.reply_to(message, f"⚙️ أصبحت حالة وضع الصيانة الآن:\n{status}")


# --- استقبال الأزرار الشفافة للأدمن (حظر / فك حظر) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(('block_', 'unblock_')))
def handle_admin_buttons(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ عذراً، هذا الأمر للمشرف فقط.")
        return
    
    action, target_id_str = call.data.split('_')
    target_id = int(target_id_str)
    
    blocked = load_json(BLOCKED_FILE, [])
    
    if action == 'block':
        if target_id not in blocked:
            blocked.append(target_id)
            save_json(BLOCKED_FILE, blocked)
            bot.answer_callback_query(call.id, f"تم حظر المستخدم {target_id} بنجاح 🚫")
            bot.edit_message_caption(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                caption=call.message.caption + "\n\n**[ 🚫 تم حظر هذا المستخدم ]**", 
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "المستخدم محظور مسبقاً.")
            
    elif action == 'unblock':
        if target_id in blocked:
            blocked.remove(target_id)
            save_json(BLOCKED_FILE, blocked)
            bot.answer_callback_query(call.id, f"تم إلغاء حظر المستخدم {target_id} ✅")
            bot.edit_message_caption(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                caption=call.message.caption + "\n\n**[ ✅ تم إلغاء حظر هذا المستخدم ]**", 
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "المستخدم ليس في قائمة الحظر.")


# --- تشغيل البوت واستقبال الصور من المستخدمين ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    track_user(user_id)
    bot.send_message(message.chat.id, "أهلاً بك! أرسل صورتك الآن لتحويلها إلى `.xavatar` لجهاز PS4 🎮")

@bot.message_handler(content_types=['photo', 'document'])
def handle_image(message):
    user = message.from_user
    user_id = user.id
    
    # تتبع المستخدم
    track_user(user_id)
    
    # التحقق مما إذا كان المستخدم محظوراً
    blocked = load_json(BLOCKED_FILE, [])
    if user_id in blocked:
        bot.reply_to(message, "❌ عذراً، أنت محظور من استخدام هذا البوت.")
        return
        
    # التحقق من وضع الصيانة (يستثنى المشرف)
    if is_maintenance_mode() and user_id != ADMIN_ID:
        bot.reply_to(message, "🛠️ البوت خاضع للصيانة المؤقتة حالياً، يرجى المحاولة لاحقاً.")
        return
    
    try:
        processing_msg = bot.reply_to(message, "⏳ جاري معالجة الصورة وتحويلها...")
        
        # استلام الصورة
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
        
        # عملية التحويل باستخدام main.py
        convert_image(str(input_path), str(output_path))
        add_conversion_stat(success=True)
        
        # إرسال الملف الناتج للمستخدم
        with open(output_path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ تفضل ملف الـ xavatar الخاص بك جاهزاً!")
            
        bot.delete_message(message.chat.id, processing_msg.message_id)
        
        # إرسال تفاصيل الصورة والمستخدم إلى الأدمن مع أزرار الحظر والفك
        username_str = f"@{user.username}" if user.username else "بدون يوزر"
        admin_caption = (
            "📥 **عملية تحويل جديدة:**\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🔗 اليوزر: {username_str}\n"
            f"🆔 الآيدي: `{user_id}`"
        )
        
        markup = InlineKeyboardMarkup()
        btn_block = InlineKeyboardButton("🚫 حظر المستخدم", callback_data=f"block_{user_id}")
        btn_unblock = InlineKeyboardButton("✅ إلغاء الحظر", callback_data=f"unblock_{user_id}")
        markup.add(btn_block, btn_unblock)
        
        if original_photo_id:
            bot.send_photo(ADMIN_ID, original_photo_id, caption=admin_caption, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, f"{admin_caption}\n(أرسل مستنداً وليس صورة مباشرة)", reply_markup=markup, parse_mode="Markdown")
            
        # تنظيف الملفات المؤقتة
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        
    except Exception as e:
        add_conversion_stat(success=False)
        bot.reply_to(message, f"❌ حدث خطأ أثناء عملية المعالجة:\n`{e}`", parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot is running successfully with complete Admin Panel...")
    bot.infinity_polling()
