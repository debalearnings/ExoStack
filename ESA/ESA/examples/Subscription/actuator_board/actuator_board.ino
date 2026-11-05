/*
  actuator_board - ESA actuation board (worked example of the ExoStack user manual, Sec. 2.2-B)

  Drives one proportional pressure valve per side. The command topics match the
  output_topic of the planners in exo_stack_resources/config/mplanner.yaml.
*/
#include "ESA.h"

SoftExoWalk exo;

DeviceConfig deviceList[] = { };                       // no sensors on this board
const size_t deviceList_len = sizeof(deviceList) / sizeof(deviceList[0]);

void setup() {
  exo.setupCommunication("wifi", "YOUR_WIFI_SSID", "YOUR_WIFI_PASSWORD", "192.168.1.10", 8888);
  if (exo.initializeSystem()) {
    exo.setupNode("actuator_node");
    //                  command topic          actuator name          out  x1  x2
    exo.setupActuation("/right/hip_ppr_cmd", ACT_FESTO_VEAB_L26,   26,  17, 34);
    exo.setupActuation("/left/hip_ppr_cmd",  ACT_FESTO_VEAB_L26,   25,   5, 39);
    exo.bootSystem();
  }
}

void loop() {
  exo.actuate();      // all actuators; exo.actuate("/right/hip_ppr_cmd") drives only that one
}
