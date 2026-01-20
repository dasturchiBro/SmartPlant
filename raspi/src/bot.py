import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from . import config

logger = logging.getLogger(__name__)

class SmartPlantBot:
    def __init__(self, db_manager, ingestor):
        self.db_manager = db_manager
        self.ingestor = ingestor
        self.application = None
        self.watering_duration = 3 # Default 3 seconds

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🌱 Assalomu alaykum, men Smart Plant Botman! 🌿\nO'simlik holatini tekshirish uchun /status buyrug'idan foydalaning."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "/start - Botni ishga tushirish\n"
            "/status - O'simlik holatini tekshirish\n"
            "/vaqt <sekund> - Sug'orish vaqtini sozlash (masalan/ex: /vaqt 5)\n"
            "/help - Yordam"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

    async def set_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if context.args:
                seconds = int(context.args[0])
                if 1 <= seconds <= 10:
                    self.watering_duration = seconds
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Sug'orish vaqti {seconds} soniyaga o'zgartirildi.")
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Iltimos, 1 dan 10 gacha son kiriting.")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"ℹ️ Hozirgi sug'orish vaqti: {self.watering_duration} soniya.\nO'zgartirish uchun: /vaqt 5")
        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Iltimos, raqam kiriting.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Fetch latest data
            data = self.db_manager.get_recent_data(limit=1)
            
            if data:
                # database.py returns a list of tuples: 
                # (timestamp, soil_moisture, temperature, humidity, light_intensity, temperature_lm35, water_level)
                latest = data[0]
                
                # Unpack tuple
                timestamp_val = latest[0]
                soil = latest[1]
                temp_dht = latest[2]
                humidity = latest[3]
                light_raw = latest[4]
                temp_lm35 = latest[5] 
                water_level = latest[6] if len(latest) > 6 else 0
                
                # Calculate Average Temperature (Matches Arduino Logic)
                if temp_lm35 and temp_lm35 > 0:
                    temp_final = (temp_dht + temp_lm35) / 2.0
                else:
                    temp_final = temp_dht

                # Interpret Light Value
                if light_raw < 300:
                    light_text = "Qorong'u 🌙"
                else:
                    light_text = "Yorug' ☀️"

                # Format timestamp
                import datetime
                dt_object = datetime.datetime.fromtimestamp(timestamp_val)
                time_str = dt_object.strftime('%Y-%m-%d %H:%M:%S')

                # Basic assessment
                # Interpret Soil Status (Consistent with Arduino: < 800 is Wet/Nam)
                soil_limit = 800
                if soil < soil_limit:
                    soil_text = "Nam 🟢"
                    soil_advice = "\n✅ Tuproq namligi joyida!"
                else:
                    soil_text = "Quruq 🔴"
                    soil_advice = "\n⚠️ Tuproq QURUQ! Sug'orish kerak."

                status_msg = f"🌿 **O'simlik Holati** 🌿\n\n"
                status_msg += f"🕒 Vaqt: {time_str}\n"
                status_msg += f"💧 Tuproq: {soil_text}\n"
                status_msg += f"🌡️ Harorat: {temp_final:.1f}°C\n"
                status_msg += f"💧 Namlik: {humidity:.1f}%\n"
                status_msg += f"☀️ Yorug'lik: {light_text}\n"
                
                if water_level == 1:
                    status_msg += "🌊 Suv sathi: Yaxshi\n"
                else:
                    status_msg += "🚫 Suv sathi: PAST! (Bakni to'ldiring)\n"

                status_msg += soil_advice

                # Add Watering Button
                keyboard = [
                    [InlineKeyboardButton("💧 Suv quyish", callback_data='water_plant')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(chat_id=update.effective_chat.id, text=status_msg, reply_markup=reply_markup)
            else:
                 await context.bot.send_message(chat_id=update.effective_chat.id, text="Hali birinchi ma'lumot kelmadi... biroz kuting! ⏳")
        
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Holatni aniqlashda xatolik: {e}")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer() # Acknowledge the button click

        if query.data == 'water_plant':
             # Check Water Level first
             data = self.db_manager.get_recent_data(limit=1)
             if data:
                 latest = data[0]
                 water_level = latest[6] if len(latest) > 6 else 0
                 
                 if water_level == 1:
                     command = f"W{self.watering_duration}"
                     if self.ingestor.write_command(command):
                         await query.edit_message_text(text=f"💧 Sug'orilmoqda... ({self.watering_duration} soniya)")
                     else:
                         await query.edit_message_text(text="⚠️ Xatolik: Arduino bilan aloqa yo'q.")
                 else:
                     await query.edit_message_text(text="🚫 Bak bo'sh! Iltimos, oldin suv quying.")
             else:
                 await query.edit_message_text(text="⚠️ Ma'lumot yo'q, xavfsizlik uchun sug'orilmadi.")

    def run(self):
        """
        Runs the bot. Note: Application.run_polling() is blocking.
        For a script with other threads, we might need a different approach 
        or run this in its own thread/process.
        """
        if not config.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram Token not set. Bot will not start.")
            return

        self.application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        start_handler = CommandHandler('start', self.start)
        status_handler = CommandHandler('status', self.status)
        help_handler = CommandHandler('help', self.help_command)
        duration_handler = CommandHandler('vaqt', self.set_duration)
        button_handler = CallbackQueryHandler(self.button_handler)

        self.application.add_handler(start_handler)
        self.application.add_handler(status_handler)
        self.application.add_handler(help_handler)
        self.application.add_handler(duration_handler)
        self.application.add_handler(button_handler)

        logger.info("Starting Telegram Bot...")
        # run_polling is blocking, so we'll likely wrap this whole 'run' method in a thread in main.py
        self.application.run_polling()
