"""
Logged Mechanism 2D Visualization Module

This module provides LoggedMechanism2d, a visual representation of robot mechanisms
for real-time and replay visualization in NetworkTables dashboards (SmartDashboard,
AdvantageScope). It publishes directly to a NetworkTable (NTSendable was removed in 2027) and integrates with the pykit
logging system.

Key Features:
- Two-dimensional mechanism visualization with hierarchical structure
- Configurable canvas dimensions and background color
- NetworkTables integration via publish(table)
- Log recording support for replay analysis
- 3D Pose generation from 2D mechanism structure
- Root-based organization for complex mechanisms

Typical Usage:
    ```python
    mechanism = LoggedMechanism2d(width=10.0, height=10.0)

    # Create roots (pivot points)
    base = mechanism.get_root("Base", x=5.0, y=5.0)

    # Add mechanism components to root (via LoggedMechanismRoot2d)
    # ...

    # Record to logs for replay
    table = LogTable(timestamp_ns)
    mechanism.log_output(table)

    # Publish to NetworkTables for dashboards
    mechanism.publish(NetworkTableInstance.get_default().get_table("Mechanism"))
    ```

Credit: Jemison High School - Huntsville Alabama
"""

from ntcore import BooleanPublisher, DoubleArrayPublisher, NetworkTable, StringPublisher
from wpimath import Pose3d
from wpimath.units import meters
from wpiutil import Color, Color8Bit

from lib_6107.pykit.LoggedMechanismRoot2d import LoggedMechanismRoot2d
from lib_6107.pykit.logtable import LogTable


class LoggedMechanism2d:
    """
    A 2D mechanism visualization for robot mechanisms with NetworkTables integration.

    LoggedMechanism2d provides a hierarchical representation of robot mechanisms,
    suitable for visualization in real-time dashboards and log replay analysis.
    The mechanism consists of a canvas with configurable dimensions and one or more
    root nodes that serve as pivot points for mechanism components.

    Architecture:
    - Canvas: The drawing surface defined by width and height
    - Roots: Named pivot points that serve as starting points for mechanism structures
    - Components: Attached to roots via LoggedMechanismRoot2d, forming a tree structure

    NetworkTables Integration:
    When published to a dashboard (via SmartDashboard or similar), LoggedMechanism2d
    automatically creates NetworkTables entries for dimensions, background color, and
    all mechanism roots. The dashboard renders these as an interactive 2D visualization.

    Logging Support:
    The mechanism can be recorded to log files via logOutput(), enabling replay
    and post-match analysis of mechanism state over time.

    Attributes:
        _dimensions (List[meters]): [width, height] canvas dimensions in meters.
            Defines the drawable area for the mechanism.
        _color (str): Hexadecimal color string for the canvas background.
            Example: "#1e3a8a" (dark blue).
        _roots (Dict[str, LoggedMechanismRoot2d]): Named roots (pivot points).
            Each root represents an independent starting point for mechanism structure.
        _table (Optional[NetworkTable]): NetworkTables reference when published.
            Created during initSendable(), used to publish dimensions and roots.
        _dimension_publisher (Optional[DoubleArrayPublisher]): Publishes canvas dimensions.
            Deprecated/managed internally; closed during close().
        _color_publisher (Optional[StringPublisher]): Publishes background color.
            Deprecated/managed internally; closed during close().

    Line Limits:
    The frcviz visualization engine enforces a limit of 512 lines per mechanism
    for performance. Keep mechanism complexity within this constraint.

    Thread Safety:
    Not thread-safe. Assume single-threaded use in robot main loop and dashboard
    context. Proper synchronization required for multi-threaded scenarios.

    Example Usage:
        ```python
        from wpiutil import Color, Color8Bit
        from lib_6107.pykit.LoggedMechanism2d import LoggedMechanism2d
        from wpimath.units import meters

        # Create mechanism with 10m x 10m canvas, default dark blue background
        mechanism = LoggedMechanism2d(10.0, 10.0)

        # Get root at coordinates (5, 5)
        base = mechanism.get_root("Base", 5.0, 5.0)

        # (Mechanism components added via base methods)

        # Change background color
        mechanism.set_background_color(Color8Bit(Color.WHITE))

        # Publish to dashboard (explicit; NTSendable/SmartDashboard are gone in 2027)
        mechanism.publish(NetworkTableInstance.get_default().get_table("Robot Mechanism"))

        # Record for replay
        table = LogTable(RobotController.get_monotonic_time())
        mechanism.log_output(table)
        ```
    """

    def __init__(self, width: meters, height: meters, background_color: Color8Bit | None = None):
        """
        Create a new LoggedMechanism2d with the given dimensions and background color.

        The dimensions represent the drawable canvas area. All mechanism components
        are positioned relative to this coordinate system. The background_color
        provides visual context for the mechanism visualization.

        Args:
            width (meters): The width of the mechanism canvas in meters.
                Typically ranges from 5 to 20 meters depending on robot scale.
            height (meters): The height of the mechanism canvas in meters.
                Typically ranges from 5 to 20 meters depending on robot scale.
            background_color (Optional[Color8Bit]): The background color for visualization.
                Defaults to dark blue (Color.DARK_BLUE). Common choices include
                kBlack, kWhite, kGray, kDarkBlue for good contrast.

        Side Effects:
            - Initializes empty roots dictionary
            - Initializes publishers to None (created on demand during initSendable)

        Example:
            ```python
            mech = LoggedMechanism2d(12.0, 8.0)  # 12m x 8m canvas
            mech_white = LoggedMechanism2d(10.0, 10.0,
                                            Color8Bit(Color.WHITE))
            ```
        """

        background_color = background_color or Color8Bit(Color.DARK_BLUE)

        self._dimensions: list[meters] = [width, height]
        self._color: str = background_color.hex_string()
        self._roots: dict[str, LoggedMechanismRoot2d] = {}

        self._table: NetworkTable | None = None
        self._dimension_publisher: DoubleArrayPublisher | None = None
        self._color_publisher: StringPublisher | None = None
        self._type_publisher: StringPublisher | None = None
        self._controllable_publisher: BooleanPublisher | None = None

    def close(self) -> None:
        """
        Clean up resources associated with this mechanism.

        Closes all NetworkTables publishers and mechanism roots. This should be
        called when the mechanism is no longer needed to free resources and prevent
        memory leaks in long-running robot programs.

        Side Effects:
            - Closes dimension publisher if created
            - Closes background color publisher if created
            - Closes all root mechanisms recursively
            - Clears internal references to released resources

        Thread Safety:
            Not thread-safe. Call only from main robot thread after all dashboard
            communication is complete.

        Note:
            After calling close(), do not call other methods on this mechanism.
            Create a new instance if reuse is needed.

        Example:
            ```python
            mechanism.close()
            # mechanism is now unusable
            ```
        """
        dim_pub, self._dimension_publisher = self._dimension_publisher, None
        color_pub, self._color_publisher = self._color_publisher, None
        type_pub, self._type_publisher = self._type_publisher, None
        controllable_pub, self._controllable_publisher = self._controllable_publisher, None
        roots, self._roots = self._roots, {}

        if dim_pub is not None:
            dim_pub.close()

        if color_pub is not None:
            color_pub.close()

        for pub in (type_pub, controllable_pub):
            if pub is not None:
                pub.close()

        for root in roots.values():
            root.close()

    def get_root(self, name: str, x: meters, y: meters) -> LoggedMechanismRoot2d | None:
        """
        Get or create a root (pivot point) in this mechanism with the given name and position.

        Roots serve as starting points for hierarchical mechanism structures. Multiple
        roots can exist in a single mechanism, each with independent coordinate systems.

        Idempotent Behavior:
        If a root with the given name already exists, the provided x and y coordinates
        are ignored and the existing root is returned. This allows safe repeated calls
        with different coordinates without accidentally recreating roots.

        NetworkTables Binding:
        If this mechanism is already published to NetworkTables (i.e., initSendable
        has been called), the new root is automatically bound to its subtable.

        Args:
            name (str): Unique identifier for the root within this mechanism.
                Common names include "Base", "Pivot", "Joint1", "Endpoint".
                Should be descriptive and consistent across multiple calls.
            x (meters): X coordinate of the root pivot point on the canvas.
                Measured from the left edge. Typically 0 to width.
            y (meters): Y coordinate of the root pivot point on the canvas.
                Measured from the top edge. Typically 0 to height.

        Returns:
            LoggedMechanismRoot2d: The newly created root or existing root with the
                given name. Used to add mechanism components (ligaments, etc.).
                Returns None only if creation fails (rare).

        Side Effects:
            - Creates new LoggedMechanismRoot2d if name doesn't exist
            - Adds root to _roots dictionary
            - Binds to NetworkTables if mechanism is already published

        Example:
            ```python
            # Create initial root
            base = mechanism.get_root("Base", 5.0, 5.0)

            # Later: retrieve same root (coordinates ignored)
            base_again = mechanism.get_root("Base", 3.0, 3.0)
            assert base == base_again  # Same object

            # Create second root
            endpoint = mechanism.get_root("Endpoint", 8.0, 5.0)
            ```
        """
        existing = self._roots.get(name)
        if existing is not None:
            return existing

        root = LoggedMechanismRoot2d(name, x, y)
        self._roots[name] = root

        if self._table is not None:
            root.update(self._table.get_sub_table(name))

        return root

    def set_background_color(self, color: Color8Bit) -> None:
        """
        Set or update the mechanism canvas background color.

        Changes the background color for visualization in dashboards. This affects
        the appearance of the mechanism but not its structure or behavior.

        Color Selection:
        Choose colors that provide good contrast with mechanism components:
        - Dark backgrounds: kDarkBlue, kBlack for light-colored components
        - Light backgrounds: kWhite, kGray for dark-colored components
        - Avoid similar colors between background and mechanism elements

        Args:
            color (Color8Bit): The new background color using WPILib Color8Bit
                representation. Examples:
                - Color8Bit(Color.DARK_BLUE)
                - Color8Bit(Color.GRAY)
                - Color8Bit(200, 100, 50)  # Custom RGB

        Side Effects:
            - Updates internal _color hex string representation
            - If mechanism is published, updates NetworkTables (dashboard updates)

        Example:
            ```python
            mechanism.set_background_color(Color8Bit(Color.WHITE))
            mechanism.set_background_color(Color8Bit(100, 150, 200))  # Custom RGB
            ```
        """
        self._color = color.hex_string()

        if self._color_publisher is not None:
            self._color_publisher.set(self._color)

    def publish(self, table: NetworkTable) -> None:
        """Publish the mechanism to a NetworkTable for dashboard visualization.

        Replaces the pre-2027 ``initSendable()``; NTSendable no longer exists, so the mechanism is
        bound to a table explicitly. Dashboards (Elastic, AdvantageScope) read the Mechanism2d layout.

        NetworkTables Structure:
        - ".type" = "Mechanism2d" (dashboard type identifier)
        - ".controllable" = false (mechanism is read-only)
        - "dims" (double array): [width, height]
        - "backgroundColor" (string): hex color code
        - Subtables for each root, recursively for all components

        Existing publishers are closed first, so calling this more than once is safe.

        Args:
            table (NetworkTable): Table that receives the mechanism data.

        Example:
            ```python
            mechanism.publish(NetworkTableInstance.getDefault().getTable("Mechanism"))
            ```
        """
        self._table = table

        for publisher in (
            self._dimension_publisher,
            self._color_publisher,
            self._type_publisher,
            self._controllable_publisher,
        ):
            if publisher is not None:
                publisher.close()

        self._type_publisher = table.get_string_topic(".type").publish()
        self._type_publisher.set("Mechanism2d")
        self._controllable_publisher = table.get_boolean_topic(".controllable").publish()
        self._controllable_publisher.set(False)

        self._dimension_publisher = table.get_double_array_topic("dims").publish()
        self._dimension_publisher.set(self._dimensions)

        self._color_publisher = table.get_string_topic("backgroundColor").publish()
        self._color_publisher.set(self._color)

        for name, root in self._roots.items():
            root.update(table.get_sub_table(name))

    def log_output(self, table: LogTable) -> None:
        """
        Record the current mechanism state to a log table for replay analysis.

        Logs all mechanism data (dimensions, color, root structures) to the provided
        LogTable. This enables deterministic replay and post-match analysis of
        mechanism visualization.

        Logged Entries:
        - ".type": "Mechanism2d" (identifies entry type)
        - ".controllable": false (mechanism is non-interactive in replay)
        - "dims": [width, height]
        - "backgroundColor": hex color string
        - Root subtables: Each root logs its own state recursively

        Integration with pykit Logger:
        This method is typically called by the pykit Logger system during each
        robot periodic cycle. User code should not call this directly.

        Args:
            table (LogTable): The log table to receive mechanism data.
                Should be the current timestamp's snapshot.

        Side Effects:
            - Adds entries to table for this mechanism
            - Calls recursively on all registered roots
            - Creates subtables within table as needed

        Example:
            ```python
            # Automatic via pykit logging
            table = LogTable(RobotController.get_monotonic_time())
            mechanism.log_output(table)
            # Later: table is flushed to disk/NetworkTables
            ```
        """
        table.put(".type", "Mechanism2d")
        table.put(".controllable", False)
        table.put("dims", self._dimensions)
        table.put("backgroundColor", self._color)

        for name, root in self._roots.items():
            root.log_output(table.get_sub_table(name))

    def generate3d_mechanism(self) -> list[Pose3d]:
        """
        Convert the 2D mechanism structure into a series of 3D poses for 3D visualization.

        Generates 3D representation of the mechanism suitable for use in 3D visualization
        tools (e.g., Glass, frcviz). The conversion assumes:
        - Forward direction: +X axis
        - Left direction: +Y axis
        - Up direction: +Z axis
        - Each pivot point is at the origin of its local frame

        Processing Order:
        Poses are returned in depth-first order matching root insertion order.
        The first root inserted is processed first, with all its descendants before
        moving to the next root.

        Coordinate System:
        The 2D canvas (X=horizontal, Y=vertical) is mapped to 3D as:
        - 2D X → 3D X (forward)
        - 2D Y → 3D Y (left, inverted for standard right-handed coordinates)
        - 3D Z (up) = 0 for all mechanism components in this 2D view

        Use Cases:
        - 3D visualization of robot mechanism state
        - Export to external analysis tools
        - Multi-view mechanism analysis (2D dashboard + 3D visualization)

        Returns:
            List[Pose3d]: List of Pose3d objects representing mechanism components,
                one for each structural element in the mechanism tree.
                List is empty if no roots are defined.
                Order is depth-first based on root and component insertion.

        Example:
            ```python
            poses = mechanism.generate3dMechanism()
            for pose in poses:
                print(f"Component at: {pose.translation()}")
                print(f"Rotation: {pose.rotation()}")

            # Use with 3D visualization
            field_obj = Field3d("Field")
            field_obj.get_object("Mechanism").set_poses(poses)
            ```
        """
        poses: list[Pose3d] = []
        for root in self._roots.values():
            poses.extend(root.generate3d_mechanism())

        return poses
