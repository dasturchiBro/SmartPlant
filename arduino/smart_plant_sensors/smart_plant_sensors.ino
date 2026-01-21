#include <DHT.h>
#include <ArduinoJson.h>
#include <Wire.h> 
#include <LiquidCrystal_I2C.h>

// ========== PIN CONFIGURATION FOR ARDUINO UNO (USER CUSTOMIZED) ==========
// Digital Pins
#define BUTTON_PIN 2       // Manual watering button (User connected to D2)
#define WATER_LEVEL_PIN 4  // Water level sensor (User connected to D4)
#define MOTOR_PIN1 6       // Water pump motor IN+ (User connected to D6)
#define MOTOR_PIN2 5       // Water pump motor IN- (User connected to D5)
#define DHTPIN 8           // DHT22 sensor (User connected to D8)
#define FAN_INA_PIN 7      // Fan motor INA (User connected)
#define FAN_INB_PIN 10     // Fan motor INB (User connected)
#define HEATER_PIN 9      // Heater simulation (User's 4 Red LEDs)
#define OK_STATUS_PIN 13  // OK Status (User's 4 Green LEDs)
// Pin 3, 11, 12 are available

// Analog Pins
#define SOIL_PIN1 A0       // Soil moisture sensor 1 (User connected to A0)
#define SOIL_PIN2 A1       // Soil moisture sensor 2 (User connected to A1)
#define SOIL_PIN3 A2       // Soil moisture sensor 3 (User connected to A2)
// A3 available
// A4, A5 reserved for I2C (SDA, SCL)

// Sensor Configuration
#define DHTTYPE DHT22      // DHT22 sensor type

// Initialize Components
DHT dht(DHTPIN, DHTTYPE);
LiquidCrystal_I2C lcd(0x27, 16, 2); // I2C address 0x27, 16x2 display

// Timing
const long interval = 5000;  // Send data every 5 seconds
unsigned long previousMillis = 0;

// User-configurable thresholds (can be updated via serial)
int soilThreshold = 250;      // Auto-water if any soil > this value (DRY)
float fanTempThreshold = 28.0;   // Fan ON if temp >= this
float heaterTempThreshold = 18.0; // Heater ON if temp <= this

// Automation flags (can be toggled via serial)
bool autoWaterEnabled = true;
bool autoFanEnabled = true;
bool autoHeaterEnabled = true;

// State variables
bool fanStatus = false;
bool heaterStatus = false;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

// Non-blocking timers
unsigned long lastWateringTime = 0;
const unsigned long wateringRestPeriod = 60000; // 1 minute rest after watering
unsigned long messageStartTime = 0;
const unsigned long messageDuration = 3000;    // 3 seconds for messages
bool isShowingMessage = false;
String currentMessage = "";

void setup() {
  Serial.begin(9600);
  dht.begin();
  
  // Setup Motor Pins
  pinMode(MOTOR_PIN1, OUTPUT);
  pinMode(MOTOR_PIN2, OUTPUT);
  digitalWrite(MOTOR_PIN1, LOW);
  digitalWrite(MOTOR_PIN2, LOW);
  
  // Setup Fan Pins (Motor Module Control)
  pinMode(FAN_INA_PIN, OUTPUT);
  pinMode(FAN_INB_PIN, OUTPUT);
  digitalWrite(FAN_INA_PIN, LOW);
  digitalWrite(FAN_INB_PIN, LOW);
  
  // Setup LED Pins
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(OK_STATUS_PIN, OUTPUT);
  digitalWrite(HEATER_PIN, LOW);
  digitalWrite(OK_STATUS_PIN, HIGH); // ON by default (everything OK)
  
  // Setup Water Level and Button (with pullup)
  pinMode(WATER_LEVEL_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Setup I2C LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Smart Plant");
  lcd.setCursor(0, 1);
  lcd.print("Ishga tushmoqda");  // "Starting" in Uzbek
  
  delay(2000);
  lcd.clear();
}

void loop() {
  unsigned long currentMillis = millis();
  
  // ========== READ SENSORS ==========
  float h = dht.readHumidity();
  float temp = dht.readTemperature(); // Celsius
  
  int soil1 = analogRead(SOIL_PIN1);
  int soil2 = analogRead(SOIL_PIN2);
  int soil3 = analogRead(SOIL_PIN3);
  
  // Water level (digital: 1 = water present, 0 = empty)
  // Inverted because user's sensor returns 0 when full
  int waterLevel = !digitalRead(WATER_LEVEL_PIN);
  
  // Calculate average soil moisture
  int soilAvg = (soil1 + soil2 + soil3) / 3;
  
  // ========== CHECK BUTTON FOR MANUAL WATERING ==========
  int buttonReading = digitalRead(BUTTON_PIN);
  // Detect falling edge (High to Low transition)
  if (buttonReading == LOW && lastButtonState == HIGH) {
    delay(50); // Small debounce delay
    if (digitalRead(BUTTON_PIN) == LOW) {
      triggerWatering(3); // Manual water for 3 seconds
    }
  }
  lastButtonState = buttonReading;
  
  // ========== AUTOMATION LOGIC ==========
  if (!isnan(temp)) {
    // Fan/Heater Control (Mutual Exclusion)
    if (autoFanEnabled && temp >= fanTempThreshold) {
      // Turn ON fan, turn OFF heater
      setFan(true);
      setHeater(false);
    } 
    else if (autoHeaterEnabled && temp <= heaterTempThreshold) {
      // Turn ON heater, turn OFF fan
      setHeater(true);
      setFan(false);
    }
    else {
      // Comfortable zone - turn both OFF
      setFan(false);
      setHeater(false);
    }
  }

  // Update OK Status LEDs (Green)
  // ON only if both Fan and Heater are OFF
  if (!fanStatus && !heaterStatus) {
    digitalWrite(OK_STATUS_PIN, HIGH);
  } else {
    digitalWrite(OK_STATUS_PIN, LOW);
  }
  
  if (autoWaterEnabled && waterLevel == 1) {
    // Only check if we are NOT in the rest period
    if (currentMillis - lastWateringTime >= wateringRestPeriod) {
      // Trigger if any sensor is ABOVE threshold (DRY)
      if (soil1 > soilThreshold || soil2 > soilThreshold || soil3 > soilThreshold) {
        triggerWatering(5);
        lastWateringTime = millis(); // Reset rest timer
      }
    }
  }
  
  // ========== UPDATE LCD DISPLAY ==========
  // Only update sensor data if we aren't showing a temporary message (like "Tayyor!")
  if (isShowingMessage) {
    if (currentMillis - messageStartTime >= messageDuration) {
      isShowingMessage = false;
      lcd.clear();
    }
  }

  if (!isShowingMessage) {
    updateLCD(temp, h, soilAvg, waterLevel);
  }
  
  // ========== SEND DATA VIA SERIAL ==========
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    // Check if DHT read failed
    if (isnan(h) || isnan(temp)) {
      // Still send data with null values
      h = 0;
      temp = 0;
    }
    
    // Create JSON document
    StaticJsonDocument<384> doc;
    doc["timestamp"] = millis();
    doc["soil1"] = soil1;
    doc["soil2"] = soil2;
    doc["soil3"] = soil3;
    doc["soil_avg"] = soilAvg;
    doc["temp"] = temp;
    doc["hum"] = h;
    doc["water_level"] = waterLevel;
    doc["fan_status"] = fanStatus ? 1 : 0;
    doc["heater_status"] = heaterStatus ? 1 : 0;
    
    // Serialize and send
    serializeJson(doc, Serial);
    Serial.println();
  }
  
  // ========== CHECK FOR INCOMING COMMANDS ==========
  processSerialCommands();
  
  delay(100); // Small delay for stability
}

// ========== FUNCTIONS ==========

void triggerWatering(int durationSeconds) {
  // Check water level first (1 = Full, 0 = Empty)
  int currentWaterLevel = !digitalRead(WATER_LEVEL_PIN);
  
  if (currentWaterLevel == 1) {
    // Show temporary message
    isShowingMessage = true;
    messageStartTime = millis();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sug'orilmoqda...");
    
    // Motor on
    digitalWrite(MOTOR_PIN1, HIGH);
    digitalWrite(MOTOR_PIN2, LOW);
    
    // We use a small delay for motor run since it's short, 
    // but better would be non-blocking. For now keeping short delay.
    delay(durationSeconds * 1000); 
    
    digitalWrite(MOTOR_PIN1, LOW);
    
    // Set "Done" message to show for rest of messageDuration
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Tayyor!");
    messageStartTime = millis(); // Reset start time so "Tayyor" shows for full 3s
  } else {
    isShowingMessage = true;
    messageStartTime = millis();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Xato: Suv yo'q!");
  }
}

void setFan(bool state) {
  if (fanStatus != state) {
    fanStatus = state;
    if (state) {
      digitalWrite(FAN_INA_PIN, HIGH);
      digitalWrite(FAN_INB_PIN, LOW);
    } else {
      digitalWrite(FAN_INA_PIN, LOW);
      digitalWrite(FAN_INB_PIN, LOW);
    }
  }
}

void setHeater(bool state) {
  if (heaterStatus != state) {
    heaterStatus = state;
    digitalWrite(HEATER_PIN, state ? HIGH : LOW);
  }
}

void updateLCD(float temp, float hum, int soilAvg, int waterLevel) {
  lcd.setCursor(0, 0);
  
  // Line 1: Temperature and Soil Status
  lcd.print("T:");
  if (!isnan(temp)) {
    lcd.print(temp, 1);
    lcd.print("C ");
  } else {
    lcd.print("--C ");
  }
  
  // Soil status in Uzbek
  if (soilAvg < 500) {
    lcd.print("Nam   "); // Wet
  } else {
    lcd.print("Quruq "); // Dry
  }
  
  // Line 2: Humidity and Water Status
  lcd.setCursor(0, 1);
  lcd.print("N:");
  if (!isnan(hum)) {
    lcd.print(hum, 0);
    lcd.print("% ");
  } else {
    lcd.print("--% ");
  }
  
  lcd.print("S:");
  if (waterLevel == HIGH) {
    lcd.print("Bor  "); // Water available
  } else {
    lcd.print("Yo'q "); // No water
  }
}

void processSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Manual watering command (from bot)
    if (command.startsWith("W")) {
      int duration = command.substring(1).toInt();
      if (duration <= 0) duration = 3;
      if (duration > 10) duration = 10;
      triggerWatering(duration);
    }
    
    // Settings commands
    else if (command.startsWith("SET_SOIL_THRESH:")) {
      soilThreshold = command.substring(16).toInt();
      Serial.print("ACK:SOIL_THRESH:"); Serial.println(soilThreshold);
    }
    else if (command.startsWith("SET_FAN_TEMP:")) {
      fanTempThreshold = command.substring(13).toFloat();
      Serial.print("ACK:FAN_TEMP:"); Serial.println(fanTempThreshold);
    }
    else if (command.startsWith("SET_HEATER_TEMP:")) {
      heaterTempThreshold = command.substring(16).toFloat();
      Serial.print("ACK:HEATER_TEMP:"); Serial.println(heaterTempThreshold);
    }
    else if (command == "AUTO_WATER_ON") {
      autoWaterEnabled = true;
      Serial.println("ACK:AUTO_WATER:1");
    }
    else if (command == "AUTO_WATER_OFF") {
      autoWaterEnabled = false;
      Serial.println("ACK:AUTO_WATER:0");
    }
    else if (command == "AUTO_FAN_ON") {
      autoFanEnabled = true;
      Serial.println("ACK:AUTO_FAN:1");
    }
    else if (command == "AUTO_FAN_OFF") {
      autoFanEnabled = false;
      Serial.println("ACK:AUTO_FAN:0");
    }
    else if (command == "AUTO_HEATER_ON") {
      autoHeaterEnabled = true;
      Serial.println("ACK:AUTO_HEATER:1");
    }
    else if (command == "AUTO_HEATER_OFF") {
      autoHeaterEnabled = false;
      Serial.println("ACK:AUTO_HEATER:0");
    }
    // Manual fan test commands
    else if (command == "TEST_FAN_ON") {
      setFan(true);
      Serial.println("ACK:FAN_TEST:1");
    }
    else if (command == "TEST_FAN_OFF") {
      setFan(false);
      Serial.println("ACK:FAN_TEST:0");
    }
  }
}
