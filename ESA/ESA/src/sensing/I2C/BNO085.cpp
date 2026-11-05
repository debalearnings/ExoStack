#include "BNO085.h"

bool _init_bno085_sensor(BNO080* imu, uint8_t no_of_data, uint8_t dev_idx) {
    if (!imu) return false;
    
    switch (no_of_data) {        
        case 6: // add Gyro
            imu->enableRotationVector(6); // 166Hz data, higher rate not reqd and increases battery consumption
            // imu->enableAccelerometer(6); 
            imu->enableGyroIntegratedRotationVector(6); 
            deviceList[dev_idx].data_per_device = 6;
            break;
        case 9: // add Accl.
            imu->enableGyroIntegratedRotationVector(6);            
            imu->enableAccelerometer(6);
            deviceList[dev_idx].data_per_device = 9;
            break;
        case 0:
        case 3: 
        default: 
            imu->enableRotationVector(6);
            deviceList[dev_idx].data_per_device = 3;
            break;
    }
    sensorIndices += deviceList[dev_idx].data_per_device;
    delay(100);
    return true;    
}

bool _read_bno085_sensor(BNO080* imu, uint8_t dev_idx) {
    if (!imu || !imu->dataAvailable()) return false;

    // RPY
    msg.intensities.data[sensorIndices] = (imu->getRoll()) * _RPY_CONV; sensorIndices++;
    msg.intensities.data[sensorIndices] = (imu->getPitch()) * _RPY_CONV; sensorIndices++;
    msg.intensities.data[sensorIndices] = (imu->getYaw()) * _RPY_CONV; sensorIndices++;

    uint8_t data_count = deviceList[dev_idx].data_per_device;
    
    if(data_count >= 6) {
        msg.intensities.data[sensorIndices] = imu->getFastGyroX(); sensorIndices++;
        msg.intensities.data[sensorIndices] = imu->getFastGyroY(); sensorIndices++;
        msg.intensities.data[sensorIndices] = imu->getFastGyroZ(); sensorIndices++;                        
    }
    if(data_count >= 9) {
        msg.intensities.data[sensorIndices] = imu->getAccelX(); sensorIndices++;
        msg.intensities.data[sensorIndices] = imu->getAccelY(); sensorIndices++;
        msg.intensities.data[sensorIndices] = imu->getAccelZ(); sensorIndices++;
    }
    
    return true;
}

bool BNO085__INIT_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens) return false;
    
    TwoWire& wire_ = (i2c_sens->line == MAIN) ? Wire : Wire1;
    
    // Allocate BNO080 instance - one per sensor
    BNO080* imu = new BNO080();
    if (!imu) return false;

    // Attempt initialization with retries
    for(int i = 0; i <= _MAX_SENSOR_INIT_RETRIES; i++) {
        if (imu->begin(i2c_sens->addr, wire_)) {
            _init_bno085_sensor(imu, (uint8_t)deviceList[i2c_sens->idx].dev_misc_data, i2c_sens->idx);
            i2c_sens->sens_instance = (void*)imu;
            return true;
        }
        delay(5);
    }
    
    return false;
}

bool BNO085__READ_(I2C_Sens_Ctx* i2c_sens) {
    if (!i2c_sens || !i2c_sens->sens_instance) return false;
    
    BNO080* imu = (BNO080*)i2c_sens->sens_instance;
    return _read_bno085_sensor(imu, i2c_sens->idx);
}