# ESA: Embedded Sensing and Actuation

Arduino library for ESP32 boards in [ExoStack](../../README.md). A board is declared by a device
list and five set-up calls; it then publishes all its sensor channels as one micro-ROS message,
subscribes to one command topic per actuator, or both.

**Install:** copy this folder to `~/Arduino/libraries/ESA`, and the folders in
`../PREREQUISITE_LIBRARIES_COPY_TO_ARDUINO_LIBRARIES/` to `~/Arduino/libraries/`.
`micro_ros_arduino` (Humble release) is installed separately.

**Examples:** *File → Examples → ESA*, `Publisher/hub_right` (sensing hub) and
`Subscription/actuator_board` (actuation board) match the worked example of the documentation.

Full documentation: see the main [README](../../README.md).
