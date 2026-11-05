#include "LED_TEST.h"


void LED_TEST__INIT_(ActInfo* sub) {
    if (!sub) return;
    pinMode(sub->out_gpio_i2caddr, OUTPUT);
}

void LED_TEST__ACTUATE_(ActInfo* sub) {
    if (!sub) return;

    float cmd = sub->val;
    int8_t out_gpio = sub->out_gpio_i2caddr;
    
    // digitalWrite(exhaust, HIGH);
    
    if (cmd>0) {
            digitalWrite(out_gpio, HIGH);
            }
    else
    {
            digitalWrite(out_gpio, LOW);
    }    
}
