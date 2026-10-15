import os
import telebot
from main import convert_image

TOKEN = "8474006270:AAFIGxrQEA5pxj1GWEtH4itc-tZCx1HasQo"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي أي صورة وسأحولها فوراً إلى ملف .xavatar جاهز للبلايستيشن.")

@bot.message_handler(content_types=['photo', 'document'])
def handle_image(message):
    try:
        bot.reply_to(message, "⏳ جاري معالجة الصورة وتحويلها إلى ملف .xavatar...")
        
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
        else:
            file_info = bot.get_file(message.document.file_id)
            
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = "temp_input.png"
        output_path = "avatar.xavatar"
        
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        convert_image(input_path, output_path)
        
        with open(output_path, 'rb') as doc:
            bot.send_document(message.chat.id, doc, caption="✅ تفضل ملف الـ xavatar جاهز للاستخدام على جهازك!")
            
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()