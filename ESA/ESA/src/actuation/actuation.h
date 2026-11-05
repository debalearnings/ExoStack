#pragma once
#include <utils.h>
#include "sensing/SoftwareAnalogFilters.h"

// UPDATE BELOW ENUM FOR NEW ACTUATOR
typedef enum {
    NO_ACT = 0,    
    // PPRs
    ACT_FESTO_VEAB_L26,   // veab_l_26_d9_14_v2_1r1
    // ACT_FESTO_VPPE_3_1,       // vppe_3_1_1_/_8_10_010_e1t
    // ACT_SMC_ITV1050_312BL2,   // ITV1050_312BL2
    
    // MOTORS
    // ACT_RESERVED,             // RESERVED, future work

    // I2C Motor Drivers
    ACT_SG90_SERVO,              // PCA9685 16-Ch I2C Motor Driver

    // **** NEW ACTUATOR / ACT. DRIVERS / LED DRIVER - ADD BELOW ***
    // ACT_XYZ                // XYZ Actuator
    
    LED_TEST,

    ACTUATOR_COUNT            // !! Auto calculated - dont touch !!
} ActuatorType;








struct ActInfo {
    rcl_subscription_t sub;
    const char* topicName = "";
    std_msgs__msg__Float32 msg2;
    float val;

    ActuatorType act_type;    

    int8_t out_gpio_i2caddr;   // gpio or i2c address for actuation
    int8_t extra_info1; // any additional actuator specific info, such as for first ppr we need an external exhaust gpio pin
    int8_t extra_info2; // some other additional info
}; extern ActInfo* actuators;

typedef void (*ActuatorInitFn)(ActInfo* sub);
typedef void (*ActuationFn)(ActInfo* sub);

typedef struct {
    ActuatorInitFn init;
    ActuationFn run;
} ActuatorModuleEntry;

extern SoftwareAnalogFilters _act_fb_filt;
extern FilterConfig* act_fb_filter_config;
extern uint8_t _act_fb_idx;

class ActuatorRegistry {
public:
    static ActuatorRegistry& instance();

    // Refer macro below (for actuator registering)
    void registerModule(ActuatorType id, 
                        ActuatorInitFn init_fn, 
                        ActuationFn run_fn);

    // Device specific init fn for ith actuator
    void init(ActInfo* sub);

    // Device specific actuation fn (sub.val, refer struct above) for ith actuator
    void actuate(ActInfo* sub);


private:
    ActuatorRegistry();
    
    ActuatorModuleEntry _entries[ACTUATOR_COUNT];
    bool _registered[ACTUATOR_COUNT];
     
};

// Macro for registering specific actuator module codes (.h+.ccp)
#define REGISTER_ACTUATOR(ID, INIT_FN, ACT_FN)          \
    namespace {                                         \
        struct AutoReg_##ID {                           \
            AutoReg_##ID() {                            \
                ActuatorRegistry::instance().registerModule( \
                    ID,                                 \
                    INIT_FN,                            \
                    ACT_FN                              \
                );                                      \
            }                                           \
        };                                              \
        static AutoReg_##ID _auto_reg_##ID;             \
    }


class Actuation {

    public:
        Actuation();
        
        // Public APIs for main cpp
        void init_(ActInfo* sub);
        void actuate_(ActInfo* sub);

};
