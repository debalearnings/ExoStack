// I2C_Manager.h
#pragma once
#include "utils.h"
#include "sensing/SoftwareAnalogFilters.h"

constexpr uint8_t MAIN_SDA = 21;
constexpr uint8_t MAIN_SCL = 22;
constexpr uint32_t MAIN_I2C_SPEED = 400000;

constexpr uint8_t AUX_SDA = 19;
constexpr uint8_t AUX_SCL = 18;
constexpr uint32_t AUX_I2C_SPEED = 400000;

typedef struct I2C_Sens_Entry I2C_Sens_Entry;

typedef struct {
    uint8_t line;
    uint8_t addr;
    uint8_t idx;

    void* sens_instance;
    I2C_Sens_Entry* entry_ptr;

    // in case I2C device needs extra information for init / read
    float info1;
    float info2;    
} I2C_Sens_Ctx; // I2C Device Context

typedef bool (*I2CSens_InitFn)(I2C_Sens_Ctx* sens);
typedef bool (*I2CSens_ReadFn)(I2C_Sens_Ctx* sens);

typedef struct I2C_Sens_Entry {
    uint8_t line;
    uint8_t addr;
    I2CSens_InitFn init;
    I2CSens_ReadFn read;
    float info1;
    float info2;
} I2C_Sens_Entry;

// in case some signal needs to be filtered even further - not used currently. refer actuation .h / .cpp for implementation details
extern SoftwareAnalogFilters _act_fb_filt;
extern FilterConfig* act_fb_filter_config;
extern uint8_t _act_fb_idx;

class I2CSensorRegistry {
public:
    static I2CSensorRegistry& instance();
    
    void registerI2C_Sensor(uint8_t line, 
                            uint8_t addr, 
                            I2CSens_InitFn init_fn, 
                            I2CSens_ReadFn read_fn,
                            float info1 = 0.0,
                            float info2 = 0.0);
    
    // Device specific init fn for ith i2c device
    bool init(I2C_Sens_Ctx* sens);
    bool read(I2C_Sens_Ctx* sens);
    
private:
    I2CSensorRegistry();
    
    static constexpr uint8_t MAX_I2C_SENS = 8;
    I2C_Sens_Entry _i2c_sens[MAX_I2C_SENS];
    uint8_t _i2c_sens_count = 0;
    
    int8_t _find_i2c_sens(uint8_t line, uint8_t addr);
};

// Macro for registering specific I2C sensor codes (.h+.ccp)
#define REGISTER_I2C_SENSOR(ADDR, LINE, INIT_FN, READ_FN, ...)              \
    namespace {                                                             \
        struct AutoReg_I2C_##LINE##_##ADDR {                                \
            AutoReg_I2C_##LINE##_##ADDR() {                                 \
                I2CSensorRegistry::instance().registerI2C_Sensor(           \
                    LINE,                                                   \
                    ADDR,                                                   \
                    INIT_FN,                                                \
                    READ_FN,                                                \
                    ##__VA_ARGS__                                           \
                );                                                          \
            }                                                               \
        };                                                                  \
        static AutoReg_I2C_##LINE##_##ADDR _auto_reg_i2c_##LINE##_##ADDR;   \
    }

// __VA_OPT__(,) __VA_ARGS__ 

class I2C_Manager {

public:
    I2C_Manager();
    
    // Public APIs for main cpp
    bool i2c_init(uint8_t dev_idx);
    bool i2c_read(uint8_t dev_idx);

private:
    I2C_Sens_Ctx* _i2csens_contexts = nullptr;

    bool _main_bus_rg = false;
    bool _aux1_bus_rg = false;
    bool _aux2_bus_rg = false;
    
    void _begin_bus_if_needed(uint8_t line);
};