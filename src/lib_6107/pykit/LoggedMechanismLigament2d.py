"""
Logged Mechanism Ligament 2D Module

This module provides LoggedMechanismLigament2d, representing a line segment
(ligament) within a 2D mechanism visualization. Ligaments form the edges of
a mechanism structure, connecting pivot points and representing rigid links,
flexible members, or constraints.

A ligament has:
- Position: Determined by its parent joint
- Length: Distance from parent to end point
- Angle: Rotation from parent coordinate frame
- Color: Visual appearance in dashboard
- Line weight: Thickness of the rendered line

Ligaments support real-time visualization in dashboards (SmartDashboard,
AdvantageScope) with NetworkTables two-way binding for interactive updates.

Typical Usage:
    ```python
    root = mechanism.getRoot("Base", 5.0, 5.0)
    ligament = root.appendLigament2d("Arm", length=3.0, angle=45.0)
    ligament.setColor(Color8Bit(Color.kRed))
    ligament.setLineWeight(5.0)
    ```

Credit: Jemison High School - Huntsville Alabama
"""

# ...existing header comments...

from typing import Optional
from ntcore import DoubleEntry, NetworkTable, StringEntry, StringPublisher
from wpilib import Color8Bit
from wpimath.geometry import Rotation2d
from wpimath.units import degrees, meters


from lib_6107.pykit.LoggedMechanismObject2d import LoggedMechanismObject2d
from lib_6107.pykit.logtable import LogTable


class LoggedMechanismLigament2d(LoggedMechanismObject2d):
    """
    A line segment component representing a rigid or flexible member in a 2D mechanism.
    
    LoggedMechanismLigament2d represents a visual line segment (ligament) in a mechanism,
    typically emanating from a root joint or parent ligament endpoint. Ligaments are the
    primary structural elements of mechanism visualizations and typically represent:
    - Rigid links (arms, shafts)
    - Flexible members (belts, chains)
    - Constraints or guides
    
    Coordinate System:
    A ligament extends from its parent position at the specified angle and length.
    The parent is typically a LoggedMechanismRoot2d or another LoggedMechanismLigament2d
    endpoint. The angle is measured in the parent's coordinate frame.
    
    Angle Convention:
    - 0° points to the right (+X direction)
    - 90° points up (+Y direction)
    - 180° points left (-X direction)
    - 270° points down (-Y direction)
    
    NetworkTables Integration:
    When published to a dashboard, creates NetworkTables entries for:
    - "angle": Current angle in degrees (bidirectional)
    - "length": Current length in meters (bidirectional)
    - "color": Hex color string (bidirectional)
    - "weight": Line weight in pixels (bidirectional)
    - ".type": "line" (read-only, identifies component type)
    
    Dashboard updates are bidirectional: changes made in the dashboard (e.g., via
    widgets) are reflected in the ligament state, and programmatic changes are
    immediately sent to the dashboard.
    
    Logging:
    Ligament state (angle, length, color, weight) is recorded to logs for replay
    and post-match analysis. This allows deterministic visualization reconstruction
    during log playback.
    
    Attributes:
        _angle (degrees): Current rotation in degrees from parent frame
        _length (meters): Distance from parent position to ligament endpoint
        _color (str): Hexadecimal color code (e.g., "#eb8934")
        _weight (float): Line thickness in pixels for visualization (default 10)
        _angle_entry (DoubleEntry): NT bidirectional angle binding
        _length_entry (DoubleEntry): NT bidirectional length binding
        _color_entry (StringEntry): NT bidirectional color binding
        _weight_entry (DoubleEntry): NT bidirectional weight binding
        _type_pub (StringPublisher): NT publisher for ".type" identifier
    
    Example:
        ```python
        from wpilib import Color8Bit, Color
        from wpimath.units import meters, degrees
        
        # Create mechanism and root
        mechanism = LoggedMechanism2d(10.0, 10.0)
        root = mechanism.getRoot("Base", 5.0, 5.0)
        
        # Create a ligament (45 degrees, 3 meters long, default color)
        arm = root.appendLigament2d("Arm", 3.0, 45.0)
        
        # Customize appearance
        arm.setColor(Color8Bit(Color.kRed))
        arm.setLineWeight(5.0)
        
        # Update during robot operation
        arm.setAngle(Rotation2d.fromDegrees(60.0))
        
        # Query current state
        current_angle = arm.getAngle()
        ```
    """

    def __init__(self, name: str,  # pylint: disable=too-many-positional-arguments
                 length: meters, angle: degrees,
                 linewidth: Optional[float] = 10,
                 color: Optional[Color8Bit] = None):
        """
        Create a new ligament with the specified properties.
        
        A ligament is a line segment emanating from its parent (root or another ligament)
        at the given angle and extending for the specified length. The ligament can be
        customized with color and line weight.

        Args:
            name (str): The unique identifier for this ligament within its parent.
                Used in NetworkTables paths and logging. Should be descriptive
                (e.g., "Arm", "Joint1Link", "Shaft"). No leading "/" needed.
            length (meters): The distance from parent to ligament endpoint in meters.
                Positive values only. Typically 0.1 to 5.0 meters depending on scale.
            angle (degrees): The angle of the ligament from the parent frame in degrees.
                0° = right, 90° = up, 180° = left, 270° = down.
                Can be any value; multiples of 360 are equivalent.
            linewidth (Optional[float]): The thickness of the rendered line in pixels.
                Defaults to 10. Typical range 1-20 pixels. Affects visual prominence
                but not mechanism behavior.
            color (Optional[Color8Bit]): The RGB color for the ligament visualization.
                Defaults to orange (235, 137, 52) if not specified. Use Color8Bit
                with predefined colors (Color.kRed, Color.kBlue) or custom RGB values.
                
        Raises:
            ValueError: Potentially raised by parent class if name is invalid.
            
        Side Effects:
            - Calls parent LoggedMechanismObject2d.__init__(name)
            - Initializes all NetworkTables entry references to None (created on demand)
            - Sets internal state for angle, length, color, and line weight
            - No NetworkTables publishing until updateEntries() is called
            
        Example:
            ```python
            ligament1 = LoggedMechanismLigament2d(
                "Arm", 
                length=3.0, 
                angle=45.0
            )
            
            ligament2 = LoggedMechanismLigament2d(
                "Link", 
                length=2.5, 
                angle=90.0,
                linewidth=8,
                color=Color8Bit(Color.kGreen)
            )
            ```
        """
        # ...existing code...

    def close(self) -> None:
        """
        Clean up all NetworkTables resources and publishers.
        
        Closes all NT entries and publishers, releasing resources. Should be called
        when the ligament is no longer needed or when the mechanism is being shut down.
        This is typically called automatically by the parent mechanism's close() method.
        
        Side Effects:
            - Closes parent resources via super().close()
            - Closes type publisher if created
            - Closes angle, color, length, and weight NT entries if created
            - Sets all entry references to None
            - Prevents further NetworkTables communication
            
        Note:
            After calling close(), do not call other methods on this ligament.
            Create a new instance if reuse is needed.
            
        Thread Safety:
            Not thread-safe. Call only from main robot thread.
            
        Example:
            ```python
            ligament.close()
            # ligament is now unusable
            ```
        """
        # ...existing code...

    def set_angle(self, angle: degrees | Rotation2d) -> None:
        """
        Set the angle of this ligament from its parent frame.
        
        Updates the ligament rotation immediately in local state and syncs to
        NetworkTables if connected to a dashboard. Changes are visible in real-time
        during operation and recorded to logs for replay.
        
        Angle Convention:
        - 0° points to the right (+X in parent frame)
        - 90° points up (+Y in parent frame)
        - 180° points left (-X in parent frame)
        - 270° points down (-Y in parent frame)
        Angles wrap at 360° (e.g., 450° = 90°).

        Args:
            angle (degrees | Rotation2d): The new angle. Can be specified as:
                - A float/int in degrees (e.g., 45.0)
                - A Rotation2d object (automatically converts to degrees)
                Both positive and negative angles are supported.
                
        Side Effects:
            - Updates self._angle
            - If NetworkTables entry exists, publishes new angle to dashboard
            - Dashboard visualization updates immediately
            
        Example:
            ```python
            ligament.setAngle(45.0)  # Direct angle
            ligament.setAngle(Rotation2d.fromDegrees(90.0))  # From Rotation2d
            ligament.setAngle(-30.0)  # Negative angle (330°)
            ```
        """
        # ...existing code...

    def get_angle(self) -> degrees:
        """
        Get the current angle of this ligament from its parent frame.
        
        Returns the angle in degrees. If NetworkTables is connected and the angle
        has been modified on the dashboard, this reflects the updated value.

        Returns:
            degrees: The current angle in degrees (0-360 range, but not clamped).
                Example: 45.0, 90.0, 180.0, etc.
                
        Side Effects:
            - If NetworkTables entry exists, synchronizes state from dashboard
            - Updates self._angle if dashboard modification is detected
            
        Example:
            ```python
            current_angle = ligament.getAngle()
            print(f"Ligament angle: {current_angle}°")
            ```
        """
        # ...existing code...

    def set_length(self, length: meters) -> None:
        """
        Set the length of this ligament from its parent position.
        
        Updates the distance from the parent joint to the ligament endpoint.
        Changes are immediately reflected in the dashboard visualization and
        recorded to logs for deterministic replay.

        Args:
            length (meters): The new length in meters. Should be positive.
                Typical range 0.1 to 5.0 meters depending on mechanism scale.
                No explicit validation; cosmetic effects if zero or negative.
                
        Side Effects:
            - Updates self._length
            - If NetworkTables entry exists, publishes new length to dashboard
            - Dashboard visualization updates in real-time
            
        Example:
            ```python
            ligament.setLength(3.5)  # Extend to 3.5 meters
            ```
        """
        # ...existing code...

    def get_length(self) -> meters:
        """
        Get the current length of this ligament.
        
        Returns the distance from the parent position to the ligament endpoint
        in meters. If NetworkTables is connected and the length has been modified
        on the dashboard, this reflects the updated value.

        Returns:
            meters: The current length in meters (e.g., 3.5, 2.0, etc.).
                
        Side Effects:
            - If NetworkTables entry exists, synchronizes state from dashboard
            - Updates self._length if dashboard modification is detected
            
        Example:
            ```python
            current_length = ligament.getLength()
            print(f"Ligament extends {current_length} meters")
            ```
        """
        # ...existing code...

    def set_color(self, color: Color8Bit) -> None:
        """
        Set the color of this ligament for visualization.
        
        Changes the display color in dashboards immediately. The color is stored
        as a hexadecimal string and synchronized with NetworkTables.

        Args:
            color (Color8Bit): The new color using WPILib Color8Bit.
                Examples:
                - Color8Bit(Color.kRed)
                - Color8Bit(255, 128, 0)  # Custom RGB
                - Color8Bit(0xFF0000)  # Direct hex
                
        Side Effects:
            - Updates self._color as hex string
            - If NetworkTables entry exists, publishes new color to dashboard
            - Dashboard visualization updates immediately
            
        Example:
            ```python
            ligament.setColor(Color8Bit(Color.kRed))
            ligament.setColor(Color8Bit(100, 200, 50))
            ```
        """
        # ...existing code...

    def get_color(self) -> Color8Bit:
        """
        Get the current color of this ligament.
        
        Returns the color as a Color8Bit object. If NetworkTables is connected
        and the color has been modified on the dashboard, this reflects the
        updated value.

        Returns:
            Color8Bit: The current color of the ligament. Can be inspected for
                RGB components or converted to other formats.
                
        Side Effects:
            - If NetworkTables entry exists, synchronizes state from dashboard
            - Updates self._color if dashboard modification is detected
            
        Example:
            ```python
            current_color = ligament.getColor()
            print(f"Ligament color: {current_color.hexString()}")
            ```
        """
        # ...existing code...

    def set_line_weight(self, weight: float) -> None:
        """
        Set the line weight (thickness) of this ligament.
        
        Adjusts the pixel thickness of the rendered line. Thicker lines are more
        visually prominent; thinner lines create delicate visualizations. Changes
        are visible immediately in connected dashboards.

        Args:
            weight (float): The line thickness in pixels. Typical range 1-20.
                Common values: 1 (thin), 5 (medium), 10 (default), 20 (thick).
                Larger values may reduce performance if many ligaments are rendered.
                
        Side Effects:
            - Updates self._weight
            - If NetworkTables entry exists, publishes new weight to dashboard
            - Dashboard visualization updates in real-time
            
        Example:
            ```python
            ligament.setLineWeight(5.0)   # Thin line
            ligament.setLineWeight(15.0)  # Thick line
            ```
        """
        # ...existing code...

    def get_line_weight(self) -> float:
        """
        Get the current line weight (thickness) of this ligament.
        
        Returns the pixel thickness of the rendered line. If NetworkTables is
        connected and the weight has been modified on the dashboard, this reflects
        the updated value.

        Returns:
            float: The current line weight in pixels (e.g., 10.0, 5.0, etc.).
                
        Side Effects:
            - If NetworkTables entry exists, synchronizes state from dashboard
            - Updates self._weight if dashboard modification is detected
            
        Example:
            ```python
            current_weight = ligament.getLineWeight()
            print(f"Line thickness: {current_weight} pixels")
            ```
        """
        # ...existing code...

    def update_entries(self, table: NetworkTable) -> None:
        """
        Initialize or update NetworkTables entries for this ligament.
        
        Creates bidirectional (get+set) NetworkTables entries for angle, length, color,
        and weight. After this call, changes made in the dashboard are reflected in
        the ligament state and vice versa. Typically called automatically when the
        mechanism is published to a dashboard.
        
        Existing entries are closed before creating new ones to prevent resource leaks
        if updateEntries is called multiple times.
        
        Created NT Entries:
        - ".type" (StringPublisher): "line" (identifies ligament type)
        - "angle" (DoubleEntry): Current angle in degrees
        - "length" (DoubleEntry): Current length in meters
        - "color" (StringEntry): Hex color string
        - "weight" (DoubleEntry): Line weight in pixels

        Args:
            table (NetworkTable): The NetworkTable subtable for this ligament.
                Typically provided by the parent mechanism or root.
                
        Side Effects:
            - Closes any existing publishers/entries
            - Creates new NT entries in the provided table
            - Ligament becomes visible and controllable in dashboard
            - All subsequent changes sync to the dashboard automatically
            
        Note:
            This method is called automatically by the mechanism framework and
            should not be called directly by user code.
            
        Example:
            ```python
            # Automatic (called by framework)
            nt_table = nt_instance.getTable("/LiveWindow/Mechanism")
            ligament.updateEntries(nt_table.getSubTable("Arm"))
            ```
        """
        # ...existing code...

    def log_output(self, table: LogTable) -> None:
        """
        Record the current ligament state to a log table for replay.
        
        Logs all ligament properties (type, angle, length, color, weight) to the
        provided LogTable snapshot. This enables deterministic recreation of the
        mechanism visualization during log replay. Also calls parent logOutput()
        to record inherited properties.
        
        Logged Entries:
        - ".type": "line" (identifies as ligament)
        - "angle": Current angle in degrees
        - "length": Current length in meters
        - "color": Hex color string
        - "weight": Line weight in pixels
        - Plus any entries from parent LoggedMechanismObject2d

        Args:
            table (LogTable): The log table snapshot to receive ligament data.
                Typically the root mechanism table or a subtable thereof.
                
        Side Effects:
            - Adds entries to table for this ligament
            - Calls parent.logOutput(table) for inherited entries
            - Table is later flushed to disk/NetworkTables by Logger
            
        Example:
            ```python
            # Automatic via pykit logging
            table = LogTable(fpga_time_us)
            mechanism.logOutput(table)
            # table entries include ligament data
            ```
        """
        # ...existing code...

    def get_object2d_range(self) -> meters:
        """
        Get the range (extent) of this ligament for layout calculations.
        
        Returns the length of the ligament, which defines how far this component
        extends from its parent. Used by the mechanism visualization engine to
        calculate bounding boxes and layout geometry.

        Returns:
            meters: The length of the ligament in meters.
                Same as getLength().
                
        Example:
            ```python
            range_meters = ligament.getObject2dRange()
            print(f"Component extends {range_meters} from parent")
            ```
        """
        # ...existing code...