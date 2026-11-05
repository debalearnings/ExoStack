#include "AS5600_local.h"

bool AS5600_LOC__INIT_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens) return false;
    
    TwoWire& wire_ = (i2c_sens->line == MAIN) ? Wire : Wire1;
    
    // Allocate NAU7802 instance - one per sensor
    // AS5600* enc(wire_);
    AS5600* enc = new AS5600(&wire_);
    if (!enc) return false;

    // Attempt initialization with retries
    for(int i = 0; i <= _MAX_SENSOR_INIT_RETRIES; i++) {

        enc->begin(4);    // i2c_sens.info1 = dir value
        // enc->setDirection(AS5600_CLOCK_WISE);

        if(enc->isConnected()) {
            enc->setDirection(AS5600_CLOCK_WISE);
            enc->resetCumulativePosition(0);

            delay(100);

            deviceList[i2c_sens->idx].data_per_device = 3;
            sensorIndices+=3; 

            i2c_sens->sens_instance = (void*)enc;

            return true;
        }
    }

    return false;
}

bool AS5600_LOC__READ_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens || !i2c_sens->sens_instance) return false;

    AS5600* enc = (AS5600*)i2c_sens->sens_instance;

    if(enc->isConnected()) {
        enc->readAngle();
        
        msg.intensities.data[sensorIndices] = enc->rawAngle() * AS5600_RAW_TO_RADIANS * _RAD_TO_DEG;
        sensorIndices++;
        msg.intensities.data[sensorIndices] = enc->getAngularSpeed(AS5600_MODE_DEGREES, false);
        sensorIndices++;
        msg.intensities.data[sensorIndices] = enc->getCumulativePosition(false);
        sensorIndices++;

        return true;
    }

    return false;
}