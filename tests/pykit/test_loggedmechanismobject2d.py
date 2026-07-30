import pytest
from ntcore import NetworkTableInstance
from wpimath.geometry import Pose3d, Rotation3d

from lib_6107.pykit.LoggedMechanismObject2d import LoggedMechanismObject2d
from lib_6107.pykit.logtable import LogTable


class FakeMechanismObject2d(LoggedMechanismObject2d):
    """Minimal concrete LoggedMechanismObject2d used to exercise the base class in isolation."""

    def __init__(self, name, angle = 0.0, obj_range = 1.0):
        super().__init__(name)
        self._angle = angle
        self._range = obj_range
        self.update_entries_calls = []
        self.closed = False

    def update_entries(self, table):
        self.update_entries_calls.append(table)

    def get_object2d_range(self):
        return self._range

    def get_angle(self):
        return self._angle

    def close(self):
        self.closed = True
        super().close()


@pytest.fixture
def nt_instance():
    inst = NetworkTableInstance.create()
    yield inst
    NetworkTableInstance.destroy(inst)


def object2d_get_name_returns_constructor_name():
    node = FakeMechanismObject2d("Arm")
    assert node.get_name() == "Arm"


def object2d_append_returns_the_appended_object():
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    assert parent.append(child) is child


def object2d_append_raises_on_duplicate_child_name():
    parent = FakeMechanismObject2d("Parent")
    parent.append(FakeMechanismObject2d("Child"))
    with pytest.raises(ValueError):
        parent.append(FakeMechanismObject2d("Child"))


def object2d_append_before_update_does_not_synchronize_child():
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    parent.append(child)
    assert child.update_entries_calls == []


def object2d_append_after_update_immediately_synchronizes_child(nt_instance):
    parent = FakeMechanismObject2d("Parent")
    table = nt_instance.getTable("Mechanism")
    parent.update(table)

    child = FakeMechanismObject2d("Child")
    parent.append(child)

    assert len(child.update_entries_calls) == 1


def object2d_update_invokes_update_entries_with_given_table(nt_instance):
    node = FakeMechanismObject2d("Arm")
    table = nt_instance.getTable("Mechanism")
    node.update(table)

    assert node.update_entries_calls == [table]


def object2d_update_propagates_to_existing_children(nt_instance):
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    parent.append(child)

    table = nt_instance.getTable("Mechanism")
    parent.update(table)

    assert len(child.update_entries_calls) == 1


def object2d_update_propagates_to_grandchildren(nt_instance):
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    grandchild = FakeMechanismObject2d("Grandchild")
    child.append(grandchild)
    parent.append(child)

    table = nt_instance.getTable("Mechanism")
    parent.update(table)

    assert len(grandchild.update_entries_calls) == 1


def object2d_default_update_entries_raises_not_implemented_error(nt_instance):
    node = LoggedMechanismObject2d("Arm")
    table = nt_instance.getTable("Mechanism")
    with pytest.raises(NotImplementedError):
        node.update_entries(table)


def object2d_default_get_object2d_range_raises_not_implemented_error():
    node = LoggedMechanismObject2d("Arm")
    with pytest.raises(NotImplementedError):
        node.get_object2d_range()


def object2d_default_get_angle_raises_not_implemented_error():
    node = LoggedMechanismObject2d("Arm")
    with pytest.raises(NotImplementedError):
        node.get_angle()


def object2d_close_with_no_children_does_not_raise():
    node = FakeMechanismObject2d("Arm")
    node.close()


def object2d_close_recursively_closes_children():
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    parent.append(child)

    parent.close()

    assert child.closed is True


def object2d_append_after_close_allows_reusing_previous_child_name():
    parent = FakeMechanismObject2d("Parent")
    parent.append(FakeMechanismObject2d("Child"))
    parent.close()

    parent.append(FakeMechanismObject2d("Child"))


def object2d_log_output_with_no_children_writes_nothing():
    node = FakeMechanismObject2d("Arm")
    table = LogTable(1000)
    node.log_output(table)
    assert table.data == {}


def object2d_log_output_recurses_into_named_child_subtable():
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child")
    parent.append(child)

    table = LogTable(1000)
    parent.log_output(table)
    child_table = table.getSubTable("Child")
    child_table.put("value", 1.0)

    assert table.data["/Child/value"].value == 1.0


def object2d_generate3d_mechanism_with_no_children_returns_empty_list():
    node = FakeMechanismObject2d("Arm")
    poses = node.generate3d_mechanism(Pose3d())
    assert poses == []


def object2d_generate3d_mechanism_places_first_child_pose_at_seed_translation():
    parent = FakeMechanismObject2d("Parent")
    parent.append(FakeMechanismObject2d("Child", angle=0.0, obj_range=1.0))

    seed = Pose3d(1.0, 2.0, 3.0, Rotation3d())
    poses = parent.generate3d_mechanism(seed)

    assert len(poses) == 1
    translation = poses[0].translation()
    assert translation.x == pytest.approx(1.0)
    assert translation.y == pytest.approx(2.0)
    assert translation.z == pytest.approx(3.0)


def object2d_generate3d_mechanism_inverts_2d_angle_for_3d_pitch():
    parent = FakeMechanismObject2d("Parent")
    parent.append(FakeMechanismObject2d("Child", angle=90.0, obj_range=1.0))

    poses = parent.generate3d_mechanism(Pose3d())

    expected_pitch = -1.5707963267948966
    assert poses[0].rotation().y == pytest.approx(expected_pitch, abs=1e-6)


def object2d_generate3d_mechanism_recurses_into_grandchildren():
    parent = FakeMechanismObject2d("Parent")
    child = FakeMechanismObject2d("Child", angle=0.0, obj_range=1.0)
    grandchild = FakeMechanismObject2d("Grandchild", angle=0.0, obj_range=1.0)
    child.append(grandchild)
    parent.append(child)

    poses = parent.generate3d_mechanism(Pose3d())

    assert len(poses) == 2


def object2d_generate3d_mechanism_preserves_child_append_order():
    parent = FakeMechanismObject2d("Parent")
    parent.append(FakeMechanismObject2d("First", angle=0.0, obj_range=1.0))
    parent.append(FakeMechanismObject2d("Second", angle=45.0, obj_range=2.0))

    poses = parent.generate3d_mechanism(Pose3d())

    assert len(poses) == 2
    assert poses[0].rotation().y == pytest.approx(0.0)
    assert poses[1].rotation().y != pytest.approx(0.0)
