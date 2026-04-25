# Future home of some documentation

For the foreseeable future, this will be constantly updated and reworked.  While
this disclaimer exists, expect things to change.

# Purpose of this library

# Using lib-6107

## Starting a new project


## constants.py

There are three _constants.py_ files in the lib-6107 project, and they are broken down
along the lines of robot specific, subsystem specific, and command specific constants.

All constants are defined under a object class name that has no other information except
for property attributes. In some cases, they may be constants from a vendor's specification
page (max RPMs of a motor) or they may be just a value where some values need to be customized
for your robot by deriving your own constants from the constants here.

For example, assume the RobotConstants class is defined as

```python
from dataclasses import dataclass
from wpimath.units import kilograms, lbsToKilograms, meters, inchesToMeters

@dataclass(slots=True)
class RobotConstants:
    """
    Various constants related to the physical robot. Many of these need to be customized in your
    robot's implementations
    """
    MASS: kilograms = lbsToKilograms(80)

    X_WIDTH: meters = inchesToMeters(24)
    Y_WIDTH: meters = inchesToMeters(24)

    # Controller Ports
    DRIVER_CONTROLLER_PORT = 0
    SHOOTER_CONTROLLER_PORT = 1
    CALIBRATION_CONTROLLER_PORT = 2  # Set to < 0 to disable initialization

    ...
```
Obviously, the weight and dimensions of your robot will be different, but you may be happy
with many of the other values. So define your own sub-class:

```python
from wpimath.units import kilograms, lbsToKilograms, meters, inchesToMeters
from lib_6107.constants import RobotConstants

from dataclasses import dataclass
@dataclass(slots=True)
class MyRobotConstants(RobotConstants):
    
    MASS: kilograms = lbsToKilograms(110)
    X_WIDTH: meters = inchesToMeters(27)
    Y_WIDTH: meters = inchesToMeters(27)
    
    ...

    MY_ADDITIONAL_VALUES: meters = ...
```
This provides you a way to override just the constants you need to as well as to define
additional constants that are unique to just your robot (so all is in one convenient place).

The constants are defined as a dataclass with **slots=True** to allow for lower memory footprint
and faster access.

During _robotInit()_, you will need to register any of your derived constant classes. During
simulation startup, many of these values will be validated against common constants that other
tools may use and errors will be issued if they are different.

## lib_6107/constants.py

The _constants.py_ file in the base lib_6107 subdirectory contains many constants classes related
to the robot itself (physical) as well as various values used by other tools (**pykit**, **PathPlanner**,
...).  Each constants class will include descriptions of each attribute and indicate their use. Note
that some constants are not meant to be overridden and are not customizable. Those classes will
be clearly marked with a proper disclaimer.

## lib_6107/subsystems/constants.py

## lib_6107/commands/constants.py


# PathPlanner

# Vision

# Appendix

Supplementary information

## example subdirectory

This is a small example project that consumes the lib-6107 module and is actually used to
help with unit-testing of the library. The goal is for it to make use of the most common
features with clear indications of what is being used and why.