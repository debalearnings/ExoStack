#include "I2C_Manager.h"

I2CSensorRegistry& I2CSensorRegistry::instance() {
    static I2CSensorRegistry inst;
    return inst;
}

I2CSensorRegistry::I2CSensorRegistry() {
    memset(_i2c_sens, 0, sizeof(_i2c_sens));
}

void I2CSensorRegistry::registerI2C_Sensor(uint8_t line, uint8_t addr, I2CSens_InitFn init_fn, I2CSens_ReadFn read_fn, float info1, float info2) {
    if (_i2c_sens_count >= MAX_I2C_SENS) return;
    
    _i2c_sens[_i2c_sens_count].line = line;
    _i2c_sens[_i2c_sens_count].addr = addr;

    _i2c_sens[_i2c_sens_count].info1 = info1;
    _i2c_sens[_i2c_sens_count].info2 = info2;

    _i2c_sens[_i2c_sens_count].init = init_fn;
    _i2c_sens[_i2c_sens_count].read = read_fn;

    _i2c_sens_count++;
}

int8_t I2CSensorRegistry::_find_i2c_sens(uint8_t line, uint8_t addr) {
    for (uint8_t i = 0; i < _i2c_sens_count; i++) {
        if (_i2c_sens[i].line == line && _i2c_sens[i].addr == addr) return i;
    }
    return -1;
}

bool I2CSensorRegistry::init(I2C_Sens_Ctx* sens) {
    if (!sens) return false;
    int8_t idx = _find_i2c_sens(sens->line, sens->addr);
    if (idx < 0) return false;
    
    // Cache entry pointer for O(1) read access
    sens->entry_ptr = &_i2c_sens[idx];
    sens->info1 = _i2c_sens[idx].info1;
    sens->info2 = _i2c_sens[idx].info2;
    
    if (_i2c_sens[idx].init)
        return _i2c_sens[idx].init(sens);
    return false;
}

bool I2CSensorRegistry::read(I2C_Sens_Ctx* sens) {
    if (!sens || !sens->entry_ptr) return false;
    
    // Direct pointer dereference - no search!
    if (sens->entry_ptr->read)
        return sens->entry_ptr->read(sens);
    return false;
}

I2C_Manager::I2C_Manager() {}

void I2C_Manager::_begin_bus_if_needed(uint8_t line) {
    if(line == MAIN) {
        if (!_main_bus_rg) {
            Wire.begin(MAIN_SDA, MAIN_SCL); 
            Wire.setClock(MAIN_I2C_SPEED); 
            _main_bus_rg = true;
        }
    }
    else if(line == AUX1) {
        if (!_aux1_bus_rg) {
            Wire1.begin(AUX_SDA, AUX_SCL); 
            Wire1.setClock(AUX_I2C_SPEED); 
            _aux1_bus_rg = true;
        }
    }
}

bool I2C_Manager::i2c_init(uint8_t sens_idx) {
    if(sens_idx < 0 || sens_idx >= NUM_DEVICES) return false;
    
    if (!_i2csens_contexts) {
        _i2csens_contexts = (I2C_Sens_Ctx*)calloc(NUM_DEVICES, sizeof(I2C_Sens_Ctx));
        if (!_i2csens_contexts) return false;
    }

    uint8_t line = deviceList[sens_idx].extra_info1;
    uint8_t addr = deviceList[sens_idx].pin_or_address;

    _begin_bus_if_needed(line);

    _i2csens_contexts[sens_idx] = {line, addr, sens_idx, nullptr, nullptr, 0.0, 0.0};
    return I2CSensorRegistry::instance().init(&_i2csens_contexts[sens_idx]);
}

bool I2C_Manager::i2c_read(uint8_t sens_idx) {
    if (!_i2csens_contexts) return false;

    return I2CSensorRegistry::instance().read(&_i2csens_contexts[sens_idx]);
}