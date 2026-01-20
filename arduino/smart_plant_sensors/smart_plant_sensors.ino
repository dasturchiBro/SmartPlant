#include <DHT.h>
#include <ArduinoJson.h>
#include <Wire.h> 
#include <LiquidCrystal.h>

// Configuration
#define DHTPIN 2     // Digital pin connected to the DHT sensor
#define DHTTYPE DHT11   // DHT 11
#define SOIL_PIN A0  // Analog pin for soil moisture
#define PHOTOCELL_PIN A1 // Analog pin for photocell
#define LM35_PIN A2 // Analog pin for LM35

#define LEVEL_PIN A3 // Analog pin for Water Level Sensor (Droplet Detection)
#define MOTOR_PIN1 4 // Digital pin for Motor IN1
#define MOTOR_PIN2 5 // Digital pin for Motor IN2 (Optional if using simple driver)

// LCD Pin Definitions (Parallel Mode)
// RS, E, D4, D5, D6, D7
const int rs = 22, en = 23, d4 = 24, d5 = 25, d6 = 26, d7 = 27;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);

DHT dht(DHTPIN, DHTTYPE); // Restored DHT Declaration

// Interval for sending data (milliseconds)
const long interval = 5000; 
unsigned long previousMillis = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();
  
  // Setup Motor Pins
  pinMode(MOTOR_PIN1, OUTPUT);
  pinMode(MOTOR_PIN2, OUTPUT);
  digitalWrite(MOTOR_PIN1, LOW); // Motor Off initially
  digitalWrite(MOTOR_PIN2, LOW);

  // Setup Level Sensor (Analog usually doesn't need pinMode, but good practice to leave as default or regular input)
  pinMode(LEVEL_PIN, INPUT_PULLUP); 

  // Setup LCD
  lcd.begin(16, 2);
  // lcd.backlight(); // Not creating object for backlight, usually hardwired or via pin
  lcd.setCursor(0,0);
  lcd.print("Smart Plant");
  lcd.setCursor(0,1);
  lcd.print("System Starting");

  // Allow sensors to stabilize
  delay(2000);
  lcd.clear();
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // Read sensors
    float h = dht.readHumidity();
    float t_dht = dht.readTemperature(); // Celsius
    int soilValue = analogRead(SOIL_PIN);
    
    // Read Photocell
    int lightValue = analogRead(PHOTOCELL_PIN);
    
    // Read LM35
    int lm35Raw = analogRead(LM35_PIN);
    float t_lm35 = (lm35Raw * 5.0 * 100.0) / 1024.0;

    // Calculate Precise Temperature (Average of DHT and LM35)
    // Check if DHT is valid before averaging, otherwise use LM35
    float preciseTemp;
    if (!isnan(t_dht)) {
      preciseTemp = (t_dht + t_lm35) / 2.0;
    } else {
      preciseTemp = t_lm35;
    }

    // Read Water Level (Analog)
    int waterRaw = analogRead(LEVEL_PIN);
    int waterLevel = 0;
    // Logic for Pull-Up Sensor (Active Low)
    // Dry = ~1023 (High)
    // Wet = < 800 (Low, conductivity to ground)
    if (waterRaw < 800) { 
        waterLevel = 1;
    }

    // Interpret Soil Moisture
    // User data: 703 is Wet. Assuming Standard Resistive (1023 Dry).
    // Threshold: < 800 = Wet (Nam), > 800 = Dry (Quruq)
    String soilStatus;
    if (soilValue < 800) {
      soilStatus = "Nam";   // Wet/Moist in Uzbek
    } else {
      soilStatus = "Quruq"; // Dry in Uzbek
    }

    // Update LCD
    lcd.clear(); // Clear to ensure clean slate for variable lengths
    lcd.setCursor(0,0);
    lcd.print("T:"); 
    lcd.print(preciseTemp, 1);
    lcd.print("C S:");
    lcd.print(soilStatus);
    
    lcd.setCursor(0,1);
    lcd.print("H:");
    lcd.print(h, 0);
    lcd.print("% W:");
    lcd.print(waterLevel == 1 ? "Bor" : "Yo'q"); // Water Level in Uzbek (Bor=Exists, Yo'q=None)

    // Check if critical reads failed (DHT only, LM35 is always analog read)
    if (isnan(h) && isnan(t_dht)) {
       // If DHT failed completely, we might still want to send LM35 data, 
       // but original logic returned. We'll keep it but maybe relax it later.
       // For now, if DHT fails, we return as per original safety.
       return; 
    }

    // Create JSON document
    StaticJsonDocument<256> doc;
    doc["timestamp"] = millis();
    doc["soil"] = soilValue;
    doc["soil_status"] = soilStatus; // Uzbek Status
    doc["temp"] = t_dht;       
    doc["hum"] = h;
    doc["light"] = lightValue; 
    doc["temp_lm35"] = t_lm35; 
    doc["temp_precise"] = preciseTemp; // Combined Precise Temp
    doc["water_level"] = waterLevel; 
    doc["water_raw"] = waterRaw; 

    // Serialize to JSON and send over Serial
    serializeJson(doc, Serial);
    Serial.println(); 
  }

  // Check for incoming serial commands
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == 'W') {
       // Water Command Received
       // Parse duration (e.g., W5 = 5 seconds)
       int duration = Serial.parseInt();
       if (duration <= 0) duration = 3; // Default to 3 seconds if no number provided
       if (duration > 10) duration = 10; // Cap at 10 seconds for safety

       // Double check water level before pumping
       int currentWaterRaw = analogRead(LEVEL_PIN);
       if (currentWaterRaw < 800) { // Active Low Check
          lcd.setCursor(0,1);
          lcd.print("Watering...     ");
          
          digitalWrite(MOTOR_PIN1, HIGH);
          // digitalWrite(MOTOR_PIN2, LOW); // If using H-Bridge
          delay(duration * 1000); // Run pump for 'duration' seconds
          digitalWrite(MOTOR_PIN1, LOW);
          
          lcd.setCursor(0,1);
          lcd.print("Done!           ");
          delay(1000); // Show "Done" for a second before loop clears it potentially
       } else {
          // Safety: Tank empty
          lcd.setCursor(0,1);
          lcd.print("Error: Empty!   ");
          delay(2000);
       }
    }
  }
}
