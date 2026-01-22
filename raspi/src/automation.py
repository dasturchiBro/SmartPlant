import logging
import time
import threading
from . import config

logger = logging.getLogger(__name__)

class AutomationController:
    """Handles automated actions based on sensor data and user settings."""
    
    def __init__(self, db_manager, ingestor):
        self.db_manager = db_manager
        self.ingestor = ingestor
        self.running = False
        self.check_interval = 30  # Check every 30 seconds
        
    def start(self):
        """Start the automation loop in a separate thread."""
        self.running = True
        automation_thread = threading.Thread(target=self._automation_loop)
        automation_thread.daemon = True
        automation_thread.start()
        logger.info("Automation controller started")
        
    def stop(self):
        """Stop the automation loop."""
        self.running = False
        logger.info("Automation controller stopped")
        
    def _automation_loop(self):
        """Main automation loop that runs periodically."""
        while self.running:
            try:
                self._check_and_act()
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
            
            time.sleep(self.check_interval)
    
    def _check_and_act(self):
        """Check sensor data and execute automated actions based on settings."""
        # Get latest sensor data
        latest = self.db_manager.get_latest_reading()
        if not latest:
            return
        
        # Use keys from sqlite3.Row for safety and clarity
        soil_avg = latest['soil_moisture_avg']
        temp = latest['temperature']
        hum = latest['humidity']
        water_level = latest['water_level']
        
        # Get user settings
        settings = self.db_manager.get_all_settings()
        
        # Auto-watering logic
        if settings.get('auto_water_enabled') == '1' and water_level == 1:
            soil_threshold = int(settings.get('soil_threshold', 340))
            
            # Check if average soil moisture is ABOVE threshold (DRY)
            if soil_avg > soil_threshold:
                logger.info(f"Auto-watering triggered: Average soil moisture ({soil_avg}) above threshold ({soil_threshold}) - DRY")
                duration = int(settings.get('watering_duration', 5))
                self.ingestor.write_command(f"W{duration}")
                
                # Wait to avoid rapid re-triggering
                time.sleep(60)  # Wait 1 minute
        
        # Note: Fan and heater control is handled by Arduino firmware directly
        # The Arduino makes real-time decisions based on temperature
        # We just sync settings to Arduino when user changes them
        
    def sync_settings_to_arduino(self):
        """Send current settings to Arduino."""
        settings = self.db_manager.get_all_settings()
        self.ingestor.send_settings_to_arduino(settings)
        logger.info("Settings synchronized to Arduino")
