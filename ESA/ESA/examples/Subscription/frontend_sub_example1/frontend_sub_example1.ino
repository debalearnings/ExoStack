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

DeviceConfig deviceList[] = {
};
const size_t deviceList_len = sizeof(deviceList) / sizeof(deviceList[0]);

void setup() {
  Serial.begin(57600);

  Serial.print("\n\nLibrary version: ");
  Serial.println(ESA_LIB_VERSION);
  Serial.println(exo1.get_actCount());
  Serial.println();

  // USB COMMS
  exo1.setupCommunication("usb");
  // wifi comms
//  exo1.setupCommunication(
//    "wifi",                     // Communication Mode - wifi is case sensitive
//    "YOUR_WIFI_SSID",             // SSID
//    "YOUR_WIFI_PASSWORD",                 // Password
////    "192.168.1.11",            // Server IP
//    "192.168.1.10",            // Server IP
//    8888,                       // Server Port
//    15                          // Maximum time in secs to try connecting
//  );
// 
  if(exo1.initializeSystem()) {
    exo1.setupNode("HIP_NODE2");
    // setupActuation args - topic name, actuator type, actuation GPIO / I2C add, extra info1, extra info2
//    exo1.setupActuation("right_hip_ppr_cmd_flexion", ACT_FESTO_VEAB_L26, 26, 17, 34);
//    exo1.setupActuation("right_hip_ppr_cmd_extension", ACT_FESTO_VEAB_L26, 25, 5, 39);
    exo1.setupActuation("right_hip_ppr_cmd_extension", ACT_FESTO_VEAB_L26, 26, 17, 34);
    exo1.setupActuation("right_hip_ppr_cmd_extension", ACT_FESTO_VEAB_L26, 25, 5, 39);
//    exo1.setupActuation("servo_test", ACT_PCA9685, 0x40, 0, 50);
    exo1.bootSystem();
  }
  
  pinMode(led, OUTPUT);
  digitalWrite(led, HIGH);
//  Serial.println(exo1.get_actCount());
  
}

void loop() {
  digitalWrite(led, exo1.ros_connected == true ? HIGH : LOW);
  exo1.actuate(); // args optional - user may choose to actuate only a single topic by mentioning topic name
}
