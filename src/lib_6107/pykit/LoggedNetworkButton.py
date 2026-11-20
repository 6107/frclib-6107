# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
"""
Logged Network Button Module for Elastic-Controlled Triggers

This module provides NetworkTableButton, a Commands-v2 integration for creating
operator-controlled triggers backed by a tunable boolean. A toggle in Elastic
(published at ``/Tunables/<key>``) can trigger robot commands.

Usage:
    button = NetworkTableButton("MyButton")
    button.on_true(some_command)   # Execute command when the toggle turns on
    button.on_false(some_command)  # Execute command when the toggle turns off

The button state is automatically logged for telemetry and replay analysis.
"""

from commands2.button import Trigger

from lib_6107.pykit.networktables.loggednetworkboolean import LoggedNetworkBoolean


class NetworkTableButton(Trigger):
    """
    A Commands-v2 Trigger that reads its state from a tunable boolean.

    This class bridges the FRC Commands-v2 framework with tunables so an operator
    can trigger robot actions from Elastic. The button state is a
    LoggedNetworkBoolean, so it is editable in real time and logged each cycle.

    Key Features:
    - Elastic Integration: Appears as a boolean toggle at ``/Tunables/<key>``
    - Command Integration: Works with Commands-v2 on_true(), on_false(), etc.
    - Logging Support: Button state is logged for telemetry and replay analysis
    - Replay Compatible: Button state can be replayed from logs for deterministic testing
    - Default Values: Supports an initial state before the operator touches the toggle

    Usage:
        ```python
        from lib_6107.pykit.LoggedNetworkButton import NetworkTableButton

        # Create a toggle at /Tunables/Intake
        intake_button = NetworkTableButton("Intake", default=False)

        # Bind commands to button state changes
        intake_button.on_true(IntakeCommand())
        intake_button.on_false(StopIntakeCommand())

        # Operators can now control the button from Elastic
        # The button state is automatically logged for replay
        ```

    Design:
    - Stateful: Maintains internal state via LoggedNetworkBoolean
    - Lazy: State is only read when the Trigger is evaluated (efficient)
    - Logged: All button presses/releases are captured in telemetry logs
    - Replay-Safe: Button state can be replayed from logs for testing

    Attributes:
        _log_bool (LoggedNetworkBoolean): Internal wrapper managing the tunable
            and logging. Updated each cycle by the Logger.

    From Commands-v2 (Inherited):
        - on_true(command) - Execute command when the button transitions false → true
        - on_false(command) - Execute command when the button transitions true → false
        - while_true(command) - Execute command while the button is true (repeating)
        - while_false(command) - Execute command while the button is false (repeating)
    """

    def __init__(self, key: str, default: bool | None = False) -> None:
        """
        Initialize a tunable-backed button trigger.

        Creates a new button that operators can control from Elastic. The button's
        state is published as a tunable and automatically logged for telemetry
        capture and replay analysis.

        Args:
            key (str): The tunable name for this button.
                Examples: "Intake", "Shooter/Fire"
                A leading "/" is accepted and removed.

            default (bool, optional): The initial state shown in Elastic before the
                operator changes it. Defaults to False (unpressed).

        Attributes Set:
            _log_bool (LoggedNetworkBoolean): Creates the boolean tunable at
                ``/Tunables/<key>`` with the default value. This object handles:
                - Publishing to Elastic
                - Reading changes made by the operator
                - Logging state changes for telemetry
                - Replay compatibility

        Parent Initialization:
            Calls super().__init__() with a lambda that reads the current state
            from _log_bool.value. This lambda is evaluated by the Trigger base
            class to determine when to fire commands.

        Example:
            ```python
            # Create button for intake subsystem
            intake_button = NetworkTableButton("Intake", default=False)

            # The button is now accessible in:
            # - Elastic (as a boolean toggle at /Tunables/Intake)
            # - Logs (under "NetworkInputs/Intake" telemetry)

            # Operators can toggle the button, and commands will trigger
            intake_button.on_true(IntakeOnCommand())
            intake_button.on_false(IntakeOffCommand())
            ```
        """
        # Create the boolean wrapper that handles tunable syncing and logging
        self._log_bool: LoggedNetworkBoolean = LoggedNetworkBoolean(key, default or False)

        # Initialize the parent Trigger class with a lambda that reads current state
        # This lambda is called by Commands-v2 to determine trigger state
        super().__init__(lambda: self._log_bool.value)
