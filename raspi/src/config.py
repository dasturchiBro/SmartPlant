import os
from pathlib import Path
from dotenv import load_dotenv

# Determine project root and load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

# Serial Configuration
# SERIAL_PORT = '/dev/ttyUSB0'  # Default for Raspberry Pi, might need adjustment
SERIAL_PORT = 'COM6'  # Windows port (not used on Raspberry Pi)
BAUD_RATE = 9600

# Database Configuration
DB_NAME = 'plant_data_v3.db'
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DB_NAME)

# Model Configuration
MODEL_FILENAME = 'plant_model.joblib'
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), MODEL_FILENAME)

# System Loop Configuration
DATA_READ_INTERVAL_SECONDS = 0.1 # Serial read timeout or loop delay
TRAINING_INTERVAL_MINUTES = 60 * 24 # Train once a day
PREDICTION_INTERVAL_SECONDS = 60 * 5 # Predict every 5 minutes

# Thresholds (logic based if no model)
MOISTURE_THRESHOLD_LOW = 340 # Example analog value, needs calibration
HEATER_THRESHOLD_TEMP = 20.0 # Turn heater on if temp <= this

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8516510783:AAGo_7fVLiuYmZ1ubdhM8MOH1C9MUNEIf5s" # Get from @BotFather

# AI & Voice Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

VOICE_NAME = "uz-UZ-MadinaNeural"
