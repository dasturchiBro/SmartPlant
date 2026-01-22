import asyncio
import logging
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.voice import VoiceModule

logging.basicConfig(level=logging.INFO)

async def test_voice():
    print("Testing Voice Module...")
    voice = VoiceModule()
    
    print("1. Testing Welcome Message...")
    await voice.welcome()
    
    print("2. Testing AI Report (Fallback)...")
    sensor_data = {
        'soil_avg': 450,
        'temp': 22.5,
        'hum': 60,
        'water_level': 1
    }
    await voice.say_status(sensor_data)
    
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_voice())
