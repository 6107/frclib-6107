import pytest
from ntcore import NetworkTableInstance
from wpiutil import Color, Color8Bit

from lib_6107.pykit.LoggedMechanism2d import LoggedMechanism2d
from lib_6107.pykit.logtable import LogTable


@pytest.fixture
def nt_instance():
    inst = NetworkTableInstance.create()
    yield inst
    NetworkTableInstance.destroy(inst)


def test_mechanism_get_root_creates_and_returns_new_root():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    root = mechanism.get_root("Base", 5.0, 5.0)
    assert root.get_name() == "Base"


def test_mechanism_get_root_is_idempotent_and_ignores_new_coordinates_on_repeat_calls():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    first = mechanism.get_root("Base", 5.0, 5.0)
    second = mechanism.get_root("Base", 1.0, 1.0)
    assert first is second


def test_mechanism_get_root_supports_multiple_distinct_roots():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    base = mechanism.get_root("Base", 5.0, 5.0)
    endpoint = mechanism.get_root("Endpoint", 8.0, 5.0)
    assert base is not endpoint
    assert base.get_name() == "Base"
    assert endpoint.get_name() == "Endpoint"


def test_mechanism_close_does_not_raise_when_never_published():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.close()


def test_mechanism_close_does_not_raise_after_publish(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    mechanism.close()


def test_mechanism_set_background_color_does_not_raise_before_publish():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.set_background_color(Color8Bit(Color.WHITE))


def test_mechanism_log_output_records_type_as_mechanism2d():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/.type"].value == "Mechanism2d"


def test_mechanism_log_output_records_non_controllable_flag():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/.controllable"].value is False


def test_mechanism_log_output_records_dims_matching_constructor_width_height():
    mechanism = LoggedMechanism2d(12.0, 7.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/dims"].value == [12.0, 7.0]


def test_mechanism_log_output_records_default_dark_blue_background_when_not_specified():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.DARK_BLUE).hex_string()


def test_mechanism_log_output_records_custom_background_color():
    mechanism = LoggedMechanism2d(10.0, 10.0, background_color=Color8Bit(Color.RED))
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.RED).hex_string()


def test_mechanism_log_output_reflects_background_color_changed_after_construction():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.set_background_color(Color8Bit(Color.GREEN))
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.GREEN).hex_string()


def test_mechanism_log_output_recurses_into_named_root_subtable():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.get_root("Base", 3.0, 4.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/Base/x"].value == 3.0
    assert table.data["/Base/y"].value == 4.0


def test_mechanism_generate3d_mechanism_returns_empty_list_when_no_roots():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    assert mechanism.generate3d_mechanism() == []


def test_mechanism_generate3d_mechanism_includes_poses_from_each_root():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    base = mechanism.get_root("Base", 0.0, 0.0)
    endpoint = mechanism.get_root("Endpoint", 5.0, 5.0)

    from lib_6107.pykit.LoggedMechanismLigament2d import LoggedMechanismLigament2d
    base.append(LoggedMechanismLigament2d("Arm", 1.0, 0.0))
    endpoint.append(LoggedMechanismLigament2d("Arm", 1.0, 0.0))

    poses = mechanism.generate3d_mechanism()
    assert len(poses) == 2


def test_mechanism_publish_sets_type_to_mechanism2d(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    assert table.get_entry(".type").get_string("") == "Mechanism2d"


def test_mechanism_publish_does_not_mark_mechanism_controllable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    assert table.get_entry(".controllable").get_boolean(True) is False


def test_mechanism_publish_publishes_current_dimensions(nt_instance):
    mechanism = LoggedMechanism2d(9.0, 6.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    assert list(table.get_entry("dims").get_double_array([])) == [9.0, 6.0]


def test_mechanism_publish_publishes_current_background_color(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0, background_color=Color8Bit(Color.ORANGE))
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    assert table.get_entry("backgroundColor").get_string("") == Color8Bit(Color.ORANGE).hex_string()


def test_mechanism_publish_binds_existing_root_to_networktable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    root = mechanism.get_root("Base", 2.0, 3.0)

    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)

    root_table = table.get_sub_table("Base")
    assert root_table.get_entry("x").get_double(-1) == 2.0
    assert root_table.get_entry("y").get_double(-1) == 3.0


def test_mechanism_get_root_after_publish_binds_new_root_to_networktable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)

    mechanism.get_root("LateRoot", 6.0, 7.0)

    root_table = table.get_sub_table("LateRoot")
    assert root_table.get_entry("x").get_double(-1) == 6.0
    assert root_table.get_entry("y").get_double(-1) == 7.0


def test_mechanism_publish_called_again_does_not_raise(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.get_table("Mechanism")
    mechanism.publish(table)
    mechanism.publish(table)
