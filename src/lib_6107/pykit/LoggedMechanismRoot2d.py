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
    """A root node for a 2D mechanism that can be logged and visualized.

    This class represents the root of a mechanism tree structure, providing
    a fixed coordinate position and managing child mechanism objects. It
    handles network table publishing and 3D pose generation for the entire
    mechanism hierarchy.

    Attributes:
        _name: The unique name of this root mechanism.
        _x: The x-coordinate position of the root in meters.
        _y: The y-coordinate position of the root in meters.
        _objects: Dictionary of child mechanism objects.
        _table: The NetworkTable associated with this root.
        _x_publisher: Publisher for x-coordinate values.
        _y_publisher: Publisher for y-coordinate values.
    """

    def __init__(self, name: str, x: meters, y: meters) -> None:
        """Initialize a new mechanism root.

        Args:
            name: The unique name for this root mechanism.
            x: The x-coordinate position of the root in meters.
            y: The y-coordinate position of the root in meters.
        """
        self._name = name
        self._x: meters = x
        self._y: meters = y
        self._objects: Dict[str, LoggedMechanismObject2d] = {}
        self._table: Optional[NetworkTable] = None
        self._x_publisher: DoublePublisher | None = None
        self._y_publisher: DoublePublisher | None = None

    def close(self) -> None:
        """Close this root and all its child objects.

        This method properly cleans up resources by closing publishers
        and all child objects, then clearing internal collections.
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
        """Append a mechanism object as a child of this root.

        Args:
            obj: The mechanism object to add as a child.

        Returns:
            The object that was added (useful for method chaining).

        Raises:
            ValueError: If an object with the same name already exists.
                Object names must be unique among siblings.
        """
        name = obj.get_name()
        if name in self._objects:
            raise ValueError(f"Mechanism object names must be unique: {name}")

        self._objects[name] = obj

        if self._table is not None:
            # Note: Using getSubTable instead of get_subtable based on ntcore API
            obj.update(self._table.getSubTable(name))

        return obj

    def set_position(self, x: meters, y: meters) -> None:
        """Set the root's position coordinates.

        Updates both x and y coordinates and immediately publishes
        the new values to the network table.

        Args:
            x: The new x-coordinate in meters.
            y: The new y-coordinate in meters.
        """
        self._x, self._y = x, y
        self.flush()

    def update(self, table: NetworkTable) -> None:
        """Update this root with the given network table.

        Sets up publishers for x and y coordinates and updates all
        child objects with their respective subtables.

        Args:
            table: The NetworkTable to use for publishing values.
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
            # Note: Using getSubTable instead of get_subtable based on ntcore API
            obj.update(self._table.getSubTable(obj.get_name()))

    def get_name(self) -> str:
        """Get the name of this root mechanism.

        Returns:
            The name of this root.
        """
        return self._name

    def flush(self) -> None:
        """Flush current position values to network table publishers.

        Publishes the current x and y coordinates to their respective
        network table topics if publishers are available.
        """
        if self._x_publisher is not None:
            self._x_publisher.set(self._x)

        if self._y_publisher is not None:
            self._y_publisher.set(self._y)

    def log_output(self, table: LogTable) -> None:
        """Log output for this root and all child objects.

        Logs the current x and y coordinates to the provided log table
        and recursively logs all child objects.

        Args:
            table: The LogTable to use for logging output.
        """
        table.put("x", self._x)
        table.put("y", self._y)

        for obj in self._objects.values():
            obj.log_output(table.get_subtable(obj.get_name()))

    def generate3d_mechanism(self) -> List[Pose3d]:
        """Generate 3D poses for the entire mechanism starting from this root.

        Converts the 2D mechanism into a series of 3D poses using standard
        coordinate frame (+x forward, +y left, +z up). Each pivot point is
        assumed to be at the origin of the model.

        The coordinate system transforms from the xz plane to xyz plane
        where the 2D y-coordinate becomes the 3D z-coordinate (with y=0).

        Returns:
            A list of 3D poses starting from the root point, processed in
            depth-first order based on insertion order.

        Note:
            Positive rotation in 2D corresponds to negative pitch in 3D.
        """
        poses: List[Pose3d] = []

        # Coordinate shift changes from the xz plane to the xyz plane where 'y' is 0
        initial_pose: Pose3d = Pose3d(self._x, 0, self._y, Rotation3d())

        for obj in self._objects.values():
            # Convert mech2d angle to Rotation3d
            # Remember that +rotation in 2d is -pitch in 3d
            new_rotation = Rotation3d(0, degreesToRadians(-obj.get_angle()), 0)

            # Generate the pose for the next segment
            new_pose = Pose3d(initial_pose.translation(), new_rotation)
            poses.append(new_pose)

            # Recurse down the length of that ligament
            next_pose = new_pose.transformBy(Transform3d(obj.get_object2d_range(), 0, 0, Rotation3d()))
            more_poses: List[Pose3d] = obj.generate3d_mechanism(next_pose)
            poses.extend(more_poses)

        return poses
