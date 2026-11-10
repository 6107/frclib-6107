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

from ntcore import NetworkTableInstance
from phoenix6 import StatusCode


class Alert:
    registry = []

    def __init__(self, text: str, is_error: bool = False, ctre_device=None, clear_func=None):

        self.text = text
        self.is_error = is_error
        self.active = False
        self.ctre_device = ctre_device
        self.clear_func = clear_func

        topic_name = "Errors" if is_error else "Warnings"
        self.publisher = NetworkTableInstance.getDefault().getTable("Alerts").getStringArrayTopic(topic_name).publish()
        Alert.registry.append(self)

    def set(self, active: bool):
        if self.active != active:
            self.active = active
            Alert.refresh()

    def clear_sticky(self) -> StatusCode:
        if self.ctre_device and self.clear_func:
            status = self.clear_func()
            if status == StatusCode.OK:
                self.set(False)
                return status
            return StatusCode.OK

    @staticmethod
    def clear_all_device_sticky_faults():
        unique_devices = {a.ctre_device for a in Alert.registry if a.ctre_device is not None}
        for device in unique_devices:
            device.clear_sticky_faults()

        Alert.refresh()

    @staticmethod
    def refresh():

        active_errors = [a.text for a in Alert.registry if a.active and a.is_error]
        active_warnings = [a.text for a in Alert.registry if a.active and not a.is_error]

        table = NetworkTableInstance.getDefault().getTable("Alerts")

        table.getStringArrayTopic("Errors").publish().set(active_errors)
        table.getStringArrayTopic("Warnings").publish().set(active_warnings)
