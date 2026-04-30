"""
Logged Network Button Module for Dashboard-Controlled Triggers

This module provides NetworkTableButton, a WPILib Command integration for creating
operator-controlled triggers that are synchronized with NetworkTables. This enables
dashboard buttons (via SmartDashboard, Elastic, or custom dashboards) to trigger
robot commands.

Usage:
    button = NetworkTableButton("/SmartDashboard/MyButton")
    button.onTrue(some_command)  # Execute command when button pressed
    button.onFalse(some_command)  # Execute command when button released

The button state is automatically logged for telemetry and replay analysis.
"""

# ...existing header comments...

from typing import Optional

from commands2.button import Trigger

from lib_6107.pykit.networktables.loggednetworkboolean import LoggedNetworkBoolean


class NetworkTableButton(Trigger):
    """
    A WPILib Trigger that reads its state from a NetworkTables boolean.
    
    This class bridges the FRC Commands-v2 framework with NetworkTables to enable
    dashboard operators to trigger robot actions. The button state is maintained as
    a networked variable, allowing real-time control from SmartDashboard, Elastic, or
    custom operator interfaces.
    
    Key Features:
    - NetworkTables Integration: State synchronized across network in real-time
    - Command Integration: Works with Commands-v2 onTrue(), onFalse(), etc.
    - Logging Support: Button state is logged for telemetry and replay analysis
    - Replay Compatible: Button state can be replayed from logs for deterministic testing
    - Default Values: Supports initial state when NetworkTables entry doesn't exist
    
    The button state is exposed to operators via NetworkTables at the specified key.
    Operators can toggle the button by setting the NetworkTables value to true/false
    from their dashboard application.
    
    Usage:
        ```python
        from lib_6107.pykit.LoggedNetworkButton import NetworkTableButton
        
        # Create a button at /SmartDashboard/Intake
        intake_button = NetworkTableButton("/SmartDashboard/Intake", default=False)
        
        # Bind commands to button state changes
        intake_button.onTrue(IntakeCommand())
        intake_button.onFalse(StopIntakeCommand())
        
        # Dashboard operators can now control the button via SmartDashboard
        # The button state is automatically logged for replay
        ```
    
    Design:
    - Stateful: Maintains internal state via LoggedNetworkBoolean
    - Lazy: State is only polled when Trigger is evaluated (efficient)
    - Logged: All button presses/releases are captured in telemetry logs
    - Replay-Safe: Button state can be replayed from logs for testing
    
    Example Dashboard Integration:
        SmartDashboard (Java/Python): Displays as boolean switch
        Elastic Dashboard: Shows as toggle box with state indicator
        Shuffleboard: Customizable widget with boolean binding
    
    Attributes:
        _log_bool (LoggedNetworkBoolean): Internal wrapper managing the NetworkTables
            entry and logging. Automatically synced with the dashboard.
            
    From Commands-v2 (Inherited):
        - onTrue(command) - Execute command when button transitions false → true
        - onFalse(command) - Execute command when button transitions true → false
        - whileTrue(command) - Execute command while button is true (repeating)
        - whileFalse(command) - Execute command while button is false (repeating)
    """

    def __init__(self, key: str, default: Optional[bool] = False) -> None:
        """
        Initialize a NetworkTable-backed button trigger.
        
        Creates a new networked button that operators can control from dashboards.
        The button's state is synchronized via NetworkTables and automatically logged
        for telemetry capture and replay analysis.
        
        Args:
            key (str): The NetworkTables entry key for this button.
                Examples: "/SmartDashboard/Intake", "/SmartDashboard/Shooter/Fire"
                Typically starts with "/SmartDashboard/" for dashboard visibility.
                
            default (bool, optional): The initial state if the NetworkTables entry
                doesn't exist. Once the entry is created (by dashboard or Logger),
                this default is overridden. Defaults to False (unpressed).
        
        Attributes Set:
            _log_bool (LoggedNetworkBoolean): Creates the networked boolean entry
                at the specified key with the default value. This object handles:
                - Publishing to NetworkTables
                - Subscribing to changes from the dashboard
                - Logging state changes for telemetry
                - Replay compatibility
        
        Parent Initialization:
            Calls super().__init__() with a lambda that reads the current state
            from _log_bool.value. This lambda is evaluated by the Trigger base
            class to determine when to fire commands.
        
        Example:
            ```python
            # Create button for intake subsystem
            intake_button = NetworkTableButton("/SmartDashboard/Intake", default=False)
            
            # The button is now accessible in:
            # - SmartDashboard (as a toggle switch)
            # - Elastic (as a boolean widget)
            # - Logs (under "SmartDashboard/Intake" telemetry)
            
            # Dashboard operators can toggle the button, and commands will trigger
            intake_button.onTrue(IntakeOnCommand())
            intake_button.onFalse(IntakeOffCommand())
            ```
        """
        # Create the networked boolean wrapper that handles NT syncing and logging
        self._log_bool = LoggedNetworkBoolean(key, default)
        # Initialize to the provided default value
        self._log_bool.value = default

        # Initialize the parent Trigger class with a lambda that reads current state
        # This lambda is called by Commands-v2 to determine trigger state
        super().__init__(lambda: self._log_bool.value)