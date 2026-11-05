#pragma once
#include "I2C_Manager.h"
#include "SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h"

bool NAU7802__INIT_(I2C_Sens_Ctx* sens);
bool NAU7802__READ_(I2C_Sens_Ctx* sens);

REGISTER_I2C_SENSOR(0x2A, MAIN, NAU7802__INIT_, NAU7802__READ_, -0.0243, -299.094); // last two - slope, zero offset
REGISTER_I2C_SENSOR(0x2A, AUX1, NAU7802__INIT_, NAU7802__READ_, -0.0242, -299.096); // last two - slope, zero offset