import serial
import json
import time
import logging
import threading
from . import config

logger = logging.getLogger(__name__)

class DataIngestion:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.serial_connection = None
        self.running = False
        self._write_lock = threading.Lock()
    
    def connect_serial(self):
        """Attempt to connect to the serial port."""
        try:
            self.serial_connection = serial.Serial(
                config.SERIAL_PORT, 
                config.BAUD_RATE, 
                timeout=1
            )
            logger.info(f"Connected to {config.SERIAL_PORT}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port: {e}")
            return False

    def start_listening(self):
        """Main loop to read from serial and save to DB."""
        self.running = True
        logger.info("Started listening for sensor data thread...")
        
        while self.running:
            # 1. Ensure serial is connected
            if not self.serial_connection or not self.serial_connection.is_open:
                logger.info(f"Attempting to connect to serial port {config.SERIAL_PORT}...")
                if self.connect_serial():
                    logger.info("Successfully connected/reconnected to serial.")
                else:
                    logger.error(f"Failed to connect to {config.SERIAL_PORT}. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue

            # 2. Read data
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        logger.debug(f"Raw serial data: {line}")
                        try:
                            data = json.loads(line)
                            logger.debug(f"JSON parsed: {data}")
                            
                            soil1 = data.get('soil1', 0)
                            soil2 = data.get('soil2', 0)
                            soil3 = data.get('soil3', 0)
                            soil_avg = data.get('soil_avg', 0)
                            temp = data.get('temp', 0)
                            hum = data.get('hum', 0)
                            water_level = data.get('water_level', 0)
                            fan_status = data.get('fan_status', 0)
                            heater_status = data.get('heater_status', 0)
                            
                            if soil1 is not None and temp is not None:
                                self.db_manager.insert_sensor_data(
                                    soil1, soil2, soil3, soil_avg, 
                                    temp, hum, 0, water_level, 
                                    fan_status, heater_status
                                )
                                logger.info(f"Successfully saved reading to DB: T={temp}, S1={soil1}")
                        except json.JSONDecodeError:
                            logger.warning(f"Received malformed JSON-like data: {line}")
            except serial.SerialException as e:
                logger.error(f"Serial error: {e}. Attempting reconnect...")
                try:
                    self.serial_connection.close()
                except:
                    pass
                time.sleep(5)
                # Next iteration will handle reconnection
            except Exception as e:
                logger.error(f"Unexpected error in ingestion loop: {e}")
            
            time.sleep(config.DATA_READ_INTERVAL_SECONDS)

    def write_command(self, command):
        """Writes a command string to the serial port."""
        with self._write_lock:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    # Encode string to bytes and add newline
                    self.serial_connection.write(f"{command}\n".encode('utf-8'))
                    self.serial_connection.flush() # Ensure it's sent
                    logger.info(f"Sent command to Arduino: {command}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to write command '{command}': {e}")
                    return False
            else:
                logger.warning(f"Serial connection to {config.SERIAL_PORT} not open. Cannot send command: {command}")
                return False

    def send_settings_to_arduino(self, settings):
        """Send all relevant settings to Arduino."""
        try:
            # Send threshold settings
            self.write_command(f"SET_SOIL_THRESH:{settings.get('soil_threshold', 500)}")
            time.sleep(0.1)
            self.write_command(f"SET_FAN_TEMP:{settings.get('fan_temp_threshold', 28.0)}")
            time.sleep(0.1)
            self.write_command(f"SET_HEATER_TEMP:{settings.get('heater_temp_threshold', 18.0)}")
            time.sleep(0.1)
            
            # Send automation flags
            if settings.get('auto_water_enabled') == '1':
                self.write_command("AUTO_WATER_ON")
            else:
                self.write_command("AUTO_WATER_OFF")
            time.sleep(0.1)
            
            if settings.get('auto_fan_enabled') == '1':
                self.write_command("AUTO_FAN_ON")
            else:
                self.write_command("AUTO_FAN_OFF")
            time.sleep(0.1)
            
            if settings.get('auto_heater_enabled') == '1':
                self.write_command("AUTO_HEATER_ON")
            else:
                self.write_command("AUTO_HEATER_OFF")
            
            logger.info("Settings synced to Arduino")
            return True
        except Exception as e:
            logger.error(f"Failed to send settings to Arduino: {e}")
            return False

    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
