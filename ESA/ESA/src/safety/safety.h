#pragma once
#include "utils.h"

#if defined(ARDUINO_ARCH_ESP32)
  #define PLATFORM_ESP32_ARDUINO
#endif

#if defined(ESP32) || defined(ESP_PLATFORM)
  #define PLATFORM_ESP32
#endif

#if defined(STM32) || defined(STM32F1) || defined(STM32F4) || defined(ARDUINO_ARCH_STM32) || defined(ARDUINO_ARCH_STM32H7) || defined(ARDUINO_ARCH_MBED_PORTENTA) || defined(__ARM_ARCH) || defined(__arm__)
  #define PLATFORM_STM32_VARIANTS

#endif

void wdt_begin(uint32_t wdg_tm = 0);
void wdt_rst();
void wdt_end();

void bod_disable();
void bod_enable();

void deep_sleep_begin();