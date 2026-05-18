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
    """A logged mechanism object for 2D visualization and tracking.

    This class represents a node in a mechanism tree structure that can be
    logged and visualized. It manages child objects and provides methods for
    updating network tables and generating 3D representations.

    Attributes:
        _name: The unique name of this mechanism object.
        _table: The NetworkTable associated with this object.
        _objects: Dictionary of child mechanism objects.
    """

    def __init__(self, name: str) -> None:
        """Initialize a new mechanism node object.

        Args:
            name: The node's name must be unique among siblings.
        """
        self._name: str = name
        self._table: NetworkTable | None = None
        self._objects: Dict[str, LoggedMechanismObject2d] = {}

    def close(self) -> None:
        """Close this object and all its child objects.

        This method properly cleans up resources by closing all child objects
        and clearing the object dictionary.
        """
        objects, self._objects = self._objects, {}
        for obj in objects.values():
            obj.close()

    def append(self, obj: "LoggedMechanismObject2d") -> "LoggedMechanismObject2d":
        """Append a mechanism object as a child of this one.

        Args:
            obj: The mechanism object to add as a child.

        Returns:
            The object that was added (useful for method chaining).

        Raises:
            ValueError: If an object with the same name already exists.
                Object names must be unique among siblings.
        """
        name = obj._name
        if name in self._objects:
            raise ValueError(f"Mechanism object names must be unique: {name}")

        self._objects[name] = obj

        if self._table is not None:
            obj.update(self._table.getSubTable(name))

        return obj

    def update(self, table: NetworkTable) -> None:
        """Update this object and all children with the given network table.

        Args:
            table: The NetworkTable to use for updates.
        """
        self._table = table
        self.update_entries(table)

        for obj in self._objects.values():
            obj.update(self._table.getSubTable(obj.get_name()))

    def update_entries(self, table: NetworkTable) -> None:
        """Update entries in the network table.

        This is an abstract method that subclasses must implement
        to define how the specific mechanism object updates its entries.

        Args:
            table: The NetworkTable to update.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("update_entries must be implemented in subclass")

    def get_name(self) -> str:
        """Get the name of this mechanism object.

        Returns:
            The name of this object.
        """
        return self._name

    def log_output(self, table: LogTable) -> None:
        """Log output for this object and all children.

        Args:
            table: The LogTable to use for logging output.
        """
        for obj in self._objects.values():
            obj.log_output(table.get_subtable(obj.get_name()))

    def generate3d_mechanism(self, seed: Pose3d) -> List[Pose3d]:
        """Generate 3D poses for the mechanism tree starting from a seed pose.

        Propagates the mechanism2d down the tree structure using depth-first
        traversal, converting 2D angles to 3D rotations and applying transforms.

        Args:
            seed: The initial 3D pose to start calculations from.

        Returns:
            A list of all poses generated from this point in depth-first order.

        Note:
            Positive rotation in 2D corresponds to negative pitch in 3D.
        """
        poses: List[Pose3d] = []
        initial_pose = seed

        for obj in self._objects.values():
            # Convert mech2d angle to Rotation3d
            # Remember that +rotation in 2d is -pitch in 3d
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
        """Get the range/distance of this 2D object.

        This is an abstract helper method that should return the relevant
        distance measurement for the object type (e.g., length for ligaments,
        radius for circular parts).

        Returns:
            The distance in meters.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("get_object2d_range must be implemented in subclass")

    def get_angle(self) -> degrees:
        """Get the angle of this 2D object.

        This abstract helper method should be implemented by all 2D parts.
        Assumes a normal xy or xz positive direction of left or up, respectively.

        Returns:
            The angle in degrees.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("get_angle must be implemented in subclass")
