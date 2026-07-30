import ntcore
import pytest
from ntcore import NetworkTableInstance
from wpilib import Color, Color8Bit

from lib_6107.pykit.LoggedMechanism2d import LoggedMechanism2d
from lib_6107.pykit.logtable import LogTable


class RecordingSendableBuilder(ntcore.NTSendableBuilder):
    """NTSendableBuilder double that records published properties against a real NetworkTable."""

    def __init__(self, table):
        super().__init__()
        self._table = table
        self.calls = []
        self.double_array_properties = {}
        self.string_properties = {}

    def getTable(self):
        return self._table

    def getTopic(self, name):
        return self._table.getTopic(name)

    def setSmartDashboardType(self, type_string):
        self.calls.append(("setSmartDashboardType", type_string))

    def setActuator(self, value):
        self.calls.append(("setActuator", value))

    def addDoubleArrayProperty(self, key, getter, setter):
        self.double_array_properties[key] = getter

    def addStringProperty(self, key, getter, setter):
        self.string_properties[key] = getter

    def addBooleanProperty(self, *a, **k): pass

    def addBooleanArrayProperty(self, *a, **k): pass

    def addFloatProperty(self, *a, **k): pass

    def addFloatArrayProperty(self, *a, **k): pass

    def addIntegerProperty(self, *a, **k): pass

    def addIntegerArrayProperty(self, *a, **k): pass

    def addRawProperty(self, *a, **k): pass

    def addSmallStringProperty(self, *a, **k): pass

    def addSmallStringArrayProperty(self, *a, **k): pass

    def addSmallBooleanArrayProperty(self, *a, **k): pass

    def addSmallDoubleArrayProperty(self, *a, **k): pass

    def addSmallFloatArrayProperty(self, *a, **k): pass

    def addSmallIntegerArrayProperty(self, *a, **k): pass

    def addSmallRawProperty(self, *a, **k): pass

    def clearProperties(self): pass

    def getBackendKind(self):
        return ntcore.NTSendableBuilder.BackendKind.kUnknown

    def isPublished(self):
        return True

    def publishConstBoolean(self, *a, **k): pass

    def publishConstBooleanArray(self, *a, **k): pass

    def publishConstDouble(self, *a, **k): pass

    def publishConstDoubleArray(self, *a, **k): pass

    def publishConstFloat(self, *a, **k): pass

    def publishConstFloatArray(self, *a, **k): pass

    def publishConstInteger(self, *a, **k): pass

    def publishConstIntegerArray(self, *a, **k): pass

    def publishConstRaw(self, *a, **k): pass

    def publishConstString(self, *a, **k): pass

    def publishConstStringArray(self, *a, **k): pass

    def setSafeState(self, *a, **k): pass

    def setUpdateTable(self, *a, **k): pass

    def update(self): pass


@pytest.fixture
def nt_instance():
    inst = NetworkTableInstance.create()
    yield inst
    NetworkTableInstance.destroy(inst)


def mechanism_get_root_creates_and_returns_new_root():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    root = mechanism.get_root("Base", 5.0, 5.0)
    assert root.get_name() == "Base"


def mechanism_get_root_is_idempotent_and_ignores_new_coordinates_on_repeat_calls():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    first = mechanism.get_root("Base", 5.0, 5.0)
    second = mechanism.get_root("Base", 1.0, 1.0)
    assert first is second


def mechanism_get_root_supports_multiple_distinct_roots():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    base = mechanism.get_root("Base", 5.0, 5.0)
    endpoint = mechanism.get_root("Endpoint", 8.0, 5.0)
    assert base is not endpoint
    assert base.get_name() == "Base"
    assert endpoint.get_name() == "Endpoint"


def mechanism_close_does_not_raise_when_never_published():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.close()


def mechanism_close_does_not_raise_after_initsendable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    mechanism.close()


def mechanism_set_background_color_does_not_raise_before_publish():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.set_background_color(Color8Bit(Color.kWhite))


def mechanism_log_output_records_type_as_mechanism2d():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/.type"].value == "Mechanism2d"


def mechanism_log_output_records_non_controllable_flag():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/.controllable"].value is False


def mechanism_log_output_records_dims_matching_constructor_width_height():
    mechanism = LoggedMechanism2d(12.0, 7.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/dims"].value == [12.0, 7.0]


def mechanism_log_output_records_default_dark_blue_background_when_not_specified():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.kDarkBlue).hexString()


def mechanism_log_output_records_custom_background_color():
    mechanism = LoggedMechanism2d(10.0, 10.0, background_color=Color8Bit(Color.kRed))
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.kRed).hexString()


def mechanism_log_output_reflects_background_color_changed_after_construction():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.set_background_color(Color8Bit(Color.kGreen))
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/backgroundColor"].value == Color8Bit(Color.kGreen).hexString()


def mechanism_log_output_recurses_into_named_root_subtable():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    mechanism.get_root("Base", 3.0, 4.0)
    table = LogTable(1000)
    mechanism.log_output(table)
    assert table.data["/Base/x"].value == 3.0
    assert table.data["/Base/y"].value == 4.0


def mechanism_generate3d_mechanism_returns_empty_list_when_no_roots():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    assert mechanism.generate3d_mechanism() == []


def mechanism_generate3d_mechanism_includes_poses_from_each_root():
    mechanism = LoggedMechanism2d(10.0, 10.0)
    base = mechanism.get_root("Base", 0.0, 0.0)
    endpoint = mechanism.get_root("Endpoint", 5.0, 5.0)

    from lib_6107.pykit.LoggedMechanismLigament2d import LoggedMechanismLigament2d
    base.append(LoggedMechanismLigament2d("Arm", 1.0, 0.0))
    endpoint.append(LoggedMechanismLigament2d("Arm", 1.0, 0.0))

    poses = mechanism.generate3d_mechanism()
    assert len(poses) == 2


def mechanism_initsendable_sets_smart_dashboard_type_to_mechanism2d(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    assert ("setSmartDashboardType", "Mechanism2d") in builder.calls


def mechanism_initsendable_marks_mechanism_as_non_actuator(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    assert ("setActuator", False) in builder.calls


def mechanism_initsendable_publishes_current_dimensions(nt_instance):
    mechanism = LoggedMechanism2d(9.0, 6.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    assert builder.double_array_properties["dims"]() == [9.0, 6.0]


def mechanism_initsendable_publishes_current_background_color(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0, background_color=Color8Bit(Color.kOrange))
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    assert builder.string_properties["backgroundColor"]() == Color8Bit(Color.kOrange).hexString()


def mechanism_initsendable_binds_existing_root_to_networktable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    root = mechanism.get_root("Base", 2.0, 3.0)

    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)

    root_table = table.getSubTable("Base")
    assert root_table.getEntry("x").getDouble(-1) == 2.0
    assert root_table.getEntry("y").getDouble(-1) == 3.0


def mechanism_get_root_after_initsendable_binds_new_root_to_networktable(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)

    mechanism.get_root("LateRoot", 6.0, 7.0)

    root_table = table.getSubTable("LateRoot")
    assert root_table.getEntry("x").getDouble(-1) == 6.0
    assert root_table.getEntry("y").getDouble(-1) == 7.0


def mechanism_initsendable_called_again_does_not_raise(nt_instance):
    mechanism = LoggedMechanism2d(10.0, 10.0)
    table = nt_instance.getTable("Mechanism")
    builder = RecordingSendableBuilder(table)
    mechanism.initSendable(builder)
    mechanism.initSendable(builder)
