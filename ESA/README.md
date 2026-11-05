# ESA: Embedded Sensing and Actuation

Firmware side of ExoStack: an Arduino library that turns an ESP32 board into a micro-ROS sensing or actuation hub.

| Folder | Content |
|---|---|
| [`ESA/`](ESA) | the Arduino library: `src/`, `examples/` |
| [`PREREQUISITE_LIBRARIES_COPY_TO_ARDUINO_LIBRARIES/`](PREREQUISITE_LIBRARIES_COPY_TO_ARDUINO_LIBRARIES) | the vendor libraries ESA depends on, with their own licenses |

## Requirements

- Arduino IDE 2.x with the **esp32** board package (tested with 2.0.17)
- `micro_ros_arduino`, Humble release (tested with 2.0.7-humble), added through *Sketch → Include Library → Add .ZIP Library*

## Install

From the root of the cloned repository:

```bash
rm -rf ~/Arduino/libraries/ESA          # only if an earlier copy exists
cp -r ESA/ESA ~/Arduino/libraries/ESA
cp -r ESA/PREREQUISITE_LIBRARIES_COPY_TO_ARDUINO_LIBRARIES/* ~/Arduino/libraries/
```

Restart the Arduino IDE, then open *File → Examples → ESA → Publisher → hub_right* and press **Verify**.

> [!IMPORTANT]
> Keep exactly one ESA library in `~/Arduino/libraries`. Remove any older sensor-suite library from earlier releases; two libraries defining the same classes cause duplicate-definition errors.

Back to the [main README](../README.md).
