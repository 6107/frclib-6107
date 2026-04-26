# frclib-6107

Python helper library focused on the CyberJagzz FRC Team 6107 robot requirements

## Table of Contents

 * [Background and Intended Direction](#background-and-intended-direction)
 * [Key Interfaces](#key-interfaces)
 * [Commands](#commands)
   * [Drivetrain](#drivetrain)
   * [Vision](#vision)
   * [Pykit](#pykit)
 * [Subsystems](#subsystems)
   * [Gyro](#gyro)
   * [Pykit](#pykit-1)
   * [RPM](#rpm)
   * [Vision](#vision-1)
 * [Utilities](#util)

# Background and Intended Direction

During the initial FRC python effort for the 2026 Rebuilt build-season, several useful
utilities were identified along with much common functionality between some subsystems. On
top of this, the pykit module had a few bugs identified and were brought into the Team's
product.

All of this work was performed under the _**lib_6107**_ subdirectory of our
[2026 Rebuilt](https://github.com/6107/2026-Rebuilt) project, and now that build season
is over, it sure would be nice to pull this into a loadable module, clean up and document
the interfaces, and get under some sort of unit tests.

If this is successful, the hope is that the main robot-loadable source for 2026 and our 
future robots is greatly reduced.

Another key focus is to speed the periodic code by at least 25%. The current loop is taking
about 23 mS, and we need this under 20. While the new controller for 2027 will probably be
significantly faster, saving time to run new functionality (vision w/ dynamic collision
avoidance) will most likely take this time up.

# Key Interfaces

Below are the main areas (often subdirectories) contained in this project.

# commands

## drivetrain

## vision

# pykit

# subsystems

## gyro

## pykit

## rpm

## vision

# util

# Planned Releases and Improvements

The first 'beta' release will be 2026.0.1 and will primarily be a move of the
current [2026-Rebuilt](https://github.com/6107/2026-Rebuilt) project into an
installable module. Following that _release_, the start of several improvements
based on the prioritized list below. Note that priorities may change without
notice.

|       Improvement       |      Task       | Description                                                                                                                                                  |
|:-----------------------:|:---------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <input type="checkbox"> | drivesubsystem  | A base subsystem for a drivetrain (focus on swerve initially)                                                                                                
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |  build-part-1   | [automation] Support automated release via Makefile                                                                                                          |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |   lint-part-2   | [automation] Support lint via GitHub actions                                                                                                                 |
| <input type="checkbox"> |  bandit-part-2  | [automation] Support bandit via GitHub actions                                                                                                               |
| <input type="checkbox"> |  build-part-2   | [automation] Support automated release via GitHub actions                                                                                                    |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |   performance   | [performance] Review existing code so far and address and areas for increasing code efficiency. Create items for the improvement                             |
| <input type="checkbox"> | fault handling  | [fault handling] Review existing code so far and address and areas for increasing code stability and recovery.C reate items for the improvement              |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> | pykit unit-test | [fault handling] Get to >70% unit test coverage of pykit logging functionality<br/>Focus on performance measurements. Keep track of results                  |
| <input type="checkbox"> |    ut-part-1    | [automation] Support unit-tests via makefile                                                                                                                 |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |    CTRE/REV     | Provide customized/customizable subsystem support for CTRE and Rev Robotics based subsystems                                                                 |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |   pykit slots   | [performance] Support @DataClass(slots=True) for pykit logging if it can help with performance                                                               |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |   pykit meta    | Support subsystem metadata. Auto-save firmware versions, model numbers, vendor info, and other status we can scrap from devices and their APIs.              |
| <input type="checkbox"> |  pykit asyncio  | [performance] Support asyncio in pykit to improve performance                                                                                                |
| <input type="checkbox"> | canbus logging  | [performance] Support Canbus logging to pykit (option to disable via logged chooser)                                                                         |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> | github copilot  | Investigate what github copilot may help us with                                                                                                             |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |    ut-part-2    | [automation] Support unit-tests via GitHub actions                                                                                                           |
| <input type="checkbox"> |  unit-test-10%  | Reach at least 10% or better unit-test coverage                                                                                                              |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |  vision sim 1   | Support vision simulation (PhotonVision)                                                                                                                     |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |     example     | Create an example project that can be used by other to examine how to use this module.<br/>Also may be able to use it in some automated unit-tests.          |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |  vision sim 2   | Support vision simulation (Limelight)                                                                                                                        |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |  unit-test-30%  | Reach at least 30% or better unit-test coverage. Supports github action/workflow.                                                                            |
| <input type="checkbox"> |  unit-test-50%  | Reach at least 50% or better unit-test coverage.                                                                                                             |
| <input type="checkbox"> |  unit-test-70%  | Reach at least 70% or better unit-test coverage                                                                                                              |
| <input type="checkbox"> |  unit-test-80%  | Reach at least 80% or better unit-test coverage                                                                                                              |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |      tools      | Generate a list of possible tools to improve or automate some of the steps we go through                                                                     |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |  log exporter   | [tools] Auto-log export into a database (mongodb?)<br/>Include additional match/circumstance type metadata and have settable via UI.                         |
| <input type="checkbox"> |      otel       | [tools] [performance] OpenTelemetry support investigation                                                                                                    |
| <input type="checkbox"> |     elastic     | [example] In the 'example' robot project.<br/>Include an _elastic_ JSON layout file that shows how some of the module NT4 data can be displayed/manipulated. |
| <input type="checkbox"> |        -        |                                                                                                                                                              |
| <input type="checkbox"> |        -        |                                                                                                                                                              |

**Completed Tasks **

|            Complete             | Release    |     Task      | Description                                                                                                               |
|:-------------------------------:|:-----------|:-------------:|:--------------------------------------------------------------------------------------------------------------------------|
| <input type="checkbox" checked> | 2026.0.0.1 | lib_2026 move | Successful move into an installable module. Little or no added functionality                                              |       
|               ---               | ---------- |               |                                                                                                                           |
| <input type="checkbox" checked> | 2026.0.0.2 |  lint-part-1  | [automation] Support lint via Makefile                                                                                    |                                                                                        
| <input type="checkbox" checked> | 2026.0.0.2 | bandit-part-1 | [automation] Support bandit via Makefile                                                                                  |
| <input type="checkbox" checked> | 2026.0.0.2 |    period     | Support an easy way to set/manipulate the period with the default being the 20 mS standard value                          |
|               ---               | ---------- |               |                                                                                                                           |
| <input type="checkbox" checked> | 2026.0.0.3 |   constants   | Do constants better so initial value are in lib_6107 but easy to override by developers                                   |
| <input type="checkbox" checked> | 2026.0.0.3 |   robot base  | Base class for the robot that is responsible for at least the initial logging setup and determining if this is a replay   |
| <input type="checkbox" checked> | 2026.0.0.3 | simulation base | A base class for simulation (physics.py)                                                                                                
| <input type="checkbox" checked> | 2026.0.0.3 | subsystem base  | Base subsystem class that supports pykit, simulation, and sysId overridable methods                                                                          |

# NOTICE
As with many _FRC_ projects, the code in this module draws from many other repositories
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

- The original work on pykit and of course their robots tha provide good examples of how to use pykit

## Team 714

- Gene Panov's (Team 714) CommandRevSwerve project and so many good videos of how to use robotpy...
- Misc vision videos by other team members