#pragma once

#include "Arduino.h"
#include <light_CD74HC4067.h>


extern CD74HC4067* mux1;  // single MUX instance

void ai_mux_init(uint8_t ch_count, uint8_t pin0, uint8_t pin1, uint8_t pin2, uint8_t pin3);
