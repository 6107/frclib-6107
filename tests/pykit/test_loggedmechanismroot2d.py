import pytest
from ntcore import NetworkTableInstance
from wpimath.geometry import Rotation3d

from lib_6107.pykit.LoggedMechanismObject2d import LoggedMechanismObject2d
from lib_6107.pykit.LoggedMechanismRoot2d import LoggedMechanismRoot2d
from lib_6107.pykit.logtable import LogTable


class FakeMechanismObject2d(LoggedMechanismObject2d):
    """Minimal LoggedMechanismObject2d double used to observe root behavior in isolation."""

    def __init__(self, name, angle = 0.0, obj_range = 1.0):
        super().__init__(name)
        self._angle = angle
        self._range = obj_range
        self.update_entries_calls = []

    def update_entries(self, table):
        self.update_entries_calls.append(table)

    def get_object2d_range(self):
        return self._range

    def get_angle(self):
        return self._angle


@pytest.fixture
def nt_instance():
    inst = NetworkTableInstance.create()
    yield inst
    NetworkTableInstance.destroy(inst)


def root_get_name_returns_constructor_name():
    root = LoggedMechanismRoot2d("Base", 1.0, 2.0)
    assert root.get_name() == "Base"


def root_append_returns_the_appended_object():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    child = FakeMechanismObject2d("Arm")
    assert root.append(child) is child


def root_append_raises_on_duplicate_child_name():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.append(FakeMechanismObject2d("Arm"))
    with pytest.raises(ValueError):
        root.append(FakeMechanismObject2d("Arm"))


def root_append_before_update_does_not_synchronize_child():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    child = FakeMechanismObject2d("Arm")
    root.append(child)
    assert child.update_entries_calls == []


def root_append_after_update_immediately_synchronizes_child(nt_instance):
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    table = nt_instance.getTable("Mechanism")
    root.update(table)

    child = FakeMechanismObject2d("Arm")
    root.append(child)

    assert len(child.update_entries_calls) == 1


def root_update_publishes_initial_position(nt_instance):
    root = LoggedMechanismRoot2d("Base", 3.0, 4.0)
    table = nt_instance.getTable("Mechanism")
    root.update(table)

    assert table.getEntry("x").getDouble(-1) == 3.0
    assert table.getEntry("y").getDouble(-1) == 4.0


def root_update_synchronizes_existing_children(nt_instance):
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    child = FakeMechanismObject2d("Arm")
    root.append(child)

    table = nt_instance.getTable("Mechanism")
    root.update(table)

    assert len(child.update_entries_calls) == 1


def root_set_position_updates_published_coordinates(nt_instance):
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    table = nt_instance.getTable("Mechanism")
    root.update(table)

    root.set_position(5.5, -2.5)

    assert table.getEntry("x").getDouble(-1) == 5.5
    assert table.getEntry("y").getDouble(-1) == -2.5


def root_set_position_before_update_does_not_raise():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.set_position(1.0, 1.0)


def root_flush_before_update_does_not_raise():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.flush()


def root_update_called_again_republishes_current_position(nt_instance):
    root = LoggedMechanismRoot2d("Base", 1.0, 2.0)
    first_table = nt_instance.getTable("Mechanism")
    root.update(first_table)

    second_table = nt_instance.getTable("MechanismTwo")
    root.update(second_table)

    assert second_table.getEntry("x").getDouble(-1) == 1.0
    assert second_table.getEntry("y").getDouble(-1) == 2.0


def root_log_output_records_x_and_y():
    root = LoggedMechanismRoot2d("Base", 7.0, 8.0)
    table = LogTable(1000)
    root.log_output(table)

    assert table.data["/x"].value == 7.0
    assert table.data["/y"].value == 8.0


def root_log_output_recurses_into_children():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    child = FakeMechanismObject2d("Arm")
    root.append(child)

    table = LogTable(1000)
    root.log_output(table)

    assert table.data["/x"].value == 0.0


def root_generate3d_mechanism_with_no_children_returns_empty_list():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    assert root.generate3d_mechanism() == []


def root_generate3d_mechanism_places_first_pose_at_root_position():
    root = LoggedMechanismRoot2d("Base", 2.0, 3.0)
    root.append(FakeMechanismObject2d("Arm", angle=0.0, obj_range=1.0))

    poses = root.generate3d_mechanism()

    assert len(poses) == 1
    translation = poses[0].translation()
    assert translation.x == pytest.approx(2.0)
    assert translation.z == pytest.approx(3.0)
    assert translation.y == pytest.approx(0.0)


def root_generate3d_mechanism_inverts_2d_angle_for_3d_pitch():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.append(FakeMechanismObject2d("Arm", angle=90.0, obj_range=1.0))

    poses = root.generate3d_mechanism()

    expected_rotation = Rotation3d(0, -1 * (3.14159265358979 / 2), 0)
    assert poses[0].rotation().y == pytest.approx(expected_rotation.y, abs=1e-6)


def root_generate3d_mechanism_preserves_child_append_order():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.append(FakeMechanismObject2d("First", angle=0.0, obj_range=1.0))
    root.append(FakeMechanismObject2d("Second", angle=45.0, obj_range=2.0))

    poses = root.generate3d_mechanism()

    assert len(poses) == 2
    assert poses[0].rotation().y == pytest.approx(0.0)
    assert poses[1].rotation().y != pytest.approx(0.0)


def root_close_does_not_raise_when_never_updated():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.close()


def root_close_does_not_raise_after_update(nt_instance):
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    table = nt_instance.getTable("Mechanism")
    root.update(table)
    root.close()


def root_append_after_close_allows_reusing_previous_child_name():
    root = LoggedMechanismRoot2d("Base", 0.0, 0.0)
    root.append(FakeMechanismObject2d("Arm"))
    root.close()

    root.append(FakeMechanismObject2d("Arm"))
