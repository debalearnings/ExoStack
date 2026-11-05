#include "mux.h"

CD74HC4067* mux1 = NULL;

void ai_mux_init(uint8_t ch_count, uint8_t pin0, uint8_t pin1, uint8_t pin2, uint8_t pin3) {
    if(ch_count == 2) {
        // mux1 = new CD74HC4067(pin0,pin1);    // need different call for 2ch MUX
    }
    else if(ch_count == 3) {
        // mux1 = new CD74HC4067(pin0,pin1,pin2);   // need different call for 3ch MUX
    }
    else if(ch_count == 4) {
        mux1 = new CD74HC4067(pin0,pin1,pin2,pin3);
    }

    delay(2);
}
