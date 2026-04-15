# frclib-6107

Python helper library focused on the CyberJagzz FRC Team 6107 robot requirements

# Background and Intended Direction

During the initial FRC python effort for the 2026 Rebuilt build-season, several useful
utilities were identified along with common functionality between some subsystems. On
top of this, the pykit module had a few bugs identified and were brought into the Team's
product.

All of this work is under the _**lib_6107**_ subdirectory and now that build season is
over, it sure would be nice to pull this into a loadable module, clean up and document
the interfaces, and get under some sort of unit tests.

If this is successful, the hope is that the source for 2026 and future robots is greatly
reduced.

Another key focus is to speed the periodic code by at least 25%. The current loop is taking
about 23 mS, and we need this under 20. While the new controller for 2027 will probably be
significantly faster, saving time to run new functionality (vision w/ dynamic collision
avoidance) will most likely take this time up.

# Key Interfaces

Below are the main areas (often subdirectories) contained in this project

# Planned Releases

The first 'beta' release will be 2026.0.1 and will primarily be a move of the
current [2026-Rebuilt](https://github.com/6107/2026-Rebuilt) project into an
installable module. Following that _release_, the start of several improvements
based on the prioritized list below. Note that priorities may change without
notice.

|              Status              |      Task       | Description                                                                                                                                                                       |
|:--------------------------------:|:---------------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     <input type="checkbox">      |  lib_2026 move  | 2026.0.1 - Successful move into an installable module. Little or no added functionality.                                                                                          
|     <input type="checkbox">      |   robot base    | Base class for the robot that is responsible for at least the initial logging setup and determining if this is a replay                                                           |
|     <input type="checkbox">      | subsystem base  | Base subsystem class that supports pykit, simulation, and sysId overridable methods                                                                                               |
|     <input type="checkbox">      | pykit unit-test | Get to >70% unit test coverage of pykit logging functionality<br/>Focus on performance measurements. Keep track of results                                                        |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |    CTRE/REV     | Provide customized subsystem support for CTRE and Rev Robotics based subsystems                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |   pykit slots   | Support @DataClass(slots=True) for pykit logging if it can help with performance                                                                                                  |
|     <input type="checkbox">      |   pykit meta    | Support subsystem metadata                                                                                                                                                        |
|     <input type="checkbox">      |  pykit asyncio  | Support asyncio in pykit to improve performance                                                                                                                                   |
|     <input type="checkbox">      | canbus logging  | Support Canbus logging to pykit (option to disable via logged chooser)                                                                                                            |
|     <input type="checkbox">      |     period      | Support an easy way to set the period with the default being the 20 mS standard value                                                                                             |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      | github copilot  | Investigate what github copilot may help us with                                                                                                                                  |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |  unit-test-10%  | Reach at least 10% or better unit-test coverage                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |  vision sim 1   | Support vision simulation (PhotonVision)                                                                                                                                          |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |  vision sim 2   | Support vision simulation (Limelight)                                                                                                                                             |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |  unit-test-30%  | Reach at least 30% or better unit-test coverage. Supports github action/workflow.                                                                                                 |
|     <input type="checkbox">      |  unit-test-50%  | Reach at least 50% or better unit-test coverage.                                                                                                                                  |
|     <input type="checkbox">      |  unit-test-70%  | Reach at least 70% or better unit-test coverage                                                                                                                                   |
|     <input type="checkbox">      |  unit-test-80%  | Reach at least 80% or better unit-test coverage                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|     <input type="checkbox">      |        -        |                                                                                                                                                                                   |
|             **DONE**             |  -------------  | ---------------------------------------------                                                                                                                                     |
| <input type="checkbox" checked>  |   Placeholder   | As items are completed, the will be moved below this lineDo we want to support pitch and roll in our logged gyro outputs<br/>with the version that they first became available in |


# NOTICE
As with many frc projects, the code in this module draws from many other repositories
belonging to different teams. As I begin to extract code and move it into this repo,
I hope to provide credit below. If I miss anyone, my apologies, it is not intentional.

Also, we use:
    - both Rev and CTRE motors
    - pathplanner
    - pykit
    - PhotonVision (and maybe Limelight soon)

So those modules will be downloaded if you install this module as well. Maybe a little
code bloat, but it should not be much of an impact in 2027 where this is being targeted.

## Westwood Robotics - 1757
    TODO

## Team 714 (Eugene)
    TODO