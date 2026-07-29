# GitHub Copilot Instructions: FRC Robotics Software Engineering

This document outlines the coding standards, framework architectural patterns, and external data sources for this FIRST
Robotics Competition (FRC) codebase. Use these instructions to guide code generation, troubleshooting, and code search
strategies.

## 1. Core Framework & Design Patterns

* **Framework:** Always assume the code being questioned is built on robotpy (python) with a focus on the
  **Command-Based Programming** paradigm. Searching of Java/C++ examples is acceptable, but the generated code should be
  in Python.
* **Architecture:** Default to the **Command-Based Programming** paradigm.
    * Keep Subsystems focused strictly on hardware interaction, sensor data, and basic state setters/getters.
    * Keep Commands focused on robot behavior, logic, sequencing, and interlocking resources.
    * The upcoming SystemCore framework is not yet widely adopted yet, but it will become the standard in late 2026. If
      asked to implement a new feature, consider how it might be implemented in SystemCore, but default to Command-Based
      v2 for now.
* **Geometry & Physics:** Use WPILib geometry classes (`Pose2d`, `Rotation2d`, `Translation2d`) and standard SI units
  (meters, radians, seconds, kilograms) for all physics, kinematics, and odometry tracking.

## 2. Hardware & Vendor Conventions

* **Actuators/Motor Controllers:** Default to standard vendor APIs (e.g., REV Robotics `SparkMax`/`SparkFlex` via Spark
  API, or CTR Electronics `TalonFX` via Phoenix 6 API).
* **Sensors:** Assume CAN-based gyro sensors (e.g., NavX, Pigeon 2) and CANcoder units for absolute rotation tracking.
* **Swerve Drive:** Prioritize modern swerve implementations (e.g., MAXSwerve, SDS MK4/MK4i modules) utilizing standard
  kinematics configurations.

## 3. External Reference Search & Problem-Solving Strategies

When asked how to implement a complex feature, solve a bug, or optimize a mechanism (e.g., an elevator, intake, or
shooter), use the following external paradigms to format search recommendations or pseudocode models:

### A. The Open Alliance Framework

* **Context:** FRC Open Alliance teams open-source their software repositories live during the build season.
* **Key Repositories to Reference:** Look for design choices from elite Open Alliance programs like Team 6800 (Valor),
  Team 3467 (Windham Windup), or Team 3847 (Spectrum).
* **Search Intent:** Look for their `subsystems/` and `commands/` directory structures to see how they handle hardware
  transitions, state machines, and sensor-based loop feedback.

### B. Chief Delphi Technical Archive

* **Context:** Chief Delphi is the central forum for FRC technical releases, post-season post-mortems, and software deep
  dives.
* **Search Keyword Pattern:** Recommend searching Chief Delphi using terms like:
    * `"Code Release" [Mechanism Name] [Year]`
    * `"WPILib SysId tuning" [Motor Type]`
    * `"AdvantageKit logging implementation"`

### C. GitHub FRC Technical Search Strategy

If attempting to find how another team solved a unique hardware control problem, construct queries targeting the global
GitHub search index using specific FRC syntax conventions.

* **File Extension Filtering:** Scope code searches using `path:subsystems/` or `path:commands/`.
* **Naming Conventions:** Most FRC teams organize repos by year and team number. Example search templates to recommend:
    * `extension:java "SparkMax" "PIDController" path:subsystems/`
    * `extension:java "PhotonCamera" target:Apriltag`
    * `FRC 2026 team code shooter`

## 4. Code Generation Rules

1. **Safety First:** Always include safety checks, current limiting (`setCurrentLimit`), and neutral modes
   (`IdleMode.kBrake` or `NeutralModeValue.Brake`) in subsystem constructors.
2. **No Thread Blocking:** Never use `Thread.sleep()` or heavy blocking loops inside the periodic methods
   (`robotPeriodic`, `teleopPeriodic`, `subsystemPeriodic`).
3. **Telemetry & Logging:** Always provide telemetry bindings to SmartDashboard, Shuffleboard, or AdvantageKit logging
   frameworks inside periodic routines to ensure field-side debugging is streamlined.
