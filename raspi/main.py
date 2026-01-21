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
from src import config

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

def run_prediction_job(db_manager, predictor):
    try:
        # Get recent data (last 20 points should be enough for features)
        recent_data = db_manager.get_recent_data(limit=20)
        prediction, explanation = predictor.predict(recent_data)
        
        if prediction:
            logger.info(f"PREDICTION: {prediction}")
            logger.info(f"EXPLANATION: {explanation}")
            db_manager.insert_prediction(prediction, explanation)
            
            # Here acts on the decision (e.g. Turn on pump GPIO or Send Alert)
            if "Stress" in prediction:
                logger.warning("!!! PLANT STRESS DETECTED - RECOMMEND WATERING !!!")
    except Exception as e:
        logger.error(f"Prediction job failed: {e}")

def scheduler_loop():
    """Background thread for scheduled tasks."""
    while True:
        schedule.run_pending()
        time.sleep(1)

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

    # Schedule Jobs
    # Schedule training once a day
    schedule.every(config.TRAINING_INTERVAL_MINUTES).minutes.do(run_training_job, trainer)
    
    # Schedule prediction every N minutes
    schedule.every(config.PREDICTION_INTERVAL_SECONDS).seconds.do(run_prediction_job, db_manager, predictor)

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
