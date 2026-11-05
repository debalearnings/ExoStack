#include "actuation.h"

bool first_run = true;
// Easy and Modular registration, initiation and actuation logic
ActInfo* actuators = nullptr;

SoftwareAnalogFilters _act_fb_filt;
FilterConfig* act_fb_filter_config = nullptr;
uint8_t _act_fb_idx = 0;

ActuatorRegistry& ActuatorRegistry::instance() {
    static ActuatorRegistry inst;
    return inst;
}

ActuatorRegistry::ActuatorRegistry() {
    memset(_entries, 0, sizeof(_entries));
    memset(_registered, 0, sizeof(_registered));

    act_fb_filter_config = (FilterConfig*)calloc((int)sizeof(_registered), sizeof(FilterConfig));
}


void ActuatorRegistry::registerModule(ActuatorType id,
                                      ActuatorInitFn init_fn,
                                      ActuationFn run_fn) {
    if (id < 0 || id >= ACTUATOR_COUNT) return;

    _entries[id].init = init_fn;
    _entries[id].run = run_fn;
    _registered[id] = true;   // considered registered by default, need to review for I2C and other drivers
}

void ActuatorRegistry::init(ActInfo* sub) {
    if (!sub) return;

    int idx = sub->act_type;
    if (idx < 0 || idx >= ACTUATOR_COUNT) return;

    if (!_registered[idx]) return;

    if (_entries[idx].init) 
        _entries[idx].init(sub);

}

void ActuatorRegistry::actuate(ActInfo* sub) {
    if (!sub) return;

    if(first_run && act_fb_filter_config!= nullptr) {
        _act_fb_filt.Init(act_fb_filter_config, _act_fb_idx, ros_pub_rate_hz);
        first_run = false;
    }

    int idx = sub->act_type;
    if (idx < 0 || idx >= ACTUATOR_COUNT) return;

    if (!_registered[idx]) return;

    if (_entries[idx].run) 
        _entries[idx].run(sub);
}




// Class Actuation - sort of a public API, called by main.cpp
Actuation::Actuation() {}

void Actuation::init_(ActInfo* sub) {
    ActuatorRegistry::instance().init(sub);
}

void Actuation::actuate_(ActInfo* sub) {
    ActuatorRegistry::instance().actuate(sub);
}