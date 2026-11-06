# Device and Subsystem Telemetry Metrics

The lib_6017/pykit subdirectory contains a telemetry framework for collecting and logging data from
devices and subsystems. The framework is designed to be flexible and extensible, allowing developers to
easily add new telemetry sources and sinks. This documents addresses metrics available for most devices
and subsystems.

Not all possible metrics will be listed here, but the most common ones will be.

# RoboRio / WPILib Telemetry

 - comments from the roboRIO web interface.  RobotController.getComments()
 - Serial number from the roboRIO web interface.  RobotController.getSerialNumber()

## Power Distribution & Rail Status
 - Battery voltage (`RobotController.getBatteryVoltage()`)
 - Brownout voltage (`RobotController.getBrownoutVoltage()`)
 - Brownout status (`RobotController.isBrownedOut()`)
 - Input Current/Voltage (`PowerDistribution.getInputCurrent()`, `PowerDistribution.getInputVoltage()`)
 - Rail Voltage Diagnostics (3.3V, 5V, 6V) ('RobotController.getVoltage3V3()', 'RobotController.getVoltage5V()', 'RobotController.getVoltage6V()')
 - Rail Current Diagnostics (3.3V, 5V, 6V) ('RobotController.getCurrent3V3()', 'RobotController.getCurrent5V()', 'RobotController.getCurrent6V()')
 - Rail Faults (3.3V, 5V, 6V) ('RobotController.getFaultCount3V3()', 'RobotController.getFaultCount5V()', 'RobotController.getFaultCount6V()')
 - Rail State (3.3V, 5V, 6V) ('RobotController.getEnabled3V3()', 'RobotController.getEnabled5V()', 'RobotController.getEnabled6V()')

## Onboard Accelerometer
 - Acceleration (`BuiltInAccelerometer.getX()`, `BuiltInAccelerometer.getY()`, `BuiltInAccelerometer.getZ()`)

## CAN Bus / Device Telemetry
Via the CANStatus object returned by `RobotController.getCANStatus()`, the following metrics are available:
 - CAN Bus Utilization ('RobotController.getCANStatus().busUtilization')
 - CAN Bus Off Count ('RobotController.getCANStatus().busOffCount')
 - CAN Bus TX Error Count ('RobotController.getCANStatus().txErrorCount')
 - CAN Bus RX Error Count ('RobotController.getCANStatus().rxErrorCount')
 - CAN Bus TX Overflow Count ('RobotController.getCANStatus().txFullCount')

## CPU, System Time, and Hardware Metadata

 - CPU Temperature: RobotController.getCPUTemp() (In Celsius, essential for monitoring roboRIO thermal throttling).
 - System Time Validity: RobotController.isSystemTimeValid() (True if synced via Network Tables/Driver Station).
 - RSL State: RobotController.getRSLState() (Returns whether the Robot Signal Light is currently illuminated).

# SystemCore / WPILOG Telemetry
  primary_status = wpilib.RobotController.get_can_status(self.primary_bus)
  expansion_status = wpilib.RobotController.get_can_status(self.expansion_bus)

        # Update telemetry streams cleanly
        self.telemetry_stream.pub_double("diagnostics/primary_util", primary_status.bus_utilization)
        self.telemetry_stream.pub_double("diagnostics/expansion_util", expansion_status.bus_utilization)
        self.telemetry_stream.pub_int("diagnostics/loop_timestamp", loop_time_ns)

# Network Tables

    nt_clients_table = table.getSubTable("NTClients")

    # Query current NetworkTables connections
    nt_connections = NetworkTableInstance.getDefault().getConnections()

    # Build set of currently connected remote client IDs
    nt_remote_ids = set()
    for connection in nt_connections:
        # Track disconnections by removing from last_nt_remote_ids if present
        if connection.remote_id in LoggedSystemStats.last_nt_remote_ids:
            LoggedSystemStats.last_nt_remote_ids.remove(connection.remote_id)
        # Add to current set
        nt_remote_ids.add(connection.remote_id)

        # Log metadata for this connected client
        nt_client_table = nt_clients_table.getSubTable(connection.remote_id)
        nt_client_table.put("Connected", True)
        nt_client_table.put("IPAddress", connection.remote_ip)
        nt_client_table.put("RemotePort", connection.remote_port)
        nt_client_table.put("ProtocolVersion", connection.protocol_version)

            # Mark any clients that were previously connected but are now disconnected
            # These are the remote IDs that were in last_nt_remote_ids but not in nt_remote_ids
            for remoteId in LoggedSystemStats.last_nt_remote_ids:
                nt_client_table = nt_clients_table.getSubTable(remoteId)
                nt_client_table.put("Connected", False)

            # Update tracking set for next sample
            LoggedSystemStats.last_nt_remote_ids = nt_remote_ids

# WPILib Misc Metrics
    FPGAVersion", getFPGAVersion()[0])
    FPGARevision", getFPGARevision()[0]
    SerialNumber", getSerialNumber())
    Comments", getComments())
    TeamNumber", getTeamNumber())
    FPGAButton", getFPGAButton()[0])

            table.put("SystemActive", getSystemActive()[0])
            table.put("BrownedOut", getBrownedOut()[0])
            table.put("CommsDisabledCount", getCommsDisableCount()[0])
            table.put("RSLState", getRSLState()[0])
            table.put("SystemTimeValid", getSystemTimeValid()[0])

# CTRE Phoenix 6 Telemetry

# Rev Robotics Telemetry

# Other
