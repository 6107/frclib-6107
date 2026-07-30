import pytest
from ntcore import NetworkTableInstance
from wpilib import Color, Color8Bit
from wpimath.geometry import Rotation2d

from lib_6107.pykit.LoggedMechanismLigament2d import LoggedMechanismLigament2d
from lib_6107.pykit.logtable import LogTable


@pytest.fixture
def nt_instance():
    inst = NetworkTableInstance.create()
    yield inst
    NetworkTableInstance.destroy(inst)


def ligament_initializes_with_given_name_length_and_angle():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    assert ligament.get_name() == "Arm"
    assert ligament.get_length() == 3.0
    assert ligament.get_angle() == 45.0


def ligament_initializes_with_default_line_weight_when_not_specified():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    assert ligament.get_line_weight() == 10


def ligament_initializes_with_custom_line_weight():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0, linewidth=6)
    assert ligament.get_line_weight() == 6


def ligament_initializes_with_default_orange_color_when_not_specified():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    color = ligament.get_color()
    assert color.hexString() == Color8Bit(235, 137, 52).hexString()


def ligament_initializes_with_custom_color():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0, color=Color8Bit(Color.kRed))
    assert ligament.get_color().hexString() == Color8Bit(Color.kRed).hexString()


def ligament_set_angle_updates_stored_angle():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_angle(90.0)
    assert ligament.get_angle() == 90.0


def ligament_set_angle_accepts_rotation2d():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_angle(Rotation2d.fromDegrees(60.0))
    assert ligament.get_angle() == pytest.approx(60.0)


def ligament_set_angle_accepts_negative_values():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_angle(-30.0)
    assert ligament.get_angle() == pytest.approx(-30.0)


def ligament_set_length_updates_stored_length():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_length(5.5)
    assert ligament.get_length() == 5.5


def ligament_get_object2d_range_matches_length():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_length(4.2)
    assert ligament.get_object2d_range() == ligament.get_length()


def ligament_set_color_updates_stored_color():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_color(Color8Bit(Color.kBlue))
    assert ligament.get_color().hexString() == Color8Bit(Color.kBlue).hexString()


def ligament_set_line_weight_updates_stored_weight():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 0.0)
    ligament.set_line_weight(15.0)
    assert ligament.get_line_weight() == 15.0


def ligament_update_entries_publishes_type_as_line(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)
    assert table.getEntry(".type").getString("") == "line"


def ligament_update_entries_publishes_current_angle_length_weight(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0, linewidth=8)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)
    assert table.getEntry("angle").getDouble(-1) == 45.0
    assert table.getEntry("length").getDouble(-1) == 3.0
    assert table.getEntry("weight").getDouble(-1) == 8


def ligament_update_entries_publishes_current_color(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0, color=Color8Bit(Color.kGreen))
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)
    assert table.getEntry("color").getString("") == Color8Bit(Color.kGreen).hexString()


def ligament_get_angle_reflects_value_changed_externally_on_dashboard(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)

    table.getEntry("angle").setDouble(123.0)

    assert ligament.get_angle() == pytest.approx(123.0)


def ligament_get_length_reflects_value_changed_externally_on_dashboard(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)

    table.getEntry("length").setDouble(7.5)

    assert ligament.get_length() == pytest.approx(7.5)


def ligament_set_angle_after_update_entries_publishes_to_dashboard(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)

    ligament.set_length(9.0)

    assert table.getEntry("length").getDouble(-1) == 9.0


def ligament_update_entries_called_again_does_not_raise(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)
    ligament.update_entries(table)
    assert table.getEntry("angle").getDouble(-1) == 45.0


def ligament_close_does_not_raise_after_update_entries(nt_instance):
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = nt_instance.getTable("Mechanism/Arm")
    ligament.update_entries(table)
    ligament.close()


def ligament_close_does_not_raise_when_never_published():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    ligament.close()


def ligament_log_output_records_type_as_line():
    ligament = LoggedMechanismLigament2d("Arm", 3.0, 45.0)
    table = LogTable(1000)
    ligament.log_output(table)
    assert table.data["/.type"].value == "line"


def ligament_log_output_records_angle_length_and_weight():
    ligament = LoggedMechanismLigament2d("Arm", 2.5, 90.0, linewidth=12)
    table = LogTable(1000)
    ligament.log_output(table)
    assert table.data["/angle"].value == 90.0
    assert table.data["/length"].value == 2.5
    assert table.data["/weight"].value == 12


def ligament_log_output_records_color_as_hex_string():
    ligament = LoggedMechanismLigament2d("Arm", 2.5, 90.0, color=Color8Bit(Color.kRed))
    table = LogTable(1000)
    ligament.log_output(table)
    assert table.data["/color"].value == Color8Bit(Color.kRed).hexString()
