#include <Arduino.h>
#include <QMI8658.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Define BLE service and characteristic UUIDs
#define SERVICE_UUID "12345678-1234-1234-1234-123456789012"
#define SENSOR_CHARACTERISTIC_UUID "12345678-1234-1234-1234-123456789013"

// Sampling parameters
#define FIFO_SIZE 8
#define SAMPLES_PER_PACKAGE 32 // Number of samples to send in one package
#define SAMPLING_RATE 112.1//224.2//896.8
#define BATTERY_VOLTAGE_PIN 1 

short acc_fifo[FIFO_SIZE][3];
short gyro_fifo[FIFO_SIZE][3];
//short sensorData[SAMPLES_PER_PACKAGE][6]; // Array to hold the last SAMPLES_PER_PACKAGE samples (8 shorts per sample)

// Prepare the byte array to send (SAMPLES_PER_PACKAGE samples * 6 shorts + 6 timestamps)
uint8_t sendData[SAMPLES_PER_PACKAGE * (6 * 2 ) + 6 * SAMPLES_PER_PACKAGE/FIFO_SIZE ]; // Each sample has 6 16-bit (2-byte) values + 3 bytes for the timestamp
unsigned short sendDataIndex = 0;

unsigned short packageCount = 0;
unsigned char packageCountFifo = 0;
BLECharacteristic *pSensorCharacteristic;
bool deviceConnected = false;
unsigned char delay_time = (unsigned char)FIFO_SIZE/SAMPLING_RATE*1000*0.8;
//void IRAM_ATTR fifo_watermark_interrupt();


// Callback for BLE server connections
class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    Serial.println("Connected to device");
    deviceConnected = true;
  }

  void onDisconnect(BLEServer* pServer) {
    Serial.println("Disconnected from device");
    deviceConnected = false;
    pServer->startAdvertising();  // Restart advertising
  }
};

float readBatteryVoltage() {
    // Read the raw ADC value
    int rawValue = analogRead(BATTERY_VOLTAGE_PIN);
    
    // Convert to voltage (assuming a 3.3V reference and a voltage divider)
    float voltage = (rawValue / 4095.0) * 3.3; // Convert ADC value to voltage
    return voltage;
}

void setup() {
    Serial.begin(115200);
    // Initialize QMI8658 IMU
    Wire.begin(6, 7);
    Wire.setClock(400000); // Set I2C clock to 400 kHz
    QMI8658_init();
    // Configure FIFO in Stream Mode with 64 samples
    QMI8658_config_fifo(0x01, 0b00);
    Serial.println("FIFO configured in stream mode.");
    Serial.println("QMI8658 initialized");

    // Read battery voltage
    float batteryVoltage = readBatteryVoltage();
    Serial.print("Battery Voltage: ");
    Serial.println(batteryVoltage);

    // Attach interrupt to the watermark
    //QMI8658_write_reg(QMI8658Register_Ctrl7, (1<<7)); // ENABLE SyncSample Mode
    //attachInterrupt(digitalPinToInterrupt(PIN_FOR_INTERRUPT), fifo_watermark_interrupt, RISING); // Replace with actual pin
    //Serial.println("FIFO configured with watermark interrupt.");

    // Initialize BLE
    BLEDevice::init("ESP32S3_IMU_Sender");
    BLEServer *pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());


    // Print the MAC address of the Arduino device (BLE server)
    Serial.print("BLE Server MAC Address: ");
    Serial.println(BLEDevice::getAddress().toString().c_str());

    // Create BLE service
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // Create a characteristic for combined accelerometer and gyroscope data
    pSensorCharacteristic = pService->createCharacteristic(
        SENSOR_CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pSensorCharacteristic->addDescriptor(new BLE2902());

    // Start the service
    pService->start();

    // Start advertising
    pServer->getAdvertising()->start();
    Serial.println("Waiting for a client connection..."); 

    // Initial delay for stability
    delay(2000);
}

void loop() {
// only sample signal if connected to bluetooth
if (deviceConnected) {
  unsigned short fifo_count = QMI8658_fifo_count();
  if (fifo_count/6 >= FIFO_SIZE) {
      read_fifo();
      delay(delay_time);
    }
  } else {
  // sleep for 2 second to save energy
  delay(2000);
  }
}

void read_fifo() {
  //Serial.println("Reading FIFO package...");

  unsigned char num_samples = FIFO_SIZE; // Number of samples to read from FIFO
  // Read accelerometer and gyroscope data
  QMI8658_read_fifo_data(acc_fifo, gyro_fifo, num_samples);
  uint32_t timestamp = (uint32_t)(esp_timer_get_time()/1000);
  //Serial.print("Timestamp: ");
  //Serial.println(timestamp);

  // print data
  //for (unsigned short i = 0; i < FIFO_SIZE; i++) {
  //  Serial.print(packageCount);
  //  Serial.print("\t");
  //  Serial.print(acc_fifo[i][0]);
  //  Serial.print("\t");
  //  Serial.print(acc_fifo[i][1]);
  //  Serial.print("\t");
  //  Serial.print(acc_fifo[i][2]);
  //  Serial.print("\t");
  //  Serial.print(gyro_fifo[i][0]);
  //  Serial.print("\t");
  //  Serial.print(gyro_fifo[i][1]);
  //  Serial.print("\t");
  //  Serial.println(gyro_fifo[i][2]);
  //}
  //Serial.print("");

  // Copy timestamp (24 bits)
  // Secnding extra 0xFF to preceed the timestamp
  sendData[sendDataIndex++] = (uint8_t)(packageCount & 0xFF);
  sendData[sendDataIndex++] = (uint8_t)((packageCount >> 8) & 0xFF); 
  sendData[sendDataIndex++] = (uint8_t)((timestamp >> 16) & 0xFF); // High byte
  sendData[sendDataIndex++] = (uint8_t)((timestamp >> 8) & 0xFF);      // Middle byte
  sendData[sendDataIndex++] = (uint8_t)(timestamp & 0xFF);      // Low byte

  for (unsigned char i = 0; i < FIFO_SIZE; i++) {
      // Copy accelerometer and gyroscope data
      for (unsigned char j = 0; j < 3; j++) {
          sendData[sendDataIndex++] = (acc_fifo[i][j] >> 8) & 0xFF; // High byte
          sendData[sendDataIndex++] = acc_fifo[i][j] & 0xFF;        // Low byte
      }
      for (unsigned char j = 0; j < 3; j++) {
          sendData[sendDataIndex++] = (gyro_fifo[i][j] >> 8) & 0xFF; // High byte
          sendData[sendDataIndex++] = gyro_fifo[i][j] & 0xFF;        // Low byte
      }
  }
  sendData[sendDataIndex++] = 0xFF;
  packageCountFifo++;
  
  if (packageCountFifo >= SAMPLES_PER_PACKAGE/FIFO_SIZE) {   
    // send out data
    // extra suffix
    

    //Serial.print("Sending Package...");
    // Send the combined data
    if (deviceConnected) {
      pSensorCharacteristic->setValue(sendData, sizeof(sendData));
      pSensorCharacteristic->notify();  // Notify the client
    }
    packageCountFifo = 0;
    sendDataIndex = 0;
    
  }
  // always increment the package count
  packageCount++;
  
}
  
