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

from typing import Dict, List

from ntcore import NetworkTable
from wpimath.geometry import Pose3d, Rotation3d, Transform3d
from wpimath.units import degrees, degreesToRadians

from lib_6107.pykit.logtable import LogTable


class LoggedMechanismObject2d:
    """Base class for 2D mechanism objects in the logged mechanism visualization system.

    Represents a node in a hierarchical mechanism tree structure. Each node can contain
    child objects and be associated with a NetworkTable for telemetry logging. This class
    provides the interface for converting 2D mechanism objects to 3D poses for visualization
    and supports recursive tree operations like updates and logging.

    Subclasses must implement:
        - update_entries(): Update NetworkTable entries with current state
        - get_object2d_range(): Get the distance/length of this object
        - get_angle(): Get the current angle of this object in degrees

    Attributes:
        _name (str): Unique identifier for this mechanism object.
        _table (NetworkTable): Reference to the NetworkTable for this object.
        _objects (Dict[str, LoggedMechanismObject2d]): Child mechanism objects by name.
    """

    def __init__(self, name: str):
        """Initialize a new Mechanism node object.

        Args:
            name (str): The node's unique name. Must be unique within parent's children.
                Names are used as keys in the parent's object dictionary and for
                NetworkTable subtable identification.

        Raises:
            ValueError: If this name is already used as a sibling object name.
        """
        self._name = name
        self._table = None
        self._objects: Dict[str, LoggedMechanismObject2d] = {}

    def close(self) -> None:
        """Recursively close this object and all child objects.

        Properly cleans up resources for this node and all descendants by calling
        close() on each child mechanism object. This should be called when the
        mechanism is being destroyed to ensure proper cleanup of NetworkTable
        references and other resources.
        """
        objects, self._objects = self._objects, {}
        for obj in objects.values():
            obj.close()

    def append(self, obj: "LoggedMechanismObject2d") -> "LoggedMechanismObject2d":
        """Append a child mechanism object to this object.

        Adds a new child object to this mechanism node. The child's name must be
        unique among siblings. If this object is already connected to a NetworkTable,
        the child is immediately synchronized with its corresponding subtable.

        Args:
            obj (LoggedMechanismObject2d): The child object to add. Must have a
                unique name not used by any sibling.

        Returns:
            LoggedMechanismObject2d: The object that was appended, enabling method
                chaining for functional-style object construction.

        Raises:
            ValueError: If obj._name is already used by another child object.
        """
        name = obj._name
        if name in self._objects:
            raise ValueError(f"Mechanism object names must be unique: {name}")

        self._objects[name] = obj

        if self._table is not None:
            obj.update(self._table.get_subtable(name))

        return obj

    def update(self, table: NetworkTable) -> None:
        """Update this object and all children with a new NetworkTable reference.

        Associates this mechanism object with a NetworkTable for telemetry logging.
        Triggers update_entries() to synchronize current state and recursively
        updates all child objects with their corresponding subtables.

        Args:
            table (NetworkTable): The NetworkTable to associate with this object.
                Children will be mapped to subtables using their names.
        """
        self._table = table
        self.update_entries(table)

        for obj in self._objects.values():
            obj.update(self._table.get_subtable(obj.get_name()))

    def update_entries(self, table: NetworkTable) -> None:
        """Update NetworkTable entries with current mechanism state.

        Abstract method that subclasses must implement to synchronize their
        mechanism state with NetworkTable entries for real-time telemetry logging.

        Args:
            table (NetworkTable): The NetworkTable to update with current state.

        Raises:
            NotImplementedError: This is an abstract method and must be implemented
                by subclasses.
        """
        raise NotImplementedError("updateEntries: Implement in a subclass")

    def get_name(self) -> str:
        """Get the unique name of this mechanism object.

        Returns:
            str: The name assigned to this object at construction.
        """
        return self._name

    def log_output(self, table: LogTable) -> None:
        """Recursively log this object and all children to a LogTable.

        Propagates logging down the mechanism tree, allowing each node to record
        its telemetry data to the appropriate LogTable subtable. Used for
        AdvantageScope integration and telemetry replay analysis.

        Args:
            table (LogTable): The LogTable to write mechanism state to. Child
                objects will log to subtables using their names.
        """
        for obj in self._objects.values():
            obj.log_output(table.get_subtable(obj.get_name()))

    def generate3d_mechanism(self, seed: Pose3d) -> List[Pose3d]:
        """Recursively generate 3D poses for this mechanism and all children.

        Propagates the mechanism structure down the tree, converting 2D objects
        and angles into a sequence of 3D poses for visualization. The conversion
        accounts for the difference between 2D rotation (positive counterclockwise)
        and 3D pitch (negative in 3D space).

        The algorithm:
        1. For each child object, convert its 2D angle to a 3D rotation
        2. Create a pose at the current position with the rotated frame
        3. Transform along the child's length to find the next joint position
        4. Recursively process the child's descendants

        Args:
            seed (Pose3d): The starting position and orientation for this subtree.
                Typically the parent's end-effector position.

        Returns:
            List[Pose3d]: All poses generated from this point in depth-first order.
                Includes the pose for each child and its descendants.
        """
        poses: List[Pose3d] = []
        initial_pose = seed

        for obj in self._objects.values():
            # Convert mech2d angle to Rotation3d
            # Note: +rotation in 2d is -pitch in 3d (inverted Y-axis convention)
            new_rotation = Rotation3d(0, degreesToRadians(-obj.get_angle()), 0)

            # Generate the pose for the new joint
            new_pose = Pose3d(initial_pose.translation(), new_rotation)
            poses.append(new_pose)

            # Recurse down the length of that ligament
            transform: Transform3d = Transform3d(obj.get_object2d_range(), 0, 0, Rotation3d())
            next_pose: Pose3d = new_pose.transformBy(transform)

            more_poses = obj.generate3d_mechanism(next_pose)
            poses.extend(more_poses)

        return poses

    def get_object2d_range(self) -> float:
        """Get the distance/size metric for this 2D object.

        Abstract helper function that returns a characteristic distance or size
        for this mechanism object. For Ligament2d objects, this is the length.
        For circular parts, this might be the radius or diameter.

        Returns:
            float: Distance in meters (for ligaments, this is the length).

        Raises:
            NotImplementedError: This is an abstract method and must be implemented
                by subclasses.
        """
        raise NotImplementedError("getObject2dRange: Implement in a subclass")

    def get_angle(self) -> degrees:
        """Get the current angle of this 2D object.

        Abstract helper function that should be implemented by all 2D mechanism
        parts. Assumes a standard XY or XZ coordinate system with positive angles
        in the counterclockwise direction (left or up, respectively).

        Returns:
            degrees: The object's current angle in degrees.

        Raises:
            NotImplementedError: This is an abstract method and must be implemented
                by subclasses.
        """
        raise NotImplementedError("getAngle: Implement in a subclass")