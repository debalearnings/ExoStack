#include "analogread.h"

#if defined(PLATFORM_ESP32_ARDUINO)

    void set_adc_pin(uint8_t gpio_pin) {
        pinMode(gpio_pin, INPUT);
    }

    uint16_t read_adc_pin(uint8_t gpio_pin) {
        return analogRead(gpio_pin);
    }

    void dma_read() {   // placeholder currently
        // ESP Arduino seems to give an example for DMA, but doesnt seem to work well
    }
    
#elif defined(PLATFORM_ESP32)

    void set_adc_pin(uint8_t gpio_pin) {
        // IDF Code
    }

    uint16_t read_adc_pin(uint8_t gpio_pin) {
        // IDF Code
    }

    void dma_read() {
        // IDF Code
    }

#elif defined(PLATFORM_STM32_VARIANTS)

    void set_adc_pin(uint8_t gpio_pin) {
        // CubeIDE Code
    }

    uint16_t read_adc_pin(uint8_t gpio_pin) {
        // CubeIDE Code
    }

    void dma_read() {
        // CubeIDE Code
    }

#endif