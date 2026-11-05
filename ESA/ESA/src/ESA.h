/*
 * Copyright (C) 2025 Soft Exosuit Sensor Suite
 *
 * Licensed under the PolyForm Noncommercial License 1.0.0.
 * You may not use this file except in compliance with the License.
 * A copy is in the LICENSE file of the repository and at
 *
 * https://polyformproject.org/licenses/noncommercial/1.0.0
 *
 * SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 *

 * Authored by xxxxxxx (CSIR - CMERI) 
 
 */

// Exosuit Sensor Suite - .h file

#ifndef SENSOR_LIB_H
#define SENSOR_LIB_H

#define ESA_LIB_VERSION     (F("1.0"))    // F stores library version in flash memory (PROGMEM) instead of RAM

#include <WiFi.h>
#include <esp_wifi.h>

#include "safety/safety.h"

// Sensor Libraries
#include "sensing/SoftwareAnalogFilters.h"
#include "sensing/ANALOG/analogread.h"
#include "sensing/DIGITAL/digitalread.h"
#include "sensing/I2C/I2C_Manager.h"
// include spi manager, uart manager
#include "sensing/MUX/mux.h"

#include "actuation/actuation.h"

// micro-ros variables, node and msg type declaration
extern rcl_publisher_t publisher1;
extern rcl_subscription_t subscriber1;  // time-sync subscriber
extern rclc_support_t support;
extern rcl_allocator_t allocator;
extern rcl_node_t node;
extern rclc_executor_t executor;
extern rcl_service_t service;
extern rcl_wait_set_t wait_set;
extern rcl_timer_t timer;

class SoftExoWalk {

public:    

    bool wifi_connected = false;
    bool ros_connected = false;

    uint8_t batt_pos; // Mark if any GPIO is reading a battery voltage

    // possible user inputs
    const uint8_t WDG_TM = 3;   // watchdog timer in seconds
    const uint8_t ROS_LED_PIN = 23; // ROS_LED_PIN 3 on PCB, indicate ROS connection failure

    // WiFi communication (works for pub, pub+sub, or sub when topicName omitted)
    void setupCommunication(
        char* commMode,
        char* ssid,
        char* password,
        char* server,
        uint16_t serverPort,
        uint16_t max_wifi_connection_trial_time = 30,     
        char* ros_connect_err_msg = "Failure to connect to ROS2. Check connection and retry, or reset microcontroller."
    );

    // USB Serial communication (pub / pub+sub; sub-only is done by omitting topicName)
    void setupCommunication(char* commMode);


    bool initializeSystem();
    void setupNode(char* nodeNameX = "microROS_Node");

    void setupPublisher(char* topicNameX = "", int pub_rate = 0);
    void setupActuation(char* ros2_act_topic, ActuatorType act_dev, uint8_t out_gpio_i2c_addr, int8_t extra_data1 = -1, int8_t extra_data2 = -1);
    
    void bootSystem();

    void actuate(char* topicName = "");
    void readSensorsData();

    void publish(bool ros_reconnection_reqd = false);

    void emergencyShutdown();

    // helper getters
    uint8_t get_actCount();
    float get_actCMD(uint8_t sub_id);
    int get_debugFlag();
    int get_pubRate();

private:

    I2C_Manager _i2c;
    SoftwareAnalogFilters _filt;
    uint8_t _analogFilters_reqd = 0;
    
    Actuation _actuator;

    bool _i2c_main_def = false;
    bool _i2c_aux1_def = false;
    bool _i2c_aux2_def = false;

    // ROS variables
    struct _node_data {
        char* mode = "";
        char* topicName = "";

        char* nodeName = "";
        char* ssid = "";
        char* pwd = "";
        char* server = "";        
        uint16_t wifi_cnt_time = 30, port = 8888;     
        
        // Note: Only mode and topicName is applicable for USB
    };
    _node_data _rosnode_data;   
    
    uint16_t _ros_connect_timeout = 2000;    
    int _ros_pub_ms = 10;

    uint8_t _actCount = 0;
    char* _ros2act_topics[5];
    int8_t _ros2act_type[5];
    int8_t _ros2act_gpio_or_i2c_addr[5];
    int8_t _ros2act_extra_info1[5];
    int8_t _ros2act_extra_info2[5];
    int8_t _ros2act_fbIdx[5];


    uint8_t _executorFailureCount = 0;
    uint8_t _EXECUTOR_MAX_FAILURES = 5;
    
    uint8_t _imu_basic_all = 0;

    void _microros_transport(char* wifi_or_usb);
    bool _connectToWiFi();
    bool _init_analog_filters(int no_analog_fitlers_reqd = 0);
    void _set_pubRate(int pub_rate = 0);
    void _create_entities();
    void _run_executor();
    void _destroy_entities();

    bool _name_contains_bat(const char* dev_name);
    void _cleanupResources();
    void _error_loop();
    

};// class

#endif // SENSOR_LIB_H