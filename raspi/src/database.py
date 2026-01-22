import sqlite3
import time
from . import config

class DatabaseManager:
    def __init__(self, db_path=config.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Sensor data table with 3 soil sensors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                soil_moisture_1 INTEGER,
                soil_moisture_2 INTEGER,
                soil_moisture_3 INTEGER,
                soil_moisture_avg INTEGER,
                temperature REAL,
                humidity REAL,
                light_intensity INTEGER,
                water_level INTEGER,
                fan_status INTEGER,
                heater_status INTEGER
            )
        ''')
        
        # Predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                prediction TEXT,
                explanation TEXT
            )
        ''')
        
        # Settings table for user preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT UNIQUE,
                setting_value TEXT,
                last_updated REAL
            )
        ''')
        
        # Insert default settings if not exists
        default_settings = {
            'auto_water_enabled': '1',
            'auto_fan_enabled': '1',
            'auto_heater_enabled': '1',
            'soil_threshold': '340',
            'fan_temp_threshold': '28.0',
            'heater_temp_threshold': '20.0',
            'watering_duration': '5'
        }
        
        for name, value in default_settings.items():
            cursor.execute('''
                INSERT OR IGNORE INTO user_settings (setting_name, setting_value, last_updated)
                VALUES (?, ?, ?)
            ''', (name, value, time.time()))
            
        # Migration: Ensure thresholds match user's latest requirements
        cursor.execute('''
            UPDATE user_settings 
            SET setting_value = '340' 
            WHERE setting_name = 'soil_threshold' AND (setting_value = '500' OR setting_value = '250' OR setting_value = '300')
        ''')
        
        cursor.execute('''
            UPDATE user_settings 
            SET setting_value = '20.0' 
            WHERE setting_name = 'heater_temp_threshold' AND setting_value = '18.0'
        ''')
        
        conn.commit()
        conn.close()

    def insert_sensor_data(self, soil1, soil2, soil3, soil_avg, temp, hum, light, water_level, fan_status, heater_status):
        """Insert a new reading with 3 soil sensors."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = time.time()
        cursor.execute('''
            INSERT INTO sensor_data 
            (timestamp, soil_moisture_1, soil_moisture_2, soil_moisture_3, soil_moisture_avg, 
             temperature, humidity, light_intensity, water_level, fan_status, heater_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, soil1, soil2, soil3, soil_avg, temp, hum, light, water_level, fan_status, heater_status))
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
        """Get recent sensor readings as a list of dictionaries/Rows."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT timestamp, soil_moisture_1, soil_moisture_2, soil_moisture_3, soil_moisture_avg,
                   temperature, humidity, light_intensity, water_level, fan_status, heater_status
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        data = cursor.fetchall()
        conn.close()
        # Return in ascending order for trainer/predictor
        return list(reversed(data))

    def get_latest_reading(self):
        """Get the absolute latest reading."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, soil_moisture_1, soil_moisture_2, soil_moisture_3, soil_moisture_avg,
                   temperature, humidity, light_intensity, water_level, fan_status, heater_status
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        return result

    def get_all_data(self):
        """Get all sensor readings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, soil_moisture_1, soil_moisture_2, soil_moisture_3, soil_moisture_avg,
                   temperature, humidity, light_intensity, water_level, fan_status, heater_status
            FROM sensor_data 
            ORDER BY timestamp ASC
        ''')
        data = cursor.fetchall()
        conn.close()
        return data

    def get_setting(self, setting_name, default=None):
        """Get a setting value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT setting_value FROM user_settings WHERE setting_name = ?', (setting_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default

    def update_setting(self, setting_name, setting_value):
        """Update or insert a setting."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_settings (setting_name, setting_value, last_updated)
            VALUES (?, ?, ?)
        ''', (setting_name, str(setting_value), time.time()))
        conn.commit()
        conn.close()

    def get_all_settings(self):
        """Get all settings as a dictionary."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT setting_name, setting_value FROM user_settings')
        settings = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return settings
