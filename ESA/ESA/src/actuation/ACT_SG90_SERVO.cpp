#include "ACT_SG90_SERVO.h"

uint16_t min_pulse = 120;
uint16_t max_pulse = 460;

Adafruit_PWMServoDriver* servo = nullptr;

void SG90_SERVO__INIT_(ActInfo* sub) {
    // Assumes default / main I2C connection

    if (!sub) return;

    int8_t servo_freq = sub->extra_info2;

    servo = new Adafruit_PWMServoDriver(sub->out_gpio_i2caddr);

    servo->begin();
    servo->setPWMFreq(servo_freq);

    delay(10);
}


void SG90_SERVO__ACTUATE_(ActInfo* sub) {
    if (!sub) return;

    float pos_cmd = sub->val;
    int8_t servo_ch = sub->extra_info1;

    if(pos_cmd < 0) pos_cmd = 0;
    if(pos_cmd > 180) pos_cmd = 180;
    pos_cmd = (uint8_t)pos_cmd; // SG90 position b/w 0 and 180, and cannot be a float

    int pulseWidth = map(pos_cmd, 0, 180, min_pulse, max_pulse);
    servo->setPWM(servo_ch, 0, pulseWidth);
}