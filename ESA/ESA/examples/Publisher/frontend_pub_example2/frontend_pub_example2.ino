/* Board - ESP-WROOM-32 Development Board, 30 pin version
                                   ____________________
                         (RST)EN -| (WiFi)             |- GPIO23/VSPI_MOSI
            SensVP/ADC1_0/GPIO36 -|    ESP-WROOM-32    |- GPIO22/SCL
            SensVN/ADC1_3/GPIO39 -|                    |- GPIO1/UO_TXD/CLK3
                   ADC1_6/GPIO34 -|                    |- GPIO3/UO_RXD/CLK2
                   ADC1_7/GP1035 -|                    |- GPIO21/SDA
     XTAL32/Touch9/ADC1_4/GPIO32 -|                    |- GPIO19/VSPI_MISO
     XTAL32/Touch8/ADC1_5/GPIO33 -|                    |- GPI018/VSPI_CLK
              DAC1/ADC2_8/GPIO25 -|                    |- GPIO5/VSPI_CS
              DAC2/ADC2_9/GPIO26 -|                    |- GPIO17/U2_TXD
            Touch7/ADC2_7/GPIO27 -|                    |- GPIO16/U2_RXD
   HSPI_CLK/Touch6/ADC2_6/GPIO14 -|                    |- GPIO4/ADC2_0/Touch0
  HSPI_MISO/Touch5/ADC2_5/GPIO12 -|                    |- GPIO2/ADC2_2/Touch2
  HSPI_MOSI/Touch4/ADC2_4/GPIO13 -|                    |- GPI015/ADC2_3/Touch3/HSPI_CS
                             GND -|         ___        |- GND
                              5V -|    .   | U |  .    |- 3V3
                                  |   RST  | S | BOOT  |
                                  |________|_B_|_______|

*/

#include "ESA.h"
#define led 15
SoftExoWalk exo1; 

// topic name - /HIP12 Sensors list:
DeviceConfig deviceList[] = {
  {I2C, 0x36, "ENC2", MAIN},  // I2C device at address 0x36 (AS5600 Encoder): Raw angle, angular speed, cumulative position
  {I2C, 0x36, "ENC1", AUX1},  // I2C device at address 0x36 (AS5600 Encoder): Raw angle, angular speed, cumulative position
  {AI, 36, "P_BTL"},            // Bottle Pressure
  {AI, 34, "R_FLEX", MOV_AVG, 10},         // PPR1_FB  
  {AI, 39, "R_EXT", MOV_AVG, 10},          // PPR2_FB   
  {AI, 32, "STR1"},             // pSTAM 1 Strain sensor
  {AI, 35, "STR2"},             // pSTAM 2 Strain sensor
};
const size_t deviceList_len = sizeof(deviceList) / sizeof(deviceList[0]);

void setup() {
  Serial.begin(57600);

  Serial.print("\n\nLibrary version: ");
  Serial.println(ESA_LIB_VERSION);

  // WIFI COMMS
  exo1.setupCommunication(
    "wifi",                     // Communication Mode - wifi is case sensitive
    "YOUR_WIFI_SSID",             // SSID
    "YOUR_WIFI_PASSWORD",                 // Password
//    "192.168.1.11",            // Server IP
    "192.168.1.10",            // Server IP
    8888,                       // Server Port
    15                          // Maximum time in secs to try connecting
  );

//  exo1.setupCommunication("usb");

  if(exo1.initializeSystem()) {
    exo1.setupNode("HIP_NODE1");  // args - nodeName (default microROS_Node)
    exo1.setupPublisher("HIP12PUB", 100); // args - topicName, pub rate hz (optional, default max)
    exo1.bootSystem();
  }
  pinMode(led, OUTPUT);
  digitalWrite(led, HIGH);
  
}

void loop() {
  digitalWrite(led, exo1.ros_connected == true ? HIGH : LOW);
  exo1.readSensorsData();
  exo1.publish(true);  // args - ros_reconnection_reqd. default false

}
