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

from typing import List,Tuple, Optional

from commands2 import Command, InstantCommand, PrintCommand, RunCommand, Subsystem
from commands2.button import CommandXboxController, Trigger

from phoenix6 import swerve
from wpilib import DriverStation, SmartDashboard, \
    XboxController


from lib_6107.robotcontainer import RobotContainer

from lib_6107.subsystems.vision.visionsubsystem import VisionSubsystem
from lib_6107.util.numerical_chooser import IntegerEditBox

from constants import DeviceID, FRONT_CAMERA_INFO, LEFT_CAMERA_INFO, REAR_CAMERA_INFO, RIGHT_CAMERA_INFO

from util.field.field_2026 import RebuiltField as Field
from generated.tuner_constants import TunerConstants

from subsystems.ctre_pivot import CtreIntakePivot as IntakePivot
from subsystems.rev_flywheel import RevFlywheel as Shooter
from util.alerts import MyRobotAlerts


class MyRobotContainer(RobotContainer):
    """
    This class is where the bulk of the robot should be declared. Since Command-based is a
    "declarative" paradigm, very little robot logic should actually be handled in the :class:`.Robot`
    periodic methods (other than the scheduler calls). Instead, the structure of the robot (including
    subsystems, commands, and button mappings) should be declared here.
    """
    def __init__(self, robot: 'MyRobot') -> None:
        # The robot's subsystems

        ##########################################
        #  Subsystems (fully initialized in base class when it calls into
        #  the subsystem_init() function.  First declare everything that we will create
        #  later in the subsystem_init() function
        #
        self._field: Field = None
        self.robot_drive = None
        self.climber = None
        self.flywheel = None

        # Now let the base class handle most of the rest of the work
        super().__init__(robot)

        ##########################################
        #   ALERTS, overwrite it with ours (which are derived from the base alerts
        #
        self._alerts: MyRobotAlerts = MyRobotAlerts(self)

        ########################################################
        # Configure the button bindings
        for controller, port_id in self._controllers:
            if isinstance(controller, CommandXboxController):
                self.configure_button_bindings_xbox(controller, port_id)

            elif controller is not None:
                print(f"Unsupported controller type {type(controller)}")

        # Configure the additional autos that do not come from pathplanner
        self.configure_additional_autos()

        # Speed limiter useful during initial development. This can be exposed in
        # the elastic UI and be used to control the drivetrain speed. The drivetrain
        # can move quite fast, and it is best to start off at a low percentage (10%)
        # while you verify all is working and you driver has the skills to go faster.
        self._limit_chooser = None
        self.configure_speed_limiter()

        ########################################################
        # Initialize the Smart dashboard for each subsystem
        # Dashboard setup
        for subsystem in self.subsystems:
            if hasattr(subsystem, "dashboard_initialize") and callable(getattr(subsystem,
                                                                               "dashboard_initialize")):
                subsystem.dashboard_initialize()

    @staticmethod
    def create(robot: 'Robot') -> RobotContainer:
        """
        This is passed into the base 'Robot' class's robotInit to be initialized
        near the end of that initialization section.
        """
        return MyRobotContainer(robot)

    def subsystem_init(self) -> Tuple[Subsystem, ...]:
        """
        Create all subsystems for this years robot
        """
        self._field: Field = Field()
        subsystems: List[Subsystem] = []

        ##########################################
        #  Drivetrain
        #
        # self.robot_drive = DriveSubsystem(self, **drive_kwargs)
        self.robot_drive = TunerConstants.create_drivetrain(self)
        subsystems.append(self.robot_drive)

        ##########################################
        #   VISION
        #
        camera_subsystems = self._init_vision_subsystems()
        subsystems.extend(camera_subsystems)

        ##########################################
        #   Climber
        #
        # Right Pivot Motor should be Inverted
        self.climber = None

        ###########################################
        #   SHOOTER/FLYWHEEL
        self.flywheel: Shooter = Shooter(self, DeviceID.SHOOTER_DEVICE_ID, False)

        # Add subsystems that got initialized
        for sub in (self.intake_pivot, self.flywheel):
            if sub is not None and sub.is_connected:
                subsystems.append(sub)

            elif sub is not None:
                print(f"Subsystem {sub} not connected to robot or failed to initialize")

        if self.flywheel is not None:
            self._shooter_rpm_chooser = IntegerEditBox("Shooter RPM",
                                                       initial_value=0,
                                                       minimum_value=0,
                                                       maximum_value=5676)
            SmartDashboard.putData(self._shooter_rpm_chooser.name, self._shooter_rpm_chooser)

        return tuple(subsystems)

    def _init_vision_subsystems(self) -> Tuple[Subsystem, ...]:
        camera_subsystems = []

        for camera_info in (FRONT_CAMERA_INFO, REAR_CAMERA_INFO, RIGHT_CAMERA_INFO, LEFT_CAMERA_INFO):

            camera_subsystem = VisionSubsystem.create(camera_info, self.robot_drive,
                                                      self._field)
            if camera_subsystem is not None:
                camera_subsystems.append(camera_subsystem)
                self._cameras[camera_info["Label"]] = camera_subsystem

        return tuple(camera_subsystems)

    def _configure_driver_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        """
        Use this method to define your button->command mappings. Buttons can be created by
        instantiating a :GenericHID or one of its subclasses (Joystick or XboxController),
        and then passing it to a JoystickButton.

        LS == Left Stick    - Robot direction on field. Fwd, Back, Left, Right (from operators perspective)
        RS == Right Stick   - Robot rotation  <- Counter-Clockwise  -> Clockwise

        LSB == Left Stick Button  - Nothing
        RSB == Right Stick Button - Nothing

        D-Pad == Directional Pad
                - Up        Extend Climber
                - Right     Tweak Climber Down (small increments)       # TODO: Low Priority
                - Down      Retract Climber
                - Left      Tweak Climber Up (small increments)         # TODO: Low Priority

        LB == Left Bumper   Set the default drive to field-centric
        RB == Right Bumper  Set the default drive to robot-centric


        A == A Button (Bottom) - Brake
        B == B Button (Right)  -
        Y == Y Button (Top)    -
        X == X Button (Left)   -

        Start Button (3 lines) -
        Back Button            - Not used by itself
        """
        x_limiter = self.robot_drive.x_drive_limiter
        y_limiter = self.robot_drive.y_drive_limiter
        turn_limiter = self.robot_drive.turn_limiter

        self.robot_drive.setDefaultCommand(
            # Drivetrain will execute this command periodically. The slew rate limiters are
            # applied to both the drive and turn aspects of the command.
            self.robot_drive.apply_request(
                lambda: (
                    self.robot_drive.drive_request.with_velocity_x(
                        x_limiter.calculate(-self._driver_controller.getLeftY() * self.max_speed))
                    .with_velocity_y(y_limiter.calculate(-self._driver_controller.getLeftX() * self.max_speed))
                    .with_rotational_rate(
                        turn_limiter.calculate(-self._driver_controller.getRightX() * self.max_angular_rate))
                )
            )
        )
        # Idle while the robot is disabled. This ensures the configured
        # neutral mode is applied to the drive motors while disabled.
        idle = swerve.requests.Idle()

        Trigger(DriverStation.isDisabled).whileTrue(
            self.robot_drive.apply_request(lambda: idle).ignoringDisable(True)
        )
        # Left Bumper - Reset the default drive to field-centric
        controller.leftBumper().onTrue(InstantCommand(lambda: self.robot_drive.set_field_centric_drive(True)))

        # Right Bumper - Reset the default drive to robot-centric
        controller.rightBumper().onTrue(InstantCommand(lambda: self.robot_drive.set_field_centric_drive(False)))

        # A Button - Brake
        controller.a().whileTrue(self.robot_drive.apply_request(lambda: self.robot_drive.brake_request))


    def _configure_operator_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        if self.flywheel is not None and self.flywheel.is_connected:
            rpm = 5000
            tolerance = 40

            controller.button(XboxController.Axis.kLeftTrigger).onTrue(
                InstantCommand(lambda: self.flywheel.set_velocity_goal(rpm, tolerance))
            ).onFalse(
                InstantCommand(lambda: self.flywheel.stop())
            )

        if self.intake_pivot is not None and self.intake_pivot.is_connected:
            rotate_down = controller.povLeft()
            up_command = InstantCommand(lambda: self.intake_pivot.pivot_up())
            rotate_down.onTrue(up_command)

            rotate_up = controller.povRight()
            down_command = InstantCommand(lambda: self.intake_pivot.pivot_down())
            rotate_up.onTrue(down_command)


    def _configure_calibration_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        """
        Use this method to define your button->command mappings. Buttons can be created by
        instantiating a :GenericHID or one of its subclasses (Joystick or XboxController),
        and then passing it to a JoystickButton.
        """

    def configure_additional_autos(self):
        """
        Add to dashboard "'"Chosen" dialog that allows us to select which 'automation'
        commands to run when we enter the Autonomous phase.
        """
        self._auto_end_chooser.setDefaultOption("Do nothing", self.get_do_nothing(stop=False))

    def get_do_nothing(self, stop: Optional[bool] = True) -> Command:
        """
        Have robot stop

        Makes a good default autonomous default while robot is still under test
        """
        if stop:
            return InstantCommand(lambda: self.robot_drive.stop())

        return PrintCommand("Do-Nothing Command")

    def robotPeriodic(self) -> None:
        """
        This is called from Robot.robotPeriodic() after the Phoenix6 signal updates
        are requested.

        Also remember that the SubSystem 'periodic' calls are from the CommandScheduler
        run() method which is AFTER robotPeriodic returns

        This should update the saved robot state that can then be used later by
        any commands.
        """
        # Some year specific work first
        pass

        # Now the base class
        super().robotPeriodic()
