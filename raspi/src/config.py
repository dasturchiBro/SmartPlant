import os

# Serial Configuration
SERIAL_PORT = '/dev/ttyACM0'  # Default for Raspberry Pi, might need adjustment
# SERIAL_PORT = 'COM6'  # Default for Raspberry Pi, might need adjustment (e.g. COM3 on Windows)
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
MOISTURE_THRESHOLD_LOW = 300 # Example analog value, needs calibration

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8468978930:AAHL0ApuXAtyFuieDAPPTthWxT12EFFupBQ" # Get from @BotFather
