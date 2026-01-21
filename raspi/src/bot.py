import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from . import config

logger = logging.getLogger(__name__)

class SmartPlantBot:
    def __init__(self, db_manager, ingestor, automation_controller=None):
        self.db_manager = db_manager
        self.ingestor = ingestor
        self.automation_controller = automation_controller
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command with button menu."""
        keyboard = [
            [InlineKeyboardButton("\U0001F4CA Holat ko'rish", callback_data='show_status')],
            [InlineKeyboardButton("\U0001F4A7 Suv quyish", callback_data='water_plant')],
            [InlineKeyboardButton("\u2699\ufe0f Sozlamalar", callback_data='show_settings')],
            [InlineKeyboardButton("\u2753 Yordam", callback_data='show_help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\U0001F331 *Assalomu alaykum!* \U0001F33F\n\nMen Smart Plant Botman. O'simligingizni nazorat qilishda yordam beraman.\n\nQuyidagi tugmalardan foydalaning:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command showing all available commands."""
        help_text = (
            "\U0001F4D6 *Buyruqlar ro'yxati:*\n\n"
            "/start - Botni ishga tushirish\n"
            "/holat - O'simlik holatini ko'rish\n"
            "/suv - Sug'orish\n"
            "/sozlamalar - Sozlamalarni ko'rish\n\n"
            "*Chegara sozlash:*\n"
            "/tuproq_chegara <qiymat> (yoki /tuproqchegara)\n"
            "/fan_harorat <qiymat> (yoki /fanharorat)\n"
            "/isitgich_harorat <qiymat> (yoki /isitgichharorat)\n\n"
            "*Avtomatik rejim:*\n"
            "/avto_suv <on/off> (yoki /avtowater)\n"
            "/avto_fan <on/off> (yoki /autofan)\n"
            "/avto_isitgich <on/off> (yoki /autoheater)\n\n"
            "/yordam - Bu yordam\n"
            "/debug - Diagnostika (Raqamlarni ko'rish)"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=help_text,
            parse_mode='Markdown'
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display detailed plant status in Uzbek."""
        try:
            data = self.db_manager.get_recent_data(limit=1)
            
            if data:
                latest = data[0]
                # Unpack: timestamp, soil1, soil2, soil3, soil_avg, temp, hum, light, water_level, fan_status, heater_status
                timestamp = latest[0]
                soil1 = latest[1]
                soil2 = latest[2]
                soil3 = latest[3]
                soil_avg = latest[4]
                temp = latest[5]
                hum = latest[6]
                light = latest[7]
                water_level = latest[8]
                fan_status = latest[9]
                heater_status = latest[10]
                
                # Format timestamp
                import datetime
                dt = datetime.datetime.fromtimestamp(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Interpret soil moisture for each sensor
                def interpret_soil(value):
                    if value < 200:
                        return "Juda nam \U0001F4A7"
                    elif value < 250:
                        return "Nam \U0001F7E2"
                    elif value < 300:
                        return "Quruq \U0001F7E1"
                    else:
                        return "Juda quruq \U0001F534"
                
                soil1_status = interpret_soil(soil1)
                soil2_status = interpret_soil(soil2)
                soil3_status = interpret_soil(soil3)
                
                # Temperature advice
                if temp < 15:
                    temp_advice = "\n\u2744\ufe0f Harorat past!"
                elif temp > 30:
                    temp_advice = "\n\U0001F525 Harorat baland!"
                else:
                    temp_advice = "\n\u2705 Harorat yaxshi"
                
                # Build status message
                status_msg = f"\U0001F33F *O'simlik Holati* \U0001F33F\n\n"
                status_msg += f"\U0001F552 *Vaqt:* {time_str}\n\n"
                
                status_msg += f"\U0001F4A7 *Tuproq namligi:*\n"
                status_msg += f"  Sensor 1: {soil1} - {soil1_status}\n"
                status_msg += f"  Sensor 2: {soil2} - {soil2_status}\n"
                status_msg += f"  Sensor 3: {soil3} - {soil3_status}\n"
                status_msg += f"  O'rtacha: {soil_avg}\n\n"
                
                status_msg += f"🌡️ *Harorat:* {temp:.1f}°C{temp_advice}\n"
                status_msg += f"💨 *Namlik:* {hum:.1f}%\n\n"
                
                # Water tank status
                if water_level == 1:
                    status_msg += "🌊 *Suv baki:* To'liq \u2705\n"
                else:
                    status_msg += "\U0001F6AB *Suv baki:* Bo'sh (To'ldiring!) \u26A0\n"
                
                # Fan and heater status
                status_msg += f"\U0001F300 *Fan:* {'Yoniq \U0001F7E2' if fan_status else 'O\'chiq \u26AA'}\n"
                status_msg += f"\U0001F525 *Isitgich:* {'Yoniq \U0001F534' if heater_status else 'O\'chiq \u26AA'}\n"
                
                # Add action buttons
                keyboard = [
                    [InlineKeyboardButton("\u267b\ufe0f Yangilash", callback_data='show_status')],
                    [InlineKeyboardButton("\U0001F4A7 Suv quyish", callback_data='water_plant')],
                    [InlineKeyboardButton("\u2699\ufe0f Sozlamalar", callback_data='show_settings')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=status_msg,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="\u231b Hali ma'lumot kelmadi... biroz kuting!"
                )
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"\u26A0 Xatolik yuz berdi: {e}"
            )

    async def suv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual watering command."""
        try:
            # Check water level and water plant
            data = self.db_manager.get_recent_data(limit=1)
            if data:
                latest = data[0]
                water_level = latest[8]
                
                if water_level == 1:
                    duration = int(self.db_manager.get_setting('watering_duration', 5))
                    command = f"W{duration}"
                    if self.ingestor.write_command(command):
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"\U0001F4A7 Sug'orilmoqda... ({duration} soniya)\n\u2705 Tayyor!"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="\u26A0 Arduino bilan bog'lanishda xatolik."
                        )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="\U0001F6AB Suv baki bo'sh! Iltimos, to'ldiring."
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="\u26A0 Ma'lumot yo'q."
                )
        except Exception as e:
            logger.error(f"Error in suv command: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"\u26A0 Xatolik: {e}"
            )

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display current settings."""
        try:
            settings = self.db_manager.get_all_settings()
            
            msg = "\u2699\ufe0f *Joriy Sozlamalar* \u2699\ufe0f\n\n"
            
            # Thresholds
            msg += f"\U0001F4CA *Chegaralar:*\n"
            msg += f"  Tuproq namligi: {settings.get('soil_threshold', 250)}\n"
            msg += f"  Fan harorati: {settings.get('fan_temp_threshold', 28.0)}°C\n"
            msg += f"  Isitgich harorati: {settings.get('heater_temp_threshold', 18.0)}°C\n"
            msg += f"  Sug'orish davomiyligi: {settings.get('watering_duration', 5)} s\n\n"
            
            # Automation status
            auto_water = "\u2705 Yoniq" if settings.get('auto_water_enabled') == '1' else "\u26d4 O'chiq"
            auto_fan = "\u2705 Yoniq" if settings.get('auto_fan_enabled') == '1' else "\u26d4 O'chiq"
            auto_heater = "\u2705 Yoniq" if settings.get('auto_heater_enabled') == '1' else "\u26d4 O'chiq"
            
            msg += f"\U0001F916 *Avtomatik rejim:*\n"
            msg += f"  Sug'orish: {auto_water}\n"
            msg += f"  Fan: {auto_fan}\n"
            msg += f"  Isitgich: {auto_heater}\n"
            
            # Add toggle buttons
            keyboard = [
                [InlineKeyboardButton(
                    "\U0001F4A7 Avto-suv: O'chirish" if settings.get('auto_water_enabled') == '1' else "\U0001F4A7 Avto-suv: Yoqish",
                    callback_data='toggle_auto_water'
                )],
                [InlineKeyboardButton(
                    "\U0001F300 Avto-fan: O'chirish" if settings.get('auto_fan_enabled') == '1' else "\U0001F300 Avto-fan: Yoqish",
                    callback_data='toggle_auto_fan'
                )],
                [InlineKeyboardButton(
                    "\U0001F525 Avto-isitgich: O'chirish" if settings.get('auto_heater_enabled') == '1' else "\U0001F525 Avto-isitgich: Yoqish",
                    callback_data='toggle_auto_heater'
                )],
                [InlineKeyboardButton("\u25c0\ufe0f Orqaga", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Xatolik: {e}"
            )

    async def set_soil_threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set soil moisture threshold."""
        try:
            if context.args:
                value = int(context.args[0])
                if 100 <= value <= 1023:
                    self.db_manager.update_setting('soil_threshold', value)
                    
                    # Sync to Arduino
                    if self.automation_controller:
                        self.automation_controller.sync_settings_to_arduino()
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"\u2705 Tuproq namligi chegarasi {value} ga o'zgartirildi."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="\u26A0 Qiymat 100 dan 1023 gacha bo'lishi kerak."
                    )
            else:
                current = self.db_manager.get_setting('soil_threshold', 250)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"ℹ️ Joriy chegara: {current}\n\nO'zgartirish uchun: /tuproq_chegara 300"
                )
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\u26A0 Iltimos, raqam kiriting."
            )

    async def set_fan_temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set fan activation temperature."""
        try:
            if context.args:
                value = float(context.args[0])
                if 20 <= value <= 50:
                    self.db_manager.update_setting('fan_temp_threshold', value)
                    
                    if self.automation_controller:
                        self.automation_controller.sync_settings_to_arduino()
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"\u2705 Fan harorati {value}°C ga o'zgartirildi."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="\u26A0 Harorat 20°C dan 50°C gacha bo'lishi kerak."
                    )
            else:
                current = self.db_manager.get_setting('fan_temp_threshold', 28.0)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"ℹ️ Joriy chegara: {current}°C\n\nO'zgartirish: /fan_harorat 30"
                )
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\u26A0 Iltimos, raqam kiriting."
            )

    async def set_heater_temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set heater activation temperature."""
        try:
            if context.args:
                value = float(context.args[0])
                if 5 <= value <= 25:
                    self.db_manager.update_setting('heater_temp_threshold', value)
                    
                    if self.automation_controller:
                        self.automation_controller.sync_settings_to_arduino()
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"\u2705 Isitgich harorati {value}°C ga o'zgartirildi."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="\u26A0 Harorat 5°C dan 25°C gacha bo'lishi kerak."
                    )
            else:
                current = self.db_manager.get_setting('heater_temp_threshold', 18.0)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"ℹ️ Joriy chegara: {current}°C\n\nO'zgartirish: /isitgich_harorat 15"
                )
        except ValueError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\u26A0 Iltimos, raqam kiriting."
            )

    async def toggle_auto_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
        """Toggle automation mode (water/fan/heater)."""
        try:
            if context.args:
                state = context.args[0].lower()
                if state in ['on', 'yoniq', '1']:
                    self.db_manager.update_setting(f'auto_{mode}_enabled', '1')
                    msg = f"\u2705 Avtomatik {mode} yoqildi."
                elif state in ['off', 'ochiq', '0']:
                    self.db_manager.update_setting(f'auto_{mode}_enabled', '0')
                    msg = f"\u26d4 Avtomatik {mode} o'chirildi."
                else:
                    msg = "\u26A0 Faqat 'on' yoki 'off' ishlating."
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
                    return
                
                if self.automation_controller:
                    self.automation_controller.sync_settings_to_arduino()
                
                await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            else:
                current = self.db_manager.get_setting(f'auto_{mode}_enabled', '1')
                status = "Yoniq \u2705" if current == '1' else "O'chiq \u26d4"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"ℹ️ Avtomatik {mode}: {status}\n\nO'zgartirish: /avto_{mode} on/off"
                )
        except Exception as e:
            logger.error(f"Error toggling auto mode: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"\u26A0 Xatolik: {e}"
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks."""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'show_status':
            # Create a fake update object for status command
            fake_update = Update(update.update_id, message=query.message)
            fake_update._effective_chat = query.message.chat
            await self.status(fake_update, context)
            
        elif query.data == 'water_plant':
            # Check water level and water plant
            data = self.db_manager.get_recent_data(limit=1)
            if data:
                latest = data[0]
                water_level = latest[8]
                
                if water_level == 1:
                    duration = int(self.db_manager.get_setting('watering_duration', 5))
                    command = f"W{duration}"
                    if self.ingestor.write_command(command):
                        await query.edit_message_text(
                            text=f"\U0001F4A7 Sug'orilmoqda... ({duration} soniya)\n\u2705 Tayyor!"
                        )
                    else:
                        await query.edit_message_text(text="\u26A0 Arduino bilan bog'lanishda xatolik.")
                else:
                    await query.edit_message_text(text="\U0001F6AB Suv baki bo'sh! Iltimos, to'ldiring.")
            else:
                await query.edit_message_text(text="\u26A0 Ma'lumot yo'q.")
                
        elif query.data == 'show_settings':
            fake_update = Update(update.update_id, message=query.message)
            fake_update._effective_chat = query.message.chat
            await self.show_settings(fake_update, context)
            
        elif query.data == 'show_help':
            fake_update = Update(update.update_id, message=query.message)
            fake_update._effective_chat = query.message.chat
            await self.help_command(fake_update, context)
            
        elif query.data == 'main_menu':
            fake_update = Update(update.update_id, message=query.message)
            fake_update._effective_chat = query.message.chat
            await self.start(fake_update, context)
            
        elif query.data.startswith('toggle_auto_'):
            mode = query.data.replace('toggle_auto_', '')
            current = self.db_manager.get_setting(f'auto_{mode}_enabled', '1')
            new_value = '0' if current == '1' else '1'
            self.db_manager.update_setting(f'auto_{mode}_enabled', new_value)
            
            if self.automation_controller:
                self.automation_controller.sync_settings_to_arduino()
            
            # Refresh settings display
            fake_update = Update(update.update_id, message=query.message)
            fake_update._effective_chat = query.message.chat
            await self.show_settings(fake_update, context)

    async def fannotest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual fan test command."""
        try:
            if context.args:
                state = context.args[0].lower()
                if state in ['on', '1', 'yoq']:
                    self.ingestor.write_command("TEST_FAN_ON")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="\U0001F300 Fan yoqildi (TEST rejim).")
                elif state in ['off', '0', 'och']:
                    self.ingestor.write_command("TEST_FAN_OFF")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="\U0001F300 Fan o'chirildi (TEST rejim).")
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Ishlatish: /fannotest on/off")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="ℹ️ Fan testi: /fannotest on yoki /fannotest off")
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Xatolik: {e}")

    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show raw sensor data for troubleshooting."""
        try:
            data = self.db_manager.get_recent_data(limit=1)
            if not data:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Ma'lumot yo'q.")
                return
                
            latest = data[0]
            # timestamp, s1, s2, s3, savg, t, h, l, wl, fan, heat
            msg = (
                "\U0001F50D *Diagnostic Ma'lumotlar:*\n\n"
                f"🔢 *Soil 1:* {latest[1]}\n"
                f"🔢 *Soil 2:* {latest[2]}\n"
                f"🔢 *Soil 3:* {latest[3]}\n"
                f"🔢 *Soil Avg:* {latest[4]}\n"
                f"🌡️ *Temp:* {latest[5]}\n"
                f"💧 *Hum:* {latest[6]}\n"
                f"🌊 *Water Level (Raw):* {latest[8]}\n"
                f"🌀 *Fan:* {latest[9]}\n"
                f"🔥 *Heater:* {latest[10]}\n\n"
                "_Ushbu raqamlarni menga yuboring!_"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Xatolik: {e}")

    async def _run(self):
        """Async internal runner."""
        if not config.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram Token not set. Bot will not start.")
            return

        self.application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('holat', self.status))
        self.application.add_handler(CommandHandler('status', self.status))
        self.application.add_handler(CommandHandler('suv', self.suv))
        self.application.add_handler(CommandHandler('sozlamalar', self.show_settings))
        self.application.add_handler(CommandHandler('settings', self.show_settings))
        self.application.add_handler(CommandHandler('yordam', self.help_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('fannotest', self.fannotest))
        self.application.add_handler(CommandHandler('debug', self.debug_command))
        
        # Settings commands (with aliases)
        self.application.add_handler(CommandHandler(['tuproq_chegara', 'tuproqchegara'], self.set_soil_threshold))
        self.application.add_handler(CommandHandler(['fan_harorat', 'fanharorat'], self.set_fan_temp))
        self.application.add_handler(CommandHandler(['isitgich_harorat', 'isitgichharorat'], self.set_heater_temp))
        
        # Automation toggle commands (with aliases)
        self.application.add_handler(
            CommandHandler(['avto_suv', 'avtosuv', 'avto_water', 'avtowater', 'autowater'], lambda u, c: self.toggle_auto_mode(u, c, 'water'))
        )
        self.application.add_handler(
            CommandHandler(['avto_fan', 'avtofan', 'autofan'], lambda u, c: self.toggle_auto_mode(u, c, 'fan'))
        )
        self.application.add_handler(
            CommandHandler(['avto_isitgich', 'avtoisitgich', 'auto_heater', 'autoheater'], lambda u, c: self.toggle_auto_mode(u, c, 'heater'))
        )
        
        # Button handler
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

        logger.info("Starting Telegram Bot with enhanced features...")
        
        # Explicit initialization for better compatibility
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running until stopped
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
            pass
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    def run(self):
        """Standard entry point."""
        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            pass



# TESTING COMMENT