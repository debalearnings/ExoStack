// Exosuit Sensor Suite - .cpp file
#include "ESA.h"

// User inputs
int ros_pub_rate_hz = 100;
unsigned long offset_time = 0;  // Used to time-sync all publishers connected to a single subscription point. Refer Python codes for more details.

uint8_t NUM_DEVICES = 0;             // total devices
volatile uint8_t NUM_DEVICES_Indices = 0;   // used for defining data per device
volatile uint8_t sensorIndices = 0; // common data accessed by many sensor headers
int debug_flag = -1;

FilterConfig* filters_config = nullptr;

// ROS node and msg type declaration
rcl_publisher_t publisher1;
rcl_subscription_t subscriber1;
std_msgs__msg__Int32 msg1;
sensor_msgs__msg__LaserScan msg;
rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rcl_timer_t timer;

// ----- LOCAL FUNCTIONS -----
#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){_error_loop();}}
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){}}
#define EXECUTE_EVERY_N_MS(MS, X)  do { \
  static volatile int64_t init = -1; \
  if (init == -1) { init = uxr_millis();} \
  if (uxr_millis() - init > MS) { X; init = uxr_millis();} \
} while (0)\

void timer_callback(rcl_timer_t * timer, int64_t last_call_time){
  RCLC_UNUSED(last_call_time);
  if (timer != NULL) {
    RCSOFTCHECK(rcl_publish(&publisher1, &msg, NULL));
  }
}

void trigger_callback(const void * msgin) {
    offset_time = millis(); // Received message for time sync;
}

void readAct_SubData_callback(const void * msgin, void * context) {  
    // if(context == nullptr || msgin == nullptr)  return;

    ActInfo *s = (ActInfo*) context;
    if(s == nullptr) return;

    const std_msgs__msg__Float32 * msg_in = (const std_msgs__msg__Float32 *)msgin;

    s->val = msg_in->data;
}

void SoftExoWalk::_error_loop(){
    while(true){
        digitalWrite(ROS_LED_PIN, !read_di_pin(ROS_LED_PIN));
        delay(100);
    }
}

// WiFi
void SoftExoWalk::setupCommunication(
    char* commMode, 
    char* ssidX, 
    char* passwordX, 
    char* serverX, 
    uint16_t serverPortX, 
    uint16_t max_wifi_connection_trial_timeX,
    char* ros_connect_err_msgX
    ){
    // WiFi setup
    _rosnode_data.mode = commMode;
    
    _rosnode_data.wifi_cnt_time = max_wifi_connection_trial_timeX;
    _rosnode_data.ssid = ssidX;
    _rosnode_data.pwd = passwordX;
    _rosnode_data.server = serverX;
    _rosnode_data.port = serverPortX;    

    _microros_transport(commMode);     

}//setupCommunication - for wifi

// USB Serial
void SoftExoWalk::setupCommunication(char* commMode){

    _rosnode_data.mode = commMode;

    _microros_transport(commMode);

}//setupCommunication - for usbserial

void SoftExoWalk::_microros_transport(char* commMode) {
    
    if(strcmp(commMode, "wifi") == 0) 
        wifi_connected = _connectToWiFi();

    else if(strcmp(commMode, "usb") == 0) {
        set_microros_transports();
        delay(100);
    }


}

bool SoftExoWalk::_connectToWiFi() {
    bod_disable();  //  refer wdt_bo.h
    delay(100);

    set_microros_wifi_transports(_rosnode_data.ssid, _rosnode_data.pwd, _rosnode_data.server, _rosnode_data.port);

    pinMode(ROS_LED_PIN, OUTPUT);
    digitalWrite(ROS_LED_PIN, HIGH);

    delay(100);

    if(millis()+200 <= _rosnode_data.wifi_cnt_time*1000)
        return true;
    else
        return false;

} //_connectToWiFi

bool SoftExoWalk::initializeSystem() {
    
    bool systemReady = true;
    NUM_DEVICES = uint8_t(deviceList_len);

    if(strcmp(_rosnode_data.mode, "wifi") == 0 && !wifi_connected) {
        delay(5);
        emergencyShutdown(); 
    }

    // Initialization
    bod_enable();   //  refer wdt_bo.h
    for(int i = 0; i< NUM_DEVICES; i++) {
        
        if(!deviceList[i].IP_type){
            delay(5);
            emergencyShutdown();
        }
        else {
        // 1 - AI, 2 - AO, 3 - DI, 4 - DO, 5 - I2C, 6 - SPI, 7 - UART
        bool i2cDeviceInitSuccess = false;        
        // bool spiDeviceInitSuccess = false;
        // bool uartDeviceInitSuccess = false;

        if(deviceList[i].IP_type == 1){
            
            if(_name_contains_bat(deviceList[i].name))
                batt_pos = i;

            // Init
            set_adc_pin(deviceList[i].pin_or_address);
            systemReady&= true;
            
            deviceList[NUM_DEVICES_Indices].data_per_device = 1; 
            
            if(deviceList[NUM_DEVICES_Indices].extra_info1 - 8 >= 1) 
                _analogFilters_reqd++;
            
            sensorIndices++; 
            NUM_DEVICES_Indices++;

        }
        else if(deviceList[i].IP_type == 2){

            // Init
            
            
            //set_di_pin(deviceList[i].pin_or_address, normal); // mention pullup instead of NORMAL, if using pullups
            
            
            //////////////////////////////////////////////////////////
            DI_TYPES pinModeType=normal;
            
            if(deviceList[i].extra_info1==20)
            {
            pinModeType=normal;
            }
            
            else if(deviceList[i].extra_info1==21)
            {
            pinModeType=pulldown;
            }
            
            else if(deviceList[i].extra_info1==22)
            {
            pinModeType=pullup;
            }
            
            else
            {
            pinModeType=normal;
            }
            
            set_di_pin(deviceList[i].pin_or_address, pinModeType);
            ///////////////////////////////////////////////////////
            
            
            
            
            systemReady&= true;

            sensorIndices++;
            deviceList[NUM_DEVICES_Indices].data_per_device = 1; NUM_DEVICES_Indices++;
        
        }
        else if(deviceList[i].IP_type == 3) {

            if(deviceList[i].extra_info1 == 0) _i2c_main_def = true;
            else if(deviceList[i].extra_info1 == 1) _i2c_aux1_def = true;
                 
            i2cDeviceInitSuccess = _i2c.i2c_init(i);
            NUM_DEVICES_Indices++;

            // Initialisation
            if(i2cDeviceInitSuccess)
                systemReady&= true; 
            else
                systemReady&= false; // One I2C device failed, mark system as not ready

        }
        else {
            systemReady&= false; // Unknown input device, cannot initialise, mark system as not ready

        }

        }
    }

    if(!_init_analog_filters(_analogFilters_reqd))
        return false;
    
    delay(100);
    
    return systemReady;
} //initializeSystem

bool SoftExoWalk::_init_analog_filters(int no_analog_fitlers_reqd) {
    
    if(no_analog_fitlers_reqd > 0) {
        filters_config = (FilterConfig*)calloc(_analogFilters_reqd, sizeof(FilterConfig));
        if(!filters_config) 
            return false;
    }
    else
        return true;

    uint8_t _analogFilters_i = 0;
    for(int i = 0; i < NUM_DEVICES; i++) {
        if(deviceList[i].IP_type == 1) {
            if(deviceList[i].extra_info1 >= 9){
        
                filters_config[_analogFilters_i].gpio = deviceList[i].pin_or_address;
                filters_config[_analogFilters_i].name = deviceList[i].name;
                filters_config[_analogFilters_i].filter_type = deviceList[i].extra_info1 - 8;
                filters_config[_analogFilters_i].param1 = deviceList[i].dev_misc_data;
                filters_config[_analogFilters_i].param2 = deviceList[i].dev_misc_data2;

                _analogFilters_i++;
            }
        }
    }

    if(no_analog_fitlers_reqd == _analogFilters_i) return true;

    return false;
}

void SoftExoWalk::setupNode(char* nodeNameX) {
    _rosnode_data.nodeName = nodeNameX;
}

void SoftExoWalk::setupPublisher(char* topicNameX, int pub_rate) {
    _rosnode_data.topicName = topicNameX;
    _set_pubRate(pub_rate);   
}

void SoftExoWalk::_set_pubRate(int pub_rate) {
    if(NUM_DEVICES > 0) {
        ros_pub_rate_hz = pub_rate;
        _ros_pub_ms = pub_rate > 0 ? (1000/pub_rate) : NULL;

        if(_analogFilters_reqd > 0 && filters_config!= nullptr)
            _filt.Init(filters_config, _analogFilters_reqd, pub_rate);
    }
}

void SoftExoWalk::setupActuation(char* ros2_act_topic, ActuatorType act_dev, uint8_t out_gpio_i2c_addr, int8_t extra_data1, int8_t extra_data2) {

    _ros2act_topics[_actCount] = ros2_act_topic; // topic
    _ros2act_gpio_or_i2c_addr[_actCount] = out_gpio_i2c_addr;   // actuation dac pin / i2c address
    _ros2act_extra_info1[_actCount] = (extra_data1 > 0) ? extra_data1 : 0;    // first additional data, if any
    _ros2act_extra_info2[_actCount] = (extra_data2 > 0) ? extra_data2 : 0;    // second additional data, if any
    
    // Store the actuator type
    _ros2act_type[_actCount] = (uint8_t)act_dev;

    _actCount++;

}

void SoftExoWalk::bootSystem() {
    delay(100);
    
    // Keep WDG timer initialisation disabled to avoid any conflict before booting
    wdt_end();  //  refer wdt_bo.h 

    _create_entities();

    if(ros_connected && NUM_DEVICES > 0) {
        // initializing ros message data
        // msg.ranges.data = (float*)malloc(NUM_DEVICES * sizeof(float));
        // if (!msg.ranges.data) return;
        // msg.ranges.size = NUM_DEVICES;
        msg.intensities.data = (float*)malloc(sensorIndices * sizeof(float));
        if (!msg.intensities.data) return;
        msg.intensities.size = sensorIndices;
        
        msg.range_min = NUM_DEVICES;
        msg.range_max = sensorIndices;

        // for(int i = 0; i < NUM_DEVICES; i++)
        //     msg.ranges.data[i] = deviceList[i].data_per_device;
        for(int i = 0; i < sensorIndices; i++)
            msg.intensities.data[i] = 0.0;
        
    }
    
    wdt_begin(WDG_TM);   // 3 secs default 
    
    sensorIndices = 0;
}

void SoftExoWalk::_create_entities() {
    delay(100);
    allocator = rcl_get_default_allocator();

    //create init_options
    RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

    // create node
    RCCHECK(rclc_node_init_default(&node, _rosnode_data.nodeName, "", &support));

    const unsigned int timer_timeout = _ros_pub_ms;
    uint8_t pub = 0;
    if(NUM_DEVICES > 0) {
        // create sensor data publisher
        RCCHECK(rclc_publisher_init_best_effort(
            &publisher1,
            &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, LaserScan),
            _rosnode_data.topicName));

        // create timer,
        
        RCCHECK(rclc_timer_init_default(
            &timer,
            &support,
            RCL_MS_TO_NS(timer_timeout),
            timer_callback));

        //create subscriber    
        RCCHECK(rclc_subscription_init_best_effort(
        &subscriber1, 
        &node, 
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32), 
        "sync_trigger"
        ));    
        
        pub = 2;
    }

    uint8_t _act_i = 0;
    if(_actCount > 0) {  // user defined actuators
        // _actuator.actuation_fb_init(_actCount);

        if(_act_i == 0) {
            actuators = (ActInfo*)calloc(_actCount, sizeof(ActInfo));
            if (!actuators) {
                Serial.println("ERROR: Actuator subscriptions allocation failed");
                _actCount = 0;
                return;
            }
            // memset(actuators, 0, _actCount * sizeof(ActInfo));
        }

        while(_act_i < _actCount) {
            
            // strcpy
            actuators[_act_i].topicName = _ros2act_topics[_act_i];
            if(actuators[_act_i].topicName == NULL) return;

            actuators[_act_i].act_type = (ActuatorType)_ros2act_type[_act_i];
            actuators[_act_i].out_gpio_i2caddr = _ros2act_gpio_or_i2c_addr[_act_i];
            actuators[_act_i].extra_info1 = _ros2act_extra_info1[_act_i];
            actuators[_act_i].extra_info2 = _ros2act_extra_info2[_act_i];
            

            std_msgs__msg__Float32__init(&actuators[_act_i].msg2);
            actuators[_act_i].msg2.data = -1.0;

            

            RCCHECK(rclc_subscription_init_best_effort(
            &actuators[_act_i].sub, 
            &node, 
            ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32), 
            actuators[_act_i].topicName
            ));

            _act_i++; 
        }
    }

    // free(_ros2act_topics);
    // free(_ros2act_type);
    // free(_ros2act_gpio_or_i2c_addr);
    // free(_ros2act_fbIdx);
    // free(_ros2act_extra_info1);
    // free(_ros2act_extra_info2);
    // free(_act_i);
    

    // create executor
    RCCHECK(rclc_executor_init(&executor, &support.context, pub+_actCount, &allocator));
    if(NUM_DEVICES > 0) {
        RCCHECK(rclc_executor_add_timer(&executor, &timer));
        RCCHECK(rclc_executor_add_subscription(&executor, &subscriber1, &msg1, &trigger_callback, ON_NEW_DATA)); 
    }

    for(uint8_t i = 0; i < _actCount; i++) {
        _actuator.init_(&actuators[i]);

        rclc_executor_add_subscription_with_context(&executor, &actuators[i].sub, &actuators[i].msg2, &readAct_SubData_callback, (void*)&actuators[i], ON_NEW_DATA);

    }

    

    ros_connected = true;
}

void SoftExoWalk::_destroy_entities() {
    delay(500);

    rmw_context_t * rmw_context = rcl_context_get_rmw_context(&support.context);
    (void) rmw_uros_set_context_entity_destroy_session_timeout(rmw_context, 0);

    rcl_publisher_fini(&publisher1, &node);
    rcl_timer_fini(&timer);
    rclc_executor_fini(&executor);
    rcl_node_fini(&node);
    rclc_support_fini(&support);

    if(actuators)
        free(actuators);
}

void SoftExoWalk::actuate(char* curr_topic) {

    _run_executor();
    
    if(curr_topic == "") {
        for(uint8_t i = 0; i<_actCount; i++) {
            wdt_rst();
            _actuator.actuate_(&actuators[i]);

        }
    }
    
    else {
        for(uint8_t i = 0; i<_actCount; i++) {
            if(strcmp(actuators[i].topicName, curr_topic) == 0) {
                wdt_rst();
                _actuator.actuate_(&actuators[i]);
            }
        }
    }
}

void SoftExoWalk::readSensorsData() {

    for (int curr_device = 0; curr_device < NUM_DEVICES; curr_device++) {
        
        switch (deviceList[curr_device].IP_type) {
            // 1 - AI, 2 - DI, 3 - I2C, ...rest to be added
            case 1: {// AI pin
                float val = 0.0;
                val = read_adc_pin(deviceList[curr_device].pin_or_address) * _ADC_SCALE; // from data_bus

                if(deviceList[curr_device].extra_info1 - 8 >= 1){
                    val = _filt.analog_filter(deviceList[curr_device].pin_or_address);
                }

                if(curr_device != batt_pos)   
                    msg.intensities.data[sensorIndices] = val;
                else
                    msg.intensities.data[sensorIndices] = 1.34 * val > 4.2 ? 4.2 : 1.34 * val;

                Serial.print(val); Serial.print(",");
                Serial.println(0.7); 
                sensorIndices++;
                
                break;
            }
            
            case 2: {// DI pin

                msg.intensities.data[sensorIndices] = read_di_pin(deviceList[curr_device].pin_or_address);
                sensorIndices++;

                break;
            }
            
            case 3: {// I2C device
                (void)_i2c.i2c_read(curr_device);

                break;
            }
            

            default:  

                break;
        }
    }

    wdt_rst();
    sensorIndices = 0;
}

void SoftExoWalk::_run_executor() {
    rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
}

void SoftExoWalk::publish(bool ros_reconnection_reqd) {
    // Set timestamp properly
    int64_t current_time = millis();  // Get time in milliseconds
    msg.header.stamp.nanosec = ((current_time-offset_time) % 1000) * 1000000;
    msg.header.stamp.sec = (current_time-offset_time) / 1000;

    if(!ros_reconnection_reqd)
        _run_executor();
    
    else{
        EXECUTE_EVERY_N_MS(_ros_connect_timeout, ros_connected = (RMW_RET_OK == rmw_uros_ping_agent(100, 1)) ? true : false);

        if(ros_connected == true) {
            rcl_ret_t ret = rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
            if(ret == RCL_RET_TIMEOUT || ret == RCL_RET_OK ) {
               // continue
            } 
            else if (ret!=RCL_RET_OK) {
                _executorFailureCount = 0;
            }
            else {
                _executorFailureCount++;
                Serial.println("Executor error, ROS disconnected");
                if(_executorFailureCount > _EXECUTOR_MAX_FAILURES) {
                    _executorFailureCount = 0;
                    ros_connected = false;
                    _destroy_entities();
                }
            }
        }
        else {
            _destroy_entities();
            if(_rosnode_data.mode == "wifi" && WiFi.status() != WL_CONNECTED)
                wifi_connected = _connectToWiFi(); 
            _set_pubRate(ros_pub_rate_hz);
            bootSystem(); // anyway disconnected - added safety check
        }
    }

    wdt_rst();





}

// Misc. utility functions

bool SoftExoWalk::_name_contains_bat(const char* dev_name) {
    if(dev_name[0] == 'B' || dev_name[0] == 'b') {
        if(dev_name[1] == 'A' || dev_name[1] == 'a') {
            if(dev_name[2] == 'T' || dev_name[2] == 't') {
                return true;
            } else return false;
        } else return false;
    }
    else return false;
}

void SoftExoWalk::emergencyShutdown() {
    _destroy_entities();
    _cleanupResources();
    delay(1000);

    if(_i2c_main_def)   Wire.endTransmission();
    if(_i2c_aux1_def)   Wire1.endTransmission();
    
    if(strcmp(_rosnode_data.mode, "wifi") == 0 && wifi_connected) {
        WiFi.disconnect();
        WiFi.mode(WIFI_OFF);
    }
    
    // MCU to go into deep sleep unless reset / reuploaded
    deep_sleep_begin();

}//emergencyShutdown

void SoftExoWalk::_cleanupResources() {
    
    if (msg.ranges.data != NULL) {
        free(msg.ranges.data);
        //clean memory and heap
        msg.ranges.data = NULL;
    }
    
    if (msg.intensities.data != NULL) {
        free(msg.intensities.data);
        //clean memory and heap
        msg.intensities.data = NULL;
    }
    
}

// Getter functions

uint8_t SoftExoWalk::get_actCount() {
    return _actCount;
}

float SoftExoWalk::get_actCMD(uint8_t sub_id) {
    return actuators[sub_id].val;
}

int SoftExoWalk::get_debugFlag() {
    return debug_flag;
}

int SoftExoWalk::get_pubRate() {
    return ros_pub_rate_hz;
}
