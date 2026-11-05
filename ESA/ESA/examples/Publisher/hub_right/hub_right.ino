/*
  hub_right - ESA sensing hub (worked example of the ExoStack user manual, Sec. 2.2-A)

  Publishes 21 channels on /hub_right: two 9-channel IMUs, two load cells and one
  foot-pressure sensor. The channel order matches hubs.hubr.sensors in
  exo_stack_resources/config/sensors.yaml.
*/
#include "ESA.h"

SoftExoWalk exo;

DeviceConfig deviceList[] = {
  // type  addr/pin  name     extra_info1   misc1       misc2
  { I2C,   0x4A,     "IMU_T", MAIN,         9 },                      // thigh IMU, 9 channels
  { I2C,   0x4A,     "IMU_S", AUX1,         9 },                      // shank IMU, same address on the 2nd bus
  { I2C,   0x2A,     "LC_F",  MAIN,        -0.0243f,  -299.094f },    // load cell: slope, zero offset
  { I2C,   0x2A,     "LC_E",  AUX1,        -0.0242f,  -299.096f },
  { AI,    34,       "FSR",   MEDIAN,       3 },                      // median filter, window 3
};
const size_t deviceList_len = sizeof(deviceList) / sizeof(deviceList[0]);

void setup() {
  exo.setupCommunication("wifi", "YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "192.168.1.10", 8888);
  // USB alternative: exo.setupCommunication("usb");  (then do not use Serial in the sketch)
  if (exo.initializeSystem()) {
    exo.setupNode("hub_right_node");
    exo.setupPublisher("/hub_right", 100);   // topic, rate in Hz
    exo.bootSystem();                        // always last
  }
}

void loop() {
  exo.readSensorsData();
  exo.publish(true);                         // true: rebuild the link automatically if the agent restarts
}
