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
from src import config

# Setup logging
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
    bot = SmartPlantBot(db_manager, ingestor)

    # Start Data Ingestion in a separate thread
    ingestion_thread = threading.Thread(target=ingestor.start_listening)
    ingestion_thread.daemon = True
    ingestion_thread.start()

    # Start Telegram Bot in a separate thread
    bot_thread = threading.Thread(target=bot.run)
    bot_thread.daemon = True
    bot_thread.start()

    # Schedule Jobs
    # Schedule training once a day
    schedule.every(config.TRAINING_INTERVAL_MINUTES).minutes.do(run_training_job, trainer)
    
    # Schedule prediction every N minutes
    schedule.every(config.PREDICTION_INTERVAL_SECONDS).seconds.do(run_prediction_job, db_manager, predictor)

    logger.info("System initialized. Running main loop...")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping system...")
        ingestor.stop()
        ingestion_thread.join()
        logger.info("System stopped.")

if __name__ == "__main__":
    main()
