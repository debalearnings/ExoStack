#pragma once
#include "Arduino.h"

#if defined(ARDUINO_ARCH_ESP32)
  #define PLATFORM_ESP32_ARDUINO
#endif

#if defined(ESP32) || defined(ESP_PLATFORM)
  #define PLATFORM_ESP32
#endif

#if defined(STM32) || defined(STM32F1) || defined(STM32F4) || defined(ARDUINO_ARCH_STM32) || defined(ARDUINO_ARCH_STM32H7) || defined(ARDUINO_ARCH_MBED_PORTENTA) || defined(__ARM_ARCH) || defined(__arm__)
  #define PLATFORM_STM32_VARIANTS

#endif

void set_adc_pin(uint8_t gpio_pin);
uint16_t read_adc_pin(uint8_t gpio_pin);

void dma_read();    // placeholder currently