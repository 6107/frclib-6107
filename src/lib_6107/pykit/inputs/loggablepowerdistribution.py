"""
Logged Power Distribution Module for Robot Energy Monitoring

This module provides LoggedPowerDistribution, a singleton wrapper around WPILib's
PowerDistribution class that enables telemetry logging of robot electrical system
state (voltage, current draw, power consumption, energy used, and temperature).

Key Features:
- Centralized Energy Monitoring: Single access point for all power distribution data
- Automatic Telemetry: Captures voltage, current, power, and energy metrics
- Per-Channel Current: Individual current measurement for each PDP/PDH channel
- Singleton Pattern: Only one instance created, accessed via getInstance()
- Robust Error Handling: Gracefully handles FMS compatibility issues during matches
- Support for Multiple Modules: Works with REV PDH and CTR Electronics PDP

Typical Usage:
    # Get singleton instance
    pdp = LoggedPowerDistribution.getInstance()
    
    # Log power data each cycle
    pdp.saveToTable(entry.get_subtable("PowerDistribution"))
    
    # Access live data
    voltage = pdp.distribution.getVoltage()
    total_current = pdp.distribution.getTotalCurrent()

Data Captured:
- System Voltage: Battery voltage (volts)
- Total Current: Sum of all channel currents (amps)
- Total Power: Instantaneous power consumption (watts)
- Total Energy: Cumulative energy consumed (joules)
- Temperature: Power distribution module temperature (°C)
- Per-Channel Current: Individual current for each channel (amps)

Known Issues:
- FMS Compatibility: During FMS-controlled matches, PDP communication may raise
  exceptions. These are safely caught to prevent telemetry logging from crashing
  the robot code (hence the try/except wrapper).
"""

from wpilib import PowerDistribution

from lib_6107.pykit.logtable import LogTable


class LoggedPowerDistribution:
    """
    Singleton wrapper for WPILib PowerDistribution providing integrated telemetry.
    
    LoggedPowerDistribution wraps the WPILib PowerDistribution class to provide:
    - Centralized access to all power distribution measurements
    - Automatic logging of electrical system state each cycle
    - Per-channel current monitoring for circuit-level diagnostics
    - Singleton pattern for convenient global access
    - Robust error handling for FMS compatibility issues
    
    Supported Hardware:
    - REV Robotics Power Distribution Hub (PDH) - Recommended
    - CTR Electronics Power Distribution Panel (PDP) - Legacy support
    
    Data Measurements:
    
    System-Level Metrics:
    - Voltage (volts): Battery voltage supplying the system
    - Total Current (amps): Sum of all output channel currents
    - Total Power (watts): Instantaneous power consumption (V × I)
    - Total Energy (joules): Cumulative energy used in this session
    - Temperature (°C): Temperature inside the power distribution module
    
    Per-Channel Measurement:
    - Channel Currents (amps): Individual current for each of 16-24 channels
    - Channel Current List: Array of per-channel current values
    - Channel Current Total: Sum of all per-channel currents (should match total)
    
    Singleton Pattern:
    getInstance() returns a single shared instance. The first call creates it with
    default settings (module ID=1, type=REV). For custom configuration, construct
    directly before calling getInstance():
    
    ```python
    # Create custom instance with specific settings
    LoggedPowerDistribution(moduleId=0, module_type=PowerDistribution.ModuleType.kCTRE)
    
    # All subsequent calls return that instance
    pdp = LoggedPowerDistribution.getInstance()
    ```
    
    Typical Integration:
    ```python
    # In robotInit()
    self.pdp = LoggedPowerDistribution.getInstance()
    
    # In periodicAfterUser() or via Logger.periodicAfterUser()
    self.pdp.saveToTable(entry.get_subtable("PowerDistribution"))
    ```
    
    FMS Compatibility:
    During FMS-controlled matches, the JNI layer for power distribution hardware may
    raise exceptions during polling. This implementation wraps all hardware reads in
    try/except to gracefully handle these edge cases (see saveToTable() implementation).
    
    Attributes:
        module_id (int): The CAN ID of the power distribution module (typically 1)
        module_type (PowerDistribution.ModuleType): Type of module (kRev or kCTRE)
        distribution (PowerDistribution): WPILib wrapper for the hardware
        instance (LoggedPowerDistribution | None): Class-level singleton instance
    """

    module_id: int
    """CAN ID of the power distribution module. Typically 1 for primary PDP/PDH."""
    
    module_type: PowerDistribution.ModuleType
    """Type of power distribution hardware (kRev=PDH, kCTRE=legacy PDP)."""
    
    distribution: PowerDistribution
    """WPILib PowerDistribution object for hardware communication."""

    instance: LoggedPowerDistribution | None = None
    """Singleton instance. Created on first getInstance() call."""

    def __init__(self,
                 module_id: int = 1,
                 module_type: PowerDistribution.ModuleType = PowerDistribution.ModuleType.kRev) -> None:
        """
        Initialize a LoggedPowerDistribution wrapper.
        
        Creates a new wrapper around a physical power distribution module. Under normal
        usage, this constructor is called implicitly by getInstance(). For custom
        configuration, construct directly before calling getInstance():
        
        ```python
        # Create with CTR Electronics PDP on CAN ID 0
        LoggedPowerDistribution(module_id=0, module_type=PowerDistribution.ModuleType.kCTRE)
        
        # Subsequent calls to getInstance() return this configured instance
        pdp = LoggedPowerDistribution.getInstance()
        ```

        Args:
            module_id (int, optional): CAN network ID of the power distribution module.
                REV PDH typically uses ID 1. CTR PDP can use 0 or 1 depending on configuration.
                Defaults to 1.
                
            module_type (PowerDistribution.ModuleType, optional): Hardware type selector.
                - PowerDistribution.ModuleType.kRev: REV Robotics Power Distribution Hub (PDH)
                - PowerDistribution.ModuleType.kCTRE: CTR Electronics Power Distribution Panel (legacy)
                Defaults to kRev (recommended for 2026+).
                
        Attributes Initialized:
            self.module_id: Stores the CAN ID for reference
            self.module_type: Stores the hardware type
            self.distribution: Creates WPILib PowerDistribution object connected to hardware
            
        Note:
            The WPILib PowerDistribution constructor will fail if the specified module
            is not found on the CAN bus. Check robot CAN wiring and ID configuration if
            initialization fails.
        """
        self.module_id = module_id
        self.module_type = module_type

        # Create WPILib PowerDistribution object for hardware communication
        self.distribution = PowerDistribution(self.module_id, self.module_type)

    @classmethod
    def get_instance(cls) -> LoggedPowerDistribution:
        """
        Get the singleton instance of LoggedPowerDistribution.
        
        Returns a single shared instance throughout the robot's lifetime. On the first
        call, creates and initializes a new instance with default settings (module ID=1,
        type=REV PDH). Subsequent calls return the same instance.
        
        For custom configuration, construct a LoggedPowerDistribution directly before
        calling getInstance():
        
        ```python
        # In robotInit(), before any getInstance() call:
        LoggedPowerDistribution(module_id=0, module_type=PowerDistribution.ModuleType.kCTRE)
        
        # Now getInstance() returns the custom-configured instance
        pdp = LoggedPowerDistribution.getInstance()
        ```
        
        Singleton Pattern Benefits:
        - Single instance avoids multiple hardware connections to same module
        - Convenient global access via class method (no dependency injection needed)
        - Thread-safe (single instantiation due to Python's GIL in robotics context)
        - Consistent configuration across entire robot lifetime

        Returns:
            LoggedPowerDistribution: The singleton instance. On first call, creates with
                default settings: module_id=1, module_type=kRev (REV PDH).
                
        Note:
            This method returns the same object on all calls. Modifying the returned
            object affects all subsequent calls and the entire robot.
            
        Example:
            ```python
            # Get instance (creates if needed)
            pdp = LoggedPowerDistribution.getInstance()
            
            # Safe to call multiple times - returns same instance
            pdp2 = LoggedPowerDistribution.getInstance()
            assert pdp is pdp2  # True
            ```
        """
        if cls.instance is None:
            cls.instance = LoggedPowerDistribution()

        return cls.instance

    def save_to_table(self, table: LogTable) -> None:
        """
        Capture and save all power distribution telemetry to a LogTable.
        
        This method reads all available measurements from the power distribution module
        and writes them to the LogTable for permanent storage and telemetry visualization.
        
        Called Each Cycle:
        Typically invoked once per robot cycle (50 Hz) from Logger.periodicAfterUser():
        
        ```python
        LoggedPowerDistribution.getInstance().saveToTable(
            entry.get_subtable("PowerDistribution")
        )
        ```
        
        Data Captured:
        
        System Voltage and Current:
        - "Voltage" (V): Main battery voltage supplying all circuits
        - "TotalCurrent" (A): Sum of all channel currents
        - "TotalPower" (W): Instantaneous power consumption (V × I)
        - "TotalEnergy" (J): Cumulative joules consumed this session
        - "Temperature" (°C): Internal temperature of the PDP/PDH
        
        Per-Channel Current:
        - "ChannelCurrentsList" (A[]): Current on each channel [ch0, ch1, ..., ch15/23]
        - "ChannelCurrentsTotal" (A): Sum of per-channel currents
        
        Channel Count:
        - REV PDH: 24 channels (0-23)
        - CTR PDP: 16 channels (0-15)
        
        Error Handling:
        Wrapped in try/except to handle FMS compatibility issues. During FMS-controlled
        matches, the power distribution JNI layer may raise exceptions when the PDP/PDH
        communication is interrupted by Field Management System control. These exceptions
        are silently caught to prevent telemetry logging from crashing user code.
        
        Note:
        If an exception occurs, no data is written to the table for that cycle. The
        robot continues running normally. On the next cycle, healthy data will be logged.

        Args:
            table (LogTable): The LogTable subtable to write power distribution data to.
                Typically: entry.get_subtable("PowerDistribution")
                All measurements are written with hierarchical keys:
                - "Voltage", "TotalCurrent", "TotalPower", "TotalEnergy", "Temperature"
                - "ChannelCurrentsList", "ChannelCurrentsTotal"
                
        Side Effects:
            - Reads from physical power distribution hardware via WPILib
            - Populates table with all measurements
            - May skip writing if an exception occurs
            - No exceptions raised (all caught internally)
            
        Typical Data Values:
            - Voltage: 10-13V (battery dependent)
            - TotalCurrent: 0-200A (motor dependent)
            - TotalPower: 0-2600W (max ~200A × 13V)
            - TotalEnergy: Accumulates throughout match
            - Temperature: 20-50°C (depends on load and cooling)
            
        Telemetry Integration:
            Logged data is automatically published to:
            - .wpilog files (USB storage or local replay)
            - NetworkTables (SmartDashboard, Elastic)
            - AdvantageScope (for analysis and visualization)
        """
        try:   # HACK: Exception work around when in match (FMS Active)
            # Capture system-level measurements
            table.put("Voltage", self.distribution.getVoltage())
            table.put("TotalCurrent", self.distribution.getTotalCurrent())
            table.put("TotalPower", self.distribution.getTotalPower())
            table.put("TotalEnergy", self.distribution.getTotalEnergy())
            table.put("Temperature", self.distribution.getTemperature())

            # Capture individual channel currents for circuit diagnostics
            channel_currets = []
            for channel in range(self.distribution.getNumChannels()):
                channel_currets.append(self.distribution.getCurrent(channel))

            # Store both the per-channel list and the sum (for convenient access)
            table.put("ChannelCurrentsList", channel_currets)
            table.put("ChannelCurrentsTotal", sum(channel_currets))

        except Exception as e:
            # Silently ignore exceptions from FMS or hardware communication issues
            # Robot continues operating; data will be logged on next successful cycle
            pass