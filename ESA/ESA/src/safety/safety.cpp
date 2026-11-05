#include "safety.h"

#if defined(PLATFORM_ESP32_ARDUINO)

    #include "esp_task_wdt.h"
    #include "esp_system.h"

    #include "soc/soc.h"
    #include "soc/rtc_cntl_reg.h"

    // Watchdog
    void wdt_begin(uint32_t wdg_tm) {
        
        #if ESP_ARDUINO_VERSION_MAJOR < 3
            // Legacy Arduino
            esp_task_wdt_init(wdg_tm, true);
            esp_task_wdt_add(NULL);
        #else
            // Newer Arduino
            esp_task_wdt_config_t config = {
                .timeout_ms = wdg_tm * 1000,
                .idle_core_mask = (1 << CONFIG_FREERTOS_NUMBER_OF_CORES) - 1,
                .trigger_panic = true,
            };
            esp_task_wdt_deinit();
            esp_task_wdt_init(&config);
            esp_task_wdt_add(NULL);
        
        #endif
    }

    void wdt_rst() {
        esp_task_wdt_reset();
    }

    void wdt_end() {
        esp_task_wdt_delete(NULL);
    }

    // Brown out
    void bod_disable() {
        WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    }

    void bod_enable() {
        WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 1);
    }

    // Deep sleep - wake on hardware reset only
    void deep_sleep_begin() {
        esp_sleep_enable_timer_wakeup(UINT64_MAX);
        esp_deep_sleep_start(); 
    }

#elif defined(PLATFORM_ESP32)
    #include "esp_task_wdt.h"
    #include "esp_system.h"
    #include "soc/soc.h"
    #include "soc/rtc_cntl_reg.h"

    void wdt_begin(uint32_t wdg_tm) {
        #if defined(ESP_IDF_VERSION_MAJOR) && (ESP_IDF_VERSION_MAJOR >= 5)
            esp_task_wdt_config_t config;
            memset(&config, 0, sizeof(config));
            config.timeout_ms = (uint32_t)wdg_tm * 1000;
            esp_task_wdt_init(&config);
            esp_task_wdt_add(NULL);
        #else
            esp_task_wdt_init(wdg_tm, true);
            esp_task_wdt_add(NULL);
        #endif
    }

    void wdt_rst() {
        esp_task_wdt_reset();
    }

    void wdt_end() {
        esp_task_wdt_delete(NULL);
    }

    void bod_disable() {
        WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    }

    void bod_enable() {
        WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 1);
    }

    void deep_sleep_begin() {
        #if defined(ESP_DEEP_SLEEP_SUPPORT) || 1
            esp_deep_sleep_start();
        #else
            delay(UINT64_MAX);
        #endif
    }

#elif defined(PLATFORM_STM32_VARIANTS)

    // TBA - Currently only crude deep sleep is programmed. Will be updated

    void wdt_begin(uint32_t wdg_tm) {
        
    }

    void wdt_rst() {

    }

    void wdt_end() {

    }

    // Brown out
    void bod_disable() {

    }

    void bod_enable() {
        
    }

    // Deep sleep - wake on hardware reset only
    void deep_sleep_begin() {
        delay(UINT64_MAX);  // crude way, not recommended once proper code is written
    }

#endif 