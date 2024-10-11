#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEClient.h>
#include <BLEAdvertisedDevice.h>
#include "QMI8658.h"

//#define TARGET_DEVICE_ADDRESS "7c:df:a1:ed:61:55"  // Replace with the target device's MAC address
#define TARGET_DEVICE_ADDRESS "7c:df:a1:ed:60:11" // Replace with the target device's MAC address
#define SERVICE_UUID "12345678-1234-1234-1234-123456789012"  // Replace with your service UUID
#define CHARACTERISTIC_UUID "12345678-1234-1234-1234-123456789013"  // Replace with your characteristic UUID
#define SAMPLES_PER_PACKAGE 32
#define FIFO_SIZE 8
#define SAMPLING_FREQUENCY 112.1//224.2  //112.1 //224.2

BLEClient* pClient;
BLEScan* pBLEScan;
bool deviceConnected = false;
bool foundTargetDevice = false;
unsigned short lastPackageCount = 0;
unsigned short num_packages = SAMPLES_PER_PACKAGE/FIFO_SIZE;
unsigned short delay_time = (unsigned short)FIFO_SIZE/SAMPLING_FREQUENCY*1000*0.8;

void setup() {
    Serial.begin(115200);
    Serial.println("Starting BLE Client...");

    // Initialize BLE device
    BLEDevice::init("ESP32_BLE_Client");  // Use a name for the BLE device

    // Create a BLE client
    pClient = BLEDevice::createClient();

    // Set scan parameters
    pBLEScan = BLEDevice::getScan();  // Create new scan
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);
    pBLEScan->setActiveScan(true);  // Active scan to gather more data
}

void loop() {
    if (!deviceConnected && !foundTargetDevice) {
        // Start scanning
        Serial.println("Scanning for BLE devices...");
        BLEScanResults* scanResults = pBLEScan->start(5, false);  // Scan for 5 seconds, false to not return a pointer

        for (int i = 0; i < scanResults->getCount(); i++) {
            BLEAdvertisedDevice advertisedDevice = scanResults->getDevice(i);

            // Check if the advertised device matches the target device MAC address
            if (advertisedDevice.getAddress().toString() == TARGET_DEVICE_ADDRESS) {
                Serial.print("Found target device: ");
                Serial.println(advertisedDevice.getAddress().toString().c_str());

                // Connect to the device
                if (pClient->connect(&advertisedDevice)) {
                    foundTargetDevice = true;
                    deviceConnected = true;
                    Serial.println("Connected to target device!");
                    pClient->setMTU(512);
                } else {
                    Serial.println("Failed to connect to the target device.");
                }

                // Stop scanning
                pBLEScan->stop();
                break;
            }
        }

        if (!foundTargetDevice) {
            Serial.println("Target device not found. Rescanning...");
        }
    }

    // If connected, read data from the BLE characteristic
    if (deviceConnected) {
        // Get the BLE service
        BLERemoteService* pRemoteService = pClient->getService(SERVICE_UUID);
        if (pRemoteService == nullptr) {
            Serial.println("Failed to find the service UUID.");
            pClient->disconnect();
            deviceConnected = false; // Set the connection status to false
            return;
        }

        // Get the BLE characteristic
        BLERemoteCharacteristic* pRemoteCharacteristic = pRemoteService->getCharacteristic(CHARACTERISTIC_UUID);
        if (pRemoteCharacteristic == nullptr) {
            Serial.println("Failed to find the characteristic UUID.");
            pClient->disconnect();
            deviceConnected = false; // Set the connection status to false
            return;
        }

        // Read the value of the characteristic
        String value = pRemoteCharacteristic->readValue();
        if (value.length() >= (sizeof(uint16_t) * 6 * SAMPLES_PER_PACKAGE + 6)) {  // Ensure enough bytes for 6 samples * 6 shorts + 6 timestamps (3 bytes each)
          unsigned short index = 0;

          for (unsigned char package_num; package_num < num_packages; package_num++) {

            // Create arrays to hold the decoded data
            
            unsigned short package_count_lsb = value[index++];
            unsigned short package_count_msb = value[index++];
            unsigned short package_count = (package_count_msb << 8) | package_count_lsb;

            // make sure not to read the same package twice
            if (package_count <= lastPackageCount){
              break;
            }

          lastPackageCount = package_count;
          short sensorData[SAMPLES_PER_PACKAGE][6]; // 6 samples of 6 shorts
              //Reassemble the timestamp
            unsigned int timestamp = (static_cast<uint32_t>(value[index++]) << 16) | 
                (static_cast<uint32_t>(value[index++]) << 8) | 
                (static_cast<uint32_t>(value[index++]));

            for (unsigned char i = 0; i < FIFO_SIZE; i++) {
                // Copy accelerometer and gyroscope data
                for (int j = 0; j < 6; j++) {
                    sensorData[i][j] = (static_cast<uint8_t>(value[index++]) << 8) | static_cast<uint8_t>(value[index++]);
                }
            }
            index++; // for suffix

            Serial.println("Package count: " + String(package_count));
            // Print the decoded accelerometer and gyroscope data for each sample
            for (unsigned char i = 0; i < FIFO_SIZE; i++) {
              for (int j = 0; j < 6; j++) {
                  Serial.print(sensorData[i][j]);
                  Serial.print("\t");
              }

              //Serial.print("Timestamp: ");
              Serial.print(timestamp + i*1000/SAMPLING_FREQUENCY);
              Serial.println("");
            }
          }
          

          // Add a delay before the next read
          delay(delay_time);
        }
    }
}
