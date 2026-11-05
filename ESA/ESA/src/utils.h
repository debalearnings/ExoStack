#ifndef UTILS
#define UTILS

#include <Arduino.h>
#include <Wire.h>

// Communication libarary headers
#include <micro_ros_arduino.h>
#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <std_msgs/msg/string.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>

#include <std_msgs/msg/int32.h>
#include <std_msgs/msg/float32.h>
// #include <sensor_msgs/msg/joint_state.h>
#include <sensor_msgs/msg/laser_scan.h>

typedef enum : uint8_t {
    NONE = 0,
    AI,
    // AO, - not input, kept in case usage modifies later
    DI,
    // DO, - not input, kept in case usage modifies later
    I2C,
    // MUX,
    // SPI,
    // UART

    SUPPORTED_DEV_COUNT
} SupportedInpTypes;    // AI = 1, DI = 2, I2C = 3

// One underlying type:
typedef enum : uint8_t {
    // I2C Lines  (0 to 7)
    MAIN = 0,   // default
    AUX1,
    AUX2,
    // Reserve
    TOT_I2C_LINES = 7,

    // Analog Filters (start at 9)
    FILTER_NONE = 8,
    MOV_AVG,    // default 9
    MEDIAN,
    EXPONENTIAL,
    BUTTER2_LPF,
    BUTTER2_HPF,
    BUTTER2_BPF,
    BUTTER2_NOTCH,
    // Reserve
    
    TOT_ANALOG_FILTERS,  // MOV_AVG = 9, MEDIAN = 10, EXPONENTIAL = 11, BUTTER2_LPF = 12, BUTTER2_HPF = 13, BUTTER2_BPF = 14, BUTTER2_NOTCH = 15
	
    ////////////////////////////////////////////
    NORMAL=20,
    PDOWN,
    PUP
    ////////////////////////////////////////////

} DeviceExtraInfo;


// Device Config Data structure
struct DeviceConfig {
    SupportedInpTypes IP_type;    // Input Device type; Currently supported - AI, DI, I2C, MUX (both AI and I2C)
    uint8_t pin_or_address;      // Pin number AI, AO, DI, DO, SPI (for CS pin only) and UART, or address (I2C)
    const char* name;            // Device name - max 4 characters
    DeviceExtraInfo extra_info1;     // User mentions if I2C device on "MAIN", "AUX1" (19,18) ; or which kind of analog filtering user wants ; user changeable
    float dev_misc_data;
    float dev_misc_data2;
    
    uint8_t data_per_device;     // Tells no. of data populated from a device (imp for I2C / SPI devices)
};
// struct DeviceConfig;
extern DeviceConfig deviceList[];
extern const size_t deviceList_len;

extern uint8_t NUM_DEVICES;             // total devices
extern volatile uint8_t NUM_DEVICES_Indices;   // used for defining data per device
extern volatile uint8_t sensorIndices;       // running total of data slots across devices

extern std_msgs__msg__Int32 msg1;
// extern sensor_msgs__msg__JointState msg; 
extern sensor_msgs__msg__LaserScan msg; 
extern int ros_pub_rate_hz;  // common data accessed by main publisher and 2nd order analog filters
/*
Laser Scan Message:
Header header
float32 angle_min
float32 angle_max
float32 angle_increment
float32 time_increment
float32 scan_time
float32 range_min
float32 range_max
float32[] ranges        // array range between range_min and range_max
float32[] intensities   // array range between range_min and range_max
*/

// Cache for sensor data indices
constexpr uint8_t _MAX_SENSOR_INIT_RETRIES = 5;
constexpr float _PI = 3.14159265359;

// --- USER DEFINED CONSTANTS ---
// bno085 imu
constexpr float _RPY_CONV = 180.0 / _PI;
// encoder
constexpr float _RAD_TO_DEG = 360.0 / (2*_PI);

constexpr float _ADC_SCALE = 3.3 / 4095.0;

#endif
