#pragma once
#include "I2C_Manager.h"

// Device library
#include "AS5600.h"

bool AS5600_LOC__INIT_(I2C_Sens_Ctx* sens);
bool AS5600_LOC__READ_(I2C_Sens_Ctx* sens);

REGISTER_I2C_SENSOR(0x36, MAIN, AS5600_LOC__INIT_, AS5600_LOC__READ_, 4);   // last value = dir = 4
REGISTER_I2C_SENSOR(0x36, AUX1, AS5600_LOC__INIT_, AS5600_LOC__READ_, 4);// last value = dir = 4