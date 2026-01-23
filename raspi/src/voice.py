import asyncio
import edge_tts
import pygame
import os
import logging
import time
import google.generativeai as genai

# Handle import regardless of how the script is run
try:
    from . import config
except ImportError:
    try:
        from src import config
    except ImportError:
        import config

logger = logging.getLogger(__name__)

class VoiceModule:
    def __init__(self):
        self.voice = config.VOICE_NAME
        self.model = None
        self.gemini_ready = False
        
        # Absolute paths for audio files
        self.tmp_audio = os.path.join(config.BASE_DIR, "speech.mp3")
        self.cached_audio = os.path.join(config.BASE_DIR, "status_cache.mp3")
        self.welcome_audio = os.path.join(config.BASE_DIR, "welcome.mp3")
        self.watering_audio = os.path.join(config.BASE_DIR, "watering.mp3")
        
        self.is_refreshing = False
        self._refresh_lock = asyncio.Lock()
        self.last_refresh_time = 0
        self.last_ai_refresh_time = 0
        self.ai_refresh_interval = 7200  # 2 hours for AI (stay within 20/day)
        self.fallback_refresh_interval = 60 # 1 minute for factual fallback (faster response to changes)
        self.last_soil_dry = None
        self.last_temp = None
        self.last_hum = None
        
        # Initialize mixer early
        try:
            pygame.mixer.init()
            logger.info("Pygame mixer initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")
            
        # Cleanup old status cache on startup to avoid hearing stale data from yesterday
        if os.path.exists(self.cached_audio):
            try:
                os.remove(self.cached_audio)
                logger.info("Stale status cache deleted on startup.")
            except Exception as e:
                logger.error(f"Failed to delete stale cache: {e}")
        
        # Initialize Gemini
        if config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                
                # Try to find a working model automatically
                logger.info("Discovering available Gemini models...")
                available = []
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available.append(m.name)
                except Exception as list_e:
                    logger.error(f"Could not list models: {list_e}")

                if not available:
                    # Fallback to standard if listing failed
                    logger.warning("Could not list models, falling back to gemini-1.5-flash")
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                    self.gemini_ready = True
                else:
                    logger.info(f"Available models: {available}")
                    # Prioritize flash, then pro
                    preferred = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']
                    target = None
                    for p in preferred:
                        if p in available:
                            target = p
                            break
                    
                    if not target:
                        target = available[0] # Use first available if no preferred found
                    
                    logger.info(f"Using model: {target}")
                    self.model = genai.GenerativeModel(target)
                    self.gemini_ready = True
                    
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("Gemini API Key missing. AI descriptions will be limited to fallback.")

        # Initialize Pygame Mixer
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

    async def _generate_audio(self, text, filename=None):
        """Generate audio file from text using edge-tts."""
        target = filename if filename else self.tmp_audio
        try:
            # slowed down to standard speed (+0%) for better clarity
            communicate = edge_tts.Communicate(text, self.voice, rate="+0%", pitch="+15Hz")
            await communicate.save(target)
            return True
        except Exception as e:
            logger.error(f"TTS Generation failed: {e}")
            return False

    def _play_audio(self):
        """Play the generated audio file using pygame."""
        try:
            if not os.path.exists(self.tmp_audio):
                return
            
            pygame.mixer.music.load(self.tmp_audio)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                asyncio.run(asyncio.sleep(0.1)) # This is tricky if called from sync/async mix
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
        finally:
            try:
                pygame.mixer.music.unload()
            except:
                pass

    def play_audio_sync(self, filename):
        """Play audio file synchronously in a simple loop. Safe for threads."""
        try:
            logger.info(f"Sync playback started for: {filename}")
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            import time
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            logger.info("Sync playback finished.")
        except Exception as e:
            logger.error(f"Sync playback error: {e}")

    async def speak(self, text, filename=None):
        """Generate and play speech (async)."""
        target = filename if filename else self.tmp_audio
        
        if text:
            logger.info(f"Generating and speaking: {text[:50]}...")
            if not await self._generate_audio(text, target):
                return
        else:
            logger.info(f"Playing existing file: {target}")

        try:
            pygame.mixer.music.load(target)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"Playback error in speak: {e}")

    async def generate_static_sounds(self):
        """Pre-generate sounds that don't change often."""
        logger.info("Pre-generating static voice sounds...")
        await self._generate_audio("Salom! Men aqlli o'simlik tizimi man. Sizni ko'rganimdan xursandman!", self.welcome_audio)
        await self._generate_audio("Yashang! Suv uchun katta rahmat, juda chanqagan edim.", self.watering_audio)
        logger.info("Static voice sounds ready.")

    async def welcome(self):
        """Play the pre-generated welcome message."""
        if os.path.exists(self.welcome_audio):
            self.play_audio_sync(self.welcome_audio)
        else:
            await self.speak("Salom! Men aqlli o'simlik tizimi man. Sizni ko'rganimdan xursandman!", self.welcome_audio)

    async def speak_watering(self):
        """Say something when watering starts (using cache)."""
        if os.path.exists(self.watering_audio):
            self.play_audio_sync(self.watering_audio)
        else:
            await self.speak("Yashang! Suv uchun katta rahmat, juda chanqagan edim.", self.watering_audio)

    def _generate_fallback_report(self, sensor_data):
        """Structured report in Uzbek if AI fails or quota is met."""
        soil_avg = sensor_data.get('soil_avg', 0)
        temp = sensor_data.get('temp', 0)
        hum = sensor_data.get('hum', 0)
        water_level = sensor_data.get('water_level', 0)
        fan_status = sensor_data.get('fan_status', 0)
        heater_status = sensor_data.get('heater_status', 0)
        
        # Soil condition
        soil_status = "Tuproq namligi yaxshi"
        if soil_avg >= config.MOISTURE_THRESHOLD_LOW:
            soil_status = "Diqqat, tuproq juda quruq, suv quyish kerak"
        
        # Water tank
        tank_status = "Suv idishi to'la"
        if water_level == 0:
            tank_status = "Diqqat, idishda suv tugagan"
            
        # Fan and Heater
        fan_text = "Ventilyator yoqilgan" if fan_status else "Ventilyator o'chirilgan"
        heater_text = "Isitgich yoqilgan" if heater_status else "Isitgich o'chirilgan"
        
        return (
            f"Hozirgi holat haqida hisobot: "
            f"Harorat {temp} daraja. Namlik {hum} foiz. "
            f"{soil_status}. {tank_status}. "
            f"{fan_text}. {heater_text}."
        )

    def generate_ai_report(self, sensor_data):
        """Use Gemini to generate a report, with fallback."""
        if not self.gemini_ready:
            return self._generate_fallback_report(sensor_data)
        
        prompt = (
            f"You are a smart plant speaking and explaining your current condition in Uzbek. "
            f"Based on these sensor readings, give a short, factual, and neutral status update: "
            f"Soil moisture: {sensor_data.get('soil_avg')} (CRITICAL: If this is >= 340, the soil is VERY DRY and you MUST sound concerned/urgent and tell the owner to water you. DO NOT say everything is okay if moisture is 340 or higher), "
            f"Temperature: {sensor_data.get('temp')} degrees, "
            f"Humidity: {sensor_data.get('hum')}%, "
            f"Water Level in tank: {'Full' if sensor_data.get('water_level') == 1 else 'Empty'}, "
            f"Fan status: {'Running' if sensor_data.get('fan_status') else 'Stopped'}, "
            f"Heater status: {'Active' if sensor_data.get('heater_status') else 'Off'}. "
            f"IMPORTANT: Mention the exact temperature value ({sensor_data.get('temp')}) followed by the word 'daraja'. DO NOT use the letter 'C' or the word 'Selsiy'. "
            f"Keep it under 3 sentences. If soil is dry, prioritize that over temperature. "
            f"CRITICAL: DO NOT use intimate or inappropriate terms like 'Jonim', 'Azizim', or 'Begim'. "
            f"Do not address the user personally. Focus strictly on explaining the sensor values and status."
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                logger.warning("Gemini Quota exceeded (429). Using fallback report.")
            else:
                logger.error(f"Gemini generation failed: {e}")
            return self._generate_fallback_report(sensor_data)

    def say_status_instant(self, sensor_data):
        """Instant playback of cache with age and value verification."""
        temp = sensor_data.get('temp', 0)
        hum = sensor_data.get('hum', 0)
        
        # 1. Check if cache exists and is FRESH (less than 60 seconds old AND data matches)
        if os.path.exists(self.cached_audio):
            cache_age = time.time() - os.path.getmtime(self.cached_audio)
            
            # Check for data discrepancy since the cache was made
            # (If temp changed by >0.4 or hum by >3%, the cache is "wrong")
            data_mismatch = False
            if self.last_temp is not None and abs(temp - self.last_temp) >= 0.4:
                data_mismatch = True
            if self.last_hum is not None and abs(hum - self.last_hum) >= 3.0:
                data_mismatch = True

            if cache_age < 60 and not data_mismatch:
                logger.info(f"Instant status: Playing fresh cache (Age: {int(cache_age)}s).")
                self.play_audio_sync(self.cached_audio)
                # Refresh in background for NEXT time
                import threading
                threading.Thread(target=lambda: asyncio.run(self.refresh_status_cache(sensor_data)), daemon=True).start()
                return True
            else:
                reason = "STALE" if cache_age >= 60 else "DATA MISMATCH"
                logger.info(f"Instant status: Cache is {reason}. Generating live fallback...")
        else:
            logger.info("Instant status: No cache found. Generating live fallback...")
            
        # 2. If no cache or stale, generate a FAST fallback report synchronously
        # This takes ~1 second but is 100% accurate.
        report = self._generate_fallback_report(sensor_data)
        asyncio.run(self.speak(report))
        # Update the cache for next time
        import threading
        threading.Thread(target=lambda: asyncio.run(self.refresh_status_cache(sensor_data)), daemon=True).start()
        return True

    async def say_status(self, sensor_data):
        """Regular status report."""
        report = self.generate_ai_report(sensor_data)
        await self.speak(report)
        # Refresh the cache for NEXT time
        await self.refresh_status_cache(sensor_data)

    async def refresh_status_cache(self, sensor_data, force=False):
        """Update the background audio cache intelligently."""
        now = time.time()
        soil_avg = sensor_data.get('soil_avg', 0)
        temp = sensor_data.get('temp', 0)
        hum = sensor_data.get('hum', 0)
        current_soil_dry = soil_avg >= config.MOISTURE_THRESHOLD_LOW
        
        # State change detection
        soil_changed = (self.last_soil_dry is not None and self.last_soil_dry != current_soil_dry)
        
        # Significant value change detection (Force refresh if temp changed by 0.5 or hum by 5%)
        value_changed = False
        if self.last_temp is not None and abs(temp - self.last_temp) >= 0.5:
            value_changed = True
        if self.last_hum is not None and abs(hum - self.last_hum) >= 5.0:
            value_changed = True

        force_refresh = force or soil_changed or value_changed
        
        # Decide if we SHOULD skip based on time
        time_since_refresh = now - self.last_refresh_time
        should_skip = not force_refresh and os.path.exists(self.cached_audio) and (time_since_refresh < self.fallback_refresh_interval)
        
        if should_skip:
            return

        async with self._refresh_lock:
            if self.is_refreshing:
                return
            self.is_refreshing = True

        try:
            # Decide: AI or Fallback?
            # We ONLY use AI if the long interval has passed AND it's not a sudden forced value change
            # (Sudden changes are best handled by fast fallback)
            can_use_ai = (now - self.last_ai_refresh_time >= self.ai_refresh_interval) and not value_changed
            
            if can_use_ai:
                logger.info("Refreshing AI status cache (with Gemini)...")
                report = self.generate_ai_report(sensor_data)
                # If Gemini returned fallback (quota), don't update last_ai_refresh_time to try again later
                if "hisobot" not in report: # Simple check if it's the AI report vs structured fallback
                     self.last_ai_refresh_time = now
            else:
                logger.info(f"Refreshing AI status cache (Fallback only - Reason: {'State Change' if force_refresh else 'Cooldown'})...")
                report = self._generate_fallback_report(sensor_data)
            
            if report:
                await self._generate_audio(report, self.cached_audio)
                self.last_refresh_time = now
                self.last_soil_dry = current_soil_dry
                self.last_temp = temp
                self.last_hum = hum
                logger.info("Voice status cache updated successfully.")
        except Exception as e:
            logger.error(f"Cache refresh failed: {e}")
        finally:
            self.is_refreshing = False

if __name__ == "__main__":
    # Quick test if run directly
    import asyncio
    logging.basicConfig(level=logging.INFO)
    async def test():
        v = VoiceModule()
        await v.welcome()
        await v.say_status({'soil_avg': 500, 'temp': 20, 'hum': 50, 'water_level': 1})
    asyncio.run(test())
