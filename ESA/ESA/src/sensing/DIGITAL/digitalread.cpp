#include "digitalread.h"

#if defined(PLATFORM_ESP32_ARDUINO)

    void set_di_pin(uint8_t gpio_pin, DI_TYPES type) {

        if(type == normal) pinMode(gpio_pin, INPUT); // Normal Digital Input pin
        else if (type==pullup) pinMode(gpio_pin, INPUT_PULLUP); // Add pullup if needed
        else if (type=pulldown) pinMode(gpio_pin, INPUT_PULLDOWN); // Add pulldown if needed
        
            
    }

    bool read_di_pin(uint8_t gpio_pin, uint16_t debounce_tm) {
        if(debounce_tm == 0) return digitalRead(gpio_pin);

        bool reading = digitalRead(gpio_pin);
        bool start_reading = reading;
        uint32_t db_start_tm = millis();
        
        while(millis() - db_start_tm <= debounce_tm) {
            bool reading = digitalRead(gpio_pin);
            if(reading != start_reading) {
                start_reading = reading;
                db_start_tm = millis();
            }
        }

        return start_reading;
    }
    
#elif defined(PLATFORM_ESP32)

    void set_di_pin(uint8_t gpio_pin, uint8_t type) {
        // IDF Code
    }

    bool read_di_pin(uint8_t gpio_pin, uint16_t debounce_tm) {
        // IDF Code
    }

#elif defined(PLATFORM_STM32_VARIANTS)

    void set_di_pin(uint8_t gpio_pin, uint8_t type) {
        // CubeIDE Code
    }

    bool read_di_pin(uint8_t gpio_pin, uint16_t debounce_tm) {
        // CubeIDE Code
    }

#endif
