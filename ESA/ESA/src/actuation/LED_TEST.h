#pragma once
#include "actuation.h"

void LED_TEST__INIT_(ActInfo* sub);
void LED_TEST__ACTUATE_(ActInfo* sub);


REGISTER_ACTUATOR(
            LED_TEST, // ActuatorType - match actuation.h enum
            LED_TEST__INIT_, // Actuator Initiation - Specific function
            LED_TEST__ACTUATE_ // Actuation Logic - Specific function
            )
