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
#define SAMPLE_INTERVAL 2   // Sampling interval in milliseconds
#define SAMPLES_PER_PACKAGE 32 // Number of samples to send in one package
#define SAMPLING_RATE 224.2//896.8
#define PIN_FOR_INTERRUPT 47

short acc_fifo[SAMPLES_PER_PACKAGE][3];
short gyro_fifo[SAMPLES_PER_PACKAGE][3];
short sensorData[SAMPLES_PER_PACKAGE][6]; // Array to hold the last SAMPLES_PER_PACKAGE samples (8 shorts per sample)

unsigned short packageCount = 0;
BLECharacteristic *pSensorCharacteristic;
bool deviceConnected = false;
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

void setup() {
    Serial.begin(115200);

    // Initialize QMI8658 IMU
    Wire.begin(6, 7);
    QMI8658_init();
    // Configure FIFO in Stream Mode with 32 samples
    QMI8658_config_fifo(0x02, 0b01);
    Serial.println("FIFO configured in stream mode.");
    Serial.println("QMI8658 initialized");

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

void loop()
{

if (QMI8658_fifo_full()) {
    read_fifo();
    delay(100);
  }

}

void read_fifo() {
  //Serial.println("Reading FIFO package...");

  unsigned char num_samples = SAMPLES_PER_PACKAGE; // Number of samples to read from FIFO
  // Read accelerometer and gyroscope data
  QMI8658_read_fifo_data(acc_fifo, gyro_fifo, num_samples);
  uint32_t timestamp = (uint32_t)(esp_timer_get_time()/1000);
  //Serial.print("Timestamp: ");
  //Serial.println(timestamp);
  // store samples in sensorData array
  int sampleCount = 0;     // Counter for the number of samples collected
  for (unsigned char i = 0; i < num_samples; i++) {
    sensorData[sampleCount][0] = acc_fifo[i][0];
    sensorData[sampleCount][1] = acc_fifo[i][1];
    sensorData[sampleCount][2] = acc_fifo[i][2];
    sensorData[sampleCount][3] = gyro_fifo[i][0];
    sensorData[sampleCount][4] = gyro_fifo[i][1];
    sensorData[sampleCount][5] = gyro_fifo[i][2];
    sampleCount++;
  }

   // print data
/*   for (unsigned char i = 0; i < num_samples; i++) {
    Serial.print(sensorData[i][0]);
    Serial.print("\t");
    Serial.print(sensorData[i][1]);
    Serial.print("\t");
    Serial.print(sensorData[i][2]);
    Serial.print("\t");
    Serial.print(sensorData[i][3]);
    Serial.print("\t");
    Serial.print(sensorData[i][4]);
    Serial.print("\t");
    Serial.print(sensorData[i][5]);
    Serial.print("\t");
    Serial.println(timestamp);
  }   */

  if (deviceConnected) {       
    
    // Prepare the byte array to send (SAMPLES_PER_PACKAGE samples * 6 shorts + 6 timestamps)
    uint8_t sendData[SAMPLES_PER_PACKAGE * (6 * 2 ) + 6]; // Each sample has 6 16-bit (2-byte) values + 3 bytes for the timestamp

    unsigned short index = 0;

      // Copy timestamp (24 bits)
      // Secnding extra 0xFF to preceed the timestamp
      sendData[index++] = (uint8_t)(packageCount & 0xFF);
      sendData[index++] = (uint8_t)((packageCount >> 8) & 0xFF); 
      sendData[index++] = (uint8_t)((timestamp >> 16) & 0xFF); // High byte
      sendData[index++] = (uint8_t)((timestamp >> 8) & 0xFF);      // Middle byte
      sendData[index++] = (uint8_t)(timestamp & 0xFF);      // Low byte

    for (unsigned char i = 0; i < SAMPLES_PER_PACKAGE; i++) {
        // Copy accelerometer and gyroscope data
        for (unsigned char j = 0; j < 6; j++) {
            sendData[index++] = (sensorData[i][j] >> 8) & 0xFF; // High byte
            sendData[index++] = sensorData[i][j] & 0xFF;        // Low byte
        }
    }
    // extra suffix
    sendData[index++] = 0xFF;

    //Serial.print("Sending Package...");
    // Send the combined data
    pSensorCharacteristic->setValue(sendData, sizeof(sendData));
    pSensorCharacteristic->notify();  // Notify the client
  }
  // always increment the package count
  packageCount++;
}
  
