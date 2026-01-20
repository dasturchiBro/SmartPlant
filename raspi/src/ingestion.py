import serial
import json
import time
import logging
from . import config

logger = logging.getLogger(__name__)

class DataIngestion:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.serial_connection = None
        self.running = False
    
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
        if not self.serial_connection:
            if not self.connect_serial():
                return

        self.running = True
        logger.info("Started listening for sensor data...")
        
        while self.running:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            soil = data.get('soil')
                            temp = data.get('temp')
                            hum = data.get('hum')
                            light = data.get('light', 0)
                            temp_lm35 = data.get('temp_lm35', 0.0)
                            water_level = data.get('water_level', 0)
                            
                            if soil is not None and temp is not None:
                                self.db_manager.insert_sensor_data(soil, temp, hum, light, temp_lm35, water_level)
                                logger.debug(f"Saved data: {data}")
                        except json.JSONDecodeError:
                            logger.warning(f"Received malformed JSON-like data: {line}")
            except serial.SerialException as e:
                logger.error(f"Serial error: {e}. Attempting reconnect...")
                self.serial_connection.close()
                time.sleep(5)
                self.connect_serial()
            except Exception as e:
                logger.error(f"Unexpected error in ingestion loop: {e}")
            
            time.sleep(config.DATA_READ_INTERVAL_SECONDS)

    def write_command(self, command):
        """Writes a command string/char to the serial port."""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                # Encode string to bytes
                self.serial_connection.write(command.encode('utf-8'))
                logger.info(f"Sent command to Arduino: {command}")
                return True
            except Exception as e:
                logger.error(f"Failed to write command: {e}")
                return False
        else:
            logger.warning("Serial connection not open. Cannot send command.")
            return False

    def stop(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
