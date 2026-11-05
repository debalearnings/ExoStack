#include "ACT_FESTO_VEAB_L26.h"

float prev_cmd = 0.0;

void FESTO_VEAB_L26__INIT_(ActInfo* sub) {
    if (!sub) return;

    int8_t exhaust = sub->extra_info1;
    int8_t fbPin = sub->extra_info2;

    if(FEEDBACK_VOLTS_SMOOTHENING_REQD && fbPin > 0)  {
        // USER TO CHANGE ONLY THESE TWO:
        act_fb_filter_config[_act_fb_idx].filter_type = 1;  // moving avg filter type (refer data_bus.h), harcoded for now
        act_fb_filter_config[_act_fb_idx].param1 = 10;  // window size
        
        // DO NOT TOUCH THESE:
        act_fb_filter_config[_act_fb_idx].gpio = fbPin;
        _act_fb_idx++;
    }


    if (exhaust > 0) {
        pinMode(exhaust, OUTPUT);
        digitalWrite(exhaust, LOW); // exhaust closed by default
    }
    if (fbPin > 0) {
        pinMode(fbPin, INPUT);
    }
}

void FESTO_VEAB_L26__ACTUATE_(ActInfo* sub) {
    if (!sub) return;

    float ppr_cmd = sub->val;
    int8_t out_gpio = sub->out_gpio_i2caddr;
    
    int8_t exhaust = sub->extra_info1;
    int8_t fbPin = sub->extra_info2;

    // *** CALIBRATION ***
    float sp_volts = ppr_cmd * (5-0) / (600.0 - 3.0);
    float sp_dac_val = sp_volts * 255 / 3.3;

    // *** ACTUATION ***
    // using ESP32 on-board DAC
    sp_dac_val = constrain(sp_dac_val, 0, 255);
    analogWrite(out_gpio, sp_dac_val);

    // digitalWrite(exhaust, HIGH);
    
    if (fbPin >= 0) {
        float fb_kpa = _act_fb_filt.analog_filter(fbPin) * (144.41) - 114.64;
        if(fb_kpa - ppr_cmd > 15)
            digitalWrite(exhaust, HIGH);
        else
            digitalWrite(exhaust, LOW);
    } 
    else {
        float curr = ppr_cmd;

        if (prev_cmd - curr > 5.0f)
            digitalWrite(exhaust, HIGH);
        else
            digitalWrite(exhaust, LOW);

        prev_cmd = curr;
    }
    
}
