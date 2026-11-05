#pragma once
#include "actuation.h"

void FESTO_VEAB_L26__INIT_(ActInfo* sub);
void FESTO_VEAB_L26__ACTUATE_(ActInfo* sub);

bool FEEDBACK_VOLTS_SMOOTHENING_REQD = true;

REGISTER_ACTUATOR(
            ACT_FESTO_VEAB_L26, // ActuatorType - match actuation.h enum
            FESTO_VEAB_L26__INIT_, // Actuator Initiation - Specific function
            FESTO_VEAB_L26__ACTUATE_ // Actuation Logic - Specific function
            )
