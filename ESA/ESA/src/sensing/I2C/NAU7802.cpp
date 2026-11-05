#include "NAU7802.h"

bool NAU7802__INIT_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens) return false;
    
    TwoWire& wire_ = (i2c_sens->line == MAIN) ? Wire : Wire1;
    
    // Allocate NAU7802 instance - one per sensor
    NAU7802* load = new NAU7802();
    if (!load) return false;

    // Attempt initialization with retries
    for(int i = 0; i <= _MAX_SENSOR_INIT_RETRIES; i++) {
        if(load->begin(wire_)) {

            load->setGain(NAU7802_GAIN_32);
            load->setSampleRate(NAU7802_SPS_320);

            deviceList[i2c_sens->idx].data_per_device = 1; 
            sensorIndices++;                    
            delay(100);

            i2c_sens->sens_instance = (void*)load;
            return true;
        }

    }
    
    return false;
}

bool NAU7802__READ_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens || !i2c_sens->sens_instance) return false;
    
    NAU7802* load = (NAU7802*)i2c_sens->sens_instance;
    
    if(load->available()) {
        float loadraw = load->getReading();
        float loadnewton = 1 + (loadraw * i2c_sens->info1 + i2c_sens->info2) * 0.00981;
        // float loadnewton = 1 + (loadraw * -0.0243 + -299.094) * 0.00981;

        msg.intensities.data[sensorIndices] = (loadnewton>0) ? loadnewton : 0.0;    // ONLY PULLING FORCE READ, NOT COMPRESSIVE
        sensorIndices++;

        return true;
    }
    return false;
}