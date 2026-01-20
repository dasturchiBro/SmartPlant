import sqlite3
import time
from . import config

class DatabaseManager:
    def __init__(self, db_path=config.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                soil_moisture INTEGER,
                temperature REAL,
                humidity REAL,
                light_intensity INTEGER,
                temperature_lm35 REAL,
                water_level INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                prediction TEXT,
                explanation TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def insert_sensor_data(self, soil, temp, hum, light, temp_lm35, water_level):
        """Insert a new reading."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = time.time()
        cursor.execute('''
            INSERT INTO sensor_data (timestamp, soil_moisture, temperature, humidity, light_intensity, temperature_lm35, water_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, soil, temp, hum, light, temp_lm35, water_level))
        conn.commit()
        conn.close()

    def insert_prediction(self, prediction, explanation):
        """Log a prediction."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = time.time()
        cursor.execute('''
            INSERT INTO predictions (timestamp, prediction, explanation)
            VALUES (?, ?, ?)
        ''', (timestamp, prediction, explanation))
        conn.commit()
        conn.close()

    def get_recent_data(self, limit=1000):
        """Get recent sensor readings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT * FROM (
                SELECT timestamp, soil_moisture, temperature, humidity, light_intensity, temperature_lm35, water_level
                FROM sensor_data 
                ORDER BY timestamp DESC 
                LIMIT ?
            ) ORDER BY timestamp ASC
        ''', (limit,))
        data = cursor.fetchall()
        conn.close()
        return data

    def get_all_data(self):
        """Get all sensor readings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp, soil_moisture, temperature, humidity, light_intensity, temperature_lm35, water_level FROM sensor_data ORDER BY timestamp ASC')
        data = cursor.fetchall()
        conn.close()
        return data
