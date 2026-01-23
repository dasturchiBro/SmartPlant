import time
import threading
import schedule
import logging
import sys
from src.database import DatabaseManager
from src.ingestion import DataIngestion
from src.preprocessing import DataPreprocessor
from src.training import ModelTrainer
from src.prediction import Predictor
from src.prediction import Predictor
from src.explainability import ExplainabilityModule
from src.bot import SmartPlantBot
from src.automation import AutomationController
from src.voice import VoiceModule
from src import config
import asyncio

# Setup logging NEW
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemLoop")

def run_training_job(trainer):
    try:
        trainer.train_model()
    except Exception as e:
        logger.error(f"Training job failed: {e}")

def run_prediction_job(db_manager, predictor, voice_module=None, bot=None):
    try:
        # Get recent data
        recent_data = db_manager.get_recent_data(limit=20)
        prediction, explanation = predictor.predict(recent_data)
        
        if prediction:
            logger.info(f"PREDICTION: {prediction}")
            logger.info(f"EXPLANATION: {explanation}")
            db_manager.insert_prediction(prediction, explanation)
            
            if "Stress" in prediction:
                logger.warning("!!! PLANT STRESS DETECTED - RECOMMEND WATERING !!!")
                if bot:
                    alert_msg = f"O'simlikda stress aniqlandi! 🌿\nBashorat: {prediction}\nTahlil: {explanation}"
                    bot.send_alert_sync(alert_msg)

        # Update voice cache if sensor data is available
        if voice_module and recent_data:
            latest = recent_data[-1] 
            # Use keys from sqlite3.Row for safety
            sensor_dict = {
                'soil_avg': latest['soil_moisture_avg'],
                'temp': latest['temperature'],
                'hum': latest['humidity'],
                'water_level': latest['water_level'],
                'fan_status': latest['fan_status'],
                'heater_status': latest['heater_status']
            }
            # Refresh cache in background
            asyncio.run(voice_module.refresh_status_cache(sensor_dict))

    except Exception as e:
        logger.error(f"Prediction job failed: {e}")

def scheduler_loop():
    """Background thread for scheduled tasks."""
    while True:
        schedule.run_pending()
        time.sleep(1)

def handle_button_press(voice_module, db_manager):
    """Callback for button press to trigger AI voice status report."""
    try:
        logger.info("Button press callback triggered. Fetching status...")
        # Get absolute freshest sensor data
        latest = db_manager.get_latest_reading()
        if latest:
            sensor_dict = {
                'soil_avg': latest['soil_moisture_avg'],
                'temp': latest['temperature'],
                'hum': latest['humidity'],
                'water_level': latest['water_level'],
                'fan_status': latest['fan_status'],
                'heater_status': latest['heater_status']
            }
            
            # Start instant voice report in a separate thread to NOT block ingestion
            threading.Thread(target=lambda: voice_module.say_status_instant(sensor_dict), daemon=True).start()
        else:
            logger.warning("No sensor data available for voice report.")
    except Exception as e:
        logger.error(f"Error handling button press: {e}")

def handle_watering_trigger(voice_module):
    """Callback for manual watering button press."""
    try:
        logger.info("Watering trigger callback triggered.")
        asyncio.run(voice_module.speak_watering())
        # Refresh cache immediately after watering as status has changed
        # We can't use Gemini here easily without data, so we'll wait for next prediction refresh 
        # or just trigger a refresh in the next prediction cycle.
    except Exception as e:
        logger.error(f"Error handling watering trigger: {e}")

def main():
    logger.info("Starting Smart Plant Monitoring System...")
    
    # Initialize components
    db_manager = DatabaseManager()
    preprocessor = DataPreprocessor()
    trainer = ModelTrainer(db_manager, preprocessor)
    explainer = ExplainabilityModule()
    # Predictor loads model, so might be None initially if no model exists
    predictor = Predictor(preprocessor, explainer) 
    ingestor = DataIngestion(db_manager)
    voice = VoiceModule()
    
    # Set callbacks for buttons
    # Direct event handlers with threads for zero-latency response
    ingestor.on_button_pressed_callback = lambda: handle_button_press(voice, db_manager)
    ingestor.on_watering_triggered_callback = lambda: threading.Thread(
        target=lambda: voice.play_audio_sync(voice.watering_audio), 
        daemon=True
    ).start()
    
    # Initialize automation controller
    automation = AutomationController(db_manager, ingestor)
    
    # Initialize bot with automation controller
    bot = SmartPlantBot(db_manager, ingestor, automation)

    # Start Data Ingestion in a separate thread
    ingestion_thread = threading.Thread(target=ingestor.start_listening)
    ingestion_thread.daemon = True
    ingestion_thread.start()

    # Start Automation Controller
    automation.start()
    
    # Sync initial settings to Arduino after connection
    time.sleep(3)  # Wait for Arduino to be ready
    automation.sync_settings_to_arduino()

    # Pre-generate static sounds and then play welcome in separate threads
    def setup_voice():
        asyncio.run(voice.generate_static_sounds())
        voice.play_audio_sync(voice.welcome_audio)
    
    threading.Thread(target=setup_voice, daemon=True).start()
    
    # Continuous background loop to keep the voice report fresh and accurate
    def voice_maintenance_loop():
        # Short sleep at start to let sensors settle
        time.sleep(2)
        while True:
            try:
                latest = db_manager.get_latest_reading()
                if latest:
                    sensor_dict = {
                        'soil_avg': latest['soil_moisture_avg'], 
                        'temp': latest['temperature'], 
                        'hum': latest['humidity'],
                        'water_level': latest['water_level'], 
                        'fan_status': latest['fan_status'], 
                        'heater_status': latest['heater_status']
                    }
                    # This will internally decide whether to use AI, Fallback, or Skip
                    # based on time and sensor changes (±0.5°C, ±5% Hum)
                    asyncio.run(voice.refresh_status_cache(sensor_dict))
            except Exception as e:
                logger.error(f"Error in voice maintenance loop: {e}")
            
            # Check every 30 seconds for significant changes
            time.sleep(30)
            
    threading.Thread(target=voice_maintenance_loop, daemon=True).start()

    # Schedule Jobs
    # Schedule training once a day
    schedule.every(config.TRAINING_INTERVAL_MINUTES).minutes.do(run_training_job, trainer)
    
    # Schedule prediction every N minutes (also refreshes voice cache)
    schedule.every(config.PREDICTION_INTERVAL_SECONDS).seconds.do(run_prediction_job, db_manager, predictor, voice, bot)

    # Start Scheduler in a separate thread
    scheduler_thread = threading.Thread(target=scheduler_loop)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    logger.info("System initialized. Starting Bot (Main Thread)...")

    # Run Telegram Bot in MAIN Thread (Blocking)
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Stopping system...")
    finally:
        automation.stop()
        ingestor.stop()
        logger.info("System stopped.")

if __name__ == "__main__":
    main()
