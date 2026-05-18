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

from typing import Dict, List, Optional

from ntcore import DoublePublisher, NetworkTable
from wpimath.geometry import Pose3d, Rotation3d, Transform3d
from wpimath.units import degreesToRadians, meters

from lib_6107.pykit.LoggedMechanismObject2d import LoggedMechanismObject2d
from lib_6107.pykit.logtable import LogTable


class LoggedMechanismRoot2d:
    """Root node for a 2D mechanism tree structure with NetworkTable integration.

    Represents the base (anchor) point of a 2D mechanism visualization system.
    Unlike LoggedMechanismObject2d, root nodes have fixed 2D coordinates that serve
    as the starting point for all child mechanism objects. The root publishes its
    position to NetworkTable for real-time visualization in dashboards like AdvantageScope.

    Roots act as containers for child LoggedMechanismObject2d nodes, forming a tree
    hierarchy that can be recursively converted to 3D poses for 3D visualization.
    Each root maintains DoublePublishers for its X and Y coordinates to enable
    dynamic position updates during operation.

    Coordinate System:
        2D Input: XZ plane (X forward, Z up)
        3D Output: XYZ space (X forward, Y left, Z up) with Y=0 for mechanism plane

    Attributes:
        _name (str): Unique identifier for this root node.
        _x (meters): X coordinate of the root's position in meters.
        _y (meters): Y (or Z in 2D terms) coordinate of the root's position in meters.
        _objects (Dict[str, LoggedMechanismObject2d]): Child mechanism objects keyed by name.
        _table (Optional[NetworkTable]): Reference to the NetworkTable for publishing data.
        _x_publisher (Optional[DoublePublisher]): Publisher for X coordinate updates.
        _y_publisher (Optional[DoublePublisher]): Publisher for Y coordinate updates.
    """

    def __init__(self, name: str, x: meters, y: meters):
        """Initialize a new mechanism root node.

        Creates a new root at the specified 2D coordinates. The root initializes
        empty of children and is not yet connected to a NetworkTable. Call update()
        to establish the NetworkTable connection for publishing coordinates.

        Args:
            name (str): Unique identifier for this root node. Used as the key in
                parent structures and for NetworkTable subtable organization.
            x (meters): Initial X coordinate of the root in meters.
            y (meters): Initial Y coordinate (Z in 2D space) of the root in meters.

        Note:
            Coordinates represent positions in the 2D mechanism plane. When converted
            to 3D, these map to X and Z coordinates with Y set to 0.
        """
        self._name = name
        self._x: meters = x
        self._y: meters = y
        self._objects: Dict[str, LoggedMechanismObject2d] = {}
        self._table: Optional[NetworkTable] = None
        self._x_publisher: DoublePublisher | None = None
        self._y_publisher: DoublePublisher | None = None

    def close(self) -> None:
        """Recursively close this root and all child objects, freeing resources.

        Properly shuts down all NetworkTable publishers and recursively closes all
        child mechanism objects. This should be called when the mechanism is no longer
        needed to ensure clean resource cleanup and prevent memory leaks or lingering
        NetworkTable entries.
        """
        x_pub, self._x_publisher = self._x_publisher, None
        y_pub, self._y_publisher = self._y_publisher, None
        objects, self._objects = self._objects, {}

        if x_pub:
            x_pub.close()

        if y_pub:
            y_pub.close()

        for obj in objects.values():
            obj.close()

    def append(self, obj: LoggedMechanismObject2d) -> LoggedMechanismObject2d:
        """Add a child mechanism object to this root.

        Appends a new mechanism object as a direct child of this root. The child's
        name must be unique among siblings. If this root is already connected to a
        NetworkTable, the child is immediately synchronized with its corresponding
        subtable for automatic telemetry logging.

        Args:
            obj (LoggedMechanismObject2d): The child mechanism object to add.
                Must have a unique name not used by any sibling.

        Returns:
            LoggedMechanismObject2d: The same object that was appended, enabling
                method chaining for fluent object construction patterns.

        Raises:
            ValueError: If obj.get_name() matches an existing child's name, as
                all mechanism object names must be unique within a parent.

        Example:
            root = LoggedMechanismRoot2d("arm", 0, 0)
            ligament = LoggedMechanismLigament2d(...)
            root.append(ligament)  # Returns ligament for chaining
        """
        name = obj.get_name()
        if name in self._objects:
            raise ValueError(f"Mechanism objet names must be unique: {name}")

        self._objects[name] = obj

        if self._table is not None:
            obj.update(self._table.get_subtable(name))

        return obj

    def set_position(self, x: meters, y: meters) -> None:
        """Update the root's 2D position and publish to NetworkTable.

        Changes the coordinates of this root node and immediately publishes the
        new values to NetworkTable via the X and Y publishers. This allows dynamic
        repositioning of the mechanism's origin during operation (e.g., updating
        a mount point position).

        Args:
            x (meters): New X coordinate in meters.
            y (meters): New Y coordinate (Z in 2D terms) in meters.

        Note:
            Changes are immediately flushed to NetworkTable publishers if one is
            connected. The mechanism's 3D representation updates automatically in
            connected dashboards.
        """
        self._x, self._y = x, y
        self.flush()

    def update(self, table: NetworkTable) -> None:
        """Connect this root to a NetworkTable and establish publishers.

        Associates this root with a NetworkTable for telemetry logging and creates
        DoublePublishers for the X and Y coordinates. Any existing publishers are
        properly closed before new ones are created. All child objects are recursively
        updated with their corresponding subtables.

        Args:
            table (NetworkTable): The NetworkTable to connect to. Should typically
                be a subtable specific to this mechanism for organization.

        Note:
            This method should be called once during initialization and will handle
            cleanup of any previous NetworkTable connection. The current position
            is immediately flushed to the new publishers.
        """
        self._table = table

        if self._x_publisher is not None:
            self._x_publisher.close()

        self._x_publisher = table.getDoubleTopic("x").publish()

        if self._y_publisher is not None:
            self._y_publisher.close()

        self._y_publisher = table.getDoubleTopic("y").publish()
        self.flush()

        for obj in self._objects.values():
            obj.update(self._table.get_subtable(obj.get_name()))

    def get_name(self) -> str:
        """Get the unique name of this root node.

        Returns:
            str: The name assigned to this root at construction time.
        """
        return self._name

    def flush(self) -> None:
        """Publish the current coordinates to NetworkTable.

        Sends the current X and Y coordinates to their respective NetworkTable
        publishers. Called automatically after position updates or table connection,
        but can be called manually to force a refresh of values in NetworkTable.

        Note:
            Safe to call even if no NetworkTable is connected; publishers simply
            won't exist and the operation is a no-op.
        """
        if self._x_publisher is not None:
            self._x_publisher.set(self._x)

        if self._y_publisher is not None:
            self._y_publisher.set(self._y)

    def log_output(self, table: LogTable) -> None:
        """Recursively log the root position and all children to a LogTable.

        Writes the root's current X and Y coordinates to the provided LogTable
        subtable, then recursively logs all child mechanism objects. Used for
        AdvantageScope integration during telemetry recording and replay analysis.

        Args:
            table (LogTable): The LogTable to write data to. Child objects will
                each write to their own subtable with their name as the key.

        Note:
            This method is typically called by higher-level mechanism managers
            during the logging phase of each robot periodic cycle.
        """
        table.put("x", self._x)
        table.put("y", self._y)

        for obj in self._objects.values():
            obj.log_output(table.get_subtable(obj.get_name()))

    def generate3d_mechanism(self) -> List[Pose3d]:
        """Convert this 2D mechanism tree into a series of 3D poses for visualization.

        Transforms the 2D mechanism structure (with root at 2D coordinates and child
        objects at angles/lengths) into a depth-first sequence of 3D Pose3d objects.
        Poses are generated using the standard FRC coordinate frame: +X forward,
        +Y left, +Z up. The mechanism plane lies at Y=0.

        The conversion accounts for the coordinate system transformation:
            - 2D: XZ plane (X forward, Z up)
            - 3D: XYZ space (Y left is perpendicular to mechanism plane)

        Each child object's 2D angle is converted to 3D pitch rotation (with negation
        because 2D positive rotation opposes 3D positive pitch).

        Returns:
            List[Pose3d]: All poses generated in depth-first order. Each pose represents
                a pivot point in the mechanism. Poses are in the order children were
                appended to the root, with each child's descendants following immediately.

        Note:
            - The root's own position becomes the initial transform context
            - The first pose of each child is at the root's position with rotation
            - Subsequent poses follow the ligament/object's length in the rotated frame
            - This output is suitable for publishing to Mechanism2d visualizations
        """
        poses: List[Pose3d] = []

        # Coordinate shift: 2D XZ plane to 3D XYZ plane (Y=0 for mechanism plane)
        initial_pose: Pose3d = Pose3d(self._x, 0, self._y, Rotation3d())

        for obj in self._objects.values():
            # Convert 2D angle to 3D rotation
            # Note: +rotation in 2D is -pitch in 3D (coordinate frame inversion)
            new_rotation = Rotation3d(0, degreesToRadians(-obj.get_angle()), 0)

            # Generate the pose for the pivot point
            new_pose = Pose3d(initial_pose.translation(), new_rotation)
            poses.append(new_pose)

            # Recursively process the child's descendants starting from the end
            # of this ligament (transformed along its length in the rotated frame)
            next_pose = new_pose.transformBy(Transform3d(obj.get_object2d_range(), 0, 0, Rotation3d()))
            more_poses: List[Pose3d] = obj.generate3d_mechanism(next_pose)
            poses.extend(more_poses)

        return poses