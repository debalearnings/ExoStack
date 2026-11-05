#pragma once
#include "actuation.h"
#include <Adafruit_PWMServoDriver.h>

extern Adafruit_PWMServoDriver* servo;

void SG90_SERVO__INIT_(ActInfo* sub);
void SG90_SERVO__ACTUATE_(ActInfo* sub);

REGISTER_ACTUATOR(
            ACT_SG90_SERVO, // ActuatorType
            SG90_SERVO__INIT_, // Actuator Initiation - Specific function
            SG90_SERVO__ACTUATE_ // Actuation Logic - Specific function
            )
